/**
 * MetafaseEditor — la metafase como lienzo principal (DD-KARYO-007 F1, T2).
 *
 * Pinta la metafase entera y encima la silueta de cada cromosoma, con el color
 * de su semáforo. Seleccionar aquí o en el cariograma es lo mismo: los dos leen
 * y escriben el mismo `selectedId` de la página.
 *
 * Es el sitio donde, en Ikaros y en MetaClass, se corrige la segmentación: en
 * el cariograma cada cromosoma está aislado y no se ve con qué se tocaba. T3
 * añade aquí descartar y añadir objetos; F2, el corte por línea.
 *
 * Coordenadas: el Stage lleva la escala total (ajuste × zoom) y el
 * desplazamiento. Imagen y contornos van en píxeles de la metafase, tal cual
 * los guarda el servidor, así que no hay conversión que pueda desalinearlos.
 */
import { useEffect, useState } from 'react';
import { Image as KonvaImage, Layer, Line, Stage, Text } from 'react-konva';
import type { Chromosome } from '../types/karyotype';
import type { Punto } from '../lib/medicion';
import {
  PASO_ZOOM,
  ZOOM_MAX,
  ZOOM_MIN,
  centrarEn,
  centroDe,
  escalaAjuste,
  limitarDesplazamiento,
  poligonoDe,
  puntosPlanos,
  zoomEnPunto,
} from '../lib/contornoMetafase';

const SEMAFORO: Record<string, string> = {
  green: '#1e8868',
  orange: '#d45100',
  red: '#E30613',
};
/** El mismo color, translúcido, para el relleno: deja ver las bandas debajo. */
const RELLENO: Record<string, string> = {
  green: 'rgba(30, 136, 104, 0.25)',
  orange: 'rgba(212, 81, 0, 0.25)',
  red: 'rgba(227, 6, 19, 0.25)',
};
const SELECCION = '#f2c94c';
const RELLENO_SELECCION = 'rgba(242, 201, 76, 0.35)';

/** Tamaño máximo del lienzo en pantalla. */
export const LIENZO_MAX = { w: 760, h: 560 };

interface MetafaseEditorProps {
  metafase: HTMLImageElement;
  chromosomes: Chromosome[];
  selectedId: string | null;
  onSelect: (c: Chromosome) => void;
}

interface EventoRueda {
  evt: { deltaY: number; preventDefault: () => void };
  target: { getStage: () => unknown };
}

