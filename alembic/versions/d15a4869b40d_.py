"""new fields & indices required for streaming engine

Revision ID: d15a4869b40d
Revises: 69798e5c53e4
Create Date: 2021-12-06 16:25:34.173657+00:00

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "d15a4869b40d"
down_revision = "69798e5c53e4"
branch_labels = None
depends_on = None


def upgrade():
    # new fields required for squaremeal export
    op.add_column(
        "export_transaction",
        sa.Column("feed_type", postgresql.ENUM(name="feedtype", create_type=False), nullable=True),
    )
    op.add_column("export_transaction", sa.Column("store_id", sa.String(length=50), nullable=True))
    op.add_column("export_transaction", sa.Column("brand_id", sa.String(length=50), nullable=True))
    op.add_column("export_transaction", sa.Column("payment_card_account_id", sa.Integer(), nullable=True))

    # index transaction.match_group for performance
    op.create_index(op.f("ix_transaction_match_group"), "transaction", ["match_group"], unique=False)

    # incorporate feed type into import_transaction duplicate checking
    op.add_column(
        "import_transaction",
        sa.Column("feed_type", postgresql.ENUM(name="feedtype", create_type=False), nullable=True),
    )
    op.drop_constraint("_slug_tid_it_uc", "import_transaction", type_="unique")
    op.create_unique_constraint(
        "_slug_id_feed_uc", "import_transaction", ["provider_slug", "transaction_id", "feed_type"]
    )


def downgrade():
    op.drop_constraint("_slug_id_feed_uc", "import_transaction", type_="unique")
    op.create_unique_constraint("_slug_tid_it_uc", "import_transaction", ["provider_slug", "transaction_id"])
    op.drop_column("import_transaction", "feed_type")

    op.drop_index(op.f("ix_transaction_match_group"), table_name="transaction")

    op.drop_column("export_transaction", "payment_card_account_id")
    op.drop_column("export_transaction", "brand_id")
    op.drop_column("export_transaction", "store_id")
    op.drop_column("export_transaction", "feed_type")
