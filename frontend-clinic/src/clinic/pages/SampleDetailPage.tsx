import { Link, useNavigate, useParams } from 'react-router-dom';
import { BiomedShell } from '../components/BiomedShell';
import { ProcessButton } from '../components/ProcessButton';
import { StatusPoller } from '../components/StatusPoller';
import { Skeleton } from '../components/Skeleton';
import { useSample } from '../hooks/useSamples';

export function SampleDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: sample, isLoading, isError } = useSample(id);

  if (isLoading) return <BiomedShell><Skeleton rows={3} /></BiomedShell>;
  if (isError || !sample) return <BiomedShell><p role="alert">Muestra no encontrada.</p></BiomedShell>;

  return (
    <BiomedShell>
      <h1>{sample.chn_code}</h1>
      <p>Paciente: {sample.patient_ref} &nbsp; Estado: <span className="status-badge" data-status={sample.status}>{sample.status}</span></p>
      <p>Creada: {new Date(sample.created_at).toLocaleString('es-BO')} &nbsp; Por: {sample.analyst_name}</p>

      {sample.metadata && Object.keys(sample.metadata).length > 0 && (
        <div>
          <h3>Metadata</h3>
          <ul>
            {Object.entries(sample.metadata).map(([k, v]) => (
              <li key={k}>{k}: {String(v)}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="actions">
        <ProcessButton sampleId={sample.id} status={sample.status} />
        <button type="button" onClick={() => navigate(`/clinic/samples/${sample.id}/edit`)}>Editar</button>
        <a href={`/correccion de cariotipo.html?sample=${sample.id}`}>Ver cariotipo →</a>
      </div>

      <StatusPoller sampleId={sample.id} initialStatus={sample.status} />

      <Link to="/clinic/samples">← Volver a la lista</Link>
    </BiomedShell>
  );
}
