import { useState, type FormEvent } from 'react';
import { z } from 'zod';
import type { SampleCreateRequest, SampleRead } from '../types/sample';

const createSchema = z.object({
  chn_code: z.string().min(1, 'CHN requerido'),
  patient_ref: z.string().min(1, 'Paciente requerido'),
  image_path: z.string().optional(),
});

const updateSchema = z.object({
  patient_ref: z.string().min(1, 'Paciente requerido'),
});

interface SampleFormModalProps {
  mode: 'create' | 'edit';
  initial?: SampleRead;
  onSubmit: (data: SampleCreateRequest) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
}

export function SampleFormModal({ mode, initial, onSubmit, onCancel, isSubmitting }: SampleFormModalProps) {
  const [chnCode, setChnCode] = useState(initial?.chn_code ?? '');
  const [patientRef, setPatientRef] = useState(initial?.patient_ref ?? '');
  const [imagePath, setImagePath] = useState(initial?.image_path ?? '');
  const [errors, setErrors] = useState<Record<string, string>>({});

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const schema = mode === 'create' ? createSchema : updateSchema;
    const payload = mode === 'create'
      ? { chn_code: chnCode, patient_ref: patientRef, image_path: imagePath }
      : { patient_ref: patientRef };

    const result = schema.safeParse(payload);
    if (!result.success) {
      const fieldErrors: Record<string, string> = {};
      for (const issue of result.error.issues) {
        fieldErrors[String(issue.path[0])] = issue.message;
      }
      setErrors(fieldErrors);
      return;
    }
    setErrors({});
    onSubmit({ chn_code: chnCode, patient_ref: patientRef, image_path: imagePath });
  }

  return (
    <div role="dialog" aria-modal="true" className="modal-overlay">
      <div className="modal-content">
        <h3>{mode === 'create' ? 'Nueva Muestra' : 'Editar Muestra'}</h3>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="chn_code">CHN *</label>
            <input
              id="chn_code"
              value={chnCode}
              onChange={(e) => setChnCode(e.target.value)}
              disabled={mode === 'edit'}
            />
            {errors.chn_code && <span className="field-error">{errors.chn_code}</span>}
          </div>
          <div className="form-group">
            <label htmlFor="patient_ref">Paciente *</label>
            <input
              id="patient_ref"
              value={patientRef}
              onChange={(e) => setPatientRef(e.target.value)}
            />
            {errors.patient_ref && <span className="field-error">{errors.patient_ref}</span>}
          </div>
          {mode === 'create' && (
            <div className="form-group">
              <label htmlFor="image_path">Imagen (S3 path)</label>
              <input id="image_path" value={imagePath} onChange={(e) => setImagePath(e.target.value)} />
            </div>
          )}
          <div className="modal-actions">
            <button type="button" onClick={onCancel}>Cancelar</button>
            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Guardando...' : 'Guardar Muestra'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
