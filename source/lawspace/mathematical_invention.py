"""Φ-Mathematical Invention Kernel.

This owner does not choose a named representation from a catalogue.  It turns a
frozen internal Φ-space research region plus falsification evidence into a
minimal generated algebraic signature, discovers exact finite morphisms between
generated objects, and searches parameter directions in which a generated
family has a controlled limit.

Qualification demonstrates mechanism only.  It does not claim that any
synthetic primitive is mathematically novel in the world.
"""
from __future__ import annotations

import itertools
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .candidates import CandidateGenerationPipeline, DirectedResearchQuery
from .runtime import LawSpaceRuntime
from .schema import canonical_json, digest_payload

KERNEL_OWNER_ID = "PHI-MATHEMATICAL-INVENTION-KERNEL/1.0.0"
UNKNOWN_OWNER_ID = "UNKNOWN-UNKNOWN-REPRESENTATION-TYPE-DISCOVERY/1.0.0"
PRIMITIVE_OWNER_ID = "PRIMITIVE-SYNTHESIS/1.0.0"
MORPHISM_OWNER_ID = "MORPHISM-DISCOVERY/1.0.0"
LIMIT_OWNER_ID = "CONTROLLED-LIMIT-ENGINE/1.0.0"
SCHEMA = "phi-mathematical-invention-kernel/v1"


def _digest(payload: Mapping[str, Any]) -> str:
    return digest_payload(dict(payload))


def _with_digest(payload: dict[str, Any]) -> dict[str, Any]:
    payload["digest"] = _digest(payload)
    return payload


