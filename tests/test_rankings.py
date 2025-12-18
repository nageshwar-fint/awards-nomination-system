"""Tests for rankings endpoints."""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient


def test_get_cycle_rankings(client: TestClient, test_cycle):
    """Test getting rankings for a cycle."""
    response = client.get(f"/api/v1/cycles/{test_cycle.id}/rankings")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_cycle_rankings_cycle_not_found(client: TestClient):
    """Test getting rankings for non-existent cycle."""
    fake_id = uuid4()
    response = client.get(f"/api/v1/cycles/{fake_id}/rankings")
    assert response.status_code == 404


def test_compute_rankings_unauthorized(client: TestClient, test_cycle):
    """Test computing rankings without authentication."""
    response = client.post(f"/api/v1/cycles/{test_cycle.id}/rankings/compute")
    assert response.status_code in (401, 403)


def test_compute_rankings_employee_role(client: TestClient, test_cycle, test_employee_user, get_auth_headers):
    """Test computing rankings as employee (should fail)."""
    response = client.post(
        f"/api/v1/cycles/{test_cycle.id}/rankings/compute",
        headers=get_auth_headers(test_employee_user),
    )
    assert response.status_code in (401, 403)


def test_compute_rankings(client: TestClient, test_cycle, test_manager_user, get_auth_headers, db_session):
    """Test computing rankings for a cycle."""
    # First, we need an approved nomination
    from app.models.domain import Nomination, NominationStatus
    from datetime import datetime, timezone
    
    approved_nomination = Nomination(
        id=uuid4(),
        cycle_id=test_cycle.id,
        nominee_user_id=test_cycle.created_by,  # Use cycle creator as nominee
        team_id=None,
        submitted_by=test_cycle.created_by,
        submitted_at=datetime.now(timezone.utc),
        status=NominationStatus.APPROVED,
    )
    db_session.add(approved_nomination)
    db_session.commit()

    response = client.post(
        f"/api/v1/cycles/{test_cycle.id}/rankings/compute",
        headers=get_auth_headers(test_manager_user),
    )
    assert response.status_code == 201
    data = response.json()
    assert isinstance(data, list)


def test_finalize_cycle_unauthorized(client: TestClient, test_cycle):
    """Test finalizing cycle without authentication."""
    response = client.post(f"/api/v1/cycles/{test_cycle.id}/finalize")
    assert response.status_code in (401, 403)


def test_finalize_cycle_not_closed(client: TestClient, test_cycle, test_manager_user, get_auth_headers):
    """Test finalizing cycle that's not closed (should fail)."""
    response = client.post(
        f"/api/v1/cycles/{test_cycle.id}/finalize",
        headers=get_auth_headers(test_manager_user),
    )
    assert response.status_code == 400
    assert "CLOSED" in response.json()["error"]["message"]


def test_finalize_cycle(client: TestClient, test_manager_user, get_auth_headers, db_session):
    """Test finalizing a closed cycle."""
    from app.models.domain import NominationCycle, CycleStatus
    from datetime import datetime, timezone, timedelta
    
    # Create a closed cycle
    closed_cycle = NominationCycle(
        id=uuid4(),
        name="Cycle to Finalize",
        start_at=datetime.now(timezone.utc) - timedelta(days=60),
        end_at=datetime.now(timezone.utc) - timedelta(days=30),
        status=CycleStatus.CLOSED,
        created_by=test_manager_user.id,
    )
    db_session.add(closed_cycle)
    db_session.commit()

    response = client.post(
        f"/api/v1/cycles/{closed_cycle.id}/finalize",
        headers=get_auth_headers(test_manager_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert "finalized successfully" in data["message"].lower()
    assert data["cycle_id"] == str(closed_cycle.id)
