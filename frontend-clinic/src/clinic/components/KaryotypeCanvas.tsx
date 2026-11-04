/**
 * KaryotypeCanvas — cariograma interactivo sobre Konva.js (ADR-0021 P3, D4;
 * DD-KARYO-003). Reemplaza el grid SVG read-only de P1 por un lienzo con
 * **drag & drop de reclasificación**: arrastrar un cromosoma a otro slot lo
 * reclasifica (la geometría del drop la resuelve `karyoLayout`, puro).
 *
 * Las correcciones morfológicas (separar/unir/cruce) se disparan desde el
 * panel de propiedades (DOM), no desde el canvas — más accesible y robusto.
 *
 * DD-KARYO-007 T7: todos los recortes a una ESCALA COMÚN y apoyados en la
 * línea base del hueco, para que el tamaño relativo de los pares se vea; cada
 * uno con su orientación (girar 180° / voltear, D7); y el lienzo crece hasta el
 * ancho del panel. La geometría es `lib/presentacionCariograma.ts`.
 *
 * Conserva los `data-testid` `karyotype-viewer` y `chromosome-{id}` de P1/P2.
 * react-konva se mockea en tests (jsdom no tiene canvas); la interacción real
 * se valida en E2E.
 */
import { useEffect, useRef, useState } from 'react';
import { Circle, Group, Image as KonvaImage, Layer, Line, Rect, Stage, Text } from 'react-konva';
import type { Chromosome } from '../types/karyotype';
import { CHROMOSOME_SLOTS } from '../types/karyotype';
import {
  CHROMO_W,
  SLOT_H,
  SLOT_W,
  STAGE_HEIGHT,
  STAGE_WIDTH,
  posicionesCariograma,
  reclassifyTargetFromDrop,
  slotOrigin,
} from '../lib/karyoLayout';
import type { ViewportState } from '../lib/viewport';
import { INITIAL_VIEWPORT, cssFilter, stageScale } from '../lib/viewport';
import type { Punto } from '../lib/medicion';
import { recorteValido, type Caja, type Dimensiones } from '../lib/encajarRecorte';
import {
  colocarEnLineaBase,
  colocarSilueta,
  dimensionesDePie,
  escalaComun,
  factorAjuste,
  marcoVisible,
  orientacionDe,
  siluetaDe,
  transformacionImagen,
  trazarSilueta,
  type Silueta,
  type TrazoCamino,
} from '../lib/presentacionCariograma';

const SEMAPHORE_FILL: Record<string, string> = {
  green: '#1e8868',
  orange: '#d45100',
  red: '#E30613',
};

const CHROMO_BODY_W = 22;
const CHROMO_BODY_H = 100;
/** Caja del cuerpo del cromosoma dentro de su grupo: ahí se encaja el recorte. */
const CUERPO: Caja = { x: 2, y: 10, w: CHROMO_BODY_W, h: CHROMO_BODY_H };

/** Tamaño real de la metafase. `naturalWidth` es el de los píxeles decodificados;
 * `width` cubre los dobles de los tests, que no decodifican. */
function tamanoDe(imagen: HTMLImageElement): { w: number; h: number } {
  return { w: imagen.naturalWidth || imagen.width, h: imagen.naturalHeight || imagen.height };
}

interface KaryotypeCanvasProps {
  chromosomes: Chromosome[];
  selectedId: string | null;
  joinPickId?: string | null;
  /** false cuando el caso ya fue validado → sin arrastre (case-lock). */
  editable?: boolean;
  /** Herramientas de imagen (P4): zoom/rotación/offset/brillo/contraste/pan. */
  viewport?: ViewportState;
  onSelect: (chromosome: Chromosome) => void;
  onReclassify?: (chromosome: Chromosome, targetClass: string) => void;
  /** Nuevo offset del lienzo tras un arrastre en modo "Mover" (P4). */
  onPan?: (offsetX: number, offsetY: number) => void;
  /**
   * Modo medición: los clics marcan puntos en vez de seleccionar cromosomas.
   * Se necesitan tres —extremo p, centrómero, extremo q— porque el índice
   * centromérico exige saber dónde está la constricción, no solo los extremos.
   */
  measureMode?: boolean;
  measurePoints?: Punto[];
  onMeasureClick?: (punto: Punto) => void;
  /**
   * Metafase del cariotipo (DD-KARYO-006). Con ella cada cromosoma se pinta
   * recortado de la imagen real; sin ella —o si su `bbox` no es válido— se
   * pinta el rectángulo de color de siempre (degradación, RN-07).
   */
  metafase?: HTMLImageElement | null;
}

