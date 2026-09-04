"""add plate_reading.plate_crop_asset_id

Persist the color-processed plate crop as a second encrypted image asset,
linked from the reading. SQLite test suite uses create_all; this keeps
Postgres in sync.

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
"""
from alembic import op
import sqlalchemy as sa

revision = "d5e6f7a8b9c0"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "plate_reading",
        sa.Column("plate_crop_asset_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_plate_reading_plate_crop_asset",
        "plate_reading", "image_asset",
        ["plate_crop_asset_id"], ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_plate_reading_plate_crop_asset", "plate_reading", type_="foreignkey")
    op.drop_column("plate_reading", "plate_crop_asset_id")
