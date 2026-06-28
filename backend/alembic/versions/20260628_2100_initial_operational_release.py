"""initial operational release

Revision ID: 20260628_2100
Revises:
Create Date: 2026-06-28
"""

from collections.abc import Sequence

from alembic import op

from app.db.session import Base
from app.models import domain  # noqa: F401

revision: str = "20260628_2100"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
