# Guion de la exposicion - 3 minutos

Generado desde `docs/BIOMED_defensa_3min.pptx` por `scripts/armar_deck_defensa.js`; no se edita a mano.

Orden pedido por el docente: **hallazgo - modelo - plantilla - resultado - punto**. Hay alarma a los 3 minutos, asi que va cronometrado lamina a lamina.

## 1. Portada  -  0:00–0:15  (39 palabras)

Cariotipado asistido por IA para el laboratorio de citogenética de la UMSS. Django, un clasificador propio y un asistente con modelo de lenguaje local. Lo que traigo no es el producto: es cómo lo probamos y cómo lo atacamos.

## 2. Las cuatro capas  -  0:15–0:45  (57 palabras)

Ochocientos noventa y cinco tests en verde. Unitarias sobre las reglas clínicas. Integración sobre el pipeline completo. Contrato sobre la frontera entre el backend clínico y el de administración, que es justo donde se rompía. Y end-to-end con Playwright sobre navegador real. Cobertura de producción, 97,56 %. De dieciséis flujos de la aplicación, trece cubiertos: 81 %.

## 3. Red teaming: el hallazgo  -  0:45–1:20  (71 palabras)

El hallazgo. Un analista preguntaba al asistente por sus cromosomas pendientes y recibía casos de otros analistas, con su código CHN. No era el modelo portándose mal: la consulta nunca supo quién preguntaba.
Modelo de amenazas de siete filas. Nueve ataques en cinco categorías, tres corridas cada uno, con criterio observable — nunca igualdad de texto. Un ataque tiene éxito cuando falla el sistema, no cuando el modelo dice algo raro.

## 4. Red teaming: el resultado  -  1:20–1:50  (44 palabras)

Tres hallazgos confirmados, dos altos. Tres mitigaciones, todas en la aplicación y ninguna en el prompt: el modelo propone, la aplicación decide. Veinticuatro tests de regresión que no llaman al modelo. Y el retest: el atacante pasó de quince éxitos de quince a cero.

## 5. Evals: la v3 pasa la compuerta  -  1:50–2:30  (105 palabras)

Evals. Doce casos de los cinco tipos, cinco críticos. La v1 y la v2 solo cambian el prompt, y las dos se callaban ante «¿puedo emitir el informe?» y «¿puedo firmar yo?». La v3 salió al quinto intento: cada regla que añadía al prompt arreglaba un caso y rompía otro, y el primer borrador le dijo al analista «sí, puedes firmar tu propio caso». Lo que funcionó fue sacar esa decisión del modelo: la aplicación decide cuándo no responder y el modelo solo elige qué oraciones responden. Cinco de cinco críticos, compuerta en cero, y cada corrida cuesta unos cuatro mil tokens: cero en dinero.

## 6. El punto  -  2:30–3:00  (66 palabras)

Siete veces en red teaming y cuatro más en evals, el instrumento falló antes que el sistema. Ataques que nunca llegaron a su objetivo y devolvían cero. Una frase prohibida que marcaba como falsa la respuesta correcta, «no se puede firmar», porque no sabía de negaciones.
Un cero que no has intentado invalidar no es un resultado. Eso es lo que me llevo del módulo. Gracias.

---

**382 palabras habladas.** A ~140 palabras por minuto son **2.7 minutos**.
