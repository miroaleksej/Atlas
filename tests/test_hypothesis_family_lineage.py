"""Generic hypothesis-family lineage regression for AdaptiveResearchKernelOwner."""
import pytest
from source.lawspace.research_cycle import AdaptiveResearchKernelOwner
from copy import deepcopy


def retired_parent():
    return AdaptiveResearchKernelOwner._hypothesis_family_lineage(
        family_request(), evidence_digest="E1", transition_status="REPRESENTATION_GAP",
        current_form_id="F1", current_form_digest="D1", current_form_structure_digest="S1",
    )


def family_request(domain_id="physics"):
    return {
        "domain_id": domain_id,
        "hypothesis_family": {
            "family_id": "HF-GENERIC-001",
            "statement": "A broader typed mechanism family may survive failure of one concrete representation.",
            "preserved_invariants": ["typed evidence", "fresh post-freeze validation"],
            "open_representation_questions": ["missing scale", "missing symmetry"],
        },
        "gap_evidence": {"failure_scope": "FORM_OR_REPRESENTATION"},
    }


def test_form_failure_retires_form_but_keeps_family_active():
    row = AdaptiveResearchKernelOwner._hypothesis_family_lineage(
        family_request(), evidence_digest="E1",
        transition_status="REPRESENTATION_GAP_OR_TRANSFER_FAILURE",
        current_form_id="F1", current_form_digest="D1", current_form_structure_digest="S1",
    )
    assert row["family_state"] == "ACTIVE_REPRESENTATION_EXPANSION"
    assert row["current_form_state"] == "RETIRED_FAILED_FORM"
    assert "D1" in row["retired_form_digests"]
    assert row["same_failed_form_resurrection_allowed"] is False
    assert row["automatic_law_promotion_allowed"] is False


def test_family_invariant_failure_closes_family():
    req = family_request()
    req["gap_evidence"] = {"failure_scope": "FAMILY_INVARIANT"}
    row = AdaptiveResearchKernelOwner._hypothesis_family_lineage(
        req, evidence_digest="E2", transition_status="FAMILY_INVARIANT_FALSIFIED",
        current_form_id="F1", current_form_digest="D1", current_form_structure_digest="S1",
    )
    assert row["family_state"] == "FALSIFIED_FAMILY"
    assert row["next_action"] == "ARCHIVE_FAMILY_AND_SEARCH_ALTERNATIVES"


def test_child_generation_is_digest_bound_to_parent_lineage():
    parent = AdaptiveResearchKernelOwner._hypothesis_family_lineage(
        family_request(), evidence_digest="E1",
        transition_status="REPRESENTATION_GAP_OR_TRANSFER_FAILURE",
        current_form_id="F1", current_form_digest="D1", current_form_structure_digest="S1",
    )
    req = family_request()
    req["hypothesis_family_lineage"] = parent
    child = AdaptiveResearchKernelOwner._hypothesis_family_lineage(
        req, evidence_digest="E3",
        transition_status="EXECUTABLE_REPRESENTATION_CANDIDATE_SYNTHESIZED_NOT_LAW",
        current_form_id="F2", current_form_digest="D2", current_form_structure_digest="S2",
    )
    assert child["generation"] == parent["generation"] + 1
    assert child["parent_lineage_digest"] == parent["digest"]
    assert child["family_state"] == "ACTIVE_TESTABLE_FAMILY"
    assert "D1" in child["retired_form_digests"]
    assert child["fresh_postfreeze_evidence_required"] is True


def test_tampered_parent_lineage_fails_closed():
    parent = AdaptiveResearchKernelOwner._hypothesis_family_lineage(
        family_request(), evidence_digest="E1",
        transition_status="REPRESENTATION_GAP_OR_TRANSFER_FAILURE",
        current_form_id="F1", current_form_digest="D1", current_form_structure_digest="S1",
    )
    tampered = dict(parent)
    tampered["family_state"] = "ACTIVE_TESTABLE_FAMILY"
    req = family_request()
    req["hypothesis_family_lineage"] = tampered
    with pytest.raises(ValueError, match="digest mismatch"):
        AdaptiveResearchKernelOwner._hypothesis_family_lineage(
            req, evidence_digest="E4", transition_status="REPRESENTATION_GAP",
        )


def test_domain_label_does_not_change_lineage_reasoning():
    rows = []
    for domain in ("astronomy", "nuclear", "chemistry", "biology", "fluid_dynamics", "mathematics"):
        rows.append(AdaptiveResearchKernelOwner._hypothesis_family_lineage(
            family_request(domain), evidence_digest="E5",
            transition_status="REPRESENTATION_GAP_OR_TRANSFER_FAILURE",
            current_form_id="F1", current_form_digest="D1", current_form_structure_digest="S1",
        ))
    assert len({row["digest"] for row in rows}) == 1
    assert len({row["family_state"] for row in rows}) == 1


def test_falsified_family_cannot_be_resurrected_by_child_form():
    req = family_request()
    req["gap_evidence"] = {"failure_scope": "FAMILY_INVARIANT"}
    closed = AdaptiveResearchKernelOwner._hypothesis_family_lineage(
        req, evidence_digest="E6", transition_status="FAMILY_INVARIANT_FALSIFIED",
        current_form_id="F1", current_form_digest="D1", current_form_structure_digest="S1",
    )
    next_req = family_request()
    next_req["hypothesis_family_lineage"] = closed
    child = AdaptiveResearchKernelOwner._hypothesis_family_lineage(
        next_req, evidence_digest="E7",
        transition_status="EXECUTABLE_REPRESENTATION_CANDIDATE_SYNTHESIZED_NOT_LAW",
        current_form_id="F9", current_form_digest="D9",
    )
    assert child["family_state"] == "FALSIFIED_FAMILY"
    assert child["current_form_state"] == "REJECTED_CHILD_OF_FALSIFIED_FAMILY"


