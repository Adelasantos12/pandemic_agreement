from sqlalchemy import select
from apps.api.models import Proposal, Match, DraftVersion

def compute_country_metrics(db, job_id: int):
    proposals = db.execute(select(Proposal).where(Proposal.job_id == job_id)).scalars().all()
    by_country = {}
    for p in proposals:
        c = p.country or "UNKNOWN"
        by_country.setdefault(c, {"total": 0, "adopted": 0, "partial": 0, "points": 0.0})
        by_country[c]["total"] += 1

    matches = db.execute(select(Match).join(Proposal, Match.proposal_id == Proposal.id).where(Proposal.job_id == job_id)).scalars().all()
    for m in matches:
        p = db.get(Proposal, m.proposal_id)
        if not p:
            continue
        c = p.country or "UNKNOWN"
        if c not in by_country:
             by_country.setdefault(c, {"total": 0, "adopted": 0, "partial": 0, "points": 0.0})

        if m.status == "adopted":
            by_country[c]["adopted"] += 1
            by_country[c]["points"] += 1.0
        elif m.status == "partial":
            by_country[c]["partial"] += 1
            by_country[c]["points"] += 0.5

    # rates
    for c, d in by_country.items():
        d["adoption_rate"] = (d["points"] / d["total"]) if d["total"] else 0.0
    return by_country
