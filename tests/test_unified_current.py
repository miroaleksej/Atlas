from pathlib import Path
from functools import lru_cache
import hashlib
import json

from source.lawspace.api import LawSpaceAPI
from source.lawspace.runtime import LawSpaceRuntime
from source.lawspace.domains import DOMAIN_REGISTRIES, canonical_axis_count
from source.lawspace.black_hole import BlackHoleLabOwner
from source.lawspace.einstein_dynamics import EinsteinDynamicsOwner
from source.lawspace.neutrino import NeutrinoPhenomenologyOwner
from source.lawspace.particle_space import ParticleSpaceOwner
from source.lawspace.pharmaceutical import PharmaceuticalDomainOwner
from source.lawspace.aeronautics import AeronauticsLawIntersectionClosureOwner
from source.lawspace.quantum_vacuum import QuantumVacuumGravityIntersectionOwner
from source.lawspace.mathematical_invention import MathematicalInventionKernel
from source.lawspace.theory_compiler import TheoryCompilerKernel
from source.lawspace.knowledge_evolution import CrossDomainBridgeOwner
from source.lawspace.schema import digest_payload

ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def _frontier_replay_readonly():
    from evaluation.lawspace_qualification import run_frontier_scan_current
    ledger = ROOT / "data/frontiers/ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl"
    before = hashlib.sha256(ledger.read_bytes()).hexdigest()
    result = run_frontier_scan_current(ROOT, pair_frontier_limit=256, persist_ledger=False)
    after = hashlib.sha256(ledger.read_bytes()).hexdigest()
    return result, before, after


def test_current_runtime_registry_is_snapshot_not_ceiling():
    runtime = LawSpaceRuntime(ROOT)
    count = canonical_axis_count()
    assert count == sum(len(reg.axes) for reg in DOMAIN_REGISTRIES.values())
    assert count > 0
    assert len(DOMAIN_REGISTRIES) == 13
    assert len(runtime.catalog.passports) == 445
    assert len(runtime.candidates) == 0
    assert len(runtime.evidence) == 0
    assert len(runtime.quantum_method_routes) == 0
    assert len(runtime.constants) == 26
    assert len(runtime.computational_methods) >= 22


def test_preexisting_domain_owners_remain_live():
    contracts = [
        BlackHoleLabOwner().contract(),
        EinsteinDynamicsOwner().contract(),
        NeutrinoPhenomenologyOwner().contract(),
        ParticleSpaceOwner().contract(),
        PharmaceuticalDomainOwner().contract(),
        AeronauticsLawIntersectionClosureOwner(ROOT).contract(),
        QuantumVacuumGravityIntersectionOwner(ROOT).contract(),
        MathematicalInventionKernel(ROOT).contract(),
        TheoryCompilerKernel(ROOT).contract(),
    ]
    assert all(c.get('owner_id') for c in contracts)
    assert len({c['owner_id'] for c in contracts}) == len(contracts)


def test_typed_bridge_can_transfer_or_refuse_without_merging_axes():
    owner = CrossDomainBridgeOwner()
    positive = owner.certify_typed_law_bridge(
        source={'dimension_signature':'FIELD_PER_SOURCE','validity_tags':['inverse_square'],'operator_family':'DIVIDE_BY_TEST_SOURCE'},
        target={'dimension_signature':'FIELD_PER_SOURCE','validity_tags':['inverse_square'],'operator_family':'DIVIDE_BY_TEST_SOURCE'},
        mapping={'SOURCE':'SOURCE','TEST_SOURCE':'TEST_SOURCE'}, consequence_transfer=True,
    )
    assert positive['status'] == 'TYPED_BRIDGE_CONSEQUENCE_TRANSFER'
    negative = owner.certify_typed_law_bridge(
        source={'dimension_signature':'DIMENSIONLESS','validity_tags':['chemical_activity'],'operator_family':'NEG_LOG'},
        target={'dimension_signature':'DIMENSIONLESS','validity_tags':['independent_probability'],'operator_family':'NEG_LOG'},
        mapping={'ARG':'ARG'}, consequence_transfer=False,
    )
    assert negative['status'] == 'MATHEMATICAL_ANALOGY_ONLY'
    assert negative['canonical_axes_merged'] is False


def test_current_api_exposes_adaptive_kernel_and_preserves_domain_surfaces():
    api = LawSpaceAPI(ROOT)
    adaptive = {
        'get_adaptive_research_kernel_contract', 'advance_adaptive_research',
        'search_observations_for_function_forms',
        'get_claim_provenance_firewall_contract', 'run_energy_space_temperature_axis_control',
        'run_temperature_energy_adaptive_control',
        'run_adaptive_research_kernel_qualification', 'synthesize_phi_executable_representation',
    }
    preserved = {
        'get_black_hole_lab_contract','get_einstein_dynamics_contract','get_neutrino_owner_contract',
        'get_particle_space_contract','get_pharmaceutical_domain_contract','get_quantum_vacuum_gravity_contract',
        'get_science_atlas_core_qualification','get_tensor_geometry_contract',
    }
    assert adaptive | preserved <= set(api.READ_TOOLS)


def test_current_release_tree_and_book_are_single_authority():
    assert not (ROOT/'docs/history').exists()
    hist = ROOT/'reports/history'
    if hist.exists():
        assert [p.name for p in hist.iterdir()] == ['version-control']
        assert all(p.is_file() for p in (hist/'version-control').iterdir())
    books = list(ROOT.glob('MATHEMATICAL_BOOK*.md'))
    assert books == [ROOT/'MATHEMATICAL_BOOK.md']
    text = books[0].read_text(encoding='utf-8')
    assert 'CURRENT 0.15.28.0' in text
    assert 'Adaptive Research Kernel' in text


def test_global_axis_space_is_open_ended_not_619_fundamental():
    from source.lawspace.candidates import global_axis_combination_contract
    contract = global_axis_combination_contract()
    current = contract['current_registered_axis_count']
    assert current == canonical_axis_count()
    assert int(contract['total_nonempty_registered_axis_subsets']) == (1 << current) - 1
    assert contract['fixed_axis_combination_order_ceiling'] is None
    assert contract['claim_boundary']['all_possible_scientific_axes_known'] is False


