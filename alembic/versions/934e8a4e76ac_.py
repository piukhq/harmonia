"""add settlement_key field to payment transaction

Revision ID: 934e8a4e76ac
Revises: a3c90f608d86
Create Date: 2020-03-27 10:04:20.187586+00:00

"""
import sqlalchemy as sa

from alembic import op

revision = "934e8a4e76ac"
down_revision = "a3c90f608d86"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payment_transaction", sa.Column("settlement_key", sa.String(length=100), nullable=True))
    op.create_index(
        op.f("ix_payment_transaction_settlement_key"), "payment_transaction", ["settlement_key"], unique=True
    )


def downgrade():
    op.drop_index(op.f("ix_payment_transaction_settlement_key"), table_name="payment_transaction")
    op.drop_column("payment_transaction", "settlement_key")
