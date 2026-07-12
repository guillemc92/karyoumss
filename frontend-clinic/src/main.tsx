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
    await worker.start({
      onUnhandledRequest: 'bypass',
      serviceWorker: { url: '/mockServiceWorker.js' },
    });
  }
  mount();
}

void bootstrap();
