"""add feature_toggle.dev_mode

Ẩn các đường tắt chỉ để test (tải ảnh thay camera thật, sau này là xem trước
RTSP) khỏi màn Trạm cổng lúc vận hành thật; mặc định tắt.

Revision ID: f2a3b4c5d6e7
Revises: e1a2b3c4d5e6
"""
from alembic import op
import sqlalchemy as sa

revision = "f2a3b4c5d6e7"
down_revision = "e1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("feature_toggle") as batch:
        batch.add_column(
            sa.Column("dev_mode", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    with op.batch_alter_table("feature_toggle") as batch:
        batch.drop_column("dev_mode")
