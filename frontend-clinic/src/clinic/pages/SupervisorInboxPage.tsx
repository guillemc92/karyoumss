/**
 * SupervisorInboxPage — bandeja de trabajo del Supervisor (FSD-UC-005/006).
 *
 * El Supervisor entraba por la misma lista que el Analista y tenía que abrir
 * caso por caso para descubrir si le tocaba auditar, firmar o reportar. Esta
 * bandeja invierte eso: agrupa los casos por la acción que corresponde a cada
 * estado del flujo (ADR-0023).
 *
 *   ANALYST_VALIDATED → auditar el 5% y firmar (S1 + S2)
 *   SIGNED            → generar el ISCN (S3)
 *   REPORTED          → cerrado, solo consulta
 *
 * Es una vista de navegación: no ejecuta acciones clínicas, lleva al visor —
 * donde vive el gating real y la traza de auditoría.
 */
import { useNavigate } from 'react-router-dom';
import { BiomedShell } from '../components/BiomedShell';
import { Skeleton } from '../components/Skeleton';
import { useSamples } from '../hooks/useSamples';
import { useSession } from '../auth';
import type { SampleListItem, SampleStatus } from '../types/sample';

interface Etapa {
  status: SampleStatus;
  titulo: string;
  descripcion: string;
  accion: string;
  icono: string;
  clase: string;
}

/** Orden = el del flujo: lo que espera acción primero. */
const ETAPAS: Etapa[] = [
  {
    status: 'ANALYST_VALIDATED',
    titulo: 'Pendientes de auditoría y firma',
    descripcion: 'El analista validó el caso. Revise la auditoría del 5% y firme con MFA.',
    accion: 'Auditar y firmar',
    icono: 'fa-clipboard-check',
    clase: 'inbox-stage--pending',
  },
  {
    status: 'SIGNED',
    titulo: 'Firmados, pendientes de ISCN',
    descripcion: 'Firmado digitalmente. Falta generar la nomenclatura para emitir el informe.',
    accion: 'Generar ISCN',
    icono: 'fa-dna',
    clase: 'inbox-stage--signed',
  },
  {
    status: 'REPORTED',
    titulo: 'Reportados',
    descripcion: 'Con nomenclatura ISCN emitida. Solo consulta.',
    accion: 'Ver caso',
    icono: 'fa-file-medical',
    clase: 'inbox-stage--reported',
  },
];

function CasoRow({ caso, accion, onOpen }: { caso: SampleListItem; accion: string; onOpen: () => void }) {
  return (
    <li className="inbox-row" data-testid={`inbox-row-${caso.id}`}>
      <div className="inbox-row__info">
        <strong className="inbox-row__chn">{caso.chn_code}</strong>
        <span className="inbox-row__analyst">Analista: {caso.analyst_name || '—'}</span>
      </div>
      <button
        type="button" className="btn-primary" onClick={onOpen}
        data-testid={`inbox-open-${caso.id}`}
      >{accion}</button>
    </li>
  );
}

function Etapa({ etapa, casos, onOpen }: {
  etapa: Etapa;
  casos: SampleListItem[];
  onOpen: (id: string) => void;
}) {
  return (
    <section className={`inbox-stage ${etapa.clase}`} data-testid={`inbox-stage-${etapa.status}`}>
      <header className="inbox-stage__header">
        <h2><i className={`fas ${etapa.icono}`}></i> {etapa.titulo}</h2>
        <span className="inbox-stage__count" data-testid={`inbox-count-${etapa.status}`}>
          {casos.length}
        </span>
      </header>
      <p className="inbox-stage__desc">{etapa.descripcion}</p>

      {casos.length === 0 ? (
        <p className="inbox-stage__empty" data-testid={`inbox-empty-${etapa.status}`}>
          No hay casos en esta etapa.
        </p>
      ) : (
        <ul className="inbox-stage__list">
          {casos.map((c) => (
            <CasoRow key={c.id} caso={c} accion={etapa.accion} onOpen={() => onOpen(c.id)} />
          ))}
        </ul>
      )}
    </section>
  );
}

export function SupervisorInboxPage() {
  const navigate = useNavigate();
  const { role } = useSession();
  const { data: items = [], isLoading, isError } = useSamples();

  // RN-06: la bandeja es del Supervisor. El backend ya rechaza las acciones,
  // pero mostrarla a un analista sería confundirlo con trabajo que no le toca.
  if (role && role !== 'supervisor' && role !== 'admin') {
    return (
      <BiomedShell>
        <p role="alert" data-testid="inbox-forbidden">
          Esta bandeja es exclusiva del Supervisor.
        </p>
      </BiomedShell>
    );
  }

  const porEstado = (s: SampleStatus) => items.filter((i) => i.status === s);
  const totalPendiente = porEstado('ANALYST_VALIDATED').length + porEstado('SIGNED').length;

  return (
    <BiomedShell>
      <div className="page-header">
        <div>
          <h1><i className="fas fa-user-check"></i> Bandeja del Supervisor</h1>
          <p>Casos agrupados por la acción que les corresponde en el flujo</p>
        </div>
        {!isLoading && !isError && (
          <span className="inbox-total" data-testid="inbox-total-pending">
            {totalPendiente} caso(s) esperando acción
          </span>
        )}
      </div>

      {isLoading && <Skeleton />}
      {isError && (
        <p role="alert" data-testid="inbox-error">No se pudieron cargar los casos.</p>
      )}

      {!isLoading && !isError && (
        <div className="inbox-stages">
          {ETAPAS.map((etapa) => (
            <Etapa
              key={etapa.status}
              etapa={etapa}
              casos={porEstado(etapa.status)}
              onOpen={(id) => navigate(`/clinic/samples/${id}/karyotype`)}
            />
          ))}
        </div>
      )}
    </BiomedShell>
  );
}
