"""add dpan first six & last four to scheme transaction

Revision ID: b63ca0388cfc
Revises: b723a8757024
Create Date: 2021-04-20 14:29:02.163605+00:00

"""
from alembic import op
import sqlalchemy as sa


revision = "b63ca0388cfc"
down_revision = "b723a8757024"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("scheme_transaction", sa.Column("first_six", sa.Text(), nullable=True))
    op.add_column("scheme_transaction", sa.Column("last_four", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("scheme_transaction", "last_four")
    op.drop_column("scheme_transaction", "first_six")
