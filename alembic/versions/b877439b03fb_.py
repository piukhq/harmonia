"""store a list of merchant ids on scheme/payment transactions

Revision ID: b877439b03fb
Revises: 1c4b5f65fcb7
Create Date: 2019-02-19 09:46:02.781595+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b877439b03fb"
down_revision = "1c4b5f65fcb7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "payment_transaction",
        sa.Column(
            "merchant_identifier_ids",
            postgresql.ARRAY(sa.Integer()),
            nullable=True,
        ),
    )
    op.drop_constraint(
        "payment_transaction_merchant_identifier_id_fkey",
        "payment_transaction",
        type_="foreignkey",
    )
    op.drop_column("payment_transaction", "merchant_identifier_id")
    op.add_column(
        "scheme_transaction",
        sa.Column(
            "merchant_identifier_ids",
            postgresql.ARRAY(sa.Integer()),
            nullable=True,
        ),
    )
    op.drop_constraint(
        "scheme_transaction_merchant_identifier_id_fkey",
        "scheme_transaction",
        type_="foreignkey",
    )
    op.drop_column("scheme_transaction", "merchant_identifier_id")


def downgrade():
    op.add_column(
        "scheme_transaction",
        sa.Column(
            "merchant_identifier_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "scheme_transaction_merchant_identifier_id_fkey",
        "scheme_transaction",
        "merchant_identifier",
        ["merchant_identifier_id"],
        ["id"],
    )
    op.drop_column("scheme_transaction", "merchant_identifier_ids")
    op.add_column(
        "payment_transaction",
        sa.Column(
            "merchant_identifier_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "payment_transaction_merchant_identifier_id_fkey",
        "payment_transaction",
        "merchant_identifier",
        ["merchant_identifier_id"],
        ["id"],
    )
    op.drop_column("payment_transaction", "merchant_identifier_ids")