export function MetafaseEditor({ metafase, chromosomes, selectedId, onSelect }: MetafaseEditorProps) {
  const imagen = { w: metafase.naturalWidth || metafase.width, h: metafase.naturalHeight || metafase.height };
  const ajuste = escalaAjuste(imagen, LIENZO_MAX);
  const lienzo = { w: Math.round(imagen.w * ajuste), h: Math.round(imagen.h * ajuste) };

  const [zoom, setZoom] = useState(ZOOM_MIN);
  const [pos, setPos] = useState<Punto>({ x: 0, y: 0 });
  const escala = ajuste * zoom;

  const objetos = chromosomes
    .filter((c) => c.is_active)
    .map((c) => ({ c, poligono: poligonoDe(c, imagen) }))
    .filter((o): o is { c: Chromosome; poligono: number[][] } => o.poligono !== null);

  // Seleccionar en el cariograma con zoom puesto trae el cromosoma a la vista.
  // Sin zoom no se mueve nada: `centrarEn` limita el desplazamiento a (0, 0).
  const seleccionado = objetos.find((o) => o.c.id === selectedId);
  useEffect(() => {
    if (!seleccionado) return;
    setPos(centrarEn(centroDe(seleccionado.poligono), escala, lienzo, zoom));
  }, [selectedId]); // eslint-disable-line react-hooks/exhaustive-deps

  const cambiarZoom = (nuevo: number, ancla: Punto) => {
    const z = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, nuevo));
    setPos(zoomEnPunto(pos, zoom, z, ancla, lienzo));
    setZoom(z);
  };
  const centro = { x: lienzo.w / 2, y: lienzo.h / 2 };

  const alGirarRueda = (e: EventoRueda) => {
    e.evt.preventDefault();
    const stage = e.target.getStage() as { getPointerPosition: () => Punto | null } | null;
    const ancla = stage?.getPointerPosition() ?? centro;
    cambiarZoom(e.evt.deltaY < 0 ? zoom * PASO_ZOOM : zoom / PASO_ZOOM, ancla);
  };

  return (
    <section className="metafase-editor" data-testid="metafase-editor" aria-label="Metafase">
      <div className="metafase-editor__barra">
        <strong>Metafase</strong>
        <span className="metafase-editor__cuenta" data-testid="metafase-cuenta">
          {objetos.length} objeto(s)
        </span>
        <button
          type="button"
          className="btn-outline"
          data-testid="metafase-alejar"
          disabled={zoom <= ZOOM_MIN}
          onClick={() => cambiarZoom(zoom / PASO_ZOOM, centro)}
          aria-label="Alejar"
        >
          −
        </button>
        <span data-testid="metafase-zoom">{Math.round(zoom * 100)}%</span>
        <button
          type="button"
          className="btn-outline"
          data-testid="metafase-acercar"
          disabled={zoom >= ZOOM_MAX}
          onClick={() => cambiarZoom(zoom * PASO_ZOOM, centro)}
          aria-label="Acercar"
        >
          +
        </button>
        <button
          type="button"
          className="btn-outline"
          data-testid="metafase-ajustar"
          disabled={zoom === ZOOM_MIN}
          onClick={() => {
            setZoom(ZOOM_MIN);
            setPos({ x: 0, y: 0 });
          }}
        >
          Ajustar
        </button>
      </div>
      <Stage
        data-testid="metafase-editor-stage"
        width={lienzo.w}
        height={lienzo.h}
        scaleX={escala}
        scaleY={escala}
        x={pos.x}
        y={pos.y}
        // Sin zoom no hay nada que desplazar, y arrastrar movería la imagen fuera.
        draggable={zoom > ZOOM_MIN}
        dragBoundFunc={(p: Punto) => limitarDesplazamiento(p, lienzo, zoom)}
        onDragEnd={(e: { target: { x: () => number; y: () => number } }) =>
          setPos(limitarDesplazamiento({ x: e.target.x(), y: e.target.y() }, lienzo, zoom))}
        onWheel={alGirarRueda}
      >
        <Layer>
          <KonvaImage data-testid="metafase-editor-imagen" image={metafase} width={imagen.w} height={imagen.h} listening={false} />
          {objetos.map(({ c, poligono }) => {
            const elegido = c.id === selectedId;
            const color = SEMAFORO[c.semaphore] ?? SEMAFORO.red;
            return (
              <Line
                key={c.id}
                data-testid={`metafase-objeto-${c.id}`}
                data-semaphore={c.semaphore}
                data-seleccionado={String(elegido)}
                data-silueta={String(Array.isArray(c.contour) && c.contour.length >= 3)}
                aria-label={`Cromosoma ${c.predicted_class}, semáforo ${c.semaphore}`}
                points={puntosPlanos(poligono)}
                closed
                stroke={elegido ? SELECCION : color}
                strokeWidth={elegido ? 3 : 1.5}
                // El grosor del trazo no crece con el zoom: a 8× taparía el cromosoma.
                strokeScaleEnabled={false}
                // Un relleno tenue: sin relleno, Konva solo detecta el clic en el borde.
                fill={elegido ? RELLENO_SELECCION : (RELLENO[c.semaphore] ?? RELLENO.red)}
                hitStrokeWidth={6}
                onClick={() => onSelect(c)}
                onTap={() => onSelect(c)}
              />
            );
          })}
          {objetos.map(({ c, poligono }) => {
            const { x, y } = centroDe(poligono);
            return (
              <Text
                key={`etiqueta-${c.id}`}
                text={c.predicted_class}
                x={x}
                y={y}
                // Tamaño constante en pantalla, como el trazo.
                fontSize={12 / escala}
                offsetX={6 / escala}
                offsetY={6 / escala}
                fill="#ffffff"
                // Sin sombra, la etiqueta blanca se pierde sobre el fondo de la metafase.
                shadowColor="#000000"
                shadowBlur={3}
                shadowOpacity={0.9}
                listening={false}
              />
            );
          })}
        </Layer>
      </Stage>
      <p className="metafase-editor__ayuda">
        Pulse un cromosoma para seleccionarlo; queda marcado también en el cariograma. Use la
        rueda o los botones para acercar, y arrastre para moverse.
      </p>
    </section>
  );
}
