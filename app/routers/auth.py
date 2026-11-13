"""认证路由：注册 / 登录"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import security
from ..db import User, get_db
from ..schemas import LoginRequest, RegisterRequest

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/register", summary="用户注册")
def register(body: RegisterRequest, session: Session = Depends(get_db)):
    username = body.username.strip()
    exists = session.scalar(select(User.id).where(User.username == username))
    if exists:
        raise HTTPException(400, "用户名已存在")
    user = User(username=username, password_hash=security.hash_password(body.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    user_id = user.id
    token = security.create_token({"uid": user_id, "username": username, "role": "user"})
    return {"token": token, "user": {"id": user_id, "username": username, "role": "user"}}


@router.post("/login", summary="登录")
def login(body: LoginRequest, session: Session = Depends(get_db)):
    user = session.scalar(select(User).where(User.username == body.username.strip()))
    if user is None or not security.verify_password(body.password, user.password_hash):
        raise HTTPException(401, "用户名或密码错误")
    token = security.create_token({"uid": user.id, "username": user.username, "role": user.role})
    return {
        "token": token,
        "user": {"id": user.id, "username": user.username, "role": user.role},
    }
