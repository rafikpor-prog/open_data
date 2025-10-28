"""
Module: report_service.service
Opis: Implementuje `ReportService` odpowiedzialny za generowanie raportów HTML/PDF
na podstawie wizualizacji, metadanych DCAT-AP i raportów transformacji (Etap 15).
Funkcje i klasy:
- class ReportService: główny silnik raportów z obsługą fallbacku PDF.
- function build_report_service: helper zwracający skonfigurowaną usługę na
  podstawie `ConfigProfile`.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence

from ingestion_service.profile import ConfigProfile, ReportSettings
from report_service.models import ReportProduct, ReportRequest, ReportVisualization


class ReportService:
    """
    Technical description:
        Generator raportów łączy wizualizacje, metadane DCAT-AP oraz raporty
        transformacji w dokumenty HTML i PDF. Korzysta z konfiguracji `ReportSettings`
        (sekcja `reports` profilu), uwzględnia załączniki JSON-LD i dzienniki audytu,
        a w środowisku offline tworzy poprawne placeholdery PDF zgodne z wymogami
        archiwizacji danych publicznych.

    Instructions for laika:
        "To maszyna do składania raportów. Wskaż zbiór danych, wybierz wykresy i
        kliknij 'Generuj' – system przygotuje dokument HTML i (jeśli chcesz) PDF,
        dołączy licencję, kontakt oraz załączniki."

    Example:
        ```python
        service = ReportService(profile.report_settings)
        product = service.generate(request)
        ```

    Effect for end user:
        Interesariusze otrzymują kompletny raport zgodny ze standardami dane.gov.pl
        i API BDL bez ręcznego składania dokumentów.
    """

    def __init__(self, settings: ReportSettings) -> None:
        self._settings = settings
        self._output_dir = Path(settings.output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, request: ReportRequest) -> ReportProduct:
        """
        Technical description:
            Buduje raport na podstawie przekazanych danych. Tworzy dokument HTML
            (korzystając z szablonu lub domyślnej struktury) oraz – jeżeli formaty
            przewidują – dokument PDF. Zbiera załączniki JSON-LD, raporty podsumowań
            wizualizacji oraz (opcjonalnie) zapisuje dziennik audytu do pliku.

        Instructions for laika:
            "Przekazujesz opis zbioru, wykresy i załączniki. Funkcja zapisuje raport
            w katalogu `build/reports` i zwraca listę plików, które możesz pobrać."

        Example:
            ```python
            product = service.generate(report_request)
            ```

        Effect for end user:
            Administrator otrzymuje gotowy dokument HTML/PDF wraz z listą załączników
            (JSON-LD, raporty wizualizacji, logi audytu), co skraca czas publikacji.
        """

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        base_name = f"{request.dataset.dataset.dataset_id}-report-{timestamp}"
        html_path = self._output_dir / f"{base_name}.html"
        html_content = self._render_html(request)
        html_path.write_text(html_content, encoding="utf-8")

        files: List[Path] = [html_path]
        attachments: List[Path] = []
        message: Optional[str] = None

        if "pdf" in (format_.lower() for format_ in self._settings.formats):
            pdf_path = self._output_dir / f"{base_name}.pdf"
            try:
                self._generate_pdf(html_content, pdf_path)
            except Exception:
                self._generate_pdf_placeholder(pdf_path, html_path)
                message = (
                    "Wygenerowano zastępczy plik PDF (fallback) – pełny dokument dostępny w HTML."
                )
            files.append(pdf_path)

        for jsonld_path in request.jsonld_paths:
            path = Path(jsonld_path)
            if path.exists():
                attachments.append(path)

        for visualization in request.visualizations:
            product = visualization.product
            if self._settings.include_visualization_summary and visualization.embed_summary:
                summary_path = getattr(product, "summary_path", None)
                if summary_path:
                    path = Path(summary_path)
                    if path.exists():
                        attachments.append(path)

        if self._settings.include_audit_trail and request.audit_entries:
            audit_path = self._output_dir / f"{base_name}-audit.txt"
            audit_path.write_text("\n".join(request.audit_entries), encoding="utf-8")
            attachments.append(audit_path)

        return ReportProduct(
            files=tuple(files),
            attachments=tuple(dict.fromkeys(attachments)),
            generated_at=datetime.utcnow(),
            message=message,
        )

    def _render_html(self, request: ReportRequest) -> str:
        dataset = request.dataset
        template = self._load_template()
        title = f"{self._settings.template.title_prefix}: {dataset.title}"
        metadata_table = self._build_metadata_section(dataset)
        viz_section = self._build_visualization_section(request.visualizations)
        transform_section = self._build_transformation_section(request.transformation)
        audit_section = self._build_audit_section(request.audit_entries)
        notes_section = (
            f"<section class=\"notes\"><h2>Notatki</h2><p>{request.notes}</p></section>"
            if request.notes
            else ""
        )
        body = "\n".join(
            [
                metadata_table,
                viz_section,
                transform_section,
                audit_section,
                notes_section,
            ]
        )
        html = template.replace("{{TITLE}}", title).replace("{{BODY}}", body)
        return html

    def _build_metadata_section(self, dataset: DatasetMetadata) -> str:
        items = [
            ("Identyfikator", dataset.dataset.dataset_id),
            ("Tytuł", dataset.title),
            ("Opis", dataset.description),
            ("Licencja", dataset.license),
            ("Słowa kluczowe", ", ".join(dataset.keywords)),
            ("Tematy", ", ".join(dataset.themes)),
            ("Kontakt", f"{dataset.contact_name} ({dataset.contact_email})"),
            ("Częstotliwość aktualizacji", dataset.accrual_periodicity),
            ("Zakres przestrzenny", dataset.spatial or "-"),
            ("Język", dataset.language or "-"),
            ("Data publikacji", dataset.issued.isoformat()),
            ("Ostatnia modyfikacja", dataset.modified.isoformat()),
        ]
        rows = "\n".join(
            f"<tr><th>{label}</th><td>{value}</td></tr>" for label, value in items
        )
        return f"""
