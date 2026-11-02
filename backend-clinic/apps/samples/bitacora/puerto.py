"""El contrato de la bitácora: lo único que conoce quien la lee."""
from typing import Protocol
from uuid import UUID


class BitacoraNoDisponible(Exception):
    """La bitácora no respondió a tiempo o está caída. La vista responde 503."""


class BitacoraPort(Protocol):
    def listar(self, sample_id: UUID) -> list[dict]:
        """Los eventos del caso, en orden, con la forma de `AuditEventSerializer`.

        Un caso sin eventos devuelve `[]`. Que el caso exista y que quien
        pregunta pueda verlo lo comprueba la API ANTES de llamar.
        """
        ...
