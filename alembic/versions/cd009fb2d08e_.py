"""initial revision

Revision ID: cd009fb2d08e
Revises:
Create Date: 2018-08-31 09:49:04.547339+00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'cd009fb2d08e'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'import_transactions', sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('transaction_id', sa.String(length=50), nullable=False),
        sa.Column('provider_slug', sa.String(length=50), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=True), sa.Column('data', sa.JSON(), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True), sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider_slug', 'transaction_id', name='_slug_tid_uc'))
    op.create_table(
        'payment_transactions', sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider_slug', sa.String(length=50), nullable=False),
        sa.Column('mid', sa.String(length=50), nullable=False),
        sa.Column('transaction_id', sa.String(length=100), nullable=False),
        sa.Column('transaction_date', sa.DateTime(), nullable=False),
        sa.Column('spend_amount', sa.Integer(), nullable=False),
        sa.Column('spend_multiplier', sa.Integer(), nullable=False),
        sa.Column('spend_currency', sa.String(length=3), nullable=False),
        sa.Column('card_token', sa.String(length=100), nullable=True),
        sa.Column('extra_fields', sa.JSON(), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True), sa.PrimaryKeyConstraint('id'))
    op.create_table(
        'scheme_transactions', sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider_slug', sa.String(length=50), nullable=False),
        sa.Column('mid', sa.String(length=50), nullable=False),
        sa.Column('transaction_id', sa.String(length=100), nullable=False),
        sa.Column('transaction_date', sa.DateTime(), nullable=False),
        sa.Column('spend_amount', sa.Integer(), nullable=False),
        sa.Column('spend_multiplier', sa.Integer(), nullable=False),
        sa.Column('spend_currency', sa.String(length=3), nullable=False),
        sa.Column('points_amount', sa.Integer(), nullable=True),
        sa.Column('points_multiplier', sa.Integer(), nullable=True), sa.Column(
            'extra_fields', sa.JSON(), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True), sa.PrimaryKeyConstraint('id'))


def downgrade():
    op.drop_table('scheme_transactions')
    op.drop_table('payment_transactions')
    op.drop_table('import_transactions')
