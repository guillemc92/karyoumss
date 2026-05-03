# **Business Requirements Document (BRD)**

## **BIOMED UMSS — Intelligent Karyotyping Platform**

| Campo | Detalle   |
| :---- | :---- |
| **Proyecto** | BIOMED UMSS – Intelligent Karyotyping |
| **Versión** | 1.1 (Revisión Ejecutiva) |
| **Fecha** | Mayo 2026 |
| **Autor** | Ing. Guillermo Mamani Chambi |
| **Institución** | Universidad Mayor de San Simón (UMSS) |
| **Clasificación** | Confidencial – Uso interno / Estratégico |

## **1\. Resumen Ejecutivo**

**BIOMED UMSS** es una plataforma web SaaS de Inteligencia Aumentada diseñada para modernizar y escalar el análisis citogenético (cariotipado). El sistema transforma un proceso manual y propenso a errores, que actualmente consume entre 30 y 45 minutos por paciente, en un flujo asistido que lo reduce a menos de 15 minutos.  
Mediante un modelo **Human-in-the-Loop**, BIOMED delega la carga mecánica de la segmentación a la IA, reservando la decisión diagnóstica final al criterio médico. Esto democratiza el acceso a tecnología clínica de alta precisión, reemplazando sistemas *legacy* costosos por una solución 100% web que facilita el diagnóstico remoto y la interconsulta en tiempo real.

## **2\. Problema y Oportunidad de Negocio**

### **2.1. El Problema (Pain Points)**

* **Ineficiencia Operativa:** El flujo actual requiere segmentar imágenes de metafases, emparejar cromosomas homólogos y analizar bandas G de forma manual (pixel por pixel).  
* **Riesgo Clínico por Fatiga:** La alta carga cognitiva y visual genera cansancio en los especialistas, aumentando el riesgo de falsos negativos en diagnósticos críticos (ej. anomalías oncológicas o prenatales).  
* **Barrera de Acceso:** El software tradicional de cariotipado es tipo *on-premise*, requiere hardware especializado (dongles) y licencias prohibitivas (aprox. USD 20,000) para laboratorios emergentes.

### **2.2. La Oportunidad**

Desarrollar un sistema SaaS que asuma el 80% del trabajo mecánico (clasificación base) y dirija la atención del médico mediante "semaforización de confianza" (resaltando solo el 20% dudoso). Esto permite a los laboratorios triplicar su capacidad de procesamiento diario sin incrementar su planilla de personal.

## **3\. Usuarios Objetivo y Tareas Core**

| Perfil de Usuario | Objetivo Principal | Tareas Críticas en el Sistema   |
| :---- | :---- | :---- |
| **Analista Citogenetista** | Clasificar y detectar anomalías genéticas de forma rápida y sin fatiga. | 1\. Ingresar muestra y capturas. 2\. Corregir y validar la propuesta de la IA (Drag & Drop). 3\. Solicitar aprobación. |
| **Garante Clínico (Supervisor)** | Auditar diagnósticos y asegurar el cumplimiento legal (ISCN). | 1\. Revisar conflictos no resueltos o de baja confianza. 2\. Autorizar o rechazar informes. 3\. Firmar digitalmente. |
| **Director de Laboratorio** | Maximizar la rentabilidad y el volumen de procesamiento del laboratorio. | 1\. Monitorear el tiempo promedio por caso (TTK). 2\. Administrar usuarios y roles. |

## **4\. Propuesta de Valor**

* **Para el Especialista:** Interfaz fluida, eliminación del estrés visual y agencia diagnóstica total. La IA sugiere, el humano decide.  
* **Para el Laboratorio:** Reducción del 70% en el tiempo de análisis (TTK), estandarización automática bajo normas ISCN y cero costos de mantenimiento de servidores locales.  
* **Para el Paciente:** Tiempos de espera drásticamente menores para resultados sensibles (ej. amniocentesis).

## **5\. Resumen del Business Model Canvas**

