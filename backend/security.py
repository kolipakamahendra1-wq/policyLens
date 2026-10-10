"""OAuth2 password flow with JWT bearer tokens and role-based access control."""
import hashlib
import hmac
import os
import re
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


USERNAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{2,31}$")
MIN_PASSWORD = 10


def password_problems(password: str, username: str = "") -> list[str]:
    """Rules shown to the user; empty list means the password is acceptable."""
    problems = []
    if len(password) < MIN_PASSWORD:
        problems.append(f"Use at least {MIN_PASSWORD} characters.")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        problems.append("Include at least one letter and one number.")
    if username and username.lower() in password.lower():
        problems.append("Don't include your username.")
    if len(password) > 128:
        problems.append("Use at most 128 characters.")
    return problems


def create_token(user: User) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=JWT_TTL_MINUTES)
    claims = {"sub": user.username, "role": user.role, "ver": user.token_version, "exp": exp}
    return jwt.encode(claims, JWT_SECRET, algorithm="HS256")


def current_user(token: str = Depends(oauth2)) -> User:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"})
    with SessionLocal() as s:
        user = s.scalar(select(User).where(User.username == payload["sub"]))
    if not user or not user.is_active or payload.get("ver", 0) != user.token_version:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired or account disabled; sign in again",
                            headers={"WWW-Authenticate": "Bearer"})
    return user


def require(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role: {', '.join(roles)}")
        return user

    return dep
