// Imprime un HTML a PDF con el Chromium de Playwright.
//
//     node scripts/html_a_pdf.js entrada.html salida.pdf
//
// Existe porque la consigna de Evals exige PDF (entregar .md resta 20 puntos)
// y en este equipo no hay LibreOffice: Chromium es el unico motor de
// impresion fiable disponible, y ya esta instalado para los E2E.
const path = require('path');
const { chromium } = require(path.join(__dirname, '..', 'frontend-clinic',
  'node_modules', '@playwright', 'test'));

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
  await pagina.pdf({
    path: salida, format: 'A4', printBackground: true,
    margin: { top: '18mm', bottom: '18mm', left: '16mm', right: '16mm' },
    displayHeaderFooter: true,
    headerTemplate: '<span></span>',
    footerTemplate: '<div style="font-size:8px;width:100%;text-align:center;color:#667">' +
      'M7 Evals · BIOMED UMSS · <span class="pageNumber"></span>/<span class="totalPages"></span></div>',
  });
  await navegador.close();
  console.log('escrito ' + salida);
})().catch((e) => { console.error(e); process.exit(1); });
