# Business Requirements Document (BRD) – Plantilla

**Propósito del BRD**: formalizar las **necesidades y restricciones de negocio** que justifican la existencia del producto, *independientemente de la solución técnica*. Responde a **"¿qué necesita el negocio y por qué?"**.

**Alcance en este módulo**: en este Módulo 4, **todos los grupos entregan BRD** como primer documento de la cadena `BRD → MRD → PRD → FSD → DTI`. El BRD captura la visión del *sponsor*; el MRD profundizará luego la mirada de mercado y competencia.

El BRD debe alinearse al marco conceptual visto en S02 (método científico aplicado al software): aquí formulamos la **etapa "Problema"** —qué dolor real resolvemos y por qué importa— antes de pasar a la abstracción de producto en MRD/PRD.

---

## 0\. Metadatos

| Campo | Valor |
| :---- | :---- |
| Producto | `<Nombre>` |
| Grupo | `<identificador del grupo, p. ej. G07>` |
| Versión | `v0.1` |
| Fecha | `<dd/mm/aaaa>` |
| Sponsor de negocio | `<nombre + cargo>` |
| Stakeholders | `<lista>` |
| Autores | `<…>` |
| Revisores | Docente \+ 1 grupo par |
| Estado | Borrador / En revisión / Aprobado |
| Insumo del Módulo Anterior (M2 UI/UX) | `<ruta a 01_Vision_de_Negocio_*.md u otros entregables M2 que alimentan este BRD>` |
| Prompts utilizados | `<IDs de docs/PROMPT_MAPPING.md, p. ej. PR-BRD-001>` (vacío si no se usó IA) |

## 1\. Resumen ejecutivo

Síntesis de **½ página** (escribirla al final, una vez completadas las secciones 2–17). Debe permitir que un *sponsor* o decisor entienda en menos de 2 minutos:

- **Problema**: una frase que nombre el dolor con su evidencia más fuerte.  
- **Propuesta**: qué construiremos a alto nivel, en lenguaje de negocio.  
- **Valor esperado**: 2–3 cifras objetivas (ahorro, ingreso, tiempo, NPS, etc.).  
- **Métricas clave de éxito**: 2–3 KPIs con meta cuantificada y horizonte.  
- **Llamada a la acción**: qué se requiere del *sponsor* para avanzar (presupuesto, decisiones, accesos).

## 2\. Contexto del negocio

- **Organización**: `<entidad>`.  
- **Unidad impactada**: `<área>`.  
- **Proceso(s) de negocio afectado(s)**: `<…>`.  
- **Estrategia de la organización** que justifica el proyecto (objetivo estratégico vinculado).

## 3\. Problema y oportunidad de negocio

### 3.1 Problema

Describir en 150–250 palabras el **dolor actual**: síntomas, causas raíz, evidencia cuantitativa (tiempos, costos, errores, quejas) y consecuencia de no actuar.

### 3.2 Oportunidad

- Valor económico estimado (ahorro, ingresos, evitación de pérdidas).  
- Valor estratégico / reputacional.  
- Ventana de oportunidad (time‑to‑value).

### 3.3 Evidencia de Continuous Discovery

Vincula este BRD al **track de Discovery** del Dual‑Track Agile (ver S04 §B6). El BRD no se escribe en el vacío: se sostiene en evidencia de campo.

- **Documento de Discovery**: `docs/discovery/discovery_v0.1.md` (entregable de S03).  
- **Entrevistas realizadas**: `<n>` con `<perfiles>` (resumen en anexo).  
- **Hipótesis principales validadas / refutadas**: enlazar a la sección correspondiente del documento de Discovery.  
- **Artefactos M2 (UI/UX)** que sustentan la propuesta: `<wireframes, journeys, use cases del módulo anterior>`.  
- **Próxima cadencia de Discovery**: `<semanal / quincenal>` durante la iteración del producto.

## 4\. Usuarios objetivo / Personas clave