class UnknownUnknownRepresentationOwner:
    """Diagnose a missing *kind* of representation from independent failures.

    This layer does not name a known method.  It emits required algebraic
    capabilities/operation arities and a frozen provenance receipt that the
    primitive synthesizer must satisfy.
    """

    def __init__(self, runtime: LawSpaceRuntime) -> None:
        self.runtime = runtime

    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": UNKNOWN_OWNER_ID,
            "candidate_source": "INTERNAL_OWNER_CONNECTED_PHI_SPACE_ONLY",
            "required_evidence_modes": (
                "residual", "latent", "causal", "counterfactual", "cross_domain_bridge", "operator_probe"
            ),
            "internet_prefreeze": "FORBIDDEN",
            "output": "GENERATED_ALGEBRAIC_SIGNATURE_OBLIGATIONS_NOT_NAMED_METHOD",
        }

    def discover(
        self,
        *,
        question: str,
        evidence_rows: Sequence[Mapping[str, Any]],
        seed_owner_ids: Sequence[str] = (
            "FND-01", "FND-11", "FND-12", "STRUCTURAL-IDENTIFIABILITY-EQUIVALENCE"
        ),
    ) -> Mapping[str, Any]:
        if not evidence_rows:
            return _with_digest({
                "schema": SCHEMA,
                "owner_id": UNKNOWN_OWNER_ID,
                "status": "UNKNOWN_UNKNOWN_INSUFFICIENT_EVIDENCE",
                "obligations": {},
                "claim_boundary": {"new_representation_type_established": False},
            })
        pipeline = CandidateGenerationPipeline(self.runtime.catalog, self.runtime.bridges)
        scan = pipeline.directed_research(DirectedResearchQuery(
            question=question,
            seed_owner_ids=tuple(seed_owner_ids),
            discovery_mode="BLIND_PRIMITIVE_FIREWALL",
            include_all_connected_owners=False,
        ))
        modes: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for row in evidence_rows:
            mode = str(row.get("mode", "")).strip().lower()
            if mode in {"residual", "latent", "causal", "counterfactual", "cross_domain_bridge", "operator_probe"}:
                modes[mode].append(row)
        independent_envs = {str(r.get("environment_id", "")) for r in evidence_rows if r.get("environment_id")}
        active_modes = sorted(k for k, rows in modes.items() if rows)
        # Obligations are derived from failure structure, not from a named model list.
        operations: list[dict[str, Any]] = [
            {"operation": "observe", "arity": 1, "reason": "prediction contract"},
            {"operation": "update", "arity": 2, "reason": "action-conditioned update contract"},
        ]
        if modes.get("residual") or modes.get("latent"):
            operations.append({"operation": "distinguish_hidden_equivalence_classes", "arity": 1, "reason": "persistent residual/latent evidence"})
        if modes.get("counterfactual"):
            operations.append({"operation": "counterfactual_update", "arity": 2, "reason": "counterfactual failure"})
        if modes.get("causal"):
            operations.append({"operation": "intervention_response", "arity": 2, "reason": "causal failure"})
        if modes.get("cross_domain_bridge"):
            operations.append({"operation": "typed_bridge_projection", "arity": 1, "reason": "cross-domain structural analogy"})
        if modes.get("operator_probe"):
            operations.append({"operation": "typed_operator_action", "arity": 1, "reason": "black-box operator-response evidence"})
        interaction_ranks = sorted({
            int(r.get("operator_interaction_rank", 0))
            for r in modes.get("operator_probe", ())
            if int(r.get("operator_interaction_rank", 0) or 0) > 1
        })
        if interaction_ranks:
            operations.append({
                "operation": "joint_coordinate_interaction",
                "arity": int(interaction_ranks[-1]),
                "reason": "minimal normal-ordered operator shell required by sealed black-box holdout",
            })
        # A representation change is warranted by a persistent residual plus at
        # least one independent line of evidence.  There is no fixed number of
        # evidence modes: repeated environments or a distinct evidence modality
        # can independently establish the need to change representation.
        warranted = bool(modes.get("residual")) and (len(active_modes) >= 2 or len(independent_envs) >= 2)
        payload = {
            "schema": SCHEMA,
            "owner_id": UNKNOWN_OWNER_ID,
            "status": "PROPOSE_GENERATED_REPRESENTATION_SIGNATURE" if warranted else "UNKNOWN_UNKNOWN_INSUFFICIENT_INDEPENDENT_MODES",
            "phi_scan_digest": scan["digest"],
            "phi_scan": {
                "registered_axis_count": scan["registered_axis_count"],
                "all_registered_axes_visited": scan["all_registered_axes_visited"],
                "owner_visits": scan["owner_visits"],
                "fixed_owner_visit_budget": scan["fixed_owner_visit_budget"],
                "fixed_candidate_axis_order_ceiling": scan["fixed_candidate_axis_order_ceiling"],
                "knowledge_firewall": scan["knowledge_firewall"],
            },
            "active_evidence_modes": active_modes,
            "independent_environment_count": len(independent_envs),
            "obligations": {
                "carrier": "GENERATED_OBSERVATIONAL_EQUIVALENCE_CARRIER",
                "operations": operations,
                "invariants": ["deterministic_update_when_evidence_is_deterministic", "observational_consistency"],
                "minimality_required": True,
                "known_representation_name_required": False,
            },
            "claim_boundary": {
                "internet_used_prefreeze": False,
                "known_method_selected_as_answer": False,
                "new_representation_type_established": warranted,
                "world_novelty_established": False,
            },
        }
        return _with_digest(payload)


