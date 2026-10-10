"""PolicyLens HTTP API (PRD §7)."""
import os
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from agents.graph import match_requirements, run_review
from api.account import router as account_router
from backend import audit_package
from backend.config import CORS_ORIGINS
from backend.db import (AuditLog, ControlResult, Decision, Evidence, Policy, Requirement, Review, Section,
                        SessionLocal, User, audit, init_db, now)
from backend.security import create_token, current_user, hash_password, require, verify_password
from evidence import store
from evidence.extract import evidence_types, extract_claims, extract_text
from policies.ingest import ingest, ingest_samples

MAX_UPLOAD = 10 * 1024 * 1024
SEED_USERS = [("alice", "engineer", "Alice Chen"), ("rita", "reviewer", "Rita Okafor"), ("admin", "admin", "Admin")]


def seed():
    init_db()
    password = os.getenv("SEED_PASSWORD", "policylens")
    with SessionLocal() as s:
        for name, role, display in SEED_USERS:
            u = s.scalar(select(User).where(User.username == name))
            if not u:
                s.add(User(username=name, password_hash=hash_password(password), role=role, display_name=display,
                           is_demo=True))
            elif not u.is_demo:  # accounts seeded before the flag existed
                u.is_demo, u.display_name = True, u.display_name or display
        if os.getenv("SEED_POLICIES", "1") == "1" and not s.scalar(select(func.count(Policy.id))):
            ingest_samples(s)
        s.commit()


@asynccontextmanager
async def lifespan(_app):
    seed()
    yield


app = FastAPI(title="PolicyLens AI", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
app.include_router(account_router)


def db():
    with SessionLocal() as s:
        yield s


# ---------- helpers ----------

def _review(s: Session, review_id: int) -> Review:
    r = s.scalar(
        select(Review).where(Review.id == review_id).options(
            selectinload(Review.evidence), selectinload(Review.decisions),
            selectinload(Review.results).selectinload(ControlResult.requirement)
            .selectinload(Requirement.section).selectinload(Section.policy),
        )
    )
    if not r:
        raise HTTPException(404, "Review not found")
    return r


def _evidence_dicts(review: Review) -> list[dict]:
    return [{"id": e.id, "filename": e.filename, "text": e.text,
             "types": evidence_types(e.filename, e.text, e.evidence_type)} for e in review.evidence]


def _review_out(r: Review) -> dict:
    return {
        "id": r.id, "title": r.title, "description": r.description, "submitted_by": r.submitted_by,
        "status": r.status, "result": r.result, "claims": r.claims, "summary": r.summary,
        "evidence_requested": r.evidence_requested, "created_at": r.created_at.isoformat(),
        "evidence": [{"id": e.id, "filename": e.filename, "evidence_type": e.evidence_type, "sha256": e.sha256,
                      "content_type": e.content_type, "excerpt": e.text[:300], "created_at": e.created_at.isoformat()}
                     for e in r.evidence],
        "findings": [{
            "id": c.id, "requirement": c.requirement.code, "requirement_text": c.requirement.text,
            "risk": c.requirement.risk, "citation": c.requirement.section.citation,
            "policy": c.requirement.section.policy.title, "section_heading": c.requirement.section.heading,
            "policy_text": c.policy_quote, "status": c.status, "interpretation": c.interpretation,
            "evidence_ids": c.evidence_ids, "confidence": c.confidence, "source": c.source, "notes": c.notes,
            "evidence_types": c.requirement.evidence_types,
        } for c in r.results],
        "decisions": [{"reviewer": d.reviewer, "action": d.action, "comment": d.comment,
                       "created_at": d.created_at.isoformat()} for d in r.decisions],
    }


async def _read(upload: UploadFile) -> bytes:
    data = await upload.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "File too large (max 10 MB)")
    if not data:
        raise HTTPException(400, "Empty file")
    return data


# ---------- auth ----------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/token")
def token(form: OAuth2PasswordRequestForm = Depends(), s: Session = Depends(db)):
    user = s.scalar(select(User).where(User.username == form.username))
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(401, "Incorrect username or password")
    if not user.is_active:
        raise HTTPException(403, "This account has been deactivated. Contact an administrator.")
    user.last_login_at = now()
    audit(s, user.username, "auth.login", f"user:{user.id}")
    s.commit()
    return {"access_token": create_token(user), "token_type": "bearer", "username": user.username, "role": user.role}


# ---------- setup: policies ----------

