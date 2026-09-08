"""Canonical scientific schema for the Φ-Compiler law-space federation.

Typed Python objects in this module are the authoritative representation.
Human-readable LaTeX, JSON and HTML are projections of these objects, not
parallel owners of scientific meaning.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import re

try:
    import numpy as np
except ImportError:  # law-space schema itself remains importable without NumPy
    np = None

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

LAWSPACE_SCHEMA = "phi-lawspace/v6.1-science-atlas-core"
OWNER_VERSION = "6.1.0"


def _json_default(obj: Any) -> Any:
    if np is not None and isinstance(obj, np.generic):
        return obj.item()
    if np is not None and isinstance(obj, np.ndarray):
        if np.iscomplexobj(obj):
            return [[{"real": float(v.real), "imag": float(v.imag)} for v in row] for row in obj] if obj.ndim > 1 else [{"real": float(v.real), "imag": float(v.imag)} for v in obj]
        return obj.tolist()
    if isinstance(obj, complex):
        return {"real": float(obj.real), "imag": float(obj.imag)}
    if isinstance(obj, Enum):
        return obj.value
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    if isinstance(obj, tuple):
        return list(obj)
    raise TypeError(type(obj).__name__)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=_json_default)


def digest_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class AxisValueKind(str, Enum):
    ENUM = "ENUM"
    HIERARCHICAL_ENUM = "HIERARCHICAL_ENUM"
    MULTI_ENUM = "MULTI_ENUM"
    BOOLEAN = "BOOLEAN"
    INTEGER = "INTEGER"
    RATIONAL = "RATIONAL"
    CONTINUOUS_RANGE = "CONTINUOUS_RANGE"
    DIMENSION_VECTOR = "DIMENSION_VECTOR"
    SYMBOLIC_EXPRESSION = "SYMBOLIC_EXPRESSION"
    ONTOLOGY_REFERENCE = "ONTOLOGY_REFERENCE"
    GRAPH_REFERENCE = "GRAPH_REFERENCE"
    DISTRIBUTION = "DISTRIBUTION"
    TEXT = "TEXT"


class EpistemicState(str, Enum):
    ESTABLISHED = "ESTABLISHED_LAW"
    THEORETICAL = "THEORETICAL"
    EMPIRICAL = "EXPERIMENTALLY_CONFIRMED"
    PHENOMENOLOGICAL = "PHENOMENOLOGICAL"
    HYPOTHESIS = "HYPOTHESIS"
    DERIVED_COMPOSITE = "DERIVED_COMPOSITE_MODEL"
    PENDING_PROPOSAL = "PENDING_PROPOSAL"
    PENDING_BRIDGE = "PENDING_BRIDGE"
    PENDING_NORMALIZATION = "PENDING_NORMALIZATION"
    PENDING_CELL_ASSIGNMENT = "PENDING_CELL_ASSIGNMENT"
    REJECTED = "REJECTED"


class ScientificObjectClass(str, Enum):
    SCIENTIFIC_QUANTITY = "SCIENTIFIC_QUANTITY"
    STATE = "STATE"
    OBSERVABLE = "OBSERVABLE"
    PARAMETER = "PARAMETER"
    CONSTANT = "CONSTANT"
    RATE_OR_FLOW = "RATE_OR_FLOW"
    INPUT_PORT = "INPUT_PORT"
    OUTPUT_PORT = "OUTPUT_PORT"
    OPERATOR = "OPERATOR"
    LATENT_OBJECT = "LATENT_OBJECT"
    DIMENSIONLESS_OBSERVABLE = "DIMENSIONLESS_OBSERVABLE"


class ScientificSymbolRole(str, Enum):
    STATE = "STATE"
    OBSERVABLE = "OBSERVABLE"
    PARAMETER = "PARAMETER"
    CONSTANT = "CONSTANT"
    RATE_OR_FLOW = "RATE_OR_FLOW"
    INPUT = "INPUT"
    OUTPUT = "OUTPUT"
    OPERATOR = "OPERATOR"
    LATENT = "LATENT"
    SCIENTIFIC_QUANTITY = "SCIENTIFIC_QUANTITY"
    LEGACY_UNTYPED = "LEGACY_UNTYPED"


class ScienceAtlasDefectClass(str, Enum):
    CLOSURE_HOLE = "CLOSURE_HOLE"
    OPERATOR_HOLE = "OPERATOR_HOLE"
    BOUNDARY_GAUGE_GAP = "BOUNDARY_GAUGE_GAP"
    BRIDGE_HOLE = "BRIDGE_HOLE"
    SEMANTIC_META_AXIS_GAP = "SEMANTIC_META_AXIS_GAP"
    OBJECT_ONTOLOGY_HOLE = "OBJECT_ONTOLOGY_HOLE"
    AXIS_GENESIS_CANDIDATE = "AXIS_GENESIS_CANDIDATE"
    OBSERVER_GAP = "OBSERVER_GAP"
    IDENTIFIABILITY_GAP = "IDENTIFIABILITY_GAP"
    FRONTIER_DEFECT = "FRONTIER_DEFECT"


class EpistemicKnowledgeKind(str, Enum):
    FACT = "FACT"
    EMPIRICAL_RELATION = "EMPIRICAL_RELATION"
    MODEL = "MODEL"
    THEOREM = "THEOREM"
    STRUCTURAL_ANALOGY = "STRUCTURAL_ANALOGY"
    TYPED_BRIDGE = "TYPED_BRIDGE"
    ACTIVE_HYPOTHESIS = "ACTIVE_HYPOTHESIS"
    RADICAL_HYPOTHESIS = "RADICAL_HYPOTHESIS"
    SPECULATION = "SPECULATION"
    UNRESOLVED_DEFECT = "UNRESOLVED_DEFECT"
    IDENTIFIABILITY_GAP = "IDENTIFIABILITY_GAP"
    CANDIDATE_LAW = "CANDIDATE_LAW"
    FALSIFIED = "FALSIFIED"


@dataclass(frozen=True)
class DimensionVector:
    """Seven-base-dimension SI exponent vector (L, M, T, I, Θ, N, J)."""

    length: str = "0"
    mass: str = "0"
    time: str = "0"
    current: str = "0"
    temperature: str = "0"
    amount: str = "0"
    luminous_intensity: str = "0"

    def as_tuple(self) -> Tuple[str, ...]:
        return (
            self.length,
            self.mass,
            self.time,
            self.current,
            self.temperature,
            self.amount,
            self.luminous_intensity,
        )


@dataclass(frozen=True)
class ContinuousRange:
    minimum: float | None
    maximum: float | None
    unit: str | None = None
    minimum_inclusive: bool = True
    maximum_inclusive: bool = True

    def validate(self) -> None:
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("continuous range minimum exceeds maximum")


@dataclass(frozen=True)
class AxisDefinition:
    axis_id: str
    domain: str
    description_ru: str
    value_kind: AxisValueKind = AxisValueKind.TEXT
    allowed_values: Tuple[str, ...] = ()
    required_for: Tuple[str, ...] = ()
    forbidden_for: Tuple[str, ...] = ()
    provenance: str = "PDF_TASK_V2_6"

    def validate_value(self, value: Any) -> None:
        if self.value_kind in {AxisValueKind.ENUM, AxisValueKind.HIERARCHICAL_ENUM} and self.allowed_values:
            if str(value) not in self.allowed_values:
                raise ValueError(f"{self.axis_id}: unsupported value {value!r}")
        if self.value_kind == AxisValueKind.MULTI_ENUM and self.allowed_values:
            values = value if isinstance(value, (list, tuple, set)) else (value,)
            invalid = [str(v) for v in values if str(v) not in self.allowed_values]
            if invalid:
                raise ValueError(f"{self.axis_id}: unsupported values {invalid!r}")
        if self.value_kind == AxisValueKind.CONTINUOUS_RANGE:
            if isinstance(value, Mapping):
                ContinuousRange(**value).validate()
            elif isinstance(value, ContinuousRange):
                value.validate()
            else:
                raise TypeError(f"{self.axis_id}: expected ContinuousRange or mapping")


@dataclass(frozen=True)
class AxisProfile:
    entity_kind: str
    applicable_axes: Tuple[str, ...]
    required_axes: Tuple[str, ...] = ()
    forbidden_axes: Tuple[str, ...] = ()


@dataclass(frozen=True)
class AxisConstraint:
    constraint_id: str
    description_ru: str
    expression: str


@dataclass(frozen=True)
class DomainAxisRegistry:
    domain_id: str
    schema_version: str
    description_ru: str
    axes: Mapping[str, AxisDefinition]
    entity_profiles: Mapping[str, AxisProfile] = field(default_factory=dict)
    constraints: Tuple[AxisConstraint, ...] = ()
    domain_role: str = "natural_science"

    @property
    def axis_count(self) -> int:
        return len(self.axes)

    @property
    def digest(self) -> str:
        return digest_payload(dataclasses.asdict(self))

    def validate_coordinate(self, coordinates: Mapping[str, Any], entity_kind: str | None = None) -> None:
        unknown = sorted(set(coordinates) - set(self.axes))
        if unknown:
            raise ValueError(f"{self.domain_id}: unregistered axes {unknown}")
        for axis_id, value in coordinates.items():
            self.axes[axis_id].validate_value(value)
        if entity_kind and entity_kind in self.entity_profiles:
            profile = self.entity_profiles[entity_kind]
            missing = sorted(set(profile.required_axes) - set(coordinates))
            forbidden = sorted(set(profile.forbidden_axes) & set(coordinates))
            inapplicable = sorted(set(coordinates) - set(profile.applicable_axes))
            if missing:
                raise ValueError(f"{entity_kind}: missing required axes {missing}")
            if forbidden:
                raise ValueError(f"{entity_kind}: forbidden axes present {forbidden}")
            if inapplicable:
                raise ValueError(f"{entity_kind}: inapplicable axes present {inapplicable}")


_TOKEN_RE = re.compile(
    r"\\[A-Za-z]+|[A-Za-z_][A-Za-z0-9_]*|[Α-Ωα-ωϑϕϖℏ∞∂∇]+|"
    r"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|<=|>=|!=|:=|->|→|↔|"
    r"[+\-*/^_=<>±×·:,;|&]|[()\[\]{}]|\S"
)


@dataclass(frozen=True)
class ASTNode:
    kind: str
    value: str = ""
    children: Tuple["ASTNode", ...] = ()


@dataclass(frozen=True)
class OperatorScopeIR:
    """Semantic scope of an operator, not merely its printed symbols.

    D: domain, C: codomain, mu: measure, dagger: adjoint/boundary
    structure, tau: topology used for limiting operations.
    """

    domain_definition: str = "UNRESOLVED_DOMAIN"
    codomain_definition: str = "UNRESOLVED_CODOMAIN"
    measure: str = "UNRESOLVED_MEASURE"
    adjoint_structure: str = "UNRESOLVED_ADJOINT"
    limit_topology: str = "UNRESOLVED_LIMIT_TOPOLOGY"
    status: str = "STRUCTURAL_SCOPE_ONLY"
    assumptions: Tuple[str, ...] = ()
    digest: str = ""

    def finalized(self) -> "OperatorScopeIR":
        payload = dataclasses.asdict(self)
        payload["digest"] = ""
        return dataclasses.replace(self, digest=digest_payload(payload))

    @classmethod
    def for_expression(cls, expression_kind: str) -> "OperatorScopeIR":
        return cls(
            domain_definition=f"typed arguments admitted by expression_kind={expression_kind}",
            codomain_definition=f"typed result admitted by expression_kind={expression_kind}",
            measure="NOT_APPLICABLE_OR_NOT_YET_LOWERED",
            adjoint_structure="NOT_APPLICABLE_OR_NOT_YET_LOWERED",
            limit_topology="NOT_APPLICABLE_OR_NOT_YET_LOWERED",
            status="STRUCTURAL_SCOPE_ONLY",
        ).finalized()


@dataclass(frozen=True)
class SharedBinding:
    binding_id: str
    occurrences: Tuple[str, ...]
    relation: str = "IDENTICAL_VARIABLE"
    status: str = "DECLARED"


@dataclass(frozen=True)
class SharedBindingGraph:
    """Graph of symbol/index occurrences that must denote one shared variable."""

    nodes: Tuple[str, ...] = ()
    bindings: Tuple[SharedBinding, ...] = ()
    free_indices: Tuple[str, ...] = ()
    bound_indices: Tuple[str, ...] = ()
    status: str = "NO_CROSS_EXPRESSION_BINDINGS_DECLARED"
    digest: str = ""

    def validate(self) -> None:
        node_set = set(self.nodes)
        seen_ids: set[str] = set()
        for binding in self.bindings:
            if not binding.binding_id or binding.binding_id in seen_ids:
                raise ValueError("SharedBindingGraph requires unique non-empty binding IDs")
            seen_ids.add(binding.binding_id)
            if len(binding.occurrences) < 2:
                raise ValueError(f"binding {binding.binding_id} must join at least two occurrences")
            if not set(binding.occurrences).issubset(node_set):
                raise ValueError(f"binding {binding.binding_id} references undeclared nodes")
        if set(self.free_indices) & set(self.bound_indices):
            raise ValueError("an index cannot be simultaneously free and bound")

    def finalized(self) -> "SharedBindingGraph":
        self.validate()
        payload = dataclasses.asdict(self)
        payload["digest"] = ""
        return dataclasses.replace(self, digest=digest_payload(payload))

    def has_shared_occurrences(self, *occurrences: str) -> bool:
        requested = set(occurrences)
        return any(requested.issubset(set(binding.occurrences)) for binding in self.bindings)

    @classmethod
    def structural(cls, symbols: Sequence[str]) -> "SharedBindingGraph":
        return cls(nodes=tuple(sorted(set(symbols)))).finalized()


@dataclass(frozen=True)
class DistributionWavefrontIR:
    """Distributional type and microlocal admissibility contract."""

    distribution_space: str = "NOT_DISTRIBUTIONAL_OR_NOT_DECLARED"
    wavefront_description: str = "NOT_COMPUTED"
    operations: Tuple[str, ...] = ()
    pullback_map: str = "NOT_APPLICABLE"
    pushforward_map: str = "NOT_APPLICABLE"
    tensor_product_status: str = "NOT_APPLICABLE"
    product_condition: str = "NOT_APPLICABLE"
    product_status: str = "NOT_APPLICABLE"
    status: str = "STRUCTURAL_ONLY"
    digest: str = ""

    def finalized(self) -> "DistributionWavefrontIR":
        payload = dataclasses.asdict(self)
        payload["digest"] = ""
        return dataclasses.replace(self, digest=digest_payload(payload))

    @staticmethod
    def hormander_product_allowed(
        left_covectors: Sequence[Tuple[float, ...]],
        right_covectors: Sequence[Tuple[float, ...]],
        *,
        tolerance: float = 1e-12,
    ) -> bool:
        """Finite certificate for the no-opposite-covectors sufficient condition.

        This checks supplied covector samples only. It is not a proof that a full
        analytic wavefront set has been exhaustively computed.
        """
        for left in left_covectors:
            for right in right_covectors:
                if len(left) != len(right):
                    raise ValueError("wavefront covectors must have equal dimension")
                if all(abs(float(a) + float(b)) <= tolerance for a, b in zip(left, right)):
                    return False
        return True

    @classmethod
    def structural(cls, expression_kind: str) -> "DistributionWavefrontIR":
        return cls(
            distribution_space=f"not lowered from expression_kind={expression_kind}",
            status="STRUCTURAL_ONLY",
        ).finalized()


@dataclass(frozen=True)
class ProofObligationNode:
    node_id: str
    description_ru: str
    depends_on: Tuple[str, ...] = ()
    status: str = "OPEN"
    evidence_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ProofObligationGraph:
    graph_id: str
    nodes: Tuple[ProofObligationNode, ...]
    status: str = "OPEN"
    digest: str = ""

    def validate(self) -> None:
        ids = [node.node_id for node in self.nodes]
        if len(ids) != len(set(ids)) or not ids:
            raise ValueError("ProofObligationGraph requires unique non-empty nodes")
        known = set(ids)
        if any(dep not in known for node in self.nodes for dep in node.depends_on):
            raise ValueError("proof obligation references an unknown dependency")
        graph = {node.node_id: set(node.depends_on) for node in self.nodes}
        temporary: set[str] = set()
        permanent: set[str] = set()
        def visit(node_id: str) -> None:
            if node_id in permanent:
                return
            if node_id in temporary:
                raise ValueError("ProofObligationGraph contains a cycle")
            temporary.add(node_id)
            for dep in graph[node_id]:
                visit(dep)
            temporary.remove(node_id)
            permanent.add(node_id)
        for node_id in ids:
            visit(node_id)

    def finalized(self) -> "ProofObligationGraph":
        self.validate()
        payload = dataclasses.asdict(self)
        payload["digest"] = ""
        return dataclasses.replace(self, digest=digest_payload(payload))


@dataclass(frozen=True)
class LimitPath:
    path_id: str
    regulator_order: Tuple[str, ...]
    schedule: str
    endpoint: str
    status: str = "NOT_RUN"


@dataclass(frozen=True)
class LimitProtocol:
    protocol_id: str
    regulators: Tuple[str, ...]
    cofinal_paths: Tuple[LimitPath, ...]
    tail_estimate_status: str
    path_independence_status: str
    precision_switch_policy: str
    claim_scope: str
    status: str = "OPEN"
    digest: str = ""

    def validate(self) -> None:
        path_ids = [path.path_id for path in self.cofinal_paths]
        if len(path_ids) != len(set(path_ids)) or not path_ids:
            raise ValueError("LimitProtocol requires unique non-empty cofinal paths")
        if self.claim_scope == "REGULATOR_INDEPENDENT_LIMIT" and len(self.cofinal_paths) < 2:
            raise ValueError("regulator-independent claims require multiple cofinal paths")
        regulator_set = set(self.regulators)
        for path in self.cofinal_paths:
            if not set(path.regulator_order).issubset(regulator_set):
                raise ValueError(f"limit path {path.path_id} uses an unregistered regulator")

    def finalized(self) -> "LimitProtocol":
        self.validate()
        payload = dataclasses.asdict(self)
        payload["digest"] = ""
        return dataclasses.replace(self, digest=digest_payload(payload))


@dataclass(frozen=True)
class PrimarySourceEntry:
    source_id: str
    identifier_type: str
    identifier: str
    version: str
    snapshot_date: str
    formula_signature: str
    claim_scope: str


@dataclass(frozen=True)
class PrimarySourceLedger:
    ledger_id: str
    entries: Tuple[PrimarySourceEntry, ...]
    external_novelty_status: str = "NOT_SEARCHED"
    status: str = "PARTIAL"
    digest: str = ""

    def validate(self) -> None:
        ids = [entry.source_id for entry in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("PrimarySourceLedger source IDs must be unique")
        for entry in self.entries:
            if not all((entry.source_id, entry.identifier_type, entry.identifier, entry.version, entry.snapshot_date, entry.formula_signature)):
                raise ValueError("primary source entries require identifier, version, snapshot and formula signature")

    def finalized(self) -> "PrimarySourceLedger":
        self.validate()
        payload = dataclasses.asdict(self)
        payload["digest"] = ""
        return dataclasses.replace(self, digest=digest_payload(payload))


@dataclass(frozen=True)
class ExpressionIR:
    """Typed expression with explicit operator, binding and distributional scope."""

    source: str
    canonical: str
    expression_kind: str
    ast: ASTNode
    symbols: Tuple[str, ...]
    operator_scope: OperatorScopeIR = field(default_factory=lambda: OperatorScopeIR.for_expression("symbolic_expression"))
    binding_graph: SharedBindingGraph = field(default_factory=lambda: SharedBindingGraph.structural(()))
    distribution_wavefront: DistributionWavefrontIR = field(default_factory=lambda: DistributionWavefrontIR.structural("symbolic_expression"))
    semantic_level: str = "STRUCTURAL_TYPED_AST_WITH_FORMAL_SCOPE"
    parse_status: str = "PASS"
    digest: str = ""

    @staticmethod
    def _leaf(token: str) -> ASTNode:
        if token.startswith("\\"):
            kind = "COMMAND"
        elif re.fullmatch(r"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", token):
            kind = "NUMBER"
        elif re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*|[Α-Ωα-ωϑϕϖℏ∞∂∇]+", token):
            kind = "SYMBOL"
        elif token in {"+", "-", "*", "/", "^", "_", "=", "<", ">", "±", "×", "·", ":", ",", ";", "|", "&", "<=", ">=", "!=", ":=", "->", "→", "↔"}:
            kind = "OPERATOR"
        else:
            kind = "TEXT"
        return ASTNode(kind=kind, value=token)

    @classmethod
    def from_source(
        cls,
        source: str,
        expression_kind: str = "symbolic_expression",
        *,
        operator_scope: OperatorScopeIR | None = None,
        binding_graph: SharedBindingGraph | None = None,
        distribution_wavefront: DistributionWavefrontIR | None = None,
    ) -> "ExpressionIR":
        raw = str(source or "").strip()
        if not raw:
            raise ValueError("formula source is empty")
        tokens = _TOKEN_RE.findall(raw)
        if not tokens:
            raise ValueError("formula contains no tokens")
        pairs = {"(": ")", "[": "]", "{": "}"}
        closers = {v: k for k, v in pairs.items()}
        stack: List[Tuple[str, List[ASTNode]]] = [("ROOT", [])]
        for token in tokens:
            if token in pairs:
                stack.append((token, []))
            elif token in closers:
                if len(stack) == 1 or stack[-1][0] != closers[token]:
                    raise ValueError(f"unbalanced delimiter {token!r}")
                opener, children = stack.pop()
                stack[-1][1].append(ASTNode(kind="GROUP", value=opener + token, children=tuple(children)))
            else:
                stack[-1][1].append(cls._leaf(token))
        if len(stack) != 1:
            raise ValueError(f"unclosed delimiter {stack[-1][0]!r}")
        canonical = " ".join(tokens)
        ast = ASTNode(kind="ROOT", children=tuple(stack[0][1]))
        symbol_values = sorted({
            n.value for n in _walk_nodes(ast) if n.kind in {"SYMBOL", "COMMAND"}
        })
        scope = (operator_scope or OperatorScopeIR.for_expression(expression_kind))
        bindings = (binding_graph or SharedBindingGraph.structural(symbol_values))
        distribution = (distribution_wavefront or DistributionWavefrontIR.structural(expression_kind))
        # Re-finalize supplied nested contracts if callers omitted their digests.
        if not scope.digest:
            scope = scope.finalized()
        if not bindings.digest:
            bindings = bindings.finalized()
        if not distribution.digest:
            distribution = distribution.finalized()
        temp = cls(
            source=raw,
            canonical=canonical,
            expression_kind=expression_kind,
            ast=ast,
            symbols=tuple(symbol_values),
            operator_scope=scope,
            binding_graph=bindings,
            distribution_wavefront=distribution,
        )
        object.__setattr__(temp, "digest", digest_payload({k: v for k, v in dataclasses.asdict(temp).items() if k != "digest"}))
        return temp


def _walk_nodes(node: ASTNode) -> Iterable[ASTNode]:
    yield node
    for child in node.children:
        yield from _walk_nodes(child)


@dataclass(frozen=True)
class SymbolRecord:
    symbol_id: str
    display: str
    role: str
    quantity_id: str | None = None
    unit: str | None = None
    dimension: DimensionVector | None = None
    meaning_ru: str = ""
    provenance: str = ""


@dataclass(frozen=True)
class QuantityRecord:
    quantity_id: str
    name_ru: str
    dimension: DimensionVector
    canonical_unit: str
    ontology_reference: str | None = None


@dataclass(frozen=True)
class ParameterRecord:
    parameter_id: str
    name_ru: str
    symbol: str
    dimension: DimensionVector
    canonical_unit: str = "1"
    parameter_class: str = "MODEL_PARAMETER"
    domain_scope: Tuple[str, ...] = ()
    operational_definition: str = ""
    provenance: str = ""


@dataclass(frozen=True)
class EpistemicCertificate:
    certificate_id: str
    knowledge_kind: str
    proof_grade: str
    evidence_grade: str
    provenance_grade: str
    novelty_grade: str
    identifiability_grade: str
    prediction_grade: str = "NOT_EVALUATED"
    claim_boundary: Mapping[str, Any] = field(default_factory=dict)
    evidence_digests: Tuple[str, ...] = ()
    digest: str = ""

    def finalized(self) -> "EpistemicCertificate":
        payload = dataclasses.asdict(self)
        payload["digest"] = ""
        return dataclasses.replace(self, digest=digest_payload(payload))


@dataclass(frozen=True)
class FrontierDefectRecord:
    defect_id: str
    defect_class: str
    chart_ids: Tuple[str, ...]
    unresolved_relation: str
    constraints: Tuple[str, ...] = ()
    residuals: Tuple[str, ...] = ()
    admitted_operator_closure_status: str = "NOT_EVALUATED"
    bridge_support: Tuple[str, ...] = ()
    validity_conditions: Tuple[str, ...] = ()
    prior_art_status: str = "NOT_SCREENED"
    identifiability_status: str = "NOT_EVALUATED"
    evidence_status: str = "UNRESOLVED"
    information_gain_score: float | None = None
    claim_boundary: Mapping[str, Any] = field(default_factory=dict)
    digest: str = ""

    def finalized(self) -> "FrontierDefectRecord":
        payload = dataclasses.asdict(self)
        payload["digest"] = ""
        return dataclasses.replace(self, digest=digest_payload(payload))


@dataclass(frozen=True)
class AtlasSnapshotRecord:
    snapshot_id: str
    object_registry_digest: str
    law_registry_digest: str
    operator_registry_digest: str
    chart_registry_digest: str
    bridge_registry_digest: str
    axis_registry_digest: str
    defect_registry_digest: str
    observer_registry_digest: str
    evidence_registry_digest: str
    prospective_freeze_digest: str = ""
    replay_contract: str = "EXACT_DIGEST_BOUND_REPLAY"
    digest: str = ""

    def finalized(self) -> "AtlasSnapshotRecord":
        payload = dataclasses.asdict(self)
        payload["digest"] = ""
        return dataclasses.replace(self, digest=digest_payload(payload))


@dataclass(frozen=True)
class ConstantRecord:
    constant_id: str
    symbol: str
    name_ru: str
    value: str
    unit: str
    dimension: DimensionVector
    value_type: str
    constant_class: str
    standard_uncertainty: str | None
    covariance_group: str | None
    edition: str
    valid_from: str | None
    source_id: str
    source_digest: str
    derivation_expression: str | None = None
    depends_on: Tuple[str, ...] = ()
    independence_status: str = "INDEPENDENT_MEASURED_OR_DEFINED"
    scope: str = "UNIVERSAL"
    fit_status: str = "NOT_A_FIT_PARAMETER"


@dataclass(frozen=True)
class MeasurementRecord:
    measurement_id: str
    observable_id: str
    value: str
    unit: str
    uncertainty_id: str | None
    method: str
    conditions: Mapping[str, Any]
    source_id: str


@dataclass(frozen=True)
class UncertaintyRecord:
    uncertainty_id: str
    model: str
    standard_uncertainty: str | None
    covariance_group: str | None
    confidence_level: float | None = None


@dataclass(frozen=True)
class SourceManifest:
    source_id: str
    title: str
    source_type: str
    edition: str
    location: str
    sha256: str
    declared_records: Mapping[str, int]
    processed_records: Mapping[str, int]
    source_families: Tuple[Mapping[str, str], ...] = ()
    record_level_bibliography: str = ""
    claim_boundary: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    owner_id: str
    evidence_type: str
    claim_level: str
    source_ids: Tuple[str, ...]
    validity_domain: str
    falsification_criterion: str
    status: str
    digest: str = ""


@dataclass(frozen=True)
class ProjectionRecord:
    projection_id: str
    source_owner_id: str
    target_cell_id: str
    transformation: ExpressionIR
    assumptions: Tuple[str, ...] = ()


@dataclass(frozen=True)
class CellOccupancy:
    cell_id: str
    domain_id: str
    coordinates: Mapping[str, Any]
    occupant_owner_ids: Tuple[str, ...]
    schema_digest: str


@dataclass(frozen=True)
class DomainBridge:
    bridge_id: str
    source_domains: Tuple[str, ...]
    input_entity_types: Tuple[str, ...]
    output_entity_type: str
    mapping_rules: Tuple[str, ...]
    dimensional_contract: str
    assumptions: Tuple[str, ...]
    validity_conditions: Tuple[str, ...]
    composition_ast: ExpressionIR
    controlled_limits: Tuple[str, ...]
    status: str = "ACTIVE"


@dataclass(frozen=True)
class CrossDomainComposition:
    composition_id: str
    input_owner_ids: Tuple[str, ...]
    bridge_ids: Tuple[str, ...]
    result_formula: ExpressionIR
    assumptions: Tuple[str, ...]
    validation_status: str


@dataclass(frozen=True)
class LawPassport:
    owner_id: str
    name_ru: str
    domain_id: str
    entity_kind: str
    formula: ExpressionIR
    scientific_coordinate: Mapping[str, Any]
    quantity_semantics: Mapping[str, Any]
    epistemic_state: str
    provenance: Mapping[str, Any]
    home_cell_id: str
    symbols: Tuple[SymbolRecord, ...] = ()
    constants: Tuple[str, ...] = ()
    assumptions: Tuple[str, ...] = ()
    validity_domain: str = ""
    controlled_limits: Tuple[str, ...] = ()
    observables: Tuple[str, ...] = ()
    uncertainty_model: str = "NOT_DECLARED"
    projection_ids: Tuple[str, ...] = ()
    digest: str = ""

    def finalized(self) -> "LawPassport":
        payload = dataclasses.asdict(self)
        payload["digest"] = ""
        return dataclasses.replace(self, digest=digest_payload(payload))


@dataclass(frozen=True)
class ComputationalMethodPassport:
    """Machine-readable passport for an established computational method.

    This object is deliberately separate from ``LawPassport``: a numerical
    representation or contraction algorithm is not a law of nature.
    """

    method_id: str
    name_ru: str
    domain_id: str
    method_family: str
    role: str
    scientific_coordinate: Mapping[str, Any]
    capabilities: Tuple[str, ...]
    applicability_rules: Tuple[Mapping[str, Any], ...]
    cost_model: Mapping[str, str]
    error_contract: Mapping[str, str]
    exactness_class: str
    limitations: Tuple[str, ...]
    provenance: Mapping[str, Any]
    epistemic_state: str = "ESTABLISHED_METHOD"
    incompatible_method_ids: Tuple[str, ...] = ()
    exclusive_group: str | None = None
    digest: str = ""

    def finalized(self) -> "ComputationalMethodPassport":
        payload = dataclasses.asdict(self)
        payload["digest"] = ""
        return dataclasses.replace(self, digest=digest_payload(payload))


@dataclass
class GateCertificate:
    """Digest-bound certificate compatible with the existing Φ owner."""

    owner_version: str
    observation_kind: str
    family: str
    checks: Dict[str, bool]
    metrics: Dict[str, float | int | str]
    assumptions: List[str]
    status: str = ""
    digest: str = ""

    def finalize(self) -> "GateCertificate":
        self.status = "PASS" if self.checks and all(self.checks.values()) else "FAIL"
        payload = dataclasses.asdict(self)
        payload["digest"] = ""
        self.digest = digest_payload(payload)
        return self


@dataclass(frozen=True)
class CorpusCoverageCertificate:
    manifest_ids: Tuple[str, ...]
    declared_records: int
    processed_records: int
    missing_owner_ids: Tuple[str, ...]
    unknown_source_ids: Tuple[str, ...]
    status: str
    digest: str


def dataclass_from_dict(cls: type, payload: Mapping[str, Any]) -> Any:
    """Restricted helper for simple persisted records."""
    return cls(**payload)
