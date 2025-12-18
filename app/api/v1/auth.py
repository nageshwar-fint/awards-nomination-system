"""Authentication endpoints: register, login, forgot password, reset password."""
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.auth.jwt import JWTPayload
from app.auth.password import hash_password, verify_password, validate_password_strength
from app.config import get_settings
from app.core.errors import AppError
from app.db.session import get_session
from app.models.domain import User, UserRole
from app.schemas.base import (
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    SecurityQuestionAnswer,
    TokenResponse,
    UserRead,
)

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["authentication"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


def create_access_token(user: User) -> str:
    """Create JWT access token for user."""
    return JWTPayload.create_token(
        user_id=user.id,
        email=user.email,
        role=user.role.value
    )


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")  # Rate limit: 10 registrations per minute
def register(
    request: Request,
    register_data: RegisterRequest,
    db: Session = Depends(get_session),
) -> UserRead:
    """
    Register a new user.
    
    Defaults to EMPLOYEE role. Password must meet strength requirements.
    """
    # Validate password strength
    is_valid, error_message = validate_password_strength(register_data.password)
    if not is_valid:
        raise AppError(error_message or "Invalid password", status_code=status.HTTP_400_BAD_REQUEST)
    
    # Check if email already exists
    existing_user = db.scalar(select(User).where(User.email == register_data.email))
    if existing_user:
        raise AppError("Email already registered", status_code=status.HTTP_400_BAD_REQUEST)
    
    # Validate team_id if provided
    if register_data.team_id:
        team = db.get(models.Team, register_data.team_id)
        if not team:
            raise AppError("Team not found", status_code=status.HTTP_400_BAD_REQUEST)
    
    # Validate security questions
    if len(register_data.security_questions) < 2:
        raise AppError("At least 2 security questions are required", status_code=status.HTTP_400_BAD_REQUEST)
    
    # Check for duplicate questions
    questions = [q.question_text.lower() for q in register_data.security_questions]
    if len(questions) != len(set(questions)):
        raise AppError("Duplicate security questions are not allowed", status_code=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Hash password
        password_hash = hash_password(register_data.password)
        
        # Create user with EMPLOYEE role by default
        user = User(
            id=uuid4(),
            name=register_data.name,
            email=register_data.email,
            password_hash=password_hash,
            role=UserRole.EMPLOYEE,  # Default role
            team_id=register_data.team_id,
            status="ACTIVE",
        )
        
        db.add(user)
        db.flush()  # Flush to get user.id
        
        # Create security questions
        for idx, sec_q in enumerate(register_data.security_questions, start=1):
            answer_hash = hash_password(sec_q.answer.lower().strip())  # Normalize answer (lowercase, trim)
            security_question = models.SecurityQuestion(
                id=uuid4(),
                user_id=user.id,
                question_text=sec_q.question_text,
                answer_hash=answer_hash,
                question_order=idx,
            )
            db.add(security_question)
        
        db.commit()
        db.refresh(user)
        
        return UserRead.model_validate(user)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register user: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")  # Rate limit: 5 login attempts per minute
def login(
    request: Request,
    login_data: LoginRequest,
    db: Session = Depends(get_session),
) -> TokenResponse:
    """
    Authenticate user and return JWT token.
    
    Requires valid email and password. User must have ACTIVE status.
    """
    # Find user by email
    user = db.scalar(select(User).where(User.email == login_data.email))
    
    # Check if user exists and has password hash
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Verify password
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Check if account is active
    if user.status != "ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact administrator."
        )
    
    # Create access token
    access_token = create_access_token(user)
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,  # Convert to seconds
        user=UserRead.model_validate(user)
    )


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("5/hour")  # Rate limit: 5 password reset requests per hour
def forgot_password(
    request: Request,
    request_data: ForgotPasswordRequest,
    db: Session = Depends(get_session),
) -> MessageResponse:
    """
    Verify user exists for password reset.
    
    Always returns success message to prevent email enumeration.
    Returns message indicating user can proceed with security questions.
    """
    # Find user by email
    user = db.scalar(select(User).where(User.email == request_data.email))
    
    # Always return success to prevent email enumeration
    if user and user.password_hash:
        # Check if user has security questions set up
        security_questions_count = db.scalar(
            select(func.count(models.SecurityQuestion.id)).where(
                models.SecurityQuestion.user_id == user.id
            )
        ) or 0
        
        if security_questions_count == 0:
            # User doesn't have security questions (legacy user)
            return MessageResponse(
                message="If an account with that email exists, please contact administrator for password reset."
            )
    
    return MessageResponse(
        message="If an account with that email exists, you can reset your password by answering your security questions."
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    request: Request,
    request_data: ResetPasswordRequest,
    db: Session = Depends(get_session),
) -> MessageResponse:
    """
    Reset password using security questions.
    
    Validates security question answers and updates password.
    User must answer all their security questions correctly.
    """
    # Validate password strength
    is_valid, error_message = validate_password_strength(request_data.new_password)
    if not is_valid:
        raise AppError(error_message or "Invalid password", status_code=status.HTTP_400_BAD_REQUEST)
    
    # Find user by email
    user = db.scalar(select(User).where(User.email == request_data.email))
    if not user or not user.password_hash:
        # Return generic error to prevent email enumeration
        raise AppError("Invalid email or security question answers", status_code=status.HTTP_400_BAD_REQUEST)
    
    # Get user's security questions
    user_security_questions = db.scalars(
        select(models.SecurityQuestion)
        .where(models.SecurityQuestion.user_id == user.id)
        .order_by(models.SecurityQuestion.question_order)
    ).all()
    
    if not user_security_questions or len(user_security_questions) == 0:
        raise AppError("Security questions not set up for this account. Please contact administrator.", status_code=status.HTTP_400_BAD_REQUEST)
    
    # Verify that all security questions are answered
    if len(request_data.security_question_answers) != len(user_security_questions):
        raise AppError("Must answer all security questions", status_code=status.HTTP_400_BAD_REQUEST)
    
    # Verify each answer
    provided_answers = {qa.question_text.lower(): qa.answer.lower().strip() for qa in request_data.security_question_answers}
    
    for sec_q in user_security_questions:
        question_text_lower = sec_q.question_text.lower()
        if question_text_lower not in provided_answers:
            raise AppError(f"Missing answer for question: {sec_q.question_text}", status_code=status.HTTP_400_BAD_REQUEST)
        
        provided_answer = provided_answers[question_text_lower]
        
        # Verify answer
        if not verify_password(provided_answer, sec_q.answer_hash):
            raise AppError("Invalid security question answers", status_code=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Hash new password
        new_password_hash = hash_password(request_data.new_password)
        
        # Update user password
        user.password_hash = new_password_hash
        
        db.commit()
        
        return MessageResponse(
            message="Password has been reset successfully. You can now login with your new password."
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset password: {str(e)}"
        )
