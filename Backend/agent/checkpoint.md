# NeoMakalah Status Checkpoint

**Last updated**: 2026-04-20
**Current Version**: Stable (Post-CSL Integration)

## 🚀 Project Overview
NeoMakalah is an automated academic paper generator. It uses **Next.js** for the frontend and **Python (python-docx)** with **Node.js (citation-js)** for document generation.

## 🛠️ System State
- **Core Engine**: `src/template_engine.py` (Handles replacement, formatting, and TOC logic).
- **Citations**: `src/cite_renderer.js` + `src/ai_engine.py` (Uses BibTeX -> CSL APA 7th).
- **Bridge**: `python_web_bridge.py` (Connects Next.js to the generator).

## ✅ Recent Progress & Fixes
- **Data Mapping Success ({{isi1}}-{{isi4}})**: 
    - Updated `document_builder.py` to merge sub-chapter paragraphs into single blocks.
    - **Confirmed**: Placeholders are now filled correctly in the template.
- **Isi Pembahasan Formatting**: 
    - **Confirmed**: Left Indent (0.75 cm), First Line Indent (0.75 cm), and Exactly 24pt line spacing are fully implemented and verified "Sukses".
- **Surgical TOC Exclusion**: Confirmed working.

## 💬 Discussion History & Decisions
- **Issue**: Placeholders `{{isi1}}` were returning empty.
    - *Decision*: Mapped entire sub-chapter content to single-key placeholders for better template flexibility. [SUKSES]
- **Indentation Refinement**:
    - *Isi/Body*: Successfully synced with Gambar 3 (0.75cm/0.75cm). 
    - *Headings A-D*: Still under iterative testing (Special: none vs Hanging vs First-line). **NOT YET LOGGED AS FINAL**.

## 📌 Pending Tasks
- [ ] Finalize and verify Heading A-D formatting (current: Left 0cm, Special: none).
- [ ] Integration with SERPAPI for automatic journal searching.
- **Indonesian Academic Formatting**:
    - **Sections (A, B, C)**: Header items preserve their original style.
    - **Body Content**: Left Indent (0.75 cm), First Line (1.25 cm) applied to `latar_belakang`, `isi/pembahasan`, and `kesimpulan`.
    - **Line Spacing**: Exactly 24 pt (or 1.5 for references).
- **Split Logic**: 
    - `daftar_pustaka`: Split by single `\n`.
    - `body_text`: Split by `\n\n`.

## ⚠️ Important Notes for Successor AI
- **Style Preservation**: NEVER use `paragraph.style = 'Normal'` on content that might have custom numbering. Use `self._exclude_from_toc(paragraph)` instead.
- **Custom Styles**: The template uses a specific hierarchy: `1BAB`, `2Subbab`, `3Paragraf`, `4Anak Subbab`, etc. These must be preserved for visual consistency and numbering.
- **Indentation**: Body paragraphs (non-headings) in main sections must be forced to Left Indent 0.75cm to align with local academic standards.
- **Placeholder Names**: Placeholders containing "isi", "tujuan", "rumusan", "kesimpulan", or "latar_belakang" are treated as body content and will be surgically removed from the TOC.

## 📌 Pending Tasks
- [ ] Integration with SERPAPI for automatic journal searching.
- [ ] UI refinement for citation style selection.
