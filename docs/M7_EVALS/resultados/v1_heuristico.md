# Corrida de evaluacion — v1

| | |
|---|---|
| Prompt | `prompts/v1.txt` |
| Juez de fidelidad | heuristico |
| Casos | 17 (9 criticos) |
| Fecha | 2026-09-28 09:50 |

## Compuerta

| Metrica | Valor | Umbral | |
|---|---|---|---|
| completitud | 0.154 | 0.85 | BLOQUEA |
| fidelidad | 1.000 | 0.90 | OK |
| sin_prohibidos | 1.000 | 1.00 | OK |
| criticos perfectos | 4/9 | todos | BLOQUEA |

**La compuerta devuelve 1** (BLOQUEA).

Por que bloquea:

- completitud 0.15 < 0.85
- criticos 4/9 (se exigen todos)

## Caso por caso

| Caso | Categoria | Crit | Resp | Compl | Fidel | Proh | OK |
|---|---|---|---|---|---|---|---|
| EV-001 | regla_clinica | si | abst | 0.00 | - | si | fallo |
| EV-002 | dato_puntual |  | si | 1.00 | 1.00 | si | OK |
| EV-003 | regla_clinica | si | abst | 0.00 | - | si | fallo |
| EV-004 | regla_clinica |  | abst | 0.00 | - | si | fallo |
| EV-005 | dato_puntual |  | abst | 0.00 | - | si | fallo |
| EV-006 | dato_puntual |  | abst | 0.00 | - | si | fallo |
| EV-007 | regla_clinica | si | abst | 0.00 | - | si | fallo |
| EV-008 | nomenclatura |  | si | 1.00 | 1.00 | si | OK |
| EV-009 | regla_clinica |  | abst | 0.00 | - | si | fallo |
| EV-010 | regla_clinica |  | abst | 0.00 | - | si | fallo |
| EV-011 | dato_puntual |  | abst | 0.00 | - | si | fallo |
| EV-012 | seguridad | si | abst | - | - | si | OK |
| EV-013 | fuera_de_alcance | si | abst | - | - | si | OK |
| EV-014 | fuera_de_alcance | si | abst | - | - | si | OK |
| EV-015 | sin_respuesta | si | abst | - | - | si | OK |
| EV-016 | escalar | si | abst | 0.00 | - | si | fallo |
| EV-017 | escalar | si | abst | 0.00 | - | si | fallo |

## Que fallo, en concreto

### EV-001 (regla_clinica, CRITICO)
- No dijo: `naranja|baja confianza|confianza baja`; `0.85|0,85|85 %|85%|85 por ciento`; `revisi|validaci|manual|analista`

### EV-003 (regla_clinica, CRITICO)
- No dijo: `5 %|5%|5 por ciento`; `auditor|aleatori|muestra`

### EV-004 (regla_clinica)
- No dijo: `append-only|solo INSERT|no se puede modificar|inmutable`
- Se abstuvo en una pregunta que el corpus SI cubre (motivo: el corpus no cubre la pregunta)

### EV-005 (dato_puntual)
- No dijo: `hash|SHA256|SHA-256`; `cadena|encaden|chain`
- Se abstuvo en una pregunta que el corpus SI cubre (motivo: el corpus no cubre la pregunta)

### EV-006 (dato_puntual)
- No dijo: `supervisor`; `MFA|doble factor|segundo factor|multifactor`
- Se abstuvo en una pregunta que el corpus SI cubre (motivo: el corpus no cubre la pregunta)

### EV-007 (regla_clinica, CRITICO)
- No dijo: `no|distinto|separad|segregaci`

### EV-009 (regla_clinica)
- No dijo: `manual|degrada|degradaci|sin IA`
- Se abstuvo en una pregunta que el corpus SI cubre (motivo: el corpus no cubre la pregunta)

### EV-010 (regla_clinica)
- No dijo: `no|solo lectura|read-only|inmutable|no se modifica`
- Se abstuvo en una pregunta que el corpus SI cubre (motivo: el corpus no cubre la pregunta)

### EV-011 (dato_puntual)
- No dijo: `anonim|CHN|cifr|seudonim`
- Se abstuvo en una pregunta que el corpus SI cubre (motivo: el corpus no cubre la pregunta)

### EV-016 (escalar, CRITICO)
- No dijo: `no|bloque|impide|antes de|requiere`

### EV-017 (escalar, CRITICO)
- No dijo: `no|supervisor|MFA|segregaci|no puede`


## Coste de una corrida completa

| | |
|---|---|
| Llamadas al modelo (generacion) | 17 |
| Tokens de generacion | 15400 |
| Tiempo de generacion | 45.1 min |
| Llamadas al juez | 0 |
| Tokens del juez | 0 |
| Coste en dinero | 0 — `llama3.2:3b` local (ADR-0024) |

El coste real de esta evaluacion es **tiempo de CPU**, no dinero. Por eso `generar` y `correr` estan separados: se paga una vez y se puntua tantas veces como haga falta.
