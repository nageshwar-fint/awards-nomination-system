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
        "created_by": str(uuid4()),
    }
    response = client.post("/api/v1/cycles", json=cycle_data)
    # HTTPBearer returns 403 when no Authorization header, but 401 when invalid token
    assert response.status_code in (401, 403)  # Unauthorized or Forbidden


def test_create_cycle(client: TestClient, test_team_lead_user, get_auth_headers):
    """Test creating a cycle."""
    cycle_data = {
        "name": "New Test Cycle",
        "start_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "end_at": (datetime.now(timezone.utc) + timedelta(days=31)).isoformat(),
        "created_by": str(test_team_lead_user.id),
    }
    response = client.post(
        "/api/v1/cycles",
        json=cycle_data,
        headers=get_auth_headers(test_team_lead_user),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == cycle_data["name"]
    assert data["status"] == CycleStatus.DRAFT.value


def test_create_cycle_invalid_dates(client: TestClient, test_team_lead_user, get_auth_headers):
    """Test creating cycle with invalid dates (end before start)."""
    cycle_data = {
        "name": "Invalid Cycle",
        "start_at": (datetime.now(timezone.utc) + timedelta(days=31)).isoformat(),
        "end_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "created_by": str(test_team_lead_user.id),
    }
    response = client.post(
        "/api/v1/cycles",
        json=cycle_data,
        headers=get_auth_headers(test_team_lead_user),
    )
    assert response.status_code == 400


def test_update_cycle(client: TestClient, test_draft_cycle, test_team_lead_user, get_auth_headers):
    """Test updating a draft cycle."""
    update_data = {"name": "Updated Cycle Name"}
    response = client.patch(
        f"/api/v1/cycles/{test_draft_cycle.id}",
        json=update_data,
        headers=get_auth_headers(test_team_lead_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Cycle Name"


def test_update_cycle_not_draft(client: TestClient, test_cycle, test_team_lead_user, get_auth_headers):
    """Test updating a non-draft cycle (should fail)."""
    update_data = {"name": "Updated Name"}
    response = client.patch(
        f"/api/v1/cycles/{test_cycle.id}",
        json=update_data,
        headers=get_auth_headers(test_team_lead_user),
    )
    assert response.status_code == 400
    assert "DRAFT" in response.json()["error"]["message"]


def test_update_cycle_unauthorized(client: TestClient, test_draft_cycle):
    """Test updating cycle without authentication."""
    update_data = {"name": "Updated Name"}
    response = client.patch(f"/api/v1/cycles/{test_draft_cycle.id}", json=update_data)
    assert response.status_code in (401, 403)


def test_delete_cycle(client: TestClient, test_draft_cycle, test_team_lead_user, get_auth_headers):
    """Test deleting a draft cycle."""
    response = client.delete(
        f"/api/v1/cycles/{test_draft_cycle.id}",
        headers=get_auth_headers(test_team_lead_user),
    )
    assert response.status_code == 204

    # Verify it's deleted
    get_response = client.get(f"/api/v1/cycles/{test_draft_cycle.id}")
    assert get_response.status_code == 404


def test_delete_cycle_with_nominations(client: TestClient, test_draft_cycle, test_nomination, test_team_lead_user, get_auth_headers, db_session):
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
        headers=get_auth_headers(test_team_lead_user),
    )
    assert response.status_code == 400
    assert "nominations" in response.json()["error"]["message"].lower()


def test_delete_cycle_not_draft(client: TestClient, test_cycle, test_team_lead_user, get_auth_headers):
    """Test deleting non-draft cycle (should fail)."""
    response = client.delete(
        f"/api/v1/cycles/{test_cycle.id}",
        headers=get_auth_headers(test_team_lead_user),
    )
    assert response.status_code == 400
    assert "DRAFT" in response.json()["error"]["message"]
