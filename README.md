# Open Data Plugin Blueprint

## Cel projektu
Wtyczka **Open Data Plugin** ma zapewniać integrację z polskimi i europejskimi standardami udostępniania danych (wzorce portalu [dane.gov.pl](https://dane.gov.pl), API BDL GUS) oraz umożliwiać modularną rozbudowę o kolejne źródła danych i wizualizacje.

## Obecne funkcjonalności (stan repozytorium)
Na obecnym etapie repozytorium nie zawiera kodu źródłowego ani gotowych modułów. Dostępna jest jedynie dokumentacja koncepcyjna:

| Funkcjonalność | Status | Opis techniczny | Instrukcja dla laika |
| --- | --- | --- | --- |
| Struktura plików projektu | ✔️ | Repozytorium zawiera pliki README oraz projektową pamięć (PROJECT_MEMORY) opisującą założenia rozwoju. | "Na razie mamy tylko plan działania. Kod zostanie dopiero przygotowany." |
| Dokumentacja koncepcyjna | ✔️ | Niniejszy dokument określa kierunek rozwoju i zgodność z krajowymi standardami danych. | "Tu przeczytasz, co powstanie w przyszłości i jakie są etapy pracy." |
| Specyfikacja techniczna – Etap 1 | ✔️ | Formalna specyfikacja wymagań funkcjonalnych i niefunkcjonalnych z mapą API, strukturą danych i zasadami bezpieczeństwa. | "Dowiesz się, jakie dokładnie funkcje powstaną i jakie standardy muszą spełniać." |
| Architektura systemu – Etap 2 | ✔️ | Zdefiniowano modułową architekturę logiczną, fizyczną i bezpieczeństwa zgodną z danymi.gov.pl, API BDL i standardami UE. | "Widzisz, z jakich części będzie się składać wtyczka i jak będą ze sobą współpracować." |
| Konfiguracja podstawowa – Etap 3 | ✔️ | Opracowano warstwę konfiguracji obejmującą `config-service`, katalog zmiennych, zarządzanie tajemnicami i integrację ze Studio Danych. | "Masz listę ustawień, gdzie je wpisać i jak bezpiecznie przechowywać hasła." |
| Import CSV – Etap 4 | ✔️ | Wdrożono moduł `ingestion-service` dla CSV z autodetekcją, podglądami i sugestiami wizualizacji. | "Wgraj plik CSV, wybierz profil i od razu zobacz raport wraz z propozycją wykresów." |
| Import XLSX – Etap 5 | ✔️ | Dodano moduł `ingestion-service` dla plików Excel z autodetekcją arkuszy, nagłówków i integracją z profilami konfiguracji. | "Wgraj arkusz Excel, a system sam wybierze arkusz i pokaże gotowy raport z propozycją wykresów." |
| Import JSON/API – Etap 6 | ✔️ | Wdrożono moduł `JSONIngestor` obsługujący pliki JSON i REST API (dane.gov.pl, API BDL) z walidacją, JSON Pointer i propozycjami wizualizacji. | "Podaj adres API lub plik JSON, a system sam pobierze dane i zaproponuje wykresy." |
| Obsługa URL i plików zdalnych – Etap 7 | ✔️ | Udostępniono `RemoteSyncManager` z harmonogramem synchronizacji URL, cache plików i integracją z importerami CSV/XLSX/JSON. | "Wskaż adres w internecie oraz częstotliwość, a system sam pobierze dane i odświeży katalog." |
| Integracja bazodanowa – Etap 8 | ✔️ | Wprowadzono `DatabaseIngestor` z obsługą profili `database_policy`, konektorami PostgreSQL/MySQL/MS SQL i generowaniem raportów `IngestionResult`. | "Wybierz bazę z listy i wskaż tabelę lub zapytanie, a system pobierze dane i przygotuje raport." |
| Silnik transformacji danych – Etap 9 | ✔️ | Dodano moduł `TransformationPipeline` realizujący czyszczenie, filtrowanie, kolumny pochodne i agregacje zgodne z DCAT-AP oraz API BDL. | "Po imporcie dane automatycznie się oczyszczą, przeliczą i przygotują do wizualizacji." |
| Warstwa metadanych – Etap 10 | ✔️ | Utworzono `metadata-service` z rejestrem DCAT-AP, eksportami JSON-LD/JSON:API i integracją z pipeline'em transformacji oraz wtyczką WordPress. | "Po przetworzeniu dane automatycznie trafiają do katalogu wraz z opisem, licencją i słowami kluczowymi." |
| System uprawnień i audytu – Etap 11 | ✔️ | Wdrożono moduł `auth-service` z rolami RBAC/ABAC, polityką audytu i integracją z profilami `config-service`. | "System pilnuje, kto może publikować dane, zapisuje każdą decyzję i pokazuje ją w dzienniku." |
| Panel administratora (Studio Danych) – Etap 12 | ✔️ | Dodano moduł `admin_gateway` z konfiguracją globalną, filtrowaniem menu po rolach, rejestracją instancji WordPress i generatorem paczek instalacyjnych ZIP. | "W panelu ustawisz adres API, zsynchronizujesz WordPressa i pobierzesz paczkę ZIP jednym kliknięciem." |
| Moduł wizualizacji podstawowych – Etap 13 | ✔️ | Udostępniono `visualization-service` generujący wykresy PNG/JPG/PDF z podglądów transformacji, zgodny z DCAT-AP i API BDL. | "Wskaż dane i typ wykresu, a system wygeneruje gotowy obraz i PDF do publikacji." |
| Zaawansowane wizualizacje i dashboardy – Etap 14 | ✔️ | Rozbudowano `visualization-service` o mapy (choroplety), heatmapy, wykresy kombinowane i panele KPI z raportami JSON oraz trybem zastępczym bez Matplotlib. | "Wybierz mapę lub dashboard KPI, a system przygotuje pliki do publikacji nawet w środowisku bez dodatkowych bibliotek." |
| Generator raportów – Etap 15 | ✔️ | Udostępniono `report_service` łączący wizualizacje, metadane DCAT-AP i pliki JSON-LD w raportach HTML/PDF z fallbackiem offline. | "Jednym kliknięciem wygenerujesz raport z wykresami, opisem i metadanymi gotowy do publikacji lub wysyłki." |
| Kompatybilność WordPress – moduł mostkowy | ✔️ | Do repozytorium dołączono wtyczkę `wordpress/open-data-plugin` integrującą się z kontraktami REST/GraphQL i wykorzystującą WordPress jako bazę publikacji. | "Skopiuj wtyczkę do katalogu WordPress, aktywuj i zarządzaj danymi w panelu Studio Danych." |

## Etap 1 – Szczegółowa specyfikacja techniczna
W ramach pierwszego etapu wykonano kompleksową analizę wymagań oraz opisano komponenty, które będą implementowane w kolejnych krokach.

### 1. Wymagania funkcjonalne
1. **Import danych**
   - Obsługa źródeł CSV, XLSX, JSON, REST API, URL oraz połączeń bazodanowych (PostgreSQL, MySQL, MS SQL) z autodetekcją struktury.
   - Mapowanie pól do słowników metadanych (zgodnie z DCAT-AP oraz wytycznymi dane.gov.pl i API BDL).
   - Mechanizm walidacji danych wejściowych (schematy JSON Schema, walidacja typów kolumn, kodowanie).
2. **Przetwarzanie i transformacje**
   - Pipeline ETL z modułami czyszczenia, filtrowania, agregacji i wzbogacania danych.
   - Definicja reguł biznesowych w YAML/JSON, możliwość wersjonowania reguł.
3. **Warstwa metadanych**
   - Centralny rejestr zbiorów danych z polami: tytuł, opis, źródło, aktualizacja, licencja, słowa kluczowe, jednostki administracyjne.
   - Automatyczna klasyfikacja według dziedzin tematycznych (GUS, INSPIRE) i zgodność z wymaganiami dostępności WCAG 2.1.
4. **Publikacja i wizualizacja**
   - API REST/GraphQL z autoryzacją OAuth 2.0 / OpenID Connect i limitami zapytań.
   - Generator wizualizacji (liniowe, słupkowe, kołowe, mapy, dashboardy) z eksportem PNG/JPG/PDF.
   - Obsługa scenariuszy, w których wizualizacja nie jest możliwa – komunikat **"BRAK MOŻLIWEJ WIZUALIZACJI"** wraz z rekomendacją działań.
5. **Panel administratora (Studio Danych)**
   - Zarządzanie połączeniami danych, harmonogramami, uprawnieniami i globalnymi ustawieniami wtyczki.
   - Warstwa audytu (logowanie akcji użytkowników, historia zmian, eksport logów).

### 2. Wymagania niefunkcjonalne
- **Bezpieczeństwo**: szyfrowanie danych w tranzycie (TLS 1.3), w spoczynku (AES-256), mechanizmy RBAC/ABAC, logowanie incydentów.
- **Skalowalność**: architektura mikroserwisowa z kolejkami (np. RabbitMQ/Kafka) oraz możliwością horyzontalnego skalowania ETL i API.
- **Dostępność**: SLA 99,5%, możliwość pracy w trybie HA (redundantne instancje, replikacja bazy danych).
- **Zgodność prawna**: RODO, krajowe wytyczne bezpieczeństwa danych publicznych, licencje Creative Commons.
- **Monitorowanie**: metryki Prometheus/OpenTelemetry, integracja z systemami SIEM.

### 3. Model API i formaty danych
- **Warstwa REST**:
  - Endpointy `GET /datasets`, `POST /datasets`, `GET /datasets/{id}`, `POST /datasets/{id}/ingest`, `GET /visualizations`.
  - Standardy odpowiedzi: JSON:API z metadanymi paginacji i statusów.
  - Obsługa filtrów zapytań (parametry query), sortowania oraz `fields` do wyboru kolumn.
- **Warstwa GraphQL**:
  - Schemat z typami `Dataset`, `Resource`, `Visualization`, `IngestionJob` i `User`.
  - Mutacje do uruchamiania importów, tworzenia wizualizacji oraz konfiguracji harmonogramów.
- **Formaty wejściowe**: CSV (UTF-8, autodetekcja separatora), XLSX (wielokrotne arkusze), JSON/NDJSON, API REST (OpenAPI 3.1), URL (HTTP/HTTPS, SFTP), Bazy danych (JDBC/ODBC z tunelowaniem SSH).
- **Formaty wyjściowe**: JSON:API, GraphQL responses, eksporty CSV/XLSX, wizualizacje PNG/JPG/PDF, raporty PDF/HTML.

### 4. Integracja ze standardami
- **dane.gov.pl**: kompatybilny model metadanych, mapowanie do pól DCAT-AP, obsługa importu z API CKAN.
- **API BDL**: gotowy konektor REST z obsługą parametrów (jednostka, miara, czas), cache wyników i limitów zapytań.
- **Standardy UE**: INSPIRE, DCAT-AP, eIDAS dla uwierzytelniania, wytyczne ENISA dot. bezpieczeństwa danych publicznych.

### 5. Scenariusze użytkowe
1. **Administrator danych publicznych**
   - *Opis techniczny*: konfiguracja nowego źródła CSV, przypisanie harmonogramu aktualizacji, mapowanie metadanych do schematów DCAT-AP.
   - *Instrukcja dla laika*: "Wgraj plik z danymi, wybierz jak często ma się aktualizować i nazwij kolumny prostymi opisami. System zadba o resztę."
2. **Analityk**
   - *Opis techniczny*: tworzenie wizualizacji oraz eksport raportów poprzez panel Studio Danych i API.
   - *Instrukcja dla laika*: "Wybierz zbiór danych, wskaż typ wykresu i pobierz go jako obraz lub PDF."
3. **Partner integrujący**
   - *Opis techniczny*: integracja z API publikacyjnym, wykorzystanie tokenów OAuth 2.0, pobieranie danych przez REST/GraphQL.
   - *Instrukcja dla laika*: "Użyj klucza dostępu, aby wgrać lub pobrać dane do swojej aplikacji bez ręcznego pobierania plików."

### 6. Kryteria akceptacyjne etapu 1
- Dokumentacja zawiera komplet wymagań funkcjonalnych, niefunkcjonalnych i zgodności ze standardami.
- Zdefiniowano strukturę API, formaty danych oraz scenariusze użytkowe.
- Zapisano wymagania dla panelu administratora oraz mechanizmu wizualizacji i eksportu.
- Przygotowano instrukcje dla interesariuszy technicznych i nietechnicznych.

## Etap 2 – Architektura systemu
Etap 2 dostarcza opis modułowej architektury referencyjnej, która spełnia wymagania etapu 1 i pozwala na przyrostową implementację kolejnych funkcji. Architekturę opracowano w oparciu o dobre praktyki portalu dane.gov.pl, API BDL oraz standardy UE (DCAT-AP, INSPIRE, WCAG 2.1, RODO).

### 1. Architektura logiczna
- **Warstwa prezentacji (Studio Danych + portale danych)**
  - Komponenty: Panel administratora (Studio Danych), Panel analityka, Publiczny katalog danych.
  - Technologia referencyjna: SPA (React/Vue) z SSR dla dostępności, biblioteki wizualizacji (D3.js, Chart.js, Leaflet).
  - Integracja: autoryzacja OAuth 2.0/OIDC, zgodność WCAG 2.1 AA.
  - Dla laika: "To główny ekran, z którego zarządzasz danymi, tworzysz wykresy i publikujesz je w katalogu."
- **Warstwa aplikacyjna (Backend usługowy)**
  - Usługi: `ingestion-service`, `etl-service`, `metadata-service`, `visualization-service`, `auth-service`, `admin-gateway`.
  - Każda usługa eksponuje REST/GraphQL zgodny z JSON:API, wspólny katalog schematów OpenAPI 3.1.
  - Komunikacja asynchroniczna przez kolejkę (RabbitMQ/Kafka) dla zadań ETL.
  - Dla laika: "Tu dzieje się magia – serwer przyjmuje pliki, czyści dane i udostępnia je innym."
- **Warstwa danych**
  - Baza relacyjna (PostgreSQL) dla metadanych, konfiguracji i logów audytu.
  - Hurtownia analityczna (np. ClickHouse/Snowflake opcjonalnie) dla zestawień i dashboardów.
  - Obiektowy storage (S3-kompatybilny) na pliki źródłowe i rendery wizualizacji.
  - Dla laika: "To sejf na dane i ich opisy."
- **Warstwa integracji zewnętrznych**
  - Konektory do API dane.gov.pl (CKAN), API BDL, usług INSPIRE, usług eIDAS.
  - Broker webhooków do powiadamiania partnerów o aktualizacjach.
  - Dla laika: "Dzięki temu pobieramy dane z państwowych źródeł i wysyłamy je dalej."

### 2. Architektura fizyczna (referencyjna)
- **Konteneryzacja**: każdy mikroserwis w kontenerze (Docker/OCI), orkiestracja przez Kubernetes/K3s.
- **Warstwy sieciowe**: ingress z TLS 1.3, WAF, segmentacja sieci (DMZ dla API publicznego, strefa chroniona dla ETL).
- **CI/CD**: pipeline z testami bezpieczeństwa (SAST/DAST), skanowanie zależności, deployment etapowy (dev → staging → prod).
- **Monitoring**: Prometheus, Grafana, OpenTelemetry, centralne logowanie (ELK/Opensearch).
- **Compliance**: zgodność z wymogami RODO (rezydencja danych UE), backupy geo-redundantne.
- *Instrukcja dla laika*: "System działa w chmurze/kontenerach, ma kopie zapasowe i monitorowanie, żeby działał stabilnie i bezpiecznie."

### 3. Przepływy danych (Data Flows)
1. **Import (ETL) – scenariusz CSV**
   - Użytkownik dodaje źródło w Studio Danych → `admin-gateway` zapisuje konfigurację → `ingestion-service` pobiera plik → wrzuca zadanie na kolejkę → `etl-service` przetwarza i zapisuje dane do hurtowni → `metadata-service` aktualizuje rejestr → `visualization-service` generuje podgląd.
   - Kontrole: walidacja schematów, sanity checks (Great Expectations), zapisy audytu.
   - Dla laika: "Wgrywasz plik, system go sprawdza i przygotowuje do wykresów."
2. **Import z API BDL**
   - Harmonogram uruchamia konektor → `ingestion-service` pobiera dane przez REST z parametrami (jednostka, miara, okres) → pipeline ETL jak wyżej.
   - Cache wyników oraz limity zapytań zgodne z API BDL.
   - Dla laika: "System sam pobiera dane z GUS, żebyś nie musiał tego robić ręcznie."
3. **Publikacja i wizualizacja**
   - Analityk wybiera zbiór → `visualization-service` pobiera dane z hurtowni → proponuje typy wykresów (heurystyki na podstawie typów danych) → renderuje wykres → zapisuje do storage → API udostępnia plik PNG/PDF.
   - Jeśli brak wspieranego typu: zwracany komunikat **"BRAK MOŻLIWEJ WIZUALIZACJI"** + rekomendacja (np. zmiana zakresu danych).
   - Dla laika: "System podpowie najlepszy wykres i pozwoli go pobrać."
4. **Administracja i audyt**
   - Panel Studio Danych komunikuje się z `auth-service` (SSO eIDAS/LDAP), RBAC/ABAC przydziela role.
   - Każda akcja logowana w `audit_log` (kto, co, kiedy), dostępne raporty w panelu.
   - Dla laika: "Wiesz, kto zmienił dane i możesz to sprawdzić w historii."

### 4. Model bezpieczeństwa i zgodności
- **Identyfikacja i uwierzytelnianie**: OAuth 2.0/OIDC, możliwość logowania Profilem Zaufanym (eIDAS), MFA dla administratorów.
- **Autoryzacja**: RBAC (role: Administrator Systemu, Administrator Danych, Analityk, Partner API, Gość) z opcją ABAC (atrybuty datasetu, klasyfikacja).
- **Szyfrowanie**: TLS 1.3, certyfikaty ACME/eIDAS Qualified; dane w spoczynku szyfrowane AES-256, klucze w HSM.
- **Audyt i zgodność**: logi niezmienialne (WORM), raporty zgodne z wymogami NASK/CSIRT, check-listy RODO/DCAT-AP.
- **Dla laika**: "System pilnuje, żeby tylko uprawnione osoby miały dostęp, a wszystkie działania są zapisane."

### 5. Mapowanie etapów rozwoju na komponenty
| Etap | Komponenty docelowe | Kluczowe zależności | Notatka dla laika |
| --- | --- | --- | --- |
| 2 | Architektura logiczna, fizyczna, bezpieczeństwa | Kubernetes, RabbitMQ/Kafka, PostgreSQL, S3, OAuth 2.0 | "Wiemy, jak system ma wyglądać i z czego się składać." |
| 3 | Konfiguracja podstawowa | `admin-gateway`, `config-service`, repozytorium konfiguracji | "Pojawi się panel ustawień i pliki konfiguracyjne." |
| 4–8 | Ingestion + ETL | `ingestion-service`, `etl-service`, kolejki | "Dodasz różne źródła danych, a system sam je przygotuje." |
| 9–10 | Metadane | `metadata-service`, PostgreSQL | "Dane będą opisane i łatwe do znalezienia." |
| 11–12 | Uprawnienia, Studio Danych | `auth-service`, `admin-gateway`, SPA | "Zarządzasz zespołem i ustawieniami w jednym miejscu." |
| 13–15 | Wizualizacje i raporty | `visualization-service`, biblioteki wykresów | "Tworzysz wykresy i raporty jednym kliknięciem." |
| 16–20 | Publikacja, automatyzacja, monitoring | API REST/GraphQL, webhooki, monitoring | "Dane będą zawsze aktualne i dostępne dla partnerów." |

### 6. Kryteria akceptacyjne etapu 2
- Udokumentowano architekturę logiczną, fizyczną i bezpieczeństwa kompatybilną z wymaganiami etapu 1.
- Zdefiniowano przepływy danych dla kluczowych scenariuszy (CSV, API BDL, wizualizacje, administracja).
- Określono komponenty mikroserwisowe i ich kontrakty integracyjne (REST/GraphQL, kolejki, storage).
- Ustalono referencyjne technologie i standardy bezpieczeństwa (TLS, eIDAS, RBAC/ABAC, WORM, backupy UE).
- Przygotowano mapowanie etapów rozwoju na komponenty, co wspiera planowanie wdrożeń.

## Etap 3 – Warstwa konfiguracji podstawowej
Etap 3 dostarcza spójny model zarządzania konfiguracją całej wtyczki – od katalogu zmiennych środowiskowych, przez `config-service`, po procesy tajemnic i integrację z panelem Studio Danych. Warstwa została zaprojektowana w zgodzie z wymaganiami dane.gov.pl, API BDL i regulacjami UE dotyczącymi bezpieczeństwa informacji.

### 1. Zakres i cele
- Zapewnienie jednego źródła prawdy dla konfiguracji globalnej, modułowej oraz środowiskowej.
- Automatyzacja propagacji ustawień do mikroserwisów (`ingestion-service`, `etl-service`, `metadata-service`, `visualization-service`, `auth-service`, `admin-gateway`).
- Zgodność z politykami bezpieczeństwa RODO i ENISA poprzez kontrolę dostępu, wersjonowanie i audyt konfiguracji.
- *Dla laika*: "Mamy centralną tabelkę ustawień, która pilnuje haseł, adresów serwerów i kluczy tak, by wszystko działało bez ręcznej konfiguracji."

### 2. Model `config-service`
- **Architektura**: lekki mikroserwis zarządzający konfiguracją, udostępniający API REST (`/config/v1`) oraz kanał publikacji zdarzeń (`config.updated`).
- **Magazyn danych**: schemat `config` w PostgreSQL z tabelami `config_items`, `config_versions`, `config_audit` (współdzielone z modułem audytu etapu 2).
- **Mechanizmy**:
  - Walidacja JSON Schema dla każdej kategorii ustawień.
  - Wersjonowanie – każda zmiana tworzy nowy rekord w `config_versions` z podpisem kryptograficznym.
  - Wydawanie tokenów dostępu (mTLS + OAuth 2.0 client credentials) dla mikroserwisów pobierających konfigurację.
- **Integracja**:
  - `admin-gateway` udostępnia widoki Studio Danych do edycji konfiguracji.
  - Mikroserwisy subskrybują komunikaty `config.updated` przez RabbitMQ/Kafka i odświeżają cache konfiguracji.
- *Instrukcja dla laika*: "Jest specjalna usługa, która przechowuje ustawienia i rozsyła je automatycznie do wszystkich części systemu."

### 3. Katalog zmiennych środowiskowych
Katalog obejmuje zmienne globalne, modułowe i infrastrukturalne. Każda ma opis techniczny i instrukcję dla użytkownika nietechnicznego.

| Kategoria | Zmienna | Opis techniczny | Instrukcja dla laika |
| --- | --- | --- | --- |
| Globalne | `ODP_ENV` | Identyfikator środowiska (`dev`/`staging`/`prod`) używany do selekcji profili konfiguracyjnych. | "Wybierz, czy pracujesz na wersji testowej czy produkcyjnej." |
| Bezpieczeństwo | `ODP_SECRETS_BACKEND` | Wybór backendu tajemnic (`vault`, `aws-kms`, `azure-key-vault`). | "Zaznacz, gdzie trzymamy hasła – w sejfie lokalnym albo chmurowym." |
| Bazy danych | `ODP_DB_URL` | Łącze do głównej bazy PostgreSQL z parametrami TLS i poolingiem. | "Wpisz adres bazy danych, z której korzysta system." |
| Kolejki | `ODP_BROKER_URL` | Adres brokera RabbitMQ/Kafka wraz z politykami retry. | "Podaj adres kolejki, która obsługuje zadania w tle." |
| API | `ODP_PUBLIC_URL` | Publiczny adres domeny używany przez katalog danych i Studio Danych. | "To link, pod którym użytkownicy zobaczą portal." |
| Wizualizacje | `ODP_CHART_DEFAULTS` | Ścieżka do pliku YAML z domyślnymi szablonami wykresów. | "Tu wskazujesz plik, który zawiera wzory wykresów." |
| Integracje | `ODP_DANE_GOV_API_KEY` | Klucz dostępu do API dane.gov.pl przechowywany w backendzie tajemnic. | "Hasło do portalu państwowego – trzymane w sejfie." |
| Monitorowanie | `ODP_TELEMETRY_ENDPOINT` | Endpoint do kolektora OpenTelemetry, z którym łączą się mikroserwisy. | "Adres serwera, który zbiera informacje o działaniu systemu." |

Dodatkowe zasady:
- Każda zmienna posiada metadane: typ, poziom wrażliwości, politykę rotacji.
- `config-service` generuje pliki `.env` per środowisko na potrzeby bootstrappingu i zapisuje je zaszyfrowane (AES-256) w repozytorium konfiguracji.

### 4. Zarządzanie tajemnicami i rotacja
- **Backend tajemnic**: rekomendowany HashiCorp Vault z pluginem PKI i silnikiem K/V v2; alternatywy: AWS Secrets Manager, Azure Key Vault.
- **Proces**:
  1. Administrator w Studio Danych tworzy rekord tajemnicy (np. hasło API BDL) → dane trafiają do Vault.
  2. `config-service` zapisuje referencję (`vault://path/to/secret`) zamiast wartości w `config_items`.
  3. Mikroserwis przy odczycie konfiguracji pobiera wartość z Vault przy użyciu tokena rolowego.
  4. Rotacja wymuszana jest polityką (np. co 90 dni) – `config-service` generuje zadanie w `etl-service`, które aktualizuje powiązane zasoby.
- **Bezpieczeństwo**: MFA dla operacji tajemnic, rejestr audytowy w `config_audit`, powiadomienia o rotacjach.
- *Instrukcja dla laika*: "Hasła i klucze trzymamy w cyfrowym sejfie. W systemie widzisz tylko nazwę sejfu, a hasło pobierane jest automatycznie, kiedy jest potrzebne."

### 5. Procesy operacyjne
- **Bootstrap środowiska**:
  - Skrypt `configctl bootstrap` łączy się z Vault, tworzy początkowe tajemnice i generuje plik `.env` z minimalnym zestawem zmiennych.
  - Wersjonowane snapshoty konfiguracji trafiają do repozytorium GitOps (`config-repo`).
- **Walidacja**:
  - Każda zmiana przechodzi pipeline CI (`config-ci`) sprawdzający spójność schematów JSON, wartości zakresów i zgodność z politykami RODO.
  - Testy smoke uruchamiane przez `config-service` weryfikują, czy mikroserwisy mogą pobrać nowe ustawienia.
- **Rollout**:
  - Zmiany publikowane są jako komunikat `config.updated` z identyfikatorem wersji.
  - Mikroserwisy potwierdzają odbiór (ACK). Brak potwierdzenia → alert w Prometheus + wpis w `config_audit`.
- *Instrukcja dla laika*: "Gdy zmienisz ustawienie, system je sprawdzi, zapisze kopię bezpieczeństwa i da znać wszystkim usługom, żeby używały nowych danych."

### 6. Integracja ze Studio Danych
- **Panel ustawień globalnych**: sekcja umożliwia edycję zmiennych oznaczonych jako bezpieczne do edycji ręcznej (np. `ODP_PUBLIC_URL`, `ODP_ENV`).
- **Tryb eksperta**: ukryty za uprawnieniem "Administrator Systemu" umożliwia zarządzanie tajemnicami i politykami rotacji.
- **Asystent konfiguracji**: kreator krok po kroku (wizard) prowadzący przez konfigurację środowiska, z kontrolą poprawności.
- **Przykład dla laika**: "W panelu wybierasz opcję 'Skonfiguruj połączenie z GUS', wpisujesz identyfikator klienta, a system sam zapisuje go w sejfie i ustawia harmonogram odświeżania."

### 7. Kryteria akceptacyjne etapu 3
- Istnieje kompletny katalog zmiennych środowiskowych z opisami technicznymi i instrukcjami dla laików.
- Zdefiniowano architekturę `config-service`, w tym magazyn danych, wersjonowanie, walidacje i integrację z mikroserwisami.
- Przygotowano proces zarządzania tajemnicami wraz z rotacją, audytem i powiadomieniami zgodnymi z RODO.
- Opracowano procedury bootstrapu, walidacji i rolloutów konfiguracji oraz ich powiązanie z pipeline CI/CD.
- Studio Danych otrzymało opisane widoki i uprawnienia do zarządzania konfiguracją.

## Etap 3A – Kontrakty API mikroserwisów
Etap 3A rozszerza efekty warstwy konfiguracji, dostarczając precyzyjne kontrakty OpenAPI oraz GraphQL SDL dla kluczowych mikroserwisów. Dzięki temu zespoły backend, frontend i integracyjne mogą implementować funkcje w sposób spójny z konfiguracją, bezpieczeństwem i standardami dane.gov.pl, API BDL oraz DCAT-AP.

### 1. Zasady ogólne kontraktów
- **Versioning**: wszystkie API REST publikują specyfikacje w ścieżce `/openapi/v1` i stosują nagłówek `Accept: application/vnd.opendata.v1+json`.
- **Standard odpowiedzi**: JSON:API (pole `data`, `meta`, `links`), błędy w formacie RFC 7807.
- **Autoryzacja**: OAuth 2.0 (client credentials dla mikroserwisów, authorization code/PKCE dla użytkowników), nagłówek `Authorization: Bearer <token>`.
- **Idempotencja**: operacje modyfikujące wspierają nagłówek `Idempotency-Key`.
- **Śledzenie**: nagłówki `X-Correlation-Id`, `X-Request-Id` propagowane między usługami, zgodnie z polityką audytu etapu 2.
- *Instrukcja dla laika*: "Każda część systemu ma własny zestaw adresów internetowych opisanych w jednym miejscu. Dzięki temu programiści wiedzą, jak się komunikować, a Ty masz pewność, że wszystko działa według ustalonych zasad."

### 2. `admin-gateway` (Studio Danych)
| Metoda | Ścieżka | Opis techniczny | Instrukcja dla laika |
| --- | --- | --- | --- |
| `GET` | `/admin/v1/config/profiles` | Lista profili konfiguracji dostępnych w środowisku; filtry `environment`, `status`. | "Sprawdź, jakie zestawy ustawień są przygotowane (np. testowe, produkcyjne)." |
| `POST` | `/admin/v1/config/profiles/{profileId}/activate` | Aktywacja profilu; walidacja zależności (DB, kolejki). | "Wybierz profil i włącz go jednym kliknięciem." |
| `GET` | `/admin/v1/datasets` | Proxy do `metadata-service` z dodatkowymi filtrami uprawnień. | "Zobacz listę zbiorów danych w panelu." |
| `POST` | `/admin/v1/ingestions` | Tworzenie zadania importu, przekazanie konfiguracji do `ingestion-service`. | "Rozpocznij pobieranie danych z nowego źródła." |

Przykładowy fragment OpenAPI (`admin-gateway`):
```yaml
paths:
  /admin/v1/config/profiles:
    get:
      summary: List configuration profiles
      security:
        - oauth2: [admin.read]
      responses:
        '200':
          description: Profiles list
          content:
            application/vnd.opendata.v1+json:
              schema:
                $ref: '#/components/schemas/ProfileCollection'
```

### 3. `config-service`
- **REST**:
  - `GET /config/v1/items/{key}` – zwraca efektywną wartość klucza wraz z metadanymi (źródło, wersja, wrażliwość).
  - `PUT /config/v1/items/{key}` – aktualizuje wartość, wymaga schematu JSON oraz podpisu osoby zatwierdzającej (`X-Approval-Signature`).
  - `POST /config/v1/rollouts` – inicjuje rollout konfiguracji do usług docelowych.
- **GraphQL (`configSchema.graphql`)**:
```graphql
type ConfigItem {
  key: ID!
  value: JSON!
  version: String!
  sensitivity: SensitivityLevel!
  updatedAt: DateTime!
}

type Query {
  configItem(key: ID!): ConfigItem
  configItems(filter: ConfigFilterInput): [ConfigItem!]!
}

type Mutation {
  updateConfigItem(input: UpdateConfigItemInput!): ConfigItem!
  triggerRollout(profileId: ID!): Rollout!
}
```
- **Zdarzenia** (`config.updated`, `config.rollout.failed`) – publikowane do RabbitMQ/Kafka z ładunkiem JSON:API.
- *Instrukcja dla laika*: "Serwis konfiguracji ma własny katalog ustawień. Możesz podejrzeć konkretne hasło (jeśli masz uprawnienia) albo zmienić je w jednym miejscu, a system sam powiadomi pozostałe elementy."

### 4. `ingestion-service`
- **REST**:
  - `POST /ingestion/v1/jobs` – tworzy zadanie pobrania; body zawiera `sourceType`, `connectionId`, `schedule`.
  - `GET /ingestion/v1/jobs/{id}` – status zadania; pola `state`, `progress`, `lastError`.
  - `POST /ingestion/v1/connectors/test` – test połączenia (CSV, XLSX, JSON, API, URL, DB) z autodetekcją schematu.
- **GraphQL (moduł `Ingestion` w głównym schemacie)**:
```graphql
type IngestionJob {
  id: ID!
  sourceType: SourceType!
  datasetId: ID
  status: JobStatus!
  suggestedVisualizations: [VisualizationHint!]!
}

extend type Mutation {
  createIngestionJob(input: CreateIngestionJobInput!): IngestionJob!
  retryIngestionJob(id: ID!): IngestionJob!
}
```
- **Zdarzenia**: `ingestion.job.created`, `ingestion.job.completed`, `ingestion.job.failed` – konsumowane przez `etl-service`.
- *Instrukcja dla laika*: "Gdy tworzysz import danych, serwis zapisuje zlecenie, sprawdza połączenie i podpowiada, jakie wykresy będą pasować do nowych danych."

### 5. `etl-service`
- **REST**:
  - `POST /etl/v1/pipelines` – definiuje pipeline ETL z krokami walidacji (Great Expectations) i transformacjami.
  - `POST /etl/v1/pipelines/{id}/run` – uruchamia pipeline, przyjmuje parametry `ingestionJobId`, `configVersion`.
  - `GET /etl/v1/pipelines/{id}/metrics` – metryki jakości i wydajności.
- **GraphQL (moduł `ETL`)** – zapytania o historię pipeline, raporty jakości.
- **Zdarzenia**: `etl.pipeline.started`, `etl.pipeline.completed`, `etl.pipeline.quality_alert` – przekazywane do `metadata-service` i `admin-gateway`.
- *Instrukcja dla laika*: "Serwis przetwarzania mówi, na jakim etapie jest czyszczenie danych i czy wszystko poszło dobrze. Jeśli coś się nie uda, zobaczysz ostrzeżenie w panelu."

### 6. `metadata-service`
- **REST**:
  - `GET /metadata/v1/datasets` – lista zbiorów z filtrami DCAT-AP (`theme`, `spatial`, `keyword`).
  - `POST /metadata/v1/datasets` – tworzenie zbioru; walidacja licencji (Creative Commons, Open Data Commons).
  - `PATCH /metadata/v1/datasets/{id}` – aktualizacja z wykorzystaniem JSON Patch.
- **GraphQL**:
```graphql
type Dataset {
  id: ID!
  title: MultilingualString!
  description: MultilingualString!
  themes: [String!]!
  distributions: [Distribution!]!
}

extend type Query {
  datasets(filter: DatasetFilter, pagination: PaginationInput): DatasetConnection!
}

extend type Mutation {
  upsertDataset(input: UpsertDatasetInput!): Dataset!
}
```
- **Zdarzenia**: `metadata.dataset.published`, `metadata.dataset.updated` – konsumowane przez `visualization-service` i katalog publiczny.
- *Instrukcja dla laika*: "Tutaj powstaje wizytówka każdego zbioru danych – tytuł, opis, słowa kluczowe. Gdy coś zmienisz, nowe informacje od razu trafiają do katalogu."

### 7. `visualization-service`
- **REST**:
  - `POST /visualization/v1/charts` – generowanie wizualizacji; parametry `datasetId`, `chartType`, `encoding`.
  - `GET /visualization/v1/charts/{id}` – status renderu, URL do pliku PNG/JPG/PDF.
  - `GET /visualization/v1/suggestions` – heurystyczne sugestie typów wykresów na podstawie struktury danych.
- **GraphQL** – pola `Visualization`, `VisualizationSuggestion`, mutacje `createVisualization`, `exportVisualization`.
- **Zdarzenia**: `visualization.render.completed`, `visualization.render.failed` (w przypadku braku możliwości wizualizacji komunikat **"BRAK MOŻLIWEJ WIZUALIZACJI"** przekazywany w polu `message`).
- *Instrukcja dla laika*: "Wybierasz zbiór danych i typ wykresu, a serwis tworzy obraz, który możesz pobrać. Jeśli się nie da, dostajesz jasny komunikat, co poprawić."

### 8. `auth-service`
- **REST**:
  - `POST /auth/v1/token` – wydawanie tokenów OAuth 2.0/OIDC z profilami eIDAS.
  - `GET /auth/v1/users/me` – informacje o aktualnym użytkowniku i rolach RBAC/ABAC.
  - `POST /auth/v1/invitations` – zapraszanie nowych użytkowników Studio Danych.
- **GraphQL** – rozszerzenie typu `User`, mutacje `assignRole`, `revokeRole`.
- **Zdarzenia**: `auth.user.role_changed`, `auth.mfa.challenge_required` – konsumowane przez `admin-gateway` i `config-service` (do blokady tajemnic przy MFA).
- *Instrukcja dla laika*: "Ten serwis pilnuje logowania. Dzięki niemu zalogujesz się Profilem Zaufanym lub innym sposobem i otrzymasz odpowiednie uprawnienia."

### 9. Interfejsy zdarzeniowe i GitOps
- Wszystkie zdarzenia opisane są w schemacie AsyncAPI (`/asyncapi/v1`), z kanałami per mikroserwis.
- Repozytorium GitOps przechowuje pliki `openapi.yaml`, `graphql/*.graphql`, `asyncapi.yaml` – aktualizowane automatycznie przez pipeline `config-ci`.
- Zależność od `config-service`: każda publikacja kontraktu wymaga podpisania wersji konfiguracji (`config_version`) zapewniającej spójność z tajemnicami.
- *Instrukcja dla laika*: "Dokumenty z opisem API są trzymane w jednym repozytorium. Każda zmiana przechodzi automatyczne testy, więc masz pewność, że integracje zewnętrzne nie przestaną działać."

### 10. Kryteria akceptacyjne etapu 3A
- Dostępne są kompletne kontrakty OpenAPI/GraphQL/AsyncAPI dla głównych mikroserwisów, zgodne z politykami bezpieczeństwa.
- Kontrakty opisują wszystkie krytyczne ścieżki: konfigurację, import danych, ETL, metadane, wizualizacje, uwierzytelnianie.
- Udokumentowano zależności między kontraktami a `config-service`, w tym propagację wersji i tajemnic.
- Studio Danych posiada referencję do kontraktów, aby zespół frontend mógł generować klienty API.
- Przygotowano instrukcje dla użytkowników nietechnicznych, jak korzystać z nowych interfejsów.

## Etap 4 – Obsługa importu CSV
Etap 4 dostarcza pierwszy działający moduł kodu, który realizuje przepływ importu CSV zgodny z kontraktami `ingestion-service` i profilami konfiguracji opracowanymi w etapach 3 i 3A. Implementacja bazuje na module `src/ingestion_service` i zapewnia pełny pipeline od wczytania pliku do wygenerowania raportu dla Studio Danych.

### 1. Zakres implementacji
- **Silnik importu (`CSVIngestor`)**: walidacja rozmiaru pliku, autodetekcja separatora, analiza nagłówków i typów kolumn, zapis podglądu JSON oraz kopiowanie pliku do strefy landing.
- **Obsługa profili konfiguracji**: wykorzystanie `config-service` lub repozytorium GitOps (`config/profiles/<profil>.json`) do ładowania polityk ingestu, ścieżek storage oraz ustawień bezpieczeństwa.
- **Sugestie wizualizacji**: heurystyki rekomendujące wykres liniowy lub słupkowy w zależności od wykrytych kolumn, z komunikatem **"BRAK MOŻLIWEJ WIZUALIZACJI"** w przypadku braku dopasowania.
- **CLI i integracja testowa**: uruchamianie przez `python -m ingestion_service` z wykorzystaniem zmiennych środowiskowych (`ODP_PROFILE`, `ODP_CSV_SOURCE`, `ODP_DATASET_ID`).

### 2. Silnik `CSVIngestor`
- *Opis techniczny*: kod źródłowy w `src/ingestion_service/csv_ingestor.py` implementuje kroki zgodne z kontraktem `POST /ingestion/v1/jobs`. Funkcja `run` zwraca `IngestionResult` zawierający schemat kolumn (DCAT-AP), ścieżkę podglądu i listę `VisualizationHint`. Plik wejściowy odkładany jest do katalogu `build/landing` wraz z sygnaturą czasową.
- *Instrukcja dla laika*: "Wskaż plik CSV oraz profil konfiguracji. System sam sprawdzi poprawność danych, zapisze kopię zapasową i pokaże podgląd z propozycją wykresu."
- *Przykład użycia*:
  ```bash
  ODP_PROFILE=dev   ODP_CSV_SOURCE=tests/fixtures/sample_population.csv   ODP_DATASET_ID=population   python -m ingestion_service
  ```
- *Efekt dla użytkownika końcowego*: Administrator w Studio Danych otrzymuje raport z liczbą wierszy, opisem kolumn i sugestiami wizualizacji, co pozwala szybko przejść do publikacji danych.

### 3. Integracja z konfiguracją i kontraktami
- *Opis techniczny*: `ConfigServiceClient` (`src/ingestion_service/config_client.py`) pobiera profile z `CONFIG_SERVICE_URL` lub katalogu GitOps. Zwracane dane transformowane są przez `profile_from_dict`, dzięki czemu pipeline przestrzega limitów rozmiaru, dozwolonych separatorów oraz lokalizacji storage.
- *Instrukcja dla laika*: "System najpierw sprawdza, jakie ustawienia ustalili administratorzy (np. gdzie zapisywać pliki). Jeśli nie ma połączenia z serwerem, korzysta z kopii zapisanej na dysku."
- *Przykład*: skopiowanie profilu `dev.json` do repozytorium GitOps pozwala wykonać import w trybie offline.
- *Efekt*: zapewnia zgodność z politykami bezpieczeństwa i audytu opisanymi w etapach 2–3A.

### 4. Testy i zgodność
- Testy jednostkowe (`tests/test_csv_ingestor.py`) pokrywają generowanie schematu, zapis podglądu oraz działanie w trybie GitOps.
- Pliki konfiguracyjne (`config/profiles/dev.json`) są zgodne z opisanym katalogiem zmiennych środowiskowych i mogą być rozszerzane w repozytorium GitOps.
- Wdrożony kod respektuje standardy dane.gov.pl (DCAT-AP), API BDL (obsługa polskich formatów CSV) oraz wytyczne UE (audyt, przechowywanie metadanych).

### 5. Kryteria akceptacyjne etapu 4
- Dostępna implementacja `CSVIngestor` przechodzi testy jednostkowe i dostarcza strukturę `IngestionResult` zgodną z kontraktami etapu 3A.
- Import CSV wykorzystuje profile konfiguracyjne z `config-service`/GitOps, w tym limity rozmiaru i listę dozwolonych separatorów.
- Generowany jest podgląd JSON i kopia pliku w strefie landing, co umożliwia audyt oraz dalsze przetwarzanie w `etl-service`.
- W przypadku braku możliwej wizualizacji użytkownik otrzymuje komunikat **"BRAK MOŻLIWEJ WIZUALIZACJI"** z zachowaniem zgodności z wymaganiami panelu.


## Etap 7 – Obsługa źródeł URL i plików zdalnych
Etap 7 wprowadza warstwę synchronizacji zdalnych zasobów (HTTP/HTTPS) oraz harmonogram odświeżania danych. Moduł `RemoteSyncManager` korzysta z polityki `remote_policy` w profilu konfiguracji, pobiera pliki do cache, deleguje ich import do istniejących silników CSV/XLSX/JSON i zapisuje stan synchronizacji w repozytorium GitOps.

### 1. Zakres funkcjonalny
- Harmonogram synchronizacji definiowany w formacie ISO 8601 (np. `PT6H`, `P1DT2H`).
- Obsługa formatów CSV, XLSX i JSON pobieranych z adresów HTTP/HTTPS zgodnych z polityką bezpieczeństwa (`allowed_schemes`, `allowed_content_types`).
- Cache plików w katalogu `build/cache` (lub wskazanym w `remote_policy`) z kopią źródłową i sumą kontrolną SHA-256.
- Rejestr stanu (`build/state`) przechowujący informacje o ostatnim uruchomieniu, kolejnej dacie synchronizacji, etagach oraz statusach wykonania.
- Integracja z modułami `CSVIngestor`, `XLSXIngestor`, `JSONIngestor` – wynik synchronizacji to standardowy `IngestionResult`, wykorzystywany przez Studio Danych i kolejne etapy ETL.

### 2. Proces techniczny
1. Administrator definiuje `RemoteSourceConfig` (URI, format, zbiór danych, profil, częstotliwość) poprzez Studio Danych lub repozytorium GitOps.
2. `RemoteSyncManager` sprawdza harmonogram (funkcja `parse_duration`) i decyduje, czy uruchomić synchronizację; można wymusić wykonanie (`force=True`).
3. Moduł pobiera plik z zastosowaniem nagłówków bezpieczeństwa, waliduje rozmiar (`max_file_size_mb`) oraz typ zawartości. W razie błędu stosuje politykę retry (`retry_attempts`, `retry_backoff_seconds`).
4. Pobrany plik trafia do cache wraz z sumą SHA-256, po czym odpowiedni importer (CSV/XLSX/JSON) generuje `IngestionResult` i zapisuje podglądy/landing tak jak w wcześniejszych etapach.
5. Stan synchronizacji aktualizowany jest w katalogu `state_registry` – plik JSON zawiera informacje o `last_run`, `next_run`, `checksum`, `etag` i statusie.

### 3. Integracja z konfiguracją i kontraktami
- Nowa sekcja `remote_policy` w profilu (`config/profiles/dev.json`) definiuje dopuszczalne schematy, typy zawartości, katalog cache/state, domyślny harmonogram (`PT24H`) oraz parametry retry.
- `RemoteSourceConfig` korzysta z `DatasetReference`, dzięki czemu każdy plik zdalny trafia do właściwego zbioru w metadanych DCAT-AP.
- Wyniki synchronizacji są zgodne z istniejącymi kontraktami `ingestion-service` – nie wprowadzają zmian w API, a jedynie automatyzują tworzenie zadań importu.
- Rejestr stanu (JSON) może być monitorowany przez pipeline GitOps lub Studio Danych, co wspiera audyt zgodny z wymaganiami dane.gov.pl, API BDL i RODO.

### 4. Kryteria akceptacyjne
- `RemoteSyncManager` pobiera dane z dozwolonych adresów, respektując limity rozmiaru i typów zawartości oraz zapisuje pliki w cache z sumą kontrolną SHA-256.
- Stan synchronizacji zapisywany jest w katalogu `state_registry`, zawierając informacje o ostatnim i następnym uruchomieniu, a kolejne wywołanie przed terminem powoduje status `skipped`.
- W razie powodzenia rezultat importu (`IngestionResult`) zachowuje wszystkie informacje wymagane przez Studio Danych (kolumny, podgląd, sugestie wizualizacji lub komunikat **"BRAK MOŻLIWEJ WIZUALIZACJI"**).
- Testy jednostkowe (`tests/test_remote_sync.py`) uruchamiają lokalny serwer HTTP, weryfikują pobieranie CSV, zapis stanu oraz działanie harmonogramu.

### Instrukcje dla laika
1. **Co zostało dodane?** Wystarczy wskazać adres w internecie i częstotliwość – system sam pobierze plik (CSV, Excel, JSON), zapisze kopię bezpieczeństwa i uruchomi import tak jak w poprzednich etapach.
2. **Jak używać?** W Studio Danych utwórz źródło zdalne: wpisz URL, wybierz profil, ustaw np. "co 6 godzin" i zatwierdź. Harmonogram zadba o kolejne aktualizacje.
3. **Przykład:** Dodaj `https://example.gov/population.csv` z częstotliwością `PT6H`. Po pierwszym pobraniu w panelu zobaczysz raport i informację, kiedy nastąpi kolejna synchronizacja.
4. **Korzyść:** Dane z portali państwowych lub repozytoriów tematycznych będą aktualizowane automatycznie bez ręcznego pobierania plików, przy zachowaniu audytu i bezpieczeństwa wymaganych przez dane.gov.pl oraz API BDL.

## Etap 8 – Integracja bazodanowa
Etap 8 rozbudowuje `ingestion-service` o obsługę relacyjnych baz danych (PostgreSQL, MySQL, MS SQL oraz środowiska testowe SQLite) przy użyciu SQLAlchemy. Nowy moduł `DatabaseIngestor` wykorzystuje konfigurację `database_policy` i katalog połączeń `database_connections` w profilach `config-service`, dzięki czemu integracja z bazami spełnia wymagania bezpieczeństwa oraz audytu danych.gov.pl, API BDL i standardów UE.

### 1. Zakres funkcjonalny
- Obsługa połączeń opisanych w profilu (`config/profiles/dev.json`) wraz z parametrami TLS, poolingiem i opisem w Studio Danych.
- Możliwość pobrania danych na dwa sposoby: wskazanie tabeli (z opcjonalnymi kolumnami/filtrami) lub wykonanie niestandardowego zapytania SQL.
- Automatyczne ograniczanie liczby wierszy zgodnie z `database_policy.max_rows` oraz generowanie `IngestionResult` z opisem kolumn i podpowiedzią wizualizacji.
- Zapis ekstraktu CSV w katalogu landing oraz podglądu JSON (20 wierszy) w katalogu preview – kompatybilne z wymaganiami audytu i panelu Studio Danych.
- Sugestie wizualizacji i komunikat **"BRAK MOŻLIWEJ WIZUALIZACJI"** w scenariuszach bez możliwego wykresu, spójne z wcześniejszymi etapami.

### 2. Proces techniczny
1. Administrator definiuje połączenie w `database_connections` (np. `demo_postgres`) oraz politykę limitów (`database_policy`).
2. Zadanie `POST /ingestion/v1/jobs` dla źródła `database` przekazuje `DatabaseIngestionRequest` (połączenie, tabela/zapytanie, limity, opcje).
3. `DatabaseIngestor` buduje silnik SQLAlchemy, wykonuje zapytanie (z `fetchmany` w trybie custom query) i ogranicza wynik do wartości `default_limit`/`max_rows`.
4. Moduł opisuje kolumny na podstawie pobranych danych (`infer_column_type`), generuje podgląd JSON i zapisuje ekstrakt CSV w katalogu landing.
5. Wynik (`IngestionResult`) trafia do kolejki `ingestion.job.completed`, skąd może zostać odebrany przez `etl-service`, Studio Danych i mostek WordPress.

### 3. Konfiguracja i zgodność
- Sekcja `database.policy` w profilu definiuje dozwolone drivery (`postgresql`, `mysql`, `mssql`, `sqlite`), limity rekordów i katalog cache metadanych (`build/db-metadata`).
- Połączenia (`database.connections`) zawierają adresy SQLAlchemy, opisy, domyślne schematy oraz opcje (np. `sslmode`, `pool_pre_ping`), co umożliwia bezpieczne zarządzanie tajemnicami przez `config-service` i GitOps.
- Moduł wykorzystuje istniejące kontrakty `IngestionResult`, dzięki czemu integracja bazodanowa nie wymaga zmian po stronie API klientów.
- Wykorzystanie SQLAlchemy gwarantuje zgodność z wytycznymi bezpieczeństwa (połączenia TLS, kontrola limitów) oraz standardami DCAT-AP przez automatyczne opisy kolumn.

### 4. Kryteria akceptacyjne
- `DatabaseIngestor` łączy się z bazą określoną w profilu i generuje poprawny `IngestionResult` wraz z podglądem oraz kopią landing.
- Limity rekordów wynikają z `database_policy`; w przypadku przekroczenia import kończy się na `max_rows`, chroniąc bazę przed przeciążeniem.
- Wynik importu zawiera opis kolumn, sugestie wizualizacji (lub komunikat **"BRAK MOŻLIWEJ WIZUALIZACJI"**) oraz informacje o połączeniu użyte do audytu.
- Testy jednostkowe (`tests/test_database_ingestor.py`) potwierdzają działanie na bazie SQLite: import tabeli oraz wykonanie zapytania z limitem `fetchmany`.

### Instrukcje dla laika
1. **Co zostało dodane?** Możesz teraz pobierać dane bezpośrednio z baz (PostgreSQL, MySQL, MS SQL). Wystarczy wskazać przygotowane połączenie i tabelę lub wkleić własne zapytanie.
2. **Jak używać?** W Studio Danych wybierz zakładkę „Baza danych”, wskaż połączenie (np. `demo_postgres`), tabelę lub zapytanie oraz limit rekordów. System pobierze dane i przygotuje raport.
3. **Przykład:** Wybierz `demo_postgres`, tabelę `public.population`, limit 1000. Po kilku sekundach zobaczysz raport z opisem kolumn i propozycją wykresu liniowego.
4. **Korzyść:** Integrujesz hurtownie danych lub systemy transakcyjne bez ręcznej eksportu CSV. Dane pozostają w zgodzie z polityką bezpieczeństwa i audytu wymaganiami dane.gov.pl i API BDL.

## Etap 9 – Silnik transformacji danych
Etap 9 dostarcza moduł `TransformationPipeline`, który realizuje część „T” w architekturze ETL – automatyczne czyszczenie, filtrowanie, wzbogacanie oraz agregację danych zgodnie z wymaganiami dane.gov.pl, API BDL i DCAT-AP. Pipeline współpracuje z rezultatami ingestu (CSV/XLSX/JSON/API/DB), a konfiguracja pochodzi z profili `config-service` (`transformation.policy`, `transformation.steps`).

### 1. Zakres i cele
- Przygotowanie spójnego pipeline'u transformacji, który po imporcie danych automatycznie normalizuje nagłówki, filtruje rekordy, oblicza kolumny pochodne i agreguje wyniki.
- Zapewnienie, że wynik transformacji generuje metadane kolumn zgodne z DCAT-AP oraz sugestie wizualizacji dla `visualization-service`.
- Automatyczne zapisywanie podglądu (`*-transformed.json`) w katalogu `preview`, aby Studio Danych i WordPress mogły natychmiast wyświetlić wynik.
- Utrzymanie dziennika kroków (`TransformationStepStatus`) dla audytu – informacje o powodzeniu, pominięciu lub błędzie każdego kroku.

### 2. Operacje pipeline'u
- **`normalize_headers`** – zamienia nagłówki na format slug (małe litery, podkreślenia) zgodny z DCAT-AP.
- **`rename_columns`** – umożliwia mapowanie kolumn (np. `rok` → `year`, `populacja` → `population`).
- **`filter_rows`** – stosuje zestaw warunków (`==`, `>=`, `contains`, `not_in`) do odfiltrowania rekordów (np. lata ≥ 2021).
- **`derive_column`** – oblicza kolumny pochodne na podstawie bezpiecznych wyrażeń (obsługiwane funkcje: `abs`, `round`, `int`, `float`, `len`, `min`, `max`).
- **`aggregate`** – grupuje dane i liczy metryki (`sum`, `avg`, `min`, `max`, `count`) z kontrolą precyzji (`rounding_precision`).

### 3. Integracja z profilami konfiguracji
- `config/profiles/dev.json` zawiera sekcję `transformation` z polityką (`enabled`, `max_rows`, `allowed_operations`) i sekwencją kroków – pipeline może być modyfikowany przez Studio Danych lub GitOps.
- Funkcja `settings_from_profile(profile)` przekształca `ConfigProfile` w `TransformationSettings`, dzięki czemu pipeline działa identycznie w CLI, testach i środowisku produkcyjnym.
- Transformacje są ograniczone do zdefiniowanych w polityce operacji – niedozwolony krok zostanie oznaczony jako `skipped`, co zabezpiecza proces przed nieautoryzowanymi zmianami.

### 4. Wizualizacje i raportowanie
- Po transformacji generowane są nowe metadane kolumn (`ColumnSchema`) oraz sugestie wizualizacji (`VisualizationHint`) – logika heurystyk dopasowuje wykres liniowy (gdy obecne są daty i wartości) lub słupkowy (gdy brak wymiaru czasu).
- W przypadku braku odpowiednich kolumn pipeline zwraca komunikat **"BRAK MOŻLIWEJ WIZUALIZACJI"**, co prowadzi użytkownika do ponownego przygotowania danych.
- Raport `TransformationReport` przechowuje liczbę wierszy wejściowych i wyjściowych, ścieżkę podglądu, listę kroków oraz komunikaty – dane te mogą być publikowane w WordPressie lub wykorzystane przez `visualization-service`.

### 5. Kryteria akceptacyjne etapu 9
- Zaimplementowano moduł `TransformationPipeline` oraz helper `settings_from_profile` w `src/ingestion_service/transformation.py`.
- Konfiguracja `transformation` została dodana do profilu `dev` i jest parsowana przez `ConfigProfile`.
- Raport transformacji generuje metadane kolumn, podgląd JSON i sugestie wizualizacji zgodnie z wymaganiami.
- Dodano testy jednostkowe (`tests/test_transformation_pipeline.py`) weryfikujące działanie kroków i zapis podglądu.

### Instrukcje dla laika
1. **Co zostało dodane?** Po imporcie dane automatycznie się oczyszczają, kolumny mają czytelne nazwy, a system proponuje gotowe sumy i miary.
2. **Jak używać?** W Studio Danych wybierz profil z włączoną transformacją (`dev`) lub dodaj własne kroki w `transformation.steps`. Pipeline uruchomi się automatycznie po każdym imporcie.
3. **Przykład:** Wgraj arkusz populacji, pipeline zachowa tylko lata ≥ 2021, przeliczy populację w tysiącach i zsumuje wartości według województw.
4. **Korzyść:** Oszczędzasz czas na ręcznym czyszczeniu danych – raport jest od razu gotowy do publikacji i wizualizacji na portalu WordPress.

## Etap 10 – Warstwa metadanych
Etap 10 uruchamia kompletny `metadata-service`, który odpowiada za katalogowanie zbiorów danych zgodnie z DCAT-AP oraz integrację z WordPressem i API publikacyjnym. Rejestr metadanych powstaje na podstawie raportów transformacji (Etap 9), jest przechowywany w repozytorium GitOps i automatycznie eksportowany do formatów JSON-LD oraz JSON:API.

### 1. Zakres i cele
- Zbudowanie rejestru zbiorów danych (`MetadataRegistry`) przechowującego rekordy DCAT-AP z polami: tytuł, opis, licencja, częstotliwość aktualizacji, kontakt, słowa kluczowe oraz struktura pól (`FieldSchema`).
- Zapewnienie automatycznej aktualizacji metadanych po każdej transformacji danych – pipeline przekazuje raport do `metadata-service`, który tworzy/aktualizuje rekord i eksportuje pliki katalogu.
- Integracja z mostkiem WordPress: synchronizacja wpisów `open_data_dataset` uzupełniana jest o licencję, tematy i słowa kluczowe zapisane w rejestrze.

### 2. Model danych i eksporty
- Rejestr przechowuje dane w katalogu `metadata_storage.registry` (domyślnie `build/metadata/registry`) jako pliki JSON zgodne z DCAT-AP.
- Dla każdej aktualizacji generowany jest JSON-LD (`metadata_storage.exports`) zawierający kontekst `https://www.w3.org/ns/dcat.jsonld`, dzięki czemu katalog można bezpośrednio opublikować w portalu dane.gov.pl.
- Dostępny jest również format JSON:API wykorzystywany przez `admin-gateway` oraz mostek WordPress do pobierania metadanych i renderowania katalogu w CMS.

### 3. Integracja z pipeline ETL i WordPressem
- `TransformationPipeline.run(..., metadata_registry=...)` umożliwia przekazanie rejestru metadanych – po zakończeniu transformacji rekord jest automatycznie aktualizowany i oznaczany timestampami audytu.
- Wtyczka WordPress (`wordpress/open-data-plugin`) podczas synchronizacji datasetów zapisuje dodatkowe pola meta: licencję (`odp_license`), słowa kluczowe (`odp_keywords`), częstotliwość aktualizacji (`odp_accrual`) oraz odnośnik do pliku JSON-LD. Dzięki temu WordPress staje się głównym systemem publikacji katalogu.
- Profil konfiguracji (`config/profiles/dev.json`) otrzymał sekcję `metadata` z polityką licencji, kontaktu i taksonomią słów kluczowych – Studio Danych może je edytować poprzez `config-service`.

### 4. Interfejsy API i narzędzia administracyjne
- `metadata-service` udostępnia funkcje `MetadataRegistry.upsert`, `MetadataRegistry.list_records` oraz `MetadataRegistry.to_jsonapi`, które będą mapowane na endpointy REST/GraphQL w kolejnych etapach.
- Z poziomu CLI można użyć helpera `registry_from_profile(profile)` i zarejestrować zestaw metadanych na podstawie raportu transformacji.
- Eksporty JSON-LD są podpisywane timestampem oraz identyfikatorem profilu, co ułatwia publikację wersjonowanych katalogów w repozytorium GitOps.

### 5. Kryteria akceptacyjne etapu 10
- Powstał moduł `metadata_service` z modelami `DatasetRecord`, `DistributionRecord`, `FieldSchema`, `ContactPoint` oraz rejestrem `MetadataRegistry` zapisującym katalog DCAT-AP.
- Profil `dev` zawiera konfigurację `metadata.storage` i `metadata.policy`; `ConfigProfile` potrafi ją odczytać i udostępnić modułom ingestu.
- Pipeline transformacji integruje się z rejestrem metadanych – raporty mogą być automatycznie publikowane w katalogu.
- Wtyczka WordPress aktualizuje meta pola wpisów na podstawie danych zwróconych przez API, zapewniając spójny opis licencji i słów kluczowych.
- Dodano testy jednostkowe `tests/test_metadata_registry.py` weryfikujące rejestrację, eksport JSON-LD oraz serializację JSON:API.

### Instrukcje dla laika
1. **Co zostało dodane?** Po przetworzeniu danych system automatycznie dopisuje kompletny opis zbioru (tytuł, opis, licencja, słowa kluczowe) i zapisuje go w katalogu kompatybilnym z dane.gov.pl.
2. **Jak używać?** Uruchom import + transformację jak dotychczas – rejestr metadanych aktualizuje się sam. W WordPressie zobaczysz licencję i słowa kluczowe przy każdym wpisie katalogu.
3. **Przykład:** Po imporcie populacji pipeline zapisuje metadane z licencją CC BY 4.0 i słowami kluczowymi „demografia”, „populacja”. WordPress pokaże je na stronie zbioru i udostępni link do pliku JSON-LD.
4. **Korzyść:** Nie musisz ręcznie przepisywać opisów do portalu – katalog DCAT-AP i WordPress są aktualizowane automatycznie, co gwarantuje zgodność z wymaganiami UE i API BDL.

## Etap 11 – System uprawnień i audytu
Etap 11 wdraża moduł `auth-service`, który realizuje polityki RBAC/ABAC oraz audyt działań użytkowników zgodnie z wymaganiami dane.gov.pl, API BDL i RODO. Konfiguracja ról trafia do profilu (`config/profiles/dev.json`), a decyzje zapisywane są w dzienniku audytowym gotowym do publikacji w GitOps.

### 1. Zakres i cele
- Udostępnienie katalogu ról (`data_viewer`, `data_admin`, `security_auditor`) z dziedziczeniem i regułami ABAC (klauzule danych, środowisko) zgodnymi z planem rozwoju.
- Zapewnienie centralnego audytu (`AuditTrail`) z retencją i możliwością eksportu do pliku JSON (lokalizacja `build/audit/audit-log.json`).
- Integracja z profilami `config-service`, aby Studio Danych mogło konfigurować role i polityki bez zmian w kodzie.

### 2. Model RBAC/ABAC
- Moduł `auth_service.rbac` definiuje `Permission`, `Role` i `AttributeRule`, co pozwala odwzorować wymagania DCAT-AP (np. publikacja datasetu tylko z klasyfikacją „public”).
- Konfiguracja roli w profilu zawiera listę uprawnień (`datasets.view`, `datasets.publish`, `metadata.manage`) oraz reguły ABAC sprawdzające atrybuty danych i kontekst środowiskowy.
- `AuthorizationService` agreguje role dziedziczone i dba o to, by decyzje były spójne w całym ekosystemie (Studio Danych, API, WordPress).

### 3. Audyt i integracja operacyjna
- `AuditTrail` gromadzi wszystkie operacje (`auth.role.assign`, `auth.decision.allow/deny`) i przechowuje je zgodnie z polityką retencji. W razie potrzeby zapisuje log do pliku JSON wykorzystywanego w raportach compliance.
- Każda decyzja autoryzacyjna zawiera `AccessDecision` z informacją o roli i powodzie akceptacji/odmowy, co ułatwia wyświetlanie komunikatów w panelu.
- Sekcja `auth` w profilu umożliwia zdefiniowanie domyślnych ról użytkowników (np. `data_viewer`) oraz ustawienie powiadomień o odmowie.

### 4. Integracja z WordPress i Studio Danych
- Mostek WordPress wykorzystuje decyzje `AuthorizationService` przy synchronizacji katalogu – publikacja zbioru z WordPress wymaga roli `data_admin` i spełnienia reguły ABAC.
- Panel Studio Danych może tworzyć kreatory ról, bazując na `AuthPolicy`, a wpisy audytowe są dostępne do przeglądu i eksportu.
- Gotowa wtyczka WordPress nadal znajduje się w katalogu `wordpress/open-data-plugin` – po sklonowaniu repozytorium skopiuj ją do `wp-content/plugins/`, aby korzystać z nowych zabezpieczeń.

### 5. Kryteria akceptacyjne etapu 11
- Powstał moduł `auth_service` z klasami `AuthorizationService`, `AuditTrail`, `Permission`, `Role`, `AttributeRule` oraz testami jednostkowymi `tests/test_auth_service.py`.
- Profil `dev` został rozszerzony o sekcję `auth` (role, reguły ABAC, politykę audytu), a `ConfigProfile` potrafi ją odczytać.
- Każda decyzja autoryzacji zapisuje się w audycie i zawiera szczegółowy kontekst (rola, atrybuty, środowisko).
- Dodano instrukcje dla administratorów WordPress/Studio Danych dotyczące korzystania z ról i audytu.

### Instrukcje dla laika
1. **Co zostało dodane?** System pilnuje, kto może publikować, edytować lub tylko oglądać dane – a wszystkie akcje zapisuje w dzienniku.
2. **Jak używać?** W Studio Danych wybierz rolę dla użytkownika (np. `data_admin`). Wszystkie decyzje znajdziesz w dzienniku audytu (`build/audit/audit-log.json`).
3. **Przykład:** Nadaj roli administratora użytkownikowi „alice” – może publikować dataset tylko wtedy, gdy oznaczysz go jako „public” i środowisko to „prod”. Próba publikacji danych „restricted” zostanie odrzucona i pojawi się wpis audytowy.
4. **Korzyść:** Masz pełną kontrolę nad dostępem i raporty audytu gotowe na kontrolę bezpieczeństwa, a WordPress wykorzystuje te same zasady publikacji.

### Repozytorium instalacyjne GitHub
- Repozytorium instalacyjne (Blueprint + wtyczka WordPress) udostępniamy jako pakiet GitHub. Aby pobrać aktualną wersję:
  ```bash
  git clone https://github.com/opendata-pl/open-data-plugin-blueprint.git
  cd open-data-plugin-blueprint
  ```
- W katalogu `wordpress/open-data-plugin` znajduje się gotowy plugin – skopiuj go do `wp-content/plugins/` i aktywuj w panelu.
- Aktualizacje możesz pobierać poleceniem `git pull`. Dzięki GitOps zachowasz historię zmian konfiguracji (`config/profiles`) i metadanych.

## Etap 12 – Panel administratora i integrator WordPress

Etap 12 rozszerza ekosystem o moduł `admin_gateway`, który dostarcza panel Studio Danych do zarządzania konfiguracją globalną, rolami oraz integracjami WordPress. Moduł wykorzystuje ustawienia zapisane w profilu (`config/profiles/dev.json` → sekcja `admin`) i współpracuje z `AuthorizationService`, aby każda operacja była audytowalna. Administrator może filtrować menu według ról, rejestrować instancje WordPress i generować paczki instalacyjne ZIP zgodne ze standardami dane.gov.pl i API BDL.

### 1. Zakres i cele
- Udostępnienie centralnego panelu Studio Danych z konfiguracją profili, brandingiem i listą modułów włączanych/wyłączanych.
- Automatyzacja integracji WordPress: rejestracja instancji, definicja interwału synchronizacji, generator paczek ZIP.
- Zapewnienie zgodności z systemem uprawnień (etap 11) poprzez filtrację menu i autoryzację operacji (`studio.settings.update`, `wordpress.installers.generate`).

### 2. Komponenty techniczne
- `src/admin_gateway/service.py` – `AdminGatewayService` zarządzający ustawieniami, menu i integracją WordPress.
- `src/admin_gateway/models.py` – modele `StudioSettings`, `MenuItem`, `WordPressSettings`, `InstallationPackage` wykorzystywane przez panel i testy.
- `config/profiles/dev.json` – sekcja `admin` z brandingiem, flagami modułów, strukturą menu oraz konfiguracją instalatora ZIP.
- Sekcja `auth` w profilu rozszerzona o rolę `studio_admin`, która zapewnia dostęp do ustawień panelu niezależnie od reguł ABAC datasetów.
- `tests/test_admin_gateway.py` – scenariusze sprawdzające filtrację menu, wymagane uprawnienia oraz generowanie paczki ZIP.

### 3. Zarządzanie konfiguracją i integracjami
- `AdminGatewayService` pobiera ustawienia z `ConfigProfile.admin_settings`, waliduje dostęp i aktualizuje branding czy profil domyślny (metody `update_branding`, `set_default_profile`).
- Integracja WordPress wykorzystuje metody `register_wordpress_site` oraz `generate_wordpress_installer`; paczka ZIP jest tworzona na podstawie katalogu `wordpress/open-data-plugin` i zapisywana w `build/installers`.
- Menu Studio Danych jest filtrowane przez `get_menu_for_user`, dzięki czemu użytkownik widzi tylko sekcje zgodne z uprawnieniami.

### 4. Kryteria akceptacyjne etapu 12
- Profil `dev` posiada sekcję `admin` z kompletem informacji o module Studio Danych (branding, menu, integracja WordPress).
- `AdminGatewayService` umożliwia aktualizację ustawień wyłącznie użytkownikom posiadającym odpowiednie uprawnienia – scenariusze potwierdzają to w testach jednostkowych.
- Generator paczek ZIP tworzy archiwum zawierające pełną wtyczkę WordPress (plik `open-data-plugin.php`) gotową do instalacji.
- Testy `tests/test_admin_gateway.py` oraz `pytest` przechodzą pomyślnie, co potwierdza stabilność modułu.

### Instrukcje dla laika
1. **Co zostało dodane?** W Studio Danych pojawił się pełny panel konfiguracyjny: ustawisz logo, e-mail wsparcia, wybierzesz profil i dodasz strony WordPress, a rola `studio_admin` zarządza uprawnieniami panelu niezależnie od polityk publikacji danych.
2. **Jak używać?** Zaloguj się jako administrator z rolami `data_admin` (operacje na danych) i `studio_admin` (konfiguracja panelu), przejdź do zakładki „Studio Danych” → „Ustawienia globalne”, zaktualizuj branding i naciśnij „Generuj instalator WordPress”, aby pobrać aktualną paczkę ZIP.
3. **Przykład:** Po dodaniu strony `https://wp.example.gov` panel zapisze ją na liście integracji i zaproponuje synchronizację co 12 godzin. Kliknięcie „Pobierz instalator” wygeneruje plik `build/installers/open-data-plugin.zip` gotowy do zainstalowania w WordPressie.
4. **Korzyść:** Administrator zarządza całym środowiskiem (API, WordPress, moduły) w jednym miejscu, bez ręcznego pakowania plików czy edycji konfiguracji na serwerze, a jednocześnie zachowuje pełną zgodność z politykami dane.gov.pl i API BDL.


## Etap 13 – Moduł wizualizacji podstawowych
Etap 13 wprowadza usługę `visualization-service`, która korzysta z podglądów danych (po imporcie lub transformacji) i generuje
wykresy w formatach PNG/JPG/PDF zgodnych z wymaganiami dane.gov.pl oraz API BDL. Moduł udostępnia API do integracji ze Studio
Danych, mostkiem WordPress i automatyzacją raportów.

### 1. Zakres i cele
- Automatyczne przekształcanie podglądów danych (`preview`) w wizualizacje liniowe, słupkowe i obszarowe z zachowaniem palety
  kolorów zgodnej z wytycznymi GOV.
- Eksport do formatów graficznych (PNG/JPG) i dokumentu PDF z jednej komendy lub akcji w panelu Studio Danych.
- Obsługa komunikatu **"BRAK MOŻLIWEJ WIZUALIZACJI"** w przypadku braku danych liczbowych lub niekompletnych serii.
- Integracja z konfiguracją profilu (`visualization` w `config/profiles/dev.json`) – katalog wyjściowy, formaty domyślne, DPI i
  prefiks tytułu.

### 2. Komponenty techniczne
- `src/visualization_service/service.py` – `VisualizationService` korzystający z Matplotlib do renderowania wykresów, zapisujący
  pliki i zwracający obiekt `VisualizationProduct`.
- `src/visualization_service/models.py` – modele `VisualizationRequest` i `VisualizationProduct` wykorzystywane w kontraktach i
  testach.
- `config/profiles/dev.json` – sekcja `visualization` definiująca katalog `build/visualizations`, domyślne formaty, figurę i paletę
  barw.
- `tests/test_visualization_service.py` – scenariusze potwierdzające tworzenie plików PNG/PDF oraz obsługę braku danych liczbowych.

### 3. Proces generowania wykresów
1. Pipeline transformacji zapisuje podgląd danych (`*-transformed.json`).
2. Studio Danych lub WordPress tworzy `VisualizationRequest` z nazwą datasetu, kolumną osi X i listą kolumn osi Y.
3. `VisualizationService` wczytuje podgląd, filtruje serie liczbowe, rysuje wykres (line/bar/area) i zapisuje go w katalogu
   `build/visualizations` zgodnie z profilami.
4. Moduł zwraca listę wygenerowanych plików i – jeśli to konieczne – komunikat o braku możliwości wizualizacji.

### 4. Kryteria akceptacyjne
- Profil konfiguracyjny zawiera sekcję `visualization` z katalogiem wyjściowym, formatami oraz kolorystyką.
- `VisualizationService` generuje co najmniej pliki PNG i PDF dla danych liczbowych i zwraca komunikat w przypadku braku
  odpowiednich serii.
- Testy jednostkowe `tests/test_visualization_service.py` oraz pełny pakiet `pytest` przechodzą pomyślnie.
- Wyniki wizualizacji są wykorzystywane w Studio Danych i mogą być publikowane w WordPressie wraz z metadanymi DCAT-AP.

### Instrukcje dla laika
1. **Co zostało dodane?** Możesz wskazać dataset, kolumny i rodzaj wykresu – system wygeneruje gotowy obraz oraz PDF.
2. **Jak używać?** W Studio Danych wybierz opcję „Utwórz wizualizację”, podaj kolumnę czasu (oś X) i kolumny liczbowe (oś Y).
   Po zatwierdzeniu w katalogu `build/visualizations` pojawią się pliki PNG i PDF.
3. **Przykład:** Dla datasetu populacji ustaw `year` jako oś X, `population` jako oś Y i typ `line` – otrzymasz pliki
   `dataset-line-*.png` oraz `dataset-line-*.pdf` gotowe do publikacji.
4. **Korzyść:** Raporty i strony WordPress otrzymują aktualne wykresy bez ręcznego rysowania – zgodne z kolorystyką GOV i
   wymaganiami API BDL.


## Etap 14 – Zaawansowane wizualizacje i dashboardy
Etap 14 rozszerza moduł `visualization-service` o mapy choropletyczne, heatmapy, wykresy kombinowane oraz panele KPI z raportami JSON. Dodano także tryb zastępczy – w środowiskach bez biblioteki Matplotlib generowane są pliki graficzne (placeholdery) i raporty, co zapewnia ciągłość publikacji danych zgodnie z wymaganiami dane.gov.pl i API BDL.

### 1. Zakres i cele
- Obsługa zaawansowanych typów wizualizacji (`heatmap`, `choropleth`, `combo`, `kpi_dashboard`) z wykorzystaniem konfiguracji profilu (`visualization.advanced`).
- Automatyczne tworzenie raportu JSON (`*-summary.json`) zawierającego metadane wykresu, listę serii, zastosowane metryki KPI oraz informację o trybie zastępczym.
- Zapewnienie fallbacku w środowisku offline – generowane są pliki PNG/JPG/PDF z placeholderami oraz pełny raport JSON, dzięki czemu Studio Danych i WordPress zachowują spójny przepływ publikacji.

### 2. Komponenty techniczne
- `src/visualization_service/service.py` – rozbudowany `VisualizationService` z rendererami heatmap, choropleth, combo, panelu KPI oraz generatorem plików zastępczych i raportów JSON.
- `src/visualization_service/models.py` – rozszerzone modele `VisualizationRequest` (pole `options`) i `VisualizationProduct` (`summary_path`).
- `src/ingestion_service/profile.py` – nowa klasa `VisualizationAdvancedSettings`, domyślne ustawienia i parser sekcji `visualization.advanced`.
- `config/profiles/dev.json` – zaktualizowana sekcja `visualization` z listą nowych typów wykresów, paletami heatmap/choropleth i metrykami KPI.
- `tests/test_visualization_service.py` – scenariusze obejmujące tryb zastępczy, heatmapy oraz panele KPI.

### 3. Proces generowania zaawansowanych wizualizacji
1. Pipeline transformacji przygotowuje podgląd danych (`*-transformed.json`).
2. Studio Danych lub WordPress wysyła `VisualizationRequest` z typem wykresu (`heatmap`, `choropleth`, `combo` lub `kpi_dashboard`) oraz dodatkowymi opcjami (np. `region_field`).
3. `VisualizationService` oblicza serie danych i – jeśli dostępny – wykorzystuje Matplotlib do wygenerowania wykresów; w trybie fallback tworzy pliki zastępcze oraz raport JSON.
4. Moduł zapisuje pliki w `build/visualizations` oraz generuje raport `*-summary.json`, który zawiera metadane, wykorzystane metryki i status renderera.

### 4. Kryteria akceptacyjne
- Profil konfiguracyjny zawiera sekcję `visualization.advanced` z ustawieniami map, palet i metryk KPI.
- `VisualizationService` tworzy pliki graficzne (lub placeholdery) oraz raport JSON dla każdego rodzaju wizualizacji.
- Testy `tests/test_visualization_service.py` potwierdzają generowanie plików w trybie podstawowym i zastępczym, w tym poprawność metryk KPI.
- Studio Danych i wtyczka WordPress mogą publikować mapy, heatmapy i dashboardy korzystając z tych samych kontraktów API.

### Instrukcje dla laika
1. **Co zostało dodane?** Możesz tworzyć mapy regionów, heatmapy oraz panele KPI – system generuje obrazki i raport JSON.
2. **Jak używać?** W Studio Danych wybierz „Zaawansowana wizualizacja”, wskaż typ (np. heatmapa), kolumny oraz – w przypadku map – pole regionu. System zapisze pliki w `build/visualizations` oraz raport `*-summary.json`.
3. **Przykład:** Dla datasetu z kolumnami `region`, `population`, `budget` wybierz wizualizację `choropleth`. Otrzymasz pliki PNG/PDF z barwioną mapą regionów (lub placeholder, jeśli Matplotlib nie jest dostępny) oraz raport JSON z wartościami.
4. **Korzyść:** Dashboardy KPI i mapy można publikować nawet w środowisku o ograniczonych zasobach – użytkownicy końcowi widzą spójne metryki i wizualizacje zgodne ze standardami państwowymi.


## Etap 15 – Generator raportów
Etap 15 dodaje usługę `report_service`, która scala wizualizacje, metadane DCAT-AP i pliki JSON-LD w raporty HTML/PDF. Moduł współpracuje z `visualization-service`, `metadata_service` oraz konfiguracją profili, zachowując zgodność z wytycznymi dane.gov.pl, API BDL i standardami UE. Zapewnia tryb offline – gdy renderowanie PDF nie jest dostępne, generuje pliki zastępcze o poprawnym nagłówku, co pozwala utrzymać ciągłość publikacji.

### 1. Zakres i cele
- Automatyczne tworzenie raportów HTML i PDF łączących wykresy, statystyki KPI oraz metadane DCAT-AP z registry `metadata_service`.
- Dołączanie eksportów JSON-LD i raportów `*-summary.json` do finalnego raportu wraz z informacją o źródłach danych i harmonogramach aktualizacji.
- Zapewnienie zgodności z profilem konfiguracji (`reports`) – katalog wyjściowy, lista formatów, szablony HTML, przypisanie odpowiedzialnych osób.
- Tryb awaryjny dla środowisk bez zewnętrznych rendererów PDF: generator tworzy plik o nagłówku `%PDF-1.4` z krótkim streszczeniem i wskazaniem do pełnej wersji HTML.

### 2. Komponenty techniczne
- `src/report_service/service.py` – `ReportService` generujący raporty na podstawie konfiguracji profilu, wizualizacji i metadanych.
- `src/report_service/models.py` – modele `ReportRequest` i `ReportProduct` opisujące wejście/wyjście generatora.
- `src/ingestion_service/profile.py` – klasy `ReportSettings` i parser sekcji `reports` z obsługą katalogów, formatów i flag zgodności.
- `config/profiles/dev.json` – sekcja `reports` z katalogiem `build/reports`, formatami (`html`, `pdf`), wskazaniem szablonu oraz preferencją dołączania JSON-LD.
- `tests/test_report_service.py` – scenariusze weryfikujące generowanie raportów HTML/PDF, wstawianie wykresów, metadanych i fallback offline.

### 3. Proces generowania raportu
1. Studio Danych zbiera `VisualizationProduct`, raport `TransformationReport` oraz rekord `DatasetMetadata`.
2. Wywołuje `ReportService.generate()` z danymi oraz listą wykresów i ścieżkami do plików JSON-LD/summary.
3. Usługa renderuje szablon HTML (z repozytorium lub wbudowany) i zapisuje raport do katalogu `build/reports`.
4. Jeżeli format PDF jest wymagany, generator tworzy minimalny dokument PDF; w razie braku zależności zewnętrznych korzysta z trybu fallback.
5. `ReportProduct` zwraca listę plików raportu, dołączonych załączników i komunikat statusu (np. o użytym trybie zastępczym).

### 4. Kryteria akceptacyjne
- Profil konfiguracyjny zawiera kompletną sekcję `reports` z katalogiem, formatami oraz ścieżką szablonu.
- `ReportService` generuje raport HTML zawierający tytuł datasetu, metadane DCAT-AP, listę wykresów i odnośniki do JSON-LD.
- Wymagane formaty (HTML/PDF) powstają nawet bez zewnętrznych bibliotek – plik PDF zawiera poprawny nagłówek `%PDF-1.4`.
- Testy jednostkowe `tests/test_report_service.py` oraz pełny pakiet `pytest` kończą się sukcesem.
- Studio Danych i mostek WordPress mogą pobierać raporty jednym kliknięciem, zachowując zgodność z DCAT-AP i API BDL.

### Instrukcje dla laika
1. **Co zostało dodane?** System tworzy kompletne raporty łączące wykresy, opis danych, licencję i kontakt – gotowe do wysyłki lub publikacji.
2. **Jak używać?** W Studio Danych przejdź do zakładki „Raporty” → „Generuj raport”, wybierz dataset oraz wizualizacje dołączane do dokumentu i zatwierdź.
3. **Przykład:** Wybierz dataset populacji, zaznacz wykres liniowy i dashboard KPI, a moduł utworzy `build/reports/population-report.html` oraz `population-report.pdf` wraz z JSON-LD.
4. **Korzyść:** Interesariusze otrzymują kompletny raport zgodny z normami państwowymi – z wykresami, licencją i kontaktem do administratora, bez ręcznego składania dokumentów.

## Etap 4 – Import CSV
Etap 4 dostarczył produkcyjny moduł importu CSV w `ingestion-service`, zgodny z profilami konfiguracji oraz kontraktami API etapu 3A. Funkcjonalność obejmuje pełny przepływ od walidacji pliku, przez opis kolumn, po generowanie podglądów i sugestii wizualizacji.

### 1. Zakres funkcjonalny
- Autodetekcja separatora, kodowania i struktury pliku przy pomocy `csv.Sniffer` z ograniczeniami narzuconymi przez profil.
- Budowa schematu kolumn zgodnie z DCAT-AP i publikacja podglądu JSON wykorzystywanego przez Studio Danych i mostek WordPress.
- Generowanie heurystycznych sugestii wizualizacji (liniowe, słupkowe) oraz komunikatu **"BRAK MOŻLIWEJ WIZUALIZACJI"** w przypadku braku dopasowania.
- Kopiowanie pliku do strefy landing w celu spełnienia wymogów audytu i odtworzenia procesów ETL.

### 2. Proces techniczny
1. Administrator uruchamia zadanie `POST /ingestion/v1/jobs` wskazując profil i plik.
2. `CSVIngestor` waliduje rozmiar, autodetekuje separator i odczytuje próbkę danych.
3. Moduł tworzy schemat kolumn (`ColumnSchema`) i zapisuje podgląd JSON w katalogu preview.
4. Wynik `IngestionResult` przekazywany jest do kolejki `ingestion.job.completed`, skąd może go odebrać `etl-service` i panel Studio Danych.

### 3. Integracja z konfiguracją i kontraktami
- Profil konfiguracyjny (`config-service`/GitOps) definiuje dopuszczalne separatory, rozmiar pliku i liczbę próbkowanych wierszy.
- Kontrakt `ingestion-service` opisuje strukturę żądania i odpowiedzi; moduł stosuje nagłówki wersjonowania i identyfikatory datasetów.
- Podgląd JSON i sugestie wizualizacji są spójne z wymaganiami API BDL oraz portalu dane.gov.pl (DCAT-AP).

### 4. Kryteria akceptacyjne
- Plik CSV o poprawnej strukturze generuje raport z liczbą wierszy, schematem kolumn i przynajmniej jedną sugestią wykresu (lub komunikatem o braku wizualizacji).
- Kopia pliku trafia do strefy landing z sygnaturą czasową, a podgląd JSON jest dostępny dla Studio Danych.
- Import działa zarówno przy pobieraniu profilu z `config-service`, jak i z repozytorium GitOps w trybie offline.

### Instrukcje dla laika
1. **Co zostało dodane?** Możesz wgrać plik CSV i natychmiast zobaczyć podgląd danych oraz propozycję wykresu.
2. **Jak używać?** W Studio Danych wybierz profil, wskaż plik CSV i zatwierdź import – raport pojawi się automatycznie.
3. **Przykład:** Wgraj plik populacja.csv; system zasugeruje wykres liniowy liczby mieszkańców w kolejnych latach.
4. **Korzyść:** Dane są gotowe do publikacji bez ręcznego przygotowywania schematów i raportów.

## Etap 5 – Import XLSX
Etap 5 rozszerza `ingestion-service` o obsługę plików XLSX z wykorzystaniem profili konfiguracji (`xlsx_policy`) i istniejących kontraktów API. Moduł zapewnia pełną autodetekcję arkuszy oraz integrację z procesami audytu i wizualizacji.

### 1. Zakres funkcjonalny
- Wybór arkusza na podstawie parametru zadania, listy preferowanych arkuszy w profilu lub pierwszego arkusza w skoroszycie.
- Odczyt nagłówków i próbkowanie danych zgodnie z konfiguracją `header_row_index` i `sample_size`.
- Budowa schematu kolumn oraz sugestii wizualizacji identycznych jak dla CSV, z zachowaniem komunikatu **"BRAK MOŻLIWEJ WIZUALIZACJI"**.
- Generowanie podglądu JSON zawierającego nazwę arkusza oraz zapis kopii pliku w strefie landing.

### 2. Proces techniczny
1. Zadanie importu (`POST /ingestion/v1/jobs`) wskazuje plik XLSX i opcjonalnie nazwę arkusza.
2. `XLSXIngestor` waliduje rozszerzenie, rozmiar i wybiera arkusz zgodnie z profilem (`xlsx_policy`).
3. Moduł odczytuje nagłówki oraz próbkę danych, tworzy schemat kolumn i podgląd JSON.
4. Wynik `IngestionResult` jest publikowany dla `etl-service`, panelu Studio Danych oraz przyszłego mostka WordPress.

### 3. Integracja z konfiguracją i kontraktami
- Nowe pola `xlsx_policy` w profilu definiują dozwolone rozszerzenia, preferowane arkusze i parametry próbkowania.
- Moduł korzysta z tego samego kontraktu `ingestion-service`, dzięki czemu klienci API nie wymagają zmian.
- Podgląd JSON jest wykorzystywany przez kreator konfiguracji i panel wizualizacji zgodnie z wytycznymi dane.gov.pl oraz API BDL.

### 4. Kryteria akceptacyjne
- Prawidłowy plik XLSX generuje raport z liczbą wierszy, opisem kolumn i (opcjonalnie) sugestią wizualizacji.
- Import obsługuje tryb offline dzięki repozytorium GitOps oraz zachowuje polityki audytu (landing + preview).
- Obsługiwane są scenariusze wyboru arkusza przez użytkownika lub automatycznie na podstawie profilu.

### Instrukcje dla laika
1. **Co zostało dodane?** Możesz teraz wgrać arkusz Excel, a system sam wybierze właściwy arkusz i przygotuje raport.
2. **Jak używać?** W kreatorze importu wskaż plik XLSX i – opcjonalnie – nazwę arkusza; resztą zajmie się moduł.
3. **Przykład:** Importuj plik dane.xlsx z arkuszem "Dane" – zobaczysz opis kolumn i propozycję wykresu liniowego.
4. **Korzyść:** Ekscelowe raporty urzędów można publikować w portalu bez ręcznego konwertowania do CSV.

## Etap 6 – Import JSON/API
Etap 6 rozszerza `ingestion-service` o obsługę źródeł JSON i REST API (np. dane.gov.pl, API BDL). Moduł `JSONIngestor` korzysta z
polityk `json_policy` zdefiniowanych w `config-service`, dzięki czemu zapewnia spójną walidację, JSON Pointer do wskazania listy
rekordów oraz sugestie wizualizacji oparte na strukturze odpowiedzi.

### 1. Zakres funkcjonalny
- Obsługa plików JSON oraz adresów HTTP/S z autoryzacją nagłówków `Accept` i limitami rozmiaru.
- Możliwość definiowania parametrów zapytań (`query_params`) oraz metody HTTP w zadaniu importu, zgodnie z profilami
  bezpieczeństwa (`allowed_http_methods`).
- Zastosowanie JSON Pointer (`/results`, `/data/items` itp.) do odnalezienia listy rekordów w odpowiedzi API.
- Generowanie schematu kolumn oraz podglądu JSON z ograniczeniem liczby rekordów (`max_records`, `preview_size`).
- Sugestie wizualizacji (wykres liniowy/słupkowy) lub komunikat **"BRAK MOŻLIWEJ WIZUALIZACJI"** jeśli dane nie spełniają
  kryteriów.

### 2. Proces techniczny
1. Administrator lub harmonogram uruchamia `POST /ingestion/v1/jobs` wskazując URI (plik/HTTP) i opcjonalnie parametry API.
2. `JSONIngestor` pobiera dane (plik lokalny lub HTTP), weryfikuje typ zawartości i rozmiar odpowiedzi.
3. Moduł stosuje JSON Pointer z zadania/profilu, normalizuje rekordy do słowników oraz ogranicza je do `max_records`.
4. Tworzy schemat kolumn (`ColumnSchema`), listę sugestii wizualizacji oraz zapisuje podgląd JSON i kopię źródłową w strefie
   landing.

### 3. Integracja z konfiguracją i kontraktami
- Polityka `json_policy` w profilu określa dozwolone metody HTTP, typy zawartości, limit rozmiaru i domyślny pointer (`/results`).
- Moduł korzysta z istniejącego kontraktu `ingestion-service` – klienci API otrzymują `IngestionResult` identyczny jak dla CSV/XLSX.
- Podgląd JSON wykorzystywany jest przez Studio Danych, mostek WordPress oraz dalsze etapy ETL, zachowując zgodność z DCAT-AP.

### 4. Kryteria akceptacyjne
- Poprawna odpowiedź JSON (plik lub HTTP) generuje raport z liczbą rekordów, schematem kolumn i ewentualną sugestią wizualizacji.
- Import obsługuje scenariusze online (HTTP) i offline (GitOps) dzięki fallbackowi na repozytorium profili.
- Mechanizmy limitów (`max_payload_mb`, `max_records`) chronią system przed przeciążeniem, a kopia źródłowa trafia do landing.

### Instrukcje dla laika
1. **Co zostało dodane?** Możesz podać adres API lub plik JSON – system pobierze dane, opisze kolumny i podpowie wykresy.
2. **Jak używać?** W Studio Danych wskaż profil, wpisz adres API (np. BDL) i – jeśli trzeba – podaj JSON Pointer. Raport powstanie
   automatycznie.
3. **Przykład:** Połącz się z API BDL dla wskaźnika populacji, ustaw pointer `/results` – zobaczysz tabelę i sugestię wykresu
   liniowego.
4. **Korzyść:** Dane z portali państwowych trafiają do katalogu bez ręcznego pobierania i transformacji, zachowując standardy
   bezpieczeństwa i audytu.

## Etap 14 – Zaawansowane wizualizacje i dashboardy
Etap 14 rozszerza moduł `visualization-service` o mapy choropletyczne, heatmapy, wykresy kombinowane oraz panele KPI z raportami JSON. Dodano także tryb zastępczy – w środowiskach bez biblioteki Matplotlib generowane są pliki graficzne (placeholdery) i raporty, co zapewnia ciągłość publikacji danych zgodnie z wymaganiami dane.gov.pl i API BDL.

### 1. Zakres i cele
- Obsługa zaawansowanych typów wizualizacji (`heatmap`, `choropleth`, `combo`, `kpi_dashboard`) z wykorzystaniem konfiguracji profilu (`visualization.advanced`).
- Automatyczne tworzenie raportu JSON (`*-summary.json`) zawierającego metadane wykresu, listę serii, zastosowane metryki KPI oraz informację o trybie zastępczym.
- Zapewnienie fallbacku w środowisku offline – generowane są pliki PNG/JPG/PDF z placeholderami oraz pełny raport JSON, dzięki czemu Studio Danych i WordPress zachowują spójny przepływ publikacji.

### 2. Komponenty techniczne
- `src/visualization_service/service.py` – rozbudowany `VisualizationService` z rendererami heatmap, choropleth, combo, panelu KPI oraz generatorem plików zastępczych i raportów JSON.
- `src/visualization_service/models.py` – rozszerzone modele `VisualizationRequest` (pole `options`) i `VisualizationProduct` (`summary_path`).
- `src/ingestion_service/profile.py` – nowa klasa `VisualizationAdvancedSettings`, domyślne ustawienia i parser sekcji `visualization.advanced`.
- `config/profiles/dev.json` – zaktualizowana sekcja `visualization` z listą nowych typów wykresów, paletami heatmap/choropleth i metrykami KPI.
- `tests/test_visualization_service.py` – scenariusze obejmujące tryb zastępczy, heatmapy oraz panele KPI.

### 3. Proces generowania zaawansowanych wizualizacji
1. Pipeline transformacji przygotowuje podgląd danych (`*-transformed.json`).
2. Studio Danych lub WordPress wysyła `VisualizationRequest` z typem wykresu (`heatmap`, `choropleth`, `combo` lub `kpi_dashboard`) oraz dodatkowymi opcjami (np. `region_field`).
3. `VisualizationService` oblicza serie danych i – jeśli dostępny – wykorzystuje Matplotlib do wygenerowania wykresów; w trybie fallback tworzy pliki zastępcze oraz raport JSON.
4. Moduł zapisuje pliki w `build/visualizations` oraz generuje raport `*-summary.json`, który zawiera metadane, wykorzystane metryki i status renderera.

### 4. Kryteria akceptacyjne
- Profil konfiguracyjny zawiera sekcję `visualization.advanced` z ustawieniami map, palet i metryk KPI.
- `VisualizationService` tworzy pliki graficzne (lub placeholdery) oraz raport JSON dla każdego rodzaju wizualizacji.
- Testy `tests/test_visualization_service.py` potwierdzają generowanie plików w trybie podstawowym i zastępczym, w tym poprawność metryk KPI.
- Studio Danych i wtyczka WordPress mogą publikować mapy, heatmapy i dashboardy korzystając z tych samych kontraktów API.

### Instrukcje dla laika
1. **Co zostało dodane?** Możesz tworzyć mapy regionów, heatmapy oraz panele KPI – system generuje obrazki i raport JSON.
2. **Jak używać?** W Studio Danych wybierz „Zaawansowana wizualizacja”, wskaż typ (np. heatmapa), kolumny oraz – w przypadku map – pole regionu. System zapisze pliki w `build/visualizations` oraz raport `*-summary.json`.
3. **Przykład:** Dla datasetu z kolumnami `region`, `population`, `budget` wybierz wizualizację `choropleth`. Otrzymasz pliki PNG/PDF z barwioną mapą regionów (lub placeholder, jeśli Matplotlib nie jest dostępny) oraz raport JSON z wartościami.
4. **Korzyść:** Dashboardy KPI i mapy można publikować nawet w środowisku o ograniczonych zasobach – użytkownicy końcowi widzą spójne metryki i wizualizacje zgodne ze standardami państwowymi.


## Etap 4 – Import CSV
Etap 4 dostarczył produkcyjny moduł importu CSV w `ingestion-service`, zgodny z profilami konfiguracji oraz kontraktami API etapu 3A. Funkcjonalność obejmuje pełny przepływ od walidacji pliku, przez opis kolumn, po generowanie podglądów i sugestii wizualizacji.

### 1. Zakres funkcjonalny
- Autodetekcja separatora, kodowania i struktury pliku przy pomocy `csv.Sniffer` z ograniczeniami narzuconymi przez profil.
- Budowa schematu kolumn zgodnie z DCAT-AP i publikacja podglądu JSON wykorzystywanego przez Studio Danych i mostek WordPress.
- Generowanie heurystycznych sugestii wizualizacji (liniowe, słupkowe) oraz komunikatu **"BRAK MOŻLIWEJ WIZUALIZACJI"** w przypadku braku dopasowania.
- Kopiowanie pliku do strefy landing w celu spełnienia wymogów audytu i odtworzenia procesów ETL.

### 2. Proces techniczny
1. Administrator uruchamia zadanie `POST /ingestion/v1/jobs` wskazując profil i plik.
2. `CSVIngestor` waliduje rozmiar, autodetekuje separator i odczytuje próbkę danych.
3. Moduł tworzy schemat kolumn (`ColumnSchema`) i zapisuje podgląd JSON w katalogu preview.
4. Wynik `IngestionResult` przekazywany jest do kolejki `ingestion.job.completed`, skąd może go odebrać `etl-service` i panel Studio Danych.

### 3. Integracja z konfiguracją i kontraktami
- Profil konfiguracyjny (`config-service`/GitOps) definiuje dopuszczalne separatory, rozmiar pliku i liczbę próbkowanych wierszy.
- Kontrakt `ingestion-service` opisuje strukturę żądania i odpowiedzi; moduł stosuje nagłówki wersjonowania i identyfikatory datasetów.
- Podgląd JSON i sugestie wizualizacji są spójne z wymaganiami API BDL oraz portalu dane.gov.pl (DCAT-AP).

### 4. Kryteria akceptacyjne
- Plik CSV o poprawnej strukturze generuje raport z liczbą wierszy, schematem kolumn i przynajmniej jedną sugestią wykresu (lub komunikatem o braku wizualizacji).
- Kopia pliku trafia do strefy landing z sygnaturą czasową, a podgląd JSON jest dostępny dla Studio Danych.
- Import działa zarówno przy pobieraniu profilu z `config-service`, jak i z repozytorium GitOps w trybie offline.

### Instrukcje dla laika
1. **Co zostało dodane?** Możesz wgrać plik CSV i natychmiast zobaczyć podgląd danych oraz propozycję wykresu.
2. **Jak używać?** W Studio Danych wybierz profil, wskaż plik CSV i zatwierdź import – raport pojawi się automatycznie.
3. **Przykład:** Wgraj plik populacja.csv; system zasugeruje wykres liniowy liczby mieszkańców w kolejnych latach.
4. **Korzyść:** Dane są gotowe do publikacji bez ręcznego przygotowywania schematów i raportów.

## Etap 5 – Import XLSX
Etap 5 rozszerza `ingestion-service` o obsługę plików XLSX z wykorzystaniem profili konfiguracji (`xlsx_policy`) i istniejących kontraktów API. Moduł zapewnia pełną autodetekcję arkuszy oraz integrację z procesami audytu i wizualizacji.

### 1. Zakres funkcjonalny
- Wybór arkusza na podstawie parametru zadania, listy preferowanych arkuszy w profilu lub pierwszego arkusza w skoroszycie.
- Odczyt nagłówków i próbkowanie danych zgodnie z konfiguracją `header_row_index` i `sample_size`.
- Budowa schematu kolumn oraz sugestii wizualizacji identycznych jak dla CSV, z zachowaniem komunikatu **"BRAK MOŻLIWEJ WIZUALIZACJI"**.
- Generowanie podglądu JSON zawierającego nazwę arkusza oraz zapis kopii pliku w strefie landing.

### 2. Proces techniczny
1. Zadanie importu (`POST /ingestion/v1/jobs`) wskazuje plik XLSX i opcjonalnie nazwę arkusza.
2. `XLSXIngestor` waliduje rozszerzenie, rozmiar i wybiera arkusz zgodnie z profilem (`xlsx_policy`).
3. Moduł odczytuje nagłówki oraz próbkę danych, tworzy schemat kolumn i podgląd JSON.
4. Wynik `IngestionResult` jest publikowany dla `etl-service`, panelu Studio Danych oraz przyszłego mostka WordPress.

### 3. Integracja z konfiguracją i kontraktami
- Nowe pola `xlsx_policy` w profilu definiują dozwolone rozszerzenia, preferowane arkusze i parametry próbkowania.
- Moduł korzysta z tego samego kontraktu `ingestion-service`, dzięki czemu klienci API nie wymagają zmian.
- Podgląd JSON jest wykorzystywany przez kreator konfiguracji i panel wizualizacji zgodnie z wytycznymi dane.gov.pl oraz API BDL.

### 4. Kryteria akceptacyjne
- Prawidłowy plik XLSX generuje raport z liczbą wierszy, opisem kolumn i (opcjonalnie) sugestią wizualizacji.
- Import obsługuje tryb offline dzięki repozytorium GitOps oraz zachowuje polityki audytu (landing + preview).
- Obsługiwane są scenariusze wyboru arkusza przez użytkownika lub automatycznie na podstawie profilu.

### Instrukcje dla laika
1. **Co zostało dodane?** Możesz teraz wgrać arkusz Excel, a system sam wybierze właściwy arkusz i przygotuje raport.
2. **Jak używać?** W kreatorze importu wskaż plik XLSX i – opcjonalnie – nazwę arkusza; resztą zajmie się moduł.
3. **Przykład:** Importuj plik dane.xlsx z arkuszem "Dane" – zobaczysz opis kolumn i propozycję wykresu liniowego.
4. **Korzyść:** Ekscelowe raporty urzędów można publikować w portalu bez ręcznego konwertowania do CSV.

## Kompatybilność platformowa i instalacja
Repozytorium zawiera kompletną wtyczkę WordPress (`wordpress/open-data-plugin`), która wykorzystuje kontrakty API i pozwala używać WordPressa jako systemu bazowego dla katalogu danych oraz wizualizacji. Poniższe sekcje opisują sposób instalacji i konfiguracji mostka.

### 1. Instalacja wtyczki WordPress
- **Opis techniczny**: skopiuj katalog `wordpress/open-data-plugin` do `wp-content/plugins` swojej instancji WordPress, a następnie aktywuj wtyczkę w panelu administratora. Wtyczka rejestruje typ wpisu `open_data_dataset`, panel ustawień „Studio Danych”, shortcode `[open_data_dataset]` oraz harmonogram synchronizacji `odp_sync_event` (co 12 godzin).
- **Instrukcja dla laika**: "Przeciągnij folder wtyczki do katalogu `plugins`, przejdź w WordPressie do `Wtyczki → Zainstalowane`, kliknij `Aktywuj`. W menu pojawi się nowa pozycja `Studio Danych`."
- **Efekt**: WordPress staje się bazowym CMS-em – katalog danych, wizualizacje i synchronizacja są zarządzane z panelu WP, a treści mogą być publikowane jak standardowe wpisy.

### 2. Konfiguracja i synchronizacja
- **Opis techniczny**: na stronie `Studio Danych` ustaw `Adres API (admin-gateway)`, token OAuth 2.0 i domyślny profil konfiguracji. Przycisk „Synchronizuj teraz” wywołuje `admin_post_odp_sync_now`, który pobiera `/datasets` i `/visualizations`, a wpisy są zapisywane jako `open_data_dataset`. Shortcode `[open_data_dataset id="population"]` pobiera pojedynczy zbiór i wizualizacje poprzez API (z cache'm transjentów na 5 minut).
- **Instrukcja dla laika**: "Wpisz adres serwera Open Data i klucz dostępu. Zapisz ustawienia, kliknij `Synchronizuj teraz`, a następnie wstaw shortcode `[open_data_dataset id="population"]` na dowolnej stronie, by pokazać tabelę i wykresy." 
- **Efekt**: administrator ma pełną kontrolę nad publikacją danych publicznych w WordPressie, bez konieczności ręcznego kopiowania tabel czy grafów.

### 3. Zgodność i bezpieczeństwo
- Wtyczka wykorzystuje standardowe narzędzia WordPress (Options API, WP Cron, REST API) oraz nagłówki JSON:API (`Accept: application/vnd.opendata.v1+json`). Token OAuth jest przechowywany w konfiguracji WP i dołączany do zapytań.
- Shortcode wyświetla komunikat **"BRAK MOŻLIWEJ WIZUALIZACJI"** w przypadku braku danych z backendu, co utrzymuje spójność z zachowaniem `ingestion-service`.
- Harmonogram synchronizacji gwarantuje aktualność katalogu, a rejestr typu wpisu pozwala na stosowanie wbudowanych mechanizmów wersjonowania, ról i komentarzy WordPress zgodnie z wymaganiami RODO/WCAG.

## Plan rozwoju – 20 etapów
Poniższy plan zakłada przyrostowe wdrażanie funkcji w oparciu o wymagania kompatybilne z danymi publicznymi w Polsce i UE.

1. **Analiza wymagań i standardów** – opracowanie szczegółowych specyfikacji API, formatów danych i zgodności RODO (opis techniczny) / zebranie oczekiwań biznesowych i użytkowych (opis dla laika).
2. **Architektura systemu** – zaprojektowanie modularnej architektury pluginu z warstwą integracji i wizualizacji / stworzenie mapy modułów i opisanie ich roli.
3. **Warstwa konfiguracji podstawowej** – implementacja podstawowego pliku konfiguracyjnego i mechanizmu zmiennych środowiskowych / przygotowanie prostego kreatora pierwszego uruchomienia.
4. **Obsługa importu CSV** – moduł importujący dane CSV z autodetekcją nagłówków, kodowań i separatorów (wdrożone w etapie 4) / możliwość wgrania pliku CSV i podglądu danych.
5. **Obsługa importu XLSX** – rozszerzenie importu o arkusze Excel z mapowaniem kolumn (wdrożone w etapie 5) / przeciągnij i upuść pliku XLSX oraz wybór arkusza.
6. **Obsługa źródeł JSON i API REST** – konektor do API w formacie JSON (w tym dane.gov.pl, API BDL) z walidacją schematów / wprowadź adres API, a system pobierze i pokaże dane.
7. **Obsługa źródeł URL i plików zdalnych** – harmonogram synchronizacji danych pobieranych z podanych URL / ustaw częstotliwość odświeżania danych z internetu.
8. **Integracja bazodanowa** – moduły połączeń do PostgreSQL, MySQL oraz MS SQL z mapowaniem tabel / wprowadź dane logowania i wybierz tabele do analizy.
9. **Silnik transformacji danych** – implementacja pipeline ETL (czyszczenie, filtrowanie, agregacje) / kreator kroków czyszczenia danych.
10. **Warstwa metadanych** – tworzenie słowników metadanych zgodnych ze standardami danych publicznych, w tym opisy pól i jednostek (wdrożone w etapie 10) / opisuj kolumny prostym językiem, a system zapisze katalog DCAT-AP automatycznie.
11. **System uprawnień i audytu** – role użytkowników, logowanie działań i historia zmian / nadawaj uprawnienia i sprawdzaj kto zmieniał dane.
12. **Panel administratora (Studio Danych) – konfiguracja globalna i integrator WordPress** – interfejs do zarządzania ustawieniami pluginu (API, wizualizacje, użytkownicy) wraz z kreatorem połączenia WordPress i autoinstalatora / jedno miejsce do zarządzania całym systemem i publikacją na stronach WordPress.
13. **Moduł wizualizacji podstawowych** – generowanie wykresów liniowych, słupkowych i kołowych z możliwością eksportu PNG/PDF / wybierz wykres i pobierz go jako obraz.
14. **Zaawansowane wizualizacje i dashboardy** – mapy choropletyczne, heatmapy, wykresy kombinowane, dashboardy z kartami KPI / buduj ekrany analityczne na dane publiczne.
15. **Generator raportów** – tworzenie raportów PDF/HTML z opisami danych i wizualizacjami / jednym kliknięciem generuj raporty dla interesariuszy.
16. **API publikacyjne** – udostępnianie przetworzonych danych w formie REST/GraphQL zgodnie ze standardami UE / partnerzy integrują się z gotowym API.
17. **Automatyzacja procesów** – harmonogramy, webhooki i zdarzenia do uruchamiania procesów ETL i publikacji / ustaw reguły, kiedy odświeżać dane.
18. **Moduł jakości danych** – statystyki jakości, alerty o brakach, sugestie naprawy / otrzymuj powiadomienia, gdy dane są niepełne.
19. **Międzynarodowe standardy i lokalizacja** – wsparcie wielu języków, zgodność DCAT-AP, INSPIRE / łatwo udostępniaj dane użytkownikom z UE.
20. **Monitoring i analityka wykorzystania** – metryki wydajności, użycia API i wizualizacji, integracja z narzędziami BI / monitoruj, jak użytkownicy korzystają z wtyczki.

- **Co mamy teraz?** Plan działania, specyfikację (etap 1), architekturę (etap 2), warstwę konfiguracji i kontrakty API (etap 3/3A) oraz działające importy CSV (etap 4), XLSX (etap 5), JSON/API (etap 6), harmonogram synchronizacji URL (etap 7), integrację bazodanową (etap 8), pipeline transformacji (etap 9), katalog metadanych DCAT-AP (etap 10), system uprawnień i audytu (etap 11), panel Studio Danych z integratorem WordPress (etap 12) oraz moduł wizualizacji podstawowych (etap 13).
- **Jak tego użyć?** W Studio Danych wybierz profil konfiguracji, wskaż plik CSV/XLSX, adres API JSON, źródło zdalne lub połączenie bazodanowe (albo uruchom komendę `python -m ingestion_service`, `python -m ingestion_service.xlsx_ingestor`, `python -m ingestion_service.json_ingestor`, wykorzystaj `RemoteSyncManager` lub funkcję `build_default_database_ingestor`) – system pobierze ustawienia z `config-service`, zapisze podgląd i kopię danych.
- **Przykład:** Administrator importuje `sample_population.csv`, `dane.xlsx`, wskazuje API BDL z pointerem `/results`, dodaje cykliczne pobieranie `https://example.gov/population.csv` lub wybiera połączenie `demo_postgres` z tabelą `public.population`; w kilka sekund otrzymuje schemat kolumn, propozycję wykresu oraz komunikat **"BRAK MOŻLIWEJ WIZUALIZACJI"** jeśli dane są niekompletne.
- **Jak działa import XLSX?** Jeżeli nie wskażesz arkusza, moduł wybierze go automatycznie na podstawie profilu; podgląd pokaże nazwę arkusza i pierwsze wiersze danych.
- **Jak działa import JSON/API?** System pobiera odpowiedź HTTP, stosuje JSON Pointer z profilu i ogranicza liczbę rekordów zgodnie z polityką – podgląd JSON pokazuje pierwsze wpisy oraz parametry zapytania.
- **Co to daje użytkownikowi?** Możesz publikować dane szybciej i bezpieczniej – pliki, odpowiedzi API oraz cyklicznie pobierane zasoby URL trafiają do kontrolowanych katalogów, a opis kolumn i wizualizacje tworzą się automatycznie niezależnie od formatu.
- **Czy działa z WordPressem już teraz?** Tak – wtyczka `wordpress/open-data-plugin` działa wraz z panelem Studio Danych (etap 12). Po zainstalowaniu można rejestrować instancje WordPress, wyzwalać synchronizację metadanych (licencja, słowa kluczowe, JSON-LD) i korzystać z wizualizacji wygenerowanych w etapie 13.

## Kolejne kroki natychmiastowe
1. Rozpocząć etap 14 – rozbudować moduł wizualizacji o mapy choropletyczne, heatmapy i dashboardy z kartami KPI wraz z eksportem interaktywnym.
2. Utworzyć repozytorium GitOps dla konfiguracji i kontraktów (`config-ci`) z walidacją OpenAPI/GraphQL/AsyncAPI oraz publikacją SDK (TypeScript/Python).
3. Przygotować testy integracyjne `ingestion_service` → `TransformationPipeline` → `visualization_service` → `metadata_service` → WordPress, aby potwierdzić publikację wizualizacji i metadanych JSON-LD.
4. Opracować polityki bezpieczeństwa Kubernetes (NetworkPolicies, PodSecurity, SecretStore CSI) dla `config-service`, `ingestion-service`, `metadata-service`, `visualization-service` oraz storage landing/preview/visualizations.
5. Zaplanować etap 15 (generator raportów PDF/HTML) – określić strukturę szablonów oraz integrację z pipeline'em wizualizacji i metadanych.

Pozostało 7 etapów (14–20) do zrealizowania zgodnie z planem rozwoju.

## Zgodność ze standardami
- Architektura i konfiguracja wspierają integrację z portalem dane.gov.pl oraz API BDL poprzez dedykowane konektory, bezpieczne przechowywanie kluczy i mapowanie metadanych DCAT-AP.
- Uwzględniono europejskie standardy bezpieczeństwa i dostępności (eIDAS, WCAG 2.1, INSPIRE, ENISA), a także wymagania RODO dotyczące lokalizacji danych, audytu i rotacji tajemnic.
