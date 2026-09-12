# Prompt para el agente — Ejercicio 2 · el endpoint del cariotipo

Es el «servicio con tres códigos» del producto, el equivalente de
`GET /pedidos/{numero}` del LabX. La ruta es
`GET /api/clinic/samples/{id}/karyotype/` y devuelve el producto del sistema:
el cariotipo propuesto con su semaforización.

| Quién pide | Código | Por qué |
|---|---|---|
| el analista dueño del caso, o un supervisor | **200** | tiene el cariotipo |
| un analista que no es dueño del caso | **403** | segregación de funciones (RN-06) |
| una muestra que aún no tiene cariotipo | **404** | está registrada, no procesada |

Los tres códigos **son la regla de negocio**, igual que en el LabX. Y hay un
cuarto que no puede faltar: **401** sin token.

Los cinco casos de la lista se comprobaron **ausentes** del fichero a mano antes
de pedirlos. Es la diferencia con el prompt del ejercicio 1, que pidio casos que
ya estaban cubiertos — ver la seccion «lo que fallo del prompt» del informe.

Al agente se le entregan **solo dos archivos**: `apps/samples/contratos.py` (el
JSON Schema del endpoint, con `CODIGOS_HTTP`) y
`apps/samples/tests/test_contrato_karyotype.py`. Se pega tal cual:

```
Lee contratos.py y test_contrato_karyotype.py. Crea el archivo
test_karyotype_endpoint_agente.py con tests del endpoint
GET /api/clinic/samples/{id}/karyotype/ para casos que NO esten en el
archivo a mano: que el admin vea cualquier caso, que una muestra
desactivada (is_active=False) devuelva 404, que los cromosomas vengan
ordenados por el campo order, que sample_iscn sea cadena vacia mientras
no se ha generado, y que model_version viaje en la respuesta.
Maximo 6 tests.
Reglas:
- Usa las fixtures analyst_client, supervisor_client, api_client y
  analyst_user del conftest, como el archivo a mano. Sin red, sin servidor.
- assert exacto sobre status_code y sobre el JSON.
- Nombre de cada test = una frase con el comportamiento esperado.
- Primera linea despues de los imports: pytestmark = pytest.mark.agente
- No modifiques contratos.py.
- Corre una sola vez: pytest test_karyotype_endpoint_agente.py -q  y pega la salida.
```

Después, la auditoría con las tres preguntas (README, sección 3 del LabX).
