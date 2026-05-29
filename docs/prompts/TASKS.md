# TASKS — FSD-UC-001: Procesamiento Asíncrono de Muestra
## BIOMED UMSS — Pipeline de Inferencia IA

> **Formato de cada tarea:**
> - Descripción clara de QUÉ hacer
> - Criterio de aceptación (verificable)
> - Comportamiento observable (output esperado)

---

## 📦 Sprint 0: Infraestructura Base (Setup)

### TASK-001: Configurar docker-compose con servicios core
- Levantar PostgreSQL 15 con volumen persistente
- Levantar Redis 7 como broker de mensajes
- Levantar MinIO (S3-compatible) para almacenamiento de imágenes
- Configurar red común entre servicios
- **Criterio:** `docker compose up -d` ejecuta sin errores y `docker compose ps` muestra 3 servicios con estado "healthy" o "running"
- **Output esperado:** 
```bash
$ docker compose ps
postgres running (healthy)
redis running
minio running (healthy)
```

### TASK-002: Crear scaffold del proyecto FastAPI
- Crear estructura `backend/app/{api,core,domain,services,tasks,ws,db}`
- Crear `backend/app/main.py` con FastAPI app y health check endpoint
- Configurar CORS para frontend
- **Criterio:** `GET /health` retorna `{"status": "ok"}`
- **Output esperado:** 
```json
{"status": "ok", "version": "0.1.0"}
```

### TASK-003: Configurar SQLAlchemy y conexión a PostgreSQL
- Configurar `DATABASE_URL` desde variable de entorno
- Crear base `Base = declarative_base()`
- Implementar `get_db()` como dependencia de FastAPI
- **Criterio:** La aplicación puede conectarse a PostgreSQL y ejecutar `SELECT 1` sin errores
- **Output esperado:** Log en consola: `"Connected to PostgreSQL at postgres:5432"`

---

## 🗄️ Sprint 1: Base de Datos y Modelos

### TASK-010: Implementar modelo Sample
- Crear tabla `samples` con campos: `id` (UUID), `chn_code` (str UNIQUE), `s3_path` (str), `status` (Enum), `analyst_id` (UUID), `created_at`, `processed_at`
- Implementar enum `SampleStatus` con valores: `queued`, `processing`, `ready`, `error`
- **Criterio:** SQLAlchemy puede crear la tabla en PostgreSQL y hacer INSERT de un registro de prueba
- **Output esperado:**
```sql
INSERT INTO samples (id, chn_code, status) VALUES (...) RETURNING id;
→ (uuid, 'CHN-2026-05-27-0001', 'queued')
```

### TASK-011: Implementar modelo Chromosome
- Crear tabla `chromosomes` con campos: `id` (UUID), `sample_id` (FK), `pair_number` (int), `confidence_score` (float), `polygon_coords` (JSON), `requires_review` (bool), `validated` (bool), `validated_at`
- Establecer relación con Sample (one-to-many)
- **Criterio:** Se puede insertar un cromosoma asociado a un sample existente
- **Output esperado:**
```sql
INSERT INTO chromosomes (sample_id, pair_number, confidence_score) 
VALUES (...) RETURNING id;
→ (uuid, 21, 0.94)
```

### TASK-012: Implementar modelo EditTrail (inalterable)
- Crear tabla `edits` con campos: `id` (UUID), `chromosome_id` (FK), `user_id` (UUID), `action` (Enum), `before_state` (JSON), `after_state` (JSON), `created_at` (DEFAULT NOW())
- Configurar permisos: `REVOKE UPDATE, DELETE ON edits FROM app_user`
- **Criterio:** Solo se permite INSERT; UPDATE y DELETE deben fallar con error de permisos
- **Output esperado:**
```sql
UPDATE edits SET action='rotate' WHERE id='...';
→ ERROR: permission denied for table edits
```

---

## 🔐 Sprint 2: Anonimización y CHN

### TASK-020: Implementar CHNService - generación de código único
- Formato: `CHN-YYYY-MM-DD-NNNN` (ej: `CHN-2026-05-27-0042`)
- Verificar unicidad en tabla `samples` antes de retornar
- Si hay colisión, incrementar número secuencial y reintentar (máx 3 veces)
- **Criterio:** Genera códigos únicos secuenciales por día
- **Output esperado:**
```python
await chn_service.generate() 
→ "CHN-2026-05-27-0042"
```

