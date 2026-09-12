import type { SampleListItem } from '../types/sample';

interface SampleStatsProps {
  items: SampleListItem[];
}

export function SampleStats({ items }: SampleStatsProps) {
  const total = items.length;
  const processing = items.filter((i) => i.status === 'PROCESSING').length;
  const review = items.filter((i) => i.status === 'READY').length;
  const completed = items.filter((i) => i.status === 'VALIDATED').length;

  return (
    <div className="stats-row">
      <div className="stat-card">
        <div className="stat-icon"><i className="fas fa-chart-line"></i></div>
        <div className="stat-info"><h3>{total}</h3><p>Total muestras</p></div>
      </div>
      <div className="stat-card">
        <div className="stat-icon"><i className="fas fa-hourglass-half"></i></div>
        <div className="stat-info"><h3>{processing}</h3><p>En proceso</p></div>
      </div>
      <div className="stat-card">
        <div className="stat-icon warning"><i className="fas fa-exclamation-triangle"></i></div>
        <div className="stat-info"><h3>{review}</h3><p>Requieren revisión</p></div>
      </div>
      <div className="stat-card">
        <div className="stat-icon success"><i className="fas fa-check-circle"></i></div>
        <div className="stat-info"><h3>{completed}</h3><p>Completadas</p></div>
      </div>
    </div>
  );
}
