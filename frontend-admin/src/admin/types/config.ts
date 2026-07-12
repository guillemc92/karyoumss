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
};

/** Patch parcial para PATCH /api/admin/me/profile/. */
export type AdminProfileUpdate = Partial<AdminProfileInput>;
