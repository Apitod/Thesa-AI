"""
Celery Application — konfigurasi task queue untuk generation jobs.

Menggunakan Redis sebagai broker (antrian task) sekaligus result backend.
Setiap kali user request generation, FastAPI akan mengirimkan task ke sini
dan langsung mengembalikan job_id ke frontend. Worker yang menjalankan
proses di background.
"""

from celery import Celery

from python_api.config import settings

# ---------------------------------------------------------------------------
# Buat Celery app
# ---------------------------------------------------------------------------

celery_app = Celery(
    "thesa_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["python_api.worker.tasks"],
)

# ---------------------------------------------------------------------------
# Konfigurasi
# ---------------------------------------------------------------------------

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="Asia/Makassar",
    enable_utc=True,

    # Task behavior
    task_track_started=True,
    task_acks_late=True,           # Task di-ack setelah selesai, bukan setelah diterima
    worker_prefetch_multiplier=1,  # Satu task per worker agar tidak berebut resource AI

    # Result TTL (setelah selesai, hasil Celery disimpan selama ini)
    result_expires=settings.job_ttl_seconds,

    # Retry
    task_max_retries=2,
    task_default_retry_delay=5,

    # Logging
    worker_redirect_stdouts=False,
)
