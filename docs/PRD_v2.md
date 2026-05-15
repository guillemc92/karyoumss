# **Product Requirements Document (PRD) – BIOMED UMSS**

**Propósito del PRD:** Describir qué debe hacer el producto para cumplir los requerimientos del MRD y BRD, con nivel suficiente para que diseño, ingeniería y QA puedan proceder. Responde a "¿qué hace el producto?" (no cómo lo hace).  
**Audiencia:** Product, Diseño (UX/UI), Ingeniería, QA.

## ---

**0\. Metadatos**

| Campo | Valor   |
| :---- | :---- |
| Producto | BIOMED UMSS – Intelligent Karyotyping Platform |
| Grupo | G04 |
| Versión | v1.0 (Definitive PRD) |
| Fecha | Mayo 2026 |
| Product Manager / Autor | Ing. Guillermo Mamani Chambi |
| Revisores | Docente \+ Tech Lead \+ QA |
| Estado | Aprobado |
| BRD de referencia | BRD v3.5 |
| MRD de referencia | MRD v1.0 |
| Insumos M2 (UI/UX) | mod2informefinal.pdf, mod3informe2.pdf, wireframes Figma, prototipo HTML |
| Fase Spec Kit cubierta | Specify ✅ / Plan ⬜ / Tasks ⬜ / Implement ⬜ |
| Prompts utilizados | PR-PRD-001, PR-PRD-002, PR-PRD-003 |

## **0.1 Constitution (Spec Kit)**

* **Principio 1 (Privacidad Innegociable):** Nunca se procesarán datos filiatorios (PII) fuera de la jurisdicción local; la tokenización CHN ocurre siempre en el borde.  
* **Principio 2 (Human-in-the-loop Restrictivo):** El sistema nunca emitirá un diagnóstico final de manera autónoma; todo hallazgo con un *confidence score* \<85% quedará bloqueado hasta revisión manual.  
* **Principio 3 (Explicabilidad y Auditoría):** Toda decisión de reclasificación o rotación debe ser auditable y registrada de forma inmutable, priorizando mapas de calor (XAI) para mitigar el sesgo algorítmico.

## ---

**1\. Resumen Ejecutivo**

El producto BIOMED UMSS transformará el flujo de análisis citogenético mediante una plataforma web centrada en "Inteligencia Aumentada". Traduciendo las directrices del BRD v3.5, el producto entregará una interfaz de usuario interactiva (drag & drop) donde la Inteligencia Artificial actúa como un "borrador avanzado". El sistema exigirá interacción explícita (resolución de conflictos en pares naranjas) y una firma final jerárquica (supervisor). El resultado final es la reducción del Time to Karyotype (TTK) a menos de 15 minutos, manteniendo una tasa de falsos negativos de 0% gracias al control clínico humano.

## **2\. Alcance (Scope)**

### **2.1 En alcance**

* Módulo de ingesta y tokenización automática (CHN) de archivos TIFF.  
* Panel interactivo SVG/Canvas de edición de cromosomas (Drag & Drop, Rotar, Unir, Dividir).  
* Motor visual de Semaforización: Verde (≥85% confianza) y Naranja (\<85% o conflicto).  
* Explicabilidad de IA (XAI) mediante Saliency Maps activables por demanda.  
* Flujos de aprobación segregados: Analista (prepara) y Supervisor (audita/firma).  
* Generador determinístico de reportes ISCN 2024 en PDF.  
* Registro inmutable de auditoría (Audit Trail) por cada muestra.

### **2.2 Fuera de alcance**

* Soporte para secuenciación de nueva generación (NGS) o microarrays (CMA).  
* Toma fotográfica directa desde microscopios conectados por hardware local.  
* Aplicaciones nativas móviles (iOS/Android) para la mesa de edición.

## **3\. Usuarios / Personas**

* **Analista Citogenetista (Operador Principal):** Especialista encargado de cargar muestras, lidiar con la UI de edición, corregir a la IA en los cromosomas dudosos (naranjas) y dejar el caso listo. Requiere interfaz rápida y baja fatiga visual.  
* **Supervisor / Médico Especialista (Auditor):** Autoridad médica. Accede para revisar las alertas (cromosomas que el analista modificó o que la IA dudaba), confirmar la fórmula ISCN y firmar. Requiere trazabilidad absoluta.

## **4\. Casos de uso de alto nivel (Epics)**

1. **Ingesta y Tokenización Segura:** Carga de imagen TIFF y asignación del código CHN-YYYY-NNNN.  
2. **Resolución de Cariotipo (Mesa de Edición):** Manipulación de objetos cromosómicos, validación de la propuesta algorítmica y confirmación visual.  
3. **Generación y Auditoría del Reporte ISCN:** Verificación final del supervisor basada en el Audit Trail y emisión del PDF firmado digitalmente.

