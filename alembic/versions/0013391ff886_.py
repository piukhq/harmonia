"""add retry count & date to export transaction table. add EXPORT_FAILED status to matched transaction status enum.

Revision ID: 0013391ff886
Revises: 1090a4d58a2a
Create Date: 2020-12-08 13:47:56.986687+00:00

"""
import sqlalchemy as sa

from alembic import op

revision = "0013391ff886"
down_revision = "1090a4d58a2a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("pending_export", sa.Column("retry_count", sa.Integer(), nullable=True))
    op.execute("UPDATE pending_export SET retry_count = 0")
    op.alter_column("pending_export", "retry_count", nullable=False)

    op.add_column("pending_export", sa.Column("retry_at", sa.DateTime(), nullable=True, index=True))

    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE matchedtransactionstatus ADD VALUE IF NOT EXISTS 'EXPORT_FAILED'")


def downgrade():
    op.drop_column("pending_export", "retry_at")
    op.drop_column("pending_export", "retry_count")

    # WRT matchedtransactionstatus::EXPORT_FAILED
    # enum values cannot be removed without dropping & recreating the enum type
    # leaving it in the enum will not break anything should we ever downgrade this revision
