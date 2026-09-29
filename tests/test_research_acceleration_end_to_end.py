import dataclasses
import json
from pathlib import Path

from source.lawspace.canonical_law_transaction import CanonicalLawRegistryTransactionOwner
from source.lawspace.discriminating_experiment_autopilot import DiscriminatingExperimentAutopilotOwner
from source.lawspace.promotion_confirmation import AUTHORIZATION_STATEMENT, HumanGatedPromotionAuthorizationOwner
from source.lawspace.research_cycle import ScientificResearchCycleOwner
from source.lawspace.runtime import LawSpaceRuntime, passport_from_persisted
from source.lawspace.scientific_promotion import _digest
from source.lawspace.u5_attempt_scheduler import U5AttemptScheduler


class PhaseVerifier:
    def __init__(self):
        self.world_ready = False

    def verify_bundle(self, bundle):
        if self.world_ready:
            return {
                "overall_status": "PASS_SCIENTIFIC_VERIFICATION_PRECONDITION",
                "verification_digest": "e" * 64,
                "evidence_ready_for_domain": True,
                "world_attestation_ready": True,
                "scientific_candidate_allowed": True,
                "evidence_class": "EXTERNAL_SOURCE",
            }
        return {
            "overall_status": "PASS_ENGINE_OR_MODEL_VERIFICATION_WORLD_CLAIM_BLOCKED",
            "verification_digest": "a" * 64,
            "evidence_ready_for_domain": True,
            "world_attestation_ready": False,
            "scientific_candidate_allowed": False,
            "evidence_class": "INTERNAL_MEASUREMENT",
        }


class FakeExperimentKernel:
    def design(self, **kwargs):
        return {
            "status": "DISCRIMINATING_EXPERIMENT_SELECTED",
            "selection": {
                "status": "DISCRIMINATING_EXPERIMENT_SELECTED",
                "digest": "s" * 64,
                "frontier_freeze_digest": "f" * 64,
                "selected_experiment": {"experiment_id": "Q-E2E"},
                "theory_promotion_allowed": False,
            },
            "attestation_bridge": {
                "status": "WORLD_ATTESTATION_PENDING_EXTERNAL_MEASUREMENT",
                "measurement_protocol": {
                    "measurement_id": "M-E2E",
                    "experiment_id": "Q-E2E",
                    "initial_state": "S0",
                    "actions": ["A"],
                    "protocol_digest": "p" * 64,
                    "required_result_fields": ["data_digest"],
                },
            },
        }


def _promotion_receipt():
    row = {
        "RECEIPT_ID": "SPR-PENDING",
        "CANDIDATES": ["E2E-CANDIDATE"],
        "PROMOTION_ALLOWED": True,
        "FINAL_STATUS": "LAW_CANDIDATE",
        "TERMINAL_REASON": "ALL_GATES_PASS_WITH_WORLD_VERIFIED_EVIDENCE",
        "scientific_verification": {"verification_digest": "e" * 64},
        "OUTPUT_HASH": "",
    }
    row["OUTPUT_HASH"] = _digest({k: v for k, v in row.items() if k not in {"OUTPUT_HASH", "RECEIPT_ID"}})
    row["RECEIPT_ID"] = "SPR-" + row["OUTPUT_HASH"][:24].upper()
    return row


class PromotionCore:
    def __init__(self, receipt):
        self.receipt = dict(receipt)

    def evaluate(self, request):
        return dict(self.receipt)


def _u5_candidate():
    return {
        "candidate_id": "E2E-CANDIDATE",
        "scientific_verification_bundle": {"bundle": "digest-bound-controlled-attestation-stub"},
        "ood_pass": True,
        "ood_fractional_improvement": 0.1,
        "complexity_penalized_delta_log_likelihood": 1.0,
        "independent_replication": True,
        "replication_provenance": "INDEPENDENT-E2E-CONTROL",
        "falsification_protocol": "FROZEN-E2E-PROTOCOL",
        "falsification_status": "SURVIVED",
    }