Identifiquen los **1 o 2 usuarios principales** del sistema desde la perspectiva del negocio (no técnica). Profundizarán este análisis en el MRD y PRD; aquí basta con caracterizarlos lo suficiente para validar la propuesta de valor.

### 4.1 Persona principal

| Atributo | Valor |
| :---- | :---- |
| Nombre / rol | `<p. ej. Estudiante de pregrado UMSS>` |
| Contexto | `<dónde y cómo interactúa con el proceso actual>` |
| *Jobs‑to‑be‑done* | `<3–5 tareas que necesita lograr>` |
| Dolores principales | `<filas, demoras, falta de información, etc.>` |
| Ganancia esperada | `<qué espera obtener si el sistema funciona>` |

### 4.2 Persona secundaria (opcional)

| Atributo | Valor |
| :---- | :---- |
| Nombre / rol | `<p. ej. Funcionario de la Dirección Académica>` |
| Contexto | `<…>` |
| *Jobs‑to‑be‑done* | `<…>` |
| Dolores principales | `<…>` |
| Ganancia esperada | `<…>` |

## 5\. Propuesta de valor

Síntesis tipo *Value Proposition Canvas* (Osterwalder). Debe poder leerse de pie.

| Eje | Contenido |
| :---- | :---- |
| **Para quién** (cliente / usuario principal) | `<segmento concreto>` |
| **Que necesita** (*job‑to‑be‑done*) | `<tarea funcional, emocional o social que quiere completar>` |
| **Nuestra propuesta es** (producto / servicio) | `<una frase>` |
| **Que le aporta** (*pain relievers* \+ *gain creators*) | `<3–5 bullets verificables>` |
| **A diferencia de** (alternativa actual) | `<qué hace hoy o cómo lo resuelve sin nosotros>` |
| **Nuestro diferencial es** (*unique value*) | `<por qué somos preferibles>` |

## 6\. Panorama competitivo (resumen)

Visión sintética suficiente para sustentar el BRD. El **análisis profundo** vive en el MRD; aquí basta con ubicar el producto.

| Competidor / alternativa | Tipo (directo / indirecto / *do‑nothing*) | Fortaleza percibida | Debilidad percibida |
| :---- | :---- | :---- | :---- |
| `<Sistema legado actual>` | *do‑nothing* | conocido por los usuarios | manual, sin trazabilidad |
| `<Competidor 1>` | directo | UX moderna | costo |
| `<Competidor 2>` | indirecto | datos integrados | no cubre el caso boliviano |

Nota: este resumen se complementa con la sección de competencia del MRD (`docs/mrd/MRD_v0.1.md`).

## 7\. Business Model Canvas

Síntesis del **modelo de negocio** del producto en los 9 bloques de Osterwalder. Debe contener **al menos 3 elementos por bloque** (criterio de parada de la consigna).

| Bloque | Mínimo 3 elementos concretos |
| :---- | :---- |
| 1\. Segmentos de clientes | `<…>` / `<…>` / `<…>` |
| 2\. Propuesta de valor | `<…>` / `<…>` / `<…>` |
| 3\. Canales | `<…>` / `<…>` / `<…>` |
| 4\. Relación con clientes | `<…>` / `<…>` / `<…>` |
| 5\. Fuentes de ingresos | `<…>` / `<…>` / `<…>` |
| 6\. Recursos clave | `<…>` / `<…>` / `<…>` |
| 7\. Actividades clave | `<…>` / `<…>` / `<…>` |
| 8\. Socios clave | `<…>` / `<…>` / `<…>` |
| 9\. Estructura de costos | `<…>` / `<…>` / `<…>` |

## 8\. Métricas clave de éxito (North Star \+ apoyo)

Aquí declaran los **KPIs de negocio** que medirán si el proyecto resuelve realmente el problema. Si falta una línea base, decláralo explícitamente como "por medir antes del lanzamiento".

