from rest_framework.permissions import BasePermission


class CanRegisterSample(BasePermission):
    """RN-06: cualquier usuario autenticado del bounded context clínico
    puede registrar (igual control de acceso que registrarmuestrafinal.html:
    citogenetista/admin/supervisor). El scoping por rol para acciones
    admin-only (delete) vive en las views del CRUD, no acá."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)
