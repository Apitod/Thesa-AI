"""
Generation Tasks — Celery worker tasks untuk pipeline pembuatan makalah.

Setiap task memanggil engine NeoMakalah secara berurutan dan
melaporkan progress nyata melalui progress_reporter ke Redis.

Pipeline:
  1. VALIDATING       (0–10%)
  2. REFERENCE_SEARCH (10–30%)
  3. STRUCTURE & AI   (30–75%)   ← content_generation
  4. DOCUMENT_BUILDING(75–92%)
  5. EXPORT / TOC     (92–99%)
  6. COMPLETED        (100%)

Prinsip:
- Setiap stage memanggil emit_progress() SEBELUM mulai dan saat selesai.
- Error internal TIDAK di-raise ke frontend — hanya kode error + pesan ramah.
- Worker memeriksa flag "cancelled" sebelum lanjut ke stage berikutnya.
"""

import contextlib
import io
import json
import os
import re
import sys
import traceback
from typing import Any, Dict, Optional
from urllib.parse import quote

# Tambahkan root Backend ke path agar engine NeoMakalah bisa diimport
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from python_api.worker.celery_app import celery_app
from python_api.models.schemas import GenerationStage, JobStatus
from python_api.services.progress_reporter import (
    emit_progress,
    emit_result,
    emit_failure,
    get_job_state,
)
from python_api.config import settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def generate_fancy_toc(content: dict) -> tuple:
    """Builds a dictionary of TOC entries for granular document placeholders."""
    # 1. Extract Sub-headings from Pembahasan
    pembahasan_text = content.get('pembahasan', '')
    sub_headings = re.findall(r'^[A-Z]\.\s+(.+)$', pembahasan_text, re.MULTILINE)

    def _clean_t(t):
        t = t.strip()
        return (t[:60] + "...") if len(t) > 60 else t

    titles = {
        'pembahasan1': _clean_t(sub_headings[0]) if len(sub_headings) > 0 else "Pembahasan Utama",
        'pembahasan2': _clean_t(sub_headings[1]) if len(sub_headings) > 1 else "Tinjauan Kasus",
        'pembahasan3': _clean_t(sub_headings[2]) if len(sub_headings) > 2 else "Analisis Mendalam",
        'pembahasan4': _clean_t(sub_headings[3]) if len(sub_headings) > 3 else "Penerapan Praktis",
    }

    rm_text = content.get('rumusan_masalah', '').split('\n')[0].replace('**', '').replace('"', '').strip()
    titles['rumusan_masalah'] = rm_text[:45] + "..." if len(rm_text) > 45 else rm_text

    tj_text = content.get('tujuan', '').split('\n')[0].replace('**', '').replace('"', '').strip()
    titles['tujuan'] = tj_text[:45] + "..." if len(tj_text) > 45 else tj_text

    # Using real Tab Stops (\t) for a truly tidy and professional Look
    def add_dots(left_text, page):
        clean_text = left_text.replace('**', '').strip()
        return f"{clean_text}\t{page}"

    search_targets = {
        "KATA PENGANTAR": "__PG_KATA__",
        "DAFTAR ISI": "__PG_TOC__",
        "BAB I PENDAHULUAN": "__PG_BAB1__",
        "Latar Belakang": "__PG_LATAR__",
        "Rumusan Masalah": "__PG_RUMUSAN__",
        "Tujuan Penelitian": "__PG_TUJUAN__",
        "BAB II PEMBAHASAN": "__PG_BAB2__",
        f"{titles['pembahasan1']}": "__PG_B2_1__",
        f"{titles['pembahasan2']}": "__PG_B2_2__",
        f"{titles['pembahasan3']}": "__PG_B2_3__",
        f"{titles['pembahasan4']}": "__PG_B2_4__",
        "BAB III PENUTUP": "__PG_BAB3__",
        "Kesimpulan": "__PG_KESIMPULAN__",
        "DAFTAR PUSTAKA": "__PG_PUSTAKA__"
    }

    # Create a mapping for each granular placeholder
    toc_data = {
        "di_kata_pengantar": add_dots("KATA PENGANTAR", search_targets["KATA PENGANTAR"]),
        "di_daftar_isi": add_dots("DAFTAR ISI", search_targets["DAFTAR ISI"]),
        "di_bab_1": add_dots("BAB I PENDAHULUAN", search_targets["BAB I PENDAHULUAN"]),
        "di_latar_belakang": add_dots("    A. Latar Belakang", search_targets["Latar Belakang"]),
        "di_rumusan_masalah": add_dots("    B. Rumusan Masalah", search_targets["Rumusan Masalah"]),
        "di_tujuan_penelitian": add_dots("    C. Tujuan Penelitian", search_targets["Tujuan Penelitian"]),
        "di_bab_2": add_dots("BAB II PEMBAHASAN", search_targets["BAB II PEMBAHASAN"]),
        "di_bab_2_1": add_dots(f"    A. {titles['pembahasan1']}", search_targets[f"{titles['pembahasan1']}"]),
        "di_bab_2_2": add_dots(f"    B. {titles['pembahasan2']}", search_targets[f"{titles['pembahasan2']}"]),
        "di_bab_2_3": add_dots(f"    C. {titles['pembahasan3']}", search_targets[f"{titles['pembahasan3']}"]),
        "di_bab_2_4": add_dots(f"    D. {titles['pembahasan4']}", search_targets[f"{titles['pembahasan4']}"]),
        "di_bab_3 ": add_dots("BAB III PENUTUP", search_targets["BAB III PENUTUP"]),
        "di_kesimpulan ": add_dots("    A. Kesimpulan", search_targets["Kesimpulan"]),
        "di_daftar_pustaka": add_dots("DAFTAR PUSTAKA", search_targets["DAFTAR PUSTAKA"])
    }

    return toc_data, search_targets


