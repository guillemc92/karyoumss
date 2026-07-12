import { useRef, useState, useCallback } from 'react';

interface UseCameraResult {
  videoRef: React.MutableRefObject<HTMLVideoElement | null>;
  isConnected: boolean;
  error: string | null;
  connect: () => Promise<void>;
  disconnect: () => void;
  /** Captura el frame actual del video aplicando brillo/contraste, retorna dataURL JPEG. */
  capture: (brightness: number, contrast: number) => string | null;
}

export function useCamera(): UseCameraResult {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connect = useCallback(async () => {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setIsConnected(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo acceder a la cámara');
      setIsConnected(false);
    }
  }, []);

  const disconnect = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsConnected(false);
  }, []);

  const capture = useCallback((brightness: number, contrast: number): string | null => {
    const video = videoRef.current;
    if (!video || !streamRef.current) return null;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return null;
    ctx.filter = `brightness(${100 + brightness}%) contrast(${100 + contrast}%)`;
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg');
  }, []);

  return { videoRef, isConnected, error, connect, disconnect, capture };
}
