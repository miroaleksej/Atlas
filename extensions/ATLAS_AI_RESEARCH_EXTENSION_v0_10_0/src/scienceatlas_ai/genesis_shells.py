"""Fair open-ended genesis shells and lifetime alpha accounting.

Two defects in 0.7.0 are closed here, and they are one defect seen from two
sides.

**Search was free.**  ``AlphaLedger`` claimed that every genesis run spends
alpha, but ``OperatorGenesisOwner.run`` never touched it: only promotion paid.
Worse, a rejected run left no trace at all, because ``GenesisState.promote``
refuses anything that is not ``PROMOTED`` and stores nothing.  That combination
permits the cheapest form of self-deception available to a self-expanding
system: rerun the search on the same data until the permutation null happens to
let something through.  Every individual run stays correct, every receipt stays
honest, and the conclusion is still worthless.  ``GenesisJournal`` records every
run, promoted or not, and pricing is charged before the search, not after it.

**Ceilings were constants.**  ``max_terms <= 6``, ``max_degree <= 4``,
``max_families_examined <= 100_000`` were config validation masquerading as a
scientific boundary.  ``ShellLadder`` replaces the constant with a declared
growth rule: each shell is finite and replayable, the ladder is a pure function
of the shell index, and there is no final ceiling
(``fixed_genesis_shell_ceiling = None``).

The link between the two is what makes open-endedness safe.  A larger shell is
not forbidden, it is *more expensive*, and it is paid for in independent data.
Growth without pricing would be unbounded multiplicity at a larger scale, which
is why the ladder must never be enabled before the ledger is wired.

Three rules govern reruns, and they are the whole point:

* same split, shell not strictly larger -> ``REFUSED_DUPLICATE_SEARCH``.  A
  retry on exhausted data is not a new experiment.
* same split, strictly larger shell -> charged for the increment only.  Widening
  a shell should not re-buy what was already paid for.
* a family that already failed the null on this split is ineligible on this
  split forever.  Otherwise widening the shell is just a legal way to ask the
  null the same question twice.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .operator_genesis import FamilySpec, GenesisBudget, GenesisSplit, OperatorGrammar
from .provenance import digest_json


FIXED_GENESIS_SHELL_CEILING = None
"""There is no final shell.  Each shell is finite; the sequence is not."""


# ---------------------------------------------------------------------------
# Shells
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GenesisShell:
    """One finite, replayable stratum of the operator space."""

    index: int
    grammar: OperatorGrammar
    max_families_examined: int

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("shell index must be non-negative")
        if self.max_families_examined < 1:
            raise ValueError("a shell must admit at least one family")

    @property
    def shell_id(self) -> str:
        return f"G{self.index}:" + digest_json(self.to_json(), namespace=b"SCIENCEATLAS_AI_GENESIS_SHELL_V1")[:16]

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scienceatlas-ai-genesis-shell-v1",
            "index": self.index,
            "grammar": self.grammar.to_json(),
            "max_families_examined": self.max_families_examined,
        }

    def contains_shell(self, other: "GenesisShell") -> bool:
        """Whether this shell's grammar covers everything ``other`` enumerates."""
        a, b = self.grammar, other.grammar
        return (
            a.max_terms >= b.max_terms
            and a.max_degree >= b.max_degree
            and (a.allow_negative_exponents or not b.allow_negative_exponents)
            and (b.require_constant_term or not a.require_constant_term)
            and self.max_families_examined >= other.max_families_examined
        )

    def strictly_larger_than(self, other: "GenesisShell") -> bool:
        return self.contains_shell(other) and self.to_json() != other.to_json()

    def budget(
        self,
        *,
        permutation_count: int,
        alpha_bp: int = 500,
        min_sealed_gain_bp: int = 500,
        quarantine_epochs: int = 3,
        promoted_prior_bp: int = 3_000,
    ) -> GenesisBudget:
        return GenesisBudget(
            grammar=self.grammar,
            max_families_examined=self.max_families_examined,
            permutation_count=permutation_count,
            alpha_bp=alpha_bp,
            min_sealed_gain_bp=min_sealed_gain_bp,
            quarantine_epochs=quarantine_epochs,
            promoted_prior_bp=promoted_prior_bp,
        )


