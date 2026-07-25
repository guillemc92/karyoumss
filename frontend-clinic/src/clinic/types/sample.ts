export type SampleStatus =
  | 'DRAFT' | 'PENDING_AI' | 'PROCESSING' | 'READY'
  | 'BLOCKED_BY_CONFIDENCE' | 'ANALYST_VALIDATED'
  | 'SIGNED' | 'REPORTED' // flujo del Supervisor (ADR-0023 S2/S3)
  | 'VALIDATED' | 'REJECTED';

export interface SampleMetadata {
  gender?: 'M' | 'F';
  age?: number;
  notes?: string;
  [key: string]: unknown;
}

export interface SampleListItem {
  id: string;
  chn_code: string;
  patient_ref: string;
  status: SampleStatus;
  analyst_name: string;
  has_karyotype: boolean;
  created_at: string;
  updated_at: string;
}

export interface SampleRead {
  id: string;
  chn_code: string;
  patient_ref: string;
  image_path: string;
  status: SampleStatus;
  analyst: number;
  analyst_name: string;
  supervisor: number | null;
  supervisor_name: string;
  metadata: SampleMetadata;
  created_at: string;
  updated_at: string;
  chromosome_count?: number;
  confidence_avg?: number;
}

export interface SampleListResponse {
  items?: SampleListItem[];
  total?: number;
  page?: number;
  page_size?: number;
}

export interface SampleCreateRequest {
  chn_code: string;
  patient_ref: string;
  image_path?: string;
  metadata?: SampleMetadata;
}

export interface SampleUpdateRequest {
  patient_ref?: string;
  metadata?: SampleMetadata;
}

export interface SampleFilters {
  status?: SampleStatus;
  chn_query?: string;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

export interface ProcessResponse {
  sample_id: string;
  task_id: string;
  status: 'queued';
}

export interface StatusResponse {
  sample_id: string;
  status: SampleStatus;
  progress?: number;
  task_id?: string;
  chromosome_count?: number;
  confidence_avg?: number;
}

export interface MLDegradedError {
  code: 'ML_DEGRADED';
  detail: string;
  retry_after_seconds: number;
}

export class ClinicApiException extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly code?: string,
  ) {
    super(message);
    this.name = 'ClinicApiException';
  }
}
