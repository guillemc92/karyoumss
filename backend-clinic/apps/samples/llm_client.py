"""llm_client — cliente del LLM local para la narrativa del informe (ADR-0024).

IA **generativa** vía SDK, complementaria a la IA **discriminativa** del pipeline
(EfficientNet-B3, ADR-0007). Este cliente NO calcula datos clínicos: recibe el
ISCN ya generado por `generate_iscn()` (función pura, ADR-0023 D4) y pide al
modelo únicamente la prosa que lo acompaña.

Proveedor: **Ollama en localhost** (ADR-0024 D2). Expone una API compatible con
el SDK de OpenAI, así que se usa el SDK estándar apuntando a `base_url` local —
mismos conceptos que un proveedor de pago (SDK, request/response, tokens,
latencia) sin egreso de datos: RN-03 se cumple por construcción, no por
convención.

Circuit breaker con el mismo patrón que `pipeline_client` (ADR-0015 #6) y
`admin_client` (ADR-0023 D3). A diferencia de la firma MFA, aquí el fallo NO
bloquea: sin narrativa el informe se emite igual (RN-07, ADR-0024 D4.3).
"""
from __future__ import annotations

import logging
import time

from django.conf import settings
from pydantic import ValidationError

from .llm_schemas import NARRATIVA_JSON_SCHEMA, NarrativaCariotipo

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    'Eres un asistente de redacción para un laboratorio de citogenética. '
    'Recibes una nomenclatura ISCN ya calculada y validada por un analista humano. '
    'Devuelves un objeto JSON con la redacción para el informe, en español.\n\n'
    'REGLAS ESTRICTAS:\n'
    '1. NO inventes ni infieras anomalías que no estén en el ISCN recibido.\n'
    '2. NO recuentes ni cuestiones el ISCN: es un dato ya verificado.\n'
    '3. NO emitas diagnóstico definitivo ni recomendación terapéutica.\n'
    '4. Registro clínico formal y sobrio.\n'
    '5. Cierra la interpretación indicando que requiere correlación clínica.\n\n'
    'CAMPOS:\n'
    '- hallazgo: qué se observa, en una o dos frases objetivas.\n'
    '- interpretacion: el párrafo interpretativo (2 a 4 frases).\n'
    '- es_normal: true solo si el ISCN no tiene anomalías (p. ej. 46,XX o 46,XY).\n'
    '- anomalias_citadas: las anomalías que afirmas, en notación ISCN ("+21", '
    '"del(5p)"). Lista vacía si el cariotipo es normal. DEBEN estar en el ISCN '
    'recibido: cualquier otra cosa se rechaza.\n'
    '- nivel_confianza: "alta", "media" o "baja".'
)


class LlmServiceError(Exception):
    """El servicio LLM no está disponible o devolvió algo inutilizable."""


