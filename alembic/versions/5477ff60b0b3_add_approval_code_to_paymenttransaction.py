"""Add approval code to PaymentTransaction

Revision ID: 5477ff60b0b3
Revises: 76de66565f46
Create Date: 2022-10-03 13:54:57.089500+00:00

"""
import sqlalchemy as sa

from alembic import op

revision = "5477ff60b0b3"
down_revision = "76de66565f46"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "payment_transaction", sa.Column("approval_code", sa.String(length=20), nullable=False, server_default="")
    )


def downgrade():
    op.drop_column("payment_transaction", "approval_code")
