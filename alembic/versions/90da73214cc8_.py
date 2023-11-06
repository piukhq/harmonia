"""include loyalty scheme ID in MID uniqueness constraint

Revision ID: 90da73214cc8
Revises: dccf9b0dbe0a
Create Date: 2023-11-06 17:13:56.630818+00:00

"""
from alembic import op

revision = "90da73214cc8"
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
