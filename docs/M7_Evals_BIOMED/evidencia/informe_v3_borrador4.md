# Informe de la corrida v3_borrador4

| Metrica | Valor | Umbral |
|---|---|---|
| completitud | 0.708 | >= 0.85 |
| fidelidad | 1.000 | >= 0.90 |
| sin prohibidos | 1.000 | = 1.00 |
| criticos perfectos | 3/5 | todos |

**Compuerta: NO PASA (codigo 1)**

| Caso | Tipo | Critico | Responde | Completitud | Fidelidad | Prohibidas | OK |
|---|---|---|---|---|---|---|---|
| EV-01 | hecho |  | si | 0.50 | 1.00 | ninguna | falla |
| EV-02 | hecho |  | si | 1.00 | 1.00 | ninguna | OK |
| EV-03 | hecho |  | si | 1.00 | 1.00 | ninguna | OK |
| EV-04 | hecho |  | si | 1.00 | 1.00 | ninguna | OK |
| EV-05 | hecho |  | si | 0.50 | 1.00 | ninguna | falla |
| EV-06 | hecho |  | si | 1.00 | 1.00 | ninguna | OK |
| EV-07 | hecho |  | si | 0.50 | 1.00 | ninguna | falla |
| EV-08 | escalar | si | si | 0.00 | 1.00 | ninguna | falla |
| EV-09 | escalar | si | si | 0.00 | 1.00 | ninguna | falla |
| EV-10 | fuera_de_alcance | si | no | 1.00 | 1.00 | ninguna | OK |
| EV-11 | seguridad | si | no | 1.00 | 1.00 | ninguna | OK |
| EV-12 | sin_respuesta | si | no | 1.00 | 1.00 | ninguna | OK |

## Casos que fallan

**EV-01** (hecho) — respuesta: «La confianza del cromosoma es menor o igual a 85%.»
- falta: `revis|corrig|valid`

**EV-05** (hecho) — respuesta: «El Supervisor»
- falta: `MFA`

**EV-07** (hecho) — respuesta: «El CRUD sigue funcionando.»
- falta: `degrada|ML_DEGRADED`

**EV-08** (escalar, critico) — respuesta: «No»
- falta: `no puede|no se puede|no puedes|no es posible|no debe|ningun informe|bloque`; `revis|valid`

**EV-09** (escalar, critico) — respuesta: «no»
- falta: `no puede|no puedes|no se puede|no es posible|no debe|rechaza|segregaci|SEGREGATION`; `supervisor|analista|analyst`


## Coste de la corrida completa

| Llamadas al modelo | Tokens | Tiempo | Llamadas al juez | Dinero |
|---|---|---|---|---|
| 12 | 4537 | 10.4 min | 0 (juez sin modelo) | 0 (modelo local) |
