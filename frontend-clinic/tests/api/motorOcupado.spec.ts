// DD-OBS-001 D8: el cliente entrega al visor el código ML_BUSY y los segundos
// de espera, que es con lo que el visor decide qué aviso mostrar.
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';
import { createSamplesClient } from '../../src/clinic/api/samplesClient';
import { setBusyMode, setDegradedMode } from '../../src/clinic/msw/handlers';
import { server } from '../../src/clinic/msw/server';
import { ClinicApiException } from '../../src/clinic/types/sample';

const client = createSamplesClient('/api/clinic');
const ID = '00000000-0000-0000-0000-000000000442';

async function fallo(): Promise<ClinicApiException> {
  try {
    await client.process(ID);
  } catch (err) {
    return err as ClinicApiException;
  }
  throw new Error('process() tenía que fallar');
}

function responder(cuerpo: unknown) {
  server.use(http.post('/api/clinic/samples/:id/process/', () => HttpResponse.json(cuerpo as object, { status: 503 })));
}

beforeEach(() => {
  localStorage.setItem('biomed.auth.access', 'mock-token');
});

describe('process() con el motor ocupado', () => {
  it('lanza ML_BUSY con los segundos que manda el backend', async () => {
    setBusyMode(25);
    const err = await fallo();
    expect(err).toBeInstanceOf(ClinicApiException);
    expect(err.status).toBe(503);
    expect(err.code).toBe('ML_BUSY');
    expect(err.retryAfterSeconds).toBe(25);
    expect(err.message).toContain('otro caso');
  });

  it('ML_DEGRADED sigue llegando como ML_DEGRADED', async () => {
    setDegradedMode(true);
    const err = await fallo();
    expect(err.code).toBe('ML_DEGRADED');
    expect(err.retryAfterSeconds).toBe(60);
    setDegradedMode(false);
  });

  it.each([
    ['falta', { code: 'ML_BUSY', detail: 'x' }],
    ['es texto', { code: 'ML_BUSY', detail: 'x', retry_after_seconds: '25' }],
    ['es cero', { code: 'ML_BUSY', detail: 'x', retry_after_seconds: 0 }],
    ['es negativo', { code: 'ML_BUSY', detail: 'x', retry_after_seconds: -3 }],
  ])('si retry_after_seconds %s, no se inventa un número', async (_caso, cuerpo) => {
    responder(cuerpo);
    const err = await fallo();
    expect(err.code).toBe('ML_BUSY');
    expect(err.retryAfterSeconds).toBeUndefined();
  });

  it('un cuerpo que no es un objeto no rompe el cliente', async () => {
    server.use(http.post('/api/clinic/samples/:id/process/', () => new HttpResponse('503 del proxy', { status: 503 })));
    const err = await fallo();
    expect(err.status).toBe(503);
    expect(err.retryAfterSeconds).toBeUndefined();
  });
});
