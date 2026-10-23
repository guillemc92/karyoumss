/**
 * MetafaseEditor — la metafase como lienzo principal (DD-KARYO-007 F1, T2).
 *
 * Pinta la metafase entera y encima la silueta de cada cromosoma, con el color
 * de su semáforo. Seleccionar aquí o en el cariograma es lo mismo: los dos leen
 * y escriben el mismo `selectedId` de la página.
 *
 * Es el sitio donde, en Ikaros y en MetaClass, se corrige la segmentación: en
 * el cariograma cada cromosoma está aislado y no se ve con qué se tocaba.
 *
 * T3 (D5): **añadir** el cromosoma que la segmentación no vio, dibujando su caja,
 * y **descartar** lo que no es un cromosoma (núcleo, suciedad), con motivo.
 * Supr abre el descarte del seleccionado, como en MetaClass; Esc cancela.
 * F2 añadirá el corte por línea.
 *
 * Coordenadas: el Stage lleva la escala total (ajuste × zoom) y el
 * desplazamiento. Imagen y contornos van en píxeles de la metafase, tal cual
 * los guarda el servidor, así que no hay conversión que pueda desalinearlos.
 */
import { useEffect, useState } from 'react';
import { Image as KonvaImage, Layer, Line, Rect, Stage, Text } from 'react-konva';
import type { BBox, Chromosome, MotivoDescarte } from '../types/karyotype';
import { CHROMOSOME_SLOTS, MOTIVOS_DESCARTE } from '../types/karyotype';
import type { Punto } from '../lib/medicion';
import {
  PASO_ZOOM,
  ZOOM_MAX,
  ZOOM_MIN,
  aImagen,
  cajaEntre,
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
  /** Sin `onAnadir` ni `onDescartar` el editor es de consulta (caso validado). */
  onAnadir?: (bbox: BBox, clase: string) => void;
  onDescartar?: (c: Chromosome, motivo: MotivoDescarte) => void;
  /** Hay una corrección en curso en el servidor: no se lanza otra encima. */
  busy?: boolean;
}

type Herramienta = 'seleccionar' | 'anadir';

interface EventoPuntero {
  target: { getStage: () => unknown };
}

interface EventoRueda extends EventoPuntero {
  evt: { deltaY: number; preventDefault: () => void };
}

/** Las teclas del editor no deben saltar mientras se escribe en un campo. */
function escribiendo(e: KeyboardEvent): boolean {
  const t = e.target as HTMLElement | null;
  return Boolean(t && ['INPUT', 'SELECT', 'TEXTAREA'].includes(t.tagName));
}

