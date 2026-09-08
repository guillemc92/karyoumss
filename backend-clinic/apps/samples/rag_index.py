"""Embeddings, índice y consulta top-k del RAG.

Pasos 3, 4 y 5 del pipeline: **embeber** cada fragmento, **indexar** de forma
consultable desde el repositorio, y **recuperar** los más similares con su
porcentaje de similitud.

## Por qué NO hay base de datos vectorial

El corpus son ~1.150 fragmentos. Buscar por fuerza bruta es un producto
matriz-vector de 1.150×768: menos de un millón de multiplicaciones, que NumPy
resuelve en microsegundos. Montar pgvector, FAISS o un servicio en la nube para
esto añadiría infraestructura, despliegue y un punto de fallo más sin ganar nada
medible.

Es el criterio de «usa el nivel mínimo que resuelva el problema»: el índice es
un fichero que se versiona con el código y se carga en memoria al arrancar. Si
el corpus creciera un par de órdenes de magnitud, esta decisión se revisa —
`buscar()` es la única función que habría que cambiar.

## Similitud coseno sobre vectores normalizados

Al normalizar en la indexación, el coseno se reduce a un producto escalar. Se
reporta como porcentaje porque es lo que la consigna pide mostrar y lo que
permite comparar candidatos entre sí.

**Un porcentaje alto no significa que la respuesta sea correcta**: significa que
ese fragmento es el más parecido a la pregunta *de los que hay*. Por eso existe
`UMBRAL_MINIMO`: por debajo, se prefiere decir que no se sabe antes que
responder con el fragmento menos malo.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .rag_corpus import Fragmento

# El índice vive en el repositorio (lo exige la consigna) y se versiona.
RUTA_INDICE = Path(__file__).resolve().parent / 'rag_data'
MODELO_POR_DEFECTO = 'nomic-embed-text'

# Por debajo de esta similitud, ningún fragmento se considera pertinente. El
# valor sale de medir, no de la intuición: ver `manage.py eval_rag`.
UMBRAL_MINIMO = 0.55

TOP_K = 4


class RagError(Exception):
    """El índice no existe, no se puede leer, o el embebedor no responde."""


# Lote pequeño y timeout generoso: en CPU, embeber 32 fragmentos de 2.000
# caracteres puede pasar de dos minutos. Se midió agotando el timeout anterior.
LOTE = 16
TIMEOUT_S = 600.0


def embeber(textos: list[str], modelo: str = MODELO_POR_DEFECTO,
            base_url: str = 'http://localhost:11434',
            progreso=None) -> np.ndarray:
    """Convierte textos a vectores normalizados usando Ollama local.

    Local por la misma razón que el resto del pipeline (ADR-0024, RN-03): el
    corpus incluye documentación clínica del laboratorio y no tiene por qué
    salir de la máquina para convertirse en números.

    `progreso(hechos, total)` se llama tras cada lote — construir el índice
    tarda minutos y sin señal no se distingue de un cuelgue.
    """
    import httpx

    vectores: list[list[float]] = []
    try:
        with httpx.Client(timeout=TIMEOUT_S) as cliente:
            # Por lotes: una petición por fragmento multiplicaría por mil la
            # latencia de construir el índice.
            for i in range(0, len(textos), LOTE):
                lote = textos[i:i + LOTE]
                r = cliente.post(f'{base_url}/api/embed',
                                 json={'model': modelo, 'input': lote})
                r.raise_for_status()
                vectores.extend(r.json()['embeddings'])
                if progreso:
                    progreso(len(vectores), len(textos))
    except Exception as exc:                       # noqa: BLE001
        raise RagError(f'no se pudo embeber con {modelo}: {exc}') from exc

    m = np.asarray(vectores, dtype=np.float32)
    normas = np.linalg.norm(m, axis=1, keepdims=True)
    normas[normas == 0] = 1.0                      # un vector nulo no rompe nada
    return m / normas


@dataclass
class Resultado:
    """Un fragmento recuperado, con de dónde salió y cuánto se parece."""

    fragmento: Fragmento
    similitud: float

    @property
    def porcentaje(self) -> str:
        return f'{self.similitud * 100:.1f}%'

    def como_cita(self) -> str:
        donde = f'{self.fragmento.fuente}'
        if self.fragmento.seccion:
            donde += f' — {self.fragmento.seccion}'
        return f'{donde} ({self.porcentaje})'


class Indice:
    """Índice consultable: vectores en memoria + metadatos de cada fragmento."""

    def __init__(self, vectores: np.ndarray, fragmentos: list[Fragmento], modelo: str):
        if len(vectores) != len(fragmentos):
            raise RagError('vectores y fragmentos descuadrados')
        self.vectores = vectores
        self.fragmentos = fragmentos
        self.modelo = modelo

    def __len__(self) -> int:
        return len(self.fragmentos)

    def buscar(self, consulta: str, k: int = TOP_K,
               umbral: float = UMBRAL_MINIMO) -> list[Resultado]:
        """Los `k` fragmentos más similares que superen el umbral.

        Devuelve lista vacía si ninguno lo supera — que es una respuesta
        legítima, no un fallo: significa que el corpus no cubre esa pregunta.
        """
        if not consulta.strip() or len(self) == 0:
            return []
        v = embeber([consulta], self.modelo)[0]
        similitudes = self.vectores @ v            # coseno: ambos normalizados
        mejores = np.argsort(-similitudes)[:k]
        return [Resultado(self.fragmentos[i], float(similitudes[i]))
                for i in mejores if similitudes[i] >= umbral]

    # --- persistencia --------------------------------------------------------

    def guardar(self, ruta: Path = RUTA_INDICE) -> None:
        ruta.mkdir(parents=True, exist_ok=True)
        # float16 basta para similitud coseno y parte por dos el peso del
        # fichero que se versiona: importa, porque esto entra al repositorio.
        np.save(ruta / 'vectores.npy', self.vectores.astype(np.float16))
        (ruta / 'fragmentos.json').write_text(json.dumps({
            'modelo': self.modelo,
            'fragmentos': [
                {'texto': f.texto, 'fuente': f.fuente,
                 'seccion': f.seccion, 'orden': f.orden}
                for f in self.fragmentos
            ],
        }, ensure_ascii=False), encoding='utf-8')

    @classmethod
    def cargar(cls, ruta: Path = RUTA_INDICE) -> Indice:
        vec_path, meta_path = ruta / 'vectores.npy', ruta / 'fragmentos.json'
        if not vec_path.exists() or not meta_path.exists():
            raise RagError(
                f'no hay índice en {ruta}. Constrúyelo con: manage.py build_rag_index')
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        fragmentos = [Fragmento(**d) for d in meta['fragmentos']]
        vectores = np.load(vec_path).astype(np.float32)
        return cls(vectores, fragmentos, meta['modelo'])


_indice: Indice | None = None


def indice() -> Indice:
    """Índice cargado una sola vez por proceso (son ~2 MB en memoria)."""
    global _indice
    if _indice is None:
        _indice = Indice.cargar()
    return _indice


def construir(fragmentos: list[Fragmento], modelo: str = MODELO_POR_DEFECTO,
              progreso=None) -> Indice:
    """Embebe todos los fragmentos y devuelve el índice listo para guardar."""
    if not fragmentos:
        raise RagError('no hay fragmentos que indexar')
    vectores = embeber([f.con_contexto() for f in fragmentos], modelo,
                       progreso=progreso)
    return Indice(vectores, fragmentos, modelo)
