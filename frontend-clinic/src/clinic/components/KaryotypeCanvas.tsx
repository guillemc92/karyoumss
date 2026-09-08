/**
 * KaryotypeCanvas — cariograma interactivo sobre Konva.js (ADR-0021 P3, D4;
 * DD-KARYO-003). Reemplaza el grid SVG read-only de P1 por un lienzo con
 * **drag & drop de reclasificación**: arrastrar un cromosoma a otro slot lo
 * reclasifica (la geometría del drop la resuelve `karyoLayout`, puro).
 *
 * Las correcciones morfológicas (separar/unir/cruce) se disparan desde el
 * panel de propiedades (DOM), no desde el canvas — más accesible y robusto.
 *
 * Conserva los `data-testid` `karyotype-viewer` y `chromosome-{id}` de P1/P2.
 * react-konva se mockea en tests (jsdom no tiene canvas); la interacción real
 * se valida en E2E.
 */
import { useState } from 'react';
import { Circle, Group, Layer, Line, Rect, Stage, Text } from 'react-konva';
import type { Chromosome } from '../types/karyotype';
import { CHROMOSOME_SLOTS } from '../types/karyotype';
import {
  CHROMO_W,
  SLOT_H,
  SLOT_W,
  STAGE_HEIGHT,
  STAGE_WIDTH,
  chromosomePosition,
  reclassifyTargetFromDrop,
  slotOrigin,
} from '../lib/karyoLayout';
import type { ViewportState } from '../lib/viewport';
import { INITIAL_VIEWPORT, cssFilter, stageScale } from '../lib/viewport';
import type { Punto } from '../lib/medicion';
import { esRecorteUtil, rectanguloDeRecorte } from '../lib/recorte';

const SEMAPHORE_FILL: Record<string, string> = {
  green: '#1e8868',
  orange: '#d45100',
  red: '#E30613',
};

const CHROMO_BODY_W = 22;
const CHROMO_BODY_H = 100;

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
   * Modo recorte: arrastrar dibuja el nuevo límite del cromosoma seleccionado.
   * Al soltar se envía; el servidor reclasifica con el recorte nuevo.
   */
  cropMode?: boolean;
  onCropDone?: (bbox: { x: number; y: number; w: number; h: number }) => void;
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
  cropMode = false,
  onCropDone,
}: KaryotypeCanvasProps) {
  // Rectángulo en curso. Vive aquí y no en la página porque solo importa
  // mientras se arrastra: al soltar se emite el bbox y se olvida.
  const [cropInicio, setCropInicio] = useState<Punto | null>(null);
  const [cropActual, setCropActual] = useState<Punto | null>(null);
  const active = chromosomes.filter((c) => c.is_active);
  // En modo "Mover" el lienzo se arrastra y los cromosomas NO (evita el
  // conflicto con el drag de reclasificación).
  // Midiendo, nada se arrastra: un clic marca un punto, no mueve un cromosoma.
  const chromoDraggable = editable && !viewport.panMode && !measureMode && !cropMode;

  // El clic llega en coordenadas de pantalla; las medidas y los recortes se
  // calculan sobre las del lienzo. Sin deshacer zoom, rotación y offset, medir
  // con la vista ampliada daría longitudes distintas del mismo cromosoma, y un
  // recorte hecho con zoom recortaría una región que no es la que se ve.
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

  const handleCropStart = (e: { target: { getStage: () => unknown } }) => {
    if (!cropMode) return;
    const punto = puntoEnLienzo(e);
    if (!punto) return;
    setCropInicio(punto);
    setCropActual(punto);
  };

  const handleCropMove = (e: { target: { getStage: () => unknown } }) => {
    if (!cropMode || !cropInicio) return;
    const punto = puntoEnLienzo(e);
    if (punto) setCropActual(punto);
  };

  // Se emite al soltar, no en cada movimiento: el recorte dispara una
  // reclasificación en el servidor y no tiene sentido pedirla por cada píxel.
  const handleCropEnd = () => {
    if (!cropMode || !cropInicio || !cropActual) return;
    const rect = rectanguloDeRecorte(cropInicio, cropActual);
    setCropInicio(null);
    setCropActual(null);
    // Un clic sin arrastre no es un recorte: sería un bbox degenerado que el
    // servidor rechazaría (w o h nulos).
    if (!esRecorteUtil(rect)) return;
    onCropDone?.(rect);
  };

  const recorteEnCurso =
    cropInicio && cropActual ? rectanguloDeRecorte(cropInicio, cropActual) : null;

  return (
    <div className="karyo-canvas" data-testid="karyotype-viewer" style={{ filter: cssFilter(viewport) }}>
      <Stage
        width={STAGE_WIDTH}
        height={STAGE_HEIGHT}
        scaleX={stageScale(viewport).x}
        scaleY={stageScale(viewport).y}
        rotation={viewport.rotation}
        x={viewport.offsetX}
        y={viewport.offsetY}
        draggable={viewport.panMode}
        onDragEnd={viewport.panMode && onPan ? (e) => onPan(e.target.x(), e.target.y()) : undefined}
        onClick={measureMode ? handleStageClick : undefined}
        onMouseDown={cropMode ? handleCropStart : undefined}
        onMouseMove={cropMode ? handleCropMove : undefined}
        onMouseUp={cropMode ? handleCropEnd : undefined}
        // Soltar fuera del lienzo cancelaría el arrastre dejando el rectángulo
        // pegado al cursor para siempre.
        onMouseLeave={cropMode ? handleCropEnd : undefined}
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

          {active.map((chromo) => {
            const pos = chromosomePosition(chromo);
            const selected = chromo.id === selectedId;
            const picked = chromo.id === joinPickId;
            const stroke = picked ? '#7b2cbf' : selected ? '#0b7285' : '#1b3a4b';
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
                        e.target.position(chromosomePosition(chromo)); // snap-back; el refetch mueve el nodo
                        if (target && onReclassify) onReclassify(chromo, target);
                      }
                    : undefined
                }
              >
                <Rect
                  x={2}
                  y={10}
                  width={CHROMO_BODY_W}
                  height={CHROMO_BODY_H}
                  cornerRadius={7}
                  fill={SEMAPHORE_FILL[chromo.semaphore]}
                  stroke={stroke}
                  strokeWidth={selected || picked ? 3 : 1}
                  dash={chromo.is_anomaly ? [6, 4] : undefined}
                  opacity={chromo.resolution_status === 'RESOLVED' ? 0.6 : 1}
                />
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
          {/* Recorte en curso: se dibuja mientras se arrastra y desaparece al
              soltar. Sin relleno para no tapar el cromosoma que se recorta. */}
          {recorteEnCurso && (
            <Rect
              data-testid="recorte-rect"
              x={recorteEnCurso.x}
              y={recorteEnCurso.y}
              width={recorteEnCurso.w}
              height={recorteEnCurso.h}
              stroke="#0b7285"
              strokeWidth={2}
              dash={[6, 4]}
              fillEnabled={false}
              listening={false}
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
