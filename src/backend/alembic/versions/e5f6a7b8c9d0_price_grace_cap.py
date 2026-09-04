"""add grace_minutes and daily_cap to price_rule

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-23
"""
import sqlalchemy as sa

from alembic import op

revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("price_rule", sa.Column("grace_minutes", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("price_rule", sa.Column("daily_cap", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("price_rule", "daily_cap")
    op.drop_column("price_rule", "grace_minutes")
