# Business Requirements Document (BRD)
## BIOMED UMSS — Intelligent Karyotyping Platform

| Campo | Detalle |
|---|---|
| **Proyecto** | BIOMED UMSS – Intelligent Karyotyping |
| **Versión** | 1.0 |
| **Fecha** | Mayo 2026 |
| **Autor** | Ing. Guillermo Mamani Chambi |
| **Institución** | Universidad Mayor de San Simón (UMSS) |
| **Clasificación** | Confidencial – Uso interno |

---

## 1. Resumen Ejecutivo

BIOMED UMSS es una plataforma web SaaS de inteligencia artificial diseñada para automatizar el análisis citogenético (cariotipado). El sistema transforma un proceso manual que consume entre 30 y 45 minutos por caso en un flujo asistido por IA que lo reduce a menos de 15 minutos, manteniendo una tasa de error de diagnóstico de cero mediante un modelo **Human-in-the-loop**.

La plataforma aborda una brecha tecnológica crítica en los laboratorios de genética clínica de Bolivia y Latinoamérica: la dependencia de software local costoso (hasta USD 20,000), propenso a fatiga visual y errores humanos acumulados. BIOMED democratiza el acceso a tecnología de punta mediante una solución 100% web, accesible desde cualquier navegador, sin hardware especializado, con diagnóstico remoto e interconsulta en tiempo real.

El proyecto está respaldado por la UMSS y desarrollado por un equipo fundador multidisciplinario con roles de CEO/Producto, CTO/Desarrollo e IA, y CMO/Validación Clínica.

---

## 2. Problema y Oportunidad de Negocio

### 2.1 Problema Central

El análisis citogenético tradicional presenta tres fallas estructurales:

1. **Ineficiencia temporal**: El recorte manual, segmentación y clasificación de cromosomas demanda entre 30 y 45 minutos por muestra, generando cuellos de botella críticos en laboratorios de alto volumen (>50 muestras/mes).

2. **Fatiga cognitiva y riesgo clínico**: La atención visual sostenida provoca fatiga extrema en los especialistas, incrementando la probabilidad de errores diagnósticos en anomalías estructurales complejas y raras.

3. **Barreras de acceso tecnológico**: Los sistemas disponibles (Ikaros de MetaSystems, CytoVision de Leica) son instalaciones locales que requieren estaciones de trabajo dedicadas de hasta USD 20,000, licencias locales costosas y no permiten colaboración remota ni actualización continua.

### 2.2 Oportunidad de Mercado

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
| **Frustración principal** | Pérdida de tiempo en tareas mecánicas de recorte manual de imágenes microscópicas |
| **Objetivo en el sistema** | Clasificar cromosomas de forma rápida y precisa para identificar anomalías genéticas |

**Tareas críticas en el sistema:**
1. Cargar imágenes de metafases y registrar datos clínicos del paciente (anonimizados)
2. Corregir y validar la clasificación automática sugerida por la IA
3. Realizar ediciones manuales (rotar, unir, dividir fragmentos) en cromosomas complejos

---

### Usuario Principal #2 — Supervisor / Garante Clínico

| Atributo | Detalle |
|---|---|
| **Rol** | Especialista en control de calidad y responsabilidad diagnóstica |
| **Objetivo en el sistema** | Auditar los casos procesados y firmar el informe final antes de la entrega |

**Tareas críticas en el sistema:**
1. Revisar cromosomas marcados con "baja confianza" por la IA y corregidos por el analista
2. Autorizar o rechazar el diagnóstico propuesto para cada muestra
3. Firmar digitalmente el reporte final para su envío al sistema hospitalario (LIS)

---

### Usuario #3 — Director del Laboratorio (Decision Maker)

| Atributo | Detalle |
|---|---|
| **Rol** | Tomador de decisiones económicas y operativas |
| **Objetivo** | Optimizar el TAT (Turn Around Time) y reducir costos operativos sin comprometer la calidad |

