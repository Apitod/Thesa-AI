# THESA AI × NEOMAKALAH --- Integration Context & Migration Specification

> **Dokumen konteks untuk AI coding agent**
>
> Dokumen ini menjelaskan konteks dua project, keputusan arsitektur,
> target integrasi, serta batasan implementasi. Gunakan dokumen ini
> sebagai **source of truth** sebelum melakukan perubahan kode.

------------------------------------------------------------------------

# 1. Ringkasan Project

## 1.1 Thesa AI

Thesa AI adalah platform AI untuk mahasiswa dan peneliti. Fokus
produknya adalah membantu proses akademik seperti:

-   pembuatan makalah/karya tulis ilmiah;
-   analisis literatur;
-   pembuatan outline;
-   pendampingan/Socratic coaching;
-   simulasi sidang;
-   supervisor/examiner experience;
-   sistem tier/kuota;
-   export dokumen;
-   pengalaman UI/UX yang interaktif dan berorientasi pada proses.

Repository Thesa saat ini memiliki frontend berbasis HTML/CSS/JavaScript
dan backend utama berbasis Go.

Struktur penting:

``` text
thesa-ai/
├── web/
│   ├── app.html
│   ├── app.js
│   ├── style.css
│   ├── auth.html
│   ├── admin.html
│   ├── landing.html
│   └── export_service.js
│
├── cmd/
│   └── server/
│       └── main.go
│
├── internal/
│   ├── agent/
│   ├── handlers/
│   ├── db/
│   ├── payment/
│   └── security/
│
├── monitoring/
├── scripts/
├── docker-compose.yml
├── Dockerfile
├── go.mod
└── go.sum
```

Backend Go menangani banyak hal, antara lain:

-   authentication;
-   database;
-   AI endpoint;
-   literature;
-   template;
-   outline;
-   Socratic supervisor;
-   examiner simulation;
-   cascade/dependency;
-   payment/kuota;
-   dan fungsi backend lainnya.

**Namun backend Go tersebut TIDAK akan menjadi backend final.**

------------------------------------------------------------------------

## 1.2 NeoMakalah

NeoMakalah adalah project generator makalah yang memiliki backend/engine
Python yang sudah cukup matang untuk proses pembuatan dokumen akademik.

Komponen penting:

``` text
neomakalaha/
├── app/
│   ├── page.tsx
│   └── api/
│       ├── generate/
│       │   └── route.ts
│       └── download/
│
├── src/
│   ├── ai_engine.py
│   ├── reference_engine.py
│   ├── document_builder.py
│   ├── template_engine.py
│   ├── toc_engine.py
│   ├── fewshot_cache.py
│   ├── token_logger.py
│   ├── input_handler.py
│   ├── main.py
│   ├── docm_converter.py
│   └── zotero_engine.py
│
├── sinta_finder/
├── templates/
├── data/
├── python_web_bridge.py
├── requirements.txt
└── package.json
```

Arsitektur NeoMakalah saat ini menggunakan Next.js sebagai web/API layer
dan Python sebagai engine pembuatan makalah.

Alur utamanya:

``` text
Next.js
   ↓
POST /api/generate
   ↓
python_web_bridge.py
   ↓
Python AI / Reference / Document Pipeline
   ↓
DOCX / PDF
```

Engine Python merupakan bagian yang ingin dipertahankan karena sudah
menjadi komponen inti yang solid untuk pembuatan makalah.

------------------------------------------------------------------------

# 2. Keputusan Arsitektur Final

## 2.1 Prinsip utama

Project **tidak akan melakukan konversi Go → JavaScript**.

Backend Go Thesa akan **dihentikan dan secara bertahap dihapus**.

Backend/engine Python NeoMakalah akan menjadi dasar backend untuk fitur
pembuatan makalah.

Frontend dan UX Thesa akan menjadi dasar pengalaman pengguna final.

Konsep sederhananya:

