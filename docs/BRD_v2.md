# Business Requirements Document v2.0
## BIOMED UMSS — Intelligent Karyotyping Platform

| Campo | Detalle |
|---|---|
| **Proyecto** | BIOMED UMSS – Intelligent Karyotyping |
| **Versión** | 2.0 |
| **Fecha** | Mayo 2026 |
| **Autor** | Ing. Guillermo Mamani Chambi |
| **Institución** | Universidad Mayor de San Simón (UMSS) |
| **Trazabilidad** | Actualiza BRD v1.0 — incorpora refinamientos del Módulo 4 |
| **Clasificación** | Confidencial – Uso interno |

---

## Changelog v2.0

| Sección | Cambio |
|---|---|
| §4 Propuesta de Valor | Se añade detalle del modelo de confianza Softmax y los 4 mecanismos anti-sesgo |
| §5 Métricas | Se agregan métricas de activación y corrección manual con base técnica |
| §6 Competidores | Se profundiza en diferenciadores técnicos del stack SaaS |
| §8 Riesgos | Se añaden riesgos de sesgo de automatización con mitigaciones específicas |
| §9 (Nuevo) | Se añade sección de Jerarquía Documental y trazabilidad al PRD/FSD |

---

## 1. Resumen Ejecutivo

BIOMED UMSS es una plataforma web SaaS de inteligencia artificial diseñada para automatizar el análisis citogenético (cariotipado). El sistema transforma un proceso manual que consume entre 30 y 45 minutos por caso en un flujo asistido por IA que lo reduce a menos de 15 minutos, manteniendo una tasa de error de diagnóstico de cero mediante un modelo **Human-in-the-loop**.

La plataforma aborda una brecha tecnológica crítica en los laboratorios de genética clínica de Bolivia y Latinoamérica: la dependencia de software local costoso (hasta USD 20,000), propenso a fatiga visual y errores humanos acumulados. BIOMED democratiza el acceso a tecnología de punta mediante una solución 100% web, accesible desde cualquier navegador, sin hardware especializado, con diagnóstico remoto e interconsulta en tiempo real.

**Stack tecnológico de referencia (v2):** React + Vite (Frontend), FastAPI Python 3.11+ (Backend), Redis + Celery (Cola asíncrona), TorchServe / NVIDIA Triton (Motor IA GPU), PostgreSQL 15+ (Persistencia), WebSockets (Notificaciones tiempo real).

---

## 2. Problema y Oportunidad de Negocio

### 2.1 Problema Central

El análisis citogenético tradicional presenta tres fallas estructurales:

1. **Ineficiencia temporal**: El recorte manual, segmentación y clasificación de cromosomas demanda entre 30 y 45 minutos por muestra, generando cuellos de botella críticos en laboratorios de alto volumen (>50 muestras/mes).

2. **Fatiga cognitiva y riesgo clínico**: La atención visual sostenida provoca fatiga extrema en los especialistas, incrementando la probabilidad de errores diagnósticos en anomalías estructurales complejas y raras.

3. **Barreras de acceso tecnológico**: Los sistemas disponibles (Ikaros de MetaSystems, CytoVision de Leica) son instalaciones locales que requieren estaciones de trabajo dedicadas de hasta USD 20,000, licencias locales costosas y no permiten colaboración remota.

### 2.2 Riesgo Adicional: Sesgo de Automatización

Un riesgo clínico identificado en v2 es el **sesgo de automatización**: el peligro de que el especialista confíe ciegamente en los resultados de la IA, omitiendo la verificación de cromosomas no marcados como dudosos. BIOMED mitiga este riesgo con cuatro mecanismos específicos (ver §8.2).

### 2.3 Oportunidad de Mercado

La transición del paradigma de software local al modelo **Web SaaS** representa la oportunidad central. BIOMED se diferencia al:

