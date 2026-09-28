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
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from .candidates import CandidateGenerationPipeline, DirectedResearchQuery
from .runtime import LawSpaceRuntime
from .schema import canonical_json, digest_payload

KERNEL_OWNER_ID = "PHI-MATHEMATICAL-INVENTION-KERNEL/1.5.0"
UNKNOWN_OWNER_ID = "UNKNOWN-UNKNOWN-REPRESENTATION-TYPE-DISCOVERY/1.0.0"
PRIMITIVE_OWNER_ID = "PRIMITIVE-SYNTHESIS/1.0.0"
MORPHISM_OWNER_ID = "MORPHISM-DISCOVERY/1.0.0"
LIMIT_OWNER_ID = "CONTROLLED-LIMIT-ENGINE/1.0.0"
SCHEMA = "phi-mathematical-invention-kernel/v1"
AUTONOMOUS_CANDIDATE_BIRTH_COMPONENT_ID = "AUTONOMOUS-MATHEMATICAL-CANDIDATE-BIRTH/1.0.0-COMPONENT"
SEMANTIC_OBLIGATION_COMPILER_COMPONENT_ID = "SEMANTIC-PROOF-OBLIGATION-COMPILER/1.0.0-COMPONENT"
SEMANTIC_BINDING_INVENTION_COMPONENT_ID = "SEMANTIC-BINDING-INVENTION/1.0.0-COMPONENT"


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
        target_action_mode: str="TIME_TRANSLATION_MOMENT_RESPONSE",
        predictor_fields: Sequence[str] | None=None,
    ) -> Mapping[str, Any]:
        cdim={str(k):self._dim(v) for k,v in coordinate_dimensions.items()}
        fdim={str(k):self._dim(v) for k,v in field_dimensions.items()}
        target_field=str(target_field)
        if target_field not in fdim or not cdim:
            raise ValueError("operator-language birth requires coordinate/field dimensions and target_field")
        budget=max(2,int(search_shell_budget))
        factor_budget=max(1,int(carrier_factor_budget))
        target_mode=str(target_action_mode).upper().strip()
        if target_mode not in {"TIME_TRANSLATION_MOMENT_RESPONSE","DIRECT_FIELD_VALUE"}:
            raise ValueError("unsupported operator-language target_action_mode")
        if predictor_fields is None:
            predictor_names=tuple(sorted(k for k in fdim if target_mode!="DIRECT_FIELD_VALUE" or k!=target_field))
        else:
            predictor_names=tuple(sorted({str(x) for x in predictor_fields}))
            missing=[name for name in predictor_names if name not in fdim]
            if missing:
                raise ValueError(f"operator-language predictor_fields missing from field_dimensions: {missing}")
        if target_mode=="DIRECT_FIELD_VALUE" and target_field in predictor_names:
            raise ValueError("DIRECT_FIELD_VALUE target_field must be excluded from predictor_fields")
        predictor_fdim={name:fdim[name] for name in predictor_names}
        if not predictor_fdim:
            raise ValueError("operator-language birth requires at least one predictor field")
        time_signature=(0.0,0.0,1.0,0.0,0.0,0.0,0.0)
        time_coords=[k for k,v in cdim.items() if self._eq(v,time_signature)]
        if target_mode=="TIME_TRANSLATION_MOMENT_RESPONSE":
            if len(time_coords)!=1:
                raise ValueError("operator-language birth requires exactly one time-like coordinate")
            time_coord=time_coords[0]
            target_relation_dim=self._sub(fdim[target_field],cdim[time_coord])
            target_action=None
        else:
            time_coord=None
            target_relation_dim=fdim[target_field]
            target_action={
                "kind":"DIRECT_FIELD_VALUE",
                "response_field":target_field,
                "coordinate":None,
                "moment_rank":0,
                "carrier_field":None,
                "carrier_power":0,
                "dimension":list(target_relation_dim),
            }

        # The target action is itself born from the same translation-moment shells.
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
                if target_mode=="TIME_TRANSLATION_MOMENT_RESPONSE" and coord == time_coord:
                    continue
                for response_field,response_dim in sorted(predictor_fdim.items()):
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
                    for carrier,carrier_dim in sorted(predictor_fdim.items()):
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
                        atoms=[(name,power) for name in sorted(predictor_fdim) for power in (-1,1)]
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
                                    out=self._add(out,self._scale(predictor_fdim[name],float(power)))
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
            if target_mode=="TIME_TRANSLATION_MOMENT_RESPONSE":
                assert time_coord is not None
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
            "target_field":target_field,"target_action_mode":target_mode,
            "predictor_fields":list(predictor_names),
            "target_field_excluded_from_predictor_language":bool(target_mode=="DIRECT_FIELD_VALUE"),
            "inferred_time_coordinate":time_coord,
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


SCALE_REPRESENTATION_OWNER_ID = "SCALE-INVARIANT-REPRESENTATION-BIRTH/1.0.0"


