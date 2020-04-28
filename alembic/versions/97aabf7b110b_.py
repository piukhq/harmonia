"""add provider slugs to payment & scheme transactions

Revision ID: 97aabf7b110b
Revises: fd616c5e3fcf
Create Date: 2020-04-27 14:54:28.583591+00:00

"""
from alembic import op
import sqlalchemy as sa


revision = "97aabf7b110b"
down_revision = "fd616c5e3fcf"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payment_transaction", sa.Column("provider_slug", sa.String(length=50), nullable=False))
    op.add_column("scheme_transaction", sa.Column("provider_slug", sa.String(length=50), nullable=False))
    op.add_column("scheme_transaction", sa.Column("payment_provider_slug", sa.String(length=50), nullable=False))


def downgrade():
    op.drop_column("scheme_transaction", "provider_slug")
    op.drop_column("payment_transaction", "provider_slug")
    op.drop_column("scheme_transaction", "payment_provider_slug")