@dataclass(frozen=True, slots=True)
class ShellLadder:
    """Deterministic, unbounded sequence of shells.

    The growth rule is preregistered and its digest travels with every run, so
    "shell 4" means one specific finite grammar and not whatever the search felt
    like trying next.  Growth alternates degree and terms so neither dimension
    runs away alone, and the family cap grows geometrically.
    """

    base_max_terms: int = 2
    base_max_degree: int = 1
    base_max_families: int = 64
    families_growth_numerator: int = 4
    families_growth_denominator: int = 1
    negative_exponents_from_shell: int = 3

    def __post_init__(self) -> None:
        if self.base_max_terms < 1 or self.base_max_degree < 1 or self.base_max_families < 1:
            raise ValueError("ladder base must be positive")
        if self.families_growth_numerator <= self.families_growth_denominator:
            raise ValueError("shell family cap must grow")
        if self.negative_exponents_from_shell < 0:
            raise ValueError("negative-exponent shell index must be non-negative")

    def shell(self, index: int) -> GenesisShell:
        if index < 0:
            raise ValueError("shell index must be non-negative")
        terms = self.base_max_terms + (index + 1) // 2
        degree = self.base_max_degree + index // 2
        cap = self.base_max_families
        for _ in range(index):
            cap = cap * self.families_growth_numerator // self.families_growth_denominator
        grammar = OperatorGrammar(
            max_terms=terms,
            max_degree=degree,
            allow_negative_exponents=index >= self.negative_exponents_from_shell,
        )
        return GenesisShell(index=index, grammar=grammar, max_families_examined=cap)

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scienceatlas-ai-shell-ladder-v1",
            "base_max_terms": self.base_max_terms,
            "base_max_degree": self.base_max_degree,
            "base_max_families": self.base_max_families,
            "families_growth_numerator": self.families_growth_numerator,
            "families_growth_denominator": self.families_growth_denominator,
            "negative_exponents_from_shell": self.negative_exponents_from_shell,
            "fixed_genesis_shell_ceiling": FIXED_GENESIS_SHELL_CEILING,
        }

    def deepest_affordable(
        self,
        *,
        pricing: "SearchPricing",
        balance_bp: int,
        permutation_count: int,
    ) -> int | None:
        """Deepest shell affordable by the supplied finite compatible balance.

        There is no diagnostic search ceiling.  Termination follows from strictly
        increasing geometric family caps and positive per-family pricing.
        """
        if balance_bp < 0:
            raise ValueError("balance must be non-negative")
        deepest: int | None = None
        index = 0
        while True:
            shell = self.shell(index)
            price = pricing.search_price_bp(
                families_charged=shell.max_families_examined,
                permutation_count=permutation_count,
            )
            if price > balance_bp:
                return deepest
            deepest = index
            index += 1

    @property
    def digest(self) -> str:
        return digest_json(self.to_json(), namespace=b"SCIENCEATLAS_AI_SHELL_LADDER_V1")


# ---------------------------------------------------------------------------
# Pricing
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SearchPricing:
    """What a search costs in lifetime alpha.

    Priced on work actually done, not on outcome: a rejected run costs the same
    as an accepted one, which is the whole point.  Permutations are priced
    separately because the null's cost scales with them and so does the
    confidence it buys.
    """

    per_family_bp: int = 1
    per_permutation_bp: int = 5
    promotion_bp: int = 500

    def __post_init__(self) -> None:
        if self.per_family_bp < 1 or self.per_permutation_bp < 1:
            raise ValueError("search must not be free")

    def search_price_bp(self, *, families_charged: int, permutation_count: int) -> int:
        return families_charged * self.per_family_bp + permutation_count * self.per_permutation_bp

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scienceatlas-ai-search-pricing-v1",
            "per_family_bp": self.per_family_bp,
            "per_permutation_bp": self.per_permutation_bp,
            "promotion_bp": self.promotion_bp,
        }

    @property
    def digest(self) -> str:
        return digest_json(self.to_json(), namespace=b"SCIENCEATLAS_AI_SEARCH_PRICING_V1")


