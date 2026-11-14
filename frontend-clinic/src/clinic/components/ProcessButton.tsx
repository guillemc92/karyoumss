import { useTriggerProcess } from '../hooks/useProcessPipeline';
import { BusyBanner } from './BusyBanner';
import { DegradedBanner } from './DegradedBanner';

interface ProcessButtonProps {
  sampleId: string;
  status: string;
}

export function ProcessButton({ sampleId, status }: ProcessButtonProps) {
  const { mutate, isPending, degraded, resetDegraded, busySeconds, resetBusy } = useTriggerProcess(sampleId);

  const disabled = isPending || status === 'PROCESSING' || status === 'VALIDATED';

  return (
    <div>
      <button type="button" disabled={disabled} onClick={() => mutate(false)}>
        {isPending ? 'Encolando...' : status === 'PROCESSING' ? 'Procesando...' : '▶ Procesar'}
      </button>
      {busySeconds !== null && (
        <BusyBanner seconds={busySeconds} onRetry={() => mutate(false)} onDismiss={resetBusy} />
      )}
      {degraded && (
        <DegradedBanner onRetry={() => { resetDegraded(); mutate(false); }} onDismiss={resetDegraded} />
      )}
    </div>
  );
}
