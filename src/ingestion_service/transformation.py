"""
Module: ingestion_service.transformation
Opis: Implementuje silnik transformacji danych (Etap 9) wykorzystywany przez
`ingestion-service` do przygotowania danych po imporcie CSV/XLSX/JSON/DB.
Funkcje i klasy:
- class TransformationStep: pojedyncza operacja transformacji z parametrami.
- class TransformationSettings: ustawienia polityki transformacji oraz domyślne kroki.
- class TransformationPipeline: wykonuje sekwencję transformacji na danych i zapisuje
  raport zgodny z wymaganiami dane.gov.pl oraz API BDL.
- function load_rows_from_preview: pomaga wczytać próbkę danych z pliku preview.
- function slugify_header: normalizuje nagłówki kolumn do standardu DCAT-AP.
"""

from __future__ import annotations

import ast
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

from .contracts import (
    ColumnSchema,
    DatasetReference,
    IngestionResult,
    TransformationReport,
    TransformationStepStatus,
    VisualizationHint,
)
from .csv_ingestor import infer_column_type


try:  # pragma: no cover - import cykliczny rozwiązywany dynamicznie
    from .profile import ConfigProfile, TransformationStepConfig
except ImportError:  # pragma: no cover - podczas inicjalizacji modułu w testach
    ConfigProfile = None  # type: ignore
    TransformationStepConfig = None  # type: ignore


if TYPE_CHECKING:  # pragma: no cover - tylko wskazówki typów
    from metadata_service.registry import MetadataRegistry


@dataclass(frozen=True)
class TransformationStep:
    """
    Technical description:
        Reprezentuje pojedynczą operację w pipeline ETL. Pole `operation`
        określa typ transformacji (np. `normalize_headers`, `filter_rows`), a
        `parameters` przechowuje słownik dodatkowych ustawień wymaganych przez
        daną operację.

    Instructions for laika:
        "To element przepisu na przetwarzanie danych. Każdy krok mówi, co mamy
        zrobić z tabelą: np. zmienić nazwy kolumn albo odfiltrować wiersze."

    Example:
        ```python
        TransformationStep(operation="rename_columns", parameters={"mapping": {"rok": "year"}})
        ```
    Effect for end user:
        Administrator otrzymuje powtarzalny zestaw kroków, który może być
        ponownie wykorzystany dla wielu zbiorów danych, zapewniając zgodność ze
        standardami dane.gov.pl i API BDL.
    """

    operation: str
    parameters: Dict[str, Any]


@dataclass(frozen=True)
class TransformationSettings:
    """
    Technical description:
        Przechowuje politykę transformacji (np. maksymalna liczba wierszy,
        dopuszczalne operacje, precyzja zaokrągleń) oraz domyślny pipeline
        wykorzystywany przy automatycznym przetwarzaniu danych po imporcie.

    Instructions for laika:
        "To zbiór reguł opisujących, jak możemy przerabiać dane. Określa limit
        wierszy, jakie kroki są dozwolone i jakie operacje stosujemy domyślnie
        po każdym imporcie."

    Example:
        ```python
        TransformationSettings(
            enabled=True,
            max_rows=5000,
            rounding_precision=2,
            allowed_operations=("normalize_headers", "rename_columns"),
            steps=[TransformationStep(operation="normalize_headers", parameters={})]
        )
        ```
    Effect for end user:
        Gwarantuje, że przetwarzanie danych odbywa się w kontrolowany sposób,
        z zachowaniem limitów bezpieczeństwa i zgodności ze standardami UE.
    """

    enabled: bool
    max_rows: int
    rounding_precision: int
    allowed_operations: Sequence[str]
    steps: Sequence[TransformationStep]


