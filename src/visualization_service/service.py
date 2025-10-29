"""
Module: visualization_service.service
Opis: Implementuje silnik generowania wizualizacji (Etapy 13–14) korzystający z
ustawień profilu konfiguracji oraz plików podglądu danych przygotowanych przez
moduły ingestu i transformacji. Moduł tworzy wykresy, mapy, heatmapy oraz
panele KPI w formatach PNG/JPG/PDF zgodnie ze standardami dane.gov.pl i API BDL,
a przy braku zewnętrznych bibliotek generuje pliki zastępcze gwarantujące ciągłość
procesów publikacji.
Funkcje i klasy:
- class VisualizationService: główny silnik generowania wykresów i dashboardów.
- function build_visualization_service: helper tworzący usługę na podstawie profilu.
"""

from __future__ import annotations

import base64
import json
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from ingestion_service.contracts import DatasetReference
from ingestion_service.profile import ConfigProfile, VisualizationSettings
from visualization_service.models import VisualizationProduct, VisualizationRequest

try:  # pragma: no cover - import zależny od środowiska CI
    import matplotlib.pyplot as _plt  # type: ignore
except Exception:  # pragma: no cover - brak biblioteki w środowisku
    _plt = None


_PLACEHOLDER_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z/C/HwAFgwJ/l8n9mwAAAABJRU5ErkJggg=="
)
_PLACEHOLDER_JPG = base64.b64decode(
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxISEhISEhIQEBAQEBAPDw8QDw8QFRAQFhUVFRUYHSggGBolGxUVITEhJSkrLi4uFx8zODMtNygtLisBCgoKDg0OGhAQGi0lHyUtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLf/AABEIAKgBLAMBIgACEQEDEQH/xAAcAAABBQEBAQAAAAAAAAAAAAAEAAIDBQYBBwj/xABFEAACAQIEAwUGBAQEBQIHAAABAhEAAwQSITEFBkFREyJhcYEykaGxFCNCUrHwBxQjM1Lh8AcUYnKCo8LxFqKy0vEz4RVFkrPi/8QAGQEAAwEBAQAAAAAAAAAAAAAAAAECAwQF/8QAJhEBAAICAQMDBAMAAAAAAAAAAAECAxEEEiExQVETImFxodHhMv/aAAwDAQACEQMRAD8A9WiIiAiIgIiICIiAiIgIiICIiAiIgIiICIiAiIgIiICIiAiIgIiICH//2Q=="
)
_PLACEHOLDER_PDF = (
    b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    b"4 0 obj\n<< /Length 63 >>\nstream\nBT /F1 12 Tf 36 100 Td (Visualization placeholder) Tj ET\nendstream\nendobj\n"
    b"5 0 obj\n<< /Type /Font /Subtype /Type1 /Name /F1 /BaseFont /Helvetica >>\nendobj\n"
    b"xref\n0 6\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000116 00000 n \n0000000304 00000 n \n0000000405 00000 n \n"
    b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n470\n%%EOF"
)