``` text
THESA
= Product / UI / UX / User Flow

NEOMAKALAH
= Academic Generation Engine / Backend Capability
```

Target akhir:

``` text
                 THESA AI
                    │
                    │
             Frontend / UX
                    │
                    │ API
                    ↓
          ┌───────────────────┐
          │ Python Backend    │
          │ NeoMakalah Engine │
          └─────────┬─────────┘
                    │
          ┌─────────┼──────────┐
          ↓         ↓          ↓
       AI Engine  Reference  Document
                  Engine      Builder
          │         │          │
          └─────────┼──────────┘
                    ↓
                DOCX / PDF
```

------------------------------------------------------------------------

# 3. Tujuan Integrasi

Tujuan utama adalah menghasilkan **Thesa AI versi baru** dengan:

1.  UI/UX Thesa dipertahankan semirip mungkin dengan versi sekarang.
2.  Flow interaksi Thesa tetap dipertahankan.
3.  Backend Go tidak lagi menjadi dependency.
4.  Engine pembuatan makalah NeoMakalah dipertahankan.
5.  Python backend dikembangkan agar memenuhi kebutuhan frontend Thesa.
6.  Progress generation harus berasal dari proses backend yang nyata,
    bukan progress palsu/estimasi.
7.  Fitur Thesa yang belum tersedia di NeoMakalah akan dikembangkan
    kemudian pada backend Python.
8.  API baru harus dirancang dengan kontrak yang jelas antara frontend
    dan backend.
9.  Arsitektur final harus mudah dikembangkan untuk fitur akademik Thesa
    berikutnya.

------------------------------------------------------------------------

# 4. Filosofi Integrasi

Jangan memaksa frontend Thesa mengikuti keterbatasan API NeoMakalah saat
ini.

Sebaliknya:

> **Backend Python NeoMakalah harus dikembangkan untuk memenuhi
> kebutuhan product dan UX Thesa.**

Engine yang sudah solid tidak perlu ditulis ulang tanpa alasan.

Misalnya:

``` text
NeoMakalah:
AI generation
Reference search
Citation
Document builder
TOC
DOCX/PDF
```

tetap dipertahankan.

Kemudian ditambahkan layer backend baru untuk kebutuhan Thesa:

``` text
Generation Job
Progress
Status
Events
Cancellation
History
User context
Error handling
Feature-specific API
```

------------------------------------------------------------------------

# 5. UI/UX Thesa Adalah Prioritas

## 5.1 Jangan melakukan redesign besar

UI/UX Thesa dianggap sebagai bagian yang sudah matang.

Pertahankan semirip mungkin:

-   layout;
-   sidebar;
-   navigation;
-   typography;
-   visual hierarchy;
-   cards;
-   modal;
-   loading experience;
-   Socratic interaction;
-   progress bar;
-   status indicator;
-   micro-interactions;
-   terminology;
-   user flow;
-   responsive behavior;
-   visual identity.

Perubahan UI hanya boleh dilakukan apabila benar-benar diperlukan untuk
menyesuaikan API/backend baru.

------------------------------------------------------------------------

# 6. Real Backend Progress

Ini merupakan requirement penting.

Saat ini frontend Thesa memiliki progress UI seperti:

``` text
0%
35%
55%
65%
75%
85%
92%
100%
```

dan beberapa progress tersebut masih dipicu oleh frontend.

Pada arsitektur baru, progress harus berasal dari **event nyata dari
backend**.

Jangan membuat:

``` text
Frontend:
setTimeout(() => progress = 30)
setTimeout(() => progress = 60)
setTimeout(() => progress = 100)
```

karena itu bukan real progress.

Yang diinginkan:

``` text
Backend
   ↓
actual stage starts
   ↓
emit event
   ↓
frontend updates progress
```

Contoh event:

``` json
{
  "job_id": "abc123",
  "stage": "reference_search",
  "progress": 32,
  "message": "Mencari referensi akademik..."
}
```

