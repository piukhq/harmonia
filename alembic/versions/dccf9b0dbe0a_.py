"""convert primary_identifier scalar field to primary_identifiers array field on transaction and scheme_transaction tables

Revision ID: dccf9b0dbe0a
Revises: 6e064125f2d7
Create Date: 2023-04-26 13:17:57.628563+00:00

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "dccf9b0dbe0a"
down_revision = "6e064125f2d7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "scheme_transaction", sa.Column("primary_identifiers", postgresql.ARRAY(sa.String(length=50)), nullable=True)
    )
    op.execute("UPDATE scheme_transaction SET primary_identifiers = ARRAY[primary_identifier]")
    op.alter_column("scheme_transaction", "primary_identifiers", nullable=False)
    op.drop_column("scheme_transaction", "primary_identifier")

    op.add_column(
        "transaction", sa.Column("primary_identifiers", postgresql.ARRAY(sa.String(length=50)), nullable=True)
    )
    op.execute("UPDATE transaction SET primary_identifiers = ARRAY[primary_identifier]")
    op.alter_column("transaction", "primary_identifiers", nullable=False)
    op.drop_column("transaction", "primary_identifier")


def downgrade():
    op.add_column("transaction", sa.Column("primary_identifier", sa.VARCHAR(length=50), nullable=True))
    op.execute("UPDATE transaction SET primary_identifier = primary_identifiers[1]")
    op.alter_column("transaction", "primary_identifier", nullable=False)
    op.drop_column("transaction", "primary_identifiers")

    op.add_column(
        "scheme_transaction",
        sa.Column("primary_identifier", sa.VARCHAR(length=50), nullable=True),
    )
    op.execute("UPDATE scheme_transaction SET primary_identifier = primary_identifiers[1]")
    op.alter_column("scheme_transaction", "primary_identifier", nullable=False)
    op.drop_column("scheme_transaction", "primary_identifiers")
