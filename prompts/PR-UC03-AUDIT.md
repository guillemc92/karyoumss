# Prompt: Middleware FastAPI — Audit Trail de Ediciones

## Metadata
* **ID:** PR-UC03-AUDIT
* **Componente:** `backend/app/middleware/audit_trail.py`
* **Objetivo:** Registrar en base de datos cada corrección manual en la mesa de edición de forma inalterable.

## Prompt Cuerpo
```
Role: Eres un desarrollador backend especializado en FastAPI con experiencia en sistemas de auditoría para aplicaciones clínicas.

Task: Implementa el middleware AuditTrailMiddleware para FastAPI que:
1. Intercepta todos los requests PATCH a /chromosomes/{id}/*
2. Captura el estado before y after
3. Registra en tabla `edits`
4. El registro debe ser INALTERABLE: la tabla edits solo permite INSERT, no UPDATE ni DELETE

Context:
- Stack: FastAPI + SQLAlchemy 2.0 + PostgreSQL 15
- La inalterabilidad se garantiza a nivel de base de datos con: REVOKE UPDATE, DELETE ON edits FROM app_user

Reasoning:
1. Capturar before_state ANTES de ejecutar el endpoint
2. Capturar after_state DESPUÉS
3. Si el endpoint falla, NO registrar

Stop Condition: Detente cuando el middleware capture before/after, la SQL revoque permisos y un test verifique que UPDATE falla.

Output: Código Python + SQL:
- `backend/app/middleware/audit_trail.py`
```
