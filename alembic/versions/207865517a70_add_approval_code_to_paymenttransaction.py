"""add approval code to PaymentTransaction

Revision ID: 207865517a70
Revises: ba66e031b852
Create Date: 2022-09-28 13:15:08.736228+00:00

"""
from alembic import op
import sqlalchemy as sa


revision = "207865517a70"
down_revision = "ba66e031b852"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "payment_transaction", sa.Column("approval_code", sa.String(length=20), nullable=False, server_default="")
    )


def downgrade():
    op.drop_column("payment_transaction", "approval_code")
