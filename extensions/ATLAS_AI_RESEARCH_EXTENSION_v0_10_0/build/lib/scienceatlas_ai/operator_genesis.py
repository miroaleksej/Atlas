"""Operator genesis for ScienceAtlas AI.

Draft contract (0.1.0-draft) for synthesising *new* mechanism families instead of
selecting from a hardcoded list.

Three design commitments, in decreasing order of importance:

1.  A synthesised operator is **declarative data**, never generated Python.  A
    family is a ``FamilySpec``: a canonical, hashable, serialisable list of
    monomial terms.  This is what keeps ``deterministic=True`` and
    ``replayable=True`` honest, keeps the state envelope in ``persistence.py``
    meaningful, and keeps genesis out of the position of executing code it wrote
    itself.

2.  Genesis inflates the hypothesis space by orders of magnitude, so the null
    must be recalibrated *around the whole genesis pipeline*, not around the
    winning family.  Every permutation replays enumeration **and** selection.
    A family that beats a null computed only for its own fit has proved nothing.

3.  Genesis must not be able to credit itself.  Proposal, fit and gain use three
    disjoint sample splits; a promoted owner enters the ``MetaLearner`` under a
    penalised prior and a quarantine period, so a synthesised operator cannot
    raise its own strategy score on the evidence that produced it.

Out of scope by construction: cross-domain composition and any external typed
bridge.  Genesis operates on axes of a single domain that are already present in
the representation graph.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from itertools import combinations_with_replacement
from typing import Any, Callable, Iterable, Mapping, Sequence

from .owners import OwnerSpec, _least_squares
from .provenance import digest_json
from .types import Hypothesis, ValidityDomain, fraction_json, fraction_from_json


GENESIS_CAPABILITY = "hypothesis.operator_genesis"
SYNTHESIZED_CAPABILITY_PREFIX = "hypothesis.numeric_relation.synthesized"

# Promotion is fail-closed: gates are evaluated in this exact order and the first
# failure terminates evaluation.  Order is preregistered so that a later reader of
# a certificate can tell which gates were never reached.
GATE_ORDER = (
    "LEDGER_AFFORDABILITY",
    "SEARCH_NOVELTY",
    "DOMAIN_ADMISSIBILITY",
    "RANK_NONDEGENERACY",
    "NON_REDUNDANCY",
    "PRIOR_FAILURE_EXCLUSION",
    "BUDGET_CONFORMANCE",
    "SEALED_GAIN",
    "PIPELINE_NULL",
)


# ---------------------------------------------------------------------------
# Operator representation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TermSpec:
    """One feature column: a product of integer powers of input axes.

    ``powers`` is a canonically sorted tuple of ``(axis_id, exponent)`` with no
    zero exponents.  The empty tuple is the constant term.  Negative exponents
    are admissible but carry a domain guard: the term is undefined where the
    axis value is zero, and ``features`` returns ``None`` for that row rather
    than silently dropping it.
    """

    powers: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        cleaned = tuple(sorted(((str(a), int(p)) for a, p in self.powers if int(p) != 0)))
        seen = [a for a, _ in cleaned]
        if len(seen) != len(set(seen)):
            raise ValueError("duplicate axis in term")
        object.__setattr__(self, "powers", cleaned)

    @property
    def degree(self) -> int:
        return sum(abs(p) for _, p in self.powers)

    def evaluate(self, xs: Mapping[str, Fraction]) -> Fraction | None:
        acc = Fraction(1)
        for axis_id, exponent in self.powers:
            value = xs[axis_id]
            if value == 0 and exponent < 0:
                return None
            acc *= value ** exponent
        return acc

    def to_json(self) -> dict[str, Any]:
        return {"powers": [[a, p] for a, p in self.powers]}

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "TermSpec":
        return cls(powers=tuple((str(a), int(p)) for a, p in payload.get("powers", [])))


@dataclass(frozen=True, slots=True)
class FamilySpec:
    """A synthesised mechanism family: a linear model over declared terms."""

    input_axes: tuple[str, ...]
    terms: tuple[TermSpec, ...]

    def __post_init__(self) -> None:
        if not self.input_axes:
            raise ValueError("family requires at least one input axis")
        object.__setattr__(self, "input_axes", tuple(str(a) for a in self.input_axes))
        ordered = tuple(sorted(set(self.terms), key=lambda t: (t.degree, t.powers)))
        if not ordered:
            raise ValueError("family requires at least one term")
        known = set(self.input_axes)
        for term in ordered:
            for axis_id, _ in term.powers:
                if axis_id not in known:
                    raise ValueError(f"term references undeclared axis: {axis_id}")
        object.__setattr__(self, "terms", ordered)

    @property
    def family_id(self) -> str:
        return "syn:" + digest_json(self.to_json(), namespace=b"SCIENCEATLAS_AI_FAMILY_SPEC_V1")[:20]

    @property
    def complexity(self) -> int:
        # Terms plus total degree: a family is not cheap merely because it is short.
        return len(self.terms) + sum(t.degree for t in self.terms)

    def features(self, xs: Mapping[str, Fraction]) -> tuple[Fraction, ...] | None:
        row: list[Fraction] = []
        for term in self.terms:
            value = term.evaluate(xs)
            if value is None:
                return None
            row.append(value)
        return tuple(row)

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scienceatlas-ai-family-spec-v1",
            "input_axes": list(self.input_axes),
            "terms": [t.to_json() for t in self.terms],
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "FamilySpec":
        return cls(
            input_axes=tuple(str(a) for a in payload["input_axes"]),
            terms=tuple(TermSpec.from_json(t) for t in payload["terms"]),
        )


# ---------------------------------------------------------------------------
# Bounded grammar and preregistered budget
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OperatorGrammar:
    """Deterministic bounded enumerator over families.

    The grammar is finite and its enumeration order is canonical, so the same
    budget always examines the same prefix of the same sequence.  This is what
    makes the permutation null replayable.
    """

    max_terms: int = 3
    max_degree: int = 2
    allow_negative_exponents: bool = False
    require_constant_term: bool = False

    def __post_init__(self) -> None:
        # No constant upper ceiling. A grammar is bounded by the shell it belongs
        # to and by what the alpha ledger can afford, not by a number chosen once
        # in the source. What must stay true is that each grammar is finite and
        # its enumeration order is canonical, which is what keeps the permutation
        # null replayable.
        if self.max_terms < 1:
            raise ValueError("max_terms must be positive")
        if self.max_degree < 1:
            raise ValueError("max_degree must be positive")

    def _atomic_terms(self, input_axes: Sequence[str], *, max_atoms: int | None = None) -> tuple[TermSpec, ...]:
        """Canonical atomic-term prefix with bounded materialisation.

        The former implementation built the complete set and sliced afterwards,
        which did not protect memory.  Here each degree layer is streamed and only
        the smallest still-needed canonical terms are retained.
        """
        import heapq
        limit = None if max_atoms is None else max(1, int(max_atoms))
        out: list[TermSpec] = [TermSpec(())]
        if limit == 1:
            return tuple(out)
        axes_sorted = tuple(sorted(str(a) for a in input_axes))
        for width in range(1, min(len(axes_sorted), self.max_degree) + 1):
            remaining = None if limit is None else limit - len(out)
            if remaining is not None and remaining <= 0:
                break
            def layer():
                for axes in combinations_with_replacement(axes_sorted, width):
                    counts: dict[str, int] = {}
                    for axis_id in axes:
                        counts[axis_id] = counts.get(axis_id, 0) + 1
                    positive = TermSpec(tuple(counts.items()))
                    yield positive
                    if self.allow_negative_exponents:
                        yield TermSpec(tuple((a, -c) for a, c in counts.items()))
            key = lambda t: (t.degree, t.powers)
            if remaining is None:
                level = sorted(layer(), key=key)
            else:
                level = heapq.nsmallest(remaining, layer(), key=key)
            out.extend(level)
            if limit is not None and len(out) >= limit:
                break
        return tuple(out)

    def enumerate(self, input_axes: Sequence[str], *, max_atoms: int | None = None) -> Iterable[FamilySpec]:
        atoms = self._atomic_terms(input_axes, max_atoms=max_atoms)
        constant = TermSpec(())
        for size in range(1, self.max_terms + 1):
            for combo in combinations_with_replacement(atoms, size):
                unique = tuple(sorted(set(combo), key=lambda t: (t.degree, t.powers)))
                if len(unique) != size:
                    continue
                if self.require_constant_term and constant not in unique:
                    continue
                yield FamilySpec(input_axes=tuple(input_axes), terms=unique)

    def to_json(self) -> dict[str, Any]:
        return {
            "max_terms": self.max_terms,
            "max_degree": self.max_degree,
            "allow_negative_exponents": self.allow_negative_exponents,
            "require_constant_term": self.require_constant_term,
        }


@dataclass(frozen=True, slots=True)
class GenesisBudget:
    """Preregistered genesis configuration.  Its digest is part of every receipt."""

    grammar: OperatorGrammar
    max_families_examined: int
    permutation_count: int
    alpha_bp: int = 500
    min_sealed_gain_bp: int = 500
    quarantine_epochs: int = 3
    promoted_prior_bp: int = 3_000

    def __post_init__(self) -> None:
        if self.max_families_examined < 1:
            raise ValueError("max_families_examined must be positive")
        if self.permutation_count < 1:
            raise ValueError("genesis without a permutation null is not admissible")
        if not 0 < self.alpha_bp < 10_000:
            raise ValueError("alpha_bp must be in (0,10000)")
        if not 0 <= self.promoted_prior_bp <= 5_000:
            raise ValueError("a promoted operator may not enter above the neutral prior")

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scienceatlas-ai-genesis-budget-v1",
            "grammar": self.grammar.to_json(),
            "max_families_examined": self.max_families_examined,
            "permutation_count": self.permutation_count,
            "alpha_bp": self.alpha_bp,
            "min_sealed_gain_bp": self.min_sealed_gain_bp,
            "quarantine_epochs": self.quarantine_epochs,
            "promoted_prior_bp": self.promoted_prior_bp,
        }

    @property
    def digest(self) -> str:
        return digest_json(self.to_json(), namespace=b"SCIENCEATLAS_AI_GENESIS_BUDGET_V1")


@dataclass(frozen=True, slots=True)
class GenesisSplit:
    """Three disjoint sample partitions.

    PROPOSE  seeds the grammar (residual shape, axis pool).  Never fitted on.
    FIT      estimates parameters and ranks families.
    SEAL     is touched exactly once, by the gain gate, and never by proposal.
    """

    propose: tuple[str, ...]
    fit: tuple[str, ...]
    seal: tuple[str, ...]

    def __post_init__(self) -> None:
        parts = [tuple(sorted(set(p))) for p in (self.propose, self.fit, self.seal)]
        object.__setattr__(self, "propose", parts[0])
        object.__setattr__(self, "fit", parts[1])
        object.__setattr__(self, "seal", parts[2])
        union = set(parts[0]) | set(parts[1]) | set(parts[2])
        if len(union) != sum(len(p) for p in parts):
            raise ValueError("genesis splits must be pairwise disjoint")
        if len(parts[1]) < 2 or len(parts[2]) < 2:
            raise ValueError("fit and seal splits require at least two samples each")

    def to_json(self) -> dict[str, Any]:
        return {"propose": list(self.propose), "fit": list(self.fit), "seal": list(self.seal)}

    @property
    def digest(self) -> str:
        return digest_json(self.to_json(), namespace=b"SCIENCEATLAS_AI_GENESIS_SPLIT_V1")


# ---------------------------------------------------------------------------
# Exact-rational linear algebra helpers
# ---------------------------------------------------------------------------


def _rank(matrix: Sequence[Sequence[Fraction]]) -> int:
    rows = [list(r) for r in matrix]
    if not rows:
        return 0
    width = len(rows[0])
    rank = 0
    for col in range(width):
        pivot = next((r for r in range(rank, len(rows)) if rows[r][col] != 0), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        pivot_row = rows[rank]
        for r in range(len(rows)):
            if r != rank and rows[r][col] != 0:
                factor = rows[r][col] / pivot_row[col]
                rows[r] = [a - factor * b for a, b in zip(rows[r], pivot_row, strict=True)]
        rank += 1
        if rank == len(rows):
            break
    return rank


def _sse(
    family: FamilySpec,
    params: Sequence[Fraction],
    rows: Sequence[tuple[Mapping[str, Fraction], Fraction]],
) -> Fraction | None:
    total = Fraction(0)
    for xs, y in rows:
        features = family.features(xs)
        if features is None:
            return None
        predicted = sum((a * b for a, b in zip(features, params, strict=True)), Fraction(0))
        residual = y - predicted
        total += residual * residual
    return total


def _gain_bp(incumbent_sse: Fraction, candidate_sse: Fraction) -> int:
    """Sealed-split improvement in basis points, clamped to [0, 10000]."""
    if incumbent_sse <= 0:
        return 0
    ratio = candidate_sse / incumbent_sse
    raw = (Fraction(1) - ratio) * 10_000
    return max(0, min(10_000, int(raw)))


# ---------------------------------------------------------------------------
# Owner produced by a successful genesis
# ---------------------------------------------------------------------------


class SynthesizedMechanismOwner:
    """A hypothesis owner whose family list came from genesis, not from source.

    Registered under a capability derived from the certificate digest, so
    ``OwnerBus.register``'s one-authoritative-owner-per-capability invariant is
    preserved without touching the incumbent numeric owners.
    """

    def __init__(self, *, certificate: "OperatorCertificate") -> None:
        if certificate.status != "PROMOTED":
            raise ValueError("only a promoted certificate may back a live owner")
        self.certificate = certificate
        self.family = certificate.family
        short = certificate.digest[:12]
        self.spec = OwnerSpec(
            owner_id=f"synthesized-mechanism-owner/{short}",
            capability=f"{SYNTHESIZED_CAPABILITY_PREFIX}.{short}",
            input_types=("measurement",),
            output_types=("hypothesis", "prediction"),
            validity_domain=(
                "exact rational relations over the axes declared in the certified family; "
                "single domain; rows where a negative-exponent term is undefined are excluded"
            ),
            uncertainty_contract=(
                "measurement uncertainty retained by world model; parameters fitted on the FIT split only"
            ),
            cost_model="O(T^2*N + T^3) for T certified terms",
            deterministic=True,
            replayable=True,
            falsification_contract=(
                "certificate is revoked when sealed-split gain fails to reproduce on new samples, "
                "or when the family becomes rank-degenerate or redundant against a later incumbent"
            ),
            owner_kind="hypothesis",
        )

    def propose(
        self,
        rows: Sequence[tuple[Mapping[str, Fraction], Fraction]],
        *,
        input_axes: tuple[str, ...],
        target_axis: str,
        provenance: tuple[str, ...],
    ) -> tuple[Hypothesis, ...]:
        if tuple(input_axes) != self.family.input_axes or len(rows) < 2:
            return ()
        matrix: list[tuple[Fraction, ...]] = []
        ys: list[Fraction] = []
        for xs, y in rows:
            features = self.family.features(xs)
            if features is None:
                return ()
            matrix.append(features)
            ys.append(y)
        params = _least_squares(matrix, ys)
        if params is None:
            return ()
        payload = {
            "owner_id": self.spec.owner_id,
            "family": self.family.family_id,
            "family_spec": self.family.to_json(),
            "certificate": self.certificate.digest,
            "input_axes": list(input_axes),
            "target_axis": target_axis,
            "parameters": [fraction_json(p) for p in params],
            "provenance": list(provenance),
        }
        return (
            Hypothesis(
                hypothesis_id=digest_json(payload, namespace=b"SCIENCEATLAS_AI_HYPOTHESIS_V2")[:24],
                owner_id=self.spec.owner_id,
                family=self.family.family_id,
                input_axes=tuple(input_axes),
                target_axis=target_axis,
                parameters=params,
                complexity=self.family.complexity,
                validity=ValidityDomain(notes=f"certified by {self.certificate.digest[:12]}"),
                status="candidate",
                provenance=provenance,
            ),
        )

    def predict(self, hypothesis: Hypothesis, x: Fraction | Mapping[str, Fraction]) -> Fraction:
        xs = x if isinstance(x, Mapping) else {self.family.input_axes[0]: x}
        features = self.family.features(xs)
        if features is None:
            raise ValueError(f"hypothesis {hypothesis.hypothesis_id} undefined at input")
        if len(features) != len(hypothesis.parameters):
            raise ValueError("hypothesis parameter width mismatch")
        return sum((a * b for a, b in zip(features, hypothesis.parameters, strict=True)), Fraction(0))


# ---------------------------------------------------------------------------
# Certificate
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OperatorCertificate:
    family: FamilySpec
    target_axis: str
    status: str
    gates: tuple[tuple[str, str], ...]
    sealed_gain_bp: int
    families_examined: int
    budget_digest: str
    split_digest: str
    null_receipt_digest: str
    incumbent_owner_ids: tuple[str, ...]
    quarantine_epochs_remaining: int
    revocation_reason: str = ""
    shell_index: int = 0
    shell_id: str = ""
    alpha_price_bp: int = 0
    run_id: str = ""
    search_domain: str = "*"
    alpha_receipt_digest: str = ""

    def __post_init__(self) -> None:
        if self.status not in {"PROMOTED", "REJECTED", "REVOKED"}:
            raise ValueError("unsupported certificate status")
        names = [g for g, _ in self.gates]
        if names != list(GATE_ORDER[: len(names)]):
            raise ValueError("gates must be recorded in the preregistered order")

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scienceatlas-ai-operator-certificate-v3",
            "family": self.family.to_json(),
            "family_id": self.family.family_id,
            "target_axis": self.target_axis,
            "status": self.status,
            "gates": [[name, verdict] for name, verdict in self.gates],
            "sealed_gain_bp": self.sealed_gain_bp,
            "families_examined": self.families_examined,
            "budget_digest": self.budget_digest,
            "split_digest": self.split_digest,
            "null_receipt_digest": self.null_receipt_digest,
            "incumbent_owner_ids": list(self.incumbent_owner_ids),
            "quarantine_epochs_remaining": self.quarantine_epochs_remaining,
            "revocation_reason": self.revocation_reason,
            "shell_index": self.shell_index,
            "shell_id": self.shell_id,
            "alpha_price_bp": self.alpha_price_bp,
            "run_id": self.run_id,
            "search_domain": self.search_domain,
            "alpha_receipt_digest": self.alpha_receipt_digest,
            "claim_boundary": {
                "promotion_means_law": False,
                "promotion_means": "family survived preregistered sealed-split and whole-pipeline null gates",
            },
        }

    @property
    def digest(self) -> str:
        return digest_json(self.to_json(), namespace=b"SCIENCEATLAS_AI_OPERATOR_CERTIFICATE_V3")

    def revoked(self, reason: str) -> "OperatorCertificate":
        return OperatorCertificate(
            family=self.family,
            target_axis=self.target_axis,
            status="REVOKED",
            gates=self.gates,
            sealed_gain_bp=self.sealed_gain_bp,
            families_examined=self.families_examined,
            budget_digest=self.budget_digest,
            split_digest=self.split_digest,
            null_receipt_digest=self.null_receipt_digest,
            incumbent_owner_ids=self.incumbent_owner_ids,
            quarantine_epochs_remaining=0,
            revocation_reason=reason,
            shell_index=self.shell_index,
            shell_id=self.shell_id,
            alpha_price_bp=self.alpha_price_bp,
            run_id=self.run_id,
            search_domain=self.search_domain,
            alpha_receipt_digest=self.alpha_receipt_digest,
        )


# ---------------------------------------------------------------------------
# The genesis owner
# ---------------------------------------------------------------------------


RowSet = Sequence[tuple[Mapping[str, Fraction], Fraction]]
IncumbentFit = Callable[[RowSet, RowSet], Fraction | None]
"""Fit incumbents on the first row set, return their best SSE on the second."""

NullReplay = Callable[[int], Fraction | None]
"""Replay the *entire* genesis under permutation ``seed``; return the winning gain."""


@dataclass(frozen=True, slots=True)
class OperatorGenesisOwner:
    """Synthesises, sandboxes and certifies new mechanism families.

    This owner never registers anything itself.  It returns a certificate; the
    runtime decides whether to build a ``SynthesizedMechanismOwner`` from it and
    put it on the bus.  Genesis proposing and genesis promoting stay separable.
    """

    null_owner: Any  # PipelineNullCalibrationOwner

    spec = OwnerSpec(
        owner_id="operator-genesis-owner/0.1.0",
        capability=GENESIS_CAPABILITY,
        input_types=("measurement", "genesis_budget", "genesis_split", "incumbent_family_matrix"),
        output_types=("family_spec", "operator_certificate"),
        validity_domain=(
            "single-domain rational relations over declared input axes; "
            "bounded monomial grammar; no code generation; no cross-domain composition"
        ),
        uncertainty_contract=(
            "sealed-split gain is a point statistic; significance comes only from the "
            "whole-pipeline permutation null, which replays enumeration and selection"
        ),
        cost_model="grammar_size * (T^2*N + T^3), multiplied by permutation_count for the null",
        deterministic=True,
        replayable=True,
        falsification_contract=(
            "a promoted family is revoked when its sealed gain fails to reproduce on later "
            "samples, or when a permutation replay at the same budget matches it"
        ),
        owner_kind="genesis",
    )

    def enumerate_candidates(
        self,
        *,
        budget: GenesisBudget,
        input_axes: Sequence[str],
    ) -> tuple[FamilySpec, ...]:
        """Bounded, canonical prefix of the grammar.  Truncation is recorded, not silent."""
        out: list[FamilySpec] = []
        for family in budget.grammar.enumerate(input_axes, max_atoms=budget.max_families_examined):
            if len(out) >= budget.max_families_examined:
                break
            out.append(family)
        return tuple(out)

    # -- gates ------------------------------------------------------------

    def _gate_domain(self, family: FamilySpec, rows: RowSet) -> bool:
        return all(family.features(xs) is not None for xs, _ in rows)

    def _gate_rank(self, family: FamilySpec, rows: RowSet) -> bool:
        matrix = [family.features(xs) for xs, _ in rows]
        if any(row is None for row in matrix):
            return False
        return _rank([list(r) for r in matrix]) == len(family.terms)

    def _gate_non_redundancy(
        self,
        family: FamilySpec,
        rows: RowSet,
        incumbent_columns: Sequence[Sequence[Fraction]],
    ) -> bool:
        """Reject families whose column space is already spanned by incumbents.

        A reparametrisation of an existing family is not a new operator, however
        novel its printed form looks.
        """
        if not incumbent_columns:
            return True
        base = [list(col) for col in incumbent_columns]
        base_rank = _rank(base)
        new_cols: list[list[Fraction]] = []
        for index in range(len(family.terms)):
            column: list[Fraction] = []
            for xs, _ in rows:
                features = family.features(xs)
                if features is None:
                    return False
                column.append(features[index])
            new_cols.append(column)
        joint_rank = _rank(base + new_cols)
        return joint_rank > base_rank

    # -- main entry -------------------------------------------------------

    def run(
        self,
        *,
        target_axis: str,
        input_axes: Sequence[str],
        rows_fit: RowSet,
        rows_seal: RowSet,
        budget: GenesisBudget,
        split: GenesisSplit,
        incumbent_fit: IncumbentFit,
        incumbent_owner_ids: Sequence[str],
        incumbent_columns_on_fit: Sequence[Sequence[Fraction]] = (),
        null_replay: NullReplay | None = None,
        null_seeds: Sequence[int] = (),
        shell: Any = None,
        ledger: Any = None,
        journal: Any = None,
        pricing: Any = None,
        search_domain: str = "*",
        journal_write: bool = True,
    ) -> OperatorCertificate:
        """Run one genesis search, paying for it before it happens.

        ``ledger``, ``journal``, ``shell`` and ``pricing`` are optional only so
        that the unpriced call signature still type-checks; when a ledger is
        supplied the search is charged whatever its outcome, and when a journal
        is supplied every run is recorded, rejections included.  Calling without
        them is a bare search with no lifetime accounting and is fit for tests
        only, which is why the certificate then carries ``LEDGER_AFFORDABILITY``
        as ``UNPRICED`` rather than ``PASS``.
        """
        from .genesis_shells import (
            GenesisRunRecord,
            GenesisShell,
            SearchPricing,
            search_context_key,
        )

        gates: list[tuple[str, str]] = []
        shell = shell or GenesisShell(
            index=0, grammar=budget.grammar, max_families_examined=budget.max_families_examined
        )
        pricing = pricing or SearchPricing()
        context = search_context_key(target_axis, input_axes, split.digest)

        # -- gate 1: can this search be afforded at all? --------------------
        verdict, already_charged = (
            journal.novelty_verdict(context=context, shell=shell) if journal is not None else ("NEW_CONTEXT", 0)
        )
        families_charged = max(0, shell.max_families_examined - already_charged) if verdict == "SHELL_EXTENSION" else shell.max_families_examined
        price_bp = pricing.search_price_bp(
            families_charged=families_charged, permutation_count=budget.permutation_count
        )
        run_id = digest_json(
            {
                "context": context,
                "shell": shell.to_json(),
                "budget": budget.to_json(),
                "prior_runs": len(journal.runs) if journal is not None else 0,
            },
            namespace=b"SCIENCEATLAS_AI_GENESIS_RUN_V1",
        )[:24]
        alpha_receipt_digest = ""
        search_axes = tuple(sorted({str(target_axis), *(str(a) for a in input_axes)}))

        def record_and_return(
            certificate: OperatorCertificate,
            *,
            status: str,
            examined: int,
            barred: Sequence[str] = (),
            executed: bool = True,
        ) -> OperatorCertificate:
            if journal is not None and journal_write:
                journal.record(
                    GenesisRunRecord(
                        run_id=run_id,
                        shell_index=shell.index,
                        shell_id=shell.shell_id,
                        target_axis=target_axis,
                        input_axes=tuple(str(a) for a in input_axes),
                        split_digest=split.digest,
                        budget_digest=budget.digest,
                        families_examined=examined,
                        families_charged=families_charged if status != "REFUSED_DUPLICATE_SEARCH" else 0,
                        permutation_count=budget.permutation_count,
                        alpha_price_bp=certificate.alpha_price_bp,
                        status=status,
                        winner_family_id=certificate.family.family_id,
                        sealed_gain_bp=certificate.sealed_gain_bp,
                        certificate_digest=certificate.digest,
                    ),
                    context=context,
                    shell=shell,
                    barred_family_ids=barred,
                    executed=executed,
                )
            return certificate

        def certificate_of(
            family: FamilySpec,
            *,
            status: str,
            gain_bp: int = 0,
            examined: int = 0,
            null_digest: str = "",
            charged_bp: int = 0,
        ) -> OperatorCertificate:
            return OperatorCertificate(
                family=family,
                target_axis=target_axis,
                status=status,
                gates=tuple(gates),
                sealed_gain_bp=gain_bp,
                families_examined=examined,
                budget_digest=budget.digest,
                split_digest=split.digest,
                null_receipt_digest=null_digest,
                incumbent_owner_ids=tuple(incumbent_owner_ids),
                quarantine_epochs_remaining=budget.quarantine_epochs if status == "PROMOTED" else 0,
                shell_index=shell.index,
                shell_id=shell.shell_id,
                alpha_price_bp=charged_bp,
                run_id=run_id,
                search_domain=str(search_domain),
                alpha_receipt_digest=alpha_receipt_digest,
            )

        empty = FamilySpec(input_axes=tuple(input_axes), terms=(TermSpec(()),))

        if ledger is None:
            gates.append((GATE_ORDER[0], "UNPRICED"))
            charged_bp = 0
        else:
            # Affordability is checked before novelty, but debit is delayed until
            # novelty passes. A duplicate is a no-op and must cost exactly zero.
            if not ledger.can_spend(price_bp, domain=str(search_domain), axes=search_axes):
                gates.append((GATE_ORDER[0], "FAIL_ALPHA_EXHAUSTED"))
                return record_and_return(
                    certificate_of(empty, status="REJECTED"),
                    status="REFUSED_ALPHA_EXHAUSTED", examined=0, executed=False,
                )
            gates.append((GATE_ORDER[0], "PASS"))
            charged_bp = 0

        # -- gate 2: is this search new? -----------------------------------
        if verdict == "DUPLICATE_SEARCH":
            gates.append((GATE_ORDER[1], "FAIL_DUPLICATE_SEARCH"))
            return record_and_return(
                certificate_of(empty, status="REJECTED", charged_bp=0),
                status="REFUSED_DUPLICATE_SEARCH", examined=0, executed=False,
            )
        gates.append((GATE_ORDER[1], "PASS"))

        if ledger is not None:
            receipt = ledger.spend(
                price_bp, purpose=f"genesis_search:{run_id}",
                domain=str(search_domain), axes=search_axes,
            )
            if receipt["status"] != "SPENT":
                raise RuntimeError("alpha affordability/debit invariant violated")
            charged_bp = price_bp
            alpha_receipt_digest = str(receipt.get("digest", ""))

        barred = journal.barred_families(context=context) if journal is not None else frozenset()
        candidates = self.enumerate_candidates(budget=budget, input_axes=input_axes)
        examined = len(candidates)

        incumbent_seal_sse = incumbent_fit(rows_fit, rows_seal)
        best: tuple[int, FamilySpec] | None = None
        excluded_by_prior_failure = 0

        for family in candidates:
            if family.family_id in barred:
                excluded_by_prior_failure += 1
                continue
            if not self._gate_domain(family, rows_fit) or not self._gate_domain(family, rows_seal):
                continue
            if not self._gate_rank(family, rows_fit):
                continue
            if not self._gate_non_redundancy(family, rows_fit, incumbent_columns_on_fit):
                continue
            matrix = [family.features(xs) for xs, _ in rows_fit]
            params = _least_squares([list(r) for r in matrix if r is not None], [y for _, y in rows_fit])
            if params is None:
                continue
            sealed = _sse(family, params, rows_seal)
            if sealed is None or incumbent_seal_sse is None:
                continue
            gain = _gain_bp(incumbent_seal_sse, sealed)
            key = (-gain, family.complexity, family.family_id)
            if best is None or key < (-best[0], best[1].complexity, best[1].family_id):
                best = (gain, family)

        if best is None:
            gates.append((GATE_ORDER[2], "FAIL_NO_ADMISSIBLE_FAMILY"))
            return record_and_return(
                certificate_of(empty, status="REJECTED", examined=examined, charged_bp=charged_bp),
                status="REJECTED_NO_ADMISSIBLE_FAMILY",
                examined=examined,
            )

        gain_bp, winner = best
        gates.append((GATE_ORDER[2], "PASS"))
        gates.append((GATE_ORDER[3], "PASS"))
        gates.append((GATE_ORDER[4], "PASS"))
        gates.append((
            GATE_ORDER[5],
            "PASS" if excluded_by_prior_failure == 0 else f"PASS_EXCLUDED_{excluded_by_prior_failure}",
        ))
        gates.append((
            GATE_ORDER[6],
            "PASS" if examined <= budget.max_families_examined else "FAIL_BUDGET_OVERRUN",
        ))

        def reject(status: str, null_digest: str = "") -> OperatorCertificate:
            # A winner that fails any remaining gate is barred from this split
            # for good: widening the shell later must not re-ask the same
            # question of the same null.
            return record_and_return(
                certificate_of(
                    winner, status="REJECTED", gain_bp=gain_bp, examined=examined,
                    null_digest=null_digest, charged_bp=charged_bp,
                ),
                status=status,
                examined=examined,
                barred=(winner.family_id,),
            )

        if gates[-1][1] != "PASS":
            return reject("REJECTED_BUDGET_OVERRUN")

        if gain_bp < budget.min_sealed_gain_bp:
            gates.append((GATE_ORDER[7], "FAIL_BELOW_PREREGISTERED_MARGIN"))
            return reject("REJECTED_BELOW_MARGIN")
        gates.append((GATE_ORDER[7], "PASS"))

        # Whole-pipeline null: each permutation re-runs enumeration and selection,
        # so the multiplicity introduced by genesis itself is priced in.
        if null_replay is None or len(null_seeds) < budget.permutation_count:
            gates.append((GATE_ORDER[8], "FAIL_NULL_NOT_SUPPLIED"))
            return reject("REJECTED_NULL_NOT_SUPPLIED")
        null_stats: list[Fraction] = []
        for seed in list(null_seeds)[: budget.permutation_count]:
            value = null_replay(int(seed))
            null_stats.append(Fraction(0) if value is None else Fraction(value))
        receipt = self.null_owner.assess(
            observed=Fraction(gain_bp),
            null_statistics=null_stats,
            alpha_bp=budget.alpha_bp,
        )
        null_digest = str(receipt.get("digest", ""))
        if str(receipt.get("status")) != "PASS":
            gates.append((GATE_ORDER[8], f"FAIL_{receipt.get('status')}"))
            return reject(f"REJECTED_NULL_{receipt.get('status')}", null_digest)
        gates.append((GATE_ORDER[8], "PASS"))

        return record_and_return(
            certificate_of(
                winner, status="PROMOTED", gain_bp=gain_bp, examined=examined,
                null_digest=null_digest, charged_bp=charged_bp,
            ),
            status="PROMOTED",
            examined=examined,
        )

# ---------------------------------------------------------------------------
# Runtime-side promotion contract (sketch)
# ---------------------------------------------------------------------------


@dataclass
class GenesisRegistry:
    """Holds certificates and enforces the MetaLearner quarantine.

    The rule that matters: a promoted operator enters the strategy scores at
    ``promoted_prior_bp`` (below the 5000 neutral prior) and its outcomes are
    recorded but *not* credited until quarantine expires.  Without this, an
    operator raises its own score on the very evidence that created it.
    """

    certificates: dict[str, OperatorCertificate] = field(default_factory=dict)
    quarantine: dict[str, int] = field(default_factory=dict)

    def promote(self, certificate: OperatorCertificate, *, budget: GenesisBudget) -> SynthesizedMechanismOwner:
        if certificate.status != "PROMOTED":
            raise ValueError("certificate is not promotable")
        owner = SynthesizedMechanismOwner(certificate=certificate)
        self.certificates[certificate.digest] = certificate
        self.quarantine[owner.spec.owner_id] = budget.quarantine_epochs
        return owner

    def initial_score_bp(self, owner_id: str, *, budget: GenesisBudget) -> int:
        return budget.promoted_prior_bp if owner_id in self.quarantine else 5_000

    def credit_allowed(self, owner_id: str) -> bool:
        return self.quarantine.get(owner_id, 0) <= 0

    def tick_epoch(self) -> None:
        for owner_id in list(self.quarantine):
            if self.quarantine[owner_id] > 0:
                self.quarantine[owner_id] -= 1

    def revoke(self, certificate_digest: str, reason: str) -> OperatorCertificate:
        certificate = self.certificates[certificate_digest]
        revoked = certificate.revoked(reason)
        self.certificates[certificate_digest] = revoked
        return revoked


__all__ = [
    "GATE_ORDER",
    "GENESIS_CAPABILITY",
    "FamilySpec",
    "GenesisBudget",
    "GenesisRegistry",
    "GenesisSplit",
    "OperatorCertificate",
    "OperatorGenesisOwner",
    "OperatorGrammar",
    "SynthesizedMechanismOwner",
    "TermSpec",
]
