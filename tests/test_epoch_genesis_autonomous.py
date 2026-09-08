from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
EXT_SRC = ROOT / "extensions" / "ATLAS_AI_RESEARCH_EXTENSION_v0_10_0" / "src"
sys.path.insert(0, str(EXT_SRC))

from scienceatlas_ai.continual import AlphaLedger, GenesisState, RegionalMetaLearner
from scienceatlas_ai.epoch_genesis import (
    ESCALATE_AFTER,
    HOLD_AFTER,
    EpochGenesisDirector,
    EpochPlan,
    LedgerBinding,
    SequentialPermutationNullOwner,
    TriggerBudget,
    permutations_required,
)
from scienceatlas_ai.genesis_shells import SearchPricing, ShellLadder
from scienceatlas_ai.methodology import PipelineNullCalibrationOwner
from scienceatlas_ai.operator_genesis import OperatorGenesisOwner
from scienceatlas_ai.research_loop import (
    AcquisitionRequest,
    LoopBudget,
    LoopState,
    ResearchLoopOwner,
    source_spec,
)
from scienceatlas_ai.runtime import ScienceAtlasAI
from scienceatlas_ai.types import (
    EvidenceRecord,
    Observation,
    SemanticQuantity,
    ValidityDomain,
)

DOM = "blind"
UNIT = {"x": "m", "z": "m", "y": "J"}
VD = {
    "x": ValidityDomain(Fraction(1), Fraction(9)),
    "z": ValidityDomain(Fraction(1), Fraction(6)),
    "y": ValidityDomain(Fraction(-500), Fraction(500)),
}


def truth(x: Fraction, z: Fraction) -> Fraction:
    return Fraction(2) + 5 * x * z - Fraction(7, 1) / x


def q(axis: str, value: Fraction) -> SemanticQuantity:
    return SemanticQuantity(
        value=Fraction(value), semantic_type="scalar", domain=DOM,
        unit=UNIT[axis], validity=VD[axis],
    )


class BlindSource:
    spec = source_spec(
        source_id="blind-law-15-19",
        real_measurement=False,
        validity_domain="synthetic blind law for autonomous epoch acceptance only",
    )

    def __init__(self) -> None:
        self.n = 0

    def acquire(self, request: AcquisitionRequest):
        self.n += 1
        xs = {
            "x": Fraction(1 + (self.n * 3) % 9),
            "z": Fraction(1 + (self.n * 5) % 6),
        }
        if request.point is not None:
            for key, value in request.point.items():
                if key in xs:
                    xs[key] = value.value
        for axis in ("x", "z"):
            xs[axis] = min(max(xs[axis], VD[axis].minimum), VD[axis].maximum)
        y = truth(xs["x"], xs["z"])
        out = []
        for axis, value in (("x", xs["x"]), ("z", xs["z"]), ("y", y)):
            evidence = EvidenceRecord(
                evidence_id=f"e-{request.sample_id}-{axis}", source="blind-law-15-19",
                source_class="fixture", reliability_bp=10_000, claim=f"{axis}={value}",
            )
            out.append((Observation(request.sample_id, axis, q(axis, value), evidence.evidence_id), evidence))
        return tuple(out)


class NoiseSource(BlindSource):
    def acquire(self, request: AcquisitionRequest):
        acquired = super().acquire(request)
        seed = int(request.sample_id.encode().hex()[-6:], 16)
        y = Fraction((seed * 7919) % 401 - 200)
        out = []
        for observation, evidence in acquired:
            if observation.axis_id == "y":
                observation = Observation(request.sample_id, "y", q("y", y), evidence.evidence_id)
            out.append((observation, evidence))
        return tuple(out)


def build_director(*, compute_ceiling: int = 200):
    ai = ScienceAtlasAI()
    for axis in ("x", "z", "y"):
        ai.birth_axis(
            axis_id=axis, name=axis, semantic_type="scalar", domain=DOM,
            unit=UNIT[axis], validity=VD[axis],
        )
    genesis = GenesisState(ledger=AlphaLedger(bp_per_sample=400, max_balance_bp=200_000))
    meta = RegionalMetaLearner()
    loop = ResearchLoopOwner(budget=LoopBudget(
        max_steps=400, max_acquisitions=600, patience=99,
        min_success_gain_bp=9_000, evaluation_window=3, max_consecutive_stalls=99,
    ))
    binding = LedgerBinding(genesis.ledger)
    assert binding.scope_status == "SCOPED_UNBOUND"
    director = EpochGenesisDirector(
        ai=ai, genesis=genesis, meta=meta, loop=loop,
        genesis_owner=OperatorGenesisOwner(null_owner=SequentialPermutationNullOwner()),
        ledger_binding=binding,
        plan=EpochPlan(seed=17, grid_points=9),
        ladder=ShellLadder(), pricing=SearchPricing(),
        budget=TriggerBudget(
            stall_blocks=1, epoch_size=21, permutation_count=19,
            max_permutation_count=compute_ceiling,
        ),
    )
    assert director.binding.scope_status == "SCOPED"
    return ai, genesis, director


