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
import re
import time

from django.conf import settings

logger = logging.getLogger(__name__)

# Anomalías que el texto podría afirmar: numéricas (+21, -18) y estructurales.
_ANOMALY_RE = re.compile(r'[+-]\d{1,2}\b|\b(?:del|dup|inv|t|der|add)\s*\(', re.IGNORECASE)
# Cota de longitud del borrador (ADR-0024 D4.2).
_MIN_CHARS = 40
_MAX_CHARS = 2000

SYSTEM_PROMPT = (
    'Eres un asistente de redacción para un laboratorio de citogenética. '
    'Recibes una nomenclatura ISCN ya calculada y validada por un analista humano. '
    'Tu única tarea es redactar un párrafo interpretativo en español para el informe.\n\n'
    'REGLAS ESTRICTAS:\n'
    '1. NO inventes ni infieras anomalías que no estén en el ISCN recibido.\n'
    '2. NO recuentes ni cuestiones el ISCN: es un dato ya verificado.\n'
    '3. NO emitas diagnóstico definitivo ni recomendación terapéutica.\n'
    '4. Redacta 2 a 4 frases, en registro clínico formal y sobrio.\n'
    '5. Si el cariotipo es normal, dilo de forma directa y breve.\n'
    '6. Cierra indicando que el resultado requiere correlación clínica.'
)


class LlmServiceError(Exception):
    """El servicio LLM no está disponible o devolvió algo inutilizable."""


class LlmClient:
    def __init__(self, base_url: str, model: str, timeout: float, threshold: int, cooldown: int):
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.threshold = threshold
        self.cooldown = cooldown
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

    def _validate(self, text: str, iscn: str) -> str:
        """Valida la salida antes de aceptarla (ADR-0024 D4).

        La defensa central: el texto no puede afirmar anomalías ausentes del ISCN.
        Es heurística, no garantía formal — por eso ADR-0024 D3 exige además
        revisión humana antes de que el borrador llegue al informe.
        """
        text = (text or '').strip()
        if not (_MIN_CHARS <= len(text) <= _MAX_CHARS):
            raise LlmServiceError(f'longitud fuera de rango: {len(text)}')

        iscn_norm = iscn.replace(' ', '').lower()
        for match in _ANOMALY_RE.findall(text):
            token = match.strip().replace(' ', '').lower()
            if token and token not in iscn_norm:
                raise LlmServiceError(f'alucinación: "{match.strip()}" no está en el ISCN')
        return text

    def generate_narrative(self, iscn: str, sample_type: str, chn_code: str, counts: dict) -> dict:
        """Genera el borrador narrativo. Devuelve {text, model, tokens, latency_ms}.

        Lanza LlmServiceError ante cualquier problema; el llamador degrada sin
        bloquear el informe (RN-07).
        """
        if not getattr(settings, 'CLINIC_LLM_ENABLED', False):
            raise LlmServiceError('llm_disabled')
        if self._circuit_open():
            raise LlmServiceError('circuit_open')

        try:
            from openai import OpenAI          # import perezoso: el SDK es opcional
        except ImportError as exc:
            raise LlmServiceError('sdk_no_instalado') from exc

        started = time.time()
        try:
            # Ollama no valida la api_key, pero el SDK exige que exista.
            client = OpenAI(base_url=self.base_url, api_key='ollama', timeout=self.timeout)
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': SYSTEM_PROMPT},
                    {'role': 'user', 'content': self._build_prompt(iscn, sample_type, chn_code, counts)},
                ],
                temperature=0.2,               # baja: registro clínico, no creatividad
                max_tokens=400,
            )
            text = self._validate(resp.choices[0].message.content, iscn)
            self._record_success()
            usage = getattr(resp, 'usage', None)
            return {
                'text': text,
                'model': self.model,
                'tokens': getattr(usage, 'total_tokens', 0) or 0,
                'latency_ms': int((time.time() - started) * 1000),
            }
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
)
