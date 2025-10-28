"""
Module: report_service.models
Opis: Definiuje modele danych wykorzystywane przez generator raportów (Etap 15).
Funkcje i klasy:
- class ReportVisualization: opis pojedynczej wizualizacji dołączanej do raportu.
- class ReportRequest: zestaw danych wejściowych wymaganych do wygenerowania
  raportu HTML/PDF.
- class ReportProduct: wynik pracy generatora z listą plików i statusem.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

from ingestion_service.contracts import DatasetMetadata, TransformationReport
from visualization_service.models import VisualizationProduct


@dataclass(frozen=True)
class ReportVisualization:
    """
    Technical description:
        Reprezentuje pojedynczą wizualizację dołączaną do raportu. Zawiera
        obiekt `VisualizationProduct` (pliki PNG/PDF, opcjonalny raport JSON)
        oraz flagę `embed_summary`, która określa czy raport powinien wstawić
        dane z pliku `*-summary.json` (Etap 14).

    Instructions for laika:
        "To opis wykresu, który ma trafić do raportu. Przechowuje pliki z
        obrazkiem i informację, czy dodać tabelkę z danymi."

    Example:
        ```python
        item = ReportVisualization(product=visualization_product, embed_summary=True)
        ```

    Effect for end user:
        Gwarantuje, że raport zawiera wszystkie wybrane wykresy wraz z dodatkowymi
        opisami, dzięki czemu odbiorca widzi pełny kontekst danych.
    """

    product: VisualizationProduct
    embed_summary: bool = True


@dataclass(frozen=True)
class ReportRequest:
    """
    Technical description:
        Zbiera wszystkie dane wejściowe potrzebne do wygenerowania raportu.
        Zawiera metadane DCAT-AP (`DatasetMetadata`), opcjonalny raport
        transformacji (`TransformationReport`), listę wizualizacji,
        ścieżki do eksportów JSON-LD oraz skrócony dziennik audytu.

    Instructions for laika:
        "To paczka informacji, którą przekazujesz generatorowi raportów:
        opis zbioru, listę wykresów i dodatkowe pliki."

    Example:
        ```python
        request = ReportRequest(
            dataset=dataset_metadata,
            transformation=transformation_report,
            visualizations=[ReportVisualization(product=viz_product)],
            jsonld_paths=[Path("build/metadata/exports/dataset.jsonld")],
            audit_entries=["2024-05-01T10:00Z: dataset published"],
            notes="Raport przygotowany dla ministerstwa",
        )
        ```

    Effect for end user:
        Administrator przekazuje jeden obiekt do generatora i otrzymuje kompletny
        dokument – nie musi ręcznie kopiować danych między modułami.
    """

    dataset: DatasetMetadata
    transformation: Optional[TransformationReport]
    visualizations: Sequence[ReportVisualization]
    jsonld_paths: Sequence[Path]
    audit_entries: Sequence[str]
    notes: Optional[str] = None


@dataclass(frozen=True)
class ReportProduct:
    """
    Technical description:
        Reprezentuje wynik działania `ReportService`. Pola `files` i
        `attachments` zawierają ścieżki do wygenerowanych raportów oraz
        dodatkowych plików (np. JSON-LD). Pole `message` informuje o użyciu
        trybu fallback (np. zastępczy PDF), a `generated_at` zapisuje czas
        utworzenia raportu.

    Instructions for laika:
        "To rezultat generatora – lista gotowych dokumentów i załączników,
        wraz z krótką informacją, czy wszystko poszło zgodnie z planem."

    Example:
        ```python
        product = ReportProduct(
            files=[Path("build/reports/population-report.html")],
            attachments=[Path("build/metadata/exports/population.jsonld")],
            generated_at=datetime.utcnow(),
            message=None,
        )
        ```

    Effect for end user:
        Studio Danych i WordPress mogą bezpośrednio opublikować raport,
        ponieważ wszystkie potrzebne pliki i komunikaty znajdują się w jednym
        obiekcie zwrotnym.
    """

    files: Sequence[Path]
    attachments: Sequence[Path]
    generated_at: datetime
    message: Optional[str]
