"""Prevent duplicate nominee per cycle (regardless of submitter)

Revision ID: 71da17e1c5df
Revises: b7d5586ec07a
Create Date: 2025-12-18 16:00:00.000000

"""
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision = '71da17e1c5df'
down_revision = 'b7d5586ec07a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, remove duplicate nominations (keep the first one created for each cycle/nominee pair)
    # This handles existing data that violates the new constraint
    conn = op.get_bind()
    
    # Find duplicate nominations (same cycle and nominee, but different submitters)
    # Keep the one with the earliest created_at, delete the rest
    # First, delete related records (approvals and scores) for duplicates
    conn.execute(text("""
        DELETE FROM approvals
        WHERE nomination_id IN (
            SELECT n1.id
            FROM nominations n1
            INNER JOIN nominations n2
                ON n1.cycle_id = n2.cycle_id
                AND n1.nominee_user_id = n2.nominee_user_id
            WHERE n1.id > n2.id
        )
    """))
    
    conn.execute(text("""
        DELETE FROM nomination_criteria_scores
        WHERE nomination_id IN (
            SELECT n1.id
            FROM nominations n1
            INNER JOIN nominations n2
                ON n1.cycle_id = n2.cycle_id
                AND n1.nominee_user_id = n2.nominee_user_id
            WHERE n1.id > n2.id
        )
    """))
    
    # Now delete the duplicate nominations
    conn.execute(text("""
        DELETE FROM nominations n1
        USING nominations n2
        WHERE n1.cycle_id = n2.cycle_id
          AND n1.nominee_user_id = n2.nominee_user_id
          AND n1.id > n2.id
    """))
    
    # Drop the old unique constraint that includes submitted_by
    op.drop_constraint('uq_nomination_unique_submitter', 'nominations', type_='unique')
    
    # Add new constraint: same employee cannot be nominated twice in same cycle (regardless of who submits)
    op.create_unique_constraint('uq_nomination_unique_nominee', 'nominations', ['cycle_id', 'nominee_user_id'])
    
    # Also keep constraint to prevent same person from submitting multiple times for same employee
    op.create_unique_constraint('uq_nomination_unique_submitter', 'nominations', ['cycle_id', 'nominee_user_id', 'submitted_by'])


def downgrade() -> None:
    # Revert to old constraint
    op.drop_constraint('uq_nomination_unique_nominee', 'nominations', type_='unique')
    op.drop_constraint('uq_nomination_unique_submitter', 'nominations', type_='unique')
    op.create_unique_constraint('uq_nomination_unique_submitter', 'nominations', ['cycle_id', 'nominee_user_id', 'submitted_by'])

