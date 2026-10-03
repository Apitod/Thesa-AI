"""
fewshot_cache.py — Few-Shot Learning Cache for NeoMakalah

Stores successful generation examples and retrieves the most relevant ones
for use as few-shot examples in prompts. This reduces token usage by
replacing verbose instructions with concrete examples.

Storage: data/fewshot_cache/<section_type>/ with JSON files.
Matching: TF-IDF-like keyword overlap scoring.
"""

import json
import os
import re
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class FewShotExample:
    """A single cached example of a successful generation."""

    def __init__(
        self,
        section: str,
        keywords: List[str],
        judul: str,
        mata_kuliah: str,
        output_text: str,
        timestamp: float = 0,
        quality_score: float = 1.0,
        use_count: int = 0,
    ):
        self.section = section
        self.keywords = keywords
        self.judul = judul
        self.mata_kuliah = mata_kuliah
        self.output_text = output_text
        self.timestamp = timestamp or time.time()
        self.quality_score = quality_score
        self.use_count = use_count

    def to_dict(self) -> dict:
        return {
            "section": self.section,
            "keywords": self.keywords,
            "judul": self.judul,
            "mata_kuliah": self.mata_kuliah,
            "output_text": self.output_text,
            "timestamp": self.timestamp,
            "quality_score": self.quality_score,
            "use_count": self.use_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FewShotExample":
        return cls(**data)


class FewShotCache:
    """Manages storage and retrieval of few-shot examples."""

    # Max examples to keep per section (prevents unbounded growth)
    MAX_EXAMPLES_PER_SECTION = 50
    # Max words to store from output (truncate very long outputs)
    MAX_OUTPUT_WORDS = 400
    # Sections that benefit from few-shot learning
    CACHEABLE_SECTIONS = [
        "latar_belakang",
        "rumusan_masalah",
        "tujuan",
        "pembahasan",
        "kesimpulan",
        "kata_pengantar",
    ]

    def __init__(self, cache_dir: str = "data/fewshot_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, List[FewShotExample]] = {}
        self._load_all()

    def _section_path(self, section: str) -> Path:
        return self.cache_dir / f"{section}.json"

    def _load_all(self):
        """Load all cached examples from disk."""
        for section in self.CACHEABLE_SECTIONS:
            path = self._section_path(section)
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._cache[section] = [FewShotExample.from_dict(d) for d in data]
                except (json.JSONDecodeError, KeyError):
                    self._cache[section] = []
            else:
                self._cache[section] = []

    def _save_section(self, section: str):
        """Write a single section's examples to disk."""
        path = self._section_path(section)
        data = [ex.to_dict() for ex in self._cache.get(section, [])]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ── Keyword Extraction ───────────────────────────────────────────────

    @staticmethod
    def extract_keywords(judul: str, mata_kuliah: str = "") -> List[str]:
        """Extract significant keywords from title and course name."""
        text = f"{judul} {mata_kuliah}".lower()
        # Remove common Indonesian stop words
        stop_words = {
            "dan", "atau", "yang", "di", "ke", "dari", "untuk", "dengan",
            "pada", "dalam", "adalah", "ini", "itu", "oleh", "serta",
            "makalah", "tentang", "mengenai", "sebuah", "suatu", "terhadap",
            "sebagai", "akan", "dapat", "telah", "sudah", "juga", "tidak",
            "bagi", "secara", "melalui", "antara", "atas", "karena",
        }
        # Split and filter
        words = re.findall(r"[a-z]{3,}", text)
        keywords = [w for w in words if w not in stop_words]
        # Deduplicate while preserving order
        seen = set()
        unique = []
        for w in keywords:
            if w not in seen:
                seen.add(w)
                unique.append(w)
        return unique[:10]  # Max 10 keywords

    # ── Similarity Scoring ───────────────────────────────────────────────

    @staticmethod
    def _similarity(keywords_a: List[str], keywords_b: List[str]) -> float:
        """Compute keyword overlap similarity (0.0 to 1.0)."""
        if not keywords_a or not keywords_b:
            return 0.0
        set_a = set(keywords_a)
        set_b = set(keywords_b)
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union) if union else 0.0

    # ── Save Example ─────────────────────────────────────────────────────

    def save_example(
        self,
        section: str,
        judul: str,
        mata_kuliah: str,
        output_text: str,
        quality_score: float = 1.0,
    ):
        """Save a successful generation as a few-shot example.

        Called after a successful paper generation.
        """
        if section not in self.CACHEABLE_SECTIONS:
            return
        if not output_text or len(output_text.strip()) < 50:
            return  # Too short to be useful

        keywords = self.extract_keywords(judul, mata_kuliah)
        if not keywords:
            return

        # Truncate output to save space
        words = output_text.split()
        if len(words) > self.MAX_OUTPUT_WORDS:
            output_text = " ".join(words[: self.MAX_OUTPUT_WORDS]) + "..."

        # Check for near-duplicates (same keywords + same judul)
        existing = self._cache.get(section, [])
        for ex in existing:
            if self._similarity(ex.keywords, keywords) > 0.85 and ex.judul.lower() == judul.lower():
                # Update existing instead of adding duplicate
                ex.output_text = output_text
                ex.quality_score = max(ex.quality_score, quality_score)
                ex.timestamp = time.time()
                self._save_section(section)
                return

        # Add new example
        example = FewShotExample(
            section=section,
            keywords=keywords,
            judul=judul,
            mata_kuliah=mata_kuliah,
            output_text=output_text,
            quality_score=quality_score,
        )
        existing.append(example)

        # Prune if too many (remove lowest quality / oldest)
        if len(existing) > self.MAX_EXAMPLES_PER_SECTION:
            existing.sort(key=lambda e: (e.quality_score, e.timestamp), reverse=True)
            existing = existing[: self.MAX_EXAMPLES_PER_SECTION]

        self._cache[section] = existing
        self._save_section(section)

    # ── Retrieve Best Examples ──────────────────────────────────────────

    def find_similar(
        self,
        section: str,
        judul: str,
        mata_kuliah: str = "",
        top_k: int = 1,
        min_similarity: float = 0.15,
    ) -> List[FewShotExample]:
        """Find the most relevant cached examples for a given topic.

        Args:
            section: Which section we're generating
            judul: Title of the current paper
            mata_kuliah: Course name
            top_k: How many examples to return (1-2 recommended)
            min_similarity: Minimum keyword overlap to consider

        Returns:
            List of FewShotExample, sorted by relevance (best first)
        """
        if section not in self.CACHEABLE_SECTIONS:
            return []

        query_keywords = self.extract_keywords(judul, mata_kuliah)
        if not query_keywords:
            return []

        candidates = self._cache.get(section, [])
        if not candidates:
            return []

        # Score each candidate
        scored = []
        for ex in candidates:
            sim = self._similarity(query_keywords, ex.keywords)
            if sim >= min_similarity:
                # Composite score: similarity * quality * recency_bonus
                recency = min(1.0, 0.5 + 0.5 * (1.0 / (1.0 + (time.time() - ex.timestamp) / 86400)))
                score = sim * ex.quality_score * recency
                scored.append((score, ex))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)

        # Return top_k
        results = [ex for _, ex in scored[:top_k]]

        # Increment use counts
        for ex in results:
            ex.use_count += 1
        if results:
            self._save_section(section)

        return results

    # ── Build Few-Shot Prompt Block ──────────────────────────────────────

    def build_fewshot_block(
        self,
        section: str,
        judul: str,
        mata_kuliah: str = "",
    ) -> str:
        """Build a few-shot example block to inject into the prompt.

        Returns empty string if no relevant examples are found,
        so it can be safely concatenated without wasting tokens.
        """
        examples = self.find_similar(section, judul, mata_kuliah, top_k=1)
        if not examples:
            return ""

        ex = examples[0]

        # Truncate example output for prompt efficiency (max ~200 words)
        output_words = ex.output_text.split()
        if len(output_words) > 200:
            truncated = " ".join(output_words[:200]) + " [... lanjutan dipotong]"
        else:
            truncated = ex.output_text

        block = f"""
CONTOH REFERENSI (dari makalah serupa yang sudah berhasil sebelumnya):
---
Judul: "{ex.judul}"
Mata Kuliah: {ex.mata_kuliah}

Contoh Output:
{truncated}
---
Tulis output Anda dengan gaya, panjang, dan struktur yang SERUPA dengan contoh di atas, tetapi dengan konten yang sesuai topik baru.
"""
        return block.strip()

    # ── Batch Save (after successful generation) ─────────────────────────

    def save_generation(
        self,
        judul: str,
        mata_kuliah: str,
        content: Dict[str, str],
        quality_score: float = 1.0,
    ):
        """Save all sections from a successful generation at once.

        Called from python_web_bridge.py after a paper is successfully generated.
        """
        saved_count = 0
        for section in self.CACHEABLE_SECTIONS:
            text = content.get(section, "")
            if text and len(text.strip()) > 50:
                self.save_example(section, judul, mata_kuliah, text, quality_score)
                saved_count += 1
        return saved_count

    # ── Stats ────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, int]:
        """Return count of cached examples per section."""
        return {section: len(examples) for section, examples in self._cache.items()}


# ── Module-level singleton ───────────────────────────────────────────────────

_instance: Optional[FewShotCache] = None


def get_fewshot_cache() -> FewShotCache:
    global _instance
    if _instance is None:
        _instance = FewShotCache()
    return _instance
