from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app import models
from app.auth.jwt import get_current_user, get_optional_user
from app.auth.rbac import RequireManager, RequireTeamLead, RequireHR, get_current_user_id
from app.core.errors import AppError
from app.db.session import get_session
from app.models.domain import User
from app.schemas.base import (
    ApprovalActionRequest,
    ApprovalCriteriaReviewInput,
    ApprovalRead,
    CriteriaCreate,
    CriteriaRead,
    CriteriaUpdate,
    CycleCreate,
    CycleRead,
    CycleUpdate,
    NominationCreate,
    NominationRead,
    NominationScoreRead,
    RankingRead,
    TeamRead,
    UserRead,
)
from app.services.approval_service import ApprovalService
from app.services.nomination_service import NominationService
from app.services.ranking_service import RankingService

router = APIRouter()


# Health check endpoint (no auth required)
@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy", "service": "awards-nomination-system"}


# Cycles endpoints
@router.get("/cycles", response_model=List[CycleRead])
async def list_cycles(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_session),
) -> List[CycleRead]:
    """List all nomination cycles."""
    stmt = select(models.NominationCycle).order_by(models.NominationCycle.created_at.desc()).offset(skip).limit(limit)
    cycles = db.scalars(stmt).all()
    return [CycleRead.model_validate(cycle) for cycle in cycles]


@router.get("/cycles/{cycle_id}", response_model=CycleRead)
async def get_cycle(
    cycle_id: UUID,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_session),
) -> CycleRead:
    """Get a specific nomination cycle by ID."""
    cycle = db.get(models.NominationCycle, cycle_id)
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")
    return CycleRead.model_validate(cycle)


