"""
Module: admin_gateway.__init__
Opis: Udostępnia wysokopoziomowe API modułu panelu administracyjnego (Studio
Danych) wdrożonego w etapie 12. Eksportuje modele i serwisy odpowiedzialne za
zarządzanie konfiguracją globalną, integracjami WordPress oraz tworzeniem
paczek instalacyjnych w zgodzie z wymaganiami dane.gov.pl, API BDL i
standardami UE.
Funkcje i klasy:
- class AdminGatewayService: warstwa zarządzania ustawieniami Studio Danych,
  autoryzacją i integracjami WordPress.
- class AdminGatewayError: wyjątek domenowy panelu administracyjnego.
- class StudioSettings: obiekt DTO z aktualnymi ustawieniami panelu.
- class WordPressSite: reprezentacja zarejestrowanej instancji WordPress.
- class InstallationPackage: opis wygenerowanej paczki instalacyjnej.
"""

from .models import InstallationPackage, StudioSettings, WordPressSite
from .service import AdminGatewayError, AdminGatewayService

__all__ = [
    "AdminGatewayError",
    "AdminGatewayService",
    "InstallationPackage",
    "StudioSettings",
    "WordPressSite",
]