class LlmClient:
    def __init__(self, base_url: str, model: str, timeout: float, threshold: int,
                 cooldown: int, max_intentos: int = 2):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.threshold = threshold
        self.cooldown = cooldown
        self.max_intentos = max_intentos
        self._failures = 0
        self._circuit_open_until = 0.0

    def _circuit_open(self) -> bool:
        return time.time() < self._circuit_open_until

    def _record_failure(self):
        self._failures += 1
        if self._failures >= self.threshold:
            self._circuit_open_until = time.time() + self.cooldown

    def _record_success(self):
        self._failures = 0

    def _build_prompt(self, iscn: str, sample_type: str, chn_code: str, counts: dict) -> str:
        """Construye el prompt SIN PII (ADR-0024 D6).

        Solo entra: código CHN (seudónimo), ISCN, tipo de muestra y conteo por
        clase. Nombre, documento y fecha de nacimiento viven cifrados en
        PatientVault (ADR-0016 D2) y no se incluyen jamás.
        """
        resumen = ', '.join(f'{k}: {v}' for k, v in sorted(counts.items())) if counts else 'n/d'
        return (
            f'Caso: {chn_code}\n'
            f'Tipo de muestra: {sample_type}\n'
            f'Nomenclatura ISCN (ya validada): {iscn}\n'
            f'Conteo por clase: {resumen}\n\n'
            f'Redacta el párrafo interpretativo para este resultado.'
        )

    def _parse_structured(self, raw: str, iscn: str) -> NarrativaCariotipo:
        """Valida la respuesta contra el contrato de tipos (ADR-0024 D4).

        Dos capas: Pydantic verifica la FORMA (campos, tipos, longitudes) y
        `es_coherente_con` verifica el CONTENIDO contra el ISCN determinístico.
        Un objeto bien formado que afirme una trisomía inexistente pasa la
        primera y debe fallar la segunda.
        """
        try:
            narrativa = NarrativaCariotipo.model_validate_json(raw or '')
        except ValidationError as exc:
            primero = exc.errors()[0] if exc.errors() else {}
            campo = '.'.join(str(p) for p in primero.get('loc', ())) or '?'
            raise LlmServiceError(
                f'no cumple el esquema: {campo} — {primero.get("msg", exc)}') from exc

        coherente, motivo = narrativa.es_coherente_con(iscn)
        if not coherente:
            raise LlmServiceError(f'alucinación: {motivo}')
        return narrativa

    def generate_narrative(self, iscn: str, sample_type: str, chn_code: str,
                           counts: dict, max_intentos: int | None = None) -> dict:
        """Genera el borrador narrativo como objeto tipado, con reintento.

        Un LLM es una función no confiable: puede devolver prosa donde se pidió
        JSON, u omitir campos. Por eso se le pide un esquema (`response_format`)
        y, si la respuesta no valida, **se reintenta pasándole el error** para
        que se autocorrija. Solo se reintenta el fallo de contrato; un fallo de
        red va directo al circuit breaker.

        Devuelve {text, structured, model, tokens, latency_ms, intentos}.
        Lanza LlmServiceError; el llamador degrada sin bloquear (RN-07).
        """
        if not getattr(settings, 'CLINIC_LLM_ENABLED', False):
            raise LlmServiceError('llm_disabled')
        if self._circuit_open():
            raise LlmServiceError('circuit_open')

        try:
            from openai import OpenAI          # import perezoso: el SDK es opcional
        except ImportError as exc:
            raise LlmServiceError('sdk_no_instalado') from exc

        intentos_max = max_intentos or self.max_intentos
        started = time.time()
        mensajes = [
            {'role': 'system', 'content': SYSTEM_PROMPT},
            {'role': 'user', 'content': self._build_prompt(iscn, sample_type, chn_code, counts)},
        ]
        tokens_totales = 0
        ultimo_error = None

        try:
            # Ollama no valida la api_key, pero el SDK exige que exista.
            client = OpenAI(base_url=self.base_url, api_key='ollama', timeout=self.timeout)

            for intento in range(1, intentos_max + 1):
                resp = client.chat.completions.create(
                    model=self.model,
                    messages=mensajes,
                    response_format=NARRATIVA_JSON_SCHEMA,
                    temperature=0.2,           # baja: registro clínico, no creatividad
                    max_tokens=700,            # el objeto ocupa más que el párrafo suelto
                )
                usage = getattr(resp, 'usage', None)
                tokens_totales += getattr(usage, 'total_tokens', 0) or 0
                crudo = resp.choices[0].message.content

                try:
                    narrativa = self._parse_structured(crudo, iscn)
                except LlmServiceError as exc:
                    ultimo_error = str(exc)
                    logger.warning('LLM intento %d/%d rechazado: %s',
                                   intento, intentos_max, ultimo_error)
                    if intento == intentos_max:
                        break
                    # Reintento con el error en el contexto: el modelo se corrige
                    # mejor viendo qué falló que repitiendo el prompt original.
                    mensajes += [
                        {'role': 'assistant', 'content': crudo or ''},
                        {'role': 'user', 'content': (
                            f'Tu respuesta fue rechazada: {ultimo_error}. '
                            f'Corrígela respetando el esquema y usando ÚNICAMENTE las '
                            f'anomalías presentes en el ISCN {iscn}.'
                        )},
                    ]
                    continue

                self._record_success()
                return {
                    'text': narrativa.como_texto(),
                    'structured': narrativa.model_dump(mode='json'),
                    'model': self.model,
                    'tokens': tokens_totales,
                    'latency_ms': int((time.time() - started) * 1000),
                    'intentos': intento,
                }

            # Agotados los reintentos: el servicio responde, el contenido no sirve.
            raise LlmServiceError(f'tras {intentos_max} intentos: {ultimo_error}')
        except LlmServiceError:
            # Alucinación o longitud: el modelo respondió, el servicio está sano.
            # No cuenta como fallo de disponibilidad → no abre el circuito.
            raise
        except Exception as exc:
            self._record_failure()
            logger.warning('LLM no disponible: %s', exc)
            raise LlmServiceError(str(exc)) from exc


llm_client = LlmClient(
    base_url=getattr(settings, 'CLINIC_LLM_URL', 'http://localhost:11434/v1'),
    model=getattr(settings, 'CLINIC_LLM_MODEL', 'llama3.2:3b'),
    timeout=float(getattr(settings, 'CLINIC_LLM_TIMEOUT', 240.0)),
    threshold=int(getattr(settings, 'CLINIC_LLM_CIRCUIT_THRESHOLD', 3)),
    cooldown=int(getattr(settings, 'CLINIC_LLM_CIRCUIT_COOLDOWN', 120)),
    max_intentos=int(getattr(settings, 'CLINIC_LLM_MAX_INTENTOS', 2)),
)
