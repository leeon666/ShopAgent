"""通用依赖：当前用户 / 当前管理员"""
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import security
from ..db import User, get_db


def get_current_user(authorization: str = Header(None), session: Session = Depends(get_db)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "未登录")
    payload = security.verify_token(authorization[7:])
    if payload is None:
        raise HTTPException(401, "登录已过期，请重新登录")
    user = session.scalar(select(User).where(User.id == payload["uid"]))
    if user is None:
        raise HTTPException(401, "用户不存在")
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "created_at": user.created_at,
    }


def get_current_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(403, "需要管理员权限")
    return user
