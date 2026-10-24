"""Alcance de una consulta: qué casos puede leer quien pregunta.

## El agujero que esto cierra

El listado REST aplica RN-06 desde siempre (`views.py`: `if not user.is_staff:
qs.filter(analyst=user)`), y el visor devuelve 403 al analista que abre un caso
ajeno. Pero las herramientas del enrutador consultaban
`Sample.objects.filter(status=...)` sobre **toda** la tabla, sin saber siquiera
quién preguntaba: la identidad se comprobaba en la vista y se perdía antes de
llegar al dato.

Medido el 24/09/2026 con `scripts/red_team_biomed.py`: la analista B, dueña de
19 muestras, preguntando por el chat obtenía 3 casos pendientes de firma de A,
1 caso reportado de A **con su nomenclatura ISCN** —el diagnóstico— y 7 CHN
ajenos entre los cromosomas naranjas. Sin inyección ni jailbreak: preguntando
con normalidad, por el camino KEYWORD, que ni siquiera pasa por el modelo.

## Por qué en la aplicación y no en el prompt

Pedirle al modelo «no muestres casos de otros analistas» sería una instrucción
más en un contexto donde ya conviven instrucciones y datos. El modelo PROPONE
qué herramienta usar; la aplicación DECIDE qué puede leer esa herramienta. El
alcance sale del JWT de backend-admin (ADR-0020) y **no hay nada que el usuario
pueda escribir que lo cambie**: declararse supervisor en el texto no altera
`user.is_staff`.

## Cerrado por defecto

`Alcance.NINGUNO` no devuelve nada, y es lo que se usa cuando no hay usuario
autenticado. Si alguien añade una herramienta y olvida pasarle el alcance, el
fallo es que no ve nada — no que lo ve todo. Un control que falla abierto no es
un control.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Alcance:
    """Quién pregunta y qué le toca ver.

    `ve_todo` replica exactamente la regla del listado REST: el personal
    (supervisor, admin) ve el laboratorio entero; el analista, lo suyo. No se
    inventa una política nueva para el chat: se usa la que ya existe, porque
    dos políticas distintas para el mismo dato acaban divergiendo.
    """

    usuario: Any = None
    ve_todo: bool = False

    @classmethod
    def de_usuario(cls, usuario) -> 'Alcance':
        if usuario is None or not getattr(usuario, 'is_authenticated', False):
            return NINGUNO
        return cls(usuario=usuario, ve_todo=bool(getattr(usuario, 'is_staff', False)))

    @property
    def vacio(self) -> bool:
        return self.usuario is None and not self.ve_todo

    def acotar(self, qs):
        """Recorta un queryset de Sample a lo que este alcance puede leer."""
        if self.ve_todo:
            return qs
        if self.usuario is None:
            return qs.none()
        return qs.filter(analyst=self.usuario)

    def acotar_por_muestra(self, qs, campo: str = 'karyotype__sample'):
        """Igual, para querysets que cuelgan de Sample por una relación."""
        if self.ve_todo:
            return qs
        if self.usuario is None:
            return qs.none()
        return qs.filter(**{campo + '__analyst': self.usuario})

    def puede_leer(self, muestra) -> bool:
        """¿Este alcance puede leer esta muestra concreta?"""
        if muestra is None:
            return False
        if self.ve_todo:
            return True
        if self.usuario is None:
            return False
        return muestra.analyst_id == self.usuario.id


#: Cerrado por defecto: sin usuario no se lee nada.
NINGUNO = Alcance(usuario=None, ve_todo=False)
