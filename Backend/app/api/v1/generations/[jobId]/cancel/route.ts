/**
 * POST /api/v1/generations/[jobId]/cancel
 * Proxy cancel request ke FastAPI.
 */

import { NextRequest, NextResponse } from "next/server";

const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000";

type RouteContext = { params: Promise<{ jobId: string }> };

export async function POST(request: NextRequest, context: RouteContext) {
  const { jobId } = await context.params;
  try {
    const response = await fetch(
      `${PYTHON_API_URL}/api/v1/generations/${jobId}/cancel`,
      {
        method: "POST",
        signal: AbortSignal.timeout(5_000),
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
