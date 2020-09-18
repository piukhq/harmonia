"""add store_id to merchant identifier

Revision ID: dd1520e937b8
Revises: cfd529bc3ab4
Create Date: 2020-09-14 11:41:29.173832+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "dd1520e937b8"
down_revision = "cfd529bc3ab4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("merchant_identifier", sa.Column("store_id", sa.String(length=50), nullable=True))


def downgrade():
    op.drop_column("merchant_identifier", "store_id")