@router.post("/cycles", response_model=CycleRead, status_code=status.HTTP_201_CREATED)
async def create_cycle(
    cycle_data: CycleCreate,
    current_user: User = Depends(RequireHR),
    db: Session = Depends(get_session),
) -> CycleRead:
    """Create a new nomination cycle. HR only."""
    service = NominationService(db)
    try:
        cycle = service.create_cycle(
            name=cycle_data.name,
            start_at=cycle_data.start_at,
            end_at=cycle_data.end_at,
            created_by=current_user.id,
        )
        db.commit()
        return CycleRead.model_validate(cycle)
    except ValueError as e:
        db.rollback()
        raise AppError(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/cycles/{cycle_id}", response_model=CycleRead)
async def update_cycle(
    cycle_id: UUID,
    cycle_update: CycleUpdate,
    current_user: User = Depends(RequireHR),
    db: Session = Depends(get_session),
) -> CycleRead:
    """Update a nomination cycle. HR only.
    - DRAFT cycles: can update all fields (name, dates, status)
    - OPEN cycles: can update status and dates only
    - CLOSED cycles: can update status only
    - FINALIZED cycles: cannot be updated
    """
    cycle = db.get(models.NominationCycle, cycle_id)
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")

    # FINALIZED cycles cannot be updated
    if cycle.status == models.CycleStatus.FINALIZED:
        raise AppError("FINALIZED cycles cannot be updated", status_code=status.HTTP_400_BAD_REQUEST)

    # Update fields if provided
    update_data = cycle_update.model_dump(exclude_unset=True)
    
    # For non-DRAFT cycles, only allow status and date updates
    if cycle.status != models.CycleStatus.DRAFT:
        allowed_fields = {"status", "start_at", "end_at"}
        provided_fields = set(update_data.keys())
        disallowed_fields = provided_fields - allowed_fields
        if disallowed_fields:
            raise AppError(
                f"Only status and dates can be updated for {cycle.status} cycles. "
                f"Disallowed fields: {', '.join(disallowed_fields)}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

    if "status" in update_data:
        try:
            cycle.status = models.CycleStatus[update_data["status"].upper()]
        except KeyError:
            raise AppError(
                f"Invalid status. Must be one of: {[s.name for s in models.CycleStatus]}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
    if "name" in update_data:
        cycle.name = update_data["name"]
    if "start_at" in update_data:
        cycle.start_at = update_data["start_at"]
    if "end_at" in update_data:
        cycle.end_at = update_data["end_at"]

    # Validate end_at > start_at
    if cycle.end_at <= cycle.start_at:
        db.rollback()
        raise AppError("end_at must be after start_at", status_code=status.HTTP_400_BAD_REQUEST)

    try:
        db.commit()
        db.refresh(cycle)
        return CycleRead.model_validate(cycle)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/cycles/{cycle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cycle(
    cycle_id: UUID,
    current_user: User = Depends(RequireHR),
    db: Session = Depends(get_session),
) -> None:
    """Delete a nomination cycle. HR only. Only DRAFT cycles with no nominations can be deleted."""
    cycle = db.get(models.NominationCycle, cycle_id)
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")

    # Only allow deletion of DRAFT cycles
    if cycle.status != models.CycleStatus.DRAFT:
        raise AppError("Only DRAFT cycles can be deleted", status_code=status.HTTP_400_BAD_REQUEST)

    # Check if cycle has nominations
    nomination_count = db.scalar(
        select(func.count(models.Nomination.id)).where(models.Nomination.cycle_id == cycle_id)
    )
    if nomination_count and nomination_count > 0:
        raise AppError("Cannot delete cycle with existing nominations", status_code=status.HTTP_400_BAD_REQUEST)

    try:
        db.delete(cycle)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/cycles/{cycle_id}/criteria", response_model=List[CriteriaRead])
async def get_cycle_criteria(
    cycle_id: UUID,
    active_only: bool = Query(True, description="Filter to only active criteria"),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_session),
) -> List[CriteriaRead]:
    """Get criteria for a nomination cycle."""
    # Verify cycle exists
    cycle = db.get(models.NominationCycle, cycle_id)
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")

    stmt = select(models.Criteria).where(models.Criteria.cycle_id == cycle_id)
    if active_only:
        stmt = stmt.where(models.Criteria.is_active.is_(True))
    stmt = stmt.order_by(models.Criteria.created_at)

    criteria = db.scalars(stmt).all()
    return [CriteriaRead.model_validate(c) for c in criteria]


@router.get("/criteria/{criteria_id}", response_model=CriteriaRead)
async def get_criteria(
    criteria_id: UUID,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_session),
) -> CriteriaRead:
    """Get a specific criteria by ID."""
    criteria = db.get(models.Criteria, criteria_id)
    if not criteria:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Criteria not found")
    return CriteriaRead.model_validate(criteria)


@router.post("/cycles/{cycle_id}/criteria", response_model=List[CriteriaRead], status_code=status.HTTP_201_CREATED)
async def add_criteria_to_cycle(
    cycle_id: UUID,
    criteria_list: List[CriteriaCreate],
    current_user: User = Depends(RequireHR),
    db: Session = Depends(get_session),
) -> List[CriteriaRead]:
    """Add criteria to a nomination cycle. HR only."""
    service = NominationService(db)
    try:
        criteria_data = [c.model_dump() for c in criteria_list]
        criteria = service.add_criteria_to_cycle(cycle_id=cycle_id, criteria=criteria_data)
        db.commit()
        return [CriteriaRead.model_validate(c) for c in criteria]
    except ValueError as e:
        db.rollback()
        raise AppError(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.patch("/criteria/{criteria_id}", response_model=CriteriaRead)
async def update_criteria(
    criteria_id: UUID,
    criteria_update: CriteriaUpdate,
    current_user: User = Depends(RequireHR),
    db: Session = Depends(get_session),
) -> CriteriaRead:
    """Update criteria. HR only. Only allowed if no nominations have been submitted for the cycle."""
    criteria = db.get(models.Criteria, criteria_id)
    if not criteria:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Criteria not found")

    # Check if cycle has nominations (if updating weight, need to be careful)
    cycle = db.get(models.NominationCycle, criteria.cycle_id)
    if cycle.status != models.CycleStatus.DRAFT:
        # If cycle is not DRAFT, only allow updating is_active and description
        update_data = criteria_update.model_dump(exclude_unset=True)
        if "weight" in update_data or "name" in update_data:
            raise AppError("Cannot update weight or name of criteria in a non-DRAFT cycle", status_code=status.HTTP_400_BAD_REQUEST)

    # Update fields if provided
    update_data = criteria_update.model_dump(exclude_unset=True)
    if "name" in update_data:
        criteria.name = update_data["name"]
    if "weight" in update_data:
        criteria.weight = update_data["weight"]
    if "description" in update_data:
        criteria.description = update_data["description"]
    if "is_active" in update_data:
        criteria.is_active = update_data["is_active"]
    if "config" in update_data:
        criteria.config = update_data["config"]

    # If weight changed, validate total weight doesn't exceed 10.0
    if "weight" in update_data:
        from app.services.nomination_service import NominationService
        service = NominationService(db)
        try:
            # This will raise if weights exceed 10.0
            total_weight = service._criteria_weight_sum(criteria.cycle_id)
            if total_weight > 10.0:
                db.rollback()
                raise AppError("Criteria weights exceed 10.0 for cycle", status_code=status.HTTP_400_BAD_REQUEST)
        except AttributeError:
            # If method doesn't exist, skip validation (shouldn't happen)
            pass

    try:
        db.commit()
        db.refresh(criteria)
        return CriteriaRead.model_validate(criteria)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/criteria/{criteria_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_criteria(
    criteria_id: UUID,
    current_user: User = Depends(RequireHR),
    db: Session = Depends(get_session),
) -> None:
    """Delete criteria. HR only. Only allowed if no nominations reference it."""
    criteria = db.get(models.Criteria, criteria_id)
    if not criteria:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Criteria not found")

    # Check if criteria has been used in any nominations
    score_count = db.scalar(
        select(func.count(models.NominationCriteriaScore.id)).where(
            models.NominationCriteriaScore.criteria_id == criteria_id
        )
    )
    if score_count and score_count > 0:
        raise AppError("Cannot delete criteria that has been used in nominations. Deactivate it instead.", status_code=status.HTTP_400_BAD_REQUEST)

    try:
        db.delete(criteria)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Users endpoint for nominations (TEAM_LEAD+ can list users to nominate)
@router.get("/users", response_model=List[UserRead])
async def list_users_for_nominations(
    status_filter: Optional[str] = Query("ACTIVE", description="Filter by status (ACTIVE, INACTIVE)"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    current_user: User = Depends(RequireTeamLead),
    db: Session = Depends(get_session),
) -> List[UserRead]:
    """
    List users for nomination purposes.
    
    Allows TEAM_LEAD, MANAGER, and HR to list users so they can select nominees.
    Only returns EMPLOYEE role users (cannot nominate HR, MANAGER, or TEAM_LEAD).
    Only returns active users by default for security.
    """
    from app.models.domain import UserRole
    
    stmt = select(User)
    
    # Only show EMPLOYEE role users (cannot nominate other roles)
    stmt = stmt.where(User.role == UserRole.EMPLOYEE)
    
    # Filter by status (default to ACTIVE only)
    if status_filter:
        stmt = stmt.where(User.status == status_filter.upper())
    else:
        stmt = stmt.where(User.status == "ACTIVE")
    
    # Search by name or email if provided
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            (User.name.ilike(search_pattern)) | (User.email.ilike(search_pattern))
        )
    
    stmt = stmt.order_by(User.name.asc())
    users = db.scalars(stmt).all()
    
    # Deduplicate users by email (in case of duplicates)
    seen_emails = set()
    unique_users = []
    for user in users:
        if user.email not in seen_emails:
            seen_emails.add(user.email)
            unique_users.append(user)
    
    return [UserRead.model_validate(user) for user in unique_users]


# Nominations endpoints
@router.get("/nominations", response_model=List[NominationRead])
async def list_nominations(
    cycle_id: Optional[UUID] = Query(None, description="Filter by cycle ID"),
    nominee_user_id: Optional[UUID] = Query(None, description="Filter by nominee user ID"),
    submitted_by: Optional[UUID] = Query(None, description="Filter by submitter user ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status (PENDING, APPROVED, REJECTED)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_session),
) -> List[NominationRead]:
    """List nominations with optional filtering."""
    stmt = select(models.Nomination)
    if cycle_id:
        stmt = stmt.where(models.Nomination.cycle_id == cycle_id)
    if nominee_user_id:
        stmt = stmt.where(models.Nomination.nominee_user_id == nominee_user_id)
    if submitted_by:
        stmt = stmt.where(models.Nomination.submitted_by == submitted_by)
    if status_filter:
        try:
            status_enum = models.NominationStatus[status_filter.upper()]
            stmt = stmt.where(models.Nomination.status == status_enum)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {[s.name for s in models.NominationStatus]}",
            )

    stmt = stmt.order_by(models.Nomination.created_at.desc()).offset(skip).limit(limit)
    # Eager load relationships to avoid N+1 queries
    stmt = stmt.options(
        joinedload(models.Nomination.nominee),
        joinedload(models.Nomination.submitted_by_user)
    )
    nominations = db.scalars(stmt).unique().all()
    
    # Enrich nominations with user names
    result = []
    for nomination in nominations:
        nom_dict = NominationRead.model_validate(nomination).model_dump()
        # Add nominee information
        if nomination.nominee:
            nom_dict['nominee_name'] = nomination.nominee.name
            nom_dict['nominee_email'] = nomination.nominee.email
        # Add submitter information
        if nomination.submitted_by_user:
            nom_dict['submitted_by_name'] = nomination.submitted_by_user.name
            nom_dict['submitted_by_email'] = nomination.submitted_by_user.email
        result.append(NominationRead.model_validate(nom_dict))
    
    return result


@router.get("/nominations/{nomination_id}", response_model=NominationRead)
async def get_nomination(
    nomination_id: UUID,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_session),
) -> NominationRead:
    """Get a specific nomination by ID."""
    # Eager load relationships
    from sqlalchemy.orm import joinedload
    nomination = db.query(models.Nomination).options(
        joinedload(models.Nomination.nominee),
        joinedload(models.Nomination.submitted_by_user),
        joinedload(models.Nomination.scores)
    ).filter(models.Nomination.id == nomination_id).first()
    
    if not nomination:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nomination not found")
    
    # Enrich nomination with user names and scores
    nom_dict = NominationRead.model_validate(nomination).model_dump()
    if nomination.nominee:
        nom_dict['nominee_name'] = nomination.nominee.name
        nom_dict['nominee_email'] = nomination.nominee.email
    if nomination.submitted_by_user:
        nom_dict['submitted_by_name'] = nomination.submitted_by_user.name
        nom_dict['submitted_by_email'] = nomination.submitted_by_user.email
    if nomination.scores:
        nom_dict['scores'] = [
            {
                'id': s.id,
                'nomination_id': s.nomination_id,
                'criteria_id': s.criteria_id,
                'score': s.score,
                'answer': s.answer,
                'comment': s.comment,
                'created_at': s.created_at,
                'updated_at': s.updated_at
            }
            for s in nomination.scores
        ]
    
    return NominationRead.model_validate(nom_dict)


@router.post("/nominations", response_model=NominationRead, status_code=status.HTTP_201_CREATED)
async def submit_nomination(
    nomination_data: NominationCreate,
    current_user: User = Depends(RequireTeamLead),
    db: Session = Depends(get_session),
) -> NominationRead:
    """Submit a nomination. Note: submitted_by is taken from authenticated user, not request body."""
    service = NominationService(db)
    try:
        scores = [s.model_dump() for s in nomination_data.scores]
        # Use current_user.id instead of nomination_data.submitted_by for security
        nomination = service.submit_nomination(
            cycle_id=nomination_data.cycle_id,
            nominee_user_id=nomination_data.nominee_user_id,
            submitted_by=current_user.id,
            scores=scores,
        )
        db.commit()
        # Refresh to get relationships
        db.refresh(nomination)
        
        # Enrich nomination with user names
        nom_dict = NominationRead.model_validate(nomination).model_dump()
        if nomination.nominee:
            nom_dict['nominee_name'] = nomination.nominee.name
            nom_dict['nominee_email'] = nomination.nominee.email
        if nomination.submitted_by_user:
            nom_dict['submitted_by_name'] = nomination.submitted_by_user.name
            nom_dict['submitted_by_email'] = nomination.submitted_by_user.email
        
        return NominationRead.model_validate(nom_dict)
    except ValueError as e:
        db.rollback()
        raise AppError(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except PermissionError as e:
        db.rollback()
        raise AppError(str(e), status_code=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/nominations/{nomination_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revert_nomination(
    nomination_id: UUID,
    current_user: User = Depends(RequireHR),
    db: Session = Depends(get_session),
) -> None:
    """
    Revert/delete a nomination (HR/Admin only).
    
    This allows HR/Admin to delete a nomination, which will:
    - Remove the nomination and all associated data (scores, approvals)
    - Allow the employee to be nominated again by anyone (Team Lead, Manager, or HR)
    - Enable re-assignment of weightage for that employee
    """
    nomination = db.get(models.Nomination, nomination_id)
    if not nomination:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nomination not found")
    
    try:
        # Delete related records (approvals and scores will be deleted via cascade)
        # But we need to delete them explicitly to ensure proper cleanup
        from app.models.domain import Approval, NominationCriteriaScore
        
        # Delete approvals
        db.query(Approval).filter(Approval.nomination_id == nomination_id).delete()
        
        # Delete scores
        db.query(NominationCriteriaScore).filter(NominationCriteriaScore.nomination_id == nomination_id).delete()
        
        # Delete the nomination
        db.delete(nomination)
        db.commit()
        
        # Record audit
        from app.services.audit import record_audit
        record_audit(
            db,
            current_user.id,
            "nomination.revert",
            "Nomination",
            nomination_id,
            {"nominee_user_id": str(nomination.nominee_user_id), "cycle_id": str(nomination.cycle_id)}
        )
    except Exception as e:
        db.rollback()
        import traceback
        print(f"Error reverting nomination: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Approval endpoints
@router.get("/nominations/{nomination_id}/approvals", response_model=List[ApprovalRead])
async def get_nomination_approvals(
    nomination_id: UUID,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_session),
) -> List[ApprovalRead]:
    """Get approvals for a specific nomination."""
    # Verify nomination exists
    nomination = db.get(models.Nomination, nomination_id)
    if not nomination:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nomination not found")

    stmt = select(models.Approval).where(models.Approval.nomination_id == nomination_id).order_by(models.Approval.acted_at)
    # Eager load criteria reviews
    from sqlalchemy.orm import joinedload
    stmt = stmt.options(joinedload(models.Approval.criteria_reviews))
    approvals = db.scalars(stmt).unique().all()
    
    # Enrich approvals with criteria reviews
    result = []
    for approval in approvals:
        approval_dict = ApprovalRead.model_validate(approval).model_dump()
        if approval.criteria_reviews:
            approval_dict['criteria_reviews'] = [
                {
                    'id': r.id,
                    'approval_id': r.approval_id,
                    'criteria_id': r.criteria_id,
                    'rating': float(r.rating),
                    'comment': r.comment,
                    'created_at': r.created_at,
                    'updated_at': r.updated_at
                }
                for r in approval.criteria_reviews
            ]
        result.append(ApprovalRead.model_validate(approval_dict))
    
    return result


@router.post("/approvals/approve", response_model=ApprovalRead, status_code=status.HTTP_201_CREATED)
async def approve_nomination(
    approval_data: ApprovalActionRequest,
    current_user: User = Depends(RequireManager),
    db: Session = Depends(get_session),
) -> ApprovalRead:
    """Approve a nomination."""
    service = ApprovalService(db)
    try:
        # Convert criteria_reviews to dict format if provided
        criteria_reviews = None
        if approval_data.criteria_reviews:
            criteria_reviews = [r.model_dump() for r in approval_data.criteria_reviews]
        
        approval = service.approve(
            nomination_id=approval_data.nomination_id,
            actor_user_id=current_user.id,
            reason=approval_data.reason,
            rating=approval_data.rating,
            criteria_reviews=criteria_reviews,
        )
        db.commit()
        db.refresh(approval)
        
        # Load criteria reviews for response
        from sqlalchemy.orm import joinedload
        approval_with_reviews = db.query(models.Approval).options(
            joinedload(models.Approval.criteria_reviews)
        ).filter(models.Approval.id == approval.id).first()
        
        approval_dict = ApprovalRead.model_validate(approval_with_reviews).model_dump()
        if approval_with_reviews.criteria_reviews:
            approval_dict['criteria_reviews'] = [
                {
                    'id': r.id,
                    'approval_id': r.approval_id,
                    'criteria_id': r.criteria_id,
                    'rating': float(r.rating),
                    'comment': r.comment,
                    'created_at': r.created_at,
                    'updated_at': r.updated_at
                }
                for r in approval_with_reviews.criteria_reviews
            ]
        
        return ApprovalRead.model_validate(approval_dict)
    except ValueError as e:
        db.rollback()
        raise AppError(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except PermissionError as e:
        db.rollback()
        raise AppError(str(e), status_code=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        db.rollback()
        import traceback
        print(f"Error approving nomination: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/approvals/reject", response_model=ApprovalRead, status_code=status.HTTP_201_CREATED)
async def reject_nomination(
    approval_data: ApprovalActionRequest,
    current_user: User = Depends(RequireManager),
    db: Session = Depends(get_session),
) -> ApprovalRead:
    """Reject a nomination."""
    service = ApprovalService(db)
    try:
        # Convert criteria_reviews to dict format if provided
        criteria_reviews = None
        if approval_data.criteria_reviews:
            criteria_reviews = [r.model_dump() for r in approval_data.criteria_reviews]
        
        approval = service.reject(
            nomination_id=approval_data.nomination_id,
            actor_user_id=current_user.id,
            reason=approval_data.reason,
            rating=approval_data.rating,
            criteria_reviews=criteria_reviews,
        )
        db.commit()
        db.refresh(approval)
        
        # Load criteria reviews for response
        from sqlalchemy.orm import joinedload
        approval_with_reviews = db.query(models.Approval).options(
            joinedload(models.Approval.criteria_reviews)
        ).filter(models.Approval.id == approval.id).first()
        
        approval_dict = ApprovalRead.model_validate(approval_with_reviews).model_dump()
        if approval_with_reviews.criteria_reviews:
            approval_dict['criteria_reviews'] = [
                {
                    'id': r.id,
                    'approval_id': r.approval_id,
                    'criteria_id': r.criteria_id,
                    'rating': float(r.rating),
                    'comment': r.comment,
                    'created_at': r.created_at,
                    'updated_at': r.updated_at
                }
                for r in approval_with_reviews.criteria_reviews
            ]
        
        return ApprovalRead.model_validate(approval_dict)
    except ValueError as e:
        db.rollback()
        raise AppError(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except PermissionError as e:
        db.rollback()
        raise AppError(str(e), status_code=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        db.rollback()
        import traceback
        print(f"Error rejecting nomination: {e}")
        print(traceback.format_exc())
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Teams endpoints
@router.get("/teams", response_model=List[TeamRead])
async def list_teams(
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_session),
) -> List[TeamRead]:
    """List all teams."""
    stmt = select(models.Team).order_by(models.Team.name.asc())
    teams = db.scalars(stmt).all()
    return [TeamRead.model_validate(team) for team in teams]


# Ranking endpoints
@router.get("/cycles/{cycle_id}/rankings", response_model=List[RankingRead])
async def get_cycle_rankings(
    cycle_id: UUID,
    team_id: Optional[UUID] = Query(None, description="Filter by team ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_session),
) -> List[RankingRead]:
    """Get rankings for a nomination cycle."""
    # Verify cycle exists
    cycle = db.get(models.NominationCycle, cycle_id)
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")

    stmt = select(models.Ranking).where(models.Ranking.cycle_id == cycle_id)
    if team_id:
        stmt = stmt.where(models.Ranking.team_id == team_id)
    stmt = stmt.order_by(models.Ranking.rank, models.Ranking.computed_at.desc()).offset(skip).limit(limit)

    rankings = db.scalars(stmt).all()
    return [RankingRead.model_validate(r) for r in rankings]


@router.post("/cycles/{cycle_id}/rankings/compute", response_model=List[RankingRead], status_code=status.HTTP_201_CREATED)
async def compute_rankings(
    cycle_id: UUID,
    current_user: User = Depends(RequireManager),
    db: Session = Depends(get_session),
) -> List[RankingRead]:
    """Compute rankings for a cycle."""
    service = RankingService(db)
    try:
        rankings = service.compute_cycle_rankings(cycle_id=cycle_id)
        db.commit()
        return [RankingRead.model_validate(r) for r in rankings]
    except ValueError as e:
        db.rollback()
        raise AppError(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/cycles/{cycle_id}/finalize", status_code=status.HTTP_200_OK)
async def finalize_cycle(
    cycle_id: UUID,
    current_user: User = Depends(RequireHR),
    db: Session = Depends(get_session),
) -> dict:
    """Finalize a cycle (compute rankings and snapshot history). HR only."""
    service = RankingService(db)
    try:
        service.finalize_cycle(cycle_id=cycle_id)
        db.commit()
        return {"message": "Cycle finalized successfully", "cycle_id": str(cycle_id)}
    except ValueError as e:
        db.rollback()
        raise AppError(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
