"""make primary_identifier field not nullable

Revision ID: 3544cc4e8e2e
Revises: 76de66565f46
Create Date: 2022-09-30 11:11:54.990694+00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3544cc4e8e2e'
down_revision = '76de66565f46'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column('export_transaction', 'primary_identifier',
               existing_type=sa.VARCHAR(length=50),
               nullable=False)
    op.alter_column('matched_transaction', 'primary_identifier',
               existing_type=sa.VARCHAR(length=50),
               nullable=False)
    op.alter_column('payment_transaction', 'primary_identifier',
               existing_type=sa.VARCHAR(length=50),
               nullable=False)
    op.alter_column('scheme_transaction', 'primary_identifier',
               existing_type=sa.VARCHAR(length=50),
               nullable=False)
    op.alter_column('transaction', 'primary_identifier',
               existing_type=sa.VARCHAR(length=50),
               nullable=False)


def downgrade():
    op.alter_column('transaction', 'primary_identifier',
               existing_type=sa.VARCHAR(length=50),
               nullable=True)
    op.alter_column('scheme_transaction', 'primary_identifier',
               existing_type=sa.VARCHAR(length=50),
               nullable=True)
    op.alter_column('payment_transaction', 'primary_identifier',
               existing_type=sa.VARCHAR(length=50),
               nullable=True)
    op.alter_column('matched_transaction', 'primary_identifier',
               existing_type=sa.VARCHAR(length=50),
               nullable=True)
    op.alter_column('export_transaction', 'primary_identifier',
               existing_type=sa.VARCHAR(length=50),
               nullable=True)
