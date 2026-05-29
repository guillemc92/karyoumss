**Rúbrica de Avance Intermedio (30 % de la nota final)** 

**Filosofía:** 

Las plantillas son una **guía, no obligatorias**. La rúbrica evalúa los **elementos conceptuales del módulo** (lo trabajado en clase), no las secciones de plantilla. 

Con IA disponible (Claude, Cursor), el **volumen y la calidad son exigibles**: la asistencia agéntica acelera significativamente ambos, y los umbrales reflejan ese nivel esperado. 

**Regla de entrega:** 

La rúbrica evalúa únicamente lo que existe en el branch: 

release/1.0.0 

en el repositorio del grupo en la fecha de corte. 

Cualquier elemento fuera de ese branch (por ejemplo: `main`, otras ramas, otros tags o sin commit) **no será evaluado**, aunque exista.   
�� La entrega es el branch, no el repositorio completo. 

**Criterios de evaluación** 

**1\. Volumen y profundidad del BRD (5 %)** 

● **Excelente:** 10 o más elementos de negocio bien desarrollados (objetivos SMART, stakeholders, business case con ROI/NPV, alcance, KPIs, restricciones, supuestos, riesgos, gobernanza, criterios de éxito) 

● **Aceptable:** 7–9 elementos con calidad o más de 10 con calidad baja ● **Bajo:** 6 o menos elementos o contenido genérico 

**2\. Volumen y profundidad del MRD (5 %)** 

● **Excelente:** 7 o más elementos (segmentos, personas, JTBD, voz del cliente, competencia, posicionamiento, hipótesis) y al menos 2 segmentos bien definidos ● **Aceptable:** 5–6 elementos con perfil básico 

● **Bajo:** menos de 5 o segmentos genéricos  
**3\. Volumen y profundidad del PRD (10 %)** 

● **Excelente:** 20 o más *user stories* tipo INVEST con criterios de aceptación \+ al menos 2 *user journeys* \+ roadmap 

● **Aceptable:** 15–19 *user stories* con criterios \+ 1 *journey* 

● **Bajo:** menos de 15 *user stories* o sin criterios claros 

**4\. Volumen y profundidad del FSD (15 %)** 

● **Excelente:** 30 o más elementos totales (casos de uso, reglas de negocio, Gherkin, modelo de datos, contratos API, glosario, anexos) 

● **Aceptable:** 20–29 elementos 

● **Bajo:** menos de 20 

**5\. Calidad de casos de uso y Gherkin (10 %)** 

● **Excelente:** 10 o más casos de uso críticos con flujo principal, alternos y Gherkin verificables 

● **Aceptable:** 5 o más completos 

● **Bajo:** menos de 5 verificables 

**6\. NFRs ISO 25010 cuantificables (10 %)** 

● **Excelente:** 8 o más NFRs con métrica, umbral y verificación cubriendo al menos 5 características 

● **Aceptable:** 6–7 cubriendo al menos 4 características 

● **Bajo:** menos de 6 o baja cobertura 

**7\. Prompt**‑**contracts (10 %)** 

● **Excelente:** 10 o más contratos con los 6 elementos \+ invariants \+ failure modes ● **Aceptable:** 5–9 completos 

● **Bajo:** menos de 5 

**8\. Diagramas Mermaid coherentes con FSD (10 %)**  
● **Excelente:** 10 o más diagramas `.mmd` cubriendo secuencia, estado, ER y Gantt, con cada caso de uso crítico mapeado   
● **Aceptable:** 6–9 diagramas cubriendo todos los tipos 

● **Bajo:** menos de 6 o falta un tipo 

**9\. AGENTS.md v1.0 \+ Skills \+ Cursor Rules (15 %)** 

● **Excelente:** 

○ AGENTS.md completo 

○ 5 o más skills accionables 

○ 3 o más cursor rules específicas del dominio 

● **Aceptable:** 

○ AGENTS.md completo 

○ 2–4 skills 

○ 1–2 rules 

● **Bajo:** 

○ AGENTS.md incompleto 

○ menos de 2 skills o sin rules 

**10\. Trazabilidad \+ Métricas AI**‑**SDLC (10 %)** 

● **Excelente:** 

○ trazabilidad completa MRD → PRD → FSD 

○ métricas AI‑SDLC: *prompt coverage*, *spec fidelity* y al menos una adicional ● **Aceptable:** 

○ trazabilidad mayor o igual a 80 % 

○ incluye métricas mínimas 

● **Bajo:** 

○ trazabilidad menor al 80 % 

○ menos de 2 métricas 

**Evaluación** 

Cada criterio se califica en una escala de **1 a 5** y luego se pondera. 

El docente actúa como revisor principal.  
**Ajuste por aporte individual** 

Las notas son **grupales**, pero se ajustan según el aporte individual. Cada equipo debe incluir: 

docs/aportes/release-1.0.0.md 

**Fórmula de ajuste** 

Plain Text 

aporte\_promedio\_grupo \= total\_tareas\_grupo / n\_integrantes factor\_i \= clamp(tareas\_i / aporte\_promedio\_grupo, 0.5, 1.1) nota\_individual\_i \= nota\_grupal × factor\_i 

Show more lines 

**Reglas** 

● **Piso 0.5:** mínimo 50 % de la nota grupal 

● **Techo 1.1:** máximo \+10 % sobre la nota grupal ● Si no hay entrega → todos 0 

● Si un integrante no aparece → factor \= 0.5 

● Casos especiales → decisión del docente 

**Ejemplo** 

Grupo de 4 integrantes 

● Total tareas: 20 

● Promedio: 5 tareas por persona 

● Nota grupal: 80 

Resultados: 

● Ana: 10 tareas → factor 1.10 → 88 

● Beto: 6 tareas → factor 1.10 → 88 

● Carla: 3 tareas → factor 0.60 → 48 

● Dani: 1 tarea → factor 0.50 → 40