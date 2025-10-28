"""
Module: ingestion_service.remote_sync
Opis: Implementuje obsługę zdalnych źródeł URL i harmonogram synchronizacji
zgodnie z etapem 7 planu rozwoju. Moduł pobiera pliki przez HTTPS/HTTP,
przechowuje je w cache, uruchamia odpowiedni importer (CSV/XLSX/JSON) oraz
aktualizuje stan synchronizacji w rejestrze GitOps.
Funkcje i klasy:
- class RemoteSourceConfig: definicja zdalnego źródła i ustawień harmonogramu.
- class RemoteSyncState: struktura przechowująca dane ostatniej synchronizacji.
- class RemoteSyncOutcome: wynik pojedynczego uruchomienia synchronizacji.
- class RemoteSyncManager: główny silnik obsługujący pobieranie, walidację,
  aktualizację stanu i delegowanie importu do modułów ingestion-service.
- function parse_duration: zamienia ISO 8601 Duration na `datetime.timedelta`.
"""

from __future__ import annotations

import hashlib
import json
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
from urllib import parse, request

from .contracts import DatasetReference, IngestionJobRequest, IngestionResult
from .csv_ingestor import CSVIngestor
from .json_ingestor import JSONIngestor
from .profile import ConfigProfile
from .xlsx_ingestor import XLSXIngestor


@dataclass(frozen=True)
class RemoteSourceConfig:
    """
    Technical description:
        Opisuje pojedyncze zdalne źródło danych obsługiwane przez etap 7. Zawiera
        URI pobierania, format danych, powiązanie ze zbiorem danych DCAT-AP,
        nazwę profilu konfiguracji oraz parametry harmonogramu i dodatkowe
        opcje przekazywane do modułu ingestu.

    Instructions for laika:
        "To kartka z instrukcją: skąd pobrać dane (adres URL), jakiego są typu
        (CSV, XLSX lub JSON) i jak często je odświeżać. Wystarczy dodać taką
        kartkę do systemu, a synchronizacja zadziała automatycznie."

    Example:
        ```python
        cfg = RemoteSourceConfig(
            source_uri="https://dane.gov.pl/api/csv/population.csv",
            format="csv",
            dataset=DatasetReference(dataset_id="population"),
            profile_name="dev",
            schedule="PT6H",
            options={"encoding": "utf-8"},
        )
        ```
    Effect for end user:
        Administrator definiuje źródło raz i może liczyć na regularne pobieranie
        danych do Studio Danych bez ręcznej interwencji.
    """

    source_uri: str
    format: str
    dataset: DatasetReference
    profile_name: Optional[str] = None
    schedule: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)
    http_headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class RemoteSyncState:
    """
    Technical description:
        Przechowuje metadane ostatniego przebiegu synchronizacji: identyfikator
        źródła (slug), znacznik czasu uruchomienia i następnego zaplanowanego
        odświeżenia, sumę kontrolną, e-tag oraz status wykonania.

    Instructions for laika:
        "To dziennik synchronizacji. Zapisujemy tu, kiedy ostatnio pobraliśmy
        dane, kiedy powinniśmy zrobić to ponownie i czy wszystko się udało."

    Example:
        ```python
        state = RemoteSyncState(
            slug="population-csv",
            source_uri="https://dane.gov.pl/csv",
            dataset_id="population",
            format="csv",
            last_run=datetime.utcnow(),
            next_run=datetime.utcnow() + timedelta(hours=6),
            checksum="...",
            etag="\"abc\"",
            status="completed",
        )
        ```
    Effect for end user:
        Dzięki zapisowi stanu panel administratora może pokazać, kiedy dane
        zostały zaktualizowane i kiedy planowana jest kolejna synchronizacja.
    """

    slug: str
    source_uri: str
    dataset_id: str
    format: str
    last_run: datetime
    next_run: datetime
    checksum: str
    etag: Optional[str]
    status: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slug": self.slug,
            "source_uri": self.source_uri,
            "dataset_id": self.dataset_id,
            "format": self.format,
            "last_run": self.last_run.isoformat(),
            "next_run": self.next_run.isoformat(),
            "checksum": self.checksum,
            "etag": self.etag,
            "status": self.status,
        }

    @staticmethod
    def from_dict(payload: Dict[str, Any]) -> RemoteSyncState:
        return RemoteSyncState(
            slug=str(payload["slug"]),
            source_uri=str(payload["source_uri"]),
            dataset_id=str(payload["dataset_id"]),
            format=str(payload["format"]),
            last_run=datetime.fromisoformat(payload["last_run"]),
            next_run=datetime.fromisoformat(payload["next_run"]),
            checksum=str(payload["checksum"]),
            etag=payload.get("etag"),
            status=str(payload.get("status", "unknown")),
        )


