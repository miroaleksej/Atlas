from __future__ import annotations

import math
from pathlib import Path

from source.lawspace.api import LawSpaceAPI

DIM_LENGTH = [1, 0, 0, 0, 0, 0, 0]
DIM_VELOCITY = [1, 0, -1, 0, 0, 0, 0]
DIM_ACCELERATION = [1, 0, -2, 0, 0, 0, 0]


def _study(study_id: str, role: str, slope: float, offset: float) -> dict:
    x = [0.05 * i for i in range(25)]
    u = [offset + slope * xx for xx in x]
    target = [-0.5 * uu * slope for uu in u]
    return {
        "study_id": study_id,
        "role": role,
        "coordinate_order": ["x"],
        "coordinates": {"x": x},
        "fields": {"u": u, "q": target},
    }


def test_direct_target_field_is_excluded_and_recovered() -> None:
    root = Path(__file__).resolve().parents[1]
    api = LawSpaceAPI(root)
    request = {
        "entry_mode": "PRIMITIVE_FIELD_RESIDUAL_LANGUAGE_DISCOVERY",
        "residual_driven_language_expansion": True,
        "problem_id": "DIRECT-TARGET-RESIDUAL-QUALIFICATION",
        "domain_id": "mechanics",
        "question": "Explain an attested scalar residual field from primitive predictor fields without using the target field as a predictor.",
        "fit_tolerance_nrmse": 1.0e-8,
        "operator_language_search_budget": 4,
        "residual_language_factor_depth_budget": 2,
        "axis_birth_trial_budget": 256,
        "primitive_field_request": {
            "studies": [
                _study("D1", "DISCOVERY", 0.31, 1.20),
                _study("D2", "DISCOVERY", -0.23, 1.45),
                _study("D3", "DISCOVERY", 0.17, 0.92),
                _study("H1", "SEALED_HOLDOUT", 0.27, 1.07),
                _study("H2", "SEALED_HOLDOUT", -0.19, 1.31),
            ],
            "coordinate_dimensions": {"x": DIM_LENGTH},
            "field_dimensions": {"u": DIM_VELOCITY, "q": DIM_ACCELERATION},
            "target_field": "q",
            "target_action_mode": "DIRECT_FIELD_VALUE",
            "predictor_fields": ["u"],
        },
    }
    receipt = api.advance_adaptive_research(request)
    assert receipt["atlas_claim"]["atlas_native"] is True
    final = receipt["final_language_receipt"]
    language = final["operator_language_invention"]
    assert language["target_action_mode"] == "DIRECT_FIELD_VALUE"
    assert language["target_field_excluded_from_predictor_language"] is True
    assert language["predictor_fields"] == ["u"]
    assert all(spec.get("response_field") != "q" for spec in language["generated_signatures"])
    for spec in language["generated_signatures"]:
        assert spec.get("carrier_field") != "q"
        assert all(f.get("field") != "q" for f in spec.get("carrier_factors", []))
    result = receipt["result"]
    assert result["status"] == "HYPOTHESIS_SURVIVES_CURRENT_HELDOUT_EVIDENCE_NOT_LAW"
    assert result["best_hypothesis"]["holdout_nrmse"] < 1.0e-8
    assert result["sealed_holdout_evaluation"]["nrmse"] < 1.0e-8
    params = result["best_hypothesis"]["parameters"]
    assert any(math.isclose(float(v), -0.5, rel_tol=0.0, abs_tol=1.0e-8) for v in params)
