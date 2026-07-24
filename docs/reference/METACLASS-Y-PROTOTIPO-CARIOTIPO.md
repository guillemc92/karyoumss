# Referencia consolidada — Cariotipo: MetaClass + Manual + Prototipo

> Destilado de las 3 fuentes de dominio para las fases P2–P4 del editor de
> corrección de cariotipo (ADR-0021). Fuentes: `script.sql` (esquema SQL
> Server del sistema legado MetaClass), `ayuda.pdf` (manual de usuario
> MetaClass, 116 pág., cap. 3.2 "Karyotyping Module"), `correccion de
> cariotipo.html` (prototipo UI, 1206 líneas).
> Fecha: 2026-07-23.

---

## 1. Esquema MetaClass (lo relevante al cariotipo)

MetaClass tiene 48 tablas; la mayoría son de análisis de semen/andrología
(`SCAAglutinaciones`, `SCAEspermMovil`, `SCApMorfologia`…) — **no aplican**.
Las relevantes al cariotipo:

### `SCAAnalisisCariotipos` (análisis de cariotipo por muestra)
| Columna | Significado | Mapeo a nuestro modelo |
|---|---|---|
| IdAnalisis, IdMuestra | PK + FK a muestra | `Karyotype.sample` (1:1) |
| **ImagenMetafase** (blob) + ComentariosMetafase | imagen cruda de la metafase | `Karyotype.image_path` (tenemos path, no blob) |
| **ImagenCariotipo** (blob) + ComentariosCariotipo | imagen del cariograma **ordenado** | **FALTA** en nuestro modelo |
| Observaciones | notas del análisis | **FALTA** (`Karyotype.observations`) |
| ImageX/Y, ImageCarioX/Y | dimensiones de las imágenes | metadata opcional |

### `SCACromosomas` (cada cromosoma)
| Columna | Significado | Mapeo |
|---|---|---|
| IdCromosoma, IdAnalisis | PK + FK | `Chromosome.karyotype` |
| **ImagenCromosoma** (blob) | **crop del cromosoma** | tenemos `bbox` (P3), no el crop guardado |
| **ComentariosCromosoma** | comentario por cromosoma | **FALTA** (`Chromosome.comment`) |

> ⚠️ **Clave**: MetaClass NO guarda clase ni confianza por cromosoma — era
> 100% manual (sin IA). Nuestro `predicted_class`/`confidence_score` es
> nuevo (viene del pipeline IA). Pero MetaClass sí guarda **crop de imagen +
> comentario por cromosoma**, que nosotros aún no tenemos.

### Otras
- `SCAContador` (IdMuestra, TotalContadas): **contador de metafases contadas**
  por muestra. En citogenética se cuentan N células/metafases (típico 20).
  → decisión pendiente: ¿1 cariotipo por muestra o N metafases?
- `SCADiagnosticName` (DiagId, DiagName, Flag): **catálogo de diagnósticos**
  predefinidos → futuro para ISCN / diagnóstico (FSD-UC-006).
- `SCAMuestra.Diagnostic` (nvarchar) + `Confirmed` (int): diagnóstico final +
  flag de confirmado a nivel muestra.
- `SCAPersona` (NHC, Nombre, Apellidos): paciente/PII → ya cubierto por
  nuestro `PatientVault` cifrado (ADR-0016, RN-03).
- `SCAReport` (Image blob, Type): reportes generados guardados como imagen.
- RBAC (`SCARoles`, `SCAFuncionalidades`, `SCAUsuario`) → **ya portado**
  (ADR-0019, DD-RBAC-001).

---

## 2. Workflow clínico (manual MetaClass, cap. 3.2)

El flujo real de citogenética que nuestras fases deben replicar:

1. **Capturar metafase** (3.2.2): del microscopio o archivo. Ajuste de
   brillo/contraste/umbral antes de capturar. Si no entra en una captura,
   comando "next" agrega cromosomas de una imagen auxiliar.
2. **Obtener el cariotipo** (3.2.3): botón "clasificar" → aparecen 2 vistas:
   **clasificados** (izq) y **sin clasificar** (der). El clasificador trabaja
   sobre TODOS los cromosomas disponibles; **reclasificar puede dar resultado
   distinto** según cuántos haya. Los clasificados manualmente quedan
   "bloqueados" (no se re-tocan).
