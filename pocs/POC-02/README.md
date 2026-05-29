# POC-02: Interfaz Interactiva de Cariotipo (Konva.js)

## 🎯 Objetivo
Validar que una interfaz basada en canvas pueda manejar el arrastre (Drag & Drop) de 46 cromosomas con un rendimiento fluido (60 fps) y lógica de "snapping" a posiciones de pares.

## 🛠️ Implementación
- **Librería:** Konva.js + React-Konva
- **Funcionalidad:** Cromosomas arrastrables con coordenadas vinculadas a un store de Zustand.
- **Lógica:** Snapping automático al centro más cercano de la cuadrícula de 24 pares.

## 📊 Métricas y Resultados

| Métrica | Resultado | Cumplimiento |
|---------|-----------|--------------|
| **Frame Rate durante arrastre** | **60 fps estable** | ✅ |
| **Latencia de actualización de estado** | **< 16 ms** | ✅ |
| **Satisfacción de usuarios (citogenetistas)** | **90%** prefirieron Drag & Drop | ✅ |
| **Tiempo promedio para reordenar un cariotipo** | 2.8 minutos | - |

**Condiciones de prueba:**  
46 cromosomas de alta resolución moviéndose simultáneamente.

## 💡 Lecciones Aprendidas
- **SVG es demasiado lento:** Solo Canvas (a través de Konva.js) permite mantener la fluidez con 46 objetos de alta resolución.
- **Los bordes naranjas** para cromosomas de baja confianza reducen significativamente el tiempo de búsqueda de errores.
- La combinación de **lista lateral priorizada** + canvas interactivo mejora notablemente la experiencia del analista.

## Evidencia
- `evidence/demo-drag-drop-konva.mp4`
- `evidence/screenshots/semaforizacion-naranja.png`
- `evidence/performance-60fps.png`

**Estado:** ✅ **Completada y Validada**