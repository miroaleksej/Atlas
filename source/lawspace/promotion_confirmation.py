"""Digest-bound human authorization after ScientificPromotionCore qualification.

This module does not create a second promotion engine and never mutates a
registry.  It reruns the existing ScientificPromotionCore, verifies that the
same immutable promotion receipt is still eligible, and emits an authorization
receipt that a canonical mutation owner may consume after rechecking its own
policy/gates.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from .execution_policy import load_execution_policy, require_action
from .schema import digest_payload

OWNER_ID = "HUMAN-GATED-PROMOTION-AUTHORIZATION/1.2.0"
SCHEMA = "phi-human-gated-promotion-authorization/v1.2"
AUTHORIZATION_STATEMENT = "I authorize canonical registration; this authorization is not scientific evidence and does not itself establish a new natural law."


def _with_digest(payload: dict[str, Any]) -> dict[str, Any]:
    payload["digest"] = digest_payload({k: v for k, v in payload.items() if k != "digest"})
    return payload


def issue_canonical_mutation_authorization(
    *,
    scope: str,
    qualification_digest: str,
    evidence_digest: str,
    human_attestation: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Issue a non-mutating authorization bound to one exact dry-run receipt."""
    scope = str(scope).upper().strip()
    att = dict(human_attestation or {})
    checks = {
        "SCOPE_SUPPORTED": scope in {"DYNAMIC_AXIS_CANONICALIZATION", "SCIENTIFIC_LAW_PROMOTION"},
        "ATTESTOR_ID_DECLARED": bool(str(att.get("attestor_id", "")).strip()),
        "AUTHORIZATION_TYPE_CORRECT": str(att.get("authorization_type", "")).strip().upper() == "CANONICAL_REGISTRATION_AUTHORIZATION",
        "AUTHORIZATION_SCOPE_BOUND": str(att.get("authorization_scope", "")).strip().upper() == scope,
        "QUALIFICATION_DIGEST_BOUND": str(att.get("qualification_digest", "")).strip() == str(qualification_digest),
        "EVIDENCE_DIGEST_BOUND": str(att.get("evidence_digest", "")).strip() == str(evidence_digest) and bool(str(evidence_digest).strip()),
        "EXPLICIT_STATEMENT_CORRECT": str(att.get("explicit_statement", "")).strip() == AUTHORIZATION_STATEMENT,
        "TIMESTAMP_DECLARED": bool(str(att.get("timestamp", "")).strip()),
    }
    authorized = all(checks.values())
    payload = {
        "schema": "phi-canonical-mutation-authorization/v1",
        "owner_id": OWNER_ID,
        "scope": scope,
        "status": "CANONICAL_MUTATION_AUTHORIZED" if authorized else "BLOCKED_MISSING_OR_UNBOUND_HUMAN_ATTESTATION",
        "authorized": authorized,
        "qualification_digest": str(qualification_digest),
        "evidence_digest": str(evidence_digest),
        "attestation_checks": checks,
        "human_attestation": att if authorized else {},
        "mutation_performed": False,
        "claim_boundary": {
            "human_confirmation_is_scientific_evidence": False,
            "authorization_receipt_is_scientific_law": False,
            "canonical_registry_mutated": False,
        },
    }
    return _with_digest(payload)


def validate_canonical_mutation_authorization(
    receipt: Mapping[str, Any] | None,
    *,
    scope: str,
    qualification_digest: str,
    evidence_digest: str,
) -> bool:
    if not isinstance(receipt, Mapping):
        return False
    body = dict(receipt)
    digest = str(body.pop("digest", ""))
    if digest != digest_payload(body):
        return False
    return bool(
        receipt.get("schema") == "phi-canonical-mutation-authorization/v1"
        and receipt.get("owner_id") == OWNER_ID
        and receipt.get("authorized") is True
        and str(receipt.get("scope", "")).upper() == str(scope).upper()
        and str(receipt.get("qualification_digest", "")) == str(qualification_digest)
        and str(receipt.get("evidence_digest", "")) == str(evidence_digest)
        and receipt.get("mutation_performed") is False
    )


def validate_scientific_law_authorization(
    receipt: Mapping[str, Any] | None,
    *,
    promotion_receipt_hash: str,
    evidence_digest: str,
) -> bool:
    """Validate the human authorization consumed by the canonical LAW transaction."""
    if not isinstance(receipt, Mapping):
        return False
    body = dict(receipt)
    embedded = str(body.pop("digest", ""))
    if not embedded or embedded != digest_payload(body):
        return False
    return bool(
        receipt.get("schema") == SCHEMA
        and receipt.get("owner_id") == OWNER_ID
        and receipt.get("authorized") is True
        and receipt.get("status") == "PROMOTION_MUTATION_AUTHORIZED"
        and str(receipt.get("authorization_scope", "")).upper() == "SCIENTIFIC_LAW_PROMOTION"
        and str(receipt.get("promotion_receipt_hash", "")) == str(promotion_receipt_hash)
        and str(receipt.get("verification_digest", "")) == str(evidence_digest)
        and bool(str(evidence_digest).strip())
        and receipt.get("mutation_performed") is False
    )


