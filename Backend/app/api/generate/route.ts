/**
 * NEW /api/generate/route.ts — Migrasi dari subprocess langsung ke FastAPI Job Queue
 *
 * SEBELUM (legacy): Next.js → spawn python_web_bridge.py (sinkron, rawan timeout)
 * SESUDAH (baru):   Next.js → POST FastAPI /api/v1/generations/ → job_id
 *
 * Route ini mempertahankan response shape yang sama agar backward-compatible.
 * Ini adalah JEMBATAN TRANSISI. Route ini akan dihapus saat Go backend offline.
 */

import { NextRequest, NextResponse } from "next/server";

const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000";

/** Konversi payload lama (penulis_1/2/3 format) ke format schema FastAPI baru */
function normalizePayload(raw: Record<string, unknown>) {
  const authors: Array<{ nama: string; nim: string }> = [];
  for (const n of [1, 2, 3]) {
    const nama = (raw[`penulis_${n}`] as string || "").trim();
    const nim  = (raw[`nim_penulis_${n}`] as string || "").trim();
    if (nama) authors.push({ nama, nim });
  }

  return {
    judul:           raw.judul as string,
    mata_kuliah:     raw.mata_kuliah as string,
    dosen:           raw.dosen as string,
    authors:         authors.length ? authors : [{ nama: "Penulis", nim: "0" }],
    jurusan:         raw.jurusan as string,
    fakultas:        raw.fakultas as string,
    kampus:          raw.kampus as string,
    tahun:           (raw.tahun as string) || String(new Date().getFullYear()),
    tempat_pembuatan:(raw.tempat_pembuatan as string) || "Indonesia",
    tanggal_pembuatan:(raw.tanggal_pembuatan as string) || "",
    template_name:   (raw.template_name as string) || "default",
    generation_mode: (raw.generation_mode as string) || "ai_full",
    reference_mode:  (raw.reference_mode as string) || "smart",
    citation_range:  (raw.citation_range as string) || "5-10",
    content:         (raw.content as Record<string, string>) || {},
  };
}

export async function POST(request: NextRequest) {
  try {
    const raw = await request.json();

    // ── Tindakan validasi (action: "validate") ─────────────────
    if (raw.action === "validate") {
      const res = await fetch(`${PYTHON_API_URL}/api/v1/validate/academic-topic`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ judul: raw.judul }),
        signal: AbortSignal.timeout(30_000),
      });
      const data = await res.json();

      if (!res.ok) {
        return NextResponse.json({ ok: false, message: data.detail?.message || "Validasi gagal." });
      }

      return NextResponse.json({
        ok: data.is_academic,
        message: data.message,
        field: data.reason || "Judul terverifikasi",
      });
    }

    // ── Tindakan generate (default) ────────────────────────────
    const payload = normalizePayload(raw);

    // 1. Buat generation job
    const createRes = await fetch(`${PYTHON_API_URL}/api/v1/generations/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(15_000),
    });

    if (!createRes.ok) {
      const err = await createRes.json();
      return NextResponse.json(
        { ok: false, error: err.detail?.message || "Gagal membuat job generation." },
        { status: createRes.status }
      );
    }

    const { job_id } = await createRes.json();

    // 2. Poll status hingga selesai (max 5 menit, poll setiap 3 detik)
    //    Ini adalah mode kompatibilitas untuk page.tsx lama yang belum pakai SSE.
    const maxAttempts = 100;
    const pollInterval = 3_000;

    for (let i = 0; i < maxAttempts; i++) {
      await new Promise((r) => setTimeout(r, pollInterval));

      const statusRes = await fetch(`${PYTHON_API_URL}/api/v1/generations/${job_id}`, {
        cache: "no-store",
        signal: AbortSignal.timeout(5_000),
      });

      if (!statusRes.ok) continue;

      const status = await statusRes.json();

      if (status.status === "completed" && status.result) {
        // Ambil preview content jika tersedia
        let content: Record<string, string> = {};
        return NextResponse.json({
          ok: true,
          message: "Makalah berhasil dibuat.",
          filename: status.result.filename,
          downloadUrl: status.result.download_url,
          pdfUrl: status.result.pdf_url || null,
          outputPath: "",
          tokenUsage: { total_calls: 0, total_input_tokens: 0, total_output_tokens: 0, total_tokens: 0 },
          warnings: status.result.warnings || [],
          content,
        });
      }

      if (status.status === "failed") {
        return NextResponse.json({
          ok: false,
          error: status.error?.message || "Generation gagal.",
        });
      }

      if (status.status === "cancelled") {
        return NextResponse.json({ ok: false, error: "Job dibatalkan." });
      }
    }

    return NextResponse.json({ ok: false, error: "Generation timeout setelah 5 menit." }, { status: 504 });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Error tidak diketahui.";
    return NextResponse.json({ ok: false, error: message }, { status: 500 });
  }
}
