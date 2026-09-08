from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from source.lawspace.experiment_portfolio import PostGateExperimentPortfolioOwner
from source.lawspace.schema import digest_payload
from evaluation.pharmaceutical_semantic_qualification import run_release_qualification as run_current_pharmaceutical_qualification


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run_release_qualification(root: Path | str) -> dict[str, Any]:
    root = Path(root)
    owner = PostGateExperimentPortfolioOwner()

    aero = _read(root / "reports" / "aero_realdata_full_research_cycle_v6_24.json")
    cycle = aero["planning_cycle"]
    eig = cycle["information_gain"]
    baseline = owner.rank_from_research_cycle(research_cycle=cycle, information_gain=eig)
    expensive_11hz = owner.rank_from_research_cycle(
        research_cycle=cycle,
        information_gain=eig,
        scenario={
            "scenario_id": "WHAT_IF_11HZ_COST_X5",
            "experiment_cost_multipliers": {"DLR-FIG16-HOLDOUT-11HZ": 5.0},
        },
    )

    # Current pharmaceutical eligibility is recomputed from the authoritative
    # executable qualification.  The portfolio owner must not depend on archived
    # version-specific report files.
    pharma_current_qualification = run_current_pharmaceutical_qualification(root)
    pharma_current = [
        owner.assess_pharmaceutical_eligibility(row["assessment"])
        for row in pharma_current_qualification["rows"]
    ]

    # A synthetic provenance-only canary proves that a retained result from any
    # unregistered/noncurrent pharma owner cannot bypass the current owner/schema gate.
    # No historical report is required in the active release.
    unregistered_canary = dict(pharma_current_qualification["rows"][0]["assessment"])
    unregistered_canary.update({
        "owner_id": "PHARMACEUTICAL-DOMAIN/UNREGISTERED-CANARY",
        "schema": "phi-pharmaceutical-domain/unregistered-canary",
        "retained_for_research": True,
        "promotion_allowed": False,
        "critical_failed_gates": [],
    })
    unregistered_rejected = [owner.assess_pharmaceutical_eligibility(unregistered_canary)]

    screening_freeze = _read(root / "data" / "pharmaceutical" / "frozen_discovery_candidates_v8_1.json")
    screening_admission = [owner.assess_screening_candidate(row) for row in screening_freeze["candidates"]]
    loxt_corr = _read(root / "reports" / "pharmaceutical_loxl3_hfpef_prior_art_correction_v8_1.json")

    blocked_quadrants = owner.quadrant_view(
        portfolio_receipt=baseline,
        eig_threshold_bits=None,
        cost_threshold=None,
    )
    explicit_quadrants = owner.quadrant_view(
        portfolio_receipt=baseline,
        eig_threshold_bits=0.1,
        cost_threshold=1.0,
    )

    checks = [
        ("CONTRACT_HAS_NO_PROMOTION_AUTHORITY", owner.contract()["scientific_promotion_authority"] is False),
        ("REAL_DLR_RESEARCH_CYCLE_ELIGIBLE", baseline["eligibility"]["research_eligible"] is True),
        ("REAL_DLR_EIG_SELECTS_11HZ_UNIQUE_PARETO", baseline["selected_next_experiment_id"] == "DLR-FIG16-HOLDOUT-11HZ"),
        ("REAL_DLR_EIG_VALUES_PRESERVED", [round(x["expected_information_gain_bits"], 15) for x in baseline["experiments"]] == [round(0.20973872422819406, 15), round(0.061012018558382675, 15)]),
        ("WHAT_IF_COST_CHANGE_DOES_NOT_FORCE_SCALAR_WINNER", expensive_11hz["status"] == "PARETO_FRONTIER_REQUIRES_POLICY_OR_MORE_METRICS" and set(expensive_11hz["pareto_frontier_experiment_ids"]) == {"DLR-FIG16-HOLDOUT-11HZ", "DLR-FIG16-HOLDOUT-7HZ"}),
        ("CURRENT_V8_PHARMA_FAIL_CLOSED_NOT_PORTFOLIO_ELIGIBLE", all(not x["research_eligible"] for x in pharma_current)),
        ("UNREGISTERED_OWNER_CANNOT_BYPASS_CURRENT_GATE", bool(unregistered_rejected) and all((not x["research_eligible"] and x["reason"] == "BLOCKED_UNREGISTERED_OR_NONCURRENT_PHARMACEUTICAL_OWNER") for x in unregistered_rejected)),
        ("QUADRANTS_REQUIRE_EXPLICIT_THRESHOLDS", blocked_quadrants["status"] == "BLOCKED_EXPLICIT_THRESHOLDS_REQUIRED"),
        ("QUADRANTS_DISPLAY_ONLY", explicit_quadrants["status"] == "DISPLAY_ONLY_QUADRANTS" and explicit_quadrants["claim_boundary"]["quadrants_are_promotion_authority"] is False),
        ("PORTFOLIO_NEVER_MODIFIES_SCIENTIFIC_STATUS", baseline["claim_boundary"]["scientific_status_modified"] is False and baseline["claim_boundary"]["promotion_allowed_by_portfolio"] is False),
        ("NO_WEIGHTED_BUSINESS_LOSS", baseline["claim_boundary"]["weighted_business_loss_used"] is False),
        ("NEW_DRUG_SCREENING_FREEZE_NOT_POST_GATE_RANKED", all(not x["research_eligible"] for x in screening_admission)),
        ("LOXL3_HFPEF_RESTORED_AFTER_SOURCE_LOCK_CORRECTION", loxt_corr["corrected_status"] == "OPEN_PRIOR_ART_BOUNDARY_UNRESOLVED_WORLD_VERIFICATION_REQUIRED" and loxt_corr["claim_boundary"]["exact_patent_novelty_established"] is False),
    ]
    passed = sum(int(ok) for _, ok in checks)
    report = {
        "schema": "phi-post-gate-experiment-portfolio-qualification/v8.1",
        "owner_id": owner.owner_id,
        "status": "PASS_POST_GATE_EXPERIMENT_PORTFOLIO_V8_1" if passed == len(checks) else "FAIL_POST_GATE_EXPERIMENT_PORTFOLIO_V8_1",
        "passed": passed,
        "total": len(checks),
        "checks": [{"check": name, "pass": bool(ok)} for name, ok in checks],
        "real_dlr_baseline": baseline,
        "real_dlr_what_if_11hz_cost_x5": expensive_11hz,
        "current_v8_pharmaceutical_eligibility": pharma_current,
        "unregistered_owner_gate_canary": unregistered_rejected,
        "quadrant_missing_threshold_canary": blocked_quadrants,
        "quadrant_explicit_threshold_canary": explicit_quadrants,
        "screening_candidate_admission": screening_admission,
        "loxl3_hfpef_prior_art_correction": loxt_corr,
        "claim_boundary": {
            "scientific_status_changed": False,
            "business_loss_used": False,
            "real_positive_control_is_dlr_realdata_cycle_not_synthetic_full_data": True,
            "pharmaceutical_candidates_ranked_without_v8_verification": False,
        },
    }
    report["digest"] = digest_payload(report)
    return report


if __name__ == "__main__":
    import sys
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    out = run_release_qualification(root)
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
