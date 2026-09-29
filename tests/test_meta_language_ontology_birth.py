from evaluation.meta_language_ontology_birth_qualification import run_release_qualification


def test_meta_language_ontology_birth_qualification():
    result = run_release_qualification()
    assert result["status"] == "PASS_AUTONOMOUS_META_LANGUAGE_ONTOLOGY_BIRTH"
    assert result["passed"] == result["total"] == 13


def test_meta_language_ontology_birth_does_not_claim_agi_or_free_ontology():
    result = run_release_qualification()
    assert result["claim_boundary"]["qualification_proves_unrestricted_free_ontology_birth"] is False
    assert result["claim_boundary"]["qualification_proves_agi"] is False


def test_meta_language_ontology_birth_selects_unseen_four_field_arity():
    result = run_release_qualification()
    selected = result["four_field"]["validation"]["selected_constructor_program"]
    assert result["four_field"]["validation"]["accepted"] is True
    assert selected["constructor_arity"] == 4
