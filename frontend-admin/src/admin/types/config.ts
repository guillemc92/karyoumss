/**
 * Tipos del bounded context config (DD-ADMIN-002 P1).
 *
 * Espejo de backend-admin/apps/config/serializers.py#AdminProfileSerializer
 * y apps/config/views.py#MeProfileView.
 */
import { z } from 'zod';

// =============================================================================
// AdminProfile
// =============================================================================

/** Zod schema para validación cliente. Espejo del AdminProfileSerializer del backend. */
export const profileSchema = z.object({
  full_name: z
    .string()
    .trim()
    .min(3, 'Nombre 3-80 caracteres')
    .max(80, 'Nombre 3-80 caracteres'),
  email: z
    .string()
    .trim()
    .toLowerCase()
    .email('Email inválido'),
  specialty: z.string().max(80, 'Máximo 80 caracteres').default(''),
  professional_license: z.string().max(40, 'Máximo 40 caracteres').default(''),
  // Regex E.164 ligero: +591 2 2154847, (591) 22154847, vacío permitido
  phone: z
    .string()
    .max(30, 'Máximo 30 caracteres')
    .refine(
      (v) => v === '' || /^\+?[\d\s\-()]{6,30}$/.test(v),
      'Teléfono inválido',
    )
    .default(''),
  location: z.string().max(120, 'Máximo 120 caracteres').default(''),
  avatar_url: z
    .string()
    .refine(
      (v) => v === '' || /^https?:\/\/.+/.test(v),
      'URL debe empezar con http:// o https://',
    )
    .default(''),
});

/** Tipo inferido del Zod schema. */
export type AdminProfileInput = z.input<typeof profileSchema>;
export type AdminProfile = z.output<typeof profileSchema> & {
  id: string;
  updated_at: string;
  /** P2 — read-only, vive en users.User (ver AdminProfileSerializer). */
  two_factor_enabled: boolean;
};

/** Patch parcial para PATCH /api/admin/me/profile/. */
export type AdminProfileUpdate = Partial<AdminProfileInput>;

// =============================================================================
// Seguridad (P2 — DD-ADMIN-002 §3, ADR-0014)
// Espejo de backend-admin/apps/config/services.py + serializers.py.
// =============================================================================

/** Espejo de services.PASSWORD_MIN_LENGTH + reglas de rotate_password. */
export const changePasswordSchema = z
  .object({
    current: z.string().min(1, 'Requerido'),
    new: z
      .string()
      .min(12, 'Mínimo 12 caracteres, 1 mayúscula, 1 dígito')
      .refine((v) => /[A-Z]/.test(v), 'Mínimo 12 caracteres, 1 mayúscula, 1 dígito')
      .refine((v) => /[0-9]/.test(v), 'Mínimo 12 caracteres, 1 mayúscula, 1 dígito'),
    confirm: z.string().min(1, 'Requerido'),
  })
  .refine((data) => data.new === data.confirm, {
    message: 'No coincide con la nueva contraseña',
    path: ['confirm'],
  });

export type ChangePasswordInput = z.infer<typeof changePasswordSchema>;

/** Espejo de services.setup_2fa: {secret, qr_code_b64} (POST /me/2fa/setup/). */
export interface TwoFactorSetup {
  secret: string;
  qr_code_b64: string;
}

/** Código TOTP de 6 dígitos exigido por services.toggle_2fa. */
export const totpCodeSchema = z
  .string()
  .trim()
  .regex(/^\d{6}$/, 'Código de 6 dígitos');

/** Respuesta de POST /me/2fa/toggle/. */
export interface TwoFactorToggleResult {
  two_factor_enabled: boolean;
}

// =============================================================================
// Notificaciones (P4 — DD-ADMIN-002 §5, ADR-0014)
// Espejo de backend-admin/apps/config/models.py::NotificationPreference.
// =============================================================================

/** Espejo de NotificationPreferenceSerializer. quiet_hours_* llegan como
 * "HH:MM:SS" (TimeField de DRF); <input type="time"> usa "HH:MM". */
export interface NotificationPreference {
  id: string;
  email_review_pending: boolean;
  email_supervisor_validation: boolean;
  email_system_errors: boolean;
  email_training_completed: boolean;
  inapp_review_pending: boolean;
  inapp_supervisor_validation: boolean;
  inapp_system_errors: boolean;
  inapp_training_completed: boolean;
  quiet_hours_enabled: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
  updated_at: string;
}

export type NotificationPreferenceUpdate = Partial<
  Omit<NotificationPreference, 'id' | 'updated_at'>
>;

// =============================================================================
// Modelo IA (P3 — DD-ADMIN-002 §4, ADR-0014)
// Espejo de backend-admin/apps/config/models.py::ModelConfig/ModelMetric.
// =============================================================================

export const analysisModeSchema = z.enum(['fast', 'balanced', 'accurate']);
export type AnalysisMode = z.infer<typeof analysisModeSchema>;

export const logLevelSchema = z.enum(['WARNING', 'INFO', 'DEBUG']);
export type LogLevel = z.infer<typeof logLevelSchema>;

/** Espejo de ModelConfigSerializer. Los campos Decimal de DRF serializan
 * como string ("0.850"), no number — se parsean en el componente. */
export interface ModelConfig {
  id: string;
  is_active: boolean;
  unet_version: string;
  unet_enabled: boolean;
  classifier_version: string;
  classifier_enabled: boolean;
  confidence_threshold: string;
  detection_sensitivity: string;
  analysis_mode: AnalysisMode;
  log_level: LogLevel;
  updated_at: string;
  updated_by: string | null;
  compliance_warning: boolean;
}

/** Validación cliente del PATCH — espejo de ModelConfigSerializer
 * (rangos 0-1 en services de confidence_threshold/detection_sensitivity). */
export const modelConfigUpdateSchema = z.object({
  unet_enabled: z.boolean().optional(),
  classifier_enabled: z.boolean().optional(),
  confidence_threshold: z.number().min(0, 'Debe estar entre 0 y 1').max(1, 'Debe estar entre 0 y 1').optional(),
  detection_sensitivity: z.number().min(0, 'Debe estar entre 0 y 1').max(1, 'Debe estar entre 0 y 1').optional(),
  analysis_mode: analysisModeSchema.optional(),
  log_level: logLevelSchema.optional(),
});
export type ModelConfigUpdate = z.infer<typeof modelConfigUpdateSchema>;

/** Espejo de ModelMetricSerializer (snapshot append-only). */
export interface ModelMetric {
  id: number;
  measured_at: string;
  precision_overall: string;
  precision_per_class: Record<string, number>;
  recall_overall: string;
  f1_overall: string;
  latency_p50_ms: number;
  latency_p95_ms: number;
  latency_p99_ms: number;
  samples_evaluated: number;
  created_at: string;
}
