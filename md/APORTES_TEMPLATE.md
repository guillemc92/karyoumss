# Aportes Individuales por Release – Plantilla

**Propósito**: documentar las tareas concretas que cada integrante del grupo realizó dentro del release evaluable, para aplicar el **factor de aporte individual** que ajusta la nota grupal por persona. Esta plantilla se copia y completa por cada entregable evaluable: `docs/aportes/release-1.0.0.md` (S5), `docs/aportes/release-1.0.1.md` (S10) y `docs/aportes/release-2.0.0.md` (S12).

Audiencia: integrantes del grupo (autores), docente (revisor).

---

## 0\. Metadatos

| Campo | Valor |
| :---- | :---- |
| Producto | `<Nombre del producto del grupo>` |
| Grupo | `<G1/G2/G3/G4>` |
| Release evaluable | `release/1.0.0` · `release/1.0.1` · `release/2.0.0` (elegir uno) |
| Sesión asociada | `<S5 / S10 / S12>` |
| Fecha de cierre | `<dd/mm/aaaa>` |
| Integrantes del grupo (n) | `<lista nombres>` (n \= `<entero>`) |
| Branch del release | `<release/x.y.z>` |
| Commit de cierre (HEAD) | `<hash corto>` |

---

## 1\. Tabla de tareas atribuidas

Una fila por tarea concreta producida. Cada tarea debe poder verificarse en el repositorio (archivo+sección o commit). El grupo decide internamente quién hizo qué; el orden no importa, lo que importa es la **trazabilidad** y la **granularidad consistente** (ver §4).

| \# | Integrante | Tarea concreta | Categoría | Referencia | Fecha |
| :---- | :---- | :---- | :---- | :---- | :---- |
| 1 | `<Nombre>` | `<descripción breve, p. ej. "UC-007 Solicitud de trámite (flujo principal + Gherkin)">` | UC | `docs/fsd/FSD_v1.0.md` §4.7 / commit `abc1234` | `<dd/mm>` |
| 2 | `<Nombre>` | `<p. ej. "NFR-003 Latencia API p95 ≤ 300 ms">` | NFR | `docs/fsd/FSD_v1.0.md` §10 fila NFR-003 | `<dd/mm>` |
| 3 | `<Nombre>` | `<p. ej. "Diagrama de secuencia UC-007">` | Diagrama | `docs/diagrams/seq_uc_007.mmd` | `<dd/mm>` |
| … | … | … | … | … | … |

**Categorías admitidas** (usar exactamente uno de estos valores en la columna Categoría):

`BRD` · `MRD` · `PRD` · `FSD` · `UC` · `NFR` · `Gherkin` · `Diagrama` · `ADR` · `AGENTS` · `Skill` · `Rule` · `POC` · `Código` · `Test` · `Presentación` · `Bitácora` · `Prompt` · `Otro`

---

## 2\. Resumen por integrante

Conteo automático (o manual) de filas de §1 por integrante. Es la base del cálculo del factor.

