/**
 * SupervisorIscnPanel — nomenclatura ISCN + narrativa asistida (S3).
 *
 * Cierra el flujo del Supervisor: firma (S2) → ISCN (ADR-0025) → informe.
 * Solo se renderiza sobre casos SIGNED o REPORTED; el gating lo decide la página.
 *
 * Dos piezas con naturalezas distintas, y la UI lo hace explícito:
 *
 * - **El ISCN es el dato clínico.** Lo calcula una función pura determinística
 *   en el backend, nunca el LLM (ADR-0024 D1): `47,XY,+21` es un diagnóstico.
 *   Es read-only tras generarse (RN-04); cambiarlo exige un override justificado
 *   que queda auditado.
 * - **La narrativa es un BORRADOR.** La redacta el LLM sobre el ISCN ya
 *   calculado. Se marca como tal y requiere revisión humana (ADR-0024 D3). Si el
 *   modelo falla o alucina, se muestra el motivo y el informe sigue su curso
 *   (RN-07).
 */
import { useState } from 'react';
import { useGenerateIscn, useGenerateNarrative } from '../hooks/useAuditReview';
import { ClinicApiException } from '../types/sample';
import type { NarrativeResult } from '../types/karyotype';

const CONFIANZA_LABEL: Record<string, string> = {
  alta: '🟢 Confianza alta',
  media: '🟡 Confianza media',
  baja: '🟠 Confianza baja',
};

function OverrideForm({
  onSubmit, onCancel, busy,
}: { onSubmit: (iscn: string, motivo: string) => void; onCancel: () => void; busy: boolean }) {
  const [iscn, setIscn] = useState('');
  const [motivo, setMotivo] = useState('');
  // Sobrescribir un diagnóstico sin explicar por qué no es auditable (D4).
  const listo = iscn.trim().length > 0 && motivo.trim().length > 0;

  return (
    <div className="iscn-override" data-testid="iscn-override-form">
      <label htmlFor="iscn-override-input">Nomenclatura ISCN</label>
      <input
        id="iscn-override-input" type="text" value={iscn}
        onChange={(e) => setIscn(e.target.value)}
        placeholder="47,XY,+21"
        data-testid="iscn-override-input"
      />
      <label htmlFor="iscn-override-motivo">Justificación (obligatoria)</label>
      <textarea
        id="iscn-override-motivo" value={motivo} rows={2}
        onChange={(e) => setMotivo(e.target.value)}
        placeholder="Por qué corrige la nomenclatura calculada"
        data-testid="iscn-override-motivo"
      />
      <div className="iscn-override__actions">
        <button
          type="button" className="btn-primary" disabled={!listo || busy}
          onClick={() => onSubmit(iscn.trim(), motivo.trim())}
          title={listo ? '' : 'Complete la nomenclatura y su justificación'}
          data-testid="btn-iscn-override-submit"
        >Sobrescribir ISCN</button>
        <button type="button" className="btn-outline" onClick={onCancel} disabled={busy}
          data-testid="btn-iscn-override-cancel">Cancelar</button>
      </div>
    </div>
  );
}

function NarrativeBlock({ result }: { result: NarrativeResult }) {
  if (!result.generated) {
    return (
      <p className="iscn-panel__degraded" role="status" data-testid="narrative-degraded">
        ⚠️ Sin borrador narrativo ({result.reason}). El informe se emite igual —
        la redacción asistida nunca lo bloquea.
      </p>
    );
  }

  const est = result.structured;
  return (
    <div className="iscn-narrative" data-testid="narrative-block">
      <p className="iscn-narrative__draft-warning" role="status" data-testid="narrative-draft-warning">
        ✍️ <strong>Borrador asistido por IA.</strong> Requiere su revisión antes
        de incorporarse al informe.
      </p>

      {est && (
        <ul className="iscn-narrative__meta" data-testid="narrative-meta">
          <li data-testid="narrative-normal">
            {est.es_normal ? '✅ Cariotipo normal' : '⚠️ Con alteraciones'}
          </li>
          {est.anomalias_citadas.length > 0 && (
            <li data-testid="narrative-anomalias">
              Anomalías citadas: {est.anomalias_citadas.join(', ')}
            </li>
          )}
          <li data-testid="narrative-confianza">
            {CONFIANZA_LABEL[est.nivel_confianza] ?? est.nivel_confianza}
          </li>
        </ul>
      )}

      {est ? (
        <>
          <p className="iscn-narrative__hallazgo" data-testid="narrative-hallazgo">{est.hallazgo}</p>
          <p className="iscn-narrative__interpretacion" data-testid="narrative-interpretacion">
            {est.interpretacion}
          </p>
        </>
      ) : (
        <p data-testid="narrative-text">{result.narrative_draft}</p>
      )}

      {result.model && (
        <p className="iscn-narrative__model" data-testid="narrative-model">
          Redactado por <code>{result.model}</code> sobre el ISCN {result.iscn_input}.
        </p>
      )}
    </div>
  );
}

