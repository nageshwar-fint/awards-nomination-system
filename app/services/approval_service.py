from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app import models
from app.services.audit import record_audit


class ApprovalService:
    """Business logic for approvals and rejections."""

    def __init__(self, session: Session):
        self.session = session

    def approve(
        self, 
        nomination_id: UUID, 
        actor_user_id: UUID, 
        reason: str | None = None, 
        rating: float | None = None,
        criteria_reviews: list[dict] | None = None
    ) -> models.Approval:
        return self._act(nomination_id, actor_user_id, models.ApprovalAction.APPROVE, reason, rating, criteria_reviews)

    def reject(
        self, 
        nomination_id: UUID, 
        actor_user_id: UUID, 
        reason: str | None = None, 
        rating: float | None = None,
        criteria_reviews: list[dict] | None = None
    ) -> models.Approval:
        return self._act(nomination_id, actor_user_id, models.ApprovalAction.REJECT, reason, rating, criteria_reviews)

    def _act(
        self, 
        nomination_id: UUID, 
        actor_user_id: UUID, 
        action: models.ApprovalAction, 
        reason: str | None, 
        rating: float | None = None,
        criteria_reviews: list[dict] | None = None
    ) -> models.Approval:
        from sqlalchemy import select
        from decimal import Decimal
        
        nomination = self.session.get(models.Nomination, nomination_id)
        if not nomination:
            raise ValueError("Nomination not found")
        if nomination.status != models.NominationStatus.PENDING:
            raise ValueError("Nomination already processed")

        actor = self.session.get(models.User, actor_user_id)
        if not actor:
            raise ValueError("Actor not found")
        if actor.role not in (models.UserRole.MANAGER, models.UserRole.HR):
            raise PermissionError("Only MANAGER or HR can act on nominations")
        
        # Conflict check: If a MANAGER submitted the nomination, that same MANAGER cannot approve/reject it
        # HR can always approve/reject regardless of who submitted
        submitter = self.session.get(models.User, nomination.submitted_by)
        if submitter and actor.role == models.UserRole.MANAGER and submitter.role == models.UserRole.MANAGER:
            if actor.id == submitter.id:
                raise PermissionError("A manager cannot approve or reject their own nomination. Another manager or HR must review it.")

        # If criteria_reviews are provided, calculate total rating from them
        calculated_rating = None
        if criteria_reviews:
            # Get all criteria for the nomination's cycle
            criteria_map = {}
            criteria_list = self.session.scalars(
                select(models.Criteria).where(models.Criteria.cycle_id == nomination.cycle_id)
            ).all()
            for crit in criteria_list:
                criteria_map[crit.id] = crit
            
            # Calculate weighted total rating
            total_weighted_rating = Decimal("0")
            total_weight = Decimal("0")
            
            for review in criteria_reviews:
                crit_id = UUID(str(review["criteria_id"]))
                if crit_id not in criteria_map:
                    raise ValueError(f"Criteria {crit_id} not found in cycle")
                
                criteria = criteria_map[crit_id]
                review_rating = Decimal(str(review["rating"]))
                criteria_weight = Decimal(str(criteria.weight))
                
                # Validate rating is within criterion weight
                if review_rating < 0 or review_rating > criteria_weight:
                    raise ValueError(f"Rating for criterion '{criteria.name}' must be between 0 and {criteria.weight}")
                
                total_weighted_rating += review_rating
                total_weight += criteria_weight
            
            # Calculate overall rating (scale to 0-10)
            if total_weight > 0:
                calculated_rating = float((total_weighted_rating / total_weight) * Decimal("10"))
            else:
                calculated_rating = 0.0
            
            # Use calculated rating if no explicit rating provided
            if rating is None:
                rating = calculated_rating

        approval = models.Approval(
            nomination_id=nomination.id,
            actor_user_id=actor.id,
            action=action,
            reason=reason,
            rating=rating or calculated_rating,
            acted_at=datetime.now(timezone.utc),
        )
        self.session.add(approval)
        self.session.flush()  # Flush to get approval.id
        
        # Save per-criterion reviews if provided
        if criteria_reviews:
            for review in criteria_reviews:
                criteria_review = models.ApprovalCriteriaReview(
                    approval_id=approval.id,
                    criteria_id=UUID(str(review["criteria_id"])),
                    rating=float(review["rating"]),
                    comment=review.get("comment")
                )
                self.session.add(criteria_review)
        
        nomination.status = (
            models.NominationStatus.APPROVED if action == models.ApprovalAction.APPROVE else models.NominationStatus.REJECTED
        )
        self.session.flush()

        record_audit(
            self.session,
            actor_user_id,
            f"nomination.{action.value.lower()}",
            "Nomination",
            nomination.id,
            {"reason": reason, "rating": rating, "criteria_reviews_count": len(criteria_reviews) if criteria_reviews else 0},
        )
        return approval
