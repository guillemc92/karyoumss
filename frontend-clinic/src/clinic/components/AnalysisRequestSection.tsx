import type { AnalysisRequestId } from '../types/registration';

interface AnalysisRequestSectionProps {
  selected: AnalysisRequestId[];
  onChange: (selected: AnalysisRequestId[]) => void;
}

const COLUMN_1: { id: AnalysisRequestId; label: string }[] = [
  { id: 'karyotype_high_res', label: 'Cariotipo de alta resolución (GTG-banding 450-550)' },
  { id: 'mosaicism', label: 'Análisis de mosaicismo' },
  { id: 'fish', label: 'FISH (Fluorescence in situ hybridization)' },
];

const COLUMN_2: { id: AnalysisRequestId; label: string }[] = [
  { id: 'array_cgh', label: 'Array-CGH (Microarray)' },
  { id: 'fragility_study', label: 'Estudio de fragilidad cromosómica' },
  { id: 'other', label: 'Otro (especificar en notas)' },
];

export function AnalysisRequestSection({ selected, onChange }: AnalysisRequestSectionProps) {
  function toggle(id: AnalysisRequestId) {
    onChange(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]);
  }

  function renderColumn(items: { id: AnalysisRequestId; label: string }[]) {
    return (
      <div className="checkbox-group">
        {items.map((item) => (
          <div className="checkbox-item" key={item.id}>
            <input
              type="checkbox"
              id={item.id}
              checked={selected.includes(item.id)}
              onChange={() => toggle(item.id)}
            />
            <label htmlFor={item.id}>{item.label}</label>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="form-section">
      <div className="form-section-title"><i className="fas fa-microscope"></i> Solicitud de Análisis</div>
      <div className="form-row">
        {renderColumn(COLUMN_1)}
        {renderColumn(COLUMN_2)}
      </div>
    </div>
  );
}
