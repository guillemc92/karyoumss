/**
 * MSW worker para browser — se carga opcionalmente en dev cuando VITE_USE_MSW=true.
 * Útil para demos sin backend-clinic levantado (T66).
 */
import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';

export const worker = setupWorker(...handlers);
