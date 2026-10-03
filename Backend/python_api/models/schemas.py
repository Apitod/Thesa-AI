"""
Pydantic schemas untuk request dan response API Thesa.

Prinsip (sesuai api-design-principles):
- Request schema: hanya field yang diperlukan
- Response schema: konsisten, selalu ada status field
- Error response: structured, tidak mengekspos internal traceback
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ===========================================================================
# Enums
# ===========================================================================

class GenerationMode(str, Enum):
    """Mode generasi konten makalah."""
    AI_FULL = "ai_full"
    MANUAL = "manual"


class ReferenceMode(str, Enum):
    """Mode pencarian referensi."""
    SMART = "smart"
    STRICT = "strict"
    DISABLED = "disabled"


class JobStatus(str, Enum):
    """Status lifecycle sebuah generation job."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GenerationStage(str, Enum):
    """
    Tahapan proses generation.
    Setiap stage menghasilkan progress event ke frontend.
    """
    VALIDATING = "validating"
    REFERENCE_SEARCH = "reference_search"
    STRUCTURE_GENERATION = "structure_generation"
    CONTENT_GENERATION = "content_generation"
    CITATION_VALIDATION = "citation_validation"
    DOCUMENT_BUILDING = "document_building"
    EXPORT = "export"
    COMPLETED = "completed"
    FAILED = "failed"


# ===========================================================================
# Request Schemas
# ===========================================================================

class AuthorInput(BaseModel):
    """Data seorang penulis makalah."""
    nama: str = Field(..., min_length=2, description="Nama lengkap penulis")
    nim: str = Field(..., min_length=1, description="Nomor Induk Mahasiswa")


class GenerationRequest(BaseModel):
    """
    Request body untuk POST /api/v1/generations.
    Mapping dari field NeoMakalah + field tambahan Thesa.
    """
    # Identitas makalah
    judul: str = Field(..., min_length=5, description="Judul makalah")
    mata_kuliah: str = Field(..., min_length=2, description="Nama mata kuliah")
    dosen: str = Field(..., min_length=2, description="Nama dosen pengampu")

    # Penulis (minimal 1)
    authors: List[AuthorInput] = Field(..., min_length=1, max_length=3)

    # Institusi
    jurusan: str = Field(..., min_length=2)
    fakultas: str = Field(..., min_length=2)
    kampus: str = Field(..., min_length=2)
    tahun: Optional[str] = None
    tempat_pembuatan: Optional[str] = None
    tanggal_pembuatan: Optional[str] = None

    # Konfigurasi generasi
    template_name: str = Field(default="Uin Alauddin", description="Nama template dokumen")
    generation_mode: GenerationMode = Field(default=GenerationMode.AI_FULL)
    reference_mode: ReferenceMode = Field(default=ReferenceMode.SMART)
    citation_range: str = Field(
        default="5-10",
        pattern=r"^\d+-\d+$",
        description="Rentang jumlah sitasi, contoh: '5-10'"
    )

    # Konten manual (opsional, hanya untuk mode manual)
    content: Optional[Dict[str, str]] = Field(
        default=None,
        description="Konten per-section untuk mode manual"
    )

    @field_validator("citation_range")
    @classmethod
    def validate_citation_range(cls, v: str) -> str:
        parts = v.split("-")
        if int(parts[0]) >= int(parts[1]):
            raise ValueError("citation_range minimum harus lebih kecil dari maximum")
        return v


class ValidateTopicRequest(BaseModel):
    """Request body untuk POST /api/v1/validate/academic-topic."""
    judul: str = Field(..., min_length=3, description="Judul yang akan divalidasi")
    mata_kuliah: Optional[str] = None


# ===========================================================================
# Response Schemas
# ===========================================================================

class GenerationJobResponse(BaseModel):
    """
    Response saat job berhasil dibuat (POST /api/v1/generations).
    Frontend menggunakan job_id untuk polling/subscribe SSE.
    """
    job_id: str
    status: JobStatus = JobStatus.QUEUED
    message: str = "Job berhasil dibuat dan sedang dalam antrian."


class ProgressEvent(BaseModel):
    """
    Struktur event yang dikirim melalui SSE.
    Frontend memperbarui progress bar berdasarkan field ini.
    """
    job_id: str
    status: JobStatus
    stage: GenerationStage
    progress: int = Field(..., ge=0, le=100, description="Persentase progress (0-100)")
    message: str
    # Field tambahan yang mungkin ada tergantung stage
    extra: Optional[Dict[str, Any]] = None


class GenerationResultResponse(BaseModel):
    """
    Response saat job selesai (GET /api/v1/generations/{job_id}/result).
    """
    job_id: str
    status: JobStatus
    filename: str
    download_url: str
    pdf_url: Optional[str] = None
    token_usage: Optional[Dict[str, Any]] = None
    warnings: List[str] = []


class GenerationStatusResponse(BaseModel):
    """
    Response status job (GET /api/v1/generations/{job_id}).
    """
    job_id: str
    status: JobStatus
    stage: Optional[GenerationStage] = None
    progress: int = 0
    message: Optional[str] = None
    result: Optional[GenerationResultResponse] = None
    error: Optional["ErrorDetail"] = None


class ValidateTopicResponse(BaseModel):
    """Response validasi topik akademik."""
    is_academic: bool
    message: str
    reason: Optional[str] = None


# ===========================================================================
# Error Schemas
# ===========================================================================

class ErrorDetail(BaseModel):
    """Detail error yang aman dikirim ke frontend (tanpa traceback internal)."""
    code: str
    message: str
    stage: Optional[GenerationStage] = None


class ErrorResponse(BaseModel):
    """Wrapper standar untuk response error."""
    ok: bool = False
    error: ErrorDetail
