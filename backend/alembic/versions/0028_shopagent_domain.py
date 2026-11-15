"""create ShopAgent commerce and after-sales tables

Revision ID: 0028_shopagent_domain
Revises: 0027_user_magic_link_epoch
Create Date: 2026-11-15T20:00:00+00:00
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision = "0028_shopagent_domain"
down_revision = "0027_user_magic_link_epoch"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shop_products",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("stock", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="on"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "shop_orders",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_no", sa.String(40), nullable=False, unique=True),
        sa.Column("user_id", PG_UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("total_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_shop_orders_order_no", "shop_orders", ["order_no"], unique=True)
    op.create_index("ix_shop_orders_user_id", "shop_orders", ["user_id"])
    op.create_table(
        "shop_order_items",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_id", PG_UUID(as_uuid=True), sa.ForeignKey("shop_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
    )
    op.create_index("ix_shop_order_items_order_id", "shop_order_items", ["order_id"])
    op.create_table(
        "shop_after_sales_tickets",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticket_no", sa.String(40), nullable=False, unique=True),
        sa.Column("user_id", PG_UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", PG_UUID(as_uuid=True), sa.ForeignKey("shop_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False, server_default="refund"),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("refund_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_shop_after_sales_tickets_ticket_no", "shop_after_sales_tickets", ["ticket_no"], unique=True)
    op.create_index("ix_shop_after_sales_tickets_user_id", "shop_after_sales_tickets", ["user_id"])
    op.create_index("ix_shop_after_sales_tickets_order_id", "shop_after_sales_tickets", ["order_id"])
    op.create_table(
        "shop_after_sales_messages",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticket_id", PG_UUID(as_uuid=True), sa.ForeignKey("shop_after_sales_tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_id", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("sender_role", sa.String(16), nullable=False, server_default="user"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_shop_after_sales_messages_ticket_id", "shop_after_sales_messages", ["ticket_id"])


def downgrade() -> None:
    op.drop_index("ix_shop_after_sales_messages_ticket_id", table_name="shop_after_sales_messages")
    op.drop_table("shop_after_sales_messages")
    op.drop_index("ix_shop_after_sales_tickets_order_id", table_name="shop_after_sales_tickets")
    op.drop_index("ix_shop_after_sales_tickets_user_id", table_name="shop_after_sales_tickets")
    op.drop_index("ix_shop_after_sales_tickets_ticket_no", table_name="shop_after_sales_tickets")
    op.drop_table("shop_after_sales_tickets")
    op.drop_index("ix_shop_order_items_order_id", table_name="shop_order_items")
    op.drop_table("shop_order_items")
    op.drop_index("ix_shop_orders_user_id", table_name="shop_orders")
    op.drop_index("ix_shop_orders_order_no", table_name="shop_orders")
    op.drop_table("shop_orders")
    op.drop_table("shop_products")