| Dimensión | Elementos Clave   |
| :---- | :---- |
| **Segmentos de Clientes** | Laboratorios de genética privados, Hospitales Públicos (3er nivel), Centros Oncológicos. |
| **Propuesta de Valor** | Reducción de TTK de 45 a 15 min, modelo SaaS accesible, alta fidelidad clínica. |
| **Canales** | Venta directa institucional (B2B), convenios universitarios, congresos médicos. |
| **Relación con Clientes** | Soporte técnico especializado SLA 99.9%, capacitaciones continuas, comunidad clínica. |
| **Fuentes de Ingresos** | SaaS (Suscripción mensual/anual), Licenciamiento por volumen de muestras (Pay-per-use). |
| **Recursos Clave** | Algoritmos de visión por computadora, Dataset anonimizado, Infraestructura Cloud. |
| **Actividades Clave** | Mantenimiento del modelo IA, despliegue web, auditorías de seguridad de datos. |
| **Socios Clave** | UMSS (Respaldo académico), Ministerio de Salud, Proveedores de microscopía. |
| **Estructura de Costos** | Servidores GPU para inferencia IA, salarios de desarrollo/medicina, hosting y ciberseguridad. |

## **6\. Requisitos Clave del Sistema**

### **6.1. Requisitos Funcionales**

1. **Ingesta de Datos:** Carga de imágenes TIFF/PNG y asignación de código CHN anonimizado.  
2. **Motor predictivo:** Clasificación automática de los 46 cromosomas e identificación de anomalías numéricas.  
3. **Editor Interactivo:** Herramientas de separación, unión, rotación e inversión de cromosomas mediante *Drag & Drop*.  
4. **Prevención de Errores:** Bloqueo de la generación de informe si existen cromosomas marcados con "Baja Confianza" sin revisión manual.  
5. **Generación ISCN:** Traducción automática del orden visual a nomenclatura clínica internacional estándar.

### **6.2. Requisitos No Funcionales (NFRs)**

* **Seguridad y Privacidad:** Cumplimiento de normativas de salud mediante disociación de datos (Privacy by Design). Ninguna imagen se guarda con el nombre del paciente.  
* **Rendimiento:** La inferencia inicial de la IA sobre una metafase no debe superar los 15 segundos en conexiones estándar.  
* **Disponibilidad:** Arquitectura Cloud con un SLA de tiempo de actividad del 99.9% para entornos clínicos críticos.

## **7\. Métricas Clave de Éxito (KPIs)**

* **Productividad:** Reducción del *Time to Karyotype* (TTK) a menos de 15 minutos.  
* **Adopción / Eficiencia de IA:** Tasa de aceptación directa \> 85% (el usuario no modifica la sugerencia inicial de la IA en más del 15% de los cromosomas).  
* **Calidad Clínica:** Tasa de error diagnóstico \= 0% (asegurado por la validación del supervisor).

## **8\. Supuestos, Restricciones y Dependencias**

* **Supuestos:** Los laboratorios cliente cuentan con microscopios digitales con cámaras capaces de exportar imágenes de alta resolución.  
* **Restricciones:** El sistema no emite un diagnóstico final autónomo; legalmente actúa solo como herramienta de soporte a la decisión médica.  
* **Dependencias:** Disponibilidad y actualización de las directrices internacionales del comité ISCN.

## **9\. Alcance del Proyecto (Scope v1.0)**

**En Scope:**

* Motor de IA para segmentación y clasificación.  
* Interfaz de edición interactiva (drag & drop).  
* Semáforo de confianza predictiva.  
* Flujo de validación en dos niveles (analista \+ supervisor).  
* Generador de reportes PDF.

**Fuera de Scope (Para iteraciones futuras):**

* Integración directa por hardware con la cámara del microscopio.  
* Secuenciación Genómica de Nueva Generación (NGS).  
* Aplicación nativa móvil (se mantiene exclusivamente web responsive).
