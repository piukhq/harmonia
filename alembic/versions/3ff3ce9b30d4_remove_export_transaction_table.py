"""remove export_transaction table

Revision ID: 3ff3ce9b30d4
Revises: 6b97a818f360
Create Date: 2021-11-01 12:14:32.260013+00:00

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "3ff3ce9b30d4"
down_revision = "6b97a818f360"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("export_transaction")


def downgrade():
    op.create_table(
        "export_transaction",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("timezone('utc'::text, CURRENT_TIMESTAMP)"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("updated_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("matched_transaction_id", sa.INTEGER(), autoincrement=False, nullable=True),
        sa.Column("transaction_id", sa.VARCHAR(length=100), autoincrement=False, nullable=False),
        sa.Column("provider_slug", sa.VARCHAR(length=50), autoincrement=False, nullable=False),
        sa.Column("destination", sa.VARCHAR(length=500), autoincrement=False, nullable=True),
        sa.Column("data", postgresql.JSON(astext_type=sa.Text()), autoincrement=False, nullable=True),
        sa.ForeignKeyConstraint(
            ["matched_transaction_id"],
            ["matched_transaction.id"],
            name="export_transaction_matched_transaction_id_fkey",
        ),
        sa.PrimaryKeyConstraint("id", name="export_transaction_pkey"),
        sa.UniqueConstraint("provider_slug", "transaction_id", name="_slug_tid_et_uc"),
    )
