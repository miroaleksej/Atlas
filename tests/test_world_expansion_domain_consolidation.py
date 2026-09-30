from pathlib import Path

import pytest

from source.lawspace.api import LawSpaceAPI
from source.lawspace.domains import DOMAIN_REGISTRIES, load_domain_plugin_manifests
from source.lawspace.domain_plugins import ScienceDomainPluginRegistry
from source.lawspace.source_capabilities import (
    audit_existing_closed_loop_integration,
    load_provider_capability_registry,
    load_world_trust_registry,
    match_source_provider,
    plan_world_evidence_campaign,
    run_existing_closed_loop_glue,
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
    assert "FROZEN_EXECUTION_WAITING_FOR_RESPONSE_PROJECTION" in result["primary_bottlenecks_in_order"]
    assert "WORLD_TRUST_EMPTY" in result["primary_bottlenecks_in_order"]
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
    assert result["counts"]["blocked_world_attestor_required"] == 8
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
    route = {row["stage"]: row for row in result["route"]}
    assert route["FROZEN_EXECUTION"]["status"] == "BOUND_TO_FRONTIER_CAMPAIGN_WAITING_FOR_RESPONSE_PROJECTION"
    assert result["glue_run_status"] == "EXISTING_GLUE_EXECUTED_FAIL_CLOSED_PRE_WORLD"


def test_existing_closed_loop_glue_api_exposed():
    api = LawSpaceAPI(ROOT)
    assert "run_existing_closed_loop_glue" in api.READ_TOOLS
    result = api.run_existing_closed_loop_glue(max_frontier_rows=500, max_campaign_items=8)
    assert result["universal_execution_runtime_bound_to_frontier_campaign"] is True
