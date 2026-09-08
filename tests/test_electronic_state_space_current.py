from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_electronic_state_space_contract_has_no_answer_order_or_fixed_shell_ceiling():
    from source.lawspace.atomic_frontier import ElectronicStateSpaceSearchOwner
    c = ElectronicStateSpaceSearchOwner(ROOT).contract()
    assert c["owner_id"] == "ELECTRONIC-STATE-SPACE-SEARCH/1.1.0"
    assert c["space_policy"]["fixed_upper_Z"] is None
    assert c["space_policy"]["fixed_upper_n"] is None
    assert c["space_policy"]["fixed_upper_l"] is None
    assert c["space_policy"]["fixed_candidate_count_as_truth_gate"] is False
    assert "MADELUNG_AUFBAU_ORDER_AS_ANSWER" in c["forbidden_answer_sources"]
    assert c["claim_policy"]["unstable_ordering_returns_unknown"] is True


def test_scf_evaluator_has_no_internal_configuration_generator_or_nuclear_radius_law():
    import inspect
    import source.lawspace.atomic_scf_evaluator as m
    text = inspect.getsource(m)
    assert "def aufbau_config" not in text
    assert "def madelung_order" not in text
    assert "0.0155 * Z" not in text
    assert "NuclearSphere" in text


def test_electronic_state_space_light_atom_executes_without_answer_table():
    from source.lawspace.api import LawSpaceAPI
    r = LawSpaceAPI(ROOT).search_atomic_electronic_state_space(
        2,
        proposal_grid_points=90,
        proposal_iterations=16,
        proposal_tolerance=3e-3,
        evaluator_grid_points=260,
        evaluator_iterations=25,
        evaluator_tolerance=5e-4,
    )
    assert r["proposal_representation"]["used_as_answer"] is False
    assert r["candidate_generation"]["aufbau_madelung_used"] is False
    assert r["candidate_generation"]["element_exception_vocabulary_used"] is False
    assert r["candidate_generation"]["published_configuration_order_used"] is False
    assert r["claim_boundary"]["known_ground_state_used_as_truth"] is False
    assert r["scientific_ground_state_established"] is False
    assert r["status"] in {
        "PROVISIONAL_GROUND_STATE_WITHIN_EXECUTED_REPRESENTATIONS",
        "REPRESENTATION_GAP_STRONGER_ELECTRONIC_REPRESENTATION_REQUIRED",
    }


def test_public_api_exposes_new_authoritative_owner_not_as_regression():
    from source.lawspace.api import LawSpaceAPI
    assert "search_atomic_electronic_state_space" in LawSpaceAPI.READ_TOOLS
    assert "get_electronic_state_space_search_contract" in LawSpaceAPI.READ_TOOLS
    assert "search_atomic_electronic_state_space" not in LawSpaceAPI.REGRESSION_TOOLS
    assert "run_autonomous_atomic_frontier" in LawSpaceAPI.REGRESSION_TOOLS


def test_theory_compiler_many_body_coordinate_discovery_is_rank_adaptive_and_named_method_free():
    from source.lawspace.theory_compiler import TheoryCompilerKernel
    c = TheoryCompilerKernel(ROOT).contract()
    mb = c["many_body_coordinate_synthesis_owner"]
    assert mb["search_starts_at_rank"] == 1
    assert mb["fixed_global_interaction_rank_ceiling"] is None
    assert mb["known_many_body_method_required"] is False
    assert mb["named_solver_selection"] is False
    assert c["representation_policy"]["fermionic_many_body_operator_coordinate_discovery_supported"] is True


def test_evidence_born_many_body_coordinate_survives_precommitted_blind_atoms():
    from source.lawspace.api import LawSpaceAPI
    r = LawSpaceAPI(ROOT).run_electronic_many_body_coordinate_blind_experiment(
        radial_points=400, fit_tolerance_nrmse=1e-8,
    )
    assert r["status"] == "PASS_EVIDENCE_BORN_MANY_BODY_OPERATOR_COORDINATE_BLIND_TEST"
    assert r["negative_control"]["rank_one_pass"] is True
    assert r["discovery_rank_one_screen"]["rank_one_pass"] is False
    assert r["discovered_interaction_rank"] == 2
    assert len(r["blind_receipts"]) == 2
    assert all(
        x["many_body_operator_coordinate_synthesis"]["validated_precommitted_interaction_rank"] == 2
        for x in r["blind_receipts"]
    )
    assert all(len(x["many_body_probe_design_history"]) == 1 for x in r["blind_receipts"])
    assert r["claim_boundary"]["named_ci_or_mcdhf_selected"] is False
    assert r["claim_boundary"]["blind_atom_identity_used_during_rank_discovery"] is False
