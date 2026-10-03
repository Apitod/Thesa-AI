import copy
import re
import shutil
from pathlib import Path
from typing import Dict, Any, List, Tuple
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT, WD_LINE_SPACING, WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml.ns import qn


class TemplateEngine:
    def __init__(self, templates_dir="templates"):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(parents=True, exist_ok=True)

    def load_template(self, template_name: str) -> Document:
        """Load template. Looks for .docx only."""
        base = template_name.lower().replace(' ', '_')
        docx_path = self.templates_dir / f"{base}.docx"

        if not docx_path.exists():
            raise FileNotFoundError(f"Template tidak ditemukan: {docx_path}")

        return Document(docx_path)

    def find_placeholders(self, document: Document) -> List[str]:
        placeholders = set()
        placeholder_pattern = re.compile(r'\{\{([^}]+)\}\}')

        for paragraph in document.paragraphs:
            matches = placeholder_pattern.findall(paragraph.text)
            placeholders.update(matches)

        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        matches = placeholder_pattern.findall(paragraph.text)
                        placeholders.update(matches)

        return sorted(list(placeholders))

    def _get_run_formatting(self, run):
        """Extract formatting properties from a run for reuse."""
        return {
            'bold': run.bold,
            'italic': run.italic,
            'underline': run.underline,
            'font_name': run.font.name,
            'font_size': run.font.size,
            'font_color': run.font.color.rgb if run.font.color and run.font.color.rgb else None,
        }

    def _apply_run_formatting(self, run, fmt):
        """Apply previously extracted formatting to a run."""
        if fmt.get('bold') is not None:
            run.bold = fmt['bold']
        if fmt.get('italic') is not None:
            run.italic = fmt['italic']
        if fmt.get('underline') is not None:
            run.underline = fmt['underline']
        if fmt.get('font_name'):
            run.font.name = fmt['font_name']
        if fmt.get('font_size'):
            run.font.size = fmt['font_size']
        if fmt.get('font_color'):
            run.font.color.rgb = fmt['font_color']

    def _get_paragraph_formatting(self, paragraph):
        """Extract formatting properties from a paragraph."""
        pf = paragraph.paragraph_format
        return {
            'alignment': pf.alignment,
            'line_spacing': pf.line_spacing,
            'space_before': pf.space_before,
            'space_after': pf.space_after,
            'first_line_indent': pf.first_line_indent,
            'left_indent': pf.left_indent,
            'right_indent': pf.right_indent,
        }

    def _apply_paragraph_formatting(self, paragraph, fmt):
        """Apply previously extracted formatting to a paragraph."""
        pf = paragraph.paragraph_format
        if fmt.get('alignment') is not None:
            pf.alignment = fmt['alignment']
        if fmt.get('line_spacing') is not None:
            pf.line_spacing = fmt['line_spacing']
        if fmt.get('space_before') is not None:
            pf.space_before = fmt['space_before']
        if fmt.get('space_after') is not None:
            pf.space_after = fmt['space_after']
        if fmt.get('first_line_indent') is not None:
            pf.first_line_indent = fmt['first_line_indent']
        if fmt.get('left_indent') is not None:
            pf.left_indent = fmt['left_indent']
        if fmt.get('right_indent') is not None:
            pf.right_indent = fmt['right_indent']

    def _is_content_section(self, placeholder_name: str) -> bool:
        """Check if this placeholder is a long-content section that needs multi-paragraph support.
        Uses strict matching to avoid leaking into TOC placeholders (di_...).
        """
        content_sections = {
            'latar_belakang', 'rumusan_masalah', 'tujuan',
            'pembahasan', 'kesimpulan', 'abstrak',
            'kata_pengantar', 'daftar_pustaka', 'isi'
        }
        name = placeholder_name.lower().strip()
        # MUST be an exact match to avoid 'di_rumusan_masalah' matching 'rumusan_masalah'
        return name in content_sections

    def _replace_in_paragraph(self, paragraph, placeholder_pattern, data, replacement_status, parent_element=None):
        """Replace placeholders in a single paragraph, handling multi-paragraph content properly."""
        full_text = paragraph.text
        matches = list(placeholder_pattern.finditer(full_text))

        if not matches:
            return

        for match in matches:
            placeholder = match.group(1)
            replacement_text = data.get(placeholder)

            # If placeholder isn't in data at all, skip it
            if replacement_text is None:
                replacement_status[placeholder] = False
                continue

            replacement_status[placeholder] = True
            
            # Treat None as empty string just in case
            replacement_text = "" if replacement_text is None else str(replacement_text)

            # For long content sections, we need multi-paragraph handling
            if self._is_content_section(placeholder) and '\n' in replacement_text:
                self._replace_with_multi_paragraph(
                    paragraph, match.group(0), replacement_text, parent_element
                )
            else:
                # Simple single-line replacement that preserves formatting
                is_body = any(p in placeholder.lower() for p in ["isi", "latar_belakang", "rumusan_masalah", "tujuan", "kesimpulan", "abstrak", "kata_pengantar"])
                
                # TOC Entries (di_...) should NOT be forced to normal, to keep their template bold/italic
                if placeholder.lower().startswith("di_"):
                    is_body = False
                
                # If it's NOT body content, it might be a Heading.
                # FORCE LEFT ALIGNMENT for TOC entries to prevent "Giant Spaces" from Justification
                if placeholder.lower().startswith("di_"):
                    # Use Left Alignment (Native Tab Stops will move the page number to the right)
                    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    
                    # Professional Formatting: Add a Right Tab Stop at 16 cm (A4 width) with Dot Leader
                    # First, clear existing tab stops to avoid duplicates
                    paragraph.paragraph_format.tab_stops.clear_all()
                    
                    # Add the magical Right Tab for the Page Number
                    paragraph.paragraph_format.tab_stops.add_tab_stop(Cm(16), alignment=WD_TAB_ALIGNMENT.RIGHT, leader=WD_TAB_LEADER.DOTS)
                    
                    # Menghilangkan spasi tambahan (Tetap 2.0 sesuai permintaan)
                    paragraph.paragraph_format.line_spacing = 2.0
                    paragraph.paragraph_format.space_after = Pt(0)
                    paragraph.paragraph_format.space_before = Pt(0)
                    
                    # LOGIKA KHUSUS BAB II: WAJIB 1 BARIS
                    if placeholder.lower() == "di_bab_2":
                        # Hapus indentasi untuk judul utama agar muat dalam satu baris
                        paragraph.paragraph_format.left_indent = Pt(0)
                        paragraph.paragraph_format.first_line_indent = Pt(0)
                    else:
                        # Add a Hanging Indent so wrapped lines are indented beautifully (untuk sub-bab)
                        # Menggunakan 0.45cm sesuai permintaan agar teks panjang tetap rapi di bawahnya
                        paragraph.paragraph_format.left_indent = Cm(0.45)
                        paragraph.paragraph_format.first_line_indent = Cm(-0.45)
                    
                    # Memastikan teks Daftar Isi tidak di-bold
                    for run in paragraph.runs:
                        run.bold = False
                
                self._replace_preserving_format(paragraph, match.group(0), replacement_text, is_body)
                
                # Perbaikan Terakhir: Hapus titik-titik sisa yang ada setelah angka halaman di template
                if placeholder.lower().startswith("di_"):
                    found_placeholder = False
                    for run in paragraph.runs:
                        # Jika run ini mengandung teks pengganti (yang sudah ada angka halamannya)
                        if replacement_text in run.text:
                            found_placeholder = True
                            # Pastikan tidak ada titik sisa di akhir teks halaman
                            run.text = run.text.rstrip('. ')
                            continue
                            # Jika sudah melewati teks pengganti, kosongkan semua run setelahnya
                        if found_placeholder:
                            run.text = ""
                
                # If paragraph consists only of whitespace after replacement, remove it
                if not paragraph.text.strip():
                    p = paragraph._element
                    p.getparent().remove(p)
                    # Breaking here because paragraph is deleted, going to next match won't work on this para
                    break

    def _replace_preserving_format(self, paragraph, placeholder_str, replacement_text, force_normal=False):
        """Replace placeholder text while preserving the run's formatting."""
        for run in paragraph.runs:
            if placeholder_str in run.text:
                run.text = run.text.replace(placeholder_str, replacement_text)
                if force_normal:
                    run.bold = False
                    run.italic = False
                return

        # Fallback: if placeholder spans multiple runs, reassemble
        if placeholder_str in paragraph.text:
            # Get formatting from first run
            fmt = None
            if paragraph.runs:
                fmt = self._get_run_formatting(paragraph.runs[0])

            old_text = paragraph.text
            
            # Split the text to preserve the prefix (like "C. Tujuan Penelitian ") and suffix
            try:
                prefix, suffix = old_text.split(placeholder_str, 1)
            except ValueError:
                prefix, suffix = "", ""
                
            # Clear all runs
            for run in paragraph.runs:
                run.text = ''

            # Rebuild the paragraph with careful formatting chunks
            if prefix:
                r_pref = paragraph.add_run(prefix)
                if fmt: self._apply_run_formatting(r_pref, fmt)
            
            r_repl = paragraph.add_run(replacement_text)
            if fmt: self._apply_run_formatting(r_repl, fmt)
            if force_normal:
                r_repl.bold = False
                r_repl.italic = False
                
            if suffix:
                r_suff = paragraph.add_run(suffix)
                if fmt: self._apply_run_formatting(r_suff, fmt)

                # Surgically exclude from TOC without destroying numbering/style
                pass

            # Let headings and body content inherit formatting from the template
            merged_text = "".join(r.text for r in paragraph.runs).strip()
            # Enforce body paragraphs to align with the provided image
            if any(placeholder_str.startswith(prefix) for prefix in ["{{isi", "{{kesimpulan", "{{latar_belakang"]):
                # Alignment: Justified
                paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                # Indentation: Left 0.75 cm, Special: First Line 1.27 cm
                paragraph.paragraph_format.left_indent = Cm(0.75)
                paragraph.paragraph_format.first_line_indent = Cm(1.27)
                # Spacing: Before 12 pt, After 0 pt
                paragraph.paragraph_format.space_before = Pt(12)
                paragraph.paragraph_format.space_after = Pt(0)
                # Line spacing: 1.5 lines
                paragraph.paragraph_format.line_spacing = 1.5



    def _replace_with_multi_paragraph(self, paragraph, placeholder_str, replacement_text, parent_element=None):
        """Replace a placeholder with multi-paragraph content.
        
        Splits the replacement text by newlines and creates proper paragraphs
        in the DOCX document, preserving the original paragraph's formatting.
        """
        # Get the formatting to apply to new paragraphs
        para_fmt = self._get_paragraph_formatting(paragraph)
        run_fmt = None
        if paragraph.runs:
            run_fmt = self._get_run_formatting(paragraph.runs[0])
            # Only force normal if it's a body content section (not a heading)
            is_body = any(p in placeholder_str.lower() for p in ["isi", "latar_belakang", "rumusan_masalah", "tujuan", "kesimpulan", "abstrak", "kata_pengantar"])
            if is_body:
                run_fmt['bold'] = False
                run_fmt['italic'] = False
        
        # Force font to Cambria as per user requirement, and standard size 12
        if run_fmt is None:
            run_fmt = {
                'bold': False, 'italic': False, 'underline': False,
                'font_name': 'Cambria', 'font_size': Pt(12),
                'font_color': None,
            }
        else:
            run_fmt['font_name'] = 'Cambria'
        if not run_fmt.get('font_size'):
            run_fmt['font_size'] = Pt(12)

        # Split text into lines; empty lines are skipped in the loop below
        lines = replacement_text.split('\n')

        # Determine the parent element to insert after
        if parent_element is None:
            parent_element = paragraph._element.getparent()

        # Find the index of this paragraph in the parent
        para_index = None
        for i, child in enumerate(parent_element):
            if child is paragraph._element:
                para_index = i
                break

        if para_index is None:
            # Fallback: just set text directly
            self._replace_preserving_format(paragraph, placeholder_str, replacement_text.replace('\n', ' '))
            return

        # Use the first paragraph block to replace into the current paragraph
        first_line = lines[0] if lines else ''

        # Clear the current paragraph
        for run in paragraph.runs:
            run.text = ''
        if paragraph.runs:
            paragraph.runs[0].text = first_line
            self._apply_run_formatting(paragraph.runs[0], run_fmt)
        else:
            new_run = paragraph.add_run(first_line)
            self._apply_run_formatting(new_run, run_fmt)


        # Set body text formatting for the first paragraph
        paragraph.paragraph_format.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
        
        # Surgically exclude from TOC without destroying numbering/style
        pass
        # Set explicit 1.5 line spacing, but preserve template indents
        paragraph.paragraph_format.line_spacing = 1.5
        paragraph.paragraph_format.space_before = Pt(12)  # 'Add Space Before Paragraph' natively
        paragraph.paragraph_format.space_after = Pt(0)

        # Smart indent: regular paragraphs get first-line indent, numbered items don't
        if 'daftar_pustaka' in placeholder_str:
            paragraph.paragraph_format.left_indent = Cm(1.27)
            paragraph.paragraph_format.first_line_indent = Cm(-1.27)
            paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
            paragraph.paragraph_format.space_before = Pt(12)
            paragraph.paragraph_format.space_after = Pt(0)
            # Ensure no page break is forced on the first entry
            paragraph.paragraph_format.page_break_before = False
            paragraph.paragraph_format.keep_with_next = False
        elif self._is_numbered_item(first_line):
            paragraph.paragraph_format.first_line_indent = Pt(-18)
            paragraph.paragraph_format.left_indent = Pt(36)
            paragraph.paragraph_format.space_after = Pt(2)
        elif self._is_sub_numbered_item(first_line):
            paragraph.paragraph_format.first_line_indent = Pt(-18)
            paragraph.paragraph_format.left_indent = Pt(72)
            paragraph.paragraph_format.space_after = Pt(2)
        elif self._is_lettered_item(first_line):
            if paragraph.runs:
                paragraph.runs[0].bold = True
            # Allow template formatting to take over for lettered headings

        elif self._is_sub_heading(first_line):
            if paragraph.runs:
                paragraph.runs[0].bold = True
            paragraph.paragraph_format.first_line_indent = None
            paragraph.paragraph_format.space_before = Pt(6)
            paragraph.paragraph_format.space_after = Pt(3)
        else:
            # Regular body paragraph — inherit from template style
            paragraph.paragraph_format.first_line_indent = Pt(36)
            paragraph.paragraph_format.left_indent = Cm(0)
            
            # Application of specific image settings for main sections
            if any(placeholder_str.startswith(prefix) for prefix in ["{{isi", "{{kesimpulan", "{{latar_belakang"]):
                paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                paragraph.paragraph_format.left_indent = Cm(0.75)
                paragraph.paragraph_format.first_line_indent = Cm(1.27)
                paragraph.paragraph_format.space_before = Pt(12)
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 1.5

        # Insert remaining lines as new paragraphs after the current one
        from docx.oxml.ns import qn
        from lxml import etree

        insert_index = para_index + 1
        prev_was_empty = False  # Track consecutive empty lines

        for line_text in lines[1:]:
            stripped = line_text.strip()

            if not stripped:
                continue  # Skip empty lines completely to avoid extra gaps (Indonesian standard)

            # Create new paragraph element
            new_para_element = copy.deepcopy(paragraph._element)
            # Clear all runs in the new element
            for r in new_para_element.findall(qn('w:r')):
                new_para_element.remove(r)
            # Clear paragraph properties to start fresh
            pPr = new_para_element.find(qn('w:pPr'))
            if pPr is not None:
                # Remove ALL properties that can force page breaks or column breaks
                for bad_prop in [
                    'pageBreakBefore', 'keepLines', 'keepNext',
                    'widowControl', 'sectPr', 'framePr',
                ]:
                    elem = pPr.find(qn(f'w:{bad_prop}'))
                    if elem is not None:
                        pPr.remove(elem)

            # Insert in document
            parent_element.insert(insert_index, new_para_element)

            # Get the paragraph object from the document
            from docx.text.paragraph import Paragraph
            new_paragraph = Paragraph(new_para_element, paragraph._parent)

            # Prevent explicit page break inheritance via format override
            new_paragraph.paragraph_format.page_break_before = False
            new_paragraph.paragraph_format.keep_with_next = False

            new_run = new_paragraph.add_run(stripped)
            self._apply_run_formatting(new_run, run_fmt)

            # Base paragraph formatting
            new_paragraph.paragraph_format.line_spacing = 1.5
            new_paragraph.paragraph_format.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY
            new_paragraph.paragraph_format.space_before = Pt(12)
            new_paragraph.paragraph_format.space_after = Pt(0)

            # Check if this line looks like a sub-heading → override indent/spacing
            if self._is_sub_heading(stripped):
                new_run.bold = True
                new_paragraph.paragraph_format.first_line_indent = None
                new_paragraph.paragraph_format.left_indent = None
                new_paragraph.paragraph_format.space_before = Pt(6)
                # Mark as level 2 for TOC detection if it doesn't have lettered prefix
                pass

            # Special case for daftar_pustaka
            if 'daftar_pustaka' in placeholder_str:
                new_paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                new_paragraph.paragraph_format.left_indent = Cm(1.27)
                new_paragraph.paragraph_format.first_line_indent = Cm(-1.27)
                new_paragraph.paragraph_format.space_before = Pt(12)
                new_paragraph.paragraph_format.space_after = Pt(0)
                new_paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
                continue
            
            # Check if this line is an uppercase letter list item (A. B. C.)
            elif self._is_lettered_item(stripped):
                try:
                    new_paragraph.style = 'List Number 2'
                    stripped_text = re.sub(r'^[A-Z][\.\)]\s*', '', stripped)
                    new_run.text = stripped_text
                    new_run.bold = True
                    new_paragraph.paragraph_format.first_line_indent = None
                    new_paragraph.paragraph_format.left_indent = None
                except KeyError:
                    new_run.bold = True
                    new_paragraph.paragraph_format.first_line_indent = Pt(-18)
                    new_paragraph.paragraph_format.left_indent = Pt(36)
                new_paragraph.paragraph_format.space_before = Pt(2)
                new_paragraph.paragraph_format.space_after = Pt(2)

            # Check if this line is a main numbered item (1. 2. 3.)
            elif self._is_numbered_item(stripped):
                try:
                    new_paragraph.style = 'List Number'
                    stripped_text = re.sub(r'^\d+[\.\)]\s*', '', stripped)
                    new_run.text = stripped_text
                    new_paragraph.paragraph_format.first_line_indent = None
                    new_paragraph.paragraph_format.left_indent = None
                except KeyError:
                    new_paragraph.paragraph_format.first_line_indent = Pt(-18)
                    new_paragraph.paragraph_format.left_indent = Pt(36)
                new_paragraph.paragraph_format.space_before = Pt(2)
                new_paragraph.paragraph_format.space_after = Pt(2)

            # Check if this line is a sub-numbered item (a. b. c.)
            elif self._is_sub_numbered_item(stripped):
                new_paragraph.paragraph_format.first_line_indent = Pt(-18)
                new_paragraph.paragraph_format.left_indent = Pt(72)
                new_paragraph.paragraph_format.space_before = Pt(1)
                new_paragraph.paragraph_format.space_after = Pt(1)

            # Regular body paragraph — inherit from template style
            else:
                new_paragraph.paragraph_format.first_line_indent = Pt(36)
                
                # Application of specific image settings for main sections
                if any(placeholder_str.startswith(prefix) for prefix in ["{{isi", "{{kesimpulan", "{{latar_belakang"]):
                    new_paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    new_paragraph.paragraph_format.left_indent = Cm(0.75)
                    new_paragraph.paragraph_format.first_line_indent = Cm(1.27)
                    new_paragraph.paragraph_format.space_before = Pt(12)
                    new_paragraph.paragraph_format.space_after = Pt(0)
                    new_paragraph.paragraph_format.line_spacing = 1.5

            insert_index += 1

    def _is_sub_heading(self, text: str) -> bool:
        """Detect if a line of text looks like a sub-heading.
        
        Sub-headings are typically short, don't end with a period,
        and don't start with numbers or letters followed by a period.
        """
        if not text or len(text) > 80:
            return False
        if text.endswith('.') or text.endswith(':') or text.endswith('?'):
            return False
        if re.match(r'^\d+[\.\)]', text):
            return False
        if re.match(r'^[a-zA-Z][\.\)]', text):
            return False
        # Short line without punctuation at end = likely a heading
        words = text.split()
        if 2 <= len(words) <= 10 and not any(c in text for c in [',', ';']):
            return True
        return False

    def _is_numbered_item(self, text: str) -> bool:
        """Check if a line looks like a main numbered list item (1. 2. 3.)."""
        return bool(re.match(r'^\d+[\.)\:]\s', text))

    def _is_sub_numbered_item(self, text: str) -> bool:
        """Check if a line looks like a sub-numbered item (a. b. c.)."""
        return bool(re.match(r'^[a-z][\.)\:]\s', text))

    def _is_lettered_item(self, text: str) -> bool:
        """Check if a line looks like an uppercase lettered item (A. B. C.)."""
        return bool(re.match(r'^[A-Z][\.\)]\s', text))

    def replace_placeholders(self, document: Document, data: Dict[str, str]) -> Tuple[Document, Dict[str, bool]]:
        replacement_status = {}
        placeholder_pattern = re.compile(r'\{\{([^}]+)\}\}')

        for paragraph in document.paragraphs:
            if placeholder_pattern.search(paragraph.text):
                parent = paragraph._element.getparent()
                self._replace_in_paragraph(paragraph, placeholder_pattern, data, replacement_status, parent)

        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        if placeholder_pattern.search(paragraph.text):
                            parent = paragraph._element.getparent()
                            self._replace_in_paragraph(paragraph, placeholder_pattern, data, replacement_status, parent)

        # Remove forced page-break from heading immediately before {{daftar_pustaka}}
        # so references start on a new page ONLY when the previous page is truly full
        paragraphs = list(document.paragraphs)
        for idx, para in enumerate(paragraphs):
            if '{{daftar_pustaka}}' in para.text or 'daftar_pustaka' in para.text.lower():
                # Look at the preceding ~3 paragraphs for a heading with page_break_before
                for back in range(1, 4):
                    if idx - back >= 0:
                        prev_para = paragraphs[idx - back]
                        ppf = prev_para.paragraph_format
                        if ppf.page_break_before:
                            ppf.page_break_before = False
                        # Also strip via XML to be thorough
                        pPr = prev_para._element.find(qn('w:pPr'))
                        if pPr is not None:
                            pb = pPr.find(qn('w:pageBreakBefore'))
                            if pb is not None:
                                pPr.remove(pb)
                break

        return document, replacement_status

    def validate_template(self, document: Document) -> bool:
        try:
            placeholders = self.find_placeholders(document)
            return True
        except Exception as e:
            print(f"Error validating template: {e}")
            return False

    def clone_template(self, original_path: Path, output_path: Path) -> Document:
        shutil.copy2(original_path, output_path)
        return Document(output_path)

    def apply_formatting(self, document: Document):
        font_name = "Times New Roman"
        font_size = Pt(12)
        line_spacing = 1.5

        for paragraph in document.paragraphs:
            text_upper = paragraph.text.strip().upper()
            if text_upper.startswith("BAB ") or text_upper.startswith("DAFTAR PUSTAKA") or text_upper.startswith("KATA PENGANTAR"):
                # Always add page break before main chapters
                paragraph.paragraph_format.page_break_before = True

            for run in paragraph.runs:
                if run.font.name is None:
                    run.font.name = font_name
                if run.font.size is None:
                    run.font.size = font_size

            paragraph.paragraph_format.line_spacing = line_spacing
            paragraph.paragraph_format.space_after = Pt(12)

        for table in document.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            if run.font.name is None:
                                run.font.name = font_name
                            if run.font.size is None:
                                run.font.size = font_size

                        paragraph.paragraph_format.line_spacing = line_spacing
                        paragraph.paragraph_format.space_after = Pt(12)

    def get_template_list(self) -> List[str]:
        templates = []
        for file in self.templates_dir.glob("*.docx"):
            template_name = file.stem.replace('_', ' ').title()
            templates.append(template_name)
        return templates


def get_template_engine(templates_dir="templates"):
    return TemplateEngine(templates_dir)