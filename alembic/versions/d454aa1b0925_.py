"""add export transaction table

Revision ID: d454aa1b0925
Revises: 2e2b1afb96c2
Create Date: 2018-12-03 10:25:59.881684+00:00

"""
from alembic import op
import sqlalchemy as sa


revision = "d454aa1b0925"
down_revision = "2e2b1afb96c2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "export_transaction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("matched_transaction_id", sa.Integer(), nullable=True),
        sa.Column("transaction_id", sa.String(length=50), nullable=False),
        sa.Column("provider_slug", sa.String(length=50), nullable=False),
        sa.Column("destination", sa.String(length=500), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["matched_transaction_id"], ["matched_transaction.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_slug", "transaction_id", name="_slug_tid_et_uc"),
    )


def downgrade():
    op.drop_table("export_transaction")
