"use client";

import { FormEvent, useMemo, useState, useEffect } from "react";

type GenerationMode = "manual" | "ai_full";
type ReferenceMode = "fast" | "smart" | "strict";
type CitationRange = "5-10" | "10-15" | "20-25";
type SectionKey =
  | "kata_pengantar"
  | "daftar_isi"
  | "latar_belakang"
  | "rumusan_masalah"
  | "tujuan"
  | "pembahasan"
  | "kesimpulan"
  | "daftar_pustaka";

type PaperForm = {
  mata_kuliah: string;
  judul: string;
  dosen: string;
  penulis_1: string;
  nim_penulis_1: string;
  penulis_2: string;
  nim_penulis_2: string;
  penulis_3: string;
  nim_penulis_3: string;
  jurusan: string;
  fakultas: string;
  kampus: string;
  tahun: string;
  tempat_pembuatan: string;
  tanggal_pembuatan: string;
  template_name: string;
  generation_mode: GenerationMode;
  reference_mode: ReferenceMode;
  citation_range: CitationRange;
  content: Record<SectionKey, string>;
};

type GenerationResult = {
  ok: boolean;
  message: string;
  filename: string;
  downloadUrl: string;
  pdfUrl?: string | null;
  outputPath: string;
  tokenUsage: {
    total_calls: number;
    total_input_tokens: number;
    total_output_tokens: number;
    total_tokens: number;
  };
  warnings: string[];
  content: Record<string, string>;
};

const SECTION_LABELS: { key: SectionKey; label: string }[] = [
  { key: "kata_pengantar", label: "Kata Pengantar" },
  { key: "latar_belakang", label: "Latar Belakang" },
  { key: "rumusan_masalah", label: "Rumusan Masalah" },
  { key: "tujuan", label: "Tujuan" },
  { key: "pembahasan", label: "Pembahasan" },
  { key: "kesimpulan", label: "Kesimpulan" }
];

function todayLabel(): string {
  return new Date().toLocaleDateString("id-ID", { day: "2-digit", month: "long", year: "numeric" });
}

function getInitialForm(): PaperForm {
  return {
    mata_kuliah: "",
    judul: "",
    dosen: "",
    penulis_1: "",
    nim_penulis_1: "",
    penulis_2: "",
    nim_penulis_2: "",
    penulis_3: "",
    nim_penulis_3: "",
    jurusan: "",
    fakultas: "",
    kampus: "UIN Alauddin Makassar",
    tahun: `${new Date().getFullYear()}`,
    tempat_pembuatan: "Makassar",
    tanggal_pembuatan: todayLabel(),
    template_name: "Uin Alauddin",
    generation_mode: "manual",
    reference_mode: "smart",
    citation_range: "5-10",
    content: {
      kata_pengantar: "",
      daftar_isi: "",
      latar_belakang: "",
      rumusan_masalah: "",
      tujuan: "",
      pembahasan: "",
      kesimpulan: "",
      daftar_pustaka: ""
    }
  };
}

