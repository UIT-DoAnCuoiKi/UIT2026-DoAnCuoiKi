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
    # batch_alter_table: SQLite không ALTER được constraint, thêm cột kèm khóa
    # ngoại trực tiếp sẽ chết. Batch mode copy-and-move xử lý được, còn trên
    # PostgreSQL alembic vẫn phát ra ALTER TABLE thường nên hành vi không đổi.
    # Batch mode của SQLite bắt buộc constraint phải có tên (không tự sinh được
    # khi build lại bảng), nên đặt tên tường minh cho hai FK mới.
    with op.batch_alter_table("session") as batch:
        batch.add_column(sa.Column(
            "lot_id", sa.Integer(),
            sa.ForeignKey("parking_lot.id", name="fk_session_lot_id_parking_lot"),
            nullable=True,
        ))
        batch.add_column(sa.Column(
            "zone_id", sa.Integer(),
            sa.ForeignKey("zone.id", name="fk_session_zone_id_zone"),
            nullable=True,
        ))


def downgrade() -> None:
    op.drop_column("session", "zone_id")
    op.drop_column("session", "lot_id")
    op.drop_table("zone")
    op.drop_table("floor")
    op.drop_table("parking_lot")
