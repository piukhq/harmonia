"""Add primary_identifier column to PaymentTransaction & SchemeTransaction

Revision ID: bbb2a2304a6f
Revises: d93d68828e5a
Create Date: 2022-09-09 13:41:01.394035+00:00

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "bbb2a2304a6f"
down_revision = "d93d68828e5a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payment_transaction", sa.Column("primary_identifier", sa.String(length=50), nullable=True))
    op.add_column("scheme_transaction", sa.Column("primary_identifier", sa.String(length=50), nullable=True))


def downgrade():
    op.drop_column("scheme_transaction", "primary_identifier")
    op.drop_column("payment_transaction", "primary_identifier")