<section class=\"metadata\">
  <h2>Metadane DCAT-AP</h2>
  <table>
    {rows}
  </table>
</section>
"""

    def _build_visualization_section(self, visualizations: Sequence[ReportVisualization]) -> str:
        if not visualizations:
            return (
                "<section class=\"visualizations\"><h2>Wizualizacje</h2>"
                "<p><strong>BRAK DOŁĄCZONYCH WIZUALIZACJI</strong></p></section>"
            )
        cards: List[str] = []
        for viz in visualizations:
            product = viz.product
            figure_list = "".join(
                f"<li><a href=\"{Path(path).name}\">{Path(path).name}</a></li>"
                for path in product.files
            )
            summary_html = ""
            summary_path = getattr(product, "summary_path", None)
            if (
                summary_path
                and viz.embed_summary
                and self._settings.include_visualization_summary
                and Path(summary_path).exists()
            ):
                try:
                    summary_data = json.loads(Path(summary_path).read_text(encoding="utf-8"))
                    summary_html = (
                        "<details><summary>Podsumowanie danych</summary><pre>"
                        + json.dumps(summary_data, ensure_ascii=False, indent=2)
                        + "</pre></details>"
                    )
                except Exception:
                    summary_html = (
                        "<p><strong>Nie udało się odczytać raportu podsumowania.</strong></p>"
                    )
            cards.append(
                f"""
      <article class=\"visualization-card\">
        <h3>{product.chart_type}</h3>
        <ul>{figure_list}</ul>
        {summary_html}
      </article>
    """
            )
        return "<section class=\"visualizations\"><h2>Wizualizacje</h2>" + "".join(cards) + "</section>"

    def _build_transformation_section(
        self, transformation: Optional[TransformationReport]
    ) -> str:
        if not transformation:
            return ""
        steps = "".join(
            f"<li><strong>{step.operation}</strong>: {step.status}"
            + (f" – {step.message}" if step.message else "")
            + "</li>"
            for step in transformation.applied_steps
        )
        return f"""
<section class=\"transformation\">
  <h2>Podsumowanie transformacji</h2>
  <p>Wiersze wejściowe: {transformation.rows_in}, wiersze wyjściowe: {transformation.rows_out}</p>
  <p>Przetwarzanie rozpoczęto {transformation.started_at.isoformat()}, zakończono {transformation.finished_at.isoformat()}.</p>
  <ul>{steps}</ul>
