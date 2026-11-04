"""Forma 1: la bitácora dentro del monolito, como hasta ahora."""
from uuid import UUID

from ..models import AuditEvent
from ..serializers import AuditEventSerializer


def eventos_de(sample_id: UUID) -> list[dict]:
    """La consulta y la serialización de la bitácora de un caso.

    La comparten la forma en proceso y la vista interna del servicio extraído,
    para que las dos formas hagan exactamente el mismo trabajo en la base y lo
    único que cambie entre ellas sea el salto por la red.
    """
    return AuditEventSerializer(AuditEvent.objects.filter(sample_id=sample_id), many=True).data


class BitacoraEnProceso:
    def listar(self, sample_id: UUID) -> list[dict]:
        return eventos_de(sample_id)
