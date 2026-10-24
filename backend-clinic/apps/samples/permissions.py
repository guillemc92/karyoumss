from rest_framework.permissions import BasePermission

from .models_rbac import Opcion, PrivilegioGrupo, PrivilegioIndividual

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


def tiene_opcion(user, opcion_code: str) -> bool:
    """RBAC jerárquico (ADR-0019, DD-RBAC-001) — port literal de
    Seguridad.TieneOpcion()/nodeValue() del módulo C# real compartido
    por el arquitecto (carpeta Security/).

    Regla de resolución (idéntica al original, no una reinterpretación):
    1. Si el usuario tiene una excepción individual (PrivilegioIndividual
       con permitido != None) para esta opción, esa excepción SIEMPRE
       gana — sea para dar acceso (True) o quitarlo (False) aunque el
       grupo diga lo contrario.
    2. Si no hay excepción, se combina el resultado de TODOS los grupos
       del usuario con deny-overrides: basta que un grupo deniegue
       (permitido=False) para que el resultado combinado sea False,
       sin importar que otro grupo la permita.
    3. Si el usuario no pertenece a ningún grupo que defina esta opción,
       o la Opcion no existe (seed no ejecutado), el resultado es False
       (fail-closed — más seguro que fail-open ante un seed faltante).
    """
    opcion = Opcion.objects.filter(codigo=opcion_code).first()
    if opcion is None:
        return False

    individual = PrivilegioIndividual.objects.filter(usuario=user, opcion=opcion).first()
    if individual is not None and individual.permitido is not None:
        return individual.permitido

    privilegios_grupo = list(
        PrivilegioGrupo.objects.filter(
            opcion=opcion, grupo__usuarios__usuario=user,
        ).values_list('permitido', flat=True)
    )
    if not privilegios_grupo:
        return False
    return all(privilegios_grupo)


class HasOpcion(BasePermission):
    """Permission class DRF parametrizable, envuelve tiene_opcion().

    Uso: permission_classes = [HasOpcion('sample.delete')]
    """

    def __init__(self, opcion_code: str):
        self.opcion_code = opcion_code

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        return tiene_opcion(request.user, self.opcion_code)