def _is_cancelled(job_id: str) -> bool:
    """Cek apakah job sudah di-cancel oleh user."""
    state = get_job_state(job_id)
    if not state:
        return False
    return state.get("status") == JobStatus.CANCELLED.value


def _suppress_stdout():
    """Context manager untuk menekan stdout dari engine NeoMakalah (rich console, dsb.)."""
    return contextlib.redirect_stdout(io.StringIO())


# ---------------------------------------------------------------------------
# Main generation task
# ---------------------------------------------------------------------------

@celery_app.task(
    bind=True,
    name="thesa.generate_paper",
    max_retries=0,       # Tidak retry — kegagalan harus dilaporkan ke user
    time_limit=900,      # Hard limit 15 menit
    soft_time_limit=840, # Soft limit 14 menit (graceful shutdown)
)
def generate_paper_task(self, job_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Celery task utama untuk pipeline generation makalah.

    Args:
        job_id:  ID unik job (dibuat di FastAPI sebelum dispatch task ini).
        payload: Dict yang berisi semua field dari GenerationRequest.

    Returns:
        Dict hasil akhir (untuk Celery result backend), namun hasil utama
        dikirim via Redis/SSE melalui progress_reporter.
    """
    try:
        return _run_pipeline(job_id, payload)
    except Exception as exc:
        # Catat traceback lengkap di server log
        tb = traceback.format_exc()
        print(f"[WORKER ERROR] job_id={job_id}\n{tb}", file=sys.stderr)

        # Kirim error yang aman ke frontend (tanpa traceback)
        emit_failure(
            job_id=job_id,
            stage=GenerationStage.FAILED,
            error_code="INTERNAL_ERROR",
            message="Terjadi kesalahan internal pada server. Tim kami sedang menginvestigasi.",
        )
        return {"ok": False, "job_id": job_id, "error": str(exc)}


def _run_pipeline(job_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Menjalankan seluruh pipeline generation secara berurutan.
    Setiap stage memanggil emit_progress() untuk real-time update.
    """

    # -----------------------------------------------------------------------
    # Stage 1: VALIDATING (0–10%)
    # -----------------------------------------------------------------------
    emit_progress(
        job_id=job_id,
        stage=GenerationStage.VALIDATING,
        progress=2,
        message="Memvalidasi data makalah...",
    )

    if _is_cancelled(job_id):
        return {"ok": False, "cancelled": True}

    with _suppress_stdout():
        from src.ai_engine import get_ai_engine
        ai_engine = get_ai_engine()

    judul = payload.get("judul", "")

    # Validasi panjang judul
    if len(judul.strip().split()) < 2:
        emit_failure(
            job_id=job_id,
            stage=GenerationStage.VALIDATING,
            error_code="INVALID_TITLE",
            message="Judul terlalu singkat. Mohon masukkan judul makalah yang lengkap.",
        )
        return {"ok": False}

    emit_progress(
        job_id=job_id,
        stage=GenerationStage.VALIDATING,
        progress=5,
        message="Memverifikasi relevansi akademik judul...",
    )

    if _is_cancelled(job_id):
        return {"ok": False, "cancelled": True}

    # Validasi topik akademik via AI
    is_academic, reason = ai_engine.verify_academic_topic(judul)
    if not is_academic:
        emit_failure(
            job_id=job_id,
            stage=GenerationStage.VALIDATING,
            error_code="NON_ACADEMIC_TOPIC",
            message=f"Topik ditolak: {reason}",
        )
        return {"ok": False}

    emit_progress(
        job_id=job_id,
        stage=GenerationStage.VALIDATING,
        progress=10,
        message="Validasi selesai. Judul terverifikasi akademik.",
    )

    # -----------------------------------------------------------------------
    # Stage 2: REFERENCE_SEARCH (10–30%)
    # -----------------------------------------------------------------------
    if _is_cancelled(job_id):
        return {"ok": False, "cancelled": True}

    emit_progress(
        job_id=job_id,
        stage=GenerationStage.REFERENCE_SEARCH,
        progress=12,
        message="Mencari referensi akademik yang relevan...",
    )

    reference_mode = payload.get("reference_mode", "smart")
    citation_range = payload.get("citation_range", "5-10")
    try:
        cit_min, cit_max = [int(x) for x in citation_range.split("-")]
    except (ValueError, AttributeError):
        cit_min, cit_max = 5, 10

    mata_kuliah = payload.get("mata_kuliah", "")
    context = _build_context(payload)
    candidates = []
    formatted_refs = []

    with _suppress_stdout():
        try:
            from src.reference_engine import get_reference_engine
            ref_engine = get_reference_engine()
            candidates, formatted_refs = ref_engine.search_references(
                judul=judul,
                mata_kuliah=mata_kuliah,
                mode=reference_mode,
                citation_min=cit_min,
                citation_max=cit_max,
            )
        except Exception as ref_err:
            # Referensi gagal bukan fatal, lanjutkan dengan warning
            print(f"[WARNING] Reference search gagal: {ref_err}", file=sys.stderr)

    if formatted_refs:
        context["real_journals"] = formatted_refs

    emit_progress(
        job_id=job_id,
        stage=GenerationStage.REFERENCE_SEARCH,
        progress=30,
        message=f"Ditemukan {len(candidates)} referensi akademik.",
        extra={"reference_count": len(candidates)},
    )

    # -----------------------------------------------------------------------
    # Stage 3: CONTENT_GENERATION (30–75%)
    # -----------------------------------------------------------------------
    if _is_cancelled(job_id):
        return {"ok": False, "cancelled": True}

    emit_progress(
        job_id=job_id,
        stage=GenerationStage.CONTENT_GENERATION,
        progress=33,
        message="Memulai generasi konten makalah dengan AI...",
    )

    content = {}
    generation_mode = payload.get("generation_mode", "ai_full")
    AI_SECTIONS = [
        "kata_pengantar", "latar_belakang", "rumusan_masalah",
        "tujuan", "pembahasan", "kesimpulan", "daftar_pustaka"
    ]

    with _suppress_stdout():
        if generation_mode == "ai_full":
            emit_progress(
                job_id=job_id,
                stage=GenerationStage.CONTENT_GENERATION,
                progress=40,
                message="Menyusun seluruh bagian makalah dengan AI...",
            )
            generated = ai_engine.generate_full_paper(
                context, context,
                reference_mode=reference_mode,
                citation_min=cit_min,
                citation_max=cit_max,
            )
            for section in AI_SECTIONS:
                if generated.get(section):
                    content[section] = generated[section]

        elif generation_mode == "manual":
            incoming = payload.get("content") or {}
            content = {s: str(incoming.get(s, "")) for s in AI_SECTIONS}

    emit_progress(
        job_id=job_id,
        stage=GenerationStage.CONTENT_GENERATION,
        progress=75,
        message="Konten makalah berhasil disusun.",
    )

    # -----------------------------------------------------------------------
    # Stage 4: DOCUMENT_BUILDING (75–92%)
    # -----------------------------------------------------------------------
    if _is_cancelled(job_id):
        return {"ok": False, "cancelled": True}

    emit_progress(
        job_id=job_id,
        stage=GenerationStage.DOCUMENT_BUILDING,
        progress=78,
        message="Menyusun dokumen DOCX...",
    )

    SECTION_FIELDS = [
        "kata_pengantar", "latar_belakang", "rumusan_masalah",
        "tujuan", "pembahasan", "kesimpulan", "daftar_pustaka"
    ]

    output_path = None
    filename = None

    with _suppress_stdout():
        from src.document_builder import get_document_builder
        from src.template_engine import get_template_engine

        document_builder = get_document_builder()
        template_engine = get_template_engine()

        # Post-process sections
        for section_key in SECTION_FIELDS:
            if content.get(section_key, "").strip():
                content[section_key] = document_builder.format_section(content[section_key], section_key)

        # Build TOC
        toc_entries, search_targets = generate_fancy_toc(content)
        content.update(toc_entries)

        # Build metadata structs
        metadata, authors, institution = _extract_metadata(payload)
        complete_data = document_builder.build_complete_paper_data(metadata, authors, institution, content)

        template_name = payload.get("template_name", "Uin Alauddin")
        template_document = template_engine.load_template(template_name)
        final_document = document_builder.build_document(template_document, complete_data)

        filename = document_builder.generate_filename(metadata)
        output_path = document_builder.save_document(final_document, filename)

    emit_progress(
        job_id=job_id,
        stage=GenerationStage.DOCUMENT_BUILDING,
        progress=88,
        message="Dokumen DOCX berhasil disusun.",
    )

    # -----------------------------------------------------------------------
    # Stage 5: EXPORT / TOC (92–99%)
    # -----------------------------------------------------------------------
    if _is_cancelled(job_id):
        return {"ok": False, "cancelled": True}

    emit_progress(
        job_id=job_id,
        stage=GenerationStage.EXPORT,
        progress=92,
        message="Menjalankan TOC pipeline dan ekspor PDF...",
    )

    pdf_url = None
    pdf_filename = filename.replace(".docx", ".pdf")
    pdf_output_path = output_path.replace(".docx", ".pdf")

    with _suppress_stdout():
        try:
            from src.toc_engine import run_toc_pipeline
            toc_success, toc_pdf_path = run_toc_pipeline(
                docx_path=output_path,
                pdf_output_path=pdf_output_path,
                search_targets=search_targets,
            )
            if toc_success and toc_pdf_path:
                pdf_url = f"/api/v1/generations/{job_id}/result/pdf"
        except Exception as toc_err:
            print(f"[WARNING] TOC pipeline gagal: {toc_err}", file=sys.stderr)

    # Few-shot cache
    with _suppress_stdout():
        try:
            from src.fewshot_cache import get_fewshot_cache
            fsc = get_fewshot_cache()
            fsc.save_generation(
                judul=metadata.get("judul", ""),
                mata_kuliah=metadata.get("mata_kuliah", ""),
                content=content,
            )
        except Exception:
            pass

    emit_progress(
        job_id=job_id,
        stage=GenerationStage.EXPORT,
        progress=99,
        message="Ekspor selesai.",
    )

    # -----------------------------------------------------------------------
    # Stage 6: COMPLETED (100%)
    # -----------------------------------------------------------------------
    from src.token_logger import get_total_usage
    token_usage = get_total_usage()

    emit_result(
        job_id=job_id,
        filename=filename,
        output_path=output_path,
        download_url=f"/api/v1/generations/{job_id}/result",
        pdf_url=pdf_url,
        token_usage=token_usage,
    )

    return {"ok": True, "job_id": job_id, "filename": filename}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _build_context(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Gabungkan metadata + institusi menjadi satu context dict untuk AI engine."""
    authors = payload.get("authors", [])
    penulis_1 = authors[0] if authors else {}
    return {
        "mata_kuliah": payload.get("mata_kuliah", "").upper(),
        "judul": payload.get("judul", "").upper(),
        "dosen": payload.get("dosen", ""),
        "jurusan": payload.get("jurusan", "").upper(),
        "fakultas": payload.get("fakultas", "").upper(),
        "kampus": payload.get("kampus", "").upper(),
        "tahun": payload.get("tahun", ""),
        "tempat_pembuatan": payload.get("tempat_pembuatan", ""),
        "tanggal_pembuatan": payload.get("tanggal_pembuatan", ""),
    }


def _extract_metadata(payload: Dict[str, Any]):
    """Ekstrak metadata, authors, institution dari payload sesuai format NeoMakalah."""
    metadata = {
        "mata_kuliah": payload.get("mata_kuliah", "").upper(),
        "judul": payload.get("judul", "").upper(),
        "dosen": payload.get("dosen", ""),
    }
    raw_authors = payload.get("authors", [])
    authors = [{"nama": a.get("nama", ""), "nim": a.get("nim", "")} for a in raw_authors]

    institution = {
        "jurusan": payload.get("jurusan", "").upper(),
        "fakultas": payload.get("fakultas", "").upper(),
        "kampus": payload.get("kampus", "").upper(),
        "tahun": payload.get("tahun", ""),
        "tempat_pembuatan": payload.get("tempat_pembuatan", ""),
        "tanggal_pembuatan": payload.get("tanggal_pembuatan", ""),
    }
    return metadata, authors, institution
