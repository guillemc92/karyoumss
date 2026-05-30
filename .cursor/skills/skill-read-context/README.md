# Skill_Read_Context

Skill del **Core Agent KaryouMSS** para leer e interpretar requerimientos funcionales sin inventar datos.

## Instalación

- **Proyecto (recomendado):** ya en `.cursor/skills/skill-read-context/`
- **Global:** copiar la carpeta a `~/.cursor/skills/skill-read-context/`

## Uso rápido

```bash
# Desde la raíz del repo
python .cursor/skills/skill-read-context/scripts/read_context.py docs/fsd/FSD_vFinal.md
python .cursor/skills/skill-read-context/scripts/read_context.py docs/prd/PRD_vFinal.md --detail full -o context/prd.json
python .cursor/skills/skill-read-context/scripts/read_context.py AGENTS.md --detail standard
```

## Parámetros CLI

| Flag | Valores | Default |
|------|---------|---------|
| `file_path` | ruta al `.md` | (obligatorio) |
| `--format` | `auto`, `markdown`, `md` | `auto` |
| `--detail` | `summary`, `standard`, `full` | `standard` |
| `-o` | ruta salida JSON | stdout |

## Invocación en Cursor

Menciona `@skill-read-context` o `Skill_Read_Context` en el chat. El agente debe ejecutar el script y basar respuestas en el JSON.

## Plantilla base

Estructura derivada de `md/SKILL_TEMPLATE (1).md` (Módulo 4 UMSS).

## Dependencias

Python 3.11+ — solo biblioteca estándar.
