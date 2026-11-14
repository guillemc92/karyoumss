import { useEffect, useState } from 'react';

interface BusyBannerProps {
  /** Segundos que el backend pide esperar (`retry_after_seconds`). */
  seconds: number;
  onRetry: () => void;
  onDismiss?: () => void;
}

/**
 * DD-OBS-001 D8: el motor de IA está sano y ocupado con otro caso (503 ML_BUSY).
 * No es el modo degradado: no se ofrece el modo manual, se cuenta la espera y
 * se deja reintentar. Es un aviso (`role="status"`), no una alerta.
 */
export function BusyBanner({ seconds, onRetry, onDismiss }: BusyBannerProps) {
  const [quedan, setQuedan] = useState(seconds);

  useEffect(() => {
    setQuedan(seconds);
    const reloj = setInterval(() => setQuedan((n) => (n > 0 ? n - 1 : 0)), 1000);
    return () => clearInterval(reloj);
  }, [seconds]);

  return (
    <div role="status" className="busy-banner">
      <strong>⏳ El motor de IA está procesando otro caso</strong>
      <p>
        El motor funciona, pero atiende un caso a la vez. Su muestra no cambió.{' '}
        {quedan > 0 ? `Conviene reintentar en ${quedan} s.` : 'Ya puede reintentar.'}
      </p>
      <div className="busy-banner-actions">
        <button type="button" onClick={onRetry}>↻ Reintentar</button>
        {onDismiss && (
          <button type="button" className="busy-banner-close" onClick={onDismiss} aria-label="Cerrar">✕</button>
        )}
      </div>
    </div>
  );
}
