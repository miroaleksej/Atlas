from pathlib import Path

import pytest

from source.lawspace.api import LawSpaceAPI
from source.lawspace.domains import DOMAIN_REGISTRIES, load_domain_plugin_manifests
from source.lawspace.domain_plugins import ScienceDomainPluginRegistry
from source.lawspace.resident_cognitive import DynamicGoalGraphOwner, OntologyAwarePlannerOwner
from source.lawspace.source_capabilities import (
    audit_existing_closed_loop_integration,
    compile_required_evidence_routes,
    compile_universal_required_evidence_loop,
    derive_semantic_evidence_needs,
    run_epistemic_metabolism_cycle,
    run_universal_obligation_execution_loop,
    search_ideal_ai_formula_candidates,
    load_provider_capability_registry,
    load_world_trust_registry,
    match_source_provider,
    plan_world_evidence_campaign,
    run_existing_closed_loop_glue,
    run_existing_lowering_projection_preflight,
    run_world_closed_loop_campaign,
)


ROOT = Path(__file__).resolve().parents[1]


def test_final008_provider_registry_matches_real_archives_and_fails_closed():
    registry = load_provider_capability_registry(ROOT)
    provider_ids = {row["provider_id"] for row in registry["providers"]}
    assert {
        "ESA_GAIA_ARCHIVE_TAP_PLUS_DR3",
        "MAST_STSCI_TAP",
        "JHTDB_LOCAL_REST_CURRENT",
        "NASA_EXOPLANET_ARCHIVE_PS",
    } <= provider_ids

    gaia = match_source_provider({
        "domain_id": "astronomy",
        "needed_observable": "stellar_parallax",
        "source_class": "OBSERVATIONAL_ARCHIVE",
        "require_uncertainty": True,
    }, ROOT)
    assert gaia["status"] == "CAPABLE_PROVIDER_SELECTED"
    assert gaia["selected_provider"]["provider_id"] == "ESA_GAIA_ARCHIVE_TAP_PLUS_DR3"
    assert gaia["atlas_invented_provider"] is False

    blocked = match_source_provider({
        "domain_id": "biology",
        "needed_observable": "live_cell_intervention_result",
        "source_class": "FORWARD_ORACLE",
    }, ROOT)
    assert blocked["status"] == "NO_CAPABLE_PROVIDER"
    assert blocked["selected_provider"] is None


def test_world_trust_store_has_no_private_key_and_does_not_fake_attestation():
    trust = load_world_trust_registry(ROOT)
    assert trust["private_key_policy"]["private_key_stored_in_atlas_repository"] is False
    assert trust["private_key_policy"]["external_signer_required"] is True
    assert trust["attestors"] == []
    assert trust["empty_registry_semantics"]["world_attestation_ready"] is False


def test_world_evidence_campaign_prioritizes_obtainable_missing_evidence_without_promotion():
    plan = plan_world_evidence_campaign([
        {
            "candidate_id": "A",
            "u_stage": "U4",
            "scientific_value": 0.9,
            "missing_evidence": [{
                "domain_id": "astronomy",
                "needed_observable": "stellar_parallax",
                "require_uncertainty": True,
            }],
        },
        {
            "candidate_id": "B",
            "u_stage": "U4",
            "scientific_value": 1.0,
            "missing_evidence": [{
                "domain_id": "biology",
                "needed_observable": "unknown_live_intervention",
                "source_class": "FORWARD_ORACLE",
            }],
        },
    ], ROOT)
    rows = {row["candidate_id"]: row for row in plan["selected"]}
    assert rows["A"]["status"] == "EVIDENCE_OBTAINABLE"
    assert rows["A"]["matches"][0]["selected_provider"]["provider_id"] == "ESA_GAIA_ARCHIVE_TAP_PLUS_DR3"
    assert rows["B"]["status"] == "NO_CAPABLE_PROVIDER"
    assert plan["mutation_performed"] is False
    assert plan["scientific_promotion_allowed"] is False
    assert plan["active_world_attestor_count"] == 0


