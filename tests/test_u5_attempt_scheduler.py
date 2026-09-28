from source.lawspace.u5_attempt_scheduler import U5AttemptConfig, U5AttemptScheduler


class FakeVerifier:
    def __init__(self, receipt): self.receipt = receipt
    def verify_bundle(self, bundle): return dict(self.receipt)


def candidate():
    return {
        "candidate_id": "C",
        "scientific_verification_bundle": {"x": 1},
        "ood_pass": True,
        "ood_fractional_improvement": 0.1,
        "complexity_penalized_delta_log_likelihood": 2.0,
        "independent_replication": True,
        "replication_provenance": "replicate-B",
        "falsification_protocol": "holdout-R2",
        "falsification_status": "SURVIVED",
    }


def test_config_forbids_registry_write_and_auto_promote():
    for kwargs in ({"write_canonical_registry": True}, {"auto_promote_scientific_law": True}):
        try:
            U5AttemptConfig(**kwargs).validate()
            assert False
        except PermissionError:
            pass


def test_world_attestation_missing_is_data_pending_not_fail():
    verifier = FakeVerifier({
        "overall_status": "PASS_ENGINE_OR_MODEL_VERIFICATION_WORLD_CLAIM_BLOCKED",
        "verification_digest": "a" * 64,
        "evidence_ready_for_domain": True,
        "world_attestation_ready": False,
        "scientific_candidate_allowed": False,
        "evidence_class": "INTERNAL_MEASUREMENT",
    })
    out = U5AttemptScheduler(verifier=verifier).attempt_one(candidate())
    assert out["result"]["outcome"] == "U5_DATA_PENDING"
    assert out["mutation_performed"] is False
    assert out["promotion_allowed"] is False


def test_real_verification_failure_is_u5_fail():
    verifier = FakeVerifier({
        "overall_status": "FAIL_EVIDENCE_SOURCE_VERIFICATION",
        "verification_digest": "b" * 64,
        "evidence_ready_for_domain": False,
        "world_attestation_ready": False,
        "scientific_candidate_allowed": False,
        "evidence_class": "EXTERNAL_SOURCE",
    })
    out = U5AttemptScheduler(verifier=verifier).attempt_one(candidate())
    assert out["result"]["outcome"] == "U5_FAIL"


def test_all_gates_and_world_evidence_can_reach_u5_pass_but_not_law():
    verifier = FakeVerifier({
        "overall_status": "PASS_SCIENTIFIC_VERIFICATION_PRECONDITION",
        "verification_digest": "c" * 64,
        "evidence_ready_for_domain": True,
        "world_attestation_ready": True,
        "scientific_candidate_allowed": True,
        "evidence_class": "EXTERNAL_SOURCE",
    })
    out = U5AttemptScheduler(verifier=verifier).attempt_one(candidate())
    assert out["result"]["outcome"] == "U5_PASS"
    assert out["claim_boundary"]["u5_pass_is_not_law"] is True
