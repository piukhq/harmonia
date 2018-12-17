"""link matched transactions back to their component scheme/payment transactions

Revision ID: 2cd4f2cb0d39
Revises: e87d2fef31a9
Create Date: 2018-11-05 15:22:04.474016+00:00

"""
from alembic import op
import sqlalchemy as sa


revision = "2cd4f2cb0d39"
down_revision = "e87d2fef31a9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "matched_transaction",
        sa.Column("payment_transaction_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "matched_transaction",
        sa.Column("scheme_transaction_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        None,
        "matched_transaction",
        "payment_transaction",
        ["payment_transaction_id"],
        ["id"],
    )
    op.create_foreign_key(
        None,
        "matched_transaction",
        "scheme_transaction",
        ["scheme_transaction_id"],
        ["id"],
    )


def downgrade():
    op.drop_constraint(None, "matched_transaction", type_="foreignkey")
    op.drop_constraint(None, "matched_transaction", type_="foreignkey")
    op.drop_column("matched_transaction", "scheme_transaction_id")
    op.drop_column("matched_transaction", "payment_transaction_id")
