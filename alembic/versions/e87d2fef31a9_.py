"""add transaction status column

Revision ID: e87d2fef31a9
Revises: 01918d55a507
Create Date: 2018-11-05 10:55:31.769896+00:00

"""
from alembic import op
import sqlalchemy as sa

revision = "e87d2fef31a9"
down_revision = "01918d55a507"
branch_labels = None
depends_on = None


def upgrade():
    TransactionStatus = sa.Enum("PENDING", "MATCHED", name="transactionstatus")
    TransactionStatus.create(op.get_bind())
    op.add_column(
        "payment_transaction", sa.Column("status", TransactionStatus, nullable=False)
    )
    op.add_column(
        "scheme_transaction", sa.Column("status", TransactionStatus, nullable=False)
    )

    MatchedTransactionStatus = sa.Enum(
        "PENDING", "EXPORTED", name="matchedtransactionstatus"
    )
    MatchedTransactionStatus.create(op.get_bind())
    op.add_column(
        "matched_transaction",
        sa.Column("status", MatchedTransactionStatus, nullable=False),
    )


def downgrade():
    op.drop_column("scheme_transaction", "status")
    op.drop_column("payment_transaction", "status")
    op.drop_column("matched_transaction", "status")
    sa.Enum(name="transactionstatus").drop(op.get_bind())
    sa.Enum(name="matchedtransactionstatus").drop(op.get_bind())
