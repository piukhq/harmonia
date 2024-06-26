"""Relation pending transaction to export transacion

Revision ID: 4213a73dcd82
Revises: de9c08e4f432
Create Date: 2021-11-03 14:22:22.299105+00:00

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "4213a73dcd82"
down_revision = "de9c08e4f432"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("pending_export", sa.Column("export_transaction_id", sa.Integer(), nullable=True))
    op.drop_constraint("pending_export_matched_transaction_id_fkey", "pending_export", type_="foreignkey")
    op.create_foreign_key(None, "pending_export", "export_transaction", ["export_transaction_id"], ["id"])
    op.drop_column("pending_export", "matched_transaction_id")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "pending_export", sa.Column("matched_transaction_id", sa.INTEGER(), autoincrement=False, nullable=True)
    )
    op.drop_constraint("pending_export_export_transaction_id_fkey", "pending_export", type_="foreignkey")
    op.create_foreign_key(
        "pending_export_matched_transaction_id_fkey",
        "pending_export",
        "matched_transaction",
        ["matched_transaction_id"],
        ["id"],
    )
    op.drop_column("pending_export", "export_transaction_id")
    # ### end Alembic commands ###