def test_builtin_domain_consolidation_manifests_do_not_change_axis_counts_or_copy_rules():
    manifests = load_domain_plugin_manifests(ROOT / "data" / "domains")
    for domain_id in ("astronomy", "mechanics", "physics", "materials_science"):
        assert manifests[domain_id]["builtin_domain_consolidation"] is True
        assert domain_id in DOMAIN_REGISTRIES
        forbidden = {"generic_rules", "scientific_promotion_rules", "world_trust", "established_law"}
        assert not (forbidden & set(manifests[domain_id]))

    listed = {row["domain_id"]: row for row in ScienceDomainPluginRegistry().list_plugins()}
    assert listed["astronomy"]["builtin_domain_consolidation"] is True
    assert listed["astronomy"]["axis_count"] == DOMAIN_REGISTRIES["astronomy"].axis_count
    assert listed["astronomy"]["measurement_capability_count"] >= 3


def test_domain_manifest_still_rejects_generic_scientific_rules(tmp_path):
    bad = {
        "schema": "phi-domain-plugin-manifest/v1",
        "domain_id": "bad_science",
        "domain_role": "natural_science",
        "common_rules_owner": "COMMON-SCIENTIFIC-RULES/1.0.0",
        "axes": [],
        "entity_profiles": [],
        "constraints": [],
        "owner": {},
        "world_trust": {"promote": True},
    }
    path = tmp_path / "bad.json"
    path.write_text(__import__("json").dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError, match="generic scientific rules"):
        load_domain_plugin_manifests(tmp_path)


def test_final008_api_surfaces_are_read_only():
    api = LawSpaceAPI(ROOT)
    assert api.get_source_provider_capability_registry()["schema"] == "phi-source-provider-capability-registry/v1"
    assert api.get_world_trust_registry()["attestors"] == []
    match = api.match_source_provider({"domain_id": "mechanics", "needed_observable": "velocity_gradient"})
    assert match["selected_provider"]["provider_id"] == "JHTDB_LOCAL_REST_CURRENT"
    campaign = api.plan_world_evidence_campaign([{
        "candidate_id": "DNS-CANDIDATE",
        "scientific_value": 0.7,
        "measurement_intent": {"domain_id": "mechanics", "needed_observable": "velocity_gradient"},
    }])
    assert campaign["selected"][0]["status"] == "EVIDENCE_OBTAINABLE"
    assert campaign["private_key_in_repository"] is False


def test_world_closed_loop_campaign_uses_frontier_but_blocks_without_attestor():
    result = run_world_closed_loop_campaign(ROOT, max_frontier_rows=500, max_campaign_items=8)
    assert result["status"] == "CAMPAIGN_BLOCKED_WORLD_ATTESTOR_REQUIRED"
    assert result["frontier_rows_examined"] == 500
    assert result["provider_matched_episode_count"] > 0
    assert result["independently_attested_episode_count"] == 0
    assert result["active_world_attestor_count"] == 0
    assert result["representation_world_model_changed"] is False
    assert result["external_data_fetched"] is False
    assert result["mutation_performed"] is False
    assert all(row["status"] == "WORLD_ATTESTATION_BLOCKED_NO_ACTIVE_ATTESTOR" for row in result["episodes"])
    assert result["claim_boundary"]["empty_world_trust_store_can_update_world_model"] is False


def test_world_closed_loop_campaign_api_exposes_same_gate():
    api = LawSpaceAPI(ROOT)
    result = api.run_world_closed_loop_campaign(max_frontier_rows=500, max_campaign_items=8)
    assert result["status"] == "CAMPAIGN_BLOCKED_WORLD_ATTESTOR_REQUIRED"
    assert result["independently_attested_episode_count"] == 0


