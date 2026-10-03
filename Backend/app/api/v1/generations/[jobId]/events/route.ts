/**
 * GET /api/v1/generations/[jobId]/events — SSE proxy ke FastAPI Python
 *
 * Endpoint ini meneruskan (proxy) SSE stream dari FastAPI ke browser.
 * Penting: Next.js App Router mendukung streaming response secara native.
 *
 * Frontend Thesa cukup connect ke:
 *   new EventSource('/api/v1/generations/<jobId>/events')
 *
 * Dan progress real-time dari backend Python akan langsung diterima.
 */

import { NextRequest } from "next/server";

const PYTHON_API_URL =
  process.env.PYTHON_API_URL || "http://localhost:8000";

type RouteContext = { params: Promise<{ jobId: string }> };

export const dynamic = "force-dynamic";
export const runtime = "nodejs"; // SSE butuh Node.js runtime, bukan Edge

export async function GET(request: NextRequest, context: RouteContext) {
  const { jobId } = await context.params;

  // Forward query param last_event_index untuk SSE resume
  const lastEventIndex =
    request.nextUrl.searchParams.get("last_event_index") ?? "0";

  const upstreamUrl = new URL(
    `/api/v1/generations/${jobId}/events`,
    PYTHON_API_URL
  );
  upstreamUrl.searchParams.set("last_event_index", lastEventIndex);

  try {
    const upstream = await fetch(upstreamUrl.toString(), {
      headers: { Accept: "text/event-stream" },
      // Tidak ada timeout — SSE adalah long-running connection
    });

    if (!upstream.ok || !upstream.body) {
      return new Response(
        JSON.stringify({ ok: false, error: "SSE upstream tidak tersedia." }),
        { status: 502, headers: { "Content-Type": "application/json" } }
      );
    }

    // Pipe stream langsung dari Python FastAPI ke browser
    return new Response(upstream.body, {
      status: 200,
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "SSE proxy error.";
    return new Response(`data: ${JSON.stringify({ ok: false, error: message })}\n\n`, {
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
    });
  }
}
