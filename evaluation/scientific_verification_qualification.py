"""Release qualification for the domain-neutral Scientific Verification Core v8.0."""
from __future__ import annotations

import copy
import inspect
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from source.lawspace.scientific_verification import (
    OWNER_ID as VERIFICATION_OWNER,
    SOURCE_RECEIPT_SCHEMA,
    SOURCE_VERIFIER_OWNER_ID,
    ScientificVerificationCore,
    IndependentSourceVerifier,
    IndependentClaimVerifier,
    IndependentArtifactVerifier, ARTIFACT_VERIFIER_OWNER_ID, TRUST_STORE_SCHEMA,
    _attest_receipt, content_addressed_digest,
    build_qualification_source_receipt,
    build_qualification_claim_receipt,
    load_trust_store,
)
from source.lawspace.pharmaceutical import PharmaceuticalDomainOwner, OWNER_ID as PHARMA_OWNER
from source.lawspace.research_cycle import DynamicAxisPromotionOwner, DynamicAxisProposal
from source.lawspace.particle_candidate_dossiers import ParticleCandidateDossierOwner
from source.lawspace.schema import digest_payload
from source.lawspace.domains import reload_dynamic_axis_registry


def _source(identifier: str, proposer: str, text: str) -> Mapping[str, Any]:
    return build_qualification_source_receipt(
        identifier_type="PMID", identifier=identifier, title=f"QUAL {identifier}",
        content_text=text, proposer_owner=proposer,
    )


def _target_identity(source: Mapping[str, Any], proposer: str, target: str) -> Mapping[str, Any]:
    return build_qualification_claim_receipt(
        source, claim_field="target_identity", claim_value=target, relation="IDENTIFIES",
        claim_text=f"{target} identity", fact_summary=f"qualification identity for {target}",
        proposer_owner=proposer,
    )


def _bundle_for_nlrp3(*, include_negative: bool = True, declared_value: str = "AMBIGUOUS") -> tuple[dict[str, Any], dict[str, Any]]:
    s_pos = _source("28167322", PHARMA_OWNER, "positive NLRP3 NASH result")
    s_neg = _source("36641116", PHARMA_OWNER, "negative NLRP3 fibrosing NASH result")
    claims = [build_qualification_claim_receipt(
        s_pos, claim_field="causal_support", claim_value=declared_value, relation="SUPPORTS",
        claim_text="NLRP3 causal support adjudication", fact_summary="positive preclinical result",
        proposer_owner=PHARMA_OWNER,
    )]
    if include_negative:
        claims.append(build_qualification_claim_receipt(
            s_neg, claim_field="causal_support", claim_value=declared_value, relation="CONTRADICTS",
            claim_text="NLRP3 causal support adjudication", fact_summary="negative fibrosing NASH result",
            proposer_owner=PHARMA_OWNER,
        ))
    ident = _target_identity(s_pos, PHARMA_OWNER, "NLRP3")
    claims.append(ident)
    bundle = {
        "proposer_owner": PHARMA_OWNER,
        "evidence_class": "EXTERNAL_SOURCE",
        "claim_values": {"causal_support": declared_value},
        "source_receipts": [s_pos, s_neg] if include_negative else [s_pos],
        "claim_receipts": claims,
        "entities": [{
            "entity_slot": "target", "label": "NLRP3", "entity_kind": "MOLECULAR_TARGET",
            "resolution_status": "ESTABLISHED_EXTERNAL", "canonical_identifier": "NLRP3",
            "identity_claim_receipt_ids": [ident["claim_receipt_id"]],
        }],
        "minimum_distinct_sources": 2 if include_negative else 1,
    }
    evidence = {"causal_support": declared_value}
    return bundle, evidence


