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

import numpy as np

from .candidates import CandidateGenerationPipeline, DirectedResearchQuery
from .runtime import LawSpaceRuntime
from .schema import canonical_json, digest_payload

KERNEL_OWNER_ID = "PHI-MATHEMATICAL-INVENTION-KERNEL/1.1.0"
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


class FunctionLanguageBirthEngine:
    """Residual-driven birth of a *function language* inside the existing kernel.

    This is deliberately not a new authoritative owner and not a global catalogue
    of mathematical answers.  Query mode supplies a frozen Pi-representation plus
    out-of-fold residuals from its current language.  The engine measures which
    primitive operations would distinguish structure left in those residuals and
    returns generated operation signatures.  Fitting, ranking, multiplicity
    control and world claims remain owned by QueryDrivenResearchOwner.
    """

    _FAMILY_OPERATIONS = {
        "RATIONAL": ("add", "multiply", "reciprocal"),
        "EXPONENTIAL": ("add", "multiply", "exp"),
        "LOGARITHMIC": ("add", "multiply", "signed_log1p"),
        "PERIODIC": ("add", "multiply", "sin", "cos"),
        "PIECEWISE": ("add", "multiply", "hinge", "threshold"),
        "KERNEL": ("distance", "radial_response", "linear_superposition"),
        "LATENT": ("linear_projection", "multiply", "low_rank_composition"),
    }

    def contract(self) -> Mapping[str, Any]:
        return {
            "component": "FUNCTION-LANGUAGE-BIRTH",
            "authority": KERNEL_OWNER_ID,
            "input": "FROZEN_COORDINATES_PLUS_OUT_OF_FOLD_RESIDUAL",
            "output": "GENERATED_OPERATION_SIGNATURES_NOT_WORLD_LAWS",
            "trigger": "PERSISTENT_CROSS_VALIDATED_RESIDUAL",
            "fixed_global_language_catalog_is_primary_space": False,
            "known_family_name_is_world_novelty_claim": False,
            "candidate_operations": {k: list(v) for k, v in self._FAMILY_OPERATIONS.items()},
        }

    @staticmethod
    def _corr(a: np.ndarray, b: np.ndarray) -> float:
        a=np.asarray(a,float); b=np.asarray(b,float)
        mask=np.isfinite(a)&np.isfinite(b)
        if int(mask.sum())<6: return 0.0
        aa=a[mask]-float(np.mean(a[mask])); bb=b[mask]-float(np.mean(b[mask]))
        den=float(np.linalg.norm(aa)*np.linalg.norm(bb))
        return abs(float(np.dot(aa,bb)/den)) if den>1e-14 else 0.0

    def diagnose(self, *, coordinates: Sequence[Sequence[float]], residuals: Sequence[float],
                 baseline_nrmse: float, minimum_birth_nrmse: float = 0.08,
                 minimum_signal: float = 0.12, minimum_languages: int = 3,
                 maximum_languages: int = 7) -> Mapping[str, Any]:
        x=np.asarray(coordinates,float); r=np.asarray(residuals,float)
        if x.ndim!=2 or len(r)!=x.shape[0]:
            raise ValueError("function-language birth requires a 2D coordinate matrix aligned to residuals")
        finite=np.isfinite(r)&np.all(np.isfinite(x),axis=1)
        x=x[finite]; r=r[finite]
        if len(r)<12 or float(np.std(r))<=1e-14:
            payload={"schema":SCHEMA,"component":"FUNCTION-LANGUAGE-BIRTH","status":"NO_LANGUAGE_BIRTH_INSUFFICIENT_RESIDUAL_EVIDENCE",
                     "baseline_cross_validated_nrmse":float(baseline_nrmse),"generated_languages":[],
                     "claim_boundary":{"function_language_established":False,"world_law_established":False}}
            return _with_digest(payload)
        mu=np.mean(x,axis=0); scale=np.std(x,axis=0); scale=np.where(scale<=1e-14,1.0,scale)
        z=(x-mu)/scale

        # Scores are evidence for primitive operations, not fits of the final target.
        # Each score is the strongest residual association available to that
        # operation class on the frozen coordinates.
        scores: dict[str,float]={}
        coord_scores: dict[str,list[float]]={}
        preference_override: dict[str,list[int]]={}
        for family in self._FAMILY_OPERATIONS:
            per=[]
            for j in range(z.shape[1]):
                q=z[:,j]
                if family=="RATIONAL":
                    feats=(1.0/(1.0+np.abs(q)), q/(1.0+np.abs(q)))
                    score=max((self._corr(r,f) for f in feats),default=0.0)
                elif family=="EXPONENTIAL":
                    feats=(np.exp(np.clip(q,-4,4)), np.exp(np.clip(-q,-4,4)))
                    score=max((self._corr(r,f) for f in feats),default=0.0)
                elif family=="LOGARITHMIC":
                    feats=(np.sign(q)*np.log1p(np.abs(q)), np.log1p(q*q))
                    score=max((self._corr(r,f) for f in feats),default=0.0)
                elif family=="PERIODIC":
                    feats=tuple(v for w in (1.0,2.0,3.0) for v in (np.sin(w*q),np.cos(w*q)))
                    score=max((self._corr(r,f) for f in feats),default=0.0)
                elif family=="PIECEWISE":
                    # A threshold language is indicated by a discontinuity in
                    # residual mean, not merely by correlation with a hinge.
                    th=np.quantile(q,(0.15,0.25,0.35,0.5,0.65,0.75,0.85))
                    feats=tuple((q>float(t)).astype(float) for t in th)
                    score=max((self._corr(r,f) for f in feats),default=0.0)
                elif family=="KERNEL":
                    centers=np.quantile(q,(0.2,0.5,0.8))
                    feats=tuple(np.exp(-((q-float(c))**2)) for c in centers)
                    score=max((self._corr(r,f) for f in feats),default=0.0)
                else:  # LATENT receives pair/interacting evidence below as well.
                    feats=(q*q, q*q*q)
                    score=max((self._corr(r,f) for f in feats),default=0.0)
                per.append(float(score))
            if family=="LATENT" and z.shape[1]>=2:
                pair=max((self._corr(r,z[:,a]*z[:,b]) for a in range(z.shape[1]) for b in range(a+1,z.shape[1])),default=0.0)
                scores[family]=float(max(max(per,default=0.0),pair))
            elif family=="KERNEL" and z.shape[1]>=2:
                # Local smooth structure may be invisible in every marginal but
                # obvious in a joint coordinate neighborhood.  Nearest-neighbor
                # residual autocorrelation supplies that operation-level signal.
                best_pair=None; best_local=0.0
                for a in range(z.shape[1]):
                    for b in range(a+1,z.shape[1]):
                        zz=z[:,[a,b]]
                        d2=np.sum((zz[:,None,:]-zz[None,:,:])**2,axis=2)
                        np.fill_diagonal(d2,np.inf)
                        nn=np.argmin(d2,axis=1)
                        local=self._corr(r,r[nn])
                        if local>best_local:
                            best_local=float(local); best_pair=(a,b)
                scores[family]=float(max(max(per,default=0.0),best_local))
                if best_pair is not None:
                    rest=[j for j in range(z.shape[1]) if j not in best_pair]
                    preference_override[family]=[int(best_pair[0]),int(best_pair[1])]+rest
            else:
                scores[family]=float(max(per,default=0.0))
            coord_scores[family]=[float(v) for v in per[:z.shape[1]]]

        ordered=sorted(scores,key=lambda k:(-scores[k],k))
        # Residual diagnostics examine many transformed features.  The screening
        # gate therefore grows with the number of coordinates/tests instead of
        # treating a raw 0.12 correlation as equally persuasive in every search.
        # This is a conservative structural screen, not a formal p-value; the
        # formal familywise calibration remains Query mode's replayed permutation
        # null after languages are actually fitted.
        feature_tests=max(8,7*max(1,z.shape[1])*6)
        multiplicity_gate=math.sqrt(2.0*math.log(float(feature_tests)+1.0)/float(len(r)))
        effective_signal_gate=max(float(minimum_signal),float(multiplicity_gate))
        selected=[k for k in ordered if scores[k]>=effective_signal_gate]
        if float(baseline_nrmse) < float(minimum_birth_nrmse):
            selected=[]; status="CURRENT_LANGUAGE_RESIDUAL_WITHIN_BIRTH_TOLERANCE"
        else:
            # Do not force a minimum number of languages when residuals are
            # structureless.  A high baseline error alone is not evidence for a
            # new operation; at least one operation signal must cross the frozen
            # gate.  ``minimum_languages`` is retained in the API for backward
            # compatibility but is not allowed to manufacture evidence.
            selected=selected[:int(maximum_languages)]
            status="FUNCTION_LANGUAGE_BIRTH_WARRANTED" if selected else "NO_OPERATION_SIGNAL_ABOVE_BIRTH_GATE"

        generated=[]
        for rank,fam in enumerate(selected,1):
            per=coord_scores.get(fam,[])
            coordinate_order=list(preference_override.get(fam,sorted(range(len(per)),key=lambda j:(-per[j],j))))
            signature={
                "language_id":f"LANG-{rank}-{digest_payload({'family':fam,'ops':self._FAMILY_OPERATIONS[fam]})[:12].upper()}",
                "family":fam,
                "operations":list(self._FAMILY_OPERATIONS[fam]),
                "residual_signal":float(scores[fam]),
                "coordinate_preference":coordinate_order,
                "generated_from_residual":True,
            }
            signature["digest"]=digest_payload(signature)
            generated.append(signature)
        payload={
            "schema":SCHEMA,"component":"FUNCTION-LANGUAGE-BIRTH","status":status,
            "baseline_cross_validated_nrmse":float(baseline_nrmse),
            "minimum_birth_nrmse":float(minimum_birth_nrmse),"minimum_operation_signal":float(minimum_signal),
            "effective_multiplicity_aware_signal_gate":float(effective_signal_gate),
            "operation_signal_scores":{k:float(scores[k]) for k in sorted(scores)},
            "generated_languages":generated,
            "claim_boundary":{
                "function_language_established":bool(generated),
                "generated_language_is_confirmed_world_law":False,
                "known_family_name_used_as_novelty_evidence":False,
                "residual_diagnostics_are_independent_world_replication":False,
            },
        }
        return _with_digest(payload)


