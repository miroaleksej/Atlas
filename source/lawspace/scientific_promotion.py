"""Scientific Promotion Core v9.2.

The sole owner allowed to promote a proposed scientific model to LAW_CANDIDATE.
It does not generate models.  It adjudicates numerical evidence fail-closed.

Pipeline:
FRONTIER RECORD -> TYPED/MODEL BINDING -> CONVENTION AUDIT
-> KNOWN-DERIVABILITY AUDIT -> COLLAPSE/INVARIANCE -> REGIME OOD
-> CROSS-SYSTEM REPLICATION -> WHOLE-PIPELINE NULL
-> DISCRIMINATING EXPERIMENT -> NUMERIC PROMOTION CORE -> RECEIPT.

The numeric promotion core remains the sole adjudicator for a fully materialized
model.  The frontier path added in v9 is not a second scientific solver: it is
the common executable adapter that routes every persistent Atlas frontier record
through the same fail-closed promotion contract.  Missing evidence produces an
explicit pending gate and never means that the candidate is false.

A weighted score may rank models only after hard gates have passed.  No score,
LLM statement, literature novelty claim, or information-gain calculation can
resurrect a falsified/non-identifiable model.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.stats import chi2 as chi2_distribution

from .scientific_verification import (
    ScientificVerificationCore, IndependentArtifactVerifier, content_addressed_digest,
)

OWNER_ID = "SCIENTIFIC-PROMOTION-CORE"
OWNER_VERSION = "9.2.0"
SCHEMA = "phi-scientific-promotion/v9.2"
FRONTIER_PATH_SCHEMA = "phi-frontier-promotion-path/v2"
SYSTEM_STATUS = "RESEARCH_SYSTEM_UNDER_QUALIFICATION"
REQUIRED_ALTERNATIVE_ROLES = ("null", "simpler", "known_model", "mechanistic_competitor", "nonlinear_competitor")
FRONTIER_GATE_SEQUENCE = (
    "U0_RECORD_INTEGRITY",
    "U1_TYPED_HYPOTHESIS_BINDING",
    "U2_EXACT_DIMENSIONAL_QUALIFICATION",
    "U3_CONVENTION_ARTIFACT_AUDIT",
    "U4_KNOWN_DERIVABILITY_AUDIT",
    "U5_COLLAPSE_OR_INVARIANCE",
    "U6_DISTINCT_REGIME_OOD",
    "U7_CROSS_SYSTEM_REPLICATION",
    "U8_WHOLE_PIPELINE_PERMUTATION_NULL",
    "U9_DISCRIMINATING_EXPERIMENT",
    "U10_NUMERIC_PROMOTION_CORE",
)


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=float)


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


class ProvenanceLevel(str, Enum):
    DECLARED = "DECLARED"
    COMPUTED = "COMPUTED"
    WITNESSED = "WITNESSED"
    REPLICATED = "REPLICATED"


class IdentifiabilityStatus(str, Enum):
    PROPOSED = "PROPOSED"
    FIT_ONLY = "FIT_ONLY"
    LOCALLY_IDENTIFIED = "LOCALLY_IDENTIFIED"
    GLOBALLY_IDENTIFIED = "GLOBALLY_IDENTIFIED"
    REPLICATED = "REPLICATED"
    LAW_CANDIDATE = "LAW_CANDIDATE"
    FALSIFIED = "FALSIFIED"
    UNDERDETERMINED = "UNDERDETERMINED"
    NON_IDENTIFIABLE = "NON_IDENTIFIABLE"
    NEEDS_EXPERIMENT = "NEEDS_EXPERIMENT"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class PromotionConfig:
    absolute_fit_alpha: float = 1.0e-3
    comparative_delta_chi2_falsification: float = 9.0
    practical_singular_value_min: float = 1.0
    rank_relative_tolerance: float = 1.0e-10
    ood_absolute_fit_alpha: float = 1.0e-3
    replication_absolute_fit_alpha: float = 1.0e-3
    axis_complexity_lambda: float = 1.0
    whole_pipeline_null_alpha: float = 1.0e-2
    whole_pipeline_null_min_permutations: int = 200

    def validate(self) -> None:
        if not (0.0 < self.absolute_fit_alpha < 1.0):
            raise ValueError("absolute_fit_alpha must be in (0,1)")
        if self.comparative_delta_chi2_falsification <= 0.0:
            raise ValueError("comparative delta chi2 threshold must be positive")
        if self.practical_singular_value_min <= 0.0:
            raise ValueError("practical singular-value threshold must be positive")
        if not (0.0 < self.whole_pipeline_null_alpha < 1.0):
            raise ValueError("whole_pipeline_null_alpha must be in (0,1)")
        if self.whole_pipeline_null_min_permutations < 1:
            raise ValueError("whole_pipeline_null_min_permutations must be positive")




@dataclass(frozen=True)
class AxisScientificContract:
    axis_id: str
    name: str
    role: str
    units: str
    dimension: str
    domain: str
    uncertainty: str
    measurement_operator: str
    provenance: str
    prior: str
    causal_role: str
    falsification_value: str

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "AxisScientificContract":
        return cls(*(str(row.get(k, "")) for k in ("axis_id", "name", "role", "units", "dimension", "domain", "uncertainty", "measurement_operator", "provenance", "prior", "causal_role", "falsification_value")))

    def valid(self) -> bool:
        allowed_roles = {"observed", "latent", "generated", "nuisance"}
        return self.role in allowed_roles and all(str(v).strip() for v in dataclasses.astuple(self))


@dataclass(frozen=True)
class AxisOODValidation:
    axis_id: str
    base_log_likelihood_ood: float
    augmented_log_likelihood_ood: float
    additional_parameter_count: int = 1
    measurement_complexity: float = 0.0
    degrees_of_freedom_penalty: float = 0.0
    mechanism_absence_penalty: float = 0.0
    lambda_complexity: float = 1.0
    evidence_provenance: str = ""

    def score(self) -> float:
        complexity = (
            float(self.additional_parameter_count)
            + float(self.measurement_complexity)
            + float(self.degrees_of_freedom_penalty)
            + float(self.mechanism_absence_penalty)
        )
        return float(self.augmented_log_likelihood_ood - self.base_log_likelihood_ood - self.lambda_complexity * complexity)

    def to_result(self) -> Mapping[str, Any]:
        values = (self.base_log_likelihood_ood, self.augmented_log_likelihood_ood, self.measurement_complexity,
                  self.degrees_of_freedom_penalty, self.mechanism_absence_penalty, self.lambda_complexity)
        finite = all(math.isfinite(float(v)) for v in values)
        score = self.score() if finite else -math.inf
        accepted = bool(self.axis_id.strip()) and finite and bool(self.evidence_provenance.strip()) and score > 0.0
        return {
            "axis_id": self.axis_id,
            "delta_log_likelihood_ood": float(self.augmented_log_likelihood_ood - self.base_log_likelihood_ood) if finite else None,
            "complexity_penalty": float(self.lambda_complexity * (
                self.additional_parameter_count + self.measurement_complexity + self.degrees_of_freedom_penalty + self.mechanism_absence_penalty
            )) if finite else None,
            "score": score if finite else None,
            "status": "AXIS_PREDICTIVELY_VALIDATED" if accepted else "AXIS_NOT_PROMOTED_NO_OOD_GAIN",
            "epistemic_status": "OOD_SUPPORTED_CANDIDATE" if accepted else "UNVERIFIED_CANDIDATE",
            "candidate_is_false": False,
            "accepted": accepted,
            "evidence_provenance": self.evidence_provenance,
        }


@dataclass(frozen=True)
class DataPartition:
    y: tuple[float, ...]
    sigma: tuple[float, ...] | None
    regime_id: str
    provenance: str

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any] | None) -> "DataPartition | None":
        if row is None:
            return None
        sigma_raw = row.get("sigma")
        return cls(
            y=tuple(float(v) for v in row.get("y", ())),
            sigma=None if sigma_raw is None else tuple(float(v) for v in sigma_raw),
            regime_id=str(row.get("regime_id", "")),
            provenance=str(row.get("provenance", "")),
        )

    def integrity(self) -> Mapping[str, Any]:
        y = np.asarray(self.y, dtype=float)
        sigma = None if self.sigma is None else np.asarray(self.sigma, dtype=float)
        checks = {
            "NONEMPTY": y.size > 0,
            "FINITE_OBSERVATIONS": bool(y.size and np.all(np.isfinite(y))),
            "UNCERTAINTY_DECLARED": sigma is not None,
            "UNCERTAINTY_LENGTH_MATCH": bool(sigma is not None and sigma.size == y.size),
            "UNCERTAINTY_FINITE_POSITIVE": bool(sigma is not None and sigma.size == y.size and np.all(np.isfinite(sigma)) and np.all(sigma > 0.0)),
            "REGIME_DECLARED": bool(self.regime_id.strip()),
            "PROVENANCE_DECLARED": bool(self.provenance.strip()),
        }
        return {"checks": checks, "pass": all(checks.values())}


@dataclass(frozen=True)
class CandidateModel:
    candidate_id: str
    model_class: str
    equation: str
    parameters: tuple[str, ...]
    active_axes: tuple[str, ...]
    latent_axes: tuple[str, ...]
    assumptions: tuple[str, ...]
    units: str
    domain: str
    predictions_train: tuple[float, ...]
    predictions_ood: tuple[float, ...] = ()
    jacobian_train: tuple[tuple[float, ...], ...] = ()
    parameter_scales: tuple[float, ...] = ()
    dimension_lhs: tuple[str, ...] = ()
    dimension_rhs: tuple[str, ...] = ()
    complexity: float = 0.0
    model_version: str = "UNVERSIONED"
    provenance: str = ""

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "CandidateModel":
        return cls(
            candidate_id=str(row.get("candidate_id", "")), model_class=str(row.get("model_class", "")),
            equation=str(row.get("equation", "")), parameters=tuple(str(x) for x in row.get("parameters", ())),
            active_axes=tuple(str(x) for x in row.get("active_axes", ())), latent_axes=tuple(str(x) for x in row.get("latent_axes", ())),
            assumptions=tuple(str(x) for x in row.get("assumptions", ())), units=str(row.get("units", "")),
            domain=str(row.get("domain", "")), predictions_train=tuple(float(x) for x in row.get("predictions_train", ())),
            predictions_ood=tuple(float(x) for x in row.get("predictions_ood", ())),
            jacobian_train=tuple(tuple(float(v) for v in r) for r in row.get("jacobian_train", ())),
            parameter_scales=tuple(float(x) for x in row.get("parameter_scales", ())),
            dimension_lhs=tuple(str(x) for x in row.get("dimension_lhs", ())),
            dimension_rhs=tuple(str(x) for x in row.get("dimension_rhs", ())), complexity=float(row.get("complexity", 0.0)),
            model_version=str(row.get("model_version", "UNVERSIONED")), provenance=str(row.get("provenance", "")),
        )

    def declared_fields_ok(self) -> bool:
        return all(str(v).strip() for v in (self.candidate_id, self.model_class, self.equation, self.units, self.domain, self.model_version, self.provenance))


@dataclass(frozen=True)
class AlternativeModel:
    alternative_id: str
    role: str
    predictions_train: tuple[float, ...]
    model_class: str
    equation: str
    provenance: str

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "AlternativeModel":
        return cls(str(row.get("alternative_id", "")), str(row.get("role", "")),
                   tuple(float(x) for x in row.get("predictions_train", ())), str(row.get("model_class", "")), str(row.get("equation", "")), str(row.get("provenance", "")))


@dataclass(frozen=True)
class ReplicationEvidence:
    y: tuple[float, ...]
    sigma: tuple[float, ...] | None
    predictions: tuple[float, ...]
    regime_id: str
    provenance: str
    independent: bool

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any] | None) -> "ReplicationEvidence | None":
        if row is None:
            return None
        sigma_raw = row.get("sigma")
        return cls(tuple(float(x) for x in row.get("y", ())), None if sigma_raw is None else tuple(float(x) for x in sigma_raw),
                   tuple(float(x) for x in row.get("predictions", ())), str(row.get("regime_id", "")),
                   str(row.get("provenance", "")), bool(row.get("independent", False)))


class ScientificPromotionCore:
    owner_id = OWNER_ID

    def __init__(self, config: PromotionConfig | None = None, trusted_evidence_owners: Sequence[str] = ()) -> None:
        self.config = config or PromotionConfig()
        self.config.validate()
        self.trusted_evidence_owners = set(str(x) for x in trusted_evidence_owners) | {"SCIENTIFIC-PROMOTION-QUALIFICATION"}

    def contract(self) -> Mapping[str, Any]:
        return {
            "schema": SCHEMA,
            "owner": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "system_status_until_blind_ab_passes": SYSTEM_STATUS,
            "sole_scientific_promotion_owner": True,
            "unified_frontier_pipeline": list(FRONTIER_GATE_SEQUENCE),
            "numeric_pipeline": ["G_MINUS2_UNIFIED_FRONTIER_QUALIFICATION", "G_MINUS1_SCIENTIFIC_VERIFICATION", "G0_INPUT_INTEGRITY", "G1_DIMENSIONAL_CONSISTENCY", "G2_ABSOLUTE_FIT", "G3_ADVERSARIAL_COMPARISON", "G4_STRUCTURAL_IDENTIFIABILITY", "G5_PRACTICAL_IDENTIFIABILITY", "G6_REGIME_OOD", "G7_INDEPENDENT_REPLICATION", "RECEIPT"],
            "frontier_runtime_policy": {
                "every_persistent_frontier_candidate_gets_same_gate_sequence": True,
                "missing_evidence_is_false": False,
                "missing_evidence_status": "PENDING_OR_NEEDS_EXPERIMENT",
                "source_derived_candidate_is_false": False,
                "source_derived_candidate_new_law_promotion": False,
                "provisional_axis_routes_to_axis_promotion_not_law_promotion": True,
                "direct_numeric_evaluation_without_unified_frontier_receipt_can_reach_law_candidate": False,
                "whole_pipeline_null_required_before_law_candidate": True,
                "whole_pipeline_null_min_permutations": self.config.whole_pipeline_null_min_permutations,
                "whole_pipeline_null_alpha": self.config.whole_pipeline_null_alpha,
                "typed_relational_materialization_is_world_evidence": False,
                "typed_relational_materialization_can_skip_derivability_or_empirical_gates": False,
            },
            "required_alternative_roles": list(REQUIRED_ALTERNATIVE_ROLES),
            "hard_gate_policy": "FAILED_EARLIER_GATE_CANNOT_BE_RESURRECTED_BY_LATER_IDENTIFIABILITY_EIG_OR_SCORE",
            "uncertainty_policy": "UNKNOWN_UNCERTAINTY_BLOCKS_STATISTICAL_PROMOTION",
            "generated_axis_policy": "EACH_GENERATED_OR_LATENT_AXIS_REQUIRES_POSITIVE_COMPLEXITY_PENALISED_OOD_LOG_LIKELIHOOD_GAIN",
            "identifiability_policy": "FULL_RANK_IS_INSUFFICIENT; WHITENED_SCALED_SVD_SMIN_MUST_EXCEED_THRESHOLD",
            "ranking_policy": "WEIGHTED_SCORES_MAY_RANK_ONLY_HARD_GATE_SURVIVORS",
            "generic_evidence_verification_owner": "SCIENTIFIC-VERIFICATION-CORE/8.0.0",
            "world_promotion_requires_external_world_attestation": True,
            "serialized_verification_receipt_is_authorization": False,
            "provenance_levels": [x.value for x in ProvenanceLevel],
            "states": [x.value for x in IdentifiabilityStatus],
        }

    @staticmethod
    def _frontier_gate(status: str, *, passed: bool = False, evidence: Mapping[str, Any] | None = None,
                       reason: str = "", required: Sequence[str] = ()) -> Mapping[str, Any]:
        payload = {
            "status": str(status),
            "pass": bool(passed),
            "reason": str(reason),
            "required_evidence": [str(x) for x in required],
            "evidence": dict(evidence or {}),
        }
        payload["digest"] = _digest(payload)
        return payload

    def _validated_external_control(self, controls: Mapping[str, Any], key: str, *, pass_statuses: Sequence[str]) -> Mapping[str, Any] | None:
        row = controls.get(key)
        if not isinstance(row, Mapping):
            return None
        owner_id = str(row.get("owner_id", "")).strip()
        method = str(row.get("method", "")).strip()
        evidence_digest = str(row.get("evidence_digest", "")).strip()
        status = str(row.get("status", "")).strip()
        trusted = owner_id in self.trusted_evidence_owners or owner_id == OWNER_ID
        if not (owner_id and method and evidence_digest and trusted and status in set(pass_statuses)):
            return None
        return {
            "owner_id": owner_id,
            "method": method,
            "evidence_digest": evidence_digest,
            "status": status,
            "trusted_owner": True,
        }

    def _whole_pipeline_null_gate(self, controls: Mapping[str, Any]) -> Mapping[str, Any]:
        row = controls.get("whole_pipeline_null")
        if not isinstance(row, Mapping):
            return self._frontier_gate(
                "PENDING_WHOLE_PIPELINE_NULL",
                reason="The complete adaptive proposal-and-selection pipeline has not been replayed under a null target.",
                required=("observed_metric", "null_best_metrics", "pipeline_digest", "owner_id", "method", "evidence_digest"),
            )
        owner_id = str(row.get("owner_id", "")).strip()
        method = str(row.get("method", "")).strip()
        evidence_digest = str(row.get("evidence_digest", "")).strip()
        pipeline_digest = str(row.get("pipeline_digest", "")).strip()
        trusted = owner_id in self.trusted_evidence_owners
        try:
            observed = float(row.get("observed_metric"))
            null_scores = np.asarray(tuple(float(x) for x in row.get("null_best_metrics", ())), dtype=float)
        except (TypeError, ValueError):
            observed = math.nan
            null_scores = np.asarray((), dtype=float)
        smaller_is_better = bool(row.get("smaller_is_better", True))
        finite = bool(math.isfinite(observed) and null_scores.size and np.all(np.isfinite(null_scores)))
        n = int(null_scores.size)
        if finite:
            extreme = int(np.sum(null_scores <= observed)) if smaller_is_better else int(np.sum(null_scores >= observed))
            p_value = float((extreme + 1) / (n + 1))
        else:
            p_value = math.nan
        passed = bool(
            trusted and owner_id and method and evidence_digest and pipeline_digest and finite
            and n >= self.config.whole_pipeline_null_min_permutations
            and p_value <= self.config.whole_pipeline_null_alpha
        )
        evidence = {
            "owner_id": owner_id,
            "method": method,
            "evidence_digest": evidence_digest,
            "pipeline_digest": pipeline_digest,
            "trusted_owner": trusted,
            "observed_metric": observed if math.isfinite(observed) else None,
            "null_permutation_count": n,
            "empirical_p_value": p_value if math.isfinite(p_value) else None,
            "alpha": self.config.whole_pipeline_null_alpha,
            "minimum_permutations": self.config.whole_pipeline_null_min_permutations,
            "smaller_is_better": smaller_is_better,
        }
        return self._frontier_gate(
            "PASS_WHOLE_PIPELINE_NULL" if passed else "FAIL_OR_INCOMPLETE_WHOLE_PIPELINE_NULL",
            passed=passed,
            evidence=evidence,
            reason="Empirical null is computed from the best result of the complete adaptive pipeline, not from one frozen model.",
            required=() if passed else ("trusted owner", "complete pipeline digest", "at least configured permutation count", "empirical p <= alpha"),
        )

    @staticmethod
    def _frontier_record_core(record: Mapping[str, Any]) -> Mapping[str, Any]:
        return {k: v for k, v in dict(record).items() if k not in {"record_digest", "promotion_path"}}

    def materialize_relational_hypothesis(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        """Freeze a structural hypothesis for a fully typed adaptive subspace; invent no scalar law."""
        row=dict(record); payload=dict(row.get("payload",{}) or {}); candidate_id=str(row.get("candidate_id","")).strip()
        if str(row.get("candidate_class","")) != "ADAPTIVE_MULTIDIMENSIONAL_SUBSPACE_FRONTIER":
            return {"status":"HYPOTHESIS_MATERIALIZATION_NOT_APPLICABLE","candidate_id":candidate_id}
        axes=tuple(str(x) for x in payload.get("axis_ids",())); unbound=tuple(str(x) for x in payload.get("unbound_axis_ids",()))
        unbridged=tuple(tuple(str(y) for y in x) for x in payload.get("unbridged_domain_pairs",()))
        owners=tuple(str(x) for x in row.get("source_owner_ids",()))
        if not axes or unbound or unbridged or not owners:
            blocked={"schema":"phi-typed-relational-hypothesis/v1","owner":OWNER_ID,"owner_version":OWNER_VERSION,"candidate_id":candidate_id,"status":"HYPOTHESIS_MATERIALIZATION_BLOCKED_TYPED_BINDING","axis_ids":list(axes),"unbound_axis_ids":list(unbound),"unbridged_domain_pairs":[list(x) for x in unbridged],"source_owner_ids":list(owners)}
            return {**blocked,"digest":_digest(blocked)}
        core_digest=_digest(self._frontier_record_core(row)); experiment=dict(payload.get("discriminating_experiment",{}) or {})
        declared_families=[str(x) for x in payload.get("candidate_mechanism_families", payload.get("mechanism_families", ())) if str(x)]
        # Preserve the formal relational families used by U4 while carrying every
        # explicit competing mechanism frozen by the adaptive frontier.  A newer
        # hypothesis ledger therefore cannot make the older null/joint/regime
        # semantics disappear.
        families=list(dict.fromkeys([
            "OWNER_FACTORIZED_NULL", "JOINT_TYPED_INTERACTION", "REGIME_DEPENDENT_INTERACTION",
            *declared_families,
        ]))
        h={
            "schema":"phi-typed-relational-hypothesis/v1","owner":OWNER_ID,"owner_version":OWNER_VERSION,
            "candidate_id":candidate_id,"candidate_core_digest":core_digest,"status":"TYPED_RELATIONAL_HYPOTHESIS_MATERIALIZED",
            "representation_kind":"TYPED_RELATIONAL_INTERACTION_HYPOTHESIS","axis_ids":list(axes),
            "domain_ids":[str(x) for x in row.get("domain_ids",())],"source_owner_ids":list(owners),
            "null_family":"OWNER_FACTORIZED_OR_DIRECT_SUM_NULL","mechanism_families":families,"scalar_equation_frozen":False,
            "measurement_contract":{"experiment_digest":experiment.get("digest"),"protocol":experiment.get("intervention_or_sampling_protocol", experiment.get("protocol")),"required_controls":experiment.get("required_controls",[]),"response_observable_ids":list(experiment.get("response_observable_ids",[])),"world_result_observed":bool(experiment.get("world_result_observed",False))},
            "claim_boundary":{"new_law_established":False,"world_measurement_established":False,"novelty_established":False,"numeric_relation_established":False,"downstream_derivability_and_empirical_gates_still_required":True},
        }
        h["digest"]=_digest(h); return h

    def _validated_materialized_hypothesis(self, controls: Mapping[str, Any], *, candidate_id: str, candidate_core_digest: str) -> Mapping[str, Any] | None:
        row0=controls.get("materialized_hypothesis")
        if not isinstance(row0,Mapping): return None
        row=dict(row0); embedded=str(row.get("digest",""))
        if not embedded or embedded != _digest({k:v for k,v in row.items() if k!="digest"}): return None
        if str(row.get("owner"))!=OWNER_ID or str(row.get("owner_version"))!=OWNER_VERSION: return None
        if str(row.get("status"))!="TYPED_RELATIONAL_HYPOTHESIS_MATERIALIZED": return None
        if str(row.get("candidate_id"))!=candidate_id or str(row.get("candidate_core_digest"))!=candidate_core_digest: return None
        if str(row.get("representation_kind"))!="TYPED_RELATIONAL_INTERACTION_HYPOTHESIS": return None
        return row

    def audit_relational_known_derivability(
        self, hypothesis: Mapping[str, Any], *, accepted_owner_ids: Sequence[str]
    ) -> Mapping[str, Any]:
        """Formal U4 audit for a materialized relational *alternative family*.

        Source owners establish the factor coordinates used by the null family.
        They do not, merely by being present, entail a non-factorized joint or
        regime-dependent interaction.  This audit therefore answers only the
        precise U4 question for the frozen relational representation; it is not
        a novelty claim and does not assert that a quantitative law exists.
        """
        h=dict(hypothesis)
        embedded=str(h.get("digest",""))
        valid_digest=bool(embedded) and embedded==_digest({k:v for k,v in h.items() if k!="digest"})
        accepted={str(x) for x in accepted_owner_ids}
        sources=tuple(str(x) for x in h.get("source_owner_ids",()))
        checks={
            "HYPOTHESIS_DIGEST_VALID":valid_digest,
            "RELATIONAL_REPRESENTATION":str(h.get("representation_kind"))=="TYPED_RELATIONAL_INTERACTION_HYPOTHESIS",
            "NO_SCALAR_EQUATION_ASSERTED":h.get("scalar_equation_frozen") is False,
            "FACTORIZED_NULL_DECLARED":str(h.get("null_family"))=="OWNER_FACTORIZED_OR_DIRECT_SUM_NULL",
            "JOINT_ALTERNATIVE_DECLARED":"JOINT_TYPED_INTERACTION" in tuple(str(x) for x in h.get("mechanism_families",())),
            "SOURCE_OWNERS_ARE_ACCEPTED":bool(sources) and all(x in accepted for x in sources),
        }
        passed=all(checks.values())
        payload={
            "schema":"phi-known-derivability-audit/relational-v1",
            "owner_id":OWNER_ID,
            "method":"FORMAL_RELATIONAL_ALTERNATIVE_DERIVABILITY_AUDIT",
            "status":"PASS_NOT_DERIVED_FROM_ACCEPTED_LAWS" if passed else "BLOCKED_RELATIONAL_DERIVABILITY_AUDIT",
            "candidate_id":h.get("candidate_id"),
            "hypothesis_digest":embedded,
            "checks":checks,
            "source_owner_ids":list(sources),
            "logic":"accepted source owners establish typed factors/coordinates; no frozen accepted source theorem in this representation entails selection of the JOINT_TYPED_INTERACTION or REGIME_DEPENDENT_INTERACTION alternative",
            "claim_boundary":{
                "world_novelty_established":False,
                "quantitative_relation_established":False,
                "absence_from_literature_used":False,
                "u5_u10_empirical_gates_still_required":True,
            },
        }
        payload["evidence_digest"]=_digest(payload)
        payload["digest"]=_digest(payload)
        return payload

    def qualify_frontier_record(
        self,
        record: Mapping[str, Any],
        *,
        controls: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Execute the common pre-promotion path for one persistent frontier record.

        The method is intentionally evidence-conservative.  It may recognize a
        materialized representation or a frozen experiment blueprint from the
        candidate record, but it never invents uncertainty, OOD data, null
        replays, independent replication or world observations.  Those must be
        supplied as trusted, digest-bound controls.
        """
        controls = dict(controls or {})
        row = dict(record)
        payload = dict(row.get("payload", {}) or {})
        candidate_id = str(row.get("candidate_id", "")).strip()
        candidate_class = str(row.get("candidate_class", "")).strip()
        domain_ids = tuple(str(x) for x in row.get("domain_ids", ()))
        statuses = tuple(str(x) for x in row.get("epistemic_statuses", ()))
        source_owner_ids = tuple(str(x) for x in row.get("source_owner_ids", ()))
        core_payload = self._frontier_record_core(row)
        candidate_core_digest = _digest(core_payload)
        materialized_hypothesis = self._validated_materialized_hypothesis(controls, candidate_id=candidate_id, candidate_core_digest=candidate_core_digest)

        record_digest = str(row.get("record_digest", "")).strip()
        expected_record_digest = _digest({k: v for k, v in row.items() if k != "record_digest"}) if record_digest else ""
        record_digest_valid = (not record_digest) or record_digest == expected_record_digest
        active = "CANDIDATE_ACTIVE" in statuses
        u0_pass = bool(candidate_id and candidate_class and domain_ids and active and record_digest_valid)
        gates: dict[str, Mapping[str, Any]] = {
            "U0_RECORD_INTEGRITY": self._frontier_gate(
                "PASS_FRONTIER_RECORD_INTEGRITY" if u0_pass else "BLOCKED_FRONTIER_RECORD_INTEGRITY",
                passed=u0_pass,
                evidence={
                    "candidate_core_digest": candidate_core_digest,
                    "record_digest_present": bool(record_digest),
                    "record_digest_valid": record_digest_valid,
                    "candidate_active": active,
                },
                required=() if u0_pass else ("candidate_id", "candidate_class", "domain_ids", "CANDIDATE_ACTIVE", "valid record digest when present"),
            )
        }

        axis_route = candidate_class == "PROVISIONAL_RESEARCH_AXIS"
        source_derived = candidate_class in {"ALGEBRAIC_SOURCE_DERIVED_FRONTIER", "OPERATOR_COMPOSITION_FRONTIER"}
        if candidate_class == "ADAPTIVE_MULTIDIMENSIONAL_SUBSPACE_FRONTIER":
            axes = tuple(str(x) for x in payload.get("axis_ids", ()))
            unbound = tuple(str(x) for x in payload.get("unbound_axis_ids", ()))
            unbridged = tuple(tuple(str(y) for y in x) for x in payload.get("unbridged_domain_pairs", ()))
            typed = bool(axes and not unbound and not unbridged)
            materialized = bool(typed and materialized_hypothesis)
            typed_status = "PASS_TYPED_RELATIONAL_HYPOTHESIS_MATERIALIZED" if materialized else ("PASS_TYPED_SUBSPACE_BOUND_MODEL_NOT_YET_MATERIALIZED" if typed else "PENDING_TYPED_AXIS_OR_BRIDGE_BINDING")
            typed_reason = "A digest-bound typed relational hypothesis freezes the subspace, null family and discriminating measurement contract." if materialized else ("The scientific subspace is typed, but mechanism families are alternatives rather than one frozen equation/model." if typed else "One or more coordinates or cross-domain bridges remain unbound.")
        elif candidate_class == "CROSS_DOMAIN_AXIS_FRONTIER":
            axes = tuple(str(x) for x in payload.get("axes", ()))
            owner_groups = tuple(payload.get("owner_ids", ()))
            typed = bool(axes and payload.get("bridge_present") and owner_groups and all(bool(group) for group in owner_groups))
            materialized = False
            typed_status = "PASS_TYPED_CROSS_DOMAIN_REGION_MODEL_NOT_YET_MATERIALIZED" if typed else "PENDING_OWNER_OR_TYPED_BRIDGE_BINDING"
            typed_reason = "The pair is addressable as a typed research region; no unique mechanism/model has been frozen." if typed else "The cross-domain frontier lacks complete owner/bridge binding."
        elif candidate_class == "ALGEBRAIC_SOURCE_DERIVED_FRONTIER":
            materialized = bool(str(payload.get("polynomial", "")).strip() and source_owner_ids)
            typed = materialized
            typed_status = "PASS_FORMAL_ALGEBRAIC_REPRESENTATION_MATERIALIZED" if materialized else "PENDING_FORMAL_ALGEBRAIC_REPRESENTATION"
            typed_reason = "An exact source-derived polynomial representation is materialized." if materialized else "Formal polynomial/source binding is incomplete."
        elif candidate_class == "OPERATOR_COMPOSITION_FRONTIER":
            materialized = bool(str(payload.get("formula", "")).strip() and source_owner_ids)
            typed = materialized
            typed_status = "PASS_FORMAL_OPERATOR_REPRESENTATION_MATERIALIZED" if materialized else "PENDING_FORMAL_OPERATOR_REPRESENTATION"
            typed_reason = "A formal operator composition is materialized on a declared validity chart." if materialized else "Operator representation/source binding is incomplete."
        elif candidate_class == "REAL_DATA_MECHANISM_COMPETITION":
            materialized = bool(str(payload.get("formula_source", "")).strip() and str(payload.get("mechanism_family", "")).strip())
            typed = materialized and bool(source_owner_ids)
            typed_status = "PASS_REAL_DATA_MECHANISM_REPRESENTATION_MATERIALIZED" if typed else "PENDING_REAL_DATA_MECHANISM_BINDING"
            typed_reason = "A fitted mechanism family and formula source are present, but this is not yet a complete ScientificPromotionCore request." if typed else "Mechanism or source-owner binding is incomplete."
        elif axis_route:
            proposal = dict(payload.get("proposal", {}) or {})
            materialized = bool(str(proposal.get("axis_id", "")).strip() and str(proposal.get("measurement_protocol", "")).strip())
            typed = materialized
            typed_status = "PASS_PROVISIONAL_AXIS_MEASUREMENT_CONTRACT" if typed else "PENDING_PROVISIONAL_AXIS_MEASUREMENT_CONTRACT"
            typed_reason = "This record routes to dynamic-axis promotion; associated scientific claims still use the common evidence gates." if typed else "The provisional axis lacks a complete measurement contract."
        else:
            typed = False; materialized = False
            typed_status = "BLOCKED_UNKNOWN_FRONTIER_CLASS"; typed_reason = "No common frontier adapter exists for this candidate class."
        gates["U1_TYPED_HYPOTHESIS_BINDING"] = self._frontier_gate(
            typed_status, passed=typed,
            evidence={"materialized_model_or_coordinate": materialized, "source_owner_count": len(source_owner_ids), "materialized_hypothesis_digest": materialized_hypothesis.get("digest") if materialized_hypothesis else None},
            reason=typed_reason,
            required=() if typed else ("typed axis/owner/bridge or model binding",),
        )

        dim_control = self._validated_external_control(controls, "exact_dimensional_qualification", pass_statuses=("PASS_EXACT_7D_DIMENSIONAL_QUALIFICATION", "NOT_APPLICABLE_DIMENSIONLESS_WITH_JUSTIFICATION"))
        if dim_control:
            u2 = self._frontier_gate(dim_control["status"], passed=True, evidence=dim_control, reason="Trusted exact dimensional qualification supplied.")
        elif materialized_hypothesis:
            u2 = self._frontier_gate("NOT_APPLICABLE_RELATIONAL_REPRESENTATION_NO_SCALAR_EQUATION", passed=True, evidence={"hypothesis_digest":materialized_hypothesis.get("digest"),"representation_kind":materialized_hypothesis.get("representation_kind")}, reason="The materialized object is a typed relational interaction hypothesis, not a claimed dimensionally homogeneous scalar equation.")
        elif axis_route and str(payload.get("proposal", {}).get("units_or_normalization", "")).lower().startswith("dimensionless"):
            u2 = self._frontier_gate(
                "PENDING_EXACT_7D_OR_DIMENSIONLESS_JUSTIFICATION_RECEIPT",
                reason="The proposal declares a dimensionless ratio, but canonical promotion still requires a digest-bound dimensional/non-applicability receipt.",
                required=("exact 7D dimensional receipt or justified dimensionless non-applicability",),
            )
        elif not materialized:
            u2 = self._frontier_gate("BLOCKED_UNTIL_HYPOTHESIS_MATERIALIZED", reason="Exact dimensional qualification requires a frozen typed representation.")
        else:
            u2 = self._frontier_gate("PENDING_EXACT_7D_DIMENSIONAL_QUALIFICATION", reason="No trusted exact 7D dimensional receipt is bound to this frontier record.", required=("exact_dimensional_qualification",))
        gates["U2_EXACT_DIMENSIONAL_QUALIFICATION"] = u2

        convention = self._validated_external_control(controls, "convention_audit", pass_statuses=("PASS_CONVENTION_ROBUST", "NOT_APPLICABLE_WITH_JUSTIFICATION"))
        if convention:
            gates["U3_CONVENTION_ARTIFACT_AUDIT"] = self._frontier_gate(convention["status"], passed=True, evidence=convention, reason="Trusted convention/metrology audit supplied.")
        elif materialized_hypothesis and u2.get("pass"):
            gates["U3_CONVENTION_ARTIFACT_AUDIT"] = self._frontier_gate("NOT_APPLICABLE_RELATIONAL_REPRESENTATION_WITHOUT_UNIT_EQUATION", passed=True, evidence={"hypothesis_digest":materialized_hypothesis.get("digest")}, reason="No scalar unit equation has been asserted; convention testing becomes mandatory when a quantitative relation is later frozen.")
        elif not u2.get("pass"):
            gates["U3_CONVENTION_ARTIFACT_AUDIT"] = self._frontier_gate("BLOCKED_BY_DIMENSIONAL_QUALIFICATION", reason="Convention robustness is evaluated only after a typed dimensional representation exists.")
        else:
            special = "dB/radian/mole or other convention-sensitive quantities require explicit alternate-convention replay" if candidate_class == "REAL_DATA_MECHANISM_COMPETITION" else "alternate metrology convention or justified non-applicability"
            gates["U3_CONVENTION_ARTIFACT_AUDIT"] = self._frontier_gate("PENDING_CONVENTION_ARTIFACT_AUDIT", reason=special, required=("convention_audit",))

        deriv = self._validated_external_control(controls, "known_derivability_audit", pass_statuses=("PASS_NOT_DERIVED_FROM_ACCEPTED_LAWS",))
        if source_derived:
            gates["U4_KNOWN_DERIVABILITY_AUDIT"] = self._frontier_gate(
                "KNOWN_SOURCE_DERIVED_CONSEQUENCE",
                passed=False,
                evidence={"source_owner_ids": list(source_owner_ids), "formal_status": payload.get("formal_status")},
                reason="The candidate remains scientifically useful as a derived consequence, but it is not eligible for promotion as a new independent law on this route.",
            )
        elif deriv:
            gates["U4_KNOWN_DERIVABILITY_AUDIT"] = self._frontier_gate(deriv["status"], passed=True, evidence=deriv, reason="Trusted derivability audit supplied.")
        elif not materialized:
            gates["U4_KNOWN_DERIVABILITY_AUDIT"] = self._frontier_gate("BLOCKED_UNTIL_HYPOTHESIS_MATERIALIZED", reason="Derivability cannot be adjudicated for an unfrozen mechanism family/subspace.")
        else:
            gates["U4_KNOWN_DERIVABILITY_AUDIT"] = self._frontier_gate("PENDING_KNOWN_DERIVABILITY_AUDIT", reason="Current-corpus overlap and world prior art are not substitutes for formal derivability.", required=("known_derivability_audit",))

        collapse = self._validated_external_control(controls, "collapse_or_invariance", pass_statuses=("PASS_COLLAPSE_OR_INVARIANCE",))
        if collapse:
            gates["U5_COLLAPSE_OR_INVARIANCE"] = self._frontier_gate(collapse["status"], passed=True, evidence=collapse, reason="Trusted collapse/invariance evidence supplied.")
        elif candidate_class == "REAL_DATA_MECHANISM_COMPETITION" and payload.get("training_rmse_db") is not None:
            gates["U5_COLLAPSE_OR_INVARIANCE"] = self._frontier_gate(
                "PARTIAL_REAL_DATA_FIT_SUMMARY_NOT_COLLAPSE_OR_INVARIANCE_RECEIPT",
                evidence={"training_rmse_db": payload.get("training_rmse_db"), "leave_one_out_sigma_db": payload.get("leave_one_training_frequency_out_predictive_sigma_db")},
                reason="A fit summary exists, but raw uncertainty-aware collapse/invariance evidence is not bound here.",
                required=("collapse_or_invariance",),
            )
        elif source_derived:
            gates["U5_COLLAPSE_OR_INVARIANCE"] = self._frontier_gate("NOT_RUN_SOURCE_DERIVED_ROUTE", reason="Empirical qualification may still be useful for applicability, but new-law promotion already stops at derivability.")
        else:
            gates["U5_COLLAPSE_OR_INVARIANCE"] = self._frontier_gate("PENDING_COLLAPSE_OR_INVARIANCE", reason="No trusted multi-system collapse or trajectory-invariance result is bound to the candidate.", required=("collapse_or_invariance",))

        regime = self._validated_external_control(controls, "regime_ood", pass_statuses=("PASS_DISTINCT_REGIME_OOD",))
        if regime:
            gates["U6_DISTINCT_REGIME_OOD"] = self._frontier_gate(regime["status"], passed=True, evidence=regime, reason="Trusted non-overlapping regime/OOD evidence supplied.")
        elif candidate_class == "ADAPTIVE_MULTIDIMENSIONAL_SUBSPACE_FRONTIER" and isinstance(payload.get("discriminating_experiment"), Mapping):
            exp = dict(payload.get("discriminating_experiment", {}))
            gates["U6_DISTINCT_REGIME_OOD"] = self._frontier_gate(
                "DESIGNED_DISTINCT_REGIME_HOLDOUT_WORLD_RESULT_PENDING",
                evidence={"experiment_digest": exp.get("digest"), "world_result_observed": exp.get("world_result_observed")},
                reason="The frozen experiment requires non-overlapping regimes, but no world result is observed.",
                required=("regime_ood",),
            )
        elif candidate_class == "REAL_DATA_MECHANISM_COMPETITION" and payload.get("predicted_hidden_holdout_mean_db"):
            gates["U6_DISTINCT_REGIME_OOD"] = self._frontier_gate(
                "FROZEN_HOLDOUT_SUMMARY_PRESENT_RAW_OOD_RECEIPT_REQUIRED",
                evidence={"predicted_hidden_holdout_mean_db": payload.get("predicted_hidden_holdout_mean_db")},
                reason="Frozen holdout predictions exist, but the raw OOD partition, uncertainty and bound predictions are not part of this ledger record.",
                required=("regime_ood",),
            )
        else:
            gates["U6_DISTINCT_REGIME_OOD"] = self._frontier_gate("PENDING_DISTINCT_REGIME_OOD", reason="No trusted distinct-regime OOD result is bound.", required=("regime_ood",))

        cross = self._validated_external_control(controls, "cross_system_replication", pass_statuses=("PASS_INDEPENDENT_CROSS_SYSTEM_REPLICATION",))
        gates["U7_CROSS_SYSTEM_REPLICATION"] = (
            self._frontier_gate(cross["status"], passed=True, evidence=cross, reason="Trusted independent cross-system replication supplied.")
            if cross else
            self._frontier_gate("PENDING_INDEPENDENT_CROSS_SYSTEM_REPLICATION", reason="Replication must come from an independent system/campaign or declared independent dataset.", required=("cross_system_replication",))
        )

        gates["U8_WHOLE_PIPELINE_PERMUTATION_NULL"] = self._whole_pipeline_null_gate(controls)

        experiment = self._validated_external_control(controls, "discriminating_experiment", pass_statuses=("PASS_DISCRIMINATING_EXPERIMENT_OBSERVED",))
        if experiment:
            gates["U9_DISCRIMINATING_EXPERIMENT"] = self._frontier_gate(experiment["status"], passed=True, evidence=experiment, reason="Trusted discriminating experiment result supplied.")
        elif candidate_class == "ADAPTIVE_MULTIDIMENSIONAL_SUBSPACE_FRONTIER" and isinstance(payload.get("discriminating_experiment"), Mapping):
            exp = dict(payload.get("discriminating_experiment", {}))
            gates["U9_DISCRIMINATING_EXPERIMENT"] = self._frontier_gate(
                "EXPERIMENT_BLUEPRINT_FROZEN_WORLD_RESULT_PENDING",
                evidence={"experiment_digest": exp.get("digest"), "status": exp.get("status"), "world_result_observed": exp.get("world_result_observed")},
                reason="A discriminating experiment is frozen, but its world outcome is pending.",
                required=("observed experiment result",),
            )
        elif candidate_class == "CROSS_DOMAIN_AXIS_FRONTIER" and isinstance(payload.get("research_cycle"), Mapping):
            rc = dict(payload.get("research_cycle", {}))
            gates["U9_DISCRIMINATING_EXPERIMENT"] = self._frontier_gate(
                "RESEARCH_CYCLE_EXPERIMENT_DESIGN_WORLD_ATTESTATION_PENDING",
                evidence={"experiment_digest": rc.get("discriminating_experiment_digest"), "next_state": rc.get("next_state")},
                reason="Research-cycle experiment design exists, but world attestation/data acquisition is pending.",
                required=("observed experiment result",),
            )
        elif axis_route:
            ex = dict(payload.get("discriminating_experiment_execution", {}) or {})
            gates["U9_DISCRIMINATING_EXPERIMENT"] = self._frontier_gate(
                "AXIS_EXPERIMENT_DESIGNED_REAL_SYNCHRONIZED_DATA_PENDING" if not ex.get("full_real_execution") else "AXIS_EXPERIMENT_REAL_EXECUTION_PRESENT_REVIEW_REQUIRED",
                evidence={"status": ex.get("status"), "full_real_execution": ex.get("full_real_execution"), "public_data_status": ex.get("public_data_status")},
                reason="The provisional coordinate has an explicit measurement experiment; full real synchronized evidence is still required for canonical axis promotion.",
                required=("observed experiment result",) if not ex.get("full_real_execution") else (),
            )
        elif candidate_class == "REAL_DATA_MECHANISM_COMPETITION" and any("DISCRIMINATOR" in s for s in statuses):
            gates["U9_DISCRIMINATING_EXPERIMENT"] = self._frontier_gate(
                "DISCRIMINATOR_METHOD_QUALIFIED_REAL_DATA_PENDING" if "CANDIDATE_DISCRIMINATOR_REAL_DATA_PENDING" in statuses else "DISCRIMINATOR_METHOD_QUALIFIED_NO_BOUND_WORLD_RECEIPT",
                reason="A discriminator method is qualified, but this candidate record does not contain a trusted observed discriminator result.",
                required=("discriminating_experiment",),
            )
        else:
            gates["U9_DISCRIMINATING_EXPERIMENT"] = self._frontier_gate("EXPERIMENT_DESIGN_OR_WORLD_RESULT_REQUIRED", reason="No trusted observed discriminating experiment is bound.", required=("discriminating_experiment",))

        prepromotion_required = tuple(FRONTIER_GATE_SEQUENCE[0:10])
        all_required_pass = all(bool(gates.get(name, {}).get("pass")) for name in prepromotion_required)
        new_law_route = not source_derived and not axis_route
        prepromotion_ready = bool(all_required_pass and new_law_route)
        gates["U10_NUMERIC_PROMOTION_CORE"] = self._frontier_gate(
            "READY_FOR_NUMERIC_PROMOTION_CORE" if prepromotion_ready else ("ROUTED_TO_DYNAMIC_AXIS_PROMOTION" if axis_route else ("SOURCE_DERIVED_NOT_NEW_LAW_PROMOTION_ROUTE" if source_derived else "BLOCKED_UNTIL_UPSTREAM_EVIDENCE_COMPLETE")),
            passed=prepromotion_ready,
            reason="ScientificPromotionCore.evaluate may adjudicate a fully materialized numeric request only after all common upstream gates pass." if new_law_route else ("Canonical coordinate admission is owned by DynamicAxisPromotionOwner." if axis_route else "Source-derived consequences remain candidates/models but are not promoted as independent new laws."),
        )

        first_open = next((name for name in FRONTIER_GATE_SEQUENCE if not bool(gates.get(name, {}).get("pass"))), None)
        if axis_route:
            terminal = "AXIS_PROMOTION_ROUTE_PENDING_WORLD_EVIDENCE"
        elif source_derived:
            terminal = "SOURCE_DERIVED_CANDIDATE_RETAINED_NOT_NEW_LAW_PROMOTION"
        elif prepromotion_ready:
            terminal = "READY_FOR_NUMERIC_SCIENTIFIC_PROMOTION"
        else:
            terminal = "FRONTIER_QUALIFICATION_PENDING_EVIDENCE"
        receipt = {
            "schema": FRONTIER_PATH_SCHEMA,
            "owner": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "candidate_id": candidate_id,
            "candidate_class": candidate_class,
            "candidate_core_digest": candidate_core_digest,
            "domain_ids": list(domain_ids),
            "source_owner_ids": list(source_owner_ids),
            "gate_sequence": list(FRONTIER_GATE_SEQUENCE),
            "gates": gates,
            "prepromotion_ready": prepromotion_ready,
            "promotion_allowed": False,
            "candidate_is_false": False,
            "new_law_route": new_law_route,
            "next_gate": first_open,
            "terminal_status": terminal,
            "claim_boundary": {
                "missing_evidence_means_false": False,
                "known_source_derivation_means_candidate_false": False,
                "frontier_path_receipt_is_world_evidence": False,
                "law_candidate_requires_numeric_core_and_world_verified_evidence": True,
            },
            "OUTPUT_HASH": "",
        }
        receipt["OUTPUT_HASH"] = _digest({k: v for k, v in receipt.items() if k != "OUTPUT_HASH"})
        receipt["RECEIPT_ID"] = "FPR-" + receipt["OUTPUT_HASH"][:24].upper()
        return receipt

    @staticmethod
    def frontier_path_status(receipt: Mapping[str, Any] | None) -> Mapping[str, Any]:
        if not receipt or not str(receipt.get("RECEIPT_ID", "")).startswith("FPR-"):
            return {"status": "UNIFIED_FRONTIER_PATH_NOT_RUN", "valid": False, "prepromotion_ready": False}
        expected = _digest({k: v for k, v in receipt.items() if k not in {"OUTPUT_HASH", "RECEIPT_ID"}})
        valid = expected == str(receipt.get("OUTPUT_HASH", ""))
        return {
            "status": "VALID_UNIFIED_FRONTIER_PATH_RECEIPT" if valid else "INVALID_UNIFIED_FRONTIER_PATH_RECEIPT",
            "valid": valid,
            "prepromotion_ready": bool(valid and receipt.get("prepromotion_ready")),
            "candidate_id": receipt.get("candidate_id"),
            "terminal_status": receipt.get("terminal_status"),
            "next_gate": receipt.get("next_gate"),
        }

    @staticmethod
    def _fit(y: Sequence[float], sigma: Sequence[float], pred: Sequence[float], parameter_count: int, alpha: float) -> Mapping[str, Any]:
        yv = np.asarray(y, dtype=float); sv = np.asarray(sigma, dtype=float); pv = np.asarray(pred, dtype=float)
        if yv.size != pv.size or yv.size != sv.size or yv.size == 0:
            return {"status": "BLOCKED_LENGTH_MISMATCH", "pass": False}
        if not np.all(np.isfinite(pv)):
            return {"status": "BLOCKED_NONFINITE_PREDICTION", "pass": False}
        residual = (yv - pv) / sv
        chi2 = float(np.dot(residual, residual))
        dof = max(int(yv.size) - int(parameter_count), 1)
        reduced = chi2 / dof
        p_value = float(chi2_distribution.sf(chi2, dof))
        return {"chi2": chi2, "dof": dof, "reduced_chi2": reduced, "p_value": p_value, "alpha": alpha,
                "standardized_residual_rms": float(math.sqrt(np.mean(residual * residual))),
                "pass": bool(p_value >= alpha), "status": "PASS_ABSOLUTE_FIT" if p_value >= alpha else "FAIL_ABSOLUTE_FIT"}

    def _identifiability(self, model: CandidateModel, sigma: Sequence[float]) -> Mapping[str, Any]:
        k = len(model.parameters)
        if k == 0:
            return {"structural_pass": True, "practical_pass": True, "rank": 0, "dimension": 0, "singular_values": [], "s_min": math.inf, "status": "IDENTIFIED_NO_FREE_PARAMETERS"}
        if not model.jacobian_train or len(model.parameter_scales) != k:
            return {"structural_pass": False, "practical_pass": False, "rank": None, "dimension": k, "singular_values": [], "s_min": None, "status": "BLOCKED_JACOBIAN_OR_PARAMETER_SCALE_MISSING"}
        J = np.asarray(model.jacobian_train, dtype=float)
        s = np.asarray(sigma, dtype=float)
        scales = np.asarray(model.parameter_scales, dtype=float)
        if J.ndim != 2 or J.shape != (s.size, k) or np.any(~np.isfinite(J)) or np.any(~np.isfinite(scales)) or np.any(scales <= 0.0):
            return {"structural_pass": False, "practical_pass": False, "rank": None, "dimension": k, "singular_values": [], "s_min": None, "status": "BLOCKED_INVALID_JACOBIAN_OR_PARAMETER_SCALE"}
        raw_sv = np.linalg.svd(J, compute_uv=False)
        tol = self.config.rank_relative_tolerance * (raw_sv[0] if raw_sv.size else 1.0)
        rank = int(np.sum(raw_sv > tol))
        Jw = (J / s[:, None]) * scales[None, :]
        sv = np.linalg.svd(Jw, compute_uv=False)
        smin = float(sv[-1]) if sv.size else math.inf
        structural = rank == k
        practical = structural and smin >= self.config.practical_singular_value_min
        return {"structural_pass": structural, "practical_pass": practical, "rank": rank, "dimension": k,
                "singular_values": [float(x) for x in sv], "s_min": smin,
                "s_min_threshold": self.config.practical_singular_value_min,
                "status": "PASS_PRACTICAL_IDENTIFIABILITY" if practical else ("NON_IDENTIFIABLE_PRACTICAL" if structural else "NON_IDENTIFIABLE_STRUCTURAL")}

    def evaluate(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        run_id = str(request.get("run_id", "")).strip()
        seed = request.get("seed")
        candidate = CandidateModel.from_mapping(dict(request.get("candidate", {})))
        train = DataPartition.from_mapping(request.get("data", {}).get("train")) if isinstance(request.get("data"), Mapping) else None
        ood = DataPartition.from_mapping(request.get("data", {}).get("ood")) if isinstance(request.get("data"), Mapping) else None
        alternatives = tuple(AlternativeModel.from_mapping(row) for row in request.get("alternatives", ()))
        axis_validations = tuple(AxisOODValidation(**dict(row)) for row in request.get("generated_axis_ood_validations", ()))
        axis_contracts = tuple(AxisScientificContract.from_mapping(row) for row in request.get("axis_contracts", ()))
        axis_contract_by_id = {row.axis_id: row for row in axis_contracts}
        replication = ReplicationEvidence.from_mapping(request.get("replication"))
        global_ident = dict(request.get("global_identifiability_certificate", {}))
        unified_receipt = dict(request.get("unified_qualification_receipt", {}) or {})
        unified_status = self.frontier_path_status(unified_receipt)

        verification_bundle = dict(request.get("scientific_verification_bundle", {}) or {})
        verification = ScientificVerificationCore().verify_bundle(verification_bundle)
        artifact_receipts = {str(r.get("artifact_id", "")): dict(r) for r in verification_bundle.get("artifact_receipts", ()) if str(r.get("artifact_id", ""))}
        expected_artifacts: dict[str, Any] = {}
        if isinstance(request.get("data"), Mapping) and request.get("data", {}).get("train") is not None:
            expected_artifacts["promotion_train_data"] = request.get("data", {}).get("train")
        if isinstance(request.get("data"), Mapping) and request.get("data", {}).get("ood") is not None:
            expected_artifacts["promotion_ood_data"] = request.get("data", {}).get("ood")
        if request.get("replication") is not None:
            expected_artifacts["promotion_replication_data"] = request.get("replication")
        if global_ident:
            expected_artifacts["promotion_global_identifiability_certificate"] = global_ident
        if unified_receipt:
            expected_artifacts["promotion_unified_qualification_receipt"] = unified_receipt
        artifact_binding_checks = {}
        for artifact_id, content in expected_artifacts.items():
            row = artifact_receipts.get(artifact_id)
            artifact_binding_checks[artifact_id] = bool(
                row
                and IndependentArtifactVerifier.receipt_valid(row)
                and str(row.get("content_digest", "")) == content_addressed_digest(content)
            )
        g_minus1_engine = bool(
            verification.get("evidence_ready_for_domain") is True
            and expected_artifacts
            and all(artifact_binding_checks.values())
        )
        g_minus1_world = bool(g_minus1_engine and verification.get("scientific_candidate_allowed") is True)
        unified_artifact_bound = bool(
            unified_receipt
            and artifact_binding_checks.get("promotion_unified_qualification_receipt") is True
        )
        g_minus2_unified = bool(
            unified_status.get("valid") is True
            and unified_status.get("prepromotion_ready") is True
            and unified_artifact_bound
            and str(unified_status.get("candidate_id", "")) == candidate.candidate_id
        )

        input_payload = {k: v for k, v in request.items() if k not in {"expected_output_hash"}}
        input_hash = _digest(input_payload)
        required_axis_contract_ids = tuple(sorted(set(candidate.active_axes) | set(candidate.latent_axes)))
        g0_checks = {
            "RUN_ID_DECLARED": bool(run_id), "SEED_DECLARED": isinstance(seed, int), "CANDIDATE_DECLARATION_COMPLETE": candidate.declared_fields_ok(),
            "TRAIN_DATA_PRESENT": train is not None,
            "AXIS_CONTRACTS_COMPLETE": all(axis_id in axis_contract_by_id and axis_contract_by_id[axis_id].valid() for axis_id in required_axis_contract_ids),
            "AXIS_CONTRACT_IDS_UNIQUE": len(axis_contract_by_id) == len(axis_contracts),
        }
        train_integrity = train.integrity() if train else {"pass": False, "checks": {"TRAIN_DATA_PRESENT": False}}
        g0_checks.update({f"TRAIN_{k}": v for k, v in train_integrity.get("checks", {}).items()})
        g0 = all(g0_checks.values())

        dimension_digest = _digest({"lhs": candidate.dimension_lhs, "rhs": candidate.dimension_rhs})
        g1_checks = {
            "DIMENSION_VECTORS_DECLARED": bool(candidate.dimension_lhs) and bool(candidate.dimension_rhs),
            "DIMENSION_VECTOR_LENGTH_MATCH": len(candidate.dimension_lhs) == len(candidate.dimension_rhs) == 7,
            "DIMENSIONAL_EQUALITY_COMPUTED": bool(candidate.dimension_lhs) and candidate.dimension_lhs == candidate.dimension_rhs,
        }
        g1 = all(g1_checks.values())

        alt_roles = {a.role for a in alternatives}
        alternative_contract = {
            "roles_present": sorted(alt_roles),
            "missing_roles": [r for r in REQUIRED_ALTERNATIVE_ROLES if r not in alt_roles],
            "unique_ids": len({a.alternative_id for a in alternatives}) == len(alternatives),
            "declarations_complete": all(a.alternative_id and a.model_class and a.equation and a.provenance for a in alternatives),
        }
        alternatives_ok = not alternative_contract["missing_roles"] and alternative_contract["unique_ids"] and alternative_contract["declarations_complete"]

        fit_train: Mapping[str, Any] = {"status": "NOT_RUN", "pass": False}
        comparative: Mapping[str, Any] = {"status": "NOT_RUN", "pass": False}
        ident: Mapping[str, Any] = {"status": "NOT_RUN", "structural_pass": False, "practical_pass": False}
        ood_result: Mapping[str, Any] = {"status": "NOT_RUN", "pass": False}
        replication_result: Mapping[str, Any] = {"status": "NOT_RUN", "pass": False}
        global_owner = str(global_ident.get("owner_id", ""))
        global_certificate_pass = (
            global_ident.get("status") == "PASS"
            and global_owner in self.trusted_evidence_owners
            and str(global_ident.get("evidence_digest", "")).strip() != ""
            and str(global_ident.get("method", "")).strip() != ""
            and str(global_ident.get("provenance_level", "")) in {"COMPUTED", "WITNESSED"}
        )
        axis_results = [row.to_result() for row in axis_validations]
        axis_result_by_id = {str(row["axis_id"]): row for row in axis_results}
        required_axis_ids = tuple(sorted(set(candidate.latent_axes)))
        generated_axes_ok = all(axis_result_by_id.get(axis_id, {}).get("accepted") is True for axis_id in required_axis_ids)

        final_status = IdentifiabilityStatus.BLOCKED.value
        promotion_allowed = False
        terminal_reason = "G0_INPUT_INTEGRITY"

        if g_minus1_engine and g0 and g1:
            assert train is not None and train.sigma is not None
            fit_train = self._fit(train.y, train.sigma, candidate.predictions_train, len(candidate.parameters), self.config.absolute_fit_alpha)
            if not fit_train["pass"]:
                final_status = IdentifiabilityStatus.FALSIFIED.value; terminal_reason = "G2_ABSOLUTE_FIT"
            elif not alternatives_ok:
                final_status = IdentifiabilityStatus.BLOCKED.value; terminal_reason = "G3_ALTERNATIVES_REQUIRED"
            else:
                alt_fits = []
                for alt in alternatives:
                    row = self._fit(train.y, train.sigma, alt.predictions_train, 0, self.config.absolute_fit_alpha)
                    row = {**row, "alternative_id": alt.alternative_id, "role": alt.role, "model_class": alt.model_class}
                    alt_fits.append(row)
                best = min(alt_fits, key=lambda r: float(r.get("chi2", math.inf)))
                delta = float(fit_train["chi2"] - best["chi2"])
                comparative_pass = delta <= self.config.comparative_delta_chi2_falsification
                comparative = {"status": "PASS_COMPARATIVE_FALSIFICATION" if comparative_pass else "FAIL_COMPARATIVE_FALSIFICATION",
                               "pass": comparative_pass, "candidate_chi2": fit_train["chi2"], "best_alternative_id": best["alternative_id"],
                               "best_alternative_role": best["role"], "best_alternative_chi2": best["chi2"], "delta_chi2_candidate_minus_best": delta,
                               "falsification_threshold": self.config.comparative_delta_chi2_falsification, "alternatives": alt_fits}
                if not comparative_pass:
                    final_status = IdentifiabilityStatus.FALSIFIED.value; terminal_reason = "G3_ADVERSARIAL_COMPARISON"
                else:
                    final_status = IdentifiabilityStatus.FIT_ONLY.value
                    ident = self._identifiability(candidate, train.sigma)
                    if not ident["structural_pass"] or not ident["practical_pass"]:
                        final_status = IdentifiabilityStatus.NON_IDENTIFIABLE.value; terminal_reason = "G4_G5_IDENTIFIABILITY"
                    elif not generated_axes_ok:
                        final_status = IdentifiabilityStatus.UNDERDETERMINED.value; terminal_reason = "GENERATED_AXIS_OOD_GAIN"
                    else:
                        final_status = IdentifiabilityStatus.LOCALLY_IDENTIFIED.value
                        if ood is None:
                            final_status = IdentifiabilityStatus.NEEDS_EXPERIMENT.value; terminal_reason = "G6_OOD_MISSING"
                        else:
                            ood_integrity = ood.integrity()
                            regime_distinct = train.regime_id != ood.regime_id
                            if not ood_integrity["pass"] or not regime_distinct or ood.sigma is None or not candidate.predictions_ood:
                                final_status = IdentifiabilityStatus.NEEDS_EXPERIMENT.value; terminal_reason = "G6_OOD_INVALID_OR_SAME_REGIME"
                                ood_result = {"status": "BLOCKED_OOD_INTEGRITY_OR_REGIME", "pass": False, "integrity": ood_integrity, "regime_distinct": regime_distinct}
                            else:
                                ood_result = self._fit(ood.y, ood.sigma, candidate.predictions_ood, 0, self.config.ood_absolute_fit_alpha)
                                ood_result = {**ood_result, "regime_distinct": regime_distinct, "train_regime_id": train.regime_id, "ood_regime_id": ood.regime_id}
                                if not ood_result["pass"]:
                                    final_status = IdentifiabilityStatus.FALSIFIED.value; terminal_reason = "G6_OOD_FALSIFICATION"
                                elif not global_certificate_pass:
                                    final_status = IdentifiabilityStatus.UNDERDETERMINED.value; terminal_reason = "GLOBAL_IDENTIFIABILITY_NOT_ESTABLISHED"
                                else:
                                    final_status = IdentifiabilityStatus.GLOBALLY_IDENTIFIED.value
                                    if replication is None:
                                        terminal_reason = "G7_REPLICATION_REQUIRED_FOR_LAW_CANDIDATE"
                                    else:
                                        rep_partition = DataPartition(replication.y, replication.sigma, replication.regime_id, replication.provenance)
                                        rep_integrity = rep_partition.integrity()
                                        if not replication.independent or not rep_integrity["pass"] or replication.sigma is None:
                                            replication_result = {"status": "BLOCKED_REPLICATION_NOT_INDEPENDENT_OR_INVALID", "pass": False, "integrity": rep_integrity, "independent": replication.independent}
                                            terminal_reason = "G7_REPLICATION_INVALID"
                                        else:
                                            replication_result = self._fit(replication.y, replication.sigma, replication.predictions, 0, self.config.replication_absolute_fit_alpha)
                                            replication_result = {**replication_result, "independent": replication.independent, "regime_id": replication.regime_id}
                                            if replication_result["pass"]:
                                                if g_minus1_world and g_minus2_unified:
                                                    final_status = IdentifiabilityStatus.LAW_CANDIDATE.value; promotion_allowed = True; terminal_reason = "ALL_GATES_PASS_WITH_WORLD_VERIFIED_EVIDENCE"
                                                elif g_minus1_world:
                                                    final_status = IdentifiabilityStatus.REPLICATED.value; promotion_allowed = False; terminal_reason = "G_MINUS2_UNIFIED_FRONTIER_QUALIFICATION_REQUIRED_FOR_LAW_CANDIDATE"
                                                else:
                                                    final_status = IdentifiabilityStatus.REPLICATED.value; promotion_allowed = False; terminal_reason = "G_MINUS1_WORLD_ATTESTATION_REQUIRED_FOR_LAW_CANDIDATE"
                                            else:
                                                final_status = IdentifiabilityStatus.FALSIFIED.value; terminal_reason = "G7_REPLICATION_FALSIFICATION"
        elif not g_minus1_engine:
            final_status = IdentifiabilityStatus.BLOCKED.value; terminal_reason = "G_MINUS1_SCIENTIFIC_VERIFICATION"
        elif g0 and not g1:
            final_status = IdentifiabilityStatus.REJECTED.value; terminal_reason = "G1_DIMENSIONAL_CONSISTENCY"

        gate_results = {
            "G_MINUS2_UNIFIED_FRONTIER_QUALIFICATION": {
                "pass": g_minus2_unified,
                "receipt_present": bool(unified_receipt),
                "receipt_valid": unified_status.get("valid") is True,
                "prepromotion_ready": unified_status.get("prepromotion_ready") is True,
                "artifact_bound": unified_artifact_bound,
                "candidate_id_matches": str(unified_status.get("candidate_id", "")) == candidate.candidate_id if unified_receipt else False,
                "status": unified_status.get("status"),
                "terminal_status": unified_status.get("terminal_status"),
                "next_gate": unified_status.get("next_gate"),
            },
            "G_MINUS1_SCIENTIFIC_VERIFICATION": {
                "pass": g_minus1_engine,
                "world_pass": g_minus1_world,
                "verification_status": verification.get("overall_status"),
                "verification_digest": verification.get("verification_digest"),
                "artifact_binding_checks": artifact_binding_checks,
            },
            "G0_INPUT_INTEGRITY": {"pass": g0, "checks": g0_checks},
            "G1_DIMENSIONAL_CONSISTENCY": {"pass": g1, "checks": g1_checks},
            "G2_ABSOLUTE_FIT": fit_train,
            "G3_ADVERSARIAL_COMPARISON": {**comparative, "alternative_contract": alternative_contract},
            "G4_STRUCTURAL_IDENTIFIABILITY": {"pass": bool(ident.get("structural_pass")), "rank": ident.get("rank"), "dimension": ident.get("dimension"), "status": ident.get("status")},
            "G5_PRACTICAL_IDENTIFIABILITY": {"pass": bool(ident.get("practical_pass")), "singular_values": ident.get("singular_values", []), "s_min": ident.get("s_min"), "threshold": self.config.practical_singular_value_min, "status": ident.get("status")},
            "GENERATED_AXIS_OOD_VALIDATION": {"pass": generated_axes_ok, "required_axis_ids": list(required_axis_ids), "results": axis_results},
            "G6_REGIME_OOD": ood_result,
            "GLOBAL_IDENTIFIABILITY_CERTIFICATE": {"pass": global_certificate_pass, "trusted_owner": global_owner in self.trusted_evidence_owners, **global_ident},
            "G7_INDEPENDENT_REPLICATION": replication_result,
        }
        state_trace = [IdentifiabilityStatus.PROPOSED.value]
        if fit_train.get("pass") and comparative.get("pass"):
            state_trace.append(IdentifiabilityStatus.FIT_ONLY.value)
        if ident.get("structural_pass") and ident.get("practical_pass") and generated_axes_ok:
            state_trace.append(IdentifiabilityStatus.LOCALLY_IDENTIFIED.value)
        if ood_result.get("pass") and global_certificate_pass:
            state_trace.append(IdentifiabilityStatus.GLOBALLY_IDENTIFIED.value)
        if replication_result.get("pass"):
            state_trace.append(IdentifiabilityStatus.REPLICATED.value)
        if promotion_allowed:
            state_trace.append(IdentifiabilityStatus.LAW_CANDIDATE.value)
        elif final_status not in state_trace:
            state_trace.append(final_status)
        provenance_level = ProvenanceLevel.REPLICATED.value if replication_result.get("pass") else ProvenanceLevel.WITNESSED.value
        provenance_trace = [ProvenanceLevel.DECLARED.value, ProvenanceLevel.COMPUTED.value, provenance_level]
        receipt = {
            "schema": SCHEMA, "RUN_ID": run_id, "CORE_VERSION": OWNER_VERSION, "MODEL_VERSION": candidate.model_version,
            "DIMENSION_CHECK": {"lhs": list(candidate.dimension_lhs), "rhs": list(candidate.dimension_rhs), "digest": dimension_digest, "pass": g1},
            "SEED": seed, "INPUT_HASH": input_hash,
            "INITIAL_AXES": [dataclasses.asdict(axis_contract_by_id[x]) for x in candidate.active_axes if x in axis_contract_by_id], "GENERATED_AXES": [r for r in axis_results if r["accepted"]], "NOT_PROMOTED_AXES": [r for r in axis_results if not r["accepted"]], "REJECTED_AXES": [],
            "CANDIDATES": [candidate.candidate_id] + [a.alternative_id for a in alternatives], "MODEL_CLASSES": [candidate.model_class] + [a.model_class for a in alternatives],
            "FIT_RESULTS": fit_train, "ALTERNATIVES": comparative, "DELTA_CHI2": comparative.get("delta_chi2_candidate_minus_best"),
            "IDENTIFIABILITY": ident, "SINGULAR_VALUES": ident.get("singular_values", []), "OOD_RESULTS": ood_result,
            "REJECTED_MODELS": [candidate.candidate_id] if final_status in {IdentifiabilityStatus.FALSIFIED.value, IdentifiabilityStatus.REJECTED.value, IdentifiabilityStatus.NON_IDENTIFIABLE.value} else [],
            "SURVIVING_MODELS": [candidate.candidate_id] if final_status not in {IdentifiabilityStatus.FALSIFIED.value, IdentifiabilityStatus.REJECTED.value, IdentifiabilityStatus.BLOCKED.value} else [],
            "PREDICTIONS": {"train_digest": _digest(candidate.predictions_train), "ood_digest": _digest(candidate.predictions_ood)},
            "PLANNER_OPTIONS": list(request.get("planner_options", ())), "PREDICTED_EIG": request.get("predicted_eig"),
            "REALIZED_IG": request.get("realized_information_gain"),
            "EIG_CALIBRATION_ERROR": (
                None if request.get("predicted_eig") is None or request.get("realized_information_gain") is None
                else float(request.get("realized_information_gain")) - float(request.get("predicted_eig"))
            ),
            "SELECTED_EXPERIMENT": request.get("selected_experiment"),
            "FINAL_STATUS": final_status, "STATE_TRACE": state_trace, "TERMINAL_REASON": terminal_reason, "PROMOTION_ALLOWED": promotion_allowed,
            "PROVENANCE_LEVEL": provenance_level, "PROVENANCE_TRACE": provenance_trace, "SYSTEM_STATUS": SYSTEM_STATUS,
            "gate_results": gate_results, "scientific_verification": verification, "global_identifiability_certificate": global_ident,
            "unified_frontier_qualification": unified_status,
            "replication": replication_result, "OUTPUT_HASH": "",
        }
        receipt["OUTPUT_HASH"] = _digest({k: v for k, v in receipt.items() if k != "OUTPUT_HASH"})
        receipt["RECEIPT_ID"] = "SPR-" + receipt["OUTPUT_HASH"][:24].upper()
        return receipt

    @staticmethod
    def inference_status(receipt: Mapping[str, Any] | None) -> Mapping[str, Any]:
        if not receipt or not str(receipt.get("RECEIPT_ID", "")).startswith("SPR-"):
            return {"status": "ENGINE_NOT_RUN_SCIENTIFIC_INFERENCE_BLOCKED", "scientific_claim_allowed": False, "promotion_allowed": False}
        expected = _digest({k: v for k, v in receipt.items() if k not in {"OUTPUT_HASH", "RECEIPT_ID"}})
        valid = expected == receipt.get("OUTPUT_HASH")
        promoted = bool(valid and receipt.get("PROMOTION_ALLOWED"))
        return {"status": "SCIENTIFIC_PROMOTION_RECEIPT_VALID" if valid else "INVALID_SCIENTIFIC_PROMOTION_RECEIPT",
                "scientific_claim_allowed": promoted, "promotion_allowed": promoted,
                "final_status": receipt.get("FINAL_STATUS"), "provenance_level": receipt.get("PROVENANCE_LEVEL")}
