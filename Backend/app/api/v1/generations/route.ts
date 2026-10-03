/**
 * NEW: /api/v1/generations — Proxy ke FastAPI Python Backend
 *
 * Route ini menggantikan /api/generate yang memanggil python_web_bridge.py secara langsung.
 * Sekarang kita proxy request ke FastAPI yang mengelola job queue dan real-time progress.
 *
 * Migration strategy (Strangler Fig):
 *   /api/v1/generations/*  → Python FastAPI (NEW)
 *   /api/generate          → Deprecated (masih ada untuk backward compat)
 */

import { NextRequest, NextResponse } from "next/server";

const PYTHON_API_URL =
  process.env.PYTHON_API_URL || "http://localhost:8000";

/**
 * POST /api/v1/generations
 * Membuat generation job baru. Mengembalikan job_id.
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const response = await fetch(`${PYTHON_API_URL}/api/v1/generations/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      // Timeout 10s untuk request awal (bukan generation, hanya membuat job)
      signal: AbortSignal.timeout(10_000),
    });

    const data = await response.json();

    if (!response.ok) {
      return NextResponse.json(data, { status: response.status });
    }

    return NextResponse.json(data, { status: 202 });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Gagal menghubungi backend.";
    return NextResponse.json(
      {
        ok: false,
        error: { code: "PROXY_ERROR", message },
      },
      { status: 502 }
    );
  }
}
