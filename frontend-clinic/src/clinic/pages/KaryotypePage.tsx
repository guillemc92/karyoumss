/**
 * KaryotypePage — visor de cariotipo (ADR-0021).
 * P1: semaforización read-only + panel de propiedades.
 * P2 (ADR-0021 P2, ADR-0022): XAI Grad-CAM, resolver naranjas con gate BR-004,
 * marcar anomalías, gating de "Pasar a Supervisor" (RN-01) y bitácora.
 * P3 (ADR-0021 P3, DD-KARYO-003): corrección manual sobre canvas Konva —
 * reclasificar (drag & drop o "Mover a par"), separar/unir/resolver cruce.
 *
 * Ruta: /clinic/samples/:id/karyotype
 */
import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { BiomedShell } from '../components/BiomedShell';
import { Skeleton } from '../components/Skeleton';
import { KaryotypeCanvas } from '../components/KaryotypeCanvas';
import { ChromosomePropertiesPanel } from '../components/ChromosomePropertiesPanel';
import { XaiModal } from '../components/XaiModal';
import { useKaryotype } from '../hooks/useKaryotype';
import { useAuditTrail, useKaryotypeActions } from '../hooks/useKaryotypeActions';
import { ClinicApiException } from '../types/sample';
import type { Chromosome, XaiResult } from '../types/karyotype';
import { AUDIT_LABELS } from '../types/karyotype';

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
  const [xaiOpen, setXaiOpen] = useState(false);
  const [xaiResult, setXaiResult] = useState<XaiResult | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [validated, setValidated] = useState(false);
  const [showAudit, setShowAudit] = useState(false);
  const [joinPick, setJoinPick] = useState<{ id: string; label: string } | null>(null);

  const { viewXai, resolve, markAnomaly, validate, reclassify, split, join, resolveCross } =
    useKaryotypeActions(id);
  const audit = useAuditTrail(id, showAudit);

  // Mantener el cromosoma seleccionado sincronizado tras un refetch.
  useEffect(() => {
    if (selected && karyotype) {
      const fresh = karyotype.chromosomes.find((c) => c.id === selected.id);
      if (fresh && fresh !== selected) setSelected(fresh);
    }
  }, [karyotype]); // eslint-disable-line react-hooks/exhaustive-deps

  if (isLoading) {
    return <BiomedShell><h1>Cariotipo</h1><Skeleton rows={4} /></BiomedShell>;
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
  const blocked = summary.unresolved_orange > 0 || summary.red > 0;
  const busy =
    viewXai.isPending || resolve.isPending || markAnomaly.isPending || validate.isPending ||
    reclassify.isPending || split.isPending || join.isPending || resolveCross.isPending;

  async function handleViewXai(c: Chromosome) {
    setActionError(null);
    setXaiOpen(true);
    setXaiResult(null);
    try {
      setXaiResult(await viewXai.mutateAsync(c.id));
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Error al obtener XAI');
    }
  }

  async function handleResolve(c: Chromosome) {
    setActionError(null);
    try {
      await resolve.mutateAsync(c.id);
    } catch (err) {
      setActionError(err instanceof ClinicApiException ? err.message : 'Error al resolver');
    }
  }

  async function handleAnomaly(c: Chromosome) {
    setActionError(null);
    try {
      await markAnomaly.mutateAsync(c.id);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Error al marcar anomalía');
    }
  }

  async function handleValidate() {
    setActionError(null);
    try {
      await validate.mutateAsync();
      setValidated(true);
    } catch (err) {
      setActionError(err instanceof ClinicApiException ? err.message : 'Error al validar');
    }
  }

  // --- P3: corrección manual (DD-KARYO-003) ---
  async function runP3<T>(label: string, fn: () => Promise<T>) {
    setActionError(null);
    try {
      await fn();
    } catch (err) {
      setActionError(err instanceof ClinicApiException ? err.message : label);
    }
  }

  function handleReclassify(c: Chromosome, targetClass: string) {
    if (targetClass === c.predicted_class) return;
    void runP3('Error al reclasificar', () => reclassify.mutateAsync({ chromosomeId: c.id, targetClass }));
  }

  function handleSplit(c: Chromosome) {
    void runP3('Error al separar', () => split.mutateAsync(c.id));
  }

  function handleResolveCross(c: Chromosome) {
    void runP3('Error al resolver cruce', () => resolveCross.mutateAsync(c.id));
  }

  function handleJoinPick(c: Chromosome) {
    setJoinPick((prev) => (prev?.id === c.id ? null : { id: c.id, label: c.predicted_class }));
  }

  async function handleJoinConfirm(c: Chromosome) {
    if (!joinPick) return;
    await runP3('Error al unir', () => join.mutateAsync({ keepId: joinPick.id, otherId: c.id }));
    setJoinPick(null);
  }

  return (
    <BiomedShell>
      <div className="karyo-header">
        <div>
          <h1>Clasificación de Cariotipo</h1>
          <p className="karyo-header__meta">{summary.total} cromosomas &middot; modelo {karyotype.model_version}</p>
        </div>
        <SemaphoreLegend />
      </div>

      {validated ? (
        <div className="karyo-alert karyo-alert--ok" role="status" data-testid="karyo-validated-banner">
          ✅ <strong>Caso validado por el analista.</strong> Listo para pasar a Supervisor.
        </div>
      ) : summary.unresolved_orange > 0 && (
        <div className="karyo-alert" role="alert" data-testid="karyo-review-banner">
          ⚠ <strong>{summary.unresolved_orange} cromosoma(s) requieren revisión</strong> (confianza &lt; 85%).
          La emisión del informe queda bloqueada hasta resolverlos (RN-01).
        </div>
      )}
      {summary.red > 0 && (
        <div className="karyo-alert karyo-alert--red" role="alert" data-testid="karyo-red-banner">
          ⛔ <strong>{summary.red} cromosoma(s) con clasificación fallida</strong> — requieren intervención manual.
        </div>
      )}
      {actionError && (
        <div className="karyo-alert karyo-alert--red" role="alert" data-testid="karyo-action-error">{actionError}</div>
      )}

      <div className="karyo-workspace">
        <div className="karyo-workspace__viewer">
          <KaryotypeCanvas
            chromosomes={karyotype.chromosomes}
            selectedId={selected?.id ?? null}
            joinPickId={joinPick?.id ?? null}
            editable={!validated}
            onSelect={setSelected}
            onReclassify={validated ? undefined : handleReclassify}
          />
        </div>
        <aside className="karyo-workspace__panel">
          <ChromosomePropertiesPanel
            chromosome={selected}
            onViewXai={validated ? undefined : handleViewXai}
            onResolve={validated ? undefined : handleResolve}
            onMarkAnomaly={validated ? undefined : handleAnomaly}
            busy={busy}
            onReclassify={validated ? undefined : handleReclassify}
            onSplit={validated ? undefined : handleSplit}
            onResolveCross={validated ? undefined : handleResolveCross}
            onJoinPick={validated ? undefined : handleJoinPick}
            onJoinConfirm={validated ? undefined : handleJoinConfirm}
            joinPick={joinPick}
          />
          <div className="karyo-gating">
            <button
              type="button"
              className="btn-primary"
              disabled={blocked || busy || validated}
              onClick={handleValidate}
              data-testid="btn-pass-supervisor"
              title={blocked ? `Resuelva ${summary.unresolved_orange} cromosoma(s) naranja antes de continuar` : ''}
            >
              Pasar a Supervisor →
            </button>
          </div>
        </aside>
      </div>

      <div className="karyo-audit">
        <button type="button" className="btn-outline" onClick={() => setShowAudit((v) => !v)} data-testid="toggle-audit">
          {showAudit ? 'Ocultar' : 'Ver'} bitácora de auditoría
        </button>
        {showAudit && (
          <ul className="karyo-audit__list" data-testid="audit-log">
            {audit.isLoading && <li>Cargando…</li>}
            {audit.data && audit.data.length === 0 && <li data-testid="audit-empty">Sin eventos todavía.</li>}
            {audit.data?.map((e) => (
              <li key={e.id}>
                <span className="karyo-audit__time">{new Date(e.created_at).toLocaleTimeString('es-BO')}</span>
                {' — '}{AUDIT_LABELS[e.event_type] ?? e.event_type}
                {e.actor_name && ` · ${e.actor_name}`}
              </li>
            ))}
          </ul>
        )}
      </div>

      {xaiOpen && selected && (
        <XaiModal
          chromosome={selected}
          xai={xaiResult}
          loading={viewXai.isPending}
          error={xaiOpen && actionError ? actionError : null}
          onClose={() => setXaiOpen(false)}
        />
      )}

      <p className="karyo-footer"><Link to={`/clinic/samples/${id}`}>← Volver a la muestra</Link></p>
    </BiomedShell>
  );
}
