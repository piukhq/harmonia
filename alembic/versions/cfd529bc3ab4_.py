"""alter scheme transaction to store timezone information

Revision ID: cfd529bc3ab4
Revises: c98b8341cad2
Create Date: 2020-06-15 15:40:46.837981+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "cfd529bc3ab4"
down_revision = "c98b8341cad2"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("scheme_transaction", "transaction_date", type_=sa.TIMESTAMP(timezone=True))


def downgrade():
    op.alter_column("scheme_transaction", "transaction_date", type_=sa.TIMESTAMP(timezone=False))
