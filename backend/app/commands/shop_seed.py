"""Seed a deterministic ShopAgent demo dataset."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import click

from app.commands import command, success
from app.db.models.user import UserRole
from app.db.session import get_db_context
from app.repositories import shop as shop_repo
from app.schemas.shop import OrderCreate, OrderItemCreate, TicketCreate
from app.schemas.user import UserCreate
from app.services.shop import ShopService
from app.services.user import UserService


@command("seed-shop", help="Create deterministic ShopAgent users, products, orders, and tickets")
@click.option("--password", default="ShopAgent123!", show_default=True, help="Demo password")
def seed_shop(password: str) -> None:
    """Create an idempotent local dataset for manual demos and evaluation."""

    async def _seed() -> None:
        async with get_db_context() as db:
            users = UserService(db)
            admin = await users.get_by_email("admin@shopagent.example.com")
            if admin is None:
                admin = await users.register(
                    UserCreate(
                        email="admin@shopagent.example.com",
                        password=password,
                        full_name="ShopAgent Admin",
                    )
                )
            admin.role = UserRole.ADMIN.value
            admin.is_app_admin = True

            customer = await users.get_by_email("demo@shopagent.example.com")
            if customer is None:
                customer = await users.register(
                    UserCreate(
                        email="demo@shopagent.example.com",
                        password=password,
                        full_name="Demo Customer",
                    )
                )
            customer.is_active = True

            products, _ = await shop_repo.list_products(db, 0, 100)
            by_name = {product.name: product for product in products}

            async def ensure_product(
                name: str,
                description: str,
                price: str,
                stock: int,
            ):
                product = by_name.get(name)
                if product is None:
                    product = await shop_repo.create_product(
                        db,
                        name=name,
                        description=description,
                        price=Decimal(price),
                        stock=stock,
                    )
                    by_name[name] = product
                elif product.stock < stock:
                    product.stock = stock
                return product

            headphones = await ensure_product(
                "Aurora 降噪耳机",
                "支持七天无理由退货的蓝牙降噪耳机。",
                "399.00",
                50,
            )
            lamp = await ensure_product(
                "Luma 智能台灯",
                "高显色桌面灯, 带一年质保。",
                "269.00",
                40,
            )
            mug = await ensure_product(
                "Ceramic Daily 马克杯",
                "易碎陶瓷杯, 发货使用防震包装。",
                "89.00",
                80,
            )

            service = ShopService(db)
            now = datetime.now(UTC)
            customer_orders, _ = await shop_repo.list_orders(db, customer.id, 0, 100)
            paid_order = next(
                (order for order in customer_orders if order.status == "paid"),
                None,
            )
            if paid_order is None:
                paid_order = await service.create_order(
                    user_id=customer.id,
                    data=OrderCreate(
                        items=[OrderItemCreate(product_id=headphones.id, quantity=1)]
                    ),
                )
                paid_order = await service.mark_paid(
                    user_id=customer.id, order_id=paid_order.id
                )
            paid_order.created_at = now - timedelta(days=1, hours=2)

            completed_order = next(
                (order for order in customer_orders if order.status == "completed"),
                None,
            )
            if completed_order is None:
                completed_order = await service.create_order(
                    user_id=customer.id,
                    data=OrderCreate(
                        items=[
                            OrderItemCreate(product_id=lamp.id, quantity=1),
                            OrderItemCreate(product_id=mug.id, quantity=1),
                        ]
                    ),
                )
                completed_order = await service.mark_paid(
                    user_id=customer.id, order_id=completed_order.id
                )
                completed_order.status = "completed"
            completed_order.created_at = now - timedelta(days=4)

            pending_order = next(
                (order for order in customer_orders if order.status == "pending"),
                None,
            )
            if pending_order is None:
                pending_order = await service.create_order(
                    user_id=customer.id,
                    data=OrderCreate(items=[OrderItemCreate(product_id=mug.id, quantity=2)]),
                )

            tickets, _ = await shop_repo.list_tickets(db, customer.id, 0, 100)
            damaged_ticket = next(
                (
                    ticket
                    for ticket in tickets
                    if ticket.order_id == completed_order.id and ticket.type == "damage"
                ),
                None,
            )
            if damaged_ticket is None:
                damaged_ticket = await service.create_ticket(
                    user_id=customer.id,
                    data=TicketCreate(
                        order_id=completed_order.id,
                        type="damage",
                        reason="台灯到货时灯罩有裂纹, 马克杯完好。",
                    ),
                )
                await service.add_ticket_message(
                    ticket_id=damaged_ticket.id,
                    user_id=customer.id,
                    content="我可以在聊天中补充破损照片, 希望只退台灯。",
                )

            shipping_ticket = next(
                (
                    ticket
                    for ticket in tickets
                    if ticket.order_id == paid_order.id and ticket.type == "logistics"
                ),
                None,
            )
            if shipping_ticket is None:
                shipping_ticket = await service.create_ticket(
                    user_id=customer.id,
                    data=TicketCreate(
                        order_id=paid_order.id,
                        type="logistics",
                        reason="耳机已付款一天, 物流页面暂时没有更新。",
                    ),
                )

            click.echo(
                "\nDemo accounts:\n"
                f"  Admin:    admin@shopagent.example.com / {password}\n"
                f"  Customer: demo@shopagent.example.com / {password}\n"
            )
            click.echo(
                "Demo records:\n"
                f"  Paid order:      {paid_order.order_no}\n"
                f"  Completed order: {completed_order.order_no}\n"
                f"  Damage ticket:   {damaged_ticket.ticket_no}\n"
                f"  Logistics ticket:{shipping_ticket.ticket_no}\n"
            )
            success("ShopAgent demo data is ready.")

    asyncio.run(_seed())