## **5\. User Stories Detalladas**

| ID | User Story | Criterios de Aceptación (BDD/Gherkin) | Prioridad   |
| :---- | :---- | :---- | :---- |
| **US-01** | Como *Sistema*, quiero anonimizar la imagen mediante un código CHN para evitar fugas de PII. | Dado un TIFF con datos filiatorios, cuando se sube al portal, entonces el sistema renombra el objeto a "CHN-YYYY-NNNN" y lo envía al bucket sin metadatos DICOM/PII. | Must |
| **US-02** | Como *Analista*, quiero que los cromosomas dudosos se marquen en naranja para priorizar mi revisión. | Dado que la IA devuelve un confidence \< 0.85, cuando se renderiza el cariograma, entonces ese cromosoma debe tener borde/highlight naranja e inhabilitar el botón "Cerrar Caso". | Must |
| **US-03** | Como *Analista*, quiero arrastrar y soltar un fragmento al par correcto para corregir a la IA. | Dado el modo de edición activado, cuando arrastro el objeto A sobre la celda del Par 21, entonces la UI actualiza el conteo, y registra la acción "Move: Unclassified \-\> Pair 21" en el log de auditoría. | Must |
| **US-04** | Como *Analista*, quiero ver el Saliency Map de un cromosoma para entender por qué la IA lo clasificó así. | Dado un cromosoma con clasificación, cuando hago clic en "Ver Explicabilidad", entonces se muestra una superposición térmica de las bandas G evaluadas. | Should |
| **US-05** | Como *Supervisor*, quiero firmar y generar el PDF final solo si no hay conflictos pendientes. | Dado un caso validado por el analista, cuando presiono "Firmar Reporte", entonces el motor de lógica determina la cadena ISCN y genera el PDF con el sello y código CHN. | Must |

## **6\. Requerimientos no funcionales (NFRs de producto)**

* **Rendimiento (NFR-01):** La carga del borrador de cariotipo en la SPA (React) no debe tardar más de 2 segundos; el motor de IA en backend responde en \<15s.  
* **Auditoría (NFR-02):** Todo evento de drag\&drop o reclasificación debe ser persistido en la base de datos de auditoría con timestamp y UserID en \<500ms.  
* **Disponibilidad (NFR-03):** Uptime de 99.5% durante el turno laboral clínico (07:00 a 19:00 hrs).

## **7\. Reglas de negocio (Business Rules \- BR)**

* **BR-01 (Bloqueo de Firmas):** Un caso no puede transicionar al estado FINALIZADO si existe al menos 1 objeto cromosómico en estado CONFLICTO o NARANJA sin resolución explícita.  
* **BR-02 (Segregación RC6):** El Analista que preparó el caso no puede ser el mismo usuario que lo aprueba en el rol de Supervisor (restricción de seguridad).  
* **BR-03 (ISCN Determinístico):** El string ISCN jamás se infiere por Machine Learning. Debe generarse a partir de un motor de reglas de software tradicional (árbol de decisión rígido).

## **8\. Supuestos e Hipótesis a validar**

* **H1 (Latencia Red Boliviana):** Se asume que los laboratorios pueden tener baja velocidad de subida; por ende, se implementará compresión progresiva (tiling) local antes del envío.  
* **H2 (Fatiga Visual):** El uso del modo oscuro y bordes semaforizados reducirá el tiempo por caso y la fatiga visual en un 60% frente al proceso legado.

## **9\. Dependencias**

* Motor algorítmico (Mask R-CNN / TorchServe) expuesto vía API por el equipo de IA.  
* Adopción de las librerías oficiales HL7 FHIR para envío seguro a LIS externo.

## **10\. Requisitos de UI/UX**

* **Sistema de Cuadrícula:** Interfaz de 24 celdas fijas (22 pares autosómicos \+ Par Sexual XY/XX \+ Basurero/Artefactos).  
* **Interacciones Drag & Drop:** Fluidas (60fps) implementadas en Canvas/React-Beautiful-DnD.  
* **Paleta Clínica:** Alta accesibilidad visual (WCAG AA), contrastes claros para distinguir verde (validado) de naranja (requiere atención).

## **11\. Validación (Vibe Coding / Exploraciones ágiles)**

| Exploración | Pregunta a validar | Prompts (PROMPT\_MAPPING) | Conclusión PRD   |
| :---- | :---- | :---- | :---- |
| Prototipo de Drag & Drop HTML/JS (M3) | ¿El especialista prefiere clics o arrastrar para corregir pares? | PR-VIBE-001 | Confirma PRD-US-03 (Drag & Drop es esencial para adopción y UX). |
| Prueba de Semaforización (M2) | ¿El color naranja alerta suficiente para la intervención clínica? | PR-VIBE-002 | Confirma PRD-US-02 y BR-01 de bloqueo riguroso de firma. |

