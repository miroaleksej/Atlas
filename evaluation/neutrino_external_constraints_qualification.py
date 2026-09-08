#!/usr/bin/env python3
"""Thin evaluator for NEUTRINO-EXTERNAL-CONSTRAINTS."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from source.lawspace.neutrino_external_constraints import NeutrinoExternalConstraintsOwner


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        instance = NeutrinoExternalConstraintsOwner(args.root)
    except TypeError:
        instance = NeutrinoExternalConstraintsOwner()
    report = instance.run_qualification()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
