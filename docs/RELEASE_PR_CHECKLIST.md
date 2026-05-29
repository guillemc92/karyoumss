# Checklist de Commit y PR — `release/2.0.0`

## 1. Confirmar branch y cambios
- [ ] Verificar que el branch activo local es `release/2.0.0`.
- [ ] Confirmar que todos los archivos actualizados están en el directorio del proyecto.
- [ ] Ejecutar `git status --short` para revisar cambios pendientes.
- [ ] Revisar `git diff` y asegurar que solo contiene los archivos esperados.

## 2. Archivos clave que deben incluirse
- [ ] `docs/aportes/release-2.0.0.md`
- [ ] `docs/DEFENSE_CHECKLIST.md`
- [ ] `AGENTS.md`
- [ ] `docs/fsd/FSD_vFinal.md`
- [ ] `docs/DTI.md`
- [ ] `docs/prd/PRD_vFinal.md`
- [ ] `docs/mrd/MRD_vFinal.md`
- [ ] `docs/brd/BRD_vFinal.md`
- [ ] `docs/PROMPT_MAPPINGS.md`
- [ ] `docs/roadmap.md`
- [ ] `docs/diagrams/` actualizados y versionados
- [ ] `docs/adr/0004-Estrategia-Evolucion-Arquitectonica.md`

## 3. Mensaje de commit recomendado
```
feat(release): preparar entrega final release/2.0.0

- Actualiza trazabilidad RN-09 / BR-R5 en BRD, FSD, PRD, MRD y DTI
- Completa aportes individuales y checklist de defensa
- Corrige ADR-0004 y sincroniza AGENTS.md con release/2.0.0
```

## 4. Crear PR en GitHub
- [ ] Subir branch local con `git add .` y `git commit -m "feat(release): preparar entrega final release/2.0.0"`.
- [ ] Empujar a remoto con `git push origin release/2.0.0`.
- [ ] Abrir PR en GitHub desde `release/2.0.0` hacia el branch de evaluación.

## 5. Descripción del PR
- Resumir los cambios clave:
  - Trazabilidad y reglas clínicas RN-09 / BR-R5.
  - Correcciones ADR y documentación final.
  - Artefactos de defensa y aporte individual.
- Referenciar los documentos principales:
  - `docs/aportes/release-2.0.0.md`
  - `docs/DEFENSE_CHECKLIST.md`
  - `AGENTS.md`
  - `docs/DTI.md`

## 6. Verificación final
- [ ] Confirmar que el PR no contiene archivos no deseados.
- [ ] Validar que todas las rutas de documentación mencionadas existen.
- [ ] Revisar que el commit final esté firmado o autorizado según tu flujo de entrega.
- [ ] Si corresponde, agregar etiqueta: `release/2.0.0`, `defensa`, `entrega-final`.

---

> Nota: si tu folder local no contiene `.git`, primero asegúrate de clonar el repositorio correcto y trabajar en la raíz del proyecto antes de ejecutar los comandos de Git.