## **12\. Métricas de Éxito del Producto**

* **North Star:** Time to Karyotype (TTK) promedio consolidado en ≤ 15 minutos por muestra.  
* **KPI de Adopción (Operativo):** \> 85% de las clasificaciones cromosómicas de la IA en "Zona Verde" son aceptadas sin modificación manual.  
* **KPI Clínico (Calidad):** Tasa de sensibilidad en anomalías estructurales \> 99% (Cero falsos negativos críticos avalados por el supervisor).

## **13\. Riesgos del Producto**

| Riesgo | Probabilidad | Impacto | Estrategia de Mitigación   |
| :---- | :---- | :---- | :---- |
| Sesgo de automatización (confianza ciega en ≥85%) | Media | Alto | Implementación de US-04 (Saliency Maps) y auditoría aleatoria cruzada del 5% dictada en el BRD. |
| Problemas de latencia en carga de TIFF pesados | Alta | Medio | Compresión en el borde del cliente antes del POST al backend. |

## **14\. Trazabilidad**

| PRD ID | BRD ID | MRD ID | FSD (Mapeo Técnico)   |
| :---- | :---- | :---- | :---- |
| US-01 | RN-01 | MRD-02 | FSD-UC-001 (Ingesta CHN) |
| US-02 / US-03 | RN-02 | MRD-03 | FSD-UC-002 (Edición Core) |
| US-05 | RN-03 / RN-04 | MRD-05 | FSD-UC-004 (Firma / ISCN) |

## **15\. Anexos**

* **Informe M3 (Prototipado HTML/JS):** Evidencia y flujos de UI validados en mod3informe2.pdf.  
* **Informe M2 (UX/UI):** Análisis de la fatiga visual del citogenetista y wireframes documentados en mod2informefinal.pdf.  
* **Visión Inicial de Negocio:** Resumen 01\_vision\_negocio.txt.

## **16\. Registro de cambios**

| Versión | Fecha | Autor | Cambio   |
| :---- | :---- | :---- | :---- |
| v1.0 | Mayo 2026 | G. Mamani Chambi | Creación del PRD basado estrictamente en la plantilla oficial PRD\_TEMPLATE.md y el contenido de PRD\_1.docx. |

**Journey 2: Supervisor – Auditoría y firma**

journey  
  title Journey Supervisor – auditoría y firma  
  section Recepción  
    Recibir caso en bandeja: 4: Supervisor  
    Ver Audit Trail del analista: 5: Supervisor  
  section Auditoría Aleatoria  
    Sistema marca 5% cromosomas verdes: 5: Sistema  
    Supervisor revisa cromosomas auditados: 4: Supervisor  
    Compara con ideograma de referencia: 4: Supervisor  
  section Firma  
    Autenticación MFA (TOTP/huella): 3: Supervisor  
    Firmar reporte digitalmente: 5: Supervisor  
    Sistema genera ISCN y exporta PDF: 5: Sistema

---

**5\. User stories y criterios de aceptación**

**5.1 Épica E1 – Anonimización y carga de muestras (BR-01)**

| ID | Historia | Prioridad | Valor | Esfuerzo | Criterios Gherkin |
| :---- | :---- | :---- | :---- | :---- | :---- |
| PRD-US-001 | Como Analista, quiero cargar una imagen de metafase para iniciar el análisis de un caso | Must | 8 | 3 | ver §5.1.1 |
| PRD-US-002 | Como Analista, quiero que el sistema anonimice automáticamente la imagen con código CHN para cumplir la Ley de Secreto Médico | Must | 8 | 5 | ver §5.1.2 |

**5.1.1 Criterios PRD-US-001**

gherkin  
DADO un Analista autenticado en el sistema  
CUANDO selecciona una imagen de metafase (formato TIFF, PNG, o JPEG)  
ENTONCES el sistema valida el formato y tamaño (\<50MB)  
Y muestra una vista previa de la imagen  
Y habilita el botón "Procesar"

**5.1.2 Criterios PRD-US-002**

gherkin  
DADO un Analista que ha seleccionado una imagen de metafase  
CUANDO hace clic en "Procesar"  
ENTONCES el sistema genera un código CHN único con formato CHN-YYYY-MM-DD-NNNN  
Y elimina todos los metadatos PII de la imagen antes de subirla al servidor  
Y almacena el mapeo CHN en vault cifrado local (no en la nube)  
Y el tiempo de anonimización es \<2 segundos

**5.2 Épica E2 – Segmentación y clasificación automática (BR-02, BR-03)**

