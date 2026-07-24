/**
 * SupervisorAuditPanel — auditoría del 5% del Supervisor (S1, DD-SUP-001).
 *
 * Muestra los cromosomas seleccionados (badge púrpura "Auditoría requerida"),
 * permite Confirmar/Rechazar cada uno con comentario, y un contador de avance.
 * Solo se renderiza para rol supervisor/admin sobre casos ANALYST_VALIDATED
 * (el gating lo decide la página).
 */
import { useState } from 'react';
import { useAuditDecide, useAuditReview } from '../hooks/useAuditReview';
import { confidencePercent } from '../types/karyotype';
import type { AuditReview } from '../types/karyotype';

const DECISION_LABEL: Record<string, string> = {
  PENDING: 'Pendiente',
  CONFIRMED: '✓ Confirmado',
  REJECTED: '✗ Rechazado',
};

function ReviewRow({ review, sampleId }: { review: AuditReview; sampleId: string }) {
  const decide = useAuditDecide(sampleId);
  const [comment, setComment] = useState('');
  const decided = review.decision !== 'PENDING';

  return (
    <li className={`audit-row audit-row--${review.decision.toLowerCase()}`} data-testid={`audit-row-${review.chromosome}`}>
      <div className="audit-row__head">
        <span className="audit-badge" data-testid="audit-badge">🔬 Par {review.predicted_class}</span>
        <span className="audit-row__conf">{confidencePercent(review.confidence_score)}</span>
        <span className="audit-row__state" data-testid={`audit-state-${review.chromosome}`}>{DECISION_LABEL[review.decision]}</span>
      </div>
      {!decided && (
        <div className="audit-row__actions">
          <input
            type="text"
            placeholder="Comentario (opcional)"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            data-testid={`audit-comment-${review.chromosome}`}
            aria-label={`Comentario para par ${review.predicted_class}`}
          />
          <button
            type="button" className="btn-primary" disabled={decide.isPending}
            onClick={() => decide.mutate({ chromosomeId: review.chromosome, decision: 'CONFIRMED', comment })}
            data-testid={`audit-confirm-${review.chromosome}`}
          >Confirmar</button>
          <button
            type="button" className="btn-outline" disabled={decide.isPending}
            onClick={() => decide.mutate({ chromosomeId: review.chromosome, decision: 'REJECTED', comment })}
            data-testid={`audit-reject-${review.chromosome}`}
          >Rechazar</button>
        </div>
      )}
      {review.comment && <p className="audit-row__comment">“{review.comment}”</p>}
    </li>
  );
}

export function SupervisorAuditPanel({ sampleId }: { sampleId: string }) {
  const { data, isLoading, isError } = useAuditReview(sampleId, true);

  if (isLoading) return <div className="audit-panel" data-testid="audit-panel"><p>Cargando auditoría…</p></div>;
  if (isError || !data) return <div className="audit-panel" data-testid="audit-panel"><p role="alert">No se pudo cargar la auditoría.</p></div>;

  const { summary, reviews } = data;

  return (
    <section className="audit-panel" data-testid="audit-panel">
      <div className="audit-panel__header">
        <strong>🟣 Auditoría de calidad (5% aleatorio)</strong>
        <span data-testid="audit-progress">
          {summary.total - summary.pending}/{summary.total} revisados
        </span>
      </div>
      {summary.pending > 0 ? (
        <p className="audit-panel__hint" data-testid="audit-pending-hint">
          Debe revisar {summary.pending} cromosoma(s) de auditoría antes de firmar el reporte (FSD-UC-005).
        </p>
      ) : (
        <p className="audit-panel__ok" data-testid="audit-complete">✅ Auditoría del 5% completa.</p>
      )}
      <ul className="audit-panel__list">
        {reviews.map((r) => <ReviewRow key={r.id} review={r} sampleId={sampleId} />)}
      </ul>
    </section>
  );
}
