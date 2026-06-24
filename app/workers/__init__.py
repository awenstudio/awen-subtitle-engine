"""Celery application configuration"""

from celery import Celery

from app.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

celery_app = Celery(
    "ase",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_soft_time_limit=7200,   # 2 hours soft
    task_time_limit=10800,       # 3 hours hard
    worker_prefetch_multiplier=1,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["app.workers"])
