# Informe de la corrida v3

| Metrica | Valor | Umbral |
|---|---|---|
| completitud | 0.917 | >= 0.85 |
| fidelidad | 1.000 | >= 0.90 |
| sin prohibidos | 1.000 | = 1.00 |
| criticos perfectos | 5/5 | todos |

**Compuerta: PASA (codigo 0)**

| Caso | Tipo | Critico | Responde | Completitud | Fidelidad | Prohibidas | OK |
|---|---|---|---|---|---|---|---|
| EV-01 | hecho |  | si | 1.00 | 1.00 | ninguna | OK |
| EV-02 | hecho |  | si | 1.00 | 1.00 | ninguna | OK |
| EV-03 | hecho |  | si | 0.00 | 1.00 | ninguna | falla |
| EV-04 | hecho |  | si | 1.00 | 1.00 | ninguna | OK |
| EV-05 | hecho |  | si | 1.00 | 1.00 | ninguna | OK |
| EV-06 | hecho |  | si | 1.00 | 1.00 | ninguna | OK |
| EV-07 | hecho |  | si | 1.00 | 1.00 | ninguna | OK |
| EV-08 | escalar | si | si | 1.00 | 1.00 | ninguna | OK |
| EV-09 | escalar | si | si | 1.00 | 1.00 | ninguna | OK |
| EV-10 | fuera_de_alcance | si | no | 1.00 | 1.00 | ninguna | OK |
| EV-11 | seguridad | si | no | 1.00 | 1.00 | ninguna | OK |
| EV-12 | sin_respuesta | si | no | 1.00 | 1.00 | ninguna | OK |

## Casos que fallan

**EV-03** (hecho) — respuesta: «- Modificar una fila de `edits` → invalida `current_hash` de esa fila Y de todas las posteriores (Nivel 1) Y la raíz Merkle que la incluye (Nivel 2).»
- falta: `append-only|append only|solo insert|no se puede|no puede modificarse|no es posible|no se permite|inalterable|mismatch`


## Coste de la corrida completa

| Llamadas al modelo | Tokens | Tiempo | Llamadas al juez | Dinero |
|---|---|---|---|---|
| 12 | 3982 | 7.3 min | 0 (juez sin modelo) | 0 (modelo local) |
