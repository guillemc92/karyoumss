# M7 · Unit test + agente, sobre el producto real

| | |
|---|---|
| **Equipo** | **BIOMED UMSS** |
| **Integrante** | Ing. Guillermo Mamani Chambi (individual, G04) |
| Módulo | M7 — Pruebas y Validación de Modelos IA |
| Ejercicio | LabX aplicado al producto: una clase de lógica + un endpoint |
| Fecha | 7 de septiembre de 2026 |

El LabX cierra con un encargo concreto:

> *Para el proyecto: elegir en su propio producto **una clase de lógica** (como
> la calculadora) y **un endpoint con tres códigos** (como el servicio), y
> repetir exactamente este ciclo.*

Esto es ese ciclo, con el modelo local del M6 —`llama3.2:3b`, sin red— sobre dos
piezas reales del cariotipado.

---

## 1 · Qué se eligió, y por qué

**La clase de lógica → el motor ISCN** (`apps/samples/iscn.py`).

Es el equivalente exacto de `Calculadora`: función pura, sin ORM, sin I/O, mismo
input → mismo output. Y con una regla de negocio que **no puede reventar**, igual
que `dividir(a, 0)`:

> `generate_iscn({})` lanza `IscnError`. **No** devuelve `'46,XX'` por defecto.

La razón no es de estilo. `47,XY,+21` es un diagnóstico de síndrome de Down.
Devolver un cariotipo normal cuando no hay cromosomas sería inventar un
diagnóstico — y es la razón por la que ADR-0024 D1 prohíbe que este dato lo
produzca el LLM.

**El endpoint con tres códigos → `GET /api/clinic/samples/{id}/karyotype/`.**

| Quién pide | Código | Por qué |
|---|---|---|
| el analista dueño, o un supervisor | **200** | tiene el cariotipo |
| un analista que no es dueño del caso | **403** | segregación de funciones (RN-06) |
| una muestra que aún no se ha procesado | **404** | registrada, sin cariotipo |

Y un cuarto que no puede faltar: **401** sin token.

---

## 2 · El ciclo, medido

```
                      generados   corrieron   sobrevivieron   coste (tokens/tiempo)
ejercicio 1 · ISCN         8          2*             1        2.050 + 359 · 587 s
ejercicio 2 · endpoint     6          0              4        3.264 + 519 · 1.012 s
                          --         --             --
                          14          2              5        5.314 + 878 · 26 min 39 s
```

\* los dos que corrieron en verde eran **copias literales** del fichero a mano.

**Ninguno de los 14 se ejecutó tal cual salió del modelo.** El único arreglo que
se hizo antes de auditar fue mecánico —los imports— y está declarado en la
cabecera de cada fichero. Ningún assert se tocó antes de la auditoría.

Reproducible:

```bash
cd backend-clinic
.venv/Scripts/python ../docs/M7_UNIT_AGENTE/agente_generador.py iscn
.venv/Scripts/python ../docs/M7_UNIT_AGENTE/agente_generador.py endpoint
.venv/Scripts/python -m pytest apps/samples/tests/test_iscn_agente.py -q --no-cov
```

---

## 3 · El primer tropiezo es el que el LabX anticipa

```
apps\samples\tests\test_iscn_agente.py:1: in <module>
    pytestmark = pytest.mark.agente
E   NameError: name 'pytest' is not defined
```

Las dos veces. El generador del laboratorio corrige ese import y avisa; **el de
este proyecto no lo corrige a propósito**, porque el olvido es justamente lo que
la auditoría tiene que encontrar. Es la primera evidencia de que se lee antes de
correr.

En el ejercicio 2 fue peor y más silencioso: el modelo copió del fichero a mano
una fixture llamada `caso` **dando por hecho que se hereda**. No se hereda —vive
en otro módulo de test, no en el `conftest`—. Cinco de sus seis tests murieron
por eso, y el código se lee perfecto.

---

## 4 · La auditoría, test por test

