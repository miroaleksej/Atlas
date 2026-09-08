"""Owner contracts for ScienceAtlas AI.

All domain or strategy algorithms live behind OwnerSpec contracts.  The bus keeps
one authoritative owner per exact capability and is intentionally generic: a
hypothesis owner, a frontier owner, a representation owner or an external Atlas
service can share the same registry without becoming duplicate active logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Mapping, Protocol, Sequence

from .provenance import digest_json
from .types import (
    Axis,
    FrontierAssessment,
    FrontierAxisScore,
    Hypothesis,
    RepresentationProposal,
    SubspaceCandidate,
    ValidityDomain,
)


@dataclass(frozen=True, slots=True)
class OwnerSpec:
    owner_id: str
    capability: str
    input_types: tuple[str, ...]
    output_types: tuple[str, ...]
    validity_domain: str
    uncertainty_contract: str
    cost_model: str
    deterministic: bool
    replayable: bool
    falsification_contract: str
    owner_kind: str = "hypothesis"

    def to_json(self) -> dict[str, object]:
        return {
            "owner_id": self.owner_id,
            "capability": self.capability,
            "input_types": list(self.input_types),
            "output_types": list(self.output_types),
            "validity_domain": self.validity_domain,
            "uncertainty_contract": self.uncertainty_contract,
            "cost_model": self.cost_model,
            "deterministic": self.deterministic,
            "replayable": self.replayable,
            "falsification_contract": self.falsification_contract,
            "owner_kind": self.owner_kind,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "OwnerSpec":
        return cls(
            owner_id=str(payload["owner_id"]),
            capability=str(payload["capability"]),
            input_types=tuple(str(x) for x in payload.get("input_types", [])),
            output_types=tuple(str(x) for x in payload.get("output_types", [])),
            validity_domain=str(payload.get("validity_domain", "")),
            uncertainty_contract=str(payload.get("uncertainty_contract", "")),
            cost_model=str(payload.get("cost_model", "")),
            deterministic=bool(payload.get("deterministic", False)),
            replayable=bool(payload.get("replayable", False)),
            falsification_contract=str(payload.get("falsification_contract", "")),
            owner_kind=str(payload.get("owner_kind", "hypothesis")),
        )


class HypothesisOwner(Protocol):
    spec: OwnerSpec

    def propose(
        self,
        rows: Sequence[tuple[Mapping[str, Fraction], Fraction]],
        *,
        input_axes: tuple[str, ...],
        target_axis: str,
        provenance: tuple[str, ...],
    ) -> tuple[Hypothesis, ...]: ...

    def predict(self, hypothesis: Hypothesis, x: Fraction | Mapping[str, Fraction]) -> Fraction: ...


class OwnerBus:
    """Registry with exactly one authoritative owner per exact capability."""

    def __init__(self) -> None:
        self._by_id: dict[str, Any] = {}
        self._by_capability: dict[str, str] = {}

    def register(self, owner: Any) -> None:
        if not hasattr(owner, "spec") or not isinstance(owner.spec, OwnerSpec):
            raise TypeError("owner must expose an OwnerSpec as .spec")
        owner_id = owner.spec.owner_id
        capability = owner.spec.capability
        if owner_id in self._by_id:
            raise ValueError(f"owner already registered: {owner_id}")
        if capability in self._by_capability:
            existing = self._by_capability[capability]
            raise ValueError(f"capability already has authoritative owner: {capability} -> {existing}")
        self._by_id[owner_id] = owner
        self._by_capability[capability] = owner_id

    def attach(self, owner: Any) -> None:
        """Attach a live executor to an identical detached contract.

        Persistence restores external owners as DetachedOwner so state identity is
        retained but execution stays fail-closed. A later mount may replace only
        that detached executor, and only when the complete OwnerSpec is identical.
        This is deliberately narrower than generic replacement-in-place.
        """
        if not hasattr(owner, "spec") or not isinstance(owner.spec, OwnerSpec):
            raise TypeError("owner must expose an OwnerSpec as .spec")
        owner_id = owner.spec.owner_id
        existing = self._by_id.get(owner_id)
        if existing is None:
            self.register(owner)
            return
        if not isinstance(existing, DetachedOwner):
            raise ValueError(f"live owner already registered: {owner_id}")
        if existing.spec != owner.spec:
            raise ValueError(f"detached owner contract mismatch: {owner_id}")
        mapped = self._by_capability.get(owner.spec.capability)
        if mapped != owner_id:
            raise ValueError(f"capability ownership mismatch during attach: {owner.spec.capability}")
        self._by_id[owner_id] = owner

    def get(self, owner_id: str) -> Any:
        return self._by_id[owner_id]

    def for_capability(self, capability: str) -> Any:
        return self.get(self._by_capability[capability])

    def has_capability(self, capability: str) -> bool:
        return capability in self._by_capability

    def invoke(self, capability: str, **kwargs: Any) -> Any:
        owner = self.for_capability(capability)
        invoke = getattr(owner, "invoke", None)
        if invoke is None:
            raise TypeError(f"owner {owner.spec.owner_id} does not expose service invoke()")
        return invoke(**kwargs)

    def specs(self) -> tuple[OwnerSpec, ...]:
        return tuple(self._by_id[k].spec for k in sorted(self._by_id))

    def capabilities(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_capability))


def _solve_linear(matrix: list[list[Fraction]], rhs: list[Fraction]) -> tuple[Fraction, ...] | None:
    n = len(rhs)
    if n == 0 or len(matrix) != n or any(len(row) != n for row in matrix):
        return None
    a = [row[:] + [rhs_i] for row, rhs_i in zip(matrix, rhs, strict=True)]
    for col in range(n):
        pivot = next((r for r in range(col, n) if a[r][col] != 0), None)
        if pivot is None:
            return None
        if pivot != col:
            a[col], a[pivot] = a[pivot], a[col]
        pivot_value = a[col][col]
        a[col] = [v / pivot_value for v in a[col]]
        for r in range(n):
            if r == col:
                continue
            factor = a[r][col]
            if factor:
                a[r] = [left - factor * right for left, right in zip(a[r], a[col], strict=True)]
    return tuple(a[i][-1] for i in range(n))


def _least_squares(features: Sequence[Sequence[Fraction]], ys: Sequence[Fraction]) -> tuple[Fraction, ...] | None:
    if not features or len(features) != len(ys):
        return None
    width = len(features[0])
    if width == 0 or any(len(row) != width for row in features):
        return None
    gram = [[Fraction(0) for _ in range(width)] for _ in range(width)]
    rhs = [Fraction(0) for _ in range(width)]
    for row, y in zip(features, ys, strict=True):
        for i in range(width):
            rhs[i] += row[i] * y
            for j in range(width):
                gram[i][j] += row[i] * row[j]
    return _solve_linear(gram, rhs)


def _mapping_input(x: Fraction | Mapping[str, Fraction], input_axes: tuple[str, ...]) -> dict[str, Fraction]:
    if isinstance(x, Mapping):
        missing = [axis for axis in input_axes if axis not in x]
        if missing:
            raise ValueError(f"missing hypothesis input axes: {missing}")
        return {axis: Fraction(x[axis]) for axis in input_axes}
    if len(input_axes) != 1:
        raise TypeError("scalar prediction input is valid only for one-axis hypothesis")
    return {input_axes[0]: Fraction(x)}


class NumericMechanismOwner:
    """Exact-rational one-axis baseline mechanism owner."""

    spec = OwnerSpec(
        owner_id="numeric-mechanism-owner/1.1.0",
        capability="hypothesis.numeric_relation.baseline",
        input_types=("measurement",),
        output_types=("hypothesis", "prediction"),
        validity_domain="exact rational scalar relations; one input axis and one target axis",
        uncertainty_contract="measurement uncertainty retained by world model; fit uses central values",
        cost_model="O(F^2*N + F^3) per family",
        deterministic=True,
        replayable=True,
        falsification_contract="prediction error and future discriminating observations may falsify candidates",
        owner_kind="hypothesis",
    )

    _families = (
        "constant",
        "proportional",
        "affine",
        "quadratic_origin",
        "quadratic",
        "cubic",
        "reciprocal_affine",
    )

    @staticmethod
    def _features(family: str, x: Fraction) -> tuple[Fraction, ...] | None:
        if family == "constant":
            return (Fraction(1),)
        if family == "proportional":
            return (x,)
        if family == "affine":
            return (x, Fraction(1))
        if family == "quadratic_origin":
            return (x * x,)
        if family == "quadratic":
            return (x * x, x, Fraction(1))
        if family == "cubic":
            return (x * x * x, x * x, x, Fraction(1))
        if family == "reciprocal_affine":
            if x == 0:
                return None
            return (Fraction(1, 1) / x, Fraction(1))
        raise KeyError(family)

    def propose(
        self,
        rows: Sequence[tuple[Mapping[str, Fraction], Fraction]],
        *,
        input_axes: tuple[str, ...],
        target_axis: str,
        provenance: tuple[str, ...],
    ) -> tuple[Hypothesis, ...]:
        if len(input_axes) != 1 or len(rows) < 2:
            return ()
        input_axis = input_axes[0]
        ys = [y for _, y in rows]
        hypotheses: list[Hypothesis] = []
        for family in self._families:
            matrix: list[tuple[Fraction, ...]] = []
            valid = True
            for xs, _ in rows:
                row = self._features(family, xs[input_axis])
                if row is None:
                    valid = False
                    break
                matrix.append(row)
            if not valid:
                continue
            params = _least_squares(matrix, ys)
            if params is None:
                continue
            payload = {
                "owner_id": self.spec.owner_id,
                "family": family,
                "input_axes": list(input_axes),
                "target_axis": target_axis,
                "parameters": [{"numerator": p.numerator, "denominator": p.denominator} for p in params],
                "provenance": list(provenance),
            }
            hypotheses.append(
                Hypothesis(
                    hypothesis_id=digest_json(payload, namespace=b"SCIENCEATLAS_AI_HYPOTHESIS_V2")[:24],
                    owner_id=self.spec.owner_id,
                    family=family,
                    input_axes=input_axes,
                    target_axis=target_axis,
                    parameters=params,
                    complexity=len(params),
                    validity=ValidityDomain(),
                    status="candidate",
                    provenance=provenance,
                )
            )
        return tuple(hypotheses)

    def predict(self, hypothesis: Hypothesis, x: Fraction | Mapping[str, Fraction]) -> Fraction:
        xs = _mapping_input(x, hypothesis.input_axes)
        row = self._features(hypothesis.family, xs[hypothesis.input_axes[0]])
        if row is None:
            raise ValueError(f"hypothesis {hypothesis.hypothesis_id} invalid at input")
        if len(row) != len(hypothesis.parameters):
            raise ValueError("hypothesis parameter width mismatch")
        return sum((a * b for a, b in zip(row, hypothesis.parameters, strict=True)), Fraction(0))


class MultiAxisMechanismOwner:
    """Exact-rational multi-axis hypothesis owner.

    The caller chooses the input axes.  There is no architecture-level axis-count
    ceiling. Families are generated only when the available rows identify their
    coefficients; insufficient data yields fewer candidates rather than fabricated
    parameters.
    """

    spec = OwnerSpec(
        owner_id="multi-axis-mechanism-owner/1.0.0",
        capability="hypothesis.numeric_relation.multiaxis",
        input_types=("measurement_vector",),
        output_types=("hypothesis", "prediction"),
        validity_domain="exact rational multi-axis observations with a common sample key",
        uncertainty_contract="central-value fit; uncertainty remains attached to observations",
        cost_model="normal-equation solve; width determined by selected axes and family, not a fixed semantic ceiling",
        deterministic=True,
        replayable=True,
        falsification_contract="held-out or future observations and residual/frontier analysis",
        owner_kind="hypothesis",
    )

    _families = ("affine_multiaxis", "additive_quadratic", "full_quadratic_interaction", "joint_product_interaction")

    @staticmethod
    def _features(family: str, axes: tuple[str, ...], xs: Mapping[str, Fraction]) -> tuple[Fraction, ...]:
        values = [xs[a] for a in axes]
        if family == "affine_multiaxis":
            return (Fraction(1), *values)
        if family == "additive_quadratic":
            return (Fraction(1), *values, *(v * v for v in values))
        if family == "full_quadratic_interaction":
            interactions = [values[i] * values[j] for i in range(len(values)) for j in range(i + 1, len(values))]
            return (Fraction(1), *values, *(v * v for v in values), *interactions)
        if family == "joint_product_interaction":
            product = Fraction(1)
            for value in values:
                product *= value
            return (Fraction(1), *values, product)
        raise KeyError(family)

    def propose(
        self,
        rows: Sequence[tuple[Mapping[str, Fraction], Fraction]],
        *,
        input_axes: tuple[str, ...],
        target_axis: str,
        provenance: tuple[str, ...],
    ) -> tuple[Hypothesis, ...]:
        if len(input_axes) < 2 or len(rows) < 2:
            return ()
        ys = [y for _, y in rows]
        result: list[Hypothesis] = []
        for family in self._families:
            matrix = [self._features(family, input_axes, xs) for xs, _ in rows]
            width = len(matrix[0])
            if len(rows) < width:
                continue
            params = _least_squares(matrix, ys)
            if params is None:
                continue
            payload = {
                "owner_id": self.spec.owner_id,
                "family": family,
                "input_axes": list(input_axes),
                "target_axis": target_axis,
                "parameters": [{"numerator": p.numerator, "denominator": p.denominator} for p in params],
                "provenance": list(provenance),
            }
            result.append(
                Hypothesis(
                    hypothesis_id=digest_json(payload, namespace=b"SCIENCEATLAS_AI_HYPOTHESIS_V2")[:24],
                    owner_id=self.spec.owner_id,
                    family=family,
                    input_axes=input_axes,
                    target_axis=target_axis,
                    parameters=params,
                    complexity=len(params),
                    validity=ValidityDomain(),
                    status="candidate",
                    provenance=provenance,
                )
            )
        return tuple(result)

    def predict(self, hypothesis: Hypothesis, x: Fraction | Mapping[str, Fraction]) -> Fraction:
        xs = _mapping_input(x, hypothesis.input_axes)
        row = self._features(hypothesis.family, hypothesis.input_axes, xs)
        if len(row) != len(hypothesis.parameters):
            raise ValueError("hypothesis parameter width mismatch")
        return sum((a * b for a, b in zip(row, hypothesis.parameters, strict=True)), Fraction(0))


class ResidualFrontierOwner:
    spec = OwnerSpec(
        owner_id="residual-frontier-owner/1.0.0",
        capability="research.residual_frontier",
        input_types=("hypothesis", "world_rows", "representation_axes"),
        output_types=("frontier_assessment",),
        validity_domain="exact-rational residual diagnostics over common sample identifiers",
        uncertainty_contract="diagnostic ranking only; nonzero residual correlation is not causal proof",
        cost_model="O(A*N) after hypothesis prediction",
        deterministic=True,
        replayable=True,
        falsification_contract="candidate axes must improve out-of-sample prediction or survive discriminating experiments",
        owner_kind="frontier",
    )

    @staticmethod
    def _variance(values: Sequence[Fraction]) -> Fraction:
        if not values:
            return Fraction(0)
        mean = sum(values, Fraction(0)) / len(values)
        return sum(((x - mean) ** 2 for x in values), Fraction(0))

    @classmethod
    def _r2(cls, xs: Sequence[Fraction], rs: Sequence[Fraction]) -> tuple[Fraction, Fraction, Fraction]:
        if len(xs) != len(rs) or len(xs) < 2:
            return Fraction(0), Fraction(0), Fraction(0)
        mx = sum(xs, Fraction(0)) / len(xs)
        mr = sum(rs, Fraction(0)) / len(rs)
        vx = sum(((x - mx) ** 2 for x in xs), Fraction(0))
        vr = sum(((r - mr) ** 2 for r in rs), Fraction(0))
        if vx == 0 or vr == 0:
            return Fraction(0), vx, vr
        cov = sum(((x - mx) * (r - mr) for x, r in zip(xs, rs, strict=True)), Fraction(0))
        return (cov * cov) / (vx * vr), vx, vr

    def assess(
        self,
        *,
        hypothesis: Hypothesis,
        hypothesis_owner: Any,
        rows: Sequence[tuple[str, Mapping[str, Fraction], Fraction]],
        unused_axis_values: Mapping[str, Mapping[str, Fraction]],
        provenance: tuple[str, ...],
    ) -> FrontierAssessment:
        residual_by_sample: dict[str, Fraction] = {}
        residuals: list[Fraction] = []
        for sample_id, xs, observed in rows:
            try:
                predicted = hypothesis_owner.predict(hypothesis, xs)
            except (ValueError, ZeroDivisionError, KeyError):
                continue
            residual = observed - predicted
            residual_by_sample[sample_id] = residual
            residuals.append(residual)
        if not residuals:
            status = "UNKNOWN"
            mse = Fraction(0)
            max_abs = Fraction(0)
        else:
            mse = sum((r * r for r in residuals), Fraction(0)) / len(residuals)
            max_abs = max(abs(r) for r in residuals)
            status = "CLOSED_ON_OBSERVED_DATA" if mse == 0 else "UNEXPLAINED_RESIDUAL"
        candidates: list[FrontierAxisScore] = []
        if mse != 0:
            for axis_id, by_sample in sorted(unused_axis_values.items()):
                paired = [(by_sample[s], residual_by_sample[s]) for s in sorted(residual_by_sample) if s in by_sample]
                if len(paired) < 2:
                    continue
                xs = [x for x, _ in paired]
                rs = [r for _, r in paired]
                r2, vx, vr = self._r2(xs, rs)
                if vx == 0 or vr == 0 or r2 == 0:
                    continue
                candidates.append(
                    FrontierAxisScore(
                        axis_id=axis_id,
                        residual_r2=r2,
                        paired_count=len(paired),
                        residual_variance=vr,
                        axis_variance=vx,
                    )
                )
            candidates.sort(key=lambda x: (-x.residual_r2, -x.paired_count, x.axis_id))
            if candidates:
                status = "REPRESENTATION_FRONTIER"
        payload = {
            "hypothesis_id": hypothesis.hypothesis_id,
            "input_axes": list(hypothesis.input_axes),
            "target_axis": hypothesis.target_axis,
            "residual_mse": {"numerator": mse.numerator, "denominator": mse.denominator},
            "candidate_axes": [x.to_json() for x in candidates],
            "status": status,
            "provenance": list(provenance),
        }
        return FrontierAssessment(
            frontier_id=digest_json(payload, namespace=b"SCIENCEATLAS_AI_FRONTIER_V1")[:24],
            hypothesis_id=hypothesis.hypothesis_id,
            input_axes=hypothesis.input_axes,
            target_axis=hypothesis.target_axis,
            residual_mse=mse,
            max_abs_residual=max_abs,
            candidate_axes=tuple(candidates),
            status=status,
            provenance=provenance,
        )


class RepresentationProposalOwner:
    spec = OwnerSpec(
        owner_id="representation-proposal-owner/1.0.0",
        capability="representation.autonomous_proposal",
        input_types=("frontier_assessment", "representation_graph"),
        output_types=("representation_proposal",),
        validity_domain="research-local representation changes only",
        uncertainty_contract="proposal does not promote a coordinate to scientific truth",
        cost_model="O(A) over ranked frontier axes",
        deterministic=True,
        replayable=True,
        falsification_contract="proposal is retained only if subsequent validation improves explanatory/predictive performance",
        owner_kind="representation",
    )

    def propose(self, *, frontier: FrontierAssessment, axes: Mapping[str, Axis]) -> tuple[RepresentationProposal, ...]:
        proposals: list[RepresentationProposal] = []
        active_domains = {axes[a].domain for a in (*frontier.input_axes, frontier.target_axis) if a in axes}
        for score in frontier.candidate_axes:
            if score.axis_id not in axes:
                continue
            source_axes = tuple(dict.fromkeys((*frontier.input_axes, score.axis_id)))
            candidate_axis = axes[score.axis_id]
            cross_domain = candidate_axis.domain not in active_domains
            action = "REQUIRE_TYPED_CROSS_DOMAIN_BRIDGE" if cross_domain else "ACTIVATE_EXISTING_AXIS"
            payload = {
                "action": action,
                "frontier_id": frontier.frontier_id,
                "source_axes": list(source_axes),
                "target_axis": frontier.target_axis,
                "score": score.to_json(),
                "candidate_domain": candidate_axis.domain,
            }
            proposals.append(
                RepresentationProposal(
                    proposal_id=digest_json(payload, namespace=b"SCIENCEATLAS_AI_REPRESENTATION_PROPOSAL_V1")[:24],
                    action=action,
                    source_frontier_id=frontier.frontier_id,
                    source_axes=source_axes,
                    target_axis=frontier.target_axis,
                    proposed_axis_id=score.axis_id,
                    semantic_type=candidate_axis.semantic_type,
                    domain=candidate_axis.domain,
                    unit=candidate_axis.unit,
                    score=score.residual_r2,
                    rationale=(
                        "residual-correlated axis is in another scientific domain; require an explicit typed Atlas bridge and symbol/dimensional mapping before activation"
                        if cross_domain else
                        "existing axis covaries with current model residual; activate as a competing representation, not as causal truth"
                    ),
                )
            )
        if not proposals and frontier.status == "UNEXPLAINED_RESIDUAL":
            axis_id = f"residual::{frontier.target_axis}::{frontier.hypothesis_id}"
            target = axes[frontier.target_axis]
            payload = {
                "action": "BIRTH_DIAGNOSTIC_RESIDUAL_AXIS",
                "frontier_id": frontier.frontier_id,
                "axis_id": axis_id,
                "target_axis": frontier.target_axis,
            }
            proposals.append(
                RepresentationProposal(
                    proposal_id=digest_json(payload, namespace=b"SCIENCEATLAS_AI_REPRESENTATION_PROPOSAL_V1")[:24],
                    action="BIRTH_DIAGNOSTIC_RESIDUAL_AXIS",
                    source_frontier_id=frontier.frontier_id,
                    source_axes=frontier.input_axes,
                    target_axis=frontier.target_axis,
                    proposed_axis_id=axis_id,
                    semantic_type="model_residual",
                    domain=target.domain,
                    unit=target.unit,
                    score=frontier.residual_mse,
                    rationale="materialize signed model residual as a research diagnostic coordinate so missing-context owners can inspect structured failure",
                )
            )
        if not proposals:
            payload = {"action": "NO_ACTION", "frontier_id": frontier.frontier_id, "status": frontier.status}
            proposals.append(
                RepresentationProposal(
                    proposal_id=digest_json(payload, namespace=b"SCIENCEATLAS_AI_REPRESENTATION_PROPOSAL_V1")[:24],
                    action="NO_ACTION",
                    source_frontier_id=frontier.frontier_id,
                    source_axes=frontier.input_axes,
                    target_axis=frontier.target_axis,
                    proposed_axis_id=None,
                    semantic_type=None,
                    domain=None,
                    unit=None,
                    score=Fraction(0),
                    rationale="frontier is closed or lacks an evidenced representation move",
                )
            )
        return tuple(proposals)

class AdaptiveSubspaceExplorerOwner:
    """Selection owner for sparse, branch-preserving axis-subset exploration.

    The owner does not fit scientific models itself.  Model fitting remains with
    the existing hypothesis owners.  This owner only ranks candidates, preserves
    exploration branches and proposes which unused axes should extend a retained
    subspace.  Execution budgets are per-run controls, never semantic ceilings.
    """

    spec = OwnerSpec(
        owner_id="adaptive-subspace-explorer-owner/1.0.0",
        capability="research.adaptive_subspace_explorer",
        input_types=("subspace_candidates", "frontier_scores", "axis_pool"),
        output_types=("retained_subspaces", "axis_expansion_order"),
        validity_domain="research-local sparse subset search over typed represented axes",
        uncertainty_contract="selection metrics are diagnostics; branch retention does not promote a candidate to scientific truth",
        cost_model="best-first sparse expansion; explicit execution budget; no fixed semantic order ceiling",
        deterministic=True,
        replayable=True,
        falsification_contract="retained branches must survive held-out prediction, robustness checks or discriminating experiments; unexplained branches remain OPEN rather than FALSE",
        owner_kind="search",
    )

    @staticmethod
    def _quality_key(candidate: SubspaceCandidate) -> tuple[Any, ...]:
        status_rank = {
            "CLOSED_ON_OBSERVED_DATA": 0,
            "PROMISING": 1,
            "CANDIDATE": 2,
            "EXPLORATION": 3,
            "OPEN_GAP": 4,
            "UNKNOWN": 5,
            "PRUNED": 6,
            "EXPANDED": 7,
        }
        missing = candidate.cv_mse is None
        mse = candidate.cv_mse if candidate.cv_mse is not None else Fraction(10**60)
        return (
            status_rank.get(candidate.status, 99),
            missing,
            mse,
            -candidate.predictive_gain,
            -candidate.experiment_discrimination,
            -candidate.residual_signal,
            -candidate.sample_count,
            candidate.complexity,
            -len(candidate.domains),
            candidate.input_axes,
            candidate.subspace_id,
        )

    def select_for_expansion(
        self,
        candidates: Sequence[SubspaceCandidate],
        *,
        beam_width: int,
        exploration_width: int,
        gap_width: int,
    ) -> dict[str, str]:
        if beam_width < 1 or exploration_width < 0 or gap_width < 0:
            raise ValueError("invalid subspace branch widths")
        evaluated = [c for c in candidates if c.cv_mse is not None]
        predictive = [c for c in evaluated if c.predictive_gain > 0 or c.cv_mse == 0]
        predictive.sort(key=self._quality_key)
        selected: dict[str, str] = {}
        for candidate in predictive[:beam_width]:
            selected[candidate.subspace_id] = "PREDICTIVE_FRONTIER"

        # Preserve a deterministic quota of non-leading branches.  This is
        # required because a genuine k-way interaction can have zero marginal
        # or lower-order predictive gain for every proper subset.
        remaining = [c for c in evaluated if c.subspace_id not in selected]
        remaining.sort(key=lambda c: (len(c.domains), c.input_axes, c.subspace_id))
        for candidate in remaining[:exploration_width]:
            selected[candidate.subspace_id] = "HIGHER_ORDER_EXPLORATION"

        gaps = [c for c in candidates if c.status == "OPEN_GAP" and c.subspace_id not in selected]
        gaps.sort(key=lambda c: (-len(c.domains), c.input_axes, c.subspace_id))
        for candidate in gaps[:gap_width]:
            selected[candidate.subspace_id] = "OPEN_GAP_PRESERVATION"
        return selected

    @staticmethod
    def expansion_axis_order(
        *,
        parent: SubspaceCandidate,
        axis_pool: Sequence[str],
        residual_rank: Sequence[str],
        axis_domains: Mapping[str, str],
        fair_cursor: int,
        expansion_width: int,
        exploration_width: int,
    ) -> tuple[tuple[str, ...], int]:
        if expansion_width < 0 or exploration_width < 0:
            raise ValueError("invalid expansion widths")
        used = set(parent.input_axes)
        available = [a for a in axis_pool if a not in used]
        chosen: list[str] = []

        # First use residual/frontier evidence where available.
        for axis_id in residual_rank:
            if axis_id in available and axis_id not in chosen:
                chosen.append(axis_id)
                if len(chosen) >= expansion_width:
                    break

        # Preserve at least one new-domain direction when possible.  This is a
        # navigation heuristic, not a claim that cross-domain composition is valid.
        parent_domains = set(parent.domains)
        for axis_id in available:
            if len(chosen) >= expansion_width:
                break
            if axis_id not in chosen and axis_domains.get(axis_id) not in parent_domains:
                chosen.append(axis_id)

        for axis_id in available:
            if len(chosen) >= expansion_width:
                break
            if axis_id not in chosen:
                chosen.append(axis_id)

        # Fair rotation through the remaining universe prevents permanently
        # starving axes that have weak marginal diagnostics.
        fair_pool = [a for a in available if a not in chosen]
        if fair_pool and exploration_width:
            start = fair_cursor % len(fair_pool)
            for offset in range(min(exploration_width, len(fair_pool))):
                axis_id = fair_pool[(start + offset) % len(fair_pool)]
                if axis_id not in chosen:
                    chosen.append(axis_id)
            fair_cursor = (start + min(exploration_width, len(fair_pool))) % len(fair_pool)
        return tuple(chosen), fair_cursor


class DetachedOwner:
    """Persisted owner contract without an attached external executor.

    This preserves registry identity/integrity across state restore.  Execution is
    fail-closed until the corresponding external distribution is mounted again.
    """

    def __init__(self, spec: OwnerSpec) -> None:
        self.spec = spec

    def invoke(self, **kwargs: Any) -> Any:
        raise RuntimeError(f"owner {self.spec.owner_id} is detached; mount its external executor before invocation")

class HypergraphRouteOwner:
    """Authoritative route-ranking owner for typed owner-connected research paths.

    Structural reachability comes from the mounted Atlas registry service. This
    owner only ranks already validated routes for one fixed target axis. It does
    not infer missing dimensions, symbols or bridges.
    """

    spec = OwnerSpec(
        owner_id="owner-hypergraph-route-owner/1.0.0",
        capability="reasoning.owner_hypergraph.route_rank",
        input_types=("typed_structural_route", "experiment_disagreement", "residual_score"),
        output_types=("ranked_hypergraph_route",),
        validity_domain="routes share one target axis/unit and have PASS lowering+dimensional gates",
        uncertainty_contract="UNKNOWN/BLOCKED routes are never promoted by ranking",
        cost_model="deterministic lexicographic ranking over admitted routes; no fixed route-count ceiling",
        deterministic=True,
        replayable=True,
        falsification_contract="selected route must survive replay, route-specific residuals and discriminating experiment",
        owner_kind="reasoning",
    )

    @staticmethod
    def rank(routes: Sequence[Any]) -> tuple[Any, ...]:
        admitted = [
            r for r in routes
            if getattr(r, "lowering_status", None) == "PASS"
            and getattr(r, "dimensional_status", None) == "PASS"
            and getattr(r, "status", None) not in {"BLOCKED", "UNKNOWN"}
        ]
        # Utility is comparable only because runtime calls this owner for one
        # target axis/unit. Residual MSE is a secondary minimization criterion.
        return tuple(sorted(
            admitted,
            key=lambda r: (
                -getattr(r, "expected_discrimination"),
                -getattr(r, "route_utility"),
                getattr(r, "residual_mse") if getattr(r, "residual_mse") is not None else Fraction(10**18),
                getattr(r, "path_cost"),
                getattr(r, "route_id"),
            ),
        ))
