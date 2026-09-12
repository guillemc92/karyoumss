import { describe, expect, it } from 'vitest';
import { buildMockKaryotype, META_CASES } from '../../src/clinic/msw/karyotypeSeed';

const DOWN = '000000aa-0000-0000-0000-000000000102';   // 47,XY,+21
const KLINE = '000000aa-0000-0000-0000-000000000103';  // 47,XXY
const NORMAL = '000000aa-0000-0000-0000-000000000101'; // 46,XX

function slotCount(k: ReturnType<typeof buildMockKaryotype>, cls: string) {
  return k.chromosomes.filter((c) => c.predicted_class === cls).length;
}

describe('karyotypeSeed — metafases MetaClass reconstruidas', () => {
  it('caso genérico (no MetaClass) = 46 cromosomas con 3 naranjas', () => {
    const k = buildMockKaryotype('00000000-0000-0000-0000-000000000442');
    expect(k.chromosomes).toHaveLength(46);
    expect(k.summary.orange).toBe(3);
  });

  it('46,XX normal: 46 cromosomas, dos X, sin naranjas', () => {
    const k = buildMockKaryotype(NORMAL);
    expect(k.chromosomes).toHaveLength(46);
    expect(slotCount(k, 'X')).toBe(2);
    expect(slotCount(k, 'Y')).toBe(0);
    expect(k.summary.orange).toBe(0);
  });

  it('47,XY,+21 (Down): 47 cromosomas, tres copias del 21 (una anómala naranja)', () => {
    const k = buildMockKaryotype(DOWN);
    expect(k.chromosomes).toHaveLength(47);
    expect(slotCount(k, '21')).toBe(3);
    expect(slotCount(k, 'X')).toBe(1);
    expect(slotCount(k, 'Y')).toBe(1);
    const anomalies = k.chromosomes.filter((c) => c.is_anomaly);
    expect(anomalies).toHaveLength(1);
    expect(anomalies[0].predicted_class).toBe('21');
    expect(anomalies[0].semaphore).toBe('orange');
  });

  it('47,XXY (Klinefelter): 47 cromosomas, dos X + una Y, X extra anómala', () => {
    const k = buildMockKaryotype(KLINE);
    expect(k.chromosomes).toHaveLength(47);
    expect(slotCount(k, 'X')).toBe(2);
    expect(slotCount(k, 'Y')).toBe(1);
    const anomalies = k.chromosomes.filter((c) => c.is_anomaly);
    expect(anomalies).toHaveLength(1);
    expect(anomalies[0].predicted_class).toBe('X');
  });

  it('META_CASES declara los 3 ISCN esperados', () => {
    expect(META_CASES[NORMAL].iscn).toBe('46,XX');
    expect(META_CASES[DOWN].iscn).toBe('47,XY,+21');
    expect(META_CASES[KLINE].iscn).toBe('47,XXY');
  });
});
