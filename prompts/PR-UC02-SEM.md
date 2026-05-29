# Prompt: Componente React — Semaforización Visual de Cariotipos

## Metadata
* **ID:** PR-UC02-SEM
* **Componente:** `frontend/src/components/EditorCanvas/ChromosomeCanvas.tsx`
* **Objetivo:** Renderizar en el canvas Konva.js los cromosomas con bordes naranja/verde según su nivel de confianza.

## Prompt Cuerpo
```
Role: Eres un desarrollador frontend senior especializado en React con Konva.js para canvas interactivos y en UX para aplicaciones médicas.

Task: Implementa el componente ChromosomeCanvas que:
1. Renderiza cromosomas en Konva.js Stage con border color según confidence_score
2. Verde (#00e676) para score ≥ 0.85, Naranja (#ff6d00) para score < 0.85
3. El borde naranja debe ser 3px (vs 1px verde) para mayor visibilidad
4. El botón "Generar Informe" debe estar DESHABILITADO si existen cromosomas < 0.85 sin validar

Context:
- Stack: React 18 + Konva.js 9 + Zustand (estado global)
- Estructura de datos: [{id, pair, confidence_score, validated, requires_review}]

Reasoning:
1. Usar Konva.js Shape con stroke dinámico según score
2. El estado de validación debe vivir en Zustand store
3. El botón "Generar Informe" debe suscribirse al store y recalcular

Stop Condition: Detente cuando: (1) el semáforo muestre correctamente verde/naranja, (2) el botón se bloquee con cromosomas pendientes.

Output: Componentes React en TypeScript:
- `frontend/src/components/EditorCanvas/ChromosomeCanvas.tsx`
- `frontend/src/store/chromosomeStore.ts`
```
