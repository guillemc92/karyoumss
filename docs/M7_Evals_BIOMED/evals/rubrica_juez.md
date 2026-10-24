# Rúbrica del juez de fidelidad

**Pregunta que responde el juez:** ¿lo que afirma la respuesta sale del contexto que el asistente tenía delante?

No juzga si la respuesta es verdad en general, ni si responde bien la pregunta —eso lo mide la completitud—. Solo si cada afirmación se apoya en los fragmentos del caso.

## Reglas

| Regla | Qué dice |
|---|---|
| **R1** | La respuesta se divide en oraciones. |
| **R2** | Una frase de gestión sin cifras («no puedo…», «no encuentro…», «consulte con…») cuenta como **respaldada**: no afirma nada del laboratorio. |
| **R3** | Cualquier otra oración está respaldada solo si **todos sus números** aparecen en el contexto. Una cifra inventada es la alucinación que más daño hace en un informe clínico, y es la única que se detecta sin juzgar sentido. |
| **R4** | Y además, al menos **la mitad de sus palabras de contenido** (sin artículos ni conectores, de más de dos letras, sin tildes) aparecen en el contexto. |
| **R5** | **Fidelidad = oraciones respaldadas ÷ oraciones totales.** |

Casos especiales:

- Si el asistente **se abstiene** (`responde = false`), no afirma nada: fidelidad 1. Que abstenerse fuera correcto o no lo decide la completitud.
- Para calibrar contra una persona, el veredicto por caso es **fiel** si la fidelidad es 1 (todas las oraciones respaldadas) y **no fiel** en otro caso.

## De dónde sale

Es la rúbrica del `JuezHeuristico` del laboratorio de Evals offline (Día 10), aplicada sin cambios de fondo. Se eligió el juez heurístico y no el modelo como juez por tres razones:

1. **Determinista:** dos personas puntúan la misma corrida y obtienen el mismo número.
2. **Sin coste ni red:** la compuerta puede correr en CI en segundos.
3. **Regla visible:** quien discrepe de un veredicto puede ver exactamente qué regla lo produjo (el informe indica R2, R3 o R4 en cada oración sin respaldo).

## Límites conocidos

- **No entiende paráfrasis.** Una oración correcta dicha con otras palabras puede caer por debajo de R4 (falsa alarma).
- **No detecta una definición inventada dentro de una frase respaldada.** «MFA (Método de Autenticación de Seguridad)» comparte casi todas sus palabras con la fuente; la expansión falsa pasa. Medido en la calibración del 28/09 sobre el RAG completo.

Por eso el juez se **calibra** contra calificaciones humanas (`evaluar.py calibrar`) y el acuerdo y la kappa se reportan junto a la cifra de fidelidad.
