"""Add answer column to nomination_criteria_scores table

Revision ID: eb6969ab1909
Revises: 3bf16e83bbb2
Create Date: 2025-12-18 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'eb6969ab1909'
down_revision = '3bf16e83bbb2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add answer column for flexible criteria answers (JSONB)
    op.add_column('nomination_criteria_scores', 
                  sa.Column('answer', postgresql.JSONB, nullable=True))
    
    # Make score nullable to match model (it was created as NOT NULL in initial migration)
    op.alter_column('nomination_criteria_scores', 'score',
                    existing_type=sa.Integer,
                    nullable=True)


def downgrade() -> None:
    # Remove answer column
    op.drop_column('nomination_criteria_scores', 'answer')
    
    # Revert score to NOT NULL (though this might fail if there are NULL values)
    op.alter_column('nomination_criteria_scores', 'score',
                    existing_type=sa.Integer,
                    nullable=False)

