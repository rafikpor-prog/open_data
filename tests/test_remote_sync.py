"""
Module: tests.test_remote_sync
Opis: Testy jednostkowe weryfikujące moduł synchronizacji zdalnych URL (Etap 7).
"""

from __future__ import annotations

import http.server
import json
import socketserver
import threading
from pathlib import Path

import pytest

from ingestion_service import RemoteSourceConfig, RemoteSyncManager
from ingestion_service.contracts import DatasetReference
from ingestion_service.profile import (
    ConfigProfile,
    IngestionPolicy,
    JsonPolicy,
    RemotePolicy,
    StoragePaths,
    XLSXPolicy,
)


class _CSVHandler(http.server.BaseHTTPRequestHandler):
    _BODY = (
        "rok,populacja,wojewodztwo\n"
        "2020,1000,Mazowieckie\n"
        "2021,1200,Mazowieckie\n"
        "2022,1400,Mazowieckie\n"
    ).encode("utf-8")

    def do_GET(self) -> None:  # noqa: N802 - metoda interfejsu BaseHTTPRequestHandler
        self.send_response(200)
        self.send_header("Content-Type", "text/csv")
        self.send_header("Content-Length", str(len(self._BODY)))
        self.end_headers()
        self.wfile.write(self._BODY)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003 - zgodnie z API
        # Wyłączamy logowanie w testach dla czytelności.
        return


@pytest.fixture(name="http_server")
def fixture_http_server() -> str:
    class _ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    server = _ReusableTCPServer(("127.0.0.1", 0), _CSVHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_address[1]}/population.csv"
    yield url
    server.shutdown()
    server.server_close()
    thread.join()


def build_profile(tmp_path: Path) -> ConfigProfile:
    storage = StoragePaths(
        landing=str(tmp_path / "landing"),
        schema_registry=str(tmp_path / "schemas"),
        preview=str(tmp_path / "preview"),
    )
    csv_policy = IngestionPolicy(
        allowed_separators=(",", ";", "\t"),
        default_encoding="utf-8",
        max_file_size_mb=10,
        sample_size=100,
        timezone="Europe/Warsaw",
    )
    xlsx_policy = XLSXPolicy(
        allowed_extensions=(".xlsx",),
        max_file_size_mb=10,
        sample_size=50,
        preferred_sheets=("Dane",),
        header_row_index=1,
    )
    json_policy = JsonPolicy(
        allowed_http_methods=("GET",),
        allowed_content_types=("application/json",),
        max_payload_mb=10,
        max_records=100,
        default_pointer="/results",
        http_timeout=10,
        preview_size=10,
    )
    remote_policy = RemotePolicy(
        allowed_schemes=("https", "http"),
        allowed_content_types=("text/csv", "application/json"),
        max_file_size_mb=10,
        download_cache=str(tmp_path / "cache"),
        state_registry=str(tmp_path / "state"),
        default_schedule="PT12H",
        verify_tls=True,
        retry_attempts=1,
        retry_backoff_seconds=1,
    )
    return ConfigProfile(
        name="test-remote",
        storage=storage,
        policy=csv_policy,
        xlsx_policy=xlsx_policy,
        json_policy=json_policy,
        remote_policy=remote_policy,
        strict_schema=False,
        description="Profil testowy remote",
    )


def test_remote_sync_manager_executes_csv_schedule(tmp_path: Path, http_server: str) -> None:
    profile = build_profile(tmp_path)
    manager = RemoteSyncManager(profile)
    config = RemoteSourceConfig(
        source_uri=http_server,
        format="csv",
        dataset=DatasetReference(dataset_id="population"),
        profile_name=profile.name,
        schedule="PT1H",
        options={"encoding": "utf-8"},
    )

    outcome = manager.run(config, force=True)

    assert outcome.status == "completed"
    assert outcome.result is not None
    assert outcome.result.row_count == 3
    state_file = Path(profile.remote_policy.state_registry) / "population-csv.json"
    assert state_file.exists()
    saved_state = json.loads(state_file.read_text(encoding="utf-8"))
    assert saved_state["status"] == "completed"

    skipped = manager.run(config)
    assert skipped.status == "skipped"
    assert skipped.state is not None
    assert "Pominięto synchronizację" in (skipped.message or "")