| ID | Historia | Prioridad | Valor | Esfuerzo | Criterios Gherkin |
| :---- | :---- | :---- | :---- | :---- | :---- |
| PRD-US-003 | Como Analista, quiero que el sistema detecte y recorte automáticamente los 46 cromosomas para no hacerlo manualmente | Must | 10 | 8 | ver §5.2.1 |
| PRD-US-004 | Como Analista, quiero ver cada cromosoma con un color (verde/naranja) según su confianza para enfocar mi atención donde más se necesita | Must | 10 | 5 | ver §5.2.2 |

**5.2.1 Criterios PRD-US-003**

gherkin  
DADO una imagen de metafase cargada y anonimizada  
CUANDO el sistema completa el procesamiento  
ENTONCES detecta y segmenta los cromosomas individuales  
Y genera un bounding box por cada cromosoma  
Y la precisión de segmentación (IoU) es \>0.90 vs ground truth  
Y el tiempo de segmentación es \<15 segundos en GPU

**5.2.2 Criterios PRD-US-004**

gherkin  
DADO un cariotipo generado por el sistema  
CUANDO un cromosoma tiene confianza ≥85%  
ENTONCES el sistema lo muestra con borde verde  
Y el Analista puede aceptarlo sin revisión obligatoria  
PERO el sistema puede seleccionarlo para auditoría aleatoria (5%)  
   
DADO un cariotipo generado por el sistema  
CUANDO un cromosoma tiene confianza \<85%  
ENTONCES el sistema lo muestra con borde naranja  
Y bloquea la generación del reporte hasta que el Analista lo revise  
Y registra el bloqueo en el Audit Trail

**5.3 Épica E3 – XAI y corrección manual (BR-06, BR-09)**

| ID | Historia | Prioridad | Valor | Esfuerzo | Criterios Gherkin |
| :---- | :---- | :---- | :---- | :---- | :---- |
| PRD-US-005 | Como Analista, quiero hacer clic en un cromosoma naranja y ver un mapa de calor (XAI) para entender por qué la IA tuvo dudas | Must | 9 | 8 | ver §5.3.1 |
| PRD-US-006 | Como Analista, quiero arrastrar un cromosoma mal clasificado a su par correcto para corregirlo rápidamente | Must | 8 | 5 | ver §5.3.2 |
| PRD-US-007 | Como Analista, quiero dividir cromosomas superpuestos y unir fragmentos para corregir errores de segmentación | Should | 6 | 5 | ver §5.3.3 |

**5.3.1 Criterios PRD-US-005**

gherkin  
DADO un Analista viendo un cromosoma con borde naranja  
CUANDO hace clic en el ícono de explicabilidad (XAI)  
ENTONCES el sistema muestra un mapa de calor superpuesto sobre el cromosoma  
Y el mapa destaca las regiones (bandas) que influyeron en la decisión de la IA  
Y muestra un tooltip con "La IA se basó en la banda \[región\] para esta clasificación"  
Y el Analista no puede resolver el cromosoma naranja sin haber abierto el XAI al menos una vez

**5.3.2 Criterios PRD-US-006**

gherkin  
DADO un Analista en la pantalla de validación  
CUANDO arrastra un cromosoma desde su posición actual hacia un slot del cariograma  
ENTONCES el sistema muestra un preview del destino durante el arrastre (snapping)  
Y al soltar, el cromosoma se reubica en el nuevo slot  
Y el sistema registra la corrección en el Audit Trail (quién, cuándo, desde/hasta qué clase)  
Y si el cromosoma era naranja, se marca como resuelto

**5.3.3 Criterios PRD-US-007**

gherkin  
DADO un Analista en modo de corrección manual  
CUANDO selecciona la herramienta "Dividir" y dibuja una línea sobre un cromosoma superpuesto  
ENTONCES el sistema separa las dos regiones en cromosomas individuales  
Y ejecuta una reclasificación automática de ambos  
Y registra la acción de división en el Audit Trail  
   
DADO un Analista con dos fragmentos seleccionados  
CUANDO hace clic en "Unir fragmentos"  
ENTONCES el sistema combina las máscaras en un solo cromosoma  
Y ejecuta una reclasificación automática del cromosoma unificado

**5.4 Épica E4 – Bloqueo y reglas de negocio (BR-R1, BR-R2, BR-03)**

| ID | Historia | Prioridad | Valor | Esfuerzo | Criterios Gherkin |
| :---- | :---- | :---- | :---- | :---- | :---- |
| PRD-US-008 | Como Analista, quiero que el sistema me impida generar un informe si hay cromosomas naranja sin resolver para evitar errores médicos | Must | 10 | 3 | ver §5.4.1 |
| PRD-US-009 | Como Supervisor, quiero que el sistema seleccione automáticamente el 5% de cromosomas de alta confianza para auditoría para prevenir exceso de confianza | Must | 8 | 4 | ver §5.4.2 |