---

### Usuario #4 — Personal de IT

| Atributo | Detalle |
|---|---|
| **Rol** | Integración técnica con sistemas hospitalarios |
| **Objetivo** | Garantizar integración con LIS, seguridad de datos anonimizados y estabilidad de plataforma |

---

## 4. Propuesta de Valor

### 4.1 Propuesta Principal

> **"De 45 minutos a menos de 15 minutos por cariotipo, con cero errores por omisión."**

BIOMED entrega tres ventajas competitivas centrales:

| Ventaja | Descripción |
|---|---|
| **Automatización inteligente** | Reducción del tiempo de análisis de ~45 min a <12 min (objetivo: 5 min) mediante segmentación y clasificación automática con precisión >97% |
| **Human-in-the-loop** | La IA genera borradores editables; el especialista mantiene el control absoluto del diagnóstico final mediante transparencia algorítmica (semaforización verde/amarillo/rojo) |
| **Accesibilidad web** | Plataforma 100% web que elimina hardware dedicado, permite diagnóstico remoto e interconsulta en tiempo real desde cualquier navegador moderno |

### 4.2 Funcionalidades Clave del Sistema

1. Registrar muestras asociándolas a un código de paciente único y anonimizado
2. Procesar imágenes de metafases para segmentar y ordenar cromosomas automáticamente
3. Notificar visualmente sobre cromosomas con clasificación dudosa (confianza <85%)
4. Permitir manipulación física virtual de cromosomas (drag & drop, rotar, unir, dividir)
5. Generar automáticamente la nomenclatura técnica internacional ISCN
6. Bloquear emisión de resultados si existen conflictos de clasificación no resueltos por un humano

### 4.3 Reglas de Negocio Críticas

- **Regla 1 — Doble validación obligatoria**: Ningún informe puede emitirse sin validación manual del analista y firma digital del supervisor.
- **Regla 2 — Prioridad de sensibilidad**: El sistema prioriza la detección de anomalías sobre la precisión absoluta, obligando revisión humana en todos los casos de duda algorítmica.
- **Regla 3 — Bloqueo por baja confianza**: Si cromosomas con confianza <85% no han sido validados, la exportación del informe queda bloqueada.

---

## 5. Métricas Clave de Éxito

| Métrica | Valor Actual | Meta | Indicador |
|---|---|---|---|
| **TAT / TTK** (Time to Karyotype) | 45 min/caso | <15 min (objetivo: 5 min) | ✅ Sistema funcional |
| **Precisión del algoritmo** | — | >97% (IoU: 96.8%) | Auditoría trimestral |
| **Tasa de corrección manual** | — | <15% de cromosomas requieren corrección | Monitoreo continuo |
| **Tasa de error diagnóstico** | Variable | 0% (cero falsos negativos no detectados) | Auditoría clínica |
| **Tasa de Activación** | — | >80% usuarios completan flujo inicial | Analytics de plataforma |
| **Reducción de fatiga** | Alta | Eliminación de inspección cromosoma por cromosoma | Encuesta de satisfacción UX |

**Criterio de éxito principal**: El tiempo promedio de entrega de un resultado de cariotipo se reduce de 45 minutos a menos de 15 minutos, manteniendo tasa de error de diagnóstico de cero.

---

## 6. Panorama Competitivo

### 6.1 Competidores Directos

| Sistema | Empresa | Debilidades |
|---|---|---|
| **Ikaros** | MetaSystems | Instalación local, hardware dedicado, interfaz para ingenieros, sin colaboración remota, costo >USD 20,000 |
| **CytoVision** | Leica Biosystems | Dependencia de dongles físicos, servidores on-premise, actualización manual, acceso solo en red local |

### 6.2 Posicionamiento Competitivo de BIOMED

