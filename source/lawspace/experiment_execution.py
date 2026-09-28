"""Contract-driven execution components for the existing scientific owners.

This is orchestration, not a new scientific owner or fitting engine. Host-bound
adapters are trusted code; JSON cannot import code, authorize hardware, or prove
source authenticity. Hashes establish content identity, not historical priority.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import tempfile
import time

import numpy as np

from .schema import digest_payload

SCHEMA = "phi-frozen-experiment-execution/v1"
STAGES = ("SOURCE_CAPABILITY", "FREEZE_EXPERIMENT", "FREEZE_SAMPLES",
          "FREEZE_HYPOTHESES_FORMS", "ACQUIRE_EVIDENCE", "VERIFY_PROVENANCE",
          "MEASUREMENT_ADAPTER", "EVALUATE_FROZEN_PREDICTIONS", "ADJUDICATE",
          "THEORY_REVISION")


class TransientAcquisitionError(RuntimeError):
    """Only explicitly classified transport failures are retryable."""


def sealed(payload):
    payload = deepcopy(payload)
    payload["digest"] = digest_payload(payload)
    return payload


def verify(payload):
    if payload.get("digest") != digest_payload({k: v for k, v in payload.items() if k != "digest"}):
        raise ValueError("content digest mismatch")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def adapter_binding(adapter):
    """Bind explicit adapter implementation, declared dependencies and configuration."""
    files = [Path(inspect.getfile(type(adapter))), *map(Path, getattr(adapter, "implementation_files", ()))]
    return {"adapter_id": adapter.adapter_id,
            "implementation_sha256": [sha256(p.read_bytes()) for p in files],
            "configuration": deepcopy(getattr(adapter, "configuration", {}))}


def _runtime_binding():
    base = Path(__file__).parent
    return {name: sha256((base / name).read_bytes()) for name in (
        "experiment_execution.py", "long_horizon_scientific_cycle.py", "resident_cognitive.py",
        "research_cycle.py", "schema.py")}


def _unique(rows, name):
    ids = [row[name] for row in rows]
    if not ids or any(not isinstance(x, str) or not x.strip() for x in ids) or len(set(ids)) != len(ids):
        raise ValueError(f"nonempty unique {name} required")
    return set(ids)


def _finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("finite numerical value required")
    return value


def freeze_protocol(contract, *, source_adapter, measurement_adapter, owner_id):
    from .research_cycle import AdaptiveResearchKernelOwner
    # Strict JSON round trip: no callables, arrays, NaN or executable expressions.
    c = json.loads(json.dumps(contract, allow_nan=False))
    if c.get("schema") != SCHEMA or not c.get("experiment_id"):
        raise ValueError("execution schema and experiment_id required")
    if c.get("evidence_mode") not in {"CONTROLLED_QUALIFICATION", "RETROSPECTIVE_REPLAY", "PROSPECTIVE_REQUEST"}:
        raise ValueError("explicit evidence_mode required")
    capability = AdaptiveResearchKernelOwner._source_capability_contract({"source_capability": c["source"]})
    if not capability["explicitly_declared"] or not capability["source_id"]:
        raise ValueError("explicit source capability required")
    if (source_adapter.source_class != capability["class"] or source_adapter.source_id != capability["source_id"]):
        raise ValueError("source adapter capability mismatch")
    for key, adapter in (("source_adapter", source_adapter), ("measurement_adapter", measurement_adapter)):
        if c[key] != adapter_binding(adapter):
            raise ValueError(f"{key.replace('_', ' ')} binding mismatch")
    for key in ("samples", "cases", "forms"):
        if not isinstance(c.get(key), list) or not all(isinstance(row, dict) for row in c[key]):
            raise ValueError(f"{key} must be a list of mappings")
    samples = _unique(c["samples"], "sample_id")
    cases = _unique(c["cases"], "case_id")
    _unique(c["forms"], "form_id")
    transport = c["transport"]
    if type(transport["max_retries"]) is not int or not 0 <= transport["max_retries"] <= 10:
        raise ValueError("retry budget must be between 0 and 10")
    if not 0 <= _finite(transport["backoff_seconds"]) <= 60:
        raise ValueError("invalid backoff")
    if type(transport["max_bytes_per_sample"]) is not int or transport["max_bytes_per_sample"] <= 0:
        raise ValueError("positive byte budget required")
    for sample in c["samples"]:
        allowed = {"sample_id", "request", "request_kind", "expected_sha256", "idempotency_key"}
        if set(sample) - allowed:
            raise ValueError("unexpected sample fields")
        kind = sample["request_kind"]
        if kind not in {"NATURAL_SAMPLE", "INTERVENTION"}:
            raise ValueError("unsupported sample request kind")
        flag = "supports_natural_sample_retrieval" if kind == "NATURAL_SAMPLE" else "supports_arbitrary_state_intervention"
        if not capability[flag]:
            raise ValueError("source capability prohibits requested action")
        if kind == "INTERVENTION" and transport["max_retries"] and not str(sample.get("idempotency_key", "")).strip():
            raise ValueError("retried intervention requires a frozen idempotency key")
        expected = sample.get("expected_sha256")
        if expected is not None and (len(expected) != 64 or any(x not in "0123456789abcdef" for x in expected)):
            raise ValueError("invalid expected SHA-256")
    if {case["sample_id"] for case in c["cases"]} != samples:
        raise ValueError("every sample must have cases; unknown sample referenced")
    for form in c["forms"]:
        if form["kind"] != "LINEAR_FEATURES" or form["case_id"] not in cases:
            raise ValueError("unsupported frozen form or unknown case")
        features = form["feature_ids"]
        if len(set(features)) != len(features) or any(not isinstance(x, str) or not x for x in features):
            raise ValueError("unique feature IDs required")
        if len(form["coefficients"]) != len(features) + 1:
            raise ValueError("frozen coefficient count mismatch")
        for value in form["coefficients"]:
            _finite(value)
    if {form["case_id"] for form in c["forms"]} != cases:
        raise ValueError("every case requires a frozen form")
    metric = c["metric"]
    if metric["name"] != "NRMSE_STD" or _finite(metric["threshold"]) < 0 or _finite(metric["minimum_std"]) <= 0:
        raise ValueError("unsupported metric or invalid gates")
    revision = c.get("theory_revision")
    if revision is not None:
        frozen = revision["frozen_round"]
        verify(frozen)
        if frozen["freeze_digest"] != digest_payload(frozen["frozen"]):
            raise ValueError("theory round freeze mismatch")
        selected = frozen["selected_experiment"]
        if not selected or selected not in frozen["frozen"]["frontier"] or selected["experiment_id"] != c["experiment_id"]:
            raise ValueError("execution and theory experiment mismatch")
        if set(revision["outcomes"]) != {"ALL_FORMS_PASS", "SOME_FORMS_FAIL"}:
            raise ValueError("complete predeclared outcome mapping required")
        if any(not isinstance(x, str) or not x for x in revision["outcomes"].values()):
            raise ValueError("categorical outcome labels required")
        if any(p.get("kind") != "categorical" for p in selected["predictions"].values()):
            raise ValueError("execution v1 requires categorical theory outcome predictions")
    # Adapters must validate metadata only here, without reading outcomes.
    blockers = list(source_adapter.preflight(deepcopy(c))) + list(measurement_adapter.preflight(deepcopy(c)))
    if not all(isinstance(row, dict) for row in blockers):
        raise ValueError("adapter preflight blockers must be mappings")
    blockers = [dict(row) for row in {digest_payload(row): row for row in blockers}.values()]
    return sealed({"schema": SCHEMA, "owner_id": owner_id,
                   "status": "EXECUTION_PROTOCOL_BLOCKED" if blockers else "EXECUTION_PROTOCOL_FROZEN",
                   "contract": c, "source_capability": capability, "blockers": blockers,
                   "runtime_binding": _runtime_binding(), "heldout_refit_allowed": False,
                   "scientific_promotion_allowed": False, "historical_freeze_authenticated": False})


def _write_atomic(path, data):
    if path.is_symlink():
        raise ValueError("symlink state file prohibited")
    fd, tmp = tempfile.mkstemp(prefix=".execution-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _write_json(path, value):
    _write_atomic(path, (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode())


def _read_json(path):
    if path.is_symlink():
        raise ValueError("symlink state file prohibited")
    value = json.loads(path.read_text())
    verify(value)
    return value


def acquire_evidence(frozen, *, adapter, state_dir, owner_id):
    """Checkpoint each declared acquisition unit; never retry corrupt evidence."""
    verify(frozen)
    c = frozen["contract"]
    if adapter_binding(adapter) != c["source_adapter"]:
        raise ValueError("source adapter binding mismatch")
    receipts, payloads = [], {}
    for sample in c["samples"]:
        key = digest_payload(sample)
        raw_path, receipt_path = state_dir / (key + ".bin"), state_dir / (key + ".json")
        if raw_path.is_symlink():
            raise ValueError("symlink evidence prohibited")
        if receipt_path.exists():
            receipt = _read_json(receipt_path)
            if (receipt["protocol_digest"] != frozen["digest"] or receipt["sample_digest"] != key
                    or receipt["adapter_binding"] != c["source_adapter"]):
                raise ValueError("checkpoint binding mismatch")
            if raw_path.stat().st_size > c["transport"]["max_bytes_per_sample"]:
                raise ValueError("evidence byte budget exceeded")
            data = raw_path.read_bytes()
            if sha256(data) != receipt["raw_sha256"]:
                raise ValueError("checkpoint evidence SHA-256 mismatch")
        else:
            if raw_path.exists():
                # A crash between raw and receipt writes is ambiguous: never refetch
                # an intervention or reinterpret an unreceipted response as fresh.
                raise ValueError("unreceipted evidence; explicit recovery required")
            pending = state_dir / (key + ".pending.json")
            if pending.exists() or pending.is_symlink():
                raise ValueError("interrupted acquisition; source-specific recovery required")
            _write_json(pending, sealed({"protocol_digest": frozen["digest"], "sample_digest": key}))
            budget = c["transport"]
            for attempt in range(budget["max_retries"] + 1):
                try:
                    data = adapter.acquire(
                        deepcopy(sample["request"]),
                        idempotency_key=sample.get("idempotency_key"),
                    )
                    break
                except TransientAcquisitionError:
                    # The adapter may classify a failure as transient only if replay
                    # is safe (e.g. retrieval, or idempotency-key-protected action).
                    if attempt == budget["max_retries"]:
                        pending.unlink()
                        raise
                    time.sleep(min(60, budget["backoff_seconds"] * 2 ** attempt))
            if not isinstance(data, bytes) or not data or len(data) > budget["max_bytes_per_sample"]:
                raise ValueError("invalid evidence bytes or byte budget exceeded")
            if sample.get("expected_sha256") and sha256(data) != sample["expected_sha256"]:
                raise ValueError("source evidence SHA-256 mismatch")
            receipt = sealed({"owner_id": owner_id, "protocol_digest": frozen["digest"],
                              "sample_id": sample["sample_id"], "sample_digest": key,
                              "adapter_binding": c["source_adapter"], "raw_sha256": sha256(data),
                              "byte_count": len(data), "source_authenticity_independently_verified": False})
            _write_atomic(raw_path, data)
            _write_json(receipt_path, receipt)
            pending.unlink()
        if sample.get("expected_sha256") and sha256(data) != sample["expected_sha256"]:
            raise ValueError("expected evidence SHA-256 mismatch")
        receipts.append(receipt)
        payloads[sample["sample_id"]] = data
    return receipts, payloads


def evaluate_frozen_predictions(contract, measurements, *, owner_id):
    expected = {case["case_id"] for case in contract["cases"]}
    if set(measurements) != expected:
        raise ValueError("measurement case coverage mismatch")
    rows = []
    metric = contract["metric"]
    for form in contract["forms"]:
        case = measurements[form["case_id"]]
        observed = np.asarray(case["observed"], dtype=float)
        if observed.ndim != 1 or len(observed) < 2 or not np.isfinite(observed).all():
            raise ValueError("finite one-dimensional observations required")
        prediction = np.full_like(observed, form["coefficients"][0])
        for feature, coefficient in zip(form["feature_ids"], form["coefficients"][1:]):
            values = np.asarray(case["features"][feature], dtype=float)
            if values.shape != observed.shape or not np.isfinite(values).all():
                raise ValueError("feature shape or finiteness mismatch")
            prediction += coefficient * values
        scale = float(np.std(observed))
        if not np.isfinite(prediction).all() or not math.isfinite(scale) or scale < metric["minimum_std"]:
            raise ValueError("undefined prediction or NRMSE normalization")
        error = float(np.sqrt(np.mean((observed - prediction) ** 2)) / scale)
        if not math.isfinite(error):
            raise ValueError("nonfinite NRMSE")
        rows.append({"form_id": form["form_id"], "case_id": form["case_id"],
                     "form_digest": digest_payload(form), "measurement_digest": digest_payload(case),
                     "prediction_digest": digest_payload(prediction.tolist()),
                     "n": len(observed), "nrmse": error, "passes_gate": error <= metric["threshold"]})
    return sealed({"owner_id": owner_id, "rows": rows,
                   "outcome": "ALL_FORMS_PASS" if all(x["passes_gate"] for x in rows) else "SOME_FORMS_FAIL",
                   "refit_performed": False, "scientific_promotion_allowed": False})


def execute_protocol(kernel, frozen, *, source_adapter, measurement_adapter, state_dir):
    """Existing long-horizon kernel delegates acquisition and revision to owners."""
    import fcntl
    from .resident_cognitive import TypedWorldActionAdapterOwner
    verify(frozen)
    if frozen["schema"] != SCHEMA or frozen["runtime_binding"] != _runtime_binding():
        raise ValueError("execution implementation differs from freeze")
    c = frozen["contract"]
    for key, adapter in (("source_adapter", source_adapter), ("measurement_adapter", measurement_adapter)):
        if c[key] != adapter_binding(adapter):
            raise ValueError(f"{key.replace('_', ' ')} binding mismatch")
    if frozen["status"] == "EXECUTION_PROTOCOL_BLOCKED":
        return sealed({"status": "EXECUTION_BLOCKED_PREFLIGHT", "protocol_digest": frozen["digest"],
                       "blockers": frozen["blockers"], "evidence_acquired": False,
                       "scientific_promotion_allowed": False})
    if frozen["status"] != "EXECUTION_PROTOCOL_FROZEN":
        raise ValueError("unqualified execution protocol")
    state = Path(state_dir).resolve()
    if state == kernel.root.resolve() or kernel.root.resolve() in state.parents:
        raise ValueError("execution state must be outside release tree")
    state.mkdir(parents=True, exist_ok=True)
    lock = state / ".execution.lock"
    if lock.is_symlink():
        raise ValueError("symlink lock prohibited")
    with lock.open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        path = state / "protocol.json"
        if path.exists() or path.is_symlink():
            if _read_json(path) != frozen:
                raise ValueError("state already bound to another protocol")
        else:
            _write_json(path, frozen)  # durable freeze precedes every adapter call
        acquisition = TypedWorldActionAdapterOwner()
        receipts, payloads = acquisition.acquire_frozen_evidence(frozen, adapter=source_adapter, state_dir=state)
        evidence_digest = digest_payload(receipts)
        result_path = state / "result.json"
        if result_path.exists() or result_path.is_symlink():
            result = _read_json(result_path)
            if result["protocol_digest"] != frozen["digest"] or result["evidence_digest"] != evidence_digest:
                raise ValueError("result binding mismatch")
            return result
        measurement_path = state / "measurements.json"
        if measurement_path.exists() or measurement_path.is_symlink():
            receipt = _read_json(measurement_path)
            if receipt["protocol_digest"] != frozen["digest"] or receipt["evidence_digest"] != evidence_digest:
                raise ValueError("measurement checkpoint binding mismatch")
            measurements = receipt["cases"]
        else:
            measurements = {}
            for sample in c["samples"]:
                cases = [x for x in c["cases"] if x["sample_id"] == sample["sample_id"]]
                # No coefficients or competing hypotheses are passed to adapter.
                values = measurement_adapter.measure(payloads[sample["sample_id"]], deepcopy(cases))
                if set(values) != {x["case_id"] for x in cases} or set(values) & set(measurements):
                    raise ValueError("adapter sample/case binding mismatch")
                measurements.update(values)
            receipt = sealed({"protocol_digest": frozen["digest"], "evidence_digest": evidence_digest,
                              "adapter_binding": c["measurement_adapter"], "cases": measurements})
            _write_json(measurement_path, receipt)
        verdict = kernel.observational_revision.evaluate_frozen_predictions(c, measurements)
        revision_contract = c.get("theory_revision")
        if revision_contract:
            round_ = revision_contract["frozen_round"]
            revision = kernel.absorb_observational_measurement(frozen_experiment=round_, measurement={
                "experiment_id": c["experiment_id"], "freeze_digest": round_["freeze_digest"],
                "value": revision_contract["outcomes"][verdict["outcome"]],
                "execution_protocol_digest": frozen["digest"], "evaluation_digest": verdict["digest"],
                "evidence_digest": evidence_digest})
        else:
            revision = {"status": "THEORY_REVISION_CONTRACT_REQUIRED"}
        result = sealed({"schema": SCHEMA, "status": "FROZEN_EXPERIMENT_EVALUATED",
                         "owner_id": kernel.observational_revision.owner_id,
                         "protocol_digest": frozen["digest"], "evidence_digest": evidence_digest,
                         "evidence_receipts": receipts, "measurement_digest": receipt["digest"],
                         "evaluation": verdict, "theory_revision": revision,
                         "stages": list(STAGES[:-1]) + ([STAGES[-1]] if revision_contract else []),
                         "evidence_mode": c["evidence_mode"], "scientific_promotion_allowed": False,
                         "historical_freeze_authenticated": False})
        _write_json(result_path, result)
        return result
