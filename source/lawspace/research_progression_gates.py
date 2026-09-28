"""Shared evidence-progression gates for U5 and promotion qualification.

This module owns no scientific truth and no registry mutation.  It only
normalizes the generic OOD / replication / falsification checks so automated U5
attempts and human-gated promotion qualification can use the same semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .schema import digest_payload

OWNER_ID = "RESEARCH-PROGRESSION-GATES/1.0.0"
SCHEMA = "phi-research-progression-gates/v1"


@dataclass(frozen=True)
class ProgressionGateConfig:
    require_ood: bool = True
    require_replication: bool = True
    require_falsification_protocol: bool = True
    min_ood_fractional_improvement: float = 0.0
    min_complexity_penalized_delta_ll: float = 0.0

    def validate(self) -> None:
        if self.min_ood_fractional_improvement < 0:
            raise ValueError("min_ood_fractional_improvement must be >= 0")
        if self.min_complexity_penalized_delta_ll < 0:
            raise ValueError("min_complexity_penalized_delta_ll must be >= 0")


def evaluate_progression_gates(
    candidate: Mapping[str, Any],
    *,
    config: ProgressionGateConfig | None = None,
) -> Mapping[str, Any]:
    cfg = config or ProgressionGateConfig()
    cfg.validate()

    gates: dict[str, bool] = {}
    reasons: list[str] = []
    pending: list[str] = []

    if cfg.require_ood:
        flag = candidate.get("ood_pass")
        declared = flag is not None
        frac_declared = candidate.get("ood_fractional_improvement") is not None
        dll_declared = candidate.get("complexity_penalized_delta_log_likelihood") is not None
        frac = float(candidate.get("ood_fractional_improvement", 0.0) or 0.0)
        dll = float(candidate.get("complexity_penalized_delta_log_likelihood", 0.0) or 0.0)
        threshold_ok = (
            frac > float(cfg.min_ood_fractional_improvement)
            and dll > float(cfg.min_complexity_penalized_delta_ll)
        )
        gates.update({
            "OOD_REQUIRED": True,
            "OOD_DECLARED": declared and frac_declared and dll_declared,
            "OOD_PASS_FLAG": bool(flag) if declared else False,
            "OOD_FRACTIONAL_IMPROVEMENT_OK": frac_declared and frac > float(cfg.min_ood_fractional_improvement),
            "OOD_COMPLEXITY_PENALIZED_LL_OK": dll_declared and dll > float(cfg.min_complexity_penalized_delta_ll),
            "OOD_PASS": declared and bool(flag) and frac_declared and dll_declared and threshold_ok,
        })
        if not declared or not frac_declared or not dll_declared:
            pending.append("OOD evidence incomplete")
        elif not bool(flag):
            reasons.append("ood_pass is false")
        elif not threshold_ok:
            reasons.append("OOD quantitative threshold failed")
    else:
        gates.update({"OOD_REQUIRED": False, "OOD_DECLARED": True, "OOD_PASS": True})

    if cfg.require_replication:
        flag = candidate.get("independent_replication")
        provenance = str(candidate.get("replication_provenance", "")).strip()
        declared = flag is not None
        gates.update({
            "REPLICATION_REQUIRED": True,
            "REPLICATION_DECLARED": declared,
            "REPLICATION_PROVENANCE_DECLARED": bool(provenance),
            "REPLICATION_PASS": declared and bool(flag) and bool(provenance),
        })
        if not declared or not provenance:
            pending.append("replication evidence incomplete")
        elif not bool(flag):
            reasons.append("independent_replication is false")
    else:
        gates.update({"REPLICATION_REQUIRED": False, "REPLICATION_DECLARED": True, "REPLICATION_PASS": True})

    if cfg.require_falsification_protocol:
        protocol = str(candidate.get("falsification_protocol", "")).strip()
        status = str(candidate.get("falsification_status", "")).strip().upper()
        declared = bool(protocol) and bool(status)
        survived = status == "SURVIVED"
        gates.update({
            "FALSIFICATION_REQUIRED": True,
            "FALSIFICATION_DECLARED": declared,
            "FALSIFICATION_PROTOCOL_DECLARED": bool(protocol),
            "FALSIFICATION_SURVIVED": survived,
            "FALSIFICATION_PASS": bool(protocol) and survived,
        })
        if not protocol or not status:
            pending.append("falsification evidence incomplete")
        elif not survived:
            reasons.append(f"falsification_status={status}")
    else:
        gates.update({"FALSIFICATION_REQUIRED": False, "FALSIFICATION_DECLARED": True, "FALSIFICATION_PASS": True})

    payload = {
        "schema": SCHEMA,
        "owner_id": OWNER_ID,
        "gates": gates,
        "hard_fail_reasons": reasons,
        "pending_reasons": pending,
        "all_required_progression_gates_pass": all(
            gates.get(key, True)
            for key in ("OOD_PASS", "REPLICATION_PASS", "FALSIFICATION_PASS")
        ),
        "claim_boundary": {
            "scientific_law_promoted": False,
            "canonical_registry_mutated": False,
            "gate_receipt_is_scientific_truth": False,
        },
    }
    payload["digest"] = digest_payload(payload)
    return payload
