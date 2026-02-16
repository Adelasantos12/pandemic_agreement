from .worker import celery
from .asr import transcribe_audio
from .pdf_parse import parse_pdf_to_text, parse_draft_to_clauses
from .llm import extract_proposals, verify_match
from .matching import retrieve_candidates
from .metrics import compute_country_metrics
from .storage import download_to_tmp

import os
import json
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session
from apps.api.models import Job, VideoSource, DocSource, DraftVersion, TranscriptSegment, Proposal, DraftClause, Match

# Use sync driver for Celery worker
DB_URL = os.environ.get("DATABASE_URL", "").replace("postgres://", "postgresql://")
# Ensure using psycopg2
if DB_URL.startswith("postgresql://") and "asyncpg" not in DB_URL:
    pass # default is psycopg2
elif "asyncpg" in DB_URL:
    DB_URL = DB_URL.replace("+asyncpg", "")

@celery.task(name="apps.worker.tasks.run_job")
def run_job(job_id: int):
    # Re-create engine per task or globally? Globally is better but per task is safer for fork safety if not careful.
    # We'll do per task for simplicity as in spec.
    engine = create_engine(DB_URL, pool_pre_ping=True)

    with Session(engine) as db:
        job = db.get(Job, job_id)
        if not job:
            return

        job.status = "running"
        db.commit()

        try:
            # 1) Parse drafts into clauses
            drafts = db.execute(select(DraftVersion).where(DraftVersion.job_id == job_id)).scalars().all()
            for dv in drafts:
                pdf_path = download_to_tmp(dv.file_key)
                clauses = parse_draft_to_clauses(pdf_path)
                for c in clauses:
                    db.add(DraftClause(
                        draft_version_id=dv.id,
                        article=c.get("article"),
                        paragraph=c.get("paragraph"),
                        clause_key=c["clause_key"],
                        text=c["text"],
                    ))
                db.commit()

            # 2) Process PDFs (country proposals)
            docs = db.execute(select(DocSource).where(DocSource.job_id == job_id, DocSource.doc_type != "draft")).scalars().all()
            for doc in docs:
                pdf_path = download_to_tmp(doc.file_key)
                text_blocks = parse_pdf_to_text(pdf_path)  # list[str]
                for block in text_blocks:
                    props = extract_proposals(
                        text=block,
                        country_hint=doc.country,
                        source_type="proposal_pdf",
                        topic_hint=None
                    )
                    for p in props:
                        # Validate p is dict
                        if not isinstance(p, dict): continue

                        db.add(Proposal(
                            job_id=job_id,
                            source_type="pdf",
                            source_id=doc.id,
                            country=p.get("country"),
                            action=p.get("action", "SUPPORT"),
                            topic=p.get("topic", "General"),
                            target_ref=p.get("target_ref"),
                            proposed_text=p.get("proposed_text"),
                            rationale=p.get("rationale"),
                            evidence_quote=p.get("evidence_quote", ""),
                            confidence=p.get("confidence", 0.0),
                        ))
                db.commit()

            # 3) Videos -> ASR -> proposals
            videos = db.execute(select(VideoSource).where(VideoSource.job_id == job_id)).scalars().all()
            for vid in videos:
                audio_path = download_to_tmp(vid.url)
                segments = transcribe_audio(audio_path, language_hint=vid.language_hint)

                # Save segments
                for s in segments:
                    db.add(TranscriptSegment(
                        job_id=job_id, video_id=vid.id,
                        t0=s["start"], t1=s["end"],
                        text=s["text"], lang=s.get("lang"),
                        speaker_label=s.get("speaker"), confidence=s.get("confidence")
                    ))
                db.commit()

                # extract proposals from grouped segments
                # group by ~60-120s windows (approx 1500 chars)
                buffer = []
                buffer_len = 0
                for s in segments:
                    buffer.append(s["text"])
                    buffer_len += len(s["text"])
                    if buffer_len > 1500:
                        block = " ".join(buffer)
                        buffer = []
                        buffer_len = 0
                        props = extract_proposals(text=block, country_hint=None, source_type="transcript", topic_hint=None)
                        for p in props:
                            if not isinstance(p, dict): continue
                            db.add(Proposal(
                                job_id=job_id, source_type="transcript", source_id=vid.id,
                                country=p.get("country"), action=p.get("action", "SUPPORT"),
                                topic=p.get("topic", "General"),
                                target_ref=p.get("target_ref"), proposed_text=p.get("proposed_text"),
                                rationale=p.get("rationale"), evidence_quote=p.get("evidence_quote", ""),
                                confidence=p.get("confidence", 0.0)
                            ))
                        db.commit()

                # Remaining buffer
                if buffer:
                    block = " ".join(buffer)
                    props = extract_proposals(text=block, country_hint=None, source_type="transcript", topic_hint=None)
                    for p in props:
                        if not isinstance(p, dict): continue
                        db.add(Proposal(
                            job_id=job_id, source_type="transcript", source_id=vid.id,
                            country=p.get("country"), action=p.get("action", "SUPPORT"),
                            topic=p.get("topic", "General"),
                            target_ref=p.get("target_ref"), proposed_text=p.get("proposed_text"),
                            rationale=p.get("rationale"), evidence_quote=p.get("evidence_quote", ""),
                            confidence=p.get("confidence", 0.0)
                        ))
                    db.commit()

            # 4) Matching proposals <-> each draft version
            proposals = db.execute(select(Proposal).where(Proposal.job_id == job_id)).scalars().all()
            # Reload drafts to get clauses if needed, or query clauses directly
            drafts = db.execute(select(DraftVersion).where(DraftVersion.job_id == job_id)).scalars().all()

            for dv in drafts:
                clauses = db.execute(select(DraftClause).where(DraftClause.draft_version_id == dv.id)).scalars().all()
                if not clauses:
                    continue

                for pr in proposals:
                    candidates = retrieve_candidates(pr, clauses)  # top-k clauses (ids+text)
                    verdict = verify_match(pr, candidates)

                    # Convert match dict to DB model
                    # Note: verify_match returns best_clause_db_id (int)

                    # If verdict returns a clause_id, verify it exists in candidates (it should)
                    cid = verdict.get("best_clause_db_id")

                    db.add(Match(
                        proposal_id=pr.id,
                        draft_version_id=dv.id,
                        clause_id=cid,
                        status=verdict.get("status", "unclear"),
                        score=verdict.get("score", 0.0),
                        explanation=verdict.get("explanation", ""),
                        supporting_clause_ids=verdict.get("supporting_clause_ids", []),
                    ))
                db.commit()

            # 5) Metrics
            metrics = compute_country_metrics(db, job_id)
            job.meta = {**(job.meta or {}), "metrics": metrics}
            job.status = "completed"
            db.commit()

        except Exception as e:
            db.rollback()
            # Re-fetch job to update status
            job = db.get(Job, job_id)
            if job:
                job.status = "failed"
                job.error = str(e)
                db.commit()
            print(f"Job {job_id} failed: {e}")
            raise
