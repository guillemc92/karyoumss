import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { KaryotypeCanvas } from '../../src/clinic/components/KaryotypeCanvas';
import type { Chromosome } from '../../src/clinic/types/karyotype';
import { PAD, SLOT_W } from '../../src/clinic/lib/karyoLayout';
import { INITIAL_VIEWPORT } from '../../src/clinic/lib/viewport';

/** react-konva está mockeado globalmente en tests/setup.ts: los cromosomas se
 * renderizan como <button data-testid="chromosome-{id}"> y el drag se dispara
 * con el CustomEvent 'konvadragend' + globalThis.__konvaDrop. */

function chromo(overrides: Partial<Chromosome> = {}): Chromosome {
  return {
    id: 'c1', predicted_class: '1', position_index: 0, confidence_score: '0.960',
    semaphore: 'green', resolution_status: 'AUTO', xai_viewed: false,
    is_anomaly: false, is_active: true, measures: {}, bbox: {}, order: 0, ...overrides,
  };
}

function setDrop(x: number, y: number) {
  (globalThis as unknown as { __konvaDrop?: { x: number; y: number } }).__konvaDrop = { x, y };
}

describe('KaryotypeCanvas (Konva, P3)', () => {
  beforeEach(() => {
    delete (globalThis as unknown as { __konvaDrop?: unknown }).__konvaDrop;
  });

  it('renderiza el visor y un botón por cromosoma activo', () => {
    render(
      <KaryotypeCanvas
        chromosomes={[chromo({ id: 'a', predicted_class: '1' }), chromo({ id: 'b', predicted_class: '2' })]}
        selectedId={null}
        onSelect={() => {}}
      />,
    );
    const viewer = screen.getByTestId('karyotype-viewer');
    expect(viewer.querySelectorAll('button').length).toBe(2);
  });

  it('excluye los cromosomas inactivos (JOIN)', () => {
    render(
      <KaryotypeCanvas
        chromosomes={[chromo({ id: 'a' }), chromo({ id: 'b', predicted_class: '2', is_active: false })]}
        selectedId={null}
        onSelect={() => {}}
      />,
    );
    expect(screen.queryByTestId('chromosome-b')).not.toBeInTheDocument();
  });

  it('click en un cromosoma dispara onSelect', async () => {
    const onSelect = vi.fn();
    render(<KaryotypeCanvas chromosomes={[chromo({ id: 'a' })]} selectedId={null} onSelect={onSelect} />);
    await userEvent.click(screen.getByTestId('chromosome-a'));
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: 'a' }));
  });

  it('arrastrar a otro slot dispara onReclassify con la clase destino', () => {
    const onReclassify = vi.fn();
    render(
      <KaryotypeCanvas
        chromosomes={[chromo({ id: 'a', predicted_class: '1' })]}
        selectedId={null}
        onSelect={() => {}}
        onReclassify={onReclassify}
      />,
    );
    // Soltar sobre el slot 2 (columna siguiente) un cromosoma de clase 1.
    setDrop(PAD + SLOT_W + 10, PAD + 10);
    fireEvent(screen.getByTestId('chromosome-a'), new CustomEvent('konvadragend'));
    expect(onReclassify).toHaveBeenCalledWith(expect.objectContaining({ id: 'a' }), '2');
  });

  it('soltar en el mismo slot no reclasifica', () => {
    const onReclassify = vi.fn();
    render(
      <KaryotypeCanvas chromosomes={[chromo({ id: 'a', predicted_class: '1' })]} selectedId={null} onSelect={() => {}} onReclassify={onReclassify} />,
    );
    setDrop(PAD + 10, PAD + 10); // slot 1 = clase actual
    fireEvent(screen.getByTestId('chromosome-a'), new CustomEvent('konvadragend'));
    expect(onReclassify).not.toHaveBeenCalled();
  });

  it('en modo "Mover" (panMode) el cromosoma no reclasifica al arrastrar', () => {
    const onReclassify = vi.fn();
    render(
      <KaryotypeCanvas
        chromosomes={[chromo({ id: 'a', predicted_class: '1' })]}
        selectedId={null}
        viewport={{ ...INITIAL_VIEWPORT, panMode: true }}
        onSelect={() => {}}
        onReclassify={onReclassify}
      />,
    );
    setDrop(PAD + SLOT_W + 10, PAD + 10);
    fireEvent(screen.getByTestId('chromosome-a'), new CustomEvent('konvadragend'));
    expect(onReclassify).not.toHaveBeenCalled();
  });

  it('aplica el CSS filter de brillo/contraste al contenedor', () => {
    render(
      <KaryotypeCanvas
        chromosomes={[chromo({ id: 'a' })]}
        selectedId={null}
        viewport={{ ...INITIAL_VIEWPORT, brightness: 120, contrast: 80 }}
        onSelect={() => {}}
      />,
    );
    expect(screen.getByTestId('karyotype-viewer')).toHaveStyle({ filter: 'brightness(120%) contrast(80%)' });
  });

  it('con editable=false el cromosoma no es arrastrable (sin onReclassify)', () => {
    const onReclassify = vi.fn();
    render(
      <KaryotypeCanvas
        chromosomes={[chromo({ id: 'a', predicted_class: '1' })]}
        selectedId={null}
        editable={false}
        onSelect={() => {}}
        onReclassify={onReclassify}
      />,
    );
    setDrop(PAD + SLOT_W + 10, PAD + 10);
    fireEvent(screen.getByTestId('chromosome-a'), new CustomEvent('konvadragend'));
    expect(onReclassify).not.toHaveBeenCalled();
  });
});

