# -*- coding: utf-8 -*-
"""Convierte el documento de Evals (HTML generado) a Markdown editable.

    python scripts/html_a_md.py docs/M7_Evals_BIOMED/M7_Evals_BIOMED.html salida.md

Existe para que el autor pueda dar formato al documento a mano. Parte del HTML
ya generado —no de una transcripcion— para que las cifras sean las mismas que
las del PDF. Cubre solo las etiquetas que usa ese documento.

OJO: la consigna de Evals penaliza con 20 puntos entregar el documento en .md.
Este fichero es para EDITAR; lo que se entrega es el PDF.
"""
import io
import re
import sys
from html.parser import HTMLParser


class AMarkdown(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.salida = []          # bloques ya terminados
        self.buf = []             # texto en linea del bloque actual
        self.ignorar = 0          # dentro de <style>/<title>/<head>
        self.listas = []          # pila: 'ul' | 'ol' con contador
        self.tabla = None         # lista de filas; cada fila, lista de celdas
        self.celda = None
        self.en_pre = False
        self.clase_p = ''

    # ------------------------------------------------------------- utilidades
    def _texto(self):
        t = ''.join(self.buf)
        self.buf = []
        return re.sub(r'[ \t\r\n]+', ' ', t).strip()

    def _bloque(self, texto):
        if texto:
            self.salida.append(texto)

    # ------------------------------------------------------------- etiquetas
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('style', 'title', 'head', 'script'):
            self.ignorar += 1
            return
        if self.ignorar:
            return
        if tag in ('h1', 'h2', 'h3', 'p'):
            self._bloque(self._texto())
            self.clase_p = a.get('class', '')
        elif tag in ('ul', 'ol'):
            self._bloque(self._texto())
            self.listas.append([tag, 0])
        elif tag == 'li':
            self._bloque(self._texto())
            self.listas[-1][1] += 1
        elif tag == 'table':
            self._bloque(self._texto())
            self.tabla = []
        elif tag == 'tr' and self.tabla is not None:
            self.tabla.append([])
        elif tag in ('td', 'th') and self.tabla is not None:
            self.celda = []
        elif tag == 'br':
            (self.celda if self.celda is not None else self.buf).append(
                ' / ' if self.celda is not None else '  \n')
        elif tag == 'pre':
            self._bloque(self._texto())
            self.en_pre = True
        elif tag in ('b', 'strong'):
            self._poner('**')
        elif tag in ('i', 'em'):
            self._poner('*')
        elif tag == 'code' and not self.en_pre:
            self._poner('`')
        elif tag == 'img':
            self._bloque(self._texto())
            self._bloque('![%s](%s)' % (a.get('alt', ''), a.get('src', '')))

    def handle_endtag(self, tag):
        if tag in ('style', 'title', 'head', 'script'):
            self.ignorar -= 1
            return
        if self.ignorar:
            return
        if tag == 'h1':
            self._bloque('# ' + self._texto())
        elif tag == 'h2':
            self._bloque('## ' + self._texto())
        elif tag == 'h3':
            self._bloque('### ' + self._texto())
        elif tag == 'p':
            t = self._texto()
            if t and 'linea' in self.clase_p:
                t = '> ' + t
            elif t and 'nota' in self.clase_p:
                t = '*' + t + '*' if not t.startswith('*') else t
            self._bloque(t)
            self.clase_p = ''
        elif tag == 'li':
            tipo, n = self.listas[-1]
            marca = '%d.' % n if tipo == 'ol' else '-'
            self._bloque('%s %s' % (marca, self._texto()))
        elif tag in ('ul', 'ol'):
            self._bloque(self._texto())
            self.listas.pop()
            self.salida.append('')
        elif tag in ('td', 'th') and self.celda is not None:
            t = re.sub(r'\s+', ' ', ''.join(self.celda)).strip().replace('|', '\\|')
            self.tabla[-1].append(t)
            self.celda = None
        elif tag == 'table' and self.tabla is not None:
            filas = [f for f in self.tabla if f]
            if filas:
                ancho = max(len(f) for f in filas)
                filas = [f + [''] * (ancho - len(f)) for f in filas]
                lineas = ['| ' + ' | '.join(filas[0]) + ' |',
                          '|' + '---|' * ancho]
                lineas += ['| ' + ' | '.join(f) + ' |' for f in filas[1:]]
                self._bloque('\n'.join(lineas))
            self.tabla = None
        elif tag == 'pre':
            self._bloque('```\n' + ''.join(self.buf).strip('\n') + '\n```')
            self.buf = []
            self.en_pre = False
        elif tag in ('b', 'strong'):
            self._poner('**')
        elif tag in ('i', 'em'):
            self._poner('*')
        elif tag == 'code' and not self.en_pre:
            self._poner('`')
        elif tag == 'div':
            self._bloque(self._texto())

    def _poner(self, marca):
        (self.celda if self.celda is not None else self.buf).append(marca)

    def handle_data(self, data):
        if self.ignorar:
            return
        (self.celda if self.celda is not None else self.buf).append(data)

    def resultado(self):
        self._bloque(self._texto())
        texto = '\n\n'.join(b for b in self.salida)
        texto = re.sub(r'\n{3,}', '\n\n', texto)
        # Solo marcas vacias. No tocar espacios junto a `**`: no se distingue
        # una negrita que abre de una que cierra, y quitar el espacio pegaba
        # la palabra siguiente («**codigo 0.**v1»).
        texto = texto.replace('****', '')
        return texto.strip() + '\n'


def main():
    entrada, salida = sys.argv[1], sys.argv[2]
    p = AMarkdown()
    p.feed(io.open(entrada, encoding='utf-8').read())
    io.open(salida, 'w', encoding='utf-8', newline='\n').write(p.resultado())
    print('escrito %s' % salida)
    return 0


if __name__ == '__main__':
    sys.exit(main())