def test_existing_closed_loop_integration_audit_reuses_underused_systems_fail_closed():
    result = audit_existing_closed_loop_integration(ROOT, max_frontier_rows=500, max_campaign_items=8)
    assert result["status"] == "EXISTING_SYSTEMS_AUDITED_FAIL_CLOSED"
    assert result["integration_policy"]["new_scientific_owner_created"] is False
    assert result["integration_policy"]["reuse_existing_owners_only"] is True
    assert result["integration_policy"]["knowledge_state_mutated"] is False
    assert result["claim_boundary"]["underused_existing_systems_should_be_reused_before_new_owners"] is True
    systems = {row["system_id"]: row for row in result["system_inventory"]}
    assert {
        "SCIENTIFIC-EXPLOITATION-ORCHESTRATOR",
        "FROZEN-EXPERIMENT-EXECUTION",
        "CLOSED-LOOP-AXIS-RESEARCH",
        "WORLD-ATTESTATION",
        "U5-ATTEMPT-SCHEDULER",
        "KNOWLEDGE-EVOLUTION-KERNEL",
    } <= set(systems)
    assert result["state_counts"]["hypothesis_materializations"] == 447
    assert result["state_counts"]["world_attestations"] == 0
    assert "MASS_U4_TO_PREDICTION_LOWERING_NOT_SCALED" in result["primary_bottlenecks_in_order"]
    assert "UNIVERSAL_EXECUTION_RUNTIME_NOT_BOUND_TO_FRONTIER_CAMPAIGN" not in result["primary_bottlenecks_in_order"]
    assert "MATCHED_U4_EPISODES_REQUIRE_RESPONSE_OBSERVABLE_CONTRACT" in result["primary_bottlenecks_in_order"]
    assert "MATCHED_PROVIDER_EPISODES_REQUIRE_U4_MATERIALIZATION" in result["primary_bottlenecks_in_order"]
    assert "FROZEN_EXECUTION_WAITING_FOR_RESPONSE_PROJECTION" in result["primary_bottlenecks_in_order"]
    assert "WORLD_TRUST_EMPTY" in result["primary_bottlenecks_in_order"]
    assert result["lowering_projection_preflight_status"] == "LOWERING_PROJECTION_PREFLIGHT_CLASSIFIED_EXISTING_GAPS"
    assert result["glue_run_status"] == "EXISTING_GLUE_EXECUTED_FAIL_CLOSED_PRE_WORLD"
    route = {row["stage"]: row for row in result["route"]}
    assert route["FROZEN_EXECUTION"]["status"] == "BOUND_TO_FRONTIER_CAMPAIGN_WAITING_FOR_RESPONSE_PROJECTION"
    assert route["WORLD_ATTESTATION"]["status"] == "BLOCKED_NO_ACTIVE_EXTERNAL_ATTESTOR"
    assert route["U5_REPLAY"]["status"] == "BLOCKED_WORLD_EVIDENCE_REQUIRED"


def test_existing_closed_loop_integration_audit_api_exposed():
    api = LawSpaceAPI(ROOT)
    assert "audit_existing_closed_loop_integration" in api.READ_TOOLS
    result = api.audit_existing_closed_loop_integration(max_frontier_rows=500, max_campaign_items=8)
    assert result["status"] == "EXISTING_SYSTEMS_AUDITED_FAIL_CLOSED"
    assert result["integration_policy"]["external_data_fetched"] is False


def test_existing_closed_loop_glue_binds_runtime_to_frontier_but_stops_pre_world():
    result = run_existing_closed_loop_glue(ROOT, max_frontier_rows=500, max_campaign_items=8)
    assert result["status"] == "EXISTING_GLUE_EXECUTED_FAIL_CLOSED_PRE_WORLD"
    assert result["route_closed_through_existing_systems"] is True
    assert result["universal_execution_runtime_bound_to_frontier_campaign"] is True
    assert result["route_complete_to_world_boundary_count"] == 0
    assert result["external_data_fetched"] is False
    assert result["knowledge_state_mutated"] is False
    assert result["counts"]["provider_matched"] == 8
    assert result["counts"]["bound_to_frozen_execution_runtime"] == 8
    assert result["counts"]["blocked_prediction_lowering_required"] == 0
    assert result["counts"]["blocked_response_projection_required"] == 2
    assert result["counts"]["blocked_world_attestor_required"] == 8
    assert result["lowering_projection_preflight_digest"]
    assert any(
        stage["stage"] == "FROZEN_EXECUTION_RUNTIME"
        and stage["runtime_bound_to_frontier_provider_route"] is True
        for episode in result["episodes"]
        for stage in episode["stages"]
    )


def test_existing_closed_loop_glue_updates_audit_runtime_gap():
    result = audit_existing_closed_loop_integration(ROOT, max_frontier_rows=500, max_campaign_items=8)
    assert "UNIVERSAL_EXECUTION_RUNTIME_NOT_BOUND_TO_FRONTIER_CAMPAIGN" not in result["primary_bottlenecks_in_order"]
    assert "FROZEN_EXECUTION_WAITING_FOR_RESPONSE_PROJECTION" in result["primary_bottlenecks_in_order"]
    assert "MATCHED_U4_EPISODES_REQUIRE_RESPONSE_OBSERVABLE_CONTRACT" in result["primary_bottlenecks_in_order"]
    route = {row["stage"]: row for row in result["route"]}
    assert route["FROZEN_EXECUTION"]["status"] == "BOUND_TO_FRONTIER_CAMPAIGN_WAITING_FOR_RESPONSE_PROJECTION"
    assert result["glue_run_status"] == "EXISTING_GLUE_EXECUTED_FAIL_CLOSED_PRE_WORLD"


