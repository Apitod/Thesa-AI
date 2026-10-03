import os
import re
import time
import json
import requests
from typing import Dict, Tuple, Optional, List
from dotenv import load_dotenv
from rich.console import Console
from src.reference_engine import ReferenceEngine, ReferenceCandidate, get_reference_engine
from src.fewshot_cache import get_fewshot_cache


load_dotenv()


def strip_markdown(text: str) -> str:
    """Remove markdown formatting artifacts from AI-generated text.
    
    Ensures clean plain text output suitable for DOCX insertion.
    """
    if not text:
        return text

    # Remove markdown headings (## Heading -> Heading)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

    # Remove bold markers (**text** or __text__)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)

    # Remove italic markers (*text* or _text_)
    text = re.sub(r'(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)', r'\1', text)
    text = re.sub(r'(?<!_)_(?!_)(.+?)(?<!_)_(?!_)', r'\1', text)

    # Remove markdown bullet points (- item or * item) but keep the text
    text = re.sub(r'^[\-\*]\s+', '', text, flags=re.MULTILINE)

    # Remove markdown blockquotes
    text = re.sub(r'^>\s+', '', text, flags=re.MULTILINE)

    # Remove backticks
    text = re.sub(r'`{1,3}', '', text)

    # Remove horizontal rules
    text = re.sub(r'^[\-\*_]{3,}\s*$', '', text, flags=re.MULTILINE)

    # Remove [AI Model: ...] tags
    text = re.sub(r'\[AI Model:.*?\]', '', text)

    # Clean up excessive blank lines (max 2 consecutive newlines)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


