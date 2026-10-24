import { Link } from 'react-router-dom';

interface DegradedBannerProps {
  onRetry?: () => void;
  onDismiss?: () => void;
}

/** RN-07: se muestra cuando pipeline_client.py responde 503 ML_DEGRADED. */
export function DegradedBanner({ onRetry, onDismiss }: DegradedBannerProps) {
  return (
    <div role="alert" className="degraded-banner">
      <strong>⚠️ Pipeline de IA no disponible</strong>
      <p>El procesamiento automático está temporalmente fuera de servicio. Puede seguir creando y consultando muestras.</p>
      <div className="degraded-banner-actions">
        {onRetry && (
          <button type="button" onClick={onRetry}>↻ Reintentar</button>
        )}
        <Link to="/clinic/degraded">Ver modo manual →</Link>
        {onDismiss && (
          <button type="button" onClick={onDismiss} aria-label="Cerrar">✕</button>
        )}
      </div>
    </div>
  );
}