| ID | KPI | North Star? | Línea base | Meta | Horizonte | Fuente del dato |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| KPI-01 | `<NPS / tiempo medio / tasa de adopción>` | sí/no | `<valor>` | `<valor>` | Q4 2026 | `<sistema, encuesta>` |
| KPI-02 | `<…>` |  |  |  |  |  |

## 9\. Objetivos de negocio (SMART)

| ID | Objetivo | Métrica | Línea base | Meta | Horizonte |
| :---- | :---- | :---- | :---- | :---- | :---- |
| BO-01 | `<Reducir tiempo de trámite>` | minutos promedio | 45 min | ≤ 10 min | Q4 2026 |
| BO-02 | `<…>` |  |  |  |  |

## 10\. Stakeholders y roles (modelo RACI)

| Stakeholder | Interés | R / A / C / I |
| :---- | :---- | :---- |
| `<Sponsor>` | estratégico | A |
| `<Operaciones>` | operativo | R |
| `<Usuario final>` | experiencia | C |
| `<Legal>` | cumplimiento | C |

## 11\. Requerimientos de negocio

Cada ítem debe poder responder: ¿qué necesita el negocio, y cómo sabremos que se cumplió? **No** describir soluciones técnicas.

| ID | Requerimiento de negocio | Prioridad (MoSCoW) | Justificación | Métrica de aceptación |
| :---- | :---- | :---- | :---- | :---- |
| BR-001 | `<Permitir al estudiante iniciar el trámite sin presencia física>` | Must | evita desplazamientos y filas | 80 % de trámites iniciados en línea |
| BR-002 | `<Cobrar con QR bancario>` | Must | reduce uso de efectivo | 60 % pagos por QR |

## 12\. Reglas de negocio y políticas

| ID | Regla | Tipo | Origen |
| :---- | :---- | :---- | :---- |
| RB-01 | `<El saldo académico debe estar al día para iniciar un trámite>` | política | reglamento interno |
| RB-02 | `<…>` | normativa | Ley / ASFI / etc. |

## 13\. Supuestos, restricciones y dependencias

- **Supuestos**: condiciones que se asumen verdaderas (ej.: "el estudiante tiene acceso a internet móvil").  
- **Restricciones**: presupuesto máximo, marco normativo (Ley 164 Bolivia, PCI‑DSS si aplica), plazos obligatorios, sistemas legados que no pueden tocarse.  
- **Dependencias**: integraciones obligatorias con otros sistemas o áreas (p. ej. SIIS, sistema de tesorería, ERP universitario), aprobaciones externas requeridas.

## 14\. Alcance de negocio

### 14.1 En alcance

- `<Proceso/área incluida>`.

### 14.2 Fuera de alcance

- `<Proceso/área excluida con justificación>`.

## 15\. Beneficios esperados y *business case* resumido

| Tipo | Año 1 | Año 2 | Año 3 |
| :---- | :---- | :---- | :---- |
| Ahorro operativo | `<USD>` | `<USD>` | `<USD>` |
| Ingresos adicionales |  |  |  |
| Inversión (CAPEX) |  |  |  |
| Costo operación (OPEX) |  |  |  |
| **VAN** |  |  |  |
| **TIR** |  |  |  |

## 16\. Riesgos de negocio

| Riesgo | Probabilidad | Impacto | Mitigación | Responsable |
| :---- | :---- | :---- | :---- | :---- |
| `<Baja adopción>` | media | alta | campaña de difusión \+ capacitación | PM |

## 17\. Criterios de éxito del proyecto de negocio

- Cumplimiento de ≥ 80 % de los objetivos SMART.  
- *Business case* positivo al año 1\.  
- Satisfacción del *sponsor* ≥ 4/5.

## 18\. Trazabilidad a documentos hijos

| BRD ID | MRD relacionado | PRD relacionado | Caso de uso FSD |
| :---- | :---- | :---- | :---- |
| BR-001 | MRD-N-01 | PRD-REQ-05 | FSD-UC-001 |

