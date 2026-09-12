import { describe, expect, it } from 'vitest';
import {
  PAD,
  SLOT_H,
  SLOT_W,
  chromosomePosition,
  reclassifyTargetFromDrop,
  slotAtPoint,
  slotOrigin,
} from '../../src/clinic/lib/karyoLayout';

describe('karyoLayout — geometría pura del cariograma (DD-KARYO-003)', () => {
  it('slotOrigin ubica el slot 1 en la esquina y avanza por columnas', () => {
    expect(slotOrigin('1')).toEqual({ x: PAD, y: PAD });
    expect(slotOrigin('2')).toEqual({ x: PAD + SLOT_W, y: PAD });
  });

  it('slotOrigin baja a la segunda fila en el slot 13 (índice 12)', () => {
    expect(slotOrigin('13')).toEqual({ x: PAD, y: PAD + SLOT_H });
  });

  it('slotOrigin devuelve null para un slot inexistente', () => {
    expect(slotOrigin('99')).toBeNull();
  });

  it('chromosomePosition desplaza por position_index (copia)', () => {
    const p0 = chromosomePosition({ predicted_class: '1', position_index: 0 });
    const p1 = chromosomePosition({ predicted_class: '1', position_index: 1 });
    expect(p1.x).toBeGreaterThan(p0.x);
    expect(p1.y).toBe(p0.y);
  });

  it('chromosomePosition cae en el pad si la clase es inválida', () => {
    expect(chromosomePosition({ predicted_class: 'ZZ', position_index: 0 })).toEqual({ x: PAD, y: PAD });
  });

  it('slotAtPoint invierte slotOrigin (centro del slot 1 → "1")', () => {
    expect(slotAtPoint(PAD + 10, PAD + 10)).toBe('1');
    expect(slotAtPoint(PAD + SLOT_W + 10, PAD + 10)).toBe('2');
    expect(slotAtPoint(PAD + 10, PAD + SLOT_H + 10)).toBe('13');
  });

  it('slotAtPoint devuelve null fuera de la grilla', () => {
    expect(slotAtPoint(-50, -50)).toBeNull();
    expect(slotAtPoint(5000, 5000)).toBeNull();
  });

  it('reclassifyTargetFromDrop retorna la clase destino cuando cambia de slot', () => {
    // soltar sobre el slot 2 un cromosoma cuya clase es 1 → "2".
    expect(reclassifyTargetFromDrop(PAD + SLOT_W + 10, PAD + 10, { predicted_class: '1' })).toBe('2');
  });

  it('reclassifyTargetFromDrop retorna null si cae en el mismo slot', () => {
    expect(reclassifyTargetFromDrop(PAD + 10, PAD + 10, { predicted_class: '1' })).toBeNull();
  });

  it('reclassifyTargetFromDrop retorna null si cae fuera de la grilla', () => {
    expect(reclassifyTargetFromDrop(-100, -100, { predicted_class: '1' })).toBeNull();
  });
});
