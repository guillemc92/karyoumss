// Imprime un HTML a PDF con el Chromium de Playwright.
//
//     node scripts/html_a_pdf.js entrada.html salida.pdf
//
// Existe porque la consigna de Evals exige PDF (entregar .md resta 20 puntos)
// y en este equipo no hay LibreOffice: Chromium es el unico motor de
// impresion fiable disponible, y ya esta instalado para los E2E.
//
// La pagina decide su propio formato con etiquetas <meta>, asi el aspecto
// vive junto al documento y no en este guion:
//   pdf-formato   «Letter» o «A4» (por defecto A4)
//   pdf-cabecera  «texto izquierdo|texto derecho»
//   pdf-pie       «texto izquierdo|texto derecho»; si el derecho es «Pág.»,
//                 se le anade el numero de pagina.
const path = require('path');
const { chromium } = require(path.join(__dirname, '..', 'frontend-clinic',
  'node_modules', '@playwright', 'test'));

const ESTILO = 'font-family:Arial,Helvetica,sans-serif;width:100%;margin:0 12.7mm;' +
  'display:flex;justify-content:space-between;';

function banda(texto, color, negrita, conPagina) {
  if (!texto) return '<span></span>';
  const [izq, der = ''] = texto.split('|');
  const derecha = conPagina && der.trim() === 'Pág.'
    ? 'Pág. <span class="pageNumber"></span>' : der;
  return '<div style="' + ESTILO + 'font-size:8px;color:' + color + ';' +
    (negrita ? 'font-weight:700;' : '') + '"><span>' + izq + '</span><span>' +
    derecha + '</span></div>';
}

(async () => {
  const [entrada, salida] = process.argv.slice(2);
  if (!entrada || !salida) {
    console.error('uso: node scripts/html_a_pdf.js entrada.html salida.pdf');
    process.exit(2);
  }
  const navegador = await chromium.launch();
  const pagina = await navegador.newPage();
  await pagina.goto('file://' + path.resolve(entrada).replace(/\\/g, '/'),
    { waitUntil: 'networkidle' });
  const meta = await pagina.evaluate(() => {
    const m = (n) => (document.querySelector('meta[name="' + n + '"]') || {}).content || '';
    return { formato: m('pdf-formato'), cabecera: m('pdf-cabecera'), pie: m('pdf-pie') };
  });
  const conBandas = Boolean(meta.cabecera || meta.pie);
  await pagina.pdf({
    path: salida,
    format: meta.formato || 'A4',
    printBackground: true,
    margin: conBandas
      ? { top: '20mm', bottom: '18mm', left: '12.7mm', right: '12.7mm' }
      : { top: '18mm', bottom: '18mm', left: '16mm', right: '16mm' },
    displayHeaderFooter: true,
    headerTemplate: banda(meta.cabecera, '#1B4F72', true, false),
    footerTemplate: meta.pie
      ? banda(meta.pie, '#566573', false, true)
      : '<div style="font-size:8px;width:100%;text-align:center;color:#667">' +
        '<span class="pageNumber"></span>/<span class="totalPages"></span></div>',
  });
  await navegador.close();
  console.log('escrito ' + salida + ' (' + (meta.formato || 'A4') + ')');
})().catch((e) => { console.error(e); process.exit(1); });
