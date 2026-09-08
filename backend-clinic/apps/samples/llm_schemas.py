"""Esquemas Pydantic de la salida del LLM — ADR-0024 D4 (salida estructurada).

Un LLM es una **función no confiable**: puede devolver prosa donde se esperaba
JSON, inventar campos, u omitir los requeridos. El contrato de tipos es lo que
convierte esa salida en un dato que el sistema puede consumir sin adivinar.

Por qué un objeto tipado y no un párrafo suelto:

- **Validación real.** Sobre prosa solo se puede hacer regex; sobre campos
  tipados se valida estructura, rangos y enums.
- **Revisión por partes.** El Supervisor puede aceptar la interpretación y
  corregir solo el nivel de confianza, en vez de reescribir un bloque de texto.
- **Trazabilidad.** `hallazgo` y `interpretacion` se auditan por separado.

El campo `anomalias_citadas` es la pieza de seguridad: obliga al modelo a
**declarar** qué anomalías afirma, en vez de dejarlas enterradas en la prosa.
Así la verificación contra el ISCN (ADR-0024 D4.1) deja de depender de una
expresión regular sobre lenguaje natural.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class NivelConfianza(str, Enum):
    """Qué tan seguro está el modelo de su propia redacción.

    No es la confianza del diagnóstico —ese lo da el ISCN determinístico—, sino
    una señal para priorizar qué borradores revisa primero el Supervisor.
    """

    ALTA = 'alta'
    MEDIA = 'media'
    BAJA = 'baja'


class NarrativaCariotipo(BaseModel):
    """Salida estructurada del LLM para el informe (ADR-0024 D3).

    Es un BORRADOR: requiere revisión humana antes de llegar al informe firmado.
    """

    hallazgo: str = Field(
        min_length=10, max_length=300,
        description='Descripción objetiva de lo observado, en una o dos frases.',
    )
    interpretacion: str = Field(
        min_length=20, max_length=800,
        description='Párrafo interpretativo en registro clínico formal.',
    )
    es_normal: bool = Field(
        description='True si el cariotipo no presenta alteraciones.',
    )
    anomalias_citadas: list[str] = Field(
        default_factory=list, max_length=20,
        description=(
            'Anomalías afirmadas en el texto, en notación ISCN (+21, -18, del(5p)). '
            'Lista vacía si el cariotipo es normal.'
        ),
    )
    nivel_confianza: NivelConfianza = Field(
        default=NivelConfianza.MEDIA,
        description='Confianza del modelo en su propia redacción.',
    )

    @field_validator('hallazgo', 'interpretacion')
    @classmethod
    def _sin_relleno(cls, v: str) -> str:
        """Rechaza respuestas de relleno que pasarían el mínimo de longitud."""
        limpio = ' '.join(v.split())
        if not limpio:
            raise ValueError('el campo no puede estar vacío')
        return limpio

    @field_validator('anomalias_citadas')
    @classmethod
    def _normaliza_anomalias(cls, v: list[str]) -> list[str]:
        return [a.strip().replace(' ', '') for a in v if a and a.strip()]

    def es_coherente_con(self, iscn: str) -> tuple[bool, str]:
        """Verifica la salida contra el ISCN determinístico (ADR-0024 D4.1).

        Dos comprobaciones sobre campos declarados, no sobre prosa:

        1. Toda anomalía citada debe existir en el ISCN. Afirmar `+21` sobre un
           `46,XX` es un diagnóstico falso.
        2. `es_normal` debe concordar: un ISCN con anomalías no puede narrarse
           como normal, ni al revés.

        Devuelve (es_coherente, motivo).
        """
        iscn_norm = (iscn or '').replace(' ', '').lower()

        for anomalia in self.anomalias_citadas:
            if anomalia.lower() not in iscn_norm:
                return False, f'anomalía "{anomalia}" no está en el ISCN {iscn!r}'

        # El ISCN normal es solo '<total>,<sexo>': sin más componentes.
        iscn_tiene_anomalias = iscn_norm.count(',') > 1
        if self.es_normal and iscn_tiene_anomalias:
            return False, f'declara cariotipo normal pero el ISCN {iscn!r} tiene anomalías'
        if not self.es_normal and not iscn_tiene_anomalias and not self.anomalias_citadas:
            return False, f'declara cariotipo anormal pero el ISCN {iscn!r} es normal'

        return True, ''

    def como_texto(self) -> str:
        """Aplana el objeto al párrafo que se persiste en `narrative_draft`."""
        return f'{self.hallazgo} {self.interpretacion}'.strip()


# Esquema JSON para `response_format` de la API (Ollama y OpenAI lo soportan).
# `strict: True` obliga al modelo a respetar la forma exacta.
NARRATIVA_JSON_SCHEMA = {
    'type': 'json_schema',
    'json_schema': {
        'name': 'narrativa_cariotipo',
        'strict': True,
        'schema': {
            **NarrativaCariotipo.model_json_schema(),
            'additionalProperties': False,
        },
    },
}
