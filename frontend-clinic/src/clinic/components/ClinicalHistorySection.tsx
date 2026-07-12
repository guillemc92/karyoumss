import type { ClinicalHistory } from '../types/registration';

interface ClinicalHistorySectionProps {
  value: ClinicalHistory;
  onChange: (value: ClinicalHistory) => void;
}

export function ClinicalHistorySection({ value, onChange }: ClinicalHistorySectionProps) {
  return (
    <div className="form-section">
      <div className="form-section-title"><i className="fas fa-notes-medical"></i> Historial Clínico</div>
      <div className="form-group" style={{ marginBottom: 'var(--space-md)' }}>
        <label className="form-label">Motivo de la consulta / Indicación</label>
        <textarea
          className="form-input"
          id="indication"
          placeholder="Describa el motivo de la solicitud del estudio citogenético..."
          value={value.indication}
          onChange={(e) => onChange({ ...value, indication: e.target.value })}
        />
      </div>
      <div className="form-group">
        <label className="form-label">Antecedentes familiares relevantes</label>
        <textarea
          className="form-input"
          id="familyHistory"
          placeholder="Historial de condiciones genéticas en la familia..."
          value={value.family_history}
          onChange={(e) => onChange({ ...value, family_history: e.target.value })}
        />
      </div>
    </div>
  );
}
