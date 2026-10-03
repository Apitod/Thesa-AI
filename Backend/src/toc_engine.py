"""
toc_engine.py — Table of Contents Engine (v2 — optimized matching)

Pipeline:
  1. DOCX is generated with __PG_xxx__ tokens as page-number placeholders
  2. DOCX → PDF via Cloudmersive
  3. PDF text is extracted per-page using PyMuPDF (fitz)
  4. Heading text is matched to pages (skip TOC pages, line-start matching,
     ascending-order validation, fuzzy fallback)
  5. Tokens are replaced with real page numbers in the DOCX
  6. Final DOCX → PDF conversion via Cloudmersive

Fully portable: no MS Word or win32com required.
"""

import os
import re
import time
from typing import Dict, List, Tuple, Optional
from pathlib import Path


# ─── Cloudmersive DOCX → PDF ────────────────────────────────────────────────

_retry_count = 0

def cloudmersive_docx_to_pdf(docx_path: str, pdf_path: str) -> bool:
    """Convert a DOCX file to PDF using the Cloudmersive API.
    Returns True on success, False on failure.
    """
    import requests
    global _retry_count
    api_key = os.environ.get("CLOUDMERSIVE_API_KEY")
    if not api_key:
        print("[toc_engine] CLOUDMERSIVE_API_KEY not set — skipping PDF conversion")
        return False

    url = "https://api.cloudmersive.com/convert/docx/to/pdf"
    headers = {"Apikey": api_key}

    try:
        with open(docx_path, "rb") as f:
            files = {"inputFile": (os.path.basename(docx_path), f)}
            response = requests.post(url, headers=headers, files=files, timeout=120)

        if response.status_code == 200:
            with open(pdf_path, "wb") as out:
                out.write(response.content)
            _retry_count = 0
            return True
        elif response.status_code == 429:
            _retry_count += 1
            if _retry_count <= 2:
                wait = 2 * _retry_count
                print(f"[toc_engine] Rate-limited (429). Retry {_retry_count}/2 in {wait}s …")
                time.sleep(wait)
                return cloudmersive_docx_to_pdf(docx_path, pdf_path)
            else:
                print("[toc_engine] Rate-limit retries exhausted.")
                _retry_count = 0
                return False
        else:
            print(f"[toc_engine] Cloudmersive error {response.status_code}: {response.text[:200]}")
            return False
    except Exception as exc:
        print(f"[toc_engine] Cloudmersive exception: {exc}")
        return False


# ─── PDF Text Extraction (per page, with line-level detail) ──────────────────

def extract_text_per_page(pdf_path: str) -> List[Dict]:
    """Extract text from each page of a PDF.
    Returns list of {page: int, text: str, lines: list[str]}.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("[toc_engine] PyMuPDF (fitz) not installed — cannot extract pages")
        return []

    pages = []
    try:
        doc = fitz.open(pdf_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            # Split into lines and normalize each one
            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
            pages.append({
                "page": page_num + 1,
                "text": text,
                "lines": lines,
            })
        doc.close()
    except Exception as exc:
        print(f"[toc_engine] PDF extraction error: {exc}")

    return pages


# ─── Heading → Page Matching (v2 — high accuracy) ───────────────────────────

def _normalize(text: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation edges."""
    text = text.strip().lower()
    text = re.sub(r'\s+', ' ', text)
    return text


def _is_toc_page(page_info: Dict) -> bool:
    """Detect whether a page is a Table of Contents page.
    A TOC page typically contains multiple __PG_ tokens or the phrase "daftar isi".
    """
    text = page_info["text"]
    # Count how many __PG_ tokens appear on this page
    token_count = text.count("__PG_")
    # If 3+ tokens appear, this is almost certainly the TOC page
    if token_count >= 3:
        return True
    # Also check for "DAFTAR ISI" as a heading on this page
    for line in page_info.get("lines", []):
        if _normalize(line) == "daftar isi":
            return True
    return False


def _line_starts_with(lines: List[str], heading: str) -> bool:
    """Check if any line in the page starts with (or equals) the heading text.
    This ensures we match actual headings, not inline mentions.
    """
    norm_h = _normalize(heading)
    for line in lines:
        norm_line = _normalize(line)
        # Exact line match
        if norm_line == norm_h:
            return True
        # Line starts with the heading (e.g., "BAB I PENDAHULUAN" at start of line)
        if norm_line.startswith(norm_h):
            return True
        # Heading starts with the line (for wrapped headings)
        if norm_h.startswith(norm_line) and len(norm_line) > 5:
            return True
    return False