def test_existing_lowering_projection_preflight_classifies_all_matched_episodes():
    result = run_existing_lowering_projection_preflight(ROOT, max_frontier_rows=500, max_campaign_items=8)
    assert result["status"] == "LOWERING_PROJECTION_PREFLIGHT_CLASSIFIED_EXISTING_GAPS"
    assert result["knowledge_state_mutated"] is False
    assert result["external_data_fetched"] is False
    assert result["counts"]["episode_count"] == 8
    assert result["counts"]["provider_matched"] == 8
    assert result["counts"]["u4_materialized"] == 2
    assert result["counts"]["u4_materialization_required"] == 6
    assert result["counts"]["response_observable_contract_required"] == 2
    assert result["counts"]["ready_for_frozen_runtime"] == 0
    statuses = {row["terminal_status"] for row in result["episodes"]}
    assert "BLOCKED_RESPONSE_OBSERVABLE_CONTRACT_REQUIRED" in statuses
    assert "BLOCKED_U4_MATERIALIZATION_REQUIRED" in statuses
    assert result["claim_boundary"]["preflight_can_replace_response_projection"] is False


def test_required_evidence_route_compiler_unifies_existing_modules_without_new_owner():
    result = compile_required_evidence_routes(ROOT, max_frontier_rows=500, max_campaign_items=8)
    assert result["schema"] == "phi-required-evidence-route-compiler/v1"
    assert result["status"] == "REQUIRED_EVIDENCE_ROUTES_COMPILED_WITH_FAIL_CLOSED_NEXT_STEPS"
    assert result["route_count"] == 8
    assert result["counts"]["provider_matched_episode_count"] == 8
    assert result["counts"]["ready_for_external_acquisition"] == 0
    assert result["routing_policy"]["single_universal_route_graph"] is True
    assert result["routing_policy"]["new_scientific_owner_created"] is False
    assert result["routing_policy"]["activate_all_modules_for_every_question"] is False
    assert result["routing_policy"]["delete_historical_tests_without_replacement"] is False
    assert result["claim_boundary"]["route_compilation_changes_representation"] is False
    assert result["knowledge_state_mutated"] is False
    assert result["external_data_fetched"] is False

    assert result["architecture_layers"] == [
        "DISCOVERY_SEARCH_CORE",
        "EXPERIMENT_EVIDENCE_RUNTIME",
        "PROMOTION_TRUST_CORE",
    ]
    assert result["counts"]["by_current_layer"]["DISCOVERY_SEARCH_CORE"] == 6
    assert result["counts"]["by_current_layer"]["EXPERIMENT_EVIDENCE_RUNTIME"] == 2
    assert result["counts"]["by_next_required_object"]["u4_hypothesis_materialization"] == 6
    assert result["counts"]["by_next_required_object"]["response_observable_contract"] == 2

    by_candidate = {row["candidate_id"]: row for row in result["routes"]}
    assert by_candidate["SUBSPACE-1BB180E9901D07B0325B"]["current_stage"] == "U4_READY"
    assert by_candidate["SUBSPACE-1BB180E9901D07B0325B"]["next_required_object"] == "response_observable_contract"
    assert "DiscriminatingExperimentAutopilotOwner" in by_candidate["SUBSPACE-1BB180E9901D07B0325B"]["eligible_existing_modules"]
    assert by_candidate["SUBSPACE-19A74046A7D81C316CBF"]["next_required_object"] == "u4_hypothesis_materialization"
    assert by_candidate["SUBSPACE-19A74046A7D81C316CBF"]["no_new_module_required"] is True
    assert all(row["activate_all_modules"] is False for row in result["routes"])


