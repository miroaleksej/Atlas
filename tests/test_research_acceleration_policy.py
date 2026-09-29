from source.lawspace.execution_policy import POLICY_SCHEMA, load_execution_policy, validate_execution_policy
from source.lawspace.research_progression_gates import ProgressionGateConfig, evaluate_progression_gates
from source.lawspace.schema import digest_payload


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


def _write_policy(root, *, schema=POLICY_SCHEMA, tamper=False):
    import json
    path = root / "data/runtime/EXECUTION_POLICY_CURRENT.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = {**_policy(), "schema": schema, "policy_id": "TEST"}
    doc["digest"] = digest_payload(doc)
    if tamper:
        doc["automatic_research_triage"] = False
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_persisted_policy_rejects_stale_schema(tmp_path):
    _write_policy(tmp_path, schema="phi-runtime-execution-policy/v3")
    try:
        load_execution_policy(tmp_path)
        assert False, "stale schema must fail closed"
    except PermissionError:
        pass


def test_persisted_policy_rejects_digest_tampering(tmp_path):
    _write_policy(tmp_path, tamper=True)
    try:
        load_execution_policy(tmp_path)
        assert False, "tampered policy must fail closed"
    except PermissionError:
        pass
