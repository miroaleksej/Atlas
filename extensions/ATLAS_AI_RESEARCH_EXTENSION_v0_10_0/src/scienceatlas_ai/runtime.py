"""ScienceAtlas-native research runtime v0.10.0.

The runtime orchestrates representations, world state, hypothesis owners,
residual/frontier discovery, representation proposals, discriminating
experiments, external Atlas owner mounting and validated meta-learning.
Domain algorithms remain behind owners; the runtime contains orchestration only.
"""
from __future__ import annotations

from dataclasses import replace
import random
from fractions import Fraction
from itertools import combinations
from math import comb
from typing import Any, Iterable, Mapping, Sequence

from .ai_lab import ModelExecutionBackend, build_laboratory_owners
from .owners import (
    AdaptiveSubspaceExplorerOwner,
    DetachedOwner,
    MultiAxisMechanismOwner,
    NumericMechanismOwner,
    HypergraphRouteOwner,
    OwnerBus,
    OwnerSpec,
    RepresentationProposalOwner,
    ResidualFrontierOwner,
)
from .methodology import (
    ConventionInvariantOwner,
    DataCollapseOwner,
    DimensionalMethodOwner,
    KnownLawDerivabilityOwner,
    PipelineNullCalibrationOwner,
    PiTransitionOwner,
    RegimeHoldoutOwner,
    SystemCoverageOwner,
    canonical_group,
    group_complexity,
    pi_group_value,
)
from .provenance import ProvenanceTrace, digest_json, mapping_root
from .types import (
    Axis,
    CriticVector,
    DimensionHypothesisProfile,
    EvidenceRecord,
    ExperimentPlan,
    FrontierAssessment,
    AxisSymbolBinding,
    HypergraphRoute,
    Hypothesis,
    KnownMonomialRelation,
    Observation,
    RepresentationProposal,
    SemanticQuantity,
    SubspaceCandidate,
    SubspaceSearchState,
    ValidationOutcome,
    ValidityDomain,
    as_fraction,
    fraction_json,
)


class RepresentationGraph:
    def __init__(self, axes: Mapping[str, Axis] | None = None) -> None:
        self.axes: dict[str, Axis] = dict(axes or {})

    def add(self, axis: Axis) -> None:
        if axis.axis_id in self.axes:
            raise ValueError(f"axis already exists: {axis.axis_id}")
        if axis.parent_axis_id is not None and axis.parent_axis_id not in self.axes:
            raise ValueError(f"parent axis does not exist: {axis.parent_axis_id}")
        self.axes[axis.axis_id] = axis

    def birth(
        self,
        *,
        axis_id: str,
        name: str,
        semantic_type: str,
        domain: str,
        unit: str,
        validity: ValidityDomain | None = None,
        parent_axis_id: str | None = None,
        quantity_id: str | None = None,
        dimension: Sequence[str] | None = None,
        aliases: Sequence[str] = (),
        unit_system: str = "SI",
        convention_tags: Sequence[str] = (),
    ) -> Axis:
        axis = Axis(
            axis_id=axis_id,
            name=name,
            semantic_type=semantic_type,
            domain=domain,
            unit=unit,
            validity=validity or ValidityDomain(),
            parent_axis_id=parent_axis_id,
            quantity_id=quantity_id,
            dimension=None if dimension is None else tuple(str(x) for x in dimension),
            aliases=tuple(str(x) for x in aliases),
            unit_system=str(unit_system),
            convention_tags=tuple(str(x) for x in convention_tags),
        )
        self.add(axis)
        return axis

    def refine(self, axis_id: str, *, validity: ValidityDomain, name: str | None = None) -> Axis:
        current = self.axes[axis_id]
        refined = replace(
            current,
            name=current.name if name is None else name,
            validity=validity,
            revision=current.revision + 1,
            status="refined",
        )
        self.axes[axis_id] = refined
        return refined

    def split(self, axis_id: str, children: Sequence[Axis]) -> tuple[Axis, ...]:
        if not children:
            raise ValueError("axis split requires at least one child")
        parent = self.axes[axis_id]
        for child in children:
            if child.parent_axis_id != axis_id:
                raise ValueError("split child must point to parent axis")
            self.add(child)
        self.axes[axis_id] = replace(parent, revision=parent.revision + 1, status="split")
        return tuple(children)

    def to_json(self) -> dict[str, Any]:
        return {axis_id: self.axes[axis_id].to_json() for axis_id in sorted(self.axes)}

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "RepresentationGraph":
        return cls({str(k): Axis.from_json(v) for k, v in payload.items()})