def test_existing_closed_loop_glue_api_exposed():
    api = LawSpaceAPI(ROOT)
    assert "run_existing_closed_loop_glue" in api.READ_TOOLS
    assert "run_existing_lowering_projection_preflight" in api.READ_TOOLS
    assert "compile_required_evidence_routes" in api.READ_TOOLS
    result = api.run_existing_closed_loop_glue(max_frontier_rows=500, max_campaign_items=8)
    assert result["universal_execution_runtime_bound_to_frontier_campaign"] is True
    preflight = api.run_existing_lowering_projection_preflight(max_frontier_rows=500, max_campaign_items=8)
    assert preflight["counts"]["episode_count"] == 8
    routes = api.compile_required_evidence_routes(max_frontier_rows=500, max_campaign_items=8)
    assert routes["route_count"] == 8


def test_universal_required_evidence_loop_routes_current_frontier_without_domain_branches():
    result = compile_universal_required_evidence_loop(ROOT, max_frontier_rows=500, max_campaign_items=8)
    assert result["schema"] == "phi-universal-required-evidence-execution-loop/v1"
    assert result["status"] == "UNIVERSAL_REQUIRED_EVIDENCE_LOOP_COMPILED"
    assert result["obligation_count"] == 8
    assert result["capability_gap_count"] == 0
    assert result["input_source"] == "required_evidence_routes"
    assert result["counts"]["by_obligation_type"]["TYPED_HYPOTHESIS_MATERIALIZATION"] == 6
    assert result["counts"]["by_obligation_type"]["OBSERVABLE_CONTRACT"] == 2
    assert result["routing_policy"]["route_determined_by_scientific_obligation_not_domain"] is True
    assert result["routing_policy"]["domain_specific_if_branches_allowed"] is False
    assert result["routing_policy"]["domain_adapters_only_describe_quantities_actions_evidence"] is True
    assert result["routing_policy"]["capability_gap_becomes_birth_input"] is True
    assert result["routing_policy"]["residual_returns_to_discovery"] is True
    assert result["claim_boundary"]["universal_loop_replaces_scientific_owners"] is False
    assert result["knowledge_state_mutated"] is False
    assert result["external_data_fetched"] is False
    assert result["loop"] == [
        "QUESTION",
        "FRONTIER",
        "REQUIRED_EVIDENCE_ROUTE",
        "OBLIGATION",
        "RESOLVE_CAPABILITY",
        "MIND_PLAN",
        "ACTION_OR_GAP",
        "WORLD_OR_PROOF_OR_COMPUTATION",
        "EVIDENCE",
        "LEARNING_UPDATE",
        "INDEPENDENT_VERIFICATION",
        "RESIDUAL_ATTRIBUTION",
        "REVISION_OR_BIRTH",
        "FRONTIER_CONTINUATION",
    ]
    assert all(row["domain_conditionals_used"] is False for row in result["obligations"])
    assert all(row["action"]["executes_now"] is False for row in result["obligations"])


def test_universal_required_evidence_loop_accepts_generic_obligations_and_preserves_gaps():
    result = compile_universal_required_evidence_loop(
        ROOT,
        candidate_specs=[
            {"candidate_id": "GENERIC-OBS", "required_obligation": "OBSERVABLE_CONTRACT"},
            {"candidate_id": "GENERIC-PROOF", "required_obligation": "PROOF_OBLIGATION"},
            {"candidate_id": "GENERIC-BRIDGE", "applicability_status": "TYPED_CROSS_DOMAIN_BRIDGE_REQUIRED"},
            {"candidate_id": "GENERIC-UNKNOWN", "missing_object": "unknown_future_capability"},
        ],
    )
    assert result["schema"] == "phi-universal-required-evidence-execution-loop/v1"
    assert result["status"] == "UNIVERSAL_REQUIRED_EVIDENCE_LOOP_HAS_CAPABILITY_GAPS"
    assert result["input_source"] == "explicit_candidate_specs"
    assert result["obligation_count"] == 4
    assert result["capability_gap_count"] == 1
    by_candidate = {row["candidate_id"]: row for row in result["obligations"]}
    assert by_candidate["GENERIC-OBS"]["obligation_type"] == "OBSERVABLE_CONTRACT"
    assert by_candidate["GENERIC-PROOF"]["obligation_type"] == "PROOF_OBLIGATION"
    assert by_candidate["GENERIC-BRIDGE"]["obligation_type"] == "SEMANTIC_BRIDGE_BIRTH"
    assert by_candidate["GENERIC-UNKNOWN"]["obligation_type"] == "CAPABILITY_GAP"
    assert "measurement_adapter_birth" in by_candidate["GENERIC-UNKNOWN"]["residual"]["birth_path"]
    assert all(row["domain_conditionals_used"] is False for row in result["obligations"])


