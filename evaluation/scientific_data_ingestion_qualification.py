#!/usr/bin/env python3
"""Thin evaluator for SCIENTIFIC-DATA-INGESTION."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from source.lawspace.scientific_data_ingestion import ScientificDataIngestionOwner


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    report = ScientificDataIngestionOwner(a.root).run_qualification()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(a.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
