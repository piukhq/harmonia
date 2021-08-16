"""add has_time to identify transactions which have time

Revision ID: dfd33f24559d
Revises: cc180ddc654d
Create Date: 2020-06-01 15:45:23.197244+00:00

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "dfd33f24559d"
down_revision = "cc180ddc654d"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payment_transaction", sa.Column("has_time", sa.Boolean(), nullable=True))
    op.add_column("scheme_transaction", sa.Column("has_time", sa.Boolean(), nullable=True))
    op.execute("UPDATE payment_transaction SET has_time = False")
    op.execute("UPDATE scheme_transaction SET has_time = False")
    op.alter_column("payment_transaction", "has_time", nullable=False)
    op.alter_column("scheme_transaction", "has_time", nullable=False)


def downgrade():
    op.drop_column("scheme_transaction", "has_time")
    op.drop_column("payment_transaction", "has_time")
