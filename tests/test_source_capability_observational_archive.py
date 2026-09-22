"""Domain-neutral source-capability and observational-archive freeze regression."""
import pytest
from source.lawspace.research_cycle import AdaptiveResearchKernelOwner


def observational_request():
    return {
        "source_capability": {
            "class": "OBSERVATIONAL_ARCHIVE",
            "source_id": "ARCHIVE-X",
            "supports_arbitrary_state_intervention": False,
            "supports_natural_sample_retrieval": True,
        },
        "observational_archive_request": {
            "archive_id": "ARCHIVE-X",
            "source_manifest_digest": "MANIFEST-DIGEST",
            "measurement_adapter_owner": "DOMAIN-MEASUREMENT-ADAPTER/1.0.0",
            "selection_rule": "PRECOMMITTED",
            "selection_seed": "S1",
            "natural_samples_only": True,
            "outcomes_inspected_prefreeze": False,
            "sample_contracts": [
                {"sample_id": "A", "locator": {"index": 10}, "role": "FRESH"},
                {"sample_id": "B", "locator": {"index": 20}, "role": "FRESH"},
            ],
            "transforms": [{"kind": "SCALE", "value": 2}],
            "observable_contract": {"raw_fields": ["u", "v"]},
        },
    }


def test_legacy_source_capability_preserves_forward_oracle_behavior_but_marks_assumption():
    row = AdaptiveResearchKernelOwner._source_capability_contract({})
    assert row["class"] == "FORWARD_ORACLE"
    assert row["legacy_assumption_used"] is True
    assert row["arbitrary_state_probe_protocol_allowed"] is True


def test_explicit_observational_archive_forbids_arbitrary_intervention():
    row = AdaptiveResearchKernelOwner._source_capability_contract(observational_request())
    assert row["class"] == "OBSERVATIONAL_ARCHIVE"
    assert row["supports_arbitrary_state_intervention"] is False
    assert row["natural_sample_freeze_required"] is True
    assert row["arbitrary_state_probe_protocol_allowed"] is False


def test_observational_archive_cannot_claim_forward_intervention():
    req = observational_request()
    req["source_capability"]["supports_arbitrary_state_intervention"] = True
    with pytest.raises(ValueError, match="arbitrary-state intervention"):
        AdaptiveResearchKernelOwner._source_capability_contract(req)


def test_observational_protocol_freezes_natural_samples_before_outcomes():
    req = observational_request()
    source = AdaptiveResearchKernelOwner._source_capability_contract(req)
    row = AdaptiveResearchKernelOwner._freeze_observational_archive_protocol(
        req, source_capability=source, freeze_basis_digest="FAMILY-FREEZE",
    )
    assert row["status"] == "OBSERVATIONAL_ARCHIVE_PROTOCOL_FROZEN_AWAITING_FRESH_MEASUREMENTS"
    assert row["sample_ids"] == ["A", "B"]
    assert row["fresh_measurement_status"] == "NOT_ACQUIRED"
    assert row["outcomes_inspected_prefreeze"] is False
    assert row["claim_boundary"]["atlas_generated_arbitrary_world_states"] is False
    assert row["claim_boundary"]["scientific_law_established"] is False


def test_observational_protocol_rejects_prefreeze_outcome_inspection():
    req = observational_request()
    req["observational_archive_request"]["outcomes_inspected_prefreeze"] = True
    source = AdaptiveResearchKernelOwner._source_capability_contract(req)
    with pytest.raises(ValueError, match="must not be inspected"):
        AdaptiveResearchKernelOwner._freeze_observational_archive_protocol(
            req, source_capability=source, freeze_basis_digest="FAMILY-FREEZE",
        )


def test_observational_protocol_rejects_outcome_bearing_sample_contract():
    req = observational_request()
    req["observational_archive_request"]["sample_contracts"][0]["target_value"] = 1.23
    source = AdaptiveResearchKernelOwner._source_capability_contract(req)
    with pytest.raises(ValueError, match="outcome-bearing field"):
        AdaptiveResearchKernelOwner._freeze_observational_archive_protocol(
            req, source_capability=source, freeze_basis_digest="FAMILY-FREEZE",
        )


def test_observational_protocol_requires_unique_sample_ids():
    req = observational_request()
    req["observational_archive_request"]["sample_contracts"][1]["sample_id"] = "A"
    source = AdaptiveResearchKernelOwner._source_capability_contract(req)
    with pytest.raises(ValueError, match="must be unique"):
        AdaptiveResearchKernelOwner._freeze_observational_archive_protocol(
            req, source_capability=source, freeze_basis_digest="FAMILY-FREEZE",
        )


def test_protocol_digest_changes_when_prefrozen_sample_selection_changes():
    req1 = observational_request()
    req2 = observational_request()
    req2["observational_archive_request"]["sample_contracts"][1]["locator"]["index"] = 21
    source1 = AdaptiveResearchKernelOwner._source_capability_contract(req1)
    source2 = AdaptiveResearchKernelOwner._source_capability_contract(req2)
    a = AdaptiveResearchKernelOwner._freeze_observational_archive_protocol(req1, source_capability=source1, freeze_basis_digest="F")
    b = AdaptiveResearchKernelOwner._freeze_observational_archive_protocol(req2, source_capability=source2, freeze_basis_digest="F")
    assert a["digest"] != b["digest"]
