"""add pending export table

Revision ID: 2e2b1afb96c2
Revises: 2cd4f2cb0d39
Create Date: 2018-11-27 12:07:42.335692+00:00

"""
from alembic import op
import sqlalchemy as sa

revision = "2e2b1afb96c2"
down_revision = "2cd4f2cb0d39"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pending_export",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("provider_slug", sa.String(length=50), nullable=False),
        sa.Column("matched_transaction_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["matched_transaction_id"], ["matched_transaction.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pending_export_provider_slug"), "pending_export", ["provider_slug"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_pending_export_provider_slug"), table_name="pending_export")
    op.drop_table("pending_export")
