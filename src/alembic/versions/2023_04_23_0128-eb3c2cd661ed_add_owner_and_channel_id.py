"""Add owner and channel_id

Revision ID: eb3c2cd661ed
Revises: 9766d92172fb
Create Date: 2023-04-23 01:28:17.886014

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "eb3c2cd661ed"
down_revision = "9766d92172fb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column(
        "submission_criterion", sa.Column("owner_id", sa.BigInteger(), nullable=False)
    )
    op.add_column(
        "submission_criterion", sa.Column("channel_id", sa.BigInteger(), nullable=False)
    )

    op.create_foreign_key(
        "fk__owner", "submission_criterion", "user", ["owner_id"], ["id"]
    )


def downgrade() -> None:
    op.drop_constraint("fk__owner", "submission_criterion", type_="foreignkey")

    op.drop_column("submission_criterion", "channel_id")
    op.drop_column("submission_criterion", "owner_id")

    op.drop_table("user")