def test_owner_connected_search_reuses_existing_strong_gravity_owners():
    from source.lawspace.candidates import DirectedResearchQuery, directed_owner_hypergraph_research
    from source.lawspace.research_cycle import ScientificResearchCycleOwner
    runtime = LawSpaceRuntime(ROOT)
    surfaces = ScientificResearchCycleOwner(runtime)._runtime_owner_search_surfaces()
    query = DirectedResearchQuery(
        question='stationary axisymmetric black hole horizon gauge tensor geometry',
        required_domains=('physics',),
        target_axis_ids=('coordinate_frame','curvature_regime','gauge_group','perturbation_order'),
        seed_owner_ids=('TENSOR-GEOMETRY-OWNER/12.6.0','EINSTEIN-DYNAMICS-OWNER/12.6.0'),
    )
    result = directed_owner_hypergraph_research(runtime.catalog, runtime.bridges, query, owner_surfaces=surfaces)
    selected = set(result.get('selected_runtime_owner_ids', []))
    assert {'TENSOR-GEOMETRY-OWNER/12.6.0','EINSTEIN-DYNAMICS-OWNER/12.6.0'} <= selected


def test_atomic_frontier_is_regression_owner_not_persisted_seed():
    path = ROOT/'reports/SEQUENTIAL_PHI_ATOMIC_FRONTIER_CURRENT.json'
    assert not path.exists()
    assert (ROOT/'source/lawspace/atomic_frontier.py').exists()


def test_adaptive_research_kernel_is_current_authority_without_fixed_ceiling():
    from source.lawspace.research_cycle import AdaptiveResearchKernelOwner, ProvenanceClaimFirewallOwner
    kernel = AdaptiveResearchKernelOwner(LawSpaceRuntime(ROOT)).contract()
    assert kernel['authoritative_research_orchestration'] is True
    assert kernel['space_policy']['canonical_axis_count_is_ceiling'] is False
    assert kernel['space_policy']['fixed_hypothesis_complexity_ceiling'] is None
    assert kernel['space_policy']['fixed_competitor_count_as_truth_gate'] is False
    firewall = ProvenanceClaimFirewallOwner().contract()
    assert firewall['rules']['assistant_can_stamp_atlas_native'] is False


def test_temperature_axis_is_added_to_space_before_any_formula_coupling():
    result = LawSpaceAPI(ROOT).run_energy_space_temperature_axis_control()
    assert result['status'] == 'PASS_ENERGY_SPACE_TEMPERATURE_AXIS_AUGMENTATION_CONTROL'
    checks = result['checks']
    assert checks['temperature_not_in_initial_formula_space'] is True
    assert checks['temperature_present_as_dormant_axis'] is True
    assert checks['coupled_residual_selects_temperature'] is True
    assert checks['coupled_control_activates_temperature'] is True
    assert checks['coupled_control_improves_after_activation'] is True
    assert checks['coupled_control_born_relation_uses_temperature_only_post_activation'] is True
    assert checks['coupled_sealed_holdout_passes_after_freeze'] is True
    assert checks['null_control_does_not_activate_temperature'] is True
    assert checks['null_control_keeps_temperature_out_of_effective_formula_space'] is True
    assert checks['both_controls_not_claimed_as_physical_law'] is True


def test_assistant_cannot_assign_atlas_native_claim_origin():
    api = LawSpaceAPI(ROOT)
    try:
        api.propose_candidate({'epistemic_state':'PENDING_PROPOSAL','claim_origin':'ATLAS_NATIVE','statement':'fabricated'})
    except PermissionError:
        pass
    else:
        raise AssertionError('proposal API assigned ATLAS_NATIVE')
    row = api.propose_candidate({'epistemic_state':'PENDING_PROPOSAL','statement':'temperature may matter'})
    assert row['claim_origin'] == 'ASSISTANT_HYPOTHESIS'
    assert row['atlas_native'] is False


def test_representation_gap_can_synthesize_executable_operator_without_named_law():
    qualification = LawSpaceAPI(ROOT).run_phi_theory_compiler_qualification()
    assert qualification['status'] == 'PASS_PHI_THEORY_COMPILER_QUALIFICATION'
    checks = {row['check']: row['status'] for row in qualification['checks']}
    assert checks['operator_candidate_synthesized'] == 'PASS'
    assert checks['operator_holdout_never_used_for_term_selection'] == 'PASS'
    assert checks['operator_backward_pruning_never_reads_holdout'] == 'PASS'
    assert checks['direct_gap_rejects_unattested_operator_rows'] == 'PASS'
    assert checks['direct_gap_accepts_digest_bound_operator_provenance'] == 'PASS'
    assert checks['operator_compiles'] == 'PASS'
    assert checks['operator_executes'] == 'PASS'
    assert checks['generalized_eigenproblem_executes'] == 'PASS'
    assert checks['self_consistent_fixed_point_executes'] == 'PASS'
    assert checks['insufficient_operator_evidence_fails_closed'] == 'PASS'
    assert checks['no_named_law_required'] == 'PASS'
    assert checks['atomic_world_owner_contract'] == 'PASS'
    assert checks['atomic_world_cycle_atlas_redesigns_carrier_after_typed_feedback'] == 'PASS'
    assert checks['atomic_world_cycle_responses_from_independent_owner'] == 'PASS'
    assert checks['atomic_world_cycle_probe_attestation_is_digest_bound'] == 'PASS'
    assert checks['atomic_world_cycle_synthesizes_executable_representation'] == 'PASS'
    assert checks['atomic_world_cycle_sealed_holdout_passes'] == 'PASS'
    assert checks['atomic_world_cycle_execution_residual_small'] == 'PASS'
    assert checks['atomic_world_cycle_does_not_establish_table_upper_index_or_law'] == 'PASS'


