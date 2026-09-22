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
import math
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




class HierarchicalObservationalExperimentOwner:
    """Select a frozen discriminating experiment for a compiled hierarchical theory.

    Experiment models are frozen with the theory and contain explanation-specific
    predicted outcomes.  Selection uses only those predictions, declared costs and
    optional feasibility metadata; post-freeze measurements are never inspected.
    """
    owner_id = "HIERARCHICAL-OBSERVATIONAL-EXPERIMENT/1.0.0"

    @staticmethod
    def _pair_divergence(a: Mapping[str, Any], b: Mapping[str, Any]) -> float:
        ka, kb = str(a.get("kind", "categorical")), str(b.get("kind", "categorical"))
        if ka == kb == "categorical":
            return 0.0 if str(a.get("value")) == str(b.get("value")) else 1.0
        if ka == kb == "interval":
            alo, ahi = float(a["lo"]), float(a["hi"]); blo, bhi = float(b["lo"]), float(b["hi"])
            union = max(ahi, bhi) - min(alo, blo)
            overlap = max(0.0, min(ahi, bhi) - max(alo, blo))
            return 0.0 if union <= 0 else max(0.0, min(1.0, 1.0 - overlap / union))
        if ka == kb == "gaussian":
            ma, sa = float(a["mean"]), max(float(a.get("sigma", 1.0)), 1e-12)
            mb, sb = float(b["mean"]), max(float(b.get("sigma", 1.0)), 1e-12)
            z = abs(ma-mb) / ((sa*sa+sb*sb) ** 0.5)
            return min(1.0, z / 3.0)
        return 0.0

    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": self.owner_id,
            "input": "COMPILED_HIERARCHICAL_THEORY_WITH_FROZEN_EXPERIMENTAL_MODELS",
            "selection": "MAXIMIZE_MIN_PAIRWISE_DIVERGENCE_THEN_MEAN_DIVERGENCE_PER_COST",
            "measurement_visible_during_selection": False,
            "heldout_refit_allowed": False,
            "no_experiment_model": "BLOCKED_NEEDS_EXPERIMENTAL_MODELS",
        }

    def freeze(self, *, theory: Mapping[str, Any], cost_budget: float) -> Mapping[str, Any]:
        if theory.get("digest") != digest_payload({k: v for k, v in theory.items() if k != "digest"}):
            raise ValueError("theory digest mismatch")
        if not math.isfinite(float(cost_budget)) or float(cost_budget) <= 0:
            raise ValueError("cost budget must be finite and positive")
        if theory.get("schema") != "phi-hierarchical-observational-theory/v1" or not str(theory.get("status", "")).startswith("HIERARCHICAL_THEORY_"):
            return _with_digest({"schema": SCHEMA, "owner_id": self.owner_id, "status": "OBSERVATIONAL_EXPERIMENT_BLOCKED_UNQUALIFIED_THEORY"})
        explanation_ids = [str(x.get("id")) for x in theory.get("competing_explanations", ()) if str(x.get("id", "")).strip()]
        models = [dict(x) for x in theory.get("experimental_models", ())]
        if len(set(explanation_ids)) != len(explanation_ids):
            raise ValueError("duplicate explanation ids")
        if len(explanation_ids) < 2 or not models:
            return _with_digest({"schema": SCHEMA, "owner_id": self.owner_id, "status": "BLOCKED_NEEDS_EXPERIMENTAL_MODELS", "explanation_ids": explanation_ids})
        rows=[]
        experiment_ids = set()
        for model in models:
            preds=dict(model.get("predictions", {})); cost=float(model.get("cost", 1.0)); feasible=bool(model.get("feasible", True))
            eid = str(model.get("experiment_id", "")).strip()
            if not eid or eid in experiment_ids or not str(model.get("observable", "")).strip():
                raise ValueError("unique experiment id and observable required")
            experiment_ids.add(eid)
            if set(preds) != set(explanation_ids):
                return _with_digest({"schema": SCHEMA, "owner_id": self.owner_id,
                    "status": "BLOCKED_INCOMPLETE_EXPERIMENT_PREDICTIONS",
                    "experiment_id": eid,
                    "missing_explanation_ids": sorted(set(explanation_ids) - set(preds)),
                    "unknown_explanation_ids": sorted(set(preds) - set(explanation_ids)),
                    "selected_experiment": None})
            if not math.isfinite(cost) or cost <= 0:
                raise ValueError("positive finite cost required")
            for pred in preds.values():
                kind = pred.get("kind", "categorical")
                if kind == "categorical":
                    if pred.get("value") is None:
                        raise ValueError("categorical prediction requires value")
                elif kind == "interval":
                    lo, hi = float(pred["lo"]), float(pred["hi"])
                    if not (math.isfinite(lo) and math.isfinite(hi) and lo <= hi):
                        raise ValueError("invalid prediction interval")
                elif kind == "gaussian":
                    if not math.isfinite(float(pred["mean"])) or not math.isfinite(float(pred.get("sigma", 1))) or float(pred.get("sigma", 1)) <= 0:
                        raise ValueError("invalid gaussian prediction")
                else:
                    raise ValueError("unsupported prediction kind")
            pair=[]
            for i,a in enumerate(explanation_ids):
                for b in explanation_ids[i+1:]:
                    if a in preds and b in preds:
                        pair.append(self._pair_divergence(dict(preds[a]), dict(preds[b])))
            min_div=min(pair) if pair else 0.0; mean_div=sum(pair)/len(pair) if pair else 0.0
            core={
                "experiment_id":str(model.get("experiment_id", "")), "observable":str(model.get("observable", "")),
                "cost":cost, "feasible":feasible, "predictions":preds,
                "min_pairwise_divergence":min_div, "mean_pairwise_divergence":mean_div,
                "fully_distinguishes_all_explanations": bool(pair) and min_div>0.0,
                "utility": (min_div + 0.25*mean_div) / max(cost, 1e-12) if feasible and cost<=float(cost_budget) else -1.0,
            }
            rows.append(core)
        admissible=[r for r in rows if r["feasible"] and r["cost"]<=float(cost_budget) and r["mean_pairwise_divergence"]>0]
        selected=sorted(admissible, key=lambda r:(-r["utility"], -r["min_pairwise_divergence"], r["cost"], r["experiment_id"]))[0] if admissible else None
        frozen={
            "theory_id":theory.get("theory_id"), "theory_digest":theory.get("digest"), "evidence_digest":theory.get("evidence_digest"),
            "explanation_ids":explanation_ids, "cost_budget":float(cost_budget), "frontier":rows,
            "selection_rule":"MAX_MIN_DIVERGENCE_THEN_MEAN_DIVERGENCE_PER_COST",
            "measurement_inspected_before_selection":False,
            "selected_experiment_id": selected["experiment_id"] if selected else None,
            "compatibility_floor": 0.01,
        }
        freeze_digest=digest_payload(frozen)
        return _with_digest({
            "schema":SCHEMA,"owner_id":self.owner_id,
            "status":"HIERARCHICAL_OBSERVATIONAL_EXPERIMENT_FROZEN" if selected else "NO_DISCRIMINATING_OBSERVATIONAL_EXPERIMENT_WITHIN_BUDGET",
            "freeze_digest":freeze_digest,"frozen":frozen,"selected_experiment":selected,
            "claim_boundary":{"selection_is_world_evidence":False,"measurement_inspected_before_selection":False,"scientific_promotion_allowed":False},
        })


