"""add match_group to transaction tables

Revision ID: 1a5ad3ad85db
Revises: dd1520e937b8
Create Date: 2020-09-30 15:41:58.572686+00:00

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "1a5ad3ad85db"
down_revision = "dd1520e937b8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("import_transaction", sa.Column("match_group", sa.String(length=36), nullable=True))
    op.execute("UPDATE import_transaction SET match_group = 'no match group'")
    op.alter_column("import_transaction", "match_group", nullable=False)

    op.add_column("payment_transaction", sa.Column("match_group", sa.String(length=36), nullable=True))
    op.execute("UPDATE payment_transaction SET match_group = 'no match group'")
    op.alter_column("payment_transaction", "match_group", nullable=False)

    op.create_index(op.f("ix_payment_transaction_match_group"), "payment_transaction", ["match_group"], unique=False)

    op.add_column("scheme_transaction", sa.Column("match_group", sa.String(length=36), nullable=True))
    op.execute("UPDATE scheme_transaction SET match_group = 'no match group'")
    op.alter_column("scheme_transaction", "match_group", nullable=False)

    op.create_index(op.f("ix_scheme_transaction_match_group"), "scheme_transaction", ["match_group"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_scheme_transaction_match_group"), table_name="scheme_transaction")
    op.drop_column("scheme_transaction", "match_group")
    op.drop_index(op.f("ix_payment_transaction_match_group"), table_name="payment_transaction")
    op.drop_column("payment_transaction", "match_group")
    op.drop_column("import_transaction", "match_group")
