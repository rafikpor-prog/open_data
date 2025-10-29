"""
Module: metadata_service.models
Opis: Definiuje modele danych wykorzystywane przez rejestr metadanych (Etap 10).
Funkcje i klasy:
- class ContactPoint: dane osoby/zespołu odpowiedzialnego za zbiór.
- class DatasetRecord: pełny rekord DCAT-AP wraz z dodatkowymi metadanymi
  (profil konfiguracji, ścieżki eksportów, pola rozszerzeń).
- function to_metadata_payload: konwertuje rekord na `DatasetMetadata`
  wykorzystywany przez kontrakty API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from ingestion_service.contracts import (
    DatasetMetadata,
    DatasetReference,
    MetadataDistribution,
    MetadataField,
)


@dataclass(frozen=True)
class ContactPoint:
    """
    Technical description:
        Przechowuje informacje kontaktowe dla zbioru danych zgodnie z DCAT-AP.
        Wymagane pola to nazwa (`name`) oraz adres e-mail (`email`).

    Instructions for laika:
        "To wizytówka osoby lub zespołu opiekującego się zbiorem danych –
        dzięki niej użytkownicy wiedzą, z kim się skontaktować." 

    Example:
        ```python
        contact = ContactPoint(name="Zespół Open Data", email="opendata@example.gov")
        ```
    Effect for end user:
        Portal danych i WordPress wyświetlają jasną informację, gdzie zgłosić
        pytania dotyczące zbioru.
    """

    name: str
    email: str


@dataclass(frozen=True)
class DatasetRecord:
    """
    Technical description:
        Reprezentuje kompletny rekord katalogu DCAT-AP. Oprócz standardowych
        pól (tytuł, opis, licencja, słowa kluczowe, dystrybucje) przechowuje
        informacje o profilu konfiguracji, ścieżkach eksportów oraz dodatkowe
        atrybuty (`extras`) używane przez WordPress lub `metadata_service`.

    Instructions for laika:
        "To pełen opis zbioru danych. Zawiera wszystko, co widzisz w katalogu –
        nazwę, opis, licencję, linki do plików i dane kontaktowe." 

    Example:
        ```python
        record = DatasetRecord(
            dataset=DatasetReference(dataset_id="population"),
            title="Populacja województw",
            description="Zestawienie liczby mieszkańców",
            license="CC BY 4.0",
            keywords=["demografia", "populacja"],
            themes=["DEMOGRAFIA"],
            contact=ContactPoint(name="Zespół Open Data", email="opendata@example.gov"),
            accrual_periodicity="P1M",
            spatial="PL",
            language="pl",
            fields=[],
            distributions=[],
            issued=datetime.utcnow(),
            modified=datetime.utcnow(),
            profile_name="dev",
            jsonld_path=None,
        )
        ```
    Effect for end user:
        Zapewnia spójne dane do publikacji w portalu, API oraz wtyczce WordPress
        bez potrzeby ręcznej edycji metadanych.
    """

    dataset: DatasetReference
    title: str
    description: str
    license: str
    keywords: List[str]
    themes: List[str]
    contact: ContactPoint
    accrual_periodicity: str
    spatial: Optional[str]
    language: Optional[str]
    fields: List[MetadataField]
    distributions: List[MetadataDistribution]
    issued: datetime
    modified: datetime
    profile_name: str
    jsonld_path: Optional[str] = None
    extras: Dict[str, Any] = field(default_factory=dict)

    def to_metadata_payload(self) -> DatasetMetadata:
        """
        Technical description:
            Konwertuje rekord na `DatasetMetadata` wykorzystywany przez API
            `metadata-service` i mostek WordPress.

        Instructions for laika:
            "Zamienia dane rekordu na format katalogu, który można wysłać do
            API lub zapisać w pliku JSON-LD." 

        Example:
            ```python
            payload = record.to_metadata_payload()
            ```
        Effect for end user:
            Zapewnia, że każda usługa (API, WordPress) otrzymuje identyczny opis
            zbioru danych bez ręcznego przepisywania pól.
        """

        return DatasetMetadata(
            dataset=self.dataset,
            title=self.title,
            description=self.description,
            license=self.license,
            keywords=list(self.keywords),
            themes=list(self.themes),
            contact_name=self.contact.name,
            contact_email=self.contact.email,
            accrual_periodicity=self.accrual_periodicity,
            spatial=self.spatial,
            language=self.language,
            fields=list(self.fields),
            distributions=list(self.distributions),
            issued=self.issued,
            modified=self.modified,
        )


def to_metadata_payload(record: DatasetRecord) -> DatasetMetadata:
    """
    Technical description:
        Pomocnicza funkcja konwertująca `DatasetRecord` na `DatasetMetadata`.
        Ułatwia serializację w rejestrze metadanych i testach jednostkowych.

    Instructions for laika:
        "Wywołaj tę funkcję, aby otrzymać gotowy opis zbioru do publikacji
        w API lub w pliku katalogu." 

    Example:
        ```python
        payload = to_metadata_payload(record)
        ```
    Effect for end user:
        Zmniejsza ryzyko niespójności między katalogiem DCAT-AP a WordPressem –
        wszystkie komponenty korzystają z jednego formatu danych.
    """

    return record.to_metadata_payload()
