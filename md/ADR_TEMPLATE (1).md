# Architecture Decision Record (ADR) – Plantilla

**Propósito**: registrar de forma breve y versionada **una decisión arquitectónica** significativa, con su contexto y consecuencias. Los ADRs viven en `docs/adr/NNNN-titulo-corto.md` y son leídos tanto por humanos como por agentes de IA.

**Cuándo crear un ADR**: cada vez que se tome una decisión que:

- Afecta la estructura, seguridad, costo o escalabilidad del sistema.  
- Es costosa de revertir.  
- Impone restricciones futuras (lock‑in tecnológico, patrón obligatorio, proveedor).

**Regla MUST**: no mezclar más de una decisión por ADR. Si se requiere revisar una decisión previa, crear un nuevo ADR que **supersede** al anterior.

---

## ADR‑NNNN: `<Título corto, en imperativo o sustantivo>`

### Metadatos

| Campo | Valor |
| :---- | :---- |
| Número | `NNNN` (correlativo, 4 dígitos) |
| Título | `<Título corto>` |
| Fecha | `<dd/mm/aaaa>` |
| Autor(es) | `<…>` |
| Estado | **Propuesta** / Aceptada / Rechazada / Obsoleta / Superada por ADR‑NNNN |
| Alcance | `<módulo / servicio / todo el sistema>` |
| Stakeholders consultados | `<…>` |

### 1\. Contexto

Describir en 5–15 líneas:

- El **problema** que se intenta resolver.  
- Las **restricciones** (técnicas, de equipo, de negocio, regulatorias).  
- Las **fuerzas en tensión** (performance vs. simplicidad, costo vs. disponibilidad, etc.).  
- Lo que se sabe y lo que se desconoce.

### 2\. Alternativas consideradas

| Alternativa | Pros | Contras | Costo aproximado |
| :---- | :---- | :---- | :---- |
| A. `<…>` |  |  |  |
| B. `<…>` |  |  |  |
| C. `<…>` |  |  |  |

### 3\. Decisión

**Elegimos la alternativa `<X>`: `<descripción concisa en una frase>`.**

Desarrollar en 3–8 líneas *por qué* es la elegida, enfatizando los **criterios decisivos** y cómo balancean las fuerzas de §1.

### 4\. Consecuencias

#### 4.1 Positivas

- `<…>`.

#### 4.2 Negativas / costos

- `<…>`.

#### 4.3 Neutras / observables

- `<…>`.

### 5\. Impacto en el sistema

- **Código**: archivos/módulos afectados.  
- **Operaciones**: cambios en despliegue, monitoreo, SLO.  
- **Seguridad**: nuevos vectores, nuevas defensas.  
- **Equipo**: habilidades requeridas, capacitación.  
- **Costo**: impacto en factura AWS, licencias, etc.

### 6\. Plan de reversión

- Señales tempranas de que la decisión fue incorrecta.  
- Costo estimado de revertir.  
- Plan B si se revierte.

### 7\. Validación

- ¿Cómo verificaremos que la decisión fue acertada?  
- Métricas, plazos, responsable.

### 8\. Referencias

- Benchmarks, papers, documentación oficial, ADRs relacionados.  
- Enlace a la POC que validó la decisión (si aplica).

### 9\. Historial

| Versión | Fecha | Autor | Cambio |
| :---- | :---- | :---- | :---- |
| 1 | `<dd/mm/aaaa>` |  | propuesta inicial |
| 2 | `<…>` |  | aceptada tras revisión |

---

## Convenciones del Módulo 4

- Nomenclatura de archivo: `docs/adr/NNNN-kebab-case-titulo.md`.  
- Entrega mínima para la **Entrega Final (20 %)**: **≥ 3 ADRs aceptadas** por grupo.  
- Temas recomendados para ADRs del módulo: estilo arquitectónico (monolito vs. microservicios), persistencia principal, estrategia de mensajería, elección del *cloud*, patrón de *saga*, uso de RAG vs. *fine‑tuning*, framework de agentes.

---

## Ejemplo breve (referencia)

### ADR‑0001: Adopción de Arquitectura Hexagonal

|  |  |
| :---- | :---- |
| Estado | Aceptada |
| Fecha | 12/05/2026 |

**Contexto.** El equipo de 4 devs construye un producto con reglas de negocio complejas y múltiples integraciones externas. Se necesita aislar el dominio de la infraestructura.

**Alternativas.** Monolito por capas (MVC) / Clean / Hexagonal.

**Decisión.** Adoptamos **Arquitectura Hexagonal** con puertos y adaptadores, dominio en `src/domain/`.

**Consecuencias.** (+) aislamiento, testabilidad. (−) curva de aprendizaje, más archivos.

**Validación.** Cobertura del dominio ≥ 80 %, cero imports de frameworks en `domain/`.  
