"""Add config column to criteria table

Revision ID: 3bf16e83bbb2
Revises: 979f76045770
Create Date: 2025-12-18 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '3bf16e83bbb2'
down_revision = '979f76045770'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add config column to criteria table for flexible question types
    op.add_column('criteria', 
                  sa.Column('config', postgresql.JSONB, nullable=True))


def downgrade() -> None:
    # Remove config column
    op.drop_column('criteria', 'config')

