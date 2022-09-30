"""Add primary_identifier to MerchantIdentifier, SchemeTransaction, PaymentTransaction & ExportTransaction tables

Revision ID: 76de66565f46
Revises: ba66e031b852
Create Date: 2022-09-14 08:57:16.092651+00:00

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "76de66565f46"
down_revision = "ba66e031b852"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("export_transaction", sa.Column("primary_identifier", sa.String(length=50), nullable=True))
    op.add_column("matched_transaction", sa.Column("primary_identifier", sa.String(length=50), nullable=True))
    op.add_column("payment_transaction", sa.Column("primary_identifier", sa.String(length=50), nullable=True))
    op.add_column("scheme_transaction", sa.Column("primary_identifier", sa.String(length=50), nullable=True))
    op.add_column("transaction", sa.Column("primary_identifier", sa.String(length=50), nullable=True))


def downgrade():
    op.drop_column("transaction", "primary_identifier")
    op.drop_column("scheme_transaction", "primary_identifier")
    op.drop_column("payment_transaction", "primary_identifier")
    op.drop_column("matched_transaction", "primary_identifier")
    op.drop_column("export_transaction", "primary_identifier")
