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
    <table className="sample-table">
      <thead>
        <tr>
          <th>CHN</th>
          <th>Paciente</th>
          <th>Estado</th>
          <th>Analista</th>
          <th>Fecha</th>
          <th>Acciones</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.id} data-testid={`sample-row-${item.id}`}>
            <td>
              <Link to={`/clinic/samples/${item.id}`}>{item.chn_code}</Link>
            </td>
            <td>{item.patient_ref}</td>
            <td>
              <span className="status-badge" data-status={item.status}>
                {STATUS_LABELS[item.status] ?? item.status}
              </span>
            </td>
            <td>{item.analyst_name}</td>
            <td>{new Date(item.created_at).toLocaleDateString('es-BO')}</td>
            <td className="actions">
              <button type="button" onClick={() => onEdit(item.id)}>Editar</button>
              <RequireRole roles={['admin']}>
                <button type="button" onClick={() => onDelete(item.id)}>Eliminar</button>
              </RequireRole>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
