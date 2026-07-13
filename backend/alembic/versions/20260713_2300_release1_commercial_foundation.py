"""release 1 commercial foundation

Revision ID: 20260713_2300
Revises: 20260628_2100
Create Date: 2026-07-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260713_2300"
down_revision: str | None = "20260628_2100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("inbound_messages") as batch_op:
        batch_op.add_column(sa.Column("parse_failure_reason", sa.String(length=120), nullable=True))
        batch_op.create_unique_constraint(
            "uq_inbound_store_source_external",
            ["store_id", "source", "external_message_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("inbound_messages") as batch_op:
        batch_op.drop_constraint("uq_inbound_store_source_external", type_="unique")
        batch_op.drop_column("parse_failure_reason")
