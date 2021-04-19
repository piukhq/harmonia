"""add optional (dpan) f6/l4 to payment transaction

Revision ID: b723a8757024
Revises: a5ed556f00e8
Create Date: 2021-04-12 15:47:00.973768+00:00

"""
from alembic import op
import sqlalchemy as sa


revision = "b723a8757024"
down_revision = "a5ed556f00e8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payment_transaction", sa.Column("first_six", sa.Text(), nullable=True))
    op.add_column("payment_transaction", sa.Column("last_four", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("payment_transaction", "last_four")
    op.drop_column("payment_transaction", "first_six")
