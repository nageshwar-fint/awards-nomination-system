"""Tests for authentication endpoints: register, login, forgot password, reset password."""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from app import models
from app.auth.password import hash_password, verify_password, validate_password_strength
from app.models.domain import User, UserRole, SecurityQuestion


def test_register_user(client: TestClient, db_session):
    """Test user registration with security questions."""
    register_data = {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "password": "SecurePass123!",
        "security_questions": [
            {
                "question_text": "What was the name of your first pet?",
                "answer": "Fluffy"
            },
            {
                "question_text": "What city were you born in?",
                "answer": "New York"
            }
        ]
    }
    
    response = client.post("/api/v1/auth/register", json=register_data)
    assert response.status_code == 201
    
    data = response.json()
    assert data["name"] == register_data["name"]
    assert data["email"] == register_data["email"]
    assert data["role"] == UserRole.EMPLOYEE.value
    assert "password" not in data  # Password should never be in response
    assert "password_hash" not in data
    
    # Verify user was created in database
    user = db_session.query(User).filter(User.email == register_data["email"]).first()
    assert user is not None
    assert user.name == register_data["name"]
    assert user.password_hash is not None
    assert verify_password(register_data["password"], user.password_hash)
    
    # Verify security questions were stored
    security_questions = db_session.query(SecurityQuestion).filter(
        SecurityQuestion.user_id == user.id
    ).order_by(SecurityQuestion.question_order).all()
    
    assert len(security_questions) == 2
    assert security_questions[0].question_text == register_data["security_questions"][0]["question_text"]
    assert security_questions[1].question_text == register_data["security_questions"][1]["question_text"]
    # Verify answers are hashed
    assert verify_password(register_data["security_questions"][0]["answer"].lower().strip(), security_questions[0].answer_hash)
    assert verify_password(register_data["security_questions"][1]["answer"].lower().strip(), security_questions[1].answer_hash)


def test_register_user_duplicate_email(client: TestClient, db_session, test_user):
    """Test registration fails with duplicate email."""
    register_data = {
        "name": "Another User",
        "email": test_user.email,  # Use existing email
        "password": "SecurePass123!",
        "security_questions": [
            {"question_text": "What is your favorite color?", "answer": "Blue"},
            {"question_text": "What is your mother's maiden name?", "answer": "Smith"}
        ]
    }
    
    response = client.post("/api/v1/auth/register", json=register_data)
    assert response.status_code == 400
    assert "already registered" in response.json()["error"]["message"].lower()


def test_register_user_weak_password(client: TestClient):
    """Test registration fails with weak password."""
    register_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "password": "weak",  # Too short (Pydantic validation)
        "security_questions": [
            {"question_text": "What is your favorite color?", "answer": "Blue"},
            {"question_text": "What is your mother's maiden name?", "answer": "Smith"}
        ]
    }
    
    response = client.post("/api/v1/auth/register", json=register_data)
    # Pydantic validation errors return 422
    assert response.status_code == 422


def test_register_user_insufficient_security_questions(client: TestClient):
    """Test registration fails with less than 2 security questions."""
    register_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "password": "SecurePass123!",
        "security_questions": [
            {"question_text": "What is your favorite color?", "answer": "Blue"}
        ]  # Only 1 question (Pydantic validation)
    }
    
    response = client.post("/api/v1/auth/register", json=register_data)
    # Pydantic validation errors return 422
    assert response.status_code == 422


def test_register_user_duplicate_security_questions(client: TestClient):
    """Test registration fails with duplicate security questions."""
    register_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "password": "SecurePass123!",
        "security_questions": [
            {"question_text": "What is your favorite color?", "answer": "Blue"},
            {"question_text": "What is your favorite color?", "answer": "Red"}  # Duplicate question
        ]
    }
    
    response = client.post("/api/v1/auth/register", json=register_data)
    assert response.status_code == 400
    assert "duplicate" in response.json()["error"]["message"].lower()


def test_register_user_invalid_team_id(client: TestClient):
    """Test registration fails with invalid team_id."""
    register_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "password": "SecurePass123!",
        "team_id": str(uuid4()),  # Non-existent team
        "security_questions": [
            {"question_text": "What is your favorite color?", "answer": "Blue"},
            {"question_text": "What is your mother's maiden name?", "answer": "Smith"}
        ]
    }
    
    response = client.post("/api/v1/auth/register", json=register_data)
    assert response.status_code == 400
    assert "team" in response.json()["error"]["message"].lower()


