/**
 * MetafasePanel — el recorte manual se dibuja sobre la metafase real
 * (DD-KARYO-006 D7).
 *
 * Muestra la región de la metafase alrededor del cromosoma seleccionado —su
 * caja más un margen—, ampliada, con el recorte actual en discontinuo. El
 * analista dibuja el nuevo límite y al soltar se envía en PÍXELES DE LA
 * METAFASE, que es lo que el servidor guarda en `Chromosome.bbox`.
 *
 * Sustituye al recorte dibujado sobre el cariograma, que enviaba las
 * coordenadas del hueco del cromosoma en vez de las de la imagen: reproducido
 * el 13/10, `{x: 9, y: 18, w: 22, h: 100}` para un cromosoma que estaba en
 * `{x: 448, y: 35, w: 175, h: 73}`. Aquí, además, se puede AGRANDAR un recorte
 * que se quedó corto, cosa imposible dibujando dentro de la caja de 22 × 100.
 */
import { useMemo, useState } from 'react';
import { Image as KonvaImage, Layer, Rect, Stage } from 'react-konva';
import type { Caja } from '../lib/encajarRecorte';
import type { Punto } from '../lib/medicion';
import { esRecorteUtil, rectanguloDeRecorte } from '../lib/recorte';
import { aMetafase, aPanel, escalaPanel, regionDeRecorte } from '../lib/recorteMetafase';

interface MetafasePanelProps {
  metafase: HTMLImageElement;
  /** Caja actual del cromosoma, en píxeles de la metafase. */
  bbox: Caja;
  onCropDone: (bbox: Caja) => void;
  onCancelar: () => void;
}

export function MetafasePanel({ metafase, bbox, onCropDone, onCancelar }: MetafasePanelProps) {
  const imagen = { w: metafase.naturalWidth || metafase.width, h: metafase.naturalHeight || metafase.height };
  const region = useMemo(() => regionDeRecorte(bbox, imagen), [bbox, imagen.w, imagen.h]); // eslint-disable-line react-hooks/exhaustive-deps
  const escala = escalaPanel(region);
  const actual = aPanel(bbox, region, escala);

  const [inicio, setInicio] = useState<Punto | null>(null);
  const [fin, setFin] = useState<Punto | null>(null);

  const punto = (e: { target: { getStage: () => unknown } }): Punto | null => {
    const stage = e.target.getStage() as { getPointerPosition: () => Punto | null } | null;
    return stage?.getPointerPosition() ?? null;
  };

  const empezar = (e: { target: { getStage: () => unknown } }) => {
    const p = punto(e);
    if (!p) return;
    setInicio(p);
    setFin(p);
  };
  const mover = (e: { target: { getStage: () => unknown } }) => {
    if (!inicio) return;
    const p = punto(e);
    if (p) setFin(p);
  };
  // Al soltar, no en cada movimiento: el recorte reclasifica en el servidor.
  const soltar = () => {
    if (!inicio || !fin) return;
    const rect = rectanguloDeRecorte(inicio, fin);
    setInicio(null);
    setFin(null);
    if (!esRecorteUtil(rect)) return;          // un clic suelto no es un recorte
    const enMetafase = aMetafase(rect, region, escala, imagen);
    if (enMetafase.w > 0 && enMetafase.h > 0) onCropDone(enMetafase);
  };

  const enCurso = inicio && fin ? rectanguloDeRecorte(inicio, fin) : null;

  return (
    <section className="metafase-panel" data-testid="metafase-panel" aria-label="Recorte sobre la metafase">
      <strong className="metafase-panel__titulo">Metafase</strong>
      <p className="metafase-panel__ayuda" data-testid="metafase-ayuda">
        Dibuje el nuevo límite del cromosoma sobre la metafase. El recuadro discontinuo es el
        recorte actual; puede hacerlo más pequeño o más grande.
      </p>
      <Stage
        data-testid="metafase-stage"
        width={region.w * escala}
        height={region.h * escala}
        onMouseDown={empezar}
        onMouseMove={mover}
        onMouseUp={soltar}
        // Soltar fuera del panel cancela: el rectángulo no se queda pegado al cursor.
        onMouseLeave={soltar}
      >
        <Layer>
          <KonvaImage
            data-testid="metafase-imagen"
            image={metafase}
            crop={{ x: region.x, y: region.y, width: region.w, height: region.h }}
            width={region.w * escala}
            height={region.h * escala}
          />
          <Rect
            data-testid="metafase-recorte-actual"
            x={actual.x}
            y={actual.y}
            width={actual.w}
            height={actual.h}
            stroke="#f2c94c"
            strokeWidth={2}
            dash={[6, 4]}
            listening={false}
          />
          {enCurso && (
            <Rect
              x={enCurso.x}
              y={enCurso.y}
              width={enCurso.w}
              height={enCurso.h}
              stroke="#d45100"
              strokeWidth={2}
              listening={false}
            />
          )}
        </Layer>
      </Stage>
      <button type="button" className="btn-outline" data-testid="metafase-cancelar" onClick={onCancelar}>
        Cancelar recorte
      </button>
    </section>
  );
}
