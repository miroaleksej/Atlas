"""Thin evaluator for the authoritative neutrino owner."""
from __future__ import annotations
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from source.lawspace.neutrino import NeutrinoPhenomenologyOwner


def run(root: str | Path) -> dict:
    root_path = Path(root)
    report = dict(NeutrinoPhenomenologyOwner().run_directed_fullspace_qualification())
    output = root_path / "reports" / "neutrino_majorana_takagi_qualification_v6_9.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    run(Path(__file__).resolve().parents[1])
