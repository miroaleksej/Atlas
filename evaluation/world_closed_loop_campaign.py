"""Run the provider/frontier WORLD campaign gate without fabricating attestation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from source.lawspace.source_capabilities import (
    audit_existing_closed_loop_integration,
    compile_required_evidence_routes,
    compile_universal_required_evidence_loop,
    run_existing_closed_loop_glue,
    run_existing_lowering_projection_preflight,
    run_world_closed_loop_campaign,
)


ROOT = Path(__file__).resolve().parents[1]


def run(root: str | Path = ROOT, *, max_frontier_rows: int = 200, max_campaign_items: int = 10):
    return run_world_closed_loop_campaign(
        root,
        max_frontier_rows=max_frontier_rows,
        max_campaign_items=max_campaign_items,
    )


def audit(root: str | Path = ROOT, *, max_frontier_rows: int = 500, max_campaign_items: int = 8):
    return audit_existing_closed_loop_integration(
        root,
        max_frontier_rows=max_frontier_rows,
        max_campaign_items=max_campaign_items,
    )


def glue(root: str | Path = ROOT, *, max_frontier_rows: int = 500, max_campaign_items: int = 8):
    return run_existing_closed_loop_glue(
        root,
        max_frontier_rows=max_frontier_rows,
        max_campaign_items=max_campaign_items,
    )


def preflight(root: str | Path = ROOT, *, max_frontier_rows: int = 500, max_campaign_items: int = 8):
    return run_existing_lowering_projection_preflight(
        root,
        max_frontier_rows=max_frontier_rows,
        max_campaign_items=max_campaign_items,
    )


def routes(root: str | Path = ROOT, *, max_frontier_rows: int = 500, max_campaign_items: int = 8):
    return compile_required_evidence_routes(
        root,
        max_frontier_rows=max_frontier_rows,
        max_campaign_items=max_campaign_items,
    )


def universal_loop(root: str | Path = ROOT, *, max_frontier_rows: int = 500, max_campaign_items: int = 8):
    return compile_universal_required_evidence_loop(
        root,
        max_frontier_rows=max_frontier_rows,
        max_campaign_items=max_campaign_items,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", default=str(ROOT))
    ap.add_argument("--max-frontier-rows", type=int, default=200)
    ap.add_argument("--max-campaign-items", type=int, default=10)
    ap.add_argument("--audit-existing-systems", action="store_true")
    ap.add_argument("--run-existing-glue", action="store_true")
    ap.add_argument("--run-lowering-projection-preflight", action="store_true")
    ap.add_argument("--compile-required-evidence-routes", action="store_true")
    ap.add_argument("--compile-universal-required-evidence-loop", action="store_true")
    ap.add_argument("--out")
    ns = ap.parse_args()
    selected_modes = [
        ns.audit_existing_systems,
        ns.run_existing_glue,
        ns.run_lowering_projection_preflight,
        ns.compile_required_evidence_routes,
        ns.compile_universal_required_evidence_loop,
    ]
    if sum(bool(x) for x in selected_modes) > 1:
        raise SystemExit("--audit-existing-systems, --run-existing-glue, --run-lowering-projection-preflight, --compile-required-evidence-routes and --compile-universal-required-evidence-loop are mutually exclusive")
    if ns.audit_existing_systems:
        result = audit(
            ns.root,
            max_frontier_rows=ns.max_frontier_rows,
            max_campaign_items=ns.max_campaign_items,
        )
    elif ns.run_existing_glue:
        result = glue(
            ns.root,
            max_frontier_rows=ns.max_frontier_rows,
            max_campaign_items=ns.max_campaign_items,
        )
    elif ns.run_lowering_projection_preflight:
        result = preflight(
            ns.root,
            max_frontier_rows=ns.max_frontier_rows,
            max_campaign_items=ns.max_campaign_items,
        )
    elif ns.compile_required_evidence_routes:
        result = routes(
            ns.root,
            max_frontier_rows=ns.max_frontier_rows,
            max_campaign_items=ns.max_campaign_items,
        )
    elif ns.compile_universal_required_evidence_loop:
        result = universal_loop(
            ns.root,
            max_frontier_rows=ns.max_frontier_rows,
            max_campaign_items=ns.max_campaign_items,
        )
    else:
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
