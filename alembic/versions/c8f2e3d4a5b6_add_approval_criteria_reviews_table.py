"""Add approval_criteria_reviews table

Revision ID: c8f2e3d4a5b6
Revises: a3dba6f129e7
Create Date: 2025-12-19 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c8f2e3d4a5b6'
down_revision = 'a3dba6f129e7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create approval_criteria_reviews table
    op.create_table(
        'approval_criteria_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('approval_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('criteria_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rating', sa.Numeric(5, 2), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['approval_id'], ['approvals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['criteria_id'], ['criteria.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('approval_id', 'criteria_id', name='uq_approval_criteria_review')
    )


def downgrade() -> None:
    # Drop approval_criteria_reviews table
    op.drop_table('approval_criteria_reviews')