| Criterio | Competencia (Ikaros/CytoVision) | BIOMED |
|---|---|---|
| **Despliegue** | Local (on-premise) | 100% Web (SaaS) |
| **Acceso remoto** | No | Sí — diagnóstico y consulta en tiempo real |
| **Costo de entrada** | >USD 20,000 (hardware + licencia) | Suscripción mensual (bajo costo de entrada) |
| **Actualizaciones** | Manuales, costosas | Continuas, automáticas |
| **Transparencia IA** | "Caja negra" | Semaforización de confianza visible |
| **Colaboración** | Red local únicamente | Interconsulta en la nube |
| **Integración LIS** | Limitada | Nativa (API) |

### 6.3 Ventaja Competitiva Sostenible

BIOMED combina **precisión clínica superior al 97%** con **accesibilidad web total**, ofreciendo transparencia algorítmica que los sistemas tradicionales no tienen. La arquitectura SaaS permite recalibración trimestral del modelo y mejora continua basada en datasets anonimizados reales.

---

## 7. Resumen del Business Model Canvas

### 7.1 Segmentos de Clientes
1. Laboratorios de diagnóstico citogenético con carga >50 muestras/mes
2. Directores de clínicas y hospitales con foco en optimización de TAT y costos
3. Citogenetistas clínicos que buscan eliminar tareas mecánicas de bajo valor clínico

### 7.2 Propuesta de Valor
1. Automatización: reducción de 45 min a <12 min por caso con precisión >97%
2. Human-in-the-loop: transparencia algorítmica con control absoluto del especialista
3. Accesibilidad web: diagnóstico remoto sin hardware dedicado, costo de entrada bajo

### 7.3 Canales
1. Plataforma Web SaaS (acceso directo desde navegador)
2. Demos personalizadas gratuitas de 15 minutos para laboratorios pioneros
3. Canal digital directo: `info@biomed.umss.bo`

### 7.4 Relación con Clientes
1. Asistencia diagnóstica proactiva mediante semaforización de confianza
2. Diagnóstico remoto e interconsulta sincronizada en la nube
3. Confianza clínica: bloqueo de informes con cromosomas no validados

### 7.5 Fuentes de Ingresos
1. Suscripción mensual por acceso a la plataforma (modelo recurrente)
2. Ahorro operativo directo por reducción de horas-especialista en tareas mecánicas
3. Consultoría e integración con Sistemas de Información de Laboratorio (LIS)

### 7.6 Recursos Clave
1. Algoritmos de visión computacional (segmentación y clasificación, precisión >97%)
2. Arquitectura en la nube modular con actualización continua
3. Datasets clínicos anonimizados para entrenamiento y recalibración trimestral

### 7.7 Actividades Clave
1. Desarrollo y mejora continua de modelos de IA (detección de anomalías estructurales)
2. Diseño de UX clínica (reducción de carga cognitiva y fatiga visual)
3. Mantenimiento de plataforma, seguridad y persistencia de datos anonimizados

### 7.8 Socios Clave
1. Universidad Mayor de San Simón (UMSS) — respaldo institucional, I+D y validación
2. Laboratorios beta testers (IIBISMED-UMSS) — retroalimentación real de usabilidad y precisión
3. Proveedores de IT de salud — integración técnica con infraestructuras hospitalarias

### 7.9 Estructura de Costos
1. I+D: equipo fundador (CEO, CTO, CMO) y especialistas en IA
2. Infraestructura tecnológica: servidores en la nube, almacenamiento de imágenes de alta resolución, ciberseguridad
3. Validación clínica: auditorías periódicas de precisión, estudios de usabilidad y soporte al cliente

---

## 8. Supuestos, Riesgos, Restricciones y Dependencias

### 8.1 Supuestos

