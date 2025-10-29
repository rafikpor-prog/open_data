"""
Module: ingestion_service.csv_ingestor
Opis: Implementuje import CSV zgodny z kontraktami `ingestion-service` i profilami
konfiguracji z `config-service` (Etap 4 planu rozwoju).
Funkcje i klasy:
- function sniff_dialect: autodetekcja separatora i struktury CSV.
- function infer_column_type: heurystyczna klasyfikacja typu kolumny.
- class CSVIngestor: silnik importu CSV zapisujący metadane i podglądy.
- function build_default_csv_ingestor: helper do uruchamiania w CLI/testach.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from .config_client import resolve_profile
from .contracts import (
    ColumnSchema,
    DatasetReference,
    IngestionJobRequest,
    IngestionResult,
    VisualizationHint,
)
from .profile import ConfigProfile


def sniff_dialect(sample: str, allowed_separators: Sequence[str]) -> csv.Dialect:
    """
    Technical description:
        Wykorzystuje `csv.Sniffer` do wykrycia separatora, cudzysłowów i formatu
        CSV. Wynik jest ograniczony do separatorów określonych w polityce profilu.
        Jeśli Sniffer wybierze niedozwolony separator, funkcja wybiera pierwszy
        z listy `allowed_separators` i tworzy dialekt zastępczy.

    Instructions for laika:
        "Patrzymy na kilka pierwszych wierszy pliku i sprawdzamy, czym są
        oddzielone wartości (przecinek, średnik, tabulator). Jeśli wykryjemy
        dziwny separator, użyjemy tego, który administrator zatwierdził w profilu."

    Example:
        ```python
        dialect = sniff_dialect(sample_text, [",", ";"])
        ```
    Effect for end user:
        Zapewnia poprawne wczytanie plików CSV zgodnie ze standardami dane.gov.pl,
        niezależnie od sposobu przygotowania przez instytucję źródłową.
    """

    sniffer = csv.Sniffer()
    try:
        detected = sniffer.sniff(sample, delimiters="".join(allowed_separators))
        if detected.delimiter not in allowed_separators:
            raise ValueError("Unsupported delimiter")
        return detected
    except Exception:
        class FallbackDialect(csv.Dialect):
            delimiter = allowed_separators[0]
            quotechar = '"'
            doublequote = True
            skipinitialspace = True
            lineterminator = "\n"
            quoting = csv.QUOTE_MINIMAL

        return FallbackDialect()


def infer_column_type(values: Iterable[str]) -> Tuple[str, bool, str]:
    """
    Technical description:
        Analizuje próbkę wartości kolumny i heurystycznie ustala typ danych.
        Wspierane typy: `integer`, `decimal`, `date`, `datetime`, `boolean`, `string`.
        Funkcja zwraca krotkę `(typ, nullable, example)` zgodną z kontraktem
        `ColumnSchema`.

    Instructions for laika:
        "Patrzymy na kilkanaście wartości w kolumnie i zgadujemy, czy to liczby,
        daty czy tekst. Dzięki temu panel automatycznie opisuje dane."

    Example:
        ```python
        data_type, nullable, example = infer_column_type(["1", "2", "3"])
        ```
    Effect for end user:
        Automatycznie opisane kolumny przyspieszają publikację i spełniają wymogi
        DCAT-AP bez ręcznego wpisywania typów przez administratora.
    """

    values_list = list(values)
    cleaned_values: List[str] = [value.strip() for value in values_list if value.strip() != ""]
    if not cleaned_values:
        return "string", True, ""

    nullable = len(cleaned_values) < len(values_list)

    lowered = {value.lower() for value in cleaned_values}
    if lowered <= {"true", "false", "0", "1", "tak", "nie"}:
        return "boolean", nullable, cleaned_values[0]

    try:
        ints = [int(value) for value in cleaned_values]
        return "integer", nullable, str(ints[0])
    except ValueError:
        pass

    try:
        floats = [float(value.replace(",", ".")) for value in cleaned_values]
        return "decimal", nullable, str(floats[0])
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            datetime.strptime(cleaned_values[0], fmt)
            if "T" in fmt:
                return "datetime", nullable, cleaned_values[0]
            return "date", nullable, cleaned_values[0]
        except ValueError:
            continue

    return "string", nullable, cleaned_values[0]


class CSVIngestor:
    """
    Technical description:
        Realizuje import CSV zgodnie z kontraktami API `ingestion-service`.
        Obsługuje walidację wielkości pliku, autodetekcję separatora, budowę
        schematu kolumn i zapis podglądu danych. Wynik wysyła w strukturze
        `IngestionResult`, gotowej do publikacji zdarzenia `ingestion.job.completed`.

    Instructions for laika:
        "To silnik, który bierze plik CSV, sprawdza czy jest zgodny z zasadami,
        wylicza opis kolumn i zapisuje krótki podgląd. Na końcu zwraca raport,
        który widzisz w panelu Studio Danych."

    Example:
        ```python
        ingestor = CSVIngestor(resolve_profile("dev"))
        job = IngestionJobRequest(
            source_uri="tests/fixtures/sample_population.csv",
            profile_name="dev",
            dataset=DatasetReference(dataset_id="population")
        )
        result = ingestor.run(job)
        ```
    Effect for end user:
        Pozwala administratorowi w kilka minut przygotować zbiór danych do publikacji
        i wizualizacji, spełniając przy tym standardy dane.gov.pl oraz API BDL.
    """

    def __init__(self, profile: ConfigProfile) -> None:
        self._profile = profile
        self._landing_path = Path(profile.storage.landing)
        self._schema_path = Path(profile.storage.schema_registry)
        self._preview_path = Path(profile.storage.preview)
        self._landing_path.mkdir(parents=True, exist_ok=True)
        self._schema_path.mkdir(parents=True, exist_ok=True)
        self._preview_path.mkdir(parents=True, exist_ok=True)

    def run(self, job: IngestionJobRequest) -> IngestionResult:
        """
        Technical description:
            Główna operacja importu CSV. Kroki:
            1. Walidacja wielkości pliku i kodowania.
            2. Autodetekcja separatora (`sniff_dialect`).
            3. Analiza nagłówków i próbek wierszy.
            4. Zapis surowego pliku i podglądu (JSON).
            5. Budowa schematu kolumn i sugestii wizualizacji.

        Instructions for laika:
            "Wskazujesz plik i profil, a funkcja robi całą resztę: sprawdza plik,
            opisuje kolumny i tworzy propozycje wykresów."

        Example:
            ```python
            result = CSVIngestor(resolve_profile("dev")).run(job)
            ```
        Effect for end user:
            Generuje kompletny raport importu, który może być od razu użyty do
            publikacji danych i wizualizacji.
        """

        source_path = Path(job.source_uri)
        if not source_path.exists():
            raise FileNotFoundError(f"Plik {source_path} nie istnieje")

        file_size_mb = source_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self._profile.policy.max_file_size_mb:
            raise ValueError("Przekroczono maksymalny rozmiar pliku CSV")

        raw_content = source_path.read_text(encoding=job.options.get("encoding", self._profile.policy.default_encoding))
        sample = "\n".join(raw_content.splitlines()[: self._profile.policy.sample_size])
        dialect = sniff_dialect(sample, self._profile.policy.allowed_separators)

        reader = csv.reader(raw_content.splitlines(), dialect)
        rows = list(reader)
        if not rows:
            raise ValueError("Plik CSV jest pusty")

        headers = rows[0]
        data_rows = rows[1 : 1 + self._profile.policy.sample_size]
        if self._profile.strict_schema:
            schema_file = self._schema_path / f"{job.dataset.dataset_id}.json"
            if not schema_file.exists():
                raise ValueError("Profil wymaga zarejestrowanego schematu, ale go nie znaleziono")

        columns = self._build_columns(headers, data_rows)
        visualization_hints, message = self._build_visualization_hints(columns)
        preview_file = self._write_preview(job, headers, data_rows)
        self._copy_to_landing(source_path)

        now = datetime.utcnow()
        result = IngestionResult(
            dataset=job.dataset,
            row_count=len(rows) - 1,
            columns=columns,
            visualization_hints=visualization_hints,
            preview_path=str(preview_file),
            started_at=now,
            finished_at=now,
            message=message,
        )
        return result

    def _build_columns(self, headers: Sequence[str], rows: Sequence[Sequence[str]]) -> List[ColumnSchema]:
        """
        Technical description:
            Łączy nagłówki z próbką danych i generuje listę `ColumnSchema`. W razie
            brakujących wartości oznacza kolumnę jako `nullable`.

        Instructions for laika:
            "Dla każdej kolumny patrzymy na przykładowe wiersze i opisujemy ją tak,
            by w katalogu od razu było wiadomo, co zawiera."

        Example:
            ```python
            columns = ingestor._build_columns(headers, sample_rows)
            ```
        Effect for end user:
            Zapewnia czytelny opis danych dla panelu Studio Danych i wtyczki WordPress.
        """

        columns: List[ColumnSchema] = []
        for idx, header in enumerate(headers):
            values = [row[idx] for row in rows if len(row) > idx]
            data_type, nullable, example = infer_column_type(values)
            columns.append(
                ColumnSchema(
                    name=header.strip(),
                    data_type=data_type,
                    nullable=nullable,
                    example=example,
                )
            )
        return columns

    def _build_visualization_hints(self, columns: Sequence[ColumnSchema]) -> Tuple[List[VisualizationHint], str | None]:
        """
        Technical description:
            Na podstawie typów kolumn tworzy heurystyczne propozycje wizualizacji.
            Jeśli brak odpowiedniego zestawu kolumn, zwraca komunikat
            **"BRAK MOŻLIWEJ WIZUALIZACJI"**.

        Instructions for laika:
            "Sprawdzamy, czy w danych są liczby i daty. Jeśli tak – proponujemy
            wykres liniowy lub słupkowy. Jeśli nie, pokazujemy komunikat, że nie
            umiemy nic zaproponować."

        Example:
            ```python
            hints, message = ingestor._build_visualization_hints(columns)
            ```
        Effect for end user:
            Pozwala szybko uruchomić wizualizację lub jasno informuje o potrzebie
            przygotowania danych w innej formie.
        """

        numeric_columns = [col for col in columns if col.data_type in {"integer", "decimal"}]
        date_columns = [col for col in columns if col.data_type in {"date", "datetime"}]

        hints: List[VisualizationHint] = []
        if numeric_columns and date_columns:
            hints.append(
                VisualizationHint(
                    chart_type="line",
                    confidence=0.9,
                    reason="Wykryto kolumnę czasu i wartości liczbowe",
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
        job: IngestionJobRequest,
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
    ) -> Path:
        """
        Technical description:
            Tworzy plik JSON z podglądem danych (pierwsze 20 wierszy) w katalogu
            `preview`. Zapis obejmuje nagłówki, próbkę oraz metadane importu, co
            spełnia wymagania audytu i ułatwia prezentację w Studio Danych.

        Instructions for laika:
            "Zapisujemy małą próbkę danych w formacie JSON, aby panel mógł szybko
            wyświetlić podgląd bez wczytywania całego pliku."

        Example:
            ```python
            preview_path = ingestor._write_preview(job, headers, rows)
            ```
        Effect for end user:
            Panel administratora ładuje podgląd błyskawicznie, co przyspiesza
            zatwierdzanie importu.
        """

        preview_data = {
            "dataset_id": job.dataset.dataset_id,
            "resource_id": job.dataset.resource_id,
            "headers": list(headers),
            "rows": rows[:20],
            "generated_at": datetime.utcnow().isoformat(),
        }
        preview_file = self._preview_path / f"{job.dataset.dataset_id}-{job.profile_name}.json"
        preview_file.write_text(json.dumps(preview_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return preview_file

    def _copy_to_landing(self, source_path: Path) -> None:
        """
        Technical description:
            Kopiuje plik do katalogu landing, zachowując oryginalną nazwę i
            dopisując sygnaturę czasową. Działanie symuluje krok ETL odkładania
            pliku do strefy surowej.

        Instructions for laika:
            "Robimy kopię bezpieczeństwa oryginalnego pliku i odkładamy ją do
            specjalnego folderu, aby zawsze mieć wersję źródłową."

        Example:
            ```python
            ingestor._copy_to_landing(Path("sample.csv"))
            ```
        Effect for end user:
            Spełnia wymagania audytu – administrator może odtworzyć źródłowy plik
            nawet po przetworzeniu danych.
        """

        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        target = self._landing_path / f"{timestamp}-{source_path.name}"
        target.write_bytes(source_path.read_bytes())


def build_default_csv_ingestor(profile_name: str) -> CSVIngestor:
    """
    Technical description:
        Pomocnicza funkcja budująca `CSVIngestor` na podstawie profilu pobranego
        z `config-service`. Używana przez CLI (`python -m ingestion_service`) oraz
        testy jednostkowe.

    Instructions for laika:
        "Zamiast ręcznie tworzyć obiekt i pobierać ustawienia, wywołujesz jedną
        funkcję i od razu dostajesz gotowy silnik importu."

    Example:
        ```python
        ingestor = build_default_csv_ingestor("dev")
        ```
    Effect for end user:
        Przyspiesza uruchomienie importu CSV, ograniczając liczbę kroków konfiguracyjnych.
    """

    profile = resolve_profile(profile_name)
    return CSVIngestor(profile)


if __name__ == "__main__":
    profile_name = os.getenv("ODP_PROFILE", "dev")
    source = os.getenv("ODP_CSV_SOURCE")
    if not source:
        raise SystemExit("Zmienna środowiskowa ODP_CSV_SOURCE jest wymagana")
    job = IngestionJobRequest(
        source_uri=source,
        profile_name=profile_name,
        dataset=DatasetReference(dataset_id=os.getenv("ODP_DATASET_ID", "dataset")),
    )
    ingestor = build_default_csv_ingestor(profile_name)
    result = ingestor.run(job)
    print(json.dumps({
        "dataset": result.dataset.dataset_id,
        "row_count": result.row_count,
        "columns": [column.__dict__ for column in result.columns],
        "visualization_hints": [hint.__dict__ for hint in result.visualization_hints],
        "message": result.message,
        "preview_path": result.preview_path,
    }, ensure_ascii=False, indent=2))
