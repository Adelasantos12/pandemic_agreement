import re
from difflib import SequenceMatcher

def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, a[:2000], b[:2000]).ratio()

def retrieve_candidates(proposal, clauses, k: int = 10):
    """
    Retrieves top-k candidate clauses for a proposal based on text similarity.
    """
    q = (proposal.proposed_text or "") + " " + (proposal.topic or "")
    scored = []
    for c in clauses:
        # Combine article + paragraph text
        c_text = f"{c.article or ''} {c.paragraph or ''} {c.text}"
        score = _sim(q, c_text)
        scored.append((c, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:k]

    # return serializable candidates
    # Ensure keys match what verify_match expects (db_id, etc)
    return [
        {
            "db_id": c.id,
            "clause_key": c.clause_key,
            "article": c.article,
            "paragraph": c.paragraph,
            "text": c.text,
            "score": s
        }
        for c, s in top
    ]
