"""
Module: auth_service.service
Opis: Implementuje `AuthorizationService`, który łączy role RBAC, reguły ABAC
oraz audyt w celu weryfikacji dostępu zgodnie z etapem 11 planu rozwoju.
Funkcje i klasy:
- class AuthorizationService: centralny punkt sprawdzania uprawnień.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Set

from .audit import AuditTrail
from .rbac import AttributeRule, Permission, Role


@dataclass
class AccessDecision:
    """
    Technical description:
        Reprezentuje wynik decyzji autoryzacyjnej. Pole `allowed` informuje,
        czy dostęp został przyznany, `reason` zawiera uzasadnienie, a `role`
        wskazuje, która rola wpłynęła na decyzję.

    Instructions for laika:
        "To odpowiedź systemu: czy użytkownik może wykonać działanie i dlaczego."

    Example:
        ```python
        AccessDecision(allowed=True, reason="Role data_admin", role="data_admin")
        ```

    Effect for end user:
        Ułatwia wyświetlanie komunikatów w Studio Danych i logach audytu.
    """

    allowed: bool
    reason: str
    role: Optional[str]


class AuthorizationService:
    """
    Technical description:
        Zarządza rolami, uprawnieniami i audytem użytkowników. Obsługuje zarówno
        klasyczne RBAC, jak i reguły ABAC oraz integruje się z `AuditTrail`, aby
        zapisywać wszystkie decyzje. Zgodny z wymaganiami danych.gov.pl, API BDL
        i standardami UE (RODO, eIDAS).

    Instructions for laika:
        "To strażnik dostępu. Przypisujesz użytkownikowi rolę, a system pilnuje,
        czy może wykonywać określone akcje i zapisuje to w dzienniku."

    Example:
        ```python
        service = AuthorizationService(audit_trail)
        service.register_role(role)
        service.assign_role("user1", "data_admin")
        decision = service.enforce("user1", "datasets.publish", {"classification": "public"})
        ```

    Effect for end user:
        Zapewnia kontrolę uprawnień w całym ekosystemie (Studio Danych, WordPress,
        API) i spełnia wymagania audytowe.
    """

    def __init__(self, audit_trail: Optional[AuditTrail] = None) -> None:
        self._roles: Dict[str, Role] = {}
        self._user_roles: Dict[str, Set[str]] = {}
        self._audit_trail = audit_trail or AuditTrail()

    def register_role(self, role: Role) -> None:
        """
        Technical description:
            Dodaje lub aktualizuje rolę w katalogu. Rola jest identyfikowana po
            nazwie. Operacja jest zapisywana w audycie jako `auth.role.register`.

        Instructions for laika:
            "Dodajesz nową rolę albo aktualizujesz istniejącą – np. Administrator
            Danych."

        Example:
            ```python
            service.register_role(role)
            ```

        Effect for end user:
            Pozwala administratorom szybko wdrażać polityki bezpieczeństwa bez
            zmian w kodzie.
        """

        self._roles[role.name] = role
        self._audit_trail.log("system", "auth.role.register", role.name, {"description": role.description})

    def assign_role(self, user_id: str, role_name: str) -> None:
        """
        Technical description:
            Przypisuje rolę użytkownikowi. Operacja jest odnotowywana w audycie i
            tworzy wpis `auth.role.assign`.

        Instructions for laika:
            "Nadajesz użytkownikowi uprawnienia wynikające z danej roli."

        Example:
            ```python
            service.assign_role("analyst", "data_viewer")
            ```

        Effect for end user:
            Użytkownicy natychmiast otrzymują dostęp do funkcji panelu zgodnie z
            polityką bezpieczeństwa.
        """

        if role_name not in self._roles:
            raise KeyError(f"Rola {role_name} nie jest zarejestrowana")
        self._user_roles.setdefault(user_id, set()).add(role_name)
        self._audit_trail.log(user_id, "auth.role.assign", role_name)

    def revoke_role(self, user_id: str, role_name: str) -> None:
        """
        Technical description:
            Usuwa przypisanie roli. Operacja zapisuje się jako `auth.role.revoke`.

        Instructions for laika:
            "Zabierasz użytkownikowi określoną rolę."

        Example:
            ```python
            service.revoke_role("analyst", "data_viewer")
            ```

        Effect for end user:
            Natychmiastowe ograniczenie dostępu, co jest ważne przy zmianie zadań
            lub odejściu pracownika.
        """

        if user_id not in self._user_roles:
            return
        if role_name in self._user_roles[user_id]:
            self._user_roles[user_id].remove(role_name)
            self._audit_trail.log(user_id, "auth.role.revoke", role_name)
        if not self._user_roles[user_id]:
            del self._user_roles[user_id]

    def list_roles(self, user_id: str) -> Set[str]:
        """
        Technical description:
            Zwraca zestaw ról przypisanych użytkownikowi.

        Instructions for laika:
            "Sprawdzasz, jakie uprawnienia ma dana osoba."

        Example:
            ```python
            service.list_roles("admin")
            ```

        Effect for end user:
            Ułatwia audyt i przeglądy bezpieczeństwa.
        """

        return set(self._user_roles.get(user_id, set()))

    def enforce(
        self,
        user_id: str,
        permission_name: str,
        attributes: Optional[Dict[str, str]] = None,
        context: Optional[Dict[str, str]] = None,
    ) -> AccessDecision:
        """
        Technical description:
            Sprawdza, czy użytkownik posiada wskazane uprawnienie i spełnia
            reguły ABAC. Wykorzystuje dziedziczenie ról i w razie powodzenia
            zapisuje decyzję `auth.decision.allow`, w przeciwnym razie
            `auth.decision.deny`.

        Instructions for laika:
            "Pytamy strażnika, czy użytkownik może wykonać działanie – np.
            opublikować zbiór danych."

        Example:
            ```python
            decision = service.enforce(
                "admin",
                "datasets.publish",
                {"classification": "public"},
                {"environment": "prod"}
            )
            ```

        Effect for end user:
            Zapewnia jednolite decyzje w panelu, API i wtyczce WordPress oraz
            zapisuje je do audytu.
        """

        attributes = attributes or {}
        context = context or {}
        roles = self._collect_roles(user_id)
        permission = None
        for role_name, role in roles.items():
            all_permissions = role.all_permissions(roles)
            for perm in all_permissions:
                if perm.name != permission_name:
                    continue
                permission = perm
                if self._is_abac_allowed(role, roles, attributes, context):
                    decision = AccessDecision(True, f"Allowed via role {role_name}", role_name)
                    self._audit_trail.log(
                        user_id,
                        "auth.decision.allow",
                        permission_name,
                        {"role": role_name, "context": context, "attributes": attributes},
                    )
                    return decision
        decision = AccessDecision(False, "Permission denied", None)
        self._audit_trail.log(
            user_id,
            "auth.decision.deny",
            permission_name,
            {"context": context, "attributes": attributes},
        )
        return decision

    def _collect_roles(self, user_id: str) -> Dict[str, Role]:
        assigned = self._user_roles.get(user_id, set())
        return {name: self._roles[name] for name in assigned if name in self._roles}

    def _is_abac_allowed(
        self,
        role: Role,
        lookup: Dict[str, Role],
        attributes: Dict[str, str],
        context: Dict[str, str],
    ) -> bool:
        """
        Technical description:
            Weryfikuje reguły ABAC zdefiniowane w roli i rolach nadrzędnych.
            Jeśli rola nie ma reguł, dostęp jest dozwolony (domyślne zachowanie).

        Instructions for laika:
            "Sprawdzamy dodatkowe warunki bezpieczeństwa – np. klasę danych."

        Example:
            ```python
            service._is_abac_allowed(role, lookup, {"classification": "public"}, {"environment": "prod"})
            ```

        Effect for end user:
            Chroni przed publikacją danych oznaczonych jako zastrzeżone.
        """

        rules: Iterable[AttributeRule] = role.all_attribute_rules(lookup)
        has_rules = False
        for rule in rules:
            has_rules = True
            if not rule.is_satisfied(attributes, context):
                return False
        return True if has_rules else True
