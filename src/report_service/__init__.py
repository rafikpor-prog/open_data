"""
Module: report_service.__init__
Opis: Udostępnia publiczne API modułu generatora raportów (Etap 15) łączącego
wizualizacje, metadane DCAT-AP oraz eksporty JSON-LD.
Funkcje i klasy:
- class ReportService: silnik generowania raportów HTML/PDF z fallbackiem offline.
- class ReportRequest: model wejściowy zawierający dane datasetu, wizualizacje
  i załączniki.
- class ReportProduct: wynik działania generatora (ścieżki plików, komunikaty).
- function build_report_service: helper budujący usługę na podstawie profilu
  `ConfigProfile` (sekcja `reports`).
"""

from .models import ReportProduct, ReportRequest, ReportVisualization
from .service import ReportService, build_report_service

__all__ = [
    "ReportService",
    "ReportRequest",
    "ReportProduct",
    "ReportVisualization",
    "build_report_service",
]
