"""Release qualification for research-acceleration and final promotion boundaries."""
from __future__ import annotations

import inspect
from pathlib import Path

from source.lawspace.canonical_law_transaction import CanonicalLawRegistryTransactionOwner
from source.lawspace.discriminating_experiment_autopilot import DiscriminatingExperimentAutopilotOwner
from source.lawspace.engineering_model_acceptance import EngineeringModelAcceptanceOwner, EngineeringModelLedgerOwner
from source.lawspace.execution_policy import POLICY_SCHEMA, load_execution_policy, validate_execution_policy
from source.lawspace.promotion_confirmation import HumanGatedPromotionAuthorizationOwner
from source.lawspace.u5_attempt_scheduler import U5AttemptConfig, U5AttemptScheduler
from source.lawspace.research_cycle import ScientificResearchCycleOwner
from source.lawspace.schema import digest_payload


class _Verifier:
    def __init__(self, receipt): self.receipt = receipt
    def verify_bundle(self, bundle): return dict(self.receipt)


class _PromotionCore:
    def __init__(self, allowed=True): self.allowed = allowed
    def evaluate(self, request):
        return {
            "RECEIPT_ID": "SPR-QUALIFICATION",
            "OUTPUT_HASH": "f" * 64,
            "CANDIDATES": ["QUALIFICATION-CANDIDATE"],
            "PROMOTION_ALLOWED": self.allowed,
            "FINAL_STATUS": "LAW_CANDIDATE" if self.allowed else "REPLICATED",
            "TERMINAL_REASON": "QUALIFICATION",
            "scientific_verification": {"verification_digest": "e" * 64},
        }


class _ExperimentKernel:
    def design(self, **kwargs):
        return {
            "status": "DISCRIMINATING_EXPERIMENT_SELECTED",
            "selection": {
                "status": "DISCRIMINATING_EXPERIMENT_SELECTED",
                "digest": "s" * 64,
                "frontier_freeze_digest": "f" * 64,
                "selected_experiment": {"experiment_id": "Q"},
                "theory_promotion_allowed": False,
            },
            "attestation_bridge": {
                "status": "WORLD_ATTESTATION_PENDING_EXTERNAL_MEASUREMENT",
                "measurement_protocol": {
                    "measurement_id": "M",
                    "experiment_id": "Q",
                    "initial_state": "S",
                    "actions": ["A"],
                    "protocol_digest": "p" * 64,
                    "required_result_fields": ["data_digest"],
                },
            },
        }


