import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BiomedShell } from '../components/BiomedShell';
import { PatientInfoSection } from '../components/PatientInfoSection';
import { SampleInfoSection } from '../components/SampleInfoSection';
import { ClinicalHistorySection } from '../components/ClinicalHistorySection';
import { AnalysisRequestSection } from '../components/AnalysisRequestSection';
import { MetaphaseCaptureSection } from '../components/MetaphaseCaptureSection';
import { RegisterProcessingModal } from '../components/RegisterProcessingModal';
import { Toast } from '../components/Toast';
import { useSampleRegistration } from '../hooks/useSampleRegistration';
import { ClinicApiException } from '../types/sample';
import type {
  AnalysisRequestId, ClinicalHistory, PatientData, SampleData, CapturedImage,
} from '../types/registration';

function generateSampleCode(): string {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, '0');
  const d = String(now.getDate()).padStart(2, '0');
  const rand = Math.floor(Math.random() * 1000);
  return `BM-${y}${m}${d}-${rand}`;
}

const EMPTY_PATIENT: PatientData = { full_name: '', birth_date: '', document_id: '', phone: '' };
const EMPTY_SAMPLE: SampleData = {
  chn_code: '', sample_type: '', culture_method: '', collection_date: '',
  reception_date: '', requesting_doctor: '', department: '', gender: '',
};
const EMPTY_HISTORY: ClinicalHistory = { indication: '', family_history: '' };

export function SampleRegisterPage() {
  const navigate = useNavigate();
  const sampleCode = useMemo(generateSampleCode, []);

  const [patient, setPatient] = useState<PatientData>(EMPTY_PATIENT);
  const [sample, setSample] = useState<SampleData>(EMPTY_SAMPLE);
  const [history, setHistory] = useState<ClinicalHistory>(EMPTY_HISTORY);
  const [analysisRequests, setAnalysisRequests] = useState<AnalysisRequestId[]>(['karyotype_high_res']);
  const [images, setImages] = useState<CapturedImage[]>([]);
  const [formError, setFormError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [processingSampleId, setProcessingSampleId] = useState<string | null>(null);
  const [processingDegraded, setProcessingDegraded] = useState(false);

  const registration = useSampleRegistration();

  function resetForm() {
    setPatient(EMPTY_PATIENT);
    setSample(EMPTY_SAMPLE);
    setHistory(EMPTY_HISTORY);
    setAnalysisRequests(['karyotype_high_res']);
    setImages([]);
    setFormError(null);
  }

  function handleSaveDraft() {
    if (!sample.chn_code) {
      setFormError('Complete el CHN para guardar el borrador.');
      return;
    }
    registration.mutate(
      { patient, sample, clinical_history: history, analysis_requests: analysisRequests, images, is_draft: true },
      {
        onSuccess: () => setToast('Borrador guardado correctamente'),
        onError: (err) => setFormError(err instanceof ClinicApiException ? err.message : 'Error al guardar'),
      },
    );
  }

  function handleCancel() {
    if (window.confirm('¿Cancelar registro? Los datos no guardados se perderán.')) {
      resetForm();
      navigate('/clinic/samples');
    }
  }

  function handleSubmit() {
    setFormError(null);
    if (!sample.chn_code || !patient.full_name) {
      setFormError('Complete los campos obligatorios: CHN y Nombre del paciente.');
      return;
    }
    if (images.length < 3) {
      setFormError(`Se requieren al menos 3 metafases para el análisis (recomendado: 20). Actualmente tiene ${images.length}.`);
      return;
    }
    registration.mutate(
      { patient, sample, clinical_history: history, analysis_requests: analysisRequests, images, is_draft: false },
      {
        onSuccess: (result) => {
          setProcessingSampleId(result.id);
          setProcessingDegraded(result.degraded);
        },
        onError: (err) => setFormError(err instanceof ClinicApiException ? err.message : 'Error al registrar'),
      },
    );
  }

  function handleProcessingComplete() {
    navigate(`/correccion de cariotipo.html?sample=${processingSampleId}`);
  }

  return (
    <BiomedShell>
      <div className="page-header">
        <h1><i className="fas fa-clipboard-list"></i> Registro de Nueva Muestra</h1>
        <p>Complete la información del paciente y capture las imágenes de metafase</p>
      </div>

      <div className="alert-info">
        <i className="fas fa-info-circle"></i> <strong>Información importante:</strong> Los campos marcados con <span style={{ color: 'var(--umss-red)' }}>*</span> son obligatorios. Se requieren al menos 20 metafases de calidad.
      </div>

      {formError && <p role="alert" style={{ color: 'var(--umss-red)', marginBottom: '1rem' }}>{formError}</p>}

      <div className="form-card">
        <div className="card-header">
          <h2><i className="fas fa-dna"></i> Datos de la Muestra</h2>
          <p>Ingrese la información del paciente y las imágenes de metafase</p>
        </div>
        <div className="card-body">
          <PatientInfoSection
            patient={patient}
            gender={sample.gender}
            chnCode={sample.chn_code}
            onPatientChange={setPatient}
            onGenderChange={(gender) => setSample({ ...sample, gender })}
            onChnChange={(chn_code) => setSample({ ...sample, chn_code })}
          />
          <SampleInfoSection sample={sample} sampleCode={sampleCode} onChange={setSample} />
          <ClinicalHistorySection value={history} onChange={setHistory} />
          <AnalysisRequestSection selected={analysisRequests} onChange={setAnalysisRequests} />
          <MetaphaseCaptureSection images={images} onChange={setImages} />

          <div className="form-actions">
            <button type="button" className="btn btn-outline" onClick={handleSaveDraft} disabled={registration.isPending}>
              <i className="fas fa-save"></i> Guardar borrador
            </button>
            <button type="button" className="btn btn-outline" onClick={handleCancel}>
              <i className="fas fa-times"></i> Cancelar
            </button>
            <button type="button" className="btn btn-primary" onClick={handleSubmit} disabled={registration.isPending}>
              <i className="fas fa-robot"></i> Registrar y analizar con IA
            </button>
          </div>
        </div>
      </div>

      {processingSampleId && (
        <RegisterProcessingModal
          sampleId={processingSampleId}
          degraded={processingDegraded}
          onComplete={handleProcessingComplete}
        />
      )}

      {toast && <Toast message={toast} kind="success" onDismiss={() => setToast(null)} />}
    </BiomedShell>
  );
}
