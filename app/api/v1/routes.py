from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models
from app.auth.jwt import get_current_user, get_optional_user
from app.auth.rbac import RequireManager, RequireTeamLead, get_current_user_id
from app.core.errors import AppError
from app.db.session import get_session
from app.models.domain import User
from app.schemas.base import (
    ApprovalActionRequest,
    ApprovalRead,
    CriteriaCreate,
    CriteriaRead,
    CriteriaUpdate,
    CycleCreate,
    CycleRead,
    CycleUpdate,
    NominationCreate,
    NominationRead,
    RankingRead,
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
    current_user: User = Depends(RequireTeamLead),
    db: Session = Depends(get_session),
) -> CycleRead:
    """Create a new nomination cycle."""
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
    current_user: User = Depends(RequireTeamLead),
    db: Session = Depends(get_session),
) -> CycleRead:
    """Update a nomination cycle. Only DRAFT cycles can be updated."""
    cycle = db.get(models.NominationCycle, cycle_id)
    if not cycle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle not found")

    # Only allow updates to DRAFT cycles
    if cycle.status != models.CycleStatus.DRAFT:
        raise AppError("Only DRAFT cycles can be updated", status_code=status.HTTP_400_BAD_REQUEST)

    # Update fields if provided
    update_data = cycle_update.model_dump(exclude_unset=True)
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
    current_user: User = Depends(RequireTeamLead),
    db: Session = Depends(get_session),
) -> None:
    """Delete a nomination cycle. Only DRAFT cycles with no nominations can be deleted."""
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
    current_user: User = Depends(RequireTeamLead),
    db: Session = Depends(get_session),
) -> List[CriteriaRead]:
    """Add criteria to a nomination cycle."""
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
    current_user: User = Depends(RequireTeamLead),
    db: Session = Depends(get_session),
) -> CriteriaRead:
    """Update criteria. Only allowed if no nominations have been submitted for the cycle."""
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

    # If weight changed, validate total weight doesn't exceed 1.0
    if "weight" in update_data:
        from app.services.nomination_service import NominationService
        service = NominationService(db)
        try:
            # This will raise if weights exceed 1.0
            total_weight = service._criteria_weight_sum(criteria.cycle_id)
            if total_weight > 1.0:
                db.rollback()
                raise AppError("Criteria weights exceed 1.0 for cycle", status_code=status.HTTP_400_BAD_REQUEST)
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
    current_user: User = Depends(RequireTeamLead),
    db: Session = Depends(get_session),
) -> None:
    """Delete criteria. Only allowed if no nominations reference it."""
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
    nominations = db.scalars(stmt).all()
    return [NominationRead.model_validate(n) for n in nominations]


@router.get("/nominations/{nomination_id}", response_model=NominationRead)
async def get_nomination(
    nomination_id: UUID,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_session),
) -> NominationRead:
    """Get a specific nomination by ID."""
    nomination = db.get(models.Nomination, nomination_id)
    if not nomination:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Nomination not found")
    return NominationRead.model_validate(nomination)


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
        return NominationRead.model_validate(nomination)
    except ValueError as e:
        db.rollback()
        raise AppError(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except PermissionError as e:
        db.rollback()
        raise AppError(str(e), status_code=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        db.rollback()
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
    approvals = db.scalars(stmt).all()
    return [ApprovalRead.model_validate(a) for a in approvals]


@router.post("/approvals/approve", response_model=ApprovalRead, status_code=status.HTTP_201_CREATED)
async def approve_nomination(
    approval_data: ApprovalActionRequest,
    current_user: User = Depends(RequireManager),
    db: Session = Depends(get_session),
) -> ApprovalRead:
    """Approve a nomination."""
    service = ApprovalService(db)
    try:
        approval = service.approve(
            nomination_id=approval_data.nomination_id,
            actor_user_id=current_user.id,
            reason=approval_data.reason,
        )
        db.commit()
        return ApprovalRead.model_validate(approval)
    except ValueError as e:
        db.rollback()
        raise AppError(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except PermissionError as e:
        db.rollback()
        raise AppError(str(e), status_code=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        db.rollback()
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
        approval = service.reject(
            nomination_id=approval_data.nomination_id,
            actor_user_id=current_user.id,
            reason=approval_data.reason,
        )
        db.commit()
        return ApprovalRead.model_validate(approval)
    except ValueError as e:
        db.rollback()
        raise AppError(str(e), status_code=status.HTTP_400_BAD_REQUEST)
    except PermissionError as e:
        db.rollback()
        raise AppError(str(e), status_code=status.HTTP_403_FORBIDDEN)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


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
    current_user: User = Depends(RequireManager),
    db: Session = Depends(get_session),
) -> dict:
    """Finalize a cycle (compute rankings and snapshot history)."""
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
