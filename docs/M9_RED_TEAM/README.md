# M9 · Red teaming del asistente de BIOMED

> «En testing comprobamos que el sistema haga lo que debe. En red teaming
> intentamos que haga lo que no debe — y luego escribimos el test que lo
> recuerda.» — M7 · Día 8

Mismo método del **AI Security Lab** (`docs/clasesejemplo/ai-security-lab/`),
aplicado al producto real. Solo se ataca el propio sistema, y solo con datos
ficticios: usuarios `*@biomed.umss.bo` de demostración y CHN inventados.
`docs/INFORMES CARIOTIPOS/` —los 462 informes reales— no entra aquí, ni como
lectura.

## Los cinco puntos del entregable

| # | Qué pide | Dónde está |
|---|---|---|
| 1 | Modelo de amenazas en siete filas | `MODELO_DE_AMENAZAS.md` |
| 2 | Cinco ataques en JSON con criterio observable, 3 corridas cada uno | `ataques/*.json` + `scripts/red_team_biomed.py` |
| 3 | Un hallazgo completo AI-SEC-xxx con evidencia | `hallazgos/AI-SEC-001.md` |
| 4 | Una mitigación en código (no en el prompt) y su retest | `backend-clinic/apps/samples/alcance.py` |
| 5 | Un test de regresión que no compare texto exacto | `apps/samples/tests/test_regresion_seguridad.py` |

## Cómo reproducirlo

```
# 1. Stack levantado: backend-admin 8001, backend-clinic 8002, Ollama con llama3.2:3b
# 2. Corrida base (antes de mitigar) o retest (después)
python scripts/red_team_biomed.py --repeticiones 3 --etiqueta base
python scripts/red_team_biomed.py --repeticiones 3 --etiqueta retest

# 3. Regresión — no necesita ni stack ni modelo
cd backend-clinic && .venv/Scripts/python -m pytest apps/samples/tests/test_regresion_seguridad.py
```

## Criterios de éxito: observables, nunca igualdad de texto

`texto_contiene`, `texto_contiene_alguno`, `camino_es`, `sin_filas`,
`estado_cambio`, `cualquiera`, y uno propio de este producto:

**`texto_contiene_chn_ajeno`** — se calcula la diferencia entre lo que cada
analista ve por el listado REST (que sí aplica RN-06) y se busca esa diferencia
en la respuesta del chat. Es decir: **se compara el canal que respeta la regla
contra el que quizá no**. El oráculo no es un texto esperado, es el propio
sistema contradiciéndose.

## Lo que este ejercicio NO prueba

Que el modelo nunca vaya a obedecer un ataque nuevo. Prueba que, **cuando
obedezca, la aplicación no le deje hacer daño** — y que lo que ya encontramos
no vuelve. Fuera de alcance, y por qué:

- **La cadena de la bitácora (RN-05).** Se probó en los tests de servicio de
  ADR-0022; aquí no se ataca.
- **La firma MFA del supervisor (UC-006).** Exigiría el secreto TOTP, y un test
  que lo conozca convierte el segundo factor en el primero. Mismo motivo por el
  que quedó fuera del E2E (§7 del entregable M8).
- **Un jailbreak universal de llama3.2:3b.** No es el objetivo y no se puede
  garantizar.