class HierarchicalObservationalTheoryRevisionOwner:
    owner_id = "HIERARCHICAL-OBSERVATIONAL-THEORY-REVISION/1.0.0"

    @staticmethod
    def _likelihood(pred: Mapping[str, Any], measurement: Mapping[str, Any]) -> float:
        kind=str(pred.get("kind", "categorical")); obs=measurement.get("value")
        if kind == "categorical": return 0.99 if str(obs)==str(pred.get("value")) else 0.01
        try: x=float(obs)
        except Exception: return 0.0
        if kind == "interval": return 0.99 if float(pred["lo"]) <= x <= float(pred["hi"]) else 0.01
        if kind == "gaussian":
            import math
            mu=float(pred["mean"]); sigma=max(float(pred.get("sigma",1.0)),1e-12)
            z=(x-mu)/sigma
            return max(1e-12, math.exp(-0.5*z*z))
        return 0.0

    def revise(self, *, frozen_experiment: Mapping[str, Any], measurement: Mapping[str, Any]) -> Mapping[str, Any]:
        frozen = frozen_experiment.get("frozen", {})
        if (frozen_experiment.get("digest") != digest_payload({k: v for k, v in frozen_experiment.items() if k != "digest"})
                or frozen_experiment.get("freeze_digest") != digest_payload(frozen)):
            raise ValueError("frozen experiment digest mismatch")
        selected=frozen_experiment.get("selected_experiment")
        if not isinstance(selected, Mapping):
            return _with_digest({"schema":SCHEMA,"owner_id":self.owner_id,"status":"OBSERVATIONAL_REVISION_BLOCKED_NO_SELECTED_EXPERIMENT"})
        if measurement.get("experiment_id") != selected.get("experiment_id") or measurement.get("freeze_digest") != frozen_experiment.get("freeze_digest"):
            return _with_digest({"schema":SCHEMA,"owner_id":self.owner_id,"status":"OBSERVATIONAL_REVISION_BLOCKED_PROTOCOL_MISMATCH"})
        if selected.get("experiment_id") != frozen.get("selected_experiment_id") or selected not in frozen.get("frontier", ()):
            raise ValueError("selected experiment is not bound to frozen portfolio")
        if measurement.get("value") is None:
            raise ValueError("measurement value required")
        value = measurement["value"]
        if isinstance(value, (int, float)) and not math.isfinite(float(value)):
            raise ValueError("nonfinite measurement")
        preds=dict(selected.get("predictions", {})); ids=list(frozen_experiment.get("frozen",{}).get("explanation_ids",()))
        raw={i:self._likelihood(dict(preds.get(i,{})),measurement) for i in ids}; total=sum(raw.values())
        post={i:(raw[i]/total if total>0 else 0.0) for i in ids}
        ordered=sorted(post.items(), key=lambda kv:(-kv[1],kv[0])); survivors=[i for i,p in ordered if p>=0.05]
        incompatible = max(raw.values(), default=0.0) <= float(frozen["compatibility_floor"])
        if incompatible:
            survivors = []
            post = {i: 0.0 for i in ids}
        elif not survivors:
            survivors = [i for i in ids if raw[i] > float(frozen["compatibility_floor"])]
        if incompatible or not survivors: status="REPRESENTATION_EXPANSION_REQUIRED"
        elif ordered and ordered[0][1]>=0.95: status="HIERARCHICAL_EXPLANATION_IDENTIFIED_POSTFREEZE"
        elif len(survivors)<len(ids): status="HIERARCHICAL_EXPLANATION_SET_REDUCED_POSTFREEZE"
        else: status="HIERARCHICAL_THEORY_EVIDENCE_UPDATED"
        return _with_digest({
            "schema":SCHEMA,"owner_id":self.owner_id,"status":status,"experiment_id":selected.get("experiment_id"),
            "measurement":dict(measurement),"likelihoods":raw,"posterior_weights":post,"surviving_explanation_ids":survivors,
            "leading_explanation_id":ordered[0][0] if ordered and survivors else None,
            "weights_are_calibrated_bayesian_posteriors":False,
            "representation_expansion_required":status=="REPRESENTATION_EXPANSION_REQUIRED",
            "claim_boundary":{"postfreeze_evidence_reused_for_experiment_selection":False,"posterior_is_world_truth":False,"scientific_promotion_allowed":False},
        })