export default function HomePage() {
  const [form, setForm] = useState<PaperForm>(getInitialForm());
  const [result, setResult] = useState<GenerationResult | null>(null);
  const [error, setError] = useState<string>("");
  const [step, setStep] = useState<"idle" | "validating" | "validated" | "generating" | "success">("idle");
  const [validationResult, setValidationResult] = useState<{ is_academic: boolean; reason: string; field?: string } | null>(null);
  const [authorCount, setAuthorCount] = useState<number>(1);
  const [progress, setProgress] = useState<number>(0);
  const [progressStage, setProgressStage] = useState<string>("Memulai...");
  const [progressMessage, setProgressMessage] = useState<string>("");



  function updateFormField<K extends keyof PaperForm>(field: K, value: PaperForm[K]) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  function updateContentField(field: SectionKey, value: string) {
    setForm((prev) => ({
      ...prev,
      content: {
        ...prev.content,
        [field]: value
      }
    }));
  }

  async function handleValidate() {
    if (!form.judul.trim()) return;
    setStep("validating");
    setError("");
    setValidationResult(null);

    try {
      // Gunakan endpoint validasi baru yang langsung ke FastAPI
      const response = await fetch("/api/v1/validate/academic-topic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ judul: form.judul })
      });
      const data = await response.json();
      if (data.is_academic) {
        setValidationResult({ is_academic: true, reason: data.reason || data.message, field: data.reason });
        setStep("validated");
      } else if (response.status === 503) {
        // AI tidak tersedia — tetap izinkan lanjut dengan peringatan
        setValidationResult({ is_academic: true, reason: "Layanan validasi tidak tersedia, namun kamu tetap bisa generate.", field: "Perhatian" });
        setStep("validated");
      } else {
        setError(data.message || "Topik tidak valid.");
        setStep("idle");
      }
    } catch (err) {
      setError("Gagal memvalidasi judul.");
      setStep("idle");
    }
  }

  async function handleGenerate(event?: FormEvent) {
    if (event) event.preventDefault();
    setStep("generating");
    setError("");
    setResult(null);
    setProgress(0);
    setProgressStage("Memulai pipeline generation...");
    setProgressMessage("");

    try {
      // 1. Buat job baru via endpoint baru
      const createRes = await fetch("/api/v1/generations/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          judul: form.judul,
          mata_kuliah: form.mata_kuliah,
          dosen: form.dosen,
          authors: [
            { nama: form.penulis_1, nim: form.nim_penulis_1 },
            ...(form.penulis_2 ? [{ nama: form.penulis_2, nim: form.nim_penulis_2 }] : []),
            ...(form.penulis_3 ? [{ nama: form.penulis_3, nim: form.nim_penulis_3 }] : []),
          ],
          jurusan: form.jurusan,
          fakultas: form.fakultas,
          kampus: form.kampus,
          tahun: form.tahun,
          tempat_pembuatan: form.tempat_pembuatan,
          tanggal_pembuatan: form.tanggal_pembuatan,
          template_name: form.template_name,
          generation_mode: form.generation_mode,
          reference_mode: form.reference_mode,
          citation_range: form.citation_range,
          content: form.content,
        })
      });

      if (!createRes.ok) {
        const err = await createRes.json();
        setError(err.detail?.message || err.error || "Gagal membuat job generation.");
        setStep("validated");
        return;
      }

      const { job_id } = await createRes.json();

      // 2. Subscribe ke SSE stream untuk real-time progress
      const eventSource = new EventSource(`/api/v1/generations/${job_id}/events`);

      await new Promise<void>((resolve) => {
        eventSource.onmessage = (e) => {
          try {
            const event = JSON.parse(e.data);
            setProgress(event.progress ?? 0);
            setProgressStage(event.stage ?? "processing");
            setProgressMessage(event.message ?? "");

            if (event.status === "completed") {
              eventSource.close();
              // 3. Ambil result
              fetch(`/api/v1/generations/${job_id}`)
                .then(r => r.json())
                .then(statusData => {
                  if (statusData.result) {
                    setResult({
                      ok: true,
                      message: "Makalah berhasil dibuat.",
                      filename: statusData.result.filename,
                      downloadUrl: statusData.result.download_url,
                      pdfUrl: statusData.result.pdf_url || null,
                      outputPath: "",
                      tokenUsage: { total_calls: 0, total_input_tokens: 0, total_output_tokens: 0, total_tokens: 0 },
                      warnings: statusData.result.warnings || [],
                      content: {},
                    });
                    setStep("success");
                  }
                  resolve();
                });
            } else if (event.status === "failed") {
              eventSource.close();
              setError(event.extra?.error_code || "Generation gagal.");
              setStep("validated");
              resolve();
            } else if (event.status === "cancelled") {
              eventSource.close();
              setError("Job dibatalkan.");
              setStep("validated");
              resolve();
            }
          } catch {}
        };

        eventSource.onerror = () => {
          eventSource.close();
          setError("Koneksi ke server terputus.");
          setStep("validated");
          resolve();
        };
      });
    } catch (err) {
      setError("Terjadi kesalahan koneksi ke server.");
      setStep("validated");
    }
  }

  return (
    <>
      {/* Real-time Progress Modal Overlay */}
      {step === "generating" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-in fade-in">
          <div className="flex max-w-sm flex-col items-center rounded-2xl bg-white p-8 text-center shadow-2xl w-full mx-4">
            {/* Circular progress */}
            <div className="relative mb-5 h-20 w-20">
              <svg className="h-20 w-20 -rotate-90" viewBox="0 0 80 80">
                <circle cx="40" cy="40" r="34" fill="none" stroke="#e5e7eb" strokeWidth="8" />
                <circle
                  cx="40" cy="40" r="34"
                  fill="none"
                  stroke="#2563eb"
                  strokeWidth="8"
                  strokeLinecap="round"
                  strokeDasharray={`${2 * Math.PI * 34}`}
                  strokeDashoffset={`${2 * Math.PI * 34 * (1 - progress / 100)}`}
                  style={{ transition: "stroke-dashoffset 0.5s ease" }}
                />
              </svg>
              <span className="absolute inset-0 flex items-center justify-center text-lg font-bold text-blue-600">
                {progress}%
              </span>
            </div>

            <h3 className="mb-1 text-xl font-bold text-gray-900">Menyusun Makalah</h3>
            <p className="mb-1 text-sm font-semibold text-blue-600 capitalize">
              {progressStage.replace(/_/g, " ")}
            </p>
            <p className="text-xs text-gray-500 max-w-xs">
              {progressMessage || "AI sedang menyusun draf, mencari referensi, dan memformat dokumen..."}
            </p>

            {/* Linear progress bar */}
            <div className="mt-5 w-full rounded-full bg-gray-100 h-2 overflow-hidden">
              <div
                className="h-2 rounded-full bg-blue-600 transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>

            <p className="mt-3 text-[11px] text-gray-400">
              Proses membutuhkan 2–5 menit. Jangan tutup halaman ini.
            </p>
          </div>
        </div>
      )}

      <main className="mx-auto max-w-7xl px-4 py-8 md:px-6">
      <header className="mb-6 panel p-6">
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <span className="chip ok">Next.js 16</span>
          <span className="chip ok">Tailwind</span>
          <span className="chip warn">Python DOCX Engine</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight">NeoMakalah Web</h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Versi web untuk generator makalah UIN. Alur tetap sama: isi data, pilih mode, generate, lalu download DOCX.
        </p>
      </header>

      {error ? <div className="alert error mb-4">{error}</div> : null}

      <form 
        onSubmit={(e) => { 
          e.preventDefault(); 
          if(step === 'idle') handleValidate(); 
        }} 
        className="grid gap-6 lg:grid-cols-3"
      >
        <section className="panel p-5 lg:col-span-2">
          <h2 className="mb-4 text-lg font-bold">Informasi Dasar</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="label" htmlFor="mata_kuliah">
                Mata Kuliah
              </label>
              <input
                id="mata_kuliah"
                className="field"
                value={form.mata_kuliah}
                onChange={(e) => updateFormField("mata_kuliah", e.target.value)}
                required
              />
            </div>
            <div>
              <label className="label" htmlFor="judul">
                Judul Makalah
              </label>
              <input
                id="judul"
                className="field"
                value={form.judul}
                onChange={(e) => updateFormField("judul", e.target.value)}
                required
              />
            </div>
            <div>
              <label className="label" htmlFor="dosen">
                Dosen
              </label>
              <input
                id="dosen"
                className="field"
                value={form.dosen}
                onChange={(e) => updateFormField("dosen", e.target.value)}
                required
              />
            </div>
            <div>
              <label className="label" htmlFor="template_name">
                Template
              </label>
              <select
                id="template_name"
                className="select"
                value={form.template_name}
                onChange={(e) => updateFormField("template_name", e.target.value)}
              >
                <option value="Uin Alauddin">UIN Alauddin</option>
              </select>
            </div>
          </div>
        </section>

        <section className="panel p-5">
          <h2 className="mb-4 text-lg font-bold">Mode Generate</h2>
          <label className="label" htmlFor="generation_mode">
            Pilih Mode
          </label>
          <select
            id="generation_mode"
            className="select mb-4"
            value={form.generation_mode}
            onChange={(e) => updateFormField("generation_mode", e.target.value as GenerationMode)}
          >
            <option value="manual">Manual</option>
            <option value="ai_full">AI</option>
          </select>

          <label className="label mt-3" htmlFor="reference_mode">
            Kualitas Referensi
          </label>
          <select
            id="reference_mode"
            className="select mb-4"
            value={form.reference_mode}
            onChange={(e) => updateFormField("reference_mode", e.target.value as ReferenceMode)}
          >
            <option value="fast">Normal</option>
            <option value="smart">Disarankan ✦</option>
            <option value="strict">Terbaik ★</option>
          </select>
          <p className="text-xs text-[var(--muted)] -mt-2 mb-2">Normal: cepat tanpa validasi. Disarankan: tervalidasi. Terbaik: wajib terverifikasi.</p>

          <label className="label mt-3" htmlFor="citation_range">
            Jumlah Kutipan
          </label>
          <select
            id="citation_range"
            className="select mb-4"
            value={form.citation_range}
            onChange={(e) => updateFormField("citation_range", e.target.value as CitationRange)}
          >
            <option value="5-10">5 – 10 kutipan</option>
            <option value="10-15">10 – 15 kutipan</option>
            <option value="20-25">20 – 25 kutipan</option>
          </select>
          <p className="text-xs text-[var(--muted)] -mt-2 mb-2">Jumlah referensi yang akan dicari dan dimasukkan ke daftar pustaka.</p>

          {step === "idle" && (
            <button 
              type="button" 
              onClick={handleValidate} 
              className="btn-primary mt-5 w-full bg-blue-600 hover:bg-blue-700"
              disabled={!form.judul}
            >
              Cek Validasi Judul
            </button>
          )}

          {step === "validating" && (
            <button disabled className="btn-primary mt-5 w-full opacity-70">
              Menganalisis...
            </button>
          )}

          {step === "validated" && validationResult && (
            <div className="mt-5 space-y-4">
              <div className="rounded-xl border border-green-200 bg-green-50 p-4">
                <p className="text-xs font-bold uppercase tracking-wider text-green-600">✅ Analisis AI: {validationResult.field}</p>
                <p className="mt-1 text-sm text-green-800">{validationResult.reason}</p>
              </div>
              
              <div className="flex gap-2">
                <button 
                  type="button" 
                  onClick={() => setStep("idle")}
                  className="btn-secondary flex-1"
                >
                  Ubah
                </button>
                <button 
                  type="button" 
                  onClick={() => handleGenerate()}
                  className="btn-primary flex-[2] bg-green-600 hover:bg-green-700"
                >
                  Gas, Kerjakan!
                </button>
              </div>
            </div>
          )}

          {step === "generating" && (
            <button disabled className="btn-primary mt-5 w-full bg-green-600 opacity-70">
              Sedang Menulis...
            </button>
          )}

          {step === "success" && (
             <button 
                type="button" 
                onClick={() => {
                  setStep("idle");
                  setResult(null);
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
                className="btn-secondary mt-5 w-full"
              >
                Buat Makalah Lain
              </button>
          )}

          {error && <p className="mt-3 text-sm font-medium text-red-500">❌ {error}</p>}
        </section>

        <section className="panel p-5 lg:col-span-3">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-bold">Penulis</h2>
            {authorCount < 3 && (
              <button
                type="button"
                onClick={() => setAuthorCount(prev => prev + 1)}
                className="rounded-md bg-blue-100 px-3 py-1 text-sm font-medium text-blue-700 hover:bg-blue-200"
              >
                + Tambah Penulis
              </button>
            )}
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-2 mb-6">
            {Array.from({ length: authorCount }).map((_, idx) => {
              const num = idx + 1;
              const pKey = `penulis_${num}` as keyof PaperForm;
              const nKey = `nim_penulis_${num}` as keyof PaperForm;

              return (
                <div key={num} className="rounded-lg border border-gray-200 p-4 relative">
                  {num > 1 && (
                    <button
                      type="button"
                      onClick={() => {
                        setAuthorCount(prev => prev - 1);
                        updateFormField(`penulis_${authorCount}` as keyof PaperForm, "");
                        updateFormField(`nim_penulis_${authorCount}` as keyof PaperForm, "");
                      }}
                      className="absolute top-4 right-4 text-red-500 hover:text-red-700"
                      title="Hapus Penulis"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"></path><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                    </button>
                  )}
                  <h3 className="mb-3 text-sm font-bold text-gray-700">Penulis {num}</h3>
                  <div className="grid gap-3">
                    <div>
                      <label className="label text-xs">Nama Lengkap</label>
                      <input className="field" value={form[pKey] as string} onChange={(e) => updateFormField(pKey, e.target.value)} required />
                    </div>
                    <div>
                      <label className="label text-xs">NIM</label>
                      <input className="field" value={form[nKey] as string} onChange={(e) => updateFormField(nKey, e.target.value)} required />
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          <h2 className="mb-4 text-lg font-bold">Institusi</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="label">Jurusan</label>
              <input className="field" value={form.jurusan} onChange={(e) => updateFormField("jurusan", e.target.value)} required />
            </div>
            <div>
              <label className="label">Fakultas</label>
              <input className="field" value={form.fakultas} onChange={(e) => updateFormField("fakultas", e.target.value)} required />
            </div>
            <div>
              <label className="label">Kampus</label>
              <input className="field" value={form.kampus} onChange={(e) => updateFormField("kampus", e.target.value)} required />
            </div>
            <div>
              <label className="label">Tahun</label>
              <input className="field" value={form.tahun} onChange={(e) => updateFormField("tahun", e.target.value)} />
            </div>
            <div>
              <label className="label">Tempat Pembuatan</label>
              <input
                className="field"
                value={form.tempat_pembuatan}
                onChange={(e) => updateFormField("tempat_pembuatan", e.target.value)}
              />
            </div>
            <div>
              <label className="label">Tanggal Pembuatan</label>
              <input
                className="field"
                value={form.tanggal_pembuatan}
                onChange={(e) => updateFormField("tanggal_pembuatan", e.target.value)}
              />
            </div>
          </div>
        </section>

        {form.generation_mode === "manual" && (
          <section className="panel p-5 lg:col-span-3 animate-in fade-in zoom-in-95">
            <div className="mb-4">
              <h2 className="text-lg font-bold">Konten Makalah (Draft)</h2>
              <p className="text-sm text-[var(--muted)]">Masukkan poin-poin atau draf kasar Anda di sini. AI akan menyempurnakannya agar sesuai standar penulisan akademik. Contoh: Jika Anda hanya memasukkan 1 atau 2 rumusan masalah, sistem akan otomatis menggenapkannya untuk memenuhi isi template.</p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              {SECTION_LABELS.map((entry) => (
                <div key={entry.key}>
                  <label className="label" htmlFor={`field-${entry.key}`}>
                    {entry.label}
                  </label>
                  <textarea
                    id={`field-${entry.key}`}
                    className="textarea"
                    value={form.content[entry.key]}
                    onChange={(e) => updateContentField(entry.key, e.target.value)}
                    placeholder={`Isi draf kasar ${entry.label.toLowerCase()}...`}
                    rows={4}
                  />
                </div>
              ))}
            </div>
          </section>
        )}
      </form>

      {result ? (
        <section className="panel mt-6 p-5 animate-in slide-in-from-bottom-4 fade-in">
          <div className="mb-6 rounded-xl border border-green-200 bg-green-50 p-4">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 rounded-full bg-green-100 p-1 text-green-600">
                <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <h3 className="text-lg font-bold text-green-800">Generate Selesai!</h3>
                <p className="mt-1 text-sm text-green-700">
                  Dokumen berhasil dibuat. Silakan review hasil di bawah ini. Jika sudah sesuai, Anda dapat langsung mengunduhnya.
                </p>
              </div>
            </div>
          </div>

          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-bold">Pratinjau Dokumen</h2>
              <p className="text-sm text-[var(--muted)]">{result.message}</p>
            </div>
            <a className="btn-primary inline-flex items-center" href={result.downloadUrl}>
              <svg className="mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download DOCX
            </a>
          </div>

          {result.warnings.length > 0 ? (
            <div className="alert info mb-4">
              {result.warnings.map((warning) => (
                <div key={warning}>- {warning}</div>
              ))}
            </div>
          ) : null}

          <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-xl border border-[var(--line)] bg-white p-3">
              <p className="text-xs text-[var(--muted)]">Total Calls</p>
              <p className="text-xl font-bold">{result.tokenUsage.total_calls}</p>
            </div>
            <div className="rounded-xl border border-[var(--line)] bg-white p-3">
              <p className="text-xs text-[var(--muted)]">Input Tokens</p>
              <p className="text-xl font-bold">{result.tokenUsage.total_input_tokens}</p>
            </div>
            <div className="rounded-xl border border-[var(--line)] bg-white p-3">
              <p className="text-xs text-[var(--muted)]">Output Tokens</p>
              <p className="text-xl font-bold">{result.tokenUsage.total_output_tokens}</p>
            </div>
            <div className="rounded-xl border border-[var(--line)] bg-white p-3">
              <p className="text-xs text-[var(--muted)]">Total Tokens</p>
              <p className="text-xl font-bold">{result.tokenUsage.total_tokens}</p>
            </div>
          </div>

          {result.pdfUrl ? (
            <div className="mb-4 flex flex-col gap-4">
              <div className="flex md:hidden flex-col items-center justify-center p-6 bg-[var(--background)] rounded-xl border border-[var(--line)]">
                <p className="text-sm text-[var(--muted)] mb-3 text-center">Browser HP Anda mungkin tidak mendukung fitur pratinjau PDF secara langsung.</p>
                <a href={result.pdfUrl} target="_blank" className="px-6 py-2 bg-[var(--foreground)] text-[var(--background)] rounded-full text-sm font-semibold">
                  Buka PDF di Layar Penuh
                </a>
              </div>
              <div className="hidden md:block">
                <object 
                  data={result.pdfUrl} 
                  type="application/pdf"
                  className="w-full h-[800px] border border-[var(--line)] rounded-xl bg-white"
                  title="PDF Preview"
                >
                  <p>Memuat Preview PDF...</p>
                </object>
              </div>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {Object.entries(result.content).map(([section, text]) => (
                <div key={section}>
                  <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
                    {section.replaceAll("_", " ")}
                  </h3>
                  <div className="preview">{text || "-"}</div>
                </div>
              ))}
            </div>
          )}
        </section>
      ) : null}
    </main>
    </>
  );
}
