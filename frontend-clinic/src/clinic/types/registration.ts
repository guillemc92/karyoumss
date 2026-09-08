export interface PatientData {
  full_name: string;
  birth_date: string;
  document_id: string;
  phone: string;
}

export interface SampleData {
  chn_code: string;
  sample_type: string;
  culture_method: string;
  collection_date: string;
  reception_date: string;
  requesting_doctor: string;
  department: string;
  gender: 'M' | 'F' | 'O' | '';
}

export interface ClinicalHistory {
  indication: string;
  family_history: string;
}

export type AnalysisRequestId =
  | 'karyotype_high_res'
  | 'mosaicism'
  | 'fish'
  | 'array_cgh'
  | 'fragility_study'
  | 'other';

export interface CapturedImage {
  data_base64: string;
  source: 'camera' | 'upload';
}

export interface SampleRegistrationData {
  patient: PatientData;
  sample: SampleData;
  clinical_history: ClinicalHistory;
  analysis_requests: AnalysisRequestId[];
  images: CapturedImage[];
  is_draft: boolean;
}

export interface RegistrationResponse {
  id: string;
  chn_code: string;
  sample_code: string;
  status: 'DRAFT' | 'PENDING_AI';
  task_id: string | null;
  image_count: number;
  /**
   * Cuántas de esas imágenes se analizaron de verdad. Hoy es 1 (ADR-0036):
   * se suben tres metafases y se segmenta la primera. No es lo mismo que
   * `image_count`, y confundirlos hace creer al analista que el cariotipo
   * viene de las tres.
   */
  analyzed_count: number;
  degraded: boolean;
  created_at: string;
}
