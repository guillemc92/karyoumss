/**
 * historial — deshacer/rehacer genérico sobre cualquier reducer puro.
 *
 * ## Qué se puede deshacer y qué NO
 *
 * Esto envuelve **estado de vista y de herramienta**: zoom, rotación, volteo,
 * brillo, contraste, puntos de medición. Todo eso es local, no sale al
 * servidor y no deja rastro clínico, así que deshacerlo es gratis y esperable.
 *
 * **Las acciones clínicas quedan fuera a propósito.** Reclasificar, separar,
 * unir o resolver un cromosoma se persisten al instante y emiten un evento en
 * un audit trail *append-only* (RN-05): no se pueden borrar. Deshacerlas
 * exigiría emitir un evento de compensación —«se revirtió la reclasificación
 * X»— que es una acción clínica nueva, con su autor y su motivo.
 *
 * Un Ctrl+Z silencioso que revierte un acto clínico sería peligroso por dos
 * razones: el analista no vería que ha ocurrido, y el registro contaría una
 * historia distinta de la que el usuario cree. Revertir una decisión clínica
 * tiene que ser deliberado y visible, no un atajo de teclado.
 *
 * ## Fusión de acciones consecutivas
 *
 * Arrastrar el deslizador de brillo emite decenas de acciones. Sin fusionarlas,
 * un Ctrl+Z retrocedería un 1% y harían falta cuarenta pulsaciones para volver
 * al punto de partida. Las acciones del mismo tipo consecutivas se colapsan en
 * una sola entrada: deshacer devuelve al valor de **antes de empezar a
 * arrastrar**, que es lo que el usuario entiende por «deshacer».
 */

export interface ConHistorial<S> {
  pasado: S[];
  presente: S;
  futuro: S[];
  /** Tipo de la última acción registrada, para poder fusionar. */
  ultimoTipo: string | null;
}

export type AccionHistorial = { type: 'deshacer' } | { type: 'rehacer' };

/** Tope de profundidad: más allá, el historial solo consume memoria. */
export const MAX_HISTORIAL = 50;

export function estadoInicial<S>(presente: S): ConHistorial<S> {
  return { pasado: [], presente, futuro: [], ultimoTipo: null };
}

export const puedeDeshacer = <S,>(h: ConHistorial<S>) => h.pasado.length > 0;
export const puedeRehacer = <S,>(h: ConHistorial<S>) => h.futuro.length > 0;

interface Opciones {
  /**
   * Tipos de acción que NO crean punto de retorno. Alternar el modo «Mover» o
   * restablecer la vista no son cosas que uno quiera deshacer por separado.
   */
  ignorar?: string[];
  /** Tipos cuyas repeticiones consecutivas se fusionan (deslizadores). */
  fusionar?: string[];
}

/**
 * Envuelve un reducer para dotarlo de deshacer/rehacer.
 *
 * `deshacer`/`rehacer` no llegan al reducer envuelto: los gestiona esta capa.
 */
export function conHistorial<S, A extends { type: string }>(
  reducer: (estado: S, accion: A) => S,
  opciones: Opciones = {},
) {
  const ignorar = new Set(opciones.ignorar ?? []);
  const fusionar = new Set(opciones.fusionar ?? []);

  return function reducerConHistorial(
    h: ConHistorial<S>,
    accion: A | AccionHistorial,
  ): ConHistorial<S> {
    if (accion.type === 'deshacer') {
      if (!puedeDeshacer(h)) return h;
      const previo = h.pasado[h.pasado.length - 1];
      return {
        pasado: h.pasado.slice(0, -1),
        presente: previo,
        futuro: [h.presente, ...h.futuro],
        ultimoTipo: null, // tras deshacer no se fusiona con lo anterior
      };
    }

    if (accion.type === 'rehacer') {
      if (!puedeRehacer(h)) return h;
      const [siguiente, ...resto] = h.futuro;
      return {
        pasado: [...h.pasado, h.presente],
        presente: siguiente,
        futuro: resto,
        ultimoTipo: null,
      };
    }

    const nuevo = reducer(h.presente, accion as A);
    // Una acción que no cambia nada no ensucia el historial.
    if (Object.is(nuevo, h.presente)) return h;

    if (ignorar.has(accion.type)) {
      return { ...h, presente: nuevo, ultimoTipo: accion.type };
    }

    // Fusión: si se repite el mismo tipo fusionable, se sustituye el presente
    // sin apilar una entrada nueva.
    if (fusionar.has(accion.type) && h.ultimoTipo === accion.type) {
      return { ...h, presente: nuevo, futuro: [] };
    }

    const pasado = [...h.pasado, h.presente];
    return {
      pasado: pasado.length > MAX_HISTORIAL ? pasado.slice(-MAX_HISTORIAL) : pasado,
      presente: nuevo,
      futuro: [], // una acción nueva invalida lo rehacible
      ultimoTipo: accion.type,
    };
  };
}

/**
 * ¿Es este evento de teclado un deshacer/rehacer?
 *
 * Ctrl+Z deshace; Ctrl+Y y Ctrl+Shift+Z rehacen (Windows y Mac difieren, y
 * ambos conviven en el laboratorio). Se ignora si el foco está en un campo de
 * texto: ahí Ctrl+Z es del navegador y quitárselo sería hostil.
 */
export function accionDeTeclado(e: {
  key: string;
  ctrlKey: boolean;
  metaKey: boolean;
  shiftKey: boolean;
  target?: unknown;
}): AccionHistorial | null {
  if (!e.ctrlKey && !e.metaKey) return null;

  const destino = e.target as { tagName?: string; isContentEditable?: boolean } | undefined;
  const etiqueta = destino?.tagName?.toUpperCase();
  if (etiqueta === 'INPUT' || etiqueta === 'TEXTAREA' || destino?.isContentEditable) {
    return null;
  }

  const tecla = e.key.toLowerCase();
  if (tecla === 'z') return e.shiftKey ? { type: 'rehacer' } : { type: 'deshacer' };
  if (tecla === 'y') return { type: 'rehacer' };
  return null;
}
