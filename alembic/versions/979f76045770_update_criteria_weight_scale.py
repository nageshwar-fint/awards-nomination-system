"""Update criteria weight scale from 0-1 to 0-10

Revision ID: 979f76045770
Revises: d9cb9c59d983
Create Date: 2025-12-18 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '979f76045770'
down_revision = 'd9cb9c59d983'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Change weight column from Numeric(5, 4) to Numeric(5, 2) to support 0-10 scale
    op.alter_column('criteria', 'weight',
                    existing_type=sa.Numeric(5, 4),
                    type_=sa.Numeric(5, 2),
                    existing_nullable=False)


def downgrade() -> None:
    # Revert back to Numeric(5, 4) for 0-1 scale
    op.alter_column('criteria', 'weight',
                    existing_type=sa.Numeric(5, 2),
                    type_=sa.Numeric(5, 4),
                    existing_nullable=False)

