# Modelo de amenazas — BIOMED UMSS, capa de IA

> Plantilla de `docs/MODELO_DE_AMENAZAS.md` del AI Security Lab, aplicada al
> producto real. Lo que cambia respecto al ejemplo de la clase no es la forma:
> es que aquí el «secreto de juguete» es **el dato clínico de un paciente**, y
> las reglas que se pueden violar están firmadas en ADRs.

| Elemento | Pregunta | En BIOMED |
|---|---|---|
| **Activos** | ¿Qué queremos proteger? | **PII de paciente** (nombre, documento, fecha de nacimiento — cifrados en `PatientVault`, RN-03); **el resultado clínico** (`iscn_nomenclature`, de solo lectura tras generarse, RN-04); **la bitácora** (`AuditEvent`, *append-only* con cadena SHA-256, RN-05); **la segregación de funciones** (un analista no ve casos ajenos y no firma como supervisor, RN-06); disponibilidad del pipeline y coste de tokens del modelo local |
| **Actores** | ¿Quién podría atacar? | Un **analista legítimo curioso** (tiene sesión válida y quiere ver casos de otro); un **paciente o tercero** cuyo texto llega al sistema; quien pueda **dejar un documento en el corpus** del RAG; un **supervisor** que quiera saltarse el doble control; un atacante externo con una sesión robada |
| **Puntos de entrada** | ¿Por dónde entra información? | El campo de **consulta en lenguaje natural** (`/api/clinic/tools/query/`); los **documentos del corpus** que el RAG mete en el contexto (`corpus.py`); los **resultados de las herramientas**, que vuelven al modelo; el **CHN y el `patient_ref`** que el analista teclea al registrar; la conexión **MCP** (`mcp_conexion.py`) |
| **Fronteras de confianza** | ¿Dónde cambia el nivel de confianza? | Usuario → aplicación: **no confiable**. Aplicación → prompt del sistema: confiable. **Corpus → contexto: NO confiable aunque sea interno** (`rag_qa.py:208` concatena la pregunta y los documentos en el mismo prompt). Modelo → herramientas: **el modelo NO es confiable para decidir acciones**. Y una que el laboratorio no tiene: **sesión → herramienta**, porque aquí la autorización es por analista y por rol, no global |
| **Ataques** | ¿Qué podría intentar? | **Consultar casos de otro analista por el chat** (lo que el visor niega con 403); extraer PII pidiéndola en otro formato; **envenenar el corpus** para que el RAG afirme una política clínica falsa; hacer que el agente **valide un caso** saltándose RN-01; inyección directa para que el modelo ignore el catálogo y conteste de su memoria; **consumo sin límite** contra el modelo local, que tarda 20-200 s por consulta |
| **Impacto** | ¿Qué pasa si lo consigue? | **Violación de RN-03 y RN-06 con dato clínico real**: el ISCN de un paciente ajeno es un diagnóstico. Un informe emitido sin validación manual (RN-01) es un resultado clínico sin responsable identificado. Una política falsa en el corpus se propaga a todas las respuestas. El consumo sin límite deja el pipeline inservible para el resto del laboratorio |
| **Mitigaciones** | ¿Qué control reduce el riesgo? | **Autorización por sesión en la capa de herramientas** (lo que falta hoy y es el hallazgo AI-SEC-001); separación datos/instrucciones marcando el corpus como datos; procedencia del corpus por hash; el modelo **propone y la aplicación decide** (ya implementado en `agente_escritura.py`: el guardrail se evalúa antes de mirar los datos); validación de salida que redacte PII; límite de consumo por sesión; y **tests de regresión** que fallen si alguno de esos controles se quita |

## Diagrama de flujo, con dónde está el riesgo

```
Analista ──► API clínica ──► Prompt / Contexto ──► llama3.2:3b ──► Herramientas ──► PostgreSQL
   (1)          (2)                (3)                 (4)              (5)            (6)
```

1. **Entrada no confiable.** El texto libre del analista. También el coste: cada consulta que llega al modelo ocupa la única instancia local, 20-200 s.
2. **Aquí se decide la identidad**, y hoy la decisión se queda a medias: `permissions.py` autentica al analista, pero esa identidad **no viaja hasta la herramienta**.
3. **Instrucciones confiables y datos no confiables conviven.** `rag_qa.py:208` mete `PREGUNTA: {pregunta}` y los documentos del corpus en el mismo prompt.
4. **Salida probabilística.** El enrutador ya no se fía del modelo para los datos —`camino` declara si respondió el catálogo o el LLM—, pero sí para elegir herramienta.
5. **El modelo PROPONE, la aplicación DECIDE.** Implementado para la escritura (RN-01), **no** para la lectura: cualquier herramienta de consulta se ejecuta sin comprobar de quién es el caso.
6. **Mínimo privilegio.** Hoy las consultas hacen `Sample.objects.filter(status=…)` sobre toda la tabla.

## Lo que este modelo NO cubre

- **La cadena de la bitácora (RN-05).** El hash SHA-256 encadenado se probó en los tests de servicio de ADR-0022; aquí no se ataca.
- **La firma MFA del supervisor (RN-06/UC-006).** Atacarla exigiría el secreto TOTP, y un test que conozca el secreto convierte el segundo factor en el primero — el mismo motivo por el que quedó fuera del E2E (§7 del entregable M8).
- **El modelo en sí.** No se busca un jailbreak universal de llama3.2:3b. Se busca que, **cuando el modelo obedezca al atacante, la aplicación no le deje hacer daño**.
