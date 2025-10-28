"""
Module: visualization_service.models
Opis: Deklaruje modele danych używane przez moduł wizualizacji (Etap 13).
Funkcje i klasy:
- class VisualizationRequest: reprezentuje żądanie wygenerowania wizualizacji na podstawie danych.
- class VisualizationProduct: opisuje wygenerowaną wizualizację wraz z metadanymi i ścieżkami eksportów.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Sequence

from ingestion_service.contracts import DatasetReference


@dataclass(frozen=True)
class VisualizationRequest:
    """
    Technical description:
        Opisuje żądanie wygenerowania wizualizacji dla datasetu. Pola obejmują
        identyfikator zbioru (`dataset`), ścieżkę do pliku podglądu danych
        (`preview_path`), typ wykresu (`chart_type`) oraz kolumny wykorzystywane
        do rysowania osi (`x_field`, `y_fields`). Lista `formats` pozwala
        wymusić konkretne formaty eksportu (PNG, JPG, PDF), a `title` i
        `description` są stosowane do podpisów i metadanych.

    Instructions for laika:
        "To formularz mówiący systemowi: z którego zbioru danych chcesz zrobić
        wykres, jakie kolumny mają być na osi poziomej i pionowej oraz gdzie
        leży plik z danymi. Możesz też wybrać format pliku – np. PNG albo PDF."

    Example:
        ```python
        request = VisualizationRequest(
            dataset=DatasetReference(dataset_id="population"),
            preview_path=Path("build/preview/population-transformed.json"),
            chart_type="line",
            x_field="year",
            y_fields=["population"],
            title="Populacja w czasie",
            formats=["png", "pdf"],
        )
        ```
    Effect for end user:
        Administrator lub analityk wskazuje dataset i pola do wizualizacji,
        a system automatycznie tworzy wykres zgodny z wymaganiami dane.gov.pl
        i API BDL.
    """

    dataset: DatasetReference
    preview_path: Path
    chart_type: str
    x_field: str
    y_fields: Sequence[str]
    title: Optional[str] = None
    description: Optional[str] = None
    formats: Optional[Sequence[str]] = None


@dataclass(frozen=True)
class VisualizationProduct:
    """
    Technical description:
        Reprezentuje wynik wygenerowanej wizualizacji. Obejmuje ścieżki do
        plików eksportu (`files`), listę serii danych (`series`), datę
        wygenerowania (`generated_at`) oraz ewentualny komunikat `message`
        zwracany, gdy przygotowanie wykresu nie jest możliwe (np. brak danych
        liczbowych). Pole `chart_type` wskazuje zastosowany typ wizualizacji.

    Instructions for laika:
        "To paczka wynikowa – mówi, gdzie zapisano obrazek lub PDF z wykresem,
        jakie serie danych narysowano i czy wszystko się udało. Jeśli czegoś
        brakuje, zobaczysz komunikat, np. **BRAK MOŻLIWEJ WIZUALIZACJI**."

    Example:
        ```python
        product = VisualizationProduct(
            dataset=DatasetReference(dataset_id="population"),
            chart_type="line",
            files=[Path("build/visualizations/population-line.png")],
            series=["population"],
            generated_at=datetime.utcnow(),
            message=None,
        )
        ```
    Effect for end user:
        Studio Danych, WordPress lub integrator API otrzymują gotowe pliki do
        publikacji wraz z informacją, jakie pola zostały użyte, co skraca czas
        przygotowania raportów i wizualizacji.
    """

    dataset: DatasetReference
    chart_type: str
    files: List[Path]
    series: List[str]
    generated_at: datetime
    message: Optional[str] = None

