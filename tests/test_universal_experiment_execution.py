from copy import deepcopy
from pathlib import Path

import pytest

from evaluation.universal_experiment_qualification import (
    ControlledOracle,
    control_contract,
    jhtdb_case,
    run,
)
from source.lawspace.experiment_execution import TransientAcquisitionError, adapter_binding
from source.lawspace.long_horizon_scientific_cycle import LongHorizonBlindScientificCycleKernel
from source.lawspace.measurement_adapters import TabularJSONMeasurement


ROOT = Path(__file__).resolve().parents[1]


class FlakyControlledOracle(ControlledOracle):
    adapter_id = "FLAKY-CONTROLLED-TABULAR-ORACLE/1"

    def __init__(self):
        self.calls = 0

    def acquire(self, request, *, idempotency_key=None):
        self.calls += 1
        if self.calls < 3:
            raise TransientAcquisitionError("qualification-only transient failure")
        return super().acquire(request, idempotency_key=idempotency_key)


class WrongControlledOracle(ControlledOracle):
    adapter_id = "WRONG-CONTROLLED-TABULAR-ORACLE/1"


def setup_contract(source=None):
    kernel = LongHorizonBlindScientificCycleKernel(ROOT)
    source = source or ControlledOracle()
    measurement = TabularJSONMeasurement()
    contract = control_contract(kernel, source, measurement)
    return kernel, source, measurement, contract


def freeze(kernel, source, measurement, contract):
    return kernel.observational_experiments.freeze_execution_protocol(
        contract, source_adapter=source, measurement_adapter=measurement)


def test_universal_runtime_qualifies_two_source_classes_and_blocks_invalid_jhtdb_chart():
    result = run(ROOT)
    assert result["status"] == "PASS_UNIVERSAL_EXECUTION_QUALIFICATION"
    assert all(result["checks"].values())
    assert result["jhtdb_case_count"] == 27
    assert result["jhtdb"]["status"] == "EXECUTION_BLOCKED_PREFLIGHT"
    assert result["jhtdb"]["evidence_acquired"] is False
    assert result["scientific_law_established"] is False


def test_protocol_content_and_adapter_binding_are_immutable(tmp_path):
    kernel, source, measurement, contract = setup_contract()
    frozen = freeze(kernel, source, measurement, contract)
    tampered = deepcopy(frozen)
    tampered["contract"]["forms"][0]["coefficients"][1] = 999
    with pytest.raises(ValueError, match="digest"):
        kernel.execute_frozen_experiment(
            tampered, source_adapter=source, measurement_adapter=measurement, state_dir=tmp_path / "tampered")
    with pytest.raises(ValueError, match="source adapter binding"):
        kernel.execute_frozen_experiment(
            frozen, source_adapter=WrongControlledOracle(), measurement_adapter=measurement, state_dir=tmp_path / "wrong")


def test_retry_is_explicit_idempotent_and_checkpointed(tmp_path):
    source = FlakyControlledOracle()
    kernel, source, measurement, contract = setup_contract(source)
    contract["source_adapter"] = adapter_binding(source)
    frozen = freeze(kernel, source, measurement, contract)
    result = kernel.execute_frozen_experiment(
        frozen, source_adapter=source, measurement_adapter=measurement, state_dir=tmp_path / "state")
    assert result["evaluation"]["outcome"] == "ALL_FORMS_PASS"
    assert source.calls == 3
    replay = kernel.execute_frozen_experiment(
        frozen, source_adapter=source, measurement_adapter=measurement, state_dir=tmp_path / "state")
    assert replay == result
    assert source.calls == 3

    no_key = deepcopy(contract)
    del no_key["samples"][0]["idempotency_key"]
    with pytest.raises(ValueError, match="idempotency"):
        freeze(kernel, source, measurement, no_key)


def test_expected_sha_and_checkpoint_tampering_fail_closed(tmp_path):
    kernel, source, measurement, contract = setup_contract()
    wrong_hash = deepcopy(contract)
    wrong_hash["samples"][0]["expected_sha256"] = "0" * 64
    frozen_wrong = freeze(kernel, source, measurement, wrong_hash)
    with pytest.raises(ValueError, match="SHA-256"):
        kernel.execute_frozen_experiment(
            frozen_wrong, source_adapter=source, measurement_adapter=measurement, state_dir=tmp_path / "bad-hash")

    frozen = freeze(kernel, source, measurement, contract)
    state = tmp_path / "tamper-state"
    kernel.execute_frozen_experiment(
        frozen, source_adapter=source, measurement_adapter=measurement, state_dir=state)
    evidence_path = next(state.glob("*.bin"))
    evidence_path.write_bytes(evidence_path.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="SHA-256"):
        kernel.execute_frozen_experiment(
            frozen, source_adapter=source, measurement_adapter=measurement, state_dir=state)


def test_state_must_remain_outside_release_tree():
    kernel, source, measurement, contract = setup_contract()
    frozen = freeze(kernel, source, measurement, contract)
    with pytest.raises(ValueError, match="outside release"):
        kernel.execute_frozen_experiment(
            frozen, source_adapter=source, measurement_adapter=measurement,
            state_dir=ROOT / "state" / "forbidden-execution-test")


def test_jhtdb_contract_is_bound_to_legacy_freezes_and_uses_no_v6_heuristics():
    contract, source, measurement = jhtdb_case(ROOT)
    assert contract["legacy_protocol_digest"] == "c41038ac515826c3d6acf722488e788b13ad337e5beb40f9d903d7a401fda4bf"
    assert contract["legacy_child_freeze_digest"] == "6f3943151c8853f02bf0223ff1e54f7a9e3a27a8040b941be273bfcd74f9a6f6"
    assert measurement.adapter_id == "DNS-SGS-FROZEN-TRANSLATION-MOMENT/1"
    assert source.source_class == "OBSERVATIONAL_ARCHIVE"
    assert all(case["grid_points"] is None for case in contract["cases"])
