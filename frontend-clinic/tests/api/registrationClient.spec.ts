import { describe, expect, it, vi, beforeEach } from 'vitest';
import { createRegistrationClient } from '../../src/clinic/api/registrationClient';
import { ClinicApiException } from '../../src/clinic/types/sample';
import type { SampleRegistrationData } from '../../src/clinic/types/registration';

const client = createRegistrationClient('/api/clinic');

const VALID_PAYLOAD: SampleRegistrationData = {
  patient: { full_name: 'ANON-CLIENT', birth_date: '', document_id: '', phone: '' },
  sample: { chn_code: 'CHN-2026-07-12-0201', sample_type: '', culture_method: '', collection_date: '', reception_date: '', requesting_doctor: '', department: '', gender: '' },
  clinical_history: { indication: '', family_history: '' },
  analysis_requests: [],
  images: [
    { data_base64: 'data:image/jpeg;base64,aGVsbG8=', source: 'upload' },
    { data_base64: 'data:image/jpeg;base64,aGVsbG8=', source: 'upload' },
    { data_base64: 'data:image/jpeg;base64,aGVsbG8=', source: 'upload' },
  ],
  is_draft: false,
};

beforeEach(() => {
  localStorage.setItem('biomed.clinic.access', 'mock-token');
});

describe('registrationClient', () => {
  it('register() exitoso retorna la respuesta parseada', async () => {
    const result = await client.register(VALID_PAYLOAD);
    expect(result.status).toBe('PENDING_AI');
  });

  it('register() con fallo de red lanza ClinicApiException NETWORK_ERROR', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('connection refused'));
    await expect(client.register(VALID_PAYLOAD)).rejects.toMatchObject({ code: 'NETWORK_ERROR' });
    spy.mockRestore();
  });

  it('register() con respuesta no-JSON usa el texto como detail', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response('Internal Server Error', { status: 500 }),
    );
    try {
      await client.register(VALID_PAYLOAD);
      throw new Error('should have thrown');
    } catch (err) {
      expect(err).toBeInstanceOf(ClinicApiException);
      expect((err as ClinicApiException).message).toBe('Internal Server Error');
      expect((err as ClinicApiException).code).toBeUndefined();
    }
    spy.mockRestore();
  });

  it('register() con error JSON sin code deja code undefined', async () => {
    const spy = vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'algo falló' }), { status: 400 }),
    );
    await expect(client.register(VALID_PAYLOAD)).rejects.toMatchObject({ message: 'algo falló', code: undefined });
    spy.mockRestore();
  });

  it('register() con CHN duplicado propaga status y code', async () => {
    await client.register(VALID_PAYLOAD);
    await expect(client.register({ ...VALID_PAYLOAD, patient: { ...VALID_PAYLOAD.patient, full_name: 'OTRO' } }))
      .rejects.toMatchObject({ status: 409, code: 'CHN_DUPLICATE' });
  });
});
