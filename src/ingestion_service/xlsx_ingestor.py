"""
Module: ingestion_service.xlsx_ingestor
Opis: Implementuje import XLSX zgodny z kontraktami `ingestion-service`,
profilami konfiguracji `config-service` oraz wymaganiami etapu 5.
Funkcje i klasy:
- class SimpleWorkbook: lekki czytnik XLSX wykorzystujący standardową bibliotekę (ZIP + XML).
- class XLSXIngestor: silnik importu plików Excel z autodetekcją arkuszy i nagłówków.
- function build_default_xlsx_ingestor: helper do szybkiego uruchomienia ingestu XLSX.
"""

from __future__ import annotations

import json
import os
import zipfile
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple
from xml.etree import ElementTree as ET

from .config_client import resolve_profile
from .contracts import (
    ColumnSchema,
    DatasetReference,
    IngestionJobRequest,
    IngestionResult,
    VisualizationHint,
)
from .csv_ingestor import infer_column_type
from .profile import ConfigProfile


class SimpleWorkbook:
    """
    Technical description:
        Minimalistyczny czytnik plików XLSX oparty na standardowych modułach
        `zipfile` oraz `xml.etree.ElementTree`. Zapewnia dostęp do listy arkuszy i
        umożliwia iterację po wierszach bez dodatkowych zależności.

    Instructions for laika:
        "To mały silnik, który otwiera plik Excel jak archiwum ZIP i czyta arkusz
        linijka po linijce, aby importer mógł przygotować raport."

    Example:
        ```python
        workbook = SimpleWorkbook(Path("dane.xlsx"))
        for row in workbook.iter_rows("Dane"):
            print(row)
        workbook.close()
        ```
    Effect for end user:
        Pozwala korzystać z importu XLSX w środowiskach offline (np. GovCloud) bez
        konieczności instalowania dodatkowych bibliotek.
    """

    _NS = {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    }

    def __init__(self, filename: Path) -> None:
        self._zip = zipfile.ZipFile(filename)
        self._sheet_map = self._load_sheet_map()
        self._shared_strings = self._load_shared_strings()
        self.sheetnames = list(self._sheet_map.keys())

    def _load_sheet_map(self) -> "OrderedDict[str, str]":
        workbook_xml = self._zip.read("xl/workbook.xml")
        workbook_tree = ET.fromstring(workbook_xml)
        rels_tree = ET.fromstring(self._zip.read("xl/_rels/workbook.xml.rels"))
        rels: Dict[str, str] = {}
        for rel in rels_tree.findall("rel:Relationship", namespaces={"rel": "http://schemas.openxmlformats.org/package/2006/relationships"}):
            rels[rel.attrib["Id"]] = rel.attrib["Target"]

        sheet_map: "OrderedDict[str, str]" = OrderedDict()
        for sheet in workbook_tree.findall("main:sheets/main:sheet", namespaces=self._NS):
            name = sheet.attrib["name"]
            rel_id = sheet.attrib[f"{{{self._NS['rel']}}}id"]
            target = rels.get(rel_id)
            if not target:
                continue
            sheet_map[name] = f"xl/{target}" if not target.startswith("/") else target.lstrip("/")
        return sheet_map

    def _load_shared_strings(self) -> List[str]:
        if "xl/sharedStrings.xml" not in self._zip.namelist():
            return []
        shared_tree = ET.fromstring(self._zip.read("xl/sharedStrings.xml"))
        strings: List[str] = []
        for si in shared_tree.findall("main:si", namespaces=self._NS):
            text_node = si.find("main:t", namespaces=self._NS)
            if text_node is None:
                # Obsługa inlineStr z wieloma fragmentami
                text_chunks = [node.text or "" for node in si.findall(".//main:t", namespaces=self._NS)]
                strings.append("".join(text_chunks))
            else:
                strings.append(text_node.text or "")
        return strings

    def iter_rows(self, sheet_name: str) -> Iterable[List[str]]:
        sheet_path = self._sheet_map[sheet_name]
        sheet_tree = ET.fromstring(self._zip.read(sheet_path))
        sheet_data = sheet_tree.find("main:sheetData", namespaces=self._NS)
        if sheet_data is None:
            return []

        for row in sheet_data.findall("main:row", namespaces=self._NS):
            cells: Dict[int, str] = {}
            max_index = 0
            for cell in row.findall("main:c", namespaces=self._NS):
                ref = cell.attrib.get("r", "")
                col_index = self._column_index(ref)
                cell_type = cell.attrib.get("t")
                value = ""
                if cell_type == "s":
                    idx_text = self._safe_text(cell.find("main:v", namespaces=self._NS))
                    if idx_text:
                        try:
                            value = self._shared_strings[int(idx_text)]
                        except (ValueError, IndexError):
                            value = ""
                elif cell_type == "b":
                    value = "1" if self._safe_text(cell.find("main:v", namespaces=self._NS)) in {"1", "TRUE", "true"} else "0"
                elif cell_type == "inlineStr":
                    value = self._safe_text(cell.find("main:is/main:t", namespaces=self._NS))
                else:
                    value = self._safe_text(cell.find("main:v", namespaces=self._NS))
                if col_index == 0:
                    col_index = len(cells) + 1
                cells[col_index] = value
                max_index = max(max_index, col_index)

            row_values = ["" for _ in range(max_index)]
            for idx, cell_value in cells.items():
                row_values[idx - 1] = cell_value or ""
            yield row_values

    def close(self) -> None:
        self._zip.close()

    @staticmethod
    def _column_index(reference: str) -> int:
        letters = "".join(ch for ch in reference if ch.isalpha())
        if not letters:
            return 0
        index = 0
        for ch in letters:
            index = index * 26 + (ord(ch.upper()) - ord("A") + 1)
        return index

    @staticmethod
    def _safe_text(node: ET.Element | None) -> str:
        return node.text if node is not None and node.text is not None else ""


