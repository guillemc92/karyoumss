# Business Requirements Document (BRD)

**Propósito del BRD:** Formalizar las necesidades y restricciones de negocio que justifican la existencia del producto, independientemente de la solución técnica.

## 0. Metadatos

| Campo | Valor |
| :---- | :---- |
| Producto | BIOMED UMSS – Intelligent Karyotyping Platform |
| Grupo | G04 |
| Versión | v3.5 (Definitive Edition con resoluciones socráticas completas) |
| Fecha | Mayo 2026 |
| Sponsor de negocio | Dirección IIBISMED - UMSS |
| Stakeholders | Ministerio de Salud (Bolivia), Laboratorios Citogenéticos, Auditores Clínicos |
| Autores | Ing. Guillermo Mamani Chambi |
| Revisores | Docente + 1 grupo par |
| Estado | Aprobado |
| Insumo del Módulo Anterior | 01_vision_negocio.txt, tarea2.txt, mod2informefinal.pdf |

## 1. Resumen ejecutivo

BIOMED UMSS es una plataforma SaaS de inteligencia aumentada para diagnóstico citogenético. Transforma un proceso manual y fatigante (30-45 minutos) en un flujo asistido de atención dirigida (≤15 minutos). El pilar innegociable de la solución es el principio **Human-in-the-loop (HITL)**. Para prevenir el sesgo de automatización, el sistema aplica un **bloqueo automático a toda predicción con confianza menor al 85%**, forzando revisión manual, e incluye un motor de **Explicabilidad IA (XAI)** mediante mapas de calor. Acompañado de un Audit Trail inmutable (conforme a 21 CFR Part 11) y anonimización de borde (código CHN), BIOMED protege clínica y legalmente a las instituciones, garantizando precisión, soberanía de datos y escalabilidad en Bolivia.

## 2. Problema de negocio

El cariotipado manual consume hasta 45 minutos por muestra, causando fatiga extrema que aumenta el riesgo de falsos negativos en la segunda mitad del turno laboral. Un especialista topa su límite en 8-10 muestras diarias. Soluciones alternativas (on-premise) cuestan más de $20,000 USD por nodo, creando una barrera económica insalvable para laboratorios públicos. Esto genera un cuello de botella en diagnósticos de síndromes genéticos, afectando directamente al paciente y bloqueando la escalabilidad del IIBISMED-UMSS.

## 3. Personas / Usuarios objetivo

- **Persona 1: Analista Citogenetista (Operador)**
  *JTBD:* Ordenar y verificar los 46 cromosomas rápidamente. *Dolores:* Fatiga visual, segmentación píxel a píxel. *Ganancias:* Sugerencias pre-armadas, UI drag & drop fluida, XAI para entender por qué la IA clasificó un cromosoma de cierta forma.
- **Persona 2: Supervisor / Garante Clínico (Auditor)**
  *JTBD:* Asegurar que el reporte ISCN sea 100% certero y firmarlo legalmente. *Dolores:* Dificultad para auditar el trabajo manual previo sin un registro. *Ganancias:* Trazabilidad total (Audit Trail), alerta sobre correcciones hechas por el analista.

## 4. Propuesta de valor (VPC)

- **Creadores de Alegrías:** Semaforización predictiva visual (naranja=revisar, verde=validado); Mapas de calor (saliency maps) para justificación biológica (XAI).
- **Aliviadores de Frustraciones:** Eliminación del recorte manual de imágenes. Modo de degradación elegante que permite análisis manual puro si la IA cae o hay baja red.
- **Producto y Servicio:** Plataforma SaaS en la nube de procesamiento asíncrono con interfaz clínica de auditoría en dos niveles y motor ISCN estricto.

## 5. Panorama competitivo

- **1. Do-nothing (Proceso 100% manual):** Bajo costo de licencia, costo humano insostenible, 45 min/muestra.
- **2. Soluciones Legacy On-Premise (ej. Ikaros):** +$20,000 licencias + hardware, cerradas a su propio microscopio, mantenimiento costoso.
- **3. Plataformas Cloud de Automatización Total (Black-box AI):** Prometen 100% automatización, pero sufren de alucinaciones (artefactos) y falta de explicabilidad (riesgo legal muy alto para Bolivia).

