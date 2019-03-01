"""initial revision

Revision ID: 01918d55a507
Revises:
Create Date: 2018-10-22 13:32:00.893504+00:00

"""
from alembic import op
import sqlalchemy as sa

revision = "01918d55a507"
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
        "merchant_identifier",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.text("TIMEZONE('utc', CURRENT_TIMESTAMP)"), nullable=True
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("mid", sa.String(length=50), nullable=False),
        sa.Column("loyalty_scheme_id", sa.Integer(), nullable=True),
        sa.Column("payment_provider_id", sa.Integer(), nullable=True),
        sa.Column("location", sa.String(length=250), nullable=True),
        sa.Column("postcode", sa.String(length=16), nullable=True),
        sa.ForeignKeyConstraint(["loyalty_scheme_id"], ["loyalty_scheme.id"]),
        sa.ForeignKeyConstraint(["payment_provider_id"], ["payment_provider.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_merchant_identifier_mid"), "merchant_identifier", ["mid"], unique=False)
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
        sa.Column("card_token", sa.String(length=100), nullable=True),
        sa.Column(
            "matching_type", sa.Enum("SPOTTED", "LOYALTY", "NON_LOYALTY", "MIXED", name="matchingtype"), nullable=False
        ),
        sa.Column("extra_fields", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["merchant_identifier_id"], ["merchant_identifier.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "payment_transaction",
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
        sa.Column("card_token", sa.String(length=100), nullable=True),
        sa.Column("extra_fields", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["merchant_identifier_id"], ["merchant_identifier.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "scheme_transaction",
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
        sa.Column("extra_fields", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["merchant_identifier_id"], ["merchant_identifier.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("scheme_transaction")
    op.drop_table("payment_transaction")
    op.drop_table("matched_transaction")
    op.drop_index(op.f("ix_merchant_identifier_mid"), table_name="merchant_identifier")
    op.drop_table("merchant_identifier")
    op.drop_table("payment_provider")
    op.drop_table("loyalty_scheme")
    op.drop_table("import_transaction")
    sa.Enum(name="matchingtype").drop(op.get_bind())