class ScaleInvariantRepresentationBirthOwner:
    """Birth a dimension-preserving numerical chart from primitive predictor scales.

    This owner is generic: it receives only typed primitive coordinates/fields and
    discovery studies.  It does not receive a Reynolds number, a turbulence model,
    a named dimensionless group, or sealed target values.  It searches for stable
    scale carriers among predictor fields, falls back to joint RMS scales for a
    dimension class, and solves a small integer dimensional-balance problem for
    the target relation.  Applying the frozen chart rescales numbers while keeping
    the original physical dimension type available to the operator-language owner.
    """

    owner_id = SCALE_REPRESENTATION_OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": self.owner_id,
            "input": "DISCOVERY_PRIMITIVE_PREDICTOR_FIELDS_PLUS_DIMENSION_TYPES",
            "output": "FROZEN_DIMENSION_PRESERVING_SCALE_CHART",
            "named_dimensionless_group_catalog_used": False,
            "sealed_target_values_used_for_birth": False,
            "target_values_used_for_scale_estimation": False,
            "dimension_type_preserved_after_numerical_rescaling": True,
            "scale_sources": (
                "DISCOVERY_CONSTANT_PREDICTOR_FIELD_MEDIAN_ABS",
                "DISCOVERY_JOINT_RMS_OF_SAME_DIMENSION_PREDICTOR_FIELDS",
                "DISCOVERY_COORDINATE_SPAN_FALLBACK",
            ),
        }

    @staticmethod
    def _dim(v: Sequence[float]) -> tuple[float, ...]:
        row = tuple(float(x) for x in v)
        if len(row) != 7:
            raise ValueError("scale-representation dimensions must have seven base exponents")
        return row

    @staticmethod
    def _dim_key(v: Sequence[float]) -> str:
        return digest_payload([float(x) for x in v])[:16]

    @staticmethod
    def _eq(a: Sequence[float], b: Sequence[float], tol: float = 1e-12) -> bool:
        return all(abs(float(x)-float(y)) <= tol for x, y in zip(a, b))

    @staticmethod
    def _scale_value(rule: Mapping[str, Any], study: Mapping[str, Any]) -> float:
        fields = dict(study.get("fields", {}))
        coords = dict(study.get("coordinates", {}))
        kind = str(rule.get("kind", ""))
        names = tuple(str(x) for x in rule.get("members", ()))
        if kind == "CONSTANT_FIELD_MEDIAN_ABS":
            if len(names) != 1 or names[0] not in fields:
                raise ValueError("constant-field scale rule cannot be evaluated")
            arr = np.asarray(fields[names[0]], dtype=float)
            value = float(np.median(np.abs(arr)))
        elif kind == "JOINT_RMS_FIELDS":
            arrays = [np.asarray(fields[name], dtype=float) for name in names if name in fields]
            if len(arrays) != len(names) or not arrays:
                raise ValueError("joint-RMS field scale rule cannot be evaluated")
            value = float(np.sqrt(np.mean(np.sum([a*a for a in arrays], axis=0))))
        elif kind == "COORDINATE_SPAN":
            spans = []
            for name in names:
                arr = np.asarray(coords.get(name, ()), dtype=float)
                if arr.size < 2:
                    raise ValueError("coordinate-span scale rule cannot be evaluated")
                spans.append(float(np.max(arr)-np.min(arr)))
            value = float(np.exp(np.mean(np.log(np.asarray(spans, dtype=float)))))
        else:
            raise ValueError(f"unsupported scale rule kind {kind!r}")
        if not math.isfinite(value) or value <= 1e-14:
            raise ValueError("scale rule produced a non-positive/non-finite value")
        return value

    @classmethod
    def _constant_field_candidate(cls, name: str, discovery_studies: Sequence[Mapping[str, Any]]) -> bool:
        for study in discovery_studies:
            arr = np.asarray(dict(study.get("fields", {})).get(name), dtype=float)
            if arr.size == 0 or not np.all(np.isfinite(arr)):
                return False
            mean_abs = float(np.mean(np.abs(arr)))
            if mean_abs <= 1e-14:
                return False
            spread = float(np.std(arr))
            if spread > max(1e-12, mean_abs * 1e-10):
                return False
        return True

    @classmethod
    def _integer_balance(
        cls, target_dim: Sequence[float], rules: Sequence[Mapping[str, Any]], exponent_radius: int
    ) -> dict[str, int] | None:
        target = cls._dim(target_dim)
        rows = [(str(r["rule_id"]), cls._dim(r["dimension"])) for r in rules]
        if not rows:
            return None
        radius = max(1, int(exponent_radius))
        solutions: list[tuple[tuple[int, int, tuple[int, ...]], dict[str, int]]] = []
        for exponents in itertools.product(range(-radius, radius+1), repeat=len(rows)):
            if not any(exponents):
                continue
            out = [0.0] * 7
            for exponent, (_, dim) in zip(exponents, rows):
                for i, value in enumerate(dim):
                    out[i] += float(exponent) * float(value)
            if cls._eq(out, target):
                active = sum(1 for e in exponents if e)
                l1 = sum(abs(e) for e in exponents)
                key = (active, l1, tuple(int(e) for e in exponents))
                solutions.append((key, {rid: int(e) for e, (rid, _) in zip(exponents, rows) if e}))
        if not solutions:
            return None
        solutions.sort(key=lambda item: item[0])
        return solutions[0][1]

    def invent(
        self, *, discovery_studies: Sequence[Mapping[str, Any]],
        coordinate_dimensions: Mapping[str, Sequence[float]],
        field_dimensions: Mapping[str, Sequence[float]], target_field: str,
        predictor_fields: Sequence[str], exponent_radius: int = 4,
    ) -> Mapping[str, Any]:
        discovery = tuple(dict(x) for x in discovery_studies if str(x.get("role", "DISCOVERY")).upper() == "DISCOVERY")
        if not discovery:
            raise ValueError("scale representation birth requires discovery studies")
        target_field = str(target_field)
        predictors = tuple(sorted({str(x) for x in predictor_fields if str(x) != target_field}))
        fdim = {str(k): self._dim(v) for k, v in field_dimensions.items()}
        cdim = {str(k): self._dim(v) for k, v in coordinate_dimensions.items()}
        if target_field not in fdim or not predictors:
            raise ValueError("scale representation birth requires target and predictor field dimensions")
        missing = [name for name in predictors if name not in fdim]
        if missing:
            raise ValueError(f"predictor fields missing dimensions: {missing}")

        by_dim: dict[tuple[float, ...], list[str]] = defaultdict(list)
        for name in predictors:
            by_dim[fdim[name]].append(name)
        rules: list[dict[str, Any]] = []
        field_rule: dict[str, str] = {}
        for dim, members in sorted(by_dim.items(), key=lambda item: self._dim_key(item[0])):
            constants = [name for name in sorted(members) if self._constant_field_candidate(name, discovery)]
            if constants:
                # Each independent constant carrier is a distinct candidate scale.
                # Freeze the lexicographically first one for deterministic replay;
                # no target values are consulted in this choice.
                chosen = constants[0]
                kind = "CONSTANT_FIELD_MEDIAN_ABS"
                scale_members = [chosen]
            else:
                kind = "JOINT_RMS_FIELDS"
                scale_members = sorted(members)
            rid = "scale_" + digest_payload({"kind": kind, "members": scale_members, "dimension": list(dim)})[:16]
            rule = {"rule_id": rid, "kind": kind, "members": scale_members, "dimension": list(dim)}
            rules.append(rule)
            for name in members:
                field_rule[name] = rid

        # Coordinates inherit an existing same-dimension field scale when one is
        # available.  Otherwise birth a coordinate-span scale from discovery only.
        coordinate_rule: dict[str, str] = {}
        dim_to_rule = {tuple(self._dim(r["dimension"])): str(r["rule_id"]) for r in rules}
        for dim in sorted(set(cdim.values()), key=self._dim_key):
            if dim in dim_to_rule:
                rid = dim_to_rule[dim]
            else:
                members = sorted(name for name, d in cdim.items() if d == dim)
                rid = "scale_" + digest_payload({"kind": "COORDINATE_SPAN", "members": members, "dimension": list(dim)})[:16]
                rules.append({"rule_id": rid, "kind": "COORDINATE_SPAN", "members": members, "dimension": list(dim)})
                dim_to_rule[dim] = rid
            for name, d in cdim.items():
                if d == dim:
                    coordinate_rule[name] = rid

        target_exponents = self._integer_balance(fdim[target_field], rules, exponent_radius)
        if target_exponents is None:
            payload = {
                "schema": SCHEMA, "owner_id": self.owner_id,
                "status": "SCALE_REPRESENTATION_BIRTH_INSUFFICIENT_DIMENSIONAL_BASIS",
                "rules": rules, "target_field": target_field,
                "predictor_fields": list(predictors),
                "claim_boundary": {"sealed_target_values_used_for_birth": False, "named_dimensionless_group_catalog_used": False},
            }
            return _with_digest(payload)

        # Verify every frozen scale rule on discovery predictor/coordinate values.
        scale_receipts = []
        for study in discovery:
            values = {str(r["rule_id"]): self._scale_value(r, study) for r in rules}
            scale_receipts.append({"study_id": str(study.get("study_id", "")), "scale_values": values})

        payload = {
            "schema": SCHEMA, "owner_id": self.owner_id,
            "status": "SCALE_INVARIANT_REPRESENTATION_BORN",
            "birth_evidence_role": "DISCOVERY_ONLY",
            "target_field": target_field, "predictor_fields": list(predictors),
            "rules": rules, "field_scale_rule": field_rule,
            "coordinate_scale_rule": coordinate_rule,
            "target_scale_exponents": target_exponents,
            "discovery_scale_receipts": scale_receipts,
            "exponent_search_radius": max(1, int(exponent_radius)),
            "exponent_search_radius_is_scientific_ceiling": False,
            "claim_boundary": {
                "named_dimensionless_group_catalog_used": False,
                "reynolds_number_supplied_to_owner": False,
                "sealed_studies_used_for_birth": False,
                "sealed_target_values_used_for_birth": False,
                "target_values_used_for_scale_estimation": False,
                "numerical_rescaling_preserves_physical_dimension_type": True,
                "representation_birth_establishes_scientific_law": False,
            },
        }
        return _with_digest(payload)

    def apply(
        self, *, studies: Sequence[Mapping[str, Any]], chart: Mapping[str, Any], target_field: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if chart.get("status") != "SCALE_INVARIANT_REPRESENTATION_BORN":
            raise ValueError("cannot apply an unqualified scale representation")
        target_field = str(target_field)
        rules = [dict(x) for x in chart.get("rules", ())]
        field_rule = {str(k): str(v) for k, v in dict(chart.get("field_scale_rule", {})).items()}
        coordinate_rule = {str(k): str(v) for k, v in dict(chart.get("coordinate_scale_rule", {})).items()}
        target_exponents = {str(k): int(v) for k, v in dict(chart.get("target_scale_exponents", {})).items()}
        out: list[dict[str, Any]] = []
        receipts: list[dict[str, Any]] = []
        for source in studies:
            study = {k: v for k, v in dict(source).items() if k not in {"fields", "coordinates"}}
            fields = {str(k): np.asarray(v, dtype=float) for k, v in dict(source.get("fields", {})).items()}
            coords = {str(k): np.asarray(v, dtype=float) for k, v in dict(source.get("coordinates", {})).items()}
            scale_values = {str(r["rule_id"]): self._scale_value(r, source) for r in rules}
            target_scale = 1.0
            for rid, exponent in target_exponents.items():
                target_scale *= float(scale_values[rid]) ** int(exponent)
            if not math.isfinite(target_scale) or abs(target_scale) <= 1e-14:
                raise ValueError("target scale is invalid")
            normalized_fields: dict[str, Any] = {}
            for name, arr in fields.items():
                if name == target_field:
                    normalized_fields[name] = (arr / target_scale).tolist()
                else:
                    rid = field_rule.get(name)
                    normalized_fields[name] = (arr / float(scale_values[rid])).tolist() if rid else arr.tolist()
            normalized_coords: dict[str, Any] = {}
            for name, arr in coords.items():
                rid = coordinate_rule.get(name)
                normalized_coords[name] = (arr / float(scale_values[rid])).tolist() if rid else arr.tolist()
            study["fields"] = normalized_fields
            study["coordinates"] = normalized_coords
            out.append(study)
            receipt = {
                "study_id": str(source.get("study_id", "")), "role": str(source.get("role", "")),
                "scale_values": scale_values, "target_scale": float(target_scale),
                "target_value_used_to_compute_scales": False,
            }
            receipt["digest"] = digest_payload(receipt)
            receipts.append(receipt)
        return out, receipts



class AutonomousMathematicalCandidateBirthEngine:
    """Open-ended, domain-neutral bootstrap for mathematical/scientific candidates.

    The engine exists to cross the *first-candidate* barrier from UNKNOWN.  It does
    not pick a named theorem-solving method and it never treats the currently
    registered Atlas axes as the solution space.  Instead it deterministically
    births research-local axes from the frozen problem statement, composes proof
    meta-primitives into representations of unbounded depth, and turns unresolved
    obligations into further born operations/axes on later epochs.

    Each invocation has a finite compute budget, but the search language has no
    fixed epoch, axis-count, interaction-order, representation-depth, or candidate
    ceiling.  Exhausting a run budget therefore yields a continuation receipt,
    never an epistemic conclusion.
    """

    component_id = AUTONOMOUS_CANDIDATE_BIRTH_COMPONENT_ID
    _SEED_META_PRIMITIVES = (
        "assume", "decompose", "construct", "bound", "compare", "localize",
        "transform", "compose", "project", "lift", "invariant", "limit",
        "refute", "glue", "dualize", "iterate",
    )
    _STOPWORDS = {
        "a","an","and","are","as","at","be","by","can","determine","do","does","either","for","from","have","if","in","into","is","it","let","no","not","of","on","one","only","or","the","then","there","to","use","with","without","all","any",
        "и","в","во","на","с","со","из","для","по","к","ко","о","об","от","до","не","ни","или","а","но","что","как","это","этот","эта","эти","все","любой","любая","любые","пусть","найти","найди","исследуй","определи","без","при","если","то",
    }

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "component": self.component_id,
            "authority": KERNEL_OWNER_ID,
            "input": "FROZEN_PROBLEM_STATEMENT_PLUS_OPTIONAL_PRIOR_CONTINUATION",
            "output": "RESEARCH_LOCAL_AXES_PLUS_GENERATED_PROOF_PROGRAM_CANDIDATES",
            "search_policy": {
                "registered_axis_space_is_ceiling": False,
                "registered_representation_catalog_is_ceiling": False,
                "axis_birth_cardinality": "ADAPTIVE",
                "multi_axis_birth": True,
                "higher_order_interaction_axes": True,
                "fixed_axis_count_per_epoch": None,
                "fixed_interaction_order_ceiling": None,
                "fixed_representation_depth_ceiling": None,
                "fixed_candidate_count_ceiling": None,
                "fixed_epoch_ceiling": None,
                "budget_exhaustion_is_epistemic_termination": False,
                "continuation_required_after_budget_exhaustion": True,
                "unresolved_obligations_may_birth_new_operations": True,
            },
            "claim_boundary": {
                "generated_candidate_is_theorem": False,
                "generated_axis_is_canonical_axis": False,
                "generated_representation_is_known_method_selection": False,
                "search_continuation_guarantees_eventual_solution": False,
                "internet_used_prefreeze": False,
            },
        }
        return _with_digest(payload)

    @staticmethod
    def _validate_continuation(question_digest: str, continuation: Mapping[str, Any] | None) -> dict[str, Any]:
        if not isinstance(continuation, Mapping):
            return {
                "question_digest": question_digest,
                "next_epoch": 0,
                "frontier_digest": None,
                "born_operation_seeds": [],
                "research_local_axis_ids": [],
                "unresolved_obligation_seeds": [],
                "representation_family_seeds": [],
            }
        row = dict(continuation)
        if row.get("question_digest") not in {None, question_digest}:
            raise ValueError("mathematical search continuation belongs to another problem")
        if row.get("digest"):
            expected = digest_payload({k: v for k, v in row.items() if k != "digest"})
            if row.get("digest") != expected:
                raise ValueError("mathematical search continuation digest mismatch")
        return {
            "question_digest": question_digest,
            "next_epoch": max(0, int(row.get("next_epoch", 0) or 0)),
            "frontier_digest": row.get("frontier_digest"),
            "born_operation_seeds": [str(x) for x in row.get("born_operation_seeds", ()) if str(x)],
            "research_local_axis_ids": [str(x) for x in row.get("research_local_axis_ids", ()) if str(x)],
            "unresolved_obligation_seeds": [dict(x) for x in row.get("unresolved_obligation_seeds", ()) if isinstance(x, Mapping)],
            "representation_family_seeds": [str(x) for x in row.get("representation_family_seeds", ()) if str(x)],
        }

    @classmethod
    def _statement_atoms(cls, question: str) -> list[str]:
        raw = re.findall(r"[0-9A-Za-zА-Яа-яЁё_]+|[∂∇Δ∞νλμΣΠ]+", str(question).casefold())
        seen: set[str] = set(); out: list[str] = []
        for token in raw:
            token = token.strip("_")
            if not token or token in cls._STOPWORDS:
                continue
            if len(token) == 1 and not token.isdigit() and token not in {"u","p","f","x","t","n"}:
                continue
            if token in seen:
                continue
            seen.add(token); out.append(token)
        return out

    @classmethod
    def _problem_structure(cls, question: str) -> dict[str, Any]:
        """Extract proof-relevant structure already evidenced by the frozen statement.

        This is a domain-neutral seed only: it does not choose a named theorem
        method and never limits later axis or representation birth.
        """
        text = str(question)
        low = text.casefold()
        roles: list[dict[str, Any]] = []
        def add(role: str, evidence: str) -> None:
            row={"role":role,"evidence":evidence.strip()[:240]}
            if row not in roles: roles.append(row)
        patterns = (
            ("UNIVERSAL_QUANTIFICATION", ("for every", "for all", "∀", "для любого", "для всех", "любой")),
            ("EXISTENTIAL_QUANTIFICATION", ("there exists", "exists", "∃", "существует", "найти", "построить")),
            ("NEGATED_EXISTENCE_OR_OBSTRUCTION", ("does not exist", "no solution", "¬", "не существует", "невозможно")),
            ("GLOBAL_PROPERTY", ("global", "globally", "глобаль")),
            ("LOCAL_PROPERTY", ("local", "locally", "локаль")),
            ("REGULARITY_OR_SMOOTHNESS", ("smooth", "regular", "analytic", "гладк", "регуляр", "аналит")),
            ("BOUNDEDNESS_OR_GROWTH", ("bounded", "finite energy", "growth", "огранич", "конечн", "рост")),
            ("SINGULARITY_OR_BREAKDOWN", ("singular", "blow-up", "breakdown", "сингуляр", "взрыв", "разруш")),
            ("UNIQUENESS", ("unique", "uniqueness", "единствен")),
            ("INVARIANCE_OR_CONSERVATION", ("invariant", "conservation", "preserve", "инвариант", "сохран")),
            ("LIMIT_OR_ASYMPTOTIC", ("limit", "asymptotic", "converge", "предел", "асимптот", "сход")),
            ("SCALE_OR_RENORMALIZATION", ("scale", "scaling", "rescale", "масштаб")),
            ("SYMMETRY_OR_EQUIVALENCE", ("symmetry", "equivalent", "симметр", "эквивал")),
            ("DEPENDENCY_OR_IMPLICATION", ("implies", "if", "then", "⇒", "если", "то")),
        )
        for role, needles in patterns:
            for needle in needles:
                if needle in low or needle in text:
                    add(role, needle); break
        symbols=[]
        for token in re.findall(r"[∂∇Δ∞νλμΣΠ]|[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё0-9_]*", text):
            if token.casefold() not in cls._STOPWORDS and token not in symbols:
                symbols.append(token)
        return {"roles":roles,"symbols":symbols[:96],"role_count":len(roles),"symbol_count":min(96,len(symbols))}

    @staticmethod
    def _statement_clauses(question: str) -> list[str]:
        """Split a frozen problem into reusable semantic claim fragments.

        The splitter is intentionally conservative.  It never invents missing
        mathematical content; it only exposes text already present in the
        frozen statement so later semantic compilation can bind proof
        obligations to an actual claim instead of a generic meta-label.
        """
        text = re.sub(r"\s+", " ", str(question)).strip()
        if not text:
            return []
        raw = re.split(r"(?<=[.!?;])\s+|\s+(?=(?:where|such that|provided that|subject to)\b)", text, flags=re.I)
        clauses: list[str] = []
        for part in raw:
            part = part.strip(" ;.")
            if len(part) < 4:
                continue
            if part not in clauses:
                clauses.append(part[:1200])
        return clauses or [text[:1200]]

    @classmethod
    def _semantic_targets(cls, question: str, structure: Mapping[str, Any]) -> list[dict[str, Any]]:
        """Bind proof-relevant roles to clauses actually present in the statement."""
        clauses = cls._statement_clauses(question)
        role_needles = {
            "UNIVERSAL_QUANTIFICATION": ("for every", "for all", "∀", "для любого", "для всех"),
            "EXISTENTIAL_QUANTIFICATION": ("there exists", "exists", "∃", "существует", "построить"),
            "NEGATED_EXISTENCE_OR_OBSTRUCTION": ("does not exist", "no solution", "¬", "не существует", "невозможно"),
            "GLOBAL_PROPERTY": ("global", "globally", "глобаль"),
            "LOCAL_PROPERTY": ("local", "locally", "локаль"),
            "REGULARITY_OR_SMOOTHNESS": ("smooth", "regular", "analytic", "гладк", "регуляр", "аналит"),
            "BOUNDEDNESS_OR_GROWTH": ("bounded", "finite energy", "growth", "norm", "огранич", "конечн", "рост", "норм"),
            "SINGULARITY_OR_BREAKDOWN": ("singular", "blow-up", "blowup", "breakdown", "сингуляр", "взрыв", "разруш"),
            "UNIQUENESS": ("unique", "uniqueness", "единствен"),
            "INVARIANCE_OR_CONSERVATION": ("invariant", "conservation", "preserve", "инвариант", "сохран"),
            "LIMIT_OR_ASYMPTOTIC": ("limit", "lim", "asymptotic", "converge", "предел", "асимптот", "сход"),
            "SCALE_OR_RENORMALIZATION": ("scale", "scaling", "rescale", "масштаб"),
            "SYMMETRY_OR_EQUIVALENCE": ("symmetry", "equivalent", "симметр", "эквивал"),
            "DEPENDENCY_OR_IMPLICATION": ("implies", " if ", " then ", "⇒", "если", " то "),
        }
        targets: list[dict[str, Any]] = []
        active_roles = [str(r.get("role")) for r in structure.get("roles", ()) if r.get("role")]
        for role in active_roles:
            needles = role_needles.get(role, ())
            chosen = next((c for c in clauses if any(n in (" " + c.casefold() + " ") or n in c for n in needles)), None)
            if chosen is None:
                chosen = clauses[0] if clauses else str(question)[:1200]
            row = {"role": role, "claim": chosen, "provenance": "FROZEN_PROBLEM_STATEMENT"}
            row["digest"] = digest_payload(row)
            if row not in targets:
                targets.append(row)
        if not targets:
            row = {"role": "FROZEN_GOAL", "claim": clauses[0] if clauses else str(question)[:1200], "provenance": "FROZEN_PROBLEM_STATEMENT"}
            row["digest"] = digest_payload(row)
            targets.append(row)
        return targets[:12]

    @staticmethod
    def _axis_row(*, axis_id: str, kind: str, epoch: int, components: Sequence[str], provenance: str) -> dict[str, Any]:
        core = {
            "axis_id": axis_id,
            "axis_kind": kind,
            "epistemic_state": "RESEARCH_LOCAL",
            "canonical": False,
            "born_epoch": int(epoch),
            "components": list(components),
            "provenance": provenance,
        }
        core["digest"] = digest_payload(core)
        return core

    @staticmethod
    def _born_operation(seed_payload: Mapping[str, Any]) -> str:
        return "born_op_" + digest_payload(dict(seed_payload))[:14]

    def search(
        self,
        *,
        question: str,
        continuation: Mapping[str, Any] | None = None,
        registered_axis_ids: Sequence[str] = (),
        required_domains: Sequence[str] = (),
        epoch_budget: int = 3,
        axis_birth_budget_per_epoch: int = 24,
        candidate_budget_per_epoch: int = 8,
    ) -> Mapping[str, Any]:
        text = str(question).strip()
        if not text:
            raise ValueError("question is required")
        epoch_budget = max(1, int(epoch_budget))
        axis_birth_budget_per_epoch = max(4, int(axis_birth_budget_per_epoch))
        candidate_budget_per_epoch = max(5, int(candidate_budget_per_epoch))
        qdigest = digest_payload(text)
        prior = self._validate_continuation(qdigest, continuation)
        start_epoch = int(prior["next_epoch"])
        atoms = self._statement_atoms(text)
        if not atoms:
            atoms = ["problem_statement"]
        structure = self._problem_structure(text)
        semantic_targets = self._semantic_targets(text, structure)

        # Registered coordinates are context only.  They are never the upper bound
        # of the search, and research-local births are never silently canonicalized.
        registered = [str(x) for x in registered_axis_ids if str(x)]
        cumulative_axis_rows: list[dict[str, Any]] = []
        known_axis_ids = list(dict.fromkeys(prior.get("research_local_axis_ids", ())))
        operation_alphabet = list(self._SEED_META_PRIMITIVES)
        operation_alphabet.extend(str(x) for x in prior.get("born_operation_seeds", ()) if str(x))
        operation_alphabet = list(dict.fromkeys(operation_alphabet))
        all_candidates: list[dict[str, Any]] = []
        epoch_rows: list[dict[str, Any]] = []
        born_operation_seeds: list[str] = []
        unresolved_seed_rows = [dict(x) for x in prior.get("unresolved_obligation_seeds", ()) if isinstance(x, Mapping)]
        representation_family_seeds = [str(x) for x in prior.get("representation_family_seeds", ()) if str(x)]

        for epoch in range(start_epoch, start_epoch + epoch_budget):
            axis_rows: list[dict[str, Any]] = []
            if epoch == 0 and not known_axis_ids:
                for role_row in structure.get("roles", ()):
                    if len(axis_rows) >= axis_birth_budget_per_epoch: break
                    role=str(role_row.get("role")); evidence=str(role_row.get("evidence"))
                    aid = "RAX-ROLE-" + digest_payload({"q": qdigest, "role": role, "evidence": evidence})[:18].upper()
                    axis_rows.append(self._axis_row(axis_id=aid, kind=role, epoch=epoch, components=(evidence,), provenance="FROZEN_PROBLEM_STRUCTURE"))
                atom_order = sorted(atoms, key=lambda token: digest_payload({"q": qdigest, "atom": token}))
                for token in atom_order:
                    if len(axis_rows) >= axis_birth_budget_per_epoch: break
                    aid = "RAX-ATOM-" + digest_payload({"q": qdigest, "token": token})[:18].upper()
                    axis_rows.append(self._axis_row(axis_id=aid, kind="STATEMENT_ATOM", epoch=epoch, components=(token,), provenance="FROZEN_PROBLEM_STATEMENT"))
            for obligation in unresolved_seed_rows[:axis_birth_budget_per_epoch]:
                if len(axis_rows) >= axis_birth_budget_per_epoch: break
                okind=str(obligation.get("kind", "UNRESOLVED_PROOF_OBLIGATION"))
                oid=str(obligation.get("obligation_id", digest_payload(obligation)[:12]))
                aid="RAX-GAP-" + digest_payload({"q":qdigest,"epoch":epoch,"obligation":obligation})[:18].upper()
                axis_rows.append(self._axis_row(axis_id=aid, kind="PROOF_GAP::"+okind, epoch=epoch, components=(oid,okind), provenance="UNRESOLVED_PROOF_OBLIGATION_RESIDUAL"))
                # Semantic compilation can explain *why* an obligation is not
                # executable yet.  Missing typed bindings are therefore allowed
                # to become research-local coordinates instead of collapsing to
                # one opaque BLOCKED state.
                for binding in obligation.get("missing_bindings", ()):
                    if len(axis_rows) >= axis_birth_budget_per_epoch:
                        break
                    binding = str(binding)
                    if not binding:
                        continue
                    bid = "RAX-BIND-" + digest_payload({"q":qdigest,"epoch":epoch,"oid":oid,"binding":binding})[:18].upper()
                    axis_rows.append(self._axis_row(axis_id=bid, kind="MISSING_TYPED_BINDING::"+binding, epoch=epoch, components=(oid,binding), provenance="SEMANTIC_PROOF_OBLIGATION_COMPILATION_GAP"))
                # Generated binding objects are concrete research-local content, not
                # merely names of missing slots.  They become their own coordinates
                # so later proof programs can test, refine or reject them.
                for obj in obligation.get("generated_binding_objects", ()):
                    if len(axis_rows) >= axis_birth_budget_per_epoch:
                        break
                    if not isinstance(obj, Mapping):
                        continue
                    obj_id = str(obj.get("object_id", ""))
                    binding = str(obj.get("binding", "UNKNOWN_BINDING"))
                    if not obj_id:
                        continue
                    bid = "RAX-BOBJ-" + digest_payload({"q":qdigest,"epoch":epoch,"oid":oid,"object":obj_id})[:18].upper()
                    axis_rows.append(self._axis_row(axis_id=bid, kind="BINDING_OBJECT::"+binding, epoch=epoch, components=(oid,obj_id,binding), provenance="SEMANTIC_BINDING_INVENTION"))
            # Always birth interaction coordinates.  Interaction order increases
            # with epoch and therefore has no global ceiling across continuation.
            pool = list(dict.fromkeys(known_axis_ids + [r["axis_id"] for r in axis_rows]))
            if not pool:
                pool = ["RAX-SEED-" + digest_payload({"q": qdigest, "i": i})[:18].upper() for i in range(min(8, len(atoms)))]
            order = max(2, min(len(pool), 2 + epoch)) if len(pool) >= 2 else 1
            skip = epoch * axis_birth_budget_per_epoch
            combos = itertools.islice(itertools.combinations(pool, order), skip, skip + axis_birth_budget_per_epoch)
            for components in combos:
                aid = "RAX-INT-" + digest_payload({"q": qdigest, "epoch": epoch, "components": components})[:18].upper()
                if aid in known_axis_ids or any(r["axis_id"] == aid for r in axis_rows):
                    continue
                axis_rows.append(self._axis_row(axis_id=aid, kind=f"INTERACTION_ORDER_{order}", epoch=epoch, components=components, provenance="OPEN_ENDED_DOVETAIL_INTERACTION_BIRTH"))
                if len(axis_rows) >= axis_birth_budget_per_epoch:
                    break
            for row in axis_rows:
                if row["axis_id"] not in known_axis_ids:
                    known_axis_ids.append(row["axis_id"])
            cumulative_axis_rows.extend(axis_rows)

            # Every unresolved epoch can invent additional operations from the
            # current gap structure.  These operation names are content-derived,
            # not chosen from a fixed known-method catalogue.
            gap_seed = {
                "question_digest": qdigest,
                "epoch": epoch,
                "prior_frontier_digest": prior.get("frontier_digest"),
                "axis_birth_digest": digest_payload([r["digest"] for r in axis_rows]),
            }
            semantic_gap_kinds = [str(x.get("kind", "unresolved")) for x in unresolved_seed_rows[:4]] or ["frontier_expansion"]
            for lane, gap_kind in enumerate(semantic_gap_kinds):
                born = "born_op::" + re.sub(r"[^a-z0-9_]+", "_", gap_kind.casefold()).strip("_")[:44] + "::" + digest_payload({**gap_seed, "lane": lane, "gap_kind":gap_kind})[:10]
                if born not in operation_alphabet:
                    operation_alphabet.append(born)
                    born_operation_seeds.append(born)

            depth = 2 + epoch
            epoch_candidates: list[dict[str, Any]] = []
            seen_signatures: set[str] = set()
            seed = int(qdigest[:12], 16) + epoch * 7919
            axis_pool = known_axis_ids or registered[:8]
            for j in range(candidate_budget_per_epoch * 4):
                if len(epoch_candidates) >= candidate_budget_per_epoch:
                    break
                sequence = tuple(
                    operation_alphabet[(seed + j * (k + 3) + k * k + 17 * epoch) % len(operation_alphabet)]
                    for k in range(depth)
                )
                signature = digest_payload({"ops": sequence, "depth": depth})
                if signature in seen_signatures:
                    continue
                seen_signatures.add(signature)
                if axis_pool:
                    width = min(len(axis_pool), max(2, min(8, 2 + (j % 7))))
                    start = (seed + j * 5) % len(axis_pool)
                    selected_axes = [axis_pool[(start + t * (j + 1)) % len(axis_pool)] for t in range(width)]
                    selected_axes = list(dict.fromkeys(selected_axes))
                else:
                    selected_axes = []
                focus_gap = unresolved_seed_rows[j % len(unresolved_seed_rows)] if unresolved_seed_rows else None
                semantic_target = semantic_targets[j % len(semantic_targets)] if semantic_targets else {"role":"FROZEN_GOAL","claim":text}
                family_id = "MREP-" + signature[:18].upper()
                obligations = [
                    {"obligation_id": "OB-ASSUMPTIONS-" + signature[:10].upper(), "kind": "ASSUMPTION_COMPATIBILITY", "status": "UNRESOLVED"},
                    {"obligation_id": "OB-INVARIANT-" + signature[10:20].upper(), "kind": "DERIVE_OR_REFUTE_REPRESENTATION_INVARIANT", "status": "UNRESOLVED", "semantic_claim": str(semantic_target.get("claim", text)), "semantic_role": str(semantic_target.get("role", "FROZEN_GOAL"))},
                    {"obligation_id": "OB-CEX-" + signature[20:30].upper(), "kind": "COUNTEREXAMPLE_OR_OBSTRUCTION_SEARCH", "status": "UNRESOLVED", "semantic_claim": str(semantic_target.get("claim", text)), "semantic_role": str(semantic_target.get("role", "FROZEN_GOAL"))},
                    {"obligation_id": "OB-GOAL-" + signature[30:40].upper(), "kind": "DERIVE_FROZEN_GOAL_OR_PROVE_BRANCH_IMPOSSIBLE", "status": "UNRESOLVED", "semantic_claim": text, "semantic_role": "FROZEN_GOAL"},
                ]
                if focus_gap is not None:
                    obligations.append({
                        "obligation_id":"OB-RESIDUAL-"+signature[40:50].upper(),
                        "kind":"RESOLVE_PRIOR_PROOF_GAP::"+str(focus_gap.get("kind","UNKNOWN")),
                        "status":"UNRESOLVED",
                        "source_obligation_id":focus_gap.get("obligation_id"),
                        "semantic_claim": str(focus_gap.get("semantic_claim") or semantic_target.get("claim") or text),
                        "semantic_role": str(focus_gap.get("semantic_role") or semantic_target.get("role") or "PROOF_GAP"),
                    })
                    # Binding objects born on the previous shell carry their own
                    # validation obligations.  Re-materialize a bounded subset in the
                    # active proof program so provenance/well-typedness can execute
                    # and the decisive discrimination obligation remains explicit.
                    for bval in list(focus_gap.get("binding_validation_obligations", ()))[:6]:
                        if not isinstance(bval, Mapping):
                            continue
                        row=dict(bval)
                        row["source_obligation_id"]=focus_gap.get("obligation_id")
                        row["source_binding_object_id"]=row.get("binding_object_id")
                        obligations.append(row)
                candidate_core = {
                    "candidate_id": "MATH-" + digest_payload({"q": qdigest, "epoch": epoch, "signature": signature, "axes": selected_axes})[:22].upper(),
                    "status": "UNRESOLVED_GENERATED_PROOF_PROGRAM",
                    "search_epoch": epoch,
                    "representation_family_id": family_id,
                    "representation_signature": {
                        "operation_sequence": list(sequence),
                        "composition_depth": depth,
                        "research_local_axis_ids": selected_axes,
                        "problem_structure_roles": [str(r.get("role")) for r in structure.get("roles", ())],
                        "semantic_target": dict(semantic_target),
                        "focus_prior_obligation": dict(focus_gap) if isinstance(focus_gap, Mapping) else None,
                        "fixed_named_method_selected": False,
                    },
                    "semantic_context": {
                        "frozen_problem_statement": text,
                        "problem_structure": structure,
                        "semantic_targets": semantic_targets,
                    },
                    "proof_obligations": obligations,
                    "statement": f"Generated proof-program {family_id} for frozen problem {qdigest[:16]}; theorem truth remains unresolved until all obligations are discharged.",
                    "falsification_criterion": "REJECT_THIS_CONCRETE_PROOF_FORM_ON_VERIFIED_DEPENDENCY_FAILURE_COUNTEREXAMPLE_OR_FORMAL_KERNEL_REJECTION",
                    "controlled_limits": [],
                    "claim_boundary": {
                        "theorem_proved": False,
                        "candidate_is_world_truth": False,
                        "known_method_selected_as_answer": False,
                        "research_local_axes_are_canonical": False,
                    },
                }
                candidate_core["digest"] = digest_payload(candidate_core)
                epoch_candidates.append(candidate_core)
                all_candidates.append(candidate_core)

            epoch_row = {
                "epoch": epoch,
                "representation_depth": depth,
                "operation_alphabet_size": len(operation_alphabet),
                "born_operation_ids": list(born_operation_seeds[-2:]),
                "research_local_axis_birth_count": len(axis_rows),
                "research_local_axis_ids": [r["axis_id"] for r in axis_rows],
                "candidate_count": len(epoch_candidates),
                "candidate_ids": [c["candidate_id"] for c in epoch_candidates],
                "unresolved_obligation_count": sum(len(c["proof_obligations"]) for c in epoch_candidates),
            }
            epoch_row["digest"] = digest_payload(epoch_row)
            epoch_rows.append(epoch_row)
            prior["frontier_digest"] = epoch_row["digest"]
            unresolved_seed_rows = []
            for cand in epoch_candidates:
                for ob in cand.get("proof_obligations", ()):
                    if isinstance(ob, Mapping) and ob.get("status") == "UNRESOLVED":
                        unresolved_seed_rows.append({
                            "obligation_id":ob.get("obligation_id"),
                            "kind":ob.get("kind"),
                            "candidate_id":cand.get("candidate_id"),
                            "representation_family_id":cand.get("representation_family_id"),
                            "semantic_claim":ob.get("semantic_claim"),
                            "semantic_role":ob.get("semantic_role"),
                            "missing_bindings": list(ob.get("missing_bindings", ())),
                            "generated_binding_objects": list(ob.get("generated_binding_objects", ())),
                            "binding_validation_obligations": list(ob.get("binding_validation_obligations", ())),
                        })
            unresolved_seed_rows = unresolved_seed_rows[:64]
            representation_family_seeds.extend(str(c.get("representation_family_id")) for c in epoch_candidates if c.get("representation_family_id"))
            representation_family_seeds = list(dict.fromkeys(representation_family_seeds))[-64:]

        continuation_core = {
            "question_digest": qdigest,
            "next_epoch": start_epoch + epoch_budget,
            "frontier_digest": digest_payload([row["digest"] for row in epoch_rows]),
            "born_operation_seeds": list(dict.fromkeys(operation_alphabet[len(self._SEED_META_PRIMITIVES):])),
            "research_local_axis_ids": list(known_axis_ids),
            "unresolved_obligation_seeds": unresolved_seed_rows,
            "representation_family_seeds": representation_family_seeds,
            "fixed_epoch_ceiling": None,
            "fixed_axis_count_ceiling": None,
            "fixed_representation_depth_ceiling": None,
            "search_complete": False,
            "termination_rule": "ONLY_VERIFIED_PROOF_VERIFIED_COUNTEREXAMPLE_PROVED_UNDECIDABILITY_OR_EXPLICIT_USER_STOP_CAN_END_EPISTEMIC_SEARCH",
        }
        continuation = {**continuation_core, "digest": digest_payload(continuation_core)}
        payload = {
            "schema": "phi-autonomous-mathematical-candidate-birth/v1",
            "component": self.component_id,
            "authority": KERNEL_OWNER_ID,
            "status": "OPEN_ENDED_MATHEMATICAL_FRONTIER_FROZEN",
            "question_digest": qdigest,
            "required_domains": list(dict.fromkeys(str(x) for x in required_domains if str(x))),
            "registered_axis_context_count": len(registered),
            "registered_axis_space_is_ceiling": False,
            "problem_atom_count": len(atoms),
            "problem_atoms": atoms,
            "problem_structure": structure,
            "semantic_targets": semantic_targets,
            "search_epoch_start": start_epoch,
            "search_epoch_count": epoch_budget,
            "epoch_receipts": epoch_rows,
            "research_local_axis_births": cumulative_axis_rows,
            "research_local_axis_birth_count": len(cumulative_axis_rows),
            "operation_alphabet": operation_alphabet,
            "born_operation_count": len(set(born_operation_seeds)),
            "candidates": all_candidates,
            "candidate_count": len(all_candidates),
            "continuation": continuation,
            "claim_boundary": {
                "search_budget_exhaustion_is_solution": False,
                "generated_candidate_is_proof": False,
                "generated_axis_is_canonical": False,
                "external_solution_used_prefreeze": False,
                "world_novelty_established": False,
                "eventual_solution_guaranteed": False,
            },
        }
        return _with_digest(payload)