def test_universal_required_evidence_loop_api_exposed():
    api = LawSpaceAPI(ROOT)
    assert "compile_universal_required_evidence_loop" in api.READ_TOOLS
    result = api.compile_universal_required_evidence_loop(max_frontier_rows=500, max_campaign_items=8)
    assert result["obligation_count"] == 8
    assert result["status"] == "UNIVERSAL_REQUIRED_EVIDENCE_LOOP_COMPILED"


def test_semantic_evidence_need_derivation_uses_claim_axes_not_domain_dispatch():
    candidate = {
        "candidate_id": "GENERIC-FLOW",
        "domain_ids": ["totally_new_domain_name"],
        "payload": {
            "axis_ids": ["unknown_science.turbulence_regime", "unknown_science.data_regime"],
            "applicability_contract": {
                "status": "REPRESENTATION_AND_WORLD_ATTESTATION_REQUIRED",
                "next_requirement": "bind the observer to measurable data before promotion",
            },
            "unbound_axis_ids": ["unknown_science.data_regime"],
        },
        "promotion_path": {
            "gates": {
                "U5_COLLAPSE_OR_INVARIANCE": {
                    "pass": False,
                    "required_evidence": ["world measurement evidence"],
                }
            }
        },
    }
    needs = derive_semantic_evidence_needs(candidate)
    assert needs["schema"] == "phi-semantic-evidence-need-derivation/v1"
    assert needs["core_domain_dispatch_used"] is False
    assert needs["claim_boundary"]["domain_name_selects_observable"] is False
    assert any(row["axis_id"] == "turbulence_regime" for row in needs["intents"])
    assert all("domain_id" not in row for row in needs["intents"])
    match = match_source_provider(needs["intents"][0], ROOT)
    assert match["atlas_invented_provider"] is False


def test_universal_adaptive_mind_routes_learning_action_and_representation_without_domain_names():
    result = compile_universal_required_evidence_loop(
        ROOT,
        candidate_specs=[
            {
                "candidate_id": "GENERIC-ACTION",
                "required_obligation": "TYPED_WORLD_ACTION",
                "planning_features": {
                    "blocks_progress": True,
                    "expected_information_gain_bits": 0.75,
                    "residual_pressure": 0.0,
                    "source": "CONTROL_EIG",
                },
            },
            {
                "candidate_id": "GENERIC-LEARNING",
                "required_obligation": "LEARNING_UPDATE",
                "planning_features": {
                    "blocks_progress": True,
                    "expected_information_gain_bits": 0.0,
                    "residual_pressure": 0.5,
                    "source": "CONTROL_SUPPORT_GAP",
                },
            },
            {
                "candidate_id": "GENERIC-REPRESENTATION",
                "required_obligation": "REPRESENTATION_BIRTH",
                "planning_features": {
                    "blocks_progress": True,
                    "expected_information_gain_bits": 0.0,
                    "residual_pressure": 2.0,
                    "source": "CONTROL_RESIDUAL",
                },
            },
        ],
    )
    by_id = {row["candidate_id"]: row for row in result["obligations"]}
    assert by_id["GENERIC-ACTION"]["capability"]["capability_id"] == "typed-world-action"
    assert by_id["GENERIC-LEARNING"]["capability"]["capability_id"] == "postfreeze-world-model-learning"
    assert by_id["GENERIC-REPRESENTATION"]["capability"]["capability_id"] == "representation-birth"
    assert by_id["GENERIC-ACTION"]["planning"]["expected_information_gain_bits"] == pytest.approx(0.75)
    assert all(row["domain_conditionals_used"] is False for row in result["obligations"])
    assert result["routing_policy"]["mind_plans_from_typed_obligations_not_domain_names"] is True
    assert result["routing_policy"]["learning_requires_postfreeze_resolved_experience"] is True