- Eliminar la barrera de inversión en hardware especializado
- Habilitar el diagnóstico remoto e interconsulta en la nube en tiempo real
- Ofrecer actualizaciones continuas del modelo de IA sin intervención del laboratorio
- Democratizar el acceso a citogenética avanzada para centros que no pueden costear infraestructura dedicada

El mercado objetivo inicial son laboratorios de diagnóstico citogenético en Bolivia, con potencial de expansión regional a Latinoamérica.

---

## 3. Usuarios Objetivo

### Usuario Principal #1 — Analista Citogenetista

| Atributo | Detalle |
|---|---|
| **Perfil de referencia** | Dra. Valeria Ríos, Citogenetista Senior, 42 años, 10 años de experiencia |
| **Carga de trabajo** | ~60 muestras mensuales |
| **Frustración principal** | Pérdida de tiempo en tareas mecánicas de recorte manual |
| **Objetivo en el sistema** | Clasificar cromosomas de forma rápida y precisa |

**Tareas críticas:**
1. Cargar imágenes de metafases y registrar datos clínicos (anonimizados con código CHN)
2. Corregir y validar la clasificación automática sugerida por la IA
3. Realizar ediciones manuales (rotar, unir, dividir fragmentos) en cromosomas complejos

### Usuario Principal #2 — Supervisor / Garante Clínico

**Tareas críticas:**
1. Revisar cromosomas marcados con baja confianza (<85%) corregidos por el analista
2. Autorizar o rechazar el diagnóstico propuesto por muestra
3. Firmar digitalmente el reporte final para envío al sistema hospitalario (LIS)

### Usuario #3 — Director del Laboratorio (Decision Maker)
Optimizar TAT y reducir costos operativos sin comprometer la calidad diagnóstica.

### Usuario #4 — Personal de IT
Integración con LIS, seguridad de datos anonimizados y estabilidad de plataforma.

---

## 4. Propuesta de Valor

### 4.1 Propuesta Principal

> **"De 45 minutos a menos de 15 minutos por cariotipo, con cero errores por omisión."**

| Ventaja | Descripción |
|---|---|
| **Automatización inteligente** | Reducción del tiempo de análisis a <12 min (objetivo: 5 min), precisión >97% |
| **Human-in-the-loop** | IA genera borradores editables; especialista mantiene control absoluto |
| **Transparencia Softmax** | Score de confianza por cromosoma: verde (≥85%), naranja (<85%), bloqueado |
| **Accesibilidad web** | 100% web, diagnóstico remoto, sin hardware dedicado |

### 4.2 Funcionalidades Clave del Sistema

1. Registro de muestras con código CHN único y anonimizado
2. Segmentación y clasificación automática de cromosomas (Mask R-CNN + ResNet50)
3. Semaforización visual de confianza algorítmica (umbral: 85% Softmax)
4. Manipulación interactiva (drag & drop, rotar, unir, dividir)
5. Generación automática de nomenclatura ISCN
6. Bloqueo de emisión de resultados si existen cromosomas <85% no validados
7. Firma digital del supervisor como paso obligatorio

### 4.3 Reglas de Negocio Críticas

- **RN-01**: Ningún informe puede emitirse sin validación del analista Y firma del supervisor
- **RN-02**: El sistema prioriza sensibilidad sobre precisión absoluta en casos de duda
- **RN-03**: Cromosomas con confianza <85% bloquean la exportación del informe
- **RN-04**: La anonimización CHN es mandatoria antes de cualquier transmisión cloud

---

## 5. Métricas Clave de Éxito

| Métrica | Baseline | Meta v1 | Base técnica |
|---|---|---|---|
| **TTK** (Time to Karyotype) | 45 min | <15 min (obj: 5 min) | Pipeline asíncrono Redis/Celery |
| **Precisión diagnóstica** | Variable | >97.2% | ResNet50 + Mask R-CNN IoU>95% |
| **Tasa corrección manual** | ~100% | <15% | Proyección basada en precisión modelos |
| **Tasa de error diagnóstico** | Variable | 0% omisiones | Bloqueo por baja confianza + doble firma |
| **Tasa de Activación** | — | >80% | Usuarios que completan flujo inicial |
| **Tiempo de inferencia** | — | <15s/muestra | TorchServe GPU + tiling |

