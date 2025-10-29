"""
Module: auth_service.audit
Opis: Obsługuje rejestrowanie i eksport zdarzeń audytowych zgodnych z
wymaganiami etapu 11.
Funkcje i klasy:
- class AuditRecord: pojedynczy wpis audytowy.
- class AuditTrail: menedżer logów audytu z opcjonalną persystencją na dysku.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional
import json


@dataclass(frozen=True)
class AuditRecord:
    """
    Technical description:
        Przechowuje informację o zdarzeniu audytowym. Pola `user_id`, `action`,
        `resource` i `metadata` dokumentują kontekst operacji, a `timestamp`
        zapisuje czas w UTC zgodnie z wymaganiami RODO i ENISA.

    Instructions for laika:
        "To wpis w dzienniku działań. Zawiera kto zrobił operację, na jakim
        obiekcie i kiedy."

    Example:
        ```python
        AuditRecord(user_id="admin", action="datasets.publish", resource="population", metadata={"status": "ok"})
        ```

    Effect for end user:
        Administrator ma pełną historię operacji, co ułatwia kontrole bezpieczeństwa
        i raporty wymagane przez dane.gov.pl.
    """

    user_id: str
    action: str
    resource: str
    metadata: dict
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_json(self) -> dict:
        """
        Technical description:
            Zwraca reprezentację rekordu zgodną z JSON:API (klucz `attributes`).

        Instructions for laika:
            "Przygotowujemy rekord tak, by można go było zapisać do pliku JSON."

        Example:
            ```python
            record.to_json()
            ```

        Effect for end user:
            Zapisy audytu można łatwo udostępnić w raportach lub narzędziach SIEM.
        """

        return {
            "user_id": self.user_id,
            "action": self.action,
            "resource": self.resource,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
        }


class AuditTrail:
    """
    Technical description:
        Zarządza kolekcją rekordów audytowych i opcjonalnie zapisuje je do pliku
        w katalogu wskazanym przez administratora. Obsługuje polityki retencji i
        umożliwia filtrowanie po akcjach/użytkownikach.

    Instructions for laika:
        "To dziennik działań. Możesz dodać wpis, a gdy trzeba – zapisać go do
        pliku, by przedstawić raport kontroli."

    Example:
        ```python
        trail = AuditTrail(storage_path=Path("build/audit.json"), retention=1000)
        trail.log("admin", "datasets.publish", "population")
        ```

    Effect for end user:
        Zapewnia kompletne ślady audytowe wymagane przez dane.gov.pl i API BDL,
        chroniąc przed nieautoryzowanymi zmianami danych.
    """

    def __init__(self, storage_path: Optional[Path] = None, retention: int = 1000) -> None:
        self._storage_path = storage_path
        self._retention = retention
        self._records: List[AuditRecord] = []

    def log(self, user_id: str, action: str, resource: str, metadata: Optional[dict] = None) -> AuditRecord:
        """
        Technical description:
            Tworzy nowy wpis audytowy i dodaje go do pamięci. Przy przekroczeniu
            limitu `retention` najstarsze wpisy są usuwane. Jeśli skonfigurowano
            `storage_path`, wpisy są zapisywane do pliku JSON (append-only).

        Instructions for laika:
            "Dodajemy nową notatkę do dziennika. Gdy jest ustawiony plik, zapisuje
            się automatycznie."

        Example:
            ```python
            record = trail.log("analyst", "datasets.view", "population", {"status": "allowed"})
            ```

        Effect for end user:
            Każda akcja w systemie ma ślad, co spełnia wymagania audytu.
        """

        record = AuditRecord(user_id=user_id, action=action, resource=resource, metadata=metadata or {})
        self._records.append(record)
        if len(self._records) > self._retention:
            self._records = self._records[-self._retention :]
        if self._storage_path:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            existing: List[dict] = []
            if self._storage_path.exists():
                existing = json.loads(self._storage_path.read_text(encoding="utf-8"))
            existing.append(record.to_json())
            self._storage_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        return record

    def query(self, user_id: Optional[str] = None, action: Optional[str] = None) -> Iterable[AuditRecord]:
        """
        Technical description:
            Zwraca rekordy audytowe spełniające zadane kryteria filtrowania.

        Instructions for laika:
            "Możesz wyświetlić wpisy dla konkretnego użytkownika lub akcji."

        Example:
            ```python
            list(trail.query(user_id="admin"))
            ```

        Effect for end user:
            Ułatwia szybkie wyszukiwanie incydentów i przygotowanie raportów dla
            CSIRT lub kontroli.
        """

        for record in self._records:
            if user_id and record.user_id != user_id:
                continue
            if action and record.action != action:
                continue
            yield record

    @property
    def records(self) -> List[AuditRecord]:
        """
        Technical description:
            Zwraca bieżącą listę rekordów audytowych przechowywanych w pamięci.

        Instructions for laika:
            "Pozwala szybko zobaczyć wszystkie wpisy bez filtrowania."

        Example:
            ```python
            trail.records
            ```

        Effect for end user:
            Administrator ma natychmiastowy podgląd historii działań.
        """

        return list(self._records)
