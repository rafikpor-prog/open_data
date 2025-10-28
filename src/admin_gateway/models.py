"""
Module: admin_gateway.models
Opis: Definiuje modele danych wykorzystywane w panelu administracyjnym Studio
Danych (etap 12). Modele odwzorowują ustawienia panelu, integracje WordPress i
metadane paczek instalacyjnych zgodnie z wymaganiami dane.gov.pl, API BDL oraz
standardów UE.
Funkcje i klasy:
- class BrandingSettings: przechowuje informacje o identyfikacji wizualnej
  Studio Danych.
- class FeatureFlags: określa dostępność modułów (ingestion, transformacje,
  metadane, WordPress, jakość danych).
- class MenuItem: opisuje pozycję menu w panelu wraz z wymaganymi uprawnieniami.
- class StudioSettings: agreguje ustawienia panelu (profil domyślny, menu,
  branding, moduły).
- class WordPressInstallerConfig: konfiguracja generatora paczek instalacyjnych
  WordPress.
- class WordPressSettings: parametry integracji WordPress (synchronizacja,
  instalator).
- class WordPressSite: reprezentuje zarejestrowaną instancję WordPress.
- class InstallationPackage: opis wygenerowanej paczki instalacyjnej.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Sequence


@dataclass
class BrandingSettings:
    """
    Technical description:
        Przechowuje identyfikację wizualną Studio Danych: adres logo, adres
        kontaktowy oraz opcjonalny komunikat informacyjny. Informacje te są
        wykorzystywane przez frontend (React/WordPress) do prezentacji panelu.

    Instructions for laika:
        "Tu zapisujemy logo, e-mail wsparcia i komunikat dla użytkowników
        (np. ostrzeżenie o środowisku testowym)."

    Example:
        ```python
        BrandingSettings(
            logo_url="https://example.gov/logo.svg",
            support_email="wsparcie@example.gov",
            announcement="Środowisko testowe"
        )
        ```

    Effect for end user:
        Zapewnia spójny wygląd portalu i łatwy dostęp do pomocy technicznej,
        co jest wymagane przez standardy dostępności WCAG i dane.gov.pl.
    """

    logo_url: str | None
    support_email: str
    announcement: str | None = None


@dataclass
class FeatureFlags:
    """
    Technical description:
        Określa aktywne moduły Studio Danych. Flagi determinują, które sekcje
        panelu i API są dostępne dla użytkowników: import, transformacje,
        metadane, integracja WordPress oraz moduł jakości danych.

    Instructions for laika:
        "To lista przełączników – jeśli coś jest włączone, zobaczysz daną sekcję
        w panelu."

    Example:
        ```python
        FeatureFlags(ingestion=True, transformation=True, metadata=True,
                     wordpress=True, quality=False)
        ```

    Effect for end user:
        Administrator może elastycznie włączać/wyłączać moduły zgodnie z
        harmonogramem wdrożeń bez modyfikacji kodu.
    """

    ingestion: bool = True
    transformation: bool = True
    metadata: bool = True
    wordpress: bool = True
    quality: bool = False


@dataclass
class MenuItem:
    """
    Technical description:
        Opisuje pozycję menu w Studio Danych. Pole `permissions` zawiera listę
        uprawnień wymaganych do wyświetlenia pozycji, co zapewnia zgodność z
        modułem autoryzacji (etap 11).

    Instructions for laika:
        "Każdy wpis w menu ma nazwę, adres i listę uprawnień – dzięki temu
        widzą go tylko osoby z odpowiednimi rolami."

    Example:
        ```python
        MenuItem(
            key="dashboard",
            label="Pulpit",
            route="/studio/dashboard",
            permissions=["studio.dashboard.view"]
        )
        ```

    Effect for end user:
        Panel wyświetla tylko te funkcje, do których użytkownik ma uprawnienia,
        co upraszcza obsługę i poprawia bezpieczeństwo.
    """

    key: str
    label: str
    route: str
    permissions: Sequence[str] = field(default_factory=tuple)


@dataclass
class StudioSettings:
    """
    Technical description:
        Agreguje ustawienia panelu Studio Danych: profil domyślny, listę profili
        dostępnych do wyboru, konfigurację menu, flagi modułów oraz branding.
        Ustawienia te są ładowane z `ConfigProfile.admin_settings` i służą do
        budowy interfejsu administratora.

    Instructions for laika:
        "To komplet informacji, jakie widzi panel: który profil wybrać domyślnie,
        jakie moduły są włączone i jakie menu pokazać."

    Example:
        ```python
        StudioSettings(
            default_profile="dev",
            allowed_profiles=["dev"],
            feature_flags=FeatureFlags(),
            branding=BrandingSettings(logo_url=None, support_email="help@example.gov"),
            menu=[MenuItem(key="dashboard", label="Pulpit", route="/studio/dashboard", permissions=["studio.dashboard.view"])]
        )
        ```

    Effect for end user:
        Administrator otrzymuje panel dopasowany do roli i konfiguracji, co
        przyspiesza konfigurację systemu danych publicznych.
    """

    default_profile: str
    allowed_profiles: Sequence[str]
    feature_flags: FeatureFlags
    branding: BrandingSettings
    menu: Sequence[MenuItem]


@dataclass
class WordPressInstallerConfig:
    """
    Technical description:
        Określa lokalizację i nazwę paczki instalacyjnej generowanej dla
        WordPressa. Folder docelowy jest wykorzystywany przez generator ZIP,
        dzięki czemu panel może automatycznie przygotować pakiet.

    Instructions for laika:
        "To ustawienie, gdzie zapisać plik ZIP z wtyczką i jak go nazwać."

    Example:
        ```python
        WordPressInstallerConfig(bundle_directory="build/installers", package_name="open-data-plugin.zip")
        ```

    Effect for end user:
        Administrator pobiera gotową paczkę z panelu i instaluje ją w WordPressie
        bez ręcznego pakowania plików.
    """

    bundle_directory: str
    package_name: str


@dataclass
class WordPressSettings:
    """
    Technical description:
        Zawiera parametry integracji WordPress: informację czy integracja jest
        włączona, domyślny interwał synchronizacji oraz konfigurację generatora
        paczek instalacyjnych.

    Instructions for laika:
        "Tu zapisujemy, czy integracja z WordPressem działa, co ile godzin
        synchronizować dane i gdzie tworzyć paczkę ZIP."

    Example:
        ```python
        WordPressSettings(
            enabled=True,
            auto_sync_interval="PT12H",
            installer=WordPressInstallerConfig("build/installers", "open-data-plugin.zip")
        )
        ```

    Effect for end user:
        Zapewnia automatyczną synchronizację katalogu danych z WordPressem oraz
        szybkie przygotowanie instalatora.
    """

    enabled: bool
    auto_sync_interval: str
    installer: WordPressInstallerConfig


@dataclass
class WordPressSite:
    """
    Technical description:
        Reprezentuje zarejestrowaną instancję WordPress połączoną ze Studio
        Danych. Przechowuje adres strony, identyfikator klienta OAuth oraz datę
        ostatniej synchronizacji.

    Instructions for laika:
        "To wizytówka strony WordPress, którą połączyłeś z panelem. Widzisz tu
        adres, identyfikator i kiedy ostatnio synchronizowaliśmy dane."

    Example:
        ```python
        WordPressSite(site_url="https://wp.example.gov", client_id="odp-client", profile="dev")
        ```

    Effect for end user:
        Panel prezentuje listę stron WordPress korzystających z danych, co ułatwia
        zarządzanie publikacją i audyt.
    """

    site_url: str
    client_id: str
    profile: str
    registered_at: datetime
    last_sync: datetime | None = None


@dataclass
class InstallationPackage:
    """
    Technical description:
        Opisuje wygenerowaną paczkę instalacyjną WordPress. Pole `path`
        wskazuje plik ZIP, `generated_at` – czas utworzenia, a `size_bytes`
        – rozmiar paczki, co jest przydatne podczas audytu i monitoringu.

    Instructions for laika:
        "Po wygenerowaniu instalatora zapisujemy, gdzie leży plik, kiedy powstał
        i ile waży."

    Example:
        ```python
        InstallationPackage(path=Path("build/installers/open-data-plugin.zip"), generated_at=datetime.utcnow(), size_bytes=20480)
        ```

    Effect for end user:
        Administrator może łatwo pobrać i zarchiwizować paczkę instalacyjną,
        mając pełną informację o jej parametrach.
    """

    path: str
    generated_at: datetime
    size_bytes: int

