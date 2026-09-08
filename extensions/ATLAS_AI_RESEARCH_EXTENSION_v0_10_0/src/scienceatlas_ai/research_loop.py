"""The closed research loop for ScienceAtlas AI.

``ScienceAtlasAI.autonomous_research_step`` stops at representation proposals:
it never designs an experiment, never acquires anything, never records a
validation.  The arcs ``act -> measure -> learn -> modify strategy`` do not
exist in 0.7.0.  This module supplies them.

Two things are worth naming explicitly.

**The actuator is an owner, not an afterthought.**  Until 0.7.0 the only way an
observation could enter ``WorldModel`` was a manual ``observe()`` call, which
means the runtime had no organ for acquiring data.  ``ObservationSource`` is
that organ, under an ``OwnerSpec`` like everything else, and it declares whether
its output is a real measurement or a fixture.  A fixture source can drive the
loop for testing and can never produce a scientific claim.

**The measurement is prospective by construction.**  The loop designs an
experiment at the point of maximum disagreement, acquires the sample, and only
then compares predictions to truth.  The test point did not exist when the
hypotheses were fitted, so no held-out bookkeeping is required to keep it
honest: the ordering does that.  This is a much stronger test than any split of
an existing table, and it is the reason the loop is worth closing before
anything else.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Callable, Mapping, Protocol, Sequence

from .continual import GenesisState, RegionalMetaLearner
from .owners import OwnerSpec
from .provenance import digest_json
from .runtime import ScienceAtlasAI
from .types import (
    EvidenceRecord,
    ExperimentPlan,
    Observation,
    SemanticQuantity,
    ValidationOutcome,
)


# ---------------------------------------------------------------------------
# Actuator contract
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AcquisitionRequest:
    sample_id: str
    target_axis: str
    input_axes: tuple[str, ...]
    point: Mapping[str, SemanticQuantity] | None
    experiment_id: str | None

    def to_json(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "target_axis": self.target_axis,
            "input_axes": list(self.input_axes),
            "point": None if self.point is None else {k: self.point[k].to_json() for k in sorted(self.point)},
            "experiment_id": self.experiment_id,
        }


class ObservationSource(Protocol):
    """External source of new observations.

    ``point is None`` means the loop has nothing to intervene on yet and the
    source may choose where to sample (bootstrap).  Otherwise the source must
    realise the requested point, or refuse by returning an empty tuple.
    """

    spec: OwnerSpec

    def acquire(self, request: AcquisitionRequest) -> tuple[tuple[Observation, EvidenceRecord], ...]: ...


def source_spec(
    *,
    source_id: str,
    real_measurement: bool,
    validity_domain: str,
    cost_model: str = "one sample per acquisition",
) -> OwnerSpec:
    """Build the actuator's contract, with the fixture boundary in the spec itself."""
    return OwnerSpec(
        owner_id=f"observation-source-owner/{source_id}",
        capability=f"acquisition.observation_source.{source_id}",
        input_types=("acquisition_request",),
        output_types=("observation", "evidence_record"),
        validity_domain=validity_domain,
        uncertainty_contract=(
            "source declares per-observation uncertainty; the loop does not invent one"
        ),
        cost_model=cost_model,
        deterministic=False,
        replayable=False,
        falsification_contract=(
            "acquired observations are prospective tests of the standing hypotheses; "
            "a source declared as fixture can never produce a scientific claim; "
            "the source must preserve stable evidence_id identity across aliases of the same acquisition event"
        ),
        owner_kind="actuator" if real_measurement else "actuator_fixture",
    )


