"""increase import_transaction.transaction_id and export_transaction.transaction_id field length to 100

Revision ID: 454727e1a85e
Revises: b63ca0388cfc
Create Date: 2021-04-28 10:34:03.499410+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "454727e1a85e"
down_revision = "b63ca0388cfc"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "import_transaction",
        "transaction_id",
        existing_type=sa.String(length=50),
        type_=sa.String(length=100),
        existing_nullable=False,
    )
    op.alter_column(
        "export_transaction",
        "transaction_id",
        existing_type=sa.String(length=50),
        type_=sa.String(length=100),
        existing_nullable=False,
    )


def downgrade():
    op.alter_column(
        "import_transaction",
        "transaction_id",
        existing_type=sa.String(length=100),
        type_=sa.String(length=50),
        existing_nullable=False,
    )
    op.alter_column(
        "export_transaction",
        "transaction_id",
        existing_type=sa.String(length=100),
        type_=sa.String(length=50),
        existing_nullable=False,
    )
