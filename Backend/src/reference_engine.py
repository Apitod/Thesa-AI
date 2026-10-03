"""
reference_engine.py

Pipeline referensi akademik multi-tahap:
  Keyword Generation → SerpApi Discovery → Candidate Filtering →
  Elsevier Validation → Scoring → Zotero Sync → Final Reference List

Mode operasi:
  - fast   ("Normal")    : SerpApi only, 3 referensi, tanpa validasi
  - smart  ("Disarankan"): SerpApi + Elsevier selective, 3-5 referensi
  - strict ("Terbaik")   : SerpApi + Elsevier wajib valid, min 3 referensi
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

# ──────────────────────────────────────────────────────────────────────────────
# Data structures
# ──────────────────────────────────────────────────────────────────────────────

class ReferenceCandidate:
    """A single journal/article candidate from SerpApi."""

    def __init__(
        self,
        title: str,
        authors: str = "",
        year: str = "",
        source: str = "",
        link: str = "",
        snippet: str = "",
        doi: str = "",
        **kwargs
    ):
        self.title = title
        # Allow 'author' as an alias for 'authors' from cache
        self.authors = authors if authors else kwargs.get("author", "")
        self.year = str(year)
        self.source = source
        self.link = link
        self.snippet = snippet
        self.doi = doi
        self.score: float = float(kwargs.get("score", 0.0))
        self.elsevier_validated: bool = bool(kwargs.get("validated", False))
        self.elsevier_metadata: Optional[Dict] = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "author": self.authors,
            "year": self.year,
            "source": self.source,
            "link": self.link,
            "doi": self.doi,
            "validated": self.elsevier_validated,
            "score": round(self.score, 3),
        }

    def to_apa(self) -> str:
        """Format as APA-style citation string."""
        author_part = self.authors if self.authors else "Unknown Author"
        year_part = f"({self.year})" if self.year else "(n.d.)"
        title_part = self.title
        source_part = f". {self.source}" if self.source else ""
        doi_part = f". https://doi.org/{self.doi}" if self.doi else ""
        return f"{author_part} {year_part}. {title_part}{source_part}{doi_part}."


# ──────────────────────────────────────────────────────────────────────────────
# Cache system
# ──────────────────────────────────────────────────────────────────────────────

class ReferenceCache:
    """File-based JSON cache for reference search results."""

    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / "references.json"
        self._data: Dict = self._load()

    def _load(self) -> Dict:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save(self):
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _make_key(keywords: List[str], mode: str) -> str:
        raw = f"{','.join(sorted(keywords))}|{mode}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, keywords: List[str], mode: str, max_age_hours: int = 24) -> Optional[List[dict]]:
        key = self._make_key(keywords, mode)
        entry = self._data.get(key)
        if not entry:
            return None
        cached_at = datetime.fromisoformat(entry["cached_at"])
        if datetime.now() - cached_at > timedelta(hours=max_age_hours):
            return None  # Expired
        return entry["references"]

    def put(self, keywords: List[str], mode: str, references: List[dict]):
        key = self._make_key(keywords, mode)
        self._data[key] = {
            "keywords": keywords,
            "mode": mode,
            "cached_at": datetime.now().isoformat(),
            "references": references,
        }
        self._save()


# ──────────────────────────────────────────────────────────────────────────────
# Rate limiter
# ──────────────────────────────────────────────────────────────────────────────

class RateLimiter:
    """Simple rate limiter with configurable min interval."""

    def __init__(self, min_interval: float = 0.5):
        self.min_interval = min_interval
        self._last_call: float = 0

    def wait(self):
        elapsed = time.time() - self._last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call = time.time()


# ──────────────────────────────────────────────────────────────────────────────
# Main engine
# ──────────────────────────────────────────────────────────────────────────────

class ReferenceEngine:
    """Multi-stage academic reference pipeline."""

    # Internal mode names
    MODE_FAST = "fast"
    MODE_SMART = "smart"
    MODE_STRICT = "strict"

    # User-facing labels → internal
    LABEL_MAP = {
        "Normal": MODE_FAST,
        "Disarankan": MODE_SMART,
        "Terbaik": MODE_STRICT,
    }

    def __init__(self):
        self.console = Console()
        self.serpapi_key = os.getenv("SERPAPI_KEY", "")
        self.elsevier_key = os.getenv("ELSEVIER_API_KEY", "")
        self.openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        self.openrouter_url = os.getenv("OPENROUTER_API_URL", "")
        self.primary_model = os.getenv("PRIMARY_MODEL", "qwen/qwen2.5-7b-instruct-free")
        self.default_mode = os.getenv("REFERENCE_MODE", self.MODE_SMART)

        self.cache = ReferenceCache()
        self.elsevier_limiter = RateLimiter(min_interval=0.5)  # max 2 req/s

        # Zotero integration
        from src.zotero_engine import get_zotero_engine
        self.zotero = get_zotero_engine()

    # ── helpers ─────────────────────────────────────────────────────────────

    @classmethod
    def resolve_mode(cls, label_or_mode: str) -> str:
        """Accept either user-facing label or internal mode name."""
        return cls.LABEL_MAP.get(label_or_mode, label_or_mode)

    # ── 1. Keyword generator (AI) ──────────────────────────────────────────

    def generate_keywords(self, judul: str, mata_kuliah: str = "") -> List[str]:
        """Use AI to produce 3-5 English academic keywords from the paper title."""
        if not self.openrouter_key or not self.openrouter_url:
            # Fallback: simple split
            return self._fallback_keywords(judul, mata_kuliah)

        prompt = (
            "You are an academic keyword generator. "
            "Given a paper title and subject, generate exactly 5 concise academic search keywords in English. "
            "Each keyword should be a short phrase (2-5 words), suitable for Google Scholar. "
            "Output ONLY the keywords, one per line, nothing else.\n\n"
            f"Paper title: {judul}\n"
            f"Subject: {mata_kuliah}\n"
        )

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.openrouter_key}",
                "HTTP-Referer": "https://openrouter.ai",
            }
            payload = {
                "model": self.primary_model,
                "messages": [
                    {"role": "system", "content": "You output only plain text keywords, one per line. No numbering, no markdown."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 200,
            }
            resp = requests.post(self.openrouter_url, headers=headers, json=payload, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                keywords = [
                    line.strip().lstrip("0123456789.-) ")
                    for line in content.strip().splitlines()
                    if line.strip() and len(line.strip()) > 3
                ]
                if keywords:
                    self.console.print(f"[green]Keywords generated: {keywords}[/green]")
                    return keywords[:5]
        except Exception as e:
            self.console.print(f"[yellow]Keyword generation failed: {e}[/yellow]")

        return self._fallback_keywords(judul, mata_kuliah)

    @staticmethod
    def _fallback_keywords(judul: str, mata_kuliah: str) -> List[str]:
        """Simple keyword extraction without AI."""
        stop_words = {"dan", "di", "ke", "dari", "untuk", "yang", "dengan", "dalam", "pada", "adalah", "ini", "itu", "atau", "the", "of", "in", "and", "a", "an", "to"}
        words = re.sub(r'[^\w\s]', '', f"{judul} {mata_kuliah}").lower().split()
        unique = list(dict.fromkeys(w for w in words if w not in stop_words and len(w) > 2))
        # Combine into 2-3 word phrases
        keywords = []
        for i in range(0, min(len(unique), 10), 2):
            phrase = " ".join(unique[i:i+2])
            if phrase.strip():
                keywords.append(phrase)
        return keywords[:5] if keywords else [judul[:50]]

    # ── 2. SerpApi Discovery ────────────────────────────────────────────────

    def search_serpapi(self, keywords: List[str], num_results: int = 15) -> List[ReferenceCandidate]:
        """Search Google Scholar via SerpApi."""
        if not self.serpapi_key:
            self.console.print("[yellow]SerpApi key not configured, skipping search.[/yellow]")
            return []

        query = " ".join(keywords)
        self.console.print(f"[cyan]🔍 Searching Google Scholar: \"{query}\"...[/cyan]")

        try:
            params = {
                "engine": "google_scholar",
                "q": query,
                "api_key": self.serpapi_key,
                "hl": "en",
                "num": num_results,
            }
            resp = requests.get("https://serpapi.com/search", params=params, timeout=20)
            if resp.status_code != 200:
                self.console.print(f"[red]SerpApi error: {resp.status_code}[/red]")
                return []

            data = resp.json()
            results = data.get("organic_results", [])
            candidates = []

            for res in results:
                title = res.get("title", "").strip()
                if not title:
                    continue
                # Clean ellipsis from Google Scholar
                title = re.sub(r'\.\.\.|\u2026', '', title).strip()

                # Extract publication info
                pub_info = res.get("publication_info", {})
                summary = pub_info.get("summary", "")
                authors = ""
                year = ""
                source = ""

                # Parse summary: typically "Author1, Author2 - Journal, Year"
                if summary:
                    # Clean ellipsis from summary string before parsing
                    summary = re.sub(r'\.\.\.|\u2026', '', summary)
                    parts = summary.split(" - ")
                    if len(parts) >= 2:
                        authors = parts[0].strip()
                        rest = parts[1]
                        # Extract year (4-digit number)
                        year_match = re.search(r'\b(19|20)\d{2}\b', rest)
                        if year_match:
                            year = year_match.group()
                            source = rest.replace(year, "").strip(" ,.-")
                        else:
                            source = rest.strip()
                    elif len(parts) == 1:
                        authors = parts[0].strip()

                link = res.get("link", "")
                snippet = res.get("snippet", "")

                candidate = ReferenceCandidate(
                    title=title,
                    authors=authors,
                    year=year,
                    source=source,
                    link=link,
                    snippet=snippet,
                )
                candidates.append(candidate)

            self.console.print(f"[green]Found {len(candidates)} raw results from Google Scholar.[/green]")
            return candidates

        except Exception as e:
            self.console.print(f"[red]SerpApi search error: {e}[/red]")
            return []

    # ── 3. Candidate Filtering ──────────────────────────────────────────────

    def filter_candidates(self, candidates: List[ReferenceCandidate], max_age_years: int = 10) -> List[ReferenceCandidate]:
        """Remove candidates without year, too old, or obviously non-academic."""
        current_year = datetime.now().year
        filtered = []

        for c in candidates:
            # Must have a title
            if not c.title or len(c.title) < 10:
                continue

            # Filter by year if available
            if c.year:
                try:
                    pub_year = int(c.year)
                    if current_year - pub_year > max_age_years:
                        continue
                except ValueError:
                    pass  # Keep candidates with unparseable years

            # Skip obvious non-academic sources
            skip_patterns = ["blog", "wikipedia", "youtube", "slideshare", "scribd", "quora"]
            if any(pat in c.link.lower() for pat in skip_patterns):
                continue

            filtered.append(c)

        self.console.print(f"[cyan]After filtering: {len(filtered)}/{len(candidates)} candidates remain.[/cyan]")
        return filtered

    # ── 4. Candidate Scoring ────────────────────────────────────────────────

    def score_candidates(self, candidates: List[ReferenceCandidate], keywords: List[str]) -> List[ReferenceCandidate]:
        """Score candidates: relevance × 0.5 + recency × 0.3 + title clarity × 0.2"""
        current_year = datetime.now().year
        keyword_lower = [kw.lower() for kw in keywords]

        for c in candidates:
            # Relevance score (0-1): how many keywords appear in title/snippet
            title_lower = c.title.lower()
            snippet_lower = c.snippet.lower() if c.snippet else ""
            combined = f"{title_lower} {snippet_lower}"

            keyword_hits = sum(1 for kw in keyword_lower if kw in combined)
            # Also check individual words
            kw_words = set()
            for kw in keyword_lower:
                kw_words.update(kw.split())
            word_hits = sum(1 for w in kw_words if w in combined)
            relevance = min(1.0, (keyword_hits / max(len(keywords), 1)) * 0.6 + (word_hits / max(len(kw_words), 1)) * 0.4)

            # Recency score (0-1): newer = higher
            recency = 0.5  # default for unknown year
            if c.year:
                try:
                    age = current_year - int(c.year)
                    recency = max(0, min(1, 1 - (age / 15)))  # 0 years → 1.0, 15 years → 0.0
                except ValueError:
                    pass

            # Title quality (0-1): academic-looking title
            quality = 0.5
            if len(c.title.split()) >= 5:
                quality += 0.2
            if c.source:
                quality += 0.2
            if c.authors:
                quality += 0.1
            quality = min(1.0, quality)

            c.score = (relevance * 0.5) + (recency * 0.3) + (quality * 0.2)

        # Sort by score descending
        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates

    # ── 5. Elsevier Validation ──────────────────────────────────────────────

    def validate_with_elsevier(self, candidate: ReferenceCandidate, max_retries: int = 2) -> bool:
        """Validate a candidate against Elsevier's Scopus API."""
        if not self.elsevier_key:
            return False

        self.elsevier_limiter.wait()

        # Search Scopus by title
        search_title = re.sub(r'[^\w\s]', '', candidate.title)[:100]
        url = "https://api.elsevier.com/content/search/scopus"
        params = {
            "query": f'TITLE("{search_title}")',
            "count": 3,
            "apiKey": self.elsevier_key,
        }
        headers = {
            "Accept": "application/json",
            "X-ELS-APIKey": self.elsevier_key,
        }

        for attempt in range(max_retries + 1):
            try:
                resp = requests.get(url, params=params, headers=headers, timeout=10)

                if resp.status_code == 429:
                    # Rate limited – wait and retry
                    wait_time = 2 ** (attempt + 1)
                    self.console.print(f"[yellow]Elsevier 429: waiting {wait_time}s...[/yellow]")
                    time.sleep(wait_time)
                    continue

                if resp.status_code != 200:
                    self.console.print(f"[yellow]Elsevier API: {resp.status_code}[/yellow]")
                    return False

                data = resp.json()
                search_results = data.get("search-results", {})
                entries = search_results.get("entry", [])

                if not entries or (len(entries) == 1 and entries[0].get("@_fa") == "false"):
                    return False

                # Check if any entry is a close title match
                for entry in entries:
                    scopus_title = entry.get("dc:title", "").lower()
                    candidate_title = candidate.title.lower()

                    # Fuzzy match: at least 60% of words overlap
                    scopus_words = set(scopus_title.split())
                    cand_words = set(candidate_title.split())
                    if not scopus_words:
                        continue
                    overlap = len(scopus_words & cand_words) / max(len(scopus_words), len(cand_words))

                    if overlap >= 0.5:
                        # Enrich candidate with Scopus metadata
                        candidate.elsevier_validated = True
                        candidate.elsevier_metadata = {
                            "scopus_id": entry.get("dc:identifier", ""),
                            "eid": entry.get("eid", ""),
                            "cited_by": entry.get("citedby-count", "0"),
                        }

                        # Always update with pristine Scopus data (SerpApi data is often truncated)
                        
                        # Full Title Override
                        if entry.get("dc:title"):
                            candidate.title = entry.get("dc:title").strip()

                        # Update DOI if available
                        doi = entry.get("prism:doi", "")
                        if doi and not candidate.doi:
                            candidate.doi = doi

                        # Update source/journal (always overwrite if exists)
                        pub_name = entry.get("prism:publicationName", "")
                        if pub_name:
                            candidate.source = pub_name.strip()

                        # Update authors (always overwrite if exists)
                        creator = entry.get("dc:creator", "")
                        if creator:
                            candidate.authors = creator.strip()

                        # Update year if available
                        cover_date = entry.get("prism:coverDate", "")
                        if cover_date and not candidate.year:
                            year_match = re.search(r'(19|20)\d{2}', cover_date)
                            if year_match:
                                candidate.year = year_match.group()

                        self.console.print(f"[green]  ✓ Validated: {candidate.title[:60]}...[/green]")
                        return True

                return False

            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    time.sleep(1)
                    continue
                return False
            except Exception as e:
                self.console.print(f"[red]Elsevier error: {e}[/red]")
                return False

        return False

    def validate_candidates(self, candidates: List[ReferenceCandidate], max_validate: int = 5) -> List[ReferenceCandidate]:
        """Validate the top N candidates via Elsevier."""
        if not self.elsevier_key:
            self.console.print("[yellow]Elsevier API key not configured, skipping validation.[/yellow]")
            return candidates

        self.console.print(f"[cyan]📚 Validating top {min(max_validate, len(candidates))} candidates via Elsevier Scopus...[/cyan]")

        for candidate in candidates[:max_validate]:
            self.validate_with_elsevier(candidate)

        validated_count = sum(1 for c in candidates if c.elsevier_validated)
        self.console.print(f"[green]Validation complete: {validated_count}/{min(max_validate, len(candidates))} confirmed in Scopus.[/green]")
        return candidates

    # ── 6. Final Scoring ────────────────────────────────────────────────────

    def final_score(self, candidates: List[ReferenceCandidate]) -> List[ReferenceCandidate]:
        """Apply final scoring: initial + elsevier bonus + doi bonus."""
        for c in candidates:
            bonus = 0.0
            if c.elsevier_validated:
                bonus += 0.3
            if c.doi:
                bonus += 0.2
            c.score = c.score + bonus

        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates

    # ── 7. Main Pipeline ────────────────────────────────────────────────────

    def search_references(
        self,
        judul: str,
        mata_kuliah: str = "",
        mode: str = "smart",
        jurusan: str = "",
        citation_min: int = 5,
        citation_max: int = 10,
    ) -> Tuple[List[ReferenceCandidate], str]:
        """
        Execute the full reference pipeline.

        Args:
            citation_min: Minimum number of references to include
            citation_max: Maximum number of references to include

        Returns:
            (list of ReferenceCandidate, formatted_string_for_prompt)
        """
        mode = self.resolve_mode(mode)
        self.console.print(f"\n[bold cyan]═══ Reference Pipeline (Mode: {mode.upper()}, Target: {citation_min}-{citation_max} refs) ═══[/bold cyan]")

        # Step 1: Generate keywords
        keywords = self.generate_keywords(judul, mata_kuliah)
        if not keywords:
            self.console.print("[red]No keywords generated.[/red]")
            return [], ""

        # Check cache
        cached = self.cache.get(keywords, mode)
        if cached:
            self.console.print(f"[green]📦 Cache hit! Returning {len(cached)} cached references.[/green]")
            candidates = [ReferenceCandidate(**ref) for ref in cached]
            # Re-trim to requested range
            candidates = candidates[:citation_max]
            formatted = self._format_for_prompt(candidates)
            return candidates, formatted

        # Step 2: SerpApi search — fetch more than citation_max to have room for filtering
        num_results = max(citation_max * 2, 20)
        candidates = self.search_serpapi(keywords, num_results=num_results)

        if not candidates:
            # Retry with simplified query
            self.console.print("[yellow]No results. Retrying with simplified keywords...[/yellow]")
            simplified = keywords[:2] if len(keywords) > 2 else keywords
            candidates = self.search_serpapi(simplified, num_results=num_results)

        if not candidates:
            self.console.print("[red]No candidates found after retry.[/red]")
            return [], ""

        # Step 3: Filter
        candidates = self.filter_candidates(candidates)

        # Step 4: Initial scoring
        candidates = self.score_candidates(candidates, keywords)

        # Step 5: Elsevier validation (if applicable)
        if mode in (self.MODE_SMART, self.MODE_STRICT) and self.elsevier_key:
            max_val = min(citation_max, 7) if mode == self.MODE_SMART else min(citation_max + 2, 15)
            candidates = self.validate_candidates(candidates, max_validate=max_val)

            # Step 6: Final scoring with validation bonus
            candidates = self.final_score(candidates)

        # Step 7: Select final references using citation_min/citation_max
        if mode == self.MODE_STRICT:
            # Prioritize validated ones
            validated = [c for c in candidates if c.elsevier_validated]
            unvalidated = [c for c in candidates if not c.elsevier_validated]
            if len(validated) >= citation_min:
                final = validated[:citation_max]
            else:
                # Fill with top unvalidated to meet minimum
                needed = max(0, citation_min - len(validated))
                final = validated + unvalidated[:needed]
                self.console.print(
                    f"[yellow]⚠ Only {len(validated)} validated refs found. "
                    f"Added {needed} unvalidated to meet minimum of {citation_min}.[/yellow]"
                )
        else:
            # smart / fast — take up to citation_max, at least citation_min
            final = candidates[:citation_max]

        # Cache the results
        self.cache.put(keywords, mode, [c.to_dict() for c in final])

        self.console.print(f"[bold green]✅ Final: {len(final)} references selected.[/bold green]")
        for i, ref in enumerate(final, 1):
            v = "✓" if ref.elsevier_validated else "○"
            self.console.print(f"  {v} {i}. [{ref.score:.2f}] {ref.title[:70]}... ({ref.year})")

        # ── Step 8: Zotero Processing ──
        ref_dicts = [c.to_dict() for c in final]
        session_tag = f"neomakalah_{int(time.time())}"

        zotero_formatted, enriched_refs = self.zotero.process_references(
            references=ref_dicts,
            mode=mode,
            session_tag=session_tag,
        )

        # Use Zotero-formatted APA if available, otherwise use prompt format
        if zotero_formatted:
            self.console.print("[green]📖 Using Zotero-formatted APA bibliography.[/green]")
            formatted = self._format_for_prompt(final)
            # Store the APA bibliography for direct use in daftar_pustaka
            self._last_apa_bibliography = zotero_formatted
        else:
            formatted = self._format_for_prompt(final)
            self._last_apa_bibliography = None

        return final, formatted

    # ── Formatting helpers ──────────────────────────────────────────────────

    @staticmethod
    def _format_for_prompt(candidates: List[ReferenceCandidate]) -> str:
        """Format references as a string for AI prompt injection."""
        lines = []
        for c in candidates:
            parts = []
            if c.authors:
                parts.append(c.authors)
            if c.year:
                parts.append(f"({c.year})")
            parts.append(c.title)
            if c.source:
                parts.append(f"- {c.source}")
            if c.doi:
                parts.append(f"[DOI: {c.doi}]")
            lines.append("- " + " ".join(parts))
        return "\n".join(lines)

    @staticmethod
    def format_apa_list(candidates: List[ReferenceCandidate]) -> str:
        """Format references as APA bibliography."""
        return "\n\n".join(c.to_apa() for c in candidates if c.title)

    def get_references_json(self, candidates: List[ReferenceCandidate]) -> dict:
        """Return structured JSON output."""
        return {
            "references": [c.to_dict() for c in candidates],
            "count": len(candidates),
        }

    def get_last_apa_bibliography(self) -> Optional[str]:
        """Get the last Zotero-formatted APA bibliography, if available."""
        return getattr(self, '_last_apa_bibliography', None)


# ── Module-level shortcut ───────────────────────────────────────────────────

def get_reference_engine() -> ReferenceEngine:
    return ReferenceEngine()
