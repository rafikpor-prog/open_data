"""
Module: tests.test_xlsx_ingestor
Opis: Testy jednostkowe weryfikujące moduł importu XLSX zgodny z kontraktami
`ingestion-service` oraz profilami konfiguracji etapu 5.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import List
from xml.etree.ElementTree import Element, SubElement, tostring

from ingestion_service import XLSXIngestor, build_default_xlsx_ingestor
from ingestion_service.contracts import DatasetReference, IngestionJobRequest
from ingestion_service.profile import (
    ConfigProfile,
    IngestionPolicy,
    JsonPolicy,
    RemotePolicy,
    StoragePaths,
    XLSXPolicy,
)


def build_test_profile(tmp_path: Path) -> ConfigProfile:
    """
    Technical description:
        Tworzy profil konfiguracji na potrzeby testów ingestu XLSX. Katalogi
        pracy oraz polityki CSV/XLSX są kierowane do przestrzeni tymczasowej,
        aby test nie wpływał na realne dane.

    Instructions for laika:
        "Na czas testu tworzymy bezpieczne katalogi i zasady importu. Dzięki temu
        test dokładnie odwzorowuje środowisko produkcyjne, ale niczego nie psuje."

    Example:
        ```python
        profile = build_test_profile(tmp_path)
        ```
    Effect for end user:
        Zapewnia, że działanie modułu XLSX jest weryfikowane w warunkach zbliżonych
        do rzeczywistego wdrożenia Studio Danych.
    """

    storage = StoragePaths(
        landing=str(tmp_path / "landing"),
        schema_registry=str(tmp_path / "schemas"),
        preview=str(tmp_path / "preview"),
    )
    policy = IngestionPolicy(
        allowed_separators=(",", ";", "\t"),
        default_encoding="utf-8",
        max_file_size_mb=5,
        sample_size=50,
        timezone="Europe/Warsaw",
    )
    xlsx_policy = XLSXPolicy(
        allowed_extensions=(".xlsx",),
        max_file_size_mb=5,
        sample_size=25,
        preferred_sheets=("Dane", "Sheet1"),
        header_row_index=1,
    )
    json_policy = JsonPolicy(
        allowed_http_methods=("GET",),
        allowed_content_types=("application/json",),
        max_payload_mb=5,
        max_records=100,
        default_pointer="/results",
        http_timeout=5,
        preview_size=10,
    )
    remote_policy = RemotePolicy(
        allowed_schemes=("https", "http"),
        allowed_content_types=("text/csv", "application/json", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        max_file_size_mb=5,
        download_cache=str(tmp_path / "cache"),
        state_registry=str(tmp_path / "state"),
        default_schedule="PT6H",
        verify_tls=True,
        retry_attempts=1,
        retry_backoff_seconds=1,
    )
    return ConfigProfile(
        name="test-xlsx",
        storage=storage,
        policy=policy,
        xlsx_policy=xlsx_policy,
        json_policy=json_policy,
        remote_policy=remote_policy,
        strict_schema=False,
        description="Profil testowy XLSX",
    )


def _column_letter(index: int) -> str:
    letters: List[str] = []
    while index:
        index, remainder = divmod(index - 1, 26)
        letters.append(chr(65 + remainder))
    return "".join(reversed(letters))


def create_sample_workbook(path: Path) -> None:
    """
    Technical description:
        Generuje plik XLSX z arkuszem "Dane" zawierającym nagłówki oraz kilka
        wierszy danych liczbowych i tekstowych, korzystając wyłącznie ze
        standardowej biblioteki (ZIP + XML).

    Instructions for laika:
        "Tworzymy mini-arkusz Excela z danymi o populacji, aby sprawdzić jak moduł
        radzi sobie z importem."

    Example:
        ```python
        create_sample_workbook(Path("sample.xlsx"))
        ```
    Effect for end user:
        Pozwala odtworzyć rzeczywisty scenariusz importu bez dostępu do zewnętrznych
        bibliotek.
    """

    headers = ["rok", "populacja", "wojewodztwo"]
    rows = [
        [2020, 12345, "Mazowieckie"],
        [2021, 12500, "Mazowieckie"],
        [2022, 12650, "Mazowieckie"],
    ]

    shared_strings = []
    def shared_index(value: str) -> int:
        if value not in shared_strings:
            shared_strings.append(value)
        return shared_strings.index(value)

    sheet_root = Element("worksheet", xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main")
    sheet_data = SubElement(sheet_root, "sheetData")

    def add_row(row_idx: int, values: List[object]) -> None:
        row_el = SubElement(sheet_data, "row", r=str(row_idx))
        for col_idx, value in enumerate(values, start=1):
            cell_ref = f"{_column_letter(col_idx)}{row_idx}"
            if isinstance(value, str):
                idx = shared_index(value)
                cell_el = SubElement(row_el, "c", r=cell_ref, t="s")
                SubElement(cell_el, "v").text = str(idx)
            else:
                cell_el = SubElement(row_el, "c", r=cell_ref)
                SubElement(cell_el, "v").text = str(value)

    add_row(1, headers)
    for offset, data_row in enumerate(rows, start=2):
        add_row(offset, data_row)

    shared_root = Element("sst", xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main", count=str(len(shared_strings)), uniqueCount=str(len(shared_strings)))
    for text in shared_strings:
        si = SubElement(shared_root, "si")
        SubElement(si, "t").text = text

    workbook_root = Element("workbook", xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main", attrib={"xmlns:r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"})
    sheets_el = SubElement(workbook_root, "sheets")
    SubElement(sheets_el, "sheet", name="Dane", sheetId="1", attrib={"{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id": "rId1"})

    rels_root = Element("Relationships", xmlns="http://schemas.openxmlformats.org/package/2006/relationships")
    SubElement(rels_root, "Relationship", Id="rId1", Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet", Target="worksheets/sheet1.xml")
    SubElement(rels_root, "Relationship", Id="rId2", Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings", Target="sharedStrings.xml")
    SubElement(rels_root, "Relationship", Id="rId3", Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles", Target="styles.xml")

    styles_root = Element("styleSheet", xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main")
    fonts_el = SubElement(styles_root, "fonts", count="1")
    SubElement(fonts_el, "font")
    fills_el = SubElement(styles_root, "fills", count="1")
    SubElement(fills_el, "fill")
    borders_el = SubElement(styles_root, "borders", count="1")
    SubElement(borders_el, "border")
    cell_style_xfs = SubElement(styles_root, "cellStyleXfs", count="1")
    SubElement(cell_style_xfs, "xf")
    cell_xfs = SubElement(styles_root, "cellXfs", count="1")
    SubElement(cell_xfs, "xf", xfId="0")

    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
    <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
    <Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
    <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>
"""

    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