# ---------------------------------------------------------------------------
# Budget and loop state
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LoopBudget:
    max_steps: int = 50
    max_acquisitions: int = 200
    max_input_axes: int = 3
    patience: int = 3
    min_success_gain_bp: int = 1_000
    quarantine_epoch_length: int = 5
    max_consecutive_stalls: int = 8
    """Steps a target may go without an admissible experiment before retirement.

    Found the hard way: with declared validity domains the designer often returns
    UNKNOWN (no valid candidate intervention, or no jointly valid predictions),
    and without this counter the loop bootstraps forever and never reaches a
    verdict on the target. A stall is a result about the target too.
    """
    evaluation_window: int = 5
    """Prospective samples pooled before a validation outcome is emitted.

    A single prospective point is a terrible statistic: against a mean-predictor
    baseline, an overfitted model beats it roughly half the time by luck alone,
    so per-step credit would feed the meta-learner pure noise and no target
    would ever be retired.  Outcomes are therefore emitted per non-overlapping
    block of this many samples, on pooled squared error.
    """

    def __post_init__(self) -> None:
        if self.max_steps < 1 or self.max_acquisitions < 1:
            raise ValueError("loop budget must permit at least one step")
        if self.patience < 1:
            raise ValueError("patience must be positive")
        if not 0 <= self.min_success_gain_bp <= 10_000:
            raise ValueError("min_success_gain_bp out of range")
        if self.evaluation_window < 2:
            raise ValueError("a validation window of one sample is not a measurement")

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scienceatlas-ai-loop-budget-v1",
            "max_steps": self.max_steps,
            "max_acquisitions": self.max_acquisitions,
            "max_input_axes": self.max_input_axes,
            "patience": self.patience,
            "min_success_gain_bp": self.min_success_gain_bp,
            "quarantine_epoch_length": self.quarantine_epoch_length,
            "max_consecutive_stalls": self.max_consecutive_stalls,
            "evaluation_window": self.evaluation_window,
        }


@dataclass
class LoopState:
    target_pool: tuple[str, ...] = ()
    step: int = 0
    acquisitions: int = 0
    consecutive_low: dict[str, int] = field(default_factory=dict)
    consecutive_stall: dict[str, int] = field(default_factory=dict)
    exhausted: list[str] = field(default_factory=list)
    last_gain_bp: dict[str, int] = field(default_factory=dict)
    windows: dict[str, list[list[int]]] = field(default_factory=dict)
    receipt_head: str = "00" * 32

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scienceatlas-ai-loop-state-v1",
            "target_pool": list(self.target_pool),
            "step": self.step,
            "acquisitions": self.acquisitions,
            "consecutive_low": {k: self.consecutive_low[k] for k in sorted(self.consecutive_low)},
            "consecutive_stall": {k: self.consecutive_stall[k] for k in sorted(self.consecutive_stall)},
            "exhausted": sorted(self.exhausted),
            "last_gain_bp": {k: self.last_gain_bp[k] for k in sorted(self.last_gain_bp)},
            "windows": {k: [list(row) for row in self.windows[k]] for k in sorted(self.windows)},
            "receipt_head": self.receipt_head,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "LoopState":
        return cls(
            target_pool=tuple(str(x) for x in payload.get("target_pool", [])),
            step=int(payload.get("step", 0)),
            acquisitions=int(payload.get("acquisitions", 0)),
            consecutive_low={str(k): int(v) for k, v in payload.get("consecutive_low", {}).items()},
            consecutive_stall={str(k): int(v) for k, v in payload.get("consecutive_stall", {}).items()},
            exhausted=[str(x) for x in payload.get("exhausted", [])],
            last_gain_bp={str(k): int(v) for k, v in payload.get("last_gain_bp", {}).items()},
            windows={str(k): [[int(x) for x in row] for row in v] for k, v in payload.get("windows", {}).items()},
            receipt_head=str(payload.get("receipt_head", "00" * 32)),
        )


RegimeResolver = Callable[[str], str]


# ---------------------------------------------------------------------------
# The loop owner
# ---------------------------------------------------------------------------


