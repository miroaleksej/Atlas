"""Semantic contracts for ScienceAtlas AI.

The central invariant is that scientific quantities are not anonymous integers.
Every quantity carries semantic type, domain, unit, validity and uncertainty.
Cryptographic residues are represented by a distinct type and there is no
implicit conversion from SemanticQuantity to ScalarResidue.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Mapping, Sequence


def as_fraction(value: int | Fraction | tuple[int, int]) -> Fraction:
    if isinstance(value, bool):
        raise TypeError("boolean is not a numeric scientific value")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, tuple) and len(value) == 2:
        return Fraction(int(value[0]), int(value[1]))
    raise TypeError(f"unsupported exact numeric value: {type(value).__name__}")


def fraction_json(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


def fraction_from_json(payload: Mapping[str, Any]) -> Fraction:
    return Fraction(int(payload["numerator"]), int(payload["denominator"]))


def normalize_dimension(value: Sequence[str] | None) -> tuple[str, ...] | None:
    if value is None:
        return None
    dim = tuple(str(x).strip() for x in value)
    if len(dim) != 7 or any(not x for x in dim):
        raise ValueError("dimension vector must contain exactly seven non-empty SI exponents")
    return dim


def dimension_json(value: tuple[str, ...] | None) -> list[str] | None:
    return None if value is None else list(value)


@dataclass(frozen=True, slots=True)
class ValidityDomain:
    minimum: Fraction | None = None
    maximum: Fraction | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        if self.minimum is not None:
            object.__setattr__(self, "minimum", as_fraction(self.minimum))
        if self.maximum is not None:
            object.__setattr__(self, "maximum", as_fraction(self.maximum))
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("validity minimum exceeds maximum")

    def contains(self, value: Fraction) -> bool:
        if self.minimum is not None and value < self.minimum:
            return False
        if self.maximum is not None and value > self.maximum:
            return False
        return True

    def to_json(self) -> dict[str, Any]:
        return {
            "minimum": None if self.minimum is None else fraction_json(self.minimum),
            "maximum": None if self.maximum is None else fraction_json(self.maximum),
            "notes": self.notes,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "ValidityDomain":
        mn = payload.get("minimum")
        mx = payload.get("maximum")
        return cls(
            minimum=None if mn is None else fraction_from_json(mn),
            maximum=None if mx is None else fraction_from_json(mx),
            notes=str(payload.get("notes", "")),
        )


@dataclass(frozen=True, slots=True)
class SemanticQuantity:
    value: Fraction
    semantic_type: str
    domain: str
    unit: str
    validity: ValidityDomain = field(default_factory=ValidityDomain)
    uncertainty: Fraction | None = None
    quantity_id: str | None = None
    dimension: tuple[str, ...] | None = None
    unit_system: str = "SI"
    convention_tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "value", as_fraction(self.value))
        if self.uncertainty is not None:
            u = as_fraction(self.uncertainty)
            if u < 0:
                raise ValueError("uncertainty cannot be negative")
            object.__setattr__(self, "uncertainty", u)
        for name in ("semantic_type", "domain", "unit"):
            raw = str(getattr(self, name)).strip()
            if not raw:
                raise ValueError(f"{name} is required")
            object.__setattr__(self, name, raw)
        if self.semantic_type in {"cryptographic_scalar", "field_residue", "evm_scalar"}:
            raise TypeError("scientific quantity cannot masquerade as cryptographic scalar")
        if self.quantity_id is not None:
            qid = str(self.quantity_id).strip()
            if not qid:
                raise ValueError("quantity_id cannot be blank")
            object.__setattr__(self, "quantity_id", qid)
        object.__setattr__(self, "dimension", normalize_dimension(self.dimension))
        unit_system = str(self.unit_system).strip()
        if not unit_system:
            raise ValueError("unit_system is required")
        object.__setattr__(self, "unit_system", unit_system)
        object.__setattr__(self, "convention_tags", tuple(dict.fromkeys(str(x).strip() for x in self.convention_tags if str(x).strip())))
        if not self.validity.contains(self.value):
            raise ValueError("quantity lies outside declared validity domain")

    @property
    def sign(self) -> int:
        return (self.value > 0) - (self.value < 0)

    def compatible_with(self, other: "SemanticQuantity") -> bool:
        return (
            self.semantic_type == other.semantic_type
            and self.domain == other.domain
            and self.unit == other.unit
            and self.quantity_id == other.quantity_id
            and self.dimension == other.dimension
            and self.unit_system == other.unit_system
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scienceatlas-ai-semantic-quantity-v1",
            "value": fraction_json(self.value),
            "sign": self.sign,
            "semantic_type": self.semantic_type,
            "domain": self.domain,
            "unit": self.unit,
            "validity": self.validity.to_json(),
            "uncertainty": None if self.uncertainty is None else fraction_json(self.uncertainty),
            "quantity_id": self.quantity_id,
            "dimension": dimension_json(self.dimension),
            "unit_system": self.unit_system,
            "convention_tags": list(self.convention_tags),
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "SemanticQuantity":
        unc = payload.get("uncertainty")
        return cls(
            value=fraction_from_json(payload["value"]),
            semantic_type=str(payload["semantic_type"]),
            domain=str(payload["domain"]),
            unit=str(payload["unit"]),
            validity=ValidityDomain.from_json(payload.get("validity", {})),
            uncertainty=None if unc is None else fraction_from_json(unc),
            quantity_id=None if payload.get("quantity_id") is None else str(payload["quantity_id"]),
            dimension=normalize_dimension(payload.get("dimension")),
            unit_system=str(payload.get("unit_system", "SI")),
            convention_tags=tuple(str(x) for x in payload.get("convention_tags", ())),
        )


@dataclass(frozen=True, slots=True)
class ScalarResidue:
    """Explicit cryptographic residue. Never accepted as a scientific quantity."""

    value: int
    modulus: int
    namespace: str

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or isinstance(self.modulus, bool):
            raise TypeError("scalar residue requires integers")
        if self.modulus <= 2:
            raise ValueError("modulus must exceed 2")
        object.__setattr__(self, "value", int(self.value) % int(self.modulus))
        ns = str(self.namespace).strip()
        if not ns:
            raise ValueError("namespace is required")
        object.__setattr__(self, "namespace", ns)

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": "scienceatlas-ai-explicit-scalar-residue-v1",
            "value": self.value,
            "modulus": self.modulus,
            "namespace": self.namespace,
        }


@dataclass(frozen=True, slots=True)
class Axis:
    axis_id: str
    name: str
    semantic_type: str
    domain: str
    unit: str
    validity: ValidityDomain = field(default_factory=ValidityDomain)
    parent_axis_id: str | None = None
    revision: int = 1
    status: str = "active"
    quantity_id: str | None = None
    dimension: tuple[str, ...] | None = None
    aliases: tuple[str, ...] = ()
    unit_system: str = "SI"
    convention_tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("axis_id", "name", "semantic_type", "domain", "unit"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} is required")
        if self.semantic_type in {"cryptographic_scalar", "field_residue", "evm_scalar"}:
            raise TypeError("representation axis cannot use a cryptographic scalar semantic type")
        if self.quantity_id is not None:
            qid = str(self.quantity_id).strip()
            if not qid:
                raise ValueError("quantity_id cannot be blank")
            object.__setattr__(self, "quantity_id", qid)
        object.__setattr__(self, "dimension", normalize_dimension(self.dimension))
        object.__setattr__(self, "aliases", tuple(dict.fromkeys(str(x).strip() for x in self.aliases if str(x).strip())))
        unit_system = str(self.unit_system).strip()
        if not unit_system:
            raise ValueError("unit_system is required")
        object.__setattr__(self, "unit_system", unit_system)
        object.__setattr__(self, "convention_tags", tuple(dict.fromkeys(str(x).strip() for x in self.convention_tags if str(x).strip())))
        if self.revision < 1:
            raise ValueError("axis revision must be >= 1")
        if self.status not in {"active", "refined", "split", "retired"}:
            raise ValueError("unsupported axis status")

    def to_json(self) -> dict[str, Any]:
        return {
            "axis_id": self.axis_id,
            "name": self.name,
            "semantic_type": self.semantic_type,
            "domain": self.domain,
            "unit": self.unit,
            "validity": self.validity.to_json(),
            "parent_axis_id": self.parent_axis_id,
            "revision": self.revision,
            "status": self.status,
            "quantity_id": self.quantity_id,
            "dimension": dimension_json(self.dimension),
            "aliases": list(self.aliases),
            "unit_system": self.unit_system,
            "convention_tags": list(self.convention_tags),
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "Axis":
        return cls(
            axis_id=str(payload["axis_id"]),
            name=str(payload["name"]),
            semantic_type=str(payload["semantic_type"]),
            domain=str(payload["domain"]),
            unit=str(payload["unit"]),
            validity=ValidityDomain.from_json(payload.get("validity", {})),
            parent_axis_id=None if payload.get("parent_axis_id") is None else str(payload["parent_axis_id"]),
            revision=int(payload.get("revision", 1)),
            status=str(payload.get("status", "active")),
            quantity_id=None if payload.get("quantity_id") is None else str(payload["quantity_id"]),
            dimension=normalize_dimension(payload.get("dimension")),
            aliases=tuple(str(x) for x in payload.get("aliases", ())),
            unit_system=str(payload.get("unit_system", "SI")),
            convention_tags=tuple(str(x) for x in payload.get("convention_tags", ())),
        )


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    evidence_id: str
    source: str
    source_class: str
    reliability_bp: int
    claim: str
    status: str = "support"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.evidence_id.strip() or not self.source.strip() or not self.claim.strip():
            raise ValueError("evidence_id, source and claim are required")
        if not 0 <= int(self.reliability_bp) <= 10_000:
            raise ValueError("reliability_bp must be in [0,10000]")
        if self.status not in {"support", "contradict", "retract", "unknown"}:
            raise ValueError("unsupported evidence status")
        object.__setattr__(self, "metadata", dict(self.metadata))

    def to_json(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source": self.source,
            "source_class": self.source_class,
            "reliability_bp": int(self.reliability_bp),
            "claim": self.claim,
            "status": self.status,
            "metadata": self.metadata,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "EvidenceRecord":
        return cls(
            evidence_id=str(payload["evidence_id"]),
            source=str(payload["source"]),
            source_class=str(payload.get("source_class", "unknown")),
            reliability_bp=int(payload.get("reliability_bp", 0)),
            claim=str(payload["claim"]),
            status=str(payload.get("status", "support")),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(frozen=True, slots=True)
class Observation:
    sample_id: str
    axis_id: str
    quantity: SemanticQuantity
    evidence_id: str

    def to_json(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "axis_id": self.axis_id,
            "quantity": self.quantity.to_json(),
            "evidence_id": self.evidence_id,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "Observation":
        return cls(
            sample_id=str(payload["sample_id"]),
            axis_id=str(payload["axis_id"]),
            quantity=SemanticQuantity.from_json(payload["quantity"]),
            evidence_id=str(payload["evidence_id"]),
        )


@dataclass(frozen=True, slots=True)
class Hypothesis:
    hypothesis_id: str
    owner_id: str
    family: str
    input_axes: tuple[str, ...]
    target_axis: str
    parameters: tuple[Fraction, ...]
    complexity: int
    validity: ValidityDomain = field(default_factory=ValidityDomain)
    status: str = "candidate"
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", tuple(as_fraction(v) for v in self.parameters))
        if self.complexity < 0:
            raise ValueError("complexity cannot be negative")
        if self.status not in {"candidate", "active", "validated", "falsified", "unknown"}:
            raise ValueError("unsupported hypothesis status")

    def to_json(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "owner_id": self.owner_id,
            "family": self.family,
            "input_axes": list(self.input_axes),
            "target_axis": self.target_axis,
            "parameters": [fraction_json(v) for v in self.parameters],
            "complexity": self.complexity,
            "validity": self.validity.to_json(),
            "status": self.status,
            "provenance": list(self.provenance),
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "Hypothesis":
        return cls(
            hypothesis_id=str(payload["hypothesis_id"]),
            owner_id=str(payload["owner_id"]),
            family=str(payload["family"]),
            input_axes=tuple(str(x) for x in payload.get("input_axes", [])),
            target_axis=str(payload["target_axis"]),
            parameters=tuple(fraction_from_json(v) for v in payload.get("parameters", [])),
            complexity=int(payload.get("complexity", 0)),
            validity=ValidityDomain.from_json(payload.get("validity", {})),
            status=str(payload.get("status", "candidate")),
            provenance=tuple(str(x) for x in payload.get("provenance", [])),
        )


@dataclass(frozen=True, slots=True)
class CriticVector:
    hypothesis_id: str
    prediction_mse: Fraction
    max_abs_error: Fraction
    constraint_violations: int
    complexity: int
    novelty_rank: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "prediction_mse", as_fraction(self.prediction_mse))
        object.__setattr__(self, "max_abs_error", as_fraction(self.max_abs_error))

    def to_json(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "prediction_mse": fraction_json(self.prediction_mse),
            "max_abs_error": fraction_json(self.max_abs_error),
            "constraint_violations": self.constraint_violations,
            "complexity": self.complexity,
            "novelty_rank": self.novelty_rank,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "CriticVector":
        return cls(
            hypothesis_id=str(payload["hypothesis_id"]),
            prediction_mse=fraction_from_json(payload["prediction_mse"]),
            max_abs_error=fraction_from_json(payload["max_abs_error"]),
            constraint_violations=int(payload.get("constraint_violations", 0)),
            complexity=int(payload.get("complexity", 0)),
            novelty_rank=int(payload.get("novelty_rank", 0)),
        )


@dataclass(frozen=True, slots=True)
class ExperimentPlan:
    experiment_id: str
    owner_id: str
    input_axis: str
    target_axis: str
    input_value: SemanticQuantity
    disagreement: Fraction
    cost: Fraction
    risk: Fraction
    hypothesis_ids: tuple[str, ...]
    prediction_digest: str
    input_axes: tuple[str, ...] = ()
    context_values: dict[str, SemanticQuantity] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "disagreement", as_fraction(self.disagreement))
        object.__setattr__(self, "cost", as_fraction(self.cost))
        object.__setattr__(self, "risk", as_fraction(self.risk))
        object.__setattr__(self, "context_values", dict(self.context_values))
        if self.cost < 0 or self.risk < 0:
            raise ValueError("experiment cost/risk cannot be negative")
        axes = tuple(self.input_axes) if self.input_axes else (self.input_axis,)
        if self.input_axis not in axes:
            raise ValueError("intervention axis must be included in input_axes")
        object.__setattr__(self, "input_axes", axes)

    def to_json(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "owner_id": self.owner_id,
            "input_axis": self.input_axis,
            "input_axes": list(self.input_axes),
            "target_axis": self.target_axis,
            "input_value": self.input_value.to_json(),
            "context_values": {k: self.context_values[k].to_json() for k in sorted(self.context_values)},
            "disagreement": fraction_json(self.disagreement),
            "cost": fraction_json(self.cost),
            "risk": fraction_json(self.risk),
            "hypothesis_ids": list(self.hypothesis_ids),
            "prediction_digest": self.prediction_digest,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "ExperimentPlan":
        return cls(
            experiment_id=str(payload["experiment_id"]),
            owner_id=str(payload["owner_id"]),
            input_axis=str(payload["input_axis"]),
            input_axes=tuple(str(x) for x in payload.get("input_axes", (payload["input_axis"],))),
            target_axis=str(payload["target_axis"]),
            input_value=SemanticQuantity.from_json(payload["input_value"]),
            context_values={str(k): SemanticQuantity.from_json(v) for k, v in payload.get("context_values", {}).items()},
            disagreement=fraction_from_json(payload["disagreement"]),
            cost=fraction_from_json(payload["cost"]),
            risk=fraction_from_json(payload["risk"]),
            hypothesis_ids=tuple(str(x) for x in payload.get("hypothesis_ids", [])),
            prediction_digest=str(payload["prediction_digest"]),
        )


@dataclass(frozen=True, slots=True)
class ValidationOutcome:
    experiment_id: str
    owner_id: str
    success: bool
    prediction_gain_bp: int
    notes: str = ""

    def __post_init__(self) -> None:
        if not 0 <= int(self.prediction_gain_bp) <= 10_000:
            raise ValueError("prediction_gain_bp must be in [0,10000]")

    def to_json(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "owner_id": self.owner_id,
            "success": bool(self.success),
            "prediction_gain_bp": int(self.prediction_gain_bp),
            "notes": self.notes,
        }


@dataclass(frozen=True, slots=True)
class FrontierAxisScore:
    axis_id: str
    residual_r2: Fraction
    paired_count: int
    residual_variance: Fraction
    axis_variance: Fraction

    def __post_init__(self) -> None:
        object.__setattr__(self, "residual_r2", as_fraction(self.residual_r2))
        object.__setattr__(self, "residual_variance", as_fraction(self.residual_variance))
        object.__setattr__(self, "axis_variance", as_fraction(self.axis_variance))
        if self.paired_count < 0:
            raise ValueError("paired_count cannot be negative")
        if self.residual_r2 < 0 or self.residual_r2 > 1:
            raise ValueError("residual_r2 must be in [0,1]")

    def to_json(self) -> dict[str, Any]:
        return {
            "axis_id": self.axis_id,
            "residual_r2": fraction_json(self.residual_r2),
            "paired_count": self.paired_count,
            "residual_variance": fraction_json(self.residual_variance),
            "axis_variance": fraction_json(self.axis_variance),
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "FrontierAxisScore":
        return cls(
            axis_id=str(payload["axis_id"]),
            residual_r2=fraction_from_json(payload["residual_r2"]),
            paired_count=int(payload.get("paired_count", 0)),
            residual_variance=fraction_from_json(payload["residual_variance"]),
            axis_variance=fraction_from_json(payload["axis_variance"]),
        )


@dataclass(frozen=True, slots=True)
class FrontierAssessment:
    frontier_id: str
    hypothesis_id: str
    input_axes: tuple[str, ...]
    target_axis: str
    residual_mse: Fraction
    max_abs_residual: Fraction
    candidate_axes: tuple[FrontierAxisScore, ...]
    status: str
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "residual_mse", as_fraction(self.residual_mse))
        object.__setattr__(self, "max_abs_residual", as_fraction(self.max_abs_residual))
        if self.status not in {"CLOSED_ON_OBSERVED_DATA", "REPRESENTATION_FRONTIER", "UNEXPLAINED_RESIDUAL", "UNKNOWN"}:
            raise ValueError("unsupported frontier status")

    def to_json(self) -> dict[str, Any]:
        return {
            "frontier_id": self.frontier_id,
            "hypothesis_id": self.hypothesis_id,
            "input_axes": list(self.input_axes),
            "target_axis": self.target_axis,
            "residual_mse": fraction_json(self.residual_mse),
            "max_abs_residual": fraction_json(self.max_abs_residual),
            "candidate_axes": [x.to_json() for x in self.candidate_axes],
            "status": self.status,
            "provenance": list(self.provenance),
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "FrontierAssessment":
        return cls(
            frontier_id=str(payload["frontier_id"]),
            hypothesis_id=str(payload["hypothesis_id"]),
            input_axes=tuple(str(x) for x in payload.get("input_axes", [])),
            target_axis=str(payload["target_axis"]),
            residual_mse=fraction_from_json(payload["residual_mse"]),
            max_abs_residual=fraction_from_json(payload["max_abs_residual"]),
            candidate_axes=tuple(FrontierAxisScore.from_json(x) for x in payload.get("candidate_axes", [])),
            status=str(payload.get("status", "UNKNOWN")),
            provenance=tuple(str(x) for x in payload.get("provenance", [])),
        )


@dataclass(frozen=True, slots=True)
class RepresentationProposal:
    proposal_id: str
    action: str
    source_frontier_id: str
    source_axes: tuple[str, ...]
    target_axis: str
    proposed_axis_id: str | None
    semantic_type: str | None
    domain: str | None
    unit: str | None
    score: Fraction
    rationale: str
    status: str = "research_proposal"

    def __post_init__(self) -> None:
        object.__setattr__(self, "score", as_fraction(self.score))
        if self.action not in {"ACTIVATE_EXISTING_AXIS", "REQUIRE_TYPED_CROSS_DOMAIN_BRIDGE", "BIRTH_DIAGNOSTIC_RESIDUAL_AXIS", "NO_ACTION"}:
            raise ValueError("unsupported representation proposal action")
        if self.status not in {"research_proposal", "applied", "rejected", "unknown"}:
            raise ValueError("unsupported representation proposal status")

    def to_json(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "action": self.action,
            "source_frontier_id": self.source_frontier_id,
            "source_axes": list(self.source_axes),
            "target_axis": self.target_axis,
            "proposed_axis_id": self.proposed_axis_id,
            "semantic_type": self.semantic_type,
            "domain": self.domain,
            "unit": self.unit,
            "score": fraction_json(self.score),
            "rationale": self.rationale,
            "status": self.status,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "RepresentationProposal":
        return cls(
            proposal_id=str(payload["proposal_id"]),
            action=str(payload["action"]),
            source_frontier_id=str(payload["source_frontier_id"]),
            source_axes=tuple(str(x) for x in payload.get("source_axes", [])),
            target_axis=str(payload["target_axis"]),
            proposed_axis_id=None if payload.get("proposed_axis_id") is None else str(payload["proposed_axis_id"]),
            semantic_type=None if payload.get("semantic_type") is None else str(payload["semantic_type"]),
            domain=None if payload.get("domain") is None else str(payload["domain"]),
            unit=None if payload.get("unit") is None else str(payload["unit"]),
            score=fraction_from_json(payload["score"]),
            rationale=str(payload.get("rationale", "")),
            status=str(payload.get("status", "research_proposal")),
        )


@dataclass(frozen=True, slots=True)
class DimensionHypothesisProfile:
    """Pre-data mechanism profile whose declared dimensions differ by hypothesis."""

    profile_id: str
    label: str
    overrides: tuple[tuple[str, tuple[str, ...]], ...]
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.profile_id.strip() or not self.label.strip():
            raise ValueError("profile_id and label are required")
        normalized = []
        seen = set()
        for axis_id, dim in self.overrides:
            axis = str(axis_id).strip()
            if not axis or axis in seen:
                raise ValueError("dimension profile axis ids must be unique and nonblank")
            seen.add(axis)
            normalized.append((axis, normalize_dimension(dim)))
        object.__setattr__(self, "overrides", tuple((a, d) for a, d in normalized if d is not None))

    def to_json(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "label": self.label,
            "overrides": [{"axis_id": a, "dimension": list(d)} for a, d in self.overrides],
            "provenance": list(self.provenance),
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "DimensionHypothesisProfile":
        return cls(
            profile_id=str(payload["profile_id"]),
            label=str(payload.get("label", payload["profile_id"])),
            overrides=tuple((str(row["axis_id"]), normalize_dimension(row["dimension"])) for row in payload.get("overrides", ())),
            provenance=tuple(str(x) for x in payload.get("provenance", ())),
        )


@dataclass(frozen=True, slots=True)
class KnownMonomialRelation:
    """Accepted dimensionless monomial relation available to the derivability gate."""

    relation_id: str
    exponents: tuple[tuple[str, int], ...]
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.relation_id.strip():
            raise ValueError("relation_id is required")
        normalized = tuple(sorted((str(a), int(e)) for a, e in self.exponents if int(e)))
        if not normalized:
            raise ValueError("known monomial relation requires nonzero exponents")
        object.__setattr__(self, "exponents", normalized)

    def to_json(self) -> dict[str, Any]:
        return {"relation_id": self.relation_id, "exponents": [[a, e] for a, e in self.exponents], "provenance": list(self.provenance)}

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "KnownMonomialRelation":
        return cls(
            relation_id=str(payload["relation_id"]),
            exponents=tuple((str(a), int(e)) for a, e in payload.get("exponents", ())),
            provenance=tuple(str(x) for x in payload.get("provenance", ())),
        )


@dataclass(frozen=True, slots=True)
class SubspaceCandidate:
    """One research-local axis subset under adaptive exploration.

    A candidate is not a scientific law.  It records an addressable subspace,
    its predictive diagnostics, the branch that produced it and any structural
    gaps that prevent stronger promotion.
    """

    subspace_id: str
    input_axes: tuple[str, ...]
    target_axis: str
    order: int
    domains: tuple[str, ...]
    parent_id: str | None = None
    status: str = "CANDIDATE"
    retention_reason: str = "UNASSESSED"
    baseline_mse: Fraction = Fraction(0)
    cv_mse: Fraction | None = None
    predictive_gain: Fraction = Fraction(0)
    residual_signal: Fraction = Fraction(0)
    experiment_discrimination: Fraction = Fraction(0)
    complexity: int = 0
    sample_count: int = 0
    best_family: str | None = None
    hypothesis_ids: tuple[str, ...] = ()
    route_ids: tuple[str, ...] = ()
    frontier_id: str | None = None
    gap_kind: str | None = None
    methodology_status: str = "UNASSESSED"
    structural_gate: str = "UNASSESSED"
    convention_gate: str = "UNASSESSED"
    derivability_gate: str = "UNASSESSED"
    collapse_gate: str = "UNASSESSED"
    system_coverage_gate: str = "UNASSESSED"
    transition_gate: str = "NOT_ASSESSED_NO_EXPLICIT_TRANSITION_OBSERVABLE"
    regime_gate: str = "UNASSESSED"
    null_gate: str = "UNASSESSED"
    regime_mse: Fraction | None = None
    collapse_score_ppm: int | None = None
    system_count: int | None = None
    null_p: Fraction | None = None
    methodology_receipt_id: str | None = None
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        axes = tuple(dict.fromkeys(str(x) for x in self.input_axes))
        object.__setattr__(self, "input_axes", axes)
        object.__setattr__(self, "domains", tuple(dict.fromkeys(str(x) for x in self.domains)))
        object.__setattr__(self, "baseline_mse", as_fraction(self.baseline_mse))
        if self.cv_mse is not None:
            object.__setattr__(self, "cv_mse", as_fraction(self.cv_mse))
        object.__setattr__(self, "predictive_gain", as_fraction(self.predictive_gain))
        object.__setattr__(self, "residual_signal", as_fraction(self.residual_signal))
        object.__setattr__(self, "experiment_discrimination", as_fraction(self.experiment_discrimination))
        if self.regime_mse is not None:
            object.__setattr__(self, "regime_mse", as_fraction(self.regime_mse))
        if self.null_p is not None:
            object.__setattr__(self, "null_p", as_fraction(self.null_p))
        if self.collapse_score_ppm is not None and self.collapse_score_ppm < 0:
            raise ValueError("collapse_score_ppm cannot be negative")
        if self.system_count is not None and self.system_count < 0:
            raise ValueError("system_count cannot be negative")
        if self.order != len(axes) or self.order < 1:
            raise ValueError("subspace order must equal the number of unique input axes")
        if self.complexity < 0 or self.sample_count < 0:
            raise ValueError("subspace complexity/sample_count cannot be negative")
        if self.status not in {
            "CANDIDATE", "PROMISING", "EXPLORATION", "OPEN_GAP", "UNKNOWN",
            "PRUNED", "EXPANDED", "CLOSED_ON_OBSERVED_DATA",
        }:
            raise ValueError("unsupported subspace candidate status")

    def to_json(self) -> dict[str, Any]:
        return {
            "subspace_id": self.subspace_id,
            "input_axes": list(self.input_axes),
            "target_axis": self.target_axis,
            "order": self.order,
            "domains": list(self.domains),
            "parent_id": self.parent_id,
            "status": self.status,
            "retention_reason": self.retention_reason,
            "baseline_mse": fraction_json(self.baseline_mse),
            "cv_mse": None if self.cv_mse is None else fraction_json(self.cv_mse),
            "predictive_gain": fraction_json(self.predictive_gain),
            "residual_signal": fraction_json(self.residual_signal),
            "experiment_discrimination": fraction_json(self.experiment_discrimination),
            "complexity": self.complexity,
            "sample_count": self.sample_count,
            "best_family": self.best_family,
            "hypothesis_ids": list(self.hypothesis_ids),
            "route_ids": list(self.route_ids),
            "frontier_id": self.frontier_id,
            "gap_kind": self.gap_kind,
            "methodology_status": self.methodology_status,
            "structural_gate": self.structural_gate,
            "convention_gate": self.convention_gate,
            "derivability_gate": self.derivability_gate,
            "collapse_gate": self.collapse_gate,
            "system_coverage_gate": self.system_coverage_gate,
            "transition_gate": self.transition_gate,
            "regime_gate": self.regime_gate,
            "null_gate": self.null_gate,
            "regime_mse": None if self.regime_mse is None else fraction_json(self.regime_mse),
            "collapse_score_ppm": self.collapse_score_ppm,
            "system_count": self.system_count,
            "null_p": None if self.null_p is None else fraction_json(self.null_p),
            "methodology_receipt_id": self.methodology_receipt_id,
            "provenance": list(self.provenance),
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "SubspaceCandidate":
        cv = payload.get("cv_mse")
        return cls(
            subspace_id=str(payload["subspace_id"]),
            input_axes=tuple(str(x) for x in payload.get("input_axes", ())),
            target_axis=str(payload["target_axis"]),
            order=int(payload.get("order", 0)),
            domains=tuple(str(x) for x in payload.get("domains", ())),
            parent_id=None if payload.get("parent_id") is None else str(payload["parent_id"]),
            status=str(payload.get("status", "CANDIDATE")),
            retention_reason=str(payload.get("retention_reason", "UNASSESSED")),
            baseline_mse=fraction_from_json(payload.get("baseline_mse", {"numerator": 0, "denominator": 1})),
            cv_mse=None if cv is None else fraction_from_json(cv),
            predictive_gain=fraction_from_json(payload.get("predictive_gain", {"numerator": 0, "denominator": 1})),
            residual_signal=fraction_from_json(payload.get("residual_signal", {"numerator": 0, "denominator": 1})),
            experiment_discrimination=fraction_from_json(payload.get("experiment_discrimination", {"numerator": 0, "denominator": 1})),
            complexity=int(payload.get("complexity", 0)),
            sample_count=int(payload.get("sample_count", 0)),
            best_family=None if payload.get("best_family") is None else str(payload["best_family"]),
            hypothesis_ids=tuple(str(x) for x in payload.get("hypothesis_ids", ())),
            route_ids=tuple(str(x) for x in payload.get("route_ids", ())),
            frontier_id=None if payload.get("frontier_id") is None else str(payload["frontier_id"]),
            gap_kind=None if payload.get("gap_kind") is None else str(payload["gap_kind"]),
            methodology_status=str(payload.get("methodology_status", "UNASSESSED")),
            structural_gate=str(payload.get("structural_gate", "UNASSESSED")),
            convention_gate=str(payload.get("convention_gate", "UNASSESSED")),
            derivability_gate=str(payload.get("derivability_gate", "UNASSESSED")),
            collapse_gate=str(payload.get("collapse_gate", "UNASSESSED")),
            system_coverage_gate=str(payload.get("system_coverage_gate", "UNASSESSED")),
            transition_gate=str(payload.get("transition_gate", "NOT_ASSESSED_NO_EXPLICIT_TRANSITION_OBSERVABLE")),
            regime_gate=str(payload.get("regime_gate", "UNASSESSED")),
            null_gate=str(payload.get("null_gate", "UNASSESSED")),
            regime_mse=None if payload.get("regime_mse") is None else fraction_from_json(payload["regime_mse"]),
            collapse_score_ppm=None if payload.get("collapse_score_ppm") is None else int(payload["collapse_score_ppm"]),
            system_count=None if payload.get("system_count") is None else int(payload["system_count"]),
            null_p=None if payload.get("null_p") is None else fraction_from_json(payload["null_p"]),
            methodology_receipt_id=None if payload.get("methodology_receipt_id") is None else str(payload["methodology_receipt_id"]),
            provenance=tuple(str(x) for x in payload.get("provenance", ())),
        )


@dataclass(frozen=True, slots=True)
class SubspaceSearchState:
    """Persisted execution state for sparse, open-ended subspace search.

    ``run_order_limit`` and ``expansion_budget`` are execution controls for one
    invocation.  They are deliberately not semantic ceilings of the architecture.
    """

    search_id: str
    target_axis: str
    axis_pool: tuple[str, ...]
    seed_axes: tuple[str, ...]
    min_order: int
    run_order_limit: int | None
    expansion_budget: int
    evaluations_used: int
    max_observed_order: int
    fair_cursor: int
    frontier_ids: tuple[str, ...]
    retained_ids: tuple[str, ...]
    evaluated_ids: tuple[str, ...]
    status: str
    combination_space_by_order: dict[str, int] = field(default_factory=dict)
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.min_order < 1:
            raise ValueError("min_order must be >= 1")
        if self.run_order_limit is not None and self.run_order_limit < self.min_order:
            raise ValueError("run_order_limit cannot be below min_order")
        if self.expansion_budget < 1 or self.evaluations_used < 0:
            raise ValueError("invalid subspace execution budget accounting")
        if self.max_observed_order < 0:
            raise ValueError("max_observed_order cannot be negative")
        if self.status not in {"OPEN", "BUDGET_EXHAUSTED", "ORDER_LIMIT_REACHED", "NO_FRONTIER", "COMPLETE"}:
            raise ValueError("unsupported subspace search status")
        object.__setattr__(self, "axis_pool", tuple(dict.fromkeys(str(x) for x in self.axis_pool)))
        object.__setattr__(self, "seed_axes", tuple(dict.fromkeys(str(x) for x in self.seed_axes)))
        object.__setattr__(self, "frontier_ids", tuple(dict.fromkeys(str(x) for x in self.frontier_ids)))
        object.__setattr__(self, "retained_ids", tuple(dict.fromkeys(str(x) for x in self.retained_ids)))
        object.__setattr__(self, "evaluated_ids", tuple(dict.fromkeys(str(x) for x in self.evaluated_ids)))
        object.__setattr__(self, "combination_space_by_order", {str(k): int(v) for k, v in self.combination_space_by_order.items()})

    def to_json(self) -> dict[str, Any]:
        return {
            "search_id": self.search_id,
            "target_axis": self.target_axis,
            "axis_pool": list(self.axis_pool),
            "seed_axes": list(self.seed_axes),
            "min_order": self.min_order,
            "run_order_limit": self.run_order_limit,
            "expansion_budget": self.expansion_budget,
            "evaluations_used": self.evaluations_used,
            "max_observed_order": self.max_observed_order,
            "fair_cursor": self.fair_cursor,
            "frontier_ids": list(self.frontier_ids),
            "retained_ids": list(self.retained_ids),
            "evaluated_ids": list(self.evaluated_ids),
            "status": self.status,
            "combination_space_by_order": dict(sorted(self.combination_space_by_order.items(), key=lambda kv: int(kv[0]))),
            "provenance": list(self.provenance),
            "architecture_order_ceiling": None,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "SubspaceSearchState":
        return cls(
            search_id=str(payload["search_id"]),
            target_axis=str(payload["target_axis"]),
            axis_pool=tuple(str(x) for x in payload.get("axis_pool", ())),
            seed_axes=tuple(str(x) for x in payload.get("seed_axes", ())),
            min_order=int(payload.get("min_order", 2)),
            run_order_limit=None if payload.get("run_order_limit") is None else int(payload["run_order_limit"]),
            expansion_budget=int(payload.get("expansion_budget", 1)),
            evaluations_used=int(payload.get("evaluations_used", 0)),
            max_observed_order=int(payload.get("max_observed_order", 0)),
            fair_cursor=int(payload.get("fair_cursor", 0)),
            frontier_ids=tuple(str(x) for x in payload.get("frontier_ids", ())),
            retained_ids=tuple(str(x) for x in payload.get("retained_ids", ())),
            evaluated_ids=tuple(str(x) for x in payload.get("evaluated_ids", ())),
            status=str(payload.get("status", "OPEN")),
            combination_space_by_order={str(k): int(v) for k, v in payload.get("combination_space_by_order", {}).items()},
            provenance=tuple(str(x) for x in payload.get("provenance", ())),
        )


@dataclass(frozen=True, slots=True)
class AxisSymbolBinding:
    binding_id: str
    axis_id: str
    owner_id: str
    domain: str
    symbol_id: str
    display: str
    quantity_id: str
    unit: str
    dimension: tuple[str, ...]
    status: str = "EXACT_TYPED"

    def __post_init__(self) -> None:
        object.__setattr__(self, "dimension", normalize_dimension(self.dimension))
        if self.status not in {"EXACT_TYPED", "UNKNOWN", "BLOCKED"}:
            raise ValueError("unsupported binding status")
        for name in ("binding_id", "axis_id", "owner_id", "domain", "symbol_id", "display", "quantity_id", "unit"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} is required")

    def to_json(self) -> dict[str, Any]:
        return {
            "binding_id": self.binding_id,
            "axis_id": self.axis_id,
            "owner_id": self.owner_id,
            "domain": self.domain,
            "symbol_id": self.symbol_id,
            "display": self.display,
            "quantity_id": self.quantity_id,
            "unit": self.unit,
            "dimension": list(self.dimension),
            "status": self.status,
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "AxisSymbolBinding":
        return cls(
            binding_id=str(payload["binding_id"]), axis_id=str(payload["axis_id"]),
            owner_id=str(payload["owner_id"]), domain=str(payload["domain"]),
            symbol_id=str(payload["symbol_id"]), display=str(payload["display"]),
            quantity_id=str(payload["quantity_id"]), unit=str(payload["unit"]),
            dimension=normalize_dimension(payload["dimension"]) or (), status=str(payload.get("status", "EXACT_TYPED")),
        )


@dataclass(frozen=True, slots=True)
class HypergraphRoute:
    route_id: str
    input_axes: tuple[str, ...]
    target_axis: str
    source_owner_ids: tuple[str, ...]
    target_owner_id: str
    bridge_id: str
    bindings: tuple[AxisSymbolBinding, ...]
    dimensional_status: str
    lowering_status: str
    path_cost: int
    expected_discrimination: Fraction = Fraction(0)
    route_utility: Fraction = Fraction(0)
    experiment_id: str | None = None
    hypothesis_ids: tuple[str, ...] = ()
    residual_mse: Fraction | None = None
    status: str = "STRUCTURAL_CANDIDATE"
    provenance: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "expected_discrimination", as_fraction(self.expected_discrimination))
        object.__setattr__(self, "route_utility", as_fraction(self.route_utility))
        if self.residual_mse is not None:
            object.__setattr__(self, "residual_mse", as_fraction(self.residual_mse))
        if self.path_cost < 0:
            raise ValueError("path_cost cannot be negative")
        if self.dimensional_status not in {"PASS", "UNKNOWN", "FAIL"}:
            raise ValueError("unsupported dimensional status")
        if self.lowering_status not in {"PASS", "UNKNOWN", "FAIL"}:
            raise ValueError("unsupported lowering status")
        if self.status not in {"STRUCTURAL_CANDIDATE", "PREDICTIVE_CANDIDATE", "SELECTED", "BLOCKED", "UNKNOWN"}:
            raise ValueError("unsupported hypergraph route status")

    def to_json(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id, "input_axes": list(self.input_axes), "target_axis": self.target_axis,
            "source_owner_ids": list(self.source_owner_ids), "target_owner_id": self.target_owner_id,
            "bridge_id": self.bridge_id, "bindings": [b.to_json() for b in self.bindings],
            "dimensional_status": self.dimensional_status, "lowering_status": self.lowering_status,
            "path_cost": self.path_cost, "expected_discrimination": fraction_json(self.expected_discrimination),
            "route_utility": fraction_json(self.route_utility), "experiment_id": self.experiment_id,
            "hypothesis_ids": list(self.hypothesis_ids),
            "residual_mse": None if self.residual_mse is None else fraction_json(self.residual_mse),
            "status": self.status, "provenance": list(self.provenance),
        }

    @classmethod
    def from_json(cls, payload: Mapping[str, Any]) -> "HypergraphRoute":
        rmse = payload.get("residual_mse")
        return cls(
            route_id=str(payload["route_id"]), input_axes=tuple(str(x) for x in payload.get("input_axes", ())),
            target_axis=str(payload["target_axis"]), source_owner_ids=tuple(str(x) for x in payload.get("source_owner_ids", ())),
            target_owner_id=str(payload["target_owner_id"]), bridge_id=str(payload["bridge_id"]),
            bindings=tuple(AxisSymbolBinding.from_json(x) for x in payload.get("bindings", ())),
            dimensional_status=str(payload.get("dimensional_status", "UNKNOWN")), lowering_status=str(payload.get("lowering_status", "UNKNOWN")),
            path_cost=int(payload.get("path_cost", 0)), expected_discrimination=fraction_from_json(payload.get("expected_discrimination", {"numerator":0,"denominator":1})),
            route_utility=fraction_from_json(payload.get("route_utility", {"numerator":0,"denominator":1})),
            experiment_id=None if payload.get("experiment_id") is None else str(payload["experiment_id"]),
            hypothesis_ids=tuple(str(x) for x in payload.get("hypothesis_ids", ())),
            residual_mse=None if rmse is None else fraction_from_json(rmse), status=str(payload.get("status", "STRUCTURAL_CANDIDATE")),
            provenance=tuple(str(x) for x in payload.get("provenance", ())),
        )