## 6. Business Model Canvas

| Bloque | Elementos Clave |
| :---- | :---- |
| Segmentos | 1. Hospitales públicos (Tercer Nivel) 2. Laboratorios privados 3. Centros de investigación (UMSS) |
| Propuesta de Valor | 1. TTK ≤ 15 min 2. Cero capex en hardware 3. Privacidad y cumplimiento normativo (CHN) |
| Canales | 1. Ventas B2G (Min. Salud) 2. Alianzas universitarias 3. Congresos médicos |
| Relación Clientes | 1. Soporte especializado 2. Onboarding clínico 3. Contratos SLA garantizados |
| Flujos Ingreso | 1. Pago por reporte ($15) 2. Suscripción SaaS Anual 3. Setup de integración LIS |
| Recursos Clave | 1. Algoritmos en R&D 2. Datasets anonimizados 3. Infraestructura Cloud Híbrida |
| Actividades Clave | 1. Entrenamiento IA (MLOps) 2. Mantenimiento SaaS 3. Auditoría de seguridad |
| Socios Clave | 1. Ministerios y Sedes 2. Proveedores Cloud 3. Fabricantes de microscopios (APIs) |
| Est. Costos | 1. Cloud Storage & GPU 2. Desarrollo e I+D 3. Costos legales y certificaciones |

## 7. Objetivos de negocio (SMART)

1. **Reducción de Tiempo:** Disminuir el Time to Karyotype (TTK) de 45 a 15 minutos en el IIBISMED-UMSS en el primer trimestre post-lanzamiento.
2. **Sostenibilidad y ROI:** Alcanzar un volumen de 500 muestras/mes por laboratorio y un Payback Period de 18 a 24 meses.

### Business Case — ROI y NPV

| Concepto | Valor | Base de cálculo |
| :---- | :---- | :---- |
| **Precio por reporte** | $15 USD (público) / $25 USD (privado) | MRD §3.1 |
| **Volumen año 1** | 6,000 muestras (SOM — 20% del SAM) | MRD §3.1 |
| **Ingresos año 1** | ~$108,000 USD (6,000 × $15 promedio ponderado) | Proyección conservadora |
| **Ingresos año 3** | ~$500,000 USD (crecimiento 8 laboratorios × 500 muestras × 12 meses) | MRD §3.1 |
| **Costo desarrollo v1.0** | $150,000 USD (6 meses × equipo 3 personas) | PRD §10 Restricciones |
| **Costo operativo anual** | ~$36,000 USD (cloud GPU + soporte + 21 CFR compliance) | Estimación infraestructura |
| **Payback Period** | **18–24 meses** | ($150,000 + $36,000) / ($108,000 - $36,000) ≈ 2.6 años ajustado por ramp-up |
| **NPV (5 años, tasa 12%)** | **~$280,000 USD** | Flujos: -186K, +72K, +300K, +420K, +464K descontados |
| **ROI al año 3** | **~233%** | ($500K - $150K) / $150K × 100 |

**Sensibilidad del modelo:** El breakeven se alcanza en el mes 20 si la adopción del SOM es ≥15%. Si cae al 10%, el breakeven se extiende a 30 meses — considerado aceptable dado el perfil de riesgo del sector salud pública.
3. **Estandarización:** Lograr que el 100% de los informes emitidos cumplan la gramática médica ISCN 2024 desde el primer día de despliegue.

## 8. Métricas clave de éxito

- **North Star Metric:** Time to Karyotype (TTK) < 15 minutos.
- **KPI 1 (Éxito Clínico):** Sensibilidad diagnóstica > 99% (tasa de detección de anomalías estructurales).
- **KPI 2 (Éxito Operativo):** Tasa de procesamiento (throughput) mantenida en ≥ 500 muestras/mes por nodo.
- **KPI 3 (Resiliencia):** Porcentaje de tiempo en modo degradado < 5% mensual.

