"""Tests for criteria endpoints."""
import pytest
from uuid import uuid4
from fastapi.testclient import TestClient


def test_get_cycle_criteria(client: TestClient, test_cycle, test_criteria):
    """Test getting criteria for a cycle."""
    response = client.get(f"/api/v1/cycles/{test_cycle.id}/criteria")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(c["id"] == str(test_criteria.id) for c in data)


def test_get_cycle_criteria_cycle_not_found(client: TestClient):
    """Test getting criteria for non-existent cycle."""
    fake_id = uuid4()
    response = client.get(f"/api/v1/cycles/{fake_id}/criteria")
    assert response.status_code == 404


def test_get_criteria(client: TestClient, test_criteria):
    """Test getting a specific criteria."""
    response = client.get(f"/api/v1/criteria/{test_criteria.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_criteria.id)
    assert data["name"] == test_criteria.name


def test_get_criteria_not_found(client: TestClient):
    """Test getting non-existent criteria."""
    fake_id = uuid4()
    response = client.get(f"/api/v1/criteria/{fake_id}")
    assert response.status_code == 404


def test_add_criteria_unauthorized(client: TestClient, test_cycle):
    """Test adding criteria without authentication."""
    criteria_data = [{
        "name": "Test Criteria",
        "weight": 0.3,
        "description": "Test description",
    }]
    response = client.post(f"/api/v1/cycles/{test_cycle.id}/criteria", json=criteria_data)
    assert response.status_code in (401, 403)


def test_add_criteria_hr_only(client: TestClient, test_draft_cycle, test_hr_user, get_auth_headers):
    """Test that only HR can add criteria."""
    criteria_data = [{
        "name": "New Criteria",
        "weight": 0.3,
        "description": "New criteria description",
        "is_active": True,
    }]
    response = client.post(
        f"/api/v1/cycles/{test_draft_cycle.id}/criteria",
        json=criteria_data,
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "New Criteria"


def test_add_criteria_forbidden_non_hr(client: TestClient, test_draft_cycle, test_team_lead_user, test_manager_user, get_auth_headers):
    """Test that non-HR users cannot add criteria."""
    criteria_data = [{
        "name": "New Criteria",
        "weight": 0.3,
        "description": "New criteria description",
        "is_active": True,
    }]
    
    # Team Lead should be forbidden
    response = client.post(
        f"/api/v1/cycles/{test_draft_cycle.id}/criteria",
        json=criteria_data,
        headers=get_auth_headers(test_team_lead_user),
    )
    assert response.status_code == 403
    
    # Manager should be forbidden
    response = client.post(
        f"/api/v1/cycles/{test_draft_cycle.id}/criteria",
        json=criteria_data,
        headers=get_auth_headers(test_manager_user),
    )
    assert response.status_code == 403


def test_add_criteria_weight_exceeds_one(client: TestClient, test_draft_cycle, test_hr_user, get_auth_headers):
    """Test adding criteria that exceeds total weight of 1.0."""
    criteria_data = [{
        "name": "Heavy Criteria",
        "weight": 1.5,  # Exceeds 1.0
    }]
    response = client.post(
        f"/api/v1/cycles/{test_draft_cycle.id}/criteria",
        json=criteria_data,
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 400


def test_update_criteria_hr_only(client: TestClient, test_draft_cycle, test_hr_user, get_auth_headers, db_session):
    """Test that only HR can update criteria."""
    from app.models.domain import Criteria
    
    # Create criteria in draft cycle (can update name)
    criteria = Criteria(
        id=uuid4(),
        cycle_id=test_draft_cycle.id,
        name="Test Criteria",
        weight=0.5,
        description="Original description",
        is_active=True,
    )
    db_session.add(criteria)
    db_session.commit()
    
    update_data = {
        "name": "Updated Criteria Name",
        "description": "Updated description",
    }
    response = client.patch(
        f"/api/v1/criteria/{criteria.id}",
        json=update_data,
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Criteria Name"
    assert data["description"] == "Updated description"


def test_update_criteria_forbidden_non_hr(client: TestClient, test_criteria, test_team_lead_user, test_manager_user, get_auth_headers):
    """Test that non-HR users cannot update criteria."""
    update_data = {"name": "Updated Criteria Name"}
    
    # Team Lead should be forbidden
    response = client.patch(
        f"/api/v1/criteria/{test_criteria.id}",
        json=update_data,
        headers=get_auth_headers(test_team_lead_user),
    )
    assert response.status_code == 403
    
    # Manager should be forbidden
    response = client.patch(
        f"/api/v1/criteria/{test_criteria.id}",
        json=update_data,
        headers=get_auth_headers(test_manager_user),
    )
    assert response.status_code == 403


def test_update_criteria_unauthorized(client: TestClient, test_criteria):
    """Test updating criteria without authentication."""
    update_data = {"name": "Updated Name"}
    response = client.patch(f"/api/v1/criteria/{test_criteria.id}", json=update_data)
    assert response.status_code in (401, 403)


def test_delete_criteria_unused_hr_only(client: TestClient, test_draft_cycle, test_hr_user, get_auth_headers, db_session):
    """Test that only HR can delete unused criteria."""
    from app.models.domain import Criteria
    
    # Create a new unused criteria
    unused_criteria = Criteria(
        id=uuid4(),
        cycle_id=test_draft_cycle.id,
        name="Unused Criteria",
        weight=0.2,
        is_active=True,
    )
    db_session.add(unused_criteria)
    db_session.commit()

    response = client.delete(
        f"/api/v1/criteria/{unused_criteria.id}",
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 204

    # Verify it's deleted
    get_response = client.get(f"/api/v1/criteria/{unused_criteria.id}")
    assert get_response.status_code == 404


def test_delete_criteria_forbidden_non_hr(client: TestClient, test_criteria, test_team_lead_user, test_manager_user, get_auth_headers):
    """Test that non-HR users cannot delete criteria."""
    # Team Lead should be forbidden
    response = client.delete(
        f"/api/v1/criteria/{test_criteria.id}",
        headers=get_auth_headers(test_team_lead_user),
    )
    assert response.status_code == 403
    
    # Manager should be forbidden
    response = client.delete(
        f"/api/v1/criteria/{test_criteria.id}",
        headers=get_auth_headers(test_manager_user),
    )
    assert response.status_code == 403


def test_delete_criteria_used(client: TestClient, test_criteria, test_nomination, test_hr_user, get_auth_headers):
    """Test deleting criteria that's been used (should fail)."""
    # test_criteria is used by test_nomination fixture - ensure it exists
    # The test_nomination fixture creates NominationCriteriaScore linking to test_criteria
    response = client.delete(
        f"/api/v1/criteria/{test_criteria.id}",
        headers=get_auth_headers(test_hr_user),
    )
    assert response.status_code == 400
    assert "used" in response.json()["error"]["message"].lower()
