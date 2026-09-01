"""widen plate_reading.layout to 16

Detector thật trả layout dạng `bien_2hang`/`bien_1hang` (10 ký tự), dài hơn
String(8) ban đầu (đặt theo stub layout="1"). Postgres cưỡng chế độ dài varchar
(SQLite thì không, nên suite test SQLite không bắt được lỗi này).

Revision ID: b1c2d3e4f5a6
Revises: a7b8c9d0e1f2
"""
from alembic import op
import sqlalchemy as sa

revision = "b1c2d3e4f5a6"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "plate_reading", "layout",
        existing_type=sa.String(length=8),
        type_=sa.String(length=16),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "plate_reading", "layout",
        existing_type=sa.String(length=16),
        type_=sa.String(length=8),
        existing_nullable=True,
    )
