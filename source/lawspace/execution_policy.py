"""Central authorization policy for research execution and promotion boundaries.

This policy never replaces scientific verification or promotion gates.  It only
states which classes of automatic action are permitted at runtime.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .schema import digest_payload

POLICY_SCHEMA = "phi-runtime-execution-policy/v5"
DEFAULT_POLICY = {
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


def load_execution_policy(root: str | Path) -> Mapping[str, Any]:
    path = Path(root) / "data/runtime/EXECUTION_POLICY_CURRENT.json"
    raw = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    out = dict(DEFAULT_POLICY)
    out.update(raw)
    return out


def validate_execution_policy(policy: Mapping[str, Any]) -> Mapping[str, Any]:
    errors: list[str] = []
    if bool(policy.get("automatic_scientific_law_promotion")):
        errors.append("automatic scientific law promotion must remain CLOSED")
    if bool(policy.get("u5_attempt_writes_canonical_registry")):
        errors.append("U5 attempts may not mutate canonical registry")
    if bool(policy.get("discriminating_experiment_may_auto_promote")):
        errors.append("discriminating experiment may not auto-promote")
    if bool(policy.get("human_confirmation_is_scientific_evidence")):
        errors.append("human confirmation is authorization, not scientific evidence")
    if bool(policy.get("engineering_acceptance_is_scientific_law")):
        errors.append("engineering acceptance must not be a scientific law")
    if bool(policy.get("canonical_law_transaction")) and not bool(policy.get("human_gated_promotion")):
        errors.append("canonical law transaction requires human-gated promotion")
    if bool(policy.get("canonical_law_transaction")) and not bool(policy.get("canonical_law_transaction_requires_current_gate_replay")):
        errors.append("canonical law transaction must replay current promotion gates")
    allowed = tuple(str(x).upper() for x in policy.get("sandbox_profiles_allowed", ()))
    if not allowed or any(x not in {"STRICT", "RESEARCH", "WIDE"} for x in allowed):
        errors.append("sandbox_profiles_allowed contains unsupported profile")
    payload = {
        "schema": "phi-runtime-authorization-policy-validation/v1",
        "valid": not errors,
        "errors": errors,
        "effective_policy": dict(policy),
    }
    payload["digest"] = digest_payload(payload)
    if errors:
        raise PermissionError("; ".join(errors))
    return payload


def require_action(policy: Mapping[str, Any], action: str) -> None:
    validate_execution_policy(policy)
    action = str(action).upper().strip()
    flag = {
        "RESEARCH_TRIAGE": "automatic_research_triage",
        "U5_ATTEMPT": "automatic_u5_attempts",
        "HUMAN_GATED_PROMOTION": "human_gated_promotion",
        "ENGINEERING_MODEL_ACCEPTANCE": "engineering_model_acceptance",
        "ENGINEERING_MODEL_LEDGER": "engineering_model_ledger",
        "DISCRIMINATING_EXPERIMENT_AUTOPILOT": "automatic_discriminating_experiment_design",
        "SCIENTIFIC_LAW_CANONICAL_MUTATION": "canonical_law_transaction",
    }.get(action)
    if flag is None:
        raise ValueError(f"unsupported execution-policy action: {action}")
    if not bool(policy.get(flag)):
        raise PermissionError(f"execution policy forbids {action}")
