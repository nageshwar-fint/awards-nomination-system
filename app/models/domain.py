import enum
from datetime import datetime
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import TimestampedUUIDBase


class UserRole(str, enum.Enum):
    EMPLOYEE = "EMPLOYEE"
    TEAM_LEAD = "TEAM_LEAD"
    MANAGER = "MANAGER"
    HR = "HR"


class CycleStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    FINALIZED = "FINALIZED"


class NominationStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ApprovalAction(str, enum.Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class Team(TimestampedUUIDBase):
    __tablename__ = "teams"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    members: Mapped[list["User"]] = relationship("User", back_populates="team", foreign_keys="User.team_id")


class User(TimestampedUUIDBase):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)  # Nullable for existing users, required for new registrations
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="ACTIVE")
    profile_picture_url: Mapped[str | None] = mapped_column(String(500), nullable=True)  # URL to profile picture

    team: Mapped[Team | None] = relationship("Team", back_populates="members", foreign_keys=[team_id])
    submissions: Mapped[list["Nomination"]] = relationship(
        "Nomination", back_populates="submitted_by_user", foreign_keys="Nomination.submitted_by"
    )
    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        "PasswordResetToken", back_populates="user", cascade="all, delete-orphan"
    )
    security_questions: Mapped[list["SecurityQuestion"]] = relationship(
        "SecurityQuestion", back_populates="user", cascade="all, delete-orphan"
    )


class NominationCycle(TimestampedUUIDBase):
    __tablename__ = "nomination_cycles"

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[CycleStatus] = mapped_column(Enum(CycleStatus, name="cycle_status"), nullable=False, server_default=CycleStatus.DRAFT.value)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    criteria: Mapped[list["Criteria"]] = relationship("Criteria", back_populates="cycle", cascade="all, delete-orphan")


class Criteria(TimestampedUUIDBase):
    __tablename__ = "criteria"
    __table_args__ = (
        UniqueConstraint("cycle_id", "name", name="uq_criteria_cycle_name"),
        CheckConstraint("weight >= 0", name="ck_criteria_weight_non_negative"),
    )

    cycle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("nomination_cycles.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    weight: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    # JSON configuration for question type and options
    # Examples:
    # - {"type": "text", "required": true}
    # - {"type": "single_select", "options": ["Option 1", "Option 2"], "required": true}
    # - {"type": "multi_select", "options": ["Option A", "Option B", "Option C"], "required": true}
    # - {"type": "text_with_image", "required": false, "image_required": false}
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    cycle: Mapped[NominationCycle] = relationship("NominationCycle", back_populates="criteria")
    scores: Mapped[list["NominationCriteriaScore"]] = relationship(
        "NominationCriteriaScore", back_populates="criteria", cascade="all, delete-orphan"
    )


class Nomination(TimestampedUUIDBase):
    __tablename__ = "nominations"
    __table_args__ = (
        # Prevent same employee from being nominated twice in the same cycle (regardless of who submits)
        UniqueConstraint("cycle_id", "nominee_user_id", name="uq_nomination_unique_nominee"),
        # Also prevent same person from submitting multiple nominations for same employee in same cycle
        UniqueConstraint("cycle_id", "nominee_user_id", "submitted_by", name="uq_nomination_unique_submitter"),
        Index("ix_nominations_cycle_team", "cycle_id", "team_id"),
    )

    cycle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("nomination_cycles.id"), nullable=False)
    nominee_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    submitted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")
    status: Mapped[NominationStatus] = mapped_column(
        Enum(NominationStatus, name="nomination_status"), nullable=False, server_default=NominationStatus.PENDING.value
    )

    cycle: Mapped[NominationCycle] = relationship("NominationCycle")
    nominee: Mapped[User] = relationship("User", foreign_keys=[nominee_user_id])
    team: Mapped[Team | None] = relationship("Team")
    submitted_by_user: Mapped[User] = relationship("User", foreign_keys=[submitted_by])
    scores: Mapped[list["NominationCriteriaScore"]] = relationship(
        "NominationCriteriaScore", back_populates="nomination", cascade="all, delete-orphan"
    )
    approvals: Mapped[list["Approval"]] = relationship("Approval", back_populates="nomination", cascade="all, delete-orphan")


class NominationCriteriaScore(TimestampedUUIDBase):
    __tablename__ = "nomination_criteria_scores"
    __table_args__ = (UniqueConstraint("nomination_id", "criteria_id", name="uq_score_nomination_criteria"),)

    nomination_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("nominations.id"), nullable=False)
    criteria_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("criteria.id"), nullable=False)
    # Legacy field - kept for backward compatibility, can be calculated from answer
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Answer data stored as JSON
    # For text: {"text": "answer text"}
    # For single_select: {"selected": "Option 1"}
    # For multi_select: {"selected": ["Option A", "Option B"]}
    # For text_with_image: {"text": "answer", "image_url": "https://..."}
    answer: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Legacy comment field - kept for backward compatibility
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    nomination: Mapped[Nomination] = relationship("Nomination", back_populates="scores")
    criteria: Mapped[Criteria] = relationship("Criteria", back_populates="scores")


class Approval(TimestampedUUIDBase):
    __tablename__ = "approvals"
    __table_args__ = (UniqueConstraint("nomination_id", "actor_user_id", name="uq_approval_actor_once"),)

    nomination_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("nominations.id"), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action: Mapped[ApprovalAction] = mapped_column(Enum(ApprovalAction, name="approval_action"), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Manager rating/score for the nomination (e.g., 1-10, 1-5, etc.)
    rating: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    acted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")

    nomination: Mapped[Nomination] = relationship("Nomination", back_populates="approvals")
    actor: Mapped[User] = relationship("User")


class AuditLog(TimestampedUUIDBase):
    __tablename__ = "audit_logs"

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    actor: Mapped[User | None] = relationship("User")


class Ranking(TimestampedUUIDBase):
    __tablename__ = "rankings"

    cycle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("nomination_cycles.id"), nullable=False)
    team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True)
    nominee_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    total_score: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default="now()")


class NominationHistory(TimestampedUUIDBase):
    __tablename__ = "nominations_history"

    source_nomination_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    cycle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    nominee_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    submitted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class RankingHistory(TimestampedUUIDBase):
    __tablename__ = "rankings_history"

    source_ranking_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    cycle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    team_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    nominee_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    total_score: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PasswordResetToken(TimestampedUUIDBase):
    __tablename__ = "password_reset_tokens"
    __table_args__ = (Index("ix_password_reset_tokens_token_hash", "token_hash"), Index("ix_password_reset_tokens_user_id", "user_id"))

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="password_reset_tokens")


class SecurityQuestion(TimestampedUUIDBase):
    __tablename__ = "security_questions"
    __table_args__ = (
        Index("ix_security_questions_user_id", "user_id"),
        UniqueConstraint("user_id", "question_text", name="uq_user_question"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    question_text: Mapped[str] = mapped_column(String(500), nullable=False)
    answer_hash: Mapped[str] = mapped_column(String(255), nullable=False)  # Hashed answer
    question_order: Mapped[int] = mapped_column(Integer, nullable=False)  # Order of question (1, 2, 3, etc.)

    user: Mapped["User"] = relationship("User", back_populates="security_questions")
