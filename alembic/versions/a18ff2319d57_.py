"""add user_identity table

Revision ID: a18ff2319d57
Revises: 731b1776a55d
Create Date: 2019-01-30 11:56:51.717486+00:00

"""
from alembic import op
import sqlalchemy as sa


revision = "a18ff2319d57"
down_revision = "731b1776a55d"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user_identity",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("loyalty_id", sa.String(length=250), nullable=False),
        sa.Column("scheme_account_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("credentials", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.add_column("matched_transaction", sa.Column("user_identity_id", sa.Integer(), nullable=True))
    op.create_foreign_key(None, "matched_transaction", "user_identity", ["user_identity_id"], ["id"])


def downgrade():
    op.drop_constraint(None, "matched_transaction", type_="foreignkey")
    op.drop_column("matched_transaction", "user_identity_id")
    op.drop_table("user_identity")
