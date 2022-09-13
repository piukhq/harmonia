"""Add primary_identifier to ExportTransaction

Revision ID: b55b4026b518
Revises: f13114e488aa
Create Date: 2022-09-13 08:42:09.333045+00:00

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "b55b4026b518"
down_revision = "f13114e488aa"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("export_transaction", sa.Column("primary_identifier", sa.String(length=50), nullable=True))


def downgrade():
    op.drop_column("export_transaction", "primary_identifier")
