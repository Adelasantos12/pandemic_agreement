from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..db import SessionLocal
from ..models import Job, VideoSource, DocSource, DraftVersion
from ..settings import settings
import asyncio
import os
import httpx

router = APIRouter()

async def get_db():
    async with SessionLocal() as s:
        yield s

class CreateJobRequest(BaseModel):
    videos: list[dict] = []  # {url, meeting_id?, language_hint?}
    docs: list[dict] = []    # {file_key, country?, doc_type}
    drafts: list[dict] = []  # {file_key, label}

@router.post("")
async def create_job(req: CreateJobRequest, db: AsyncSession = Depends(get_db)):
    job = Job(status="queued")
    db.add(job)
    await db.flush()

    for v in req.videos:
        db.add(VideoSource(job_id=job.id, url=v["url"], meeting_id=v.get("meeting_id"), language_hint=v.get("language_hint")))
    for d in req.docs:
        db.add(DocSource(job_id=job.id, file_key=d["file_key"], country=d.get("country"), doc_type=d["doc_type"]))
    for dv in req.drafts:
        db.add(DraftVersion(job_id=job.id, file_key=dv["file_key"], label=dv["label"]))

    await db.commit()

    # Enqueue via Celery
    # We will implement this later or assume worker polls
    # But better to use Celery delay if possible.
    # For now, just return.

    return {"job_id": job.id, "status": job.status}

@router.get("/{job_id}")
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await db.get(Job, job_id)
    if not job:
        return {"error": "Job not found"}
    return {"id": job.id, "status": job.status, "error": job.error, "meta": job.meta}
