"""Small CLI surface for read-only U5 batch qualification."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from source.lawspace.u5_attempt_scheduler import U5AttemptConfig, U5AttemptScheduler


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=50, dest="max_attempts")
    ap.add_argument("--candidates-json", type=Path)
    ns = ap.parse_args()
    rows = []
    if ns.candidates_json:
        raw = json.loads(ns.candidates_json.read_text(encoding="utf-8"))
        rows = list(raw if isinstance(raw, list) else raw.get("candidates", []))
    out = U5AttemptScheduler(Path(".")).run_batch(rows, config=U5AttemptConfig(max_attempts=ns.max_attempts))
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
