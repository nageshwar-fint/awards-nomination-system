from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import models
from app.services.audit import record_audit


class NominationService:
    """Business logic for cycles, criteria, and nominations."""

    def __init__(self, session: Session):
        self.session = session

    # Cycles
    def create_cycle(self, name: str, start_at: datetime, end_at: datetime, created_by: UUID) -> models.NominationCycle:
        if end_at <= start_at:
            raise ValueError("end_at must be after start_at")
        cycle = models.NominationCycle(name=name, start_at=start_at, end_at=end_at, created_by=created_by)
        self.session.add(cycle)
        self.session.flush()
        record_audit(self.session, created_by, "cycle.create", "NominationCycle", cycle.id, {"name": name})
        return cycle

    def add_criteria_to_cycle(self, cycle_id: UUID, criteria: Iterable[dict]) -> list[models.Criteria]:
        cycle = self._get_cycle_or_raise(cycle_id)
        items: list[models.Criteria] = []
        for item in criteria:
            crit = models.Criteria(
                cycle_id=cycle.id,
                name=item["name"],
                weight=Decimal(str(item["weight"])),
                description=item.get("description"),
                is_active=item.get("is_active", True),
                config=item.get("config"),  # Store config JSON
            )
            self.session.add(crit)
            items.append(crit)
        self.session.flush()
        total_weight = self._criteria_weight_sum(cycle.id)
        if total_weight > Decimal("1.0000"):
            raise ValueError("Criteria weights exceed 1.0 for cycle")
        record_audit(self.session, cycle.created_by, "criteria.add", "NominationCycle", cycle.id, {"count": len(items)})
        return items

    # Nominations
    def submit_nomination(
        self,
        cycle_id: UUID,
        nominee_user_id: UUID,
        submitted_by: UUID,
        scores: list[dict],
    ) -> models.Nomination:
        cycle = self._get_cycle_or_raise(cycle_id)
        now = datetime.now(timezone.utc)
        # Ensure datetimes are timezone-aware for comparison
        start_at = cycle.start_at
        end_at = cycle.end_at
        if start_at.tzinfo is None:
            start_at = start_at.replace(tzinfo=timezone.utc)
        if end_at.tzinfo is None:
            end_at = end_at.replace(tzinfo=timezone.utc)
        if not (start_at <= now <= end_at) or cycle.status != models.CycleStatus.OPEN:
            raise ValueError("Cycle not open for submissions")

        submitter = self._get_user_or_raise(submitted_by)
        if submitter.role not in (models.UserRole.TEAM_LEAD, models.UserRole.MANAGER, models.UserRole.HR):
            raise PermissionError("Only TEAM_LEAD, MANAGER, or HR can submit nominations")

        nominee = self._get_user_or_raise(nominee_user_id)
        nomination = models.Nomination(
            cycle_id=cycle.id,
            nominee_user_id=nominee.id,
            team_id=nominee.team_id,
            submitted_by=submitter.id,
            submitted_at=now,
            status=models.NominationStatus.PENDING,
        )
        self.session.add(nomination)
        self.session.flush()

        criteria_ids = {c.id: c for c in self._get_active_criteria(cycle.id)}
        score_rows: list[models.NominationCriteriaScore] = []
        for score in scores:
            crit_id = UUID(str(score["criteria_id"]))
            if crit_id not in criteria_ids:
                raise ValueError("Criteria not active or not part of cycle")
            
            criteria = criteria_ids[crit_id]
            answer_data = None
            legacy_score = None
            comment = score.get("comment")
            
            # Handle new flexible answer format
            if "answer" in score and score["answer"]:
                answer_dict = score["answer"]
                if isinstance(answer_dict, dict):
                    # Build answer JSON based on criteria config
                    answer_data = {}
                    
                    if "text" in answer_dict:
                        answer_data["text"] = answer_dict["text"]
                    if "selected" in answer_dict:
                        answer_data["selected"] = answer_dict["selected"]
                    if "selected_list" in answer_dict:
                        answer_data["selected_list"] = answer_dict["selected_list"]
                    if "image_url" in answer_dict:
                        answer_data["image_url"] = answer_dict["image_url"]
            
            # Handle legacy score format (backward compatibility)
            if "score" in score and score["score"] is not None:
                legacy_score = int(score["score"])
            
            score_rows.append(
                models.NominationCriteriaScore(
                    nomination_id=nomination.id,
                    criteria_id=crit_id,
                    score=legacy_score,
                    answer=answer_data,
                    comment=comment,
                )
            )
        self.session.add_all(score_rows)

        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise ValueError("Duplicate nomination for this cycle/nominee/submitter") from exc

        record_audit(
            self.session,
            submitted_by,
            "nomination.submit",
            "Nomination",
            nomination.id,
            {"cycle_id": str(cycle.id), "nominee_user_id": str(nominee_user_id)},
        )
        return nomination

    # Helpers
    def _get_cycle_or_raise(self, cycle_id: UUID) -> models.NominationCycle:
        cycle = self.session.get(models.NominationCycle, cycle_id)
        if not cycle:
            raise ValueError("Cycle not found")
        return cycle

    def _get_user_or_raise(self, user_id: UUID) -> models.User:
        user = self.session.get(models.User, user_id)
        if not user:
            raise ValueError("User not found")
        return user

    def _get_active_criteria(self, cycle_id: UUID) -> list[models.Criteria]:
        result = self.session.scalars(
            select(models.Criteria).where(models.Criteria.cycle_id == cycle_id, models.Criteria.is_active.is_(True))
        )
        return list(result)

    def _criteria_weight_sum(self, cycle_id: UUID) -> Decimal:
        crit = self._get_active_criteria(cycle_id)
        total = sum(Decimal(c.weight) for c in crit)
        return total
