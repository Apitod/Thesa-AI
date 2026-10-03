"""
Router: /api/v1/generations

Endpoint utama untuk Generation Job lifecycle.

Kontrak API (sesuai api-design-principles):
  POST   /api/v1/generations              → Buat job baru
  GET    /api/v1/generations/{id}         → Status job
  GET    /api/v1/generations/{id}/events  → SSE stream progress
  GET    /api/v1/generations/{id}/result  → Download DOCX
  POST   /api/v1/generations/{id}/cancel  → Batalkan job
"""

import asyncio
import json
import os
import uuid
from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse

from python_api.config import Settings, get_settings
from python_api.models.schemas import (
    ErrorDetail,
    ErrorResponse,
    GenerationJobResponse,
    GenerationRequest,
    GenerationResultResponse,
    GenerationStage,
    GenerationStatusResponse,
    JobStatus,
)
from python_api.services.progress_reporter import (
    get_job_events,
    get_job_state,
    set_job_cancelled,
)
from python_api.worker.tasks import generate_paper_task

router = APIRouter()


# ---------------------------------------------------------------------------
# Dependency: async Redis client
# ---------------------------------------------------------------------------

async def get_redis(settings: Settings = Depends(get_settings)) -> aioredis.Redis:
    """Async Redis client untuk SSE PubSub."""
    return aioredis.from_url(settings.redis_url, decode_responses=True)


# ---------------------------------------------------------------------------
# POST /api/v1/generations
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=GenerationJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Buat generation job baru",
    description=(
        "Menerima data makalah, membuat generation job, dan mengembalikan job_id. "
        "Frontend menggunakan job_id untuk subscribe ke SSE events."
    ),
)
async def create_generation(
    request: GenerationRequest,
    settings: Settings = Depends(get_settings),
) -> GenerationJobResponse:
    job_id = str(uuid.uuid4())

    # Serialize request ke dict agar bisa dikirim ke Celery (JSON-serializable)
    payload = request.model_dump(mode="json")

    try:
        # Dispatch ke Celery worker (async, non-blocking)
        generate_paper_task.apply_async(
            args=[job_id, payload],
            task_id=job_id,
        )
    except Exception as e:
        # Celery/Redis tidak tersedia
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "QUEUE_UNAVAILABLE",
                "message": "Layanan antrian tidak tersedia. Pastikan Redis dan Worker sudah berjalan.",
            },
        )

    return GenerationJobResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        message="Job berhasil dibuat dan sedang dalam antrian.",
    )


# ---------------------------------------------------------------------------
# GET /api/v1/generations/{job_id}
# ---------------------------------------------------------------------------

@router.get(
    "/{job_id}",
    response_model=GenerationStatusResponse,
    summary="Dapatkan status job terbaru",
)
async def get_generation_status(job_id: str) -> GenerationStatusResponse:
    state = get_job_state(job_id)

    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Job '{job_id}' tidak ditemukan."},
        )

    job_status = JobStatus(state.get("status", JobStatus.QUEUED.value))
    progress = int(state.get("progress", 0))
    stage_val = state.get("stage")
    stage = GenerationStage(stage_val) if stage_val else None

    result = None
    if job_status == JobStatus.COMPLETED:
        result = GenerationResultResponse(
            job_id=job_id,
            status=job_status,
            filename=state.get("filename", ""),
            download_url=f"/api/v1/generations/{job_id}/result",
            pdf_url=state.get("pdf_url") or None,
            warnings=json.loads(state.get("warnings", "[]")),
        )

    error = None
    if job_status == JobStatus.FAILED:
        error = ErrorDetail(
            code=state.get("error_code", "UNKNOWN_ERROR"),
            message=state.get("error_message", "Terjadi kesalahan."),
            stage=stage,
        )

    return GenerationStatusResponse(
        job_id=job_id,
        status=job_status,
        stage=stage,
        progress=progress,
        message=state.get("message"),
        result=result,
        error=error,
    )


# ---------------------------------------------------------------------------
# GET /api/v1/generations/{job_id}/events  — SSE Stream
# ---------------------------------------------------------------------------

