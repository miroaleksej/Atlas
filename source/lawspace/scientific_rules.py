"""Single directory of domain-neutral scientific rules for Φ-LawSpace.

This module does not implement a second verifier, research cycle or promotion
engine.  It is the canonical routing/contract surface that binds every science
to the existing authoritative owners.  Domain packages contain only their own
semantics, equations, admissibility constraints and experiment models.
"""
from __future__ import annotations

from typing import Any, Mapping

from .schema import digest_payload
from .scientific_verification import ScientificVerificationCore, OWNER_ID as VERIFICATION_OWNER
from .research_cycle import RESEARCH_CYCLE_OWNER, RESEARCH_CYCLE_SCHEMA, RESEARCH_CYCLE_VERSION, ADAPTIVE_RESEARCH_KERNEL_OWNER, CLAIM_FIREWALL_OWNER
from .scientific_promotion import ScientificPromotionCore, OWNER_ID as PROMOTION_OWNER, OWNER_VERSION as PROMOTION_VERSION
from .adaptive_axis import OWNER_ID as ADAPTIVE_AXIS_OWNER

OWNER_ID = "COMMON-SCIENTIFIC-RULES/1.0.0"
SCHEMA = "phi-common-scientific-rules/v1.1"


class CommonScientificRulesCore:
    """Canonical non-duplicated routing contract for all scientific domains."""

    owner_id = OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        verification = ScientificVerificationCore().contract()
        promotion = ScientificPromotionCore().contract()
        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "implementation_policy": "ROUTING_CONTRACT_ONLY_NO_PARALLEL_SOLVER",
            "authoritative_owners": {
                "evidence_and_claim_verification": VERIFICATION_OWNER,
                "research_cycle_compatibility_facade": RESEARCH_CYCLE_OWNER,
                "adaptive_research_kernel": ADAPTIVE_RESEARCH_KERNEL_OWNER,
                "claim_provenance_firewall": CLAIM_FIREWALL_OWNER,
                "scientific_promotion": f"{PROMOTION_OWNER}/{PROMOTION_VERSION}",
                "adaptive_axis_discovery": ADAPTIVE_AXIS_OWNER,
            },
            "authoritative_contracts": {
                "verification": {"owner": VERIFICATION_OWNER, "schema": verification.get("schema"), "digest": verification.get("digest")},
                "research_cycle_compatibility_facade": {"owner": RESEARCH_CYCLE_OWNER, "schema": RESEARCH_CYCLE_SCHEMA, "version": RESEARCH_CYCLE_VERSION},
                "adaptive_research_kernel": {"owner": ADAPTIVE_RESEARCH_KERNEL_OWNER},
                "claim_provenance_firewall": {"owner": CLAIM_FIREWALL_OWNER},
                "promotion": {"owner": f"{PROMOTION_OWNER}/{PROMOTION_VERSION}", "schema": promotion.get("schema"), "digest": promotion.get("digest")},
            },
            "generic_rules": {
                "raw_identifiers_are_not_scientific_evidence": True,
                "semantic_null_is_not_positive_evidence": True,
                "source_authenticity_and_claim_binding_are_central": True,
                "contradictions_must_be_accounted_for": True,
                "candidate_generation_cannot_promote": True,
                "prior_art_must_not_feed_back_into_a_frozen_blind_selector": True,
                "information_gain_requires_explicit_predictive_likelihoods": True,
                "unknown_or_unexecuted_gates_fail_closed": True,
                "world_novelty_is_never_inferred_from_internal_absence": True,
                "domain_owner_may_define_domain_semantics_but_not_shadow_generic_rules": True,
                "absence_of_prior_art_is_not_candidate_rejection": True,
                "external_contradiction_triggers_context_or_axis_investigation_before_rejection": True,
                "unexplained_residual_may_propose_research_local_axis": True,
                "axis_registry_has_no_fixed_ceiling": True,
                "research_local_axis_requires_promotion_before_canonical_registration": True,
                "candidate_registry_is_baseline_not_solution_space": True,
                "active_baseline_must_contain_confirmed_controls_only": True,
                "unverified_generated_couplings_belong_to_frontier_registry": True,
                "baseline_replacement_does_not_falsify_displaced_candidates": True,
                "unknown_candidate_is_not_false": True,
                "synthetic_false_positive_term_requires_known_ground_truth": True,
                "failed_promotion_is_not_candidate_falsification": True,
                "falsified_status_requires_explicit_declared_falsification_gate": True,
                "void_or_sparse_region_is_not_proof_of_physical_absence": True,
                "void_frontier_regions_are_priority_research_targets": True,
                "search_lane_is_broader_than_promotion_lane": True,
                "promotion_statistics_do_not_revoke_exploration_rights": True,
                "high_dimensionality_reduces_identification_confidence_not_search_admissibility": True,
                "owner_affiliation_does_not_block_axis_combination": True,
                "domain_affiliation_does_not_block_axis_combination": True,
                "cross_domain_tuple_exploration_requires_no_preexisting_bridge": True,
                "arithmetic_cross_domain_composition_requires_typed_contract": True,
                "registered_axis_count_is_current_address_space_not_universal_ceiling": True,
                "known_law_catalog_is_not_required_for_hypothesis_synthesis": True,
                "fixed_competitor_count_is_not_truth_gate": True,
                "assistant_is_not_scientific_evidence_source": True,
                "assistant_cannot_assign_atlas_native_claim_origin": True,
                "atlas_native_requires_digest_bound_kernel_receipt": True,
                "every_persistent_frontier_candidate_requires_unified_promotion_path": True,
                "direct_numeric_promotion_cannot_bypass_unified_frontier_receipt": True,
                "whole_pipeline_permutation_null_required_before_law_candidate": True,
                "source_derived_candidate_is_retained_but_not_promoted_as_independent_new_law": True,
                "missing_qualification_evidence_is_pending_not_false": True,
            },
            "new_domain_onboarding": {
                "required": [
                    "data/domains/<domain>.json",
                    "optional domain-specific owner module for semantics/equations/gates",
                ],
                "must_not_copy": [
                    "source authenticity logic",
                    "semantic-null logic",
                    "generic evidence-class logic",
                    "generic novelty logic",
                    "generic EIG engine",
                    "scientific promotion gates",
                ],
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    def validate_domain_delegation(self, domain_contract: Mapping[str, Any]) -> Mapping[str, Any]:
        common = dict(domain_contract.get("common_scientific_rules", {}) or {})
        gates = {
            "COMMON_RULE_OWNER_DECLARED": common.get("owner_id") == OWNER_ID,
            "GENERIC_RULES_NOT_IMPLEMENTED_LOCALLY": domain_contract.get("generic_scientific_rules_implemented_locally") is False,
            "DOMAIN_ID_DECLARED": bool(str(domain_contract.get("domain_id", "")).strip()),
            "DOMAIN_OWNER_DECLARED": bool(str(domain_contract.get("owner_id", "")).strip()),
        }
        payload = {
            "schema": "phi-domain-common-rule-delegation/v1",
            "owner_id": OWNER_ID,
            "domain_id": domain_contract.get("domain_id"),
            "domain_owner_id": domain_contract.get("owner_id"),
            "gates": gates,
            "qualified": all(gates.values()),
            "status": "PASS_COMMON_RULE_DELEGATION" if all(gates.values()) else "BLOCKED_COMMON_RULE_DELEGATION",
        }
        return {**payload, "digest": digest_payload(payload)}