def test_resident_planner_consumes_universal_obligation_capabilities_without_parallel_owner():
    loop = compile_universal_required_evidence_loop(
        ROOT,
        candidate_specs=[
            {
                "candidate_id": "GENERIC-ACTION",
                "required_obligation": "TYPED_WORLD_ACTION",
                "planning_features": {
                    "blocks_progress": True,
                    "expected_information_gain_bits": 0.9,
                    "residual_pressure": 0.0,
                },
            },
            {
                "candidate_id": "GENERIC-REPRESENTATION",
                "required_obligation": "REPRESENTATION_BIRTH",
                "planning_features": {
                    "blocks_progress": True,
                    "expected_information_gain_bits": 0.0,
                    "residual_pressure": 2.0,
                },
            },
        ],
    )
    goals = DynamicGoalGraphOwner().update(
        (),
        root_goal={"goal_id": "GENERIC-ROOT", "statement": "resolve an unknown research problem"},
        concept_result={"status": "CONCEPT_GROUNDING_INSUFFICIENT_FAIL_CLOSED"},
        operator_result={"status": "NO_QUALIFIED_SKILL_TO_COMPILE"},
        cognitive_episode={
            "representation_route": "EXISTING_REPRESENTATION",
            "universal_obligations": loop["obligations"],
        },
    )
    selected = next(row for row in goals["goals"] if row["goal_id"] == goals["selected_goal_id"])
    assert selected["goal_class"] == "RESOLVE_RESEARCH_OBLIGATION"
    assert selected["obligation"]["obligation_type"] == "REPRESENTATION_BIRTH"
    assert goals["selected_by_universal_obligation_planning"] is True
    plan = OntologyAwarePlannerOwner().plan(
        goal_graph=goals,
        concepts=(),
        operators=(),
        previous_plans=(),
    )
    assert plan["universal_obligation_digest"] == selected["obligation"]["digest"]
    assert plan["steps"]
    assert all(step.get("owner") and step.get("operation") for step in plan["steps"])
    assert any(step.get("capability_id") == "representation-birth" for step in plan["steps"])
    assert plan["claim_boundary"]["planner_can_bypass_owner_gates"] is False


def test_universal_obligation_execution_loop_produces_typed_one_step_receipts():
    result = run_universal_obligation_execution_loop(
        ROOT,
        candidate_specs=[
            {
                "candidate_id": "GENERIC-PROOF",
                "required_obligation": "PROOF_OBLIGATION",
                "statement": "for all x in {1,2,3}, x=x",
            },
            {"candidate_id": "GENERIC-WORLD", "required_obligation": "WORLD_ATTESTATION"},
            {"candidate_id": "GENERIC-GAP", "missing_object": "unknown_future_capability"},
        ],
    )
    assert result["schema"] == "phi-universal-obligation-execution-loop/v1"
    assert result["status"] == "UNIVERSAL_OBLIGATION_EXECUTION_STEPPED_FAIL_CLOSED"
    assert result["step_count"] == 3
    by_id = {row["candidate_id"]: row for row in result["steps"]}
    assert by_id["GENERIC-PROOF"]["execution_status"] == "PROOF_OBLIGATION_COMPILED_BY_EXISTING_FORMAL_OWNER"
    assert by_id["GENERIC-WORLD"]["execution_status"] == "BLOCKED_AT_EXTERNAL_OR_AUTHORIZED_ACTION_BOUNDARY"
    assert by_id["GENERIC-GAP"]["execution_status"] == "CAPABILITY_GAP_PRESERVED_FOR_BIRTH"
    assert all(row["state_transition_allowed"] is False for row in result["steps"])
    assert result["external_data_fetched"] is False
    assert result["knowledge_state_mutated"] is False


def test_universal_execution_api_exposed():
    api = LawSpaceAPI(ROOT)
    assert "derive_semantic_evidence_needs" in api.READ_TOOLS
    assert "run_universal_obligation_execution_loop" in api.READ_TOOLS
    result = api.run_universal_obligation_execution_loop(
        candidate_specs=[{"candidate_id": "GENERIC-GAP", "missing_object": "unknown_future_capability"}]
    )
    assert result["steps"][0]["execution_status"] == "CAPABILITY_GAP_PRESERVED_FOR_BIRTH"


