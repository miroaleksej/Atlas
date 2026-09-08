"""Thin evaluator for the authoritative neutrino algebraic owner."""
from __future__ import annotations
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from source.lawspace.algebraic_experiment import NeutrinoAlgebraicExperimentalOwner


def run(root: str | Path) -> dict:
    root_path = Path(root)
    report = dict(NeutrinoAlgebraicExperimentalOwner().run_qualification())
    output = root_path / "reports" / "neutrino_algebraic_qualification_v5_6.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    run(Path(__file__).resolve().parents[1])
