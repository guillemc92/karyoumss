import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './index.css';
import './clinic/styles/tokens.css';

const USE_MSW = import.meta.env.VITE_USE_MSW === 'true';

function mount() {
  const root = document.getElementById('root');
  if (!root) {
    throw new Error('Root element #root not found in index.html');
  }
  createRoot(root).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}

async function bootstrap() {
  if (USE_MSW) {
    const { worker } = await import('./clinic/msw/browser');
    // Toggle de demo del modo degradado (P4, DD-KARYO-004): solo en el build
    // MSW. Permite mostrar en vivo el "Modo Manual" sin caer el pipeline real.
    const { setDegradedMode, setSampleStatus, applyStatusOverrides } = await import('./clinic/msw/handlers');
    const w = window as unknown as {
      __biomedSetDegraded?: (v: boolean) => void;
      __biomedSetStatus?: (id: string, status: string) => void;
    };
    w.__biomedSetDegraded = setDegradedMode;
    // Demo del flujo Supervisor (S1): forzar ANALYST_VALIDATED sin recorrer todo el flujo.
    w.__biomedSetStatus = setSampleStatus as (id: string, status: string) => void;
    applyStatusOverrides(); // re-aplica overrides de estado persistidos tras un reload
    await worker.start({
      onUnhandledRequest: 'bypass',
      serviceWorker: { url: '/mockServiceWorker.js' },
    });
  }
  mount();
}

void bootstrap();
