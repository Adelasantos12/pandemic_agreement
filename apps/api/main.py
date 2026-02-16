from fastapi import FastAPI
from .routers import jobs

app = FastAPI(title="Treaty Influence Tracker")
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])

@app.get("/health")
def health():
    return {"ok": True}