## 9. Matriz RACI

| Proceso / Tarea | Analista | Supervisor | Sist. BIOMED |
| :---- | :---- | :---- | :---- |
| Carga y Anonimización de imagen | R | I | A |
| Validación en semáforo naranja (<85%) | R/A | C | C |
| Firma Digital y Emisión LIS | I | R/A | C |

## 10. Alcance (Scope)

- **En alcance:** Segmentación IA; Interfaz HITL; Bloqueo condicional al 85%; Explicabilidad IA (Saliency Maps); Audit Trail inmutable (21 CFR Part 11); Reglas determinísticas para ISCN; Modo de Degradación Elegante.
- **Fuera de alcance:** Diagnóstico autónomo completo sin revisión humana (prohibido); Secuenciación Genómica (NGS).

## 11. Requerimientos de negocio (MoSCoW)

| ID | Requerimiento | Prioridad |
| :---- | :---- | :---- |
| BR-01 | Anonimización Nativa (Código CHN) obligatoria antes de procesar imagen. | Must |
| BR-02 | Semaforización visual de objetos en UI (naranja para dudas, verde verificado). | Must |
| BR-03 | Bloqueo estricto de informe para predicciones con <85% de confianza algorítmica. | Must |
| BR-04 | Generación de string ISCN a través de un motor determinístico clínico, NO de la IA. | Must |
| BR-05 | Audit Trail inmutable del caso (quién corrigió, rotó o unió fragmentos). Debe cumplir 21 CFR Part 11 (FDA). | Must |
| BR-06 | (XAI) Explicabilidad de IA para mostrar en qué banda se basó el modelo. | Must |
| BR-07 | Segregación funcional: Analista edita, Supervisor firma. | Must |
| BR-08 | Modo Degradación Elegante: Soporte para flujo 100% manual si hay caída de IA. | Must |
| BR-09 | Eliminación de "Artefactos" (alucinaciones) con un clic. | Should |
| BR-10 | Exportar reporte final en formato HL7 FHIR DiagnosticReport. | Should |
| BR-11 | Importar imágenes desde DICOM (no solo TIFF/PNG). | Could |

## 12. Reglas de negocio

- **BR-R1 (Integridad Médica):** El botón de "Emitir Reporte" debe estar inhabilitado lógicamente si el caso tiene cromosomas en estado de "Conflicto" o sin par asignado.
- **BR-R2 (Auditoría Aleatoria):** El sistema marcará un 5% aleatorio de los cromosomas clasificados como "alta confianza" (>86%) para revisión obligatoria, mitigando el exceso de confianza del analista.
- **BR-R3 (Reentrenamiento seguro):** Las correcciones manuales solo alimentan el dataset de reentrenamiento si el analista consultó XAI (xai_consulted=true) Y la corrección fue validada por un segundo especialista o por validación cruzada. Correcciones de analistas con sesgo sistemático (desviación >2σ del equipo) se excluyen automáticamente.
- **BR-R4 (Firma electrónica regulatoria):** La firma digital del Supervisor debe cumplir 21 CFR Part 11. Requisitos: (a) autenticación multifactor (MFA) obligatoria antes de firmar, (b) la firma está vinculada exclusivamente al supervisor autenticado, (c) el sistema registra el método de autenticación usado, (d) la firma no es reutilizable entre sesiones. Contraseña sola no es suficiente.

## 13. Requisitos no funcionales de negocio (NFRs)

