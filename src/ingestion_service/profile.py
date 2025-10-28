"""
Module: ingestion_service.profile
Opis: Definiuje modele profili konfiguracyjnych pobieranych z `config-service` na
potrzeby importu CSV, XLSX, źródeł JSON/API, synchronizacji zdalnych URL (Etap 7),
integracji bazodanowej (Etap 8), pipeline'u transformacji danych (Etap 9),
warstwy metadanych DCAT-AP (Etap 10), systemu uprawnień i audytu (Etap 11),
panelu administracyjnego Studio Danych z integracją WordPress (Etap 12) oraz
modułu wizualizacji podstawowych i zaawansowanych (Etapy 13–14) oraz generatora raportów (Etap 15).
Funkcje i klasy:
- class ConfigProfile: reprezentuje kompletny profil konfiguracji ingestu.
- class StoragePaths: przechowuje ścieżki zapisu danych i schematów.
- class IngestionPolicy: zawiera zasady walidacji i autodetekcji dla CSV.
- class XLSXPolicy: określa reguły importu plików XLSX (arkusze, nagłówki, rozmiary).
- class JsonPolicy: opisuje zasady pracy z API JSON (limity rekordów, pointer, metody HTTP).
- class RemotePolicy: opisuje zasady pobierania plików zdalnych oraz harmonogram synchronizacji URL.
- class DatabasePolicy: reguły bezpieczeństwa i limitów dla połączeń bazodanowych.
- class DatabaseConnection: opis pojedynczego połączenia JDBC/ODBC obsługiwanego przez profil.
- class TransformationPolicy: reguły wykonywania pipeline'u ETL (Etap 9).
- class TransformationStepConfig: deklaracja pojedynczego kroku transformacji.
- class MetadataStorage: lokalizacja rejestru metadanych i eksportów JSON-LD.
- class MetadataPolicy: zasady katalogowania (licencja, kontakt, słowa kluczowe).
- class AdminStudioSection / AdminWordPressSection / AdminSettings: konfiguracja
  panelu Studio Danych i integracji WordPress (Etap 12).
- class VisualizationAdvancedSettings / VisualizationSettings: konfiguracja modułu
  wizualizacji podstawowych i zaawansowanych (Etapy 13–14).
- class ReportTemplateSettings / ReportAuthoringSettings / ReportSettings: ustawienia
  generatora raportów HTML/PDF (Etap 15).
- class RoleDefinition: opis roli RBAC wykorzystywany przez etap 11.
- class AuditPolicy: zasady retencji i lokalizacji logów audytu.
- class AuthPolicy: konfiguracja systemu uprawnień (RBAC/ABAC) i audytu.
- function profile_from_dict: buduje obiekt ConfigProfile na podstawie słownika z
  `config-service` lub repozytorium GitOps.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence


@dataclass(frozen=True)
class StoragePaths:
    """
    Technical description:
        Reprezentuje ścieżki przechowywania zasobów wymagane przez pipeline ingestu
        CSV, XLSX oraz JSON/API. Pola `landing`, `schema_registry` i `preview` wskazują
        odpowiednio katalog na surowe pliki, rejestr schematów oraz miejsce zapisu
        podglądów.

    Instructions for laika:
        "Ta klasa to uporządkowana kartka z adresami katalogów. Dzięki niej system
        wie, gdzie zapisać oryginalny plik, gdzie przechować opis kolumn oraz gdzie
        włożyć podgląd danych dla panelu administratora – niezależnie, czy plik
        pochodzi z CSV, Excela czy API JSON."

    Example:
        ```python
        paths = StoragePaths(
            landing="/data/landing", schema_registry="/data/schemas", preview="/data/preview"
        )
        ```
    Effect for end user:
        Zapewnia, że dane i ich opisy zawsze lądują w przewidywalnych miejscach,
        co ułatwia ich dalszą publikację w portalu zgodnym z dane.gov.pl.
    """

    landing: str
    schema_registry: str
    preview: str


@dataclass(frozen=True)
class IngestionPolicy:
    """
    Technical description:
        Definiuje zasady walidacji importu CSV. Parametry obejmują dozwolone
        separatory, domyślne kodowanie, maksymalny rozmiar pliku oraz liczbę
        wierszy używanych do autodetekcji typu kolumn.

    Instructions for laika:
        "To zestaw reguł bezpieczeństwa – mówi, jakie pliki można wgrywać,
        jakich separatorów użyć i jak duże mogą być arkusze. Dzięki temu system
        odmówi wczytania niepoprawnych danych zanim trafią do katalogu."

    Example:
        ```python
        policy = IngestionPolicy(
            allowed_separators=[",", ";"],
            default_encoding="utf-8",
            max_file_size_mb=50,
            sample_size=500,
            timezone="Europe/Warsaw",
        )
        ```
    Effect for end user:
        Gwarantuje, że w panelu Studio Danych użytkownik otrzymuje poprawne,
        dobrze opisane dane bez potrzeby ręcznego sprawdzania jakości pliku.
    """

    allowed_separators: Sequence[str]
    default_encoding: str
    max_file_size_mb: int
    sample_size: int
    timezone: str


@dataclass(frozen=True)
class XLSXPolicy:
    """
    Technical description:
        Zawiera reguły importu arkuszy kalkulacyjnych XLSX. Parametry określają
        dopuszczalne rozszerzenia, limit rozmiaru pliku, liczbę wierszy próbkowanych
        do analizy oraz preferowaną kolejność arkuszy i numer wiersza nagłówkowego.

    Instructions for laika:
        "To instrukcja, jak traktować pliki Excel – które arkusze brać pod uwagę,
        ile wierszy sprawdzać i gdzie znajdują się nagłówki kolumn. Dzięki temu
        system potrafi sam odnaleźć właściwe dane w pliku wieloarkuszowym."

    Example:
        ```python
        xlsx_policy = XLSXPolicy(
            allowed_extensions=[".xlsx"],
            max_file_size_mb=20,
            sample_size=200,
            preferred_sheets=["Dane", "Arkusz1"],
            header_row_index=1,
        )
        ```
    Effect for end user:
        Administrator nie musi ręcznie wskazywać arkusza – profil zapisany w
        konfiguracji zapewnia spójny import zgodny z wymaganiami dane.gov.pl.
    """

    allowed_extensions: Sequence[str]
    max_file_size_mb: int
    sample_size: int
    preferred_sheets: Sequence[str]
    header_row_index: int


@dataclass(frozen=True)
class JsonPolicy:
    """
    Technical description:
        Definiuje reguły obsługi źródeł JSON i API REST wykorzystywanych w etapie 6.
        Parametry określają dozwolone metody HTTP, typy zawartości, limit rozmiaru
        odpowiedzi, maksymalną liczbę rekordów oraz domyślny wskaźnik (JSON Pointer)
        prowadzący do listy wyników.

    Instructions for laika:
        "To instrukcja, jak łączyć się z API: które metody zapytań wolno używać,
        jak duże mogą być odpowiedzi i gdzie w odebranym pliku JSON znajdują się
        właściwe dane. Dzięki temu system potrafi pobrać dane z portali państwowych
        (np. dane.gov.pl, API BDL) bez dodatkowej konfiguracji."

    Example:
        ```python
        json_policy = JsonPolicy(
            allowed_http_methods=("GET", "POST"),
            allowed_content_types=("application/json",),
            max_payload_mb=10,
            max_records=1000,
            default_pointer="/results",
            http_timeout=15,
            preview_size=25,
        )
        ```
    Effect for end user:
        Administrator wskazuje jedynie adres API oraz profil – reszta parametrów
        (limity, format danych, liczba rekordów w podglądzie) jest kontrolowana
        automatycznie, co zwiększa bezpieczeństwo i zgodność ze standardami
        państwowymi.
    """

    allowed_http_methods: Sequence[str]
    allowed_content_types: Sequence[str]
    max_payload_mb: int
    max_records: int
    default_pointer: str
    http_timeout: int
    preview_size: int


@dataclass(frozen=True)
class RemotePolicy:
    """
    Technical description:
        Definiuje reguły obsługi zdalnych źródeł danych (Etap 7). Parametry określają
        dozwolone schematy URL, maksymalny rozmiar pobieranych plików, ścieżki
        przechowywania kopii i stanów synchronizacji, domyślną częstotliwość
        odświeżania (ISO 8601 Duration), politykę ponowień oraz kontrolę TLS.

    Instructions for laika:
        "To zestaw zasad mówiący, z jakich adresów internetowych wolno pobierać
        dane, jak często je aktualizować i gdzie zapisać kopie bezpieczeństwa.
        Dzięki temu system automatycznie pilnuje harmonogramu synchronizacji."

    Example:
        ```python
        remote_policy = RemotePolicy(
            allowed_schemes=("https", "http"),
            allowed_content_types=("text/csv", "application/json"),
            max_file_size_mb=50,
            download_cache="./data/cache",
            state_registry="./data/state",
            default_schedule="PT12H",
            verify_tls=True,
            retry_attempts=3,
            retry_backoff_seconds=30,
        )
        ```
    Effect for end user:
        Administrator ma pewność, że synchronizacja z zewnętrznymi portalami (np.
        dane.gov.pl, API BDL) odbywa się cyklicznie, zgodnie z polityką
        bezpieczeństwa i bez ręcznego pobierania plików.
    """

    allowed_schemes: Sequence[str]
    allowed_content_types: Sequence[str]
    max_file_size_mb: int
    download_cache: str
    state_registry: str
    default_schedule: str
    verify_tls: bool
    retry_attempts: int
    retry_backoff_seconds: int


@dataclass(frozen=True)
class VisualizationAdvancedSettings:
    """
    Technical description:
        Definiuje ustawienia zaawansowanych wizualizacji (Etap 14). Pozwala
        kontrolować obsługę map (pole `map_region_field`), paletę heatmap,
        paletę choropleth, listę metryk KPI oraz układ dashboardu Studio Danych.
        Dzięki temu moduł wizualizacji może tworzyć mapy, heatmapy, wykresy
        kombinowane i panele KPI zgodne z wytycznymi dane.gov.pl oraz API BDL.

    Instructions for laika:
        "To lista dodatkowych ustawień dla map i dashboardów. Określasz tutaj,
        jak nazywa się kolumna z regionem, jakie kolory ma mieć heatmapa oraz
        jakie metryki pojawią się w panelu KPI. Dzięki temu każdy raport będzie
        wyglądał spójnie."

    Example:
        ```python
        advanced = VisualizationAdvancedSettings(
            enable_advanced=True,
            map_region_field="region",
            heatmap_palette=("#08306B", "#08519C", "#2171B5"),
            choropleth_palette=("#1D70B8", "#3B8AC4", "#6BB1D8"),
            kpi_metrics=("sum", "avg", "max"),
            dashboard_layout=("metric", "chart", "notes"),
        )
        ```
    Effect for end user:
        Administrator otrzymuje mapy i dashboardy zgodne z brandingiem GOV.PL,
        a użytkownik końcowy widzi te same kolory i metryki w każdej instalacji
        WordPressa.
    """

    enable_advanced: bool
    map_region_field: str
    heatmap_palette: Sequence[str]
    choropleth_palette: Sequence[str]
    kpi_metrics: Sequence[str]
    dashboard_layout: Sequence[str]


@dataclass(frozen=True)
class VisualizationSettings:
    """
    Technical description:
        Reprezentuje ustawienia modułu wizualizacji (Etapy 13–14). Określa katalog
        wyjściowy (`output_dir`), domyślne formaty eksportu (np. PNG, PDF),
        wspierane typy wykresów (`default_chart_types`), rozmiar figury (w
        calach), rozdzielczość DPI, paletę kolorów, kolor tła, maksymalną liczbę
        serii renderowanych jednocześnie, prefiks tytułów generowanych
        automatycznie oraz ustawienia sekcji `advanced` odpowiedzialnej za mapy,
        heatmapy i panele KPI.

    Instructions for laika:
        "To lista ustawień mówiących, gdzie zapisać obrazki z wykresami, w jakich
        kolorach mają być narysowane i ile linii można na nich pokazać. Dzięki
        temu wszystkie wizualizacje wyglądają spójnie."

    Example:
        ```python
        viz = VisualizationSettings(
            output_dir="build/visualizations",
            default_formats=("png", "pdf"),
            default_chart_types=("line", "bar", "heatmap"),
            figure_size=(10, 6),
            dpi=150,
            color_palette=("#0A6FB4", "#59B4D1"),
            background_color="#FFFFFF",
            max_series=4,
            title_prefix="Wizualizacja",
            advanced=VisualizationAdvancedSettings(
                enable_advanced=True,
                map_region_field="region",
                heatmap_palette=("#08306B", "#2171B5"),
                choropleth_palette=("#1D70B8", "#3B8AC4"),
                kpi_metrics=("sum", "avg", "max"),
                dashboard_layout=("metric", "chart", "notes"),
            ),
        )
        ```
    Effect for end user:
        Administrator i WordPress otrzymują wykresy, mapy i panele KPI o
        jednolitej stylistyce, przygotowane w formatach wymaganych przez
        dane.gov.pl oraz API BDL.
    """

    output_dir: str
    default_formats: Sequence[str]
    default_chart_types: Sequence[str]
    figure_size: Sequence[float]
    dpi: int
    color_palette: Sequence[str]
    background_color: str
    max_series: int
    title_prefix: str
    advanced: VisualizationAdvancedSettings


@dataclass(frozen=True)
class ReportTemplateSettings:
    """
    Technical description:
        Określa ustawienia szablonu raportu (Etap 15). Zawiera ścieżkę do
        pliku HTML, prefiks tytułu oraz flagę `include_styles`, która
        decyduje o osadzaniu stylów CSS w wygenerowanym dokumencie.
        Szablon jest używany przez `ReportService` zarówno podczas tworzenia
        raportów HTML, jak i przy generowaniu fallbacku PDF.

    Instructions for laika:
        "To ustawienia wyglądu raportu. Wskazujesz plik HTML, z którego
        korzystamy, oraz to, czy mamy dołączyć style w samym dokumencie.
        Dzięki temu każdy raport wygląda tak samo, niezależnie od tego,
        kto go generuje."

    Example:
        ```python
        template = ReportTemplateSettings(
            html="templates/report.html",
            title_prefix="Raport danych",
            include_styles=True,
        )
        ```
    Effect for end user:
        Raporty mają spójny wygląd i nagłówki zgodne z identyfikacją
        wizualną instytucji publikującej dane.
    """

    html: str
    title_prefix: str
    include_styles: bool


@dataclass(frozen=True)
class ReportAuthoringSettings:
    """
    Technical description:
        Przechowuje informacje o autorze raportu – nazwę jednostki i adres
        kontaktowy. Dane te trafiają do stopki dokumentu, co jest wymagane
        przez wytyczne dane.gov.pl oraz API BDL w zakresie transparentności
        publikacji.

    Instructions for laika:
        "Wpisujesz, kto przygotował raport i na jaki e-mail można wysłać
        pytania. Dzięki temu odbiorca zawsze wie, z kim się skontaktować."

    Example:
        ```python
        authoring = ReportAuthoringSettings(
            prepared_by="Biuro Otwartego Dostępu",
            contact_email="reports@example.gov",
        )
        ```
    Effect for end user:
        Czytelnik raportu widzi dane kontaktowe i może łatwo zgłosić pytania
        lub uwagi dotyczące opublikowanych informacji.
    """

    prepared_by: str
    contact_email: str


@dataclass(frozen=True)
class ReportSettings:
    """
    Technical description:
        Definiuje parametry generatora raportów (Etap 15). Określa katalog
        wyjściowy, listę formatów (np. HTML, PDF), ustawienia szablonu oraz
        flagi decydujące o dołączaniu podsumowań wizualizacji, eksportów
        JSON-LD i śladów audytu. Pola `authoring` i `template` zapewniają, że
        raport zawiera komplet informacji wymaganych przez standardy UE.

    Instructions for laika:
        "To konfiguracja kreatora raportów. Mówisz systemowi, gdzie zapisać
        pliki, w jakich formatach mają powstać i czy dołączyć podsumowania
        wykresów lub JSON-LD. Dzięki temu raport powstaje jednym kliknięciem
        bez ręcznej edycji."

    Example:
        ```python
        reports = ReportSettings(
            output_dir="build/reports",
            formats=("html", "pdf"),
            template=ReportTemplateSettings(
                html="templates/report.html",
                title_prefix="Raport danych",
                include_styles=True,
            ),
            include_visualization_summary=True,
            attach_jsonld=True,
            include_audit_trail=True,
            authoring=ReportAuthoringSettings(
                prepared_by="Biuro Otwartego Dostępu",
                contact_email="reports@example.gov",
            ),
        )
        ```
    Effect for end user:
        Administrator otrzymuje kompletne raporty z wykresami, licencją i
        informacjami kontaktowymi – zgodne z oczekiwaniami interesariuszy
        i gotowe do publikacji w portalu danych publicznych.
    """

    output_dir: str
    formats: Sequence[str]
    template: ReportTemplateSettings
    include_visualization_summary: bool
    attach_jsonld: bool
    include_audit_trail: bool
    authoring: ReportAuthoringSettings


@dataclass(frozen=True)
class DatabasePolicy:
    """
    Technical description:
        Określa reguły korzystania z połączeń bazodanowych opisanych w etapie 8.
        Parametry definiują dozwolone drivery SQLAlchemy (PostgreSQL, MySQL,
        SQL Server), maksymalną liczbę pobieranych rekordów, domyślne limity
        zapytań oraz ścieżkę cache metadanych stosowaną przy introspekcji
        schematów. Pole `timezone` pozwala mapować strefę czasową danych na
        ustawienia profilu.

    Instructions for laika:
        "To zbiór zasad bezpieczeństwa dla połączeń z bazą danych. Mówi, z jakich
        baz możemy korzystać, ile rekordów pobieramy naraz i gdzie zapisać
        pamięć podręczną opisów tabel. Dzięki temu import z baz danych działa
        szybko i bezpiecznie."

    Example:
        ```python
        db_policy = DatabasePolicy(
            allowed_drivers=("postgresql", "mysql", "mssql"),
            max_rows=5000,
            default_limit=1000,
            metadata_cache="./data/db-metadata",
            timezone="Europe/Warsaw",
        )
        ```
    Effect for end user:
        Administrator ma pewność, że pobieranie danych z baz relacyjnych odbywa
        się w kontrolowany sposób zgodny z limitami danych.gov.pl i API BDL.
    """

    allowed_drivers: Sequence[str]
    max_rows: int
    default_limit: int
    metadata_cache: str
    timezone: str


@dataclass(frozen=True)
class DatabaseConnection:
    """
    Technical description:
        Reprezentuje pojedyncze połączenie bazodanowe dostępne w profilu. Pole
        `url` przechowuje łańcuch połączenia SQLAlchemy (np. PostgreSQL, MySQL,
        MS SQL), `driver` określa typ silnika, `default_schema` wskazuje
        schemat/namespace, a `options` zawiera dodatkowe parametry (np. nazwa
        roli, szyfrowanie). Pole `description` służy do wyświetlenia informacji w
        Studio Danych.

    Instructions for laika:
        "To wizytówka konkretnej bazy danych. Zawiera adres połączenia, opis i
        dodatkowe ustawienia. Dzięki temu wystarczy wybrać nazwę połączenia z
        listy, aby pobrać dane do raportu."

    Example:
        ```python
        conn = DatabaseConnection(
            connection_id="gus_postgres",
            url="postgresql+psycopg2://user:pass@host/db",
            driver="postgresql",
            default_schema="public",
            description="Repozytorium danych GUS",
            options={"sslmode": "require"},
        )
        ```
    Effect for end user:
        Administrator wybiera nazwę połączenia w kreatorze Studio Danych i może
        natychmiast pobrać aktualne dane z systemów transakcyjnych bez ręcznego
        wpisywania parametrów technicznych.
    """

    connection_id: str
    url: str
    driver: str
    default_schema: Optional[str]
    description: str
    options: Dict[str, Any]


@dataclass(frozen=True)
class TransformationPolicy:
    """
    Technical description:
        Określa zasady działania pipeline'u transformacji danych (etap 9).
        Parametry obejmują włączenie/wyłączenie transformacji, maksymalną
        liczbę wierszy przetwarzanych w jednym przebiegu, precyzję zaokrągleń
        oraz listę dozwolonych operacji (`normalize_headers`, `rename_columns`,
        `filter_rows`, `derive_column`, `aggregate`).

    Instructions for laika:
        "To zestaw reguł bezpieczeństwa dla przeróbki danych. Mówimy, czy
        transformacje są aktywne, ile wierszy wolno obrabiać naraz i jakie kroki
        są dozwolone. Dzięki temu żaden krok nie zrobi czegoś, na co się nie
        zgadzamy."

    Example:
        ```python
        policy = TransformationPolicy(
            enabled=True,
            max_rows=5000,
            rounding_precision=2,
            allowed_operations=("normalize_headers", "filter_rows"),
        )
        ```
    Effect for end user:
        Administrator ma pewność, że transformacje odbywają się w kontrolowany
        sposób i spełniają wymagania audytu oraz standardów dane.gov.pl.
    """

    enabled: bool
    max_rows: int
    rounding_precision: int
    allowed_operations: Sequence[str]


@dataclass(frozen=True)
class TransformationStepConfig:
    """
    Technical description:
        Reprezentuje deklarację pojedynczego kroku transformacji zdefiniowanego
        w profilu konfiguracyjnym. Pola odpowiadają strukturze przekazywanej w
        `config-service` (`operation`, `parameters`).

    Instructions for laika:
        "To zapis kroku przepisu na dane – np. 'zmień nazwę kolumny rok na
        year'. Każdy krok ma swoją nazwę i dodatkowe parametry."

    Example:
        ```python
        step = TransformationStepConfig(operation="rename_columns", parameters={"mapping": {"rok": "year"}})
        ```
    Effect for end user:
        Ułatwia zarządzanie powtarzalnymi krokami – administrator może tworzyć
        szablony transformacji bez dotykania kodu.
    """

    operation: str
    parameters: Dict[str, Any]


@dataclass(frozen=True)
class MetadataStorage:
    """
    Technical description:
        Określa lokalizacje przechowywania metadanych DCAT-AP. Pole `registry`
        wskazuje katalog, w którym `metadata_service` utrzymuje pliki JSON z
        opisami zbiorów, a `exports` zawiera ścieżkę do katalogu z gotowymi
        eksportami JSON-LD publikowanymi w GitOps lub WordPress.

    Instructions for laika:
        "To lista folderów, w których zapisywany jest opis zbiorów danych i
        gotowe pliki do publikacji. Dzięki temu zawsze wiadomo, gdzie szukać
        katalogu." 

    Example:
        ```python
        storage = MetadataStorage(
            registry="build/metadata/registry",
            exports="build/metadata/exports",
        )
        ```
    Effect for end user:
        Administrator oraz WordPress otrzymują przewidywalne miejsca zapisu
        katalogu danych, co ułatwia publikację i audyt.
    """

    registry: str
    exports: str


@dataclass(frozen=True)
class MetadataPolicy:
    """
    Technical description:
        Definiuje domyślne wartości metadanych DCAT-AP: licencję, wydawcę,
        częstotliwość aktualizacji, punkt kontaktowy, listę słów kluczowych i
        taksonomię tematów. Flaga `auto_publish_jsonld` decyduje, czy pliki
        JSON-LD mają być generowane automatycznie po każdej aktualizacji.

    Instructions for laika:
        "To zestaw zasad opisujących każdy zbiór danych: jaką ma licencję,
        kto jest opiekunem i jakie słowa kluczowe dodać. System korzysta z tych
        ustawień, gdy tworzy katalog." 

    Example:
        ```python
        policy = MetadataPolicy(
            default_license="CC BY 4.0",
            default_publisher="Miasto Demo",
            default_contact_name="Zespół Open Data",
            default_contact_email="opendata@example.gov",
            default_accrual_periodicity="P1M",
            default_spatial="PL",
            default_language="pl",
            keyword_strategy=("dane publiczne", "demo"),
            theme_taxonomy=("DEMOGRAFIA",),
            auto_publish_jsonld=True,
            default_temporal_start=None,
            default_temporal_end=None,
        )
        ```
    Effect for end user:
        Zbiory danych automatycznie otrzymują poprawne licencje, kontakt i
        słowa kluczowe – katalog danych jest spójny z wymaganiami dane.gov.pl
        i API BDL bez dodatkowej konfiguracji.
    """

    default_license: str
    default_publisher: str
    default_contact_name: str
    default_contact_email: str
    default_accrual_periodicity: str
    default_spatial: str
    default_language: str
    keyword_strategy: Sequence[str]
    theme_taxonomy: Sequence[str]
    auto_publish_jsonld: bool
    default_temporal_start: Optional[str]
    default_temporal_end: Optional[str]


@dataclass(frozen=True)
class AdminStudioSection:
    """
    Technical description:
        Reprezentuje sekcję "studio" konfiguracji administracyjnej (etap 12).
        Zawiera nazwę profilu domyślnego, listę dostępnych profili, słownik
        flag modułów, ustawienia brandingu oraz strukturę menu prezentowaną w
        Studio Danych.

    Instructions for laika:
        "To ustawienia panelu: które profile można wybrać, jakie moduły są
        włączone, jakie logo i e-mail wsparcia pokazać oraz jakie zakładki mają
        być widoczne."

    Example:
        ```python
        AdminStudioSection(
            default_profile="dev",
            allowed_profiles=("dev",),
            feature_flags={"ingestion": True, "wordpress": True},
            branding={"support_email": "help@example.gov"},
            menu=(
                {"id": "dashboard", "label": "Pulpit", "permissions": ["studio.dashboard.view"]},
            ),
        )
        ```

    Effect for end user:
        Zapewnia spójny wygląd i funkcjonalność panelu Studio Danych zgodnie z
        wymaganiami dane.gov.pl oraz API BDL.
    """

    default_profile: str
    allowed_profiles: Sequence[str]
    feature_flags: Dict[str, bool]
    branding: Dict[str, Any]
    menu: Sequence[Dict[str, Any]]


@dataclass(frozen=True)
class AdminWordPressSection:
    """
    Technical description:
        Opisuje sekcję "wordpress" w konfiguracji administracyjnej. Określa,
        czy integracja jest włączona, domyślny interwał synchronizacji oraz
        parametry generatora paczki instalacyjnej.

    Instructions for laika:
        "To ustawienia połączenia z WordPressem: czy integracja działa, co ile
        godzin synchronizować dane i jak nazwać plik ZIP z wtyczką."

    Example:
        ```python
        AdminWordPressSection(
            enabled=True,
            auto_sync_interval="PT12H",
            installer={"bundle_directory": "build/installers", "package_name": "open-data-plugin.zip"},
        )
        ```

    Effect for end user:
        Umożliwia zautomatyzowanie publikacji danych w WordPressie oraz
        generowanie instalatora jednym kliknięciem.
    """

    enabled: bool
    auto_sync_interval: str
    installer: Dict[str, str]


@dataclass(frozen=True)
class AdminSettings:
    """
    Technical description:
        Łączy sekcje "studio" i "wordpress" konfiguracji administracyjnej.
        Obiekt ten jest przekazywany do `AdminGatewayService` i WordPress
        bridge, aby zapewnić spójną konfigurację panelu.

    Instructions for laika:
        "To cały zestaw ustawień panelu – zarówno wygląd Studio Danych, jak i
        parametry integracji WordPress."

    Example:
        ```python
        AdminSettings(
            studio=AdminStudioSection(...),
            wordpress=AdminWordPressSection(...)
        )
        ```

    Effect for end user:
        Administrator zarządza konfiguracją w jednym miejscu, a wszystkie
        moduły (panel, integracje) używają tych samych ustawień.
    """

    studio: AdminStudioSection
    wordpress: AdminWordPressSection


@dataclass(frozen=True)
class RoleDefinition:
    """
    Technical description:
        Opisuje rolę RBAC używaną przez moduł autoryzacji (Etap 11). Zawiera
        listę uprawnień (`permissions`), dziedziczenie (`inherits`) oraz reguły
        ABAC (`attribute_rules`) w postaci słowników kompatybilnych z
        `AttributeRule` (`attribute`, `allowed`, `denied`, `required`, `conditions`).

    Instructions for laika:
        "To definicja roli, np. Administrator Danych – wymieniamy tu, jakie ma
        pozwolenia oraz dodatkowe zasady bezpieczeństwa."

    Example:
        ```python
        RoleDefinition(
            name="data_admin",
            permissions=("datasets.publish", "datasets.view"),
            description="Administrator danych publicznych",
            attribute_rules=(
                {"attribute": "classification", "allowed": ["public"], "required": True}
            ),
            inherits=("data_viewer",)
        )
        ```

    Effect for end user:
        Studio Danych może budować kreator ról i tłumaczyć użytkownikom, jakie
        działania wolno im wykonywać oraz kiedy potrzebna jest dodatkowa zgoda.
    """

    name: str
    permissions: Sequence[str]
    description: str
    attribute_rules: Sequence[Dict[str, Any]]
    inherits: Sequence[str]


@dataclass(frozen=True)
class AuditPolicy:
    """
    Technical description:
        Określa politykę audytu: lokalizację pliku (`storage_path`), limit
        przechowywanych wpisów (`retention`) oraz opcję powiadamiania przy
        odmowie (`notify_on_deny`).

    Instructions for laika:
        "To ustawienia dziennika działań – gdzie przechowywać plik i ile
        wpisów zachować."

    Example:
        ```python
        AuditPolicy(storage_path="build/audit/audit-log.json", retention=1000, notify_on_deny=True)
        ```

    Effect for end user:
        Zapewnia spełnienie wymogów audytu (dane.gov.pl, API BDL) i pozwala
        łatwo znaleźć historię operacji.
    """

    storage_path: str
    retention: int
    notify_on_deny: bool


@dataclass(frozen=True)
class AuthPolicy:
    """
    Technical description:
        Grupuje definicje ról (`roles`), zestaw ról domyślnych (`default_roles`)
        oraz politykę audytu (`audit`). Sekcja jest synchronizowana z
        `AuthorizationService` w etapie 11.

    Instructions for laika:
        "To komplet ustawień bezpieczeństwa – jakie role istnieją, kto je
        dostaje domyślnie i gdzie zapisywać dziennik działań."

    Example:
        ```python
        AuthPolicy(
            roles={"data_admin": role_definition},
            default_roles=("data_viewer",),
            audit=AuditPolicy("build/audit/audit-log.json", 1000, True)
        )
        ```

    Effect for end user:
        Administrator w Studio Danych widzi gotowy zestaw ról i pewność, że
        wszystkie decyzje trafiają do audytu.
    """

    roles: Dict[str, RoleDefinition]
    default_roles: Sequence[str]
    audit: AuditPolicy


def _default_metadata_storage() -> MetadataStorage:
    return MetadataStorage(
        registry="./data/metadata/registry",
        exports="./data/metadata/exports",
    )


def _default_metadata_policy() -> MetadataPolicy:
    return MetadataPolicy(
        default_license="CC BY 4.0",
        default_publisher="Open Data Publisher",
        default_contact_name="Open Data Team",
        default_contact_email="opendata@example.gov",
        default_accrual_periodicity="P1Y",
        default_spatial="PL",
        default_language="pl",
        keyword_strategy=(),
        theme_taxonomy=(),
        auto_publish_jsonld=True,
        default_temporal_start=None,
        default_temporal_end=None,
    )


def _default_visualization_advanced_settings() -> VisualizationAdvancedSettings:
    return VisualizationAdvancedSettings(
        enable_advanced=True,
        map_region_field="region",
        heatmap_palette=("#08306B", "#2171B5", "#6BAED6", "#C6DBEF", "#F7FBFF"),
        choropleth_palette=("#1D70B8", "#3B8AC4", "#6BB1D8", "#98CBE4"),
        kpi_metrics=("sum", "avg", "min", "max", "median"),
        dashboard_layout=("metric", "chart", "notes"),
    )


def _default_visualization_settings() -> VisualizationSettings:
    return VisualizationSettings(
        output_dir="build/visualizations",
        default_formats=("png", "pdf"),
        default_chart_types=("line", "bar", "area"),
        figure_size=(10, 6),
        dpi=150,
        color_palette=("#0A6FB4", "#59B4D1", "#8DD3E1", "#BEE4EE"),
        background_color="#FFFFFF",
        max_series=4,
        title_prefix="Wizualizacja",
        advanced=_default_visualization_advanced_settings(),
    )


def _default_report_settings() -> ReportSettings:
    return ReportSettings(
        output_dir="build/reports",
        formats=("html", "pdf"),
        template=ReportTemplateSettings(
            html="templates/report.html",
            title_prefix="Raport danych",
            include_styles=True,
        ),
        include_visualization_summary=True,
        attach_jsonld=True,
        include_audit_trail=True,
        authoring=ReportAuthoringSettings(
            prepared_by="Open Data Team",
            contact_email="reports@example.gov",
        ),
    )


def _parse_role_definition(name: str, data: Dict[str, Any]) -> RoleDefinition:
    """
    Technical description:
        Buduje `RoleDefinition` na podstawie słownika z konfiguracji `auth`. W
        razie braku pól stosuje bezpieczne wartości domyślne.

    Instructions for laika:
        "Konwertujemy wpis z tabelki na uporządkowany obiekt opisujący rolę."

    Example:
        ```python
        _parse_role_definition("data_admin", {"permissions": ["datasets.publish"]})
        ```

    Effect for end user:
        Zapewnia, że kreator ról w Studio Danych otrzyma kompletny opis roli.
    """

    permissions = tuple(str(p) for p in data.get("permissions", []))
    attribute_rules = tuple(
        dict(rule)
        for rule in data.get("attribute_rules", [])
        if isinstance(rule, dict)
    )
    inherits = tuple(str(r) for r in data.get("inherits", []))
    return RoleDefinition(
        name=name,
        permissions=permissions,
        description=str(data.get("description", name)),
        attribute_rules=attribute_rules,
        inherits=inherits,
    )


def _parse_auth_policy(payload: Dict[str, Any]) -> Optional[AuthPolicy]:
    """
    Technical description:
        Konwertuje słownik `auth` na `AuthPolicy`. Jeśli konfiguracja nie
        zawiera sekcji `auth`, zwraca `None`.

    Instructions for laika:
        "Sprawdzamy, czy w profilu są ustawienia bezpieczeństwa. Jeśli tak –
        tworzymy obiekt z rolami i polityką audytu."

    Example:
        ```python
        _parse_auth_policy({"roles": {"viewer": {"permissions": ["datasets.view"]}}})
        ```

    Effect for end user:
        Ułatwia synchronizację konfiguracji bezpieczeństwa z modułem
        AuthorizationService.
    """

    if not payload:
        return None

    roles_section = payload.get("roles") or {}
    roles: Dict[str, RoleDefinition] = {}
    for role_name, role_data in roles_section.items():
        if isinstance(role_data, dict):
            roles[role_name] = _parse_role_definition(role_name, role_data)

    audit_dict = payload.get("audit") or {}
    audit_policy = AuditPolicy(
        storage_path=str(audit_dict.get("storage_path", "build/audit/audit-log.json")),
        retention=int(audit_dict.get("retention", 1000)),
        notify_on_deny=bool(audit_dict.get("notify_on_deny", True)),
    )

    default_roles = tuple(str(role) for role in payload.get("default_roles", []))
    return AuthPolicy(roles=roles, default_roles=default_roles, audit=audit_policy)


def _parse_admin_settings(payload: Dict[str, Any]) -> Optional[AdminSettings]:
    """
    Technical description:
        Konwertuje sekcję `admin` profilu na obiekt `AdminSettings`. Obsługuje
        brakujące pola, stosując wartości domyślne zgodne z wymaganiami etapu 12.

    Instructions for laika:
        "Sprawdzamy, czy w konfiguracji są ustawienia panelu. Jeśli tak –
        zamieniamy je na uporządkowany obiekt, z którego skorzysta Studio
        Danych i integracja WordPress."

    Example:
        ```python
        _parse_admin_settings({"studio": {"default_profile": "dev"}})
        ```

    Effect for end user:
        Panel administracyjny korzysta z pełnej, zweryfikowanej konfiguracji,
        co ogranicza ryzyko błędów w czasie wdrożenia.
    """

    if not payload:
        return None

    studio_payload = payload.get("studio") or {}
    wordpress_payload = payload.get("wordpress") or {}
    feature_flags = {
        str(key): bool(value)
        for key, value in (studio_payload.get("feature_flags") or {}).items()
    }
    branding = dict(studio_payload.get("branding", {}))
    if "support_email" not in branding:
        branding["support_email"] = "support@example.gov"
    menu_entries: List[Dict[str, Any]] = []
    for item in studio_payload.get("menu", []):
        if isinstance(item, dict):
            menu_entries.append(dict(item))

    studio = AdminStudioSection(
        default_profile=str(studio_payload.get("default_profile", "dev")),
        allowed_profiles=tuple(str(p) for p in studio_payload.get("allowed_profiles", ["dev"])),
        feature_flags=feature_flags or {"ingestion": True, "transformation": True, "metadata": True, "wordpress": True, "quality": False},
        branding=branding,
        menu=tuple(menu_entries),
    )

    installer_payload = wordpress_payload.get("installer") or {}
    wordpress = AdminWordPressSection(
        enabled=bool(wordpress_payload.get("enabled", True)),
        auto_sync_interval=str(wordpress_payload.get("auto_sync_interval", "PT12H")),
        installer={
            "bundle_directory": str(installer_payload.get("bundle_directory", "build/installers")),
            "package_name": str(installer_payload.get("package_name", "open-data-plugin.zip")),
        },
    )

    return AdminSettings(studio=studio, wordpress=wordpress)


@dataclass(frozen=True)
class ConfigProfile:
    """
    Technical description:
        Łączy ścieżki przechowywania, reguły ingestu CSV, XLSX i JSON/API oraz
        identyfikator profilu zatwierdzony w `config-service`. Pole `strict_schema`
        wymusza zgodność kolumn z rejestrem schematów, a `description` opisuje
        kontekst użycia profilu. Profil zawiera także polityki synchronizacji URL
        (etap 7), integracji bazodanowej (etap 8), pipeline'u transformacji danych
        (etap 9), warstwy metadanych (etap 10), systemu uprawnień i audytu (etap 11),
        ustawienia panelu Studio Danych/WordPress (etap 12), modułu wizualizacji
        podstawowych i zaawansowanych (etapy 13–14) oraz generatora raportów (etap 15).

    Instructions for laika:
        "To komplet ustawień nazwany np. 'produkcja' lub 'test'. Wystarczy wskazać
        profil przy imporcie, a system sam dobierze właściwe katalogi i zasady
        walidacji dla CSV, plików Excel oraz źródeł JSON/API."

    Example:
        ```python
        profile = ConfigProfile(
            name="prod",
            storage=paths,
            policy=policy,
            xlsx_policy=xlsx_policy,
            json_policy=json_policy,
            strict_schema=True,
            description="Profil produkcyjny",
        )
        ```
    Effect for end user:
        Administrator wybiera profil z listy i ma pewność, że import trzyma się
        ustalonych standardów oraz spełnia wymagania bezpieczeństwa i audytu.
    """

    name: str
    storage: StoragePaths
    policy: IngestionPolicy
    xlsx_policy: XLSXPolicy
    json_policy: JsonPolicy
    remote_policy: RemotePolicy
    strict_schema: bool
    description: str
    database_policy: Optional[DatabasePolicy] = None
    database_connections: Dict[str, DatabaseConnection] = field(default_factory=dict)
    transformation_policy: Optional[TransformationPolicy] = None
    transformation_steps: Sequence[TransformationStepConfig] = field(default_factory=list)
    visualization_settings: VisualizationSettings = field(default_factory=_default_visualization_settings)
    metadata_storage: MetadataStorage = field(default_factory=_default_metadata_storage)
    metadata_policy: MetadataPolicy = field(default_factory=_default_metadata_policy)
    report_settings: ReportSettings = field(default_factory=_default_report_settings)
    auth_policy: Optional[AuthPolicy] = None
    admin_settings: Optional[AdminSettings] = None


def profile_from_dict(payload: Dict[str, object]) -> ConfigProfile:
    """
    Technical description:
        Tworzy obiekt ConfigProfile na podstawie danych zwróconych przez
        `config-service`. Funkcja waliduje obecność wymaganych pól, konwertuje
        struktury słownikowe na dataclasses i zapewnia domyślne wartości zgodne
        z kontraktami API etapu 3A. Obsługuje także konfigurację importu XLSX,
        polityki źródeł JSON/API wymagane w etapie 6, polityki synchronizacji
        zdalnych URL (Etap 7), integrację bazodanową (Etap 8), pipeline
        transformacji danych (Etap 9), warstwę metadanych (Etap 10), ustawienia
        systemu uprawnień i audytu (Etap 11), konfigurację panelu
        administracyjnego/WordPress (Etap 12), parametry modułu wizualizacji
        (Etapy 13–14) oraz generatora raportów (Etap 15).

    Instructions for laika:
        "Otrzymujemy słownik z ustawieniami (np. z API). Ta funkcja zamienia go na
        poręczny obiekt, którego można używać w kodzie – tak jakbyś przepisał
        dane z tabelki do uporządkowanego formularza."

    Example:
        ```python
        profile = profile_from_dict({
            "name": "dev",
            "storage": {"landing": "./landing", "schema_registry": "./schemas", "preview": "./preview"},
            "policy": {
                "allowed_separators": [",", ";"],
                "default_encoding": "utf-8",
                "max_file_size_mb": 100,
                "sample_size": 500,
                "timezone": "Europe/Warsaw"
            },
            "xlsx_policy": {
                "allowed_extensions": [".xlsx"],
                "max_file_size_mb": 50,
                "sample_size": 200,
                "preferred_sheets": ["Dane"],
                "header_row_index": 1
            },
            "json_policy": {
                "allowed_http_methods": ["GET"],
                "allowed_content_types": ["application/json"],
                "max_payload_mb": 15,
                "max_records": 1000,
                "default_pointer": "/results",
                "http_timeout": 20,
                "preview_size": 20
            },
            "strict_schema": False,
            "description": "Profil developerski"
        })
        ```
    Effect for end user:
        Dzięki tej funkcji kreator konfiguracji w Studio Danych może szybko sprawdzić
        i zastosować ustawienia profilu bez dodatkowego kodowania, co przyspiesza
        publikację danych w zgodzie ze standardami państwowymi.
    """

    storage_dict = payload.get("storage") or {}
    policy_dict = payload.get("policy") or {}
    xlsx_dict = payload.get("xlsx_policy") or {}
    json_dict = payload.get("json_policy") or {}
    remote_dict = payload.get("remote_policy") or {}
    database_dict = payload.get("database") or {}
    transformation_dict = payload.get("transformation") or {}
    metadata_dict = payload.get("metadata") or {}
    auth_dict = payload.get("auth") or {}
    admin_dict = payload.get("admin") or {}

    storage = StoragePaths(
        landing=str(storage_dict.get("landing", "./data/landing")),
        schema_registry=str(storage_dict.get("schema_registry", "./data/schemas")),
        preview=str(storage_dict.get("preview", "./data/preview")),
    )
    policy = IngestionPolicy(
        allowed_separators=tuple(policy_dict.get("allowed_separators", [",", ";", "|", "\t"])),
        default_encoding=str(policy_dict.get("default_encoding", "utf-8")),
        max_file_size_mb=int(policy_dict.get("max_file_size_mb", 100)),
        sample_size=int(policy_dict.get("sample_size", 500)),
        timezone=str(policy_dict.get("timezone", "Europe/Warsaw")),
    )
    xlsx_policy = XLSXPolicy(
        allowed_extensions=tuple(xlsx_dict.get("allowed_extensions", [".xlsx", ".xlsm"])),
        max_file_size_mb=int(xlsx_dict.get("max_file_size_mb", policy.max_file_size_mb)),
        sample_size=int(xlsx_dict.get("sample_size", policy.sample_size)),
        preferred_sheets=tuple(xlsx_dict.get("preferred_sheets", [])),
        header_row_index=int(xlsx_dict.get("header_row_index", 1)),
    )
    json_policy = JsonPolicy(
        allowed_http_methods=tuple(json_dict.get("allowed_http_methods", ["GET"])),
        allowed_content_types=tuple(json_dict.get("allowed_content_types", ["application/json", "application/vnd.api+json"])),
        max_payload_mb=int(json_dict.get("max_payload_mb", 15)),
        max_records=int(json_dict.get("max_records", 1000)),
        default_pointer=str(json_dict.get("default_pointer", "/results")),
        http_timeout=int(json_dict.get("http_timeout", 15)),
        preview_size=int(json_dict.get("preview_size", 25)),
    )
    remote_policy = RemotePolicy(
        allowed_schemes=tuple(remote_dict.get("allowed_schemes", ["https", "http"])),
        allowed_content_types=tuple(
            remote_dict.get(
                "allowed_content_types",
                [
                    "text/csv",
                    "application/json",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                ],
            )
        ),
        max_file_size_mb=int(remote_dict.get("max_file_size_mb", 100)),
        download_cache=str(remote_dict.get("download_cache", "./data/cache")),
        state_registry=str(remote_dict.get("state_registry", "./data/state")),
        default_schedule=str(remote_dict.get("default_schedule", "PT24H")),
        verify_tls=bool(remote_dict.get("verify_tls", True)),
        retry_attempts=int(remote_dict.get("retry_attempts", 3)),
        retry_backoff_seconds=int(remote_dict.get("retry_backoff_seconds", 30)),
    )

    database_policy_payload = database_dict.get("policy") or {}
    database_policy = None
    if database_policy_payload:
        database_policy = DatabasePolicy(
            allowed_drivers=tuple(
                database_policy_payload.get(
                    "allowed_drivers",
                    ["postgresql", "mysql", "mssql", "sqlite"],
                )
            ),
            max_rows=int(database_policy_payload.get("max_rows", 10000)),
            default_limit=int(database_policy_payload.get("default_limit", 1000)),
            metadata_cache=str(
                database_policy_payload.get("metadata_cache", "./data/db-metadata")
            ),
            timezone=str(database_policy_payload.get("timezone", policy.timezone)),
        )

    connections_payload = database_dict.get("connections") or {}
    database_connections: Dict[str, DatabaseConnection] = {}
    for connection_id, data in connections_payload.items():
        url = data.get("url")
        if not url:
            continue
        driver = str(data.get("driver") or str(url).split(":")[0])
        database_connections[connection_id] = DatabaseConnection(
            connection_id=connection_id,
            url=str(url),
            driver=driver,
            default_schema=data.get("default_schema"),
            description=str(data.get("description", connection_id)),
            options=dict(data.get("options", {})),
        )

    transformation_policy_payload = transformation_dict.get("policy") or {}
    transformation_policy = None
    if transformation_policy_payload:
        transformation_policy = TransformationPolicy(
            enabled=bool(transformation_policy_payload.get("enabled", True)),
            max_rows=int(transformation_policy_payload.get("max_rows", 5000)),
            rounding_precision=int(transformation_policy_payload.get("rounding_precision", 2)),
            allowed_operations=tuple(
                transformation_policy_payload.get(
                    "allowed_operations",
                    [
                        "normalize_headers",
                        "rename_columns",
                        "filter_rows",
                        "derive_column",
                        "aggregate",
                    ],
                )
            ),
        )

    steps_payload: List[Dict[str, Any]] = []
    if isinstance(transformation_dict.get("steps"), list):
        steps_payload = list(transformation_dict.get("steps", []))
    elif isinstance(transformation_dict.get("default_pipeline"), list):
        steps_payload = list(transformation_dict.get("default_pipeline", []))

    transformation_steps: List[TransformationStepConfig] = []
    for step_data in steps_payload:
        operation = step_data.get("operation")
        if not operation:
            continue
        transformation_steps.append(
            TransformationStepConfig(
                operation=str(operation),
                parameters=dict(step_data.get("parameters", {})),
            )
        )

    visualization_dict = payload.get("visualization") or {}
    figure_size_payload = visualization_dict.get("figure_size", [10, 6])
    figure_size_values: List[float] = []
    for value in figure_size_payload[:2]:
        try:
            figure_size_values.append(float(value))
        except (TypeError, ValueError):
            continue
    if len(figure_size_values) != 2:
        figure_size = (10.0, 6.0)
    else:
        figure_size = tuple(figure_size_values)
    advanced_dict = visualization_dict.get("advanced") or {}
    visualization_advanced = VisualizationAdvancedSettings(
        enable_advanced=bool(advanced_dict.get("enable_advanced", True)),
        map_region_field=str(advanced_dict.get("map_region_field", "region")),
        heatmap_palette=tuple(
            advanced_dict.get(
                "heatmap_palette",
                ["#08306B", "#2171B5", "#6BAED6", "#C6DBEF", "#F7FBFF"],
            )
        ),
        choropleth_palette=tuple(
            advanced_dict.get(
                "choropleth_palette",
                ["#1D70B8", "#3B8AC4", "#6BB1D8", "#98CBE4"],
            )
        ),
        kpi_metrics=tuple(
            advanced_dict.get(
                "kpi_metrics",
                ["sum", "avg", "min", "max", "median"],
            )
        ),
        dashboard_layout=tuple(
            advanced_dict.get("dashboard_layout", ["metric", "chart", "notes"])
        ),
    )

    visualization_settings = VisualizationSettings(
        output_dir=str(visualization_dict.get("output_dir", "build/visualizations")),
        default_formats=tuple(visualization_dict.get("default_formats", ["png", "pdf"])),
        default_chart_types=tuple(
            visualization_dict.get("default_chart_types", ["line", "bar", "area"])
        ),
        figure_size=figure_size,
        dpi=int(visualization_dict.get("dpi", 150)),
        color_palette=tuple(
            visualization_dict.get(
                "color_palette",
                ["#0A6FB4", "#59B4D1", "#8DD3E1", "#BEE4EE"],
            )
        ),
        background_color=str(visualization_dict.get("background_color", "#FFFFFF")),
        max_series=int(visualization_dict.get("max_series", 4)),
        title_prefix=str(visualization_dict.get("title_prefix", "Wizualizacja")),
        advanced=visualization_advanced,
    )

    metadata_storage_dict = metadata_dict.get("storage") or {}
    metadata_policy_dict = metadata_dict.get("policy") or {}
    contact_dict = metadata_policy_dict.get("default_contact") or {}
    metadata_storage = MetadataStorage(
        registry=str(metadata_storage_dict.get("registry", "./data/metadata/registry")),
        exports=str(metadata_storage_dict.get("exports", "./data/metadata/exports")),
    )
    metadata_policy = MetadataPolicy(
        default_license=str(metadata_policy_dict.get("default_license", "CC BY 4.0")),
        default_publisher=str(metadata_policy_dict.get("default_publisher", "Open Data Publisher")),
        default_contact_name=str(contact_dict.get("name", "Open Data Team")),
        default_contact_email=str(contact_dict.get("email", "opendata@example.gov")),
        default_accrual_periodicity=str(
            metadata_policy_dict.get("default_accrual_periodicity", "P1Y")
        ),
        default_spatial=str(metadata_policy_dict.get("default_spatial", "PL")),
        default_language=str(metadata_policy_dict.get("default_language", "pl")),
        keyword_strategy=tuple(metadata_policy_dict.get("keyword_strategy", [])),
        theme_taxonomy=tuple(metadata_policy_dict.get("theme_taxonomy", [])),
        auto_publish_jsonld=bool(metadata_policy_dict.get("auto_publish_jsonld", True)),
        default_temporal_start=metadata_policy_dict.get("default_temporal_start"),
        default_temporal_end=metadata_policy_dict.get("default_temporal_end"),
    )

    reports_dict = payload.get("reports") or {}
    template_dict = reports_dict.get("template") or {}
    authoring_dict = reports_dict.get("authoring") or {}
    report_settings = ReportSettings(
        output_dir=str(reports_dict.get("output_dir", "build/reports")),
        formats=tuple(reports_dict.get("formats", ["html", "pdf"])),
        template=ReportTemplateSettings(
            html=str(template_dict.get("html", "templates/report.html")),
            title_prefix=str(template_dict.get("title_prefix", "Raport danych")),
            include_styles=bool(template_dict.get("include_styles", True)),
        ),
        include_visualization_summary=bool(reports_dict.get("include_visualization_summary", True)),
        attach_jsonld=bool(reports_dict.get("attach_jsonld", True)),
        include_audit_trail=bool(reports_dict.get("include_audit_trail", True)),
        authoring=ReportAuthoringSettings(
            prepared_by=str(authoring_dict.get("prepared_by", "Open Data Team")),
            contact_email=str(authoring_dict.get("contact_email", "reports@example.gov")),
        ),
    )

    auth_policy = _parse_auth_policy(auth_dict)
    admin_settings = _parse_admin_settings(admin_dict)

    return ConfigProfile(
        name=str(payload.get("name", "default")),
        storage=storage,
        policy=policy,
        xlsx_policy=xlsx_policy,
        json_policy=json_policy,
        remote_policy=remote_policy,
        strict_schema=bool(payload.get("strict_schema", False)),
        description=str(payload.get("description", "Profil wygenerowany automatycznie.")),
        database_policy=database_policy,
        database_connections=database_connections,
        transformation_policy=transformation_policy,
        transformation_steps=transformation_steps,
        visualization_settings=visualization_settings,
        metadata_storage=metadata_storage,
        metadata_policy=metadata_policy,
        report_settings=report_settings,
        auth_policy=auth_policy,
        admin_settings=admin_settings,
    )
