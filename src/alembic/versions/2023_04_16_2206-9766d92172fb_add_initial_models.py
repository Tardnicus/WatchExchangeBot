"""Add initial models

Revision ID: 9766d92172fb
Revises:
Create Date: 2023-04-16 22:06:38.727112

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9766d92172fb"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "processed_submission",
        sa.Column("id", sa.String(), autoincrement=False, nullable=False),
        sa.Column("date_processed", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "submission_criterion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "submission_type",
            sa.Enum("WTB", "WTS", name="submissiontype"),
            nullable=False,
        ),
        sa.Column("min_transactions", sa.Integer(), nullable=False),
        sa.Column("all_required", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "keyword",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("criterion_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["criterion_id"],
            ["submission_criterion.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("keyword")
    op.drop_table("submission_criterion")
    op.drop_table("processed_submission")
