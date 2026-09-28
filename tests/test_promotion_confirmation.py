from source.lawspace.promotion_confirmation import AUTHORIZATION_STATEMENT, HumanGatedPromotionAuthorizationOwner


class Core:
    def __init__(self, allowed=True): self.allowed = allowed
    def evaluate(self, request):
        return {
            "RECEIPT_ID": "SPR-X",
            "OUTPUT_HASH": "f" * 64,
            "PROMOTION_ALLOWED": self.allowed,
            "FINAL_STATUS": "LAW_CANDIDATE" if self.allowed else "REPLICATED",
            "TERMINAL_REASON": "TEST",
            "scientific_verification": {"verification_digest": "e" * 64},
        }


def test_bad_digest_blocks_confirmation():
    owner = HumanGatedPromotionAuthorizationOwner(promotion_core=Core(True))
    out = owner.confirm({}, qualification_digest="deadbeef", human_attestation={})
    assert out["authorized"] is False
    assert out["mutation_performed"] is False


def test_attestation_must_bind_qualification_and_evidence():
    owner = HumanGatedPromotionAuthorizationOwner(promotion_core=Core(True))
    q = owner.qualify({})
    att = {
        "attestor_id": "HUMAN-1",
        "authorization_type": "CANONICAL_REGISTRATION_AUTHORIZATION",
        "authorization_scope": "SCIENTIFIC_LAW_PROMOTION",
        "qualification_digest": q["digest"],
        "promotion_receipt_hash": q["promotion_receipt_hash"],
        "evidence_digest": q["verification_digest"],
        "explicit_statement": AUTHORIZATION_STATEMENT,
        "timestamp": "2026-09-28T20:00:00+03:00",
    }
    out = owner.confirm({}, qualification_digest=q["digest"], human_attestation=att)
    assert out["authorized"] is True
    assert out["mutation_performed"] is False
    assert out["claim_boundary"]["human_confirmation_is_scientific_evidence"] is False


def test_unqualified_core_cannot_be_human_overridden():
    owner = HumanGatedPromotionAuthorizationOwner(promotion_core=Core(False))
    q = owner.qualify({})
    assert q["qualified"] is False


def test_generic_canonical_authorization_is_digest_bound():
    from source.lawspace.promotion_confirmation import issue_canonical_mutation_authorization, validate_canonical_mutation_authorization
    qd = "q" * 64
    ed = "e" * 64
    att = {
        "attestor_id": "HUMAN-1",
        "authorization_type": "CANONICAL_REGISTRATION_AUTHORIZATION",
        "authorization_scope": "DYNAMIC_AXIS_CANONICALIZATION",
        "qualification_digest": qd,
        "evidence_digest": ed,
        "explicit_statement": AUTHORIZATION_STATEMENT,
        "timestamp": "2026-09-28T20:00:00+03:00",
    }
    receipt = issue_canonical_mutation_authorization(
        scope="DYNAMIC_AXIS_CANONICALIZATION",
        qualification_digest=qd,
        evidence_digest=ed,
        human_attestation=att,
    )
    assert receipt["authorized"] is True
    assert validate_canonical_mutation_authorization(
        receipt,
        scope="DYNAMIC_AXIS_CANONICALIZATION",
        qualification_digest=qd,
        evidence_digest=ed,
    ) is True
    assert validate_canonical_mutation_authorization(
        receipt,
        scope="DYNAMIC_AXIS_CANONICALIZATION",
        qualification_digest="wrong",
        evidence_digest=ed,
    ) is False
