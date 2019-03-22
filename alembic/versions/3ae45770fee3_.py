"""delete administrator model

Revision ID: 3ae45770fee3
Revises: a39cd4ddfaa9
Create Date: 2019-03-22 14:37:46.013341+00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "3ae45770fee3"
down_revision = "a39cd4ddfaa9"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("administrator")


def downgrade():
    op.create_table(
        "administrator",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(),
            server_default=sa.text("timezone('utc'::text, CURRENT_TIMESTAMP)"),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("updated_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
        sa.Column("uid", sa.VARCHAR(length=64), autoincrement=False, nullable=False),
        sa.Column("email_address", sa.VARCHAR(length=256), autoincrement=False, nullable=False),
        sa.Column("password_hash", sa.TEXT(), autoincrement=False, nullable=False),
        sa.Column("salt", sa.VARCHAR(length=64), autoincrement=False, nullable=False),
        sa.Column("is_active", sa.BOOLEAN(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint("id", name="administrator_pkey"),
    )
