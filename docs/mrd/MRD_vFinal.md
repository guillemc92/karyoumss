# Market Requirements Document (MRD) – BIOMED UMSS

**Propósito del MRD:** describir **el mercado, los usuarios y la oportunidad comercial** que justifican la construcción del producto. Responde a **"¿qué pide el mercado y por qué este producto ganará?"**.

Complementa al BRD (visión interna del negocio) y antecede al PRD (qué debe hacer el producto). Audiencia típica: *Product Management, Marketing, Ventas, Sponsor*.

---

## 0. Metadatos

| Campo | Valor |
| :---- | :---- |
| Producto | BIOMED UMSS – Intelligent Karyotyping Platform |
| Grupo | G04 |
| Versión | v1.0 |
| Fecha | Mayo 2026 |
| Product Manager / Autor | Ing. Guillermo Mamani Chambi |
| Revisores | Docente + stakeholders |
| Estado | Aprobado |
| Relación con BRD | BRD v3.5 |

---

## 1. Resumen ejecutivo

El mercado de diagnóstico citogenético en Bolivia presenta una oportunidad no atendida. Los laboratorios públicos y privados procesan más de 15,000 muestras anuales, pero el análisis sigue siendo 100% manual. Cada cariotipo toma entre 30 y 45 minutos por especialista, generando cuellos de botella diagnosticados y fatiga visual que incrementa el riesgo de error.

BIOMED UMSS es una plataforma SaaS de inteligencia aumentada que automatiza la segmentación y clasificación cromosómica, reduciendo el Time to Karyotype (TTK) a menos de 15 minutos. A diferencia de soluciones legacy (Ikaros, CytoVision) que cuestan más de $20,000 USD por nodo, BIOMED opera 100% web, sin hardware dedicado, con modelo de pago por reporte o suscripción anual.

El mercado objetivo inicial son los 5 laboratorios públicos de tercer nivel y 3 laboratorios privados en Bolivia, con una oportunidad de ingresos estimada en $180,000 USD anuales en el primer año, creciendo a $500,000 USD en el tercer año.

---

## 2. Visión del producto

**"Para los citogenetistas bolivianos que hoy pierden 45 minutos por muestra en análisis manual, BIOMED UMSS es una plataforma web de inteligencia aumentada que reduce el tiempo diagnóstico a 15 minutos, con transparencia algorítmica y cumplimiento normativo, a diferencia de sistemas legacy que cuestan más de $20,000 USD."**

---

## 3. Análisis de mercado

### 3.1 Tamaño de mercado

| Métrica | Valor | Fuente |
| :---- | :---- | :---- |
| TAM (*Total Addressable Market*) | 50,000 muestras/año en Bolivia | IIBISMED-UMSS, 2025 |
| SAM (*Serviceable Addressable Market*) | 15,000 muestras/año (laboratorios públicos y privados con capacidad de pago) | Análisis interno |
| SOM (*Serviceable Obtainable Market*) | 6,000 muestras/año en primeros 12 meses (20% de SAM) | Proyección comercial |

**Justificación TAM:** Bolivia tiene 9 departamentos, cada uno con al menos 1 laboratorio de referencia. El IIBISMED-UMSS procesa 5,000 muestras/año. Extrapolando, el mercado total estimado es de 50,000 muestras/año.

### 3.2 Tendencias del sector

- **Tendencia 1 – Digitalización de laboratorios clínicos:** La pandemia aceleró la adopción de sistemas de información de laboratorio (LIS) y telemedicina. El Ministerio de Salud impulsa la transformación digital de hospitales públicos.

- **Tendencia 2 – Democratización de IA en salud:** Modelos de código abierto (U-Net, EfficientNet) permiten a instituciones con presupuestos limitados acceder a tecnología de punta sin depender de proveedores extranjeros costosos.

- **Tendencia 3 – Regulaciones de privacidad más estrictas:** Ley 164 (Bolivia) y GDPR en la región exigen anonimización de datos de salud. Las soluciones cloud deben garantizar que los datos de pacientes no salgan de la jurisdicción local.

### 3.3 Factores regulatorios y de cumplimiento

- **Ley 164 (Bolivia):** Protección de datos personales. BIOMED implementa anonimización local con código CHN antes de cualquier procesamiento cloud.
- **ISO 15189:** Requisitos de calidad para laboratorios clínicos. BIOMED facilita la certificación mediante audit trail inmutable.
- **21 CFR Part 11 (FDA):** Estándar internacional para registros electrónicos. El audit trail con hash chain cumple este requisito para laboratorios que buscan certificación internacional.