### TASK-021: Implementar middleware de anonimización (RN-03)
- Interceptar cualquier request saliente a TorchServe o S3
- Reemplazar metadata PII por código CHN
- Loggear advertencia si se detecta PII en logs
- **Criterio:** Ninguna llamada externa contiene nombre de paciente, DNI o fecha de nacimiento
- **Output esperado:**
```text
[WARNING] PII detected in request header: 'patient_name' → sanitized to CHN-2026-05-27-0001
```

### TASK-022: Implementar endpoint POST /samples con CHN
- Recibir `{analyst_id}` en body (JWT se usará después)
- Generar CHN vía `CHNService`
- Crear registro en tabla `samples` con status `queued`
- Retornar `201 Created` con `sample_id` y `chn_code`
- **Criterio:** Cada request crea un sample único con CHN no repetido
- **Output esperado:**
```json
POST /api/v1/samples → 201
{"sample_id": "abc-123", "chn_code": "CHN-2026-05-27-0001", "status": "queued"}
```

---

## ☁️ Sprint 3: Almacenamiento y Carga de Imágenes

### TASK-030: Configurar cliente S3 (boto3) para MinIO
- Configurar endpoint, access key, secret key desde variables de entorno
- Crear bucket `biomed-images` si no existe
- Implementar `upload_file(bucket, key, file_path)` y `download_file(bucket, key)`
- **Criterio:** Puede subir y descargar un archivo de prueba desde/hacia MinIO
- **Output esperado:**
```text
$ python test_s3.py
✅ Uploaded test.txt to biomed-images/test.txt
✅ Downloaded test.txt from biomed-images/test.txt
```

### TASK-031A: Validar imagen antes de procesar
- Verificar formato (TIFF/PNG/JPEG, máx 50MB)
- Verificar dimensiones ($\ge 1024 \times 1024$ píxeles)
- Verificar DPI ($\ge 300$ para calidad clínica)
- Retornar 422 si cualquier validación falla
- **Criterio:** Imagen corrupta o inválida nunca llega a S3 ni DB
- **Output esperado:**
```json
{"valid": false, "errors": ["Image too small: 800x600 < 1024x1024", "DPI too low: 72 < 300"]}
```

### TASK-031B: Subir imagen a S3 con path basado en CHN
- Generar path: `{chn_code}/{timestamp}.{ext}`
- Subir usando boto3 con multipart upload para archivos $> 10\text{MB}$
- Implementar reintentos (máx 3) con backoff
- Retornar `s3_path` si éxito, `None` si falla
- **Criterio:** Imagen almacenada en S3, path en DB
- **Output esperado:**
```python
s3_path = await upload_to_s3(image_bytes, chn_code, ext)
# → "CHN-2026-05-27-0001/20260527_103000.tiff"
```

### TASK-031C: Actualizar sample.s3_path en DB
- Recibir `sample_id` y `s3_path`
- Ejecutar `UPDATE samples SET s3_path = :path, status = 'queued' WHERE id = :id`
- Retornar `True` si actualización exitosa
- **Criterio:** La ruta S3 persiste incluso si falla el pipeline
- **Output esperado:**
```sql
UPDATE samples SET s3_path='...', status='queued' WHERE id='abc-123';
→ UPDATE 1
```

### TASK-031D: Encolar tarea en Redis y retornar 202
- Crear mensaje `{sample_id, s3_path, chn_code, submitted_at}`
- Publicar en `inference_queue`
- Retornar `{"sample_id": "...", "task_id": "...", "status": "queued"}`
- **Criterio:** API retorna en $< 500\text{ms}$ (no espera procesamiento)
- **Output esperado:**
```json
HTTP/1.1 202 Accepted
{"sample_id": "abc-123", "task_id": "celery-456", "status": "queued"}
```