class FormalMathematicalVerificationOwner:
    """Domain-neutral formal verification contour for mathematical claims.

    The owner is deliberately fail-closed.  It can certify only checks that it
    actually executes (exact symbolic identities and exhaustive finite domains)
    or a frozen artifact executed by an external proof kernel.  Dependency-graph
    structure, search for counterexamples and proof obligations are useful
    research evidence, but are never silently upgraded to a theorem proof.
    """

    owner_id = "FORMAL-MATHEMATICAL-VERIFICATION/1.0.0"
    schema = "phi-formal-mathematical-verification/v1"
    _KERNELS = ("LEAN", "COQ", "ISABELLE")

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": self.schema,
            "owner_id": self.owner_id,
            "authority": KERNEL_OWNER_ID,
            "scope": "DOMAIN_NEUTRAL_FORMALIZABLE_CLAIMS",
            "pipeline": "FROZEN_CLAIM->DEPENDENCY_DAG->LEMMA_GATES->COUNTEREXAMPLE_REGIONS->PROOF_OBLIGATIONS->FORMAL_KERNEL_HANDOFF",
            "internal_verifiers": ["EXACT_SYMBOLIC_IDENTITY", "FINITE_EXHAUSTIVE_BOOLEAN"],
            "external_kernel_handoff": list(self._KERNELS),
            "external_kernel_executor": {"LEAN": "LOCAL_BINARY_IF_AVAILABLE", "COQ": "HANDOFF_ONLY", "ISABELLE": "HANDOFF_ONLY"},
            "external_kernel_attestation": "PROVENANCE_AND_AXIOM_AUDIT_WITHOUT_LOCAL_VERIFICATION_PROMOTION",
            "memory_owner": "UNIVERSAL-PROOF-MECHANISM-MEMORY/1.0.0",
            "claim_boundary": {
                "dependency_graph_is_proof": False,
                "counterexample_search_without_witness_is_proof": False,
                "finite_search_proves_unbounded_claim": False,
                "unverified_lemma_may_be_promoted": False,
                "formal_kernel_success_must_bind_frozen_source": True,
                "external_formal_attestation_is_local_kernel_verification": False,
                "external_attestation_requires_pinned_source_toolchain_theorems_axioms_and_replay_evidence": True,
                "proof_mechanism_reuse_transfers_theorem_truth": False,
            },
        }
        return _with_digest(payload)

    @staticmethod
    def _proof_digest(proof_artifact: Mapping[str, Any]) -> str:
        return digest_payload(dict(proof_artifact))

    @staticmethod
    def _node_id(row: Mapping[str, Any]) -> str:
        return str(row.get("id", "")).strip()

    def decompose(self, proof_artifact: Mapping[str, Any]) -> Mapping[str, Any]:
        proof = dict(proof_artifact)
        theorem_id = str(proof.get("theorem_id", "")).strip()
        statement = str(proof.get("statement", "")).strip()
        assumptions = [dict(x) for x in proof.get("assumptions", ())]
        lemmas = [dict(x) for x in proof.get("lemmas", ())]
        conclusion_id = str(proof.get("conclusion_id", "")).strip()
        issues: list[str] = []
        if not theorem_id:
            issues.append("MISSING_THEOREM_ID")
        if not statement:
            issues.append("MISSING_THEOREM_STATEMENT")
        ids = [self._node_id(x) for x in assumptions + lemmas]
        if any(not x for x in ids):
            issues.append("EMPTY_NODE_ID")
        if len(ids) != len(set(ids)):
            issues.append("DUPLICATE_NODE_ID")
        nodes = {self._node_id(x): dict(x) for x in assumptions + lemmas if self._node_id(x)}
        kinds = {self._node_id(x): "ASSUMPTION" for x in assumptions if self._node_id(x)}
        kinds.update({self._node_id(x): "LEMMA" for x in lemmas if self._node_id(x)})
        deps: dict[str, list[str]] = {}
        assumption_ids = set(self._node_id(x) for x in assumptions if self._node_id(x))
        for node_id, row in nodes.items():
            raw = [] if node_id in assumption_ids else [str(x).strip() for x in row.get("depends_on", ()) if str(x).strip()]
            deps[node_id] = raw
            for dep in raw:
                if dep not in nodes:
                    issues.append(f"MISSING_DEPENDENCY:{node_id}:{dep}")
                if dep == node_id:
                    issues.append(f"SELF_DEPENDENCY:{node_id}")
        if conclusion_id not in nodes:
            issues.append("MISSING_OR_UNKNOWN_CONCLUSION_ID")
        elif kinds.get(conclusion_id) != "LEMMA":
            issues.append("CONCLUSION_MUST_BE_LEMMA")

        indegree = {node_id: 0 for node_id in nodes}
        children: dict[str, list[str]] = {node_id: [] for node_id in nodes}
        for node_id, parents in deps.items():
            for parent in parents:
                if parent in nodes:
                    indegree[node_id] += 1
                    children[parent].append(node_id)
        queue = sorted([node_id for node_id, degree in indegree.items() if degree == 0])
        topo: list[str] = []
        work = dict(indegree)
        while queue:
            current = queue.pop(0)
            topo.append(current)
            for child in sorted(children[current]):
                work[child] -= 1
                if work[child] == 0:
                    queue.append(child)
                    queue.sort()
        if len(topo) != len(nodes):
            issues.append("DEPENDENCY_CYCLE")

        closure: set[str] = set()
        if conclusion_id in nodes:
            stack = [conclusion_id]
            while stack:
                current = stack.pop()
                if current in closure:
                    continue
                closure.add(current)
                stack.extend(dep for dep in deps.get(current, ()) if dep in nodes)

        obligations = []
        for lemma in lemmas:
            lemma_id = self._node_id(lemma)
            if lemma_id and lemma_id in closure and not isinstance(lemma.get("verification"), Mapping):
                obligations.append({"lemma_id": lemma_id, "reason": "NO_VERIFICATION_METHOD_BOUND"})
        valid = not issues
        payload = {
            "schema": self.schema,
            "owner_id": self.owner_id,
            "status": "PROOF_DEPENDENCY_GRAPH_FROZEN" if valid else "PROOF_GRAPH_BLOCKED",
            "theorem_id": theorem_id,
            "statement": statement,
            "proof_artifact_digest": self._proof_digest(proof),
            "assumption_ids": sorted(assumption_ids),
            "lemma_ids": sorted(set(ids) - assumption_ids),
            "conclusion_id": conclusion_id,
            "dependencies": deps,
            "topological_order": topo if valid else [],
            "theorem_dependency_closure": [x for x in topo if x in closure] if valid else [],
            "unreferenced_nodes": sorted(set(nodes) - closure),
            "proof_obligations": obligations,
            "issues": sorted(set(issues)),
            "claim_boundary": {"dependency_graph_is_proof": False, "theorem_verified": False},
        }
        return _with_digest(payload)

    @staticmethod
    def _symbol_table(names: Sequence[str]) -> dict[str, Any]:
        import sympy as sp
        table = {str(name): sp.Symbol(str(name), real=True) for name in names}
        table.update({"sin": sp.sin, "cos": sp.cos, "exp": sp.exp, "log": sp.log, "sqrt": sp.sqrt,
                      "Abs": sp.Abs, "pi": sp.pi, "E": sp.E})
        return table

    def _verify_symbolic_identity(self, spec: Mapping[str, Any]) -> Mapping[str, Any]:
        import sympy as sp
        names = [str(x) for x in spec.get("symbols", ())]
        table = self._symbol_table(names)
        lhs_text = str(spec.get("lhs", "")).strip(); rhs_text = str(spec.get("rhs", "")).strip()
        if not lhs_text or not rhs_text:
            return {"status": "BLOCKED_EXACT_IDENTITY_MISSING_SIDE", "verified": False}
        try:
            lhs = sp.sympify(lhs_text, locals=table)
            rhs = sp.sympify(rhs_text, locals=table)
            reduced = sp.simplify(lhs - rhs)
            ok = bool(reduced == 0)
            return {
                "status": "VERIFIED_INTERNAL_EXACT" if ok else "REFUTED_INTERNAL_EXACT",
                "verified": ok,
                "method": "EXACT_SYMBOLIC_IDENTITY",
                "normalized_difference": str(reduced),
            }
        except Exception as exc:
            return {"status": "BLOCKED_EXACT_IDENTITY_PARSE", "verified": False, "error_type": type(exc).__name__}

    @staticmethod
    def _finite_points(variables: Mapping[str, Any], maximum_points: int) -> tuple[list[str], list[tuple[Any, ...]], bool]:
        names = sorted(str(k) for k in variables)
        domains: list[list[Any]] = []
        for name in names:
            values = list(variables.get(name, ()))
            if not values:
                return names, [], False
            domains.append(values)
        total = math.prod(len(v) for v in domains) if domains else 0
        if total > maximum_points:
            return names, list(itertools.islice(itertools.product(*domains), maximum_points)), False
        return names, list(itertools.product(*domains)), True

    def search_counterexample_regions(self, search_spec: Mapping[str, Any]) -> Mapping[str, Any]:
        import sympy as sp
        variables = dict(search_spec.get("variables", {}) or {})
        max_points = int(search_spec.get("maximum_points", 100000) or 100000)
        if max_points < 1:
            raise ValueError("maximum_points must be positive")
        names, points, exhaustive = self._finite_points(variables, max_points)
        table = self._symbol_table(names)
        assumptions_text = [str(x) for x in search_spec.get("assumptions", ())]
        claim_text = str(search_spec.get("claim", "")).strip()
        if not claim_text:
            return _with_digest({"schema": self.schema, "owner_id": self.owner_id, "status": "COUNTEREXAMPLE_SEARCH_BLOCKED_NO_CLAIM", "counterexample_found": False})
        try:
            assumptions = [sp.sympify(text, locals=table) for text in assumptions_text]
            claim = sp.sympify(claim_text, locals=table)
        except Exception as exc:
            return _with_digest({"schema": self.schema, "owner_id": self.owner_id, "status": "COUNTEREXAMPLE_SEARCH_BLOCKED_PARSE", "counterexample_found": False, "error_type": type(exc).__name__})
        admissible = 0
        witness = None
        for values in points:
            sub = {table[name]: sp.Rational(str(value)) if isinstance(value, (int, float)) else value for name, value in zip(names, values)}
            try:
                if assumptions and not all(bool(a.subs(sub)) for a in assumptions):
                    continue
                admissible += 1
                if not bool(claim.subs(sub)):
                    witness = {name: value for name, value in zip(names, values)}
                    break
            except Exception:
                continue
        found = witness is not None
        status = "COUNTEREXAMPLE_FOUND" if found else ("FINITE_REGION_EXHAUSTED_NO_COUNTEREXAMPLE" if exhaustive else "FINITE_REGION_PARTIALLY_SCANNED_NO_COUNTEREXAMPLE")
        payload = {
            "schema": self.schema,
            "owner_id": self.owner_id,
            "status": status,
            "search_id": str(search_spec.get("search_id", "")),
            "variables": {name: list(variables[name]) for name in names},
            "claim": claim_text,
            "assumptions": assumptions_text,
            "points_examined": len(points),
            "admissible_points_examined": admissible,
            "finite_region_exhausted": exhaustive and not found,
            "counterexample_found": found,
            "counterexample": witness,
            "claim_boundary": {
                "counterexample_refutes_claim_under_declared_assumptions": found,
                "no_counterexample_in_finite_region_proves_unbounded_claim": False,
            },
        }
        return _with_digest(payload)

    def _verify_finite_exhaustive(self, spec: Mapping[str, Any]) -> Mapping[str, Any]:
        search = self.search_counterexample_regions(spec)
        ok = search.get("status") == "FINITE_REGION_EXHAUSTED_NO_COUNTEREXAMPLE" and bool(spec.get("declared_domain_is_exactly_listed_points", False))
        return {
            "status": "VERIFIED_FINITE_EXHAUSTIVE" if ok else ("REFUTED_BY_COUNTEREXAMPLE" if search.get("counterexample_found") else "BLOCKED_FINITE_EXHAUSTIVE_NOT_COMPLETE"),
            "verified": ok,
            "method": "FINITE_EXHAUSTIVE_BOOLEAN",
            "search_receipt": search,
        }

    def verify(self, proof_artifact: Mapping[str, Any]) -> Mapping[str, Any]:
        proof = dict(proof_artifact)
        graph = self.decompose(proof)
        if graph.get("status") != "PROOF_DEPENDENCY_GRAPH_FROZEN":
            return _with_digest({
                "schema": self.schema, "owner_id": self.owner_id, "status": "FORMAL_VERIFICATION_BLOCKED_GRAPH",
                "proof_artifact_digest": self._proof_digest(proof), "graph": graph,
                "verified": False, "proof_obligations": graph.get("proof_obligations", []),
                "claim_boundary": {"theorem_verified": False},
            })
        assumptions = {self._node_id(x): dict(x) for x in proof.get("assumptions", ())}
        lemmas = {self._node_id(x): dict(x) for x in proof.get("lemmas", ())}
        closure = list(graph.get("theorem_dependency_closure", ()))
        results: dict[str, Mapping[str, Any]] = {}
        obligations: list[dict[str, Any]] = []
        for node_id in closure:
            if node_id in assumptions:
                results[node_id] = {"status": "DECLARED_ASSUMPTION", "verified": True, "is_proven_inside_artifact": False}
                continue
            lemma = lemmas[node_id]
            verification = dict(lemma.get("verification", {}) or {})
            method = str(verification.get("method", "")).upper()
            if method == "EXACT_SYMBOLIC_IDENTITY":
                receipt = self._verify_symbolic_identity(verification)
            elif method == "FINITE_EXHAUSTIVE_BOOLEAN":
                receipt = self._verify_finite_exhaustive(verification)
            else:
                receipt = {"status": "PROOF_OBLIGATION_UNRESOLVED", "verified": False, "method": method or None}
            results[node_id] = receipt
            if not receipt.get("verified"):
                obligations.append({"lemma_id": node_id, "statement": str(lemma.get("statement", "")), "method": method or None, "status": receipt.get("status")})
        conclusion_id = str(graph.get("conclusion_id", ""))
        conclusion_verified = bool(results.get(conclusion_id, {}).get("verified"))
        all_lemma_nodes = [node_id for node_id in closure if node_id in lemmas]
        all_verified = conclusion_verified and all(bool(results.get(node_id, {}).get("verified")) for node_id in all_lemma_nodes)
        status = "FORMAL_DERIVATION_VERIFIED_RELATIVE_TO_DECLARED_ASSUMPTIONS" if all_verified else "FORMAL_PROOF_OBLIGATIONS_REMAIN"
        payload = {
            "schema": self.schema,
            "owner_id": self.owner_id,
            "status": status,
            "proof_artifact_digest": self._proof_digest(proof),
            "dependency_graph_digest": graph.get("digest"),
            "verification_results": results,
            "proof_obligations": obligations,
            "verified": all_verified,
            "conclusion_verified": conclusion_verified,
            "declared_assumption_count": len(assumptions),
            "verified_lemma_count": sum(1 for node_id in all_lemma_nodes if results.get(node_id, {}).get("verified")),
            "required_lemma_count": len(all_lemma_nodes),
            "claim_boundary": {
                "verified_relative_to_declared_assumptions": all_verified,
                "declared_assumptions_proven_inside_artifact": False,
                "world_mathematical_novelty_established": False,
                "external_formal_kernel_executed": False,
            },
        }
        return _with_digest(payload)

    def prepare_formal_kernel_handoff(self, proof_artifact: Mapping[str, Any], *, target_kernel: str = "LEAN") -> Mapping[str, Any]:
        target = str(target_kernel).upper().strip()
        if target not in self._KERNELS:
            raise ValueError(f"unsupported target kernel: {target_kernel!r}")
        graph = self.decompose(proof_artifact)
        payload = {
            "schema": "phi-formal-kernel-handoff/v1",
            "owner_id": self.owner_id,
            "status": "FORMAL_KERNEL_HANDOFF_READY" if graph.get("status") == "PROOF_DEPENDENCY_GRAPH_FROZEN" else "FORMAL_KERNEL_HANDOFF_BLOCKED_GRAPH",
            "target_kernel": target,
            "proof_artifact_digest": self._proof_digest(proof_artifact),
            "dependency_graph_digest": graph.get("digest"),
            "theorem_id": graph.get("theorem_id"),
            "statement": graph.get("statement"),
            "assumptions": [dict(x) for x in proof_artifact.get("assumptions", ())],
            "ordered_lemmas": [dict(next(x for x in proof_artifact.get("lemmas", ()) if self._node_id(x) == node_id)) for node_id in graph.get("theorem_dependency_closure", ()) if node_id in set(graph.get("lemma_ids", ()))],
            "conclusion_id": graph.get("conclusion_id"),
            "proof_obligations": graph.get("proof_obligations", []),
            "source_generation_required": True,
            "frozen_before_kernel_execution": True,
            "claim_boundary": {"handoff_is_kernel_verification": False},
        }
        return _with_digest(payload)

    @staticmethod
    def _is_hex_digest(value: Any, *, lengths: tuple[int, ...] = (40, 64)) -> bool:
        text = str(value or "").strip()
        return len(text) in lengths and all(ch in "0123456789abcdefABCDEF" for ch in text)

    def verify_external_formal_attestation(self, attestation: Mapping[str, Any]) -> Mapping[str, Any]:
        """Audit a third-party formal-kernel replay without promoting it to local verification.

        The attestation is accepted only as provenance-bound *external evidence*.
        It must pin source identity and toolchain, enumerate theorem outcomes and
        actual axioms, and contain at least one digest-bound formal-kernel replay
        check.  Even a fully accepted attestation leaves ``verified=False`` and
        ``locally_kernel_verified=False``: only :meth:`run_lean_kernel` (or a
        future local kernel executor) can produce a local kernel-verification
        receipt.
        """
        doc = dict(attestation)
        attestation_id = str(doc.get("attestation_id", "")).strip()
        source = dict(doc.get("source_identity", {}) or {})
        toolchain = dict(doc.get("toolchain", {}) or {})
        provenance = dict(doc.get("provenance", {}) or {})
        theorem_rows = [dict(row) for row in doc.get("theorems", ()) if isinstance(row, Mapping)]
        replay_rows = [dict(row) for row in doc.get("replay_checks", ()) if isinstance(row, Mapping)]
        permitted_axioms = sorted({str(x).strip() for x in doc.get("permitted_axioms", ()) if str(x).strip()})
        issues: list[str] = []

        repository = str(source.get("repository", "")).strip()
        commit = str(source.get("commit", "")).strip()
        if not attestation_id:
            issues.append("MISSING_ATTESTATION_ID")
        if not repository:
            issues.append("MISSING_SOURCE_REPOSITORY")
        if not self._is_hex_digest(commit, lengths=(40, 64)):
            issues.append("SOURCE_COMMIT_NOT_IMMUTABLY_PINNED")
        kernel = str(toolchain.get("kernel", "")).upper().strip()
        version = str(toolchain.get("version", "")).strip()
        if kernel not in self._KERNELS:
            issues.append("UNSUPPORTED_OR_MISSING_FORMAL_KERNEL")
        if not version:
            issues.append("MISSING_TOOLCHAIN_VERSION")
        if not theorem_rows:
            issues.append("NO_ATTESTED_THEOREMS")
        if not permitted_axioms:
            issues.append("PERMITTED_AXIOM_SURFACE_NOT_DECLARED")

        theorem_ids: list[str] = []
        theorem_results: list[dict[str, Any]] = []
        unexpected_axioms: dict[str, list[str]] = {}
        for row in theorem_rows:
            theorem_id = str(row.get("theorem_id", "")).strip()
            theorem_ids.append(theorem_id)
            actual = sorted({str(x).strip() for x in row.get("actual_axioms", ()) if str(x).strip()})
            unexpected = sorted(set(actual) - set(permitted_axioms))
            accepted = row.get("accepted") is True
            if not theorem_id:
                issues.append("EMPTY_THEOREM_ID")
            if not accepted:
                issues.append(f"THEOREM_NOT_ACCEPTED:{theorem_id or '<empty>'}")
            if unexpected:
                unexpected_axioms[theorem_id or "<empty>"] = unexpected
                issues.append(f"UNEXPECTED_AXIOMS:{theorem_id or '<empty>'}")
            theorem_results.append({
                "theorem_id": theorem_id,
                "accepted": accepted,
                "actual_axioms": actual,
                "unexpected_axioms": unexpected,
            })
        if len([x for x in theorem_ids if x]) != len(set(x for x in theorem_ids if x)):
            issues.append("DUPLICATE_THEOREM_ID")

        audited_checks: list[dict[str, Any]] = []
        kernel_replay_count = 0
        for row in replay_rows:
            check_id = str(row.get("check_id", "")).strip()
            checker = str(row.get("checker", "")).strip()
            accepted = row.get("accepted") is True
            source_unchanged = row.get("source_unchanged") is True
            evidence_digest = str(row.get("evidence_digest", "")).strip()
            formal_kernel_evidence = row.get("formal_kernel_evidence") is True
            if formal_kernel_evidence and accepted and source_unchanged and self._is_hex_digest(evidence_digest, lengths=(64,)):
                kernel_replay_count += 1
            audited_checks.append({
                "check_id": check_id,
                "checker": checker,
                "accepted": accepted,
                "source_unchanged": source_unchanged,
                "formal_kernel_evidence": formal_kernel_evidence,
                "evidence_digest_valid": self._is_hex_digest(evidence_digest, lengths=(64,)),
                "evidence_digest": evidence_digest or None,
            })
        if not replay_rows:
            issues.append("NO_REPLAY_CHECKS")
        if kernel_replay_count < 1:
            issues.append("NO_DIGEST_BOUND_FORMAL_KERNEL_REPLAY_EVIDENCE")

        issuer = str(provenance.get("issuer", "")).strip()
        source_url = str(provenance.get("source_url", "")).strip()
        receipt_digest = str(provenance.get("receipt_digest", "")).strip()
        if not issuer:
            issues.append("MISSING_ATTESTATION_ISSUER")
        if not source_url:
            issues.append("MISSING_ATTESTATION_SOURCE_URL")
        if not self._is_hex_digest(receipt_digest, lengths=(64,)):
            issues.append("ATTESTATION_RECEIPT_NOT_SHA256_BOUND")

        accepted_external = not issues
        payload = {
            "schema": "phi-external-formal-kernel-attestation/v1",
            "owner_id": self.owner_id,
            "status": "EXTERNAL_FORMAL_ATTESTATION_ACCEPTED" if accepted_external else "EXTERNAL_FORMAL_ATTESTATION_REJECTED",
            "attestation_id": attestation_id,
            "attestation_input_digest": digest_payload(doc),
            "source_identity": {"repository": repository, "commit": commit},
            "toolchain": {"kernel": kernel, "version": version},
            "permitted_axioms": permitted_axioms,
            "theorem_results": theorem_results,
            "replay_checks": audited_checks,
            "kernel_replay_evidence_count": kernel_replay_count,
            "unexpected_axioms": unexpected_axioms,
            "provenance": {
                "issuer": issuer,
                "source_url": source_url,
                "receipt_digest": receipt_digest or None,
            },
            "issues": sorted(set(issues)),
            "external_attestation_accepted": accepted_external,
            "attested_kernel_acceptance": accepted_external,
            "verified": False,
            "locally_kernel_verified": False,
            "claim_boundary": {
                "external_attestation_is_local_kernel_verification": False,
                "external_attestation_establishes_theorem_truth_by_atlas": False,
                "source_statement_alignment_independently_verified_by_atlas": False,
                "formal_kernel_execution_replayed_in_current_runtime": False,
                "axiom_surface_audited_against_declared_permitted_set": True,
                "external_receipt_is_evidence_not_local_execution": True,
                "world_mathematical_novelty_established": False,
            },
        }
        return _with_digest(payload)

    def run_lean_kernel(self, *, handoff: Mapping[str, Any], source_path: str | Path, project_dir: str | Path | None = None, timeout_seconds: int = 120) -> Mapping[str, Any]:
        import hashlib
        import shutil
        import subprocess
        handoff_doc = dict(handoff)
        if handoff_doc.get("status") != "FORMAL_KERNEL_HANDOFF_READY" or str(handoff_doc.get("target_kernel")) != "LEAN":
            raise ValueError("a frozen LEAN handoff is required")
        expected_handoff_digest = digest_payload({k: v for k, v in handoff_doc.items() if k != "digest"})
        if handoff_doc.get("digest") != expected_handoff_digest:
            raise ValueError("formal kernel handoff digest mismatch")
        path = Path(source_path).resolve()
        if not path.is_file():
            raise FileNotFoundError(path)
        raw = path.read_bytes(); text = raw.decode("utf-8", errors="replace")
        source_digest = hashlib.sha256(raw).hexdigest()
        lowered = text.lower()
        proof_holes = sorted(token for token in ("sorry", "admit", "by_contra?", "exact?") if token in lowered)
        if proof_holes:
            return _with_digest({
                "schema": "phi-formal-kernel-execution/v1", "owner_id": self.owner_id,
                "status": "FORMAL_KERNEL_BLOCKED_PROOF_HOLE", "target_kernel": "LEAN",
                "handoff_digest": handoff_doc.get("digest"), "source_path": str(path), "source_digest": source_digest,
                "proof_hole_tokens": proof_holes, "verified": False,
                "claim_boundary": {"formal_kernel_verified": False, "world_novelty_established": False},
            })
        lean = shutil.which("lean"); lake = shutil.which("lake")
        if lean:
            command = [lean, str(path)]
        elif lake:
            command = [lake, "env", "lean", str(path)]
        else:
            return _with_digest({
                "schema": "phi-formal-kernel-execution/v1", "owner_id": self.owner_id,
                "status": "FORMAL_KERNEL_UNAVAILABLE", "target_kernel": "LEAN",
                "handoff_digest": handoff_doc.get("digest"), "source_path": str(path), "source_digest": source_digest,
                "verified": False,
                "claim_boundary": {"formal_kernel_verified": False, "world_novelty_established": False},
            })
        try:
            proc = subprocess.run(command, cwd=str(Path(project_dir).resolve()) if project_dir else None, capture_output=True, text=True, timeout=int(timeout_seconds), check=False)
            ok = proc.returncode == 0
            payload = {
                "schema": "phi-formal-kernel-execution/v1", "owner_id": self.owner_id,
                "status": "FORMAL_KERNEL_VERIFIED" if ok else "FORMAL_KERNEL_REJECTED",
                "target_kernel": "LEAN", "handoff_digest": handoff_doc.get("digest"),
                "source_path": str(path), "source_digest": source_digest,
                "command_executable": str(command[0]), "returncode": int(proc.returncode),
                "stdout_digest": hashlib.sha256(proc.stdout.encode("utf-8")).hexdigest(),
                "stderr_digest": hashlib.sha256(proc.stderr.encode("utf-8")).hexdigest(),
                "verified": ok,
                "claim_boundary": {"kernel_exit_zero_is_bound_to_exact_source_digest": ok, "world_novelty_established": False},
            }
            return _with_digest(payload)
        except subprocess.TimeoutExpired:
            return _with_digest({
                "schema": "phi-formal-kernel-execution/v1", "owner_id": self.owner_id,
                "status": "FORMAL_KERNEL_TIMEOUT", "target_kernel": "LEAN",
                "handoff_digest": handoff_doc.get("digest"), "source_path": str(path), "source_digest": source_digest,
                "verified": False,
                "claim_boundary": {"formal_kernel_verified": False, "world_novelty_established": False},
            })