### 3.4 Cadencia de Continuous Discovery

| Aspecto | Valor |
| :---- | :---- |
| Cadencia de entrevistas | Semanal (cada viernes) |
| Usuarios contactados por ciclo | 3 (1 citogenetista, 1 supervisor, 1 administrador de laboratorio) |
| Formato de hipótesis | *Cuando `<analista revisa cromosomas naranja>`, espero `<reducción de tiempo del 60%>`, porque `<solo revisa el 13% de los pares>`* |
| Backlog de hipótesis | Ver sección §12 |
| Output del track | Validaciones documentadas en M2 y M3 (entrevistas, pruebas de usabilidad) |

**Histórico de validación (M2/M3):** Se realizaron 3 entrevistas a citogenetistas del IIBISMED-UMSS y una prueba de usabilidad con el prototipo HTML. Todos los hallazgos están documentados en mod2informefinal.pdf y mod3informe2.pdf.

---

## 4. Segmentación y personas

### 4.1 Segmentos de clientes

| Segmento | Tamaño | Necesidad principal | Disposición a pagar | Origen M2 |
| :---- | :---- | :---- | :---- | :---- |
| Laboratorios públicos de tercer nivel | 5 laboratorios | Reducir tiempos de espera de pacientes, cumplir normas de calidad | $10-15 por reporte (limitado por presupuesto público) | IIBISMED-UMSS |
| Laboratorios privados de citogenética | 3 laboratorios | Diferenciación competitiva, mayor throughput, certificaciones internacionales | $20-30 por reporte o suscripción anual | Benchmark sector privado |
| Centros de investigación (UMSS) | 1 centro | Precisión en investigación, trazabilidad de datos, capacidad de reentrenamiento de modelos | $5,000 anuales (investigación) | UMSS |

### 4.2 Personas

#### Persona 1 – Dra. Valeria Ríos (Analista Citogenetista)

- **Origen M2:** mod2informefinal.pdf §3 (User Persona, págs. 13-14)
- **Rol:** Citogenetista senior en laboratorio público, 12 años de experiencia
- **Demografía:** 42 años, trabaja 8 horas diarias, procesa 15-20 muestras por semana
- **Objetivos:** Completar análisis rápido sin errores, mantener precisión diagnóstica >99%
- **Dolores actuales:** Fatiga visual después del cuarto caso diario, frustración por recortar cromosomas manualmente, desconfianza en sistemas "caja negra"
- **Comportamiento digital:** Usa sistema legacy (Ikaros) con interfaz de los 90s, no confía en la nube, prefiere instalación local
- **Frase representativa:** "El software debería ayudarme a detectar anomalías, no obligarme a recortar cromosomas manualmente."

#### Persona 2 – Dr. Javier Méndez (Supervisor / Garante Clínico)

- **Origen M2:** mod2informefinal.pdf §2.4 (Análisis de Stakeholders, pág. 4)
- **Rol:** Jefe de laboratorio, responsable legal de los reportes emitidos
- **Demografía:** 55 años, 25 años de experiencia, firma 200+ reportes al mes
- **Objetivos:** Cero errores diagnósticos, trazabilidad completa del trabajo de los analistas, cumplir normativas de acreditación
- **Dolores actuales:** Dificultad para auditar el trabajo de analistas sin un registro digital, ansiedad por posibles demandas por diagnóstico erróneo
- **Comportamiento digital:** Usa firma digital básica, requiere auditoría en papel como respaldo
- **Frase representativa:** "Si el sistema se equivoca y yo no lo noto por confiar ciegamente, el paciente sufre las consecuencias."

#### Persona 3 – Lic. Carlos Vargas (Administrador de Laboratorio)

- **Origen M2:** mod2informefinal.pdf §2.4 (Stakeholder IT, pág. 4)
- **Rol:** Administrador de TI del laboratorio
- **Demografía:** 38 años, 8 años en el cargo
- **Objetivos:** Mantener sistemas funcionando sin interrupciones, garantizar seguridad de datos, controlar costos operativos
- **Dolores actuales:** Instalaciones y actualizaciones manuales de software legacy, pérdida de datos al reinstalar, falta de soporte local
- **Comportamiento digital:** Prefiere cloud por facilidad de mantenimiento, pero tiene restricciones de seguridad por datos de pacientes
- **Frase representativa:** "Cada vez que se cae el servidor local, perdemos medio día de trabajo."

