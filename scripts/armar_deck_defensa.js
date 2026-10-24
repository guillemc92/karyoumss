// Guion de 3 minutos — BIOMED UMSS, M7/M8/M9.
// Paleta tomada del propio producto: el semaforo clinico (verde = pre-validado,
// naranja = hay que mirarlo). El naranja es el acento porque toda la charla va
// de lo que hay que volver a mirar.
const pptxgen = require('pptxgenjs');

const OSCURO = '0E2A33';
const CLARO = 'FFFFFF';
const TINTA = '15323C';
const TENUE = '6E8892';
const NARANJA = 'E8833A';
const VERDE = '4C9A6A';
const HIELO = 'EAF1F3';

const SERIF = 'Cambria';
const SANS = 'Calibri';

const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9';          // 10" x 5.625"
pres.author = 'Ing. Guillermo Mamani Chambi';
pres.title = 'BIOMED UMSS — Probar y atacar la capa de IA';

const M = 0.6;                         // margen lateral
const ANCHO = 10 - M * 2;

function titulo(slide, texto, opts = {}) {
  slide.addText(texto, {
    x: M, y: opts.y || 0.42, w: ANCHO, h: 0.7,
    fontFace: SERIF, fontSize: opts.size || 30, bold: true,
    color: opts.color || TINTA, align: 'left', margin: 0, isTextBox: true,
  });
}

function bolita(slide, x, y, n, color) {
  slide.addShape(pres.ShapeType.ellipse, {
    x: x, y: y, w: 0.34, h: 0.34, fill: { color: color },
  });
  slide.addText(String(n), {
    x: x, y: y, w: 0.34, h: 0.34, fontFace: SANS, fontSize: 13, bold: true,
    color: CLARO, align: 'center', valign: 'middle', margin: 0, isTextBox: true,
  });
}

// --------------------------------------------------------------- 1. portada
const s1 = pres.addSlide();
s1.background = { color: OSCURO };
s1.addText('BIOMED UMSS', {
  x: M, y: 1.5, w: ANCHO, h: 0.45, fontFace: SANS, fontSize: 15,
  color: NARANJA, charSpacing: 3, bold: true, margin: 0, isTextBox: true,
});
s1.addText('Probar y atacar\nla capa de IA', {
  x: M, y: 1.95, w: ANCHO, h: 1.6, fontFace: SERIF, fontSize: 40, bold: true,
  color: CLARO, lineSpacing: 44, margin: 0, isTextBox: true,
});
s1.addText('Cariotipado asistido por IA · Módulos 7, 8 y 9', {
  x: M, y: 3.62, w: ANCHO, h: 0.35, fontFace: SANS, fontSize: 14,
  color: '9FB6BE', margin: 0, isTextBox: true,
});
s1.addText('Ing. Guillermo Mamani Chambi · G04', {
  x: M, y: 4.62, w: ANCHO, h: 0.35, fontFace: SANS, fontSize: 12,
  color: TENUE, margin: 0, isTextBox: true,
});
s1.addNotes(
  '[0:00–0:15]\n' +
  'Cariotipado asistido por IA para el laboratorio de citogenética de la UMSS. ' +
  'Django, un clasificador propio y un asistente con modelo de lenguaje local. ' +
  'Lo que traigo no es el producto: es cómo lo probamos y cómo lo atacamos.');

// ------------------------------------------------------- 2. piramide de tests
const s2 = pres.addSlide();
s2.background = { color: CLARO };
titulo(s2, 'Las cuatro capas, y dónde se rompía');

const CAPAS = [
  ['Unitarias', 'Las reglas clínicas RN-01 a RN-09, una por una'],
  ['Integración', 'El pipeline muestra → cariotipo → informe, extremo a extremo'],
  ['Contrato', 'La frontera backend clínico ↔ backend admin: aquí aparecían los fallos'],
  ['End-to-end', 'Playwright sobre navegador real: registro, visor, bandejas, modo degradado'],
];
CAPAS.forEach((c, i) => {
  const y = 1.42 + i * 0.68;
  bolita(s2, M, y, i + 1, i === 2 ? NARANJA : OSCURO);
  s2.addText(c[0], {
    x: M + 0.52, y: y - 0.04, w: 1.7, h: 0.3, fontFace: SANS, fontSize: 14,
    bold: true, color: TINTA, margin: 0, isTextBox: true,
  });
  s2.addText(c[1], {
    x: M + 2.25, y: y - 0.02, w: 3.45, h: 0.45, fontFace: SANS, fontSize: 11.5,
    color: TENUE, margin: 0, isTextBox: true,
  });
});