def run_release_qualification(root: str | Path | None = None) -> Mapping[str, Any]:
    checks: list[dict[str, Any]] = []
    def check(name: str, value: bool, detail: Any = None) -> None:
        checks.append({"check": name, "pass": bool(value), "detail": detail})

    core = ScientificVerificationCore()
    contract = core.contract()
    trust = load_trust_store()
    world_keys = [k for k, v in trust["keys"].items() if str(v.get("trust_tier", "")).upper() == "WORLD"]
    check("WORLD_TRUST_STORE_EMPTY_BY_DEFAULT", world_keys == [], world_keys)
    check("NO_RUNTIME_WORLD_SIGNING_ARGUMENT_SOURCE", "attestation_private_key" not in inspect.signature(IndependentSourceVerifier.verify).parameters)
    check("NO_RUNTIME_WORLD_SIGNING_ARGUMENT_CLAIM", "attestation_private_key" not in inspect.signature(IndependentClaimVerifier.verify).parameters)
    check("NO_RUNTIME_WORLD_SIGNING_ARGUMENT_ARTIFACT", "attestation_private_key" not in inspect.signature(IndependentArtifactVerifier.verify).parameters)
    check("CONTRACT_REQUIRES_EXTERNAL_WORLD_SERVICE", contract["world_trust_configuration"]["external_independent_verifier_service_required"] is True)

    # Fake plausible receipt: correct-looking schema/digest fields but no valid attestation.
    fake = {
        "schema": SOURCE_RECEIPT_SCHEMA, "owner_id": SOURCE_VERIFIER_OWNER_ID,
        "proposer_owner": PHARMA_OWNER, "resolver_owner": "EXTERNAL-WEB-RESOLVER",
        "identifier_type": "PMID", "declared_identifier": "99999999", "resolved_identifier": "99999999",
        "resolved_url": "https://pubmed.ncbi.nlm.nih.gov/99999999/", "title": "Plausible fabricated paper",
        "container": "text/html", "retrieved_at": "2026-08-28", "retrieval_method": "LIVE_EXTERNAL_RESOLUTION",
        "content_digest": "0" * 64, "checks": {}, "verified": True, "status": "VERIFIED_EXTERNAL_SOURCE",
    }
    fake["source_verification_digest"] = digest_payload(fake)
    fake["source_receipt_id"] = "SVR-" + fake["source_verification_digest"][:24].upper()
    check("PLAUSIBLE_UNSIGNED_FAKE_PMID_REJECTED", not IndependentSourceVerifier.receipt_valid(fake))
    fake_doi = dict(fake)
    fake_doi.update({
        "identifier_type": "DOI", "declared_identifier": "10.9999/fabricated.2026.001",
        "resolved_identifier": "10.9999/fabricated.2026.001",
        "resolved_url": "https://doi.org/10.9999/fabricated.2026.001",
    })
    fake_doi.pop("source_receipt_id", None); fake_doi.pop("source_verification_digest", None)
    fake_doi["source_verification_digest"] = digest_payload(fake_doi)
    fake_doi["source_receipt_id"] = "SVR-" + fake_doi["source_verification_digest"][:24].upper()
    check("PLAUSIBLE_UNSIGNED_FAKE_DOI_REJECTED", not IndependentSourceVerifier.receipt_valid(fake_doi))

    # Qualification fixture can test the engine, but can never authorize world truth.
    fake_q = _source("99999999", PHARMA_OWNER, "fabricated qualification fixture")
    fake_claim = build_qualification_claim_receipt(
        fake_q, claim_field="causal_support", claim_value="SUPPORTED", relation="SUPPORTS",
        claim_text="fixture claim", fact_summary="fixture fact", proposer_owner=PHARMA_OWNER,
    )
    fake_ident = _target_identity(fake_q, PHARMA_OWNER, "FAKE-TARGET")
    fake_bundle = {
        "proposer_owner": PHARMA_OWNER, "evidence_class": "EXTERNAL_SOURCE",
        "claim_values": {"causal_support": "SUPPORTED"}, "source_receipts": [fake_q],
        "claim_receipts": [fake_claim, fake_ident],
        "entities": [{"entity_slot":"target","resolution_status":"ESTABLISHED_EXTERNAL","canonical_identifier":"FAKE-TARGET","identity_claim_receipt_ids":[fake_ident["claim_receipt_id"]]}],
        "minimum_distinct_sources": 1,
    }
    fake_result = core.verify_bundle(fake_bundle, required_entity_slots=("target",), allowed_entity_states={"target":("ESTABLISHED_EXTERNAL",)})
    check("QUALIFICATION_FIXTURE_ENGINE_ONLY_NOT_WORLD", fake_result["evidence_ready_for_domain"] and not fake_result["scientific_candidate_allowed"], fake_result["overall_status"])

    tampered = dict(fake_q); tampered["title"] = "tampered after signing"
    check("TAMPERED_SIGNATURE_REJECTED", not IndependentSourceVerifier.receipt_valid(tampered))

    # NLRP3 AMBIGUOUS requires both signed relations to the exact field value.
    two_bundle, two_evidence = _bundle_for_nlrp3(include_negative=True)
    two = core.verify_bundle(two_bundle, required_entity_slots=("target",), allowed_entity_states={"target":("ESTABLISHED_EXTERNAL",)})
    check("NLRP3_AMBIGUOUS_TWO_SIDED_SOURCE_LOCK_ENGINE_PASS", two["field_results"]["causal_support"]["source_lock_pass"] and two["evidence_ready_for_domain"])
    one_bundle, _ = _bundle_for_nlrp3(include_negative=False)
    one = core.verify_bundle(one_bundle, required_entity_slots=("target",), allowed_entity_states={"target":("ESTABLISHED_EXTERNAL",)})
    check("AMBIGUOUS_WITHOUT_CONTRADICTION_REJECTED", not one["field_results"]["causal_support"]["source_lock_pass"] and not one["evidence_ready_for_domain"])

    mismatch_bundle, _ = _bundle_for_nlrp3(include_negative=True, declared_value="SUPPORTED")
    # Re-declare a different value without changing signed claim receipts.
    mismatch_bundle["claim_values"]["causal_support"] = "AMBIGUOUS"
    mismatch = core.verify_bundle(mismatch_bundle, required_entity_slots=("target",), allowed_entity_states={"target":("ESTABLISHED_EXTERNAL",)})
    check("CLAIM_VALUE_MISMATCH_REJECTED", "causal_support" in mismatch["source_lock_failures"])

    # ZTRB-19: no authenticated entity identity => hard fail before domain evidence can retain it.
    z = PharmaceuticalDomainOwner().assess_hypothesis(
        {"target":"ZTRB-19","modality":"PROTAC","route":"inhaled","localization":"nanoparticle","indication":"solid tumors"},
        {}, {},
    )
    check("ZTRB19_UNRESOLVED_TARGET_REJECTED", z["gates"]["SCIENTIFIC_VERIFICATION"]["status"] == "FAIL" and not z["retained_for_research"], z["overall_status"])

    # Serialized receipt alone is not an authorization token.
    serialized = core.verify_bundle(two_bundle, required_entity_slots=("target",), allowed_entity_states={"target":("ESTABLISHED_EXTERNAL",)})
    z_receipt_only = PharmaceuticalDomainOwner().assess_hypothesis(
        {"target":"NLRP3","modality":"small-molecule inhibitor","route":"oral","localization":"systemic","indication":"MASH"},
        {"causal_support":"AMBIGUOUS", "_scientific_verification_receipt": serialized},
    )
    check("SERIALIZED_VERIFICATION_RECEIPT_NOT_AUTHORIZATION", z_receipt_only["gates"]["SCIENTIFIC_VERIFICATION"]["status"] == "FAIL")

    # Raw title/provenance records can no longer canonicalize an axis.
    proposal = DynamicAxisProposal(
        proposal_id="V8-RAW-SOURCE-CANARY", domain_id="pharmaceutical", axis_id="v8_raw_source_canary",
        description_ru="qualification canary", value_kind="CONTINUOUS_RANGE",
        physical_or_information_meaning="canary", measurement_protocol="canary", units_or_normalization="1",
        expected_range={"minimum":0.0,"maximum":1.0}, falsifiable_advantage="canary", redundancy_test="canary",
        allowed_values=(), provenance_evidence=(),
    )
    validation = {
        "promotion_route":"SOURCE_ESTABLISHED", "semantic_class":"INDEPENDENT_MEASURAND",
        "postfreeze_redundancy_status":"NO_REGISTERED_AXIS_EQUIVALENT", "falsification_protocol":"canary",
        "independent_measurement_or_calibration":True, "source_relevance_supported":True,
        "source_records":[
            {"title":"fake A","provenance":"fake","authority":"PEER_REVIEWED"},
            {"title":"fake B","provenance":"fake","authority":"REGULATORY"},
        ],
    }
    with tempfile.TemporaryDirectory() as tmp:
        pr = DynamicAxisPromotionOwner(Path(tmp)).evaluate_and_promote(proposal, validation, mutate=False, registry_path=Path(tmp)/"axes.json")
    check("DYNAMIC_AXIS_RAW_STRING_PROVENANCE_BLOCKED", not pr["qualified"] and not pr["gates"]["CENTRAL_SCIENTIFIC_VERIFICATION_PASS"])

    # Positive deployment simulation for the exact trust separation requested by
    # the v8 architecture: the WORLD SOURCE signer is the external resolver actor,
    # the WORLD CLAIM signer is a distinct independent reviewer actor, and neither
    # is the evidence proposer. The private keys exist only in this harness.
    with tempfile.TemporaryDirectory() as td_world:
        td_world_path = Path(td_world)
        src_private = Ed25519PrivateKey.generate(); claim_private = Ed25519PrivateKey.generate()
        b64 = __import__("base64")
        src_public = b64.b64encode(src_private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode("ascii")
        claim_public = b64.b64encode(claim_private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode("ascii")
        resolver_owner = "DEPLOYMENT-EXTERNAL-SOURCE-RESOLVER"
        reviewer_owner = "DEPLOYMENT-INDEPENDENT-CLAIM-REVIEWER"
        trust_path_world = td_world_path / "trust.json"
        trust_path_world.write_text(json.dumps({
            "schema": TRUST_STORE_SCHEMA, "keys": {
                "deployment-world-source-key": {
                    "public_key_b64": src_public, "trust_tier": "WORLD", "roles": ["SOURCE"],
                    "authorized_owners": [resolver_owner, "OTHER-AUTHORIZED-SOURCE-ACTOR"],
                    "private_key_shipped": False, "external_service_required": True,
                },
                "deployment-world-claim-key": {
                    "public_key_b64": claim_public, "trust_tier": "WORLD", "roles": ["CLAIM"],
                    "authorized_owners": [reviewer_owner],
                    "private_key_shipped": False, "external_service_required": True,
                },
            }
        }), encoding="utf-8")
        proposer = PHARMA_OWNER
        source_text = b"deployment simulation source content: target X causally supports phenotype Y"
        resolution = {
            "identifier_type":"DOI", "declared_identifier":"10.0000/deployment.sim",
            "resolved_identifier":"10.0000/deployment.sim", "source_exists":True,
            "bibliographic_match":True, "title":"Deployment simulation source",
            "resolved_url":"https://example.invalid/deployment.sim", "retrieved_at":"DEPLOYMENT_SIMULATION",
            "retrieval_method":"LIVE_EXTERNAL_RESOLUTION", "resolver_owner":resolver_owner,
            "content_digest":__import__("hashlib").sha256(source_text).hexdigest(), "container":"text/plain",
        }
        # Provision the independently supplied WORLD public keys before either
        # source or claim attestation is consumed.  IndependentClaimVerifier.verify()
        # revalidates the signed source receipt, so delaying trust-store provisioning
        # until verify_bundle() would incorrectly fail closed in the harness.
        old_env_world=os.environ.get("PHI_SCIENTIFIC_VERIFIER_TRUST_STORE_PATH")
        os.environ["PHI_SCIENTIFIC_VERIFIER_TRUST_STORE_PATH"]=str(trust_path_world)
        try:
            unsigned_src = IndependentSourceVerifier(trusted_resolver_owners=[resolver_owner]).verify(resolution, proposer_owner=proposer)
            src_body=dict(unsigned_src); src_body.pop("source_receipt_id",None)
            signed_src=_attest_receipt(src_body,digest_key="source_verification_digest",private_key=src_private,key_id="deployment-world-source-key",attestation_owner=resolver_owner)
            signed_src["source_receipt_id"]="SVR-"+signed_src["source_verification_digest"][:24].upper()
            review={
                "reviewer_owner":reviewer_owner,"relation":"SUPPORTS","review_method":"INDEPENDENT_MANUAL_REVIEW",
                "claim_field":"causal_support","claim_value":"SUPPORTED",
                "claim_text":"target X supports phenotype Y","fact_summary":"deployment simulation fact",
                "locator":"simulation:1","quote_or_paraphrase":"source states causal support",
                "entailment_verified":True,"source_content_digest":resolution["content_digest"],
            }
            unsigned_claim=IndependentClaimVerifier(trusted_reviewer_owners=[reviewer_owner]).verify(signed_src,review,proposer_owner=proposer)
            claim_body=dict(unsigned_claim); claim_body.pop("claim_receipt_id",None)
            signed_claim=_attest_receipt(claim_body,digest_key="claim_verification_digest",private_key=claim_private,key_id="deployment-world-claim-key",attestation_owner=reviewer_owner)
            signed_claim["claim_receipt_id"]="CVR-"+signed_claim["claim_verification_digest"][:24].upper()
            world_bundle={
                "proposer_owner":proposer,"evidence_class":"EXTERNAL_SOURCE",
                "claim_values":{"causal_support":"SUPPORTED"},
                "source_receipts":[signed_src],"claim_receipts":[signed_claim],"minimum_distinct_sources":1,
            }
            world_result=ScientificVerificationCore().verify_bundle(world_bundle)
            signer_mismatch=dict(signed_src); signer_mismatch["attestation_owner"]="OTHER-AUTHORIZED-SOURCE-ACTOR"
            mismatch_body=dict(signer_mismatch); mismatch_body.pop("source_receipt_id",None); mismatch_body.pop("attestation_signature",None)
            signer_mismatch=_attest_receipt(mismatch_body,digest_key="source_verification_digest",private_key=src_private,key_id="deployment-world-source-key",attestation_owner="OTHER-AUTHORIZED-SOURCE-ACTOR")
            signer_mismatch["source_receipt_id"]="SVR-"+signer_mismatch["source_verification_digest"][:24].upper()
            signer_mismatch_rejected=not IndependentSourceVerifier.receipt_valid(signer_mismatch,require_world_attestation=True)
        finally:
            if old_env_world is None: os.environ.pop("PHI_SCIENTIFIC_VERIFIER_TRUST_STORE_PATH",None)
            else: os.environ["PHI_SCIENTIFIC_VERIFIER_TRUST_STORE_PATH"]=old_env_world
        check("EXTERNAL_WORLD_SOURCE_AND_CLAIM_ACTORS_CAN_AUTHORIZE_DEPLOYMENT_PATH", world_result["scientific_candidate_allowed"] is True and world_result["world_attestation_ready"] is True, world_result["overall_status"])
        check("WORLD_SOURCE_SIGNER_MUST_EQUAL_DECLARED_RESOLVER_ACTOR", signer_mismatch_rejected)
        check("WORLD_SOURCE_AND_CLAIM_KEYS_ARE_DISTINCT", signed_src["attestation_key_id"] != signed_claim["attestation_key_id"])

    # Positive deployment simulation: an externally provisioned WORLD artifact key
    # can unlock a model-discovered axis in an isolated registry.  The private key
    # exists only in this qualification harness; it is not written into the release
    # and does not validate any world scientific claim.
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        private = Ed25519PrivateKey.generate()
        public_b64 = __import__("base64").b64encode(
            private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        ).decode("ascii")
        trust_path = td_path / "trust.json"
        trust_path.write_text(json.dumps({
            "schema": TRUST_STORE_SCHEMA,
            "keys": {
                "deployment-sim-artifact-key": {
                    "public_key_b64": public_b64, "trust_tier": "WORLD", "roles": ["ARTIFACT"],
                    "authorized_owners": [ARTIFACT_VERIFIER_OWNER_ID], "private_key_shipped": False,
                    "external_service_required": True, "purpose": "QUALIFICATION_DEPLOYMENT_SIMULATION_ONLY",
                }
            },
        }), encoding="utf-8")
        proposer_owner = "DYNAMIC-AXIS-PROMOTION/8.0.0"
        content = {"dataset":"independent hidden-axis deployment simulation", "n":120}
        artifact = {
            "artifact_id":"dynamic_axis_measurement", "artifact_class":"INTERNAL_MEASUREMENT",
            "producer_owner":"INDEPENDENT-MEASUREMENT-PRODUCER", "verifier_owner":ARTIFACT_VERIFIER_OWNER_ID,
            "content_digest":content_addressed_digest(content), "provenance":"DEPLOYMENT_SIMULATION",
            "independent_from_candidate_fit":True,
        }
        unsigned = IndependentArtifactVerifier().verify(artifact, proposer_owner=proposer_owner)
        body = dict(unsigned); body.pop("artifact_receipt_id", None)
        signed = _attest_receipt(
            body, digest_key="artifact_verification_digest", private_key=private,
            key_id="deployment-sim-artifact-key", attestation_owner=ARTIFACT_VERIFIER_OWNER_ID,
        )
        signed["artifact_receipt_id"] = "AVR-" + signed["artifact_verification_digest"][:24].upper()
        bundle = {
            "proposer_owner":proposer_owner, "evidence_class":"INTERNAL_MEASUREMENT",
            "claim_values":{}, "source_receipts":[], "claim_receipts":[],
            "artifact_receipts":[signed], "required_artifact_ids":["dynamic_axis_measurement"],
        }
        axis2 = DynamicAxisProposal(
            proposal_id="V8-DEPLOYMENT-SIM", domain_id="physics", axis_id="v8_deployment_sim_axis",
            description_ru="deployment simulation axis", value_kind="CONTINUOUS_RANGE",
            physical_or_information_meaning="qualification only", measurement_protocol="independent simulated measurement",
            units_or_normalization="1", expected_range={"minimum":0.0,"maximum":1.0},
            falsifiable_advantage="must improve OOD", redundancy_test="no existing equivalent",
            allowed_values=(), provenance_evidence=("DEPLOYMENT_SIMULATION",),
        )
        validation2 = {
            "promotion_route":"MODEL_DISCOVERED", "semantic_class":"DERIVED_COORDINATE",
            "postfreeze_redundancy_status":"NO_REGISTERED_AXIS_EQUIVALENT",
            "falsification_protocol":"predeclared", "measurement_uncertainty_declared":True,
            "identifiability_pass":True, "ood_pass":True, "ood_fractional_improvement":0.2,
            "complexity_penalized_delta_log_likelihood":5.0, "independent_replication":True,
            "replication_provenance":"independent simulated replicate", "falsification_status":"SURVIVED",
            "derivation":"qualification derived coordinate", "independent_measurement_or_calibration":False,
            "scientific_verification_bundle":bundle,
        }
        old_env = os.environ.get("PHI_SCIENTIFIC_VERIFIER_TRUST_STORE_PATH")
        os.environ["PHI_SCIENTIFIC_VERIFIER_TRUST_STORE_PATH"] = str(trust_path)
        try:
            promoted = DynamicAxisPromotionOwner(td_path).evaluate_and_promote(
                axis2, validation2, mutate=True, registry_path=td_path/"axes.json"
            )
        finally:
            if old_env is None:
                os.environ.pop("PHI_SCIENTIFIC_VERIFIER_TRUST_STORE_PATH", None)
            else:
                os.environ["PHI_SCIENTIFIC_VERIFIER_TRUST_STORE_PATH"] = old_env
            reload_dynamic_axis_registry()
        check("EXTERNALLY_PROVISIONED_WORLD_ARTIFACT_PATH_CAN_MUTATE_ISOLATED_REGISTRY",
              promoted["status"] == "PROMOTED_CANONICAL_DYNAMIC_AXIS" and promoted["scientific_verification"]["world_attestation_ready"] is True,
              promoted["status"])

    # Legacy dossier evidence remains audit-only, not active scientific evidence.
    pd = ParticleCandidateDossierOwner().attach_postfreeze_evidence({"P-001":{"postfreeze_status":"CLAIMED","world_novelty_status":"CLAIMED","experimental_recast":{"status":"CLAIMED"}}})
    p1 = pd["dossiers"][0]
    check("PARTICLE_DOSSIER_RAW_EVIDENCE_FAILS_CLOSED", p1["postfreeze_status"] == "UNVERIFIED_EVIDENCE_REJECTED" and p1["promotion_allowed"] is False)

    passed = sum(int(c["pass"]) for c in checks)
    payload = {
        "schema":"phi-scientific-verification-qualification/v8.0",
        "owner_id":VERIFICATION_OWNER,
        "checks":checks, "passed":passed, "total":len(checks),
        "status":"PASS_SCIENTIFIC_VERIFICATION_CORE_V8" if passed == len(checks) else "FAIL_SCIENTIFIC_VERIFICATION_CORE_V8",
        "world_trust_store_default_key_count":len(world_keys),
        "claim_boundary":{
            "qualification_fixture_is_world_evidence":False,
            "world_scientific_promotion_available_without_external_verifier_configuration":False,
            "cryptographic_signature_alone_proves_claim_truth":False,
        },
    }
    payload["digest"] = digest_payload(payload)
    if root is not None:
        root = Path(root); (root/"reports").mkdir(parents=True, exist_ok=True)
        (root/"reports"/"scientific_verification_qualification_v8_0.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    return payload

if __name__ == "__main__":
    print(json.dumps(run_release_qualification(Path(__file__).resolve().parents[1]), ensure_ascii=False, indent=2, sort_keys=True))
