"""remove points_amount and points_multiplier

Revision ID: fba8c235398c
Revises: dfd33f24559d
Create Date: 2020-06-09 09:55:22.670965+00:00

"""
import sqlalchemy as sa

from alembic import op

revision = "fba8c235398c"
down_revision = "dfd33f24559d"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("matched_transaction", "points_amount")
    op.drop_column("matched_transaction", "points_multiplier")
    op.drop_column("scheme_transaction", "points_amount")
    op.drop_column("scheme_transaction", "points_multiplier")


def downgrade():
    op.add_column(
        "scheme_transaction", sa.Column("points_multiplier", sa.INTEGER(), autoincrement=False, nullable=True)
    )
    op.add_column("scheme_transaction", sa.Column("points_amount", sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column(
        "matched_transaction", sa.Column("points_multiplier", sa.INTEGER(), autoincrement=False, nullable=True)
    )
    op.add_column("matched_transaction", sa.Column("points_amount", sa.INTEGER(), autoincrement=False, nullable=True))
