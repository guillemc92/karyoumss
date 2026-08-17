/**
 * MedicionPanel — la regla del analista.
 *
 * Muestra las medidas con las que la citogenética clasifica un cromosoma:
 * longitud, índice centromérico y razón de brazos. Es la herramienta que usa
 * quien quiere discutirle al modelo la clase que propuso.
 *
 * Las medidas van en píxeles a propósito: no hay calibración a micras, así que
 * sirven para **comparar dentro de la misma metafase** —que es lo que hace
 * falta para decidir si un cromosoma está en el par correcto— y no como valor
 * absoluto para un informe. Se dice en pantalla para que nadie lo confunda.
 */
import type { Medida, Punto } from '../lib/medicion';
import { medirCromosoma } from '../lib/medicion';

interface Props {
  activo: boolean;
  puntos: Punto[];
  onActivar: () => void;
  onLimpiar: () => void;
}

const PASOS = ['extremo del brazo corto', 'centrómero', 'extremo del brazo largo'];

export function MedicionPanel({ activo, puntos, onActivar, onLimpiar }: Props) {
  const completa = puntos.length === 3;
  const medida: Medida | null = completa
    ? medirCromosoma(puntos[0], puntos[1], puntos[2])
    : null;

  return (
    <section className="medicion-panel" data-testid="medicion-panel">
      <header className="medicion-panel__head">
        <h3>Medición</h3>
        <button
          type="button"
          className={activo ? 'btn-primary' : 'btn-outline'}
          data-testid="medicion-toggle"
          aria-pressed={activo}
          onClick={onActivar}
        >
          {activo ? 'Midiendo…' : 'Medir'}
        </button>
      </header>

      {activo && !completa && (
        <p className="medicion-panel__hint" data-testid="medicion-instruccion">
          Marca el <strong>{PASOS[puntos.length]}</strong> ({puntos.length + 1} de 3)
        </p>
      )}

      {medida && (
        <>
          <dl className="medicion-panel__datos" data-testid="medicion-resultado">
            <div>
              <dt>Longitud total</dt>
              <dd data-testid="medicion-longitud">{medida.longitudTotal} px</dd>
            </div>
            <div>
              <dt>Brazo corto (p)</dt>
              <dd>{medida.brazoP} px</dd>
            </div>
            <div>
              <dt>Brazo largo (q)</dt>
              <dd>{medida.brazoQ} px</dd>
            </div>
            <div>
              {/* El criterio real: es una proporción, así que no le afecta el
                  grado de condensación de la preparación. */}
              <dt>Índice centromérico</dt>
              <dd data-testid="medicion-indice">
                <strong>{medida.indiceCentromerico}%</strong>
              </dd>
            </div>
            <div>
              <dt>Razón q/p</dt>
              <dd>{Number.isFinite(medida.razonBrazos) ? medida.razonBrazos.toFixed(2) : '∞'}</dd>
            </div>
            <div>
              <dt>Morfología</dt>
              <dd data-testid="medicion-morfologia">
                <strong>{medida.morfologia}</strong>
              </dd>
            </div>
          </dl>

          <p className="medicion-panel__nota">
            Medidas en píxeles, sin calibración a micras: sirven para comparar
            cromosomas de <em>esta</em> metafase, no como valor absoluto.
          </p>
        </>
      )}

      {puntos.length > 0 && (
        <button type="button" className="btn-outline" data-testid="medicion-limpiar" onClick={onLimpiar}>
          Limpiar
        </button>
      )}
    </section>
  );
}