def test_representation_gap_entry_is_executable_without_fabricated_observations():
    api = LawSpaceAPI(ROOT)
    receipt = api.advance_adaptive_research({
        "problem_id":"TEST-GAP-ENTRY",
        "domain_id":"physics",
        "question":"Continue from an attested representation gap without a named law or fabricated observations.",
        "representation_gap":True,
        "gap_kind":"REPRESENTATION_CAPABILITY_GAP",
        "gap_evidence":{
            "source":"CURRENT_TEST_CAPABILITY_ATTESTATION",
            "status":"REPRESENTATION_INSUFFICIENT_FOR_CONTROL",
            "world_measurement":False,
        },
        "blind_no_named_law_catalog":True,
        "operator_probe_rows":(),
    })
    assert receipt['entry_mode'] == 'ATTESTED_REPRESENTATION_GAP'
    assert receipt['observations_origin'] == 'NONE_REQUIRED_FOR_GAP_ENTRY'
    assert receipt['phi_space']['named_law_catalog_read'] is False
    assert receipt['result']['status'] == 'REPRESENTATION_GAP_OPERATOR_PROBE_PROTOCOL_FROZEN_AWAITING_ATTESTED_RESPONSES'
    assert receipt['executable_representation_synthesis']['reason'] == 'NO_ATTESTED_OPERATOR_RESPONSE_VALUES_AVAILABLE'
    assert receipt['operator_probe_design']['design_certificate']['full_rank_for_current_grammar'] is True
    assert receipt['operator_probe_design']['claim_boundary']['atlas_generated_probe_inputs'] is True
    assert receipt['operator_probe_design']['claim_boundary']['atlas_generated_operator_responses'] is False
    assert receipt['claim_boundary']['missing_operator_probe_values_filled_by_assistant'] is False
    assert receipt['claim_boundary']['fixed_upper_index_used'] is False
    assert receipt['atlas_claim']['atlas_native'] is True
    assert receipt['result']['scientific_law_established'] is False


def test_public_api_surface_is_complete_and_regressions_are_quarantined():
    api = LawSpaceAPI(ROOT)
    public = {
        name for name, value in LawSpaceAPI.__dict__.items()
        if callable(value) and not name.startswith("_")
    }
    read = set(api.READ_TOOLS)
    mutation = set(api.MUTATION_TOOLS)
    regression = set(api.REGRESSION_TOOLS)
    assert public == read | mutation | regression
    assert not (read & mutation)
    assert not (read & regression)
    assert not (mutation & regression)
    assert {"get_quantity", "compile_neutrino_multidomain_candidate"} <= read
    answer_bearing_atomic = {
        "run_element_compactness_frontier_probe", "run_blind_per_element_reconstruction",
        "run_phi_space_atomic_interior_hole_qualification", "run_autonomous_atomic_frontier",
        "get_frontier_world_attestation", "get_frontier_higher_order_expansion",
    }
    assert answer_bearing_atomic == regression
    for name in sorted(regression):
        try:
            getattr(api, name)()
        except PermissionError as exc:
            assert "regression_mode=True" in str(exc)
        else:
            raise AssertionError(f"regression surface {name} did not fail closed")
    from source.lawspace.candidates import CandidateGenerationPipeline
    pipeline = CandidateGenerationPipeline(api.runtime.catalog, api.runtime.bridges)
    for name in (
        "run_element_compactness_frontier_probe",
        "run_blind_per_element_reconstruction",
        "run_phi_space_atomic_interior_hole_qualification",
    ):
        try:
            getattr(pipeline, name)(ROOT)
        except PermissionError as exc:
            assert "regression_mode=True" in str(exc)
        else:
            raise AssertionError(f"candidate owner regression surface {name} did not fail closed")




def test_open_ended_periodic_frontier_has_no_numeric_z_ceiling_and_fails_closed_without_prefix():
    api = LawSpaceAPI(ROOT)
    physical = api.run_open_ended_periodic_frontier()
    assert physical["status"] == "BLOCKED_CLEAN_BASELINE_REQUIRES_ATTESTED_CLOSED_PREFIX"
    assert physical["fixed_Zmax_used"] is False
    assert physical["historical_172_boundary_used"] is False
    assert physical["scan"]["fixed_upper_Z"] is None
    assert physical["scan"]["numeric_iteration_or_visit_ceiling"] is None
    assert physical["scan"]["physical_frontier_advanced"] is False
    # Arbitrary requested views are symbolic, not a claim that those elements exist.
    exploratory = api.run_open_ended_periodic_frontier(z_values=(119, 124, 169, 200, 1000, 10000))
    assert exploratory["status"] == "PASS_OPEN_ENDED_SYMBOLIC_FRONTIER_VIEW"
    assert exploratory["scan"]["fixed_upper_Z"] is None
    rows = {int(row["Z"]): row for row in exploratory["results"]}
    assert set(rows) == {119, 124, 169, 200, 1000, 10000}
    assert rows[169]["dynamically_born_channel_count"] > 0
    assert rows[1000]["status"] == "IDENTIFIABILITY_GAP"
    assert rows[10000]["symbolic_candidate_count"] > 1
    assert all(row["physical_object_existence"] == "UNATTESTED" for row in rows.values())


def test_every_current_source_module_imports_cleanly():
    import importlib
    modules = []
    for path in (ROOT / "source").rglob("*.py"):
        rel = path.relative_to(ROOT).with_suffix("")
        module = ".".join(rel.parts)
        if module.endswith(".__init__"):
            module = module[:-9]
        modules.append(module)
    failures = {}
    for module in sorted(set(modules)):
        try:
            importlib.import_module(module)
        except Exception as exc:  # pragma: no cover - failure receipt only
            failures[module] = f"{type(exc).__name__}: {exc}"
    assert set(modules)
    assert len(set(modules)) == len(modules)
    assert failures == {}

    # Exercise the integration path used by the all-offline benchmark. NumPy
    # 2.4 no longer exposes the legacy np.trapz alias.
    from source.phi_compiler_owner import candidate_experiment_specs
    specs = candidate_experiment_specs()
    assert specs and all(spec.safe() for spec in specs)

    from evaluation.phi_bench import _handler_connectivity
    connectivity = _handler_connectivity()
    assert connectivity["registry_size"] == connectivity["expected_registry_size"] == 8
    assert connectivity["all_handlers_registered"] is True
    assert connectivity["within_family_all_pass"] is True


