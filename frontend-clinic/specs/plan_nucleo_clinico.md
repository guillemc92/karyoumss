# Plan de pruebas E2E — Núcleo clínico de cariotipado

**Origen:** producido por el agente *Planner* (`scripts/e2e_planner.py`, modelo
`llama3.2:3b` local) sobre las 10 rutas reales de `frontend-clinic`, los 7 casos
de uso del FSD y las reglas RN-01..RN-09. Salida cruda intacta en
`docs/M8_E2E/plan_crudo.txt`.
**Tokens del Planner:** entrada 913 · salida 894 · 732,3 s.
**Revisión humana marcada con `AUDITORÍA`.**

## Resumen de la aplicación

Diez pantallas bajo `/clinic`: listado de muestras (entrada), registro con
captura de metafases, detalle, visor de cariotipo con semaforización, formulario
de edición, bandeja del supervisor, consultas en lenguaje natural y modo
degradado. La autenticación no vive aquí: backend-admin es la única autoridad de
JWT (ADR-0020), y el clínico solo valida el token.

## El hallazgo de la auditoría del plan

**5 de los 8 casos emparejaban el caso de uso *N* con la regla *RN-0N* por
POSICIÓN, no por significado.** Le di dos listas al Planner y las cerró con
cremallera:

```
E2E-01 -> RN-01    E2E-05 -> RN-08
E2E-02 -> RN-02    E2E-06 -> RN-05
E2E-03 -> RN-03    E2E-07 -> RN-07
E2E-04 -> RN-04    E2E-08 -> RN-06
```

Generar sobre ese plan habría producido tests sintácticamente impecables que
comprueban **la regla equivocada**, y en verde.

---

## 1. Registro e ingesta

### 1.1 Registro de muestra con metafases
**Pasos:** abrir `/clinic/samples/register`; rellenar CHN único, paciente e
imágenes; enviar.
**Resultado esperado:** la muestra existe con su CHN y la interfaz **no afirma
haber analizado las tres metafases** (ADR-0036: se sube N y se analiza 1).
`AUDITORÍA: CORREGIDO. El Planner le puso RN-01 (validar naranjas), que no
interviene en la ingesta. Sustituido por el oráculo real del flujo.`

### 1.2 Listado del analista
**Pasos:** abrir `/clinic/samples`.
**Resultado esperado:** se ve el encabezado de gestión y **ningún aviso de
acceso denegado** — el analista es dueño de lo que ve (RN-06).
`AUDITORÍA: AÑADIDO. El Planner no propuso ni un caso para la pantalla de
entrada, que es por la que pasa todo usuario.`

## 2. Cariotipo y semaforización

### 2.1 Semáforo por confianza
**Pasos:** abrir el visor de un caso con cromosomas de confianza dispar.
**Resultado esperado:** un cromosoma con 0,40 se muestra naranja y uno con 0,95
verde, en la misma pantalla (RN-02).
`AUDITORÍA: CORREGIDO. El oráculo era correcto pero el criterio decía «confianza
SUPERIOR a 0,85», invirtiendo la regla.`

### 2.2 Bloqueo de emisión por naranjas sin resolver
**Pasos:** con un naranja en PENDING, intentar validar el caso.
**Resultado esperado:** la validación queda bloqueada y la interfaz dice cuántos
faltan (RN-01 + RN-02).
`AUDITORÍA: CORREGIDO. El Planner mezclaba flujo XAI, ruta /edit —que es el
formulario, no el visor— y oráculo RN-03 (PII). Tres cosas que no encajaban.`

## 3. Segregación de funciones

### 3.1 Analista ajeno al caso
**Pasos:** con sesión de analista, abrir un caso que no es suyo.
**Resultado esperado:** 403 y aviso en pantalla, no una pantalla rota (RN-06).
`AUDITORÍA: CORREGIDO. El Planner ponía ruta /supervisor y oráculo RN-04 (ISCN).`

### 3.2 El supervisor ve cualquier caso
**Pasos:** con sesión de supervisor, abrir un caso que no registró él.
**Resultado esperado:** lo ve completo.
`AUDITORÍA: CORREGIDO. El Planner escribió el criterio INVERTIDO: «el supervisor
no puede acceder a casos que no son suyos». RN-06 dice lo contrario.`

## 4. Informe

### 4.1 El ISCN es de solo lectura
**Pasos:** abrir el detalle de un caso con ISCN generado.
**Resultado esperado:** la interfaz no ofrece ningún control para editarlo
(RN-04).
`AUDITORÍA: CORREGIDO. El Planner le asignó RN-05 (bitácora append-only) a un
flujo de ISCN.`

### 4.2 Auditoría aleatoria del 5 %
`AUDITORÍA: DESCARTADO. El criterio era circular («se ha realizado
correctamente»), que es fallar la pregunta 3. Y el flujo exige un caso en
ANALYST_VALIDATED con la auditoría completa, un estado que E2E no monta barato.
Va a evals.`

## 5. Degradación y sesión

### 5.1 Modo degradado
**Pasos:** con backend-ml caído, registrar una muestra.
**Resultado esperado:** la muestra queda registrada y aparece el banner de modo
manual (RN-07).
`AUDITORÍA: OK. Único caso del Planner aceptado sin tocar: flujo, ruta y oráculo
coherentes entre sí.`

### 5.2 Sin token no hay datos clínicos
**Pasos:** abrir `/clinic/samples` sin token en localStorage.
**Resultado esperado:** no se muestran datos de pacientes (ADR-0020, RN-03).
`AUDITORÍA: AÑADIDO. Es el caso límite que protege RN-03 en la frontera de la
sesión, y el Planner no lo contempló.`

## 6. Consultas en lenguaje natural

### 6.1 La respuesta declara su procedencia
**Pasos:** abrir `/clinic/consultas`, escribir una consulta, enviar.
**Resultado esperado:** `tool-camino` declara por qué vía salió (KEYWORD / LLM /
SIN_MATCH) — **no se asegura la redacción de la respuesta**.
`AUDITORÍA: AÑADIDO. Es el análogo directo del ejemplo del laboratorio y el caso
que mejor ejercita la pregunta 3: el texto lo pone el modelo, así que se verifica
el camino y la fuente, nunca la redacción.`

---

## Resumen de la auditoría del plan

| | Propuestos | Aceptados | Corregidos | Descartados | Añadidos |
|---|---:|---:|---:|---:|---:|
| Casos del Planner | 8 | 1 | 6 | 1 | +3 |

El plan aprobado queda en **10 casos**.