def test_login_success(client: TestClient, db_session):
    """Test successful login."""
    # Create user with password
    password = "SecurePass123!"
    user = User(
        id=uuid4(),
        name="Test User",
        email="test@example.com",
        password_hash=hash_password(password),
        role=UserRole.EMPLOYEE,
        status="ACTIVE"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    login_data = {
        "email": "test@example.com",
        "password": password
    }
    
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "expires_in" in data
    assert data["user"]["email"] == login_data["email"]
    assert data["user"]["id"] == str(user.id)
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]


def test_login_invalid_email(client: TestClient):
    """Test login fails with invalid email."""
    login_data = {
        "email": "nonexistent@example.com",
        "password": "SomePassword123!"
    }
    
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower() or "unauthorized" in response.json()["detail"].lower()


def test_login_invalid_password(client: TestClient, db_session):
    """Test login fails with invalid password."""
    password = "SecurePass123!"
    user = User(
        id=uuid4(),
        name="Test User",
        email="test@example.com",
        password_hash=hash_password(password),
        role=UserRole.EMPLOYEE,
        status="ACTIVE"
    )
    db_session.add(user)
    db_session.commit()
    
    login_data = {
        "email": "test@example.com",
        "password": "WrongPassword123!"
    }
    
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower() or "unauthorized" in response.json()["detail"].lower()


def test_login_inactive_user(client: TestClient, db_session):
    """Test login fails for inactive user."""
    password = "SecurePass123!"
    user = User(
        id=uuid4(),
        name="Test User",
        email="test@example.com",
        password_hash=hash_password(password),
        role=UserRole.EMPLOYEE,
        status="INACTIVE"  # Inactive status
    )
    db_session.add(user)
    db_session.commit()
    
    login_data = {
        "email": "test@example.com",
        "password": password
    }
    
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 403
    assert "inactive" in response.json()["detail"].lower()


def test_login_user_without_password(client: TestClient, db_session, test_user):
    """Test login fails for user without password_hash (legacy user)."""
    # test_user doesn't have password_hash by default
    login_data = {
        "email": test_user.email,
        "password": "SomePassword123!"
    }
    
    response = client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower() or "unauthorized" in response.json()["detail"].lower()


def test_forgot_password_user_exists(client: TestClient, db_session):
    """Test forgot password for existing user."""
    password = "SecurePass123!"
    user = User(
        id=uuid4(),
        name="Test User",
        email="test@example.com",
        password_hash=hash_password(password),
        role=UserRole.EMPLOYEE,
        status="ACTIVE"
    )
    db_session.add(user)
    db_session.commit()
    
    # Add security questions
    for idx, q in enumerate([
        {"question": "What is your favorite color?", "answer": "Blue"},
        {"question": "What city were you born in?", "answer": "New York"}
    ], start=1):
        sq = SecurityQuestion(
            id=uuid4(),
            user_id=user.id,
            question_text=q["question"],
            answer_hash=hash_password(q["answer"].lower().strip()),
            question_order=idx
        )
        db_session.add(sq)
    db_session.commit()
    
    forgot_data = {
        "email": "test@example.com"
    }
    
    response = client.post("/api/v1/auth/forgot-password", json=forgot_data)
    assert response.status_code == 200
    assert "message" in response.json()
    # Should return success message even if user exists (security)
    assert "security question" in response.json()["message"].lower() or "reset" in response.json()["message"].lower()


def test_forgot_password_user_not_exists(client: TestClient):
    """Test forgot password for non-existent user (should still return success)."""
    forgot_data = {
        "email": "nonexistent@example.com"
    }
    
    response = client.post("/api/v1/auth/forgot-password", json=forgot_data)
    assert response.status_code == 200
    # Should return success to prevent email enumeration
    assert "message" in response.json()


def test_reset_password_success(client: TestClient, db_session):
    """Test successful password reset with security questions."""
    # Create user with password and security questions
    old_password = "OldPass123!"
    new_password = "NewPass123!"
    
    user = User(
        id=uuid4(),
        name="Test User",
        email="test@example.com",
        password_hash=hash_password(old_password),
        role=UserRole.EMPLOYEE,
        status="ACTIVE"
    )
    db_session.add(user)
    db_session.flush()
    
    # Add security questions
    questions = [
        {"question": "What is your favorite color?", "answer": "Blue"},
        {"question": "What city were you born in?", "answer": "New York"}
    ]
    
    security_questions = []
    for idx, q in enumerate(questions, start=1):
        sq = SecurityQuestion(
            id=uuid4(),
            user_id=user.id,
            question_text=q["question"],
            answer_hash=hash_password(q["answer"].lower().strip()),
            question_order=idx
        )
        db_session.add(sq)
        security_questions.append(sq)
    db_session.commit()
    
    reset_data = {
        "email": "test@example.com",
        "security_question_answers": [
            {"question_text": q["question"], "answer": q["answer"]}
            for q in questions
        ],
        "new_password": new_password
    }
    
    response = client.post("/api/v1/auth/reset-password", json=reset_data)
    assert response.status_code == 200
    assert "successfully" in response.json()["message"].lower()
    
    # Verify password was changed
    db_session.refresh(user)
    assert verify_password(new_password, user.password_hash)
    assert not verify_password(old_password, user.password_hash)


