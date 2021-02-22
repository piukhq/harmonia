"""add import file log table

Revision ID: 1090a4d58a2a
Revises: d38f82ac2182
Create Date: 2020-11-19 11:55:10.605902+00:00

"""
from alembic import op
import sqlalchemy as sa


revision = "1090a4d58a2a"
down_revision = "d38f82ac2182"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "import_file_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("provider_slug", sa.String(length=50), nullable=False),
        sa.Column("file_name", sa.String(length=500), nullable=False),
        sa.Column("imported", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("import_file_log")
