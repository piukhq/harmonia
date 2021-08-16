"""add transaction count and date range to ImportFileLog table

Revision ID: a5ed556f00e8
Revises: b7dbeeffcb2f
Create Date: 2021-03-15 09:21:52.046675+00:00

"""
import sqlalchemy as sa

from alembic import op

revision = "a5ed556f00e8"
down_revision = "b7dbeeffcb2f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("import_file_log", sa.Column("transaction_count", sa.Integer(), nullable=True))
    op.add_column("import_file_log", sa.Column("date_range_from", sa.DateTime(), nullable=True))
    op.add_column("import_file_log", sa.Column("date_range_to", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("import_file_log", "date_range_to")
    op.drop_column("import_file_log", "date_range_from")
    op.drop_column("import_file_log", "transaction_count")
