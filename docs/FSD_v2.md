\# Functional Specification Document (FSD) – BIOMED UMSS

\*\*Propósito del FSD:\*\* Describir \*\*cómo\*\* el sistema implementa los requisitos del PRD, con nivel de detalle técnico suficiente para que los ingenieros puedan construir, probar y desplegar. Responde a "¿cómo funciona?".

\*\*Audiencia:\*\* Ingeniería, QA, Arquitectura, Product (validación técnica).

\---

\#\# 0\. Metadatos ⚡🔧

| Campo | Valor |  
| :---- | :---- |  
| Producto | BIOMED UMSS – Intelligent Karyotyping Platform |  
| Grupo | G04 |  
| Versión del documento | v1.0 |  
| Fecha | Mayo 2026 |  
| Autores | Ing. Guillermo Mamani Chambi |  
| Revisores | Docente \+ 1 grupo par |  
| Estado | Aprobado |  
| \*\*Modo elegido\*\* | \*\*FSD clásico 🔧\*\* |  
| Trazabilidad a PRD | PRD v1.0 (Documento final del grupo) |  
| Insumos M2 (UI/UX) | mod2informefinal.pdf, mod3informe2.pdf, wireframes Figma, prototipo HTML https://guillemc92.github.io/karyoumss/ |  
| Fase Spec Kit cubierta | Specify ✅ / Plan ✅ / Tasks ⬜ / Implement ⬜ |  
| Prompts utilizados | PR-FSD-001, PR-FSD-002, PR-FSD-003, PR-FSD-004, PR-FSD-005 |

\---

\#\# 1\. Resumen ejecutivo ⚡🔧

BIOMED UMSS es una plataforma web de inteligencia aumentada para análisis citogenético. El sistema recibe imágenes de metafase (TIFF, PNG, JPEG), las anonimiza localmente con código CHN, y ejecuta un pipeline de visión computacional que segmenta y clasifica los 46 cromosomas. Cada cromosoma recibe un confidence score. La interfaz semaforiza en verde (confianza ≥85%) y naranja (confianza \<85%). El Analista revisa y corrige los cromosomas naranja mediante XAI (mapas de calor) y herramientas drag & drop. El Supervisor audita un 5% aleatorio de cromosomas verdes, firma con MFA, y el sistema genera el reporte ISCN mediante motor determinístico. El sistema opera en modo degradado manual si la IA falla. El valor diferencial es reducir el Time to Karyotype de 45 a 15 minutos con trazabilidad total y cumplimiento 21 CFR Part 11\.

\---

\#\# 2\. Alcance ⚡🔧

\#\#\# 2.1 Dentro del alcance

