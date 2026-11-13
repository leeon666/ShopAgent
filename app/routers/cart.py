"""购物车路由（需登录）。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import CartItem, Product, get_db
from ..schemas import CartAddRequest, CartUpdateRequest
from .deps import get_current_user

router = APIRouter(prefix="/api/cart", tags=["购物车"])


def _cart_items(session: Session, user_id: int) -> list[dict]:
    rows = session.execute(
        select(CartItem, Product)
        .join(Product, Product.id == CartItem.product_id)
        .where(CartItem.user_id == user_id)
        .order_by(CartItem.id.desc())
    ).all()
    return [
        {
            "product_id": product.id,
            "quantity": item.quantity,
            "name": product.name,
            "price": product.price,
            "stock": product.stock,
            "status": product.status,
            "image": product.image,
        }
        for item, product in rows
    ]


@router.get("", summary="查看购物车")
def get_cart(user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    items = _cart_items(session, user["id"])
    total = sum(i["price"] * i["quantity"] for i in items)
    return {"items": items, "total": round(total, 2)}


@router.post("", summary="加入购物车")
def add_to_cart(body: CartAddRequest, user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    product = session.get(Product, body.product_id)
    if product is None or product.status != "on":
        raise HTTPException(404, "商品不存在或已下架")
    existing = session.scalar(
        select(CartItem).where(CartItem.user_id == user["id"], CartItem.product_id == body.product_id)
    )
    if existing:
        new_qty = existing.quantity + body.quantity
        if new_qty > product.stock:
            raise HTTPException(400, f"库存不足，当前库存 {product.stock}")
        existing.quantity = new_qty
    else:
        if body.quantity > product.stock:
            raise HTTPException(400, f"库存不足，当前库存 {product.stock}")
        session.add(CartItem(user_id=user["id"], product_id=body.product_id, quantity=body.quantity))
    session.commit()
    return {"ok": True, "message": "已加入购物车"}


@router.patch("/{product_id}", summary="修改数量")
def update_cart(product_id: int, body: CartUpdateRequest, user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    row = session.execute(
        select(CartItem, Product.stock)
        .join(Product, Product.id == CartItem.product_id)
        .where(CartItem.user_id == user["id"], CartItem.product_id == product_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(404, "购物车中没有该商品")
    item, stock = row
    if body.quantity > stock:
        raise HTTPException(400, f"库存不足，当前库存 {stock}")
    item.quantity = body.quantity
    session.commit()
    return {"ok": True}


@router.delete("/{product_id}", summary="移除商品")
def remove_from_cart(product_id: int, user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    item = session.scalar(
        select(CartItem).where(CartItem.user_id == user["id"], CartItem.product_id == product_id)
    )
    if item is not None:
        session.delete(item)
        session.commit()
    return {"ok": True}


@router.delete("", summary="清空购物车")
def clear_cart(user: dict = Depends(get_current_user), session: Session = Depends(get_db)):
    for item in session.scalars(select(CartItem).where(CartItem.user_id == user["id"])).all():
        session.delete(item)
    session.commit()
    return {"ok": True}