class WorldModel:
    def __init__(
        self,
        observations: Iterable[Observation] = (),
        evidence: Mapping[str, EvidenceRecord] | None = None,
    ) -> None:
        self.observations: list[Observation] = list(observations)
        self.evidence: dict[str, EvidenceRecord] = dict(evidence or {})

    def observe(self, observation: Observation, evidence: EvidenceRecord, axis: Axis) -> None:
        if observation.axis_id != axis.axis_id:
            raise ValueError("observation axis mismatch")
        q = observation.quantity
        if q.semantic_type != axis.semantic_type or q.domain != axis.domain or q.unit != axis.unit or q.unit_system != axis.unit_system:
            raise TypeError(
                f"semantic mismatch for axis {axis.axis_id}: "
                f"expected ({axis.semantic_type},{axis.domain},{axis.unit},{axis.unit_system}), "
                f"got ({q.semantic_type},{q.domain},{q.unit},{q.unit_system})"
            )
        if axis.quantity_id is not None and q.quantity_id != axis.quantity_id:
            raise TypeError(f"quantity_id mismatch for axis {axis.axis_id}: expected {axis.quantity_id}, got {q.quantity_id}")
        if axis.dimension is not None and q.dimension != axis.dimension:
            raise TypeError(f"dimension mismatch for axis {axis.axis_id}: expected {axis.dimension}, got {q.dimension}")
        if not axis.validity.contains(q.value):
            raise ValueError(f"observation outside axis validity: {axis.axis_id}")
        if observation.evidence_id != evidence.evidence_id:
            raise ValueError("observation/evidence id mismatch")
        previous = self.evidence.get(evidence.evidence_id)
        if previous is not None and previous != evidence:
            raise ValueError(f"evidence id collision: {evidence.evidence_id}")
        self.evidence[evidence.evidence_id] = evidence
        self.observations.append(observation)

    def _best_measurement(self, sample_id: str, axis_id: str) -> Observation | None:
        candidates = [
            obs
            for obs in self.observations
            if obs.sample_id == sample_id
            and obs.axis_id == axis_id
            and self.evidence.get(obs.evidence_id) is not None
            and self.evidence[obs.evidence_id].status == "support"
        ]
        if not candidates:
            return None
        candidates.sort(
            key=lambda obs: (
                self.evidence[obs.evidence_id].reliability_bp,
                obs.evidence_id,
            ),
            reverse=True,
        )
        return candidates[0]

    def sample_ids(self) -> tuple[str, ...]:
        return tuple(sorted({obs.sample_id for obs in self.observations}))

    def rows_for_axes(
        self,
        input_axes: Sequence[str],
        target_axis: str,
    ) -> tuple[tuple[str, dict[str, Fraction], Fraction], ...]:
        axes = tuple(str(x) for x in input_axes)
        if not axes:
            return ()
        rows: list[tuple[str, dict[str, Fraction], Fraction]] = []
        for sample_id in self.sample_ids():
            target = self._best_measurement(sample_id, target_axis)
            if target is None:
                continue
            xs: dict[str, Fraction] = {}
            complete = True
            for axis_id in axes:
                obs = self._best_measurement(sample_id, axis_id)
                if obs is None:
                    complete = False
                    break
                xs[axis_id] = obs.quantity.value
            if complete:
                rows.append((sample_id, xs, target.quantity.value))
        return tuple(rows)

    def paired_rows(self, input_axis: str, target_axis: str) -> tuple[tuple[Fraction, Fraction], ...]:
        return tuple((xs[input_axis], y) for _, xs, y in self.rows_for_axes((input_axis,), target_axis))

    def provenance_for_axes(self, axis_ids: Sequence[str]) -> tuple[str, ...]:
        target = set(axis_ids)
        ids = {
            obs.evidence_id
            for obs in self.observations
            if obs.axis_id in target and self.evidence.get(obs.evidence_id) is not None
        }
        return tuple(sorted(ids))

    def values_for_axis(self, axis_id: str) -> tuple[Fraction, ...]:
        return tuple(obs.quantity.value for obs in self.observations if obs.axis_id == axis_id)

    def values_by_sample(self, axis_id: str) -> dict[str, Fraction]:
        result: dict[str, Fraction] = {}
        for sample_id in self.sample_ids():
            obs = self._best_measurement(sample_id, axis_id)
            if obs is not None:
                result[sample_id] = obs.quantity.value
        return result

    def to_json(self) -> dict[str, Any]:
        return {
            "observations": [obs.to_json() for obs in self.observations],
            "evidence": {k: self.evidence[k].to_json() for k in sorted(self.evidence)},
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "WorldModel":
        return cls(
            observations=(Observation.from_json(row) for row in payload.get("observations", [])),
            evidence={str(k): EvidenceRecord.from_json(v) for k, v in payload.get("evidence", {}).items()},
        )


class CriticEnsemble:
    @staticmethod
    def evaluate(
        hypotheses: Sequence[Hypothesis],
        rows: Sequence[tuple[str, Mapping[str, Fraction], Fraction]],
        *,
        owner_bus: OwnerBus,
        target_axis: Axis,
        previously_validated_families: set[str],
    ) -> dict[str, CriticVector]:
        scores: dict[str, CriticVector] = {}
        for hypothesis in hypotheses:
            owner = owner_bus.get(hypothesis.owner_id)
            errors: list[Fraction] = []
            violations = 0
            for _, xs, observed in rows:
                try:
                    predicted = owner.predict(hypothesis, xs)
                except (ValueError, ZeroDivisionError, KeyError, TypeError):
                    violations += 1
                    continue
                if not target_axis.validity.contains(predicted):
                    violations += 1
                errors.append(predicted - observed)
            if errors:
                mse = sum((e * e for e in errors), Fraction(0)) / len(errors)
                max_abs = max(abs(e) for e in errors)
            else:
                mse = Fraction(10**30)
                max_abs = Fraction(10**30)
                violations += max(1, len(rows))
            scores[hypothesis.hypothesis_id] = CriticVector(
                hypothesis_id=hypothesis.hypothesis_id,
                prediction_mse=mse,
                max_abs_error=max_abs,
                constraint_violations=violations,
                complexity=hypothesis.complexity,
                novelty_rank=0 if hypothesis.family in previously_validated_families else 1,
            )
        return scores

    @staticmethod
    def pareto_frontier(scores: Mapping[str, CriticVector]) -> tuple[str, ...]:
        def dominates(a: CriticVector, b: CriticVector) -> bool:
            a_values = (
                a.prediction_mse,
                a.max_abs_error,
                a.constraint_violations,
                a.complexity,
                -a.novelty_rank,
            )
            b_values = (
                b.prediction_mse,
                b.max_abs_error,
                b.constraint_violations,
                b.complexity,
                -b.novelty_rank,
            )
            return all(x <= y for x, y in zip(a_values, b_values, strict=True)) and any(
                x < y for x, y in zip(a_values, b_values, strict=True)
            )

        ids = sorted(scores)
        return tuple(
            hid for hid in ids if not any(dominates(scores[other], scores[hid]) for other in ids if other != hid)
        )


class MetaLearner:
    """Strategy adaptation driven only by externally validated outcomes."""

    def __init__(self, scores_bp: Mapping[str, int] | None = None) -> None:
        self.scores_bp: dict[str, int] = {str(k): int(v) for k, v in (scores_bp or {}).items()}
        self.validated_families: set[str] = set()

    def score(self, owner_id: str) -> int:
        return self.scores_bp.get(owner_id, 5_000)

    def update(self, outcome: ValidationOutcome) -> int:
        previous = self.score(outcome.owner_id)
        centered = outcome.prediction_gain_bp - 5_000
        success_term = 500 if outcome.success else -500
        updated = max(0, min(10_000, previous + centered // 4 + success_term))
        self.scores_bp[outcome.owner_id] = updated
        return updated

    def to_json(self) -> dict[str, Any]:
        return {
            "scores_bp": {k: self.scores_bp[k] for k in sorted(self.scores_bp)},
            "validated_families": sorted(self.validated_families),
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "MetaLearner":
        obj = cls(payload.get("scores_bp", {}))
        obj.validated_families = {str(x) for x in payload.get("validated_families", [])}
        return obj


class ScienceAtlasAI:
    VERSION = "0.10.0"
    RUNTIME_CONTRACT = {
        "architecture": "scienceatlas-native-research-intelligence",
        "objective": "dimension-first+convention-invariant+known-law-aware+adaptive-subspace-search+regime-holdout+whole-pipeline-null+owner-connected-hypergraph+higher-order-hypotheses+discriminating-experiment+ai-laboratory-execution",
        "forbidden_cognitive_objectives": ["hash_target_distance", "secp256k1_scalar_distance"],
        "semantic_quantity_contract": "signed+typed+domain+unit+validity+uncertainty",
        "owner_rule": "one-authoritative-owner-per-exact-capability",
        "external_atlas_rule": "mount-real-owner-registry-by-digest; detached-restore-fails-closed-for-execution",
        "external_numeric_rule": "external floating diagnostics remain external; no implicit float-to-exact-Fraction admission",
        "cross_domain_rule": "built-in numeric composition fails closed until typed Atlas bridge plus exact axis-to-symbol quantity/unit/dimension lowering",
        "hypergraph_rule": "owner routes are admitted only from canonical Atlas passports+ACTIVE bridges; unknown lowering never becomes a route",
        "subspace_rule": "search sparse axis subsets adaptively; preserve higher-order exploration and OPEN gaps; never require all registered axes simultaneously",
        "methodology_rule": "structural nomination and convention/derivability gates precede data-driven scoring; scientific candidate status additionally requires regime holdout and whole-pipeline null calibration",
        "dimension_rule": "dimension may depend on declared mechanism profile; missing dimensions are UNKNOWN; dimensionless/context coordinates are side axes rather than automatic pi-rank inflation",
        "literature_rule": "absence from literature is neutral and never rejects an internally retained candidate",
        "ai_laboratory_rule": "real AI measurements require an attached backend attesting one architecture family at three scales plus explicit R/V/M/W/E budget controls and all requested regime evaluators; fixture backends cannot produce scientific measurements",
        "subspace_order_ceiling": None,
        "axis_ceiling": None,
        "hypothesis_ceiling": None,
        "owner_visit_ceiling": None,
    }

    def __init__(self, *, register_baseline_owner: bool = True) -> None:
        self.representation = RepresentationGraph()
        self.world = WorldModel()
        self.owner_bus = OwnerBus()
        if register_baseline_owner:
            self.owner_bus.register(NumericMechanismOwner())
            self.owner_bus.register(MultiAxisMechanismOwner())
            self.owner_bus.register(ResidualFrontierOwner())
            self.owner_bus.register(RepresentationProposalOwner())
            self.owner_bus.register(HypergraphRouteOwner())
            self.owner_bus.register(AdaptiveSubspaceExplorerOwner())
            self.owner_bus.register(DimensionalMethodOwner())
            self.owner_bus.register(ConventionInvariantOwner())
            self.owner_bus.register(KnownLawDerivabilityOwner())
            self.owner_bus.register(DataCollapseOwner())
            self.owner_bus.register(SystemCoverageOwner())
            self.owner_bus.register(PiTransitionOwner())
            self.owner_bus.register(RegimeHoldoutOwner())
            self.owner_bus.register(PipelineNullCalibrationOwner())
            laboratory, laboratory_contracts = build_laboratory_owners()
            self.owner_bus.register(laboratory)
            for laboratory_contract in laboratory_contracts:
                self.owner_bus.register(laboratory_contract)
        self.hypotheses: dict[str, Hypothesis] = {}
        self.critic_scores: dict[str, CriticVector] = {}
        self.frontiers: dict[str, FrontierAssessment] = {}
        self.representation_proposals: dict[str, RepresentationProposal] = {}
        self.experiments: dict[str, ExperimentPlan] = {}
        self.hypergraph_routes: dict[str, HypergraphRoute] = {}
        self.hypergraph_queries: dict[str, dict[str, Any]] = {}
        self.last_hypergraph_query_digest: str = ""
        self.subspace_candidates: dict[str, SubspaceCandidate] = {}
        self.subspace_searches: dict[str, SubspaceSearchState] = {}
        self.dimension_profiles: dict[str, DimensionHypothesisProfile] = {}
        self.known_monomial_relations: dict[str, KnownMonomialRelation] = {}
        self.methodology_records: dict[str, dict[str, Any]] = {}
        self.qualification_runs: dict[str, dict[str, Any]] = {}
        self.laboratory_runs: dict[str, dict[str, Any]] = {}
        self.meta = MetaLearner()
        self.trace = ProvenanceTrace()
        self.freezes: dict[str, str] = {}
        self.atlas_registry_snapshot: dict[str, Any] = {}

    @property
    def runtime_contract_digest(self) -> str:
        return digest_json(self.RUNTIME_CONTRACT, namespace=b"SCIENCEATLAS_AI_RUNTIME_CONTRACT_V6")

    def _append_trace(self, event: Mapping[str, Any]) -> None:
        self.trace = self.trace.append(event)

    @staticmethod
    def _normalize_axes(*, input_axis: str | None = None, input_axes: Sequence[str] | None = None) -> tuple[str, ...]:
        if input_axes is None:
            if input_axis is None:
                raise ValueError("input_axis or input_axes is required")
            axes = (str(input_axis),)
        else:
            axes = tuple(dict.fromkeys(str(x) for x in input_axes))
            if input_axis is not None and input_axis not in axes:
                axes = (str(input_axis), *axes)
        if not axes:
            raise ValueError("at least one input axis is required")
        return axes


    def _observed_axis_pool(self, target_axis: str) -> tuple[str, ...]:
        if target_axis not in self.representation.axes:
            raise KeyError(target_axis)
        target_values = self.world.values_by_sample(target_axis)
        result: list[str] = []
        for axis_id, axis in sorted(self.representation.axes.items()):
            if axis_id == target_axis or axis.status == "retired":
                continue
            values = self.world.values_by_sample(axis_id)
            paired = set(values).intersection(target_values)
            if len(paired) >= 2:
                result.append(axis_id)
        return tuple(result)

    @staticmethod
    def _variance(values: Sequence[Fraction]) -> Fraction:
        if not values:
            return Fraction(0)
        mean = sum(values, Fraction(0)) / len(values)
        return sum(((v - mean) ** 2 for v in values), Fraction(0)) / len(values)

    def register_dimension_profile(
        self,
        *,
        profile_id: str,
        label: str,
        overrides: Mapping[str, Sequence[str]],
        provenance: Sequence[str] = (),
    ) -> DimensionHypothesisProfile:
        if profile_id in self.dimension_profiles:
            raise ValueError(f"dimension profile already exists: {profile_id}")
        missing = [axis_id for axis_id in overrides if axis_id not in self.representation.axes]
        if missing:
            raise KeyError(f"dimension profile references unknown axes: {missing}")
        profile = DimensionHypothesisProfile(
            profile_id=str(profile_id),
            label=str(label),
            overrides=tuple((str(axis_id), tuple(str(x) for x in dim)) for axis_id, dim in sorted(overrides.items())),
            provenance=tuple(str(x) for x in provenance),
        )
        self.dimension_profiles[profile.profile_id] = profile
        self._append_trace({"kind": "dimension_profile_register", "profile": profile.to_json()})
        return profile

    def register_known_monomial_relation(
        self,
        *,
        relation_id: str,
        exponents: Mapping[str, int],
        provenance: Sequence[str] = (),
    ) -> KnownMonomialRelation:
        if relation_id in self.known_monomial_relations:
            raise ValueError(f"known relation already exists: {relation_id}")
        missing = [axis_id for axis_id in exponents if axis_id not in self.representation.axes]
        if missing:
            raise KeyError(f"known relation references unknown axes: {missing}")
        relation = KnownMonomialRelation(
            relation_id=str(relation_id),
            exponents=tuple((str(axis), int(exp)) for axis, exp in sorted(exponents.items()) if int(exp)),
            provenance=tuple(str(x) for x in provenance),
        )
        self.known_monomial_relations[relation.relation_id] = relation
        self._append_trace({"kind": "known_monomial_relation_register", "relation": relation.to_json()})
        return relation

    def _profile_overrides_for_axes(self, axes: Sequence[str]) -> dict[str, dict[str, tuple[str, ...]]]:
        selected = set(str(x) for x in axes)
        result: dict[str, dict[str, tuple[str, ...]]] = {}
        for profile_id, profile in sorted(self.dimension_profiles.items()):
            overrides = {axis_id: dim for axis_id, dim in profile.overrides if axis_id in selected}
            if overrides:
                result[profile_id] = overrides
        return result

    def _axis_dimensions(self, axes: Sequence[str]) -> dict[str, tuple[str, ...] | None]:
        return {axis_id: self.representation.axes[axis_id].dimension for axis_id in axes}

    @staticmethod
    def _apply_dimension_overrides(
        base: Mapping[str, tuple[str, ...] | None],
        overrides: Mapping[str, Sequence[str]],
    ) -> dict[str, tuple[str, ...] | None]:
        result = dict(base)
        for axis_id, dim in overrides.items():
            if axis_id in result:
                result[axis_id] = tuple(str(x) for x in dim)
        return result

    def assess_dimensional_structure(
        self,
        *,
        axis_ids: Sequence[str],
    ) -> Mapping[str, Any]:
        axes = tuple(dict.fromkeys(str(x) for x in axis_ids))
        if not axes:
            raise ValueError("at least one axis is required")
        missing = [axis_id for axis_id in axes if axis_id not in self.representation.axes]
        if missing:
            raise KeyError(f"unknown axes: {missing}")
        dim_owner = self.owner_bus.for_capability("methodology.dimensional_nomination")
        conv_owner = self.owner_bus.for_capability("methodology.convention_invariance")
        deriv_owner = self.owner_bus.for_capability("methodology.known_law_derivability")
        base_dims = self._axis_dimensions(axes)
        profiles = self._profile_overrides_for_axes(axes)
        dimensional = dim_owner.assess(axis_dimensions=base_dims, profiles=profiles)
        profile_details: dict[str, Any] = {}
        known_groups = [dict(relation.exponents) for relation in self.known_monomial_relations.values()]
        amount_count_enabled = any(
            "amount_count_equivalence" in self.representation.axes[a].convention_tags
            for a in axes
        )
        for profile_id, dim_result in sorted(dimensional.get("profiles", {}).items()):
            overrides = {} if profile_id == "DEFAULT" else profiles.get(profile_id, {})
            effective_dims = self._apply_dimension_overrides(base_dims, overrides)
            convention = conv_owner.assess_amount_count_convention(
                axis_dimensions=effective_dims, enabled=amount_count_enabled
            )
            groups = [dict(g) for g in dim_result.get("groups", ())]
            derivability = deriv_owner.assess(groups=groups, known_groups=known_groups)
            dim_status = str(dim_result.get("status", "UNKNOWN"))
            if dim_status == "UNKNOWN_DIMENSION_METADATA":
                profile_status = "OPEN_GAP"
            elif dim_status == "NO_DIMENSIONLESS_GROUP":
                profile_status = "REJECT_DIMENSIONAL"
            elif dim_status == "SIDE_AXIS_ONLY":
                profile_status = "PASS_SIDE_AXIS"
            elif convention.get("status") == "ARTIFACT":
                profile_status = "ARTIFACT"
            elif derivability.get("status") == "KNOWN_DERIVED":
                profile_status = "KNOWN_DERIVED"
            else:
                profile_status = "PASS"
            profile_details[profile_id] = {
                "status": profile_status,
                "dimension": dim_result,
                "convention": convention,
                "derivability": derivability,
            }
        statuses = {str(row.get("status")) for row in profile_details.values()}
        if statuses.intersection({"PASS", "PASS_SIDE_AXIS"}):
            overall = "PASS"
        elif "OPEN_GAP" in statuses:
            overall = "OPEN_GAP"
        elif "KNOWN_DERIVED" in statuses and statuses <= {"KNOWN_DERIVED", "ARTIFACT", "REJECT_DIMENSIONAL"}:
            overall = "KNOWN_DERIVED"
        elif "ARTIFACT" in statuses and statuses <= {"ARTIFACT", "REJECT_DIMENSIONAL"}:
            overall = "ARTIFACT"
        else:
            overall = "REJECT_DIMENSIONAL"
        admissible_groups: list[dict[str, int]] = []
        complexities: list[int] = []
        for row in profile_details.values():
            if row["status"] not in {"PASS", "PASS_SIDE_AXIS"}:
                continue
            for group in row["dimension"].get("groups", ()):
                cg = dict(canonical_group(group))
                if cg and cg not in admissible_groups:
                    admissible_groups.append(cg)
                    complexities.append(group_complexity(cg))
        unit_systems = sorted({self.representation.axes[a].unit_system for a in axes})
        payload = {
            "schema": "scienceatlas-ai-unified-structural-methodology-v1",
            "axis_ids": list(axes),
            "status": overall,
            "profile_details": profile_details,
            "admissible_groups": admissible_groups,
            "minimum_pi_complexity": min(complexities) if complexities else None,
            "unit_systems": unit_systems,
            "mixed_unit_systems": len(unit_systems) > 1,
            "claim_boundary": {
                "structural_pass_is_law": False,
                "known_derived_is_world_false": False,
                "artifact_representation_is_new_candidate": False,
                "literature_absence_used": False,
            },
        }
        payload["digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_UNIFIED_STRUCTURAL_METHODOLOGY_V1")
        self.methodology_records[payload["digest"]] = dict(payload)
        self._append_trace({"kind": "dimensional_structure_assessment", "receipt_digest": payload["digest"], "status": overall})
        return payload

    def design_dimension_profile_discriminator(
        self,
        *,
        axis_ids: Sequence[str],
    ) -> Mapping[str, Any]:
        """Design a pre-data experiment when mechanism profiles imply different pi groups."""
        receipt = self.assess_dimensional_structure(axis_ids=axis_ids)
        profile_groups: dict[str, tuple[tuple[str, int], ...]] = {}
        for profile_id, row in receipt.get("profile_details", {}).items():
            if row.get("status") not in {"PASS", "PASS_SIDE_AXIS"}:
                continue
            groups = row.get("dimension", {}).get("groups", ())
            if not groups:
                continue
            group = min((dict(g) for g in groups), key=lambda g: (group_complexity(g), tuple(sorted(g.items()))))
            profile_groups[str(profile_id)] = canonical_group(group)
        unique = {group for group in profile_groups.values()}
        exponent_values: dict[str, set[int]] = {}
        for group in unique:
            mapping = dict(group)
            for axis_id in axis_ids:
                exponent_values.setdefault(str(axis_id), set()).add(int(mapping.get(str(axis_id), 0)))
        varying_axes = tuple(sorted(axis for axis, values in exponent_values.items() if len(values) > 1))
        status = "EXPERIMENT_REQUIRED" if len(unique) >= 2 and varying_axes else "NO_DIMENSION_PROFILE_DISCRIMINATOR"
        payload = {
            "schema": "scienceatlas-ai-dimension-profile-discriminator-v1",
            "status": status,
            "structural_receipt_digest": receipt.get("digest"),
            "profile_groups": {pid: [[a, e] for a, e in group] for pid, group in sorted(profile_groups.items())},
            "varying_axes": list(varying_axes),
            "experiment": (
                "vary the axes whose candidate pi exponents differ while measuring the remaining quantities; test which candidate pi group remains invariant"
                if status == "EXPERIMENT_REQUIRED" else None
            ),
            "claim_boundary": {"experiment_result_known_pre_measurement": False},
        }
        payload["digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_DIMENSION_PROFILE_DISCRIMINATOR_V1")
        self.methodology_records[payload["digest"]] = dict(payload)
        self._append_trace({"kind": "dimension_profile_discriminator", "receipt_digest": payload["digest"], "status": status})
        return payload

    def _candidate_structural_methodology(self, candidate: SubspaceCandidate) -> Mapping[str, Any]:
        participants = (*candidate.input_axes, candidate.target_axis)
        return self.assess_dimensional_structure(axis_ids=participants)

    def _sample_regime_map(
        self,
        *,
        target_axis: str,
        sample_ids: Sequence[str],
    ) -> dict[str, str]:
        result: dict[str, str] = {}
        for sample_id in sample_ids:
            observation = self.world._best_measurement(sample_id, target_axis)
            if observation is None:
                continue
            evidence = self.world.evidence.get(observation.evidence_id)
            if evidence is None:
                continue
            raw = evidence.metadata.get("regime_id", evidence.metadata.get("regime"))
            if raw is not None and str(raw).strip():
                result[sample_id] = str(raw).strip()
        return result

    def _sample_system_map(
        self,
        *,
        target_axis: str,
        sample_ids: Sequence[str],
    ) -> dict[str, str]:
        """Read explicit system identity from evidence; never infer it from domain."""
        result: dict[str, str] = {}
        for sample_id in sample_ids:
            observation = self.world._best_measurement(sample_id, target_axis)
            if observation is None:
                continue
            evidence = self.world.evidence.get(observation.evidence_id)
            if evidence is None:
                continue
            raw = evidence.metadata.get("system_id", evidence.metadata.get("system"))
            if raw is not None and str(raw).strip():
                result[sample_id] = str(raw).strip()
        return result

    def _system_coverage_assessment(
        self,
        *,
        target_axis: str,
        rows: Sequence[tuple[str, Mapping[str, Fraction], Fraction]],
    ) -> Mapping[str, Any]:
        owner = self.owner_bus.for_capability("methodology.system_coverage")
        system_by_sample = self._sample_system_map(
            target_axis=target_axis, sample_ids=[row[0] for row in rows]
        )
        return owner.assess(rows=rows, system_by_sample=system_by_sample)

    def _regime_holdout_assessment(
        self,
        *,
        input_axes: tuple[str, ...],
        target_axis: str,
        rows: Sequence[tuple[str, Mapping[str, Fraction], Fraction]],
    ) -> Mapping[str, Any]:
        capability = "hypothesis.numeric_relation.baseline" if len(input_axes) == 1 else "hypothesis.numeric_relation.multiaxis"
        fit_owner = self.owner_bus.for_capability(capability)
        regime_owner = self.owner_bus.for_capability("methodology.regime_holdout")
        regime_by_sample = self._sample_regime_map(target_axis=target_axis, sample_ids=[row[0] for row in rows])
        return regime_owner.assess(
            fit_owner=fit_owner,
            input_axes=input_axes,
            target_axis=target_axis,
            rows=rows,
            regime_by_sample=regime_by_sample,
        )

    @staticmethod
    def _fraction_from_payload(payload: Mapping[str, Any] | None) -> Fraction | None:
        if not payload:
            return None
        return Fraction(int(payload["numerator"]), int(payload["denominator"]))

    def _post_methodology_assessment(
        self,
        *,
        candidate: SubspaceCandidate,
        structural: Mapping[str, Any],
        rows: Sequence[tuple[str, Mapping[str, Fraction], Fraction]],
    ) -> SubspaceCandidate:
        groups = [dict(g) for g in structural.get("admissible_groups", ())]
        target_groups = [g for g in groups if int(g.get(candidate.target_axis, 0)) != 0]
        collapse: dict[str, Any]
        if target_groups:
            selected_group = min(target_groups, key=lambda g: (group_complexity(g), tuple(sorted(g.items()))))
            collapse_owner = self.owner_bus.for_capability("methodology.data_collapse")
            collapse = collapse_owner.assess(group=selected_group, target_axis=candidate.target_axis, rows=rows)
        elif any(
            row.get("dimension", {}).get("status") == "SIDE_AXIS_ONLY"
            for row in structural.get("profile_details", {}).values()
            if row.get("status") in {"PASS", "PASS_SIDE_AXIS"}
        ):
            collapse = {"status": "NOT_APPLICABLE_SIDE_AXIS_SPACE", "score_ppm": None}
        else:
            collapse = {"status": "UNKNOWN_NO_TARGET_COUPLED_PI_GROUP", "score_ppm": None}
        system_coverage = self._system_coverage_assessment(
            target_axis=candidate.target_axis,
            rows=rows,
        )
        regime = self._regime_holdout_assessment(
            input_axes=candidate.input_axes,
            target_axis=candidate.target_axis,
            rows=rows,
        )
        collapse_status = str(collapse.get("status", "UNKNOWN"))
        system_coverage_status = str(system_coverage.get("status", "UNKNOWN"))
        regime_status = str(regime.get("status", "UNKNOWN"))
        if collapse_status == "FAIL":
            methodology_status = "COLLAPSE_NOT_CONFIRMED"
        elif regime_status != "PASS":
            methodology_status = "REGIME_HOLDOUT_REQUIRED"
        else:
            methodology_status = "AWAITING_PIPELINE_NULL"
        receipt = {
            "schema": "scienceatlas-ai-post-data-methodology-v1",
            "subspace_id": candidate.subspace_id,
            "structural_receipt_digest": structural.get("digest"),
            "collapse": collapse,
            "system_coverage": system_coverage,
            "regime_holdout": regime,
            "status": methodology_status,
            "claim_boundary": {"post_data_pass_is_law": False, "within_regime_loo_substituted_for_regime_holdout": False},
        }
        receipt["digest"] = digest_json(receipt, namespace=b"SCIENCEATLAS_AI_POST_DATA_METHODOLOGY_V1")
        self.methodology_records[receipt["digest"]] = dict(receipt)
        regime_mse = self._fraction_from_payload(regime.get("regime_mse"))
        updated = replace(
            candidate,
            methodology_status=methodology_status,
            collapse_gate=collapse_status,
            system_coverage_gate=system_coverage_status,
            regime_gate=regime_status,
            regime_mse=regime_mse,
            collapse_score_ppm=None if collapse.get("score_ppm") is None else int(collapse["score_ppm"]),
            system_count=None if system_coverage.get("system_count") is None else int(system_coverage["system_count"]),
            methodology_receipt_id=receipt["digest"],
            provenance=tuple(dict.fromkeys((*candidate.provenance, f"methodology:{receipt['digest']}"))),
        )
        self.subspace_candidates[updated.subspace_id] = updated
        return updated

    @staticmethod
    def _validation_gain(candidate: SubspaceCandidate) -> Fraction:
        if candidate.regime_gate != "PASS" or candidate.regime_mse is None or candidate.baseline_mse <= 0:
            return Fraction(0)
        return max(Fraction(0), candidate.baseline_mse - candidate.regime_mse) / candidate.baseline_mse

    def _subspace_cv_score(
        self,
        *,
        input_axes: tuple[str, ...],
        target_axis: str,
        rows: Sequence[tuple[str, Mapping[str, Fraction], Fraction]],
    ) -> tuple[str | None, Fraction | None, int]:
        """Deterministic leave-one-out score delegated to the existing fit owner.

        This method does not implement a parallel regression algorithm.  Every
        fold calls the authoritative numeric hypothesis owner, then evaluates its
        returned families on the held-out row.  A family is comparable only when
        it produced a valid prediction for every fold.
        """
        if len(rows) < 3:
            return None, None, 0
        capability = "hypothesis.numeric_relation.baseline" if len(input_axes) == 1 else "hypothesis.numeric_relation.multiaxis"
        owner = self.owner_bus.for_capability(capability)
        errors: dict[str, list[Fraction]] = {}
        complexities: dict[str, int] = {}
        expected_folds = len(rows)
        for holdout_index in range(expected_folds):
            held = rows[holdout_index]
            train = [row for i, row in enumerate(rows) if i != holdout_index]
            train_rows = tuple((xs, y) for _, xs, y in train)
            proposals = owner.propose(
                train_rows,
                input_axes=input_axes,
                target_axis=target_axis,
                provenance=(),
            )
            for hypothesis in proposals:
                try:
                    predicted = owner.predict(hypothesis, held[1])
                except (ValueError, ZeroDivisionError, KeyError, TypeError):
                    continue
                errors.setdefault(hypothesis.family, []).append((predicted - held[2]) ** 2)
                complexities[hypothesis.family] = hypothesis.complexity
        comparable: list[tuple[Fraction, int, str]] = []
        for family, sq_errors in errors.items():
            if len(sq_errors) != expected_folds:
                continue
            mse = sum(sq_errors, Fraction(0)) / expected_folds
            comparable.append((mse, complexities.get(family, 10**9), family))
        if not comparable:
            return None, None, 0
        mse, complexity, family = min(comparable, key=lambda row: (row[0], row[1], row[2]))
        return family, mse, complexity

    def _subspace_route_authorization(
        self,
        *,
        input_axes: tuple[str, ...],
        target_axis: str,
    ) -> tuple[str, tuple[str, ...], str | None]:
        domains = {self.representation.axes[a].domain for a in (*input_axes, target_axis)}
        if len(domains) <= 1:
            return "PASS", (), None
        if not self.atlas_registry_snapshot or not self.owner_bus.has_capability("atlas.registry.semantic_hypergraph"):
            return "OPEN_GAP", (), "TYPED_CROSS_DOMAIN_ATLAS_ROUTE_REQUIRED"
        routes = self.atlas_hypergraph_plan(input_axes=input_axes, target_axis=target_axis)
        if not routes:
            receipt = self.hypergraph_queries.get(self.last_hypergraph_query_digest, {})
            gap = str(receipt.get("status", "OWNER_BRIDGE_LOWERING_GAP"))
            return "OPEN_GAP", (), gap
        admissible = tuple(sorted(r.route_id for r in routes if r.lowering_status == "PASS" and r.dimensional_status == "PASS"))
        if not admissible:
            return "OPEN_GAP", (), "OWNER_BRIDGE_LOWERING_GAP"
        return "PASS", admissible, None

    def _record_subspace_full_fit(
        self,
        *,
        input_axes: tuple[str, ...],
        target_axis: str,
        route_ids: tuple[str, ...],
        subspace_id: str,
    ) -> tuple[Hypothesis, ...]:
        rows_full = self.world.rows_for_axes(input_axes, target_axis)
        if len(rows_full) < 2:
            return ()
        capability = "hypothesis.numeric_relation.baseline" if len(input_axes) == 1 else "hypothesis.numeric_relation.multiaxis"
        owner = self.owner_bus.for_capability(capability)
        provenance = list(self.world.provenance_for_axes((*input_axes, target_axis)))
        provenance.append(f"adaptive-subspace:{subspace_id}")
        if route_ids:
            auth_digest = digest_json(
                {"route_ids": list(route_ids), "registry": self.atlas_registry_snapshot.get("registry_snapshot_digest", "")},
                namespace=b"SCIENCEATLAS_AI_SUBSPACE_ROUTE_AUTH_V1",
            )
            provenance.extend((
                f"subspace-route-auth:{auth_digest}",
                f"atlas-registry:{self.atlas_registry_snapshot.get('registry_snapshot_digest', '')}",
                *(f"hypergraph-route:{rid}" for rid in route_ids),
            ))
        proposals = owner.propose(
            tuple((xs, y) for _, xs, y in rows_full),
            input_axes=input_axes,
            target_axis=target_axis,
            provenance=tuple(dict.fromkeys(provenance)),
        )
        for hypothesis in proposals:
            self.hypotheses[hypothesis.hypothesis_id] = hypothesis
        if proposals:
            scores = CriticEnsemble.evaluate(
                proposals,
                rows_full,
                owner_bus=self.owner_bus,
                target_axis=self.representation.axes[target_axis],
                previously_validated_families=self.meta.validated_families,
            )
            self.critic_scores.update(scores)
        return proposals

    def _evaluate_subspace_candidate(self, candidate: SubspaceCandidate) -> SubspaceCandidate:
        axes = candidate.input_axes
        target_axis = candidate.target_axis

        # Source-grounded methodological order: structural gates execute before
        # any model fit, residual, marginal relevance or target-driven ranking.
        structural = self._candidate_structural_methodology(candidate)
        structural_status = str(structural.get("status", "OPEN_GAP"))
        profile_rows = list(structural.get("profile_details", {}).values())
        convention_statuses = {str(row.get("convention", {}).get("status", "UNKNOWN")) for row in profile_rows}
        derivability_statuses = {str(row.get("derivability", {}).get("status", "UNKNOWN")) for row in profile_rows}
        convention_gate = "ARTIFACT" if structural_status == "ARTIFACT" or "ARTIFACT" in convention_statuses else ("PASS" if convention_statuses else "UNKNOWN")
        if structural_status == "KNOWN_DERIVED":
            derivability_gate = "KNOWN_DERIVED"
        elif "NOT_DERIVED_IN_DECLARED_MONOMIAL_CLOSURE" in derivability_statuses:
            derivability_gate = "NOT_DERIVED_IN_DECLARED_MONOMIAL_CLOSURE"
        elif "UNKNOWN_NO_DECLARED_MONOMIAL_CLOSURE" in derivability_statuses:
            derivability_gate = "UNKNOWN_NO_DECLARED_MONOMIAL_CLOSURE"
        else:
            derivability_gate = "NOT_APPLICABLE_OR_UNKNOWN"
        mdl_complexity = structural.get("minimum_pi_complexity")
        structural_complexity = int(mdl_complexity) if mdl_complexity is not None else candidate.complexity

        if structural_status in {"ARTIFACT", "KNOWN_DERIVED", "REJECT_DIMENSIONAL"}:
            reason = {
                "ARTIFACT": "CONVENTION_ARTIFACT",
                "KNOWN_DERIVED": "KNOWN_DERIVED",
                "REJECT_DIMENSIONAL": "NO_DIMENSIONALLY_HOMOGENEOUS_RELATION_WITH_CURRENT_PARTICIPANTS",
            }[structural_status]
            updated = replace(
                candidate,
                status="PRUNED",
                retention_reason=reason,
                methodology_status=structural_status,
                structural_gate=structural_status,
                convention_gate=convention_gate,
                derivability_gate=derivability_gate,
                complexity=structural_complexity,
                methodology_receipt_id=str(structural.get("digest", "")) or None,
                provenance=tuple(dict.fromkeys((*candidate.provenance, f"methodology:{structural.get('digest','')}"))),
            )
            self.subspace_candidates[updated.subspace_id] = updated
            return updated
        if structural_status == "OPEN_GAP":
            updated = replace(
                candidate,
                status="OPEN_GAP",
                retention_reason="STRUCTURAL_DIMENSION_GAP",
                methodology_status="STRUCTURAL_GAP",
                structural_gate="OPEN_GAP",
                convention_gate=convention_gate,
                derivability_gate=derivability_gate,
                complexity=structural_complexity,
                gap_kind="MISSING_OR_UNRESOLVED_DIMENSION_METADATA",
                methodology_receipt_id=str(structural.get("digest", "")) or None,
            )
            self.subspace_candidates[updated.subspace_id] = updated
            return updated

        # Only structurally admitted candidates are allowed to touch data.
        rows = self.world.rows_for_axes(axes, target_axis)
        sample_count = len(rows)
        baseline_mse = self._variance([y for _, _, y in rows]) if rows else Fraction(0)
        route_status, route_ids, gap_kind = self._subspace_route_authorization(input_axes=axes, target_axis=target_axis)
        if route_status != "PASS":
            updated = replace(
                candidate,
                status="OPEN_GAP",
                retention_reason="STRUCTURAL_GAP",
                baseline_mse=baseline_mse,
                sample_count=sample_count,
                route_ids=route_ids,
                gap_kind=gap_kind,
                methodology_status="STRUCTURAL_ROUTE_GAP",
                structural_gate="PASS",
                convention_gate=convention_gate,
                derivability_gate=derivability_gate,
                complexity=structural_complexity,
                methodology_receipt_id=str(structural.get("digest", "")) or None,
            )
            self.subspace_candidates[updated.subspace_id] = updated
            return updated
        family, cv_mse, fit_complexity = self._subspace_cv_score(input_axes=axes, target_axis=target_axis, rows=rows)
        if cv_mse is None:
            updated = replace(
                candidate,
                status="OPEN_GAP",
                retention_reason="IDENTIFIABILITY_GAP",
                baseline_mse=baseline_mse,
                sample_count=sample_count,
                route_ids=route_ids,
                gap_kind="INSUFFICIENT_CROSS_VALIDATION_SUPPORT",
                methodology_status="IDENTIFIABILITY_GAP",
                structural_gate="PASS",
                convention_gate=convention_gate,
                derivability_gate=derivability_gate,
                complexity=max(structural_complexity, fit_complexity),
                methodology_receipt_id=str(structural.get("digest", "")) or None,
            )
            self.subspace_candidates[updated.subspace_id] = updated
            return updated
        parent_mse = baseline_mse
        if candidate.parent_id and candidate.parent_id in self.subspace_candidates:
            parent = self.subspace_candidates[candidate.parent_id]
            if parent.cv_mse is not None:
                parent_mse = parent.cv_mse
        if parent_mse > 0:
            gain = max(Fraction(0), parent_mse - cv_mse) / parent_mse
        else:
            gain = Fraction(1) if cv_mse == 0 and baseline_mse > 0 else Fraction(0)
        hypotheses = self._record_subspace_full_fit(
            input_axes=axes,
            target_axis=target_axis,
            route_ids=route_ids,
            subspace_id=candidate.subspace_id,
        )
        best_hypothesis = None
        if family is not None:
            matches = [h for h in hypotheses if h.family == family]
            if matches:
                best_hypothesis = min(matches, key=lambda h: h.hypothesis_id)
        frontier_id = None
        residual_signal = Fraction(0)
        if best_hypothesis is not None:
            unused = {
                axis_id: self.world.values_by_sample(axis_id)
                for axis_id, axis in self.representation.axes.items()
                if axis_id not in axes and axis_id != target_axis and axis.status != "retired"
            }
            frontier_owner = self.owner_bus.for_capability("research.residual_frontier")
            assessment = frontier_owner.assess(
                hypothesis=best_hypothesis,
                hypothesis_owner=self.owner_bus.get(best_hypothesis.owner_id),
                rows=rows,
                unused_axis_values=unused,
                provenance=self.world.provenance_for_axes((*axes, target_axis, *unused.keys())),
            )
            self.frontiers[assessment.frontier_id] = assessment
            frontier_id = assessment.frontier_id
            if assessment.candidate_axes:
                residual_signal = assessment.candidate_axes[0].residual_r2
        discrimination = Fraction(0)
        experiment_id = None
        if len(hypotheses) >= 2:
            experiment = self.design_multiaxis_experiment(
                input_axes=axes,
                target_axis=target_axis,
                hypothesis_ids=[h.hypothesis_id for h in hypotheses],
            )
            if experiment is not None:
                discrimination = experiment.disagreement
                experiment_id = experiment.experiment_id
        if cv_mse == 0:
            status = "CLOSED_ON_OBSERVED_DATA"
            reason = "WITHIN_REGIME_CV_ZERO_ERROR_NOT_YET_LAW"
        elif gain > 0:
            status = "PROMISING"
            reason = "WITHIN_REGIME_PREDICTIVE_GAIN"
        else:
            status = "CANDIDATE"
            reason = "NO_LOWER_ORDER_GAIN_YET"
        provenance = tuple(dict.fromkeys((
            *candidate.provenance,
            *(f"hypothesis:{h.hypothesis_id}" for h in hypotheses),
            *(f"route:{rid}" for rid in route_ids),
            *( () if experiment_id is None else (f"experiment:{experiment_id}",) ),
            f"methodology:{structural.get('digest','')}",
        )))
        updated = replace(
            candidate,
            status=status,
            retention_reason=reason,
            baseline_mse=baseline_mse,
            cv_mse=cv_mse,
            predictive_gain=gain,
            residual_signal=residual_signal,
            experiment_discrimination=discrimination,
            complexity=max(structural_complexity, fit_complexity),
            sample_count=sample_count,
            best_family=family,
            hypothesis_ids=tuple(h.hypothesis_id for h in hypotheses),
            route_ids=route_ids,
            frontier_id=frontier_id,
            gap_kind=None,
            methodology_status="POST_DATA_VALIDATION_REQUIRED",
            structural_gate="PASS",
            convention_gate=convention_gate,
            derivability_gate=derivability_gate,
            methodology_receipt_id=str(structural.get("digest", "")) or None,
            provenance=provenance,
        )
        self.subspace_candidates[updated.subspace_id] = updated
        return self._post_methodology_assessment(candidate=updated, structural=structural, rows=rows)

    def _subspace_shell(
        self,
        *,
        input_axes: Sequence[str],
        target_axis: str,
        parent_id: str | None,
        search_id: str,
    ) -> SubspaceCandidate:
        axes = tuple(sorted(dict.fromkeys(str(x) for x in input_axes)))
        domains = tuple(sorted({self.representation.axes[a].domain for a in axes}))
        subspace_id = digest_json(
            {"input_axes": list(axes), "target_axis": target_axis},
            namespace=b"SCIENCEATLAS_AI_SUBSPACE_V1",
        )[:24]
        existing = self.subspace_candidates.get(subspace_id)
        if existing is not None:
            return existing
        candidate = SubspaceCandidate(
            subspace_id=subspace_id,
            input_axes=axes,
            target_axis=target_axis,
            order=len(axes),
            domains=domains,
            parent_id=parent_id,
            status="CANDIDATE",
            retention_reason="UNASSESSED",
            provenance=(f"subspace-search:{search_id}",),
        )
        self.subspace_candidates[subspace_id] = candidate
        return candidate

    def adaptive_subspace_search(
        self,
        *,
        target_axis: str,
        seed_axes: Sequence[str] | None = None,
        min_order: int = 2,
        run_order_limit: int | None = None,
        expansion_budget: int = 64,
        seed_width: int = 8,
        fair_seed_width: int = 4,
        beam_width: int = 6,
        exploration_width: int = 4,
        gap_width: int = 4,
        expansion_width: int = 4,
        fair_expansion_width: int = 2,
        continuation_search_id: str | None = None,
    ) -> Mapping[str, Any]:
        """Explore sparse axis subsets without a fixed semantic order ceiling.

        ``run_order_limit`` and width/budget arguments bound one concrete run so
        computation remains finite.  Setting ``run_order_limit=None`` leaves the
        order open-ended; the search then stops only on the explicit evaluation
        budget or an exhausted frontier.  Non-improving branches are deliberately
        retained under an exploration quota so pure higher-order interactions are
        discoverable even when every proper subset has zero predictive gain.
        """
        if min_order < 1:
            raise ValueError("min_order must be >= 1")
        if run_order_limit is not None and run_order_limit < min_order:
            raise ValueError("run_order_limit cannot be below min_order")
        if expansion_budget < 1:
            raise ValueError("expansion_budget must be >= 1")
        if min(seed_width, fair_seed_width, beam_width, exploration_width, gap_width, expansion_width, fair_expansion_width) < 0:
            raise ValueError("subspace width controls cannot be negative")
        if beam_width < 1:
            raise ValueError("beam_width must be >= 1")
        pool = self._observed_axis_pool(target_axis)
        if seed_axes is not None:
            supplied = tuple(dict.fromkeys(str(x) for x in seed_axes))
            missing = [a for a in supplied if a not in pool]
            if missing:
                raise ValueError(f"seed axes are not observed with target: {missing}")
        else:
            supplied = ()
        owner = self.owner_bus.for_capability("research.adaptive_subspace_explorer")
        axis_domains = {axis_id: self.representation.axes[axis_id].domain for axis_id in pool}

        if continuation_search_id is not None:
            if continuation_search_id not in self.subspace_searches:
                raise KeyError(continuation_search_id)
            previous = self.subspace_searches[continuation_search_id]
            if previous.target_axis != target_axis:
                raise ValueError("continuation target mismatch")
            search_id = previous.search_id
            pool = previous.axis_pool
            fair_cursor = previous.fair_cursor
            frontier_ids = list(previous.frontier_ids)
            retained_ids = list(previous.retained_ids)
            evaluated_ids = list(previous.evaluated_ids)
            evaluations_used_total = previous.evaluations_used
            budget_this_call = expansion_budget
            combination_space = dict(previous.combination_space_by_order)
            seed_record = previous.seed_axes
            min_order = previous.min_order
            if run_order_limit is None:
                run_order_limit = previous.run_order_limit
        else:
            if len(pool) < min_order:
                payload = {
                    "status": "NO_FRONTIER",
                    "reason": "fewer observed input axes than min_order",
                    "target_axis": target_axis,
                    "axis_pool_count": len(pool),
                    "min_order": min_order,
                    "architecture_order_ceiling": None,
                }
                payload["digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_SUBSPACE_SEARCH_GAP_V1")
                self._append_trace({"kind": "adaptive_subspace_search", "result": payload})
                return payload
            # Pre-data structural seed nomination.  Do not rank axes by target
            # correlation here: the paper's central methodological requirement is
            # that structural reduction precedes access to target-driven scores.
            structural_order = sorted(
                pool,
                key=lambda axis_id: (
                    self.representation.axes[axis_id].dimension is None,
                    self.representation.axes[axis_id].unit_system,
                    self.representation.axes[axis_id].domain,
                    self.representation.axes[axis_id].quantity_id is None,
                    self.representation.axes[axis_id].dimension or (),
                    axis_id,
                ),
            )
            selected: list[str] = list(supplied)
            if not supplied:
                by_domain: dict[str, list[str]] = {}
                for axis_id in structural_order:
                    by_domain.setdefault(axis_domains[axis_id], []).append(axis_id)
                domain_names = sorted(by_domain)
                cursor = 0
                target_seed_count = min(len(pool), seed_width + fair_seed_width)
                while len(selected) < target_seed_count and domain_names:
                    progressed = False
                    for domain in domain_names:
                        rows = by_domain[domain]
                        if cursor < len(rows) and rows[cursor] not in selected:
                            selected.append(rows[cursor])
                            progressed = True
                            if len(selected) >= target_seed_count:
                                break
                    if not progressed:
                        break
                    cursor += 1
                for axis_id in structural_order:
                    if len(selected) >= target_seed_count:
                        break
                    if axis_id not in selected:
                        selected.append(axis_id)
            if len(selected) < min_order:
                for axis_id in pool:
                    if axis_id not in selected:
                        selected.append(axis_id)
                    if len(selected) >= min_order:
                        break
            seed_record = tuple(selected)
            search_id = digest_json(
                {
                    "target_axis": target_axis,
                    "axis_pool": list(pool),
                    "seed_axes": list(seed_record),
                    "min_order": min_order,
                    "trace_head": self.trace.head,
                },
                namespace=b"SCIENCEATLAS_AI_SUBSPACE_SEARCH_V1",
            )[:24]
            fair_cursor = 0
            # Rank the finite execution seed shell *before data* by exact
            # dimensional admissibility and pi/MDL complexity.  Width controls
            # only this run; it is not an architectural statement that omitted
            # combinations do not exist.
            nominated: list[tuple[tuple[Any, ...], str]] = []
            for axes in combinations(seed_record, min_order):
                shell = self._subspace_shell(input_axes=axes, target_axis=target_axis, parent_id=None, search_id=search_id)
                structural = self._candidate_structural_methodology(shell)
                status_rank = {"PASS": 0, "OPEN_GAP": 1, "KNOWN_DERIVED": 2, "ARTIFACT": 3, "REJECT_DIMENSIONAL": 4}.get(str(structural.get("status")), 9)
                mdl = structural.get("minimum_pi_complexity")
                key = (
                    status_rank,
                    10**9 if mdl is None else int(mdl),
                    -len(shell.domains),
                    shell.input_axes,
                    shell.subspace_id,
                )
                nominated.append((key, shell.subspace_id))
            nominated.sort(key=lambda row: row[0])
            frontier_ids = [sid for _key, sid in nominated[:expansion_budget]]
            retained_ids = []
            evaluated_ids = []
            evaluations_used_total = 0
            budget_this_call = expansion_budget
            combination_space = {}

        evaluations_this_call = 0
        max_observed_order = max((self.subspace_candidates[sid].order for sid in evaluated_ids if sid in self.subspace_candidates), default=0)
        status = "OPEN"
        while frontier_ids and evaluations_this_call < budget_this_call:
            order = self.subspace_candidates[frontier_ids[0]].order
            same_order_ids = [sid for sid in frontier_ids if self.subspace_candidates[sid].order == order]
            later_ids = [sid for sid in frontier_ids if self.subspace_candidates[sid].order != order]
            level_evaluated: list[SubspaceCandidate] = []
            unprocessed_same_order: list[str] = []
            for index, sid in enumerate(same_order_ids):
                if evaluations_this_call >= budget_this_call:
                    unprocessed_same_order.extend(same_order_ids[index:])
                    break
                candidate = self.subspace_candidates[sid]
                if candidate.retention_reason == "UNASSESSED":
                    candidate = self._evaluate_subspace_candidate(candidate)
                    evaluations_this_call += 1
                    evaluations_used_total += 1
                level_evaluated.append(candidate)
                if sid not in evaluated_ids:
                    evaluated_ids.append(sid)
                max_observed_order = max(max_observed_order, candidate.order)
                combination_space[str(candidate.order)] = comb(len(pool), candidate.order) if len(pool) >= candidate.order else 0
            if unprocessed_same_order:
                frontier_ids = unprocessed_same_order + later_ids
                status = "BUDGET_EXHAUSTED"
                break

            selected_reasons = owner.select_for_expansion(
                level_evaluated,
                beam_width=beam_width,
                exploration_width=exploration_width,
                gap_width=gap_width,
            )
            level_retained: list[SubspaceCandidate] = []
            for candidate in level_evaluated:
                reason = selected_reasons.get(candidate.subspace_id)
                if reason is None:
                    updated = replace(candidate, status="PRUNED", retention_reason="DOMINATED_OR_BUDGET_DEPRIORITIZED")
                elif reason == "PREDICTIVE_FRONTIER":
                    next_status = "PROMISING" if candidate.status not in {"CLOSED_ON_OBSERVED_DATA", "OPEN_GAP"} else candidate.status
                    updated = replace(candidate, status=next_status, retention_reason=reason)
                    level_retained.append(updated)
                elif reason == "HIGHER_ORDER_EXPLORATION":
                    updated = replace(candidate, status="EXPLORATION", retention_reason=reason)
                    level_retained.append(updated)
                else:
                    updated = replace(candidate, status="OPEN_GAP", retention_reason=reason)
                    level_retained.append(updated)
                self.subspace_candidates[updated.subspace_id] = updated
                if updated.subspace_id in selected_reasons and updated.subspace_id not in retained_ids:
                    retained_ids.append(updated.subspace_id)

            next_frontier: list[str] = []
            order_blocked = run_order_limit is not None and order >= run_order_limit
            if not order_blocked:
                for parent in level_retained:
                    if parent.status == "OPEN_GAP":
                        # Preserve the structural/measurement gap as an addressable
                        # research state. Adding more axes cannot repair a missing
                        # typed bridge by itself.
                        continue
                    residual_rank: tuple[str, ...] = ()
                    if parent.frontier_id and parent.frontier_id in self.frontiers:
                        residual_rank = tuple(score.axis_id for score in self.frontiers[parent.frontier_id].candidate_axes)
                    additions, fair_cursor = owner.expansion_axis_order(
                        parent=parent,
                        axis_pool=pool,
                        residual_rank=residual_rank,
                        axis_domains=axis_domains,
                        fair_cursor=fair_cursor,
                        expansion_width=expansion_width,
                        exploration_width=fair_expansion_width,
                    )
                    produced_child = False
                    for axis_id in additions:
                        child_axes = tuple(sorted((*parent.input_axes, axis_id)))
                        if len(child_axes) == len(parent.input_axes):
                            continue
                        child = self._subspace_shell(
                            input_axes=child_axes,
                            target_axis=target_axis,
                            parent_id=parent.subspace_id,
                            search_id=search_id,
                        )
                        if child.subspace_id not in evaluated_ids and child.subspace_id not in next_frontier:
                            next_frontier.append(child.subspace_id)
                            produced_child = True
                    if produced_child:
                        self.subspace_candidates[parent.subspace_id] = replace(parent, status="EXPANDED")
            elif level_retained:
                status = "ORDER_LIMIT_REACHED"
            frontier_ids = later_ids + next_frontier
            if status == "ORDER_LIMIT_REACHED":
                break
            if not frontier_ids:
                status = "COMPLETE" if level_retained else "NO_FRONTIER"
                break
        if evaluations_this_call >= budget_this_call and frontier_ids:
            status = "BUDGET_EXHAUSTED"
        if not frontier_ids and status == "OPEN":
            status = "NO_FRONTIER"

        state = SubspaceSearchState(
            search_id=search_id,
            target_axis=target_axis,
            axis_pool=pool,
            seed_axes=seed_record,
            min_order=min_order,
            run_order_limit=run_order_limit,
            expansion_budget=(self.subspace_searches[search_id].expansion_budget + expansion_budget if continuation_search_id is not None else expansion_budget),
            evaluations_used=evaluations_used_total,
            max_observed_order=max_observed_order,
            fair_cursor=fair_cursor,
            frontier_ids=tuple(frontier_ids),
            retained_ids=tuple(retained_ids),
            evaluated_ids=tuple(evaluated_ids),
            status=status,
            combination_space_by_order=combination_space,
            provenance=(f"trace-head:{self.trace.head}",),
        )
        self.subspace_searches[search_id] = state
        evaluated_candidates = [self.subspace_candidates[sid] for sid in state.evaluated_ids if sid in self.subspace_candidates]
        ranked = owner.select_for_expansion(
            evaluated_candidates,
            beam_width=max(beam_width, 1),
            exploration_width=0,
            gap_width=max(gap_width, 0),
        ) if evaluated_candidates else {}
        top_ids = tuple(ranked)[: max(beam_width, 1)]
        result = {
            "schema": "scienceatlas-ai-adaptive-subspace-search-v1",
            "status": state.status,
            "search_id": state.search_id,
            "target_axis": target_axis,
            "axis_pool_count": len(pool),
            "seed_axes": list(state.seed_axes),
            "structural_seed_combination_count": comb(len(state.seed_axes), state.min_order) if len(state.seed_axes) >= state.min_order else 0,
            "min_order": state.min_order,
            "run_order_limit": state.run_order_limit,
            "architecture_order_ceiling": None,
            "expansion_budget_total": state.expansion_budget,
            "evaluations_used_total": state.evaluations_used,
            "evaluations_this_call": evaluations_this_call,
            "max_observed_order": state.max_observed_order,
            "combination_space_by_order": dict(state.combination_space_by_order),
            "evaluated_subspace_count": len(state.evaluated_ids),
            "retained_subspace_count": len(state.retained_ids),
            "frontier_subspace_count": len(state.frontier_ids),
            "top_subspaces": [self.subspace_candidates[sid].to_json() for sid in top_ids if sid in self.subspace_candidates],
            "open_gap_count": sum(1 for c in evaluated_candidates if c.status == "OPEN_GAP" or c.gap_kind is not None),
            "claim_boundary": {
                "candidate_is_law": False,
                "zero_lower_order_gain_prunes_all_descendants": False,
                "cross_domain_gap_means_candidate_false": False,
                "execution_budget_is_semantic_axis_ceiling": False,
                "internet_absence_is_rejection_criterion": False,
            },
        }
        result["digest"] = digest_json(result, namespace=b"SCIENCEATLAS_AI_ADAPTIVE_SUBSPACE_SEARCH_RESULT_V1")
        self._append_trace({"kind": "adaptive_subspace_search", "result": result})
        return result

    def _qualified_once(
        self,
        *,
        target_axis: str,
        search_kwargs: Mapping[str, Any],
    ) -> tuple[Mapping[str, Any], Fraction, tuple[str, ...]]:
        result = self.adaptive_subspace_search(target_axis=target_axis, **dict(search_kwargs))
        search_id = str(result.get("search_id", ""))
        state = self.subspace_searches.get(search_id)
        if state is None:
            return result, Fraction(0), ()
        eligible: list[SubspaceCandidate] = []
        for sid in state.evaluated_ids:
            candidate = self.subspace_candidates.get(sid)
            if candidate is None:
                continue
            if candidate.structural_gate != "PASS":
                continue
            if candidate.convention_gate == "ARTIFACT" or candidate.derivability_gate == "KNOWN_DERIVED":
                continue
            if candidate.collapse_gate not in {"PASS", "NOT_APPLICABLE_SIDE_AXIS_SPACE"}:
                continue
            if candidate.regime_gate != "PASS":
                continue
            eligible.append(candidate)
        best = max((self._validation_gain(c) for c in eligible), default=Fraction(0))
        ids = tuple(c.subspace_id for c in sorted(eligible, key=lambda c: (-self._validation_gain(c), c.complexity, c.input_axes, c.subspace_id)))
        return result, best, ids

    def _shadow_with_permuted_target(self, *, target_axis: str, seed: int) -> "ScienceAtlasAI":
        shadow = ScienceAtlasAI(register_baseline_owner=False)
        # Owner contracts/executors are read-only during shadow qualification.
        # Sharing the bus keeps the *same* mounted Atlas route semantics without
        # mutating the authoritative runtime.
        shadow.owner_bus = self.owner_bus
        shadow.representation = RepresentationGraph.from_json(self.representation.to_json())
        shadow.world = WorldModel.from_json(self.world.to_json())
        shadow.dimension_profiles = dict(self.dimension_profiles)
        shadow.known_monomial_relations = dict(self.known_monomial_relations)
        shadow.atlas_registry_snapshot = dict(self.atlas_registry_snapshot)

        samples: list[str] = []
        values: list[Fraction] = []
        for sample_id in shadow.world.sample_ids():
            observation = shadow.world._best_measurement(sample_id, target_axis)
            if observation is not None:
                samples.append(sample_id)
                values.append(observation.quantity.value)
        rng = random.Random(int(seed))
        shuffled = list(values)
        rng.shuffle(shuffled)
        permuted = dict(zip(samples, shuffled, strict=True))
        replaced_observations: list[Observation] = []
        for observation in shadow.world.observations:
            if observation.axis_id == target_axis and observation.sample_id in permuted:
                replaced_observations.append(
                    replace(observation, quantity=replace(observation.quantity, value=permuted[observation.sample_id]))
                )
            else:
                replaced_observations.append(observation)
        shadow.world.observations = replaced_observations
        return shadow

    def qualified_subspace_research(
        self,
        *,
        target_axis: str,
        null_permutations: int = 200,
        permutation_seed: int = 0,
        null_alpha_bp: int = 500,
        **search_kwargs: Any,
    ) -> Mapping[str, Any]:
        """Run the source-grounded scientific qualification around the explorer.

        The adaptive explorer remains navigation only.  This method is the sole
        built-in path that may assign ``CALIBRATED_CANDIDATE``.  It freezes the
        observed search before null calibration, then reruns the same search and
        all post-data gates on permuted targets.  Internet/literature status is
        intentionally absent from the survival criteria.
        """
        if null_permutations < 0:
            raise ValueError("null_permutations cannot be negative")
        if "continuation_search_id" in search_kwargs and search_kwargs.get("continuation_search_id") is not None:
            raise ValueError("qualified null calibration requires a fresh fixed pipeline configuration")
        observed_result, observed_best, eligible_ids = self._qualified_once(
            target_axis=target_axis,
            search_kwargs=search_kwargs,
        )
        search_id = str(observed_result.get("search_id", ""))
        if not search_id:
            payload = {
                "schema": "scienceatlas-ai-qualified-subspace-research-v1",
                "status": "NO_FRONTIER",
                "target_axis": target_axis,
                "search_result": dict(observed_result),
                "claim_boundary": {"no_frontier_means_no_law_exists": False},
            }
            payload["digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_QUALIFIED_SUBSPACE_RESEARCH_V1")
            self.qualification_runs[payload["digest"]] = dict(payload)
            self._append_trace({"kind": "qualified_subspace_research", "qualification_digest": payload["digest"], "status": payload["status"]})
            return payload

        observed_freeze = self.freeze(f"qualified-observed:{search_id}")
        null_statistics: list[Fraction] = []
        if null_permutations and eligible_ids:
            for index in range(null_permutations):
                shadow = self._shadow_with_permuted_target(target_axis=target_axis, seed=int(permutation_seed) + index)
                _shadow_result, statistic, _ids = shadow._qualified_once(
                    target_axis=target_axis,
                    search_kwargs=search_kwargs,
                )
                null_statistics.append(statistic)
        null_owner = self.owner_bus.for_capability("methodology.pipeline_null")
        global_null = null_owner.assess(
            observed=observed_best,
            null_statistics=null_statistics,
            alpha_bp=int(null_alpha_bp),
        )
        threshold = self._fraction_from_payload(global_null.get("threshold"))
        state = self.subspace_searches[search_id]
        calibrated_ids: list[str] = []
        for sid in state.evaluated_ids:
            candidate = self.subspace_candidates[sid]
            if sid not in eligible_ids:
                continue
            gain = self._validation_gain(candidate)
            candidate_null = null_owner.assess(
                observed=gain,
                null_statistics=null_statistics,
                alpha_bp=int(null_alpha_bp),
            )
            p_value = self._fraction_from_payload(candidate_null.get("empirical_p"))
            null_status = str(candidate_null.get("status", "UNKNOWN"))
            if null_status == "PASS":
                methodology_status = "CALIBRATED_CANDIDATE"
                calibrated_ids.append(sid)
            elif null_status == "FAIL":
                methodology_status = "NULL_COMPATIBLE"
            else:
                methodology_status = "NULL_CALIBRATION_REQUIRED"
            updated = replace(
                candidate,
                null_gate=null_status,
                null_p=p_value,
                methodology_status=methodology_status,
                provenance=tuple(dict.fromkeys((*candidate.provenance, f"pipeline-null:{candidate_null.get('digest','')}"))),
            )
            self.subspace_candidates[sid] = updated
            self.methodology_records[str(candidate_null.get("digest"))] = dict(candidate_null)

        ranked_calibrated = sorted(
            (self.subspace_candidates[sid] for sid in calibrated_ids),
            key=lambda c: (-self._validation_gain(c), c.regime_mse if c.regime_mse is not None else Fraction(10**60), c.complexity, c.input_axes, c.subspace_id),
        )
        payload = {
            "schema": "scienceatlas-ai-qualified-subspace-research-v1",
            "status": (
                "CALIBRATED_CANDIDATES" if calibrated_ids else
                ("REGIME_OR_COLLAPSE_QUALIFICATION_REQUIRED" if not eligible_ids else
                 ("NULL_CALIBRATION_REQUIRED" if not null_permutations else "NO_CANDIDATE_ABOVE_PIPELINE_NULL"))
            ),
            "target_axis": target_axis,
            "search_id": search_id,
            "observed_freeze_root": observed_freeze,
            "observed_best_validation_gain": fraction_json(observed_best),
            "eligible_pre_null_count": len(eligible_ids),
            "calibrated_candidate_count": len(calibrated_ids),
            "calibrated_candidates": [c.to_json() for c in ranked_calibrated],
            "pipeline_null": global_null,
            "null_threshold": None if threshold is None else fraction_json(threshold),
            "search_result_digest": str(observed_result.get("digest", "")),
            "pipeline_configuration": {
                **{str(k): v for k, v in search_kwargs.items()},
                "null_permutations": null_permutations,
                "permutation_seed": permutation_seed,
                "null_alpha_bp": null_alpha_bp,
            },
            "claim_boundary": {
                "calibrated_candidate_is_law": False,
                "calibrated_candidate_is_world_novel": False,
                "internet_absence_is_positive_or_negative_evidence": False,
                "whole_pipeline_null_was_rerun": bool(null_permutations),
                "within_regime_loo_substituted_for_regime_holdout": False,
            },
        }
        payload["digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_QUALIFIED_SUBSPACE_RESEARCH_V1")
        self.qualification_runs[payload["digest"]] = dict(payload)
        self.methodology_records[str(global_null.get("digest"))] = dict(global_null)
        self._append_trace({"kind": "qualified_subspace_research", "qualification_digest": payload["digest"], "status": payload["status"]})
        return payload

    def assess_pi_transition(
        self,
        *,
        group: Mapping[str, int],
        transition_observable_axis: str,
        lower: Fraction = Fraction(1, 2),
        upper: Fraction = Fraction(2, 1),
    ) -> Mapping[str, Any]:
        """Assess whether a preregistered pi~1 transition experiment is covered.

        The source paper specifies the scientific question but not a unique test
        statistic.  This API therefore reports exact coverage and descriptive
        summaries only.  It never promotes a transition claim.
        """
        group = {str(axis): int(exp) for axis, exp in group.items() if int(exp)}
        if not group:
            raise ValueError("pi group cannot be empty")
        if transition_observable_axis in group:
            raise ValueError("transition observable must be distinct from pi-group axes")
        axes = tuple(sorted(group))
        for axis_id in (*axes, transition_observable_axis):
            if axis_id not in self.representation.axes:
                raise KeyError(axis_id)
        value_maps = {axis_id: self.world.values_by_sample(axis_id) for axis_id in (*axes, transition_observable_axis)}
        sample_ids = sorted(set.intersection(*(set(values) for values in value_maps.values()))) if value_maps else []
        rows: list[tuple[str, Mapping[str, Fraction], Fraction]] = []
        observable_by_sample: dict[str, Fraction] = {}
        for sample_id in sample_ids:
            xs = {axis_id: value_maps[axis_id][sample_id] for axis_id in axes}
            rows.append((sample_id, xs, Fraction(0)))
            observable_by_sample[sample_id] = value_maps[transition_observable_axis][sample_id]
        owner = self.owner_bus.for_capability("methodology.pi_transition")
        receipt = owner.assess(
            group=group,
            rows=rows,
            transition_observable_by_sample=observable_by_sample,
            lower=Fraction(lower),
            upper=Fraction(upper),
        )
        payload = {
            **dict(receipt),
            "pi_group": dict(sorted(group.items())),
            "transition_observable_axis": transition_observable_axis,
            "sample_count": len(sample_ids),
        }
        payload["digest"] = digest_json(payload, namespace=b"SCIENCEATLAS_AI_PI_TRANSITION_RUNTIME_V1")
        self.methodology_records[payload["digest"]] = dict(payload)
        self._append_trace({"kind": "pi_transition_assessment", "receipt_digest": payload["digest"], "status": payload.get("status")})
        return payload

    def birth_axis(self, **kwargs: Any) -> Axis:
        axis = self.representation.birth(**kwargs)
        self._append_trace({"kind": "axis_birth", "axis": axis.to_json()})
        return axis

    def refine_axis(self, axis_id: str, *, validity: ValidityDomain, name: str | None = None) -> Axis:
        axis = self.representation.refine(axis_id, validity=validity, name=name)
        self._append_trace({"kind": "axis_refine", "axis": axis.to_json()})
        return axis

    def split_axis(self, axis_id: str, children: Sequence[Axis]) -> tuple[Axis, ...]:
        result = self.representation.split(axis_id, children)
        self._append_trace({"kind": "axis_split", "parent_axis_id": axis_id, "children": [a.to_json() for a in result]})
        return result

    def observe(self, observation: Observation, evidence: EvidenceRecord) -> None:
        axis = self.representation.axes[observation.axis_id]
        self.world.observe(observation, evidence, axis)
        self._append_trace({"kind": "observation", "observation": observation.to_json(), "evidence": evidence.to_json()})

    def mount_atlas(self, root: str) -> Mapping[str, Any]:
        from .atlas_bridge import mount_real_scienceatlas

        receipt = mount_real_scienceatlas(self.owner_bus, root)
        self.atlas_registry_snapshot = dict(receipt["registry_snapshot"])
        self._append_trace({"kind": "atlas_mount", "receipt": dict(receipt)})
        return receipt

    def atlas_frontier_probe(self) -> Mapping[str, Any]:
        """Read the real Atlas frontier while keeping external floats out of AI state.

        Atlas contracts may legitimately contain floating diagnostics. They are
        returned to the caller unchanged, but the AI provenance chain records only
        the Atlas-provided source digest plus typed integer/string metadata. This
        prevents an implicit float -> exact-scientific-value conversion at the
        distribution boundary.
        """
        if not self.atlas_registry_snapshot:
            receipt = {
                "schema": "scienceatlas-ai-atlas-frontier-probe-receipt-v1",
                "status": "UNKNOWN",
                "reason": "real ScienceAtlas registry is not mounted",
            }
            receipt["digest"] = digest_json(receipt, namespace=b"SCIENCEATLAS_AI_ATLAS_FRONTIER_PROBE_RECEIPT_V1")
            self._append_trace({"kind": "atlas_frontier_probe", "receipt": receipt})
            return dict(receipt)
        frontier = self.owner_bus.invoke("atlas.frontier.current", action="frontier_contract")
        catalog = self.owner_bus.invoke("atlas.registry.catalog", action="summary")
        receipt = {
            "schema": "scienceatlas-ai-atlas-frontier-probe-receipt-v1",
            "status": "OPEN" if frontier.get("top_frontier_defect") else "UNKNOWN",
            "registry_snapshot_digest": str(self.atlas_registry_snapshot.get("registry_snapshot_digest", "")),
            "catalog_digest": str(catalog.get("catalog_digest", "")),
            "catalog_owner_count": int(catalog.get("owner_count", 0)),
            "source_frontier_digest": str(frontier.get("digest", "")),
            "claim_boundary": {
                "frontier_candidate_is_law": False,
                "probe_mutates_atlas": False,
                "novelty_established_by_probe": False,
                "external_numeric_diagnostics_are_not_coerced_into_exact_ai_quantities": True,
            },
        }
        receipt["digest"] = digest_json(receipt, namespace=b"SCIENCEATLAS_AI_ATLAS_FRONTIER_PROBE_RECEIPT_V1")
        self._append_trace({"kind": "atlas_frontier_probe", "receipt": receipt})
        return {**receipt, "catalog": dict(catalog), "frontier": dict(frontier)}

    def atlas_adaptive_axis_scan(
        self,
        *,
        domain_id: str,
        evidence_records: Sequence[Mapping[str, Any]],
        **kwargs: Any,
    ) -> Mapping[str, Any]:
        """Delegate a missing-context scan to the real Atlas adaptive-axis owner."""
        if not self.atlas_registry_snapshot:
            raise RuntimeError("real ScienceAtlas registry is not mounted")
        result = self.owner_bus.invoke(
            "atlas.representation.adaptive_axis_scan",
            action="scan",
            domain_id=domain_id,
            evidence_records=evidence_records,
            **kwargs,
        )
        summary = dict(result.get("scan_summary", {}) or {})
        receipt = {
            "schema": "scienceatlas-ai-atlas-adaptive-axis-scan-receipt-v1",
            "registry_snapshot_digest": str(self.atlas_registry_snapshot.get("registry_snapshot_digest", "")),
            "source_result_digest": str(result.get("digest", "")),
            "source_owner_id": str(result.get("owner_id", "")),
            "domain_id": str(result.get("domain_id", domain_id)),
            "evidence_record_count": int(result.get("evidence_record_count", len(evidence_records))),
            "research_local_candidate_count": int(summary.get("research_local_candidate_count", 0)),
            "identifiability_status": str(summary.get("identifiability_status", "UNKNOWN")),
            "automatic_causal_axis_selection_allowed": bool(summary.get("automatic_causal_axis_selection_allowed", False)),
            "claim_boundary": {
                "research_local_axis_is_world_truth": False,
                "scan_mutates_canonical_registry": False,
                "external_float_diagnostics_are_not_exact_ai_quantities": True,
            },
        }
        receipt["digest"] = digest_json(receipt, namespace=b"SCIENCEATLAS_AI_ATLAS_ADAPTIVE_AXIS_SCAN_RECEIPT_V1")
        self._append_trace({"kind": "atlas_adaptive_axis_scan", "receipt": receipt})
        return {**receipt, "result": dict(result)}

    def atlas_bridge_typing_audit(self) -> Mapping[str, Any]:
        """Audit the real Atlas standard bridges for semantic+typed owner readiness.

        The external Atlas remains authoritative for bridge-role qualification.
        This method only asks the mounted semantic-hypergraph service to count
        where bridge-eligible owners also expose typed quantity/unit/dimension
        symbols. No canonical owner or bridge is mutated.
        """
        if not self.atlas_registry_snapshot or not self.owner_bus.has_capability("atlas.registry.semantic_hypergraph"):
            raise RuntimeError("real ScienceAtlas semantic hypergraph is not mounted")
        result = self.owner_bus.invoke("atlas.registry.semantic_hypergraph", action="bridge_typing_audit")
        receipt = {
            "schema": "scienceatlas-ai-atlas-bridge-typing-audit-receipt-v1",
            "registry_snapshot_digest": str(self.atlas_registry_snapshot.get("registry_snapshot_digest", "")),
            "source_digest": str(result.get("digest", "")),
            "standard_bridge_count": int(result.get("standard_bridge_count", 0)),
            "fully_typed_bridge_count": int(result.get("fully_typed_bridge_count", 0)),
            "qualified_owner_axis_binding_count": int(result.get("qualified_owner_axis_binding_count", 0)),
            "status": str(result.get("status", "UNKNOWN")),
            "next_action": str(result.get("next_action", "NONE")),
            "claim_boundary": {
                "audit_mutates_atlas": False,
                "semantic_eligibility_reimplemented_by_ai": False,
                "missing_typed_bridge_is_promoted_to_route": False,
            },
        }
        receipt["digest"] = digest_json(receipt, namespace=b"SCIENCEATLAS_AI_ATLAS_BRIDGE_TYPING_AUDIT_RECEIPT_V1")
        self._append_trace({"kind": "atlas_bridge_typing_audit", "receipt": receipt})
        return {**receipt, "audit": dict(result)}

    def atlas_qualified_owner_axis_bindings(self) -> Mapping[str, Any]:
        """Read Atlas-qualified owner<->axis semantic bindings without route promotion."""
        if not self.atlas_registry_snapshot or not self.owner_bus.has_capability("atlas.registry.semantic_hypergraph"):
            raise RuntimeError("real ScienceAtlas semantic hypergraph is not mounted")
        result = self.owner_bus.invoke("atlas.registry.semantic_hypergraph", action="qualified_owner_axis_bindings")
        receipt = {
            "schema": "scienceatlas-ai-qualified-owner-axis-bindings-receipt-v1",
            "registry_snapshot_digest": str(self.atlas_registry_snapshot.get("registry_snapshot_digest", "")),
            "source_digest": str(result.get("digest", "")),
            "count": int(result.get("count", 0)),
            "status": str(result.get("status", "UNKNOWN")),
            "claim_boundary": {
                "bindings_are_cross_domain_routes": False,
                "bindings_are_world_measurements": False,
                "query_mutates_atlas": False,
            },
        }
        receipt["digest"] = digest_json(receipt, namespace=b"SCIENCEATLAS_AI_QUALIFIED_OWNER_AXIS_BINDINGS_RECEIPT_V1")
        self._append_trace({"kind": "atlas_qualified_owner_axis_bindings", "receipt": receipt})
        return {**receipt, "bindings": list(result.get("bindings", ())) }

    def _atlas_axis_contract(self, axis_id: str) -> dict[str, Any]:
        axis = self.representation.axes[axis_id]
        return {
            "axis_id": axis.axis_id,
            "name": axis.name,
            "semantic_type": axis.semantic_type,
            "domain": axis.domain,
            "unit": axis.unit,
            "quantity_id": axis.quantity_id,
            "dimension": None if axis.dimension is None else list(axis.dimension),
            "aliases": list(axis.aliases),
        }

    def atlas_hypergraph_plan(
        self,
        *,
        input_axes: Sequence[str],
        target_axis: str,
    ) -> tuple[HypergraphRoute, ...]:
        axes = self._normalize_axes(input_axes=input_axes)
        if not self.atlas_registry_snapshot or not self.owner_bus.has_capability("atlas.registry.semantic_hypergraph"):
            raise RuntimeError("real ScienceAtlas semantic hypergraph is not mounted")
        for axis_id in (*axes, target_axis):
            if axis_id not in self.representation.axes:
                raise KeyError(axis_id)
        raw = self.owner_bus.invoke(
            "atlas.registry.semantic_hypergraph",
            action="plan_routes",
            input_axes=[self._atlas_axis_contract(a) for a in axes],
            target_axis=self._atlas_axis_contract(target_axis),
        )
        registry_digest = str(self.atlas_registry_snapshot.get("registry_snapshot_digest", ""))
        query_digest = str(raw.get("digest", ""))
        routes: list[HypergraphRoute] = []
        for row in raw.get("routes", []):
            bindings = tuple(AxisSymbolBinding.from_json(x) for x in row.get("bindings", ()))
            provenance = (
                f"atlas-registry:{registry_digest}",
                f"hypergraph-query:{query_digest}",
                f"bridge-contract:{row.get('bridge_contract_digest', '')}",
                *(f"source-passport:{d}" for d in row.get("source_passport_digests", ())),
                f"target-passport:{row.get('target_passport_digest', '')}",
            )
            route = HypergraphRoute(
                route_id=str(row["route_id"]),
                input_axes=tuple(str(x) for x in row.get("input_axes", ())),
                target_axis=str(row["target_axis"]),
                source_owner_ids=tuple(str(x) for x in row.get("source_owner_ids", ())),
                target_owner_id=str(row["target_owner_id"]),
                bridge_id=str(row["bridge_id"]),
                bindings=bindings,
                dimensional_status=str(row.get("dimensional_status", "UNKNOWN")),
                lowering_status=str(row.get("lowering_status", "UNKNOWN")),
                path_cost=int(row.get("path_cost", 0)),
                status="STRUCTURAL_CANDIDATE",
                provenance=tuple(x for x in provenance if not x.endswith(":")),
            )
            self.hypergraph_routes[route.route_id] = route
            routes.append(route)
        receipt = {
            "kind": "atlas_hypergraph_plan",
            "status": str(raw.get("status", "UNKNOWN")),
            "input_axes": list(axes),
            "target_axis": target_axis,
            "required_domains": list(raw.get("required_domains", ())),
            "route_count": len(routes),
            "unlowered_axes": list(raw.get("unlowered_axes", ())),
            "frontier_filtered_typed_axes": list(raw.get("frontier_filtered_typed_axes", ())),
            "query_digest": query_digest,
            "route_ids": [r.route_id for r in routes],
            "atlas_directed_research": dict(raw.get("atlas_directed_research", {})),
            "semantic_lowering_gaps": list(raw.get("semantic_lowering_gaps", ())),
            "next_action": str(raw.get("next_action", "NONE")),
        }
        self.hypergraph_queries[query_digest] = dict(receipt)
        self.last_hypergraph_query_digest = query_digest
        self._append_trace(receipt)
        return tuple(routes)

    def generate_hypotheses_via_route(self, route_id: str) -> tuple[Hypothesis, ...]:
        route = self.hypergraph_routes[route_id]
        registry_digest = str(self.atlas_registry_snapshot.get("registry_snapshot_digest", ""))
        if (
            route.lowering_status != "PASS"
            or route.dimensional_status != "PASS"
            or not registry_digest
            or f"atlas-registry:{registry_digest}" not in route.provenance
        ):
            self._append_trace({"kind": "routed_hypothesis_generation", "route_id": route_id, "status": "UNKNOWN", "reason": "route gates or current Atlas attestation not PASS"})
            return ()
        axes = route.input_axes
        target_axis = route.target_axis
        relation_domains = {self.representation.axes[a].domain for a in (*axes, target_axis)}
        if len(relation_domains) < 2:
            self._append_trace({"kind": "routed_hypothesis_generation", "route_id": route_id, "status": "UNKNOWN", "reason": "route is not cross-domain"})
            return ()
        # The route is the explicit authorization missing from ordinary
        # generate_hypotheses(). Numeric fitting remains owned by the existing
        # mechanism owner; no duplicate route-specific regression algorithm exists.
        capability = "hypothesis.numeric_relation.baseline" if len(axes) == 1 else "hypothesis.numeric_relation.multiaxis"
        owner = self.owner_bus.for_capability(capability)
        rows_full = self.world.rows_for_axes(axes, target_axis)
        if len(rows_full) < 2:
            return ()
        rows = tuple((xs, y) for _, xs, y in rows_full)
        provenance = tuple(dict.fromkeys((*self.world.provenance_for_axes((*axes, target_axis)), *route.provenance, f"hypergraph-route:{route.route_id}", f"atlas-bridge:{route.bridge_id}")))
        proposals = owner.propose(rows, input_axes=axes, target_axis=target_axis, provenance=provenance)
        for hypothesis in proposals:
            self.hypotheses[hypothesis.hypothesis_id] = hypothesis
        self._append_trace({
            "kind": "routed_hypothesis_generation",
            "status": "CANDIDATES" if proposals else "UNKNOWN",
            "route_id": route.route_id,
            "bridge_id": route.bridge_id,
            "owner_id": owner.spec.owner_id,
            "hypothesis_ids": [h.hypothesis_id for h in proposals],
        })
        return proposals

    def generate_hypotheses_via_route_group(self, route_ids: Sequence[str]) -> tuple[Hypothesis, ...]:
        ids = tuple(sorted(dict.fromkeys(str(x) for x in route_ids)))
        if not ids:
            return ()
        routes = [self.hypergraph_routes[rid] for rid in ids]
        first = routes[0]
        if any(r.input_axes != first.input_axes or r.target_axis != first.target_axis or r.bridge_id != first.bridge_id for r in routes):
            raise ValueError("route group must share input axes, target axis and bridge")
        registry_digest = str(self.atlas_registry_snapshot.get("registry_snapshot_digest", ""))
        if (
            not registry_digest
            or any(r.lowering_status != "PASS" or r.dimensional_status != "PASS" for r in routes)
            or any(f"atlas-registry:{registry_digest}" not in r.provenance for r in routes)
        ):
            return ()
        axes = first.input_axes
        target_axis = first.target_axis
        relation_domains = {self.representation.axes[a].domain for a in (*axes, target_axis)}
        if len(relation_domains) < 2:
            return ()
        capability = "hypothesis.numeric_relation.baseline" if len(axes) == 1 else "hypothesis.numeric_relation.multiaxis"
        owner = self.owner_bus.for_capability(capability)
        rows_full = self.world.rows_for_axes(axes, target_axis)
        if len(rows_full) < 2:
            return ()
        rows = tuple((xs, y) for _, xs, y in rows_full)
        group_digest = digest_json({"route_ids": list(ids), "bridge_id": first.bridge_id}, namespace=b"SCIENCEATLAS_AI_ROUTE_AUTH_GROUP_V1")
        provenance = tuple(dict.fromkeys((
            *self.world.provenance_for_axes((*axes, target_axis)),
            f"hypergraph-route-group:{group_digest}",
            f"atlas-bridge:{first.bridge_id}",
            f"atlas-registry:{self.atlas_registry_snapshot.get('registry_snapshot_digest', '')}",
        )))
        proposals = owner.propose(rows, input_axes=axes, target_axis=target_axis, provenance=provenance)
        for hypothesis in proposals:
            self.hypotheses[hypothesis.hypothesis_id] = hypothesis
        for route in routes:
            self.hypergraph_routes[route.route_id] = replace(route, provenance=tuple(dict.fromkeys((*route.provenance, f"prediction-auth-group:{group_digest}"))))
        self._append_trace({
            "kind": "routed_hypothesis_group_generation",
            "status": "CANDIDATES" if proposals else "UNKNOWN",
            "route_group_digest": group_digest,
            "route_count": len(ids),
            "bridge_id": first.bridge_id,
            "hypothesis_ids": [h.hypothesis_id for h in proposals],
        })
        return proposals

    def _evaluate_hypothesis_ids(
        self,
        *,
        hypothesis_ids: Sequence[str],
        input_axes: Sequence[str],
        target_axis: str,
    ) -> dict[str, CriticVector]:
        axes = self._normalize_axes(input_axes=input_axes)
        wanted = tuple(dict.fromkeys(str(x) for x in hypothesis_ids))
        rows = self.world.rows_for_axes(axes, target_axis)
        relevant = [
            self.hypotheses[hid] for hid in wanted
            if hid in self.hypotheses
            and self.hypotheses[hid].input_axes == axes
            and self.hypotheses[hid].target_axis == target_axis
            and self.hypotheses[hid].status != "falsified"
        ]
        scores = CriticEnsemble.evaluate(
            relevant,
            rows,
            owner_bus=self.owner_bus,
            target_axis=self.representation.axes[target_axis],
            previously_validated_families=self.meta.validated_families,
        )
        self.critic_scores.update(scores)
        frontier = CriticEnsemble.pareto_frontier(scores)
        for hypothesis in relevant:
            if hypothesis.hypothesis_id in frontier and hypothesis.status == "candidate":
                self.hypotheses[hypothesis.hypothesis_id] = replace(hypothesis, status="active")
        return scores

    def reason_over_hypergraph(
        self,
        *,
        input_axes: Sequence[str],
        target_axis: str,
        intervention_axis: str | None = None,
        candidates: Sequence[SemanticQuantity] | None = None,
        cost: int | Fraction = 1,
        risk: int | Fraction = 0,
    ) -> Mapping[str, Any]:
        """Run typed owner→axis→bridge→owner→prediction→residual→experiment reasoning.

        Atlas passports and bridges authorize structural semantics. The currently
        executable prediction stage is deliberately data-derived through the
        existing numeric hypothesis owners; this method does *not* claim to
        execute arbitrary Atlas formula ASTs as numerical solvers.
        """
        axes = self._normalize_axes(input_axes=input_axes)
        structural = self.atlas_hypergraph_plan(input_axes=axes, target_axis=target_axis)
        if not structural:
            receipt = dict(self.hypergraph_queries.get(self.last_hypergraph_query_digest, {}))
            result = {
                "status": str(receipt.get("status", "UNKNOWN")),
                "reason": "no exact typed+semantically-qualified owner/bridge route",
                "input_axes": list(axes),
                "target_axis": target_axis,
                "selected_route": None,
                "routes": [],
                "atlas_directed_research": dict(receipt.get("atlas_directed_research", {})),
                "semantic_lowering_gaps": list(receipt.get("semantic_lowering_gaps", ())),
                "unlowered_axes": list(receipt.get("unlowered_axes", ())),
                "frontier_filtered_typed_axes": list(receipt.get("frontier_filtered_typed_axes", ())),
                "next_action": str(receipt.get("next_action", "NONE")),
                "claim_boundary": {
                    "atlas_formula_ast_executed_as_solver": False,
                    "structural_semantics_from_real_atlas": True,
                    "prediction_stage_data_derived": False,
                    "name_similarity_lowering_allowed": False,
                    "unknown_promoted_to_route": False,
                },
            }
            result["digest"] = digest_json(result, namespace=b"SCIENCEATLAS_AI_OWNER_HYPERGRAPH_GAP_V1")
            self._append_trace({"kind": "owner_hypergraph_reasoning", "result": result})
            return result

        evaluated: list[HypergraphRoute] = []
        route_groups: dict[str, list[HypergraphRoute]] = {}
        for route in structural:
            route_groups.setdefault(route.bridge_id, []).append(route)
        for bridge_id in sorted(route_groups):
            group = route_groups[bridge_id]
            hypotheses = self.generate_hypotheses_via_route_group([r.route_id for r in group])
            scores = self._evaluate_hypothesis_ids(
                hypothesis_ids=[h.hypothesis_id for h in hypotheses],
                input_axes=axes,
                target_axis=target_axis,
            ) if hypotheses else {}
            best_mse = min((v.prediction_mse for v in scores.values()), default=None)
            plan = self.design_multiaxis_experiment(
                input_axes=axes,
                target_axis=target_axis,
                intervention_axis=intervention_axis,
                candidates=candidates,
                hypothesis_ids=[h.hypothesis_id for h in hypotheses],
                cost=cost,
                risk=risk,
            ) if len(hypotheses) >= 2 else None
            disagreement = Fraction(0) if plan is None else plan.disagreement
            for route0 in group:
                route = self.hypergraph_routes[route0.route_id]
                utility = disagreement / Fraction(1 + route.path_cost)
                updated = replace(
                    route,
                    expected_discrimination=disagreement,
                    route_utility=utility,
                    experiment_id=None if plan is None else plan.experiment_id,
                    hypothesis_ids=tuple(h.hypothesis_id for h in hypotheses),
                    residual_mse=best_mse,
                    status="PREDICTIVE_CANDIDATE" if hypotheses else "UNKNOWN",
                )
                self.hypergraph_routes[route.route_id] = updated
                evaluated.append(updated)

        ranker = self.owner_bus.for_capability("reasoning.owner_hypergraph.route_rank")
        ranked = ranker.rank(evaluated)
        selected = ranked[0] if ranked else None
        if selected is not None:
            selected = replace(selected, status="SELECTED")
            self.hypergraph_routes[selected.route_id] = selected
        result = {
            "status": "SELECTED" if selected is not None else "UNKNOWN",
            "input_axes": list(axes),
            "target_axis": target_axis,
            "selected_route": None if selected is None else selected.to_json(),
            "routes": [self.hypergraph_routes[r.route_id].to_json() for r in ranked],
            "ranking_owner_id": ranker.spec.owner_id,
            "claim_boundary": {
                "atlas_formula_ast_executed_as_solver": False,
                "structural_semantics_from_real_atlas": True,
                "prediction_stage_data_derived": True,
                "name_similarity_lowering_allowed": False,
            },
        }
        result["digest"] = digest_json(result, namespace=b"SCIENCEATLAS_AI_OWNER_HYPERGRAPH_REASONING_V1")
        self._append_trace({"kind": "owner_hypergraph_reasoning", "result": result})
        return result

    def generate_hypotheses(
        self,
        *,
        target_axis: str,
        input_axis: str | None = None,
        input_axes: Sequence[str] | None = None,
        capability: str | None = None,
    ) -> tuple[Hypothesis, ...]:
        axes = self._normalize_axes(input_axis=input_axis, input_axes=input_axes)
        rows_full = self.world.rows_for_axes(axes, target_axis)
        if len(rows_full) < 2:
            self._append_trace({
                "kind": "hypothesis_generation",
                "status": "UNKNOWN",
                "reason": "insufficient complete observations",
                "input_axes": list(axes),
                "target_axis": target_axis,
            })
            return ()
        selected_capability = capability or (
            "hypothesis.numeric_relation.baseline" if len(axes) == 1 else "hypothesis.numeric_relation.multiaxis"
        )
        internal_numeric_capabilities = {
            "hypothesis.numeric_relation.baseline",
            "hypothesis.numeric_relation.multiaxis",
        }
        relation_domains = {self.representation.axes[a].domain for a in (*axes, target_axis)}
        if selected_capability in internal_numeric_capabilities and len(relation_domains) > 1:
            self._append_trace({
                "kind": "hypothesis_generation",
                "status": "UNKNOWN",
                "reason": "cross-domain numeric composition requires an explicit typed Atlas bridge and symbol/dimensional mapping",
                "input_axes": list(axes),
                "target_axis": target_axis,
                "domains": sorted(relation_domains),
            })
            return ()
        owner = self.owner_bus.for_capability(selected_capability)
        if not hasattr(owner, "propose"):
            raise TypeError(f"owner {owner.spec.owner_id} is not a hypothesis owner")
        rows = tuple((xs, y) for _, xs, y in rows_full)
        provenance = self.world.provenance_for_axes((*axes, target_axis))
        proposals = owner.propose(rows, input_axes=axes, target_axis=target_axis, provenance=provenance)
        for hypothesis in proposals:
            self.hypotheses[hypothesis.hypothesis_id] = hypothesis
        self._append_trace({
            "kind": "hypothesis_generation",
            "status": "CANDIDATES" if proposals else "UNKNOWN",
            "owner_id": owner.spec.owner_id,
            "count": len(proposals),
            "hypothesis_ids": [h.hypothesis_id for h in proposals],
            "input_axes": list(axes),
            "target_axis": target_axis,
        })
        return proposals

    def evaluate_hypotheses(
        self,
        *,
        target_axis: str,
        input_axis: str | None = None,
        input_axes: Sequence[str] | None = None,
    ) -> dict[str, CriticVector]:
        axes = self._normalize_axes(input_axis=input_axis, input_axes=input_axes)
        rows = self.world.rows_for_axes(axes, target_axis)
        relevant = [
            h for h in self.hypotheses.values()
            if h.input_axes == axes and h.target_axis == target_axis and h.status != "falsified"
        ]
        scores = CriticEnsemble.evaluate(
            relevant,
            rows,
            owner_bus=self.owner_bus,
            target_axis=self.representation.axes[target_axis],
            previously_validated_families=self.meta.validated_families,
        )
        self.critic_scores.update(scores)
        frontier = CriticEnsemble.pareto_frontier(scores)
        for hypothesis in relevant:
            if hypothesis.hypothesis_id in frontier and hypothesis.status == "candidate":
                self.hypotheses[hypothesis.hypothesis_id] = replace(hypothesis, status="active")
        self._append_trace({
            "kind": "critic_evaluation",
            "input_axes": list(axes),
            "target_axis": target_axis,
            "scores": {k: scores[k].to_json() for k in sorted(scores)},
            "pareto_frontier": list(frontier),
        })
        return scores

    def pareto_hypotheses(
        self,
        *,
        target_axis: str,
        input_axis: str | None = None,
        input_axes: Sequence[str] | None = None,
    ) -> tuple[Hypothesis, ...]:
        axes = self._normalize_axes(input_axis=input_axis, input_axes=input_axes)
        relevant_scores = {
            hid: score
            for hid, score in self.critic_scores.items()
            if hid in self.hypotheses
            and self.hypotheses[hid].input_axes == axes
            and self.hypotheses[hid].target_axis == target_axis
            and self.hypotheses[hid].status != "falsified"
        }
        ids = CriticEnsemble.pareto_frontier(relevant_scores)
        return tuple(self.hypotheses[hid] for hid in ids)

    def assess_frontier(
        self,
        *,
        target_axis: str,
        input_axis: str | None = None,
        input_axes: Sequence[str] | None = None,
        hypothesis_id: str | None = None,
    ) -> FrontierAssessment | None:
        axes = self._normalize_axes(input_axis=input_axis, input_axes=input_axes)
        candidates = [
            h for h in self.hypotheses.values()
            if h.input_axes == axes and h.target_axis == target_axis and h.status != "falsified"
        ]
        if not candidates:
            self._append_trace({"kind": "frontier_assessment", "status": "UNKNOWN", "reason": "no hypotheses"})
            return None
        if hypothesis_id is not None:
            hypothesis = self.hypotheses[hypothesis_id]
            if hypothesis not in candidates:
                raise ValueError("hypothesis does not belong to requested input/target representation")
        else:
            def key(h: Hypothesis) -> tuple[Any, ...]:
                score = self.critic_scores.get(h.hypothesis_id)
                if score is None:
                    return (Fraction(10**30), 10**9, 10**9, h.hypothesis_id)
                return (score.prediction_mse, score.constraint_violations, score.complexity, h.hypothesis_id)
            hypothesis = min(candidates, key=key)
        rows = self.world.rows_for_axes(axes, target_axis)
        unused = {
            axis_id: self.world.values_by_sample(axis_id)
            for axis_id, axis in self.representation.axes.items()
            if axis_id not in axes and axis_id != target_axis and axis.status != "retired"
        }
        owner = self.owner_bus.for_capability("research.residual_frontier")
        assessment = owner.assess(
            hypothesis=hypothesis,
            hypothesis_owner=self.owner_bus.get(hypothesis.owner_id),
            rows=rows,
            unused_axis_values=unused,
            provenance=self.world.provenance_for_axes((*axes, target_axis, *unused.keys())),
        )
        self.frontiers[assessment.frontier_id] = assessment
        self._append_trace({"kind": "frontier_assessment", "assessment": assessment.to_json()})
        return assessment

    def propose_representations(self, frontier_id: str) -> tuple[RepresentationProposal, ...]:
        frontier = self.frontiers[frontier_id]
        owner = self.owner_bus.for_capability("representation.autonomous_proposal")
        proposals = owner.propose(frontier=frontier, axes=self.representation.axes)
        for proposal in proposals:
            self.representation_proposals[proposal.proposal_id] = proposal
        self._append_trace({
            "kind": "representation_proposals",
            "frontier_id": frontier_id,
            "proposals": [p.to_json() for p in proposals],
        })
        return proposals

    def apply_representation_proposal(self, proposal_id: str) -> RepresentationProposal:
        proposal = self.representation_proposals[proposal_id]
        if proposal.action == "NO_ACTION":
            updated = replace(proposal, status="unknown")
            self.representation_proposals[proposal_id] = updated
            self._append_trace({"kind": "representation_proposal_apply", "proposal": updated.to_json()})
            return updated
        if proposal.action == "REQUIRE_TYPED_CROSS_DOMAIN_BRIDGE":
            updated = replace(proposal, status="unknown")
            self.representation_proposals[proposal_id] = updated
            bridge_candidates: list[str] = []
            if self.atlas_registry_snapshot and proposal.domain is not None:
                source_domains = sorted({
                    self.representation.axes[a].domain
                    for a in (*proposal.source_axes, proposal.target_axis)
                    if a in self.representation.axes
                })
                result = self.owner_bus.invoke(
                    "atlas.registry.domain_bridges", action="find", source_domains=source_domains
                )
                bridge_candidates = [str(row.get("bridge_id", "")) for row in result.get("bridges", [])]
            self._append_trace({
                "kind": "representation_proposal_apply",
                "proposal": updated.to_json(),
                "status": "UNKNOWN",
                "reason": "cross-domain activation blocked pending explicit typed bridge plus axis-to-symbol/dimension mapping",
                "candidate_bridge_ids": bridge_candidates,
            })
            return updated
        if proposal.action == "ACTIVATE_EXISTING_AXIS":
            if proposal.proposed_axis_id not in self.representation.axes:
                raise KeyError(f"proposed existing axis missing: {proposal.proposed_axis_id}")
            updated = replace(proposal, status="applied")
            self.representation_proposals[proposal_id] = updated
            self._append_trace({"kind": "representation_proposal_apply", "proposal": updated.to_json()})
            return updated
        if proposal.action == "BIRTH_DIAGNOSTIC_RESIDUAL_AXIS":
            frontier = self.frontiers[proposal.source_frontier_id]
            hypothesis = self.hypotheses[frontier.hypothesis_id]
            target = self.representation.axes[frontier.target_axis]
            axis_id = str(proposal.proposed_axis_id)
            if axis_id not in self.representation.axes:
                self.birth_axis(
                    axis_id=axis_id,
                    name=f"Residual diagnostic for {frontier.target_axis}",
                    semantic_type="model_residual",
                    domain=target.domain,
                    unit=target.unit,
                    validity=ValidityDomain(),
                    parent_axis_id=frontier.target_axis,
                    unit_system=target.unit_system,
                    convention_tags=target.convention_tags,
                )
            rows = self.world.rows_for_axes(hypothesis.input_axes, hypothesis.target_axis)
            owner = self.owner_bus.get(hypothesis.owner_id)
            for sample_id, xs, observed in rows:
                predicted = owner.predict(hypothesis, xs)
                residual = observed - predicted
                evidence_id = digest_json(
                    {
                        "kind": "derived_model_residual",
                        "frontier_id": frontier.frontier_id,
                        "hypothesis_id": hypothesis.hypothesis_id,
                        "sample_id": sample_id,
                        "residual": fraction_json(residual),
                    },
                    namespace=b"SCIENCEATLAS_AI_DERIVED_RESIDUAL_EVIDENCE_V1",
                )[:24]
                evidence = EvidenceRecord(
                    evidence_id=evidence_id,
                    source=f"internal:{hypothesis.hypothesis_id}",
                    source_class="derived_model_diagnostic",
                    reliability_bp=10_000,
                    claim="signed deterministic residual from current model and admitted observations; not independent world evidence",
                    status="support",
                    metadata={"frontier_id": frontier.frontier_id, "derived_not_world_truth": True},
                )
                obs = Observation(
                    sample_id=sample_id,
                    axis_id=axis_id,
                    quantity=SemanticQuantity(
                        value=residual,
                        semantic_type="model_residual",
                        domain=target.domain,
                        unit=target.unit,
                        unit_system=target.unit_system,
                        convention_tags=target.convention_tags,
                    ),
                    evidence_id=evidence_id,
                )
                if evidence_id not in self.world.evidence:
                    self.observe(obs, evidence)
            updated = replace(proposal, status="applied")
            self.representation_proposals[proposal_id] = updated
            self._append_trace({"kind": "representation_proposal_apply", "proposal": updated.to_json()})
            return updated
        raise ValueError(f"unsupported proposal action: {proposal.action}")

    def autonomous_research_step(
        self,
        *,
        input_axes: Sequence[str],
        target_axis: str,
    ) -> Mapping[str, Any]:
        axes = tuple(dict.fromkeys(str(x) for x in input_axes))
        proposals = self.generate_hypotheses(input_axes=axes, target_axis=target_axis)
        scores = self.evaluate_hypotheses(input_axes=axes, target_axis=target_axis) if proposals else {}
        frontier = self.assess_frontier(input_axes=axes, target_axis=target_axis) if proposals else None
        rep_proposals = self.propose_representations(frontier.frontier_id) if frontier is not None else ()
        expanded: tuple[str, ...] | None = None
        expanded_hypotheses: tuple[Hypothesis, ...] = ()
        expanded_scores: dict[str, CriticVector] = {}
        for proposal in rep_proposals:
            if proposal.action != "ACTIVATE_EXISTING_AXIS":
                continue
            self.apply_representation_proposal(proposal.proposal_id)
            if len(proposal.source_axes) <= len(axes):
                continue
            expanded = proposal.source_axes
            expanded_hypotheses = self.generate_hypotheses(input_axes=expanded, target_axis=target_axis)
            if expanded_hypotheses:
                expanded_scores = self.evaluate_hypotheses(input_axes=expanded, target_axis=target_axis)
            break
        payload = {
            "schema": "scienceatlas-ai-autonomous-research-step-v1",
            "initial_input_axes": list(axes),
            "target_axis": target_axis,
            "initial_hypothesis_ids": [h.hypothesis_id for h in proposals],
            "initial_scores": {k: scores[k].to_json() for k in sorted(scores)},
            "frontier": None if frontier is None else frontier.to_json(),
            "representation_proposals": [p.to_json() for p in rep_proposals],
            "expanded_input_axes": None if expanded is None else list(expanded),
            "expanded_hypothesis_ids": [h.hypothesis_id for h in expanded_hypotheses],
            "expanded_scores": {k: expanded_scores[k].to_json() for k in sorted(expanded_scores)},
        }
        result = {**payload, "digest": digest_json(payload, namespace=b"SCIENCEATLAS_AI_AUTONOMOUS_RESEARCH_STEP_V1")}
        self._append_trace({"kind": "autonomous_research_step", "result": result})
        return result

    def _automatic_experiment_candidates(self, input_axis: str) -> tuple[SemanticQuantity, ...]:
        axis = self.representation.axes[input_axis]
        values = sorted(set(self.world.values_for_axis(input_axis)))
        if not values:
            return ()
        if len(values) == 1:
            step = Fraction(1)
        else:
            gaps = [b - a for a, b in zip(values, values[1:]) if b != a]
            step = min((abs(g) for g in gaps), default=Fraction(1))
            if step == 0:
                step = Fraction(1)
        raw = [values[0] - step, values[-1] + step]
        if len(values) > 1:
            raw.extend([(values[0] + values[-1]) / 2, values[0] - 2 * step, values[-1] + 2 * step])
        unique: list[Fraction] = []
        for value in raw:
            if value in values or value in unique or not axis.validity.contains(value):
                continue
            unique.append(value)
        return tuple(
            SemanticQuantity(
                value=value,
                semantic_type=axis.semantic_type,
                domain=axis.domain,
                unit=axis.unit,
                validity=axis.validity,
                quantity_id=axis.quantity_id,
                dimension=axis.dimension,
                unit_system=axis.unit_system,
                convention_tags=axis.convention_tags,
            )
            for value in unique
        )

    def _default_context_quantity(self, axis_id: str) -> SemanticQuantity:
        axis = self.representation.axes[axis_id]
        values = sorted(self.world.values_for_axis(axis_id))
        if not values:
            raise ValueError(f"cannot construct experiment context for unobserved axis {axis_id}")
        value = values[len(values) // 2]
        return SemanticQuantity(
            value=value,
            semantic_type=axis.semantic_type,
            domain=axis.domain,
            unit=axis.unit,
            validity=axis.validity,
            quantity_id=axis.quantity_id,
            dimension=axis.dimension,
            unit_system=axis.unit_system,
            convention_tags=axis.convention_tags,
        )

    def design_multiaxis_experiment(
        self,
        *,
        input_axes: Sequence[str],
        target_axis: str,
        intervention_axis: str | None = None,
        context_values: Mapping[str, SemanticQuantity] | None = None,
        candidates: Sequence[SemanticQuantity] | None = None,
        hypothesis_ids: Sequence[str] | None = None,
        cost: int | Fraction = 1,
        risk: int | Fraction = 0,
    ) -> ExperimentPlan | None:
        axes = self._normalize_axes(input_axes=input_axes)
        intervention = str(intervention_axis or axes[0])
        if intervention not in axes:
            raise ValueError("intervention_axis must belong to input_axes")
        if hypothesis_ids is not None:
            wanted = tuple(dict.fromkeys(str(x) for x in hypothesis_ids))
            hypotheses = tuple(
                self.hypotheses[hid] for hid in wanted
                if hid in self.hypotheses
                and self.hypotheses[hid].input_axes == axes
                and self.hypotheses[hid].target_axis == target_axis
                and self.hypotheses[hid].status != "falsified"
            )
        else:
            hypotheses = self.pareto_hypotheses(input_axes=axes, target_axis=target_axis)
            if len(hypotheses) < 2:
                hypotheses = tuple(
                    h for h in self.hypotheses.values()
                    if h.input_axes == axes and h.target_axis == target_axis and h.status != "falsified"
                )
        if len(hypotheses) < 2:
            self._append_trace({"kind": "experiment_design", "status": "UNKNOWN", "reason": "fewer than two competing hypotheses"})
            return None
        axis = self.representation.axes[intervention]
        proposed = tuple(candidates) if candidates is not None else self._automatic_experiment_candidates(intervention)
        valid_candidates = [
            q for q in proposed
            if q.semantic_type == axis.semantic_type
            and q.domain == axis.domain
            and q.unit == axis.unit
            and q.unit_system == axis.unit_system
            and (axis.quantity_id is None or q.quantity_id == axis.quantity_id)
            and (axis.dimension is None or q.dimension == axis.dimension)
            and axis.validity.contains(q.value)
        ]
        if not valid_candidates:
            self._append_trace({"kind": "experiment_design", "status": "UNKNOWN", "reason": "no valid candidate interventions"})
            return None
        context: dict[str, SemanticQuantity] = {}
        for axis_id in axes:
            if axis_id == intervention:
                continue
            supplied = None if context_values is None else context_values.get(axis_id)
            q = supplied if supplied is not None else self._default_context_quantity(axis_id)
            expected = self.representation.axes[axis_id]
            if (
                q.semantic_type != expected.semantic_type
                or q.domain != expected.domain
                or q.unit != expected.unit
                or q.unit_system != expected.unit_system
                or (expected.quantity_id is not None and q.quantity_id != expected.quantity_id)
                or (expected.dimension is not None and q.dimension != expected.dimension)
            ):
                raise TypeError(f"context quantity mismatch for axis {axis_id}")
            context[axis_id] = q
        cost_f = as_fraction(cost)
        risk_f = as_fraction(risk)
        best: tuple[Fraction, SemanticQuantity, dict[str, Fraction], Fraction] | None = None
        for q in valid_candidates:
            point = {axis_id: context[axis_id].value for axis_id in context}
            point[intervention] = q.value
            predictions: dict[str, Fraction] = {}
            for hypothesis in hypotheses:
                try:
                    predictions[hypothesis.hypothesis_id] = self.owner_bus.get(hypothesis.owner_id).predict(hypothesis, point)
                except (ValueError, ZeroDivisionError, KeyError, TypeError):
                    continue
            if len(predictions) < 2:
                continue
            values = list(predictions.values())
            pairs = [(a - b) ** 2 for i, a in enumerate(values) for b in values[i + 1 :]]
            disagreement = sum(pairs, Fraction(0)) / len(pairs)
            utility = disagreement / (Fraction(1) + cost_f + risk_f)
            candidate_tuple = (utility, q, predictions, disagreement)
            if best is None or utility > best[0] or (utility == best[0] and q.value < best[1].value):
                best = candidate_tuple
        if best is None:
            self._append_trace({"kind": "experiment_design", "status": "UNKNOWN", "reason": "hypotheses had no jointly valid predictions"})
            return None
        _, q, predictions, disagreement = best
        pred_payload = {hid: fraction_json(predictions[hid]) for hid in sorted(predictions)}
        prediction_digest = digest_json(pred_payload, namespace=b"SCIENCEATLAS_AI_EXPERIMENT_PREDICTIONS_V2")
        owner_ids = sorted({self.hypotheses[hid].owner_id for hid in predictions})
        owner_id = owner_ids[0] if len(owner_ids) == 1 else "multi-owner"
        experiment_id = digest_json(
            {
                "input_axes": list(axes),
                "intervention_axis": intervention,
                "target_axis": target_axis,
                "input_value": q.to_json(),
                "context_values": {k: context[k].to_json() for k in sorted(context)},
                "prediction_digest": prediction_digest,
                "trace_head": self.trace.head,
            },
            namespace=b"SCIENCEATLAS_AI_EXPERIMENT_V2",
        )[:24]
        plan = ExperimentPlan(
            experiment_id=experiment_id,
            owner_id=owner_id,
            input_axis=intervention,
            input_axes=axes,
            target_axis=target_axis,
            input_value=q,
            context_values=context,
            disagreement=disagreement,
            cost=cost_f,
            risk=risk_f,
            hypothesis_ids=tuple(sorted(predictions)),
            prediction_digest=prediction_digest,
        )
        self.experiments[experiment_id] = plan
        self._append_trace({"kind": "experiment_design", "status": "PLANNED", "plan": plan.to_json(), "predictions": pred_payload})
        return plan

    def design_experiment(
        self,
        *,
        input_axis: str,
        target_axis: str,
        candidates: Sequence[SemanticQuantity] | None = None,
        cost: int | Fraction = 1,
        risk: int | Fraction = 0,
    ) -> ExperimentPlan | None:
        return self.design_multiaxis_experiment(
            input_axes=(input_axis,),
            target_axis=target_axis,
            intervention_axis=input_axis,
            candidates=candidates,
            cost=cost,
            risk=risk,
        )

    def record_validation(self, outcome: ValidationOutcome, *, validated_family: str | None = None) -> int:
        if outcome.experiment_id not in self.experiments:
            raise KeyError(f"unknown experiment: {outcome.experiment_id}")
        if outcome.owner_id == "multi-owner":
            raise ValueError("multi-owner validation must be attributed to a concrete owner")
        updated = self.meta.update(outcome)
        if outcome.success and validated_family:
            self.meta.validated_families.add(validated_family)
        self._append_trace({
            "kind": "validated_feedback",
            "outcome": outcome.to_json(),
            "strategy_score_bp": updated,
            "validated_family": validated_family,
        })
        return updated

    def freeze(self, label: str) -> str:
        if not label.strip():
            raise ValueError("freeze label is required")
        root = self.snapshot_root()
        self.freezes[label] = root
        self._append_trace({"kind": "freeze", "label": label, "snapshot_root_before_freeze_event": root})
        return root

    def attach_model_execution_backend(self, backend: ModelExecutionBackend) -> dict[str, Any]:
        owner = self.owner_bus.for_capability("ai.laboratory.factorial_execution")
        owner.attach_backend(backend)
        status = dict(owner.status())
        self._append_trace({
            "kind": "ai_laboratory_backend_attached",
            "backend": backend.spec.to_json(),
            "status": status.get("status"),
        })
        return status

    def detach_model_execution_backend(self) -> None:
        owner = self.owner_bus.for_capability("ai.laboratory.factorial_execution")
        owner.detach_backend()
        self._append_trace({"kind": "ai_laboratory_backend_detached"})

    def ai_laboratory_status(self) -> dict[str, Any]:
        owner = self.owner_bus.for_capability("ai.laboratory.factorial_execution")
        status = dict(owner.status())
        status["capability_contracts"] = {
            capability: dict(self.owner_bus.invoke(capability, action="status"))
            for capability in self.owner_bus.capabilities()
            if capability.startswith("ai.") and capability != "ai.laboratory.factorial_execution"
        }
        return status

    def run_ai_factorial_experiment(
        self,
        *,
        manifest_rows: Sequence[Mapping[str, Any]],
        task_regimes: Sequence[str],
        seed: int = 0,
        require_real: bool = True,
    ) -> dict[str, Any]:
        owner = self.owner_bus.for_capability("ai.laboratory.factorial_execution")
        receipt = dict(owner.execute_factorial(
            manifest_rows=manifest_rows,
            task_regimes=task_regimes,
            seed=seed,
            require_real=require_real,
        ))
        run_digest = str(receipt["run_digest"])
        self.laboratory_runs[run_digest] = receipt
        self._append_trace({
            "kind": "ai_laboratory_factorial_run",
            "run_digest": run_digest,
            "measurement_count": receipt.get("measurement_count", 0),
            "scientific_measurement": receipt.get("scientific_measurement", False),
        })
        return receipt

    def research_status(
        self,
        *,
        target_axis: str,
        input_axis: str | None = None,
        input_axes: Sequence[str] | None = None,
    ) -> str:
        axes = self._normalize_axes(input_axis=input_axis, input_axes=input_axes)
        relevant = [
            h for h in self.hypotheses.values()
            if h.input_axes == axes and h.target_axis == target_axis and h.status != "falsified"
        ]
        if not relevant:
            return "UNKNOWN"
        return "CANDIDATES"

    def authoritative_components(self) -> dict[str, Any]:
        return {
            "representation": self.representation.to_json(),
            "world": self.world.to_json(),
            "hypotheses": {k: self.hypotheses[k].to_json() for k in sorted(self.hypotheses)},
            "critic_scores": {k: self.critic_scores[k].to_json() for k in sorted(self.critic_scores)},
            "frontiers": {k: self.frontiers[k].to_json() for k in sorted(self.frontiers)},
            "representation_proposals": {k: self.representation_proposals[k].to_json() for k in sorted(self.representation_proposals)},
            "experiments": {k: self.experiments[k].to_json() for k in sorted(self.experiments)},
            "hypergraph_routes": {k: self.hypergraph_routes[k].to_json() for k in sorted(self.hypergraph_routes)},
            "hypergraph_queries": {k: self.hypergraph_queries[k] for k in sorted(self.hypergraph_queries)},
            "last_hypergraph_query_digest": self.last_hypergraph_query_digest,
            "subspace_candidates": {k: self.subspace_candidates[k].to_json() for k in sorted(self.subspace_candidates)},
            "subspace_searches": {k: self.subspace_searches[k].to_json() for k in sorted(self.subspace_searches)},
            "dimension_profiles": {k: self.dimension_profiles[k].to_json() for k in sorted(self.dimension_profiles)},
            "known_monomial_relations": {k: self.known_monomial_relations[k].to_json() for k in sorted(self.known_monomial_relations)},
            "methodology_records": {k: self.methodology_records[k] for k in sorted(self.methodology_records)},
            "qualification_runs": {k: self.qualification_runs[k] for k in sorted(self.qualification_runs)},
            "laboratory_runs": {k: self.laboratory_runs[k] for k in sorted(self.laboratory_runs)},
            "meta": self.meta.to_json(),
            "freezes": {k: self.freezes[k] for k in sorted(self.freezes)},
            "owner_specs": [spec.to_json() for spec in self.owner_bus.specs()],
            "atlas_registry_snapshot": dict(self.atlas_registry_snapshot),
            "runtime_contract_digest": self.runtime_contract_digest,
        }

    def snapshot_root(self) -> str:
        components = self.authoritative_components()
        roots = {
            name: digest_json(payload, namespace=f"SCIENCEATLAS_AI_COMPONENT_{name.upper()}_V6".encode("ascii"))
            for name, payload in components.items()
        }
        roots["trace_head"] = self.trace.head
        return mapping_root(roots, namespace=b"SCIENCEATLAS_AI_SNAPSHOT_ROOT_V6")

    def to_json(self) -> dict[str, Any]:
        components = self.authoritative_components()
        return {
            "schema": "scienceatlas-ai-state-v0.10.0",
            "version": self.VERSION,
            **components,
            "trace": self.trace.to_json(),
            "snapshot_root": self.snapshot_root(),
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "ScienceAtlasAI":
        state_version = str(payload.get("version"))
        if state_version not in {"0.7.0", "0.9.0", cls.VERSION}:
            raise ValueError(f"unsupported state version: {payload.get('version')}")
        obj = cls(register_baseline_owner=True)
        expected_builtin = {spec.owner_id: spec.to_json() for spec in obj.owner_bus.specs()}
        supplied_specs = [OwnerSpec.from_json(row) for row in payload.get("owner_specs", [])]
        supplied_by_id = {spec.owner_id: spec for spec in supplied_specs}
        for owner_id, expected in expected_builtin.items():
            actual = supplied_by_id.get(owner_id)
            if actual is None or actual.to_json() != expected:
                raise ValueError(f"saved built-in owner contract mismatch: {owner_id}")
        for spec in supplied_specs:
            if spec.owner_id not in expected_builtin:
                obj.owner_bus.register(DetachedOwner(spec))
        if str(payload.get("runtime_contract_digest", "")) != obj.runtime_contract_digest:
            raise ValueError("runtime contract digest mismatch")
        obj.representation = RepresentationGraph.from_json(payload.get("representation", {}))
        obj.world = WorldModel.from_json(payload.get("world", {}))
        obj.hypotheses = {str(k): Hypothesis.from_json(v) for k, v in payload.get("hypotheses", {}).items()}
        obj.critic_scores = {str(k): CriticVector.from_json(v) for k, v in payload.get("critic_scores", {}).items()}
        obj.frontiers = {str(k): FrontierAssessment.from_json(v) for k, v in payload.get("frontiers", {}).items()}
        obj.representation_proposals = {str(k): RepresentationProposal.from_json(v) for k, v in payload.get("representation_proposals", {}).items()}
        obj.experiments = {str(k): ExperimentPlan.from_json(row) for k, row in payload.get("experiments", {}).items()}
        obj.hypergraph_routes = {str(k): HypergraphRoute.from_json(row) for k, row in payload.get("hypergraph_routes", {}).items()}
        obj.hypergraph_queries = {str(k): dict(row) for k, row in payload.get("hypergraph_queries", {}).items()}
        obj.last_hypergraph_query_digest = str(payload.get("last_hypergraph_query_digest", ""))
        obj.subspace_candidates = {str(k): SubspaceCandidate.from_json(v) for k, v in payload.get("subspace_candidates", {}).items()}
        obj.subspace_searches = {str(k): SubspaceSearchState.from_json(v) for k, v in payload.get("subspace_searches", {}).items()}
        obj.dimension_profiles = {str(k): DimensionHypothesisProfile.from_json(v) for k, v in payload.get("dimension_profiles", {}).items()}
        obj.known_monomial_relations = {str(k): KnownMonomialRelation.from_json(v) for k, v in payload.get("known_monomial_relations", {}).items()}
        obj.methodology_records = {str(k): dict(v) for k, v in payload.get("methodology_records", {}).items()}
        obj.qualification_runs = {str(k): dict(v) for k, v in payload.get("qualification_runs", {}).items()}
        obj.laboratory_runs = {str(k): dict(v) for k, v in payload.get("laboratory_runs", {}).items()}
        obj.meta = MetaLearner.from_json(payload.get("meta", {}))
        obj.freezes = {str(k): str(v) for k, v in payload.get("freezes", {}).items()}
        obj.atlas_registry_snapshot = dict(payload.get("atlas_registry_snapshot", {}))
        obj.trace = ProvenanceTrace.from_json(payload.get("trace", {}))
        observed_root = obj.snapshot_root()
        if observed_root != str(payload.get("snapshot_root", "")):
            raise ValueError("authoritative snapshot root mismatch")
        return obj
