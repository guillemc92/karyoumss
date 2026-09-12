---
id: ADR-NNNN
title: Frase que dice la decisión, no el tema
date: AAAA-MM-DD
status: proposed
related: []
---

# ADR-NNNN: Título

## Contexto

Qué situación obliga a decidir. Hechos, no opiniones.

Si hay medición previa, va aquí con el comando que la reproduce:

    python training/mi_evaluador.py --casos 30

Si **no** hay medición y la decisión la necesita, decirlo: es un motivo
legítimo para diferir (ver ADR-0007 y ADR-0035).

## Decisión

### D1 — Una frase que se pueda citar

El detalle debajo. Una decisión por bloque, numerada, para poder referenciarla
desde el código: `# ADR-NNNN D1: ...`.

### D2 — …

## Cómo se sabrá si funcionó

Sin criterio de éxito esto no es una decisión, es una intención.

- Métrica primaria, y contra qué línea base
- El comando que la mide
- Qué resultado haría reconsiderar esta ADR

## Consecuencias

**A favor**

- Lo que mejora, con número si lo hay.

**En contra, y hay que decirlo**

- Lo que empeora, lo que queda sin resolver, y los supuestos que podrían caerse.
- Esta sección vacía es señal de que la ADR no está terminada.

## Alternativas descartadas

**Nombre de la alternativa.** Por qué no. Descartar sin explicar el porqué
convierte la ADR en un anuncio en vez de en un registro.

## Pendiente antes de pasar a `accepted`

1. …

---

## Recordatorios de este proyecto

Borrar esta sección al escribir la ADR.

- **AGENTS.md manda.** Si la decisión contradice una regla constitucional
  (§11: nada de Mask R-CNN ni ResNet50; RN-01…RN-09), hay que **derogarla
  nominalmente** y actualizar `AGENTS.md` en el mismo cambio. Contradecirla en
  silencio invalida la ADR.
- **Toda cifra lleva el comando que la reproduce.** Sin excepción.
- **Cuidado con medir y ajustar sobre el mismo banco.** Ya pasó: ADR-0033
  proponía una penalización que rendía la mitad en datos nuevos. Si se ajusta
  un parámetro, se comprueba en un conjunto que no participó en elegirlo.
- **Usar el nivel mínimo que resuelva el problema.** Un agente donde bastaba un
  `if` resta (ADR-0031); NumPy donde no hacía falta ChromaDB (ADR-0029 D3).
- **El modelo propone, el código decide.** Es la regla que mejor ha funcionado
  en este sistema (ADR-0024 D1, ADR-0033).
- **Si toca datos de paciente**, decir explícitamente cómo se cumple RN-03.
- **Si toca el cariotipo o la bitácora**, decir cómo se cumplen RN-04 y RN-05.
- Al terminar: `python docs/adr/generar_indice.py`
