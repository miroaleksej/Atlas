"""Pharmaceutical Problem Atlas and research operators for Φ-LawSpace v8.3.

The atlas stores *source-derived research problems*, not scientific truth.  A PDF,
conference proceeding, review, patent list, or model output may seed a problem
record, but no source-derived claim becomes active evidence until the existing
SCIENTIFIC-VERIFICATION-CORE independently verifies the supplied evidence bundle.

Pipeline:
    Source document -> normalized source article -> Problem -> Evidence -> Axes
    -> Research operator -> Candidate search region -> Blocking uncertainty
    -> Next experiment design

The four operators in this module never perform scientific promotion and never
invent missing numeric measurements, candidate structures, EIG values, costs,
PK/PD values, or clinical efficacy.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
import json
import math

from .domains import DOMAIN_REGISTRIES
from .schema import digest_payload
from .scientific_verification import ScientificVerificationCore

OWNER_ID = "PHARMACEUTICAL-PROBLEM-ATLAS/8.3.0"
SCHEMA = "phi-pharmaceutical-problem-atlas/v8.3"
OPERATOR_OWNER_ID = "PHARMACEUTICAL-RESEARCH-OPERATORS/8.3.0"
OPERATOR_SCHEMA = "phi-pharmaceutical-research-operators/v8.3"

SOURCE_DERIVED_UNVERIFIED = "SOURCE_DERIVED_UNVERIFIED"
WORLD_VERIFIED = "WORLD_VERIFIED"

RESEARCH_OPERATORS = (
    "FORMULATION_RESCUE",
    "DELIVERY_RESCUE",
    "MULTIOBJECTIVE_MEDCHEM_SEARCH",
    "LOW_COST_ASSAY_DESIGN",
)

# Required canonical coordinates and cross-domain references.  Required means
# "the search operator must address this coordinate", not "a measured value is
# already known".
_OPERATOR_SPECS: Mapping[str, Mapping[str, Any]] = {
    "FORMULATION_RESCUE": {
        "candidate_class": "FORMULATION_SEARCH_REGION",
        "required_pharmaceutical_axes": (
            "formulation", "route_of_administration", "solubility",
            "excipient_compatibility", "solubilization_capacity",
            "release_profile", "storage_stability",
        ),
        "optional_pharmaceutical_axes": (
            "bioavailability", "gastric_resistance", "therapeutic_window",
            "assay_reproducibility",
        ),
        "objectives": (
            "increase usable exposure without asserting efficacy",
            "preserve chemical/biological integrity",
            "reduce formulation failure modes",
        ),
    },
    "DELIVERY_RESCUE": {
        "candidate_class": "DELIVERY_SEARCH_REGION",
        "required_pharmaceutical_axes": (
            "therapeutic_modality", "route_of_administration", "formulation",
            "release_profile", "gastric_resistance", "storage_stability",
        ),
        "optional_pharmaceutical_axes": (
            "localization_strategy", "bioavailability", "target_engagement",
            "exposure_metric",
        ),
        "objectives": (
            "deliver intact payload to declared compartment",
            "separate route feasibility from pharmacodynamic efficacy",
            "measure release and stability under relevant conditions",
        ),
    },
    "MULTIOBJECTIVE_MEDCHEM_SEARCH": {
        "candidate_class": "MEDCHEM_SEARCH_REGION",
        "required_pharmaceutical_axes": (
            "molecular_target", "potency_metric", "selectivity",
            "off_target_liability", "safety_pharmacology",
            "synthetic_accessibility",
        ),
        "optional_pharmaceutical_axes": (
            "binding_kinetics", "solubility", "metabolism_pathway",
            "therapeutic_window", "cardiac_safety",
        ),
        "objectives": (
            "optimize a Pareto set rather than potency alone",
            "retain uncertainty and applicability-domain status",
            "reject candidates whose gain is driven by unverified evidence",
        ),
    },
    "LOW_COST_ASSAY_DESIGN": {
        "candidate_class": "ASSAY_DESIGN_REGION",
        "required_pharmaceutical_axes": (
            "assay_cost", "assay_reproducibility",
        ),
        "cross_domain_axes": (
            "chemistry:analytical_method", "chemistry:instrument_type",
            "metrology:uncertainty_model", "metrology:repeatability",
            "metrology:reproducibility",
        ),
        "objectives": (
            "minimize assay cost subject to declared accuracy/reproducibility constraints",
            "preserve traceability and calibration requirements",
            "do not infer equivalence to a reference method without paired data",
        ),
    },
}


def _finite_nonnegative(v: Any) -> bool:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return False
    return math.isfinite(x) and x >= 0.0


def _axis_ref_exists(ref: str) -> bool:
    if ":" not in ref:
        return ref in DOMAIN_REGISTRIES["pharmaceutical"].axes
    domain, axis = ref.split(":", 1)
    return domain in DOMAIN_REGISTRIES and axis in DOMAIN_REGISTRIES[domain].axes


def _normalized_source_locator(locator: Mapping[str, Any]) -> Mapping[str, Any]:
    start = int(locator.get("pdf_start_page", 0) or 0)
    end = int(locator.get("pdf_end_page", start) or start)
    total = int(locator.get("pdf_total_pages", 0) or 0)
    if start < 1 or end < start or (total and end > total):
        raise ValueError("invalid PDF source page locator")
    digest = str(locator.get("source_document_sha256", "")).strip().lower()
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("source_document_sha256 must be a 64-character hexadecimal SHA-256")
    return {
        "source_document_name": str(locator.get("source_document_name", "")).strip(),
        "source_document_sha256": digest,
        "pdf_start_page": start,
        "pdf_end_page": end,
        "pdf_total_pages": total,
        "printed_start_page": locator.get("printed_start_page"),
    }


def _canonical_source_claims(claims: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Keep raw source excerpts audit-only regardless of caller-supplied flags.

    Scientific activation has exactly one channel: ``active_verified_claims`` from
    SCIENTIFIC-VERIFICATION-CORE.  A source record is untrusted input and cannot
    smuggle ``active_evidence=True`` through this owner, even when the source later
    becomes WORLD-verified.  Verification may activate sanitized claim *values*,
    never the raw excerpt object itself.
    """
    rows: list[dict[str, Any]] = []
    for claim in claims:
        row = dict(claim)
        row["active_evidence"] = False
        row["evidence_channel"] = "AUDIT_ONLY_SOURCE_DERIVED"
        rows.append(row)
    return rows


