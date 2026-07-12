import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BiomedShell } from '../components/BiomedShell';
import { SampleStats } from '../components/SampleStats';
import { SampleFilters } from '../components/SampleFilters';
import { SampleTable } from '../components/SampleTable';
import { SamplePagination } from '../components/SamplePagination';
import { SampleDeleteConfirm } from '../components/SampleDeleteConfirm';
import { Skeleton } from '../components/Skeleton';
import { Toast } from '../components/Toast';
import { useSamples } from '../hooks/useSamples';
import { useDeleteSample } from '../hooks/useSampleMutations';
import type { SampleFilters as Filters } from '../types/sample';

const PAGE_SIZE = 8;

export function SampleListPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<Filters>({});
  const [page, setPage] = useState(1);
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const { data: items = [], isLoading, isError } = useSamples(filters);
  const deleteMutation = useDeleteSample();

  const paginated = items.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const deleteTarget = items.find((i) => i.id === deleteTargetId);

  function handleDeleteConfirm() {
    if (!deleteTargetId) return;
    deleteMutation.mutate(deleteTargetId, {
      onSuccess: () => {
        setToast('Muestra eliminada correctamente');
        setDeleteTargetId(null);
      },
    });
  }

  return (
    <BiomedShell>
      <div className="page-header">
        <div>
          <h1><i className="fas fa-flask"></i> Gestión de Muestras</h1>
          <p>Administre todas las muestras del sistema (CRUD completo)</p>
        </div>
        <button type="button" className="btn-primary" onClick={() => navigate('/clinic/samples/new')}>
          <i className="fas fa-plus"></i> Nueva Muestra
        </button>
      </div>

      <SampleStats items={items} />

      <SampleFilters value={filters} onChange={(f) => { setFilters(f); setPage(1); }} />

      {isLoading && <Skeleton rows={5} />}
      {isError && <p role="alert">Error al cargar muestras. <button type="button" onClick={() => window.location.reload()}>Reintentar</button></p>}

      {!isLoading && !isError && (
        <>
          <SampleTable
            items={paginated}
            onEdit={(id) => navigate(`/clinic/samples/${id}/edit`)}
            onDelete={(id) => setDeleteTargetId(id)}
          />
          <SamplePagination page={page} pageSize={PAGE_SIZE} total={items.length} onPageChange={setPage} />
        </>
      )}

      {deleteTarget && (
        <SampleDeleteConfirm
          chnCode={deleteTarget.chn_code}
          onConfirm={handleDeleteConfirm}
          onCancel={() => setDeleteTargetId(null)}
          isDeleting={deleteMutation.isPending}
        />
      )}

      {toast && <Toast message={toast} kind="success" onDismiss={() => setToast(null)} />}
    </BiomedShell>
  );
}
