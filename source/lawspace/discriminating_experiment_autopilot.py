"""Automatic discriminating-experiment design and measurement-request queue.

This owner orchestrates existing discriminating-experiment owners. It never
observes the world result before selection, never promotes a theory, and never
mutates a scientific-law or canonical-axis registry. Live request state is kept
outside the sealed release tree through ``LawSpaceRuntime.external_state_path``.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from .execution_policy import load_execution_policy, require_action
from .runtime import LawSpaceRuntime
from .schema import digest_payload

OWNER_ID = "DISCRIMINATING-EXPERIMENT-AUTOPILOT/1.0.0"
SCHEMA = "phi-discriminating-experiment-autopilot/v1"
QUEUE_SCHEMA = "phi-discriminating-measurement-request-queue/v1"


def _with_digest(payload: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    out["digest"] = digest_payload({k: v for k, v in out.items() if k != "digest"})
    return out


class DiscriminatingExperimentAutopilotOwner:
    owner_id = OWNER_ID

    def __init__(self, root: str | Path, *, kernel: Any | None = None) -> None:
        self.root = Path(root)
        self.runtime = object.__new__(LawSpaceRuntime)
        self.runtime.root = self.root
        if kernel is None:
            from .discriminating_experiment import AutomaticDiscriminatingExperimentKernel
            kernel = AutomaticDiscriminatingExperimentKernel(self.root)
        self.kernel = kernel

    def _policy(self) -> Mapping[str, Any]:
        return load_execution_policy(self.root)

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner_id": self.owner_id,
            "pipeline": [
                "COMPILE_OR_RECEIVE_COMPETING_THEORIES",
                "FREEZE_FRONTIER",
                "SELECT_DISCRIMINATING_EXPERIMENT",
                "EMIT_MEASUREMENT_REQUEST",
            ],
            "world_result_used_before_selection": False,
            "theory_promotion_allowed": False,
            "canonical_registry_mutation_allowed": False,
            "live_queue_inside_sealed_release": False,
        }
        return _with_digest(payload)

    def design(
        self,
        *,
        question: str,
        candidate_theory: Mapping[str, Any],
        baseline_theories: Sequence[Mapping[str, Any]],
        cost_budget: float,
    ) -> Mapping[str, Any]:
        require_action(self._policy(), "DISCRIMINATING_EXPERIMENT_AUTOPILOT")
        result = dict(self.kernel.design(
            question=str(question),
            candidate_theory=dict(candidate_theory),
            baseline_theories=tuple(dict(x) for x in baseline_theories),
            cost_budget=float(cost_budget),
        ))
        selection = dict(result.get("selection") or {})
        bridge = dict(result.get("attestation_bridge") or {})
        protocol = bridge.get("measurement_protocol")
        ready = (
            selection.get("status") == "DISCRIMINATING_EXPERIMENT_SELECTED"
            and isinstance(protocol, Mapping)
        )
        request = None
        if ready:
            core = {
                "measurement_protocol": dict(protocol),
                "frontier_freeze_digest": selection.get("frontier_freeze_digest"),
                "selection_digest": selection.get("digest"),
                "candidate_theory_digest": candidate_theory.get("digest"),
                "baseline_theory_digests": [x.get("digest") for x in baseline_theories],
                "question": str(question),
            }
            request = {
                "schema": "phi-measurement-request/v1",
                "request_id": "MR-" + digest_payload(core)[:24].upper(),
                **core,
                "status": "MEASUREMENT_REQUEST_READY",
                "world_result_observed": False,
                "theory_promotion_allowed": False,
                "canonical_registry_mutation_allowed": False,
            }
            request["digest"] = digest_payload(request)
        status = (
            "MEASUREMENT_REQUEST_READY"
            if ready
            else str(selection.get("status") or result.get("status") or "MEASUREMENT_REQUEST_NOT_AVAILABLE")
        )
        return _with_digest({
            "schema": SCHEMA,
            "owner_id": self.owner_id,
            "status": status,
            "design_receipt": result,
            "measurement_request": request,
            "mutation_performed": False,
            "claim_boundary": {
                "experiment_selection_is_world_result": False,
                "measurement_request_is_world_evidence": False,
                "theory_promotion_allowed": False,
                "scientific_law_promoted": False,
                "canonical_registry_mutated": False,
            },
        })

    def _queue_path(self) -> Path:
        return self.runtime.external_state_path("discriminating_measurement_requests")

    def queue(self, design_receipt: Mapping[str, Any]) -> Mapping[str, Any]:
        require_action(self._policy(), "DISCRIMINATING_EXPERIMENT_AUTOPILOT")
        request = design_receipt.get("measurement_request")
        if not isinstance(request, Mapping) or design_receipt.get("status") != "MEASUREMENT_REQUEST_READY":
            return _with_digest({
                "schema": QUEUE_SCHEMA,
                "owner_id": self.owner_id,
                "status": "MEASUREMENT_REQUEST_QUEUE_BLOCKED_NO_READY_REQUEST",
                "queued": False,
                "canonical_registry_mutated": False,
            })
        request = dict(request)
        embedded = str(request.get("digest", ""))
        if not embedded or embedded != digest_payload({k: v for k, v in request.items() if k != "digest"}):
            raise ValueError("measurement request digest mismatch")
        path = self._queue_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.is_file():
            doc = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(doc, Mapping) or doc.get("schema") != QUEUE_SCHEMA:
                raise ValueError("invalid measurement-request queue")
            rows = [dict(x) for x in doc.get("requests", ())]
        else:
            rows = []
        if any(str(x.get("request_id")) == str(request.get("request_id")) for x in rows):
            return _with_digest({
                "schema": QUEUE_SCHEMA,
                "owner_id": self.owner_id,
                "status": "IDEMPOTENT_MEASUREMENT_REQUEST_ALREADY_QUEUED",
                "queued": True,
                "request_id": request.get("request_id"),
                "queue_path": str(path),
                "canonical_registry_mutated": False,
            })
        rows.append(request)
        body = {
            "schema": QUEUE_SCHEMA,
            "owner_id": self.owner_id,
            "requests": rows,
            "request_count": len(rows),
            "mutable_state_inside_sealed_tree": False,
            "scientific_law_promoted": False,
        }
        body["digest"] = digest_payload(body)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(body, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)
        return _with_digest({
            "schema": QUEUE_SCHEMA,
            "owner_id": self.owner_id,
            "status": "MEASUREMENT_REQUEST_QUEUED",
            "queued": True,
            "request_id": request.get("request_id"),
            "queue_path": str(path),
            "queue_digest": body["digest"],
            "canonical_registry_mutated": False,
            "theory_promotion_allowed": False,
        })

    def queue_state(self) -> Mapping[str, Any]:
        path = self._queue_path()
        if not path.is_file():
            return _with_digest({
                "schema": QUEUE_SCHEMA,
                "owner_id": self.owner_id,
                "status": "MEASUREMENT_REQUEST_QUEUE_EMPTY",
                "request_count": 0,
                "requests": [],
                "queue_path": str(path),
            })
        doc = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(doc, Mapping) or doc.get("schema") != QUEUE_SCHEMA:
            raise ValueError("invalid measurement-request queue")
        embedded = str(doc.get("digest", ""))
        core = {k: v for k, v in doc.items() if k != "digest"}
        if embedded != digest_payload(core):
            raise ValueError("measurement-request queue digest mismatch")
        return {**dict(doc), "queue_path": str(path)}