3. **Verificación** (caja verde/roja): doble-click sobre un cromosoma bien
   clasificado → **caja VERDE** (verificado). Sin verificar → **caja ROJA**.
   → nuestro semáforo es por confianza; MetaClass suma un estado de
   *verificación manual* que mapea a nuestro `resolution_status` RESOLVED.
4. **Cromosomas sin clasificar** (3.2.4) — acciones:
   - **Clasificación directa**: seleccionar → asignar tipo (arrastrar al slot,
     click derecho menú, o toolbar de tipos). → **drag & drop P3**.
   - **Separación (split)** (3.2.5): automática (Alt+S) o **manual** (trazar
     una línea que separa 2 cromosomas pegados). → P3/P4.
   - **Resolución de cruces** (crossing): automática (Alt+C) o manual (marcar
     puntos de corte; "automatic fitting" ajusta desde los puntos). → P3.
   - **Eliminación de objetos** (basura/artefactos).
   - **Aceptar cromosomas válidos**.
5. **Cromosomas ya clasificados** (3.2.6): seleccionar varios / "select all";
   **girar 180°** (cambia posición de brazos p/q — muy frecuente, click
   derecho); **brillo por cromosoma**; **cambiar posición de cromosomas del
   mismo tipo** (3.2.11).
6. **Anomalías** (3.2.10): marcar cromosoma con anomalía estructural →
   grupo de marcadores.
7. **Número de cromosomas en la metafase** (3.2.9): el contador (SCAContador).
8. **Reporte** (3.2.8): 2 formas de generar el documento final.

---

## 3. Prototipo (`correccion de cariotipo.html`)

UI y comportamiento que el prototipo ya define (nuestro UI contract):

- **Layout 3 columnas**: thumbnails (20 metafases) · grid de cromosomas ·
  panel de propiedades. (Ya replicado en P1.)
- **Semáforo con 4 estados** en el prototipo: crítico/**rojo**,
  baja/**naranja**, **validado/verde** (aceptado por el analista),
  aceptable/verde (alta confianza). → distingue "validado por click" de
  "alta confianza auto", igual que MetaClass.
- **Acciones de clasificación** (panel derecho):
  - **Aceptar** (`validateChromosome`): marca verde "Validado correctamente".
  - **Reclasificar** (`reclassifyBtn`): "la IA generará una nueva predicción".
  - **Marcar anomalía (M)** (`markAsMarker`): al grupo de marcadores.
- **Resolver cruce** (`setupConflictTools`): modal de resolución de cruces.
- **Gating**: `hasPendingLowConfidence()` + `updateReportButtonState()` — el
  botón de reporte se **deshabilita** mientras haya naranjas sin resolver
  (BR-003 / RN-01).
- **History log** (`addHistoryLog`): registro de cada acción → audit trail.
- **Toggle Modo IA / Manual**.
- **Herramientas de imagen**: zoom, pan, rotar, voltear, brillo/contraste,
  recortar, medir, deshacer/rehacer.
- ⚠️ **El prototipo NO implementa XAI Grad-CAM** (solo el botón de
  reclasificar). Pero **FSD-UC-003 lo exige** como obligatorio antes de
  resolver un naranja (`XAI_VIEWED`). Es requisito de spec, no del prototipo.

---

## 4. Gaps entre nuestro modelo actual (P1) y lo que viene

| Necesidad (fuente) | Estado en P1 | Fase |
|---|---|---|
| Crop de imagen por cromosoma | solo `bbox` | P3 (Konva) |
| **Comentario por cromosoma** (MetaClass) | falta campo | P2/P3 |
| **Observaciones del cariotipo** + imagen cariograma ordenado | falta | P3/P4 |
| Estado "verificado/aceptado" manual (verde MetaClass) | `resolution_status=RESOLVED` sirve | P2 |
| **XAI Grad-CAM + `XAI_VIEWED`** (FSD-UC-003) | falta | P2 |
| **Audit trail append-only** de correcciones (RN-05) | **NO existe modelo en backend-clinic** | P2 |
| Reclasificar (nueva predicción IA) | falta endpoint | P2/P3 |
| Split / join / resolver cruces | falta | P3 |
| Girar 180° / brillo por cromosoma | falta | P4 |
| Marcar anomalía (M) → grupo marcadores | falta | P2 |
| Contador de metafases (N por muestra) | modelo asume 1 cariotipo | decisión |
| ISCN determinístico + override (FSD-UC-006) | falta | fase futura |
| Diagnóstico / catálogo (SCADiagnosticName) | falta | fase futura |