class HumanGatedPromotionAuthorizationOwner:
    owner_id = OWNER_ID

    def __init__(
        self,
        root: str | Path | None = None,
        *,
        trusted_evidence_owners: Sequence[str] = (),
        promotion_core: Any | None = None,
    ) -> None:
        self.root = Path(root) if root is not None else None
        if promotion_core is None:
            from .scientific_promotion import ScientificPromotionCore
            promotion_core = ScientificPromotionCore(trusted_evidence_owners=tuple(trusted_evidence_owners))
        self.core = promotion_core

    def _policy(self) -> Mapping[str, Any]:
        if self.root is None:
            return {
                "automatic_scientific_law_promotion": False,
                "automatic_research_triage": True,
                "automatic_u5_attempts": True,
                "human_gated_promotion": True,
                "engineering_model_acceptance": True,
                "engineering_model_ledger": True,
                "automatic_discriminating_experiment_design": True,
                "canonical_law_transaction": True,
                "canonical_law_transaction_requires_current_gate_replay": True,
                "sandbox_profiles_allowed": ["STRICT", "RESEARCH", "WIDE"],
                "u5_attempt_writes_canonical_registry": False,
                "discriminating_experiment_may_auto_promote": False,
                "human_confirmation_is_scientific_evidence": False,
                "engineering_acceptance_is_scientific_law": False,
            }
        return load_execution_policy(self.root)

    @staticmethod
    def _receipt_hash(evaluation: Mapping[str, Any]) -> str:
        value = str(evaluation.get("OUTPUT_HASH", "")).strip()
        return value if value else digest_payload(dict(evaluation))

    def qualify(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        require_action(self._policy(), "HUMAN_GATED_PROMOTION")
        evaluation = dict(self.core.evaluate(dict(request)))
        allowed = evaluation.get("PROMOTION_ALLOWED") is True
        receipt_hash = self._receipt_hash(evaluation)
        payload = {
            "schema": SCHEMA,
            "owner_id": self.owner_id,
            "status": "AWAITING_HUMAN_CONFIRMATION" if allowed else "BLOCKED",
            "qualified": allowed,
            "promotion_receipt_id": evaluation.get("RECEIPT_ID"),
            "promotion_receipt_hash": receipt_hash,
            "final_status": evaluation.get("FINAL_STATUS"),
            "terminal_reason": evaluation.get("TERMINAL_REASON"),
            "verification_digest": dict(evaluation.get("scientific_verification") or {}).get("verification_digest"),
            "mutation_performed": False,
            "auto_promote": False,
            "claim_boundary": {
                "human_confirmation_is_scientific_evidence": False,
                "human_confirmation_establishes_world_novelty": False,
                "authorization_receipt_is_registry_mutation": False,
                "scientific_promotion_core_remains_authoritative": True,
            },
        }
        return _with_digest(payload)

    def confirm(
        self,
        request: Mapping[str, Any],
        *,
        qualification_digest: str,
        human_attestation: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        require_action(self._policy(), "HUMAN_GATED_PROMOTION")
        replay = dict(self.qualify(request))
        if replay.get("digest") != str(qualification_digest):
            return _with_digest({
                "schema": SCHEMA, "owner_id": self.owner_id,
                "status": "BLOCKED_QUALIFICATION_DIGEST_MISMATCH",
                "authorized": False, "mutation_performed": False,
                "expected_qualification_digest": replay.get("digest"),
            })
        if replay.get("qualified") is not True:
            return _with_digest({
                "schema": SCHEMA, "owner_id": self.owner_id,
                "status": "BLOCKED_PROMOTION_NOT_QUALIFIED",
                "authorized": False, "mutation_performed": False,
                "promotion_receipt_hash": replay.get("promotion_receipt_hash"),
            })

        att = dict(human_attestation or {})
        checks = {
            "ATTESTOR_ID_DECLARED": bool(str(att.get("attestor_id", "")).strip()),
            "AUTHORIZATION_TYPE_CORRECT": str(att.get("authorization_type", "")).strip().upper() == "CANONICAL_REGISTRATION_AUTHORIZATION",
            "AUTHORIZATION_SCOPE_BOUND": str(att.get("authorization_scope", "")).strip().upper() == "SCIENTIFIC_LAW_PROMOTION",
            "QUALIFICATION_DIGEST_BOUND": str(att.get("qualification_digest", "")).strip() == str(qualification_digest),
            "PROMOTION_RECEIPT_HASH_BOUND": str(att.get("promotion_receipt_hash", "")).strip() == str(replay.get("promotion_receipt_hash", "")),
            "EVIDENCE_DIGEST_BOUND": str(att.get("evidence_digest", "")).strip() == str(replay.get("verification_digest", "")) and bool(str(replay.get("verification_digest", "")).strip()),
            "EXPLICIT_STATEMENT_CORRECT": str(att.get("explicit_statement", "")).strip() == AUTHORIZATION_STATEMENT,
            "TIMESTAMP_DECLARED": bool(str(att.get("timestamp", "")).strip()),
        }
        if not all(checks.values()):
            return _with_digest({
                "schema": SCHEMA, "owner_id": self.owner_id,
                "status": "BLOCKED_MISSING_OR_UNBOUND_HUMAN_ATTESTATION",
                "authorized": False,
                "attestation_checks": checks,
                "mutation_performed": False,
            })

        payload = {
            "schema": SCHEMA,
            "owner_id": self.owner_id,
            "status": "PROMOTION_MUTATION_AUTHORIZED",
            "authorized": True,
            "authorization_scope": "SCIENTIFIC_LAW_PROMOTION",
            "qualification_digest": qualification_digest,
            "promotion_receipt_hash": replay["promotion_receipt_hash"],
            "promotion_receipt_id": replay.get("promotion_receipt_id"),
            "verification_digest": replay.get("verification_digest"),
            "human_attestation": att,
            "human_attestation_digest": digest_payload(att),
            "mutation_performed": False,
            "next_action": "canonical promotion owner must revalidate this authorization and its own current gates before any mutation",
            "claim_boundary": {
                "human_confirmation_is_scientific_evidence": False,
                "authorization_receipt_is_scientific_law": False,
                "authorization_receipt_establishes_world_novelty": False,
                "scientific_promotion_core_remains_authoritative": True,
                "canonical_registry_mutated": False,
            },
        }
        return _with_digest(payload)
