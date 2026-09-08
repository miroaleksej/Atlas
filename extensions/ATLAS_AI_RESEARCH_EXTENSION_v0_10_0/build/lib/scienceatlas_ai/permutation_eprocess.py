"""Finite-group permutation e-process owner for ScienceAtlas Genesis.

This owner closes the state-leakage hole that appears when a Genesis search is
used as the score W inside a permutation e-variable.  Every orbit member must be
scored against exactly the same pre-epoch scientific state.  In particular the
Genesis journal is snapshotted once, passed read-only to all orbit evaluations,
and is verified byte-identical afterwards.  Orbit evaluations never debit the
alpha ledger and never mutate the journal; one EProcessEpochRecord is committed
only after the group normalisation has completed.

The resulting e-value is per-target evidence only.  Crossing 1/alpha for one
target is not a system-wide discovery guarantee.  A future online multi-target
controller (e-BH/e-LOND or a qualified successor) is required before e-process
crossings can gate Atlas-wide scientific promotion.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from itertools import permutations
from typing import Any, Callable, Mapping, Sequence

from .genesis_shells import GenesisJournal, GenesisShell
from .operator_genesis import GenesisSplit, OperatorGenesisOwner
from .owners import OwnerSpec
from .provenance import digest_json

Row = tuple[Mapping[str, Fraction], Fraction]
IncumbentFit = Callable[[Sequence[Row], Sequence[Row]], Fraction | None]


def _fjson(value: Fraction) -> dict[str, int]:
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _ffrom(payload: Mapping[str, Any]) -> Fraction:
    return Fraction(int(payload["numerator"]), int(payload["denominator"]))


def _compose(a: tuple[int, ...], b: tuple[int, ...]) -> tuple[int, ...]:
    """Composition for the action y_i <- y_perm[i]: first b, then a."""
    return tuple(b[a[i]] for i in range(len(a)))


@dataclass(frozen=True, slots=True)
class PermutationGroup:
    """Explicit finite permutation group, normally created by a safe factory."""

    degree: int
    elements: tuple[tuple[int, ...], ...]
    name: str = "explicit"

    def __post_init__(self) -> None:
        n = int(self.degree)
        if n < 2:
            raise ValueError("permutation group degree must be >=2")
        expected = tuple(range(n))
        elems = tuple(tuple(int(i) for i in p) for p in self.elements)
        if not elems or expected not in elems:
            raise ValueError("permutation group must contain the identity")
        if len(set(elems)) != len(elems):
            raise ValueError("duplicate permutation in group")
        for p in elems:
            if len(p) != n or tuple(sorted(p)) != expected:
                raise ValueError("invalid permutation")
        object.__setattr__(self, "degree", n)
        object.__setattr__(self, "elements", elems)

    @classmethod
    def cyclic(cls, n: int) -> "PermutationGroup":
        n = int(n)
        return cls(n, tuple(tuple((i + k) % n for i in range(n)) for k in range(n)), f"C{n}")

    @classmethod
    def symmetric(cls, n: int) -> "PermutationGroup":
        n = int(n)
        return cls(n, tuple(permutations(range(n))), f"S{n}")

    def verify_group_laws(self) -> dict[str, Any]:
        elems = set(self.elements)
        identity = tuple(range(self.degree))
        closure = all(_compose(a, b) in elems for a in self.elements for b in self.elements)
        inverse = True
        for a in self.elements:
            if not any(_compose(a, b) == identity and _compose(b, a) == identity for b in self.elements):
                inverse = False
                break
        return {"identity": identity in elems, "closure": closure, "inverse": inverse,
                "group_size": len(self.elements), "valid": identity in elems and closure and inverse}

    @property
    def identity_index(self) -> int:
        return self.elements.index(tuple(range(self.degree)))

    def to_json(self) -> dict[str, Any]:
        return {"schema": "scienceatlas-ai-permutation-group-v1", "name": self.name,
                "degree": self.degree, "elements": [list(p) for p in self.elements]}

    @property
    def digest(self) -> str:
        return digest_json(self.to_json(), namespace=b"SCIENCEATLAS_AI_PERMUTATION_GROUP_V1")


@dataclass(frozen=True, slots=True)
class GainPowerMixture:
    """Exact positive W-family over one Genesis gain vector.

    Each component uses W_q(D)=(offset_bp+gain_bp(D))**q.  Component e-values
    are normalised separately over the complete group and then mixed with
    preregistered convex weights.  This permits concentration tuning without
    rerunning Genesis for each q and keeps all arithmetic exact.
    """

    powers: tuple[int, ...] = (1, 2, 4, 8)
    weights: tuple[Fraction, ...] = ()
    offset_bp: int = 1

    def __post_init__(self) -> None:
        if self.offset_bp < 1:
            raise ValueError("W must stay strictly positive")
        powers = tuple(int(q) for q in self.powers)
        if not powers or any(q < 1 for q in powers) or len(set(powers)) != len(powers):
            raise ValueError("powers must be distinct positive integers")
        weights = tuple(Fraction(w) for w in self.weights)
        if not weights:
            weights = tuple(Fraction(1, len(powers)) for _ in powers)
        if len(weights) != len(powers) or any(w < 0 for w in weights) or sum(weights, Fraction(0)) != 1:
            raise ValueError("mixture weights must be non-negative and sum exactly to one")
        object.__setattr__(self, "powers", powers)
        object.__setattr__(self, "weights", weights)

    def evaluate(self, gains_bp: Sequence[int], *, identity_index: int) -> dict[str, Any]:
        gains = tuple(int(g) for g in gains_bp)
        if not gains:
            raise ValueError("empty orbit")
        components: list[dict[str, Any]] = []
        mixture = Fraction(0)
        orbit_mixture = [Fraction(0) for _ in gains]
        for q, weight in zip(self.powers, self.weights, strict=True):
            W = [Fraction((self.offset_bp + g) ** q) for g in gains]
            denom = sum(W, Fraction(0)) / len(W)
            if denom <= 0:
                raise ValueError("non-positive group denominator")
            e_all = [w / denom for w in W]
            e0 = e_all[identity_index]
            mixture += weight * e0
            for i, e in enumerate(e_all):
                orbit_mixture[i] += weight * e
            components.append({"power": q, "weight": _fjson(weight), "denominator": _fjson(denom),
                               "identity_e": _fjson(e0), "orbit_average_e": _fjson(sum(e_all, Fraction(0))/len(e_all))})
        average = sum(orbit_mixture, Fraction(0)) / len(orbit_mixture)
        return {"identity_e": mixture, "orbit_average_e": average,
                "components": components, "orbit_e": tuple(orbit_mixture)}

    def to_json(self) -> dict[str, Any]:
        return {"schema": "scienceatlas-ai-gain-power-mixture-v1", "powers": list(self.powers),
                "weights": [_fjson(w) for w in self.weights], "offset_bp": self.offset_bp}

    @property
    def digest(self) -> str:
        return digest_json(self.to_json(), namespace=b"SCIENCEATLAS_AI_GAIN_POWER_MIXTURE_V1")


@dataclass(frozen=True, slots=True)
class EProcessEpochPlan:
    target_axis: str
    input_axes: tuple[str, ...]
    shell: GenesisShell
    group: PermutationGroup
    score: GainPowerMixture = field(default_factory=GainPowerMixture)
    fit_size: int = 3
    per_target_alpha: Fraction = Fraction(1, 20)
    conditional_group_invariance_attested: bool = False
    acquisition_plan_digest: str = ""

    def __post_init__(self) -> None:
        if self.group.degree < 4 or not 2 <= self.fit_size <= self.group.degree - 2:
            raise ValueError("epoch split must leave at least two fit and two seal rows")
        if not 0 < self.per_target_alpha < 1:
            raise ValueError("per-target alpha must be in (0,1)")

    def to_json(self) -> dict[str, Any]:
        return {"schema": "scienceatlas-ai-eprocess-epoch-plan-v1", "target_axis": self.target_axis,
                "input_axes": list(self.input_axes), "shell": self.shell.to_json(), "group": self.group.to_json(),
                "score": self.score.to_json(), "fit_size": self.fit_size,
                "per_target_alpha": _fjson(self.per_target_alpha),
                "conditional_group_invariance_attested": self.conditional_group_invariance_attested,
                "acquisition_plan_digest": self.acquisition_plan_digest,
                "per_target_only": True, "system_wide_error_control": False}

    @property
    def digest(self) -> str:
        return digest_json(self.to_json(), namespace=b"SCIENCEATLAS_AI_EPROCESS_EPOCH_PLAN_V1")


@dataclass(frozen=True, slots=True)
class EProcessEpochRecord:
    target_key: str
    epoch_index: int
    sample_ids: tuple[str, ...]
    plan_digest: str
    group_digest: str
    frozen_genesis_journal_digest: str
    live_genesis_journal_digest_before: str
    live_genesis_journal_digest_after: str
    orbit_stats_digest: str
    identity_gain_bp: int
    identity_winner_family_id: str
    group_size: int
    distinct_winners: int
    max_gain_bp: int
    max_gain_multiplicity: int
    epoch_e: Fraction
    cumulative_e: Fraction
    per_target_threshold: Fraction
    crossed_per_target_threshold: bool

    def to_json(self) -> dict[str, Any]:
        return {"schema": "scienceatlas-ai-eprocess-epoch-record-v1", "target_key": self.target_key,
                "epoch_index": self.epoch_index, "sample_ids": list(self.sample_ids), "plan_digest": self.plan_digest,
                "group_digest": self.group_digest, "frozen_genesis_journal_digest": self.frozen_genesis_journal_digest,
                "live_genesis_journal_digest_before": self.live_genesis_journal_digest_before,
                "live_genesis_journal_digest_after": self.live_genesis_journal_digest_after,
                "orbit_stats_digest": self.orbit_stats_digest, "identity_gain_bp": self.identity_gain_bp,
                "identity_winner_family_id": self.identity_winner_family_id, "group_size": self.group_size,
                "distinct_winners": self.distinct_winners, "max_gain_bp": self.max_gain_bp,
                "max_gain_multiplicity": self.max_gain_multiplicity, "epoch_e": _fjson(self.epoch_e),
                "cumulative_e": _fjson(self.cumulative_e), "per_target_threshold": _fjson(self.per_target_threshold),
                "crossed_per_target_threshold": self.crossed_per_target_threshold,
                "per_target_only": True, "system_wide_error_control": False,
                "atlas_wide_promotion_allowed_from_this_record_alone": False}

    @property
    def digest(self) -> str:
        return digest_json(self.to_json(), namespace=b"SCIENCEATLAS_AI_EPROCESS_EPOCH_RECORD_V1")

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "EProcessEpochRecord":
        return cls(target_key=str(payload["target_key"]), epoch_index=int(payload["epoch_index"]),
                   sample_ids=tuple(str(x) for x in payload.get("sample_ids", [])), plan_digest=str(payload["plan_digest"]),
                   group_digest=str(payload["group_digest"]), frozen_genesis_journal_digest=str(payload["frozen_genesis_journal_digest"]),
                   live_genesis_journal_digest_before=str(payload["live_genesis_journal_digest_before"]),
                   live_genesis_journal_digest_after=str(payload["live_genesis_journal_digest_after"]),
                   orbit_stats_digest=str(payload["orbit_stats_digest"]), identity_gain_bp=int(payload["identity_gain_bp"]),
                   identity_winner_family_id=str(payload["identity_winner_family_id"]), group_size=int(payload["group_size"]),
                   distinct_winners=int(payload["distinct_winners"]), max_gain_bp=int(payload["max_gain_bp"]),
                   max_gain_multiplicity=int(payload["max_gain_multiplicity"]), epoch_e=_ffrom(payload["epoch_e"]),
                   cumulative_e=_ffrom(payload["cumulative_e"]), per_target_threshold=_ffrom(payload["per_target_threshold"]),
                   crossed_per_target_threshold=bool(payload["crossed_per_target_threshold"]))


@dataclass
class PermutationEProcessState:
    records: list[EProcessEpochRecord] = field(default_factory=list)

    def target_records(self, target_key: str) -> list[EProcessEpochRecord]:
        return [r for r in self.records if r.target_key == target_key]

    def cumulative(self, target_key: str) -> Fraction:
        rows = self.target_records(target_key)
        return Fraction(1) if not rows else rows[-1].cumulative_e

    def used_sample_ids(self, target_key: str) -> frozenset[str]:
        return frozenset(s for r in self.target_records(target_key) for s in r.sample_ids)

    def append(self, record: EProcessEpochRecord) -> None:
        if set(record.sample_ids) & set(self.used_sample_ids(record.target_key)):
            raise ValueError("fresh-epoch invariant violated: sample id reused")
        self.records.append(record)

    def to_json(self) -> dict[str, Any]:
        return {"schema": "scienceatlas-ai-permutation-eprocess-state-v1",
                "records": [r.to_json() for r in self.records], "per_target_only": True,
                "global_online_controller": "UNIMPLEMENTED"}

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "PermutationEProcessState":
        return cls(records=[EProcessEpochRecord.from_json(r) for r in payload.get("records", [])])


class _PassNull:
    def assess(self, *, observed: Fraction, null_statistics: Sequence[Fraction], alpha_bp: int = 500) -> dict[str, Any]:
        return {"status": "PASS", "digest": "EPROCESS_INTERNAL_SCORE_ONLY_NO_NULL"}


class PermutationEProcessOwner:
    """Compute one conditional finite-group e-variable and update one target process."""

    spec = OwnerSpec(
        owner_id="permutation-eprocess-owner/0.1.0",
        capability="methodology.permutation_eprocess",
        input_types=("fresh_epoch", "frozen_genesis_state", "finite_permutation_group", "e_score_plan"),
        output_types=("eprocess_epoch_record",),
        validity_domain=("fresh exchangeable epochs with a finite permutation group fixed before acquisition; "
                         "per-target evidence only"),
        uncertainty_contract=("requires conditional group-invariance under the null; every orbit member sees the "
                              "same frozen Genesis journal and none may mutate it"),
        cost_model="|S| complete Genesis score evaluations per epoch; score mixtures reuse the same gain vector",
        deterministic=True,
        replayable=True,
        falsification_contract=("refuse reused samples, missing invariance attestation, incomplete groups, state leakage, "
                                "or orbit-average e != 1 exactly"),
        owner_kind="methodology",
    )

    def __init__(self, *, state: PermutationEProcessState | None = None) -> None:
        self.state = state or PermutationEProcessState()
        self._score_genesis = OperatorGenesisOwner(null_owner=_PassNull())

    @staticmethod
    def _journal_digest(journal: GenesisJournal) -> str:
        return digest_json(journal.to_json(), namespace=b"SCIENCEATLAS_AI_FROZEN_GENESIS_JOURNAL_V1")

    def assess_epoch(
        self, *, target_key: str, plan: EProcessEpochPlan, rows: Sequence[Row], sample_ids: Sequence[str],
        live_genesis_journal: GenesisJournal, incumbent_fit: IncumbentFit, incumbent_owner_ids: Sequence[str] = (),
    ) -> dict[str, Any]:
        if not plan.conditional_group_invariance_attested:
            return {"status": "REFUSED_NO_CONDITIONAL_GROUP_INVARIANCE_ATTESTATION", "per_target_only": True}
        laws = plan.group.verify_group_laws()
        if not laws["valid"]:
            return {"status": "REFUSED_NOT_A_GROUP", "group_laws": laws, "per_target_only": True}
        if len(rows) != plan.group.degree or len(sample_ids) != plan.group.degree:
            return {"status": "REFUSED_EPOCH_SIZE_MISMATCH", "per_target_only": True}
        if len(set(sample_ids)) != len(sample_ids):
            return {"status": "REFUSED_DUPLICATE_SAMPLE_IDS_WITHIN_EPOCH", "per_target_only": True}
        if set(sample_ids) & set(self.state.used_sample_ids(target_key)):
            return {"status": "REFUSED_REUSED_EPOCH_SAMPLE", "per_target_only": True}

        before = self._journal_digest(live_genesis_journal)
        frozen = GenesisJournal.from_json(live_genesis_journal.to_json())
        frozen_digest = self._journal_digest(frozen)
        split = GenesisSplit(propose=(f"eprocess:{plan.digest}",),
                             fit=tuple(sample_ids[:plan.fit_size]), seal=tuple(sample_ids[plan.fit_size:]))
        budget = plan.shell.budget(permutation_count=1, min_sealed_gain_bp=0)
        gains: list[int] = []
        winners: list[str] = []
        terms: list[Any] = []
        for perm in plan.group.elements:
            permuted = [(rows[i][0], rows[perm[i]][1]) for i in range(len(rows))]
            cert = self._score_genesis.run(
                target_axis=plan.target_axis, input_axes=plan.input_axes,
                rows_fit=permuted[:plan.fit_size], rows_seal=permuted[plan.fit_size:], budget=budget, split=split,
                incumbent_fit=incumbent_fit, incumbent_owner_ids=tuple(incumbent_owner_ids),
                null_replay=lambda seed: Fraction(0), null_seeds=(0,), shell=plan.shell,
                journal=frozen, journal_write=False, ledger=None, search_domain="EPROCESS_SCORE_ONLY",
            )
            gains.append(int(cert.sealed_gain_bp)); winners.append(cert.family.family_id)
            terms.append([t.to_json()["powers"] for t in cert.family.terms])
        after = self._journal_digest(live_genesis_journal)
        if after != before:
            raise RuntimeError("GenesisJournal mutated during permutation orbit scoring")
        if self._journal_digest(frozen) != frozen_digest:
            raise RuntimeError("frozen Genesis journal was mutated during orbit scoring")

        score = plan.score.evaluate(gains, identity_index=plan.group.identity_index)
        if score["orbit_average_e"] != 1:
            raise RuntimeError("finite-group e normalisation identity failed")
        identity_idx = plan.group.identity_index
        orbit_payload = {"gains_bp": gains, "winner_family_ids": winners, "winner_terms": terms,
                         "group_digest": plan.group.digest, "plan_digest": plan.digest}
        orbit_digest = digest_json(orbit_payload, namespace=b"SCIENCEATLAS_AI_EPROCESS_ORBIT_STATS_V1")
        epoch_e = Fraction(score["identity_e"])
        prior = self.state.cumulative(target_key)
        cumulative = prior * epoch_e
        threshold = Fraction(1, 1) / plan.per_target_alpha
        record = EProcessEpochRecord(
            target_key=target_key, epoch_index=len(self.state.target_records(target_key)), sample_ids=tuple(sample_ids),
            plan_digest=plan.digest, group_digest=plan.group.digest, frozen_genesis_journal_digest=frozen_digest,
            live_genesis_journal_digest_before=before, live_genesis_journal_digest_after=after,
            orbit_stats_digest=orbit_digest, identity_gain_bp=gains[identity_idx], identity_winner_family_id=winners[identity_idx],
            group_size=len(gains), distinct_winners=len(set(winners)), max_gain_bp=max(gains),
            max_gain_multiplicity=gains.count(max(gains)), epoch_e=epoch_e, cumulative_e=cumulative,
            per_target_threshold=threshold, crossed_per_target_threshold=cumulative >= threshold,
        )
        self.state.append(record)
        return {"status": "PASS_EPROCESS_EPOCH", "record": record.to_json(), "record_digest": record.digest,
                "score": {"identity_e": _fjson(epoch_e), "orbit_average_e": _fjson(score["orbit_average_e"]),
                          "components": score["components"]},
                "orbit_summary": orbit_payload,
                "claim_boundary": {"per_target_only": True, "system_wide_error_control": False,
                                   "atlas_wide_promotion_allowed": False,
                                   "global_online_controller": "UNIMPLEMENTED",
                                   "ville_threshold_is_per_target_only": True}}


__all__ = ["EProcessEpochPlan", "EProcessEpochRecord", "GainPowerMixture", "PermutationEProcessOwner",
           "PermutationEProcessState", "PermutationGroup"]
