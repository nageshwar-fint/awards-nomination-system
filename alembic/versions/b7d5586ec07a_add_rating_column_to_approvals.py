"""Add rating column to approvals table

Revision ID: b7d5586ec07a
Revises: eb6969ab1909
Create Date: 2025-12-18 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b7d5586ec07a'
down_revision = 'eb6969ab1909'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add rating column for manager rating/score (e.g., 1-10, 1-5, etc.)
    op.add_column('approvals', 
                  sa.Column('rating', sa.Numeric(5, 2), nullable=True))


def downgrade() -> None:
    # Remove rating column
    op.drop_column('approvals', 'rating')