class AIEngine:
    def __init__(self):
        self.console = Console()

        # Load OpenRouter configuration
        self.openrouter_key = os.getenv('OPENROUTER_API_KEY')
        self.openrouter_url = os.getenv('OPENROUTER_API_URL')
        self.primary_model = os.getenv('PRIMARY_MODEL', 'qwen/qwen2.5-7b-instruct-free')
        self.serpapi_key = os.getenv('SERPAPI_KEY')

        # Reference engine (multi-stage pipeline)
        self.reference_engine = get_reference_engine()

        # Few-shot learning cache
        self.fewshot_cache = get_fewshot_cache()
        cache_stats = self.fewshot_cache.get_stats()
        total_examples = sum(cache_stats.values())
        if total_examples > 0:
            self.console.print(f"[green]📚 Few-Shot Cache loaded: {total_examples} examples across {len([v for v in cache_stats.values() if v > 0])} sections[/green]")

        if not self.openrouter_key or self.openrouter_key == 'your_openrouter_api_key_here':
            self.console.print("[yellow]WARNING: OPENROUTER_API_KEY belum diatur di file .env[/yellow]")
            self.console.print("[yellow]Fitur AI tidak akan berfungsi sampai API key diatur[/yellow]\n")
            self.api_available = False
        else:
            self.api_available = True
            self.console.print(f"[green]OpenRouter Key detected: {self.openrouter_key[:10]}...{self.openrouter_key[-4:]}[/green]")
            self.console.print(f"[cyan]OpenRouter URL: {self.openrouter_url}[/cyan]\n")
            self.console.print(f"[green]Primary Model: {self.primary_model}[/green]\n")

    def verify_academic_topic(self, judul: str) -> Tuple[bool, str]:
        """Perform a check on topic viability with heuristics, hard filters and AI analysis."""
        if not self.api_available:
            return True, ""

        # 1. HEURISTIC FILTER (Length check)
        # Judul ilmiah biasanya minimal 3 kata. Judul 1-2 kata (misal: "Makan") biasanya bukan judul akademis.
        word_count = len(judul.split())
        if word_count < 3:
            return False, "Judul terlalu pendek. Cobalah buat judul yang lebih spesifik (minimal 3 kata) agar memenuhi standar akademik."

        # 2. HARD FILTER (Local check for vulgarity)
        bad_words = [
            "ngentot", "memek", "kontol", "anjing", "bangsat", "goblok", 
            "tolol", "sex", "porno", "colly", "bokep", "ngocok", "peler",
            "jancok", "asu", "bgst", "vcs", "open bo", "lonte", "bitch"
        ]
        
        judul_lower = judul.lower()
        for word in bad_words:
            if word in judul_lower:
                self.console.print(f"[bold red]❌ BLOCKED BY HARD FILTER: {word}[/bold red]")
                return False, f"Input mengandung kata tidak pantas: '{word}'. Mohon gunakan bahasa akademik yang sopan."

        # 3. AI DEEP ANALYSIS
        self.console.print(f"[bold yellow]🔍 Analyzing Topic Viability: {judul}[/bold yellow]")

        prompt = f"""
Saring apakah JUDUL berikut layak untuk sebuah makalah ilmiah kampus.
JUDUL: "{judul}"

RESPON JSON:
{{
  "is_academic": boolean,
  "field_of_study": "Bidang Ilmu",
  "reason": "Alasan penolakan jika is_academic false",
  "suggested_title": "Saran judul lebih baik"
}}
"""
        response_data, _, _ = self.call_api(prompt)
        if response_data and 'message' in response_data:
            msg = response_data['message']
            try:
                match = re.search(r'\{.*\}', msg, re.DOTALL)
                if match:
                    data = json.loads(match.group())
                    is_academic = data.get('is_academic', True) # Balik ke True jika tidak ada field
                    field = data.get('field_of_study', 'Akademik')
                    
                    if is_academic:
                        self.console.print(f"[green]✅ Terverifikasi: {field}[/green]")
                        return True, ""
                    else:
                        reason = data.get('reason', 'Topik kurang sesuai standar akademik.')
                        saran = data.get('suggested_title', 'Gunakan judul yang lebih formal.')
                        return False, f"Ditolak: {reason}. \n\nSaran: {saran}"
            except:
                pass
        
        # Jika AI gagal (limit/error), jangan hambat user jika judulnya panjang
        return True, ""

    def format_prompt(self, section_type: str, context: Dict[str, str]) -> str:
        judul = context.get('judul', '')
        mata_kuliah = context.get('mata_kuliah', '')
        jurusan = context.get('jurusan', '')
        real_journals = context.get('real_journals', '')

        if real_journals:
            dp_instructions = f"- Tuliskan dan susun referensi nyata berikut ini agar menjadi daftar pustaka standar.\nReferensi Google Scholar:\n{real_journals}"
        else:
            dp_instructions = "- Buat tepat 3-5 referensi buku atau jurnal fiktif namun realistis dan relevan dengan topik."

        # Common formatting rules appended to every prompt
        format_rules = """

ATURAN FORMAT WAJIB (STRICT):
1. BAHASA: Tulis dalam bahasa Indonesia formal akademik. Gunakan struktur kalimat kompleks dan konjungsi akademik (oleh karena itu, dengan demikian, selanjutnya).
2. TONE: Deskriptif dan objektif.
3. PARAGRAF: Buat paragraf yang panjang dan padat (4-8 kalimat per paragraf).
6. TAB & SPASI: Pisahkan antar paragraf dengan satu baris kosong.
7. Tidak boleh ada format tebal/bold, miring/italic pada seluruh isi konten.
8. DILARANG KERAS menuliskan Judul Sub/Bab di teks awal (tapi sub-bab boleh di Bab 2 saja jika diperlukan). Untuk Kata Pengantar, Latar Belakang, Rumusan Masalah, Kesimpulan, dll MAKA LANGSUNG TULIS ISI PARAGRAFNYA. JANGAN MENGULANG TULIS "BAB 1 PENDAHULUAN" ATAU "KATA PENGANTAR". Template docx sudah menyiapkan judulnya otomatis!
"""

        # Inject few-shot example if available (reduces need for verbose instructions)
        fewshot_block = self.fewshot_cache.build_fewshot_block(section_type, judul, mata_kuliah)
        if fewshot_block:
            format_rules = f"\n{fewshot_block}\n{format_rules}"
            self.console.print(f"[dim]  💡 Few-shot example injected for {section_type}[/dim]")

        prompts = {
            'latar_belakang': f"""Tulis bagian Pendahuluan (Latar Belakang) untuk makalah berjudul: "{judul}"
untuk mata kuliah {mata_kuliah} jurusan {jurusan}.

STRUKTUR WAJIB (Bab 1 - Latar Belakang):
- Panjang minimal: 250 kata.
- Terdiri dari tepat 2 paragraf utama, namun jika panjang bisa dipecah dengan syarat transisi mengalir (konteks umum -> spesifik).
- Pola pembahasan harus mencakup secara berurutan: definisi umum terkait topik, pentingnya topik tersebut, masalah yang terjadi saat ini, dan alasan pembahasan.
- Gaya penulisan: Deskriptif.

KONTEN:{format_rules}""",

            'rumusan_masalah': f"""Tulis bagian Rumusan Masalah untuk makalah berjudul: "{judul}"
dalam mata kuliah {mata_kuliah}.

STRUKTUR WAJIB (Bab 1 - Rumusan Masalah):
Tulis 1 KATA/KALIMAT pendek saja sebagai pengantar (misal: "Berdasarkan latar belakang tersebut, adapun rumusan masalah dalam makalah ini adalah sebagai berikut:"). Jangan terlalu panjang!

Kemudian, tuliskan dalam format list berisi TEPAT 4 pertanyaan rumusan masalah (WAJIB 4 POIN, TIDAK BOLEH KURANG ATAU LEBIH).
Setiap pertanyaan/poin HARUS DITULIS SEPANJANG TEPAT 2 BARIS SAJA (TIDAK BOLEH LEBIH, TIDAK BOLEH KURANG). Jangan buat pertanyaan yang terlalu pendek (1 baris) dan jangan terlalu panjang (3 baris ke atas).
Format list harus angka lurus biasa seperti ini (tanpa bold/italic):
1. Pertanyaan pertama...
2. Pertanyaan kedua...
3. Pertanyaan ketiga...
4. Pertanyaan keempat...

Gunakan gaya kalimat pertanyaan (misal: "Bagaimana...", "Apa peran...").{format_rules}""",

            'tujuan': f"""Tulis bagian Tujuan Penulisan untuk makalah berjudul: "{judul}"
dalam mata kuliah {mata_kuliah}.

STRUKTUR WAJIB (Bab 1 - Tujuan):
Tulis 1 KATA/KALIMAT pendek saja sebagai pengantar (misal: "Adapun tujuan dari penulisan makalah ini adalah sebagai berikut:"). Jangan terlalu panjang!

Kemudian, tuliskan dalam format list berisi TEPAT 4 tujuan (WAJIB 4 POIN, TIDAK BOLEH KURANG ATAU LEBIH). Jumlah dan isi tujuan ini HARUS memetakan (mapping) langsung dari 4 rumusan masalah.
Isi pada masing-masing poin tujuan HARUS DITULIS SEPANJANG TEPAT 2 BARIS SAJA (TIDAK BOLEH LEBIH, TIDAK BOLEH KURANG). Jangan buat penjelasan yang terlalu pendek (1 baris) dan jangan terlalu panjang (3 baris ke atas). Berikan penjelasan padat yang memadai (misal: "Menguraikan secara komprehensif mengenai konsep dan definisi X, termasuk sejarah awal mula perkembangannya dalam masyarakat...").
Format list harus angka lurus biasa:
1. Tujuan pertama...
2. Tujuan kedua...
3. Tujuan ketiga...
4. Tujuan keempat...{format_rules}""",

            'pembahasan': f"""Tulis bagian Pembahasan untuk makalah berjudul: "{judul}"
dalam mata kuliah {mata_kuliah} jurusan {jurusan}.

Ini adalah BAB 2 - PEMBAHASAN. Bagian ini WAJIB menjadi bagian TERPANJANG dari seluruh makalah.
(TIDAK PERLU menulis "BAB II PEMBAHASAN" di baris pertama, langsung mulai saja).

STRUKTUR WAJIB:
- Panjang: 600 - 1200 kata. (Kurangi sedikit agar tidak terlalu boros halaman).
- Jumlah Paragraf: 5 - 10 paragraf total.
- Sub-bagian: WAJIB pecah menjadi TEPAT 4 sub-bab (A, B, C, D) yang langsung menjawab dan membahas ke-4 Rumusan Masalah.
- Tiap sub-bab WAJIB diawali dengan judul singkat berformat abjad (Contoh: "A. Definisi Sistem", "B. Dampak Positif Teknologi"). JANGAN mencetak tebal/bold judulnya, cukup tulis biasa.

POLA PEMBAHASAN:
Untuk setiap topik atau sub-bab, isi penjabaran WAJIB DIPECAH menjadi TEPAT 3 PARAGRAF terpisah!
Gunakan pola alur pembahasan berikut dalam memecah paragraf:
1. Paragraf 1: Definisi dan teori yang mendasari.
2. Paragraf 2: Contoh kasus atau penerapan di dunia nyata.
3. Paragraf 3: Penjelasan mendalam / analisis kritis.

KUTIPAN/REFERENSI WAJIB:
- Sertakan 2-4 kutipan (sitasi) dari jurnal nyata dalam teks menggunakan format in-text citation APA (Penulis, Tahun).
{("- JURNAL REFERENSI YANG HARUS DIGUNAKAN UNTUK SITASI:\\n" + real_journals if real_journals else "- Gunakan format sitasi: (Penulis, Tahun) di akhir kalimat yang mengandung teori.")}{format_rules}""",

            'kesimpulan': f"""Tulis bagian Kesimpulan untuk makalah berjudul: "{judul}"
dalam mata kuliah {mata_kuliah}.

STRUKTUR WAJIB (Bab 3 - Penutup):
- Kesimpulan WAJIB terdiri dari TEPAT 2 PARAGRAF terpisah.
- Paragraf 1: Berisi ringkasan langsung dari poin-poin utama di BAB 2 (Pembahasan).
- Paragraf 2: Berisi rekomendasi praktis atau akademis terkait topik (Saran).
- JANGAN menulis sub-judul "A. Kesimpulan" atau "Saran". Langsung mulai dengan teks paragraf pertama.{format_rules}""",
            
            'kata_pengantar': f"""Tulis bagian Kata Pengantar untuk makalah berjudul: "{judul}".

STRUKTUR WAJIB:
- Panjang: MAKSIMAL 1-2 paragraf pendek saja! BUKAN hal yang panjang. Tujuannya agar muat di 1 halaman yang sama dengan nama Penyusun.
- Gaya penulisan: Semi-formal.
- Pola pembahasan secara berurutan:
  1. Ucapan puji syukur.
  2. Tujuan penulisan makalah secara singkat.
  3. Ucapan terima kasih (opsional).
  4. Penutup (harapan).{format_rules}""",
            
            'daftar_pustaka': f"""Tulis bagian Daftar Pustaka untuk makalah berjudul: "{judul}"
dengan mata kuliah {mata_kuliah}.

STRUKTUR WAJIB DAN KETAT (CSL COMPLIANT):
- Berikan daftar referensi jurnal/buku yang Anda kutip.
- Anda WAJIB memberikan output MURNI HANYA dalam format BibTeX (@article, @book, dll).
- JANGAN berikan teks pengantar, penutup, atau penjelasan apapun di luar blok BibTeX.
- JANGAN menuliskan judul "DAFTAR PUSTAKA". Langsung berikan daftar BibTeX-nya.
- Berikan minimal 3-5 referensi berbentuk jurnal/buku yang relevan.
{dp_instructions}

Contoh Output BibTeX yang benar:
@article{{smith2023,
    title={{Judul Artikel Jurnal}},
    author={{Nama, Penulis and Penulis, Kedua}},
    journal={{Nama Jurnal}},
    year={{2023}},
    volume={{1}},
    pages={{1--10}}
}}
"""
        }

        return prompts.get(section_type, f"Buat {section_type.replace('_', ' ')} untuk makalah berjudul: {judul}")

    def estimate_tokens(self, text: str) -> int:
        return int(len(text.split()) * 1.5)

    def search_references(self, context: Dict[str, str], mode: str = "smart", citation_min: int = 5, citation_max: int = 10) -> Tuple[list, str]:
        """Search academic references using the multi-stage pipeline.
        
        Returns (candidates_list, formatted_string_for_prompt)
        """
        judul = context.get('judul', '')
        mata_kuliah = context.get('mata_kuliah', '')
        jurusan = context.get('jurusan', '')
        
        candidates, formatted = self.reference_engine.search_references(
            judul=judul,
            mata_kuliah=mata_kuliah,
            mode=mode,
            jurusan=jurusan,
            citation_min=citation_min,
            citation_max=citation_max,
        )
        return candidates, formatted

    def call_api(self, prompt: str, max_retries: int = 3) -> Tuple[Optional[dict], int, int]:
        if not self.api_available:
            self.console.print("[red]AI API tidak tersedia. Gunakan mode manual atau atur API key.[/red]")
            return None, 0, 0

        # Use OpenRouter API format
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.openrouter_key}',
            'HTTP-Referer': 'https://openrouter.ai'  # Required by OpenRouter
        }

        # OpenRouter payload format
        payload = {
            'model': self.primary_model,  # Use the configured primary model
            'messages': [
                {
                    'role': 'system',
                    'content': (
                        'Anda adalah asisten penulisan akademik profesional. '
                        'Anda menulis dalam bahasa Indonesia formal yang baik dan benar. '
                        'ATURAN KETAT: Anda HANYA menulis plain text murni. '
                        'DILARANG KERAS menggunakan format markdown seperti **, __, ##, *, -, `, atau format lainnya. '
                        'DILARANG menulis ulang judul Bab/Bagian (misalnya jangan tulis "BAB I PENDAHULUAN" atau "Kata Pengantar" di awal respons). Langsung ke isi saja. '
                        'Untuk penomoran gunakan angka biasa (1. 2. 3.) tanpa format khusus. '
                        'Pisahkan paragraf dengan baris kosong. '
                        'Tulis dengan gaya akademis yang natural dan terstruktur.'
                    )
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'temperature': 0.7,
            'max_tokens': 2000
        }

        input_tokens = self.estimate_tokens(prompt)

        self.console.print(f"[cyan]Making OpenRouter API request to {self.openrouter_url}...[/cyan]")

        for attempt in range(max_retries):
            try:
                start_time = time.time()

                self.console.print(f"[dim]Attempt {attempt + 1}/{max_retries}...[/dim]")

                response = requests.post(
                    self.openrouter_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                )

                elapsed_time = time.time() - start_time

                self.console.print(f"[dim]Response status: {response.status_code}[/dim]")

                if response.status_code == 200:
                    try:
                        response_data = response.json()

                        # Handle OpenRouter response format
                        if 'choices' in response_data:
                            content = response_data['choices'][0]['message']['content']
                        elif 'message' in response_data:
                            content = response_data['message']['content'] if isinstance(response_data['message'], dict) else str(response_data['message'])
                        elif 'content' in response_data:
                            content = response_data['content']
                        elif 'data' in response_data:
                            content = response_data['data']
                        else:
                            self.console.print("[red]Unexpected OpenRouter response format[/red]")
                            self.console.print(f"[dim]Response: {json.dumps(response_data, indent=2)[:500]}[/dim]")
                            return None, input_tokens, 0

                        # Post-process: strip any remaining markdown
                        content = strip_markdown(content)

                        output_tokens = self.estimate_tokens(content)

                        self.console.print(f"[green][OK] OpenRouter API call successful ({elapsed_time:.2f}s)[/green]")

                        return {
                            'content': content,
                            'model': response_data.get('model', 'unknown'),
                            'response_time': elapsed_time
                        }, input_tokens, output_tokens

                    except json.JSONDecodeError as e:
                        self.console.print(f"[red]JSON Decode Error: {e}[/red]")
                        self.console.print(f"[dim]Response text: {response.text[:500]}[/dim]")
                        return None, input_tokens, 0

                elif response.status_code == 401:
                    self.console.print(f"[red]Authentication Error: OpenRouter API key tidak valid atau expired[/red]")
                    self.console.print(f"[yellow]Cek API key di file .env[/yellow]")
                    return None, input_tokens, 0

                elif response.status_code == 402:
                    try:
                        error_data = response.json()
                        error_message = error_data.get('error', {}).get('message', str(error_data))

                        self.console.print(f"[red]Payment Required: OpenRouter balance tidak cukup[/red]")
                        self.console.print(f"[yellow]Top up balance di dashboard OpenRouter Anda[/yellow]")
                        return None, input_tokens, 0
                    except:
                        self.console.print(f"[red]Payment Required: Response: {response.text[:200]}[/red]")

                elif response.status_code == 429:
                    self.console.print(f"[yellow]Rate Limit: Terlalu banyak request. Tunggu sebentar...[/yellow]")
                    if attempt < max_retries - 1:
                        time.sleep(5)
                        continue
                    else:
                        return None, input_tokens, 0

                elif response.status_code == 500:
                    self.console.print(f"[yellow]Server Error: OpenRouter API server error[/yellow]")
                    if attempt < max_retries - 1:
                        time.sleep(5)
                        continue
                    else:
                        return None, input_tokens, 0

                else:
                    self.console.print(f"[yellow]OpenRouter API call failed (attempt {attempt + 1}/{max_retries}): {response.status_code}[/yellow]")
                    self.console.print(f"[dim]Response: {response.text[:500]}[/dim]")

                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) * 2
                        self.console.print(f"[dim]Waiting {wait_time}s before retry...[/dim]")
                        time.sleep(wait_time)

            except requests.exceptions.Timeout:
                self.console.print(f"[yellow]OpenRouter API timeout (attempt {attempt + 1}/{max_retries})[/yellow]")
                if attempt < max_retries - 1:
                    time.sleep((2 ** attempt) * 2)

            except requests.exceptions.ConnectionError as e:
                self.console.print(f"[red]Connection error: Tidak dapat terhubung ke OpenRouter[/red]")
                self.console.print(f"[yellow]Error: {str(e)}[/yellow]")
                return None, input_tokens, 0

            except Exception as e:
                self.console.print(f"[red]Error calling OpenRouter: {e}[/red]")
                import traceback
                self.console.print(f"[dim]{traceback.format_exc()}[/dim]")
                return None, input_tokens, 0

        self.console.print(f"[red]Max retries reached. OpenRouter API call failed.[/red]")
        return None, input_tokens, 0

    def generate_section(self, section_type: str, context: Dict[str, str]) -> Tuple[str, int, int]:
        self.console.print(f"\\n[cyan]Generating {section_type.replace('_', ' ').title()} with model {self.primary_model}...[/cyan]")
        
        # Jurnal sudah di-load di awal generate_full_paper
        prompt = self.format_prompt(section_type, context)

        result, input_tokens, output_tokens = self.call_api(prompt)

        if result and 'content' in result:
            content = result['content'].strip()
            
            # === CSL INTERCEPTION FOR DAFTAR PUSTAKA ===
            if section_type == 'daftar_pustaka':
                import subprocess
                import os
                self.console.print("[cyan]Processing BibTeX through CSL engine (citation-js)...[/cyan]")
                try:
                    js_path = os.path.join(os.path.dirname(__file__), 'cite_renderer.js')
                    process = subprocess.Popen(
                        ['node', js_path],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding='utf-8'
                    )
                    out, err = process.communicate(input=content, timeout=15)
                    if process.returncode == 0 and out.strip():
                        content = out.strip()
                        self.console.print("[green][OK] CSL APA Formatting successful[/green]")
                    else:
                        self.console.print(f"[red][WARNING] CSL Engine failed or returned empty: {err}[/red]")
                except Exception as e:
                    self.console.print(f"[red][WARNING] CSL Engine error: {e}[/red]")
            # ==========================================
            
            self.console.print(f"[green][OK] {section_type.replace('_', ' ').title()} generated successfully ({output_tokens} tokens)[/green]")
            return content, input_tokens, output_tokens
        else:
            self.console.print(f"[red][FAIL] Failed to generate {section_type.replace('_', ' ').title()}[/red]")
            return "", input_tokens, output_tokens

    def refine_manual_section(self, section_type: str, user_input: str, context: Dict[str, str]) -> Tuple[str, int, int]:
        """Refines rough user input into professional academic text."""
        if not user_input or not user_input.strip():
            # If no input provided but in manual mode, generate from scratch
            return self.generate_section(section_type, context)

        self.console.print(f"\n[cyan]Refining manual input for {section_type.replace('_', ' ').title()}...[/cyan]")
        
        judul = context.get('judul', '')
        mata_kuliah = context.get('mata_kuliah', '')
        refine_rules = """
ATURAN FORMAT WAJIB:
1. Tidak boleh ada format tebal/bold, miring/italic, dsb (TIDAK ADA MARKDOWN ** ATAU __).
2. Pisahkan paragraf dengan baris kosong.
3. DILARANG KERAS menulis ulang judul bagian (jangan tulis "BAB 1 PENDAHULUAN" atau "RUMUSAN MASALAH" di awal teks). Langsung tulis ke isinya (atau daftar list/paragrafnya).
"""

        refine_prompt = f"""Anda adalah Editor Akademik Profesional.
User memberikan asupan draf / kerangka manual untuk bagian {section_type.replace('_', ' ').title()} dari makalah "{judul}" (Mata Kuliah: {mata_kuliah}).

INPUT USER KASAR:
---
{user_input}
---

TUGAS ANDA:
1. Rapikan tata bahasa, ejaan, dan struktur bahasanya ke bahasa Indonesia formal.
2. PERTAHANKAN poin-poin yang diberikan user tanpa melebih-lebihkannya. Jika user memberikan pertanyaan sederhana, JANGAN merombaknya menjadi berbelit-belit (tetap pertahankan kalimat ringkas user).
3. KETENTUAN KHUSUS SEKSI INI:"""

        if section_type == 'rumusan_masalah' or section_type == 'tujuan':
            refine_prompt += f"\n- Jika user memberikan kurang dari 4 poin, Anda WAJIB menambahkan poin tambahan untuk melengkapinya menjadi TEPAT 4 poin."
            refine_prompt += f"\n- Pertahankan teks rumusan/tujuan user semirip mungkin dengan aslinya (jangan dibuat kompleks). Cukup berikan satu kalimat pengantar pendek dan format list angka biasa."
        elif section_type == 'latar_belakang':
            refine_prompt += "\n- Jika input terlalu singkat (misal hanya 1 kalimat), kembangkan sedikit secara logis agar menjadi 2 paragraf pendek. Tetap fokus pada konteks yang diangkat user."
        elif section_type == 'pembahasan':
            refine_prompt += "\n- Tata menjadi sub-bab berformat huruf abjad (A., B., C., D.) berdasarkan poin user. Jika penjelasan user kurang, tambahkan argumen pendukung sewajarnya."
        elif section_type == 'kesimpulan':
            refine_prompt += "\n- Pecah menjadi dua paragraf pendek: Paragraf 1 untuk ringkasan (merangkum poin user), Paragraf 2 untuk saran (bisa buatkan jika user tidak memberi saran)."

        refine_prompt += f"\n\n{refine_rules}"

        result, input_tokens, output_tokens = self.call_api(refine_prompt)
        
        if result and 'content' in result:
            content = result['content'].strip()
            
            # CSL Interception for bibliography if refined
            if section_type == 'daftar_pustaka':
                import subprocess, os
                try:
                    js_path = os.path.join(os.path.dirname(__file__), 'cite_renderer.js')
                    process = subprocess.Popen(['node', js_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
                    out, err = process.communicate(input=content, timeout=15)
                    if process.returncode == 0 and out.strip(): content = out.strip()
                except: pass

            self.console.print(f"[green][OK] Refinement successful for {section_type}[/green]")
            return content, input_tokens, output_tokens
        else:
            return user_input, 0, 0

    def generate_full_paper(self, metadata: Dict[str, str], context: Dict[str, str], reference_mode: str = "smart", citation_min: int = 5, citation_max: int = 10) -> Dict[str, str]:
        sections = ['kata_pengantar', 'latar_belakang', 'rumusan_masalah', 'tujuan', 'pembahasan', 'kesimpulan', 'daftar_pustaka']
        content = {}

        self.console.print(f"\\n[cyan]Generating full paper with model {self.primary_model}...[/cyan]")
        
        # Use the new multi-stage reference pipeline
        if 'real_journals' not in context:
            candidates, formatted_refs = self.search_references(context, mode=reference_mode, citation_min=citation_min, citation_max=citation_max)
            if formatted_refs:
                context['real_journals'] = formatted_refs
                # Store candidates for structured daftar pustaka
                context['_reference_candidates'] = candidates

            # Check if Zotero produced a formatted APA bibliography
            zotero_apa = self.reference_engine.get_last_apa_bibliography()
            if zotero_apa:
                context['_zotero_apa'] = zotero_apa

        for section in sections:
            self.console.print(f"[dim]  Processing {section.replace('_', ' ').title()}...[/dim]")
            content[section], input_tokens, output_tokens = self.generate_section(section, context)

            if content[section]:
                from src.token_logger import log_usage
                log_usage(f"generate_{section}", input_tokens, output_tokens)
            else:
                self.console.print(f"[yellow][WARNING] {section.replace('_', ' ').title()} kosong, menggunakan placeholder[/yellow]")
                content[section] = f"[{section.replace('_', ' ').title()} akan diisi manual]"

        # If Zotero provided APA bibliography, use it directly for daftar_pustaka
        zotero_apa = context.get('_zotero_apa')
        if zotero_apa:
            self.console.print("[green]📖 Using Zotero-formatted Daftar Pustaka.[/green]")
            content['daftar_pustaka'] = zotero_apa

        return content


def get_ai_engine():
    return AIEngine()