def test_post118_identifiability_is_set_valued_and_relativistic_axis_active():
    result = LawSpaceAPI(ROOT).run_post118_configuration_identifiability_experiment_design()
    assert result["status"] == "PASS_OPEN_ENDED_SYMBOLIC_FRONTIER_VIEW"
    assert result["post118_reference_configurations_used"] is False
    assert result["seen_correction_label_vocabulary_used"] is False
    rows = {int(r["Z"]): r for r in result["results"]}
    assert set(rows) == set(range(119, 125))
    for z, row in rows.items():
        assert row["status"] == "IDENTIFIABILITY_GAP"
        assert row["relativistic_axis_active"] is True
        assert row["configuration_mixture_allowed"] is True
        assert row["single_answer_promoted"] is False
        assert row["candidate_count"] > 1
        assert row["discriminating_experiments"][0]["observable"] == "FIRST_IONIZATION_POTENTIAL"
    z121 = rows[121]
    supports = {tuple(c["frontier_support"]) for c in z121["candidate_set"]}
    assert ("8p",) in supports
    assert ("7d",) in supports
    assert ("6f",) in supports
    assert ("5g",) in supports


def test_open_ended_nuclear_world_is_evidence_first_and_has_no_numeric_ceiling():
    api = LawSpaceAPI(ROOT)
    result = api.run_open_ended_nuclear_binding_decay_world()
    assert result["status"] == "STOPPED_AT_FIRST_UNRESOLVED_NUCLEAR_EXISTENCE_GATE"
    assert result["scan"]["fixed_upper_Z"] is None
    assert result["scan"]["fixed_upper_N"] is None
    assert result["scan"]["numeric_iteration_or_visit_ceiling"] is None
    assert result["scan"]["first_unresolved_Z"] == 119
    assert result["scan"]["Zmax_identified"] is False
    row = result["results"][0]
    assert row["attestation"]["physical_object_existence"] == "UNATTESTED"
    ref = row["reference_world"]
    assert ref["reference_simulation_is_empirical_world"] is False
    assert ref["total_half_life_identified"] is False
    candidate = ref["reference_candidate"]
    assert candidate["fixed_N_ceiling"] is None
    assert 130 <= candidate["N_model"] <= 230
    assert candidate["Q_alpha_model_MeV"] > 0.0
    assert candidate["spontaneous_fission_half_life_s"] is None
    assert result["claim_boundary"]["physical_Zmax_identified"] is False


def test_nuclear_world_advances_only_with_attested_lifetime_and_never_treats_absence_as_nonexistence():
    api = LawSpaceAPI(ROOT)
    synthetic_attestation = [{
        "Z": 119, "N": 180, "A": 299,
        "source_kind": "WORLD_ATTESTED",
        "estimated_or_systematics": False,
        "z_identity_attested": True,
        "half_life_s": 1.0e-9,
        "qualification_fixture": True,
    }]
    result = api.run_open_ended_nuclear_binding_decay_world(attested_nuclides=synthetic_attestation)
    assert [r["Z"] for r in result["results"]] == [119, 120]
    assert result["results"][0]["attestation"]["physical_object_existence"] == "ATTESTED"
    assert result["results"][1]["attestation"]["physical_object_existence"] == "UNATTESTED"
    assert result["scan"]["first_unresolved_Z"] == 120
    assert result["scan"]["Zmax_identified"] is False

    too_short = [{
        "Z": 119, "N": 180, "A": 299,
        "source_kind": "WORLD_ATTESTED",
        "estimated_or_systematics": False,
        "z_identity_attested": True,
        "half_life_s": 1.0e-16,
        "qualification_fixture": True,
    }]
    short = api.run_open_ended_nuclear_binding_decay_world(attested_nuclides=too_short)
    assert short["results"][0]["attestation"]["physical_object_existence"] == "UNATTESTED"
    assert short["results"][0]["attestation"]["absence_is_nonexistence_proof"] is False
    assert short["claim_boundary"]["absence_of_attestation_establishes_nonexistence"] is False


def test_first_post_clean_atlas_native_experiment_replays_and_stays_not_law():
    from evaluation.first_atlas_native_experiment import run
    result = run(ROOT)
    assert result['status'] == 'PASS_FIRST_POST_CLEAN_ATLAS_EXPERIMENT'
    assert result['passed'] == result['total'] == 15
    summary = result['result_summary']
    assert summary['activated_axes'] == ['medium_state']
    assert summary['born_expression'] == 'c0 + c1*drive + c2*drive*medium_state'
    assert float(summary['sealed_holdout_nrmse']) < 1e-12
    assert result['execution_receipt']['atlas_claim']['atlas_native'] is True
    assert result['execution_receipt']['atlas_claim']['scientific_truth_established'] is False



def test_low_frequency_gust_anomaly_is_quantified_without_false_mechanism_promotion():
    from source.lawspace.constraint_atlas import ConstraintAtlasOwner
    result = ConstraintAtlasOwner(ROOT).analyze_low_frequency_gust_anomaly_public_evidence()
    assert result['status'] == 'PASS_LOW_FREQUENCY_GUST_ANOMALY_PUBLIC_EVIDENCE_ANALYSIS'
    low = result['bands']['low_4_8_hz']
    assert 1.7 < float(low['mean_residual_db']) < 1.8
    assert 0.80 < float(low['mean_conditional_effective_input_magnitude_ratio']) < 0.84
    assert abs(float(result['bands']['resonance_9_hz']['mean_residual_db'])) < 0.2
    pairs = result['multispeed_scalar_gain_shape_test']['pair_metrics']
    p3050 = next(row for row in pairs if row['speed_pair_m_s'] == [30.0, 50.0])
    assert float(p3050['normalized_shape_max_abs_difference_db']) > 5.0
    assert result['multispeed_scalar_gain_shape_test']['formal_falsification_claimed'] is False
    assert 'TENSIONED_AS_COMPLETE_EXPLANATION' in result['candidate_consequences']['H-AERO-REAL-001']
    assert result['flap_to_wrbm_negative_control']['structural_mechanism_falsified'] is False
    experiment = result['discriminating_experiment']
    assert [row['state'] for row in experiment['states']] == ['NO_WING', 'RIGID_WING', 'FLEXIBLE_WING']
    assert experiment['status'] == 'EXPERIMENT_DESIGNED_REAL_SYNCHRONIZED_DATA_PENDING'
    assert result['claim_boundary']['new_physical_mechanism_established'] is False


