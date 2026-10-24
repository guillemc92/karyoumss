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
  return new Promise((resolve, reject) => {
    // Dentro de la promesa: si el entorno no sabe crear la URL (jsdom), es un
    // rechazo —el visor cae a los rectángulos— y no una excepción que tumbe
    // la pantalla entera desde el efecto que la llama.
    const url = URL.createObjectURL(blob);
    const imagen = new Image();
    imagen.onload = () => resolve({ imagen, liberar: () => URL.revokeObjectURL(url) });
    imagen.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('El navegador no pudo decodificar la metafase'));
    };
    imagen.src = url;
  });
}
