"""Autonomous operator genesis on fresh exchangeable epochs.

This module is **additive**.  It overwrites no file in the sealed tree.  The
previous attempt shipped a rewritten ``research_loop.py`` and silently deleted
the 15.18 evidence-fingerprint code, reverting scoped alpha to an unscoped
``grant_for_samples([sample_id])`` call; the resulting run showed a healthy
balance and refused every search, because the ledger correctly declined to spend
legacy credit on a scoped search.  Nothing here rewrites the loop.  Epoch acquisition delegates to the sealed
``ResearchLoopOwner._acquire`` boundary so evidence identity and admission remain
authoritative in one place.

**Epochs come first, because they are what makes the null valid.**

The earlier design rebuilt FIT/SEAL from the whole accumulated randomized
history on every escalation.  That means the seal set of the G0 search, which
produced the decision to escalate to G1, is partly reused as fit and seal data
for G1.  ``null_replay`` re-runs the current search under permutation but never
re-runs the *history of shell selection*, so the null stops covering the whole
pipeline exactly when escalation becomes automatic.  Every gate would still
report PASS.

So the order is fixed and enforced here:

    trigger decides  ->  shell Gk is fixed and sealed
                     ->  a NEW randomized epoch is acquired
                     ->  that epoch alone is split into FIT/SEAL
                     ->  genesis runs at Gk, null over that epoch only
                     ->  the outcome decides the next shell
                     ->  which requires another new epoch

No observation that took part in a decision is ever used to test the search that
decision authorised.  This costs data: four shells at ``epoch_size`` points each
is the real price of autonomy, and it should be priced against a real measurement
backend before ``bp_per_sample`` is fixed.

**Scoped alpha is required, not optional.**  ``LedgerBinding`` inspects the
ledger at construction and refuses to run against one that does not accept
domain and axis scoping, unless the caller explicitly declares an unscoped run.
An unscoped run is recorded as such in every epoch record and can never be
mistaken for a scoped one afterwards.
"""
from __future__ import annotations

import inspect
import random
from dataclasses import dataclass, field
from fractions import Fraction
from math import ceil
from typing import Any, Mapping, Sequence

from .continual import GenesisState, RegionalMetaLearner
from .genesis_shells import GenesisShell, SearchPricing, ShellLadder, search_context_key
from .operator_genesis import GenesisSplit, OperatorGenesisOwner
from .owners import OwnerSpec
from .provenance import digest_json
from .research_loop import AcquisitionRequest, ObservationSource, ResearchLoopOwner
from .types import SemanticQuantity, ValidityDomain


ESCALATE_AFTER = frozenset({"REJECTED_NO_ADMISSIBLE_FAMILY", "REJECTED_BELOW_MARGIN"})
HOLD_AFTER = frozenset({
    "REJECTED_NULL_FAIL",
    "REJECTED_NULL_INSUFFICIENT_NULL_RESOLUTION",
    "REJECTED_NULL_INSUFFICIENT_NULL",
})

RULE_ORDER = (
    "MODEL_INSUFFICIENCY_SIGNAL",
    "EPOCH_FRESHNESS",
    "ESCALATION_ADMISSIBILITY",
    "SCOPED_ALPHA_AFFORDABILITY",
)


# ---------------------------------------------------------------------------
# Ledger binding: scoped or explicitly declared unscoped
# ---------------------------------------------------------------------------


@dataclass
class LedgerBinding:
    """Adapter to the alpha ledger that refuses to silently lose scoping.

    Three things this got wrong before, all found by running it against the real
    15.18 ledger rather than against a local copy:

    * ``_accepts_scope`` accepted any ledger exposing ``domain`` and ``axes`` and
      then called it with ``evidence_fingerprint=`` (singular). The 15.18 API
      takes ``evidence_fingerprints={sample_id: fingerprint}``. The probe said
      SCOPED and the call raised ``TypeError``.
    * The fallback chain tried a second keyword spelling and then an unscoped
      call, which is exactly how scoping gets lost without anyone noticing.
      There is no fallback now: a signature that is not understood is refused.
    * Fingerprints were minted here from scheduler metadata. They must come from
      the acquisition boundary that already exists in the sealed
      ``research_loop``, which derives identity from the source owner, the
      measured quantities, upstream evidence ids and claims, and deliberately
      excludes the caller-chosen ``sample_id``. This class does not compute
      identity; it requires a callable that does.
    """

    ledger: Any
    fingerprint_fn: Any = None
    allow_unscoped: bool = False
    scoped: bool = field(init=False, default=False)
    _grant_kwarg: str = field(init=False, default="")

    def __post_init__(self) -> None:
        self._grant_kwarg = self._probe()
        self.scoped = bool(self._grant_kwarg)
        if not self.scoped and not self.allow_unscoped:
            raise ValueError(
                "alpha ledger does not expose a recognised evidence-scoped "
                "grant_for_samples(domain=, axes=, evidence_fingerprints=); pass "
                "allow_unscoped=True only for a legacy ledger, and expect every "
                "receipt to be marked UNSCOPED_LEDGER"
            )
        # A scoped binding may be constructed before its fingerprint source
        # exists: the Director binds the sealed acquisition boundary in its own
        # __init__, which cannot run before the binding is passed to it. Raising
        # here made that impossible and contradicted the claim that binding is
        # automatic. The refusal moves to grant(), where it actually matters.

    def _probe(self) -> str:
        try:
            params = inspect.signature(self.ledger.grant_for_samples).parameters
        except (TypeError, ValueError):
            return ""
        names = set(params)
        if "domain" not in names or "axes" not in names:
            return ""
        for candidate in ("evidence_fingerprints", "evidence_fingerprint_by_sample"):
            if candidate in names:
                return candidate
        return ""

    @property
    def scope_status(self) -> str:
        if not self.scoped:
            return "UNSCOPED_LEDGER"
        return "SCOPED" if self.fingerprint_fn is not None else "SCOPED_UNBOUND"

    def bind_fingerprints(self, fingerprint_fn: Any) -> None:
        """Attach the acquisition boundary's fingerprint source, once."""
        if self.fingerprint_fn is not None:
            raise ValueError("fingerprint source is already bound")
        self.fingerprint_fn = fingerprint_fn

    def grant(self, sample_ids: Sequence[str], *, domain: str, axes: Sequence[str]) -> int:
        if not self.scoped:
            return self.ledger.grant_for_samples(list(sample_ids))
        if self.fingerprint_fn is None:
            raise ValueError(
                "scoped grant attempted before an evidence fingerprint source was "
                "bound; the Director binds the sealed acquisition boundary at init"
            )
        fingerprints = {sid: self.fingerprint_fn(sid) for sid in sample_ids}
        missing = [sid for sid, fp in fingerprints.items() if not fp]
        if missing:
            raise ValueError(f"acquisition boundary produced no evidence fingerprint for {missing[:3]}")
        if len(set(fingerprints.values())) != len(fingerprints):
            raise ValueError("distinct samples share an evidence fingerprint; independence is not established")
        return self.ledger.grant_for_samples(
            list(sample_ids), domain=domain, axes=tuple(sorted(axes)),
            **{self._grant_kwarg: fingerprints},
        )

    def can_spend(self, price_bp: int, *, domain: str, axes: Sequence[str]) -> bool:
        if self.scoped:
            return bool(self.ledger.can_spend(price_bp, domain=domain, axes=tuple(sorted(axes))))
        return bool(self.ledger.can_spend(price_bp))

    @property
    def balance_bp(self) -> int:
        return int(self.ledger.balance_bp)


