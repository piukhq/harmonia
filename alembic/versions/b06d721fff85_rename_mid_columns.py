"""rename MID columns: store_id -> location_id, brand_id -> merchant_internal_id

Revision ID: b06d721fff85
Revises: d15a4869b40d
Create Date: 2022-03-15 11:55:16.433006+00:00

"""
from alembic import op

revision = "b06d721fff85"
down_revision = "d15a4869b40d"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("export_transaction", "store_id", new_column_name="location_id")
    op.alter_column("export_transaction", "brand_id", new_column_name="merchant_internal_id")
    op.alter_column("merchant_identifier", "store_id", new_column_name="location_id")
    op.alter_column("merchant_identifier", "brand_id", new_column_name="merchant_internal_id")


def downgrade():
    op.alter_column("export_transaction", "location_id", new_column_name="store_id")
    op.alter_column("export_transaction", "merchant_internal_id", new_column_name="brand_id")
    op.alter_column("merchant_identifier", "location_id", new_column_name="store_id")
    op.alter_column("merchant_identifier", "merchant_internal_id", new_column_name="brand_id")
