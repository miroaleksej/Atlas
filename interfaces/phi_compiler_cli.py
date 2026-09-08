#!/usr/bin/env python3
"""Thin CLI for Φ-Compiler current-state external qualification; no scientific algorithms."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.lawspace_qualification import run_lawspace_qualification
from evaluation.phi_bench import run_hardware_digital_twin_benchmark, run_multiseed_benchmark
from evaluation.phi_physical_exam import (
    run_adapter_relay_contract,
    run_prebuild_qualification,
    run_real_device_open_loop_qualification,
)
from source.lawspace.api import LawSpaceAPI
from source.lawspace.runtime import LawSpaceRuntime
from source.lawspace.candidates import CandidateGenerationPipeline, regenerate_candidates, load_candidate_spot_checks, regenerate_quantum_method_routes
from source.lawspace.schema import digest_payload
from source.lawspace.resident_cognitive import ResidentStateLedgerOwner, validate_external_state_path
from evaluation.read_only_audit import run as run_read_only_audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ΦCompiler current-state qualification, query or autonomous research")
    legacy_modes = ("lawspace", "lawspace-query", "candidate-query", "candidate-scan", "candidate-regenerate", "quantum-method-scan", "quantum-method-query", "synthetic", "hardware-twin", "physical-prebuild", "physical-adapter", "physical-open-loop", "all-offline")
    parser.add_argument("command", nargs="?", choices=("research","resident-state-restore","audit-read-only"), help="Modern terminal command; legacy modes remain available through --mode")
    parser.add_argument("question", nargs="?", help="Human research question for the research command")
    parser.add_argument("--mode", choices=legacy_modes, default=None)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--shard-size", type=int, default=60)
    parser.add_argument("--contract", type=Path, default=ROOT / "hardware" / "PHYSICAL_STAND.json")
    parser.add_argument("--query", type=str, default="")
    parser.add_argument("--domain", type=str)
    parser.add_argument("--generator", type=str)
    parser.add_argument("--category", type=str)
    parser.add_argument("--risk", type=str)
    parser.add_argument("--source-owner", type=str)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--max-order", type=int, default=None, help="Optional explicit prefix order; omitted means all registered method orders")
    parser.add_argument("--combination-budget", type=int, default=None, help="Fail-closed upper bound for method combinations; omitted means the exact finite full scan")
    parser.add_argument("--capability", type=str)
    parser.add_argument("--host", type=str)
    parser.add_argument("--expected-serial", type=str)
    parser.add_argument("--operator-approved", action="store_true")
    parser.add_argument("--raw-output", type=Path)
    parser.add_argument("--state-dir", type=Path, help="External mutable workspace for Resident state; defaults to PHI_STATE_DIR/XDG state")
    parser.add_argument("--read-only-state", action="store_true", help="Run research without committing Resident state")
    parser.add_argument("--snapshot", type=Path, help="Resident state snapshot JSON for resident-state-restore")
    parser.add_argument("--expected-sha256", type=str, help="Optional expected SHA-256 of the resident snapshot")
    parser.add_argument("--overwrite-state", action="store_true", help="Explicitly allow replacement of an existing external resident state")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    mode = args.command or args.mode or "all-offline"
    result = {}
    exit_code = 0
    if mode == "research":
        question = str(args.question or args.query or "").strip()
        if not question:
            parser.error('research requires a question: phi-compiler research "..."')
        request = {"question": question, "commit_resident_state": not args.read_only_state}
        if args.state_dir is not None:
            request["resident_state_path"] = str(args.state_dir / "resident_cognitive_state.json")
        result["research"] = LawSpaceAPI(ROOT).run_autonomous_research(request)
    if mode == "resident-state-restore":
        if args.snapshot is None:
            parser.error("resident-state-restore requires --snapshot")
        runtime=LawSpaceRuntime(ROOT)
        dest=(args.state_dir / "resident_cognitive_state.json") if args.state_dir is not None else runtime.external_state_path("resident_cognitive_state")
        dest=validate_external_state_path(runtime,dest)
        ledger=ResidentStateLedgerOwner(dest,system_release=runtime.current_release_id())
        result["resident_state_restore"]=ledger.restore_snapshot(args.snapshot,expected_sha256=args.expected_sha256,overwrite=args.overwrite_state)
    if mode == "audit-read-only":
        result["read_only_audit"]=run_read_only_audit(ROOT)
    if mode in ("lawspace", "all-offline"):
        result["lawspace"] = run_lawspace_qualification(ROOT)
    if mode == "lawspace-query":
        if not args.query.strip():
            parser.error("lawspace-query requires --query")
        result["lawspace_query"] = {"query": args.query, "domain": args.domain, "results": LawSpaceAPI(ROOT).search_entities(args.query, args.domain, args.limit)}
    if mode == "candidate-query":
        api = LawSpaceAPI(ROOT)
        result["candidate_query"] = {
            "domain": args.domain, "generator": args.generator, "category": args.category,
            "risk": args.risk, "source_owner": args.source_owner,
            "results": api.search_candidates(
                domain_id=args.domain, generator_id=args.generator, category=args.category,
                risk_class=args.risk, source_owner_id=args.source_owner, limit=args.limit,
            ),
        }
    if mode == "candidate-scan":
        runtime = LawSpaceRuntime(ROOT)
        regenerated, summary = CandidateGenerationPipeline(runtime.catalog, runtime.bridges, load_candidate_spot_checks(ROOT)).run()
        persisted_ids = [row.get("candidate_id") for row in runtime.candidates]
        persisted_digests = [row.get("digest") for row in runtime.candidates]
        summary = dict(summary)
        summary["persisted_count"] = len(runtime.candidates)
        summary["ids_match_persisted"] = [row["candidate_id"] for row in regenerated] == persisted_ids
        summary["digests_match_persisted"] = [row["digest"] for row in regenerated] == persisted_digests
        summary["status"] = "PASS" if summary["ids_match_persisted"] and summary["digests_match_persisted"] else "FAIL"
        summary["all_acceptance_gates_pass"] = summary["status"] == "PASS"
        summary["sha256"] = digest_payload({k: v for k, v in summary.items() if k != "sha256"})
        result["candidate_scan"] = summary
    if mode == "candidate-regenerate":
        runtime = LawSpaceRuntime(ROOT)
        result["candidate_regenerate"] = regenerate_candidates(ROOT, runtime.catalog, runtime.bridges)
    if mode == "quantum-method-scan":
        try:
            result["quantum_method_scan"] = regenerate_quantum_method_routes(
                ROOT, max_order=args.max_order, limit=args.limit, combination_budget=args.combination_budget
            )
        except RuntimeError as exc:
            if not str(exc).startswith("SCAN_BUDGET_INSUFFICIENT:"):
                raise
            result["quantum_method_scan"] = {
                "schema": "phi-quantum-method-scan-block/v4.5",
                "status": "BLOCKED_INSUFFICIENT_COMBINATION_BUDGET",
                "error": str(exc),
                "max_order": args.max_order,
                "combination_budget": args.combination_budget,
                "all_registered_orders_scanned": False,
            }
            exit_code = 2
    if mode == "quantum-method-query":
        api = LawSpaceAPI(ROOT)
        result["quantum_method_query"] = {
            "capability": args.capability,
            "results": api.search_quantum_method_routes(capability=args.capability, limit=args.limit),
        }
    if mode in ("synthetic", "all-offline"):
        result["synthetic"] = run_multiseed_benchmark(repeats_per_hypothesis=args.repeats, workers=args.workers, shard_size=args.shard_size)
    if mode in ("hardware-twin", "all-offline"):
        result["hardware_twin"] = run_hardware_digital_twin_benchmark()
    if mode in ("physical-prebuild", "all-offline"):
        result["physical_prebuild"] = run_prebuild_qualification(args.contract)
    if mode in ("physical-adapter", "all-offline"):
        result["physical_adapter"] = run_adapter_relay_contract(args.contract)
    if mode == "physical-open-loop":
        if not args.host or not args.expected_serial or args.raw_output is None:
            parser.error("physical-open-loop requires --host, --expected-serial and --raw-output")
        result["physical_open_loop"] = run_real_device_open_loop_qualification(
            args.contract, host=args.host, expected_serial=args.expected_serial,
            operator_approved=args.operator_approved, raw_output_path=args.raw_output,
        )

    payload = result[next(iter(result))] if len(result) == 1 else result
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        print(json.dumps({
            "output": str(args.output), "mode": mode,
            "reports": {key: {"status": value.get("status") if isinstance(value, dict) else None, "sha256": value.get("sha256") if isinstance(value, dict) else None, "all_acceptance_gates_pass": value.get("all_acceptance_gates_pass") if isinstance(value, dict) else None} for key, value in result.items()},
        }, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    if exit_code:
        raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