# ---------------------------------------------------------------------------
# Null at a rational level
# ---------------------------------------------------------------------------


def permutations_required(level: Fraction) -> int:
    """Smallest N with 1/(N+1) <= level.  ``ceil``, not floor.

    The floor form ``10000 // alpha_bp - 1`` is off by one wherever the division
    is inexact: at 62 bp it yields 160, whose resolution 1/161 is still coarser
    than the level, so the search pays for 160 permutations and is then told the
    null had insufficient resolution.
    """
    return max(1, ceil(Fraction(1, 1) / level) - 1)


class SequentialPermutationNullOwner:
    """Whole-pipeline permutation null judged at an exact rational level.

    Named for what it is. It is a sequential permutation test under a summable
    level schedule, not an anytime-valid procedure; its own receipt says
    ``is_anytime_valid: False``. The Anytime name belongs to a future e-process
    and should not be spent on this.

    Separate from the sealed ``PipelineNullCalibrationOwner`` for one reason: the
    sealed one takes its level in integer basis points, and an integer-valued
    alpha schedule cannot be summable.  Any positive integer sequence diverges,
    so a halving schedule expressed in basis points floors at 1 bp and its total
    type-I error becomes unbounded; the only thing hiding that was the compute
    ceiling of 4095 permutations, which made the proof depend on a resource
    limit.  Levels here are ``Fraction``, so the schedule really is infinite and
    the compute ceiling goes back to being a scheduling matter.

    The sealed owner still needs its own fix — deciding PASS by quantile
    exceedance while computing an exact p-value it then ignores is a bug
    independent of this module.
    """

    spec = OwnerSpec(
        owner_id="sequential-permutation-null-owner/0.1.0",
        capability="methodology.pipeline_null.rational_level",
        input_types=("whole_pipeline_statistic", "permutation_statistics", "rational_level"),
        output_types=("familywise_null_receipt",),
        validity_domain="same adaptive pipeline rerun on permuted target at a preregistered rational level",
        uncertainty_contract=(
            "exact permutation p-value; a level finer than 1/(N+1) is reported as "
            "insufficient resolution rather than decided"
        ),
        cost_model="pipeline_cost * permutation_count",
        deterministic=True,
        replayable=True,
        falsification_contract="candidate loses calibrated status when p exceeds the level for its attempt",
        owner_kind="methodology",
    )

    def __init__(self, level: Fraction | None = None) -> None:
        self.level = level or Fraction(500, 10_000)

    def set_level(self, level: Fraction) -> None:
        if not 0 < level < 1:
            raise ValueError("null level must be a fraction in (0,1)")
        self.level = level

    def assess(self, *, observed: Fraction, null_statistics: Sequence[Fraction], alpha_bp: int = 500) -> dict[str, Any]:
        # alpha_bp is accepted for signature compatibility and deliberately not
        # used: the statistical level is self.level, set by the alpha schedule.
        # The integer value that reaches here is a ledger price, not a level.
        del alpha_bp
        level = self.level
        if not null_statistics:
            payload: dict[str, Any] = {"status": "UNKNOWN_NO_NULL_RUNS"}
        else:
            stats = sorted(Fraction(v) for v in null_statistics)
            exceed = sum(1 for value in stats if value >= observed)
            p = Fraction(exceed + 1, len(stats) + 1)
            resolution = Fraction(1, len(stats) + 1)
            if resolution > level:
                status = "INSUFFICIENT_NULL_RESOLUTION"
            else:
                status = "PASS" if p <= level else "FAIL"
            payload = {
                "status": status,
                "observed": {"numerator": observed.numerator, "denominator": observed.denominator},
                "permutation_count": len(stats),
                "level": {"numerator": level.numerator, "denominator": level.denominator},
                "empirical_p": {"numerator": p.numerator, "denominator": p.denominator},
                "min_achievable_p": {"numerator": resolution.numerator, "denominator": resolution.denominator},
                "permutations_required_for_level": permutations_required(level),
            }
        payload["schema"] = "scienceatlas-ai-sequential-permutation-null-v1"
        payload["claim_boundary"] = {
            "permutation_pass_means_law": False,
            "sequential_control": "per-target union bound over a summable level schedule",
            "is_anytime_valid": False,
        }
        payload["digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_SEQUENTIAL_PERMUTATION_NULL_V1")
        return payload


