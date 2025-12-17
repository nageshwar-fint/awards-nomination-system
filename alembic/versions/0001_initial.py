"""Initial schema for core nomination tables."""

from datetime import datetime
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _create_enum_if_not_exists(name: str, values: list[str]) -> None:
    quoted = ", ".join([f"'{v}'" for v in values])
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = '{name}') THEN
                CREATE TYPE {name} AS ENUM ({quoted});
            END IF;
        END$$;
        """
    )


def upgrade() -> None:
    # Clean up leftover enum types from prior failed runs (no tables yet).
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP TYPE IF EXISTS cycle_status")
    op.execute("DROP TYPE IF EXISTS nomination_status")
    op.execute("DROP TYPE IF EXISTS approval_action")

    _create_enum_if_not_exists("user_role", ["EMPLOYEE", "TEAM_LEAD", "MANAGER", "HR"])
    _create_enum_if_not_exists("cycle_status", ["DRAFT", "OPEN", "CLOSED", "FINALIZED"])
    _create_enum_if_not_exists("nomination_status", ["PENDING", "APPROVED", "REJECTED"])
    _create_enum_if_not_exists("approval_action", ["APPROVE", "REJECT"])

    user_role = postgresql.ENUM("EMPLOYEE", "TEAM_LEAD", "MANAGER", "HR", name="user_role", create_type=False)
    cycle_status = postgresql.ENUM("DRAFT", "OPEN", "CLOSED", "FINALIZED", name="cycle_status", create_type=False)
    nomination_status = postgresql.ENUM("PENDING", "APPROVED", "REJECTED", name="nomination_status", create_type=False)
    approval_action = postgresql.ENUM("APPROVE", "REJECT", name="approval_action", create_type=False)

    op.create_table(
        "teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("role", user_role, nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="ACTIVE"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "nomination_cycles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", cycle_status, nullable=False, server_default="DRAFT"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
    )

    op.create_table(
        "criteria",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("cycle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("nomination_cycles.id"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("weight", sa.Numeric(5, 4), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("cycle_id", "name", name="uq_criteria_cycle_name"),
        sa.CheckConstraint("weight >= 0", name="ck_criteria_weight_non_negative"),
    )

    op.create_table(
        "nominations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("cycle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("nomination_cycles.id"), nullable=False),
        sa.Column("nominee_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("submitted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("status", nomination_status, nullable=False, server_default="PENDING"),
        sa.UniqueConstraint("cycle_id", "nominee_user_id", "submitted_by", name="uq_nomination_unique_submitter"),
    )
    op.create_index("ix_nominations_cycle_team", "nominations", ["cycle_id", "team_id"])

    op.create_table(
        "nomination_criteria_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("nomination_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("nominations.id"), nullable=False),
        sa.Column("criteria_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("criteria.id"), nullable=False),
        sa.Column("score", sa.Integer, nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.UniqueConstraint("nomination_id", "criteria_id", name="uq_score_nomination_criteria"),
    )

    op.create_table(
        "approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("nomination_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("nominations.id"), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", approval_action, nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("acted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("nomination_id", "actor_user_id", name="uq_approval_actor_once"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=255), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("approvals")
    op.drop_table("nomination_criteria_scores")
    op.drop_table("nominations")
    op.drop_table("criteria")
    op.drop_table("nomination_cycles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("teams")

    op.execute("DROP TYPE IF EXISTS approval_action")
    op.execute("DROP TYPE IF EXISTS nomination_status")
    op.execute("DROP TYPE IF EXISTS cycle_status")
    op.execute("DROP TYPE IF EXISTS user_role")
