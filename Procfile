web: uvicorn apps.api.main:app --host 0.0.0.0 --port $PORT
worker: celery -A apps.worker.worker.celery worker --loglevel=INFO