| Integrante | Total de tareas | Categorías cubiertas (\#) | Observación |
| :---- | :---- | :---- | :---- |
| `<Nombre 1>` | `<n1>` | `<m1>` | `<opcional: ej. lideró calidad, escribió ADRs>` |
| `<Nombre 2>` | `<n2>` | `<m2>` | `<opcional>` |
| `<Nombre 3>` | `<n3>` | `<m3>` | `<opcional>` |
| … | … | … | … |
| **Total grupo** | **`<T>`** | — | — |

---

## 3\. Cálculo del factor de aporte individual

Fórmula estandarizada del módulo. Idéntica en los 3 releases evaluables.

aporte\_promedio\_grupo \= total\_tareas\_grupo / n\_integrantes

factor\_i              \= clamp(tareas\_i / aporte\_promedio\_grupo, 0.5, 1.1)

Nota\_individual\_i     \= Nota\_grupal × factor\_i

- **Piso**: `0.5` → quien aporta muy poco se lleva al menos la mitad de la nota grupal.  
- **Techo**: `1.1` → quien aporta mucho gana hasta \+10 % sobre la grupal.  
- **Caso `total_tareas_grupo = 0`** → todos en `0` (no hubo entrega real).  
- **Integrante ausente en §1** → factor \= `0.5` (clamp inferior aplicado).  
- **Integrante con justificación documentada de ausencia/baja contribución** → el docente decide caso por caso (puede elevar el piso o documentar excepción en §5).

### Aplicación

| Integrante | Tareas (de §2) | factor sin clamp \= tareas / promedio | factor (clamp 0.5–1.1) | Nota individual (Nota\_grupal × factor) |
| :---- | :---- | :---- | :---- | :---- |
| `<Nombre 1>` | `<n1>` | `<n1 / aporte_promedio>` | `<f1>` | `<Nota_grupal × f1>` |
| `<Nombre 2>` | `<n2>` | `<n2 / aporte_promedio>` | `<f2>` | `<Nota_grupal × f2>` |
| … | … | … | … | … |

**Aporte promedio del grupo**: `<T> / <n> = <aporte_promedio>` tareas/persona.

### Ejemplo numérico

Grupo de 4 integrantes, total 20 tareas, nota grupal \= 80/100.

| Integrante | Tareas | Sin clamp | Con clamp | Nota individual |
| :---- | :---- | :---- | :---- | :---- |
| Ana | 10 | 10/5 \= 2.0 | 1.10 | 88 |
| Beto | 6 | 6/5 \= 1.2 | 1.10 | 88 |
| Carla | 3 | 3/5 \= 0.6 | 0.60 | 48 |
| Dani | 1 | 1/5 \= 0.2 | 0.50 | 40 |

(Aporte promedio \= 20/4 \= 5 tareas.)

---

## 4\. Reglas del grupo sobre qué cuenta como tarea

Granularidad estándar recomendada por el módulo. El grupo puede afinar pero no relajar.

- **Un UC** (con flujo principal \+ alterno \+ Gherkin) \= 1 tarea.  
- **Un NFR ISO 25010** cuantificable con métrica \+ umbral \+ verificación \= 1 tarea.  
- **Un diagrama Mermaid** (`.mmd`) versionado y coherente con FSD \= 1 tarea.  
- **Una sección de un documento** del nivel `##` (BRD/MRD/PRD/FSD/DTI) con contenido sustantivo \= 1 tarea.  
- **Un ADR aceptado** \= 1 tarea.  
- **Una POC ejecutada con evidencia** \= 1 tarea.  
- **Un skill propio** (`docs/skills/<skill>.md`) accionable \= 1 tarea.  
- **Una cursor rule** (`.cursor/rules/<dominio>.mdc`) específica del dominio \= 1 tarea.  
- **Un prompt-contrato** con los 6 elementos \+ Invariants \+ Failure modes \= 1 tarea.  
- **Una user story** INVEST con criterios de aceptación \= 1 tarea.  
- **Una sección de bitácora** o **una sesión de demo** preparada y entregada \= 1 tarea.  
- **Una función o módulo no trivial de código** (con su prueba) \= 1 tarea.  
- **Co-autoría**: si dos personas hicieron la misma tarea de forma sustantiva, registrarla **dos veces** (una por autor) con la observación `co-autoría con <otro>`.

No cuentan: cambios cosméticos, correcciones tipográficas aisladas, commits de configuración sin contenido sustantivo, copiar/pegar de otra fuente sin adaptación.

---

## 5\. Auditoría del docente (opcional)

Espacio para que el docente registre observaciones, ajustes manuales o justificaciones aprobadas. Si está vacío, se aplica el cálculo automático de §3.

| Integrante | Factor calculado (§3) | Factor final aplicado | Justificación del ajuste |
| :---- | :---- | :---- | :---- |
| `<Nombre>` | `<f_i>` | `<f_i ajustado>` | `<razón documentada>` |

---

## 6\. Checklist de cierre del release

- [ ] §0 Metadatos completos con `n_integrantes` y branch del release.  
- [ ] §1 Cada tarea tiene Integrante, Categoría y Referencia verificable.  
- [ ] §2 Suma de tareas por integrante \= total del grupo.  
- [ ] §3 Aporte promedio y factor calculado para cada integrante.  
- [ ] §4 El grupo confirma que respetó la granularidad estándar (o documentó las diferencias).  
- [ ] Archivo commiteado en el branch del release (`release/1.0.0`, `release/1.0.1` o `release/2.0.0`) antes del cierre.