### TASK-031E: Rollback transaccional (si algo falla)
- Si S3 falla $\to$ no actualizar DB, retornar 500
- Si DB falla $\to$ eliminar imagen de S3 (limpieza)
- Usar patrón Saga coreografía entre S3 y DB
- **Criterio:** Estado consistente siempre (S3 y DB sincronizados)
- **Output esperado:**
```python
try:
    s3_path = await upload_to_s3(...)
    await db.update_sample_path(sample_id, s3_path)
except Exception as e:
    if s3_path:
        await s3.delete(s3_path)  # rollback
    raise HTTPException(500, str(e))
```

---

## ⚙️ Sprint 4: Pipeline Asíncrono (Celery + Redis)

### TASK-040: Configurar Celery app con Redis broker
- Crear `backend/app/tasks/worker.py` con Celery app
- Configurar `broker_url = redis://redis:6379/0`
- Configurar `result_backend = redis://redis:6379/0`
- **Criterio:** Celery worker se conecta a Redis y muestra `connected to redis://redis:6379/0`
- **Output esperado:**
```text
$ celery -A app.tasks.worker worker --loglevel=info
[2026-05-27 10:00:00] Connected to redis://redis:6379/0
```

### TASK-041: Definir schema de mensaje para la cola
- Crear clase Pydantic `InferenceTask` con campos: `sample_id` (UUID), `s3_path` (str), `chn_code` (str), `submitted_at` (datetime)
- **Criterio:** Mensaje puede serializarse a JSON y deserializarse sin pérdida
- **Output esperado:**
```python
task = InferenceTask(sample_id=uuid4(), s3_path="CHN-2026-.../image.tiff")
json.dumps(task.dict()) → '{"sample_id": "...", "s3_path": "..."}'
```

### TASK-042: Implementar endpoint que encola tarea en Redis
- Al recibir `POST /samples/{id}/image`, crear mensaje `InferenceTask`
- Publicar mensaje en Redis queue `inference_queue`
- Retornar `task_id` (ID de Celery)
- **Criterio:** Mensaje aparece en Redis después del request
- **Output esperado:**
```bash
$ redis-cli LRANGE inference_queue 0 -1
1) '{"sample_id": "abc-123", "s3_path": "CHN-.../image.tiff"}'
```

### TASK-043: Implementar consumidor básico de Celery
- Crear tarea `@celery.task(bind=True, name="process_inference")`
- Recibir mensaje `{sample_id, s3_path}`
- Imprimir payload en consola
- Actualizar estado de la tarea en Redis
- Retornar ACK al broker automáticamente
- **Criterio:** Consumidor imprime el mensaje recibido y retorna ACK
- **Output esperado:**
```text
[2026-05-27 10:00:05] Received task: process_inference[abc-123]
[2026-05-27 10:00:05] Payload: {'sample_id': 'abc-123', 's3_path': '...'}
[2026-05-27 10:00:05] Task process_inference[abc-123] succeeded in 0.01s
```

### TASK-044: Implementar tolerancia a fallos del pipeline (ADR-0002)
#### 044-A: Reintentos con backoff exponencial
- Configurar Celery task con `autoretry_for=(Exception,)`
- Parámetros: `retry_kwargs={'max_retries': 3}`, `retry_backoff=True`, `retry_backoff_max=60`
- **Criterio:** Task se reintenta 3 veces antes de fallar definitivamente
- **Output esperado:** 
```text
[ERROR] Task process_inference[abc-123] failed (attempt 1/3): ConnectionError to TorchServe
[INFO] Retrying in 4 seconds...
[ERROR] Task process_inference[abc-123] failed after 3 retries. Marking as FAILED.
```

#### 044-B: Timeout por componente (ADR-0002 §3.2)
- U-Net segmentación: timeout 10s
- EfficientNet clasificación: timeout 5s
- CLAHE pre-procesamiento: timeout 5s
- **Criterio:** Si cualquier componente excede timeout, tarea se reintenta (no queda colgada)
- **Output esperado:** 
```python
@celery.task(timeout=30, soft_timeout=25)
def process_inference(self, sample_id, s3_path):
    try:
        result = torchserve_client.segment(image, timeout=10)
    except TimeoutError:
        self.retry(countdown=5, exc=TimeoutError("U-Net timeout"))
```

