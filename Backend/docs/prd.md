# 📄 Product Requirements Document (PRD)

## MVP — Sistem Generator Makalah CLI (Template UIN + AI)

---

## 1. 🎯 Ringkasan Produk

Produk ini adalah aplikasi berbasis CLI yang memungkinkan pengguna membuat makalah otomatis menggunakan:

* Template kampus (fokus: UIN Alauddin)
* Input data pengguna
* Generate isi makalah (manual / AI)
* Output file `.docx` siap dikumpulkan

Fokus utama MVP:

> **Akurasi format + stabilitas sistem + kemudahan penggunaan**

---

## 2. 🎯 Tujuan MVP

* Menghasilkan makalah sesuai format kampus (≥98% mirip template)
* Memvalidasi penggunaan AI dalam pembuatan makalah
* Mengukur konsumsi token AI secara real
* Menyediakan alur sederhana untuk user (CLI-based)

---

## 3. 👥 Target Pengguna

* Mahasiswa UIN (fase awal)
* Mahasiswa yang ingin membuat makalah cepat dan rapi

---

## 4. 🧩 Scope MVP

---

### ✅ Termasuk:

* CLI application
* 1 template kampus (UIN)
* Input data makalah
* Generate isi:

  * Manual
  * AI (per BAB / full)
* Preview & edit teks sederhana
* Generate file `.docx`
* Token usage tracking

---

### ❌ Tidak termasuk:

* Multi kampus
* Upload template user
* Web interface
* RAG (jurnal real)
* Styling kompleks di CLI
* Multi-user / login system

---

## 5. 🔧 Fitur Utama

---

### 5.1 Template UIN

Template menggunakan file `.docx` yang sudah berisi placeholder:

Contoh:

```text id="tmpl01"
{{mata_kuliah}}
{{judul}}
{{dosen}}
{{penulis_1}}
{{nim_penulis_1}}
{{latar_belakang}}
{{pembahasan}}
{{kesimpulan}}
```

---

### 5.2 Input Data

User mengisi:

* Mata kuliah
* Judul makalah
* Nama dosen
* Nama penulis & NIM
* Jurusan
* Fakultas
* Kampus
* Tahun
* Tempat & tanggal

---

### 5.3 Mode Generate

User memilih:

1. Manual (isi sendiri)
2. AI per BAB
3. AI full

---

### 5.4 AI Content Generator

Menggunakan API dari Z.ai

Kemampuan:

* Generate:

  * Latar belakang
  * Rumusan masalah
  * Tujuan
  * Pembahasan
  * Kesimpulan

Batasan:

* Panjang terkontrol (±500–800 kata per bagian)
* Bahasa akademik formal

---

### 5.5 Preview & Edit

* User melihat hasil di CLI
* Bisa edit ulang sebelum export
* Fokus pada teks (tanpa styling kompleks)

---

### 5.6 Document Generator

* Sistem membaca template `.docx`
* Mengganti placeholder dengan data
* Menghasilkan:

```bash id="out01"
output/makalah.docx
```

---

### 5.7 Token Tracking

Setiap penggunaan AI dicatat:

```json id="tok01"
{
  "feature": "generate_pembahasan",
  "input_tokens": 800,
  "output_tokens": 1200,
  "total": 2000
}
```

---

## 6. 🔄 User Flow

```text id="flow01"
Start
 ↓
Pilih template (UIN)
 ↓
Input data makalah
 ↓
Pilih mode (manual / AI)
 ↓
Generate konten
 ↓
Preview & edit
 ↓
Generate DOCX
 ↓
Selesai
```

---

## 7. 🏗️ Arsitektur Sistem

---

### Modul Utama:

#### 1. Main Controller (`main.py`)

* Mengatur flow CLI

#### 2. Input Handler

* Mengambil input user

#### 3. AI Engine

* Menghubungkan ke API Z.ai
* Generate konten

#### 4. Template Engine

* Replace placeholder dalam DOCX

#### 5. Document Builder

* Generate file akhir

#### 6. Token Logger

* Mencatat penggunaan token

---

## 8. 📁 Struktur Folder

```bash id="struct01"
project/
├── templates/
│   └── template-uin.docx
│
├── output/
├── logs/
│   └── token_usage.json
│
├── src/
│   ├── main.py
│   ├── ai_engine.py
│   ├── input_handler.py
│   ├── template_engine.py
│   ├── document_builder.py
│   └── token_logger.py
```

---

## 9. ⚙️ Non-Functional Requirements

* Output sesuai template ≥ 98%
* Waktu generate ≤ 10 detik per bagian
* Sistem stabil (tidak crash)
* Placeholder berhasil diganti 100%
* CLI mudah digunakan

---

## 10. ⚠️ Risiko & Mitigasi

| Risiko                    | Mitigasi                 |
| ------------------------- | ------------------------ |
| Placeholder tidak terbaca | Standarisasi format      |
| API gagal                 | Tambahkan retry          |
| Token membengkak          | Logging & limit          |
| Format rusak              | Gunakan template cloning |

---

## 11. 📏 Definition of Done

MVP dianggap selesai jika:

* ✅ Template berhasil digunakan
* ✅ User bisa generate makalah (manual & AI)
* ✅ Output `.docx` sesuai format
* ✅ Token usage tercatat
* ✅ Tidak ada error fatal

---

## 12. 🚀 Future Development

* Multi kampus template
* Web version
* RAG (jurnal valid)
* Editor visual
* Sistem akun & pembayaran

---

## 13. 📌 Kesimpulan

MVP ini difokuskan pada:

* Stabilitas engine DOCX
* Integrasi AI sederhana
* Flow CLI yang jelas

Prioritas utama:

> **Makalah jadi, rapi, dan bisa langsung dikumpulkan**

---
