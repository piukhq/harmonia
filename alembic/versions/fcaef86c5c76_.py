"""intial schema

Revision ID: fcaef86c5c76
Revises:
Create Date: 2020-03-02 11:13:37.689031+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "fcaef86c5c76"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "import_transaction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("transaction_id", sa.String(length=50), nullable=False),
        sa.Column("provider_slug", sa.String(length=50), nullable=False),
        sa.Column("identified", sa.Boolean(), nullable=False),
        sa.Column("source", sa.String(length=500), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_slug", "transaction_id", name="_slug_tid_it_uc"),
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
    op.create_table(
        "scheme_transaction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("merchant_identifier_ids", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("transaction_id", sa.String(length=100), nullable=False),
        sa.Column("transaction_date", sa.DateTime(), nullable=False),
        sa.Column("spend_amount", sa.Integer(), nullable=False),
        sa.Column("spend_multiplier", sa.Integer(), nullable=False),
        sa.Column("spend_currency", sa.String(length=3), nullable=False),
        sa.Column("points_amount", sa.Integer(), nullable=True),
        sa.Column("points_multiplier", sa.Integer(), nullable=True),
        sa.Column("status", sa.Enum("PENDING", "MATCHED", name="transactionstatus"), nullable=False),
        sa.Column("extra_fields", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "user_identity",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("loyalty_id", sa.String(length=250), nullable=False),
        sa.Column("scheme_account_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("credentials", sa.Text(), nullable=False),
        sa.Column("first_six", sa.Text(), nullable=False),
        sa.Column("last_four", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "merchant_identifier",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("mid", sa.String(length=50), nullable=False),
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
        sa.UniqueConstraint("mid", "payment_provider_id", name="_mid_provider_mi_uc"),
    )
    op.create_index(op.f("ix_merchant_identifier_mid"), "merchant_identifier", ["mid"], unique=False)
    op.create_table(
        "payment_transaction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("merchant_identifier_ids", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("transaction_id", sa.String(length=100), nullable=False),
        sa.Column("transaction_date", sa.DateTime(), nullable=False),
        sa.Column("spend_amount", sa.Integer(), nullable=False),
        sa.Column("spend_multiplier", sa.Integer(), nullable=False),
        sa.Column("spend_currency", sa.String(length=3), nullable=False),
        sa.Column("card_token", sa.String(length=100), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "MATCHED", name="transactionstatus"), nullable=False),
        sa.Column("user_identity_id", sa.Integer(), nullable=True),
        sa.Column("extra_fields", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_identity_id"],
            ["user_identity.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "matched_transaction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("merchant_identifier_id", sa.Integer(), nullable=True),
        sa.Column("transaction_id", sa.String(length=100), nullable=False),
        sa.Column("transaction_date", sa.DateTime(), nullable=False),
        sa.Column("spend_amount", sa.Integer(), nullable=False),
        sa.Column("spend_multiplier", sa.Integer(), nullable=False),
        sa.Column("spend_currency", sa.String(length=3), nullable=False),
        sa.Column("points_amount", sa.Integer(), nullable=True),
        sa.Column("points_multiplier", sa.Integer(), nullable=True),
        sa.Column("card_token", sa.String(length=100), nullable=False),
        sa.Column(
            "matching_type", sa.Enum("SPOTTED", "LOYALTY", "NON_LOYALTY", "MIXED", name="matchingtype"), nullable=False
        ),
        sa.Column("status", sa.Enum("PENDING", "EXPORTED", name="matchedtransactionstatus"), nullable=False),
        sa.Column("payment_transaction_id", sa.Integer(), nullable=True),
        sa.Column("scheme_transaction_id", sa.Integer(), nullable=True),
        sa.Column("extra_fields", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(
            ["merchant_identifier_id"],
            ["merchant_identifier.id"],
        ),
        sa.ForeignKeyConstraint(
            ["payment_transaction_id"],
            ["payment_transaction.id"],
        ),
        sa.ForeignKeyConstraint(
            ["scheme_transaction_id"],
            ["scheme_transaction.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "export_transaction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("matched_transaction_id", sa.Integer(), nullable=True),
        sa.Column("transaction_id", sa.String(length=50), nullable=False),
        sa.Column("provider_slug", sa.String(length=50), nullable=False),
        sa.Column("destination", sa.String(length=500), nullable=True),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["matched_transaction_id"],
            ["matched_transaction.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_slug", "transaction_id", name="_slug_tid_et_uc"),
    )
    op.create_table(
        "pending_export",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("provider_slug", sa.String(length=50), nullable=False),
        sa.Column("matched_transaction_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["matched_transaction_id"],
            ["matched_transaction.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pending_export_provider_slug"), "pending_export", ["provider_slug"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_pending_export_provider_slug"), table_name="pending_export")
    op.drop_table("pending_export")
    op.drop_table("export_transaction")
    op.drop_table("matched_transaction")
    op.drop_table("payment_transaction")
    op.drop_index(op.f("ix_merchant_identifier_mid"), table_name="merchant_identifier")
    op.drop_table("merchant_identifier")
    op.drop_table("user_identity")
    op.drop_table("scheme_transaction")
    op.drop_table("payment_provider")
    op.drop_table("loyalty_scheme")
    op.drop_table("import_transaction")
