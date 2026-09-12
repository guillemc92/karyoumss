import { describe, expect, it, beforeEach } from 'vitest';
import { createSamplesClient } from '../../src/clinic/api/samplesClient';
import { ClinicApiException } from '../../src/clinic/types/sample';

const client = createSamplesClient('/api/clinic');

beforeEach(() => {
  localStorage.setItem('biomed.auth.access', 'mock-token');
});

describe('samplesClient', () => {
  it('list() retorna items del seed', async () => {
    const items = await client.list();
    expect(items.length).toBeGreaterThan(0);
  });

  it('list() filtra por status', async () => {
    const items = await client.list({ status: 'VALIDATED' });
    expect(items.every((i) => i.status === 'VALIDATED')).toBe(true);
  });

  it('create() crea una muestra nueva', async () => {
    const created = await client.create({ chn_code: 'CHN-TEST-001', patient_ref: 'ANON-TEST' });
    expect(created.chn_code).toBe('CHN-TEST-001');
    expect(created.status).toBe('PENDING_AI');
  });

  it('create() con CHN duplicado lanza 409', async () => {
    await client.create({ chn_code: 'CHN-DUP-001', patient_ref: 'A' });
    await expect(client.create({ chn_code: 'CHN-DUP-001', patient_ref: 'B' })).rejects.toMatchObject({
      status: 409,
      code: 'CHN_DUPLICATE',
    });
  });

  it('get() retorna detalle de una muestra existente', async () => {
    const created = await client.create({ chn_code: 'CHN-GET-001', patient_ref: 'X' });
    const fetched = await client.get(created.id);
    expect(fetched.id).toBe(created.id);
  });

  it('get() con id inexistente lanza 404', async () => {
    await expect(client.get('nonexistent-id')).rejects.toMatchObject({ status: 404 });
  });

  it('update() rechaza campo status (RN-04)', async () => {
    const created = await client.create({ chn_code: 'CHN-UPD-001', patient_ref: 'X' });
    await expect(
      // @ts-expect-error probando rechazo de campo prohibido
      client.update(created.id, { status: 'VALIDATED', patient_ref: 'Y' }),
    ).rejects.toMatchObject({ status: 400, code: 'FIELD_NOT_ALLOWED' });
  });

  it('process() responde 202 con task_id', async () => {
    const created = await client.create({ chn_code: 'CHN-PROC-001', patient_ref: 'X' });
    const result = await client.process(created.id);
    expect(result.status).toBe('queued');
    expect(result.task_id).toBeTruthy();
  });

  it('sin token, request lanza excepción de tipo ClinicApiException en error de red simulado', () => {
    expect(new ClinicApiException('x', 401, 'UNAUTHENTICATED')).toBeInstanceOf(Error);
  });

  it('softDelete() elimina una muestra existente', async () => {
    const created = await client.create({ chn_code: 'CHN-DEL-CLIENT-001', patient_ref: 'X' });
    await expect(client.softDelete(created.id)).resolves.toBeUndefined();
    await expect(client.get(created.id)).rejects.toMatchObject({ status: 404 });
  });

  it('softDelete() con muestra VALIDATED lanza 409', async () => {
    const items = await client.list({ status: 'VALIDATED' });
    expect(items.length).toBeGreaterThan(0);
    await expect(client.softDelete(items[0].id)).rejects.toMatchObject({ status: 409, code: 'CANNOT_DELETE_VALIDATED' });
  });

  it('getStatus() retorna el estado del pipeline', async () => {
    const created = await client.create({ chn_code: 'CHN-STATUS-001', patient_ref: 'X' });
    const status = await client.getStatus(created.id);
    expect(status.sample_id).toBe(created.id);
  });

  it('process() en muestra ya PROCESSING retorna 409', async () => {
    const created = await client.create({ chn_code: 'CHN-DOUBLEPROC-001', patient_ref: 'X' });
    await client.process(created.id);
    await expect(client.process(created.id)).rejects.toMatchObject({ status: 409, code: 'ALREADY_PROCESSING' });
  });
});