@dataclass
class RemoteSyncOutcome:
    """
    Technical description:
        Reprezentuje wynik pojedynczego uruchomienia synchronizacji. Pole `status`
        przyjmuje wartości: "completed", "skipped" lub "failed". W przypadku
        powodzenia zawiera wynik importu (`IngestionResult`).

    Instructions for laika:
        "Po każdej próbie synchronizacji otrzymujesz raport: czy się udało,
        jeśli tak – ile rekordów pobrano; jeśli nie – dlaczego."

    Example:
        ```python
        outcome = RemoteSyncOutcome(status="completed", state=state, result=result)
        ```
    Effect for end user:
        Panel Studio Danych może bezpośrednio pokazać, czy harmonogram działa,
        a w razie problemów wygenerować alert administratorowi.
    """

    status: str
    state: Optional[RemoteSyncState]
    result: Optional[IngestionResult]
    message: Optional[str] = None


def parse_duration(duration: str) -> timedelta:
    """
    Technical description:
        Zamienia zapis ISO 8601 Duration (np. `PT6H30M`, `P1DT2H`) na obiekt
        `datetime.timedelta`. Obsługuje części dzienne oraz czasowe (godziny,
        minuty, sekundy). W razie nieprawidłowego formatu zgłasza `ValueError`.

    Instructions for laika:
        "Zamieniamy zapis czasu w stylu `PT6H` (co 6 godzin) na liczbę sekund,
        aby system wiedział, kiedy uruchomić następną synchronizację."

    Example:
        ```python
        interval = parse_duration("PT15M")
        assert interval.total_seconds() == 900
        ```
    Effect for end user:
        Pozwala administratorowi podawać częstotliwość w czytelnej formie,
        zgodnej z dokumentacją dane.gov.pl oraz API BDL.
    """

    import re

    match = re.fullmatch(
        r"P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?",
        duration,
    )
    if not match:
        raise ValueError("Nieprawidłowy format czasu w harmonogramie synchronizacji")

    days = int(match.group("days") or 0)
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    if days == hours == minutes == seconds == 0:
        raise ValueError("Harmonogram musi określać niezerowy interwał")
    return timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)


