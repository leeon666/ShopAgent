"""商品浏览路由。"""
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..cache import cache_get, cache_set
from ..db import Category, Product, get_db

router = APIRouter(prefix="/api/products", tags=["商品"])


def _product_dict(product: Product, category_name: str | None = None) -> dict:
    data = {
        "id": product.id,
        "category_id": product.category_id,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "stock": product.stock,
        "sales": product.sales,
        "status": product.status,
        "image": product.image,
        "created_at": product.created_at,
    }
    if category_name is not None:
        data["category_name"] = category_name
    return data


@router.get("", summary="商品列表（分类/搜索/分页）")
def list_products(
    category_id: int | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=12, ge=1, le=100),
    session: Session = Depends(get_db),
):
    filters = [Product.status == "on"]
    if category_id:
        filters.append(Product.category_id == category_id)
    if q:
        like = f"%{q}%"
        filters.append(Product.name.ilike(like) | Product.description.ilike(like))

    total = session.scalar(select(func.count()).select_from(Product).where(*filters)) or 0
    rows = session.execute(
        select(Product, Category.name)
        .join(Category, Category.id == Product.category_id)
        .where(*filters)
        .order_by(Product.created_at.desc(), Product.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    items = [_product_dict(product, category_name) for product, category_name in rows]
    return {"items": items, "total": total, "page": page, "size": size, "pages": (total + size - 1) // size}


@router.get("/{product_id}", summary="商品详情")
def get_product(product_id: int, session: Session = Depends(get_db)):
    row = session.execute(
        select(Product, Category.name)
        .join(Category, Category.id == Product.category_id)
        .where(Product.id == product_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(404, "商品不存在")
    product, category_name = row
    return _product_dict(product, category_name)


@router.get("/meta/categories", summary="全部分类")
def list_categories(session: Session = Depends(get_db)):
    cached = cache_get("categories")
    if cached:
        return {"items": json.loads(cached)}
    categories = session.scalars(select(Category).order_by(Category.sort, Category.id)).all()
    items = [{"id": c.id, "name": c.name, "sort": c.sort} for c in categories]
    cache_set("categories", json.dumps(items), ttl_seconds=60)
    return {"items": items}
