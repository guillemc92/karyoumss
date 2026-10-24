interface SamplePaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

export function SamplePagination({ page, pageSize, total, onPageChange }: SamplePaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  return (
    <div className="pagination">
      <span>Mostrando {start}-{end} de {total}</span>
      <div className="pagination-buttons">
        <button type="button" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>← Anterior</button>
        <span>{page} / {totalPages}</span>
        <button type="button" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>Siguiente →</button>
      </div>
    </div>
  );
}
