# Guion de la exposicion - 3 minutos

Generado desde `docs/BIOMED_defensa_3min.pptx` por `scripts/armar_deck_defensa.js`; no se edita a mano.

Orden pedido por el docente: **hallazgo - modelo - plantilla - resultado - punto**. Hay alarma a los 3 minutos, asi que va cronometrado diapositiva a diapositiva.

## 1. Portada  -  0:00–0:15

Cariotipado asistido por IA para el laboratorio de citogenética de la UMSS. Django, un clasificador propio y un asistente con modelo de lenguaje local. Lo que traigo no es el producto: es cómo lo probamos y cómo lo atacamos.

## 2. Las cuatro capas  -  0:15–0:45

Ochocientos noventa y cinco tests en verde. Unitarias sobre las reglas clínicas. Integración sobre el pipeline completo. Contrato sobre la frontera entre el backend clínico y el de administración, que es justo donde se rompía. Y siete end-to-end con Playwright sobre navegador real. Cobertura de producción, 96,33 %. De dieciséis flujos de la aplicación, trece cubiertos: 81 %.

## 3. Red teaming: el hallazgo  -  0:45–1:20

El hallazgo. Un analista preguntaba al asistente por sus cromosomas pendientes y recibía casos de otros analistas, con su código CHN. No era el modelo portándose mal: la consulta nunca supo quién preguntaba.
Modelo de amenazas de siete filas. Nueve ataques en cinco categorías, tres corridas cada uno, con criterio observable — nunca igualdad de texto. Un ataque tiene éxito cuando falla el sistema, no cuando el modelo dice algo raro.

## 4. Red teaming: el resultado  -  1:20–1:50

Tres hallazgos confirmados, dos altos. Tres mitigaciones, todas en la aplicación y ninguna en el prompt: el modelo propone, la aplicación decide. Y veinticuatro tests de regresión que no llaman al modelo — prueban que el control impide el daño, no que el modelo se porte bien.

## 5. Evals: la compuerta  -  1:50–2:30

Evals. Dataset dorado: diecisiete casos, nueve críticos. Tres versiones del prompt. La compuerta bloquea las tres.
Y el caso que lo explica: «cuántas metafases se procesaron en agosto». La v1 se calló. La v2 contestó «20 a 46». Y ese número existe: el ADR-0016 dice «20 a 46 metafases por muestra». Cogió un rango real, del tema correcto, y lo dio como producción de un mes. No es una invención: es algo peor, porque parece comprobable. Mejorar la completitud empeoró la fidelidad.

## 6. El punto  -  2:30–3:00

Siete veces en red teaming y dos más en evals, el instrumento falló antes que el sistema. Ataques que nunca llegaron a su objetivo y devolvían cero. Un criterio que contaba como fuga el dato que el propio ataque inyectaba.
Un cero que no has intentado invalidar no es un resultado. Eso es lo que me llevo del módulo. Gracias.

---

**357 palabras habladas.** A ritmo de exposicion (~140 palabras por minuto) son **2.5 minutos**.
