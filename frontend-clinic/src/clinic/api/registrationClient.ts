/**
 * registrationClient — wrapper HTTP para el flujo de Registro de Muestras (ADR-0016, SPEC-009).
 *
 *   POST /api/clinic/samples/register/   crea Sample + PatientVault + N SampleImage
 *
 * Errores esperados:
 *   400 → CHN_REQUIRED / INVALID_CHN_FORMAT / PATIENT_NAME_REQUIRED / INSUFFICIENT_IMAGES
 *   401 → JWT ausente/inválido
 *   403 → PERMISSION_DENIED
 *   409 → CHN_DUPLICATE
 */
import { getAccessToken } from './authClient';
import { ClinicApiException } from '../types/sample';
import type { RegistrationResponse, SampleRegistrationData } from '../types/registration';

const DEFAULT_BASE_URL = (import.meta.env.VITE_CLINIC_API_BASE as string | undefined) ?? '/api/clinic';

export function createRegistrationClient(baseUrl: string = DEFAULT_BASE_URL) {
  return {
    baseUrl,
    async register(data: SampleRegistrationData): Promise<RegistrationResponse> {
      const headers: Record<string, string> = {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      };
      const token = getAccessToken();
      if (token) headers['Authorization'] = `Bearer ${token}`;

      let res: Response;
      try {
        res = await fetch(`${baseUrl}/samples/register/`, {
          method: 'POST',
          headers,
          body: JSON.stringify(data),
        });
      } catch (err) {
        throw new ClinicApiException(err instanceof Error ? err.message : 'Fallo de red', 0, 'NETWORK_ERROR');
      }

      const text = await res.text();
      let payload: unknown = null;
      if (text) {
        try {
          payload = JSON.parse(text);
        } catch {
          payload = { detail: text };
        }
      }

      if (!res.ok) {
        const detail =
          typeof payload === 'object' && payload !== null && 'detail' in payload
            ? String((payload as { detail: unknown }).detail)
            : `HTTP ${res.status}`;
        const code =
          typeof payload === 'object' && payload !== null && 'code' in payload
            ? String((payload as { code: unknown }).code)
            : undefined;
        throw new ClinicApiException(detail, res.status, code);
      }
      return payload as RegistrationResponse;
    },
  };
}

export type RegistrationClient = ReturnType<typeof createRegistrationClient>;
export const registrationClient: RegistrationClient = createRegistrationClient();
