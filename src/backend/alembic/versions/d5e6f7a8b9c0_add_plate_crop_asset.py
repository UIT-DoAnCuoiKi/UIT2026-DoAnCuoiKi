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
    # batch_alter_table: SQLite không ALTER được constraint (xem migration
    # a1b2c3d4e5f6 cho cùng vấn đề). Trên PostgreSQL alembic vẫn phát ADD COLUMN
    # / ADD CONSTRAINT thường, hành vi không đổi.
    with op.batch_alter_table("plate_reading") as batch:
        batch.add_column(sa.Column("plate_crop_asset_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_plate_reading_plate_crop_asset",
            "image_asset",
            ["plate_crop_asset_id"], ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("plate_reading") as batch:
        batch.drop_constraint("fk_plate_reading_plate_crop_asset", type_="foreignkey")
        batch.drop_column("plate_crop_asset_id")
