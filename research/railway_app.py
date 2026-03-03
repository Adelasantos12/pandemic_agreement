from pathlib import Path

from fastapi import FastAPI

app = FastAPI(title="LATAM Pandemic Treaty ML Workspace")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/")
def index() -> dict:
    readme = Path("README.md")
    return {
        "service": "latam-pandemic-treaty-ml",
        "status": "running",
        "readme_exists": readme.exists(),
        "next_steps": [
            "Upload or mount source datasets (V-Dem/WGI/Manifesto).",
            "Run research/build_latam_panel.py to create data/latam_treaty_panel.csv.",
            "Run research/latam_treaty_capacity_model.py for training and outputs.",
        ],
    }
