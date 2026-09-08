import { describe, expect, it, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useCamera } from '../../src/clinic/hooks/useCamera';

function mockGetUserMedia(impl: () => Promise<MediaStream>) {
  Object.defineProperty(navigator, 'mediaDevices', {
    value: { getUserMedia: vi.fn(impl) },
    configurable: true,
  });
}

describe('useCamera', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('estado inicial: desconectado, sin error', () => {
    const { result } = renderHook(() => useCamera());
    expect(result.current.isConnected).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('connect() exitoso marca isConnected=true', async () => {
    const fakeStream = { getTracks: () => [] } as unknown as MediaStream;
    mockGetUserMedia(() => Promise.resolve(fakeStream));
    const { result } = renderHook(() => useCamera());

    await act(async () => {
      await result.current.connect();
    });

    await waitFor(() => expect(result.current.isConnected).toBe(true));
  });

  it('connect() rechazado por el usuario setea error', async () => {
    mockGetUserMedia(() => Promise.reject(new Error('Permission denied')));
    const { result } = renderHook(() => useCamera());

    await act(async () => {
      await result.current.connect();
    });

    await waitFor(() => expect(result.current.error).toBe('Permission denied'));
    expect(result.current.isConnected).toBe(false);
  });

  it('disconnect() detiene el stream y marca isConnected=false', async () => {
    const stop = vi.fn();
    const fakeStream = { getTracks: () => [{ stop }] } as unknown as MediaStream;
    mockGetUserMedia(() => Promise.resolve(fakeStream));
    const { result } = renderHook(() => useCamera());

    await act(async () => {
      await result.current.connect();
    });
    act(() => {
      result.current.disconnect();
    });

    expect(stop).toHaveBeenCalled();
    expect(result.current.isConnected).toBe(false);
  });

  it('capture() sin cámara conectada retorna null', () => {
    const { result } = renderHook(() => useCamera());
    expect(result.current.capture(0, 0)).toBeNull();
  });

  it('connect() asigna srcObject al elemento video cuando videoRef está attacheado', async () => {
    const fakeStream = { getTracks: () => [] } as unknown as MediaStream;
    mockGetUserMedia(() => Promise.resolve(fakeStream));
    const { result } = renderHook(() => useCamera());
    const video = document.createElement('video');
    result.current.videoRef.current = video;

    await act(async () => {
      await result.current.connect();
    });

    expect(video.srcObject).toBe(fakeStream);
  });

  it('capture() con cámara conectada y video attacheado retorna dataURL', async () => {
    const fakeStream = { getTracks: () => [] } as unknown as MediaStream;
    mockGetUserMedia(() => Promise.resolve(fakeStream));
    const { result } = renderHook(() => useCamera());
    const video = document.createElement('video');
    result.current.videoRef.current = video;

    await act(async () => {
      await result.current.connect();
    });

    const fakeCtx = { filter: '', drawImage: vi.fn() } as unknown as CanvasRenderingContext2D;
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(fakeCtx);
    vi.spyOn(HTMLCanvasElement.prototype, 'toDataURL').mockReturnValue('data:image/jpeg;base64,mocked');

    const result_ = result.current.capture(10, -5);
    expect(result_).toBe('data:image/jpeg;base64,mocked');
    expect(fakeCtx.filter).toBe('brightness(110%) contrast(95%)');
  });

  it('capture() cuando getContext retorna null, retorna null', async () => {
    const fakeStream = { getTracks: () => [] } as unknown as MediaStream;
    mockGetUserMedia(() => Promise.resolve(fakeStream));
    const { result } = renderHook(() => useCamera());
    const video = document.createElement('video');
    result.current.videoRef.current = video;

    await act(async () => {
      await result.current.connect();
    });

    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);
    expect(result.current.capture(0, 0)).toBeNull();
  });

  it('disconnect() limpia srcObject del video attacheado', async () => {
    const fakeStream = { getTracks: () => [{ stop: vi.fn() }] } as unknown as MediaStream;
    mockGetUserMedia(() => Promise.resolve(fakeStream));
    const { result } = renderHook(() => useCamera());
    const video = document.createElement('video');
    result.current.videoRef.current = video;

    await act(async () => {
      await result.current.connect();
    });
    act(() => {
      result.current.disconnect();
    });

    expect(video.srcObject).toBeNull();
  });
});
