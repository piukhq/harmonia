"""enforce mid uniqueness

Revision ID: a39cd4ddfaa9
Revises: b877439b03fb
Create Date: 2019-03-19 16:16:51.087603+00:00

"""
from alembic import op


revision = "a39cd4ddfaa9"
down_revision = "b877439b03fb"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint("_mid_provider_mi_uc", "merchant_identifier", ["mid", "payment_provider_id"])


def downgrade():
    op.drop_constraint("_mid_provider_mi_uc", "merchant_identifier", type_="unique")
