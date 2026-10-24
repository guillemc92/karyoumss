"""
DRF permissions for bounded context admin.

El token de Django (DRF TokenAuth) autentica. Luego verificamos que el rol
sea 'admin' para mutaciones (POST/PATCH/DELETE).
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminRole(BasePermission):
    """
    Permite solo a usuarios con role='admin' hacer mutaciones.

    - GET: cualquier usuario autenticado (futuro: supervisor en modo solo-lectura).
    - POST/PATCH/DELETE: solo role='admin'.
    """

    message = 'Se requiere rol administrador para esta operación.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        # Mutaciones: solo admin
        return getattr(request.user, 'role', None) == 'admin'


class IsAdminOrSelf(BasePermission):
    """Permite al usuario ver/editar su propio perfil, o a un admin editar cualquiera."""

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        if getattr(request.user, 'role', None) == 'admin':
            return True
        # Self-edit: solo si obj.user == request.user (no implementado en MVP)
        return obj.user_id == request.user.id if hasattr(obj, 'user_id') else False