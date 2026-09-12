"""RBAC jerárquico (TipoObjeto→Objeto→Opción, Grupos + excepción individual).

Port fiel del módulo de seguridad C# real compartido por el arquitecto
(carpeta `Security/`, proyecto WinForms `iibismed`) — ver ADR-0019 y
DD-RBAC-001 para el diseño completo y la correspondencia con el código
original (`seg_tipos_objetos`, `seg_objetos`, `seg_opciones`,
`seg_grupos`, `seg_privilegios_grupo`, `seg_usuarios_grupos`,
`seg_privilegios_individuales`).

Extiende ADR-0018 (no lo deroga): el scoping "propias vs. todas" sigue
viviendo en get_queryset()/IsOwnerOrStaff, sin cambios. Este módulo
resuelve una pregunta distinta: ¿puede este usuario intentar esta
acción en absoluto?
"""
from django.conf import settings
from django.db import models


class TipoObjeto(models.Model):
    """Análogo a seg_tipos_objetos. Categoría de objeto: 'Formulario', 'Menú', etc."""

    nombre = models.CharField(max_length=25)
    descripcion = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'clinic_rbac_tipo_objeto'

    def __str__(self):
        return self.nombre


class Objeto(models.Model):
    """Análogo a seg_objetos. Una pantalla/recurso concreto, ej. 'Muestras'."""

    tipo = models.ForeignKey(TipoObjeto, on_delete=models.CASCADE, related_name='objetos')
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'clinic_rbac_objeto'

    def __str__(self):
        return self.nombre


class Opcion(models.Model):
    """Análogo a seg_opciones. Una acción dentro de un Objeto.

    `codigo` es la referencia estable desde el código Python
    (ej. 'sample.delete'), a diferencia del C# original que usaba el
    `opc_cod` autoincremental hardcodeado en cada form
    (`Seguridad.TieneOpcion(31)`) — patrón frágil que este modelo evita
    deliberadamente (ADR-0019 D2/A3).
    """

    objeto = models.ForeignKey(Objeto, on_delete=models.CASCADE, related_name='opciones')
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'clinic_rbac_opcion'
        constraints = [
            models.UniqueConstraint(fields=['objeto', 'nombre'], name='uniq_objeto_opcion_nombre'),
        ]

    def __str__(self):
        return f'{self.codigo} ({self.nombre})'


class Grupo(models.Model):
    """Análogo a seg_grupos. Catálogo configurable de grupos de acceso.

    Reemplaza los 3 roles fijos de ADR-0018 (analista/supervisor/admin
    derivados de is_staff/is_superuser) por un catálogo de datos. El
    seed inicial (migración) crea exactamente esos 3 grupos para no
    cambiar el comportamiento observable el día del despliegue.
    """

    nombre = models.CharField(max_length=25, unique=True)
    descripcion = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'clinic_rbac_grupo'

    def __str__(self):
        return self.nombre


class PrivilegioGrupo(models.Model):
    """Análogo a seg_privilegios_grupo. Qué puede hacer cada grupo en
    cada opción. `permitido` es BooleanField real (bit en el original),
    no un TipoAcceso de 3 niveles."""

    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, related_name='privilegios')
    opcion = models.ForeignKey(Opcion, on_delete=models.CASCADE, related_name='privilegios_grupo')
    permitido = models.BooleanField(default=False)

    class Meta:
        db_table = 'clinic_rbac_privilegio_grupo'
        constraints = [
            models.UniqueConstraint(fields=['grupo', 'opcion'], name='uniq_grupo_opcion'),
        ]

    def __str__(self):
        return f'{self.grupo} / {self.opcion.codigo} = {self.permitido}'


class UsuarioGrupo(models.Model):
    """Análogo a seg_usuarios_grupos. N:M real: un usuario puede
    pertenecer a varios grupos simultáneamente."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='grupos_clinicos',
    )
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, related_name='usuarios')

    class Meta:
        db_table = 'clinic_rbac_usuario_grupo'
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'grupo'], name='uniq_usuario_grupo'),
        ]

    def __str__(self):
        return f'{self.usuario} ∈ {self.grupo}'


class PrivilegioIndividual(models.Model):
    """Análogo a seg_privilegios_individuales. Excepción absoluta por
    usuario: permitido=None significa "sin excepción, usa el resultado
    combinado de grupos"; True/False fuerza el valor sin importar qué
    digan los grupos del usuario (port literal de nodeValue() del C#
    real — ver ADR-0019 §Contexto y DD-RBAC-001 §4)."""

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='privilegios_individuales',
    )
    opcion = models.ForeignKey(Opcion, on_delete=models.CASCADE, related_name='privilegios_individuales')
    permitido = models.BooleanField(null=True, default=None)

    class Meta:
        db_table = 'clinic_rbac_privilegio_individual'
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'opcion'], name='uniq_usuario_opcion_individual'),
        ]

    def __str__(self):
        return f'{self.usuario} / {self.opcion.codigo} = {self.permitido}'
