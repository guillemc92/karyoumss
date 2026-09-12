/**
 * MswBootstrapError — banner visible cuando MSW no se carga.
 *
 * SPEC-007 §2.3: antes el error de `worker.start()` solo se logueaba a
 * consola (App.tsx catch). Eso era un "silent failure" — el dev veía
 * "Inicializando mock service worker…" eternamente y no sabía por qué.
 * Este componente da feedback visual + acción de recovery.
 *
 * Solo se renderiza en modo MSW (USE_MSW=true). En modo prod real este
 * componente nunca se monta.
 */
interface MswBootstrapErrorProps {
  error: unknown;
  onRetry: () => void;
}

function formatError(err: unknown): string {
  if (err instanceof Error) {
    // MSW suele lanzar con un mensaje tipo "Failed to start the Service
    // Worker". Lo mostramos tal cual, más un hint si es 404 (el SW no existe).
    if (/404|not found|fetch/i.test(err.message)) {
      return `${err.message}\n\nHint: ¿existe frontend-admin/public/mockServiceWorker.js? Regenerar con \`npx msw init public/ --save\`.`;
    }
    return err.message;
  }
  return String(err);
}

export function MswBootstrapError({ error, onRetry }: MswBootstrapErrorProps) {
  return (
    <main className="biomed-main" data-testid="msw-bootstrap-error">
      <div className="biomed-page-header">
        <h2>
          <i className="fas fa-triangle-exclamation" aria-hidden="true" />{' '}
          Mock Service Worker no se cargó
        </h2>
        <p>
          El demo de <code>frontend-admin</code> requiere MSW para mockear
          las llamadas a <code>/api/admin/*</code>. El SW no se pudo
          registrar; las llamadas habrían escapado al backend real (que
          no está corriendo).
        </p>
      </div>

      <div
        className="biomed-banner biomed-banner--error"
        role="alert"
        data-testid="msw-bootstrap-error-message"
        style={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace', fontSize: 13 }}
      >
        {formatError(error)}
      </div>

      <div className="biomed-form-actions" style={{ marginTop: 16 }}>
        <button
          type="button"
          className="biomed-btn biomed-btn--primary"
          onClick={onRetry}
          data-testid="msw-bootstrap-error-retry"
        >
          <i className="fas fa-rotate" aria-hidden="true" /> Reintentar
        </button>
        <a
          className="biomed-btn biomed-btn--outline"
          href="https://mswjs.io/docs/recipes/debugging-unhandled-requests"
          target="_blank"
          rel="noreferrer"
          data-testid="msw-bootstrap-error-docs"
        >
          <i className="fas fa-book" aria-hidden="true" /> Doc MSW
        </a>
      </div>
    </main>
  );
}
