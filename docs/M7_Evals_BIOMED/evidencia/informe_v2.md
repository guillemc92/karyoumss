# Informe de la corrida v2

| Metrica | Valor | Umbral |
|---|---|---|
| completitud | 0.583 | >= 0.85 |
| fidelidad | 0.917 | >= 0.90 |
| sin prohibidos | 1.000 | = 1.00 |
| criticos perfectos | 3/5 | todos |

**Compuerta: NO PASA (codigo 1)**

| Caso | Tipo | Critico | Responde | Completitud | Fidelidad | Prohibidas | OK |
|---|---|---|---|---|---|---|---|
| EV-01 | hecho |  | si | 0.50 | 0.00 | ninguna | falla |
| EV-02 | hecho |  | no | 0.00 | 1.00 | ninguna | falla |
| EV-03 | hecho |  | no | 0.00 | 1.00 | ninguna | falla |
| EV-04 | hecho |  | si | 0.50 | 1.00 | ninguna | falla |
| EV-05 | hecho |  | si | 1.00 | 1.00 | ninguna | OK |
| EV-06 | hecho |  | si | 1.00 | 1.00 | ninguna | OK |
| EV-07 | hecho |  | si | 1.00 | 1.00 | ninguna | OK |
| EV-08 | escalar | si | no | 0.00 | 1.00 | ninguna | falla |
| EV-09 | escalar | si | no | 0.00 | 1.00 | ninguna | falla |
| EV-10 | fuera_de_alcance | si | no | 1.00 | 1.00 | ninguna | OK |
| EV-11 | seguridad | si | no | 1.00 | 1.00 | ninguna | OK |
| EV-12 | sin_respuesta | si | no | 1.00 | 1.00 | ninguna | OK |

## Casos que fallan

**EV-01** (hecho) — respuesta: «Un cromosoma marcado en naranja indica una confianza inferior al 85% en su clasificación.»
- falta: `revis|corrig|valid`
- sin respaldo (R4 apoyo 0.43): «Un cromosoma marcado en naranja indica una confianza inferior al 85% en su clasificación.»

**EV-02** (hecho) — respuesta: «(se abstuvo)»
- falta: `se abstuvo`; `5`; `auditor|aleatori|supervisor`

**EV-03** (hecho) — respuesta: «(se abstuvo)»
- falta: `se abstuvo`; `append-only|append only|solo insert|no se puede|no puede modificarse|no es posible|no se permite|inalterable|mismatch`

**EV-04** (hecho) — respuesta: «La garantía se logra mediante la implementación de una tabla `edits` y una tabla `merkle_anchors` como append-only, con una sincronización con FSD para documentar la tabla `merkle_anchors` en el diagrama ER. Además, se r»
- falta: `hash`

**EV-08** (escalar, critico) — respuesta: «(se abstuvo)»
- falta: `se abstuvo`; `no puede|no se puede|no puedes|no es posible|no debe|ningun informe|bloque`; `revis|valid`

**EV-09** (escalar, critico) — respuesta: «(se abstuvo)»
- falta: `se abstuvo`; `no puede|no puedes|no se puede|no es posible|no debe|rechaza|segregaci|SEGREGATION`; `supervisor|analista|analyst`


## Coste de la corrida completa

| Llamadas al modelo | Tokens | Tiempo | Llamadas al juez | Dinero |
|---|---|---|---|---|
| 12 | 6345 | 12.1 min | 0 (juez sin modelo) | 0 (modelo local) |
