# Detail Sistem NeoMakalah (Aksara Academic Generator)

NeoMakalah adalah sistem generator makalah akademik otomatis yang dirancang khusus untuk memenuhi standar penulisan akademik Indonesia (khususnya standar UIN). Sistem ini menggabungkan kekuatan **AI (Artificial Intelligence)** dengan **Template Engine berbasis Microsoft Word (.docx)** untuk menghasilkan dokumen yang siap guna dengan format yang presisi.

## 1. Arsitektur Sistem

Sistem ini dibangun menggunakan bahasa pemrograman **Python** dengan struktur modular:

- **`main.py`**: Entry point aplikasi yang mengatur alur kerja (workflow) utama.
- **`input_handler.py`**: Mengelola interaksi dengan pengguna (CLI) untuk mengumpulkan metadata makalah, informasi penulis, dan institusi.
- **`ai_engine.py`**: Otak AI sistem yang terhubung ke **OpenRouter API** (seperti Qwen/GPT-4) untuk menghasilkan konten akademik. Ia juga terintegrasi dengan **SerpApi (Google Scholar)** untuk mencari referensi jurnal nyata.
- **`template_engine.py`**: Mengelola proses injeksi data ke dalam file `.docx`. Mengatur pemformatan paragraf, indentasi, dan *Table of Contents* (Daftar Isi).
- **`document_builder.py`**: Memproses teks kasar dari AI menjadi data yang terstruktur sesuai dengan placeholder di template.
- **`cite_renderer.js`**: Modul berbasis **Node.js** yang menggunakan **citation-js** untuk mengubah referensi BibTeX menjadi format sitasi APA secara otomatis.

---

## 2. Fitur Utama

### A. Tiga Mode Pembuatan Konten
1. **Manual**: Pengguna mengetik sendiri isi makalah per bagian.
2. **AI Per BAB**: Pengguna bisa memilih bagian mana yang ingin dibuat oleh AI dan mana yang ingin diisi manual.
3. **AI Full**: AI menghasilkan seluruh konten makalah mulai dari Kata Pengantar hingga Daftar Pustaka secara otomatis.

### B. Smart Manual (Penyempurnaan Input Manual)
Meskipun pengguna memilih mode manual, sistem tetap memiliki fitur **Refinement**. Jika input pengguna terlalu singkat atau bahasaka kurang formal, AI akan merapikannya menjadi bahasa akademik yang lebih baik tanpa menghilangkan substansi aslinya.

### C. Integrasi Referensi Nyata (Google Scholar)
Sistem dapat melakukan pencarian otomatis ke Google Scholar menggunakan **SerpApi**. Hal ini memastikan sitasi dan daftar pustaka yang digunakan adalah jurnal/buku yang benar-benar ada, bukan sekadar karangan AI.

### D. Pemformatan Akademik Otomatis
Sistem mengatur secara otomatis:
- **Font**: Cambria/Times New Roman (Ukuran 12).
- **Indetasi Paragraf**: Baris pertama menjorok ke dalam (1.27 cm).
- **Line Spacing**: 1.5 spasi untuk isi, 2.0 spasi untuk Daftar Isi.
- **Heading**: Penomoran otomatis (A, B, C, D) pada Bab II Pembahasan.
- **Alignment**: Rata kanan-kiri (Justify).

---

## 3. Alur Kerja (Workflow)

1. **Input Data**: Pengguna memasukkan judul, mata kuliah, nama dosen, dan informasi penulis (1-3 orang).
2. **Setup Institusi**: Memasukkan nama jurusan, fakultas, kampus, dan tahun.
3. **Pemilihan Mode**: Memilih mode pembuatan (Manual/AI).
4. **Pencarian Referensi**: AI mencari jurnal terkait di internet.
5. **Generasi Konten**: AI membuat teks akademik berdasarkan prompt khusus yang memaksa gaya penulisan formal.
6. **Injeksi Template**: Teks yang dihasilkan dimasukkan ke file template `.docx`.
7. **Penyempurnaan Akhir**: Sistem merapikan daftar isi, memastikan nomor halaman sejajar, dan menghapus sisa-sisa karakter markdown.
8. **Output**: File disimpan dalam format `.docx` di folder `output/`.

---

## 4. Keunggulan Teknis

- **Struktur Pembahasan Terpola**: Pada Bab II, sistem mewajibkan pola 3 paragraf (Definisi & Teori, Contoh Kasus/Penerapan, Analisis Kritis) untuk setiap sub-bab.
- **Clean Output**: Sistem memiliki filter regex yang kuat untuk memastikan tidak ada simbol markdown (seperti `**` atau `##`) yang terbawa ke dalam dokumen Word.
- **Presisi Daftar Isi**: Menggunakan logika *Tab Stop* dengan *Dot Leader* yang memastikan titik-titik di Daftar Isi sejajar sempurna, baik di versi Word maupun saat diekspor ke PDF.
- **Token Usage Logging**: Setiap penggunaan API AI dicatat dalam log untuk transparansi biaya/penggunaan token.
