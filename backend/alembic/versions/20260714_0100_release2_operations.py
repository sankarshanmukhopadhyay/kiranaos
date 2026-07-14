"""release 2 operations

Revision ID: 20260714_0100
Revises: 20260713_2300
Create Date: 2026-07-14
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260714_0100"
down_revision: str | None = "20260713_2300"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id"), nullable=False, index=True),
        sa.Column("sku", sa.String(length=80), nullable=False, index=True),
        sa.Column("name", sa.String(length=160), nullable=False, index=True),
        sa.Column("canonical_name", sa.String(length=160), nullable=False, index=True),
        sa.Column("category", sa.String(length=80), nullable=True, index=True),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("stock_quantity", sa.Float(), nullable=True),
        sa.Column("status", sa.Enum("active", "inactive", name="productstatus"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("store_id", "sku", name="uq_product_store_sku"),
    )
    op.create_table(
        "product_substitutions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id"), nullable=False, index=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False, index=True),
        sa.Column("substitute_product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False, index=True),
        sa.Column("reason", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("store_id", "product_id", "substitute_product_id", name="uq_product_substitution_pair"),
    )
    with op.batch_alter_table("order_items") as batch_op:
        batch_op.add_column(sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=True))
        batch_op.add_column(sa.Column("substitution_for_item_id", sa.Integer(), sa.ForeignKey("order_items.id"), nullable=True))
        batch_op.add_column(sa.Column("notes", sa.Text(), nullable=True))
        batch_op.create_index("ix_order_items_product_id", ["product_id"])
    op.create_table(
        "staff_assignments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id"), nullable=False, index=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False, index=True),
        sa.Column("operator_id", sa.Integer(), sa.ForeignKey("operators.id"), nullable=False, index=True),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("status", sa.Enum("assigned", "accepted", "completed", "reassigned", "cancelled", name="staffassignmentstatus"), nullable=False, index=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "ai_usage_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("store_id", sa.Integer(), sa.ForeignKey("stores.id"), nullable=False, index=True),
        sa.Column("provider", sa.String(length=40), nullable=False, index=True),
        sa.Column("model", sa.String(length=120), nullable=True),
        sa.Column("purpose", sa.Enum("parse", "ocr", "stt", "review_assist", name="aiusagepurpose"), nullable=False, index=True),
        sa.Column("inbound_message_id", sa.Integer(), sa.ForeignKey("inbound_messages.id"), nullable=True, index=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True, index=True),
        sa.Column("estimated_units", sa.Float(), nullable=False),
        sa.Column("estimated_cost", sa.Float(), nullable=False),
        sa.Column("success", sa.Integer(), nullable=False),
        sa.Column("failure_reason", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("ai_usage_events")
    op.drop_table("staff_assignments")
    with op.batch_alter_table("order_items") as batch_op:
        batch_op.drop_index("ix_order_items_product_id")
        batch_op.drop_column("notes")
        batch_op.drop_column("substitution_for_item_id")
        batch_op.drop_column("product_id")
    op.drop_table("product_substitutions")
    op.drop_table("products")