def _passport_payload(auth, receipt):
    source = Path("data/passports/known_laws.jsonl")
    first = json.loads(next(line for line in source.read_text(encoding="utf-8").splitlines() if line.strip()))
    base = passport_from_persisted(first)
    promoted = dataclasses.replace(
        base,
        owner_id="E2E-PROMOTED-LAW-001",
        name_ru="E2E promoted law qualification control",
        epistemic_state="ESTABLISHED_LAW",
        provenance={
            "candidate_id": "E2E-CANDIDATE",
            "scientific_promotion_receipt_id": receipt["RECEIPT_ID"],
            "scientific_promotion_receipt_hash": receipt["OUTPUT_HASH"],
            "scientific_verification_digest": receipt["scientific_verification"]["verification_digest"],
            "human_authorization_digest": auth["digest"],
            "source_id": "RESEARCH-ACCELERATION-E2E-QUALIFICATION-CONTROL",
        },
        digest="",
    ).finalized()
    return dataclasses.asdict(promoted)


def test_integrated_progression_to_canonical_reload_and_reseal(tmp_path):
    # This is a controlled orchestration regression.  The verifier receipt models
    # the boundary after central cryptographic/world verification; it is not a
    # claim that this synthetic test generated real world evidence.
    verifier = PhaseVerifier()
    receipt = _promotion_receipt()
    core = PromotionCore(receipt)

    owner = object.__new__(ScientificResearchCycleOwner)
    owner.runtime = type("Runtime", (), {"root": tmp_path, "catalog": type("Catalog", (), {"passports": {}})()})()
    owner._u5_scheduler = U5AttemptScheduler(verifier=verifier)
    owner._experiment_autopilot = DiscriminatingExperimentAutopilotOwner(tmp_path, kernel=FakeExperimentKernel())
    owner._promotion_authorization = HumanGatedPromotionAuthorizationOwner(promotion_core=core)

    cycle = {"competitive_set": {"candidates": []}, "information_gain": {"experiments": []}}
    request = {
        "u5_candidate": _u5_candidate(),
        "candidate_theory": {"candidate_id": "E2E-CANDIDATE", "digest": "c" * 64},
        "baseline_theories": [{"candidate_id": "BASELINE", "digest": "b" * 64}],
        "discriminating_experiment_cost_budget": 2.0,
        "promotion_request": {},
    }

    pending = owner._research_acceleration_progression(question="Q", cycle=cycle, request=request)
    assert pending["status"] == "MEASUREMENT_REQUEST_READY"
    assert pending["u5_attempt"]["result"]["outcome"] == "U5_DATA_PENDING"
    assert pending["discriminating_experiment"]["measurement_request"]["world_result_observed"] is False
    assert pending["mutation_performed"] is False

    verifier.world_ready = True
    qualified = owner._research_acceleration_progression(question="Q", cycle=cycle, request=request)
    assert qualified["u5_attempt"]["result"]["outcome"] == "U5_PASS"
    assert qualified["status"] == "AWAITING_HUMAN_CONFIRMATION"
    assert qualified["promotion_qualification"]["mutation_performed"] is False
    assert qualified["claim_boundary"]["canonical_registry_mutated_by_autonomous_research"] is False

    gate = owner._promotion_authorization
    q = qualified["promotion_qualification"]
    attestation = {
        "attestor_id": "HUMAN-E2E",
        "authorization_type": "CANONICAL_REGISTRATION_AUTHORIZATION",
        "authorization_scope": "SCIENTIFIC_LAW_PROMOTION",
        "qualification_digest": q["digest"],
        "promotion_receipt_hash": q["promotion_receipt_hash"],
        "evidence_digest": q["verification_digest"],
        "explicit_statement": AUTHORIZATION_STATEMENT,
        "timestamp": "2026-09-28T23:00:00+03:00",
    }
    authorization = gate.confirm({}, qualification_digest=q["digest"], human_attestation=attestation)
    assert authorization["authorized"] is True
    assert authorization["claim_boundary"]["human_confirmation_is_scientific_evidence"] is False

    tx_root = tmp_path / "runtime-reload"
    tx = CanonicalLawRegistryTransactionOwner(tx_root, promotion_core=core)
    passport = _passport_payload(authorization, receipt)
    committed = tx.commit(promotion_request={}, authorization=authorization, passport=passport)
    assert committed["status"] == "CANONICAL_SCIENTIFIC_LAW_REGISTERED"
    assert committed["claim_boundary"]["release_reseal_required"] is True

    reloaded = LawSpaceRuntime(tx_root)
    assert "E2E-PROMOTED-LAW-001" in reloaded.catalog.passports
    assert reloaded.catalog.passports["E2E-PROMOTED-LAW-001"].digest == passport["digest"]
