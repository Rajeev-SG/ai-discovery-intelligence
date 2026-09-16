"""drop uq_evidence_capture, add non-unique index

Revision ID: a1b2c3d4e5f6
Revises: 798291b8c6af
Create Date: 2026-09-16
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "798291b8c6af"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("uq_evidence_capture", "evidence_item", type_="unique")
    op.create_index(
        "ix_evidence_canonical_capture", "evidence_item", ["canonical_url", "capture_hash"]
    )


def downgrade() -> None:
    op.drop_index("ix_evidence_canonical_capture", table_name="evidence_item")
    op.create_unique_constraint(
        "uq_evidence_capture", "evidence_item", ["canonical_url", "capture_hash"]
    )
