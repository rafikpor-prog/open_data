"""
Module: tests.test_admin_gateway
Opis: Testy jednostkowe modułu panelu administracyjnego (etap 12) weryfikujące
obsługę menu, aktualizację ustawień, integrację WordPress oraz generowanie
instalatora ZIP.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from admin_gateway import AdminGatewayError, AdminGatewayService
from ingestion_service.profile import profile_from_dict


def load_profile() -> object:
    """
    Technical description:
        Ładuje profil `dev` z repozytorium GitOps (plik JSON) i konwertuje go na
        strukturę `ConfigProfile`.

    Instructions for laika:
        "Czytamy plik z ustawieniami, aby test mógł korzystać z tych samych
        danych co prawdziwy system."

    Example:
        ```python
        profile = load_profile()
        ```

    Effect for end user:
        Testy pracują na realistycznej konfiguracji, co zmniejsza ryzyko błędów
        podczas wdrożenia.
    """

    payload = json.loads(Path("config/profiles/dev.json").read_text(encoding="utf-8"))
    return profile_from_dict(payload)


def test_menu_is_filtered_by_permissions(tmp_path: Path) -> None:
    """
    Technical description:
        Sprawdza, czy użytkownik z rolą `data_viewer` widzi tylko pozycje menu
        wymagające uprawnienia `studio.dashboard.view`.

    Instructions for laika:
        "Nadajemy analitykowi rolę i upewniamy się, że w menu widzi tylko
        pulpit."

    Example:
        ```python
        test_menu_is_filtered_by_permissions(tmp_path)
        ```

    Effect for end user:
        Panel prezentuje wyłącznie dozwolone sekcje, co poprawia bezpieczeństwo.
    """

    profile = load_profile()
    service = AdminGatewayService(profile, plugin_root=Path("wordpress/open-data-plugin"))
    service.authorization_service.assign_role("carol", "data_viewer")

    menu = service.get_menu_for_user("carol")
    assert len(menu) == 1
    assert menu[0].key == "dashboard"


def test_update_branding_requires_permission() -> None:
    """
    Technical description:
        Weryfikuje, że próba aktualizacji brandingu przez użytkownika bez
        uprawnienia `studio.settings.update` kończy się błędem.

    Instructions for laika:
        "Użytkownik z prawami tylko do podglądu nie może zmienić logo – system
        powinien zgłosić błąd."

    Example:
        ```python
        test_update_branding_requires_permission()
        ```

    Effect for end user:
        Tylko uprawnieni administratorzy mogą modyfikować komunikaty w panelu.
    """

    profile = load_profile()
    service = AdminGatewayService(profile, plugin_root=Path("wordpress/open-data-plugin"))
    service.authorization_service.assign_role("dave", "data_viewer")

    try:
        service.update_branding("dave", announcement="Nowy komunikat")
    except AdminGatewayError as exc:
        assert "Brak uprawnień" in str(exc)
    else:
        raise AssertionError("Oczekiwano wyjątku AdminGatewayError")


def test_generate_installer_and_register_wordpress(tmp_path: Path) -> None:
    """
    Technical description:
        Potwierdza, że administrator może zmienić profil domyślny, zarejestrować
        stronę WordPress i wygenerować paczkę instalacyjną ZIP.

    Instructions for laika:
        "Administrator wybiera profil, dodaje stronę WordPress i pobiera
        przygotowany plik ZIP."

    Example:
        ```python
        test_generate_installer_and_register_wordpress(tmp_path)
        ```

    Effect for end user:
        Panel umożliwia obsługę całego cyklu integracji WordPress bez narzędzi
        zewnętrznych.
    """

    profile = load_profile()
    service = AdminGatewayService(profile, plugin_root=Path("wordpress/open-data-plugin"))
    service.authorization_service.assign_role("alice", "data_admin")
    service.authorization_service.assign_role("alice", "studio_admin")

    settings = service.set_default_profile("alice", "dev")
    assert settings.default_profile == "dev"

    site = service.register_wordpress_site(
        "alice",
        site_url="https://wp.example.gov",
        client_id="odp-client",
    )
    assert site.site_url == "https://wp.example.gov"
    assert service.list_wordpress_sites()

    package = service.generate_wordpress_installer("alice", output_directory=tmp_path)
    package_path = Path(package.path)
    assert package_path.exists()

    with zipfile.ZipFile(package_path, "r") as archive:
        files = archive.namelist()
        assert "open-data-plugin/open-data-plugin.php" in files
