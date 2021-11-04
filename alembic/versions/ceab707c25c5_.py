"""replace user id payment card foreign key with indexed transaction ID

Revision ID: ceab707c25c5
Revises: 6b97a818f360
Create Date: 2021-11-01 15:04:39.543438+00:00

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "ceab707c25c5"
down_revision = "4213a73dcd82"
branch_labels = None
depends_on = None


FOREIGN_KEY_TO_TXID = """
UPDATE user_identity SET settlement_key =
   (SELECT settlement_key FROM payment_transaction where payment_transaction.user_identity_id = user_identity.id)
"""

TXID_TO_FOREIGN_KEY = """
UPDATE payment_transaction SET user_identity_id =
   (SELECT id FROM user_identity where user_identity.settlement_key = payment_transaction.settlement_key)
"""


def upgrade():
    op.drop_constraint("payment_transaction_user_identity_id_fkey", "payment_transaction", type_="foreignkey")
    op.add_column("user_identity", sa.Column("settlement_key", sa.String(), nullable=True))
    op.execute(FOREIGN_KEY_TO_TXID)
    op.alter_column("user_identity", "settlement_key", nullable=False)
    op.drop_column("payment_transaction", "user_identity_id")
    op.create_index(op.f("ix_user_identity_settlement_key"), "user_identity", ["settlement_key"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_user_identity_settlement_key"), table_name="user_identity")
    op.add_column(
        "payment_transaction", sa.Column("user_identity_id", sa.INTEGER(), autoincrement=False, nullable=True)
    )
    op.execute(TXID_TO_FOREIGN_KEY)
    op.drop_column("user_identity", "settlement_key")
    op.create_foreign_key(
        "payment_transaction_user_identity_id_fkey",
        "payment_transaction",
        "user_identity",
        ["user_identity_id"],
        ["id"],
    )