| ID | Categoría | Requisito | Cumplimiento / Métrica |
| :---- | :---- | :---- | :---- |
| NFR-01 | Privacidad | Datos personales (PII) no salen del nodo institucional, protegiendo el Secreto Médico (Ley Bol.). | Anonimización local obligatoria |
| NFR-02 | Disponibilidad | SLA de 99.5% de uptime en horarios hábiles de laboratorio (07:00 a 19:00). | Tiempo máximo de degradación: 2 horas continuas |
| NFR-03 | Usabilidad/Ergonomía | Contrastes de colores que prevengan la fatiga visual bajo estándares WCAG 2.1 AA. | Auditoría periódica |
| NFR-04 | Rendimiento | TTK garantizado: <15 minutos en 95% de los casos con conexión a internet >5 Mbps. | Monitoreo continuo |
| NFR-05 | Audit Trail | Cumplimiento 21 CFR Part 11 (FDA) para registros electrónicos. | Hash chain SHA256 + timestamping externo + almacenamiento inmutable. Costo estimado: <$0.03 por caso. |
| NFR-06 | Interoperabilidad | Exportación HL7 FHIR y soporte DICOM. | BR-10 (Should), BR-11 (Could) |
| NFR-07 | Seguridad / Cumplimiento | La firma del Supervisor debe cumplir 21 CFR Part 11 (firma electrónica robusta). | Autenticación multifactor (MFA) obligatoria. Opciones: token TOTP, huella digital, tarjeta inteligente, o biometría facial. Contraseña sola no es suficiente. |

## 14. Restricciones y supuestos

- **Supuesto Crítico:** Los laboratorios públicos en Bolivia pueden sufrir latencia de red; el sistema debe soportar compresión local (tiling) en el borde para mitigar subidas lentas.
- **Supuesto de Capacitación:** Los analistas reciben capacitación en uso de XAI antes de que sus correcciones alimenten el reentrenamiento del modelo.
- **Supuesto de Infraestructura:** El costo incremental de cumplimiento 21 CFR Part 11 (<$0.03/caso) es aceptable frente al valor clínico y legal.
- **Restricción:** El software es clasificado como Software as a Medical Device (SaMD) de apoyo, no como sistema de diagnóstico autónomo.

## 15. Dependencias externas

- Adopción vigente del comité internacional de la gramática ISCN 2024.
- Conexión mediante HL7 FHIR para empujar el reporte firmado al LIS Hospitalario.

## 16. Riesgos de negocio

| Riesgo | Probabilidad / Impacto | Mitigación |
| :---- | :---- | :---- |
| Sesgo Automatización (Humano confía en fallos >86%) | Media / Crítico | Explicabilidad (XAI) + 5% de auditoría cruzada obligatoria aleatoria (BR-R2). |
| Deriva de IA con reentrenamiento sesgado (aprende vicios humanos) | Media / Alto | Filtro de calidad: solo correcciones con XAI consultado + validación cruzada + exclusión de analistas con sesgo >2σ (BR-R3). |
| Fuga de Datos Sensibles (PII) | Baja / Alto | Arquitectura de anonimización local obligatoria (Código CHN). |
| Latencia Red ralentiza TTK | Alta / Medio | Procesamiento híbrido y compresión (tiling) + SLA TTK 95% <15 min. |
| Modo degradado prolongado afecta rentabilidad | Media / Medio | Límites estrictos (2h continuas, 8h/mes) + penalidad a BIOMED si excede + detección automática. Modo Degradado 3 (caída total) no se factura. |
| Costo de cumplimiento 21 CFR Part 11 | Baja / Bajo | Estimación incluida en modelo de negocio (<$0.03/caso). Opción de nivel alternativo para laboratorios con presupuesto restringido. |
| Pérdida de mapeo CHN por laboratorio | Baja / Alto | Mecanismo de hash salado reversible por el laboratorio, no por BIOMED (sección 23). |

## 17. Gobernanza y aprobación

Firmado y aprobado bajo la directriz del módulo 4, aislando las decisiones técnicas (ver documento FSD/DTI) para mantener la pureza de las necesidades del negocio.

## 18. Trazabilidad

El flujo de derivación de este documento impactará los siguientes niveles: BRD v3.5 → MRD → PRD (User Stories) → FSD (Criterios Gherkin) → DTI (Arquitectura).

## 19. Glosario y referencias

