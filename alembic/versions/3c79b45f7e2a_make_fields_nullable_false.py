"""make fields nullable=False

Revision ID: 3c79b45f7e2a
Revises: 5477ff60b0b3
Create Date: 2022-12-21 15:39:04.190057+00:00

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "3c79b45f7e2a"
down_revision = "5477ff60b0b3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "config_item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_config_item_key"), "config_item", ["key"], unique=True)
    op.create_table(
        "export_transaction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("transaction_id", sa.String(length=100), nullable=False),
        sa.Column("feed_type", sa.Enum("MERCHANT", "AUTH", "SETTLED", "REFUND", name="feedtype"), nullable=True),
        sa.Column("provider_slug", sa.String(length=50), nullable=False),
        sa.Column("transaction_date", sa.DateTime(), nullable=False),
        sa.Column("spend_amount", sa.Integer(), nullable=False),
        sa.Column("spend_currency", sa.String(length=3), nullable=False),
        sa.Column("loyalty_id", sa.String(length=100), nullable=False),
        sa.Column("mid", sa.String(length=50), nullable=False),
        sa.Column("primary_identifier", sa.String(length=50), nullable=False),
        sa.Column("location_id", sa.String(length=50), nullable=True),
        sa.Column("merchant_internal_id", sa.String(length=50), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("scheme_account_id", sa.Integer(), nullable=False),
        sa.Column("payment_card_account_id", sa.Integer(), nullable=True),
        sa.Column("credentials", sa.Text(), nullable=False),
        sa.Column("auth_code", sa.String(length=20), nullable=False),
        sa.Column("approval_code", sa.String(length=20), nullable=False),
        sa.Column(
            "status", sa.Enum("PENDING", "EXPORTED", "EXPORT_FAILED", name="exporttransactionstatus"), nullable=False
        ),
        sa.Column("settlement_key", sa.String(length=100), nullable=True),
        sa.Column("last_four", sa.String(length=4), nullable=True),
        sa.Column("expiry_month", sa.Integer(), nullable=True),
        sa.Column("expiry_year", sa.Integer(), nullable=True),
        sa.Column("payment_provider_slug", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "file_sequence_number",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("provider_slug", sa.String(length=50), nullable=False),
        sa.Column("next_value", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_file_sequence_number_provider_slug"), "file_sequence_number", ["provider_slug"], unique=False
    )
    op.create_table(
        "import_file_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("provider_slug", sa.String(length=50), nullable=False),
        sa.Column("file_name", sa.String(length=500), nullable=False),
        sa.Column("imported", sa.Boolean(), nullable=False),
        sa.Column("date_range_from", sa.DateTime(), nullable=True),
        sa.Column("date_range_to", sa.DateTime(), nullable=True),
        sa.Column("transaction_count", sa.Integer(), nullable=True),
        sa.Column("unique_transaction_count", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "import_transaction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("transaction_id", sa.String(length=100), nullable=False),
        sa.Column("feed_type", sa.Enum("MERCHANT", "AUTH", "SETTLED", "REFUND", name="feedtype"), nullable=False),
        sa.Column("provider_slug", sa.String(length=50), nullable=False),
        sa.Column("identified", sa.Boolean(), nullable=False),
        sa.Column("match_group", sa.String(length=36), nullable=False),
        sa.Column("source", sa.String(length=500), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_slug", "transaction_id", "feed_type", name="_slug_id_feed_uc"),
    )
    op.create_table(
        "loyalty_scheme",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_loyalty_scheme_slug"), "loyalty_scheme", ["slug"], unique=True)
    op.create_table(
        "payment_provider",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payment_provider_slug"), "payment_provider", ["slug"], unique=True)
    op.create_table(
        "payment_transaction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("merchant_identifier_ids", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("primary_identifier", sa.String(length=50), nullable=False),
        sa.Column("provider_slug", sa.String(length=50), nullable=False),
        sa.Column("transaction_id", sa.String(length=100), nullable=False),
        sa.Column("settlement_key", sa.String(length=100), nullable=True),
        sa.Column("transaction_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("has_time", sa.Boolean(), nullable=False),
        sa.Column("spend_amount", sa.Integer(), nullable=False),
        sa.Column("spend_multiplier", sa.Integer(), nullable=False),
        sa.Column("spend_currency", sa.String(length=3), nullable=False),
        sa.Column("card_token", sa.String(length=100), nullable=False),
        sa.Column("first_six", sa.Text(), nullable=True),
        sa.Column("last_four", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PENDING", "IMPORTED", "MATCHED", "EXPORTED", "EXPORT_FAILED", name="transactionstatus"),
            nullable=False,
        ),
        sa.Column("auth_code", sa.String(length=20), nullable=False),
        sa.Column("approval_code", sa.String(length=20), nullable=False),
        sa.Column("match_group", sa.String(length=36), nullable=False),
        sa.Column("extra_fields", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payment_transaction_match_group"), "payment_transaction", ["match_group"], unique=False)
    op.create_index(
        op.f("ix_payment_transaction_settlement_key"), "payment_transaction", ["settlement_key"], unique=False
    )
    op.create_table(
        "scheme_transaction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("merchant_identifier_ids", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("primary_identifier", sa.String(length=50), nullable=False),
        sa.Column("provider_slug", sa.String(length=50), nullable=False),
        sa.Column("payment_provider_slug", sa.String(length=50), nullable=False),
        sa.Column("transaction_id", sa.String(length=100), nullable=False),
        sa.Column("transaction_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("has_time", sa.Boolean(), nullable=False),
        sa.Column("spend_amount", sa.Integer(), nullable=False),
        sa.Column("spend_multiplier", sa.Integer(), nullable=False),
        sa.Column("spend_currency", sa.String(length=3), nullable=False),
        sa.Column("first_six", sa.Text(), nullable=True),
        sa.Column("last_four", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PENDING", "IMPORTED", "MATCHED", "EXPORTED", "EXPORT_FAILED", name="transactionstatus"),
            nullable=False,
        ),
        sa.Column("auth_code", sa.String(length=20), nullable=False),
        sa.Column("match_group", sa.String(length=36), nullable=False),
        sa.Column("extra_fields", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scheme_transaction_match_group"), "scheme_transaction", ["match_group"], unique=False)
    op.create_index(
        op.f("ix_scheme_transaction_transaction_date"), "scheme_transaction", ["transaction_date"], unique=False
    )
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
        sa.Column("primary_identifier", sa.String(length=50), nullable=False),
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
        sa.Column("approval_code", sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_id", "feed_type", name="_transaction_id_feed_type_t_uc"),
    )
    op.create_index(op.f("ix_transaction_match_group"), "transaction", ["match_group"], unique=False)
    op.create_index(op.f("ix_transaction_settlement_key"), "transaction", ["settlement_key"], unique=False)
    op.create_table(
        "user_identity",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("transaction_id", sa.String(), nullable=False),
        sa.Column("loyalty_id", sa.String(length=250), nullable=False),
        sa.Column("scheme_account_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("credentials", sa.Text(), nullable=False),
        sa.Column("first_six", sa.Text(), nullable=False),
        sa.Column("last_four", sa.Text(), nullable=False),
        sa.Column("payment_card_account_id", sa.Integer(), nullable=True),
        sa.Column("expiry_month", sa.Integer(), nullable=True),
        sa.Column("expiry_year", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_identity_transaction_id"), "user_identity", ["transaction_id"], unique=False)
    op.create_table(
        "merchant_identifier",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("identifier", sa.String(length=50), nullable=False),
        sa.Column("identifier_type", sa.Enum("PRIMARY", "SECONDARY", "PSIMI", name="identifiertype"), nullable=False),
        sa.Column("location_id", sa.String(length=50), nullable=True),
        sa.Column("merchant_internal_id", sa.String(length=50), nullable=True),
        sa.Column("loyalty_scheme_id", sa.Integer(), nullable=True),
        sa.Column("payment_provider_id", sa.Integer(), nullable=True),
        sa.Column("location", sa.String(length=250), nullable=False),
        sa.Column("postcode", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(
            ["loyalty_scheme_id"],
            ["loyalty_scheme.id"],
        ),
        sa.ForeignKeyConstraint(
            ["payment_provider_id"],
            ["payment_provider.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "identifier", "identifier_type", "payment_provider_id", name="_identifier_type_provider_mi_uc"
        ),
    )
    op.create_table(
        "pending_export",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("provider_slug", sa.String(length=50), nullable=False),
        sa.Column("export_transaction_id", sa.Integer(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("retry_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["export_transaction_id"],
            ["export_transaction.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pending_export_provider_slug"), "pending_export", ["provider_slug"], unique=False)
    op.create_index(op.f("ix_pending_export_retry_at"), "pending_export", ["retry_at"], unique=False)
    op.create_table(
        "matched_transaction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("merchant_identifier_id", sa.Integer(), nullable=True),
        sa.Column("primary_identifier", sa.String(length=50), nullable=False),
        sa.Column("transaction_id", sa.String(length=100), nullable=False),
        sa.Column("transaction_date", sa.DateTime(), nullable=False),
        sa.Column("spend_amount", sa.Integer(), nullable=False),
        sa.Column("spend_multiplier", sa.Integer(), nullable=False),
        sa.Column("spend_currency", sa.String(length=3), nullable=False),
        sa.Column("card_token", sa.String(length=100), nullable=False),
        sa.Column(
            "matching_type",
            sa.Enum("SPOTTED", "LOYALTY", "NON_LOYALTY", "MIXED", "FORCED", name="matchingtype"),
            nullable=False,
        ),
        sa.Column(
            "status", sa.Enum("PENDING", "EXPORTED", "EXPORT_FAILED", name="matchedtransactionstatus"), nullable=False
        ),
        sa.Column("extra_fields", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["merchant_identifier_id"],
            ["merchant_identifier.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("matched_transaction")
    op.drop_index(op.f("ix_pending_export_retry_at"), table_name="pending_export")
    op.drop_index(op.f("ix_pending_export_provider_slug"), table_name="pending_export")
    op.drop_table("pending_export")
    op.drop_table("merchant_identifier")
    op.drop_index(op.f("ix_user_identity_transaction_id"), table_name="user_identity")
    op.drop_table("user_identity")
    op.drop_index(op.f("ix_transaction_settlement_key"), table_name="transaction")
    op.drop_index(op.f("ix_transaction_match_group"), table_name="transaction")
    op.drop_table("transaction")
    op.drop_index(op.f("ix_scheme_transaction_transaction_date"), table_name="scheme_transaction")
    op.drop_index(op.f("ix_scheme_transaction_match_group"), table_name="scheme_transaction")
    op.drop_table("scheme_transaction")
    op.drop_index(op.f("ix_payment_transaction_settlement_key"), table_name="payment_transaction")
    op.drop_index(op.f("ix_payment_transaction_match_group"), table_name="payment_transaction")
    op.drop_table("payment_transaction")
    op.drop_index(op.f("ix_payment_provider_slug"), table_name="payment_provider")
    op.drop_table("payment_provider")
    op.drop_index(op.f("ix_loyalty_scheme_slug"), table_name="loyalty_scheme")
    op.drop_table("loyalty_scheme")
    op.drop_table("import_transaction")
    op.drop_table("import_file_log")
    op.drop_index(op.f("ix_file_sequence_number_provider_slug"), table_name="file_sequence_number")
    op.drop_table("file_sequence_number")
    op.drop_table("export_transaction")
    op.drop_index(op.f("ix_config_item_key"), table_name="config_item")
    op.drop_table("config_item")
