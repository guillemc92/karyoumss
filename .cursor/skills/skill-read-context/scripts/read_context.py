#!/usr/bin/env python3
"""
Skill_Read_Context — Parser de requerimientos funcionales (KaryouMSS / BIOMED UMSS).

Lee artefactos Markdown (PRD, FSD, BRD, AGENTS) y devuelve JSON estructurado.
Dependencias: solo biblioteca estándar de Python 3.11+.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SUPPORTED_EXTENSIONS = {".md", ".markdown"}
DOC_TYPE_HINTS = {
    "prd": "PRD",
    "fsd": "FSD",
    "brd": "BRD",
    "mrd": "MRD",
    "agents": "AGENTS",
    "lfsd": "LFSD",
}

# --- Patrones de extracción (KaryouMSS / Spec Kit) ---

RE_FSD_UC = re.compile(
    r"(?:^|\n)#+\s*(?:\d+\.\d+\s+)?(FSD-UC-\d{3})\s*[–\-]\s*(.+?)(?:\n|$)",
    re.IGNORECASE,
)
RE_USER_STORY_ROW = re.compile(
    r"\|\s*\*\*(US-\d{2})\*\*\s*\|\s*Como\s*\*?([^|*]+)\*?",
    re.IGNORECASE,
)
RE_BR = re.compile(r"\b(BR-\d{3}|BR-\d{2}|BR-R\d)\b", re.IGNORECASE)
RE_RN = re.compile(r"\b(RN-\d{2})\s*[:：]\s*(.+?)(?=\n\n|\nRN-|\Z)", re.DOTALL)
RE_NFR = re.compile(r"\b(NFR-\d{2})\b", re.IGNORECASE)
RE_ACTOR_ROW = re.compile(
    r"^\|\s*([^|]+?)\s*\|\s*(humano|sistema|agente\s*IA)\s*\|",
    re.IGNORECASE | re.MULTILINE,
)
RE_SECTION_BLOCK = re.compile(
    r"\*\*(Precondiciones|Postcondiciones|Flujo principal|Actor principal|"
    r"Reglas de negocio aplicables)\*\*\s*:?\s*\n((?:[\s\S]*?)(?=\n\* \*\*|\n#|\Z))",
    re.IGNORECASE,
)
RE_GHERKIN_FENCE = re.compile(r"```gherkin\s*([\s\S]*?)```", re.IGNORECASE)
RE_GHERKIN_INLINE = re.compile(
    r"(Dado[^|]+?)(?:,\s*)?(cuando[^|]+?)(?:,\s*)?(entonces[^|\.]+)",
    re.IGNORECASE,
)


@dataclass
class ValidationIssue:
    code: str
    message: str
    severity: str  # error | warning


@dataclass
class ParsedContext:
    meta: dict[str, Any] = field(default_factory=dict)
    actors: list[dict[str, str]] = field(default_factory=list)
    use_cases: list[dict[str, Any]] = field(default_factory=list)
    user_stories: list[dict[str, Any]] = field(default_factory=list)
    business_rules: list[dict[str, str]] = field(default_factory=list)
    invariants: list[dict[str, str]] = field(default_factory=list)
    nfrs: list[str] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)


def normalize_markdown(text: str) -> str:
    """Normaliza escapes frecuentes en FSD exportado (\\# → #)."""
    text = text.replace("\\#", "#").replace("\\*", "*").replace("\\`", "`")
    text = re.sub(r"\\([_\-\[\]()])", r"\1", text)
    return text


def detect_doc_type(path: Path, content: str) -> str:
    name = path.stem.lower()
    for hint, doc_type in DOC_TYPE_HINTS.items():
        if hint in name:
            return doc_type
    upper = content[:2000].upper()
    if "FUNCTIONAL SPECIFICATION" in upper or "FSD-UC-" in upper:
        return "FSD"
    if "PRODUCT REQUIREMENTS" in upper or "| **US-" in content:
        return "PRD"
    if "BUSINESS REQUIREMENTS" in upper:
        return "BRD"
    if "AGENTS.MD" in upper or "REGLA DE ORO" in upper:
        return "AGENTS"
    return "UNKNOWN"


def extract_list_items(block: str) -> list[str]:
    items: list[str] = []
    for line in block.splitlines():
        line = line.strip()
        m = re.match(r"^[\d]+\.\s+(.+)$", line)
        if m:
            items.append(m.group(1).strip())
            continue
        m = re.match(r"^[-*]\s+(.+)$", line)
        if m:
            items.append(m.group(1).strip())
    return items


def extract_use_case_sections(content: str, detail: str) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for match in RE_FSD_UC.finditer(content):
        uc_id = match.group(1).upper()
        title = match.group(2).strip()
        start = match.end()
        next_uc = RE_FSD_UC.search(content, start)
        block = content[start : next_uc.start() if next_uc else len(content)]

        uc: dict[str, Any] = {
            "id": uc_id,
            "title": title,
            "main_actor": None,
            "preconditions": [],
            "postconditions": [],
            "actions": [],
            "business_rules": sorted(set(RE_BR.findall(block))),
            "gherkin": [],
        }

        for sec_match in RE_SECTION_BLOCK.finditer(block):
            label = sec_match.group(1).lower()
            body = sec_match.group(2).strip()
            if "precondicion" in label:
                uc["preconditions"] = extract_list_items(body)
            elif "postcondicion" in label:
                uc["postconditions"] = extract_list_items(body)
            elif "flujo principal" in label:
                uc["actions"] = extract_list_items(body)
            elif "actor principal" in label:
                uc["main_actor"] = body.split("\n")[0].strip().strip("*`")

        if detail in ("standard", "full"):
            for g in RE_GHERKIN_FENCE.findall(block):
                uc["gherkin"].append(g.strip())
        if detail == "full" and not uc["gherkin"]:
            uc["gherkin"] = [
                " ".join(m.groups())
                for m in RE_GHERKIN_INLINE.finditer(block)
            ]

        cases.append(uc)
    return cases


def extract_user_stories(content: str) -> list[dict[str, Any]]:
    stories: list[dict[str, Any]] = []
    for row in content.splitlines():
        if "| **US-" not in row and "| US-" not in row:
            continue
        parts = [p.strip() for p in row.split("|")]
        if len(parts) < 5:
            continue
        us_id = re.search(r"US-\d{2}", parts[1])
        if not us_id:
            continue
        gherkin_parts = RE_GHERKIN_INLINE.search(parts[3] if len(parts) > 3 else "")
        stories.append(
            {
                "id": us_id.group(0),
                "actor": parts[1].replace("**", "").split("Como")[-1].strip() if "Como" in parts[1] else parts[1],
                "story": parts[2] if len(parts) > 2 else "",
                "acceptance": parts[3] if len(parts) > 3 else "",
                "gherkin": {
                    "given": gherkin_parts.group(1).strip() if gherkin_parts else None,
                    "when": gherkin_parts.group(2).strip() if gherkin_parts else None,
                    "then": gherkin_parts.group(3).strip() if gherkin_parts else None,
                },
                "priority": parts[4] if len(parts) > 4 else None,
            }
        )
    return stories


def extract_business_rules(content: str) -> list[dict[str, str]]:
    rules: dict[str, str] = {}
    for m in re.finditer(
        r"\*\*(BR-\d{2,3}(?:\s*\([^)]+\))?)\*\*\s*[:：]\s*(.+?)(?=\n\* \*\*BR-|\n##|\Z)",
        content,
        re.DOTALL | re.IGNORECASE,
    ):
        rules[m.group(1).split("(")[0].strip()] = m.group(2).strip()[:500]
    for m in re.finditer(
        r"^\|\s*(BR-\d{3})\s*\|\s*([^|]+)\|",
        content,
        re.MULTILINE | re.IGNORECASE,
    ):
        rules[m.group(1).upper()] = m.group(2).strip()
    return [{"id": k, "description": v} for k, v in sorted(rules.items())]


def extract_invariants(content: str) -> list[dict[str, str]]:
    inv: list[dict[str, str]] = []
    for m in RE_RN.finditer(content):
        inv.append({"id": m.group(1).upper(), "description": m.group(2).strip()[:800]})
    return inv


def extract_actors(content: str) -> list[dict[str, str]]:
    actors: list[dict[str, str]] = []
    for m in RE_ACTOR_ROW.finditer(content):
        name = m.group(1).strip()
        if name.lower() in ("actor", ":----"):
            continue
        actors.append({"name": name, "type": m.group(2).strip()})
    return actors


def validate_context(ctx: ParsedContext, doc_type: str) -> None:
    issues: list[ValidationIssue] = []

    if doc_type == "FSD" and not ctx.use_cases:
        issues.append(
            ValidationIssue(
                "MISSING_USE_CASES",
                "No se encontraron bloques FSD-UC-NNN.",
                "error",
            )
        )
    for uc in ctx.use_cases:
        if not uc.get("preconditions"):
            issues.append(
                ValidationIssue(
                    "INCOMPLETE_UC",
                    f"{uc['id']}: sin precondiciones detectadas.",
                    "warning",
                )
            )
        if not uc.get("actions") and doc_type == "FSD":
            issues.append(
                ValidationIssue(
                    "INCOMPLETE_UC",
                    f"{uc['id']}: sin flujo principal / acciones.",
                    "warning",
                )
            )

    if doc_type == "PRD" and not ctx.user_stories:
        issues.append(
            ValidationIssue(
                "MISSING_USER_STORIES",
                "No se encontraron filas US-NN en tablas.",
                "warning",
            )
        )

    total_checks = max(len(ctx.use_cases) * 3, 1)
    failed = sum(1 for i in issues if i.severity == "error")
    warnings = sum(1 for i in issues if i.severity == "warning")
    score = max(0.0, 1.0 - (failed * 0.5 + warnings * 0.1) / total_checks)

    ctx.validation = {
        "completeness_score": round(score, 2),
        "is_valid": failed == 0,
        "issues": [asdict(i) for i in issues],
    }


def parse_requirements(
    file_path: Path,
    doc_format: str = "auto",
    detail_level: str = "standard",
) -> ParsedContext:
    if not file_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")

    ext = file_path.suffix.lower()
    if doc_format == "auto":
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Formato no soportado: {ext}. Use .md o especifique --format markdown."
            )
    elif doc_format not in ("markdown", "md"):
        raise ValueError(f"Formato no soportado: {doc_format}")

    raw = file_path.read_text(encoding="utf-8")
    content = normalize_markdown(raw)
    doc_type = detect_doc_type(file_path, content)

    ctx = ParsedContext(
        meta={
            "source_file": str(file_path.resolve()),
            "doc_type": doc_type,
            "detail_level": detail_level,
            "parsed_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    if detail_level in ("standard", "full"):
        ctx.actors = extract_actors(content)
        ctx.business_rules = extract_business_rules(content)
        ctx.invariants = extract_invariants(content)
        ctx.nfrs = sorted(set(RE_NFR.findall(content)))

    if doc_type in ("FSD", "UNKNOWN") and detail_level != "summary":
        ctx.use_cases = extract_use_case_sections(content, detail_level)

    if doc_type in ("PRD", "UNKNOWN"):
        ctx.user_stories = extract_user_stories(content)

    if detail_level == "summary":
        ctx.use_cases = [{"id": u["id"], "title": u["title"]} for u in ctx.use_cases]
        ctx.user_stories = [{"id": u["id"]} for u in ctx.user_stories]

    validate_context(ctx, doc_type)
    return ctx


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Skill_Read_Context — parsea requerimientos funcionales a JSON."
    )
    parser.add_argument(
        "file_path",
        type=Path,
        help="Ruta al artefacto (ej. docs/FSD_v2.md, docs/PRD_v2.md)",
    )
    parser.add_argument(
        "--format",
        choices=["auto", "markdown", "md"],
        default="auto",
        help="Formato del archivo (default: auto)",
    )
    parser.add_argument(
        "--detail",
        choices=["summary", "standard", "full"],
        default="standard",
        help="Nivel de detalle en la salida (default: standard)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Archivo JSON de salida (default: stdout)",
    )
    args = parser.parse_args()

    try:
        ctx = parse_requirements(args.file_path, args.format, args.detail)
        payload = json.dumps(asdict(ctx), ensure_ascii=False, indent=2)
        if args.output:
            args.output.write_text(payload, encoding="utf-8")
        else:
            print(payload)
        return 0 if ctx.validation.get("is_valid", True) else 2
    except FileNotFoundError as e:
        print(json.dumps({"error": {"code": "FILE_NOT_FOUND", "message": str(e)}}), file=sys.stderr)
        return 1
    except ValueError as e:
        print(json.dumps({"error": {"code": "UNSUPPORTED_FORMAT", "message": str(e)}}), file=sys.stderr)
        return 1
    except Exception as e:
        print(
            json.dumps({"error": {"code": "PARSE_ERROR", "message": str(e)}}),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
