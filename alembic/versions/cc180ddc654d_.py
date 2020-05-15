"""Add auth_code to payment and merchant transactions

Revision ID: cc180ddc654d
Revises: 97aabf7b110b
Create Date: 2020-05-15 08:57:46.115349+00:00

"""
from alembic import op
import sqlalchemy as sa


revision = "cc180ddc654d"
down_revision = "97aabf7b110b"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payment_transaction", sa.Column("auth_code", sa.String(length=20), nullable=False))
    op.add_column("scheme_transaction", sa.Column("auth_code", sa.String(length=20), nullable=False))


def downgrade():
    op.drop_column("scheme_transaction", "auth_code")
    op.drop_column("payment_transaction", "auth_code")