class LongHorizonBlindScientificCycleKernel:
    def __init__(self, root: str | Path, *, state_path: str | Path | None = None) -> None:
        self.root = Path(root)
        self.experiments = AutomaticDiscriminatingExperimentKernel(self.root)
        self.knowledge = KnowledgeEvolutionKernel(self.root)
        self.revision = PostfreezeTheoryRevisionOwner()
        self.observational_experiments = HierarchicalObservationalExperimentOwner()
        self.observational_revision = HierarchicalObservationalTheoryRevisionOwner()
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
                "hierarchical_observational_experiment": self.observational_experiments.owner_id,
                "hierarchical_observational_revision": self.observational_revision.owner_id,
            },
            "blindness": {
                "hidden_truth_parameter_in_solver_api": False,
                "hidden_truth_may_be_selected_after_freeze": True,
                "internet_prefreeze": "FORBIDDEN",
                "observation_outside_frozen_predictions": "REPRESENTATION_EXPANSION_REQUIRED",
            },
            "hierarchical_observational_cycle": {
                "supported": True,
                "pipeline": "COMPILED_HIERARCHICAL_THEORY->FROZEN_EXPERIMENT_PORTFOLIO->POSTFREEZE_EVIDENCE->EXPLANATION_REVISION",
                "measurement_visible_during_selection": False,
                "heldout_refit_allowed": False,
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


    def freeze_observational_round(self, *, theory: Mapping[str, Any], cost_budget: float) -> Mapping[str, Any]:
        return self.observational_experiments.freeze(theory=theory, cost_budget=cost_budget)

    def absorb_observational_measurement(self, *, frozen_experiment: Mapping[str, Any], measurement: Mapping[str, Any]) -> Mapping[str, Any]:
        return self.observational_revision.revise(frozen_experiment=frozen_experiment, measurement=measurement)

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