# ---------------------------------------------------------------------------
# Journal of every run, promoted or not
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GenesisRunRecord:
    run_id: str
    shell_index: int
    shell_id: str
    target_axis: str
    input_axes: tuple[str, ...]
    split_digest: str
    budget_digest: str
    families_examined: int
    families_charged: int
    permutation_count: int
    alpha_price_bp: int
    status: str
    winner_family_id: str
    sealed_gain_bp: int
    certificate_digest: str

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scienceatlas-ai-genesis-run-v1",
            "run_id": self.run_id,
            "shell_index": self.shell_index,
            "shell_id": self.shell_id,
            "target_axis": self.target_axis,
            "input_axes": list(self.input_axes),
            "split_digest": self.split_digest,
            "budget_digest": self.budget_digest,
            "families_examined": self.families_examined,
            "families_charged": self.families_charged,
            "permutation_count": self.permutation_count,
            "alpha_price_bp": self.alpha_price_bp,
            "status": self.status,
            "winner_family_id": self.winner_family_id,
            "sealed_gain_bp": self.sealed_gain_bp,
            "certificate_digest": self.certificate_digest,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "GenesisRunRecord":
        return cls(
            run_id=str(payload["run_id"]),
            shell_index=int(payload.get("shell_index", 0)),
            shell_id=str(payload.get("shell_id", "")),
            target_axis=str(payload["target_axis"]),
            input_axes=tuple(str(x) for x in payload.get("input_axes", [])),
            split_digest=str(payload.get("split_digest", "")),
            budget_digest=str(payload.get("budget_digest", "")),
            families_examined=int(payload.get("families_examined", 0)),
            families_charged=int(payload.get("families_charged", 0)),
            permutation_count=int(payload.get("permutation_count", 0)),
            alpha_price_bp=int(payload.get("alpha_price_bp", 0)),
            status=str(payload.get("status", "")),
            winner_family_id=str(payload.get("winner_family_id", "")),
            sealed_gain_bp=int(payload.get("sealed_gain_bp", 0)),
            certificate_digest=str(payload.get("certificate_digest", "")),
        )


def search_context_key(target_axis: str, input_axes: Sequence[str], split_digest: str) -> str:
    return f"{target_axis}|{','.join(sorted(str(a) for a in input_axes))}|{split_digest}"