---

## 6. Panorama Competitivo

| Criterio | Ikaros (MetaSystems) | CytoVision (Leica) | **BIOMED UMSS** |
|---|---|---|---|
| **Despliegue** | Local (on-premise) | Local (on-premise) | **100% Web SaaS** |
| **Acceso remoto** | No | No | **Sí — tiempo real** |
| **Costo entrada** | >USD 20,000 | >USD 20,000 | **Suscripción mensual** |
| **Actualizaciones** | Manuales, costosas | Manuales | **Continuas, automáticas** |
| **Transparencia IA** | Caja negra | Caja negra | **Semaforización Softmax** |
| **Colaboración** | Red local | Red local | **Interconsulta en la nube** |
| **Escalabilidad** | Hardware fijo | Hardware fijo | **Horizontal (Docker/Celery)** |

---

## 7. Business Model Canvas

### 7.1 Segmentos de Clientes
1. Laboratorios citogenéticos con carga >50 muestras/mes
2. Directores de clínicas/hospitales con foco en TAT y costos
3. Citogenetistas que buscan eliminar tareas mecánicas

### 7.2 Propuesta de Valor
1. TTK: 45 min → <12 min con precisión >97%
2. Human-in-the-loop con transparencia Softmax
3. Acceso web sin hardware, diagnóstico remoto

### 7.3 Canales
1. Plataforma Web SaaS (acceso directo navegador)
2. Demos personalizadas gratuitas (15 minutos)
3. Canal digital: `info@biomed.umss.bo`

### 7.4 Relación con Clientes
1. Asistencia diagnóstica proactiva (semaforización)
2. Diagnóstico remoto e interconsulta en la nube
3. Bloqueo de informes incompletos como garantía clínica

### 7.5 Fuentes de Ingresos
1. Suscripción mensual por acceso SaaS
2. Ahorro operativo: reducción horas-especialista en tareas mecánicas
3. Consultoría e integración con LIS

### 7.6 Recursos Clave
1. Algoritmos IA (Mask R-CNN + ResNet50, IoU >95%)
2. Arquitectura cloud modular (FastAPI + Redis + TorchServe)
3. Datasets clínicos anonimizados para recalibración trimestral

### 7.7 Actividades Clave
1. Desarrollo y mejora continua de modelos IA
2. Diseño UX clínica (reducción carga cognitiva)
3. Mantenimiento, seguridad y auditoría de datos

### 7.8 Socios Clave
1. UMSS — respaldo institucional, I+D y validación
2. IIBISMED-UMSS — laboratorio beta tester
3. Proveedores IT de salud — integración hospitalaria

### 7.9 Estructura de Costos
1. I+D: equipo fundador (CEO, CTO, CMO) + especialistas IA
2. Infraestructura: servidores cloud, GPU, almacenamiento, ciberseguridad
3. Validación clínica: auditorías, estudios de usabilidad, soporte

---

## 8. Supuestos, Riesgos, Restricciones y Dependencias

### 8.1 Supuestos

| # | Supuesto |
|---|---|
| S1 | Borrador automático editable en <1 min reduce tiempo de procesamiento en 60% |
| S2 | Semaforización elimina inspección cromosoma por cromosoma, reduciendo fatiga |
| S3 | Laboratorios objetivo tienen conectividad suficiente para plataforma web |
| S4 | Curva de aprendizaje menor a 2 sesiones de uso |
| S5 | Suscripción mensual preferida sobre licencia única para presupuestos limitados |

### 8.2 Riesgos — Versión Refinada