s2.addShape(pres.ShapeType.roundRect, {
  x: 6.5, y: 1.35, w: 2.9, h: 2.9, rectRadius: 0.08, fill: { color: HIELO },
});
s2.addText('895', {
  x: 6.75, y: 1.58, w: 2.4, h: 0.85, fontFace: SERIF, fontSize: 54, bold: true,
  color: OSCURO, margin: 0, isTextBox: true,
});
s2.addText('tests en verde', {
  x: 6.78, y: 2.42, w: 2.4, h: 0.3, fontFace: SANS, fontSize: 12,
  color: TENUE, margin: 0, isTextBox: true,
});
s2.addText('97,56 %', {
  x: 6.75, y: 2.95, w: 2.4, h: 0.45, fontFace: SERIF, fontSize: 26, bold: true,
  color: VERDE, margin: 0, isTextBox: true,
});
s2.addText('cobertura de producción\n13 de 16 flujos cubiertos (81 %)', {
  x: 6.78, y: 3.42, w: 2.45, h: 0.6, fontFace: SANS, fontSize: 11,
  color: TENUE, margin: 0, isTextBox: true,
});
s2.addNotes(
  '[0:15–0:45]\n' +
  'Ochocientos noventa y cinco tests en verde. Unitarias sobre las reglas ' +
  'clínicas. Integración sobre el pipeline completo. Contrato sobre la ' +
  'frontera entre el backend clínico y el de administración, que es justo ' +
  'donde se rompía. Y end-to-end con Playwright sobre navegador real. ' +
  'Cobertura de producción, 97,56 %. De dieciséis flujos de la aplicación, ' +
  'trece cubiertos: 81 %.');

// ------------------------------------------------- 3. red team: hallazgo
const s3 = pres.addSlide();
s3.background = { color: CLARO };
s3.addText('RED TEAMING', {
  x: M, y: 0.42, w: ANCHO, h: 0.28, fontFace: SANS, fontSize: 11.5, bold: true,
  color: NARANJA, charSpacing: 2.5, margin: 0, isTextBox: true,
});
titulo(s3, 'El hallazgo', { y: 0.72, size: 30 });

s3.addShape(pres.ShapeType.roundRect, {
  x: M, y: 1.62, w: 5.0, h: 1.75, rectRadius: 0.08, fill: { color: HIELO },
});
s3.addText(
  'Un analista pregunta al asistente por sus cromosomas pendientes ' +
  'y recibe casos de OTROS analistas, con su código CHN.', {
    x: M + 0.28, y: 1.85, w: 4.45, h: 1.3, fontFace: SERIF, fontSize: 16,
    color: TINTA, italic: true, lineSpacing: 22, margin: 0, isTextBox: true,
  });
s3.addText(
  'No era el modelo portándose mal:\nla consulta nunca supo quién preguntaba.', {
    x: M, y: 3.62, w: 5.0, h: 0.7, fontFace: SANS, fontSize: 13, bold: true,
    color: OSCURO, lineSpacing: 19, margin: 0, isTextBox: true,
  });

const FICHA = [
  ['Modelo de amenazas', '7 filas: activos, actores, entradas,\nfronteras, ataques, impacto, mitigación'],
  ['Plantilla de ataque', '9 ataques · 5 categorías · 3 corridas\ncriterio observable, nunca igualdad de texto'],
];
FICHA.forEach((f, i) => {
  const y = 1.72 + i * 1.35;
  s3.addText(f[0], {
    x: 6.15, y: y, w: 3.3, h: 0.3, fontFace: SANS, fontSize: 13, bold: true,
    color: NARANJA, margin: 0, isTextBox: true,
  });
  s3.addText(f[1], {
    x: 6.15, y: y + 0.33, w: 3.3, h: 0.8, fontFace: SANS, fontSize: 11.5,
    color: TENUE, lineSpacing: 16, margin: 0, isTextBox: true,
  });
});
s3.addNotes(
  '[0:45–1:20]\n' +
  'El hallazgo. Un analista preguntaba al asistente por sus cromosomas ' +
  'pendientes y recibía casos de otros analistas, con su código CHN. ' +
  'No era el modelo portándose mal: la consulta nunca supo quién preguntaba.\n' +
  'Modelo de amenazas de siete filas. Nueve ataques en cinco categorías, ' +
  'tres corridas cada uno, con criterio observable — nunca igualdad de texto. ' +
  'Un ataque tiene éxito cuando falla el sistema, no cuando el modelo dice ' +
  'algo raro.');

// ------------------------------------------------- 4. red team: resultado
const s4 = pres.addSlide();
s4.background = { color: CLARO };
titulo(s4, 'El resultado: la aplicación decide');

