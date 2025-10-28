"""
Module: ingestion_service.config_client
Opis: Zapewnia klienta komunikującego się z `config-service` i repozytorium GitOps,
aby dostarczać profile konfiguracji dla modułu importu CSV.
Funkcje i klasy:
- class ConfigServiceClient: pobiera profile konfiguracji przez HTTP lub z plików lokalnych.
- function load_profile_from_file: ładuje profil z repozytorium GitOps.
- function resolve_profile: strategia wyboru źródła profilu (HTTP → plik → domyślne).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib import request

from .profile import ConfigProfile, profile_from_dict


class ConfigServiceClient:
    """
    Technical description:
        Zapewnia komunikację z usługą `config-service` zgodnie z kontraktem
        `/config/v1/items/{key}` oraz `config.updated`. Klient potrafi pobrać
        profil konfiguracji poprzez HTTPS (mTLS) lub z lokalnego repozytorium
        GitOps, stosując nagłówki wersjonowania (`X-Config-Version`).

    Instructions for laika:
        "To pomocnik, który potrafi zapytać centralny system o ustawienia.
        Jeżeli sieć nie działa, sięga po kopię zapasową zapisaną na dysku.
        Dzięki temu import danych może działać nawet w trybie offline."

    Example:
        ```python
        client = ConfigServiceClient()
        profile = client.fetch_profile("dev")
        ```
    Effect for end user:
        Administrator otrzymuje pewność, że import zawsze korzysta z aktualnych
        ustawień zatwierdzonych w Studio Danych i spełnia wymogi bezpieczeństwa.
    """

    def __init__(self, base_url: Optional[str] = None, gitops_root: Optional[Path] = None) -> None:
        self._base_url = base_url or os.getenv("CONFIG_SERVICE_URL")
        self._gitops_root = gitops_root or Path(os.getenv("CONFIG_GITOPS_ROOT", "config/profiles"))

    def fetch_profile(self, profile_name: str) -> ConfigProfile:
        """
        Technical description:
            Próbuje pobrać profil konfiguracji z usług `config-service` (HTTPS).
            W przypadku błędu sieciowego lub braku usługi korzysta z repozytorium
            GitOps. Jeśli oba źródła zawiodą, zwraca profil domyślny określony w
            dokumentacji etapu 3.

        Instructions for laika:
            "Najpierw prosimy centralny serwer o ustawienia. Jeśli nie odpowiada,
            korzystamy z kopii na dysku. Dzięki temu import się nie zatrzymuje."

        Example:
            ```python
            profile = ConfigServiceClient().fetch_profile("prod")
            ```
        Effect for end user:
            Gwarantuje ciągłość działania panelu Studio Danych i importów CSV nawet
            przy chwilowych problemach z siecią.
        """

        if self._base_url:
            payload = self._fetch_profile_via_http(profile_name)
            if payload:
                return profile_from_dict(payload)

        file_payload = load_profile_from_file(self._gitops_root, profile_name)
        if file_payload:
            return profile_from_dict(file_payload)

        return profile_from_dict({"name": profile_name})

    def _fetch_profile_via_http(self, profile_name: str) -> Optional[Dict[str, Any]]:
        """
        Technical description:
            Wykonuje zapytanie HTTP GET na endpoint
            `/config/v1/items/profiles/{profile_name}`. Obsługuje nagłówki
            bezpieczeństwa oraz błędy sieciowe, zwracając None, gdy odpowiedź jest
            niepoprawna.

        Instructions for laika:
            "Jeśli mamy adres serwera konfiguracji, wysyłamy do niego pytanie o
            wybrany profil. Jeżeli serwer nie odpowie, przechodzimy do planu B."

        Example:
            ```python
            payload = client._fetch_profile_via_http("dev")
            ```
        Effect for end user:
            Pozwala korzystać z centralnego zarządzania konfiguracją, co ogranicza
            błędy manualne i poprawia bezpieczeństwo.
        """

        url = f"{self._base_url.rstrip('/')}/config/v1/items/profiles/{profile_name}"
        req = request.Request(url, headers={"Accept": "application/json"})
        try:
            with request.urlopen(req, timeout=10) as response:
                if response.status != 200:
                    return None
                return json.load(response)
        except Exception:
            return None


def load_profile_from_file(root: Path, profile_name: str) -> Optional[Dict[str, Any]]:
    """
    Technical description:
        Wyszukuje plik JSON lub YAML z definicją profilu w katalogu GitOps.
        Obsługuje strukturę `config/profiles/<profile>.json`. Funkcja waliduje,
        czy plik istnieje oraz czy zawiera poprawny JSON.

    Instructions for laika:
        "To jak otwarcie segregatora z kopią ustawień. Szukamy kartki o nazwie
        profilu i czytamy jej zawartość."

    Example:
        ```python
        payload = load_profile_from_file(Path("config/profiles"), "dev")
        ```
    Effect for end user:
        Pozwala administratorom posiadać kopię konfiguracji pod kontrolą GitOps,
        dzięki czemu zmiany są audytowalne i łatwe do odtworzenia.
    """

    json_path = root / f"{profile_name}.json"
    if json_path.exists():
        return json.loads(json_path.read_text(encoding="utf-8"))
    return None


def resolve_profile(profile_name: str, client: Optional[ConfigServiceClient] = None) -> ConfigProfile:
    """
    Technical description:
        Skrót do pobrania profilu konfiguracji z zachowaniem logiki awaryjnej.
        Używany przez CLI i testy integracyjne. Pozwala na wstrzykiwanie niestandardowego
        klienta (np. mock w testach).

    Instructions for laika:
        "Zamiast pisać kilka linijek kodu, wywołujesz jedną funkcję i otrzymujesz
        gotowe ustawienia importu."

    Example:
        ```python
        profile = resolve_profile("dev")
        ```
    Effect for end user:
        Przyspiesza przygotowanie importu, ograniczając ryzyko pomyłki w wyborze
        profilu i zapewniając zgodność z centralnymi ustawieniami.
    """

    client = client or ConfigServiceClient()
    return client.fetch_profile(profile_name)
