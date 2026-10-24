/**
 * ProfileSection — vista de la sección "Perfil de Usuario" del bounded
 * context config (DD-ADMIN-002 P1).
 *
 * Estructura:
 *  - ConfigSection envuelve la carga (loading/error/data).
 *  - Una tarjeta de cabecera muestra nombre, email, especialidad (read-only).
 *  - ConfigForm permite editar los campos del AdminProfileSerializer.
 *
 * Estado: por ahora self-fetch en el render. P3 introducirá
 * adminConfigStore (DD §11.3) y esto pasará a ser un consumidor.
 */
import { useCallback, useState } from 'react';
import { ConfigSection } from './ConfigSection';
import { ConfigForm, ConfigFieldDef } from './ConfigForm';
import { AdminApiException } from '../types/adminUser';
import { adminConfigClient } from '../api/adminConfigClient';
import { AdminProfile, AdminProfileInput, profileSchema } from '../types/config';
const FIELDS: ConfigFieldDef<AdminProfile>[] = [
  { name: 'full_name', label: 'Nombre completo', required: true, maxLength: 80 },
  { name: 'email', label: 'Email institucional', type: 'email', required: true },
  {
    name: 'specialty',
    label: 'Especialidad',
    maxLength: 80,
    hint: 'Ej.: Citogenética Clínica, Genética Médica',
  },
  {
    name: 'professional_license',
    label: 'Matrícula profesional',
    maxLength: 40,
    hint: 'Identificador del colegio profesional',
  },
  { name: 'phone', label: 'Teléfono', type: 'tel', maxLength: 30 },
  {
    name: 'location',
    label: 'Ubicación',
    maxLength: 120,
    hint: 'Sede o dependencia UMSS donde ejerces',
  },
  {
    name: 'avatar_url',
    label: 'URL de avatar',
    type: 'url',
    hint: 'https://… — opcional',
  },
];

function errorMessageFromUnknown(err: unknown): string {
  if (err instanceof AdminApiException) {
    // Errores de validación: aplanar fieldErrors al general
    if (err.error.kind === 'validation' && err.error.fieldErrors) {
      const lines = Object.entries(err.error.fieldErrors)
        .map(([k, v]) => `${k}: ${v.join(', ')}`)
        .join(' · ');
      return lines || err.error.message;
    }
    return err.error.message;
  }
  return err instanceof Error ? err.message : 'Error desconocido';
}

export function ProfileSection() {
  // Cache del último perfil confirmado por el backend. Se hidrata vía
  // `onData` de ConfigSection (sin setState-during-render). Se actualiza
  // también tras un PATCH exitoso.
  const [profile, setProfile] = useState<AdminProfile | null>(null);

  const loadProfile = useCallback(() => adminConfigClient.getProfile(), []);

  async function handleUpdate(patch: Partial<AdminProfile>) {
    const updated = await adminConfigClient.updateProfile(patch);
    setProfile(updated);
  }

  return (
    <ConfigSection<AdminProfile>
      load={loadProfile}
      testId="profile-section"
      loadingText="Cargando perfil…"
      onData={setProfile}
    >
      {(data) => {
        const current = profile ?? data;
        return (
          <div data-testid="profile-section-content">
            <div className="biomed-history-item" data-testid="profile-header" style={{
              padding: 16, marginBottom: 16, display: 'flex', flexDirection: 'column', gap: 4,
            }}>
              <strong data-testid="profile-header-name">{current.full_name}</strong>
              <span className="biomed-history-item__meta">
                {current.email}
                {current.specialty ? ` · ${current.specialty}` : ''}
                {current.professional_license ? ` · ${current.professional_license}` : ''}
              </span>
            </div>

            <ConfigForm<AdminProfile, AdminProfileInput>
              initial={current}
              schema={profileSchema}
              fields={FIELDS}
              onSubmit={async (patch) => {
                try {
                  await handleUpdate(patch);
                } catch (err) {
                  throw new Error(errorMessageFromUnknown(err));
                }
              }}
              submitLabel="Guardar cambios"
              testId="profile-form"
            />
          </div>
        );
      }}
    </ConfigSection>
  );
}
