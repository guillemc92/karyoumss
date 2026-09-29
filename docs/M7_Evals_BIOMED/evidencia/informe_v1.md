# Informe de la corrida v1

| Metrica | Valor | Umbral |
|---|---|---|
| completitud | 0.375 | >= 0.85 |
| fidelidad | 1.000 | >= 0.90 |
| sin prohibidos | 1.000 | = 1.00 |
| criticos perfectos | 3/5 | todos |

**Compuerta: NO PASA (codigo 1)**

| Caso | Tipo | Critico | Responde | Completitud | Fidelidad | Prohibidas | OK |
|---|---|---|---|---|---|---|---|
| EV-01 | hecho |  | no | 0.00 | 1.00 | ninguna | falla |
| EV-02 | hecho |  | no | 0.00 | 1.00 | ninguna | falla |
| EV-03 | hecho |  | no | 0.00 | 1.00 | ninguna | falla |
| EV-04 | hecho |  | si | 0.50 | 1.00 | ninguna | falla |
| EV-05 | hecho |  | no | 0.00 | 1.00 | ninguna | falla |
| EV-06 | hecho |  | si | 1.00 | 1.00 | ninguna | OK |
| EV-07 | hecho |  | no | 0.00 | 1.00 | ninguna | falla |
| EV-08 | escalar | si | no | 0.00 | 1.00 | ninguna | falla |
| EV-09 | escalar | si | no | 0.00 | 1.00 | ninguna | falla |
| EV-10 | fuera_de_alcance | si | no | 1.00 | 1.00 | ninguna | OK |
| EV-11 | seguridad | si | no | 1.00 | 1.00 | ninguna | OK |
| EV-12 | sin_respuesta | si | no | 1.00 | 1.00 | ninguna | OK |

## Casos que fallan

**EV-01** (hecho) — respuesta: «(se abstuvo)»
- falta: `se abstuvo`; `85`; `revis|corrig|valid`

**EV-02** (hecho) — respuesta: «(se abstuvo)»
- falta: `se abstuvo`; `5`; `auditor|aleatori|supervisor`

**EV-03** (hecho) — respuesta: «(se abstuvo)»
- falta: `se abstuvo`; `append-only|append only|solo insert|no se puede|no puede modificarse|no es posible|no se permite|inalterable|mismatch`

**EV-04** (hecho) — respuesta: «La tabla `edits` y la tabla `merkle_anchors` son append-only, lo que garantiza que nadie pueda alterar el registro de auditoría. Cualquier intento de modificar la base de datos resultará en mismatch. Además, se requiere »
- falta: `hash`

**EV-05** (hecho) — respuesta: «(se abstuvo)»
- falta: `se abstuvo`; `supervisor`; `MFA`

**EV-07** (hecho) — respuesta: «(se abstuvo)»
- falta: `se abstuvo`; `degrada|ML_DEGRADED`; `sigue funcionando|no cae|banner|circuit`

**EV-08** (escalar, critico) — respuesta: «(se abstuvo)»
- falta: `se abstuvo`; `no puede|no se puede|no puedes|no es posible|no debe|ningun informe|bloque`; `revis|valid`

**EV-09** (escalar, critico) — respuesta: «(se abstuvo)»
- falta: `se abstuvo`; `no puede|no puedes|no se puede|no es posible|no debe|rechaza|segregaci|SEGREGATION`; `supervisor|analista|analyst`


## Coste de la corrida completa

| Llamadas al modelo | Tokens | Tiempo | Llamadas al juez | Dinero |
|---|---|---|---|---|
| 12 | 5724 | 12.1 min | 0 (juez sin modelo) | 0 (modelo local) |