#### 044-C: Estado "error" consistente
- Si fallan todos los reintentos $\to$ `samples.status = "error"`
- Guardar `error_message` y `error_timestamp` en columna `error_log`
- Publicar WebSocket `{status: "error", reason: "Inference failed after 3 retries"}`
- **Criterio:** No hay estados "zombie" (quedados en processing para siempre)
- **Output esperado:**
```sql
SELECT status, error_log FROM samples WHERE id='abc-123';
→ 'error', '{"attempts": 3, "last_error": "TorchServe timeout", "timestamp": "2026-05-27T10:30:00Z"}'
```

#### 044-D: Recovery de Redis restart
- Usar Celery with Redis con `visibility_timeout=3600` (1 hora)
- Si worker muere, tarea vuelve a la cola después de `visibility_timeout`
- Configurar `result_backend` con persistencia RDB
- **Criterio:** Si Redis se reinicia, las tareas pendientes se recuperan
- **Output esperado:**
```yaml
# celeryconfig.py
broker_transport_options = {
    'visibility_timeout': 3600,
    'queue_order_strategy': 'round_robin'
}
result_backend_transport_options = {
    'master_name': 'mymaster',
    'retry_policy': {'timeout': 5.0}
}
```

#### 044-E: Idempotencia en procesamiento
- Antes de procesar, verificar `samples.status`:
    - Si `status == "processing"` y `updated_at < NOW() - 15min` $\to$ asumir worker muerto y reprocesar
    - Si `status == "ready"` o `"error"` $\to$ no reprocesar
- Usar `sample.lock` con Redis distributed lock (TTL 30s) para evitar duplicados
- **Criterio:** Una misma muestra nunca se procesa dos veces concurrentemente
- **Output esperado:**
```python
with redis_lock(f"sample_lock_{sample_id}", timeout=30):
    sample = db.query(Sample).filter_by(id=sample_id).first()
    if sample.status in ['ready', 'error']:
        return {"skipped": True, "reason": f"Already {sample.status}"}
    sample.status = "processing"
    db.commit()
```

---

## 🧠 Sprint 5: Pipeline de IA (Segmentación + Clasificación)

### TASK-050: Implementar cliente HTTP para TorchServe
- Crear `TorchServeClient` con métodos `segment(image)` y `classify(crops)`
- Configurar timeout de 30 segundos por request
- Implementar reintentos (máx 3) con backoff exponencial
- **Criterio:** Cliente puede enviar request a TorchServe mock y recibir respuesta
- **Output esperado:**
```python
client = TorchServeClient("http://torchserve:8080")
result = await client.segment(image_bytes)
→ {"predictions": [{"bbox": [x1,y1,x2,y2], "mask": "base64..."}]}
```

### TASK-051: Implementar pre-procesamiento CLAHE
- Aplicar CLAHE con parámetros: `clipLimit=3.0`, `tileGridSize=(8,8)`
- Convertir imagen a escala de grises si es RGB
- Normalizar intensidades a $[0,1]$
- **Criterio:** La imagen procesada tiene mayor contraste en bandas G
- **Output esperado:** La imagen resultante tiene histograma más plano y bandas más visibles

### TASK-052: Implementar tiling para imágenes $>4\text{K}$ (ADR-0001)
- Verificar dimensiones: si ancho $> 4000$ o alto $> 4000$
- Dividir en tiles de $1024 \times 1024$ con overlap de $64\text{px}$
- Calcular coordenadas de cada tile en sistema original
- **Criterio:** Para imagen $8000 \times 6000$, se generan $\sim 63$ tiles ($9 \times 7$)
- **Output esperado:**
```python
tiles = split_into_tiles(image, tile_size=1024, overlap=64)
len(tiles) → 63
tiles[0]['bbox'] → (0, 0, 1024, 1024)  # tile 0,0
tiles[62]['bbox'] → (7040, 5056, 8064, 6080)  # tile 8,6 con padding
```

