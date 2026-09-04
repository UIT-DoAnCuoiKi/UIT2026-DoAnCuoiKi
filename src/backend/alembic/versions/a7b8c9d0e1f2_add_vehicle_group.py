"""add vehicle_group catalog

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
"""
from alembic import op
import sqlalchemy as sa

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "vehicle_group",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=16), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code", name="uq_vehicle_group_code"),
    )
    op.bulk_insert(
        sa.table(
            "vehicle_group",
            sa.column("code", sa.String),
            sa.column("display_name", sa.String),
            sa.column("sort_order", sa.Integer),
            sa.column("active", sa.Boolean),
        ),
        [
            {"code": "xe_may", "display_name": "Xe máy", "sort_order": 1, "active": True},
            {"code": "o_to_con", "display_name": "Ô tô con", "sort_order": 2, "active": True},
            {"code": "xe_tai", "display_name": "Xe tải", "sort_order": 3, "active": True},
            {"code": "xe_khach", "display_name": "Xe khách", "sort_order": 4, "active": True},
            {"code": "unknown", "display_name": "Chưa xác định", "sort_order": 99, "active": True},
        ],
    )


def downgrade() -> None:
    op.drop_table("vehicle_group")
