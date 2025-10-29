"""
Module: tests.test_report_service
Opis: Testy jednostkowe weryfikujące działanie generatora raportów (Etap 15).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List

import pytest

from ingestion_service.contracts import (
    DatasetMetadata,
    DatasetReference,
    TransformationReport,
    TransformationStepStatus,
    VisualizationHint,
)
from visualization_service.models import VisualizationProduct
from ingestion_service.profile import profile_from_dict
from report_service import ReportRequest, ReportService, ReportVisualization, build_report_service


def _build_profile(tmp_path: Path):
    preview_dir = tmp_path / "preview"
    preview_dir.mkdir()
    return profile_from_dict(
        {
            "name": "dev",
            "description": "Profil testowy raportów",
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
                "default_formats": ["png"],
                "default_chart_types": ["line"],
                "figure_size": [6, 4],
                "dpi": 100,
                "color_palette": ["#000000"],
                "background_color": "#FFFFFF",
                "max_series": 2,
                "title_prefix": "Test",
                "advanced": {
                    "enable_advanced": True,
                    "map_region_field": "region",
                    "heatmap_palette": ["#08306B"],
                    "choropleth_palette": ["#1D70B8"],
                    "kpi_metrics": ["sum"],
                    "dashboard_layout": ["metric"],
                },
            },
            "metadata": {
                "storage": {
                    "registry": str(tmp_path / "metadata" / "registry"),
                    "exports": str(tmp_path / "metadata" / "exports"),
                },
                "policy": {
                    "default_license": "CC BY 4.0",
                    "default_publisher": "Demo",
                    "default_contact": {
                        "name": "Zespół",
                        "email": "opendata@example.gov",
                    },
                    "default_accrual_periodicity": "P1M",
                    "default_spatial": "PL",
                    "default_language": "pl",
                    "keyword_strategy": ["demo"],
                    "theme_taxonomy": ["DEMOGRAFIA"],
                    "auto_publish_jsonld": True,
                    "default_temporal_start": "2020-01-01",
                    "default_temporal_end": None,
                },
            },
            "reports": {
                "output_dir": str(tmp_path / "reports"),
                "formats": ["html", "pdf"],
                "template": {
                    "html": str(tmp_path / "templates" / "report.html"),
                    "title_prefix": "Raport",
                    "include_styles": True,
                },
                "include_visualization_summary": True,
                "attach_jsonld": True,
                "include_audit_trail": True,
                "authoring": {
                    "prepared_by": "Biuro Open Data",
                    "contact_email": "reports@example.gov",
                },
            },
        }
    )


def _build_dataset_metadata() -> DatasetMetadata:
    now = datetime.utcnow()
    return DatasetMetadata(
        dataset=DatasetReference(dataset_id="dataset"),
        title="Populacja",
        description="Raport demograficzny",
        license="CC BY 4.0",
        keywords=["demo"],
        themes=["DEMOGRAFIA"],
        contact_name="Zespół",
        contact_email="opendata@example.gov",
        accrual_periodicity="P1M",
        spatial="PL",
        language="pl",
        fields=[],
        distributions=[],
        issued=now,
        modified=now,
    )


def _build_visualization(tmp_path: Path) -> ReportVisualization:
    chart_path = tmp_path / "visualizations" / "chart.png"
    chart_path.parent.mkdir(parents=True, exist_ok=True)
    chart_path.write_bytes(b"PNG")
    summary_path = tmp_path / "visualizations" / "chart-summary.json"
    summary_path.write_text(json.dumps({"series": "population"}, ensure_ascii=False), encoding="utf-8")
    product = VisualizationProduct(
        dataset=DatasetReference(dataset_id="dataset"),
        chart_type="line",
        files=[chart_path],
        series=["population"],
        generated_at=datetime.utcnow(),
        summary_path=summary_path,
        message=None,
    )
    return ReportVisualization(product=product, embed_summary=True)


def _build_transformation_report() -> TransformationReport:
    now = datetime.utcnow()
    step = TransformationStepStatus(operation="filter_rows", status="applied", message="Odfiltrowano dane sprzed 2020")
    return TransformationReport(
        dataset=DatasetReference(dataset_id="dataset"),
        rows_in=100,
        rows_out=80,
        columns=[],
        visualization_hints=[VisualizationHint(chart_type="line", confidence=0.9, reason="Dane czasowe")],
        preview_path="build/preview/dataset-transformed.json",
        started_at=now,
        finished_at=now,
        applied_steps=[step],
        message=None,
    )


def test_report_service_generates_files(tmp_path: Path) -> None:
    profile = _build_profile(tmp_path)
    template_path = Path(profile.report_settings.template.html)
    template_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.write_text(
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>{{TITLE}}</title>{{STYLES}}</head><body>{{BODY}}</body></html>",
        encoding="utf-8",
    )

    jsonld_path = tmp_path / "metadata" / "exports" / "dataset.jsonld"
    jsonld_path.parent.mkdir(parents=True, exist_ok=True)
    jsonld_path.write_text(json.dumps({"@id": "dataset"}, ensure_ascii=False), encoding="utf-8")

    report_request = ReportRequest(
        dataset=_build_dataset_metadata(),
        transformation=_build_transformation_report(),
        visualizations=[_build_visualization(tmp_path)],
        jsonld_paths=[jsonld_path],
        audit_entries=["2024-05-01T10:00Z: dataset published"],
        notes="Raport kontrolny",
    )

    service = build_report_service(profile)
    product = service.generate(report_request)

    generated_files = [path for path in product.files if path.exists()]
    assert len(generated_files) == 2  # HTML + PDF
    html_file = next(path for path in generated_files if path.suffix == ".html")
    html_content = html_file.read_text(encoding="utf-8")
    assert "Raport:" in html_content
    assert "Metadane DCAT-AP" in html_content

    attachment_names = sorted(path.name for path in product.attachments)
    assert "chart-summary.json" in attachment_names
    assert "dataset.jsonld" in attachment_names
    assert any(name.endswith("-audit.txt") for name in attachment_names)
    assert product.message is None


def test_report_service_pdf_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    profile = _build_profile(tmp_path)
    # Brak szablonu wymusi użycie domyślnego HTML
    request = ReportRequest(
        dataset=_build_dataset_metadata(),
        transformation=None,
        visualizations=[],
        jsonld_paths=[],
        audit_entries=[],
    )

    service = ReportService(profile.report_settings)

    original_write = service._write_minimal_pdf

    def failing_write(path: Path, text: str) -> None:  # type: ignore[override]
        raise RuntimeError("Renderer failure")

    monkeypatch.setattr(service, "_write_minimal_pdf", failing_write)
    product = service.generate(request)

    pdf_files: List[Path] = [path for path in product.files if path.suffix == ".pdf"]
    assert pdf_files, "PDF file should be generated in fallback mode"
    assert product.message and "fallback" in product.message.lower()

    # Przywracamy oryginalną metodę, aby inne testy mogły korzystać
    monkeypatch.setattr(service, "_write_minimal_pdf", original_write)
