"""drop scheme and payment transaction relationships from matched transaction

Revision ID: 2782ee0b9f9c
Revises: 663e08279b0d
Create Date: 2022-04-05 16:31:24.829485+00:00

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "2782ee0b9f9c"
down_revision = "663e08279b0d"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("matched_transaction_payment_transaction_id_fkey", "matched_transaction", type_="foreignkey")
    op.drop_constraint("matched_transaction_scheme_transaction_id_fkey", "matched_transaction", type_="foreignkey")
    op.drop_column("matched_transaction", "scheme_transaction_id")
    op.drop_column("matched_transaction", "payment_transaction_id")


def downgrade():
    op.add_column(
        "matched_transaction", sa.Column("payment_transaction_id", sa.INTEGER(), autoincrement=False, nullable=True)
    )
    op.add_column(
        "matched_transaction", sa.Column("scheme_transaction_id", sa.INTEGER(), autoincrement=False, nullable=True)
    )
    op.create_foreign_key(
        "matched_transaction_scheme_transaction_id_fkey",
        "matched_transaction",
        "scheme_transaction",
        ["scheme_transaction_id"],
        ["id"],
    )
    op.create_foreign_key(
        "matched_transaction_payment_transaction_id_fkey",
        "matched_transaction",
        "payment_transaction",
        ["payment_transaction_id"],
        ["id"],
    )