class PrimitiveSynthesisOwner:
    """Synthesize a minimal finite predictive algebra from opaque histories.

    Histories are quotient-partitioned only by observable behaviour under the
    supplied action transition relation.  The resulting object is named by its
    content digest, not by a known representation family.
    """

    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": PRIMITIVE_OWNER_ID,
            "input": "OPAQUE_HISTORY_TRANSITIONS_PLUS_OBSERVATIONS",
            "objective": "MINIMIZE_CARRIER_CARDINALITY_SUBJECT_TO_UPDATE_AND_OBSERVE_CONTRACTS",
            "output": "GENERATED_ALGEBRAIC_PRIMITIVE",
            "known_representation_catalog": "NOT_USED",
        }

    @staticmethod
    def _normalize(rows: Sequence[Mapping[str, Any]]) -> tuple[list[str], list[str], dict[str, str], dict[tuple[str, str], str]]:
        histories: set[str] = set()
        actions: set[str] = set()
        obs: dict[str, str] = {}
        trans: dict[tuple[str, str], str] = {}
        for r in rows:
            s = str(r["history_id"]); a = str(r["action"]); t = str(r["next_history_id"])
            o = str(r["observation"])
            histories.update((s, t)); actions.add(a)
            if s in obs and obs[s] != o:
                raise ValueError(f"inconsistent observation for {s}")
            obs[s] = o
            key = (s, a)
            if key in trans and trans[key] != t:
                raise ValueError(f"nondeterministic transition for {key}")
            trans[key] = t
        missing_obs = sorted(histories - set(obs))
        # Allow next histories to have observation rows elsewhere, but complete coverage is mandatory.
        if missing_obs:
            raise ValueError(f"missing observations for histories: {missing_obs}")
        missing = [(s, a) for s in sorted(histories) for a in sorted(actions) if (s, a) not in trans]
        if missing:
            raise ValueError(f"incomplete action coverage: {missing[:4]}")
        return sorted(histories), sorted(actions), obs, trans

    def synthesize(self, *, transition_rows: Sequence[Mapping[str, Any]], freeze_digest: str) -> Mapping[str, Any]:
        if not freeze_digest:
            raise ValueError("primitive synthesis requires a pre-existing freeze digest")
        try:
            histories, actions, obs, trans = self._normalize(transition_rows)
        except Exception as exc:
            return _with_digest({
                "schema": SCHEMA, "owner_id": PRIMITIVE_OWNER_ID,
                "status": "PRIMITIVE_SYNTHESIS_BLOCKED_INCOMPLETE_OR_INCONSISTENT_EVIDENCE",
                "error": str(exc), "claim_boundary": {"primitive_promoted": False},
            })
        # Initial partition: histories with the same immediate observation.
        label = {s: obs[s] for s in histories}
        changed = True; rounds = 0
        while changed:
            rounds += 1
            signatures = {
                s: (obs[s], tuple(label[trans[(s, a)]] for a in actions))
                for s in histories
            }
            unique = {sig: f"q{idx}" for idx, sig in enumerate(sorted(set(signatures.values()), key=canonical_json))}
            new_label = {s: unique[signatures[s]] for s in histories}
            changed = new_label != label
            label = new_label
            if rounds > len(histories) + 2:
                raise RuntimeError("partition refinement failed to converge")
        classes: dict[str, list[str]] = defaultdict(list)
        for s, q in label.items(): classes[q].append(s)
        # Canonicalize class ids by member lists rather than transient q labels.
        ordered_classes = sorted((tuple(sorted(v)) for v in classes.values()))
        class_id = {members: f"x{idx}" for idx, members in enumerate(ordered_classes)}
        state_of: dict[str, str] = {}
        for members in ordered_classes:
            for s in members: state_of[s] = class_id[members]
        carrier = sorted(set(state_of.values()))
        observe: dict[str, str] = {}
        update: dict[str, dict[str, str]] = {a: {} for a in actions}
        for members in ordered_classes:
            q = class_id[members]; rep = members[0]; observe[q] = obs[rep]
            for a in actions:
                targets = {state_of[trans[(s, a)]] for s in members}
                if len(targets) != 1:
                    raise RuntimeError("quotient update is not well defined")
                update[a][q] = next(iter(targets))
        distinguishable_pairs = []
        for a, b in itertools.combinations(carrier, 2):
            if observe[a] != observe[b] or any(update[x][a] != update[x][b] for x in actions):
                distinguishable_pairs.append((a, b))
        primitive_core = {
            "carrier": carrier,
            "operations": {
                "observe": observe,
                "update": update,
            },
            "action_alphabet": actions,
            "relations": ["observational_equivalence_quotient"],
            "invariants": ["update_total_on_frozen_action_alphabet", "observation_single_valued"],
            "history_to_carrier": state_of,
        }
        primitive_digest = digest_payload(primitive_core)
        payload = {
            "schema": SCHEMA,
            "owner_id": PRIMITIVE_OWNER_ID,
            "status": "GENERATED_MINIMAL_ALGEBRAIC_PRIMITIVE",
            "freeze_digest": freeze_digest,
            "primitive_id": f"X-{primitive_digest[:16].upper()}",
            "primitive_type": "GENERATED_FINITE_ALGEBRAIC_SIGNATURE",
            "primitive": primitive_core,
            "minimality_certificate": {
                "input_history_count": len(histories),
                "carrier_cardinality": len(carrier),
                "partition_refinement_rounds": rounds,
                "all_distinct_carrier_pairs_behaviorally_separated": len(distinguishable_pairs) == len(carrier) * (len(carrier)-1)//2,
                "distinguishable_pairs": distinguishable_pairs,
            },
            "claim_boundary": {
                "known_representation_selected": False,
                "world_mathematical_novelty_established": False,
                "finite_evidence_minimality_only": True,
            },
        }
        return _with_digest(payload)


