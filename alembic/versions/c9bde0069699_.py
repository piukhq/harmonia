"""add FORCED to the enum of matching types

Revision ID: c9bde0069699
Revises: cfd529bc3ab4
Create Date: 2020-08-24 13:47:48.752984+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c9bde0069699"
down_revision = "cfd529bc3ab4"
branch_labels = None
depends_on = None


def upgrade():
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE matchingtype ADD VALUE IF NOT EXISTS 'FORCED'")


def downgrade():
    # enum values cannot be removed without dropping & recreating the enum type
    # leaving it in the enum will not break anything should we ever downgrade this revision
    pass
