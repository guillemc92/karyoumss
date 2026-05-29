# 📄 Especificación Técnica: FSD-UC-001 — Procesamiento Asíncrono de Muestra

## 🟢 CAPA 1 — SPEC (Alto Nivel)

### 🔄 Flujo Funcional
1. **Registro de muestra:** Asignación obligatoria de código **CHN** para anonimización.
2. **Ingesta de imagen:** Carga de archivo TIFF/PNG ($\le 50\text{MB}$) y almacenamiento en S3.
3. **Procesamiento IA asíncrono:** Ejecución de pipeline de segmentación y clasificación en segundo plano.
4. **Generación de resultados:** Producción de 46 cromosomas con sus respectivos **scores de confianza (Softmax)**.
5. **Validación HITL obligatoria:** Marcado de revisión manual para todo cromosoma con $\text{score} < 0.85$.
6. **Auditoría y persistencia:** Registro de resultados en base de datos y trazabilidad de cambios.

### 📊 Estados del Proceso
| Estado | Descripción | Transición |
| :--- | :--- | :--- |
| `queued` | Imagen recibida y en cola de Redis | $\to$ `processing` |
| `processing` | Motor de IA ejecutando inferencia | $\to$ `ready_ai` / `error` |
| `ready_ai` | Resultado generado y disponible para el analista | $\to$ `validated` |
| `validated` | Analista ha revisado y aceptado los resultados | $\to$ `audited` |
| `audited` | Cambios registrados en el Audit Trail inalterable | Final |

### 🛡️ Reglas Críticas
- **RN-03 (Privacidad):** Anonimización obligatoria vía CHN. Ningún dato PII debe salir del entorno local hacia S3 o TorchServe.
- **HITL (Semaforización):** Si $\text{confidence} < 0.85$, el sistema **DEBE** obligar a la validación humana.
- **Bloqueo de Reporte:** No se permite la exportación del informe final si existen cromosomas no validados.

---

## ⚙️ CAPA 2 — IMPLEMENTATION / ADR (Detalle Técnico)

### 🛠️ Pipeline de Procesamiento de Imagen
- **Pre-procesamiento:** Implementación de **CLAHE** (`clipLimit=3.0`, `tileGridSize=8x8`) para normalización de contraste.
- **Tiling (ADR-0001):** División de imágenes $> 4\text{K}$ en tiles de $1024 \times 1024\text{px}$ con un **overlap de $64\text{px}$** para evitar pérdida de datos en bordes.
- **Segmentación:** Uso de **U-Net** vía TorchServe para la generación de polígonos y bounding boxes.
- **Post-procesamiento:** Aplicación de **NMS (Non-Maximum Suppression)** para fusionar detecciones redundantes en las zonas de overlap de los tiles.
- **Clasificación:** Uso de **EfficientNet-B3** para asignar el par cromosómico y calcular el score de confianza mediante función Softmax.

### 🚀 Configuración de Infraestructura e IA
- **Serving:** TorchServe / NVIDIA Triton con batching optimizado.
- **Hardware:** Mínimo 8GB VRAM NVIDIA.
- **Orquestación:** FastAPI $\to$ Redis (Broker) $\to$ Celery (Worker).
- **SLA:** Tiempo de respuesta p95 $\le 15$ segundos por muestra.

### 🔌 Contratos de Interfaz (API)
- `POST /samples/{id}/image`: Recibe `multipart/form-data`, retorna `202 Accepted`.
- `GET /samples/{id}/chromosomes`: Retorna lista de objetos `ChromosomeDetail` con `confidence_score` y `polygon_coords`.
- **WebSocket:** Evento push `{sample_id, status: "ready"}` al finalizar el worker de Celery.

### 💾 Persistencia y Auditoría
- **PostgreSQL:** Almacenamiento de resultados en tabla `chromosomes`.
- **Audit Trail:** Registro de cada edición manual en la tabla `edits` mediante operaciones de **Solo INSERT** (prohibido UPDATE/DELETE).