# ---------------------------------------------------------------------------
# Epochs
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EpochPlan:
    """Preregistered exchangeable sampling plan for one epoch.

    Deterministic in ``(seed, epoch_index, position, axis)``, uniform over a
    canonical grid inside the declared validity domain.  An axis without declared
    bounds is refused rather than sampled from an invented range: exchangeability
    is a claim about a population, and an unbounded axis does not describe one.
    """

    seed: int = 0
    grid_points: int = 16

    def __post_init__(self) -> None:
        if self.grid_points < 2:
            raise ValueError("an epoch plan needs at least two grid points")

    def point(
        self,
        *,
        epoch_index: int,
        position: int,
        axes: Sequence[str],
        validity: Mapping[str, ValidityDomain],
    ) -> dict[str, Fraction] | None:
        out: dict[str, Fraction] = {}
        for axis_id in sorted(axes):
            domain = validity.get(axis_id)
            if domain is None or domain.minimum is None or domain.maximum is None:
                return None
            draw = int(
                digest_json(
                    {"seed": self.seed, "epoch": epoch_index, "pos": position, "axis": axis_id},
                    namespace=b"SCIENCEATLAS_AI_EPOCH_PLAN_V1",
                )[:8],
                16,
            )
            step = draw % self.grid_points
            span = domain.maximum - domain.minimum
            out[axis_id] = domain.minimum + span * Fraction(step, self.grid_points - 1)
        return out

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scienceatlas-ai-epoch-plan-v1",
            "seed": self.seed,
            "grid_points": self.grid_points,
        }

    @property
    def digest(self) -> str:
        return digest_json(self.to_json(), namespace=b"SCIENCEATLAS_AI_EPOCH_PLAN_V1")


@dataclass(frozen=True, slots=True)
class EpochRecord:
    """One confirmation epoch: what was decided, then what was acquired."""

    epoch_index: int
    target_axis: str
    input_axes: tuple[str, ...]
    domain: str
    shell_index: int
    decision_digest: str
    plan_digest: str
    sample_ids: tuple[str, ...]
    split_digest: str
    scope_status: str
    genesis_status: str
    sealed_gain_bp: int
    alpha_price_bp: int
    certificate_digest: str

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scienceatlas-ai-epoch-record-v1",
            "epoch_index": self.epoch_index,
            "target_axis": self.target_axis,
            "input_axes": list(self.input_axes),
            "domain": self.domain,
            "shell_index": self.shell_index,
            "decision_digest": self.decision_digest,
            "plan_digest": self.plan_digest,
            "sample_ids": list(self.sample_ids),
            "split_digest": self.split_digest,
            "scope_status": self.scope_status,
            "genesis_status": self.genesis_status,
            "sealed_gain_bp": self.sealed_gain_bp,
            "alpha_price_bp": self.alpha_price_bp,
            "certificate_digest": self.certificate_digest,
            "ordering_claim": "shell fixed before acquisition; epoch used by exactly one search",
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "EpochRecord":
        return cls(
            epoch_index=int(payload["epoch_index"]),
            target_axis=str(payload["target_axis"]),
            input_axes=tuple(str(a) for a in payload.get("input_axes", [])),
            domain=str(payload.get("domain", "")),
            shell_index=int(payload.get("shell_index", 0)),
            decision_digest=str(payload.get("decision_digest", "")),
            plan_digest=str(payload.get("plan_digest", "")),
            sample_ids=tuple(str(s) for s in payload.get("sample_ids", [])),
            split_digest=str(payload.get("split_digest", "")),
            scope_status=str(payload.get("scope_status", "")),
            genesis_status=str(payload.get("genesis_status", "")),
            sealed_gain_bp=int(payload.get("sealed_gain_bp", 0)),
            alpha_price_bp=int(payload.get("alpha_price_bp", 0)),
            certificate_digest=str(payload.get("certificate_digest", "")),
        )