@router.get(
    "/{job_id}/events",
    summary="Subscribe ke real-time progress events (SSE)",
    description=(
        "Mengembalikan stream Server-Sent Events. "
        "Frontend mendengarkan channel ini untuk memperbarui progress bar secara real-time. "
        "Gunakan query param `last_event_index` untuk resume setelah koneksi putus."
    ),
    response_class=StreamingResponse,
)
async def stream_generation_events(
    job_id: str,
    last_event_index: int = Query(default=0, ge=0, description="Index event terakhir yang diterima client"),
    settings: Settings = Depends(get_settings),
) -> StreamingResponse:

    # Periksa apakah job ada
    if not get_job_state(job_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Job '{job_id}' tidak ditemukan."},
        )

    async def event_generator() -> AsyncGenerator[str, None]:
        """
        Generator SSE:
        1. Kirim semua event yang sudah ada (catch-up jika client baru connect / reconnect).
        2. Subscribe ke Redis pub/sub channel untuk event baru.
        3. Tutup stream saat job completed/failed/cancelled.
        """
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = r.pubsub()
        channel = f"thesa:job:{job_id}:channel"

        try:
            # --- Catch-up: kirim event yang sudah ada sejak last_event_index ---
            existing_events = get_job_events(job_id, start_index=last_event_index)
            for i, event in enumerate(existing_events):
                idx = last_event_index + i
                yield _format_sse(event, event_id=str(idx))

            # Jika job sudah terminal, tidak perlu subscribe lagi
            current_state = get_job_state(job_id)
            if current_state and current_state.get("status") in (
                JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value
            ):
                return

            # --- Subscribe ke channel untuk event baru ---
            await pubsub.subscribe(channel)

            event_index = last_event_index + len(existing_events)
            while True:
                # Keepalive agar koneksi tidak di-timeout oleh proxy
                await asyncio.sleep(settings.sse_keepalive_seconds)

                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.1)
                if message and message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        yield _format_sse(event_data, event_id=str(event_index))
                        event_index += 1

                        # Tutup stream jika sudah terminal
                        if event_data.get("status") in (
                            JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value
                        ):
                            break
                    except (json.JSONDecodeError, Exception):
                        continue

                # Keepalive ping comment
                yield ": keepalive\n\n"

        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()
            await r.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Penting untuk NGINX agar SSE tidak di-buffer
        },
    )


# ---------------------------------------------------------------------------
# GET /api/v1/generations/{job_id}/result  — Download DOCX
# ---------------------------------------------------------------------------

@router.get(
    "/{job_id}/result",
    summary="Download hasil DOCX generation",
)
async def download_result(job_id: str) -> FileResponse:
    state = get_job_state(job_id)

    if not state:
        raise HTTPException(status_code=404, detail={"code": "JOB_NOT_FOUND", "message": "Job tidak ditemukan."})

    if state.get("status") != JobStatus.COMPLETED.value:
        raise HTTPException(status_code=409, detail={"code": "JOB_NOT_READY", "message": "Job belum selesai."})

    output_path = state.get("output_path", "")
    if not output_path or not os.path.isfile(output_path):
        raise HTTPException(status_code=404, detail={"code": "FILE_NOT_FOUND", "message": "File hasil tidak ditemukan di server."})

    filename = state.get("filename", "makalah.docx")
    return FileResponse(
        path=output_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


# ---------------------------------------------------------------------------
# POST /api/v1/generations/{job_id}/cancel
# ---------------------------------------------------------------------------

@router.post(
    "/{job_id}/cancel",
    status_code=status.HTTP_200_OK,
    summary="Batalkan generation job",
)
async def cancel_generation(job_id: str) -> dict:
    success = set_job_cancelled(job_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Job '{job_id}' tidak ditemukan."},
        )

    return {"ok": True, "job_id": job_id, "message": "Job berhasil dibatalkan."}


# ---------------------------------------------------------------------------
# Helper: format SSE message
# ---------------------------------------------------------------------------

def _format_sse(data: dict, event_id: str = "") -> str:
    """Format dictionary menjadi SSE message string."""
    lines = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"data: {json.dumps(data, ensure_ascii=False)}")
    lines.append("")
    lines.append("")
    return "\n".join(lines)
