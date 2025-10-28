"""
Module: admin_gateway.service
Opis: Implementuje `AdminGatewayService` odpowiedzialny za obsługę panelu
administracyjnego Studio Danych (etap 12). Serwis korzysta z konfiguracji
`ConfigProfile` i modułu autoryzacji (etap 11), aby zarządzać ustawieniami,
integracjami WordPress oraz generowaniem paczek instalacyjnych.
Funkcje i klasy:
- class AdminGatewayService: zarządza ustawieniami panelu, filtruje menu
  użytkownika i obsługuje integracje WordPress.
- class AdminGatewayError: wyjątek sygnalizujący błędy autoryzacji lub
  konfiguracji.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

from auth_service import AttributeRule, AuthorizationService, Permission, Role
from ingestion_service.profile import (
    AdminSettings,
    ConfigProfile,
    RoleDefinition,
)

from .models import (
    BrandingSettings,
    FeatureFlags,
    InstallationPackage,
    MenuItem,
    StudioSettings,
    WordPressInstallerConfig,
    WordPressSettings,
    WordPressSite,
)


class AdminGatewayError(RuntimeError):
    """
    Technical description:
        Wyjątek domenowy modułu panelu administracyjnego. Rzucany w przypadku
        braku uprawnień, nieprawidłowej konfiguracji lub błędów operacyjnych
        (np. brak katalogu z wtyczką WordPress).

    Instructions for laika:
        "Jeśli zobaczysz ten błąd, oznacza to, że brakuje uprawnień lub
        konfiguracja jest niepełna."

    Example:
        ```python
        raise AdminGatewayError("Brak uprawnień do aktualizacji ustawień")
        ```

    Effect for end user:
        Zapewnia przejrzyste komunikaty o problemach w panelu Studio Danych.
    """


@dataclass
class _AdminState:
    """
    Technical description:
        Utrzymuje bieżący stan panelu administracyjnego: ustawienia Studio
        Danych oraz zarejestrowane instancje WordPress.

    Instructions for laika:
        "To pamięć panelu – trzyma aktualne ustawienia i listę stron
        WordPress, które połączyliśmy."

    Example:
        ```python
        _AdminState(settings=studio_settings, wordpress_sites={})
        ```

    Effect for end user:
        Umożliwia szybkie odczytywanie konfiguracji bez ponownego parsowania
        profilu i zapewnia spójność między aktualizacjami a audytem.
    """

    settings: StudioSettings
    wordpress: WordPressSettings
    wordpress_sites: Dict[str, WordPressSite]


class AdminGatewayService:
    """
    Technical description:
        Udostępnia metody do zarządzania konfiguracją Studio Danych, filtrowania
        menu według ról, rejestrowania instancji WordPress oraz generowania
        paczek instalacyjnych. Integruje się z `AuthorizationService`, dzięki
        czemu każda operacja jest audytowana zgodnie z etapem 11.

    Instructions for laika:
        "To główny serwis panelu. Sprawdza, kto ma dostęp do ustawień, zapisuje
        konfigurację i przygotowuje plik ZIP z wtyczką WordPress."

    Example:
        ```python
        profile = profile_from_dict(json.load(open("config/profiles/dev.json")))
        service = AdminGatewayService(profile)
        service.authorization_service.assign_role("alice", "data_admin")
        menu = service.get_menu_for_user("alice")
        package = service.generate_wordpress_installer("alice")
        ```

    Effect for end user:
        Administrator otrzymuje jedno miejsce do zarządzania całym ekosystemem
        (Studio Danych + WordPress) z zachowaniem standardów dane.gov.pl i API
        BDL.
    """

    def __init__(
        self,
        profile: ConfigProfile,
        authorization_service: Optional[AuthorizationService] = None,
        plugin_root: Optional[Path] = None,
    ) -> None:
        self._profile = profile
        self._authorization = authorization_service or AuthorizationService()
        self._plugin_root = plugin_root or Path(__file__).resolve().parents[2] / "wordpress" / "open-data-plugin"
        self._state = self._build_state(profile.admin_settings)
        if profile.auth_policy:
            self._register_roles(profile.auth_policy.roles.values())

    @property
    def authorization_service(self) -> AuthorizationService:
        """Zwraca obiekt `AuthorizationService` używany przez panel."""

        return self._authorization

    def get_settings(self) -> StudioSettings:
        """
        Technical description:
            Zwraca bieżące ustawienia Studio Danych bez filtracji uprawnień.

        Instructions for laika:
            "Daje pełny obraz tego, jak jest skonfigurowany panel."

        Example:
            ```python
            settings = service.get_settings()
            ```

        Effect for end user:
            Ułatwia prezentację konfiguracji w panelu lub API administracyjnym.
        """

        return self._state.settings

    def get_menu_for_user(self, user_id: str) -> List[MenuItem]:
        """
        Technical description:
            Filtruje pozycje menu na podstawie uprawnień użytkownika. Pozycja
            jest widoczna, jeśli użytkownik posiada wszystkie wymagane
            uprawnienia (`menu.permissions`).

        Instructions for laika:
            "Sprawdzamy, które zakładki w menu ma zobaczyć dany użytkownik."

        Example:
            ```python
            menu = service.get_menu_for_user("analyst")
            ```

        Effect for end user:
            Panel ukrywa funkcje, do których użytkownik nie ma dostępu, co
            zwiększa przejrzystość i bezpieczeństwo.
        """

        visible: List[MenuItem] = []
        for item in self._state.settings.menu:
            if self._has_permissions(user_id, item.permissions):
                visible.append(item)
        return visible

    def update_branding(
        self,
        user_id: str,
        *,
        logo_url: Optional[str] = None,
        support_email: Optional[str] = None,
        announcement: Optional[str] = None,
    ) -> StudioSettings:
        """
        Technical description:
            Aktualizuje ustawienia brandingowe Studio Danych. Wymaga uprawnienia
            `studio.settings.update`.

        Instructions for laika:
            "Pozwala zmienić logo, adres wsparcia lub komunikat wyświetlany w
            panelu."

        Example:
            ```python
            service.update_branding(
                "admin",
                logo_url="https://example.gov/new-logo.svg",
                announcement="Aktualizacja o 22:00"
            )
            ```

        Effect for end user:
            Administrator może szybko dostosować komunikaty i branding do kampanii
            informacyjnych lub ostrzeżeń.
        """

        self._enforce(user_id, "studio.settings.update")
        branding = self._state.settings.branding
        updated = BrandingSettings(
            logo_url=logo_url if logo_url is not None else branding.logo_url,
            support_email=support_email if support_email is not None else branding.support_email,
            announcement=announcement if announcement is not None else branding.announcement,
        )
        self._state = replace(
            self._state,
            settings=replace(self._state.settings, branding=updated),
        )
        return self._state.settings

    def set_default_profile(self, user_id: str, profile_name: str) -> StudioSettings:
        """
        Technical description:
            Ustawia domyślny profil konfiguracji dla Studio Danych. Waliduje, czy
            profil znajduje się na liście dozwolonych oraz czy użytkownik posiada
            uprawnienie `studio.settings.update`.

        Instructions for laika:
            "Wybierasz, który profil (np. testowy lub produkcyjny) ma być domyślny
            w panelu."

        Example:
            ```python
            service.set_default_profile("admin", "dev")
            ```

        Effect for end user:
            Panel otwiera się od razu na odpowiednim profilu, co przyspiesza pracę
            administratorów danych.
        """

        self._enforce(user_id, "studio.settings.update")
        if profile_name not in self._state.settings.allowed_profiles:
            raise AdminGatewayError(f"Profil {profile_name} nie jest dozwolony")
        self._state = replace(
            self._state,
            settings=replace(self._state.settings, default_profile=profile_name),
        )
        return self._state.settings

    def register_wordpress_site(
        self,
        user_id: str,
        site_url: str,
        client_id: str,
        profile_name: Optional[str] = None,
    ) -> WordPressSite:
        """
        Technical description:
            Rejestruje instancję WordPress w panelu. Wymaga uprawnienia
            `wordpress.integrations.manage`. Zwraca obiekt `WordPressSite` z datą
            rejestracji.

        Instructions for laika:
            "Dodajesz stronę WordPress, która ma korzystać z danych – podajesz jej
            adres oraz identyfikator klienta OAuth."

        Example:
            ```python
            site = service.register_wordpress_site(
                "admin",
                site_url="https://wp.example.gov",
                client_id="odp-client"
            )
            ```

        Effect for end user:
            Panel przechowuje listę zaufanych instancji WordPress, co ułatwia audyt
            i zarządzanie integracjami.
        """

        self._enforce(user_id, "wordpress.integrations.manage")
        if not self._state.wordpress.enabled:
            raise AdminGatewayError("Integracja WordPress jest wyłączona w profilu")
        profile_name = profile_name or self._state.settings.default_profile
        if profile_name not in self._state.settings.allowed_profiles:
            raise AdminGatewayError(f"Profil {profile_name} nie jest dostępny dla WordPress")
        site = WordPressSite(
            site_url=site_url,
            client_id=client_id,
            profile=profile_name,
            registered_at=datetime.utcnow(),
        )
        self._state.wordpress_sites[site_url] = site
        return site

    def list_wordpress_sites(self) -> Sequence[WordPressSite]:
        """Zwraca listę zarejestrowanych instancji WordPress."""

        return list(self._state.wordpress_sites.values())

    def generate_wordpress_installer(
        self,
        user_id: str,
        output_directory: Optional[Path] = None,
    ) -> InstallationPackage:
        """
        Technical description:
            Generuje paczkę ZIP z wtyczką WordPress. Wymaga uprawnienia
            `wordpress.installers.generate`. Plik jest zapisywany w katalogu
            określonym w konfiguracji lub przekazanym jako argument.

        Instructions for laika:
            "System pakuje aktualną wtyczkę do pliku ZIP, który możesz pobrać i
            zainstalować w WordPressie."

        Example:
            ```python
            package = service.generate_wordpress_installer("admin")
            ```

        Effect for end user:
            Administrator pobiera aktualny pakiet instalacyjny bez ręcznego
            przygotowywania archiwum.
        """

        self._enforce(user_id, "wordpress.installers.generate")
        if not self._plugin_root.exists():
            raise AdminGatewayError(f"Nie znaleziono katalogu wtyczki: {self._plugin_root}")

        installer_cfg = self._state.wordpress.installer
        bundle_dir = Path(output_directory or installer_cfg.bundle_directory)
        bundle_dir.mkdir(parents=True, exist_ok=True)
        package_path = bundle_dir / installer_cfg.package_name

        with zipfile.ZipFile(package_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for path in self._plugin_root.rglob("*"):
                if path.is_file():
                    archive.write(path, path.relative_to(self._plugin_root.parent))

        size_bytes = package_path.stat().st_size
        package = InstallationPackage(
            path=str(package_path),
            generated_at=datetime.utcnow(),
            size_bytes=size_bytes,
        )
        return package

    # --- internal helpers -------------------------------------------------

    def _build_state(self, settings: Optional[AdminSettings]) -> _AdminState:
        if settings is None:
            raise AdminGatewayError("Profil nie zawiera sekcji admin – etap 12 wymaga konfiguracji panelu")
        studio = self._convert_studio_settings(settings)
        return _AdminState(
            settings=studio,
            wordpress=self._convert_wordpress_settings(settings),
            wordpress_sites={},
        )

    def _convert_studio_settings(self, settings: AdminSettings) -> StudioSettings:
        studio = settings.studio
        feature_flags = FeatureFlags(**studio.feature_flags)
        branding = BrandingSettings(
            logo_url=studio.branding.get("logo_url"),
            support_email=studio.branding.get("support_email", "support@example.gov"),
            announcement=studio.branding.get("announcement"),
        )
        menu = [
            MenuItem(
                key=item.get("id", item.get("key", "item")),
                label=item.get("label", item.get("id", "")),
                route=item.get("route", "/studio"),
                permissions=tuple(item.get("permissions", [])),
            )
            for item in studio.menu
        ]
        return StudioSettings(
            default_profile=studio.default_profile,
            allowed_profiles=tuple(studio.allowed_profiles),
            feature_flags=feature_flags,
            branding=branding,
            menu=tuple(menu),
        )

    def _convert_wordpress_settings(self, settings: AdminSettings) -> WordPressSettings:
        wp = settings.wordpress
        installer_cfg = WordPressInstallerConfig(
            bundle_directory=wp.installer["bundle_directory"],
            package_name=wp.installer["package_name"],
        )
        return WordPressSettings(
            enabled=wp.enabled,
            auto_sync_interval=wp.auto_sync_interval,
            installer=installer_cfg,
        )

    def _register_roles(self, definitions: Iterable[RoleDefinition]) -> None:
        for definition in definitions:
            permissions = {
                Permission(name=perm, description=f"Permission {perm}")
                for perm in definition.permissions
            }
            attribute_rules = [
                AttributeRule(
                    attribute=str(rule.get("attribute", "")),
                    allowed=set(rule.get("allowed")) if rule.get("allowed") else None,
                    denied=set(rule.get("denied")) if rule.get("denied") else None,
                    required=bool(rule.get("required", False)),
                    conditions={str(k): str(v) for k, v in (rule.get("conditions") or {}).items()},
                )
                for rule in definition.attribute_rules
            ]
            role = Role(
                name=definition.name,
                permissions=permissions,
                attribute_rules=attribute_rules,
                description=definition.description,
                inherits=set(definition.inherits),
            )
            self._authorization.register_role(role)

    def _has_permissions(self, user_id: str, permissions: Sequence[str]) -> bool:
        return all(self._authorization.enforce(user_id, perm).allowed for perm in permissions)

    def _enforce(self, user_id: str, permission: str) -> None:
        decision = self._authorization.enforce(user_id, permission)
        if not decision.allowed:
            raise AdminGatewayError(f"Brak uprawnień: {permission}")

