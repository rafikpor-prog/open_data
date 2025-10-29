"""
Module: auth_service
Opis: Zapewnia centralny system uprawnień (RBAC/ABAC) oraz audytu operacji
zgodny z wymaganiami etapu 11 planu rozwoju.
Funkcje i klasy:
- class Permission, class Role, class AttributeRule (w module `rbac`).
- class AuditRecord, class AuditTrail (w module `audit`).
- class AuthorizationService (w module `service`).
"""

from .rbac import AttributeRule, Permission, Role
from .audit import AuditRecord, AuditTrail
from .service import AuthorizationService

__all__ = [
    "AttributeRule",
    "Permission",
    "Role",
    "AuditRecord",
    "AuditTrail",
    "AuthorizationService",
]
