"""
Module: ingestion_service.contracts
Opis: Deklaruje modele danych zgodne z kontraktami API `ingestion-service`
z etapu 3A (import), etapu 9 (pipeline transformacji danych) oraz etapu 10
(warstwa metadanych DCAT-AP).
Funkcje i klasy:
- class DatasetReference: identyfikator zbioru danych.
- class IngestionJobRequest: struktura żądania importu.
- class ColumnSchema: opis kolumny wykrytej w trakcie ingestu.
- class VisualizationHint: propozycja wizualizacji na podstawie danych.
- class IngestionResult: wynik importu przekazywany do kolejnych usług.
- class TransformationStepStatus: status pojedynczego kroku transformacji.
- class TransformationReport: raport z pipeline ETL etapu 9.
- class MetadataField / MetadataDistribution / DatasetMetadata: modele
  katalogu DCAT-AP wykorzystywane przez `metadata_service` i WordPress.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass(frozen=True)
class DatasetReference:
    """
    Technical description:
        Reprezentuje identyfikator zbioru danych zgodnie z DCAT-AP. Zawiera pole
        `dataset_id` oraz opcjonalne `resource_id` (dla konkretnej dystrybucji).

    Instructions for laika:
        "To etykieta mówiąca, którego zbioru danych dotyczy import – podobnie jak
        numer katalogowy książki w bibliotece."

    Example:
        ```python
        DatasetReference(dataset_id="population", resource_id="2024-Q1")
        ```
    Effect for end user:
        Dzięki jednoznacznemu identyfikatorowi dane w panelu Studio Danych
        łączą się z opisem metadanych i mogą być publikowane na portalu.
    """

    dataset_id: str
    resource_id: Optional[str] = None


@dataclass(frozen=True)
class IngestionJobRequest:
    """
    Technical description:
        Odzwierciedla payload `POST /ingestion/v1/jobs` dla źródła CSV. Pola
        `source_uri`, `profile_name` i `dataset` umożliwiają powiązanie importu z
        konfiguracją oraz rejestrem metadanych. `options` przechowuje parametry
        dodatkowe (np. wymuszenie separatora).

    Instructions for laika:
        "To formularz, który wypełnia system, gdy prosisz o zaimportowanie pliku.
        Wskazujesz ścieżkę do pliku, nazwę profilu i zbiór danych, a reszta dzieje
        się automatycznie."

    Example:
        ```python
        IngestionJobRequest(
            source_uri="tests/fixtures/sample_population.csv",
            profile_name="dev",
            dataset=DatasetReference(dataset_id="population")
        )
        ```
    Effect for end user:
        Zapewnia, że import wykonuje się w sposób zgodny ze standardami i trafia
        do odpowiedniego zbioru danych w katalogu.
    """

    source_uri: str
    profile_name: str
    dataset: DatasetReference
    options: Dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ColumnSchema:
    """
    Technical description:
        Przechowuje metadane kolumny wykrytej podczas importu CSV. Pola `name`,
        `data_type`, `nullable` i `example` są zgodne z kontraktem `metadata-service`
        i przygotowują dane do rejestru DCAT-AP.

    Instructions for laika:
        "Dla każdej kolumny zapisujemy jej nazwę, typ (np. liczba, tekst) oraz
        przykład wartości. Dzięki temu w katalogu danych od razu wiesz, co oznacza
        dana kolumna."

    Example:
        ```python
        ColumnSchema(name="population", data_type="integer", nullable=False, example="12345")
        ```
    Effect for end user:
        Ułatwia zrozumienie struktury danych i automatyczne budowanie formularzy
        w Studio Danych oraz wtyczce WordPress.
    """

    name: str
    data_type: str
    nullable: bool
    example: Optional[str]


@dataclass(frozen=True)
class VisualizationHint:
    """
    Technical description:
        Opisuje propozycję wizualizacji generowaną przez `ingestion-service` i
        przekazywaną do `visualization-service`. Pola `chart_type`, `confidence`
        i `reason` wspierają heurystyki doboru wykresu.

    Instructions for laika:
        "To sugestia wykresu – np. 'wykres liniowy pasuje najlepiej', wraz z
        uzasadnieniem, dlaczego system tak uważa."

    Example:
        ```python
        VisualizationHint(chart_type="line", confidence=0.8, reason="Wykryto kolumnę czasu i wartości liczbowe")
        ```
    Effect for end user:
        Przyspiesza tworzenie wizualizacji i raportów, oferując gotowe propozycje
        zgodne ze standardami dane.gov.pl.
    """

    chart_type: str
    confidence: float
    reason: str


@dataclass(frozen=True)
class IngestionResult:
    """
    Technical description:
        Reprezentuje wynik importu, który trafia na kolejkę `ingestion.job.completed`.
        Zawiera referencję do zbioru danych, wykrytą strukturę kolumn, liczbę
        wierszy oraz listę sugestii wizualizacji. Pole `preview_path` wskazuje lokalizację
        zapisanego podglądu CSV.

    Instructions for laika:
        "Po zakończeniu importu otrzymujemy paczkę informacji: ile było wierszy,
        jakie kolumny znaleziono i jakie wykresy system poleca. Jeśli nie ma żadnej
        propozycji, pojawi się komunikat **BRAK MOŻLIWEJ WIZUALIZACJI**."

    Example:
        ```python
        result = IngestionResult(
            dataset=DatasetReference(dataset_id="population"),
            row_count=120,
            columns=[ColumnSchema(name="year", data_type="integer", nullable=False, example="2020")],
            visualization_hints=[VisualizationHint(chart_type="line", confidence=0.9, reason="Dane czasowe")],
            preview_path="/data/preview/population.csv",
            message=None
        )
        ```
    Effect for end user:
        Administrator widzi klarowny raport z importu i może jednym kliknięciem
        przejść do wizualizacji lub publikacji danych.
    """

    dataset: DatasetReference
    row_count: int
    columns: List[ColumnSchema]
    visualization_hints: List[VisualizationHint]
    preview_path: str
    started_at: datetime
    finished_at: datetime
    message: Optional[str] = None


@dataclass(frozen=True)
class TransformationStepStatus:
    """
    Technical description:
        Reprezentuje status pojedynczego kroku transformacji danych.
        Przechowuje nazwę operacji (`operation`), status (`applied`,
        `skipped`, `failed`) oraz opcjonalną wiadomość opisującą wynik.

    Instructions for laika:
        "To notatka do każdego kroku przeróbki danych. Widzisz, które kroki
        się udały, które zostały pominięte, a jeśli coś poszło nie tak –
        dostajesz krótkie wyjaśnienie."

    Example:
        ```python
        TransformationStepStatus(operation="filter_rows", status="applied", message="Usunięto 5 wierszy")
        ```
    Effect for end user:
        Administrator ma przejrzysty dziennik działań, co zwiększa audytowalność
        procesu ETL i zgodność z wymaganiami dane.gov.pl.
    """

    operation: str
    status: str
    message: Optional[str] = None


@dataclass(frozen=True)
class TransformationReport:
    """
    Technical description:
        Raport generowany po wykonaniu pipeline'u transformacji (etap 9).
        Zawiera referencję do zbioru danych, liczbę wierszy wejściowych i
        wyjściowych, opis kolumn po transformacji, sugestie wizualizacji,
        ścieżkę do podglądu danych oraz listę kroków z ich statusami.

    Instructions for laika:
        "Po przeróbce danych otrzymujesz raport, który mówi: ile wierszy
        zostało, jakie kolumny powstały, gdzie znajdziesz podgląd i jakie
        wykresy system poleca."

    Example:
        ```python
        TransformationReport(
            dataset=DatasetReference(dataset_id="population"),
            rows_in=100,
            rows_out=80,
            columns=[ColumnSchema(name="year", data_type="integer", nullable=False, example="2020")],
            visualization_hints=[VisualizationHint(chart_type="line", confidence=0.9, reason="Oś czasu")],
            preview_path="build/preview/population-transformed.json",
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            applied_steps=[TransformationStepStatus(operation="filter_rows", status="applied", message="Usunięto stare dane")],
            message=None,
        )
        ```
    Effect for end user:
        Zapewnia gotowy materiał do publikacji i wizualizacji oraz potwierdza,
        że wszystkie kroki transformacji przebiegły zgodnie z polityką
        bezpieczeństwa i audytu.
    """

    dataset: DatasetReference
    rows_in: int
    rows_out: int
    columns: List[ColumnSchema]
    visualization_hints: List[VisualizationHint]
    preview_path: str
    started_at: datetime
    finished_at: datetime
    applied_steps: List[TransformationStepStatus]
    message: Optional[str] = None


@dataclass(frozen=True)
class MetadataField:
    """
    Technical description:
        Reprezentuje pojedyncze pole w schemacie datasetu DCAT-AP. Zawiera
        nazwę kolumny, typ danych, informację czy pole jest wymagane, a także
        jednostkę miary i przykładową wartość.

    Instructions for laika:
        "To opis kolumny w katalogu – widzisz nazwę, typ (np. liczba, tekst)
        oraz przykład, żeby łatwiej zrozumieć dane." 

    Example:
        ```python
        MetadataField(
            name="population",
            data_type="integer",
            required=True,
            unit="osoby",
            example="12500",
        )
        ```
    Effect for end user:
        Katalog danych w Studio Danych i WordPressie prezentuje czytelne opisy
        pól, co zwiększa zrozumienie datasetów zgodnie z wymaganiami dane.gov.pl.
    """

    name: str
    data_type: str
    required: bool
    unit: Optional[str]
    example: Optional[str]


@dataclass(frozen=True)
class MetadataDistribution:
    """
    Technical description:
        Opisuje dystrybucję datasetu (plik, API, podgląd). Pola `identifier`,
        `access_url`, `format` i `updated_at` umożliwiają publikację informacji
        zgodnych z DCAT-AP i kontrolę wersji plików.

    Instructions for laika:
        "To wpis o tym, skąd pobierzesz dane – adres pliku lub API oraz kiedy
        został zaktualizowany." 

    Example:
        ```python
        MetadataDistribution(
            identifier="population-preview",
            access_url="https://example.gov/datasets/population.json",
            format="application/json",
            updated_at=datetime.utcnow(),
        )
        ```
    Effect for end user:
        Użytkownicy portalu otrzymują gotowe linki do pobrania danych wraz z
        formatem i datą aktualizacji.
    """

    identifier: str
    access_url: str
    format: str
    updated_at: datetime


@dataclass(frozen=True)
class DatasetMetadata:
    """
    Technical description:
        Gromadzi komplet metadanych DCAT-AP: identyfikator datasetu,
        tytuł, opis, licencję, słowa kluczowe, tematy, informacje kontaktowe,
        częstotliwość aktualizacji oraz listę pól i dystrybucji.

    Instructions for laika:
        "To pełny opis zbioru. Dzięki niemu katalog i WordPress wiedzą, jak
        zaprezentować dane i jakiej licencji użyć." 

    Example:
        ```python
        DatasetMetadata(
            dataset=DatasetReference(dataset_id="population"),
            title="Populacja województw",
            description="Zestawienie liczby mieszkańców",
            license="CC BY 4.0",
            keywords=["demografia", "populacja"],
            themes=["DEMOGRAFIA"],
            contact_name="Zespół Open Data",
            contact_email="opendata@example.gov",
            accrual_periodicity="P1M",
            spatial="PL",
            language="pl",
            fields=[],
            distributions=[],
            issued=datetime.utcnow(),
            modified=datetime.utcnow(),
        )
        ```
    Effect for end user:
        Zapewnia spójny opis datasetów publikowanych w katalogu oraz przez
        wtyczkę WordPress – zgodny z DCAT-AP i wymaganiami API BDL.
    """

    dataset: DatasetReference
    title: str
    description: str
    license: str
    keywords: List[str]
    themes: List[str]
    contact_name: str
    contact_email: str
    accrual_periodicity: str
    spatial: Optional[str]
    language: Optional[str]
    fields: List[MetadataField]
    distributions: List[MetadataDistribution]
    issued: datetime
    modified: datetime
