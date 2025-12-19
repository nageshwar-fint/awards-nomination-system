"""Tests for cycles endpoints."""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from fastapi.testclient import TestClient

from app.models.domain import CycleStatus


def test_list_cycles(client: TestClient, test_cycle):
    """Test listing cycles."""
    response = client.get("/api/v1/cycles")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(cycle["id"] == str(test_cycle.id) for cycle in data)


def test_get_cycle(client: TestClient, test_cycle):
    """Test getting a specific cycle."""
    response = client.get(f"/api/v1/cycles/{test_cycle.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_cycle.id)
    assert data["name"] == test_cycle.name


def test_get_cycle_not_found(client: TestClient):
    """Test getting non-existent cycle."""
    fake_id = uuid4()
    response = client.get(f"/api/v1/cycles/{fake_id}")
    assert response.status_code == 404


def test_create_cycle_unauthorized(client: TestClient):
    """Test creating cycle without authentication."""
    cycle_data = {
        "name": "Test Cycle",
        "start_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "end_at": (datetime.now(timezone.utc) + timedelta(days=31)).isoformat(),
    }
    response = client.post("/api/v1/cycles", json=cycle_data)
    # HTTPBearer returns 403 when no Authorization header, but 401 when invalid token
    assert response.status_code in (401, 403)  # Unauthorized or Forbidden


def test_create_cycle_hr_only(client: TestClient, test_hr_user, get_auth_headers):
    """Test that only HR can create cycles."""
    cycle_data = {
        "name": "New Test Cycle",
        "start_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "end_at": (datetime.now(timezone.utc) + timedelta(days=31)).isoformat(),
    }
    response = client.post(
        "/api/v1/cycles",
        json=cycle_data,
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == cycle_data["name"]
    assert data["status"] == CycleStatus.DRAFT.value
    assert data["created_by"] == str(test_hr_user.id)  # Should be set automatically


def test_create_cycle_forbidden_non_hr(client: TestClient, test_team_lead_user, test_manager_user, get_auth_headers):
    """Test that non-HR users cannot create cycles."""
    cycle_data = {
        "name": "New Test Cycle",
        "start_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "end_at": (datetime.now(timezone.utc) + timedelta(days=31)).isoformat(),
    }
    
    # Team Lead should be forbidden
    response = client.post(
        "/api/v1/cycles",
        json=cycle_data,
        headers=get_auth_headers(test_team_lead_user),
    )
    assert response.status_code == 403
    
    # Manager should be forbidden
    response = client.post(
        "/api/v1/cycles",
        json=cycle_data,
        headers=get_auth_headers(test_manager_user),
    )
    assert response.status_code == 403


def test_create_cycle_invalid_dates(client: TestClient, test_hr_user, get_auth_headers):
    """Test creating cycle with invalid dates (end before start)."""
    cycle_data = {
        "name": "Invalid Cycle",
        "start_at": (datetime.now(timezone.utc) + timedelta(days=31)).isoformat(),
        "end_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    }
    response = client.post(
        "/api/v1/cycles",
        json=cycle_data,
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 400


def test_update_cycle_hr_only(client: TestClient, test_draft_cycle, test_hr_user, get_auth_headers):
    """Test that only HR can update cycles."""
    update_data = {"name": "Updated Cycle Name"}
    response = client.patch(
        f"/api/v1/cycles/{test_draft_cycle.id}",
        json=update_data,
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Cycle Name"


def test_update_cycle_forbidden_non_hr(client: TestClient, test_draft_cycle, test_team_lead_user, test_manager_user, get_auth_headers):
    """Test that non-HR users cannot update cycles."""
    update_data = {"name": "Updated Cycle Name"}
    
    # Team Lead should be forbidden
    response = client.patch(
        f"/api/v1/cycles/{test_draft_cycle.id}",
        json=update_data,
        headers=get_auth_headers(test_team_lead_user),
    )
    assert response.status_code == 403
    
    # Manager should be forbidden
    response = client.patch(
        f"/api/v1/cycles/{test_draft_cycle.id}",
        json=update_data,
        headers=get_auth_headers(test_manager_user),
    )
    assert response.status_code == 403


def test_update_cycle_not_draft(client: TestClient, test_cycle, test_hr_user, get_auth_headers):
    """Test updating a non-draft cycle (should fail)."""
    update_data = {"name": "Updated Name"}
    response = client.patch(
        f"/api/v1/cycles/{test_cycle.id}",
        json=update_data,
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 400
    assert "DRAFT" in response.json()["error"]["message"]


def test_update_cycle_unauthorized(client: TestClient, test_draft_cycle):
    """Test updating cycle without authentication."""
    update_data = {"name": "Updated Name"}
    response = client.patch(f"/api/v1/cycles/{test_draft_cycle.id}", json=update_data)
    assert response.status_code in (401, 403)


def test_delete_cycle_hr_only(client: TestClient, test_draft_cycle, test_hr_user, get_auth_headers):
    """Test that only HR can delete cycles."""
    response = client.delete(
        f"/api/v1/cycles/{test_draft_cycle.id}",
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 204

    # Verify it's deleted
    get_response = client.get(f"/api/v1/cycles/{test_draft_cycle.id}")
    assert get_response.status_code == 404


def test_delete_cycle_forbidden_non_hr(client: TestClient, test_draft_cycle, test_team_lead_user, test_manager_user, get_auth_headers):
    """Test that non-HR users cannot delete cycles."""
    # Team Lead should be forbidden
    response = client.delete(
        f"/api/v1/cycles/{test_draft_cycle.id}",
        headers=get_auth_headers(test_team_lead_user),
    )
    assert response.status_code == 403
    
    # Manager should be forbidden
    response = client.delete(
        f"/api/v1/cycles/{test_draft_cycle.id}",
        headers=get_auth_headers(test_manager_user),
    )
    assert response.status_code == 403


def test_delete_cycle_with_nominations(client: TestClient, test_draft_cycle, test_nomination, test_hr_user, get_auth_headers, db_session):
    """Test deleting draft cycle with nominations (should fail)."""
    from app.models.domain import Nomination
    
    # Create a nomination in the draft cycle
    nomination = Nomination(
        id=uuid4(),
        cycle_id=test_draft_cycle.id,
        nominee_user_id=test_nomination.nominee_user_id,
        team_id=test_nomination.team_id,
        submitted_by=test_nomination.submitted_by,
        submitted_at=test_nomination.submitted_at,
        status=test_nomination.status,
    )
    db_session.add(nomination)
    db_session.commit()
    
    response = client.delete(
        f"/api/v1/cycles/{test_draft_cycle.id}",
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 400
    assert "nominations" in response.json()["error"]["message"].lower()


def test_delete_cycle_not_draft(client: TestClient, test_cycle, test_hr_user, get_auth_headers):
    """Test deleting non-draft cycle (should fail)."""
    response = client.delete(
        f"/api/v1/cycles/{test_cycle.id}",
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 400
    assert "DRAFT" in response.json()["error"]["message"]


def test_finalize_cycle_hr_only(client: TestClient, test_cycle, test_hr_user, test_manager_user, get_auth_headers):
    """Test that only HR can finalize cycles."""
    from app.models.domain import CycleStatus
    
    # First close the cycle
    test_cycle.status = CycleStatus.CLOSED
    
    # HR should succeed
    response = client.post(
        f"/api/v1/cycles/{test_cycle.id}/finalize",
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert "finalized" in data["message"].lower()


def test_finalize_cycle_forbidden_manager(client: TestClient, test_cycle, test_manager_user, get_auth_headers, db_session):
    """Test that Manager cannot finalize cycles."""
    from app.models.domain import CycleStatus
    
    # Set cycle to CLOSED
    test_cycle.status = CycleStatus.CLOSED
    db_session.commit()
    
    # Manager should be forbidden
    response = client.post(
        f"/api/v1/cycles/{test_cycle.id}/finalize",
        headers=get_auth_headers(test_manager_user),
    )
    assert response.status_code == 403
