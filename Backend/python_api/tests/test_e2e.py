#!/usr/bin/env python3
"""
Test Script End-to-End — Thesa Python API
Fase 3 QA (sesuai skill: agent-qa-debug-fix)

Menguji:
1. Health check API
2. Validasi topik akademik
3. Membuat generation job
4. Subscribe SSE dan terima progress events
5. Download hasil DOCX

Cara jalankan (setelah FastAPI server berjalan):
    python3 tests/test_e2e.py

Atau dengan API key langsung:
    OPENROUTER_API_KEY=<key> python3 tests/test_e2e.py
"""

import json
import os
import sys
import time
import threading
import urllib.request
import urllib.error

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# ANSI Colors
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"


def ok(msg):  print(f"  {GREEN}✅ {msg}{RESET}")
def fail(msg): print(f"  {RED}❌ {msg}{RESET}")
def info(msg): print(f"  {CYAN}ℹ  {msg}{RESET}")
def warn(msg): print(f"  {YELLOW}⚠  {msg}{RESET}")
def header(msg): print(f"\n{BOLD}{CYAN}{'='*60}{RESET}\n{BOLD}{msg}{RESET}\n{'='*60}")


def http_get(path, timeout=10):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode()), resp.status


def http_post(path, data, timeout=30):
    url = f"{BASE_URL}{path}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode()), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode()), e.code


# ===========================================================================
# Test 1: Health Check
# ===========================================================================

def test_health():
    header("TEST 1: Health Check")
    try:
        data, status = http_get("/api/v1/health")
        assert status == 200, f"Expected 200, got {status}"
        assert data.get("status") == "ok", f"Expected status=ok, got: {data}"
        ok(f"Health check: {data}")
    except Exception as e:
        fail(f"Health check gagal: {e}")
        sys.exit(1)


# ===========================================================================
# Test 2: Validasi Topik Akademik
# ===========================================================================

def test_validate_academic_topic():
    header("TEST 2: Validasi Topik Akademik")

    # Kasus valid
    try:
        data, status = http_post(
            "/api/v1/validate/academic-topic",
            {"judul": "Pengaruh Media Sosial terhadap Prestasi Akademik Mahasiswa"},
            timeout=60,
        )
        info(f"Response: {data}")
        if data.get("is_academic"):
            ok("Topik akademik valid dikenali dengan benar")
        else:
            warn(f"AI menolak topik (mungkin API key belum diset): {data.get('message')}")
    except Exception as e:
        warn(f"Validasi topik gagal (pastikan API key tersedia): {e}")

    # Kasus invalid (judul terlalu pendek)
    try:
        data, status = http_post(
            "/api/v1/validate/academic-topic",
            {"judul": "halo"},
        )
        assert not data.get("is_academic"), "Seharusnya ditolak"
        ok(f"Judul pendek ditolak dengan benar: {data.get('message')}")
    except Exception as e:
        fail(f"Validasi judul pendek gagal: {e}")


# ===========================================================================
# Test 3: Buat Generation Job
# ===========================================================================

def test_create_generation_job():
    header("TEST 3: Buat Generation Job")

    payload = {
        "judul": "Dampak Kecerdasan Buatan terhadap Dunia Pendidikan Tinggi di Indonesia",
        "mata_kuliah": "Teknologi Pendidikan",
        "dosen": "Dr. Ahmad Fauzi, M.Pd.",
        "authors": [
            {"nama": "Budi Santoso", "nim": "12345678"},
        ],
        "jurusan": "Teknologi Pendidikan",
        "fakultas": "Fakultas Ilmu Pendidikan",
        "kampus": "Universitas Negeri Jakarta",
        "tahun": "2026",
        "generation_mode": "ai_full",
        "reference_mode": "smart",
        "citation_range": "5-10",
    }

    try:
        data, status = http_post("/api/v1/generations/", payload, timeout=15)
        info(f"Response ({status}): {data}")

        assert status == 202, f"Expected 202, got {status}"
        assert "job_id" in data, f"job_id tidak ada di response: {data}"
        assert data.get("status") == "queued", f"Expected queued, got {data.get('status')}"

        job_id = data["job_id"]
        ok(f"Job berhasil dibuat: job_id={job_id}")
        return job_id

    except AssertionError as e:
        fail(f"Assertion gagal: {e}")
        return None
    except Exception as e:
        fail(f"Gagal membuat generation job: {e}")
        return None


# ===========================================================================
# Test 4: Status Job & SSE Events
# ===========================================================================

