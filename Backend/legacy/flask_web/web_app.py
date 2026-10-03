import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, send_from_directory, url_for

from src.ai_engine import get_ai_engine
from src.document_builder import get_document_builder
from src.template_engine import get_template_engine
from src.token_logger import TokenLogger, get_total_usage


load_dotenv()

app = Flask(__name__, template_folder="web_templates", static_folder="web_static")
app.config["SECRET_KEY"] = os.getenv("WEB_SECRET_KEY", "ganti-secret-key-anda")

OUTPUT_DIR = Path("output").resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SECTION_FIELDS = [
    "abstrak",
    "kata_pengantar",
    "daftar_isi",
    "latar_belakang",
    "rumusan_masalah",
    "tujuan",
    "pembahasan",
    "kesimpulan",
    "daftar_pustaka",
]
AI_SECTIONS = ["latar_belakang", "rumusan_masalah", "tujuan", "pembahasan", "kesimpulan"]
REQUIRED_FIELDS = ["mata_kuliah", "judul", "dosen", "jurusan", "fakultas", "kampus"]

template_engine = get_template_engine()
document_builder = get_document_builder()
ai_engine = get_ai_engine()
token_logger = TokenLogger()


def is_ai_ready() -> bool:
    return bool(getattr(ai_engine, "api_available", False) and getattr(ai_engine, "openrouter_url", None))


def get_template_choices() -> List[str]:
    templates = template_engine.get_template_list()
    return templates or ["Uin Alauddin"]


def default_form_data() -> Dict[str, str]:
    today = datetime.now().strftime("%d %B %Y")
    return {
        "mata_kuliah": "",
        "judul": "",
        "dosen": "",
        "penulis_1": "",
        "nim_penulis_1": "",
        "penulis_2": "",
        "nim_penulis_2": "",
        "jurusan": "",
        "fakultas": "",
        "kampus": "UIN Alauddin Makassar",
        "tahun": str(datetime.now().year),
        "tempat_pembuatan": "Makassar",
        "tanggal_pembuatan": today,
        "generation_mode": "manual",
        "template_name": get_template_choices()[0],
        "ai_latar_belakang": "on",
        "ai_rumusan_masalah": "on",
        "ai_tujuan": "on",
        "ai_pembahasan": "on",
        "ai_kesimpulan": "on",
        "abstrak": "",
        "kata_pengantar": "",
        "daftar_isi": "",
        "latar_belakang": "",
        "rumusan_masalah": "",
        "tujuan": "",
        "pembahasan": "",
        "kesimpulan": "",
        "daftar_pustaka": "",
    }


def build_form_data_from_request() -> Dict[str, str]:
    incoming = default_form_data()
    for key in incoming.keys():
        incoming[key] = request.form.get(key, incoming[key]).strip()
    for section in AI_SECTIONS:
        checkbox = f"ai_{section}"
        incoming[checkbox] = "on" if request.form.get(checkbox) == "on" else ""
    return incoming


def validate_form_data(form_data: Dict[str, str]) -> List[str]:
    errors = []
    for field in REQUIRED_FIELDS:
        if not form_data.get(field, "").strip():
            errors.append(f"Field '{field}' wajib diisi.")
    if not form_data.get("penulis_1", "").strip():
        errors.append("Minimal isi nama penulis pertama.")
    if not form_data.get("nim_penulis_1", "").strip():
        errors.append("Minimal isi NIM penulis pertama.")
    return errors


def collect_metadata(form_data: Dict[str, str]):
    metadata = {
        "mata_kuliah": form_data["mata_kuliah"],
        "judul": form_data["judul"],
        "dosen": form_data["dosen"],
    }
    authors = [
        {"nama": form_data["penulis_1"], "nim": form_data["nim_penulis_1"]},
    ]
    if form_data.get("penulis_2") or form_data.get("nim_penulis_2"):
        authors.append(
            {"nama": form_data.get("penulis_2", ""), "nim": form_data.get("nim_penulis_2", "")}
        )
    institution = {
        "jurusan": form_data["jurusan"],
        "fakultas": form_data["fakultas"],
        "kampus": form_data["kampus"],
        "tahun": form_data.get("tahun", ""),
        "tempat_pembuatan": form_data.get("tempat_pembuatan", ""),
        "tanggal_pembuatan": form_data.get("tanggal_pembuatan", ""),
    }
    return metadata, authors, institution


def manual_content(form_data: Dict[str, str]) -> Dict[str, str]:
    return {section: form_data.get(section, "") for section in SECTION_FIELDS}


def ai_per_section_content(form_data: Dict[str, str], context: Dict[str, str]) -> Dict[str, str]:
    content = manual_content(form_data)
    if not is_ai_ready():
        flash("AI belum siap. Pastikan OPENROUTER_API_URL dan OPENROUTER_API_KEY sudah diatur.", "warning")
        return content

    for section in AI_SECTIONS:
        if form_data.get(f"ai_{section}") == "on":
            generated_text, input_tokens, output_tokens = ai_engine.generate_section(section, context)
            if generated_text:
                content[section] = generated_text
                token_logger.log_usage(f"generate_{section}", input_tokens, output_tokens)
            elif not content[section].strip():
                content[section] = f"[{section.replace('_', ' ').title()} diisi manual]"
    return content


def ai_full_content(form_data: Dict[str, str], context: Dict[str, str]) -> Dict[str, str]:
    content = manual_content(form_data)
    if not is_ai_ready():
        flash("AI belum siap. Pastikan OPENROUTER_API_URL dan OPENROUTER_API_KEY sudah diatur.", "warning")
        return content

    generated = ai_engine.generate_full_paper(context, context)
    content.update(generated)
    return content


@app.route("/", methods=["GET"])
def index():
    return render_template(
        "index.html",
        form_data=default_form_data(),
        template_choices=get_template_choices(),
        ai_ready=is_ai_ready(),
    )


@app.route("/generate", methods=["POST"])
def generate():
    form_data = build_form_data_from_request()
    errors = validate_form_data(form_data)
    if errors:
        for error in errors:
            flash(error, "danger")
        return render_template(
            "index.html",
            form_data=form_data,
            template_choices=get_template_choices(),
            ai_ready=is_ai_ready(),
        )

    metadata, authors, institution = collect_metadata(form_data)
    context = {**metadata, **institution}
    mode = form_data.get("generation_mode", "manual")

    if mode == "ai_full":
        content = ai_full_content(form_data, context)
    elif mode == "ai_per_bab":
        content = ai_per_section_content(form_data, context)
    else:
        content = manual_content(form_data)

    complete_data = document_builder.build_complete_paper_data(metadata, authors, institution, content)
    template_name = form_data.get("template_name", get_template_choices()[0])
    template_document = template_engine.load_template(template_name)
    final_document = document_builder.build_document(template_document, complete_data)

    filename = document_builder.generate_filename(metadata)
    output_path = document_builder.save_document(final_document, filename)
    token_usage = get_total_usage()

    return render_template(
        "result.html",
        filename=filename,
        output_path=output_path,
        content=content,
        token_usage=token_usage,
        mode=mode,
    )


@app.route("/download/<path:filename>", methods=["GET"])
def download_file(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        flash("File tidak ditemukan.", "danger")
        return redirect(url_for("index"))
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)
