"""Long-horizon blind scientific cycle over the existing Phi owners.

This module does not implement another scientific solver. It orchestrates the
already-authoritative discriminating-experiment, theory-runtime, world-
attestation and ontology/lifecycle owners under a persistent, digest-bound
research session. Hidden-world truth is deliberately absent from the public
solver API. Post-freeze observations may demote frozen theories; observations
outside the frozen prediction set require representation expansion rather than
nearest-theory guessing.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from .discriminating_experiment import AutomaticDiscriminatingExperimentKernel
from .knowledge_evolution import KnowledgeEvolutionKernel
from .schema import digest_payload

SCHEMA = "phi-long-horizon-blind-scientific-cycle/v1"
KERNEL_OWNER_ID = "PHI-LONG-HORIZON-BLIND-SCIENTIFIC-CYCLE/1.0.0"
SESSION_OWNER_ID = "LONG-HORIZON-SCIENTIFIC-SESSION-LEDGER/1.0.0"
REVISION_OWNER_ID = "POSTFREEZE-THEORY-REVISION/1.0.0"
RELEASE = "10.7.0"


def _with_digest(payload: dict[str, Any]) -> dict[str, Any]:
    payload["digest"] = digest_payload(payload)
    return payload


def _state_digest(state: Mapping[str, Any]) -> str:
    return digest_payload({k: v for k, v in state.items() if k != "state_digest"})


class LongHorizonSessionLedgerOwner:
    owner_id = SESSION_OWNER_ID
    max_transition_receipts = 256

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def empty(self) -> dict[str, Any]:
        state = {
            "schema": "phi-long-horizon-session-state/v1",
            "owner_id": self.owner_id,
            "release": RELEASE,
            "heartbeat_count": 0,
            "epoch_count": 0,
            "completed_epoch_count": 0,
            "representation_expansion_count": 0,
            "theory_demotions": {},
            "identified_theories": [],
            "measurement_receipts": [],
            "transitions": [],
        }
        state["state_digest"] = _state_digest(state)
        return state

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return self.empty()
        state = json.loads(self.path.read_text(encoding="utf-8"))
        if state.get("state_digest") != _state_digest(state):
            raise ValueError("long-horizon state digest mismatch")
        return state

    def commit(self, state: Mapping[str, Any]) -> Mapping[str, Any]:
        payload = dict(state)
        payload["transitions"] = list(payload.get("transitions", ())) [-self.max_transition_receipts:]
        payload["measurement_receipts"] = list(payload.get("measurement_receipts", ())) [-self.max_transition_receipts:]
        payload["state_digest"] = _state_digest(payload)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, self.path)
        return _with_digest({
            "owner_id": self.owner_id,
            "status": "LONG_HORIZON_SESSION_COMMITTED",
            "heartbeat_count": payload["heartbeat_count"],
            "epoch_count": payload["epoch_count"],
            "completed_epoch_count": payload["completed_epoch_count"],
            "state_digest": payload["state_digest"],
        })


class PostfreezeTheoryRevisionOwner:
    owner_id = REVISION_OWNER_ID

    def revise(
        self,
        *,
        epoch_freeze: Mapping[str, Any],
        measurement: Mapping[str, Any],
        active_theory_ids: Sequence[str],
    ) -> Mapping[str, Any]:
        selection = epoch_freeze.get("selection", {})
        selected = selection.get("selected_experiment") if isinstance(selection, Mapping) else None
        if not isinstance(selected, Mapping):
            return _with_digest({
                "schema": SCHEMA, "owner_id": self.owner_id,
                "status": "THEORY_REVISION_BLOCKED_NO_SELECTED_EXPERIMENT",
                "surviving_theory_ids": list(active_theory_ids),
            })
        if measurement.get("experiment_id") != selected.get("experiment_id"):
            return _with_digest({
                "schema": SCHEMA, "owner_id": self.owner_id,
                "status": "THEORY_REVISION_BLOCKED_PROTOCOL_MISMATCH",
                "surviving_theory_ids": list(active_theory_ids),
            })
        freeze_digest = epoch_freeze.get("frontier", {}).get("freeze_digest")
        if measurement.get("frontier_freeze_digest") != freeze_digest:
            return _with_digest({
                "schema": SCHEMA, "owner_id": self.owner_id,
                "status": "THEORY_REVISION_BLOCKED_FREEZE_DIGEST_MISMATCH",
                "surviving_theory_ids": list(active_theory_ids),
            })
        observation = str(measurement.get("observation", ""))
        predictions = [str(selected.get("candidate_final_observation", ""))] + [str(x) for x in selected.get("baseline_final_observations", ())]
        theory_ids = list(active_theory_ids)
        if len(predictions) != len(theory_ids):
            return _with_digest({
                "schema": SCHEMA, "owner_id": self.owner_id,
                "status": "THEORY_REVISION_BLOCKED_THEORY_PREDICTION_CARDINALITY_MISMATCH",
                "surviving_theory_ids": theory_ids,
            })
        survivors = [tid for tid, pred in zip(theory_ids, predictions) if pred == observation]
        demoted = [tid for tid in theory_ids if tid not in survivors]
        if not survivors:
            status = "REPRESENTATION_EXPANSION_REQUIRED"
        elif len(survivors) == 1:
            status = "THEORY_IDENTIFIED_POSTFREEZE"
        else:
            status = "THEORY_SET_REDUCED_POSTFREEZE"
        return _with_digest({
            "schema": SCHEMA,
            "owner_id": self.owner_id,
            "status": status,
            "experiment_id": selected.get("experiment_id"),
            "observation": observation,
            "surviving_theory_ids": survivors,
            "demoted_theory_ids": demoted,
            "representation_expansion_required": status == "REPRESENTATION_EXPANSION_REQUIRED",
            "claim_boundary": {
                "nearest_theory_guessing_allowed": False,
                "single_synthetic_measurement_is_world_confirmation": False,
                "theory_world_novelty_established": False,
            },
        })


class LongHorizonBlindScientificCycleKernel:
    def __init__(self, root: str | Path, *, state_path: str | Path | None = None) -> None:
        self.root = Path(root)
        self.experiments = AutomaticDiscriminatingExperimentKernel(self.root)
        self.knowledge = KnowledgeEvolutionKernel(self.root)
        self.revision = PostfreezeTheoryRevisionOwner()
        self.ledger = LongHorizonSessionLedgerOwner(state_path or self.root / "state" / "phi_long_horizon_session.json")

    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": KERNEL_OWNER_ID,
            "schema": SCHEMA,
            "pipeline": "FREEZE_THEORIES->INTERNAL_PHI_EXPERIMENT_SEARCH->POSTFREEZE_MEASUREMENT->THEORY_REVISION->ATTESTATION->REPEAT",
            "owners_reused": {
                "discriminating_experiment": "PHI-AUTOMATIC-DISCRIMINATING-EXPERIMENT/1.0.0",
                "world_attestation": "WORLD-ATTESTATION/1.0.0",
                "session_ledger": SESSION_OWNER_ID,
                "revision": REVISION_OWNER_ID,
            },
            "blindness": {
                "hidden_truth_parameter_in_solver_api": False,
                "hidden_truth_may_be_selected_after_freeze": True,
                "internet_prefreeze": "FORBIDDEN",
                "observation_outside_frozen_predictions": "REPRESENTATION_EXPANSION_REQUIRED",
            },
            "long_horizon": {
                "persistent_state": True,
                "bounded_transition_receipts": self.ledger.max_transition_receipts,
                "wrong_theory_demotion": True,
                "repeated_epochs": True,
            },
            "claim_boundary": {
                "synthetic_blind_cycle_is_world_discovery": False,
                "qualification_measurement_is_world_attestation": False,
                "agi_demonstrated": False,
            },
            "roadmap_dependency": {
                "previous": "PHI-AUTOMATIC-DISCRIMINATING-EXPERIMENT/1.0.0",
                "next": "PROSPECTIVE-EXTERNAL-SCIENTIFIC-VALIDATION",
            },
        }

    def freeze_round(
        self,
        *,
        question: str,
        active_theories: Sequence[Mapping[str, Any]],
        cost_budget: float,
    ) -> Mapping[str, Any]:
        theories = [dict(x) for x in active_theories]
        if len(theories) < 2:
            return _with_digest({"schema": SCHEMA, "owner_id": KERNEL_OWNER_ID, "status": "ROUND_FREEZE_BLOCKED_NEEDS_COMPETING_THEORIES"})
        design = self.experiments.design(
            question=question,
            candidate_theory=theories[0],
            baseline_theories=theories[1:],
            cost_budget=cost_budget,
        )
        theory_ids = [str(x.get("executable_id", "")) for x in theories]
        payload = {
            "schema": SCHEMA,
            "owner_id": KERNEL_OWNER_ID,
            "status": "LONG_HORIZON_ROUND_FROZEN" if design.get("status") == "DISCRIMINATING_EXPERIMENT_SELECTED" else str(design.get("status")),
            "active_theory_ids": theory_ids,
            "design": design,
            "frontier": design.get("frontier"),
            "selection": design.get("selection"),
            "attestation_bridge": design.get("attestation_bridge"),
            "hidden_truth_accessed": False,
            "internet_used_prefreeze": False,
        }
        return _with_digest(payload)

    def absorb_measurement(
        self,
        *,
        epoch_freeze: Mapping[str, Any],
        measurement: Mapping[str, Any],
        environment_id: str,
        persist: bool = True,
    ) -> Mapping[str, Any]:
        revision = self.revision.revise(
            epoch_freeze=epoch_freeze,
            measurement=measurement,
            active_theory_ids=epoch_freeze.get("active_theory_ids", ()),
        )
        attestation = self.knowledge.world.attest(
            verification_bundles=(),
            measurements=({
                "measurement_id": str(measurement.get("measurement_id", "")),
                "observable_id": "LONG_HORIZON_FINAL_OBSERVATION",
                "environment_id": str(environment_id),
                "measurement_owner": str(measurement.get("measurement_owner", "QUALIFICATION-HIDDEN-WORLD-EVALUATOR")),
                "protocol_digest": str(measurement.get("protocol_digest", "")),
                "data_digest": str(measurement.get("data_digest", "")),
                "uncertainty": measurement.get("uncertainty", 0.0),
            },),
            qualification_mode=True,
        )
        state = self.ledger.load()
        state["heartbeat_count"] += 1
        transition = {
            "heartbeat": state["heartbeat_count"],
            "environment_id": str(environment_id),
            "epoch_freeze_digest": epoch_freeze.get("digest"),
            "measurement_digest": measurement.get("digest"),
            "revision_digest": revision.get("digest"),
            "revision_status": revision.get("status"),
        }
        state["transitions"].append(transition)
        state["measurement_receipts"].append(dict(measurement))
        demotions = dict(state.get("theory_demotions", {}))
        for tid in revision.get("demoted_theory_ids", ()):
            demotions[tid] = int(demotions.get(tid, 0)) + 1
        state["theory_demotions"] = demotions
        if revision.get("status") == "THEORY_IDENTIFIED_POSTFREEZE":
            state["identified_theories"].append(revision.get("surviving_theory_ids", [None])[0])
        if revision.get("status") == "REPRESENTATION_EXPANSION_REQUIRED":
            state["representation_expansion_count"] += 1
        commit = self.ledger.commit(state) if persist else {"status": "NOT_PERSISTED_QUALIFICATION_ONLY"}
        return _with_digest({
            "schema": SCHEMA,
            "owner_id": KERNEL_OWNER_ID,
            "status": revision.get("status"),
            "revision": revision,
            "attestation": attestation,
            "state_commit": commit,
            "claim_boundary": {
                "qualification_measurement_promotes_world_theory": False,
                "attestation_world_ready": attestation.get("world_ready") is True,
            },
        })

    def pulse(self, status: str = "RESIDENT_HEARTBEAT") -> Mapping[str, Any]:
        state = self.ledger.load()
        state["heartbeat_count"] += 1
        state["transitions"].append({"heartbeat": state["heartbeat_count"], "status": str(status)})
        return self.ledger.commit(state)

    def mark_epoch_complete(self) -> Mapping[str, Any]:
        state = self.ledger.load()
        state["heartbeat_count"] += 1
        state["epoch_count"] += 1
        state["completed_epoch_count"] += 1
        state["transitions"].append({"heartbeat": state["heartbeat_count"], "status": "EPOCH_COMPLETED", "epoch": state["epoch_count"]})
        return self.ledger.commit(state)
