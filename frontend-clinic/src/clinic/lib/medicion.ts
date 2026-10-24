/**
 * medicion — cálculo puro de las medidas con las que se clasifica un cromosoma.
 *
 * No es una regla de dibujo: es la aritmética que la citogenética usa desde la
 * Conferencia de Denver (1960) para decidir a qué grupo pertenece un cromosoma.
 * Un analista que discute la clase que propuso el modelo mide esto.
 *
 * ## Las tres medidas
 *
 *   longitud total   p + q, en píxeles de la metafase
 *   índice centromérico   p / (p + q) · 100 — dónde está el centrómero
 *   razón de brazos   q / p — la forma en que la literatura clásica lo expresa
 *
 * ## Por qué el índice centromérico y no solo la longitud
 *
 * La longitud depende del grado de condensación, que varía entre metafases y
 * entre preparaciones: dos imágenes del mismo cromosoma pueden diferir un 30%.
 * El índice centromérico es una **proporción**, así que no le afecta. Por eso
 * es el criterio que separa metacéntrico de submetacéntrico y de acrocéntrico,
 * y no la longitud absoluta.
 *
 * Todo aquí es geometría pura y sin unidades clínicas: las medidas se dan en
 * píxeles porque no hay calibración de micras. Sirven para **comparar** dentro
 * de la misma metafase, no para informar un valor absoluto.
 */

/** Un punto del lienzo, en coordenadas de la imagen (no de pantalla). */
export interface Punto {
  x: number;
  y: number;
}

export type Morfologia =
  | 'metacéntrico'
  | 'submetacéntrico'
  | 'acrocéntrico'
  | 'telocéntrico';

export interface Medida {
  /** Longitud del brazo corto (p), en píxeles. */
  brazoP: number;
  /** Longitud del brazo largo (q), en píxeles. */
  brazoQ: number;
  /** p + q. */
  longitudTotal: number;
  /** p / (p+q) · 100. Rango [0, 50]: por definición p es el brazo corto. */
  indiceCentromerico: number;
  /** q / p. Infinito si p es 0 (telocéntrico puro). */
  razonBrazos: number;
  morfologia: Morfologia;
}

export function distancia(a: Punto, b: Punto): number {
  return Math.hypot(b.x - a.x, b.y - a.y);
}

/**
 * Clasificación morfológica por índice centromérico (Levan et al., 1964).
 *
 * Los cortes son los clásicos de la literatura citogenética. Se dejan como
 * constantes con nombre para que se vea de dónde salen y se puedan revisar:
 * son convención, no una ley física.
 */
export const CORTE_METACENTRICO = 37.5; // 37.5–50 → brazos casi iguales
export const CORTE_SUBMETACENTRICO = 25; // 25–37.5
export const CORTE_ACROCENTRICO = 12.5; // 12.5–25; por debajo, telocéntrico

export function morfologiaPorIndice(indice: number): Morfologia {
  if (indice >= CORTE_METACENTRICO) return 'metacéntrico';
  if (indice >= CORTE_SUBMETACENTRICO) return 'submetacéntrico';
  if (indice >= CORTE_ACROCENTRICO) return 'acrocéntrico';
  return 'telocéntrico';
}

/**
 * Mide un cromosoma a partir de tres puntos marcados por el analista:
 * extremo del brazo corto, centrómero y extremo del brazo largo.
 *
 * Si el usuario marca los extremos al revés (el "corto" más largo que el
 * "largo"), se intercambian: p es el brazo corto **por definición**, y dejar
 * que el índice pase de 50 daría una morfología imposible.
 */
export function medirCromosoma(
  extremoP: Punto,
  centromero: Punto,
  extremoQ: Punto,
): Medida {
  let brazoP = distancia(extremoP, centromero);
  let brazoQ = distancia(centromero, extremoQ);

  if (brazoP > brazoQ) [brazoP, brazoQ] = [brazoQ, brazoP];

  const longitudTotal = brazoP + brazoQ;
  const indiceCentromerico = longitudTotal > 0 ? (brazoP / longitudTotal) * 100 : 0;
  const razonBrazos = brazoP > 0 ? brazoQ / brazoP : Infinity;

  return {
    brazoP: redondea(brazoP),
    brazoQ: redondea(brazoQ),
    longitudTotal: redondea(longitudTotal),
    indiceCentromerico: redondea(indiceCentromerico),
    razonBrazos: Number.isFinite(razonBrazos) ? redondea(razonBrazos) : Infinity,
    morfologia: morfologiaPorIndice(indiceCentromerico),
  };
}

/**
 * Longitud relativa: qué porcentaje de la longitud total del genoma medido
 * ocupa este cromosoma. Es la forma en que las tablas de referencia expresan
 * el tamaño, precisamente para neutralizar la condensación.
 */
export function longitudRelativa(longitud: number, totalMetafase: number): number {
  if (totalMetafase <= 0) return 0;
  return redondea((longitud / totalMetafase) * 100);
}

/** Texto corto para el panel, en el orden en que se lee un informe. */
export function resumenMedida(m: Medida): string {
  const razon = Number.isFinite(m.razonBrazos) ? `${m.razonBrazos.toFixed(2)}` : '∞';
  return `L ${m.longitudTotal} px · IC ${m.indiceCentromerico}% · q/p ${razon} · ${m.morfologia}`;
}

const redondea = (v: number) => Math.round(v * 100) / 100;
