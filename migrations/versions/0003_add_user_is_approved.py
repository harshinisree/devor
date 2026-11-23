"""add users.is_approved

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_approved", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    # Backfill: customers and admins never need approval.
    op.execute("UPDATE users SET is_approved = true WHERE role IN ('customer', 'admin')")


def downgrade() -> None:
    op.drop_column("users", "is_approved")
