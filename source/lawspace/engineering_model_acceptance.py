"""Regime-scoped engineering acceptance and append-only ledger.

Engineering acceptance is deliberately distinct from scientific law.  Live
ledger state is stored outside the sealed release tree; a release may export a
snapshot explicitly, but runtime acceptance never mutates the canonical law
registry or the sealed source tree.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from .execution_policy import load_execution_policy, require_action
from .runtime import LawSpaceRuntime
from .schema import digest_payload

OWNER_ID = "ENGINEERING-MODEL-ACCEPTANCE/1.2.0"
SCHEMA = "phi-engineering-model-acceptance/v1.2"
LEDGER_OWNER_ID = "ENGINEERING-MODEL-LEDGER/1.0.0"
LEDGER_SCHEMA = "phi-engineering-model-ledger/v1"


def _valid_receipt(receipt: Mapping[str, Any] | None) -> bool:
    if not isinstance(receipt, Mapping):
        return False
    body = dict(receipt)
    embedded = str(body.pop("digest", ""))
    return bool(embedded and embedded == digest_payload(body))


class EngineeringModelAcceptanceOwner:
    owner_id = OWNER_ID

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else None

    def _policy(self) -> Mapping[str, Any]:
        if self.root is None:
            return {
                "automatic_scientific_law_promotion": False,
                "automatic_research_triage": True,
                "automatic_u5_attempts": True,
                "human_gated_promotion": True,
                "engineering_model_acceptance": True,
                "engineering_model_ledger": True,
                "sandbox_profiles_allowed": ["STRICT", "RESEARCH", "WIDE"],
                "u5_attempt_writes_canonical_registry": False,
                "discriminating_experiment_may_auto_promote": False,
                "human_confirmation_is_scientific_evidence": False,
                "engineering_acceptance_is_scientific_law": False,
            }
        return load_execution_policy(self.root)

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner_id": self.owner_id,
            "accepted_status": "ENGINEERING_MODEL_ACCEPTED_FOR_REGIME",
            "canonical_law_registry_target": False,
            "scientific_law_established": False,
            "world_novelty_established": False,
            "persistent_ledger_owner": LEDGER_OWNER_ID,
        }
        return {**payload, "digest": digest_payload(payload)}

    def accept(
        self,
        candidate: Mapping[str, Any],
        regime_spec: Mapping[str, Any],
        evidence: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        require_action(self._policy(), "ENGINEERING_MODEL_ACCEPTANCE")
        cid = str(candidate.get("candidate_id", "")).strip()
        domain = str(regime_spec.get("domain", "")).strip()
        regime_id = str(regime_spec.get("regime_id", "")).strip()
        bounds = regime_spec.get("validity_bounds")
        evidence_class = str(evidence.get("evidence_class", "MODEL_DERIVED")).strip().upper()
        allowed_evidence_classes = {"MODEL_DERIVED", "INTERNAL_MEASUREMENT", "LOCAL_SNAPSHOT", "EXTERNAL_SOURCE"}
        checks = {
            "CANDIDATE_ID_DECLARED": bool(cid),
            "DOMAIN_DECLARED": bool(domain),
            "REGIME_ID_DECLARED": bool(regime_id),
            "VALIDITY_BOUNDS_DECLARED": isinstance(bounds, Mapping) and bool(bounds),
            "EVIDENCE_CLASS_ALLOWED": evidence_class in allowed_evidence_classes,
            "UNCERTAINTY_DECLARED": evidence.get("uncertainty_declared") is True,
            "FIT_PASS": evidence.get("fit_pass") is True,
            "REGIME_OOD_PASS": evidence.get("regime_ood_pass") is True,
            "EVIDENCE_DIGEST_DECLARED": bool(str(evidence.get("evidence_digest", "")).strip()),
        }
        accepted = all(checks.values())
        payload = {
            "schema": SCHEMA,
            "owner_id": self.owner_id,
            "status": "ENGINEERING_MODEL_ACCEPTED_FOR_REGIME" if accepted else "ENGINEERING_MODEL_ACCEPTANCE_BLOCKED",
            "accepted": accepted,
            "candidate_id": cid,
            "candidate_digest": str(candidate.get("digest", "")),
            "regime_scope": {"domain": domain, "regime_id": regime_id, "validity_bounds": bounds},
            "checks": checks,
            "evidence_class": evidence_class,
            "evidence_digest": str(evidence.get("evidence_digest", "")),
            "acceptance_receipt_is_scientific_verification_receipt": False,
            "claim_boundary": {
                "scientific_law_established": False,
                "world_novelty_established": False,
                "usable_for_engineering_prediction": accepted,
                "canonical_law_registry_mutated": False,
                "canonical_axis_registry_mutated": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}


class EngineeringModelLedgerOwner:
    """Append-only acceptance/revocation history outside the sealed release."""

    owner_id = LEDGER_OWNER_ID

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.runtime = object.__new__(LawSpaceRuntime)
        self.runtime.root = self.root

    def _policy(self) -> Mapping[str, Any]:
        return load_execution_policy(self.root)

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": LEDGER_SCHEMA,
            "owner_id": self.owner_id,
            "append_only_events": ["ACCEPT", "REVOKE"],
            "live_state_inside_sealed_release": False,
            "canonical_law_registry_target": False,
            "scientific_law_established": False,
        }
        return {**payload, "digest": digest_payload(payload)}

    def _path(self) -> Path:
        return self.runtime.external_state_path("engineering_model_ledger")

    def _read(self) -> dict[str, Any]:
        path = self._path()
        if not path.is_file():
            return {
                "schema": LEDGER_SCHEMA,
                "owner_id": self.owner_id,
                "events": [],
                "event_count": 0,
                "mutable_state_inside_sealed_tree": False,
            }
        doc = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(doc, Mapping) or doc.get("schema") != LEDGER_SCHEMA or doc.get("owner_id") != self.owner_id:
            raise ValueError("invalid engineering model ledger")
        embedded = str(doc.get("digest", ""))
        core = {k: v for k, v in doc.items() if k != "digest"}
        if embedded != digest_payload(core):
            raise ValueError("engineering model ledger digest mismatch")
        return dict(doc)

    def _write(self, doc: Mapping[str, Any]) -> None:
        path = self._path()
        path.parent.mkdir(parents=True, exist_ok=True)
        core = {k: v for k, v in dict(doc).items() if k != "digest"}
        out = {**core, "digest": digest_payload(core)}
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(tmp, path)

    @staticmethod
    def _event(event_type: str, acceptance_digest: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        core = {
            "event_type": str(event_type),
            "acceptance_digest": str(acceptance_digest),
            **dict(payload),
        }
        event_id = "EME-" + digest_payload(core)[:24].upper()
        return {"event_id": event_id, **core, "digest": digest_payload({"event_id": event_id, **core})}

    def record_acceptance(self, acceptance_receipt: Mapping[str, Any]) -> Mapping[str, Any]:
        require_action(self._policy(), "ENGINEERING_MODEL_LEDGER")
        receipt = dict(acceptance_receipt or {})
        if not _valid_receipt(receipt) or receipt.get("accepted") is not True or receipt.get("status") != "ENGINEERING_MODEL_ACCEPTED_FOR_REGIME":
            return {
                "status": "ENGINEERING_MODEL_LEDGER_BLOCKED_INVALID_ACCEPTANCE",
                "recorded": False,
                "scientific_law_established": False,
            }
        acceptance_digest = str(receipt["digest"])
        doc = self._read()
        events = [dict(x) for x in doc.get("events", ())]
        if any(x.get("event_type") == "ACCEPT" and x.get("acceptance_digest") == acceptance_digest for x in events):
            return {
                "status": "IDEMPOTENT_ENGINEERING_ACCEPTANCE_ALREADY_RECORDED",
                "recorded": True,
                "acceptance_digest": acceptance_digest,
                "ledger_path": str(self._path()),
                "scientific_law_established": False,
            }
        event = self._event("ACCEPT", acceptance_digest, {
            "candidate_id": receipt.get("candidate_id"),
            "candidate_digest": receipt.get("candidate_digest"),
            "regime_scope": receipt.get("regime_scope"),
            "evidence_digest": receipt.get("evidence_digest"),
            "acceptance_receipt": receipt,
        })
        events.append(event)
        self._write({
            "schema": LEDGER_SCHEMA,
            "owner_id": self.owner_id,
            "events": events,
            "event_count": len(events),
            "mutable_state_inside_sealed_tree": False,
            "canonical_law_registry_mutated": False,
        })
        return {
            "status": "ENGINEERING_MODEL_ACCEPTANCE_RECORDED",
            "recorded": True,
            "event": event,
            "ledger_path": str(self._path()),
            "scientific_law_established": False,
            "canonical_law_registry_mutated": False,
        }

    def revoke(self, *, acceptance_digest: str, reason: str, actor_id: str) -> Mapping[str, Any]:
        require_action(self._policy(), "ENGINEERING_MODEL_LEDGER")
        acceptance_digest = str(acceptance_digest).strip()
        reason = str(reason).strip()
        actor_id = str(actor_id).strip()
        if not acceptance_digest or not reason or not actor_id:
            raise ValueError("acceptance_digest, reason and actor_id are required")
        doc = self._read()
        events = [dict(x) for x in doc.get("events", ())]
        if not any(x.get("event_type") == "ACCEPT" and x.get("acceptance_digest") == acceptance_digest for x in events):
            return {"status": "ENGINEERING_MODEL_REVOCATION_BLOCKED_UNKNOWN_ACCEPTANCE", "revoked": False}
        if any(x.get("event_type") == "REVOKE" and x.get("acceptance_digest") == acceptance_digest for x in events):
            return {"status": "IDEMPOTENT_ENGINEERING_MODEL_ALREADY_REVOKED", "revoked": True}
        event = self._event("REVOKE", acceptance_digest, {"reason": reason, "actor_id": actor_id})
        events.append(event)
        self._write({
            "schema": LEDGER_SCHEMA,
            "owner_id": self.owner_id,
            "events": events,
            "event_count": len(events),
            "mutable_state_inside_sealed_tree": False,
            "canonical_law_registry_mutated": False,
        })
        return {
            "status": "ENGINEERING_MODEL_ACCEPTANCE_REVOKED",
            "revoked": True,
            "event": event,
            "scientific_law_established": False,
            "canonical_law_registry_mutated": False,
        }

    def state(self) -> Mapping[str, Any]:
        doc = self._read()
        active: dict[str, Mapping[str, Any]] = {}
        revoked: set[str] = set()
        for event in doc.get("events", ()):
            d = str(event.get("acceptance_digest", ""))
            if event.get("event_type") == "ACCEPT":
                active[d] = event
            elif event.get("event_type") == "REVOKE":
                revoked.add(d)
        rows = [dict(v) for k, v in sorted(active.items()) if k not in revoked]
        return {
            "schema": LEDGER_SCHEMA,
            "owner_id": self.owner_id,
            "status": "ENGINEERING_MODEL_LEDGER_STATE",
            "active_acceptance_count": len(rows),
            "active_acceptances": rows,
            "event_count": int(doc.get("event_count", 0)),
            "ledger_path": str(self._path()),
            "scientific_law_established": False,
            "canonical_law_registry_mutated": False,
        }
