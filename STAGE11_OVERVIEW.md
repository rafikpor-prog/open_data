# Stage 11 – System uprawnień i audytu

## Cel dokumentu
Ten dokument podsumowuje funkcje wdrożone w etapie 11 projektu **Open Data Plugin** oraz wskazuje, gdzie w repozytorium znajduje się gotowa wtyczka WordPress.

## Zakres etapu 11
- Moduł `auth-service` (RBAC/ABAC) zarządzający rolami i regułami atrybutowymi zgodnymi z wymaganiami dane.gov.pl oraz API BDL.
- Zintegrowany audyt (retencja, eksport JSON) rejestrujący każdą decyzję autoryzacyjną i umożliwiający kontrolę zgodności z RODO oraz ENISA.
- Rozszerzony profil konfiguracji (`config/profiles/dev.json`) o sekcję `auth`, dzięki czemu `config-service` dystrybuuje uprawnienia i polityki audytu do wszystkich mikroserwisów.
- Testy jednostkowe (`tests/test_auth_service.py`) potwierdzające poprawność decyzji RBAC/ABAC oraz rejestrowanie wpisów audytowych.

## Komponenty techniczne
1. **`src/auth_service/rbac.py`** – definicje ról (`Role`), uprawnień (`Permission`) oraz reguł atrybutowych (`AttributeRule`).
2. **`src/auth_service/audit.py`** – klasy `AuditRecord` oraz `AuditTrail` zapisujące zdarzenia w plikach JSON wraz z retencją.
3. **`src/auth_service/service.py`** – `AuthorizationService`, który łączy RBAC z ABAC, integruje się z audytem i dostarcza decyzję `AccessDecision` dla Studio Danych, ingestu i mostka WordPress.
4. **`src/ingestion_service/profile.py`** – parser profili konfiguracyjnych obejmujący role, reguły ABAC i ustawienia audytu.
5. **`README.md`** – sekcja „System uprawnień i audytu – Etap 11” opisująca korzyści i instrukcję dla laika.
6. **`PROJECT_MEMORY.md`** – zaktualizowane rejestry plików, interfejsów, zależności, migracji oraz TODO, uwzględniające nowy moduł.

## Instrukcja dla laika
1. **Co zostało dodane?** System ról i audytu pilnujący, kto może publikować lub modyfikować dane. Każda akcja jest zapisywana w dzienniku, dzięki czemu można odtworzyć historię.
2. **Jak używać?** W panelu Studio Danych (etap 12) wybierzesz rolę dla użytkownika: np. `Administrator Danych` pozwala publikować, `Obserwator` tylko podgląda dane. Wszystkie uprawnienia pochodzą z profilu `auth` w konfiguracji.
3. **Przykład:** Administrator przypisuje roli „Analyst” możliwość odczytu datasetów w regionie „PL-MZ”. Gdy użytkownik poprosi o raport z innego regionu, audyt pokaże odmowę wraz z powodem.
4. **Efekt dla użytkownika końcowego:** Portal danych publicznych spełnia wymogi bezpieczeństwa i przejrzystości – wiadomo, kto widział lub edytował dane, a decyzje można zaskarżyć.

## Lokalizacja gotowej wtyczki WordPress
Kod produkcyjny wtyczki mostkowej znajduje się w katalogu: **`wordpress/open-data-plugin`**. Skopiuj go do `wp-content/plugins/` w swojej instalacji WordPress, a następnie aktywuj w panelu administratora, aby połączyć CMS z modułami Open Data Plugin.

## Kolejne kroki
- Etap 12 rozszerzy Studio Danych o zarządzanie użytkownikami i kreator autoinstalacji WordPress, wykorzystując opisane tu role i audyt.
- Przygotuj repozytorium GitOps z walidacją schematów `auth`, aby każda zmiana ról przechodziła przegląd bezpieczeństwa.
