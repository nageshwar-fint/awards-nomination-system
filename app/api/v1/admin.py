"""Admin API endpoints for user management.

All endpoints require HR role access.
"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.auth.rbac import RequireHR
from app.core.errors import AppError
from app.db.session import get_session
from app.models.domain import User, UserRole
from app.schemas.base import MessageResponse, UserRead, UserUpdate

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=List[UserRead])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    role_filter: Optional[str] = Query(None, description="Filter by role (EMPLOYEE, TEAM_LEAD, MANAGER, HR)"),
    status_filter: Optional[str] = Query(None, description="Filter by status (ACTIVE, INACTIVE)"),
    team_id: Optional[UUID] = Query(None, description="Filter by team ID"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    current_user: User = Depends(RequireHR),
    db: Session = Depends(get_session),
) -> List[UserRead]:
    """
    List all users with optional filtering.
    
    Requires HR role.
    """
    stmt = select(User)
    
    # Apply filters
    if role_filter:
        try:
            role_enum = UserRole[role_filter.upper()]
            stmt = stmt.where(User.role == role_enum)
        except KeyError:
            raise AppError(
                f"Invalid role. Must be one of: {[r.name for r in UserRole]}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    if status_filter:
        stmt = stmt.where(User.status == status_filter.upper())
    
    if team_id:
        stmt = stmt.where(User.team_id == team_id)
    
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            (User.name.ilike(search_pattern)) | (User.email.ilike(search_pattern))
        )
    
    stmt = stmt.order_by(User.created_at.desc()).offset(skip).limit(limit)
    users = db.scalars(stmt).all()
    
    return [UserRead.model_validate(user) for user in users]


@router.get("/users/{user_id}", response_model=UserRead)
def get_user(
    user_id: UUID,
    current_user: User = Depends(RequireHR),
    db: Session = Depends(get_session),
) -> UserRead:
    """
    Get a specific user by ID.
    
    Requires HR role.
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return UserRead.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: UUID,
    user_update: UserUpdate,
    current_user: User = Depends(RequireHR),
    db: Session = Depends(get_session),
) -> UserRead:
    """
    Update a user's information (role, status, team, name, email).
    
    Requires HR role.
    
    - Cannot update password through this endpoint (use password reset flow)
    - Email uniqueness is validated if email is being updated
    - Role must be a valid UserRole enum value
    - Status must be ACTIVE or INACTIVE
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    update_data = user_update.model_dump(exclude_unset=True)
    
    # Validate email uniqueness if email is being updated
    if "email" in update_data and update_data["email"] != user.email:
        existing_user = db.scalar(select(User).where(User.email == update_data["email"]))
        if existing_user and existing_user.id != user_id:
            raise AppError(
                "Email already in use by another user",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        user.email = update_data["email"]
    
    # Update name if provided
    if "name" in update_data:
        user.name = update_data["name"]
    
    # Update role if provided
    if "role" in update_data:
        try:
            user.role = UserRole[update_data["role"].upper()]
        except KeyError:
            raise AppError(
                f"Invalid role. Must be one of: {[r.name for r in UserRole]}",
                status_code=status.HTTP_400_BAD_REQUEST
            )
    
    # Update status if provided
    if "status" in update_data:
        status_value = update_data["status"].upper()
        if status_value not in ("ACTIVE", "INACTIVE"):
            raise AppError(
                "Invalid status. Must be ACTIVE or INACTIVE",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        user.status = status_value
    
    # Update team_id if provided
    if "team_id" in update_data:
        team_id = update_data["team_id"]
        if team_id is not None:
            # Validate team exists
            team = db.get(models.Team, team_id)
            if not team:
                raise AppError(
                    "Team not found",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
        user.team_id = team_id
    
    try:
        db.commit()
        db.refresh(user)
        return UserRead.model_validate(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )


@router.delete("/users/{user_id}", response_model=MessageResponse)
def delete_user(
    user_id: UUID,
    current_user: User = Depends(RequireHR),
    db: Session = Depends(get_session),
) -> MessageResponse:
    """
    Delete a user (soft delete by setting status to INACTIVE).
    
    Requires HR role.
    
    Note: This performs a soft delete by setting the user status to INACTIVE
    rather than actually deleting the record, to preserve data integrity.
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        raise AppError(
            "Cannot delete your own account",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Soft delete: set status to INACTIVE
    user.status = "INACTIVE"
    
    try:
        db.commit()
        return MessageResponse(message=f"User {user.email} has been deactivated successfully")
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


@router.post("/users/{user_id}/activate", response_model=MessageResponse)
def activate_user(
    user_id: UUID,
    current_user: User = Depends(RequireHR),
    db: Session = Depends(get_session),
) -> MessageResponse:
    """
    Activate a user (set status to ACTIVE).
    
    Requires HR role.
    """
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.status = "ACTIVE"
    
    try:
        db.commit()
        return MessageResponse(message=f"User {user.email} has been activated successfully")
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate user: {str(e)}"
        )