| # | Supuesto |
|---|---|
| S1 | Generar un borrador automático editable en <1 minuto reducirá el tiempo de procesamiento manual en un 60% |
| S2 | La señalización de baja confianza disminuirá la fatiga visual al eliminar inspecciones cromosoma por cromosoma |
| S3 | Los laboratorios objetivo tienen conectividad a internet suficiente para operar una plataforma web |
| S4 | Los citogenetistas adoptarán el sistema si la curva de aprendizaje es menor a 2 sesiones de uso |
| S5 | El modelo de suscripción es preferible a licencia única para laboratorios con presupuesto limitado |

### 8.2 Riesgos

| # | Riesgo | Impacto | Probabilidad | Mitigación |
|---|---|---|---|---|
| R1 | **Sesgo de automatización**: el especialista confía ciegamente en la IA, omitiendo verificación de anomalías no marcadas | Alto | Medio | Sistema de semaforización obligatorio; bloqueo de informe sin validación completa |
| R2 | **Conectividad limitada**: hospitales con red deficiente generan cuellos de botella en transferencia de imágenes de alta resolución | Alto | Medio | Compresión progresiva de imágenes; modo offline parcial en roadmap |
| R3 | **Baja tasa de activación**: usuarios no completan el flujo inicial y abandonan antes de percibir valor | Alto | Medio | Onboarding guiado; demo en 15 min; soporte técnico proactivo |
| R4 | **Resistencia al cambio**: citogenetistas senior rechazan delegar decisiones a la IA | Medio | Medio | Comunicación de transparencia algorítmica; Human-in-the-loop explícito |
| R5 | **Falsos negativos en anomalías raras**: precisión del modelo puede caer en patologías poco representadas en datasets de entrenamiento | Alto | Bajo | Recalibración trimestral; umbral de confianza conservador (85%); auditoría clínica |

### 8.3 Restricciones

| # | Restricción |
|---|---|
| RC1 | Ningún informe puede emitirse sin la validación manual del analista **y** la firma digital del supervisor |
| RC2 | El sistema no permite exportar el informe final si existen cromosomas con confianza <85% no validados manualmente |
| RC3 | Todos los datos de pacientes deben estar anonimizados antes de ser procesados o almacenados |
| RC4 | Los informes generados deben seguir estrictamente la nomenclatura ISCN vigente |
| RC5 | La plataforma debe ser compatible con navegadores modernos sin requerir instalación local |

### 8.4 Dependencias

| # | Dependencia | Tipo |
|---|---|---|
| D1 | Integración con Sistemas de Información de Laboratorio (LIS) existentes | Técnica |
| D2 | Cumplimiento con nomenclatura ISCN para generación automática de informes | Regulatoria |
| D3 | Alineación con normativas del Ministerio de Salud sobre trazabilidad y diagnóstico clínico | Regulatoria |
| D4 | Disponibilidad de datasets clínicos anonimizados para entrenamiento y recalibración del modelo | Técnica / Institucional |
| D5 | Respaldo y validación institucional de UMSS para fase de pruebas con IIBISMED-UMSS | Institucional |

---

## 9. Alcance del Proyecto

### En scope (incluido)
- Módulo de carga y registro de muestras (código anonimizado de paciente)
- Motor de IA para segmentación y clasificación automática de cromosomas
- Interfaz de edición interactiva (drag & drop, rotar, unir, dividir)
- Sistema de semaforización de confianza algorítmica
- Generación automática de nomenclatura ISCN
- Flujo de validación en dos niveles (analista + supervisor)
- Firma digital y emisión de informe final bloqueada por validación
- Panel de supervisión para auditoría de casos

### Fuera de scope (v1.0)
- Módulo de secuenciación genómica (NGS)
- Integración directa con equipos de microscopía (automatización de captura de imagen)
- Aplicación móvil nativa
- Modo offline completo

---

*Documento generado con base en `01_vision_negocio.txt` y análisis del notebook NotebookLM "Biomed - Plataforma IA Cariotipado".*
*Cuando esté disponible la plantilla oficial `\plantillas\BRD_TEMPLATE.md`, verificar alineación de encabezados.*
