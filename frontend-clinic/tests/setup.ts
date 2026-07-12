/**
 * Setup global para Vitest.
 *
 * - Carga @testing-library/jest-dom para matchers como toBeInTheDocument.
 * - Inicia MSW antes de todas las pruebas (handlers + reset entre tests).
 * - Stub de import.meta.env.VITE_CLINIC_API_BASE para que samplesClient caiga en /api/clinic.
 */
import '@testing-library/jest-dom/vitest';
import { afterAll, afterEach, beforeAll, beforeEach } from 'vitest';
import { server } from '../src/clinic/msw/server';
import { resetMockData } from '../src/clinic/msw/handlers';

Object.defineProperty(import.meta, 'env', {
  value: { VITE_CLINIC_API_BASE: '/api/clinic' },
  writable: true,
});

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));
beforeEach(() => resetMockData());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
