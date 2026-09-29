"""Run the provider/frontier WORLD campaign gate without fabricating attestation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from source.lawspace.source_capabilities import run_world_closed_loop_campaign


ROOT = Path(__file__).resolve().parents[1]


def run(root: str | Path = ROOT, *, max_frontier_rows: int = 200, max_campaign_items: int = 10):
    return run_world_closed_loop_campaign(
        root,
        max_frontier_rows=max_frontier_rows,
        max_campaign_items=max_campaign_items,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--max-frontier-rows", type=int, default=200)
    ap.add_argument("--max-campaign-items", type=int, default=10)
    ap.add_argument("--out")
    ns = ap.parse_args()
    result = run(
        ns.root,
        max_frontier_rows=ns.max_frontier_rows,
        max_campaign_items=ns.max_campaign_items,
    )
    if ns.out:
        path = Path(ns.out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