def test_frontier_scan_preserves_every_materialized_candidate_without_promotion():
    result, persisted_before, _ = _frontier_replay_readonly()
    assert result['status'] == 'PASS_ATLAS_FRONTIER_CANDIDATE_SCAN', {
        'failed_checks': sorted(name for name, passed in result.get('checks', {}).items() if not passed),
        'generated_ledger_sha256': result.get('active_candidate_ledger', {}).get('sha256'),
        'persisted_ledger_sha256': persisted_before,
    }
    assert result['scan_summary']['cross_domain_pair_regions_scanned'] == 183996
    assert result['scan_summary']['materialized_pair_frontier_candidates'] == 256
    assert result['scan_summary']['algebraic_generated_candidates'] == 116
    assert result['scan_summary']['adaptive_multidimensional_subspace_candidates'] >= 900
    assert result['scan_summary']['adaptive_subspace_minimum_axis_order'] >= 2
    assert result['scan_summary']['adaptive_subspace_maximum_axis_order'] > 15
    hist = result['scan_summary']['adaptive_subspace_axis_order_histogram']
    assert all(str(k) in hist for k in (3,4,5,6,7))
    assert result['scan_summary']['operator_generated_candidates'] == 11
    assert result['scan_summary']['real_data_mechanism_candidates'] == 5
    assert result['scan_summary']['provisional_axis_candidates'] == 1
    assert result['scan_summary']['probe_to_wing_full_real_execution'] is False
    assert result['scan_summary']['probe_to_wing_public_data_status'] == 'PARTIAL_REAL_EVIDENCE_FULL_COMPLEX_DISCRIMINATOR_BLOCKED'
    assert result['incomplete_frontiers']['probe_to_wing_physical_measurement']['posterior_update_allowed'] is False
    assert result['checks']['probe_to_wing_discriminator_method_qualified'] is True
    assert result['checks']['probe_to_wing_real_data_fail_closed'] is True
    assert result['checks']['low_frequency_anomaly_quantified'] is True
    assert result['checks']['tri_state_complex_transfer_experiment_designed'] is True
    assert 1.7 < float(result['scan_summary']['low_frequency_mean_residual_db']) < 1.8
    active_count = result['active_candidate_ledger']['record_count']
    assert active_count == sum(result['candidate_class_counts'].values())
    assert result['candidate_status_counts']['CANDIDATE_ACTIVE'] == active_count
    assert result['policy']['ranking_is_deletion_policy'] is False
    assert result['policy']['unknown_candidate_is_false'] is False
    assert result['claim_boundary']['new_scientific_law_established_by_scan'] is False
    assert result['incomplete_frontiers']['algebraic_search']['status'] == 'CURRENT_POLYNOMIAL_IDEAL_BASIS_SATURATED'
    assert result['incomplete_frontiers']['algebraic_search']['fixed_execution_visit_ceiling'] is None
    assert result['incomplete_frontiers']['adaptive_multidimensional_subspace_search']['fixed_axis_order_ceiling'] is None
    assert result['checks']['adaptive_subspaces_include_pure_higher_order_nominations'] is True
    assert result['checks']['adaptive_subspaces_can_cross_order_15_without_ceiling'] is True
    assert result['checks']['postfreeze_prior_art_receipt_present_and_digest_valid'] is True
    assert result['checks']['postfreeze_prior_art_bound_to_frozen_current_ledger'] is True
    assert result['checks']['postfreeze_prior_art_absence_never_means_false'] is True
    assert result['postfreeze_prior_art_review']['review_count'] >= 6
    assert result['checks']['adaptive_candidates_have_problem_applicability_and_experiment_contracts'] is True



def test_algebraic_frontier_polynomial_identity_is_global_sign_canonical():
    import sympy as sp
    from source.lawspace.constraint_atlas import _normalize_polynomial

    R_s, T, T0, V, gamma = sp.symbols('R_s T T0 V gamma')
    a = T * (2*R_s*T*gamma - 2*R_s*T0*gamma + V**2*gamma - V**2)
    b = -T * (-2*R_s*T*gamma + 2*R_s*T0*gamma - V**2*gamma + V**2)
    na = _normalize_polynomial(a)
    nb = _normalize_polynomial(b)
    assert sp.srepr(na) == sp.srepr(nb)
    assert str(na) == str(nb)


def test_frontier_replay_is_read_only_for_persisted_candidate_ledger():
    ledger = ROOT / "data/frontiers/ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl"
    replay, before, after = _frontier_replay_readonly()
    assert replay["status"] == "PASS_ATLAS_FRONTIER_CANDIDATE_SCAN", {
        "failed_checks": sorted(name for name, passed in replay.get("checks", {}).items() if not passed),
        "generated_ledger_sha256": replay.get("active_candidate_ledger", {}).get("sha256"),
        "persisted_ledger_sha256": before,
    }
    assert before == after
    assert replay["active_candidate_ledger"]["record_count"] == len([line for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()])


def test_frontier_candidate_ledger_is_current_research_state_not_baseline_registry():
    runtime = LawSpaceRuntime(ROOT)
    assert len(runtime.candidates) == 0
    ledger = ROOT/'data/frontiers/ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl'
    assert ledger.exists()
    rows = [json.loads(line) for line in ledger.read_text(encoding='utf-8').splitlines() if line.strip()]
    assert len(rows) > 0
    assert len({row['candidate_id'] for row in rows}) == len(rows)
    assert all('CANDIDATE_ACTIVE' in row['epistemic_statuses'] for row in rows)
    classes = {row['candidate_class'] for row in rows}
    assert classes == {'CROSS_DOMAIN_AXIS_FRONTIER','ADAPTIVE_MULTIDIMENSIONAL_SUBSPACE_FRONTIER','ALGEBRAIC_SOURCE_DERIVED_FRONTIER','OPERATOR_COMPOSITION_FRONTIER','REAL_DATA_MECHANISM_COMPETITION','PROVISIONAL_RESEARCH_AXIS','RESEARCH_AXIS_PROPOSAL'}


