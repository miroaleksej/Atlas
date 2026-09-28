from source.lawspace.engineering_model_acceptance import EngineeringModelAcceptanceOwner, EngineeringModelLedgerOwner


def test_engineering_ledger_is_append_only_and_not_law(tmp_path, monkeypatch):
    monkeypatch.setenv("PHI_STATE_DIR", str(tmp_path / "state"))
    root = tmp_path / "atlas"
    acceptance = EngineeringModelAcceptanceOwner(root).accept(
        {"candidate_id": "M1", "digest": "c" * 64},
        {"domain": "thermal", "regime_id": "R1", "validity_bounds": {"T": [250, 350]}},
        {"evidence_class": "MODEL_DERIVED", "fit_pass": True, "regime_ood_pass": True,
         "uncertainty_declared": True, "evidence_digest": "e" * 64},
    )
    ledger = EngineeringModelLedgerOwner(root)
    recorded = ledger.record_acceptance(acceptance)
    assert recorded["recorded"] is True
    assert recorded["scientific_law_established"] is False
    assert ledger.state()["active_acceptance_count"] == 1
    revoked = ledger.revoke(acceptance_digest=acceptance["digest"], reason="regime drift", actor_id="HUMAN-1")
    assert revoked["revoked"] is True
    assert ledger.state()["active_acceptance_count"] == 0
    assert ledger.state()["event_count"] == 2
