"""
Module: metadata_service.__init__
Opis: Udostępnia wysokopoziomowe API warstwy metadanych (Etap 10).
Eksportowane elementy:
- class DatasetRecord, MetadataField, MetadataDistribution, ContactPoint – modele DCAT-AP.
- class MetadataRegistry – rejestr katalogu danych.
- function record_from_transformation – buduje rekord metadanych na podstawie raportu transformacji.
- function registry_from_profile – tworzy rejestr korzystając z `ConfigProfile` i GitOps.
"""

from .models import ContactPoint, DatasetRecord, MetadataDistribution, MetadataField
from .registry import MetadataRegistry, record_from_transformation, registry_from_profile

__all__ = [
    "ContactPoint",
    "DatasetRecord",
    "MetadataDistribution",
    "MetadataField",
    "MetadataRegistry",
    "record_from_transformation",
    "registry_from_profile",
]
