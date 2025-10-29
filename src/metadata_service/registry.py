"""
Module: metadata_service.registry
Opis: Implementuje rejestr metadanych DCAT-AP (Etap 10) oraz narzędzia
pozwalające tworzyć rekordy na podstawie raportów transformacji.
Funkcje i klasy:
- class MetadataRegistry: zapis/odczyt rekordów, eksport JSON-LD/JSON:API.
- function record_from_transformation: buduje `DatasetRecord` na bazie raportu
  transformacji i polityki profilu.
- function registry_from_profile: tworzy rejestr wykorzystując `ConfigProfile`
  (`metadata_storage`, `metadata_policy`).
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from ingestion_service.contracts import DatasetReference, TransformationReport
from ingestion_service.profile import MetadataPolicy

from .models import ContactPoint, DatasetRecord, MetadataDistribution, MetadataField, to_metadata_payload


class MetadataRegistry:
    """
    Technical description:
        Zarządza rejestrem metadanych DCAT-AP. Przechowuje rekordy w katalogu
        `registry_root`, generuje eksporty JSON-LD w `exports_root`, publikuje
        widok JSON:API oraz umożliwia aktualizację na podstawie raportów
        transformacji.

    Instructions for laika:
        "To centralny katalog opisów zbiorów. Zapamiętuje licencję, słowa
        kluczowe i linki do plików, a także automatycznie tworzy pliki do
        publikacji na portalu i w WordPressie." 

    Example:
        ```python
        registry = MetadataRegistry(Path("build/metadata/registry"), Path("build/metadata/exports"), policy)
        record = registry.register_transformation(report)
        ```
    Effect for end user:
        Administrator otrzymuje zawsze aktualny katalog zgodny z DCAT-AP,
        gotowy do udostępnienia w portalu dane.gov.pl oraz w wtyczce WordPress.
    """

    def __init__(self, registry_root: Path, exports_root: Path, policy: MetadataPolicy) -> None:
        self._registry_root = Path(registry_root)
        self._exports_root = Path(exports_root)
        self._policy = policy
        self._registry_root.mkdir(parents=True, exist_ok=True)
        self._exports_root.mkdir(parents=True, exist_ok=True)

    def upsert(self, record: DatasetRecord) -> DatasetRecord:
        """
        Technical description:
            Zapisuje rekord w katalogu i – jeśli polityka na to pozwala –
            publikuje plik JSON-LD. Aktualizuje również indeks `catalog.json`.

        Instructions for laika:
            "Zapisujemy opis zbioru na dysku. Jeżeli włączone jest automatyczne
            publikowanie, powstaje też plik JSON-LD gotowy do udostępnienia." 

        Example:
            ```python
            record = registry.upsert(record)
            ```
        Effect for end user:
            Katalog danych i WordPress natychmiast widzą najnowsze informacje o
            zbiorze.
        """

        path = self._registry_root / f"{record.dataset.dataset_id}.json"
        jsonld_path: Optional[str] = record.jsonld_path
        if self._policy.auto_publish_jsonld:
            jsonld_path = str(self.publish_jsonld(record))
        stored_record = replace(record, jsonld_path=jsonld_path)
        path.write_text(
            json.dumps(self._record_to_dict(stored_record), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._write_catalog_index()
        return stored_record

    def load(self, dataset_id: str) -> Optional[DatasetRecord]:
        """
        Technical description:
            Wczytuje rekord metadanych z katalogu. Zwraca `None`, jeśli plik nie
            istnieje lub jest uszkodzony.

        Instructions for laika:
            "Sprawdzamy, czy katalog zawiera opis konkretnego zbioru i zwracamy
            go jako obiekt Python." 

        Example:
            ```python
            record = registry.load("population")
            ```
        Effect for end user:
            Ułatwia ręczną edycję i audyt – administrator może obejrzeć opis
            zbioru bezpośrednio z plików katalogu.
        """

        path = self._registry_root / f"{dataset_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return self._record_from_dict(data)

    def list_records(self) -> List[DatasetRecord]:
        """
        Technical description:
            Zwraca posortowaną listę wszystkich rekordów katalogu.

        Instructions for laika:
            "Daje podgląd całego katalogu – lista zawiera każdy zbiór zapisany
            w systemie." 

        Example:
            ```python
            records = registry.list_records()
            ```
        Effect for end user:
            Pozwala szybko zweryfikować, które zbiory zostały już opisane i
            udostępnione.
        """

        records: List[DatasetRecord] = []
        for path in sorted(self._registry_root.glob("*.json")):
            loaded = self._record_from_dict(json.loads(path.read_text(encoding="utf-8")))
            if loaded:
                records.append(loaded)
        return records

    def publish_jsonld(self, record: DatasetRecord) -> Path:
        """
        Technical description:
            Tworzy plik JSON-LD (`dataset_id.jsonld`) zgodny z DCAT-AP.

        Instructions for laika:
            "Generujemy plik katalogu w formacie wymaganym przez dane.gov.pl –
            można go od razu opublikować." 

        Example:
            ```python
            jsonld_path = registry.publish_jsonld(record)
            ```
        Effect for end user:
            Zapewnia gotowy plik do publikacji na portalu i w WordPressie.
        """

        payload = self._build_jsonld(record)
        path = self._exports_root / f"{record.dataset.dataset_id}.jsonld"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def to_jsonapi(self, record: DatasetRecord) -> Dict[str, Any]:
        """
        Technical description:
            Serializuje rekord do formatu JSON:API (`type`: `datasets`).

        Instructions for laika:
            "Zamieniamy rekord na strukturę, którą można zwrócić w API REST
            lub GraphQL." 

        Example:
            ```python
            payload = registry.to_jsonapi(record)
            ```
        Effect for end user:
            Integracje (np. WordPress) mogą łatwo pobierać katalog danych.
        """

        metadata = to_metadata_payload(record)
        return {
            "data": {
                "type": "datasets",
                "id": record.dataset.dataset_id,
                "attributes": {
                    "title": record.title,
                    "description": record.description,
                    "license": record.license,
                    "keywords": record.keywords,
                    "themes": record.themes,
                    "contact": {
                        "name": record.contact.name,
                        "email": record.contact.email,
                    },
                    "accrual_periodicity": record.accrual_periodicity,
                    "spatial": record.spatial,
                    "language": record.language,
                    "issued": metadata.issued.isoformat(),
                    "modified": metadata.modified.isoformat(),
                    "fields": [
                        {
                            "name": field.name,
                            "data_type": field.data_type,
                            "required": field.required,
                            "unit": field.unit,
                            "example": field.example,
                        }
                        for field in metadata.fields
                    ],
                    "distributions": [
                        {
                            "identifier": dist.identifier,
                            "access_url": dist.access_url,
                            "format": dist.format,
                            "updated_at": dist.updated_at.isoformat(),
                        }
                        for dist in metadata.distributions
                    ],
                    "profile_name": record.profile_name,
                    "jsonld_path": record.jsonld_path,
                    "extras": record.extras,
                },
            }
        }

    def register_transformation(
        self,
        report: TransformationReport,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> DatasetRecord:
        """
        Technical description:
            Buduje rekord metadanych na podstawie raportu transformacji oraz
            polityki profilu, następnie zapisuje go w katalogu.

        Instructions for laika:
            "Po zakończeniu przetwarzania danych wywołujemy tę metodę, aby
            katalog automatycznie uzupełnił opis zbioru." 

        Example:
            ```python
            record = registry.register_transformation(report, {"title": "Populacja"})
            ```
        Effect for end user:
            Zbiory danych trafiają do katalogu bez ręcznej edycji metadanych,
            a WordPress natychmiast widzi aktualny opis.
        """

        record = record_from_transformation(report, self._policy, overrides)
        return self.upsert(record)

    def _write_catalog_index(self) -> None:
        index_path = self._registry_root / "catalog.json"
        entries = [
            {
                "id": record.dataset.dataset_id,
                "title": record.title,
                "modified": record.modified.isoformat(),
            }
            for record in self.list_records()
        ]
        index_path.write_text(json.dumps({"datasets": entries}, ensure_ascii=False, indent=2), encoding="utf-8")

    def _record_to_dict(self, record: DatasetRecord) -> Dict[str, Any]:
        metadata = to_metadata_payload(record)
        return {
            "dataset": metadata.dataset.dataset_id,
            "resource": metadata.dataset.resource_id,
            "title": metadata.title,
            "description": metadata.description,
            "license": metadata.license,
            "keywords": metadata.keywords,
            "themes": metadata.themes,
            "contact": {
                "name": metadata.contact_name,
                "email": metadata.contact_email,
            },
            "accrual_periodicity": metadata.accrual_periodicity,
            "spatial": metadata.spatial,
            "language": metadata.language,
            "fields": [
                {
                    "name": field.name,
                    "data_type": field.data_type,
                    "required": field.required,
                    "unit": field.unit,
                    "example": field.example,
                }
                for field in metadata.fields
            ],
            "distributions": [
                {
                    "identifier": dist.identifier,
                    "access_url": dist.access_url,
                    "format": dist.format,
                    "updated_at": dist.updated_at.isoformat(),
                }
                for dist in metadata.distributions
            ],
            "issued": metadata.issued.isoformat(),
            "modified": metadata.modified.isoformat(),
            "profile_name": record.profile_name,
            "jsonld_path": record.jsonld_path,
            "extras": record.extras,
        }

    def _record_from_dict(self, data: Dict[str, Any]) -> Optional[DatasetRecord]:
        dataset_id = data.get("dataset")
        if not dataset_id:
            return None
        dataset = DatasetReference(dataset_id=str(dataset_id), resource_id=data.get("resource"))
        fields = [
            MetadataField(
                name=str(field.get("name")),
                data_type=str(field.get("data_type")),
                required=bool(field.get("required", True)),
                unit=field.get("unit"),
                example=field.get("example"),
            )
            for field in data.get("fields", [])
        ]
        distributions = [
            MetadataDistribution(
                identifier=str(dist.get("identifier")),
                access_url=str(dist.get("access_url")),
                format=str(dist.get("format", "application/json")),
                updated_at=datetime.fromisoformat(dist.get("updated_at")),
            )
            for dist in data.get("distributions", [])
        ]
        return DatasetRecord(
            dataset=dataset,
            title=str(data.get("title", dataset.dataset_id)),
            description=str(data.get("description", "")),
            license=str(data.get("license", self._policy.default_license)),
            keywords=[str(keyword) for keyword in data.get("keywords", [])],
            themes=[str(theme) for theme in data.get("themes", [])],
            contact=ContactPoint(
                name=str(data.get("contact", {}).get("name", self._policy.default_contact_name)),
                email=str(data.get("contact", {}).get("email", self._policy.default_contact_email)),
            ),
            accrual_periodicity=str(data.get("accrual_periodicity", self._policy.default_accrual_periodicity)),
            spatial=data.get("spatial"),
            language=data.get("language"),
            fields=fields,
            distributions=distributions,
            issued=datetime.fromisoformat(data.get("issued", datetime.utcnow().isoformat())),
            modified=datetime.fromisoformat(data.get("modified", datetime.utcnow().isoformat())),
            profile_name=str(data.get("profile_name", "default")),
            jsonld_path=data.get("jsonld_path"),
            extras=dict(data.get("extras", {})),
        )

    def _build_jsonld(self, record: DatasetRecord) -> Dict[str, Any]:
        metadata = to_metadata_payload(record)
        return {
            "@context": "https://www.w3.org/ns/dcat.jsonld",
            "@type": "dcat:Dataset",
            "dct:identifier": metadata.dataset.dataset_id,
            "dct:title": metadata.title,
            "dct:description": metadata.description,
            "dct:license": record.license,
            "dct:publisher": self._policy.default_publisher,
            "dct:contactPoint": {
                "fn": record.contact.name,
                "hasEmail": f"mailto:{record.contact.email}",
            },
            "dcat:keyword": metadata.keywords,
            "dcat:theme": metadata.themes,
            "dct:language": metadata.language,
            "dct:spatial": metadata.spatial,
            "dct:accrualPeriodicity": record.accrual_periodicity,
            "dct:issued": metadata.issued.isoformat(),
            "dct:modified": metadata.modified.isoformat(),
            "dcat:distribution": [
                {
                    "@type": "dcat:Distribution",
                    "dct:identifier": dist.identifier,
                    "dct:format": dist.format,
                    "dcat:accessURL": dist.access_url,
                    "dct:modified": dist.updated_at.isoformat(),
                }
                for dist in metadata.distributions
            ],
        }


def record_from_transformation(
    report: TransformationReport,
    policy: MetadataPolicy,
    overrides: Optional[Dict[str, Any]] = None,
) -> DatasetRecord:
    """
    Technical description:
        Tworzy rekord metadanych na bazie raportu transformacji (`TransformationReport`).
        Wykorzystuje domyślne wartości z `MetadataPolicy`, a parametry w `overrides`
        pozwalają nadpisać tytuł, opis, licencję czy słowa kluczowe.

    Instructions for laika:
        "Po zakończeniu przetwarzania wywołaj tę funkcję, aby powstał kompletny
        opis zbioru – system sam wypełni brakujące pola." 

    Example:
        ```python
        record = record_from_transformation(report, policy, {"title": "Populacja"})
        ```
    Effect for end user:
        Pozwala automatycznie publikować katalog danych po każdym imporcie,
        bez ręcznego przepisywania informacji.
    """

    overrides = overrides or {}
    contact = overrides.get("contact", {})
    keyword_overrides: Iterable[str] = overrides.get("keywords", [])
    theme_overrides: Iterable[str] = overrides.get("themes", [])
    unit_overrides: Dict[str, str] = overrides.get("field_units", {})
    distributions: List[MetadataDistribution] = []

    distributions.append(
        MetadataDistribution(
            identifier=f"{report.dataset.dataset_id}-preview",
            access_url=overrides.get("preview_url", report.preview_path),
            format="application/json",
            updated_at=report.finished_at,
        )
    )
    if overrides.get("download_url"):
        distributions.append(
            MetadataDistribution(
                identifier=f"{report.dataset.dataset_id}-download",
                access_url=str(overrides["download_url"]),
                format=str(overrides.get("download_format", "application/zip")),
                updated_at=report.finished_at,
            )
        )

    fields = [
        MetadataField(
            name=column.name,
            data_type=column.data_type,
            required=not column.nullable,
            unit=unit_overrides.get(column.name),
            example=column.example,
        )
        for column in report.columns
    ]

    keywords = list(policy.keyword_strategy)
    keywords.extend(str(keyword) for keyword in keyword_overrides)
    themes = list(policy.theme_taxonomy)
    themes.extend(str(theme) for theme in theme_overrides)

    extras = {
        "visualization_hints": [
            {
                "chart_type": hint.chart_type,
                "confidence": hint.confidence,
                "reason": hint.reason,
            }
            for hint in report.visualization_hints
        ],
        "message": report.message,
    }

    return DatasetRecord(
        dataset=report.dataset,
        title=str(overrides.get("title", report.dataset.dataset_id)),
        description=str(overrides.get("description", "Dataset wygenerowany automatycznie.")),
        license=str(overrides.get("license", policy.default_license)),
        keywords=keywords,
        themes=themes,
        contact=ContactPoint(
            name=str(contact.get("name", policy.default_contact_name)),
            email=str(contact.get("email", policy.default_contact_email)),
        ),
        accrual_periodicity=str(overrides.get("accrual_periodicity", policy.default_accrual_periodicity)),
        spatial=overrides.get("spatial", policy.default_spatial),
        language=overrides.get("language", policy.default_language),
        fields=fields,
        distributions=distributions,
        issued=report.started_at,
        modified=report.finished_at,
        profile_name=str(overrides.get("profile_name", "default")),
        extras=extras,
    )


def registry_from_profile(profile: "ConfigProfile") -> MetadataRegistry:
    """
    Technical description:
        Tworzy `MetadataRegistry` na podstawie profilu konfiguracji (`ConfigProfile`).

    Instructions for laika:
        "Profil przechowuje ustawienia katalogu. Dzięki tej funkcji tworzysz
        rejestr bez ręcznego wpisywania ścieżek i licencji." 

    Example:
        ```python
        registry = registry_from_profile(profile)
        ```
    Effect for end user:
        Integracja z `config-service` pozwala zarządzać katalogiem w trybie
        GitOps i zachować spójność między środowiskami.
    """

    from ingestion_service.profile import ConfigProfile

    if not isinstance(profile, ConfigProfile):  # pragma: no cover - ochrona typu w runtime
        raise TypeError("registry_from_profile expects ConfigProfile instance")

    return MetadataRegistry(
        registry_root=Path(profile.metadata_storage.registry),
        exports_root=Path(profile.metadata_storage.exports),
        policy=profile.metadata_policy,
    )
