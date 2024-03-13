"""Add failure reason to pending_export

Revision ID: 01bd04c18481
Revises: dccf9b0dbe0a
Create Date: 2024-03-11 12:29:41.762590+00:00

"""
import sqlalchemy as sa

from alembic import op

revision = "01bd04c18481"
down_revision = "dccf9b0dbe0a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("pending_export", sa.Column("failure_reason", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("pending_export", "failure_reason")