class ResearchLoopOwner:
    """observe -> hypothesize -> act -> measure -> learn -> modify strategy -> repeat."""

    spec = OwnerSpec(
        owner_id="research-loop-owner/0.1.0",
        capability="research.autonomous_loop",
        input_types=("world_model", "acquisition_source", "loop_budget"),
        output_types=("loop_step_receipt", "validation_outcome"),
        validity_domain=(
            "single-domain axes already present in the representation graph; "
            "one intervention axis per step"
        ),
        uncertainty_contract=(
            "prediction gain is measured on a sample acquired after the hypotheses were "
            "fitted; no retrospective split is used or claimed"
        ),
        cost_model="one acquisition per step plus hypothesis refit over observed rows",
        deterministic=False,
        replayable=False,
        falsification_contract=(
            "a target is retired when the standing hypotheses fail to beat the mean "
            "predictor on newly acquired samples for `patience` consecutive steps"
        ),
        owner_kind="loop",
    )

    def __init__(
        self,
        *,
        budget: LoopBudget | None = None,
        regime_of: RegimeResolver | None = None,
    ) -> None:
        self.budget = budget or LoopBudget()
        self.regime_of = regime_of or (lambda sample_id: "default")

    # -- scheduling --------------------------------------------------------

    def _select_target(self, ai: ScienceAtlasAI, state: LoopState) -> str | None:
        available = [t for t in state.target_pool if t not in state.exhausted]
        if not available:
            return None
        # Fewest observations first: the loop spends its budget where it is
        # least informed, not where it is already succeeding.
        ranked = sorted(available, key=lambda t: (len(ai.world.values_for_axis(t)), t))
        return ranked[0]

    def _select_input_axes(self, ai: ScienceAtlasAI, target_axis: str) -> tuple[str, ...]:
        target = ai.representation.axes[target_axis]
        scored: list[tuple[int, str]] = []
        for axis_id, axis in ai.representation.axes.items():
            if axis_id == target_axis or axis.domain != target.domain:
                continue
            count = len(ai.world.values_for_axis(axis_id))
            if count >= 2:
                scored.append((-count, axis_id))
        return tuple(axis_id for _, axis_id in sorted(scored)[: self.budget.max_input_axes])

    # -- acquisition -------------------------------------------------------

    def _acquire(
        self,
        ai: ScienceAtlasAI,
        source: ObservationSource,
        request: AcquisitionRequest,
    ) -> tuple[str, tuple[str, ...], str]:
        """Realise a request, derive stable evidence identity, and admit it fail-closed.

        ``sample_id`` is deliberately excluded from the evidence fingerprint.  A
        caller cannot mint fresh alpha by re-labelling the same acquisition.  The
        fingerprint is anchored in the acquisition owner, upstream evidence IDs,
        evidence claims/statuses and measured semantic quantities.  Independence
        still remains an upstream scientific/source assertion; the ledger records
        identity faithfully but cannot prove independence from payload bytes.
        """
        acquired = source.acquire(request)
        if not acquired:
            return ("REFUSED_BY_SOURCE", (), "")
        required = set(request.input_axes) | {request.target_axis}
        seen: set[str] = set()
        for observation, _ in acquired:
            if observation.sample_id != request.sample_id:
                return ("REJECTED_SAMPLE_ID_MISMATCH", (), "")
            seen.add(observation.axis_id)
        if not required.issubset(seen):
            return ("REJECTED_INCOMPLETE_SAMPLE", (), "")

        identity_payload = {
            "source_owner_id": source.spec.owner_id,
            "observations": sorted(
                (
                    {
                        "axis_id": observation.axis_id,
                        "quantity": observation.quantity.to_json(),
                        "evidence_id": observation.evidence_id,
                    }
                    for observation, _ in acquired
                ),
                key=lambda row: (str(row["axis_id"]), str(row["evidence_id"])),
            ),
            "evidence": sorted(
                (
                    {
                        "evidence_id": evidence.evidence_id,
                        "source": evidence.source,
                        "source_class": evidence.source_class,
                        "claim": evidence.claim,
                        "status": evidence.status,
                    }
                    for _, evidence in acquired
                ),
                key=lambda row: (str(row["source"]), str(row["evidence_id"]), str(row["claim"])),
            ),
        }
        evidence_fingerprint = digest_json(
            identity_payload,
            namespace=b"SCIENCEATLAS_AI_ACQUISITION_EVIDENCE_IDENTITY_V1",
        )
        for observation, evidence in acquired:
            ai.observe(observation, evidence)
        return ("ACQUIRED", tuple(sorted(seen)), evidence_fingerprint)

    # -- measurement -------------------------------------------------------

    @staticmethod
    def _baseline_sse(previous_values: Sequence[Fraction], actual: Fraction) -> Fraction | None:
        """Mean predictor over what was known before the acquisition."""
        if not previous_values:
            return None
        mean = sum(previous_values, Fraction(0)) / len(previous_values)
        return (actual - mean) ** 2

    def _measure(
        self,
        ai: ScienceAtlasAI,
        plan: ExperimentPlan,
        point: Mapping[str, Fraction],
        actual: Fraction,
        previous_values: Sequence[Fraction],
    ) -> dict[str, Any] | None:
        baseline = self._baseline_sse(previous_values, actual)
        if baseline is None:
            return None
        best: tuple[Fraction, str] | None = None
        errors: dict[str, Fraction] = {}
        for hid in plan.hypothesis_ids:
            hypothesis = ai.hypotheses.get(hid)
            if hypothesis is None:
                continue
            try:
                owner = ai.owner_bus.get(hypothesis.owner_id)
                predicted = owner.predict(hypothesis, dict(point))
            except (ValueError, ZeroDivisionError, KeyError, TypeError):
                continue
            err = (actual - predicted) ** 2
            errors[hid] = err
            if best is None or err < best[0] or (err == best[0] and hid < best[1]):
                best = (err, hid)
        if best is None:
            return None
        best_err, best_hid = best
        if baseline <= 0:
            gain_bp = 0
        else:
            raw = (Fraction(1) - best_err / baseline) * 10_000
            gain_bp = max(0, min(10_000, int(raw)))
        return {
            "best_hypothesis_id": best_hid,
            "best_owner_id": ai.hypotheses[best_hid].owner_id,
            "best_family": ai.hypotheses[best_hid].family,
            "point_gain_bp": gain_bp,
            "best_error": {"numerator": best_err.numerator, "denominator": best_err.denominator},
            "baseline_error": {"numerator": baseline.numerator, "denominator": baseline.denominator},
            "errors": {hid: {"numerator": errors[hid].numerator, "denominator": errors[hid].denominator} for hid in sorted(errors)},
        }

    # -- one full turn -----------------------------------------------------

    def step(
        self,
        *,
        ai: ScienceAtlasAI,
        source: ObservationSource,
        state: LoopState,
        meta: RegionalMetaLearner,
        genesis: GenesisState | None = None,
    ) -> dict[str, Any]:
        state.step += 1
        payload: dict[str, Any] = {
            "schema": "scienceatlas-ai-loop-step-v1",
            "step": state.step,
            "previous_receipt": state.receipt_head,
            "source_owner_id": source.spec.owner_id,
            "source_kind": source.spec.owner_kind,
        }

        target = self._select_target(ai, state)
        if target is None:
            return self._seal(state, {**payload, "status": "STOP_ALL_TARGETS_EXHAUSTED"})
        payload["target_axis"] = target
        domain = ai.representation.axes[target].domain
        payload["domain"] = domain

        axes = self._select_input_axes(ai, target)
        payload["input_axes"] = list(axes)
        sample_id = f"loop-{state.step:06d}"

        # observe / hypothesize
        hypotheses = ai.generate_hypotheses(input_axes=axes, target_axis=target) if axes else ()
        payload["hypothesis_count"] = len(hypotheses)

        plan = None
        if len(hypotheses) >= 2:
            ai.evaluate_hypotheses(input_axes=axes, target_axis=target)
            plan = ai.design_multiaxis_experiment(
                input_axes=axes,
                target_axis=target,
                intervention_axis=axes[0],
            )

        if plan is None:
            # act (bootstrap): the loop is not informed enough to intervene.
            status, covered, evidence_fingerprint = self._acquire(
                ai,
                source,
                AcquisitionRequest(
                    sample_id=sample_id,
                    target_axis=target,
                    input_axes=axes,
                    point=None,
                    experiment_id=None,
                ),
            )
            if status == "ACQUIRED":
                state.acquisitions += 1
                if genesis is not None:
                    genesis.ledger.grant_for_samples(
                        [sample_id], domain=domain, axes=(target, *covered),
                        evidence_fingerprints={sample_id: evidence_fingerprint},
                    )
            stalls = state.consecutive_stall.get(target, 0) + 1
            state.consecutive_stall[target] = stalls
            extra: dict[str, Any] = {"consecutive_stalls": stalls}
            if stalls >= self.budget.max_consecutive_stalls and target not in state.exhausted:
                state.exhausted.append(target)
                state.exhausted.sort()
                extra["strategy_change"] = {
                    "retired_target": target,
                    "reason": "no admissible experiment could be designed",
                }
            return self._seal(state, {**payload, "status": f"BOOTSTRAP_{status}", "axes_covered": list(covered), **extra})

        state.consecutive_stall[target] = 0
        payload["experiment_id"] = plan.experiment_id
        payload["disagreement"] = {
            "numerator": plan.disagreement.numerator,
            "denominator": plan.disagreement.denominator,
        }

        point_quantities: dict[str, SemanticQuantity] = dict(plan.context_values)
        point_quantities[plan.input_axis] = plan.input_value
        previous_values = list(ai.world.values_for_axis(target))

        # act
        status, covered, evidence_fingerprint = self._acquire(
            ai,
            source,
            AcquisitionRequest(
                sample_id=sample_id,
                target_axis=target,
                input_axes=plan.input_axes,
                point=point_quantities,
                experiment_id=plan.experiment_id,
            ),
        )
        if status != "ACQUIRED":
            return self._seal(state, {**payload, "status": f"ACT_{status}"})
        state.acquisitions += 1

        # measure
        realised = ai.world.values_by_sample(target).get(sample_id)
        realised_point = {axis_id: ai.world.values_by_sample(axis_id).get(sample_id) for axis_id in plan.input_axes}
        if realised is None or any(v is None for v in realised_point.values()):
            return self._seal(state, {**payload, "status": "MEASURE_INCOMPLETE_SAMPLE"})
        measurement = self._measure(
            ai,
            plan,
            {k: v for k, v in realised_point.items() if v is not None},
            realised,
            previous_values,
        )
        if measurement is None:
            return self._seal(state, {**payload, "status": "MEASURE_NO_USABLE_PREDICTION"})
        payload["measurement"] = measurement

        # accumulate: one prospective point is evidence, not a verdict
        best_owner_id = str(measurement["best_owner_id"])
        window_key = f"{target}|{best_owner_id}"
        window = state.windows.setdefault(window_key, [])
        window.append([
            int(measurement["best_error"]["numerator"]),
            int(measurement["best_error"]["denominator"]),
            int(measurement["baseline_error"]["numerator"]),
            int(measurement["baseline_error"]["denominator"]),
        ])
        if len(window) < self.budget.evaluation_window:
            if genesis is not None:
                genesis.ledger.grant_for_samples(
                    [sample_id], domain=domain, axes=(target, *covered),
                    evidence_fingerprints={sample_id: evidence_fingerprint},
                )
            payload["learning"] = {
                "status": "ACCUMULATING",
                "window_key": window_key,
                "window_filled": len(window),
                "window_required": self.budget.evaluation_window,
            }
            return self._seal(state, {**payload, "status": "COMPLETE_ACCUMULATING"})

        # learn: pooled squared error over a closed, non-overlapping block
        model_sse = sum((Fraction(a, b) for a, b, _, _ in window), Fraction(0))
        baseline_sse = sum((Fraction(c, d) for _, _, c, d in window), Fraction(0))
        state.windows[window_key] = []
        if baseline_sse <= 0:
            gain_bp = 0
        else:
            gain_bp = max(0, min(10_000, int((Fraction(1) - model_sse / baseline_sse) * 10_000)))
        success = gain_bp >= self.budget.min_success_gain_bp
        outcome = ValidationOutcome(
            experiment_id=plan.experiment_id,
            owner_id=best_owner_id,
            success=success,
            prediction_gain_bp=gain_bp,
            notes=f"pooled over {self.budget.evaluation_window} prospective samples",
        )
        scalar_score = ai.record_validation(
            outcome,
            validated_family=str(measurement["best_family"]) if success else None,
        )
        regime = self.regime_of(sample_id)
        regional_score = meta.update(outcome, regime=regime, domain=domain, family=str(measurement["best_family"]))
        payload["learning"] = {
            "status": "VALIDATED_BLOCK",
            "regime": regime,
            "success": success,
            "window_gain_bp": gain_bp,
            "window_size": self.budget.evaluation_window,
            "scalar_strategy_score_bp": scalar_score,
            "regional_strategy_score_bp": regional_score,
        }

        if genesis is not None:
            genesis.ledger.grant_for_samples(
                [sample_id], domain=domain, axes=(target, *covered),
                evidence_fingerprints={sample_id: evidence_fingerprint},
            )
            falsification = genesis.observe_outcome(outcome)
            if falsification is not None:
                payload["falsification"] = falsification
            if state.step % self.budget.quarantine_epoch_length == 0:
                genesis.tick_epoch()
                payload["quarantine_ticked"] = True

        # modify strategy
        if success:
            state.consecutive_low[target] = 0
        else:
            state.consecutive_low[target] = state.consecutive_low.get(target, 0) + 1
            if state.consecutive_low[target] >= self.budget.patience and target not in state.exhausted:
                state.exhausted.append(target)
                state.exhausted.sort()
                payload["strategy_change"] = {"retired_target": target, "reason": "patience exhausted"}
        state.last_gain_bp[target] = gain_bp

        return self._seal(state, {**payload, "status": "COMPLETE"})

    def _seal(self, state: LoopState, payload: Mapping[str, Any]) -> dict[str, Any]:
        receipt = dict(payload)
        receipt["digest"] = digest_json(receipt, namespace=b"SCIENCEATLAS_AI_LOOP_STEP_V1")
        state.receipt_head = receipt["digest"]
        return receipt

    # -- driving -----------------------------------------------------------

    def should_stop(self, state: LoopState) -> str | None:
        if state.step >= self.budget.max_steps:
            return "STEP_BUDGET_EXHAUSTED"
        if state.acquisitions >= self.budget.max_acquisitions:
            return "ACQUISITION_BUDGET_EXHAUSTED"
        if state.target_pool and all(t in state.exhausted for t in state.target_pool):
            return "ALL_TARGETS_RETIRED"
        return None

    def run(
        self,
        *,
        ai: ScienceAtlasAI,
        source: ObservationSource,
        state: LoopState,
        meta: RegionalMetaLearner,
        genesis: GenesisState | None = None,
    ) -> dict[str, Any]:
        receipts: list[dict[str, Any]] = []
        stop = self.should_stop(state)
        while stop is None:
            receipt = self.step(ai=ai, source=source, state=state, meta=meta, genesis=genesis)
            receipts.append(receipt)
            if str(receipt.get("status", "")).startswith("STOP_"):
                stop = str(receipt["status"])
                break
            stop = self.should_stop(state)
        summary = {
            "schema": "scienceatlas-ai-loop-run-v1",
            "stop_reason": stop,
            "steps_executed": len(receipts),
            "acquisitions": state.acquisitions,
            "retired_targets": sorted(state.exhausted),
            "receipt_head": state.receipt_head,
            "statuses": [str(r.get("status")) for r in receipts],
        }
        summary["digest"] = digest_json(summary, namespace=b"SCIENCEATLAS_AI_LOOP_RUN_V1")
        return summary


__all__ = [
    "AcquisitionRequest",
    "LoopBudget",
    "LoopState",
    "ObservationSource",
    "ResearchLoopOwner",
    "source_spec",
]
