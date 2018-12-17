"""add identified column to import transaction table

Revision ID: 731b1776a55d
Revises: d454aa1b0925
Create Date: 2018-12-04 14:16:42.119802+00:00

"""
from alembic import op
import sqlalchemy as sa


revision = "731b1776a55d"
down_revision = "d454aa1b0925"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "import_transaction", sa.Column("identified", sa.Boolean(), nullable=False)
    )


def downgrade():
    op.drop_column("import_transaction", "identified")
