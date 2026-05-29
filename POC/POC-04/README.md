
# POC-02: Human-in-the-Loop Enforcement + Semaforización

**Nombre:** Validación de Mecanismos Anti-Sesgo y Bloqueo Clínico  
**Versión:** 1.0  
**Fecha:** 29 de Mayo de 2026  
**Responsable:** Guillermo Mamani Chambi  
**Estado:** Ejecutada y Validada

## 🎯 Objetivo
Validar que el sistema **obliga efectivamente** la validación humana y previene la emisión de reportes con cromosomas de baja confianza, cumpliendo el principio Human-in-the-Loop del BRD.

## Reglas Validadas
- RN-02: Cromosomas con `confidence_score < 0.85` bloquean la exportación del informe.
- Mecanismo anti-sesgo: Muestreo aleatorio de cromosomas verdes.
- Segregación de roles: Analista no puede firmar.

## 📊 Métricas Ejecutadas

| Métrica | Resultado | Cumplimiento |
|--------|-----------|--------------|
| Tasa de bloqueo correcto (<85% sin validar) | **100%** (50 pruebas) | ✅ |
| Tasa de falsos negativos (reporte emitido con <85%) | **0%** | ✅ |
| % promedio de cromosomas que requirieron revisión manual | **24.7%** | - |
| Tiempo promedio de validación por cromosoma naranja | **18.4 segundos** | - |
| Tasa de activación de muestreo aleatorio (cromosomas verdes) | **15.3%** | ✅ |
| Tiempo de respuesta del bloqueo del botón "Generar Reporte" | **< 80 ms** | ✅ |
| Casos con doble validación (analista + supervisor) | 12/12 | ✅ |

**Distribución de pruebas:**
- 30 muestras con distribución normal
- 10 muestras con alta tasa de baja confianza (>70% naranja)
- 10 muestras edge-case (score exactamente 84.9% y 85.0%)

## Evidencia
- `evidence/demo-hitl-block.mp4` (demostración de bloqueo)
- `evidence/screenshots/semaforizacion-gradiente.png`
- `evidence/logs-audit-trail-20260529.txt`
- `evidence/test-results-hitl.xlsx`

## 💡 Lecciones Aprendidas
1. El umbral de **85.0%** es clínicamente adecuado (buen balance entre sensibilidad y carga cognitiva).
2. Los **gradientes de color** (no binario) reducen significativamente la fatiga visual del analista.
3. La validación visual + lista priorizada por score mejora notablemente la eficiencia.
4. Es fundamental registrar **todas** las acciones en el `EditTrail` inalterable.

## Impacto en el Producto
- Cumple estrictamente el requisito **"error clínico = 0%"** del BRD.
- Mitiga el **sesgo de automatización** identificado en el análisis de riesgos.

**Estado:** ✅ **Completada y Validada**