def test_reset_password_invalid_email(client: TestClient):
    """Test password reset fails with invalid email."""
    reset_data = {
        "email": "nonexistent@example.com",
        "security_question_answers": [
            {"question_text": "What is your favorite color?", "answer": "Blue"},
            {"question_text": "What city were you born in?", "answer": "New York"}
        ],
        "new_password": "NewPass123!"
    }
    
    response = client.post("/api/v1/auth/reset-password", json=reset_data)
    assert response.status_code == 400
    assert "invalid" in response.json()["error"]["message"].lower() or "email" in response.json()["error"]["message"].lower()


def test_reset_password_no_security_questions(client: TestClient, db_session):
    """Test password reset fails when user has no security questions."""
    user = User(
        id=uuid4(),
        name="Test User",
        email="test@example.com",
        password_hash=hash_password("OldPass123!"),
        role=UserRole.EMPLOYEE,
        status="ACTIVE"
    )
    db_session.add(user)
    db_session.commit()
    
    # Provide at least 2 answers to pass Pydantic validation (min_length=2)
    reset_data = {
        "email": "test@example.com",
        "security_question_answers": [
            {"question_text": "What is your favorite color?", "answer": "Blue"},
            {"question_text": "What city were you born in?", "answer": "New York"}
        ],
        "new_password": "NewPass123!"
    }
    
    response = client.post("/api/v1/auth/reset-password", json=reset_data)
    # Business logic check - user has no security questions
    assert response.status_code == 400
    assert "security question" in response.json()["error"]["message"].lower()


def test_reset_password_wrong_answers(client: TestClient, db_session):
    """Test password reset fails with wrong security question answers."""
    user = User(
        id=uuid4(),
        name="Test User",
        email="test@example.com",
        password_hash=hash_password("OldPass123!"),
        role=UserRole.EMPLOYEE,
        status="ACTIVE"
    )
    db_session.add(user)
    db_session.flush()
    
    # Add security questions
    questions = [
        {"question": "What is your favorite color?", "answer": "Blue"},
        {"question": "What city were you born in?", "answer": "New York"}
    ]
    
    for idx, q in enumerate(questions, start=1):
        sq = SecurityQuestion(
            id=uuid4(),
            user_id=user.id,
            question_text=q["question"],
            answer_hash=hash_password(q["answer"].lower().strip()),
            question_order=idx
        )
        db_session.add(sq)
    db_session.commit()
    
    reset_data = {
        "email": "test@example.com",
        "security_question_answers": [
            {"question_text": "What is your favorite color?", "answer": "Red"},  # Wrong answer
            {"question_text": "What city were you born in?", "answer": "New York"}
        ],
        "new_password": "NewPass123!"
    }
    
    response = client.post("/api/v1/auth/reset-password", json=reset_data)
    assert response.status_code == 400
    assert "invalid" in response.json()["error"]["message"].lower() or "security question" in response.json()["error"]["message"].lower()
    
    # Verify password was NOT changed
    db_session.refresh(user)
    assert verify_password("OldPass123!", user.password_hash)  # Still old password


def test_reset_password_missing_questions(client: TestClient, db_session):
    """Test password reset fails when not all questions are answered."""
    user = User(
        id=uuid4(),
        name="Test User",
        email="test@example.com",
        password_hash=hash_password("OldPass123!"),
        role=UserRole.EMPLOYEE,
        status="ACTIVE"
    )
    db_session.add(user)
    db_session.flush()
    
    # Add 2 security questions
    questions = [
        {"question": "What is your favorite color?", "answer": "Blue"},
        {"question": "What city were you born in?", "answer": "New York"}
    ]
    
    for idx, q in enumerate(questions, start=1):
        sq = SecurityQuestion(
            id=uuid4(),
            user_id=user.id,
            question_text=q["question"],
            answer_hash=hash_password(q["answer"].lower().strip()),
            question_order=idx
        )
        db_session.add(sq)
    db_session.commit()
    
    reset_data = {
        "email": "test@example.com",
        "security_question_answers": [
            {"question_text": "What is your favorite color?", "answer": "Blue"}
            # Missing second question - violates min_length=2 in schema
        ],
        "new_password": "NewPass123!"
    }
    
    response = client.post("/api/v1/auth/reset-password", json=reset_data)
    # Pydantic validation error (min_length=2 violated)
    assert response.status_code == 422


