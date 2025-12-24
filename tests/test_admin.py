"""Tests for admin API endpoints (HR only)."""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from app.models.domain import UserRole


def test_create_user_unauthorized(client: TestClient):
    """Test creating user without authentication."""
    user_data = {
        "name": "New User",
        "email": "newuser@test.com",
        "password": "SecurePass123!",
        "role": "EMPLOYEE",
    }
    response = client.post("/api/v1/admin/users", json=user_data)
    assert response.status_code in (401, 403)


def test_create_user_forbidden_non_hr(client: TestClient, test_team_lead_user, test_manager_user, get_auth_headers):
    """Test that non-HR users cannot create users."""
    user_data = {
        "name": "New User",
        "email": "newuser@test.com",
        "password": "SecurePass123!",
        "role": "EMPLOYEE",
    }
    
    # Team Lead should be forbidden
    response = client.post(
        "/api/v1/admin/users",
        json=user_data,
        headers=get_auth_headers(test_team_lead_user),
    )
    assert response.status_code == 403
    
    # Manager should be forbidden
    response = client.post(
        "/api/v1/admin/users",
        json=user_data,
        headers=get_auth_headers(test_manager_user),
    )
    assert response.status_code == 403


def test_create_user_hr_only(client: TestClient, test_hr_user, test_team, get_auth_headers):
    """Test HR can create users with any role."""
    user_data = {
        "name": "New Employee",
        "email": "newemployee@test.com",
        "password": "SecurePass123!",
        "role": "EMPLOYEE",
        "team_id": str(test_team.id),
        "status": "ACTIVE",
    }
    response = client.post(
        "/api/v1/admin/users",
        json=user_data,
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Employee"
    assert data["email"] == "newemployee@test.com"
    assert data["role"] == "EMPLOYEE"
    assert data["status"] == "ACTIVE"


def test_create_user_with_hr_role(client: TestClient, test_hr_user, get_auth_headers):
    """Test HR can create users with HR (admin) role."""
    user_data = {
        "name": "New HR Admin",
        "email": "newhr@test.com",
        "password": "SecurePass123!",
        "role": "HR",
        "status": "ACTIVE",
    }
    response = client.post(
        "/api/v1/admin/users",
        json=user_data,
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "HR"


def test_create_user_invalid_password(client: TestClient, test_hr_user, get_auth_headers):
    """Test creating user with weak password fails."""
    user_data = {
        "name": "New User",
        "email": "newuser@test.com",
        "password": "weak",  # Too weak
        "role": "EMPLOYEE",
    }
    response = client.post(
        "/api/v1/admin/users",
        json=user_data,
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 400


def test_create_user_duplicate_email(client: TestClient, test_hr_user, test_employee_user, get_auth_headers):
    """Test creating user with duplicate email fails."""
    user_data = {
        "name": "New User",
        "email": test_employee_user.email,  # Duplicate
        "password": "SecurePass123!",
        "role": "EMPLOYEE",
    }
    response = client.post(
        "/api/v1/admin/users",
        json=user_data,
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 400


def test_list_users_hr_only(client: TestClient, test_hr_user, test_team_lead_user, get_auth_headers):
    """Test that only HR can list users."""
    # HR should succeed
    response = client.get(
        "/api/v1/admin/users",
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    
    # Team Lead should be forbidden
    response = client.get(
        "/api/v1/admin/users",
        headers=get_auth_headers(test_team_lead_user),
    )
    assert response.status_code == 403


def test_list_users_with_filters(client: TestClient, test_hr_user, get_auth_headers):
    """Test listing users with filters."""
    response = client.get(
        "/api/v1/admin/users?role_filter=EMPLOYEE&status_filter=ACTIVE",
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # All returned users should be EMPLOYEE and ACTIVE
    for user in data:
        assert user["role"] == "EMPLOYEE"
        assert user["status"] == "ACTIVE"


def test_get_user(client: TestClient, test_hr_user, test_employee_user, get_auth_headers):
    """Test getting a specific user."""
    response = client.get(
        f"/api/v1/admin/users/{test_employee_user.id}",
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_employee_user.id)
    assert data["email"] == test_employee_user.email


def test_update_user_role(client: TestClient, test_hr_user, test_employee_user, get_auth_headers):
    """Test HR can update user role, including assigning HR role."""
    # Promote to MANAGER (TEAM_LEAD role removed)
    update_data = {"role": "MANAGER"}
    response = client.patch(
        f"/api/v1/admin/users/{test_employee_user.id}",
        json=update_data,
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "MANAGER"
    
    # Promote to HR (admin)
    update_data = {"role": "HR"}
    response = client.patch(
        f"/api/v1/admin/users/{test_employee_user.id}",
        json=update_data,
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "HR"
    
    # Demote back to EMPLOYEE
    update_data = {"role": "EMPLOYEE"}
    response = client.patch(
        f"/api/v1/admin/users/{test_employee_user.id}",
        json=update_data,
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "EMPLOYEE"


def test_update_user_status(client: TestClient, test_hr_user, test_employee_user, get_auth_headers):
    """Test HR can update user status."""
    # Deactivate
    update_data = {"status": "INACTIVE"}
    response = client.patch(
        f"/api/v1/admin/users/{test_employee_user.id}",
        json=update_data,
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "INACTIVE"
    
    # Activate
    update_data = {"status": "ACTIVE"}
    response = client.patch(
        f"/api/v1/admin/users/{test_employee_user.id}",
        json=update_data,
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ACTIVE"


def test_deactivate_user(client: TestClient, test_hr_user, test_employee_user, get_auth_headers):
    """Test HR can deactivate users."""
    response = client.post(
        f"/api/v1/admin/users/{test_employee_user.id}/deactivate",
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert "deactivated" in data["message"].lower()


def test_deactivate_user_self_forbidden(client: TestClient, test_hr_user, get_auth_headers):
    """Test HR cannot deactivate themselves."""
    response = client.post(
        f"/api/v1/admin/users/{test_hr_user.id}/deactivate",
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 400
    data = response.json()
    assert "cannot deactivate your own account" in data["error"]["message"].lower()


def test_activate_user(client: TestClient, test_hr_user, test_employee_user, get_auth_headers, db_session):
    """Test HR can activate users."""
    # First deactivate
    test_employee_user.status = "INACTIVE"
    db_session.commit()
    
    # Then activate
    response = client.post(
        f"/api/v1/admin/users/{test_employee_user.id}/activate",
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert "activated" in data["message"].lower()


def test_delete_user_soft_delete(client: TestClient, test_hr_user, test_employee_user, get_auth_headers):
    """Test delete user performs soft delete (sets status to INACTIVE)."""
    response = client.delete(
        f"/api/v1/admin/users/{test_employee_user.id}",
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert "deactivated" in data["message"].lower()
    
    # Verify user still exists but is inactive
    response = client.get(
        f"/api/v1/admin/users/{test_employee_user.id}",
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "INACTIVE"


def test_delete_user_self_forbidden(client: TestClient, test_hr_user, get_auth_headers):
    """Test HR cannot delete themselves."""
    response = client.delete(
        f"/api/v1/admin/users/{test_hr_user.id}",
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 400
    data = response.json()
    assert "cannot delete your own account" in data["error"]["message"].lower()


def test_list_users_search(client: TestClient, test_hr_user, test_employee_user, get_auth_headers):
    """Test searching users by name or email."""
    response = client.get(
        f"/api/v1/admin/users?search={test_employee_user.name.split()[0]}",
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(user["id"] == str(test_employee_user.id) for user in data)
