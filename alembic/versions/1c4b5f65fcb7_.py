"""add administrator model

Revision ID: 1c4b5f65fcb7
Revises: a18ff2319d57
Create Date: 2019-02-13 15:16:21.938262+00:00

"""
from alembic import op
import sqlalchemy as sa


revision = "1c4b5f65fcb7"
down_revision = "a18ff2319d57"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "administrator",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("uid", sa.String(length=64), nullable=False),
        sa.Column("email_address", sa.String(length=256), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("salt", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("administrator")