| # | Riesgo | Impacto | Prob. | Mitigación |
|---|---|---|---|---|
| R1 | **Sesgo de automatización** — especialista confía ciegamente en IA | Alto | Medio | 4 mecanismos: (1) muestreo aleatorio 10-20% de verdes, (2) score global de cariograma, (3) gradientes de color (no binario), (4) auditoría por supervisor en casos críticos |
| R2 | **Conectividad limitada** — red deficiente en hospitales | Alto | Medio | Compresión progresiva, tiling de imágenes, modo offline parcial en roadmap |
| R3 | **Baja tasa de activación** — usuarios no completan flujo inicial | Alto | Medio | Onboarding guiado, demo 15 min, soporte proactivo |
| R4 | **Resistencia al cambio** — rechazo de citogenetistas senior | Medio | Medio | Comunicar transparencia algorítmica; Human-in-the-loop explícito |
| R5 | **Falsos negativos en anomalías raras** — precisión cae en patologías poco representadas | Alto | Bajo | Recalibración trimestral, umbral conservador 85%, auditoría clínica |
| R6 | **Pérdida de datos** — falla en persistencia PostgreSQL | Alto | Bajo | Backups automáticos, audit trail inalterable, alta disponibilidad |

### 8.3 Restricciones

| # | Restricción |
|---|---|
| RC1 | Ningún informe puede emitirse sin validación del analista Y firma digital del supervisor |
| RC2 | Sistema no exporta informe con cromosomas <85% confianza no validados |
| RC3 | Datos de pacientes deben anonimizarse (CHN) antes de cualquier procesamiento cloud |
| RC4 | Informes deben seguir nomenclatura ISCN vigente |
| RC5 | Plataforma compatible con navegadores modernos sin instalación local |
| RC6 | Analista y supervisor no pueden ser la misma persona en casos críticos |

### 8.4 Dependencias

| # | Dependencia | Tipo |
|---|---|---|
| D1 | Integración con Sistemas de Información de Laboratorio (LIS) | Técnica |
| D2 | Cumplimiento nomenclatura ISCN | Regulatoria |
| D3 | Normativas Ministerio de Salud sobre trazabilidad diagnóstica | Regulatoria |
| D4 | Datasets clínicos anonimizados para entrenamiento/recalibración | Técnica / Institucional |
| D5 | Validación institucional UMSS / IIBISMED-UMSS | Institucional |

---

## 9. Jerarquía Documental y Trazabilidad

```
BRD v2.0 (este documento)
    └── PRD_v1.md        → Qué debe hacer el producto (User Stories, Criterios Aceptación)
         └── FSD_v1.md   → Cómo se implementa técnicamente (Stack, Tasks, Casos de Uso)
              └── LFSD.md → Versión ágil y viva para iteraciones tempranas
              └── PROMPT_MAPPINGS.md → Trazabilidad Requerimiento → Prompt → Código
```

Este documento es la fuente de verdad de negocio. Todos los documentos técnicos deben trazarse a las secciones de este BRD.

---

## 10. Alcance del Proyecto

### En scope (v1.0)
- Registro de muestras con código CHN anonimizado
- Motor IA: segmentación (Mask R-CNN) + clasificación (ResNet50)
- Interfaz de edición interactiva (drag & drop, rotar, unir, dividir)
- Semaforización de confianza Softmax (verde/naranja/bloqueado)
- Generación automática nomenclatura ISCN
- Flujo de validación en dos niveles (analista + supervisor)
- Firma digital y emisión bloqueada por validación incompleta
- Panel de auditoría de casos

### Fuera de scope (v1.0)
- Módulo de secuenciación genómica (NGS)
- Integración directa con equipos de microscopía
- Aplicación móvil nativa
- Modo offline completo

---

*Trazabilidad: BRD_v2.md → PRD_v1.md → FSD_v1.md / LFSD.md → PROMPT_MAPPINGS.md*
