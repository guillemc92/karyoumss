# -*- coding: utf-8 -*-
"""Guarda de abstencion: decide en CODIGO cuando no se responde.

## Por que existe (lo que se midio)

v1, v2 y los dos borradores de v3 le pedian al MODELO que decidiera cuando
callarse, con una lista de categorias en el prompt. Medido sobre el dataset
dorado:

- v2 se abstenia bien en los tres casos de abstencion, pero tambien en cinco
  preguntas que el contexto SI responde (completitud 0,583).
- el borrador 1 de v3 dejo de abstenerse de mas (completitud 0,958), y a cambio
  respondio «Si, puedes firmar» al analista que queria firmar su propio caso.
- el borrador 2 de v3, con nueve reglas, rompio lo que ya funcionaba: devolvio
  `full_name` a una peticion de datos de paciente y el «20-46» a una pregunta
  de produccion.

Cada regla anadida al prompt arreglaba un caso y rompia otro. Con un modelo de
3.000 millones de parametros, cuando callarse no puede depender de que el
modelo lea bien una lista. Es la misma leccion del red teaming (M9): **el
modelo propone, la aplicacion decide**.

## Que decide y que no

Solo tres categorias, las mismas que el prompt de produccion ya enumeraba:

1. datos de una persona concreta o de un paciente,
2. cifras de produccion del laboratorio en un periodo,
3. precios, presupuestos o compras.

Si la pregunta cae en una, no se llama al modelo: la respuesta es una
abstencion con el motivo registrado. Todo lo demas pasa al modelo.

Las reglas son de CATEGORIA, no de caso: ninguna nombra al doctor Rojas, al
CHN del dataset ni a agosto. Cualquier pregunta con esa forma cae igual.

**Limite declarado:** es un filtro lexico. Una peticion de datos personales
formulada sin ninguna de estas palabras pasa al modelo, que sigue teniendo en
su prompt la instruccion de abstenerse. La guarda es una capa, no la unica.
"""
import re
import unicodedata

DATO_PERSONAL = r'\b(nombres?|apellidos?|carnet|cedula|ci|telefonos?|celular|direccion|domicilio|correo|email|edad|fecha de nacimiento)\b'
QUIEN = r'\b(paciente|pacientes|doctor|doctora|dr|dra|persona|senor|senora|chn-\d)'

CUANTOS = r'\bcuant[oa]s\b'
ALGO_PRODUCIDO = r'\b(casos|muestras|metafases|informes|cariotipos|pacientes|estudios)\b'
PERIODO = (r'\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|'
           r'octubre|noviembre|diciembre|mes|meses|semana|semanas|ano|anos|periodo|trimestre|'
           r'hoy|ayer)\b|\b20\d\d\b')

DINERO = r'\b(precio|precios|cuesta|cuestan|costo|coste|presupuesto|licencia|compras?|factura)\b'


def _plano(texto):
    t = unicodedata.normalize('NFD', (texto or '').lower())
    return ''.join(c for c in t if unicodedata.category(c) != 'Mn')


def motivo_abstencion(pregunta):
    """Devuelve el motivo si la pregunta NO debe llegar al modelo, o None."""
    p = _plano(pregunta)
    if re.search(DATO_PERSONAL, p) and re.search(QUIEN, p):
        return 'datos de una persona o paciente (RN-03)'
    if re.search(CUANTOS, p) and re.search(ALGO_PRODUCIDO, p) and re.search(PERIODO, p):
        return 'cifras de produccion: la documentacion describe reglas, no produccion'
    if re.search(DINERO, p):
        return 'precios o compras: fuera del alcance de la documentacion'
    return None
