import os
from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")

celery = Celery(
    "treaty_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery.conf.task_routes = {"apps.worker.tasks.*": {"queue": "default"}}
celery.conf.broker_connection_retry_on_startup = True