### TASK-053: Integrar U-Net para segmentación
- Para cada tile, llamar a TorchServe `POST /predictions/unet`
- Recibir máscaras y bounding boxes de cromosomas
- Almacenar coordenadas relativas al tile
- **Criterio:** Se detectan cromosomas en cada tile con $\text{IoU} > 0.90$
- **Output esperado:**
```json
{"chromosomes": [
  {"id": a "chrom_001", "bbox": [120, 340, 215, 550], "confidence": 0.96}
]}
```

### TASK-054: Implementar NMS para ensamblado de tiles
- Convertir coordenadas relativas a absolutas (sistema original)
- Aplicar Non-Maximum Suppression con $\text{IoU threshold} = 0.5$
- Fusionar detecciones duplicadas en zonas de overlap
- **Criterio:** No hay cromosomas duplicados en bordes de tiles
- **Output esperado:** Número final de cromosomas $\approx 46$ (sin duplicados)

### TASK-055: Integrar EfficientNet-B3 para clasificación
- Extraer crops de cada bounding box (expandir $10\%$)
- Redimensionar a $224 \times 224$ para el modelo
- Llamar a TorchServe `POST /predictions/efficientnet`
- Recibir `{pair_number, confidence_score}` para cada cromosoma
- **Criterio:** Cada cromosoma tiene pair (1-22, X, Y) y score en $[0,1]$
- **Output esperado:**
```json
{"chromosomes": [
  {"id": "chrom_001", "pair": 21, "confidence": 0.94},
  {"id": "chrom_002", "pair": 21, "confidence": 0.96}
]}
```

### TASK-056: Implementar flag requires_review (HITL)
- Por cada cromosoma, si $\text{confidence\_score} < 0.85 \to \text{requires\_review} = \text{True}$
- Si $\text{requires\_review} == \text{True}$, el cromosoma se marca con borde naranja en UI
- **Criterio:** Score 0.84 $\to$ requiere revisión; Score 0.85 $\to$ no requiere
- **Output esperado:**
```python
if confidence_score < 0.85:
    chromosome.requires_review = True
    chromosome.color = "orange"
else:
    chromosome.requires_review = False
    chromosome.color = "green"
```

### TASK-056B: Implementar métrica de bloqueo HITL y bypass controlado
#### 056B-A: Calcular % de requires_review por muestra
- Después de clasificación, calcular `review_rate = count(requires_review=True) / 46 * 100`
- Almacenar en `samples.review_rate` (columna nueva FLOAT)
- **Criterio:** Muestra con 40 cromosomas $< 85\%$ $\to$ `review_rate = 87%`
- **Output esperado:** `UPDATE samples SET review_rate = 87.0 WHERE id='abc-123';`

#### 056B-B: Flag de alerta por baja calidad
- Si `review_rate > 80%` $\to$ `samples.low_confidence_flag = True`
- Notificar a supervisor por email: `"Alerta: muestra con 87% de baja confianza"`
- Registrar en audit_trail con $\text{action} = \text{"LOW\_CONFIDENCE\_ALERT"}$
- **Criterio:** Supervisor recibe alerta antes de que el analista bloquee el sistema
- **Output esperado:** Email to: `supervisor@lab.com` Subject: `[BIOMED ALERT] Muestra abc-123 tiene 87% de baja confianza`

#### 056B-C: Métrica agregada en dashboard
- Agregar a `GET /metrics`: `avg_review_rate_7d` y `samples_blocked_24h`
- Exponer endpoint `GET /metrics/prometheus` para monitoreo
- **Criterio:** El director del laboratorio ve tendencias de calidad del modelo
- **Output esperado:**
```json
GET /api/v1/metrics
{"avg_review_rate_7d": 23.5, "samples_blocked_24h": 2, "model_health": "degraded"}
```

#### 056B-D: Bypass controlado (modo degradado)
- Si `review_rate > 80%` por 3 muestras consecutivas $\to$ activar flag `system.emergency_mode`
- En `emergency_mode`: reducir umbral temporalmente a $70\%$ (justificado en audit trail)
- Notificar al arquitecto del sistema
- **Criterio:** El sistema puede operar aunque el modelo esté degradado
- **Output esperado:** `requires_review = confidence_score < get_dynamic_threshold()`