# ---------------------------------------------------------------------------
# Trigger state and budget
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TriggerBudget:
    stall_blocks: int = 1
    sufficiency_gain_bp: int = 10_000
    """Only an exact fit counts as the incumbents explaining the target.

    Two earlier attempts were wrong here. Counting a block as evidence of
    insufficiency only when the incumbents failed the loop's success margin
    never fired at all on ``y = 2 + 5xz - 7/x``, because the built-in
    ``joint_product_interaction`` beats the mean predictor on the ``5xz`` term
    alone. Lowering the bar to 9900 bp did not help either: the incumbents
    scored 9997-9999. Against a mean-predictor baseline, a model that captures
    the dominant term always looks nearly perfect however much structure is
    left, so no threshold below 10000 separates "explains it" from "caught the
    big term and missed the rest".

    On exact-rational data an exact fit is a real distinction (SSE exactly
    zero). On noisy sources this degenerates to "always worth looking", which is
    the honest outcome: the scoped ledger then rations how often the system may
    look, and the null decides what it found. Noisy deployments should lower
    this deliberately, knowing it is a budget knob and not a detector.
    """
    assessment_epoch_size: int = 9
    """Separate, smaller epoch used only to decide whether to look.

    The director does not read the loop's validated blocks for this. It was
    written that way first, and the acceptance test caught it: the unmodified
    loop spends most steps in BOOTSTRAP because the experiment designer often
    finds no admissible intervention, so blocks almost never close and the
    trigger never fired at all. Worse, it coupled the decision to whatever the
    active stream happened to produce.

    An assessment epoch is exchangeable data acquired for the decision, and it
    is never shown to genesis. The confirmation epoch that genesis does see is
    acquired afterwards. Decision data and test data never meet.
    """
    epoch_size: int = 24
    seal_numerator: int = 1
    seal_denominator: int = 3
    alpha_total_bp: int = 500
    """Total type-I error for the entire sequence of searches on one target.

    Fixing the null's arithmetic was necessary and not sufficient. With the exact
    p-value gate in place the noise control still promoted an operator on one
    seed in three: ten sequential searches at 5% each give roughly a 40% chance
    that one of them passes on noise, and the ledger does not help, because it
    prices searches without tightening the level at which they are judged.

    So alpha is spent, not merely accounted. The k-th search on a target is
    judged at ``alpha_total / 2^(k+1)``, whose sum over all k stays below
    ``alpha_total`` however long the sequence runs. The permutation count grows
    to match, which is what makes escalation terminate on its own instead of
    grinding until something passes.
    """
    max_permutation_count: int = 4_095
    permutation_count: int = 19
    """Below 1/alpha - 1 permutations the null cannot reject at all.

    The default was 8, chosen to keep test runtime down, which made the exact
    permutation p-value floor 1/9 = 0.111 against alpha = 0.05. The gate was
    unable to reject anything, and the noise control duly promoted an operator
    out of pure noise. The null owner now returns INSUFFICIENT_NULL_RESOLUTION
    in that regime instead of PASS, and this default no longer walks into it.
    """
    max_shell_index: int | None = None

    def __post_init__(self) -> None:
        if self.stall_blocks < 1:
            raise ValueError("stall_blocks must be positive")
        if self.assessment_epoch_size < 6:
            raise ValueError("an assessment epoch must be splittable")
        if self.epoch_size < 6:
            raise ValueError("an epoch must be large enough to split into fit and seal")
        if not 0 < self.seal_numerator < self.seal_denominator:
            raise ValueError("seal fraction must be a proper fraction")
        if self.permutation_count < 1:
            raise ValueError("genesis without a null is not admissible")
        if self.permutation_count < 19:
            raise ValueError(
                "permutation_count below 19 cannot reject at alpha=0.05; raise it "
                "or raise alpha deliberately"
            )
        if not 0 < self.alpha_total_bp < 10_000:
            raise ValueError("alpha_total_bp must be in (0,10000)")

    def level_for_attempt(self, attempt: int) -> Fraction:
        """Exact rational level for the k-th search on a target.

        Kept as a ``Fraction`` on purpose. In integer basis points the schedule
        floors at 1 bp and stops being summable, so the type-I guarantee quietly
        came to depend on ``max_permutation_count`` stopping the sequence. A
        compute limit must never be load-bearing in a statistical proof.
        """
        return Fraction(self.alpha_total_bp, 10_000) / (2 ** (attempt + 1))

    def permutations_for_attempt(self, attempt: int) -> int:
        return max(self.permutation_count, permutations_required(self.level_for_attempt(attempt)))

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scienceatlas-ai-trigger-budget-v2",
            "stall_blocks": self.stall_blocks,
            "sufficiency_gain_bp": self.sufficiency_gain_bp,
            "assessment_epoch_size": self.assessment_epoch_size,
            "epoch_size": self.epoch_size,
            "seal_numerator": self.seal_numerator,
            "seal_denominator": self.seal_denominator,
            "alpha_total_bp": self.alpha_total_bp,
            "max_permutation_count": self.max_permutation_count,
            "permutation_count": self.permutation_count,
            "max_shell_index": self.max_shell_index,
        }


@dataclass
class TriggerState:
    blocks_without_gain: dict[str, int] = field(default_factory=dict)
    last_status: dict[str, str] = field(default_factory=dict)
    last_shell_index: dict[str, int] = field(default_factory=dict)
    epochs_used: dict[str, int] = field(default_factory=dict)
    epoch_counter: int = 0
    fired: int = 0
    promoted: int = 0

    @staticmethod
    def stem(target_axis: str, input_axes: Sequence[str]) -> str:
        return f"{target_axis}|{','.join(sorted(str(a) for a in input_axes))}"

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scienceatlas-ai-trigger-state-v2",
            "blocks_without_gain": {k: self.blocks_without_gain[k] for k in sorted(self.blocks_without_gain)},
            "last_status": {k: self.last_status[k] for k in sorted(self.last_status)},
            "last_shell_index": {k: self.last_shell_index[k] for k in sorted(self.last_shell_index)},
            "epochs_used": {k: self.epochs_used[k] for k in sorted(self.epochs_used)},
            "epoch_counter": self.epoch_counter,
            "fired": self.fired,
            "promoted": self.promoted,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "TriggerState":
        return cls(
            blocks_without_gain={str(k): int(v) for k, v in payload.get("blocks_without_gain", {}).items()},
            last_status={str(k): str(v) for k, v in payload.get("last_status", {}).items()},
            last_shell_index={str(k): int(v) for k, v in payload.get("last_shell_index", {}).items()},
            epochs_used={str(k): int(v) for k, v in payload.get("epochs_used", {}).items()},
            epoch_counter=int(payload.get("epoch_counter", 0)),
            fired=int(payload.get("fired", 0)),
            promoted=int(payload.get("promoted", 0)),
        )


# ---------------------------------------------------------------------------
# The director
# ---------------------------------------------------------------------------