**5.4.1 Criterios PRD-US-008**

gherkin  
DADO un caso con al menos un cromosoma naranja sin resolver  
CUANDO el Analista intenta hacer clic en "Pasar a Supervisor" o "Generar Reporte"  
ENTONCES el botón está inhabilitado (disabled)  
Y el sistema muestra un mensaje: "Resuelva X cromosomas naranja antes de continuar"  
Y el estado del caso permanece en BLOQUEADO\_POR\_CONFIANZA  
   
DADO un caso donde TODOS los cromosomas naranja han sido resueltos  
CUANDO el Analista hace clic en "Pasar a Supervisor"  
ENTONCES el sistema cambia el estado del caso a VALIDADO\_POR\_ANALISTA  
Y habilita la transición a la bandeja del Supervisor

**5.4.2 Criterios PRD-US-009**

gherkin  
DADO un caso validado por Analista con 46 cromosomas clasificados  
CUANDO el caso llega a la bandeja del Supervisor  
ENTONCES el sistema selecciona aleatoriamente el 5% de los cromosomas con confianza \>86%  
Y marca esos cromosomas con un badge púrpura "Auditoría requerida"  
Y el Supervisor no puede firmar el reporte sin revisar cada uno de esos cromosomas  
Y la selección es reproducible (mismo caso siempre selecciona los mismos cromosomas)

**5.5 Épica E5 – Auditoría y firma con MFA (BR-05, BR-07, BR-R4)**

| ID | Historia | Prioridad | Valor | Esfuerzo | Criterios Gherkin |
| :---- | :---- | :---- | :---- | :---- | :---- |
| PRD-US-010 | Como Supervisor, quiero ver el Audit Trail inmutable de cada caso para auditar el trabajo del Analista | Must | 8 | 5 | ver §5.5.1 |
| PRD-US-011 | Como Supervisor, quiero firmar digitalmente el reporte con autenticación MFA para que la firma sea legalmente vinculante | Must | 9 | 6 | ver §5.5.2 |

**5.5.1 Criterios PRD-US-010**

gherkin  
DADO un Supervisor viendo un caso validado por Analista  
CUANDO accede a la pestaña "Audit Trail"  
ENTONCES el sistema muestra una tabla con:  
  \- Timestamp de cada acción  
  \- Usuario que realizó la acción  
  \- Tipo de acción (CORREGIR\_CLASE, ROTAR, DIVIDIR, UNIR, etc.)  
  \- Valor anterior y nuevo  
  \- Hash SHA256 del registro  
Y cada registro tiene un ícono de verificación que permite validar la integridad de la cadena  
Y el Supervisor puede exportar el Audit Trail a PDF/A para auditoría externa

**5.5.2 Criterios PRD-US-011**

gherkin  
DADO un Supervisor que ha completado la revisión del caso  
CUANDO hace clic en "Firmar Reporte"  
ENTONCES el sistema solicita autenticación MFA (TOTP, huella digital o tarjeta inteligente)  
Y el Supervisor no puede continuar sin completar el MFA  
Y tras validar MFA, el sistema genera el reporte ISCN  
Y registra en el Audit Trail:  
  \- "FIRMAR\_REPORTE"  
  \- Método de autenticación usado  
  \- Timestamp  
  \- Hash de la firma  
Y el reporte queda legalmente vinculado al Supervisor

**5.6 Épica E6 – Reporte ISCN y modo degradado (BR-04, BR-08)**

| ID | Historia | Prioridad | Valor | Esfuerzo | Criterios Gherkin |
| :---- | :---- | :---- | :---- | :---- | :---- |
| PRD-US-012 | Como Supervisor, quiero que el sistema genere automáticamente la nomenclatura ISCN según las clasificaciones finales para no hacerlo manualmente | Must | 8 | 3 | ver §5.6.1 |
| PRD-US-013 | Como Analista, quiero que el sistema siga funcionando en modo manual si la IA no está disponible para no detener el laboratorio | Must | 7 | 5 | ver §5.6.2 |

**5.6.1 Criterios PRD-US-012**

gherkin  
DADO un cariotipo completamente validado y firmado por Supervisor  
CUANDO el sistema genera el reporte  
ENTONCES el motor determinístico (no IA) cuenta cromosomas por clase  
Y aplica reglas ISCN 2024: orden ascendente de anomalías numéricas, sexo al final  
Y genera un string como "46,XX" para cariotipo normal femenino  
Y genera un string como "47,XY,+21" para trisomía 21  
Y el string es 100% válido según gramática ISCN  
Y NUNCA la IA genera este string directamente

**5.6.2 Criterios PRD-US-013**