Kemudian:

``` json
{
  "job_id": "abc123",
  "stage": "chapter_generation",
  "progress": 55,
  "chapter": "BAB I",
  "message": "Menyusun BAB I..."
}
```

Kemudian:

``` json
{
  "job_id": "abc123",
  "stage": "document_building",
  "progress": 92,
  "message": "Menyusun dokumen akhir..."
}
```

Dan:

``` json
{
  "job_id": "abc123",
  "stage": "completed",
  "progress": 100,
  "message": "Makalah berhasil dibuat."
}
```

------------------------------------------------------------------------

# 7. Generation Job Architecture

Generation makalah sebaiknya tidak dianggap sebagai request HTTP
sederhana yang hanya:

``` text
POST
 ↓
wait
 ↓
return document
```

Gunakan konsep **Generation Job**.

Contoh:

``` text
POST /api/v1/generations
        ↓
      job_id
        ↓
backend menjalankan pipeline
        ↓
frontend subscribe/poll event
        ↓
job selesai
        ↓
download result
```

Target API konseptual:

``` text
POST /api/v1/generations
GET  /api/v1/generations/:id
GET  /api/v1/generations/:id/events
POST /api/v1/generations/:id/cancel
GET  /api/v1/generations/:id/result
```

Implementasi transport event dapat menggunakan mekanisme yang sesuai
dengan arsitektur final, misalnya SSE atau mekanisme event lain.

Prioritasnya adalah:

-   event real-time/near-real-time;
-   progress berasal dari backend;
-   frontend dapat mengetahui stage aktif;
-   error dapat dikirim sebagai event;
-   job dapat dilacak menggunakan `job_id`;
-   hasil dapat diambil setelah selesai.

------------------------------------------------------------------------

# 8. Generation Pipeline yang Diinginkan

Backend Python harus mempertahankan kemampuan NeoMakalah dan mengekspos
prosesnya sebagai pipeline.

Pipeline konseptual:

``` text
1. Receive input
        ↓
2. Validate request
        ↓
3. Validate academic topic
        ↓
4. Prepare context
        ↓
5. Search references
        ↓
6. Filter/validate references
        ↓
7. Generate academic structure
        ↓
8. Generate sections
        ↓
9. Generate citations
        ↓
10. Validate generated content
        ↓
11. Build document
        ↓
12. Generate TOC
        ↓
13. Convert/export
        ↓
14. Store result
        ↓
15. Complete
```

Setiap stage harus dapat menghasilkan event progress.

Contoh mapping:

``` text
VALIDATING
    0–10%

REFERENCE_SEARCH
    10–30%

STRUCTURE_GENERATION
    30–40%

CONTENT_GENERATION
    40–75%

CITATION_VALIDATION
    75–85%

DOCUMENT_BUILDING
    85–95%

EXPORT
    95–99%

COMPLETED
    100%
```

**Catatan:** angka di atas adalah contoh desain, bukan angka wajib.
Progress final harus mencerminkan pekerjaan aktual semaksimal mungkin.

------------------------------------------------------------------------

# 9. Mapping Frontend Thesa → Backend Python

Frontend Thesa sudah memiliki banyak state dan flow.

Contoh:

``` text
User input
   ↓
Academic validation
   ↓
Socratic interaction
   ↓
Research context
   ↓
Makalah generation
   ↓
Document completion
   ↓
Export
```

Backend Python harus menyediakan API yang mendukung flow tersebut.

Jangan menghapus UX hanya karena backend lama Go menyediakan endpoint
tertentu.

Jika suatu fitur Thesa membutuhkan endpoint baru, tambahkan endpoint
pada Python backend.

------------------------------------------------------------------------

# 10. Existing NeoMakalah API

NeoMakalah saat ini memiliki endpoint utama:

``` text
POST /api/generate
```

