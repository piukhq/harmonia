"""add payment card account id

Revision ID: 7782940a86d5
Revises: d22c4e87c370
Create Date: 2021-11-17 11:47:16.735350+00:00

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "7782940a86d5"
down_revision = "d22c4e87c370"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("user_identity", sa.Column("payment_card_account_id", sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("user_identity", "payment_card_account_id")
    # ### end Alembic commands ###