gherkin  
DADO que el servicio de IA está caído o la red tiene latencia \>10 segundos  
CUANDO el Analista intenta procesar una imagen  
ENTONCES el sistema muestra un banner: "Modo Manual Activado \- IA no disponible"  
Y permite al Analista segmentar y clasificar cromosomas manualmente  
Y las herramientas manuales (dividir, unir, rotar, arrastrar) están disponibles  
Y cuando la IA se restaura, el sistema sincroniza el caso automáticamente  
Y el tiempo en modo degradado se registra para facturación automática (crédito al laboratorio)

---

**6\. Priorización**

**6.1 MoSCoW**

| Prioridad | Historias | Cantidad |
| :---- | :---- | :---- |
| Must | PRD-US-001, 002, 003, 004, 005, 006, 008, 009, 010, 011, 012, 013 | 12 |
| Should | PRD-US-007 | 1 |
| Could | (ninguna en v1.0) | 0 |
| Won't | Integración HL7, DICOM (v1.1/v1.2) | — |

**6.2 RICE (para top 10\)**

| ID | Historia | Reach (casos/mes) | Impact (0.25-3) | Confidence (%) | Effort (días) | RICE |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| PRD-US-003 | Segmentación automática | 500 | 3.0 | 95 | 8 | 178 |
| PRD-US-004 | Semaforización | 500 | 3.0 | 95 | 5 | 285 |
| PRD-US-008 | Bloqueo | 500 | 3.0 | 100 | 3 | 500 |
| PRD-US-005 | XAI | 500 | 2.5 | 90 | 8 | 140 |
| PRD-US-011 | Firma con MFA | 500 | 2.5 | 95 | 6 | 198 |
| PRD-US-010 | Audit Trail | 500 | 2.0 | 95 | 5 | 190 |
| PRD-US-006 | Drag & drop | 500 | 2.0 | 90 | 5 | 180 |
| PRD-US-002 | Anonimización | 500 | 2.0 | 100 | 5 | 200 |
| PRD-US-009 | Auditoría aleatoria 5% | 500 | 1.5 | 85 | 4 | 159 |
| PRD-US-013 | Modo degradado | 500 | 1.5 | 80 | 5 | 120 |

---

**7\. Requerimientos funcionales (alto nivel)**

| ID | Requisito | Historia(s) | Prioridad |
| :---- | :---- | :---- | :---- |
| PRD-REQ-001 | Anonimización local con código CHN | PRD-US-002 | Must |
| PRD-REQ-002 | Segmentación automática de cromosomas | PRD-US-003 | Must |
| PRD-REQ-003 | Clasificación cromosómica con confianza | PRD-US-003, 004 | Must |
| PRD-REQ-004 | Semaforización verde/naranja por umbral 85% | PRD-US-004 | Must |
| PRD-REQ-005 | Bloqueo de reporte si hay naranjas sin resolver | PRD-US-008 | Must |
| PRD-REQ-006 | XAI con mapas de calor (Grad-CAM) | PRD-US-005 | Must |
| PRD-REQ-007 | Corrección manual drag & drop | PRD-US-006 | Must |
| PRD-REQ-008 | Auditoría aleatoria 5% de cromosomas verdes | PRD-US-009 | Must |
| PRD-REQ-009 | Audit Trail inmutable con hash chain | PRD-US-010 | Must |
| PRD-REQ-010 | Firma digital con MFA | PRD-US-011 | Must |
| PRD-REQ-011 | Generación determinística de ISCN | PRD-US-012 | Must |
| PRD-REQ-012 | Modo degradado sin IA | PRD-US-013 | Must |
| PRD-REQ-013 | Herramientas de edición manual avanzada (dividir, unir, rotar) | PRD-US-007 | Should |

---

**8\. Requerimientos no funcionales (alto nivel)**

| ID | Categoría | Requerimiento | Métrica | Umbral |
| :---- | :---- | :---- | :---- | :---- |
| PRD-NFR-001 | Rendimiento | Tiempo de segmentación \+ clasificación por imagen | Mediana | \<15 segundos (GPU) |
| PRD-NFR-002 | Rendimiento | Time to Karyotype (TTK) total por caso | Percentil 95 | \<15 minutos |
| PRD-NFR-003 | Disponibilidad | Uptime en horario laboral (07-19) | SLA | 99.5% |
| PRD-NFR-004 | Seguridad | Audit Trail | Cumplimiento | 21 CFR Part 11 |
| PRD-NFR-005 | Seguridad | Firma de Supervisor | Autenticación | MFA obligatorio |
| PRD-NFR-006 | Privacidad | Datos PII | Almacenamiento | No salen del nodo institucional |
| PRD-NFR-007 | Resiliencia | Tiempo máximo en modo degradado | Continuo | \<2 horas |
| PRD-NFR-008 | Usabilidad | Curva de aprendizaje para Analista | Tiempo | \<1 hora |
| PRD-NFR-009 | Escalabilidad | Throughput por laboratorio | Muestras/mes | ≥500 |

