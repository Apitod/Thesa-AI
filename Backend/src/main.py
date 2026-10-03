import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.input_handler import InputHandler, get_input_handler
from src.template_engine import TemplateEngine, get_template_engine
from src.document_builder import DocumentBuilder, get_document_builder
from src.ai_engine import AIEngine, get_ai_engine
from src.token_logger import TokenLogger, get_total_usage
from rich.console import Console
from rich.panel import Panel


class PaperGeneratorApp:
    def __init__(self):
        self.console = Console()
        self.input_handler = get_input_handler()
        self.template_engine = get_template_engine()
        self.document_builder = get_document_builder()
        self.ai_engine = get_ai_engine()
        self.token_logger = TokenLogger()

    def display_welcome(self):
        self.input_handler.display_welcome()

    def run_workflow(self):
        self.display_welcome()

        try:
            metadata = self.input_handler.collect_paper_metadata()
            authors = self.input_handler.collect_author_info()
            institution = self.input_handler.collect_institution_info()

            if not self.input_handler.validate_input({**metadata, **institution}):
                self.console.print("[red][FAIL] Validasi gagal. Silakan periksa input Anda.[/red]")
                return

            self.input_handler.display_summary(metadata, authors, institution)

            template_name = self.input_handler.select_template()

            generation_mode = self.input_handler.select_generation_mode()

            context = {**metadata, **institution}

            if generation_mode == "1":
                content = self.manual_content_generation(context)

            elif generation_mode == "2":
                content = self.ai_per_section_generation(context)

            else:
                content = self.ai_full_generation(context)

            self.input_handler.preview_content(content)

            edit = self.input_handler.console.input("\n[cyan]Edit konten? (y/n): [/cyan]").lower()

            if edit == 'y':
                content = self.input_handler.edit_content(content)

            complete_paper_data = self.document_builder.build_complete_paper_data(
                metadata, authors, institution, content
            )

            template = self.template_engine.load_template(template_name)

            final_document = self.document_builder.build_document(template, complete_paper_data)

            filename = self.document_builder.generate_filename(metadata)
            output_path = self.document_builder.save_document(final_document, filename)

            token_usage = get_total_usage()

            self.document_builder.display_completion_summary(output_path, token_usage)

        except KeyboardInterrupt:
            self.console.print("\n\n[yellow][WARNING] Proses dibatalkan oleh pengguna[/yellow]")
        except Exception as e:
            self.console.print(f"\n[red][FAIL] Terjadi kesalahan: {str(e)}[/red]")
            import traceback
            self.console.print(f"[dim]{traceback.format_exc()}[/dim]")

    def manual_content_generation(self, context: dict) -> dict:
        self.console.print("\n[bold yellow]========== GENERASI MANUAL ==========[/bold yellow]\n")

        content = {}
        sections = [
            'latar_belakang',
            'rumusan_masalah',
            'tujuan',
            'pembahasan',
            'kesimpulan'
        ]

        for section in sections:
            section_name = section.replace('_', ' ').title()
            content[section] = self.input_handler.collect_section_content(section_name)

        return content

    def ai_per_section_generation(self, context: dict) -> dict:
        self.console.print("\n[bold yellow]========== AI GENERATION PER BAGIAN ==========[/bold yellow]\n")

        content = {}
        sections = [
            'latar_belakang',
            'rumusan_masalah',
            'tujuan',
            'pembahasan',
            'kesimpulan'
        ]

        for section in sections:
            generate = self.input_handler.console.input(
                f"\n[cyan]Generate {section.replace('_', ' ').title()} menggunakan AI? (y/n): [/cyan]"
            ).lower()

            if generate == 'y':
                generated_content, input_tokens, output_tokens = self.ai_engine.generate_section(section, context)

                if generated_content:
                    content[section] = generated_content
                    self.token_logger.log_usage(f"generate_{section}", input_tokens, output_tokens)
                else:
                    self.console.print(f"[yellow][WARNING] Gagal generate {section.replace('_', ' ').title()}, menggunakan input manual[/yellow]")
                    content[section] = self.input_handler.collect_section_content(section.replace('_', ' ').title())
            else:
                content[section] = self.input_handler.collect_section_content(section.replace('_', ' ').title())

        return content

    def ai_full_generation(self, context: dict) -> dict:
        self.console.print("\n[bold yellow]========== AI FULL GENERATION ==========[/bold yellow]\n")

        confirm = self.input_handler.console.input(
            "[cyan]Generate seluruh konten menggunakan AI? (y/n): [/cyan]"
        ).lower()

        if confirm != 'y':
            return self.manual_content_generation(context)

        return self.ai_engine.generate_full_paper(context, context)

    def display_help(self):
        help_text = """
[bold cyan]============================================================
                      BANTUAN SISTEM
============================================================[/bold cyan]

[bold green]Tentang Sistem:[/bold green]
Sistem Generator Makalah CLI membantu Anda membuat makalah dengan
format UIN menggunakan template dan AI generation.

[bold green]Cara Penggunaan:[/bold green]
1. Jalankan sistem: python src/main.py
2. Ikuti instruksi di layar untuk mengisi data makalah
3. Pilih mode pembuatan konten (Manual/AI)
4. Preview dan edit konten jika diperlukan
5. Makalah akan disimpan di folder output/

[bold green]Mode Pembuatan:[/bold green]
- Manual: Isi semua bagian secara manual
- AI Per BAB: Generate per bagian dengan pilihan manual
- AI Full: Generate seluruh konten menggunakan AI

[bold green]Token Usage:[/bold green]
Setiap penggunaan AI akan dicatat di logs/token_usage.json
Anda dapat memantau penggunaan token untuk mengontrol biaya.

[bold green]Template:[/bold green]
Template disimpan di folder templates/
Anda dapat menambahkan template baru dengan format .docx

[bold green]Troubleshooting:[/bold green]
- Pastikan dependencies terinstall: pip install -r requirements.txt
- Atur ZAI_API_KEY di file .env untuk fitur AI
- Pastikan folder templates/ dan output/ dapat diakses

[bold green]Support:[/bold green]
Untuk bantuan lebih lanjut, hubungi tim pengembang.
        """
        self.console.print(Panel(help_text, border_style="cyan"))


def main():
    app = PaperGeneratorApp()

    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        app.display_help()
        return

    try:
        app.run_workflow()
    except KeyboardInterrupt:
        app.console.print("\n\n[yellow][WARNING] Program dihentikan oleh pengguna[/yellow]")
        sys.exit(0)
    except Exception as e:
        app.console.print(f"\n[red][FAIL] Error: {str(e)}[/red]")
        import traceback
        app.console.print(f"[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()