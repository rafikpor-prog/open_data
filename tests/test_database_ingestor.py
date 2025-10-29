"""
Module: tests.test_database_ingestor
Opis: Testy jednostkowe weryfikujące etap 8 – integrację bazodanową modułu
ingestion-service z wykorzystaniem SQLAlchemy i profili konfiguracji.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from ingestion_service.database_ingestor import (
    DatabaseIngestionRequest,
    DatabaseIngestor,
)
from ingestion_service.contracts import DatasetReference
from ingestion_service.profile import (
    ConfigProfile,
    DatabaseConnection,
    DatabasePolicy,
    IngestionPolicy,
    JsonPolicy,
    RemotePolicy,
    StoragePaths,
    XLSXPolicy,
)


def build_db_profile(tmp_path: Path, db_path: Path) -> ConfigProfile:
    """
    Technical description:
        Buduje kompletny profil konfiguracyjny zawierający definicję połączenia
        SQLite wykorzystywanego w testach. Katalogi zapisu kierowane są do
        katalogu tymczasowego pytest, aby uniknąć efektów ubocznych.

    Instructions for laika:
        "Na potrzeby testu przygotowujemy profil z połączeniem do mini bazy
        SQLite – tak jakby była to prawdziwa baza PostgreSQL czy MySQL."

    Example:
        ```python
        profile = build_db_profile(tmp_path, db_path)
        ```
    Effect for end user:
        Zapewnia, że testy odwzorowują zachowanie produkcyjne bez modyfikacji
        właściwych katalogów roboczych.
    """

    storage = StoragePaths(
        landing=str(tmp_path / "landing"),
        schema_registry=str(tmp_path / "schemas"),
        preview=str(tmp_path / "preview"),
    )
    policy = IngestionPolicy(
        allowed_separators=(',', ';'),
        default_encoding="utf-8",
        max_file_size_mb=10,
        sample_size=50,
        timezone="Europe/Warsaw",
    )
    xlsx_policy = XLSXPolicy(
        allowed_extensions=(".xlsx",),
        max_file_size_mb=10,
        sample_size=50,
        preferred_sheets=("Sheet1",),
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
        max_file_size_mb=5,
        download_cache=str(tmp_path / "cache"),
        state_registry=str(tmp_path / "state"),
        default_schedule="PT24H",
        verify_tls=True,
        retry_attempts=1,
        retry_backoff_seconds=5,
    )
    database_policy = DatabasePolicy(
        allowed_drivers=("sqlite",),
        max_rows=1000,
        default_limit=100,
        metadata_cache=str(tmp_path / "metadata"),
        timezone="Europe/Warsaw",
    )
    database_connection = DatabaseConnection(
        connection_id="sqlite_local",
        url=f"sqlite:///{db_path}",
        driver="sqlite",
        default_schema=None,
        description="Testowa baza SQLite",
        options={},
    )
    return ConfigProfile(
        name="test",
        storage=storage,
        policy=policy,
        xlsx_policy=xlsx_policy,
        json_policy=json_policy,
        remote_policy=remote_policy,
        strict_schema=False,
        description="Profil testowy z bazą danych",
        database_policy=database_policy,
        database_connections={"sqlite_local": database_connection},
    )


def create_sqlite_dataset(db_path: Path) -> None:
    """
    Technical description:
        Tworzy lokalną bazę SQLite wraz z tabelą `population` i przykładowymi
        rekordami wykorzystywanymi w testach.

    Instructions for laika:
        "Budujemy małą tabelę z danymi o populacji, aby sprawdzić, czy importer
        potrafi pobrać dane z bazy."

    Example:
        ```python
        create_sqlite_dataset(db_path)
        ```
    Effect for end user:
        Pozwala przetestować zachowanie modułu bez potrzeby uruchamiania
        pełnowymiarowej bazy PostgreSQL lub MySQL.
    """

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "CREATE TABLE population (year INTEGER, value INTEGER, region TEXT)"
        )
        cursor.executemany(
            "INSERT INTO population (year, value, region) VALUES (?, ?, ?)",
            [
                (2020, 12345, "Mazowieckie"),
                (2021, 12500, "Mazowieckie"),
                (2022, 12650, "Mazowieckie"),
            ],
        )
        conn.commit()
    finally:
        conn.close()


def test_database_ingestor_reads_table(tmp_path: Path) -> None:
    """
    Technical description:
        Weryfikuje, że `DatabaseIngestor` poprawnie pobiera dane z tabeli,
        generuje podgląd oraz propozycje wizualizacji.

    Instructions for laika:
        "Sprawdzamy, czy importer potrafi połączyć się z bazą SQLite, pobrać
        tabelę i przygotować raport tak jak w panelu Studio Danych."

    Example:
        ```python
        test_database_ingestor_reads_table(tmp_path)
        ```
    Effect for end user:
        Zapewnia, że integracja bazodanowa dostarcza komplet informacji (kolumny,
        podgląd, sugestie wykresów) zgodnie z wymaganiami etapu 8.
    """

    db_path = tmp_path / "sample.db"
    create_sqlite_dataset(db_path)
    profile = build_db_profile(tmp_path, db_path)

    ingestor = DatabaseIngestor(profile)
    job = DatabaseIngestionRequest(
        connection_id="sqlite_local",
        profile_name=profile.name,
        dataset=DatasetReference(dataset_id="population"),
        table="population",
        limit=10,
    )

    result = ingestor.run(job)

    assert result.row_count == 3
    assert {column.name for column in result.columns} == {"year", "value", "region"}
    preview_data = json.loads(Path(result.preview_path).read_text(encoding="utf-8"))
    assert preview_data["connection_id"] == "sqlite_local"
    assert len(preview_data["rows"]) == 3

    if result.visualization_hints:
        assert result.visualization_hints[0].chart_type in {"line", "bar"}
    else:
        assert result.message == "**BRAK MOŻLIWEJ WIZUALIZACJI**"


def test_database_ingestor_executes_custom_query(tmp_path: Path) -> None:
    """
    Technical description:
        Sprawdza obsługę niestandardowego zapytania SQL i limitowania wyników
        poprzez `fetchmany`.

    Instructions for laika:
        "Uruchamiamy własne zapytanie SQL i upewniamy się, że importer pobierze
        tylko określoną liczbę rekordów."

    Example:
        ```python
        test_database_ingestor_executes_custom_query(tmp_path)
        ```
    Effect for end user:
        Potwierdza, że administrator może stosować własne zapytania (np. z JOIN)
        zachowując kontrolę nad limitami bezpieczeństwa.
    """

    db_path = tmp_path / "sample.db"
    create_sqlite_dataset(db_path)
    profile = build_db_profile(tmp_path, db_path)

    ingestor = DatabaseIngestor(profile)
    job = DatabaseIngestionRequest(
        connection_id="sqlite_local",
        profile_name=profile.name,
        dataset=DatasetReference(dataset_id="population"),
        query="SELECT year, value FROM population ORDER BY year",
        limit=2,
    )

    result = ingestor.run(job)

    assert result.row_count == 2
    assert [column.name for column in result.columns] == ["year", "value"]
