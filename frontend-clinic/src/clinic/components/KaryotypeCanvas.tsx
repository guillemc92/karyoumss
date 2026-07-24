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
import { Group, Layer, Rect, Stage, Text } from 'react-konva';
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
import { INITIAL_VIEWPORT, cssFilter } from '../lib/viewport';

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
}: KaryotypeCanvasProps) {
  const active = chromosomes.filter((c) => c.is_active);
  // En modo "Mover" el lienzo se arrastra y los cromosomas NO (evita el
  // conflicto con el drag de reclasificación).
  const chromoDraggable = editable && !viewport.panMode;

  return (
    <div className="karyo-canvas" data-testid="karyotype-viewer" style={{ filter: cssFilter(viewport) }}>
      <Stage
        width={STAGE_WIDTH}
        height={STAGE_HEIGHT}
        scaleX={viewport.scale}
        scaleY={viewport.scale}
        rotation={viewport.rotation}
        x={viewport.offsetX}
        y={viewport.offsetY}
        draggable={viewport.panMode}
        onDragEnd={viewport.panMode && onPan ? (e) => onPan(e.target.x(), e.target.y()) : undefined}
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
        </Layer>
      </Stage>
    </div>
  );
}
