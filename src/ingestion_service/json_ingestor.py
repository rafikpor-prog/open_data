"""
Module: ingestion_service.json_ingestor
Opis: Implementuje obsługę źródeł JSON i API REST (Etap 6) w module `ingestion-service`.
Funkcje i klasy:
- function is_http_uri: wykrywa, czy adres źródłowy wskazuje na zasób HTTP/S.
- class JSONIngestor: główny silnik importu danych JSON/API z obsługą profili konfiguracji.
- function build_default_json_ingestor: helper tworzący skonfigurowany JSONIngestor dla CLI/testów.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Sequence
from urllib import parse, request

from .config_client import resolve_profile
from .contracts import (
    ColumnSchema,
    DatasetReference,
    IngestionJobRequest,
    IngestionResult,
    VisualizationHint,
)
from .csv_ingestor import infer_column_type
from .profile import ConfigProfile


def is_http_uri(uri: str) -> bool:
    """
    Technical description:
        Sprawdza, czy przekazany URI rozpoczyna się od protokołu HTTP lub HTTPS.
        Funkcja jest wykorzystywana przy wyborze strategii pobierania (plik lokalny
        vs. żądanie sieciowe) w klasie JSONIngestor.

    Instructions for laika:
        "To szybkie sprawdzenie, czy wskazany adres zaczyna się od http:// albo
        https://. Jeśli tak – wiemy, że dane trzeba pobrać z internetu."

    Example:
        ```python
        assert is_http_uri("https://api.dane.gov.pl")
        ```
    Effect for end user:
        Automatyczne rozpoznanie rodzaju źródła pozwala administratorowi używać
        tej samej funkcji zarówno dla plików JSON, jak i adresów API.
    """

    return uri.startswith("http://") or uri.startswith("https://")


class JSONIngestor:
    """
    Technical description:
        Realizuje import danych JSON/API zgodny z kontraktami `ingestion-service`
        oraz profilami konfiguracji (Etap 6). Obsługuje pobieranie plików lokalnych,
        wykonywanie żądań HTTP/S z walidacją nagłówków, zastosowanie JSON Pointera
        do wyodrębnienia listy rekordów, heurystyczne budowanie schematu kolumn,
        generowanie podglądu i sugestii wizualizacji.

    Instructions for laika:
        "To odpowiednik importu CSV dla API. Podajesz adres lub plik JSON, a moduł
        pobiera dane, wybiera właściwą listę rekordów i przygotowuje raport razem
        z propozycjami wykresów."

    Example:
        ```python
        ingestor = JSONIngestor(resolve_profile("dev"))
        job = IngestionJobRequest(
            source_uri="https://api.example.gov/data",
            profile_name="dev",
            dataset=DatasetReference(dataset_id="population"),
            options={"json_pointer": "/results"}
        )
        result = ingestor.run(job)
        ```
    Effect for end user:
        Administrator może pobierać dane z API dane.gov.pl lub API BDL i w kilka
        sekund otrzymać gotowy raport z opisem kolumn, liczbą rekordów oraz
        podpowiedziami wizualizacji.
    """

    def __init__(self, profile: ConfigProfile) -> None:
        self._profile = profile
        self._landing_path = Path(profile.storage.landing)
        self._preview_path = Path(profile.storage.preview)
        self._landing_path.mkdir(parents=True, exist_ok=True)
        self._preview_path.mkdir(parents=True, exist_ok=True)

    def run(self, job: IngestionJobRequest) -> IngestionResult:
        """
        Technical description:
            Wykonuje kompletny proces importu JSON/API:
            1. Pobiera dane (plik lokalny lub HTTP) z kontrolą nagłówków i limitu
               rozmiaru ustalonego w profilu.
            2. Stosuje JSON Pointer (z zadania lub profilu) do wyodrębnienia listy
               rekordów, ogranicza je do `max_records`.
            3. Buduje schemat kolumn (ColumnSchema) i sugestie wizualizacji.
            4. Zapisuje kopię źródłową w strefie landing oraz podgląd JSON w katalogu
               preview.

        Instructions for laika:
            "Podajesz adres API lub plik, a funkcja sama pobiera dane, wybiera
            odpowiednie rekordy i przygotowuje zwięzły raport."

        Example:
            ```python
            result = JSONIngestor(resolve_profile("dev")).run(job)
            ```
        Effect for end user:
            Pozwala natychmiast zobaczyć, ile rekordów zwróciło API, jakie są pola
            w danych oraz czy możliwe jest wygenerowanie wykresów.
        """

        started_at = datetime.utcnow()
        records, raw_text, truncated = self._load_records(job)
        columns = self._build_columns(records)
        hints, viz_message = self._build_visualization_hints(columns)
        preview_file = self._write_preview(job, records)
        self._write_landing_copy(job, raw_text)
        finished_at = datetime.utcnow()

        messages: List[str] = []
        if truncated:
            messages.append(
                f"Ograniczono wynik do {self._profile.json_policy.max_records} rekordów zgodnie z profilem."
            )
        if viz_message:
            messages.append(viz_message)
        message = " ".join(messages) if messages else None

        return IngestionResult(
            dataset=job.dataset,
            row_count=len(records),
            columns=columns,
            visualization_hints=hints,
            preview_path=str(preview_file),
            started_at=started_at,
            finished_at=finished_at,
            message=message,
        )

    # ---------------------------------------------------------------------
    # Internal helpers – pobieranie danych i konstrukcja rekordu
    # ---------------------------------------------------------------------
    def _load_records(self, job: IngestionJobRequest) -> tuple[List[Dict[str, Any]], str, bool]:
        policy = self._profile.json_policy
        raw_text: str
        if is_http_uri(job.source_uri):
            raw_text = self._load_http(job)
        else:
            raw_text = self._load_file(job.source_uri)

        payload = json.loads(raw_text)
        pointer = job.options.get("json_pointer", policy.default_pointer)
        records = self._extract_records(payload, pointer)
        truncated = len(records) > policy.max_records
        normalized = self._normalize_records(records[: policy.max_records])
        return normalized, raw_text, truncated

    def _load_http(self, job: IngestionJobRequest) -> str:
        policy = self._profile.json_policy
        method = job.options.get("http_method", "GET").upper()
        if method not in policy.allowed_http_methods:
            raise ValueError("Nieobsługiwana metoda HTTP w profilu JSON")

        query_payload: Dict[str, Any] = {}
        if "query_params" in job.options:
            query_payload = self._parse_query_params(job.options["query_params"])

        url = job.source_uri
        data_bytes: bytes | None = None
        if method == "GET" and query_payload:
            parsed = parse.urlparse(url)
            existing = parse.parse_qsl(parsed.query, keep_blank_values=True)
            merged = existing + list(query_payload.items())
            url = parse.urlunparse(parsed._replace(query=parse.urlencode(merged)))
        elif method != "GET" and query_payload:
            data_bytes = json.dumps(query_payload).encode("utf-8")

        req = request.Request(url, method=method)
        req.add_header("Accept", ",".join(policy.allowed_content_types))
        if data_bytes is not None:
            req.add_header("Content-Type", "application/json")

        with request.urlopen(req, data=data_bytes, timeout=policy.http_timeout) as response:
            status = getattr(response, "status", 200)
            if status >= 400:
                raise ValueError(f"Błąd HTTP podczas pobierania danych JSON: {status}")
            content_type = (response.headers.get("Content-Type", "").split(";")[0]).strip()
            if content_type and content_type not in policy.allowed_content_types:
                raise ValueError("Nieobsługiwany typ zawartości JSON")
            raw_bytes = response.read()

        self._validate_payload_size(raw_bytes)
        return raw_bytes.decode("utf-8")

    def _load_file(self, uri: str) -> str:
        path = Path(uri)
        if not path.exists():
            raise FileNotFoundError(f"Plik {uri} nie istnieje")
        raw_bytes = path.read_bytes()
        self._validate_payload_size(raw_bytes)
        return raw_bytes.decode("utf-8")

    def _validate_payload_size(self, raw_bytes: bytes) -> None:
        size_mb = len(raw_bytes) / (1024 * 1024)
        if size_mb > self._profile.json_policy.max_payload_mb:
            raise ValueError("Przekroczono maksymalny rozmiar odpowiedzi JSON")

    def _parse_query_params(self, value: str) -> Dict[str, Any]:
        try:
            parsed = json.loads(value)
            if not isinstance(parsed, dict):
                raise ValueError
            return parsed
        except ValueError as exc:  # pragma: no cover - sygnalizacja błędu użytkownika
            raise ValueError("Parametr query_params musi być słownikiem JSON") from exc

    def _extract_records(self, payload: Any, pointer: str) -> List[Any]:
        node = payload
        if pointer and pointer != "/":
            for part in pointer.split("/"):
                if not part:
                    continue
                if isinstance(node, dict):
                    node = node.get(part)
                elif isinstance(node, list):
                    try:
                        index = int(part)
                    except ValueError as exc:
                        raise ValueError("Pointer JSON wskazuje na listę, ale część ścieżki nie jest liczbą") from exc
                    if index >= len(node):
                        raise ValueError("Pointer JSON wykracza poza zakres listy")
                    node = node[index]
                else:
                    raise ValueError("Pointer JSON prowadzi do nieobsługiwanego typu danych")
        if isinstance(node, list):
            return node
        if isinstance(node, dict):
            return [node]
        raise ValueError("Pointer JSON nie wskazuje na listę rekordów")

    def _normalize_records(self, records: Sequence[Any]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for item in records:
            if isinstance(item, dict):
                normalized.append(item)
            else:
                normalized.append({"value": item})
        return normalized

    def _build_columns(self, records: Sequence[Dict[str, Any]]) -> List[ColumnSchema]:
        if not records:
            return []
        keys = self._collect_keys(records)
        columns: List[ColumnSchema] = []
        for key in keys:
            values = [self._stringify(record.get(key)) for record in records]
            data_type, nullable, example = infer_column_type(values)
            columns.append(
                ColumnSchema(
                    name=key,
                    data_type=data_type,
                    nullable=nullable,
                    example=example,
                )
            )
        return columns

    def _collect_keys(self, records: Sequence[Dict[str, Any]]) -> Sequence[str]:
        seen: Dict[str, None] = {}
        for record in records:
            for key in record.keys():
                if key not in seen:
                    seen[key] = None
        return list(seen.keys())

    def _stringify(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    def _build_visualization_hints(self, columns: Sequence[ColumnSchema]) -> tuple[List[VisualizationHint], str | None]:
        numeric_columns = [col for col in columns if col.data_type in {"integer", "decimal"}]
        date_columns = [col for col in columns if col.data_type in {"date", "datetime"}]
        hints: List[VisualizationHint] = []
        if numeric_columns and date_columns:
            hints.append(
                VisualizationHint(
                    chart_type="line",
                    confidence=0.9,
                    reason="Wykryto pola czasu oraz wartości liczbowe",
                )
            )
        elif numeric_columns:
            hints.append(
                VisualizationHint(
                    chart_type="bar",
                    confidence=0.7,
                    reason="Zestaw danych zawiera wartości liczbowe bez osi czasu",
                )
            )
        message = None
        if not hints:
            message = "**BRAK MOŻLIWEJ WIZUALIZACJI**"
        return hints, message

    def _write_preview(self, job: IngestionJobRequest, records: Sequence[Dict[str, Any]]) -> Path:
        preview_size = min(self._profile.json_policy.preview_size, len(records))
        preview_data = {
            "dataset_id": job.dataset.dataset_id,
            "resource_id": job.dataset.resource_id,
            "json_pointer": job.options.get("json_pointer", self._profile.json_policy.default_pointer),
            "records": list(records[:preview_size]),
            "generated_at": datetime.utcnow().isoformat(),
        }
        preview_file = self._preview_path / f"{job.dataset.dataset_id}-{job.profile_name}-json.json"
        preview_file.write_text(json.dumps(preview_data, ensure_ascii=False, indent=2), encoding="utf-8")
        return preview_file

    def _write_landing_copy(self, job: IngestionJobRequest, raw_text: str) -> None:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        target = self._landing_path / f"{timestamp}-{job.dataset.dataset_id}.json"
        target.write_text(raw_text, encoding="utf-8")


def build_default_json_ingestor(profile_name: str) -> JSONIngestor:
    """
    Technical description:
        Tworzy instancję JSONIngestor na podstawie profilu pobranego z `config-service`
        lub repozytorium GitOps. Umożliwia uruchomienie importu JSON w CLI.

    Instructions for laika:
        "Wywołaj tę funkcję z nazwą profilu (np. 'dev'), a dostaniesz gotowy silnik
        do pobierania danych z API."

    Example:
        ```python
        ingestor = build_default_json_ingestor("dev")
        ```
    Effect for end user:
        Upraszcza konfigurację narzędzi linii poleceń i testów, bo nie trzeba
        ręcznie konstruować obiektu JSONIngestor.
    """

    profile = resolve_profile(profile_name)
    return JSONIngestor(profile)


if __name__ == "__main__":
    profile_name = os.getenv("ODP_PROFILE", "dev")
    source_uri = os.getenv("ODP_JSON_SOURCE")
    if not source_uri:
        raise SystemExit("Zmienna ODP_JSON_SOURCE jest wymagana do importu JSON")
    dataset_id = os.getenv("ODP_DATASET_ID", "dataset")
    resource_id = os.getenv("ODP_RESOURCE_ID")
    pointer = os.getenv("ODP_JSON_POINTER")
    http_method = os.getenv("ODP_HTTP_METHOD")
    query_params = os.getenv("ODP_QUERY_PARAMS")

    options: Dict[str, str] = {}
    if pointer:
        options["json_pointer"] = pointer
    if http_method:
        options["http_method"] = http_method
    if query_params:
        options["query_params"] = query_params

    job = IngestionJobRequest(
        source_uri=source_uri,
        profile_name=profile_name,
        dataset=DatasetReference(dataset_id=dataset_id, resource_id=resource_id),
        options=options,
    )

    ingestor = build_default_json_ingestor(profile_name)
    result = ingestor.run(job)
    print(
        json.dumps(
            {
                "dataset": result.dataset.dataset_id,
                "row_count": result.row_count,
                "columns": [column.__dict__ for column in result.columns],
                "visualization_hints": [hint.__dict__ for hint in result.visualization_hints],
                "message": result.message,
                "preview_path": result.preview_path,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
