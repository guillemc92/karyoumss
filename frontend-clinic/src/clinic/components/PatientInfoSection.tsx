import type { PatientData, SampleData } from '../types/registration';

interface PatientInfoSectionProps {
  patient: PatientData;
  gender: SampleData['gender'];
  chnCode: string;
  onPatientChange: (patient: PatientData) => void;
  onGenderChange: (gender: SampleData['gender']) => void;
  onChnChange: (chn: string) => void;
}

export function PatientInfoSection({
  patient, gender, chnCode, onPatientChange, onGenderChange, onChnChange,
}: PatientInfoSectionProps) {
  return (
    <div className="form-section">
      <div className="form-section-title"><i className="fas fa-user"></i> Información del Paciente</div>
      <div className="form-row three-col">
        <div className="form-group">
          <label className="form-label">CHN (Historia Clínica) <span className="required">*</span></label>
          <input
            className="form-input"
            id="chn"
            placeholder="Ej: CHN-12345"
            value={chnCode}
            onChange={(e) => onChnChange(e.target.value)}
          />
          <small style={{ fontSize: '0.65rem', color: 'var(--gray-text)', marginTop: '4px' }}>
            Número único de historia clínica
          </small>
        </div>
        <div className="form-group">
          <label className="form-label">Nombre completo <span className="required">*</span></label>
          <input
            className="form-input"
            id="patientName"
            placeholder="Nombre del paciente"
            value={patient.full_name}
            onChange={(e) => onPatientChange({ ...patient, full_name: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label className="form-label">Fecha de nacimiento <span className="required">*</span></label>
          <input
            className="form-input"
            type="date"
            id="birthDate"
            value={patient.birth_date}
            onChange={(e) => onPatientChange({ ...patient, birth_date: e.target.value })}
          />
        </div>
      </div>
      <div className="form-row three-col">
        <div className="form-group">
          <label className="form-label">Género <span className="required">*</span></label>
          <select className="form-input" id="gender" value={gender} onChange={(e) => onGenderChange(e.target.value as SampleData['gender'])}>
            <option value="">Seleccionar...</option>
            <option value="M">Masculino</option>
            <option value="F">Femenino</option>
            <option value="O">Otro</option>
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">Documento de identidad</label>
          <input
            className="form-input"
            id="document"
            placeholder="CI / Pasaporte"
            value={patient.document_id}
            onChange={(e) => onPatientChange({ ...patient, document_id: e.target.value })}
          />
        </div>
        <div className="form-group">
          <label className="form-label">Teléfono de contacto</label>
          <input
            className="form-input"
            type="tel"
            id="phone"
            placeholder="+591 XXXXXXXX"
            value={patient.phone}
            onChange={(e) => onPatientChange({ ...patient, phone: e.target.value })}
          />
        </div>
      </div>
    </div>
  );
}
