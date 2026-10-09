"""SQLAlchemy models and session for Postgres + pgvector."""
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from backend.config import DATABASE_URL, EMBED_DIM

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(16))  # engineer | reviewer | admin


class Policy(Base):
    __tablename__ = "policies"
    id: Mapped[int] = mapped_column(primary_key=True)
    policy_key: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(256))
    domain: Mapped[str] = mapped_column(String(64))
    filename: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    sections: Mapped[list["Section"]] = relationship(back_populates="policy", cascade="all, delete-orphan")


class Section(Base):
    __tablename__ = "sections"
    id: Mapped[int] = mapped_column(primary_key=True)
    policy_id: Mapped[int] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"))
    citation: Mapped[str] = mapped_column(String(128))  # e.g. "SEC-ACCESS §2.1"
    heading: Mapped[str] = mapped_column(String(256))
    text: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(EMBED_DIM))
    embed_model: Mapped[str] = mapped_column(String(64))  # vectors are only compared within one model
    policy: Mapped[Policy] = relationship(back_populates="sections")
    requirements: Mapped[list["Requirement"]] = relationship(back_populates="section", cascade="all, delete-orphan")


class Requirement(Base):
    __tablename__ = "requirements"
    id: Mapped[int] = mapped_column(primary_key=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("sections.id", ondelete="CASCADE"))
    code: Mapped[str] = mapped_column(String(64))
    text: Mapped[str] = mapped_column(Text)
    risk: Mapped[str] = mapped_column(String(8))  # high | medium | low
    evidence_types: Mapped[list] = mapped_column(JSON, default=list)
    section: Mapped[Section] = relationship(back_populates="requirements")


class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text)
    submitted_by: Mapped[str] = mapped_column(String(64))
    # submitted | evaluated | approved | rejected | returned
    status: Mapped[str] = mapped_column(String(16), default="submitted")
    result: Mapped[str | None] = mapped_column(String(32), nullable=True)  # Compliant | Needs Review
    claims: Mapped[list] = mapped_column(JSON, default=list)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_requested: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="review", cascade="all, delete-orphan")
    results: Mapped[list["ControlResult"]] = relationship(back_populates="review", cascade="all, delete-orphan")
    decisions: Mapped[list["Decision"]] = relationship(back_populates="review", cascade="all, delete-orphan")


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"))
    evidence_type: Mapped[str] = mapped_column(String(32))
    filename: Mapped[str] = mapped_column(String(256))
    content_type: Mapped[str] = mapped_column(String(128))
    sha256: Mapped[str] = mapped_column(String(64))
    path: Mapped[str] = mapped_column(String(512))
    text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    review: Mapped[Review] = relationship(back_populates="evidence")


class ControlResult(Base):
    __tablename__ = "control_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"))
    requirement_id: Mapped[int] = mapped_column(ForeignKey("requirements.id", ondelete="CASCADE"))
    status: Mapped[str] = mapped_column(String(24))
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)
    policy_quote: Mapped[str] = mapped_column(Text)
    interpretation: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    source: Mapped[str] = mapped_column(String(16))  # llm | rules
    notes: Mapped[list] = mapped_column(JSON, default=list)  # guardrail adjustments
    review: Mapped[Review] = relationship(back_populates="results")
    requirement: Mapped[Requirement] = relationship()


class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id", ondelete="CASCADE"))
    reviewer: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(16))  # approve | reject | return
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    review: Mapped[Review] = relationship(back_populates="decisions")


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    target: Mapped[str] = mapped_column(String(128))
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def init_db(drop: bool = False):
    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    if drop:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def audit(session, actor: str, action: str, target: str, **detail):
    session.add(AuditLog(actor=actor, action=action, target=target, detail=detail))
