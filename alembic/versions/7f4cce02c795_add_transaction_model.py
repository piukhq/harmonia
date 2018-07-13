"""Add transaction model

Revision ID: 7f4cce02c795
Revises:
Create Date: 2018-05-21 15:34:52.236069+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7f4cce02c795'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('hash', sa.String(), nullable=True),
        sa.Column('match_fields', sa.JSON(), nullable=True),
        sa.Column('extra_fields', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'))


def downgrade():
    op.drop_table('transactions')
