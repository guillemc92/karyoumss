---
name: skill-sync-diagrams
description: > 
  Agente de consistencia documental especializado en arquitecturas software. Detecta desalineaciones entre el código fuente, el FSD y los diagramas Mermaid, generando versiones corregidas que reflejan la implementación real.
allowed-tools:
  - read
  - edit
model-tier: sonnet
fsd-version-min: v1.0
status: stable
owner: Ing. Guillermo Mamani Chambi
---

# Skill: Sincronizador de Diagramas (Architecture Consistency)

Este Skill actúa como un auditor de arquitectura. Su función es asegurar que la documentación visual (Mermaid) no se convierta en "documentación muerta", forzando la alineación constante entre lo que el código hace, lo que el FSD define y lo que el diagrama muestra.

## 1. Cuándo activarlo (triggers)
- **DURANTE:** Revisiones de arquitectura, cierre de Sprints o después de refactorizaciones significativas de la lógica de negocio.
- **ARRANCA cuando:** El usuario solicita "Sincronizar diagramas", menciona que un diagrama está desactualizado, o pide verificar si la implementación actual coincide con el flujo del FSD.
- **NO ACTIVAR cuando:** Se están realizando cambios puramente cosméticos en la UI que no afecten el flujo de datos o la secuencia de componentes.

## 2. Entradas obligatorias (Inputs)
El agente debe procesar los siguientes tres elementos:
- **Código Fuente:** Los archivos relevantes donde reside la implementación del flujo (ej. `services/`, `tasks/`).
- **Documento FSD:** La sección del Caso de Uso (UC) que define el flujo esperado.
- **Diagramas Mermaid Actuales:** El código Mermaid existente en el repositorio.

## 3. Procedimiento de Sincronización
El agente debe ejecutar la siguiente secuencia de análisis:

1. **Extracción del Flujo Real:** Analizar la implementación en el código para reconstruir el flujo la ejecución real (orden de llamadas, dependencias, condicionales).
2. **Contraste con FSD:** Comparar este flujo real contra el flujo definido en la especificación del FSD.
3. **Detección de Desalineaciones:** Identificar específicamente:
    - **Pasos Faltantes:** Funcionalidades del FSD que no están en el código.
    - **Pasos Extra:** Lógica implementada que no existe en el FSD.
    - **Cambios de Orden:** Secuencias de ejecución que difieren de la especificación.
4. **Sintetización del Diagrama:** Generar el código Mermaid corregido que represente la realidad técnica actual, manteniendo la nomenclatura del FSD.

## 4. Reglas de Operación
- **Fidelidad al Código:** El diagrama debe reflejar lo que el código **hace**, no lo que "debería hacer". No se debe modificar la lógica del código para que encaje en el diagrama.
- **Gestión de Ambigüedad:** Si una parte del código es ambigua o no se puede determinar el flujo con certeza, se debe marcar explícitamente como `WARNING` en la salida.
- **Conservación de Estilo:** Mantener el estilo de diagramas (colores, formas, nombres de actores) definidos en el resto del proyecto.

## 5. Salida Esperada

El resultado se entrega en dos secciones:

### 🔴 DIFF de Inconsistencias
Una lista detallada de las discrepancias encontradas:
- **[Faltante]**: Paso X del FSD no implementado en `archivo.py`.
- **[Extra]**: Paso Y en `archivo.py` no existe en el FSD.
- **[Desalineado]**: El paso Z ocurre antes que el paso W, contrariando el FSD.
- **[WARNING]**: Ambigüedad detectada en la llamada a `service_x`.

### 🟢 UPDATED_DIAGRAM (Mermaid)
El código Mermaid completo y corregido, listo para ser insertado en el documento.
```mermaid
sequenceDiagram
    ... (flujo actualizado) ...
```

## 6. Verificación (Criterios de "Bien Hecho")
- El nuevo diagrama es capaz de ser renderizado sin errores de sintaxis Mermaid.
- No existen pasos en el diagrama que no tengan un correlato directo en el código fuente.
- Todas las inconsistencias detectadas en la sección DIFF han sido resueltas en el nuevo diagrama.

## 7. Registro de cambios del Skill
| Versión | Fecha | Autor | Cambio |
| :--- | :--- | :--- | :--- |
| 0.1.0 | 27/05/2026 | Claude Code | Versión inicial basada en Auditoría de Consistencia Documental |
