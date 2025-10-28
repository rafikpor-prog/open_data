"""
Module: visualization_service.service
Opis: Implementuje silnik generowania wizualizacji (Etap 13) korzystający z
ustawień profilu konfiguracji oraz plików podglądu danych przygotowanych przez
moduły ingestu i transformacji. Moduł tworzy wykresy PNG/JPG/PDF zgodnie ze
standardami dane.gov.pl i API BDL.
Funkcje i klasy:
- class VisualizationService: główny silnik generowania wykresów.
- function build_visualization_service: helper tworzący usługę na podstawie profilu.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

import matplotlib.pyplot as plt

from ingestion_service.contracts import DatasetReference
from ingestion_service.profile import ConfigProfile, VisualizationSettings
from visualization_service.models import VisualizationProduct, VisualizationRequest


@dataclass(frozen=True)
class _SeriesData:
    """
    Technical description:
        Struktura pomocnicza używana wewnętrznie do przechowywania danych
        liczbowych dla pojedynczej serii wykresu. Zawiera nazwę serii oraz
        listy wartości osi X i Y przygotowane do przekazania do Matplotlib.

    Instructions for laika:
        "To małe pudełko na dane jednego wykresu – przechowuje podpis serii oraz
        listę punktów X i Y, żeby moduł rysujący mógł je łatwo narysować."

    Example:
        ```python
        series = _SeriesData(name="population", x=[2020, 2021], y=[12345, 12650])
        ```
    Effect for end user:
        Uporządkowane dane serii gwarantują, że wykres wygeneruje się poprawnie i
        zachowa kolejność wartości zgodną z API BDL.
    """

    name: str
    x: List[float]
    y: List[float]


class VisualizationService:
    """
    Technical description:
        Odpowiada za generowanie wykresów na podstawie plików podglądu (JSON)
        oraz ustawień `VisualizationSettings`. Obsługuje typy `line`, `bar` i
        `area`, zapisując wyniki w katalogu `output_dir` w formatach PNG/JPG/PDF.
        Zwraca obiekt `VisualizationProduct` zawierający metadane, listę plików
        oraz komunikat w przypadku braku możliwości wizualizacji.

    Instructions for laika:
        "To serce modułu wizualizacji. Dostaje dane oraz informację, jaki wykres
        chcesz zobaczyć, i tworzy gotowe pliki (np. PNG i PDF), które możesz
        pobrać z panelu lub WordPressa. Jeśli danych brakuje – wyświetli
        komunikat **BRAK MOŻLIWEJ WIZUALIZACJI**."

    Example:
        ```python
        service = VisualizationService(profile.visualization_settings)
        product = service.generate(
            VisualizationRequest(
                dataset=DatasetReference(dataset_id="population"),
                preview_path=Path("build/preview/population-transformed.json"),
                chart_type="line",
                x_field="year",
                y_fields=["population"],
            )
        )
        ```
    Effect for end user:
        Administrator otrzymuje gotowy wykres zgodny z kolorystyką i formatami
        zatwierdzonymi w profilu – obraz można od razu opublikować na portalu
        lub w WordPressie.
    """

    def __init__(self, settings: VisualizationSettings) -> None:
        self._settings = settings
        self._output_dir = Path(settings.output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, request: VisualizationRequest) -> VisualizationProduct:
        """
        Technical description:
            Generuje wizualizację na podstawie żądania. Kroki:
            1. Wczytanie danych z pliku preview (obsługa struktur ingestu oraz
               pipeline'u transformacji).
            2. Przygotowanie serii danych zgodnie z parametrami `x_field` oraz
               `y_fields`, z konwersją do wartości liczbowych.
            3. Narysowanie wykresu w Matplotlib z wykorzystaniem palety kolorów
               z profilu oraz zapis do formatów z `request.formats` lub
               ustawień domyślnych.
            4. Zwrócenie `VisualizationProduct` z listą wygenerowanych plików
               lub komunikatem **"BRAK MOŻLIWEJ WIZUALIZACJI"** w razie braku
               danych liczbowych.

        Instructions for laika:
            "Podajesz plik z danymi, nazwę kolumn z liczbami i typ wykresu. Usługa
            tworzy obrazek i PDF, zapisuje je w katalogu wizualizacji i zwraca
            informacje, gdzie je znaleźć. Jeśli danych liczbowych brakuje –
            dostaniesz jasny komunikat."

        Example:
            ```python
            product = service.generate(
                VisualizationRequest(
                    dataset=DatasetReference(dataset_id="population"),
                    preview_path=Path("build/preview/population-transformed.json"),
                    chart_type="line",
                    x_field="year",
                    y_fields=["population"],
                    formats=["png", "pdf"],
                )
            )
            ```
        Effect for end user:
            Panel Studio Danych i WordPress otrzymują gotowe wykresy wraz z
            metadanymi, dzięki czemu publikacja danych trwa kilka sekund.
        """

        rows = self._load_preview_rows(request.preview_path)
        series = self._prepare_series(rows, request.x_field, request.y_fields)
        if not series:
            return VisualizationProduct(
                dataset=request.dataset,
                chart_type=request.chart_type,
                files=[],
                series=[],
                generated_at=datetime.utcnow(),
                message="**BRAK MOŻLIWEJ WIZUALIZACJI**",
            )

        formats = list(request.formats or self._settings.default_formats)
        export_paths = self._render_chart(request, series, formats)
        return VisualizationProduct(
            dataset=request.dataset,
            chart_type=request.chart_type,
            files=export_paths,
            series=[s.name for s in series],
            generated_at=datetime.utcnow(),
            message=None,
        )

    def _load_preview_rows(self, preview_path: Path) -> List[Dict[str, object]]:
        if not preview_path.exists():
            return []
        payload = json.loads(preview_path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            rows = payload.get("rows")
            if isinstance(rows, list) and rows and isinstance(rows[0], dict):
                return [dict(row) for row in rows]
            if isinstance(rows, list) and rows and isinstance(rows[0], list):
                headers = payload.get("headers", [])
                return [dict(zip(headers, row)) for row in rows]
        if isinstance(payload, list):
            return [dict(row) for row in payload if isinstance(row, dict)]
        return []

    def _prepare_series(
        self,
        rows: List[Dict[str, object]],
        x_field: str,
        y_fields: Sequence[str],
    ) -> List[_SeriesData]:
        if not rows:
            return []

        numeric_series: List[_SeriesData] = []
        x_values_raw = [row.get(x_field) for row in rows]
        x_values = _coerce_axis(x_values_raw)
        if not x_values:
            return []

        palette_cycle = _cycle_colors(self._settings.color_palette)
        for field in y_fields[: self._settings.max_series]:
            y_raw = [row.get(field) for row in rows]
            y_values = _coerce_numeric(y_raw)
            if not y_values or len(y_values) != len(x_values):
                continue
            numeric_series.append(
                _SeriesData(name=str(field), x=list(x_values), y=list(y_values))
            )
            next(palette_cycle)  # advance palette for determinism

        return numeric_series

    def _render_chart(
        self,
        request: VisualizationRequest,
        series: Sequence[_SeriesData],
        formats: Sequence[str],
    ) -> List[Path]:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        base_name = f"{request.dataset.dataset_id}-{request.chart_type}-{timestamp}"
        export_paths: List[Path] = []

        fig, ax = plt.subplots(figsize=self._settings.figure_size)
        ax.set_facecolor(self._settings.background_color)

        for idx, data in enumerate(series):
            color = self._settings.color_palette[idx % len(self._settings.color_palette)]
            if request.chart_type == "line":
                ax.plot(data.x, data.y, marker="o", label=data.name, color=color)
            elif request.chart_type == "bar":
                ax.bar([x + idx * 0.1 for x in data.x], data.y, width=0.1, label=data.name, color=color)
            elif request.chart_type == "area":
                ax.fill_between(data.x, data.y, alpha=0.4, label=data.name, color=color)
            else:
                ax.plot(data.x, data.y, marker="o", label=data.name, color=color)

        ax.set_xlabel(request.x_field)
        ax.set_ylabel(", ".join(request.y_fields))
        ax.set_title(request.title or f"Wykres {request.chart_type}")
        ax.grid(True, alpha=0.2)
        ax.legend()

        for export_format in formats:
            safe_format = export_format.lower()
            if safe_format not in {"png", "jpg", "jpeg", "pdf"}:
                continue
            suffix = "jpg" if safe_format in {"jpg", "jpeg"} else safe_format
            target = self._output_dir / f"{base_name}.{suffix}"
            plt.savefig(target, dpi=self._settings.dpi, bbox_inches="tight")
            export_paths.append(target)

        plt.close(fig)
        return export_paths


def build_visualization_service(profile: ConfigProfile) -> VisualizationService:
    """
    Technical description:
        Helper tworzący `VisualizationService` na podstawie ustawień profilu
        (`profile.visualization_settings`). Dzięki temu moduły CLI oraz testy
        mogą szybko skonfigurować usługę bez ręcznego przekazywania parametrów.

    Instructions for laika:
        "Zamiast ręcznie wpisywać wszystkie ustawienia wykresów, wywołaj tę
        funkcję – system sam wczyta kolorystykę, katalog wyjściowy i listę
        formatów z profilu."

    Example:
        ```python
        service = build_visualization_service(profile)
        ```
    Effect for end user:
        Umożliwia szybkie tworzenie wykresów w CLI lub automatycznych procesach
        bez ryzyka pomyłek w konfiguracji.
    """

    return VisualizationService(profile.visualization_settings)


def _coerce_axis(values: Iterable[object]) -> List[float]:
    coerced: List[float] = []
    for value in values:
        if value is None:
            continue
        try:
            coerced.append(float(value))
        except (TypeError, ValueError):
            try:
                coerced.append(float(datetime.fromisoformat(str(value)).timestamp()))
            except Exception:
                return []
    return coerced


def _coerce_numeric(values: Iterable[object]) -> List[float]:
    coerced: List[float] = []
    for value in values:
        if value is None or value == "":
            return []
        try:
            coerced.append(float(value))
        except (TypeError, ValueError):
            return []
    return coerced


def _cycle_colors(palette: Sequence[str]):
    while True:
        for color in palette:
            yield color