Endpoint tersebut menerima data makalah seperti:

``` json
{
  "mata_kuliah": "...",
  "judul": "...",
  "dosen": "...",
  "jurusan": "...",
  "fakultas": "...",
  "kampus": "...",
  "penulis_1": "...",
  "nim_penulis_1": "...",
  "generation_mode": "ai_full",
  "reference_mode": "smart",
  "citation_range": "10-15"
}
```

Backend kemudian menjalankan Python bridge dan menghasilkan dokumen.

Endpoint download juga tersedia secara konseptual:

``` text
GET /api/download/[filename]
```

API ini boleh direfactor agar menjadi bagian dari API generasi Thesa
yang lebih terstruktur.

------------------------------------------------------------------------

# 11. Fitur NeoMakalah yang Harus Dipertahankan

Jangan menghilangkan kemampuan yang sudah ada tanpa alasan.

Komponen yang perlu dipertahankan dan diintegrasikan:

``` text
src/ai_engine.py
src/reference_engine.py
src/document_builder.py
src/template_engine.py
src/toc_engine.py
src/fewshot_cache.py
src/token_logger.py
src/input_handler.py
src/zotero_engine.py
src/docm_converter.py
sinta_finder/
templates/
data/
```

Fungsi detail setiap komponen harus dianalisis terlebih dahulu sebelum
refactor.

------------------------------------------------------------------------

# 12. Fitur Thesa yang Belum Ada di NeoMakalah

Thesa memiliki fitur yang lebih luas daripada generator makalah
NeoMakalah.

Contohnya:

``` text
Authentication
User profile
Tier system
Quota
Payment
Socratic coaching
Supervisor
Examiner simulation
Research workflow
Dashboard
History
Potential academic modules
```

Fitur-fitur tersebut **tidak perlu dipaksakan selesai dalam tahap
migrasi pertama**.

Prioritas tahap pertama:

> **Makalah generation end-to-end.**

Setelah generator stabil:

``` text
Phase 1
Makalah generation
        ↓
Phase 2
Real progress + job management
        ↓
Phase 3
History / workspace
        ↓
Phase 4
Socratic / supervisor features
        ↓
Phase 5
Authentication / user system
        ↓
Phase 6
Payment / quota
        ↓
Phase 7
Additional academic modules
```

Urutan dapat berubah setelah audit teknis.

------------------------------------------------------------------------

# 13. Backend Go Thesa

Backend Go dianggap sebagai **legacy backend yang akan dipensiunkan**.

Contoh komponen:

``` text
cmd/server/
internal/
go.mod
go.sum
```

Jangan langsung menghapusnya.

Prosedur:

``` text
1. Audit dependency frontend terhadap Go.
2. Identifikasi seluruh API yang masih dipanggil.
3. Buat pengganti API di Python.
4. Redirect frontend ke API baru.
5. Test fitur.
6. Pastikan tidak ada dependency aktif terhadap Go.
7. Baru hapus backend Go.
```

Backend Go tidak boleh dihapus sebelum frontend berhasil berjalan tanpa
dependency terhadapnya.

------------------------------------------------------------------------

# 14. API Contract

Frontend dan backend harus memiliki kontrak yang eksplisit.

Contoh:

``` text
POST /api/v1/generations
```

Request:

``` json
{
  "title": "...",
  "course": "...",
  "lecturer": "...",
  "authors": [],
  "institution": "...",
  "template": "...",
  "generation_mode": "ai_full",
  "reference_mode": "smart",
  "citation_range": "5-10"
}
```

Response:

``` json
{
  "job_id": "abc123",
  "status": "queued"
}
```

Kemudian frontend menerima event:

``` json
{
  "job_id": "abc123",
  "status": "running",
  "stage": "reference_search",
  "progress": 32,
  "message": "Mencari referensi..."
}
```

Ketika selesai:

