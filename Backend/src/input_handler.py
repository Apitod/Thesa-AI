import re
from typing import List, Dict, Optional
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table


class InputHandler:
    def __init__(self):
        self.console = Console()

    def display_welcome(self):
        welcome_text = """
[bold cyan]============================================================
                 SISTEM GENERATOR MAKALIH UIN
                    (Template + AI Engine)
============================================================[/bold cyan]

[green]Selamat datang! Sistem ini akan membantu Anda membuat makalah
dengan format UIN menggunakan template dan AI generation.[/green]

        """
        self.console.print(Panel(welcome_text, border_style="cyan"))

    def collect_paper_metadata(self) -> Dict[str, str]:
        metadata = {}

        self.console.print("[bold yellow]1. Informasi Dasar Makalah[/bold yellow]\n")

        metadata['mata_kuliah'] = Prompt.ask(
            "[cyan]Mata Kuliah",
            default="Pengantar Ilmu Komputer"
        )

        metadata['judul'] = Prompt.ask(
            "[cyan]Judul Makalah",
            default="Penerapan Artificial Intelligence dalam Pendidikan"
        )

        metadata['dosen'] = Prompt.ask(
            "[cyan]Nama Dosen Pengampu",
            default="Dr. Ahmad, M.Kom"
        )

        return metadata

    def collect_author_info(self) -> List[Dict[str, str]]:
        authors = []

        self.console.print("\n[bold yellow]2. Informasi Penulis[/bold yellow]\n")

        while True:
            author = {}

            author['nama'] = Prompt.ask(
                f"[cyan]Nama Penulis {len(authors) + 1}",
                default="Budi Santoso"
            )

            author['nim'] = Prompt.ask(
                f"[cyan]NIM Penulis {len(authors) + 1}",
                default="123456789"
            )

            authors.append(author)

            if len(authors) >= 3:
                self.console.print("[yellow]Maksimal 3 penulis yang diperbolehkan.[/yellow]")
                break

            add_more = Confirm.ask(
                "[cyan]Tambah penulis lain?",
                default=False
            )
            if not add_more:
                break

        return authors

    def collect_institution_info(self) -> Dict[str, str]:
        institution = {}

        self.console.print("\n[bold yellow]3. Informasi Kampus[/bold yellow]\n")

        institution['jurusan'] = Prompt.ask(
            "[cyan]Jurusan",
            default="Teknik Informatika"
        )

        institution['fakultas'] = Prompt.ask(
            "[cyan]Fakultas",
            default="Fakultas Sains dan Teknologi"
        )

        institution['kampus'] = Prompt.ask(
            "[cyan]Nama Kampus",
            default="UIN Alauddin Makassar"
        )

        institution['tahun'] = Prompt.ask(
            "[cyan]Tahun",
            default="2025"
        )

        institution['tempat_tanggal'] = Prompt.ask(
            "[cyan]Tempat & Tanggal",
            default="Makassar, 17 April 2025"
        )

        return institution

    def select_template(self) -> str:
        templates = ["UIN Alauddin"]

        self.console.print("\n[bold yellow]4. Pilihan Template[/bold yellow]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("No", style="cyan", width=5)
        table.add_column("Template", style="green")

        for i, template in enumerate(templates, 1):
            table.add_row(str(i), template)

        self.console.print(table)

        choice = Prompt.ask(
            "[cyan]Pilih template (1)",
            choices=["1"],
            default="1"
        )

        return templates[int(choice) - 1]

    def select_generation_mode(self) -> str:
        modes = {
            "1": {
                "name": "Manual",
                "description": "Isi semua bagian makalah secara manual"
            },
            "2": {
                "name": "AI Per BAB",
                "description": "Generate konten per bagian menggunakan AI"
            },
            "3": {
                "name": "AI Full",
                "description": "Generate semua konten menggunakan AI"
            }
        }

        self.console.print("\n[bold yellow]5. Mode Pembuatan Konten[/bold yellow]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("No", style="cyan", width=5)
        table.add_column("Mode", style="green")
        table.add_column("Deskripsi", style="white")

        for key, mode in modes.items():
            table.add_row(key, mode["name"], mode["description"])

        self.console.print(table)

        choice = Prompt.ask(
            "[cyan]Pilih mode pembuatan konten (1/2/3)",
            choices=["1", "2", "3"],
            default="1"
        )

        return choice

    def collect_section_content(self, section_name: str) -> str:
        self.console.print(f"\n[bold yellow]Isi {section_name}:[/bold yellow]")
        self.console.print("[dim](Ketik 'SELESAI' pada baris baru untuk mengakhiri input)[/dim]\n")

        lines = []
        while True:
            line = Prompt.ask(">", default="")
            if line.upper() == "SELESAI":
                break
            if line:
                lines.append(line)

        return "\n".join(lines)

    def preview_content(self, content: Dict[str, str]):
        self.console.print("\n[bold cyan]========== PREVIEW KONTEN ==========[/bold cyan]\n")

        for section, text in content.items():
            self.console.print(f"[bold green]{section.upper()}:[/bold green]")
            if len(text) > 500:
                self.console.print(f"[white]{text[:500]}...[/white]")
            else:
                self.console.print(f"[white]{text}[/white]")
            self.console.print("-" * 50 + "\n")

    def edit_content(self, content: Dict[str, str]) -> Dict[str, str]:
        sections = list(content.keys())

        while True:
            self.console.print("\n[bold yellow]PILIH BAGIAN UNTUK DIEDIT:[/bold yellow]")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("No", style="cyan", width=5)
            table.add_column("Bagian", style="green")

            for i, section in enumerate(sections, 1):
                table.add_row(str(i), section)

            self.console.print(table)

            choice = Prompt.ask(
                "\n[cyan]Pilih nomor bagian untuk diedit (0 untuk selesai)",
                choices=[str(i) for i in range(len(sections) + 1)],
                default="0"
            )

            if choice == "0":
                break

            section_to_edit = sections[int(choice) - 1]
            new_content = self.collect_section_content(section_to_edit)

            if new_content:
                content[section_to_edit] = new_content
                self.console.print(f"[green][OK] {section_to_edit} berhasil diperbarui[/green]")
            else:
                self.console.print(f"[yellow][UNCHANGED] {section_to_edit} tidak diubah[/yellow]")

        return content

    def validate_input(self, data: Dict[str, str]) -> bool:
        required_fields = ['mata_kuliah', 'judul', 'dosen', 'jurusan', 'fakultas']

        for field in required_fields:
            if field not in data or not data[field].strip():
                self.console.print(f"[red]✗ Field '{field}' tidak boleh kosong[/red]")
                return False

        return True

    def display_summary(self, metadata: Dict[str, str], authors: List[Dict[str, str]], institution: Dict[str, str]):
        self.console.print("\n[bold cyan]========== RINGKASAN MAKAHLAH ==========[/bold cyan]\n")

        table = Table(show_header=False, box=None)
        table.add_column("Field", style="cyan", width=20)
        table.add_column("Value", style="white")

        for key, value in metadata.items():
            table.add_row(key.replace('_', ' ').title(), value)

        self.console.print(table)

        self.console.print(f"\n[bold green]Penulis:[/bold green]")
        for i, author in enumerate(authors, 1):
            self.console.print(f"  {i}. {author['nama']} (NIM: {author['nim']})")

        table2 = Table(show_header=False, box=None)
        table2.add_column("Field", style="cyan", width=20)
        table2.add_column("Value", style="white")

        for key, value in institution.items():
            table2.add_row(key.replace('_', ' ').title(), value)

        self.console.print("\n")
        self.console.print(table2)


def get_input_handler():
    return InputHandler()