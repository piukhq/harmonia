"""Add primary_identifier to MatchedTransaction

Revision ID: f13114e488aa
Revises: bbb2a2304a6f
Create Date: 2022-09-12 13:34:51.402488+00:00

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f13114e488aa"
down_revision = "bbb2a2304a6f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("matched_transaction", sa.Column("primary_identifier", sa.String(length=50), nullable=True))


def downgrade():
    op.drop_column("matched_transaction", "primary_identifier")
