"""First post-clean Atlas-native blind interaction experiment for release 15.7.0.

The controlled world is generated deterministically inside this qualification.
The hidden response law is used ONLY by the fixture generator and by the final
verification block; it is not passed to AdaptiveResearchKernelOwner.  The
initial model receives `drive` as its only active predictor. `medium_state` is
observable but dormant, and may enter the formula space only after residual
axis discovery activates it.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from source.lawspace.api import LawSpaceAPI
from source.lawspace.schema import digest_payload

OWNER_ID = "FIRST-POST-CLEAN-ATLAS-EXPERIMENT/15.7.0"
SCHEMA = "phi-first-post-clean-atlas-experiment/v1"
PROBLEM_ID = "CLEAN-FIRST-BLIND-INTERACTION-001"


def _build_world() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    # Hidden control-world generator. This formula is never supplied to Atlas.
    xs = (-2.5, -2.0, -1.5, -1.0, -0.5, 0.5, 1.0, 1.5, 2.0, 2.5)
    zs = (-1.2, -0.6, 0.0, 0.6, 1.2)
    rows: list[dict[str, Any]] = []
    for i, x in enumerate(xs):
        for j, _ in enumerate(zs):
            z = zs[(2 * j + 3 * i) % len(zs)]
            y = 0.7 + 1.2 * x + 0.45 * x * z
            rows.append({
                "record_id": f"D-{i:02d}-{j:02d}",
                "study_id": f"D-{i:02d}-{j:02d}",
                "values": {"drive": x, "medium_state": z, "response": y},
            })
    rows = rows[::2] + rows[1::2]

    holdout: list[dict[str, Any]] = []
    holdout_x = (-2.25, -1.75, -1.25, -0.75, -0.25, 0.25, 0.75, 1.25, 1.75, 2.25)
    holdout_z = (1.0, -1.0, 0.5, -0.5, 0.25, -0.25, 0.75, -0.75, 1.1, -1.1)
    for i, (x, z) in enumerate(zip(holdout_x, holdout_z)):
        y = 0.7 + 1.2 * x + 0.45 * x * z
        holdout.append({
            "record_id": f"H-{i:02d}",
            "study_id": f"H-{i:02d}",
            "values": {"drive": x, "medium_state": z, "response": y},
        })
    return rows, holdout


def _request() -> dict[str, Any]:
    observations, sealed_holdout = _build_world()
    dimensionless = [0, 0, 0, 0, 0, 0, 0]
    return {
        "problem_id": PROBLEM_ID,
        "domain_id": "physics",
        "question": (
            "In a sealed controlled response world, discover whether response is closed by drive alone "
            "or whether residual evidence requires activation of the independently observed medium_state coordinate."
        ),
        "observations": observations,
        "sealed_holdout_observations": sealed_holdout,
        "target_variable": "response",
        "predictor_variables": ["drive"],
        "dormant_axis_variables": ["medium_state"],
        "variable_dimensions": {
            "response": dimensionless,
            "drive": dimensionless,
            "medium_state": dimensionless,
        },
        "complexity_level": 2,
        "fit_tolerance_nrmse": 1e-10,
        "observations_origin": "CONTROL_REFERENCE",
        "auto_activate_dormant_axes": True,
        "experiment_points": [
            {"drive": 1.5, "medium_state": -1.0},
            {"drive": 1.5, "medium_state": 1.0},
            {"drive": -1.5, "medium_state": -1.0},
            {"drive": -1.5, "medium_state": 1.0},
        ],
    }


def run(root: str | Path | None = None) -> dict[str, Any]:
    root = Path(root or Path(__file__).resolve().parents[1]).resolve()
    receipt = LawSpaceAPI(root).advance_adaptive_research(_request())
    result = receipt["result"]
    initial_candidates = receipt.get("initial_hypothesis_space", {}).get("candidates", [])
    initial_best = initial_candidates[0] if initial_candidates else {}
    best = result.get("best_hypothesis") or {}
    params = list(best.get("parameters", ()))
    sealed = result.get("sealed_holdout_evaluation", {})
    activation = result.get("axis_activation_improvement", {})
    expression = str(best.get("expression", ""))

    checks = {
        "INITIAL_SPACE_HAS_ONLY_DRIVE": receipt.get("initial_hypothesis_space", {}).get("predictor_variables") == ["drive"],
        "DORMANT_AXIS_NOT_INSERTED_INITIAL_FORMULA": "medium_state" not in str(initial_best.get("expression", "")),
        "INITIAL_MODEL_FAILS_TOLERANCE": float(initial_best.get("holdout_nrmse", 0.0)) > 1e-2,
        "RESIDUAL_DISCOVERS_MEDIUM_STATE": "medium_state" in result.get("research_local_axis_candidates", []),
        "RESIDUAL_ACTIVATES_MEDIUM_STATE": result.get("activated_axis_variables") == ["medium_state"],
        "ACTIVATION_IMPROVES_HELDOUT_ERROR": bool(activation.get("improved")) and float(activation.get("relative_improvement", 0.0)) > 0.99,
        "ATLAS_BIRTHS_INTERACTION_TERM": "drive*medium_state" in expression,
        "BORN_MODEL_IS_SPARSE_DRIVE_PLUS_INTERACTION": expression == "c0 + c1*drive + c2*drive*medium_state",
        "RECOVERED_CONTROL_PARAMETERS": len(params) == 3 and abs(params[0]-0.7) < 1e-12 and abs(params[1]-1.2) < 1e-12 and abs(params[2]-0.45) < 1e-12,
        "SEALED_HOLDOUT_EVALUATED": sealed.get("status") == "SEALED_HOLDOUT_EVALUATED" and sealed.get("count") == 10,
        "SEALED_HOLDOUT_NEAR_MACHINE_PRECISION": float(sealed.get("nrmse", 1.0)) < 1e-12,
        "CLAIM_FIREWALL_ACCEPTS_ATLAS_NATIVE_RECEIPT": receipt.get("atlas_claim", {}).get("atlas_native") is True,
        "ATLAS_NATIVE_NOT_PROMOTED_TO_WORLD_LAW": receipt.get("atlas_claim", {}).get("scientific_truth_established") is False and result.get("scientific_law_established") is False,
        "NO_HIDDEN_LAW_PASSED_IN_REQUEST": "formula" not in _request() and "expected_expression" not in _request(),
        "DISCRIMINATING_EXPERIMENT_RANKED": receipt.get("discriminating_experiment", {}).get("selected_experiment_id") is not None,
    }
    passed = sum(bool(v) for v in checks.values())
    payload = {
        "schema": SCHEMA,
        "owner": OWNER_ID,
        "problem_id": PROBLEM_ID,
        "status": "PASS_FIRST_POST_CLEAN_ATLAS_EXPERIMENT" if passed == len(checks) else "FAIL_FIRST_POST_CLEAN_ATLAS_EXPERIMENT",
        "passed": passed,
        "total": len(checks),
        "checks": [{"check": k, "status": "PASS" if v else "FAIL"} for k, v in checks.items()],
        "blind_protocol": {
            "active_predictors_at_start": ["drive"],
            "dormant_observable_axes": ["medium_state"],
            "hidden_control_generator_disclosed_to_kernel": False,
            "sealed_holdout_used_for_axis_activation": False,
            "complexity_shell": 2,
        },
        "result_summary": {
            "initial_expression": initial_best.get("expression"),
            "initial_holdout_nrmse": initial_best.get("holdout_nrmse"),
            "activated_axes": result.get("activated_axis_variables"),
            "born_expression": best.get("expression"),
            "recovered_parameters": params,
            "post_activation_holdout_nrmse": best.get("holdout_nrmse"),
            "sealed_holdout_nrmse": sealed.get("nrmse"),
            "selected_discriminating_experiment_id": receipt.get("discriminating_experiment", {}).get("selected_experiment_id"),
            "atlas_claim_status": receipt.get("atlas_claim", {}).get("status"),
        },
        "execution_receipt": receipt,
        "claim_boundary": {
            "this_is_a_controlled_world_not_a_new_physical_law": True,
            "atlas_native_means_execution_provenance_not_world_truth": True,
            "scientific_discovery_established": False,
            "proof_of_post_clean_research_cycle_execution": passed == len(checks),
        },
    }
    return {**payload, "digest": digest_payload(payload)}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, sort_keys=True))