\- Ingesta de imágenes con validación de formato, tamaño, e integridad.  
\- Anonimización local con código CHN (formato CHN-YYYY-MM-DD-NNNN).  
\- Segmentación automática (U-Net) y clasificación (EfficientNet-B3).  
\- Semaforización por umbral 85% (verde/naranja).  
\- XAI con mapas de calor Grad-CAM y log obligatorio \`XAI\_VIEWED\`.  
\- Corrección manual: drag & drop, dividir, unir, rotar, eliminar artefactos.  
\- Bloqueo de emisión de reporte si hay naranjas sin resolver.  
\- Auditoría aleatoria del 5% de cromosomas con confianza \>86%.  
\- Audit Trail inmutable con hash chain SHA256.  
\- Segregación de roles (Analista, Supervisor, Administrador).  
\- Firma digital con MFA obligatorio (TOTP/huella/tarjeta).  
\- Generación determinística de ISCN con override manual.  
\- Modo degradado elegante (manual puro si IA falla).  
\- Exportación a PDF con nota al pie en overrides manuales.  
\- Validación de calidad de metafase (detección de superposición \>30%).

\#\#\# 2.2 Fuera del alcance (explícito)

\- Integración HL7 FHIR (v1.1).  
\- Importación DICOM (v1.2).  
\- Diagnóstico autónomo sin revisión humana (prohibido por BRD).  
\- Secuenciación NGS.  
\- Aplicación móvil nativa.  
\- Captura directa desde microscopio.

\#\#\# 2.3 Supuestos y dependencias

\*\*Supuestos técnicos:\*\*  
\- Laboratorios disponen de conexión a internet \>5 Mbps.  
\- GPU NVIDIA disponible para inferencia (cloud o on-premise).  
\- Imágenes cumplen requisitos mínimos: ≥300 DPI, ≥1024x1024 píxeles, \<50MB.  
\- Dataset de entrenamiento de 10,000+ metafases anotadas está disponible.

\*\*Dependencias externas:\*\*  
\- Servicio de timestamping (opcional, para 21 CFR Part 11).  
\- LIS Hospitalario (v1.1, no bloqueante para v1.0).  
\- Vault de mapeo CHN (local al laboratorio).

\#\#\# 2.4 Plan técnico (Spec Kit fase Plan) 🔧

| Bloque | Contenido |  
| :---- | :---- |  
| \*\*Stack tecnológico\*\* | Backend: Python 3.11 \+ FastAPI \+ PyTorch \+ PostgreSQL 15 \+ Redis 7\. Frontend: React 18 \+ TypeScript \+ Vite \+ Zustand \+ TailwindCSS. Infra: Docker \+ NVIDIA GPU (T4 o superior) \+ MinIO/S3. |  
| \*\*Arquitectura prevista\*\* | Hexagonal (puertos y adaptadores). Capas: API (FastAPI), Aplicación (casos de uso), Dominio (entidades, reglas), Infraestructura (repositorios, ML, storage). Frontend: Componentes atómicos, stores Zustand, servicios API. |  
| \*\*Project structure\*\* | \`backend/\` (src, tests, models, migrations), \`frontend/\` (src, components, stores, services, assets), \`infra/\` (docker, k8s, terraform), \`docs/\` (fsd, adr, api). |  
| \*\*Decisiones técnicas anticipadas\*\* | U-Net para segmentación (mejor manejo de solapamientos). EfficientNet-B3 para clasificación (trade-off precisión/velocidad). Grad-CAM para XAI. Hash chain SHA256 para audit trail. WebSockets para actualizaciones en tiempo real. localStorage para vault CHN local. |  
| \*\*Restricciones técnicas\*\* | Anonimización OBLIGATORIA antes de cualquier envío a servidor. PII nunca sale del nodo institucional. Modo degradado debe funcionar sin conexión a backend de IA. |

\#\#\# 2.5 Descomposición en Tasks (Spec Kit) ⚡🔧

| Task ID | Descripción | Caso de uso (FSD-UC) | Dependencias | Prompt asociado | Estado |  
| :---- | :---- | :---- | :---- | :---- | :---- |  
| \`T-001\` | Implementar endpoint \`POST /upload\` con validación de imagen y anonimización CHN local | \`FSD-UC-001\` | Ninguna | \`PR-FSD-001\` | pendiente |  
| \`T-002\` | Implementar pipeline de segmentación U-Net | \`FSD-UC-002\` | \`T-001\` | \`PR-FSD-002\` | pendiente |  
| \`T-003\` | Implementar pipeline de clasificación EfficientNet-B3 con confidence score | \`FSD-UC-002\` | \`T-002\` | \`PR-FSD-002\` | pendiente |  
| \`T-004\` | Implementar XAI Grad-CAM y log \`XAI\_VIEWED\` en audit trail | \`FSD-UC-003\` | \`T-003\` | \`PR-FSD-003\` | pendiente |  
| \`T-005\` | Implementar UI de cariotipo con semaforización (verde/naranja) y bloqueo | \`FSD-UC-002\`, \`FSD-UC-004\` | \`T-003\` | \`PR-FSD-004\` | pendiente |  
| \`T-006\` | Implementar herramientas de corrección manual (drag & drop, dividir, unir, rotar) | \`FSD-UC-003\` | \`T-005\` | \`PR-FSD-004\` | pendiente |  
| \`T-007\` | Implementar auditoría aleatoria 5% (BR-R2) | \`FSD-UC-005\` | \`T-005\` | \`PR-FSD-005\` | pendiente |  
| \`T-008\` | Implementar audit trail inmutable con hash chain SHA256 | \`FSD-UC-005\` | \`T-001\` | \`PR-FSD-005\` | pendiente |  
| \`T-009\` | Implementar firma digital con MFA y override ISCN manual | \`FSD-UC-006\` | \`T-007\`, \`T-008\` | \`PR-FSD-005\` | pendiente |  
| \`T-010\` | Implementar modo degradado elegante (manual puro sin IA) | \`FSD-UC-007\` | \`T-005\` | \`PR-FSD-001\` | pendiente |

\---

\#\# 3\. Actores y roles del sistema ⚡🔧

| Actor | Tipo (humano/sistema/agente IA) | Responsabilidad principal | Permisos clave |  
| :---- | :---- | :---- | :---- |  
| Analista Citogenetista | humano | Cargar imágenes, revisar cromosomas naranja, corregir clasificaciones, pasar caso a Supervisor | \`case:upload\`, \`case:edit\`, \`case:pass\_to\_supervisor\` |  
| Supervisor | humano | Auditar casos, revisar 5% aleatorio, firmar con MFA, editar ISCN manualmente | \`case:audit\`, \`case:sign\`, \`case:override\_iscn\` |  
| Administrador | humano | Configurar sistema, gestionar usuarios, ver métricas | \`admin:\*\` |  
| Sistema IA (Agente clasificador) | agente IA | Segmentar cromosomas, clasificar, generar confidence scores, producir mapas de calor XAI | \`ml:inference\` |  
| Sistema Audit Trail | sistema | Registrar acciones inmutables, generar hash chain, verificar integridad | \`audit:write\`, \`audit:read\`, \`audit:verify\` |

\---

\#\# 4\. Casos de uso funcionales ⚡🔧

\#\#\# 4.1 FSD-UC-001 – Ingesta y anonimización de imagen

\- \*\*Trazabilidad\*\*: \`PRD-US-001\`, \`PRD-US-002\`, \`PRD-REQ-001\`  
\- \*\*Actor principal\*\*: Analista  
\- \*\*Precondiciones\*\*:  
  1\. Analista autenticado en el sistema.  
  2\. Imagen de metafase disponible en formato TIFF, PNG, o JPEG.  
\- \*\*Disparador\*\*: Analista hace clic en "Cargar imagen" y selecciona un archivo.  
\- \*\*Flujo principal\*\*:  
  1\. Sistema valida formato, tamaño (\<50MB), e integridad del archivo.  
  2\. Sistema genera código CHN único: \`CHN-YYYY-MM-DD-NNNN\`.  
  3\. Sistema elimina todos los metadatos EXIF/DICOM con PII.  
  4\. Sistema almacena mapeo CHN en vault cifrado local (no sube a la nube).  
  5\. Sistema envía imagen anonimizada al backend para procesamiento.  
  6\. Sistema retorna \`case\_id\` y \`chn\_code\` al frontend.  
\- \*\*Flujos alternativos / excepciones\*\*:  
  \- \`A1\`: Archivo corrupto → sistema rechaza, mensaje "El archivo está dañado".  
  \- \`A2\`: Formato no soportado → sistema rechaza, mensaje "Formato no soportado. Use TIFF, PNG o JPEG".  
  \- \`A3\`: Tamaño \>50MB → sistema rechaza, mensaje "Imagen demasiado grande (máx 50MB)".  
\- \*\*Postcondiciones\*\*:  
  1\. Imagen anonimizada almacenada en bucket seguro.  
  2\. Caso creado en estado \`PENDIENTE\_REVISION\_IA\`.  
  3\. Audit Trail registra evento \`CASE\_CREATED\` y \`ANONYMIZATION\_COMPLETED\`.  
\- \*\*Reglas de negocio aplicables\*\*: \`BR-01\` (anonimización obligatoria)  
\- \*\*Datos de entrada\*\*:  
  \`\`\`json  
  {  
    "file": "multipart/form-data",  
    "hospital\_code": "string (opcional)"  
  }

* Datos de salida:  
* `json`

`{`  
  `"case_id": "uuid",`  
  `"chn_code": "CHN-2026-05-15-0001",`  
  `"status": "PENDING_AI",`  
  `"uploaded_at": "2026-05-15T10:30:00Z"`

* `}`  
* Criterios de aceptación:

`gherkin`

`DADO un Analista autenticado`  
`CUANDO selecciona una imagen TIFF válida de 15MB`  
`ENTONCES el sistema genera un código CHN EN <2 SEGUNDOS`  
`Y la imagen se almacena sin metadatos PII`  
`Y se retorna case_id y chn_code`

`DADO un Analista autenticado`  
`CUANDO selecciona un archivo corrupto`  
`ENTONCES el sistema rechaza la carga`  
`Y muestra mensaje "El archivo está dañado o incompleto"`

`Y NO se crea un caso en el sistema`

### **4.2 FSD-UC-002 – Segmentación, clasificación y semaforización**

* Trazabilidad: `PRD-US-003`, `PRD-US-004`, `PRD-REQ-002`, `PRD-REQ-003`, `PRD-REQ-004`  
* Actor principal: Sistema IA (automático)  
* Precondiciones:  
  1. Caso existe en estado `PENDIENTE_REVISION_IA`.  
  2. Imagen anonimizada disponible en storage.  
* Disparador: Evento `IMAGE_UPLOADED` enviado a cola de procesamiento.  
* Flujo principal:  
  1. Sistema carga imagen desde storage.  
  2. Sistema ejecuta preprocesamiento: redimension a 1024x1024, normalización, denoising bilateral.  
  3. Sistema ejecuta segmentación U-Net: detecta cromosomas, genera bounding boxes y máscaras.  
  4. Sistema evalúa calidad: calcula porcentaje de superposición (overlap).  
  5. Si superposición \>30%, sistema marca `quality_flag: HIGH_OVERLAP`.  
  6. Sistema extrae crops de cada cromosoma (224x224).  
  7. Sistema ejecuta clasificación EfficientNet-B3: 24 clases \+ confidence score.  
  8. Sistema asigna semáforo: verde si confidence ≥85%, naranja si \<85%.  
  9. Sistema almacena resultados en base de datos.  
  10. Sistema cambia estado del caso a `BLOQUEADO_POR_CONFIANZA` (si hay naranjas) o `VALIDADO_POR_ANALISTA` (si todos verdes).  
* Flujos alternativos / excepciones:  
  1. `A1`: Segmentación detecta \<40 o \>55 cromosomas → sistema marca `quality_flag: ABNORMAL_COUNT`, requiere revisión manual prioritaria.  
  2. `A2`: Modelo IA timeout (\>30s) → sistema entra en modo degradado (ver FSD-UC-007).  
* Postcondiciones:  
  1. Caso tiene 46 cromosomas segmentados y clasificados.  
  2. Cada cromosoma tiene confidence score y color asociado.  
  3. Audit Trail registra evento `SEGMENTATION_COMPLETED` y `CLASSIFICATION_COMPLETED`.  
* Reglas de negocio aplicables: `BR-02` (semaforización), `BR-03` (bloqueo)  
* Datos de entrada (desde T-001):  
* `json`

`{`  
  `"case_id": "uuid",`  
  `"image_path": "s3://bucket/CHN-2026-05-15-0001.tiff"`

* `}`  
* Datos de salida:  
* `json`

`{`  
  `"case_id": "uuid",`  
  `"chromosomes": [`  
    `{`  
      `"id": "chrom_001",`  
      `"bbox": [120, 340, 95, 210],`  
      `"mask_rle": "encoded_string",`  
      `"predicted_class": "21",`  
      `"confidence": 0.94,`  
      `"color": "green",`  
      `"quality_flag": null`  
    `},`  
    `{`  
      `"id": "chrom_012",`  
      `"predicted_class": "14",`  
      `"confidence": 0.82,`  
      `"color": "orange",`  
      `"requires_xai": true`  
    `}`  
  `],`  
  `"quality_flags": ["HIGH_OVERLAP"]  // si aplica`

* `}`  
* Criterios de aceptación:

`gherkin`

`DADO una imagen de metafase anonimizada`  
`CUANDO el pipeline de IA completa el procesamiento`  
`ENTONCES se detectan 46 cromosomas`  
`Y cada cromosoma tiene confidence score`  
`Y el tiempo de procesamiento es <15 SEGUNDOS en GPU`  
`Y la precisión de segmentación IoU es >0.90`

`DADO un cromosoma con confidence 0.82 (<85%)`  
`CUANDO se renderiza el cariotipo en UI`  
`ENTONCES el cromosoma se muestra con borde naranja`  
`Y el botón "Pasar a Supervisor" está inhabilitado`

`DADO una metafase con superposición >30%`  
`CUANDO el pipeline completa el procesamiento`  
`ENTONCES el sistema muestra un banner de advertencia amarillo`

`Y registra quality_flag: HIGH_OVERLAP en Audit Trail`

### **4.3 FSD-UC-003 – XAI y corrección manual**

* Trazabilidad: `PRD-US-005`, `PRD-US-006`, `PRD-US-007`, `PRD-REQ-006`, `PRD-REQ-007`, `PRD-REQ-013`  
* Actor principal: Analista  
* Precondiciones:  
  1. Caso en estado `BLOQUEADO_POR_CONFIANZA` o `REVISION_ANALISTA`.  
  2. Al menos un cromosoma naranja pendiente de resolución.  
* Disparador: Analista hace clic en un cromosoma naranja o activa herramienta de edición.  
* Flujo principal (XAI):  
  1. Analista hace clic en ícono de explicabilidad de un cromosoma naranja.  
  2. Sistema recupera logits almacenados del modelo.  
  3. Sistema ejecuta Grad-CAM en la última capa convolucional.  
  4. Sistema genera mapa de calor superpuesto sobre el crop del cromosoma.  
  5. Sistema muestra modal con mapa de calor y tooltip con región de banda relevante.  
  6. Sistema registra `XAI_VIEWED` en Audit Trail con `chromosome_id`, `analyst_id`, `timestamp`, `confidence_pre_xai`.  
  7. Analista puede ahora resolver el cromosoma.  
* Flujo principal (corrección drag & drop):  
  1. Analista selecciona un cromosoma (naranja o verde).  
  2. Analista arrastra el cromosoma hacia un slot del cariograma (1-22, X, Y, o basurero).  
  3. Sistema muestra preview visual durante el arrastre (snapping).  
  4. Analista suelta el cromosoma en el slot destino.  
  5. Sistema actualiza `predicted_class` al nuevo slot.  
  6. Sistema marca cromosoma como `RESOLVED` (si era naranja).  
  7. Sistema registra `CORREGIR_CLASE` en Audit Trail con `original_class`, `new_class`, `analyst_id`.  
  8. Si era el último cromosoma naranja, sistema cambia estado a `VALIDADO_POR_ANALISTA` y habilita botón "Pasar a Supervisor".  
* Flujos alternativos / excepciones:  
  1. `A1`: Analista intenta resolver cromosoma naranja sin abrir XAI → sistema bloquea, mensaje "Debe consultar la explicabilidad (XAI) antes de resolver".  
  2. `A2`: Herramienta dividir → Analista dibuja línea, sistema separa máscaras, reclasifica ambas partes.  
  3. `A3`: Herramienta unir → Analista selecciona dos fragmentos, sistema combina máscaras, reclasifica.  
* Postcondiciones:  
  1. Corrección registrada en Audit Trail.  
  2. Si era último naranja, caso transiciona a `VALIDADO_POR_ANALISTA`.  
  3. XAI log obligatorio existe para cada naranja resuelto.  
* Reglas de negocio aplicables: `BR-03` (bloqueo), `BR-R3` (reentrenamiento seguro)  
* Criterios de aceptación:

`gherkin`

`DADO un Analista viendo un cromosoma naranja`  
`CUANDO hace clic en el ícono XAI`  
`ENTONCES el sistema muestra un mapa de calor EN <1 SEGUNDO`  
`Y registra XAI_VIEWED en Audit Trail`  
`Y el Analista ahora puede resolver el cromosoma`

`DADO un Analista que intenta resolver un cromosoma naranja sin abrir XAI`  
`CUANDO hace clic en "Aceptar" o arrastra a otro slot`  
`ENTONCES el sistema bloquea la acción`  
`Y muestra mensaje "Debe consultar XAI antes de resolver"`

`DADO un Analista en la pantalla de validación`  
`CUANDO arrastra un cromosoma al slot del Par 21`  
`ENTONCES el sistema reubica el cromosoma EN <500ms`  
`Y registra la corrección en Audit Trail`

`Y el número máximo de acciones es 1 (un solo arrastre)`

### **4.4 FSD-UC-004 – Bloqueo y validación de Analista**

* Trazabilidad: `PRD-US-008`, `PRD-REQ-005`  
* Actor principal: Analista \+ Sistema  
* Precondiciones:  
  1. Caso en estado `BLOQUEADO_POR_CONFIANZA` o `REVISION_ANALISTA`.  
* Disparador: Analista completa resolución de todos los cromosomas naranja.  
* Flujo principal:  
  1. Analista resuelve el último cromosoma naranja (vía XAI \+ corrección).  
  2. Sistema verifica: `unresolved_orange_count == 0`.  
  3. Sistema cambia estado del caso a `VALIDADO_POR_ANALISTA`.  
  4. Sistema habilita botón "Pasar a Supervisor" en UI.  
  5. Sistema registra `ANALYST_VALIDATED` en Audit Trail con `time_in_blocked_state_seconds`.  
* Flujos alternativos / excepciones:  
  1. `A1`: Analista intenta pasar a supervisor sin resolver todos los naranjas → botón inhabilitado, mensaje "Resuelva X cromosomas naranja antes de continuar".  
* Postcondiciones:  
  1. Caso listo para envío a Supervisor.  
  2. Audit Trail contiene resolución de cada cromosoma naranja.  
* Criterios de aceptación:

`gherkin`

`DADO un caso con 3 cromosomas naranja sin resolver`  
`CUANDO el Analista resuelve el último cromosoma naranja`  
`ENTONCES el sistema cambia estado a VALIDADO_POR_ANALISTA`  
`Y el botón "Pasar a Supervisor" se habilita EN <1 SEGUNDO`

`DADO un caso con al menos un cromosoma naranja sin resolver`  
`CUANDO el Analista intenta hacer clic en "Pasar a Supervisor"`  
`ENTONCES el botón está inhabilitado visualmente`

`Y muestra mensaje "Resuelva X cromosomas naranja antes de continuar"`

### **4.5 FSD-UC-005 – Auditoría aleatoria y firma con MFA**

* Trazabilidad: `PRD-US-009`, `PRD-US-010`, `PRD-US-011`, `PRD-REQ-008`, `PRD-REQ-009`, `PRD-REQ-010`  
* Actor principal: Supervisor  
* Precondiciones:  
  1. Caso en estado `PENDIENTE_SUPERVISOR`.  
  2. Supervisor autenticado.  
* Disparador: Supervisor abre caso desde bandeja de auditoría.  
* Flujo principal (auditoría aleatoria):  
  1. Sistema identifica cromosomas con confianza \>86% en el caso.  
  2. Sistema selecciona aleatoriamente el 5% (mínimo 1).  
  3. Sistema marca esos cromosomas con badge púrpura "Auditoría requerida".  
  4. Supervisor revisa cada cromosoma auditado, comparando con ideograma de referencia.  
  5. Para cada cromosoma, Supervisor selecciona "Confirmado" o "Rechazado" con comentario opcional.  
  6. Sistema registra cada decisión en Audit Trail.  
* Flujo principal (firma con MFA):  
  1. Supervisor completa revisión (incluyendo 5% auditoría).  
  2. Supervisor hace clic en "Firmar Reporte".  
  3. Sistema solicita autenticación MFA (TOTP, huella digital, o tarjeta inteligente).  
  4. Supervisor completa MFA.  
  5. Sistema genera reporte ISCN (ver FSD-UC-006).  
  6. Sistema registra `SIGN_REPORT` en Audit Trail con método de autenticación usado.  
  7. Sistema cambia estado del caso a `FIRMADO`.  
* Flujos alternativos / excepciones:  
  1. `A1`: Supervisor intenta firmar sin revisar 5% auditoría → sistema bloquea, mensaje "Debe revisar X cromosomas de auditoría antes de firmar".  
  2. `A2`: MFA falla 3 veces → sistema bloquea firma por 15 minutos, registra evento de seguridad.  
* Postcondiciones:  
  1. Reporte firmado digitalmente.  
  2. Audit Trail completo con hashes encadenados.  
* Criterios de aceptación:

`gherkin`

`DADO un caso validado por Analista con 46 cromosomas`  
`CUANDO el Supervisor abre el caso`  
`ENTONCES el sistema selecciona aleatoriamente el 5% de cromosomas con confianza >86%`  
`Y los marca con badge púrpura "Auditoría requerida"`  
`Y la selección es reproducible (mismo caso, mismos cromosomas)`

`DADO un Supervisor que ha completado la revisión del caso`  
`CUANDO hace clic en "Firmar Reporte"`  
`ENTONCES el sistema solicita autenticación MFA`  
`Y el Supervisor no puede firmar sin completar MFA`  
`Y tras validar MFA, el sistema genera el reporte EN <2 SEGUNDOS`

`Y registra SIGN_REPORT en Audit Trail con el método de autenticación usado`

### **4.6 FSD-UC-006 – Generación de reporte ISCN con override manual**

* Trazabilidad: `PRD-US-012`, `PRD-REQ-011`  
* Actor principal: Supervisor \+ Sistema  
* Precondiciones:  
  1. Caso en estado `FIRMADO` (después de MFA).  
* Disparador: Evento `REPORT_GENERATION` tras firma exitosa.  
* Flujo principal (automático):  
  1. Sistema cuenta cromosomas por clase final (incluyendo correcciones manuales).  
  2. Sistema aplica reglas determinísticas ISCN 2024:  
     * Orden ascendente de anomalías numéricas (ej: \+18 antes de \+21).  
     * Sexo al final (XX o XY).  
     * Anomalías estructurales en orden de cromosoma afectado.  
  3. Sistema genera string ISCN (ej: "46,XX" o "47,XY,+21").  
  4. Sistema muestra ISCN generado en pantalla de resumen.  
* Flujo principal (override manual):  
  1. Supervisor revisa ISCN generado automáticamente.  
  2. Supervisor puede editar manualmente el string en un campo de texto.  
  3. Sistema valida que el string editado cumpla gramática ISCN.  
  4. Si la gramática es inválida, sistema muestra alerta roja "ISCN inválido. Revise la sintaxis".  
  5. Supervisor confirma override.  
  6. Sistema registra `ISCN_OVERRIDE` en Audit Trail con:  
     * `original_iscn` (generado automáticamente)  
     * `final_iscn` (editado por Supervisor)  
     * `supervisor_id`  
     * `justification` (campo opcional)  
  7. Sistema genera PDF con nota al pie: "\* Nomenclatura editada manualmente por Supervisor. Revisión clínica aplicada."  
* Postcondiciones:  
  1. Reporte PDF generado y almacenado.  
  2. ISCN final registrado en caso.  
  3. Caso cambia a estado `REPORTADO`.  
* Criterios de aceptación:

`gherkin`

`DADO un cariotipo con 3 copias del cromosoma 21 y sexo XY`  
`CUANDO el sistema genera el ISCN automáticamente`  
`ENTONCES el string es "47,XY,+21"`

`DADO un Supervisor que edita manualmente el ISCN a "48,XY,+21,+18"`  
`CUANDO confirma el override`  
`ENTONCES el sistema valida la gramática ISCN`  
`Y registra ISCN_OVERRIDE en Audit Trail`

`Y el PDF incluye nota al pie sobre la edición manual`

### **4.7 FSD-UC-007 – Modo degradado elegante**

* Trazabilidad: `PRD-US-013`, `PRD-REQ-012`  
* Actor principal: Analista \+ Sistema  
* Precondiciones:  
  1. Servicio de IA no disponible (timeout \>10s, errores 5xx, GPU offline).  
* Disparador: Detección de fallo de IA en el endpoint de procesamiento.  
* Flujo principal:  
  1. Sistema detecta fallo de IA (3 timeouts consecutivos).  
  2. Sistema muestra banner en UI: "Modo Manual Activado \- IA no disponible".  
  3. Analista carga imagen normalmente.  
  4. Sistema NO ejecuta segmentación ni clasificación automática.  
  5. Analista debe segmentar y clasificar cromosomas manualmente:  
     * Herramientas de dibujo de bounding boxes.  
     * Asignación manual a pares cromosómicos.  
  6. Todas las herramientas manuales (dividir, unir, rotar, arrastrar) están disponibles.  
  7. Sistema registra cada acción manual en Audit Trail con flag `mode: "degradado"`.  
  8. Sistema monitorea disponibilidad de IA cada 30 segundos.  
  9. Cuando IA se restaura, sistema sincroniza el caso y ofrece "Migrar a modo automático".  
* Flujos alternativos / excepciones:  
  1. `A1`: Modo degradado excede 2 horas continuas → sistema activa alerta a ops, laboratorio recibe crédito automático.  
* Postcondiciones:  
  1. El laboratorio puede seguir operando sin IA.  
  2. Tiempo en modo degradado registrado para facturación.  
* Criterios de aceptación:

`gherkin`

`DADO que el servicio de IA está caído`  
`CUANDO un Analista intenta procesar una imagen`  
`ENTONCES el sistema muestra banner "Modo Manual Activado - IA no disponible"`  
`Y permite segmentación y clasificación manual`  
`Y registra todas las acciones con flag mode: "degradado"`

`Y cuando la IA se restaura, sincroniza el caso automáticamente`

---

## **5\. Reglas de negocio ⚡🔧**

| ID | Regla | Tipo | Origen | Casos de uso afectados |
| :---- | :---- | :---- | :---- | :---- |
| BR-001 | Anonimización CHN obligatoria antes de cualquier procesamiento. PII nunca sale del nodo institucional. | validación | BR-01 | FSD-UC-001 |
| BR-002 | Semaforización: verde si confidence ≥85%, naranja si \<85%. | cálculo | BR-02 | FSD-UC-002 |
| BR-003 | Bloqueo de reporte: caso no puede pasar a Supervisor si ∃ cromosoma naranja sin `resolution_status='RESOLVED'`. | política | BR-03, BR-R1 | FSD-UC-004 |
| BR-004 | XAI obligatorio: cromosoma naranja no puede resolverse sin evento `XAI_VIEWED` en Audit Trail. | validación | BR-06 | FSD-UC-003 |
| BR-005 | Auditoría aleatoria: 5% de cromosomas con confianza \>86% seleccionados para revisión obligatoria por Supervisor. Selección reproducible por `case_id + seed`. | política | BR-R2 | FSD-UC-005 |
| BR-006 | ISCN determinístico: generado por motor de reglas (no IA). Supervisor puede hacer override manual con registro en Audit Trail. | cálculo | BR-04 | FSD-UC-006 |
| BR-007 | Firma regulatoria: Supervisor debe completar MFA antes de firmar. Método de autenticación registrado en Audit Trail. | validación | BR-R4 | FSD-UC-005 |
| BR-008 | Modo degradado: sistema debe operar sin IA por hasta 2 horas continuas. Tiempo registrado para facturación automática. | política | BR-08 | FSD-UC-007 |
| BR-009 | Calidad de metafase: superposición \>30% genera advertencia pero no bloquea. | validación | PRD-US-004b | FSD-UC-002 |

---

## **6\. Modelo de datos funcional ⚡🔧**

### **6.1 Diagrama ER (Mermaid)**

`erDiagram`  
    `CASO ||--o{ CROMOSOMA : contiene`  
    `CASO ||--o{ AUDIT_TRAIL : genera`  
    `SUPERVISOR ||--o{ CASO : firma`  
    `ANALISTA ||--o{ CASO : edita`  
    `CASO ||--o{ CASO_AUDITORIA : seleccionado_para`

    `CASO {`  
        `uuid id PK`  
        `string chn_code UK`  
        `string hospital_code`  
        `string estado`  
        `timestamp created_at`  
        `timestamp analyst_validated_at`  
        `timestamp supervisor_signed_at`  
        `int ttk_seconds`  
        `uuid analyst_id FK`  
        `uuid supervisor_id FK`  
        `jsonb quality_flags`  
    `}`

    `CROMOSOMA {`  
        `uuid id PK`  
        `uuid case_id FK`  
        `int index`  
        `string predicted_class`  
        `float confidence`  
        `boolean is_low_confidence`  
        `string resolution_status`  
        `string original_class`  
        `uuid resolved_by FK`  
        `timestamp resolved_at`  
        `boolean xai_consulted`  
        `boolean random_audit_flag`  
        `boolean random_audit_reviewed`  
        `string heatmap_path`  
    `}`

    `AUDIT_TRAIL {`  
        `uuid id PK`  
        `uuid case_id FK`  
        `string action_type`  
        `jsonb previous_value`  
        `jsonb new_value`  
        `uuid user_id`  
        `string user_role`  
        `timestamp created_at`  
        `string previous_hash`  
        `string current_hash`  
    `}`

    `CASO_AUDITORIA {`  
        `uuid id PK`  
        `uuid case_id FK`  
        `uuid chromosome_id FK`  
        `string decision`  
        `string comment`  
        `uuid supervisor_id FK`  
        `timestamp reviewed_at`

    `}`

### **6.2 Diccionario de datos**

| Entidad | Atributo | Tipo | Obligatorio | Validaciones | Origen |
| :---- | :---- | :---- | :---- | :---- | :---- |
| `CASO` | `id` | UUID | sí | formato UUIDv4 | sistema |
| `CASO` | `chn_code` | VARCHAR(50) | sí | regex `CHN-\d{4}-\d{2}-\d{2}-\d{4}` | sistema |
| `CASO` | `estado` | ENUM | sí | `PENDING_AI`, `BLOCKED_CONF`, `ANALYST_VALIDATED`, `PENDING_SUPERVISOR`, `SIGNED`, `REPORTED` | sistema |
| `CASO` | `ttk_seconds` | INTEGER | no | ≥0 | sistema |
| `CROMOSOMA` | `predicted_class` | VARCHAR(3) | sí | `1`\-`22`, `X`, `Y` | IA o manual |
| `CROMOSOMA` | `confidence` | DECIMAL(4,3) | sí | 0.000 a 1.000 | IA |
| `CROMOSOMA` | `resolution_status` | ENUM | sí | `PENDING`, `RESOLVED` | sistema |
| `CROMOSOMA` | `xai_consulted` | BOOLEAN | sí | `true`/`false` | sistema |
| `AUDIT_TRAIL` | `action_type` | VARCHAR(50) | sí | `XAI_VIEWED`, `CORREGIR_CLASE`, `DIVIDIR`, `UNIR`, `ROTAR`, `SIGN_REPORT`, `ISCN_OVERRIDE` | sistema |
| `AUDIT_TRAIL` | `current_hash` | VARCHAR(64) | sí | SHA256 hexadecimal | sistema (generado) |

---

## **7\. Prompt como Contrato Funcional ⚡🔧**

### **7.1 Prompt‑contrato para FSD-UC-002 (Segmentación y clasificación)**

`markdown`

`# Role`  
`Eres un pipeline de visión computacional especializado en análisis citogenético. Actúas como agente autónomo que recibe una imagen de metafase y devuelve cromosomas segmentados y clasificados.`

`# Task`  
`Procesar una imagen de metafase anonimizada y producir:`  
`1. Segmentación de cromosomas individuales (bounding boxes y máscaras)`  
`2. Clasificación de cada cromosoma (par 1-22, X, Y)`  
`3. Confidence score por cada clasificación`  
`4. Flag de calidad (detección de superposición >30%)`

`# Context`  
`- Entrada: Imagen TIFF/PNG/JPEG, anonimizada, resolución ≥1024x1024, DPI ≥300`  
`- Referencias de dominio: Bandas G, morfología cromosómica (longitud, posición de centrómero)`  
`- Restricciones: Tiempo de inferencia <15 segundos en GPU, IoU segmentación >0.90`

`# Reasoning`  
`Pasos obligatorios:`  
`1. Preprocesar: redimensionar a 1024x1024, normalizar intensidades, aplicar denoising bilateral`  
`2. Segmentar: U-Net con backbone ResNet34, post-procesar con watershed para separar solapamientos`  
`3. Validar calidad: calcular área de superposición, si >30% marcar flag HIGH_OVERLAP`  
`4. Extraer crops: cada bounding box expandido 10%, redimensionar a 224x224`  
`5. Clasificar: EfficientNet-B3 (24 clases), softmax + logits`  
`6. Calcular confianza: max(softmax) como confidence score`  
`7. Generar salida: JSON con cromosomas, clases, confianzas, flags`

`# Stop condition`  
`Detente cuando: se hayan procesado todos los cromosomas detectados (target: 46) o cuando timeout >30 segundos.`

`# Output`  
`Formato: JSON`  
`{`  
  `"chromosomes": [`  
    `{`  
      `"id": "uuid",`  
      `"bbox": [x1, y1, x2, y2],`  
      `"mask_rle": "string",`  
      `"predicted_class": "21",`  
      `"confidence": 0.94,`  
      `"color": "green"`  
    `}`  
  `],`  
  `"quality_flags": ["HIGH_OVERLAP"],`  
  `"inference_time_ms": 3200`  
`}`

`Invariants: confidence entre 0.000 y 1.000, suma de confianzas no requerida. Failure modes: si detecta <40 o >55 cromosomas, retornar quality_flag "ABNORMAL_COUNT".`

### **7.2 Prompt‑contrato para FSD-UC-003 (XAI Grad-CAM)**

`markdown`

`# Role`  
`Eres un motor de explicabilidad de IA especializado en cariotipado. Generas mapas de calor (Grad-CAM) que muestran en qué regiones de la imagen se basó la clasificación.`

`# Task`  
`Recibir un crop de cromosoma, los logits del modelo, y la clase predicha. Producir un mapa de calor superpuesto sobre el crop original.`

`# Context`  
`- Entrada: crop 224x224 RGB, logits del modelo EfficientNet-B3 (vector 24), clase predicha`  
`- Referencias de dominio: Bandas G cromosómicas, región de interés diagnóstico`  
`- Restricciones: Tiempo de generación <1 segundo por cromosoma`

`# Reasoning`  
`Pasos obligatorios:`  
`1. Identificar la última capa convolucional del modelo (features.dense_block5)`  
`2. Calcular gradientes de la clase predicha respecto a los feature maps de esa capa`  
`3. Promediar gradientes por canal para obtener pesos de importancia`  
`4. Generar mapa de calor: combinación lineal ponderada de feature maps`  
`5. Aplicar ReLU para mantener solo influencia positiva`  
`6. Redimensionar mapa de calor a 224x224`  
`7. Superponer sobre crop original con opacidad 0.5`  
`8. Identificar región de máxima intensidad y mapear a banda cromosómica conocida (lookup table de bandas G)`

`# Stop condition`  
`Detente cuando: mapa de calor generado y superpuesto correctamente.`

`# Output`  
`Formato: PNG (base64) + región identificada`  
`{`  
  `"heatmap_base64": "base64_encoded_png",`  
  `"salient_region": "q22.3",`  
  `"explanation_text": "La IA se basó en la banda q22.3 del cromosoma 21 para esta clasificación"`  
`}`

`Invariants: mapa de calor debe cubrir toda la imagen del crop. Failure modes: si no se puede identificar región, retornar explanation_text genérico "Región de influencia no determinable".`

### **7.3 Prompt‑contrato para FSD-UC-005 (Auditoría aleatoria)**

`markdown`

`# Role`  
`Eres un motor de auditoría que selecciona aleatoriamente cromosomas para revisión obligatoria, previniendo el sesgo de automatización.`

`# Task`  
`Recibir un caso validado por Analista con 46 cromosomas clasificados. Seleccionar el 5% de los cromosomas con confianza >86% para auditoría por Supervisor.`

`# Context`  
`- Entrada: case_id, lista de cromosomas con id, clase, confidence (>86% filtrados)`  
`- Referencias de dominio: BR-R2 del BRD (auditoría aleatoria 5%)`  
`- Restricciones: La selección debe ser reproducible: mismo case_id siempre produce los mismos cromosomas seleccionados`

`# Reasoning`  
`Pasos obligatorios:`  
`1. Filtrar cromosomas con confidence >0.86`  
`2. Calcular seed reproducible: SHA256(case_id + "audit_salt") % (2^32)`  
`3. Inicializar PRNG con esa seed`  
`4. Calcular sample_size = max(1, int(len(filtered) * 0.05))`  
`5. Seleccionar sample_size cromosomas usando PRNG`  
`6. Marcar cromosomas seleccionados con flag random_audit_flag = true`  
`7. Registrar selección en tabla CASO_AUDITORIA con selection_hash`

`# Stop condition`  
`Detente cuando: sample_size cromosomas seleccionados y flags actualizados.`

`# Output`  
`Formato: JSON`  
`{`  
  `"selected_chromosomes": ["chrom_012", "chrom_034"],`  
  `"sample_size": 2,`  
  `"selection_hash": "0x8f3a9b2c..."`  
`}`

`Invariants: sample_size siempre ≥1 si filtered.length > 0. Failure modes: si no hay cromosomas con confidence >86%, retornar lista vacía y no aplicar auditoría.`

---

## **8\. Integraciones externas 🔧**

| Sistema | Tipo | Protocolo | Operaciones | SLA esperado | Autenticación |
| :---- | :---- | :---- | :---- | :---- | :---- |
| GPU Cluster (TorchServe) | síncrono REST | HTTPS | `POST /predict/segment`, `POST /predict/classify` | 99.5% / 15s p95 | API Key \+ JWT |
| MinIO/S3 Storage | asíncrono | S3 API | `PUT /bucket/{case_id}`, `GET /bucket/{case_id}` | 99.9% | IAM / Access Key |
| PostgreSQL | síncrono | TCP | SQL queries | 99.99% | Usuario/contraseña \+ TLS |
| Servicio de timestamping (opcional) | síncrono | HTTPS | `POST /timestamp` | 99.9% / 500ms p95 | API Key |

---

## **9\. Interfaces de usuario (referencia) ⚡🔧**

| Pantalla | Caso de uso cubierto |
| :---- | :---- |
| `/login` | Autenticación (todos los roles) |
| `/dashboard` | Listado de casos, priorización visual |
| `/upload` | FSD-UC-001 (Ingesta y anonimización) |
| `/karyotype/{case_id}` | FSD-UC-002 (Visualización de cariotipo), FSD-UC-003 (Corrección manual) |
| `/validation/{case_id}` | FSD-UC-003 (XAI), FSD-UC-004 (Bloqueo) |
| `/supervisor/{case_id}` | FSD-UC-005 (Auditoría y firma) |
| `/report/{case_id}` | FSD-UC-006 (Reporte ISCN) |
| `/degraded` | FSD-UC-007 (Modo degradado) |

### **9.1 Trazabilidad con M2 (UI/UX) ⚡🔧**

| Wireframe / mockup M2 | Pantalla FSD | Caso de uso (FSD-UC) | Estado de la traza |
| :---- | :---- | :---- | :---- |
| Dashboard de muestras (mod2, pág. 23\) | `/dashboard` | FSD-UC-004, FSD-UC-005 | ✅ cubierto |
| Pantalla de análisis de metafase (mod2, pág. 24-25) | `/karyotype/{case_id}` | FSD-UC-002 | ✅ cubierto |
| Pantalla de validación experta (mod2, pág. 26\) | `/validation/{case_id}` | FSD-UC-003, FSD-UC-004 | ✅ cubierto |
| Pantalla de corrección manual (mod2, pág. 27\) | `/karyotype/{case_id}` (modo edición) | FSD-UC-003 | ✅ cubierto |
| Pantalla de generación de reporte (mod2, pág. 28\) | `/supervisor/{case_id}`, `/report/{case_id}` | FSD-UC-005, FSD-UC-006 | ✅ cubierto |
| Prototipo HTML (mod3) | Todas las pantallas | Validación completa | ✅ validado |

---

## **10\. Requerimientos No Funcionales (NFR) ⚡🔧**

| ID | Categoría | Requisito | Métrica | Umbral | Cómo se verifica |
| :---- | :---- | :---- | :---- | :---- | :---- |
| NFR-001 | Rendimiento | Tiempo de segmentación \+ clasificación por imagen | Mediana | \<15 segundos (GPU) | Prueba de carga con 100 imágenes |
| NFR-002 | Rendimiento | Time to Karyotype (TTK) total por caso | Percentil 95 | \<15 minutos | Logs del sistema |
| NFR-003 | Rendimiento | Tiempo de renderizado de cariotipo en UI | Mediana | \<2 segundos | Prueba de rendimiento frontend |
| NFR-004 | Disponibilidad | Uptime en horario laboral (07-19) | SLA mensual | ≥99.5% | Monitoreo (Prometheus \+ Uptime Robot) |
| NFR-005 | Seguridad | Audit Trail | Cumplimiento | 21 CFR Part 11 | Auditoría externa \+ tests de integridad |
| NFR-006 | Seguridad | Firma de Supervisor | Autenticación | MFA obligatorio | Pruebas de autenticación |
| NFR-007 | Seguridad | Tiempo de inactividad por MFA fallido | Bloqueo | 15 minutos tras 3 fallos | Prueba de seguridad |
| NFR-008 | Privacidad | Datos PII | Almacenamiento | No salen del nodo institucional | Auditoría de red \+ inspección de logs |
| NFR-009 | Resiliencia | Tiempo máximo en modo degradado | Continuo | \<2 horas | Monitoreo \+ simulación de fallos |
| NFR-010 | Usabilidad | Rotación de cromosoma | Número de clics/acciones | Máximo 2 clics | Prueba de usabilidad think-aloud |
| NFR-011 | Escalabilidad | Throughput por laboratorio | Muestras/mes | ≥500 | Prueba de carga |
| NFR-012 | Integridad | Verificación de hash chain | Tiempo de verificación | \<100ms por cadena de 1000 registros | Test unitario |

---

## **11\. Trazabilidad MRD → PRD → FSD ⚡🔧**

| MRD (necesidad) | PRD (requerimiento) | FSD (caso de uso) | NFR | Prueba de aceptación |
| :---- | :---- | :---- | :---- | :---- |
| MRD-01 (anonimización) | PRD-REQ-001 | FSD-UC-001 | NFR-008 | TC-001 |
| MRD-02 (segmentación) | PRD-REQ-002 | FSD-UC-002 | NFR-001 | TC-002 |
| MRD-03 (clasificación) | PRD-REQ-003 | FSD-UC-002 | NFR-001 | TC-003 |
| MRD-04 (semaforización) | PRD-REQ-004 | FSD-UC-002 | N/A | TC-004 |
| MRD-05 (bloqueo) | PRD-REQ-005 | FSD-UC-004 | N/A | TC-005 |
| MRD-06 (XAI) | PRD-REQ-006 | FSD-UC-003 | N/A | TC-006 |
| MRD-07 (corrección manual) | PRD-REQ-007 | FSD-UC-003 | NFR-010 | TC-007 |
| MRD-08 (auditoría aleatoria) | PRD-REQ-008 | FSD-UC-005 | N/A | TC-008 |
| MRD-09 (audit trail) | PRD-REQ-009 | FSD-UC-005 | NFR-005, NFR-012 | TC-009 |
| MRD-10 (firma MFA) | PRD-REQ-010 | FSD-UC-005 | NFR-006, NFR-007 | TC-010 |
| MRD-11 (ISCN determinístico) | PRD-REQ-011 | FSD-UC-006 | N/A | TC-011 |
| MRD-12 (modo degradado) | PRD-REQ-012 | FSD-UC-007 | NFR-009 | TC-012 |

---

## **12\. Plan de pruebas funcionales 🔧**

Estrategia:

* Unitarias: pytest para backend (cobertura \>80% en servicios core, modelos, reglas de negocio). Jest \+ React Testing Library para frontend (cobertura \>70% en componentes críticos).  
* Integración: Pruebas de API con pytest \+ FastAPI TestClient. Verificación de integridad de hash chain. Validación de pipeline CV con imágenes sintéticas.  
* E2E: Playwright para flujos completos (carga → segmentación → corrección → firma).  
* Contract testing: Pacto entre frontend y backend para cada endpoint crítico.  
* Prompt-contract tests: Verificación de que los outputs de los agentes IA cumplen invariants y failure modes definidos en §7.

Herramientas:

* Backend: `pytest`, `pytest-asyncio`, `pytest-cov`, `locust` (carga)  
* Frontend: `Jest`, `React Testing Library`, `Playwright`  
* CV: `torchtest`, `opencv` (validación de máscaras)  
* Auditoría: Scripts personalizados para verificar hash chain

Cobertura mínima aceptada: 80% en módulos core (dominio, casos de uso), 70% en infraestructura (repositorios, API).

---

## **13\. Riesgos funcionales ⚡🔧**

| Riesgo | Probabilidad | Impacto | Mitigación | Responsable |
| :---- | :---- | :---- | :---- | :---- |
| Modelo IA no alcanza precisión prometida (IoU \<0.90) | Media | Alto | Dataset de validación con 2000 imágenes anotadas. Plan B: threshold ajustable por laboratorio. | ML Engineer |
| XAI\_GradCAM lento (\>1s) afecta TTK | Media | Medio | Precomputar heatmaps durante procesamiento inicial (no bajo demanda). | Backend |
| Hash chain causa bottleneck en DB | Baja | Bajo | Escritura por lotes cada 10 eventos, índices optimizados. | Backend |
| MFA no es aceptado por Supervisores | Media | Medio | Ofrecer múltiples métodos (TOTP, huella, tarjeta inteligente). Capacitación pre-lanzamiento. | Product |
| Modo degradado excede 2 horas por fallo de GPU | Baja | Alto | Failover a GPU secundaria automático. Contrato SLA con proveedor cloud. | DevOps |
| Override ISCN mal utilizado (cambios sin justificación) | Baja | Medio | Audit trail registra cada override. Dashboard de métricas para Supervisores con alerta si tasa de override \>10%. | Product |
| Pérdida de mapeo CHN por laboratorio | Baja | Alto | Mecanismo de hash salado (BRD sección 23). Laboratorio responsable de su sal. | Soporte |

---

## **14\. Glosario 🔧**

| Término | Definición |
| :---- | :---- |
| CHN | Código de Historia Clínica anonimizado. Formato CHN-YYYY-MM-DD-NNNN. |
| Confidence score | Valor entre 0 y 1 que indica la certeza del modelo IA en su clasificación. |
| Grad-CAM | Gradient-weighted Class Activation Mapping. Técnica de XAI que genera mapas de calor. |
| HITL | Human-in-the-loop. Paradigma donde la IA asiste pero el humano toma la decisión final. |
| IoU | Intersection over Union. Métrica de precisión de segmentación. |
| ISCN | International System for Human Cytogenomic Nomenclature. Estándar para reportes citogenéticos. |
| MFA | Autenticación Multifactor. Requiere dos o más métodos de verificación. |
| Override | Edición manual de un valor generado automáticamente por el sistema. |
| PII | Personally Identifiable Information. Datos que pueden identificar a un paciente. |
| TTK | Time to Karyotype. Tiempo desde carga de imagen hasta reporte firmado. |
| XAI | Explainable AI. Capacidad del sistema de justificar sus decisiones. |

---

## **15\. Registro de cambios ⚡🔧**

| Versión | Fecha | Autor | Cambio |
| :---- | :---- | :---- | :---- |
| v0.1 | Mayo 2026 | G. Mamani | Versión inicial del FSD clásico |
| v0.2 | Mayo 2026 | G. Mamani | Adición de tasks, prompts-contrato, trazabilidad completa |
| v1.0 | Mayo 2026 | G. Mamani | Versión final aprobada, alineada con PRD v1.0 y BRD v3.5 |

---

## **Checklist de entrega — modo FSD clásico 🔧**

* §0 Metadatos completos, modo declarado como FSD clásico 🔧, versión inicial commiteada en Git.  
* §1 Resumen ejecutivo (150–250 palabras).  
* §2 Alcance y fuera de alcance explícitos \+ §2.4 Plan técnico detallado \+ §2.5 Tasks (10 tasks ejecutables con prompt asociado).  
* §3 Actores y permisos.  
* ≥ 3 casos de uso críticos (7 casos documentados) con flujos principal, alternativos y excepciones, datos de entrada/salida y criterios Gherkin.  
* §5 Reglas de negocio con tipo y origen (9 reglas).  
* §6 Modelo de datos completo (diagrama Mermaid \+ diccionario completo).  
* Un prompt‑contrato por caso de uso crítico con los 6 elementos de la anatomía (§7, 3 prompts documentados).  
* §8 Integraciones externas con SLA y autenticación.  
* §9 \+ §9.1 Trazabilidad con M2 (Wireframe → Pantalla → UC).  
* §10 NFRs con métrica, umbral y forma de verificación (12 NFRs).  
* §11 Matriz de trazabilidad MRD → PRD → FSD → NFR → prueba.  
* §12 Plan de pruebas detallado (estrategia \+ herramientas \+ cobertura objetivo).  
* §13 Riesgos funcionales.  
* §14 Glosario.  
* §15 Registro de cambios.  
* Revisión por pares (otro grupo) registrada como comentarios en el PR.

