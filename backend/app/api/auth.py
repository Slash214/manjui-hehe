from datetime import timedelta
from typing import Annotated

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User, utcnow
from app.repos import database
from app.schemas import Credentials
from app.services.content import Problem

router = APIRouter()
DB = Annotated[Session, Depends(database)]
hasher = PasswordHasher()
bearer = HTTPBearer(auto_error=False)


def secret() -> str:
    if len(settings.jwt_secret) < 32:
        raise Problem(503, "CONFIG_REQUIRED", "请先配置至少 32 字符的 JWT_SECRET 后重试。")
    return settings.jwt_secret


def current_user(
    db: DB, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> User:
    try:
        if credentials is None:
            raise ValueError()
        payload = jwt.decode(
            credentials.credentials,
            secret(),
            algorithms=["HS256"],
            options={"require": ["sub", "exp", "iat"]},
        )
        user = db.get(User, payload["sub"])
        if user is None:
            raise ValueError()
        return user
    except (jwt.PyJWTError, ValueError) as error:
        raise Problem(401, "UNAUTHORIZED", "登录已失效，请重新登录。") from error


CurrentUser = Annotated[User, Depends(current_user)]


def token(user: User) -> dict[str, str]:
    return {
        "access_token": jwt.encode(
            {"sub": user.id, "iat": utcnow(), "exp": utcnow() + timedelta(hours=12)},
            secret(),
            algorithm="HS256",
        ),
        "token_type": "bearer",
    }


@router.post("/auth/register", status_code=201)
def register(body: Credentials, db: DB) -> dict[str, str]:
    secret()
    email = body.email.strip().lower()
    if db.scalar(select(User).where(User.email == email)):
        raise Problem(409, "EMAIL_EXISTS", "该邮箱已注册，请直接登录。")
    user = User(email=email, password_hash=hasher.hash(body.password))
    db.add(user)
    db.flush()
    return token(user)


@router.post("/auth/login")
def login(body: Credentials, db: DB) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == body.email.strip().lower()))
    try:
        if user is None:
            hasher.hash(body.password)
            raise ValueError()
        hasher.verify(user.password_hash, body.password)
    except (VerifyMismatchError, VerificationError, ValueError) as error:
        raise Problem(401, "INVALID_LOGIN", "邮箱或密码不正确，请重试。") from error
    return token(user)


@router.get("/me")
def me(user: CurrentUser) -> dict[str, str]:
    return {"id": user.id, "email": user.email}
