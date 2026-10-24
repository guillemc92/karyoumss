"""Carga y troceado del corpus documental para el RAG.

Pasos 1 y 2 del pipeline: **cargar** los documentos base y **trocearlos con
solape**. Lógica pura —sin red, sin base de datos, sin Ollama— para poder
probarla y razonarla por separado del resto.

## Qué se indexa, y por qué esto y no la base de datos

ADR-0027 midió la búsqueda vectorial sobre datos **estructurados** (enrutar
preguntas a herramientas) y rindió ~60%: se rechazó, y ADR-0028 la sustituyó por
búsqueda determinística por clave. Ese hallazgo sigue vigente y no se reabre.

El RAG entra donde esa clave exacta **no existe**: preguntas sobre el dominio y
sus reglas, que hoy el sistema no puede responder. Del banco de 56 preguntas de
`eval_enrutado`, seis son exactamente de este tipo y todas caen en «no sé»:

    «¿Qué significa que un cromosoma esté naranja?»
    «¿Cómo se calcula la nomenclatura ISCN?»
    «¿Quién tiene permiso para firmar un caso?»
    «¿Qué umbral de confianza deberíamos usar?»

Son preguntas de documentación, no de estado. El estado lo siguen resolviendo
las herramientas (`tools.py`), que para eso son exactas y cuestan milisegundos.

## Troceado por secciones, no por longitud ciega

Cortar cada N caracteres parte definiciones por la mitad y produce fragmentos
que empiezan a media frase. Como todas las fuentes son Markdown con encabezados,
se trocea **respetando la jerarquía de secciones** y solo se subdivide cuando una
sección excede el tamaño máximo. Cada fragmento arrastra su cadena de
encabezados, que sirve para dos cosas: da contexto al modelo de embeddings y
permite citar la procedencia exacta (§ del ISCN, ADR concreto) en la respuesta.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# ~4 caracteres por token en castellano/inglés técnico. La consigna pide
# fragmentos de unos 500 tokens; el solape evita que una definición que cae
# justo en la frontera quede partida y sea irrecuperable por ambos lados.
MAX_CHARS = 2000
SOLAPE_CHARS = 300
MIN_CHARS = 120          # por debajo de esto el fragmento no aporta contexto

_ENCABEZADO_RE = re.compile(r'^(#{1,6})\s+(.*?)\s*#*$')


@dataclass(frozen=True)
class Fragmento:
    """Un trozo indexable, con lo necesario para citarlo después."""

    texto: str
    fuente: str          # nombre legible del documento
    seccion: str         # cadena de encabezados: «5 Nomenclatura > 5.2 Sexo»
    orden: int           # posición dentro del documento

    @property
    def clave(self) -> str:
        return f'{self.fuente}#{self.orden}'

    def con_contexto(self) -> str:
        """Texto que se embebe: el fragmento precedido de dónde vive.

        Sin esto, un fragmento que dice «se escribe primero el sexo» no se
        parece a la pregunta «¿cómo se calcula el ISCN?». Con la sección
        delante, sí.
        """
        cabecera = f'{self.fuente} — {self.seccion}' if self.seccion else self.fuente
        return f'{cabecera}\n\n{self.texto}'


def _limpia(texto: str) -> str:
    """Quita ruido de conversión que no aporta y sí ocupa contexto."""
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    texto = re.sub(r'[ \t]{2,}', ' ', texto)
    return texto.strip()


def _subdivide(texto: str, maximo: int, solape: int) -> list[str]:
    """Parte un bloque largo en trozos con solape, cortando por frase.

    Se busca el final de frase más cercano al límite en vez de cortar en seco:
    un fragmento que empieza a media oración confunde tanto al modelo de
    embeddings como al lector que ve la cita.
    """
    if len(texto) <= maximo:
        return [texto]

    trozos: list[str] = []
    inicio = 0
    while inicio < len(texto):
        fin = min(inicio + maximo, len(texto))
        if fin < len(texto):
            # Retroceder hasta un final de frase razonable dentro del último 30%.
            ventana = texto[inicio + int(maximo * 0.7):fin]
            corte = max(ventana.rfind('. '), ventana.rfind('.\n'), ventana.rfind('\n\n'))
            if corte != -1:
                fin = inicio + int(maximo * 0.7) + corte + 1
        trozo = texto[inicio:fin].strip()
        if trozo:
            trozos.append(trozo)
        if fin >= len(texto):
            break
        inicio = max(fin - solape, inicio + 1)
    return trozos


def trocear_markdown(contenido: str, fuente: str,
                     maximo: int = MAX_CHARS,
                     solape: int = SOLAPE_CHARS) -> list[Fragmento]:
    """Trocea un Markdown respetando su jerarquía de encabezados."""
    pila: list[str] = []            # cadena de encabezados vigente
    buffer: list[str] = []
    fragmentos: list[Fragmento] = []

    def volcar():
        cuerpo = _limpia('\n'.join(buffer))
        buffer.clear()
        if len(cuerpo) < MIN_CHARS:
            return
        seccion = ' > '.join(pila)
        for trozo in _subdivide(cuerpo, maximo, solape):
            if len(trozo) >= MIN_CHARS:
                fragmentos.append(Fragmento(
                    texto=trozo, fuente=fuente, seccion=seccion,
                    orden=len(fragmentos),
                ))

    for linea in contenido.splitlines():
        m = _ENCABEZADO_RE.match(linea)
        if m:
            volcar()
            nivel = len(m.group(1))
            titulo = re.sub(r'[*_`]', '', m.group(2)).strip()
            del pila[nivel - 1:]
            pila.append(titulo)
        else:
            buffer.append(linea)
    volcar()
    return fragmentos


def cargar_fuentes(raiz: Path, rutas: list[tuple[str, str]]) -> list[Fragmento]:
    """Carga y trocea la lista declarada de documentos.

    `rutas` es una lista de (patrón glob relativo a `raiz`, etiqueta). Los
    ficheros que no existan se ignoran en silencio: el corpus documental de un
    proyecto cambia, y que falte un documento no debe romper la construcción del
    índice — solo empobrecerlo.
    """
    fragmentos: list[Fragmento] = []
    for patron, etiqueta in rutas:
        for ruta in sorted(raiz.glob(patron)):
            if not ruta.is_file():
                continue
            try:
                contenido = ruta.read_text(encoding='utf-8')
            except (UnicodeDecodeError, OSError):
                continue
            nombre = f'{etiqueta}: {ruta.name}' if etiqueta else ruta.name
            fragmentos.extend(trocear_markdown(contenido, nombre))
    return fragmentos


# Los documentos que se indexan. Se declara aquí y no se descubre solo: un
# corpus que crece por accidente es un corpus que nadie revisó.
FUENTES: list[tuple[str, str]] = [
    ('ISCN 2024.md', 'ISCN 2024'),          # el estándar internacional
    ('docs/adr/*.md', 'ADR'),               # las decisiones de arquitectura
    ('AGENTS.md', 'Guía'),                  # reglas de negocio RN-01..RN-09
    ('docs/fsd/*.md', 'FSD'),               # especificación funcional
    ('docs/brd/*.md', 'BRD'),               # requisitos de negocio
]
