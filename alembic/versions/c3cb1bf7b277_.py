"""add merchant & payment slug to transaction table unique constraint

Revision ID: c3cb1bf7b277
Revises: fd64a9549bac
Create Date: 2024-01-23 16:36:55.776228+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c3cb1bf7b277"
down_revision = "fd64a9549bac"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("_transaction_id_feed_type_t_uc", "transaction", type_="unique")
    op.create_unique_constraint(
        "transaction_slug_id_feed_uc", "transaction", ["payment_provider_slug", "merchant_slug", "transaction_id", "feed_type"]
    )


def downgrade():
    op.drop_constraint("transaction_slug_id_feed_uc", "transaction", type_="unique")
    op.create_unique_constraint("_transaction_id_feed_type_t_uc", "transaction", ["transaction_id", "feed_type"])
