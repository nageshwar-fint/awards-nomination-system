"""Add profile_picture_url column to users table

Revision ID: a3dba6f129e7
Revises: 71da17e1c5df
Create Date: 2025-12-18 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a3dba6f129e7'
down_revision = '71da17e1c5df'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add profile_picture_url column to users table
    op.add_column('users', 
                  sa.Column('profile_picture_url', sa.String(length=500), nullable=True))


def downgrade() -> None:
    # Remove profile_picture_url column
    op.drop_column('users', 'profile_picture_url')

