"""add first six/last four to user identity

Revision ID: dca8d95d37b7
Revises: 25cea07a031e
Create Date: 2020-02-13 15:47:18.124639+00:00

"""
from alembic import op
import sqlalchemy as sa


revision = "dca8d95d37b7"
down_revision = "25cea07a031e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("user_identity", sa.Column("first_six", sa.Text(), nullable=False))
    op.add_column("user_identity", sa.Column("last_four", sa.Text(), nullable=False))


def downgrade():
    op.drop_column("user_identity", "last_four")
    op.drop_column("user_identity", "first_six")
