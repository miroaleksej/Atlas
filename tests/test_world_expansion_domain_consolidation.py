from pathlib import Path

import pytest

from source.lawspace.api import LawSpaceAPI
from source.lawspace.domains import DOMAIN_REGISTRIES, load_domain_plugin_manifests
from source.lawspace.domain_plugins import ScienceDomainPluginRegistry
from source.lawspace.source_capabilities import (
    load_provider_capability_registry,
    load_world_trust_registry,
    match_source_provider,
    plan_world_evidence_campaign,
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
