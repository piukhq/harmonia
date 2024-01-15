"""add loyalty_scheme_id to merchant_identifier unique constraint

Revision ID: fd64a9549bac
Revises: dccf9b0dbe0a
Create Date: 2024-01-15 10:10:21.428553+00:00

"""
import sqlalchemy as sa

from alembic import op

revision = "fd64a9549bac"
down_revision = "dccf9b0dbe0a"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("_identifier_type_provider_mi_uc", "merchant_identifier", type_="unique")
    op.create_unique_constraint(
        "_identifier_type_provider_mi_uc",
        "merchant_identifier",
        ["identifier", "identifier_type", "payment_provider_id", "loyalty_scheme_id"],
    )


def downgrade():
    op.drop_constraint("_identifier_type_provider_mi_uc", "merchant_identifier", type_="unique")
    op.create_unique_constraint(
        "_identifier_type_provider_mi_uc",
        "merchant_identifier",
        ["identifier", "identifier_type", "payment_provider_id"],
    )
