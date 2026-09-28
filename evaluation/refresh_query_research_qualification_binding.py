"""Refresh only the function-language qualification binding in the current query report.

This helper does not refit world data or alter stored query hypotheses.  It
replays the current mechanism qualification, binds that fresh receipt into the
existing query report, and recomputes the report digest.  Writing requires
explicit --apply.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from evaluation.function_language_birth_qualification import run_release_qualification
from source.lawspace.schema import digest_payload

REPORT = Path("data/frontiers/ATLAS_QUERY_RESEARCH_CURRENT.json")


def refreshed(root: Path) -> tuple[dict, dict]:
    path = root / REPORT
    report = json.loads(path.read_text(encoding="utf-8"))
    qualification = dict(run_release_qualification(root))
    if qualification.get("status") != "PASS_FUNCTION_LANGUAGE_BIRTH_QUALIFICATION":
        raise RuntimeError("current function-language qualification did not PASS")
    before = str(dict(report.get("function_language_birth_qualification") or {}).get("digest", ""))
    report["function_language_birth_qualification"] = qualification
    acceptance = dict(report.get("acceptance") or {})
    acceptance["function_language_birth_qualification_pass"] = True
    report["acceptance"] = acceptance
    boundary = dict(report.get("claim_boundary") or {})
    boundary.update({
        "abs_power_parameterized_birth_is_world_law": False,
        "operation_signal_without_materialization_gain_is_retained": False,
    })
    report["claim_boundary"] = boundary
    report["digest"] = digest_payload({k: v for k, v in report.items() if k != "digest"})
    meta = {
        "report": str(REPORT),
        "qualification_digest_before": before,
        "qualification_digest_after": qualification.get("digest"),
        "report_digest_after": report["digest"],
        "world_data_refit_performed": False,
        "stored_hypotheses_modified": False,
    }
    return report, meta


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("."))
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--apply", action="store_true")
    ns = ap.parse_args()
    root = ns.root.resolve()
    report, meta = refreshed(root)
    print(json.dumps(meta, ensure_ascii=False, indent=2, sort_keys=True))
    if ns.apply:
        path = root / REPORT
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
