"""
Module: ingestion_service.__init__
Opis: Udostępnia wysokopoziomowe API modułu ingestion-service dla etapów 4–9.
Funkcje i klasy:
- class CSVIngestor: główny silnik importu CSV korzystający z profili konfiguracji.
- class XLSXIngestor: silnik importu XLSX z autodetekcją arkuszy.
- class JSONIngestor: silnik importu źródeł JSON/API z obsługą HTTP i JSON Pointer.
- class DatabaseIngestor: silnik integracji bazodanowej (PostgreSQL/MySQL/MS SQL).
- class RemoteSyncManager: koordynuje harmonogram synchronizacji zdalnych URL.
- class RemoteSourceConfig: opisuje zdalne źródło danych wraz z harmonogramem.
- class TransformationPipeline: realizuje pipeline ETL (Etap 9).
- function settings_from_profile: buduje ustawienia transformacji na bazie profilu.
- function build_default_csv_ingestor: tworzy skonfigurowany obiekt CSVIngestor dla CLI/testów.
- function build_default_xlsx_ingestor: tworzy skonfigurowany obiekt XLSXIngestor dla CLI/testów.
- function build_default_json_ingestor: tworzy skonfigurowany JSONIngestor dla CLI/testów.
- function build_default_database_ingestor: tworzy skonfigurowany DatabaseIngestor dla CLI/testów.

Ten moduł inicjuje obszar importu CSV, XLSX, JSON/API, integracji bazodanowej i synchronizacji URL zgodny z wymaganiami dane.gov.pl oraz API BDL.
"""

from .csv_ingestor import CSVIngestor, build_default_csv_ingestor
from .database_ingestor import DatabaseIngestor, build_default_database_ingestor
from .json_ingestor import JSONIngestor, build_default_json_ingestor
from .remote_sync import RemoteSourceConfig, RemoteSyncManager
from .transformation import (
    TransformationPipeline,
    settings_from_profile,
)
from .xlsx_ingestor import XLSXIngestor, build_default_xlsx_ingestor

__all__ = [
    "CSVIngestor",
    "build_default_csv_ingestor",
    "XLSXIngestor",
    "build_default_xlsx_ingestor",
    "JSONIngestor",
    "build_default_json_ingestor",
    "DatabaseIngestor",
    "build_default_database_ingestor",
    "RemoteSourceConfig",
    "RemoteSyncManager",
    "TransformationPipeline",
    "settings_from_profile",
]
