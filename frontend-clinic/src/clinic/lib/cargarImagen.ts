/**
 * Decodifica un `Blob` de imagen en un `HTMLImageElement` listo para Konva.
 *
 * Está aparte del hook a propósito: jsdom no decodifica imágenes (el `onload`
 * nunca llega) y no implementa `URL.createObjectURL`. Aislada aquí, los tests
 * del hook la sustituyen y prueban el ciclo de vida real —crear, usar,
 * revocar— sin esperar un evento que en jsdom no existe. La decodificación de
 * verdad se comprueba en el E2E, sobre un navegador real.
 */
export interface ImagenCargada {
  imagen: HTMLImageElement;
  /** Libera la URL temporal. La imagen ya decodificada sigue siendo válida. */
  liberar: () => void;
}

export function cargarImagen(blob: Blob): Promise<ImagenCargada> {
  const url = URL.createObjectURL(blob);
  return new Promise((resolve, reject) => {
    const imagen = new Image();
    imagen.onload = () => resolve({ imagen, liberar: () => URL.revokeObjectURL(url) });
    imagen.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('El navegador no pudo decodificar la metafase'));
    };
    imagen.src = url;
  });
}