const CIFRAS = [
  ['3', 'hallazgos confirmados\ndos de severidad alta', NARANJA],
  ['3', 'mitigaciones, todas en la\naplicación — ninguna en el prompt', OSCURO],
  ['24', 'tests de regresión\nninguno llama al modelo', VERDE],
];
CIFRAS.forEach((c, i) => {
  const x = M + i * 3.05;
  s4.addShape(pres.ShapeType.roundRect, {
    x: x, y: 1.4, w: 2.7, h: 1.9, rectRadius: 0.08, fill: { color: HIELO },
  });
  s4.addText(c[0], {
    x: x + 0.25, y: 1.6, w: 2.2, h: 0.8, fontFace: SERIF, fontSize: 46,
    bold: true, color: c[2], margin: 0, isTextBox: true,
  });
  s4.addText(c[1], {
    x: x + 0.27, y: 2.45, w: 2.3, h: 0.7, fontFace: SANS, fontSize: 11.5,
    color: TENUE, lineSpacing: 15, margin: 0, isTextBox: true,
  });
});
s4.addText('El modelo PROPONE, la aplicación DECIDE.', {
  x: M, y: 3.62, w: ANCHO, h: 0.4, fontFace: SERIF, fontSize: 20, bold: true,
  color: TINTA, margin: 0, isTextBox: true,
});
s4.addText(
  'Prueban que el control impide el daño, no que el modelo se porte bien.', {
    x: M, y: 4.05, w: ANCHO, h: 0.35, fontFace: SANS, fontSize: 12.5,
    color: TENUE, margin: 0, isTextBox: true,
  });
// Evidencia del retest, contada en docs/M9_RED_TEAM/evidencia: cinco ataques
// pasaban 3/3 en la linea base (AI-SEC-001, 002, 005, 006, 007) y los cinco
// quedaron en 0/3 tras las mitigaciones.
s4.addText('Retest: el atacante pasó de 15 de 15 éxitos a 0 de 15.', {
  x: M, y: 4.55, w: ANCHO, h: 0.4, fontFace: SANS, fontSize: 14, bold: true,
  color: VERDE, margin: 0, isTextBox: true,
});
s4.addNotes(
  '[1:20–1:50]\n' +
  'Tres hallazgos confirmados, dos altos. Tres mitigaciones, todas en la ' +
  'aplicación y ninguna en el prompt: el modelo propone, la aplicación decide. ' +
  'Veinticuatro tests de regresión que no llaman al modelo. Y el retest: el ' +
  'atacante pasó de quince éxitos de quince a cero.');

// ------------------------------------------------------------- 5. evals
const s5 = pres.addSlide();
s5.background = { color: CLARO };
s5.addText('EVALS IA OFFLINE', {
  x: M, y: 0.42, w: ANCHO, h: 0.28, fontFace: SANS, fontSize: 11.5, bold: true,
  color: NARANJA, charSpacing: 2.5, margin: 0, isTextBox: true,
});
// Cifras de la entrega oficial del 29/09 (docs/M7_Evals_BIOMED/): 12 casos,
// 5 criticos, v3 PASA con codigo 0. La version del 28/09 de esta lamina
// («la compuerta bloquea las tres») era de un intento superado.
titulo(s5, 'La v3 pasa la compuerta, al quinto intento', { y: 0.72, size: 28 });

const enc = (t) => ({
  text: t, options: { bold: true, color: CLARO, fill: { color: OSCURO },
                      fontSize: 11.5, align: 'center' },
});
const cel = (t, color, negrita) => ({
  text: t, options: { color: color || TINTA, fontSize: 11.5, align: 'center', bold: !!negrita },
});
s5.addTable([
  [enc(''), enc('v1'), enc('v2 prod.'), enc('v3')],
  [cel('completitud'), cel('0,375'), cel('0,583'), cel('0,917')],
  [cel('fidelidad'), cel('1,000'), cel('0,917'), cel('1,000')],
  [cel('casos críticos'), cel('3 / 5'), cel('3 / 5'), cel('5 / 5')],
  [cel('compuerta'), cel('NO PASA', NARANJA, true), cel('NO PASA', NARANJA, true),
   cel('PASA', VERDE, true)],
], {
  x: M, y: 1.45, w: 5.2, colW: [1.6, 1.2, 1.2, 1.2], rowH: 0.35,
  border: { type: 'solid', color: 'DDE6E9', pt: 1 }, fontFace: SANS,
  valign: 'middle',
});

s5.addText('12 casos · 5 críticos · juez calibrado: κ = 0,437', {
  x: M, y: 3.42, w: 5.2, h: 0.3, fontFace: SANS, fontSize: 11.5, color: TENUE,
  margin: 0, isTextBox: true,
});
// Coste medido en respuestas/v3.jsonl: 9 llamadas (las 3 abstenciones no
// llaman), 3.982 tokens, 0 en dinero porque el modelo es local.
s5.addText('Coste de una corrida: 9 llamadas · ~4.000 tokens · 0 en dinero', {
  x: M, y: 3.74, w: 5.2, h: 0.3, fontFace: SANS, fontSize: 11.5, color: TENUE,
  margin: 0, isTextBox: true,
});

