import { useStatusPolling } from '../hooks/useProcessPipeline';

const TERMINAL = new Set(['READY', 'VALIDATED', 'REJECTED']);

interface StatusPollerProps {
  sampleId: string;
  initialStatus: string;
}

export function StatusPoller({ sampleId, initialStatus }: StatusPollerProps) {
  const shouldPoll = !TERMINAL.has(initialStatus) || initialStatus === 'PROCESSING';
  const { data, isLoading } = useStatusPolling(sampleId, shouldPoll);

  const status = data?.status ?? initialStatus;
  const isPolling = shouldPoll && status !== undefined && !TERMINAL.has(status);

  return (
    <div className="status-poller" role="status">
      <div className="status-poller-track">
        <span data-active={status === 'PENDING_AI'}>PENDING_AI</span>
        <span>→</span>
        <span data-active={status === 'PROCESSING'}>PROCESSING</span>
        <span>→</span>
        <span data-active={status === 'READY' || status === 'VALIDATED'}>READY</span>
      </div>
      {data?.chromosome_count !== undefined && (
        <p>chromosomes: {data.chromosome_count}/46 confidence_avg: {data.confidence_avg ?? '—'}</p>
      )}
      {isPolling && !isLoading && <p>⏳ Polling cada 2s...</p>}
    </div>
  );
}