---

**9\. Dependencias e integraciones**

| Sistema | Tipo | Propósito | Riesgo |
| :---- | :---- | :---- | :---- |
| GPU Cluster (Cloud o on-premise) | Infraestructura | Ejecución de modelos U-Net y EfficientNet | Alta (sin GPU, sin IA) |
| Almacenamiento de imágenes (MinIO/S3) | Infraestructura | Persistencia de metafases y resultados | Media |
| Vault de mapeo CHN | Seguridad | Almacenamiento local del mapeo anonimizado | Alta (si se pierde, no hay recuperación) |
| LIS Hospitalario (futuro v1.1) | API externa | Envío de reporte vía HL7 FHIR | Media (dependencia del laboratorio) |
| Servicio de timestamping (futuro) | Externo | Cumplimiento 21 CFR Part 11 | Baja (opcional, costo marginal) |

---

**10\. Supuestos y restricciones**

**Supuestos:**

* Los laboratorios disponen de conexión a internet \>5 Mbps para procesamiento cloud.  
* Los analistas aceptan el flujo de atención dirigida (solo revisar naranjas) después de capacitación.  
* Los supervisores aceptan usar MFA (TOTP/huella) para firmar reportes.  
* El dataset de entrenamiento (10,000+ metafases anotadas) está disponible.

**Restricciones:**

* Presupuesto de desarrollo: 150,000 USD.  
* Cronograma: 6 meses a MVP v1.0.  
* Stack tecnológico: Python/FastAPI backend, React/TypeScript frontend, PostgreSQL, Redis, GPU NVIDIA.  
* Cumplimiento: ISO 15189, 21 CFR Part 11, Ley Boliviana de Secreto Médico.

---

**11\. Experiencia de usuario**

**11.1 Referencias a mockups M2**

| Wireframe M2 | Pantalla / flujo PRD | Estado |
| :---- | :---- | :---- |
| Dashboard de muestras (mod2, pág. 23\) | Flujo: listado de casos con prioridad | validado |
| Pantalla de análisis de metafase (mod2, pág. 24-25) | Flujo: imagen original \+ cromosomas segmentados \+ cariotipo | validado |
| Pantalla de validación experta (mod2, pág. 26\) | Flujo: lista de cromosomas con baja confianza | validado |
| Pantalla de corrección manual (mod2, pág. 27\) | Flujo: herramientas de edición drag & drop | validado |
| Pantalla de generación de reporte (mod2, pág. 28\) | Flujo: ISCN \+ firma \+ exportación | validado |
| Prototipo HTML (mod3) | Implementación completa de flujos | validado con usuarios |

**11.2 Trazabilidad con M2 (Use Cases)**

| Use Case M2 | User Story PRD | Estado de la traza |
| :---- | :---- | :---- |
| UC-M2-01: Carga de imagen | PRD-US-001, 002 | ✅ cubierto |
| UC-M2-02: Segmentación automática | PRD-US-003 | ✅ cubierto |
| UC-M2-03: Semaforización | PRD-US-004 | ✅ cubierto |
| UC-M2-04: Validación de baja confianza | PRD-US-005, 008, 009 | ✅ cubierto |
| UC-M2-05: Corrección manual | PRD-US-006, 007 | ✅ cubierto |
| UC-M2-06: Auditoría y firma | PRD-US-010, 011 | ✅ cubierto |
| UC-M2-07: Generación de reporte | PRD-US-012 | ✅ cubierto |
| UC-M2-08: Modo manual | PRD-US-013 | ✅ cubierto |

**11.3 Lineamientos de diseño**

* Paleta de colores: Azul UMSS \#003770 (primario), Rojo \#E30613 (anomalías), Verde \#1e8868 (validado), Naranja \#d45100 (baja confianza).  
* Tipografía: Inter para alta legibilidad en interfaces densas.  
* Accesibilidad: WCAG 2.2 AA (contraste mínimo 4.5:1, navegación por teclado).  
* Micro-interacciones: Snapping en drag & drop, parpadeo sutil en cromosomas naranja, transiciones de capa en modales.

---

**12\. Métricas de éxito del producto**

* **North Star Metric:** Time to Karyotype (TTK) \< 15 minutos.

