"""OAuth2 password flow with JWT bearer tokens and role-based access control."""
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select

from backend.config import JWT_SECRET, JWT_TTL_MINUTES
from backend.db import SessionLocal, User

oauth2 = OAuth2PasswordBearer(tokenUrl="token")
ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"{salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt, dk = stored.split("$")
    test = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS)
    return hmac.compare_digest(test.hex(), dk)


def create_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=JWT_TTL_MINUTES)
    return jwt.encode({"sub": user.username, "role": user.role, "exp": exp}, JWT_SECRET, algorithm="HS256")


def current_user(token: str = Depends(oauth2)) -> User:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"})
    with SessionLocal() as s:
        user = s.scalar(select(User).where(User.username == payload["sub"]))
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    return user


def require(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role: {', '.join(roles)}")
        return user

    return dep
