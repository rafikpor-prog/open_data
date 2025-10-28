"""
Module: ingestion_service.database_ingestor
Opis: Implementuje etap 8 – integrację bazodanową ingestion-service. Moduł
zapewnia pobieranie danych z relacyjnych baz PostgreSQL, MySQL oraz MS SQL
(kompatybilne drivery SQLAlchemy) z wykorzystaniem profili konfiguracji i
centralnego zarządzania tajemnicami.
Funkcje i klasy:
- class DatabaseIngestionRequest: opis zapytania do bazy (połączenie, tabela lub
  zapytanie SQL, limity, opcje dodatkowe).
- class DatabaseIngestor: główny silnik realizujący połączenie z bazą, pobieranie
  danych, generowanie schematu kolumn, zapis podglądów i tworzenie raportu
  `IngestionResult`.
- function build_default_database_ingestor: helper do tworzenia instancji na
  podstawie profilu z `config-service`.
"""

from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

try:  # pragma: no cover - fallback obsługi importu
    from sqlalchemy import MetaData, Table, create_engine, select, text
    from sqlalchemy.engine import Engine
except ModuleNotFoundError:  # pragma: no cover - środowisko bez SQLAlchemy
    MetaData = Table = create_engine = select = text = None  # type: ignore
    Engine = Any  # type: ignore

from .config_client import resolve_profile
from .contracts import ColumnSchema, DatasetReference, IngestionResult, VisualizationHint
from .csv_ingestor import infer_column_type
from .profile import ConfigProfile, DatabaseConnection, DatabasePolicy


@dataclass(frozen=True)
class DatabaseIngestionRequest:
    """
    Technical description:
        Reprezentuje ładunek `POST /ingestion/v1/jobs` dla źródeł bazodanowych.
        Pola `connection_id`, `table`/`query`, `columns`, `filters` i `limit`
        umożliwiają zdefiniowanie sposobu pobrania danych, a `options` pozwala na
        przekazanie dodatkowych parametrów (np. `order_by`, `snapshot_at`).

    Instructions for laika:
        "To formularz importu z bazy danych. Wskazujesz nazwę połączenia,
        ewentualnie tabelę i warunki filtrowania. System sam pobierze dane i
        przygotuje raport."

    Example:
        ```python
        request = DatabaseIngestionRequest(
            connection_id="analytics_pg",
            profile_name="dev",
            dataset=DatasetReference(dataset_id="population"),
            table="public.population",
            columns=["year", "value", "region"],
            limit=500,
        )
        ```
    Effect for end user:
        Administrator może jednym kliknięciem zaciągnąć dane z hurtowni lub
        systemu transakcyjnego do Studio Danych, zgodnie z limitami bezpieczeństwa
        dane.gov.pl i API BDL.
    """

    connection_id: str
    profile_name: str
    dataset: DatasetReference
    table: Optional[str] = None
    schema: Optional[str] = None
    query: Optional[str] = None
    columns: Optional[Sequence[str]] = None
    filters: Optional[str] = None
    limit: Optional[int] = None
    options: Dict[str, Any] = field(default_factory=dict)


