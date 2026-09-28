from source.lawspace.discriminating_experiment_autopilot import DiscriminatingExperimentAutopilotOwner


class FakeKernel:
    def design(self, **kwargs):
        protocol = {
            "measurement_id": "M-TEST",
            "observable_id": "OBS",
            "experiment_id": "Q-TEST",
            "initial_state": "S0",
            "actions": ["A"],
            "measurement_owner": "PENDING_TYPED_WORLD_ACTION_OR_EXPERIMENT_OWNER",
            "protocol_digest": "p" * 64,
            "required_result_fields": ["data_digest"],
        }
        return {
            "status": "DISCRIMINATING_EXPERIMENT_SELECTED",
            "digest": "d" * 64,
            "selection": {
                "status": "DISCRIMINATING_EXPERIMENT_SELECTED",
                "digest": "s" * 64,
                "frontier_freeze_digest": "f" * 64,
                "selected_experiment": {"experiment_id": "Q-TEST"},
                "theory_promotion_allowed": False,
            },
            "attestation_bridge": {
                "status": "WORLD_ATTESTATION_PENDING_EXTERNAL_MEASUREMENT",
                "measurement_protocol": protocol,
            },
        }


def test_autopilot_selects_and_queues_without_promotion(tmp_path, monkeypatch):
    monkeypatch.setenv("PHI_STATE_DIR", str(tmp_path / "state"))
    owner = DiscriminatingExperimentAutopilotOwner(tmp_path / "atlas", kernel=FakeKernel())
    out = owner.design(
        question="Q",
        candidate_theory={"digest": "c" * 64},
        baseline_theories=[{"digest": "b" * 64}],
        cost_budget=3.0,
    )
    assert out["status"] == "MEASUREMENT_REQUEST_READY"
    assert out["claim_boundary"]["theory_promotion_allowed"] is False
    queued = owner.queue(out)
    assert queued["queued"] is True
    assert queued["canonical_registry_mutated"] is False
    state = owner.queue_state()
    assert state["request_count"] == 1
    again = owner.queue(out)
    assert again["status"].startswith("IDEMPOTENT_")