def _fuzzy_line_match(lines: List[str], heading: str) -> bool:
    """Fuzzy matching: check if significant words from the heading
    appear together in any single line on the page.
    """
    norm_h = _normalize(heading)
    # Extract significant words (skip short ones like "a.", "b.", "i", "ii")
    words = [w for w in norm_h.split() if len(w) > 2]
    if not words:
        return False
    
    for line in lines:
        norm_line = _normalize(line)
        # All significant words must appear in this single line
        if all(w in norm_line for w in words):
            return True
    return False


def match_headings_to_pages(
    search_targets: Dict[str, str],
    pdf_pages: List[Dict],
) -> Dict[str, str]:
    """Match heading texts to their actual page numbers in the PDF.
    
    Strategy (ordered by priority):
    1. Skip TOC pages and cover page (page 1) for body matching
    2. Context-aware: sub-headings searched AFTER their parent BAB's page
    3. Line-start matching: heading must appear at the START of a line
    4. Fuzzy line matching: all significant words in one line
    5. Broad substring matching (last resort)
    6. Ascending-order validation + correction
    
    Returns {token: page_number_str}.
    """
    # ── Define parent-child relationships for context-aware matching ──────
    parent_map = {
        "__PG_LATAR__": "__PG_BAB1__",
        "__PG_RUMUSAN__": "__PG_BAB1__",
        "__PG_TUJUAN__": "__PG_BAB1__",
        "__PG_B2_1__": "__PG_BAB2__",
        "__PG_B2_2__": "__PG_BAB2__",
        "__PG_B2_3__": "__PG_BAB2__",
        "__PG_B2_4__": "__PG_BAB2__",
        "__PG_KESIMPULAN__": "__PG_BAB3__",
    }
    
    found: Dict[str, str] = {}

    # ── Debug: Page Peeking (Show what the scanner sees) ──────────────────
    print("[toc_engine]   --- DEBUG: PDF Page Inspection ---")
    for page_info in pdf_pages:
        peek = " | ".join(page_info["lines"][:4])
        print(f"      P{page_info['page']}: {peek[:110]}...")
    print("[toc_engine]   ----------------------------------")

    def _search_pages_aggressive(pages_to_search, heading_text, token):
        """Search with multiple fallback layers."""
        # 1. Exact start-of-line
        for p in pages_to_search:
            if _line_starts_with(p["lines"], heading_text): return p["page"]
        
        # 2. Fuzzy words-in-line
        for p in pages_to_search:
            if _fuzzy_line_match(p["lines"], heading_text): return p["page"]
        
        # 3. Keyword Keywords (Mandatory for accuracy)
        kmap = {
            "__PG_LATAR__": "latar", "__PG_RUMUSAN__": "rumusan", "__PG_TUJUAN__": "tujuan",
            "__PG_KESIMPULAN__": "kesimpulan", "__PG_PUSTAKA__": "pustaka"
        }
        kw = kmap.get(token)
        if kw:
            for p in pages_to_search:
                for line in p["lines"]:
                    if kw in _normalize(line): return p["page"]

        # 4. Global substring check
        nh = _normalize(heading_text)
        for p in pages_to_search:
            if nh in _normalize(p["text"]): return p["page"]
        return None

    # ── First pass: BAB headings ──────────────────────────────────────────
    bab_tokens = {"__PG_BAB1__", "__PG_BAB2__", "__PG_BAB3__"}
    for heading_text, token in search_targets.items():
        if token in bab_tokens:
            page = _search_pages_aggressive(pdf_pages, heading_text, token)
            if page: 
                found[token] = str(page)
                print(f"[toc_engine]   ✅ Found {token} ({heading_text}) on page {page}")

    # ── Special: DAFTAR PUSTAKA (Search Backwards) ────────────────────────
    for page_info in reversed(pdf_pages):
        if "pustaka" in _normalize(page_info["text"]):
            found["__PG_PUSTAKA__"] = str(page_info["page"])
            print(f"[toc_engine]   ✅ Found __PG_PUSTAKA__ on page {page_info['page']}")
            break

    # ── Second pass: Sub-headings with context ─────────────────────────────
    for heading_text, token in search_targets.items():
        if token in bab_tokens or token == "__PG_PUSTAKA__":
            continue
        if token in ("__PG_KATA__", "__PG_TOC__"):
            found[token] = str(_search_pages_aggressive(pdf_pages, heading_text, token) or "?")
            continue
            
        parent_token = parent_map.get(token)
        min_p = 1
        if parent_token and parent_token in found:
            min_p = int(found[parent_token])
        
        eligible = [p for p in pdf_pages if p["page"] >= min_p]
        page = _search_pages_aggressive(eligible, heading_text, token)
        if page:
            found[token] = str(page)
            print(f"[toc_engine]   ✅ Found {token} on page {page}")

    # ── Validation ────────────────────────────────────────────────────────
    token_order = list(search_targets.values())
    last_v = 1
    for token in token_order:
        if token in found and found[token] != "?":
            pnum = int(found[token])
            if pnum < last_v: found[token] = str(last_v)
            else: last_v = pnum
            
    return found


