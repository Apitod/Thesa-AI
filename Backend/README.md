# NeoMakalah

Generator makalah berbasis template DOCX dengan mode CLI dan web (Next.js 16 + Tailwind) yang terhubung ke engine Python.

## Stack
- Frontend web: Next.js 16, React 19, Tailwind CSS
- Backend logic: Python (`src/`) untuk template processing, AI generation, dan DOCX builder
- API bridge: `python_web_bridge.py` (dipanggil dari route Next.js)

## Struktur Folder
```text
neomakalah/
├─ app/                         # Next.js app router (UI + API routes)
├─ src/                         # Core Python engine
├─ templates/                   # Template .docx
├─ output/                      # Hasil dokumen .docx
├─ logs/                        # Log token usage
├─ docs/                        # Dokumentasi proyek
├─ scripts/                     # Script utilitas/test Python
├─ legacy/flask_web/            # Arsip versi web Flask lama
├─ python_web_bridge.py         # Bridge Next API -> Python engine
├─ requirements.txt             # Dependency Python
├─ package.json                 # Dependency Node.js
└─ .env                         # Konfigurasi environment
```

## Setup
1. Install dependency Python
```bash
pip install -r requirements.txt
```

2. Install dependency Node.js
```bash
npm install
```

3. Siapkan `.env`
```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_API_URL=https://openrouter.ai/api/v1/chat/completions
PRIMARY_MODEL=qwen/qwen2.5-7b-instruct-free
```

## Menjalankan Aplikasi
### Web (utama)
```bash
npm run dev
```
Buka: `http://127.0.0.1:3000`

### CLI (opsional)
```bash
python src/main.py
```

## Build & Quality Check
```bash
npm run lint
npm run typecheck
npm run build
```

## Script Python
- Smoke test: `python scripts/run_test.py`
- Test API: `python scripts/test_api.py`
- Test OpenRouter: `python scripts/test_openrouter_simple.py`
- Generate template: `python scripts/create_template.py`

## Catatan
- Jika AI belum siap (key/url belum valid), mode AI akan fallback ke konten manual.
- Seluruh dokumen pendukung lama dipindahkan ke folder `docs/`.
