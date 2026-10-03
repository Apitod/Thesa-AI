"""
Router: /api/v1/validate

Endpoint validasi topik akademik secara terpisah (tanpa membuat full generation job).
Digunakan oleh Thesa UI sebelum user melanjutkan ke form generation.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import APIRouter, HTTPException, status

from python_api.models.schemas import ValidateTopicRequest, ValidateTopicResponse

router = APIRouter()


@router.post(
    "/academic-topic",
    response_model=ValidateTopicResponse,
    summary="Validasi apakah topik/judul bersifat akademik",
    description=(
        "Melakukan validasi topik menggunakan AI engine NeoMakalah. "
        "Endpoint ini ringan dan cepat karena hanya melakukan satu AI call, "
        "bukan full generation pipeline."
    ),
)
async def validate_academic_topic(request: ValidateTopicRequest) -> ValidateTopicResponse:
    """
    Validasi akademik menggunakan AI engine yang sama dengan pipeline generation.
    Dipanggil oleh Thesa frontend pada step awal form pembuatan makalah.

    Validasi dasar (panjang judul) dilakukan SEBELUM memanggil AI engine
    sehingga tidak membutuhkan API key untuk kasus-kasus trivial.
    """
    # --- Validasi cepat tanpa AI ---
    word_count = len(request.judul.strip().split())
    if word_count < 2:
        return ValidateTopicResponse(
            is_academic=False,
            message="Judul terlalu singkat. Mohon masukkan judul makalah yang lengkap.",
            reason="Judul terlalu pendek (kurang dari 2 kata).",
        )

    # --- Validasi via AI engine ---
    try:
        from src.ai_engine import get_ai_engine
        ai_engine = get_ai_engine()

        is_academic, reason = ai_engine.verify_academic_topic(request.judul)

        return ValidateTopicResponse(
            is_academic=is_academic,
            message="Topik terverifikasi akademik." if is_academic else f"Topik ditolak: {reason}",
            reason=reason,
        )

    except Exception as exc:
        # Jangan ekspos detail error internal — kembalikan error yang ramah
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "AI_UNAVAILABLE",
                "message": "Layanan validasi AI sedang tidak tersedia. Silakan coba lagi.",
            },
        )
