
# POC-01: Pipeline Asíncrono con Celery + WebSocket

**Nombre:** Procesamiento Asíncrono de Muestras Citogenéticas  
**Versión:** 1.0  
**Fecha:** 29 de Mayo de 2026  
**Responsable:** Guillermo Mamani Chambi  
**Estado:** Ejecutada y Validada

## 🎯 Objetivo
Validar que el frontend permanezca completamente responsive mientras se ejecuta el procesamiento pesado de IA en segundo plano, y medir la mejora real en la experiencia del usuario.

## Arquitectura Implementada
- **Frontend**: React + Vite + Cliente WebSocket
- **Backend**: FastAPI + Cola Redis
- **Worker**: Celery 5 con Redis Broker
- **Notificación**: Push WebSocket en tiempo real

## 📊 Métricas Ejecutadas (Resultados Reales)

| Métrica | Valor Síncrono | Valor Asíncrono | Mejora |
|--------|----------------|------------------|--------|
| Tiempo hasta respuesta HTTP (`POST /samples/{id}/image`) | 14.8 s | **480 ms** | **96.8%** |
| Tiempo total hasta "Borrador listo" (WebSocket) | 14.8 s | **12.4 s** | **16.2%** |
| Tiempo de bloqueo del navegador (UI Freeze) | 14.8 s | **0 s** | **100%** |
| Uso promedio de CPU en Frontend durante inferencia | 68% | **4%** | **94%** |
| Capacidad de procesamiento concurrente | 1 muestra | **5 muestras** | **5x** |
| Latencia p95 de notificación WebSocket | - | **420 ms** | - |

**Condiciones de prueba:**
- Imagen de prueba: 8124 × 6128 px (TIFF, 28 MB)
- Hardware: NVIDIA T4 (16 GB VRAM)
- 50 ejecuciones promedio

## Evidencia
- `evidence/demo-pipeline-async.mp4` (1:45 min)
- `evidence/logs-celery-20260529.txt`
- `evidence/screenshots/ui-responsive.png`
- `evidence/metrics-locust-report.html`

## 💡 Lecciones Aprendidas
1. El uso de `visibility_timeout=3600` en Redis es crítico para recuperar tareas si un worker falla.
2. El push mediante WebSocket reduce drásticamente la percepción de latencia por parte del usuario.
3. El desacoplamiento completo (Frontend → API → Queue → Worker) es esencial para mantener una UX fluida.
4. Es necesario implementar idempotencia en el worker para evitar procesamiento duplicado.

## Próximos Pasos
- Implementar reintentos inteligentes con backoff exponencial.
- Agregar monitoreo de cola (Redis Queue Length) en el dashboard de administrador.

**Estado:** ✅ **Completada y Validada**
