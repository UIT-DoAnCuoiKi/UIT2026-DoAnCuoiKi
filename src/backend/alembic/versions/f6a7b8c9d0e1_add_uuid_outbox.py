"""add session.uuid and outbox table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-23
"""
import uuid as uuidlib

import sqlalchemy as sa

from alembic import op

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("session", sa.Column("uuid", sa.String(length=36), nullable=True))
    # backfill uuid cho phiên cũ
    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id FROM session WHERE uuid IS NULL")).fetchall()
    for (sid,) in rows:
        bind.execute(sa.text("UPDATE session SET uuid = :u WHERE id = :i"),
                     {"u": str(uuidlib.uuid4()), "i": sid})
    op.create_index("ix_session_uuid", "session", ["uuid"], unique=True)

    op.create_table(
        "outbox",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_uuid", sa.String(length=36), nullable=False),
        sa.Column("lot_id", sa.Integer(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("synced", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_outbox_entity_uuid", "outbox", ["entity_uuid"])
    op.create_index("ix_outbox_synced", "outbox", ["synced"])


def downgrade() -> None:
    op.drop_table("outbox")
    op.drop_index("ix_session_uuid", table_name="session")
    op.drop_column("session", "uuid")
