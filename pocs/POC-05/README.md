# POC-03: Anonimización CHN en el Borde (Privacy by Design)

**Nombre:** Implementación y Validación del Sistema de Anonimización CHN  
**Versión:** 1.0  
**Fecha:** 29 de Mayo de 2026  
**Responsable:** Guillermo Mamani Chambi  
**Estado:** Ejecutada y Validada

## 🎯 Objetivo
Validar que el sistema cumpla estrictamente con la regla **RN-03** (Anonimización obligatoria), asegurando que ningún dato de identificación personal (PII) llegue al motor de IA ni al almacenamiento en la nube.

## 🛠️ Implementación
- **Momento de ejecución:** Antes de cualquier transmisión hacia S3/MinIO o TorchServe.
- **Formato CHN:** `CHN-YYYY-MM-DD-NNNN` (ej: `CHN-2026-05-29-0047`)
- **Mecanismo:** Middleware en FastAPI que intercepta requests y reemplaza metadata sensible.
- **Validación:** Scanner automático de PII en headers, body y logs.

## 📊 Métricas y Resultados

| Métrica | Resultado | Cumplimiento |
|---------|-----------|--------------|
| Tasa de anonimización exitosa | **100%** (120 pruebas) | ✅ |
| Tasa de fuga de PII detectada | **0%** | ✅ |
| Tiempo adicional por anonimización | **8.4 ms** | Aceptable |
| Unicidad de códigos CHN generados | **100%** (sin colisiones) | ✅ |
| Casos donde se detectó y bloqueó PII | 27/120 | - |
| Cumplimiento RN-03 (ningún PII en TorchServe) | **100%** | ✅ |

**Tipos de PII probados:**
- Nombre completo del paciente
- Fecha de nacimiento
- Número de historia clínica
- DNI / CI
- Metadata en headers HTTP

## Evidencia
- `evidence/demo-anonimizacion.mp4` (demostración en tiempo real)
- `evidence/logs-pii-scanner-20260529.txt`
- `evidence/screenshots/before-after-chn.png`
- `evidence/test-privacy-audit-report.pdf`

## 💡 Lecciones Aprendidas
1. La anonimización **en el borde** (antes de cualquier llamada externa) es mucho más segura que hacerlo dentro del worker de Celery.
2. El formato `CHN-YYYY-MM-DD-NNNN` es simple, trazable y suficiente para requerimientos regulatorios bolivianos.
3. Implementar un **PII Scanner** automático en el middleware evita fugas por error humano o descuido del desarrollador.
4. Es fundamental registrar el evento de anonimización en el **Audit Trail** inalterable.

## Impacto en el Producto
- Cumple con **Ley 164 de Protección de Datos** (Bolivia) y buenas prácticas de privacidad en sistemas clínicos.
- Reduce significativamente el riesgo legal y ético del proyecto.
- Sirve como base sólida para futuras integraciones con hospitales (LIS).

**Estado:** ✅ **Completada y Validada**