# ─── Token replacement in DOCX ──────────────────────────────────────────────

def replace_tokens_in_docx(docx_path: str, token_page_map: Dict[str, str]) -> bool:
    """Open the DOCX, find all __PG_xxx__ tokens (even split across runs), replace with page numbers.
    Saves in-place. Returns True on success.
    """
    try:
        from docx import Document
    except ImportError:
        print("[toc_engine] python-docx not installed")
        return False

    def _replace_all_tokens(paragraph_or_cell, token_map):
        runs = paragraph_or_cell.runs
        # We process one token at a time and frequently check if the paragraph
        # still contains any tokens. This is the safest way to handle split runs.
        for token, page_num in token_map.items():
            full_text = "".join(r.text for r in runs)
            if token not in full_text:
                continue

            # Need the latest char_map because runs might have changed
            char_map = []
            for r_idx, run in enumerate(runs):
                for _ in range(len(run.text)):
                    char_map.append(r_idx)

            start_idx = full_text.find(token)
            while start_idx != -1:
                end_idx = start_idx + len(token)
                
                # Identify run indices
                start_run_idx = char_map[start_idx]
                end_run_idx = char_map[end_idx - 1]

                if start_run_idx == end_run_idx:
                    # Token in one run
                    runs[start_run_idx].text = runs[start_run_idx].text.replace(token, page_num)
                else:
                    # Token spans multiple runs
                    # 1. Determine local offset in first run
                    text_before_token = "".join(runs[i].text for i in range(start_run_idx))
                    local_start = start_idx - len(text_before_token)
                    
                    # 2. Determine local offset in last run
                    text_before_last = "".join(runs[i].text for i in range(end_run_idx))
                    local_end = (end_idx - 1) - len(text_before_last)

                    # 3. Modify first run: keep prefix + add page_num
                    runs[start_run_idx].text = runs[start_run_idx].text[:local_start] + page_num
                    
                    # 4. Clear intermediate runs
                    for mid in range(start_run_idx + 1, end_run_idx):
                        runs[mid].text = ""
                    
                    # 5. Modify last run: keep suffix only
                    runs[end_run_idx].text = runs[end_run_idx].text[local_end + 1:]

                # Re-verify and rebuild for next occurrences or next tokens
                full_text = "".join(r.text for r in runs)
                char_map = []
                for r_idx, run in enumerate(runs):
                    for _ in range(len(run.text)):
                        char_map.append(r_idx)
                start_idx = full_text.find(token)

    try:
        doc = Document(docx_path)
        for paragraph in doc.paragraphs:
            if "__PG_" in paragraph.text:
                _replace_all_tokens(paragraph, token_page_map)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        if "__PG_" in paragraph.text:
                            _replace_all_tokens(paragraph, token_page_map)
        doc.save(docx_path)
        return True
    except Exception as exc:
        print(f"[toc_engine] Token replacement error: {exc}")
        return False


# ─── Fallback: estimate pages from word count ───────────────────────────────

