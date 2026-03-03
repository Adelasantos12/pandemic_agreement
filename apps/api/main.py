from fastapi import FastAPI

from .routers import jobs, research

app = FastAPI(title="Treaty Influence Tracker")
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(research.router, prefix="/research", tags=["research"])


@app.get("/health")
def health():
    return {"ok": True}
