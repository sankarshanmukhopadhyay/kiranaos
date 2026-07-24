"""release 3 order to cash

Revision ID: 20260724_0900
Revises: 20260714_0100
"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op
revision: str = "20260724_0900"
down_revision: str | None = "20260714_0100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

def upgrade() -> None:
    with op.batch_alter_table("payments") as b:
        b.add_column(sa.Column("method", sa.Enum("cash","upi","split",name="paymentmethod"), nullable=False, server_default="upi"))
        b.add_column(sa.Column("cash_amount", sa.Float(), nullable=False, server_default="0"))
        b.add_column(sa.Column("upi_amount", sa.Float(), nullable=False, server_default="0"))
        b.add_column(sa.Column("refunded_amount", sa.Float(), nullable=False, server_default="0"))
        b.add_column(sa.Column("notes", sa.Text(), nullable=True))
        b.create_index("ix_payments_method", ["method"])
    op.create_table("refunds",
        sa.Column("id",sa.Integer(),primary_key=True), sa.Column("store_id",sa.Integer(),sa.ForeignKey("stores.id"),nullable=False,index=True),
        sa.Column("payment_id",sa.Integer(),sa.ForeignKey("payments.id"),nullable=False,index=True), sa.Column("order_id",sa.Integer(),sa.ForeignKey("orders.id"),nullable=True,index=True),
        sa.Column("amount",sa.Float(),nullable=False), sa.Column("reason",sa.String(240),nullable=False),
        sa.Column("status",sa.Enum("requested","approved","rejected",name="refundstatus"),nullable=False,index=True),
        sa.Column("requested_by",sa.String(120),nullable=True),sa.Column("decided_by",sa.String(120),nullable=True),
        sa.Column("requested_at",sa.DateTime(timezone=True),nullable=False),sa.Column("decided_at",sa.DateTime(timezone=True),nullable=True))
    op.create_table("daily_settlements",
        sa.Column("id",sa.Integer(),primary_key=True),sa.Column("store_id",sa.Integer(),sa.ForeignKey("stores.id"),nullable=False,index=True),
        sa.Column("business_day",sa.String(10),nullable=False,index=True),sa.Column("cash_total",sa.Float(),nullable=False),sa.Column("upi_total",sa.Float(),nullable=False),
        sa.Column("refund_total",sa.Float(),nullable=False),sa.Column("net_total",sa.Float(),nullable=False),sa.Column("payment_count",sa.Integer(),nullable=False),
        sa.Column("status",sa.Enum("draft","closed",name="settlementstatus"),nullable=False,index=True),sa.Column("notes",sa.Text(),nullable=True),
        sa.Column("generated_at",sa.DateTime(timezone=True),nullable=False),sa.Column("closed_at",sa.DateTime(timezone=True),nullable=True),sa.Column("closed_by",sa.String(120),nullable=True),
        sa.UniqueConstraint("store_id","business_day",name="uq_settlement_store_day"))

def downgrade() -> None:
    op.drop_table("daily_settlements"); op.drop_table("refunds")
    with op.batch_alter_table("payments") as b:
        b.drop_index("ix_payments_method"); b.drop_column("notes"); b.drop_column("refunded_amount"); b.drop_column("upi_amount"); b.drop_column("cash_amount"); b.drop_column("method")