</section>
"""

    def _build_audit_section(self, audit_entries: Sequence[str]) -> str:
        if not audit_entries:
            return ""
        items = "".join(f"<li>{entry}</li>" for entry in audit_entries)
        return f"""
<section class=\"audit\">
  <h2>Dziennik audytu</h2>
  <ul>{items}</ul>
</section>
"""

    def _load_template(self) -> str:
        template_path = Path(self._settings.template.html)
        if template_path.exists():
            content = template_path.read_text(encoding="utf-8")
        else:
            content = """
<!DOCTYPE html>
<html lang=\"pl\">
<head>
  <meta charset=\"utf-8\" />
  <title>{{TITLE}}</title>
  {{STYLES}}
</head>
<body>
  <header><h1>{{TITLE}}</h1></header>
  {{BODY}}
</body>
</html>
"""
        if "{{STYLES}}" in content:
            styles = ""
            if self._settings.template.include_styles:
                styles = """
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #d0d7de; padding: 0.5rem; text-align: left; }
    header { margin-bottom: 1.5rem; }
    section { margin-bottom: 1.5rem; }
    .visualization-card { border: 1px solid #d0d7de; padding: 1rem; margin-bottom: 1rem; }
  </style>
"""
            content = content.replace("{{STYLES}}", styles)
        return content

    def _generate_pdf(self, html_content: str, pdf_path: Path) -> None:
        """
        Technical description:
            Tworzy minimalny dokument PDF na podstawie treści HTML. W pierwszej
            kolejności próbuje wykorzystać prosty renderer wbudowany w moduł
            (konwersja tekstu). Jeśli zapis się nie powiedzie, zgłasza wyjątek,
            który zostanie przechwycony i przekształcony w fallback.

        Instructions for laika:
            "System próbuje zamienić raport HTML na plik PDF. Jeśli się nie uda,
            automatycznie powstanie wersja zastępcza."
        """

        text_content = self._html_to_text(html_content)
        self._write_minimal_pdf(pdf_path, text_content)

    def _generate_pdf_placeholder(self, pdf_path: Path, html_path: Path) -> None:
        note = (
            "Raport w formacie PDF wymaga renderera zewnętrznego. Pełna wersja dostępna w pliku HTML: "
            f"{html_path.name}."
        )
        try:
            self._write_minimal_pdf(pdf_path, note)
        except Exception:
            pdf_path.write_text(note, encoding="utf-8")

    def _write_minimal_pdf(self, pdf_path: Path, text: str) -> None:
        # Minimal dokument PDF z jednym wpisem tekstowym.
        encoded = text.encode("latin-1", errors="ignore")
        stream = b"BT /F1 12 Tf 72 720 Td (" + encoded.replace(b"(", b"[").replace(b")", b"]") + b") Tj ET"
        pdf_bytes = (
            b"%PDF-1.4\n"
            b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n"
            b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n"
            b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n"
            + f"4 0 obj<< /Length {len(stream)} >>stream\n".encode("utf-8")
            + stream
            + b"\nendstream endobj\n"
            b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
            b"xref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000114 00000 n \n0000000227 00000 n \n0000000415 00000 n \n"
            b"trailer<< /Size 6 /Root 1 0 R >>\nstartxref\n502\n%%EOF"
        )
        pdf_path.write_bytes(pdf_bytes)

    def _html_to_text(self, html_content: str) -> str:
        stripped = html_content.replace("<", " <").replace(">", "> ")
        return " ".join(stripped.split())


def build_report_service(profile: ConfigProfile) -> ReportService:
    """
    Technical description:
        Helper tworzący `ReportService` na podstawie profilu konfiguracji.
        Dzięki temu Studio Danych lub testy jednostkowe mogą szybko uzyskać
        gotowy generator raportów zgodny z ustawieniami (`reports`).

    Instructions for laika:
        "Wywołaj tę funkcję, aby otrzymać przygotowany generator raportów dla
        wybranego profilu (np. `dev`)."

    Example:
        ```python
        report_service = build_report_service(profile)
        ```

    Effect for end user:
        Umożliwia natychmiastowe generowanie raportów bez ręcznej konfiguracji
        katalogów i szablonów.
    """

    return ReportService(profile.report_settings)