@app.post("/policies", status_code=201)
async def upload_policy(file: UploadFile = File(...), user: User = Depends(require("admin", "reviewer")),
                        s: Session = Depends(db)):
    data = await _read(file)
    try:
        p = ingest(s, data, file.filename or "policy.md", actor=user.username)
    except ValueError as e:
        raise HTTPException(400, str(e))
    s.commit()
    return {"id": p.id, "policy_key": p.policy_key, "title": p.title, "domain": p.domain,
            "sections": len(p.sections), "requirements": sum(len(x.requirements) for x in p.sections)}


@app.get("/policies")
def list_policies(_: User = Depends(current_user), s: Session = Depends(db)):
    policies = s.scalars(select(Policy).options(selectinload(Policy.sections).selectinload(Section.requirements))
                         .order_by(Policy.title))
    return [{"id": p.id, "policy_key": p.policy_key, "title": p.title, "domain": p.domain, "filename": p.filename,
             "sections": len(p.sections), "requirements": sum(len(x.requirements) for x in p.sections),
             "created_at": p.created_at.isoformat()} for p in policies]


@app.get("/policies/{policy_id}")
def get_policy(policy_id: int, _: User = Depends(current_user), s: Session = Depends(db)):
    p = s.scalar(select(Policy).where(Policy.id == policy_id)
                 .options(selectinload(Policy.sections).selectinload(Section.requirements)))
    if not p:
        raise HTTPException(404, "Policy not found")
    return {"id": p.id, "policy_key": p.policy_key, "title": p.title, "domain": p.domain,
            "sections": [{"citation": x.citation, "heading": x.heading, "text": x.text,
                          "requirements": [{"code": r.code, "text": r.text, "risk": r.risk,
                                            "evidence_types": r.evidence_types} for r in x.requirements]}
                         for x in p.sections]}


# ---------- 1. submit ----------

class ReviewIn(BaseModel):
    title: str = Field(min_length=3, max_length=256)
    description: str = Field(min_length=10, max_length=10_000)


@app.post("/reviews", status_code=201)
def create_review(body: ReviewIn, user: User = Depends(require("engineer", "admin")), s: Session = Depends(db)):
    r = Review(title=body.title, description=body.description, submitted_by=user.username,
               claims=extract_claims(body.description), evidence_requested=[])
    s.add(r)
    s.flush()
    audit(s, user.username, "review.submit", f"review:{r.id}")
    s.commit()
    return _review_out(_review(s, r.id))


@app.get("/reviews")
def list_reviews(_: User = Depends(current_user), s: Session = Depends(db)):
    rows = s.scalars(select(Review).options(selectinload(Review.evidence), selectinload(Review.results))
                     .order_by(Review.id.desc()))
    return [{"id": r.id, "title": r.title, "submitted_by": r.submitted_by, "status": r.status, "result": r.result,
             "evidence": len(r.evidence), "findings": len(r.results),
             "open": sum(1 for c in r.results if c.status != "PASS"), "created_at": r.created_at.isoformat()}
            for r in rows]


@app.post("/evidence", status_code=201)
async def add_evidence(review_id: int = Form(...), evidence_type: str = Form(""), note: str = Form(""),
                       file: UploadFile = File(...), user: User = Depends(require("engineer", "admin")),
                       s: Session = Depends(db)):
    r = _review(s, review_id)
    if r.status in ("approved", "rejected"):
        raise HTTPException(409, f"Review is {r.status}; evidence can no longer be added")
    data = await _read(file)
    filename = file.filename or "evidence"
    digest, path = store.save(data)
    text = extract_text(data, filename, note)
    declared = evidence_type or (evidence_types(filename, text) or ["other"])[0]
    e = Evidence(review_id=r.id, evidence_type=declared, filename=filename, sha256=digest, path=path, text=text,
                 content_type=file.content_type or "application/octet-stream")
    s.add(e)
    if r.status == "returned":
        r.status = "submitted"
    s.flush()
    audit(s, user.username, "evidence.add", f"review:{r.id}", evidence_id=e.id, sha256=digest)
    s.commit()
    return {"id": e.id, "filename": filename, "evidence_type": declared, "sha256": digest,
            "detected_types": evidence_types(filename, text, declared), "excerpt": text[:300]}


@app.get("/evidence/{evidence_id}/download")
def download_evidence(evidence_id: int, user: User = Depends(current_user), s: Session = Depends(db)):
    e = s.get(Evidence, evidence_id)
    if not e:
        raise HTTPException(404, "Evidence not found")
    audit(s, user.username, "evidence.download", f"evidence:{e.id}")
    s.commit()
    return Response(store.load(e.path), media_type=e.content_type,
                    headers={"Content-Disposition": f'attachment; filename="{e.filename}"'})