def test_every_current_frontier_candidate_has_one_valid_fail_closed_promotion_path():
    from source.lawspace.scientific_promotion import ScientificPromotionCore, FRONTIER_GATE_SEQUENCE
    ledger = ROOT / 'data/frontiers/ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl'
    rows = [json.loads(line) for line in ledger.read_text(encoding='utf-8').splitlines() if line.strip()]
    assert len(rows) > 0
    for row in rows:
        path = row.get('promotion_path')
        status = ScientificPromotionCore.frontier_path_status(path)
        assert status['valid'] is True
        assert tuple(path['gate_sequence']) == tuple(FRONTIER_GATE_SEQUENCE)
        assert path['promotion_allowed'] is False
        assert path['candidate_is_false'] is False
        assert 'U8_WHOLE_PIPELINE_PERMUTATION_NULL' in path['gates']
    source_derived = [r for r in rows if r['candidate_class'] in {'ALGEBRAIC_SOURCE_DERIVED_FRONTIER','OPERATOR_COMPOSITION_FRONTIER'}]
    assert source_derived
    assert all(r['promotion_path']['terminal_status'] == 'SOURCE_DERIVED_CANDIDATE_RETAINED_NOT_NEW_LAW_PROMOTION' for r in source_derived)
    axis_rows = [r for r in rows if r['candidate_class'] == 'PROVISIONAL_RESEARCH_AXIS']
    assert len(axis_rows) == 1
    assert axis_rows[0]['promotion_path']['terminal_status'] == 'AXIS_PROMOTION_ROUTE_PENDING_WORLD_EVIDENCE'


def test_whole_pipeline_null_is_computed_and_unified_path_can_become_prepromotion_ready():
    from source.lawspace.scientific_promotion import ScientificPromotionCore
    owner = 'SCIENTIFIC-PROMOTION-QUALIFICATION'
    core = ScientificPromotionCore()
    record = {
        'candidate_id': 'CAND',
        'candidate_class': 'REAL_DATA_MECHANISM_COMPETITION',
        'domain_ids': ['qualification'],
        'source_owner_ids': ['QUALIFICATION-SOURCE'],
        'epistemic_statuses': ['CANDIDATE_ACTIVE'],
        'payload': {
            'candidate_id': 'CAND',
            'formula_source': 'dimensionless qualification relation',
            'mechanism_family': 'QUALIFICATION_MECHANISM',
            'training_rmse_db': 0.0,
        },
    }
    base = {'owner_id': owner, 'method': 'deterministic qualification fixture', 'evidence_digest': 'a' * 64}
    controls = {
        'exact_dimensional_qualification': {**base, 'status': 'NOT_APPLICABLE_DIMENSIONLESS_WITH_JUSTIFICATION'},
        'convention_audit': {**base, 'status': 'NOT_APPLICABLE_WITH_JUSTIFICATION'},
        'known_derivability_audit': {**base, 'status': 'PASS_NOT_DERIVED_FROM_ACCEPTED_LAWS'},
        'collapse_or_invariance': {**base, 'status': 'PASS_COLLAPSE_OR_INVARIANCE'},
        'regime_ood': {**base, 'status': 'PASS_DISTINCT_REGIME_OOD'},
        'cross_system_replication': {**base, 'status': 'PASS_INDEPENDENT_CROSS_SYSTEM_REPLICATION'},
        'whole_pipeline_null': {
            **base,
            'pipeline_digest': 'b' * 64,
            'observed_metric': 0.0,
            'null_best_metrics': [1.0 + i / 1000.0 for i in range(200)],
            'smaller_is_better': True,
        },
        'discriminating_experiment': {**base, 'status': 'PASS_DISCRIMINATING_EXPERIMENT_OBSERVED'},
    }
    receipt = core.qualify_frontier_record(record, controls=controls)
    assert core.frontier_path_status(receipt)['valid'] is True
    assert receipt['gates']['U8_WHOLE_PIPELINE_PERMUTATION_NULL']['pass'] is True
    assert receipt['gates']['U8_WHOLE_PIPELINE_PERMUTATION_NULL']['evidence']['null_permutation_count'] == 200
    assert receipt['gates']['U8_WHOLE_PIPELINE_PERMUTATION_NULL']['evidence']['empirical_p_value'] < 0.01
    assert receipt['prepromotion_ready'] is True
    assert receipt['gates']['U10_NUMERIC_PROMOTION_CORE']['pass'] is True


def test_numeric_scientific_promotion_cannot_bypass_unified_frontier_receipt():
    import numpy as np
    from evaluation.scientific_promotion_benchmark import _fixed_request, _alt_rows
    from source.lawspace.scientific_promotion import ScientificPromotionCore
    y = np.linspace(1.0, 2.0, 30)
    sigma = np.full_like(y, 0.05)
    replication = {
        'y': [float(v) for v in y + 1.0],
        'sigma': [float(v) for v in sigma],
        'predictions': [float(v) for v in y + 1.0],
        'regime_id': 'REPLICATION',
        'provenance': 'independent deterministic qualification',
        'independent': True,
    }
    request = _fixed_request(
        run_id='UNIFIED-PATH-BYPASS-CANARY', y_train=y, sigma_train=sigma, pred_train=y,
        y_ood=y + 0.5, sigma_ood=sigma, pred_ood=y + 0.5,
        alternatives=_alt_rows(y, y), replication=replication,
    )
    receipt = ScientificPromotionCore().evaluate(request)
    assert receipt['gate_results']['G_MINUS2_UNIFIED_FRONTIER_QUALIFICATION']['pass'] is False
    assert receipt['PROMOTION_ALLOWED'] is False
    assert receipt['FINAL_STATUS'] != 'LAW_CANDIDATE'


def test_fair_dovetail_release_snapshot_preserves_15_13_frontier_and_has_no_hidden_ceiling():
    from source.lawspace.candidates import DOVETAIL_STATE_RELATIVE_PATH, load_dovetail_state_file, dovetail_state_status
    result, _, _ = _frontier_replay_readonly()
    fair = result['fair_open_ended_traversal']
    summary = result['scan_summary']
    assert fair['state_valid'] is True
    assert fair['legacy_15_13_candidate_set_deleted'] is False
    assert fair['preserved_15_13_candidate_count'] == 1005
    assert fair['dovetail_continuation_candidate_count'] == 2175
    assert summary['active_candidate_ledger_count'] == 4106
    assert summary['dovetail_preserved_15_13_candidate_count'] == 1005
    state = load_dovetail_state_file(ROOT / DOVETAIL_STATE_RELATIVE_PATH)
    status = dovetail_state_status(state)
    assert status['valid'] is True
    contract = state['fairness_contract']
    assert contract['fixed_global_step_ceiling'] is None
    assert contract['fixed_pair_seed_ceiling'] is None
    assert contract['fixed_node_visit_ceiling'] is None
    assert contract['fixed_axis_order_ceiling'] is None
    assert contract['axis_birth_order_is_append_only'] is True
    assert contract['coverage_lane'].startswith('EVERY_MISSING_AXIS_EDGE_IS_ADDRESSABLE')


