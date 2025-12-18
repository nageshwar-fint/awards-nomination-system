"""Tests for approvals endpoints."""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient


def test_get_nomination_approvals(client: TestClient, test_nomination):
    """Test getting approvals for a nomination."""
    response = client.get(f"/api/v1/nominations/{test_nomination.id}/approvals")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_nomination_approvals_nomination_not_found(client: TestClient):
    """Test getting approvals for non-existent nomination."""
    fake_id = uuid4()
    response = client.get(f"/api/v1/nominations/{fake_id}/approvals")
    assert response.status_code == 404


def test_approve_nomination_unauthorized(client: TestClient, test_nomination):
    """Test approving nomination without authentication."""
    approval_data = {
        "nomination_id": str(test_nomination.id),
        "actor_user_id": str(uuid4()),
        "reason": "Great work",
    }
    response = client.post("/api/v1/approvals/approve", json=approval_data)
    assert response.status_code in (401, 403)


def test_approve_nomination_employee_role(client: TestClient, test_nomination, test_employee_user, get_auth_headers):
    """Test approving nomination as employee (should fail)."""
    approval_data = {
        "nomination_id": str(test_nomination.id),
        "actor_user_id": str(test_employee_user.id),
        "reason": "Great work",
    }
    response = client.post(
        "/api/v1/approvals/approve",
        json=approval_data,
        headers=get_auth_headers(test_employee_user),
    )
    assert response.status_code in (401, 403)


def test_approve_nomination(client: TestClient, test_nomination, test_manager_user, get_auth_headers):
    """Test approving a nomination."""
    approval_data = {
        "nomination_id": str(test_nomination.id),
        "actor_user_id": str(test_manager_user.id),  # Will be overridden by auth
        "reason": "Excellent performance",
    }
    response = client.post(
        "/api/v1/approvals/approve",
        json=approval_data,
        headers=get_auth_headers(test_manager_user),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["action"] == "APPROVE"
    assert data["nomination_id"] == str(test_nomination.id)

    # Verify nomination status updated
    nomination_response = client.get(f"/api/v1/nominations/{test_nomination.id}")
    nomination_data = nomination_response.json()
    assert nomination_data["status"] == "APPROVED"


def test_approve_nomination_already_processed(client: TestClient, test_nomination, test_manager_user, get_auth_headers):
    """Test approving nomination that's already been processed."""
    # First approval
    approval_data = {
        "nomination_id": str(test_nomination.id),
        "actor_user_id": str(test_manager_user.id),
        "reason": "First approval",
    }
    response1 = client.post(
        "/api/v1/approvals/approve",
        json=approval_data,
        headers=get_auth_headers(test_manager_user),
    )
    assert response1.status_code == 201

    # Try to approve again (should fail)
    response2 = client.post(
        "/api/v1/approvals/approve",
        json=approval_data,
        headers=get_auth_headers(test_manager_user),
    )
    assert response2.status_code == 400
    assert "already processed" in response2.json()["error"]["message"].lower()


def test_reject_nomination(client: TestClient, test_cycle, test_employee_user, test_manager_user, test_team_lead_user, test_criteria, get_auth_headers, db_session):
    """Test rejecting a nomination."""
    # Create a fresh pending nomination for rejection test (use different nominee to avoid duplicates)
    from app.models.domain import Nomination, NominationStatus, User, UserRole
    from datetime import datetime, timezone
    
    # Create another employee as nominee to avoid duplicate constraint
    another_employee = User(
        id=uuid4(),
        name="Another Employee",
        email="another@test.com",
        role=UserRole.EMPLOYEE,
        team_id=test_employee_user.team_id,
        status="ACTIVE",
    )
    db_session.add(another_employee)
    db_session.flush()
    
    pending_nomination = Nomination(
        id=uuid4(),
        cycle_id=test_cycle.id,
        nominee_user_id=another_employee.id,  # Use different nominee
        team_id=another_employee.team_id,
        submitted_by=test_team_lead_user.id,
        submitted_at=datetime.now(timezone.utc),
        status=NominationStatus.PENDING,
    )
    db_session.add(pending_nomination)
    db_session.commit()

    rejection_data = {
        "nomination_id": str(pending_nomination.id),
        "actor_user_id": str(test_manager_user.id),
        "reason": "Does not meet criteria",
    }
    response = client.post(
        "/api/v1/approvals/reject",
        json=rejection_data,
        headers=get_auth_headers(test_manager_user),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["action"] == "REJECT"
    assert data["nomination_id"] == str(pending_nomination.id)

    # Verify nomination status updated
    nomination_response = client.get(f"/api/v1/nominations/{pending_nomination.id}")
    nomination_data = nomination_response.json()
    assert nomination_data["status"] == "REJECTED"


def test_reject_nomination_unauthorized(client: TestClient, test_nomination):
    """Test rejecting nomination without authentication."""
    rejection_data = {
        "nomination_id": str(test_nomination.id),
        "actor_user_id": str(uuid4()),
        "reason": "Not good enough",
    }
    response = client.post("/api/v1/approvals/reject", json=rejection_data)
    assert response.status_code in (401, 403)
