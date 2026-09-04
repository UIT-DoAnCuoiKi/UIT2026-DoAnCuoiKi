"""add parking_lot, floor, zone and session lot/zone fk

Revision ID: a1b2c3d4e5f6
Revises: 0b0007c4dc28
Create Date: 2026-08-23
"""
import sqlalchemy as sa

from alembic import op

revision = "a1b2c3d4e5f6"
down_revision = "0b0007c4dc28"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parking_lot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("address", sa.String(length=256), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "floor",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lot_id", sa.Integer(), sa.ForeignKey("parking_lot.id"), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_table(
        "zone",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lot_id", sa.Integer(), sa.ForeignKey("parking_lot.id"), nullable=False),
        sa.Column("floor_id", sa.Integer(), sa.ForeignKey("floor.id"), nullable=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column("session", sa.Column("lot_id", sa.Integer(), sa.ForeignKey("parking_lot.id"), nullable=True))
    op.add_column("session", sa.Column("zone_id", sa.Integer(), sa.ForeignKey("zone.id"), nullable=True))


def downgrade() -> None:
    op.drop_column("session", "zone_id")
    op.drop_column("session", "lot_id")
    op.drop_table("zone")
    op.drop_table("floor")
    op.drop_table("parking_lot")