``` json
{
  "job_id": "abc123",
  "status": "completed",
  "progress": 100,
  "result": {
    "filename": "makalah.docx",
    "download_url": "/api/v1/generations/abc123/result"
  }
}
```

Gunakan struktur yang konsisten untuk seluruh API.

------------------------------------------------------------------------

# 15. Error Handling

Backend harus mengirim error yang dapat dipahami frontend.

Contoh:

``` json
{
  "job_id": "abc123",
  "status": "failed",
  "stage": "reference_search",
  "progress": 30,
  "error": {
    "code": "REFERENCE_SEARCH_FAILED",
    "message": "Gagal mendapatkan referensi akademik."
  }
}
```

Frontend kemudian dapat menampilkan error dengan UX Thesa tanpa
mengetahui detail internal Python.

Jangan mengirim raw traceback Python ke user.

Traceback tetap dicatat di server/logging.

------------------------------------------------------------------------

# 16. Separation of Concerns

Gunakan pembagian:

``` text
Frontend
   ↓
API Layer
   ↓
Job / Orchestration Layer
   ↓
Academic Generation Services
   ↓
Document Services
```

Frontend tidak boleh mengetahui detail:

``` text
ai_engine.py
reference_engine.py
document_builder.py
```

Frontend cukup mengetahui:

``` text
job_id
status
stage
progress
message
result
error
```

Dengan demikian engine Python dapat diubah tanpa harus mengubah UX.

------------------------------------------------------------------------

# 17. Prinsip Implementasi untuk AI Coding Agent

Sebelum menulis kode:

1.  Baca seluruh repository Thesa.
2.  Baca seluruh repository NeoMakalah yang relevan.
3.  Jangan langsung menghapus backend Go.
4.  Buat dependency map.
5.  Buat API migration map.
6.  Identifikasi semua frontend call ke backend Go.
7.  Identifikasi pipeline generation NeoMakalah.
8.  Tentukan bagian yang dapat dipertahankan tanpa perubahan.
9.  Tentukan bagian yang perlu adapter/refactor.
10. Buat implementation plan.

Setelah plan disetujui, implementasikan secara bertahap.

------------------------------------------------------------------------

# 18. Aturan Penting

## Jangan

``` text
❌ Convert Go menjadi JavaScript.
❌ Rewrite seluruh Python engine tanpa alasan.
❌ Redesign UI Thesa.
❌ Menggunakan fake progress.
❌ Menghapus Go sebelum dependency-nya diputus.
❌ Membuat API baru tanpa dokumentasi contract.
❌ Menaruh business logic besar di frontend.
❌ Mengubah output document engine yang sudah stabil tanpa kebutuhan.
```

## Lakukan

``` text
✅ Pertahankan UI/UX Thesa.
✅ Pertahankan core engine NeoMakalah.
✅ Bangun API Python yang mengikuti kebutuhan Thesa.
✅ Gunakan real backend progress.
✅ Gunakan generation job.
✅ Pisahkan API layer dari generation engine.
✅ Migrasikan secara incremental.
✅ Test setiap tahap.
✅ Pertahankan backward compatibility jika diperlukan selama transisi.
```

------------------------------------------------------------------------

# 19. Definition of Done --- Tahap Pertama

Migrasi tahap pertama dianggap berhasil apabila:

-   [ ] Frontend Thesa dapat berjalan tanpa backend Go.
-   [ ] User dapat mengisi form makalah melalui UI Thesa.
-   [ ] Validasi akademik dapat dilakukan melalui Python backend.
-   [ ] Generation job dapat dibuat.
-   [ ] Backend menjalankan engine NeoMakalah.
-   [ ] Reference engine berjalan.
-   [ ] AI generation berjalan.
-   [ ] Document builder berjalan.
-   [ ] DOCX berhasil dibuat.
-   [ ] PDF/export jika tersedia tetap berfungsi.
-   [ ] Frontend menerima progress nyata dari backend.
-   [ ] Progress menampilkan stage yang sedang berlangsung.
-   [ ] Error backend dapat ditampilkan dengan UX Thesa.
-   [ ] User dapat mengunduh hasil.
-   [ ] Tidak ada request aktif yang masih bergantung pada Go.
-   [ ] Core UI/UX Thesa tetap semirip mungkin dengan versi awal.