@dataclass(frozen=True)
class _SeriesData:
    """
    Technical description:
        Struktura pomocnicza używana wewnętrznie do przechowywania danych
        liczbowych dla pojedynczej serii wykresu. Zawiera nazwę serii oraz
        listy wartości osi X i Y przygotowane do przekazania do rendererów
        (Matplotlib lub generator zastępczy).

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
        Odpowiada za generowanie wizualizacji na podstawie plików podglądu (JSON)
        oraz ustawień `VisualizationSettings`. Obsługuje typy `line`, `bar`,
        `area`, `heatmap`, `choropleth`, `combo` i `kpi_dashboard`, zapisując
        wyniki w katalogu `output_dir` w formatach PNG/JPG/PDF. Przy braku
        biblioteki Matplotlib tworzy pliki zastępcze z raportem JSON,
        gwarantując ciągłość procesu ETL. Zwraca `VisualizationProduct`
        zawierający metadane, listę plików i opcjonalny komunikat o braku
        wizualizacji.

    Instructions for laika:
        "To serce modułu wizualizacji. Dostaje dane oraz informację, jaki wykres
        lub dashboard chcesz zobaczyć, i tworzy gotowe pliki (np. PNG i PDF),
        które możesz pobrać z panelu lub WordPressa. Jeśli danych brakuje –
        wyświetli komunikat **BRAK MOŻLIWEJ WIZUALIZACJI**."

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
        self._plt = _plt

    def generate(self, request: VisualizationRequest) -> VisualizationProduct:
        """
        Technical description:
            Generuje wizualizację lub dashboard na podstawie żądania. Kroki:
            1. Wczytanie danych z pliku preview.
            2. Przygotowanie serii danych oraz (dla typów zaawansowanych) macierzy
               lub statystyk.
            3. Renderowanie wykresu z wykorzystaniem Matplotlib lub generatora
               zastępczego, zapis do żądanych formatów.
            4. Utworzenie raportu JSON z metadanymi wizualizacji.

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
            raportem JSON, dzięki czemu publikacja danych trwa kilka sekund.
        """

        rows = self._load_preview_rows(request.preview_path)
        formats = list(request.formats or self._settings.default_formats)
        summary_payload: Dict[str, object] = {
            "dataset": request.dataset.dataset_id,
            "chart_type": request.chart_type,
            "generated_at": datetime.utcnow().isoformat(),
            "formats": formats,
            "options": request.options or {},
        }

        if request.chart_type == "kpi_dashboard":
            files, series_names, message = self._render_kpi_dashboard(request, rows, formats, summary_payload)
        else:
            series = self._prepare_series(rows, request.x_field, request.y_fields)
            if not series:
                summary_payload["reason"] = "insufficient_numeric_data"
                summary_path = self._create_summary(request, summary_payload)
                return VisualizationProduct(
                    dataset=request.dataset,
                    chart_type=request.chart_type,
                    files=[],
                    series=[],
                    generated_at=datetime.utcnow(),
                    summary_path=summary_path,
                    message="**BRAK MOŻLIWEJ WIZUALIZACJI**",
                )
            files, series_names, message = self._render_chart(request, series, rows, formats, summary_payload)

        summary_path = self._create_summary(request, summary_payload)
        return VisualizationProduct(
            dataset=request.dataset,
            chart_type=request.chart_type,
            files=files,
            series=series_names,
            generated_at=datetime.utcnow(),
            summary_path=summary_path,
            message=message,
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

        for field in y_fields[: self._settings.max_series]:
            y_raw = [row.get(field) for row in rows]
            y_values = _coerce_numeric(y_raw)
            if not y_values or len(y_values) != len(x_values):
                continue
            numeric_series.append(_SeriesData(name=str(field), x=list(x_values), y=list(y_values)))

        return numeric_series

    def _render_chart(
        self,
        request: VisualizationRequest,
        series: Sequence[_SeriesData],
        rows: List[Dict[str, object]],
        formats: Sequence[str],
        summary_payload: Dict[str, object],
    ) -> Tuple[List[Path], List[str], Optional[str]]:
        base_name = self._base_name(request)
        if self._plt is None:
            files = self._generate_placeholder_files(base_name, formats)
            summary_payload["placeholder"] = True
            summary_payload["series"] = [s.name for s in series]
            if request.chart_type == "heatmap":
                summary_payload.setdefault("heatmap", {"mode": "placeholder"})
            if request.chart_type == "choropleth":
                summary_payload.setdefault("choropleth", {"mode": "placeholder"})
            if request.chart_type == "combo":
                summary_payload.setdefault("combo", {"mode": "placeholder"})
            return files, [s.name for s in series], None

        chart_type = request.chart_type
        if chart_type == "heatmap":
            return self._render_heatmap(request, rows, formats, base_name, summary_payload)
        if chart_type == "choropleth":
            return self._render_choropleth(request, series, formats, base_name, summary_payload)
        if chart_type == "combo":
            return self._render_combo(request, series, formats, base_name, summary_payload)

        return self._render_standard(request, series, formats, base_name, summary_payload)

    def _render_standard(
        self,
        request: VisualizationRequest,
        series: Sequence[_SeriesData],
        formats: Sequence[str],
        base_name: str,
        summary_payload: Dict[str, object],
    ) -> Tuple[List[Path], List[str], Optional[str]]:
        plt = self._plt
        assert plt is not None
        fig, ax = plt.subplots(figsize=self._settings.figure_size)
        ax.set_facecolor(self._settings.background_color)

        for idx, data in enumerate(series):
            color = self._settings.color_palette[idx % len(self._settings.color_palette)]
            if request.chart_type == "line":
                ax.plot(data.x, data.y, marker="o", label=data.name, color=color)
            elif request.chart_type == "bar":
                width = self._settings.advanced.dashboard_layout.count("chart") or 1
                ax.bar([x + idx * 0.1 for x in data.x], data.y, width=0.1 * width, label=data.name, color=color)
            elif request.chart_type == "area":
                ax.fill_between(data.x, data.y, alpha=0.4, label=data.name, color=color)
            else:
                ax.plot(data.x, data.y, marker="o", label=data.name, color=color)

        ax.set_xlabel(request.x_field)
        ax.set_ylabel(", ".join(request.y_fields))
        ax.set_title(request.title or f"{self._settings.title_prefix} {request.chart_type}")
        ax.grid(True, alpha=0.2)
        ax.legend()

        files = self._save_figure(fig, base_name, formats)
        summary_payload["series"] = [s.name for s in series]
        summary_payload["x_field"] = request.x_field
        summary_payload["y_fields"] = list(request.y_fields)
        return files, [s.name for s in series], None

    def _render_heatmap(
        self,
        request: VisualizationRequest,
        rows: List[Dict[str, object]],
        formats: Sequence[str],
        base_name: str,
        summary_payload: Dict[str, object],
    ) -> Tuple[List[Path], List[str], Optional[str]]:
        plt = self._plt
        assert plt is not None
        matrix, x_labels, y_labels = self._build_heatmap_matrix(rows, request)
        fig, ax = plt.subplots(figsize=self._settings.figure_size)
        cmap = plt.get_cmap("Blues")
        if self._settings.advanced.heatmap_palette:
            cmap = plt.matplotlib.colors.LinearSegmentedColormap.from_list(
                "custom_heatmap", list(self._settings.advanced.heatmap_palette)
            )
        im = ax.imshow(matrix, aspect="auto", cmap=cmap)
        ax.set_xticks(range(len(y_labels)))
        ax.set_xticklabels(y_labels, rotation=45, ha="right")
        ax.set_yticks(range(len(x_labels)))
        ax.set_yticklabels(x_labels)
        ax.set_title(request.title or "Heatmap danych publicznych")
        fig.colorbar(im, ax=ax)

        files = self._save_figure(fig, base_name, formats)
        summary_payload["heatmap"] = {"x_labels": x_labels, "y_labels": y_labels}
        return files, y_labels, None

    def _render_choropleth(
        self,
        request: VisualizationRequest,
        series: Sequence[_SeriesData],
        formats: Sequence[str],
        base_name: str,
        summary_payload: Dict[str, object],
    ) -> Tuple[List[Path], List[str], Optional[str]]:
        plt = self._plt
        assert plt is not None
        fig, ax = plt.subplots(figsize=self._settings.figure_size)
        palette = list(self._settings.advanced.choropleth_palette or self._settings.color_palette)
        region_field = (request.options or {}).get("region_field", self._settings.advanced.map_region_field)
        values = []
        regions = []
        for idx, data in enumerate(series):
            regions.extend([str(x) for x in data.x])
            values.extend(data.y)
            color = palette[idx % len(palette)]
            ax.barh([str(x) for x in data.x], data.y, color=color, label=data.name, alpha=0.85)
        ax.set_xlabel(", ".join(request.y_fields))
        ax.set_ylabel(region_field)
        ax.set_title(request.title or "Mapa wartości według regionu")
        ax.legend()

        files = self._save_figure(fig, base_name, formats)
        summary_payload["choropleth"] = {"regions": regions, "values": values}
        return files, [s.name for s in series], None

    def _render_combo(
        self,
        request: VisualizationRequest,
        series: Sequence[_SeriesData],
        formats: Sequence[str],
        base_name: str,
        summary_payload: Dict[str, object],
    ) -> Tuple[List[Path], List[str], Optional[str]]:
        plt = self._plt
        assert plt is not None
        fig, ax1 = plt.subplots(figsize=self._settings.figure_size)
        color_cycle = list(self._settings.color_palette)
        ax2 = ax1.twinx()

        if series:
            primary = series[0]
            ax1.plot(primary.x, primary.y, color=color_cycle[0], marker="o", label=primary.name)
        if len(series) > 1:
            secondary = series[1]
            ax2.bar(
                [x + 0.1 for x in secondary.x],
                secondary.y,
                color=color_cycle[1 % len(color_cycle)],
                alpha=0.4,
                label=secondary.name,
            )
        for extra_idx, extra in enumerate(series[2:], start=2):
            ax1.plot(extra.x, extra.y, linestyle="--", color=color_cycle[extra_idx % len(color_cycle)], label=extra.name)

        ax1.set_xlabel(request.x_field)
        ax1.set_ylabel(series[0].name if series else request.y_fields[0])
        ax2.set_ylabel(series[1].name if len(series) > 1 else "")
        ax1.set_title(request.title or "Wykres kombinowany")
        ax1.grid(True, alpha=0.2)

        fig.legend(loc="upper center", bbox_to_anchor=(0.5, -0.05), ncol=len(series))
        files = self._save_figure(fig, base_name, formats)
        summary_payload["combo"] = {"series": [s.name for s in series]}
        return files, [s.name for s in series], None

    def _render_kpi_dashboard(
        self,
        request: VisualizationRequest,
        rows: List[Dict[str, object]],
        formats: Sequence[str],
        summary_payload: Dict[str, object],
    ) -> Tuple[List[Path], List[str], Optional[str]]:
        metrics = self._compute_kpis(rows, request.y_fields)
        summary_payload["kpi"] = metrics
        base_name = self._base_name(request)

        if self._plt is None:
            files = self._generate_placeholder_files(base_name, formats)
            return files, list(request.y_fields), None

        plt = self._plt
        assert plt is not None
        fig, axes = plt.subplots(1, max(1, len(metrics)), figsize=self._settings.figure_size)
        if not isinstance(axes, (list, tuple)):
            axes = [axes]

        for ax, (field, stats_map) in zip(axes, metrics.items()):
            ax.axis("off")
            ax.set_title(f"KPI: {field}")
            lines = [f"{metric}: {value}" for metric, value in stats_map.items()]
            ax.text(0.05, 0.8, "\n".join(lines), fontsize=12)

        files = self._save_figure(fig, base_name, formats)
        return files, list(request.y_fields), None

    def _save_figure(self, fig, base_name: str, formats: Sequence[str]) -> List[Path]:
        plt = self._plt
        assert plt is not None
        files: List[Path] = []
        for export_format in formats:
            safe_format = export_format.lower()
            if safe_format not in {"png", "jpg", "jpeg", "pdf"}:
                continue
            suffix = "jpg" if safe_format in {"jpg", "jpeg"} else safe_format
            target = self._output_dir / f"{base_name}.{suffix}"
            fig.savefig(target, dpi=self._settings.dpi, bbox_inches="tight")
            files.append(target)
        plt.close(fig)
        return files

    def _generate_placeholder_files(self, base_name: str, formats: Sequence[str]) -> List[Path]:
        files: List[Path] = []
        for export_format in formats:
            safe_format = export_format.lower()
            if safe_format not in {"png", "jpg", "jpeg", "pdf"}:
                continue
            suffix = "jpg" if safe_format in {"jpg", "jpeg"} else safe_format
            target = self._output_dir / f"{base_name}.{suffix}"
            if suffix == "png":
                target.write_bytes(_PLACEHOLDER_PNG)
            elif suffix == "jpg":
                target.write_bytes(_PLACEHOLDER_JPG)
            elif suffix == "pdf":
                target.write_bytes(_PLACEHOLDER_PDF)
            files.append(target)
        return files

    def _build_heatmap_matrix(
        self,
        rows: List[Dict[str, object]],
        request: VisualizationRequest,
    ) -> Tuple[List[List[float]], List[str], List[str]]:
        x_values = sorted({str(row.get(request.x_field)) for row in rows})
        y_labels = list(request.y_fields)
        matrix: List[List[float]] = []
        for x in x_values:
            row_values: List[float] = []
            for field in y_labels:
                values = [row.get(field) for row in rows if str(row.get(request.x_field)) == x]
                numeric = _coerce_numeric(values)
                row_values.append(float(statistics.mean(numeric)) if numeric else 0.0)
            matrix.append(row_values)
        return matrix, x_values, y_labels

    def _compute_kpis(self, rows: List[Dict[str, object]], fields: Sequence[str]) -> Dict[str, Dict[str, float]]:
        metrics: Dict[str, Dict[str, float]] = {}
        for field in fields:
            values = _coerce_numeric([row.get(field) for row in rows])
            if not values:
                metrics[field] = {metric: float("nan") for metric in self._settings.advanced.kpi_metrics}
                continue
            stats_map: Dict[str, float] = {}
            for metric in self._settings.advanced.kpi_metrics:
                if metric == "sum":
                    stats_map[metric] = float(sum(values))
                elif metric == "avg":
                    stats_map[metric] = float(statistics.mean(values))
                elif metric == "min":
                    stats_map[metric] = float(min(values))
                elif metric == "max":
                    stats_map[metric] = float(max(values))
                elif metric == "median":
                    stats_map[metric] = float(statistics.median(values))
                else:
                    stats_map[metric] = float("nan")
            metrics[field] = stats_map
        return metrics

    def _create_summary(self, request: VisualizationRequest, payload: Dict[str, object]) -> Path:
        base_name = self._base_name(request)
        summary_path = self._output_dir / f"{base_name}-summary.json"
        summary_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return summary_path

    def _base_name(self, request: VisualizationRequest) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"{request.dataset.dataset_id}-{request.chart_type}-{timestamp}"


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
        Umożliwia szybkie tworzenie wykresów i dashboardów w CLI lub automatycznych
        procesach bez ryzyka pomyłek w konfiguracji.
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
            continue
        try:
            coerced.append(float(value))
        except (TypeError, ValueError):
            return []
    return coerced