def test_fair_dovetail_runtime_advance_is_external_append_only_and_does_not_modify_seal(tmp_path, monkeypatch):
    from source.lawspace.candidates import DOVETAIL_STATE_RELATIVE_PATH
    sealed = ROOT / DOVETAIL_STATE_RELATIVE_PATH
    sealed_before = hashlib.sha256(sealed.read_bytes()).hexdigest()
    monkeypatch.setenv('PHI_STATE_DIR', str(tmp_path / 'state'))
    api = LawSpaceAPI(ROOT)
    before = api.get_atlas_dovetail_traversal_state()
    assert before['source'] == 'SEALED_RELEASE_SNAPSHOT'
    assert before['state_status']['node_count'] == 3706
    advance = api.advance_atlas_dovetail_traversal(step_budget=2)
    assert advance['status'] == 'DOVETAIL_TRANCHE_COMMITTED'
    assert advance['step_budget_this_call'] == 2
    assert advance['fixed_global_step_ceiling'] is None
    assert advance['old_nodes_deleted'] is False
    assert advance['node_count'] >= 3706
    assert advance['last_advance']['pair_visits_added'] == 1
    assert advance['last_advance']['node_visits_added'] == 1
    after = api.get_atlas_dovetail_traversal_state()
    assert after['source'] == 'EXTERNAL_MUTABLE_RUNTIME_STATE'
    assert after['state_status']['steps_executed'] == before['state_status']['steps_executed'] + 2
    assert after['state_status']['node_count'] >= before['state_status']['node_count']
    assert hashlib.sha256(sealed.read_bytes()).hexdigest() == sealed_before


def test_owner_axis_binding_overlay_recovers_only_qualified_existing_owner_semantics():
    from source.lawspace.knowledge_evolution import KnowledgeEvolutionKernel
    runtime=LawSpaceRuntime(ROOT); state=KnowledgeEvolutionKernel(ROOT).state(); rows=list(state.get('owner_axis_bindings',()))
    assert len(rows)==3 and all(row['status']=='OWNER_AXIS_BINDING_QUALIFIED' for row in rows)
    assert all(row['digest']==digest_payload({k:v for k,v in row.items() if k!='digest'}) for row in rows)
    assert 'aeronautics_and_aerostation.actuator_bandwidth' in runtime.catalog.effective_owner_axis_bindings('AERO-AEROSERVOELASTIC-STATE-SPACE')
    assert 'aeronautics_and_aerostation.actuator_bandwidth' in runtime.catalog.effective_owner_axis_bindings('AERO-STATE-FEEDBACK-CONTROL')
    assert 'chemistry.photochemical_regime' in runtime.catalog.effective_owner_axis_bindings('OCH-035')
    overlay={axis for values in runtime.catalog.owner_axis_bindings.values() for axis in values}
    assert 'aeronautics_and_aerostation.directional_stability' not in overlay
    assert 'aeronautics_and_aerostation.aeroelastic_divergence' not in overlay
    assert 'physics.detector_coupling' not in overlay