class TransformationPipeline:
    """
    Technical description:
        Realizuje etap 9 – silnik transformacji danych. Pipeline przyjmuje
        wynik importu (`IngestionResult`) oraz wiersze danych (np. z landing lub
        preview), a następnie wykonuje serię operacji: normalizację nagłówków,
        zmiany nazw kolumn, filtrowanie, tworzenie kolumn pochodnych oraz
        agregację. Wynik zapisywany jest jako raport (`TransformationReport`)
        z metadanymi kolumn i sugestiami wizualizacji.

    Instructions for laika:
        "To automatyczna pralka danych: bierze tabelę po imporcie, czyści ją,
        odfiltrowuje niepotrzebne wiersze, liczy dodatkowe kolumny i szykuje
        gotowy raport do wizualizacji."

    Example:
        ```python
        pipeline = TransformationPipeline(settings, profile_preview_path)
        report = pipeline.run(ingestion_result, rows)
        ```
    Effect for end user:
        Administrator otrzymuje gotowy zbiór do publikacji i wizualizacji bez
        konieczności ręcznej edycji arkuszy – zgodnie z wymaganiami dane.gov.pl
        i API BDL.
    """

    SAFE_FUNCTIONS: Dict[str, Any] = {
        "abs": abs,
        "round": round,
        "int": int,
        "float": float,
        "len": len,
        "min": min,
        "max": max,
    }

    def __init__(self, settings: TransformationSettings, preview_root: Path) -> None:
        self._settings = settings
        self._preview_root = preview_root
        self._preview_root.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        ingestion: IngestionResult,
        rows: Sequence[Dict[str, Any]],
        pipeline: Optional[Sequence[TransformationStep]] = None,
        metadata_registry: Optional["MetadataRegistry"] = None,
        metadata_overrides: Optional[Dict[str, Any]] = None,
    ) -> TransformationReport:
        """
        Technical description:
            Wykonuje pipeline transformacji na przekazanych wierszach. Kontroluje
            dozwolone operacje, ogranicza liczbę wierszy (`max_rows`), zapisuje
            podgląd wyniku oraz generuje metadane kolumn i sugestie wizualizacji.
            Opcjonalnie aktualizuje rejestr metadanych (`metadata_registry`)
            wykorzystując ustawienia etapu 10.

        Instructions for laika:
            "Podajemy raport z importu i dane. Funkcja stosuje zapisane kroki,
            zapisuje nowe dane w katalogu `preview` i zwraca podsumowanie – ile
            wierszy zostało, jakie kolumny powstały i jakie wykresy polecamy.
            Jeśli włączysz katalog metadanych, opis zbioru zapisze się sam."

        Example:
            ```python
            report = pipeline.run(
                ingestion_result,
                rows,
                metadata_registry=registry,
                metadata_overrides={"title": "Populacja"},
            )
            ```
        Effect for end user:
            Pozwala szybko przejść od surowych danych do gotowej tabeli, która
            spełnia kryteria publikacji i może być natychmiast wykorzystana w
            wizualizacjach, katalogu DCAT-AP oraz eksporcie do WordPress.
        """

        if not self._settings.enabled:
            raise ValueError("Transformation pipeline is disabled for this profile")

        steps = list(pipeline or self._settings.steps)
        applied: List[TransformationStepStatus] = []
        working_rows = [dict(row) for row in rows[: self._settings.max_rows]]

        for step in steps:
            if step.operation not in self._settings.allowed_operations:
                applied.append(
                    TransformationStepStatus(
                        operation=step.operation,
                        status="skipped",
                        message="Operacja nie jest dozwolona w polityce profilu.",
                    )
                )
                continue
            try:
                working_rows = self._apply_step(working_rows, step)
                applied.append(
                    TransformationStepStatus(
                        operation=step.operation,
                        status="applied",
                        message="Operacja wykonana poprawnie.",
                    )
                )
            except Exception as exc:  # pragma: no cover - ochronny fallback
                applied.append(
                    TransformationStepStatus(
                        operation=step.operation,
                        status="failed",
                        message=str(exc),
                    )
                )

        columns = self._build_columns(working_rows)
        hints, message = self._build_visualization_hints(columns)
        preview_path = self._write_preview(ingestion.dataset, working_rows)

        now = datetime.utcnow()
        report = TransformationReport(
            dataset=ingestion.dataset,
            rows_in=len(rows),
            rows_out=len(working_rows),
            columns=columns,
            visualization_hints=hints,
            preview_path=str(preview_path),
            started_at=now,
            finished_at=now,
            applied_steps=applied,
            message=message,
        )

        if metadata_registry is not None:
            metadata_registry.register_transformation(report, metadata_overrides)

        return report

    def _apply_step(
        self,
        rows: List[Dict[str, Any]],
        step: TransformationStep,
    ) -> List[Dict[str, Any]]:
        operation = step.operation
        params = step.parameters or {}
        if operation == "normalize_headers":
            return [self._normalize_headers(row) for row in rows]
        if operation == "rename_columns":
            return [self._rename_columns(row, params.get("mapping", {})) for row in rows]
        if operation == "filter_rows":
            return self._filter_rows(rows, params.get("conditions", []))
        if operation == "derive_column":
            return self._derive_column(rows, params.get("name"), params.get("expression"))
        if operation == "aggregate":
            return self._aggregate(rows, params)
        raise ValueError(f"Nieobsługiwana operacja transformacji: {operation}")

    def _normalize_headers(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {slugify_header(key): value for key, value in row.items()}

    def _rename_columns(self, row: Dict[str, Any], mapping: Dict[str, str]) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        for key, value in row.items():
            new_key = mapping.get(key, key)
            result[new_key] = value
        return result

    def _filter_rows(
        self,
        rows: List[Dict[str, Any]],
        conditions: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        if not conditions:
            return rows
        filtered: List[Dict[str, Any]] = []
        for row in rows:
            if self._row_matches(row, conditions):
                filtered.append(row)
        return filtered

    def _row_matches(self, row: Dict[str, Any], conditions: Sequence[Dict[str, Any]]) -> bool:
        for condition in conditions:
            field = condition.get("field")
            operator = condition.get("operator", "==")
            expected = condition.get("value")
            actual = row.get(field)
            if not self._compare(actual, operator, expected):
                return False
        return True

    def _compare(self, actual: Any, operator: str, expected: Any) -> bool:
        if operator in {"==", "equals"}:
            return str(actual) == str(expected)
        if operator in {"!=", "not_equals"}:
            return str(actual) != str(expected)
        try:
            actual_float = float(str(actual).replace(",", "."))
            expected_float = float(str(expected).replace(",", "."))
        except (TypeError, ValueError):
            actual_float = None
            expected_float = None
        if operator in {">", "gt"} and actual_float is not None and expected_float is not None:
            return actual_float > expected_float
        if operator in {">=", "gte"} and actual_float is not None and expected_float is not None:
            return actual_float >= expected_float
        if operator in {"<", "lt"} and actual_float is not None and expected_float is not None:
            return actual_float < expected_float
        if operator in {"<=", "lte"} and actual_float is not None and expected_float is not None:
            return actual_float <= expected_float
        if operator in {"in", "contains"}:
            if isinstance(expected, (list, tuple, set)):
                return actual in expected
            return str(expected) in str(actual)
        if operator in {"not_in", "not_contains"}:
            if isinstance(expected, (list, tuple, set)):
                return actual not in expected
            return str(expected) not in str(actual)
        return False

    def _derive_column(
        self,
        rows: List[Dict[str, Any]],
        name: Optional[str],
        expression: Optional[str],
    ) -> List[Dict[str, Any]]:
        if not name or not expression:
            return rows
        for row in rows:
            context = {slugify_header(key): self._coerce_value(value) for key, value in row.items()}
            row[name] = self._safe_eval(expression, context)
        return rows

    def _aggregate(self, rows: List[Dict[str, Any]], params: Dict[str, Any]) -> List[Dict[str, Any]]:
        group_by: Sequence[str] = tuple(params.get("group_by", []))
        metrics: Sequence[Dict[str, Any]] = tuple(params.get("metrics", []))
        groups: Dict[Tuple[Any, ...], List[Dict[str, Any]]] = defaultdict(list)
        if not metrics:
            return rows
        for row in rows:
            key = tuple(row.get(field) for field in group_by)
            groups[key].append(row)
        aggregated: List[Dict[str, Any]] = []
        for key, group_rows in groups.items():
            aggregated_row: Dict[str, Any] = {}
            for index, field in enumerate(group_by):
                aggregated_row[field] = key[index]
            for metric in metrics:
                field = metric.get("field")
                function = (metric.get("function") or "sum").lower()
                alias = metric.get("alias") or f"{field}_{function}"
                values = [self._coerce_numeric(row.get(field)) for row in group_rows]
                values = [value for value in values if value is not None]
                if not values:
                    aggregated_row[alias] = None
                    continue
                if function == "sum":
                    aggregated_row[alias] = round(sum(values), self._settings.rounding_precision)
                elif function in {"avg", "mean"}:
                    aggregated_row[alias] = round(
                        sum(values) / len(values), self._settings.rounding_precision
                    )
                elif function == "min":
                    aggregated_row[alias] = min(values)
                elif function == "max":
                    aggregated_row[alias] = max(values)
                elif function == "count":
                    aggregated_row[alias] = len(values)
                else:
                    raise ValueError(f"Nieobsługiwana funkcja agregująca: {function}")
            aggregated.append(aggregated_row)
        return aggregated

    def _coerce_value(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str) and value.strip() == "":
            return None
        if isinstance(value, str):
            text = value.strip()
            if text.lower() in {"true", "false"}:
                return text.lower() == "true"
            try:
                if "." in text or "," in text:
                    return float(text.replace(",", "."))
                return int(text)
            except ValueError:
                return text
        return value

    def _coerce_numeric(self, value: Any) -> Optional[float]:
        coerced = self._coerce_value(value)
        if isinstance(coerced, (int, float)):
            return float(coerced)
        return None

    def _safe_eval(self, expression: str, context: Dict[str, Any]) -> Any:
        tree = ast.parse(expression, mode="eval")
        for node in ast.walk(tree):
            if not isinstance(
                node,
                (
                    ast.Expression,
                    ast.BinOp,
                    ast.UnaryOp,
                    ast.Num,
                    ast.Name,
                    ast.Load,
                    ast.Add,
                    ast.Sub,
                    ast.Mult,
                    ast.Div,
                    ast.Pow,
                    ast.Mod,
                    ast.USub,
                    ast.UAdd,
                    ast.Call,
                    ast.Constant,
                    ast.Compare,
                    ast.Eq,
                    ast.NotEq,
                    ast.Gt,
                    ast.GtE,
                    ast.Lt,
                    ast.LtE,
                ),
            ):
                raise ValueError("Niedozwolone wyrażenie w transformacji")
            if isinstance(node, ast.Call) and not isinstance(node.func, ast.Name):
                raise ValueError("Dozwolone są tylko proste funkcje w wyrażeniach")
        safe_globals = {name: func for name, func in self.SAFE_FUNCTIONS.items()}
        return eval(compile(tree, filename="<transformation>", mode="eval"), safe_globals, context)

    def _build_columns(self, rows: Sequence[Dict[str, Any]]) -> List[ColumnSchema]:
        if not rows:
            return []
        headers = list(rows[0].keys())
        sample_rows = [list(row.values()) for row in rows[: min(len(rows), 25)]]
        columns: List[ColumnSchema] = []
        for index, header in enumerate(headers):
            values = [row[index] for row in sample_rows if len(row) > index]
            data_type, nullable, example = infer_column_type([str(value) if value is not None else "" for value in values])
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
    ) -> Tuple[List[VisualizationHint], Optional[str]]:
        numeric_columns = [col for col in columns if col.data_type in {"integer", "decimal"}]
        date_columns = [col for col in columns if col.data_type in {"date", "datetime"}]
        hints: List[VisualizationHint] = []
        if numeric_columns and date_columns:
            hints.append(
                VisualizationHint(
                    chart_type="line",
                    confidence=0.85,
                    reason="Wykryto kolumnę czasu i miary liczbowe po transformacji.",
                )
            )
        elif numeric_columns:
            hints.append(
                VisualizationHint(
                    chart_type="bar",
                    confidence=0.7,
                    reason="Dane liczbowe bez osi czasu – sugerowany wykres słupkowy.",
                )
            )
        message = None
        if not hints:
            message = "**BRAK MOŻLIWEJ WIZUALIZACJI**"
        return hints, message

    def _write_preview(self, dataset: DatasetReference, rows: Sequence[Dict[str, Any]]) -> Path:
        preview_file = self._preview_root / f"{dataset.dataset_id}-transformed.json"
        payload = {
            "dataset_id": dataset.dataset_id,
            "resource_id": dataset.resource_id,
            "rows": rows[:50],
            "generated_at": datetime.utcnow().isoformat(),
        }
        preview_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return preview_file


def load_rows_from_preview(preview_path: Path) -> List[Dict[str, Any]]:
    """
    Technical description:
        Pomocnicza funkcja wczytująca dane z pliku preview (JSON) wygenerowanego
        podczas importu. Zwraca listę wierszy (lista słowników), którą można
        przekazać do pipeline'u transformacji.

    Instructions for laika:
        "Jeśli masz gotowy podgląd danych w pliku JSON, ta funkcja otworzy go i
        zwróci listę wierszy, by można było je dalej przetwarzać."

    Example:
        ```python
        rows = load_rows_from_preview(Path("build/preview/population-dev.json"))
        ```
    Effect for end user:
        Umożliwia ponowne użycie zapisanych podglądów bez konieczności
        przeprowadzania pełnego importu, co przyspiesza przygotowanie raportów.
    """

    if not preview_path.exists():
        return []
    payload = json.loads(preview_path.read_text(encoding="utf-8"))
    return [dict(row) for row in payload.get("rows", [])]


def settings_from_profile(profile: "ConfigProfile") -> TransformationSettings:
    """
    Technical description:
        Buduje obiekt `TransformationSettings` na podstawie profilu konfiguracyjnego
        (`ConfigProfile`). Funkcja mapuje `TransformationStepConfig` na
        `TransformationStep` oraz wypełnia parametry polityki transformacji.

    Instructions for laika:
        "Jeśli masz gotowy profil z ustawieniami, ta funkcja zamienia go na
        pakiet kroków, który silnik transformacji potrafi wykonać."

    Example:
        ```python
        settings = settings_from_profile(profile)
        pipeline = TransformationPipeline(settings, Path(profile.storage.preview))
        ```
    Effect for end user:
        Umożliwia użycie tych samych ustawień z panelu Studio Danych w kodzie,
        dzięki czemu transformacje są spójne we wszystkich środowiskach.
    """

    if profile.transformation_policy is None:
        raise ValueError("Profil nie zawiera polityki transformacji (Etap 9)")
    policy = profile.transformation_policy
    steps: List[TransformationStep] = []
    for step_config in profile.transformation_steps:
        steps.append(
            TransformationStep(
                operation=step_config.operation,
                parameters=step_config.parameters,
            )
        )
    return TransformationSettings(
        enabled=policy.enabled,
        max_rows=policy.max_rows,
        rounding_precision=policy.rounding_precision,
        allowed_operations=policy.allowed_operations,
        steps=steps,
    )


def slugify_header(value: str) -> str:
    """
    Technical description:
        Normalizuje nagłówek kolumny do formatu zgodnego z DCAT-AP: małe litery,
        znaki nieliterowe zastępowane znakiem podkreślenia, usunięcie podwójnych
        separatorów oraz przycięcie końcowych znaków `_`.

    Instructions for laika:
        "Zmieniamy nazwę kolumny na prostą i czytelną – małe litery bez spacji,
        żeby łatwo było odwoływać się do niej w raportach."

    Example:
        ```python
        slugify_header("Liczba Ludności (ogółem)")  # -> "liczba_ludnosci_ogolem"
        ```
    Effect for end user:
        Ujednolica nazwy kolumn w raportach i wizualizacjach, dzięki czemu
        użytkownicy końcowi portalu otrzymują spójne nazewnictwo.
    """

    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_")
