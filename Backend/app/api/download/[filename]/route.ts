import fs from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const revalidate = 0;

const DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";

export async function GET(
  _request: Request,
  context: { params: Promise<{ filename: string }> }
) {
  const params = await context.params;
  const fileName = params.filename;
  const safeName = path.basename(fileName);

  if (!safeName || safeName !== fileName) {
    return NextResponse.json({ ok: false, error: "Nama file tidak valid." }, { status: 400 });
  }

  const filePath = path.join(process.cwd(), "output", safeName);
  const isPdf = safeName.toLowerCase().endsWith('.pdf');
  const mimeType = isPdf ? "application/pdf" : DOCX_MIME;
  const disposition = isPdf ? "inline" : "attachment";

  try {
    const buffer = await fs.readFile(filePath);
    return new NextResponse(buffer, {
      status: 200,
      headers: {
        "Content-Type": mimeType,
        "Content-Disposition": `${disposition}; filename="${encodeURIComponent(safeName)}"`,
        "Cache-Control": "no-store"
      }
    });
  } catch {
    return NextResponse.json({ ok: false, error: "File tidak ditemukan." }, { status: 404 });
  }
}
