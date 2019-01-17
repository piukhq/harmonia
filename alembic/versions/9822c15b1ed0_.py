"""add user_identity table

Revision ID: 9822c15b1ed0
Revises: 731b1776a55d
Create Date: 2019-01-16 14:53:20.329173+00:00

"""
from alembic import op
import sqlalchemy as sa


revision = "9822c15b1ed0"
down_revision = "731b1776a55d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_identity",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("loyalty_id", sa.String(length=250), nullable=False),
        sa.Column("scheme_account_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("credentials", sa.Text(), nullable=False),
        sa.Column("matched_transaction_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["matched_transaction_id"], ["matched_transaction.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("user_identity")
