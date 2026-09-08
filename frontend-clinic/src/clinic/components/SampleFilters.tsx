import { useEffect, useState } from 'react';
import type { SampleFilters as Filters, SampleStatus } from '../types/sample';

const STATUS_CHIPS: { value: SampleStatus | ''; label: string }[] = [
  { value: '', label: 'Todas' },
  { value: 'READY', label: '⚠️ Revisión' },
  { value: 'PROCESSING', label: '⏳ En proceso' },
  { value: 'VALIDATED', label: '✓ Completadas' },
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
    <div className="search-bar">
      <div className="search-input">
        <i className="fas fa-search"></i>
        <input
          type="text"
          placeholder="Buscar por ID, paciente o CHN..."
          value={chnInput}
          onChange={(e) => setChnInput(e.target.value)}
          aria-label="Buscar por CHN"
        />
      </div>
      <div className="filter-buttons">
        {STATUS_CHIPS.map((chip) => (
          <button
            key={chip.value || 'all'}
            type="button"
            className={`filter-chip${(value.status ?? '') === chip.value ? ' active' : ''}`}
            onClick={() => onChange({ ...value, status: (chip.value || undefined) as SampleStatus | undefined })}
          >
            {chip.label}
          </button>
        ))}
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
    </div>
  );
}
