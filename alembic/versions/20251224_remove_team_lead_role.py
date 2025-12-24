"""Remove TEAM_LEAD role from user_role enum and map existing TEAM_LEAD users to MANAGER

Revision ID: 20251224_remove_team_lead_role
Revises: c8f2e3d4a5b6
Create Date: 2025-12-24 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20251224_remove_team_lead_role"
down_revision = "c8f2e3d4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Map any existing TEAM_LEAD users to MANAGER
    op.execute("UPDATE users SET role='MANAGER' WHERE role='TEAM_LEAD'")

    # Create a new enum type without TEAM_LEAD
    op.execute("CREATE TYPE user_role_new AS ENUM('EMPLOYEE','MANAGER','HR')")

    # Alter users.role to new type
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE user_role_new USING role::text::user_role_new"
    )

    # Drop old type and rename new to user_role
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("ALTER TYPE user_role_new RENAME TO user_role")


def downgrade() -> None:
    # Recreate original enum including TEAM_LEAD
    op.execute("CREATE TYPE user_role_old AS ENUM('EMPLOYEE','TEAM_LEAD','MANAGER','HR')")

    # Alter users.role to old type
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE user_role_old USING role::text::user_role_old"
    )

    # Drop current user_role and rename old back
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("ALTER TYPE user_role_old RENAME TO user_role")
