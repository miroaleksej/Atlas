"""Prospective external scientific validation.

The owner is intentionally downstream of an already-frozen internal candidate.
External evidence may validate, falsify, support, or leave the frozen claim
blocked, but it may not select a new candidate or alter the estimand after
lookup.  This is the bridge from internal Φ-discovery to World Attestation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .schema import canonical_json, digest_payload

KERNEL_OWNER_ID = "PHI-PROSPECTIVE-EXTERNAL-SCIENTIFIC-VALIDATION/1.0.0"
VALIDATION_OWNER_ID = "PROSPECTIVE-VALIDATION-GATE/1.0.0"
EXTERNAL_EVIDENCE_OWNER_ID = "POSTFREEZE-EXTERNAL-EVIDENCE-BINDER/1.0.0"
SCHEMA = "phi-prospective-external-scientific-validation/v1"


def _valid_sha256(value: Any) -> bool:
    s = str(value or "")
    return len(s) == 64 and all(c in "0123456789abcdefABCDEF" for c in s)


def _freeze_digest_valid(freeze: Mapping[str, Any]) -> bool:
    expected = freeze.get("validation_freeze_digest")
    if not _valid_sha256(expected):
        return False
    body = {k: v for k, v in freeze.items() if k != "validation_freeze_digest"}
    return digest_payload(body) == expected


class ProspectiveValidationGateOwner:
    owner_id = VALIDATION_OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": "phi-prospective-validation-gate/v1",
            "owner_id": self.owner_id,
            "ordering": ["internal_candidate_freeze", "external_lookup", "evidence_binding", "primary_estimand_test", "world_attestation_or_revision"],
            "rules": {
                "candidate_switch_after_external_lookup_allowed": False,
                "external_evidence_may_select_candidate_prefreeze": False,
                "supportive_mechanism_evidence_may_substitute_primary_estimand": False,
                "blocked_is_valid_scientific_outcome": True,
                "world_claim_requires_admissible_primary_measurement": True,
                "primary_measurement_must_be_postfreeze": True,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    def evaluate(self, *, freeze: Mapping[str, Any], external_audit: Mapping[str, Any]) -> Mapping[str, Any]:
        checks = {
            "freeze_digest_valid": _freeze_digest_valid(freeze),
            "candidate_frozen_before_lookup": freeze.get("selection_policy", {}).get("candidate_selected_from_preexisting_internal_freeze") is True,
            "internet_not_candidate_selector": freeze.get("selection_policy", {}).get("internet_used_for_candidate_selection") is False,
            "candidate_switch_forbidden": freeze.get("selection_policy", {}).get("candidate_switch_after_external_lookup_allowed") is False,
            "same_candidate": str(external_audit.get("candidate_id")) == str(freeze.get("candidate", {}).get("candidate_id")),
            "audit_did_not_select_candidate": external_audit.get("selection_policy", {}).get("candidate_selected_before_external_lookup") is True,
        }
        if not all(checks.values()):
            payload = {
                "schema": SCHEMA, "owner_id": self.owner_id,
                "status": "BLOCKED_VALIDATION_CONTRACT_VIOLATION",
                "checks": checks, "selected_candidate": None,
                "claim_boundary": {"world_validated": False, "candidate_switch_allowed": False},
            }
            return {**payload, "digest": digest_payload(payload)}

        sources = list(external_audit.get("sources", ()))
        admissible = [s for s in sources if s.get("primary_estimand_available") is True and s.get("prospective_after_candidate_freeze") is True]
        supportive = [s for s in sources if s.get("primary_estimand_available") is not True and s.get("relevance")]
        direction = str(freeze.get("validation_contract", {}).get("directional_prediction", "")).strip()
        decisions: list[dict[str, Any]] = []
        positive = negative = 0
        for s in admissible:
            est = s.get("primary_estimate")
            lo = s.get("confidence_interval_low")
            hi = s.get("confidence_interval_high")
            if not isinstance(est, (int, float)):
                decisions.append({"source_id": s.get("source_id"), "status": "INADMISSIBLE_MISSING_PRIMARY_ESTIMATE"})
                continue
            if direction == "beta_TE > 0":
                if isinstance(lo, (int, float)) and lo > 0:
                    positive += 1; st = "SUPPORTS_FROZEN_DIRECTION"
                elif isinstance(hi, (int, float)) and hi <= 0:
                    negative += 1; st = "CONTRADICTS_FROZEN_DIRECTION"
                else:
                    st = "INCONCLUSIVE_PRIMARY_ESTIMATE"
            else:
                st = "BLOCKED_UNSUPPORTED_DIRECTIONAL_CONTRACT"
            decisions.append({"source_id": s.get("source_id"), "status": st, "estimate": est, "ci_low": lo, "ci_high": hi})

        if negative > 0:
            status = "PROSPECTIVE_EXTERNAL_VALIDATION_FAIL"
        elif positive > 0:
            status = "PROSPECTIVE_EXTERNAL_VALIDATION_PASS"
        else:
            status = "BLOCKED_NO_ADMISSIBLE_PROSPECTIVE_MEASUREMENT"

        payload = {
            "schema": SCHEMA,
            "owner_id": self.owner_id,
            "status": status,
            "candidate_id": freeze.get("candidate", {}).get("candidate_id"),
            "candidate_freeze_digest": freeze.get("candidate", {}).get("freeze_digest"),
            "validation_freeze_digest": freeze.get("validation_freeze_digest"),
            "primary_estimand": freeze.get("validation_contract", {}).get("primary_estimand"),
            "directional_prediction": direction,
            "checks": checks,
            "external_source_count": len(sources),
            "admissible_primary_measurement_count": len(admissible),
            "supportive_source_count": len(supportive),
            "primary_decisions": decisions,
            "supportive_sources": [
                {"source_id": s.get("source_id"), "relevance": s.get("relevance"), "inadmissibility_reasons": s.get("inadmissibility_reasons", [])}
                for s in supportive
            ],
            "claim_boundary": {
                "external_lookup_occurred_after_validation_freeze": True,
                "supportive_evidence_is_primary_validation": False,
                "blocked_status_is_candidate_confirmation": False,
                "world_validated": status == "PROSPECTIVE_EXTERNAL_VALIDATION_PASS",
                "world_falsified": status == "PROSPECTIVE_EXTERNAL_VALIDATION_FAIL",
                "candidate_switch_allowed": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}


class ProspectiveExternalScientificValidationKernel:
    owner_id = KERNEL_OWNER_ID

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.gate = ProspectiveValidationGateOwner()

    def freeze_internal_candidate(self, candidate: Mapping[str, Any]) -> Mapping[str, Any]:
        """Bind a current digest-bound internal candidate to the prospective gate.

        This replaces the deleted historical freeze-report dependency.  The
        machine-readable estimand/direction must already be present in the
        frozen internal candidate; this owner does not infer a scientific
        direction from prose or external evidence.
        """
        candidate_id = str(candidate.get("candidate_id") or "")
        freeze_digest = str(candidate.get("freeze_digest") or "")
        primary_estimand = str(candidate.get("primary_estimand") or "")
        direction = str(candidate.get("machine_directional_prediction") or "")
        if not candidate_id or not _valid_sha256(freeze_digest) or not primary_estimand or not direction:
            payload = {
                "schema": "phi-prospective-validation-freeze/v1",
                "owner_id": self.owner_id,
                "status": "BLOCKED_INTERNAL_CANDIDATE_NOT_MACHINE_FREEZABLE",
                "candidate": {"candidate_id": candidate_id, "freeze_digest": freeze_digest},
                "claim_boundary": {"direction_inferred_from_external_evidence": False},
            }
            return {**payload, "digest": digest_payload(payload)}
        body = {
            "schema": "phi-prospective-validation-freeze/v1",
            "owner_id": self.owner_id,
            "status": "PROSPECTIVE_VALIDATION_FREEZE_BOUND",
            "candidate": {
                "candidate_id": candidate_id,
                "freeze_digest": freeze_digest,
                "source_scan_digest": candidate.get("source_scan_digest"),
            },
            "validation_contract": {
                "primary_estimand": primary_estimand,
                "directional_prediction": direction,
            },
            "selection_policy": {
                "candidate_selected_from_preexisting_internal_freeze": True,
                "internet_used_for_candidate_selection": False,
                "candidate_switch_after_external_lookup_allowed": False,
            },
            "claim_boundary": {
                "direction_inferred_from_external_evidence": False,
                "historical_report_required": False,
            },
        }
        body["validation_freeze_digest"] = digest_payload(body)
        return body

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": "phi-prospective-external-validation-contract/v1",
            "owner_id": self.owner_id,
            "owners": [VALIDATION_OWNER_ID, EXTERNAL_EVIDENCE_OWNER_ID],
            "pipeline": ["internal_phi_discovery", "freeze", "external_evidence", "primary_estimand_gate", "world_attestation_or_revision"],
            "rules": self.gate.contract()["rules"],
            "next": "MULTI-CYCLE-PROSPECTIVE-EXTERNAL-VALIDATION",
        }
        return {**payload, "digest": digest_payload(payload)}

    def validate_files(self, *, freeze_path: str | Path, external_audit_path: str | Path) -> Mapping[str, Any]:
        freeze = json.loads(Path(freeze_path).read_text(encoding="utf-8"))
        audit = json.loads(Path(external_audit_path).read_text(encoding="utf-8"))
        return self.gate.evaluate(freeze=freeze, external_audit=audit)
