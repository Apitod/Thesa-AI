/**
 * POST /api/v1/validate/academic-topic
 * Proxy validasi topik akademik ke FastAPI Python.
 */

import { NextRequest, NextResponse } from "next/server";

const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const response = await fetch(
      `${PYTHON_API_URL}/api/v1/validate/academic-topic`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(30_000), // Validasi AI mungkin butuh ~10-15s
      }
    );

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Gagal menghubungi backend.";
    return NextResponse.json(
      { ok: false, error: { code: "PROXY_ERROR", message } },
      { status: 502 }
    );
  }
}
