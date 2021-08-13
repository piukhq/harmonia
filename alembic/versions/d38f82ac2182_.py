"""add index on transaction_date field

Revision ID: d38f82ac2182
Revises: 1a5ad3ad85db
Create Date: 2020-10-02 09:06:53.793222+00:00

"""
from alembic import op

revision = "d38f82ac2182"
down_revision = "1a5ad3ad85db"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        op.f("ix_scheme_transaction_transaction_date"), "scheme_transaction", ["transaction_date"], unique=False
    )


def downgrade():
    op.drop_index(op.f("ix_scheme_transaction_transaction_date"), table_name="scheme_transaction")
