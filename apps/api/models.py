import enum
from sqlalchemy import String, Text, Integer, Float, ForeignKey, Enum, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from .db import Base

class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    failed = "failed"
    completed = "completed"

class MatchStatus(str, enum.Enum):
    adopted = "adopted"
    partial = "partial"
    not_adopted = "not_adopted"
    unclear = "unclear"

class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(32), default=JobStatus.queued.value)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)

class VideoSource(Base):
    __tablename__ = "video_sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    url: Mapped[str] = mapped_column(Text)
    meeting_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    language_hint: Mapped[str | None] = mapped_column(String(32), nullable=True)

class DocSource(Base):
    __tablename__ = "doc_sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    country: Mapped[str | None] = mapped_column(String(128), nullable=True)
    doc_type: Mapped[str] = mapped_column(String(64))  # proposal|draft|other
    file_key: Mapped[str] = mapped_column(Text)        # in S3/R2

class DraftVersion(Base):
    __tablename__ = "draft_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    label: Mapped[str] = mapped_column(String(128))  # e.g., INB9_A_INB9_3
    file_key: Mapped[str] = mapped_column(Text)

class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    video_id: Mapped[int] = mapped_column(ForeignKey("video_sources.id"))
    t0: Mapped[float] = mapped_column(Float)
    t1: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(Text)
    lang: Mapped[str | None] = mapped_column(String(16), nullable=True)
    speaker_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

class Proposal(Base):
    __tablename__ = "proposals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    source_type: Mapped[str] = mapped_column(String(32))  # transcript|pdf
    source_id: Mapped[int] = mapped_column(Integer)       # video_id or doc_id
    country: Mapped[str | None] = mapped_column(String(128), nullable=True)
    action: Mapped[str] = mapped_column(String(16))
    topic: Mapped[str] = mapped_column(String(128))
    target_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    proposed_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_quote: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)

class DraftClause(Base):
    __tablename__ = "draft_clauses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    draft_version_id: Mapped[int] = mapped_column(ForeignKey("draft_versions.id"))
    article: Mapped[str | None] = mapped_column(String(64), nullable=True)
    paragraph: Mapped[str | None] = mapped_column(String(64), nullable=True)
    clause_key: Mapped[str] = mapped_column(String(128))  # stable key within version
    text: Mapped[str] = mapped_column(Text)

class Match(Base):
    __tablename__ = "matches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    proposal_id: Mapped[int] = mapped_column(ForeignKey("proposals.id"))
    draft_version_id: Mapped[int] = mapped_column(ForeignKey("draft_versions.id"))
    clause_id: Mapped[int | None] = mapped_column(ForeignKey("draft_clauses.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16))
    score: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(Text)
    supporting_clause_ids: Mapped[dict] = mapped_column(JSON, default=list)
