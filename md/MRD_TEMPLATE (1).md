# Market Requirements Document (MRD) – Plantilla

**Propósito del MRD**: describir **el mercado, los usuarios y la oportunidad comercial** que justifican la construcción del producto. Responde a **"¿qué pide el mercado y por qué este producto ganará?"**.

Complementa al BRD (visión interna del negocio) y antecede al PRD (qué debe hacer el producto). Audiencia típica: *Product Management, Marketing, Ventas, Sponsor*.

---

## 0\. Metadatos

| Campo | Valor |
| :---- | :---- |
| Producto | `<Nombre>` |
| Grupo | `<G1/G2/G3/G4>` |
| Versión | `v0.1` |
| Fecha | `<dd/mm/aaaa>` |
| Product Manager / Autor | `<…>` |
| Revisores | Docente \+ stakeholders |
| Estado | Borrador / Aprobado |
| Relación con BRD | `<BRD v…>` (si aplica) |

## 1\. Resumen ejecutivo

De 150 a 250 palabras. Responde: **¿qué producto, para qué mercado, con qué diferenciación y qué tamaño de oportunidad?**.

**Formato alternativo (opcional)**: el grupo puede presentar este MRD como **6‑pager narrativo estilo Amazon** (ver S04 §B7.1). El 6‑pager Amazon‑style sustituye el formato de tabla por una narrativa de ≤ 6 páginas con prosa estructurada (problema → tamaño de mercado → personas → diferenciación → riesgos → recomendación). Si el grupo elige esa ruta, conserve igualmente la sección §14 *Trazabilidad* y los anexos.

## 2\. Visión del producto

Una frase inspiradora (máx. 25 palabras) que condense **para quién, qué, por qué y cuándo**.

*Ejemplo*: "Para estudiantes de la UMSS, que hoy pierden horas en filas burocráticas, una plataforma de trámites académicos 100 % digital que reduce el tiempo promedio de resolución de 45 a 10 minutos en 2026."

## 3\. Análisis de mercado

### 3.1 Tamaño de mercado

| Métrica | Valor | Fuente |
| :---- | :---- | :---- |
| TAM (*Total Addressable Market*) | `<USD / usuarios>` | `<…>` |
| SAM (*Serviceable Addressable Market*) | `<…>` | `<…>` |
| SOM (*Serviceable Obtainable Market*) | `<…>` | `<…>` |

### 3.2 Tendencias del sector

- Tendencia 1: `<…>`.  
- Tendencia 2: `<…>`.  
- Tendencia 3: `<…>`.

### 3.3 Factores regulatorios y de cumplimiento

- Ley 164 Bolivia, ASFI, PCI‑DSS, GDPR, etc.

### 3.4 Cadencia de Continuous Discovery

Ver S04 §B6 (*Continuous Discovery \+ Dual‑Track Agile*). El MRD es un documento **vivo** que se alimenta semanalmente del *track de Discovery*.

| Aspecto | Valor |
| :---- | :---- |
| Cadencia de entrevistas | `<semanal / quincenal>` |
| Usuarios contactados por ciclo | `<n>` (Torres recomienda ≥ 1 por semana) |
| Formato de hipótesis | *Cuando `<situación>`, espero `<resultado>`, porque `<razón>`* |
| Backlog de hipótesis | `<link a tablero / sección de §12>` |
| Output del track | Validaciones que actualizan §3, §5, §11 y §12 de este MRD |

**Criterio**: si en una semana no hubo contacto con usuarios, declárelo explícitamente como riesgo en §13.

## 4\. Segmentación y *personas*

### 4.1 Segmentos de clientes

| Segmento | Tamaño | Necesidad principal | Disposición a pagar | Origen M2 (segmento equivalente del Módulo anterior) |
| :---- | :---- | :---- | :---- | :---- |
| `<Estudiante de pregrado>` | 38 000 | `<trámite rápido>` | incluido en matrícula | `<Persona del M2 que valida este segmento>` |
| `<…>` |  |  |  |  |

### 4.2 Personas

**Trazabilidad con M2 (UI/UX)**: si una persona del MRD ya fue caracterizada en el módulo anterior (entregables M2), declárelo en el campo *"Origen M2"* y enlace al artefacto. No replique trabajo: complemente con la mirada de mercado (tamaño, *willingness‑to‑pay*, segmento competitivo).

#### Persona 1 – `<Nombre>`

- **Origen M2**: `<ruta al artefacto del módulo anterior, p. ej. M2/personas/persona_estudiante.md>` (vacío si es nueva en MRD).  
- **Rol**: `<…>`.  
- **Demografía**: edad, ocupación, contexto.  
- **Objetivos**: `<…>`.  
- **Dolores actuales**: `<…>`.  
- **Comportamiento digital**: dispositivos, canales, hábitos.  
- **Frase representativa**: "`<…>`".