class SemanticProofObligationCompiler:
    """Compile born mathematical claims into typed, executable proof schemas.

    The compiler is deliberately weaker than a theorem prover.  Its job is to
    turn natural/symbolic obligation text into an explicit formal contract:
    quantifiers, symbols, relations, semantic predicates and the bindings that
    are still missing.  Only claims whose semantics are sufficiently explicit
    are lowered automatically to an executable verifier.  Everything else
    remains typed-but-unresolved and therefore becomes causal input to later
    representation/observer/axis birth.

    No domain name (PDE, number theory, biology, ...) is used as a dispatch key.
    Compilation depends only on mathematical structure present in the frozen
    claim itself.
    """

    component_id = SEMANTIC_OBLIGATION_COMPILER_COMPONENT_ID
    schema = "phi-semantic-proof-obligation-compilation/v1"

    _PREDICATE_PATTERNS = (
        ("EXISTENCE", ("there exists", "exists", "∃", "существует")),
        ("NONEXISTENCE", ("does not exist", "no solution", "¬∃", "не существует", "невозможно")),
        ("UNIQUENESS", ("unique", "uniqueness", "единствен")),
        ("GLOBAL_PROPERTY", ("global", "globally", "глобаль")),
        ("LOCAL_PROPERTY", ("local", "locally", "локаль")),
        ("SMOOTHNESS_REGULARITY", ("smooth", "regular", "analytic", "гладк", "регуляр", "аналит")),
        ("BOUNDEDNESS", ("bounded", "finite energy", "norm", "огранич", "конечн", "норм")),
        ("GROWTH_DECAY", ("growth", "decay", "vanish", "рост", "убы", "затух")),
        ("SINGULARITY_BREAKDOWN", ("singular", "blow-up", "blowup", "breakdown", "сингуляр", "взрыв", "разруш")),
        ("LIMIT_ASYMPTOTIC", ("limit", "lim", "asymptotic", "converge", "предел", "асимптот", "сход")),
        ("INVARIANCE_CONSERVATION", ("invariant", "conservation", "preserve", "инвариант", "сохран")),
        ("SYMMETRY_EQUIVALENCE", ("symmetry", "equivalent", "симметр", "эквивал")),
        ("DIFFERENTIAL_STRUCTURE", ("∂", "∇", "Δ", "derivative", "gradient", "laplac", "производн", "градиент")),
        ("INTEGRAL_STRUCTURE", ("∫", "integral", "интеграл")),
    )

    _REQUIRED_BINDING_RULES = {
        "EXISTENCE": "WITNESS_OR_CONSTRUCTION_BINDING",
        "NONEXISTENCE": "OBSTRUCTION_OR_IMPOSSIBILITY_CERTIFICATE_BINDING",
        "UNIQUENESS": "EQUALITY_EQUIVALENCE_AND_COMPARISON_BINDING",
        "GLOBAL_PROPERTY": "GLOBAL_DOMAIN_AND_INTERVAL_BINDING",
        "LOCAL_PROPERTY": "LOCAL_NEIGHBOURHOOD_BINDING",
        "SMOOTHNESS_REGULARITY": "FUNCTION_SPACE_OR_REGULARITY_PREDICATE_BINDING",
        "BOUNDEDNESS": "NORM_OR_ENERGY_FUNCTIONAL_BINDING",
        "GROWTH_DECAY": "ASYMPTOTIC_RATE_OR_WEIGHT_BINDING",
        "SINGULARITY_BREAKDOWN": "BREAKDOWN_OR_BLOWUP_PREDICATE_BINDING",
        "LIMIT_ASYMPTOTIC": "LIMIT_TOPOLOGY_AND_CONVERGENCE_BINDING",
        "INVARIANCE_CONSERVATION": "INVARIANT_FUNCTIONAL_AND_EVOLUTION_BINDING",
        "SYMMETRY_EQUIVALENCE": "SYMMETRY_ACTION_OR_EQUIVALENCE_RELATION_BINDING",
        "DIFFERENTIAL_STRUCTURE": "DIFFERENTIAL_OPERATOR_AND_DOMAIN_BINDING",
        "INTEGRAL_STRUCTURE": "MEASURE_AND_INTEGRABILITY_BINDING",
    }

    _QUANTIFIER_PATTERNS = (
        ("FOR_ALL", ("for every", "for all", "∀", "для любого", "для всех")),
        ("EXISTS", ("there exists", "exists", "∃", "существует")),
    )

    @staticmethod
    def _normalize(text: str) -> str:
        value = str(text or "").strip()
        replacements = {
            "≤": "<=", "≥": ">=", "≠": "!=", "＝": "=", "−": "-", "×": "*", "·": "*",
            "²": "**2", "³": "**3", "^": "**",
            "\\leq": "<=", "\\le": "<=", "\\geq": ">=", "\\ge": ">=", "\\neq": "!=",
            "\\cdot": "*", "\\times": "*",
        }
        for src, dst in replacements.items():
            value = value.replace(src, dst)
        value = value.replace("$", "").replace("\\(", "").replace("\\)", "")
        value = re.sub(r"\s+", " ", value).strip()
        return value

    @staticmethod
    def _symbols(text: str) -> list[str]:
        # Preserve conventional one-letter mathematical variables and Greek
        # identifiers while filtering common prose.  The list is descriptive;
        # it never establishes a type by itself.
        stop = {
            "a","an","the","as","at","in","on","for","all","every","there","exists","such","that","with","and","or","if","then","is","are","be","prove","refute","show","find",
            "для","всех","любого","существует","если","то","доказать","опровергнуть","найти",
        }
        out: list[str] = []
        for token in re.findall(r"[A-Za-z_][A-Za-z0-9_]*|[α-ωΑ-Ωνλμσρτφψω]+", text):
            if token.casefold() in stop:
                continue
            if token not in out:
                out.append(token)
        return out[:96]

    @classmethod
    def _quantifiers(cls, text: str) -> list[dict[str, Any]]:
        low = text.casefold()
        rows: list[dict[str, Any]] = []
        for qtype, needles in cls._QUANTIFIER_PATTERNS:
            for needle in needles:
                if needle in low or needle in text:
                    rows.append({"quantifier": qtype, "evidence": needle})
                    break
        return rows

    @classmethod
    def _predicates(cls, text: str) -> list[str]:
        low = text.casefold()
        rows: list[str] = []
        for predicate, needles in cls._PREDICATE_PATTERNS:
            if any(needle in low or needle in text for needle in needles):
                rows.append(predicate)
        return rows

    @staticmethod
    def _finite_domains(text: str) -> dict[str, list[Any]]:
        domains: dict[str, list[Any]] = {}
        # x in {1,2,3}, x ∈ {-1, 0, 1}
        for match in re.finditer(r"\b([A-Za-z][A-Za-z0-9_]*)\s*(?:in|∈)\s*\{([^{}]+)\}", text):
            name = match.group(1)
            values: list[Any] = []
            good = True
            for raw in match.group(2).split(","):
                token = raw.strip()
                try:
                    if re.fullmatch(r"[-+]?\d+", token):
                        values.append(int(token))
                    elif re.fullmatch(r"[-+]?(?:\d+\.\d*|\d*\.\d+)", token):
                        values.append(float(token))
                    else:
                        good = False; break
                except Exception:
                    good = False; break
            if good and values:
                domains[name] = values
        return domains

    @staticmethod
    def _operator_tokens(text: str) -> list[str]:
        low = text.casefold()
        tokens: list[str] = []
        probes = (
            ("PARTIAL_DERIVATIVE", ("∂", "partial", "derivative", "производн")),
            ("NABLA", ("∇", "nabla")),
            ("LAPLACIAN", ("Δ", "laplacian", "laplace", "лаплас")),
            ("DIVERGENCE", ("div ", "div(", "divergence", "диверген")),
            ("GRADIENT", ("grad ", "grad(", "gradient", "градиент")),
            ("INTEGRAL", ("∫", "integral", "интеграл")),
            ("NORM", ("||", "norm", "норм")),
            ("LIMIT", ("lim", "limit", "предел")),
        )
        for name, needles in probes:
            if any(n in low or n in text for n in needles):
                tokens.append(name)
        if re.search(r"\([^)]*[A-Za-zα-ωΑ-Ωνλμσρτφψω][^)]*[\*·]\s*∇\s*\)", text):
            tokens.append("FIELD_OPERATOR_ACTION")
        return list(dict.fromkeys(tokens))

    @staticmethod
    def _function_symbols(text: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for match in re.finditer(r"\b([A-Za-z][A-Za-z0-9_]*)\s*\(([^()]*)\)", text):
            name = match.group(1)
            args = [a.strip() for a in match.group(2).split(",") if a.strip()]
            row = {"symbol": name, "arguments": args, "arity": len(args)}
            if row not in out:
                out.append(row)
        return out[:32]

    @staticmethod
    def _domain_mentions(text: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for match in re.finditer(r"\bR\*\*(\d+)\b|ℝ\s*(?:\*\*|\^)?\s*(\d+)", text):
            dim = next((g for g in match.groups() if g), None)
            row = {"kind": "EUCLIDEAN_SPACE", "dimension": int(dim) if dim else None, "source": match.group(0)}
            if row not in out:
                out.append(row)
        low = text.casefold()
        if "torus" in low or "тор" in low:
            out.append({"kind": "TORUS", "periodic": True, "source": "torus"})
        if "periodic" in low or "период" in low:
            out.append({"kind": "PERIODIC_DOMAIN", "periodic": True, "source": "periodic"})
        return out

    @classmethod
    def _explicit_relations(cls, text: str) -> list[dict[str, Any]]:
        """Extract relation fragments explicitly present in the frozen text.

        This is a source-preserving parser, not an equation solver.  It is used
        to construct formal obligation schemas and never upgrades a relation to
        a proved lemma.
        """
        normalized = cls._normalize(text)
        rows: list[dict[str, Any]] = []
        # Scalar constraints such as nu>0 or n=3.
        for m in re.finditer(r"\b([A-Za-zνλμσρτφψω][A-Za-z0-9_νλμσρτφψω]*)\s*(<=|>=|!=|=|<|>)\s*([-+]?\d+(?:\.\d+)?)", normalized):
            prefix = normalized[max(0, m.start()-12):m.start()].casefold()
            if re.search(r"(?:div|grad|laplacian)\s+$", prefix) or any(op in prefix[-4:] for op in ("∂", "∇", "Δ")):
                continue
            row = {"lhs": m.group(1), "op": m.group(2), "rhs": m.group(3), "source": m.group(0), "relation_kind": "SCALAR_CONSTRAINT"}
            if row not in rows:
                rows.append(row)

        # Operator-equation zones introduced by ordinary mathematical wording.
        for z in re.finditer(r"\b(?:satisfy|satisfies|such that|subject to)\b\s+(.+?)(?:[.;]|$)", normalized, flags=re.I):
            zone = z.group(1).strip()
            parts = re.split(r"\s+and\s+(?=(?:div\b|grad\b|laplacian\b|∂|∇|Δ|[A-Za-zνλμσρτφψω][A-Za-z0-9_νλμσρτφψω]*\s*[=<>]))", zone, flags=re.I)
            for part in parts:
                part = re.split(r"\s+with\s+", part, maxsplit=1, flags=re.I)[0].strip(" ,")
                matches = list(re.finditer(r"(?<![<>!=])(?:==|=|<=|>=|!=|<|>)(?![=])", part))
                if len(matches) != 1:
                    continue
                m = matches[0]
                lhs = part[:m.start()].strip(); rhs = part[m.end():].strip(); op = m.group(0)
                if not lhs or not rhs:
                    continue
                row = {
                    "lhs": lhs, "op": "=" if op == "==" else op, "rhs": rhs,
                    "source": part,
                    "relation_kind": "OPERATOR_EQUATION" if cls._operator_tokens(part) else "EXPLICIT_RELATION",
                    "operator_tokens": cls._operator_tokens(part),
                }
                if row not in rows:
                    rows.append(row)
        return rows[:32]

    @staticmethod
    def _relation(text: str) -> dict[str, Any] | None:
        """Extract one compact algebraic relation if the claim exposes it."""
        # Prefer the final math-like clause; this avoids lowering a hypothesis
        # such as ``nu > 0`` when the prose conclusion follows afterwards.
        chunks = [c.strip() for c in re.split(r"[;\n]", text) if c.strip()]
        mathish = re.compile(r"^[A-Za-z0-9_α-ωΑ-Ωνλμσρτφψω()+\-*/., <>=!]+$")
        for chunk in reversed(chunks):
            candidate = chunk
            candidate = re.sub(
                r"^(?:for all|for every)\s+[A-Za-z][A-Za-z0-9_]*\s*(?:in|∈)\s*\{[^{}]+\}\s*,\s*",
                "", candidate, flags=re.I,
            )
            # Remove a short leading quantifier phrase only when the remaining
            # text is still an explicit relation.
            candidate = re.sub(r"^(?:for all|for every)\s+[A-Za-z0-9_, ]+[:,]?\s*", "", candidate, flags=re.I)
            if len(candidate) > 320 or not mathish.match(candidate):
                continue
            matches = list(re.finditer(r"(?<![<>!=])(?:==|=|<=|>=|!=|<|>)(?![=])", candidate))
            if len(matches) != 1:
                continue
            m = matches[0]
            lhs = candidate[:m.start()].strip(); rhs = candidate[m.end():].strip(); op = m.group(0)
            if lhs and rhs:
                return {"lhs": lhs, "op": "=" if op == "==" else op, "rhs": rhs, "source": candidate}
        return None

    @staticmethod
    def _sympy_parseable(expr: str, symbols: Sequence[str]) -> bool:
        import sympy as sp
        table = {str(name): sp.Symbol(str(name), real=True) for name in symbols}
        table.update({"sin":sp.sin,"cos":sp.cos,"exp":sp.exp,"log":sp.log,"sqrt":sp.sqrt,"Abs":sp.Abs,"pi":sp.pi,"E":sp.E})
        try:
            sp.sympify(expr, locals=table)
            return True
        except Exception:
            return False

    def contract(self) -> Mapping[str, Any]:
        return _with_digest({
            "component": self.component_id,
            "authority": KERNEL_OWNER_ID,
            "input": "BORN_OBLIGATION_WITH_FROZEN_SEMANTIC_CLAIM",
            "output": "TYPED_FORMAL_SCHEMA_PLUS_EXECUTABLE_SPEC_OR_EXPLICIT_MISSING_BINDINGS",
            "automatic_lowerings": ["EXACT_SYMBOLIC_IDENTITY", "FINITE_EXHAUSTIVE_BOOLEAN", "COUNTEREXAMPLE_REGION_SEARCH"],
            "domain_specific_dispatch": False,
            "claim_boundary": {
                "typed_schema_is_proof": False,
                "missing_binding_is_false_claim": False,
                "natural_language_ambiguity_may_be_guessed": False,
                "automatic_lowering_requires_explicit_semantics": True,
            },
        })

    def compile(
        self,
        *,
        obligation: Mapping[str, Any],
        candidate: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        ob = dict(obligation); cand = dict(candidate)
        claim = str(ob.get("semantic_claim") or ob.get("statement") or "").strip()
        if not claim:
            ctx = dict(cand.get("semantic_context", {}) or {})
            claim = str(ctx.get("frozen_problem_statement", "")).strip()
        normalized = self._normalize(claim)
        if not normalized:
            return _with_digest({
                "schema": self.schema, "component": self.component_id,
                "status": "SEMANTIC_COMPILATION_BLOCKED_EMPTY_CLAIM",
                "obligation_id": str(ob.get("obligation_id", "")),
                "typed_schema": {}, "executable_verification": {}, "missing_bindings": ["SEMANTIC_CLAIM_BINDING"],
                "claim_boundary": {"typed_schema_is_proof": False},
            })

        quantifiers = self._quantifiers(normalized)
        predicates = self._predicates(normalized)
        symbols = self._symbols(normalized)
        relation = self._relation(normalized)
        finite_domains = self._finite_domains(normalized)
        operator_tokens = self._operator_tokens(normalized)
        function_symbols = self._function_symbols(normalized)
        domain_mentions = self._domain_mentions(normalized)
        explicit_relations = self._explicit_relations(normalized)
        missing_bindings = list(dict.fromkeys(self._REQUIRED_BINDING_RULES[p] for p in predicates if p in self._REQUIRED_BINDING_RULES))
        if operator_tokens and "OPERATOR_SYMBOL_SEMANTICS_BINDING" not in missing_bindings:
            missing_bindings.append("OPERATOR_SYMBOL_SEMANTICS_BINDING")
        if function_symbols and "FUNCTION_SIGNATURE_AND_CODOMAIN_BINDING" not in missing_bindings:
            missing_bindings.append("FUNCTION_SIGNATURE_AND_CODOMAIN_BINDING")
        executable: dict[str, Any] = {}

        if relation is not None:
            relation_symbols = [s for s in symbols if re.search(rf"\b{re.escape(s)}\b", relation["source"])]
            relation_symbols = relation_symbols or symbols
            lhs_ok = self._sympy_parseable(relation["lhs"], relation_symbols)
            rhs_ok = self._sympy_parseable(relation["rhs"], relation_symbols)
            if relation["op"] == "=" and lhs_ok and rhs_ok:
                executable = {
                    "method": "EXACT_SYMBOLIC_IDENTITY",
                    "symbols": relation_symbols,
                    "lhs": relation["lhs"],
                    "rhs": relation["rhs"],
                    "compiled_from_semantic_claim": True,
                }
                # An exact algebraic identity no longer needs the generic
                # prose-level predicate bindings for execution of this scoped
                # obligation.  They may still matter to the global theorem.
                missing_bindings = []
            elif relation["op"] in {"<", ">", "<=", ">=", "!=", "="} and finite_domains and lhs_ok and rhs_ok:
                claim_expr = f"({relation['lhs']}) {relation['op']} ({relation['rhs']})"
                universal = any(q.get("quantifier") == "FOR_ALL" for q in quantifiers)
                executable = {
                    "method": "FINITE_EXHAUSTIVE_BOOLEAN" if universal else "COUNTEREXAMPLE_REGION_SEARCH",
                    "search_id": "SEM-" + digest_payload({"claim": normalized, "domains": finite_domains})[:18].upper(),
                    "variables": finite_domains,
                    "claim": claim_expr,
                    "assumptions": [],
                    "declared_domain_is_exactly_listed_points": bool(universal),
                    "compiled_from_semantic_claim": True,
                }
                if universal:
                    missing_bindings = []

        typed_schema = {
            "claim": claim,
            "normalized_claim": normalized,
            "semantic_role": str(ob.get("semantic_role", "")),
            "quantifiers": quantifiers,
            "symbols": symbols,
            "relation": relation,
            "predicates": predicates,
            "finite_domains": finite_domains,
            "operator_tokens": operator_tokens,
            "function_symbols": function_symbols,
            "domain_mentions": domain_mentions,
            "explicit_relations": explicit_relations,
            "required_bindings": list(missing_bindings),
            "candidate_representation_family_id": cand.get("representation_family_id"),
        }

        # Produce a frozen formal-obligation skeleton even when the claim cannot
        # yet be executed.  This gives the proof kernel a stable dependency
        # object and makes missing semantics explicit instead of leaving the
        # born lemma as free prose.
        assumptions = []
        for i, rel in enumerate(explicit_relations, start=1):
            assumptions.append({
                "id": f"A{i}",
                "statement": str(rel.get("source", "")),
                "typed_relation": rel,
                "source": "FROZEN_PROBLEM_STATEMENT",
            })
        conclusion_id = "L-GOAL"
        formal_obligation_artifact = {
            "theorem_id": "SEMANTIC-OBLIGATION-" + digest_payload({"candidate":cand.get("candidate_id"),"obligation":ob.get("obligation_id"),"claim":claim})[:20].upper(),
            "statement": claim,
            "assumptions": assumptions,
            "lemmas": [{
                "id": conclusion_id,
                "statement": claim,
                "depends_on": [row["id"] for row in assumptions],
                "typed_schema_digest": digest_payload(typed_schema),
            }],
            "conclusion_id": conclusion_id,
        }
        status = "EXECUTABLE_SEMANTIC_SPEC_COMPILED" if executable else "TYPED_FORMAL_SCHEMA_COMPILED_REQUIRES_BINDINGS"
        return _with_digest({
            "schema": self.schema,
            "component": self.component_id,
            "status": status,
            "candidate_id": str(cand.get("candidate_id", "")),
            "obligation_id": str(ob.get("obligation_id", "")),
            "typed_schema": typed_schema,
            "formal_obligation_artifact": formal_obligation_artifact,
            "executable_verification": executable,
            "missing_bindings": list(missing_bindings),
            "claim_boundary": {
                "typed_schema_is_proof": False,
                "automatic_executable_spec_is_theorem_proof": False,
                "missing_binding_is_falsification": False,
                "semantic_claim_was_invented": False,
            },
        })


class SemanticBindingInventionEngine:
    """Invent research-local content for typed semantic binding gaps.

    The engine is deliberately not a catalogue selector.  It constructs
    parameterized mathematical objects from the frozen typed schema: operator
    signatures, function signatures, generated seminorm/energy families,
    invariant defects, witness/obstruction families and breakdown criteria.
    Objects invented here are hypotheses with validation obligations.  Only
    bindings explicitly recoverable from the frozen statement are marked
    GROUNDED; generated objects remain PROPOSED until separately discharged.
    """

    component_id = SEMANTIC_BINDING_INVENTION_COMPONENT_ID
    schema = "phi-semantic-binding-invention/v1"

    _OPERATOR_SIGNATURES = {
        "partial_derivative": {"arity": 2, "kind": "DIFFERENTIAL", "order": 1},
        "gradient": {"arity": 1, "kind": "DIFFERENTIAL", "order": 1},
        "divergence": {"arity": 1, "kind": "DIFFERENTIAL", "order": 1},
        "laplacian": {"arity": 1, "kind": "DIFFERENTIAL", "order": 2},
        "integral": {"arity": 2, "kind": "INTEGRAL", "order": 0},
    }

    @staticmethod
    def _object_id(binding: str, payload: Mapping[str, Any]) -> str:
        return "BINDOBJ-" + re.sub(r"[^A-Z0-9]+", "-", binding.upper()).strip("-")[:28] + "-" + digest_payload(dict(payload))[:14].upper()

    @staticmethod
    def _validation_obligations(binding: str, object_id: str, *, grounded: bool) -> list[dict[str, Any]]:
        rows = [{
            "kind": "BINDING_PROVENANCE_ALIGNMENT",
            "object_id": object_id,
            "criterion": "EXACTLY_DERIVED_FROM_FROZEN_STATEMENT" if grounded else "DOES_NOT_CONTRADICT_FROZEN_STATEMENT",
            "required_for_acceptance": True,
        }]
        if not grounded:
            rows.extend([
                {"kind": "BINDING_WELL_TYPEDNESS", "object_id": object_id, "required_for_acceptance": True},
                {"kind": "BINDING_DISCRIMINATION_OR_CLOSURE_GAIN", "object_id": object_id, "required_for_acceptance": True},
            ])
        return rows

    @staticmethod
    def _operator_semantics(typed: Mapping[str, Any]) -> dict[str, Any] | None:
        toks = [str(x) for x in typed.get("operator_tokens", ())]
        if not toks:
            return None
        rows=[]
        for tok in toks:
            key=tok.casefold().replace(" ", "_")
            sig = dict(SemanticBindingInventionEngine._OPERATOR_SIGNATURES.get(key, {}))
            if not sig:
                if "laplac" in key or tok == "Δ": sig={"arity":1,"kind":"DIFFERENTIAL","order":2}
                elif "div" in key: sig={"arity":1,"kind":"DIFFERENTIAL","order":1}
                elif "grad" in key or tok == "∇": sig={"arity":1,"kind":"DIFFERENTIAL","order":1}
                elif "partial" in key or tok == "∂": sig={"arity":2,"kind":"DIFFERENTIAL","order":1}
                elif "integr" in key or tok == "∫": sig={"arity":2,"kind":"INTEGRAL","order":0}
                else: sig={"arity":None,"kind":"UNINTERPRETED_OPERATOR","order":None}
            rows.append({"symbol":tok,**sig})
        return {"operator_signatures":rows,"source":"FROZEN_TYPED_SCHEMA"}

    @staticmethod
    def _function_signatures(typed: Mapping[str, Any]) -> dict[str, Any] | None:
        funcs=[dict(x) for x in typed.get("function_symbols", ()) if isinstance(x, Mapping)]
        if not funcs:
            return None
        domains=[str(x) for x in typed.get("domain_mentions", ())]
        out=[]
        for f in funcs:
            out.append({
                "function":f.get("name") or f.get("symbol"),
                "arguments":list(f.get("arguments", ()) or f.get("args", ())),
                "domain_evidence":domains,
                "codomain":"UNRESOLVED_UNLESS_EXPLICIT_IN_STATEMENT",
            })
        return {"function_signatures":out,"source":"FROZEN_TYPED_SCHEMA"}

    @staticmethod
    def _domain_binding(typed: Mapping[str, Any]) -> dict[str, Any] | None:
        domains=[str(x) for x in typed.get("domain_mentions", ()) if str(x)]
        if not domains:
            return None
        return {"domains":domains,"source":"FROZEN_TYPED_SCHEMA","global_vs_local":"GLOBAL" if "GLOBAL_PROPERTY" in typed.get("predicates",()) else "UNSPECIFIED"}

    @staticmethod
    def _generated_object(binding: str, typed: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
        funcs=[]
        for f in typed.get("function_symbols", ()):
            if isinstance(f, Mapping): funcs.append(str(f.get("name") or f.get("symbol") or "f"))
            else: funcs.append(str(f))
        funcs=list(dict.fromkeys(x for x in funcs if x)) or ["f"]
        ops=[str(x) for x in typed.get("operator_tokens", ()) if str(x)]
        domains=[str(x) for x in typed.get("domain_mentions", ()) if str(x)]
        seed={"binding":binding,"claim":typed.get("normalized_claim"),"functions":funcs,"operators":ops,"domains":domains,"family":candidate.get("representation_family_id")}
        oid=SemanticBindingInventionEngine._object_id(binding, seed)
        common={"object_id":oid,"binding":binding,"status":"PROPOSED_RESEARCH_LOCAL_BINDING","canonical":False,"source":"GENERATED_FROM_TYPED_GAP","parameters":[],"validation_obligations":SemanticBindingInventionEngine._validation_obligations(binding,oid,grounded=False)}
        if binding == "FUNCTION_SPACE_OR_REGULARITY_PREDICATE_BINDING":
            content={"object_type":"GENERATED_REGULARITY_SPACE_FAMILY","carrier_functions":funcs,"domain":domains or ["D"],"seminorm_generators":ops or ["identity"],"free_parameters":["derivative_order_s","integrability_p","weight_rho"],"membership_rule":"finite generated seminorm family under chosen parameters"}
        elif binding == "NORM_OR_ENERGY_FUNCTIONAL_BINDING":
            content={"object_type":"GENERATED_ENERGY_FUNCTIONAL_FAMILY","functions":funcs,"terms":[{"observable":o,"coefficient":f"w_{i}","power":f"q_{i}"} for i,o in enumerate((ops or ["identity"]),1)],"free_parameters":["weights_w","powers_q"],"functional_form":"sum_i w_i * Phi_i(functions)^q_i"}
        elif binding == "INVARIANT_FUNCTIONAL_AND_EVOLUTION_BINDING":
            content={"object_type":"GENERATED_INVARIANT_CANDIDATE","functional":"I_theta","state_functions":funcs,"evolution_operators":ops,"validation_target":"evolution_defect d/dt I_theta = 0 or signed monotonicity","free_parameters":["theta"]}
        elif binding in {"WITNESS_OR_CONSTRUCTION_BINDING","OBSTRUCTION_OR_IMPOSSIBILITY_CERTIFICATE_BINDING"}:
            content={"object_type":"GENERATED_WITNESS_OR_OBSTRUCTION_FAMILY","role":"WITNESS" if binding.startswith("WITNESS") else "OBSTRUCTION","functions":funcs,"domains":domains,"construction_parameters":["scale_lambda","amplitude_a","profile_phi"],"validation_target":"satisfy all frozen assumptions and target/contradiction predicate"}
        elif binding == "BREAKDOWN_OR_BLOWUP_PREDICATE_BINDING":
            content={"object_type":"GENERATED_BREAKDOWN_CRITERION_FAMILY","monitor_functional":"F_theta(state)","criterion":"limsup_{t -> T} F_theta(state(t)) = +infinity OR continuation_condition_fails","free_parameters":["theta","T"],"dependency":"requires norm/regularity binding"}
        elif binding == "EQUALITY_EQUIVALENCE_AND_COMPARISON_BINDING":
            content={"object_type":"GENERATED_COMPARISON_FUNCTIONAL","distance":"D_theta(u,v)","criterion":"D_theta(u,v)=0 implies selected equivalence relation","free_parameters":["theta"]}
        elif binding == "ASYMPTOTIC_RATE_OR_WEIGHT_BINDING":
            content={"object_type":"GENERATED_ASYMPTOTIC_WEIGHT_FAMILY","weight":"w_theta(x,t)","rate":"r_theta","validation_target":"weighted residual has improved asymptotic closure","free_parameters":["theta"]}
        elif binding == "LIMIT_TOPOLOGY_AND_CONVERGENCE_BINDING":
            content={"object_type":"GENERATED_CONVERGENCE_STRUCTURE","topology":"tau_theta","convergence_observable":"D_theta(x_n,x)","free_parameters":["theta"]}
        elif binding == "SYMMETRY_ACTION_OR_EQUIVALENCE_RELATION_BINDING":
            content={"object_type":"GENERATED_SYMMETRY_ACTION_FAMILY","action":"G_theta x state -> state","validation_target":"preserve frozen equations/relations","free_parameters":["theta"]}
        elif binding == "GLOBAL_DOMAIN_AND_INTERVAL_BINDING":
            content={"object_type":"GENERATED_GLOBAL_DOMAIN_INTERVAL_FAMILY","spatial_domain_evidence":domains,"time_interval":"I_theta","endpoint_policy":"research_local","free_parameters":["interval_endpoints_theta"],"validation_target":"contains every point required by the frozen global claim"}
        elif binding == "FUNCTION_SIGNATURE_AND_CODOMAIN_BINDING":
            content={"object_type":"GENERATED_FUNCTION_SIGNATURE_FAMILY","functions":funcs,"argument_evidence":[dict(x) for x in typed.get("function_symbols",()) if isinstance(x,Mapping)],"codomain":"Y_theta","free_parameters":["codomain_type_theta"],"validation_target":"all frozen operators/relations are well-typed"}
        elif binding in {"OPERATOR_SYMBOL_SEMANTICS_BINDING","DIFFERENTIAL_OPERATOR_AND_DOMAIN_BINDING"}:
            content={"object_type":"GENERATED_OPERATOR_SEMANTICS_FAMILY","operator_symbols":ops,"domain_evidence":domains,"signature_parameters":["arity_theta","order_theta","source_space_theta","target_space_theta"],"validation_target":"typed composition matches every frozen operator relation"}
        elif binding == "LOCAL_NEIGHBOURHOOD_BINDING":
            content={"object_type":"GENERATED_LOCAL_NEIGHBOURHOOD_FAMILY","center":"z0","radius":"r","geometry":"research_local","free_parameters":["z0","r"]}
        elif binding == "MEASURE_AND_INTEGRABILITY_BINDING":
            content={"object_type":"GENERATED_MEASURE_INTEGRABILITY_PAIR","measure":"mu_theta","integrability_exponent":"p","free_parameters":["theta","p"]}
        else:
            content={"object_type":"GENERATED_TYPED_BINDING_FAMILY","binding_role":binding,"functions":funcs,"operators":ops,"domains":domains,"free_parameters":["theta"]}
        row={**common,"content":content}
        row["digest"]=digest_payload(row)
        return row

    def contract(self) -> Mapping[str, Any]:
        return _with_digest({
            "component":self.component_id,
            "authority":KERNEL_OWNER_ID,
            "input":"TYPED_SEMANTIC_BINDING_GAPS",
            "output":"GROUNDED_BINDINGS_PLUS_GENERATED_RESEARCH_LOCAL_BINDING_OBJECTS",
            "fixed_domain_method_catalog":False,
            "claim_boundary":{
                "generated_binding_is_true":False,
                "generated_function_space_is_correct_space":False,
                "generated_invariant_is_invariant_before_validation":False,
                "grounded_binding_requires_frozen_statement_evidence":True,
                "binding_invention_may_close_theorem_without_discharge":False,
            },
        })

    def synthesize(self, *, semantic_compilation: Mapping[str, Any], obligation: Mapping[str, Any], candidate: Mapping[str, Any]) -> Mapping[str, Any]:
        sem=dict(semantic_compilation); typed=dict(sem.get("typed_schema",{}) or {})
        missing=[str(x) for x in sem.get("missing_bindings",()) if str(x)]
        grounded=[]; generated=[]; remaining=[]
        op_sem = self._operator_semantics(typed)
        op_complete = bool(op_sem) and all(row.get("kind") != "UNINTERPRETED_OPERATOR" for row in op_sem.get("operator_signatures", ()))
        direct={
            "OPERATOR_SYMBOL_SEMANTICS_BINDING": op_sem if op_complete else None,
            "DIFFERENTIAL_OPERATOR_AND_DOMAIN_BINDING": op_sem if op_complete and bool(typed.get("domain_mentions")) else None,
            # Function arguments or a spatial domain can be statement-grounded evidence,
            # but a binding that explicitly asks for a codomain or a global time
            # interval is not considered complete unless those are explicit.  The
            # current semantic compiler does not infer them by convention.
            "FUNCTION_SIGNATURE_AND_CODOMAIN_BINDING": None,
            "GLOBAL_DOMAIN_AND_INTERVAL_BINDING": None,
        }
        for binding in missing:
            payload=direct.get(binding)
            if payload:
                oid=self._object_id(binding,payload)
                row={"object_id":oid,"binding":binding,"status":"GROUNDED_FROM_FROZEN_STATEMENT","canonical":False,"source":"FROZEN_TYPED_SCHEMA","content":payload,"validation_obligations":self._validation_obligations(binding,oid,grounded=True)}
                row["digest"]=digest_payload(row); grounded.append(row)
            else:
                obj=self._generated_object(binding,typed,candidate); generated.append(obj); remaining.append(binding)
        validation=[]
        for obj in generated:
            for idx,v in enumerate(obj.get("validation_obligations",()),1):
                core={"obligation_id":"BVAL-"+digest_payload({"obj":obj["object_id"],"i":idx,"v":v})[:16].upper(),"kind":v.get("kind"),"binding":obj.get("binding"),"binding_object_id":obj.get("object_id"),"status":"UNRESOLVED","semantic_claim":typed.get("claim"),"semantic_role":"BINDING_VALIDATION","verification_target":v.get("criterion") or v.get("kind")}
                if v.get("kind") == "BINDING_PROVENANCE_ALIGNMENT":
                    core["verification"]={"method":"BINDING_OBJECT_PROVENANCE_ALIGNMENT","binding_object":obj,"frozen_claim":typed.get("claim")}
                elif v.get("kind") == "BINDING_WELL_TYPEDNESS":
                    core["verification"]={"method":"BINDING_OBJECT_WELL_TYPEDNESS","binding_object":obj}
                core["digest"]=digest_payload(core); validation.append(core)
        status="ALL_BINDINGS_GROUNDED" if missing and not remaining else ("BINDING_HYPOTHESES_GENERATED" if generated else "NO_BINDING_GAP")
        return _with_digest({
            "schema":self.schema,"component":self.component_id,"status":status,
            "candidate_id":candidate.get("candidate_id"),"obligation_id":obligation.get("obligation_id"),
            "grounded_bindings":grounded,"generated_binding_objects":generated,
            "binding_validation_obligations":validation,"remaining_unvalidated_bindings":remaining,
            "claim_boundary":{"generated_binding_is_discharged":False,"grounded_binding_is_theorem_proof":False,"binding_selection_is_final":False},
        })


class ProofObligationDischargeEngine:
    """Execute and prioritize born proof obligations without promoting guesses.

    This component closes the gap between open-ended candidate birth and the
    formal verifier.  It is domain-neutral: obligations carry executable specs
    or digest-bound evidence; the engine never contains a Navier–Stokes/PDE
    rule.  Only checks that actually run can be marked DISCHARGED.  Missing
    executable content remains UNRESOLVED and becomes causal input for the next
    axis/representation birth shell.
    """

    component_id = "PROOF-OBLIGATION-DISCHARGE/1.1.0-COMPONENT"

    def __init__(self, formal: "FormalMathematicalVerificationOwner", semantic_compiler: "SemanticProofObligationCompiler", binding_invention: "SemanticBindingInventionEngine") -> None:
        self.formal = formal
        self.semantic_compiler = semantic_compiler
        self.binding_invention = binding_invention

    def contract(self) -> Mapping[str, Any]:
        return _with_digest({
            "component": self.component_id,
            "authority": KERNEL_OWNER_ID,
            "input": "BORN_PROOF_OBLIGATIONS_PLUS_OPTIONAL_DIGEST_BOUND_EVIDENCE",
            "output": "DISCHARGED_REFUTED_OR_UNRESOLVED_OBLIGATIONS_PLUS_CLOSURE_GAIN",
            "execution_methods": [
                "SEMANTIC_AUTOCOMPILE_TO_EXECUTABLE_SPEC",
                "STRUCTURAL_ASSUMPTION_CONSISTENCY",
                "EXACT_SYMBOLIC_IDENTITY",
                "FINITE_EXHAUSTIVE_BOOLEAN",
                "COUNTEREXAMPLE_REGION_SEARCH",
                "FORMAL_PROOF_ARTIFACT",
                "ATTESTED_BOOLEAN_WITNESS",
                "BINDING_OBJECT_PROVENANCE_ALIGNMENT",
                "BINDING_OBJECT_WELL_TYPEDNESS",
            ],
            "selection_policy": "EXPECTED_THEOREM_CLOSURE_GAIN_PER_EXECUTION_COST",
            "semantic_compiler": self.semantic_compiler.component_id,
            "binding_invention": self.binding_invention.component_id,
            "claim_boundary": {
                "missing_executable_spec_is_discharged": False,
                "typed_but_unbound_schema_is_discharged": False,
                "no_counterexample_found_in_nonexhaustive_search_is_proof": False,
                "structural_consistency_proves_theorem": False,
                "external_evidence_without_digest_binding_is_accepted": False,
                "discharge_score_is_truth_probability": False,
            },
        })

    @staticmethod
    def _obligation_key(candidate: Mapping[str, Any], obligation: Mapping[str, Any]) -> tuple[str, str]:
        return str(candidate.get("candidate_id", "")), str(obligation.get("obligation_id", ""))

    @staticmethod
    def _priority(kind: str, *, has_spec: bool, dependency_weight: int = 1, prior_attempts: int = 0) -> float:
        base = {
            "ASSUMPTION_COMPATIBILITY": 0.95,
            "COUNTEREXAMPLE_OR_OBSTRUCTION_SEARCH": 0.90,
            "DERIVE_OR_REFUTE_REPRESENTATION_INVARIANT": 0.80,
            "DERIVE_FROZEN_GOAL_OR_PROVE_BRANCH_IMPOSSIBLE": 1.00,
        }.get(kind.split("::", 1)[0], 0.65)
        executable = 1.0 if has_spec else 0.18
        dep = 1.0 + min(4, max(0, int(dependency_weight) - 1)) * 0.12
        retry = 1.0 / (1.0 + 0.35 * max(0, int(prior_attempts)))
        return float(base * executable * dep * retry)

    @staticmethod
    def _evidence_index(evidence_rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
        out: dict[tuple[str, str], dict[str, Any]] = {}
        for raw in evidence_rows:
            if not isinstance(raw, Mapping):
                continue
            row = dict(raw)
            cid = str(row.get("candidate_id", "")); oid = str(row.get("obligation_id", ""))
            if not cid or not oid:
                continue
            digest = row.get("digest")
            if digest:
                expected = digest_payload({k: v for k, v in row.items() if k != "digest"})
                if digest != expected:
                    continue
            out[(cid, oid)] = row
        return out

    def compile_tasks(
        self,
        *,
        candidates: Sequence[Mapping[str, Any]],
        evidence_rows: Sequence[Mapping[str, Any]] = (),
        maximum_tasks: int = 64,
    ) -> Mapping[str, Any]:
        evidence = self._evidence_index(evidence_rows)
        tasks: list[dict[str, Any]] = []
        for cand_raw in candidates:
            cand = dict(cand_raw)
            cid = str(cand.get("candidate_id", ""))
            for ob_raw in cand.get("proof_obligations", ()):
                if not isinstance(ob_raw, Mapping):
                    continue
                ob = dict(ob_raw); oid = str(ob.get("obligation_id", "")); kind = str(ob.get("kind", ""))
                if ob.get("status") not in {None, "UNRESOLVED", "BLOCKED_MISSING_EXECUTABLE_SPEC"}:
                    continue
                bound = evidence.get((cid, oid), {})
                spec = dict(bound.get("verification", {}) or ob.get("verification", {}) or {})
                semantic_compilation = self.semantic_compiler.compile(obligation=ob, candidate=cand)
                binding_synthesis = self.binding_invention.synthesize(semantic_compilation=semantic_compilation, obligation=ob, candidate=cand)
                formal_artifact = dict(semantic_compilation.get("formal_obligation_artifact", {}) or {})
                semantic_formal_graph = self.formal.decompose(formal_artifact) if formal_artifact else {}
                if not spec and isinstance(semantic_compilation.get("executable_verification"), Mapping):
                    spec = dict(semantic_compilation.get("executable_verification", {}) or {})
                method = str(spec.get("method", "")).upper().strip()
                has_spec = bool(method) or kind == "ASSUMPTION_COMPATIBILITY"
                priority = self._priority(kind, has_spec=has_spec, dependency_weight=int(ob.get("dependency_weight", 1) or 1), prior_attempts=int(ob.get("attempt_count", 0) or 0))
                if has_spec:
                    task_status = "READY"
                elif semantic_compilation.get("status") == "TYPED_FORMAL_SCHEMA_COMPILED_REQUIRES_BINDINGS":
                    task_status = "BLOCKED_BINDING_HYPOTHESES_REQUIRE_VALIDATION" if binding_synthesis.get("generated_binding_objects") else "BLOCKED_TYPED_BINDINGS_REQUIRED"
                else:
                    task_status = "BLOCKED_MISSING_EXECUTABLE_SPEC"
                task = {
                    "task_id": "DTASK-" + digest_payload({"candidate": cid, "obligation": oid, "spec": spec})[:20].upper(),
                    "candidate_id": cid,
                    "obligation_id": oid,
                    "kind": kind,
                    "method": method or ("STRUCTURAL_ASSUMPTION_CONSISTENCY" if kind == "ASSUMPTION_COMPATIBILITY" else "EXECUTABLE_SPEC_REQUIRED"),
                    "priority": priority,
                    "verification": spec,
                    "semantic_compilation": semantic_compilation,
                    "binding_synthesis": binding_synthesis,
                    "semantic_formal_graph": semantic_formal_graph,
                    "evidence_digest": bound.get("digest"),
                    "status": task_status,
                }
                task["digest"] = digest_payload(task)
                tasks.append(task)
        tasks.sort(key=lambda row: (-float(row["priority"]), row["task_id"]))
        tasks = tasks[:max(1, int(maximum_tasks))]
        return _with_digest({
            "schema": "phi-proof-obligation-task-compiler/v1",
            "component": self.component_id,
            "status": "PROOF_OBLIGATION_TASK_PORTFOLIO_FROZEN",
            "task_count": len(tasks),
            "ready_task_count": sum(1 for t in tasks if t["status"] == "READY"),
            "blocked_task_count": sum(1 for t in tasks if t["status"] != "READY"),
            "tasks": tasks,
        })

    def _execute_task(self, task: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
        method = str(task.get("method", "")).upper()
        spec = dict(task.get("verification", {}) or {})
        if method == "STRUCTURAL_ASSUMPTION_CONSISTENCY":
            # This only checks the generated program for internal bookkeeping
            # contradictions.  It does not establish any mathematical lemma.
            sig = dict(candidate.get("representation_signature", {}) or {})
            axes = [str(x) for x in sig.get("research_local_axis_ids", ())]
            ops = [str(x) for x in sig.get("operation_sequence", ())]
            ok = bool(axes) and bool(ops) and len(axes) == len(set(axes))
            return {
                "status": "DISCHARGED_STRUCTURAL_COMPATIBILITY" if ok else "REFUTED_STRUCTURAL_INCONSISTENCY",
                "discharged": ok,
                "branch_refuted": not ok,
                "mathematical_theorem_evidence": False,
                "method": method,
            }
        if method == "EXACT_SYMBOLIC_IDENTITY":
            rec = self.formal._verify_symbolic_identity(spec)
            return {"status": rec.get("status"), "discharged": bool(rec.get("verified")), "branch_refuted": rec.get("status") == "REFUTED_INTERNAL_EXACT", "receipt": rec, "method": method}
        if method == "FINITE_EXHAUSTIVE_BOOLEAN":
            rec = self.formal._verify_finite_exhaustive(spec)
            return {"status": rec.get("status"), "discharged": bool(rec.get("verified")), "branch_refuted": rec.get("status") == "REFUTED_BY_COUNTEREXAMPLE", "receipt": rec, "method": method}
        if method == "COUNTEREXAMPLE_REGION_SEARCH":
            rec = self.formal.search_counterexample_regions(spec)
            found = bool(rec.get("counterexample_found"))
            return {"status": rec.get("status"), "discharged": found, "branch_refuted": found, "receipt": rec, "method": method}
        if method == "FORMAL_PROOF_ARTIFACT":
            art = dict(spec.get("proof_artifact", {}) or {})
            rec = self.formal.verify(art) if art else {"status": "PROOF_OBLIGATION_UNRESOLVED", "verified": False}
            return {"status": rec.get("status"), "discharged": bool(rec.get("verified")), "branch_refuted": False, "receipt": rec, "method": method}
        if method == "ATTESTED_BOOLEAN_WITNESS":
            accepted = spec.get("accepted") is True and bool(spec.get("witness_digest"))
            return {"status": "DISCHARGED_ATTESTED_WITNESS" if accepted else "BLOCKED_INVALID_ATTESTED_WITNESS", "discharged": accepted, "branch_refuted": bool(spec.get("branch_refuted", False)) if accepted else False, "method": method}
        if method == "BINDING_OBJECT_PROVENANCE_ALIGNMENT":
            obj=dict(spec.get("binding_object", {}) or {})
            claim=str(spec.get("frozen_claim", "")).strip()
            ok=bool(obj.get("object_id")) and obj.get("source") == "GENERATED_FROM_TYPED_GAP" and bool(claim) and obj.get("canonical") is False
            return {"status":"DISCHARGED_BINDING_PROVENANCE_ALIGNMENT" if ok else "REFUTED_BINDING_PROVENANCE_ALIGNMENT","discharged":ok,"branch_refuted":not ok,"mathematical_theorem_evidence":False,"method":method}
        if method == "BINDING_OBJECT_WELL_TYPEDNESS":
            obj=dict(spec.get("binding_object", {}) or {}); content=dict(obj.get("content", {}) or {})
            ok=bool(obj.get("object_id")) and bool(obj.get("binding")) and bool(content.get("object_type")) and obj.get("canonical") is False and bool(obj.get("validation_obligations"))
            return {"status":"DISCHARGED_BINDING_WELL_TYPEDNESS" if ok else "REFUTED_BINDING_WELL_TYPEDNESS","discharged":ok,"branch_refuted":not ok,"mathematical_theorem_evidence":False,"method":method}
        return {"status": "BLOCKED_MISSING_EXECUTABLE_SPEC", "discharged": False, "branch_refuted": False, "method": method or None}

    def discharge(
        self,
        *,
        candidates: Sequence[Mapping[str, Any]],
        evidence_rows: Sequence[Mapping[str, Any]] = (),
        execution_budget: int = 32,
    ) -> Mapping[str, Any]:
        portfolio = self.compile_tasks(candidates=candidates, evidence_rows=evidence_rows, maximum_tasks=max(1, int(execution_budget) * 4))
        candidate_map = {str(c.get("candidate_id", "")): dict(c) for c in candidates if isinstance(c, Mapping)}
        results: list[dict[str, Any]] = []
        executed = 0
        for task in portfolio.get("tasks", ()):
            if executed >= max(1, int(execution_budget)):
                break
            if task.get("status") != "READY":
                continue
            cand = candidate_map.get(str(task.get("candidate_id", "")), {})
            rec = self._execute_task(task, cand)
            row = {**dict(task), **rec, "executed": True}
            row["digest"] = digest_payload({k: v for k, v in row.items() if k != "digest"})
            results.append(row); executed += 1
        discharged_keys = {(r["candidate_id"], r["obligation_id"]) for r in results if r.get("discharged")}
        refuted_candidates = sorted({r["candidate_id"] for r in results if r.get("branch_refuted")})
        task_by_key = {
            (str(t.get("candidate_id", "")), str(t.get("obligation_id", ""))): dict(t)
            for t in portfolio.get("tasks", ()) if isinstance(t, Mapping)
        }
        total_obligations = sum(len(c.get("proof_obligations", ())) for c in candidate_map.values())
        unresolved_rows: list[dict[str, Any]] = []
        for cand in candidate_map.values():
            cid = str(cand.get("candidate_id", ""))
            for ob in cand.get("proof_obligations", ()):
                if not isinstance(ob, Mapping):
                    continue
                oid = str(ob.get("obligation_id", ""))
                if (cid, oid) in discharged_keys:
                    continue
                task = task_by_key.get((cid, oid), {})
                semantic = dict(task.get("semantic_compilation", {}) or {})
                binding_synthesis = dict(task.get("binding_synthesis", {}) or {})
                semantic_graph = dict(task.get("semantic_formal_graph", {}) or {})
                typed = dict(semantic.get("typed_schema", {}) or {})
                unresolved_rows.append({
                    "candidate_id": cid,
                    "obligation_id": oid,
                    "kind": ob.get("kind"),
                    "representation_family_id": cand.get("representation_family_id"),
                    "semantic_claim": ob.get("semantic_claim") or typed.get("claim"),
                    "semantic_role": ob.get("semantic_role") or typed.get("semantic_role"),
                    "semantic_compilation_status": semantic.get("status"),
                    "semantic_compilation_digest": semantic.get("digest"),
                    "semantic_formal_graph_digest": semantic_graph.get("digest"),
                    "semantic_formal_graph_status": semantic_graph.get("status"),
                    "typed_predicates": list(typed.get("predicates", ())),
                    "missing_bindings": list(binding_synthesis.get("remaining_unvalidated_bindings", semantic.get("missing_bindings", ()))),
                    "grounded_bindings": list(binding_synthesis.get("grounded_bindings", ())),
                    "generated_binding_objects": list(binding_synthesis.get("generated_binding_objects", ())),
                    "binding_validation_obligations": list(binding_synthesis.get("binding_validation_obligations", ())),
                })
        closure_gain = len(discharged_keys) / max(1, total_obligations)
        return _with_digest({
            "schema": "phi-proof-obligation-discharge/v1",
            "component": self.component_id,
            "status": "PROOF_OBLIGATION_DISCHARGE_EXECUTED",
            "portfolio_digest": portfolio.get("digest"),
            "execution_budget": max(1, int(execution_budget)),
            "executed_task_count": executed,
            "discharged_obligation_count": len(discharged_keys),
            "total_obligation_count": total_obligations,
            "closure_gain": float(closure_gain),
            "refuted_candidate_ids": refuted_candidates,
            "results": results,
            "unresolved_obligation_seeds": unresolved_rows[:128],
            "semantic_compilation": {
                "component": self.semantic_compiler.component_id,
                "typed_unresolved_count": sum(1 for row in unresolved_rows if row.get("semantic_compilation_status") == "TYPED_FORMAL_SCHEMA_COMPILED_REQUIRES_BINDINGS"),
                "unresolved_with_explicit_missing_bindings": sum(1 for row in unresolved_rows if row.get("missing_bindings")),
                "generated_binding_object_count": sum(len(row.get("generated_binding_objects", ())) for row in unresolved_rows),
                "grounded_binding_count": sum(len(row.get("grounded_bindings", ())) for row in unresolved_rows),
            },
            "claim_boundary": {
                "closure_gain_is_theorem_truth_probability": False,
                "unexecuted_or_blocked_obligation_is_discharged": False,
                "refuted_branch_refutes_global_problem": False,
                "theorem_closed": total_obligations > 0 and len(discharged_keys) == total_obligations and not refuted_candidates,
            },
        })


class MathematicalInventionKernel:
    def __init__(self, root: str|Path) -> None:
        self.root=Path(root); self.runtime=LawSpaceRuntime(self.root)
        self.unknown_unknown=UnknownUnknownRepresentationOwner(self.runtime)
        self.function_language=FunctionLanguageBirthEngine()
        self.operator_language=OperatorLanguageBirthEngine()
        self.scale_invariant=ScaleInvariantRepresentationBirthOwner()
        self.autonomous_candidate_birth=AutonomousMathematicalCandidateBirthEngine()
        self.primitive=PrimitiveSynthesisOwner(); self.morphism=MorphismDiscoveryOwner(); self.limit=ControlledLimitEngine()
        self.formal=FormalMathematicalVerificationOwner(self.root)
        self.semantic_obligation_compiler=SemanticProofObligationCompiler()
        self.semantic_binding_invention=SemanticBindingInventionEngine()
        self.proof_discharge=ProofObligationDischargeEngine(self.formal, self.semantic_obligation_compiler, self.semantic_binding_invention)

    def contract(self)->Mapping[str,Any]:
        payload={
            "schema":SCHEMA,"owner_id":KERNEL_OWNER_ID,
            "owners":{
                "unknown_unknown":UNKNOWN_OWNER_ID,
                "primitive_synthesis":PRIMITIVE_OWNER_ID,
                "morphism_discovery":MORPHISM_OWNER_ID,
                "controlled_limit":LIMIT_OWNER_ID,
            },
            "components":{"function_language_birth":"FUNCTION-LANGUAGE-BIRTH/1.0.0-COMPONENT","operator_language_birth":self.operator_language.component_id,"scale_invariant_representation_birth":self.scale_invariant.owner_id,"autonomous_mathematical_candidate_birth":self.autonomous_candidate_birth.component_id,"semantic_proof_obligation_compiler":self.semantic_obligation_compiler.component_id,"semantic_binding_invention":self.semantic_binding_invention.component_id,"formal_mathematical_verification":self.formal.owner_id,"proof_obligation_discharge":self.proof_discharge.component_id},
            "pipeline":"UNKNOWN->OPEN_ENDED_CANDIDATE_BIRTH->SEMANTIC_OBLIGATION_COMPILATION->SEMANTIC_BINDING_INVENTION->BINDING_VALIDATION->PROOF_OBLIGATION_DISCHARGE->TYPED_BINDING_GAP_BIRTH->RESIDUAL_GAP_BIRTH->PHI_SCAN->REPRESENTATION_OBLIGATIONS->GENERATED_PRIMITIVE->MORPHISM->CONTROLLED_LIMIT->FORMAL_VERIFICATION",
            "function_language_pipeline":"QUERY_OOF_RESIDUAL->OPERATION_SIGNAL->GENERATED_LANGUAGE_SIGNATURE->QUERY_REFIT_AND_NULL",
            "operator_language_pipeline":"LOCAL_TRANSLATION_PLUS_POINTWISE_ALGEBRA->MOMENT_RANK_SHELLS->TYPED_SIGNATURES->EMPIRICAL_SUPPORT_SEARCH",
            "internet_prefreeze":"FORBIDDEN",
            "world_novelty":"NOT_ESTABLISHED_BY_MECHANISM_QUALIFICATION",
        }
        return _with_digest(payload)


__all__=[
    "MathematicalInventionKernel","UnknownUnknownRepresentationOwner","PrimitiveSynthesisOwner",
    "MorphismDiscoveryOwner","ControlledLimitEngine","FunctionLanguageBirthEngine","OperatorLanguageBirthEngine","ScaleInvariantRepresentationBirthOwner","AutonomousMathematicalCandidateBirthEngine","SemanticProofObligationCompiler","SemanticBindingInventionEngine","FormalMathematicalVerificationOwner","ProofObligationDischargeEngine", "KERNEL_OWNER_ID", "UNKNOWN_OWNER_ID",
    "PRIMITIVE_OWNER_ID","MORPHISM_OWNER_ID","LIMIT_OWNER_ID","SCALE_REPRESENTATION_OWNER_ID","AUTONOMOUS_CANDIDATE_BIRTH_COMPONENT_ID",
]
