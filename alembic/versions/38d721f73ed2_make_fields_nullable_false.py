"""make fields nullable=False

Revision ID: 38d721f73ed2
Revises: 5477ff60b0b3
Create Date: 2022-12-21 16:07:18.699305+00:00

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "38d721f73ed2"
down_revision = "5477ff60b0b3"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("export_transaction", "primary_identifier", existing_type=sa.VARCHAR(length=50), nullable=False)
    op.alter_column(
        "import_transaction",
        "feed_type",
        existing_type=postgresql.ENUM("MERCHANT", "AUTH", "SETTLED", "REFUND", name="feedtype"),
        nullable=False,
    )
    op.alter_column("matched_transaction", "primary_identifier", existing_type=sa.VARCHAR(length=50), nullable=False)
    op.alter_column("payment_transaction", "primary_identifier", existing_type=sa.VARCHAR(length=50), nullable=False)
    op.alter_column("scheme_transaction", "primary_identifier", existing_type=sa.VARCHAR(length=50), nullable=False)
    op.alter_column("transaction", "primary_identifier", existing_type=sa.VARCHAR(length=50), nullable=False)


def downgrade():
    op.alter_column("transaction", "primary_identifier", existing_type=sa.VARCHAR(length=50), nullable=True)
    op.alter_column("scheme_transaction", "primary_identifier", existing_type=sa.VARCHAR(length=50), nullable=True)
    op.alter_column("payment_transaction", "primary_identifier", existing_type=sa.VARCHAR(length=50), nullable=True)
    op.alter_column("matched_transaction", "primary_identifier", existing_type=sa.VARCHAR(length=50), nullable=True)
    op.alter_column(
        "import_transaction",
        "feed_type",
        existing_type=postgresql.ENUM("MERCHANT", "AUTH", "SETTLED", "REFUND", name="feedtype"),
        nullable=True,
    )
    op.alter_column("export_transaction", "primary_identifier", existing_type=sa.VARCHAR(length=50), nullable=True)
