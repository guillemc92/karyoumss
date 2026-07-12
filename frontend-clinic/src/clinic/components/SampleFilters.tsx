import { useEffect, useState } from 'react';
import type { SampleFilters as Filters, SampleStatus } from '../types/sample';

const STATUS_OPTIONS: { value: SampleStatus | ''; label: string }[] = [
  { value: '', label: 'Todas' },
  { value: 'PENDING_AI', label: 'Pendiente' },
  { value: 'PROCESSING', label: 'En proceso' },
  { value: 'READY', label: 'Revisión' },
  { value: 'VALIDATED', label: 'Validada' },
  { value: 'REJECTED', label: 'Rechazada' },
];

interface SampleFiltersProps {
  value: Filters;
  onChange: (filters: Filters) => void;
}

export function SampleFilters({ value, onChange }: SampleFiltersProps) {
  const [chnInput, setChnInput] = useState(value.chn_query ?? '');

  useEffect(() => {
    const t = setTimeout(() => {
      if (chnInput !== value.chn_query) {
        onChange({ ...value, chn_query: chnInput || undefined });
      }
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chnInput]);

  return (
    <div className="sample-filters">
      <input
        type="text"
        placeholder="Buscar CHN, paciente..."
        value={chnInput}
        onChange={(e) => setChnInput(e.target.value)}
        aria-label="Buscar por CHN"
      />
      <select
        value={value.status ?? ''}
        onChange={(e) => onChange({ ...value, status: (e.target.value || undefined) as SampleStatus | undefined })}
        aria-label="Filtrar por estado"
      >
        {STATUS_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
      <input
        type="date"
        value={value.date_from ?? ''}
        onChange={(e) => onChange({ ...value, date_from: e.target.value || undefined })}
        aria-label="Fecha desde"
      />
      <input
        type="date"
        value={value.date_to ?? ''}
        onChange={(e) => onChange({ ...value, date_to: e.target.value || undefined })}
        aria-label="Fecha hasta"
      />
    </div>
  );
}