@dataclass(frozen=True)
class ProblemPlan:
    problem_id: str
    operator_id: str
    payload: Mapping[str, Any]


class PharmaceuticalResearchOperatorOwner:
    owner_id = OPERATOR_OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": OPERATOR_SCHEMA,
            "owner_id": OPERATOR_OWNER_ID,
            "operators": {k: dict(v) for k, v in _OPERATOR_SPECS.items()},
            "hard_invariants": {
                "operator_is_scientific_promotion": False,
                "operator_may_invent_missing_measurements": False,
                "operator_may_invent_candidate_structure": False,
                "operator_may_assign_world_novelty": False,
                "operator_may_assign_clinical_efficacy": False,
                "unverified_source_claim_may_become_active_evidence": False,
                "raw_source_active_evidence_flag_is_trusted": False,
                "cross_domain_required_coordinates_may_be_omitted": False,
                "missing_numeric_objective_may_be_imputed": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    def plan(self, problem: Mapping[str, Any], operator_id: str) -> Mapping[str, Any]:
        operator_id = str(operator_id).upper()
        if operator_id not in _OPERATOR_SPECS:
            raise ValueError(f"unsupported research operator {operator_id!r}")
        spec = dict(_OPERATOR_SPECS[operator_id])
        required = tuple(spec.get("required_pharmaceutical_axes", ()))
        cross = tuple(spec.get("cross_domain_axes", ()))
        missing_registry = [a for a in required if not _axis_ref_exists(a)] + [a for a in cross if not _axis_ref_exists(a)]
        if missing_registry:
            raise RuntimeError(f"operator references unregistered axes: {missing_registry}")

        declared_axes = set(str(x) for x in problem.get("relevant_axes", ()))
        addressed = sorted(declared_axes & set(required))
        unresolved = sorted(set(required) - declared_axes)
        addressed_cross = sorted(declared_axes & set(cross))
        unresolved_cross = sorted(set(cross) - declared_axes)
        unresolved_all = sorted(set(unresolved) | set(unresolved_cross))
        source_world_verified = problem.get("source_verification_status") == WORLD_VERIFIED
        blockers = list(dict.fromkeys(str(x) for x in problem.get("blocking_uncertainties", ())))
        if not source_world_verified and "WORLD_SOURCE_VERIFICATION_REQUIRED" not in blockers:
            blockers.insert(0, "WORLD_SOURCE_VERIFICATION_REQUIRED")
        if unresolved:
            blockers.append("OPERATOR_REQUIRED_COORDINATES_NOT_YET_ADDRESSED")
        if unresolved_cross:
            blockers.append("OPERATOR_REQUIRED_CROSS_DOMAIN_COORDINATES_NOT_YET_ADDRESSED")
        blockers = list(dict.fromkeys(blockers))

        candidate = {
            "candidate_class": spec["candidate_class"],
            "status": "PARAMETERIZED_SEARCH_REGION_NOT_DRUG_CLAIM",
            "operator_id": operator_id,
            "search_variables": list(required),
            "cross_domain_variables": list(cross),
            "objectives": list(spec.get("objectives", ())),
            "generated_molecular_structure": False,
            "clinical_efficacy_claimed": False,
            "world_novelty_claimed": False,
        }
        next_experiment = self._next_experiment_design(problem, operator_id, unresolved_all, source_world_verified)
        payload = {
            "schema": OPERATOR_SCHEMA,
            "owner_id": OPERATOR_OWNER_ID,
            "problem_id": problem.get("problem_id"),
            "operator_id": operator_id,
            "source_world_verified": source_world_verified,
            "required_axes": list(required),
            "cross_domain_axes": list(cross),
            "addressed_required_axes": addressed,
            "unresolved_required_axes": unresolved,
            "addressed_cross_domain_axes": addressed_cross,
            "unresolved_cross_domain_axes": unresolved_cross,
            "coordinate_closure_complete": not unresolved_all,
            "candidate": candidate,
            "blocking_uncertainties": blockers,
            "next_experiment": next_experiment,
            "scientific_status_modified": False,
            "promotion_allowed_by_operator": False,
        }
        return {**payload, "digest": digest_payload(payload)}

    @staticmethod
    def _next_experiment_design(problem: Mapping[str, Any], operator_id: str, unresolved: Sequence[str], world_verified: bool) -> Mapping[str, Any]:
        # The operator selects the *kind* of discriminating measurement.  It does
        # not invent numerical sample size, concentration, dose, EIG, cost, or
        # acceptance thresholds absent from verified inputs.
        designs = {
            "FORMULATION_RESCUE": {
                "experiment_class": "PAIRED_FORMULATION_SCREEN_WITH_REFERENCE",
                "required_outputs": ["solubility", "solubilization_capacity", "excipient_compatibility", "storage_stability", "release_profile"],
            },
            "DELIVERY_RESCUE": {
                "experiment_class": "DELIVERY_STABILITY_RELEASE_CHALLENGE",
                "required_outputs": ["payload_integrity", "gastric_resistance", "release_profile", "storage_stability"],
            },
            "MULTIOBJECTIVE_MEDCHEM_SEARCH": {
                "experiment_class": "ORTHOGONAL_ACTIVITY_SELECTIVITY_SAFETY_PANEL",
                "required_outputs": ["potency_metric", "selectivity", "off_target_liability", "safety_pharmacology", "synthetic_accessibility"],
            },
            "LOW_COST_ASSAY_DESIGN": {
                "experiment_class": "PAIRED_REFERENCE_METHOD_VALIDATION",
                "required_outputs": ["assay_cost", "assay_reproducibility", "bias_vs_reference", "uncertainty_budget"],
            },
        }
        row = dict(designs[operator_id])
        row.update({
            "status": "DESIGN_ONLY_WORLD_EVIDENCE_REQUIRED_BEFORE_SCIENTIFIC_DECISION" if not world_verified else "DESIGN_READY_FOR_PARAMETERIZATION",
            "numeric_protocol_parameters_invented": False,
            "expected_information_gain_computed": False,
            "unresolved_operator_axes": list(unresolved),
        })
        return row


class PharmaceuticalProblemAtlasOwner:
    owner_id = OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "pipeline": ["PROBLEM", "EVIDENCE", "SEMANTIC_GRAPH", "AXES", "OPERATOR_ELIGIBILITY", "CANDIDATE", "BLOCKING_UNCERTAINTY", "NEXT_EXPERIMENT"],
            "source_policy": {
                "uploaded_or_local_document_is_world_verified_by_presence": False,
                "source_excerpt_is_active_scientific_evidence_without_core": False,
                "raw_source_active_evidence_flag_is_authoritative": False,
                "source_digest_proves_document_integrity_not_claim_truth": True,
                "scientific_verification_owner": "SCIENTIFIC-VERIFICATION-CORE/8.0.0",
            },
            "research_operator_owner": OPERATOR_OWNER_ID,
            "research_operators": list(RESEARCH_OPERATORS),
            "registered_pharmaceutical_axis_count": DOMAIN_REGISTRIES["pharmaceutical"].axis_count,
            "scientific_promotion_authority": False,
        }
        return {**payload, "digest": digest_payload(payload)}

    def ingest_problem(self, record: Mapping[str, Any], verification_bundle: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        problem_id = str(record.get("problem_id", "")).strip()
        if not problem_id:
            raise ValueError("problem_id required")
        locator = _normalized_source_locator(dict(record.get("source_locator", {})))
        relevant_axes = tuple(str(x) for x in record.get("relevant_axes", ()))
        unknown = [x for x in relevant_axes if not _axis_ref_exists(x)]
        if unknown:
            raise ValueError(f"problem {problem_id}: unregistered relevant axes {unknown}")

        # Always invoke the common core.  No bundle means fail-closed source
        # provenance; the source-derived text remains audit material only.
        bundle = dict(verification_bundle or {})
        if not bundle:
            bundle = {"proposer_owner": OWNER_ID, "evidence_class": "EXTERNAL_SOURCE", "claim_values": {}}
        verification = ScientificVerificationCore().verify_bundle(bundle)
        world_verified = bool(verification.get("scientific_candidate_allowed") is True)
        source_status = WORLD_VERIFIED if world_verified else SOURCE_DERIVED_UNVERIFIED

        raw_claims = _canonical_source_claims(record.get("source_derived_claims", ()))
        active_claims = dict(verification.get("sanitized_claim_values", {})) if world_verified else {}
        operator_id = str(record.get("research_operator", "NONE_SOURCE_CONTEXT_ONLY")).upper()
        if operator_id not in RESEARCH_OPERATORS and operator_id != "NONE_SOURCE_CONTEXT_ONLY":
            raise ValueError(f"problem {problem_id}: unknown research_operator {operator_id}")
        blockers = list(dict.fromkeys(str(x) for x in record.get("blocking_uncertainties", ())))
        if not world_verified and "WORLD_SOURCE_VERIFICATION_REQUIRED" not in blockers:
            blockers.insert(0, "WORLD_SOURCE_VERIFICATION_REQUIRED")

        typed_problem_graph = dict(record.get("typed_problem_graph", {}))
        quantitative_model_seed = dict(record.get("quantitative_model_seed", {}))
        world_binding = {
            "schema": "phi-pharmaceutical-problem-world-binding/v8.3",
            "problem_id": problem_id,
            "article_id": record.get("article_id"),
            "title": record.get("title"),
            "source_locator": locator,
            "source_claims_digest": digest_payload(raw_claims),
            "typed_problem_graph_digest": digest_payload(typed_problem_graph),
            "quantitative_model_seed_digest": digest_payload(quantitative_model_seed),
        }
        world_binding_digest = digest_payload(world_binding)

        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "problem_id": problem_id,
            "article_id": record.get("article_id"),
            "title": record.get("title"),
            "problem_type": record.get("problem_type", "SOURCE_DERIVED_RESEARCH_PROBLEM"),
            "problem_statement": record.get("problem_statement"),
            "source_locator": locator,
            "source_derived_claims": raw_claims,
            "typed_problem_graph": typed_problem_graph,
            "operator_adjudication": dict(record.get("operator_adjudication", {})),
            "evidence_supported_axes": list(record.get("evidence_supported_axes", ())),
            "operator_required_axes": list(record.get("operator_required_axes", ())),
            "semantic_adjudication_source": record.get("semantic_adjudication_source"),
            "quantitative_model_seed": quantitative_model_seed,
            "world_binding": world_binding,
            "world_binding_digest": world_binding_digest,
            "source_verification_status": source_status,
            "verification_overall_status": verification.get("overall_status"),
            "verification_digest": verification.get("verification_digest"),
            "active_verified_claims": active_claims,
            "relevant_axes": list(relevant_axes),
            "research_operator": operator_id,
            "candidate_seed": dict(record.get("candidate_seed", {})),
            "blocking_uncertainties": blockers,
            "source_claims_are_scientific_truth": False,
            "scientific_status_modified": False,
        }
        if record.get("problem_type") == "EVIDENCE_GAP":
            payload["evidence_gap"] = self._evidence_gap_plan(record, world_verified)
        if operator_id in RESEARCH_OPERATORS:
            payload["operator_plan"] = PharmaceuticalResearchOperatorOwner().plan(payload, operator_id)
        else:
            payload["operator_plan"] = {
                "status": "SOURCE_CONTEXT_ONLY_NO_RESEARCH_OPERATOR_SELECTED",
                "scientific_status_modified": False,
            }
        return {**payload, "digest": digest_payload(payload)}

    def prepare_world_cycle(
        self,
        problem: Mapping[str, Any],
        verification_bundle: Mapping[str, Any] | None = None,
        predictive_model_receipt: Mapping[str, Any] | None = None,
        predictive_verification_bundle: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Materialize Source -> Verification -> Model -> Experiment -> EIG fail-closed.

        Serialized ``source_verification_status`` is never an authorization token.
        WORLD readiness is recomputed from ``verification_bundle`` and is bound to
        this exact problem through the signed ``problem_binding_digest`` claim.
        Likewise, predictive likelihoods and their uncertainty model are accepted
        only when a second WORLD verification bundle is bound to the exact
        ``predictive_model_digest``.  Exact EIG mathematics is delegated to the
        existing DOMAIN-NEUTRAL-INFORMATION-GAIN owner.
        """
        operator_id = str(problem.get("research_operator", "NONE_SOURCE_CONTEXT_ONLY"))
        plan = dict(problem.get("operator_plan", {}))
        quantitative_model = dict(problem.get("quantitative_model_seed", {}))
        falsifier_templates = {
            "FORMULATION_RESCUE": [
                "predeclared solubility/exposure objective not met",
                "excipient incompatibility or precipitation observed",
                "release or storage-stability criterion fails",
            ],
            "DELIVERY_RESCUE": [
                "payload integrity lost under route-relevant challenge",
                "gastric/release behavior contradicts declared delivery window",
                "storage stability fails predeclared criterion",
            ],
            "MULTIOBJECTIVE_MEDCHEM_SEARCH": [
                "orthogonal potency assay fails to reproduce predicted activity",
                "selectivity panel collapses the claimed Pareto advantage",
                "safety/off-target panel removes the candidate from the Pareto set",
            ],
            "LOW_COST_ASSAY_DESIGN": [
                "paired reference-method bias exceeds predeclared acceptance criterion",
                "repeatability/reproducibility is insufficient across devices/operators",
                "uncertainty budget or traceability is inferior to the declared requirement",
            ],
        }

        # Never trust a serialized status. Recompute central verification now.
        source_verification = ScientificVerificationCore().verify_bundle(dict(verification_bundle or {}))
        expected_problem_binding = str(problem.get("world_binding_digest", ""))
        verified_problem_binding = str(source_verification.get("sanitized_claim_values", {}).get("problem_binding_digest", ""))
        problem_binding_pass = bool(expected_problem_binding) and verified_problem_binding == expected_problem_binding
        world_verified = bool(source_verification.get("scientific_candidate_allowed") is True and problem_binding_pass)

        predictive = dict(predictive_model_receipt or {})
        predictive_digest = digest_payload(predictive) if predictive else ""
        predictive_verification = ScientificVerificationCore().verify_bundle(dict(predictive_verification_bundle or {}))
        verified_predictive_digest = str(predictive_verification.get("sanitized_claim_values", {}).get("predictive_model_digest", ""))
        predictive_binding_pass = bool(predictive_digest) and verified_predictive_digest == predictive_digest
        predictive_world_verified = bool(
            predictive_verification.get("scientific_candidate_allowed") is True and predictive_binding_pass
        )

        has_operator = operator_id in RESEARCH_OPERATORS
        candidate_ids = tuple(str(x) for x in predictive.get("candidate_ids", ()))
        experiment_rows = tuple(dict(x) for x in predictive.get("experiment_specs", ()))
        uncertainty_model = predictive.get("uncertainty_model")
        uncertainty_declared = isinstance(uncertainty_model, Mapping) and bool(uncertainty_model)
        predictive_likelihoods_declared = bool(candidate_ids) and bool(experiment_rows)

        blockers: list[str] = []
        if not has_operator:
            blockers.append("RESEARCH_OPERATOR_ABSTAIN_OR_NOT_SELECTED")
        if not world_verified:
            blockers.append("EXTERNAL_WORLD_ATTESTATION_REQUIRED")
            if source_verification.get("scientific_candidate_allowed") is True and not problem_binding_pass:
                blockers.append("WORLD_VERIFICATION_PROBLEM_BINDING_REQUIRED")
        if not quantitative_model:
            blockers.append("QUANTITATIVE_MODEL_NOT_MATERIALIZED")
        if not predictive_likelihoods_declared:
            blockers.append("PREDICTIVE_LIKELIHOODS_REQUIRED_BEFORE_EIG")
        if not uncertainty_declared:
            blockers.append("UNCERTAINTY_MODEL_REQUIRED_BEFORE_EIG")
        if predictive and not predictive_world_verified:
            blockers.append("PREDICTIVE_MODEL_WORLD_ATTESTATION_REQUIRED")
            if predictive_verification.get("scientific_candidate_allowed") is True and not predictive_binding_pass:
                blockers.append("PREDICTIVE_MODEL_BINDING_REQUIRED")

        eig_receipt: Mapping[str, Any] | None = None
        can_compute_eig = (
            has_operator and world_verified and bool(quantitative_model)
            and predictive_likelihoods_declared and uncertainty_declared and predictive_world_verified
        )
        if can_compute_eig:
            from .research_cycle import DomainNeutralInformationGainOwner, ExperimentLikelihoodSpec
            specs = tuple(ExperimentLikelihoodSpec(**row) for row in experiment_rows)
            eig_receipt = DomainNeutralInformationGainOwner().rank(
                candidate_ids=candidate_ids, experiment_specs=specs, priors=predictive.get("priors"),
            )
            if eig_receipt.get("status") != "EIG_RANKED":
                blockers.append("DOMAIN_NEUTRAL_EIG_OWNER_DID_NOT_RANK")

        eig_computed = bool(eig_receipt and eig_receipt.get("status") == "EIG_RANKED")
        world_cycle_complete = bool(can_compute_eig and eig_computed and not blockers)
        if world_cycle_complete:
            status = "WORLD_CYCLE_EIG_READY_NOT_SCIENTIFIC_PROMOTION"
        elif not has_operator:
            status = "WORLD_CYCLE_BLOCKED_OPERATOR_ABSTAIN"
        elif not world_verified:
            status = "WORLD_CYCLE_BLOCKED_EXTERNAL_ATTESTATION_REQUIRED"
        elif not quantitative_model:
            status = "WORLD_CYCLE_BLOCKED_QUANTITATIVE_MODEL_REQUIRED"
        else:
            status = "WORLD_CYCLE_BLOCKED_PREDICTIVE_MODEL_OR_EIG_INPUTS_REQUIRED"

        payload = {
            "schema": "phi-pharmaceutical-world-cycle/v8.3",
            "owner_id": OWNER_ID,
            "problem_id": problem.get("problem_id"),
            "serialized_source_verification_status_trusted": False,
            "source_verification": {
                "overall_status": source_verification.get("overall_status"),
                "verification_digest": source_verification.get("verification_digest"),
                "scientific_candidate_allowed": source_verification.get("scientific_candidate_allowed") is True,
                "expected_problem_binding_digest": expected_problem_binding,
                "verified_problem_binding_digest": verified_problem_binding,
                "problem_binding_pass": problem_binding_pass,
                "world_verified_for_this_problem": world_verified,
            },
            "quantitative_model": quantitative_model or {"status": "NOT_MATERIALIZED"},
            "candidate_region": dict(plan.get("candidate", {})) if has_operator else {"status": "NOT_MATERIALIZED_OPERATOR_ABSTAIN"},
            "falsifiers": falsifier_templates.get(operator_id, []),
            "next_experiment": dict(plan.get("next_experiment", {})) if has_operator else {"status": "NOT_MATERIALIZED_OPERATOR_ABSTAIN"},
            "predictive_model": {
                "present": bool(predictive),
                "digest": predictive_digest or None,
                "world_verified": predictive_world_verified,
                "binding_pass": predictive_binding_pass,
                "uncertainty_model_declared": uncertainty_declared,
                "predictive_likelihoods_declared": predictive_likelihoods_declared,
            },
            "expected_information_gain": (
                {
                    "computed": True,
                    "status": "EIG_RANKED_BY_EXISTING_DOMAIN_NEUTRAL_OWNER",
                    "invented_probabilities": False,
                    "owner": eig_receipt.get("owner"),
                    "selected_experiment_id": eig_receipt.get("selected_experiment_id"),
                    "receipt": dict(eig_receipt),
                }
                if eig_computed else {
                    "computed": False,
                    "status": "BLOCKED_WORLD_VERIFICATION_PREDICTIVE_LIKELIHOODS_AND_UNCERTAINTY_REQUIRED",
                    "invented_probabilities": False,
                }
            ),
            "blocking_uncertainties": list(dict.fromkeys(blockers)),
            "scientific_promotion_allowed": False,
            "world_cycle_complete": world_cycle_complete,
            "status": status,
        }
        return {**payload, "digest": digest_payload(payload)}

    @staticmethod
    def _evidence_gap_plan(record: Mapping[str, Any], world_verified: bool) -> Mapping[str, Any]:
        gap = dict(record.get("evidence_gap", {}))
        outcomes = [str(x) for x in gap.get("required_outcomes", ())]
        comparators = [str(x) for x in gap.get("comparators", ())]
        missing = [str(x) for x in gap.get("missing_evidence", ())]
        return {
            "status": "EVIDENCE_GAP_RECORDED_WORLD_VERIFICATION_REQUIRED" if not world_verified else "EVIDENCE_GAP_VERIFIED_READY_FOR_EXPERIMENT_DESIGN",
            "decision_question": gap.get("decision_question"),
            "comparators": comparators,
            "required_outcomes": outcomes,
            "missing_evidence": missing,
            "sample_size_invented": False,
            "dose_invented": False,
            "expected_information_gain_computed": False,
            "next_step": "BUILD_PREDECLARED_PREDICTIVE_OR_TRIAL_MODEL_BEFORE_EIG",
        }

    def load_atlas(self, path: str | Path, verification_bundles: Mapping[str, Mapping[str, Any]] | None = None) -> Mapping[str, Any]:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        records = list(doc.get("problems", ()))
        bundles = dict(verification_bundles or {})
        rows = [self.ingest_problem(r, bundles.get(str(r.get("problem_id")))) for r in records]
        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "source_collection": doc.get("source_collection"),
            "problem_count": len(rows),
            "world_verified_problem_count": sum(r["source_verification_status"] == WORLD_VERIFIED for r in rows),
            "evidence_gap_count": sum(r.get("problem_type") == "EVIDENCE_GAP" for r in rows),
            "operator_counts": {op: sum(r.get("research_operator") == op for r in rows) for op in RESEARCH_OPERATORS},
            "rows": rows,
            "claim_boundary": {
                "source_collection_ingested_as_world_truth": False,
                "new_drug_discovered": False,
                "clinical_efficacy_established": False,
                "world_novelty_established": False,
                "problem_atlas_is_scientific_promotion": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}