# ---------- 2. match ----------

@app.get("/controls")
def controls(review_id: int = Query(...), _: User = Depends(current_user), s: Session = Depends(db)):
    r = _review(s, review_id)
    reqs = match_requirements(s, r.description, r.claims, _evidence_dicts(r))
    return [{k: v for k, v in q.items() if k != "section_text"} | {"policy_text": q["section_text"]} for q in reqs]


# ---------- 3. evaluate ----------

class EvaluateIn(BaseModel):
    review_id: int


@app.post("/evaluate")
def evaluate(body: EvaluateIn, user: User = Depends(require("engineer", "reviewer", "admin")),
             s: Session = Depends(db)):
    r = _review(s, body.review_id)
    if r.status in ("approved", "rejected"):
        raise HTTPException(409, f"Review is {r.status}")
    state = run_review(s, r.description, _evidence_dicts(r))
    r.results.clear()
    s.flush()
    for f in state["findings"]:
        r.results.append(ControlResult(
            requirement_id=f["requirement"]["id"], status=f["status"], evidence_ids=f["evidence_ids"],
            policy_quote=f["policy_quote"], interpretation=f["interpretation"], confidence=f["confidence"],
            source=f["source"], notes=f["notes"]))
    r.claims = state["claims"]
    r.result, r.summary, r.evidence_requested = state["result"], state["summary"], state["evidence_requested"]
    r.status = "evaluated"
    audit(s, user.username, "review.evaluate", f"review:{r.id}", result=r.result, findings=len(state["findings"]))
    s.commit()
    s.expire_all()
    return _review_out(_review(s, r.id))


@app.get("/reviews/{review_id}")
def get_review(review_id: int, _: User = Depends(current_user), s: Session = Depends(db)):
    return _review_out(_review(s, review_id))


# ---------- 4. approve ----------

class ApproveIn(BaseModel):
    review_id: int
    action: Literal["approve", "reject", "return"]
    comment: str = Field(default="", max_length=5000)


@app.post("/approve")
def approve(body: ApproveIn, user: User = Depends(require("reviewer", "admin")), s: Session = Depends(db)):
    r = _review(s, body.review_id)
    if r.status != "evaluated":
        raise HTTPException(409, "Only evaluated reviews can be decided; run /evaluate first")
    if r.submitted_by == user.username:
        raise HTTPException(403, "Reviewers cannot decide on their own change request")
    open_items = [c for c in r.results if c.status != "PASS"]
    if body.action == "approve" and open_items and len(body.comment.strip()) < 10:
        raise HTTPException(422, f"{len(open_items)} findings are not PASS; approving requires a justification comment")
    if body.action != "approve" and len(body.comment.strip()) < 10:
        raise HTTPException(422, "Say what needs to change: rejecting or sending back requires a comment")
    s.add(Decision(review_id=r.id, reviewer=user.username, action=body.action, comment=body.comment))
    r.status = {"approve": "approved", "reject": "rejected", "return": "returned"}[body.action]
    audit(s, user.username, f"review.{body.action}", f"review:{r.id}", open_findings=len(open_items))
    s.commit()
    s.expire_all()
    return _review_out(_review(s, r.id))


# ---------- 5. package ----------

@app.get("/audit/{review_id}")
def audit_pkg(review_id: int, format: Literal["json", "md"] = "json", user: User = Depends(current_user),
              s: Session = Depends(db)):
    r = _review(s, review_id)
    if not r.results:
        raise HTTPException(409, "Review has not been evaluated yet")
    pkg = audit_package.build(r)
    audit(s, user.username, "audit.package", f"review:{r.id}", format=format)
    s.commit()
    if format == "md":
        return PlainTextResponse(audit_package.to_markdown(pkg), media_type="text/markdown",
                                 headers={"Content-Disposition": f'attachment; filename="audit-review-{r.id}.md"'})
    return pkg


@app.get("/audit-log")
def audit_log(limit: int = 100, _: User = Depends(require("admin", "reviewer")), s: Session = Depends(db)):
    rows = s.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(min(limit, 500)))
    return [{"id": a.id, "actor": a.actor, "action": a.action, "target": a.target, "detail": a.detail,
             "ts": a.ts.isoformat()} for a in rows]
