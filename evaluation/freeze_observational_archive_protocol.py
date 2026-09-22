"""CLI only: freeze a natural-sample protocol through AdaptiveResearchKernelOwner.

Scientific semantics live in source/lawspace/research_cycle.py.  This module only
loads JSON, delegates to the core, and writes an immutable receipt.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from source.lawspace.research_cycle import AdaptiveResearchKernelOwner


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", required=True)
    ap.add_argument("--output", required=True)
    ns = ap.parse_args()
    request_path = Path(ns.request)
    output_path = Path(ns.output)
    request = json.loads(request_path.read_text())
    freeze_basis_digest = str(request.get("freeze_basis_digest", "")).strip()
    if not freeze_basis_digest:
        raise SystemExit("request requires freeze_basis_digest")
    source = AdaptiveResearchKernelOwner._source_capability_contract(request)
    protocol = AdaptiveResearchKernelOwner._freeze_observational_archive_protocol(
        request, source_capability=source, freeze_basis_digest=freeze_basis_digest,
    )
    receipt = {
        "schema": "atlas-observational-archive-freeze-cli/v1",
        "status": protocol["status"],
        "request_path": str(request_path),
        "request_sha256": _sha256(request_path),
        "source_capability": source,
        "protocol": protocol,
        "claim_boundary": {
            "cli_contains_scientific_reasoning_algorithm": False,
            "fresh_measurements_acquired": False,
            "scientific_law_established": False,
        },
    }
    text = json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if output_path.exists():
        old = output_path.read_text()
        if old != text:
            raise SystemExit(f"refusing to overwrite different frozen protocol: {output_path}")
        print(f"OBSERVATIONAL_FREEZE_ALREADY_IDENTICAL {protocol['digest']}")
        return 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text)
    print(f"STATUS: {protocol['status']}")
    print(f"SOURCE_CLASS: {source['class']}")
    print(f"SAMPLES: {len(protocol['sample_ids'])}")
    print(f"FRESH_MEASUREMENT: {protocol['fresh_measurement_status']}")
    print(f"PROTOCOL_DIGEST: {protocol['digest']}")
    print(f"OUTPUT: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
