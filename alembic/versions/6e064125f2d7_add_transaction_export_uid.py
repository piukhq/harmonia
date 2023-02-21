"""add transaction export uid

Revision ID: 6e064125f2d7
Revises: 38d721f73ed2
Create Date: 2023-02-03 11:40:49.479165+00:00

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "6e064125f2d7"
down_revision = "38d721f73ed2"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("export_transaction", sa.Column("export_uid", sa.String(length=100), nullable=True, default=""))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("export_transaction", "export_uid")
    # ### end Alembic commands ###
