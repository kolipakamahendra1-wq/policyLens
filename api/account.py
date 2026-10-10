"""Accounts: sign-up, profile, password, sessions, the dashboard summary and admin user management."""
import os
import re
import secrets
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.db import AuditLog, Policy, Review, SessionLocal, User, audit, now
from backend.security import USERNAME_RE, create_token, current_user, hash_password, password_problems, require, verify_password

router = APIRouter()
ALLOW_REGISTRATION = os.getenv("ALLOW_REGISTRATION", "1") == "1"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
OPEN_STATES = ("submitted", "evaluated", "returned")


def db():
    with SessionLocal() as s:
        yield s


def profile(u: User) -> dict:
    return {
        "id": u.id, "username": u.username, "display_name": u.display_name or u.username, "email": u.email,
        "role": u.role, "is_active": u.is_active, "is_demo": u.is_demo, "created_at": u.created_at.isoformat(),
        "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
    }


def _check_password(password: str, username: str):
    problems = password_problems(password, username)
    if problems:
        raise HTTPException(422, " ".join(problems))


def _check_email(email: str | None) -> str | None:
    email = (email or "").strip() or None
    if email and not EMAIL_RE.match(email):
        raise HTTPException(422, "Enter a valid email address, like name@company.com.")
    return email


def _locked_user(s: Session, user: User) -> User:
    """Re-load the caller inside this session so changes persist."""
    return s.get(User, user.id)


# ---------- sign-up ----------

class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=128)
    display_name: str = Field(default="", max_length=128)
    email: str | None = Field(default=None, max_length=254)


@router.post("/register", status_code=201)
def register(body: RegisterIn, s: Session = Depends(db)):
    if not ALLOW_REGISTRATION:
        raise HTTPException(403, "Self sign-up is turned off. Ask an administrator for an account.")
    username = body.username.strip().lower()
    if not USERNAME_RE.match(username):
        raise HTTPException(422, "Usernames are 3-32 characters: lowercase letters, numbers, dots, dashes or underscores.")
    if s.scalar(select(User).where(User.username == username)):
        raise HTTPException(409, "That username is taken. Try another one.")
    _check_password(body.password, username)
    # New accounts are engineers; an admin can grant the reviewer role.
    u = User(username=username, password_hash=hash_password(body.password), role="engineer",
             display_name=body.display_name.strip(), email=_check_email(body.email), last_login_at=now())
    s.add(u)
    s.flush()
    audit(s, username, "account.register", f"user:{u.id}")
    s.commit()
    return {"access_token": create_token(u), "token_type": "bearer", "username": u.username, "role": u.role}


# ---------- profile, password, sessions ----------

@router.get("/me")
def me(user: User = Depends(current_user)):
    return profile(user)


class ProfileIn(BaseModel):
    display_name: str = Field(default="", max_length=128)
    email: str | None = Field(default=None, max_length=254)


@router.patch("/me")
def update_me(body: ProfileIn, user: User = Depends(current_user), s: Session = Depends(db)):
    u = _locked_user(s, user)
    u.display_name = body.display_name.strip()
    u.email = _check_email(body.email)
    audit(s, u.username, "account.profile", f"user:{u.id}")
    s.commit()
    return profile(u)