class XLSXIngestor:
    """
    Technical description:
        Wykonuje import danych z plików XLSX. Obsługuje wybór arkusza na podstawie
        profilu konfiguracji lub parametrów zadania, waliduje rozszerzenie i rozmiar,
        generuje schemat kolumn i podgląd danych oraz przygotowuje sugestie
        wizualizacji zgodne z kontraktami `ingestion-service`.

    Instructions for laika:
        "To odpowiednik importu CSV dla plików Excel. Wskazujesz arkusz albo
        pozwalasz systemowi wybrać go automatycznie, a moduł przygotowuje raport
        i propozycje wykresów."

    Example:
        ```python
        ingestor = XLSXIngestor(resolve_profile("dev"))
        job = IngestionJobRequest(
            source_uri="/ścieżka/dane.xlsx",
            profile_name="dev",
            dataset=DatasetReference(dataset_id="population"),
            options={"sheet_name": "Dane"}
        )
        result = ingestor.run(job)
        ```
    Effect for end user:
        Administrator otrzymuje spójny raport z importu Excela, który może
        natychmiast wykorzystać do publikacji i wizualizacji w portalu danych.
    """

    def __init__(self, profile: ConfigProfile) -> None:
        self._profile = profile
        self._landing_path = Path(profile.storage.landing)
        self._schema_path = Path(profile.storage.schema_registry)
        self._preview_path = Path(profile.storage.preview)
        self._landing_path.mkdir(parents=True, exist_ok=True)
        self._schema_path.mkdir(parents=True, exist_ok=True)
        self._preview_path.mkdir(parents=True, exist_ok=True)

    def run(self, job: IngestionJobRequest) -> IngestionResult:
        """
        Technical description:
            Przetwarza pojedynczy plik XLSX: waliduje rozszerzenie i rozmiar,
            wybiera arkusz, odczytuje nagłówki i próbkę danych, generuje opis
            kolumn, zapisuje podgląd JSON oraz kopię w strefie landing.

        Instructions for laika:
            "System otwiera plik Excel, wybiera właściwy arkusz i tworzy raport
            z najważniejszymi informacjami. Ty widzisz ile jest wierszy, jakie
            kolumny wykryto i jaki wykres warto utworzyć."

        Example:
            ```python
            result = XLSXIngestor(resolve_profile("dev")).run(job)
            ```
        Effect for end user:
            Zapewnia zgodny z wymaganiami dane.gov.pl import Excela oraz gotowe
            informacje dla panelu Studio Danych i integracji WordPress.
        """

        source_path = Path(job.source_uri)
        if not source_path.exists():
            raise FileNotFoundError(f"Plik {source_path} nie istnieje")

        self._validate_extension(source_path.suffix)
        self._validate_size(source_path)

        workbook = SimpleWorkbook(source_path)
        try:
            sheet = self._select_sheet(workbook.sheetnames, job.options)
            rows_iter = workbook.iter_rows(sheet)
            header_row_index = int(job.options.get("header_row_index", self._profile.xlsx_policy.header_row_index))

            headers = self._extract_headers(rows_iter, header_row_index)
            data_rows, total_rows = self._collect_rows(rows_iter, self._profile.xlsx_policy.sample_size)
            if not headers:
                raise ValueError("Nie wykryto nagłówków w arkuszu XLSX")

            columns = self._build_columns(headers, data_rows)
            visualization_hints, message = self._build_visualization_hints(columns)
            preview_file = self._write_preview(job, sheet, headers, data_rows, total_rows)
            self._copy_to_landing(source_path)

            now = datetime.utcnow()
            result = IngestionResult(
                dataset=job.dataset,
                row_count=total_rows,
                columns=columns,
                visualization_hints=visualization_hints,
                preview_path=str(preview_file),
                started_at=now,
                finished_at=now,
                message=message,
            )
            return result
        finally:
            workbook.close()

    def _validate_extension(self, suffix: str) -> None:
        allowed = {ext.lower() for ext in self._profile.xlsx_policy.allowed_extensions}
        if suffix.lower() not in allowed:
            raise ValueError("Nieobsługiwane rozszerzenie pliku XLSX")

    def _validate_size(self, source_path: Path) -> None:
        file_size_mb = source_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self._profile.xlsx_policy.max_file_size_mb:
            raise ValueError("Przekroczono maksymalny rozmiar pliku XLSX")

    def _select_sheet(self, sheetnames: Sequence[str], options: dict[str, str]) -> str:
        requested = options.get("sheet_name")
        if requested:
            if requested in sheetnames:
                return requested
            raise ValueError("Wskazany arkusz nie istnieje w pliku XLSX")

        for preferred in self._profile.xlsx_policy.preferred_sheets:
            if preferred in sheetnames:
                return preferred

        return sheetnames[0]

    def _extract_headers(self, rows_iter: Iterable[List[str]], header_row_index: int) -> List[str]:
        current_index = 1
        headers: List[str] = []
        for row in rows_iter:
            if current_index < header_row_index:
                current_index += 1
                continue
            headers = [self._format_cell(value, idx) for idx, value in enumerate(row, start=1)]
            break
        return headers

    def _collect_rows(self, rows_iter: Iterable[List[str]], limit: int) -> Tuple[List[List[str]], int]:
        data_rows: List[List[str]] = []
        total = 0
        for row in rows_iter:
            total += 1
            if len(data_rows) < limit:
                data_rows.append([self._stringify(value) for value in row])
        return data_rows, total

    def _build_columns(self, headers: Sequence[str], rows: Sequence[Sequence[str]]) -> List[ColumnSchema]:
        columns: List[ColumnSchema] = []
        for idx, header in enumerate(headers):
            values = [row[idx] for row in rows if len(row) > idx]
            data_type, nullable, example = infer_column_type(values)
            columns.append(
                ColumnSchema(
                    name=header.strip(),
                    data_type=data_type,
                    nullable=nullable,
                    example=example,
                )
            )
        return columns

    def _build_visualization_hints(self, columns: Sequence[ColumnSchema]) -> Tuple[List[VisualizationHint], str | None]:
        numeric_columns = [col for col in columns if col.data_type in {"integer", "decimal"}]
        date_columns = [col for col in columns if col.data_type in {"date", "datetime"}]

        hints: List[VisualizationHint] = []
        if numeric_columns and date_columns:
            hints.append(
                VisualizationHint(
                    chart_type="line",
                    confidence=0.9,
                    reason="Wykryto kolumnę czasu i wartości liczbowe",
                )
            )
        elif numeric_columns:
            hints.append(
                VisualizationHint(
                    chart_type="bar",
                    confidence=0.7,
                    reason="Dane liczbowe bez wymiaru czasu – sugerowany wykres słupkowy",
                )
            )

        message = None
        if not hints:
            message = "**BRAK MOŻLIWEJ WIZUALIZACJI**"
        return hints, message

    def _write_preview(
        self,
        job: IngestionJobRequest,
        sheet_name: str,
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
        total_rows: int,
    ) -> Path:
        preview_data = {
            "dataset_id": job.dataset.dataset_id,
            "resource_id": job.dataset.resource_id,
            "sheet_name": sheet_name,
            "headers": list(headers),
            "rows": [list(row) for row in rows[:20]],
            "total_rows": total_rows,
            "generated_at": datetime.utcnow().isoformat(),
        }
        preview_file = self._preview_path / f"{job.dataset.dataset_id}-{job.profile_name}-xlsx.json"
        preview_file.write_text(json.dumps(preview_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return preview_file

    def _copy_to_landing(self, source_path: Path) -> None:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        target = self._landing_path / f"{timestamp}-{source_path.name}"
        target.write_bytes(source_path.read_bytes())

    @staticmethod
    def _format_cell(value: object, index: int) -> str:
        return value if isinstance(value, str) and value.strip() else f"column_{index}"

    @staticmethod
    def _stringify(value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)


def build_default_xlsx_ingestor(profile_name: str) -> XLSXIngestor:
    """
    Technical description:
        Pomocnicza funkcja budująca `XLSXIngestor` na podstawie profilu
        konfiguracji. Używana w CLI oraz testach, aby szybko uruchomić import
        Excela z zachowaniem tych samych zasad co w środowisku produkcyjnym.

    Instructions for laika:
        "Zamiast konfigurować wszystko ręcznie, wywołujesz tę funkcję i natychmiast
        otrzymujesz gotowy mechanizm importu XLSX."

    Example:
        ```python
        ingestor = build_default_xlsx_ingestor("dev")
        ```
    Effect for end user:
        Przyspiesza konfigurację pracy administratora danych i automatyzuje
        korzystanie z centralnych profili.
    """

    profile = resolve_profile(profile_name)
    return XLSXIngestor(profile)


if __name__ == "__main__":
    profile_name = os.getenv("ODP_PROFILE", "dev")
    source = os.getenv("ODP_XLSX_SOURCE")
    if not source:
        raise SystemExit("Zmienna środowiskowa ODP_XLSX_SOURCE jest wymagana")
    job = IngestionJobRequest(
        source_uri=source,
        profile_name=profile_name,
        dataset=DatasetReference(dataset_id=os.getenv("ODP_DATASET_ID", "dataset")),
        options={
            "sheet_name": os.getenv("ODP_XLSX_SHEET", ""),
        },
    )
    ingestor = build_default_xlsx_ingestor(profile_name)
    result = ingestor.run(job)
    print(
        json.dumps(
            {
                "dataset": result.dataset.dataset_id,
                "row_count": result.row_count,
                "columns": [column.__dict__ for column in result.columns],
                "visualization_hints": [hint.__dict__ for hint in result.visualization_hints],
                "message": result.message,
                "preview_path": result.preview_path,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