## 19\. Aprobaciones

| Rol | Nombre | Firma | Fecha |
| :---- | :---- | :---- | :---- |
| Sponsor |  |  |  |
| PM |  |  |  |
| Arquitecto |  |  |  |

## 20\. Registro de cambios

| Versión | Fecha | Autor | Cambio |
| :---- | :---- | :---- | :---- |
| v0.1 |  |  | versión inicial |

## 21\. Anexo opcional — PR‑FAQ Amazon‑style (Working Backwards)

**Opcional**. El equipo puede optar por presentar la propuesta como **PR‑FAQ** estilo Amazon (ver S04 §B7.1). No reemplaza al BRD: lo **acompaña** como narrativa orientada al cliente. Útil para validar coherencia y comunicar al sponsor.

### 21.1 Press Release (≤ 1 página, futuro fingido)

\[FECHA DE LANZAMIENTO PROYECTADA\]

\[CIUDAD\] — \<Organización\> anunció hoy \<Producto\>, una nueva \<categoría\>

que permite a \<persona principal\> \<beneficio principal cuantificado\>.

"\<Cita inspiradora del sponsor o líder\>", dijo \<nombre y cargo\>.

\<Descripción del problema actual del cliente en 2-3 frases\>.

\<Cómo el producto lo resuelve, en 2-3 frases en lenguaje del cliente, no técnico\>.

"\<Cita de un cliente tipo / persona ficticia validada\>".

\<Producto\> está disponible \<a partir de cuándo / dónde / cómo\>.

Para más información: \<link\>.

### 21.2 External FAQ (5–10 preguntas)

Preguntas que un cliente externo se haría:

- ¿Qué es exactamente `<Producto>`?  
- ¿Cómo me beneficia comparado con lo que uso hoy?  
- ¿Cuánto cuesta y qué incluye?  
- ¿En qué se diferencia de `<competidor>`?  
- ¿Qué pasa si \<escenario de error o cancelación\>?  
- `<…>`

### 21.3 Internal FAQ (5–10 preguntas)

Preguntas que el equipo interno y el sponsor se harán:

- ¿Por qué *ahora* y no en 6 meses?  
- ¿Cuál es la inversión y el horizonte de retorno?  
- ¿Qué riesgos ven y cómo se mitigan?  
- ¿Qué dependencias críticas existen (sistemas, regulación, partners)?  
- ¿Cómo escalamos si la demanda supera la proyección?  
- `<…>`

**Criterio de uso**: si el grupo no escribe el PR‑FAQ, esta sección queda vacía. Si lo escribe, debe ser **coherente** con las secciones 1–17 del BRD (no debe contradecir métricas, alcance ni *business case*).

---

## Checklist mínimo de entrega

- [ ] **Resumen ejecutivo** de ½ página con problema, propuesta, valor y métricas.  
- [ ] Problema de negocio con evidencia cuantitativa.  
- [ ] **1–2 personas / usuarios objetivo** caracterizadas (JTBD, dolores, ganancias).  
- [ ] **Propuesta de valor** explícita (formato VPC).  
- [ ] **Panorama competitivo resumen** con ≥ 3 alternativas (incluyendo *do‑nothing*).  
- [ ] **Business Model Canvas** con los 9 bloques poblados, **≥ 3 elementos por bloque**.  
- [ ] **Métricas clave de éxito**: ≥ 1 *North Star* \+ 2 KPIs de apoyo, con meta y horizonte.  
- [ ] ≥ 3 objetivos de negocio SMART.  
- [ ] Matriz RACI completa.  
- [ ] ≥ 8 requerimientos de negocio priorizados (MoSCoW).  
- [ ] Reglas, restricciones, supuestos y dependencias explícitos.  
- [ ] *Business case* cuantitativo (aunque sea estimado).  
- [ ] Trazabilidad a MRD/PRD iniciada.

