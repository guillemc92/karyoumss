# Prompt: Servicio Python — Generación Automática de ISCN

## Metadata
* **ID:** PR-UC03-ISCN
* **Componente:** `backend/app/services/iscn_generator.py`
* **Objetivo:** Generar el string clínico de cariotipo siguiendo el estándar ISCN 2020.

## Prompt Cuerpo
```
Role: Eres un especialista en bioinformática con profundo conocimiento de la nomenclatura ISCN 2020 y experiencia implementando generadores de nomenclatura citogenética en Python.

Task: Implementa el servicio ISCNGenerator que:
1. Recibe la clasificación final de 46 cromosomas
2. Genera la cadena ISCN estándar (ej: "46,XY" para cariotipo masculino normal)
3. El campo iscn_nomenclature es READ-ONLY una vez generado (no editable por el usuario)

Context:
- Estándar: ISCN 2020
- Formato básico: {número_cromosomas},{sexo} (ej: 46,XX)
- Restricción: si la clasificación tiene cromosomas sin validar, no debe generar nomenclatura

Reasoning:
1. Verificar que todos los 46 cromosomas estén validados antes de generar
2. Contar: número total de cromosomas, número de X, número de Y

Stop Condition: Detente cuando genere correctamente "46,XY" para masculino normal, "47,XY,+21" para trisomía 21 y rechace si hay no validados.

Output: Servicio Python:
- `backend/app/services/iscn_generator.py`
```