def test_reset_password_weak_new_password(client: TestClient, db_session):
    """Test password reset fails with weak new password."""
    user = User(
        id=uuid4(),
        name="Test User",
        email="test@example.com",
        password_hash=hash_password("OldPass123!"),
        role=UserRole.EMPLOYEE,
        status="ACTIVE"
    )
    db_session.add(user)
    db_session.flush()
    
    questions = [
        {"question": "What is your favorite color?", "answer": "Blue"},
        {"question": "What city were you born in?", "answer": "New York"}
    ]
    
    for idx, q in enumerate(questions, start=1):
        sq = SecurityQuestion(
            id=uuid4(),
            user_id=user.id,
            question_text=q["question"],
            answer_hash=hash_password(q["answer"].lower().strip()),
            question_order=idx
        )
        db_session.add(sq)
    db_session.commit()
    
    reset_data = {
        "email": "test@example.com",
        "security_question_answers": [
            {"question_text": q["question"], "answer": q["answer"]}
            for q in questions
        ],
        "new_password": "weak"  # Weak password (Pydantic validation)
    }
    
    response = client.post("/api/v1/auth/reset-password", json=reset_data)
    # Pydantic validation errors return 422
    assert response.status_code == 422


def test_reset_password_case_insensitive_answers(client: TestClient, db_session):
    """Test password reset works with case-insensitive answers."""
    user = User(
        id=uuid4(),
        name="Test User",
        email="test@example.com",
        password_hash=hash_password("OldPass123!"),
        role=UserRole.EMPLOYEE,
        status="ACTIVE"
    )
    db_session.add(user)
    db_session.flush()
    
    # Store answer as lowercase
    questions = [
        {"question": "What is your favorite color?", "answer": "blue"},  # lowercase stored
        {"question": "What city were you born in?", "answer": "new york"}  # lowercase stored
    ]
    
    for idx, q in enumerate(questions, start=1):
        sq = SecurityQuestion(
            id=uuid4(),
            user_id=user.id,
            question_text=q["question"],
            answer_hash=hash_password(q["answer"].lower().strip()),
            question_order=idx
        )
        db_session.add(sq)
    db_session.commit()
    
    # Try with different cases
    reset_data = {
        "email": "test@example.com",
        "security_question_answers": [
            {"question_text": "What is your favorite color?", "answer": "BLUE"},  # Uppercase
            {"question_text": "What city were you born in?", "answer": "New York"}  # Mixed case
        ],
        "new_password": "NewPass123!"
    }
    
    response = client.post("/api/v1/auth/reset-password", json=reset_data)
    assert response.status_code == 200
    # Should work because answers are normalized (lowercase, trimmed)


def test_password_strength_validation():
    """Test password strength validation utility."""
    # Valid password
    is_valid, error = validate_password_strength("SecurePass123!")
    assert is_valid is True
    assert error is None
    
    # Too short
    is_valid, error = validate_password_strength("Short1!")
    assert is_valid is False
    assert "8" in error.lower()
    
    # No uppercase
    is_valid, error = validate_password_strength("securepass123!")
    assert is_valid is False
    assert "uppercase" in error.lower()
    
    # No lowercase
    is_valid, error = validate_password_strength("SECUREPASS123!")
    assert is_valid is False
    assert "lowercase" in error.lower()
    
    # No number
    is_valid, error = validate_password_strength("SecurePass!")
    assert is_valid is False
    assert "number" in error.lower()
    
    # No special character
    is_valid, error = validate_password_strength("SecurePass123")
    assert is_valid is False
    assert "special" in error.lower()


def test_password_hashing():
    """Test password hashing and verification."""
    password = "TestPassword123!"
    
    # Hash password
    password_hash = hash_password(password)
    assert password_hash != password  # Should be hashed
    assert len(password_hash) > 50  # bcrypt hashes are long
    
    # Verify correct password
    assert verify_password(password, password_hash) is True
    
    # Verify incorrect password
    assert verify_password("WrongPassword", password_hash) is False
    
    # Same password should produce different hashes (due to salt)
    password_hash2 = hash_password(password)
    assert password_hash != password_hash2
    # But both should verify correctly
    assert verify_password(password, password_hash2) is True


def test_logout(client: TestClient, get_auth_headers, test_user):
    """Test logout endpoint."""
    headers = get_auth_headers(test_user)
    
    response = client.post("/api/v1/auth/logout", headers=headers)
    
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "logged out" in data["message"].lower()


def test_logout_unauthorized(client: TestClient):
    """Test logout without authentication."""
    response = client.post("/api/v1/auth/logout")
    assert response.status_code in (401, 403)
