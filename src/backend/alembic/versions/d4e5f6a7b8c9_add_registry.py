"""add vehicle_owner, monthly_pass, plate_whitelist, plate_blacklist

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-23
"""
import sqlalchemy as sa

from alembic import op

revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def _plate_list(name: str) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plate_hash", sa.String(length=64), nullable=False),
        sa.Column("plate_ciphertext", sa.String(length=512), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(f"ix_{name}_plate_hash", name, ["plate_hash"])


def upgrade() -> None:
    op.create_table(
        "vehicle_owner",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("plate_hash", sa.String(length=64), nullable=False),
        sa.Column("plate_ciphertext", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_vehicle_owner_plate_hash", "vehicle_owner", ["plate_hash"])
    op.create_table(
        "monthly_pass",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("vehicle_owner.id"), nullable=True),
        sa.Column("plate_hash", sa.String(length=64), nullable=False),
        sa.Column("plate_ciphertext", sa.String(length=512), nullable=False),
        sa.Column("vehicle_group", sa.String(length=16), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_monthly_pass_plate_hash", "monthly_pass", ["plate_hash"])
    _plate_list("plate_whitelist")
    _plate_list("plate_blacklist")


def downgrade() -> None:
    op.drop_table("plate_blacklist")
    op.drop_table("plate_whitelist")
    op.drop_table("monthly_pass")
    op.drop_table("vehicle_owner")