def test_pipeline_null_exact_p_and_resolution_gate():
    owner = PipelineNullCalibrationOwner()
    observed = Fraction(100)
    assert owner.assess(observed=observed, null_statistics=[Fraction(0)] * 18, alpha_bp=500)["status"] == "INSUFFICIENT_NULL_RESOLUTION"
    receipt = owner.assess(observed=observed, null_statistics=[Fraction(0)] * 19, alpha_bp=500)
    assert receipt["status"] == "PASS"
    assert receipt["empirical_p"] == {"numerator": 1, "denominator": 20}
    assert receipt["permutations_required_for_alpha"] == 19


def test_rational_schedule_has_correct_resolution_and_is_summable_prefix():
    budget = TriggerBudget(alpha_total_bp=500, permutation_count=19)
    expected = [39, 79, 159, 319, 639, 1279]
    assert [budget.permutations_for_attempt(i) for i in range(len(expected))] == expected
    assert [permutations_required(budget.level_for_attempt(i)) for i in range(len(expected))] == expected
    prefix = sum((budget.level_for_attempt(i) for i in range(9)), Fraction(0))
    assert prefix == Fraction(511, 10240)
    assert prefix < Fraction(1, 20)


def test_scoped_binding_is_fail_closed_until_director_binds_fingerprints():
    ledger = AlphaLedger()
    binding = LedgerBinding(ledger)
    assert binding.scope_status == "SCOPED_UNBOUND"
    with pytest.raises(ValueError):
        binding.grant(["s1"], domain="d", axes=("x",))


def test_duplicate_fingerprints_are_refused():
    class ScopedStub:
        balance_bp = 10_000
        def grant_for_samples(self, sample_ids, *, domain, axes, evidence_fingerprints):
            return self.balance_bp
        def can_spend(self, price_bp, *, domain=None, axes=None):
            return price_bp <= self.balance_bp
    binding = LedgerBinding(ScopedStub(), fingerprint_fn=lambda _sid: "same")
    with pytest.raises(ValueError):
        binding.grant(["s1", "s2"], domain="d", axes=("x",))


def test_blind_autonomous_path_reaches_honest_resource_frontier_without_false_claim():
    _ai, genesis, director = build_director(compute_ceiling=200)
    summary = director.run(
        source=BlindSource(), loop_state=LoopState(target_pool=("y",)),
        target_axis="y", input_axes=("x", "z"), max_cycles=14,
    )
    assert summary["scope_status"] == "SCOPED"
    assert summary["stopped_reason"] == "DEFERRED_RESOURCE"
    assert summary["promoted"] == 0
    assert list(genesis.active_owner_ids()) == []
    request = summary["resource_request"]
    assert request is not None
    assert request["permutation_count"] == 319
    assert request["compute_ceiling"] == 200
    assert request["level"] == {"numerator": 1, "denominator": 320}

    epochs = summary["epochs"]
    assert len(epochs) >= 3
    shells = [row["shell_index"] for row in epochs]
    assert shells == sorted(shells)
    for previous, current in zip(epochs, epochs[1:]):
        step = current["shell_index"] - previous["shell_index"]
        if previous["genesis_status"] in ESCALATE_AFTER:
            assert step == 1
        elif previous["genesis_status"] in HOLD_AFTER:
            assert step == 0

    splits = [row["split_digest"] for row in epochs]
    assert len(splits) == len(set(splits))
    seen: set[str] = set()
    for epoch in epochs:
        ids = set(epoch["sample_ids"])
        assert not (ids & seen)
        seen |= ids


def test_noise_is_not_promoted_before_the_same_resource_yield():
    _ai, genesis, director = build_director(compute_ceiling=200)
    summary = director.run(
        source=NoiseSource(), loop_state=LoopState(target_pool=("y",)),
        target_axis="y", input_axes=("x", "z"), max_cycles=8,
    )
    assert summary["promoted"] == 0
    assert list(genesis.active_owner_ids()) == []
    assert all(row["genesis_status"] != "PROMOTED" for row in summary["epochs"])
    assert summary["stopped_reason"] == "DEFERRED_RESOURCE"


def test_deferred_resource_yields_before_buying_another_confirmation_epoch():
    _ai, _genesis, director = build_director(compute_ceiling=80)
    source = BlindSource()
    summary = director.run(
        source=source, loop_state=LoopState(target_pool=("y",)),
        target_axis="y", input_axes=("x", "z"), max_cycles=12,
    )
    # Attempts 0 and 1 require 39 and 79 permutations; attempt 2 requires 159 and is deferred.
    assert summary["stopped_reason"] == "DEFERRED_RESOURCE"
    assert summary["resource_request"]["permutation_count"] == 159
    # Only successful searches create EpochRecord objects; no confirmation epoch is acquired after deferral.
    assert len(summary["epochs"]) == 2