class DatabaseIngestor:
    """
    Technical description:
        Łączy się z bazą danych zdefiniowaną w `ConfigProfile`, wykonuje zapytanie
        lub selekcję tabeli, ogranicza wynik zgodnie z `DatabasePolicy`, generuje
        schemat kolumn i zapisuje podgląd w formacie JSON oraz ekstrakt CSV w
        strefie landing. Wynik zwracany jest jako `IngestionResult`, gotowy do
        publikacji w kolejnych warstwach ETL.

    Instructions for laika:
        "To silnik importu z bazy danych. Sam tworzy połączenie, pobiera tabelę,
        zapisuje kopię do raportu i podpowiada, jakie wykresy możesz przygotować."

    Example:
        ```python
        profile = resolve_profile("dev")
        ingestor = DatabaseIngestor(profile)
        result = ingestor.run(DatabaseIngestionRequest(
            connection_id="sqlite_local",
            profile_name="dev",
            dataset=DatasetReference(dataset_id="population"),
            table="population",
        ))
        ```
    Effect for end user:
        Użytkownik Studio Danych otrzymuje z bazy uporządkowany raport z opisem
        kolumn i propozycjami wizualizacji bez pisania dodatkowego kodu.
    """

    def __init__(self, profile: ConfigProfile) -> None:
        if not profile.database_connections:
            raise ValueError(
                "Profil konfiguracji nie zawiera zdefiniowanych połączeń bazodanowych."
            )
        self._profile = profile
        self._landing_path = Path(profile.storage.landing)
        self._preview_path = Path(profile.storage.preview)
        self._landing_path.mkdir(parents=True, exist_ok=True)
        self._preview_path.mkdir(parents=True, exist_ok=True)
        self._sqlalchemy_available = create_engine is not None and MetaData is not None

    def run(self, job: DatabaseIngestionRequest) -> IngestionResult:
        """
        Technical description:
            Wykonuje zapytanie bazodanowe w oparciu o profil konfiguracji. Kroki:
            1. Pobranie konfiguracji połączenia i polityki limitów.
            2. Utworzenie silnika SQLAlchemy (mTLS/sekrety obsługiwane przez
               ConfigProfile + ConfigService).
            3. Wykonanie zapytania lub selekcji tabeli z ograniczeniem liczby
               wierszy (`DatabasePolicy.max_rows`).
            4. Generowanie schematu kolumn, propozycji wizualizacji i zapis
               podglądu JSON + ekstraktu CSV.

        Instructions for laika:
            "Funkcja łączy się z bazą, pobiera wskazaną tabelę lub wynik zapytania
            i zwraca raport gotowy do publikacji."

        Example:
            ```python
            ingestor = DatabaseIngestor(resolve_profile("dev"))
            result = ingestor.run(DatabaseIngestionRequest(
                connection_id="sqlite_local",
                profile_name="dev",
                dataset=DatasetReference(dataset_id="population"),
                table="population",
            ))
            ```
        Effect for end user:
            Administrator dostaje informację o liczbie wierszy, strukturze kolumn
            oraz ewentualnych sugestiach wizualizacji zgodnych ze standardami
            dane.gov.pl.
        """

        connection = self._resolve_connection(job.connection_id)
        policy = self._profile.database_policy or DatabasePolicy(
            allowed_drivers=(connection.driver,),
            max_rows=10000,
            default_limit=1000,
            metadata_cache=str(self._profile.storage.schema_registry),
            timezone=self._profile.policy.timezone,
        )
        limit = min(job.limit or policy.default_limit, policy.max_rows)

        engine = self._create_engine(connection)
        rows, headers = self._fetch_rows(engine, job, connection, limit)
        columns = self._build_columns(headers, rows)
        hints, message = self._build_visualization_hints(columns)
        preview_file = self._write_preview(job, headers, rows)
        self._write_landing_extract(job, headers, rows)

        now = datetime.utcnow()
        return IngestionResult(
            dataset=job.dataset,
            row_count=len(rows),
            columns=columns,
            visualization_hints=hints,
            preview_path=str(preview_file),
            started_at=now,
            finished_at=now,
            message=message,
        )

    def _resolve_connection(self, connection_id: str) -> DatabaseConnection:
        """
        Technical description:
            Pobiera definicję połączenia z profilu. Rzuca `KeyError`, jeśli
            identyfikator nie istnieje w konfiguracji.

        Instructions for laika:
            "Sprawdzamy, czy w profilu istnieje wybrane połączenie. Jeśli nie –
            zwracamy błąd, aby administrator mógł je dodać."

        Example:
            ```python
            connection = ingestor._resolve_connection("sqlite_local")
            ```
        Effect for end user:
            Minimalizuje ryzyko literówek i zapewnia, że import korzysta z
            zatwierdzonych połączeń audytowanych w Studio Danych.
        """

        if connection_id not in self._profile.database_connections:
            raise KeyError(f"Nie znaleziono połączenia bazodanowego: {connection_id}")
        return self._profile.database_connections[connection_id]

    def _create_engine(self, connection: DatabaseConnection) -> Optional[Engine]:
        """
        Technical description:
            Tworzy instancję `Engine` SQLAlchemy, stosując parametry opcji (np.
            `connect_args`, `pool_pre_ping`).

        Instructions for laika:
            "Budujemy bezpieczne połączenie do bazy na podstawie ustawień z
            profilu – bez potrzeby wpisywania haseł w kodzie."

        Example:
            ```python
            engine = ingestor._create_engine(connection)
            ```
        Effect for end user:
            Zapewnia bezpieczne, powtarzalne połączenie zgodne z polityką IT.
        """

        driver = connection.driver.lower()
        options = dict(connection.options)
        connect_args = options.pop("connect_args", {})

        if driver == "sqlite" and not self._sqlalchemy_available:
            # W trybie bez SQLAlchemy korzystamy z natywnego sqlite3
            return None

        if not self._sqlalchemy_available:
            raise ModuleNotFoundError(
                "Do obsługi połączeń bazodanowych innych niż SQLite wymagane jest SQLAlchemy."
            )

        engine = create_engine(connection.url, connect_args=connect_args, **options)
        return engine

    def _fetch_rows(
        self,
        engine: Optional[Engine],
        job: DatabaseIngestionRequest,
        connection: DatabaseConnection,
        limit: int,
    ) -> tuple[List[Sequence[Any]], List[str]]:
        """
        Technical description:
            Wykonuje zapytanie lub selekcję tabeli przy użyciu SQLAlchemy,
            zapewniając limit rekordów. Dla zapytania tekstowego wykorzystuje
            `fetchmany`, aby nie przekroczyć limitu polityki.

        Instructions for laika:
            "Pobieramy dane z bazy w porcjach tak, aby nie przekroczyć ustalonych
            limitów i nie obciążyć systemu źródłowego."

        Example:
            ```python
            rows, headers = ingestor._fetch_rows(engine, job, connection, 1000)
            ```
        Effect for end user:
            Chroni bazę przed nadmiernym obciążeniem i zapewnia szybki podgląd
            danych w Studio Danych.
        """

        driver = connection.driver.lower()
        if driver == "sqlite" and engine is None:
            return self._fetch_rows_sqlite(job, connection, limit)

        if not self._sqlalchemy_available:
            raise ModuleNotFoundError(
                "Do obsługi tego połączenia wymagane jest zainstalowanie SQLAlchemy."
            )

        with engine.connect() as conn:  # type: ignore[union-attr]
            if job.query:
                statement = text(job.query)
                result = conn.execute(statement)
                rows = result.fetchmany(limit)
                headers = list(result.keys())
                return [tuple(row) for row in rows], headers

            if not job.table:
                raise ValueError("Należy podać nazwę tabeli lub zapytanie SQL.")

            metadata = MetaData()
            schema_name = job.schema or connection.default_schema
            table_name = job.table
            if "." in job.table and not job.schema:
                schema_candidate, table_candidate = job.table.rsplit(".", 1)
                schema_name = schema_candidate
                table_name = table_candidate
            table = Table(
                table_name,
                metadata,
                schema=schema_name,
                autoload_with=conn,
            )
            selected_columns = self._resolve_columns(table, job.columns)
            stmt = select(*selected_columns)
            if job.filters:
                stmt = stmt.where(text(job.filters))
            stmt = stmt.limit(limit)
            result = conn.execute(stmt)
            rows = result.fetchall()
            headers = [col.name for col in selected_columns]
            return [tuple(row) for row in rows], headers

    def _resolve_columns(
        self, table: Table, requested: Optional[Sequence[str]]
    ) -> List[Any]:
        """
        Technical description:
            Zamienia listę nazw kolumn na obiekty SQLAlchemy. Jeżeli lista jest
            pusta, wybiera wszystkie kolumny tabeli z zachowaniem kolejności.

        Instructions for laika:
            "Jeśli nie wskażesz kolumn, system pobierze wszystkie dostępne.
            Możesz też wskazać konkretne nazwy, aby ograniczyć wynik."

        Example:
            ```python
            columns = ingestor._resolve_columns(table, ["year", "value"])
            ```
        Effect for end user:
            Ułatwia przygotowanie raportów zawierających tylko potrzebne dane.
        """

        if not requested:
            return list(table.columns)

        resolved = []
        for column_name in requested:
            if column_name not in table.columns:
                raise KeyError(f"Kolumna {column_name} nie istnieje w tabeli {table.name}.")
            resolved.append(table.columns[column_name])
        return resolved

    def _build_columns(
        self, headers: Sequence[str], rows: List[Sequence[Any]]
    ) -> List[ColumnSchema]:
        """
        Technical description:
            Analizuje wartości kolumn, konwertuje je do tekstu i wykorzystuje
            heurystykę `infer_column_type`, aby określić typ danych i przykładową
            wartość.

        Instructions for laika:
            "Dla każdej kolumny tworzymy opis typu (liczba, tekst, data), żeby w
            katalogu danych od razu było wiadomo, co zawiera."

        Example:
            ```python
            column_schemas = ingestor._build_columns(headers, rows)
            ```
        Effect for end user:
            Zapewnia automatyczne opisy kolumn zgodne z wymaganiami DCAT-AP.
        """

        columns: List[ColumnSchema] = []
        for idx, header in enumerate(headers):
            values = [row[idx] for row in rows if len(row) > idx]
            string_values = ["" if value is None else str(value) for value in values]
            data_type, nullable, example = infer_column_type(string_values)
            columns.append(
                ColumnSchema(
                    name=header,
                    data_type=data_type,
                    nullable=nullable,
                    example=example,
                )
            )
        return columns

    def _build_visualization_hints(
        self, columns: Sequence[ColumnSchema]
    ) -> tuple[List[VisualizationHint], Optional[str]]:
        """
        Technical description:
            Generuje heurystyczne sugestie wykresów identycznie jak moduł CSV –
            preferuje wykres liniowy dla kombinacji data+liczba i słupkowy, gdy
            dostępne są jedynie wartości liczbowe.

        Instructions for laika:
            "Sprawdzamy typy kolumn i proponujemy najbardziej pasujący wykres. Jeśli
            się nie da, pokazujemy komunikat **BRAK MOŻLIWEJ WIZUALIZACJI**."

        Example:
            ```python
            hints, message = ingestor._build_visualization_hints(columns)
            ```
        Effect for end user:
            Przyspiesza pracę analityków – system od razu sugeruje, jak zaprezentować
            dane z bazy.
        """

        numeric_columns = [col for col in columns if col.data_type in {"integer", "decimal"}]
        date_columns = [col for col in columns if col.data_type in {"date", "datetime"}]

        hints: List[VisualizationHint] = []
        if numeric_columns and date_columns:
            hints.append(
                VisualizationHint(
                    chart_type="line",
                    confidence=0.85,
                    reason="Wykryto kolumnę czasu oraz dane liczbowe pobrane z bazy",
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
        job: DatabaseIngestionRequest,
        headers: Sequence[str],
        rows: List[Sequence[Any]],
    ) -> Path:
        """
        Technical description:
            Tworzy plik JSON zawierający podstawowy podgląd danych (do 20 wierszy)
            oraz metadane importu, zgodnie z wymaganiami audytu Studio Danych.

        Instructions for laika:
            "Zapisujemy próbkę danych w czytelnej formie, żeby panel mógł szybko
            wyświetlić podgląd bez łączenia się z bazą."

        Example:
            ```python
            preview_path = ingestor._write_preview(job, headers, rows)
            ```
        Effect for end user:
            Podgląd w panelu ładuje się natychmiast, a administrator może szybko
            zweryfikować poprawność importu.
        """

        preview_data = {
            "dataset_id": job.dataset.dataset_id,
            "resource_id": job.dataset.resource_id,
            "connection_id": job.connection_id,
            "headers": list(headers),
            "rows": [list(row) for row in rows[:20]],
            "generated_at": datetime.utcnow().isoformat(),
        }
        preview_file = self._preview_path / f"{job.dataset.dataset_id}-{job.connection_id}.json"
        preview_file.write_text(json.dumps(preview_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return preview_file

    def _write_landing_extract(
        self,
        job: DatabaseIngestionRequest,
        headers: Sequence[str],
        rows: List[Sequence[Any]],
    ) -> None:
        """
        Technical description:
            Zapisuje wynik zapytania w formacie CSV do katalogu landing z
            sygnaturą czasową – spełnia wymagania audytu i umożliwia późniejsze
            przetwarzanie w pipeline ETL.

        Instructions for laika:
            "Robimy kopię danych pobranych z bazy i odkładamy ją w bezpiecznym
            katalogu, żeby zawsze mieć zapis tego, co zaimportowaliśmy."

        Example:
            ```python
            ingestor._write_landing_extract(job, headers, rows)
            ```
        Effect for end user:
            Umożliwia łatwe ponowne przetworzenie danych oraz spełnia wymagania
            audytu publicznych danych.
        """

        if not rows:
            return
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        landing_file = self._landing_path / f"{timestamp}-{job.dataset.dataset_id}-{job.connection_id}.csv"
        with landing_file.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            for row in rows:
                writer.writerow(row)

    def _fetch_rows_sqlite(
        self,
        job: DatabaseIngestionRequest,
        connection: DatabaseConnection,
        limit: int,
    ) -> tuple[List[Sequence[Any]], List[str]]:
        """
        Technical description:
            Obsługuje import danych z baz SQLite bez użycia SQLAlchemy. Funkcja
            parsuje ścieżkę z URL, wykonuje zapytanie (custom lub wygenerowane) i
            zwraca ograniczony zestaw wierszy wraz z nagłówkami.

        Instructions for laika:
            "Gdy korzystamy z lokalnej bazy SQLite, importer sam otwiera plik
            bazy, uruchamia zapytanie i pobiera tylko tyle wierszy, ile wolno."

        Example:
            ```python
            rows, headers = ingestor._fetch_rows_sqlite(job, connection, 100)
            ```
        Effect for end user:
            Pozwala testować i używać profili bazodanowych nawet w środowiskach
            bez zainstalowanego SQLAlchemy, zachowując te same limity co w
            produkcji.
        """

        db_path = self._sqlite_path_from_url(connection.url)
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            if job.query:
                cursor = conn.execute(job.query)
                rows = cursor.fetchmany(limit)
                headers = [desc[0] for desc in cursor.description]
            else:
                if not job.table:
                    raise ValueError("Należy podać nazwę tabeli lub zapytanie SQL.")
                table_name = job.table.split(".")[-1]
                columns = list(job.columns) if job.columns else self._sqlite_columns(conn, table_name)
                where_clause = f" WHERE {job.filters}" if job.filters else ""
                sql = f"SELECT {', '.join(columns)} FROM {table_name}{where_clause} LIMIT ?"
                cursor = conn.execute(sql, (limit,))
                rows = cursor.fetchall()
                headers = columns

            materialized = [tuple(row[col] for col in headers) for row in rows]
            return materialized, headers

    def _sqlite_columns(self, conn: sqlite3.Connection, table: str) -> List[str]:
        """
        Technical description:
            Pobiera listę kolumn z tabeli SQLite przy użyciu `PRAGMA table_info`.
            Zwracana jest kolejność zdefiniowana w schemacie.

        Instructions for laika:
            "Sprawdzamy, jakie kolumny ma tabela w bazie SQLite, żeby przygotować
            prawidłowy raport."

        Example:
            ```python
            columns = ingestor._sqlite_columns(conn, "population")
            ```
        Effect for end user:
            Zapewnia automatyczne opisy kolumn nawet przy pracy na testowych
            bazach SQLite bez dodatkowej konfiguracji.
        """

        cursor = conn.execute(f"PRAGMA table_info('{table}')")
        rows = cursor.fetchall()
        if not rows:
            raise KeyError(f"Tabela {table} nie istnieje w bazie SQLite.")
        return [row[1] for row in rows]

    def _sqlite_path_from_url(self, url: str) -> str:
        """
        Technical description:
            Konwertuje URL SQLite (np. `sqlite:///tmp/db.sqlite`) na ścieżkę
            plikową używaną przez moduł `sqlite3`.

        Instructions for laika:
            "Tłumaczymy adres połączenia na zwykłą ścieżkę do pliku bazy, aby
            można było go otworzyć."

        Example:
            ```python
            path = ingestor._sqlite_path_from_url("sqlite:///tmp/db.sqlite")
            ```
        Effect for end user:
            Umożliwia użycie tego samego profilu zarówno w środowisku testowym,
            jak i produkcyjnym (gdzie URL może wskazywać na inny nośnik danych).
        """

        prefix = "sqlite:///"
        if url.startswith(prefix):
            return url[len(prefix) :]
        if url.startswith("sqlite://"):
            return url[len("sqlite://") :]
        return url


def build_default_database_ingestor(profile_name: str) -> DatabaseIngestor:
    """
    Technical description:
        Pobiera profil konfiguracji z `config-service` (lub repozytorium GitOps)
        i tworzy gotowy do użycia `DatabaseIngestor`. Funkcja wykorzystywana jest
        przez CLI oraz testy automatyczne.

    Instructions for laika:
        "Wywołujesz jedną funkcję, aby przygotować importer baz danych dla
        wybranego profilu – bez ręcznej konfiguracji."

    Example:
        ```python
        ingestor = build_default_database_ingestor("dev")
        ```
    Effect for end user:
        Przyspiesza start pracy administratora – importer od razu korzysta z
        zatwierdzonych połączeń i limitów.
    """

    profile = resolve_profile(profile_name)
    return DatabaseIngestor(profile)
