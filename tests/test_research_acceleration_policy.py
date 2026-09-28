from source.lawspace.execution_policy import validate_execution_policy
from source.lawspace.research_progression_gates import ProgressionGateConfig, evaluate_progression_gates


def _policy():
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


def test_policy_keeps_law_promotion_closed():
    out = validate_execution_policy(_policy())
    assert out["valid"] is True


def test_policy_rejects_auto_law_promotion():
    p = _policy(); p["automatic_scientific_law_promotion"] = True
    try:
        validate_execution_policy(p)
        assert False, "must fail closed"
    except PermissionError:
        pass


def test_shared_progression_gate_distinguishes_pending_from_fail():
    pending = evaluate_progression_gates({"ood_pass": None}, config=ProgressionGateConfig())
    assert pending["all_required_progression_gates_pass"] is False
    assert pending["pending_reasons"]
    failed = evaluate_progression_gates({
        "ood_pass": False,
        "ood_fractional_improvement": 0.1,
        "complexity_penalized_delta_log_likelihood": 1.0,
        "independent_replication": True,
        "replication_provenance": "R",
        "falsification_protocol": "P",
        "falsification_status": "SURVIVED",
    })
    assert "ood_pass is false" in failed["hard_fail_reasons"]
