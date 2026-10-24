"""Fase C5 — re-exporta los cariogramas desde la base MetaClass real (ADR-0007).

La base `SCAMC.mdf` del laboratorio creció de 460 a **1113** análisis con imagen.
Este script vuelca `SCAAnalisisCariotipos.ImagenCariotipo` (y opcionalmente
`ImagenMetafase`) a `datasets/metaclass/cariogramas/`, con el mismo naming que
espera `extract_labels.py` (`cario_{IdAnalisis}.bmp`), de modo que la Fase C1
corre después sin cambios.

**No extrae PII** (RN-03): solo imágenes e IDs internos. Nombres, NHC y fechas de
nacimiento viven en `SCAPersona` y NO se tocan.

Requiere SQL Server Express corriendo y `sqlcmd` en el PATH (viene con el Client
SDK de SQL Server). Se usa `sqlcmd` en vez de pyodbc para no agregar una
dependencia nativa solo para un volcado que se hace una vez.

Uso:
  python export_from_mdf.py                 # exporta cariogramas nuevos
  python export_from_mdf.py --metafases     # también las metafases
  python export_from_mdf.py --force         # re-exporta los ya existentes
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DATASET = Path(__file__).resolve().parents[2] / 'datasets' / 'metaclass'
CARIO_DIR = DATASET / 'cariogramas'
META_DIR = DATASET / 'metafases'

SERVER = r'.\SQLEXPRESS'
DATABASE = 'SCAMC'


def _sqlcmd(query: str) -> str:
    """Ejecuta una consulta y devuelve stdout como texto."""
    proc = subprocess.run(
        ['sqlcmd', '-S', SERVER, '-E', '-d', DATABASE, '-h', '-1', '-W', '-s', '|', '-Q', query],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f'sqlcmd falló: {proc.stderr.strip()}')
    return proc.stdout


def listar_ids(columna: str) -> list[int]:
    """IDs de los análisis con imagen utilizable en `columna`."""
    out = _sqlcmd(
        f'SET NOCOUNT ON; SELECT IdAnalisis FROM SCAAnalisisCariotipos '
        f'WHERE {columna} IS NOT NULL AND DATALENGTH({columna}) > 1000 ORDER BY IdAnalisis;'
    )
    ids = []
    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            ids.append(int(line))
    return ids


def exportar(id_analisis: int, columna: str, destino: Path) -> bool:
    """Vuelca una imagen a disco vía BCP. Devuelve True si quedó un archivo válido.

    Se usa `bcp` con formato nativo -N: `sqlcmd` no puede emitir binario crudo sin
    corromperlo (hexadecimal + saltos de línea), y convertir varios GB de hex en
    Python sería innecesariamente lento.
    """
    query = (
        f'SELECT {columna} FROM {DATABASE}.dbo.SCAAnalisisCariotipos '
        f'WHERE IdAnalisis = {id_analisis}'
    )
    proc = subprocess.run(
        ['bcp', query, 'queryout', str(destino), '-S', SERVER, '-T', '-N'],
        capture_output=True, text=True,
    )
    if proc.returncode != 0 or not destino.exists():
        return False
    # BCP en formato nativo antepone un prefijo de longitud de 4 bytes al blob.
    data = destino.read_bytes()
    if len(data) > 4 and data[4:6] == b'BM':      # cabecera BMP tras el prefijo
        destino.write_bytes(data[4:])
    elif data[:2] != b'BM':
        destino.unlink(missing_ok=True)
        return False
    return True


def correr(columna: str, carpeta: Path, prefijo: str, force: bool) -> None:
    carpeta.mkdir(parents=True, exist_ok=True)
    ids = listar_ids(columna)
    print(f'{columna}: {len(ids)} análisis con imagen en la base')

    nuevos = ok = fallidos = 0
    for i, id_analisis in enumerate(ids, 1):
        destino = carpeta / f'{prefijo}_{id_analisis}.bmp'
        if destino.exists() and not force:
            continue
        nuevos += 1
        if exportar(id_analisis, columna, destino):
            ok += 1
        else:
            fallidos += 1
            print(f'  ! falló IdAnalisis={id_analisis}')
        if nuevos % 50 == 0:
            print(f'  ... {ok} exportados ({i}/{len(ids)} revisados)')

    existentes = len(list(carpeta.glob(f'{prefijo}_*.bmp')))
    print(f'{columna}: {ok} nuevos, {fallidos} fallidos -> {existentes} archivos en {carpeta.name}/')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--metafases', action='store_true', help='exportar también ImagenMetafase')
    ap.add_argument('--force', action='store_true', help='re-exportar los ya existentes')
    args = ap.parse_args()

    try:
        _sqlcmd('SET NOCOUNT ON; SELECT 1;')
    except (RuntimeError, FileNotFoundError) as exc:
        print(f'ERROR: no se pudo conectar a {SERVER}/{DATABASE}: {exc}')
        print('Verifica que el servicio MSSQL$SQLEXPRESS esté corriendo.')
        return 1

    correr('ImagenCariotipo', CARIO_DIR, 'cario', args.force)
    if args.metafases:
        correr('ImagenMetafase', META_DIR, 'metafase', args.force)

    print()
    print('Siguiente paso: python extract_labels.py   (re-genera los crops etiquetados)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