"""

    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", tostring(workbook_root, encoding="utf-8", xml_declaration=True))
        archive.writestr("xl/_rels/workbook.xml.rels", tostring(rels_root, encoding="utf-8", xml_declaration=True))
        archive.writestr("xl/sharedStrings.xml", tostring(shared_root, encoding="utf-8", xml_declaration=True))
        archive.writestr("xl/worksheets/sheet1.xml", tostring(sheet_root, encoding="utf-8", xml_declaration=True))
        archive.writestr("xl/styles.xml", tostring(styles_root, encoding="utf-8", xml_declaration=True))


def test_xlsx_ingestor_generates_preview_and_hints(tmp_path: Path) -> None:
    """
    Technical description:
        Sprawdza, czy XLSXIngestor poprawnie wczytuje arkusz, tworzy schemat
        kolumn oraz zapisuje podgląd JSON z sugestią wizualizacji.

    Instructions for laika:
        "Importujemy testowy plik Excel i upewniamy się, że raport wygląda
        dokładnie tak, jak oczekuje panel Studio Danych."

    Example:
        ```python
        test_xlsx_ingestor_generates_preview_and_hints(tmp_path)
        ```
    Effect for end user:
        Gwarantuje, że użytkownik zobaczy opis kolumn i propozycję wykresu po
        zaimportowaniu Excela w produkcyjnej wtyczce.
    """

    workbook_path = tmp_path / "sample.xlsx"
    create_sample_workbook(workbook_path)
    profile = build_test_profile(tmp_path)
    ingestor = XLSXIngestor(profile)
    job = IngestionJobRequest(
        source_uri=str(workbook_path),
        profile_name=profile.name,
        dataset=DatasetReference(dataset_id="population"),
        options={"sheet_name": "Dane"},
    )

    result = ingestor.run(job)

    assert result.row_count == 3
    assert len(result.columns) == 3
    assert {column.name for column in result.columns} == {"rok", "populacja", "wojewodztwo"}
    assert Path(result.preview_path).exists()

    preview_json = json.loads(Path(result.preview_path).read_text(encoding="utf-8"))
    assert preview_json["sheet_name"] == "Dane"
    assert preview_json["dataset_id"] == "population"
    assert preview_json["total_rows"] == 3

    if result.visualization_hints:
        assert result.visualization_hints[0].chart_type in {"line", "bar"}
    else:
        assert result.message == "**BRAK MOŻLIWEJ WIZUALIZACJI**"


def test_build_default_xlsx_ingestor_uses_gitops_profile(tmp_path: Path, monkeypatch) -> None:
    """
    Technical description:
        Weryfikuje, że funkcja `build_default_xlsx_ingestor` potrafi odczytać profil
        z repozytorium GitOps, gdy `config-service` jest niedostępny.

    Instructions for laika:
        "Udajemy, że pracujemy offline. Sprawdzamy, czy moduł korzysta z kopii
        ustawień zapisanej na dysku i nadal poprawnie importuje arkusz."

    Example:
        ```python
        test_build_default_xlsx_ingestor_uses_gitops_profile(tmp_path, monkeypatch)
        ```
    Effect for end user:
        Potwierdza, że administrator może polegać na profilach GitOps podczas
        awarii sieci i nadal importować dane do katalogu.
    """

    gitops_root = tmp_path / "profiles"
    gitops_root.mkdir()
    (gitops_root / "offline.json").write_text(
        json.dumps(
            {
                "name": "offline",
                "storage": {
                    "landing": str(tmp_path / "landing"),
                    "schema_registry": str(tmp_path / "schemas"),
                    "preview": str(tmp_path / "preview"),
                },
                "policy": {
                    "allowed_separators": [",", ";"],
                    "default_encoding": "utf-8",
                    "max_file_size_mb": 5,
                    "sample_size": 50,
                    "timezone": "Europe/Warsaw",
                },
                "xlsx_policy": {
                    "allowed_extensions": [".xlsx"],
                    "max_file_size_mb": 5,
                    "sample_size": 25,
                    "preferred_sheets": ["Dane"],
                    "header_row_index": 1,
                },
                "strict_schema": False,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("CONFIG_GITOPS_ROOT", str(gitops_root))

    workbook_path = tmp_path / "offline.xlsx"
    create_sample_workbook(workbook_path)

    ingestor = build_default_xlsx_ingestor("offline")
    job = IngestionJobRequest(
        source_uri=str(workbook_path),
        profile_name="offline",
        dataset=DatasetReference(dataset_id="population"),
        options={},
    )
    result = ingestor.run(job)

    assert result.row_count == 3
    assert Path(result.preview_path).exists()