def run_release_qualification(root: str | Path | None = None):
    root = Path(root or ".").resolve()
    policy = {
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
    checks = {}
    checks["policy_valid"] = bool(validate_execution_policy(policy)["valid"])
    try:
        persisted_policy = dict(load_execution_policy(root))
        checks["persisted_policy_v5_integrity_valid"] = (
            persisted_policy.get("schema") == POLICY_SCHEMA
            and bool(str(persisted_policy.get("digest", "")).strip())
        )
    except (OSError, ValueError, PermissionError):
        checks["persisted_policy_v5_integrity_valid"] = False

    pending_verification = {
        "overall_status": "PASS_ENGINE_OR_MODEL_VERIFICATION_WORLD_CLAIM_BLOCKED",
        "verification_digest": "a" * 64,
        "evidence_ready_for_domain": True,
        "world_attestation_ready": False,
        "scientific_candidate_allowed": False,
        "evidence_class": "INTERNAL_MEASUREMENT",
    }
    sched = U5AttemptScheduler(verifier=_Verifier(pending_verification))
    candidate = {
        "candidate_id": "Q-U5",
        "scientific_verification_bundle": {"x": 1},
        "ood_pass": True,
        "ood_fractional_improvement": 0.1,
        "complexity_penalized_delta_log_likelihood": 1.0,
        "independent_replication": True,
        "replication_provenance": "Q",
        "falsification_protocol": "Q",
        "falsification_status": "SURVIVED",
    }
    u5 = sched.attempt_one(candidate, config=U5AttemptConfig())
    checks["world_missing_is_pending_not_fail"] = u5["result"]["outcome"] == "U5_DATA_PENDING"
    checks["u5_never_promotes"] = u5["mutation_performed"] is False and u5["promotion_allowed"] is False

    core = _PromotionCore(True)
    auth_owner = HumanGatedPromotionAuthorizationOwner(promotion_core=core)
    q = auth_owner.qualify({})
    checks["human_gate_waits"] = q["status"] == "AWAITING_HUMAN_CONFIRMATION" and q["mutation_performed"] is False
    bad = auth_owner.confirm({}, qualification_digest=q["digest"], human_attestation={})
    checks["human_gate_blocks_unbound_attestation"] = bad["authorized"] is False

    eng = EngineeringModelAcceptanceOwner().accept(
        {"candidate_id": "Q-E"},
        {"domain": "qualification", "regime_id": "R", "validity_bounds": {"x": [0, 1]}},
        {"evidence_class": "MODEL_DERIVED", "fit_pass": True, "regime_ood_pass": True,
         "uncertainty_declared": True, "evidence_digest": "d" * 64},
    )
    checks["engineering_accept_is_not_law"] = eng["accepted"] is True and eng["claim_boundary"]["scientific_law_established"] is False
    ledger_contract = EngineeringModelLedgerOwner(root).contract()
    checks["engineering_ledger_is_external_and_not_law"] = (
        ledger_contract["live_state_inside_sealed_release"] is False
        and ledger_contract["scientific_law_established"] is False
    )

    autopilot = DiscriminatingExperimentAutopilotOwner(root, kernel=_ExperimentKernel())
    auto_contract = autopilot.contract()
    design = autopilot.design(
        question="Q", candidate_theory={"digest": "c" * 64},
        baseline_theories=[{"digest": "b" * 64}], cost_budget=2.0,
    )
    checks["discriminating_autopilot_emits_request_without_promotion"] = (
        design["status"] == "MEASUREMENT_REQUEST_READY"
        and design["claim_boundary"]["theory_promotion_allowed"] is False
        and auto_contract["canonical_registry_mutation_allowed"] is False
    )

    tx_contract = CanonicalLawRegistryTransactionOwner(root, promotion_core=core).contract()
    checks["canonical_transaction_is_thin_replay_gated_persistence"] = (
        tx_contract["transaction_role_only"] is True
        and tx_contract["rerun_current_promotion_gates_before_write"] is True
        and tx_contract["human_authorization_required"] is True
        and tx_contract["automatic_scientific_law_promotion"] is False
    )

    from source.lawspace.api import LawSpaceAPI
    promote_src = inspect.getsource(LawSpaceAPI.promote_dynamic_axis)
    axis_model_src = inspect.getsource(LawSpaceAPI.run_axis_modeling_with_dynamic_expansion)
    checks["dynamic_axis_api_requires_authorization"] = (
        "authorization" in promote_src
        and "validate_canonical_mutation_authorization" in promote_src
        and "BLOCKED_MISSING_HUMAN_MUTATION_AUTHORIZATION" in promote_src
    )
    checks["axis_modeling_routes_through_gated_api"] = (
        "self.promote_dynamic_axis(" in axis_model_src
        and 'authorization=promotion_cfg.get("authorization")' in axis_model_src
    )
    progression_src = inspect.getsource(ScientificResearchCycleOwner._research_acceleration_progression)
    autonomous_src = inspect.getsource(ScientificResearchCycleOwner.run_autonomous)
    checks["scientific_research_cycle_owns_acceleration_progression"] = (
        "_get_u5_scheduler().attempt_one" in progression_src
        and "_get_experiment_autopilot().design" in progression_src
        and "_get_promotion_authorization().qualify" in progression_src
        and ".commit(" not in progression_src
        and "research_acceleration = self._research_acceleration_progression" in autonomous_src
    )
    checks["autonomous_cycle_stops_before_human_or_canonical_mutation"] = (
        '"human_authorization_performed_automatically": False' in progression_src
        and '"canonical_registry_mutated_by_autonomous_research": False' in progression_src
        and ".confirm(" not in progression_src
        and ".commit(" not in progression_src
    )

    checks["tool_classification_preserves_truth_boundary"] = (
        "run_u5_attempt_batch" in LawSpaceAPI.READ_TOOLS
        and "design_discriminating_experiment_autopilot" in LawSpaceAPI.READ_TOOLS
        and "get_engineering_model_ledger_state" in LawSpaceAPI.READ_TOOLS
        and "get_canonical_law_transaction_contract" in LawSpaceAPI.READ_TOOLS
        and "qualify_scientific_law_transaction" in LawSpaceAPI.READ_TOOLS
        and "confirm_promotion_authorization" in LawSpaceAPI.MUTATION_TOOLS
        and "queue_discriminating_experiment_measurement_request" in LawSpaceAPI.MUTATION_TOOLS
        and "record_engineering_model_acceptance" in LawSpaceAPI.MUTATION_TOOLS
        and "revoke_engineering_model_acceptance" in LawSpaceAPI.MUTATION_TOOLS
        and "commit_scientific_law_promotion" in LawSpaceAPI.MUTATION_TOOLS
    )
    payload = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "passed": sum(bool(x) for x in checks.values()),
        "total": len(checks),
        "checks": checks,
    }
    payload["digest"] = digest_payload(payload)
    return payload


if __name__ == "__main__":
    import json
    print(json.dumps(run_release_qualification(), ensure_ascii=False, indent=2, sort_keys=True))
