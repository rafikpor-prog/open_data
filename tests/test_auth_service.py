"""
Module: tests.test_auth_service
Opis: Testy jednostkowe weryfikujące moduł uprawnień i audytu z etapu 11.
"""

from __future__ import annotations

import json
from pathlib import Path

from auth_service import AttributeRule, AuthorizationService, AuditTrail, Permission, Role


def build_roles() -> dict:
    """
    Technical description:
        Tworzy zestaw ról testowych wykorzystywanych w scenariuszach RBAC/ABAC.

    Instructions for laika:
        "Przygotowujemy przykładowe role: administrator i analityk."

    Example:
        ```python
        roles = build_roles()
        ```

    Effect for end user:
        Ułatwia tworzenie powtarzalnych testów i dokumentuje konfigurację ról.
    """

    admin_role = Role(
        name="data_admin",
        permissions={
            Permission("datasets.publish", "Publikacja datasetu"),
            Permission("datasets.view", "Podgląd datasetu"),
        },
        attribute_rules=[
            AttributeRule(attribute="classification", allowed={"public"}, required=True, conditions={"environment": "prod"})
        ],
        description="Administrator danych publicznych",
    )
    viewer_role = Role(
        name="data_viewer",
        permissions={Permission("datasets.view", "Podgląd datasetu")},
        description="Analityk z dostępem tylko do odczytu",
    )
    return {"data_admin": admin_role, "data_viewer": viewer_role}


def test_rbac_permission_check(tmp_path: Path) -> None:
    """
    Technical description:
        Sprawdza, czy użytkownik z przypisaną rolą otrzymuje uprawnienie i czy
        decyzja zostaje zapisana w audycie.

    Instructions for laika:
        "Nadajemy rolę administratora i prosimy o publikację zbioru danych."

    Example:
        ```python
        test_rbac_permission_check(tmp_path)
        ```

    Effect for end user:
        Gwarantuje, że panel poprawnie przyzna dostęp i zapisze wpis audytowy.
    """

    audit_path = tmp_path / "audit.json"
    audit = AuditTrail(storage_path=audit_path)
    service = AuthorizationService(audit)
    roles = build_roles()
    for role in roles.values():
        service.register_role(role)

    service.assign_role("alice", "data_admin")
    decision = service.enforce(
        "alice",
        "datasets.publish",
        attributes={"classification": "public"},
        context={"environment": "prod"},
    )

    assert decision.allowed is True
    assert decision.role == "data_admin"
    stored = json.loads(audit_path.read_text(encoding="utf-8"))
    assert any(entry["action"] == "auth.decision.allow" for entry in stored)


def test_abac_denies_restricted_data() -> None:
    """
    Technical description:
        Weryfikuje, czy reguła ABAC blokuje publikację danych o klauzuli
        niedozwolonej i czy decyzja zostaje odnotowana jako `deny`.

    Instructions for laika:
        "Sprawdzamy, że system nie pozwoli opublikować danych zastrzeżonych."

    Example:
        ```python
        test_abac_denies_restricted_data()
        ```

    Effect for end user:
        Zapewnia zgodność z politykami bezpieczeństwa i RODO.
    """

    audit = AuditTrail()
    service = AuthorizationService(audit)
    roles = build_roles()
    for role in roles.values():
        service.register_role(role)

    service.assign_role("bob", "data_admin")
    decision = service.enforce(
        "bob",
        "datasets.publish",
        attributes={"classification": "restricted"},
        context={"environment": "prod"},
    )

    assert decision.allowed is False
    assert decision.role is None
    assert any(record.action == "auth.decision.deny" for record in audit.records)


def test_viewer_role_has_limited_permissions() -> None:
    """
    Technical description:
        Upewnia się, że rola `data_viewer` otrzymuje dostęp tylko do podglądu i
        nie może publikować danych.

    Instructions for laika:
        "Analityk powinien móc obejrzeć dane, ale nie je publikować."

    Example:
        ```python
        test_viewer_role_has_limited_permissions()
        ```

    Effect for end user:
        Potwierdza poprawną konfigurację ról biznesowych w Studio Danych.
    """

    service = AuthorizationService()
    roles = build_roles()
    for role in roles.values():
        service.register_role(role)

    service.assign_role("carol", "data_viewer")
    view_decision = service.enforce("carol", "datasets.view")
    publish_decision = service.enforce("carol", "datasets.publish", attributes={"classification": "public"})

    assert view_decision.allowed is True
    assert publish_decision.allowed is False
