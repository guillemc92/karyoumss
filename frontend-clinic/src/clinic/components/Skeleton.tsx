export function Skeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div role="status" aria-label="Cargando" className="skeleton-table">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="skeleton-row" />
      ))}
    </div>
  );
}
