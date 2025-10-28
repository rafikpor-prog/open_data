"""
Module: tests.test_transformation_pipeline
Opis: Testy jednostkowe weryfikujące działanie pipeline'u transformacji danych
(Etap 9) oraz konwersję profilu konfiguracji do ustawień transformacji.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ingestion_service import TransformationPipeline, settings_from_profile
from ingestion_service.contracts import ColumnSchema, DatasetReference, IngestionResult
from ingestion_service.profile import (
    ConfigProfile,
    DatabaseConnection,
    DatabasePolicy,
    IngestionPolicy,
    JsonPolicy,
    RemotePolicy,
    StoragePaths,
    TransformationPolicy,
    TransformationStepConfig,
    XLSXPolicy,
)


def build_profile_with_transformation(tmp_path: Path) -> ConfigProfile:
    """
    Technical description:
        Buduje profil konfiguracyjny zawierający politykę transformacji, używany
        w testach pipeline'u. Profil obejmuje minimalne ustawienia importu oraz
        przykładową sekwencję kroków (normalizacja nagłówków, zmiana nazw,
        filtracja, wyliczenie kolumny oraz agregacja).

    Instructions for laika:
        "Na potrzeby testu tworzymy zestaw ustawień, który mówi jak obrabiać
        dane: czyści nagłówki, zostawia tylko lata od 2021 roku, liczy wartości w
        tysiącach i sumuje je według regionów."

    Example:
        ```python
        profile = build_profile_with_transformation(tmp_path)
        ```
    Effect for end user:
        Zapewnia, że test odtwarza zachowanie produkcyjne profilu transformacji
        zgodnego z wymaganiami dane.gov.pl.
    """

    storage = StoragePaths(
        landing=str(tmp_path / "landing"),
        schema_registry=str(tmp_path / "schemas"),
        preview=str(tmp_path / "preview"),
    )
    policy = IngestionPolicy(
        allowed_separators=(",", ";"),
        default_encoding="utf-8",
        max_file_size_mb=10,
        sample_size=100,
        timezone="Europe/Warsaw",
    )
    xlsx_policy = XLSXPolicy(
        allowed_extensions=(".xlsx",),
        max_file_size_mb=10,
        sample_size=100,
        preferred_sheets=("Dane",),
        header_row_index=1,
    )
    json_policy = JsonPolicy(
        allowed_http_methods=("GET",),
        allowed_content_types=("application/json",),
        max_payload_mb=5,
        max_records=100,
        default_pointer="/results",
        http_timeout=10,
        preview_size=10,
    )
    remote_policy = RemotePolicy(
        allowed_schemes=("https", "http"),
        allowed_content_types=("text/csv", "application/json"),
        max_file_size_mb=20,
        download_cache=str(tmp_path / "cache"),
        state_registry=str(tmp_path / "state"),
        default_schedule="PT12H",
        verify_tls=True,
        retry_attempts=3,
        retry_backoff_seconds=15,
    )
    transformation_policy = TransformationPolicy(
        enabled=True,
        max_rows=5000,
        rounding_precision=2,
        allowed_operations=(
            "normalize_headers",
            "rename_columns",
            "filter_rows",
            "derive_column",
            "aggregate",
        ),
    )
    transformation_steps = (
        TransformationStepConfig(operation="normalize_headers", parameters={}),
        TransformationStepConfig(
            operation="rename_columns",
            parameters={"mapping": {"rok": "year", "populacja": "population", "wojewodztwo": "region"}},
        ),
        TransformationStepConfig(
            operation="filter_rows",
            parameters={"conditions": [{"field": "year", "operator": ">=", "value": 2021}]},
        ),
        TransformationStepConfig(
            operation="derive_column",
            parameters={"name": "population_thousands", "expression": "population / 1000"},
        ),
        TransformationStepConfig(
            operation="aggregate",
            parameters={
                "group_by": ["region"],
                "metrics": [
                    {"field": "population", "function": "sum", "alias": "population_sum"}
                ],
            },
        ),
    )
    return ConfigProfile(
        name="test",
        storage=storage,
        policy=policy,
        xlsx_policy=xlsx_policy,
        json_policy=json_policy,
        remote_policy=remote_policy,
        strict_schema=False,
        description="Profil testowy transformacji",
        database_policy=DatabasePolicy(
            allowed_drivers=("sqlite",),
            max_rows=10000,
            default_limit=1000,
            metadata_cache=str(tmp_path / "db-metadata"),
            timezone="Europe/Warsaw",
        ),
        database_connections={
            "local_sqlite": DatabaseConnection(
                connection_id="local_sqlite",
                url=f"sqlite:///{tmp_path/'demo.sqlite'}",
                driver="sqlite",
                default_schema=None,
                description="Lokalna baza testowa",
                options={},
            )
        },
        transformation_policy=transformation_policy,
        transformation_steps=transformation_steps,
    )


def test_transformation_pipeline_generates_report(tmp_path: Path) -> None:
    """
    Technical description:
        Weryfikuje, że pipeline transformacji stosuje wszystkie kroki profilu,
        generuje agregowane dane, zapisuje podgląd oraz tworzy sugestie
        wizualizacji.

    Instructions for laika:
        "Uruchamiamy pełną sekwencję transformacji na przykładowych danych.
        Sprawdzamy, że raport zawiera nową tabelę z sumami, plik podglądu oraz
        propozycje wykresów."

    Example:
        ```python
        test_transformation_pipeline_generates_report(tmp_path)
        ```
    Effect for end user:
        Potwierdza, że administrator po imporcie otrzyma gotowy materiał do
        publikacji i wizualizacji zgodny ze standardami dane.gov.pl.
    """

    profile = build_profile_with_transformation(tmp_path)
    settings = settings_from_profile(profile)
    pipeline = TransformationPipeline(settings, Path(profile.storage.preview))

    rows = [
        {"rok": "2020", "populacja": "12345", "wojewodztwo": "Mazowieckie"},
        {"rok": "2021", "populacja": "12500", "wojewodztwo": "Mazowieckie"},
        {"rok": "2021", "populacja": "5000", "wojewodztwo": "Małopolskie"},
    ]
    ingestion = IngestionResult(
        dataset=DatasetReference(dataset_id="population", resource_id="2021"),
        row_count=len(rows),
        columns=[
            ColumnSchema(name="rok", data_type="integer", nullable=False, example="2021"),
            ColumnSchema(name="populacja", data_type="integer", nullable=False, example="12500"),
            ColumnSchema(name="wojewodztwo", data_type="string", nullable=False, example="Mazowieckie"),
        ],
        visualization_hints=[],
        preview_path=str(tmp_path / "preview" / "population.json"),
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
        message=None,
    )

    report = pipeline.run(ingestion, rows)

    assert report.rows_in == 3
    assert report.rows_out == 2
    assert Path(report.preview_path).exists()

    preview_data = json.loads(Path(report.preview_path).read_text(encoding="utf-8"))
    assert {row["region"] for row in preview_data["rows"]} == {"Mazowieckie", "Małopolskie"}
    assert any(step.status == "applied" for step in report.applied_steps)
    assert report.visualization_hints
    assert report.message is None or "BRAK" in report.message
