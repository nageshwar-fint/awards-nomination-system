"""Tests for flexible criteria system with configurable question types."""
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app import models
from app.models.domain import (
    User, UserRole, NominationCycle, CycleStatus, Criteria,
    Nomination, NominationStatus, NominationCriteriaScore
)


def test_create_criteria_with_text_config(client: TestClient, db_session, test_cycle, get_auth_headers, test_hr_user):
    """Test creating criteria with text question type."""
    headers = get_auth_headers(test_hr_user)
    
    criteria_data = [{
        "name": "Leadership Qualities",
        "weight": 0.3,
        "description": "Describe leadership qualities",
        "config": {
            "type": "text",
            "required": True
        }
    }]
    
    response = client.post(
        f"/api/v1/cycles/{test_cycle.id}/criteria",
        json=criteria_data,
        headers=headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Leadership Qualities"
    assert data[0]["config"]["type"] == "text"
    assert data[0]["config"]["required"] is True
    
    # Verify in database
    criteria = db_session.query(Criteria).filter(Criteria.cycle_id == test_cycle.id).first()
    assert criteria is not None
    assert criteria.config["type"] == "text"
    assert criteria.config["required"] is True


def test_create_criteria_with_single_select_config(client: TestClient, db_session, test_cycle, get_auth_headers, test_hr_user):
    """Test creating criteria with single select question type."""
    headers = get_auth_headers(test_hr_user)
    
    criteria_data = [{
        "name": "Performance Rating",
        "weight": 0.4,
        "description": "Select performance level",
        "config": {
            "type": "single_select",
            "required": True,
            "options": ["Excellent", "Good", "Average", "Needs Improvement"]
        }
    }]
    
    response = client.post(
        f"/api/v1/cycles/{test_cycle.id}/criteria",
        json=criteria_data,
        headers=headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data[0]["config"]["type"] == "single_select"
    assert len(data[0]["config"]["options"]) == 4
    assert "Excellent" in data[0]["config"]["options"]


def test_create_criteria_with_multi_select_config(client: TestClient, db_session, test_cycle, get_auth_headers, test_hr_user):
    """Test creating criteria with multi select question type."""
    headers = get_auth_headers(test_hr_user)
    
    criteria_data = [{
        "name": "Technical Skills",
        "weight": 0.3,
        "config": {
            "type": "multi_select",
            "required": True,
            "options": ["Python", "JavaScript", "React", "Docker", "Kubernetes"]
        }
    }]
    
    response = client.post(
        f"/api/v1/cycles/{test_cycle.id}/criteria",
        json=criteria_data,
        headers=headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data[0]["config"]["type"] == "multi_select"
    assert len(data[0]["config"]["options"]) == 5


def test_create_criteria_with_text_image_config(client: TestClient, db_session, test_cycle, get_auth_headers, test_hr_user):
    """Test creating criteria with text with image question type."""
    headers = get_auth_headers(test_hr_user)
    
    criteria_data = [{
        "name": "Achievement Documentation",
        "weight": 0.4,
        "config": {
            "type": "text_with_image",
            "required": False,
            "image_required": False
        }
    }]
    
    response = client.post(
        f"/api/v1/cycles/{test_cycle.id}/criteria",
        json=criteria_data,
        headers=headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data[0]["config"]["type"] == "text_with_image"
    assert data[0]["config"]["image_required"] is False


def test_submit_nomination_with_text_answer(client: TestClient, db_session, test_cycle, test_employee_user, get_auth_headers, test_team_lead_user):
    """Test submitting nomination with text answer."""
    headers = get_auth_headers(test_team_lead_user)
    
    # Create criteria with text config
    criteria = Criteria(
        id=uuid4(),
        cycle_id=test_cycle.id,
        name="Leadership",
        weight=0.5,
        config={"type": "text", "required": True},
        is_active=True
    )
    db_session.add(criteria)
    db_session.commit()
    
    nomination_data = {
        "cycle_id": str(test_cycle.id),
        "nominee_user_id": str(test_employee_user.id),
        "scores": [{
            "criteria_id": str(criteria.id),
            "answer": {
                "text": "The nominee demonstrates excellent leadership skills..."
            }
        }]
    }
    
    response = client.post(
        "/api/v1/nominations",
        json=nomination_data,
        headers=headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["nominee_user_id"] == str(test_employee_user.id)
    
    # Get the actual nomination
    nomination = db_session.query(Nomination).filter(
        Nomination.nominee_user_id == test_employee_user.id,
        Nomination.cycle_id == test_cycle.id
    ).first()
    assert nomination is not None
    
    # Verify answer stored in database
    score = db_session.query(NominationCriteriaScore).filter(
        NominationCriteriaScore.nomination_id == nomination.id
    ).first()
    assert score is not None
    assert score.answer["text"] == "The nominee demonstrates excellent leadership skills..."


def test_submit_nomination_with_single_select_answer(client: TestClient, db_session, test_cycle, test_employee_user, get_auth_headers, test_team_lead_user):
    """Test submitting nomination with single select answer."""
    headers = get_auth_headers(test_team_lead_user)
    
    criteria = Criteria(
        id=uuid4(),
        cycle_id=test_cycle.id,
        name="Performance",
        weight=0.5,
        config={
            "type": "single_select",
            "required": True,
            "options": ["Excellent", "Good", "Average"]
        },
        is_active=True
    )
    db_session.add(criteria)
    db_session.commit()
    
    nomination_data = {
        "cycle_id": str(test_cycle.id),
        "nominee_user_id": str(test_employee_user.id),
        "scores": [{
            "criteria_id": str(criteria.id),
            "answer": {
                "selected": "Excellent"
            }
        }]
    }
    
    response = client.post(
        "/api/v1/nominations",
        json=nomination_data,
        headers=headers
    )
    
    assert response.status_code == 201
    
    # Verify answer
    nomination = db_session.query(Nomination).filter(
        Nomination.nominee_user_id == test_employee_user.id
    ).first()
    score = db_session.query(NominationCriteriaScore).filter(
        NominationCriteriaScore.nomination_id == nomination.id
    ).first()
    assert score.answer["selected"] == "Excellent"


def test_submit_nomination_with_multi_select_answer(client: TestClient, db_session, test_cycle, test_employee_user, get_auth_headers, test_team_lead_user):
    """Test submitting nomination with multi select answer."""
    headers = get_auth_headers(test_team_lead_user)
    
    criteria = Criteria(
        id=uuid4(),
        cycle_id=test_cycle.id,
        name="Skills",
        weight=0.5,
        config={
            "type": "multi_select",
            "required": True,
            "options": ["Python", "JavaScript", "React", "Docker"]
        },
        is_active=True
    )
    db_session.add(criteria)
    db_session.commit()
    
    nomination_data = {
        "cycle_id": str(test_cycle.id),
        "nominee_user_id": str(test_employee_user.id),
        "scores": [{
            "criteria_id": str(criteria.id),
            "answer": {
                "selected_list": ["Python", "React", "Docker"]
            }
        }]
    }
    
    response = client.post(
        "/api/v1/nominations",
        json=nomination_data,
        headers=headers
    )
    
    assert response.status_code == 201
    
    # Verify answer
    nomination = db_session.query(Nomination).filter(
        Nomination.nominee_user_id == test_employee_user.id
    ).first()
    score = db_session.query(NominationCriteriaScore).filter(
        NominationCriteriaScore.nomination_id == nomination.id
    ).first()
    assert "Python" in score.answer["selected_list"]
    assert "React" in score.answer["selected_list"]
    assert len(score.answer["selected_list"]) == 3


def test_submit_nomination_with_text_image_answer(client: TestClient, db_session, test_cycle, test_employee_user, get_auth_headers, test_team_lead_user):
    """Test submitting nomination with text and image answer."""
    headers = get_auth_headers(test_team_lead_user)
    
    criteria = Criteria(
        id=uuid4(),
        cycle_id=test_cycle.id,
        name="Achievement",
        weight=0.5,
        config={
            "type": "text_with_image",
            "required": True,
            "image_required": False
        },
        is_active=True
    )
    db_session.add(criteria)
    db_session.commit()
    
    nomination_data = {
        "cycle_id": str(test_cycle.id),
        "nominee_user_id": str(test_employee_user.id),
        "scores": [{
            "criteria_id": str(criteria.id),
            "answer": {
                "text": "Led the implementation of microservices",
                "image_url": "https://storage.example.com/achievement.jpg"
            }
        }]
    }
    
    response = client.post(
        "/api/v1/nominations",
        json=nomination_data,
        headers=headers
    )
    
    assert response.status_code == 201
    
    # Verify answer
    nomination = db_session.query(Nomination).filter(
        Nomination.nominee_user_id == test_employee_user.id
    ).first()
    score = db_session.query(NominationCriteriaScore).filter(
        NominationCriteriaScore.nomination_id == nomination.id
    ).first()
    assert score.answer["text"] == "Led the implementation of microservices"
    assert score.answer["image_url"] == "https://storage.example.com/achievement.jpg"


def test_submit_nomination_with_mixed_answer_types(client: TestClient, db_session, test_cycle, test_employee_user, get_auth_headers, test_team_lead_user):
    """Test submitting nomination with multiple criteria having different answer types."""
    headers = get_auth_headers(test_team_lead_user)
    
    # Create multiple criteria with different types
    criteria1 = Criteria(
        id=uuid4(),
        cycle_id=test_cycle.id,
        name="Leadership Text",
        weight=0.3,
        config={"type": "text", "required": True},
        is_active=True
    )
    criteria2 = Criteria(
        id=uuid4(),
        cycle_id=test_cycle.id,
        name="Performance Select",
        weight=0.3,
        config={
            "type": "single_select",
            "required": True,
            "options": ["Excellent", "Good"]
        },
        is_active=True
    )
    criteria3 = Criteria(
        id=uuid4(),
        cycle_id=test_cycle.id,
        name="Skills Multi",
        weight=0.4,
        config={
            "type": "multi_select",
            "required": True,
            "options": ["Python", "JavaScript"]
        },
        is_active=True
    )
    db_session.add_all([criteria1, criteria2, criteria3])
    db_session.commit()
    
    nomination_data = {
        "cycle_id": str(test_cycle.id),
        "nominee_user_id": str(test_employee_user.id),
        "scores": [
            {
                "criteria_id": str(criteria1.id),
                "answer": {"text": "Excellent leader"}
            },
            {
                "criteria_id": str(criteria2.id),
                "answer": {"selected": "Excellent"}
            },
            {
                "criteria_id": str(criteria3.id),
                "answer": {"selected_list": ["Python", "JavaScript"]}
            }
        ]
    }
    
    response = client.post(
        "/api/v1/nominations",
        json=nomination_data,
        headers=headers
    )
    
    assert response.status_code == 201
    
    # Verify all answers stored correctly
    nomination = db_session.query(Nomination).filter(
        Nomination.nominee_user_id == test_employee_user.id
    ).first()
    scores = db_session.query(NominationCriteriaScore).filter(
        NominationCriteriaScore.nomination_id == nomination.id
    ).all()
    
    assert len(scores) == 3
    score_dict = {s.criteria_id: s for s in scores}
    assert score_dict[criteria1.id].answer["text"] == "Excellent leader"
    assert score_dict[criteria2.id].answer["selected"] == "Excellent"
    assert len(score_dict[criteria3.id].answer["selected_list"]) == 2


def test_submit_nomination_backward_compatibility_legacy_score(client: TestClient, db_session, test_cycle, test_employee_user, get_auth_headers, test_team_lead_user):
    """Test backward compatibility with legacy numeric score format."""
    headers = get_auth_headers(test_team_lead_user)
    
    criteria = Criteria(
        id=uuid4(),
        cycle_id=test_cycle.id,
        name="Legacy Criteria",
        weight=0.5,
        is_active=True  # No config - legacy criteria
    )
    db_session.add(criteria)
    db_session.commit()
    
    nomination_data = {
        "cycle_id": str(test_cycle.id),
        "nominee_user_id": str(test_employee_user.id),
        "scores": [{
            "criteria_id": str(criteria.id),
            "score": 8,  # Legacy score format
            "comment": "Legacy comment"
        }]
    }
    
    response = client.post(
        "/api/v1/nominations",
        json=nomination_data,
        headers=headers
    )
    
    assert response.status_code == 201
    
    # Verify legacy score stored
    nomination = db_session.query(Nomination).filter(
        Nomination.nominee_user_id == test_employee_user.id
    ).first()
    score = db_session.query(NominationCriteriaScore).filter(
        NominationCriteriaScore.nomination_id == nomination.id
    ).first()
    assert score.score == 8
    assert score.comment == "Legacy comment"


def test_approve_nomination_with_rating(client: TestClient, db_session, test_nomination, get_auth_headers, test_manager_user):
    """Test manager approving nomination with rating."""
    headers = get_auth_headers(test_manager_user)
    
    approval_data = {
        "nomination_id": str(test_nomination.id),
        "reason": "Excellent performance, discussed with team lead",
        "rating": 8.5
    }
    
    response = client.post(
        "/api/v1/approvals/approve",
        json=approval_data,
        headers=headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["action"] == "APPROVE"
    assert data["rating"] == 8.5
    assert data["reason"] == "Excellent performance, discussed with team lead"
    
    # Verify in database
    from app.models.domain import Approval
    approval = db_session.query(Approval).filter(
        Approval.nomination_id == test_nomination.id
    ).first()
    assert approval is not None
    assert approval.rating == 8.5


def test_reject_nomination_with_rating(client: TestClient, db_session, test_nomination, get_auth_headers, test_manager_user):
    """Test manager rejecting nomination with rating."""
    headers = get_auth_headers(test_manager_user)
    
    approval_data = {
        "nomination_id": str(test_nomination.id),
        "reason": "Does not meet criteria",
        "rating": 4.0
    }
    
    response = client.post(
        "/api/v1/approvals/reject",
        json=approval_data,
        headers=headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["action"] == "REJECT"
    assert data["rating"] == 4.0


def test_approve_nomination_without_rating(client: TestClient, db_session, test_nomination, get_auth_headers, test_manager_user):
    """Test manager approving nomination without rating (optional field)."""
    headers = get_auth_headers(test_manager_user)
    
    approval_data = {
        "nomination_id": str(test_nomination.id),
        "reason": "Approved after discussion"
    }
    
    response = client.post(
        "/api/v1/approvals/approve",
        json=approval_data,
        headers=headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["action"] == "APPROVE"
    assert data["rating"] is None


def test_get_criteria_with_config(client: TestClient, db_session, test_cycle, get_auth_headers, test_hr_user):
    """Test retrieving criteria includes config field."""
    headers = get_auth_headers(test_hr_user)
    
    # Create criteria with config
    criteria = Criteria(
        id=uuid4(),
        cycle_id=test_cycle.id,
        name="Test Criteria",
        weight=0.5,
        config={
            "type": "multi_select",
            "required": True,
            "options": ["Option 1", "Option 2"]
        },
        is_active=True
    )
    db_session.add(criteria)
    db_session.commit()
    
    response = client.get(
        f"/api/v1/criteria/{criteria.id}",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["config"] is not None
    assert data["config"]["type"] == "multi_select"
    assert len(data["config"]["options"]) == 2


def test_update_criteria_config(client: TestClient, db_session, test_draft_cycle, get_auth_headers, test_hr_user):
    """Test updating criteria configuration."""
    headers = get_auth_headers(test_hr_user)
    
    # Create criteria
    criteria = Criteria(
        id=uuid4(),
        cycle_id=test_draft_cycle.id,
        name="Test Criteria",
        weight=0.5,
        config={"type": "text", "required": True},
        is_active=True
    )
    db_session.add(criteria)
    db_session.commit()
    
    # Update config
    update_data = {
        "config": {
            "type": "single_select",
            "required": True,
            "options": ["A", "B", "C"]
        }
    }
    
    response = client.patch(
        f"/api/v1/criteria/{criteria.id}",
        json=update_data,
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["config"]["type"] == "single_select"
    assert len(data["config"]["options"]) == 3
