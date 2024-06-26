"""add settlement key to export_transaction

Revision ID: 663e08279b0d
Revises: b06d721fff85
Create Date: 2022-03-22 17:03:53.307053+00:00

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "663e08279b0d"
down_revision = "b06d721fff85"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("export_transaction", sa.Column("settlement_key", sa.String(length=100), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("export_transaction", "settlement_key")
    # ### end Alembic commands ###
