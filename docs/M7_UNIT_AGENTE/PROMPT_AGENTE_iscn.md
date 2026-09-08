# Prompt para el agente — Ejercicio 1 · el motor ISCN

Es la «clase de lógica» del producto, el equivalente de `Calculadora` del LabX:
función pura, sin ORM, sin red, mismo input → mismo output. Y con **una regla de
negocio que no puede reventar**, igual que `dividir(a, 0)`:

> `generate_iscn({})` lanza `IscnError`. **No** devuelve `'46,XX'` por defecto.
> Devolver un cariotipo normal cuando no hay cromosomas sería inventar un
> diagnóstico.

Al agente se le entregan **solo dos archivos**: `apps/samples/iscn.py` y
`apps/samples/tests/test_iscn.py`. Se pega tal cual:

```
Lee iscn.py y test_iscn.py. Crea el archivo test_iscn_agente.py con tests
unitarios de generate_iscn(counts) para casos que NO esten ya en el archivo
a mano: cariotipo femenino normal, cariotipo masculino normal, trisomia 21,
monosomia X, Klinefelter (XXY), y el conteo vacio.
Maximo 8 tests.
Reglas:
- assert exacto (==) sobre el string ISCN devuelto, no "is not None".
- Nombre de cada test = una frase con el comportamiento esperado.
- Primera linea despues de los imports: pytestmark = pytest.mark.agente
- No uses la base de datos ni Django: generate_iscn es una funcion pura.
- No modifiques iscn.py.
- Corre una sola vez: pytest test_iscn_agente.py -q  y pega la salida.
```

Después, la auditoría con las tres preguntas (README, sección 3 del LabX).