#### Persona 2 – `<Nombre>`

*(replicar)*

## 5\. *Jobs‑to‑be‑Done*

| JTBD ID | Cuando… | Quiero… | Para poder… |
| :---- | :---- | :---- | :---- |
| JTBD-01 | necesito un certificado urgente | iniciar el trámite desde mi celular | no perder medio día en la universidad |

## 6\. Análisis competitivo

### 6.1 Tabla comparativa

| Criterio | Nuestro producto | Competidor A | Competidor B | Competidor C |
| :---- | :---- | :---- | :---- | :---- |
| Precio |  |  |  |  |
| Cobertura geográfica |  |  |  |  |
| Integración con pagos |  |  |  |  |
| Uso de IA |  |  |  |  |
| SLA |  |  |  |  |

### 6.2 *Positioning statement*

Para `<persona>`, que `<dolor>`, nuestro `<producto>` es `<categoría>` que `<beneficio principal>` a diferencia de `<competidor>` que `<limitación>`.

### 6.3 Ventaja competitiva sostenible

- `<Fuente de la ventaja: datos propios, red, marca, regulación, tecnología>`.

## 7\. Propuesta de valor

### 7.1 *Value proposition canvas* resumido

| Gains | Pains | Gains relievers | Pain relievers | Products & services |
| :---- | :---- | :---- | :---- | :---- |
|  |  |  |  |  |

## 8\. Pricing y modelo de negocio

- Modelo: suscripción / transacción / freemium / SaaS B2B / marketplace.  
- Estructura de precios propuesta.  
- Elasticidad / *benchmark* con competidores.

## 9\. *Go‑to‑market*

### 9.1 Canales de adquisición

- Canal directo: `<…>`.  
- Canal digital: `<SEO, ads, referidos>`.  
- Partners: `<…>`.

### 9.2 Estrategia de lanzamiento

- **Pre‑launch**: `<beta cerrada, waitlist>`.  
- **Launch**: `<…>`.  
- **Post‑launch**: `<activación, retención>`.

### 9.3 Funnel AARRR inicial

| Etapa | Métrica | Meta |
| :---- | :---- | :---- |
| Acquisition | visitas / mes |  |
| Activation | registros |  |
| Retention | MAU / DAU |  |
| Revenue | ARPU |  |
| Referral | k‑factor |  |

## 10\. Métricas de éxito del producto

- **North Star Metric**: `<…>`.  
- **KPIs secundarios**: 3 a 5, todos cuantitativos y fechados.

## 11\. Requerimientos de mercado (alto nivel)

| ID | Requerimiento | Prioridad | Justificación |
| :---- | :---- | :---- | :---- |
| MRD-N-01 | soportar 10 000 usuarios concurrentes | Must | volumen esperado en matrícula |
| MRD-N-02 | integración con pagos QR Bolivia | Must | preferencia del segmento |

## 12\. Supuestos e hipótesis a validar

| ID | Hipótesis | Cómo validar | Criterio de éxito |
| :---- | :---- | :---- | :---- |
| H1 | 60 % de estudiantes pagará por QR | encuesta \+ piloto | ≥ 55 % en piloto |

## 13\. Riesgos de mercado

| Riesgo | Prob. | Impacto | Mitigación |
| :---- | :---- | :---- | :---- |
| `<competidor establecido lanza lo mismo>` | media | alto | acelerar time‑to‑market |

## 14\. Trazabilidad

| MRD ID | BRD ID | PRD ID |
| :---- | :---- | :---- |
| MRD-N-01 | BR-001 | PRD-REQ-05 |

## 15\. Anexos

- Entrevistas con usuarios (resumen).  
- Datos cuantitativos de mercado (enlaces).  
- *Benchmarks*.

## 16\. Registro de cambios

| Versión | Fecha | Autor | Cambio |
| :---- | :---- | :---- | :---- |
| v0.1 |  |  | versión inicial |

---

## Checklist mínimo

- [ ] TAM/SAM/SOM con fuentes.  
- [ ] ≥ 2 personas completas.  
- [ ] ≥ 3 JTBD.  
- [ ] ≥ 2 competidores en matriz.  
- [ ] *Positioning statement* en 1 frase.  
- [ ] Pricing y *go‑to‑market* esbozados.  
- [ ] North Star \+ 3 KPIs fechados.  
- [ ] Requerimientos MRD-N-\* priorizados.  
- [ ] 3 hipótesis a validar con criterio de éxito.  
- [ ] Trazabilidad a BRD y PRD iniciada.

