from rest_framework.permissions import BasePermission

RoleLiteral = str  # 'analista' | 'supervisor' | 'admin'


def role_for_user(user) -> RoleLiteral:
    """Deriva el rol clínico de los campos ya existentes del User de Django
    (ADR-0018) — sin campo `role` nuevo, sin migración.

    is_superuser=True         -> admin
    is_staff=True (sin super) -> supervisor
    ninguno de los anteriores -> analista
    """
    if user.is_superuser:
        return 'admin'
    if user.is_staff:
        return 'supervisor'
    return 'analista'


class IsClinicRole(BasePermission):
    """Cualquier usuario autenticado del contexto clínico (los 3 roles).

    RN-06: cualquier rol clínico puede listar/crear/registrar (igual
    control de acceso que registrarmuestrafinal.html: citogenetista/
    admin/supervisor). El scoping fino (propias vs. todas) vive en
    get_queryset() de cada view, no acá.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsAdminRole(BasePermission):
    """Solo admin (is_superuser) — ADR-0018 D3, usado en DELETE."""

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.is_superuser
        )


class IsOwnerOrStaff(BasePermission):
    """Permiso a nivel de objeto (SPEC-008 CA-5): un analista solo accede a
    sus propias muestras (403 si no es dueño); supervisor/admin (is_staff)
    acceden a cualquiera. Distinto de filtrar en get_queryset(): acá "existe
    pero no es tuya" es 403, no 404 — es la semántica que pide SPEC-008."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_staff:
            return True
        return obj.analyst_id == user.id


# Alias semántico: el registro de una muestra nueva está abierto a los 3
# roles clínicos, igual que IsClinicRole. Se mantiene como nombre propio
# porque CanRegisterSample ya es referenciado desde SampleRegisterView
# (ADR-0016) y desde su suite de tests — renombrar rompería ambos sin
# aportar valor.
CanRegisterSample = IsClinicRole