export function MetafaseEditor({
  metafase, chromosomes, selectedId, onSelect, onAnadir, onDescartar, busy = false,
}: MetafaseEditorProps) {
  const imagen = { w: metafase.naturalWidth || metafase.width, h: metafase.naturalHeight || metafase.height };
  const ajuste = escalaAjuste(imagen, LIENZO_MAX);
  const lienzo = { w: Math.round(imagen.w * ajuste), h: Math.round(imagen.h * ajuste) };

  const [zoom, setZoom] = useState(ZOOM_MIN);
  const [pos, setPos] = useState<Punto>({ x: 0, y: 0 });
  const escala = ajuste * zoom;

  const [herramienta, setHerramienta] = useState<Herramienta>('seleccionar');
  // Esquinas de la caja que se está dibujando, en píxeles de la metafase.
  const [inicio, setInicio] = useState<Punto | null>(null);
  const [fin, setFin] = useState<Punto | null>(null);
  /** '' = que la decida el modelo. */
  const [clase, setClase] = useState('');
  const [confirmando, setConfirmando] = useState(false);
  const [motivo, setMotivo] = useState<MotivoDescarte | ''>('');
  const anadiendo = herramienta === 'anadir' && Boolean(onAnadir);

  const objetos = chromosomes
    .filter((c) => c.is_active)
    .map((c) => ({ c, poligono: poligonoDe(c, imagen) }))
    .filter((o): o is { c: Chromosome; poligono: number[][] } => o.poligono !== null);

  // Seleccionar en el cariograma con zoom puesto trae el cromosoma a la vista.
  // Sin zoom no se mueve nada: `centrarEn` limita el desplazamiento a (0, 0).
  const seleccionado = objetos.find((o) => o.c.id === selectedId);
  useEffect(() => {
    // Cambiar de cromosoma cierra el descarte a medias: confirmaría otro objeto.
    setConfirmando(false);
    setMotivo('');
    if (!seleccionado) return;
    setPos(centrarEn(centroDe(seleccionado.poligono), escala, lienzo, zoom));
  }, [selectedId]); // eslint-disable-line react-hooks/exhaustive-deps

  const cancelar = () => {
    setInicio(null);
    setFin(null);
    setConfirmando(false);
    setMotivo('');
  };

  useEffect(() => {
    const alPulsar = (e: KeyboardEvent) => {
      if (escribiendo(e)) return;
      if (e.key === 'Escape') {
        cancelar();
        setHerramienta('seleccionar');
      } else if (e.key === 'Delete' && onDescartar && seleccionado && !busy) {
        e.preventDefault();
        setConfirmando(true);
      }
    };
    window.addEventListener('keydown', alPulsar);
    return () => window.removeEventListener('keydown', alPulsar);
  });

  const puntero = (e: EventoPuntero): Punto | null => {
    const stage = e.target.getStage() as { getPointerPosition: () => Punto | null } | null;
    const p = stage?.getPointerPosition();
    return p ? aImagen(p, pos, escala) : null;
  };
  const empezarCaja = (e: EventoPuntero) => {
    if (!anadiendo || busy) return;
    const p = puntero(e);
    if (!p) return;
    setInicio(p);
    setFin(p);
  };
  const moverCaja = (e: EventoPuntero) => {
    if (!inicio) return;
    const p = puntero(e);
    if (p) setFin(p);
  };
  // Al soltar se envía. La herramienta sigue activa: en un caso suele faltar
  // más de un cromosoma pequeño, y volver a pulsar «Añadir» cada vez estorba.
  const soltarCaja = () => {
    if (!inicio || !fin) return;
    const caja = cajaEntre(inicio, fin, imagen);
    setInicio(null);
    setFin(null);
    if (caja && onAnadir) onAnadir(caja, clase);
  };
  const enCurso = inicio && fin ? cajaEntre(inicio, fin, imagen) : null;

  const confirmarDescarte = () => {
    if (!seleccionado || !motivo || !onDescartar) return;
    onDescartar(seleccionado.c, motivo);
    setConfirmando(false);
    setMotivo('');
  };

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

  const elegirHerramienta = (h: Herramienta) => {
    cancelar();
    setHerramienta(h);
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
      {(onAnadir || onDescartar) && (
        <div className="metafase-editor__barra" data-testid="metafase-herramientas">
          <button
            type="button"
            className="btn-outline"
            data-testid="metafase-herramienta-seleccionar"
            aria-pressed={herramienta === 'seleccionar'}
            onClick={() => elegirHerramienta('seleccionar')}
          >
            Seleccionar
          </button>
          {onAnadir && (
            <button
              type="button"
              className="btn-outline"
              data-testid="metafase-herramienta-anadir"
              aria-pressed={herramienta === 'anadir'}
              onClick={() => elegirHerramienta('anadir')}
            >
              Añadir cromosoma
            </button>
          )}
          {onAnadir && (
            // Siempre en el DOM, oculto fuera de «Añadir»: si apareciera al
            // entrar, la barra crecería y el lienzo bajaría justo cuando el
            // analista va a dibujar (medido: 6 px de metafase el 23/10).
            <label className="metafase-editor__campo" style={{ visibility: anadiendo ? 'visible' : 'hidden' }}
              aria-hidden={!anadiendo}>
              Clase
              <select data-testid="metafase-anadir-clase" value={clase} disabled={!anadiendo}
                onChange={(e) => setClase(e.target.value)}>
                <option value="">Automática (IA)</option>
                {CHROMOSOME_SLOTS.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </label>
          )}
          {onDescartar && (
            <button
              type="button"
              className="btn-outline"
              data-testid="metafase-descartar"
              disabled={!seleccionado || busy}
              onClick={() => setConfirmando(true)}
              title="Supr"
            >
              Descartar objeto
            </button>
          )}
        </div>
      )}
      {confirmando && seleccionado && (
        <div
          className="metafase-editor__barra metafase-editor__confirmar"
          data-testid="metafase-confirmar-descarte"
          role="group"
          aria-label="Confirmar descarte"
        >
          <span>Descartar el objeto marcado como {seleccionado.c.predicted_class}. Motivo:</span>
          <select
            data-testid="metafase-motivo"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value as MotivoDescarte | '')}
            aria-label="Motivo del descarte"
          >
            <option value="">— elija —</option>
            {MOTIVOS_DESCARTE.map((m) => <option key={m.valor} value={m.valor}>{m.texto}</option>)}
          </select>
          <button
            type="button"
            className="btn-outline"
            data-testid="metafase-confirmar"
            disabled={!motivo || busy}
            onClick={confirmarDescarte}
          >
            Confirmar
          </button>
          <button type="button" className="btn-outline" data-testid="metafase-cancelar-descarte" onClick={cancelar}>
            Cancelar
          </button>
        </div>
      )}
      <Stage
        data-testid="metafase-editor-stage"
        data-herramienta={herramienta}
        width={lienzo.w}
        height={lienzo.h}
        scaleX={escala}
        scaleY={escala}
        x={pos.x}
        y={pos.y}
        // Sin zoom no hay nada que desplazar, y arrastrar movería la imagen fuera.
        // Añadiendo, arrastrar dibuja la caja: no puede mover también la vista.
        draggable={zoom > ZOOM_MIN && !anadiendo}
        dragBoundFunc={(p: Punto) => limitarDesplazamiento(p, lienzo, zoom)}
        onDragEnd={(e: { target: { x: () => number; y: () => number } }) =>
          setPos(limitarDesplazamiento({ x: e.target.x(), y: e.target.y() }, lienzo, zoom))}
        onWheel={alGirarRueda}
        onMouseDown={empezarCaja}
        onMouseMove={moverCaja}
        onMouseUp={soltarCaja}
        // Soltar fuera del lienzo también cierra la caja: si no, se queda pegada al cursor.
        onMouseLeave={soltarCaja}
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
                // Añadiendo, el clic es para la caja nueva, no para seleccionar.
                listening={!anadiendo}
                onClick={anadiendo ? undefined : () => onSelect(c)}
                onTap={anadiendo ? undefined : () => onSelect(c)}
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
          {enCurso && (
            <Rect
              data-testid="metafase-caja-nueva"
              x={enCurso.x}
              y={enCurso.y}
              width={enCurso.w}
              height={enCurso.h}
              stroke={SELECCION}
              strokeWidth={2}
              strokeScaleEnabled={false}
              dash={[6, 4]}
              listening={false}
            />
          )}
        </Layer>
      </Stage>
      <p className="metafase-editor__ayuda" data-testid="metafase-ayuda-editor">
        {anadiendo
          ? 'Dibuje una caja alrededor del cromosoma que falta. Si la IA no responde, elija antes la clase. Esc para terminar.'
          : 'Pulse un cromosoma para seleccionarlo; queda marcado también en el cariograma. Use la rueda o los botones para acercar, y arrastre para moverse.'}
      </p>
    </section>
  );
}
