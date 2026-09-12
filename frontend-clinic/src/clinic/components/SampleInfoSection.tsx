import type { SampleData } from '../types/registration';

interface SampleInfoSectionProps {
  sample: SampleData;
  sampleCode: string;
  onChange: (sample: SampleData) => void;
}

export function SampleInfoSection({ sample, sampleCode, onChange }: SampleInfoSectionProps) {
  return (
    <div className="form-section">
      <div className="form-section-title"><i className="fas fa-flask"></i> Información de la Muestra</div>
      <div className="form-row three-col">
        <div className="form-group">
          <label className="form-label">Código de muestra <span className="required">*</span></label>
          <input className="form-input" id="sampleCode" value={sampleCode} readOnly style={{ background: 'var(--gray-bg)' }} />
        </div>
        <div className="form-group">
          <label className="form-label">Tipo de muestra <span className="required">*</span></label>
          <select className="form-input" id="sampleType" value={sample.sample_type} onChange={(e) => onChange({ ...sample, sample_type: e.target.value })}>
            <option value="">Seleccionar...</option>
            <option value="sangre">Sangre periférica</option>
            <option value="medula">Médula ósea</option>
            <option value="amniotico">Líquido amniótico</option>
            <option value="vellosidades">Vellosidades coriales</option>
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">Método de cultivo</label>
          <select className="form-input" id="cultureMethod" value={sample.culture_method} onChange={(e) => onChange({ ...sample, culture_method: e.target.value })}>
            <option value="">Seleccionar...</option>
            <option value="72h">Sangre periférica — Cultura 72h</option>
            <option value="24h">Médula ósea — Cultura 24h</option>
            <option value="7d">Líquido amniótico — Cultura 7 días</option>
          </select>
        </div>
      </div>
      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Fecha de recolección <span className="required">*</span></label>
          <input className="form-input" type="date" id="collectionDate" value={sample.collection_date} onChange={(e) => onChange({ ...sample, collection_date: e.target.value })} />
        </div>
        <div className="form-group">
          <label className="form-label">Fecha de recepción en laboratorio</label>
          <input className="form-input" type="date" id="receptionDate" value={sample.reception_date} onChange={(e) => onChange({ ...sample, reception_date: e.target.value })} />
        </div>
      </div>
      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Médico solicitante</label>
          <input className="form-input" id="requestingDoctor" placeholder="Nombre del médico" value={sample.requesting_doctor} onChange={(e) => onChange({ ...sample, requesting_doctor: e.target.value })} />
        </div>
        <div className="form-group">
          <label className="form-label">Servicio/Departamento</label>
          <input className="form-input" id="department" placeholder="Ej: Genética Clínica" value={sample.department} onChange={(e) => onChange({ ...sample, department: e.target.value })} />
        </div>
      </div>
    </div>
  );
}
