# Resumen de build y pruebas

## Estado general

- Build: correcto. backend-ml no tiene compilación, y la aplicación importa sin errores.
- Pruebas: 76 de 76 en verde (65 existentes + 11 nuevas).
- Cobertura: 100 % de líneas en `app/concurrencia.py` y `app/main.py`.

## Inventario de tipos de prueba

| Tipo | Generado | Archivo |
|---|---|---|
| Unitarias (lógica + endpoint) | Sí, en code-generation | `backend-ml/tests/test_estado_inferencias.py` |
| Integración | No aplica (Minimal) | `integration-test-instructions.md` |
| Rendimiento | No aplica (sin umbral) | `performance-test-instructions.md` |
| Seguridad | Cubierta por las unitarias de FR4 | `security-test-instructions.md` |

## Cobertura esperada

Al menos 90 % de líneas en el código nuevo (NFR3, RN-09). Real: 100 %.

## Target Verification Matrix

| Target ID | Source | Expected | Actual | Evidence | Owning Stage | Verdict |
|---|---|---|---|---|---|---|
| NFR3-tests-por-FR | `requirements.md` NFR3 | ≥ 1 prueba por FR | 11 pruebas, FR1–FR4 cubiertos | `test-results.md` | build-and-test | Met |
| NFR3-suite-existente | `requirements.md` NFR3; contrato `scope_floor` | 65 en verde | 65 de 65 | `test-results.md` | build-and-test | Met |
| NFR3-cobertura | `requirements.md` NFR3 | ≥ 90 % | 100 % | `test-results.md` | build-and-test | Met |
| TC-minimal-happy-path | Testing Contract | 1 camino feliz por componente | 2 de 2 componentes | `tests/test_estado_inferencias.py` | build-and-test | Met |

## Preparación

- Lista para build: sí.
- Lista para pruebas: sí.
- Lista para desplegar: sí. Antes, hay que añadir `INTERNAL_SERVICE_SECRET` al entorno de backend-ml; si no, el endpoint responde 503.

## Limitaciones y pendientes

- Ningún servicio consume todavía el endpoint (fuera de alcance).
- El aviso `StarletteDeprecationWarning` ya existía antes y no tiene que ver con este cambio.
