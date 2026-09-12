import { describe, expect, it } from 'vitest';
import { createKaryotypeClient } from '../../src/clinic/api/karyotypeClient';
import { ClinicApiException } from '../../src/clinic/types/sample';

const client = createKaryotypeClient('/api/clinic');
const READY_SAMPLE = '00000000-0000-0000-0000-000000000442';    // READY → tiene cariotipo
const PROCESSING_SAMPLE = '00000000-0000-0000-0000-000000000441'; // PROCESSING → NO_KARYOTYPE

describe('karyotypeClient', () => {
  it('get() devuelve el cariotipo con 46 cromosomas y summary', async () => {
    const k = await client.get(READY_SAMPLE);
    expect(k.sample_id).toBe(READY_SAMPLE);
    expect(k.chromosomes).toHaveLength(46);
    expect(k.summary.total).toBe(46);
    expect(k.summary.orange).toBe(3);
    expect(k.summary.is_blocked).toBe(true);
  });

  it('get() sin cariotipo lanza ClinicApiException con code NO_KARYOTYPE (404)', async () => {
    await expect(client.get(PROCESSING_SAMPLE)).rejects.toMatchObject({
      status: 404,
      code: 'NO_KARYOTYPE',
    });
  });

  it('get() muestra inexistente lanza 404 NOT_FOUND', async () => {
    await expect(client.get('nonexistent')).rejects.toBeInstanceOf(ClinicApiException);
  });
});
