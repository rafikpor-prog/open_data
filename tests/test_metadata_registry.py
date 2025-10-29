"""
Module: tests.test_metadata_registry
Opis: Testy jednostkowe rejestru metadanych (Etap 10) weryfikujące
rejestrowanie datasetów na podstawie raportów transformacji oraz eksporty
JSON-LD/JSON:API.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ingestion_service.contracts import (
    ColumnSchema,
    DatasetReference,
    TransformationReport,
    TransformationStepStatus,
    VisualizationHint,
)
from ingestion_service.profile import MetadataPolicy
from metadata_service import MetadataRegistry, record_from_transformation


def build_policy() -> MetadataPolicy:
    """
    Technical description:
        Tworzy politykę metadanych dla testów. Wykorzystuje licencję CC BY 4.0,
        domyślne słowa kluczowe oraz częstotliwość aktualizacji `P1M`.

    Instructions for laika:
        "To zestaw zasad do testu – określamy licencję, kontakt i słowa kluczowe,
        aby katalog miał domyślne wartości." 

    Example:
        ```python
        policy = build_policy()
        ```
    Effect for end user:
        Test odwzorowuje ustawienia produkcyjne katalogu DCAT-AP.
    """

    return MetadataPolicy(
        default_license="CC BY 4.0",
        default_publisher="Miasto Demo",
        default_contact_name="Zespół Open Data",
        default_contact_email="opendata@example.gov",
        default_accrual_periodicity="P1M",
        default_spatial="PL",
        default_language="pl",
        keyword_strategy=("dane publiczne", "demo"),
        theme_taxonomy=("DEMOGRAFIA",),
        auto_publish_jsonld=True,
        default_temporal_start=None,
        default_temporal_end=None,
    )


def build_report() -> TransformationReport:
    """
    Technical description:
        Konstruuje przykładowy raport transformacji z jedną kolumną oraz
        sugestią wizualizacji. Dane bazują na fikcyjnym zbiorze populacji.

    Instructions for laika:
        "Symulujemy wynik przetwarzania danych – raport zawiera kolumny, liczbę
        wierszy i propozycję wykresu." 

    Example:
        ```python
        report = build_report()
        ```
    Effect for end user:
        Pozwala odtworzyć scenariusz publikacji katalogu po imporcie danych.
    """

    dataset = DatasetReference(dataset_id="population", resource_id=None)
    columns = [
        ColumnSchema(name="year", data_type="integer", nullable=False, example="2022"),
        ColumnSchema(name="population", data_type="integer", nullable=False, example="12650"),
    ]
    hints = [
        VisualizationHint(chart_type="line", confidence=0.9, reason="Dane czasowe"),
    ]
    now = datetime.utcnow()
    return TransformationReport(
        dataset=dataset,
        rows_in=100,
        rows_out=80,
        columns=columns,
        visualization_hints=hints,
        preview_path="build/preview/population-transformed.json",
        started_at=now,
        finished_at=now,
        applied_steps=[
            TransformationStepStatus(operation="normalize_headers", status="applied", message="OK"),
        ],
        message=None,
    )


def test_record_from_transformation_builds_dataset(tmp_path: Path) -> None:
    policy = build_policy()
    report = build_report()

    record = record_from_transformation(
        report,
        policy,
        overrides={
            "title": "Populacja województw",
            "description": "Zbiór danych o populacji",
            "profile_name": "dev",
            "preview_url": "https://demo.gov/population-preview.json",
            "keywords": ["populacja"],
        },
    )

    assert record.title == "Populacja województw"
    assert "populacja" in record.keywords
    assert record.profile_name == "dev"

    registry = MetadataRegistry(tmp_path / "registry", tmp_path / "exports", policy)
    stored = registry.upsert(record)

    dataset_file = tmp_path / "registry" / "population.json"
    jsonld_file = tmp_path / "exports" / "population.jsonld"
    assert dataset_file.exists()
    assert jsonld_file.exists()
    assert stored.jsonld_path == str(jsonld_file)

    loaded = registry.load("population")
    assert loaded is not None
    assert loaded.license == "CC BY 4.0"

    jsonapi = registry.to_jsonapi(stored)
    assert jsonapi["data"]["attributes"]["title"] == "Populacja województw"
    assert jsonapi["data"]["attributes"]["profile_name"] == "dev"

    catalog = json.loads((tmp_path / "registry" / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["datasets"][0]["id"] == "population"


def test_register_transformation_updates_metadata(tmp_path: Path) -> None:
    policy = build_policy()
    registry = MetadataRegistry(tmp_path / "registry", tmp_path / "exports", policy)
    report = build_report()

    stored = registry.register_transformation(
        report,
        overrides={
            "title": "Populacja",
            "download_url": "https://demo.gov/population.csv",
            "download_format": "text/csv",
        },
    )

    assert stored.jsonld_path is not None
    jsonld = json.loads(Path(stored.jsonld_path).read_text(encoding="utf-8"))
    assert jsonld["dct:identifier"] == "population"
    assert jsonld["dct:license"] == "CC BY 4.0"

    loaded = registry.load("population")
    assert loaded is not None
    assert loaded.distributions[-1].format == "text/csv"
    assert loaded.extras["visualization_hints"][0]["chart_type"] == "line"