class MorphismDiscoveryOwner:
    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": MORPHISM_OWNER_ID,
            "objective": "FIND_F:A_TO_B_WITH_EXPLICIT_PRESERVE_LOSE",
            "exact_search_scope": "FINITE_GENERATED_PRIMITIVES_UP_TO_8_CARRIER_STATES",
        }

    @staticmethod
    def _core(obj: Mapping[str, Any]) -> Mapping[str, Any]:
        return obj.get("primitive", obj)

    def discover(self, *, source: Mapping[str, Any], target: Mapping[str, Any]) -> Mapping[str, Any]:
        A = self._core(source); B = self._core(target)
        sa = list(A["carrier"]); sb = list(B["carrier"])
        if len(sa) > 8 or len(sb) > 8 or not sa or not sb:
            return _with_digest({"schema": SCHEMA,"owner_id":MORPHISM_OWNER_ID,"status":"MORPHISM_SEARCH_BLOCKED_SCOPE","claim_boundary":{"morphism_established":False}})
        actions = sorted(set(A["operations"]["update"]) & set(B["operations"]["update"]))
        if not actions:
            return _with_digest({"schema": SCHEMA,"owner_id":MORPHISM_OWNER_ID,"status":"NO_COMMON_TYPED_UPDATE_OPERATIONS","claim_boundary":{"morphism_established":False}})
        candidates = []
        for image_tuple in itertools.product(sb, repeat=len(sa)):
            f = dict(zip(sa, image_tuple))
            observation_preserved = all(
                A["operations"]["observe"].get(s) == B["operations"]["observe"].get(f[s]) for s in sa
            )
            update_preserved = all(
                f[A["operations"]["update"][a][s]] == B["operations"]["update"][a][f[s]]
                for a in actions for s in sa
            )
            if not (observation_preserved and update_preserved):
                continue
            collapsed = sorted([list(pair) for pair in itertools.combinations(sa,2) if f[pair[0]] == f[pair[1]]])
            preserve = ["observe", "typed_update_commutation"]
            if set(f.values()) == set(sb): preserve.append("surjectivity")
            lose = ["source_state_distinction"] if collapsed else []
            row = {"mapping":f,"Preserve":preserve,"Lose":lose,"collapsed_source_pairs":collapsed}
            row["digest"] = digest_payload(row); candidates.append(row)
        candidates.sort(key=lambda r: (len(r["Lose"]), canonical_json(r["mapping"])))
        best = candidates[0] if candidates else None
        return _with_digest({
            "schema": SCHEMA,
            "owner_id": MORPHISM_OWNER_ID,
            "status": "EXACT_MORPHISM_DISCOVERED" if best else "NO_EXACT_MORPHISM_FOUND",
            "source_primitive_id": source.get("primitive_id"),
            "target_primitive_id": target.get("primitive_id"),
            "candidate_count": len(candidates),
            "morphism": best,
            "claim_boundary": {
                "morphism_established": bool(best),
                "source_target_canonicals_merged": False,
                "world_novelty_established": False,
            },
        })


