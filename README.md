# LATAM Pandemic Treaty ML Workspace

This branch now contains only machine-learning related code and docs for modeling implementation capacity of the International Pandemic Treaty in LATAM under a CAS framing.

## Included

- `research/latam_treaty_capacity_model.py` — model training/evaluation pipeline (RF + GBM, CV, metrics, optional PCA/SHAP).
- `research/build_latam_panel.py` — merges source datasets into a LATAM country-year panel.
- `research/download_public_sources.py` — helper to fetch/organize public data files.
- `research/README.md` — methodology and usage details.
- `research/requirements-ml.txt` — Python dependencies for this ML workflow.

## Quick start

```bash
pip install -r research/requirements-ml.txt
python research/build_latam_panel.py --help
python research/latam_treaty_capacity_model.py --help
```


## Railway deployment fix (Railpack)

If Railpack reports `Script start.sh not found`, this branch now includes:

- `start.sh` (entrypoint used by Railway)
- `requirements.txt` (Python dependency manifest for build detection)
- `research/railway_app.py` (minimal FastAPI app with `/` and `/health`)

### Recommended Railway settings

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `./start.sh`

After deploy, verify:

```bash
curl https://<your-railway-url>/health
```
