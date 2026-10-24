/**
 * MSW worker para browser — se carga opcionalmente en dev cuando VITE_USE_MSW=true.
 * Útil para demos sin backend levantado (F4/F5).
 *
 * En prod real, MSW está deshabilitado y se conecta al backend real.
 */
import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';

export const worker = setupWorker(...handlers);