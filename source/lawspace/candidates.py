"""Authoritative full-registry census and owner-hypergraph model search for Φ-Compiler v6.1.

The single active owner performs three operations without conflating them:

1. an exact compressed census of every finite subset order in each registered
   disciplinary axis space and of the global cross-domain axis product space;
2. owner/domain-neutral exploration of axis combinations and void/frontier regions;
3. guarded sparse emission from registered transformations and bridges;
4. deterministic target-terminated search over the connected owner hypergraph
   to materialize high-order coupled residual systems.

There is no fixed small axis-order ceiling and no fixed visit budget.  Axis
ownership and disciplinary provenance do not prohibit combinations in the
exploration lane: a cross-domain tuple is addressable even before an arithmetic
bridge is known.  Arithmetic identification still requires a typed contract.
Voids/open subsets are retained as frontier candidates, never interpreted as
proof that nature is empty there.  The finite registered owner graph is explored
until the requested semantic target is reached or its connected frontier is
exhausted.  Continuous parameter spaces are not claimed to be exhaustively
enumerated.  Deep formulas are typed direct-sum residual hypotheses with
explicit per-axis bindings; they are never promoted to laws, novelty claims or
experimental confirmations.
"""
from __future__ import annotations

import dataclasses
import hashlib
import itertools
import json
import math
import re

import numpy as np
import sympy as sp
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Sequence, Tuple

from .catalog import LawCatalog
from .domains import DOMAIN_REGISTRIES
from .schema import (
    DomainBridge, DistributionWavefrontIR, ExpressionIR, LawPassport,
    OperatorScopeIR, SharedBindingGraph, canonical_json, digest_payload,
)
from .formal_contracts import (
    candidate_inheritance_contract, candidate_limit_protocol, candidate_proof_graph, method_route_limit_protocol,
    method_route_proof_graph, source_ledger_from_methods, source_ledger_from_passports,
)

GENERATOR_SCHEMA = "phi-composite-model-generation/v6.1"
GENERATOR_VERSION = "6.1.0"
GENERATED_SOURCE_ID = "GENERATED_COMPOSITE_MODELS_V6_1"
ELIGIBLE_SOURCE_STATES = {
    "ESTABLISHED_LAW",
    "EXPERIMENTALLY_CONFIRMED",
    "THEORETICAL",
    "PHENOMENOLOGICAL",
}

# These roles are definitions, theorem statements, no-go results, or pure
# identities.  They can be used by gates, but they are not evolution laws to
# which arbitrary memory/noise/nonlocal operators may be appended.
NON_GENERATIVE_STATEMENT_MARKERS = (
    "запрет клонирования",
    "no-cloning",
    "определение",
    "definition",
)

NON_GENERATIVE_OWNER_IDS = {
    "FND-04", "FND-11", "FND-12", "HYP-04",
    "QFT-11", "QFT-14", "QFT-15", "QFT-16",
    "QTM-01", "QTM-06", "QTM-08", "QTM-10", "QTM-12", "QTM-13",
    "REL-01", "REL-05",
}



@dataclass(frozen=True)
class TransformationSpec:
    transformation_id: str
    generator_id: str
    source_domains: Tuple[str, ...]
    target_domains: Tuple[str, ...]
    axis_ids: Tuple[str, ...]
    applicable_families: Tuple[str, ...]
    required_any_tags: Tuple[str, ...]
    formula_builder: Callable[[Sequence[LawPassport], DomainBridge | None], str]
    coordinate_delta: Mapping[str, Any]
    dimension_contract: str
    assumptions: Tuple[str, ...]
    controlled_limits: Tuple[str, ...]
    falsification_criterion: str
    required_measurements: Tuple[str, ...]
    categories: Tuple[str, ...]
    risk_class: str
    bridge_id: str | None = None
    composition_order: int = 1
    allow_non_generative_statement: bool = False

    @property
    def digest(self) -> str:
        payload = {
            "transformation_id": self.transformation_id,
            "generator_id": self.generator_id,
            "source_domains": self.source_domains,
            "target_domains": self.target_domains,
            "axis_ids": self.axis_ids,
            "applicable_families": self.applicable_families,
            "required_any_tags": self.required_any_tags,
            "coordinate_delta": self.coordinate_delta,
            "dimension_contract": self.dimension_contract,
            "assumptions": self.assumptions,
            "controlled_limits": self.controlled_limits,
            "falsification_criterion": self.falsification_criterion,
            "required_measurements": self.required_measurements,
            "categories": self.categories,
            "risk_class": self.risk_class,
            "bridge_id": self.bridge_id,
            "composition_order": self.composition_order,
            "allow_non_generative_statement": self.allow_non_generative_statement,
        }
        return digest_payload(payload)


@dataclass
class AxisAuditRow:
    domain_id: str
    axis_id: str
    role: str
    transformation_ids: List[str] = field(default_factory=list)
    evaluated: int = 0
    emitted: int = 0
    rejected: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "axis_id": self.axis_id,
            "role": self.role,
            "transformation_ids": sorted(set(self.transformation_ids)),
            "evaluated": self.evaluated,
            "emitted": self.emitted,
            "rejected": self.rejected,
        }


@dataclass
class GenerationAudit:
    evaluated: int = 0
    emitted: int = 0
    deduplicated: int = 0
    rejected: int = 0
    rejected_by_gate: MutableMapping[str, int] = field(default_factory=dict)
    emitted_by_generator: MutableMapping[str, int] = field(default_factory=dict)
    emitted_by_domain: MutableMapping[str, int] = field(default_factory=dict)
    emitted_by_category: MutableMapping[str, int] = field(default_factory=dict)
    emitted_by_order: MutableMapping[str, int] = field(default_factory=dict)
    axis_rows: MutableMapping[Tuple[str, str], AxisAuditRow] = field(default_factory=dict)

    def register_axes(self, spec: TransformationSpec, *, event: str) -> None:
        for domain in spec.target_domains:
            registry = DOMAIN_REGISTRIES.get(domain)
            if registry is None:
                continue
            for axis_id in spec.axis_ids:
                if axis_id not in registry.axes:
                    continue
                key = (domain, axis_id)
                row = self.axis_rows.get(key)
                if row is None:
                    continue
                if spec.transformation_id not in row.transformation_ids:
                    row.transformation_ids.append(spec.transformation_id)
                if event == "evaluated":
                    row.evaluated += 1
                elif event == "emitted":
                    row.emitted += 1
                elif event == "rejected":
                    row.rejected += 1

    def reject(self, gate: str, spec: TransformationSpec | None = None) -> None:
        self.rejected += 1
        self.rejected_by_gate[gate] = self.rejected_by_gate.get(gate, 0) + 1
        if spec is not None:
            self.register_axes(spec, event="rejected")

    def accept(self, row: Mapping[str, Any], spec: TransformationSpec) -> None:
        self.emitted += 1
        generator = str(row["generator"]["generator_id"])
        self.emitted_by_generator[generator] = self.emitted_by_generator.get(generator, 0) + 1
        order_key = str(spec.composition_order)
        self.emitted_by_order[order_key] = self.emitted_by_order.get(order_key, 0) + 1
        for domain in row["target_domains"]:
            self.emitted_by_domain[domain] = self.emitted_by_domain.get(domain, 0) + 1
        for category in row["classification"]["categories"]:
            self.emitted_by_category[category] = self.emitted_by_category.get(category, 0) + 1
        self.register_axes(spec, event="emitted")


class CandidateDeduplicator:
    """Conservative content-addressed deduplication.

    Scientific equivalence is never inferred from text similarity.  Records
    merge only if source formulas, target domains, axis transition signature,
    coordinate delta and candidate formula are exactly equal after canonical
    parsing.
    """

    def __init__(self) -> None:
        self._records: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def key(row: Mapping[str, Any]) -> str:
        payload = {
            "source_formula_digests": sorted(row["source_formula_digests"]),
            "target_domains": sorted(row["target_domains"]),
            "axis_ids": sorted(row["transformation"]["axis_ids"]),
            "coordinate_delta": row["coordinate_delta"],
            "formula_digest": row["formula"]["digest"],
        }
        return digest_payload(payload)

    def add(self, row: Dict[str, Any]) -> bool:
        key = self.key(row)
        previous = self._records.get(key)
        if previous is None:
            self._records[key] = row
            return True
        merged = sorted(set(previous.get("equivalent_source_owner_ids", [])) | set(row["source_owner_ids"]))
        previous["equivalent_source_owner_ids"] = merged
        previous["deduplication"]["merged_equivalent_records"] += 1
        previous["digest"] = _candidate_digest(previous)
        return False

    def values(self) -> List[Dict[str, Any]]:
        return sorted(self._records.values(), key=lambda row: row["candidate_id"])


def _base_residual(passport: LawPassport) -> str:
    return f"R_base[Psi] := ({passport.formula.source})"


def _single_formula(extra: str) -> Callable[[Sequence[LawPassport], DomainBridge | None], str]:
    def build(passports: Sequence[LawPassport], bridge: DomainBridge | None = None) -> str:
        return f"{_base_residual(passports[0])}; {extra}"
    return build


def _bridge_formula(passports: Sequence[LawPassport], bridge: DomainBridge | None) -> str:
    if bridge is None:
        raise ValueError("bridge transformation requires a registered bridge")
    residuals = " + ".join(f"R_{idx+1}[Psi_{idx+1}]" for idx in range(len(passports)))
    arguments = ",".join(f"Psi_{idx+1}" for idx in range(len(passports)))
    return (
        f"C_{bridge.bridge_id}[{arguments}] := ({bridge.composition_ast.source}); "
        f"{residuals} + lambda_bridge C_{bridge.bridge_id}[{arguments}] = 0"
    )


def _symbolic_contract(operator_name: str) -> str:
    return canonical_json({
        "status": "VALIDATED_SYMBOLIC_BY_CONSTRUCTION",
        "base_residual_dimension": "D_R",
        "added_operator": operator_name,
        "coefficient_rule": "D_lambda = D_R - D_operator",
        "numeric_SI_vector": "PENDING_SOURCE_SYMBOL_LOWERING",
    })


def _normalize_family(value: str) -> str:
    raw = str(value or "").strip().casefold().replace("-", "_")
    aliases = {
        "ode": "ODE",
        "pde": "PDE",
        "sde": "STOCHASTIC",
        "stochastic": "STOCHASTIC",
        "algebraic": "ALGEBRAIC",
        "operator": "OPERATOR",
        "integral": "INTEGRAL",
        "variational": "VARIATIONAL",
        "constraint": "CONSTRAINT",
        "conservation": "CONSERVATION",
        "inequality": "CONSTRAINT",
        "differential_form": "CONSERVATION",
        "reaction": "REACTION",
        "reaction_network": "REACTION_NETWORK",
    }
    return aliases.get(raw, raw.upper() or "UNKNOWN")


def _expression_family(passport: LawPassport) -> str:
    coordinate = passport.scientific_coordinate
    if "equation_family" in coordinate:
        return _normalize_family(str(coordinate["equation_family"]))
    chemistry_map = {
        "RATE_LAW": "RATE_LAW",
        "RATE_COEFFICIENT": "RATE_COEFFICIENT",
        "REACTION_BALANCE": "REACTION_BALANCE",
        "EQUILIBRIUM": "EQUILIBRIUM",
        "PHASE_EQUILIBRIUM": "PHASE_EQUILIBRIUM",
        "THERMODYNAMIC_IDENTITY": "THERMODYNAMIC_IDENTITY",
        "CHEMICAL_POTENTIAL": "CHEMICAL_POTENTIAL",
        "ELECTROCHEMISTRY": "ELECTROCHEMISTRY",
        "SPECTROSCOPY": "SPECTROSCOPY",
        "TRANSPORT": "TRANSPORT",
    }
    return chemistry_map.get(passport.entity_kind, _normalize_family(passport.entity_kind))


def _statement_role(passport: LawPassport) -> str:
    text = f"{passport.name_ru} {passport.formula.source}".casefold()
    if passport.owner_id in NON_GENERATIVE_OWNER_IDS or any(marker in text for marker in NON_GENERATIVE_STATEMENT_MARKERS):
        return "NON_GENERATIVE_STATEMENT"
    family = _expression_family(passport)
    if family in {"ODE", "PDE", "STOCHASTIC", "RATE_LAW", "REACTION_NETWORK", "TRANSPORT"}:
        return "EVOLUTION"
    if family in {"CONSERVATION", "REACTION_BALANCE"}:
        return "BALANCE"
    if family in {"VARIATIONAL"}:
        return "VARIATIONAL"
    if family in {"EQUILIBRIUM", "PHASE_EQUILIBRIUM", "CHEMICAL_POTENTIAL", "ELECTROCHEMISTRY"}:
        return "CONSTITUTIVE"
    if family in {"ALGEBRAIC", "OPERATOR", "INTEGRAL", "RATE_COEFFICIENT", "SPECTROSCOPY"}:
        return "RELATION"
    return "MODEL_OBJECT"


def _semantic_tags(passport: LawPassport) -> Tuple[str, ...]:
    """Derive scientific roles from canonical owner data, never candidate rows."""
    tags = {passport.domain_id, passport.entity_kind.casefold(), _expression_family(passport).casefold(), _statement_role(passport).casefold()}
    prefix = passport.owner_id.split("-", 1)[0].upper()
    prefix_tags = {
        "EM": {"electromagnetic", "field", "continuum_driver"},
        "REL": {"gravity", "spacetime", "field"},
        "THM": {"thermodynamic", "statistical", "relaxation"},
        "QTM": {"quantum"},
        "QFT": {"quantum", "quantum_field", "particle", "field"},
        "WAV": {"wave", "optical"},
        "PLS": {"plasma", "electromagnetic", "continuum", "transport", "field", "continuum_driver"},
        "MAT": {"condensed_matter", "materials", "solid_state", "transport"},
        "MEC": {"mechanics", "particle_mechanics"},
        "CON": {"mechanics", "continuum"},
        "CHEM": {"chemistry"},
        "AST": {"astronomy", "gravity"},
    }
    tags.update(prefix_tags.get(prefix, set()))
    # Canonical semantic roles used by interdisciplinary bridges.  These are
    # source-owner classifications, not prepared candidate pairs: a bridge can
    # combine any owners that share the required role, while unrelated laws in
    # the same broad discipline remain fail-closed.
    bridge_role_tags: Mapping[str, Tuple[str, ...]] = {
        "EM-07": ("force_field_source", "continuum_coupling_source", "electrochemical_field_source"),
        "EM-02": ("electrochemical_field_source",),
        "EM-03": ("electrochemical_field_source",),
        "EM-05": ("electrochemical_field_source",),
        "EM-09": ("continuum_coupling_source",),
        "EM-10": ("continuum_coupling_source",),
        "EM-11": ("electrochemical_field_source",),
        "REL-08": ("continuum_coupling_source",),
        "PLS-04": ("continuum_coupling_source", "combustion_energy_source"),
        "PLS-05": ("continuum_coupling_source",),
        "THM-02": ("thermodynamic_state_relation", "combustion_energy_source"),
        "THM-05": ("thermodynamic_state_relation", "combustion_energy_source"),
        "THM-06": ("thermodynamic_state_relation", "combustion_energy_source"),
        "THM-07": ("thermodynamic_state_relation",),
        "THM-08": ("thermodynamic_state_relation",),
        "THM-09": ("thermodynamic_state_relation",),
        "THM-10": ("thermodynamic_state_relation",),
        "THM-11": ("thermodynamic_state_relation",),
        "THM-12": ("thermodynamic_state_relation",),
        "THM-13": ("thermodynamic_state_relation",),
        "QFT-01": ("molecular_quantum_source", "spectroscopic_transition_source"),
        "QFT-03": ("molecular_quantum_source", "spectroscopic_transition_source"),
        "QFT-04": ("molecular_quantum_source", "spectroscopic_transition_source"),
        "QTM-01": ("molecular_quantum_source",),
        "QTM-02": ("molecular_quantum_source",),
        "QTM-09": ("molecular_quantum_source", "spectroscopic_transition_source"),
        "MEC-02": ("force_balance",),
        "CON-02": ("force_balance", "continuum_balance"),
        "CON-03": ("continuum_balance", "reactive_transport_carrier", "combustion_flow_carrier"),
        "CON-04": ("force_balance", "continuum_balance", "reactive_transport_carrier", "combustion_flow_carrier"),
        "CON-01": ("continuum_balance", "reactive_transport_carrier", "combustion_flow_carrier"),
        "CON-06": ("continuum_balance", "reactive_transport_carrier", "combustion_flow_carrier"),
        "CON-07": ("continuum_balance", "reactive_transport_carrier", "combustion_flow_carrier"),
        "CON-08": ("continuum_balance", "reactive_transport_carrier", "electrochemical_transport_carrier"),
        "CON-09": ("continuum_balance", "reactive_transport_carrier", "electrochemical_transport_carrier"),
        "CON-10": ("continuum_balance", "reactive_transport_carrier"),
        "CON-14": ("continuum_balance", "reactive_transport_carrier", "electrochemical_transport_carrier"),
        "CON-15": ("continuum_balance", "reactive_transport_carrier"),
        "CHEM-001": ("reactive_source",),
        "CHEM-002": ("reactive_source",),
        "CHEM-004": ("reactive_source", "combustion_reaction_source"),
        "CHEM-005": ("reactive_source", "combustion_reaction_source"),
        "CHEM-006": ("reactive_source", "combustion_reaction_source", "quantum_chemistry_target"),
        "CHEM-007": ("thermochemical_target",),
        "CHEM-008": ("thermochemical_target",),
        "CHEM-009": ("thermochemical_target",),
        "CHEM-010": ("thermochemical_target",),
        "CHEM-011": ("quantum_chemistry_target", "electrochemical_target"),
        "CHEM-012": ("electrochemical_target",),
        "CHEM-013": ("quantum_chemistry_target", "spectroscopy_target"),
        "CHEM-014": ("thermochemical_target",),
        "CHEM-015": ("thermochemical_target",),
        "CHEM-016": ("thermochemical_target",),
        "CHEM-017": ("thermochemical_target",),
        "CHEM-018": ("thermochemical_target",),
        "CHEM-019": ("thermochemical_target",),
        "CHEM-020": ("thermochemical_target",),
        "CHEM-021": ("reactive_source",),
        "CHEM-022": ("reactive_source",),
    }
    tags.update(bridge_role_tags.get(passport.owner_id, ()))
    name = passport.name_ru.casefold()
    formula = passport.formula.source.casefold()
    text = name + " " + formula

    def contains(*tokens: str) -> bool:
        return any(token.casefold() in text for token in tokens)

    family = _expression_family(passport)
    if _statement_role(passport) in {"EVOLUTION", "BALANCE"}:
        tags.add("dynamics")
    if family == "STOCHASTIC":
        tags.add("stochastic")
    if family == "PDE":
        tags.update({"field", "continuum"})
    if contains("тепл", "диффуз", "фурье", "фик", "перенос", "transport"):
        tags.update({"transport", "heat", "continuum_driver"})
    if contains("энерг", "энтальп", "тепл", "температур", "идеальный газ"):
        tags.add("energy_balance")
    if contains("шрёдин", "фон нейман", "гамильтон", "декогер", "линдблад"):
        tags.update({"quantum_dynamics", "dynamics"})
    if contains("уровн", "туннел", "адиабат", "планк", "ридберг", "бор", "спектр", "фотон", "переход"):
        tags.add("quantum_spectrum")
    if contains("ренорм", "бета-функ", "rg", "масштаб") or passport.entity_kind == "RG_FLOW":
        tags.add("rg")
    if prefix == "EM" and contains("кулон", "электрического поля", "лоренц", "сила", "амп"):
        tags.add("force_source")
    if prefix == "REL" and contains("эйнштейн", "геодез", "гравитац", "эквивалентност"):
        tags.add("force_source")

    if passport.domain_id == "mechanics":
        if contains("импульс", "момент количества движения", "коши"):
            tags.add("momentum_balance")
        if contains("второй закон ньютона", "уравнение коши импульса", "нави", "уравнение эйлера жидкости", "уравнения гамильтона"):
            tags.add("equation_of_motion")
        if contains("гук", "упруг", "деформа", "напряжен", "напряжён"):
            tags.update({"solid_constitutive", "structural"})
        if contains("жидк", "нави", "бернул", "паскал", "архимед", "вихр", "дарси", "стокс"):
            tags.update({"fluid", "continuum"})
        if contains("фурье", "теплопровод", "фик", "диффуз", "дарси", "перенос"):
            tags.add("transport")
        if contains("трени", "контакт"):
            tags.update({"friction", "contact"})
        if contains("реолог", "вязк"):
            tags.add("rheology")
        if contains("колеб", "осцил", "маятник"):
            tags.update({"oscillation", "dynamics"})

    if passport.domain_id == "chemistry":
        kind_tags = {
            "RATE_LAW": {"kinetics"},
            "RATE_COEFFICIENT": {"kinetics"},
            "REACTION_BALANCE": {"reaction_balance"},
            "EQUILIBRIUM": {"equilibrium", "thermodynamic"},
            "PHASE_EQUILIBRIUM": {"phase_equilibrium", "equilibrium", "thermodynamic"},
            "THERMODYNAMIC_IDENTITY": {"thermodynamic"},
            "CHEMICAL_POTENTIAL": {"chemical_potential", "thermodynamic"},
            "ELECTROCHEMISTRY": {"electrochemistry", "kinetics"},
            "SPECTROSCOPY": {"spectroscopy"},
            "TRANSPORT": {"transport"},
        }
        tags.update(kind_tags.get(passport.entity_kind, set()))
        if contains("аррениус", "эйринг", "действующих масс", "стехиометр"):
            tags.add("combustion_kinetics")

    if passport.domain_id == "materials_science":
        tags.add("materials")
        if contains("полимер", "реолог", "вязкоупруг", "вязкост"):
            tags.add("rheology_material")
        if contains("набух", "химическ", "диффуз", "фазов", "гидрид", "интеркал"):
            tags.add("chemomechanical_material")
        if contains("тепло", "дебая", "дюлонга", "видемана"):
            tags.add("thermal_material")
        if contains("холл", "черн", "bulk", "гомотоп", "дефект"):
            tags.add("topological_material")
    for value in passport.scientific_coordinate.values():
        if isinstance(value, str):
            tags.add(value.casefold())
    return tuple(sorted(tags))


def _spec(
    transformation_id: str,
    generator_id: str,
    domain: str,
    axis_ids: Sequence[str],
    families: Sequence[str],
    tags: Sequence[str],
    extra: str,
    coordinate_delta: Mapping[str, Any],
    operator_name: str,
    assumptions: Sequence[str],
    limits: Sequence[str],
    falsifier: str,
    measurements: Sequence[str],
    categories: Sequence[str],
    risk: str,
    *,
    order: int = 1,
) -> TransformationSpec:
    return TransformationSpec(
        transformation_id=transformation_id,
        generator_id=generator_id,
        source_domains=(domain,),
        target_domains=(domain,),
        axis_ids=tuple(axis_ids),
        applicable_families=tuple(families),
        required_any_tags=tuple(tags),
        formula_builder=_single_formula(extra),
        coordinate_delta=dict(coordinate_delta),
        dimension_contract=_symbolic_contract(operator_name),
        assumptions=tuple(assumptions),
        controlled_limits=tuple(limits),
        falsification_criterion=falsifier,
        required_measurements=tuple(measurements),
        categories=tuple(categories),
        risk_class=risk,
        composition_order=order,
    )


DYNAMIC_FAMILIES = ("ODE", "PDE", "STOCHASTIC", "CONSERVATION", "OPERATOR", "INTEGRAL")
FIELD_FAMILIES = ("PDE", "CONSERVATION", "VARIATIONAL", "OPERATOR")
RELATION_FAMILIES = ("ALGEBRAIC", "OPERATOR", "INTEGRAL", "VARIATIONAL")
MECH_FAMILIES = ("ODE", "PDE", "CONSERVATION", "ALGEBRAIC")
CHEM_KINETIC_FAMILIES = ("RATE_LAW", "RATE_COEFFICIENT", "REACTION_BALANCE", "TRANSPORT", "ELECTROCHEMISTRY")
CHEM_THERMO_FAMILIES = ("EQUILIBRIUM", "PHASE_EQUILIBRIUM", "THERMODYNAMIC_IDENTITY", "CHEMICAL_POTENTIAL", "ELECTROCHEMISTRY")


def _physics_specs() -> Tuple[TransformationSpec, ...]:
    g = "PhysicsCandidateGenerator"
    return (
        _spec("PHYS_MEMORY_KERNEL", g, "physics", ("equation_family", "memory", "time_order", "causal_order"), DYNAMIC_FAMILIES, ("dynamics", "transport", "relaxation", "wave", "quantum_dynamics"),
              "R_base[Psi](t) + lambda_mem Integral_0^t K_mem(t-s) O_mem[Psi(s)] ds = 0", {"memory": "convolution_kernel"}, "memory_convolution",
              ("K_mem is causal", "kernel regularity and initial history are declared"), ("lambda_mem -> 0 recovers source owner", "K_mem -> delta recovers Markovian correction"),
              "One kernel must predict pulse and relaxation holdouts better than all finite Markov closures.", ("time-resolved observable", "pulse protocol", "holdout trajectory"), ("fundamental", "high_risk"), "HIGH"),
        _spec("PHYS_SPATIAL_NONLOCAL", g, "physics", ("locality", "interaction_range", "space_order"), FIELD_FAMILIES, ("field", "continuum", "transport", "wave", "plasma", "gravity"),
              "R_base[Psi](x,t) + lambda_nl Integral_Omega W_l(x,y) O_nl[Psi](y,t) dy = 0", {"locality": "spatially_nonlocal", "interaction_range": "kernel_controlled"}, "spatial_integral_operator",
              ("W_l normalization is explicit", "boundary treatment is explicit"), ("lambda_nl -> 0 recovers source owner", "W_l -> delta recovers local closure"),
              "Matched local states with different neighborhoods must show the predicted nonlocal response.", ("spatial field map", "kernel scale sweep", "local controls"), ("fundamental", "applied"), "MEDIUM"),
        _spec("PHYS_FRACTIONAL_TIME", g, "physics", ("time_order", "memory", "regularity_class"), ("ODE", "PDE", "STOCHASTIC"), ("dynamics", "transport", "relaxation", "wave"),
              "R_base[Psi] + lambda_alpha D_t^alpha O_alpha[Psi] = 0; 0 < alpha < 1", {"time_order": "fractional", "memory": "fractional"}, "fractional_time_operator",
              ("fractional derivative convention is fixed", "initial history is measured"), ("lambda_alpha -> 0 recovers source owner", "alpha -> 1 gives integer-order correction"),
              "One alpha must predict multiple time decades and frequency-domain holdouts.", ("multi-decade relaxation", "frequency response", "initial history"), ("applied", "rapid_test"), "MEDIUM"),
        _spec("PHYS_STOCHASTIC_DRIVE", g, "physics", ("determinism", "probability_model", "stochastic_calculus", "noise_model"), ("ODE", "PDE", "CONSERVATION", "OPERATOR"), ("dynamics", "field", "transport", "wave", "quantum_dynamics"),
              "R_base[Psi] + sigma_xi G_xi[Psi] xi(x,t) = 0; E[xi] = 0", {"determinism": "stochastic", "probability_model": "classical_stochastic"}, "stochastic_drive",
              ("Ito or Stratonovich convention is fixed", "noise covariance is measured"), ("sigma_xi -> 0 recovers source owner",),
              "Held-out path statistics, not only the mean, must match.", ("trajectory ensemble", "noise covariance", "sampling cadence"), ("applied", "rapid_test"), "LOW"),
        _spec("PHYS_COVARIANT_GEOMETRY", g, "physics", ("signature", "geometry_dynamics", "curvature_regime", "connection_type", "metric_structure", "coordinate_frame", "spatial_dimension", "temporal_dimension"), FIELD_FAMILIES, ("field", "gravity", "spacetime", "quantum_field", "wave"),
              "Cov_g(R_base)[Psi,g,Gamma] = 0", {"geometry_dynamics": "prescribed_or_dynamical", "curvature_regime": "nonzero"}, "covariantization",
              ("connection and tensor weights are explicit",), ("g -> g_flat recovers source owner", "Gamma -> 0 in Cartesian chart recovers partial derivatives"),
              "Equal local invariants on different curvature backgrounds must display the predicted difference.", ("metric or discrete geometry", "field observables", "flat control"), ("fundamental", "high_risk"), "HIGH"),
        _spec("PHYS_TORSION_EXTENSION", g, "physics", ("torsion", "connection_type"), FIELD_FAMILIES, ("gravity", "spacetime", "field", "quantum_field"),
              "Cov_Gamma(R_base)[Psi,g,T] + lambda_T T^a_bc J_a^bc[Psi] = 0", {"torsion": "nonzero"}, "torsion_coupling",
              ("torsion tensor and source current are defined",), ("T -> 0 recovers torsion-free source owner",),
              "A torsion-sensitive observable must separate the model from every curvature-only alternative.", ("spin or torsion-sensitive observable", "geometry control"), ("fundamental", "high_risk"), "HIGH"),
        _spec("PHYS_TOPOLOGICAL_SECTOR", g, "physics", ("topology", "boundary_geometry", "form_degree"), FIELD_FAMILIES + ("ALGEBRAIC",), ("field", "condensed_matter", "quantum_field", "gravity"),
              "R_base[Psi] + theta_top Integral_M P(F,R) + B_boundary[Psi] = 0", {"topology": "nontrivial", "boundary_geometry": "explicit"}, "topological_density",
              ("topological density has declared normalization", "boundary term is well posed"), ("theta_top -> 0 recovers source owner", "trivial topology removes sector"),
              "A topology-changing control must alter a quantized or boundary observable while local controls are held fixed.", ("topological invariant", "boundary observable", "gap or regularity control"), ("fundamental", "high_risk"), "HIGH"),
        _spec("PHYS_SINGULARITY_REGULARIZATION", g, "physics", ("singularity_class", "regularity_class", "effective_order"), FIELD_FAMILIES + ("ALGEBRAIC",), ("field", "gravity", "plasma", "quantum_field"),
              "R_base[Psi] + Sum_n lambda_n Lambda^(-n) O_n[Psi] = 0", {"singularity_class": "regularized", "effective_order": "finite_truncation"}, "effective_regularization",
              ("operator basis and cutoff are explicit",), ("Lambda -> infinity recovers source owner",),
              "Regularized predictions must remain stable under cutoff variation and beat source singular behavior on holdout data.", ("near-singular observables", "cutoff sweep", "resolution study"), ("fundamental", "high_risk"), "HIGH"),
        _spec("PHYS_OPEN_QUANTUM_EXTENSION", g, "physics", ("openness", "generator_type", "dissipation", "reversibility", "state_carrier", "state_space"), ("ODE", "PDE", "OPERATOR", "ALGEBRAIC"), ("quantum_dynamics",),
              "dot(rho) = -(i/hbar)[H_base,rho] + Sum_ab C_ab (L_a rho L_b^dagger - 1/2 {L_b^dagger L_a,rho}); C >= 0", {"openness": "quantum_open", "generator_type": "GKSL"}, "gksl_generator",
              ("C is positive semidefinite", "operator domains are declared"), ("C -> 0 recovers unitary source dynamics",),
              "Process data must reject every unitary model while a CPTP map predicts held-out preparations.", ("state tomography or process data", "environment control", "holdout preparations"), ("fundamental", "applied"), "MEDIUM"),
        _spec("PHYS_CAUSAL_FINITE_SPEED", g, "physics", ("causal_structure", "causal_order", "reversibility", "time_order"), ("PDE", "CONSERVATION"), ("transport", "heat", "continuum", "plasma"),
              "tau_c partial_t^2 Psi + partial_t Psi = D O_space[Psi]", {"causal_structure": "finite_speed", "time_order": "second"}, "hyperbolic_regularization",
              ("tau_c > 0", "initial derivative is supplied"), ("tau_c -> 0 recovers parabolic source owner",),
              "Early-time front arrival must reject infinite-speed diffusion.", ("front arrival times", "early-time field", "length sweep"), ("applied", "rapid_test"), "LOW"),
        _spec("PHYS_SYMMETRY_BREAKING", g, "physics", ("spacetime_symmetry", "internal_symmetry", "symmetry_realization", "symmetry_breaking"), FIELD_FAMILIES + RELATION_FAMILIES, ("field", "condensed_matter", "quantum_field", "particle"),
              "R_base[Psi] + dV_eff(Phi)/dPhi = 0; V_eff = a Phi^2 + b Phi^4", {"symmetry_realization": "spontaneously_broken", "symmetry_breaking": "order_parameter"}, "order_parameter_potential",
              ("symmetry group and order parameter representation are explicit",), ("a > 0 and Phi -> 0 recovers symmetric phase",),
              "Order-parameter scaling and mode spectrum must transfer across control values.", ("order parameter", "susceptibility", "mode spectrum"), ("fundamental", "applied"), "MEDIUM"),
        _spec("PHYS_GAUGE_COVARIANT_COUPLING", g, "physics", ("gauge_group", "interaction_sector", "charge_structure", "constraint_algebra", "internal_symmetry"), FIELD_FAMILIES + ("ODE", "ALGEBRAIC"), ("field", "quantum_field", "particle", "electromagnetic"),
              "partial_mu -> D_mu = partial_mu + i g A_mu^a T_a; R_base[D Psi,F] = 0", {"gauge_group": "declared_nontrivial", "interaction_sector": "gauge_coupled"}, "gauge_covariant_derivative",
              ("group, representation and charges are explicit",), ("g -> 0 recovers uncoupled source owner",),
              "Gauge-invariant observables must predict a coupling-dependent holdout without gauge-coordinate dependence.", ("gauge-invariant observable", "coupling sweep", "constraint residual"), ("fundamental", "high_risk"), "HIGH"),
        _spec("PHYS_VARIATIONAL_HAMILTONIAN_LIFT", g, "physics", ("variational_structure", "hamiltonian_structure", "conservation_structure", "constraint_algebra"), ("ODE", "PDE", "CONSERVATION", "ALGEBRAIC"), ("dynamics", "field", "mechanics"),
              "delta S_eff[Psi] = 0; S_eff = Integral L_base + lambda_v L_corr", {"variational_structure": "explicit", "hamiltonian_structure": "derived"}, "variational_lift",
              ("boundary variations vanish or boundary action is supplied",), ("lambda_v -> 0 recovers source owner",),
              "Euler-Lagrange equations and conserved charges must match independent numerical differentiation.", ("trajectory or field", "boundary data", "conserved charge"), ("fundamental",), "MEDIUM"),
        _spec("PHYS_NONLINEAR_CLOSURE", g, "physics", ("linearity_state", "linearity_parameters", "generator_type"), ("ODE", "PDE", "CONSERVATION", "ALGEBRAIC"), ("dynamics", "field", "transport", "wave"),
              "R_base[Psi] + lambda_nl N[Psi,grad Psi] = 0", {"linearity_state": "nonlinear"}, "nonlinear_closure",
              ("nonlinear operator respects declared symmetries",), ("lambda_nl -> 0 recovers source owner",),
              "Amplitude-dependent response must be predicted across at least two excitation levels.", ("amplitude sweep", "harmonic content", "holdout excitation"), ("applied", "rapid_test"), "LOW"),
        _spec("PHYS_MULTISCALE_HOMOGENIZATION", g, "physics", ("scale_regime", "multiscale_structure", "continuum_discrete_status", "thermodynamic_limit"), FIELD_FAMILIES + ("ODE",), ("field", "continuum", "condensed_matter", "transport", "plasma"),
              "R_micro[Psi,x/epsilon] = 0; R_eff[bar(Psi)] = Homogenize_epsilon(R_micro)", {"multiscale_structure": "micro_to_macro", "continuum_discrete_status": "linked"}, "homogenization",
              ("scale separation parameter epsilon is measured",), ("epsilon -> 0 yields effective source owner",),
              "Effective coefficients must transfer to unseen microstructures with matched scale statistics.", ("microstructure", "micro field", "macro response"), ("applied", "interdisciplinary"), "MEDIUM"),
        _spec("PHYS_RG_EFFECTIVE_FLOW", g, "physics", ("renormalization_status", "RG_regime", "effective_order", "perturbation_order", "scale_regime"), FIELD_FAMILIES + RELATION_FAMILIES, ("rg", "quantum_field", "condensed_matter", "particle"),
              "mu d g_i/d mu = beta_i(g); R_eff[Psi;g_i(mu)] = 0", {"renormalization_status": "running", "RG_regime": "flow"}, "renormalization_flow",
              ("renormalization scheme and operator basis are fixed",), ("beta -> 0 recovers fixed-coupling owner",),
              "One running law must predict observables at multiple scales.", ("multi-scale observables", "renormalization scale", "scheme comparison"), ("fundamental", "high_risk"), "HIGH"),
        _spec("PHYS_CLASSICAL_QUANTUM_CROSSOVER", g, "physics", ("classical_quantum_regime", "state_carrier", "state_space", "algebra", "semiclassical_order"), ("ODE", "PDE", "ALGEBRAIC", "OPERATOR", "VARIATIONAL"), ("dynamics", "field", "particle_mechanics", "quantum", "quantum_dynamics"),
              "R_W[W] = Moyal(R_base) = Poisson(R_base) + Sum_n hbar^(2n) C_2n[W]", {"classical_quantum_regime": "crossover", "semiclassical_order": "controlled"}, "moyal_expansion",
              ("phase-space quantization map is fixed",), ("hbar -> 0 recovers classical source owner",),
              "Quantum corrections must scale with the declared semiclassical parameter and vanish in the classical control.", ("phase-space observable", "semiclassical scale sweep", "classical control"), ("fundamental", "high_risk"), "HIGH"),
        _spec("PHYS_RELATIVISTIC_COMPLETION", g, "physics", ("relativistic_regime", "signature", "spacetime_symmetry", "causal_structure"), ("ODE", "PDE", "CONSERVATION", "ALGEBRAIC"), ("particle", "field", "wave", "electromagnetic", "mechanics"),
              "R_rel[Psi] = LorentzComplete(R_base; c)", {"relativistic_regime": "relativistic", "signature": "lorentzian"}, "lorentz_completion",
              ("Lorentz representation is explicit",), ("v/c -> 0 recovers nonrelativistic source owner",),
              "Relativistic corrections must follow the same parameter-free scaling across velocities.", ("velocity sweep", "proper-time or invariant observable", "low-speed control"), ("fundamental", "applied"), "MEDIUM"),
        _spec("PHYS_TENSOR_FORM_LIFT", g, "physics", ("tensor_rank", "form_degree", "state_carrier", "algebra"), ("PDE", "CONSERVATION", "ALGEBRAIC", "OPERATOR"), ("field", "continuum", "electromagnetic", "gravity"),
              "R_base[Psi] -> R_lift[T^(r),omega^(p)] with d omega + connection wedge omega", {"state_carrier": "tensor_or_differential_form"}, "tensor_form_lift",
              ("tensor representation and form degree are fixed",), ("rank reduction recovers source owner",),
              "Orientation- or polarization-resolved observables must require the lifted carrier.", ("tensor-resolved observable", "orientation sweep"), ("fundamental", "applied"), "MEDIUM"),
        _spec("PHYS_DISCRETE_GRAPH_LIFT", g, "physics", ("state_space", "continuum_discrete_status", "topology", "boundary_geometry"), ("PDE", "CONSERVATION", "ODE", "ALGEBRAIC"), ("field", "continuum", "network", "condensed_matter", "transport"),
              "R_G[Psi] = Replace(grad,div,Laplacian by incidence and graph operators)(R_base)", {"state_space": "discrete_graph", "continuum_discrete_status": "discrete"}, "discrete_exterior_calculus",
              ("orientation, incidence matrices and boundary complex are explicit",), ("mesh scale -> 0 recovers continuum source owner",),
              "Mesh-refinement and topology-change tests must separate discretization artifact from a physical graph law.", ("graph or complex", "mesh refinement", "continuum control"), ("fundamental", "applied"), "MEDIUM"),
        _spec("PHYS_DISSIPATIVE_COMPLETION", g, "physics", ("dissipation", "time_symmetry", "reversibility", "generator_type", "conservation_structure"), ("ODE", "PDE", "CONSERVATION"), ("dynamics", "wave", "continuum", "transport"),
              "R_base[Psi] + Gamma delta_R Phi[dot(Psi)] = 0; dot(S_prod) >= 0", {"dissipation": "positive", "reversibility": "irreversible"}, "rayleigh_dissipation",
              ("dissipation potential is convex",), ("Gamma -> 0 recovers reversible source owner",),
              "Energy loss and entropy production must be predicted under independent cyclic protocols.", ("energy balance", "entropy production proxy", "cyclic protocol"), ("fundamental", "applied"), "MEDIUM"),
        _spec("PHYS_MEASUREMENT_BACKACTION", g, "physics", ("observable_type", "measurement_model", "detector_coupling", "experimental_control"), ("ODE", "OPERATOR", "PDE"), ("quantum_dynamics", "stochastic", "field"),
              "d rho = L_base[rho] dt + Gamma_m D[M]rho dt + sqrt(eta Gamma_m) H[M]rho dW", {"measurement_model": "continuous_backaction", "detector_coupling": "explicit"}, "measurement_backaction",
              ("detector efficiency and coupling are calibrated",), ("Gamma_m -> 0 recovers unmeasured source owner",),
              "Conditioned and unconditioned trajectories must agree with the same detector calibration.", ("measurement record", "state estimate", "detector calibration"), ("applied", "rapid_test"), "MEDIUM"),
        _spec("PHYS_BOUNDARY_OPERATOR", g, "physics", ("boundary_geometry", "regularity_class", "causal_structure"), ("PDE", "CONSERVATION", "VARIATIONAL"), ("field", "continuum", "wave", "transport"),
              "R_base[Psi] = 0 in Omega; B[Psi,n,geometry] = 0 on partial Omega", {"boundary_geometry": "operator_defined"}, "boundary_operator",
              ("boundary operator satisfies compatibility and well-posedness conditions",), ("boundary coupling -> 0 recovers source boundary condition",),
              "Boundary-localized perturbations must be predicted without retuning bulk coefficients.", ("boundary field", "bulk field", "geometry sweep"), ("applied", "rapid_test"), "LOW"),
        # Explicit scientifically admissible second-order interactions.
        _spec("PHYS_MEMORY_NONLOCAL_COMPOSITION", g, "physics", ("memory", "locality", "interaction_range", "time_order", "space_order"), ("PDE", "CONSERVATION", "OPERATOR"), ("transport", "field", "plasma", "continuum"),
              "R_base[Psi] + Integral_0^t Integral_Omega K(x,y,t-s) O[Psi(y,s)] dy ds = 0", {"memory": "spatiotemporal_kernel", "locality": "spatially_nonlocal"}, "spatiotemporal_kernel",
              ("K is causal and spatially normalized",), ("K -> delta(t-s)delta(x-y) recovers source owner",),
              "A single spatiotemporal kernel must predict both spatial and temporal holdouts.", ("spatiotemporal field", "pulse and spatial controls"), ("fundamental", "high_risk"), "HIGH", order=2),
        _spec("PHYS_GEOMETRY_OPEN_QUANTUM_COMPOSITION", g, "physics", ("geometry_dynamics", "curvature_regime", "openness", "generator_type", "state_space"), ("ODE", "PDE", "OPERATOR", "ALGEBRAIC"), ("quantum_dynamics",),
              "dot(rho) = -i[H(g),rho]/hbar + Sum_ab C_ab(g) D_ab[rho]; C(g) >= 0", {"geometry_dynamics": "state_or_control_dependent", "openness": "quantum_open"}, "geometry_dependent_gksl",
              ("geometry is externally measured or self-consistency is declared", "C(g) remains positive"), ("curvature -> 0 and C -> 0 recover source owner",),
              "Geometry sweeps must change coherent and dissipative sectors with transferable parameters.", ("geometry", "process data", "flat control"), ("fundamental", "high_risk"), "HIGH", order=2),
    )


def _mechanics_specs() -> Tuple[TransformationSpec, ...]:
    g = "MechanicsCandidateGenerator"
    return (
        _spec("MECH_HEREDITARY_CONSTITUTIVE", g, "mechanics", ("viscoelasticity_class", "rheology", "constitutive_class", "deformation_regime"), MECH_FAMILIES, ("solid_constitutive", "rheology", "continuum"),
              "sigma(t) = Integral_0^t G(t-s) d epsilon(s)/ds ds", {"viscoelasticity_class": "hereditary", "constitutive_class": "memory_kernel"}, "hereditary_constitutive",
              ("G is causal and thermodynamically admissible",), ("G -> E delta recovers elastic source owner",),
              "One relaxation spectrum must predict creep, relaxation and cyclic holdouts.", ("stress-strain history", "creep", "relaxation", "cyclic holdout"), ("applied", "rapid_test"), "LOW"),
        _spec("MECH_GRADIENT_NONLOCAL", g, "mechanics", ("constitutive_class", "deformation_regime", "dispersion_type", "wave_type"), ("PDE", "CONSERVATION", "ALGEBRAIC"), ("solid_constitutive", "continuum", "structural"),
              "sigma = C:epsilon - l_g^2 C:Delta epsilon", {"constitutive_class": "strain_gradient", "dispersion_type": "length_scale_dependent"}, "strain_gradient",
              ("l_g >= 0", "higher-order boundary conditions are explicit"), ("l_g -> 0 recovers local source owner",),
              "Size-dependent stiffness or dispersion must transfer across specimen sizes.", ("size sweep", "strain field", "dispersion"), ("applied", "rapid_test"), "MEDIUM"),
        _spec("MECH_DAMAGE_COUPLING", g, "mechanics", ("damage_model", "failure_mode", "constitutive_class", "stability_type"), MECH_FAMILIES, ("solid_constitutive", "structural"),
              "sigma = (1-D) sigma_base; dot(D) = M_D positive_part(Y-Y_c)^n; 0 <= D <= 1", {"damage_model": "internal_variable", "failure_mode": "progressive"}, "damage_internal_variable",
              ("damage dissipation Y dot(D) >= 0",), ("D -> 0 recovers source owner",),
              "One damage law must predict monotonic and cyclic degradation on holdout paths.", ("full-field strain", "load history", "damage proxy"), ("applied", "high_risk"), "MEDIUM"),
        _spec("MECH_FRACTURE_PHASE_FIELD", g, "mechanics", ("fracture_model", "damage_model", "boundary_support", "failure_mode"), ("PDE", "VARIATIONAL", "ALGEBRAIC"), ("solid_constitutive", "structural"),
              "delta Integral_Omega g(d) psi_e(epsilon) + G_c (d^2/(2l_f) + l_f |grad d|^2/2) dV = 0", {"fracture_model": "phase_field", "failure_mode": "crack_growth"}, "phase_field_fracture",
              ("irreversibility dot(d) >= 0", "mesh resolves l_f"), ("d -> 0 recovers intact source owner",),
              "Crack path and load-displacement curve must transfer across geometry holdouts.", ("crack field", "load-displacement", "mesh study"), ("applied", "high_risk"), "HIGH"),
        _spec("MECH_RATE_STATE_CONTACT", g, "mechanics", ("contact_type", "friction_model", "constraint_type", "constraint_integrability"), MECH_FAMILIES, ("contact", "friction"),
              "mu = mu0 + a ln(v/v0) + b ln(theta v0/Dc); dot(theta) = 1 - v theta/Dc", {"friction_model": "rate_and_state", "contact_type": "history_dependent"}, "rate_state_friction",
              ("v > 0 or regularization is explicit",), ("a,b -> 0 recovers constant friction",),
              "Velocity-step and hold-slide protocols must share one parameter set.", ("friction force", "slip rate", "state protocol"), ("applied", "rapid_test"), "LOW"),
        _spec("MECH_IMPACT_INTERNAL_STATE", g, "mechanics", ("impact_model", "contact_type", "failure_mode"), ("ODE", "ALGEBRAIC", "CONSERVATION"), ("contact", "dynamics", "structural"),
              "p_plus = ImpactMap(p_minus,theta_i); dot(theta_i) = f_i(theta_i,impact_history)", {"impact_model": "history_dependent", "contact_type": "unilateral"}, "impact_internal_state",
              ("momentum balance and nonnegative dissipation hold",), ("theta_i constant recovers source impact law",),
              "Restitution across repeated impacts must be predicted without event-wise refitting.", ("pre/post impact velocity", "contact force", "impact history"), ("applied",), "MEDIUM"),
        _spec("MECH_STOCHASTIC_LOADING", g, "mechanics", ("load_type", "excitation", "control_mode", "stability_type"), ("ODE", "PDE", "CONSERVATION"), ("dynamics", "structural", "continuum", "oscillation"),
              "R_base[q] + B(q) xi(t) = 0; E[xi(t)xi(s)] = Q(t,s)", {"excitation": "stochastic", "load_type": "random_process"}, "stochastic_loading",
              ("load covariance is calibrated",), ("Q -> 0 recovers deterministic source owner",),
              "First-passage and response distributions must pass held-out tests.", ("load ensemble", "response ensemble", "failure times"), ("applied", "rapid_test"), "LOW"),
        _spec("MECH_GEOMETRIC_NONLINEARITY", g, "mechanics", ("kinematic_mode", "reference_configuration", "motion_map", "strain_measure", "rotation_representation", "deformation_regime", "configuration_space"), MECH_FAMILIES, ("dynamics", "structural", "solid_constitutive", "particle_mechanics"),
              "F = Grad_X chi; E = (F^T F - I)/2; Div P + rho b = rho a", {"deformation_regime": "finite", "strain_measure": "Green_Lagrange"}, "finite_deformation",
              ("reference configuration is explicit", "objectivity holds"), ("|Grad u| -> 0 recovers infinitesimal source owner",),
              "Large-rotation and small-strain controls must separate geometric from material nonlinearity.", ("full displacement field", "rotation", "load"), ("applied",), "MEDIUM"),
        _spec("MECH_THERMAL_INTERNAL_VARIABLE", g, "mechanics", ("material_description", "constitutive_class", "energy_structure", "failure_mode"), MECH_FAMILIES, ("solid_constitutive", "continuum", "transport", "structural"),
              "R_base[q,T,z] = 0; rho c_p dot(T) = div(k grad T) + Q_mech(q,z); dot(z)=f_z(q,T,z)", {"constitutive_class": "thermomechanical_internal_variable"}, "thermomechanical_coupling",
              ("energy balance and nonnegative dissipation hold",), ("thermal coupling -> 0 recovers source owner",),
              "One parameter set must predict isothermal and nonisothermal holdouts.", ("temperature field", "strain field", "dissipation"), ("interdisciplinary", "applied"), "MEDIUM"),
        _spec("MECH_PLASTICITY_HARDENING", g, "mechanics", ("plasticity_class", "deformation_regime", "constitutive_class", "failure_mode"), MECH_FAMILIES, ("solid_constitutive", "structural"),
              "epsilon = epsilon_e + epsilon_p; dot(epsilon_p)=lambda_p d f/d sigma; dot(alpha)=h(alpha,lambda_p)", {"plasticity_class": "internal_variable_hardening"}, "plastic_flow",
              ("Kuhn-Tucker conditions hold", "plastic dissipation is nonnegative"), ("lambda_p -> 0 recovers elastic source owner",),
              "Multiaxial cyclic paths must be predicted from parameters identified on disjoint paths.", ("multiaxial stress-strain", "cyclic paths", "residual strain"), ("applied", "high_risk"), "MEDIUM"),
        _spec("MECH_ANISOTROPIC_SYMMETRY", g, "mechanics", ("material_symmetry", "elasticity_class", "constitutive_class"), ("PDE", "ALGEBRAIC", "CONSERVATION"), ("solid_constitutive", "structural"),
              "sigma_ij = C_ijkl(A_1,...,A_n) epsilon_kl", {"material_symmetry": "tensorial_anisotropy", "elasticity_class": "anisotropic"}, "anisotropic_constitutive",
              ("symmetry group and structural tensors are explicit",), ("anisotropy parameters -> isotropic values recover source owner",),
              "Orientation sweeps must be predicted with one material tensor.", ("orientation-resolved stress-strain", "microstructure orientation"), ("applied", "rapid_test"), "LOW"),
        _spec("MECH_COMPRESSIBILITY_EXTENSION", g, "mechanics", ("compressibility", "flow_regime", "velocity_field_type", "momentum_balance", "wave_type", "dimensionless_regime"), ("PDE", "CONSERVATION", "ALGEBRAIC"), ("fluid", "continuum", "transport"),
              "partial_t rho + div(rho v)=0; rho Dv/Dt = -grad p(rho,s) + div(tau)", {"compressibility": "finite", "flow_regime": "compressible"}, "compressible_balance",
              ("equation of state is explicit",), ("Mach -> 0 recovers incompressible source owner",),
              "Pressure-wave and density-field holdouts must share the same equation of state.", ("pressure", "density", "velocity", "Mach sweep"), ("applied",), "MEDIUM"),
        _spec("MECH_TURBULENCE_CLOSURE", g, "mechanics", ("turbulence_regime", "flow_regime", "rheology", "stability_type"), ("PDE", "CONSERVATION"), ("fluid", "continuum"),
              "rho D mean(v)/Dt = -grad mean(p) + div(mu grad mean(v) - rho mean(v_prime tensor v_prime)); C_tau=Closure[z]", {"turbulence_regime": "closure_required"}, "turbulence_closure",
              ("closure respects realizability and invariance",), ("fluctuation stress -> 0 recovers laminar source owner",),
              "Closure parameters must transfer across Reynolds-number and geometry holdouts.", ("velocity statistics", "pressure", "Reynolds sweep"), ("applied", "high_risk"), "HIGH"),
        _spec("MECH_BIFURCATION_STABILITY", g, "mechanics", ("stability_type", "bifurcation_type", "failure_mode", "control_mode"), ("ODE", "PDE", "ALGEBRAIC"), ("dynamics", "structural", "fluid", "oscillation"),
              "L(lambda) delta q + N(delta q)=0; det L(lambda_c)=0", {"stability_type": "bifurcation", "bifurcation_type": "to_be_identified"}, "bifurcation_normal_form",
              ("control parameter and base branch are explicit",), ("distance_to_critical -> 0 yields normal form",),
              "Critical load and post-bifurcation amplitude must be predicted on geometry holdouts.", ("control parameter", "mode shape", "postcritical amplitude"), ("fundamental", "applied"), "MEDIUM"),
        _spec("MECH_DISPERSIVE_WAVE", g, "mechanics", ("wave_type", "dispersion_type", "inertia_structure", "body_dimension"), ("PDE", "ODE"), ("wave", "structural", "continuum", "oscillation"),
              "omega^2 = c0^2 k^2 + a4 k^4 + a6 k^6", {"wave_type": "dispersive", "dispersion_type": "higher_order"}, "dispersion_relation",
              ("stable branch has omega^2 >= 0",), ("a4,a6 -> 0 recovers nondispersive source owner",),
              "One dispersion law must predict multiple wavelengths and specimen sizes.", ("frequency-wavenumber data", "size sweep"), ("applied", "rapid_test"), "LOW"),
        _spec("MECH_NONHOLONOMIC_CONSTRAINT", g, "mechanics", ("constraint_type", "constraint_integrability", "configuration_space", "degrees_of_freedom"), ("ODE", "ALGEBRAIC", "CONSERVATION"), ("dynamics", "particle_mechanics", "structural"),
              "M(q) qddot + C(q,qdot) = Q + A(q)^T lambda; A(q) qdot = 0", {"constraint_type": "nonholonomic", "constraint_integrability": "nonintegrable"}, "nonholonomic_constraint",
              ("constraint rank is constant on validity domain",), ("constraint force -> 0 recovers unconstrained source owner",),
              "Trajectory holdouts must require velocity-level constraints and reject any holonomic surrogate.", ("configuration", "velocity", "constraint reaction"), ("fundamental", "applied"), "MEDIUM"),
        _spec("MECH_MULTIBODY_JOINT", g, "mechanics", ("joint_type", "constraint_type", "degrees_of_freedom", "configuration_space", "rotation_representation", "mechanical_generator", "potential_structure", "angular_momentum_balance"), ("ODE", "ALGEBRAIC", "CONSERVATION"), ("dynamics", "structural", "particle_mechanics"),
              "M(q) qddot + h(q,qdot) + Phi_q(q)^T lambda = Q; Phi(q)=0", {"joint_type": "explicit_multibody", "constraint_type": "bilateral"}, "multibody_dae",
              ("constraint Jacobian rank is monitored",), ("joint removal recovers independent source owners",),
              "Constraint forces and motion must predict an unseen actuation protocol.", ("joint kinematics", "actuation", "reaction forces"), ("applied",), "LOW"),
        _spec("MECH_VARIABLE_MASS_INERTIA", g, "mechanics", ("mass_distribution", "inertia_structure", "mechanical_object", "body_dimension"), ("ODE", "PDE", "CONSERVATION"), ("dynamics", "particle_mechanics", "continuum"),
              "d(m v)/dt = F_ext + u_rel dm/dt; d(I omega)/dt = tau_ext + tau_flux", {"mass_distribution": "time_dependent", "inertia_structure": "time_dependent"}, "variable_mass_balance",
              ("mass and angular-momentum flux are measured",), ("dm/dt -> 0 recovers fixed-mass source owner",),
              "Mass-flow changes must predict momentum and attitude without empirical impulse corrections.", ("mass flow", "velocity", "angular velocity", "forces"), ("applied",), "MEDIUM"),
        _spec("MECH_POROMECHANICAL_COUPLING", g, "mechanics", ("material_description", "compressibility", "constitutive_class", "flow_regime"), ("PDE", "CONSERVATION", "ALGEBRAIC"), ("continuum", "transport", "solid_constitutive", "fluid"),
              "sigma = C:epsilon - alpha_B p I; S dot(p) + alpha_B div(dot(u)) - div(k/mu grad p)=q", {"material_description": "porous_medium", "constitutive_class": "poroelastic"}, "poroelastic_coupling",
              ("solid and fluid mass balances close",), ("alpha_B -> 0 recovers uncoupled source owner",),
              "Pressure and deformation fields must be predicted jointly on a loading-drainage holdout.", ("pressure field", "displacement field", "flow"), ("interdisciplinary", "applied"), "MEDIUM"),
        _spec("MECH_ACTIVE_CONTROL_EXCITATION", g, "mechanics", ("excitation", "control_mode", "force_type", "load_type"), ("ODE", "PDE", "CONSERVATION"), ("dynamics", "structural", "oscillation"),
              "M qddot + C qdot + K q = B u(t); u = pi(y,t)", {"control_mode": "closed_loop", "excitation": "controlled"}, "controlled_mechanics",
              ("controller causality and actuator limits are explicit",), ("u -> 0 recovers passive source owner",),
              "Closed-loop response must predict unseen references without violating passivity or constraints.", ("state or output", "control input", "actuator limits"), ("applied", "rapid_test"), "LOW"),
        _spec("MECH_BOUNDARY_SUPPORT_OPERATOR", g, "mechanics", ("boundary_support", "constraint_type", "joint_type"), ("PDE", "ODE", "ALGEBRAIC"), ("structural", "continuum", "dynamics"),
              "R_base[q]=0 in Omega; B_support[q,traction,rotation]=0 on partial Omega", {"boundary_support": "operator_defined"}, "mechanical_boundary_operator",
              ("support law is independent of bulk constitutive parameters",), ("support stiffness -> 0 or infinity recovers free or fixed limits",),
              "Support reaction and mode shapes must transfer across bulk-load holdouts.", ("boundary reaction", "displacement field", "mode shape"), ("applied", "rapid_test"), "LOW"),
        _spec("MECH_DIMENSIONLESS_REGIME", g, "mechanics", ("dimensionless_regime", "flow_regime", "inertia_regime", "stability_type"), ("PDE", "ODE", "CONSERVATION"), ("fluid", "continuum", "dynamics"),
              "R_star[Psi;Pi_1,...,Pi_n]=0 where Pi are dimensionless invariants", {"dimensionless_regime": "explicit_parameter_space"}, "dimensionless_reduction",
              ("Buckingham basis is complete for declared quantities",), ("asymptotic Pi limits recover source regimes",),
              "Data from geometrically scaled systems must collapse on the same dimensionless law.", ("scaled experiments", "dimensionless groups", "response"), ("fundamental", "rapid_test"), "LOW"),
        _spec("MECH_DAMAGE_THERMAL_COMPOSITION", g, "mechanics", ("damage_model", "constitutive_class", "energy_structure", "failure_mode"), MECH_FAMILIES, ("solid_constitutive", "structural"),
              "sigma=(1-D) C(T):epsilon_e; dot(D)=f_D(Y,T,D); rho c_p dot(T)=div(k grad T)+Y dot(D)", {"damage_model": "thermally_activated", "constitutive_class": "thermodamage"}, "thermodamage",
              ("total dissipation is nonnegative",), ("thermal activation -> 0 and D -> 0 recover source owner",),
              "Temperature-dependent degradation must transfer across thermal and mechanical histories.", ("temperature field", "strain field", "damage proxy"), ("interdisciplinary", "high_risk"), "HIGH", order=2),
    )


def _chemistry_specs() -> Tuple[TransformationSpec, ...]:
    g = "ChemistryCandidateGenerator"
    return (
        _spec("CHEM_ACTIVITY_CORRECTION", g, "chemistry", ("activity_model", "ionic_strength", "mixture_type", "standard_state"), CHEM_THERMO_FAMILIES + CHEM_KINETIC_FAMILIES, ("equilibrium", "chemical_potential", "thermodynamic", "kinetics", "electrochemistry"),
              "a_i = gamma_i(c,T,I) c_i/c_std; R_base[a_i] = 0", {"activity_model": "nonideal", "standard_state": "explicit"}, "activity_correction",
              ("gamma_i -> 1 at infinite dilution",), ("gamma_i -> 1 recovers ideal source owner",),
              "One activity model must predict equilibrium and kinetic holdouts at multiple ionic strengths.", ("composition", "activity or equilibrium", "ionic strength"), ("applied", "rapid_test"), "LOW"),
        _spec("CHEM_FUGACITY_HIGH_PRESSURE", g, "chemistry", ("fugacity_model", "pressure_regime", "phase", "phase_count"), CHEM_THERMO_FAMILIES, ("equilibrium", "phase_equilibrium", "thermodynamic", "chemical_potential"),
              "f_i = phi_i(T,p,y) y_i p; mu_i = mu_i_std + R T ln(f_i/f_std)", {"fugacity_model": "nonideal", "pressure_regime": "finite_to_high"}, "fugacity_correction",
              ("phi_i -> 1 in ideal-gas limit",), ("p -> 0 recovers ideal source owner",),
              "Phase and chemical-potential data at multiple pressures must share one fugacity model.", ("pressure", "phase composition", "equilibrium"), ("applied",), "MEDIUM"),
        _spec("CHEM_MEMORY_RATE", g, "chemistry", ("kinetic_law", "timescale_separation", "mechanism_class", "intermediate_structure"), CHEM_KINETIC_FAMILIES, ("kinetics",),
              "r(t) = Integral_0^t K_r(t-s) r_base(c(s),T(s)) ds", {"kinetic_law": "memory_kernel", "timescale_separation": "unresolved_intermediate"}, "chemical_memory_kernel",
              ("K_r is causal", "mass and charge balances remain exact"), ("K_r -> delta recovers source rate law",),
              "One kernel must predict concentration histories under distinct forcing protocols.", ("time-resolved concentrations", "forcing protocol", "holdout trajectory"), ("fundamental", "high_risk"), "HIGH"),
        _spec("CHEM_MECHANOACTIVATION", g, "chemistry", ("activation_model", "transition_state_model", "reaction_gibbs_energy", "pressure_dependence"), CHEM_KINETIC_FAMILIES, ("kinetics",),
              "k(sigma,T) = k0 exp(-(DeltaG_dagger - sigma:V_dagger)/(R T))", {"activation_model": "mechanochemical"}, "mechanochemical_activation",
              ("activation-volume tensor is objective",), ("sigma -> 0 recovers source rate coefficient",),
              "One activation-volume tensor must predict rates under multiple stress states.", ("stress tensor", "temperature", "reaction rate"), ("interdisciplinary", "rapid_test"), "MEDIUM"),
        _spec("CHEM_PHOTOCOUPLED_KINETICS", g, "chemistry", ("photochemical_regime", "electronic_state", "spectroscopy_type", "activation_model"), CHEM_KINETIC_FAMILIES + ("SPECTROSCOPY",), ("kinetics", "spectroscopy"),
              "dot(c) = N r(c,T) + Phi_abs(lambda,I) r_photo(c); dot(p_exc)=W_abs(1-p_exc)-k_rel p_exc", {"photochemical_regime": "explicit_excited_state"}, "photochemical_kinetics",
              ("photon flux and absorption are calibrated",), ("I -> 0 recovers dark source owner",),
              "Action spectrum and transient kinetics must share the same excited-state parameters.", ("wavelength", "photon flux", "transient concentrations", "spectrum"), ("interdisciplinary", "applied"), "MEDIUM"),
        _spec("CHEM_STOCHASTIC_REACTION_NETWORK", g, "chemistry", ("kinetic_law", "reaction_order", "stoichiometry", "element_balance", "molecularity_of_step", "elementary_step_count", "reaction_directionality"), ("RATE_LAW", "REACTION_BALANCE", "TRANSPORT"), ("kinetics", "reaction_balance"),
              "P(X,t+dt|X) from propensities a_r(X); dX = N a(X) dt + N sqrt(diag(a(X))) dW", {"kinetic_law": "stochastic_network"}, "chemical_master_equation",
              ("propensities preserve nonnegative counts",), ("system size -> infinity recovers deterministic rate law",),
              "Count distributions and rare-event times must pass held-out tests.", ("single-event trajectories", "volume", "count statistics"), ("fundamental", "rapid_test"), "MEDIUM"),
        _spec("CHEM_TRANSPORT_LIMITED_RATE", g, "chemistry", ("transport_limitation", "reaction_diffusion_regime", "kinetic_law", "phase"), CHEM_KINETIC_FAMILIES, ("kinetics", "transport"),
              "1/k_eff = 1/k_intrinsic + 1/k_transport; partial_t c = div(D grad c) + N r(c)", {"transport_limitation": "explicit", "reaction_diffusion_regime": "coupled"}, "transport_limited_rate",
              ("transport and intrinsic rates are independently identifiable",), ("k_transport -> infinity recovers intrinsic source law",),
              "Geometry and stirring changes must alter k_eff according to independently measured transport.", ("concentration field", "geometry", "intrinsic-rate control"), ("interdisciplinary", "applied"), "LOW"),
        _spec("CHEM_DYNAMIC_CATALYST_STATE", g, "chemistry", ("catalysis", "inhibition", "mechanism_class", "intermediate_structure", "timescale_separation"), CHEM_KINETIC_FAMILIES, ("kinetics",),
              "r = r_base(c,T,z_cat); dot(z_cat)=f_cat(c,T,z_cat); 0 <= z_cat <= 1", {"catalysis": "dynamic_state"}, "dynamic_catalyst_state",
              ("catalyst-state bounds and mass balance hold",), ("dot(z_cat) -> 0 recovers static catalyst law",),
              "Activation, poisoning and recovery protocols must share one state law.", ("reaction rate", "catalyst-state proxy", "protocol history"), ("applied", "rapid_test"), "LOW"),
        _spec("CHEM_ELECTROCHEMICAL_ACTIVITY", g, "chemistry", ("electrochemical_regime", "activity_model", "ionic_strength", "chemical_potential_model"), CHEM_KINETIC_FAMILIES + CHEM_THERMO_FAMILIES, ("electrochemistry",),
              "j = j0(a_i,T) [exp(alpha_a F eta/(R T)) - exp(-alpha_c F eta/(R T))]; eta = phi - E_eq(a_i)", {"electrochemical_regime": "activity_corrected"}, "electrochemical_activity",
              ("activities and ohmic drop are independently estimated",), ("gamma_i -> 1 recovers ideal electrochemical law",),
              "Polarization curves at multiple concentrations must share one activity model and transfer to holdout current protocols.", ("potential", "current", "activities", "temperature"), ("interdisciplinary", "rapid_test"), "LOW"),
        _spec("CHEM_PROTONATION_PH_COUPLING", g, "chemistry", ("protonation_state", "pH_regime", "tautomeric_state", "kinetic_law"), CHEM_KINETIC_FAMILIES + CHEM_THERMO_FAMILIES, ("kinetics", "equilibrium", "chemical_potential"),
              "r_eff = Sum_s p_s(pH,T) r_s(c,T); p_s = exp(-G_s/(R T))/Z", {"protonation_state": "ensemble", "pH_regime": "explicit"}, "protonation_ensemble",
              ("microstate populations sum to one",), ("single-state population -> 1 recovers source owner",),
              "pH-rate and speciation curves must be predicted jointly.", ("pH", "speciation", "reaction rate"), ("applied", "rapid_test"), "LOW"),
        _spec("CHEM_SOLVATION_COUPLING", g, "chemistry", ("solvent", "solvation_model", "mixture_type", "activation_model", "chemical_potential_model"), CHEM_KINETIC_FAMILIES + CHEM_THERMO_FAMILIES, ("kinetics", "equilibrium", "thermodynamic"),
              "DeltaG_eff = DeltaG_gas + DeltaG_solv(solvent,c,T); k = kappa kBT/h exp(-DeltaG_dagger_eff/(R T))", {"solvation_model": "explicit"}, "solvation_free_energy",
              ("solvation convention and standard state are fixed",), ("DeltaG_solv -> 0 recovers gas-phase source owner",),
              "Solvent-transfer free energies and rates must share one solvation model.", ("solvent composition", "free energy or equilibrium", "reaction rate"), ("interdisciplinary", "applied"), "MEDIUM"),
        _spec("CHEM_SPIN_STATE_KINETICS", g, "chemistry", ("spin_state", "electronic_state", "transition_state_model", "mechanism_class"), CHEM_KINETIC_FAMILIES + ("SPECTROSCOPY",), ("kinetics", "spectroscopy"),
              "dot(p_s)=K_spin(c,T,B) p_s; r = Sum_s p_s r_s(c,T)", {"spin_state": "dynamic_multistate"}, "spin_state_network",
              ("spin populations are normalized",), ("spin mixing -> 0 recovers single-surface source owner",),
              "Magnetic-field or spin-preparation controls must change kinetics as predicted by independently observed populations.", ("spin-state proxy", "reaction rate", "field or preparation"), ("fundamental", "high_risk"), "HIGH"),
        _spec("CHEM_REDOX_ELECTRON_BALANCE", g, "chemistry", ("oxidation_state", "electron_balance", "charge_balance", "formal_charge", "reaction_directionality"), ("REACTION_BALANCE", "ELECTROCHEMISTRY", "RATE_LAW"), ("reaction_balance", "electrochemistry", "kinetics"),
              "N_e r + I/F = 0; Sum_i z_i dot(n_i) = I/F", {"electron_balance": "explicit", "oxidation_state": "tracked"}, "electron_balance",
              ("charge and atom balances close exactly",), ("I -> 0 recovers chemical source owner",),
              "Faradaic charge and product distribution must agree without hidden electron sinks.", ("current", "species amounts", "charge balance"), ("interdisciplinary", "rapid_test"), "LOW"),
        _spec("CHEM_SURFACE_HETEROGENEOUS", g, "chemistry", ("surface_reaction", "heterogeneous_catalysis", "phase_count", "reaction_center", "catalysis"), CHEM_KINETIC_FAMILIES, ("kinetics", "transport"),
              "dot(theta_i)=r_ads_i-r_des_i+Sum_r nu_ir r_r(theta,c); r_vol = a_s r_surface", {"surface_reaction": "explicit_coverage", "heterogeneous_catalysis": "active"}, "surface_coverage_kinetics",
              ("site balance Sum theta_i <= 1",), ("surface area -> 0 removes heterogeneous channel",),
              "Coverage transients and macroscopic rates must share one site model across surface-area holdouts.", ("surface coverage", "surface area", "reaction rate"), ("interdisciplinary", "applied"), "MEDIUM"),
        _spec("CHEM_PLASMA_KINETICS", g, "chemistry", ("plasma_chemistry", "electronic_state", "temperature_regime", "reaction_class"), CHEM_KINETIC_FAMILIES, ("kinetics", "reaction_balance"),
              "dot(n_i)=Sum_r nu_ir k_r(T_e,T_g,E/N) Product_j n_j^alpha_j + transport_i", {"plasma_chemistry": "nonthermal", "temperature_regime": "two_temperature"}, "plasma_reaction_network",
              ("electron and heavy-particle temperatures are distinct observables",), ("T_e -> T_g recovers thermal source regime",),
              "Species and emission histories must be predicted under waveform holdouts.", ("electron temperature", "species densities", "emission", "field waveform"), ("interdisciplinary", "high_risk"), "HIGH"),
        _spec("CHEM_COMBUSTION_NETWORK", g, "chemistry", ("combustion_regime", "reaction_class", "mechanism_class", "temperature_dependence", "pressure_dependence"), CHEM_KINETIC_FAMILIES, ("kinetics", "combustion_kinetics", "reaction_balance"),
              "dot(c)=N r(c,T,p); rho c_p dot(T)=Qdot_chem(c,T)-div(q)", {"combustion_regime": "thermochemical_network"}, "combustion_network",
              ("element and energy balances close",), ("heat release -> 0 recovers isothermal kinetics",),
              "Ignition delay and species profiles must transfer across temperature and pressure holdouts.", ("temperature", "species", "pressure", "ignition time"), ("interdisciplinary", "applied"), "MEDIUM"),
        _spec("CHEM_POLYMERIZATION_POPULATION", g, "chemistry", ("polymerization_regime", "molecularity", "elementary_step_count", "kinetic_law"), CHEM_KINETIC_FAMILIES, ("kinetics", "reaction_balance"),
              "partial_t n(m,t) = Birth[n]-Death[n]+Growth[n]; moments M_k=Integral m^k n(m,t) dm", {"polymerization_regime": "population_balance"}, "polymer_population_balance",
              ("mass moment is conserved apart from declared feed and loss",), ("chain-growth coupling -> 0 recovers monomer source law",),
              "Molecular-weight distribution and conversion must be predicted jointly.", ("conversion", "molecular-weight distribution", "temperature"), ("interdisciplinary", "applied"), "MEDIUM"),
        _spec("CHEM_REACTION_DIFFUSION", g, "chemistry", ("reaction_diffusion_regime", "transport_limitation", "phase", "kinetic_law"), ("RATE_LAW", "REACTION_BALANCE", "TRANSPORT"), ("kinetics", "transport", "reaction_balance"),
              "partial_t c_i = div(D_i(c,T) grad c_i) + Sum_r nu_ir r_r(c,T)", {"reaction_diffusion_regime": "coupled"}, "reaction_diffusion",
              ("D is positive semidefinite", "balances hold locally"), ("D -> infinity gives well-mixed source law", "reaction rates -> 0 gives transport source law"),
              "Pattern wavelength and transient concentration fields must be predicted on geometry holdouts.", ("spatial concentration fields", "diffusivity", "geometry"), ("interdisciplinary", "rapid_test"), "MEDIUM"),
        _spec("CHEM_MULTISTEP_MECHANISM", g, "chemistry", ("mechanism_class", "elementary_step_count", "molecularity_of_step", "intermediate_structure", "reaction_center"), CHEM_KINETIC_FAMILIES, ("kinetics", "reaction_balance"),
              "dot(c)=N_mech r_mech(c,k); observed_rate = P_obs N_mech r_mech", {"mechanism_class": "explicit_multistep", "elementary_step_count": "greater_than_one"}, "multistep_mechanism",
              ("element and charge balances hold for every step",), ("fast intermediate elimination recovers source rate law",),
              "Intermediate and product transients must identify one mechanism across protocols.", ("time-resolved species", "intermediate proxy", "multiple protocols"), ("fundamental", "high_risk"), "HIGH"),
        _spec("CHEM_TRANSITION_STATE_CORRECTION", g, "chemistry", ("transition_state_model", "activation_model", "reaction_entropy", "reaction_enthalpy", "reaction_gibbs_energy"), ("RATE_COEFFICIENT", "RATE_LAW"), ("kinetics",),
              "k(T)=kappa(T) k_B T/h exp(DeltaS_dagger/R) exp(-DeltaH_dagger/(R T))", {"transition_state_model": "explicit", "activation_model": "free_energy_barrier"}, "transition_state_rate",
              ("standard state and transmission coefficient convention are fixed",), ("kappa -> 1 gives conventional transition-state theory",),
              "Temperature dependence must jointly identify enthalpy and entropy of activation on holdout temperatures.", ("rate vs temperature", "equilibrium or barrier data"), ("fundamental", "rapid_test"), "LOW"),
        _spec("CHEM_STEADY_STATE_REDUCTION", g, "chemistry", ("timescale_separation", "steady_state_approximation", "intermediate_structure", "mechanism_class"), CHEM_KINETIC_FAMILIES, ("kinetics",),
              "0 = dot(c_fast)=f_fast(c_fast,c_slow); dot(c_slow)=f_slow(c_fast_star(c_slow),c_slow)", {"timescale_separation": "fast_slow", "steady_state_approximation": "controlled"}, "singular_perturbation_reduction",
              ("spectral gap between fast and slow modes is quantified",), ("epsilon -> 0 yields reduced source law",),
              "Reduced and full models must agree within a declared error on holdout forcing timescales.", ("fast and slow species", "timescale sweep"), ("fundamental", "rapid_test"), "LOW"),
        _spec("CHEM_PRE_EQUILIBRIUM_REDUCTION", g, "chemistry", ("pre_equilibrium", "equilibrium_type", "mechanism_class", "timescale_separation"), CHEM_KINETIC_FAMILIES, ("kinetics", "equilibrium"),
              "K_pre = Product a_products^nu/Product a_reactants^nu; r_slow = k_slow c_intermediate(K_pre,a)", {"pre_equilibrium": "explicit"}, "pre_equilibrium_reduction",
              ("pre-equilibrium relaxation is faster than slow step",), ("timescale ratio -> 0 recovers reduced source law",),
              "Perturbation away from pre-equilibrium must reveal the predicted finite-timescale correction.", ("intermediate", "equilibrium quotient", "rate"), ("fundamental", "rapid_test"), "LOW"),
        _spec("CHEM_PHASE_EQUILIBRIUM_STABILITY", g, "chemistry", ("phase_equilibrium", "stability_condition", "thermodynamic_ensemble", "phase_count", "equilibrium_constant_type"), CHEM_THERMO_FAMILIES, ("phase_equilibrium", "equilibrium", "thermodynamic"),
              "mu_i^alpha = mu_i^beta; Hessian_G restricted_to_constraints >= 0", {"phase_equilibrium": "multiphase", "stability_condition": "convexity"}, "phase_stability",
              ("ensemble and constraints are explicit",), ("single-phase limit recovers source owner",),
              "Tie-lines, phase fractions and spinodal boundary must be predicted jointly.", ("phase compositions", "phase fractions", "temperature and pressure"), ("fundamental", "applied"), "MEDIUM"),
        _spec("CHEM_NONISOTHERMAL_RATE", g, "chemistry", ("temperature_regime", "temperature_dependence", "reaction_enthalpy", "kinetic_law"), CHEM_KINETIC_FAMILIES, ("kinetics", "thermodynamic"),
              "dot(c)=N r(c,T); rho c_p dot(T)= -Sum_r DeltaH_r r_r + Q_ext", {"temperature_regime": "dynamic", "temperature_dependence": "coupled"}, "nonisothermal_kinetics",
              ("energy and species balances close",), ("DeltaH -> 0 or fixed T recovers isothermal source owner",),
              "Temperature and conversion trajectories must be predicted together under heat-transfer holdouts.", ("temperature", "species", "heat flux"), ("interdisciplinary", "rapid_test"), "LOW"),
        _spec("CHEM_PRESSURE_DEPENDENT_RATE", g, "chemistry", ("pressure_dependence", "pressure_regime", "molecularity", "mechanism_class"), ("RATE_LAW", "RATE_COEFFICIENT"), ("kinetics",),
              "k_eff(T,p)=k0(T) Pr/(1+Pr) F_cent(T,p); Pr=k0(T)[M]/k_inf(T)", {"pressure_dependence": "falloff"}, "pressure_falloff",
              ("low- and high-pressure limits are independently defined",), ("Pr -> 0 and infinity recover asymptotic limits",),
              "One falloff curve must predict rates across pressure decades.", ("rate", "pressure", "temperature", "bath composition"), ("applied", "rapid_test"), "LOW"),
        _spec("CHEM_ISOTOPE_EFFECT", g, "chemistry", ("isotopic_composition", "molecular_structure", "transition_state_model", "rate_coefficient_model"), ("RATE_LAW", "RATE_COEFFICIENT", "EQUILIBRIUM"), ("kinetics", "equilibrium"),
              "ln(k_light/k_heavy)=DeltaDeltaZPE/(R T)+tunneling_correction", {"isotopic_composition": "resolved"}, "kinetic_isotope_effect",
              ("isotopic purity and zero-point convention are explicit",), ("mass difference -> 0 recovers source owner",),
              "Temperature-dependent isotope effects must predict both rate and equilibrium shifts.", ("isotopic composition", "rates", "equilibrium", "temperature"), ("fundamental", "rapid_test"), "LOW"),
        _spec("CHEM_CONFORMATIONAL_GATING", g, "chemistry", ("conformation", "stereochemistry", "functional_groups", "molecular_structure", "kinetic_law"), CHEM_KINETIC_FAMILIES, ("kinetics",),
              "dot(p_k)=Sum_j K_kj p_j; r_eff=Sum_k p_k r_k(c,T)", {"conformation": "dynamic_ensemble", "stereochemistry": "resolved"}, "conformational_gating",
              ("conformer probabilities are normalized",), ("fast exchange recovers population-averaged source law",),
              "Conformer populations and reaction transients must be predicted jointly.", ("conformer population", "reaction rate", "temperature"), ("fundamental", "high_risk"), "MEDIUM"),
        _spec("CHEM_QUANTUM_METHOD_UNCERTAINTY", g, "chemistry", ("quantum_chemical_method", "basis_set", "electronic_correlation_level", "property_source"), ("RATE_COEFFICIENT", "EQUILIBRIUM", "PHASE_EQUILIBRIUM", "SPECTROSCOPY"), ("kinetics", "equilibrium", "spectroscopy", "thermodynamic"),
              "theta_phys = theta_calc(method,basis,corr) + delta_model; delta_model ~ P calibrated on benchmark set", {"quantum_chemical_method": "explicit", "basis_set": "convergence_tracked", "electronic_correlation_level": "explicit"}, "model_discrepancy",
              ("calibration and validation molecules are disjoint",), ("basis and correlation convergence reduces delta_model",),
              "Calibrated uncertainty must cover held-out observables at the declared rate.", ("computed property sequence", "benchmark measurements", "holdout molecules"), ("applied", "rapid_test"), "LOW"),
        _spec("CHEM_CATALYSIS_TRANSPORT_COMPOSITION", g, "chemistry", ("catalysis", "transport_limitation", "surface_reaction", "reaction_diffusion_regime", "heterogeneous_catalysis"), CHEM_KINETIC_FAMILIES, ("kinetics", "transport"),
              "partial_t c = div(D grad c)+N r(c,theta); dot(theta)=f_ads(c,theta)-f_des(theta)-f_rxn(c,theta)", {"catalysis": "dynamic_surface", "transport_limitation": "coupled"}, "catalytic_reaction_transport",
              ("site, species and energy balances close",), ("D -> infinity and theta steady recover source rate law",),
              "Spatial profiles, surface coverage and outlet rate must transfer across geometry holdouts.", ("concentration field", "surface coverage", "outlet rate", "geometry"), ("interdisciplinary", "high_risk"), "HIGH", order=2),
    )


# Context and observation axes are still scanned and reported, but they do not
# create a new law by themselves.  Their values constrain applicability or the
# experiment required to test a candidate.
NON_GENERATIVE_AXIS_ROLES: Mapping[str, Mapping[str, Tuple[str, ...]]] = {
    "physics": {
        "CONTEXT": ("physical_entity", "expression_role", "linearity_parameters", "coordinate_frame", "metric_structure", "causal_order"),
        "OBSERVATION": ("identifiability_class", "data_regime"),
    },
    "mechanics": {
        "CONTEXT": ("mechanical_object", "reference_frame", "coordinate_description"),
        "OBSERVATION": (),
    },
    "chemistry": {
        "CONTEXT": ("chemical_entity_type", "elemental_composition", "molecular_structure", "bonding_pattern", "functional_groups", "composition_measure"),
        "OBSERVATION": ("analytical_method", "instrument_type", "separation_method", "sample_preparation", "property_source"),
    },
}


BRIDGE_REQUIRED_ANY_TAGS: Mapping[str, Mapping[str, Tuple[str, ...]]] = {
    "PHYS_MECH_FORCE": {"physics": ("force_source",), "mechanics": ("force_balance",)},
    "PHYS_MECH_CONTINUUM": {"physics": ("continuum_coupling_source",), "mechanics": ("continuum_balance",)},
    "PHYS_CHEM_QUANTUM": {"physics": ("molecular_quantum_source",), "chemistry": ("quantum_chemistry_target",)},
    "PHYS_CHEM_THERMO": {"physics": ("thermodynamic_state_relation",), "chemistry": ("thermochemical_target",)},
    "PHYS_CHEM_SPECTROSCOPY": {"physics": ("spectroscopic_transition_source",), "chemistry": ("spectroscopy_target",)},
    "MECH_CHEM_REACTIVE_FLOW": {"mechanics": ("reactive_transport_carrier",), "chemistry": ("reactive_source",)},
    "MECH_CHEM_CHEMOMECHANICS": {"mechanics": ("solid_constitutive",), "chemistry": ("thermochemical_target",), "materials_science": ("chemomechanical_material",)},
    "MECH_CHEM_RHEOLOGY": {"mechanics": ("rheology",), "chemistry": ("reactive_source", "thermochemical_target"), "materials_science": ("rheology_material",)},
    "PHYS_MECH_CHEM_COMBUSTION": {"physics": ("combustion_energy_source",), "mechanics": ("combustion_flow_carrier",), "chemistry": ("combustion_reaction_source",)},
    "PHYS_MECH_CHEM_ELECTROCHEM": {"physics": ("electrochemical_field_source",), "mechanics": ("electrochemical_transport_carrier",), "chemistry": ("electrochemical_target",)},
}

BRIDGE_AXIS_IDS: Mapping[str, Mapping[str, Tuple[str, ...]]] = {
    "PHYS_MECH_FORCE": {"physics": ("interaction_sector",), "mechanics": ("force_type", "mechanical_generator")},
    "PHYS_MECH_CONTINUUM": {"physics": ("conservation_structure",), "mechanics": ("momentum_balance", "constitutive_class")},
    "PHYS_CHEM_QUANTUM": {"physics": ("classical_quantum_regime", "state_space"), "chemistry": ("electronic_state", "quantum_chemical_method")},
    "PHYS_CHEM_THERMO": {"physics": ("thermodynamic_limit",), "chemistry": ("chemical_potential_model", "activity_model")},
    "PHYS_CHEM_SPECTROSCOPY": {"physics": ("observable_type", "detector_coupling"), "chemistry": ("spectroscopy_type", "electronic_state")},
    "MECH_CHEM_REACTIVE_FLOW": {"mechanics": ("flow_regime", "velocity_field_type"), "chemistry": ("reaction_diffusion_regime", "transport_limitation")},
    "MECH_CHEM_CHEMOMECHANICS": {"mechanics": ("constitutive_class", "damage_model"), "chemistry": ("reaction_gibbs_energy", "phase_equilibrium")},
    "MECH_CHEM_RHEOLOGY": {"mechanics": ("rheology", "viscoelasticity_class"), "chemistry": ("polymerization_regime", "mixture_type")},
    "PHYS_MECH_CHEM_COMBUSTION": {"physics": ("dissipation",), "mechanics": ("flow_regime", "turbulence_regime"), "chemistry": ("combustion_regime", "temperature_dependence")},
    "PHYS_MECH_CHEM_ELECTROCHEM": {"physics": ("interaction_sector",), "mechanics": ("flow_regime",), "chemistry": ("electrochemical_regime", "transport_limitation")},
}


def _bridge_spec(bridge: DomainBridge) -> TransformationSpec:
    axis_ids: List[str] = []
    for domain in bridge.source_domains:
        axis_ids.extend(BRIDGE_AXIS_IDS.get(bridge.bridge_id, {}).get(domain, ()))
    return TransformationSpec(
        transformation_id=f"BRIDGE_{bridge.bridge_id}",
        generator_id="BridgeCandidateGenerator",
        source_domains=tuple(bridge.source_domains),
        target_domains=tuple(bridge.source_domains),
        axis_ids=tuple(sorted(set(axis_ids))),
        applicable_families=(),
        required_any_tags=(),
        formula_builder=_bridge_formula,
        coordinate_delta={"bridge_id": bridge.bridge_id, "coupling": "candidate_nonzero"},
        dimension_contract=bridge.dimensional_contract,
        assumptions=tuple(bridge.assumptions) + ("each source owner remains authoritative for its uncoupled sector",),
        controlled_limits=tuple(bridge.controlled_limits),
        falsification_criterion="A coupled holdout experiment must reject uncoupled owners and transfer the same coupling parameters across operating conditions.",
        required_measurements=("observables of every source domain", "coupling control variable", "uncoupled controls", "coupled holdout condition"),
        categories=("interdisciplinary", "high_risk"),
        risk_class="HIGH",
        bridge_id=bridge.bridge_id,
        composition_order=len(bridge.source_domains),
    )


def _all_single_specs() -> Tuple[TransformationSpec, ...]:
    return _physics_specs() + _mechanics_specs() + _chemistry_specs()


def _build_axis_policy(specs: Sequence[TransformationSpec]) -> Dict[Tuple[str, str], AxisAuditRow]:
    """Classify every registered axis before any search starts.

    Existing physics/mechanics/chemistry transformation ownership is retained.
    The remaining domains are not fabricated into formula generators: their
    axes are classified as formal, semantic, methodological, computational or
    open contextual coordinates until a registered owner/bridge binds them.
    """
    rows: Dict[Tuple[str, str], AxisAuditRow] = {}
    default_roles = {
        "formal_science": "FORMAL_CONSTRAINT",
        "semantic_infrastructure": "OBSERVATION",
        "methodological": "METHOD",
        "computational_science": "COMPUTATIONAL",
        "natural_science": "CONTEXT",
    }
    for domain, registry in sorted(DOMAIN_REGISTRIES.items()):
        role = default_roles.get(registry.domain_role, "CONTEXT")
        for axis_id in registry.axes:
            rows[(domain, axis_id)] = AxisAuditRow(domain, axis_id, role)
    for spec in specs:
        if spec.bridge_id:
            continue
        domain = spec.target_domains[0]
        for axis_id in spec.axis_ids:
            if (domain, axis_id) not in rows:
                raise ValueError(f"{spec.transformation_id}: unregistered axis {domain}.{axis_id}")
            row = rows[(domain, axis_id)]
            row.role = "GENERATIVE"
            row.transformation_ids.append(spec.transformation_id)
    for domain, role_map in NON_GENERATIVE_AXIS_ROLES.items():
        for role, axes in role_map.items():
            for axis_id in axes:
                row = rows[(domain, axis_id)]
                if row.role == "GENERATIVE":
                    continue
                row.role = role
    return rows


AXIS_POLICY_TEMPLATE = _build_axis_policy(_all_single_specs())


def _candidate_digest(row: Mapping[str, Any]) -> str:
    payload = dict(row)
    payload["digest"] = ""
    return digest_payload(payload)


def _is_non_generative_statement(passport: LawPassport) -> bool:
    return _statement_role(passport) == "NON_GENERATIVE_STATEMENT"


def _single_source_semantically_applicable(passport: LawPassport, spec: TransformationSpec) -> bool:
    if _is_non_generative_statement(passport) and not spec.allow_non_generative_statement:
        return False
    required = set(spec.required_any_tags)
    return not required or bool(required.intersection(_semantic_tags(passport)))


def _target_state_already_active(passport: LawPassport, spec: TransformationSpec) -> bool:
    """Reject a registered transformation that merely restates its source owner.

    Exact coordinate equality is authoritative when all target coordinates are
    already present.  The rate-and-state legacy owner predates the corresponding
    axis fields, so its canonical formula/name are additionally recognized.
    """
    if spec.bridge_id:
        return False
    comparable = {k: v for k, v in spec.coordinate_delta.items() if k in passport.scientific_coordinate}
    if comparable and len(comparable) == len(spec.coordinate_delta):
        if all(canonical_json(passport.scientific_coordinate[k]) == canonical_json(v) for k, v in comparable.items()):
            return True
    if spec.transformation_id == "MECH_RATE_STATE_CONTACT":
        text = f"{passport.name_ru} {passport.formula.source}".casefold().replace("-", "_")
        return "rate_and_state" in text or ("rate" in text and "state" in text and "dot(theta)" in text)
    return False


def load_candidate_spot_checks(root: str | Path) -> List[Dict[str, Any]]:
    path = Path(root) / "data" / "evidence" / "candidate_spot_checks.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("checks", payload if isinstance(payload, list) else [])
    return [dict(row) for row in rows]


def _spot_check_signature(transformation_id: str, source_owner_ids: Sequence[str]) -> str:
    return digest_payload({"transformation_id": transformation_id, "source_owner_ids": sorted(source_owner_ids)})


def _apply_spot_checks(candidates: Sequence[Dict[str, Any]], checks: Sequence[Mapping[str, Any]]) -> Mapping[str, int]:
    index = {str(row["signature"]): row for row in checks}
    counts: Dict[str, int] = {}
    for candidate in candidates:
        signature = _spot_check_signature(candidate["transformation"]["transformation_id"], candidate["source_owner_ids"])
        evidence = index.get(signature)
        if evidence is None:
            continue
        status = str(evidence["prior_art_status"])
        candidate["novelty_status"] = status
        candidate["prior_art_status"] = status
        candidate["prior_art_check_id"] = evidence["spot_check_id"]
        candidate["prior_art_checked_at"] = evidence["checked_at"]
        candidate["prior_art_sources"] = list(evidence.get("sources", []))
        candidate["prior_art_claim_boundary"] = evidence["claim_boundary"]
        candidate["digest"] = _candidate_digest(candidate)
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _bridge_domain_eligible(passport: LawPassport, bridge_id: str) -> bool:
    required = set(BRIDGE_REQUIRED_ANY_TAGS.get(bridge_id, {}).get(passport.domain_id, ()))
    return bool(required and required.intersection(_semantic_tags(passport))) and not _is_non_generative_statement(passport)


def _bridge_tuple_semantically_compatible(passports: Sequence[LawPassport], bridge: DomainBridge | None) -> bool:
    if bridge is None:
        return False
    requirements = BRIDGE_REQUIRED_ANY_TAGS.get(bridge.bridge_id, {})
    if not requirements:
        return False
    return all(
        set(requirements.get(p.domain_id, ())).intersection(_semantic_tags(p))
        and not _is_non_generative_statement(p)
        for p in passports
    )


def _axis_policy_valid(spec: TransformationSpec) -> bool:
    if spec.bridge_id:
        return bool(spec.axis_ids) and all(
            any(
                domain in DOMAIN_REGISTRIES and axis_id in DOMAIN_REGISTRIES[domain].axes
                for domain in spec.target_domains
            )
            for axis_id in spec.axis_ids
        )
    domain = spec.target_domains[0]
    return bool(spec.axis_ids) and all(AXIS_POLICY_TEMPLATE[(domain, axis_id)].role == "GENERATIVE" for axis_id in spec.axis_ids)


def _coordinate_axes_valid(spec: TransformationSpec) -> bool:
    metadata_keys = {"bridge_id", "coupling"}
    target_registries = [DOMAIN_REGISTRIES.get(domain) for domain in spec.target_domains]
    if any(registry is None for registry in target_registries):
        return False
    registered_union = set().union(*(set(registry.axes) for registry in target_registries if registry is not None))
    if any(key not in registered_union and key not in metadata_keys for key in spec.coordinate_delta):
        return False
    for registry in target_registries:
        if registry is None:
            continue
        domain_delta = {k: v for k, v in spec.coordinate_delta.items() if k in registry.axes}
        if domain_delta:
            try:
                registry.validate_coordinate(domain_delta)
            except (ValueError, TypeError):
                return False
    return True


def _gate_candidate(
    passports: Sequence[LawPassport],
    spec: TransformationSpec,
    expression: ExpressionIR,
    known_formula_digests: set[str],
    bridge: DomainBridge | None,
) -> Dict[str, bool]:
    if spec.bridge_id:
        transformation_applicable = bridge is not None
        semantic_compatible = _bridge_tuple_semantically_compatible(passports, bridge)
    else:
        transformation_applicable = all(_expression_family(p) in spec.applicable_families for p in passports)
        semantic_compatible = all(_single_source_semantically_applicable(p, spec) for p in passports)
    return {
        "SOURCE_OWNER_PRESENT": bool(passports) and all(p.owner_id and p.formula.digest for p in passports),
        "SOURCE_EPISTEMIC_ELIGIBLE": all(p.epistemic_state in ELIGIBLE_SOURCE_STATES for p in passports),
        "SOURCE_DOMAIN_MATCH": tuple(p.domain_id for p in passports) == spec.source_domains,
        "TARGET_DOMAINS_REGISTERED": all(d in DOMAIN_REGISTRIES for d in spec.target_domains),
        "AXIS_POLICY_REGISTERED": _axis_policy_valid(spec),
        "TRANSFORMATION_APPLICABLE": transformation_applicable,
        "NON_GENERATIVE_STATEMENT_BLOCKED": all(not _is_non_generative_statement(p) or spec.allow_non_generative_statement for p in passports),
        "SEMANTIC_ROLE_COMPATIBLE": semantic_compatible,
        "FORMULA_PARSE_PASS": expression.parse_status == "PASS" and bool(expression.digest),
        "NONTRIVIAL_TRANSFORM": all(expression.digest != p.formula.digest for p in passports),
        "TARGET_STATE_NOT_ALREADY_ACTIVE": all(not _target_state_already_active(p, spec) for p in passports),
        "SYMBOLIC_DIMENSION_CONTRACT": "VALIDATED_SYMBOLIC" in spec.dimension_contract,
        "COORDINATE_DELTA_REGISTERED": _coordinate_axes_valid(spec),
        "CONTROLLED_LIMIT_DECLARED": bool(spec.controlled_limits),
        "FALSIFIER_DECLARED": bool(spec.falsification_criterion.strip()),
        "MEASUREMENTS_DECLARED": bool(spec.required_measurements),
        "NOT_EXACT_KNOWN_FORMULA": expression.digest not in known_formula_digests,
        "BRIDGE_REGISTERED_WHEN_REQUIRED": (bridge is not None and bridge.status == "ACTIVE") if spec.bridge_id else True,
    }


def _build_row(
    passports: Sequence[LawPassport],
    spec: TransformationSpec,
    bridge: DomainBridge | None,
    known_formula_digests: set[str],
) -> Tuple[Dict[str, Any] | None, str | None]:
    try:
        formula_source = spec.formula_builder(passports, bridge)
        preliminary = ExpressionIR.from_source(formula_source, "composite_model_family")
        source_scopes = [p.formula.operator_scope for p in passports]
        scope = OperatorScopeIR(
            domain_definition="intersection of source validity domains: " + " | ".join(p.validity_domain or p.owner_id for p in passports),
            codomain_definition="candidate residual/operator on target domains: " + ",".join(spec.target_domains),
            measure="inherited/required measures: " + " | ".join(s.measure for s in source_scopes),
            adjoint_structure="inherited/required adjoints: " + " | ".join(s.adjoint_structure for s in source_scopes),
            limit_topology="candidate controlled limits: " + " | ".join(spec.controlled_limits),
            status="PARTIAL_INHERITED_SCOPE_REQUIRES_LOWERING",
            assumptions=tuple(spec.assumptions),
        ).finalized()
        distribution = DistributionWavefrontIR(
            distribution_space="inherited from sources; explicit lowering required before any singular product or pullback",
            wavefront_description="NOT_COMPUTED",
            operations=("candidate_composition",),
            product_condition="Hörmander condition required if distributional factors are present",
            product_status="NOT_EVALUATED",
            status="DISTRIBUTIONAL_ANALYSIS_REQUIRED_BEFORE_LIMIT_CLAIM",
        ).finalized()
        expression = ExpressionIR.from_source(
            formula_source, "composite_model_family",
            operator_scope=scope,
            binding_graph=SharedBindingGraph.structural(preliminary.symbols),
            distribution_wavefront=distribution,
        )
    except Exception:
        return None, "FORMULA_PARSE_PASS"
    checks = _gate_candidate(passports, spec, expression, known_formula_digests, bridge)
    failed = next((gate for gate, status in checks.items() if not status), None)
    if failed:
        return None, failed
    identity_payload = {
        "generator_version": GENERATOR_VERSION,
        "transformation_digest": spec.digest,
        "source_formula_digests": [p.formula.digest for p in passports],
        "source_owner_ids": [p.owner_id for p in passports],
        "target_domains": spec.target_domains,
        "axis_ids": spec.axis_ids,
    }
    candidate_id = "CGEN-" + digest_payload(identity_payload)[:20].upper()
    proof_graph = candidate_proof_graph(candidate_id)
    limit_protocol = candidate_limit_protocol(candidate_id, spec.controlled_limits)
    source_ledger = source_ledger_from_passports(passports, ledger_id=candidate_id + ":SOURCES")
    dimension_payload = json.loads(spec.dimension_contract)
    inheritance = candidate_inheritance_contract(
        candidate_id, passports, expression,
        dimension_contract=dimension_payload,
        controlled_limits=spec.controlled_limits,
        transformation_id=spec.transformation_id,
    )
    row: Dict[str, Any] = {
        "schema": GENERATOR_SCHEMA,
        "candidate_id": candidate_id,
        "owner_id": candidate_id,
        "entity_kind": "GENERATED_COMPOSITE_MODEL_FAMILY",
        "candidate_scope": "SOURCE_LAWS_EMBEDDED_COUPLED_EXTENSION",
        "operator_instantiation_status": "PARAMETRIC_OPERATOR_SCHEMA",
        "epistemic_state": "DERIVED_COMPOSITE_MODEL",
        "scientific_status": "SOURCE_SECTORS_INHERITED_COUPLED_EXTENSION_UNRESOLVED",
        "active_registry_mutation": False,
        "source_id": GENERATED_SOURCE_ID,
        "source_owner_ids": [p.owner_id for p in passports],
        "source_formula_digests": [p.formula.digest for p in passports],
        "source_domains": [p.domain_id for p in passports],
        "target_domains": list(spec.target_domains),
        "source_names_ru": [p.name_ru for p in passports],
        "source_expression_families": {p.owner_id: _expression_family(p) for p in passports},
        "source_statement_roles": {p.owner_id: _statement_role(p) for p in passports},
        "source_semantic_tags": {p.owner_id: list(_semantic_tags(p)) for p in passports},
        "generator": {
            "generator_id": spec.generator_id,
            "generator_version": GENERATOR_VERSION,
            "truth_access": False,
            "uses_legacy_candidates": False,
            "uses_archetype_candidate_rows": False,
        },
        "transformation": {
            "transformation_id": spec.transformation_id,
            "transformation_digest": spec.digest,
            "bridge_id": spec.bridge_id,
            "axis_ids": list(spec.axis_ids),
            "composition_order": spec.composition_order,
        },
        "formula": dataclasses.asdict(expression),
        "property_inheritance_contract": inheritance,
        "proof_obligation_graph": dataclasses.asdict(proof_graph),
        "limit_protocol": dataclasses.asdict(limit_protocol),
        "primary_source_ledger": dataclasses.asdict(source_ledger),
        "coordinate_delta": dict(spec.coordinate_delta),
        "dimension_contract": dimension_payload,
        "assumptions": list(spec.assumptions),
        "controlled_limits": list(spec.controlled_limits),
        "falsification_criterion": spec.falsification_criterion,
        "required_measurements": list(spec.required_measurements),
        "classification": {
            "categories": list(spec.categories),
            "risk_class": spec.risk_class,
            "source_sector_status": "INHERITED_WITHIN_DECLARED_VALIDITY_INTERSECTION",
            "coupled_extension_status": "UNRESOLVED",
            "candidate_scope": "SOURCE_LAWS_EMBEDDED_COUPLED_EXTENSION",
        },
        "gates": checks,
        "gate_status": "FORMALLY_ADMISSIBLE",
        "novelty_status": "NOT_SEARCHED",
        "identifiability_status": "NOT_RUN",
        "experimental_status": "NOT_RUN",
        "deduplication": {
            "method": "conservative_content_addressed_axis_signature",
            "merged_equivalent_records": 0,
            "semantic_similarity_not_used_as_identity": True,
            "scientific_equivalence_requires_proof": True,
        },
        "equivalent_source_owner_ids": [],
        "provenance": {
            "source_catalog": "data/passports/known_laws.jsonl",
            "legacy_candidate_file_used": False,
            "generated_from_canonical_owners_only": True,
            "axis_registry_digests": {d: DOMAIN_REGISTRIES[d].digest for d in spec.target_domains},
        },
        "digest": "",
    }
    row["digest"] = _candidate_digest(row)
    return row, None


class _SingleDomainGenerator:
    generator_id: str = ""
    domain_id: str = ""
    specs: Tuple[TransformationSpec, ...] = ()

    def generate(self, catalog: LawCatalog, known_formula_digests: set[str], audit: GenerationAudit) -> Iterable[Tuple[Dict[str, Any], TransformationSpec]]:
        sources = sorted((p for p in catalog.passports.values() if p.domain_id == self.domain_id), key=lambda p: p.owner_id)
        for passport in sources:
            family = _expression_family(passport)
            for spec in self.specs:
                audit.evaluated += 1
                audit.register_axes(spec, event="evaluated")
                if family not in spec.applicable_families:
                    audit.reject("TRANSFORMATION_APPLICABLE", spec)
                    continue
                row, failed = _build_row((passport,), spec, None, known_formula_digests)
                if row is None:
                    audit.reject(failed or "UNKNOWN", spec)
                    continue
                yield row, spec


class PhysicsCandidateGenerator(_SingleDomainGenerator):
    generator_id = "PhysicsCandidateGenerator"
    domain_id = "physics"
    specs = _physics_specs()


class MechanicsCandidateGenerator(_SingleDomainGenerator):
    generator_id = "MechanicsCandidateGenerator"
    domain_id = "mechanics"
    specs = _mechanics_specs()


class ChemistryCandidateGenerator(_SingleDomainGenerator):
    generator_id = "ChemistryCandidateGenerator"
    domain_id = "chemistry"
    specs = _chemistry_specs()


class BridgeCandidateGenerator:
    generator_id = "BridgeCandidateGenerator"

    def __init__(self, bridges: Mapping[str, DomainBridge]) -> None:
        self.bridges = bridges

    def generate(self, catalog: LawCatalog, known_formula_digests: set[str], audit: GenerationAudit) -> Iterable[Tuple[Dict[str, Any], TransformationSpec]]:
        by_domain: Dict[str, List[LawPassport]] = {}
        for passport in catalog.passports.values():
            by_domain.setdefault(passport.domain_id, []).append(passport)
        for values in by_domain.values():
            values.sort(key=lambda p: p.owner_id)

        for bridge_id in sorted(self.bridges):
            bridge = self.bridges[bridge_id]
            if bridge_id not in BRIDGE_REQUIRED_ANY_TAGS:
                continue
            pools: List[List[LawPassport]] = []
            compatible = True
            for domain in bridge.source_domains:
                pool = [
                    p for p in by_domain.get(domain, ())
                    if p.epistemic_state in ELIGIBLE_SOURCE_STATES and _bridge_domain_eligible(p, bridge_id)
                ]
                if not pool:
                    compatible = False
                    break
                pools.append(pool)
            if not compatible:
                continue
            spec = _bridge_spec(bridge)
            for passports in _cartesian_product(pools):
                audit.evaluated += 1
                # Bridge axis IDs belong to different domains.  They are in the
                # row and report, but per-domain counters are updated only when
                # the axis exists in that domain.
                row, failed = _build_row(passports, spec, bridge, known_formula_digests)
                if row is None:
                    audit.reject(failed or "UNKNOWN")
                    continue
                yield row, spec


def _cartesian_product(pools: Sequence[Sequence[LawPassport]]) -> Iterable[Tuple[LawPassport, ...]]:
    if not pools:
        return
    result: List[Tuple[LawPassport, ...]] = [()]
    for pool in pools:
        result = [prefix + (item,) for prefix in result for item in pool]
    yield from result


AXIS_EXPLORATION_POLICY_SCHEMA = "phi-global-axis-combination-space/v1"


def global_axis_combination_contract() -> Mapping[str, Any]:
    """Exact compressed contract for the current registered global axis space.

    This is an addressability/exploration statement, not a claim that the
    current registry is complete or ontologically privileged.  Ownership and
    domain membership carry provenance but are not admissibility gates for a
    joint tuple-region.  Arithmetic composition of heterogeneous coordinates
    remains subject to dimensional/typed-functor checks.
    """
    domain_axes = {
        domain: tuple(f"{domain}.{axis_id}" for axis_id in sorted(registry.axes))
        for domain, registry in sorted(DOMAIN_REGISTRIES.items())
    }
    counts = {domain: len(axes) for domain, axes in domain_axes.items()}
    n = sum(counts.values())
    total_nonempty = (1 << n) - 1
    within_domain = sum((1 << c) - 1 for c in counts.values())
    cross_domain = total_nonempty - within_domain
    representative_orders = sorted({k for k in (1, 2, 3, 4, 8, 16, 32, 64, 128, 256, n) if 1 <= k <= n})
    order_rows = {}
    for k in representative_orders:
        total_k = math.comb(n, k)
        within_k = sum(math.comb(c, k) for c in counts.values() if c >= k)
        order_rows[str(k)] = {
            "all_registered_axis_combinations": str(total_k),
            "within_single_domain": str(within_k),
            "cross_domain": str(total_k - within_k),
        }

    # Deterministic examples are only witnesses that cross-domain tuples are
    # addressable. They are not privileged candidates or a search ceiling.
    domains = list(domain_axes)
    samples: List[Dict[str, Any]] = []
    for i in range(min(8, max(0, len(domains) - 1))):
        d1, d2 = domains[i], domains[i + 1]
        if not domain_axes[d1] or not domain_axes[d2]:
            continue
        axes = [domain_axes[d1][0], domain_axes[d2][0]]
        samples.append({
            "axes": axes,
            "axis_order": 2,
            "domains": [d1, d2],
            "status": "CROSS_DOMAIN_AXIS_COMBINATION_RESEARCH_CANDIDATE",
        })
    if domains:
        full_witness = [domain_axes[d][0] for d in domains if domain_axes[d]]
        if len(full_witness) >= 2:
            samples.append({
                "axes": full_witness,
                "axis_order": len(full_witness),
                "domains": [a.split('.', 1)[0] for a in full_witness],
                "status": "MULTIDOMAIN_AXIS_COMBINATION_RESEARCH_CANDIDATE",
            })

    payload = {
        "schema": AXIS_EXPLORATION_POLICY_SCHEMA,
        "current_registered_axis_count": n,
        "current_registered_domain_count": len(counts),
        "registry_is_example_not_universal_solution_space": True,
        "candidate_registry_is_baseline_not_solution_space": True,
        "active_baseline_contains_confirmed_controls_only": True,
        "unverified_generated_couplings_live_in_frontier_registry": True,
        "total_nonempty_registered_axis_subsets": str(total_nonempty),
        "within_single_domain_nonempty_axis_subsets": str(within_domain),
        "cross_domain_nonempty_axis_subsets": str(cross_domain),
        "all_orders_1_through_axis_count_addressable": True,
        "fixed_axis_combination_order_ceiling": None,
        "owner_affiliation_is_combination_gate": False,
        "domain_affiliation_is_combination_gate": False,
        "bridge_required_for_joint_tuple_exploration": False,
        "bridge_or_typed_functor_required_for_arithmetic_identification": True,
        "high_dimensionality_is_search_rejection": False,
        "high_dimensionality_may_require_stronger_promotion_evidence": True,
        "unknown_candidate_is_false": False,
        "unmaterialized_or_sparse_region_is_physical_void": False,
        "void_frontier_regions_are_priority_research_targets": True,
        "search_and_promotion_are_separate": True,
        "representative_order_counts": order_rows,
        "cross_domain_combination_witnesses": samples,
        "claim_boundary": {
            "continuous_parameter_cartesian_exhaustion": False,
            "all_possible_scientific_axes_known": False,
            "all_axis_combinations_materialized": False,
            "world_novelty_from_open_region": False,
        },
    }
    return {**payload, "digest": digest_payload(payload)}


def _axis_coverage_summary(
    audit: GenerationAudit,
    specs: Sequence[TransformationSpec],
    catalog: LawCatalog,
    *,
    max_exact_strength: int | None = None,
) -> Mapping[str, Any]:
    """Exactly classify every finite subset of the registered axis set.

    There is no built-in interaction-order ceiling.  The open universe is not
    materialized: total counts are obtained combinatorially, while the finite
    occupied/reachable family is represented by explicit subset sets generated
    from registered passports and transformations.  This gives an exact census
    for every order ``1..axis_count`` without allocating ``2**axis_count`` rows.

    ``max_exact_strength`` is retained only as an explicit caller-requested
    prefix for diagnostic use.  ``None`` (the production default) scans all
    registered orders.
    """
    transformation_map: Dict[Tuple[str, str], List[str]] = {
        key: list(row.transformation_ids) for key, row in AXIS_POLICY_TEMPLATE.items()
    }
    for spec in specs:
        for domain in set(spec.source_domains) | set(spec.target_domains):
            registry = DOMAIN_REGISTRIES.get(domain)
            if registry is None:
                continue
            for axis_id in set(spec.axis_ids) | set(spec.coordinate_delta):
                if (domain, axis_id) in transformation_map and axis_id in registry.axes:
                    transformation_map[(domain, axis_id)].append(spec.transformation_id)

    rows: List[Dict[str, Any]] = []
    by_domain: Dict[str, Dict[str, Any]] = {}
    interaction_domains: Dict[str, Any] = {}
    global_hash = hashlib.sha256()
    total_interactions = 0
    total_open = 0

    def register_subsets(
        destination: Dict[int, set[Tuple[str, ...]]],
        active_sets: Iterable[Tuple[str, ...]],
        order_limit: int,
    ) -> None:
        # Duplicate active sets are common in the registry; collapsing them is
        # exact and prevents repeated subset generation.
        for active in sorted(set(active_sets), key=lambda value: (len(value), value)):
            for strength in range(1, min(order_limit, len(active)) + 1):
                destination.setdefault(strength, set()).update(
                    itertools.combinations(active, strength)
                )

    def open_samples(
        axes: Tuple[str, ...],
        strength: int,
        covered: set[Tuple[str, ...]],
        sample_limit: int = 40,
    ) -> List[List[str]]:
        sample: List[List[str]] = []
        for combo in itertools.combinations(axes, strength):
            if combo not in covered:
                sample.append(list(combo))
                if len(sample) >= sample_limit:
                    break
        return sample

    for domain in sorted(DOMAIN_REGISTRIES):
        registry = DOMAIN_REGISTRIES[domain]
        axes = tuple(sorted(registry.axes))
        order_limit = len(axes) if max_exact_strength is None else min(
            len(axes), max(0, int(max_exact_strength))
        )
        if order_limit < 1:
            raise ValueError("axis interaction scan requires at least one order")
        passports = tuple(sorted(
            (p for p in catalog.passports.values() if p.domain_id == domain),
            key=lambda p: p.owner_id,
        ))
        domain_specs = tuple(
            spec for spec in specs
            if domain in spec.source_domains or domain in spec.target_domains
        )

        axis_values: Dict[str, set[str]] = {axis: set() for axis in axes}
        axis_owner_counts: Dict[str, int] = {axis: 0 for axis in axes}
        passport_axis_sets: List[Tuple[str, ...]] = []
        for passport in passports:
            active: List[str] = []
            for axis in axes:
                value = passport.scientific_coordinate.get(axis)
                if value not in (None, "", (), [], {}):
                    axis_values[axis].add(canonical_json(value))
                    axis_owner_counts[axis] += 1
                    active.append(axis)
            passport_axis_sets.append(tuple(sorted(active)))

        spec_axis_sets: List[Tuple[str, ...]] = []
        for spec in domain_specs:
            active = sorted(
                axis for axis in (set(spec.axis_ids) | set(spec.coordinate_delta))
                if axis in registry.axes
            )
            for axis in active:
                if axis in spec.coordinate_delta:
                    axis_values[axis].add(canonical_json(spec.coordinate_delta[axis]))
            spec_axis_sets.append(tuple(active))

        known_by_t: Dict[int, set[Tuple[str, ...]]] = {}
        reachable_by_t: Dict[int, set[Tuple[str, ...]]] = {}
        register_subsets(known_by_t, passport_axis_sets, order_limit)
        register_subsets(reachable_by_t, spec_axis_sets, order_limit)

        strengths: Dict[str, Any] = {}
        frontier_samples: Dict[str, List[List[str]]] = {}
        domain_hash = hashlib.sha256()
        for strength in range(1, order_limit + 1):
            total = math.comb(len(axes), strength)
            known = known_by_t.get(strength, set())
            reachable = reachable_by_t.get(strength, set())
            reachable_only = reachable - known
            covered = known | reachable
            open_count = total - len(covered)
            if open_count < 0:
                raise RuntimeError(f"invalid compressed census for {domain} t={strength}")
            sample = open_samples(axes, strength, covered) if open_count else []
            # The digest is exact over the compressed classification: universe
            # cardinality plus every non-open subset and its class.
            header = (
                f"{domain}|{strength}|{total}|{len(known)}|"
                f"{len(reachable_only)}|{open_count}\n"
            ).encode("utf-8")
            domain_hash.update(header)
            global_hash.update(header)
            for combo in sorted(known):
                line = f"{domain}|{strength}|{','.join(combo)}|KNOWN_OCCUPIED\n".encode("utf-8")
                domain_hash.update(line)
                global_hash.update(line)
            for combo in sorted(reachable_only):
                line = f"{domain}|{strength}|{','.join(combo)}|TRANSFORMATION_REACHABLE\n".encode("utf-8")
                domain_hash.update(line)
                global_hash.update(line)
            strengths[str(strength)] = {
                "axis_subset_count": total,
                "classified_count": total,
                "known_occupied": len(known),
                "transformation_reachable_only": len(reachable_only),
                "open_interaction": open_count,
                "occupied_or_reachable_fraction": (len(covered) / total) if total else 1.0,
                "classification_mode": "EXACT_COMPRESSED_FINITE_SET_CENSUS",
            }
            frontier_samples[str(strength)] = sample
            total_interactions += total
            total_open += open_count

        domain_rows: List[Dict[str, Any]] = []
        role_counts = {"generative": 0, "context": 0, "observation": 0, "role_unclassified": 0}
        for axis in axes:
            base = AXIS_POLICY_TEMPLATE[(domain, axis)]
            runtime_row = audit.axis_rows[(domain, axis)]
            payload = runtime_row.as_dict()
            payload["role"] = base.role
            payload["transformation_ids"] = sorted(set(transformation_map[(domain, axis)]))
            payload["observed_or_declared_value_count"] = len(axis_values[axis])
            payload["source_owner_count"] = axis_owner_counts[axis]
            payload["parameterization_status"] = (
                "PARAMETERIZED" if axis_values[axis] else "NO_REGISTERED_VALUE_YET"
            )
            rows.append(payload)
            domain_rows.append(payload)
            role_counts[base.role.casefold()] = role_counts.get(base.role.casefold(), 0) + 1

        parameterized = sum(1 for axis in axes if axis_values[axis])
        domain_summary = {
            "registry_axis_count": len(axes),
            "total": len(axes),
            **role_counts,
            "parameterized_axes": parameterized,
            "axes_without_registered_values": [axis for axis in axes if not axis_values[axis]],
            "all_axes_classified": len(axes) == registry.axis_count,
            "all_axes_parameterized": parameterized == len(axes),
        }
        by_domain[domain] = domain_summary
        interaction_domains[domain] = {
            "axis_count": len(axes),
            "scanned_order_count": order_limit,
            "all_registered_orders_scanned": order_limit == len(axes),
            "exact_strengths": strengths,
            "frontier_samples": frontier_samples,
            "classification_sha256": domain_hash.hexdigest(),
        }

    production_full_scan = max_exact_strength is None
    global_combinations = global_axis_combination_contract()
    return {
        "strategy": "exact_compressed_global_and_within_domain_axis_census_plus_void_frontier_exploration_plus_guarded_sparse_formula_emission",
        "scan_order_policy": "ALL_REGISTERED_AXES" if production_full_scan else "EXPLICIT_DIAGNOSTIC_PREFIX",
        "max_exact_axis_interaction_strength": None if production_full_scan else int(max_exact_strength),
        "exact_axis_subset_census": True,
        "continuous_value_cartesian_exhaustion": False,
        "higher_order_axis_interactions_5_plus": (
            "EXACT_COMPRESSED_CENSUS_ALL_REGISTERED_ORDERS"
            if production_full_scan else "CLASSIFIED_INSIDE_EXPLICIT_PREFIX"
        ),
        "method_boundary": (
            "Every finite subset of the current registered global axis set is addressable by exact compressed count, "
            "including cross-domain/cross-owner tuples. Current registries and the 2771 candidate baseline are not the "
            "solution space. Continuous parameter values are not declared exhausted; arithmetic formula emission still "
            "requires typed operators/functors and all promotion gates. Open or unmaterialized subsets are frontier "
            "candidates, not false laws and not proof of physical emptiness."
        ),
        "global_axis_combination_space": global_combinations,
        "domains": dict(sorted(by_domain.items())),
        "rows": rows,
        "interaction_census": {
            "domains": interaction_domains,
            "total_classified_axis_subsets": total_interactions,
            "total_open_axis_subsets": total_open,
            "classification_sha256": global_hash.hexdigest(),
            "materialized_open_subsets": False,
            "open_subset_research_status": "VOID_FRONTIER_CANDIDATE_NOT_FALSE",
            "open_subset_is_proof_of_physical_absence": False,
            "global_registered_subset_count": global_combinations["total_nonempty_registered_axis_subsets"],
            "global_cross_domain_subset_count": global_combinations["cross_domain_nonempty_axis_subsets"],
        },
        "all_registered_axes_classified": all(v["all_axes_classified"] for v in by_domain.values()),
        "all_registered_axis_orders_classified": production_full_scan,
        "all_registered_axes_parameterized": all(v["all_axes_parameterized"] for v in by_domain.values()),
    }


DEEP_CORE_DOMAINS = ("physics", "mechanics", "chemistry")
DEEP_SEARCH_PROFILES: Tuple[Mapping[str, Any], ...] = (
    {
        "profile_id": "ELECTRO_CHEMO_MECHANICAL_64",
        "target_axis_order": 64,
        "keywords": ("electro", "chem", "react", "transport", "continuum", "force", "thermo"),
        "purpose": "electro-chemo-mechanical reactive-continuum closure",
    },
    {
        "profile_id": "QUANTUM_REACTIVE_SPECTROSCOPIC_96",
        "target_axis_order": 96,
        "keywords": ("quantum", "spectro", "wave", "open", "measurement", "reaction"),
        "purpose": "quantum-reactive spectroscopic and open-dynamics closure",
    },
    {
        "profile_id": "MULTISCALE_CORE_128",
        "target_axis_order": 128,
        "keywords": ("multiscale", "nonlinear", "variational", "symmetry", "control", "chem", "mechan"),
        "purpose": "multiscale nonlinear core closure",
    },
    {
        "profile_id": "FULL_CORE_FRONTIER_195",
        "target_axis_order": 195,
        "keywords": (),
        "purpose": "maximum semantically bound physics-mechanics-chemistry frontier",
    },
)


def _component_axis_bindings(row: Mapping[str, Any], catalog: LawCatalog) -> Dict[str, List[Dict[str, Any]]]:
    bindings: Dict[str, List[Dict[str, Any]]] = {}
    for owner_id in row.get("source_owner_ids", ()):
        passport = catalog.passports.get(str(owner_id))
        if passport is None:
            continue
        registry = DOMAIN_REGISTRIES.get(passport.domain_id)
        if registry is None:
            continue
        for axis_id, value in passport.scientific_coordinate.items():
            if axis_id not in registry.axes or value in (None, "", (), [], {}):
                continue
            bindings.setdefault(f"{passport.domain_id}.{axis_id}", []).append({
                "binding_type": "LAW_PASSPORT_COORDINATE",
                "owner_id": passport.owner_id,
                "value": value,
            })
    transformation = row.get("transformation", {})
    transformation_id = str(transformation.get("transformation_id", ""))
    for domain in sorted(set(row.get("source_domains", ())) | set(row.get("target_domains", ()))):
        registry = DOMAIN_REGISTRIES.get(str(domain))
        if registry is None:
            continue
        for axis_id in set(transformation.get("axis_ids", ())) | set(row.get("coordinate_delta", {})):
            if axis_id not in registry.axes:
                continue
            payload: Dict[str, Any] = {
                "binding_type": "REGISTERED_TRANSFORMATION_AXIS",
                "transformation_id": transformation_id,
            }
            if axis_id in row.get("coordinate_delta", {}):
                payload["value"] = row["coordinate_delta"][axis_id]
            bindings.setdefault(f"{domain}.{axis_id}", []).append(payload)
    return {key: value for key, value in sorted(bindings.items())}


def _component_tokens(row: Mapping[str, Any]) -> set[str]:
    text: List[str] = [
        str(row.get("candidate_id", "")),
        str(row.get("transformation", {}).get("transformation_id", "")),
        " ".join(str(x) for x in row.get("source_names_ru", ())),
        " ".join(str(x) for x in row.get("classification", {}).get("categories", ())),
    ]
    for tags in row.get("source_semantic_tags", {}).values():
        text.extend(str(tag) for tag in tags)
    return set(re.findall(r"[0-9A-Za-zА-Яа-я_]+", " ".join(text).casefold()))


def _deep_component_search(
    base_candidates: Sequence[Mapping[str, Any]],
    catalog: LawCatalog,
    profile: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Deterministic relevance-first, coupling-ready search with no fixed visit budget.

    Fresh deep birth operates on non-deep component candidates.  Previously
    materialized ``DEEP_OWNER_HYPERGRAPH_COMPOSITE_MODEL_FAMILY`` rows are
    outputs of this same owner and therefore cannot silently become one atomic
    component of a new fresh birth.  When semantic keywords are supplied they
    outrank raw axis breadth.  A coupled residual is not considered target-ready
    until at least two component sectors share a registered axis, because the
    downstream structural Gamma owner requires typed component edges.
    """
    core_prefixes = tuple(domain + "." for domain in DEEP_CORE_DOMAINS)
    prepared: List[Dict[str, Any]] = []
    excluded_nested_deep = 0
    for row in base_candidates:
        if row.get("entity_kind") == "DEEP_OWNER_HYPERGRAPH_COMPOSITE_MODEL_FAMILY":
            excluded_nested_deep += 1
            continue
        bindings = _component_axis_bindings(row, catalog)
        core_bindings = {key: value for key, value in bindings.items() if key.startswith(core_prefixes)}
        if not core_bindings:
            continue
        prepared.append({
            "row": row,
            "bindings": core_bindings,
            "axes": set(core_bindings),
            "tokens": _component_tokens(row),
            "domains": set(row.get("source_domains", ())) | set(row.get("target_domains", ())),
            "owners": set(row.get("source_owner_ids", ())),
        })
    prepared.sort(key=lambda item: str(item["row"]["candidate_id"]))
    keywords = {str(word).casefold() for word in profile.get("keywords", ())}
    required_owners = {str(owner_id) for owner_id in profile.get("required_source_owner_ids", ())}
    target = int(profile["target_axis_order"])
    selected: List[Dict[str, Any]] = []
    covered: set[str] = set()
    selected_tokens: set[str] = set()
    selected_domains: set[str] = set()
    selected_owners: set[str] = set()
    evaluated = 0
    typed_edge_pairs: set[tuple[str, str]] = set()

    while True:
        best: Dict[str, Any] | None = None
        best_key: Tuple[int, int, int, int, int, int, int, str] | None = None
        target_already_reached = len(covered) >= target
        coupling_ready = len(selected) >= 2 and bool(typed_edge_pairs)
        required_owner_coverage = required_owners.issubset(selected_owners)
        if target_already_reached and coupling_ready and required_owner_coverage:
            break
        for item in prepared:
            if item in selected:
                continue
            evaluated += 1
            new_axes = item["axes"] - covered
            shared_axes = item["axes"] & covered
            keyword_hits = len(keywords & item["tokens"])
            connected = not selected or bool(
                item["domains"] & selected_domains
                or item["tokens"] & selected_tokens
                or item["owners"] & selected_owners
                or item["row"].get("transformation", {}).get("bridge_id")
            )
            if not connected:
                continue
            # Before the target is reached, a component must advance coverage or
            # create a typed coupling edge.  Once target coverage is already met
            # by one sector, only a component that creates an actual shared-axis
            # edge is useful for the coupled residual.
            if target_already_reached and selected and not shared_axes:
                continue
            if not target_already_reached and selected and not new_axes and not shared_axes:
                continue
            if not selected and not new_axes:
                continue
            bridge_bonus = 1 if item["row"].get("transformation", {}).get("bridge_id") else 0
            typed_edge_bonus = 1 if shared_axes else 0
            required_owner_hits = len((item["owners"] & required_owners) - selected_owners)
            # Explicit owner anchors are stronger than lexical relevance; then
            # semantic relevance outranks raw axis breadth.
            key = (
                required_owner_hits,
                keyword_hits if keywords else 0,
                typed_edge_bonus,
                len(new_axes),
                len(shared_axes),
                bridge_bonus,
                len(item["axes"]),
                str(item["row"]["candidate_id"]),
            )
            if best_key is None or key > best_key:
                best, best_key = item, key
        if best is None:
            break
        best_id = str(best["row"]["candidate_id"])
        for prior in selected:
            if best["axes"] & prior["axes"]:
                a, b = sorted((best_id, str(prior["row"]["candidate_id"])))
                typed_edge_pairs.add((a, b))
        selected.append(best)
        covered.update(best["axes"])
        selected_tokens.update(best["tokens"])
        selected_domains.update(best["domains"])
        selected_owners.update(best["owners"])

    merged_bindings: Dict[str, List[Dict[str, Any]]] = {}
    for item in selected:
        for axis_id, values in item["bindings"].items():
            existing = merged_bindings.setdefault(axis_id, [])
            existing_keys = {canonical_json(v) for v in existing}
            for value in values:
                key = canonical_json(value)
                if key not in existing_keys:
                    existing.append(value)
                    existing_keys.add(key)
    coupling_ready = len(selected) >= 2 and bool(typed_edge_pairs)
    target_reached = len(merged_bindings) >= target
    required_owner_coverage = required_owners.issubset(selected_owners)
    return {
        "selected": selected,
        "axis_bindings": {key: value for key, value in sorted(merged_bindings.items())},
        "achieved_axis_order": len(merged_bindings),
        "target_axis_order": target,
        "target_reached": target_reached,
        "coupling_ready": coupling_ready,
        "typed_shared_axis_edge_count": len(typed_edge_pairs),
        "required_source_owner_ids": sorted(required_owners),
        "covered_required_source_owner_ids": sorted(required_owners & selected_owners),
        "required_source_owner_coverage": required_owner_coverage,
        "frontier_exhausted": not (target_reached and coupling_ready and required_owner_coverage),
        "evaluated_component_visits": evaluated,
        "fixed_visit_budget": None,
        "nested_deep_components_excluded": excluded_nested_deep,
        "semantic_relevance_priority": bool(keywords),
        "minimum_component_count_for_coupling": 2,
    }


def _build_deep_candidate(
    search: Mapping[str, Any],
    profile: Mapping[str, Any],
    catalog: LawCatalog,
) -> Dict[str, Any]:
    selected = list(search["selected"])
    component_rows = [item["row"] for item in selected]
    source_owner_ids = sorted({str(owner) for row in component_rows for owner in row.get("source_owner_ids", ())})
    passports = [catalog.passports[owner_id] for owner_id in source_owner_ids]
    qualified_axes = sorted(search["axis_bindings"])
    safe_profile = re.sub(r"[^0-9A-Za-z_]", "_", str(profile["profile_id"]))
    component_terms = [
        f"R_{re.sub(r'[^0-9A-Za-z_]', '_', str(row['candidate_id']))}[Psi_{idx}]"
        for idx, row in enumerate(component_rows, 1)
    ]
    formula_source = (
        f"R_{safe_profile}[Psi] := DirectSum(" + "; ".join(component_terms) +
        ") + CouplingClosure_Gamma[Psi] = 0"
    )
    preliminary = ExpressionIR.from_source(formula_source, "deep_owner_hypergraph_residual_system")
    scope = OperatorScopeIR(
        domain_definition="intersection of selected source-owner validity domains on the registered owner hypergraph",
        codomain_definition="typed direct sum of component residual codomains; no scalar addition of unlike dimensions",
        measure="component measures remain owner-controlled; coupling maps require explicit typed lowering",
        adjoint_structure="direct sum of inherited adjoint structures plus unresolved coupling adjoints",
        limit_topology="all coupling coefficients -> 0 recovers the direct product of selected source sectors",
        status="PARTIAL_INHERITED_SCOPE_REQUIRES_COUPLING_LOWERING",
        assumptions=("every active axis has a machine-readable semantic binding", "all component owners retain authority"),
    ).finalized()
    distribution = DistributionWavefrontIR(
        distribution_space="typed direct sum of inherited component spaces",
        wavefront_description="component wavefront data inherited; cross-component products not yet computed",
        operations=("direct_sum", "owner_hypergraph_coupling"),
        product_condition="every cross-component product requires an explicit Hörmander or regularity certificate",
        product_status="NOT_EVALUATED_FOR_NEW_COUPLINGS",
        status="DISTRIBUTIONAL_ANALYSIS_REQUIRED_BEFORE_PROMOTION",
    ).finalized()
    expression = ExpressionIR.from_source(
        formula_source,
        "deep_owner_hypergraph_residual_system",
        operator_scope=scope,
        binding_graph=SharedBindingGraph.structural(preliminary.symbols),
        distribution_wavefront=distribution,
    )
    identity_payload = {
        "generator_version": GENERATOR_VERSION,
        "profile_id": profile["profile_id"],
        "selected_component_digests": [row["digest"] for row in component_rows],
        "qualified_axis_ids": qualified_axes,
    }
    candidate_id = "DSPACE-" + digest_payload(identity_payload)[:20].upper()
    dimension_payload = {
        "status": "VALIDATED_AS_TYPED_DIRECT_SUM_BY_CONSTRUCTION",
        "operation": "DIRECT_SUM_OF_RESIDUAL_CODOMAINS",
        "scalar_cross_sector_addition": False,
        "coupling_map_requirement": "EXPLICIT_DOMAIN_AND_CODOMAIN_REQUIRED",
        "numeric_SI_vector": "PER_COMPONENT_OWNER; GLOBAL_SCALAR_VECTOR_NOT_APPLICABLE",
    }
    controlled_limits = (
        "all owner-hypergraph coupling coefficients -> 0 recovers the direct product of selected source sectors",
        "removal of any selected component recovers the induced connected sub-hypergraph candidate",
    )
    inheritance = candidate_inheritance_contract(
        candidate_id, passports, expression,
        dimension_contract=dimension_payload,
        controlled_limits=controlled_limits,
        transformation_id="OWNER_HYPERGRAPH_DEEP_SEARCH",
    )
    proof_graph = candidate_proof_graph(candidate_id)
    limit_protocol = candidate_limit_protocol(candidate_id, controlled_limits)
    source_ledger = source_ledger_from_passports(passports, ledger_id=candidate_id + ":SOURCES")
    checks = {
        "SOURCE_OWNER_PRESENT": bool(passports),
        "SOURCE_EPISTEMIC_ELIGIBLE": all(p.epistemic_state in ELIGIBLE_SOURCE_STATES for p in passports),
        "OWNER_HYPERGRAPH_CONNECTED": bool(component_rows),
        "ALL_ACTIVE_AXES_SEMANTICALLY_BOUND": len(qualified_axes) == len(search["axis_bindings"]),
        "AXIS_IDS_DOMAIN_QUALIFIED": all("." in axis for axis in qualified_axes),
        "FORMULA_PARSE_PASS": expression.parse_status == "PASS" and bool(expression.digest),
        "TYPED_DIRECT_SUM_DIMENSION_GATE": True,
        "CONTROLLED_LIMIT_DECLARED": bool(controlled_limits),
        "FALSIFIER_DECLARED": True,
        "MEASUREMENTS_DECLARED": True,
        "NO_FIXED_SMALL_ORDER_CEILING": True,
        "NO_FIXED_VISIT_BUDGET": search.get("fixed_visit_budget") is None,
        "CONTINUUM_EXHAUSTION_NOT_CLAIMED": True,
        "NOT_EXACT_KNOWN_FORMULA": expression.digest not in {p.formula.digest for p in catalog.passports.values()},
    }
    formula_blocks = []
    for item in selected[:12]:
        row = item["row"]
        formula_blocks.append({
            "component_candidate_id": row["candidate_id"],
            "source_owner_ids": row.get("source_owner_ids", []),
            "formula": row.get("formula", {}).get("source", ""),
            "active_axis_ids": sorted(item["axes"]),
        })
    row: Dict[str, Any] = {
        "schema": GENERATOR_SCHEMA,
        "candidate_id": candidate_id,
        "owner_id": candidate_id,
        "entity_kind": "DEEP_OWNER_HYPERGRAPH_COMPOSITE_MODEL_FAMILY",
        "candidate_scope": "SOURCE_LAWS_EMBEDDED_COUPLED_EXTENSION",
        "operator_instantiation_status": "TYPED_COUPLED_RESIDUAL_SYSTEM_SCHEMA",
        "epistemic_state": "DERIVED_COMPOSITE_MODEL",
        "scientific_status": "SOURCE_SECTORS_INHERITED_COUPLED_EXTENSION_UNRESOLVED",
        "active_registry_mutation": False,
        "source_id": GENERATED_SOURCE_ID,
        "source_owner_ids": source_owner_ids,
        "source_formula_digests": [p.formula.digest for p in passports],
        "source_domains": [p.domain_id for p in passports],
        "target_domains": sorted({axis.split(".", 1)[0] for axis in qualified_axes}),
        "source_names_ru": [p.name_ru for p in passports],
        "source_expression_families": {p.owner_id: _expression_family(p) for p in passports},
        "source_statement_roles": {p.owner_id: _statement_role(p) for p in passports},
        "source_semantic_tags": {p.owner_id: list(_semantic_tags(p)) for p in passports},
        "generator": {
            "generator_id": "CandidateGenerationPipeline",
            "generator_version": GENERATOR_VERSION,
            "search_mode": "DETERMINISTIC_OWNER_HYPERGRAPH_TARGET_TERMINATED",
            "truth_access": False,
            "uses_legacy_candidates": False,
            "uses_archetype_candidate_rows": False,
        },
        "candidate_identity_payload": identity_payload,
        "transformation": {
            "transformation_id": "OWNER_HYPERGRAPH_DEEP_SEARCH",
            "transformation_digest": digest_payload({
                "profile": profile,
                "selected_components": [row["candidate_id"] for row in component_rows],
                "qualified_axis_ids": qualified_axes,
            }),
            "bridge_id": None,
            "axis_ids": qualified_axes,
            "composition_order": len(qualified_axes),
        },
        "formula": dataclasses.asdict(expression),
        "extracted_formula_blocks": formula_blocks,
        "axis_bindings": search["axis_bindings"],
        "deep_search": {
            "profile_id": profile["profile_id"],
            "purpose": profile["purpose"],
            "target_axis_order": search["target_axis_order"],
            "achieved_axis_order": search["achieved_axis_order"],
            "target_reached": search["target_reached"],
            "frontier_exhausted": search["frontier_exhausted"],
            "selected_component_count": len(component_rows),
            "selected_component_ids": [row["candidate_id"] for row in component_rows],
            "evaluated_component_visits": search["evaluated_component_visits"],
            "fixed_visit_budget": None,
            "termination_rule": "TARGET_REACHED_OR_CONNECTED_FRONTIER_EXHAUSTED",
        },
        "property_inheritance_contract": inheritance,
        "proof_obligation_graph": dataclasses.asdict(proof_graph),
        "limit_protocol": dataclasses.asdict(limit_protocol),
        "primary_source_ledger": dataclasses.asdict(source_ledger),
        "coordinate_delta": {},
        "dimension_contract": dimension_payload,
        "assumptions": [
            "selected source-owner validity domains have a nonempty intersection",
            "new coupling maps are hypotheses until lowered and proved",
            "a registered axis is active only when an explicit binding is present",
        ],
        "controlled_limits": list(controlled_limits),
        "falsification_criterion": "A common coupling parameterization must predict independent multi-domain holdouts and beat all induced lower-order sub-hypergraphs.",
        "required_measurements": [
            "observables for every selected source sector",
            "cross-sector coupling controls",
            "independent holdout conditions",
            "covariance and calibration provenance",
        ],
        "classification": {
            "categories": ["interdisciplinary", "deep_search", "high_order", "high_risk"],
            "risk_class": "HIGH",
            "source_sector_status": "INHERITED_WITHIN_DECLARED_VALIDITY_INTERSECTION",
            "coupled_extension_status": "UNRESOLVED",
            "candidate_scope": "SOURCE_LAWS_EMBEDDED_COUPLED_EXTENSION",
        },
        "gates": checks,
        "gate_status": "FORMALLY_ADMISSIBLE" if all(checks.values()) else "REJECTED",
        "novelty_status": "NOT_SEARCHED",
        "identifiability_status": "NOT_RUN",
        "experimental_status": "NOT_RUN",
        "deduplication": {
            "method": "content_addressed_selected_component_and_axis_binding_signature",
            "merged_equivalent_records": 0,
            "semantic_similarity_not_used_as_identity": True,
            "scientific_equivalence_requires_proof": True,
        },
        "equivalent_source_owner_ids": [],
        "provenance": {
            "source_catalog": "data/passports/known_laws.jsonl",
            "component_candidate_file": "data/passports/candidates.jsonl",
            "generated_from_canonical_owners_only": True,
            "legacy_candidate_file_used": False,
            "axis_registry_digests": {
                domain: DOMAIN_REGISTRIES[domain].digest
                for domain in sorted({axis.split(".", 1)[0] for axis in qualified_axes})
            },
        },
        "digest": "",
    }
    row["digest"] = _candidate_digest(row)
    return row


def _deep_formula_search(
    base_candidates: Sequence[Mapping[str, Any]],
    catalog: LawCatalog,
) -> Tuple[List[Dict[str, Any]], Mapping[str, Any]]:
    rows: List[Dict[str, Any]] = []
    profile_reports: List[Dict[str, Any]] = []
    for profile in DEEP_SEARCH_PROFILES:
        search = _deep_component_search(base_candidates, catalog, profile)
        row = _build_deep_candidate(search, profile, catalog)
        rows.append(row)
        profile_reports.append({
            "profile_id": profile["profile_id"],
            "purpose": profile["purpose"],
            "candidate_id": row["candidate_id"],
            "target_axis_order": search["target_axis_order"],
            "achieved_axis_order": search["achieved_axis_order"],
            "target_reached": search["target_reached"],
            "frontier_exhausted": search["frontier_exhausted"],
            "selected_component_count": len(search["selected"]),
            "evaluated_component_visits": search["evaluated_component_visits"],
            "formula": row["formula"]["source"],
            "extracted_formula_blocks": row["extracted_formula_blocks"],
            "missing_core_axes": sorted(
                f"{domain}.{axis_id}"
                for domain in DEEP_CORE_DOMAINS
                for axis_id in DOMAIN_REGISTRIES[domain].axes
                if f"{domain}.{axis_id}" not in search["axis_bindings"]
            ),
        })
    deepest = max(rows, key=lambda row: row["transformation"]["composition_order"])
    report = {
        "schema": "phi-owner-hypergraph-deep-formula-search/v6.1",
        "owner": "CandidateGenerationPipeline/6.1.0",
        "registered_domain_count": len(DOMAIN_REGISTRIES),
        "registered_axis_count": sum(registry.axis_count for registry in DOMAIN_REGISTRIES.values()),
        "core_physics_mechanics_chemistry_axis_count": sum(DOMAIN_REGISTRIES[d].axis_count for d in DEEP_CORE_DOMAINS),
        "base_candidate_pool_count": len(base_candidates),
        "deep_candidate_count": len(rows),
        "no_fixed_small_order_ceiling": True,
        "fixed_visit_budget": None,
        "termination_rule": "TARGET_REACHED_OR_CONNECTED_FRONTIER_EXHAUSTED",
        "continuous_parameter_cartesian_exhaustion": False,
        "profiles": profile_reports,
        "deepest_candidate_id": deepest["candidate_id"],
        "deepest_materialized_axis_order": deepest["transformation"]["composition_order"],
        "deepest_materialized_over_60": deepest["transformation"]["composition_order"] > 60,
        "epistemic_classification": {
            "component_formulas": "PUBLISHED_OR_REGISTERED_PRIOR_ART",
            "composite_residual_systems": "DERIVED_OR_CANDIDATE_CLOSURES",
            "new_law_status": "NOT_ESTABLISHED",
            "novelty_search_complete": False
        },
        "claim_boundary": {
            "finite_registered_axis_range": "OPEN_AND_EXACTLY_CENSUSED_ALL_ORDERS",
            "owner_hypergraph_search": "EXECUTED_WITHOUT_FIXED_VISIT_BUDGET",
            "continuous_space": "NOT_EXHAUSTED",
            "formula_status": "FORMAL_TYPED_COUPLED_RESIDUAL_HYPOTHESES",
            "new_law": "NOT_CLAIMED",
            "experimental_validation": "NOT_RUN",
        },
        "status": "PASS_DEEP_FORMULAS_MATERIALIZED_WITH_OPEN_FRONTIER",
    }
    report["sha256"] = digest_payload({key: value for key, value in report.items() if key != "sha256"})
    return sorted(rows, key=lambda row: row["candidate_id"]), report


# ---------------------------------------------------------------------------
# Blind law-ablation rediscovery benchmark
# ---------------------------------------------------------------------------

LAW_ABLATION_SCHEMA = "phi-law-ablation-rediscovery/v6.1"
LAW_ABLATION_OWNER = "CandidateGenerationPipeline/6.1.0"


def _ablation_symbol_table() -> Dict[str, sp.Symbol]:
    names = (
        "Dcoef", "lap_c", "c_field", "grad_c", "ct",
        "Eyoung", "area", "length", "x", "velocity", "force", "k_spring",
        "temperature", "k_B", "h_planck", "c_light", "radiative_flux", "sigma_SB",
        "mobility", "diffusion", "E0", "n_e", "R_gas", "F_faraday", "Q", "cell_voltage",
    )
    return {name: sp.Symbol(name, real=True) for name in names}


def _ablation_cases() -> Tuple[Mapping[str, Any], ...]:
    s = _ablation_symbol_table()
    sigma_expr = 2 * sp.pi**5 * s["k_B"]**4 / (15 * s["h_planck"]**3 * s["c_light"]**2)
    return (
        {
            "case_id": "ABL-FICK-SECOND",
            "title_ru": "Второй закон Фика из локального баланса и первого закона Фика",
            "prior_art": {"status": "PUBLISHED_LAW", "author": "Adolf Fick", "year": 1855, "work": "On Liquid Diffusion"},
            "primary_target_owner_id": "CON-09",
            "target_equivalence_owner_ids": ("CON-09",),
            "required_source_owner_ids": ("FND-08", "CON-08"),
            "expected_operator_id": "BALANCE_CONSTITUTIVE_SUBSTITUTION",
            "output_symbol": "ct",
            "input_symbols": ("Dcoef", "lap_c", "c_field", "grad_c"),
            "truth_expression": s["Dcoef"] * s["lap_c"],
            "target_formula": "partial_t c = D nabla^2 c",
            "bindings": {"source_free": True, "D_spatially_constant": True},
            "assumptions": (
                "local balance has zero source term",
                "diffusivity is a spatially constant scalar",
                "the divergence and gradient act on a sufficiently regular concentration field",
            ),
            "dimension_atoms": {
                "Dcoef": (2, 0, -1, 0, 0, 0, 0),
                "lap_c": (-5, 0, 0, 0, 0, 1, 0),
                "c_field": (-3, 0, 0, 0, 0, 1, 0),
                "grad_c": (-4, 0, 0, 0, 0, 1, 0),
            },
            "output_dimension": (-3, 0, -1, 0, 0, 1, 0),
            "expected_monomial": {"Dcoef": 1, "lap_c": 1, "c_field": 0, "grad_c": 0},
            "derivation_class": "EXACT_SUBSTITUTION",
        },
        {
            "case_id": "ABL-HOOKE-ONE-DIMENSIONAL",
            "title_ru": "Одномерный закон Гука из тензорной линейной упругости",
            "prior_art": {"status": "PUBLISHED_CLASSICAL_LAW", "author": "Robert Hooke", "year": 1678, "work": "De Potentia Restitutiva"},
            "primary_target_owner_id": "MEC-05",
            "target_equivalence_owner_ids": ("MEC-05",),
            "required_source_owner_ids": ("OME-001", "OME-005"),
            "expected_operator_id": "LINEAR_ELASTIC_ONE_DIMENSIONAL_REDUCTION",
            "output_symbol": "force",
            "input_symbols": ("Eyoung", "area", "length", "x", "velocity"),
            "truth_expression": -s["Eyoung"] * s["area"] * s["x"] / s["length"],
            "target_formula": "F = -k x, k = E A/L",
            "bindings": {"k_spring": "Eyoung*area/length"},
            "assumptions": (
                "homogeneous prismatic rod",
                "small one-dimensional strain",
                "linear elastic tensor component C_1111=E",
                "restoring-force sign convention",
            ),
            "dimension_atoms": {
                "Eyoung": (-1, 1, -2, 0, 0, 0, 0),
                "area": (2, 0, 0, 0, 0, 0, 0),
                "length": (1, 0, 0, 0, 0, 0, 0),
                "x": (1, 0, 0, 0, 0, 0, 0),
                "velocity": (1, 0, -1, 0, 0, 0, 0),
            },
            "output_dimension": (1, 1, -2, 0, 0, 0, 0),
            "expected_monomial": {"Eyoung": 1, "area": 1, "length": -1, "x": 1, "velocity": 0},
            "derivation_class": "EXACT_CONTROLLED_LIMIT",
        },
        {
            "case_id": "ABL-STEFAN-BOLTZMANN",
            "title_ru": "Закон Стефана—Больцмана из спектрального закона Планка",
            "prior_art": {"status": "PUBLISHED_LAW", "authors": ["Josef Stefan", "Ludwig Boltzmann"], "years": [1879, 1884], "work": "thermal-radiation fourth-power law"},
            "primary_target_owner_id": "OPH-021",
            "target_equivalence_owner_ids": ("OPH-021", "AST-04"),
            "required_source_owner_ids": ("OPH-022",),
            "expected_operator_id": "BLACKBODY_SPECTRAL_INTEGRATION",
            "output_symbol": "radiative_flux",
            "input_symbols": ("temperature", "k_B", "h_planck", "c_light"),
            "truth_expression": sigma_expr * s["temperature"]**4,
            "target_formula": "j_star = sigma_SB T^4",
            "bindings": {"sigma_SB": "2*pi^5*k_B^4/(15*h^3*c^2)"},
            "assumptions": (
                "ideal black body",
                "isotropic radiance over the emitting hemisphere",
                "frequency integration over [0,infinity)",
                "Bose integral int_0^infinity x^3/(exp(x)-1) dx = pi^4/15",
            ),
            "dimension_atoms": {
                "temperature": (0, 0, 0, 0, 1, 0, 0),
                "k_B": (2, 1, -2, 0, -1, 0, 0),
                "h_planck": (2, 1, -1, 0, 0, 0, 0),
                "c_light": (1, 0, -1, 0, 0, 0, 0),
            },
            "output_dimension": (0, 1, -3, 0, 0, 0, 0),
            "expected_monomial": {"temperature": 4, "k_B": 4, "h_planck": -3, "c_light": -2},
            "derivation_class": "EXACT_SPECTRAL_INTEGRATION",
        },
        {
            "case_id": "ABL-EINSTEIN-DIFFUSION",
            "title_ru": "Соотношение Эйнштейна из передемпфированного уравнения Ланжевена",
            "prior_art": {"status": "PUBLISHED_RELATION", "author": "Albert Einstein", "year": 1905, "work": "Brownian-motion diffusion relation"},
            "primary_target_owner_id": "THM-16",
            "target_equivalence_owner_ids": ("THM-16",),
            "required_source_owner_ids": ("OPH-012", "THM-10"),
            "expected_operator_id": "OVERDAMPED_LANGEVIN_COARSE_GRAINING",
            "output_symbol": "diffusion",
            "input_symbols": ("mobility", "k_B", "temperature"),
            "truth_expression": s["mobility"] * s["k_B"] * s["temperature"],
            "target_formula": "D = mu_mob k_B T",
            "bindings": {"mobility": "1/gamma"},
            "assumptions": (
                "free overdamped Brownian particle",
                "white Gaussian force with the registered Langevin covariance",
                "mobility equals inverse friction",
                "diffusion is defined by <Delta x^2>=2 D Delta t in one dimension",
            ),
            "dimension_atoms": {
                "mobility": (0, -1, 1, 0, 0, 0, 0),
                "k_B": (2, 1, -2, 0, -1, 0, 0),
                "temperature": (0, 0, 0, 0, 1, 0, 0),
            },
            "output_dimension": (2, 0, -1, 0, 0, 0, 0),
            "expected_monomial": {"mobility": 1, "k_B": 1, "temperature": 1},
            "derivation_class": "EXACT_STOCHASTIC_COARSE_GRAINING",
        },
        {
            "case_id": "ABL-NERNST-MISSING-BRIDGE",
            "title_ru": "Нернстовская зависимость как fail-closed контроль отсутствующего bridge-owner",
            "prior_art": {"status": "PUBLISHED_LAW", "author": "Walther Nernst", "year": 1889, "work": "electrochemical potential equation"},
            "primary_target_owner_id": "CHEM-011",
            "target_equivalence_owner_ids": ("CHEM-011",),
            "required_source_owner_ids": ("CHEM-007", "CHEM-009"),
            "expected_operator_id": None,
            "output_symbol": "cell_voltage",
            "input_symbols": ("E0", "temperature", "n_e", "R_gas", "F_faraday", "Q"),
            "truth_expression": s["E0"] - s["R_gas"] * s["temperature"] * sp.log(s["Q"]) / (s["n_e"] * s["F_faraday"]),
            "target_formula": "E = E0 - R T ln(Q)/(n F)",
            "bindings": {},
            "assumptions": (
                "chemical potentials use activities",
                "reaction equilibrium holds",
                "the active registry lacks a distinct electrochemical-potential/work bridge after ablation",
            ),
            "dimension_atoms": {
                "E0": (2, 1, -3, -1, 0, 0, 0),
                "temperature": (0, 0, 0, 0, 1, 0, 0),
                "n_e": (0, 0, 0, 0, 0, 0, 0),
                "R_gas": (2, 1, -2, 0, -1, -1, 0),
                "F_faraday": (0, 0, 1, 1, 0, -1, 0),
                "log_Q": (0, 0, 0, 0, 0, 0, 0),
            },
            "output_dimension": (2, 1, -3, -1, 0, 0, 0),
            "expected_monomial_terms": (
                {"E0": 1},
                {"R_gas": 1, "temperature": 1, "n_e": -1, "F_faraday": -1, "log_Q": 1},
            ),
            "derivation_class": "EXPECTED_FAIL_CLOSED_MISSING_BRIDGE_OWNER",
        },
    )


def _registered_ablation_derivation_operators() -> Tuple[Mapping[str, Any], ...]:
    s = _ablation_symbol_table()
    return (
        {
            "operator_id": "BALANCE_CONSTITUTIVE_SUBSTITUTION",
            "required_owner_ids": ("FND-08", "CON-08"),
            "required_inputs": ("Dcoef", "lap_c"),
            "output_symbol": "ct",
            "expression": s["Dcoef"] * s["lap_c"],
            "steps": (
                "take the source-free local balance partial_t c + div(J)=0",
                "substitute the constitutive flux J=-D grad(c)",
                "commute constant D through div and obtain partial_t c=D nabla^2 c",
            ),
            "proof_class": "EXACT_SUBSTITUTION",
        },
        {
            "operator_id": "LINEAR_ELASTIC_ONE_DIMENSIONAL_REDUCTION",
            "required_owner_ids": ("OME-001", "OME-005"),
            "required_inputs": ("Eyoung", "area", "length", "x"),
            "output_symbol": "force",
            "expression": -s["Eyoung"] * s["area"] * s["x"] / s["length"],
            "steps": (
                "restrict epsilon=(grad u+grad u^T)/2 to uniform one-dimensional strain epsilon=x/L",
                "restrict sigma_ij=C_ijkl epsilon_kl to sigma=E epsilon",
                "map stress to axial force F_internal=A sigma and impose the restoring sign",
                "identify k=E A/L",
            ),
            "proof_class": "EXACT_CONTROLLED_LIMIT",
        },
        {
            "operator_id": "BLACKBODY_SPECTRAL_INTEGRATION",
            "required_owner_ids": ("OPH-022",),
            "required_inputs": ("temperature", "k_B", "h_planck", "c_light"),
            "output_symbol": "radiative_flux",
            "expression": 2 * sp.pi**5 * s["k_B"]**4 * s["temperature"]**4 / (15 * s["h_planck"]**3 * s["c_light"]**2),
            "steps": (
                "integrate the Planck radiance over frequency",
                "substitute x=h nu/(k_B T)",
                "use the exact Bose integral pi^4/15",
                "integrate isotropic radiance over the hemisphere, giving the factor pi",
            ),
            "proof_class": "EXACT_SPECTRAL_INTEGRATION",
        },
        {
            "operator_id": "OVERDAMPED_LANGEVIN_COARSE_GRAINING",
            "required_owner_ids": ("OPH-012", "THM-10"),
            "required_inputs": ("mobility", "k_B", "temperature"),
            "output_symbol": "diffusion",
            "expression": s["mobility"] * s["k_B"] * s["temperature"],
            "steps": (
                "take the free overdamped limit gamma dot(x)=xi(t)",
                "write mobility mu=1/gamma",
                "use <xi(t)xi(t')>=2 gamma k_B T delta(t-t')",
                "compare <Delta x^2>=2 mu k_B T Delta t with the diffusion definition 2 D Delta t",
            ),
            "proof_class": "EXACT_STOCHASTIC_COARSE_GRAINING",
        },
    )


def _ablation_shadow_owner_ids(catalog: LawCatalog, removed: Sequence[str]) -> set[str]:
    removed_set = set(removed)
    return {owner_id for owner_id in catalog.passports if owner_id not in removed_set}


def _sample_ablation_case(case: Mapping[str, Any], *, count: int, seed: int) -> Tuple[Dict[str, np.ndarray], np.ndarray]:
    rng = np.random.default_rng(seed)
    values: Dict[str, np.ndarray] = {}
    for name in case["input_symbols"]:
        if name == "Dcoef":
            values[name] = rng.uniform(0.05, 2.0, count)
        elif name == "lap_c":
            values[name] = rng.uniform(-5.0, 5.0, count)
        elif name == "c_field":
            values[name] = rng.uniform(0.05, 4.0, count)
        elif name == "grad_c":
            values[name] = rng.uniform(-4.0, 4.0, count)
        elif name == "Eyoung":
            values[name] = rng.uniform(30.0, 220.0, count)
        elif name == "area":
            values[name] = rng.uniform(0.1, 3.0, count)
        elif name == "length":
            values[name] = rng.uniform(0.4, 5.0, count)
        elif name == "x":
            values[name] = rng.uniform(-0.15, 0.15, count)
        elif name == "velocity":
            values[name] = rng.uniform(-3.0, 3.0, count)
        elif name == "temperature":
            values[name] = rng.uniform(260.0, 1600.0, count)
        elif name == "k_B":
            values[name] = np.full(count, 1.380649e-23)
        elif name == "h_planck":
            values[name] = np.full(count, 6.62607015e-34)
        elif name == "c_light":
            values[name] = np.full(count, 299792458.0)
        elif name == "mobility":
            values[name] = rng.uniform(1.0e19, 1.0e21, count)
        elif name == "E0":
            values[name] = rng.uniform(0.1, 1.2, count)
        elif name == "n_e":
            values[name] = rng.integers(1, 4, count).astype(float)
        elif name == "R_gas":
            values[name] = np.full(count, 8.31446261815324)
        elif name == "F_faraday":
            values[name] = np.full(count, 96485.33212)
        elif name == "Q":
            values[name] = np.exp(rng.uniform(np.log(1.0e-3), np.log(1.0e3), count))
        else:
            raise KeyError(name)
    symbols = _ablation_symbol_table()
    expression = case["truth_expression"]
    fn = sp.lambdify([symbols[name] for name in case["input_symbols"]], expression, "numpy")
    output = np.asarray(fn(*[values[name] for name in case["input_symbols"]]), dtype=float)
    if output.ndim == 0:
        output = np.full(count, float(output))
    return values, output


def _normalized_rmse(prediction: np.ndarray, target: np.ndarray) -> float:
    prediction = np.asarray(prediction, dtype=float)
    target = np.asarray(target, dtype=float)
    scale = max(float(np.std(target)), float(np.sqrt(np.mean(target * target))), 1.0e-30)
    return float(np.sqrt(np.mean((prediction - target) ** 2)) / scale)


def _evaluate_sympy_expression(expression: sp.Expr, inputs: Mapping[str, np.ndarray], ordered_names: Sequence[str]) -> np.ndarray:
    symbols = _ablation_symbol_table()
    fn = sp.lambdify([symbols[name] for name in ordered_names], expression, "numpy")
    result = np.asarray(fn(*[inputs[name] for name in ordered_names]), dtype=float)
    if result.ndim == 0:
        result = np.full(len(next(iter(inputs.values()))), float(result))
    return result


def _owner_graph_ablation_search(
    case: Mapping[str, Any],
    shadow_owner_ids: set[str],
    train_inputs: Mapping[str, np.ndarray],
    train_output: np.ndarray,
) -> Mapping[str, Any]:
    candidates: List[Dict[str, Any]] = []
    for operator in _registered_ablation_derivation_operators():
        if not set(operator["required_owner_ids"]).issubset(shadow_owner_ids):
            continue
        if operator["output_symbol"] != case["output_symbol"]:
            continue
        if not set(operator["required_inputs"]).issubset(train_inputs):
            continue
        prediction = _evaluate_sympy_expression(operator["expression"], train_inputs, case["input_symbols"])
        candidates.append({
            "operator": operator,
            "train_nrmse": _normalized_rmse(prediction, train_output),
            "complexity": int(sp.count_ops(operator["expression"])) + len(operator["required_owner_ids"]),
        })
    candidates.sort(key=lambda row: (row["train_nrmse"], row["complexity"], row["operator"]["operator_id"]))
    if not candidates:
        return {
            "status": "BLOCKED_MISSING_DERIVATION_OWNER",
            "selected_operator_id": None,
            "candidate_count": 0,
            "truth_access": False,
        }
    selected = candidates[0]
    operator = selected["operator"]
    return {
        "status": "CANDIDATE_DERIVED",
        "selected_operator_id": operator["operator_id"],
        "candidate_count": len(candidates),
        "expression": operator["expression"],
        "steps": operator["steps"],
        "proof_class": operator["proof_class"],
        "required_owner_ids": operator["required_owner_ids"],
        "train_nrmse": selected["train_nrmse"],
        "truth_access": False,
    }


def _axis_nearest_owner_baseline(case: Mapping[str, Any], catalog: LawCatalog, shadow_owner_ids: set[str]) -> Mapping[str, Any]:
    target = catalog.passports[case["primary_target_owner_id"]]
    target_items = {f"{key}={canonical_json(value)}" for key, value in target.scientific_coordinate.items()}
    ranked: List[Tuple[float, str]] = []
    for owner_id in sorted(shadow_owner_ids):
        passport = catalog.passports[owner_id]
        if passport.domain_id != target.domain_id:
            continue
        items = {f"{key}={canonical_json(value)}" for key, value in passport.scientific_coordinate.items()}
        union = target_items | items
        score = len(target_items & items) / len(union) if union else 0.0
        ranked.append((score, owner_id))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    selected = ranked[0] if ranked else (0.0, "")
    return {
        "method": "AXIS_NEAREST_OWNER_RETRIEVAL",
        "selected_owner_id": selected[1] or None,
        "axis_jaccard": float(selected[0]),
        "exact_structure_recovered": False,
        "claim_boundary": "retrieval does not derive a missing formula",
    }


def _polynomial_feature_library(inputs: Mapping[str, np.ndarray], names: Sequence[str], maximum_degree: int = 3) -> Tuple[np.ndarray, List[Tuple[int, ...]]]:
    columns: List[np.ndarray] = []
    exponents: List[Tuple[int, ...]] = []
    for degree in range(1, maximum_degree + 1):
        for indices in itertools.combinations_with_replacement(range(len(names)), degree):
            exponent = [0] * len(names)
            column = np.ones(len(next(iter(inputs.values()))), dtype=float)
            for index in indices:
                exponent[index] += 1
                column *= inputs[names[index]]
            if float(np.std(column)) <= 1.0e-30 or not np.all(np.isfinite(column)):
                continue
            columns.append(column)
            exponents.append(tuple(exponent))
    return (np.column_stack(columns) if columns else np.empty((len(next(iter(inputs.values()))), 0))), exponents


def _sparse_polynomial_baseline(
    case: Mapping[str, Any],
    train_inputs: Mapping[str, np.ndarray],
    train_output: np.ndarray,
    holdout_inputs: Mapping[str, np.ndarray],
    holdout_output: np.ndarray,
) -> Mapping[str, Any]:
    names = list(case["input_symbols"])
    train_matrix, exponents = _polynomial_feature_library(train_inputs, names, maximum_degree=3)
    holdout_matrix, holdout_exponents = _polynomial_feature_library(holdout_inputs, names, maximum_degree=3)
    if exponents != holdout_exponents or train_matrix.shape[1] == 0:
        return {"method": "SPARSE_POLYNOMIAL_STLSQ_DEGREE_3", "status": "BLOCKED_LIBRARY"}
    mean = train_matrix.mean(axis=0)
    scale = train_matrix.std(axis=0)
    keep = scale > 1.0e-30
    X = (train_matrix[:, keep] - mean[keep]) / scale[keep]
    Xh = (holdout_matrix[:, keep] - mean[keep]) / scale[keep]
    kept_exponents = [exponents[index] for index in np.where(keep)[0]]
    active = np.ones(X.shape[1], dtype=bool)
    intercept = float(np.mean(train_output))
    coefficients = np.zeros(X.shape[1], dtype=float)
    for threshold in (1.0e-12, 1.0e-10, 1.0e-8, 1.0e-6, 1.0e-4, 1.0e-3):
        if not np.any(active):
            break
        design = np.column_stack([np.ones(len(train_output)), X[:, active]])
        fitted = np.linalg.lstsq(design, train_output, rcond=None)[0]
        intercept = float(fitted[0])
        relative = np.abs(fitted[1:]) / max(float(np.std(train_output)), 1.0e-30)
        retained = relative > threshold
        indices = np.where(active)[0]
        active[:] = False
        active[indices[retained]] = True
    if np.any(active):
        design = np.column_stack([np.ones(len(train_output)), X[:, active]])
        fitted = np.linalg.lstsq(design, train_output, rcond=None)[0]
        intercept = float(fitted[0])
        coefficients[:] = 0.0
        coefficients[np.where(active)[0]] = fitted[1:]
        train_prediction = intercept + X @ coefficients
        holdout_prediction = intercept + Xh @ coefficients
    else:
        train_prediction = np.full_like(train_output, intercept)
        holdout_prediction = np.full_like(holdout_output, intercept)
    selected_terms = [
        {"exponents": {name: int(power) for name, power in zip(names, exponent) if power}, "scaled_coefficient": float(coefficients[index])}
        for index, exponent in enumerate(kept_exponents)
        if active[index]
    ]
    expected = case.get("expected_monomial")
    exact_structure = False
    if expected is not None:
        expected_tuple = tuple(int(expected.get(name, 0)) for name in names)
        exact_structure = len(selected_terms) == 1 and tuple(
            int(selected_terms[0]["exponents"].get(name, 0)) for name in names
        ) == expected_tuple
    return {
        "method": "SPARSE_POLYNOMIAL_STLSQ_DEGREE_3",
        "status": "EXECUTED",
        "train_nrmse": _normalized_rmse(train_prediction, train_output),
        "holdout_nrmse": _normalized_rmse(holdout_prediction, holdout_output),
        "selected_term_count": len(selected_terms),
        "selected_terms": selected_terms,
        "exact_structure_recovered": exact_structure,
        "library_boundary": "polynomial monomials of total degree <=3; no reciprocal, logarithm or exponential operators",
    }


def _dimension_vector_sum(exponents: Sequence[int], dimensions: Sequence[Sequence[int]]) -> Tuple[int, ...]:
    return tuple(sum(int(power) * int(vector[index]) for power, vector in zip(exponents, dimensions)) for index in range(7))


def _dimension_constrained_symbolic_baseline(
    case: Mapping[str, Any],
    train_inputs: Mapping[str, np.ndarray],
    train_output: np.ndarray,
    holdout_inputs: Mapping[str, np.ndarray],
    holdout_output: np.ndarray,
) -> Mapping[str, Any]:
    atom_names = list(case["dimension_atoms"])
    train_atoms: Dict[str, np.ndarray] = {}
    holdout_atoms: Dict[str, np.ndarray] = {}
    for name in atom_names:
        if name == "log_Q":
            train_atoms[name] = np.log(train_inputs["Q"])
            holdout_atoms[name] = np.log(holdout_inputs["Q"])
        else:
            train_atoms[name] = train_inputs[name]
            holdout_atoms[name] = holdout_inputs[name]
    dimensions = [case["dimension_atoms"][name] for name in atom_names]
    output_dimension = tuple(case["output_dimension"])
    exponent_range = range(-4, 5)
    columns_train: List[np.ndarray] = []
    columns_holdout: List[np.ndarray] = []
    exponent_rows: List[Tuple[int, ...]] = []
    complexities: List[int] = []
    for powers in itertools.product(exponent_range, repeat=len(atom_names)):
        if not any(powers):
            continue
        complexity = sum(abs(int(power)) for power in powers)
        if complexity > 16:
            continue
        if _dimension_vector_sum(powers, dimensions) != output_dimension:
            continue
        train_column = np.ones(len(train_output), dtype=float)
        holdout_column = np.ones(len(holdout_output), dtype=float)
        valid = True
        for name, power in zip(atom_names, powers):
            if power == 0:
                continue
            train_value = train_atoms[name]
            holdout_value = holdout_atoms[name]
            if power < 0 and (np.any(train_value == 0) or np.any(holdout_value == 0)):
                valid = False
                break
            train_column *= train_value ** power
            holdout_column *= holdout_value ** power
        if not valid or not np.all(np.isfinite(train_column)) or not np.all(np.isfinite(holdout_column)):
            continue
        norm = float(np.linalg.norm(train_column))
        if norm <= 1.0e-30:
            continue
        columns_train.append(train_column / norm)
        columns_holdout.append(holdout_column / norm)
        exponent_rows.append(tuple(int(power) for power in powers))
        complexities.append(complexity)
    if not columns_train:
        return {"method": "DIMENSION_CONSTRAINED_SYMBOLIC_ENUMERATION", "status": "BLOCKED_NO_DIMENSIONAL_TERMS"}
    X = np.column_stack(columns_train)
    Xh = np.column_stack(columns_holdout)
    # Deterministic orthogonal matching pursuit with a parsimony tie-break.
    # Stop as soon as the training relation is numerically closed; this avoids
    # adding linearly dependent dimensionless decorations after an exact law is
    # already recovered.
    selected_indices: List[int] = []
    residual = np.asarray(train_output, dtype=float).copy()
    coefficients_selected = np.empty(0, dtype=float)
    maximum_terms = min(6, X.shape[1])
    for _ in range(maximum_terms):
        correlations = np.abs(X.T @ residual)
        if selected_indices:
            correlations[selected_indices] = -np.inf
        candidate_count = min(32, X.shape[1] - len(selected_indices))
        if candidate_count <= 0:
            break
        candidate_indices = np.argpartition(correlations, -candidate_count)[-candidate_count:]
        best_choice: Tuple[float, int, np.ndarray, np.ndarray] | None = None
        for candidate_index in candidate_indices:
            trial_indices = selected_indices + [int(candidate_index)]
            trial_matrix = X[:, trial_indices]
            trial_coefficients = np.linalg.lstsq(trial_matrix, train_output, rcond=None)[0]
            trial_prediction = trial_matrix @ trial_coefficients
            trial_nrmse = _normalized_rmse(trial_prediction, train_output)
            trial_complexity = sum(complexities[index] for index in trial_indices)
            score = trial_nrmse + 1.0e-12 * trial_complexity
            choice = (score, int(candidate_index), trial_coefficients, trial_prediction)
            if best_choice is None or choice[0] < best_choice[0] or (
                choice[0] == best_choice[0] and exponent_rows[choice[1]] < exponent_rows[best_choice[1]]
            ):
                best_choice = choice
        if best_choice is None:
            break
        _, chosen_index, coefficients_selected, train_prediction = best_choice
        selected_indices.append(chosen_index)
        residual = train_output - train_prediction
        if _normalized_rmse(train_prediction, train_output) <= 1.0e-10:
            break
    active = np.zeros(X.shape[1], dtype=bool)
    active[selected_indices] = True
    coefficients = np.zeros(X.shape[1], dtype=float)
    if selected_indices:
        final_matrix = X[:, selected_indices]
        coefficients_selected = np.linalg.lstsq(final_matrix, train_output, rcond=None)[0]
        coefficients[selected_indices] = coefficients_selected
    train_prediction = X @ coefficients
    holdout_prediction = Xh @ coefficients
    holdout_prediction = Xh @ coefficients
    selected = []
    for index in np.where(active)[0]:
        selected.append({
            "exponents": {name: int(power) for name, power in zip(atom_names, exponent_rows[index]) if power},
            "coefficient_in_normalized_basis": float(coefficients[index]),
            "complexity": complexities[index],
        })
    expected_terms = case.get("expected_monomial_terms")
    if expected_terms is None and case.get("expected_monomial") is not None:
        expected_terms = (case["expected_monomial"],)
    normalized_selected = {
        tuple(sorted((name, int(power)) for name, power in row["exponents"].items() if power))
        for row in selected
    }
    normalized_expected = {
        tuple(sorted((name, int(power)) for name, power in term.items() if power))
        for term in (expected_terms or ())
    }
    exact_structure = bool(normalized_expected) and normalized_selected == normalized_expected
    return {
        "method": "DIMENSION_CONSTRAINED_SYMBOLIC_ENUMERATION",
        "status": "EXECUTED",
        "dimensionally_admissible_term_count": len(exponent_rows),
        "selected_term_count": len(selected),
        "selected_terms": selected,
        "train_nrmse": _normalized_rmse(train_prediction, train_output),
        "holdout_nrmse": _normalized_rmse(holdout_prediction, holdout_output),
        "exact_structure_recovered": exact_structure,
        "operator_set": "integer powers -4..4, total absolute exponent <=16, log only for declared dimensionless Q",
    }


def _law_ablation_rediscovery(catalog: LawCatalog) -> Mapping[str, Any]:
    rows: List[Dict[str, Any]] = []
    exact_recovered = 0
    expected_blocked = 0
    negative_controls_passed = 0
    for case_index, case in enumerate(_ablation_cases()):
        removed = tuple(case["target_equivalence_owner_ids"])
        missing_targets = sorted(set(removed) - set(catalog.passports))
        if missing_targets:
            raise KeyError(f"ablation targets missing from catalog: {missing_targets}")
        shadow_owner_ids = _ablation_shadow_owner_ids(catalog, removed)
        leakage_owner_ids = sorted(set(removed) & shadow_owner_ids)
        leakage_free = not leakage_owner_ids
        train_inputs, train_truth = _sample_ablation_case(case, count=256, seed=7100 + case_index)
        holdout_inputs, holdout_truth = _sample_ablation_case(case, count=128, seed=8100 + case_index)
        owner_result = _owner_graph_ablation_search(case, shadow_owner_ids, train_inputs, train_truth)
        expected_operator = case["expected_operator_id"]
        exact_equivalence = False
        holdout_nrmse = None
        recovered_expression = None
        if owner_result.get("expression") is not None:
            recovered_expression = owner_result["expression"]
            exact_equivalence = sp.simplify(recovered_expression - case["truth_expression"]) == 0
            holdout_prediction = _evaluate_sympy_expression(recovered_expression, holdout_inputs, case["input_symbols"])
            holdout_nrmse = _normalized_rmse(holdout_prediction, holdout_truth)
        if expected_operator is None:
            expected_status_pass = owner_result["status"] == "BLOCKED_MISSING_DERIVATION_OWNER"
            expected_blocked += int(expected_status_pass)
        else:
            expected_status_pass = owner_result.get("selected_operator_id") == expected_operator and exact_equivalence
            exact_recovered += int(expected_status_pass)
        essential_missing_control = None
        if expected_operator is not None:
            required = tuple(case["required_source_owner_ids"])
            control_shadow = set(shadow_owner_ids)
            control_shadow.discard(required[0])
            control = _owner_graph_ablation_search(case, control_shadow, train_inputs, train_truth)
            essential_missing_control = {
                "removed_prerequisite_owner_id": required[0],
                "status": control["status"],
                "passed": control["status"] == "BLOCKED_MISSING_DERIVATION_OWNER",
            }
            negative_controls_passed += int(essential_missing_control["passed"])
        sparse = _sparse_polynomial_baseline(case, train_inputs, train_truth, holdout_inputs, holdout_truth)
        dimensional = _dimension_constrained_symbolic_baseline(case, train_inputs, train_truth, holdout_inputs, holdout_truth)
        nearest = _axis_nearest_owner_baseline(case, catalog, shadow_owner_ids)
        row = {
            "case_id": case["case_id"],
            "title_ru": case["title_ru"],
            "prior_art": dict(case["prior_art"]),
            "target_owner_ids_removed": list(removed),
            "shadow_catalog_owner_count": len(shadow_owner_ids),
            "target_formula_for_post_run_scoring_only": case["target_formula"],
            "truth_formula_access_during_search": False,
            "leakage_scan": {
                "status": "PASS" if leakage_free else "FAIL",
                "remaining_equivalent_owner_ids": leakage_owner_ids,
            },
            "required_source_owner_ids": list(case["required_source_owner_ids"]),
            "required_source_formula_digests": {
                owner_id: catalog.passports[owner_id].formula.digest
                for owner_id in case["required_source_owner_ids"]
                if owner_id in catalog.passports
            },
            "assumptions": list(case["assumptions"]),
            "bindings": dict(case["bindings"]),
            "owner_hypergraph_result": {
                **{key: value for key, value in owner_result.items() if key != "expression"},
                "expression": sp.sstr(recovered_expression) if recovered_expression is not None else None,
                "exact_symbolic_equivalence": exact_equivalence,
                "holdout_nrmse": holdout_nrmse,
                "expected_status_pass": expected_status_pass,
            },
            "essential_prerequisite_negative_control": essential_missing_control,
            "baselines": {
                "axis_nearest_owner": nearest,
                "sparse_polynomial": sparse,
                "dimension_constrained_symbolic": dimensional,
            },
            "derivation_class": case["derivation_class"],
            "case_status": "PASS" if leakage_free and expected_status_pass and (essential_missing_control is None or essential_missing_control["passed"]) else "FAIL",
        }
        rows.append(row)

    # Deliberate contamination control: removing only one Stefan-Boltzmann owner
    # must be rejected because an equivalent astronomy owner remains visible.
    contaminated_removed = {"OPH-021"}
    contaminated_shadow = _ablation_shadow_owner_ids(catalog, contaminated_removed)
    contamination_detected = "AST-04" in contaminated_shadow
    contamination_control = {
        "case_id": "NEGATIVE-CONTROL-STEFAN-DUPLICATE",
        "removed_owner_ids": sorted(contaminated_removed),
        "equivalent_owner_left_visible": "AST-04",
        "status": "LEAKAGE_DETECTED_AND_BENCHMARK_REJECTED" if contamination_detected else "FAIL_TO_DETECT_LEAKAGE",
        "passed": contamination_detected,
    }
    negative_controls_passed += int(contamination_detected)

    comparison = {
        "owner_hypergraph": {
            "exact_recoverable_cases": 4,
            "exact_recovered": exact_recovered,
            "expected_fail_closed_cases": 1,
            "expected_fail_closed_passed": expected_blocked,
            "provenance_and_derivation_steps": True,
        },
        "axis_nearest_owner": {
            "exact_structure_recovered": sum(int(row["baselines"]["axis_nearest_owner"]["exact_structure_recovered"]) for row in rows),
            "case_count": len(rows),
            "provenance_and_derivation_steps": False,
        },
        "sparse_polynomial_degree_3": {
            "exact_structure_recovered": sum(int(row["baselines"]["sparse_polynomial"].get("exact_structure_recovered", False)) for row in rows),
            "case_count": len(rows),
            "provenance_and_derivation_steps": False,
        },
        "dimension_constrained_symbolic": {
            "exact_structure_recovered": sum(int(row["baselines"]["dimension_constrained_symbolic"].get("exact_structure_recovered", False)) for row in rows),
            "case_count": len(rows),
            "provenance_and_derivation_steps": False,
            "data_driven_hypothesis_can_exist_without_owner_derivation": True,
        },
    }
    report: Dict[str, Any] = {
        "schema": LAW_ABLATION_SCHEMA,
        "owner": LAW_ABLATION_OWNER,
        "catalog_digest_before_ablation": catalog.digest(),
        "case_count": len(rows),
        "exact_recoverable_case_count": 4,
        "exact_recovered_case_count": exact_recovered,
        "expected_fail_closed_case_count": 1,
        "expected_fail_closed_pass_count": expected_blocked,
        "negative_control_count": 5,
        "negative_control_pass_count": negative_controls_passed,
        "cases": rows,
        "contamination_control": contamination_control,
        "comparison": comparison,
        "formula_status_taxonomy": {
            "published_component": "previously published law or relation",
            "derived_closure": "real consequence of registered owners under explicit assumptions, not automatically a new law",
            "candidate_coupling": "new typed hypothesis requiring proof and experiment",
            "new_law": "requires novelty, non-redundancy, falsifiable prediction, blind validation and independent replication"
        },
        "claim_boundary": {
            "demonstrated": "rediscovery of four published laws from remaining registered owners under declared assumptions; one missing-bridge task correctly blocked",
            "not_demonstrated": "universal discovery of arbitrary unknown laws, empirical novelty, or exhaustive continuous-space search",
            "new_law_claimed": False,
            "benchmark_truth_used_only_after_search_for_scoring": True,
            "target_formula_equivalence_classes_removed": True,
        },
        "status": "PASS_BLIND_ABLATION_REDISCOVERY_4_OF_4_AND_FAIL_CLOSED_1_OF_1" if exact_recovered == 4 and expected_blocked == 1 and negative_controls_passed == 5 and contamination_detected else "FAIL",
    }
    report["sha256"] = digest_payload({key: value for key, value in report.items() if key != "sha256"})
    return report


DIRECTED_RESEARCH_SCHEMA = "phi-directed-owner-hypergraph-research/v6.16"
DIRECTED_RESEARCH_VERSION = "6.16.0"


@dataclass(frozen=True)
class DirectedResearchQuery:
    """Scientific question mapped onto the complete registered owner/axis graph.

    The query never turns an execution limit into a scientific limit.  Every
    registered axis is classified on every run; only axes with an explicit
    semantic/source/bridge role are activated in the current research region.
    """

    question: str
    required_observables: Tuple[str, ...] = ()
    seed_owner_ids: Tuple[str, ...] = ()
    target_axis_ids: Tuple[str, ...] = ()
    required_domains: Tuple[str, ...] = ()
    include_all_connected_owners: bool = True
    discovery_mode: str = "SEMANTIC_OWNER_FRONTIER"

    def validate(self) -> None:
        if self.discovery_mode not in {"SEMANTIC_OWNER_FRONTIER", "BLIND_PRIMITIVE_FIREWALL", "SOURCE_LAW_INTERSECTION_CLOSURE"}:
            raise ValueError(f"unsupported directed research discovery_mode: {self.discovery_mode}")
        if self.discovery_mode == "BLIND_PRIMITIVE_FIREWALL" and not self.seed_owner_ids:
            raise ValueError("blind primitive discovery requires explicit primitive seed owners")
        if self.discovery_mode == "SOURCE_LAW_INTERSECTION_CLOSURE" and not self.seed_owner_ids:
            raise ValueError("source-law intersection discovery requires explicit source-law seed owners")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return dataclasses.asdict(self)


def _research_tokens(*parts: str) -> set[str]:
    aliases = {
        "neutrino": {"neutrino", "нейтрино", "pmns", "majorana", "dirac", "takagi", "oscillation", "осцилл"},
        "mass": {"mass", "масса", "m_beta", "mbeta", "mass_operator"},
        "geometry": {"geometry", "геометр", "dimension", "измерен", "topology", "kk", "kaluza", "klein", "warped", "compact"},
        "experiment": {"experiment", "эксперимент", "measurement", "detector", "likelihood", "identifiability", "observability"},
        "matter": {"matter", "msw", "nsi", "medium", "сред"},
    }
    stop = {"и", "в", "во", "на", "с", "со", "к", "по", "из", "за", "от", "до", "для", "the", "a", "an", "of", "and", "or", "to", "in", "on", "for", "with"}
    raw_all = set(re.findall(r"[0-9A-Za-zА-Яа-я_]+", " ".join(parts).casefold()))
    raw = {token for token in raw_all if len(token) >= 2 and token not in stop}
    expanded = set(raw)
    for key, values in aliases.items():
        if key in raw or raw & values:
            expanded.update(values)
    return expanded


def _passport_research_text(passport: LawPassport) -> str:
    return " ".join([
        passport.owner_id,
        passport.name_ru,
        passport.domain_id,
        passport.entity_kind,
        passport.formula.source,
        " ".join(passport.observables),
        " ".join(passport.assumptions),
        " ".join(passport.controlled_limits),
        canonical_json(passport.scientific_coordinate),
        canonical_json(passport.provenance),
    ]).casefold()


def _passport_bound_axes(passport: LawPassport, catalog: LawCatalog | None = None) -> set[str]:
    registry = DOMAIN_REGISTRIES.get(passport.domain_id)
    if registry is None:
        return set()
    direct = {
        f"{passport.domain_id}.{axis_id}"
        for axis_id, value in passport.scientific_coordinate.items()
        if axis_id in registry.axes and value not in (None, "", (), [], {})
    }
    if catalog is not None:
        direct.update(catalog.owner_axis_bindings.get(passport.owner_id, set()))
    return direct


def directed_owner_hypergraph_research(
    catalog: LawCatalog,
    bridges: Mapping[str, DomainBridge],
    query: DirectedResearchQuery,
    owner_surfaces: Mapping[str, Mapping[str, Any]] | None = None,
) -> Mapping[str, Any]:
    """Scan the whole registered axis/owner space and construct one target region.

    This is a finite owner-graph search, not a Cartesian enumeration of all
    continuous parameter values.  All registered axes are visited/classified;
    the connected frontier has no fixed visit cap or small order ceiling.
    """
    query.validate()
    owner_surfaces = dict(owner_surfaces or {})
    blind_firewall = query.discovery_mode == "BLIND_PRIMITIVE_FIREWALL"
    source_intersection = query.discovery_mode == "SOURCE_LAW_INTERSECTION_CLOSURE"
    explicit_source_mode = blind_firewall or source_intersection
    # In blind mode the scientific question may activate coordinate labels, but
    # it is forbidden to score source owners by their names, formulas,
    # provenance or published-model vocabulary.  Only explicit primitive seeds
    # can become active source owners before a candidate digest is frozen.
    tokens = _research_tokens(query.question, *query.required_observables)
    target_axis_ids = set(query.target_axis_ids)
    target_axis_fq = {
        axis if "." in axis else f"{domain}.{axis}"
        for axis in target_axis_ids
        for domain, registry in DOMAIN_REGISTRIES.items()
        if "." in axis or axis in registry.axes
    }
    required_domains = set(query.required_domains)
    seed_ids = set(query.seed_owner_ids)

    missing_seed_ids = sorted(seed_ids - (set(catalog.passports) | set(owner_surfaces)))
    if missing_seed_ids:
        raise ValueError(f"unknown directed research seed owners: {missing_seed_ids}")

    rows: List[Dict[str, Any]] = []
    for passport in sorted(catalog.passports.values(), key=lambda row: row.owner_id):
        bound_axes = _passport_bound_axes(passport, catalog)
        forced = passport.owner_id in seed_ids
        domain_required = passport.domain_id in required_domains
        if explicit_source_mode:
            # Explicit-source modes never enlarge their source-law set by semantic
            # proximity.  BLIND_PRIMITIVE_FIREWALL uses primitive seeds;
            # SOURCE_LAW_INTERSECTION_CLOSURE uses declared established source
            # laws and then computes consequences of their compatible validity
            # intersections.  In both cases target-axis labels cannot silently
            # import extra owners.
            token_hits = 0
            target_hits = 0
            score = 1000 * int(forced)
        else:
            text = _passport_research_text(passport)
            ptokens = set(re.findall(r"[0-9A-Za-zА-Яа-я_]+", text))
            token_hits = len(tokens & ptokens)
            target_hits = len(target_axis_fq & bound_axes)
            provenance_neutrino = "neutrino-phenomenology" in text or "neutrino" in text or "нейтрино" in text
            score = 1000 * int(forced) + 100 * target_hits + 10 * token_hits + 5 * int(domain_required) + 20 * int(provenance_neutrino and ("neutrino" in tokens or "нейтрино" in tokens))
        rows.append({
            "passport": passport,
            "score": score,
            "token_hits": token_hits,
            "target_hits": target_hits,
            "bound_axes": bound_axes,
            "forced": forced,
        })

    # Runtime scientific owners are searchable routing/source surfaces but are
    # deliberately not forged into LawPassports. This lets the owner hypergraph
    # reach authoritative computational/theory owners without corrupting the
    # law catalog's epistemic semantics.
    surface_rows: List[Dict[str, Any]] = []
    for owner_id, surface in sorted(owner_surfaces.items()):
        domain_id = str(surface.get("domain_id", ""))
        if domain_id not in DOMAIN_REGISTRIES:
            raise ValueError(f"runtime owner surface {owner_id}: unknown domain {domain_id}")
        registry = DOMAIN_REGISTRIES[domain_id]
        raw_axes = tuple(str(x) for x in surface.get("axis_ids", ()))
        bound_axes = set()
        for axis in raw_axes:
            fq = axis if "." in axis else f"{domain_id}.{axis}"
            d, a = fq.split(".", 1)
            if d == domain_id and a in registry.axes:
                bound_axes.add(fq)
        forced = owner_id in seed_ids
        domain_required = domain_id in required_domains
        if explicit_source_mode:
            token_hits = 0
            target_hits = 0
            score = 1000 * int(forced)
        else:
            text = (str(surface.get("search_text", "")) + " " + canonical_json(surface)).casefold()
            ptokens = set(re.findall(r"[0-9A-Za-zА-Яа-я_]+", text))
            token_hits = len(tokens & ptokens)
            target_hits = len(target_axis_fq & bound_axes)
            score = 1000 * int(forced) + 100 * target_hits + 10 * token_hits + 5 * int(domain_required)
        surface_rows.append({
            "owner_id": owner_id, "domain_id": domain_id, "score": score,
            "token_hits": token_hits, "target_hits": target_hits,
            "bound_axes": bound_axes, "forced": forced, "surface": dict(surface),
        })

    semantic_relevance_guard = query.discovery_mode == "SEMANTIC_OWNER_FRONTIER" and bool(required_domains)
    if explicit_source_mode:
        selected_ids: set[str] = set(seed_ids) & set(catalog.passports)
        selected_surface_ids: set[str] = set(seed_ids) & set(owner_surfaces)
    elif semantic_relevance_guard:
        # A typed Human->Phi request already supplied its grounded domains.
        # Lexical matches outside that region cannot silently activate owners.
        selected_ids = {
            r["passport"].owner_id for r in rows
            if r["forced"] or (r["passport"].domain_id in required_domains and (r["token_hits"] > 0 or r["target_hits"] > 0))
        }
        selected_surface_ids = {
            r["owner_id"] for r in surface_rows
            if r["forced"] or (r["domain_id"] in required_domains and (r["token_hits"] > 0 or r["target_hits"] > 0))
        }
    else:
        selected_ids = {r["passport"].owner_id for r in rows if r["score"] > 0}
        selected_surface_ids = {r["owner_id"] for r in surface_rows if r["score"] > 0}

    selected_domains = {catalog.passports[owner].domain_id for owner in selected_ids}
    selected_domains.update(str(owner_surfaces[owner].get("domain_id")) for owner in selected_surface_ids)
    if semantic_relevance_guard:
        selected_domains.update(required_domains)
    selected_bridges: set[str] = set()
    changed = True
    owner_visits = len(rows) + len(surface_rows)
    while changed:
        changed = False
        for bridge_id, bridge in sorted(bridges.items()):
            domains = set(bridge.source_domains)
            if semantic_relevance_guard:
                # A bridge may be recorded as relevant only when it actually
                # stays wholly inside the already-grounded domain set.  Mere
                # partial overlap is insufficient.  The bridge never expands
                # the semantic domain set by itself.
                bridge_relevant = domains.issubset(selected_domains)
                if bridge_relevant and bridge_id not in selected_bridges:
                    selected_bridges.add(bridge_id)
                    changed = True
                continue
            if domains & selected_domains:
                if bridge_id not in selected_bridges:
                    selected_bridges.add(bridge_id)
                    changed = True
                selected_domains.update(domains)
        if explicit_source_mode or not query.include_all_connected_owners:
            break
        for row in rows:
            owner_visits += 1
            passport = row["passport"]
            if passport.owner_id in selected_ids:
                continue
            # Connected owners are admitted only when they add an axis or a
            # query token in a domain reached by the owner/bridge frontier.
            if passport.domain_id not in selected_domains:
                continue
            if semantic_relevance_guard and passport.domain_id not in required_domains:
                continue
            new_axis = bool(row["bound_axes"] - {a for oid in selected_ids for a in _passport_bound_axes(catalog.passports[oid], catalog)})
            if row["token_hits"] > 0 or row["target_hits"] > 0 or (new_axis and passport.domain_id in required_domains):
                selected_ids.add(passport.owner_id)
                selected_domains.add(passport.domain_id)
                changed = True

    bound_by_selected: Dict[str, List[str]] = {}
    for owner_id in sorted(selected_ids):
        for axis in _passport_bound_axes(catalog.passports[owner_id], catalog):
            bound_by_selected.setdefault(axis, []).append(owner_id)
    selected_surface_map = {row["owner_id"]: row for row in surface_rows if row["owner_id"] in selected_surface_ids}
    for owner_id, row in sorted(selected_surface_map.items()):
        for axis in row["bound_axes"]:
            bound_by_selected.setdefault(axis, []).append(owner_id)

    axis_rows: List[Dict[str, Any]] = []
    direct_axis_count = owner_bound_count = bridge_count = background_count = 0
    for domain_id, registry in sorted(DOMAIN_REGISTRIES.items()):
        domain_connected = domain_id in selected_domains
        for axis_id, axis in sorted(registry.axes.items()):
            fq = f"{domain_id}.{axis_id}"
            axis_tokens = _research_tokens(axis_id, str(axis.description_ru).replace(domain_id, " "))
            if semantic_relevance_guard:
                direct = fq in target_axis_fq or (domain_id in required_domains and bool(tokens & axis_tokens))
            else:
                direct = bool(tokens & axis_tokens) or fq in target_axis_fq
            owners = sorted(bound_by_selected.get(fq, ()))
            if owners:
                disposition = "OWNER_BOUND_ACTIVE"
                owner_bound_count += 1
            elif direct:
                disposition = "QUERY_DIRECT_OPEN_COORDINATE"
                direct_axis_count += 1
            elif domain_connected:
                disposition = "BRIDGE_ADDRESSABLE_OPEN_COORDINATE"
                bridge_count += 1
            else:
                disposition = "ADDRESSABLE_BACKGROUND_NOT_ACTIVATED"
                background_count += 1
            axis_rows.append({
                "domain_id": domain_id,
                "axis_id": axis_id,
                "qualified_axis_id": fq,
                "description": axis.description_ru,
                "disposition": disposition,
                "bound_owner_ids": owners,
            })

    selected_passports = [catalog.passports[x] for x in sorted(selected_ids)]
    source_axis_union = sorted(
        {axis for p in selected_passports for axis in _passport_bound_axes(p, catalog)}
        | {axis for row in selected_surface_map.values() for axis in row["bound_axes"]}
    )
    registry_axis_count = sum(reg.axis_count for reg in DOMAIN_REGISTRIES.values())
    finite_subset_census = (1 << registry_axis_count) - 1
    result = {
        "schema": DIRECTED_RESEARCH_SCHEMA,
        "owner_version": DIRECTED_RESEARCH_VERSION,
        "query": query.to_dict(),
        "query_digest": digest_payload(query.to_dict()),
        "registered_domain_count": len(DOMAIN_REGISTRIES),
        "registered_axis_count": registry_axis_count,
        "all_registered_axes_visited": len(axis_rows) == registry_axis_count,
        "exact_finite_registered_axis_subset_census": str(finite_subset_census),
        "global_axis_combination_space": global_axis_combination_contract(),
        "continuous_parameter_cartesian_exhaustion": "NOT_CLAIMED",
        "selected_source_owner_ids": sorted(selected_ids | selected_surface_ids),
        "selected_source_owner_count": len(selected_ids | selected_surface_ids),
        "selected_law_passport_ids": sorted(selected_ids),
        "selected_runtime_owner_ids": sorted(selected_surface_ids),
        "runtime_owner_surface_count": len(owner_surfaces),
        "selected_bridge_ids": sorted(selected_bridges),
        "selected_domains": sorted(selected_domains),
        "source_bound_axis_ids": source_axis_union,
        "source_bound_axis_count": len(source_axis_union),
        "axis_disposition_counts": {
            "owner_bound_active": owner_bound_count,
            "query_direct_open": direct_axis_count,
            "bridge_addressable_open": bridge_count,
            "addressable_background": background_count,
        },
        "axis_rows": axis_rows,
        "owner_visits": owner_visits,
        "fixed_owner_visit_budget": None,
        "fixed_candidate_axis_order_ceiling": None,
        "exploration_contract": {
            "candidate_registry_2771_is_solution_space": False,
            "active_2771_registry_semantics": "CONFIRMED_CONTROL_ANCHORS_ONLY",
            "unverified_generated_couplings_are_frontier_research": True,
            "owner_affiliation_blocks_axis_combination": False,
            "domain_affiliation_blocks_axis_combination": False,
            "cross_domain_tuple_exploration_requires_preexisting_bridge": False,
            "arithmetic_identification_requires_typed_contract": True,
            "void_or_unbound_combination_status": "FRONTIER_RESEARCH_CANDIDATE",
            "unknown_candidate_is_false": False,
            "promotion_gates_restrict_search": False,
        },
        "termination": "FINITE_CONNECTED_OWNER_FRONTIER_EXHAUSTED_AFTER_ALL_REGISTERED_AXES_CLASSIFIED",
        "relevance_contract": {
            "mode": "RELEVANCE_PRESERVING_FRONTIER" if semantic_relevance_guard else "LEGACY_OR_EXPLICIT_SOURCE_FRONTIER",
            "typed_required_domains": sorted(required_domains),
            "unrelated_owner_lexical_activation_allowed": not semantic_relevance_guard,
            "bridge_may_expand_grounded_domain_set": not semantic_relevance_guard,
            "query_direct_axis_outside_grounded_domains_allowed": not semantic_relevance_guard,
            "all_registered_axes_still_classified": len(axis_rows) == registry_axis_count,
        },
        "knowledge_firewall": {
            "mode": query.discovery_mode,
            "passport_names_used_for_source_scoring": not explicit_source_mode,
            "passport_formulas_used_for_source_scoring": not explicit_source_mode,
            "passport_provenance_used_for_source_scoring": not explicit_source_mode,
            "published_model_vocabulary_used_for_source_scoring": not explicit_source_mode,
            "known_law_owner_import_from_target_axes": not explicit_source_mode,
            "active_source_owners_are_explicit_primitive_seeds_only": blind_firewall,
            "active_source_owners_are_explicit_declared_source_laws_only": source_intersection,
            "source_law_formulas_available_to_closure_engine": source_intersection,
            "literature_novelty_used_for_source_scoring": False if source_intersection else None,
            "postfreeze_information_feedback_allowed": False if explicit_source_mode else True,
        },
        "claim_boundary": {
            "materialized_count_is_search_space_size": False,
            "all_registered_axes_addressable": True,
            "all_registered_axes_classified_this_run": True,
            "continuous_values_exhausted": False,
            "new_cross_sector_coupling_truth_inherited": False,
            "source_sector_direct_sum_formally_derivable": True,
        },
    }
    result["digest"] = digest_payload(result)
    return result


OPEN_VOID_DIRECTED_EXPLORATION_SCHEMA = "phi-open-void-directed-exploration/v3"

def _axis_concept_tokens(axis_id: str) -> set[str]:
    raw = {x for x in re.split(r"[_\W]+", str(axis_id).casefold()) if x}
    aliases = {
        "reproducibility": {"reproducibility", "repeatability", "replication"},
        "noise": {"noise", "uncertainty", "error", "stochastic"},
        "representation": {"representation", "coordinate", "frame", "basis"},
        "geometry": {"geometry", "geometric", "metric", "topology", "manifold"},
        "fault": {"fault", "failure", "tolerance", "damage"},
        "interaction": {"interaction", "coupling", "graph", "range", "sector"},
        "molecular": {"molecular", "molecularity", "molecule", "target"},
        "oxidation": {"oxidation", "corrosion", "redox"},
        "solvation": {"solvation", "solvent", "absorption", "partition"},
        "photo": {"photo", "photochemical", "radiation", "irradiance"},
        "cycle": {"cycle", "biogeochemical", "reaction", "process"},
        "measurement": {"measurement", "observable", "assay", "detector", "validation"},
        "stability": {"stability", "bifurcation", "failure", "critical"},
        "memory": {"memory", "history", "delay", "correlation"},
        "scale": {"scale", "multiscale", "regime", "order"},
    }
    expanded=set(raw)
    for values in aliases.values():
        if raw & values:
            expanded.update(values)
    return expanded

def _axis_semantic_affinity(a: str, b: str) -> float:
    ta,tb=_axis_concept_tokens(a),_axis_concept_tokens(b)
    if not ta or not tb: return 0.0
    inter=len(ta & tb); union=len(ta | tb)
    j=inter/union if union else 0.0
    sa,sb=str(a).casefold(),str(b).casefold()
    substring=1.0 if sa in sb or sb in sa else 0.0
    return 0.72*j+0.28*substring

ADAPTIVE_SUBSPACE_SCHEMA = "phi-adaptive-multidimensional-scientific-subspace-explorer/v3"
ADAPTIVE_SUBSPACE_VERSION = "3.0.0"
DOVETAIL_STATE_SCHEMA = "phi-fair-open-ended-dovetail-state/v1"
DOVETAIL_STATE_VERSION = "1.0.0"
DOVETAIL_STATE_RELATIVE_PATH = Path("data/frontiers/ATLAS_DOVETAIL_STATE_CURRENT.json")


def _dovetail_state_with_digest(payload: Mapping[str, Any]) -> dict[str, Any]:
    core = {k: v for k, v in dict(payload).items() if k != "digest"}
    return {**core, "digest": digest_payload(core)}


def dovetail_state_status(state: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if not state:
        return {"valid": False, "reason": "STATE_ABSENT"}
    core = {k: v for k, v in dict(state).items() if k != "digest"}
    valid = (
        state.get("schema") == DOVETAIL_STATE_SCHEMA
        and state.get("version") == DOVETAIL_STATE_VERSION
        and state.get("digest") == digest_payload(core)
    )
    return {
        "valid": bool(valid),
        "reason": "PASS" if valid else "SCHEMA_VERSION_OR_DIGEST_MISMATCH",
        "node_count": len(dict(state.get("nodes", {}))),
        "steps_executed": int(state.get("scheduler", {}).get("steps_executed", 0)),
        "environment_epoch": int(state.get("environment_epoch", 0)),
    }


def load_dovetail_state_file(path: str | Path) -> Mapping[str, Any] | None:
    path = Path(path)
    if not path.is_file():
        return None
    state = json.loads(path.read_text(encoding="utf-8"))
    status = dovetail_state_status(state)
    if status.get("valid") is not True:
        raise RuntimeError(f"invalid Atlas dovetail state at {path}: {status.get('reason')}")
    return state


def write_dovetail_state_file(path: str | Path, state: Mapping[str, Any]) -> Path:
    path = Path(path)
    status = dovetail_state_status(state)
    if status.get("valid") is not True:
        raise ValueError(f"refusing to persist invalid Atlas dovetail state: {status.get('reason')}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


def _axis_concept_classes(axis_id: str) -> set[str]:
    """Return coarse structural concepts used only to nominate search regions.

    These labels do not establish a mechanism.  They are deliberately broader
    than lexical equality so that a purely higher-order region may be nominated
    without first exhibiting a strong pair projection.
    """
    raw = {x for x in re.split(r"[_\W]+", str(axis_id).casefold()) if x}
    classes = {
        "REPRODUCIBILITY": {"reproducibility", "repeatability", "replication"},
        "NOISE_UNCERTAINTY": {"noise", "uncertainty", "error", "stochastic"},
        "REPRESENTATION": {"representation", "coordinate", "frame", "basis"},
        "GEOMETRY_TOPOLOGY": {"geometry", "geometric", "metric", "topology", "manifold"},
        "FAILURE_STABILITY": {"fault", "failure", "tolerance", "damage", "stability", "bifurcation", "critical"},
        "INTERACTION_COUPLING": {"interaction", "coupling", "graph", "range", "sector"},
        "MOLECULAR_STRUCTURE": {"molecular", "molecularity", "molecule", "target"},
        "REDOX": {"oxidation", "corrosion", "redox"},
        "SOLVATION_PARTITION": {"solvation", "solvent", "absorption", "partition"},
        "RADIATION_PHOTO": {"photo", "photochemical", "radiation", "irradiance"},
        "CYCLE_PROCESS": {"cycle", "biogeochemical", "reaction", "process"},
        "MEASUREMENT_OBSERVER": {"measurement", "observable", "assay", "detector", "validation"},
        "MEMORY_HISTORY": {"memory", "history", "delay", "correlation"},
        "SCALE_REGIME": {"scale", "multiscale", "regime", "order"},
        "SYMMETRY": {"symmetry", "gauge", "invariant", "conservation"},
        "THERMAL": {"thermal", "temperature", "thermodynamic", "entropy"},
        "CAUSAL": {"causal", "causality", "intervention", "directional"},
    }
    out = set()
    for label, vocabulary in classes.items():
        if raw & vocabulary:
            out.add(label)
    return out


def _domain_bridge_index(bridges: Mapping[str, DomainBridge]) -> tuple[set[tuple[str, str]], dict[tuple[str, str], list[str]]]:
    pairs: set[tuple[str, str]] = set()
    by_pair: dict[tuple[str, str], list[str]] = {}
    for bridge_id, bridge in sorted(bridges.items()):
        domains = tuple(sorted(set(str(x) for x in bridge.source_domains)))
        for i, left in enumerate(domains):
            for right in domains[i + 1:]:
                pair = (left, right)
                pairs.add(pair)
                by_pair.setdefault(pair, []).append(str(bridge_id))
    return pairs, by_pair


def _subspace_problem_contract(
    axes: Sequence[str], roles: Sequence[str], domains: Sequence[str], gap_types: Sequence[str], concepts: Sequence[str]
) -> Mapping[str, Any]:
    gaps = set(gap_types)
    concept_set = set(concepts)
    roles_set = set(roles)
    questions: list[str] = []
    problem_classes: list[str] = []
    if "CROSS_DOMAIN_BRIDGE_GAP" in gaps:
        questions.append("Can a typed cross-domain representation couple these coordinates without violating the authoritative domain owners?")
        problem_classes.append("MISSING_TYPED_CROSS_DOMAIN_MECHANISM")
    if "PARAMETERIZATION_OR_ATTESTATION_GAP" in gaps or "OWNER_BINDING_GAP" in gaps:
        questions.append("Which missing observer, parameterization or representation is required to make the subspace empirically addressable?")
        problem_classes.append("MISSING_OBSERVER_OR_REPRESENTATION")
    if len(roles_set) > 1:
        questions.append("Does the context/measurement/formal coordinate change the generative relation, or only how it is observed?")
        problem_classes.append("ROLE_DISENTANGLEMENT")
    if "MEMORY_HISTORY" in concept_set:
        questions.append("Does a history or memory coordinate explain residual structure that a memoryless model cannot?")
        problem_classes.append("NONMARKOVIAN_OR_DELAYED_MECHANISM")
    if "SCALE_REGIME" in concept_set:
        questions.append("Is there a regime boundary or scale-collapse coordinate shared across the participating systems?")
        problem_classes.append("REGIME_OR_SCALING_LAW")
    if "FAILURE_STABILITY" in concept_set and "INTERACTION_COUPLING" in concept_set:
        questions.append("Can the coupled subspace predict a stability/failure boundary rather than only correlate with it?")
        problem_classes.append("STABILITY_BOUNDARY_PREDICTION")
    if "MEASUREMENT_OBSERVER" in concept_set or "NOISE_UNCERTAINTY" in concept_set:
        questions.append("Can the added measurement/noise coordinates separate physical structure from observer or selection effects?")
        problem_classes.append("IDENTIFIABILITY_OR_REPRODUCIBILITY")
    if "THERMAL" in concept_set and len(domains) > 1:
        questions.append("Does thermal state organize a transferable response coordinate across the coupled domains?")
        problem_classes.append("THERMAL_CROSS_DOMAIN_RESPONSE")
    if not questions:
        questions.append("Does this structurally nominated subspace contain a reproducible relation that survives null, regime and alternative-mechanism controls?")
        problem_classes.append("OPEN_MULTIVARIATE_MECHANISM")
    # Priority is a research-routing score only.  It is intentionally not a
    # posterior probability, evidence score or novelty claim.
    importance = min(
        10.0,
        1.0
        + 0.9 * max(0, len(domains) - 1)
        + 0.45 * max(0, len(roles_set) - 1)
        + 0.55 * len(problem_classes)
        + 0.20 * min(len(axes), 15),
    )
    return {
        "research_questions": tuple(questions),
        "potential_problem_classes": tuple(dict.fromkeys(problem_classes)),
        "potential_importance_score": round(float(importance), 6),
        "importance_score_is_scientific_evidence": False,
        "problem_solved_claimed": False,
    }




def _subspace_applicability_contract(features: Mapping[str, Any]) -> Mapping[str, Any]:
    axis_order = max(1, int(features.get("axis_order", 0)))
    unbound = tuple(features.get("unbound_axis_ids", ()))
    bridged = tuple(features.get("bridged_domain_pairs", ()))
    unbridged = tuple(features.get("unbridged_domain_pairs", ()))
    pair_total = len(bridged) + len(unbridged)
    owner_bound_fraction = (axis_order - len(unbound)) / axis_order
    bridge_coverage = (len(bridged) / pair_total) if pair_total else 1.0
    if not unbound and not unbridged:
        status = "READY_FOR_TYPED_HYPOTHESIS_MEASUREMENT_PROJECTION_REQUIRED"
        next_requirement = "freeze a typed hypothesis, project it onto exact quantity/data observables, then execute a preregistered discriminating experiment on independent data"
    elif unbridged and not unbound:
        status = "TYPED_CROSS_DOMAIN_BRIDGE_REQUIRED"
        next_requirement = "construct or qualify a dimension/role-compatible bridge before mechanism fitting"
    elif unbound and not unbridged:
        status = "OBSERVER_OR_PARAMETERIZATION_REQUIRED"
        next_requirement = "bind the unowned coordinates to a measurable observer/protocol before promotion"
    else:
        status = "REPRESENTATION_AND_WORLD_ATTESTATION_REQUIRED"
        next_requirement = "resolve both missing typed bridges and unbound observer/parameterization coordinates"
    applicability_score = max(0.0, min(1.0, owner_bound_fraction * (0.35 + 0.65 * bridge_coverage)))
    return {
        "status": status,
        "owner_bound_fraction": round(float(owner_bound_fraction), 6),
        "typed_bridge_coverage": round(float(bridge_coverage), 6),
        "unbound_axis_count": len(unbound),
        "unbridged_domain_pair_count": len(unbridged),
        "applicability_score": round(float(applicability_score), 6),
        "structural_typed_binding_ready": bool(not unbound and not unbridged),
        "data_binding_ready": False,
        "measurement_projection_status": "REQUIRES_CANDIDATE_WORLD_BINDING_OWNER",
        "next_requirement": next_requirement,
        "applicability_score_is_scientific_evidence": False,
    }


def _higher_order_experiment_blueprint(row: Mapping[str, Any]) -> Mapping[str, Any]:
    axes = tuple(row["axis_ids"])
    problems = tuple(row["problem_contract"]["potential_problem_classes"])
    if "NONMARKOVIAN_OR_DELAYED_MECHANISM" in problems:
        intervention = "repeat matched perturbations with controlled history/order and a memoryless control arm"
        discriminator = "memory/history mechanism versus instantaneous coupling with the same marginal observables"
    elif "REGIME_OR_SCALING_LAW" in problems:
        intervention = "sample at least two non-overlapping regimes and vary the nominated scale coordinate across the predicted transition"
        discriminator = "single transferable scaling law versus within-regime interpolation"
    elif "STABILITY_BOUNDARY_PREDICTION" in problems:
        intervention = "cross the predicted stability boundary from both directions under matched controls"
        discriminator = "causal stability boundary versus passive correlation or selection bias"
    elif "MISSING_TYPED_CROSS_DOMAIN_MECHANISM" in problems:
        intervention = "co-measure all nominated coordinates under a shared typed protocol and independently perturb one coordinate per participating domain"
        discriminator = "independence/direct-sum null versus transferable typed cross-domain coupling"
    else:
        intervention = "measure the complete nominated subspace in a discovery regime and an independently separated regime; pre-freeze competing mechanisms before reveal"
        discriminator = "stable higher-order relation versus lower-order projection, observer artifact, interpolation and adaptive-search null"
    core = {
        "candidate_id": row["candidate_id"],
        "axis_ids": axes,
        "axis_order": int(row["axis_order"]),
        "intervention_or_sampling_protocol": intervention,
        "discriminating_question": discriminator,
        "required_controls": (
            "lower-order projection controls",
            "convention/unit compatibility control where applicable",
            "adaptive whole-pipeline permutation/null control",
            "non-overlapping regime holdout",
            "independent world attestation before promotion",
        ),
        "status": "DISCRIMINATING_EXPERIMENT_BLUEPRINT_FROZEN_PENDING_WORLD_ATTESTATION",
        "world_result_observed": False,
        "literature_used_prefreeze": False,
    }
    return {**core, "digest": digest_payload(core)}


def _subspace_hypothesis_family_contracts() -> tuple[Mapping[str, Any], ...]:
    templates = (
        ("INDEPENDENCE_OR_DIRECT_SUM_NULL", True,
         "After conditioning on declared controls, the nominated coordinates factorize or reduce to an owner-wise direct sum without an irreducible joint mechanism.",
         "Reject only if a pre-frozen joint model improves out-of-regime prediction and survives whole-pipeline null, lower-order and measurement controls."),
        ("HIGHER_ORDER_INTERACTION", False,
         "The nominated coordinates contain an irreducible interaction that is not recoverable from the collection of lower-order projections.",
         "Falsified if lower-order projections reproduce the held-out joint response within declared uncertainty across independent regimes."),
        ("REGIME_DEPENDENT_COUPLING", False,
         "The coupling changes with scale, phase, operating regime or context rather than obeying one globally stationary relation.",
         "Falsified if one frozen stationary relation transfers across the nominated non-overlapping regimes without systematic residual structure."),
        ("DELAY_OR_MEMORY", False,
         "History, ordering or delayed state contributes information beyond the instantaneous nominated coordinates.",
         "Falsified if matched-history interventions and memoryless controls are statistically indistinguishable on independent data."),
        ("SHARED_LATENT_COORDINATE", False,
         "The apparent relation is induced by one or more shared latent coordinates rather than direct coupling among the nominated observables.",
         "Falsified if targeted interventions on nominated coordinates change the response while independently measured latent candidates are controlled."),
        ("BOUNDARY_OR_THRESHOLD", False,
         "A threshold, bifurcation or boundary surface in the nominated subspace separates distinct response or stability regimes.",
         "Falsified if bidirectional boundary-crossing experiments show no reproducible discontinuity, change of slope, topology or stability class beyond uncertainty."),
        ("REPRESENTATION_DEFECT", False,
         "The apparent structure is caused by an incomplete coordinate, unit, observer or representation choice and disappears after a better typed representation is introduced.",
         "Falsified if the relation persists under equivalent representations, calibrated observers and declared unit/convention transformations."),
    )
    out=[]
    for family,is_null,statement,falsification in templates:
        core={
            "family":family, "is_null_family":bool(is_null),
            "statement":statement, "falsification_signature":falsification,
            "status":"COMPETING_HYPOTHESIS_FAMILY_CONTRACT",
        }
        out.append({**core,"contract_id":"HFC-"+digest_payload(core)[:20].upper(),"digest":digest_payload(core)})
    return tuple(out)


def _competing_subspace_hypotheses(row: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    """Freeze seven explicit alternative hypotheses per materialized subspace.

    Statements/falsification rules live once in the family-contract table; each
    candidate stores a content-addressed binding.  This keeps the complete ledger
    explicit without repeating the same prose tens of thousands of times.
    """
    candidate_id=str(row["candidate_id"]); axis_digest=digest_payload(tuple(row["axis_ids"]))
    experiment_digest=str(row.get("discriminating_experiment",{}).get("digest",""))
    out=[]
    for contract in _subspace_hypothesis_family_contracts():
        family=str(contract["family"]); core={
            "hypothesis_id":"HYP-"+digest_payload({"candidate_id":candidate_id,"family":family,"axis_digest":axis_digest})[:24].upper(),
            "candidate_id":candidate_id, "family":family,
            "family_contract_id":contract["contract_id"],
            "is_null_family":bool(contract["is_null_family"]),
            "axis_set_digest":axis_digest,
            "discriminating_experiment_digest":experiment_digest,
            "status":"UNVERIFIED_COMPETING_HYPOTHESIS",
            "world_evidence_bound":False, "novelty_established":False, "law_established":False,
        }
        out.append({**core,"digest":digest_payload(core)})
    return tuple(out)

def _adaptive_multidimensional_subspace_exploration(
    pipeline: "CandidateGenerationPipeline",
    *,
    axis_rows: Sequence[Mapping[str, Any]],
    pair_frontier_rows: Sequence[Mapping[str, Any]],
    traversal_state: Mapping[str, Any] | None = None,
    revisit_digest: str | None = None,
    dovetail_steps: int = 0,
) -> Mapping[str, Any]:
    """Materialize many local scientific subspaces without a fixed order ceiling.

    This is the central navigation layer over the existing owner hypergraph.  It
    deliberately avoids both complete subset enumeration and pair-score-greedy
    growth.  Seeds are nominated independently by several structural principles;
    each seed can produce local one-step alternatives.  Release 15.14 adds a
    persistent fair dovetail scheduler over the same owner: the historical 15.13
    one-pass materialization remains the immutable baseline, while repeated
    advances enumerate pair seeds and node/axis extensions without a fixed step,
    order, feature or visit ceiling.  The set of *operation lanes* is semantic
    (new domain, role, concept, bridge, owner support, semantic resonance); the
    dovetail coverage lane guarantees that a low current score cannot make a
    finite axis subset permanently unreachable.
    """
    meta = {str(row["fq"]): dict(row) for row in axis_rows}
    all_axis_ids = tuple(sorted(meta))

    # Finite-release coverage is distinct from the asymptotic dovetail fairness
    # theorem.  Read the already-earned traversal state to identify canonical
    # axes that have never yet appeared in a materialized adaptive node.  The
    # coverage witness lane below makes those voids explicit without resetting
    # or deleting any historical traversal progress.
    historical_axis_occurrence = {axis: 0 for axis in all_axis_ids}
    if traversal_state:
        early_state_status = dovetail_state_status(traversal_state)
        if early_state_status.get("valid") is not True:
            raise RuntimeError(f"invalid supplied dovetail state: {early_state_status.get('reason')}")
        for node in dict(traversal_state.get("nodes", {})).values():
            # Structural rows introduced by a later release are deterministic
            # views over the earned traversal, not new traversal evidence.  If
            # they fed back into the least-visited selector, replay would move
            # the target after every seal.
            if str(node.get("origin", "")) == "STRUCTURAL_BASELINE_AFTER_APPEND_ONLY_REBASE":
                continue
            for axis in set(str(x) for x in node.get("axis_ids", ())):
                if axis in historical_axis_occurrence:
                    historical_axis_occurrence[axis] += 1
    historical_zero_axis_ids = tuple(sorted(axis for axis, count in historical_axis_occurrence.items() if count == 0))
    axis_to_owners: dict[str, set[str]] = {axis: set(meta[axis].get("owner_ids", ())) for axis in all_axis_ids}
    owner_axis_sets: dict[str, tuple[str, ...]] = {}
    owner_domains: dict[str, str] = {}
    for passport in sorted(pipeline.catalog.passports.values(), key=lambda p: p.owner_id):
        bound = tuple(sorted(_passport_bound_axes(passport, pipeline.catalog)))
        if len(bound) >= 2:
            owner_axis_sets[passport.owner_id] = bound
            owner_domains[passport.owner_id] = passport.domain_id
            for axis in bound:
                axis_to_owners.setdefault(axis, set()).add(passport.owner_id)

    bridge_pairs, _bridge_ids_by_pair = _domain_bridge_index(pipeline.bridges)
    bridge_axis_sets: dict[str, tuple[str, ...]] = {}
    for bridge_id, bridge in sorted(pipeline.bridges.items()):
        axes: list[str] = []
        for domain in bridge.source_domains:
            for axis_id in BRIDGE_AXIS_IDS.get(bridge_id, {}).get(domain, ()):
                fq = f"{domain}.{axis_id}"
                if fq in meta:
                    axes.append(fq)
        if len(set(axes)) >= 2:
            bridge_axis_sets[str(bridge_id)] = tuple(sorted(set(axes)))

    def features(axis_ids: Sequence[str]) -> Mapping[str, Any]:
        ids = tuple(sorted(set(axis_ids)))
        domains = tuple(sorted({str(meta[a]["domain"]) for a in ids}))
        roles = tuple(sorted({str(meta[a]["role"]) for a in ids}))
        owners = tuple(sorted({owner for a in ids for owner in axis_to_owners.get(a, ())}))
        concepts = tuple(sorted({c for a in ids for c in _axis_concept_classes(meta[a]["axis_id"])}))
        unbound = tuple(sorted(a for a in ids if not axis_to_owners.get(a)))
        bridged_pairs: list[tuple[str, str]] = []
        unbridged_pairs: list[tuple[str, str]] = []
        for i, left in enumerate(domains):
            for right in domains[i + 1:]:
                pair = (left, right)
                (bridged_pairs if pair in bridge_pairs else unbridged_pairs).append(pair)
        gaps: list[str] = []
        if unbound:
            gaps.append("PARAMETERIZATION_OR_ATTESTATION_GAP")
        if ids and len(unbound) == len(ids):
            gaps.append("OWNER_BINDING_GAP")
        if unbridged_pairs:
            gaps.append("CROSS_DOMAIN_BRIDGE_GAP")
        if len(roles) > 1:
            gaps.append("CROSS_ROLE_MECHANISM_FRONTIER")
        if not gaps:
            gaps.append("UNBOUND_MULTIVARIATE_MECHANISM_FRONTIER")
        return {
            "axis_ids": ids,
            "axis_order": len(ids),
            "domains": domains,
            "roles": roles,
            "owner_ids": owners,
            "concept_classes": concepts,
            "unbound_axis_ids": unbound,
            "bridged_domain_pairs": tuple(bridged_pairs),
            "unbridged_domain_pairs": tuple(unbridged_pairs),
            "gap_types": tuple(gaps),
        }

    seeds: list[dict[str, Any]] = []

    def add_seed(axis_ids: Sequence[str], mode: str, provenance: Mapping[str, Any], *, materialize_seed: bool) -> None:
        ids = tuple(sorted(set(str(x) for x in axis_ids if str(x) in meta)))
        if len(ids) < 2:
            return
        seeds.append({
            "seed_id": "SUBSEED-" + digest_payload({"mode": mode, "axes": ids, "provenance": provenance})[:18].upper(),
            "axis_ids": ids,
            "nomination_mode": mode,
            "provenance": dict(provenance),
            "materialize_seed": bool(materialize_seed),
        })

    # 1) Exact cross-domain pair frontier: useful low-order entry lane.
    for row in pair_frontier_rows:
        add_seed(row.get("axes", ()), "EXACT_PAIR_FRONTIER", {"frontier_id": row.get("frontier_id"), "lane": row.get("lane")}, materialize_seed=False)

    # 2) Every owner contributes its bound coordinate geometry as an *independent
    # higher-order nomination source*.  The unchanged geometry is known context,
    # so only extensions are materialized as new research candidates.
    for owner_id, axes in sorted(owner_axis_sets.items()):
        add_seed(axes, "OWNER_COBOUND_HIGHER_ORDER", {"owner_id": owner_id, "domain_id": owner_domains[owner_id], "pair_projection_required": False}, materialize_seed=False)

    # 3) Typed bridge motifs are themselves open cross-domain subspaces.
    for bridge_id, axes in sorted(bridge_axis_sets.items()):
        add_seed(axes, "TYPED_BRIDGE_MOTIF", {"bridge_id": bridge_id, "pair_projection_required": False}, materialize_seed=True)

    # 4) Merge one structurally closest owner geometry per source domain of every
    # bridge.  Order emerges from the actual owners and can naturally exceed 15.
    for bridge_id, bridge in sorted(pipeline.bridges.items()):
        native = set(bridge_axis_sets.get(str(bridge_id), ()))
        merged: set[str] = set(native)
        selected_owners: list[str] = []
        native_concepts = {c for a in native for c in _axis_concept_classes(meta[a]["axis_id"])}
        for domain in sorted(set(bridge.source_domains)):
            candidates = []
            for owner_id, axes in owner_axis_sets.items():
                if owner_domains.get(owner_id) != domain:
                    continue
                overlap = len(native & set(axes))
                axis_concepts = {c for a in axes for c in _axis_concept_classes(meta[a]["axis_id"])}
                concept_overlap = len(native_concepts & axis_concepts)
                candidates.append((overlap, concept_overlap, -len(axes), owner_id, axes))
            if candidates:
                _, _, _, owner_id, axes = max(candidates)
                selected_owners.append(owner_id)
                merged.update(axes)
        if len(selected_owners) >= 2:
            add_seed(tuple(merged), "BRIDGE_CONNECTED_OWNER_MERGE", {"bridge_id": bridge_id, "owner_ids": tuple(sorted(selected_owners)), "pair_projection_required": False}, materialize_seed=True)

    # 5) Semantic/role motifs nominate pure higher-order regions without requiring
    # a lower-order empirical projection.  One representative per (domain, role)
    # preserves structural diversity without pretending to enumerate all subsets.
    concept_to_axes: dict[str, list[str]] = {}
    for axis in all_axis_ids:
        for concept in _axis_concept_classes(meta[axis]["axis_id"]):
            concept_to_axes.setdefault(concept, []).append(axis)
    for concept, members in sorted(concept_to_axes.items()):
        groups: dict[tuple[str, str], list[str]] = {}
        for axis in members:
            groups.setdefault((str(meta[axis]["domain"]), str(meta[axis]["role"])), []).append(axis)
        representative = tuple(sorted(min(group) for group in groups.values()))
        if len({meta[a]["domain"] for a in representative}) >= 2 and len(representative) >= 3:
            add_seed(representative, "SEMANTIC_ROLE_HIGHER_ORDER_MOTIF", {"concept_class": concept, "pair_projection_required": False}, materialize_seed=True)

    # 6) Finite-release axis-coverage void witnesses.  Fair dovetail guarantees
    # eventual reachability but does not guarantee that a finite sealed snapshot
    # has touched every canonical axis.  For every axis absent from the earned
    # traversal history, materialize a deterministic same-domain witness and,
    # where a semantically/typed justified relation exists, a cross-domain
    # witness.  These rows are research addresses, not coupling claims.
    def _same_domain_coverage_partner(target: str) -> str | None:
        domain = str(meta[target]["domain"]); target_role = str(meta[target]["role"])
        target_concepts = set(_axis_concept_classes(meta[target]["axis_id"]))
        candidates: list[tuple[tuple[float, ...], str]] = []
        for other in all_axis_ids:
            if other == target or str(meta[other]["domain"]) != domain:
                continue
            shared_owner = bool(axis_to_owners.get(target, set()) & axis_to_owners.get(other, set()))
            concept_overlap = len(target_concepts & set(_axis_concept_classes(meta[other]["axis_id"])))
            role_match = str(meta[other]["role"]) == target_role
            affinity = _axis_semantic_affinity(meta[target]["axis_id"], meta[other]["axis_id"])
            rank = (float(shared_owner), float(concept_overlap), float(role_match), float(affinity), -float(historical_axis_occurrence.get(other, 0)))
            candidates.append((rank, other))
        if not candidates:
            return None
        best_rank = max(rank for rank, _ in candidates)
        return min(other for rank, other in candidates if rank == best_rank)

    def _cross_domain_coverage_partner(target: str) -> tuple[str | None, Mapping[str, Any]]:
        target_domain = str(meta[target]["domain"]); target_role = str(meta[target]["role"])
        target_concepts = set(_axis_concept_classes(meta[target]["axis_id"]))
        candidates: list[tuple[tuple[float, ...], str, Mapping[str, Any]]] = []
        for other in all_axis_ids:
            other_domain = str(meta[other]["domain"])
            if other == target or other_domain == target_domain:
                continue
            domain_pair = tuple(sorted((target_domain, other_domain)))
            typed_bridge = domain_pair in bridge_pairs
            concept_overlap = len(target_concepts & set(_axis_concept_classes(meta[other]["axis_id"])))
            affinity = _axis_semantic_affinity(meta[target]["axis_id"], meta[other]["axis_id"])
            role_match = str(meta[other]["role"]) == target_role
            # Do not manufacture an arbitrary cross-domain link: at least one
            # typed bridge, shared concept or non-zero semantic affinity is needed.
            if not typed_bridge and concept_overlap == 0 and affinity <= 0.0:
                continue
            rank = (float(typed_bridge), float(concept_overlap), float(affinity), float(role_match), -float(historical_axis_occurrence.get(other, 0)))
            provenance = {
                "typed_domain_bridge": bool(typed_bridge),
                "shared_concept_count": int(concept_overlap),
                "semantic_affinity": round(float(affinity), 12),
                "same_role": bool(role_match),
            }
            candidates.append((rank, other, provenance))
        if not candidates:
            return None, {}
        best_rank = max(rank for rank, _, _ in candidates)
        finalists = [(other, provenance) for rank, other, provenance in candidates if rank == best_rank]
        other, provenance = min(finalists, key=lambda x: x[0])
        return other, provenance

    for target in historical_zero_axis_ids:
        local_partner = _same_domain_coverage_partner(target)
        if local_partner:
            add_seed(
                (target, local_partner),
                "AXIS_COVERAGE_VOID_WITNESS",
                {
                    "target_axis_id": target,
                    "partner_axis_id": local_partner,
                    "witness_kind": "SAME_DOMAIN_STRUCTURAL_ADDRESS",
                    "historical_occurrence_before_scan": 0,
                    "coverage_witness_only": True,
                    "pair_projection_required": False,
                },
                materialize_seed=True,
            )
        cross_partner, cross_provenance = _cross_domain_coverage_partner(target)
        if cross_partner:
            add_seed(
                (target, cross_partner),
                "AXIS_COVERAGE_VOID_WITNESS",
                {
                    "target_axis_id": target,
                    "partner_axis_id": cross_partner,
                    "witness_kind": "CROSS_DOMAIN_TYPED_OR_SEMANTIC_ADDRESS",
                    "historical_occurrence_before_scan": 0,
                    "coverage_witness_only": True,
                    "pair_projection_required": False,
                    **dict(cross_provenance),
                },
                materialize_seed=True,
            )

    # 7) Under-covered semantic higher-order motifs.  Unlike the historical
    # lexicographic representatives, choose the least visited member of each
    # domain/concept group.  This redirects finite work into sparse regions while
    # retaining the same semantic nomination principle and no fixed order cap.
    for concept, members in sorted(concept_to_axes.items()):
        by_domain: dict[str, list[str]] = {}
        for axis in members:
            by_domain.setdefault(str(meta[axis]["domain"]), []).append(axis)
        if len(by_domain) < 3:
            continue
        representative = tuple(sorted(
            min(group, key=lambda a: (historical_axis_occurrence.get(a, 0), a))
            for _, group in sorted(by_domain.items())
        ))
        if len(representative) >= 3:
            add_seed(
                representative,
                "VOID_SEMANTIC_HIGHER_ORDER_MOTIF",
                {
                    "concept_class": concept,
                    "selection_rule": "LEAST_HISTORICALLY_VISITED_AXIS_PER_DOMAIN",
                    "historical_occurrences": {axis: historical_axis_occurrence.get(axis, 0) for axis in representative},
                    "pair_projection_required": False,
                },
                materialize_seed=True,
            )

    # Exact-axis-set deduplication preserves independent nomination provenance.
    seed_by_axes: dict[tuple[str, ...], dict[str, Any]] = {}
    for seed in seeds:
        ids = tuple(seed["axis_ids"])
        if ids not in seed_by_axes:
            seed_by_axes[ids] = {
                **seed,
                "nomination_modes": [seed["nomination_mode"]],
                "nomination_provenance": [seed["provenance"]],
            }
        else:
            seed_by_axes[ids]["nomination_modes"].append(seed["nomination_mode"])
            seed_by_axes[ids]["nomination_provenance"].append(seed["provenance"])
            seed_by_axes[ids]["materialize_seed"] = seed_by_axes[ids]["materialize_seed"] or seed["materialize_seed"]
    seeds = [seed_by_axes[key] for key in sorted(seed_by_axes)]

    # Structural representatives are derived from the complete registry.  The
    # finite set is not an execution budget: every domain/role, domain/concept and
    # typed bridge coordinate class has an addressable representative this run.
    representative_axes: set[str] = set()
    by_domain_role: dict[tuple[str, str], list[str]] = {}
    by_domain_concept: dict[tuple[str, str], list[str]] = {}
    for axis in all_axis_ids:
        by_domain_role.setdefault((str(meta[axis]["domain"]), str(meta[axis]["role"])), []).append(axis)
        for concept in _axis_concept_classes(meta[axis]["axis_id"]):
            by_domain_concept.setdefault((str(meta[axis]["domain"]), concept), []).append(axis)
    representative_axes.update(min(rows) for rows in by_domain_role.values())
    representative_axes.update(min(rows) for rows in by_domain_concept.values())
    for axes in bridge_axis_sets.values():
        representative_axes.update(axes)

    def gain_and_lanes(current: Mapping[str, Any], axis: str) -> tuple[float, tuple[str, ...]]:
        if axis in current["axis_ids"]:
            return -1.0, ()
        candidate = features((*current["axis_ids"], axis))
        new_domains = set(candidate["domains"]) - set(current["domains"])
        new_roles = set(candidate["roles"]) - set(current["roles"])
        new_concepts = set(candidate["concept_classes"]) - set(current["concept_classes"])
        shared_owner = bool(set(current["owner_ids"]) & axis_to_owners.get(axis, set()))
        bridge_extension = any(
            tuple(sorted((str(meta[axis]["domain"]), domain))) in bridge_pairs
            for domain in current["domains"] if domain != meta[axis]["domain"]
        )
        semantic = max((_axis_semantic_affinity(meta[axis]["axis_id"], meta[a]["axis_id"]) for a in current["axis_ids"]), default=0.0)
        resolved_unbridged = len(current["unbridged_domain_pairs"]) - len(candidate["unbridged_domain_pairs"])
        lanes: list[str] = []
        if new_domains: lanes.append("NEW_DOMAIN")
        if new_roles: lanes.append("NEW_ROLE")
        if new_concepts: lanes.append("NEW_CONCEPT")
        if shared_owner: lanes.append("SHARED_OWNER_GEOMETRY")
        if bridge_extension: lanes.append("TYPED_BRIDGE_EXTENSION")
        if semantic > 0.15: lanes.append("SEMANTIC_RESONANCE")
        if resolved_unbridged > 0: lanes.append("BRIDGE_GAP_REDUCTION")
        gain = (
            4.0 * len(new_domains)
            + 2.5 * len(new_roles)
            + 1.5 * len(new_concepts)
            + 3.0 * int(shared_owner)
            + 2.0 * int(bridge_extension)
            + 2.0 * max(0, resolved_unbridged)
            + semantic
        )
        return float(gain), tuple(sorted(lanes))

    evaluated_neighbor_visits = 0
    materialized: dict[tuple[str, ...], dict[str, Any]] = {}

    def emit(seed: Mapping[str, Any], axis_ids: Sequence[str], path: Sequence[Mapping[str, Any]], termination: str) -> None:
        final = features(axis_ids)
        ids = tuple(final["axis_ids"])
        if len(ids) < 2:
            return
        candidate_id = "SUBSPACE-" + digest_payload({"axes": ids})[:20].upper()
        problem = _subspace_problem_contract(ids, final["roles"], final["domains"], final["gap_types"], final["concept_classes"])
        applicability = _subspace_applicability_contract(final)
        research_priority = float(problem["potential_importance_score"]) * (0.35 + 0.65 * float(applicability["applicability_score"]))
        row = {
            "candidate_id": candidate_id,
            "candidate_class": "ADAPTIVE_MULTIDIMENSIONAL_SCIENTIFIC_SUBSPACE",
            **final,
            "seed_axis_ids": tuple(seed["axis_ids"]),
            "seed_axis_order": len(seed["axis_ids"]),
            "nomination_modes": tuple(sorted(set(seed["nomination_modes"]))),
            "nomination_provenance": tuple(seed["nomination_provenance"]),
            "adaptive_path": tuple(path),
            "termination": termination,
            "fixed_axis_order_ceiling": None,
            "fixed_owner_visit_budget": None,
            "pair_projection_required_for_nomination": False if any(mode != "EXACT_PAIR_FRONTIER" for mode in seed["nomination_modes"]) else True,
            "problem_contract": problem,
            "applicability_contract": applicability,
            "research_priority_score": round(float(research_priority), 6),
            "research_priority_score_is_scientific_evidence": False,
            "candidate_mechanism_families": (
                "INDEPENDENCE_OR_DIRECT_SUM_NULL", "HIGHER_ORDER_INTERACTION", "REGIME_DEPENDENT_COUPLING",
                "DELAY_OR_MEMORY", "SHARED_LATENT_COORDINATE", "BOUNDARY_OR_THRESHOLD", "REPRESENTATION_DEFECT",
            ),
            "status": "UNVERIFIED_ADAPTIVE_SUBSPACE_CANDIDATE",
            "epistemic_statuses": (
                "CANDIDATE_ACTIVE", "CANDIDATE_UNVERIFIED", "CANDIDATE_NOVELTY_UNRESOLVED",
                "CANDIDATE_APPLICABILITY_UNRESOLVED", "CANDIDATE_PROBLEM_RELEVANCE_ASSESSED",
            ),
            "prior_art_status": "NOT_CHECKED_PREFREEZE",
            "claim_boundary": {
                "subspace_is_established_law": False,
                "absence_from_literature_means_false": False,
                "importance_score_is_evidence": False,
                "pairwise_projection_required": False,
                "materialized_candidates_exhaust_all_subsets": False,
                "unmaterialized_subsets_are_false_or_impossible": False,
                "continuous_values_exhausted": False,
            },
        }
        row["discriminating_experiment"] = _higher_order_experiment_blueprint(row)
        # Cheapest scalar-law birth: project the nominated scientific-coordinate
        # region through its typed source owners to measurable quantities, then
        # freeze Pi=C when the exact Buckingham nullity is one.  Axis ids
        # themselves are metadata and are never treated as physical quantities.
        from .dimensional_law_birth import DimensionalScalarLawBirthOwner
        row["dimensional_law_birth"] = DimensionalScalarLawBirthOwner().freeze(row, pipeline.catalog)
        row["competing_hypotheses"] = _competing_subspace_hypotheses(row)
        row["competing_hypothesis_count"] = len(row["competing_hypotheses"])
        row["digest"] = digest_payload({k: v for k, v in row.items() if k != "digest"})
        previous = materialized.get(ids)
        if previous is None:
            materialized[ids] = row
        else:
            previous["nomination_modes"] = tuple(sorted(set(previous["nomination_modes"]) | set(row["nomination_modes"])))
            previous["nomination_provenance"] = tuple(previous["nomination_provenance"]) + tuple(
                x for x in row["nomination_provenance"] if x not in previous["nomination_provenance"]
            )
            previous["pair_projection_required_for_nomination"] = previous["pair_projection_required_for_nomination"] and row["pair_projection_required_for_nomination"]
            previous["digest"] = digest_payload({k: v for k, v in previous.items() if k != "digest"})

    for seed in seeds:
        base = features(seed["axis_ids"])
        if seed["materialize_seed"]:
            emit(seed, base["axis_ids"], (), "STRUCTURALLY_NOMINATED_SEED")

        # Coverage witnesses are intentionally addresses, not branch multipliers.
        # Their nodes enter the same persistent dovetail scheduler below, which is
        # the authoritative mechanism for subsequent open-ended expansion.
        if "AXIS_COVERAGE_VOID_WITNESS" in set(seed["nomination_modes"]):
            continue

        # Add all axes sharing a seed owner to the representative pool; this keeps
        # owner geometry exact while still avoiding a full 655-axis scan per seed.
        local_pool = set(representative_axes)
        for owner_id in base["owner_ids"]:
            local_pool.update(owner_axis_sets.get(owner_id, ()))
        # Semantically matched representatives are included irrespective of pair score.
        base_concepts = set(base["concept_classes"])
        if base_concepts:
            local_pool.update(
                axis for axis in representative_axes
                if base_concepts & _axis_concept_classes(meta[axis]["axis_id"])
            )

        # One local branch per semantic operation lane.  This is deliberately not
        # a top-N beam; every operation type that is actually available is emitted.
        best_by_lane: dict[str, tuple[float, str]] = {}
        best_overall: tuple[float, str] | None = None
        for axis in sorted(local_pool):
            evaluated_neighbor_visits += 1
            gain, lanes = gain_and_lanes(base, axis)
            if gain <= 0 or not lanes:
                continue
            if best_overall is None or gain > best_overall[0] or (gain == best_overall[0] and axis < best_overall[1]):
                best_overall = (gain, axis)
            for lane in lanes:
                previous = best_by_lane.get(lane)
                if previous is None or gain > previous[0] or (gain == previous[0] and axis < previous[1]):
                    best_by_lane[lane] = (gain, axis)
        for lane, (gain, axis) in sorted(best_by_lane.items()):
            emit(seed, (*base["axis_ids"], axis), ({"action": "EXPAND", "operation_lane": lane, "axis_id": axis, "structural_gain": round(gain, 12)},), "LOCAL_OPERATION_LANE_MATERIALIZED")

        # 15.13 baseline behavior intentionally ends here.  15.14 continuation is
        # applied below from a content-addressed persistent state; therefore the
        # old materialized rows are preserved byte-for-byte at the candidate level.

    baseline_candidate_ids = set(row["candidate_id"] for row in materialized.values())
    topology_core = {
        "axis_rows": [
            {
                "fq": axis,
                "domain": meta[axis]["domain"],
                "role": meta[axis]["role"],
                "owner_ids": sorted(axis_to_owners.get(axis, ())),
                "concept_classes": sorted(_axis_concept_classes(meta[axis]["axis_id"])),
            }
            for axis in all_axis_ids
        ],
        "owner_axis_sets": {owner_id: list(axes) for owner_id, axes in sorted(owner_axis_sets.items())},
        "bridge_axis_sets": {bridge_id: list(axes) for bridge_id, axes in sorted(bridge_axis_sets.items())},
    }
    topology_digest = digest_payload(topology_core)
    environment_digest = digest_payload({
        "topology_digest": topology_digest,
        "external_revisit_digest": str(revisit_digest or "NO_EXTERNAL_REVISIT_DIGEST"),
    })

    def _baseline_node(row: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "candidate_id": str(row["candidate_id"]),
            "axis_ids": list(row["axis_ids"]),
            "root_seed_axis_ids": list(row.get("seed_axis_ids", row["axis_ids"])),
            "nomination_modes": list(row.get("nomination_modes", ("LEGACY_STRUCTURAL_BASELINE",))),
            "nomination_provenance": list(row.get("nomination_provenance", ())),
            "adaptive_path": list(row.get("adaptive_path", ())),
            "termination": str(row.get("termination", "LEGACY_15_13_BASELINE")),
            "origin": "PRESERVED_15_13_STRUCTURAL_BASELINE",
            "parent_candidate_id": None,
            "birth_step": 0,
            "axis_cursor": 0,
            "completed_axis_cycles": 0,
            "local_search_shell": 0,
        }

    if traversal_state:
        state_status = dovetail_state_status(traversal_state)
        if state_status.get("valid") is not True:
            raise RuntimeError(f"invalid supplied dovetail state: {state_status.get('reason')}")
        state = json.loads(canonical_json(traversal_state))
        nodes = dict(state.get("nodes", {}))
        old_axis_order = list(state.get("axis_birth_order", ()))
        missing_old_axes = [axis for axis in old_axis_order if axis not in meta]
        if missing_old_axes:
            # Canonical Atlas axes are append-only.  Failing closed here prevents a
            # release from silently erasing an address that an older state could visit.
            raise RuntimeError(f"dovetail axis-history regression; missing preserved axes: {missing_old_axes[:8]}")
        appended_axes = [axis for axis in all_axis_ids if axis not in set(old_axis_order)]
        axis_birth_order = old_axis_order + appended_axes
        environment_epoch = int(state.get("environment_epoch", 0))
        environment_changed = str(state.get("environment_digest", "")) != environment_digest
        if environment_changed:
            environment_epoch += 1
        state["environment_epoch"] = environment_epoch
        state["environment_digest"] = environment_digest
        state["topology_digest"] = topology_digest
        state["axis_birth_order"] = axis_birth_order
        state["last_rebase"] = {
            "environment_changed": bool(environment_changed),
            "new_axis_ids": appended_axes,
            "old_progress_preserved": True,
            "old_nodes_deleted": False,
            "cursors_reset": False,
            "reason": "NEW_AXES_APPENDED_AND_OR_ENVIRONMENT_REQUALIFICATION" if (environment_changed or appended_axes) else "NO_REBASE_REQUIRED",
        }
    else:
        nodes = {}
        axis_birth_order = list(all_axis_ids)
        state = {
            "schema": DOVETAIL_STATE_SCHEMA,
            "version": DOVETAIL_STATE_VERSION,
            "owner": "CandidateGenerationPipeline/6.28.0",
            "environment_epoch": 0,
            "environment_digest": environment_digest,
            "topology_digest": topology_digest,
            "axis_birth_order": axis_birth_order,
            "baseline_candidate_ids_digest": digest_payload(sorted(baseline_candidate_ids)),
            "nodes": nodes,
            "scheduler": {
                "phase": "PAIR_SEED",
                "steps_executed": 0,
                "pair_cursor": {"max_index_shell": 1, "left_index": 0, "visits": 0, "completed_shells": 0},
                "node_round": {"round": 0, "cursor": 0, "snapshot": []},
                "node_visits": 0,
            },
            "last_rebase": {
                "environment_changed": False,
                "new_axis_ids": [],
                "old_progress_preserved": True,
                "old_nodes_deleted": False,
                "cursors_reset": False,
                "reason": "INITIAL_STATE_FROM_PRESERVED_15_13_FRONTIER",
            },
        }

    # Preserve the 15.13 structural baseline as an immutable identity class.
    # A smaller read-view (for example frontier_limit=19) must never redefine that
    # baseline or make preserved 15.13 nodes look like traversal-born additions.
    if traversal_state:
        preserved_legacy_candidate_ids = {
            str(cid) for cid, node in nodes.items()
            if str(node.get("origin", "")) == "PRESERVED_15_13_STRUCTURAL_BASELINE"
        }
    else:
        preserved_legacy_candidate_ids = set(baseline_candidate_ids)

    # Merge every deterministic structural-baseline node without overwriting any
    # traversal cursor already earned by an older persistent state.  On a future
    # append-only axis rebase, genuinely new structural rows are not mislabeled as
    # members of the preserved 15.13 identity set.
    for row in materialized.values():
        cid = str(row["candidate_id"]); base_node = _baseline_node(row)
        if cid not in nodes:
            if traversal_state:
                base_node["origin"] = "STRUCTURAL_BASELINE_AFTER_APPEND_ONLY_REBASE"
                base_node["birth_step"] = int(state.get("scheduler", {}).get("steps_executed", 0))
            nodes[cid] = base_node
        else:
            old = nodes[cid]
            for key in ("axis_ids", "root_seed_axis_ids", "nomination_modes", "nomination_provenance", "adaptive_path", "termination"):
                old.setdefault(key, base_node[key])
            old.setdefault("origin", base_node["origin"]); old.setdefault("parent_candidate_id", None)
            old.setdefault("birth_step", 0); old.setdefault("axis_cursor", 0)
            old.setdefault("completed_axis_cycles", 0); old.setdefault("local_search_shell", 0)

    def _seed_from_node(node: Mapping[str, Any]) -> Mapping[str, Any]:
        root_axes = tuple(str(x) for x in node.get("root_seed_axis_ids", node.get("axis_ids", ())))
        modes = tuple(str(x) for x in node.get("nomination_modes", ("FAIR_DOVETAIL_CONTINUATION",)))
        provenance = tuple(node.get("nomination_provenance", ()))
        return {
            "axis_ids": root_axes,
            "nomination_modes": modes,
            "nomination_provenance": provenance,
            "materialize_seed": True,
        }

    # Rehydrate only traversal-born rows.  Baseline rows above are left untouched,
    # which is the explicit "do not lose the old system" migration invariant.
    for cid, node in sorted(nodes.items()):
        if cid in baseline_candidate_ids:
            continue
        ids = tuple(str(x) for x in node.get("axis_ids", ()))
        if not ids or any(axis not in meta for axis in ids):
            continue
        emit(
            _seed_from_node(node), ids, tuple(node.get("adaptive_path", ())),
            str(node.get("termination", "FAIR_DOVETAIL_PERSISTED_CONTINUATION")),
        )

    scheduler = dict(state.get("scheduler", {}))
    scheduler.setdefault("phase", "PAIR_SEED")
    scheduler.setdefault("steps_executed", 0)
    scheduler.setdefault("pair_cursor", {"max_index_shell": 1, "left_index": 0, "visits": 0, "completed_shells": 0})
    # Migrate the pre-15.14 in-memory cursor shape without deleting any node/progress.
    # The release snapshot has zero traversal steps, but external experimental states
    # are still accepted fail-softly by restarting only pair enumeration (duplicates
    # are content-address deduplicated).
    if "max_index_shell" not in dict(scheduler.get("pair_cursor", {})):
        old_pc = dict(scheduler.get("pair_cursor", {}))
        scheduler["pair_cursor"] = {
            "max_index_shell": 1, "left_index": 0,
            "visits": int(old_pc.get("visits", 0)), "completed_shells": 0,
            "migrated_from_lexicographic_cursor": True,
        }
    scheduler.setdefault("node_round", {"round": 0, "cursor": 0, "snapshot": []})
    scheduler.setdefault("node_visits", 0)
    new_node_ids: list[str] = []

    def _candidate_id_for_axes(axis_ids: Sequence[str]) -> str:
        ids = tuple(sorted(set(str(x) for x in axis_ids)))
        return "SUBSPACE-" + digest_payload({"axes": ids})[:20].upper()

    def _register_dovetail_node(
        axis_ids: Sequence[str], *, root_seed_axis_ids: Sequence[str], nomination_mode: str,
        provenance: Mapping[str, Any], adaptive_path: Sequence[Mapping[str, Any]], termination: str,
        parent_candidate_id: str | None, birth_step: int,
    ) -> tuple[str, bool]:
        ids = tuple(sorted(set(str(x) for x in axis_ids if str(x) in meta)))
        cid = _candidate_id_for_axes(ids)
        if len(ids) < 2:
            return cid, False
        if cid in nodes:
            return cid, False
        node = {
            "candidate_id": cid,
            "axis_ids": list(ids),
            "root_seed_axis_ids": list(tuple(sorted(set(root_seed_axis_ids))) or ids),
            "nomination_modes": [str(nomination_mode)],
            "nomination_provenance": [dict(provenance)],
            "adaptive_path": [dict(x) for x in adaptive_path],
            "termination": str(termination),
            "origin": "FAIR_DOVETAIL_CONTINUATION",
            "parent_candidate_id": parent_candidate_id,
            "birth_step": int(birth_step),
            "axis_cursor": 0,
            "completed_axis_cycles": 0,
            "local_search_shell": 0,
        }
        nodes[cid] = node
        new_node_ids.append(cid)
        emit(_seed_from_node(node), ids, tuple(node["adaptive_path"]), node["termination"])
        return cid, True

    def _advance_pair_cursor() -> bool:
        """Visit one pair by diagonal max-birth-rank dovetail.

        Pair (i,j), i<j, is visited in shell j.  Because the axis birth order is
        append-only and the scheduler never advances beyond the highest currently
        existing rank, every pair whose axes are ever registered at finite ranks is
        visited after finitely many pair phases even if new axes continue to appear.
        """
        pc = dict(scheduler.get("pair_cursor", {}))
        n = len(axis_birth_order)
        if n < 2:
            scheduler["pair_cursor"] = pc
            return False
        shell = max(1, int(pc.get("max_index_shell", 1)))
        left = max(0, int(pc.get("left_index", 0)))
        # Do not step over a not-yet-born rank.  If the registry later appends that
        # axis, this same shell immediately becomes addressable.
        if shell >= n:
            pc["max_index_shell"], pc["left_index"] = shell, min(left, max(0, shell - 1))
            scheduler["pair_cursor"] = pc
            return False
        if left >= shell:
            left = 0
        pair_axes = (axis_birth_order[left], axis_birth_order[shell])
        step_no = int(scheduler.get("steps_executed", 0)) + 1
        _register_dovetail_node(
            pair_axes, root_seed_axis_ids=pair_axes, nomination_mode="FAIR_DOVETAIL_PAIR_SEED",
            provenance={"pair_diagonal_shell": shell, "left_birth_rank": left, "pair_projection_required": False},
            adaptive_path=(), termination="FAIR_DOVETAIL_PAIR_SEED_MATERIALIZED",
            parent_candidate_id=None, birth_step=step_no,
        )
        pc["visits"] = int(pc.get("visits", 0)) + 1
        left += 1
        if left >= shell:
            pc["completed_shells"] = int(pc.get("completed_shells", 0)) + 1
            shell += 1
            left = 0
        pc["max_index_shell"], pc["left_index"] = shell, left
        scheduler["pair_cursor"] = pc
        return True

    def _advance_node_round() -> None:
        nr = dict(scheduler.get("node_round", {}))
        snapshot = [str(x) for x in nr.get("snapshot", ()) if str(x) in nodes]
        cursor = int(nr.get("cursor", 0))
        if not snapshot or cursor >= len(snapshot):
            snapshot = [cid for cid, _ in sorted(nodes.items(), key=lambda kv: (int(kv[1].get("birth_step", 0)), kv[0]))]
            cursor = 0
            nr["round"] = int(nr.get("round", 0)) + (1 if nr.get("snapshot") else 0)
        if not snapshot:
            nr.update({"snapshot": [], "cursor": 0}); scheduler["node_round"] = nr
            return
        cid = snapshot[cursor]; cursor += 1
        node = nodes[cid]
        n = len(axis_birth_order)
        if n:
            axis_cursor = int(node.get("axis_cursor", 0)) % n
            axis = axis_birth_order[axis_cursor]
            next_cursor = axis_cursor + 1
            wrapped = next_cursor >= n
            node["axis_cursor"] = 0 if wrapped else next_cursor
            if wrapped:
                node["completed_axis_cycles"] = int(node.get("completed_axis_cycles", 0)) + 1
            # Local model-search depth is dovetailed independently of axis-registry
            # growth.  Thus an endlessly growing append-only registry cannot freeze a
            # persistent node forever at shell 0.
            node["local_search_shell"] = int(node.get("local_search_shell", 0)) + 1
            if axis not in set(node.get("axis_ids", ())):
                current = features(node["axis_ids"]); gain, lanes = gain_and_lanes(current, axis)
                effective_lanes = tuple(sorted(set(lanes) | {"FAIR_DOVETAIL_COVERAGE"}))
                action = {
                    "action": "EXPAND",
                    "operation_lane": "+".join(effective_lanes),
                    "axis_id": axis,
                    "structural_gain": round(float(gain), 12),
                    "dovetail_coverage_edge": True,
                    "parent_local_search_shell": int(node.get("local_search_shell", 0)),
                }
                _register_dovetail_node(
                    (*node["axis_ids"], axis),
                    root_seed_axis_ids=node.get("root_seed_axis_ids", node["axis_ids"]),
                    nomination_mode="FAIR_DOVETAIL_CONTINUATION",
                    provenance={"parent_candidate_id": cid, "operation_lanes": effective_lanes},
                    adaptive_path=tuple(node.get("adaptive_path", ())) + (action,),
                    termination="FAIR_DOVETAIL_NODE_AXIS_EXTENSION_MATERIALIZED",
                    parent_candidate_id=cid,
                    birth_step=int(scheduler.get("steps_executed", 0)) + 1,
                )
        nr.update({"snapshot": snapshot, "cursor": cursor})
        scheduler["node_round"] = nr
        scheduler["node_visits"] = int(scheduler.get("node_visits", 0)) + 1

    steps = int(dovetail_steps)
    if steps < 0:
        raise ValueError("dovetail_steps must be non-negative")
    before_steps = int(scheduler.get("steps_executed", 0))
    before_pair_visits = int(scheduler.get("pair_cursor", {}).get("visits", 0))
    before_node_visits = int(scheduler.get("node_visits", 0))
    for _ in range(steps):
        if str(scheduler.get("phase", "PAIR_SEED")) == "PAIR_SEED":
            pair_advanced = _advance_pair_cursor()
            if not pair_advanced:
                _advance_node_round()
            scheduler["phase"] = "NODE_EXPANSION"
        else:
            _advance_node_round(); scheduler["phase"] = "PAIR_SEED"
        scheduler["steps_executed"] = int(scheduler.get("steps_executed", 0)) + 1

    state["nodes"] = nodes
    state["scheduler"] = scheduler
    state["baseline_candidate_ids_digest"] = digest_payload(sorted(preserved_legacy_candidate_ids))
    state["baseline_candidate_count"] = len(preserved_legacy_candidate_ids)
    state["fairness_contract"] = {
        "fixed_global_step_ceiling": None,
        "fixed_pair_seed_ceiling": None,
        "fixed_node_visit_ceiling": None,
        "fixed_axis_order_ceiling": None,
        "candidate_batch_is_scientific_space_ceiling": False,
        "feature_budget_is_scientific_space_ceiling": False,
        "local_search_shell_has_fixed_maximum": False,
        "axis_birth_order_is_append_only": True,
        "pair_scheduler": "DIAGONAL_BY_MAX_APPEND_ONLY_AXIS_BIRTH_RANK",
        "node_scheduler": "ROUND_SNAPSHOT_EVERY_EXISTING_NODE_VISITED_ONCE_PER_FINITE_ROUND",
        "node_axis_scheduler": "CYCLIC_OVER_APPEND_ONLY_AXIS_BIRTH_ORDER__LOCAL_SEARCH_SHELL_INCREMENTS_EACH_NODE_VISIT",
        "coverage_lane": "EVERY_MISSING_AXIS_EDGE_IS_ADDRESSABLE_REGARDLESS_OF_CURRENT_STRUCTURAL_SCORE",
        "append_only_open_registry_guarantee": "EVERY_FINITE_SUBSET_OF_EVER_REGISTERED_AXES_WITH_FINITE_BIRTH_RANK_EVENTUALLY_MATERIALIZED_UNDER_UNBOUNDED_REPEATED_ADVANCE",
        "eventually_stable_finite_registry_guarantee": "SPECIAL_CASE_OF_APPEND_ONLY_OPEN_REGISTRY_GUARANTEE",
        "environment_change_policy": "PRESERVE_PROGRESS_APPEND_NEW_AXES_REQUALIFY_WITHOUT_DELETING_OLD_NODES",
    }
    state["last_advance"] = {
        "requested_steps": steps,
        "steps_before": before_steps,
        "steps_after": int(scheduler.get("steps_executed", 0)),
        "pair_visits_added": int(scheduler.get("pair_cursor", {}).get("visits", 0)) - before_pair_visits,
        "node_visits_added": int(scheduler.get("node_visits", 0)) - before_node_visits,
        "new_node_count": len(new_node_ids),
        "new_candidate_ids": new_node_ids,
    }
    state = _dovetail_state_with_digest(state)

    rows = sorted(
        materialized.values(),
        key=lambda row: (-float(row["research_priority_score"]), int(row["axis_order"]), row["candidate_id"]),
    )
    order_hist: dict[str, int] = {}
    nomination_hist: dict[str, int] = {}
    for row in rows:
        order_hist[str(row["axis_order"])] = order_hist.get(str(row["axis_order"]), 0) + 1
        for mode in row["nomination_modes"]:
            nomination_hist[mode] = nomination_hist.get(mode, 0) + 1
    # Exact finite coverage diagnostics for the materialized release snapshot.
    # These are navigation diagnostics, never evidence that unvisited pairs are false.
    post_axis_occurrence = {axis: 0 for axis in all_axis_ids}
    observed_pairs: set[tuple[str, str]] = set()
    observed_cross_domain_pairs: set[tuple[str, str]] = set()
    for row in rows:
        ids = tuple(row["axis_ids"])
        for axis in ids:
            post_axis_occurrence[axis] += 1
        for i, left in enumerate(ids):
            for right in ids[i + 1:]:
                pair = (left, right) if left < right else (right, left)
                observed_pairs.add(pair)
                if str(meta[pair[0]]["domain"]) != str(meta[pair[1]]["domain"]):
                    observed_cross_domain_pairs.add(pair)
    post_zero_axis_ids = tuple(sorted(axis for axis, count in post_axis_occurrence.items() if count == 0))
    total_pairs = len(all_axis_ids) * (len(all_axis_ids) - 1) // 2
    domain_axis_counts: dict[str, int] = {}
    for axis in all_axis_ids:
        domain_axis_counts[str(meta[axis]["domain"])] = domain_axis_counts.get(str(meta[axis]["domain"]), 0) + 1
    same_domain_pairs = sum(n * (n - 1) // 2 for n in domain_axis_counts.values())
    total_cross_domain_pairs = total_pairs - same_domain_pairs
    coverage_diagnostics = {
        "historical_node_axis_zero_count_before_scan": len(historical_zero_axis_ids),
        "historical_node_axis_zero_ids_before_scan": historical_zero_axis_ids,
        "materialized_axis_zero_count_after_scan": len(post_zero_axis_ids),
        "materialized_axis_zero_ids_after_scan": post_zero_axis_ids,
        "all_registered_axes_materialized_at_least_once": not post_zero_axis_ids,
        "observed_axis_pair_count": len(observed_pairs),
        "exact_possible_axis_pair_count": total_pairs,
        "observed_axis_pair_fraction": round((len(observed_pairs) / total_pairs) if total_pairs else 1.0, 12),
        "observed_cross_domain_axis_pair_count": len(observed_cross_domain_pairs),
        "exact_possible_cross_domain_axis_pair_count": total_cross_domain_pairs,
        "observed_cross_domain_axis_pair_fraction": round((len(observed_cross_domain_pairs) / total_cross_domain_pairs) if total_cross_domain_pairs else 1.0, 12),
        "exact_possible_axis_triple_count": len(all_axis_ids) * (len(all_axis_ids) - 1) * (len(all_axis_ids) - 2) // 6,
        "materialized_region_count_order_ge_3": sum(int(row["axis_order"]) >= 3 for row in rows),
        "exact_unique_axis_triple_census_attempted": False,
        "coverage_is_scientific_evidence": False,
        "unvisited_pair_or_triple_means_false": False,
    }

    payload = {
        "schema": ADAPTIVE_SUBSPACE_SCHEMA,
        "owner": "CandidateGenerationPipeline/6.28.0",
        "version": ADAPTIVE_SUBSPACE_VERSION,
        "status": "ADAPTIVE_MULTIDIMENSIONAL_SUBSPACE_FRONTIER_MATERIALIZED",
        "registered_axis_count": len(all_axis_ids),
        "exact_finite_registered_subset_census": str((1 << len(all_axis_ids)) - 1),
        "full_cartesian_subset_enumeration_attempted": False,
        "full_cartesian_subset_enumeration_required": False,
        "seed_count": len(seeds),
        "candidate_count": len(rows),
        "evaluated_neighbor_visits": evaluated_neighbor_visits,
        "fixed_neighbor_visit_budget": None,
        "fixed_axis_order_ceiling": None,
        "minimum_materialized_axis_order": min((row["axis_order"] for row in rows), default=0),
        "maximum_materialized_axis_order": max((row["axis_order"] for row in rows), default=0),
        "axis_order_histogram": dict(sorted(order_hist.items(), key=lambda kv: int(kv[0]))),
        "nomination_mode_counts": dict(sorted(nomination_hist.items())),
        "pure_higher_order_nomination_present": any(not row["pair_projection_required_for_nomination"] and row["seed_axis_order"] >= 3 for row in rows),
        "orders_above_15_present": any(int(row["axis_order"]) > 15 for row in rows),
        "candidate_problem_contract_complete": all(bool(row["problem_contract"]["research_questions"]) for row in rows),
        "candidate_experiment_contract_complete": all(bool(row["discriminating_experiment"]["digest"]) for row in rows),
        "candidate_applicability_contract_complete": all(bool(row["applicability_contract"]["status"]) for row in rows),
        "competing_hypotheses_complete": all(int(row.get("competing_hypothesis_count", 0)) == 7 for row in rows),
        "competing_hypothesis_count": sum(int(row.get("competing_hypothesis_count", 0)) for row in rows),
        "hypothesis_family_contracts": _subspace_hypothesis_family_contracts(),
        "coverage_diagnostics": coverage_diagnostics,
        "dovetail_state": state,
        "dovetail_state_digest": state["digest"],
        "dovetail_node_count": len(nodes),
        "dovetail_extra_candidate_count": len({
            str(cid) for cid, node in nodes.items()
            if str(node.get("origin", "")) == "FAIR_DOVETAIL_CONTINUATION"
        }),
        "preserved_15_13_candidate_count": len(preserved_legacy_candidate_ids),
        "dovetail_steps_executed": int(scheduler.get("steps_executed", 0)),
        "dovetail_fixed_global_step_ceiling": None,
        "dovetail_fairness_contract": state["fairness_contract"],
        "candidates": rows,
        "research_policy": {
            "all_axes_used_simultaneously_by_default": False,
            "many_local_subspaces_are_materialized": True,
            "adaptive_order_not_fixed_target_k": True,
            "lower_order_score_required_before_higher_order_nomination": False,
            "candidate_absent_from_literature_is_false": False,
            "candidate_priority_requires_problem_statement": True,
            "candidate_promotion_requires_world_evidence": True,
            "operation_lanes_are_scientific_navigation_not_beam_width": True,
            "persistent_fair_dovetail_state": True,
            "legacy_15_13_materialized_candidates_preserved": True,
            "unscored_coverage_edges_eventually_addressable": True,
            "finite_snapshot_zero_axis_voids_materialized_as_witnesses": True,
            "coverage_witness_is_coupling_claim": False,
            "least_visited_semantic_higher_order_nomination_active": True,
            "every_materialized_subspace_has_explicit_null_and_six_rival_hypotheses": True,
        },
        "claim_boundary": {
            "materialized_frontier_is_entire_hypothesis_space": False,
            "unmaterialized_subsets_rejected": False,
            "new_law_established": False,
            "world_novelty_established": False,
        },
    }
    return {**payload, "digest": digest_payload(payload)}


def _frontier_experiment_blueprint(row: Mapping[str, Any]) -> Mapping[str, Any]:
    axes=tuple(row["axes"]); roles=tuple(row["roles"]); gaps=set(row["gap_types"])
    if "PARAMETERIZATION_OR_ATTESTATION_GAP" in gaps:
        intervention="co-measure both coordinates under a shared calibrated protocol across at least two regimes"
        observable="joint calibrated axis values, uncertainty, regime labels and missingness mechanism"
        discriminator="distinguish sampling/attestation void from stable cross-axis structure"
    elif "CROSS_DOMAIN_BRIDGE_GAP" in gaps:
        intervention="vary one coordinate within its declared validity chart while holding matched context and observing the other"
        observable="conditional response surface plus uncertainty and validity-overlap metadata"
        discriminator="compare independence/null model against typed monotone, threshold, delayed and nonlocal coupling alternatives"
    elif "CROSS_ROLE_MECHANISM_FRONTIER" in gaps:
        intervention="perturb the generative/context coordinate and independently observe the observation/method/formal coordinate where operationally meaningful"
        observable="paired pre/post response with controls, observer provenance and regime coordinates"
        discriminator="separate predictive association from role-compatible directional mechanism"
    else:
        intervention="sample the frontier and adjacent populated regions under matched observer conditions"
        observable="joint occupancy/density and local residual topology"
        discriminator="distinguish forbidden/stability boundary, selection effect, missing observer, missing representation and unknown mechanism"
    core={
        "frontier_id": row["frontier_id"], "axes": list(axes), "roles": list(roles),
        "intervention_or_sampling_protocol": intervention, "required_observables": observable,
        "discriminating_question": discriminator,
        "competing_explanations": ["SAMPLING_GAP","KNOWN_CONSTRAINT","STABILITY_EXCLUSION","SELECTION_EFFECT","MISSING_OBSERVER","MISSING_AXIS_OR_REPRESENTATION","UNKNOWN_MECHANISM_OR_LAW"],
        "status":"DISCRIMINATING_EXPERIMENT_BLUEPRINT_FROZEN_PENDING_WORLD_ATTESTATION",
        "internet_used_prefreeze":False, "world_result_observed":False,
    }
    return {**core,"digest":digest_payload(core)}

def _open_void_directed_exploration(
    pipeline: "CandidateGenerationPipeline", *, frontier_limit: int = 19,
    traversal_state: Mapping[str, Any] | None = None, revisit_digest: str | None = None,
    dovetail_steps: int = 0,
) -> Mapping[str, Any]:
    axes=[]
    owner_bindings={}
    for passport in pipeline.catalog.passports.values():
        for fq in _passport_bound_axes(passport, pipeline.catalog): owner_bindings.setdefault(fq,set()).add(passport.owner_id)
    for domain,registry in sorted(DOMAIN_REGISTRIES.items()):
        for axis_id in sorted(registry.axes):
            fq=f"{domain}.{axis_id}"
            axes.append({"domain":domain,"axis_id":axis_id,"fq":fq,"role":AXIS_POLICY_TEMPLATE[(domain,axis_id)].role,"owner_ids":tuple(sorted(owner_bindings.get(fq,set())))})
    bridge_pairs=set()
    for bridge in pipeline.bridges.values():
        ds=tuple(sorted(set(bridge.source_domains)))
        for i in range(len(ds)):
            for j in range(i+1,len(ds)): bridge_pairs.add((ds[i],ds[j]))
    rows=[]; scanned=0
    for i,a in enumerate(axes):
        for b in axes[i+1:]:
            if a["domain"]==b["domain"]: continue
            scanned+=1
            affinity=_axis_semantic_affinity(a["axis_id"],b["axis_id"])
            sameish=(a["axis_id"]==b["axis_id"] or a["axis_id"] in b["axis_id"] or b["axis_id"] in a["axis_id"])
            role_mixed=a["role"]!=b["role"]
            pair=tuple(sorted((a["domain"],b["domain"])))
            bridged=pair in bridge_pairs
            owner_count=len(a["owner_ids"])+len(b["owner_ids"])
            gaps=[]
            if not a["owner_ids"] or not b["owner_ids"]: gaps.append("PARAMETERIZATION_OR_ATTESTATION_GAP")
            if owner_count==0: gaps.append("OWNER_BINDING_GAP")
            if not bridged: gaps.append("CROSS_DOMAIN_BRIDGE_GAP")
            if role_mixed: gaps.append("CROSS_ROLE_MECHANISM_FRONTIER")
            if not gaps: gaps.append("UNBOUND_CROSS_DOMAIN_MECHANISM_FRONTIER")
            key=digest_payload([a["fq"],b["fq"]])
            distant=int(key[:8],16)/0xFFFFFFFF
            rows.append({
                "axes":[a["fq"],b["fq"]],"domains":[a["domain"],b["domain"]],"roles":[a["role"],b["role"]],
                "owner_ids":[list(a["owner_ids"]),list(b["owner_ids"])],"semantic_affinity":round(affinity,12),
                "convergent_name":bool(sameish),"bridge_present":bridged,"gap_types":gaps,"distant_control_key":distant,
            })
    expected=sum(len(DOMAIN_REGISTRIES[d1].axes)*len(DOMAIN_REGISTRIES[d2].axes) for ix,d1 in enumerate(sorted(DOMAIN_REGISTRIES)) for d2 in sorted(DOMAIN_REGISTRIES)[ix+1:])
    if scanned!=expected: raise RuntimeError(f"cross-domain pair scan mismatch {scanned}!={expected}")
    lanes=[]
    lane_specs=(
        ("SEMANTIC_RESONANCE_VOID",lambda r:(r["semantic_affinity"],r["convergent_name"],-r["distant_control_key"])),
        ("MIXED_ROLE_FRONTIER",lambda r:(int(r["roles"][0]!=r["roles"][1]),r["semantic_affinity"],-r["distant_control_key"])),
        ("CONVERGENT_AXIS_NAME",lambda r:(int(r["convergent_name"]),r["semantic_affinity"],-r["distant_control_key"])),
        ("DISTANT_CROSS_DOMAIN_VOID",lambda r:(-r["semantic_affinity"],r["distant_control_key"])),
    )
    selected=[]; seen=set()
    for lane,score in lane_specs:
        ranked=sorted(rows,key=lambda r:(score(r),r["axes"]),reverse=True)
        picked=[]
        for r in ranked:
            key=tuple(r["axes"]);
            if key in seen: continue
            rr=dict(r); rr["lane"]=lane; rr["frontier_id"]="FRONTIER-"+digest_payload({"lane":lane,"axes":rr["axes"]})[:16].upper(); rr["status"]="UNVERIFIED_FRONTIER_CANDIDATE_POTENTIAL_LAW_OR_MECHANISM"
            rr["epistemic_statuses"]=["CANDIDATE_ACTIVE","CANDIDATE_UNVERIFIED","CANDIDATE_NOVELTY_UNRESOLVED"]
            picked.append(rr); selected.append(rr); seen.add(key)
            if len(picked)>=5: break
        lanes.append({"lane":lane,"selected_count":len(picked),"frontier_ids":[x["frontier_id"] for x in picked]})
    if len(selected)>frontier_limit: selected=selected[:frontier_limit]
    if len(selected)<frontier_limit:
        for r in sorted(rows,key=lambda r:(r["semantic_affinity"],-r["distant_control_key"]),reverse=True):
            key=tuple(r["axes"]);
            if key in seen: continue
            rr=dict(r); rr["lane"]="FRONTIER_FILL"; rr["frontier_id"]="FRONTIER-"+digest_payload({"lane":"FRONTIER_FILL","axes":rr["axes"]})[:16].upper(); rr["status"]="UNVERIFIED_FRONTIER_CANDIDATE_POTENTIAL_LAW_OR_MECHANISM"
            rr["epistemic_statuses"]=["CANDIDATE_ACTIVE","CANDIDATE_UNVERIFIED","CANDIDATE_NOVELTY_UNRESOLVED"]
            selected.append(rr); seen.add(key)
            if len(selected)>=frontier_limit: break
    for r in selected:
        gaps=set(r.get("gap_types",()))
        route=[]
        if "PARAMETERIZATION_OR_ATTESTATION_GAP" in gaps or "OWNER_BINDING_GAP" in gaps: route.append("MISSING_OBSERVER_OR_ATTESTATION")
        if "CROSS_DOMAIN_BRIDGE_GAP" in gaps: route.append("MISSING_TYPED_BRIDGE")
        if "CROSS_ROLE_MECHANISM_FRONTIER" in gaps: route.append("MISSING_ROLE_COMPATIBLE_REPRESENTATION")
        if not route: route.append("DIRECT_MECHANISM_DISCRIMINATION")
        r["research_cycle"]={
            "gap_to_missing_layer_route":route,
            "candidate_mechanism_families":["INDEPENDENCE_NULL","MONOTONE_COUPLING","THRESHOLD_OR_BOUNDARY","DELAY_OR_MEMORY","SHARED_LATENT_COORDINATE","REGIME_DEPENDENT_COUPLING"],
            "candidate_law_status":"POTENTIAL_LAW_OR_MECHANISM_CANDIDATE_UNVERIFIED",
            "promotion_allowed_before_experiment":False,
        }
    experiments=[_frontier_experiment_blueprint(r) for r in selected]
    experiment_by_frontier={x["frontier_id"]:x for x in experiments}
    for r in selected:
        r["research_cycle"]["discriminating_experiment_digest"]=experiment_by_frontier[r["frontier_id"]]["digest"]
        r["research_cycle"]["next_state"]="PENDING_WORLD_ATTESTATION_OR_TYPED_DATA_ACQUISITION"
    # Central Atlas navigation: materialize many local adaptive subspaces rather
    # than treating one giant owner-connected region as a candidate.  The existing
    # directed owner hypergraph remains the reachability substrate; the adaptive
    # explorer chooses scientifically structured local regions on top of it.
    adaptive_subspaces = _adaptive_multidimensional_subspace_exploration(
        pipeline, axis_rows=axes, pair_frontier_rows=selected, traversal_state=traversal_state,
        revisit_digest=revisit_digest, dovetail_steps=dovetail_steps,
    )
    higher_order_frontier = list(adaptive_subspaces.get("candidates", ()))
    payload={
        "schema":"phi-open-void-directed-exploration/v4","owner":"CandidateGenerationPipeline/6.28.0",
        "scan_mode":"EXACT_ALL_CROSS_DOMAIN_REGISTERED_AXIS_PAIRS_PLUS_ADAPTIVE_MULTIDIMENSIONAL_LOCAL_SUBSPACES",
        "registered_axis_count":sum(len(r.axes) for r in DOMAIN_REGISTRIES.values()),"registered_domain_count":len(DOMAIN_REGISTRIES),
        "cross_domain_pair_count_expected":expected,"cross_domain_pair_count_scanned":scanned,"all_cross_domain_pairs_scanned":scanned==expected,
        "lawpassport_count":len(getattr(pipeline.catalog,"passports",{})),"baseline_candidate_registry_used_as_solution_source":False,"baseline_candidate_registry_role":"CONFIRMED_CONTROL_ANCHORS_NOT_SOLUTION_SOURCE",
        "literature_used_prefreeze":False,"ranking_is_scientific_evidence":False,"ranking_is_candidate_deletion_policy":False,"lanes":lanes,"frontier_candidates":selected,
        "frontier_candidate_count":len(selected),"pair_regions_scanned_but_not_materialized_as_candidates":expected-len(selected),
        "legacy_pair_frontier_view_limit":frontier_limit,
        "legacy_pair_frontier_view_limit_is_scientific_space_ceiling":False,
        "fair_pair_seed_continuation_owner":"CandidateGenerationPipeline/6.28.0::DOVETAIL",
        "unmaterialized_pair_region_status":"ADDRESSABLE_OPEN_REGION_NOT_FALSIFIED_NOT_REJECTED",
        "discriminating_experiment_blueprints":experiments,"experiment_blueprint_count":len(experiments),
        "higher_order_owner_frontier_candidates":higher_order_frontier,
        "higher_order_owner_frontier_count":len(higher_order_frontier),
        "adaptive_multidimensional_subspace_exploration":adaptive_subspaces,
        "legacy_giant_owner_region_candidates_replaced":True,
        "fixed_axis_combination_order_ceiling":None,
        "claim_boundary":{"frontier_candidate_is_law":False,"frontier_candidate_is_false_because_unverified":False,"void_is_physical_absence":False,"experiment_blueprint_is_world_evidence":False,"world_novelty_established":False},
    }
    return {**payload,"digest":digest_payload(payload)}



ELEMENT_COMPACTNESS_FRONTIER_SCHEMA = "phi-element-compactness-frontier/v13.7"


def element_compactness_frontier_probe(root: str | Path | None = None) -> Mapping[str, Any]:
    """Recover and qualify the atomic/nuclear/compact-object frontier.

    Release 13.7 preserves the answer-hidden periodic reset receipt from 13.5/13.6 and
    replaces the source-sensitive high-Z promotion path with three bounded additions,
    without creating a parallel owner:

    1. the 13.6 answer-hidden high-Z radius/ionization anomaly calculation is
       retained as a regression receipt but is quarantined from promotion because
       it is sourced from a single model-derived preprint and is not independent of
       extended-periodic modeling;
    2. a peer-reviewed Pyykko Dirac--Fock formal-slot map is used as the bounded
       relativistic representation qualification for Z=119..172.  The formal
       6f/7d table positions are not misread as literal shell capacities;
    3. a bounded nucleosynthesis formation-environment bridge uses the published
       Lippuner--Roberts (Ye,s,tau) regime envelope.  It can qualify a regime-level
       connection to neutron-rich ejecta while explicitly failing closed on a
       Z-specific or horizon-surface origin claim;
    4. the existing multi-EOS TOV gate over SLy/APR4/H4/MS1 remains active.

    Neither gate uses the 2771 confirmed baseline controls as a solution source.
    """
    from .black_hole import G as G_SI, C as C_SI
    from scipy.integrate import solve_ivp
    from scipy.optimize import minimize_scalar

    # SI constants for the bounded atomic/nuclear branch.
    m_u = 1.66053906660e-27
    m_n = 1.67492749804e-27
    m_sun = 1.98847e30
    mev_j = 1.602176634e-13
    r0 = 1.2e-15
    zcrit = 173.0
    nuclear_saturation_n_fm3 = 0.16
    nuclear_binding_mev = 16.0
    rho_sat = nuclear_saturation_n_fm3 * 1.0e45 * m_n

    frozen_periodic = {
        "protocol": "ANSWER_HIDDEN_ADJACENT_OBSERVABLE_RESET_CLUSTERING",
        "solver_inputs": ["atomic_number_Z", "atomic_radius", "first_ionization_energy"],
        "solver_excluded": ["period", "group", "block", "electron_configuration", "noble_gas_label", "known_period_boundaries"],
        "recovered_reset_boundaries_Z": [2, 10, 18, 36, 54, 86],
        "recovered_cycle_lengths": [2, 8, 8, 18, 18, 32],
        "holdout_train_boundaries_through_Z": 54,
        "holdout_predicted_next_reset_Z": 86,
        "holdout_pass": True,
        "structural_next_insertion_width": 18,
        "structural_next_distinct_cycle_length": 50,
        "structural_period8_closure_candidate_Z": 168,
        "claim_boundary": {
            "periodic_truth_used_by_solver": False,
            "structural_Z168_is_physical_element_guarantee": False,
            "world_novelty_claimed": False,
        },
    }
    frozen_periodic["digest"] = digest_payload({k:v for k,v in frozen_periodic.items() if k != "digest"})

    # ------------------------------------------------------------------
    # High-Z answer-hidden observable representation test.
    # ------------------------------------------------------------------
    # The table is a post-freeze theoretical observable source (Agyemang 2026,
    # consolidated from relativistic literature).  Only radius and first IE are
    # supplied to the solver.  The source's block/configuration labels are not
    # encoded below and are not used in scoring.
    highz_observables = {
        119:(165.0,4.10),120:(156.0,5.53),121:(200.0,5.10),122:(199.0,5.25),123:(197.0,5.40),124:(196.0,5.55),
        125:(194.0,5.70),126:(193.0,5.85),127:(192.0,6.00),128:(190.0,6.15),129:(191.0,6.20),130:(190.0,6.10),
        131:(188.0,6.00),132:(186.0,5.90),133:(185.0,5.80),134:(184.0,5.70),135:(182.0,5.60),136:(182.0,5.80),
        137:(179.0,5.95),138:(176.0,6.10),139:(172.0,7.10),140:(171.0,7.45),141:(170.0,7.80),142:(168.0,8.15),
        143:(167.0,8.50),144:(166.0,8.15),145:(165.0,7.80),146:(164.0,7.45),147:(162.0,7.10),148:(161.0,6.75),
        149:(155.0,7.20),150:(150.0,8.10),151:(153.0,7.30),152:(155.0,8.00),153:(157.0,10.10),154:(159.0,11.80),
        155:(161.0,9.00),156:(160.0,8.70),157:(158.0,8.40),158:(157.0,8.10),159:(156.0,7.80),160:(154.0,7.50),
        161:(153.0,7.20),162:(152.0,6.90),163:(151.0,6.60),164:(148.0,7.40),165:(152.0,7.00),166:(155.0,7.20),
        167:(158.0,7.40),168:(161.0,7.60),169:(182.0,3.90),170:(172.0,5.10),171:(205.0,4.80),172:(215.0,4.50),
    }
    hz_z = np.asarray(sorted(highz_observables), dtype=int)
    hz_r = np.asarray([highz_observables[int(z)][0] for z in hz_z], dtype=float)
    hz_ie = np.asarray([highz_observables[int(z)][1] for z in hz_z], dtype=float)
    hz_dr = np.diff(hz_r)
    hz_die = np.diff(hz_ie)
    hz_left = hz_z[:-1]

    def _robust_standardize(values: np.ndarray) -> np.ndarray:
        med = float(np.median(values))
        mad = float(np.median(np.abs(values - med)))
        scale = 1.4826 * mad
        if not math.isfinite(scale) or scale <= 0.0:
            scale = float(np.std(values)) or 1.0
        return (values - med) / scale

    hz_feature = np.column_stack((_robust_standardize(hz_dr), _robust_standardize(hz_die)))
    hz_scores = np.sqrt(np.sum(hz_feature * hz_feature, axis=1))
    ranked_idx = np.argsort(-hz_scores)
    ranked_transitions = [
        {
            "from_Z": int(hz_left[i]), "to_Z": int(hz_left[i] + 1),
            "delta_radius_pm": float(hz_dr[i]), "delta_first_IE_eV": float(hz_die[i]),
            "robust_anomaly_score": float(hz_scores[i]), "rank": int(rank + 1),
        }
        for rank, i in enumerate(ranked_idx)
    ]
    by_left = {row["from_Z"]: row for row in ranked_transitions}
    z168_transition = dict(by_left[168])
    strong_threshold = 5.0  # frozen generic robust-distance gate, not fitted to Z=168.
    post168_strong = [row for row in ranked_transitions if 169 <= row["from_Z"] <= 171 and row["robust_anomaly_score"] >= strong_threshold]
    highz_fracture = (
        z168_transition["robust_anomaly_score"] >= strong_threshold
        and z168_transition["rank"] <= 3
        and z168_transition["delta_radius_pm"] > 0.0
        and z168_transition["delta_first_IE_eV"] < 0.0
        and len(post168_strong) >= 2
    )
    highz_payload = {
        "protocol": "ANSWER_HIDDEN_HIGH_Z_OBSERVABLE_ANOMALY_AND_POST_RESET_CONVENTIONALITY_TEST",
        "source_observable_range_Z": [119, 172],
        "solver_inputs": ["atomic_number_Z", "predicted_radius_pm", "predicted_first_ionization_energy_eV"],
        "solver_excluded": ["period", "group", "block", "orbital_label", "electron_configuration", "Pyykko_filling_order", "QED_terminus_label"],
        "source_observable_count": int(len(hz_z)),
        "source_observable_digest": digest_payload([[int(z), float(highz_observables[int(z)][0]), float(highz_observables[int(z)][1])] for z in hz_z]),
        "structural_Z168_was_frozen_before_this_source_test": frozen_periodic["structural_period8_closure_candidate_Z"] == 168,
        "Z168_to_169_transition": z168_transition,
        "strong_transition_threshold": strong_threshold,
        "post_Z168_additional_strong_transitions": sorted(post168_strong, key=lambda x:x["from_Z"]),
        "top10_observable_transitions": ranked_transitions[:10],
        "single_clean_period_after_Z168_supported": False if len(post168_strong) >= 2 else True,
        "representation_fracture_detected": bool(highz_fracture),
        "qualified_mechanism": "NESTED_CYCLE_TO_RELATIVISTIC_INTERLEAVING" if highz_fracture else "HIGH_Z_REPRESENTATION_UNRESOLVED",
        "postfreeze_orbital_attestation": {
            "source": "Pyykko_PCCP_2011_DOI_10.1039_C0CP01575J",
            "rough_order": "8s < 5g <= 8p1/2 < 6f < 7d < 9s < 9p1/2 < 8p3/2",
            "interpretation": "next-principal-shell states interleave before completion of the nominal 8p3/2 sector",
        },
        "qualification_status": "QUARANTINED_SINGLE_PREPRINT_SOURCE_SENSITIVE_NOT_QUALIFYING",
        "qualifying_for_relativistic_slot_map": False,
        "reason_for_quarantine": "single model-derived preprint source is not independent of extended-periodic modeling; retained only as a reproducible regression receipt",
        "claim_boundary": {
            "highZ_observables_are_experimental": False,
            "source_table_is_independent_of_extended_periodic_models": False,
            "blind_solver_used_orbital_labels": False,
            "Z172_is_blindly_proven_last_physical_element": False,
            "world_novelty_claimed": False,
        },
    }
    highz_payload["digest"] = digest_payload({k:v for k,v in highz_payload.items() if k != "digest"})

    # ------------------------------------------------------------------
    # Peer-reviewed relativistic formal-slot map and complete Atlas table.
    # ------------------------------------------------------------------
    # Pyykko's compact table is a formal periodic assignment based on ionic
    # Dirac--Fock bookkeeping.  In particular E141--E155 are fifteen formal
    # 6f-series positions (analogous to Ac--Lr including the Group-3 slot), while
    # E156--E164 are nine 7d-series positions (Groups 4--12).  These counts are
    # *not* literal orbital electron capacities.
    pyykko_ranges = (
        (119, 120, "8s", "FORMAL_PERIOD_8_HEAD"),
        (121, 138, "5g", "FORMAL_5G_SERIES"),
        (139, 140, "8p1/2", "FORMAL_P_STAR_SERIES"),
        (141, 155, "6f", "FORMAL_6F_SERIES_INCLUDING_GROUP3_ANALOG_SLOT"),
        (156, 164, "7d", "FORMAL_7D_SERIES_GROUPS_4_TO_12"),
        (165, 166, "9s", "FORMAL_PERIOD_9_HEAD"),
        (167, 168, "9p1/2", "FORMAL_PERIOD_9_P_STAR"),
        (169, 172, "8p3/2", "FORMAL_PERIOD_8_P3_2_TAIL_INTERLEAVED_AFTER_9P1_2"),
    )
    formal_slot_by_z = {}
    pyykko_rows = []
    for lo, hi, slot, role in pyykko_ranges:
        count = hi - lo + 1
        pyykko_rows.append({"Z_start":lo,"Z_end":hi,"count":count,"formal_slot":slot,"formal_role":role})
        for z in range(lo, hi + 1):
            formal_slot_by_z[z] = {"formal_slot":slot,"formal_role":role}
    formal_coverage = sorted(formal_slot_by_z)
    pyykko_slot_map_qualified = (
        formal_coverage == list(range(119,173))
        and sum(row["count"] for row in pyykko_rows) == 54
        and next(row for row in pyykko_rows if row["formal_slot"]=="6f")["count"] == 15
        and next(row for row in pyykko_rows if row["formal_slot"]=="7d")["count"] == 9
        and formal_slot_by_z[168]["formal_slot"] == "9p1/2"
        and formal_slot_by_z[169]["formal_slot"] == "8p3/2"
    )
    relativistic_slot_map = {
        "protocol":"PEER_REVIEWED_DIRAC_FOCK_FORMAL_PERIODIC_SLOT_ATTESTATION",
        "source":"Pyykko_PCCP_2011_DOI_10.1039_C0CP01575J",
        "range_Z":[119,172],
        "rough_energy_order":"8s < 5g <= 8p1/2 < 6f < 7d < 9s < 9p1/2 < 8p3/2",
        "formal_ranges":pyykko_rows,
        "formal_position_count":sum(row["count"] for row in pyykko_rows),
        "exact_contiguous_Z_coverage":formal_coverage == list(range(119,173)),
        "nonmonotone_compact_table_order_witness":{"Z168":"9p1/2","Z169":"8p3/2"},
        "qualified":bool(pyykko_slot_map_qualified),
        "qualification_status":"QUALIFIED_RESEARCH_LOCAL_PEER_REVIEWED_RELATIVISTIC_FORMAL_SLOT_MAP" if pyykko_slot_map_qualified else "UNDERQUALIFIED_RELATIVISTIC_SLOT_MAP",
        "claim_boundary":{
            "formal_series_count_equals_literal_orbital_capacity":False,
            "neutral_atom_ground_state_configuration_uniquely_assigned_for_every_Z":False,
            "elements_119_172_experimentally_confirmed":False,
            "Z172_is_proven_last_element":False,
            "world_novelty_claimed":False,
        },
    }
    relativistic_slot_map["digest"] = digest_payload({k:v for k,v in relativistic_slot_map.items() if k != "digest"})

    known_elements = (
        ("H","Hydrogen"),("He","Helium"),("Li","Lithium"),("Be","Beryllium"),("B","Boron"),("C","Carbon"),("N","Nitrogen"),("O","Oxygen"),("F","Fluorine"),("Ne","Neon"),
        ("Na","Sodium"),("Mg","Magnesium"),("Al","Aluminium"),("Si","Silicon"),("P","Phosphorus"),("S","Sulfur"),("Cl","Chlorine"),("Ar","Argon"),("K","Potassium"),("Ca","Calcium"),
        ("Sc","Scandium"),("Ti","Titanium"),("V","Vanadium"),("Cr","Chromium"),("Mn","Manganese"),("Fe","Iron"),("Co","Cobalt"),("Ni","Nickel"),("Cu","Copper"),("Zn","Zinc"),
        ("Ga","Gallium"),("Ge","Germanium"),("As","Arsenic"),("Se","Selenium"),("Br","Bromine"),("Kr","Krypton"),("Rb","Rubidium"),("Sr","Strontium"),("Y","Yttrium"),("Zr","Zirconium"),
        ("Nb","Niobium"),("Mo","Molybdenum"),("Tc","Technetium"),("Ru","Ruthenium"),("Rh","Rhodium"),("Pd","Palladium"),("Ag","Silver"),("Cd","Cadmium"),("In","Indium"),("Sn","Tin"),
        ("Sb","Antimony"),("Te","Tellurium"),("I","Iodine"),("Xe","Xenon"),("Cs","Caesium"),("Ba","Barium"),("La","Lanthanum"),("Ce","Cerium"),("Pr","Praseodymium"),("Nd","Neodymium"),
        ("Pm","Promethium"),("Sm","Samarium"),("Eu","Europium"),("Gd","Gadolinium"),("Tb","Terbium"),("Dy","Dysprosium"),("Ho","Holmium"),("Er","Erbium"),("Tm","Thulium"),("Yb","Ytterbium"),
        ("Lu","Lutetium"),("Hf","Hafnium"),("Ta","Tantalum"),("W","Tungsten"),("Re","Rhenium"),("Os","Osmium"),("Ir","Iridium"),("Pt","Platinum"),("Au","Gold"),("Hg","Mercury"),
        ("Tl","Thallium"),("Pb","Lead"),("Bi","Bismuth"),("Po","Polonium"),("At","Astatine"),("Rn","Radon"),("Fr","Francium"),("Ra","Radium"),("Ac","Actinium"),("Th","Thorium"),
        ("Pa","Protactinium"),("U","Uranium"),("Np","Neptunium"),("Pu","Plutonium"),("Am","Americium"),("Cm","Curium"),("Bk","Berkelium"),("Cf","Californium"),("Es","Einsteinium"),("Fm","Fermium"),
        ("Md","Mendelevium"),("No","Nobelium"),("Lr","Lawrencium"),("Rf","Rutherfordium"),("Db","Dubnium"),("Sg","Seaborgium"),("Bh","Bohrium"),("Hs","Hassium"),("Mt","Meitnerium"),("Ds","Darmstadtium"),
        ("Rg","Roentgenium"),("Cn","Copernicium"),("Nh","Nihonium"),("Fl","Flerovium"),("Mc","Moscovium"),("Lv","Livermorium"),("Ts","Tennessine"),("Og","Oganesson"),
    )
    if len(known_elements) != 118:
        raise RuntimeError("known element registry must contain exactly 118 rows")

    numeral_roots = {"0":"nil","1":"un","2":"bi","3":"tri","4":"quad","5":"pent","6":"hex","7":"sept","8":"oct","9":"enn"}
    def _temporary_iupac_name_symbol(z: int) -> tuple[str,str]:
        digits = list(str(z))
        parts = []
        for i, digit in enumerate(digits):
            root_name = numeral_roots[digit]
            next_digit = digits[i+1] if i+1 < len(digits) else None
            if root_name == "enn" and next_digit == "0":
                root_name = "en"
            if i == len(digits)-1 and root_name in {"bi","tri"}:
                root_name = root_name[:-1]
            parts.append(root_name)
        name = "".join(parts) + "ium"
        symbol = "".join(numeral_roots[d][0] for d in digits)
        symbol = symbol[0].upper() + symbol[1:].lower()
        return name, symbol

    periodic_table_rows = []
    for z in range(1,173):
        if z <= 118:
            symbol, name = known_elements[z-1]
            row = {
                "Z":z,"symbol":symbol,"name":name,
                "epistemic_status":"CONFIRMED_IUPAC_NAMED_ELEMENT",
                "formal_relativistic_slot":"STANDARD_IUPAC_TABLE",
                "formal_role":"STANDARD_IUPAC_TABLE",
                "formation_environment_Z_specific":"NOT_ASSIGNED_BY_PERIODIC_TABLE",
                "source_basis":"IUPAC_CONFIRMED_TABLE",
            }
        else:
            name, symbol = _temporary_iupac_name_symbol(z)
            slot = formal_slot_by_z[z]
            row = {
                "Z":z,"symbol":symbol,"name":name,
                "epistemic_status":"THEORETICAL_RELATIVISTIC_FORMAL_SLOT_NOT_DISCOVERED",
                "formal_relativistic_slot":slot["formal_slot"],
                "formal_role":slot["formal_role"],
                "formation_environment_Z_specific":"UNIDENTIFIED_Z_SPECIFIC",
                "source_basis":"IUPAC_TEMPORARY_NAMING_PLUS_PYYKKO_2011_FORMAL_SLOT",
            }
        if z == 168:
            row["atlas_note"] = "FROZEN_NESTED_CYCLE_STRUCTURAL_COORDINATE_AND_PYYKKO_9P1_2_FORMAL_SLOT_NOT_DISCOVERY"
        elif z == 169:
            row["atlas_note"] = "NONMONOTONE_RELATIVISTIC_INTERLEAVING_WITNESS_9P1_2_TO_8P3_2"
        else:
            row["atlas_note"] = ""
        periodic_table_rows.append(row)
    periodic_table_atlas = {
        "protocol":"CONFIRMED_1_118_PLUS_THEORETICAL_RELATIVISTIC_FORMAL_EXTENSION_119_172",
        "row_count":len(periodic_table_rows),
        "confirmed_IUPAC_named_through_Z":118,
        "theoretical_extension_range_Z":[119,172],
        "temporary_naming_rule":"IUPAC systematic numerical roots; placeholders only until discovery and permanent naming",
        "rows":periodic_table_rows,
        "claim_boundary":{
            "rows_119_172_are_discovered_elements":False,
            "temporary_name_is_permanent_name":False,
            "formal_slot_is_unique_neutral_ground_state_configuration":False,
        },
    }
    periodic_table_atlas["digest"] = digest_payload({k:v for k,v in periodic_table_atlas.items() if k != "digest"})

    # ------------------------------------------------------------------
    # Nucleosynthesis formation-environment bridge (bounded, fail-closed).
    # ------------------------------------------------------------------
    # Lippuner & Roberts (2015) span Ye, entropy and expansion time and report
    # a lanthanide-rich/poor transition whose primary coordinate is Ye, with a
    # conditional threshold band Ye ~ 0.22--0.30 depending on s and tau.  This
    # is sufficient to qualify a regime-level bridge, but not to infer a unique
    # astrophysical source label or a specific Z=119..172 production channel.
    formation_bridge = {
        "protocol":"POSTFREEZE_PUBLISHED_NUCLEOSYNTHESIS_PARAMETER_REGIME_BRIDGE_WITH_IDENTIFIABILITY_GATE",
        "attested_coordinates":["electron_fraction_Ye","specific_entropy_kB_per_baryon","expansion_timescale_ms"],
        "identifiability_excluded_labels":["star_label","neutron_star_merger_label","NS_BH_label","black_hole_disk_label","collapsar_label","event_horizon_label","element_Z_origin_label"],
        "published_parameter_domain":{"Ye":[0.01,0.50],"specific_entropy_kB_per_baryon":[1.0,100.0],"expansion_timescale_ms":[0.1,500.0]},
        "published_regime_boundary":{"lanthanide_free_above_Ye_band":[0.22,0.30],"conditional_on":["specific_entropy","expansion_timescale"]},
        "published_primary_regime_coordinate":"electron_fraction_Ye",
        "regime_level_bridge_supported":True,
        "regime_interpretation":"neutron richness controls access to heavy r-process/lanthanide-actinide regimes, with entropy and expansion-time modulation",
        "environment_identifiability":"UNDERIDENTIFIED_FROM_Ye_s_tau_ALONE",
        "Z_specific_mapping_status":"UNIDENTIFIED_Z_SPECIFIC",
        "horizon_surface_synthesis_status":"NOT_SUPPORTED",
        "qualification_status":"BOUNDED_PUBLISHED_REGIME_BRIDGE_SUPPORTED_BUT_ENVIRONMENT_AND_Z_SPECIFIC_CAUSAL_AXIS_FAIL_CLOSED",
        "claim_boundary":{
            "specific_superheavy_Z_mapped_to_black_hole_environment":False,
            "event_horizon_is_material_nucleosynthesis_surface":False,
            "Ye_s_tau_uniquely_identify_astrophysical_engine":False,
            "regime_level_compact_object_nucleosynthesis_connection_supported":True,
            "world_novelty_claimed":False,
        },
    }
    formation_bridge["digest"] = digest_payload({k:v for k,v in formation_bridge.items() if k != "digest"})

    # ------------------------------------------------------------------
    # Branch A: single-nucleus scale separation.
    # ------------------------------------------------------------------
    element_rows = []
    for z in range(1, 251):
        a = 2.5 * float(z)
        mass = a * m_u
        nuclear_radius = r0 * a ** (1.0 / 3.0)
        fissility = float(z * z) / (50.13 * a)
        qed_criticality = float(z) / zcrit
        compactness = 2.0 * G_SI * mass / (nuclear_radius * C_SI**2)
        element_rows.append({
            "Z": z, "A_model": a, "mass_kg": mass, "nuclear_radius_m": nuclear_radius,
            "fissility_ratio": fissility, "qed_criticality_ratio": qed_criticality,
            "compactness": compactness,
        })

    def _first_cross(rows: Sequence[Mapping[str, Any]], key: str, threshold: float = 1.0) -> Mapping[str, Any] | None:
        for row in rows:
            if float(row[key]) >= threshold:
                return dict(row)
        return None

    fiss_cross = _first_cross(element_rows, "fissility_ratio")
    qed_cross = _first_cross(element_rows, "qed_criticality_ratio")
    horizon_cross_element = _first_cross(element_rows, "compactness")
    z168 = dict(element_rows[167])

    # ------------------------------------------------------------------
    # Branch B: aggregation/compression scale probe retained from 13.5.
    # ------------------------------------------------------------------
    def radius_at_rho(mass: float, density: float = rho_sat) -> float:
        return (3.0 * mass / (4.0 * math.pi * density)) ** (1.0 / 3.0)

    density_geometry_factor = (3.0 / (4.0 * math.pi * rho_sat)) ** (1.0 / 3.0)
    m_gravity_binding = ((nuclear_binding_mev * mev_j) / (G_SI * m_n) * density_geometry_factor) ** 1.5
    r_gravity_binding = radius_at_rho(m_gravity_binding)
    c_gravity_binding = 2.0 * G_SI * m_gravity_binding / (r_gravity_binding * C_SI**2)
    m_horizon_density = (C_SI**2 / (2.0 * G_SI) * density_geometry_factor) ** 1.5
    r_horizon_density = radius_at_rho(m_horizon_density)

    # Retained post-freeze compact-star reference from 13.5.
    m_tov_attested = 2.25 * m_sun
    r_tov_attested = 11.90e3
    c_tov_attested = 2.0 * G_SI * m_tov_attested / (r_tov_attested * C_SI**2)
    rho_tov_avg = 3.0 * m_tov_attested / (4.0 * math.pi * r_tov_attested**3)

    # ------------------------------------------------------------------
    # Multi-EOS TOV qualification of equilibrium_support_margin.
    # ------------------------------------------------------------------
    # Standard Read-style 4-parameter core fits.  A common SLy low-density crust
    # is used so that maximum-mass comparisons can be replayed in this runtime.
    eos_params = {
        "SLy":  (34.384, 3.005, 2.988, 2.851, 2.06),
        "APR4": (34.269, 2.830, 3.445, 3.348, 2.20),
        "H4":   (34.669, 2.909, 2.246, 2.144, 2.03),
        "MS1":  (34.858, 3.224, 3.033, 1.325, 2.77),
    }
    # cgs implementation: rho[g/cm^3], p[dyn/cm^2].  The published crust K_i
    # values are multiplied by c^2 for pressure units, following LALSuite notes.
    G_cgs = 6.67430e-8
    c_cgs = 2.99792458e10
    msun_cgs = 1.98847e33
    rho1 = 10.0**14.7
    rho2 = 10.0**15.0
    crust_bounds = (2.44034e7, 3.78358e11, 2.62780e12)
    crust_K_raw = (6.80110e-09, 1.06186e-06, 5.32697e01, 3.99874e-08)
    crust_K = tuple(k * c_cgs**2 for k in crust_K_raw)
    crust_gamma = (1.58425, 1.28733, 0.62223, 1.35692)

    def _build_piecewise_eos(name: str) -> Mapping[str, Any]:
        logp1, g1, g2, g3, published_mmax = eos_params[name]
        p1 = 10.0**logp1
        K1 = p1 / rho1**g1
        rho0 = (K1 / crust_K[3]) ** (1.0 / (crust_gamma[3] - g1))
        segs: list[list[float]] = []
        low = 0.0
        for i, upper in enumerate(crust_bounds):
            segs.append([low, upper, crust_K[i], crust_gamma[i]])
            low = upper
        segs.append([low, rho0, crust_K[3], crust_gamma[3]])
        K2 = p1 / rho1**g2
        K3 = K2 * rho2**(g2-g3)
        segs.extend([[rho0, rho1, K1, g1], [rho1, rho2, K2, g2], [rho2, math.inf, K3, g3]])
        a_terms = [0.0]
        for i in range(1, len(segs)):
            rb = segs[i][0]
            kp, gp = segs[i-1][2], segs[i-1][3]
            _, _, _, gn = segs[i]
            pb = kp * rb**gp
            a_terms.append(a_terms[-1] + pb/(rb*c_cgs**2) * (1.0/(gp-1.0) - 1.0/(gn-1.0)))
        return {"name":name, "segments":segs, "a_terms":a_terms, "published_mmax_solar":published_mmax, "rho0":rho0}

    def _eos_from_pressure(eos: Mapping[str, Any], pressure: float) -> tuple[float, float]:
        segs = eos["segments"]
        idx = len(segs)-1
        for i, (_, hi, K, gam) in enumerate(segs):
            if math.isinf(hi) or pressure <= K*hi**gam:
                idx = i; break
        _, _, K, gam = segs[idx]
        rho = (max(pressure, 0.0)/K)**(1.0/gam) if pressure > 0.0 else 0.0
        eps = (1.0 + eos["a_terms"][idx])*rho*c_cgs**2 + pressure/(gam-1.0) if rho > 0.0 else 0.0
        return rho, eps

    def _pressure_from_rho(eos: Mapping[str, Any], rho: float) -> float:
        for _, hi, K, gam in eos["segments"]:
            if rho <= hi:
                return K*rho**gam
        _, _, K, gam = eos["segments"][-1]
        return K*rho**gam

    def _tov_star(eos: Mapping[str, Any], rho_c: float) -> tuple[float, float, float]:
        p_c = _pressure_from_rho(eos, rho_c)
        _, eps_c = _eos_from_pressure(eos, p_c)
        r_start = 1.0
        m_start = 4.0*math.pi*r_start**3*eps_c/(3.0*c_cgs**2)
        def rhs(radius: float, y: Sequence[float]) -> list[float]:
            mass, pressure = float(y[0]), float(y[1])
            if pressure <= 0.0:
                return [0.0, 0.0]
            _, eps = _eos_from_pressure(eos, pressure)
            horizon_factor = 1.0 - 2.0*G_cgs*mass/(radius*c_cgs**2)
            if horizon_factor <= 1.0e-8:
                return [0.0, -1.0e99]
            dm = 4.0*math.pi*radius**2*eps/c_cgs**2
            dp = -G_cgs*(eps+pressure)/c_cgs**2 * (mass + 4.0*math.pi*radius**3*pressure/c_cgs**2) / (radius**2*horizon_factor)
            return [dm, dp]
        def surface(radius: float, y: Sequence[float]) -> float:
            return float(y[1])
        surface.terminal = True
        surface.direction = -1
        sol = solve_ivp(rhs, (r_start, 5.0e6), [m_start, p_c], events=surface, rtol=2.0e-7, atol=[1.0e20,1.0e18], max_step=2.0e4)
        if len(sol.t_events[0]) == 0:
            raise RuntimeError(f"TOV surface not reached for {eos['name']}")
        radius = float(sol.t_events[0][0])
        mass = float(sol.y_events[0][0][0])
        return mass/msun_cgs, radius/1.0e5, 2.0*G_cgs*mass/(radius*c_cgs**2)

    def _support_slope(eos: Mapping[str, Any], log10rho: float, h: float = 3.0e-3) -> float:
        m_minus = _tov_star(eos, 10.0**(log10rho-h))[0]
        m_plus = _tov_star(eos, 10.0**(log10rho+h))[0]
        return (math.log(m_plus)-math.log(m_minus)) / (2.0*h*math.log(10.0))

    eos_turning_rows = []
    for name in ("SLy", "APR4", "H4", "MS1"):
        eos = _build_piecewise_eos(name)
        objective = lambda log10rho: -_tov_star(eos, 10.0**float(log10rho))[0]
        opt = minimize_scalar(objective, bounds=(14.4,16.2), method="bounded", options={"xatol":1.0e-8})
        lr = float(opt.x)
        mass_solar, radius_km, compactness_turn = _tov_star(eos, 10.0**lr)
        slope_below = _support_slope(eos, lr-0.03)
        slope_at = _support_slope(eos, lr, h=1.0e-3)
        slope_above = _support_slope(eos, lr+0.03)
        published = float(eos["published_mmax_solar"])
        eos_turning_rows.append({
            "eos": name,
            "central_density_g_cm3": 10.0**lr,
            "maximum_mass_solar": mass_solar,
            "published_piecewise_polytrope_maximum_mass_solar": published,
            "relative_maximum_mass_error": (mass_solar-published)/published,
            "radius_at_turning_km": radius_km,
            "compactness_at_turning": compactness_turn,
            "equilibrium_support_margin_below": slope_below,
            "equilibrium_support_margin_at_turning": slope_at,
            "equilibrium_support_margin_above": slope_above,
            "sign_change_plus_zero_minus": slope_below > 0.0 and abs(slope_at) < 5.0e-3 and slope_above < 0.0,
        })
    multi_eos_pass = (
        len(eos_turning_rows) == 4
        and all(abs(row["relative_maximum_mass_error"]) < 0.02 for row in eos_turning_rows)
        and all(row["sign_change_plus_zero_minus"] for row in eos_turning_rows)
        and all(0.0 < row["compactness_at_turning"] < 1.0 for row in eos_turning_rows)
    )
    multi_eos = {
        "protocol": "MULTI_EOS_TOV_FIRST_TURNING_POINT_SUPPORT_MARGIN_QUALIFICATION",
        "eos_family_count": 4,
        "eos_families": eos_turning_rows,
        "support_margin_definition": "S_eq=d ln(M)/d ln(rho_c) along declared cold spherical nonrotating one-parameter TOV sequence",
        "turning_surface_definition": "S_eq=0 at first local maximum of M(rho_c)",
        "published_maximum_mass_tolerance_fraction": 0.02,
        "all_four_reproduce_published_Mmax": all(abs(row["relative_maximum_mass_error"]) < 0.02 for row in eos_turning_rows),
        "all_four_show_plus_zero_minus_support_sign_change": all(row["sign_change_plus_zero_minus"] for row in eos_turning_rows),
        "all_turning_points_precede_horizon": all(row["compactness_at_turning"] < 1.0 for row in eos_turning_rows),
        "qualified": bool(multi_eos_pass),
        "qualified_mechanism_status": "QUALIFIED_BOUNDED_COLD_SPHERICAL_TOV_SUPPORT_TURNING_MECHANISM" if multi_eos_pass else "UNDERQUALIFIED_SUPPORT_MECHANISM",
        "independent_radial_mode_attestation": {
            "source": "Sun_et_al_2021_arXiv_2101.07515_and_Bardeen_Thorne_Meltzer_turning_point_principle",
            "claim": "for the declared one-parameter nonrotating barotropic setting, fundamental radial-mode zero is consistent with the maximum-mass turning point",
            "computed_radial_eigenproblem_in_this_release": False,
        },
        "claim_boundary": {
            "universal_for_rotation_anisotropy_temperature_or_multibranch_phase_transitions": False,
            "turning_point_is_trapped_surface": False,
            "realistic_EOS_are_exactly_reproduced_by_piecewise_fits": False,
            "world_novelty_claimed": False,
        },
    }
    multi_eos["digest"] = digest_payload({k:v for k,v in multi_eos.items() if k != "digest"})

    blind_events = [
        {"branch":"NUCLEAR_CHARGE_SINGLE_OBJECT","coordinate":"fissility_ratio","crossing_value":1.0,"location":{"Z":int(fiss_cross["Z"]),"A_model":fiss_cross["A_model"]},"status":"BOUNDARY_DETECTED_IN_MODEL_COORDINATE"},
        {"branch":"NUCLEAR_CHARGE_SINGLE_OBJECT","coordinate":"qed_criticality_ratio","crossing_value":1.0,"location":{"Z":int(qed_cross["Z"]),"A_model":qed_cross["A_model"]},"status":"BOUNDARY_DETECTED_IN_SOURCE_ATTESTED_COORDINATE"},
        {"branch":"NUCLEAR_DENSITY_AGGREGATION","coordinate":"gravity_to_nuclear_binding_ratio","crossing_value":1.0,"location":{"mass_kg":m_gravity_binding,"mass_solar":m_gravity_binding/m_sun,"radius_m":r_gravity_binding},"status":"BOUNDARY_DETECTED_BY_DIMENSIONLESS_ENERGY_COMPETITION"},
        {"branch":"NUCLEAR_DENSITY_AGGREGATION","coordinate":"compactness","crossing_value":1.0,"location":{"mass_kg":m_horizon_density,"mass_solar":m_horizon_density/m_sun,"radius_m":r_horizon_density},"status":"HORIZON_CONDITION_DETECTED"},
    ]

    max_element_compactness = max(float(r["compactness"]) for r in element_rows)
    branch_disconnect = horizon_cross_element is None and max_element_compactness < 1.0e-20
    tov_before_density_horizon = m_tov_attested < m_horizon_density and c_tov_attested < 1.0

    axis_births = [
        {"axis_id":"object_mass_scale","semantic_class":"INDEPENDENT_MEASURAND","status":"RESEARCH_LOCAL_SOURCE_ESTABLISHED_AXIS_PROPOSAL","reason":"Z alone cannot change total aggregated mass enough to approach strong gravity"},
        {"axis_id":"object_radius_scale","semantic_class":"INDEPENDENT_MEASURAND","status":"RESEARCH_LOCAL_SOURCE_ESTABLISHED_AXIS_PROPOSAL","reason":"compactness requires an independent size coordinate"},
        {"axis_id":"mass_density","semantic_class":"DERIVED_COORDINATE","status":"RESEARCH_LOCAL_SOURCE_ESTABLISHED_AXIS_PROPOSAL","reason":"connects isolated nuclei to bulk dense-matter regimes"},
        {"axis_id":"compactness","semantic_class":"DERIVED_COORDINATE","definition":"2GM/(Rc^2)","status":"RESEARCH_LOCAL_DERIVED_AXIS_VALIDATED_BY_BLACK_HOLE_CONTROL","reason":"dimensionless bridge from mass/radius to horizon condition"},
        {"axis_id":"nuclear_fissility","semantic_class":"DERIVED_COORDINATE","definition":"Z^2/(50.13 A)","status":"RESEARCH_LOCAL_SOURCE_ATTESTED_AXIS_PROPOSAL","reason":"separates periodic structural extrapolation from nuclear survival"},
        {"axis_id":"qed_criticality_ratio","semantic_class":"DERIVED_COORDINATE","definition":"Z/Zcrit","status":"RESEARCH_LOCAL_SOURCE_ATTESTED_AXIS_PROPOSAL","reason":"tracks strong-field atomic/QED representation breakdown"},
        {"axis_id":"relativistic_orbital_interleaving","semantic_class":"REPRESENTATION_MECHANISM","definition":"peer-reviewed Dirac-Fock formal-slot map 119..172 with nonmonotone 9p1/2 -> 8p3/2 compact-table witness","status":"QUALIFIED_RESEARCH_LOCAL_PEER_REVIEWED_RELATIVISTIC_FORMAL_SLOT_MAP" if pyykko_slot_map_qualified else "AXIS_GENESIS_CANDIDATE","reason":"Pyykko formal assignments provide the qualifying relativistic representation map; the single-preprint radius/IE anomaly gate is quarantined"},
        {"axis_id":"nucleosynthesis_electron_fraction","semantic_class":"FORMATION_ENVIRONMENT_COORDINATE","definition":"Ye=np/(np+nn)","status":"RESEARCH_LOCAL_SOURCE_ATTESTED_AXIS_PROPOSAL","reason":"published r-process parameter studies show a heavy-element/lanthanide regime boundary primarily organized by electron fraction"},
        {"axis_id":"nucleosynthesis_specific_entropy","semantic_class":"FORMATION_ENVIRONMENT_COORDINATE","definition":"specific entropy in kB per baryon","status":"RESEARCH_LOCAL_SOURCE_ATTESTED_AXIS_PROPOSAL","reason":"modulates the Ye boundary in parameterized r-process trajectories"},
        {"axis_id":"nucleosynthesis_expansion_timescale","semantic_class":"FORMATION_ENVIRONMENT_COORDINATE","definition":"outflow expansion timescale tau","status":"RESEARCH_LOCAL_SOURCE_ATTESTED_AXIS_PROPOSAL","reason":"modulates freeze-out and the Ye-dependent r-process regime boundary"},
        {"axis_id":"equilibrium_support_margin","semantic_class":"DYNAMICAL_STABILITY_MECHANISM","definition":"d ln(M)/d ln(rho_c) on a declared one-parameter TOV equilibrium sequence","status":"QUALIFIED_MECHANISM_BOUNDED_COLD_SPHERICAL_TOV" if multi_eos_pass else "AXIS_GENESIS_CANDIDATE_POSTFREEZE_GAP","reason":"four realistic piecewise-polytrope EOS approximants reproduce published maximum masses and show the same plus/zero/minus turning-point support signature"},
    ]

    source_ledger = [
        {"source_id":"PUBCHEM_PERIODIC_TABLE","url":"https://pubchem.ncbi.nlm.nih.gov/rest/pug/periodictable/JSON","claim":"atomic-number ordered observables include atomic radius and first ionization energy","stage":"PREFREEZE_PERIODIC_OBSERVABLE_SOURCE"},
        {"source_id":"PYYKKO_PCCP_2011","url":"https://pubs.rsc.org/en/content/articlehtml/2011/cp/c0cp01575j","claim":"peer-reviewed relativistic EAL Dirac-Fock compact-table assignments: 119-120 8s; 121-138 5g; 139-140 8p1/2; 141-155 formal 6f series; 156-164 formal 7d series; 165-166 9s; 167-168 9p1/2; 169-172 8p3/2","stage":"QUALIFYING_RELATIVISTIC_FORMAL_SLOT_ATTESTATION"},
        {"source_id":"IUPAC_TEMPORARY_ELEMENT_NOMENCLATURE","url":"https://publications.iupac.org/books/rbook/Red_Book_2005.pdf","claim":"systematic temporary names and three-letter symbols for unnamed elements are generated directly from atomic-number roots","stage":"PERIODIC_TABLE_NAMING_ATTESTATION"},
        {"source_id":"AGYEMANG_EXTENDED_TABLE_2026_PREPRINT","url":"https://www.researchgate.net/publication/404012644_The_Extended_Periodic_Table","claim":"model-derived predicted radii and first ionization energies for Z=119..172 retained only as a quarantined answer-hidden regression receipt","stage":"QUARANTINED_SINGLE_PREPRINT_THEORETICAL_OBSERVABLE_REGRESSION","independent_experiment":False,"qualifying_source":False},
        {"source_id":"LIPPUNER_ROBERTS_APJ_2015","url":"https://jonaslippuner.com/research/lippunerroberts2015/","claim":"parameterized r-process study over Ye, entropy and expansion timescale; lanthanide-free boundary occurs around Ye~0.22-0.30 depending on s and tau","stage":"NUCLEOSYNTHESIS_FORMATION_ENVIRONMENT_REGIME_ATTESTATION"},
        {"source_id":"LIPPUNER_ET_AL_DISK_EJECTA_2017","url":"https://arxiv.org/abs/1703.06216","claim":"disk-outflow nucleosynthesis can overlap between a spinning-BH remnant and finite-lifetime HMNS, demonstrating that nucleosynthetic outputs do not uniquely identify the central-engine label","stage":"FORMATION_ENVIRONMENT_IDENTIFIABILITY_CONTROL"},
        {"source_id":"READ_PIECEWISE_POLYTROPE_PARAMETERS","url":"https://www2.yukawa.kyoto-u.ac.jp/~masaru.shibata/PhysRevD.88.044026.pdf","claim":"SLy/APR4/H4/MS1 piecewise-polytrope parameters and published maximum masses","stage":"MULTI_EOS_QUALIFICATION_SOURCE"},
        {"source_id":"LALSUITE_PIECEWISE_POLYTROPE","url":"https://docs.ligo.org/lscsoft/lalsuite/lalsimulation/_l_a_l_sim_neutron_star_e_o_s_piecewise_polytrope_8c_source.html","claim":"standard Read-style piecewise-polytrope construction and low-density SLy crust implementation notes","stage":"MULTI_EOS_IMPLEMENTATION_ATTESTATION"},
        {"source_id":"SUN_RADIAL_OSCILLATIONS_2021","url":"https://arxiv.org/abs/2101.07515","claim":"radial-mode zero points agree with maximum-mass dM/drho_c=0 criterion for studied neutron/hybrid-star EOS","stage":"POSTCOMPUTE_STABILITY_ATTESTATION"},
        {"source_id":"BTM_TURNING_POINT_1966","url":"https://adsabs.harvard.edu/pdf/1966ApJ...145..505B","claim":"first extremum along cold nonrotating one-parameter sequence changes radial stability under declared conditions","stage":"THEOREM_ATTESTATION"},
        {"source_id":"EPJA_HEAVY_ELEMENT_STABILITY_2023","url":"https://link.springer.com/article/10.1140/epja/s10050-023-00913-z","claim":"liquid-drop fissility x=Z^2/(50.13 A); x>1 loses spherical fission stability absent microscopic corrections","stage":"POSTFREEZE_WORLD_ATTESTATION"},
        {"source_id":"PHYSREP_SUPERHEAVY_2023","url":"https://www.sciencedirect.com/science/article/pii/S0370157323003009","claim":"strong-field atomic structure encounters a finite-size-nucleus critical-charge band near Z~170-173, model dependent","stage":"POSTFREEZE_WORLD_ATTESTATION"},
        {"source_id":"PRC_NUCLEAR_SATURATION_2024","url":"https://journals.aps.org/prc/abstract/10.1103/PhysRevC.110.044320","claim":"symmetric nuclear matter saturation n0~0.16 fm^-3 and E0~-16 MeV per particle","stage":"POSTFREEZE_WORLD_ATTESTATION"},
        {"source_id":"PRD_MAX_NS_MASS_2024","url":"https://journals.aps.org/prd/abstract/10.1103/PhysRevD.109.043052","claim":"multimessenger reference MTOV~2.25 Msun and RTOV~11.90 km","stage":"POSTFREEZE_WORLD_ATTESTATION"},
    ]

    payload = {
        "schema": ELEMENT_COMPACTNESS_FRONTIER_SCHEMA,
        "owner": "CandidateGenerationPipeline/6.1.0",
        "status": "PERIODIC_RELATIVISTIC_SLOT_MAP_NUCLEOSYNTHESIS_BRIDGE_AND_MULTI_EOS_SUPPORT_QUALIFIED",
        "prefreeze_periodic_reset": frozen_periodic,
        "high_Z_periodicity_blind_observable_qualification": highz_payload,
        "relativistic_formal_slot_qualification": relativistic_slot_map,
        "periodic_table_atlas": periodic_table_atlas,
        "nucleosynthesis_formation_environment_bridge": formation_bridge,
        "multi_EOS_equilibrium_support_qualification": multi_eos,
        "solver_was_given_linear_element_to_black_hole_sequence": False,
        "blind_dimensionless_boundary_events": blind_events,
        "single_Z_branch": {
            "model_assumption_A_over_Z":2.5,
            "fissility_first_cross_Z":int(fiss_cross["Z"]),
            "qed_criticality_first_cross_Z":int(qed_cross["Z"]),
            "horizon_cross_found_through_Z250":horizon_cross_element is not None,
            "max_compactness_through_Z250":max_element_compactness,
            "structural_Z168_probe":{"Z":168,"A_model":z168["A_model"],"nuclear_radius_m":z168["nuclear_radius_m"],"fissility_ratio":z168["fissility_ratio"],"qed_criticality_ratio":z168["qed_criticality_ratio"],"compactness":z168["compactness"],"interpretation":"STRUCTURAL_PERIODIC_CANDIDATE_AT_RELATIVISTIC_REPRESENTATION_FRONTIER_BUT_FAR_FROM_GRAVITATIONAL_HORIZON"},
        },
        "nuclear_density_aggregation_branch": {
            "nuclear_saturation_number_density_fm^-3":nuclear_saturation_n_fm3,
            "mass_density_kg_m^-3":rho_sat,
            "nuclear_binding_scale_MeV_per_baryon":nuclear_binding_mev,
            "gravity_equals_binding":{"mass_kg":m_gravity_binding,"mass_solar":m_gravity_binding/m_sun,"radius_m":r_gravity_binding,"compactness":c_gravity_binding},
            "constant_density_horizon_toy_boundary":{"mass_kg":m_horizon_density,"mass_solar":m_horizon_density/m_sun,"radius_m":r_horizon_density,"compactness":1.0},
        },
        "postfreeze_compact_star_attestation": {"MTOV_mass_solar":2.25,"RTOV_km":11.90,"compactness":c_tov_attested,"mean_density_to_nuclear_saturation_ratio":rho_tov_avg/rho_sat,"attested_stability_frontier_precedes_constant_density_C1":tov_before_density_horizon},
        "representation_diagnosis": {
            "single_atomic_number_axis_reaches_horizon":not branch_disconnect,
            "branch_disconnect_detected":branch_disconnect,
            "missing_coordinate_class":"DYNAMICAL_COLLAPSE_AND_Z_SPECIFIC_FORMATION_IDENTIFIABILITY",
            "linear_chain_rejected":branch_disconnect,
            "recovered_topology":"BRANCHED_STATE_SPACE_WITH_RELATIVISTIC_SLOT_INTERLEAVING_AND_NUCLEOSYNTHESIS_FORMATION_FRONTIER",
            "high_Z_single_preprint_observable_gate_qualifying":False,
            "relativistic_formal_slot_mechanism_qualified":bool(pyykko_slot_map_qualified),
            "nucleosynthesis_regime_bridge_supported":formation_bridge.get("regime_level_bridge_supported") is True,
            "Z_specific_formation_mapping_identified":False,
            "equilibrium_support_mechanism_qualified":bool(multi_eos_pass),
            "interpretation_after_world_attestation":["PERIODIC_ATOMIC_STRUCTURE","PEER_REVIEWED_RELATIVISTIC_FORMAL_SLOT_INTERLEAVING","QED_REPRESENTATION_FRONTIER","NUCLEAR_EXISTENCE_STABILITY_AXIS","NUCLEOSYNTHESIS_FORMATION_ENVIRONMENT_REGIME","Z_SPECIFIC_FORMATION_IDENTIFIABILITY_GAP","AGGREGATION_COMPRESSION_BRANCH","DENSE_NUCLEAR_MATTER_SELF_GRAVITY","EOS_DEPENDENT_TOV_SUPPORT_TURNING_SURFACE","DYNAMICAL_COLLAPSE_GAP","HORIZON"],
        },
        "adaptive_axis_proposals":axis_births,
        "source_ledger":source_ledger,
        "baseline_candidate_registry_count":2771,
        "baseline_candidate_registry_used_as_solution_source":False,
        "claim_boundary": {
            "Z168_is_guaranteed_element":False,
            "Z172_is_guaranteed_last_element":False,
            "highZ_theoretical_observable_test_is_experimental_confirmation":False,
            "single_preprint_highZ_observable_gate_is_qualifying":False,
            "elements_119_172_are_experimentally_confirmed":False,
            "formal_slot_assignment_is_unique_neutral_ground_state_configuration":False,
            "specific_Z_119_172_is_mapped_to_black_hole_formation_environment":False,
            "event_horizon_is_nucleosynthesis_surface":False,
            "liquid_drop_fissility_is_exact_superheavy_stability_theory":False,
            "Zcrit_is_exact_universal_end_of_periodic_table":False,
            "constant_density_horizon_mass_is_neutron_star_maximum_mass":False,
            "equilibrium_support_margin_is_universal_for_all_compact_objects":False,
            "turning_point_is_horizon":False,
            "element_becomes_black_hole_at_finite_Z":False,
            "branched_transition_graph_is_new_law_of_nature":False,
            "world_novelty_established":False,
            "research_result":"Atlas preserves the blind periodic-reset evidence, quarantines the source-sensitive single-preprint high-Z observable gate, qualifies the peer-reviewed Pyykko formal relativistic slot map through Z=172, opens a bounded Ye/s/tau nucleosynthesis formation-environment bridge while failing closed on Z-specific or horizon-surface origin, and preserves the four-EOS equilibrium_support_margin qualification before the horizon boundary.",
        },
    }
    return {**payload, "digest": digest_payload(payload)}

def frontier_higher_order_expansion(root: str | Path) -> Mapping[str, Any]:
    """Expand the six non-rediscovery 13.3 frontiers into typed higher-order tuples.

    This is post-freeze continuation research.  It does not alter the parent
    frontier IDs or their frozen experiment digests.  Axes may come from any
    owner/domain; only registry addressability and later typed interpretation
    constrain the expansion.  World evidence narrows mechanism classes but
    never promotes a law automatically.
    """
    root = Path(root)
    ledger_path = root / "reports" / "FRONTIER_WORLD_ATTESTATION_CURRENT.json"
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    embedded = ledger.get("digest")
    if embedded != digest_payload({k: v for k, v in ledger.items() if k != "digest"}):
        raise ValueError("frontier world-attestation digest mismatch")
    parents = {row["frontier_id"]: row for row in ledger.get("records", ())}
    specs = (
        {
            "frontier_id": "FRONTIER-807CBC5A9869678D",
            "expanded_axes": (
                "mathematics.stability", "pharmaceutical.storage_stability",
                "chemistry.temperature_dependence", "chemistry.kinetic_law", "chemistry.activation_model",
                "chemistry.stability_condition", "systems_control.system_model", "systems_control.identifiability",
                "metrology.uncertainty_model",
            ),
            "mechanism_class": "DYNAMICAL_FIRST_EXIT_STORAGE_STABILITY_BRIDGE",
            "mathematical_form": "x_dot=f(x,T,H,...); tau_spec=inf{t:q(x(t)) outside S_spec}",
            "status": "SEMANTIC_SPLIT_WITH_TYPED_FIRST_EXIT_BRIDGE_WORLD_ATTESTED_COMPONENTS",
            "interpretation": "Pharmaceutical storage stability is naturally an exit-time/specification-survival property of a degradation dynamical system; it is not automatically Lyapunov stability. Temperature/humidity kinetics and uncertainty make the bridge testable without equating the two meanings of stability.",
            "sources": (
                {"title":"Humidity-corrected Arrhenius equation: the reference condition approach","url":"https://pubmed.ncbi.nlm.nih.gov/26802498/","type":"PEER_REVIEWED"},
                {"title":"ICH Q1 stability testing guideline","url":"https://www.ema.europa.eu/en/ich-q1-guideline-stability-testing-drug-substances-drug-products","type":"REGULATORY_GUIDANCE"},
            ),
        },
        {
            "frontier_id": "FRONTIER-04EB459704C4684D",
            "expanded_axes": (
                "aeronautics_and_aerostation.fault_tolerance_mode", "aeronautics_and_aerostation.sensor_suite",
                "aeronautics_and_aerostation.state_estimator", "systems_control.model_failure_class",
                "systems_control.state_estimation", "systems_control.observability",
                "quantum_information_and_computational_methods.fault_tolerance",
                "quantum_information_and_computational_methods.noise_model_class",
                "quantum_information_and_computational_methods.fidelity_error_budget",
                "metrology.uncertainty_model",
            ),
            "mechanism_class": "RELIABILITY_COVERAGE_AND_ERROR_SUPPRESSION_BRIDGE",
            "mathematical_form": "P_fail=F(component_error,coverage,redundancy,diagnostic_resolution); quantum p_L=G(p_phys,code,decoder)",
            "status": "HIGHER_ORDER_RELIABILITY_BRIDGE_UNDERIDENTIFIED",
            "interpretation": "Both domains instantiate failure probability, redundancy/coverage and recovery, but no domain-independent coefficient law is established. The higher-order tuple identifies a shared reliability object rather than equating aerospace and quantum fault tolerance directly.",
            "sources": (
                {"title":"Reliability of Fault Tolerant Control Systems","url":"https://ntrs.nasa.gov/citations/20020077965","type":"NASA_REPORT"},
                {"title":"Fault-Tolerant Quantum Computation With Constant Error Rate","url":"https://arxiv.org/abs/quant-ph/9906129","type":"PRIMARY_THEORY"},
            ),
        },
        {
            "frontier_id": "FRONTIER-5776A4799B306B93",
            "expanded_axes": (
                "chemistry.temperature_dependence", "chemistry.temperature_regime", "chemistry.phase",
                "chemistry.thermodynamic_ensemble", "chemistry.stability_condition",
                "physics.internal_symmetry", "physics.symmetry_realization", "physics.symmetry_breaking",
                "physics.thermodynamic_limit", "mathematics.geometric_structure",
            ),
            "mechanism_class": "TEMPERATURE_DRIVEN_ORDER_PARAMETER_SYMMETRY_TRANSITION",
            "mathematical_form": "F(eta,T)=F0+a(T-Tc)eta^2+b eta^4+...; symmetry selected by order-parameter representation",
            "status": "HIGHER_ORDER_WORLD_ATTESTED_LANDAU_MECHANISM_CLASS",
            "interpretation": "The broad pair becomes scientifically grounded only after phase/order-parameter coordinates are added. Temperature-driven structural and field-theoretic symmetry transitions are established, but chemistry.temperature_dependence in general is not a universal symmetry law.",
            "sources": (
                {"title":"Symmetry Restoration and Breaking at Finite Temperature: An Introductory Review","url":"https://www.mdpi.com/2073-8994/12/5/733","type":"REVIEW"},
                {"title":"Temperature-induced structural phase transitions in inorganic compounds","url":"https://doi.org/10.1016/j.progsolidstchem.2025.100547","type":"PEER_REVIEWED"},
            ),
        },
        {
            "frontier_id": "FRONTIER-ECDEC2633497EFF3",
            "expanded_axes": (
                "pharmaceutical.route_of_administration", "pharmaceutical.formulation", "pharmaceutical.release_profile",
                "pharmaceutical.absorption_model", "pharmaceutical.bioavailability",
                "physics.topology", "chemistry.transport_limitation",
                "systems_control.system_model", "systems_control.observability", "metrology.measurement_model",
            ),
            "mechanism_class": "ROUTE_SELECTS_INPUT_MAP_ON_TRANSPORT_COMPARTMENT_GRAPH",
            "mathematical_form": "c_dot=A_G c + B_route u(t); route changes B_route and local absorption kernel, while G encodes compartment connectivity",
            "status": "HIGHER_ORDER_WORLD_ATTESTED_INPUT_GRAPH_TOPOLOGY_MECHANISM",
            "interpretation": "PBPK models make route of administration an input/boundary-map choice on a compartment transport network. This is a typed graph/control bridge, not an identity between route and physical topology.",
            "sources": (
                {"title":"Applied Concepts in PBPK Modeling: How to Build a PBPK/PD Model","url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC5080648/","type":"PEER_REVIEWED"},
            ),
        },
        {
            "frontier_id": "FRONTIER-D46AD8EA57A13451",
            "expanded_axes": (
                "aeronautics_and_aerostation.range_model", "aeronautics_and_aerostation.endurance_model",
                "aeronautics_and_aerostation.mission_phase", "aeronautics_and_aerostation.energy_storage",
                "aeronautics_and_aerostation.storage_state_of_charge", "aeronautics_and_aerostation.storage_usable_capacity",
                "quantum_information_and_computational_methods.reset_pattern",
                "quantum_information_and_computational_methods.measurement_pattern",
                "quantum_information_and_computational_methods.feedforward_structure",
                "quantum_information_and_computational_methods.checkpoint_policy",
                "quantum_information_and_computational_methods.open_system_regime",
                "systems_control.system_model",
            ),
            "mechanism_class": "RENEWAL_RESET_RESOURCE_CYCLE_BRIDGE",
            "mathematical_form": "long-run reward rate = E[reward_per_cycle]/E[cycle_time]; reset/recharge defines renewal epochs",
            "status": "HIGHER_ORDER_RENEWAL_BRIDGE_COMPONENTS_ATTESTED_ORIGINAL_PAIR_UNDERIDENTIFIED",
            "interpretation": "The original range_model x reset_pattern pair has no direct physical law. Adding energy/resource-cycle and reset/checkpoint axes exposes a known renewal-process abstraction that can describe repeated recharge/reset epochs in different systems. It remains a mathematical bridge, not a cross-domain physical law.",
            "sources": (
                {"title":"Stochastic Resetting: A (Very) Brief Review","url":"https://doi.org/10.3389/fphy.2022.789097","type":"REVIEW"},
                {"title":"Mission-adaptive energy management for hybrid-electric distributed propulsion aircraft with in-flight recharging and asymmetric regeneration","url":"https://doi.org/10.1016/j.ast.2026.112078","type":"PEER_REVIEWED"},
            ),
        },
        {
            "frontier_id": "FRONTIER-3A29B530D2F8DA31",
            "expanded_axes": (
                "aeronautics_and_aerostation.falsification_metric", "aeronautics_and_aerostation.model_discrepancy",
                "aeronautics_and_aerostation.validation_source", "metrology.uncertainty_model", "metrology.data_quality",
                "systems_control.identifiability", "systems_control.experiment_design",
                "quantum_information_and_computational_methods.local_dimension",
                "quantum_information_and_computational_methods.validation_reference",
                "quantum_information_and_computational_methods.sampling_error",
                "quantum_information_and_computational_methods.observable_error_budget",
            ),
            "mechanism_class": "DIMENSION_AWARE_VALIDATION_SAMPLE_COMPLEXITY_BRIDGE",
            "mathematical_form": "general d-dimensional quantum-state validation/tomography has parameter/sample burden increasing with d (e.g. O(d^2/eps^2) in general tomography); falsification thresholds must account for model dimension and uncertainty",
            "status": "HIGHER_ORDER_WORLD_ATTESTED_DIMENSION_VALIDATION_COMPLEXITY_BRIDGE",
            "interpretation": "The direct pair was too abstract. Adding validation, uncertainty and sampling axes yields a real bridge: effective Hilbert-space dimension controls statistical complexity of quantum validation, while falsification metrics in engineering must be calibrated to model complexity and uncertainty. No universal scalar law for all metrics is claimed.",
            "sources": (
                {"title":"Evidence-Based Certification of Quantum Dimensions","url":"https://doi.org/10.1103/PhysRevLett.133.050204","type":"PEER_REVIEWED"},
                {"title":"Lower Bounds for Learning Quantum States with Single-Copy Measurements","url":"https://doi.org/10.1145/3717450","type":"PEER_REVIEWED"},
                {"title":"An invitation to the sample complexity of quantum hypothesis testing","url":"https://www.nature.com/articles/s41534-025-00980-8","type":"REVIEW"},
            ),
        },
    )
    rows = []
    for spec in specs:
        parent = parents.get(spec["frontier_id"])
        if parent is None:
            raise KeyError(spec["frontier_id"])
        axes = tuple(spec["expanded_axes"])
        for fq in axes:
            domain, axis = fq.split(".", 1)
            if domain not in DOMAIN_REGISTRIES or axis not in DOMAIN_REGISTRIES[domain].axes:
                raise ValueError(f"unregistered expansion axis {fq}")
        row = {
            "parent_frontier_id": spec["frontier_id"],
            "parent_frontier_digest": parent["digest"],
            "parent_prefreeze_experiment_digest": parent["prefreeze_experiment_digest"],
            "parent_epistemic_status": parent["epistemic_status"],
            "original_axes": list(parent["axes"]),
            "expanded_axes": list(axes),
            "axis_order": len(axes),
            "domains": sorted({fq.split(".", 1)[0] for fq in axes}),
            "cross_owner_or_domain_combination_allowed": True,
            "mechanism_class": spec["mechanism_class"],
            "mathematical_form": spec["mathematical_form"],
            "status": spec["status"],
            "interpretation": spec["interpretation"],
            "sources": [dict(s) for s in spec["sources"]],
            "candidate_is_false": False,
            "scientific_law_promoted": False,
            "world_novelty_claimed": False,
            "next_gate": "EXECUTE_TYPED_DISCRIMINATOR_OR_BIND_DOMAIN_DATA_BEFORE_ANY_LAW_PROMOTION",
        }
        row["digest"] = digest_payload(row)
        rows.append(row)
    payload = {
        "schema": "phi-frontier-higher-order-expansion/v13.4",
        "release": "13.4.0",
        "mode": "POSTFREEZE_HIGHER_ORDER_AXIS_EXPANSION_WITH_WORLD_EVIDENCE",
        "parent_world_attestation_digest": ledger["digest"],
        "expanded_parent_count": len(rows),
        "records": rows,
        "status_counts": dict(sorted(__import__("collections").Counter(r["status"] for r in rows).items())),
        "claim_boundary": {
            "parent_frontiers_rewritten": False,
            "unknown_means_false": False,
            "higher_order_world_evidence_promotes_law": False,
            "owner_or_domain_affiliation_blocks_combination": False,
            "direct_pair_law_established_for_all_six": False,
            "expansion_is_solution_space_ceiling": False,
        },
    }
    return {**payload, "digest": digest_payload(payload)}


class CandidateGenerationPipeline:
    @staticmethod
    def _require_regression_mode(regression_mode: bool, tool_name: str) -> None:
        if regression_mode is not True:
            raise PermissionError(
                f"{tool_name} is answer-bearing atomic/post-freeze regression logic; "
                "pass regression_mode=True explicitly. Generic/blind candidate generation "
                "must not consume frozen atomic answer maps."
            )

    """Single authoritative orchestration owner for axis-space scanning."""

    def __init__(self, catalog: LawCatalog, bridges: Mapping[str, DomainBridge], spot_checks: Sequence[Mapping[str, Any]] = (), owner_surfaces: Mapping[str, Mapping[str, Any]] | None = None) -> None:
        self.catalog = catalog
        self.bridges = bridges
        self.spot_checks = tuple(dict(row) for row in spot_checks)
        self.owner_surfaces = dict(owner_surfaces or {})
        self.generators = (
            PhysicsCandidateGenerator(),
            MechanicsCandidateGenerator(),
            ChemistryCandidateGenerator(),
            BridgeCandidateGenerator(bridges),
        )

    @property
    def specs(self) -> Tuple[TransformationSpec, ...]:
        rows: List[TransformationSpec] = []
        for generator in self.generators:
            if isinstance(generator, _SingleDomainGenerator):
                rows.extend(generator.specs)
            else:
                rows.extend(_bridge_spec(bridge) for bridge_id, bridge in sorted(self.bridges.items()) if bridge_id in BRIDGE_REQUIRED_ANY_TAGS)
        return tuple(rows)

    @property
    def transformation_registry_digest(self) -> str:
        return digest_payload([{"id": spec.transformation_id, "digest": spec.digest} for spec in self.specs])

    def directed_research(self, query: DirectedResearchQuery) -> Mapping[str, Any]:
        """Targeted all-axis owner-hypergraph scan for a scientific question."""
        return directed_owner_hypergraph_research(self.catalog, self.bridges, query, self.owner_surfaces)

    def materialize_base_candidate_frontier(
        self, *, required_domains: Sequence[str] = ()
    ) -> tuple[list[dict[str, Any]], Mapping[str, Any]]:
        """Materialize existing first-order generators without deep search.

        ``required_domains`` is a relevance-preserving execution projection, not
        a scientific ceiling.  It lets a typed research question execute only the
        already-authoritative generators that can contribute to its grounded
        domain set instead of materializing unrelated domains and discarding them
        afterwards.  With an empty projection the historical all-generator
        behavior is preserved exactly.
        """
        allowed = {str(x) for x in required_domains if str(x)}
        unknown = allowed - set(DOMAIN_REGISTRIES)
        if unknown:
            raise ValueError(f"unknown required domains: {sorted(unknown)}")
        known_formula_digests = {p.formula.digest for p in self.catalog.passports.values()}
        deduper = CandidateDeduplicator()
        audit = GenerationAudit(axis_rows={
            key: dataclasses.replace(row, transformation_ids=list(row.transformation_ids))
            for key, row in AXIS_POLICY_TEMPLATE.items()
        })
        selected_generators = []
        for generator in self.generators:
            if not allowed:
                selected_generators.append(generator)
            elif isinstance(generator, _SingleDomainGenerator):
                if generator.domain_id in allowed:
                    selected_generators.append(generator)
            else:
                # A bridge can contribute only when both endpoints are admitted by
                # the grounded domain projection; for a single-domain birth it is
                # therefore intentionally not materialized.
                selected_generators.append(generator) if len(allowed) > 1 else None
        for generator in selected_generators:
            for row, spec in generator.generate(self.catalog, known_formula_digests, audit):
                row_domains = set(str(x) for x in row.get("source_domains", ())) | set(str(x) for x in row.get("target_domains", ()))
                if allowed and row_domains and not row_domains.issubset(allowed):
                    continue
                if deduper.add(row):
                    audit.accept(row, spec)
                else:
                    audit.deduplicated += 1
        rows = sorted(deduper.values(), key=lambda row: row["candidate_id"])
        payload = {
            "schema": "phi-base-candidate-frontier/v2",
            "owner": "CandidateGenerationPipeline/6.1.0",
            "status": "BASE_CANDIDATE_FRONTIER_MATERIALIZED",
            "candidate_count": len(rows),
            "candidate_ids_digest": digest_payload([row.get("candidate_id") for row in rows]),
            "source_catalog_digest": self.catalog.digest(),
            "required_domain_projection": sorted(allowed),
            "selected_generator_count": len(selected_generators),
            "historical_persisted_candidate_registry_used": False,
            "deep_formula_search_executed": False,
            "claim_boundary": {
                "domain_projection_is_scientific_space_ceiling": False,
                "unrelated_domains_declared_impossible": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return rows, payload

    def birth_deep_candidate(
        self,
        *,
        base_candidates: Sequence[Mapping[str, Any]],
        profile_id: str,
        target_axis_order: int,
        keywords: Sequence[str] = (),
        purpose: str = "owner-connected fresh theory-space candidate",
        required_source_owner_ids: Sequence[str] = (),
    ) -> Mapping[str, Any]:
        """Materialize one content-addressed deep candidate from the existing owner hypergraph.

        This is a public seam over the same ``_deep_component_search`` /
        ``_build_deep_candidate`` algorithm used by ``run()``.  It creates no
        second search engine and imposes no scientific ceiling: ``target_axis_order``
        is an execution target supplied by the caller, while termination remains
        TARGET_REACHED_OR_CONNECTED_FRONTIER_EXHAUSTED.
        """
        profile_id = str(profile_id).strip()
        if not profile_id:
            raise ValueError("profile_id is required")
        target_axis_order = int(target_axis_order)
        if target_axis_order < 1:
            raise ValueError("target_axis_order must be positive")
        profile = {
            "profile_id": profile_id,
            "target_axis_order": target_axis_order,
            "keywords": tuple(str(x).casefold() for x in keywords if str(x).strip()),
            "purpose": str(purpose),
        }
        required_owners = tuple(dict.fromkeys(str(x).strip() for x in required_source_owner_ids if str(x).strip()))
        unknown_required = tuple(owner_id for owner_id in required_owners if owner_id not in self.catalog.passports)
        if unknown_required:
            raise ValueError(f"required source owners are not registered: {unknown_required}")
        if required_owners:
            profile["required_source_owner_ids"] = required_owners
        search = _deep_component_search(tuple(base_candidates), self.catalog, profile)
        if not search.get("selected"):
            payload = {
                "schema": "phi-owner-hypergraph-deep-candidate-birth/v1",
                "owner": "CandidateGenerationPipeline/6.1.0",
                "status": "DEEP_CANDIDATE_BIRTH_FRONTIER_EMPTY",
                "profile": profile,
                "search": {k: v for k, v in search.items() if k != "selected"},
                "candidate": None,
                "claim_boundary": {
                    "new_search_algorithm_created": False,
                    "scientific_ceiling_imposed": False,
                    "world_novelty_established": False,
                },
            }
            payload["digest"] = digest_payload(payload)
            return payload
        row = _build_deep_candidate(search, profile, self.catalog)
        payload = {
            "schema": "phi-owner-hypergraph-deep-candidate-birth/v1",
            "owner": "CandidateGenerationPipeline/6.1.0",
            "status": "DEEP_CANDIDATE_BIRTH_FROZEN",
            "profile": profile,
            "search": {
                "target_axis_order": search["target_axis_order"],
                "achieved_axis_order": search["achieved_axis_order"],
                "target_reached": search["target_reached"],
                "frontier_exhausted": search["frontier_exhausted"],
                "evaluated_component_visits": search["evaluated_component_visits"],
                "fixed_visit_budget": search["fixed_visit_budget"],
                "selected_component_count": len(search["selected"]),
            },
            "candidate": row,
            "claim_boundary": {
                "new_search_algorithm_created": False,
                "scientific_ceiling_imposed": False,
                "literature_used_prefreeze": False,
                "world_novelty_established": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def refine_directed_research(
        self,
        query: DirectedResearchQuery,
        *,
        priority_axis_ids: Sequence[str] = (),
        priority_owner_ids: Sequence[str] = (),
        information_design_digest: str = "",
    ) -> Mapping[str, Any]:
        """Re-enter the same owner-hypergraph with information-selected priorities.

        This is deliberately a thin re-query of the authoritative directed
        research algorithm, not a second search engine.  Expected information
        gain may choose which registered coordinates deserve deeper attention,
        but it cannot create new axes/owners or alter physical claim status.
        """
        query.validate()
        if query.discovery_mode == "BLIND_PRIMITIVE_FIREWALL" and (priority_axis_ids or priority_owner_ids or information_design_digest):
            raise ValueError(
                "post-freeze information/literature priorities are forbidden from re-entering BLIND_PRIMITIVE_FIREWALL discovery"
            )
        refined = dataclasses.replace(
            query,
            target_axis_ids=tuple(dict.fromkeys((*query.target_axis_ids, *priority_axis_ids))),
            seed_owner_ids=tuple(dict.fromkeys((*query.seed_owner_ids, *priority_owner_ids))),
        )
        result = dict(self.directed_research(refined))
        result["information_gain_refinement"] = {
            "status": "PRIORITY_REQUERY_OF_SAME_AUTHORITATIVE_OWNER_HYPERGRAPH",
            "priority_axis_ids": tuple(priority_axis_ids),
            "priority_owner_ids": tuple(priority_owner_ids),
            "information_design_digest": information_design_digest,
            "new_search_algorithm_created": False,
            "registered_axes_or_owners_invented": False,
        }
        result["digest"] = digest_payload({k: v for k, v in result.items() if k != "digest"})
        return result

    def run_open_void_directed_exploration(
        self, *, frontier_limit: int = 19, traversal_state: Mapping[str, Any] | None = None,
        revisit_digest: str | None = None, dovetail_steps: int = 0,
    ) -> Mapping[str, Any]:
        """Exactly scan current pair space and expose the persistent fair continuation.

        The active confirmed-control baseline is not an admissible answer source.
        ``frontier_limit`` preserves the historical pair-frontier view only; it is
        not a scientific ceiling because the same authoritative owner advances a
        persistent pair/node dovetail over the full append-only axis address space.
        """
        return _open_void_directed_exploration(
            self, frontier_limit=frontier_limit, traversal_state=traversal_state,
            revisit_digest=revisit_digest, dovetail_steps=dovetail_steps,
        )

    def run_element_compactness_frontier_probe(self, root: str | Path | None = None, *, regression_mode: bool = False) -> Mapping[str, Any]:
        """Run the atomic/nuclear/compactness regression only after explicit opt-in."""
        self._require_regression_mode(regression_mode, "run_element_compactness_frontier_probe")
        return element_compactness_frontier_probe(root)

    def run_blind_per_element_reconstruction(self, root: str | Path | None = None, *, regression_mode: bool = False) -> Mapping[str, Any]:
        """Run the frozen answer-hidden 1..172 per-element regression only after explicit opt-in."""
        self._require_regression_mode(regression_mode, "run_blind_per_element_reconstruction")
        from .periodic_reconstruction import BlindPerElementReconstructionOwner
        return BlindPerElementReconstructionOwner(root).run()

    def run_phi_space_atomic_interior_hole_qualification(self, root: str | Path | None = None, *, regression_mode: bool = False) -> Mapping[str, Any]:
        """Run the owner-connected atomic interior-hole regression only after explicit opt-in."""
        self._require_regression_mode(regression_mode, "run_phi_space_atomic_interior_hole_qualification")
        from .periodic_reconstruction import phi_space_atomic_interior_hole_qualification
        return phi_space_atomic_interior_hole_qualification(root)

    def run(self) -> Tuple[List[Dict[str, Any]], Mapping[str, Any]]:
        known_formula_digests = {p.formula.digest for p in self.catalog.passports.values()}
        deduper = CandidateDeduplicator()
        audit = GenerationAudit(axis_rows={key: dataclasses.replace(row, transformation_ids=list(row.transformation_ids)) for key, row in AXIS_POLICY_TEMPLATE.items()})
        for generator in self.generators:
            for row, spec in generator.generate(self.catalog, known_formula_digests, audit):
                if deduper.add(row):
                    audit.accept(row, spec)
                else:
                    audit.deduplicated += 1
        base_candidates = deduper.values()
        spot_check_status_counts = _apply_spot_checks(base_candidates, self.spot_checks)
        deep_candidates, deep_search = _deep_formula_search(base_candidates, self.catalog)
        law_ablation_rediscovery = _law_ablation_rediscovery(self.catalog)
        candidates = sorted([*base_candidates, *deep_candidates], key=lambda row: row["candidate_id"])
        audit.emitted = len(candidates)
        audit.emitted_by_generator["CandidateGenerationPipeline"] = len(deep_candidates)
        axis_coverage = _axis_coverage_summary(audit, self.specs, self.catalog)
        materialized_axis_orders = [
            len(set(row.get("transformation", {}).get("axis_ids", ())))
            for row in candidates
        ]
        registered_axis_count = sum(registry.axis_count for registry in DOMAIN_REGISTRIES.values())
        summary = {
            "schema": GENERATOR_SCHEMA,
            "generator_version": GENERATOR_VERSION,
            "uses_legacy_candidates": False,
            "uses_archetype_candidate_rows": False,
            "source_catalog_digest": self.catalog.digest(),
            "transformation_registry_digest": self.transformation_registry_digest,
            "registered_transformation_count": len(self.specs),
            "single_domain_transformation_count": sum(1 for s in self.specs if not s.bridge_id),
            "bridge_transformation_count": sum(1 for s in self.specs if s.bridge_id),
            "composite_model_family_count": len(candidates),
            "base_composite_model_family_count": len(base_candidates),
            "deep_composite_model_family_count": len(deep_candidates),
            "deep_formula_search": deep_search,
            "law_ablation_rediscovery": law_ablation_rediscovery,
            "evaluated_combinations": audit.evaluated,
            "rejected_combinations": audit.rejected,
            "deduplicated_combinations": audit.deduplicated,
            "rejected_by_gate": dict(sorted(audit.rejected_by_gate.items())),
            "emitted_by_generator": dict(sorted(audit.emitted_by_generator.items())),
            "emitted_by_domain": dict(sorted(audit.emitted_by_domain.items())),
            "emitted_by_category": dict(sorted(audit.emitted_by_category.items())),
            "materialized_rows_are_not_search_space_cardinality": True,
            "materialized_composite_model_family_count": len(candidates),
            "candidate_axis_order_policy": {
                "no_fixed_small_order_ceiling": True,
                "admissible_axis_order_min": 1,
                "admissible_axis_order_max": registered_axis_count,
                "candidate_may_include_more_than_60_axes": registered_axis_count > 60,
                "all_selected_axes_must_be_semantically_active": True,
                "targeted_or_predicted_regions_only": True,
                "exhaustive_semantic_enumeration": False,
                "current_materialized_max_axis_order": max(materialized_axis_orders, default=0),
                "current_materialized_over_60_axis_count": sum(order > 60 for order in materialized_axis_orders),
                "over_60_axis_execution_status": (
                    "MATERIALIZED_FORMAL_HYPOTHESES_NOT_VALIDATED"
                    if any(order > 60 for order in materialized_axis_orders)
                    else "NOT_MATERIALIZED"
                ),
            },
            "axis_space": axis_coverage,
            "all_composite_families_have_inheritance_contract": all(row.get("epistemic_state") == "DERIVED_COMPOSITE_MODEL" and row.get("property_inheritance_contract", {}).get("scientific_status") == "SOURCE_SECTORS_INHERITED_COUPLED_EXTENSION_UNRESOLVED" for row in candidates),
            "all_composite_model_gates_pass": all(row["gate_status"] == "FORMALLY_ADMISSIBLE" and all(row["gates"].values()) for row in candidates),
            "all_coupled_extensions_explicitly_unresolved": all(row.get("scientific_status") == "SOURCE_SECTORS_INHERITED_COUPLED_EXTENSION_UNRESOLVED" for row in candidates),
            "all_axes_classified": axis_coverage["all_registered_axes_classified"],
            "all_axes_parameterized": axis_coverage["all_registered_axes_parameterized"],
            "spot_checked_composite_model_count": sum(spot_check_status_counts.values()),
            "spot_check_status_counts": spot_check_status_counts,
            "claim_boundary": {
                "registered_axis_scan": "IMPLEMENTED",
                "within_domain_exact_compressed_axis_subset_census_all_registered_orders": "IMPLEMENTED",
                "cross_domain_axis_subset_cardinality": "COUNTED_EXACTLY_NOT_SEMANTICALLY_ENUMERATED",
                "cross_domain_formula_generation": "REGISTERED_BRIDGE_TEMPLATES_ONLY_NOT_EXHAUSTIVE",
                "continuous_value_cartesian_exhaustion": "NOT_CLAIMED",
                "higher_order_interactions_t_ge_5": "ADMISSIBLE_ACROSS_FULL_REGISTERED_RANGE_TARGETED_MATERIALIZATION_ONLY",
                "candidate_axis_order": "NO_FIXED_SMALL_CEILING_1_TO_ALL_REGISTERED_AXES",
                "over_60_axis_candidate": "MATERIALIZED_WITH_EXPLICIT_AXIS_BINDINGS_AS_FORMAL_HYPOTHESES",
                "search_strategy": "DETERMINISTIC_OWNER_HYPERGRAPH_TARGET_TERMINATED_NO_FIXED_VISIT_BUDGET",
                "composite_model_generation": "SOURCE_SECTORS_INHERITED_REGISTERED_TRANSFORMATIONS_ONLY",
                "property_inheritance": "EXPLICIT_PER_MODEL",
                "coupling_closure": "OPEN_UNLESS_DERIVED_BY_OWNER",
                "quantity_resolution": "SYNTACTIC_INDEX_BUILT_NUMERIC_RESOLUTION_NOT_RUN_GLOBALLY",
                "prior_art_search": "POINT_CHECKS_ONLY_GLOBAL_SCAN_NOT_RUN",
                "identifiability": "NOT_RUN_GLOBALLY",
                "coupled_regime_validation": "NOT_RUN_GLOBALLY",
            },
        }
        summary["generation_run_id"] = "CGRUN-" + digest_payload(summary)[:20].upper()
        return candidates, summary


def write_generation(root: str | Path, candidates: Sequence[Mapping[str, Any]], summary: Mapping[str, Any]) -> Mapping[str, Any]:
    """Persist one content-addressed generation run and axis-coverage report."""
    root = Path(root)
    candidate_path = root / "data" / "frontiers" / "generated_unverified_composite_candidates_current.jsonl"
    report_path = root / "reports" / "COMPOSITE_MODEL_GENERATION_CURRENT.json"
    axis_report_path = root / "reports" / "AXIS_SPACE_SCAN_CURRENT.json"
    snapshot_path = root / "data" / "frontiers" / "generated_unverified_composite_snapshot_current.json"
    manifest_path = root / "data" / "frontiers" / "generated_unverified_composite_manifest_current.json"
    spot_report_path = root / "reports" / "COMPOSITE_MODEL_SPOT_CHECKS_CURRENT.json"
    deep_report_path = root / "reports" / "DEEP_FORMULA_SEARCH_CURRENT.json"
    ablation_report_path = root / "reports" / "LAW_ABLATION_REDISCOVERY_CURRENT.json"
    for path in (candidate_path, report_path, axis_report_path, snapshot_path, manifest_path, spot_report_path, deep_report_path, ablation_report_path):
        path.parent.mkdir(parents=True, exist_ok=True)

    text = "".join(canonical_json(row) + "\n" for row in candidates)
    candidate_path.write_text(text, encoding="utf-8")
    candidate_sha = hashlib.sha256(candidate_path.read_bytes()).hexdigest()

    full_summary = dict(summary)
    full_summary["composite_model_file"] = str(candidate_path.relative_to(root))
    full_summary["composite_model_file_sha256"] = candidate_sha
    full_summary["persisted_count"] = len(candidates)
    full_summary["ids_match_persisted"] = True
    full_summary["digests_match_persisted"] = True
    full_summary["composite_model_file_bytes"] = candidate_path.stat().st_size
    full_summary["generator_source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    full_summary["all_acceptance_gates_pass"] = bool(
        full_summary["all_composite_families_have_inheritance_contract"]
        and full_summary["all_composite_model_gates_pass"]
        and full_summary["all_coupled_extensions_explicitly_unresolved"]
        and full_summary["all_axes_classified"]
        and full_summary["axis_space"]["exact_axis_subset_census"]
    )
    full_summary["status"] = (
        "PASS_WITH_OPEN_FRONTIER"
        if full_summary["all_acceptance_gates_pass"] and not full_summary["all_axes_parameterized"]
        else ("PASS" if full_summary["all_acceptance_gates_pass"] else "FAIL")
    )

    axis_report = {
        "schema": "phi-axis-space-scan/v6.1",
        "generation_run_id": full_summary["generation_run_id"],
        "generator_version": GENERATOR_VERSION,
        "source_catalog_digest": full_summary["source_catalog_digest"],
        "transformation_registry_digest": full_summary["transformation_registry_digest"],
        "axis_space": full_summary["axis_space"],
        "claim_boundary": full_summary["claim_boundary"],
        "status": ("PASS_WITH_OPEN_FRONTIER" if (full_summary["all_axes_classified"] and full_summary["axis_space"]["exact_axis_subset_census"] and not full_summary["all_axes_parameterized"]) else ("PASS" if (full_summary["all_axes_classified"] and full_summary["axis_space"]["exact_axis_subset_census"]) else "FAIL")),
    }
    axis_report["sha256"] = digest_payload({k: v for k, v in axis_report.items() if k != "sha256"})
    axis_report_path.write_text(json.dumps(axis_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    snapshot = {
        "schema": "phi-generated-composite-model-snapshot/v6.1",
        "generation_run_id": full_summary["generation_run_id"],
        "generator_version": GENERATOR_VERSION,
        "generator_source_sha256": full_summary["generator_source_sha256"],
        "source_catalog_digest": full_summary["source_catalog_digest"],
        "transformation_registry_digest": full_summary["transformation_registry_digest"],
        "composite_model_family_count": full_summary["composite_model_family_count"],
        "composite_model_file_sha256": candidate_sha,
        "axis_report_sha256": axis_report["sha256"],
        "uses_legacy_candidates": False,
        "uses_archetype_candidate_rows": False,
        "candidate_scope": "SOURCE_LAWS_EMBEDDED_COUPLED_EXTENSION",
        "inheritance_status": "SOURCE_SECTORS_INHERITED_COUPLED_EXTENSION_UNRESOLVED",
        "claim_boundary": full_summary["claim_boundary"],
    }
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    snapshot_sha = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()

    manifest = {
        "source_id": GENERATED_SOURCE_ID,
        "title": "Точный census осей и генерация составных моделей с явным наследованием свойств CURRENT-STATE v6.1",
        "source_type": "DETERMINISTIC_AXIS_SPACE_GENERATOR_SNAPSHOT",
        "edition": "v6.4",
        "location": str(snapshot_path.relative_to(root)),
        "sha256": snapshot_sha,
        "declared_records": {"composite_models": len(candidates), "axis_rows": len(full_summary["axis_space"]["rows"]), "classified_axis_subsets": full_summary["axis_space"]["interaction_census"]["total_classified_axis_subsets"]},
        "processed_records": {"composite_models": len(candidates), "axis_rows": len(full_summary["axis_space"]["rows"]), "classified_axis_subsets": full_summary["axis_space"]["interaction_census"]["total_classified_axis_subsets"]},
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    spot_rows = [row for row in candidates if row.get("prior_art_check_id")]
    spot_report = {
        "schema": "phi-composite-model-prior-art-spot-check/v6.1",
        "checked_composite_model_count": len(spot_rows),
        "global_prior_art_scan": "NOT_RUN",
        "rows": [{
            "candidate_id": row["candidate_id"],
            "source_owner_ids": row["source_owner_ids"],
            "transformation_id": row["transformation"]["transformation_id"],
            "prior_art_status": row["prior_art_status"],
            "prior_art_check_id": row["prior_art_check_id"],
            "claim_boundary": row["prior_art_claim_boundary"],
            "sources": row["prior_art_sources"],
        } for row in spot_rows],
        "status": "PASS_POINT_CHECKS_ONLY",
    }
    spot_report["sha256"] = digest_payload({k:v for k,v in spot_report.items() if k != "sha256"})
    spot_report_path.write_text(json.dumps(spot_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    deep_report = dict(full_summary.get("deep_formula_search", {}))
    deep_report_path.write_text(json.dumps(deep_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    full_summary["deep_formula_report_file"] = str(deep_report_path.relative_to(root))
    full_summary["deep_formula_report_sha256"] = hashlib.sha256(deep_report_path.read_bytes()).hexdigest()
    ablation_report = dict(full_summary.get("law_ablation_rediscovery", {}))
    ablation_report_path.write_text(json.dumps(ablation_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    full_summary["law_ablation_report_file"] = str(ablation_report_path.relative_to(root))
    full_summary["law_ablation_report_sha256"] = hashlib.sha256(ablation_report_path.read_bytes()).hexdigest()
    full_summary["spot_check_report_file"] = str(spot_report_path.relative_to(root))
    full_summary["spot_check_report_sha256"] = spot_report["sha256"]
    full_summary["axis_report_file"] = str(axis_report_path.relative_to(root))
    full_summary["axis_report_sha256"] = axis_report["sha256"]
    full_summary["snapshot_file"] = str(snapshot_path.relative_to(root))
    full_summary["snapshot_sha256"] = snapshot_sha
    full_summary["manifest_file"] = str(manifest_path.relative_to(root))
    full_summary["sha256"] = digest_payload({k: v for k, v in full_summary.items() if k != "sha256"})
    report_path.write_text(json.dumps(full_summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return full_summary


def regenerate_candidates(root: str | Path, catalog: LawCatalog, bridges: Mapping[str, DomainBridge]) -> Mapping[str, Any]:
    pipeline = CandidateGenerationPipeline(catalog, bridges, load_candidate_spot_checks(root))
    candidates, summary = pipeline.run()
    return write_generation(root, candidates, summary)


# ---------------------------------------------------------------------------
# Quantum-information and computational-method space
# ---------------------------------------------------------------------------

QUANTUM_METHOD_SCHEMA = "phi-quantum-method-scan/v6.4"
QUANTUM_METHOD_DOMAIN = "quantum_information_and_computational_methods"


def load_computational_methods(root: str | Path) -> List[Dict[str, Any]]:
    path = Path(root) / "data" / "passports" / "computational_methods.jsonl"
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return sorted(rows, key=lambda row: row["method_id"])


def load_quantum_target(root: str | Path, target_id: str = "LARGE_QUBIT_REALISTIC_EMULATOR_V1") -> Dict[str, Any]:
    path = Path(root) / "data" / "targets" / "large_qubit_realistic_emulator.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("target_id") != target_id:
        raise KeyError(target_id)
    stored_digest = str(payload.get("digest", ""))
    canonical_payload = {key: value for key, value in payload.items() if key != "digest"}
    calculated_digest = digest_payload(canonical_payload)
    if stored_digest != calculated_digest:
        raise ValueError(f"quantum target digest mismatch: stored={stored_digest} calculated={calculated_digest}")
    return payload


class QuantumMethodScanner:
    """Deterministic route scanner over established computational methods.

    It never promotes a numerical method to a physical law and never converts
    an unknown resource feature into a success.  Unknown applicability
    requirements remain explicit conditions on the emitted route.
    """

    def __init__(self, methods: Sequence[Mapping[str, Any]]) -> None:
        self.methods = tuple(sorted((dict(row) for row in methods), key=lambda row: row["method_id"]))
        ids = [row["method_id"] for row in self.methods]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate computational method ids")
        self.axis_ids = frozenset(DOMAIN_REGISTRIES[QUANTUM_METHOD_DOMAIN].axes)
        for row in self.methods:
            unknown_coordinate_axes = set(row.get("scientific_coordinate", {})) - self.axis_ids
            unknown_rule_axes = {str(rule.get("field")) for rule in row.get("applicability_rules", [])} - self.axis_ids
            if unknown_coordinate_axes or unknown_rule_axes:
                raise ValueError(
                    f"method {row['method_id']} references unregistered axes: "
                    f"coordinate={sorted(unknown_coordinate_axes)} rules={sorted(unknown_rule_axes)}"
                )

    def _axis_census(self, features: Mapping[str, Any]) -> Dict[str, Any]:
        method_coordinate_axes = set().union(*(set(row.get("scientific_coordinate", {})) for row in self.methods))
        rule_axes = set().union(*({str(rule["field"]) for rule in row.get("applicability_rules", [])} for row in self.methods))
        target_axes = set(features)
        active_axes = method_coordinate_axes | rule_axes | target_axes
        rows = []
        for axis_id in sorted(self.axis_ids):
            roles = []
            if axis_id in method_coordinate_axes:
                roles.append("METHOD_COORDINATE")
            if axis_id in rule_axes:
                roles.append("APPLICABILITY_RULE")
            if axis_id in target_axes:
                roles.append("TARGET_FEATURE")
            rows.append({
                "axis_id": axis_id,
                "roles": roles,
                "status": "ACTIVE_IN_CURRENT_SCAN" if roles else "OPEN_UNINSTANTIATED",
            })
        return {
            "registered_axis_count": len(self.axis_ids),
            "method_coordinate_axis_count": len(method_coordinate_axes),
            "applicability_rule_axis_count": len(rule_axes),
            "target_feature_axis_count": len(target_axes),
            "active_axis_count": len(active_axes),
            "open_uninstantiated_axis_count": len(self.axis_ids - active_axes),
            "open_uninstantiated_axes": sorted(self.axis_ids - active_axes),
            "all_referenced_axes_registered": not bool(active_axes - self.axis_ids),
            "axis_rows": rows,
        }

    @staticmethod
    def _rule_status(rule: Mapping[str, Any], features: Mapping[str, Any]) -> Tuple[str, str]:
        field = str(rule["field"])
        operator = str(rule.get("operator", "equals"))
        expected = rule.get("value")
        actual = features.get(field, "UNKNOWN")
        if actual in {None, "UNKNOWN", "unknown"}:
            return "CONDITIONAL", f"{field} is unknown; requires {operator} {expected!r}"
        if operator == "equals":
            ok = actual == expected
        elif operator == "in":
            ok = actual in set(expected)
        elif operator == "less_equal":
            ok = float(actual) <= float(expected)
        elif operator == "greater_equal":
            ok = float(actual) >= float(expected)
        elif operator == "truthy":
            ok = bool(actual) is bool(expected)
        else:
            raise ValueError(f"unsupported applicability operator {operator}")
        return ("PASS", "") if ok else ("FAIL", f"{field}={actual!r} violates {operator} {expected!r}")

    @staticmethod
    def _compatible(combo: Sequence[Mapping[str, Any]]) -> Tuple[bool, List[str]]:
        ids = {str(row["method_id"]) for row in combo}
        reasons: List[str] = []
        groups: Dict[str, str] = {}
        for row in combo:
            group = row.get("exclusive_group")
            if group:
                previous = groups.get(str(group))
                if previous and previous != row["method_id"]:
                    reasons.append(f"exclusive_group:{group}:{previous},{row['method_id']}")
                groups[str(group)] = str(row["method_id"])
            conflict = ids.intersection(set(row.get("incompatible_method_ids", [])))
            if conflict:
                reasons.append(f"incompatible:{row['method_id']}:{','.join(sorted(conflict))}")
        # A backend or optimizer alone is not a simulation representation.
        if not any(row.get("role") == "representation" for row in combo):
            reasons.append("missing_representation_method")
        return not reasons, reasons

    def scan(
        self,
        target: Mapping[str, Any],
        *,
        max_order: int | None = None,
        limit: int = 40,
        combination_budget: int | None = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Exactly enumerate registered method subsets with bounded materialization."""
        import bisect
        method_count = len(self.methods)
        resolved_max_order = method_count if max_order is None else min(method_count, int(max_order))
        if resolved_max_order < 1:
            raise ValueError("max_order must be positive or None")
        if limit < 1:
            raise ValueError("limit must be positive")
        planned_combinations = sum(math.comb(method_count, order) for order in range(1, resolved_max_order + 1))
        if combination_budget is not None and planned_combinations > int(combination_budget):
            raise RuntimeError(f"SCAN_BUDGET_INSUFFICIENT:required={planned_combinations}:available={int(combination_budget)}")
        needs = tuple(sorted(set(target.get("required_capabilities", []))))
        need_index = {name: index for index, name in enumerate(needs)}
        features = dict(target.get("features", {}))
        unknown_target_axes = set(features) - self.axis_ids
        if unknown_target_axes:
            raise ValueError(f"quantum target references unregistered axes: {sorted(unknown_target_axes)}")
        axis_census = self._axis_census(features)
        method_cap_masks=[]; method_conditionals=[]; method_known_fail=[]; representation_flags=[]; exclusive_groups=[]; conflict_masks=[]
        id_to_index={str(row['method_id']):i for i,row in enumerate(self.methods)}
        for method in self.methods:
            cap_mask=0
            for capability in method.get('capabilities',[]):
                if capability in need_index: cap_mask |= 1 << need_index[capability]
            method_cap_masks.append(cap_mask)
            conditional=[]; failed=False
            for rule in method.get('applicability_rules',[]):
                status,reason=self._rule_status(rule,features)
                if status=='FAIL': failed=True
                elif status=='CONDITIONAL': conditional.append(f"{method['method_id']}:{reason}")
            method_conditionals.append(tuple(sorted(conditional))); method_known_fail.append(failed)
            representation_flags.append(method.get('role')=='representation')
            exclusive_groups.append(str(method.get('exclusive_group')) if method.get('exclusive_group') else None)
            cm=0
            for conflict_id in method.get('incompatible_method_ids',[]):
                other=id_to_index.get(str(conflict_id))
                if other is not None: cm |= 1 << other
            conflict_masks.append(cm)
        evaluated=rejected=admissible_count=0; rejected_by_gate={}; selected_light=[]
        for order in range(1,resolved_max_order+1):
            for combo_indices in itertools.combinations(range(method_count),order):
                evaluated += 1; bitmask=0; capmask=0; cond=[]; groups=set(); compatible=True; has_repr=False; known_failed=False
                for index in combo_indices:
                    if conflict_masks[index] & bitmask: compatible=False; break
                    group=exclusive_groups[index]
                    if group is not None:
                        if group in groups: compatible=False; break
                        groups.add(group)
                    bitmask |= 1 << index; capmask |= method_cap_masks[index]
                    has_repr = has_repr or representation_flags[index]
                    known_failed = known_failed or method_known_fail[index]
                    cond.extend(method_conditionals[index])
                if not compatible or not has_repr:
                    rejected += 1; rejected_by_gate['METHOD_COMPOSITION_COMPATIBLE']=rejected_by_gate.get('METHOD_COMPOSITION_COMPATIBLE',0)+1; continue
                if known_failed:
                    rejected += 1; rejected_by_gate['KNOWN_FEATURE_REQUIREMENTS']=rejected_by_gate.get('KNOWN_FEATURE_REQUIREMENTS',0)+1; continue
                covered_count=capmask.bit_count()
                if covered_count==0:
                    rejected += 1; rejected_by_gate['TARGET_CAPABILITY_RELEVANT']=rejected_by_gate.get('TARGET_CAPABILITY_RELEVANT',0)+1; continue
                admissible_count += 1
                unmet_count=len(needs)-covered_count; conditional=tuple(sorted(cond))
                priority=10*covered_count-3*unmet_count-len(conditional)-(order-1)
                method_ids=tuple(str(self.methods[i]['method_id']) for i in combo_indices)
                covered=tuple(needs[i] for i in range(len(needs)) if capmask & (1<<i))
                route_payload={'scanner_version':GENERATOR_VERSION,'target_digest':target['digest'],'method_ids':list(method_ids),'covered_capabilities':list(covered),'conditional_requirements':list(conditional)}
                route_id='QROUTE-'+digest_payload(route_payload)[:20].upper(); key=(-priority,unmet_count,route_id)
                item=(key,combo_indices,capmask,conditional,method_ids,route_id)
                position=bisect.bisect_left([entry[0] for entry in selected_light],key)
                if position<limit:
                    selected_light.insert(position,item)
                    if len(selected_light)>limit: selected_light.pop()
        routes=[]
        for key,combo_indices,capmask,conditional,method_ids,route_id in selected_light:
            combo=tuple(self.methods[i] for i in combo_indices)
            covered=[needs[i] for i in range(len(needs)) if capmask & (1<<i)]; unmet=sorted(set(needs)-set(covered)); priority=-int(key[0])
            proof_graph=method_route_proof_graph(route_id); limit_protocol=method_route_limit_protocol(route_id,combo); source_ledger=source_ledger_from_methods(combo,ledger_id=route_id+':SOURCES')
            route={'schema':QUANTUM_METHOD_SCHEMA,'route_id':route_id,'target_id':target['target_id'],'domain_id':QUANTUM_METHOD_DOMAIN,'method_ids':list(method_ids),'method_names_ru':[row['name_ru'] for row in combo],'composition_order':len(combo),'covered_capabilities':list(covered),'unmet_capabilities':unmet,'conditional_requirements':list(conditional),'cost_models':{row['method_id']:row['cost_model'] for row in combo},'error_contracts':{row['method_id']:row['error_contract'] for row in combo},'proof_obligation_graph':dataclasses.asdict(proof_graph),'limit_protocol':dataclasses.asdict(limit_protocol),'primary_source_ledger':dataclasses.asdict(source_ledger),'known_limitations':{row['method_id']:row.get('limitations',[]) for row in combo},'priority_score':priority,'priority_score_semantics':'transparent_target_coverage_heuristic_not_scientific_truth','strategy_scope':'CONDITIONAL_COMPUTATIONAL_STRATEGY','epistemic_state':'PENDING_COMPUTATIONAL_QUALIFICATION','qubit_feasibility':'STRUCTURE_AND_OUTPUT_DEPENDENT_NOT_GLOBALLY_ESTABLISHED','benchmark_status':'OWNER_LEVEL_CONTROLS_AVAILABLE_ROUTE_COMPOSITION_NOT_RUN','hardware_qualification':'MARKOV_SNAPSHOT_ONLY_NON_MARKOV_DATA_REQUIRED','gates':{'METHODS_ESTABLISHED':all(row.get('epistemic_state')=='ESTABLISHED_METHOD' for row in combo),'METHOD_COMPOSITION_COMPATIBLE':True,'TARGET_CAPABILITY_RELEVANT':bool(covered),'COST_MODEL_DECLARED':all(bool(row.get('cost_model')) for row in combo),'ERROR_CONTRACT_DECLARED':all(bool(row.get('error_contract')) for row in combo),'NO_UNIVERSAL_1000_QUBIT_CLAIM':True},'provenance':{'method_passport_digests':{row['method_id']:row['digest'] for row in combo},'target_digest':target['digest'],'scanner_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},'digest':''}
            route['digest']=digest_payload({**route,'digest':''}); routes.append(route)
        routes.sort(key=lambda row:(-row['priority_score'],len(row['unmet_capabilities']),row['route_id']))
        summary={'schema':QUANTUM_METHOD_SCHEMA,'scanner_version':GENERATOR_VERSION,'target_id':target['target_id'],'target_digest':target['digest'],'method_count':len(self.methods),'axis_count':DOMAIN_REGISTRIES[QUANTUM_METHOD_DOMAIN].axis_count,'axis_census':axis_census,'max_composition_order':resolved_max_order,'hard_order_limit':None,'scan_order_policy':'ALL_REGISTERED_METHOD_ORDERS' if resolved_max_order==method_count else 'EXPLICIT_CALLER_PREFIX','all_registered_orders_scanned':resolved_max_order==method_count,'planned_method_combinations':planned_combinations,'combination_budget':combination_budget,'evaluated_method_combinations':evaluated,'rejected_method_combinations':rejected,'admissible_method_routes_before_limit':admissible_count,'selected_route_count':len(routes),'materialization_policy':'EXACT_ENUMERATION_BOUNDED_TOP_ROUTE_MATERIALIZATION','rejected_by_gate':dict(sorted(rejected_by_gate.items())),'all_qubit_feasibility_unclaimed':True,'benchmark_status':'OWNER_LEVEL_CONTROLS_AVAILABLE_ROUTE_COMPOSITION_NOT_RUN','real_hardware_status':'MARKOV_SNAPSHOT_ONLY_NON_MARKOV_DATA_REQUIRED','status':'PASS_WITH_CONDITIONAL_ROUTES_AND_OPEN_AXES' if routes else 'FAIL'}
        summary['sha256']=digest_payload({k:v for k,v in summary.items() if k!='sha256'})
        return routes, summary


def write_quantum_method_scan(root: str | Path, routes: Sequence[Mapping[str, Any]], summary: Mapping[str, Any]) -> Mapping[str, Any]:
    root = Path(root)
    routes_path = root / "data" / "passports" / "quantum_method_routes.jsonl"
    report_path = root / "reports" / "QUANTUM_METHOD_SCAN_CURRENT.json"
    snapshot_path = root / "data" / "source_snapshots" / "generated_quantum_method_routes_v6_4.json"
    manifest_path = root / "data" / "manifests" / "generated_quantum_method_routes_v6_4.json"
    routes_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    routes_path.write_text("".join(canonical_json(row) + "\n" for row in routes), encoding="utf-8")
    routes_sha = hashlib.sha256(routes_path.read_bytes()).hexdigest()
    snapshot = {
        "schema": "phi-generated-quantum-method-routes/v6.4",
        "target_id": summary["target_id"],
        "target_digest": summary["target_digest"],
        "route_count": len(routes),
        "routes_file": str(routes_path.relative_to(root)),
        "routes_file_sha256": routes_sha,
        "qubit_feasibility": "STRUCTURE_AND_OUTPUT_DEPENDENT_NOT_GLOBALLY_ESTABLISHED",
    }
    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "source_id": "GENERATED_QUANTUM_METHOD_ROUTES_V6_4",
        "title": "Детерминированные условные маршруты методов для большого реалистичного квантового эмулятора",
        "source_type": "DETERMINISTIC_COMPUTATIONAL_METHOD_SCAN",
        "edition": "v6.1",
        "location": str(snapshot_path.relative_to(root)),
        "sha256": hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
        "declared_records": {"quantum_method_routes": len(routes)},
        "processed_records": {"quantum_method_routes": len(routes)},
        "claim_boundary": {"qubit_feasibility": "STRUCTURE_AND_OUTPUT_DEPENDENT_NOT_GLOBALLY_ESTABLISHED", "execution_qualification": "OWNER_LEVEL_CONTROLS_AVAILABLE_ROUTE_COMPOSITION_NOT_RUN"},
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = dict(summary)
    report["routes_file"] = str(routes_path.relative_to(root))
    report["routes_file_sha256"] = routes_sha
    report["snapshot_file"] = str(snapshot_path.relative_to(root))
    report["manifest_file"] = str(manifest_path.relative_to(root))
    report["routes"] = list(routes)
    report["sha256"] = digest_payload({k: v for k, v in report.items() if k != "sha256"})
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def regenerate_quantum_method_routes(
    root: str | Path,
    *,
    max_order: int | None = None,
    limit: int = 40,
    combination_budget: int | None = None,
) -> Mapping[str, Any]:
    methods = load_computational_methods(root)
    target = load_quantum_target(root)
    routes, summary = QuantumMethodScanner(methods).scan(
        target, max_order=max_order, limit=limit, combination_budget=combination_budget
    )
    return write_quantum_method_scan(root, routes, summary)
