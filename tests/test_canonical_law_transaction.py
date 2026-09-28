import dataclasses
import json
from pathlib import Path

from source.lawspace.canonical_law_transaction import CanonicalLawRegistryTransactionOwner
from source.lawspace.promotion_confirmation import AUTHORIZATION_STATEMENT, HumanGatedPromotionAuthorizationOwner
from source.lawspace.runtime import passport_from_persisted
from source.lawspace.scientific_promotion import _digest


def _promotion_receipt():
    row = {
        "RECEIPT_ID": "SPR-PENDING",
        "CANDIDATES": ["TEST-CANDIDATE"],
        "PROMOTION_ALLOWED": True,
        "FINAL_STATUS": "LAW_CANDIDATE",
        "TERMINAL_REASON": "ALL_GATES_PASS_WITH_WORLD_VERIFIED_EVIDENCE",
        "scientific_verification": {"verification_digest": "e" * 64},
        "OUTPUT_HASH": "",
    }
    row["OUTPUT_HASH"] = _digest({k: v for k, v in row.items() if k not in {"OUTPUT_HASH", "RECEIPT_ID"}})
    row["RECEIPT_ID"] = "SPR-" + row["OUTPUT_HASH"][:24].upper()
    return row


class Core:
    def __init__(self, receipt): self.receipt = dict(receipt)
    def evaluate(self, request): return dict(self.receipt)


def _base_passport_payload(auth, receipt):
    source = Path("data/passports/known_laws.jsonl")
    first = json.loads(next(line for line in source.read_text(encoding="utf-8").splitlines() if line.strip()))
    base = passport_from_persisted(first)
    provenance = {
        "candidate_id": "TEST-CANDIDATE",
        "scientific_promotion_receipt_id": receipt["RECEIPT_ID"],
        "scientific_promotion_receipt_hash": receipt["OUTPUT_HASH"],
        "scientific_verification_digest": receipt["scientific_verification"]["verification_digest"],
        "human_authorization_digest": auth["digest"],
        "source_id": "QUALIFIED-HUMAN-GATED-PROMOTION",
    }
    promoted = dataclasses.replace(
        base,
        owner_id="TEST-PROMOTED-LAW-001",
        name_ru="Qualification promoted law",
        epistemic_state="ESTABLISHED_LAW",
        provenance=provenance,
        digest="",
    ).finalized()
    return dataclasses.asdict(promoted)


def _authorization(core):
    owner = HumanGatedPromotionAuthorizationOwner(promotion_core=core)
    q = owner.qualify({})
    att = {
        "attestor_id": "HUMAN-1",
        "authorization_type": "CANONICAL_REGISTRATION_AUTHORIZATION",
        "authorization_scope": "SCIENTIFIC_LAW_PROMOTION",
        "qualification_digest": q["digest"],
        "promotion_receipt_hash": q["promotion_receipt_hash"],
        "evidence_digest": q["verification_digest"],
        "explicit_statement": AUTHORIZATION_STATEMENT,
        "timestamp": "2026-09-28T21:00:00+03:00",
    }
    return owner.confirm({}, qualification_digest=q["digest"], human_attestation=att)


def test_canonical_transaction_replays_core_and_persists_known_passport(tmp_path):
    receipt = _promotion_receipt()
    core = Core(receipt)
    auth = _authorization(core)
    assert auth["authorized"] is True
    passport = _base_passport_payload(auth, receipt)
    root = tmp_path / "atlas"
    tx = CanonicalLawRegistryTransactionOwner(root, promotion_core=core)
    dry = tx.qualify(promotion_request={}, authorization=auth, passport=passport)
    assert dry["status"] == "CANONICAL_LAW_TRANSACTION_READY"
    assert dry["mutation_performed"] is False
    assert not (root / "data/passports/known_promoted_laws.jsonl").exists()
    out = tx.commit(promotion_request={}, authorization=auth, passport=passport)
    assert out["status"] == "CANONICAL_SCIENTIFIC_LAW_REGISTERED"
    assert out["mutation_performed"] is True
    assert out["claim_boundary"]["world_novelty_established_by_transaction"] is False
    target = root / "data/passports/known_promoted_laws.jsonl"
    assert target.is_file()
    again = tx.commit(promotion_request={}, authorization=auth, passport=passport)
    assert again["status"] == "IDEMPOTENT_CANONICAL_LAW_ALREADY_REGISTERED"


def test_stale_authorization_is_blocked(tmp_path):
    receipt = _promotion_receipt()
    core = Core(receipt)
    auth = dict(_authorization(core))
    passport = _base_passport_payload(auth, receipt)
    auth["promotion_receipt_hash"] = "0" * 64
    body = {k: v for k, v in auth.items() if k != "digest"}
    from source.lawspace.schema import digest_payload
    auth["digest"] = digest_payload(body)
    tx = CanonicalLawRegistryTransactionOwner(tmp_path / "atlas", promotion_core=core)
    out = tx.commit(promotion_request={}, authorization=auth, passport=passport)
    assert out["status"] == "BLOCKED_INVALID_OR_STALE_HUMAN_AUTHORIZATION"
    assert out["mutation_performed"] is False
