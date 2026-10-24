/**
 * DD-KARYO-006 T2: cómo llega la metafase al visor.
 *
 * - `karyotypeClient.metaphase()` pide la imagen con las MISMAS cabeceras que
 *   el resto (token y modo) y convierte los errores igual.
 * - `cargarImagen()` crea la URL temporal, la libera y no la deja viva si el
 *   navegador no puede decodificar.
 * - `useMetaphaseImage()` distingue «no hay imagen» (degradación) de «falló»,
 *   y libera la URL al desmontar.
 *
 * jsdom no decodifica imágenes ni implementa URL.createObjectURL: el hook se
 * prueba con `cargarImagen` sustituida y `cargarImagen` con un `Image` falso.
 * La decodificación real se comprueba en el E2E.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { server } from '../../src/clinic/msw/server';
import { setMetaphaseImageAvailable } from '../../src/clinic/msw/handlers';
import { createKaryotypeClient } from '../../src/clinic/api/karyotypeClient';
import { setClinicMode } from '../../src/clinic/api/samplesClient';

const READY = '00000000-0000-0000-0000-000000000442';      // tiene cariotipo
const PROCESSING = '00000000-0000-0000-0000-000000000441'; // NO_KARYOTYPE
const URL_METAFASE = '/api/clinic/samples/:id/karyotype/metaphase/';

const cargar = vi.hoisted(() => ({ fn: vi.fn() }));
vi.mock('../../src/clinic/lib/cargarImagen', async (original) => {
  const real = await original<typeof import('../../src/clinic/lib/cargarImagen')>();
  return { ...real, cargarImagen: (blob: Blob) => cargar.fn(blob) };
});

// Importado después del mock: el hook ve la versión sustituida.
const { useMetaphaseImage } = await import('../../src/clinic/hooks/useMetaphaseImage');

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

afterEach(() => {
  setClinicMode('auto');
  localStorage.removeItem('biomed.auth.access');
  cargar.fn.mockReset();
});

// ============================================================================
// Cliente
// ============================================================================
describe('karyotypeClient.metaphase', () => {
  const client = createKaryotypeClient('/api/clinic');

  it('devuelve la imagen como Blob con su tipo', async () => {
    const blob = await client.metaphase(READY);
    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toBe('image/png');
    expect(blob.size).toBeGreaterThan(0);
  });

  it('envía el token y el modo del sistema, como el resto de peticiones clínicas', async () => {
    localStorage.setItem('biomed.auth.access', 'token-de-prueba');
    setClinicMode('degradado');
    let cabeceras: Headers | null = null;
    server.use(http.get(URL_METAFASE, ({ request }) => {
      cabeceras = request.headers;
      return new HttpResponse(new Uint8Array([1]), { headers: { 'Content-Type': 'image/png' } });
    }));
    await client.metaphase(READY);
    expect(cabeceras!.get('Authorization')).toBe('Bearer token-de-prueba');
    expect(cabeceras!.get('X-Biomed-Mode')).toBe('degradado');
    expect(cabeceras!.get('Accept')).toBe('image/*');
  });

  it('sin metafase utilizable lanza 404 NO_METAPHASE_IMAGE', async () => {
    setMetaphaseImageAvailable(false);
    await expect(client.metaphase(READY)).rejects.toMatchObject({ status: 404, code: 'NO_METAPHASE_IMAGE' });
  });

  it('sin cariotipo lanza 404 NO_KARYOTYPE', async () => {
    await expect(client.metaphase(PROCESSING)).rejects.toMatchObject({ status: 404, code: 'NO_KARYOTYPE' });
  });

  it('un 403 de otro analista llega con su code', async () => {
    server.use(http.get(URL_METAFASE, () =>
      HttpResponse.json({ code: 'NOT_OWNER', detail: 'No es dueño de esta muestra' }, { status: 403 })));
    await expect(client.metaphase(READY)).rejects.toMatchObject({ status: 403, code: 'NOT_OWNER' });
  });

  it('un error sin JSON conserva el estado HTTP', async () => {
    server.use(http.get(URL_METAFASE, () => new HttpResponse('caído', { status: 502 })));
    await expect(client.metaphase(READY)).rejects.toMatchObject({ status: 502 });
  });

  it('un fallo de red se informa como NETWORK_ERROR', async () => {
    server.use(http.get(URL_METAFASE, () => HttpResponse.error()));
    await expect(client.metaphase(READY)).rejects.toMatchObject({ status: 0, code: 'NETWORK_ERROR' });
  });
});

// ============================================================================
// cargarImagen (con Image y URL falsos)
// ============================================================================
describe('cargarImagen', () => {
  const crear = vi.fn(() => 'blob:metafase');
  const revocar = vi.fn();
  let decodifica = true;

  class ImagenFalsa {
    onload: (() => void) | null = null;
    onerror: (() => void) | null = null;
    set src(_valor: string) {
      queueMicrotask(() => (decodifica ? this.onload?.() : this.onerror?.()));
    }
  }

  beforeEach(() => {
    decodifica = true;
    crear.mockClear();
    revocar.mockClear();
    vi.stubGlobal('Image', ImagenFalsa);
    vi.stubGlobal('URL', { ...URL, createObjectURL: crear, revokeObjectURL: revocar });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('resuelve con la imagen y liberar() revoca la URL temporal', async () => {
    const { cargarImagen } = await vi.importActual<typeof import('../../src/clinic/lib/cargarImagen')>(
      '../../src/clinic/lib/cargarImagen');
    const cargada = await cargarImagen(new Blob(['x']));
    expect(cargada.imagen).toBeInstanceOf(ImagenFalsa);
    expect(revocar).not.toHaveBeenCalled();
    cargada.liberar();
    expect(revocar).toHaveBeenCalledWith('blob:metafase');
  });

  it('si el navegador no puede decodificar, rechaza y NO deja la URL viva', async () => {
    decodifica = false;
    const { cargarImagen } = await vi.importActual<typeof import('../../src/clinic/lib/cargarImagen')>(
      '../../src/clinic/lib/cargarImagen');
    await expect(cargarImagen(new Blob(['x']))).rejects.toThrow('no pudo decodificar');
    expect(revocar).toHaveBeenCalledWith('blob:metafase');
  });
});

// ============================================================================
// useMetaphaseImage
// ============================================================================
describe('useMetaphaseImage', () => {
  const imagen = { width: 1024, height: 768 } as HTMLImageElement;

  it('lista: entrega la imagen decodificada', async () => {
    cargar.fn.mockResolvedValue({ imagen, liberar: vi.fn() });
    const { result } = renderHook(() => useMetaphaseImage(READY), { wrapper });
    expect(result.current.estado).toBe('cargando');
    await waitFor(() => expect(result.current.estado).toBe('lista'));
    expect(result.current.imagen).toBe(imagen);
    expect(cargar.fn).toHaveBeenCalledWith(expect.any(Blob));
  });

  it('al desmontar libera la URL temporal', async () => {
    const liberar = vi.fn();
    cargar.fn.mockResolvedValue({ imagen, liberar });
    const { result, unmount } = renderHook(() => useMetaphaseImage(READY), { wrapper });
    await waitFor(() => expect(result.current.estado).toBe('lista'));
    unmount();
    expect(liberar).toHaveBeenCalledTimes(1);
  });

  it('si se desmonta antes de decodificar, libera en cuanto termina', async () => {
    const liberar = vi.fn();
    let terminar: (v: unknown) => void = () => {};
    cargar.fn.mockReturnValue(new Promise((r) => { terminar = r; }));
    const { unmount } = renderHook(() => useMetaphaseImage(READY), { wrapper });
    await waitFor(() => expect(cargar.fn).toHaveBeenCalled());
    unmount();
    terminar({ imagen, liberar });
    await waitFor(() => expect(liberar).toHaveBeenCalledTimes(1));
  });

  it('sin-imagen: un 404 NO_METAPHASE_IMAGE es degradación, no error', async () => {
    setMetaphaseImageAvailable(false);
    const { result } = renderHook(() => useMetaphaseImage(READY), { wrapper });
    await waitFor(() => expect(result.current.estado).toBe('sin-imagen'));
    expect(result.current.imagen).toBeNull();
    expect(cargar.fn).not.toHaveBeenCalled();
  });

  it('sin-imagen: también sin cariotipo', async () => {
    const { result } = renderHook(() => useMetaphaseImage(PROCESSING), { wrapper });
    await waitFor(() => expect(result.current.estado).toBe('sin-imagen'));
  });

  it('error: un fallo del servidor no se confunde con «no hay imagen»', async () => {
    server.use(http.get(URL_METAFASE, () => new HttpResponse('caído', { status: 500 })));
    const { result } = renderHook(() => useMetaphaseImage(READY), { wrapper });
    await waitFor(() => expect(result.current.estado).toBe('error'));
    expect(result.current.imagen).toBeNull();
  });

  it('error: el navegador no pudo decodificar', async () => {
    cargar.fn.mockRejectedValue(new Error('no pudo decodificar'));
    const { result } = renderHook(() => useMetaphaseImage(READY), { wrapper });
    await waitFor(() => expect(result.current.estado).toBe('error'));
    expect(result.current.imagen).toBeNull();
  });

  it('sin id de muestra no pide nada', async () => {
    const { result } = renderHook(() => useMetaphaseImage(undefined), { wrapper });
    expect(result.current.estado).toBe('cargando');
    expect(cargar.fn).not.toHaveBeenCalled();
  });
});