// ============================================================================
// DD-KARYO-006 T3: los cromosomas reales
// ============================================================================
describe('KaryotypeCanvas con la metafase (DD-KARYO-006)', () => {
  /** Doble de una metafase ya decodificada de 1024 × 768. */
  const metafase = { width: 1024, height: 768, naturalWidth: 1024, naturalHeight: 768 } as HTMLImageElement;
  const BBOX = { x: 120, y: 340, w: 30, h: 60 };

  function pintar(cs: Chromosome[], props: Partial<Parameters<typeof KaryotypeCanvas>[0]> = {}) {
    return render(<KaryotypeCanvas chromosomes={cs} selectedId={null} onSelect={() => {}} metafase={metafase} {...props} />);
  }

  it('recorta de la metafase EXACTAMENTE la región de su bbox', () => {
    pintar([chromo({ id: 'a', bbox: BBOX })]);
    const img = screen.getByTestId('chromosome-img-a');
    expect(img.getAttribute('data-con-imagen')).toBe('true');
    expect(JSON.parse(img.getAttribute('data-crop')!)).toEqual({ x: 120, y: 340, width: 30, height: 60 });
  });

  it('lo encaja en su caja sin deformarlo: 30 × 60 cabe como 22 × 44', () => {
    pintar([chromo({ id: 'a', bbox: BBOX })]);
    const caja = JSON.parse(screen.getByTestId('chromosome-img-a').getAttribute('data-caja')!);
    expect(caja.w).toBeCloseTo(22);
    expect(caja.h).toBeCloseTo(44);
    expect(caja.w / caja.h).toBeCloseTo(BBOX.w / BBOX.h);
  });

  it('D8: un cromosoma tumbado se muestra de pie, girado 90° alrededor de su centro', () => {
    pintar([chromo({ id: 'a', bbox: { x: 200, y: 300, w: 70, h: 25 } })]);
    const img = screen.getByTestId('chromosome-img-a');
    // El recorte de la metafase es el mismo: el giro es solo de presentación.
    expect(JSON.parse(img.getAttribute('data-crop')!)).toEqual({ x: 200, y: 300, width: 70, height: 25 });
    const caja = JSON.parse(img.getAttribute('data-caja')!);
    expect(caja.rotacion).toBe(90);
    expect(caja.ox).toBeCloseTo(caja.w / 2);
    expect(caja.oy).toBeCloseTo(caja.h / 2);
  });

  it('el semáforo pasa a ser el borde, y el cromosoma sigue siendo seleccionable', () => {
    const onSelect = vi.fn();
    const c = chromo({ id: 'a', bbox: BBOX, semaphore: 'orange' });
    pintar([c], { onSelect });
    expect(screen.getByTestId('chromosome-frame-a')).toBeInTheDocument();
    expect(screen.getByTestId('chromosome-a').getAttribute('data-semaphore')).toBe('orange');
    screen.getByTestId('chromosome-a').click();
    expect(onSelect).toHaveBeenCalledWith(c);
  });

  it('sin metafase pinta el rectángulo de siempre (degradación)', () => {
    render(<KaryotypeCanvas chromosomes={[chromo({ id: 'a', bbox: BBOX })]} selectedId={null} onSelect={() => {}} />);
    expect(screen.queryByTestId('chromosome-img-a')).toBeNull();
    expect(screen.queryByTestId('chromosome-frame-a')).toBeNull();
  });

  it('un cromosoma sin bbox (anterior a P3) se pinta como rectángulo aunque haya metafase', () => {
    pintar([chromo({ id: 'a', bbox: {} }), chromo({ id: 'b', bbox: BBOX, predicted_class: '2' })]);
    expect(screen.queryByTestId('chromosome-img-a')).toBeNull();
    expect(screen.getByTestId('chromosome-img-b')).toBeInTheDocument();
  });

  it('un bbox que se sale de la metafase no se recorta', () => {
    pintar([chromo({ id: 'a', bbox: { x: 1010, y: 10, w: 30, h: 60 } })]);
    expect(screen.queryByTestId('chromosome-img-a')).toBeNull();
  });
});
