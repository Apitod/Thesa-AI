# Thesa AI × NeoMakalah

Thesa AI adalah platform AI terpadu yang dirancang khusus untuk mahasiswa dan peneliti guna membantu proses akademik, seperti penulisan karya ilmiah, analisis literatur, pendampingan akademik (*Socratic coaching*), hingga simulasi sidang (*Viva Voce*). 

Proyek ini merupakan integrasi dari sistem Thesa UI dengan mesin kecerdasan buatan dari NeoMakalah, menggunakan arsitektur **Python FastAPI**, **Celery**, **Redis**, dan antarmuka pengguna statis yang elegan.

---

## 🌟 Fitur Utama

- **Pembuatan Makalah Otomatis (AI-driven):** Pembuatan dokumen Word (DOCX) secara asinkron dengan *real-time progress tracking* menggunakan *Server-Sent Events* (SSE).
- **Pendampingan Akademik (Socratic Supervisor):** Analisis makro naskah ilmiah, pemberian umpan balik, dan evaluasi kesiapan sidang.
- **Simulasi Ujian (Examiner Persona):** Mensimulasikan pertanyaan dewan penguji dengan persona kritis, metodologis, atau teoretis.
- **Pembayaran Terintegrasi (Midtrans QRIS/Snap):** Sistem pemesanan paket *single* atau *semester* lengkap dengan penanganan *webhook* otomatis.
- **Dashboard Admin Telemetri:** Pantauan metrik pengguna, penggunaan token LLM, status pesanan, dan *audit logs*.
- **Zero-Dependency Database:** Menyimpan data secara persisten dan ringan menggunakan SQLite (`thesa.db`) tanpa perlu instalasi basis data eksternal, dengan dukungan in-memory fallback.

---

## 🏗️ Arsitektur Sistem

Seluruh sistem sekarang 100% didukung oleh ekosistem Python:

```text
Pengguna / Browser
   │
   ├── /app, /auth, /admin ──→ Antarmuka Statis (Frontend/web/)
   │
   └── /api/v1/... (FastAPI Core Backend)
         ├── Autentikasi (Register, Login, Session)
         ├── Pembayaran (Midtrans API)
         ├── Supervisor AI (Evaluasi Naskah & Sidang)
         ├── Admin Controlling (Telemetri & Metrik)
         └── Pembangkit Naskah (Task Queue Async via Celery)
               ↓
             Redis ──→ Celery Worker ──→ NeoMakalah Engine (DOCX Generator)
```

---

## 🛠️ Prasyarat

Sebelum menjalankan aplikasi, pastikan sistem Anda telah terinstal:
- **Python 3.12+**
- **Redis** (dapat dijalankan via Docker)
- **Docker & Docker Compose** (opsional, sangat direkomendasikan untuk produksi)

---

## 🚀 Panduan Instalasi (Development Lokal)

### 1. Setup Environment
Pindah ke direktori `Backend`, buat *virtual environment*, dan instal dependensi:
```bash
cd Backend
python -m venv .venv
source .venv/bin/activate  # Untuk Windows: .venv\Scripts\activate
pip install -r python_api/requirements.txt
```

Salin file konfigurasi *environment*:
```bash
cp python_api/.env.example python_api/.env
```
*(Catatan: Anda dapat menambahkan kunci API opsional seperti `MIDTRANS_SERVER_KEY`, `DEEPSEEK_API_KEY`, atau `GEMINI_API_KEY` di dalam file `.env` ini).*

### 2. Jalankan Redis
Redis diperlukan untuk *message broker* antrean Celery dan *Server-Sent Events* (SSE).
```bash
docker run -d -p 6379:6379 redis:7-alpine
```

### 3. Jalankan Server FastAPI (Terminal 1)
```bash
cd Backend
source .venv/bin/activate
PYTHONPATH=. uvicorn python_api.main:app --reload --port 8001
```

### 4. Jalankan Celery Worker (Terminal 2)
```bash
cd Backend
source .venv/bin/activate
PYTHONPATH=. celery -A python_api.worker.celery_app worker --loglevel=info
```

---

## 🐳 Panduan Instalasi (Docker Compose)
Cara termudah untuk menjalankan keseluruhan ekosistem (FastAPI, Redis, Celery) dalam satu perintah:

```bash
cd Backend
docker-compose up --build -d
```
Aplikasi akan tersedia di port `8001`.

---

## 💻 Cara Penggunaan Aplikasi

Setelah server berjalan, Anda dapat mengakses antarmuka pengguna melalui peramban:

- **Halaman Pendaratan (Landing):** [http://localhost:8001/](http://localhost:8001/)
- **Halaman Autentikasi:** [http://localhost:8001/auth](http://localhost:8001/auth)
- **Halaman Utama (Workspace):** [http://localhost:8001/app](http://localhost:8001/app)
- **Dasbor Admin:** [http://localhost:8001/admin](http://localhost:8001/admin)

### Akun Demo Bawaan
Sistem otomatis membuat dua akun saat pertama kali dihidupkan untuk mempermudah demonstrasi:

1. **Akun Mahasiswa (User)**
   - Email: `alif.awwaz@ui.ac.id`
   - Password: `thesa2026` (atau `password`)

2. **Akun Administrator (Admin)**
   - Email: `admin@thesa.id`
   - Password: `admin2026`

---

## 🧪 Pengujian QA
Untuk menjalankan rangkaian tes (22 skenario) yang memverifikasi semua integrasi titik akhir API:
```bash
cd Backend
source .venv/bin/activate
python python_api/tests/test_all_migrated_endpoints.py
```

---

## 📁 Struktur Direktori

- `Frontend/web/` - Seluruh aset UI (HTML, CSS, JS murni). Disajikan secara langsung oleh FastAPI.
- `Backend/python_api/` - Inti layanan backend:
  - `routes/` - Pengelompokan logika endpoint (`auth`, `payment`, `supervisor`, `admin`, `generations`).
  - `services/db.py` - Pengelola database SQLite dan *fallback* ke memori lokal.
  - `worker/` - Konfigurasi Celery dan integrasi langsung dengan mesin NeoMakalah.
  - `main.py` - File utama untuk menjalankan server FastAPI.
- `_archived_go_backend/` - Kumpulan kode warisan (*legacy*) dari backend Go terdahulu yang tidak lagi aktif.

---
*Proyek ini dikembangkan menggunakan dukungan penuh dari asisten AI Thesa.*