### TASK-057: Persistir 46 cromosomas en PostgreSQL
- Insertar cada cromosoma en tabla `chromosomes` en una sola transacción
- Usar `bulk_insert_mappings` para eficiencia
- Actualizar `samples.status` a `ready`
- **Criterio:** Después del pipeline, `SELECT COUNT(*) FROM chromosomes WHERE sample_id = X` retorna 46
- **Output esperado:**
```sql
SELECT COUNT(*) FROM chromosomes WHERE sample_id='abc-123';
→ 46
```

---

## 🔔 Sprint 6: Notificaciones y WebSocket

### TASK-060: Implementar WebSocket manager en FastAPI
- Crear `WebSocketManager` con diccionario `{sample_id: [websockets]}`
- Implementar `connect(sample_id, websocket)`, `disconnect(sample_id, websocket)`, `broadcast(sample_id, message)`
- **Criterio:** Múltiples clientes pueden conectarse al mismo `sample_id`
- **Output esperado:**
```python
manager = WebSocketManager()
await manager.connect("abc-123", websocket1)
await manager.broadcast("abc-123", {"status": "ready"})
```

### TASK-061: Publicar evento desde Celery al finalizar pipeline
- Al completar `process_inference`, llamar a `broadcast(sample_id, {"status": "ready"})`
- Incluir métricas: `processing_time_ms`, `chromosome_count`
- **Criterio:** WebSocket notificación llega al cliente en $< 500\text{ms}$ después de que Celery termina
- **Output esperado:**
```json
{"sample_id": "abc-123", "status": "ready", "processing_time_ms": 12450, "chromosome_count": 46}
```

### TASK-062: Implementar cliente WebSocket en React
- Crear hook `useWebSocket(sample_id)`
- Conectar a `ws://localhost:8000/ws/samples/{sample_id}`
- Escuchar eventos `status: "ready"` y actualizar store de Zustand
- Reconectar automáticamente si la conexión se pierde
- **C la UI muestra "Borrador listo" cuando llega la notificación
- **Output esperado:** Aparece un toast/notification `"✅ Borrador de cariotipo listo para revisión"`

---

## 🎨 Sprint 7: Frontend - Mesa de Edición

### TASK-070: Configurar React + Vite + Konva.js
- Crear app React con TypeScript
- Instalar `Konva.js` y `react-konva`
- Configurar Zustand store
- **Criterio:** La aplicación se abre en `http://localhost:5173` sin errores
- **Output esperado:** `npm run dev` $\to$ Ready

### TASK-071: Renderizar cromosomas en canvas Konva
- Crear componente `ChromosomeCanvas` que recibe lista de cromosomas
- Dibujar cada cromosoma como `Konva.Image` desde crop de imagen original
- Posicionar según `polygon_coords`
- **Criterio:** Los 46 cromosomas se muestran en grid de $4 \times 12$ (aprox)
- **Output esperado:** Canvas con cromosomas organizados por par

### TASK-072: Implementar semaforización visual (verde/naranja)
- Por cada cromosoma, si $\text{requires\_review} == \text{True} \to$ borde naranja 3px
- Si $\text{requires\_review} == \text{False} \to$ borde verde 1px
- Agregar tooltip con $\text{confidence\_score}$ al hacer hover
- **Criterio:** Cromosomas con score $< 0.85$ destacan visualmente
- **Output esperado:** Canvas con borde naranja grueso en cromosomas dudosos

### TASK-073: Implementar lista de revisión priorizada
- Mostrar lista lateral con cromosomas que tienen $\text{requires\_review} == \text{True}$
- Ordenar por $\text{confidence\_score}$ ascendente (menor confianza primero)
- Al hacer clic en un elemento de la lista, centrar canvas en ese cromosoma y resaltarlo
- **Criterio:** El analista puede identificar fácilmente los cromosomas que requieren atención
- **Output esperado:** Lista con 3-8 cromosomas naranja, el primero con score más bajo

---

## ✏️ Sprint 8: Edición Manual y Validación

### TASK-080: Implementar Drag & Drop en Konva
- Hacer cada cromosoma arrastrable (`draggable=true`)
- Al soltar, calcular nuevo slot (posición en grid)
- Llamar a `PATCH /chromosomes/{id}/position` con nuevas coordenadas
- **Criterio:** El cromosoma se mueve a nueva posición y persiste después de recargar
- **Output esperado:** El cromosoma se reubica en el grid y se actualiza en DB