Las tres preguntas del LabX §3:

1. Si rompo la función, ¿este test se pone rojo?
2. ¿El assert dice lo que el código **debe** hacer, o copió lo que hace hoy?
3. ¿El nombre dice algo?

### Ejercicio 1 · el motor ISCN

| # | Test del agente | Estado | Veredicto |
|---|---|---|---|
| 1 | `test_cariotipo_femenino_normal` | verde | **Borrado** — copia literal de `TestCariotiposNormales.test_femenino` |
| 2 | `test_cariotipo_masculino_normal` | verde | **Borrado** — copia literal de `test_masculino` |
| 3 | `test_trisomia_21` | rojo | **Borrado** — `{'21': 3}` son tres cromosomas, no un cariotipo; y el caso ya está a mano (`test_down_trisomia_21`) |
| 4 | `test_monosomia_X` | rojo | **Borrado** — espera `'45,XX,-X'`, que se contradice a sí mismo; el estándar es `45,X` y ya está a mano |
| 5 | `test_klinefelter` | rojo | **Borrado** — `{'21': 1}` no es Klinefelter. Falla la pregunta 3: **el nombre miente**. Es el mismo assert que el #3 con otro dato |
| 6 | `test_conteo_vacio` | rojo | **Borrado** — espera `''`. Falla la pregunta 2 del peor modo posible: **la regla de negocio, invertida** |
| 7 | `test_cariotipo_femenino_trisomia_13` | rojo | **Borrado** — dos errores: el conteo y el total (48 con una sola trisomía es imposible). Ya está a mano (`test_patau_trisomia_13`) |
| 8 | `test_cariotipo_masculino_trisomia_8` | rojo | **Corregido y aceptado** → `auditado` |

**El #6 es el hallazgo pedagógico.** Es el análogo exacto del error que el LabX
predice en la calculadora —probar `dividir(1, 0)` esperando `ZeroDivisionError`,
la foto de lo que haría Python en vez de lo que hace la clase—. Aquí el modelo
esperó que un conteo vacío devolviera cadena vacía. Si ese test se hubiera
aceptado y alguien hubiera «arreglado» el motor para que pasara, el sistema
emitiría una nomenclatura vacía en lugar de negarse a emitir.

### Ejercicio 2 · el endpoint

| # | Test del agente | Estado | Veredicto |
|---|---|---|---|
| 1 | `test_admin_ve_cualquier_caso` | error | **Borrado** — usa `supervisor_client`, no admin: el nombre miente. Y duplica `test_el_supervisor_ve_cualquier_caso` |
| 2 | `test_muestra_desactivada_devuelve_404` | rojo | **Corregido y aceptado** — ver abajo |
| 3 | `test_cromosomas_estan_ordenados_por_order` | error | **Corregido y aceptado** |
| 4 | `test_sample_iscn_es_cadena_vacia_mientras_no_seha_generado` | error | **Corregido y aceptado** — solo el nombre |
| 5 | `test_model_version_viaja_en_la_respuesta` | error | **Corregido y aceptado** |
| 6 | `test_admin_ve_caso_desactivado` | error | **Borrado** — usa una variable que no recibe, y **contradice al #2**: uno dice 404 y el otro 200 para el mismo caso |

Tres de estos merecen el detalle:

**El #2 habría pasado en verde sin probar nada.** El agente creó una muestra
desactivada **sin cariotipo** y esperó 404. El 404 habría salido igual aunque el
endpoint ignorara por completo `is_active`, porque la muestra no tenía cariotipo.
Corregido: el caso sí tiene cariotipo, y entonces el 404 solo puede venir del
borrado lógico. Es la pregunta 1 en su forma más difícil de ver — el test no era
rojo, era **vacío**.

**El #5 desobedeció una regla explícita del prompt.** Se le pidió «assert exacto
sobre el JSON» y escribió `assert model_version is not None`. Ese assert pasa con
la cadena vacía — que es exactamente el fallo que importa: un cariotipo sin
declarar qué modelo lo produjo no es trazable (ADR-0021).