---

## 5. Jobs-to-be-Done

| JTBD ID | Cuando… | Quiero… | Para poder… |
| :---- | :---- | :---- | :---- |
| JTBD-01 | recibo una imagen de metafase de un paciente con sospecha de síndrome genético | que el sistema segmente y clasifique los cromosomas automáticamente | enfocarme solo en validar anomalías, no en tareas mecánicas |
| JTBD-02 | la IA clasifica un cromosoma con baja confianza | ver un mapa de calor que me muestre en qué banda se basó | entender por qué la IA dudó y tomar una decisión informada |
| JTBD-03 | valido un cariotipo completo y necesito emitir el reporte | que el sistema me impida firmar si hay cromosomas sin revisar | garantizar que ningún error humano o de IA pase desapercibido |
| JTBD-04 | un caso tiene implicaciones legales o necesita auditoría externa | acceder al audit trail inmutable con todos los cambios registrados | demostrar que el diagnóstico siguió el protocolo correcto |
| JTBD-05 | la IA no está disponible por fallo técnico | que el sistema siga funcionando en modo manual | no detener la operación del laboratorio |

---

## 6. Análisis competitivo

### 6.1 Tabla comparativa

| Criterio | BIOMED UMSS | Ikaros (MetaSystems) | CytoVision (Leica) | Do-nothing (manual) |
| :---- | :---- | :---- | :---- | :---- |
| Precio inicial | $0 capex (pago por reporte) | $20,000+ USD | $25,000+ USD | $0 (costo de tiempo) |
| Modelo de pago | SaaS o $15/reporte | Licencia perpetua + mantenimiento anual | Licencia perpetua + mantenimiento anual | N/A |
| Hardware requerido | Navegador web | Estación dedicada + dongle | Estación dedicada + microscopio acoplado | Microscopio + papel |
| Automatización | Segmentación + clasificación IA | Asistida (requiere mucha intervención) | Asistida | 0% |
| Transparencia IA | Semaforización + XAI (mapas de calor) | Caja negra | Caja negra | N/A |
| Auditoría | Hash chain inmutable (21 CFR Part 11) | Logs básicos editables | Logs básicos editables | Papel (alto riesgo) |
| Acceso remoto | 100% web | No | No | N/A |
| Soporte local | Bolivia (UMSS) | Internacional (costoso) | Internacional (costoso) | N/A |
| TTK por caso | <15 minutos | 25-35 minutos | 30-40 minutos | 45 minutos |

### 6.2 Positioning statement

**Para** los citogenetistas y supervisores de laboratorios bolivianos,
**que** hoy sufren fatiga visual, tiempos de análisis prolongados y falta de trazabilidad,
**nuestro** BIOMED UMSS
**es** una plataforma SaaS de inteligencia aumentada para cariotipado,
**que** automatiza la segmentación y clasificación cromosómica con transparencia algorítmica (XAI) y audit trail inmutable,
**a diferencia de** sistemas legacy como Ikaros o CytoVision que cuestan más de $20,000 USD y operan como caja negra,
**nuestro producto** ofrece acceso web, pago por uso y cumplimiento normativo local.

### 6.3 Ventaja competitiva sostenible

1. **Know-how de dominio local:** El equipo conoce los flujos de trabajo de laboratorios bolivianos, las restricciones de infraestructura y las regulaciones específicas.

2. **Tecnología de código abierto adaptada:** U-Net, EfficientNet y Grad-CAM son modelos públicos. BIOMED UMSS los entrena con datos locales, creando una barrera de datos (no de algoritmo).

3. **Modelo de pago accesible:** Cero capex y pago por reporte eliminan la barrera de entrada para laboratorios públicos con presupuestos limitados.

4. **Ecosistema académico:** La alianza con UMSS permite acceso a talento, datasets y validación clínica que competidores extranjeros no tienen.

---

## 7. Propuesta de valor

### 7.1 Value proposition canvas resumido

