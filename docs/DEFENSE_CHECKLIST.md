# Defensa Final — Checklist de Preparación

## 1. Entrega `release/2.0.0`
- [ ] Todo el contenido crítico está en el branch `release/2.0.0`.
- [ ] `docs/DTI.md` está completo y actualizado.
- [ ] `docs/fsd/FSD_vFinal.md` está completo y actualizado.
- [ ] `docs/prd/PRD_vFinal.md` está completo y actualizado.
- [ ] `docs/mrd/MRD_vFinal.md` está completo y actualizado.
- [ ] `docs/brd/BRD_vFinal.md` está completo y actualizado.
- [ ] `AGENTS.md` está sincronizado con la entrega y el branch.
- [ ] `docs/PROMPT_MAPPINGS.md` existe y refleja trazabilidad a FSD.
- [ ] `docs/roadmap.md` está presente y con hitos claros.
- [ ] `docs/aportes/release-2.0.0.md` documenta contribuciones reales.
- [ ] `docs/diagrams/` tiene ≥ 8 archivos `.mmd` versionados.
- [ ] `pocs/` tiene al menos 2 POCs documentados y ejecutables.

## 2. Estructura de la presentación
- [ ] Abrir con el problema y la propuesta de valor (MRD/PRD).
- [ ] Mostrar 1 caso de uso destacado del FSD con su aviso-contrato.
- [ ] Explicar la arquitectura con C4 Nivel 1 + 2 y el núcleo hexagonal.
- [ ] Describir la capa distribuida / event-driven / IA como evolución.
- [ ] Señalar los ADRs clave y trade-offs, especialmente `0001`–`0004`.
- [ ] Cerrar con la hoja de ruta y compromisos.

## 3. Demo recomendada
- [ ] Si hay código ejecutable, preparar una demo de 5 minutos.
- [ ] La demo debe mostrar código + aplicación funcionando.
- [ ] Preferible: un endpoint backend o un flujo UI que respalde un UC del FSD.
- [ ] Debe conectarse directamente con lo documentado en DTI/FSD.
- [ ] Si no hay demo, explicar claramente por qué y qué se entregó.

## 4. Q&A y evaluación
- [ ] Preparar respuestas rápidas sobre trazabilidad MRD→PRD→FSD→DTI.
- [ ] Tener justificadas las decisiones de arquitectura y trade-offs.
- [ ] Conocer los criterios de la rúbrica de defensa.
- [ ] Saber qué queda en `release/2.0.0` y qué está fuera del scope.

## 5. Puntos críticos de la rúbrica
- Coherencia documental: MRD, PRD, FSD, DTI y mapeo a código.
- Calidad arquitectónica: C4, hexagonal, IA, event-driven, AWS/infra.
- AGENTS.md: sincronizado y consistente con DTI y el ciclo de entrega.
- POCs: definidos, medibles y con aprendizaje documentado.
- Diagramas: legibles, versionados y referenciados en la presentación.

## 6. Nota de última hora
- Si la defensa es en S11/S12, resaltar que `release/2.0.0` es la rama de entrega evaluada.
- Llevar ejemplos concretos de RN-09 / BR-R5 y cómo afectan al flujo de emisión.
- Mantener la presentación dentro de 15–25 minutos según el tamaño del grupo.
