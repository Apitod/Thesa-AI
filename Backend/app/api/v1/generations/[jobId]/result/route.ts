/**
 * GET /api/v1/generations/[jobId]/result — Download hasil DOCX via proxy
 */

import { NextRequest, NextResponse } from "next/server";

const PYTHON_API_URL = process.env.PYTHON_API_URL || "http://localhost:8000";

type RouteContext = { params: Promise<{ jobId: string }> };

export async function GET(request: NextRequest, context: RouteContext) {
  const { jobId } = await context.params;
  try {
    const response = await fetch(
      `${PYTHON_API_URL}/api/v1/generations/${jobId}/result`,
      { signal: AbortSignal.timeout(30_000) }
    );

    if (!response.ok) {
      const data = await response.json();
      return NextResponse.json(data, { status: response.status });
    }

    // Stream file langsung ke browser
    const blob = await response.blob();
    const contentDisposition =
      response.headers.get("content-disposition") ??
      'attachment; filename="makalah.docx"';
    const contentType =
      response.headers.get("content-type") ??
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

    return new NextResponse(blob.stream(), {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Content-Disposition": contentDisposition,
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Gagal mendownload file.";
    return NextResponse.json(
      { ok: false, error: { code: "PROXY_ERROR", message } },
      { status: 502 }
    );
  }
}
