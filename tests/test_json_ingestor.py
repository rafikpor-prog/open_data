"""
Module: tests.test_json_ingestor
Opis: Testy jednostkowe weryfikujące moduł importu JSON/API (Etap 6).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from urllib import request

from ingestion_service import JSONIngestor, build_default_json_ingestor
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
        Przygotowuje profil konfiguracji do testów modułu JSON. Wszystkie katalogi
        zapisu kierowane są do przestrzeni tymczasowej udostępnionej przez pytest,
        aby testy nie modyfikowały realnych danych.

    Instructions for laika:
        "Tworzymy testowy zestaw ustawień – wskazujemy foldery oraz zasady, jak
        pobierać dane z API. Dzięki temu test wygląda tak samo jak środowisko
        produkcyjne."

    Example:
        ```python
        profile = build_test_profile(tmp_path)
        ```
    Effect for end user:
        Zapewnia wiarygodne odtworzenie procesu importu JSON/API, co zwiększa
        zaufanie do wyników prezentowanych w Studio Danych.
    """

    storage = StoragePaths(
        landing=str(tmp_path / "landing"),
        schema_registry=str(tmp_path / "schemas"),
        preview=str(tmp_path / "preview"),
    )
    csv_policy = IngestionPolicy(
        allowed_separators=(",", ";", "\t"),
        default_encoding="utf-8",
        max_file_size_mb=5,
        sample_size=100,
        timezone="Europe/Warsaw",
    )
    xlsx_policy = XLSXPolicy(
        allowed_extensions=(".xlsx",),
        max_file_size_mb=5,
        sample_size=25,
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
        default_schedule="PT12H",
        verify_tls=True,
        retry_attempts=1,
        retry_backoff_seconds=1,
    )
    return ConfigProfile(
        name="test-json",
        storage=storage,
        policy=csv_policy,
        xlsx_policy=xlsx_policy,
        json_policy=json_policy,
        remote_policy=remote_policy,
        strict_schema=False,
        description="Profil testowy JSON",
    )


def test_json_ingestor_reads_local_file(tmp_path: Path) -> None:
    """
    Technical description:
        Sprawdza, czy JSONIngestor poprawnie wczytuje lokalny plik JSON, tworzy
        schemat kolumn, zapisuje podgląd i generuje sugestie wizualizacji.

    Instructions for laika:
        "Wczytujemy przykładowy plik JSON tak samo, jak zrobi to administrator w
        Studio Danych, i upewniamy się, że raport jest kompletny."

    Example:
        ```python
        test_json_ingestor_reads_local_file(tmp_path)
        ```
    Effect for end user:
        Potwierdza, że dane z API zapisane lokalnie mogą zostać szybko zaimportowane
        i opisane bez dodatkowej konfiguracji.
    """

    profile = build_test_profile(tmp_path)
    ingestor = JSONIngestor(profile)
    job = IngestionJobRequest(
        source_uri="tests/fixtures/sample_population.json",
        profile_name=profile.name,
        dataset=DatasetReference(dataset_id="population"),
        options={"json_pointer": "/results"},
    )

    result = ingestor.run(job)

    assert result.row_count == 3
    assert {column.name for column in result.columns} == {"rok", "populacja", "wojewodztwo"}
    assert Path(result.preview_path).exists()
    preview_data = json.loads(Path(result.preview_path).read_text(encoding="utf-8"))
    assert preview_data["json_pointer"] == "/results"
    assert len(preview_data["records"]) == 3
    if result.visualization_hints:
        assert result.visualization_hints[0].chart_type in {"line", "bar"}


class DummyResponse:
    """
    Technical description:
        Minimalna implementacja odpowiedzi HTTP do testów. Udostępnia pola
        `status`, `headers` oraz metodę `read`, aby symulować zachowanie
        `urllib.request.urlopen`.

    Instructions for laika:
        "To sztuczna odpowiedź serwera – dzięki niej test udaje, że pobiera dane
        z internetu, choć w rzeczywistości korzysta z przygotowanego ciągu znaków."

    Example:
        ```python
        response = DummyResponse(b"{}")
        ```
    Effect for end user:
        Pozwala bezpiecznie testować integrację z API bez wykonywania prawdziwych
        połączeń sieciowych.
    """

    def __init__(self, payload: bytes, headers: Dict[str, str] | None = None, status: int = 200) -> None:
        self._payload = payload
        self.headers = headers or {}
        self.status = status

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "DummyResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def test_build_default_json_ingestor_fetches_http(monkeypatch, tmp_path: Path) -> None:
    """
    Technical description:
        Weryfikuje, że `build_default_json_ingestor` potrafi wczytać profil z
        repozytorium GitOps i pobrać dane z API przy użyciu symulowanej odpowiedzi
        HTTP.

    Instructions for laika:
        "Udajemy, że łączymy się z API. Sprawdzamy, czy narzędzie potrafi pobrać
        dane i przygotować raport, nawet gdy działa bez prawdziwego internetu."

    Example:
        ```python
        test_build_default_json_ingestor_fetches_http(monkeypatch, tmp_path)
        ```
    Effect for end user:
        Potwierdza, że automatyczna konfiguracja profili i pobieranie z API działają
        w trybie GitOps/CLI.
    """

    payload = {
        "results": [
            {"rok": 2020, "populacja": 12345, "wojewodztwo": "Mazowieckie"},
            {"rok": 2021, "populacja": 12500, "wojewodztwo": "Mazowieckie"}
        ]
    }

    def fake_urlopen(req: Any, data: bytes | None = None, timeout: int | float = 0) -> DummyResponse:
        assert isinstance(req, request.Request)
        assert req.full_url.startswith("https://api.example.gov/population")
        return DummyResponse(
            json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )

    monkeypatch.setattr("ingestion_service.json_ingestor.request.urlopen", fake_urlopen)

    gitops_root = tmp_path / "profiles"
    gitops_root.mkdir()
    (gitops_root / "offline-json.json").write_text(
        json.dumps({
            "name": "offline-json",
            "storage": {
                "landing": str(tmp_path / "landing"),
                "schema_registry": str(tmp_path / "schemas"),
                "preview": str(tmp_path / "preview"),
            },
            "policy": {
                "allowed_separators": [","],
                "default_encoding": "utf-8",
                "max_file_size_mb": 5,
                "sample_size": 50,
                "timezone": "Europe/Warsaw"
            },
            "xlsx_policy": {
                "allowed_extensions": [".xlsx"],
                "max_file_size_mb": 5,
                "sample_size": 25,
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

    ingestor = build_default_json_ingestor("offline-json")
    job = IngestionJobRequest(
        source_uri="https://api.example.gov/population",
        profile_name="offline-json",
        dataset=DatasetReference(dataset_id="population"),
        options={"query_params": json.dumps({"year": 2022})},
    )

    result = ingestor.run(job)

    assert result.row_count == 2
    assert Path(result.preview_path).exists()
