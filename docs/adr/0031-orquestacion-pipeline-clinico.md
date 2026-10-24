---
id: ADR-0031
title: La orquestación del pipeline clínico es una cola de tareas, no un sistema multiagente
date: 2026-08-17
status: accepted
related: [ADR-0030, ADR-0021, ADR-0007, ADR-0025]
---

# ADR-0031: Orquestación del pipeline clínico

## Contexto

Se propuso una arquitectura de **siete agentes** para el cariotipado: un
«Agente Orquestador Supervisor» coordinando a un Preprocesador, un Detector, un
Clasificador, un agente de Pairing, un Validador ISCN y una capa de narrativa.
La propuesta venía dibujada como flujograma y el DTI §3.5 llegó a contener una
versión anterior de la misma idea (un «Agent Orchestrator» repartiendo trabajo
entre un U-Net Service y un Grad-CAM Engine).

La pregunta que hay que contestar no es si se puede construir —se puede—, sino
si la orquestación agéntica es lo que este flujo necesita. Hay tres hechos que
la responden, y ninguno es una opinión.

### El flujo dibujado no tiene decisiones

Preprocesar → detectar → clasificar tiene un orden **fijo e inevitable**: no se
puede clasificar antes de segmentar. El flujograma propuesto era una línea
recta de siete cajas con una sola bifurcación, y esa bifurcación era un `if`
sobre un umbral. Un orquestador que reparte siempre en el mismo orden y nunca
recupera el control no está orquestando: es una caja de paso.

### Seis de las siete cajas no eran agentes

Un agente es un modelo que decide el orden y cuántos pasos dar. La propia
propuesta describía el Validador ISCN como «función determinística» — que es
exactamente lo contrario de un agente. El Preprocesador, el Detector y el
Clasificador son pasos de un cálculo, no actores con criterio.

### Los servicios que el diagrama repartía no existen

DTI §9.1 ya declara que la segmentación es OpenCV + watershed y que el Grad-CAM
era un mock. El diagrama contradecía a la tabla de diseñado-frente-a-construido
del propio documento.

## Decisión

### D1 — El pipeline de visión se orquesta con una cola de tareas, no con un modelo

`Celery` mueve preprocesado → detección → clasificación → semaforización. Es
trabajo lento, encadenado y sin ramas: lo que una cola resuelve y un agente
encarece. Hoy corre **síncrono dentro de la petición**, que es la deuda que
esta decisión abre (ver Consecuencias).

`Celery` y `LangGraph` no son alternativas entre sí, y presentarlas como tales
delataba que la decisión no estaba tomada: una cola reparte trabajo lento entre
procesos; un grafo de estados sirve a flujos que decide un modelo. Aquí no hay
flujo que decidir.

### D2 — La ramificación real vive después del pipeline, y la resuelve una persona

Donde el caso se bifurca de verdad es en la **semaforización**: los cromosomas
naranjas y rojos desvían el caso a corrección manual, y de ahí a validación,
auditoría del 5% y firma (RN-01/RN-02/RN-06/RN-08). Esa rama no la decide un
modelo — la decide el analista, y es un requisito regulatorio, no una elección
de arquitectura.

Es la inversión que importa: **la baja confianza exige más revisión humana, no
menos**. Ningún camino lleva un resultado por debajo de 0.85 al informe.

### D3 — Hay un solo agente, y no está en este flujo

El agente ReAct + MCP (ADR-0030) es una **capa conversacional** que consulta el
estado por encima del pipeline: responde «¿qué casos están pendientes de
firma?», no ejecuta el cariotipado. No es un paso de la tubería y no aparece en
el flujograma de §3.5.

Se mantiene la regla de la escalera: usar el nivel mínimo que resuelva el
problema. Un agente se justifica con ramificación real y estado; envolver una
secuencia fija en un agente es escalar de nivel sin ganar nada y pagar coste,
latencia y superficie de fallo.

### D4 — «Agente Supervisor» es un nombre prohibido para un componente

En este dominio **Supervisor es un rol clínico con consecuencias legales**:
firma con MFA y está sujeto a segregación de funciones (RN-06). Llamar así a un
componente de software confunde el diagrama y, sobre todo, contamina la lectura
del audit trail, donde el actor de cada evento tiene que ser inequívoco.

### D5 — El ISCN se genera después de la firma

Ya estaba decidido (ADR-0025 D5) y el flujograma propuesto lo invertía. Se
reafirma aquí porque el error es fácil de repetir: `iscn_nomenclature` es de
solo lectura al emitirse (RN-04), así que generarlo sobre un cariotipo que
nadie ha validado congela un dato que todavía podía cambiar.

## Consecuencias

**El diagrama honesto es más útil que el vistoso.** DTI §3.5 dibuja ahora el
flujo real, con la bifurcación donde de verdad está y declarando lo que falta:
el pipeline corre síncrono, la detección es visión clásica con sub-segmentación
medida, y el emparejamiento de homólogos no existe.

**Deuda que esta decisión abre y no oculta:** Celery está declarado en el stack
del proyecto pero **no implementado**. Mientras siga síncrono, una metafase
pesada bloquea el hilo de la petición. Es la primera pieza a construir de esta
decisión, y merece su propio Design Doc cuando se aborde.

**Lo que esta decisión NO dice.** No dice que el multiagente sea malo en
general, ni que LangGraph no vaya a hacer falta nunca. ADR-0030 ya anota que el
estado del agente vive en la lista de mensajes y muere con el proceso; el día
que haga falta memoria persistente entre sesiones, esa es otra decisión y otro
ADR.

**Riesgo asumido:** presentar una arquitectura de siete agentes es más
llamativo que presentar una cola de tareas. Se acepta el coste de vender menos
a cambio de que el diagrama describa el sistema que existe.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Siete agentes, uno por etapa | Seis no son agentes; el flujo no tiene decisiones que tomar. Seis veces el coste y la superficie de fallo para la misma salida |
| Un orquestador agéntico sobre el pipeline | Repartiría siempre en el mismo orden. Un `for` con un modelo delante, cobrando latencia y tokens |
| LangGraph para el pipeline de visión | Grafo de estados para un flujo sin estados que decidir. El docente lo sitúa en memoria persistente, que es otro problema |
| Dejarlo síncrono y no meter cola | No es alternativa, es la deuda actual. Se declara, no se justifica |

## Implementación

DTI §3.5 (flujo extremo a extremo) y §3.2.1 (capa conversacional, ADR-0030).
El agente vive en `backend-clinic/apps/samples/agente.py` + `servidor_mcp.py`;
el pipeline en `backend-ml/app/pipeline.py`, invocado hoy de forma síncrona
desde `apps/samples/services.py` vía `pipeline_client`.
