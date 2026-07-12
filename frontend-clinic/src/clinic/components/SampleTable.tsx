import { Link } from 'react-router-dom';
import { RequireRole } from '../auth';
import type { SampleListItem } from '../types/sample';

const STATUS_LABELS: Record<string, string> = {
  PENDING_AI: 'Pendiente',
  PROCESSING: 'En proceso',
  READY: 'Revisión',
  VALIDATED: 'Validada',
  REJECTED: 'Rechazada',
};

interface SampleTableProps {
  items: SampleListItem[];
  onEdit: (id: string) => void;
  onDelete: (id: string) => void;
}

export function SampleTable({ items, onEdit, onDelete }: SampleTableProps) {
  if (items.length === 0) {
    return <p className="empty-state">No hay muestras que coincidan con los filtros.</p>;
  }

  return (
    <>
      <div className="table-header">
        <div>CHN</div>
        <div>Paciente</div>
        <div>Estado</div>
        <div>Analista</div>
        <div>Fecha</div>
        <div>Acciones</div>
      </div>
      <div>
        {items.map((item) => (
          <div className="table-row" key={item.id} data-testid={`sample-row-${item.id}`}>
            <div>
              <Link to={`/clinic/samples/${item.id}`}><strong>{item.chn_code}</strong></Link>
            </div>
            <div>{item.patient_ref}</div>
            <div>
              <span className="status-badge" data-status={item.status}>
                {STATUS_LABELS[item.status] ?? item.status}
              </span>
            </div>
            <div>{item.analyst_name}</div>
            <div>{new Date(item.created_at).toLocaleDateString('es-BO')}</div>
            <div className="actions">
              <button type="button" className="btn-outline" onClick={() => onEdit(item.id)}>
                <i className="fas fa-edit"></i> Editar
              </button>
              <RequireRole roles={['admin']}>
                <button type="button" className="btn-danger" onClick={() => onDelete(item.id)}>
                  <i className="fas fa-trash"></i> Eliminar
                </button>
              </RequireRole>
            </div>
          </div>
        ))}
      </div>
    </>
  );
}
