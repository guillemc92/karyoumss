"""
Permissions para apps/config (DD-ADMIN-002 §1.4).

- IsOwnerOrAdmin: para endpoints /me/* — usuario autenticado edita su
  propio recurso, admin edita cualquiera.
- IsAdminRole: re-exportado desde apps.users para conveniencia de los
  viewsets que solo el admin debe tocar (P3 modelos, P5 integraciones).
"""
from rest_framework.permissions import BasePermission

from apps.users.permissions import IsAdminRole  # noqa: F401  (re-export)


class IsOwnerOrAdmin(BasePermission):
    """
    Para /me/*:
    - GET: el propio usuario autenticado O un admin.
    - PATCH/POST: el propio usuario O un admin.

    Decisión de diseño: el permiso opera a nivel de objeto. El viewset
    debe llamar a `self.check_object_permissions(request, obj)` antes
    de mutar.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, 'role', None) == 'admin':
            return True
        # obj.user es la FK al User de auth
        return getattr(obj, 'user_id', None) == request.user.id
