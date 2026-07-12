import { useEffect } from 'react';
import { useStatusPolling } from '../hooks/useProcessPipeline';
import { DegradedBanner } from './DegradedBanner';

interface RegisterProcessingModalProps {
  sampleId: string;
  degraded: boolean;
  onComplete: () => void;
}

const TERMINAL = new Set(['READY', 'VALIDATED', 'REJECTED']);

const STEPS = [
  { key: 'detection', label: 'Detección de metafases y filtrado de calidad', activeAt: 'PROCESSING' },
  // ADR-0016 D1: corregido "Mask R-CNN" (viola AGENTS §11) a "U-Net" (modelo real)
  { key: 'segmentation', label: 'Segmentación de instancias (U-Net)', activeAt: 'PROCESSING' },
  { key: 'classification', label: 'Clasificación de bandas y ordenamiento ISCN', activeAt: 'READY' },
];

export function RegisterProcessingModal({ sampleId, degraded, onComplete }: RegisterProcessingModalProps) {
  const { data } = useStatusPolling(sampleId, !degraded);
  const status = data?.status ?? 'PENDING_AI';
  const isTerminal = TERMINAL.has(status);
  const progress = data?.progress !== undefined ? Math.round(data.progress * 100) : 0;

  useEffect(() => {
    if (isTerminal) {
      const t = setTimeout(onComplete, 800);
      return () => clearTimeout(t);
    }
  }, [isTerminal, onComplete]);

  return (
    <div className="ai-modal-overlay" style={{ display: 'flex' }}>
      <div className="ai-modal-content">
        <i className="fas fa-brain fa-4x" style={{ marginBottom: '20px' }}></i>
        <h2>Procesando con Biomed IA</h2>

        {degraded ? (
          <DegradedBanner onRetry={onComplete} />
        ) : (
          <>
            <div className="ai-progress-container">
              <div className="ai-progress-bar" style={{ width: `${progress}%` }}></div>
            </div>
            <div className="ai-status-text">
              {isTerminal ? 'Cariograma listo para validación.' : `Procesando... ${progress}%`}
            </div>
            <div className="ai-steps">
              {STEPS.map((step) => (
                <div className={`ai-step${status === step.activeAt || isTerminal ? ' active' : ''}`} key={step.key}>
                  <i className="fas fa-check-circle"></i> {step.label}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
