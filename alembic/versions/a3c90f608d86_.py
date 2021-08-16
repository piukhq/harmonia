"""add file sequence number table

Revision ID: a3c90f608d86
Revises: fcaef86c5c76
Create Date: 2020-03-11 09:20:48.270844+00:00

"""
import sqlalchemy as sa

from alembic import op

revision = "a3c90f608d86"
down_revision = "fcaef86c5c76"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "file_sequence_number",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("provider_slug", sa.String(length=50), nullable=False),
        sa.Column("next_value", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_file_sequence_number_provider_slug"), "file_sequence_number", ["provider_slug"], unique=False
    )


def downgrade():
    op.drop_index(op.f("ix_file_sequence_number_provider_slug"), table_name="file_sequence_number")
    op.drop_table("file_sequence_number")
