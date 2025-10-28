"""
Module: tests.test_visualization_service
Opis: Testy jednostkowe weryfikujące działanie modułu wizualizacji (etap 13).
"""

from __future__ import annotations

import json
from pathlib import Path

from ingestion_service.contracts import DatasetReference
from ingestion_service.profile import profile_from_dict
from visualization_service import (
    VisualizationRequest,
    build_visualization_service,
)


def _build_profile(tmp_path: Path):
    preview_dir = tmp_path / "preview"
    preview_dir.mkdir()
    return profile_from_dict(
        {
            "name": "dev",
            "description": "Profil testowy wizualizacji",
            "storage": {
                "landing": str(tmp_path / "landing"),
                "schema_registry": str(tmp_path / "schemas"),
                "preview": str(preview_dir),
            },
            "policy": {
                "allowed_separators": [","],
                "default_encoding": "utf-8",
                "max_file_size_mb": 5,
                "sample_size": 10,
                "timezone": "Europe/Warsaw",
            },
            "xlsx_policy": {
                "allowed_extensions": [".xlsx"],
                "max_file_size_mb": 5,
                "sample_size": 10,
                "preferred_sheets": ["Dane"],
                "header_row_index": 1,
            },
            "json_policy": {
                "allowed_http_methods": ["GET"],
                "allowed_content_types": ["application/json"],
                "max_payload_mb": 5,
                "max_records": 50,
                "default_pointer": "/results",
                "http_timeout": 10,
                "preview_size": 10,
            },
            "remote_policy": {
                "allowed_schemes": ["https"],
                "allowed_content_types": ["text/csv"],
                "max_file_size_mb": 5,
                "download_cache": str(tmp_path / "cache"),
                "state_registry": str(tmp_path / "state"),
                "default_schedule": "PT24H",
                "verify_tls": True,
                "retry_attempts": 2,
                "retry_backoff_seconds": 5,
            },
            "visualization": {
                "output_dir": str(tmp_path / "visualizations"),
                "default_formats": ["png", "pdf"],
                "default_chart_types": ["line", "bar"],
                "figure_size": [6, 4],
                "dpi": 100,
                "color_palette": ["#000000", "#FF0000"],
                "background_color": "#FFFFFF",
                "max_series": 2,
                "title_prefix": "Test",
            },
        }
    )


def test_visualization_service_generates_files(tmp_path: Path) -> None:
    profile = _build_profile(tmp_path)
    preview_path = profile.storage.preview / "dataset-transformed.json"
    preview_path.write_text(
        json.dumps(
            {
                "dataset_id": "dataset",
                "rows": [
                    {"year": 2020, "population": 12000},
                    {"year": 2021, "population": 12500},
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    service = build_visualization_service(profile)
    product = service.generate(
        VisualizationRequest(
            dataset=DatasetReference(dataset_id="dataset"),
            preview_path=preview_path,
            chart_type="line",
            x_field="year",
            y_fields=["population"],
            title="Populacja",
        )
    )

    assert product.message is None
    assert len(product.files) == 2
    for file_path in product.files:
        assert file_path.exists()
        assert file_path.suffix in {".png", ".pdf"}


def test_visualization_service_handles_missing_numeric_data(tmp_path: Path) -> None:
    profile = _build_profile(tmp_path)
    preview_path = profile.storage.preview / "dataset-transformed.json"
    preview_path.write_text(
        json.dumps(
            {
                "dataset_id": "dataset",
                "rows": [
                    {"year": "A", "population": "brak"},
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    service = build_visualization_service(profile)
    product = service.generate(
        VisualizationRequest(
            dataset=DatasetReference(dataset_id="dataset"),
            preview_path=preview_path,
            chart_type="line",
            x_field="year",
            y_fields=["population"],
        )
    )

    assert product.message == "**BRAK MOŻLIWEJ WIZUALIZACJI**"
    assert product.files == []