- **HITL (Human-in-the-loop):** Paradigma donde la IA sugiere y el humano decide.
- **ISCN:** International System for Human Cytogenomic Nomenclature.
- **XAI (Explicabilidad de IA):** Capacidad de la IA de justificar su decisión visualmente (Saliency Maps).
- **TTK:** Time to Karyotype.
- **21 CFR Part 11:** Regulación FDA para registros electrónicos, firmas electrónicas y audit trails.
- **MFA:** Autenticación Multifactor.
- **CHN:** Código de Historia Clínica Anonimizado.

## 20. Registro de cambios

| Versión | Fecha | Autor | Cambio |
| :---- | :---- | :---- | :---- |
| v3.1 | Mayo 2026 | G. Mamani | Integración Socrática (XAI, Audit Trail, Degradación) |
| v3.2 | Mayo 2026 | G. Mamani | Migración a BRD_TEMPLATE oficial con 20 secciones |
| v3.3 | Mayo 2026 | G. Mamani | Incorporación NFRs, BR-10, BR-11, BR-R3, sección 21, sección 22 |
| v3.4 | Mayo 2026 | G. Mamani | Resolución observaciones socráticas: licencia perpetua (versión congelada), límites modo degradado, costo 21 CFR Part 11, sección 23 (retención diferenciada) |
| v3.5 | Mayo 2026 | G. Mamani | Adiciones finales: NFR-07 (MFA para Supervisor), BR-R4 (firma regulatoria), mecanismo detección automática modo degradado (sección 22), hash salado para recuperación de CHN (sección 23), sección 25 (gestión de cambios técnico-negocio) |

## 21. Propiedad de Datos y Propiedad Intelectual

**Modelo de propiedad compartida con derecho de explotación comercial para BIOMED:**

| Aspecto | Dueño | Condiciones |
| :---- | :---- | :---- |
| Dataset de entrenamiento original (imágenes anonimizadas) | UMSS / IIBISMED | Datos generados con fondos públicos. |
| Modelo de IA desarrollado (versión base entregada) | Copropiedad UMSS + BIOMED | Ambos son copropietarios del modelo base. |
| Explotación comercial del modelo | BIOMED (licencia exclusiva) | UMSS otorga a BIOMED licencia exclusiva para comercializar el modelo, mejoras y derivados. |
| Uso académico por UMSS | UMSS (licencia perpetua gratuita) | BIOMED otorga a UMSS licencia perpetua, libre de regalías, para la VERSIÓN ESPECÍFICA del modelo entregada al cierre del proyecto. Permite uso académico, investigación y despliegue interno no comercial. |
| Mejoras post-entrega (nuevas versiones del modelo) | BIOMED (propiedad exclusiva) | UMSS recibe licencia académica preferencial para estas mejoras bajo acuerdo comercial separado. |
| Actualizaciones de seguridad críticas (primeros 24 meses) | BIOMED | Incluidas en el costo del proyecto. |
| Parches de infraestructura y mantenimiento continuo (post 24 meses) | Negociación anual | UMSS puede optar por acuerdo de soporte anual (5-10% del costo original del proyecto). |
| Reportes clínicos generados | Hospital / Laboratorio (paciente) | BIOMED no retiene copia después de 30 días (ver sección 23). |
| Métricas agregadas anonimizadas | BIOMED | Para mejora continua y benchmarks internos. |

## 22. Acuerdo de Nivel de Servicio (SLA) para Modo Degradado

**Niveles de servicio durante fallos de IA:**

| Nivel | Condición | TTK | Acción comercial | Facturación | Límite |
| :---- | :---- | :---- | :---- | :---- | :---- |
| Normal | IA disponible | 15 min | Normal | 100% del fee | Sin límite |
| Degradado 1 | IA lenta (>30s) pero responde | 20 min | Notificar laboratorio | 80% del fee | Sin límite |
| Degradado 2 | IA caída, modo manual asistido | 30 min | Crédito automático | 50% del fee | Sin límite |
| Degradado 3 | Caída total sin IA | 45 min (manual puro) | Crédito automático | 0% (no se cobra) | 2h continuas / 8h mensuales |

**Mecanismo de detección automática de niveles de servicio:**

El sistema monitorea en tiempo real las siguientes métricas por cada petición de procesamiento:

