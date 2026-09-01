import { useEffect, useState } from 'react';
import { useStatusPolling } from '../hooks/useProcessPipeline';
import { DegradedBanner } from './DegradedBanner';

interface RegisterProcessingModalProps {
  /** null mientras el POST /register/ sigue en vuelo: aún no hay muestra que consultar. */
  sampleId: string | null;
  degraded: boolean;
  onComplete: () => void;
}

const TERMINAL = new Set(['READY', 'VALIDATED', 'REJECTED']);

// El registro llama al motor de inferencia de forma SÍNCRONA dentro del POST
// (`SampleRegistrationService.register` → `pipeline_client.segment_image`), así
// que la petición bloquea decenas de segundos. Medido el 19/08 sobre 3
// metafases reales: 31,9 s. Se usa para situar al usuario, no para fingir un
// porcentaje que el servidor no está enviando.
const SEGUNDOS_TIPICOS = 32;

const STEPS = [
  { key: 'detection', label: 'Detección de metafases y filtrado de calidad', activeAt: 'PROCESSING' },
  // ADR-0016 D1 corrigió "Mask R-CNN" por "U-Net", pero U-Net tampoco se llegó
  // a construir: es diseño. Lo que corre hoy lo declara la cadena de versión
  // del servicio, `opencv-watershed-v0+efficientnet-b3-metaclass-v3`, y es lo
  // que se nombra aquí. La pantalla no puede afirmar un modelo que no existe.
  { key: 'segmentation', label: 'Segmentación de cromosomas (OpenCV + watershed)', activeAt: 'PROCESSING' },
  { key: 'classification', label: 'Clasificación con EfficientNet-B3 y ordenamiento', activeAt: 'READY' },
];

/** Segundos transcurridos desde que se montó el componente. */
function useSegundosTranscurridos(activo: boolean) {
  const [segundos, setSegundos] = useState(0);
  useEffect(() => {
    if (!activo) return;
    const id = setInterval(() => setSegundos((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [activo]);
  return segundos;
}

export function RegisterProcessingModal({ sampleId, degraded, onComplete }: RegisterProcessingModalProps) {
  const enVuelo = sampleId === null;
  const { data } = useStatusPolling(sampleId ?? '', !degraded && !enVuelo);
  const status = data?.status ?? 'PENDING_AI';
  const isTerminal = !enVuelo && TERMINAL.has(status);
  const transcurridos = useSegundosTranscurridos(enVuelo && !degraded);

  // Mientras el POST está en vuelo el servidor no reporta avance: la barra
  // refleja el tiempo transcurrido contra la duración medida, y se detiene en
  // el 95% en vez de mentir con un 100% que no se ha alcanzado.
  const progress = enVuelo
    ? Math.min(95, Math.round((transcurridos / SEGUNDOS_TIPICOS) * 100))
    : data?.progress !== undefined ? Math.round(data.progress * 100) : 0;

  useEffect(() => {
    if (isTerminal) {
      const t = setTimeout(onComplete, 800);
      return () => clearTimeout(t);
    }
  }, [isTerminal, onComplete]);

  let texto: string;
  if (isTerminal) {
    texto = 'Cariograma listo para validación.';
  } else if (enVuelo) {
    texto = `Analizando las metafases... ${transcurridos} s (suele tardar unos ${SEGUNDOS_TIPICOS} s)`;
  } else {
    texto = `Procesando... ${progress}%`;
  }

  return (
    <div className="ai-modal-overlay" style={{ display: 'flex' }}>
      <div className="ai-modal-content">
        <i className="fas fa-brain fa-4x" style={{ marginBottom: '20px' }}></i>
        <h2>Procesando con Biomed IA</h2>

        {degraded ? (
          <DegradedBanner onRetry={onComplete} />
        ) : (
          <>
            <div
              className="ai-progress-container"
              role="progressbar"
              aria-label="Progreso del análisis"
              aria-valuenow={progress}
              aria-valuemin={0}
              aria-valuemax={100}
            >
              <div className="ai-progress-bar" style={{ width: `${progress}%` }}></div>
            </div>
            <div className="ai-status-text">{texto}</div>
            <div className="ai-steps">
              {STEPS.map((step) => (
                <div
                  className={`ai-step${!enVuelo && (status === step.activeAt || isTerminal) ? ' active' : ''}`}
                  key={step.key}
                >
                  <i className="fas fa-check-circle"></i> {step.label}
                </div>
              ))}
            </div>
            {enVuelo && (
              <p style={{ fontSize: '0.85rem', opacity: 0.75, marginTop: '12px' }}>
                No cierres esta ventana: la muestra se guarda al terminar.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
