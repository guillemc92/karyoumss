"""Contrato (JSON Schema) del endpoint principal — `GET /samples/{id}/karyotype/`.

## Por que este endpoint y no otro

Es el que devuelve el producto: el cariotipo propuesto con su semaforizacion.
De el dependen el visor Konva, el panel del supervisor y la decision de si el
caso puede emitir informe. Si cambia su forma sin avisar, se rompe la pantalla
donde trabaja el analista.

## Que fija el contrato y que NO

Fija **la forma**: campos obligatorios, tipos, catalogos cerrados y rangos.

No fija el **contenido**: que un cromosoma sea de la clase 7 o de la 12 lo
decide el modelo, y no es materia de contrato. Confundir las dos cosas produce
pruebas que fallan cada vez que el clasificador mejora.

## Los catalogos son cerrados a proposito

`semaphore`, `resolution_status` y `predicted_class` son enumeraciones. Un valor
fuera del catalogo no es un dato raro: es un fallo. El visor pinta el color a
partir de `semaphore`, y RN-02 bloquea la emision segun `is_blocked` — si
llegara un valor inesperado, la pantalla no sabria que hacer con el.
"""

#: 1..22 + sexuales. Es el catalogo del dominio, no una lista de conveniencia.
CLASES_CROMOSOMA = [str(n) for n in range(1, 23)] + ['X', 'Y']

#: RN-02. `red` es "sin confianza", no "confianza baja" — son casos distintos.
SEMAFOROS = ['green', 'orange', 'red']

RESOLUCIONES = ['AUTO', 'PENDING', 'RESOLVED']

ESTADOS_MUESTRA = [
    'DRAFT', 'PENDING_AI', 'PROCESSING', 'READY',
    'ANALYST_VALIDATED', 'VALIDATED', 'SIGNED', 'REPORTED', 'REJECTED',
]

CROMOSOMA_SCHEMA = {
    'type': 'object',
    'required': ['id', 'predicted_class', 'position_index', 'confidence_score',
                 'semaphore', 'resolution_status', 'xai_viewed', 'is_anomaly',
                 'is_active', 'order'],
    'properties': {
        'id': {'type': 'string', 'format': 'uuid'},
        'predicted_class': {'type': 'string', 'enum': CLASES_CROMOSOMA},
        'position_index': {'type': 'integer', 'minimum': 0},
        # Llega como cadena: DecimalField de DRF serializa asi para no perder
        # precision en JSON. El visor la parsea; el contrato fija el formato.
        'confidence_score': {'type': ['string', 'number', 'null'],
                             'pattern': r'^\d\.\d{1,3}$'},
        'semaphore': {'type': 'string', 'enum': SEMAFOROS},
        'resolution_status': {'type': 'string', 'enum': RESOLUCIONES},
        'xai_viewed': {'type': 'boolean'},
        'is_anomaly': {'type': 'boolean'},
        'is_active': {'type': 'boolean'},
        'measures': {'type': ['object', 'null']},
        'bbox': {'type': ['object', 'null']},
        'order': {'type': 'integer', 'minimum': 0},
    },
}

SUMMARY_SCHEMA = {
    'type': 'object',
    'required': ['total', 'green', 'orange', 'red', 'unresolved_orange', 'is_blocked'],
    'properties': {
        'total': {'type': 'integer', 'minimum': 0},
        'green': {'type': 'integer', 'minimum': 0},
        'orange': {'type': 'integer', 'minimum': 0},
        'red': {'type': 'integer', 'minimum': 0},
        'unresolved_orange': {'type': 'integer', 'minimum': 0},
        # RN-01/RN-02: es lo que decide si el caso puede avanzar. Booleano
        # estricto, nunca una cadena "true".
        'is_blocked': {'type': 'boolean'},
    },
    'additionalProperties': False,
}

KARYOTYPE_SCHEMA = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema',
    'title': 'GET /api/clinic/samples/{id}/karyotype/',
    'type': 'object',
    'required': ['id', 'sample_id', 'sample_status', 'model_version',
                 'generated_at', 'summary', 'chromosomes'],
    'properties': {
        'id': {'type': 'string', 'format': 'uuid'},
        'sample_id': {'type': 'string', 'format': 'uuid'},
        'sample_status': {'type': 'string', 'enum': ESTADOS_MUESTRA},
        # RN-04: read-only. Cadena vacia mientras no se ha generado.
        'sample_iscn': {'type': 'string'},
        # Declara que produjo el resultado (ADR-0021). Puede venir vacia si el
        # cariotipo se sembro a mano, pero el campo tiene que estar.
        'model_version': {'type': 'string'},
        'generated_at': {'type': ['string', 'null']},
        'summary': SUMMARY_SCHEMA,
        'chromosomes': {'type': 'array', 'items': CROMOSOMA_SCHEMA},
    },
}

#: Codigos que el endpoint puede devolver, y solo estos.
CODIGOS_HTTP = {
    200: 'el dueno del caso, o supervisor/admin',
    401: 'sin JWT',
    403: 'analista que no es dueno del caso (RN-06)',
    404: 'la muestra no existe, o no tiene cariotipo todavia',
}
