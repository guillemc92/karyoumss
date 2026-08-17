/**
 * Tests del historial de deshacer/rehacer.
 *
 * Lo que se fija aquí es el comportamiento que un usuario da por supuesto de un
 * Ctrl+Z —y que es fácil romper sin darse cuenta—: que deshacer devuelva al
 * estado de antes de arrastrar un deslizador, que una acción nueva invalide el
 * rehacer, y que el atajo no le robe el Ctrl+Z al navegador dentro de un campo
 * de texto.
 */
import { describe, expect, it } from 'vitest';

import {
  MAX_HISTORIAL,
  accionDeTeclado,
  conHistorial,
  estadoInicial,
  puedeDeshacer,
  puedeRehacer,
} from '../../src/clinic/lib/historial';

interface Estado {
  valor: number;
  modo: boolean;
}

type Accion =
  | { type: 'sumar' }
  | { type: 'poner'; valor: number }
  | { type: 'alternarModo' }
  | { type: 'nada' };

const base: Estado = { valor: 0, modo: false };

const reducer = (s: Estado, a: Accion): Estado => {
  switch (a.type) {
    case 'sumar':
      return { ...s, valor: s.valor + 1 };
    case 'poner':
      return { ...s, valor: a.valor };
    case 'alternarModo':
      return { ...s, modo: !s.modo };
    default:
      return s; // misma referencia: no debe ensuciar el historial
  }
};

const crear = (opciones = {}) => conHistorial<Estado, Accion>(reducer, opciones);

describe('deshacer y rehacer', () => {
  it('deshacer devuelve al estado anterior', () => {
    const r = crear();
    let h = estadoInicial(base);

    h = r(h, { type: 'sumar' });
    h = r(h, { type: 'sumar' });
    expect(h.presente.valor).toBe(2);

    h = r(h, { type: 'deshacer' });

    expect(h.presente.valor).toBe(1);
  });

  it('rehacer vuelve a aplicar lo deshecho', () => {
    const r = crear();
    let h = r(estadoInicial(base), { type: 'sumar' });

    h = r(h, { type: 'deshacer' });
    h = r(h, { type: 'rehacer' });

    expect(h.presente.valor).toBe(1);
  });

  it('una acción nueva invalida el rehacer', () => {
    const r = crear();
    let h = r(r(estadoInicial(base), { type: 'sumar' }), { type: 'sumar' });

    h = r(h, { type: 'deshacer' });
    expect(puedeRehacer(h)).toBe(true);

    h = r(h, { type: 'poner', valor: 99 });

    expect(puedeRehacer(h)).toBe(false);
    expect(h.presente.valor).toBe(99);
  });

  it('deshacer sin historial no rompe ni cambia nada', () => {
    const r = crear();
    const h = estadoInicial(base);

    const resultado = r(h, { type: 'deshacer' });

    expect(resultado).toBe(h);
    expect(puedeDeshacer(h)).toBe(false);
  });
});

describe('fusión de acciones consecutivas', () => {
  it('arrastrar un deslizador deja UN solo punto de retorno', () => {
    // Sin fusión harían falta 4 Ctrl+Z para volver al inicio.
    const r = crear({ fusionar: ['poner'] });
    let h = estadoInicial(base);

    for (const v of [10, 20, 30, 40]) h = r(h, { type: 'poner', valor: v });
    expect(h.presente.valor).toBe(40);

    h = r(h, { type: 'deshacer' });

    expect(h.presente.valor).toBe(0);
  });

  it('la fusión se corta si entre medias hay otra acción', () => {
    const r = crear({ fusionar: ['poner'] });
    let h = estadoInicial(base);

    h = r(h, { type: 'poner', valor: 10 });
    h = r(h, { type: 'sumar' });
    h = r(h, { type: 'poner', valor: 30 });

    h = r(h, { type: 'deshacer' });

    expect(h.presente.valor).toBe(11); // vuelve al estado tras 'sumar'
  });
});

describe('acciones ignoradas', () => {
  it('no crean punto de retorno pero sí cambian el estado', () => {
    const r = crear({ ignorar: ['alternarModo'] });
    let h = r(estadoInicial(base), { type: 'sumar' });

    h = r(h, { type: 'alternarModo' });

    expect(h.presente.modo).toBe(true);
    h = r(h, { type: 'deshacer' });
    expect(h.presente.valor).toBe(0); // deshizo el 'sumar', no el modo
  });
});

describe('higiene del historial', () => {
  it('una acción que no cambia el estado no apila nada', () => {
    const r = crear();
    const h = r(estadoInicial(base), { type: 'nada' });

    expect(puedeDeshacer(h)).toBe(false);
  });

  it('el historial no crece sin límite', () => {
    const r = crear();
    let h = estadoInicial(base);

    for (let i = 0; i < MAX_HISTORIAL + 20; i += 1) h = r(h, { type: 'sumar' });

    expect(h.pasado.length).toBe(MAX_HISTORIAL);
  });
});

describe('atajo de teclado', () => {
  const evento = (over: Record<string, unknown> = {}) => ({
    key: 'z', ctrlKey: true, metaKey: false, shiftKey: false, target: { tagName: 'DIV' }, ...over,
  });

  it('Ctrl+Z deshace', () => {
    expect(accionDeTeclado(evento())).toEqual({ type: 'deshacer' });
  });

  it('Ctrl+Shift+Z rehace', () => {
    expect(accionDeTeclado(evento({ shiftKey: true }))).toEqual({ type: 'rehacer' });
  });

  it('Ctrl+Y rehace (convención Windows)', () => {
    expect(accionDeTeclado(evento({ key: 'y' }))).toEqual({ type: 'rehacer' });
  });

  it('Cmd+Z funciona en Mac', () => {
    expect(accionDeTeclado(evento({ ctrlKey: false, metaKey: true }))).toEqual({ type: 'deshacer' });
  });

  it('la Z sola no hace nada', () => {
    expect(accionDeTeclado(evento({ ctrlKey: false }))).toBeNull();
  });

  it('dentro de un campo de texto NO se roba el Ctrl+Z del navegador', () => {
    expect(accionDeTeclado(evento({ target: { tagName: 'INPUT' } }))).toBeNull();
    expect(accionDeTeclado(evento({ target: { tagName: 'TEXTAREA' } }))).toBeNull();
    expect(accionDeTeclado(evento({ target: { isContentEditable: true } }))).toBeNull();
  });
});