def test_epistemic_metabolism_cycle_turns_unknowns_into_obligations_without_promotion():
    result = run_epistemic_metabolism_cycle(ROOT, max_frontier_rows=500, max_campaign_items=8, max_execution_steps=8)
    assert result["schema"] == "phi-epistemic-metabolism-cycle/v1"
    assert result["status"] == "EPISTEMIC_METABOLISM_CYCLE_PRESERVED_RESIDUALS_FAIL_CLOSED"
    assert result["definition"] == "unknown_to_typed_obligation_to_existing_owner_step_to_residual_to_next_growth"
    assert result["obligation_count"] == 8
    assert result["executed_step_count"] == 8
    assert result["external_data_fetched"] is False
    assert result["knowledge_state_mutated"] is False
    assert result["scientific_promotion_allowed"] is False
    assert result["new_scientific_owner_created"] is False
    assert result["claim_boundary"]["metabolism_cycle_is_agi_claim"] is False
    assert result["claim_boundary"]["residual_is_failure"] is False
    growth = result["growth_vector"]
    assert growth["schema"] == "phi-epistemic-growth-vector/v1"
    assert growth["obligation_distribution"]["TYPED_HYPOTHESIS_MATERIALIZATION"] == 6
    assert growth["obligation_distribution"]["OBSERVABLE_CONTRACT"] == 2
    assert any(row["missing_object"] == "typed_u4_hypothesis_materialization" for row in growth["missing_objects"])
    assert any(row["missing_object"] == "response_observable_contract" for row in growth["missing_objects"])


def test_epistemic_metabolism_cycle_preserves_capability_gap_as_birth_input_and_api_exposes_it():
    api = LawSpaceAPI(ROOT)
    assert "run_epistemic_metabolism_cycle" in api.READ_TOOLS
    result = api.run_epistemic_metabolism_cycle(
        candidate_specs=[{"candidate_id": "IDEAL-AI-GAP", "missing_object": "unknown_future_capability"}],
        max_execution_steps=1,
    )
    assert result["schema"] == "phi-epistemic-metabolism-cycle/v1"
    assert result["capability_gap_count"] == 1
    assert result["executed_step_count"] == 1
    step = result["execution_loop"]["steps"][0]
    assert step["execution_status"] == "CAPABILITY_GAP_PRESERVED_FOR_BIRTH"
    assert step["next_obligation"] == "REPRESENTATION_BIRTH"
    assert result["growth_vector"]["missing_objects"][0]["growth_axis"] == "capability_birth"
    assert result["claim_boundary"]["new_representation_is_canonical_without_evidence"] is False


def test_ideal_ai_formula_search_compares_multiple_research_local_candidates():
    result = search_ideal_ai_formula_candidates(ROOT, max_frontier_rows=500, max_campaign_items=8, max_execution_steps=8)
    assert result["schema"] == "phi-ideal-ai-formula-search/v1"
    assert result["status"] == "IDEAL_AI_FORMULA_CANDIDATES_COMPARED"
    assert result["selected_formula_id"] == "F3_EPISTEMIC_METABOLISM"
    assert len(result["formula_candidates"]) >= 5
    assert {row["formula_id"] for row in result["formula_candidates"]}.issuperset({
        "F1_STRICT_TRUTH_PRODUCT",
        "F2_WORLD_TRUST_GATE",
        "F3_EPISTEMIC_METABOLISM",
        "F4_FRONTIER_PRESSURE",
        "F5_BALANCED_ORGANISM_MEAN",
    })
    params = result["parameters"]
    assert params["O_obligationization"] == pytest.approx(1.0)
    assert params["X_safe_owner_step"] == pytest.approx(1.0)
    assert params["P_promotion_discipline"] == pytest.approx(1.0)
    assert params["T_world_trust"] == pytest.approx(0.0)
    assert params["V_evidence_closure"] == pytest.approx(0.0)
    assert result["active_world_attestor_count"] == 0
    assert any(row["missing_object"] == "active_world_attestor" for row in result["missing_growth_objects"])
    assert result["claim_boundary"]["formula_is_agi_proof"] is False
    assert result["claim_boundary"]["formula_is_scientific_law"] is False
    assert result["claim_boundary"]["formula_can_replace_world_evidence"] is False
    assert result["scientific_promotion_allowed"] is False


def test_ideal_ai_formula_search_api_exposed_and_accepts_explicit_gap():
    api = LawSpaceAPI(ROOT)
    assert "search_ideal_ai_formula_candidates" in api.READ_TOOLS
    result = api.search_ideal_ai_formula_candidates(
        candidate_specs=[{"candidate_id": "IDEAL-AI-GAP", "missing_object": "unknown_future_capability"}],
        max_execution_steps=1,
    )
    assert result["selected_formula_id"] == "F3_EPISTEMIC_METABOLISM"
    assert result["parameters"]["C_capability_resolution"] == pytest.approx(0.0)
    assert any(row["missing_object"] == "new_capability_or_adapter" for row in result["missing_growth_objects"])
