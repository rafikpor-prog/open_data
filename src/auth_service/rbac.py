"""
Module: auth_service.rbac
Opis: Definiuje modele RBAC/ABAC wykorzystywane przez `AuthorizationService`.
Funkcje i klasy:
- class Permission: reprezentacja uprawnień REST/GraphQL zgodnych ze standardami dane.gov.pl i API BDL.
- class AttributeRule: reguły ABAC dla datasetów i zasobów.
- class Role: rola użytkownika z zestawem uprawnień i reguł ABAC.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional, Set


@dataclass(frozen=True)
class Permission:
    """
    Technical description:
        Reprezentuje pojedyncze uprawnienie w systemie RBAC. Pole `name`
        identyfikuje operację zgodnie z kontraktami API (np. `datasets.publish`),
        a `description` zawiera opis zgodny z wymaganiami dane.gov.pl.

    Instructions for laika:
        "To etykieta pozwolenia, np. \"opublikuj zbiór danych\". Dzięki niej
        system wie, jakie działania może wykonać użytkownik."

    Example:
        ```python
        Permission(name="datasets.publish", description="Publikacja datasetu w katalogu")
        ```

    Effect for end user:
        Administratorzy przypisują uprawnienia do ról, a użytkownicy końcowi
        zyskują kontrolę nad tym, kto może publikować lub edytować dane.
    """

    name: str
    description: str


@dataclass(frozen=True)
class AttributeRule:
    """
    Technical description:
        Opisuje regułę ABAC stosowaną do datasetów lub wizualizacji. Pole
        `attribute` wskazuje nazwę atrybutu (np. `classification`), `allowed`
        zawiera zbiór wartości dopuszczonych, a `denied` – zbiór wartości
        zabronionych. Flaga `required` określa, czy atrybut musi wystąpić w
        żądaniu. Zbiór `conditions` może zawierać dodatkowe wymagania kontekstowe
        (np. {"environment": "prod"}).

    Instructions for laika:
        "Reguła sprawdza, czy dane mają odpowiednie oznaczenie. Przykład:
        użytkownik może publikować tylko dane o klauzuli \"public\"."

    Example:
        ```python
        AttributeRule(
            attribute="classification",
            allowed={"public"},
            denied={"restricted"},
            required=True,
            conditions={"environment": "prod"}
        )
        ```

    Effect for end user:
        Zapewnia zgodność z politykami bezpieczeństwa – dane poufne nie trafią
        do katalogu bez dodatkowej zgody, a publikacja spełnia wymagania RODO.
    """

    attribute: str
    allowed: Optional[Set[str]] = None
    denied: Optional[Set[str]] = None
    required: bool = False
    conditions: Dict[str, str] = field(default_factory=dict)

    def is_satisfied(self, attributes: Dict[str, str], context: Optional[Dict[str, str]] = None) -> bool:
        """
        Technical description:
            Sprawdza, czy reguła jest spełniona w podanym zbiorze atrybutów.
            Uwzględnia zarówno dopuszczalne wartości, jak i warunki kontekstowe.

        Instructions for laika:
            "Porównujemy etykiety danych z polityką. Jeśli wszystko pasuje,
            reguła przepuszcza operację."

        Example:
            ```python
            rule.is_satisfied({"classification": "public"}, {"environment": "prod"})
            ```

        Effect for end user:
            Operacje na danych są wykonywane tylko wtedy, gdy spełniają polityki
            bezpieczeństwa i zgodności.
        """

        context = context or {}
        if self.required and self.attribute not in attributes:
            return False

        value = attributes.get(self.attribute)
        if value is None:
            value = ""

        if self.allowed and value not in self.allowed:
            return False
        if self.denied and value in self.denied:
            return False

        for key, expected in self.conditions.items():
            if context.get(key) != expected:
                return False
        return True


@dataclass
class Role:
    """
    Technical description:
        Reprezentuje rolę RBAC z listą uprawnień (`permissions`) i reguł ABAC
        (`attribute_rules`). Pole `description` dokumentuje kontekst biznesowy,
        a `inherits` umożliwia dziedziczenie uprawnień z innych ról.

    Instructions for laika:
        "Rola to zestaw przywilejów, np. Administrator Danych. Można do niej
        dodać zasady dotyczące publikacji w zależności od rodzaju danych."

    Example:
        ```python
        Role(
            name="data_admin",
            permissions={Permission("datasets.publish", "Publikacja")},
            attribute_rules=[AttributeRule(attribute="classification", allowed={"public"})],
            description="Administrator danych publicznych"
        )
        ```

    Effect for end user:
        Umożliwia granularne zarządzanie dostępem w Studio Danych, spełniając
        wymagania audytu i zgodności z dane.gov.pl oraz API BDL.
    """

    name: str
    permissions: Set[Permission] = field(default_factory=set)
    attribute_rules: Iterable[AttributeRule] = field(default_factory=list)
    description: str = ""
    inherits: Set[str] = field(default_factory=set)

    def all_permissions(self, parent_lookup: Dict[str, "Role"]) -> Set[Permission]:
        """
        Technical description:
            Zwraca zbiór uprawnień roli wraz z uprawnieniami odziedziczonymi.
            Funkcja zabezpiecza się przed cyklicznym dziedziczeniem.

        Instructions for laika:
            "Sprawdzamy, jakie pozwolenia dostaje użytkownik w tej roli,
            wliczając role nadrzędne."

        Example:
            ```python
            role.all_permissions({"base": base_role})
            ```

        Effect for end user:
            Panel administracyjny może wyświetlić pełny zakres uprawnień i
            wytłumaczyć, skąd pochodzą.
        """

        collected: Set[Permission] = set(self.permissions)
        for parent in self.inherits:
            parent_role = parent_lookup.get(parent)
            if parent_role is None:
                continue
            collected.update(parent_role.all_permissions(parent_lookup))
        return collected

    def all_attribute_rules(self, parent_lookup: Dict[str, "Role"]) -> Iterable[AttributeRule]:
        """
        Technical description:
            Zwraca listę reguł ABAC bieżącej roli oraz wszystkich ról nadrzędnych.

        Instructions for laika:
            "Tworzymy kompletną listę zasad bezpieczeństwa obowiązujących
            użytkownika."

        Example:
            ```python
            list(role.all_attribute_rules({"base": base_role}))
            ```

        Effect for end user:
            Administrator widzi cały zestaw polityk wpływających na możliwość
            publikacji lub edycji danych.
        """

        rules = list(self.attribute_rules)
        for parent in self.inherits:
            parent_role = parent_lookup.get(parent)
            if parent_role is None:
                continue
            rules.extend(parent_role.all_attribute_rules(parent_lookup))
        return rules