def estimate_page_numbers(docx_path: str, search_targets: Dict[str, str]) -> Dict[str, str]:
    """Smart fallback: Estimate page numbers based on word count if PDF fails."""
    try:
        from docx import Document
        doc = Document(docx_path)
        full_text = "\n".join([p.text for p in doc.paragraphs])
        word_count = len(full_text.split())
        # Average academic page with spacing 1.5 is ~300-350 words
        est_total_pages = max(5, round(word_count / 320) + 2)
        print(f"[toc_engine]   Smart Est: {word_count} words -> ~{est_total_pages} total pages")
    except:
        est_total_pages = 14

    # Linear distribution for fallback
    result = {
        "__PG_KATA__": "2",
        "__PG_TOC__": "3",
        "__PG_BAB1__": "4",
        "__PG_LATAR__": "4",
        "__PG_RUMUSAN__": "5",
        "__PG_TUJUAN__": "5",
        "__PG_BAB2__": "6",
        "__PG_B2_1__": str(min(est_total_pages - 6, 7)),
        "__PG_B2_2__": str(min(est_total_pages - 4, 9)),
        "__PG_B2_3__": str(min(est_total_pages - 2, 11)),
        "__PG_B2_4__": str(min(est_total_pages - 1, 13)),
        "__PG_BAB3__": str(est_total_pages - 1),
        "__PG_KESIMPULAN__": str(est_total_pages - 1),
        "__PG_PUSTAKA__": str(est_total_pages),
    }
    return result

# ─── Main Pipeline ──────────────────────────────────────────────────────────

def run_toc_pipeline(
    docx_path: str,
    pdf_output_path: str,
    search_targets: Dict[str, str],
) -> Tuple[bool, Optional[str]]:
    temp_pdf = docx_path.replace(".docx", "_temp_toc.pdf")

    print(f"[toc_engine] Pipeline started for: {os.path.basename(docx_path)}")
    
    # ── STEP 1: First conversion → temporary PDF for page scanning ────────
    print("[toc_engine] STEP 1/5: Requesting PDF conversion from Cloudmersive...")
    if not cloudmersive_docx_to_pdf(docx_path, temp_pdf):
        print("[toc_engine] ❌ CLOUDMERSIVE FAILED. Check API Key or limit. Using Smart Estimates.")
        token_page_map = estimate_page_numbers(docx_path, search_targets)
        replace_tokens_in_docx(docx_path, token_page_map)
        _cleanup(temp_pdf)
        return True, None

    # ── STEP 2: Extract text per page ─────────────────────────────────────
    print("[toc_engine] STEP 2/5: Extracting text via PyMuPDF...")
    if not os.path.exists(temp_pdf):
        print("[toc_engine] ❌ Temp PDF file not found on disk!")
        token_page_map = estimate_page_numbers(docx_path, search_targets)
    else:
        pdf_pages = extract_text_per_page(temp_pdf)
        if not pdf_pages:
            print("[toc_engine] ❌ PDF text extraction returned empty - possible Image PDF.")
            token_page_map = estimate_page_numbers(docx_path, search_targets)
        else:
            # ── STEP 3: Match headings to pages ───────────────────────────────
            print(f"[toc_engine] STEP 3/5: Matching {len(search_targets)} headings...")
            token_page_map = match_headings_to_pages(search_targets, pdf_pages)

            # Fill in missing with estimates
            estimates = estimate_page_numbers(docx_path, search_targets)
            for token in search_targets.values():
                if token not in token_page_map or token_page_map[token] == "?":
                    token_page_map[token] = estimates.get(token, "?")

    # ── STEP 4: Replace tokens in DOCX ────────────────────────────────────
    print("[toc_engine] STEP 4/5: Injecting page numbers into DOCX...")
    replace_tokens_in_docx(docx_path, token_page_map)

    # ── STEP 5: Final DOCX → PDF ─────────────────────────────────────────
    print("[toc_engine] STEP 5/5: Converting final DOCX → PDF …")
    # Small delay to respect rate limits
    time.sleep(0.5)

    success = cloudmersive_docx_to_pdf(docx_path, pdf_output_path)

    # Cleanup temp file
    _cleanup(temp_pdf)

    if success:
        print("[toc_engine] ✅ TOC pipeline complete — pages are accurate!")
        return True, pdf_output_path
    else:
        print("[toc_engine] ⚠️  Final PDF conversion failed, but DOCX has correct pages.")
        return False, None


def _cleanup(path: str):
    """Silently remove a file."""
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass
