# Visión de negocio — karyoumss-main (BIOMED UMSS)

## Dominio

Plataforma de **cariotipado inteligente** para el laboratorio de citogenética de la UMSS (Bolivia). Reemplaza al software legado MetaClass. A partir de una imagen de metafase de microscopio detecta los cromosomas, los clasifica (1–22, X, Y) y apoya al analista para construir el cariotipo y su nomenclatura ISCN. El objetivo final es un informe clínico firmado por un supervisor.

## Propósito y principio rector

La IA **propone** y la persona **decide** (human-in-the-loop). Cada cromosoma recibe una confianza y se semaforiza (verde/naranja). Los naranjas exigen validación manual del analista con explicabilidad (Grad-CAM, BR-004), y el informe exige la firma MFA del supervisor (RN-01/02). Reglas clínicas no negociables, documentadas en `CLAUDE.md`/`AGENTS.md`:

- RN-03: cero fuga de PII (anonimización antes de cualquier salida).
- RN-04/05: el ISCN es de solo lectura tras generarse; las ediciones solo se añaden (*append-only*).
- RN-06: segregación analista ≠ supervisor.
- RN-07: degradación elegante si la IA no está disponible (modo manual).
- RN-08: auditoría aleatoria del 5 % de los verdes.
- RN-09: cobertura de pruebas ≥ 90 % (regla docente).

## Funcionalidad clave

| Área | Servicio | Qué hace |
|---|---|---|
| Inferencia de IA | `backend-ml` | Segmenta la metafase (OpenCV watershed), clasifica cada cromosoma (EfficientNet-B3 v3), genera Grad-CAM y reclasifica un recorte manual. Limita las inferencias simultáneas (DD-AUD-001 F1). |
| Flujo clínico | `backend-clinic` | Registro de muestras con PII cifrada, procesamiento, visor/corrección del cariotipo, auditoría encadenada, ISCN, narrativa con LLM local (Ollama), RAG y agente. |
| Administración | `backend-admin` | Usuarios, RBAC granular, autenticación JWT/SSO, 2FA TOTP, configuración del modelo, notificaciones y apariencia. |
| Interfaces | `frontend-clinic`, `frontend-admin` | SPAs React para el analista/supervisor y para el administrador. |

## Contexto del intent activo

El intent `estado-inferencias` añade a `backend-ml` una consulta de solo lectura del **estado del límite de inferencias** (`maximo`, `en_curso`, `libres`, `espera_max_s`). Su valor de negocio es la observabilidad: saber si el motor está saturado antes de que backend-clinic reciba un 503 y degrade a modo manual (RN-07). Ver el detalle técnico en `api-documentation.md` y `component-inventory.md` (LimiteInferencias).
