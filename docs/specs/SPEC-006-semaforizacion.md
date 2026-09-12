# SPEC-006: Implementación de Semaforización Visual Basada en Confidence Score

**Estado:** Borrador $\to$ Pendiente de Aprobación
**Referencia:** ADR-0006, RN-02
**Módulo:** Frontend (Editor de Cariotipos)

---

## 1. Capa Funcional (User Experience)

### 1.1. Indicadores Visuales de Confianza
El sistema debe asignar un color de borde y fondo al cromosoma basándose en el `confidence_score` recibido del motor de IA:

| Estado | Rango de Score | Color Visual | Significado Clínico | Acción Requerida |
| :--- | :--- | :--- | :--- | :--- |
| **Alta Confianza** | $\ge 0.85$ | **Verde** (`#1e8868`) | Predicción fiable | Revisión rutinaria / Auditoría 5% (RN-08) |
| **Baja Confianza** | $< 0.85$ | **Naranja** (`#d45100`) | Incertidumbre de IA | **Validación Manual Obligatoria** |
| **Error/Crítico** | $0.0 \text{ o Nulo}$ | **Rojo** (`#E30613`) | Fallo de segmentación/clasif. | Intervención manual inmediata |

### 1.2. Flujo de Bloqueo Clínico (RN-02)
- **Bloqueo de Exportación:** El botón "Generar Informe ISCN" debe permanecer deshabilitado (`disabled`) mientras exista al menos un cromosoma en estado **Naranja** o **Rojo** que no haya sido marcado como `validated = true`.
- **Feedback de Error:** Al intentar generar el informe con pendientes, debe mostrarse un alert: *"⚠ Debe validar los cromosomas de baja confianza antes de generar el informe"*.

---

## 2. Capa Técnica (Implementación)

### 2.1. Modelo de Datos (Frontend Store)
Se debe extender la interfaz de `Chromosome` en el store de Zustand:

```typescript
interface Chromosome {
  id: string;
  pair_number: number;
  confidence_score: number; // 0.0 to 1.0
  status: 'high' | 'low' | 'error'; // Derivado del score
  validated: boolean; // Cambia a true tras acción del analista
  // ... otros campos
}
```

### 2.2. Lógica de Renderizado en Konva.js
Para cada cromosoma renderizado en el canvas:
- **Stroke (Borde):** El color del borde del polígono/bounding box debe vincularse dinámicamente al `status`.
- **Glow Effect:** Los cromosomas "Naranja" deben tener un efecto de resplandor (glow) sutil para atraer la atención del analista.
- **Sincronización:** El color debe actualizarse en tiempo real al recibir el evento WebSocket `"Borrador listo"`.

### 2.3. Integración con Backend (WebSocket)
El frontend debe escuchar el payload de `ChromosomeDetail` y actualizar el estado global:
1. Recibe `confidence_score`.
2. Calcula `status` basado en el umbral $\ge 0.85$.
3. Actualiza el componente de Konva correspondiente mediante un `forceUpdate` o reactividad de Zustand.

### 2.4. Algoritmo de Validación de Exportación
Se implementará un selector en Zustand para calcular la disponibilidad del reporte:

```typescript
const canExportReport = useStore(state => 
  state.chromosomes.every(c => c.confidence_score >= 0.85 || c.validated === true)
);
```

---

## 3. Criterios de Aceptación (Validación)
- [ ] **CA-1:** Un cromosoma con score $0.72$ aparece automáticamente con borde naranja.
- [ ] **CA-2:** Un cromosoma con score $0.91$ aparece automáticamente con borde verde.
- [ ] **CA-3:** El botón "Generar Informe" está deshabilitado si hay un cromosoma naranja no validado.
- [ ] **CA-4:** Al hacer clic en "Aceptar" sobre un cromosoma naranja, este cambia a verde y el botón de informe se habilita (si no hay más pendientes).
- [ ] **CA-5:** El cambio de color es instantáneo tras la recepción del mensaje de WebSocket.
