/**
 * ConfigSection — esqueleto loading/error/data para secciones de
 * configuración (DD-ADMIN-002 P1–P6).
 *
 * Replica el patrón del AdminUsersPanel (status: idle/loading/success/error)
 * sin meter aún un store de Zustand. P1 lo usa en modo "self-fetch" —
 * P3 introducirá adminConfigStore (DD §11.3).
 */
import { ReactNode, useEffect, useState } from 'react';

export type ConfigStatus = 'idle' | 'loading' | 'success' | 'error';

interface ConfigSectionProps<T> {
  /** Llamada HTTP que devuelve el recurso. Se invoca en mount. */
  load: () => Promise<T>;
  /** Render del contenido con los datos. */
  children: (data: T, refresh: () => void) => ReactNode;
  /** Texto mientras carga. */
  loadingText?: string;
  /** data-testid raíz. */
  testId?: string;
  /** Callback opcional cuando llega data (útil para sincronizar caches padres). */
  onData?: (data: T) => void;
}

/**
 * Esqueleto genérico: gestiona status interno (loading/error/data) y expone
 * `refresh()` al children para que pueda re-disparar la carga.
 */
export function ConfigSection<T>({
  load,
  children,
  loadingText = 'Cargando…',
  testId = 'config-section',
  onData,
}: ConfigSectionProps<T>) {
  const [status, setStatus] = useState<ConfigStatus>('idle');
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchOnce = async () => {
    setStatus('loading');
    setError(null);
    try {
      const result = await load();
      setData(result);
      setStatus('success');
      onData?.(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error al cargar');
      setStatus('error');
    }
  };

  useEffect(() => {
    if (status === 'idle') {
      void fetchOnce();
    }
    // fetchOnce no es estable por diseño; el status-idle gate evita loops
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (status === 'loading' || status === 'idle') {
    return (
      <div className="biomed-placeholder" data-testid={`${testId}-loading`}>
        <div className="biomed-placeholder__icon">
          <i className="fas fa-spinner" aria-hidden="true" />
        </div>
        <div className="biomed-placeholder__title">{loadingText}</div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div data-testid={`${testId}-error`}>
        <p
          role="alert"
          className="biomed-banner biomed-banner--error"
          data-testid={`${testId}-error-message`}
        >
          <i className="fas fa-triangle-exclamation" aria-hidden="true" />
          {error}
        </p>
        <button
          type="button"
          className="biomed-btn biomed-btn--outline"
          onClick={() => void fetchOnce()}
          data-testid={`${testId}-retry`}
        >
          <i className="fas fa-rotate" aria-hidden="true" /> Reintentar
        </button>
      </div>
    );
  }

  return <>{children(data as T, () => void fetchOnce())}</>;
}
