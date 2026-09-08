"""Methodological owners for dimension/null-calibrated ScienceAtlas research.

This module implements the source-grounded methodological gates from
``ATLAS_paper_v1.0.md`` without making the adaptive explorer a second model
owner.  The explorer navigates axis subsets; these owners determine whether a
subset is structurally admissible and whether data-derived evidence survives
scientific qualification.

Important boundaries:
- dimensional analysis nominates/filters representations; it does not choose F;
- convention checks detect representation artifacts before data;
- derivability is exact only for the declared monomial closure; otherwise UNKNOWN;
- collapse and regime scores are diagnostics, not truth promotion;
- pipeline null calibration reruns the whole adaptive procedure on permuted targets.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from math import gcd
from typing import Any, Iterable, Mapping, Sequence

from .owners import OwnerSpec
from .provenance import digest_json

BASE_DIMENSIONS = ("L", "M", "T", "I", "Theta", "N", "J")


def parse_exponent(value: str | int | Fraction) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return Fraction(value, 1)
    text = str(value).strip()
    if not text:
        raise ValueError("blank dimension exponent")
    return Fraction(text)


def _lcm(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return abs(a * b) // gcd(a, b)


def canonical_integer_vector(values: Sequence[Fraction]) -> tuple[int, ...]:
    if not values:
        return ()
    denominator = 1
    for value in values:
        denominator = _lcm(denominator, value.denominator)
    ints = [int(value * denominator) for value in values]
    nonzero = [abs(v) for v in ints if v]
    if not nonzero:
        return tuple(0 for _ in ints)
    common = nonzero[0]
    for value in nonzero[1:]:
        common = gcd(common, value)
    ints = [v // common for v in ints]
    first = next((v for v in ints if v), 1)
    if first < 0:
        ints = [-v for v in ints]
    return tuple(ints)


def rref(matrix: Sequence[Sequence[Fraction]]) -> tuple[list[list[Fraction]], tuple[int, ...]]:
    if not matrix:
        return [], ()
    width = len(matrix[0])
    a = [[Fraction(v) for v in row] for row in matrix]
    if any(len(row) != width for row in a):
        raise ValueError("ragged matrix")
    pivots: list[int] = []
    row = 0
    for col in range(width):
        pivot = next((r for r in range(row, len(a)) if a[r][col] != 0), None)
        if pivot is None:
            continue
        a[row], a[pivot] = a[pivot], a[row]
        pv = a[row][col]
        a[row] = [x / pv for x in a[row]]
        for r in range(len(a)):
            if r == row:
                continue
            factor = a[r][col]
            if factor:
                a[r] = [x - factor * y for x, y in zip(a[r], a[row], strict=True)]
        pivots.append(col)
        row += 1
        if row == len(a):
            break
    return a, tuple(pivots)


def matrix_rank(matrix: Sequence[Sequence[Fraction]]) -> int:
    if not matrix:
        return 0
    return len(rref(matrix)[1])


def nullspace(matrix: Sequence[Sequence[Fraction]]) -> tuple[tuple[Fraction, ...], ...]:
    if not matrix:
        return ()
    reduced, pivots = rref(matrix)
    width = len(reduced[0]) if reduced else 0
    free = [c for c in range(width) if c not in pivots]
    basis: list[tuple[Fraction, ...]] = []
    pivot_row = {col: i for i, col in enumerate(pivots)}
    for free_col in free:
        vector = [Fraction(0) for _ in range(width)]
        vector[free_col] = Fraction(1)
        for pivot_col in reversed(pivots):
            rr = pivot_row[pivot_col]
            vector[pivot_col] = -sum(
                (reduced[rr][c] * vector[c] for c in free if c > pivot_col),
                Fraction(0),
            )
        basis.append(tuple(vector))
    return tuple(basis)


def _dimension_matrix(axis_dimensions: Mapping[str, Sequence[str]], axis_order: Sequence[str], *, drop_rows: Iterable[int] = ()) -> list[list[Fraction]]:
    dropped = set(int(x) for x in drop_rows)
    rows: list[list[Fraction]] = []
    for i in range(7):
        if i in dropped:
            continue
        rows.append([parse_exponent(axis_dimensions[axis][i]) for axis in axis_order])
    return rows


def _is_dimensionless(dim: Sequence[str]) -> bool:
    return all(parse_exponent(v) == 0 for v in dim)


def dimensional_kernel(
    axis_dimensions: Mapping[str, Sequence[str] | None],
    *,
    drop_rows: Iterable[int] = (),
) -> dict[str, Any]:
    missing = tuple(sorted(axis for axis, dim in axis_dimensions.items() if dim is None))
    if missing:
        return {
            "status": "UNKNOWN_DIMENSION_METADATA",
            "missing_axes": list(missing),
            "dimensionful_axes": [],
            "side_axes": [],
            "rank": None,
            "nullity": None,
            "groups": [],
        }
    dimensions = {axis: tuple(str(x) for x in dim or ()) for axis, dim in axis_dimensions.items()}
    side_axes = tuple(sorted(axis for axis, dim in dimensions.items() if _is_dimensionless(dim)))
    dimensionful_axes = tuple(sorted(axis for axis in dimensions if axis not in side_axes))
    if not dimensionful_axes:
        return {
            "status": "SIDE_AXIS_ONLY",
            "missing_axes": [],
            "dimensionful_axes": [],
            "side_axes": list(side_axes),
            "rank": 0,
            "nullity": 0,
            "groups": [],
        }
    matrix = _dimension_matrix(dimensions, dimensionful_axes, drop_rows=drop_rows)
    rank = matrix_rank(matrix)
    basis = nullspace(matrix)
    groups: list[dict[str, int]] = []
    for vector in basis:
        ints = canonical_integer_vector(vector)
        groups.append({axis: exp for axis, exp in zip(dimensionful_axes, ints, strict=True) if exp})
    groups.sort(key=lambda g: (sum(abs(v) for v in g.values()), tuple(sorted(g.items()))))
    nullity = len(dimensionful_axes) - rank
    return {
        "status": "PASS" if nullity > 0 else "NO_DIMENSIONLESS_GROUP",
        "missing_axes": [],
        "dimensionful_axes": list(dimensionful_axes),
        "side_axes": list(side_axes),
        "rank": rank,
        "nullity": nullity,
        "groups": groups,
    }


def group_complexity(group: Mapping[str, int]) -> int:
    return sum(abs(int(v)) for v in group.values())


def canonical_group(group: Mapping[str, int]) -> tuple[tuple[str, int], ...]:
    axes = tuple(sorted(str(a) for a, e in group.items() if int(e)))
    if not axes:
        return ()
    vec = canonical_integer_vector([Fraction(int(group[a]), 1) for a in axes])
    return tuple((a, e) for a, e in zip(axes, vec, strict=True) if e)


def _vector_for_group(group: Mapping[str, int], universe: Sequence[str]) -> list[Fraction]:
    return [Fraction(int(group.get(axis, 0)), 1) for axis in universe]


def group_in_span(candidate: Mapping[str, int], known_groups: Sequence[Mapping[str, int]]) -> bool:
    if not known_groups:
        return False
    universe = tuple(sorted(set(candidate).union(*(set(g) for g in known_groups))))
    known_rows = [_vector_for_group(g, universe) for g in known_groups]
    rank_before = matrix_rank(known_rows)
    rank_after = matrix_rank([*known_rows, _vector_for_group(candidate, universe)])
    return rank_after == rank_before


def _decimal_fraction(value: Fraction) -> Decimal:
    return Decimal(value.numerator) / Decimal(value.denominator)


def _mean(values: Sequence[Decimal]) -> Decimal:
    return sum(values, Decimal(0)) / Decimal(len(values))


def _std(values: Sequence[Decimal]) -> Decimal:
    if not values:
        return Decimal(0)
    mean = _mean(values)
    var = sum(((v - mean) ** 2 for v in values), Decimal(0)) / Decimal(len(values))
    return var.sqrt()


def collapse_from_pi_group(
    *,
    group: Mapping[str, int],
    target_axis: str,
    rows: Sequence[tuple[str, Mapping[str, Fraction], Fraction]],
    nbins: int = 12,
    min_pts: int = 6,
) -> dict[str, Any]:
    """Paper-compatible one-coordinate collapse when a pi group contains target.

    For pi = y^a prod x_i^b_i = const we bin by
    log(z) = -sum_i (b_i/a) log(x_i), so y ~ z locally.  This avoids
    fabricating irrational exact values while preserving the log-space criterion.
    """
    target_exp = int(group.get(target_axis, 0))
    if target_exp == 0:
        return {"status": "UNKNOWN_NO_TARGET_COUPLED_PI_GROUP", "score_ppm": None}
    if nbins < 2 or min_pts < 2:
        raise ValueError("invalid collapse bin contract")
    points: list[tuple[Decimal, Decimal]] = []
    with localcontext() as ctx:
        ctx.prec = 50
        for _sample, xs, y in rows:
            if y <= 0:
                return {"status": "UNKNOWN_NONPOSITIVE_TARGET", "score_ppm": None}
            logz = Decimal(0)
            for axis, exponent in group.items():
                if axis == target_axis or not exponent:
                    continue
                value = xs.get(axis)
                if value is None or value <= 0:
                    return {"status": "UNKNOWN_NONPOSITIVE_PREDICTOR", "score_ppm": None}
                logz -= (Decimal(exponent) / Decimal(target_exp)) * _decimal_fraction(value).ln()
            points.append((logz, _decimal_fraction(y).ln()))
        if len(points) < nbins * min_pts:
            return {
                "status": "UNKNOWN_INSUFFICIENT_COLLAPSE_SUPPORT",
                "score_ppm": None,
                "point_count": len(points),
                "required_point_count": nbins * min_pts,
            }
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        x_min, x_max = min(xs), max(xs)
        y_std = _std(ys)
        if x_max == x_min or y_std == 0:
            return {"status": "UNKNOWN_DEGENERATE_COLLAPSE", "score_ppm": None}
        width = (x_max - x_min) / Decimal(nbins)
        within: list[Decimal] = []
        for i in range(nbins):
            lo = x_min + Decimal(i) * width
            hi = x_min + Decimal(i + 1) * width
            bucket = [y for x, y in points if (lo <= x < hi) or (i == nbins - 1 and x == x_max)]
            if len(bucket) >= min_pts:
                within.append(_std(bucket))
        if not within:
            return {"status": "UNKNOWN_EMPTY_COLLAPSE_BINS", "score_ppm": None}
        score = _mean(within) / y_std
        ppm = int((score * Decimal(1_000_000)).to_integral_value())
        return {
            "status": "PASS" if ppm <= 150_000 else "FAIL",
            "score_ppm": ppm,
            "score_decimal": format(score, "f"),
            "bin_count": len(within),
            "point_count": len(points),
        }


@dataclass(frozen=True, slots=True)
class DimensionalMethodOwner:
    spec = OwnerSpec(
        owner_id="dimensional-method-owner/1.0.0",
        capability="methodology.dimensional_nomination",
        input_types=("typed_axes", "dimension_profiles"),
        output_types=("pi_kernel_receipt", "structural_nomination"),
        validity_domain="seven-base-dimension exact rational exponents; dimensionless/context axes are side coordinates",
        uncertainty_contract="missing dimensions produce UNKNOWN; no guessed dimension is admitted",
        cost_model="exact rational rank/nullspace over selected subspace; pre-data",
        deterministic=True,
        replayable=True,
        falsification_contract="candidate structural nomination is invalid if declared dimensions or mechanism profile are wrong",
        owner_kind="methodology",
    )

    def assess(
        self,
        *,
        axis_dimensions: Mapping[str, Sequence[str] | None],
        profiles: Mapping[str, Mapping[str, Sequence[str]]] | None = None,
    ) -> dict[str, Any]:
        profile_map = {"DEFAULT": {}}
        for profile_id, overrides in sorted((profiles or {}).items()):
            profile_map[str(profile_id)] = {str(k): tuple(str(x) for x in v) for k, v in overrides.items()}
        profile_results: dict[str, Any] = {}
        for profile_id, overrides in profile_map.items():
            dims = dict(axis_dimensions)
            for axis_id, dim in overrides.items():
                if axis_id in dims:
                    dims[axis_id] = dim
            result = dimensional_kernel(dims)
            result["minimum_group_complexity"] = min((group_complexity(g) for g in result.get("groups", ())), default=None)
            profile_results[profile_id] = result
        statuses = {r["status"] for r in profile_results.values()}
        if "PASS" in statuses or "SIDE_AXIS_ONLY" in statuses:
            structural = "PASS"
        elif "UNKNOWN_DIMENSION_METADATA" in statuses:
            structural = "OPEN_GAP"
        else:
            structural = "REJECT_DIMENSIONAL"
        payload = {
            "schema": "scienceatlas-ai-dimensional-nomination-v1",
            "structural_status": structural,
            "profiles": profile_results,
            "claim_boundary": {
                "pi_kernel_defines_function_F": False,
                "dimensionless_side_axis_is_deleted": False,
                "missing_dimension_is_assumed_dimensionless": False,
            },
        }
        payload["digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_DIMENSIONAL_NOMINATION_V1")
        return payload


@dataclass(frozen=True, slots=True)
class ConventionInvariantOwner:
    spec = OwnerSpec(
        owner_id="convention-invariance-owner/1.0.0",
        capability="methodology.convention_invariance",
        input_types=("typed_axes", "dimension_profiles"),
        output_types=("convention_receipt",),
        validity_domain="representation-convention diagnostics before data; amount/count equivalence implemented exactly",
        uncertainty_contract="a changed nullity is an artifact warning for that representation, not a statement about nature",
        cost_model="repeat exact rank/nullspace under declared convention transforms",
        deterministic=True,
        replayable=True,
        falsification_contract="artifact diagnosis is withdrawn if the convention transform is not physically admissible for the selected quantities",
        owner_kind="methodology",
    )

    def assess_amount_count_convention(
        self, *, axis_dimensions: Mapping[str, Sequence[str] | None], enabled: bool = False
    ) -> dict[str, Any]:
        if not enabled:
            payload = {
                "status": "PASS",
                "artifact": False,
                "tested": False,
                "reason": "no declared physically-equivalent amount/count convention transform for this subspace",
            }
        elif any(dim is None for dim in axis_dimensions.values()):
            payload = {"status": "UNKNOWN_DIMENSION_METADATA", "artifact": None, "tested": True}
        else:
            full = dimensional_kernel(axis_dimensions)
            collapsed = dimensional_kernel(axis_dimensions, drop_rows=(5,))
            p_full = full.get("nullity")
            p_collapsed = collapsed.get("nullity")
            sensitive = any(
                dim is not None and parse_exponent(dim[5]) != 0
                for dim in axis_dimensions.values()
            )
            artifact = bool(sensitive and p_full is not None and p_collapsed is not None and p_full != p_collapsed)
            payload = {
                "status": "ARTIFACT" if artifact else "PASS",
                "artifact": artifact,
                "convention": "AMOUNT_AS_BASE_DIMENSION_vs_COUNTING_COORDINATE",
                "p_full": p_full,
                "p_convention_collapsed": p_collapsed,
                "amount_sensitive": sensitive,
                "tested": True,
            }
        payload["schema"] = "scienceatlas-ai-convention-invariance-v1"
        payload["digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_CONVENTION_INVARIANCE_V1")
        return payload


@dataclass(frozen=True, slots=True)
class KnownLawDerivabilityOwner:
    spec = OwnerSpec(
        owner_id="known-law-derivability-owner/1.0.0",
        capability="methodology.known_law_derivability",
        input_types=("pi_groups", "accepted_monomial_relations"),
        output_types=("derivability_receipt",),
        validity_domain="exact monomial exponent-vector closure only; arbitrary symbolic theorem proving is outside this owner",
        uncertainty_contract="unsupported symbolic forms return UNKNOWN rather than NOT_DERIVED",
        cost_model="exact rational row-span membership",
        deterministic=True,
        replayable=True,
        falsification_contract="DERIVED requires an accepted relation basis whose provenance remains valid",
        owner_kind="methodology",
    )

    def assess(self, *, groups: Sequence[Mapping[str, int]], known_groups: Sequence[Mapping[str, int]]) -> dict[str, Any]:
        if not groups:
            status = "UNKNOWN_NO_PI_GROUP"
            details: list[dict[str, Any]] = []
        elif not known_groups:
            status = "UNKNOWN_NO_DECLARED_MONOMIAL_CLOSURE"
            details = [{"group": dict(g), "derived": None} for g in groups]
        else:
            details = [{"group": dict(g), "derived": group_in_span(g, known_groups)} for g in groups]
            if all(row["derived"] is True for row in details):
                status = "KNOWN_DERIVED"
            elif any(row["derived"] is False for row in details):
                status = "NOT_DERIVED_IN_DECLARED_MONOMIAL_CLOSURE"
            else:
                status = "UNKNOWN"
        payload = {
            "schema": "scienceatlas-ai-known-law-derivability-v1",
            "status": status,
            "groups": details,
            "known_group_count": len(known_groups),
            "claim_boundary": {"not_derived_in_monomial_closure_means_world_novel": False},
        }
        payload["digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_DERIVABILITY_V1")
        return payload


@dataclass(frozen=True, slots=True)
class DataCollapseOwner:
    spec = OwnerSpec(
        owner_id="data-collapse-owner/1.0.0",
        capability="methodology.data_collapse",
        input_types=("pi_group", "multi_system_observations"),
        output_types=("collapse_receipt",),
        validity_domain="positive quantities for log-space collapse; target-coupled one-coordinate pi group",
        uncertainty_contract="collapse is evidence of shared representation, not causal proof or canonical parameterization",
        cost_model="O(N log N) deterministic binning",
        deterministic=True,
        replayable=True,
        falsification_contract="candidate fails this gate when normalized within-bin scatter exceeds preregistered threshold",
        owner_kind="methodology",
    )

    def assess(self, **kwargs: Any) -> dict[str, Any]:
        payload = collapse_from_pi_group(**kwargs)
        payload["schema"] = "scienceatlas-ai-data-collapse-v1"
        payload["digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_DATA_COLLAPSE_V1")
        return payload


@dataclass(frozen=True, slots=True)
class RegimeHoldoutOwner:
    spec = OwnerSpec(
        owner_id="regime-holdout-owner/1.0.0",
        capability="methodology.regime_holdout",
        input_types=("hypothesis_owner", "regime_partitioned_rows"),
        output_types=("regime_holdout_receipt",),
        validity_domain="two or more explicitly non-overlapping regime labels; fit delegated to existing hypothesis owner",
        uncertainty_contract="missing/ambiguous regime labels return UNKNOWN; random within-regime holdout is not substituted",
        cost_model="leave-one-regime-out refit using existing owner",
        deterministic=True,
        replayable=True,
        falsification_contract="candidate is falsified for transfer when prediction fails in a preregistered held-out regime",
        owner_kind="methodology",
    )

    def assess(
        self,
        *,
        fit_owner: Any,
        input_axes: tuple[str, ...],
        target_axis: str,
        rows: Sequence[tuple[str, Mapping[str, Fraction], Fraction]],
        regime_by_sample: Mapping[str, str],
    ) -> dict[str, Any]:
        missing_samples = tuple(sorted(sample for sample, _, _ in rows if sample not in regime_by_sample or not str(regime_by_sample.get(sample, "")).strip()))
        regimes = tuple(sorted({str(regime_by_sample[s]) for s, _, _ in rows if s in regime_by_sample and str(regime_by_sample[s]).strip()}))
        if missing_samples:
            payload = {
                "status": "UNKNOWN_INCOMPLETE_REGIME_LABELS",
                "regime_count": len(regimes),
                "missing_sample_count": len(missing_samples),
                "best_family": None,
                "regime_mse": None,
            }
        elif len(regimes) < 2:
            payload = {
                "status": "UNKNOWN_REGIME_HOLDOUT_REQUIRED",
                "regime_count": len(regimes),
                "best_family": None,
                "regime_mse": None,
            }
        else:
            errors: dict[str, list[Fraction]] = {}
            expected_points: dict[str, int] = {}
            complexities: dict[str, int] = {}
            for held_regime in regimes:
                train = [(xs, y) for sample, xs, y in rows if regime_by_sample.get(sample) != held_regime]
                held = [(sample, xs, y) for sample, xs, y in rows if regime_by_sample.get(sample) == held_regime]
                if not train or not held:
                    continue
                proposals = fit_owner.propose(
                    tuple(train),
                    input_axes=input_axes,
                    target_axis=target_axis,
                    provenance=(),
                )
                for hypothesis in proposals:
                    local: list[Fraction] = []
                    valid = True
                    for _sample, xs, observed in held:
                        try:
                            predicted = fit_owner.predict(hypothesis, xs)
                        except (ValueError, ZeroDivisionError, KeyError, TypeError):
                            valid = False
                            break
                        local.append((predicted - observed) ** 2)
                    if valid and local:
                        errors.setdefault(hypothesis.family, []).extend(local)
                        expected_points[hypothesis.family] = expected_points.get(hypothesis.family, 0) + len(local)
                        complexities[hypothesis.family] = hypothesis.complexity
            comparable = []
            total_points = sum(1 for sample, _, _ in rows if sample in regime_by_sample)
            for family, sq in errors.items():
                if expected_points.get(family, 0) != total_points:
                    continue
                mse = sum(sq, Fraction(0)) / len(sq)
                comparable.append((mse, complexities.get(family, 10**9), family))
            if not comparable:
                payload = {
                    "status": "UNKNOWN_NO_COMMON_REGIME_MODEL",
                    "regime_count": len(regimes),
                    "best_family": None,
                    "regime_mse": None,
                }
            else:
                mse, complexity, family = min(comparable, key=lambda row: (row[0], row[1], row[2]))
                payload = {
                    "status": "PASS",
                    "regime_count": len(regimes),
                    "regimes": list(regimes),
                    "best_family": family,
                    "complexity": complexity,
                    "regime_mse": {"numerator": mse.numerator, "denominator": mse.denominator},
                }
        payload["schema"] = "scienceatlas-ai-regime-holdout-v1"
        payload["claim_boundary"] = {"random_within_regime_holdout_substituted": False, "regime_pass_means_law": False}
        payload["digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_REGIME_HOLDOUT_V1")
        return payload


def pi_group_value(*, group: Mapping[str, int], values: Mapping[str, Fraction]) -> Fraction:
    """Evaluate an integer-exponent dimensionless group exactly.

    This helper is deliberately limited to rational observations and integer
    exponents produced by the exact dimensional kernel.  It never invents a
    floating representation.
    """
    result = Fraction(1)
    for axis, exponent in group.items():
        exponent = int(exponent)
        if not exponent:
            continue
        if axis not in values:
            raise KeyError(axis)
        value = Fraction(values[axis])
        if value == 0 and exponent < 0:
            raise ZeroDivisionError(f"pi group has negative exponent on zero axis: {axis}")
        result *= value ** exponent
    return result


@dataclass(frozen=True, slots=True)
class SystemCoverageOwner:
    """Classify the empirical scope of a candidate without promoting truth.

    Stage 7 of the source paper asks whether a collapse spans distinct systems.
    It does not state that single-system candidates are false, so this owner
    classifies scope instead of using system count as an automatic rejection.
    """

    spec = OwnerSpec(
        owner_id="system-coverage-owner/1.0.0",
        capability="methodology.system_coverage",
        input_types=("system_partitioned_rows",),
        output_types=("system_coverage_receipt",),
        validity_domain="explicit system_id/system labels attached to evidence; no inferred system identity",
        uncertainty_contract="missing labels produce UNKNOWN; one-system evidence remains local rather than false",
        cost_model="O(N) deterministic scope accounting",
        deterministic=True,
        replayable=True,
        falsification_contract="cross-system scope is withdrawn if labels collapse to one system or are not independently grounded",
        owner_kind="methodology",
    )

    def assess(
        self,
        *,
        rows: Sequence[tuple[str, Mapping[str, Fraction], Fraction]],
        system_by_sample: Mapping[str, str],
        minimum_cross_system_count: int = 2,
    ) -> dict[str, Any]:
        if minimum_cross_system_count < 2:
            raise ValueError("minimum_cross_system_count must be >=2")
        sample_ids = [sample for sample, _xs, _y in rows]
        missing = tuple(sorted(sample for sample in sample_ids if not str(system_by_sample.get(sample, "")).strip()))
        systems = tuple(sorted({str(system_by_sample[s]).strip() for s in sample_ids if str(system_by_sample.get(s, "")).strip()}))
        counts = {system: sum(1 for sample in sample_ids if str(system_by_sample.get(sample, "")).strip() == system) for system in systems}
        if missing:
            status = "UNKNOWN_INCOMPLETE_SYSTEM_LABELS"
            scope = "UNKNOWN"
        elif len(systems) >= minimum_cross_system_count:
            status = "PASS_CROSS_SYSTEM"
            scope = "CROSS_SYSTEM"
        elif len(systems) == 1:
            status = "LOCAL_ONLY"
            scope = "SINGLE_SYSTEM"
        else:
            status = "UNKNOWN_SYSTEM_COVERAGE_REQUIRED"
            scope = "UNKNOWN"
        payload = {
            "schema": "scienceatlas-ai-system-coverage-v1",
            "status": status,
            "scope": scope,
            "system_count": len(systems),
            "systems": list(systems),
            "counts": counts,
            "missing_sample_count": len(missing),
            "minimum_cross_system_count": minimum_cross_system_count,
            "claim_boundary": {
                "single_system_candidate_is_false": False,
                "cross_system_coverage_means_universal_law": False,
                "system_identity_inferred_from_axis_domain": False,
            },
        }
        payload["digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_SYSTEM_COVERAGE_V1")
        return payload


@dataclass(frozen=True, slots=True)
class PiTransitionOwner:
    """Preregistered coverage/diagnostic for the paper's stage ``pi ~ 1``.

    The attached paper names this stage but does not specify a unique test
    statistic.  Consequently this owner does *not* invent a significance test.
    It checks whether an exact pi coordinate and a separately declared observable
    provide measurements below, near and above one, and reports descriptive
    observable means.  Establishing a transition requires a separately declared
    falsification/statistical contract.
    """

    spec = OwnerSpec(
        owner_id="pi-transition-owner/1.0.0",
        capability="methodology.pi_transition",
        input_types=("pi_group", "transition_observable", "preregistered_pi_band"),
        output_types=("pi_transition_coverage_receipt",),
        validity_domain="exact integer-exponent pi group; explicit distinct transition observable; preregistered positive band lower<1<upper",
        uncertainty_contract="coverage is descriptive only; no transition significance is inferred without a separate declared test",
        cost_model="O(N) exact pi evaluation plus descriptive rational summaries",
        deterministic=True,
        replayable=True,
        falsification_contract="transition claim cannot be tested if data do not cover both sides and the preregistered neighborhood of pi=1",
        owner_kind="methodology",
    )

    def assess(
        self,
        *,
        group: Mapping[str, int],
        rows: Sequence[tuple[str, Mapping[str, Fraction], Fraction]],
        transition_observable_by_sample: Mapping[str, Fraction],
        lower: Fraction,
        upper: Fraction,
    ) -> dict[str, Any]:
        lower = Fraction(lower)
        upper = Fraction(upper)
        if not (Fraction(0) < lower < Fraction(1) < upper):
            raise ValueError("pi transition band must satisfy 0 < lower < 1 < upper")
        buckets: dict[str, list[Fraction]] = {"below": [], "near": [], "above": []}
        missing_observable = 0
        invalid_pi = 0
        for sample, xs, y in rows:
            values = dict(xs)
            # Target may participate in the pi group; rows store it separately.
            for axis in group:
                if axis not in values:
                    # The caller can include the target under its axis name in xs;
                    # otherwise this row cannot instantiate that pi coordinate.
                    invalid_pi += 1
                    values = {}
                    break
            if not values:
                continue
            try:
                pi_value = pi_group_value(group=group, values=values)
            except (KeyError, ZeroDivisionError):
                invalid_pi += 1
                continue
            observable = transition_observable_by_sample.get(sample)
            if observable is None:
                missing_observable += 1
                continue
            observable = Fraction(observable)
            if pi_value < lower:
                buckets["below"].append(observable)
            elif pi_value > upper:
                buckets["above"].append(observable)
            else:
                buckets["near"].append(observable)
        counts = {key: len(values) for key, values in buckets.items()}
        means = {
            key: None if not values else {"numerator": (sum(values, Fraction(0)) / len(values)).numerator, "denominator": (sum(values, Fraction(0)) / len(values)).denominator}
            for key, values in buckets.items()
        }
        coverage = all(counts[key] > 0 for key in ("below", "near", "above"))
        payload = {
            "schema": "scienceatlas-ai-pi-transition-coverage-v1",
            "status": "PASS_COVERAGE" if coverage else "UNKNOWN_TRANSITION_COVERAGE",
            "band": {
                "lower": {"numerator": lower.numerator, "denominator": lower.denominator},
                "upper": {"numerator": upper.numerator, "denominator": upper.denominator},
            },
            "counts": counts,
            "observable_means": means,
            "missing_observable_count": missing_observable,
            "invalid_pi_count": invalid_pi,
            "transition_established": False,
            "claim_boundary": {
                "paper_supplies_unique_transition_test_statistic": False,
                "coverage_means_transition": False,
                "descriptive_mean_difference_means_causality": False,
            },
        }
        payload["digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_PI_TRANSITION_V1")
        return payload


@dataclass(frozen=True, slots=True)
class PipelineNullCalibrationOwner:
    spec = OwnerSpec(
        owner_id="pipeline-null-calibration-owner/1.0.1",
        capability="methodology.pipeline_null",
        input_types=("whole_pipeline_statistic", "permutation_statistics"),
        output_types=("familywise_null_receipt",),
        validity_domain="same adaptive pipeline rerun on permuted target under fixed configuration",
        uncertainty_contract="finite permutation count yields an empirical null; no asymptotic p-value is invented",
        cost_model="pipeline_cost * permutation_count",
        deterministic=True,
        replayable=True,
        falsification_contract="candidate loses calibrated status unless the exact finite-permutation p-value is within the preregistered level; insufficient permutation resolution fails closed",
        owner_kind="methodology",
    )

    def assess(self, *, observed: Fraction, null_statistics: Sequence[Fraction], alpha_bp: int = 500) -> dict[str, Any]:
        if not null_statistics:
            payload = {"status": "UNKNOWN_NO_NULL_RUNS", "observed": {"numerator": observed.numerator, "denominator": observed.denominator}}
        else:
            stats = sorted(Fraction(v) for v in null_statistics)
            if not 0 < alpha_bp < 10_000:
                raise ValueError("alpha_bp must be in (0,10000)")
            # family-wise upper threshold: empirical (1-alpha) quantile, conservative index
            numerator = (10_000 - alpha_bp) * len(stats)
            index = min(len(stats) - 1, max(0, (numerator + 9_999) // 10_000 - 1))
            threshold = stats[index]
            exceed = sum(1 for value in stats if value >= observed)
            p = Fraction(exceed + 1, len(stats) + 1)
            resolution = Fraction(1, len(stats) + 1)
            alpha = Fraction(alpha_bp, 10_000)
            if resolution > alpha:
                status = "INSUFFICIENT_NULL_RESOLUTION"
            else:
                status = "PASS" if p <= alpha else "FAIL"
            payload = {
                "status": status,
                "observed": {"numerator": observed.numerator, "denominator": observed.denominator},
                "threshold": {"numerator": threshold.numerator, "denominator": threshold.denominator},
                "permutation_count": len(stats),
                "alpha_bp": alpha_bp,
                "empirical_p": {"numerator": p.numerator, "denominator": p.denominator},
                "min_achievable_p": {"numerator": resolution.numerator, "denominator": resolution.denominator},
                "permutations_required_for_alpha": max(1, -(-10_000 // alpha_bp) - 1),
                "null_min": {"numerator": stats[0].numerator, "denominator": stats[0].denominator},
                "null_max": {"numerator": stats[-1].numerator, "denominator": stats[-1].denominator},
            }
        payload["schema"] = "scienceatlas-ai-whole-pipeline-null-v1"
        payload["claim_boundary"] = {"permutation_pass_means_law": False}
        payload["digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_PIPELINE_NULL_V1")
        return payload
