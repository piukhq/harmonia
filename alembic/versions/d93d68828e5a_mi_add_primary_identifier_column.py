"""MI_add_primary_identifier_column

Revision ID: d93d68828e5a
Revises: ba66e031b852
Create Date: 2022-08-31 08:22:43.683342+00:00

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "d93d68828e5a"
down_revision = "ba66e031b852"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("transaction", sa.Column("primary_identifier", sa.String(length=50), nullable=True))


def downgrade():
    op.drop_column("transaction", "primary_identifier")
