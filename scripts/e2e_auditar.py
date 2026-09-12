# -*- coding: utf-8 -*-
"""Primer barrido de las cinco preguntas sobre los tests generados.

    python scripts/e2e_auditar.py

## Esto NO es la auditoria

Es un cedazo: encuentra los antipatrones que se pueden reconocer por texto y
deja el resto para la persona. La auditoria de verdad se hace leyendo cada
test, y la consigna la pide asi — una fila por test, con la pregunta que fallo
y que se cambio.

**Y hay motivo para decirlo en grande.** La primera version de este guion marco
E2E-01, E2E-09 y E2E-10 como «0 fallos». Leidos a mano:

  E2E-09  selector CSS `input[name="search"]`, `waitForSelector` en vez de
          `expect`, recorre CUATRO pantallas en un test, y hace `.id` sobre un
          string. Falla 1, 2, 4 y 5.
  E2E-10  se titula «sin token» y lo primero que hace es sembrar un token.
          Ademas usa `locator(...).expect('text', 'X')`, que no existe en
          Playwright. Falla 3 de la peor forma: no verifica lo que promete.

Las regex eran demasiado estrechas. Octava vez en este proyecto que la primera
medicion falla por el instrumento y no por lo medido, asi que el guion imprime
su propia limitacion en cada corrida en vez de fingir un veredicto.

Salida en ASCII puro (la consola de Windows rompe con Unicode).
"""
import glob
import io
import os
import re
import sys

#: (numero, nombre, patron). El texto de cada pregunta sale de AUDITORIA_E2E.md
#: del laboratorio, no de una parafrasis mia.
PREGUNTAS = [
    (1, 'localizador que NO es lo que ve una persona',
     r"""page\.(locator|fill|click)\(['"][#.\[]|nth-child|xpath=|>>"""),
    (2, 'espera fija',
     r'waitForTimeout|setTimeout\(|sleep\(|waitForSelector'),
    (3, 'asegura la redaccion del modelo, no lo que promete la interfaz',
     r"""toHaveText\(\s*['"][^'"]{60,}|toContain\(['"][^'"]{50,}"""),
    (4, 'ni pequeno ni independiente',
     r'test\.describe\.serial|\.only\('),
    (5, 'datos que no son del propio test',
     r'\.id\b(?!\s*=)'),
]

#: Fallos que no se ven con una regex sobre el cuerpo, pero si contando.
def fallos_estructurales(texto):
    malos = []
    if 'expect(' not in texto:
        malos.append((3, 'no hay ni un expect: navega sin comprobar'))
    # Mas de dos `goto` distintos = esta recorriendo media aplicacion.
    rutas = set(re.findall(r"goto\(\s*[`'\"]([^`'\"]+)", texto))
    if len(rutas) > 2:
        malos.append((4, 'recorre %d pantallas en un solo test' % len(rutas)))
    # `.expect(` colgando de un locator no existe en Playwright.
    if re.search(r'locator\([^)]*\)\.expect\(', texto):
        malos.append((3, 'usa locator().expect(), que no existe en Playwright'))
    return malos


def main():
    ficheros = sorted(glob.glob('frontend-clinic/tests/agente/*.spec.ts'))
    if not ficheros:
        raise SystemExit('no hay tests generados que auditar')

    print('CEDAZO de las cinco preguntas — NO sustituye a leer cada test')
    print('=' * 76)
    print('%-16s %-7s %s' % ('fichero', 'fallan', 'detalle'))
    print('-' * 76)

    total_con_fallo = 0
    for ruta in ficheros:
        texto = io.open(ruta, encoding='utf-8').read()
        malos = []
        for numero, nombre, patron in PREGUNTAS:
            if re.search(patron, texto):
                malos.append((numero, nombre))
        malos += fallos_estructurales(texto)

        numeros = sorted({n for n, _ in malos})
        if numeros:
            total_con_fallo += 1
        print('%-16s %-7s %s'
              % (os.path.basename(ruta),
                 ','.join(str(n) for n in numeros) or '-',
                 '; '.join(d for _, d in malos)[:44] or 'nada detectado POR TEXTO'))

    print('-' * 76)
    print('  ficheros con al menos un fallo detectado: %d de %d'
          % (total_con_fallo, len(ficheros)))
    print()
    print('  AVISO: «nada detectado» NO significa aceptado. La primera version')
    print('  de este cedazo dio limpios E2E-01, E2E-09 y E2E-10, y los tres')
    print('  fallaban cuatro preguntas al leerlos. El veredicto lo pone la')
    print('  persona, test por test, en la tabla del entregable.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
