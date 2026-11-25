"""create restaurants table

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "restaurants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("cuisine", sa.String(length=50), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("is_open", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name="fk_restaurants_owner_id_users"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_restaurants")),
    )
    op.create_index(
        "ix_restaurants_is_open_cuisine", "restaurants", ["is_open", "cuisine"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_restaurants_is_open_cuisine", table_name="restaurants")
    op.drop_table("restaurants")
