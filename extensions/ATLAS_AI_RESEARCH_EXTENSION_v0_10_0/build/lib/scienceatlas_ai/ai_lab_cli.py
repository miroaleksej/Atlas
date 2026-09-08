"""Thin command-line launcher for the ScienceAtlas AI Laboratory.

All scientific execution and admission logic remains in ModelExecutionOwner.
The CLI only loads contracts/artifacts, attaches a JsonCommandBackend, executes
Frontier 003, writes the receipt, and materializes the frozen results template.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ai_lab import JsonCommandBackend, ModelBackendSpec
from .frontier003 import execute_frontier003, materialize_results_template
from .provenance import canonical_bytes
from .runtime import ScienceAtlasAI


def main() -> None:
    parser = argparse.ArgumentParser(prog="scienceatlas-ai-lab")
    parser.add_argument("--backend-spec", required=True, help="JSON ModelBackendSpec")
    parser.add_argument("--manifest", required=True, help="Frozen Frontier 003 RUN_MANIFEST.csv")
    parser.add_argument("--results-template", required=True, help="Frozen RESULTS_TEMPLATE.csv")
    parser.add_argument("--results-output", required=True, help="Completed output CSV")
    parser.add_argument("--receipt", required=True, help="Laboratory execution receipt JSON")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    parser.add_argument("backend_argv", nargs=argparse.REMAINDER, help="External backend command after --")
    args = parser.parse_args()
    argv = list(args.backend_argv)
    if argv and argv[0] == "--":
        argv = argv[1:]
    if not argv:
        parser.error("external backend command is required after --")

    spec = ModelBackendSpec.from_json(json.loads(Path(args.backend_spec).read_text(encoding="utf-8")))
    backend = JsonCommandBackend(spec, argv, timeout_seconds=args.timeout_seconds)
    ai = ScienceAtlasAI()
    ai.attach_model_execution_backend(backend)
    receipt = execute_frontier003(
        ai,
        manifest_path=args.manifest,
        seed=args.seed,
        require_real=True,
    )
    receipt_path = Path(args.receipt)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_bytes(canonical_bytes(receipt))
    materialize_results_template(
        receipt=receipt,
        template_path=args.results_template,
        output_path=args.results_output,
    )
    print(json.dumps({
        "status": "COMPLETE",
        "run_digest": receipt["run_digest"],
        "measurement_count": receipt["measurement_count"],
        "receipt": str(receipt_path),
        "results": str(Path(args.results_output)),
    }, indent=2))


if __name__ == "__main__":
    main()
