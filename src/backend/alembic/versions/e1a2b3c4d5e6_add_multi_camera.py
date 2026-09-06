"""add reading_image, lane_camera, lane.recognition_mode

Đa camera mỗi làn (2-3 cam, thường trước + sau xe): trước đây một lượt chụp chỉ
lưu được đúng 1 ảnh, và Lane.rtsp_url không ai đọc lúc chạy (chỉ 1 ô, không có
vai trò, không phân biệt webcam/RTSP).

Revision ID: e1a2b3c4d5e6
Revises: d5e6f7a8b9c0
"""
from alembic import op
import sqlalchemy as sa

revision = "e1a2b3c4d5e6"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reading_image",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reading_id", sa.Integer(), sa.ForeignKey("plate_reading.id"), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("image_asset_id", sa.Integer(), sa.ForeignKey("image_asset.id"), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_reading_image_reading_id", "reading_image", ["reading_id"])

    op.create_table(
        "lane_camera",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("lane_id", sa.Integer(), sa.ForeignKey("lane.id"), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("source_kind", sa.String(length=16), nullable=False),
        sa.Column("device_id", sa.String(length=256), nullable=True),
        sa.Column("rtsp_url", sa.String(length=512), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_lane_camera_lane_id", "lane_camera", ["lane_id"])

    # batch_alter_table: SQLite không ALTER được, xem các migration trước đã sửa
    # cùng vấn đề này (a1b2c3d4e5f6, b1c2d3e4f5a6, d5e6f7a8b9c0).
    with op.batch_alter_table("lane") as batch:
        batch.add_column(
            sa.Column("recognition_mode", sa.String(length=16), nullable=False, server_default="primary")
        )


def downgrade() -> None:
    with op.batch_alter_table("lane") as batch:
        batch.drop_column("recognition_mode")
    op.drop_index("ix_lane_camera_lane_id", table_name="lane_camera")
    op.drop_table("lane_camera")
    op.drop_index("ix_reading_image_reading_id", table_name="reading_image")
    op.drop_table("reading_image")
