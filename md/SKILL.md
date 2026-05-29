---

name: fsd-gherkin-a-tests-aceptacion description: \> Convierte los criterios de aceptación Gherkin del FSD (§4 por UC) en tests automatizados ejecutables (Cucumber-JVM o JUnit con tablas), con fixtures realistas del dominio universitario y, cuando el AC referencia un NFR (§10), prueba de carga k6 asociada. Requiere referencia al UC; no inventa AC. allowed-tools:

- read  
- edit  
- run-tests model-tier: sonnet fsd-version-min: v0.1 status: stable owner: Módulo 4 – UMSS

---

# Skill: AC Gherkin del FSD → tests de aceptación automatizados

Skill canónica del módulo. Para activarla en Claude Code o Claude Desktop, copia esta carpeta a `~/.claude/skills/fsd-gherkin-a-tests-aceptacion/` o a `.claude/skills/fsd-gherkin-a-tests-aceptacion/` en la raíz del repo del grupo.

## 1\. Cuándo activarlo (triggers)

- DURANTE: cierre de un UC ya implementado o validación previa al merge.  
- ARRANCA cuando: el UC del FSD ya tiene bloque ```` ```gherkin … ``` ```` y el código existe (o se está generando a la par con `fsd-uc-a-vertical-slice`).  
- NO ACTIVAR cuando: aún no hay bloque Gherkin en el FSD (eso es trabajo del FSD, no de este Skill).

## 2\. Entradas obligatorias

- `FSD-UC-NNN` con bloque Gherkin (Dado / Cuando / Entonces) en su sección de criterios de aceptación.  
- §11 del FSD si el AC referencia un `NFR-NNN` (umbral medible obligatorio).  
- Datos de prueba aceptables (fixtures) si el dominio requiere identidades reales: carnet UMSS, código de materia, periodo académico, monto en BOB.

## 3\. Fuentes de verdad (orden de precedencia)

1. Bloque Gherkin del UC en §4 del FSD.  
2. §10 del FSD (NFR con métrica y umbral) cuando el AC los referencia.  
3. §8 del FSD (integraciones externas con SLA, protocolo, autenticación).  
4. `AGENTS.md` (stack de testing autoritativo: JUnit 5, Testcontainers, k6, Wiremock).

## 4\. Procedimiento

1. Decidir el nivel de prueba según la naturaleza del AC:  
   - AC sobre regla de dominio pura → JUnit 5 unit con `@ParameterizedTest` y tabla CSV.  
   - AC sobre flujo del UC end-to-end → Cucumber-JVM con `Given / When / Then` (mismo lenguaje que el FSD para que se lea idéntico).  
   - AC sobre integración con BD → integration test con Testcontainers PostgreSQL.  
   - AC sobre integración con servicio externo (§8) → Wiremock con stubs en `src/test/resources/mappings/`.  
   - AC con umbral de NFR → script k6 enlazado en `infra/perf/`.  
2. Generar fixtures realistas del dominio universitario UMSS:  
   - Materias: `CIV-101 Cálculo I`, `INF-203 Bases de Datos`, etc.  
   - Periodos: `2026-2`, `2027-1`.  
   - Carnets / RUDE con formato real (no `12345` ficticios).  
   - Calendarios con zona horaria `America/La_Paz`.  
   - Montos en BOB con dos decimales (`numeric(10,2)`).  
3. Para integraciones externas (§8 FSD) usar Wiremock y respetar el contrato declarado:  
   - Status code y schema esperados.  
   - Latencia simulada cuando hay NFR de tiempo.  
   - Failure modes: pasarela no responde, response 5xx, timeout.  
4. Anotar trazabilidad: cada test lleva `@Tag("FSD-UC-NNN")` y `@Tag("AC-<n>")` (JUnit) o etiquetas equivalentes en feature files de Cucumber.  
5. Reporte de cobertura por AC: al ejecutar la suite, generar `target/fsd-coverage.md` con la tabla `AC → test → resultado`.

## 5\. Salida esperada

- Archivos `*.feature` (Cucumber) o `*Test.java` con métodos parametrizados.  
- Stubs Wiremock en `src/test/resources/mappings/`.  
- Si hay NFR: `infra/perf/<uc>.js` (k6) con umbrales codificados como `thresholds` k6.  
- Tabla de trazabilidad obligatoria al cerrar el PR:

| AC del FSD | NFR vinculado | Archivo de test | Tipo |
| :---- | :---- | :---- | :---- |
| FSD-UC-002 AC1 | — | `inscripcion.feature` escenario `estudiante al día` | Cucumber |
| FSD-UC-002 AC2 | — | `SaldoTest#bloqueaSiVencido` | JUnit unit |
| FSD-UC-002 AC3 | NFR-001 | `infra/perf/inscripcion.js` | k6 (p95\<100 ms) |

## 6\. Verificación

- 100 % de los AC del UC tienen al menos un test verde con su tag `AC-<n>`.  
- Cualquier AC con umbral medible (NFR-001..NFR-006) tiene prueba que **falla** si el umbral se viola.  
- Los `Given` del Gherkin reflejan precondiciones del UC, no datos artificiosos.  
- Cero AC sin test, cero tests sin AC asociado.  
- `mvn verify` pasa localmente y produce `target/fsd-coverage.md`.

## 7\. Anti-patrones del dominio universitario

- AC con "el sistema responde rápido" sin umbral → STOP, pedir que se complete §10 NFR antes de testear.  
- Mockear el dominio entero para que el test pase: si pasa pero la regla está mal, no sirve.  
- Ignorar el camino de excepción de pago QR: el AC del fallo de pasarela debe tener test propio con stub Wiremock que devuelva 5xx.  
- Fixtures genéricas tipo `usuario1@test.com`: usar identidades realistas para que el grupo detecte sesgos en validaciones (longitud, regex, dominio institucional).  
- Ejecutar k6 contra producción: siempre contra entorno de staging o local con Testcontainers.

## 8\. Mini ejemplo de invocación

"Convierte los AC del `FSD-UC-003` 'Pago de matrícula con QR Banco Unión' (`docs/fsd/pago_matricula.md`) en tests Cucumber-JVM y un k6 para `NFR-001` (p95 \< 100 ms). Usa el Skill `fsd-gherkin-a-tests-aceptacion`."

## 9\. Modos de fallo conocidos

- El AC referencia un `NFR-NNN` que no existe en §10 → STOP, escalar al autor del FSD.  
- El AC contradice una regla `BR-NNN` (p. ej. AC dice "permite inscribir sin saldo" pero `BR-007` dice "MUST validar saldo") → STOP, abrir issue de spec.  
- Falta de `Given` claro: el Gherkin usa `Dado el sistema funcionando` sin precondición concreta → STOP, pedir precondición observable.

## 10\. Registro de cambios

| Versión | Fecha | Autor | Cambio |
| :---- | :---- | :---- | :---- |
| 0.1.0 | 04/05/2026 | M.Sc. Edson Terceros | versión inicial |

