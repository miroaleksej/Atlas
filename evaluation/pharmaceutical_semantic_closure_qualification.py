from __future__ import annotations

import base64
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from source.lawspace.api import LawSpaceAPI
from source.lawspace.domains import BASE_DOMAIN_REGISTRIES, DOMAIN_REGISTRIES, canonical_axis_count, dynamic_axis_registry_state
from source.lawspace.pharmaceutical import PharmaceuticalDomainOwner, SELECTIVITY_BRIDGE_ID
from source.lawspace.pharmaceutical_problem_atlas import (
    PharmaceuticalProblemAtlasOwner,
    PharmaceuticalResearchOperatorOwner,
    RESEARCH_OPERATORS,
    SOURCE_DERIVED_UNVERIFIED,
)
from source.lawspace.schema import AxisValueKind, digest_payload
from source.lawspace.scientific_verification import (
    IndependentClaimVerifier, IndependentSourceVerifier, TRUST_STORE_SCHEMA,
    _attest_receipt,
)

SCHEMA = "phi-pharmaceutical-semantic-closure-qualification/v8.3"
OWNER_ID = "PHARMACEUTICAL-SEMANTIC-CLOSURE-QUALIFICATION/8.3.0"
NEW_AXES = (
    "solubility", "excipient_compatibility", "solubilization_capacity", "release_profile",
    "gastric_resistance", "storage_stability", "chelate_speciation",
    "diffusive_bioavailability", "assay_cost", "assay_reproducibility",
    "bioprocess_growth_rate", "contamination_risk", "selectivity", "synthetic_accessibility",
)
EXPECTED_KINDS = {
    "solubility": AxisValueKind.CONTINUOUS_RANGE,
    "excipient_compatibility": AxisValueKind.HIERARCHICAL_ENUM,
    "solubilization_capacity": AxisValueKind.CONTINUOUS_RANGE,
    "release_profile": AxisValueKind.SYMBOLIC_EXPRESSION,
    "gastric_resistance": AxisValueKind.HIERARCHICAL_ENUM,
    "storage_stability": AxisValueKind.CONTINUOUS_RANGE,
    "chelate_speciation": AxisValueKind.TEXT,
    "diffusive_bioavailability": AxisValueKind.CONTINUOUS_RANGE,
    "assay_cost": AxisValueKind.CONTINUOUS_RANGE,
    "assay_reproducibility": AxisValueKind.CONTINUOUS_RANGE,
    "bioprocess_growth_rate": AxisValueKind.CONTINUOUS_RANGE,
    "contamination_risk": AxisValueKind.DISTRIBUTION,
    "selectivity": AxisValueKind.CONTINUOUS_RANGE,
    "synthetic_accessibility": AxisValueKind.CONTINUOUS_RANGE,
}


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def run_release_qualification(root: str | Path) -> Mapping[str, Any]:
    root = Path(root)
    source_catalog = _read(root / "data" / "pharmaceutical" / "conference_2024_source_catalog_v8_3.json")
    atlas_source = _read(root / "data" / "pharmaceutical" / "pharmaceutical_problem_atlas_v8_3.json")
    owner = PharmaceuticalProblemAtlasOwner()
    operators = PharmaceuticalResearchOperatorOwner()
    domain = PharmaceuticalDomainOwner()
    atlas = owner.load_atlas(root / "data" / "pharmaceutical" / "pharmaceutical_problem_atlas_v8_3.json")
    api = LawSpaceAPI(root)
    registry = dynamic_axis_registry_state()

    checks: list[dict[str, Any]] = []
    def check(name: str, passed: bool, detail: Any = None) -> None:
        checks.append({"check": name, "pass": bool(passed), "detail": detail})

    source = source_catalog.get("source_document", {})
    check("SOURCE_DOCUMENT_274_PAGES_AND_DIGEST_BOUND", source.get("pdf_total_pages") == 274 and source.get("sha256") == "869f3256fdd8059a3b0d0a40ea84e69927f2548d8a16dc8c14a9db565dab4490", source)
    check("FULL_TOC_CATALOG_60_ARTICLES", source_catalog.get("article_count") == 60 and len(source_catalog.get("articles", ())) == 60)
    coverage = set()
    for a in source_catalog.get("articles", ()):
        coverage.update(range(int(a["pdf_start_page"]), int(a["pdf_end_page"]) + 1))
    check("ARTICLE_CONTENT_COVERAGE_CONTIGUOUS_PDF_15_TO_274", coverage == set(range(15, 275)), [min(coverage), max(coverage), len(coverage)] if coverage else None)
    check("SOURCE_ARTICLE_PAGE_AND_ARTICLE_TEXT_DIGESTS_PRESENT", all(len(str(a.get("page_text_sha256", ""))) == 64 and len(str(a.get("article_text_sha256", ""))) == 64 for a in source_catalog.get("articles", ())))
    check("SHARED_START_PAGES_ARE_TRIMMED_TO_OWN_ARTICLE_HEADING", any(a.get("semantic_start_trimmed_to_article_heading") is True for a in source_catalog.get("articles", ())))

    base_axis_count = sum(r.axis_count for r in BASE_DOMAIN_REGISTRIES.values())
    current_axis_count = canonical_axis_count()
    check("BASE_REGISTRY_CURRENT_AXES", registry.get("base_axis_count") == base_axis_count, base_axis_count)
    check("CURRENT_REGISTRY_CURRENT_AXES", sum(r.axis_count for r in DOMAIN_REGISTRIES.values()) == current_axis_count, current_axis_count)
    check("PHARMACEUTICAL_59_AXES", DOMAIN_REGISTRIES["pharmaceutical"].axis_count == 59, DOMAIN_REGISTRIES["pharmaceutical"].axis_count)
    check("BASE_DYNAMIC_ACCOUNTING_CURRENT", registry.get("base_axis_count") == base_axis_count and registry.get("dynamic_axis_count") == current_axis_count - base_axis_count and registry.get("canonical_axis_count") == current_axis_count, {k: registry.get(k) for k in ("base_axis_count", "dynamic_axis_count", "canonical_axis_count")})
    axis_rows = DOMAIN_REGISTRIES["pharmaceutical"].axes
    check("ALL_V82_SCHEMA_AXES_RETAINED_TYPED_AND_PROVENANCE_MARKED", all(a in axis_rows and axis_rows[a].value_kind == EXPECTED_KINDS[a] and axis_rows[a].provenance == "PHARMACEUTICAL_SCHEMA_ENRICHMENT_V8_2" for a in NEW_AXES))

    contract = owner.contract()
    op_contract = operators.contract()
    domain_contract = domain.contract()
    check("COMMON_VERIFICATION_CORE_REUSED_NOT_DUPLICATED", contract.get("source_policy", {}).get("scientific_verification_owner") == "SCIENTIFIC-VERIFICATION-CORE/8.0.0")
    module_text = (root / "source" / "lawspace" / "pharmaceutical_problem_atlas.py").read_text(encoding="utf-8")
    forbidden_generic_reimplementations = ("ExternalSourceResolutionOwner", "IndependentClaimVerifier", "Ed25519PrivateKey", "_attestation_valid", "load_trust_store")
    check("NO_GENERIC_VERIFICATION_IMPLEMENTATION_DUPLICATED_IN_ATLAS", "ScientificVerificationCore" in module_text and "ScientificPromotionCore" not in module_text and not any(token in module_text for token in forbidden_generic_reimplementations), [token for token in forbidden_generic_reimplementations if token in module_text])
    check("FOUR_RESEARCH_OPERATORS_RETAINED_EXACTLY", tuple(RESEARCH_OPERATORS) == tuple(op_contract.get("operators", {}).keys()), list(op_contract.get("operators", {})))
    check("OPERATORS_CANNOT_INVENT_OR_PROMOTE", op_contract.get("hard_invariants", {}).get("operator_is_scientific_promotion") is False and op_contract.get("hard_invariants", {}).get("operator_may_invent_missing_measurements") is False and op_contract.get("hard_invariants", {}).get("operator_may_assign_world_novelty") is False)

    # Contract-hole regression 1: raw source flags are never authoritative.
    adversarial = {
        "problem_id": "ADVERSARIAL-ACTIVE-EVIDENCE",
        "title": "adversarial",
        "problem_statement": "adversarial raw source flag",
        "source_locator": {"source_document_name": "x", "source_document_sha256": "0" * 64, "pdf_start_page": 1, "pdf_end_page": 1, "pdf_total_pages": 1},
        "source_derived_claims": [{"claim_id": "x", "relation": "SOURCE_STATES", "text": "unverified", "active_evidence": True}],
        "relevant_axes": ["evidence_provenance"],
        "research_operator": "NONE_SOURCE_CONTEXT_ONLY",
        "candidate_seed": {"status": "NONE"},
        "blocking_uncertainties": ["WORLD_SOURCE_VERIFICATION_REQUIRED"],
    }
    adversarial_out = owner.ingest_problem(adversarial)
    check("ADVERSARIAL_RAW_ACTIVE_EVIDENCE_FLAG_CANONICALLY_SANITIZED", adversarial_out["source_derived_claims"][0].get("active_evidence") is False and adversarial_out["source_derived_claims"][0].get("evidence_channel") == "AUDIT_ONLY_SOURCE_DERIVED" and not adversarial_out.get("active_verified_claims"), adversarial_out["source_derived_claims"][0])

    # Contract-hole regression 2: required cross-domain coordinates participate in closure.
    assay_problem = {
        "problem_id": "ASSAY-CROSS-DOMAIN-REGRESSION",
        "source_verification_status": SOURCE_DERIVED_UNVERIFIED,
        "relevant_axes": ["assay_cost", "assay_reproducibility"],
        "blocking_uncertainties": [],
    }
    assay_plan = operators.plan(assay_problem, "LOW_COST_ASSAY_DESIGN")
    expected_cross = {"chemistry:analytical_method", "chemistry:instrument_type", "metrology:uncertainty_model", "metrology:repeatability", "metrology:reproducibility"}
    check("CROSS_DOMAIN_COORDINATES_ARE_UNRESOLVED_WHEN_NOT_ADDRESSED", set(assay_plan.get("unresolved_cross_domain_axes", ())) == expected_cross and assay_plan.get("coordinate_closure_complete") is False and "OPERATOR_REQUIRED_CROSS_DOMAIN_COORDINATES_NOT_YET_ADDRESSED" in assay_plan.get("blocking_uncertainties", ()), assay_plan.get("unresolved_cross_domain_axes"))

    # Typed selectivity bridge closes old/new pharmaceutical coordinate vocabulary.
    bridge_contract = domain_contract.get("typed_coordinate_bridges", {}).get(SELECTIVITY_BRIDGE_ID, {})
    raw_bridge = domain.derive_selectivity_from_profile("HDAC6 selective")
    typed_bridge = domain.derive_selectivity_from_profile({
        "potency_direction": "LOWER_IS_MORE_POTENT", "unit": "nM", "target_value": 10.0,
        "comparators": [{"name": "HDAC1", "value": 100.0, "unit": "nM"}, {"name": "HDAC8", "value": 200.0, "unit": "nM"}],
    })
    check("SELECTIVITY_PROFILE_TO_SELECTIVITY_TYPED_BRIDGE_REGISTERED", bridge_contract.get("source_axis") == "selectivity_profile" and bridge_contract.get("target_axis") == "selectivity" and bridge_contract.get("relation") == "PARTIAL_TYPED_DERIVATION")
    check("SELECTIVITY_BRIDGE_FAILS_CLOSED_ON_FREE_TEXT", raw_bridge.get("derived") is False and str(raw_bridge.get("status", "")).startswith("NOT_DERIVABLE"), raw_bridge.get("status"))
    check("SELECTIVITY_BRIDGE_DERIVES_DECLARED_FOLD_METRIC", typed_bridge.get("derived") is True and abs(float(typed_bridge.get("value")) - 10.0) < 1e-12 and typed_bridge.get("unit") == "fold", typed_bridge)
    check("LEGACY_SELECTIVITY_PROFILE_AND_NEW_SELECTIVITY_AXES_BOTH_RETAINED", "selectivity_profile" in axis_rows and "selectivity" in axis_rows)

    check("ALL_60_SOURCE_PROBLEMS_INGESTED", atlas.get("problem_count") == 60 and len(atlas.get("rows", ())) == 60)
    check("ALL_60_TYPED_PROBLEM_GRAPHS_MATERIALIZED", atlas_source.get("typed_problem_graph_count") == 60 and all(r.get("typed_problem_graph", {}).get("schema") == "phi-pharmaceutical-typed-problem-graph/v8.3" for r in atlas.get("rows", ())))
    check("ALL_60_OPERATOR_ELIGIBILITY_RECEIPTS_MATERIALIZED", atlas_source.get("operator_adjudication_count") == 60 and all(r.get("operator_adjudication", {}).get("schema") == "phi-pharmaceutical-operator-eligibility/v8.3" for r in atlas.get("rows", ())))
    check("ABSTAIN_IS_ACTIVE_AND_MAJORITY_OUTCOME", atlas_source.get("abstain_count") == 52 and sum(r.get("research_operator") == "NONE_SOURCE_CONTEXT_ONLY" for r in atlas.get("rows", ())) == 52, atlas_source.get("operator_counts"))
    check("SEMANTIC_OPERATOR_COUNTS_ARE_CONSERVATIVE", atlas_source.get("operator_counts") == {"FORMULATION_RESCUE": 4, "DELIVERY_RESCUE": 1, "MULTIOBJECTIVE_MEDCHEM_SEARCH": 2, "LOW_COST_ASSAY_DESIGN": 1}, atlas_source.get("operator_counts"))
    check("ALL_SELECTED_OPERATORS_HAVE_FULL_COORDINATE_CLOSURE", all(r.get("operator_plan", {}).get("coordinate_closure_complete") is True and not r.get("operator_plan", {}).get("unresolved_required_axes") and not r.get("operator_plan", {}).get("unresolved_cross_domain_axes") for r in atlas.get("rows", ()) if r.get("research_operator") in RESEARCH_OPERATORS))
    check("ALL_60_FAIL_CLOSED_WITHOUT_WORLD_ATTESTATION", atlas.get("world_verified_problem_count") == 0 and all(r.get("source_verification_status") == SOURCE_DERIVED_UNVERIFIED for r in atlas.get("rows", ())))
    check("NO_SOURCE_DERIVED_CLAIM_BECOMES_ACTIVE_EVIDENCE", all(not r.get("active_verified_claims") and all(c.get("active_evidence") is False for c in r.get("source_derived_claims", ())) for r in atlas.get("rows", ())))

    by_printed = {int(r["source_locator"]["printed_start_page"]): r for r in atlas.get("rows", ())}
    hdac, zinc, nitaz, phage = by_printed[131], by_printed[117], by_printed[193], by_printed[217]
    vibrio, mr, pgh, color = by_printed[226], by_printed[233], by_printed[237], by_printed[267]
    check("HDAC6_REMAINS_MULTIOBJECTIVE_MEDCHEM", hdac.get("research_operator") == "MULTIOBJECTIVE_MEDCHEM_SEARCH" and {"selectivity", "selectivity_profile", "safety_pharmacology", "synthetic_accessibility"}.issubset(set(hdac.get("relevant_axes", ()))))
    check("ZINC_CHELATE_REMAINS_FORMULATION_TRADEOFF", zinc.get("research_operator") == "FORMULATION_RESCUE" and {"chelate_speciation", "diffusive_bioavailability"}.issubset(set(zinc.get("relevant_axes", ()))))
    check("NITAZOXANIDE_EVIDENCE_GAP_REMAINS_NO_OPERATOR_AND_NO_INVENTED_EIG", nitaz.get("problem_type") == "EVIDENCE_GAP" and nitaz.get("research_operator") == "NONE_SOURCE_CONTEXT_ONLY" and nitaz.get("evidence_gap", {}).get("sample_size_invented") is False and nitaz.get("evidence_gap", {}).get("dose_invented") is False and nitaz.get("evidence_gap", {}).get("expected_information_gain_computed") is False)
    check("PHAGE_SELECTS_SPECIFIC_DELIVERY_OVER_FORMULATION_PARENT", phage.get("research_operator") == "DELIVERY_RESCUE" and phage.get("operator_adjudication", {}).get("status") == "OPERATOR_SELECTED_SPECIFIC_DELIVERY_OVER_FORMULATION_PARENT")
    check("VIBRIO_SCALEUP_REMAINS_TYPED_WITHOUT_FAKE_OPERATOR", vibrio.get("research_operator") == "NONE_SOURCE_CONTEXT_ONLY" and {"bioprocess_growth_rate", "contamination_risk"}.issubset(set(vibrio.get("relevant_axes", ()))))
    check("MEMANTINE_CITICOLINE_REMAINS_FORMULATION_REGION", mr.get("research_operator") == "FORMULATION_RESCUE" and mr.get("candidate_seed", {}).get("search_region") == "joint modified-release exposure profile")
    check("PGH_SOLUBILITY_RESCUE_REMAINS_MATERIALIZED", pgh.get("research_operator") == "FORMULATION_RESCUE" and {"solubility", "solubilization_capacity", "excipient_compatibility"}.issubset(set(pgh.get("relevant_axes", ()))))
    check("COLORIMETRY_LOW_COST_ASSAY_HAS_CROSS_DOMAIN_CLOSURE", color.get("research_operator") == "LOW_COST_ASSAY_DESIGN" and expected_cross.issubset(set(color.get("relevant_axes", ()))) and color.get("operator_plan", {}).get("coordinate_closure_complete") is True)

    # Explicit regressions for the v8.2 keyword-lowering false positives.
    check("FUMARIA_ANALYTICAL_COMPOSITION_ABSTAINS_FROM_MEDCHEM", by_printed[161].get("research_operator") == "NONE_SOURCE_CONTEXT_ONLY")
    check("ERUCA_DOSAGE_FORM_IS_FORMULATION_NOT_LOW_COST_ASSAY", by_printed[171].get("research_operator") == "FORMULATION_RESCUE")
    check("COPPER_GLYCINATE_SYNTHESIS_ABSTAINS_FROM_MEDCHEM", by_printed[210].get("research_operator") == "NONE_SOURCE_CONTEXT_ONLY")
    check("LOCAL_HEMOSTATIC_REVIEW_NOT_CONTAMINATED_BY_PREVIOUS_PHAGE_ARTICLE", by_printed[221].get("research_operator") == "NONE_SOURCE_CONTEXT_ONLY" and "БАКТЕРИОФАГ" not in json.dumps(by_printed[221].get("typed_problem_graph", {}), ensure_ascii=False).upper())
    builder_text = (root / "evaluation" / "build_pharmaceutical_problem_atlas_v8_3.py").read_text(encoding="utf-8")
    check("BLANKET_INFER_AXES_AND_OPERATOR_FUNCTION_REMOVED", "def infer_axes_and_operator" not in builder_text and "operator_assigned_by_single_keyword" in builder_text)

    all_plans = [r.get("operator_plan", {}) for r in atlas.get("rows", ()) if r.get("research_operator") in RESEARCH_OPERATORS]
    check("NO_OPERATOR_GENERATES_MOLECULAR_STRUCTURE_WORLD_CLAIM_OR_EIG", all(p.get("candidate", {}).get("generated_molecular_structure") is False and p.get("candidate", {}).get("world_novelty_claimed") is False and p.get("promotion_allowed_by_operator") is False and p.get("next_experiment", {}).get("expected_information_gain_computed") is False for p in all_plans))

    # First concrete end-to-end pharmaceutical WORLD-cycle attempt.  The model,
    # candidate region, falsifiers and experiment are materialized; WORLD/EIG stay
    # blocked because the release intentionally has no external WORLD verifier keys.
    world_cycle = api.prepare_pharmaceutical_world_cycle("PHARMA-PROBLEM-59")
    check("COLORIMETRY_QUANTITATIVE_MODEL_HAS_NINE_SOURCE_DERIVED_REGRESSIONS", len(world_cycle.get("quantitative_model", {}).get("equations", ())) == 9 and world_cycle.get("quantitative_model", {}).get("world_verified") is False)
    check("WORLD_CYCLE_MATERIALIZES_MODEL_REGION_FALSIFIERS_AND_EXPERIMENT", bool(world_cycle.get("quantitative_model")) and world_cycle.get("candidate_region", {}).get("candidate_class") == "ASSAY_DESIGN_REGION" and len(world_cycle.get("falsifiers", ())) >= 3 and world_cycle.get("next_experiment", {}).get("experiment_class") == "PAIRED_REFERENCE_METHOD_VALIDATION")
    check("WORLD_CYCLE_FAILS_CLOSED_AT_EXTERNAL_ATTESTATION_AND_EIG", world_cycle.get("status") == "WORLD_CYCLE_BLOCKED_EXTERNAL_ATTESTATION_REQUIRED" and world_cycle.get("world_cycle_complete") is False and world_cycle.get("expected_information_gain", {}).get("computed") is False and "EXTERNAL_WORLD_ATTESTATION_REQUIRED" in world_cycle.get("blocking_uncertainties", ()), world_cycle.get("blocking_uncertainties"))

    # Serialized WORLD strings are never authority.  Even direct-owner input must
    # replay the central verification bundle and exact problem binding.
    spoofed_color = dict(color)
    spoofed_color["source_verification_status"] = "WORLD_VERIFIED"
    spoofed_cycle = owner.prepare_world_cycle(spoofed_color)
    check("SERIALIZED_WORLD_STATUS_CANNOT_UNLOCK_WORLD_CYCLE", spoofed_cycle.get("source_verification", {}).get("world_verified_for_this_problem") is False and spoofed_cycle.get("status") == "WORLD_CYCLE_BLOCKED_EXTERNAL_ATTESTATION_REQUIRED")

    # Deployment-mechanics canary: ephemeral WORLD private keys exist only in this
    # harness.  It proves that *when* externally attested exact problem/model
    # bindings and an explicit uncertainty/likelihood contract are supplied, the
    # pharmaceutical owner delegates EIG to the existing domain-neutral owner.
    # This is NOT evidence for the conference article and is never persisted as WORLD.
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        source_private = Ed25519PrivateKey.generate()
        claim_private = Ed25519PrivateKey.generate()
        resolver_owner = "V83-QUALIFICATION-EXTERNAL-SOURCE-RESOLVER"
        reviewer_owner = "V83-QUALIFICATION-INDEPENDENT-CLAIM-REVIEWER"
        trust_path = td_path / "trust.json"
        trust_path.write_text(json.dumps({
            "schema": TRUST_STORE_SCHEMA,
            "keys": {
                "v83-world-source-key": {
                    "public_key_b64": base64.b64encode(source_private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode("ascii"),
                    "trust_tier": "WORLD", "roles": ["SOURCE"], "authorized_owners": [resolver_owner],
                    "private_key_shipped": False, "external_service_required": True,
                },
                "v83-world-claim-key": {
                    "public_key_b64": base64.b64encode(claim_private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode("ascii"),
                    "trust_tier": "WORLD", "roles": ["CLAIM"], "authorized_owners": [reviewer_owner],
                    "private_key_shipped": False, "external_service_required": True,
                },
            },
        }), encoding="utf-8")

        proposer = contract["owner_id"]
        def signed_world_bundle(field: str, value: str, content: str, suffix: str) -> Mapping[str, Any]:
            content_bytes = content.encode("utf-8")
            resolution = {
                "identifier_type": "DOI", "declared_identifier": f"10.0000/v83.qual.{suffix}",
                "resolved_identifier": f"10.0000/v83.qual.{suffix}", "source_exists": True,
                "bibliographic_match": True, "title": f"v8.3 qualification {suffix}",
                "resolved_url": f"https://example.invalid/v83.qual.{suffix}", "retrieved_at": "QUALIFICATION_SIMULATION",
                "retrieval_method": "LIVE_EXTERNAL_RESOLUTION", "resolver_owner": resolver_owner,
                "content_digest": hashlib.sha256(content_bytes).hexdigest(), "container": "application/json",
            }
            unsigned_source = IndependentSourceVerifier(trusted_resolver_owners=[resolver_owner]).verify(resolution, proposer_owner=proposer)
            source_body = dict(unsigned_source); source_body.pop("source_receipt_id", None)
            signed_source = _attest_receipt(source_body, digest_key="source_verification_digest", private_key=source_private, key_id="v83-world-source-key", attestation_owner=resolver_owner)
            signed_source["source_receipt_id"] = "SVR-" + signed_source["source_verification_digest"][:24].upper()
            review = {
                "reviewer_owner": reviewer_owner, "relation": "SUPPORTS", "review_method": "INDEPENDENT_MANUAL_REVIEW",
                "claim_field": field, "claim_value": value, "claim_text": f"exact {field} binding",
                "fact_summary": f"qualification binding for {suffix}", "locator": "qualification:1",
                "quote_or_paraphrase": "exact digest binding", "entailment_verified": True,
                "source_content_digest": resolution["content_digest"],
            }
            unsigned_claim = IndependentClaimVerifier(trusted_reviewer_owners=[reviewer_owner]).verify(signed_source, review, proposer_owner=proposer)
            claim_body = dict(unsigned_claim); claim_body.pop("claim_receipt_id", None)
            signed_claim = _attest_receipt(claim_body, digest_key="claim_verification_digest", private_key=claim_private, key_id="v83-world-claim-key", attestation_owner=reviewer_owner)
            signed_claim["claim_receipt_id"] = "CVR-" + signed_claim["claim_verification_digest"][:24].upper()
            return {
                "proposer_owner": proposer, "evidence_class": "EXTERNAL_SOURCE",
                "claim_values": {field: value}, "source_receipts": [signed_source],
                "claim_receipts": [signed_claim], "minimum_distinct_sources": 1,
            }

        predictive = {
            "schema": "phi-pharmaceutical-predictive-experiment-model/v8.3",
            "model_id": "QUALIFICATION-COLORIMETRY-PAIRED-REFERENCE",
            "candidate_ids": ["H_REFERENCE_EQUIVALENT", "H_REFERENCE_NONEQUIVALENT"],
            "priors": {"H_REFERENCE_EQUIVALENT": 0.5, "H_REFERENCE_NONEQUIVALENT": 0.5},
            "uncertainty_model": {
                "schema": "phi-pharmaceutical-uncertainty-model/v8.3",
                "model_id": "QUALIFICATION-BERNOULLI-OUTCOME-MODEL",
                "status": "EXPLICIT_QUALIFICATION_CANARY_ONLY",
            },
            "experiment_specs": [{
                "experiment_id": "PAIRED_REFERENCE_VALIDATION",
                "measurements": ["bias_vs_reference", "uncertainty_budget"],
                "outcomes": ["ACCEPT", "REJECT"],
                "likelihoods": {
                    "H_REFERENCE_EQUIVALENT": {"ACCEPT": 0.90, "REJECT": 0.10},
                    "H_REFERENCE_NONEQUIVALENT": {"ACCEPT": 0.20, "REJECT": 0.80},
                },
                "cost": 1.0, "risk_penalty": 0.0,
                "metadata": {"qualification_canary_only": True},
            }],
        }
        predictive_digest = digest_payload(predictive)
        old_trust = os.environ.get("PHI_SCIENTIFIC_VERIFIER_TRUST_STORE_PATH")
        os.environ["PHI_SCIENTIFIC_VERIFIER_TRUST_STORE_PATH"] = str(trust_path)
        try:
            source_bundle = signed_world_bundle("problem_binding_digest", str(color["world_binding_digest"]), json.dumps(color["world_binding"], sort_keys=True), "problem")
            predictive_bundle = signed_world_bundle("predictive_model_digest", predictive_digest, json.dumps(predictive, sort_keys=True), "predictive")
            canary_cycle = owner.prepare_world_cycle(
                color, verification_bundle=source_bundle, predictive_model_receipt=predictive,
                predictive_verification_bundle=predictive_bundle,
            )
        finally:
            if old_trust is None:
                os.environ.pop("PHI_SCIENTIFIC_VERIFIER_TRUST_STORE_PATH", None)
            else:
                os.environ["PHI_SCIENTIFIC_VERIFIER_TRUST_STORE_PATH"] = old_trust
    check("WORLD_CYCLE_EIG_BRANCH_DELEGATES_TO_EXISTING_OWNER_UNDER_EXACT_ATTESTED_BINDINGS", canary_cycle.get("world_cycle_complete") is True and canary_cycle.get("status") == "WORLD_CYCLE_EIG_READY_NOT_SCIENTIFIC_PROMOTION" and canary_cycle.get("expected_information_gain", {}).get("computed") is True and canary_cycle.get("expected_information_gain", {}).get("owner") == "DOMAIN-NEUTRAL-INFORMATION-GAIN/6.24.0" and not canary_cycle.get("blocking_uncertainties"), {"status": canary_cycle.get("status"), "source_verification": canary_cycle.get("source_verification"), "predictive_model": canary_cycle.get("predictive_model"), "blockers": canary_cycle.get("blocking_uncertainties"), "eig": canary_cycle.get("expected_information_gain", {}).get("receipt", {}).get("experiments", [{}])[0].get("expected_information_gain_bits")})

    required_api = (
        "get_pharmaceutical_domain_contract", "assess_pharmaceutical_research_record", "get_pharmaceutical_axis_subset", "assess_pharmaceutical_hypothesis", "derive_pharmaceutical_selectivity",
        "get_pharmaceutical_problem_atlas_contract", "get_pharmaceutical_research_operator_contract", "load_pharmaceutical_problem_atlas", "get_pharmaceutical_problem", "prepare_pharmaceutical_world_cycle",
    )
    check("PUBLIC_API_PRESERVES_OLD_PHARMA_AND_EXPOSES_CLOSURE_PATH", all(name in LawSpaceAPI.READ_TOOLS for name in required_api), [name for name in required_api if name not in LawSpaceAPI.READ_TOOLS])
    api_atlas = api.load_pharmaceutical_problem_atlas()
    check("PUBLIC_API_REPLAYS_SAME_60_PROBLEM_ATLAS", api_atlas.get("digest") == atlas.get("digest") and api_atlas.get("problem_count") == 60)

    passed = sum(int(x["pass"]) for x in checks)
    payload = {
        "schema": SCHEMA,
        "owner_id": OWNER_ID,
        "status": "PASS_PHARMACEUTICAL_SEMANTIC_CLOSURE_V8_3" if passed == len(checks) else "FAIL_PHARMACEUTICAL_SEMANTIC_CLOSURE_V8_3",
        "passed": passed,
        "total": len(checks),
        "checks": checks,
        "source_catalog_summary": {"article_count": source_catalog.get("article_count"), "source_document": source},
        "atlas_summary": {
            "problem_count": atlas.get("problem_count"), "world_verified_problem_count": atlas.get("world_verified_problem_count"),
            "evidence_gap_count": atlas.get("evidence_gap_count"), "operator_counts": atlas_source.get("operator_counts"), "abstain_count": atlas_source.get("abstain_count"),
            "typed_problem_graph_count": atlas_source.get("typed_problem_graph_count"),
        },
        "world_cycle_attempt": {
            "problem_id": world_cycle.get("problem_id"), "status": world_cycle.get("status"),
            "world_cycle_complete": world_cycle.get("world_cycle_complete"), "blocking_uncertainties": world_cycle.get("blocking_uncertainties"),
            "deployment_mechanics_canary": {
                "qualification_only": True, "world_cycle_complete": canary_cycle.get("world_cycle_complete"),
                "eig_computed": canary_cycle.get("expected_information_gain", {}).get("computed"),
                "eig_owner": canary_cycle.get("expected_information_gain", {}).get("owner"),
                "scientific_claim_from_canary": False,
            },
        },
        "claim_boundary": {
            "source_collection_is_world_verified": False,
            "source_derived_claims_are_active_evidence": False,
            "typed_problem_graph_is_world_truth": False,
            "semantic_operator_selection_is_scientific_promotion": False,
            "new_drug_discovered": False,
            "clinical_recommendation": False,
        },
    }
    payload["digest"] = digest_payload(payload)
    out = root / "reports" / "pharmaceutical_semantic_closure_qualification_v8_3.json"
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    import sys
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    print(json.dumps(run_release_qualification(root), ensure_ascii=False, indent=2, sort_keys=True))
