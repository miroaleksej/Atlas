"""Post-gate experiment portfolio prioritization for Φ-LawSpace v8.1.

This owner allocates research resources *only after* an authoritative scientific
or research-cycle gate has admitted work for further testing.  It cannot change
scientific status, cannot resurrect failed candidates, and never invents EIG,
cost, duration, readiness, or risk values.

Decision architecture:
    scientific/domain gates -> post-gate eligibility -> experiment metrics
    -> Pareto frontier -> optional scenario/quadrant views -> next experiment

No weighted "Business Loss" exists here.  A unique next experiment is returned
only when the declared Pareto axes leave a unique non-dominated option.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence
import math

from .schema import digest_payload

OWNER_ID = "POST-GATE-EXPERIMENT-PORTFOLIO/8.1.0"
SCHEMA = "phi-post-gate-experiment-portfolio/v8.1"

# Current authoritative sources that may establish *research eligibility*.
# This is deliberately narrower than arbitrary user-supplied status strings.
_PHARMA_OWNER = "PHARMACEUTICAL-RESEARCH-DOMAIN/8.2.0"
_PHARMA_SCHEMA = "phi-pharmaceutical-research-domain/v8.2"
_RESEARCH_CYCLE_OWNER = "SCIENTIFIC-RESEARCH-CYCLE/6.24.0"
_RESEARCH_CYCLE_SCHEMA = "phi-scientific-research-cycle/v6.24"
_EIG_OWNER = "DOMAIN-NEUTRAL-INFORMATION-GAIN/6.24.0"
_EIG_SCHEMA = "phi-domain-neutral-eig/v6.24"


def _without_digest(row: Mapping[str, Any]) -> dict[str, Any]:
    return {str(k): v for k, v in row.items() if k != "digest"}


def _digest_valid(row: Mapping[str, Any]) -> bool:
    expected = str(row.get("digest", ""))
    return bool(expected) and expected == digest_payload(_without_digest(row))


def _finite_positive(value: Any) -> bool:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(v) and v > 0.0


def _finite_nonnegative(value: Any) -> bool:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(v) and v >= 0.0


@dataclass(frozen=True)
class PortfolioScenario:
    """Explicit what-if multipliers.  No default economic assumptions."""

    scenario_id: str = "BASELINE"
    experiment_cost_multipliers: Mapping[str, float] = field(default_factory=dict)
    experiment_duration_multipliers: Mapping[str, float] = field(default_factory=dict)
    experiment_risk_multipliers: Mapping[str, float] = field(default_factory=dict)

    def validate(self) -> None:
        if not str(self.scenario_id).strip():
            raise ValueError("scenario_id must be non-empty")
        for mapping, label in (
            (self.experiment_cost_multipliers, "cost"),
            (self.experiment_duration_multipliers, "duration"),
            (self.experiment_risk_multipliers, "risk"),
        ):
            for experiment_id, value in mapping.items():
                if not str(experiment_id).strip() or not _finite_positive(value):
                    raise ValueError(f"{label} multipliers must be finite and positive")


class PostGateExperimentPortfolioOwner:
    owner_id = OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "scope": "POST_GATE_RESOURCE_ALLOCATION_ONLY",
            "hard_invariants": {
                "post_gate_priority_cannot_modify_scientific_status": True,
                "failed_or_rejected_candidate_cannot_be_resurrected": True,
                "no_business_loss_or_weighted_validity_score": True,
                "no_eig_without_explicit_predictive_likelihood_receipt": True,
                "no_missing_cost_time_risk_readiness_imputation": True,
                "pareto_dominance_precedes_any_optional_display_metric": True,
                "quadrant_thresholds_must_be_explicit": True,
                "serialized_portfolio_receipt_is_not_scientific_promotion": True,
            },
            "default_pareto_axes": {
                "maximize": ["expected_information_gain_bits"],
                "minimize": ["scenario_cost"],
            },
            "scientific_promotion_authority": False,
        }
        return {**payload, "digest": digest_payload(payload)}

    def assess_research_cycle_eligibility(self, cycle: Mapping[str, Any]) -> Mapping[str, Any]:
        gates = dict(cycle.get("gates", {}))
        eligible = (
            cycle.get("owner") == _RESEARCH_CYCLE_OWNER
            and cycle.get("schema") == _RESEARCH_CYCLE_SCHEMA
            and cycle.get("status") == "RESEARCH_CYCLE_CONTRACT_PASS"
            and bool(gates)
            and all(v is True for v in gates.values())
            and _digest_valid(cycle)
        )
        payload = {
            "source_owner": cycle.get("owner"),
            "source_schema": cycle.get("schema"),
            "source_digest": cycle.get("digest"),
            "source_digest_valid": _digest_valid(cycle),
            "source_status": cycle.get("status"),
            "research_eligible": bool(eligible),
            "reason": "POST_GATE_RESEARCH_CYCLE_PASS" if eligible else "BLOCKED_RESEARCH_CYCLE_NOT_AUTHORITATIVELY_ELIGIBLE",
            "scientific_status_modified": False,
        }
        return {**payload, "digest": digest_payload(payload)}

    def assess_screening_candidate(self, candidate: Mapping[str, Any]) -> Mapping[str, Any]:
        payload = {
            "candidate_id": candidate.get("candidate_id"),
            "domain_id": candidate.get("domain_id"),
            "screening_status": candidate.get("screening_status"),
            "research_eligible": False,
            "reason": "BLOCKED_SCREENING_CANDIDATE_REQUIRES_AUTHORITATIVE_POST_GATE_ASSESSMENT",
            "scientific_status_modified": False,
            "promotion_allowed_by_portfolio": False,
        }
        return {**payload, "digest": digest_payload(payload)}

    def assess_pharmaceutical_eligibility(self, assessment: Mapping[str, Any]) -> Mapping[str, Any]:
        failed = tuple(str(x) for x in assessment.get("critical_failed_gates", ()))
        retained = assessment.get("retained_for_research") is True
        promoted = assessment.get("promotion_allowed") is True
        current_owner = assessment.get("owner_id") == _PHARMA_OWNER and assessment.get("schema") == _PHARMA_SCHEMA
        eligible = current_owner and not failed and (retained or promoted)
        if not current_owner:
            reason = "BLOCKED_UNREGISTERED_OR_NONCURRENT_PHARMACEUTICAL_OWNER"
        elif failed:
            reason = "BLOCKED_CRITICAL_SCIENTIFIC_GATE_FAILED"
        elif not (retained or promoted):
            reason = "BLOCKED_NOT_RETAINED_OR_PROMOTED"
        else:
            reason = "POST_GATE_PHARMACEUTICAL_RESEARCH_ELIGIBLE"
        payload = {
            "source_owner": assessment.get("owner_id"),
            "source_schema": assessment.get("schema"),
            "source_assessment_digest": assessment.get("assessment_digest"),
            "source_status": assessment.get("overall_status"),
            "retained_for_research": retained,
            "promotion_allowed": promoted,
            "critical_failed_gates": list(failed),
            "research_eligible": bool(eligible),
            "reason": reason,
            "scientific_status_modified": False,
        }
        return {**payload, "digest": digest_payload(payload)}

    @staticmethod
    def _validate_eig_receipt(eig: Mapping[str, Any], expected_candidate_ids: Sequence[str]) -> tuple[bool, str]:
        if eig.get("owner") != _EIG_OWNER or eig.get("schema") != _EIG_SCHEMA:
            return False, "EIG_OWNER_OR_SCHEMA_MISMATCH"
        if eig.get("status") != "EIG_RANKED":
            return False, "EIG_NOT_RANKED"
        if not _digest_valid(eig):
            return False, "EIG_DIGEST_INVALID"
        if tuple(str(x) for x in eig.get("candidate_ids", ())) != tuple(str(x) for x in expected_candidate_ids):
            return False, "EIG_CANDIDATE_SET_MISMATCH"
        return True, "PASS"

    @staticmethod
    def _dominates(a: Mapping[str, Any], b: Mapping[str, Any], maximize: Sequence[str], minimize: Sequence[str]) -> bool:
        comparable = True
        weak_all = True
        strict_any = False
        for key in maximize:
            av, bv = a.get(key), b.get(key)
            if av is None or bv is None:
                comparable = False
                break
            av, bv = float(av), float(bv)
            weak_all = weak_all and av >= bv
            strict_any = strict_any or av > bv
        if comparable:
            for key in minimize:
                av, bv = a.get(key), b.get(key)
                if av is None or bv is None:
                    comparable = False
                    break
                av, bv = float(av), float(bv)
                weak_all = weak_all and av <= bv
                strict_any = strict_any or av < bv
        return comparable and weak_all and strict_any

    def rank_from_research_cycle(
        self,
        *,
        research_cycle: Mapping[str, Any],
        information_gain: Mapping[str, Any],
        resource_metrics: Mapping[str, Mapping[str, Any]] | None = None,
        scenario: PortfolioScenario | Mapping[str, Any] | None = None,
        maximize_axes: Sequence[str] = ("expected_information_gain_bits",),
        minimize_axes: Sequence[str] = ("scenario_cost",),
    ) -> Mapping[str, Any]:
        eligibility = self.assess_research_cycle_eligibility(research_cycle)
        if not eligibility["research_eligible"]:
            payload = {
                "schema": SCHEMA,
                "owner_id": OWNER_ID,
                "status": "BLOCKED_NO_POST_GATE_ELIGIBILITY",
                "eligibility": eligibility,
                "experiments": [],
                "pareto_frontier_experiment_ids": [],
                "selected_next_experiment_id": None,
                "scientific_status_modified": False,
                "promotion_allowed_by_portfolio": False,
            }
            return {**payload, "digest": digest_payload(payload)}

        competitive = research_cycle.get("competitive_set", {})
        candidate_ids = tuple(str(row.get("candidate_id")) for row in competitive.get("candidates", ()))
        if not candidate_ids:
            candidate_ids = tuple(str(x) for x in information_gain.get("candidate_ids", ()))
        valid_eig, eig_reason = self._validate_eig_receipt(information_gain, candidate_ids)
        if not valid_eig:
            payload = {
                "schema": SCHEMA,
                "owner_id": OWNER_ID,
                "status": "BLOCKED_VERIFIED_EIG_REQUIRED",
                "eligibility": eligibility,
                "eig_validation_reason": eig_reason,
                "experiments": [],
                "pareto_frontier_experiment_ids": [],
                "selected_next_experiment_id": None,
                "scientific_status_modified": False,
                "promotion_allowed_by_portfolio": False,
            }
            return {**payload, "digest": digest_payload(payload)}

        if scenario is None:
            scenario_obj = PortfolioScenario()
        elif isinstance(scenario, PortfolioScenario):
            scenario_obj = scenario
        else:
            scenario_obj = PortfolioScenario(**dict(scenario))
        scenario_obj.validate()
        resource_metrics = {str(k): dict(v) for k, v in (resource_metrics or {}).items()}

        experiments: list[dict[str, Any]] = []
        for row in information_gain.get("experiments", ()):
            experiment_id = str(row.get("experiment_id", ""))
            base_cost = row.get("cost")
            if not _finite_positive(base_cost):
                # Existing EIG owner already requires cost, but fail closed here too.
                continue
            metrics = resource_metrics.get(experiment_id, {})
            duration = metrics.get("duration_days") if _finite_positive(metrics.get("duration_days")) else None
            risk = metrics.get("execution_risk") if _finite_nonnegative(metrics.get("execution_risk")) else None
            readiness = metrics.get("readiness")
            if readiness is not None:
                try:
                    readiness = float(readiness)
                except (TypeError, ValueError):
                    readiness = None
                if readiness is not None and (not math.isfinite(readiness) or not (0.0 <= readiness <= 1.0)):
                    readiness = None
            decisive = metrics.get("probability_decisive")
            if decisive is not None:
                try:
                    decisive = float(decisive)
                except (TypeError, ValueError):
                    decisive = None
                if decisive is not None and (not math.isfinite(decisive) or not (0.0 <= decisive <= 1.0)):
                    decisive = None

            cm = float(scenario_obj.experiment_cost_multipliers.get(experiment_id, 1.0))
            dm = float(scenario_obj.experiment_duration_multipliers.get(experiment_id, 1.0))
            rm = float(scenario_obj.experiment_risk_multipliers.get(experiment_id, 1.0))
            eig = float(row.get("expected_information_gain_bits", 0.0))
            scenario_cost = float(base_cost) * cm
            scenario_duration = None if duration is None else duration * dm
            scenario_risk = None if risk is None else risk * rm
            experiments.append({
                "experiment_id": experiment_id,
                "candidate_ids": list(candidate_ids),
                "expected_information_gain_bits": eig,
                "base_cost": float(base_cost),
                "scenario_cost": scenario_cost,
                "duration_days": duration,
                "scenario_duration_days": scenario_duration,
                "execution_risk": risk,
                "scenario_execution_risk": scenario_risk,
                "readiness": readiness,
                "probability_decisive": decisive,
                "gates_addressed": list(metrics.get("gates_addressed", ())),
                "eig_per_cost_display_only": eig / scenario_cost,
                "scientific_status_modified": False,
            })

        maximize_axes = tuple(str(x) for x in maximize_axes)
        minimize_axes = tuple(str(x) for x in minimize_axes)
        usable = [r for r in experiments if all(r.get(k) is not None for k in maximize_axes + minimize_axes)]
        frontier: list[dict[str, Any]] = []
        for row in usable:
            if not any(self._dominates(other, row, maximize_axes, minimize_axes) for other in usable if other is not row):
                frontier.append(row)
        frontier.sort(key=lambda r: str(r["experiment_id"]))
        frontier_ids = [r["experiment_id"] for r in frontier]
        selected = frontier_ids[0] if len(frontier_ids) == 1 else None
        status = "UNIQUE_PARETO_NEXT_EXPERIMENT" if selected else (
            "PARETO_FRONTIER_REQUIRES_POLICY_OR_MORE_METRICS" if frontier_ids else "BLOCKED_PARETO_AXES_INCOMPLETE"
        )
        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "status": status,
            "eligibility": eligibility,
            "scenario": {
                "scenario_id": scenario_obj.scenario_id,
                "experiment_cost_multipliers": dict(scenario_obj.experiment_cost_multipliers),
                "experiment_duration_multipliers": dict(scenario_obj.experiment_duration_multipliers),
                "experiment_risk_multipliers": dict(scenario_obj.experiment_risk_multipliers),
            },
            "pareto_axes": {"maximize": list(maximize_axes), "minimize": list(minimize_axes)},
            "experiments": experiments,
            "pareto_frontier_experiment_ids": frontier_ids,
            "selected_next_experiment_id": selected,
            "claim_boundary": {
                "scientific_status_modified": False,
                "promotion_allowed_by_portfolio": False,
                "pareto_rank_is_scientific_validity": False,
                "eig_is_not_probability_candidate_true": True,
                "missing_metrics_imputed": False,
                "weighted_business_loss_used": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    def quadrant_view(
        self,
        *,
        portfolio_receipt: Mapping[str, Any],
        eig_threshold_bits: float | None,
        cost_threshold: float | None,
    ) -> Mapping[str, Any]:
        if eig_threshold_bits is None or cost_threshold is None:
            payload = {
                "schema": "phi-post-gate-quadrant-view/v8.1",
                "owner_id": OWNER_ID,
                "status": "BLOCKED_EXPLICIT_THRESHOLDS_REQUIRED",
                "quadrants": {},
                "scientific_status_modified": False,
            }
            return {**payload, "digest": digest_payload(payload)}
        if not _finite_nonnegative(eig_threshold_bits) or not _finite_positive(cost_threshold):
            raise ValueError("quadrant thresholds must be finite; cost must be positive")
        quadrants = {
            "LOW_COST_HIGH_EIG": [],
            "LOW_COST_LOW_EIG": [],
            "HIGH_COST_HIGH_EIG": [],
            "HIGH_COST_LOW_EIG": [],
        }
        for row in portfolio_receipt.get("experiments", ()):
            eig, cost = row.get("expected_information_gain_bits"), row.get("scenario_cost")
            if eig is None or cost is None:
                continue
            low_cost = float(cost) <= float(cost_threshold)
            high_eig = float(eig) >= float(eig_threshold_bits)
            key = ("LOW_COST_" if low_cost else "HIGH_COST_") + ("HIGH_EIG" if high_eig else "LOW_EIG")
            quadrants[key].append(str(row.get("experiment_id")))
        payload = {
            "schema": "phi-post-gate-quadrant-view/v8.1",
            "owner_id": OWNER_ID,
            "status": "DISPLAY_ONLY_QUADRANTS",
            "thresholds": {"eig_threshold_bits": float(eig_threshold_bits), "cost_threshold": float(cost_threshold)},
            "quadrants": quadrants,
            "claim_boundary": {
                "quadrants_are_scientific_status": False,
                "quadrants_are_promotion_authority": False,
                "thresholds_are_user_or_policy_inputs_not_discovered_truth": True,
            },
            "scientific_status_modified": False,
        }
        return {**payload, "digest": digest_payload(payload)}


__all__ = ["PostGateExperimentPortfolioOwner", "PortfolioScenario", "OWNER_ID", "SCHEMA"]