export function SupervisorIscnPanel({
  sampleId, iscn = '', status,
}: { sampleId: string; iscn?: string; status: string }) {
  const generarIscn = useGenerateIscn(sampleId);
  const generarNarrativa = useGenerateNarrative(sampleId);
  const [mostrarOverride, setMostrarOverride] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [narrativa, setNarrativa] = useState<NarrativeResult | null>(null);

  const reportado = status === 'REPORTED';
  const iscnActual = generarIscn.data?.iscn_nomenclature || iscn;
  const esOverride = generarIscn.data?.is_override ?? false;

  async function ejecutar(override = '', justificacion = '') {
    setError(null);
    try {
      await generarIscn.mutateAsync({ override, justification: justificacion });
      setMostrarOverride(false);
    } catch (err) {
      setError(err instanceof ClinicApiException ? err.message : 'No se pudo generar el ISCN');
    }
  }

  async function redactar() {
    setError(null);
    try {
      setNarrativa(await generarNarrativa.mutateAsync(iscnActual));
    } catch (err) {
      setError(err instanceof ClinicApiException ? err.message : 'No se pudo generar la narrativa');
    }
  }

  return (
    <section className="iscn-panel" data-testid="iscn-panel">
      <div className="iscn-panel__header">
        <strong>🧬 Nomenclatura ISCN</strong>
        {reportado && <span className="iscn-panel__state" data-testid="iscn-reported">Reportado</span>}
      </div>

      {iscnActual ? (
        <>
          <p className="iscn-panel__value" data-testid="iscn-value">
            <code>{iscnActual}</code>
            {esOverride && <span className="iscn-panel__override-tag" data-testid="iscn-override-tag">override</span>}
          </p>
          <p className="iscn-panel__readonly" data-testid="iscn-readonly-hint">
            🔒 Read-only tras generarse (RN-04). Para corregirla se requiere un
            override justificado, que queda auditado.
          </p>
        </>
      ) : (
        <p className="iscn-panel__hint" data-testid="iscn-pending-hint">
          El caso está firmado. Genere la nomenclatura para emitir el informe.
        </p>
      )}

      {error && <p className="iscn-panel__error" role="alert" data-testid="iscn-error">{error}</p>}

      <div className="karyo-gating">
        {!iscnActual && (
          <button
            type="button" className="btn-primary"
            disabled={generarIscn.isPending}
            onClick={() => ejecutar()}
            data-testid="btn-generate-iscn"
          >{generarIscn.isPending ? 'Generando…' : '🧬 Generar ISCN'}</button>
        )}

        {iscnActual && !mostrarOverride && (
          <button
            type="button" className="btn-outline"
            onClick={() => { setError(null); setMostrarOverride(true); }}
            data-testid="btn-show-iscn-override"
          >Corregir ISCN</button>
        )}

        {iscnActual && (
          <button
            type="button" className="btn-outline"
            disabled={generarNarrativa.isPending}
            onClick={redactar}
            title="La redacta un modelo local sobre el ISCN ya calculado"
            data-testid="btn-generate-narrative"
          >{generarNarrativa.isPending ? 'Redactando…' : '✍️ Generar borrador narrativo'}</button>
        )}
      </div>

      {mostrarOverride && (
        <OverrideForm
          onSubmit={(v, m) => ejecutar(v, m)}
          onCancel={() => setMostrarOverride(false)}
          busy={generarIscn.isPending}
        />
      )}

      {generarNarrativa.isPending && (
        <p className="iscn-panel__hint" role="status" data-testid="narrative-loading">
          Redactando con el modelo local… puede tardar 1-3 minutos.
        </p>
      )}

      {narrativa && <NarrativeBlock result={narrativa} />}
    </section>
  );
}