| Métrica | Umbral Modo Degradado 1 | Umbral Modo Degradado 2 | Umbral Modo Degradado 3 |
| :---- | :---- | :---- | :---- |
| Tiempo de respuesta de IA | >30 segundos | N/A (IA responde lento) | N/A |
| Tasa de error de IA (5xx) | <1% | >10% en ventana 5 min | >50% en ventana 5 min |
| Disponibilidad de GPU | 100% | Parcial | 0% |
| Timeout de inferencia | <5% | >10% en ventana 5 min | >30% en ventana 5 min |

**Detección y facturación automática:**

1. El sistema registra en cada transacción el modo de servicio real (Normal / D1 / D2 / D3).
2. Al final del ciclo de facturación (mensual), el sistema:
   - Suma el tiempo en cada modo.
   - Calcula el crédito aplicable según la tabla de niveles.
   - Genera automáticamente la factura con el crédito aplicado.
3. El laboratorio recibe un reporte mensual de calidad de servicio que muestra:
   - Porcentaje de transacciones en cada modo.
   - Tiempo total en modo degradado.
   - Crédito aplicado y su justificación (con timestamps de los incidentes).
4. No se requiere reclamación manual por parte del laboratorio. El crédito es automático.
5. El laboratorio puede auditar las métricas en cualquier momento a través del panel de administración.

**Imparcialidad:** Las métricas son objetivas (latencia, errores HTTP, disponibilidad de GPU). El código que las calcula es abierto a auditoría del laboratorio si lo solicita.

**Cláusulas de garantía y penalidades:**

1. El sistema garantiza TTK <15 minutos en el 95% de los casos con conexión estable (>5 Mbps). Si este umbral no se alcanza en un mes calendario, el laboratorio recibe un descuento proporcional en la factura del mes siguiente.

2. Si el tiempo en Modo Degradado 3 excede los límites (2 horas continuas o 8 horas acumuladas en un mes) por causa imputable a BIOMED, el laboratorio recibe un crédito del 100% del fee mensual.

3. El laboratorio no tiene incentivo para cambiar a software antiguo durante una caída porque:
   - Sus datos y casos activos ya están dentro de la plataforma BIOMED.
   - La interfaz y el flujo de trabajo son idénticos al modo normal.
   - Migrar a otro sistema implica fricción, curva de aprendizaje y pérdida de continuidad operativa.
   - El Modo Degradado 3 es temporal y BIOMED tiene incentivos financieros para restaurar la IA rápidamente.

4. Tiempo máximo de degradación continua: 2 horas. Si se excede, se activa failover a GPU secundaria.

## 23. Retención de Datos y Protección Legal

BIOMED implementa una política de retención diferenciada que equilibra privacidad del paciente, cumplimiento normativo y defensa legal.

| Tipo de dato | Retención | Propósito | Identificable? | Cumplimiento |
| :---- | :---- | :---- | :---- | :---- |
| Reporte clínico completo | 30 días | Operación diaria, entrega al laboratorio | Sí (PII: nombre, fecha nacimiento, CHN) | Eliminación irreversible después de 30 días |
| Metadatos de auditoría (sin PII) | 10 años | Defensa legal, trazabilidad forense, reconstrucción de diagnóstico | No (solo CHN anonimizado + acciones + timestamps + hashes + versiones de modelo + predicciones) | Almacenamiento inmutable, exportable para peritaje |
| Bitácora forense (hash chain) | 10 años | Verificación de integridad del audit trail | No | Inalterable por diseño |
| Modelo de decisiones de IA (logits, confianzas) | 10 años | Reconstrucción de qué predijo la IA en el momento del diagnóstico | No | Almacenado con metadatos de auditoría |
| Hash de paciente (salado) | 10 años | Recuperación forense si el laboratorio pierde su mapeo | No (hash irreversible) | Almacenado con CHN |

**Mecanismo de recuperación de mapeo CHN (hash salado):**

Para casos donde el laboratorio pierda su base de datos local de mapeo CHN->PII, BIOMED implementa un mecanismo de recuperación sin almacenar PII:

1. En el momento de la anonimización, el laboratorio genera un hash irreversible (SHA256 con sal secreta del laboratorio) del identificador único del paciente (ej: historia clínica).
2. El laboratorio envía a BIOMED: CHN + hash_paciente.
3. BIOMED almacena el hash_paciente junto al CHN en los metadatos de auditoría.
4. Si el laboratorio pierde su mapeo, regenera el hash del paciente sospechoso y consulta a BIOMED.
5. BIOMED responde con los metadatos de auditoría asociados a ese hash.
6. El laboratorio nunca pierde la capacidad de recuperación forense. BIOMED nunca almacena PII reversible.

El laboratorio es responsable de la custodia de su sal secreta. Si la pierde, no hay recuperación posible por diseño.

**Principios operativos:**

1. BIOMED no almacena el mapeo entre CHN y PII. Ese mapeo reside exclusivamente en el laboratorio cliente.
2. Para una demanda por diagnóstico erróneo, el laboratorio debe proporcionar el CHN o el hash_paciente al tribunal. BIOMED entrega los metadatos de auditoría asociados (sin PII).
3. La bitácora forense permite demostrar: qué usuario hizo qué acción, cuándo, con qué versión del modelo, qué predijo la IA, y si el usuario consultó XAI.
4. Esta separación protege a BIOMED legalmente sin violar la privacidad del paciente ni retener datos clínicos sensibles más allá de lo necesario.

**Excepción legal:** Si una orden judicial exige retener un reporte clínico específico más allá de 30 días, BIOMED cumplirá la orden y notificará al laboratorio correspondiente.

## 24. Referencias cruzadas

| Sección BRD | Documento relacionado | Responsable |
| :---- | :---- | :---- |
| 11 (BR-01 a BR-11) | PRD v1.0 (User Stories) | Product Manager |
| 12 (BR-R1 a BR-R4) | FSD v1.0 (Criterios Gherkin) | Technical Lead |
| 13 (NFR-01 a NFR-07) | DTI / Arquitectura | System Architect |
| 21 (Propiedad intelectual) | Contrato UMSS-BIOMED | Legal / Dirección |
| 22 (SLA Degradado) | Acuerdo de Nivel de Servicio | Operaciones / Ventas |
| 23 (Retención de datos) | Política de Privacidad / Términos de Servicio | Legal / DPO |

## 25. Gestión de Cambios y Resolución de Conflictos Técnico-Negocio (NUEVA SECCIÓN)

Cuando durante el desarrollo del FSD se identifica una regla de negocio del BRD que es técnicamente imposible de implementar o excede el presupuesto asignado, se activa el siguiente proceso:

**Paso 1: Documentación de la restricción**
- El Technical Lead documenta la imposibilidad con evidencia técnica (prueba de concepto, benchmark, cotización de infraestructura).
- Se estima el costo alternativo o la solución parcial.

**Paso 2: Mesa de resolución (48 horas máximo)**
- Participan: Product Manager, Technical Lead, Sponsor de negocio.
- Opciones de resolución (orden de prioridad):
  - a) Solución alternativa técnica de menor costo que cumple el espíritu de la regla.
  - b) Ajuste de presupuesto (si el valor de negocio justifica el sobrecosto).
  - c) Degradación de prioridad (Must -> Should) con aceptación formal del sponsor.
  - d) Exclusión de la regla para v1.0 con plan de inclusión en v1.1.

**Paso 3: Actualización versionada**
- El BRD se incrementa a v3.x+1 con un registro de cambio que documenta la desviación.
- El FSD se actualiza reflejando la decisión.
- El PRD se ajusta en las user stories afectadas.

**Paso 4: Comunicación a stakeholders**
- Se notifica a todos los firmantes del BRD original.
- Se actualiza la matriz de trazabilidad (sección 24).

**Principio rector:** El BRD no es un documento estático. Es un contrato vivo. Cada cambio se versiona, se justifica y se firma. No hay cambios unilaterales sin mesa de resolución.

---

**Fin del documento BRD v3.5**