class ControlledLimitEngine:
    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": LIMIT_OWNER_ID,
            "candidate_limit_directions": ("PARAMETER_TO_ZERO", "PARAMETER_TO_INFINITY"),
            "required_components": ("state", "update", "observable"),
            "promotion": "ALL_COMPONENT_ERRORS_MUST_DECREASE_WITH_POSITIVE_LOGLOG_ORDER",
        }

    @staticmethod
    def _fit(xs: Sequence[float], ys: Sequence[float]) -> tuple[float,float]:
        pts=[(math.log(x),math.log(y)) for x,y in zip(xs,ys) if x>0 and y>0 and math.isfinite(x) and math.isfinite(y)]
        if len(pts)<3:return (float("nan"),0.0)
        mx=sum(x for x,_ in pts)/len(pts); my=sum(y for _,y in pts)/len(pts)
        den=sum((x-mx)**2 for x,_ in pts)
        if den<=0:return (float("nan"),0.0)
        slope=sum((x-mx)*(y-my) for x,y in pts)/den
        pred=[my+slope*(x-mx) for x,_ in pts]
        ssr=sum((y-p)**2 for (_,y),p in zip(pts,pred)); sst=sum((y-my)**2 for _,y in pts)
        r2=1.0-ssr/sst if sst>0 else 1.0
        return slope,r2

    def assess(self, *, parameter_rows: Sequence[Mapping[str, Any]], parameter_name: str="lambda") -> Mapping[str, Any]:
        rows=[]
        for r in parameter_rows:
            lam=float(r[parameter_name])
            errs={k:float(r[f"{k}_error"]) for k in ("state","update","observable")}
            if lam<=0 or any(v<0 or not math.isfinite(v) for v in errs.values()):
                raise ValueError("controlled-limit rows require positive parameter and finite nonnegative errors")
            rows.append((lam,errs))
        if len(rows)<4:
            return _with_digest({"schema":SCHEMA,"owner_id":LIMIT_OWNER_ID,"status":"CONTROLLED_LIMIT_INSUFFICIENT_POINTS","claim_boundary":{"controlled_limit_established":False}})
        directions=[]
        for name, transform in (("PARAMETER_TO_ZERO",lambda x:x),("PARAMETER_TO_INFINITY",lambda x:1.0/x)):
            ordered=sorted(((transform(l),l,e) for l,e in rows),key=lambda z:z[0],reverse=True)
            # x -> 0 is the claimed limit; errors should also -> 0.
            xs=[x for x,_,_ in ordered]
            comp={}
            ok=True
            for k in ("state","update","observable"):
                ys=[e[k] for _,_,e in ordered]
                slope,r2=self._fit(xs,ys)
                monotone=all(ys[i+1] <= ys[i] + 1e-12 for i in range(len(ys)-1))
                reduction=(ys[-1] <= 0.35*ys[0]) if ys[0]>0 else ys[-1]==0
                good=math.isfinite(slope) and slope>0.25 and r2>=0.75 and monotone and reduction
                comp[k]={"order":slope,"r2":r2,"monotone_to_limit":monotone,"reduction_gate":reduction,"pass":good,"errors":ys}
                ok=ok and good
            directions.append({"direction":name,"pass":ok,"components":comp})
        passing=[d for d in directions if d["pass"]]
        best=max(passing,key=lambda d:min(v["r2"] for v in d["components"].values())) if passing else None
        return _with_digest({
            "schema":SCHEMA,
            "owner_id":LIMIT_OWNER_ID,
            "status":"CONTROLLED_LIMIT_ESTABLISHED" if best else "NO_CONTROLLED_LIMIT_ESTABLISHED",
            "parameter_name":parameter_name,
            "selected_limit_direction":best["direction"] if best else None,
            "direction_evidence":directions,
            "claim_boundary":{
                "controlled_limit_established":bool(best),
                "known_theory_recovered_as_limit_only_if_all_components_pass":bool(best),
                "new_theory_promoted":False,
            },
        })


class MathematicalInventionKernel:
    def __init__(self, root: str|Path) -> None:
        self.root=Path(root); self.runtime=LawSpaceRuntime(self.root)
        self.unknown_unknown=UnknownUnknownRepresentationOwner(self.runtime)
        self.primitive=PrimitiveSynthesisOwner(); self.morphism=MorphismDiscoveryOwner(); self.limit=ControlledLimitEngine()

    def contract(self)->Mapping[str,Any]:
        payload={
            "schema":SCHEMA,"owner_id":KERNEL_OWNER_ID,
            "owners":{
                "unknown_unknown":UNKNOWN_OWNER_ID,
                "primitive_synthesis":PRIMITIVE_OWNER_ID,
                "morphism_discovery":MORPHISM_OWNER_ID,
                "controlled_limit":LIMIT_OWNER_ID,
            },
            "pipeline":"PHI_SCAN->REPRESENTATION_OBLIGATIONS->GENERATED_PRIMITIVE->MORPHISM->CONTROLLED_LIMIT",
            "internet_prefreeze":"FORBIDDEN",
            "world_novelty":"NOT_ESTABLISHED_BY_MECHANISM_QUALIFICATION",
        }
        return _with_digest(payload)


__all__=[
    "MathematicalInventionKernel","UnknownUnknownRepresentationOwner","PrimitiveSynthesisOwner",
    "MorphismDiscoveryOwner","ControlledLimitEngine", "KERNEL_OWNER_ID", "UNKNOWN_OWNER_ID",
    "PRIMITIVE_OWNER_ID","MORPHISM_OWNER_ID","LIMIT_OWNER_ID",
]
