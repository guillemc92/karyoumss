"""Bitácora de auditoría detrás de una interfaz (DD-E3-001, experimento E3).

Quien lee la bitácora pide `bitacora()` y no sabe si la tiene en su proceso o
en otro servicio: `BITACORA_MODO` lo decide al arrancar. Solo la LECTURA pasa
por aquí; las escrituras siguen siendo `services.emit_audit_event()`, dentro
de la transacción clínica (D2).
"""
from django.conf import settings

from .puerto import BitacoraNoDisponible, BitacoraPort

MODOS = ('proceso', 'http')

_instancia: BitacoraPort | None = None


def bitacora() -> BitacoraPort:
    """La implementación que eligió `BITACORA_MODO`, una por proceso.

    Una sola instancia: el breaker de la forma HTTP tiene que recordar los
    fallos entre peticiones, o no abriría nunca.
    """
    global _instancia
    if _instancia is None:
        _instancia = _construir(settings.BITACORA_MODO)
    return _instancia


def _construir(modo: str) -> BitacoraPort:
    if modo == 'proceso':
        from .en_proceso import BitacoraEnProceso
        return BitacoraEnProceso()
    if modo == 'http':
        from .http import BitacoraHttp
        return BitacoraHttp.desde_settings()
    raise ValueError(f'BITACORA_MODO desconocido: {modo!r} (válidos: {", ".join(MODOS)})')


def reiniciar() -> None:
    """Olvida la instancia. Solo para tests que cambian `BITACORA_MODO`."""
    global _instancia
    _instancia = None


__all__ = ['BitacoraNoDisponible', 'BitacoraPort', 'MODOS', 'bitacora', 'reiniciar']
