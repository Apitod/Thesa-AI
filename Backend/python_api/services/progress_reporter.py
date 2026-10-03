"""
Progress Reporter — helper untuk mengirim progress events ke Redis.

Setiap kali backend menyelesaikan satu tahap (stage), panggil fungsi
emit_progress() untuk menyimpan state ke Redis dan mempublikasikan event
ke channel SSE yang didengarkan oleh frontend.

Prinsip:
- Backend push → Redis → SSE → Frontend update progress bar
- Bukan frontend setTimeout() → fake progress
"""

import json
import time
from typing import Any, Dict, Optional

import redis

from python_api.config import settings
from python_api.models.schemas import GenerationStage, JobStatus


# ---------------------------------------------------------------------------
# Redis client (lazy singleton)
# ---------------------------------------------------------------------------

_redis_client: Optional[redis.Redis] = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
            retry_on_timeout=False,
        )
    return _redis_client


def _reset_redis_client() -> None:
    """Reset singleton saat terjadi connection error agar reconnect otomatis."""
    global _redis_client
    try:
        if _redis_client:
            _redis_client.close()
    except Exception:
        pass
    _redis_client = None


# ---------------------------------------------------------------------------
# Progress event structure
# ---------------------------------------------------------------------------

def _build_event(
    job_id: str,
    status: JobStatus,
    stage: GenerationStage,
    progress: int,
    message: str,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Membangun dictionary event yang konsisten."""
    event = {
        "job_id": job_id,
        "status": status.value,
        "stage": stage.value,
        "progress": progress,
        "message": message,
        "timestamp": time.time(),
    }
    if extra:
        event["extra"] = extra
    return event


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def emit_progress(
    job_id: str,
    stage: GenerationStage,
    progress: int,
    message: str,
    status: JobStatus = JobStatus.RUNNING,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Simpan state terbaru ke Redis (hash) dan publish event ke channel SSE.

    Args:
        job_id:   ID unik job generation.
        stage:    Tahap yang sedang berjalan (lihat GenerationStage enum).
        progress: Persentase progress (0-100).
        message:  Pesan yang bisa ditampilkan ke user.
        status:   Status job (default RUNNING).
        extra:    Data tambahan opsional (misal: nama chapter yang sedang di-generate).
    """
    r = _get_redis()
    event = _build_event(job_id, status, stage, progress, message, extra)
    event_json = json.dumps(event, ensure_ascii=False)

    # Simpan state terbaru ke hash (untuk GET /generations/{id})
    job_key = f"thesa:job:{job_id}"
    r.hset(job_key, mapping={
        "status": status.value,
        "stage": stage.value,
        "progress": str(progress),
        "message": message,
        "updated_at": str(time.time()),
    })
    r.expire(job_key, settings.job_ttl_seconds)

    # Append event ke list untuk SSE stream
    stream_key = f"thesa:job:{job_id}:events"
    r.rpush(stream_key, event_json)
    r.expire(stream_key, settings.job_ttl_seconds)

    # Publish ke channel agar SSE endpoint yang sedang mendengarkan tahu ada update baru
    channel = f"thesa:job:{job_id}:channel"
    r.publish(channel, event_json)


def emit_result(
    job_id: str,
    filename: str,
    output_path: str,
    download_url: str,
    pdf_url: Optional[str] = None,
    token_usage: Optional[Dict] = None,
    warnings: Optional[list] = None,
) -> None:
    """
    Simpan hasil akhir job ke Redis setelah generation selesai.
    Dipanggil oleh worker setelah DOCX berhasil dibuat.
    """
    r = _get_redis()
    result = {
        "filename": filename,
        "output_path": output_path,
        "download_url": download_url,
        "pdf_url": pdf_url or "",
        "token_usage": json.dumps(token_usage or {}, ensure_ascii=False),
        "warnings": json.dumps(warnings or [], ensure_ascii=False),
    }
    job_key = f"thesa:job:{job_id}"
    r.hset(job_key, mapping={**result, "status": JobStatus.COMPLETED.value, "progress": "100"})
    r.expire(job_key, settings.job_ttl_seconds)

    # Kirim event terakhir
    emit_progress(
        job_id=job_id,
        stage=GenerationStage.COMPLETED,
        progress=100,
        message="Makalah berhasil dibuat. Silakan unduh hasilnya.",
        status=JobStatus.COMPLETED,
        extra={"download_url": download_url, "pdf_url": pdf_url},
    )


def emit_failure(job_id: str, stage: GenerationStage, error_code: str, message: str) -> None:
    """
    Simpan state gagal ke Redis.
    Dipanggil ketika terjadi error dalam pipeline generation.
    Tidak mengekspos traceback Python ke frontend.
    """
    r = _get_redis()
    job_key = f"thesa:job:{job_id}"
    r.hset(job_key, mapping={
        "status": JobStatus.FAILED.value,
        "stage": stage.value,
        "error_code": error_code,
        "error_message": message,
    })
    r.expire(job_key, settings.job_ttl_seconds)

    emit_progress(
        job_id=job_id,
        stage=stage,
        progress=0,
        message=message,
        status=JobStatus.FAILED,
        extra={"error_code": error_code},
    )


def get_job_state(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Ambil state terbaru sebuah job dari Redis.
    Digunakan oleh GET /generations/{job_id}.
    Returns None jika job tidak ada ATAU jika Redis tidak bisa dijangkau.
    """
    try:
        r = _get_redis()
        job_key = f"thesa:job:{job_id}"
        data = r.hgetall(job_key)
        return data if data else None
    except redis.exceptions.ConnectionError:
        _reset_redis_client()
        return None
    except Exception:
        return None


def get_job_events(job_id: str, start_index: int = 0) -> list:
    """
    Ambil semua events dari job (untuk SSE recovery jika koneksi putus).
    start_index digunakan agar client tidak menerima event yang sama dua kali.
    """
    try:
        r = _get_redis()
        stream_key = f"thesa:job:{job_id}:events"
        raw_events = r.lrange(stream_key, start_index, -1)
        return [json.loads(e) for e in raw_events]
    except redis.exceptions.ConnectionError:
        _reset_redis_client()
        return []
    except Exception:
        return []


def set_job_cancelled(job_id: str) -> bool:
    """
    Tandai job sebagai cancelled.
    Worker akan memeriksa flag ini sebelum melanjutkan setiap stage.
    Returns True jika job ditemukan dan berhasil ditandai.
    Returns False jika job tidak ada atau Redis tidak tersedia.
    """
    try:
        r = _get_redis()
        job_key = f"thesa:job:{job_id}"
        if not r.exists(job_key):
            return False
        r.hset(job_key, "status", JobStatus.CANCELLED.value)
        r.publish(f"thesa:job:{job_id}:channel", json.dumps({
            "job_id": job_id,
            "status": JobStatus.CANCELLED.value,
            "stage": GenerationStage.FAILED.value,
            "progress": 0,
            "message": "Generation dibatalkan oleh pengguna.",
        }))
        return True
    except redis.exceptions.ConnectionError:
        return False
    except Exception:
        return False
