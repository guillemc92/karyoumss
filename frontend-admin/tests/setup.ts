/**
 * Setup global para Vitest.
 *
 * - Carga @testing-library/jest-dom para matchers como toBeInTheDocument.
 * - Inicia MSW antes de todas las pruebas (handlers + reset entre tests).
 * - Stub de import.meta.env.VITE_ADMIN_API_BASE para que adminClient caiga en /api/admin.
 */
import '@testing-library/jest-dom/vitest';
import { afterAll, afterEach, beforeAll, beforeEach } from 'vitest';
import { server } from '../src/admin/msw/server';
import { resetMockData } from '../src/admin/msw/handlers';

// Stub de env var para adminClient → base '/api/admin'
// Vitest no procesa .env por defecto; MSW usa ruta relativa igual.
Object.defineProperty(import.meta, 'env', {
  value: { VITE_ADMIN_API_BASE: '/api/admin' },
  writable: true,
});

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
beforeEach(() => resetMockData());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
