# Pandemic Treaty Influence Tracker

Backend system for tracking country proposals and their influence on the Pandemic Treaty drafts.

## Deployment on Railway

This project is designed to be deployed on [Railway](https://railway.app/).

### Prerequisites

1.  A Railway account.
2.  OpenAI API Key (for LLM and ASR).
3.  (Optional) S3-compatible Object Storage (AWS S3, Cloudflare R2, etc.) for file storage.

### Steps

1.  **New Project**: Create a new project on Railway.
2.  **Add Database**: Add a **PostgreSQL** service.
3.  **Add Redis**: Add a **Redis** service.
4.  **Deploy Code**: Connect your GitHub repository to Railway and deploy this repo.

### Service Configuration

Railway should detect the `Procfile` and creating two services (or one service with multiple processes if using the new primitives, but typically you might need to split them or use the `Procfile` support).

**If deploying as a single service with Procfile:**
Railway will likely pick up the `web` process by default. You may need to spin up a separate service (or a replica with a different start command) for the `worker`.

**Recommended Railway Setup:**
1.  **Service 1 (API)**:
    *   Build Command: `pip install -r requirements.txt`
    *   Start Command: `uvicorn apps.api.main:app --host 0.0.0.0 --port $PORT`
2.  **Service 2 (Worker)**:
    *   Build Command: `pip install -r requirements.txt`
    *   Start Command: `celery -A apps.worker.worker.celery worker --loglevel=INFO`

### Environment Variables

Configure the following variables in your Railway project (Shared variables recommended):

| Variable | Description | Example / Default |
| :--- | :--- | :--- |
| `DATABASE_URL` | Connection string for PostgreSQL | `postgresql://user:pass@host:port/db` (Auto-provided by Railway PG) |
| `REDIS_URL` | Connection string for Redis | `redis://:pass@host:port` (Auto-provided by Railway Redis) |
| `LLM_API_KEY` | API Key for OpenAI (GPT-4o) | `sk-...` |
| `ASR_API_KEY` | API Key for Whisper (or same as LLM) | `sk-...` |
| `STORAGE_BUCKET` | (Optional) S3 Bucket Name | `my-treaty-bucket` |
| `STORAGE_ENDPOINT`| (Optional) S3 Endpoint URL | `https://s3.us-east-1.amazonaws.com` |
| `STORAGE_ACCESS_KEY`| (Optional) S3 Access Key | `AKIA...` |
| `STORAGE_SECRET_KEY`| (Optional) S3 Secret Key | `secret...` |

### Usage

**Create a Job:**

```bash
curl -X POST https://<your-railway-url>/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "videos": [{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}],
    "docs": [{"file_key": "proposal.pdf", "doc_type": "proposal_pdf", "country": "Brazil"}],
    "drafts": [{"file_key": "draft_v1.pdf", "label": "Draft Feb 2024"}]
  }'
```

**Check Status:**

```bash
curl https://<your-railway-url>/jobs/{job_id}
```