class RemoteSyncManager:
    """
    Technical description:
        Odpowiada za wykonanie harmonogramu synchronizacji zdalnych źródeł. Dba o
        walidację konfiguracji względem `remote_policy`, pobiera pliki z
        dopuszczonych schematów (https/http), zapisuje je w cache, deleguje import
        do odpowiedniego modułu (`CSVIngestor`, `XLSXIngestor`, `JSONIngestor`) oraz
        aktualizuje stan w katalogu `state_registry`.

    Instructions for laika:
        "To automat synchronizacji. Sprawdza, czy już czas pobrać dane, pobiera je
        z internetu, zapisuje kopię bezpieczeństwa i uruchamia odpowiedni importer.
        Na końcu notuje, kiedy ma wrócić po kolejną porcję danych."

    Example:
        ```python
        manager = RemoteSyncManager(resolve_profile("dev"))
        outcome = manager.run(RemoteSourceConfig(
            source_uri="https://example.gov/data.csv",
            format="csv",
            dataset=DatasetReference(dataset_id="population"),
            profile_name="dev",
            schedule="PT6H",
        ))
        ```
    Effect for end user:
        Harmonogramy pobierają dane z oficjalnych portali bez udziału człowieka,
        zapewniając aktualność panelu Studio Danych i zgodność z wymaganiami
        dane.gov.pl oraz API BDL.
    """

    def __init__(self, profile: ConfigProfile) -> None:
        self._profile = profile
        self._remote_policy = profile.remote_policy
        self._cache_dir = Path(self._remote_policy.download_cache)
        self._state_dir = Path(self._remote_policy.state_registry)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._state_dir.mkdir(parents=True, exist_ok=True)

    def run(self, config: RemoteSourceConfig, force: bool = False) -> RemoteSyncOutcome:
        slug = self._build_slug(config)
        state_path = self._state_path(slug)
        existing_state = self._load_state(state_path)

        interval = parse_duration(config.schedule or self._remote_policy.default_schedule)
        now = datetime.utcnow()
        if not force and existing_state and existing_state.next_run > now:
            message = (
                "Pominięto synchronizację – kolejny termin: "
                f"{existing_state.next_run.isoformat()}"
            )
            return RemoteSyncOutcome(status="skipped", state=existing_state, result=None, message=message)

        local_file, checksum, etag = self._download_with_retries(config, slug)
        try:
            result = self._run_ingestor(config, local_file)
        finally:
            # Lokalne kopie pozostają w cache zgodnie z polityką – brak usuwania.
            pass

        next_run = now + interval
        new_state = RemoteSyncState(
            slug=slug,
            source_uri=config.source_uri,
            dataset_id=config.dataset.dataset_id,
            format=config.format.lower(),
            last_run=now,
            next_run=next_run,
            checksum=checksum,
            etag=etag,
            status="completed",
        )
        self._store_state(state_path, new_state)
        message = (
            f"Zsynchronizowano {config.format.upper()} – rekordy: {result.row_count}, "
            f"kolejna próba: {next_run.isoformat()}"
        )
        return RemoteSyncOutcome(status="completed", state=new_state, result=result, message=message)

    # ------------------------------------------------------------------
    # Helpers: slug, state, download, ingestion
    # ------------------------------------------------------------------
    def _build_slug(self, config: RemoteSourceConfig) -> str:
        parsed = parse.urlparse(config.source_uri)
        scheme = parsed.scheme.lower() if parsed.scheme else "file"
        if scheme not in self._remote_policy.allowed_schemes:
            raise ValueError("Niedozwolony schemat URL w konfiguracji synchronizacji")
        dataset_slug = config.dataset.dataset_id.replace("/", "-")
        return f"{dataset_slug}-{config.format.lower()}"

    def _state_path(self, slug: str) -> Path:
        return self._state_dir / f"{slug}.json"

    def _load_state(self, path: Path) -> Optional[RemoteSyncState]:
        if not path.exists():
            return None
        return RemoteSyncState.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def _store_state(self, path: Path, state: RemoteSyncState) -> None:
        path.write_text(json.dumps(state.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def _download_with_retries(self, config: RemoteSourceConfig, slug: str) -> tuple[Path, str, Optional[str]]:
        attempts = max(1, self._remote_policy.retry_attempts)
        last_error: Optional[Exception] = None
        for attempt in range(1, attempts + 1):
            try:
                return self._download_once(config, slug)
            except Exception as exc:  # noqa: BLE001 - kontrolowany retry
                last_error = exc
                if attempt < attempts:
                    backoff = self._remote_policy.retry_backoff_seconds
                    import time

                    time.sleep(backoff)
                else:
                    raise
        assert last_error is not None
        raise last_error

    def _download_once(self, config: RemoteSourceConfig, slug: str) -> tuple[Path, str, Optional[str]]:
        parsed = parse.urlparse(config.source_uri)
        request_headers = {"User-Agent": "OpenDataPlugin/1.0"}
        request_headers.update(config.http_headers)
        req = request.Request(config.source_uri, headers=request_headers)

        context = None
        if parsed.scheme == "https" and not self._remote_policy.verify_tls:
            context = ssl._create_unverified_context()

        with request.urlopen(req, context=context, timeout=30) as response:
            status = getattr(response, "status", 200)
            if status >= 400:
                raise ValueError(f"Błąd HTTP podczas pobierania URL: {status}")
            content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
            if content_type and content_type not in self._remote_policy.allowed_content_types:
                raise ValueError("Nieobsługiwany typ zawartości dla zdalnego źródła")
            data = response.read()
            etag = response.headers.get("ETag")

        size_mb = len(data) / (1024 * 1024)
        if size_mb > self._remote_policy.max_file_size_mb:
            raise ValueError("Pobrany plik przekracza dopuszczalny rozmiar polityki remote")

        checksum = hashlib.sha256(data).hexdigest()
        extension = self._extension_for_format(config.format)
        filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{slug}{extension}"
        target = self._cache_dir / filename
        target.write_bytes(data)
        return target, checksum, etag

    def _extension_for_format(self, fmt: str) -> str:
        mapping = {"csv": ".csv", "xlsx": ".xlsx", "json": ".json"}
        return mapping.get(fmt.lower(), "")

    def _run_ingestor(self, config: RemoteSourceConfig, local_file: Path) -> IngestionResult:
        fmt = config.format.lower()
        job = IngestionJobRequest(
            source_uri=str(local_file),
            profile_name=config.profile_name or self._profile.name,
            dataset=config.dataset,
            options=config.options,
        )
        if fmt == "csv":
            ingestor = CSVIngestor(self._profile)
        elif fmt == "xlsx":
            ingestor = XLSXIngestor(self._profile)
        elif fmt == "json":
            ingestor = JSONIngestor(self._profile)
        else:
            raise ValueError("Nieobsługiwany format zdalnego źródła")
        return ingestor.run(job)
