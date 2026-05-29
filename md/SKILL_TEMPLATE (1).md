---

name: \<kebab-case-único\> description: \> Una frase muy específica que diga CUÁNDO usar este Skill en implementación. Mencionar artefacto del FSD que es la entrada (ej. "FSD-UC-XXX", "§6.2 diccionario", "AC Gherkin"), el stack y el tipo de salida (código, migración, test). Evitar verbos como "ayudar"; usar "implementar", "generar", "validar". allowed-tools:

- read  
- edit  
- run-tests model-tier: sonnet      \# opcional: haiku | sonnet | opus fsd-version-min: v0.1   \# versiones del FSD que este Skill puede consumir status: stable          \# draft | stable | deprecated owner: 

---

# Skill (plantilla): \<Título legible\>

**Convención del módulo**: Skills viven en `plantillas/skills/<slug>/SKILL.md`. Para activarlas en Claude Code o Claude Desktop, copiar la carpeta del Skill a:

- `~/.claude/skills/<slug>/` (alcance: tu usuario, todos los proyectos), o  
- `.claude/skills/<slug>/` en la raíz del repositorio del grupo (alcance: solo ese repo).

Para Cursor existe un mecanismo paralelo: `.cursor/rules/*.mdc`. Estos Skills **no** se activan automáticamente en Cursor; si quieren equivalente, deben portarlos a una regla de Cursor.

## 1\. Cuándo activarlo (triggers)

- DURANTE: implementación, refactor, tests, revisión de PR, migraciones.  
- ARRANCA cuando: \<condición textual de entrada — ej. "el usuario adjunta o cita un FSD-UC-NNN"\>.  
- NO ACTIVAR cuando: el usuario está aún definiendo negocio (BRD/MRD/PRD/FSD); este Skill es de implementación, no de descubrimiento.

## 2\. Entradas obligatorias (Inputs)

El usuario MUST proporcionar al menos una de:

- ID del UC: `FSD-UC-NNN`.  
- Ruta al FSD: `docs/fsd/<archivo>.md` (todo o sección específica con anchor).  
- Pegado del fragmento (UC, BR, fila del diccionario, Gherkin) cuando el repo no esté accesible.

Si falta cualquiera, el Skill responde con: "Necesito antes de implementar; aquí está la lista mínima de datos."

## 3\. Fuentes de verdad (orden de precedencia)

1. Fragmento citado del FSD (UC / BR / diccionario / Gherkin / NFR).  
2. §11 del FSD (matriz de trazabilidad MRD → PRD → FSD → NFR → TC).  
3. `AGENTS.md` y ADRs vigentes (stack, capas, restricciones).  
4. Código existente en el repo (estilo, nombres, convenciones).

## 4\. Procedimiento

1. Verificar que la entrada existe y está completa.  
2. Resumir en 3–5 líneas qué del FSD va a implementarse (ningún supuesto extra).  
3. Mapear el fragmento a la arquitectura del repo (paquetes, capas, archivos).  
4. Implementar el cambio mínimo viable (no feature creep).  
5. Añadir tests por cada **criterio de aceptación**, **regla BR** o **NFR** que toque.  
6. Anotar trazabilidad en código y en el resumen del PR.

## 5\. Salida esperada

- Diff o archivos completos.  
- Tabla de trazabilidad obligatoria al final del PR:

| FSD ID | Archivo de implementación | Test que lo verifica |
| :---- | :---- | :---- |
| FSD-UC-001 AC2 | `src/.../service/InscribirEstudiante` | `InscribirEstudianteIT#ac2()` |
| BR-007 | `src/.../domain/Saldo.java:42` | `SaldoTest#bloqueaSiVencido` |
| NFR-001 | `infra/k6/inscripcion.js` | reporte k6 p95 \< 100 ms |

## 6\. Verificación (criterios de "bien hecho")

- Toda lógica importante referencia un ID del FSD (UC / BR / NFR) en comentario o nombre de test.  
- Cero reglas inventadas: si algo no estaba en el FSD, hay un `TODO(spec)` y un comentario claro.  
- Build y linter verdes; tests pasan localmente.  
- No hay PII en logs ni secretos en código (revisar `AGENTS.md` §7).

## 7\. Anti-patrones específicos

- Mezclar lógica de negocio con la capa de presentación o controller.  
- Persistir sin transacción cuando hay escritura múltiple.  
- Renombrar entidades / atributos del diccionario "para que se vean mejor" — rompe trazabilidad.

## 8\. Mini ejemplo de invocación

"Implementa FSD-UC-002 (matrícula con prerequisitos) en `src/main/java/.../inscripcion/`. Usa este Skill."

## 9\. Modos de fallo conocidos

- El FSD cita un BR-NNN inexistente → STOP, pedir aclaración.  
- El AC Gherkin contradice el NFR → STOP, escalar al docente o al PR de spec.

## 10\. Registro de cambios del Skill

| Versión | Fecha | Autor | Cambio |
| :---- | :---- | :---- | :---- |
| 0.1.0 | dd/mm/aaaa |  | versión inicial |