| KPI | Descripción | Meta v1.0 | Método de medición |
| :---- | :---- | :---- | :---- |
| TTK mediano | Tiempo desde carga hasta caso firmado | \<15 min | Logs del sistema |
| Tasa de corrección manual | % de cromosomas que el Analista debe reubicar | \<15% | Audit Trail |
| Tasa de adopción de XAI | % de cromosomas naranja donde se consultó XAI antes de resolver | \>90% | Logs de XAI |
| Activación de usuario | Tiempo hasta primera validación exitosa | \<1 hora | Analytics |
| Sensibilidad diagnóstica | Detección de anomalías (prueba piloto) | \>99% | Validación clínica |
| Tasa de bloqueo correcto | % de casos con naranjas sin resolver que no pueden ser firmados | 100% | Pruebas QA |
| NPS (Net Promoter Score) | Satisfacción del Analista y Supervisor | \>60 | Encuesta trimestral |

---

**13\. Riesgos del producto**

| Riesgo | Prob. | Impacto | Mitigación |
| :---- | :---- | :---- | :---- |
| Baja adopción de XAI por analistas | Media | Alto | Capacitación obligatoria, UI prominente, métricas de adopción |
| MFA genera fricción en Supervisores | Media | Medio | Ofrecer múltiples métodos (TOTP, huella, tarjeta), onboarding guiado |
| Latencia de red en laboratorios públicos | Alta | Medio | Compresión local (tiling), procesamiento asíncrono, modo degradado |
| Rechazo a bloqueo de reporte por naranjas | Baja | Medio | Validado en pruebas de usabilidad, justificado por seguridad clínica |
| Deriva del modelo IA con el tiempo | Media | Alto | Reentrenamiento con filtros BR-R3, monitoreo de precisión mensual |
| Costo de cumplimiento 21 CFR Part 11 | Baja | Bajo | Estimado \<$0.03/caso, incluido en modelo de negocio |

---

**14\. Trazabilidad**

| PRD ID | BRD | User Story | FSD (próximo) |
| :---- | :---- | :---- | :---- |
| PRD-REQ-001 | BR-01 | PRD-US-002 | FSD-UC-001 |
| PRD-REQ-002 | BR-02, BR-03 | PRD-US-003, 004 | FSD-UC-002 |
| PRD-REQ-003 | BR-02, BR-03 | PRD-US-003, 004 | FSD-UC-002 |
| PRD-REQ-004 | BR-02 | PRD-US-004 | FSD-UC-003 |
| PRD-REQ-005 | BR-03, BR-R1 | PRD-US-008 | FSD-UC-004 |
| PRD-REQ-006 | BR-06 | PRD-US-005 | FSD-UC-005 |
| PRD-REQ-007 | BR-09 | PRD-US-006 | FSD-UC-006 |
| PRD-REQ-008 | BR-R2 | PRD-US-009 | FSD-UC-007 |
| PRD-REQ-009 | BR-05 | PRD-US-010 | FSD-UC-008 |
| PRD-REQ-010 | BR-07, BR-R4 | PRD-US-011 | FSD-UC-009 |
| PRD-REQ-011 | BR-04 | PRD-US-012 | FSD-UC-010 |
| PRD-REQ-012 | BR-08 | PRD-US-013 | FSD-UC-011 |
| PRD-REQ-013 | BR-09 | PRD-US-007 | FSD-UC-012 |

---

**15\. Anexos**

* Transcripción de entrevistas a citogenetistas (ver mod2informefinal.pdf, sección 2.5 y Parte 3).  
* Análisis competitivo detallado (mod2informefinal.pdf, Parte 2).  
* Wireframes y mockups (mod2informefinal.pdf, págs. 23-28).  
* Prototipo funcional HTML: [https://guillemc92.github.io/karyoumss/](https://guillemc92.github.io/karyoumss/)  
* Mapa de empatía y journey map (mod2informefinal.pdf, págs. 12-15).

---

**16\. Registro de cambios**

| Versión | Fecha | Autor | Cambio |
| :---- | :---- | :---- | :---- |
| v0.1 | Mayo 2026 | G. Mamani | Versión inicial |
| v0.2 | Mayo 2026 | G. Mamani | Adición de constitution, roadmap dual-track, trazabilidad M2 |
| v1.0 | Mayo 2026 | G. Mamani | Versión final aprobada, alineada con BRD v3.5 |

---

**Checklist mínimo**

* ≥ 15 user stories con INVEST y Gherkin (13 Must \+ 1 Should \+ cobertura completa)  
* Priorización MoSCoW \+ RICE para top-10  
* ≥ 2 user journeys en Mermaid (Analista y Supervisor)  
* NFRs alto nivel con umbrales  
* Roadmap de versiones (Delivery track \+ Discovery track)  
* Trazabilidad BRD → PRD → FSD iniciada  
* Revisión documentada por pares  
* Trazabilidad con M2 (UX/UI): use cases y wireframes mapeados  
* Constitution declarada (5 principios no negociables)

