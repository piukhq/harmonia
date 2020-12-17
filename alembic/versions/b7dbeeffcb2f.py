"""add table to persist running config

Revision ID: b7dbeeffcb2f
Revises: 0013391ff886
Create Date: 2020-12-15 13:57:34.440542+00:00

"""
from alembic import op
import sqlalchemy as sa

from app import config


revision = "b7dbeeffcb2f"
down_revision = "0013391ff886"
branch_labels = None
depends_on = None


def upgrade():
    table = op.create_table(
        "config_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_config_item_key"), "config_item", ["key"], unique=True)

    op.bulk_insert(table, [{"key": k, "value": v} for k, v in config.all_keys()])


def downgrade():
    op.drop_index(op.f("ix_config_item_key"), table_name="config_item")
    op.drop_table("config_item")
