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
import { textoDeDetalle } from './detalleError';

const DEFAULT_BASE_URL = (import.meta.env.VITE_CLINIC_API_BASE as string | undefined) ?? '/api/clinic';


/**
 * Quita del cuerpo las fechas que van vacías.
 *
 * El formulario inicializa `collection_date` y `reception_date` como cadena
 * vacía, y el serializador del backend rechaza `""` como fecha con un 400
 * («Fecha con formato erróneo. Use uno de los siguientes formatos…»). Pero
 * «Fecha de recepción en laboratorio» **no está marcada como obligatoria** en
 * la pantalla: quien no la rellenaba —que es lo normal— no podía registrar, y
 * hasta hoy solo veía «[object Object]» como explicación.
 *
 * Omitir la clave, en vez de mandarla vacía, es lo que significa «no informada»
 * en este contrato. Lo destapó `registro-por-interfaz.spec.ts` el 23/09/2026;
 * los tests de componente no lo veían porque sus dobles aceptan cualquier
 * cuerpo.
 */
function sinFechasVacias(data: SampleRegistrationData): SampleRegistrationData {
  const muestra = { ...(data.sample as Record<string, unknown>) };
  for (const campo of ['collection_date', 'reception_date']) {
    if (muestra[campo] === '') delete muestra[campo];
  }
  return { ...data, sample: muestra as SampleRegistrationData['sample'] };
}

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
          body: JSON.stringify(sinFechasVacias(data)),
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
            ? textoDeDetalle((payload as { detail: unknown }).detail, `HTTP ${res.status}`)
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
