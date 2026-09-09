"""Transactional current-only replay for Φ-Compiler 15.26.0.

Protocol:
    --prepare              freeze the dynamically collected current test inventory
    --batch INDEX          execute one deterministic small batch in a fresh process
    --aggregate            verify complete coverage and build the final replay receipt

No test node is optional.  Batch size and process timeouts are runtime isolation
controls only; they are neither scientific search ceilings nor truth gates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "phi-full-current-replay/v14"
OWNER_ID = "FULL-CURRENT-REPLAY-QUALIFICATION/15.26.0"
RELEASE = "15.26.0"
POLICY_RELATIVE_PATH = Path("data/runtime/EXECUTION_POLICY_CURRENT.json")
PLAN_RELATIVE_PATH = Path("reports/runtime/FULL_REPLAY_PLAN_CURRENT.json")
BATCH_DIR_RELATIVE_PATH = Path("reports/runtime/full_replay_batches")
FINAL_RELATIVE_PATH = Path("reports/FULL_HEAVY_REPLAY_CURRENT.json")


REPLAY_SURFACE_PATHS = (
    "source",
    "evaluation",
    "interfaces",
    "tests",
    "extensions",
    "data",
    "external",
    "capabilities.json",
    "invariants.json",
    "pyproject.toml",
    "Makefile",
    "MATHEMATICAL_BOOK.md",
    "reports/BLIND_REAL_PHYSICS_EXPERIMENT_CURRENT.json",
    "reports/ATLAS_FRONTIER_SCAN_CURRENT.json",
)

DEFAULT_POLICY: dict[str, Any] = {
    "schema": "phi-runtime-execution-policy/v3",
    "policy_id": "TRANSACTIONAL_SMALL_BATCH_FRESH_PROCESS_TEMPFILE",
    "max_parallel_surfaces": 1,
    "max_nodes_per_surface": 10,
    "surface_timeout_seconds": 240,
    "capture_mode": "TEMPFILE",
    "python_dont_write_bytecode": True,
    "cleanup_runtime_caches_after_replay": True,
    "scientific_search_ceiling": None,
    "source": "BUILTIN_DEFAULT",
}


def digest_payload(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _replay_surface_identity(root: Path) -> dict[str, Any]:
    """Digest every stable code/data surface that can affect current replay.

    Transactional replay reports are intentionally outside this set because they
    are outputs of replay. Canonical scientific reports are included explicitly.
    """
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rel in REPLAY_SURFACE_PATHS:
        base = root / rel
        candidates = [base] if base.is_file() else (sorted(base.rglob("*")) if base.is_dir() else [])
        for path in candidates:
            if not path.is_file():
                continue
            if "__pycache__" in path.parts or ".pytest_cache" in path.parts or path.suffix in {".pyc", ".pyo"}:
                continue
            r = str(path.relative_to(root))
            if r in seen:
                continue
            seen.add(r)
            raw = path.read_bytes()
            rows.append({"path": r, "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()})
    rows.sort(key=lambda row: row["path"])
    return {"file_count": len(rows), "digest": digest_payload(rows)}


def _clean_runtime_caches(root: Path) -> None:
    for p in list(root.rglob("__pycache__")):
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
    shutil.rmtree(root / ".pytest_cache", ignore_errors=True)
    for pattern in ("*.pyc", "*.pyo"):
        for p in root.rglob(pattern):
            p.unlink(missing_ok=True)


def _validate_policy(raw: Mapping[str, Any], *, source: str) -> dict[str, Any]:
    policy = dict(raw)
    embedded = policy.pop("digest", None)
    if embedded is not None and embedded != digest_payload(policy):
        raise ValueError(f"runtime execution policy digest mismatch: {source}")
    timeout = int(policy.get("surface_timeout_seconds", 240))
    batch = int(policy.get("max_nodes_per_surface", 10))
    if timeout < 10 or timeout > 3600:
        raise ValueError("surface_timeout_seconds must be in [10,3600]")
    if batch < 1 or batch > 32:
        raise ValueError("max_nodes_per_surface must be in [1,32]")
    if int(policy.get("max_parallel_surfaces", 1)) != 1:
        raise ValueError("current replay qualifies deterministic sequential scheduling only")
    if str(policy.get("capture_mode", "TEMPFILE")) != "TEMPFILE":
        raise ValueError("only TEMPFILE capture is qualified")
    policy.update({
        "max_parallel_surfaces": 1,
        "max_nodes_per_surface": batch,
        "surface_timeout_seconds": timeout,
        "capture_mode": "TEMPFILE",
        "python_dont_write_bytecode": bool(policy.get("python_dont_write_bytecode", True)),
        "cleanup_runtime_caches_after_replay": bool(policy.get("cleanup_runtime_caches_after_replay", True)),
        "scientific_search_ceiling": None,
        "surface_timeout_is_execution_safety_only": True,
        "batch_size_is_runtime_isolation_only": True,
        "resolved_source": source,
    })
    return policy


def _resolve_policy(root: Path) -> dict[str, Any]:
    path = root / POLICY_RELATIVE_PATH
    if path.exists():
        return _validate_policy(json.loads(path.read_text(encoding="utf-8")), source=str(POLICY_RELATIVE_PATH))
    return _validate_policy(DEFAULT_POLICY, source="BUILTIN_DEFAULT")


def _env(root: Path, policy: Mapping[str, Any]) -> dict[str, str]:
    env = os.environ.copy()
    env.update({
        "PYTHONPATH": str(root),
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTHONDONTWRITEBYTECODE": "1" if policy["python_dont_write_bytecode"] else "0",
        "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
    })
    return env


def _run(cmd: list[str], root: Path, env: Mapping[str, str], timeout_seconds: int) -> tuple[int, str]:
    # Some qualified owners intentionally keep interpreter-finalization resources
    # alive. Pytest has already produced its canonical result at that point, but
    # ``python -m pytest`` can remain alive in a multi-node batch. Execute pytest
    # through a one-shot wrapper that exits only *after* pytest.main returns and
    # stdout/stderr are flushed. This changes process teardown, not test semantics.
    if len(cmd) >= 3 and cmd[0] == sys.executable and cmd[1:3] == ["-m", "pytest"]:
        pytest_args = cmd[3:]
        runner = (
            "import os,sys,pytest; "
            "rc=pytest.main(sys.argv[1:]); "
            "sys.stdout.flush(); sys.stderr.flush(); os._exit(int(rc))"
        )
        cmd = [sys.executable, "-c", runner, *pytest_args]
    out_path = Path(tempfile.gettempdir()) / f"phi-replay-{uuid.uuid4().hex}.log"
    rc = 1
    with out_path.open("w", encoding="utf-8") as handle:
        proc = subprocess.Popen(
            cmd, cwd=str(root), env=dict(env), stdout=handle, stderr=subprocess.STDOUT,
            start_new_session=True, text=True,
        )
        try:
            rc = int(proc.wait(timeout=int(timeout_seconds)))
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
                proc.wait(timeout=5)
            except Exception:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except Exception:
                    pass
                try:
                    proc.wait(timeout=5)
                except Exception:
                    pass
            rc = 124
    out = out_path.read_text(encoding="utf-8", errors="replace") if out_path.exists() else ""
    out_path.unlink(missing_ok=True)
    if rc == 124:
        out += f"\nTIMEOUT after {timeout_seconds}s\n"
    return int(rc), out


def _collect_nodes(root: Path, policy: Mapping[str, Any]) -> list[str]:
    rc, out = _run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        root, _env(root, policy), int(policy["surface_timeout_seconds"]),
    )
    if rc:
        raise RuntimeError(out)
    nodes = [line.strip() for line in out.splitlines() if line.strip().startswith("tests/") and "::" in line]
    if not nodes:
        raise RuntimeError("empty current test inventory")
    return nodes


def prepare(root: str | Path | None = None) -> dict[str, Any]:
    root = Path(root or ROOT).resolve()
    policy = _resolve_policy(root)
    _clean_runtime_caches(root)
    nodes = _collect_nodes(root, policy)
    batch_size = int(policy["max_nodes_per_surface"])
    batches = [nodes[i:i + batch_size] for i in range(0, len(nodes), batch_size)]
    replay_surface = _replay_surface_identity(root)
    historical = [n for n in nodes if re.search(r"(?:^|/)(?:legacy|old|historical)(?:/|_)|(?:^|/)test_v\d|lawvoid_0\d", n.split("::", 1)[0], re.I)]
    plan = {
        "schema": "phi-full-current-replay-plan/v3",
        "owner_id": OWNER_ID, "release": RELEASE,
        "status": "CURRENT_TEST_INVENTORY_FROZEN",
        "nodes": nodes, "node_count": len(nodes), "historical_nodes": historical,
        "batch_size": batch_size, "batches": batches, "batch_count": len(batches),
        "test_surface_digest": replay_surface["digest"],
        "test_surface_file_count": replay_surface["file_count"],
        "execution_policy": policy,
        "claim_boundary": {
            "batch_size_is_scientific_search_ceiling": False,
            "test_nodes_removed_by_partitioning": False,
            "replay_receipts_bound_to_test_relevant_bytes": True,
        },
    }
    plan["digest"] = digest_payload(plan)
    plan_path = root / PLAN_RELATIVE_PATH
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    batch_dir = root / BATCH_DIR_RELATIVE_PATH
    shutil.rmtree(batch_dir, ignore_errors=True)
    batch_dir.mkdir(parents=True, exist_ok=True)
    return plan


def _load_plan(root: Path) -> dict[str, Any]:
    path = root / PLAN_RELATIVE_PATH
    if not path.exists():
        raise RuntimeError("full replay plan is missing; run --prepare first")
    plan = json.loads(path.read_text(encoding="utf-8"))
    embedded = plan.get("digest")
    core = dict(plan); core.pop("digest", None)
    if embedded != digest_payload(core):
        raise RuntimeError("full replay plan digest mismatch")
    return plan


def run_batch(index: int, root: str | Path | None = None) -> dict[str, Any]:
    root = Path(root or ROOT).resolve()
    plan = _load_plan(root)
    batches = list(plan["batches"])
    idx = int(index)
    if idx < 0 or idx >= len(batches):
        raise IndexError(f"batch index {idx} outside 0..{len(batches)-1}")
    batch = list(batches[idx])
    policy = dict(plan["execution_policy"])
    surface_before = _replay_surface_identity(root)
    if surface_before["digest"] != plan.get("test_surface_digest"):
        rc, out = 125, "REFUSED_TEST_SURFACE_DIGEST_CHANGED_BEFORE_BATCH"
    else:
        rc, out = _run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *batch],
            root, _env(root, policy), int(policy["surface_timeout_seconds"]),
        )
    surface_after = _replay_surface_identity(root)
    matches = re.findall(r"(\d+) passed", out)
    batch_passed = int(matches[-1]) if rc == 0 and matches else 0
    surface_unchanged = (
        surface_before["digest"] == plan.get("test_surface_digest")
        and surface_after["digest"] == plan.get("test_surface_digest")
    )
    batch_ok = rc == 0 and batch_passed == len(batch) and surface_unchanged
    receipt = {
        "schema": "phi-full-current-replay-batch/v3",
        "owner_id": OWNER_ID, "release": RELEASE,
        "plan_digest": plan["digest"], "batch_index": idx,
        "status": "PASS" if batch_ok else "FAIL",
        "node_count": len(batch), "passed": batch_passed if batch_ok else 0,
        "returncode": rc, "nodeids": batch,
        "test_surface_digest": plan.get("test_surface_digest"),
        "surface_digest_before": surface_before["digest"],
        "surface_digest_after": surface_after["digest"],
        "test_files": sorted({n.split("::", 1)[0] for n in batch}),
        "output_tail": "\n".join(out.splitlines()[-12:]),
        "claim_boundary": {
            "fresh_process_for_this_batch": True,
            "batch_runtime_limit_is_scientific_search_ceiling": False,
            "test_relevant_surface_unchanged": surface_unchanged,
        },
    }
    canonical_receipt = {k: v for k, v in receipt.items() if k != "output_tail"}
    receipt["digest_scope"] = "CANONICAL_TEST_IDENTITY_AND_RESULT_EXCLUDES_VOLATILE_STDOUT_TIMING"
    canonical_receipt["digest_scope"] = receipt["digest_scope"]
    receipt["digest"] = digest_payload(canonical_receipt)
    path = root / BATCH_DIR_RELATIVE_PATH / f"batch_{idx:03d}.json"
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def aggregate(root: str | Path | None = None) -> dict[str, Any]:
    root = Path(root or ROOT).resolve()
    plan = _load_plan(root)
    policy = _resolve_policy(root)
    current_nodes = _collect_nodes(root, policy)
    inventory_unchanged = current_nodes == list(plan["nodes"])
    current_surface = _replay_surface_identity(root)
    receipts = []
    missing_batches = []
    for idx in range(int(plan["batch_count"])):
        path = root / BATCH_DIR_RELATIVE_PATH / f"batch_{idx:03d}.json"
        if not path.exists():
            missing_batches.append(idx); continue
        receipt = json.loads(path.read_text(encoding="utf-8"))
        embedded = receipt.get("digest")
        core = {k: v for k, v in receipt.items() if k not in {"digest", "output_tail"}}
        if embedded != digest_payload(core):
            receipt = {**receipt, "status": "FAIL_DIGEST_MISMATCH"}
        receipts.append(receipt)
    covered = [node for r in sorted(receipts, key=lambda x: int(x["batch_index"])) for node in r.get("nodeids", ())]
    passed = sum(int(r.get("passed", 0)) for r in receipts if r.get("status") == "PASS")
    checks = {
        "inventory_nonempty": bool(plan["nodes"]),
        "inventory_unchanged_since_prepare": inventory_unchanged,
        "no_historical_test_nodes": not plan.get("historical_nodes"),
        "no_missing_batch_receipts": not missing_batches,
        "all_batch_receipts_bound_to_plan": all(r.get("plan_digest") == plan["digest"] for r in receipts),
        "all_surfaces_pass": len(receipts) == int(plan["batch_count"]) and all(r.get("status") == "PASS" for r in receipts),
        "covered_nodes_equal_frozen_inventory_exactly": covered == list(plan["nodes"]),
        "passed_equals_inventory": passed == int(plan["node_count"]),
        "test_relevant_surface_digest_unchanged": current_surface["digest"] == plan.get("test_surface_digest"),
        "all_batch_receipts_bound_to_test_surface": all(
            r.get("test_surface_digest") == plan.get("test_surface_digest")
            and r.get("surface_digest_before") == plan.get("test_surface_digest")
            and r.get("surface_digest_after") == plan.get("test_surface_digest")
            for r in receipts
        ),
        "scientific_search_ceiling_absent": policy.get("scientific_search_ceiling") is None,
    }
    payload = {
        "schema": SCHEMA, "owner_id": OWNER_ID, "release": RELEASE,
        "status": f"PASS_FULL_CURRENT_{passed}_OF_{plan['node_count']}" if all(checks.values()) else "FAIL_FULL_CURRENT_REPLAY",
        "expected_test_count": int(plan["node_count"]), "passed_test_count": passed,
        "test_files": sorted({n.split("::", 1)[0] for n in plan["nodes"]}),
        "surface_count": len(receipts), "execution_unit": "TRANSACTIONAL_SMALL_BATCH_PER_FRESH_PROCESS",
        "plan_digest": plan["digest"],
        "test_surface_digest": plan.get("test_surface_digest"),
        "test_surface_file_count": plan.get("test_surface_file_count"),
        "reports": sorted(receipts, key=lambda x: int(x["batch_index"])),
        "historical_nodes": plan.get("historical_nodes", []), "missing_batches": missing_batches,
        "checks": checks, "execution_policy": policy,
        "claim_boundary": {
            "runtime_timeout_is_scientific_ceiling": False,
            "batch_size_is_scientific_search_ceiling": False,
            "tests_removed_to_obtain_pass": False,
            "scientific_criteria_mutated_by_replay": False,
            "replay_receipts_bound_to_test_relevant_bytes": True,
        },
    }
    # The persisted report may retain diagnostic stdout tails, but the canonical
    # replay identity must depend only on test identity/result and the frozen plan.
    # Otherwise wall-clock timing emitted by pytest makes two scientifically
    # identical fresh-process replays hash differently.
    payload["digest_scope"] = "CANONICAL_AGGREGATE_EXCLUDES_VOLATILE_BATCH_STDOUT_TAILS"
    canonical_payload = dict(payload)
    canonical_payload["reports"] = [
        {k: v for k, v in report.items() if k != "output_tail"}
        for report in payload["reports"]
    ]
    payload["digest"] = digest_payload(canonical_payload)
    final = root / FINAL_RELATIVE_PATH
    final.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if policy["cleanup_runtime_caches_after_replay"]:
        _clean_runtime_caches(root)
    return payload


def run(root: str | Path | None = None) -> dict[str, Any]:
    """Convenience runner for ordinary environments; transactional CLI is canonical."""
    plan = prepare(root)
    for idx in range(int(plan["batch_count"])):
        run_batch(idx, root)
    return aggregate(root)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--batch", type=int)
    parser.add_argument("--aggregate", action="store_true")
    parser.add_argument("--print-batch-count", action="store_true")
    args = parser.parse_args()
    if args.prepare:
        out = prepare()
    elif args.batch is not None:
        out = run_batch(args.batch)
    elif args.aggregate:
        out = aggregate()
    elif args.print_batch_count:
        out = {"batch_count": int(_load_plan(ROOT)["batch_count"])}
    else:
        out = run()
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
