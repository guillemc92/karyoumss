"""Signals del RBAC jerárquico (ADR-0019, DD-RBAC-001 §5.4).

Auto-asigna el grupo 'Analista' (menor privilegio) a todo usuario
nuevo que no tenga ningún grupo asignado — evita que un usuario recién
creado quede sin ningún permiso por el diseño fail-closed de
tiene_opcion(). Un administrador puede reasignar/agregar grupos
después sin restricción; el signal solo actúa en la creación.
"""
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models_rbac import Grupo, UsuarioGrupo


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def asignar_grupo_analista_por_defecto(sender, instance, created, **kwargs):
    if not created:
        return
    if UsuarioGrupo.objects.filter(usuario=instance).exists():
        return
    grupo_analista, _ = Grupo.objects.get_or_create(nombre='Analista')
    UsuarioGrupo.objects.create(usuario=instance, grupo=grupo_analista)
