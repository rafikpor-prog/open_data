"""
Module: tests.test_csv_ingestor
Opis: Testy jednostkowe weryfikujące działanie modułu importu CSV zgodnego z
kontraktami `ingestion-service` i profilami konfiguracji etapu 4.
"""

from __future__ import annotations

import json
from pathlib import Path

from ingestion_service import CSVIngestor, build_default_csv_ingestor
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
        Tworzy profil konfiguracyjny na potrzeby testów. Katalogi zapisów kieruje
        do folderu tymczasowego udostępnionego przez pytest.

    Instructions for laika:
        "Na czas testu przygotowujemy bezpieczne foldery robocze, aby nie mieszać
        w prawdziwych danych." 

    Example:
        ```python
        profile = build_test_profile(tmp_path)
        ```
    Effect for end user:
        Gwarantuje, że testy odtwarzają zachowanie produkcyjne bez ryzyka uszkodzenia
        danych w katalogu roboczym.
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
        sample_size=50,
        preferred_sheets=("Dane",),
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
        allowed_content_types=("text/csv", "application/json"),
        max_file_size_mb=5,
        download_cache=str(tmp_path / "cache"),
        state_registry=str(tmp_path / "state"),
        default_schedule="PT6H",
        verify_tls=True,
        retry_attempts=1,
        retry_backoff_seconds=1,
    )
    return ConfigProfile(
        name="test",
        storage=storage,
        policy=policy,
        xlsx_policy=xlsx_policy,
        json_policy=json_policy,
        remote_policy=remote_policy,
        strict_schema=False,
        description="Profil testowy",
    )


def test_csv_ingestor_generates_preview_and_schema(tmp_path: Path) -> None:
    """
    Technical description:
        Sprawdza, czy CSVIngestor generuje poprawny wynik dla przykładowego pliku.
        Test waliduje liczbę wierszy, strukturę kolumn oraz zapis podglądu JSON.

    Instructions for laika:
        "Wczytujemy testowy plik i upewniamy się, że raport z importu wygląda tak,
        jak oczekuje panel Studio Danych."

    Example:
        ```python
        test_csv_ingestor_generates_preview_and_schema(tmp_path)
        ```
    Effect for end user:
        Zapewnia, że użytkownik otrzyma poprawny podgląd danych i sugestie
        wizualizacji po imporcie CSV.
    """

    profile = build_test_profile(tmp_path)
    ingestor = CSVIngestor(profile)
    job = IngestionJobRequest(
        source_uri="tests/fixtures/sample_population.csv",
        profile_name=profile.name,
        dataset=DatasetReference(dataset_id="population"),
    )

    result = ingestor.run(job)

    assert result.row_count == 3
    assert len(result.columns) == 3
    assert {column.name for column in result.columns} == {"rok", "populacja", "wojewodztwo"}
    assert Path(result.preview_path).exists()

    preview_json = json.loads(Path(result.preview_path).read_text(encoding="utf-8"))
    assert preview_json["dataset_id"] == "population"
    assert len(preview_json["rows"]) == 3

    if result.visualization_hints:
        assert result.visualization_hints[0].chart_type in {"line", "bar"}
    else:
        assert result.message == "**BRAK MOŻLIWEJ WIZUALIZACJI**"


def test_build_default_csv_ingestor_uses_gitops_profile(tmp_path: Path, monkeypatch) -> None:
    """
    Technical description:
        Weryfikuje, że funkcja `build_default_csv_ingestor` potrafi odczytać profil
        z repozytorium GitOps (plik JSON). Monkeypatch ustawia zmienną środowiskową
        `CONFIG_GITOPS_ROOT` na katalog tymczasowy.

    Instructions for laika:
        "Udajemy, że system działa w trybie offline. Sprawdzamy, czy potrafi użyć
        kopii ustawień z dysku i nadal poprawnie zaimportować dane."

    Example:
        ```python
        test_build_default_csv_ingestor_uses_gitops_profile(tmp_path, monkeypatch)
        ```
    Effect for end user:
        Potwierdza, że administrator może polegać na kopiach GitOps przy chwilowych
        problemach z połączeniem z `config-service`.
    """

    gitops_root = tmp_path / "profiles"
    gitops_root.mkdir()
    (gitops_root / "offline.json").write_text(
        json.dumps({
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
                "timezone": "Europe/Warsaw"
            },
            "xlsx_policy": {
                "allowed_extensions": [".xlsx"],
                "max_file_size_mb": 5,
                "sample_size": 50,
                "preferred_sheets": ["Dane"],
                "header_row_index": 1
            },
            "json_policy": {
                "allowed_http_methods": ["GET"],
                "allowed_content_types": ["application/json"],
                "max_payload_mb": 5,
                "max_records": 100,
                "default_pointer": "/results",
                "http_timeout": 5,
                "preview_size": 10
            },
            "strict_schema": False
        }),
        encoding="utf-8",
    )

    monkeypatch.setenv("CONFIG_GITOPS_ROOT", str(gitops_root))

    ingestor = build_default_csv_ingestor("offline")
    job = IngestionJobRequest(
        source_uri="tests/fixtures/sample_population.csv",
        profile_name="offline",
        dataset=DatasetReference(dataset_id="population"),
    )
    result = ingestor.run(job)

    assert result.row_count == 3
    assert Path(result.preview_path).exists()