@pytest.mark.parametrize('form,structure', [('D1', 'S2'), ('D2', 'S1')])
def test_retired_form_or_coefficient_refit_is_rejected(form, structure):
    req = family_request()
    req['hypothesis_family_lineage'] = retired_parent()
    with pytest.raises(ValueError, match='cannot be resurrected'):
        AdaptiveResearchKernelOwner._hypothesis_family_lineage(
            req, evidence_digest='NEW',
            transition_status='EXECUTABLE_REPRESENTATION_CANDIDATE_SYNTHESIZED_NOT_LAW',
            current_form_id='F2', current_form_digest=form, current_form_structure_digest=structure,
        )


def test_parent_digest_cannot_be_removed():
    req = family_request()
    req['hypothesis_family_lineage'] = retired_parent()
    del req['hypothesis_family_lineage']['digest']
    with pytest.raises(ValueError, match='digest mismatch'):
        AdaptiveResearchKernelOwner._hypothesis_family_lineage(req, evidence_digest='E', transition_status='REPRESENTATION_GAP')


@pytest.mark.parametrize('field,value', [('family_id', 'OTHER'), ('statement', 'Other claim'), ('preserved_invariants', ['weaker'])])
def test_family_identity_and_invariants_cannot_change(field, value):
    req = family_request()
    req['hypothesis_family_lineage'] = retired_parent()
    req['hypothesis_family'][field] = value
    with pytest.raises(ValueError, match='cannot change'):
        AdaptiveResearchKernelOwner._hypothesis_family_lineage(req, evidence_digest='E', transition_status='REPRESENTATION_GAP')


def test_family_failure_overrides_positive_status():
    req = family_request()
    req['gap_evidence']['failure_scope'] = 'FAMILY_INVARIANT'
    row = AdaptiveResearchKernelOwner._hypothesis_family_lineage(
        req, evidence_digest='E', transition_status='EXECUTABLE_REPRESENTATION_CANDIDATE_SYNTHESIZED_NOT_LAW',
        current_form_id='F2', current_form_digest='D2', current_form_structure_digest='S2',
    )
    assert row['family_state'] == 'FALSIFIED_FAMILY'


def test_unscoped_status_is_not_failure_adjudication():
    req = family_request()
    req['gap_evidence'] = {}
    row = AdaptiveResearchKernelOwner._hypothesis_family_lineage(req, evidence_digest='E', transition_status='NOT_SURVIVES_AXIS_RESIDUAL')
    assert row['family_state'] == 'CANDIDATE_PENDING_FAILURE_SCOPE_ADJUDICATION'
    assert row['retired_form_digests'] == []


def test_missing_evidence_digest_rejected():
    with pytest.raises(ValueError, match='requires evidence digest'):
        AdaptiveResearchKernelOwner._hypothesis_family_lineage(family_request(), evidence_digest='', transition_status='REPRESENTATION_GAP')


@pytest.mark.parametrize('missing', ['child_structure', 'parent_structure'])
def test_missing_structural_identity_blocks_continuation(missing):
    req = family_request()
    req['hypothesis_family_lineage'] = (
        retired_parent() if missing == 'child_structure' else
        AdaptiveResearchKernelOwner._hypothesis_family_lineage(
            family_request(), evidence_digest='E', transition_status='REPRESENTATION_GAP',
            current_form_id='F1', current_form_digest='D1',
        )
    )
    with pytest.raises(ValueError, match='structur'):
        AdaptiveResearchKernelOwner._hypothesis_family_lineage(
            req, evidence_digest='E2', transition_status='EXECUTABLE_REPRESENTATION_CANDIDATE_SYNTHESIZED_NOT_LAW',
            current_form_id='F2', current_form_digest='D2',
            current_form_structure_digest=None if missing == 'child_structure' else 'S2',
        )


def test_structural_identity_excludes_fitted_parameters_and_scores():
    candidate = {'expression': 'c0+c1*x', 'basis': [{'exponents': {'x': 1}}],
                 'coefficient_dimensions': {'c0': [0]*7, 'c1': [0]*7},
                 'parameters': [1, 2], 'holdout_nrmse': 0.1}
    refit = deepcopy(candidate)
    refit.update(parameters=[100, 200], holdout_nrmse=0.01)
    structure = AdaptiveResearchKernelOwner._hypothesis_form_structure_digest
    assert structure(candidate) == structure(refit)
    refit['basis'][0]['exponents']['x'] = 2
    assert structure(candidate) != structure(refit)


def test_gap_entry_binds_lineage_and_rejects_mismatched_evidence():
    from pathlib import Path
    from source.lawspace.api import LawSpaceAPI
    from source.lawspace.schema import digest_payload

    api = LawSpaceAPI(Path(__file__).resolve().parents[1])
    req = family_request('physics')
    req.update(entry_mode='ATTESTED_HYPOTHESIS_FORM_FAILURE', question='Which representation needs revision?',
               gap_kind='REPRESENTATION_CAPABILITY_GAP', blind_no_named_law_catalog=True)
    req['hypothesis_family'].update(current_form_id='F1', current_form_digest='D1', current_form_structure_digest='S1')
    report = api.advance_adaptive_research(req)
    lineage = report['hypothesis_family_lineage']
    assert lineage['family_state'] == 'ACTIVE_REPRESENTATION_EXPANSION'
    assert lineage['evidence_digest'] == digest_payload(req['gap_evidence'])
    assert report['result']['hypothesis_family_lineage'] == lineage
    req['gap_evidence_digest'] = 'wrong'
    with pytest.raises(ValueError, match='gap evidence digest mismatch'):
        api.advance_adaptive_research(req)
