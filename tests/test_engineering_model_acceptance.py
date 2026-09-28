from source.lawspace.engineering_model_acceptance import EngineeringModelAcceptanceOwner


def test_engineering_acceptance_is_regime_scoped_and_not_law():
    out = EngineeringModelAcceptanceOwner().accept(
        {"candidate_id": "M1"},
        {"domain": "thermal", "regime_id": "R1", "validity_bounds": {"T": [250, 350]}},
        {"evidence_class": "MODEL_DERIVED", "fit_pass": True, "regime_ood_pass": True, "uncertainty_declared": True, "evidence_digest": "a" * 64},
    )
    assert out["accepted"] is True
    assert out["status"] == "ENGINEERING_MODEL_ACCEPTED_FOR_REGIME"
    assert out["claim_boundary"]["scientific_law_established"] is False
    assert out["claim_boundary"]["canonical_law_registry_mutated"] is False


def test_missing_bounds_blocks_engineering_acceptance():
    out = EngineeringModelAcceptanceOwner().accept(
        {"candidate_id": "M1"},
        {"domain": "thermal", "regime_id": "R1"},
        {"evidence_class": "MODEL_DERIVED", "fit_pass": True, "regime_ood_pass": True, "uncertainty_declared": True, "evidence_digest": "a" * 64},
    )
    assert out["accepted"] is False
