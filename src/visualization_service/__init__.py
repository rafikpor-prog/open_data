"""
Module: visualization_service.__init__
Opis: Udostępnia publiczne API modułu wizualizacji (Etap 13) dla pozostałych
komponentów ekosystemu Open Data Plugin.
Funkcje i klasy:
- class VisualizationService: główny silnik generowania wizualizacji.
- class VisualizationRequest / VisualizationProduct: modele wejścia i wyjścia.
- function build_visualization_service: helper tworzący usługę na podstawie profilu.
"""

from .models import VisualizationProduct, VisualizationRequest
from .service import VisualizationService, build_visualization_service

__all__ = [
    "VisualizationProduct",
    "VisualizationRequest",
    "VisualizationService",
    "build_visualization_service",
]

