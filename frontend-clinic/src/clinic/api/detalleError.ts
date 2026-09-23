/**
 * Convierte el `detail` de un error de la API en texto que una persona pueda leer.
 *
 * ## El fallo que esto corrige
 *
 * Los clientes hacían `String(payload.detail)`. Cuando el backend responde con
 * un `VALIDATION_ERROR`, `detail` no es una cadena sino el diccionario de
 * errores por campo de DRF:
 *
 *     {"code": "VALIDATION_ERROR",
 *      "detail": {"sample": {"collection_date": ["Fecha con formato erróneo…"]}}}
 *
 * y `String()` sobre un objeto devuelve `"[object Object]"`. El analista veía
 * eso, literalmente, en vez del motivo. El dato estaba en la respuesta; se
 * perdía al formatearlo.
 *
 * Lo encontró el E2E de registro por interfaz (`registro-por-interfaz.spec.ts`)
 * el 23/09/2026: los tests de componente no lo cazaron porque sus dobles
 * devuelven `detail` como cadena, que es la forma que el mock suponía. El
 * backend real usa las dos.
 *
 * ## Qué devuelve
 *
 * Aplana el árbol a «campo: mensaje», separando por punto y coma, y recorta si
 * se hace inmanejable: un aviso de diez líneas tampoco se lee.
 */

/** Más allá de esto el aviso deja de ser un aviso y pasa a ser un volcado. */
const LARGO_MAXIMO = 240;

function aplanar(valor: unknown, prefijo = ''): string[] {
  if (valor === null || valor === undefined) return [];
  if (typeof valor === 'string') return [prefijo ? `${prefijo}: ${valor}` : valor];
  if (Array.isArray(valor)) return valor.flatMap((v) => aplanar(v, prefijo));
  if (typeof valor === 'object') {
    return Object.entries(valor as Record<string, unknown>).flatMap(([clave, v]) =>
      // El nombre del campo hoja basta; encadenar «sample.collection_date» no
      // ayuda a quien rellena el formulario.
      aplanar(v, clave),
    );
  }
  return [prefijo ? `${prefijo}: ${String(valor)}` : String(valor)];
}

export function textoDeDetalle(detalle: unknown, porDefecto: string): string {
  const partes = aplanar(detalle);
  if (partes.length === 0) return porDefecto;
  const texto = partes.join('; ');
  return texto.length > LARGO_MAXIMO ? `${texto.slice(0, LARGO_MAXIMO - 1)}…` : texto;
}