class EpochGenesisDirector:
    """Owns the autonomous cycle: loop, trigger, epoch, genesis, promotion.

    The wiring lives here, in the package, not in a test.  ``run`` is the whole
    autonomous path; nothing outside it needs to call ``loop.step``,
    ``observe_block`` or ``OperatorGenesisOwner.run``.
    """

    spec = OwnerSpec(
        owner_id="epoch-genesis-director/0.1.0",
        capability="research.autonomous_genesis_director",
        input_types=("world_model", "acquisition_source", "trigger_budget", "alpha_ledger"),
        output_types=("epoch_record", "operator_certificate", "loop_step_receipt"),
        validity_domain=(
            "single-domain targets whose input axes all declare bounded validity; "
            "genesis evidence comes only from confirmation epochs acquired after "
            "the shell was fixed"
        ),
        uncertainty_contract=(
            "each epoch is used by exactly one search; no observation that took part "
            "in a shell decision is reused to test the search it authorised"
        ),
        cost_model="epoch_size acquisitions per escalation, plus the priced search",
        deterministic=False,
        replayable=False,
        falsification_contract=(
            "a promoted operator is exposed to the loop's prospective validation and "
            "revoked by the existing continual contract; a null failure holds the shell "
            "rather than escalating it"
        ),
        owner_kind="director",
    )

    def __init__(
        self,
        *,
        ai: Any,
        genesis: GenesisState,
        meta: RegionalMetaLearner,
        loop: ResearchLoopOwner,
        genesis_owner: OperatorGenesisOwner,
        ledger_binding: LedgerBinding,
        plan: EpochPlan | None = None,
        ladder: ShellLadder | None = None,
        pricing: SearchPricing | None = None,
        budget: TriggerBudget | None = None,
        state: TriggerState | None = None,
    ) -> None:
        self.ai = ai
        self.genesis = genesis
        self.meta = meta
        self.loop = loop
        self.genesis_owner = genesis_owner
        self.binding = ledger_binding
        self.plan = plan or EpochPlan()
        self.ladder = ladder or ShellLadder()
        self.pricing = pricing or SearchPricing()
        self.budget = budget or TriggerBudget()
        self.state = state or TriggerState()
        self.epochs: list[EpochRecord] = []
        # Inspected once, up front. Wrapping the call in try/except TypeError was
        # unsafe: a TypeError raised *inside* genesis after the ledger debit would
        # have looked like a signature mismatch and run the whole search again.
        try:
            genesis_params = inspect.signature(self.genesis_owner.run).parameters
        except (TypeError, ValueError):
            genesis_params = {}
        self._genesis_takes_domain = "search_domain" in genesis_params
        self._fingerprints: dict[str, str] = {}
        if self.binding.scoped and self.binding.fingerprint_fn is None:
            # Bound to the sealed loop's boundary, so callers never supply one.
            self.binding.bind_fingerprints(self._fingerprints.get)
        if self.binding.scoped and not self._genesis_takes_domain:
            raise ValueError(
                "scoped ledger with a genesis owner that has no search_domain "
                "parameter: the search would be charged without a scope"
            )

    # -- R1 ---------------------------------------------------------------

    def _observe_block(self, *, stem: str, window_gain_bp: int) -> int:
        if window_gain_bp >= self.budget.sufficiency_gain_bp:
            self.state.blocks_without_gain[stem] = 0
        else:
            self.state.blocks_without_gain[stem] = self.state.blocks_without_gain.get(stem, 0) + 1
        return self.state.blocks_without_gain[stem]

    # -- R3 ---------------------------------------------------------------

    def _next_shell_index(self, stem: str) -> tuple[int | None, str]:
        last_status = self.state.last_status.get(stem)
        last_index = self.state.last_shell_index.get(stem)
        if last_status is None or last_index is None:
            return (0, "FIRST_SEARCH")
        if last_status == "PROMOTED":
            return (last_index, "RECHECK_AFTER_PROMOTION")
        if last_status in HOLD_AFTER:
            # The winner was noise. A bigger shell buys only more multiplicity,
            # so hold the depth and let a fresh epoch answer the same question.
            return (last_index, "HELD_AFTER_NULL_FAILURE")
        if last_status in ESCALATE_AFTER:
            nxt = last_index + 1
            if self.budget.max_shell_index is not None and nxt > self.budget.max_shell_index:
                return (None, "SHELL_LIMIT_REACHED")
            return (nxt, "ESCALATED_GRAMMAR_INSUFFICIENT")
        return (last_index, "RETRY_AT_DEPTH")

    # -- decision ---------------------------------------------------------

    def _decide(self, *, target_axis: str, input_axes: Sequence[str], domain: str) -> dict[str, Any]:
        stem = TriggerState.stem(target_axis, input_axes)
        rules: list[tuple[str, str]] = []
        payload: dict[str, Any] = {
            "schema": "scienceatlas-ai-genesis-decision-v2",
            "target_axis": target_axis,
            "input_axes": list(input_axes),
            "domain": domain,
            "stem": stem,
            "scope_status": self.binding.scope_status,
        }

        def sealed(fire: bool, reason: str, shell_index: int | None = None) -> dict[str, Any]:
            out = {**payload, "fire": fire, "reason": reason,
                   "rules": [[a, b] for a, b in rules], "shell_index": shell_index}
            out["digest"] = digest_json(out, namespace=b"SCIENCEATLAS_AI_GENESIS_DECISION_V2")
            return out

        stalls = self.state.blocks_without_gain.get(stem, 0)
        payload["blocks_without_gain"] = stalls
        if stalls < self.budget.stall_blocks:
            rules.append((RULE_ORDER[0], "HOLD"))
            return sealed(False, "incumbents still explain the target within the sufficiency margin")
        rules.append((RULE_ORDER[0], "PASS"))

        # R2 is structural here: an epoch is acquired after this decision and is
        # used by exactly one search, so freshness cannot be violated by reuse.
        rules.append((RULE_ORDER[1], "PASS"))

        shell_index, escalation = self._next_shell_index(stem)
        payload["escalation"] = escalation
        if shell_index is None:
            rules.append((RULE_ORDER[2], "HOLD"))
            return sealed(False, escalation)
        rules.append((RULE_ORDER[2], "PASS"))

        attempt = self.state.epochs_used.get(stem, 0)
        level = self.budget.level_for_attempt(attempt)
        permutations = self.budget.permutations_for_attempt(attempt)
        payload["attempt"] = attempt
        payload["level"] = {"numerator": level.numerator, "denominator": level.denominator}
        payload["permutation_count"] = permutations
        if permutations > self.budget.max_permutation_count:
            # A compute limit, not a statistical one. The schedule itself is
            # infinite; this says "not now", never "never".
            rules.append((RULE_ORDER[3], "DEFERRED_RESOURCE"))
            return sealed(False, "permutation budget exceeds the compute ceiling for this attempt", shell_index)
        shell = self.ladder.shell(shell_index)
        price = self.pricing.search_price_bp(
            families_charged=shell.max_families_examined,
            permutation_count=permutations,
        )
        payload["shell_price_bp"] = price
        payload["alpha_balance_bp"] = self.binding.balance_bp
        if not self.binding.can_spend(price, domain=domain, axes=tuple(input_axes) + (target_axis,)):
            rules.append((RULE_ORDER[3], "HOLD"))
            return sealed(False, "scoped alpha cannot pay for this shell", shell_index)
        rules.append((RULE_ORDER[3], "PASS"))
        return sealed(True, "all four trigger rules satisfied", shell_index)

    # -- epoch acquisition -------------------------------------------------

    def _acquire_epoch(
        self,
        *,
        source: ObservationSource,
        target_axis: str,
        input_axes: Sequence[str],
        epoch_index: int,
        size: int,
        kind: str = "confirmation",
    ) -> tuple[list[tuple[dict[str, Fraction], Fraction]], list[str], str]:
        axes_meta = {a: self.ai.representation.axes[a] for a in input_axes}
        validity = {a: axes_meta[a].validity for a in input_axes}
        sample_ids: list[str] = []
        for position in range(size):
            point = self.plan.point(
                epoch_index=epoch_index, position=position,
                axes=input_axes, validity=validity,
            )
            if point is None:
                return ([], [], "REFUSED_UNBOUNDED_AXIS")
            sample_id = f"{kind[:4]}-epoch-{epoch_index:04d}-{position:03d}"
            quantities = {
                a: SemanticQuantity(
                    value=point[a], semantic_type=axes_meta[a].semantic_type,
                    domain=axes_meta[a].domain, unit=axes_meta[a].unit,
                    validity=axes_meta[a].validity,
                )
                for a in input_axes
            }
            request = AcquisitionRequest(
                sample_id=sample_id, target_axis=target_axis,
                input_axes=tuple(input_axes), point=quantities, experiment_id=None,
            )
            # Delegate to the sealed loop's acquisition boundary: it admits the
            # observation and derives the evidence fingerprint from the source
            # owner, the measured quantities, upstream evidence ids and claims,
            # deliberately excluding the caller-chosen sample_id. Calling
            # source.acquire and ai.observe here instead meant minting a second,
            # weaker identity from scheduler metadata.
            result = self.loop._acquire(self.ai, source, request)
            status_code, fingerprint = self._unpack_acquisition(result)
            if status_code != "ACQUIRED":
                continue
            if fingerprint:
                self._fingerprints[sample_id] = fingerprint
            sample_ids.append(sample_id)

        rows: list[tuple[dict[str, Fraction], Fraction]] = []
        kept: list[str] = []
        for sample_id in sample_ids:
            values = {a: self.ai.world.values_by_sample(a).get(sample_id) for a in input_axes}
            y = self.ai.world.values_by_sample(target_axis).get(sample_id)
            if y is None or any(v is None for v in values.values()):
                continue
            rows.append(({a: values[a] for a in input_axes}, y))
            kept.append(sample_id)
        if len(kept) < 6:
            return (rows, kept, "EPOCH_TOO_SMALL")
        return (rows, kept, "ACQUIRED")

    @staticmethod
    def _unpack_acquisition(result: Any) -> tuple[str, str]:
        """Accept the 2-tuple of 0.7/0.8 and the 3-tuple with a fingerprint of 15.18."""
        if isinstance(result, tuple):
            if len(result) >= 3:
                return (str(result[0]), str(result[2]))
            if len(result) == 2:
                return (str(result[0]), "")
        return ("UNKNOWN_ACQUISITION_RESULT", "")

    def _incumbents_are_exact(
        self, rows: Sequence[tuple[Mapping[str, Fraction], Fraction]]
    ) -> tuple[bool, Any]:
        """Out-of-sample exact fit by the standing owners on assessment data.

        Held out inside the assessment epoch so that a family with as many
        parameters as points cannot pass by interpolation.
        """
        n = len(rows)
        cut = max(2, n * 2 // 3)
        if n - cut < 2:
            return (False, None)
        sse = build_incumbent_evaluator(self.ai, genesis=self.genesis)(list(rows[:cut]), list(rows[cut:]))
        return (sse is not None and sse == 0, sse)

    # -- one search on one epoch ------------------------------------------

    def _search_on_epoch(
        self,
        *,
        target_axis: str,
        input_axes: Sequence[str],
        domain: str,
        shell: GenesisShell,
        rows: Sequence[tuple[Mapping[str, Fraction], Fraction]],
        sample_ids: Sequence[str],
        decision_digest: str,
        epoch_index: int,
        level: Fraction,
        permutation_count: int,
    ) -> EpochRecord:
        n = len(rows)
        seal_size = max(2, n * self.budget.seal_numerator // self.budget.seal_denominator)
        fit_size = n - seal_size
        fit_rows, seal_rows = list(rows[:fit_size]), list(rows[fit_size:])
        split = GenesisSplit(
            propose=(f"epoch:{epoch_index}",),
            fit=tuple(sample_ids[:fit_size]),
            seal=tuple(sample_ids[fit_size:]),
        )
        # Three distinct quantities that used to be one integer:
        #   level              -> the statistical level of this attempt's null
        #   pricing.promotion_bp -> what promotion costs the evidence ledger
        #   the search price    -> what the search itself costs
        # GenesisBudget.alpha_bp is spent by GenesisState.promote, so it carries
        # the promotion price only. Under the old arrangement a stricter test made
        # promotion cheaper, which is backwards.
        if isinstance(self.genesis_owner.null_owner, SequentialPermutationNullOwner):
            self.genesis_owner.null_owner.set_level(level)
        budget = shell.budget(
            permutation_count=permutation_count,
            alpha_bp=max(1, min(9_999, self.pricing.promotion_bp)),
        )
        incumbent_fit = build_incumbent_evaluator(self.ai, genesis=self.genesis)
        all_rows = fit_rows + seal_rows

        def null_replay(seed: int):
            rng = random.Random(seed)
            ys = [y for _, y in all_rows]
            rng.shuffle(ys)
            permuted = [(xs, y) for (xs, _), y in zip(all_rows, ys, strict=True)]
            certificate = self._run_genesis(
                target_axis=target_axis, input_axes=input_axes, domain=domain,
                rows_fit=permuted[:fit_size], rows_seal=permuted[fit_size:],
                budget=shell.budget(permutation_count=1), split=split,
                incumbent_fit=incumbent_fit, shell=shell, priced=False,
            )
            return Fraction(certificate.sealed_gain_bp)

        seed_base = int(digest_json(
            {"decision": decision_digest, "epoch": epoch_index},
            namespace=b"SCIENCEATLAS_AI_EPOCH_NULL_SEED_V1")[:8], 16)
        certificate = self._run_genesis(
            target_axis=target_axis, input_axes=input_axes, domain=domain,
            rows_fit=fit_rows, rows_seal=seal_rows, budget=budget, split=split,
            incumbent_fit=incumbent_fit, shell=shell, priced=True,
            null_replay=null_replay,
            null_seeds=[seed_base + i for i in range(budget.permutation_count)],
        )
        journal_status = "UNKNOWN"
        for record in self.genesis.journal.runs.values():
            if record.certificate_digest == certificate.digest:
                journal_status = record.status
                break

        stem = TriggerState.stem(target_axis, input_axes)
        self.state.last_status[stem] = journal_status
        self.state.last_shell_index[stem] = shell.index
        self.state.blocks_without_gain[stem] = 0
        self.state.epochs_used[stem] = self.state.epochs_used.get(stem, 0) + 1
        self.state.fired += 1

        if certificate.status == "PROMOTED":
            owner, _ = self.genesis.promote(
                certificate, budget=budget, bus=self.ai.owner_bus,
                meta=self.meta, regime="default", domain=domain,
            )
            if owner is not None:
                self.state.promoted += 1

        record = EpochRecord(
            epoch_index=epoch_index, target_axis=target_axis,
            input_axes=tuple(input_axes), domain=domain, shell_index=shell.index,
            decision_digest=decision_digest, plan_digest=self.plan.digest,
            sample_ids=tuple(sample_ids), split_digest=split.digest,
            scope_status=self.binding.scope_status, genesis_status=journal_status,
            sealed_gain_bp=certificate.sealed_gain_bp,
            alpha_price_bp=certificate.alpha_price_bp,
            certificate_digest=certificate.digest,
        )
        self.epochs.append(record)
        return record

    def _run_genesis(self, *, priced: bool, domain: str, **kwargs: Any):
        call: dict[str, Any] = dict(kwargs)
        call["input_axes"] = tuple(call["input_axes"])
        call["incumbent_owner_ids"] = tuple(s.owner_id for s in self.ai.owner_bus.specs()) if priced else ()
        if priced:
            call.update(
                ledger=self.binding.ledger,
                journal=self.genesis.journal,
                pricing=self.pricing,
            )
        if self._genesis_takes_domain:
            call["search_domain"] = domain
        return self.genesis_owner.run(**call)

    # -- the autonomous path ----------------------------------------------

    def run(
        self,
        *,
        source: ObservationSource,
        loop_state: Any,
        target_axis: str,
        input_axes: Sequence[str],
        max_cycles: int = 12,
        loop_steps_per_cycle: int = 2,
    ) -> dict[str, Any]:
        """The whole autonomous path. Nothing outside this needs to be called.

        Each cycle: run the loop for prospective validation and revocation,
        acquire an assessment epoch to decide, and, if the incumbents are not
        exact, fix the shell and acquire a separate confirmation epoch for
        genesis. Assessment data never reaches genesis; confirmation data never
        influences the decision that authorised it.
        """
        domain = self.ai.representation.axes[target_axis].domain
        stem = TriggerState.stem(target_axis, input_axes)
        axes_scope = tuple(input_axes) + (target_axis,)
        loop_statuses: list[str] = []
        assessments: list[dict[str, Any]] = []
        deferred: dict[str, Any] | None = None

        for _ in range(max_cycles):
            for _ in range(loop_steps_per_cycle):
                receipt = self.loop.step(
                    ai=self.ai, source=source, state=loop_state,
                    meta=self.meta, genesis=self.genesis,
                )
                loop_statuses.append(str(receipt.get("status")))

            self.state.epoch_counter += 1
            assess_index = self.state.epoch_counter
            rows, sample_ids, status = self._acquire_epoch(
                source=source, target_axis=target_axis, input_axes=input_axes,
                epoch_index=assess_index, size=self.budget.assessment_epoch_size,
                kind="assessment",
            )
            if status != "ACQUIRED":
                assessments.append({"epoch": assess_index, "status": status})
                continue
            self._grant(sample_ids, domain=domain, axes=axes_scope, epoch_index=assess_index)
            exact, sse = self._incumbents_are_exact(rows)
            assessments.append({
                "epoch": assess_index, "status": "ASSESSED",
                "incumbents_exact": exact,
                "stalls": self._observe_block(stem=stem, window_gain_bp=10_000 if exact else 0),
            })
            if exact:
                continue

            decision = self._decide(target_axis=target_axis, input_axes=input_axes, domain=domain)
            if any(verdict == "DEFERRED_RESOURCE" for _, verdict in decision["rules"]):
                # Yield to whoever owns compute. Continuing the cycle would buy
                # another assessment epoch, mint more evidence credit and arrive
                # at the identical deferral: measurements spent for nothing.
                deferred = decision
                break
            if not decision["fire"]:
                continue

            shell = self.ladder.shell(int(decision["shell_index"]))
            self.state.epoch_counter += 1
            confirm_index = self.state.epoch_counter
            rows, sample_ids, status = self._acquire_epoch(
                source=source, target_axis=target_axis, input_axes=input_axes,
                epoch_index=confirm_index, size=self.budget.epoch_size,
                kind="confirmation",
            )
            if status != "ACQUIRED":
                continue
            self._grant(sample_ids, domain=domain, axes=axes_scope, epoch_index=confirm_index)
            self._search_on_epoch(
                target_axis=target_axis, input_axes=input_axes, domain=domain,
                shell=shell, rows=rows, sample_ids=sample_ids,
                decision_digest=str(decision["digest"]), epoch_index=confirm_index,
                level=Fraction(int(decision["level"]["numerator"]), int(decision["level"]["denominator"])),
                permutation_count=int(decision["permutation_count"]),
            )

        summary = {
            "schema": "scienceatlas-ai-director-run-v1",
            "scope_status": self.binding.scope_status,
            "loop_steps": len(loop_statuses),
            "assessments": assessments,
            "epochs": [r.to_json() for r in self.epochs],
            "shells_attempted": [r.shell_index for r in self.epochs],
            "promoted": self.state.promoted,
            "synthesized_owners": list(self.genesis.active_owner_ids()),
            "alpha_balance_bp": self.binding.balance_bp,
            "stopped_reason": "DEFERRED_RESOURCE" if deferred else "CYCLES_EXHAUSTED",
            "resource_request": None if deferred is None else {
                "shell_index": deferred.get("shell_index"),
                "attempt": deferred.get("attempt"),
                "level": deferred.get("level"),
                "permutation_count": deferred.get("permutation_count"),
                "compute_ceiling": self.budget.max_permutation_count,
            },
        }
        summary["digest"] = digest_json(summary, namespace=b"SCIENCEATLAS_AI_DIRECTOR_RUN_V1")
        return summary

    def _grant(self, sample_ids: Sequence[str], *, domain: str, axes: Sequence[str], epoch_index: int) -> None:
        # One evidence identity per independent measurement, computed by the
        # acquisition boundary, not one fingerprint shared across the epoch.
        self.binding.grant(sample_ids, domain=domain, axes=axes)


def build_incumbent_evaluator(
    ai: Any, *, genesis: Any = None, exclude_owner_ids: Sequence[str] = ()
) -> Any:
    """Best *eligible* owner's sealed SSE, fitted on the fit rows only.

    Eligibility goes through ``GenesisState``, never through the bus alone.
    Atlas forbids unregistering an owner, so a revoked one stays on the bus for
    history; iterating the bus directly meant a falsified law kept counting as
    an incumbent, the target still looked explained, and genesis would never run
    for it again.
    """
    excluded = set(exclude_owner_ids)
    if genesis is not None:
        excluded |= set(getattr(genesis, "revoked_owner_ids", ()))

    def incumbent_fit(rows_fit, rows_seal):
        best: Fraction | None = None
        axes = tuple(sorted(rows_fit[0][0])) if rows_fit else ()
        for spec in ai.owner_bus.specs():
            if spec.owner_id in excluded or "hypothesis" not in spec.output_types:
                continue
            owner = ai.owner_bus.get(spec.owner_id)
            propose, predict = getattr(owner, "propose", None), getattr(owner, "predict", None)
            if propose is None or predict is None:
                continue
            try:
                hypotheses = propose(list(rows_fit), input_axes=axes,
                                     target_axis="_genesis_baseline",
                                     provenance=("genesis-baseline",))
            except (TypeError, ValueError, ZeroDivisionError, KeyError):
                continue
            for hypothesis in hypotheses:
                total, usable = Fraction(0), True
                for xs, y in rows_seal:
                    try:
                        total += (y - predict(hypothesis, dict(xs))) ** 2
                    except (ValueError, ZeroDivisionError, KeyError, TypeError):
                        usable = False
                        break
                if usable and (best is None or total < best):
                    best = total
        if best is None and rows_fit and rows_seal:
            mean = sum((y for _, y in rows_fit), Fraction(0)) / len(rows_fit)
            best = sum(((y - mean) ** 2 for _, y in rows_seal), Fraction(0))
        return best

    return incumbent_fit


__all__ = [
    "ESCALATE_AFTER",
    "EpochGenesisDirector",
    "SequentialPermutationNullOwner",
    "EpochPlan",
    "EpochRecord",
    "HOLD_AFTER",
    "LedgerBinding",
    "RULE_ORDER",
    "TriggerBudget",
    "TriggerState",
    "build_incumbent_evaluator",
]