class OperatorLanguageBirthEngine:
    """Generate a local operator language from weaker translation/algebra primitives.

    The component is intentionally below a differential-operator grammar.  It is
    not given names such as gradient, derivative or Laplacian and it does not
    receive a list of desired differential orders.  Its seed capabilities are:
    local coordinate translation, linear superposition, pointwise multiplication,
    reciprocal and dimensional typing.  Translation responses are generated by
    fair-dovetail moment shells; typed pointwise compositions are retained only
    when their output dimension can participate in the frozen target relation.

    A finite ``search_shell_budget`` is a runtime resource guard, not a scientific
    ceiling.  Receipts preserve the explored shells and the stop reason.
    """

    component_id = "OPERATOR-LANGUAGE-BIRTH/1.0.0-COMPONENT"

    def contract(self) -> Mapping[str, Any]:
        return {
            "component": self.component_id,
            "authority": KERNEL_OWNER_ID,
            "input": "PRIMITIVE_COORDINATE_AND_FIELD_TYPES_ONLY",
            "output": "GENERATED_LOCAL_OPERATOR_LANGUAGE_SIGNATURES",
            "named_differential_operator_catalog_used": False,
            "fixed_derivative_order_catalog_used": False,
            "seed_meta_primitives": (
                "LOCAL_TRANSLATION", "LINEAR_SUPERPOSITION", "POINTWISE_MULTIPLY",
                "POINTWISE_RECIPROCAL", "DIMENSION_TYPING",
            ),
            "search_policy": "FAIR_DOVETAIL_MOMENT_RANK_SHELLS_WITH_RESOURCE_GUARD",
            "fixed_global_operator_rank_ceiling": None,
        }

    @staticmethod
    def _dim(v: Sequence[float]) -> tuple[float, ...]:
        row=tuple(float(x) for x in v)
        if len(row)!=7:
            raise ValueError("operator-language dimensions must have seven base exponents")
        return row

    @staticmethod
    def _add(a: Sequence[float], b: Sequence[float]) -> tuple[float, ...]:
        return tuple(float(x)+float(y) for x,y in zip(a,b))

    @staticmethod
    def _scale(a: Sequence[float], k: float) -> tuple[float, ...]:
        return tuple(float(k)*float(x) for x in a)

    @classmethod
    def _sub(cls, a: Sequence[float], b: Sequence[float]) -> tuple[float, ...]:
        return cls._add(a, cls._scale(b,-1.0))

    @staticmethod
    def _eq(a: Sequence[float], b: Sequence[float], tol: float=1e-12) -> bool:
        return all(abs(float(x)-float(y))<=tol for x,y in zip(a,b))

    def invent(
        self, *, coordinate_dimensions: Mapping[str, Sequence[float]],
        field_dimensions: Mapping[str, Sequence[float]], target_field: str,
        search_shell_budget: int=8,
        carrier_factor_budget: int=1,
    ) -> Mapping[str, Any]:
        cdim={str(k):self._dim(v) for k,v in coordinate_dimensions.items()}
        fdim={str(k):self._dim(v) for k,v in field_dimensions.items()}
        target_field=str(target_field)
        if target_field not in fdim or not cdim:
            raise ValueError("operator-language birth requires coordinate/field dimensions and target_field")
        budget=max(2,int(search_shell_budget))
        factor_budget=max(1,int(carrier_factor_budget))
        time_signature=(0.0,0.0,1.0,0.0,0.0,0.0,0.0)
        time_coords=[k for k,v in cdim.items() if self._eq(v,time_signature)]
        if len(time_coords)!=1:
            raise ValueError("operator-language birth requires exactly one time-like coordinate")
        time_coord=time_coords[0]
        target_relation_dim=self._sub(fdim[target_field],cdim[time_coord])

        # The target action is itself born from the same translation-moment shells.
        target_action=None
        generated=[]
        shell_journal=[]
        empty_after_signal=0
        ever_signal=False
        for rank in range(1,budget+1):
            shell=[]
            for coord,coord_dim in sorted(cdim.items()):
                # Evolution-target separation: the unique time-like coordinate is
                # reserved for the target action so a predictor cannot reproduce
                # the target through the same local response (identity leakage).
                if coord == time_coord:
                    continue
                for response_field,response_dim in sorted(fdim.items()):
                    response_out=self._sub(response_dim,self._scale(coord_dim,float(rank)))
                    # Bare local response.
                    if self._eq(response_out,target_relation_dim):
                        shell.append({
                            "kind":"LOCAL_TRANSLATION_MOMENT_RESPONSE",
                            "response_field":response_field,"coordinate":coord,
                            "moment_rank":rank,"carrier_field":None,"carrier_power":0,
                            "dimension":list(target_relation_dim),
                        })
                    # One pointwise factor is not a PDE-term template: both sign
                    # choices are generated generically and only typing may retain one.
                    for carrier,carrier_dim in sorted(fdim.items()):
                        for power in (-1,1):
                            out=self._add(response_out,self._scale(carrier_dim,float(power)))
                            if self._eq(out,target_relation_dim):
                                shell.append({
                                    "kind":"POINTWISE_MONOMIAL_X_LOCAL_TRANSLATION_MOMENT_RESPONSE",
                                    "response_field":response_field,"coordinate":coord,
                                    "moment_rank":rank,"carrier_field":carrier,"carrier_power":power,
                                    "dimension":list(target_relation_dim),
                                })
                    # Higher algebraic carrier depth is born only when the caller
                    # explicitly opens a wider resource shell (for example after a
                    # persistent residual).  This is a generic monomial closure of
                    # the same pointwise multiply/reciprocal primitives; it does not
                    # contain a catalogue of scientific terms.  Depth is a runtime
                    # search budget, never a scientific ceiling.
                    if factor_budget >= 2:
                        atoms=[(name,power) for name in sorted(fdim) for power in (-1,1)]
                        for depth in range(2,factor_budget+1):
                            for combo in itertools.combinations_with_replacement(atoms,depth):
                                powers: dict[str,int] = defaultdict(int)
                                for name,power in combo:
                                    powers[str(name)] += int(power)
                                powers={name:power for name,power in powers.items() if power}
                                # Opposite factors that cancel would merely recreate
                                # a shallower shell and are therefore not a new birth.
                                if sum(abs(power) for power in powers.values()) != depth:
                                    continue
                                out=response_out
                                factors=[]
                                for name,power in sorted(powers.items()):
                                    out=self._add(out,self._scale(fdim[name],float(power)))
                                    factors.append({"field":name,"power":int(power)})
                                if self._eq(out,target_relation_dim):
                                    shell.append({
                                        "kind":"POINTWISE_MONOMIAL_X_LOCAL_TRANSLATION_MOMENT_RESPONSE",
                                        "response_field":response_field,"coordinate":coord,
                                        "moment_rank":rank,"carrier_factors":factors,
                                        "carrier_factor_count":depth,
                                        "dimension":list(target_relation_dim),
                                    })
            # Target must be a pure translation response of target_field along the
            # unique time-like coordinate.  Its rank is discovered, not supplied.
            response_out=self._sub(fdim[target_field],self._scale(cdim[time_coord],float(rank)))
            if target_action is None and self._eq(response_out,target_relation_dim):
                target_action={
                    "kind":"LOCAL_TRANSLATION_MOMENT_RESPONSE",
                    "response_field":target_field,"coordinate":time_coord,
                    "moment_rank":rank,"carrier_field":None,"carrier_power":0,
                    "dimension":list(target_relation_dim),
                }
            unique={digest_payload(x):x for x in shell}
            shell=[unique[k] for k in sorted(unique)]
            generated.extend(shell)
            shell_journal.append({"rank_shell":rank,"typed_signature_count":len(shell),"digest":digest_payload(shell)})
            if shell:
                ever_signal=True; empty_after_signal=0
            elif ever_signal:
                empty_after_signal+=1
            # Two empty shells after at least one typed shell are sufficient for
            # this finite run.  Future cycles may resume at the next shell.
            if ever_signal and empty_after_signal>=2 and target_action is not None:
                break
        unique={digest_payload(x):x for x in generated}
        generated=[unique[k] for k in sorted(unique)]
        stop_rank=shell_journal[-1]["rank_shell"] if shell_journal else 0
        payload={
            "schema":SCHEMA,"component":self.component_id,
            "status":"GENERATED_OPERATOR_LANGUAGE" if generated and target_action else "OPERATOR_LANGUAGE_BIRTH_INSUFFICIENT_TYPED_STRUCTURE",
            "seed_meta_primitives":list(self.contract()["seed_meta_primitives"]),
            "target_field":target_field,"inferred_time_coordinate":time_coord,
            "target_relation_dimension":list(target_relation_dim),
            "target_action":target_action,"generated_signatures":generated,
            "generated_signature_count":len(generated),"shell_journal":shell_journal,
            "search_shell_budget":budget,"last_explored_rank_shell":stop_rank,
            "carrier_factor_budget":factor_budget,
            "search_may_resume_beyond_budget":True,
            "claim_boundary":{
                "named_differential_operator_catalog_used":False,
                "fixed_derivative_order_catalog_used":False,
                "local_translation_meta_primitive_preexists":True,
                "pointwise_algebra_meta_primitives_preexist":True,
                "generated_language_is_scientific_law":False,
                "world_novelty_established":False,
                "resource_budget_is_scientific_rank_ceiling":False,
                "carrier_factor_budget_is_scientific_ceiling":False,
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
        self.function_language=FunctionLanguageBirthEngine()
        self.operator_language=OperatorLanguageBirthEngine()
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
            "components":{"function_language_birth":"FUNCTION-LANGUAGE-BIRTH/1.0.0-COMPONENT","operator_language_birth":self.operator_language.component_id},
            "pipeline":"PHI_SCAN->REPRESENTATION_OBLIGATIONS->GENERATED_PRIMITIVE->MORPHISM->CONTROLLED_LIMIT",
            "function_language_pipeline":"QUERY_OOF_RESIDUAL->OPERATION_SIGNAL->GENERATED_LANGUAGE_SIGNATURE->QUERY_REFIT_AND_NULL",
            "operator_language_pipeline":"LOCAL_TRANSLATION_PLUS_POINTWISE_ALGEBRA->MOMENT_RANK_SHELLS->TYPED_SIGNATURES->EMPIRICAL_SUPPORT_SEARCH",
            "internet_prefreeze":"FORBIDDEN",
            "world_novelty":"NOT_ESTABLISHED_BY_MECHANISM_QUALIFICATION",
        }
        return _with_digest(payload)


__all__=[
    "MathematicalInventionKernel","UnknownUnknownRepresentationOwner","PrimitiveSynthesisOwner",
    "MorphismDiscoveryOwner","ControlledLimitEngine","FunctionLanguageBirthEngine","OperatorLanguageBirthEngine", "KERNEL_OWNER_ID", "UNKNOWN_OWNER_ID",
    "PRIMITIVE_OWNER_ID","MORPHISM_OWNER_ID","LIMIT_OWNER_ID",
]