s5.addShape(pres.ShapeType.roundRect, {
  x: 6.15, y: 1.45, w: 3.25, h: 2.72, rectRadius: 0.08, fill: { color: HIELO },
});
s5.addText('BORRADOR 1 DE LA V3', {
  x: 6.4, y: 1.62, w: 2.8, h: 0.28, fontFace: SANS, fontSize: 11, bold: true,
  color: NARANJA, charSpacing: 1.5, margin: 0, isTextBox: true,
});
s5.addText('«Sí, puedes firmar el caso que analices»', {
  x: 6.4, y: 1.92, w: 2.8, h: 0.55, fontFace: SERIF, fontSize: 13, italic: true,
  color: TINTA, lineSpacing: 17, margin: 0, isTextBox: true,
});
s5.addText('Cada regla que añadía al prompt arreglaba un caso y rompía otro.', {
  x: 6.4, y: 2.55, w: 2.8, h: 0.5, fontFace: SANS, fontSize: 10.5,
  color: TENUE, lineSpacing: 14, margin: 0, isTextBox: true,
});
s5.addText('La corrección: la aplicación decide cuándo callar; el modelo solo elige oraciones.', {
  x: 6.4, y: 3.15, w: 2.8, h: 0.8, fontFace: SANS, fontSize: 10.5, bold: true,
  color: TINTA, lineSpacing: 14, margin: 0, isTextBox: true,
});
s5.addText('El modelo propone, la aplicación decide — también en evals.', {
  x: M, y: 4.32, w: ANCHO, h: 0.35, fontFace: SANS, fontSize: 13, bold: true,
  color: OSCURO, margin: 0, isTextBox: true,
});
s5.addNotes(
  '[1:50–2:30]\n' +
  'Evals. Doce casos de los cinco tipos, cinco críticos. La v1 y la v2 solo ' +
  'cambian el prompt, y las dos se callaban ante «¿puedo emitir el informe?» ' +
  'y «¿puedo firmar yo?». La v3 salió al quinto intento: cada regla que añadía ' +
  'al prompt arreglaba un caso y rompía otro, y el primer borrador le dijo al ' +
  'analista «sí, puedes firmar tu propio caso». Lo que funcionó fue sacar esa ' +
  'decisión del modelo: la aplicación decide cuándo no responder y el modelo ' +
  'solo elige qué oraciones responden. Cinco de cinco críticos, compuerta en ' +
  'cero, y cada corrida cuesta unos cuatro mil tokens: cero en dinero.');

// ------------------------------------------------------------- 6. el punto
const s6 = pres.addSlide();
s6.background = { color: OSCURO };
s6.addText('EL PUNTO', {
  x: M, y: 0.85, w: ANCHO, h: 0.3, fontFace: SANS, fontSize: 11.5, bold: true,
  color: NARANJA, charSpacing: 2.5, margin: 0, isTextBox: true,
});
s6.addText('El instrumento falla\nantes que el sistema.', {
  x: M, y: 1.28, w: ANCHO, h: 1.3, fontFace: SERIF, fontSize: 34, bold: true,
  color: CLARO, lineSpacing: 40, margin: 0, isTextBox: true,
});
s6.addText(
  'Siete veces en red teaming. Cuatro más en evals. Ataques que nunca llegaron ' +
  'a su objetivo y devolvían cero. Una frase prohibida que marcaba como falsa ' +
  'la respuesta correcta: «no se puede firmar».', {
    x: M, y: 2.78, w: 6.6, h: 1.0, fontFace: SANS, fontSize: 13.5,
    color: '9FB6BE', lineSpacing: 20, margin: 0, isTextBox: true,
  });
s6.addText('Un cero que no has intentado invalidar no es un resultado.', {
  x: M, y: 4.0, w: ANCHO, h: 0.5, fontFace: SERIF, fontSize: 19, bold: true,
  color: NARANJA, margin: 0, isTextBox: true,
});
s6.addNotes(
  '[2:30–3:00]\n' +
  'Siete veces en red teaming y cuatro más en evals, el instrumento falló ' +
  'antes que el sistema. Ataques que nunca llegaron a su objetivo y devolvían ' +
  'cero. Una frase prohibida que marcaba como falsa la respuesta correcta, ' +
  '«no se puede firmar», porque no sabía de negaciones.\n' +
  'Un cero que no has intentado invalidar no es un resultado. Eso es lo que ' +
  'me llevo del módulo. Gracias.');

const salida = process.argv[2] || 'BIOMED_defensa_3min.pptx';
pres.writeFile({ fileName: salida }).then(() => console.log('escrito ' + salida));
