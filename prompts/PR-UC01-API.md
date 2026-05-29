# Prompt: POST /samples — Creación de Muestra y CHN

## Metadata
* **ID:** PR-UC01-API
* **Componente:** `backend/app/api/samples.py`
* **Objetivo:** Ingesta de metafase y anonimización de paciente en el borde

## Prompt Cuerpo
```
Role: Eres un desarrollador backend senior especializado en FastAPI con experiencia en sistemas de salud que deben cumplir normativas de privacidad de datos (HIPAA/GDPR equivalente).

Task: Implementa el endpoint POST /samples en FastAPI que:
1. Recibe datos de la muestra (sin datos de paciente en el body del request)
2. Genera automáticamente un código CHN único con formato CHN-YYYY-NNNN
3. Valida que el código CHN sea único en PostgreSQL
4. Retorna 201 Created con el CHN asignado y el sample_id UUID

Context:
- Stack: FastAPI + SQLAlchemy 2.0 + Pydantic v2 + PostgreSQL 15
- Modelo de datos: tabla `samples` con campos (id UUID PK, chn_code VARCHAR(20) UNIQUE, status ENUM, analyst_id UUID FK, created_at TIMESTAMP)
- El formato CHN debe ser: CHN-{AÑO_4_DÍGITOS}-{NÚMERO_4_DÍGITOS_SECUENCIAL}
- Restricción crítica: NUNCA registrar datos del paciente (nombre, edad, DNI) en este endpoint
- El endpoint debe requerir autenticación JWT con rol "analista"

Reasoning:
1. Verificar unicidad del CHN antes de insertar
2. Si colisión de CHN, reintentar con número siguiente
3. Registrar en audit log la creación de la muestra
4. Retornar 409 si el analyst_id no tiene rol "analista"

Stop Condition: Detente cuando el endpoint pase los tests unitarios de: creación exitosa, unicidad CHN, autenticación requerida y rechazo de datos de paciente en el body.

Output: Formato JSON Schema + bloque de código Python:
{
  "endpoint": "POST /samples",
  "request_body": { ... },
  "response_201": { "sample_id": "uuid", "chn_code": "CHN-2026-0001" },
  "response_409": { "detail": "CHN collision, retry" }
}
```
