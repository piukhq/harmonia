"""make primary_identifier field not nullable

Revision ID: 09c76ce2bf05
Revises: 5477ff60b0b3
Create Date: 2022-10-06 14:59:37.796077+00:00

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "09c76ce2bf05"
down_revision = "5477ff60b0b3"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("export_transaction", "primary_identifier", existing_type=sa.VARCHAR(length=50), nullable=False)
    op.alter_column("matched_transaction", "primary_identifier", existing_type=sa.VARCHAR(length=50), nullable=False)
    op.alter_column("payment_transaction", "primary_identifier", existing_type=sa.VARCHAR(length=50), nullable=False)
    op.alter_column("scheme_transaction", "primary_identifier", existing_type=sa.VARCHAR(length=50), nullable=False)
    op.alter_column("transaction", "primary_identifier", existing_type=sa.VARCHAR(length=50), nullable=False)


def downgrade():
    op.alter_column("transaction", "primary_identifier", existing_type=sa.VARCHAR(length=50), nullable=True)
    op.alter_column("scheme_transaction", "primary_identifier", existing_type=sa.VARCHAR(length=50), nullable=True)
    op.alter_column("payment_transaction", "primary_identifier", existing_type=sa.VARCHAR(length=50), nullable=True)
    op.alter_column("matched_transaction", "primary_identifier", existing_type=sa.VARCHAR(length=50), nullable=True)
    op.alter_column("export_transaction", "primary_identifier", existing_type=sa.VARCHAR(length=50), nullable=True)