class PasswordIn(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(max_length=128)


@router.post("/me/password")
def change_password(body: PasswordIn, user: User = Depends(current_user), s: Session = Depends(db)):
    u = _locked_user(s, user)
    if u.is_demo:
        raise HTTPException(403, "Demo accounts are shared, so their password can't be changed. Create your own account to try this.")
    if not verify_password(body.current_password, u.password_hash):
        raise HTTPException(400, "Your current password is incorrect.")
    if body.new_password == body.current_password:
        raise HTTPException(422, "Choose a password you haven't just used.")
    _check_password(body.new_password, u.username)
    u.password_hash = hash_password(body.new_password)
    u.token_version += 1  # every other session is signed out
    audit(s, u.username, "account.password", f"user:{u.id}")
    s.commit()
    return {"access_token": create_token(u), "token_type": "bearer", "username": u.username, "role": u.role}


@router.post("/me/sign-out-everywhere")
def sign_out_everywhere(user: User = Depends(current_user), s: Session = Depends(db)):
    u = _locked_user(s, user)
    u.token_version += 1
    audit(s, u.username, "account.sign_out_all", f"user:{u.id}")
    s.commit()
    return {"access_token": create_token(u), "token_type": "bearer", "username": u.username, "role": u.role}


# ---------- dashboard ----------

def _review_row(r: Review) -> dict:
    return {"id": r.id, "title": r.title, "submitted_by": r.submitted_by, "status": r.status, "result": r.result,
            "open": sum(1 for c in r.results if c.status != "PASS"), "findings": len(r.results),
            "created_at": r.created_at.isoformat()}


@router.get("/dashboard")
def dashboard(user: User = Depends(current_user), s: Session = Depends(db)):
    reviews = list(s.scalars(select(Review).options(selectinload(Review.results)).order_by(Review.id.desc())))
    mine = [r for r in reviews if r.submitted_by == user.username]
    can_decide = user.role in ("reviewer", "admin")
    queue = [r for r in reviews if can_decide and r.status == "evaluated" and r.submitted_by != user.username]
    scope = reviews if can_decide else mine
    statuses = {k: 0 for k in ("PASS", "FAIL", "UNKNOWN", "NEEDS_HUMAN_REVIEW")}
    for r in scope:
        for c in r.results:
            statuses[c.status] = statuses.get(c.status, 0) + 1
    activity = s.scalars(select(AuditLog).where(AuditLog.actor == user.username, AuditLog.action != "auth.login")
                         .order_by(AuditLog.id.desc()).limit(8))
    return {
        "me": profile(user),
        "counts": {
            "my_open": sum(1 for r in mine if r.status in OPEN_STATES),
            "returned_to_me": sum(1 for r in mine if r.status == "returned"),
            "awaiting_decision": len(queue),
            "approved": sum(1 for r in scope if r.status == "approved"),
            "rejected": sum(1 for r in scope if r.status == "rejected"),
            "policies": s.scalar(select(func.count(Policy.id))),
        },
        "finding_statuses": statuses,
        "needs_my_action": [_review_row(r) for r in mine if r.status in ("returned", "submitted")][:5],
        "decision_queue": [_review_row(r) for r in queue][:5],
        "my_recent": [_review_row(r) for r in mine][:5],
        "recent_activity": [{"action": a.action, "target": a.target, "ts": a.ts.isoformat()} for a in activity],
    }


# ---------- admin: users ----------

@router.get("/users")
def list_users(_: User = Depends(require("admin")), s: Session = Depends(db)):
    return [profile(u) for u in s.scalars(select(User).order_by(User.username))]


class UserUpdateIn(BaseModel):
    role: Literal["engineer", "reviewer", "admin"] | None = None
    is_active: bool | None = None


@router.patch("/users/{user_id}")
def update_user(user_id: int, body: UserUpdateIn, admin: User = Depends(require("admin")), s: Session = Depends(db)):
    u = s.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    if u.id == admin.id and (body.role not in (None, "admin") or body.is_active is False):
        raise HTTPException(409, "You can't remove your own admin access or deactivate yourself.")
    if u.is_demo and (body.role is not None or body.is_active is False):
        raise HTTPException(409, "Demo accounts keep their role and stay active so the demo keeps working.")
    if body.role is not None:
        u.role = body.role
    if body.is_active is not None:
        u.is_active = body.is_active
        if not body.is_active:
            u.token_version += 1  # end their sessions now
    audit(s, admin.username, "admin.user_update", f"user:{u.id}", role=u.role, is_active=u.is_active)
    s.commit()
    return profile(u)


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: int, admin: User = Depends(require("admin")), s: Session = Depends(db)):
    u = s.get(User, user_id)
    if not u:
        raise HTTPException(404, "User not found")
    if u.is_demo:
        raise HTTPException(409, "Demo account passwords are fixed.")
    temporary = secrets.token_urlsafe(9) + "7a"  # meets the letter + number rule
    u.password_hash = hash_password(temporary)
    u.token_version += 1
    audit(s, admin.username, "admin.password_reset", f"user:{u.id}")
    s.commit()
    return {"username": u.username, "temporary_password": temporary}