| Gains (Alegrías del cliente) | Pains (Frustraciones del cliente) | Gains relievers (Creadores de alegrías) | Pain relievers (Aliviadores de frustraciones) | Products & services |
| :---- | :---- | :---- | :---- | :---- |
| Diagnóstico más rápido (TTK <15 min) | Fatiga visual diaria | Semaforización visual (verde/naranja) | Atención dirigida solo a cromosomas dudosos | Plataforma web SaaS |
| Trazabilidad total de cada caso | Dificultad para auditar trabajo manual | Audit Trail inmutable con hash chain | Registro automático de cada corrección | Audit Trail digital |
| Confianza en decisiones de IA | Desconfianza en sistemas "caja negra" | XAI con mapas de calor (Grad-CAM) | Explicación visual de por qué la IA clasificó así | Módulo XAI |
| Cero inversión en hardware | Costos de licencias >$20,000 USD | Modelo pago por reporte o suscripción | Sin capex, solo opex | SaaS comercial |
| Cumplimiento normativo (21 CFR) | Riesgo de sanciones por no cumplir | Hash chain + MFA + anonimización CHN | Reportes listos para auditoría | Cumplimiento regulatorio |

---

## 8. Pricing y modelo de negocio

### 8.1 Modelo

**SaaS B2B con dos modalidades:**

| Modalidad | Precio | Incluye | Ideal para |
| :---- | :---- | :---- | :---- |
| Pago por reporte | $15 USD por reporte | Todo el flujo (carga a firma) + almacenamiento 30 días | Laboratorios con volumen bajo (<200 reportes/mes) |
| Suscripción anual | $500 USD/mes (≈$6,000 USD/año) | Hasta 500 reportes/mes, soporte prioritario, SLAs | Laboratorios con volumen alto (>200 reportes/mes) |
| Enterprise (setup) | $5,000 USD único | Integración con LIS, despliegue on-premise, capacitación | Hospitales públicos, institutos de investigación |

### 8.2 Comparativa con competidores

| Competidor | Modelo | Costo por año (100 reportes) | Costo por año (500 reportes) |
| :---- | :---- | :---- | :---- |
| BIOMED UMSS | SaaS + pago por uso | $1,500 USD (pago por reporte) | $6,000 USD (suscripción) |
| Ikaros | Licencia + mantenimiento | $20,000 + $4,000 mantenimiento | $20,000 + $4,000 mantenimiento |
| Manual | Tiempo de especialista | $15,000 en salario (estimado) | $45,000 en salario (estimado) |

### 8.3 Elasticidad precio

Las entrevistas con laboratorios indican disposición a pagar entre $10 y $20 por reporte. El precio de $15 está en el punto medio, validado con el IIBISMED-UMSS.

---

## 9. Go-to-market

### 9.1 Canales de adquisición

| Canal | Tipo | Inversión inicial | Estimación de alcance |
| :---- | :---- | :---- | :---- |
| Ministerio de Salud (B2G) | Directo público (licitaciones) | $0 (equipo comercial) | 3 laboratorios públicos |
| Asociaciones médicas (congresos) | Eventos | $500 (stand, materiales) | 50+ citogenetistas |
| Alianza UMSS | Académico | $0 (co-branding) | Todos los laboratorios referenciados por UMSS |
| Marketing digital | Google Ads (keywords: "cariotipo", "citogenética", "análisis cromosómico") | $200/mes | 5-10 leads/mes |

### 9.2 Estrategia de lanzamiento

| Fase | Duración | Actividades | KPI de éxito |
| :---- | :---- | :---- | :---- |
| **Pre-launch (beta cerrada)** | 1 mes | Piloto con IIBISMED-UMSS (50 casos reales), ajustes de UX/UI, documentación | 0 errores críticos, NPS >60 |
| **Launch** | 1 semana | Webinar con asociación de citogenetistas, publicación en redes académicas, nota de prensa en UMSS | 5 leads calificados |
| **Post-launch (meses 1-3)** | 3 meses | Capacitación a los primeros 3 laboratorios, seguimiento semanal, caso de éxito documentado | 3 clientes pagos, retención >90% |

### 9.3 Funnel AARRR inicial

| Etapa | Métrica | Meta (primer año) | Fuente de datos |
| :---- | :---- | :---- | :---- |
| **Acquisition** | visitas al sitio web/mes | 500 | Google Analytics |
| **Activation** | laboratorios que completan prueba piloto | 5 | CRM + logs del sistema |
| **Retention** | casos procesados por laboratorio/mes | >50 | Logs del sistema |
| **Revenue** | ARPU (Average Revenue Per Laboratory) | $6,000 USD/año | Facturación |
| **Referral** | nuevos laboratorios referidos por clientes existentes | 2 | CRM |

