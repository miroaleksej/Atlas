"""Human-gated canonical scientific-law persistence transaction.

Scientific truth qualification remains owned by ``ScientificPromotionCore``.
Canonical passport structure remains validated by ``LawCatalog``.  This owner
only performs the final persistence transaction after replaying the current
promotion gates and validating a digest-bound human authorization.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from .catalog import LawCatalog
from .execution_policy import load_execution_policy, require_action
from .promotion_confirmation import validate_scientific_law_authorization
from .runtime import passport_from_persisted
from .schema import digest_payload

OWNER_ID = "CANONICAL-LAW-REGISTRY-TRANSACTION/1.0.0"
SCHEMA = "phi-canonical-law-registry-transaction/v1"
TARGET_RELATIVE_PATH = Path("data/passports/known_promoted_laws.jsonl")


def _with_digest(payload: Mapping[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    out["digest"] = digest_payload({k: v for k, v in out.items() if k != "digest"})
    return out


class CanonicalLawRegistryTransactionOwner:
    """Persist an already-qualified law candidate; never invent promotion status."""

    owner_id = OWNER_ID

    def __init__(
        self,
        root: str | Path,
        *,
        trusted_evidence_owners: Sequence[str] = (),
        promotion_core: Any | None = None,
    ) -> None:
        self.root = Path(root)
        if promotion_core is None:
            from .scientific_promotion import ScientificPromotionCore
            promotion_core = ScientificPromotionCore(trusted_evidence_owners=tuple(trusted_evidence_owners))
        self.core = promotion_core

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner_id": self.owner_id,
            "scientific_qualification_owner": "SCIENTIFIC-PROMOTION-CORE",
            "canonical_structure_owner": "LawCatalog",
            "target": str(TARGET_RELATIVE_PATH),
            "transaction_role_only": True,
            "rerun_current_promotion_gates_before_write": True,
            "human_authorization_required": True,
            "automatic_scientific_law_promotion": False,
            "world_novelty_established_by_transaction": False,
        }
        return _with_digest(payload)

    def _policy(self) -> Mapping[str, Any]:
        return load_execution_policy(self.root)

    def _target(self) -> Path:
        return self.root / TARGET_RELATIVE_PATH

    def _existing_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for path in sorted((self.root / "data" / "passports").glob("known_*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rows.append(dict(json.loads(line)))
        return rows

    @staticmethod
    def _promotion_hash(receipt: Mapping[str, Any]) -> str:
        return str(receipt.get("OUTPUT_HASH", "")).strip()

    @staticmethod
    def _verification_digest(receipt: Mapping[str, Any]) -> str:
        return str(dict(receipt.get("scientific_verification") or {}).get("verification_digest", "")).strip()

    def _validate_passport(
        self,
        payload: Mapping[str, Any],
        *,
        replay: Mapping[str, Any],
        authorization: Mapping[str, Any],
    ) -> tuple[bool, list[str], Mapping[str, Any] | None]:
        reasons: list[str] = []
        row = dict(payload)
        try:
            passport = passport_from_persisted(row)
            finalized = passport.finalized()
        except Exception as exc:
            return False, [f"passport parse/validation failed: {exc}"], None
        if str(row.get("epistemic_state", "")) != "ESTABLISHED_LAW":
            reasons.append("passport epistemic_state must be ESTABLISHED_LAW")
        if not str(row.get("digest", "")).strip() or str(row.get("digest")) != str(finalized.digest):
            reasons.append("passport digest does not match finalized LawPassport")
        try:
            LawCatalog().add_passport(finalized)
        except Exception as exc:
            reasons.append(f"LawCatalog structural validation failed: {exc}")
        candidate_id = str((replay.get("CANDIDATES") or [""])[0])
        provenance = dict(row.get("provenance") or {})
        expected = {
            "candidate_id": candidate_id,
            "scientific_promotion_receipt_id": str(replay.get("RECEIPT_ID", "")),
            "scientific_promotion_receipt_hash": self._promotion_hash(replay),
            "scientific_verification_digest": self._verification_digest(replay),
            "human_authorization_digest": str(authorization.get("digest", "")),
        }
        for key, value in expected.items():
            if not value or str(provenance.get(key, "")) != value:
                reasons.append(f"passport provenance not bound: {key}")
        return not reasons, reasons, row

    def qualify(
        self,
        *,
        promotion_request: Mapping[str, Any],
        authorization: Mapping[str, Any],
        passport: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Dry-run the complete current transaction path without persistence."""
        require_action(self._policy(), "SCIENTIFIC_LAW_CANONICAL_MUTATION")
        replay = dict(self.core.evaluate(dict(promotion_request)))
        from .scientific_promotion import ScientificPromotionCore
        inference = dict(ScientificPromotionCore.inference_status(replay))
        promotion_hash = self._promotion_hash(replay)
        verification_digest = self._verification_digest(replay)
        current_ok = bool(
            inference.get("promotion_allowed") is True
            and replay.get("PROMOTION_ALLOWED") is True
            and str(replay.get("FINAL_STATUS", "")) == "LAW_CANDIDATE"
            and promotion_hash
            and verification_digest
        )
        if not current_ok:
            return _with_digest({
                "schema": SCHEMA, "owner_id": self.owner_id,
                "status": "BLOCKED_CURRENT_PROMOTION_GATES_NOT_PASSING",
                "qualified": False, "mutation_performed": False,
                "promotion_receipt_id": replay.get("RECEIPT_ID"),
                "promotion_receipt_hash": promotion_hash,
            })
        if not validate_scientific_law_authorization(
            authorization, promotion_receipt_hash=promotion_hash, evidence_digest=verification_digest
        ):
            return _with_digest({
                "schema": SCHEMA, "owner_id": self.owner_id,
                "status": "BLOCKED_INVALID_OR_STALE_HUMAN_AUTHORIZATION",
                "qualified": False, "mutation_performed": False,
            })
        passport_ok, reasons, row = self._validate_passport(passport, replay=replay, authorization=authorization)
        if not passport_ok or row is None:
            return _with_digest({
                "schema": SCHEMA, "owner_id": self.owner_id,
                "status": "BLOCKED_INVALID_CANONICAL_LAW_PASSPORT",
                "qualified": False, "reasons": reasons, "mutation_performed": False,
            })
        owner_id = str(row.get("owner_id", ""))
        existing = [x for x in self._existing_rows() if str(x.get("owner_id", "")) == owner_id]
        if existing and not (len(existing) == 1 and str(existing[0].get("digest", "")) == str(row.get("digest", ""))):
            return _with_digest({
                "schema": SCHEMA, "owner_id": self.owner_id,
                "status": "BLOCKED_CANONICAL_OWNER_ID_CONFLICT",
                "qualified": False, "canonical_owner_id": owner_id, "mutation_performed": False,
            })
        return _with_digest({
            "schema": SCHEMA, "owner_id": self.owner_id,
            "status": "CANONICAL_LAW_TRANSACTION_READY",
            "qualified": True,
            "idempotent_existing": bool(existing),
            "canonical_owner_id": owner_id,
            "passport_digest": row.get("digest"),
            "promotion_receipt_id": replay.get("RECEIPT_ID"),
            "promotion_receipt_hash": promotion_hash,
            "scientific_verification_digest": verification_digest,
            "human_authorization_digest": authorization.get("digest"),
            "mutation_performed": False,
            "claim_boundary": {
                "dry_run_is_registry_mutation": False,
                "scientific_promotion_core_remains_authoritative": True,
                "world_novelty_established_by_transaction": False,
            },
        })

    def commit(
        self,
        *,
        promotion_request: Mapping[str, Any],
        authorization: Mapping[str, Any],
        passport: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        require_action(self._policy(), "SCIENTIFIC_LAW_CANONICAL_MUTATION")

        # Current-gate replay: no stale qualification or stale human receipt may
        # cause mutation after the scientific state changed.
        replay = dict(self.core.evaluate(dict(promotion_request)))
        from .scientific_promotion import ScientificPromotionCore
        inference = dict(ScientificPromotionCore.inference_status(replay))
        promotion_hash = self._promotion_hash(replay)
        verification_digest = self._verification_digest(replay)
        current_ok = bool(
            inference.get("promotion_allowed") is True
            and replay.get("PROMOTION_ALLOWED") is True
            and str(replay.get("FINAL_STATUS", "")) == "LAW_CANDIDATE"
            and promotion_hash
            and verification_digest
        )
        if not current_ok:
            return _with_digest({
                "schema": SCHEMA,
                "owner_id": self.owner_id,
                "status": "BLOCKED_CURRENT_PROMOTION_GATES_NOT_PASSING",
                "registered": False,
                "promotion_receipt_id": replay.get("RECEIPT_ID"),
                "promotion_receipt_hash": promotion_hash,
                "final_status": replay.get("FINAL_STATUS"),
                "mutation_performed": False,
            })

        if not validate_scientific_law_authorization(
            authorization,
            promotion_receipt_hash=promotion_hash,
            evidence_digest=verification_digest,
        ):
            return _with_digest({
                "schema": SCHEMA,
                "owner_id": self.owner_id,
                "status": "BLOCKED_INVALID_OR_STALE_HUMAN_AUTHORIZATION",
                "registered": False,
                "promotion_receipt_id": replay.get("RECEIPT_ID"),
                "promotion_receipt_hash": promotion_hash,
                "mutation_performed": False,
            })

        passport_ok, reasons, row = self._validate_passport(
            passport, replay=replay, authorization=authorization
        )
        if not passport_ok or row is None:
            return _with_digest({
                "schema": SCHEMA,
                "owner_id": self.owner_id,
                "status": "BLOCKED_INVALID_CANONICAL_LAW_PASSPORT",
                "registered": False,
                "reasons": reasons,
                "mutation_performed": False,
            })

        owner_id = str(row.get("owner_id", ""))
        existing = [x for x in self._existing_rows() if str(x.get("owner_id", "")) == owner_id]
        if existing:
            if len(existing) == 1 and str(existing[0].get("digest", "")) == str(row.get("digest", "")):
                return _with_digest({
                    "schema": SCHEMA,
                    "owner_id": self.owner_id,
                    "status": "IDEMPOTENT_CANONICAL_LAW_ALREADY_REGISTERED",
                    "registered": True,
                    "canonical_owner_id": owner_id,
                    "passport_digest": row.get("digest"),
                    "mutation_performed": False,
                    "world_novelty_established": False,
                })
            return _with_digest({
                "schema": SCHEMA,
                "owner_id": self.owner_id,
                "status": "BLOCKED_CANONICAL_OWNER_ID_CONFLICT",
                "registered": False,
                "canonical_owner_id": owner_id,
                "mutation_performed": False,
            })

        target = self._target()
        target.parent.mkdir(parents=True, exist_ok=True)
        old = target.read_text(encoding="utf-8") if target.is_file() else ""
        new_line = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(old + new_line, encoding="utf-8")
        os.replace(tmp, target)

        # Replay the persisted row through the same passport parser and catalog
        # validator used by the runtime. The runtime already loads every
        # ``data/passports/known_*.jsonl`` file on its next construction.
        persisted = None
        for line in target.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            candidate_row = dict(json.loads(line))
            if str(candidate_row.get("owner_id", "")) == owner_id:
                persisted = candidate_row
        if persisted is None:
            raise RuntimeError("canonical law transaction row not found after atomic write")
        replay_passport = passport_from_persisted(persisted).finalized()
        LawCatalog().add_passport(replay_passport)
        if str(replay_passport.digest) != str(row.get("digest", "")):
            raise RuntimeError("canonical law transaction persisted passport digest mismatch")

        return _with_digest({
            "schema": SCHEMA,
            "owner_id": self.owner_id,
            "status": "CANONICAL_SCIENTIFIC_LAW_REGISTERED",
            "registered": True,
            "canonical_owner_id": owner_id,
            "passport_digest": row.get("digest"),
            "promotion_receipt_id": replay.get("RECEIPT_ID"),
            "promotion_receipt_hash": promotion_hash,
            "scientific_verification_digest": verification_digest,
            "human_authorization_digest": authorization.get("digest"),
            "registry_path": str(target),
            "mutation_performed": True,
            "claim_boundary": {
                "scientific_promotion_core_remains_authoritative": True,
                "human_authorization_is_scientific_evidence": False,
                "canonical_registry_mutated": True,
                "canonical_scientific_law_registered_in_atlas": True,
                "world_novelty_established_by_transaction": False,
                "release_reseal_required": True,
            },
        })
