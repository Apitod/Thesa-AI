"""
zotero_engine.py

Integrasi Zotero untuk manajemen referensi akademik:
  - Normalize metadata → format Zotero
  - Batch save ke Zotero API (dengan tagging per session)
  - Fetch formatted bibliography (APA) dari Zotero
  - Fallback ke citation-js jika Zotero gagal

Mode operasi (mengikuti reference_mode):
  - fast   : Tidak pakai Zotero, langsung citation-js
  - smart  : Save ke Zotero + fetch APA
  - strict : Save + reuse referensi lama dari library
"""

import json
import os
import re
import subprocess
import time
from typing import Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()


class ZoteroEngine:
    """Manages Zotero API interactions for reference storage and formatting."""

    def __init__(self):
        self.console = Console()
        self.api_key = os.getenv("ZOTERO_API_KEY", "")
        self.user_id = os.getenv("ZOTERO_USER_ID", "")
        self.base_url = "https://api.zotero.org"

        self.available = bool(
            self.api_key
            and self.api_key != "YOUR_ZOTERO_API_KEY_HERE"
            and self.user_id
        )

        if self.available:
            self.console.print(f"[green]Zotero connected: user {self.user_id}[/green]")
        else:
            self.console.print("[yellow]Zotero not configured. Fallback to citation-js.[/yellow]")

    # ─── Headers ──────────────────────────────────────────────────────────

    @property
    def _headers(self) -> dict:
        return {
            "Zotero-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Zotero-API-Version": "3",
        }

    @property
    def _user_url(self) -> str:
        return f"{self.base_url}/users/{self.user_id}"

    # ─── 1. Metadata Normalizer ───────────────────────────────────────────

    @staticmethod
    def normalize_to_zotero(ref: dict) -> dict:
        """Convert a reference dict to Zotero itemType format.

        Input keys: title, author (str), year, source, doi, link
        Output: Zotero-compatible item dict
        """
        creators = []
        author_str = ref.get("author", "") or ""
        if author_str:
            # Split multiple authors by ", " or " and "
            author_names = re.split(r",\s*|\s+and\s+", author_str)
            for name in author_names:
                name = name.strip()
                if not name:
                    continue
                parts = name.rsplit(" ", 1)
                if len(parts) == 2:
                    creators.append({
                        "creatorType": "author",
                        "firstName": parts[0].strip(),
                        "lastName": parts[1].strip(),
                    })
                else:
                    creators.append({
                        "creatorType": "author",
                        "firstName": "",
                        "lastName": name.strip(),
                    })

        item = {
            "itemType": "journalArticle",
            "title": ref.get("title", ""),
            "creators": creators,
            "date": str(ref.get("year", "")),
            "publicationTitle": ref.get("source", ""),
        }

        doi = ref.get("doi", "")
        if doi:
            item["DOI"] = doi

        url = ref.get("link", "")
        if url:
            item["url"] = url

        return item

    # ─── 2. Zotero Save (Batch) ──────────────────────────────────────────

    def save_references(
        self,
        references: List[dict],
        session_tag: str,
        max_retries: int = 2,
    ) -> Tuple[bool, str]:
        """Batch-save references to Zotero with a session tag.

        Args:
            references: list of reference dicts (from ReferenceCandidate.to_dict())
            session_tag: unique tag like "neomakalah_1714000000"
            max_retries: retry count on failure

        Returns:
            (success: bool, message: str)
        """
        if not self.available:
            return False, "Zotero tidak dikonfigurasi."

        # Normalize all references to Zotero format
        items = []
        for ref in references:
            item = self.normalize_to_zotero(ref)
            # Add session tag for isolation
            item["tags"] = [{"tag": session_tag}]
            items.append(item)

        if not items:
            return False, "Tidak ada referensi untuk disimpan."

        url = f"{self._user_url}/items"

        self.console.print(f"[cyan]📤 Saving {len(items)} references to Zotero (tag: {session_tag})...[/cyan]")

        for attempt in range(max_retries + 1):
            try:
                resp = requests.post(
                    url,
                    headers=self._headers,
                    json=items,
                    timeout=15,
                )

                if resp.status_code in (200, 201):
                    self.console.print(f"[green]✅ {len(items)} references saved to Zotero.[/green]")
                    return True, f"{len(items)} referensi berhasil disimpan."

                elif resp.status_code == 401:
                    self.console.print("[red]Zotero 401: API key salah atau expired.[/red]")
                    return False, "API key Zotero salah."

                elif resp.status_code == 403:
                    self.console.print("[red]Zotero 403: Permission tidak lengkap.[/red]")
                    return False, "Permission Zotero tidak cukup."

                elif resp.status_code == 400:
                    error_detail = resp.text[:200]
                    self.console.print(f"[red]Zotero 400: Format JSON salah: {error_detail}[/red]")
                    return False, f"Format data salah: {error_detail}"

                elif resp.status_code == 429:
                    wait = 2 ** (attempt + 1)
                    self.console.print(f"[yellow]Zotero 429: Rate limited, waiting {wait}s...[/yellow]")
                    time.sleep(wait)
                    continue

                elif resp.status_code >= 500:
                    if attempt < max_retries:
                        self.console.print(f"[yellow]Zotero {resp.status_code}: Server error, retrying...[/yellow]")
                        time.sleep(2)
                        continue
                    return False, f"Zotero server error: {resp.status_code}"

                else:
                    self.console.print(f"[red]Zotero unexpected: {resp.status_code} - {resp.text[:200]}[/red]")
                    return False, f"Error {resp.status_code}"

            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    time.sleep(1)
                    continue
                return False, "Zotero request timeout."

            except Exception as e:
                self.console.print(f"[red]Zotero save error: {e}[/red]")
                return False, str(e)

        return False, "Max retries exceeded."

    # ─── 3. Zotero Fetch (APA Formatted) ──────────────────────────────────

    def fetch_formatted_bibliography(
        self,
        session_tag: str,
        style: str = "apa",
        max_retries: int = 2,
    ) -> Optional[str]:
        """Fetch APA-formatted bibliography from Zotero for a session tag.

        Returns formatted bibliography string or None on failure.
        """
        if not self.available:
            return None

        url = f"{self._user_url}/items"
        params = {
            "tag": session_tag,
            "format": "bib",
            "style": style,
            "sort": "creator",
            "direction": "asc",
        }

        self.console.print(f"[cyan]📖 Fetching APA bibliography from Zotero (tag: {session_tag})...[/cyan]")

        for attempt in range(max_retries + 1):
            try:
                resp = requests.get(
                    url,
                    headers={
                        "Zotero-API-Key": self.api_key,
                        "Zotero-API-Version": "3",
                    },
                    params=params,
                    timeout=15,
                )

                if resp.status_code == 200:
                    bib_text = resp.text.strip()
                    if bib_text:
                        # Clean HTML tags that Zotero sometimes includes
                        bib_text = re.sub(r'<[^>]+>', '', bib_text)
                        # Clean up whitespace
                        bib_text = re.sub(r'\n{3,}', '\n\n', bib_text).strip()

                        line_count = len([l for l in bib_text.split('\n') if l.strip()])
                        self.console.print(f"[green]✅ Fetched {line_count} formatted references from Zotero.[/green]")
                        return bib_text
                    else:
                        self.console.print("[yellow]Zotero returned empty bibliography.[/yellow]")
                        return None

                elif resp.status_code == 429:
                    wait = 2 ** (attempt + 1)
                    time.sleep(wait)
                    continue

                elif resp.status_code >= 500:
                    if attempt < max_retries:
                        time.sleep(2)
                        continue
                    return None

                else:
                    self.console.print(f"[yellow]Zotero fetch error: {resp.status_code}[/yellow]")
                    return None

            except Exception as e:
                self.console.print(f"[red]Zotero fetch error: {e}[/red]")
                if attempt < max_retries:
                    time.sleep(1)
                    continue
                return None

        return None

    # ─── 4. Fetch Reusable References (strict/pro mode) ───────────────────

    def fetch_recent_references(
        self,
        judul: str = "",
        limit: int = 10,
    ) -> List[dict]:
        """Fetch recent NeoMakalah references from Zotero library for reuse.

        Returns list of reference dicts.
        """
        if not self.available:
            return []

        url = f"{self._user_url}/items"
        params = {
            "format": "json",
            "sort": "dateModified",
            "direction": "desc",
            "limit": limit,
            "tag": "neomakalah",  # Only NeoMakalah-tagged items
        }

        try:
            resp = requests.get(
                url,
                headers=self._headers,
                params=params,
                timeout=10,
            )

            if resp.status_code == 200:
                items = resp.json()
                results = []
                for item in items:
                    data = item.get("data", {})
                    if not data.get("title"):
                        continue

                    # Check relevance to current paper
                    title_lower = data.get("title", "").lower()
                    judul_words = set(judul.lower().split()) if judul else set()
                    overlap = len(judul_words & set(title_lower.split())) if judul_words else 0

                    creators = data.get("creators", [])
                    author_str = ", ".join(
                        f"{c.get('firstName', '')} {c.get('lastName', '')}".strip()
                        for c in creators
                    )

                    results.append({
                        "title": data.get("title", ""),
                        "author": author_str,
                        "year": data.get("date", ""),
                        "source": data.get("publicationTitle", ""),
                        "doi": data.get("DOI", ""),
                        "link": data.get("url", ""),
                        "validated": True,  # Already in Zotero = trusted
                        "relevance_overlap": overlap,
                    })

                # Sort by relevance to current paper
                results.sort(key=lambda x: x.get("relevance_overlap", 0), reverse=True)
                self.console.print(f"[green]Found {len(results)} reusable references in Zotero.[/green]")
                return results

        except Exception as e:
            self.console.print(f"[yellow]Zotero fetch recent error: {e}[/yellow]")

        return []

    # ─── 5. Full Pipeline ─────────────────────────────────────────────────

    def process_references(
        self,
        references: List[dict],
        mode: str = "smart",
        session_tag: str = "",
    ) -> Tuple[Optional[str], List[dict]]:
        """Full Zotero pipeline: save → fetch formatted → return.

        Args:
            references: list of reference dicts
            mode: "fast", "smart", or "strict"
            session_tag: unique tag for this generation session

        Returns:
            (formatted_apa_string or None, enriched_references)
        """
        if not session_tag:
            session_tag = f"neomakalah_{int(time.time())}"

        # Add base "neomakalah" tag to all items for reuse filtering
        for ref in references:
            if "tags" not in ref:
                ref["_session_tag"] = session_tag

        # ── FAST MODE: skip Zotero entirely ──
        if mode == "fast" or not self.available:
            self.console.print("[dim]Zotero: skipped (fast mode or not configured).[/dim]")
            formatted = self._fallback_citation_js(references)
            return formatted, references

        # ── SMART MODE: save + fetch APA ──
        if mode == "smart":
            success, msg = self.save_references(references, session_tag)

            if success:
                # Small delay for Zotero to index
                time.sleep(1)
                formatted = self.fetch_formatted_bibliography(session_tag)
                if formatted:
                    return formatted, references

            # Fallback to citation-js
            self.console.print("[yellow]Zotero failed, falling back to citation-js.[/yellow]")
            formatted = self._fallback_citation_js(references)
            return formatted, references

        # ── STRICT MODE: save + reuse old refs ──
        if mode == "strict":
            # First, check for reusable references from library
            judul = references[0].get("title", "") if references else ""
            reusable = self.fetch_recent_references(judul=judul, limit=10)

            # Merge: current validated refs + relevant old refs (avoid duplicates)
            existing_titles = {r.get("title", "").lower() for r in references}
            for old_ref in reusable:
                if old_ref.get("title", "").lower() not in existing_titles:
                    references.append(old_ref)
                    existing_titles.add(old_ref.get("title", "").lower())

            # Save current batch
            success, msg = self.save_references(references, session_tag)

            if success:
                time.sleep(1)
                formatted = self.fetch_formatted_bibliography(session_tag)
                if formatted:
                    return formatted, references

            formatted = self._fallback_citation_js(references)
            return formatted, references

        # Unknown mode — fallback
        formatted = self._fallback_citation_js(references)
        return formatted, references

    # ─── 6. Citation-js Fallback ──────────────────────────────────────────

    def _fallback_citation_js(self, references: List[dict]) -> Optional[str]:
        """Format references using citation-js as fallback when Zotero is unavailable."""
        if not references:
            return None

        # Build BibTeX from reference data
        bibtex_entries = []
        for i, ref in enumerate(references):
            author = ref.get("author", "Unknown")
            key = re.sub(r'\W+', '', author.split(",")[0].split(" ")[-1].lower()) + str(ref.get("year", "2024"))
            entry = f"""@article{{{key}{i},
    title={{{ref.get("title", "")}}},
    author={{{author}}},
    journal={{{ref.get("source", "")}}},
    year={{{ref.get("year", "")}}}"""
            doi = ref.get("doi", "")
            if doi:
                entry += f",\n    doi={{{doi}}}"
            entry += "\n}"
            bibtex_entries.append(entry)

        bibtex_str = "\n\n".join(bibtex_entries)

        try:
            js_path = os.path.join(os.path.dirname(__file__), "cite_renderer.js")
            if not os.path.exists(js_path):
                self.console.print("[yellow]cite_renderer.js not found, using manual format.[/yellow]")
                return self._manual_apa_format(references)

            process = subprocess.Popen(
                ["node", js_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            out, err = process.communicate(input=bibtex_str, timeout=15)

            if process.returncode == 0 and out.strip():
                self.console.print("[green]✅ citation-js formatting successful (fallback).[/green]")
                return out.strip()
            else:
                self.console.print(f"[yellow]citation-js returned empty or error: {err[:200]}[/yellow]")
                return self._manual_apa_format(references)

        except Exception as e:
            self.console.print(f"[yellow]citation-js error: {e}[/yellow]")
            return self._manual_apa_format(references)

    @staticmethod
    def _manual_apa_format(references: List[dict]) -> str:
        """Last-resort manual APA formatting."""
        lines = []
        for ref in references:
            author = ref.get("author", "Unknown")
            year = ref.get("year", "n.d.")
            title = ref.get("title", "")
            source = ref.get("source", "")
            doi = ref.get("doi", "")

            entry = f"{author} ({year}). {title}."
            if source:
                entry += f" {source}."
            if doi:
                entry += f" https://doi.org/{doi}"
            lines.append(entry)

        return "\n\n".join(lines)


# ── Module-level shortcut ────────────────────────────────────────────────────

def get_zotero_engine() -> ZoteroEngine:
    return ZoteroEngine()
