/**
 * Tipos del recurso AdminUser.
 *
 * Espejo de backend-admin/apps/users/serializers.py#AdminUserSerializer.
 * Si el serializer cambia, actualizar esto y avisar al backend.
 */

export type AdminRole = 'analista' | 'supervisor' | 'admin';

export const ADMIN_ROLES: readonly AdminRole[] = ['analista', 'supervisor', 'admin'] as const;

export interface AdminUser {
  id: string; // UUID
  full_name: string;
  email: string;
  role: AdminRole;
  active: boolean;
  created_at: string; // ISO-8601
  updated_at: string; // ISO-8601
  created_by: string | null; // UUID del AdminUser creador (o null si seed)
}

export type AdminUserDraft = Pick<AdminUser, 'full_name' | 'email' | 'role' | 'active'>;

export interface AdminUserUpdate {
  full_name?: string;
  role?: AdminRole;
  active?: boolean;
}

/** Entrada del audit log expuesta por GET /admin/users/{id}/history (django-auditlog). */
export interface AuditLogEntry {
  id: number;
  action: 'create' | 'update' | 'delete';
  timestamp: string; // ISO-8601
  actor_email: string | null;
  changes: Record<string, { from: unknown; to: unknown }>;
  object_repr: string;
}

/** Errores que adminClient.ts puede lanzar (discriminados por `kind`). */
export type AdminApiError =
  | { kind: 'network'; message: string }
  | { kind: 'unauthorized'; message: string }
  | { kind: 'forbidden'; message: string }
  | { kind: 'not_found'; message: string }
  | { kind: 'conflict'; message: string; detail?: string }
  | { kind: 'validation'; message: string; fieldErrors: Record<string, string[]> }
  | { kind: 'server'; message: string; status: number }
  | { kind: 'unknown'; message: string; status: number };

export class AdminApiException extends Error {
  public readonly error: AdminApiError;
  constructor(error: AdminApiError) {
    super(error.message);
    this.name = 'AdminApiException';
    this.error = error;
  }
}