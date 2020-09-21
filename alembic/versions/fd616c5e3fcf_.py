"""ensure uniqueness of loyalty scheme and payment provider slugs

Revision ID: fd616c5e3fcf
Revises: cfed42292ce7
Create Date: 2020-04-17 13:34:32.686538+00:00

"""
from alembic import op


revision = "fd616c5e3fcf"
down_revision = "cfed42292ce7"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(op.f("ix_loyalty_scheme_slug"), "loyalty_scheme", ["slug"], unique=True)
    op.create_index(op.f("ix_payment_provider_slug"), "payment_provider", ["slug"], unique=True)


def downgrade():
    op.drop_index(op.f("ix_payment_provider_slug"), table_name="payment_provider")
    op.drop_index(op.f("ix_loyalty_scheme_slug"), table_name="loyalty_scheme")
