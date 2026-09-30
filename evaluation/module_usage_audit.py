"""Audit Atlas module reachability without activating every subsystem.

The audit answers a narrow engineering question: which Python modules are
connected to the current Atlas runtime, tests, reports, or sealed artifacts, and
which modules would require retirement/integration review before they could be
removed.  It is deliberately read-only and does not treat an inventory count as
scientific evidence.
"""
from __future__ import annotations

import argparse
import ast
import importlib
import json
from pathlib import Path
from typing import Any, Mapping

from source.lawspace.schema import digest_payload


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "phi-module-usage-audit/v1"


def _python_files(root: Path) -> list[Path]:
    skipped = {".git", ".venv", "__pycache__"}
    return [
        p
        for p in root.rglob("*.py")
        if not any(part in skipped for part in p.parts)
    ]


def _module_name(root: Path, path: Path) -> str:
    return ".".join(path.relative_to(root).with_suffix("").parts)


def _source_modules(root: Path) -> dict[str, Path]:
    source_root = root / "source" / "lawspace"
    out: dict[str, Path] = {}
    for path in sorted(source_root.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        out[_module_name(root, path)] = path
    return out


def _resolve_import_from(module: str, level: int, importer: str) -> str:
    if level <= 0:
        return module
    parts = importer.split(".")[:-1]
    base = parts[: max(0, len(parts) - level + 1)]
    if module:
        base.extend(module.split("."))
    return ".".join(base)


def _python_references(root: Path, modules: Mapping[str, Path]) -> tuple[dict[str, set[str]], list[Mapping[str, str]]]:
    refs = {name: set() for name in modules}
    errors: list[Mapping[str, str]] = []
    for path in _python_files(root):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - receipt records parse failure
            errors.append({"path": str(path.relative_to(root)), "error": f"{type(exc).__name__}: {exc}"})
            continue
        importer = _module_name(root, path) if path.is_relative_to(root) else ""
        for node in ast.walk(tree):
            candidates: list[str] = []
            if isinstance(node, ast.Import):
                candidates.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                base = _resolve_import_from(node.module or "", node.level, importer)
                candidates.append(base)
                candidates.extend(f"{base}.{alias.name}" for alias in node.names if base)
            for candidate in candidates:
                for mod_name, mod_path in modules.items():
                    if path == mod_path:
                        continue
                    if candidate == mod_name or candidate.startswith(mod_name + "."):
                        refs[mod_name].add(str(path.relative_to(root)))
    return refs, errors


def _constant_strings(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    out: list[str] = []
    interesting = {"OWNER_ID", "OWNER", "SCHEMA", "OWNER_SCHEMA"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if any(t in interesting or t.endswith("_SCHEMA") or t.endswith("_OWNER_ID") for t in targets):
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    out.append(node.value.value)
    return out


def _artifact_references(root: Path, modules: Mapping[str, Path]) -> dict[str, set[str]]:
    refs = {name: set() for name in modules}
    text_suffixes = {".md", ".json", ".jsonl", ".txt", ".yml", ".yaml"}
    skipped = {".git", ".venv", "__pycache__"}
    control_files = {
        "FILE_TREE.md",
        "HASHES.txt",
        "RELEASE_MANIFEST.json",
        "reports/MODULE_USAGE_AUDIT_CURRENT.json",
    }
    needles: dict[str, set[str]] = {}
    for name, path in modules.items():
        stem = path.stem
        module_tail = name.rsplit(".", 1)[-1]
        classish = "".join(part.capitalize() for part in stem.split("_"))
        values = {stem, module_tail, name}
        values.update(_constant_strings(path))
        if classish:
            values.add(classish)
        needles[name] = {value for value in values if value and len(value) >= 4}
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in text_suffixes:
            continue
        if any(part in skipped for part in path.parts):
            continue
        rel = str(path.relative_to(root))
        if rel.startswith("source/lawspace/"):
            continue
        if rel in control_files:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for name, values in needles.items():
            if any(value in text for value in values):
                refs[name].add(rel)
    return refs


def _import_status(modules: Mapping[str, Path]) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for name in modules:
        try:
            importlib.import_module(name)
            out[name] = {"status": "IMPORT_OK"}
        except Exception as exc:  # pragma: no cover - receipt records import failure
            out[name] = {"status": "IMPORT_FAILED", "error": f"{type(exc).__name__}: {exc}"}
    return out


def _classify(
    *,
    module: str,
    py_refs: set[str],
    artifact_refs: set[str],
    import_status: Mapping[str, Any],
) -> str:
    if import_status.get("status") != "IMPORT_OK":
        return "BROKEN_IMPORT_REQUIRES_FIX_OR_RETIREMENT"
    if any(ref.startswith("source/lawspace/api.py") for ref in py_refs):
        return "PUBLIC_API_ROUTED"
    if any(ref.startswith("tests/") for ref in py_refs):
        return "TEST_COVERED_RUNTIME"
    if any(ref.startswith("evaluation/") for ref in py_refs):
        return "EVALUATION_ROUTED"
    if any(ref.startswith("source/lawspace/") for ref in py_refs):
        return "INTERNAL_RUNTIME_SUPPORT"
    if py_refs:
        return "PYTHON_REFERENCED_SUPPORT"
    if artifact_refs:
        return "SEALED_ARTIFACT_OR_DOCUMENTED_DIAGNOSTIC"
    return "RETIREMENT_REVIEW_REQUIRED_NO_REFERENCES"


def run_module_usage_audit(root: str | Path = ROOT) -> Mapping[str, Any]:
    root_path = Path(root)
    modules = _source_modules(root_path)
    py_refs, parse_errors = _python_references(root_path, modules)
    artifact_refs = _artifact_references(root_path, modules)
    imports = _import_status(modules)
    rows = []
    for name, path in sorted(modules.items()):
        py = sorted(py_refs[name])
        art = sorted(artifact_refs[name])
        status = _classify(module=name, py_refs=set(py), artifact_refs=set(art), import_status=imports[name])
        row = {
            "module": name,
            "path": str(path.relative_to(root_path)),
            "status": status,
            "import_status": imports[name],
            "python_reference_count": len(py),
            "test_reference_count": sum(ref.startswith("tests/") for ref in py),
            "evaluation_reference_count": sum(ref.startswith("evaluation/") for ref in py),
            "source_reference_count": sum(ref.startswith("source/lawspace/") for ref in py),
            "artifact_reference_count": len(art),
            "sample_python_references": py[:12],
            "sample_artifact_references": art[:12],
        }
        row["digest"] = digest_payload(row)
        rows.append(row)
    status_counts: dict[str, int] = {}
    for row in rows:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    retirement_review = [row for row in rows if row["status"] == "RETIREMENT_REVIEW_REQUIRED_NO_REFERENCES"]
    import_failures = [row for row in rows if row["import_status"].get("status") != "IMPORT_OK"]
    report = {
        "schema": SCHEMA,
        "status": (
            "MODULE_USAGE_AUDIT_PASS_NO_UNREFERENCED_SOURCE_MODULES"
            if not retirement_review and not import_failures
            else "MODULE_USAGE_AUDIT_REVIEW_REQUIRED"
        ),
        "source_module_count": len(rows),
        "evaluation_module_count": len(list((root_path / "evaluation").glob("*.py"))),
        "test_module_count": len(list((root_path / "tests").glob("test_*.py"))),
        "status_counts": dict(sorted(status_counts.items())),
        "parse_errors": parse_errors,
        "import_failure_count": len(import_failures),
        "retirement_review_count": len(retirement_review),
        "retirement_review_modules": [row["module"] for row in retirement_review],
        "documented_diagnostic_modules": [
            row["module"] for row in rows if row["status"] == "SEALED_ARTIFACT_OR_DOCUMENTED_DIAGNOSTIC"
        ],
        "claim_boundary": {
            "audit_activates_all_modules_for_every_question": False,
            "unused_by_python_means_scientifically_false": False,
            "sealed_diagnostic_may_be_deleted_without_lineage_review": False,
            "module_inventory_is_scientific_evidence": False,
        },
        "modules": rows,
    }
    return {**report, "digest": digest_payload(report)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--out")
    ns = ap.parse_args()
    result = run_module_usage_audit(ns.root)
    if ns.out:
        path = Path(ns.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
