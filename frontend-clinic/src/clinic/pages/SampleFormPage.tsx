import { useNavigate, useParams } from 'react-router-dom';
import { BiomedShell } from '../components/BiomedShell';
import { SampleFormModal } from '../components/SampleFormModal';
import { Skeleton } from '../components/Skeleton';
import { useSample } from '../hooks/useSamples';
import { useCreateSample, useUpdateSample } from '../hooks/useSampleMutations';
import type { SampleCreateRequest } from '../types/sample';

export function SampleFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEdit = Boolean(id);

  const { data: existing, isLoading } = useSample(id);
  const createMutation = useCreateSample();
  const updateMutation = useUpdateSample(id ?? '');

  function handleSubmit(data: SampleCreateRequest) {
    if (isEdit && id) {
      updateMutation.mutate({ patient_ref: data.patient_ref }, {
        onSuccess: () => navigate('/clinic/samples'),
      });
    } else {
      createMutation.mutate(data, {
        onSuccess: () => navigate('/clinic/samples'),
      });
    }
  }

  if (isEdit && isLoading) {
    return <BiomedShell><Skeleton rows={3} /></BiomedShell>;
  }

  return (
    <BiomedShell>
      <SampleFormModal
        mode={isEdit ? 'edit' : 'create'}
        initial={existing}
        onSubmit={handleSubmit}
        onCancel={() => navigate('/clinic/samples')}
        isSubmitting={createMutation.isPending || updateMutation.isPending}
      />
    </BiomedShell>
  );
}