### TASK-081: Implementar endpoint PATCH /chromosomes/{id}/validated
- Recibir `{validated: true}` en body
- Verificar que el usuario tiene rol "analista" (JWT)
- Actualizar `chromosomes.validated = true` y `validated_at = NOW()`
- Registrar en `edits` con $\text{action} = \text{"validate"}$
- **Criterio:** Solo analistas pueden validar; queda registro en audit trail
- **Output esperado:**
```json
PATCH /api/v1/chromosomes/chrom-001/validated → 200
{"id": "chrom-001", "validated": true, "all_validated": false, "remaining": 3}
```

### TASK-082: Implementar bloqueo de informe (RN-01)
- Antes de permitir `POST /reports`, verificar: No existen cromosomas con $\text{requires\_review} == \text{True} \text{ AND } \text{validated} == \text{False}$
- Si existen, retornar `409 Conflict` con mensaje y conteo
- **Criterio:** No se puede generar informe con cromosomas naranja sin validar
- **Output esperado:**
```json
POST /api/v1/reports → 409
{"detail": "Cannot generate report: 3 chromosomes require review", "pending": 3}
```

---

## 📄 Sprint 9: Reporte ISCN y Firma

### TASK-090: Implementar generador ISCN determinístico
- Contar cromosomas por `pair_number`
- Detectar anomalías (Normal 46,XX/XY; Trisomía 21: 47,XX,+21, etc.)
- **Criterio:** Misma entrada produce mismo ISCN siempre (determinista)
- **Output esperado:**
```python
generate_iscn(chromosomes, sex="XY") 
→ "46,XY"
```

### TASK-091: Implementar endpoint POST /reports
- Crear reporte asociado a `sample_id`
- Generar ISCN automáticamente
- Estado inicial: `pending_signature`
- **Criterio:** Cada sample tiene exactamente un reporte
- **Output esperado:**
```json
POST /api/v1/reports → 201
{"report_id": "rep-123", "sample_id": "abc-123", "iscn": "46,XY", "status": "pending_signature"}
```

### TASK-092: Implementar endpoint POST /reports/{id}/sign con MFA
- Validar que el usuario tiene rol "supervisor"
- Validar MFA (TOTP) antes de firmar
- Actualizar status a `emitido`
- Registrar `signed_by` y `signed_at`
- **Criterio:** Supervisor no puede firmar sin MFA; analista no puede firmar
- **Output esperado:**
```json
POST /api/v1/reports/rep-123/sign → 200
{"report_id": "rep-123", "status": "emitido", "signed_at": "2026-05-27T10:30:00Z"}
```

---

## 🧪 Sprint 10: Tests y Validación

### TASK-100: Implementar test de integración E2E
- Crear test con pytest que: Crea sample $\to$ Sube imagen $\to$ Espera WebSocket $\to$ Verifica 46 cromosomas en DB
- **Criterio:** El flujo completo se ejecuta sin errores en entorno de prueba
- **Output esperado:**
```text
$ pytest tests/e2e/test_pipeline.py -v
test_complete_pipeline PASSED [100%]
```

### TASK-101: Implementar test de privacidad (RN-03)
- Mockear TorchServe y S3
- Verificar que ningún request externo contiene PII (nombre, DNI, fecha)
- Usar `unittest.mock` para interceptar llamadas HTTP
- **Criterio:** 0% de requests externos contienen PII
- **Output esperado:**
```text
$ pytest tests/security/test_privacy.py -v
test_no_pii_in_torchserve_requests PASSED
```

### TASK-102: Implementar test de performance (SLA)
- Usar locust o k6 para simular 10 muestras concurrentes
- Medir tiempo p95 desde upload hasta notificación WebSocket
- Umbral de éxito: $< 15$ segundos
- **Criterio:** 95% de las muestras se procesan en $\le 15$ segundos
- **Output esperado:**
```text
$ k6 run tests/performance/load_test.js
✓ p95 inference time: 12.4s (threshold <15s)
```
