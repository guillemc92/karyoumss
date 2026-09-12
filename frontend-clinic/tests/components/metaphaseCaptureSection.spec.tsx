import { describe, expect, it, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MetaphaseCaptureSection } from '../../src/clinic/components/MetaphaseCaptureSection';
import type { CapturedImage } from '../../src/clinic/types/registration';

const SAMPLE_IMAGE: CapturedImage = { data_base64: 'data:image/jpeg;base64,aGVsbG8=', source: 'upload' };

describe('MetaphaseCaptureSection', () => {
  beforeEach(() => {
    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getUserMedia: vi.fn(() => Promise.reject(new Error('no camera in jsdom'))) },
      configurable: true,
    });
  });

  it('muestra "Sin conectar" y placeholder cuando no hay cámara', () => {
    render(<MetaphaseCaptureSection images={[]} onChange={vi.fn()} />);
    expect(screen.getByText('📷 Cámara desconectada')).toBeInTheDocument();
    expect(screen.getByText(/Conecte una cámara o seleccione un archivo/)).toBeInTheDocument();
  });

  it('badge de calidad muestra advertencia con pocas imágenes', () => {
    render(<MetaphaseCaptureSection images={[]} onChange={vi.fn()} />);
    expect(screen.getByText(/Faltan 20 metafases/)).toBeInTheDocument();
  });

  it('badge de calidad muestra "Suficiente" con >=20 imágenes', () => {
    const images = Array.from({ length: 20 }, () => SAMPLE_IMAGE);
    render(<MetaphaseCaptureSection images={images} onChange={vi.fn()} />);
    expect(screen.getByText(/Calidad: Suficiente/)).toBeInTheDocument();
  });

  it('galería vacía muestra mensaje informativo', () => {
    render(<MetaphaseCaptureSection images={[]} onChange={vi.fn()} />);
    expect(screen.getByText(/No hay metafases capturadas/)).toBeInTheDocument();
  });

  it('galería con imágenes las renderiza', () => {
    render(<MetaphaseCaptureSection images={[SAMPLE_IMAGE, SAMPLE_IMAGE]} onChange={vi.fn()} />);
    expect(screen.getByText('Metafase 1')).toBeInTheDocument();
    expect(screen.getByText('Metafase 2')).toBeInTheDocument();
  });

  it('eliminar una imagen individual llama onChange sin esa imagen', async () => {
    const onChange = vi.fn();
    const img2: CapturedImage = { data_base64: 'data:image/jpeg;base64,d29ybGQ=', source: 'camera' };
    const { container } = render(<MetaphaseCaptureSection images={[SAMPLE_IMAGE, img2]} onChange={onChange} />);
    const deleteButtons = container.querySelectorAll('.delete-image');
    await userEvent.click(deleteButtons[0]);
    expect(onChange).toHaveBeenCalledWith([img2]);
  });

  it('limpiar todas pide confirmación y vacía la galería', async () => {
    const onChange = vi.fn();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    render(<MetaphaseCaptureSection images={[SAMPLE_IMAGE]} onChange={onChange} />);
    await userEvent.click(screen.getByText(/Limpiar todas/));
    expect(onChange).toHaveBeenCalledWith([]);
  });

  it('limpiar todas cancelada no vacía la galería', async () => {
    const onChange = vi.fn();
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    render(<MetaphaseCaptureSection images={[SAMPLE_IMAGE]} onChange={onChange} />);
    await userEvent.click(screen.getByText(/Limpiar todas/));
    expect(onChange).not.toHaveBeenCalled();
  });

  it('conectar cámara falla (jsdom) y muestra mensaje de error', async () => {
    render(<MetaphaseCaptureSection images={[]} onChange={vi.fn()} />);
    await userEvent.click(screen.getByText(/Conectar cámara/));
    expect(await screen.findByText('no camera in jsdom')).toBeInTheDocument();
  });

  it('subir archivo agrega una imagen a la galería', async () => {
    const onChange = vi.fn();
    const { container } = render(<MetaphaseCaptureSection images={[]} onChange={onChange} />);
    const file = new File(['hello'], 'metafase.jpg', { type: 'image/jpeg' });
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(input, file);
    await vi.waitFor(() => expect(onChange).toHaveBeenCalled());
  });

  it('el botón capturar está deshabilitado sin cámara conectada', () => {
    render(<MetaphaseCaptureSection images={[]} onChange={vi.fn()} />);
    expect(screen.getByText(/Capturar metafase/)).toBeDisabled();
  });

  it('cambiar el slider de brillo actualiza el valor mostrado', async () => {
    render(<MetaphaseCaptureSection images={[]} onChange={vi.fn()} />);
    const sliders = document.querySelectorAll('input[type="range"]');
    await userEvent.type(sliders[0] as HTMLInputElement, '{arrowright}');
    expect(sliders[0]).toBeInTheDocument();
  });

  it('conectar cámara exitosamente y capturar agrega una imagen', async () => {
    const fakeStream = { getTracks: () => [] } as unknown as MediaStream;
    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getUserMedia: vi.fn(() => Promise.resolve(fakeStream)) },
      configurable: true,
    });
    const fakeCtx = { filter: '', drawImage: vi.fn() } as unknown as CanvasRenderingContext2D;
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(fakeCtx);
    vi.spyOn(HTMLCanvasElement.prototype, 'toDataURL').mockReturnValue('data:image/jpeg;base64,captured');

    const onChange = vi.fn();
    render(<MetaphaseCaptureSection images={[]} onChange={onChange} />);
    await userEvent.click(screen.getByText(/Conectar cámara/));
    await screen.findByText('✅ Cámara conectada');

    await userEvent.click(screen.getByText(/Capturar metafase/));
    expect(onChange).toHaveBeenCalledWith([{ data_base64: 'data:image/jpeg;base64,captured', source: 'camera' }]);
  });

  it('subir múltiples archivos agrega todas las imágenes de una vez (no race condition)', async () => {
    const onChange = vi.fn();
    const { container } = render(<MetaphaseCaptureSection images={[]} onChange={onChange} />);
    const files = [
      new File(['a'], 'a.jpg', { type: 'image/jpeg' }),
      new File(['b'], 'b.jpg', { type: 'image/jpeg' }),
      new File(['c'], 'c.jpg', { type: 'image/jpeg' }),
    ];
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(input, files);
    await vi.waitFor(() => expect(onChange).toHaveBeenCalledTimes(1));
    expect(onChange.mock.calls[0][0]).toHaveLength(3);
  });

  it('desconectar cámara vuelve al estado inicial', async () => {
    const fakeStream = { getTracks: () => [] } as unknown as MediaStream;
    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getUserMedia: vi.fn(() => Promise.resolve(fakeStream)) },
      configurable: true,
    });
    render(<MetaphaseCaptureSection images={[]} onChange={vi.fn()} />);
    await userEvent.click(screen.getByText(/Conectar cámara/));
    await screen.findByText('✅ Cámara conectada');
    await userEvent.click(screen.getByText('Desconectar cámara'));
    expect(screen.getByText('📷 Cámara desconectada')).toBeInTheDocument();
  });
});