---

## 10. Métricas de éxito del producto

- **North Star Metric:** Time to Karyotype (TTK) < 15 minutos (medido desde carga de imagen hasta reporte firmado)

| KPI | Línea base | Meta año 1 | Meta año 2 | Método de medición |
| :---- | :---- | :---- | :---- | :---- |
| TTK promedio | 45 minutos (manual) | 15 minutos | 10 minutos | Logs del sistema |
| Laboratorios activos | 0 | 5 | 15 | CRM |
| Reportes procesados/mes | 0 | 500 | 2,000 | Logs del sistema |
| Tasa de adopción de XAI | N/A | >80% | >90% | Logs de XAI_VIEWED |
| NPS (Net Promoter Score) | N/A | >60 | >70 | Encuesta trimestral |
| Tasa de error diagnóstico | 5-8% (manual) | <1% | <0.5% | Validación clínica |
| Churn (cancelación de clientes) | N/A | <10% anual | <5% anual | CRM |

---

## 11. Requerimientos de mercado (alto nivel)

| ID | Requerimiento | Prioridad | Justificación | Origen |
| :---- | :---- | :---- | :---- | :---- |
| MRD-01 | Anonimización local (código CHN) antes de procesar en cloud | Must | Ley 164 Bolivia, privacidad del paciente | BR-01 |
| MRD-02 | Semaforización visual (verde/naranja) por umbral de confianza 85% | Must | Reduce fatiga visual, atención dirigida | BR-02 |
| MRD-03 | Bloqueo de reporte si hay cromosomas con baja confianza sin revisar | Must | Seguridad clínica, cero errores | BR-03, BR-R1 |
| MRD-04 | XAI (mapas de calor) para cromosomas con baja confianza | Must | Transparencia algorítmica, confianza del médico | BR-06 |
| MRD-05 | Audit Trail inmutable con hash chain | Must | Cumplimiento 21 CFR Part 11, defensa legal | BR-05 |
| MRD-06 | Segregación de roles: Analista edita, Supervisor firma | Must | Control jerárquico, responsabilidad legal | BR-07 |
| MRD-07 | Firma digital con MFA para Supervisor | Should | Seguridad adicional, cumplimiento regulatorio | BR-R4 |
| MRD-08 | Modo degradado elegante (manual puro si IA falla) | Should | Continuidad operativa, SLA | BR-08 |
| MRD-09 | Soporte para conexiones de baja latencia (<5 Mbps) | Must | Realidad de infraestructura en Bolivia | Hipótesis validada M2 |
| MRD-10 | Interfaz 100% web, sin instalación de software local | Must | Accesibilidad, reducción de costos de TI | Propuesta de valor |

---

## 12. Supuestos e hipótesis a validar

| ID | Hipótesis | Cómo validar | Criterio de éxito | Estado |
| :---- | :---- | :---- | :---- | :---- |
| H1 | Los citogenetistas prefieren validar solo cromosomas naranja (atención dirigida) en lugar de revisar todo el cariotipo | Prueba A/B con 5 analistas (prototipo M3) | 80% prefieren atención dirigida | ✅ validado (M2/M3) |
| H2 | Los mapas de calor (XAI) aumentan la confianza del analista en clasificaciones de baja confianza | Entrevistas + think-aloud (M2) | 70% reportan mayor confianza | ✅ validado (M2) |
| H3 | El bloqueo de reporte con naranjas sin resolver no genera frustración | Prueba de usabilidad | Tasa de éxito 100%, NPS >60 | 🔄 en curso (pendiente piloto) |
| H4 | Supervisores aceptan usar MFA (TOTP/huella) en flujo clínico | Encuesta a 5 supervisores | 100% lo completan sin asistencia | 🔄 pendiente |
| H5 | Laboratorios públicos en Bolivia tienen conexión a internet suficiente (>5 Mbps) para procesamiento cloud | Medición en 3 laboratorios | 80% tienen velocidad >5 Mbps | 🔄 pendiente |
| H6 | La tasa de corrección manual de cromosomas será <15% | Piloto con 100 casos reales | <15% de cromosomas requieren reubicación | 🔄 en curso |
| H7 | El TTK real será <15 minutos en condiciones reales de laboratorio | Medición con 50 casos piloto | Percentil 95 <15 minutos | 🔄 en curso |

