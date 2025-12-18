"""Tests for nominations endpoints."""
import pytest
from datetime import datetime, timezone
from uuid import uuid4
from fastapi.testclient import TestClient


def test_list_nominations(client: TestClient, test_nomination):
    """Test listing nominations."""
    response = client.get("/api/v1/nominations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(n["id"] == str(test_nomination.id) for n in data)


def test_list_nominations_filter_by_cycle(client: TestClient, test_cycle, test_nomination):
    """Test listing nominations filtered by cycle."""
    response = client.get(f"/api/v1/nominations?cycle_id={test_cycle.id}")
    assert response.status_code == 200
    data = response.json()
    assert all(n["cycle_id"] == str(test_cycle.id) for n in data)


def test_list_nominations_filter_by_status(client: TestClient, test_nomination):
    """Test listing nominations filtered by status."""
    response = client.get("/api/v1/nominations?status_filter=PENDING")
    assert response.status_code == 200
    data = response.json()
    assert all(n["status"] == "PENDING" for n in data)


def test_list_nominations_invalid_status(client: TestClient):
    """Test listing nominations with invalid status filter."""
    response = client.get("/api/v1/nominations?status_filter=INVALID")
    assert response.status_code == 400


def test_get_nomination(client: TestClient, test_nomination):
    """Test getting a specific nomination."""
    response = client.get(f"/api/v1/nominations/{test_nomination.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_nomination.id)
    assert data["cycle_id"] == str(test_nomination.cycle_id)


def test_get_nomination_not_found(client: TestClient):
    """Test getting non-existent nomination."""
    fake_id = uuid4()
    response = client.get(f"/api/v1/nominations/{fake_id}")
    assert response.status_code == 404


def test_submit_nomination_unauthorized(client: TestClient, test_cycle, test_employee_user, test_criteria):
    """Test submitting nomination without authentication."""
    nomination_data = {
        "cycle_id": str(test_cycle.id),
        "nominee_user_id": str(test_employee_user.id),
        "submitted_by": str(uuid4()),
        "scores": [{
            "criteria_id": str(test_criteria.id),
            "score": 8,
            "comment": "Great work",
        }],
    }
    response = client.post("/api/v1/nominations", json=nomination_data)
    assert response.status_code in (401, 403)


def test_submit_nomination(client: TestClient, test_team_lead_user, test_employee_user, get_auth_headers, db_session):
    """Test submitting a nomination."""
    # Create fresh cycle and criteria to avoid conflicts with fixtures
    from app.models.domain import NominationCycle, CycleStatus, Criteria, User, UserRole, Team
    from datetime import timedelta
    
    # Create a new cycle
    new_cycle = NominationCycle(
        id=uuid4(),
        name="Test Submission Cycle",
        start_at=datetime.now(timezone.utc) - timedelta(days=1),
        end_at=datetime.now(timezone.utc) + timedelta(days=30),
        status=CycleStatus.OPEN,
        created_by=test_team_lead_user.id,
    )
    db_session.add(new_cycle)
    db_session.commit()
    
    # Create criteria for this cycle
    criteria = Criteria(
        id=uuid4(),
        cycle_id=new_cycle.id,
        name="Test Criteria",
        weight=1.0,
        is_active=True,
    )
    db_session.add(criteria)
    db_session.commit()
    
    nomination_data = {
        "cycle_id": str(new_cycle.id),
        "nominee_user_id": str(test_employee_user.id),
        "submitted_by": str(test_team_lead_user.id),  # Will be overridden by auth
        "scores": [{
            "criteria_id": str(criteria.id),
            "score": 9,
            "comment": "Excellent performance",
        }],
    }
    response = client.post(
        "/api/v1/nominations",
        json=nomination_data,
        headers=get_auth_headers(test_team_lead_user),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["cycle_id"] == str(new_cycle.id)
    assert data["nominee_user_id"] == str(test_employee_user.id)
    assert data["status"] == "PENDING"


def test_submit_nomination_employee_role(client: TestClient, test_cycle, test_employee_user, test_criteria, get_auth_headers):
    """Test submitting nomination as employee (should fail)."""
    nomination_data = {
        "cycle_id": str(test_cycle.id),
        "nominee_user_id": str(test_employee_user.id),
        "submitted_by": str(test_employee_user.id),
        "scores": [{
            "criteria_id": str(test_criteria.id),
            "score": 8,
        }],
    }
    response = client.post(
        "/api/v1/nominations",
        json=nomination_data,
        headers=get_auth_headers(test_employee_user),
    )
    assert response.status_code in (401, 403)


def test_submit_nomination_cycle_closed(client: TestClient, test_team_lead_user, test_employee_user, get_auth_headers, db_session):
    """Test submitting nomination to closed cycle (should fail)."""
    from app.models.domain import NominationCycle, CycleStatus, Criteria
    from datetime import timedelta
    
    # Create a closed cycle
    closed_cycle = NominationCycle(
        id=uuid4(),
        name="Closed Cycle",
        start_at=datetime.now(timezone.utc) - timedelta(days=60),
        end_at=datetime.now(timezone.utc) - timedelta(days=30),
        status=CycleStatus.CLOSED,
        created_by=test_team_lead_user.id,
    )
    db_session.add(closed_cycle)
    db_session.commit()
    
    # Create criteria for the closed cycle
    criteria = Criteria(
        id=uuid4(),
        cycle_id=closed_cycle.id,
        name="Test Criteria",
        weight=1.0,
        is_active=True,
    )
    db_session.add(criteria)
    db_session.commit()

    nomination_data = {
        "cycle_id": str(closed_cycle.id),
        "nominee_user_id": str(test_employee_user.id),
        "submitted_by": str(test_team_lead_user.id),
        "scores": [{
            "criteria_id": str(criteria.id),
            "score": 8,
        }],
    }
    response = client.post(
        "/api/v1/nominations",
        json=nomination_data,
        headers=get_auth_headers(test_team_lead_user),
    )
    assert response.status_code == 400
