"""move user identity from matched transaction into payment transaction

Revision ID: 25cea07a031e
Revises: 3ae45770fee3
Create Date: 2020-02-06 16:02:48.359415+00:00

"""
from alembic import op
import sqlalchemy as sa


revision = "25cea07a031e"
down_revision = "3ae45770fee3"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("matched_transaction", "card_token", existing_type=sa.VARCHAR(length=100), nullable=False)
    op.drop_constraint("matched_transaction_user_identity_id_fkey", "matched_transaction", type_="foreignkey")
    op.drop_column("matched_transaction", "user_identity_id")
    op.alter_column("merchant_identifier", "location", existing_type=sa.VARCHAR(length=250), nullable=False)
    op.alter_column("merchant_identifier", "postcode", existing_type=sa.VARCHAR(length=16), nullable=False)
    op.add_column("payment_transaction", sa.Column("user_identity_id", sa.Integer(), nullable=True))
    op.alter_column("payment_transaction", "card_token", existing_type=sa.VARCHAR(length=100), nullable=False)
    op.create_foreign_key(None, "payment_transaction", "user_identity", ["user_identity_id"], ["id"])


def downgrade():
    op.drop_constraint(None, "payment_transaction", type_="foreignkey")
    op.alter_column("payment_transaction", "card_token", existing_type=sa.VARCHAR(length=100), nullable=True)
    op.drop_column("payment_transaction", "user_identity_id")
    op.alter_column("merchant_identifier", "postcode", existing_type=sa.VARCHAR(length=16), nullable=True)
    op.alter_column("merchant_identifier", "location", existing_type=sa.VARCHAR(length=250), nullable=True)
    op.add_column(
        "matched_transaction", sa.Column("user_identity_id", sa.INTEGER(), autoincrement=False, nullable=True)
    )
    op.create_foreign_key(
        "matched_transaction_user_identity_id_fkey",
        "matched_transaction",
        "user_identity",
        ["user_identity_id"],
        ["id"],
    )
    op.alter_column("matched_transaction", "card_token", existing_type=sa.VARCHAR(length=100), nullable=True)
