Sip, berarti sekarang kita fokus full ke **AI layer (core intelligence sistemmu)** 🔥
Semua fondasi sudah ada → tinggal bikin **otak sistemnya**.

Aku langsung kasih kamu **AI ENGINE + RESEARCH ENGINE siap pakai (real code + clean + modular)**.

---

# 🧠 ARSITEKTUR AI FINAL

```text
Topik
 ↓
generate_keyword()
 ↓
search_journal()
 ↓
generate_bab()
 ↓
generate_kesimpulan()
 ↓
generate_daftar_pustaka()
```

---

# 🧩 1. `research_engine.py` (AMBIL JURNAL)

```python
import requests

def search_journal(query, limit=5):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"

    params = {
        "query": query,
        "limit": limit,
        "fields": "title,year,authors"
    }

    response = requests.get(url, params=params)
    data = response.json()

    results = []

    for paper in data.get("data", []):
        title = paper.get("title", "Unknown Title")
        year = paper.get("year", "N/A")

        results.append(f"{title} ({year})")

    return results
```

---

# 🧩 2. `ai_engine.py` (CORE AI)

Contoh pakai Gemini-style API (sesuaikan endpoint kamu nanti).

---

## 🔧 Setup dasar

```python
import requests

API_KEY = "API_KEY_KAMU"
API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"
```

---

## 🔹 Helper function

```python
def call_ai(prompt):
    headers = {
        "Content-Type": "application/json"
    }

    params = {
        "key": API_KEY
    }

    body = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    response = requests.post(API_URL, headers=headers, params=params, json=body)
    data = response.json()

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except:
        return "Error generating content"
```

---

# 🧩 3. FUNCTION: GENERATE KEYWORD

```python
def generate_keyword(topik):
    prompt = f"""
Buat 3 keyword pencarian jurnal akademik dari topik berikut:
"{topik}"

Gunakan bahasa Inggris akademik.
Output hanya berupa list tanpa penjelasan.
"""

    result = call_ai(prompt)
    return result
```

---

# 🧩 4. FUNCTION: GENERATE BAB

```python
def generate_bab(topik, bab_name, references):
    refs_text = "\n".join(references)

    prompt = f"""
Buat bagian "{bab_name}" untuk makalah dengan topik:
"{topik}"

Gunakan referensi berikut:
{refs_text}

Ketentuan:
- Bahasa Indonesia formal akademik
- Maksimal 700 kata
- Gunakan paragraf jelas
- Sisipkan referensi (Author, Tahun)
- Jangan membuat referensi baru

Output hanya isi tanpa judul tambahan
"""

    return call_ai(prompt)
```

---

# 🧩 5. FUNCTION: GENERATE KESIMPULAN

```python
def generate_kesimpulan(topik):
    prompt = f"""
Buat kesimpulan makalah dari topik:
"{topik}"

Gunakan bahasa akademik formal.
Maksimal 300 kata.
"""

    return call_ai(prompt)
```

---

# 🧩 6. FUNCTION: DAFTAR PUSTAKA

```python
def generate_daftar_pustaka(references):
    refs_text = "\n".join(references)

    prompt = f"""
Buat daftar pustaka format APA dari referensi berikut:

{refs_text}

Output rapi tanpa penjelasan tambahan.
"""

    return call_ai(prompt)
```

---

# 🧩 7. CONTOH INTEGRASI (MAIN FLOW)

```python
from ai_engine import generate_keyword, generate_bab, generate_kesimpulan, generate_daftar_pustaka
from research_engine import search_journal

def run_pipeline(topik):
    print("🔍 Generating keyword...")
    keyword = generate_keyword(topik)
    print(keyword)

    print("\n📚 Searching journals...")
    journals = search_journal(keyword)
    print(journals)

    print("\n✍️ Generating BAB I...")
    bab1 = generate_bab(topik, "BAB I PENDAHULUAN", journals)

    print("\n✍️ Generating BAB II...")
    bab2 = generate_bab(topik, "BAB II PEMBAHASAN", journals)

    print("\n✍️ Generating BAB III...")
    bab3 = generate_bab(topik, "BAB III PENUTUP", journals)

    print("\n🧠 Generating kesimpulan...")
    kesimpulan = generate_kesimpulan(topik)

    print("\n📖 Generating daftar pustaka...")
    pustaka = generate_daftar_pustaka(journals)

    return {
        "bab1": bab1,
        "bab2": bab2,
        "bab3": bab3,
        "kesimpulan": kesimpulan,
        "daftar_pustaka": pustaka
    }
```

---

# ⚠️ HAL PENTING (JANGAN DIABAIKAN)

---

## ❗ 1. Keyword hasil AI harus dibersihkan

Kadang output:

```text
1. AI in education
2. ...
```

👉 kamu perlu parse → ambil text saja

---

## ❗ 2. Error handling

Tambahkan:

* retry kalau API fail
* fallback kalau kosong

---

## ❗ 3. Token control

Batasi:

* max output
* jangan generate terlalu panjang

---

# 🚀 HASIL AKHIR

Kalau ini jalan:

👉 kamu sudah punya:

* AI research system
* AI writing system
* auto reference system

---

# 🧩 NEXT STEP

Kalau mau lanjut lebih advance:

👉 aku bisa bantu:

* parsing keyword jadi clean list
* auto format ke template_engine
* atau optimasi prompt biar output makin “akademik banget”

---

Tinggal bilang:
👉 “lanjut integrasi ke docx” atau “optimasi ai lagi” 😄
