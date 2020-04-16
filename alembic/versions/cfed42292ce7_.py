"""remove duplicate index on mid table

Revision ID: cfed42292ce7
Revises: 934e8a4e76ac
Create Date: 2020-04-16 14:10:19.246184+00:00

"""
from alembic import op


revision = "cfed42292ce7"
down_revision = "934e8a4e76ac"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("ix_merchant_identifier_mid", table_name="merchant_identifier")
    op.drop_index("ix_payment_transaction_settlement_key", table_name="payment_transaction")
    op.create_index(
        op.f("ix_payment_transaction_settlement_key"), "payment_transaction", ["settlement_key"], unique=False
    )


def downgrade():
    op.drop_index(op.f("ix_payment_transaction_settlement_key"), table_name="payment_transaction")
    op.create_index("ix_payment_transaction_settlement_key", "payment_transaction", ["settlement_key"], unique=True)
    op.create_index("ix_merchant_identifier_mid", "merchant_identifier", ["mid"], unique=False)