---

## 13. Riesgos de mercado

| Riesgo | Prob. | Impacto | Mitigación | Responsable |
| :---- | :---- | :---- | :---- | :---- |
| Baja adopción por desconfianza en IA | Media | Alto | XAI (mapas de calor), pruebas piloto extensas, validación con UMSS | Product Manager |
| Competidor internacional lanza SaaS similar a menor precio | Baja | Alto | Diferenciación por datos locales (entrenamiento con metafases bolivianas), soporte en español, alianza UMSS | Marketing |
| Latencia de red en hospitales públicos | Alta | Medio | Modo degradado elegante, procesamiento asíncrono, compresión local | Arquitectura |
| Presupuesto insuficiente en sector público | Media | Medio | Modelo pago por reporte (sin capex), suscripción anual con descuento para públicos, búsqueda de financiamiento externo | Ventas |
| Cambios regulatorios (Ley de datos más estricta) | Baja | Medio | Arquitectura de anonimización local (CHN) fácil de adaptar, compliance by design | Legal |
| Resistencia al cambio de analistas con años de experiencia manual | Media | Media | Capacitación gratuita, UI pensada para reducir fricción (drag & drop similar a herramientas conocidas), casos de éxito documentados | Product Manager |

---

## 14. Trazabilidad

| MRD ID | BRD ID | PRD User Story | FSD (próximo) |
| :---- | :---- | :---- | :---- |
| MRD-01 | BR-01 | PRD-US-001, PRD-US-002 | FSD-UC-001 |
| MRD-02 | BR-02 | PRD-US-004 | FSD-UC-002, FSD-UC-003 |
| MRD-03 | BR-03, BR-R1, BR-R5 | PRD-US-008 | FSD-UC-004 |
| MRD-04 | BR-06 | PRD-US-005 | FSD-UC-003 |
| MRD-05 | BR-05 | PRD-US-010 | FSD-UC-005, FSD-UC-008 |
| MRD-06 | BR-07 | PRD-US-011 | FSD-UC-005 |
| MRD-07 | BR-R4 | PRD-US-011 | FSD-UC-005 |
| MRD-08 | BR-08 | PRD-US-013 | FSD-UC-007 |
| MRD-09 | Supuesto crítico | PRD-US-013 | FSD-UC-007 |
| MRD-10 | Propuesta de valor | Todas las US | Todos los UC |

---

## 15. Anexos

- **Entrevistas a usuarios:** mod2informefinal.pdf §2.5 (Plan de investigación) y §3.1 (Síntesis de insights)
- **Prototipo validado:** mod3informe2.pdf §4 (Testing y heurísticas)
- **Prototipo funcional:** https://guillemc92.github.io/karyoumss/
- **Benchmark detallado:** mod2informefinal.pdf §2 (Auditoría competitiva) y §6 (Matriz ERRC)
- **Análisis de stakeholders:** mod2informefinal.pdf §2.4
- **Métricas de mercado:** IIBISMED-UMSS, informes anuales 2024-2025

---

## 16. Registro de cambios

| Versión | Fecha | Autor | Cambio |
| :---- | :---- | :---- | :---- |
| v0.1 | Mayo 2026 | G. Mamani | Versión inicial basada en BRD v3.5 y hallazgos M2/M3 |
| v0.2 | Mayo 2026 | G. Mamani | Adición de personas (alineadas con M2), JTBD, pricing, riesgos |
| v1.0 | Mayo 2026 | G. Mamani | Versión final aprobada, lista para release/2.0.0 |

---

## Checklist mínimo

- [x] TAM/SAM/SOM con fuentes (IIBISMED-UMSS + análisis interno)
- [x] ≥ 2 personas completas (3 personas: Analista, Supervisor, Administrador)
- [x] ≥ 3 JTBD (5 JTBD documentados)
- [x] ≥ 2 competidores en matriz (3 competidores: Ikaros, CytoVision, Do-nothing)
- [x] *Positioning statement* en 1 frase
- [x] Pricing y *go-to-market* esbozados
- [x] North Star + 6 KPIs fechados
- [x] Requerimientos MRD-N-* priorizados (10 requerimientos)
- [x] 3 hipótesis a validar con criterio de éxito (7 hipótesis documentadas, 2 validadas)
- [x] Trazabilidad a BRD y PRD completada