def test_materialized_relational_hypotheses_reach_u4_and_fail_closed_at_u5_world_evidence():
    from source.lawspace.knowledge_evolution import KnowledgeEvolutionKernel
    hypotheses={row['candidate_id']:row for row in KnowledgeEvolutionKernel(ROOT).state().get('hypothesis_materializations',())}
    assert len(hypotheses)==447
    rows=[json.loads(line) for line in (ROOT/'data/frontiers/ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    bound=[row for row in rows if row['candidate_id'] in hypotheses]; assert len(bound)==447
    for row in bound:
        g=row['promotion_path']['gates']; assert g['U1_TYPED_HYPOTHESIS_BINDING']['pass'] is True; assert g['U2_EXACT_DIMENSIONAL_QUALIFICATION']['pass'] is True; assert g['U3_CONVENTION_ARTIFACT_AUDIT']['pass'] is True; assert g['U4_KNOWN_DERIVABILITY_AUDIT']['pass'] is True; assert g['U5_COLLAPSE_OR_INVARIANCE']['pass'] is False
        assert row['promotion_path']['promotion_allowed'] is False and row['promotion_path']['candidate_is_false'] is False

def test_current_frontier_advances_by_depth_without_auto_promotion():
    result,before,after=_frontier_replay_readonly(); assert before==after; summary=result['scan_summary']; q=result['qualification_runtime']
    assert summary['active_candidate_ledger_count']==4106 and summary['dovetail_preserved_15_13_candidate_count']==1005 and summary['dovetail_extra_candidate_count']==2175
    assert summary['typed_hypothesis_materializations_persisted']==447 and summary['typed_hypothesis_materializations_bound_to_current_records']==447
    assert q['gate_pass_counts']['U2_EXACT_DIMENSIONAL_QUALIFICATION']==447 and q['gate_pass_counts']['U3_CONVENTION_ARTIFACT_AUDIT']==447 and q['gate_pass_counts']['U4_KNOWN_DERIVABILITY_AUDIT']==447 and q['gate_pass_counts']['U5_COLLAPSE_OR_INVARIANCE']==0
    assert q['promotion_allowed_count']==0 and q['candidate_false_count']==0


def test_resident_state_versions_are_separate_and_snapshot_restore_is_digest_bound(tmp_path):
    from source.lawspace.resident_cognitive import (
        ResidentStateLedgerOwner, COMPONENT_SCHEMA_VERSION, STATE_SCHEMA_VERSION,
        AI_ACCEPTANCE_VERSION, STATE_SCHEMA,
    )
    runtime=LawSpaceRuntime(ROOT)
    source=tmp_path/'source.json'
    src_ledger=ResidentStateLedgerOwner(source,system_release='15.16.0')
    state=src_ledger.empty(); state['heartbeat_count']=7; src_ledger.commit(state)
    raw=source.read_bytes(); source_sha=hashlib.sha256(raw).hexdigest()
    dest=tmp_path/'external'/'resident_cognitive_state.json'
    ledger=ResidentStateLedgerOwner(dest,system_release=runtime.current_release_id())
    receipt=ledger.restore_snapshot(source,expected_sha256=source_sha)
    restored=ledger.load()
    assert receipt['status']=='RESIDENT_STATE_RESTORED'
    assert restored['schema']==STATE_SCHEMA
    assert restored['heartbeat_count']==7
    ident=ledger.version_identity()
    assert ident['component_schema_version']==COMPONENT_SCHEMA_VERSION=='6.0.0'
    assert ident['state_schema_version']==STATE_SCHEMA_VERSION=='5'
    assert ident['ai_acceptance_version']==AI_ACCEPTANCE_VERSION=='15.10.5'
    assert ident['system_release']==runtime.current_release_id()
    assert ident['system_release'] not in {ident['component_schema_version'],ident['state_schema_version'],ident['ai_acceptance_version']}


def test_materialized_hypotheses_execute_u4_and_fail_closed_at_world_evidence():
    scan,_,_=_frontier_replay_readonly()
    assert scan['scan_summary']['typed_hypothesis_materializations_bound_to_current_records']==447
    assert scan['scan_summary']['materialized_relational_u4_pass_count']==447
    assert scan['scan_summary']['materialized_relational_u5_pass_count']==0
    assert scan['scan_summary']['candidate_response_projection_count']==1
    assert scan['scan_summary']['candidate_measurement_execution_count']==1
    assert scan['scan_summary']['measurement_executable_contract_count']==1
    assert scan['scan_summary']['scientifically_discriminating_measurement_count']==0
    assert scan['scan_summary']['world_attestation_count']==0
    assert scan['scan_summary']['automatic_scientific_promotion_count']==0
    execution=scan['data_binding_diagnostic']['measurement_execution']
    assert execution['status']=='PASS_EXECUTABLE_MEASUREMENT_RESPONSE_ACQUIRED_CANDIDATE_DISCRIMINATION_PENDING'
    assert execution['response']['value']==595.1908738041352 and execution['response']['auxiliary']['ndf']==518
    assert execution['candidate_specific_prediction_used'] is False and execution['scientific_discrimination_executed'] is False


def test_genesis_evidence_scoped_open_search_invariants():
    import sys
    ext_src=ROOT/'extensions'/'ATLAS_AI_RESEARCH_EXTENSION_v0_10_0'/'src'
    if str(ext_src) not in sys.path:
        sys.path.insert(0,str(ext_src))
    from scienceatlas_ai.continual import AlphaLedger, GenesisState
    from scienceatlas_ai.genesis_shells import FIXED_GENESIS_SHELL_CEILING, SearchPricing, ShellLadder
    from scienceatlas_ai.methodology import PipelineNullCalibrationOwner
    from scienceatlas_ai.operator_genesis import GenesisSplit, OperatorGenesisOwner
    from fractions import Fraction

    ledger=AlphaLedger()
    ledger.grant_for_samples(['e1'],domain='D',axes=('x','y'),evidence_fingerprints={'e1':'ev-1'})
    ledger.grant_for_samples(['e1'],domain='D',axes=('x','y'),evidence_fingerprints={'e1':'ev-1'})
    ledger.grant_for_samples(['alias'],domain='D',axes=('x','y'),evidence_fingerprints={'alias':'ev-1'})
    ledger.grant_for_samples(['missing-fp'],domain='D',axes=('x','y'))
    restored=AlphaLedger.from_json(ledger.to_json())
    restored.grant_for_samples(['alias2'],domain='D',axes=('x','y'),evidence_fingerprints={'alias2':'ev-1'})
    assert restored.balance_bp==25
    assert restored.max_balance_bp is None
    assert restored.can_spend(25,domain='D',axes=('x','y'))
    assert not restored.can_spend(25,domain='OTHER',axes=('x','y'))
    assert not restored.can_spend(25,domain='D',axes=('x','z'))

    ladder=ShellLadder(); pricing=SearchPricing()
    assert FIXED_GENESIS_SHELL_CEILING is None
    price70=pricing.search_price_bp(families_charged=ladder.shell(70).max_families_examined,permutation_count=1)
    assert ladder.deepest_affordable(pricing=pricing,balance_bp=price70,permutation_count=1)==70
    atoms=ladder.shell(20).grammar._atomic_terms(tuple(f'a{i}' for i in range(40)),max_atoms=64)
    assert len(atoms)==64 and atoms==tuple(sorted(atoms,key=lambda t:(t.degree,t.powers)))

    owner=OperatorGenesisOwner(null_owner=PipelineNullCalibrationOwner())
    shell=ladder.shell(0); budget=shell.budget(permutation_count=1)
    split=GenesisSplit(propose=('p',),fit=('f1','f2','f3'),seal=('s1','s2','s3'))
    rows=[({'x':Fraction(i)},Fraction(2*i+1)) for i in range(1,7)]
    def incumbent(rf,rs):
        return sum((y-Fraction(0))**2 for _,y in rs)
    state=GenesisState(ledger=AlphaLedger())
    state.ledger.grant_for_samples(
        [f's{i}' for i in range(20)],domain='D',axes=('x','y'),
        evidence_fingerprints={f's{i}':f'ev-s-{i}' for i in range(20)},
    )
    owner.run(target_axis='y',input_axes=('x',),rows_fit=rows[:3],rows_seal=rows[3:],budget=budget,
              split=split,incumbent_fit=incumbent,incumbent_owner_ids=('i',),shell=shell,
              ledger=state.ledger,journal=state.journal,pricing=pricing,search_domain='D')
    before=state.ledger.balance_bp
    duplicate=owner.run(target_axis='y',input_axes=('x',),rows_fit=rows[:3],rows_seal=rows[3:],budget=budget,
              split=split,incumbent_fit=incumbent,incumbent_owner_ids=('i',),shell=shell,
              ledger=state.ledger,journal=state.journal,pricing=pricing,search_domain='D')
    assert dict(duplicate.gates)['SEARCH_NOVELTY']=='FAIL_DUPLICATE_SEARCH'
    assert duplicate.alpha_price_bp==0 and state.ledger.balance_bp==before
