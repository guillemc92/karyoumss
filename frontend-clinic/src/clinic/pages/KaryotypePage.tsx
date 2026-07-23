/**
 * KaryotypePage — visor read-only del cariotipo (ADR-0021 P1, DD-KARYO-001).
 *
 * Ruta: /clinic/samples/:id/karyotype
 * P1: semaforización + panel de propiedades. Sin edición (P2/P3).
 */
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { BiomedShell } from '../components/BiomedShell';
import { Skeleton } from '../components/Skeleton';
import { KaryotypeViewer } from '../components/KaryotypeViewer';
import { ChromosomePropertiesPanel } from '../components/ChromosomePropertiesPanel';
import { useKaryotype } from '../hooks/useKaryotype';
import { ClinicApiException } from '../types/sample';
import type { Chromosome } from '../types/karyotype';

function SemaphoreLegend() {
  return (
    <div className="karyo-legend" data-testid="semaphore-legend">
      <span><span className="karyo-dot karyo-dot--green" /> Verde ≥ 85%</span>
      <span><span className="karyo-dot karyo-dot--orange" /> Naranja &lt; 85%</span>
      <span><span className="karyo-dot karyo-dot--red" /> Rojo (falla)</span>
    </div>
  );
}

export function KaryotypePage() {
  const { id } = useParams<{ id: string }>();
  const { data: karyotype, isLoading, isError, error } = useKaryotype(id);
  const [selected, setSelected] = useState<Chromosome | null>(null);

  if (isLoading) {
    return (
      <BiomedShell>
        <h1>Cariotipo</h1>
        <Skeleton rows={4} />
      </BiomedShell>
    );
  }

  if (isError || !karyotype) {
    const noKaryotype = error instanceof ClinicApiException && error.code === 'NO_KARYOTYPE';
    return (
      <BiomedShell>
        <h1>Cariotipo</h1>
        <p role="alert" data-testid="karyo-error">
          {noKaryotype
            ? 'Esta muestra aún no tiene un cariotipo generado. Procese la muestra con IA primero.'
            : 'No se pudo cargar el cariotipo.'}
        </p>
        <Link to={`/clinic/samples/${id}`}>← Volver a la muestra</Link>
      </BiomedShell>
    );
  }

  const { summary } = karyotype;

  return (
    <BiomedShell>
      <div className="karyo-header">
        <div>
          <h1>Clasificación de Cariotipo</h1>
          <p className="karyo-header__meta">
            {summary.total} cromosomas &middot; modelo {karyotype.model_version}
          </p>
        </div>
        <SemaphoreLegend />
      </div>

      {summary.unresolved_orange > 0 && (
        <div className="karyo-alert" role="alert" data-testid="karyo-review-banner">
          ⚠ <strong>{summary.unresolved_orange} cromosoma(s) requieren revisión</strong> (confianza &lt; 85%).
          La emisión del informe quedará bloqueada hasta resolverlos.
        </div>
      )}
      {summary.red > 0 && (
        <div className="karyo-alert karyo-alert--red" role="alert" data-testid="karyo-red-banner">
          ⛔ <strong>{summary.red} cromosoma(s) con clasificación fallida</strong> — requieren intervención manual.
        </div>
      )}

      <div className="karyo-workspace">
        <div className="karyo-workspace__viewer">
          <KaryotypeViewer
            chromosomes={karyotype.chromosomes}
            selectedId={selected?.id ?? null}
            onSelect={setSelected}
          />
        </div>
        <aside className="karyo-workspace__panel">
          <ChromosomePropertiesPanel chromosome={selected} />
        </aside>
      </div>

      <p className="karyo-footer">
        <Link to={`/clinic/samples/${id}`}>← Volver a la muestra</Link>
      </p>
    </BiomedShell>
  );
}