def test_job_status(job_id: str):
    header("TEST 4: Status Job")

    try:
        data, status = http_get(f"/api/v1/generations/{job_id}")
        info(f"Status response: {data}")
        assert "job_id" in data
        assert "status" in data
        ok(f"Status job: {data.get('status')} | progress: {data.get('progress')}%")
    except Exception as e:
        fail(f"Status job gagal: {e}")


def test_sse_stream(job_id: str, timeout_seconds: int = 300):
    header("TEST 5: SSE Progress Stream (real-time)")
    info(f"Mendengarkan events untuk job {job_id}...")
    info(f"Timeout: {timeout_seconds}s")

    url = f"{BASE_URL}/api/v1/generations/{job_id}/events"
    events_received = []
    completed = threading.Event()
    last_progress = 0

    def listen():
        nonlocal last_progress
        try:
            req = urllib.request.Request(
                url,
                headers={"Accept": "text/event-stream"},
            )
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                buffer = ""
                for line_bytes in resp:
                    line = line_bytes.decode("utf-8").rstrip()
                    if line.startswith("data: "):
                        data_str = line[6:]
                        try:
                            event = json.loads(data_str)
                            events_received.append(event)
                            stage    = event.get("stage", "")
                            progress = event.get("progress", 0)
                            message  = event.get("message", "")
                            status   = event.get("status", "")

                            if progress > last_progress:
                                print(f"  {GREEN}[{progress:3d}%]{RESET} {CYAN}[{stage}]{RESET} {message}")
                                last_progress = progress

                            if status in ("completed", "failed", "cancelled"):
                                completed.set()
                                break
                        except json.JSONDecodeError:
                            pass
                    elif line.startswith(":"):
                        pass  # keepalive, abaikan
        except Exception as e:
            warn(f"SSE stream error: {e}")
            completed.set()

    thread = threading.Thread(target=listen, daemon=True)
    thread.start()

    completed.wait(timeout=timeout_seconds)

    if not events_received:
        warn("Tidak ada SSE events yang diterima (mungkin worker belum berjalan)")
        return None

    last_event = events_received[-1]
    final_status = last_event.get("status")

    if final_status == "completed":
        ok(f"Generation selesai! Total events: {len(events_received)}")
    elif final_status == "failed":
        fail(f"Generation gagal: {last_event.get('extra', {}).get('error_code')}")
    else:
        warn(f"Stream berakhir dengan status: {final_status}")

    return last_event


# ===========================================================================
# Test 6: Download Result
# ===========================================================================

def test_download_result(job_id: str):
    header("TEST 6: Download Hasil DOCX")

    try:
        url = f"{BASE_URL}/api/v1/generations/{job_id}/result"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=30) as resp:
            content_type = resp.headers.get("Content-Type", "")
            content_length = resp.headers.get("Content-Length", "?")
            ok(f"Download berhasil: Content-Type={content_type}, Size={content_length} bytes")
    except urllib.error.HTTPError as e:
        if e.code == 409:
            warn("Job belum selesai — download belum tersedia (expected jika test cepat)")
        else:
            fail(f"Download gagal: HTTP {e.code}")
    except Exception as e:
        fail(f"Download error: {e}")


# ===========================================================================
# Test 7: Cancel Job
# ===========================================================================

def test_cancel_nonexistent_job():
    header("TEST 7: Cancel Job Tidak Ditemukan")
    try:
        data, status = http_post(
            "/api/v1/generations/nonexistent-job-id-12345/cancel",
            {},
            timeout=5,
        )
        assert status == 404, f"Expected 404, got {status}"
        ok(f"404 dikembalikan dengan benar untuk job tidak ada")
    except Exception as e:
        fail(f"Test cancel gagal: {e}")


# ===========================================================================
# Main
# ===========================================================================

if __name__ == "__main__":
    print(f"\n{BOLD}{'='*60}")
    print(f"  THESA PYTHON API — End-to-End Test")
    print(f"  Base URL: {BASE_URL}")
    print(f"{'='*60}{RESET}")

    # Test 1: Server alive
    test_health()

    # Test 2: Validasi topik
    test_validate_academic_topic()

    # Test 3: Buat job
    job_id = test_create_generation_job()

    if job_id:
        # Test 4: Status awal
        test_job_status(job_id)

        # Test 5: SSE stream (tunggu hingga selesai, max 5 menit)
        last_event = test_sse_stream(job_id, timeout_seconds=300)

        # Test 6: Download jika selesai
        if last_event and last_event.get("status") == "completed":
            test_download_result(job_id)

    # Test 7: Error handling
    test_cancel_nonexistent_job()

    print(f"\n{BOLD}{GREEN}{'='*60}")
    print(f"  Test selesai.")
    print(f"{'='*60}{RESET}\n")
