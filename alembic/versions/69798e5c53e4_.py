"""add transaction model and status fields, rename user_identity.settlement_key to user_identity.transaction_id

Revision ID: 69798e5c53e4
Revises: d22c4e87c370
Create Date: 2021-11-17 16:25:08.027415+00:00

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "69798e5c53e4"
down_revision = "7782940a86d5"
branch_labels = None
depends_on = None


def upgrade():
    # add transaction model
    op.create_table(
        "transaction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("feed_type", sa.Enum("MERCHANT", "AUTH", "SETTLED", "REFUND", name="feedtype"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "IMPORTED", "MATCHED", "EXPORTED", "EXPORT_FAILED", name="transactionstatus"),
            nullable=False,
        ),
        sa.Column("merchant_identifier_ids", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("merchant_slug", sa.String(length=50), nullable=False),
        sa.Column("payment_provider_slug", sa.String(length=50), nullable=False),
        sa.Column("transaction_id", sa.String(length=100), nullable=False),
        sa.Column("settlement_key", sa.String(length=100), nullable=True),
        sa.Column("match_group", sa.String(length=36), nullable=False),
        sa.Column("transaction_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("has_time", sa.Boolean(), nullable=False),
        sa.Column("spend_amount", sa.Integer(), nullable=False),
        sa.Column("spend_multiplier", sa.Integer(), nullable=False),
        sa.Column("spend_currency", sa.String(length=3), nullable=False),
        sa.Column("card_token", sa.String(length=100), nullable=True),
        sa.Column("first_six", sa.Text(), nullable=True),
        sa.Column("last_four", sa.Text(), nullable=True),
        sa.Column("auth_code", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_id", "feed_type", name="_transaction_id_feed_type_t_uc"),
    )
    op.create_index(op.f("ix_transaction_settlement_key"), "transaction", ["settlement_key"], unique=False)

    # alter transactionstatus enum with new fields
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE transactionstatus RENAME TO transactionstatus_old")
        op.execute(
            "CREATE TYPE transactionstatus AS ENUM('PENDING', 'IMPORTED', 'MATCHED', 'EXPORTED', 'EXPORT_FAILED')"
        )
        op.execute(
            "ALTER TABLE transaction "
            "ALTER COLUMN status "
            "TYPE transactionstatus "
            "USING status::text::transactionstatus"
        )
        op.execute(
            "ALTER TABLE scheme_transaction "
            "ALTER COLUMN status "
            "TYPE transactionstatus "
            "USING status::text::transactionstatus"
        )
        op.execute(
            "ALTER TABLE payment_transaction "
            "ALTER COLUMN status "
            "TYPE transactionstatus "
            "USING status::text::transactionstatus"
        )
        op.execute("DROP TYPE transactionstatus_old")

    # rename user_identity.settlement_key to user_identity.transaction_id
    op.drop_index("ix_user_identity_settlement_key", table_name="user_identity")
    op.alter_column("user_identity", "settlement_key", new_column_name="transaction_id")
    op.create_index(op.f("ix_user_identity_transaction_id"), "user_identity", ["transaction_id"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_transaction_settlement_key"), table_name="transaction")
    op.drop_table("transaction")

    # rename user_identity.transaction_id to user_identity.settlement_key
    op.drop_index(op.f("ix_user_identity_transaction_id"), table_name="user_identity")
    op.alter_column("user_identity", "transaction_id", new_column_name="settlement_key")
    op.create_index("ix_user_identity_settlement_key", "user_identity", ["settlement_key"], unique=False)
