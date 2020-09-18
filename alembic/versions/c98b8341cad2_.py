"""alter transaction date field to have timezone

Revision ID: c98b8341cad2
Revises: fba8c235398c
Create Date: 2020-06-10 08:05:29.339417+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c98b8341cad2"
down_revision = "fba8c235398c"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("payment_transaction", "transaction_date", type_=sa.TIMESTAMP(timezone=True))


def downgrade():
    op.alter_column("payment_transaction", "transaction_date", type_=sa.TIMESTAMP(timezone=False))