export function KaryotypeCanvas({
  chromosomes,
  selectedId,
  joinPickId = null,
  editable = true,
  viewport = INITIAL_VIEWPORT,
  onSelect,
  onReclassify,
  onPan,
  measureMode = false,
  measurePoints = [],
  onMeasureClick,
  metafase = null,
}: KaryotypeCanvasProps) {
  const active = chromosomes.filter((c) => c.is_active);

  // T7: el lienzo crece hasta el ancho del panel. Sin ResizeObserver (jsdom) o
  // sin ancho medido, se queda en su tamaño de siempre.
  const contenedor = useRef<HTMLDivElement>(null);
  const [anchoDisponible, setAnchoDisponible] = useState(0);
  useEffect(() => {
    const el = contenedor.current;
    if (!el || typeof ResizeObserver === 'undefined') return undefined;
    const obs = new ResizeObserver(([entrada]) => setAnchoDisponible(entrada.contentRect.width));
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  const ajuste = factorAjuste(anchoDisponible, STAGE_WIDTH);

  // DD-KARYO-008: el que tiene silueta se recorta por ella y se endereza.
  const siluetas = new Map<string, Silueta>();
  // T7: la misma escala para todos los recortes (percentil 90 del largo). Con
  // silueta cuenta lo que mide de pie: la caja de uno en diagonal es más corta.
  const medidasDePie: Dimensiones[] = [];
  if (metafase) {
    for (const c of active) {
      if (!recorteValido(c.bbox as Partial<Caja>, tamanoDe(metafase))) continue;
      const s = siluetaDe(c.contour, c.bbox as Caja);
      if (s) siluetas.set(c.id, s);
      medidasDePie.push(s ? dimensionesDePie(s) : (c.bbox as Caja));
    }
  }
  const escala = escalaComun(medidasDePie, CUERPO);
  // T7: las copias de un par se quedan en su hueco aunque haya muchas.
  const posiciones = posicionesCariograma(active);
  // En modo "Mover" el lienzo se arrastra y los cromosomas NO (evita el
  // conflicto con el drag de reclasificación).
  // Midiendo, nada se arrastra: un clic marca un punto, no mueve un cromosoma.
  const chromoDraggable = editable && !viewport.panMode && !measureMode;

  // El clic llega en coordenadas de pantalla; las medidas se calculan sobre
  // las del lienzo. Sin deshacer zoom, rotación y offset, medir con la vista
  // ampliada daría longitudes distintas del mismo cromosoma.
  const puntoEnLienzo = (e: { target: { getStage: () => unknown } }): Punto | null => {
    const stage = e.target.getStage() as {
      getPointerPosition: () => { x: number; y: number } | null;
      getAbsoluteTransform: () => { copy: () => { invert: () => { point: (p: Punto) => Punto } } };
    } | null;
    const pos = stage?.getPointerPosition();
    if (!stage || !pos) return null;
    return stage.getAbsoluteTransform().copy().invert().point(pos);
  };

  const handleStageClick = (e: { target: { getStage: () => unknown } }) => {
    if (!measureMode || !onMeasureClick) return;
    const punto = puntoEnLienzo(e);
    if (punto) onMeasureClick(punto);
  };

  return (
    <div ref={contenedor} className="karyo-canvas" data-testid="karyotype-viewer" style={{ filter: cssFilter(viewport) }}>
      <Stage
        width={STAGE_WIDTH * ajuste}
        height={STAGE_HEIGHT * ajuste}
        scaleX={stageScale(viewport).x * ajuste}
        scaleY={stageScale(viewport).y * ajuste}
        rotation={viewport.rotation}
        x={viewport.offsetX}
        y={viewport.offsetY}
        draggable={viewport.panMode}
        onDragEnd={viewport.panMode && onPan ? (e) => onPan(e.target.x(), e.target.y()) : undefined}
        onClick={measureMode ? handleStageClick : undefined}
        data-testid="karyo-stage"
      >
        <Layer>
          {/* Etiquetas de cada slot (1..22, X, Y). */}
          {CHROMOSOME_SLOTS.map((slot) => {
            const o = slotOrigin(slot);
            if (!o) return null;
            return (
              <Text
                key={`label-${slot}`}
                data-testid={`slot-label-${slot}`}
                text={slot}
                x={o.x}
                y={o.y + SLOT_H - 20}
                width={SLOT_W - CHROMO_W}
                align="center"
                fontSize={13}
                fill="#5a7688"
              />
            );
          })}

          {/* De izquierda a derecha: cada copia queda encima de la anterior y la
              última de un par comprimido se ve entera. */}
          {[...active]
            .sort((a, b) => (posiciones.get(a.id)?.x ?? 0) - (posiciones.get(b.id)?.x ?? 0))
            .map((chromo) => {
            const pos = posiciones.get(chromo.id) ?? { x: 0, y: 0 };
            const selected = chromo.id === selectedId;
            const picked = chromo.id === joinPickId;
            const stroke = picked ? '#7b2cbf' : selected ? '#0b7285' : '#1b3a4b';
            // DD-KARYO-006: el recorte real, si hay metafase y el bbox cabe en ella.
            const recorte: Caja | null =
              metafase && recorteValido(chromo.bbox as Partial<Caja>, tamanoDe(metafase))
                ? (chromo.bbox as Caja)
                : null;
            // D8: los tumbados se giran 90° para mostrarlos de pie. T7: a la
            // escala común y sobre la línea base, con su orientación (D7).
            const orientacion = orientacionDe(chromo.measures);
            const silueta = siluetas.get(chromo.id) ?? null;
            const enSilueta = silueta && escala ? colocarSilueta(silueta, orientacion, CUERPO, escala) : null;
            const colocacion = recorte && escala && !enSilueta ? colocarEnLineaBase(recorte, CUERPO, escala) : null;
            const transformacion = colocacion ? transformacionImagen(colocacion, orientacion) : null;
            const marco = enSilueta ? enSilueta.marco : colocacion ? marcoVisible(colocacion, CUERPO) : null;
            const dataOrientacion = `${orientacion.giro}${orientacion.volteo ? '-v' : ''}`;
            return (
              <Group
                key={chromo.id}
                data-testid={`chromosome-${chromo.id}`}
                data-semaphore={chromo.semaphore}
                aria-label={`Cromosoma ${chromo.predicted_class}`}
                x={pos.x}
                y={pos.y}
                draggable={chromoDraggable}
                onClick={() => onSelect(chromo)}
                onTap={() => onSelect(chromo)}
                onDragEnd={
                  chromoDraggable
                    ? (e) => {
                        const target = reclassifyTargetFromDrop(e.target.x(), e.target.y(), chromo);
                        e.target.position(pos); // snap-back; el refetch mueve el nodo
                        if (target && onReclassify) onReclassify(chromo, target);
                      }
                    : undefined
                }
              >
                {recorte && marco && (enSilueta || (colocacion && transformacion)) ? (
                  <>
                    {/* El hueco entero sigue siendo donde se pulsa y se arrastra
                        (transparente), aunque el cromosoma ocupe solo una parte. */}
                    <Rect x={CUERPO.x} y={CUERPO.y} width={CUERPO.w} height={CUERPO.h} fill="rgba(0,0,0,0)" />
                    {/* Fondo claro solo detrás de la imagen (T7). */}
                    <Rect x={marco.x} y={marco.y} width={marco.w} height={marco.h} fill="#f4f6f7" listening={false} />
                    {enSilueta && silueta ? (
                      // DD-KARYO-008: recortado por la silueta (D1), de pie por su
                      // eje (D2). El grupo gira alrededor del centro de la silueta.
                      <Group
                        data-testid={`chromosome-silueta-${chromo.id}`}
                        data-giro-final={Math.round(enSilueta.giroFinal)}
                        data-enderezado={String(silueta.enderezado)}
                        x={enSilueta.x}
                        y={enSilueta.y}
                        rotation={enSilueta.rotation}
                        scaleX={enSilueta.scaleX}
                        scaleY={enSilueta.scaleY}
                        clipFunc={(ctx: TrazoCamino) => trazarSilueta(ctx, silueta)}
                        listening={false}
                      >
                        <KonvaImage
                          data-testid={`chromosome-img-${chromo.id}`}
                          image={metafase as HTMLImageElement}
                          crop={{ x: recorte.x, y: recorte.y, width: recorte.w, height: recorte.h }}
                          x={recorte.x - silueta.eje.centro.x}
                          y={recorte.y - silueta.eje.centro.y}
                          width={recorte.w}
                          height={recorte.h}
                          data-orientacion={dataOrientacion}
                        />
                      </Group>
                    ) : (
                      // Sin silueta: el recorte por la caja de siempre (RN-07).
                      // La condición de fuera garantiza colocación y transformación.
                      <KonvaImage
                        data-testid={`chromosome-img-${chromo.id}`}
                        image={metafase as HTMLImageElement}
                        crop={{ x: recorte.x, y: recorte.y, width: recorte.w, height: recorte.h }}
                        x={colocacion!.cx}
                        y={colocacion!.cy}
                        width={colocacion!.w}
                        height={colocacion!.h}
                        offsetX={colocacion!.w / 2}
                        offsetY={colocacion!.h / 2}
                        rotation={transformacion!.rotation}
                        scaleX={transformacion!.scaleX}
                        scaleY={transformacion!.scaleY}
                        data-orientacion={dataOrientacion}
                      />
                    )}
                    {/* Con la imagen a la vista el semáforo ya no puede ser el
                        relleno: pasa a ser el borde. La selección, otro borde
                        por fuera, para que las dos señales no se pisen. */}
                    <Rect
                      data-testid={`chromosome-frame-${chromo.id}`}
                      x={marco.x}
                      y={marco.y}
                      width={marco.w}
                      height={marco.h}
                      cornerRadius={4}
                      stroke={SEMAPHORE_FILL[chromo.semaphore]}
                      strokeWidth={2}
                      dash={chromo.is_anomaly ? [6, 4] : undefined}
                      opacity={chromo.resolution_status === 'RESOLVED' ? 0.6 : 1}
                      listening={false}
                    />
                    {(selected || picked) && (
                      <Rect
                        x={marco.x - 2}
                        y={marco.y - 2}
                        width={marco.w + 4}
                        height={marco.h + 4}
                        cornerRadius={6}
                        stroke={stroke}
                        strokeWidth={3}
                        listening={false}
                      />
                    )}
                  </>
                ) : (
                  <Rect
                    x={CUERPO.x}
                    y={CUERPO.y}
                    width={CUERPO.w}
                    height={CUERPO.h}
                    cornerRadius={7}
                    fill={SEMAPHORE_FILL[chromo.semaphore]}
                    stroke={stroke}
                    strokeWidth={selected || picked ? 3 : 1}
                    dash={chromo.is_anomaly ? [6, 4] : undefined}
                    opacity={chromo.resolution_status === 'RESOLVED' ? 0.6 : 1}
                  />
                )}
                <Text text={chromo.predicted_class} x={0} y={0} width={CHROMO_BODY_W + 4} align="center" fontSize={11} fill="#1b3a4b" />
              </Group>
            );
          })}

          {/* Medición: los dos segmentos son los brazos p y q. Se dibujan de
              colores distintos porque el índice centromérico depende de cuál es
              cuál, y confundirlos cambia la morfología. */}
          {measurePoints.length >= 2 && (
            <Line
              data-testid="medicion-brazo-p"
              points={[measurePoints[0].x, measurePoints[0].y, measurePoints[1].x, measurePoints[1].y]}
              stroke="#0b7285"
              strokeWidth={2}
            />
          )}
          {measurePoints.length >= 3 && (
            <Line
              data-testid="medicion-brazo-q"
              points={[measurePoints[1].x, measurePoints[1].y, measurePoints[2].x, measurePoints[2].y]}
              stroke="#7b2cbf"
              strokeWidth={2}
            />
          )}
          {measurePoints.map((p, i) => (
            <Circle
              key={`medicion-${i}`}
              data-testid={`medicion-punto-${i}`}
              x={p.x}
              y={p.y}
              radius={i === 1 ? 6 : 4}       // el centrómero, más grande
              fill={i === 1 ? '#d45100' : '#0b7285'}
              stroke="#fff"
              strokeWidth={1.5}
            />
          ))}
        </Layer>
      </Stage>
    </div>
  );
}
