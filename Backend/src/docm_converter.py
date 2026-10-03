"""
docm_converter.py

Pipeline:
  1. Inject vbaProject.bin from the original .docm template into the generated .docx
     (fixing Content-Types and relationship references so Word accepts it as .docm).
  2. Open the resulting .docm headlessly via win32com.
     Word fires the Document_Open() VBA macro → TOC is updated automatically.
  3. Save as clean .docx (wdFormatDocumentDefault=16) and delete the interim .docm.
"""

import os
import shutil
import time
import zipfile


# ─── Content-type and relationship constants ──────────────────────────────────
_VBA_CONTENT_TYPE = "application/vnd.ms-office.vbaProject"
_DOCM_MAIN_CT = (
    "application/vnd.ms-word.document.macroEnabled.main+xml"
)
_DOCX_MAIN_CT = (
    "application/vnd.openxmlformats-officedocument"
    ".wordprocessingml.document.main+xml"
)
_VBA_REL_TYPE = (
    "http://schemas.microsoft.com/office/2006/relationships/vbaProject"
)
_VBA_REL_ENTRY = (
    '<Relationship Id="rIdVBA" '
    f'Type="{_VBA_REL_TYPE}" '
    'Target="vbaProject.bin"/>'
)


# ─── Step 1: inject VBA ───────────────────────────────────────────────────────

def inject_vba_from_template(docx_path: str, template_docm_path: str) -> str:
    """Copy vbaProject.bin from *template_docm_path* into *docx_path*.

    Patches [Content_Types].xml and word/_rels/document.xml.rels so that
    Microsoft Word accepts the resulting file as a proper macro-enabled document.
    Returns the path to the new *.docm* file (the original *.docx* is deleted).
    """
    # Extract vbaProject.bin from the template
    with zipfile.ZipFile(template_docm_path, "r") as tmpl:
        try:
            vba_bin = tmpl.read("word/vbaProject.bin")
        except KeyError as exc:
            raise ValueError(
                f"Template '{template_docm_path}' does not contain "
                "word/vbaProject.bin — save it as .docm with a macro first."
            ) from exc

    docm_path = os.path.splitext(docx_path)[0] + ".docm"
    tmp_path = docm_path + ".building"

    with zipfile.ZipFile(docx_path, "r") as src:
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as dst:
            for info in src.infolist():
                data = src.read(info.filename)

                # ── patch [Content_Types].xml ─────────────────────────────
                if info.filename == "[Content_Types].xml":
                    text = data.decode("utf-8")
                    # Swap document content-type to macro-enabled variant
                    text = text.replace(_DOCX_MAIN_CT, _DOCM_MAIN_CT)
                    # Add vbaProject.bin content-type override if missing
                    if "vbaProject" not in text:
                        text = text.replace(
                            "</Types>",
                            f'<Override PartName="/word/vbaProject.bin" '
                            f'ContentType="{_VBA_CONTENT_TYPE}"/></Types>',
                        )
                    data = text.encode("utf-8")

                # ── patch word/_rels/document.xml.rels ───────────────────
                elif info.filename == "word/_rels/document.xml.rels":
                    text = data.decode("utf-8")
                    if "vbaProject" not in text:
                        text = text.replace(
                            "</Relationships>",
                            _VBA_REL_ENTRY + "</Relationships>",
                        )
                    data = text.encode("utf-8")

                dst.writestr(info, data)

            # Inject the VBA binary
            dst.writestr("word/vbaProject.bin", vba_bin)

    # Swap files
    os.remove(docx_path)
    os.replace(tmp_path, docm_path)
    return docm_path


# ─── Step 2 + 3: open in Word, update TOC, export .docx ─────────────────────

def convert_docm_to_docx(docm_path: str) -> str:
    """Open *docm_path* invisibly in Word (VBA fires → TOC updates),
    then export as *.docx*.  The *.docm* is deleted.  Returns the *.docx* path.

    Requires: Microsoft Word installed  +  pip install pywin32
    """
    try:
        import win32com.client
    except ImportError as exc:
        raise RuntimeError(
            "pywin32 tidak terinstall. Jalankan: pip install pywin32"
        ) from exc

    docm_abs = os.path.abspath(docm_path)
    docx_path = os.path.splitext(docm_abs)[0] + ".docx"

    word = win32com.client.Dispatch("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0          # wdAlertsNone

    try:
        doc = word.Documents.Open(
            docm_abs,
            ReadOnly=False,
            AddToRecentFiles=False,
            PasswordDocument="",
        )
        # Give VBA Document_Open() time to finish
        time.sleep(2)

        # wdFormatDocumentDefault = 16  →  .docx
        doc.SaveAs2(docx_path, FileFormat=16)
        doc.Close(SaveChanges=False)
    finally:
        word.Quit()

    # Clean up the interim .docm
    try:
        os.remove(docm_abs)
    except OSError:
        pass

    return docx_path
