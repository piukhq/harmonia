"""empty message

Revision ID: 3595a2b68d0e
Revises:
Create Date: 2018-07-13 16:03:18.445559+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3595a2b68d0e'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        'import_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.String(), nullable=True),
        sa.Column('provider_slug', sa.String(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider_slug', 'transaction_id', name='_slug_tid_uc')
    )
    op.create_table(
        'transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.String(), nullable=True),
        sa.Column('pence', sa.Integer(), nullable=True),
        sa.Column('points_earned', sa.Integer(), nullable=True),
        sa.Column('card_id', sa.String(), nullable=True),
        sa.Column('total_points', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('transactions')
    op.drop_table('import_transactions')
    # ### end Alembic commands ###
