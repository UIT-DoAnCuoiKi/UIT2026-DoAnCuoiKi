"""add session.color

Lưu màu biển (đã suy luận từ model hoặc nhân viên sửa tay ở trạm cổng) lên
phiên gửi xe để tra cứu về sau, song song với plate_reading.color.

Revision ID: c4d5e6f7a8b9
Revises: b1c2d3e4f5a6
"""
from alembic import op
import sqlalchemy as sa

revision = "c4d5e6f7a8b9"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("session", sa.Column("color", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("session", "color")
