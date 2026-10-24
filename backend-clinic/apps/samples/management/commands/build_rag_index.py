"""Construye el indice del RAG desde los documentos declarados en rag_corpus.

    python manage.py build_rag_index
    python manage.py build_rag_index --modelo mxbai-embed-large

Necesita Ollama corriendo con el modelo de embeddings descargado. El indice
resultante se guarda en apps/samples/rag_data/ y se versiona con el codigo: la
consigna pide un "indice consultable corriendo en el repositorio".

Salida en ASCII (consola Windows cp1252).
"""
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.samples.rag_corpus import FUENTES, cargar_fuentes
from apps.samples.rag_index import MODELO_POR_DEFECTO, RUTA_INDICE, construir

# manage.py vive en backend-clinic/; los documentos, en la raiz del repo.
RAIZ = Path(__file__).resolve().parents[5]


class Command(BaseCommand):
    help = 'Carga, trocea, embebe e indexa el corpus documental del RAG.'

    def add_arguments(self, parser):
        parser.add_argument('--modelo', default=MODELO_POR_DEFECTO,
                            help='modelo de embeddings de Ollama')
        parser.add_argument('--salida', default=str(RUTA_INDICE),
                            help='carpeta donde guardar el indice')

    def handle(self, *args, **opts):
        self.stdout.write(f'raiz del repositorio: {RAIZ}')

        # --- pasos 1 y 2: cargar y trocear con solape ------------------------
        self.stdout.write('Cargando y troceando...')
        fragmentos = cargar_fuentes(RAIZ, FUENTES)
        if not fragmentos:
            self.stderr.write('No se encontro ningun documento. Revisa FUENTES.')
            return

        por_fuente = {}
        for f in fragmentos:
            etiqueta = f.fuente.split(':')[0]
            por_fuente[etiqueta] = por_fuente.get(etiqueta, 0) + 1
        for etiqueta, n in sorted(por_fuente.items(), key=lambda kv: -kv[1]):
            self.stdout.write(f'   {etiqueta:14} {n:>5} fragmentos')
        total_chars = sum(len(f.texto) for f in fragmentos)
        self.stdout.write(f'   {"TOTAL":14} {len(fragmentos):>5} fragmentos '
                          f'({total_chars / 1000:.0f}K caracteres)')

        # --- pasos 3 y 4: embeber e indexar ----------------------------------
        modelo = opts['modelo']
        self.stdout.write(f'\nEmbebiendo con {modelo} (puede tardar unos minutos)...')
        def progreso(hechos, total):
            if hechos % 160 == 0 or hechos == total:
                self.stdout.write(f"   {hechos:>5}/{total} fragmentos embebidos")
                self.stdout.flush()

        indice = construir(fragmentos, modelo, progreso=progreso)

        salida = Path(opts['salida'])
        indice.guardar(salida)

        peso = sum(p.stat().st_size for p in salida.glob('*')) / 1e6
        self.stdout.write('')
        self.stdout.write(f'Indice construido: {len(indice)} fragmentos, '
                          f'{indice.vectores.shape[1]} dimensiones')
        self.stdout.write(f'   guardado en {salida}  ({peso:.1f} MB)')
        self.stdout.write('')
        self.stdout.write('Siguiente: manage.py eval_rag  (mide contra el banco)')