------------------------------------------------------------------------

# 20. Target Arsitektur Akhir

Arsitektur final yang dituju:

``` text
                         USER
                           │
                           ↓
                    ┌─────────────┐
                    │  THESA UI   │
                    │             │
                    │ Dashboard   │
                    │ Workspace   │
                    │ Makalah     │
                    │ Socratic    │
                    │ Progress    │
                    └──────┬──────┘
                           │
                           │ HTTP / SSE
                           ↓
                 ┌─────────────────────┐
                 │   PYTHON API        │
                 │                     │
                 │ Auth                │
                 │ Generation Jobs     │
                 │ Progress Events     │
                 │ History             │
                 │ Academic Features   │
                 └──────────┬──────────┘
                            │
                  ┌─────────┴─────────┐
                  ↓                   ↓
          ┌───────────────┐    ┌───────────────┐
          │ NeoMakalah    │    │ Future Thesa  │
          │ Core Engine   │    │ Services      │
          └───────┬───────┘    └───────────────┘
                  │
        ┌─────────┼──────────┐
        ↓         ↓          ↓
       AI      References   Document
      Engine     Engine     Builder
                             │
                             ↓
                         DOCX / PDF
```

------------------------------------------------------------------------

# 21. Ringkasan untuk AI Agent

Jika seluruh dokumen ini harus diringkas menjadi satu instruksi:

> **THESA AI adalah product/UI/UX layer yang ingin dipertahankan hampir
> 100%. NEOMAKALAH adalah academic document-generation engine yang ingin
> dipertahankan karena kemampuan Python-nya sudah solid. Backend Go
> Thesa akan dipensiunkan, bukan dikonversi ke JavaScript. Tugas utama
> adalah mengintegrasikan frontend Thesa dengan backend Python
> NeoMakalah, lalu mengembangkan backend Python agar mampu memenuhi
> seluruh kebutuhan UI/UX Thesa. Generation harus menggunakan real
> backend progress berbasis job dan event, bukan fake frontend timers.
> Jangan melakukan redesign besar, jangan rewrite engine Python tanpa
> alasan, dan jangan menghapus backend Go sebelum seluruh dependency
> frontend terhadapnya dipetakan dan digantikan. Implementasikan secara
> bertahap dengan API contract yang jelas dan prioritaskan end-to-end
> makalah generation terlebih dahulu.**

------------------------------------------------------------------------

# 22. Source Repositories

Project yang menjadi sumber integrasi:

``` text
Thesa AI
Repository: thesa-ai-main
Role: Product/UI/UX + existing feature reference
Backend legacy: Go

NeoMakalah
Repository: neomakalaha-main
Role: Academic generation backend/engine
Backend core: Python
Web/API layer: Next.js
```

**Status arsitektur:**

``` text
THESA UI              → KEEP
THESA GO BACKEND      → DEPRECATE → REMOVE
NEOMAKALAH UI         → Reference only / selectively reuse
NEOMAKALAH PYTHON     → KEEP + EXTEND
NEOMAKALAH GENERATION → CORE ENGINE
REAL PROGRESS         → IMPLEMENT
THESA FEATURES        → IMPLEMENT GRADUALLY IN PYTHON
```

------------------------------------------------------------------------

> **Prinsip utama proyek:**
>
> **"Pertahankan pengalaman terbaik dari Thesa dan kemampuan generation
> terbaik dari NeoMakalah; satukan keduanya melalui backend Python yang
> dirancang untuk memenuhi kebutuhan product Thesa."**