@dataclass
class GenesisJournal:
    """Every genesis run ever attempted, and what it is no longer allowed to do."""

    runs: dict[str, GenesisRunRecord] = field(default_factory=dict)
    largest_shell: dict[str, dict[str, Any]] = field(default_factory=dict)
    families_charged: dict[str, int] = field(default_factory=dict)
    failed_families: dict[str, list[str]] = field(default_factory=dict)
    ineligibility_reasons: dict[str, dict[str, list[str]]] = field(default_factory=dict)

    # -- admissibility -----------------------------------------------------

    def novelty_verdict(self, *, context: str, shell: GenesisShell) -> tuple[str, int]:
        """Is this search new, and how much of it has already been paid for?

        Returns the verdict and the number of families already charged in this
        context.  A context is ``(target, input axes, split)``: the same shell on
        genuinely new data is a new experiment and is charged in full.
        """
        previous = self.largest_shell.get(context)
        if previous is None:
            return ("NEW_CONTEXT", 0)
        prior = GenesisShell(
            index=int(previous["index"]),
            grammar=OperatorGrammar(**{k: v for k, v in previous["grammar"].items()}),
            max_families_examined=int(previous["max_families_examined"]),
        )
        if not shell.strictly_larger_than(prior):
            return ("DUPLICATE_SEARCH", self.families_charged.get(context, 0))
        return ("SHELL_EXTENSION", self.families_charged.get(context, 0))

    def family_is_barred(self, *, context: str, family_id: str) -> bool:
        return family_id in self.failed_families.get(context, ())

    def barred_families(self, *, context: str) -> frozenset[str]:
        return frozenset(self.failed_families.get(context, ()))

    # -- recording ---------------------------------------------------------

    def record(
        self,
        record: GenesisRunRecord,
        *,
        context: str,
        shell: GenesisShell,
        barred_family_ids: Sequence[str] = (),
        executed: bool = True,
    ) -> None:
        """Record a run; only an executed search claims the context.

        A run refused before enumeration (alpha exhausted, duplicate) is still
        journalled, because refusals are evidence about the search history.  But
        it must not advance ``largest_shell``: an unaffordable G4 that never ran
        would otherwise mark the context as searched to depth 4 and every later
        shell, G4 included, would be refused as a duplicate.  Genesis would die
        on that target for good, and the receipts would all look correct.
        """
        self.runs[record.run_id] = record
        if not executed:
            if barred_family_ids:
                bucket = self.failed_families.setdefault(context, [])
                for family_id in barred_family_ids:
                    if family_id and family_id not in bucket:
                        bucket.append(family_id)
                bucket.sort()
                reasons = self.ineligibility_reasons.setdefault(context, {})
                for family_id in barred_family_ids:
                    if family_id:
                        rb = reasons.setdefault(family_id, [])
                        if record.status not in rb:
                            rb.append(record.status); rb.sort()
            return
        previous = self.largest_shell.get(context)
        if previous is None or shell.strictly_larger_than(
            GenesisShell(
                index=int(previous["index"]),
                grammar=OperatorGrammar(**{k: v for k, v in previous["grammar"].items()}),
                max_families_examined=int(previous["max_families_examined"]),
            )
        ):
            self.largest_shell[context] = shell.to_json()
        self.families_charged[context] = max(
            self.families_charged.get(context, 0), record.families_examined
        )
        if barred_family_ids:
            bucket = self.failed_families.setdefault(context, [])
            for family_id in barred_family_ids:
                if family_id and family_id not in bucket:
                    bucket.append(family_id)
            bucket.sort()
            reasons = self.ineligibility_reasons.setdefault(context, {})
            for family_id in barred_family_ids:
                if family_id:
                    rb = reasons.setdefault(family_id, [])
                    if record.status not in rb:
                        rb.append(record.status); rb.sort()

    # -- reporting ---------------------------------------------------------

    def summary(self) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        spent = 0
        for record in self.runs.values():
            by_status[record.status] = by_status.get(record.status, 0) + 1
            spent += record.alpha_price_bp
        payload = {
            "schema": "scienceatlas-ai-genesis-journal-summary-v1",
            "runs": len(self.runs),
            "by_status": {k: by_status[k] for k in sorted(by_status)},
            "alpha_spent_on_search_bp": spent,
            "contexts": len(self.largest_shell),
            "barred_families": sum(len(v) for v in self.failed_families.values()),
        }
        payload["digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_GENESIS_JOURNAL_SUMMARY_V1")
        return payload

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scienceatlas-ai-genesis-journal-v1",
            "runs": {k: self.runs[k].to_json() for k in sorted(self.runs)},
            "largest_shell": {k: self.largest_shell[k] for k in sorted(self.largest_shell)},
            "families_charged": {k: self.families_charged[k] for k in sorted(self.families_charged)},
            "failed_families": {k: list(self.failed_families[k]) for k in sorted(self.failed_families)},
            "ineligibility_reasons": {
                c: {f: list(v) for f, v in sorted(self.ineligibility_reasons[c].items())}
                for c in sorted(self.ineligibility_reasons)
            },
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "GenesisJournal":
        return cls(
            runs={str(k): GenesisRunRecord.from_json(v) for k, v in payload.get("runs", {}).items()},
            largest_shell={str(k): dict(v) for k, v in payload.get("largest_shell", {}).items()},
            families_charged={str(k): int(v) for k, v in payload.get("families_charged", {}).items()},
            failed_families={str(k): [str(x) for x in v] for k, v in payload.get("failed_families", {}).items()},
            ineligibility_reasons={
                str(c): {str(f): [str(x) for x in reasons] for f, reasons in rows.items()}
                for c, rows in payload.get("ineligibility_reasons", {}).items()
            },
        )


__all__ = [
    "FIXED_GENESIS_SHELL_CEILING",
    "GenesisJournal",
    "GenesisRunRecord",
    "GenesisShell",
    "SearchPricing",
    "ShellLadder",
    "search_context_key",
]