**El #3 afirmaba el fixture, no el orden.** `chromosomes[0]['order'] == 0`,
`[1] == 1`, `[2] == 2` funciona solo mientras haya exactamente tres cromosomas.
Corregido a comparar la lista contra su propia versión ordenada.

---

## 5 · Lo que falló del prompt, y es culpa mía

En el ejercicio 1 le pedí al agente «casos que **NO** estén ya en el archivo a
mano» y a continuación le listé seis casos que **sí estaban todos**. El modelo
obedeció la lista e ignoró la restricción — y siete de sus ocho tests fueron
redundantes por diseño del encargo, no por incapacidad del modelo.

Peor: `test_iscn.py` ya cubría 37 casos, incluidos XXX, XYY, XXXY, Klinefelter,
doble trisomía, monosomía, ganancia+pérdida y tetrasomía. **No quedaba casi nada
real que pedirle.** Pedirle tests a un agente sobre una unidad ya saturada
produce duplicados o disparates; no hay una tercera opción.

Para el ejercicio 2 corregí el método: **verifiqué que los cinco casos estuvieran
ausentes antes de pedirlos**. La tasa de supervivencia pasó de 1/8 a 4/6. El
modelo era el mismo; lo que cambió fue el encargo.

Es el mismo patrón que ya apareció dos veces este módulo —en la detección de
duplicados y en el contrato de errores—: **la primera medición dice más sobre las
suposiciones de quien mide que sobre el sistema medido.**

---

## 6 · Lo que se aprendió

El agente escribió 14 tests en 27 minutos de modelo local. **Cero corrieron tal
cual.** Dos quedaron en verde y los dos eran copias del fichero a mano — el verde
no dijo nada hasta que alguien hizo las tres preguntas. Cinco sobrevivieron.

Lo que el agente aportó, cuando aportó algo, fue **la idea del caso**: «trisomía
8 sobre XY», «una muestra desactivada», «que `model_version` viaje». La entrada
correcta, el valor esperado y el nombre los puso la persona en los cinco.

Eso es la regla del módulo, y aquí está medida en un producto clínico y no en una
calculadora:

> **El agente escribe; la persona decide.**
> *Ninguna prueba generada por IA se acepta sin auditoría humana.*

Y una lección que el laboratorio de juguete no puede enseñar: sobre una unidad ya
bien probada, un agente generador **no aporta cobertura, aporta duplicados**. Su
sitio está donde hay hueco de verdad — y saber dónde hay hueco es trabajo de la
persona, con el informe de cobertura delante.

---

## 7 · Qué queda en el repositorio

| Ruta | Qué es |
|---|---|
| `docs/M7_UNIT_AGENTE/agente_generador.py` | el agente, misma anatomía que el del LabX; **no corrige** lo que devuelve el modelo |
| `docs/M7_UNIT_AGENTE/PROMPT_AGENTE_iscn.md` | el encargo del ejercicio 1 (con su defecto, sin maquillar) |
| `docs/M7_UNIT_AGENTE/PROMPT_AGENTE_endpoint.md` | el encargo del ejercicio 2, ya con los casos verificados ausentes |
| `docs/M7_UNIT_AGENTE/salida_agente/*_crudo.py` | lo que devolvió el modelo, **intacto**: la evidencia de la auditoría |
| `backend-clinic/apps/samples/tests/test_iscn_agente.py` | 1 test `@pytest.mark.auditado` |
| `backend-clinic/apps/samples/tests/test_karyotype_endpoint_agente.py` | 4 tests `@pytest.mark.auditado` |

Las marcas están registradas en `backend-clinic/pytest.ini`, así que se pueden
correr por separado:

```bash
pytest -m auditado -q --no-cov      # 5 passed
pytest -m agente -q --no-cov        # 0: no queda ninguno sin auditar
```
