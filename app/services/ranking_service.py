from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app import models
from app.services.audit import record_audit


class RankingService:
    """Ranking and finalization logic."""

    def __init__(self, session: Session):
        self.session = session

    def compute_cycle_rankings(self, cycle_id: UUID) -> list[models.Ranking]:
        cycle = self._get_cycle_or_raise(cycle_id)
        # Fetch nominations and scores
        stmt = (
            select(models.Nomination, models.NominationCriteriaScore, models.Criteria)
            .join(models.NominationCriteriaScore, models.NominationCriteriaScore.nomination_id == models.Nomination.id)
            .join(models.Criteria, models.Criteria.id == models.NominationCriteriaScore.criteria_id)
            .where(models.Nomination.cycle_id == cycle_id, models.Nomination.status == models.NominationStatus.APPROVED)
        )
        rows = self.session.execute(stmt).all()
        scores_by_nomination: dict[UUID, Decimal] = {}
        team_by_nomination: dict[UUID, UUID | None] = {}
        nominee_by_nomination: dict[UUID, UUID] = {}
        for nomination, score_row, crit in rows:
            weighted = Decimal(score_row.score) * Decimal(crit.weight)
            scores_by_nomination[nomination.id] = scores_by_nomination.get(nomination.id, Decimal("0")) + weighted
            team_by_nomination[nomination.id] = nomination.team_id
            nominee_by_nomination[nomination.id] = nomination.nominee_user_id

        # Clear existing rankings for the cycle
        self.session.execute(delete(models.Ranking).where(models.Ranking.cycle_id == cycle_id))

        # Sort and assign ranks (dense rank)
        ranking_items: list[tuple[UUID, Decimal]] = sorted(
            scores_by_nomination.items(), key=lambda kv: kv[1], reverse=True
        )
        rankings: list[models.Ranking] = []
        current_rank = 0
        last_score: Decimal | None = None
        for idx, (nomination_id, total_score) in enumerate(ranking_items, start=1):
            if last_score is None or total_score < last_score:
                current_rank = idx
                last_score = total_score
            ranking = models.Ranking(
                cycle_id=cycle_id,
                team_id=team_by_nomination[nomination_id],
                nominee_user_id=nominee_by_nomination[nomination_id],
                total_score=total_score,
                rank=current_rank,
                computed_at=datetime.now(timezone.utc),
            )
            self.session.add(ranking)
            rankings.append(ranking)

        self.session.flush()
        record_audit(
            self.session, None, "ranking.compute", "NominationCycle", cycle_id, {"ranking_count": len(rankings)}
        )
        return rankings

    def finalize_cycle(self, cycle_id: UUID) -> None:
        cycle = self._get_cycle_or_raise(cycle_id)
        if cycle.status != models.CycleStatus.CLOSED:
            raise ValueError("Cycle must be CLOSED before finalization")

        rankings = self.compute_cycle_rankings(cycle_id)

        # Snapshot nominations to history
        nominations = self.session.scalars(
            select(models.Nomination).where(models.Nomination.cycle_id == cycle_id)
        ).all()
        for nom in nominations:
            hist = models.NominationHistory(
                source_nomination_id=nom.id,
                cycle_id=nom.cycle_id,
                nominee_user_id=nom.nominee_user_id,
                team_id=nom.team_id,
                submitted_by=nom.submitted_by,
                submitted_at=nom.submitted_at,
                status=nom.status.value if hasattr(nom.status, "value") else str(nom.status),
                payload=None,
            )
            self.session.add(hist)

        for r in rankings:
            rh = models.RankingHistory(
                source_ranking_id=r.id,
                cycle_id=r.cycle_id,
                team_id=r.team_id,
                nominee_user_id=r.nominee_user_id,
                total_score=r.total_score,
                rank=r.rank,
                computed_at=r.computed_at,
            )
            self.session.add(rh)

        cycle.status = models.CycleStatus.FINALIZED
        self.session.flush()
        record_audit(self.session, None, "cycle.finalize", "NominationCycle", cycle_id, {"rankings": len(rankings)})

    def _get_cycle_or_raise(self, cycle_id: UUID) -> models.NominationCycle:
        cycle = self.session.get(models.NominationCycle, cycle_id)
        if not cycle:
            raise ValueError("Cycle not found")
        return cycle
