from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app import models
from app.services.audit import record_audit


class ApprovalService:
    """Business logic for approvals and rejections."""

    def __init__(self, session: Session):
        self.session = session

    def approve(self, nomination_id: UUID, actor_user_id: UUID, reason: str | None = None, rating: float | None = None) -> models.Approval:
        return self._act(nomination_id, actor_user_id, models.ApprovalAction.APPROVE, reason, rating)

    def reject(self, nomination_id: UUID, actor_user_id: UUID, reason: str | None = None, rating: float | None = None) -> models.Approval:
        return self._act(nomination_id, actor_user_id, models.ApprovalAction.REJECT, reason, rating)

    def _act(
        self, nomination_id: UUID, actor_user_id: UUID, action: models.ApprovalAction, reason: str | None, rating: float | None = None
    ) -> models.Approval:
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

        approval = models.Approval(
            nomination_id=nomination.id,
            actor_user_id=actor.id,
            action=action,
            reason=reason,
            rating=rating,
            acted_at=datetime.now(timezone.utc),
        )
        self.session.add(approval)
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
            {"reason": reason, "rating": rating},
        )
        return approval
