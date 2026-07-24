/**
 * XaiModal — muestra el mapa de calor Grad-CAM de un cromosoma (ADR-0021 P2,
 * FSD-UC-003). Abrirlo registra XAI_VIEWED (BR-004), habilitando "Aceptar".
 */
import type { Chromosome, XaiResult } from '../types/karyotype';
import { confidencePercent } from '../types/karyotype';

interface XaiModalProps {
  chromosome: Chromosome;
  xai: XaiResult | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
}

export function XaiModal({ chromosome, xai, loading, error, onClose }: XaiModalProps) {
  return (
    <div className="modal-overlay" data-testid="xai-modal" role="dialog" aria-modal="true">
      <div className="modal-content modal-content--small">
        <h3>Explicabilidad (Grad-CAM) — Cromosoma {chromosome.predicted_class}</h3>
        <div style={{ padding: '1.5rem' }}>
          {loading && <p data-testid="xai-loading">Generando mapa de calor…</p>}
          {error && <p role="alert" data-testid="xai-error" className="field-error">{error}</p>}
          {xai && (
            <>
              <p className="karyo-props__semaphore">
                Confianza del modelo: <strong>{confidencePercent(xai.confidence_score)}</strong>
              </p>
              <img
                src={`data:image/png;base64,${xai.heatmap_base64}`}
                alt={`Mapa de calor Grad-CAM del cromosoma ${chromosome.predicted_class}`}
                data-testid="xai-heatmap"
                style={{ width: '100%', maxWidth: 260, imageRendering: 'pixelated', border: '1px solid var(--border-light)', borderRadius: 8, marginTop: 8 }}
              />
              <p className="karyo-props__hint" style={{ marginTop: 8 }}>
                Las regiones resaltadas son las bandas que más pesaron en la clasificación.
                Consultada la explicabilidad, ya puede aceptar o corregir el cromosoma.
              </p>
            </>
          )}
        </div>
        <div className="modal-actions">
          <button type="button" onClick={onClose} data-testid="xai-close">Entendido</button>
        </div>
      </div>
    </div>
  );
}
