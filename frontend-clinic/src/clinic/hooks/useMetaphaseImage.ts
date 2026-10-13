import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { karyotypeClient } from '../api/karyotypeClient';
import { cargarImagen } from '../lib/cargarImagen';
import { ClinicApiException } from '../types/sample';

/**
 * Estado de la metafase del cariotipo (DD-KARYO-006):
 * - `cargando`   todavía no hay imagen;
 * - `lista`      `imagen` decodificada, el lienzo recorta los cromosomas de ella;
 * - `sin-imagen` el caso no tiene una metafase utilizable (404): es
 *                degradación, no un fallo, y el lienzo pinta los rectángulos;
 * - `error`      falló la red o la decodificación: también se pintan los
 *                rectángulos, pero la pantalla puede decir que algo falló.
 */
export type EstadoMetafase = 'cargando' | 'lista' | 'sin-imagen' | 'error';

const SIN_IMAGEN = new Set(['NO_METAPHASE_IMAGE', 'NO_KARYOTYPE']);

export function useMetaphaseImage(sampleId: string | undefined): {
  imagen: HTMLImageElement | null;
  estado: EstadoMetafase;
} {
  const consulta = useQuery({
    queryKey: ['clinic', 'karyotype', sampleId, 'metaphase'] as const,
    queryFn: () => karyotypeClient.metaphase(sampleId as string),
    enabled: Boolean(sampleId),
    retry: false,
    // La metafase de un caso no cambia: separar, unir o recortar mueven cajas
    // sobre la misma imagen. No hay que volver a descargar 3 MB por eso.
    staleTime: Infinity,
  });

  const [imagen, setImagen] = useState<HTMLImageElement | null>(null);
  const [falloDecodificar, setFalloDecodificar] = useState(false);

  useEffect(() => {
    const blob = consulta.data;
    setImagen(null);
    setFalloDecodificar(false);
    if (!blob) return undefined;

    let vigente = true;
    let liberar: (() => void) | null = null;
    cargarImagen(blob).then(
      (cargada) => {
        if (!vigente) {
          cargada.liberar();
          return;
        }
        liberar = cargada.liberar;
        setImagen(cargada.imagen);
      },
      () => {
        if (vigente) setFalloDecodificar(true);
      },
    );
    // Al desmontar o al cambiar de caso se libera la URL temporal. Sin esto,
    // cada caso abierto dejaría varios MB retenidos en el navegador.
    return () => {
      vigente = false;
      liberar?.();
    };
  }, [consulta.data]);

  let estado: EstadoMetafase = 'cargando';
  if (consulta.isError) {
    const error = consulta.error;
    estado = error instanceof ClinicApiException && error.code && SIN_IMAGEN.has(error.code)
      ? 'sin-imagen'
      : 'error';
  } else if (falloDecodificar) {
    estado = 'error';
  } else if (imagen) {
    estado = 'lista';
  }
  return { imagen: estado === 'lista' ? imagen : null, estado };
}
