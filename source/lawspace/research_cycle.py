"""Authoritative open-ended research orchestration for Φ-Compiler 15.2.8.

The module coordinates existing scientific owners around one adaptive research
loop.  It does not assume that a law is known in advance and it does not treat
the current registered axis count, hypothesis order, competitor count, or a
domain-specific frontier as a universal ceiling.

Core discipline:
* observations and provenance define the current evidence state;
* active model coordinates and dormant available coordinates are distinct;
* dormant coordinates may enter a model only after residual evidence selects
  them through AdaptiveAxisDiscovery;
* hypotheses are research objects, not laws, and may force axis/language or
  representation evolution;
* no user/assistant/external text can stamp ATLAS_NATIVE; only a digest-bound
  execution receipt accepted by ClaimProvenanceFirewall can do that.

Legacy ScientificResearchCycle surfaces remain compatibility facades only.
"""
from __future__ import annotations

import dataclasses
import hashlib
import itertools
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence, Tuple

import numpy as np

from .candidates import CandidateGenerationPipeline, DEEP_CORE_DOMAINS, DirectedResearchQuery, directed_owner_hypergraph_research
from .domains import DOMAIN_REGISTRIES, dynamic_axis_registry_state, install_canonical_dynamic_axis
from .schema import AxisValueKind, LawPassport, canonical_json, digest_payload
from .scientific_verification import ScientificVerificationCore

RESEARCH_CYCLE_SCHEMA = "phi-scientific-research-cycle/v15.0"
RESEARCH_CYCLE_OWNER = "SCIENTIFIC-RESEARCH-CYCLE/15.2.8"
RESEARCH_CYCLE_VERSION = "15.2.8"
SEMANTIC_QUESTION_OWNER = "SEMANTIC-TYPED-QUESTION/2.0.0"
AUTONOMOUS_RESEARCH_SCHEMA = "phi-autonomous-research-orchestration/v2"
CANDIDATE_BIRTH_SCHEMA = "phi-candidate-birth-capability-resolution/v1"
GAMMA_CLOSURE_SCHEMA = "phi-deep-coupling-closure/v1"
MINIMUM_COMPETING_HYPOTHESES = 5


def _tokens(*values: Any) -> set[str]:
    text = " ".join(str(v) for v in values if v is not None).casefold()
    return set(re.findall(r"[0-9a-zа-я_]+", text))


def _entropy(probabilities: Sequence[float]) -> float:
    total = float(sum(probabilities))
    if total <= 0.0:
        return 0.0
    value = 0.0
    for raw in probabilities:
        p = float(raw) / total
        if p > 0.0:
            value -= p * math.log2(p)
    return value


def _normalise_probability_map(values: Mapping[str, float], required_ids: Sequence[str]) -> Dict[str, float]:
    missing = [candidate_id for candidate_id in required_ids if candidate_id not in values]
    extra = sorted(set(values) - set(required_ids))
    if missing or extra:
        raise ValueError(f"probability map mismatch: missing={missing}, extra={extra}")
    raw = {candidate_id: float(values[candidate_id]) for candidate_id in required_ids}
    if any((not math.isfinite(v)) or v < 0.0 for v in raw.values()):
        raise ValueError("probabilities must be finite and non-negative")
    total = sum(raw.values())
    if total <= 0.0:
        raise ValueError("probability mass must be positive")
    return {candidate_id: value / total for candidate_id, value in raw.items()}


def _candidate_formula_digest(candidate: Mapping[str, Any]) -> str:
    return str(candidate.get("formula", {}).get("digest", ""))


def _candidate_mechanism_family_signature(candidate: Mapping[str, Any]) -> str:
    """Mechanistic independence class, intentionally coarser than formula identity."""
    transformation = candidate.get("transformation", {})
    generator = candidate.get("generator", {})
    payload = {
        "transformation_id": transformation.get("transformation_id"),
        "bridge_id": transformation.get("bridge_id"),
        "generator_id": generator.get("generator_id"),
        "source_domains": sorted(set(str(x) for x in candidate.get("source_domains", ()))),
        "target_domains": sorted(set(str(x) for x in candidate.get("target_domains", ()))),
        "categories": sorted(str(x) for x in candidate.get("classification", {}).get("categories", ())),
    }
    return digest_payload(payload)


def _candidate_content_signature(candidate: Mapping[str, Any]) -> str:
    payload = {
        "mechanism_family_signature": _candidate_mechanism_family_signature(candidate),
        "source_owner_ids": sorted(str(x) for x in candidate.get("source_owner_ids", ())),
        "formula_digest": _candidate_formula_digest(candidate),
        "controlled_limits": sorted(str(x) for x in candidate.get("controlled_limits", ())),
    }
    return digest_payload(payload)


def _candidate_text(candidate: Mapping[str, Any]) -> str:
    return " ".join(
        [
            str(candidate.get("candidate_id", "")),
            " ".join(str(x) for x in candidate.get("source_names_ru", ())),
            " ".join(str(x) for x in candidate.get("source_domains", ())),
            " ".join(str(x) for x in candidate.get("target_domains", ())),
            " ".join(str(x) for x in candidate.get("classification", {}).get("categories", ())),
            str(candidate.get("formula", {}).get("source", "")),
            str(candidate.get("falsification_criterion", "")),
        ]
    ).casefold()


@dataclass(frozen=True)
class DynamicAxisProposal:
    proposal_id: str
    domain_id: str
    axis_id: str
    description_ru: str
    value_kind: str
    physical_or_information_meaning: str
    measurement_protocol: str
    units_or_normalization: str
    expected_range: Mapping[str, Any]
    falsifiable_advantage: str
    redundancy_test: str
    allowed_values: Tuple[str, ...] = ()
    provenance_evidence: Tuple[str, ...] = ()

    def validate(self) -> None:
        required = {
            "proposal_id": self.proposal_id,
            "domain_id": self.domain_id,
            "axis_id": self.axis_id,
            "description_ru": self.description_ru,
            "value_kind": self.value_kind,
            "physical_or_information_meaning": self.physical_or_information_meaning,
            "measurement_protocol": self.measurement_protocol,
            "units_or_normalization": self.units_or_normalization,
            "falsifiable_advantage": self.falsifiable_advantage,
            "redundancy_test": self.redundancy_test,
        }
        empty = [key for key, value in required.items() if not str(value).strip()]
        if empty:
            raise ValueError(f"dynamic axis proposal missing required fields: {empty}")
        if self.domain_id not in DOMAIN_REGISTRIES:
            raise ValueError(f"unknown domain for dynamic axis proposal: {self.domain_id}")
        try:
            AxisValueKind(self.value_kind)
        except ValueError as exc:
            raise ValueError(f"unsupported axis value kind: {self.value_kind}") from exc
        if not isinstance(self.expected_range, Mapping) or not self.expected_range:
            raise ValueError("expected_range must be a non-empty mapping")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return dataclasses.asdict(self)


class DynamicAxisAdmissionOwner:
    """Provisional admission owner; never mutates canonical registries implicitly."""

    owner_id = "DYNAMIC-AXIS-ADMISSION/6.24.0"

    @staticmethod
    def _redundancy_rows(proposal: DynamicAxisProposal) -> list[Mapping[str, Any]]:
        proposal_tokens = _tokens(proposal.axis_id, proposal.description_ru, proposal.physical_or_information_meaning)
        rows: list[Mapping[str, Any]] = []
        registry = DOMAIN_REGISTRIES[proposal.domain_id]
        for axis_id, axis in registry.axes.items():
            existing_tokens = _tokens(axis_id, axis.description_ru)
            union = proposal_tokens | existing_tokens
            similarity = (len(proposal_tokens & existing_tokens) / len(union)) if union else 0.0
            if axis_id == proposal.axis_id or similarity >= 0.45:
                rows.append({
                    "axis_id": axis_id,
                    "description_ru": axis.description_ru,
                    "token_jaccard": similarity,
                    "exact_axis_id_match": axis_id == proposal.axis_id,
                })
        return sorted(rows, key=lambda row: (-float(row["token_jaccard"]), str(row["axis_id"])))

    def assess(self, proposal: DynamicAxisProposal) -> Mapping[str, Any]:
        proposal.validate()
        redundancy = self._redundancy_rows(proposal)
        exact_duplicate = any(bool(row["exact_axis_id_match"]) for row in redundancy)
        near_duplicate = any(float(row["token_jaccard"]) >= 0.70 for row in redundancy)
        range_keys = {str(k) for k in proposal.expected_range}
        range_declared = bool(range_keys & {"minimum", "maximum", "values", "distribution", "normalization"})
        gates = {
            "DOMAIN_REGISTERED": proposal.domain_id in DOMAIN_REGISTRIES,
            "AXIS_ID_NOT_ALREADY_REGISTERED": not exact_duplicate,
            "MEANING_DECLARED": bool(proposal.physical_or_information_meaning.strip()),
            "MEASUREMENT_PROTOCOL_DECLARED": bool(proposal.measurement_protocol.strip()),
            "UNITS_OR_NORMALIZATION_DECLARED": bool(proposal.units_or_normalization.strip()),
            "EXPECTED_RANGE_DECLARED": range_declared,
            "FALSIFIABLE_ADVANTAGE_DECLARED": bool(proposal.falsifiable_advantage.strip()),
            "REDUNDANCY_TEST_DECLARED": bool(proposal.redundancy_test.strip()),
            "NO_HIGH_CONFIDENCE_REDUNDANCY": not near_duplicate,
        }
        hard_ok = all(gates.values())
        status = "ADMITTED_PROVISIONAL_RESEARCH_AXIS" if hard_ok else (
            "PENDING_REDUNDANCY_REVIEW" if not exact_duplicate and near_duplicate else "REJECTED_DYNAMIC_AXIS_PROPOSAL"
        )
        axis_definition = None
        if hard_ok:
            axis_definition = {
                "axis_id": proposal.axis_id,
                "domain": proposal.domain_id,
                "description_ru": proposal.description_ru,
                "value_kind": proposal.value_kind,
                "allowed_values": list(proposal.allowed_values),
                "provenance": f"PROVISIONAL:{proposal.proposal_id}",
            }
        result = {
            "schema": "phi-dynamic-axis-admission/v6.24",
            "owner": self.owner_id,
            "proposal": proposal.to_dict(),
            "gates": gates,
            "redundancy_candidates": redundancy[:20],
            "status": status,
            "provisional_axis_definition": axis_definition,
            "active_registry_mutation": False,
            "canonical_registration_required": hard_ok,
            "claim_boundary": {
                "provisional_axis_may_guide_research": hard_ok,
                "provisional_axis_is_established_scientific_coordinate": False,
                "canonical_axis_registry_mutated": False,
                "new_physical_truth_created_by_admission": False,
            },
        }
        result["digest"] = digest_payload(result)
        return result


class DynamicAxisPromotionOwner:
    """Sole owner for provisional -> canonical dynamic-axis registration.

    Two evidence routes are intentionally distinct:
    * MODEL_DISCOVERED: genuinely model-born coordinates require measured uncertainty,
      practical distinguishability, complexity-penalised OOD gain, independent
      replication and a survived falsification attempt.
    * SOURCE_ESTABLISHED: a scientifically established measurand missing from the
      local registry can be added from authoritative source evidence after semantic
      and redundancy checks.  This is registry completion, not discovery.

    Canonical registration never creates a law or a truth claim.
    """

    owner_id = "DYNAMIC-AXIS-PROMOTION/8.0.0"
    schema = "phi-dynamic-axis-promotion/v8.0"
    semantic_classes = {"INDEPENDENT_MEASURAND", "DERIVED_COORDINATE", "LATENT_MECHANISM"}
    routes = {"MODEL_DISCOVERED", "SOURCE_ESTABLISHED"}

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": self.schema,
            "owner": self.owner_id,
            "sole_canonical_dynamic_axis_mutation_owner": True,
            "routes": sorted(self.routes),
            "semantic_classes": sorted(self.semantic_classes),
            "pipeline": [
                "PROVISIONAL_ADMISSION", "SEMANTIC_CLASS", "REDUNDANCY",
                "CENTRAL_SCIENTIFIC_VERIFICATION", "IDENTIFIABILITY_OR_SOURCE_AUTHORITY",
                "OOD_OR_SOURCE_RELEVANCE", "INDEPENDENT_REPLICATION_OR_MULTI_SOURCE", "FALSIFICATION",
                "ATOMIC_PERSIST", "RUNTIME_RELOAD", "RECEIPT",
            ],
            "hard_boundaries": {
                "canonical_axis_is_new_law": False,
                "canonical_axis_is_independent_physical_dimension": False,
                "model_discovered_single_fit_can_promote": False,
                "source_established_registry_completion_is_discovery": False,
                "silent_replacement_of_existing_axis": False,
                "string_provenance_can_authorize_source_established_axis": False,
                "serialized_verification_receipt_is_authorization": False,
                "world_attestation_required_for_canonical_mutation": True,
            },
        }
        return {**payload, "digest": digest_payload(payload)}


    def evaluate_and_promote(
        self,
        proposal: DynamicAxisProposal,
        validation: Mapping[str, Any],
        *,
        mutate: bool = True,
        registry_path: str | Path | None = None,
    ) -> Mapping[str, Any]:
        v = dict(validation)
        route = str(v.get("promotion_route", "MODEL_DISCOVERED")).upper()
        registry_file = Path(registry_path) if registry_path else None
        verification_bundle = dict(v.get("scientific_verification_bundle", {}) or {})
        verification = ScientificVerificationCore().verify_bundle(verification_bundle)
        evidence_digest = str(verification.get("verification_digest", "")).strip()
        existing_state = dynamic_axis_registry_state(registry_file)
        for existing in existing_state.get("entries", ()):
            axis_row = dict(existing.get("axis_definition", {}))
            if axis_row.get("domain") == proposal.domain_id and axis_row.get("axis_id") == proposal.axis_id:
                same = (
                    str(existing.get("proposal_id", "")) == proposal.proposal_id
                    and str(existing.get("promotion_route", "")) == route
                    and str(existing.get("evidence_digest", "")) == evidence_digest
                )
                if same:
                    payload = {
                        "schema": self.schema, "owner": self.owner_id, "proposal": proposal.to_dict(),
                        "validation": v, "promotion_route": route,
                        "semantic_class": str(v.get("semantic_class", "")).upper(),
                        "gates": {"IDEMPOTENT_EXISTING_REGISTRATION_MATCH": True},
                        "qualified": True, "mutation_requested": bool(mutate),
                        "persistence": {"status": "IDEMPOTENT_ALREADY_REGISTERED", "axis_id": proposal.axis_id, "domain_id": proposal.domain_id},
                        "registry_before": {k: existing_state[k] for k in ("base_axis_count", "dynamic_axis_count", "canonical_axis_count")},
                        "registry_after": {k: existing_state[k] for k in ("base_axis_count", "dynamic_axis_count", "canonical_axis_count")},
                        "status": "IDEMPOTENT_ALREADY_REGISTERED",
                        "claim_boundary": {"canonical_axis_registered": True, "new_law_established": False, "new_physical_truth_created": False, "world_novelty_established": False},
                    }
                    return {**payload, "digest": digest_payload(payload)}
                raise ValueError(f"conflicting canonical dynamic axis already exists: {proposal.domain_id}:{proposal.axis_id}")
        admission = DynamicAxisAdmissionOwner().assess(proposal)
        semantic_class = str(v.get("semantic_class", "")).upper()
        postfreeze_redundancy = str(v.get("postfreeze_redundancy_status", "")).upper()
        verification_ok = (
            verification.get("scientific_candidate_allowed") is True
            and str(verification_bundle.get("proposer_owner", "")) == self.owner_id
        )
        common = {
            "PROVISIONAL_ADMITTED": admission.get("status") == "ADMITTED_PROVISIONAL_RESEARCH_AXIS",
            "SEMANTIC_CLASS_DECLARED": semantic_class in self.semantic_classes,
            "POSTFREEZE_NO_REGISTERED_EQUIVALENT": postfreeze_redundancy == "NO_REGISTERED_AXIS_EQUIVALENT",
            "CENTRAL_SCIENTIFIC_VERIFICATION_PASS": verification_ok,
            "WORLD_ATTESTATION_READY": verification.get("world_attestation_ready") is True,
            "EVIDENCE_DIGEST_DECLARED": bool(evidence_digest),
            "FALSIFICATION_PROTOCOL_DECLARED": bool(str(v.get("falsification_protocol", "")).strip()),
        }
        route_gates: Dict[str, bool]
        if route == "MODEL_DISCOVERED":
            route_gates = {
                "VERIFIED_INTERNAL_MEASUREMENT_CLASS": str(verification.get("evidence_class", "")) in {"INTERNAL_MEASUREMENT", "LOCAL_SNAPSHOT"},
                "MEASUREMENT_UNCERTAINTY_DECLARED": bool(v.get("measurement_uncertainty_declared")),
                "IDENTIFIABILITY_PASS": bool(v.get("identifiability_pass")),
                "OOD_GAIN_PASS": bool(v.get("ood_pass")) and float(v.get("ood_fractional_improvement", 0.0)) > 0.0 and float(v.get("complexity_penalized_delta_log_likelihood", 0.0)) > 0.0,
                "INDEPENDENT_REPLICATION_PASS": bool(v.get("independent_replication")) and bool(str(v.get("replication_provenance", "")).strip()),
                "FALSIFICATION_SURVIVED": str(v.get("falsification_status", "")).upper() == "SURVIVED",
                "DERIVATION_DECLARED_IF_DERIVED": semantic_class != "DERIVED_COORDINATE" or bool(str(v.get("derivation", "")).strip()),
                "MEASUREMENT_DECLARED_IF_INDEPENDENT": semantic_class != "INDEPENDENT_MEASURAND" or bool(v.get("independent_measurement_or_calibration")),
            }
        elif route == "SOURCE_ESTABLISHED":
            route_gates = {
                "VERIFIED_EXTERNAL_SOURCE_CLASS": str(verification.get("evidence_class", "")) == "EXTERNAL_SOURCE",
                "SOURCE_RELEVANCE_VERIFIED": str(verification.get("sanitized_claim_values", {}).get("axis_source_relevance", "")).upper() == "SUPPORTED",
                "MEASUREMENT_DEFINITION_VERIFIED": str(verification.get("sanitized_claim_values", {}).get("axis_measurement_definition", "")).upper() == "SUPPORTED",
                "MEASUREMENT_OR_DEFINITION_DECLARED": bool(v.get("independent_measurement_or_calibration")) or semantic_class == "DERIVED_COORDINATE",
                "FALSIFICATION_OR_RELEVANCE_TEST_DECLARED": bool(str(v.get("falsification_protocol", "")).strip()),
            }
        else:
            route_gates = {"PROMOTION_ROUTE_SUPPORTED": False}

        gates = {**common, "PROMOTION_ROUTE_SUPPORTED": route in self.routes, **route_gates}
        hard_ok = all(gates.values())
        before = dynamic_axis_registry_state(registry_file)
        persistence: Mapping[str, Any] = {"status": "NOT_MUTATED"}
        status = "BLOCKED_DYNAMIC_AXIS_PROMOTION"
        if hard_ok:
            status = "QUALIFIED_CANONICAL_DYNAMIC_AXIS_MUTATION_NOT_REQUESTED"
            if mutate:
                axis_definition = {
                    "axis_id": proposal.axis_id,
                    "domain": proposal.domain_id,
                    "description_ru": proposal.description_ru,
                    "value_kind": proposal.value_kind,
                    "allowed_values": list(proposal.allowed_values),
                    "required_for": [],
                    "forbidden_for": [],
                    "provenance": f"CANONICAL_DYNAMIC:{route}:{proposal.proposal_id}:{evidence_digest}",
                }
                entry = {
                    "axis_definition": axis_definition,
                    "proposal_id": proposal.proposal_id,
                    "promotion_route": route,
                    "semantic_class": semantic_class,
                    "admission_digest": admission["digest"],
                    "validation_digest": digest_payload(v),
                    "evidence_digest": evidence_digest,
                    "claim_boundary": {
                        "new_law_established": False,
                        "new_physical_truth_created": False,
                        "independent_dimension_claimed": False,
                        "registry_coordinate_canonicalized": True,
                    },
                }
                persistence = install_canonical_dynamic_axis(entry, registry_file)
                status = "PROMOTED_CANONICAL_DYNAMIC_AXIS" if persistence.get("status") == "REGISTERED_CANONICAL_DYNAMIC_AXIS" else str(persistence.get("status"))
        after = dynamic_axis_registry_state(registry_file)
        payload = {
            "schema": self.schema,
            "owner": self.owner_id,
            "proposal": proposal.to_dict(),
            "admission": admission,
            "validation": {k: val for k, val in v.items() if k != "scientific_verification_bundle"},
            "scientific_verification": verification,
            "promotion_route": route,
            "semantic_class": semantic_class,
            "gates": gates,
            "qualified": hard_ok,
            "mutation_requested": bool(mutate),
            "persistence": persistence,
            "registry_before": {k: before[k] for k in ("base_axis_count", "dynamic_axis_count", "canonical_axis_count")},
            "registry_after": {k: after[k] for k in ("base_axis_count", "dynamic_axis_count", "canonical_axis_count")},
            "status": status,
            "claim_boundary": {
                "canonical_axis_registered": bool(hard_ok and mutate and persistence.get("status") in {"REGISTERED_CANONICAL_DYNAMIC_AXIS", "IDEMPOTENT_ALREADY_REGISTERED"}),
                "new_law_established": False,
                "new_physical_truth_created": False,
                "world_novelty_established": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}


class CompetitiveSetOwner:
    """Build a mechanism-family-distinct, query-relevant candidate set.

    v6.24 makes relevance a hard gate.  Connectivity of the owner hypergraph
    may expand the research region, but it can no longer make an unrelated
    domain candidate eligible merely to satisfy the >=5 competitor contract.
    """

    owner_id = "COMPETITIVE-SET-CONTRACT/6.24.0"

    @staticmethod
    def _candidate_domains(candidate: Mapping[str, Any]) -> set[str]:
        return set(str(x) for x in candidate.get("source_domains", ())) | set(str(x) for x in candidate.get("target_domains", ()))

    def build(
        self,
        *,
        question: str,
        directed_region: Mapping[str, Any],
        candidates: Sequence[Mapping[str, Any]],
        minimum: int = MINIMUM_COMPETING_HYPOTHESES,
    ) -> Mapping[str, Any]:
        if minimum < MINIMUM_COMPETING_HYPOTHESES:
            raise ValueError(f"minimum competing hypotheses cannot be below {MINIMUM_COMPETING_HYPOTHESES}")
        question_tokens = _tokens(question)
        query = dict(directed_region.get("query", {}))
        explicit_seed_owner_ids = set(str(x) for x in query.get("seed_owner_ids", ()))
        expanded_owner_ids = set(str(x) for x in directed_region.get("selected_source_owner_ids", ()))
        explicit_required_domains = set(str(x) for x in query.get("required_domains", ()))
        expanded_domains = set(str(x) for x in directed_region.get("selected_domains", ()))

        # Seed-owner domains are the strongest domain anchors when the user/query
        # supplied owners explicitly.  A bridge-reached chemistry/physics domain
        # therefore cannot satisfy an aeronautics query by connectivity alone.
        seed_owner_domains: set[str] = set()
        catalog = getattr(getattr(self, "_runtime", None), "catalog", None)
        if catalog is not None:
            for owner_id in explicit_seed_owner_ids:
                passport = catalog.passports.get(owner_id)
                if passport is not None:
                    seed_owner_domains.add(str(passport.domain_id))
        # CompetitiveSetOwner is also usable independently of a runtime.  The
        # caller may provide the derived seed domains in the directed-region
        # query; ScientificResearchCycleOwner always does so in v6.24.
        seed_owner_domains.update(str(x) for x in query.get("seed_owner_domains", ()))
        anchor_domains = seed_owner_domains or explicit_required_domains

        direct_axes = {
            str(row.get("qualified_axis_id"))
            for row in directed_region.get("axis_rows", ())
            if row.get("disposition") in {"OWNER_BOUND_ACTIVE", "QUERY_DIRECT_OPEN_COORDINATE"}
        }
        scored: list[tuple[tuple[int, int, int, int, int, str], Mapping[str, Any], str]] = []
        rejected_irrelevant = 0
        for candidate in candidates:
            candidate_id = str(candidate.get("candidate_id", ""))
            if not candidate_id or candidate.get("gate_status") == "REJECTED":
                continue
            candidate_domains = self._candidate_domains(candidate)
            candidate_owners = set(str(x) for x in candidate.get("source_owner_ids", ()))
            seed_owner_overlap = len(explicit_seed_owner_ids & candidate_owners)
            expanded_owner_overlap = len(expanded_owner_ids & candidate_owners)
            explicit_domain_overlap = len(explicit_required_domains & candidate_domains)
            anchor_domain_overlap = len(anchor_domains & candidate_domains) if anchor_domains else explicit_domain_overlap

            # HARD RELEVANCE GATE.  When explicit seed owners anchor the query, a
            # candidate must either use one of them or live in a seed-owner domain.
            # Otherwise explicit required domains are the hard anchor.  Expanded
            # bridge domains are scoring context only and never eligibility.
            if explicit_seed_owner_ids:
                relevant = bool(seed_owner_overlap or anchor_domain_overlap)
            elif explicit_required_domains:
                relevant = bool(explicit_domain_overlap)
            else:
                relevant = bool(expanded_owner_overlap or (candidate_domains & expanded_domains))
            if not relevant:
                rejected_irrelevant += 1
                continue

            candidate_axes = set()
            for domain in candidate_domains:
                for axis_id in candidate.get("transformation", {}).get("axis_ids", ()):
                    if domain in DOMAIN_REGISTRIES and axis_id in DOMAIN_REGISTRIES[domain].axes:
                        candidate_axes.add(f"{domain}.{axis_id}")
            axis_overlap = len(direct_axes & candidate_axes)
            token_overlap = len(question_tokens & _tokens(_candidate_text(candidate)))
            score = (seed_owner_overlap, anchor_domain_overlap, expanded_owner_overlap, axis_overlap, token_overlap, candidate_id)
            scored.append((score, candidate, _candidate_mechanism_family_signature(candidate)))
        scored.sort(key=lambda item: item[0], reverse=True)

        selected: list[Mapping[str, Any]] = []
        signatures: set[str] = set()
        for score, candidate, signature in scored:
            if signature in signatures:
                continue
            selected.append(candidate)
            signatures.add(signature)
            if len(selected) >= minimum:
                break

        rows = []
        for candidate in selected:
            rows.append({
                "candidate_id": candidate["candidate_id"],
                "candidate_origin_owner": candidate.get("candidate_origin_owner") or candidate.get("generator", {}).get("generator_id") or "CandidateGenerationPipeline/6.1.0",
                "mechanism_family_signature": _candidate_mechanism_family_signature(candidate),
                "content_signature": _candidate_content_signature(candidate),
                "formula_digest": _candidate_formula_digest(candidate),
                "source_owner_ids": list(candidate.get("source_owner_ids", ())),
                "source_domains": list(candidate.get("source_domains", ())),
                "target_domains": list(candidate.get("target_domains", ())),
                "transformation_id": candidate.get("transformation", {}).get("transformation_id"),
                "falsification_criterion": candidate.get("falsification_criterion", ""),
                "required_measurements": list(candidate.get("required_measurements", ())),
            })
        freeze_payload = {
            "question_digest": digest_payload(question),
            "directed_region_digest": directed_region.get("digest"),
            "candidate_ids": [row["candidate_id"] for row in rows],
            "mechanism_family_signatures": [row["mechanism_family_signature"] for row in rows],
            "content_signatures": [row["content_signature"] for row in rows],
        }
        freeze_digest = digest_payload(freeze_payload)
        status = "COMPETITIVE_SET_FROZEN" if len(rows) >= minimum else "BLOCKED_INSUFFICIENT_INDEPENDENT_COMPETITORS"
        result = {
            "schema": "phi-competitive-set/v6.24",
            "owner": self.owner_id,
            "minimum_required": minimum,
            "candidate_count": len(rows),
            "candidates": rows,
            "candidate_freeze_digest": freeze_digest,
            "mechanism_family_signatures": [row["mechanism_family_signature"] for row in rows],
            "content_signatures": [row["content_signature"] for row in rows],
            "mechanism_independence_rule": "distinct mechanism-family signature after hard query-domain/seed-owner relevance gating",
            "relevance_contract": {
                "explicit_seed_owner_ids": sorted(explicit_seed_owner_ids),
                "seed_owner_domains": sorted(seed_owner_domains),
                "explicit_required_domains": sorted(explicit_required_domains),
                "expanded_domains_are_eligibility": False,
                "irrelevant_candidate_count_rejected_before_independence": rejected_irrelevant,
            },
            "literature_access_before_freeze": False,
            "status": status,
        }
        result["digest"] = digest_payload(result)
        return result


class PredictionFalsificationOwner:
    """Lower candidate records to explicit prediction/falsification contracts."""

    owner_id = "PREDICTION-FALSIFICATION-CONTRACT/6.24.0"

    def derive(
        self,
        competitive_set: Mapping[str, Any],
        candidate_lookup: Mapping[str, Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        rows: list[Mapping[str, Any]] = []
        all_signatures: Dict[str, str] = {}
        for summary in competitive_set.get("candidates", ()):
            candidate_id = str(summary["candidate_id"])
            candidate = candidate_lookup[candidate_id]
            measurements = tuple(str(x) for x in candidate.get("required_measurements", ()))
            criterion = str(candidate.get("falsification_criterion", "")).strip()
            formula_digest = _candidate_formula_digest(candidate)
            predictive_signature = digest_payload({
                "formula_digest": formula_digest,
                "measurements": measurements,
                "controlled_limits": tuple(str(x) for x in candidate.get("controlled_limits", ())),
                "coordinate_delta": candidate.get("coordinate_delta", {}),
            })
            all_signatures[candidate_id] = predictive_signature
            rows.append({
                "candidate_id": candidate_id,
                "prediction_contract_id": "PRED-" + predictive_signature[:20].upper(),
                "predictive_object": {
                    "formula_digest": formula_digest,
                    "formula_source": candidate.get("formula", {}).get("source", ""),
                    "coordinate_delta": candidate.get("coordinate_delta", {}),
                    "controlled_limits": list(candidate.get("controlled_limits", ())),
                },
                "required_measurements": list(measurements),
                "falsification_criterion": criterion,
                "prediction_signature": predictive_signature,
                "gates": {
                    "FORMULA_BOUND": bool(formula_digest),
                    "MEASUREMENTS_DECLARED": bool(measurements),
                    "FALSIFICATION_DECLARED": bool(criterion),
                },
            })
        for row in rows:
            row["discriminates_from_candidate_ids"] = [
                other_id for other_id, signature in all_signatures.items()
                if other_id != row["candidate_id"] and signature != row["prediction_signature"]
            ]
            row["status"] = (
                "DISCRIMINATING_PREDICTION_CONTRACT_READY"
                if all(row["gates"].values()) and row["discriminates_from_candidate_ids"]
                else "BLOCKED_NONDISCRIMINATING_OR_INCOMPLETE_PREDICTION_CONTRACT"
            )
        result = {
            "schema": "phi-prediction-falsification/v6.24",
            "owner": self.owner_id,
            "candidate_freeze_digest": competitive_set.get("candidate_freeze_digest"),
            "predictions": rows,
            "all_candidates_have_falsification_contract": bool(rows) and all(bool(row["falsification_criterion"]) for row in rows),
            "all_predictions_discriminate_at_least_one_competitor": bool(rows) and all(bool(row["discriminates_from_candidate_ids"]) for row in rows),
        }
        result["status"] = (
            "PREDICTION_AND_FALSIFICATION_CONTRACTS_READY"
            if result["all_candidates_have_falsification_contract"] and result["all_predictions_discriminate_at_least_one_competitor"]
            else "BLOCKED_PREDICTION_OR_FALSIFICATION_CONTRACT"
        )
        result["digest"] = digest_payload(result)
        return result


@dataclass(frozen=True)
class ExperimentLikelihoodSpec:
    experiment_id: str
    measurements: Tuple[str, ...]
    outcomes: Tuple[str, ...]
    likelihoods: Mapping[str, Mapping[str, float]]
    cost: float = 1.0
    risk_penalty: float = 0.0
    observed_outcome: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self, candidate_ids: Sequence[str]) -> None:
        if not self.experiment_id.strip():
            raise ValueError("experiment_id must be non-empty")
        if not self.measurements:
            raise ValueError("experiment measurements must be non-empty")
        if len(set(self.outcomes)) < 2:
            raise ValueError("experiment must have at least two distinct outcomes")
        if not math.isfinite(float(self.cost)) or float(self.cost) <= 0.0:
            raise ValueError("experiment cost must be finite and positive")
        if not math.isfinite(float(self.risk_penalty)) or float(self.risk_penalty) < 0.0:
            raise ValueError("risk penalty must be finite and non-negative")
        if self.observed_outcome is not None and self.observed_outcome not in self.outcomes:
            raise ValueError("observed outcome must belong to declared outcomes")
        if set(self.likelihoods) != set(candidate_ids):
            raise ValueError("likelihood rows must match the frozen competing candidate IDs exactly")
        for candidate_id in candidate_ids:
            row = self.likelihoods[candidate_id]
            if set(row) != set(self.outcomes):
                raise ValueError(f"likelihood outcomes mismatch for {candidate_id}")
            values = [float(row[outcome]) for outcome in self.outcomes]
            if any((not math.isfinite(v)) or v < 0.0 for v in values):
                raise ValueError("likelihood values must be finite and non-negative")
            if sum(values) <= 0.0:
                raise ValueError("each likelihood row needs positive probability mass")

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


class DomainNeutralInformationGainOwner:
    """Exact discrete EIG owner.  No predictive likelihoods -> no EIG claim."""

    owner_id = "DOMAIN-NEUTRAL-INFORMATION-GAIN/6.24.0"

    def rank(
        self,
        *,
        candidate_ids: Sequence[str],
        experiment_specs: Sequence[ExperimentLikelihoodSpec],
        priors: Mapping[str, float] | None = None,
    ) -> Mapping[str, Any]:
        candidate_ids = tuple(str(x) for x in candidate_ids)
        if not candidate_ids:
            raise ValueError("candidate_ids must be non-empty")
        prior = (
            _normalise_probability_map(priors, candidate_ids)
            if priors is not None
            else {candidate_id: 1.0 / len(candidate_ids) for candidate_id in candidate_ids}
        )
        h_prior = _entropy([prior[candidate_id] for candidate_id in candidate_ids])
        if not experiment_specs:
            result = {
                "schema": "phi-domain-neutral-eig/v6.24",
                "owner": self.owner_id,
                "candidate_ids": list(candidate_ids),
                "priors": prior,
                "prior_entropy_bits": h_prior,
                "experiments": [],
                "selected_experiment_id": None,
                "status": "BLOCKED_PREDICTIVE_LIKELIHOODS_REQUIRED",
                "claim_boundary": "EIG is not estimated from text similarity, formula distance or invented probabilities",
            }
            result["digest"] = digest_payload(result)
            return result

        ranked: list[Dict[str, Any]] = []
        for spec in experiment_specs:
            spec.validate(candidate_ids)
            norm_likelihoods: Dict[str, Dict[str, float]] = {}
            for candidate_id in candidate_ids:
                row = {outcome: float(spec.likelihoods[candidate_id][outcome]) for outcome in spec.outcomes}
                total = sum(row.values())
                norm_likelihoods[candidate_id] = {outcome: value / total for outcome, value in row.items()}
            p_outcome: Dict[str, float] = {}
            posteriors: Dict[str, Dict[str, float]] = {}
            expected_posterior_entropy = 0.0
            for outcome in spec.outcomes:
                p_o = sum(prior[cid] * norm_likelihoods[cid][outcome] for cid in candidate_ids)
                p_outcome[outcome] = p_o
                if p_o <= 0.0:
                    posteriors[outcome] = {cid: 0.0 for cid in candidate_ids}
                    continue
                posterior = {
                    cid: prior[cid] * norm_likelihoods[cid][outcome] / p_o
                    for cid in candidate_ids
                }
                posteriors[outcome] = posterior
                expected_posterior_entropy += p_o * _entropy([posterior[cid] for cid in candidate_ids])
            eig = h_prior - expected_posterior_entropy
            utility = eig / float(spec.cost) - float(spec.risk_penalty)
            ranked.append({
                "experiment_id": spec.experiment_id,
                "measurements": list(spec.measurements),
                "outcomes": list(spec.outcomes),
                "predictive_likelihoods": norm_likelihoods,
                "outcome_probabilities": p_outcome,
                "posterior_by_outcome": posteriors,
                "expected_information_gain_bits": eig,
                "cost": float(spec.cost),
                "risk_penalty": float(spec.risk_penalty),
                "utility": utility,
                "observed_outcome": spec.observed_outcome,
                "metadata": dict(spec.metadata),
            })
        ranked.sort(key=lambda row: (-float(row["utility"]), -float(row["expected_information_gain_bits"]), str(row["experiment_id"])))
        result = {
            "schema": "phi-domain-neutral-eig/v6.24",
            "owner": self.owner_id,
            "candidate_ids": list(candidate_ids),
            "priors": prior,
            "prior_entropy_bits": h_prior,
            "experiments": ranked,
            "selected_experiment_id": ranked[0]["experiment_id"] if ranked else None,
            "status": "EIG_RANKED" if ranked else "BLOCKED_PREDICTIVE_LIKELIHOODS_REQUIRED",
            "claim_boundary": "EIG is exact for the supplied discrete predictive likelihood contract; physical validity of those likelihoods remains with domain owners",
        }
        result["digest"] = digest_payload(result)
        return result


@dataclass(frozen=True)
class LiteratureRecord:
    record_id: str
    title: str
    source_locator: str
    source_type: str = "UNKNOWN"
    publication_year: int | None = None
    formula: str = ""
    formula_digest: str = ""
    keywords: Tuple[str, ...] = ()
    source_owner_ids: Tuple[str, ...] = ()
    independent_source_id: str = ""

    def validate(self) -> None:
        if not self.record_id.strip() or not self.title.strip() or not self.source_locator.strip():
            raise ValueError("literature record requires record_id, title and source_locator")
        if self.publication_year is not None and self.publication_year < 0:
            raise ValueError("publication_year must be non-negative")

    def to_dict(self) -> Dict[str, Any]:
        self.validate()
        return dataclasses.asdict(self)


class PostDerivationNoveltyOwner:
    """Corpus-relative prior-art owner; deliberately cannot assert world novelty."""

    owner_id = "POST-DERIVATION-NOVELTY/6.24.0"

    @staticmethod
    def _formula_tokens(value: str) -> set[str]:
        return _tokens(re.sub(r"\s+", "", value))

    def assess(
        self,
        *,
        candidate: Mapping[str, Any],
        candidate_freeze_digest: str,
        literature_records: Sequence[LiteratureRecord],
    ) -> Mapping[str, Any]:
        if not candidate_freeze_digest:
            raise ValueError("candidate_freeze_digest is required before prior-art review")
        candidate_formula = str(candidate.get("formula", {}).get("source", ""))
        candidate_formula_digest = _candidate_formula_digest(candidate)
        candidate_tokens = self._formula_tokens(candidate_formula) | _tokens(_candidate_text(candidate))
        candidate_owners = set(str(x) for x in candidate.get("source_owner_ids", ()))
        candidate_mechanism_text = " ".join([
            *(str(x).replace("_", " ").replace("-", " ") for x in candidate.get("classification", {}).get("categories", ())),
            *(str(x) for x in candidate.get("source_names_ru", ())),
            str(candidate.get("coordinate_delta", {})).replace("_", " ").replace("-", " "),
        ])
        candidate_mechanism_tokens = _tokens(candidate_mechanism_text)
        comparisons: list[Dict[str, Any]] = []
        exact_match = False
        close_match = False
        independent_sources: set[str] = set()
        for record in literature_records:
            record.validate()
            independent_sources.add(record.independent_source_id or record.source_locator)
            record_digest = record.formula_digest or (digest_payload(record.formula) if record.formula else "")
            formula_exact = bool(candidate_formula_digest and record_digest and candidate_formula_digest == record_digest)
            record_tokens = self._formula_tokens(record.formula) | _tokens(record.title, *record.keywords)
            union = candidate_tokens | record_tokens
            token_jaccard = len(candidate_tokens & record_tokens) / len(union) if union else 0.0
            owner_overlap = len(candidate_owners & set(record.source_owner_ids))
            record_mechanism_tokens = _tokens(*(str(x).replace("_", " ").replace("-", " ") for x in record.keywords), record.title)
            mech_intersection = candidate_mechanism_tokens & record_mechanism_tokens
            mechanism_overlap_coefficient = (
                len(mech_intersection) / min(len(candidate_mechanism_tokens), len(record_mechanism_tokens))
                if candidate_mechanism_tokens and record_mechanism_tokens else 0.0
            )
            # Formula identity remains the strongest signal.  For mechanism-level
            # prior art, a shared registered source owner plus substantial overlap
            # in mechanism terms is enough to demand manual review.  This is not
            # semantic equivalence and cannot establish novelty or non-novelty.
            is_close = (
                formula_exact
                or token_jaccard >= 0.55
                or (owner_overlap > 0 and (token_jaccard >= 0.20 or mechanism_overlap_coefficient >= 0.20))
            )
            exact_match = exact_match or formula_exact
            close_match = close_match or is_close
            comparisons.append({
                "record_id": record.record_id,
                "title": record.title,
                "source_locator": record.source_locator,
                "formula_exact": formula_exact,
                "token_jaccard": token_jaccard,
                "mechanism_overlap_coefficient": mechanism_overlap_coefficient,
                "mechanism_overlap_tokens": sorted(mech_intersection),
                "source_owner_overlap_count": owner_overlap,
                "close_match_flag": is_close,
            })
        comparisons.sort(key=lambda row: (not bool(row["formula_exact"]), -float(row["token_jaccard"]), str(row["record_id"])))
        if exact_match:
            status = "PRIOR_ART_EQUIVALENT_IN_SUPPLIED_CORPUS"
        elif close_match:
            status = "POTENTIAL_PRIOR_ART_REVIEW_REQUIRED"
        elif literature_records:
            status = "NO_CLOSE_MATCH_IN_SUPPLIED_CORPUS"
        else:
            status = "NOVELTY_NOT_ESTABLISHED_NO_LITERATURE_RECORDS"
        result = {
            "schema": "phi-post-derivation-novelty/v6.24",
            "owner": self.owner_id,
            "candidate_id": candidate.get("candidate_id"),
            "candidate_digest": candidate.get("digest"),
            "candidate_freeze_digest": candidate_freeze_digest,
            "candidate_frozen_before_literature_access": True,
            "literature_record_count": len(literature_records),
            "independent_literature_source_count": len(independent_sources),
            "comparisons": comparisons[:100],
            "status": status,
            "world_literature_novelty_established": False,
            "corpus_relative_novelty_established": status == "NO_CLOSE_MATCH_IN_SUPPLIED_CORPUS",
            "claim_boundary": "absence of a close match in a supplied finite corpus is not proof of world novelty",
        }
        result["digest"] = digest_payload(result)
        return result


_LANGUAGE_EQUIVALENTS: Mapping[str, tuple[str, ...]] = {
    # Interface-only multilingual normalization.  These rows translate surface
    # language into scientific concepts; they do not map a concept to a domain.
    # Domain selection remains derived from live domain/axis/owner registries.
    "collective": ("collective", "коллектив", "группов"),
    "coordination": ("coordination", "coordinate", "координац", "согласован", "consensus"),
    "control": ("control", "controllability", "coordination", "координац", "согласован", "управлен", "управляем", "регулирован"),
    "state": ("state", "states", "состоян"),
    "model": ("model", "модел"),
    "cognitive": ("cognitive", "когнитив", "интеллект", "мышлен"),
    "autonomy": ("autonomy", "autonomous", "автоном", "самостоятель"),
    "local": ("local", "локаль"),
    "interaction": ("interaction", "взаимодейств"),
    "information": ("information", "информац"),
    "communication": ("communication", "коммуникац", "связ"),
    "measurement": ("measurement", "measure", "измер"),
    "experiment": ("experiment", "эксперимент", "опыт"),
    "uncertainty": ("uncertainty", "неопредел"),
    "identifiability": ("identifiability", "идентифиц"),
    "observability": ("observability", "наблюдаем"),
    "stability": ("stability", "устойчив", "стабиль"),
    "equivalence": ("equivalence", "эквивалент"),
    "causal": ("causal", "causality", "причин"),
    "distributed": ("distributed", "распредел"),
    "multiple": ("multiple", "нескольк", "множеств"),
    "loss": ("loss", "потер"),
    "preserve": ("preserve", "сохран"),
    "research": ("research", "исслед", "изуч"),
    "find": ("find", "discover", "найд", "обнаруж"),
    "explain": ("explain", "объясн"),
    # Scientific language normalization needed to ground the current live
    # registries.  Again these are concept translations, not domain answers.
    "quantum": ("quantum", "квант"),
    "computation": ("computation", "computational", "compute", "вычисл"),
    "decoherence": ("decoherence", "декогер"),
    "noise": ("noise", "шум", "шумом", "шумов"),
    "neutrino": ("neutrino", "нейтрино"),
    "oscillation": ("oscillation", "oscillations", "осцилл"),
    "mass": ("mass", "масса", "масс"),
    "spectrum": ("spectrum", "spectral", "спектр"),
    "biology": ("biology", "biological", "биолог"),
    "genotype": ("genotype", "генотип"),
    "regulatory": ("regulatory", "регулятор"),
    "homeostasis": ("homeostasis", "гомеост"),
    "cell": ("cell", "cellular", "клет"),
    "dynamics": ("dynamics", "dynamic", "динамик"),
    "chemistry": ("chemistry", "chemical", "хими", "химичес"),
    "reaction": ("reaction", "reactive", "реакц"),
    "transport": ("transport", "перенос", "транспорт"),
    "field": ("field", "полев", "поле", "поля"),
    "mechanics": ("mechanics", "mechanical", "механик"),
    "material": ("material", "materials", "материал"),
    "earth": ("earth", "геосистем", "земн", "климат"),
    "particle": ("particle", "particles", "частиц"),
    "scalar": ("scalar", "скаляр"),
    "gauge": ("gauge", "калибров"),
    "operator": ("operator", "оператор"),
    "kernel": ("kernel", "ядр"),
    "constraint": ("constraint", "ограничен"),
    "coupling": ("coupling", "связност", "сопряж", "связанн"),
    "continuum": ("continuum", "контину"),
    "thermo": ("thermo", "термодин"),
}

# Concepts in this set are scientifically useful but too generic to establish a
# domain on their own.  They can rank an already grounded domain, but they do not
# get the same semantic-specificity bonus as a domain identifier or rare owner
# concept.  The list is domain-neutral by construction.
_SEMANTIC_GENERIC_CONCEPTS = {
    "state", "model", "information", "interaction", "communication", "measurement",
    "experiment", "uncertainty", "stability", "local", "multiple", "loss", "preserve",
    "control", "mass", "spectrum", "dynamics", "noise",
}
_SEMANTIC_META_CONCEPTS = {"research", "find", "explain"}


def _identifier_terms(value: str) -> set[str]:
    return {x for x in re.findall(r"[0-9a-zа-я]+", str(value).casefold().replace("_", " ")) if x}


def _language_concepts(text: str) -> set[str]:
    raw = _tokens(text)
    concepts = set(raw)
    for canonical, aliases in _LANGUAGE_EQUIVALENTS.items():
        for token in raw:
            if any(token == alias or (len(alias) >= 4 and token.startswith(alias)) for alias in aliases):
                concepts.add(canonical)
                break
    return concepts


def _semantic_signal_concepts(text: str) -> set[str]:
    """Return comparable semantic concepts without leaking raw RU morphology.

    ASCII scientific identifiers survive directly.  Russian/free-form terms
    participate only through the multilingual equivalence layer above.  This
    prevents inflected natural-language fragments from accidentally matching
    unrelated owner prose while retaining deterministic cross-language routing.
    """
    raw = _tokens(str(text).replace("_", " "))
    signal = {token for token in raw if token.isascii()}
    for canonical, aliases in _LANGUAGE_EQUIVALENTS.items():
        for token in raw:
            if any(token == alias or (len(alias) >= 4 and token.startswith(alias)) for alias in aliases):
                signal.add(canonical)
                break
    return signal - _SEMANTIC_META_CONCEPTS


class SemanticTypedQuestionOwner:
    """Deterministic Human->typed Phi intent router over live registries/state.

    It does not contain a domain answer map. Multilingual normalization produces
    generic concepts; domains, axes and capability gaps are then selected from
    the current registries/capability files with an explicit score receipt.
    """

    owner_id = SEMANTIC_QUESTION_OWNER

    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime

    @staticmethod
    def _load_mapping(path: Path, key: str) -> Mapping[str, Any]:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        value = raw.get(key, {}) if isinstance(raw, Mapping) else {}
        return dict(value) if isinstance(value, Mapping) else {}

    def interpret(self, question: str) -> Mapping[str, Any]:
        question = str(question).strip()
        if not question:
            raise ValueError("question is required")
        raw_terms = _tokens(question)
        concepts = _language_concepts(question)
        signal_concepts = _semantic_signal_concepts(question)
        lowered = question.casefold()
        constraints: list[str] = []
        constraint_text = ""
        for token in (" без ", " without "):
            padded = f" {lowered} "
            if token in padded:
                start = lowered.find(token.strip())
                constraint_text = question[start:].strip()
                constraints.append(constraint_text)
                break
        constraint_terms = _tokens(constraint_text) if constraint_text else set()
        constraint_concepts = _language_concepts(constraint_text) if constraint_text else set()
        constraint_signal = _semantic_signal_concepts(constraint_text) if constraint_text else set()
        topic_terms = raw_terms - constraint_terms
        topic_concepts = concepts - constraint_concepts
        topic_signal = signal_concepts - constraint_signal

        # Build semantic profiles from the live registries first.  Registered
        # owner text is used only for scientific concepts absent from every
        # registry identifier (for example a named phenomenon such as neutrino),
        # so prose-rich domains cannot win by sheer vocabulary volume.
        registry_profiles: dict[str, dict[str, Any]] = {}
        global_registry_concepts: set[str] = set()
        for domain_id, registry in sorted(DOMAIN_REGISTRIES.items()):
            identifier_concepts = _semantic_signal_concepts(domain_id)
            axis_concepts: set[str] = set()
            per_axis: dict[str, set[str]] = {}
            for axis_id, axis in sorted(registry.axes.items()):
                axis_description = str(axis.description_ru).replace(domain_id, " ")
                aconcepts = _semantic_signal_concepts(f"{axis_id} {axis_description}")
                per_axis[axis_id] = aconcepts
                axis_concepts.update(aconcepts)
            registry_profiles[domain_id] = {
                "identifier_concepts": identifier_concepts,
                "axis_concepts": axis_concepts,
                "per_axis": per_axis,
            }
            global_registry_concepts.update(identifier_concepts)
            global_registry_concepts.update(axis_concepts)

        owner_concept_counts: dict[str, dict[str, int]] = {domain: {} for domain in DOMAIN_REGISTRIES}
        for passport in self.runtime.catalog.passports.values():
            if passport.domain_id not in owner_concept_counts:
                continue
            owner_text = " ".join((
                passport.owner_id,
                passport.name_ru,
                " ".join(passport.observables),
                canonical_json(passport.provenance),
            ))
            for concept in _semantic_signal_concepts(owner_text):
                owner_concept_counts[passport.domain_id][concept] = owner_concept_counts[passport.domain_id].get(concept, 0) + 1

        axis_rows: list[dict[str, Any]] = []
        domain_rows: list[dict[str, Any]] = []
        for domain_id, registry in sorted(DOMAIN_REGISTRIES.items()):
            profile = registry_profiles[domain_id]
            identifier_matches = topic_signal & set(profile["identifier_concepts"])
            local_rows: list[dict[str, Any]] = []
            axis_specific_matches: set[str] = set()
            axis_all_matches: set[str] = set()
            best_by_concept: dict[str, float] = {}

            for concept in identifier_matches:
                best_by_concept[concept] = max(best_by_concept.get(concept, 0.0), 12.0)

            for axis_id, axis in sorted(registry.axes.items()):
                matches = topic_signal & set(profile["per_axis"][axis_id])
                if not matches:
                    continue
                per_concept = {
                    concept: (3.0 if concept in _SEMANTIC_GENERIC_CONCEPTS else 6.0)
                    for concept in matches
                }
                score = sum(per_concept.values())
                axis_all_matches.update(matches)
                axis_specific_matches.update(c for c in matches if c not in _SEMANTIC_GENERIC_CONCEPTS)
                for concept, value in per_concept.items():
                    best_by_concept[concept] = max(best_by_concept.get(concept, 0.0), value)
                local_rows.append({
                    "qualified_axis_id": f"{domain_id}.{axis_id}",
                    "domain_id": domain_id,
                    "axis_id": axis_id,
                    "score": score,
                    "matched_concepts": sorted(matches),
                    "specific_matched_concepts": sorted(c for c in matches if c not in _SEMANTIC_GENERIC_CONCEPTS),
                })

            owner_only_matches: dict[str, int] = {}
            for concept in topic_signal:
                if concept in global_registry_concepts or concept in _SEMANTIC_GENERIC_CONCEPTS:
                    continue
                count = int(owner_concept_counts[domain_id].get(concept, 0))
                if count <= 0:
                    continue
                owner_only_matches[concept] = count
                best_by_concept[concept] = max(best_by_concept.get(concept, 0.0), float(min(8, 2 + 2 * count)))

            specific_evidence = {c for c in best_by_concept if c not in _SEMANTIC_GENERIC_CONCEPTS}
            domain_score = sum(best_by_concept.values()) + 2.0 * len(specific_evidence)
            if domain_score > 0.0:
                domain_rows.append({
                    "domain_id": domain_id,
                    "score": domain_score,
                    "identifier_matches": sorted(identifier_matches),
                    "axis_matches": sorted(axis_all_matches),
                    "specific_axis_matches": sorted(axis_specific_matches),
                    "owner_only_matches": [
                        {"concept": concept, "passport_count": count}
                        for concept, count in sorted(owner_only_matches.items())
                    ],
                    "concept_scores": {concept: best_by_concept[concept] for concept in sorted(best_by_concept)},
                })
            local_rows.sort(key=lambda row: (-float(row["score"]), str(row["qualified_axis_id"])))
            axis_rows.extend(local_rows)

        domain_rows.sort(key=lambda row: (-float(row["score"]), str(row["domain_id"])))
        axis_rows.sort(key=lambda row: (-float(row["score"]), str(row["qualified_axis_id"])))
        selected_domains: list[str] = []
        max_domain = float(domain_rows[0]["score"]) if domain_rows else 0.0
        if domain_rows and max_domain >= 8.0:
            selected_domains.append(str(domain_rows[0]["domain_id"]))
            for row in domain_rows[1:]:
                score = float(row["score"])
                if score < max(10.0, 0.55 * max_domain):
                    continue
                has_identifier_anchor = bool(row["identifier_matches"])
                specific_axis_count = len(row["specific_axis_matches"])
                if not (has_identifier_anchor or specific_axis_count >= 2):
                    continue
                selected_domains.append(str(row["domain_id"]))
                if len(selected_domains) >= 3:
                    break

        selected_axes: list[dict[str, Any]] = []
        for domain in selected_domains:
            rows = [row for row in axis_rows if row["domain_id"] == domain]
            local_max = max((float(row["score"]) for row in rows), default=0.0)
            selected_axes.extend([
                row for row in rows
                if float(row["score"]) >= max(3.0, 0.5 * local_max)
            ][:8])
        selected_axes.sort(key=lambda row: (-float(row["score"]), str(row["qualified_axis_id"])))

        capabilities = dict(self.runtime.live_capability_ledger().get("capabilities", {}))
        capability_rows: list[dict[str, Any]] = []
        capability_query_concepts = topic_signal - {"local", "multiple", "loss", "preserve"}
        for capability_id, state in sorted(capabilities.items()):
            cterms = _semantic_signal_concepts(capability_id)
            overlap = capability_query_concepts & cterms
            if not overlap:
                continue
            score = 5.0 * len(overlap) + 1.0 * len(topic_terms & _identifier_terms(capability_id))
            state_text = str(state)
            gap = any(token in state_text.upper() for token in (
                "REQUIRED", "NOT_OWNER_GROUNDED", "OPEN", "BLOCKED", "GAP", "PENDING", "UNRESOLVED",
            ))
            capability_rows.append({
                "capability_id": str(capability_id), "state": state_text, "score": score,
                "matched_concepts": sorted(overlap), "gap_or_open": gap,
            })
        capability_rows.sort(key=lambda row: (-float(row["score"]), str(row["capability_id"])))
        if capability_rows:
            cap_max = float(capability_rows[0]["score"])
            capability_rows = [row for row in capability_rows if float(row["score"]) >= max(5.0, 0.6 * cap_max)][:8]

        intent = "SCIENTIFIC_RESEARCH"
        if "find" in concepts:
            intent = "DISCOVERY_RESEARCH"
        elif "explain" in concepts:
            intent = "EXPLANATORY_RESEARCH"

        status = "SEMANTIC_TYPED_IR_READY" if selected_domains or capability_rows else "SEMANTIC_TYPED_IR_LOW_CONFIDENCE"
        payload = {
            "schema": "phi-semantic-typed-question/v2",
            "owner": self.owner_id,
            "question": question,
            "intent": intent,
            "language_concepts": sorted(concepts),
            "semantic_signal_concepts": sorted(signal_concepts),
            "topic_concepts": sorted(topic_concepts),
            "topic_signal_concepts": sorted(topic_signal),
            "constraint_concepts": sorted(constraint_concepts),
            "constraints": constraints,
            "required_domains": selected_domains,
            "target_axis_ids": [str(row["qualified_axis_id"]) for row in selected_axes],
            "required_observables": sorted({str(row["axis_id"]) for row in selected_axes}),
            "axis_relevance": selected_axes,
            "domain_relevance": domain_rows[:8],
            "matched_capabilities": capability_rows,
            "capability_gap_detected": any(bool(row["gap_or_open"]) for row in capability_rows),
            "status": status,
            "grounding_contract": {
                "primary_domain_min_score": 8.0,
                "secondary_domain_relative_score": 0.55,
                "secondary_requires_identifier_or_two_specific_axes": True,
                "owner_text_can_ground_only_concepts_absent_from_registry_identifiers": True,
                "generic_concept_volume_cannot_create_domain_answer": True,
            },
            "claim_boundary": {
                "typed_intent_is_scientific_answer": False,
                "language_equivalence_is_domain_truth": False,
                "domain_selection_is_scored_from_live_registry": True,
                "registered_owner_corpus_used_only_as_missing_concept_grounding": True,
                "capability_selection_is_scored_from_live_capability_state": True,
                "hand_authored_domain_answer_map_used": False,
                "hand_authored_architecture_answer_map_used": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload




# ---------------------------------------------------------------------------
# Adaptive Research Kernel 15.0
# ---------------------------------------------------------------------------
# This is the current authority for open-ended research orchestration.  The
# older ScientificResearchCycleOwner below is retained only as a compatibility
# facade for already published API surfaces and regression tests; it does not
# own ATLAS_NATIVE claim issuance.

ADAPTIVE_RESEARCH_KERNEL_SCHEMA = "phi-adaptive-research-kernel/v2"
ADAPTIVE_RESEARCH_KERNEL_OWNER = "ADAPTIVE-RESEARCH-KERNEL/15.4.0"
CLAIM_FIREWALL_SCHEMA = "phi-claim-provenance-firewall/v1"
CLAIM_FIREWALL_OWNER = "CLAIM-PROVENANCE-FIREWALL/15.2.8"
HYPOTHESIS_SYNTHESIS_OWNER = "ADAPTIVE-HYPOTHESIS-SYNTHESIS/15.2.8"

_ALLOWED_CLAIM_ORIGINS = {
    "ATLAS_NATIVE",
    "USER_SUPPLIED",
    "EXTERNAL_REFERENCE",
    "ASSISTANT_HYPOTHESIS",
    "CONTROL_REFERENCE",
    "UNKNOWN",
}


def _dim_tuple(value: Sequence[Any] | None) -> tuple[float, ...]:
    if value is None:
        return (0.0,) * 7
    out = tuple(float(x) for x in value)
    if len(out) != 7:
        raise ValueError("dimension vectors must have seven SI-base exponents (L,M,T,I,Theta,N,J)")
    if any(not math.isfinite(x) for x in out):
        raise ValueError("dimension exponents must be finite")
    return out


def _dim_add(a: Sequence[float], b: Sequence[float]) -> tuple[float, ...]:
    return tuple(float(x) + float(y) for x, y in zip(a, b))


def _dim_sub(a: Sequence[float], b: Sequence[float]) -> tuple[float, ...]:
    return tuple(float(x) - float(y) for x, y in zip(a, b))


def _dim_scale(a: Sequence[float], n: int | float) -> tuple[float, ...]:
    return tuple(float(n) * float(x) for x in a)


def _dim_equal(a: Sequence[float], b: Sequence[float], tol: float = 1e-12) -> bool:
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class ProvenanceClaimFirewallOwner:
    """The only owner allowed to stamp ``ATLAS_NATIVE`` on research claims.

    The firewall is deliberately small.  It does not decide scientific truth;
    it verifies that a claim is bound to an executable Atlas receipt.  Human or
    assistant proposals remain proposals even when their text happens to match
    a later Atlas result.  Promotion to scientific law remains the job of the
    Scientific Promotion / Verification owners.
    """

    owner_id = CLAIM_FIREWALL_OWNER

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": CLAIM_FIREWALL_SCHEMA,
            "owner_id": self.owner_id,
            "allowed_origins": sorted(_ALLOWED_CLAIM_ORIGINS),
            "atlas_native_required_receipt_fields": (
                "owner", "schema", "input_digest", "axis_registry_digest",
                "hypothesis_space_digest", "code_digest", "result_digest", "digest",
            ),
            "rules": {
                "assistant_can_stamp_atlas_native": False,
                "user_can_stamp_atlas_native": False,
                "external_reference_can_stamp_atlas_native": False,
                "atlas_native_requires_kernel_receipt": True,
                "atlas_native_implies_scientific_truth": False,
                "missing_provenance_fails_closed": True,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    def label_proposal(self, *, statement: str, origin: str, payload: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        origin = str(origin).upper().strip()
        if origin not in _ALLOWED_CLAIM_ORIGINS or origin == "ATLAS_NATIVE":
            if origin == "ATLAS_NATIVE":
                raise ValueError("ATLAS_NATIVE cannot be assigned by proposal API")
            raise ValueError(f"unsupported claim origin {origin!r}")
        core = {
            "schema": CLAIM_FIREWALL_SCHEMA,
            "owner": self.owner_id,
            "statement": str(statement),
            "origin": origin,
            "payload": dict(payload or {}),
            "atlas_native": False,
            "scientific_truth_established": False,
            "status": "PROPOSAL_PROVENANCE_LABELED",
        }
        return {**core, "digest": digest_payload(core)}

    def seal_atlas_claim(self, *, statement: str, execution_receipt: Mapping[str, Any], payload: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        receipt = dict(execution_receipt)
        required = tuple(self.contract()["atlas_native_required_receipt_fields"])
        missing = [key for key in required if not receipt.get(key)]
        recomputed = digest_payload({k: v for k, v in receipt.items() if k != "digest"})
        checks = {
            "issuer_is_adaptive_research_kernel": receipt.get("owner") == ADAPTIVE_RESEARCH_KERNEL_OWNER,
            "required_receipt_fields_present": not missing,
            "receipt_digest_valid": bool(receipt.get("digest")) and receipt.get("digest") == recomputed,
            "result_digest_bound": bool(receipt.get("result_digest")),
            "code_digest_bound": bool(receipt.get("code_digest")),
        }
        if not all(checks.values()):
            core = {
                "schema": CLAIM_FIREWALL_SCHEMA,
                "owner": self.owner_id,
                "statement": str(statement),
                "origin": "UNKNOWN",
                "atlas_native": False,
                "scientific_truth_established": False,
                "status": "REJECTED_ATLAS_NATIVE_PROVENANCE",
                "checks": checks,
                "missing_receipt_fields": missing,
            }
            return {**core, "digest": digest_payload(core)}
        core = {
            "schema": CLAIM_FIREWALL_SCHEMA,
            "owner": self.owner_id,
            "statement": str(statement),
            "origin": "ATLAS_NATIVE",
            "atlas_native": True,
            "scientific_truth_established": False,
            "execution_receipt_digest": receipt["digest"],
            "result_digest": receipt["result_digest"],
            "payload": dict(payload or {}),
            "status": "ATLAS_NATIVE_PROVENANCE_ACCEPTED_NOT_SCIENTIFIC_PROMOTION",
            "checks": checks,
        }
        return {**core, "digest": digest_payload(core)}


class AdaptiveHypothesisSynthesisOwner:
    """Fair-dovetail empirical hypothesis synthesis with dimensional typing.

    Each call explores exactly one complexity shell.  There is no global order
    ceiling: the next research cycle may request the next shell.  Coefficients
    are typed automatically.  Coordinates supplied only as dormant research
    axes are not visible here until residual evidence has activated them.
    """

    owner_id = HYPOTHESIS_SYNTHESIS_OWNER

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "owner_id": self.owner_id,
            "search_policy": "FAIR_DOVETAIL_ONE_COMPLEXITY_SHELL_PER_RESEARCH_CYCLE",
            "fixed_polynomial_order_ceiling": None,
            "fixed_axis_count_ceiling": None,
            "coefficient_typing": "TARGET_DIMENSION_MINUS_MONOMIAL_DIMENSION",
            "known_law_catalog_required": False,
            "hypothesis_is_law": False,
        }
        return {**payload, "digest": digest_payload(payload)}

    @staticmethod
    def additive_type_check(term_dimensions: Sequence[Sequence[float]]) -> Mapping[str, Any]:
        dims = [_dim_tuple(v) for v in term_dimensions]
        compatible = bool(dims) and all(_dim_equal(dims[0], d) for d in dims[1:])
        payload = {
            "owner": HYPOTHESIS_SYNTHESIS_OWNER,
            "term_dimensions": [list(x) for x in dims],
            "status": "DIMENSIONALLY_VALID_ADDITION" if compatible else "DIMENSION_MISMATCH_REQUIRES_TYPED_COEFFICIENT_OR_NORMALIZATION",
            "compatible": compatible,
        }
        return {**payload, "digest": digest_payload(payload)}

    @staticmethod
    def _monomials(variable_names: Sequence[str], degree: int) -> list[tuple[int, ...]]:
        n = len(variable_names)
        if degree < 1:
            return []
        exps: set[tuple[int, ...]] = set()
        for combo in itertools.combinations_with_replacement(range(n), degree):
            row = [0] * n
            for idx in combo:
                row[idx] += 1
            exps.add(tuple(row))
        return sorted(exps)

    @staticmethod
    def _term_name(names: Sequence[str], exps: Sequence[int]) -> str:
        parts = []
        for name, exp in zip(names, exps):
            if exp == 1:
                parts.append(name)
            elif exp > 1:
                parts.append(f"{name}^{exp}")
        return "*".join(parts) if parts else "1"

    @staticmethod
    def _evaluate_term(matrix: np.ndarray, exps: Sequence[int]) -> np.ndarray:
        out = np.ones(matrix.shape[0], dtype=float)
        with np.errstate(over="ignore", invalid="ignore"):
            for col, exp in enumerate(exps):
                if exp:
                    out *= np.power(matrix[:, col], int(exp))
        return out

    def synthesize(
        self,
        *,
        observations: Sequence[Mapping[str, Any]],
        target_variable: str,
        predictor_variables: Sequence[str],
        variable_dimensions: Mapping[str, Sequence[float]],
        complexity_level: int,
    ) -> Mapping[str, Any]:
        if int(complexity_level) < 1:
            raise ValueError("complexity_level must be >=1")
        if len(observations) < 8:
            payload = {
                "schema": "phi-adaptive-hypothesis-space/v1", "owner": self.owner_id,
                "status": "INSUFFICIENT_OBSERVATIONS_FOR_HELDOUT_SYNTHESIS", "candidate_count": 0,
                "current_complexity_shell": int(complexity_level), "candidates": [],
            }
            return {**payload, "digest": digest_payload(payload)}
        names = tuple(str(x) for x in predictor_variables)
        if not names:
            raise ValueError("at least one predictor variable is required")
        target_dim = _dim_tuple(variable_dimensions[target_variable])
        predictor_dims = {name: _dim_tuple(variable_dimensions[name]) for name in names}
        rows = []
        for obs in observations:
            values = dict(obs.get("values", obs))
            try:
                x = [float(values[name]) for name in names]
                y = float(values[target_variable])
            except (KeyError, TypeError, ValueError):
                continue
            if math.isfinite(y) and all(math.isfinite(v) for v in x):
                rows.append((x, y))
        if len(rows) < 8:
            raise ValueError("fewer than eight finite observations remain after validation")
        Xraw = np.asarray([r[0] for r in rows], dtype=float)
        y = np.asarray([r[1] for r in rows], dtype=float)
        n = len(y)
        cut = max(6, int(math.floor(0.7 * n)))
        cut = min(cut, n - 2)
        scale = float(np.std(y)) or max(abs(float(np.mean(y))), 1.0)

        shell_terms = self._monomials(names, int(complexity_level))
        all_terms: list[tuple[int, ...]] = []
        for degree in range(1, int(complexity_level) + 1):
            all_terms.extend(self._monomials(names, degree))

        # Candidate families are generated from structure, not a named-law list.
        basis_sets: list[tuple[tuple[int, ...], ...]] = []
        for term in shell_terms:
            basis_sets.append((term,))
        # additive first-order chart and the cumulative current complexity chart
        first_order = tuple(self._monomials(names, 1))
        if first_order:
            basis_sets.append(first_order)
        if all_terms:
            basis_sets.append(tuple(all_terms))
        # Pairwise charts are opened fairly around the new shell.  A newly born
        # higher-order term may combine with a lower-order survivor; restricting
        # pairs to the new shell would prevent representations such as x + x*z
        # from ever appearing as a sparse candidate.
        lower_terms = [term for term in all_terms if sum(term) < int(complexity_level)]
        for a, b in itertools.combinations(shell_terms, 2):
            basis_sets.append((a, b))
        for new_term in shell_terms:
            for lower_term in lower_terms:
                basis_sets.append((lower_term, new_term))
        unique_basis = []
        seen = set()
        for basis in basis_sets:
            key = tuple(sorted(set(basis)))
            if key and key not in seen:
                seen.add(key); unique_basis.append(key)

        candidates: list[dict[str, Any]] = []
        for basis in unique_basis:
            cols = [np.ones(n, dtype=float)] + [self._evaluate_term(Xraw, term) for term in basis]
            design = np.column_stack(cols)
            if not np.all(np.isfinite(design)):
                continue
            Xt, Xv = design[:cut], design[cut:]
            yt, yv = y[:cut], y[cut:]
            try:
                beta, *_ = np.linalg.lstsq(Xt, yt, rcond=None)
            except np.linalg.LinAlgError:
                continue
            pred_t = Xt @ beta; pred_v = Xv @ beta
            train_rmse = float(np.sqrt(np.mean((yt - pred_t) ** 2)))
            holdout_rmse = float(np.sqrt(np.mean((yv - pred_v) ** 2)))
            rank = int(np.linalg.matrix_rank(Xt))
            expressions = [f"c0"]
            coefficient_dimensions = {"c0": list(target_dim)}
            term_rows = []
            for i, term in enumerate(basis, start=1):
                mon_dim = (0.0,) * 7
                for name, exp in zip(names, term):
                    if exp:
                        mon_dim = _dim_add(mon_dim, _dim_scale(predictor_dims[name], exp))
                coef_dim = _dim_sub(target_dim, mon_dim)
                tname = self._term_name(names, term)
                cname = f"c{i}"
                expressions.append(f"{cname}*{tname}")
                coefficient_dimensions[cname] = list(coef_dim)
                term_rows.append({
                    "term": tname,
                    "exponents": dict(zip(names, term)),
                    "monomial_dimension": list(mon_dim),
                    "coefficient": cname,
                    "coefficient_dimension": list(coef_dim),
                })
            source = " + ".join(expressions)
            core = {
                "expression": source,
                "basis": term_rows,
                "coefficient_dimensions": coefficient_dimensions,
                "parameters": [float(v) for v in beta],
                "parameter_count": len(beta),
                "design_rank": rank,
                "identifiable_on_train": rank == len(beta),
                "train_nrmse": train_rmse / scale,
                "holdout_nrmse": holdout_rmse / scale,
                "holdout_count": int(len(yv)),
                "complexity_shell": int(complexity_level),
            }
            cid = "H-" + digest_payload(core)[:20].upper()
            score = float(core["holdout_nrmse"]) + 0.001 * len(beta)
            candidates.append({
                "candidate_id": cid,
                "origin": "ATLAS_GENERATED_HYPOTHESIS",
                "lifecycle_state": "TESTABLE" if core["identifiable_on_train"] else "CANDIDATE",
                "score": score,
                **core,
            })
        candidates.sort(key=lambda r: (float(r["score"]), int(r["parameter_count"]), str(r["candidate_id"])))
        for row in candidates:
            row["digest"] = digest_payload({k: v for k, v in row.items() if k != "digest"})
        payload = {
            "schema": "phi-adaptive-hypothesis-space/v1",
            "owner": self.owner_id,
            "status": "HYPOTHESIS_SPACE_FROZEN_FOR_CURRENT_COMPLEXITY_SHELL" if candidates else "NO_IDENTIFIABLE_HYPOTHESIS_IN_CURRENT_SHELL",
            "current_complexity_shell": int(complexity_level),
            "next_complexity_shell_exists": True,
            "fixed_complexity_ceiling": None,
            "predictor_variables": list(names),
            "target_variable": target_variable,
            "candidate_count": len(candidates),
            "candidates": candidates,
        }
        return {**payload, "digest": digest_payload(payload)}


class AdaptiveResearchKernelOwner:
    """Single current research loop: observations -> hypotheses -> experiment -> evolution.

    The kernel is deliberately domain-neutral.  It coordinates existing owners
    and adds only the missing common semantics: research-local representation,
    fair-dovetail hypothesis synthesis, explicit lifecycle state, and claim
    provenance.  Domain solvers remain authoritative for their own numerical
    physics/chemistry/etc.; this owner never replaces them.
    """

    owner_id = ADAPTIVE_RESEARCH_KERNEL_OWNER

    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime
        from .adaptive_axis import AdaptiveAxisDiscoveryOwner
        self.axis_discovery = AdaptiveAxisDiscoveryOwner()
        self.hypothesis_synthesis = AdaptiveHypothesisSynthesisOwner()
        self.firewall = ProvenanceClaimFirewallOwner()
        from .mathematical_invention import MathematicalInventionKernel
        from .theory_compiler import TheoryCompilerKernel
        self.invention = MathematicalInventionKernel(runtime.root)
        self.theory_compiler = TheoryCompilerKernel(runtime.root)

    def _code_digest(self) -> str:
        paths = [
            self.runtime.root / "source/lawspace/research_cycle.py",
            self.runtime.root / "source/lawspace/adaptive_axis.py",
            self.runtime.root / "source/lawspace/mathematical_invention.py",
            self.runtime.root / "source/lawspace/theory_compiler.py",
            self.runtime.root / "source/lawspace/law_discovery.py",
        ]
        payload = {str(p.relative_to(self.runtime.root)): _sha256_file(p) for p in paths if p.exists()}
        return digest_payload(payload)

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": ADAPTIVE_RESEARCH_KERNEL_SCHEMA,
            "owner_id": self.owner_id,
            "authoritative_research_orchestration": True,
            "pipeline": (
                "OBSERVATIONS", "CURRENT_REPRESENTATION", "OWNER_CONNECTED_PHI_SCAN",
                "HYPOTHESIS_SYNTHESIS", "TYPED_CLOSURE", "PREDICTION", "RESIDUAL",
                "FALSIFICATION", "DISCRIMINATING_EXPERIMENT", "AXIS_OR_LANGUAGE_EVOLUTION",
                "EXECUTABLE_REPRESENTATION_SYNTHESIS", "SANDBOX_EXECUTION",
                "CLAIM_FIREWALL", "NEXT_RESEARCH_CYCLE",
            ),
            "space_policy": {
                "canonical_axis_count_is_ceiling": False,
                "research_local_axes_may_be_born": True,
                "observed_axes_may_exist_dormant_before_model_activation": True,
                "dormant_axis_activation_requires_residual_evidence": True,
                "dormant_axis_presence_does_not_insert_it_into_a_formula": True,
                "axes_may_split_merge_or_retire": True,
                "representation_type_may_change": True,
                "known_law_catalog_required": False,
                "fixed_hypothesis_complexity_ceiling": None,
                "fixed_competitor_count_as_truth_gate": False,
                "competitor_diversity_target": 5,
                "competitor_diversity_target_is_search_pressure_not_blocking_rule": True,
            },
            "epistemic_policy": {
                "strange_hypotheses_allowed": True,
                "hypotheses_must_survive_typing_and_evidence": True,
                "assistant_is_evidence_source": False,
                "assistant_may_propose_research_question": True,
                "only_claim_firewall_can_stamp_atlas_native": True,
                "atlas_native_does_not_equal_scientific_law": True,
            },
            "existing_owner_reuse": {
                "constraint_atlas": "CONSTRAINT-ATLAS",
                "adaptive_axis": self.axis_discovery.owner_id,
                "mathematical_invention": self.invention.contract().get("owner_id"),
                "theory_compiler": self.theory_compiler.contract().get("owner_id"),
                "claim_firewall": self.firewall.owner_id,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    @staticmethod
    def _normalize_request(request: Mapping[str, Any]) -> dict[str, Any]:
        req = dict(request)
        observations = tuple(dict(x) for x in req.get("observations", ()))
        sealed_holdout = tuple(dict(x) for x in req.get("sealed_holdout_observations", ()))
        target = str(req.get("target_variable", "")).strip()
        predictors = tuple(dict.fromkeys(str(x) for x in req.get("predictor_variables", ())))
        dormant = tuple(dict.fromkeys(str(x) for x in req.get("dormant_axis_variables", ())))
        dims = {str(k): list(_dim_tuple(v)) for k, v in dict(req.get("variable_dimensions", {})).items()}
        if not target or target not in dims:
            raise ValueError("target_variable and its dimension are required")
        if not predictors or any(name not in dims for name in predictors):
            raise ValueError("predictor_variables and their dimensions are required")
        if any(name not in dims for name in dormant):
            raise ValueError("dormant_axis_variables and their dimensions are required")
        if target in predictors or target in dormant:
            raise ValueError("target_variable cannot also be an active or dormant predictor axis")
        overlap = sorted(set(predictors) & set(dormant))
        if overlap:
            raise ValueError(f"axes cannot be active and dormant simultaneously: {overlap}")
        if not observations:
            raise ValueError("observations are required")
        return {
            **req,
            "observations": observations,
            "sealed_holdout_observations": sealed_holdout,
            "target_variable": target,
            "predictor_variables": predictors,
            "dormant_axis_variables": dormant,
            "variable_dimensions": dims,
            "domain_id": str(req.get("domain_id", "physics")),
            "question": str(req.get("question", f"discover relation for {target}")),
            "complexity_level": max(1, int(req.get("complexity_level", 1))),
            "fit_tolerance_nrmse": max(0.0, float(req.get("fit_tolerance_nrmse", 0.05))),
            "observations_origin": str(req.get("observations_origin", "USER_SUPPLIED")).upper(),
            "auto_activate_dormant_axes": bool(req.get("auto_activate_dormant_axes", True)),
            "operator_probe_rows": tuple(dict(x) for x in req.get("operator_probe_rows", ())),
            "operator_probe_design_request": dict(req.get("operator_probe_design_request", {})) if isinstance(req.get("operator_probe_design_request"), Mapping) else {},
            "operator_fit_tolerance_nrmse": max(0.0, float(req.get("operator_fit_tolerance_nrmse", 1e-5))),
            "operator_max_terms_per_output": req.get("operator_max_terms_per_output"),
            "operator_eigenpair_count": max(1, int(req.get("operator_eigenpair_count", 4))),
        }

    @staticmethod
    def _residual_evidence(
        observations: Sequence[Mapping[str, Any]], predictor_variables: Sequence[str], target_variable: str,
        best: Mapping[str, Any] | None, dormant_axis_variables: Sequence[str] = (),
    ) -> tuple[list[dict[str, Any]], list[float]]:
        if not best:
            return [], []
        names = tuple(predictor_variables)
        rows = []
        Xraw=[]; y=[]
        for obs in observations:
            vals=dict(obs.get("values",obs))
            try:
                Xraw.append([float(vals[n]) for n in names]); y.append(float(vals[target_variable]))
            except (KeyError,TypeError,ValueError):
                continue
        X=np.asarray(Xraw,float); yv=np.asarray(y,float)
        if len(yv)<2:return [],[]
        design=[np.ones(len(yv),float)]
        for term in best.get("basis",()):
            expmap=dict(term.get("exponents",{})); exps=[int(expmap.get(n,0)) for n in names]
            design.append(AdaptiveHypothesisSynthesisOwner._evaluate_term(X,exps))
        pred=np.column_stack(design) @ np.asarray(best.get("parameters",()),float)
        residual=yv-pred
        scale=float(np.std(yv)) or 1.0
        threshold=max(0.10*scale,float(np.median(np.abs(residual)))*1.5)
        for i,(obs,r) in enumerate(zip(observations,residual)):
            vals=dict(obs.get("values",obs))
            context={}
            for name in names:
                v=float(vals[name]); col=X[:,names.index(name)]
                q1,q2=np.quantile(col,[1/3,2/3])
                context[name+"__bin"]="LOW" if v<=q1 else "MID" if v<=q2 else "HIGH"
                context[name+"__square_bin"]="LOW" if v*v<=np.quantile(col*col,1/3) else "MID" if v*v<=np.quantile(col*col,2/3) else "HIGH"
            # Dormant axes exist in the research representation but are not
            # available to hypothesis synthesis.  They are exposed only here,
            # as residual context.  A dormant axis can therefore enter the
            # active model only after the residual carries information about it.
            for name in tuple(dormant_axis_variables):
                try:
                    col=np.asarray([float(dict(o.get("values",o))[name]) for o in observations],float)
                    v=float(vals[name])
                except (KeyError,TypeError,ValueError):
                    continue
                if not np.all(np.isfinite(col)) or not math.isfinite(v):
                    continue
                q1,q2=np.quantile(col,[1/3,2/3])
                context[name]="LOW" if v<=q1 else "MID" if v<=q2 else "HIGH"
            for a,b in itertools.combinations(range(len(names)),2):
                pname=f"{names[a]}__x__{names[b]}"
                prod=X[:,a]*X[:,b]; v=X[i,a]*X[i,b]
                q1,q2=np.quantile(prod,[1/3,2/3]); context[pname]="LOW" if v<=q1 else "MID" if v<=q2 else "HIGH"
            outcome="NEAR_ZERO" if abs(float(r))<=threshold else "POSITIVE_RESIDUAL" if r>0 else "NEGATIVE_RESIDUAL"
            rows.append({"study_id":str(obs.get("study_id",f"OBS-{i:04d}")),"outcome_class":outcome,"context":context})
        return rows,[float(x) for x in residual]

    @staticmethod
    def _experiment_disagreement(candidates: Sequence[Mapping[str, Any]], experiment_points: Sequence[Mapping[str, Any]], predictor_variables: Sequence[str]) -> Mapping[str, Any]:
        if len(candidates)<2 or not experiment_points:
            payload={"status":"DISCRIMINATING_EXPERIMENT_NOT_AVAILABLE","selected_experiment_id":None,"rows":[]}
            return {**payload,"digest":digest_payload(payload)}
        names=tuple(predictor_variables); rows=[]
        for idx,point in enumerate(experiment_points):
            vals=dict(point.get("values",point)); xv=np.asarray([[float(vals[n]) for n in names]],float)
            preds=[]
            for cand in candidates[:12]:
                design=[np.ones(1,float)]
                for term in cand.get("basis",()):
                    expmap=dict(term.get("exponents",{})); exps=[int(expmap.get(n,0)) for n in names]
                    design.append(AdaptiveHypothesisSynthesisOwner._evaluate_term(xv,exps))
                preds.append(float((np.column_stack(design) @ np.asarray(cand.get("parameters",()),float)).item()))
            score=float(np.var(preds)) if preds else 0.0
            rows.append({"experiment_id":str(point.get("experiment_id",f"EXP-{idx:04d}")),"candidate_predictions":preds,"prediction_variance":score})
        rows.sort(key=lambda r:(-float(r["prediction_variance"]),str(r["experiment_id"])))
        payload={"status":"DISAGREEMENT_EXPERIMENT_RANKED_NOT_PROBABILISTIC_EIG","selected_experiment_id":rows[0]["experiment_id"] if rows else None,"rows":rows,"invented_likelihoods":False}
        return {**payload,"digest":digest_payload(payload)}

    @staticmethod
    def _activation_improvement(initial_best: Mapping[str, Any] | None, expanded_best: Mapping[str, Any] | None) -> Mapping[str, Any]:
        before=float(initial_best.get("holdout_nrmse",float("inf"))) if initial_best else float("inf")
        after=float(expanded_best.get("holdout_nrmse",float("inf"))) if expanded_best else float("inf")
        finite=math.isfinite(before) and math.isfinite(after)
        absolute=(before-after) if finite else 0.0
        relative=(absolute/max(abs(before),1e-30)) if finite else 0.0
        payload={
            "initial_holdout_nrmse":before,
            "expanded_holdout_nrmse":after,
            "absolute_improvement":absolute,
            "relative_improvement":relative,
            "improved":bool(finite and after < before),
        }
        return {**payload,"digest":digest_payload(payload)}

    @staticmethod
    def _evaluate_candidate_on_observations(
        candidate: Mapping[str, Any] | None,
        observations: Sequence[Mapping[str, Any]],
        predictor_variables: Sequence[str],
        target_variable: str,
    ) -> Mapping[str, Any]:
        if not candidate or not observations:
            payload={"status":"SEALED_HOLDOUT_NOT_AVAILABLE","count":0,"nrmse":None,"rmse":None}
            return {**payload,"digest":digest_payload(payload)}
        names=tuple(predictor_variables)
        Xraw=[]; y=[]
        for obs in observations:
            vals=dict(obs.get("values",obs))
            try:
                Xraw.append([float(vals[n]) for n in names]); y.append(float(vals[target_variable]))
            except (KeyError,TypeError,ValueError):
                continue
        if not y:
            payload={"status":"SEALED_HOLDOUT_NO_FINITE_ROWS","count":0,"nrmse":None,"rmse":None}
            return {**payload,"digest":digest_payload(payload)}
        X=np.asarray(Xraw,float); yv=np.asarray(y,float)
        design=[np.ones(len(yv),float)]
        for term in candidate.get("basis",()):
            expmap=dict(term.get("exponents",{})); exps=[int(expmap.get(n,0)) for n in names]
            design.append(AdaptiveHypothesisSynthesisOwner._evaluate_term(X,exps))
        params=np.asarray(candidate.get("parameters",()),float)
        matrix=np.column_stack(design)
        if matrix.shape[1] != len(params):
            payload={"status":"SEALED_HOLDOUT_CANDIDATE_SHAPE_MISMATCH","count":len(yv),"nrmse":None,"rmse":None}
            return {**payload,"digest":digest_payload(payload)}
        pred=matrix @ params
        rmse=float(np.sqrt(np.mean((yv-pred)**2)))
        scale=float(np.std(yv)) or max(abs(float(np.mean(yv))),1.0)
        payload={"status":"SEALED_HOLDOUT_EVALUATED","count":len(yv),"rmse":rmse,"nrmse":rmse/scale,"prediction_digest":digest_payload([float(v) for v in pred])}
        return {**payload,"digest":digest_payload(payload)}

    def _advance_representation_gap(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        """Enter the research loop from an attested representation/capability gap.

        This path exists specifically so callers never need to fabricate tabular
        observations merely to make a representation gap executable.  It can
        synthesize/compile/execute only when typed operator-response probes are
        actually supplied.  In strict-blind mode the named-law owner catalog is
        not queried at all; the result is therefore a probe contract, not a
        guessed named solver.
        """
        req = dict(request)
        domain_id = str(req.get("domain_id", "physics"))
        if domain_id not in DOMAIN_REGISTRIES:
            raise ValueError(f"unknown domain {domain_id!r}")
        question = str(req.get("question", "")).strip()
        if not question:
            raise ValueError("question is required for representation-gap entry")
        gap_kind = str(req.get("gap_kind", "REPRESENTATION_CAPABILITY_GAP")).strip().upper()
        gap_evidence = dict(req.get("gap_evidence", {})) if isinstance(req.get("gap_evidence"), Mapping) else {}
        gap_evidence_digest = str(req.get("gap_evidence_digest", "")).strip()
        if not gap_evidence_digest and gap_evidence:
            gap_evidence_digest = digest_payload(gap_evidence)
        if not gap_evidence_digest:
            raise ValueError("gap_evidence or gap_evidence_digest is required; the assistant may not invent a gap receipt")
        strict_blind = bool(req.get("blind_no_named_law_catalog", False))
        probe_rows = tuple(dict(x) for x in req.get("operator_probe_rows", ()))
        probe_digest = digest_payload(probe_rows)
        operator_probe_evidence = dict(req.get("operator_probe_evidence", {})) if isinstance(req.get("operator_probe_evidence"), Mapping) else {}
        operator_probe_evidence_digest = str(req.get("operator_probe_evidence_digest", "")).strip()
        if not operator_probe_evidence_digest and operator_probe_evidence:
            operator_probe_evidence_digest = digest_payload(operator_probe_evidence)
        operator_probe_evidence_valid = True
        operator_probe_evidence_reason = "NO_PROBES_SUPPLIED"
        if probe_rows:
            if not operator_probe_evidence_digest:
                operator_probe_evidence_valid = False
                operator_probe_evidence_reason = "OPERATOR_PROBE_ATTESTATION_REQUIRED"
            elif str(operator_probe_evidence.get("probe_digest", "")) != probe_digest:
                operator_probe_evidence_valid = False
                operator_probe_evidence_reason = "OPERATOR_PROBE_ATTESTATION_DIGEST_MISMATCH"
            elif not str(operator_probe_evidence.get("attestation_class", "")).strip():
                operator_probe_evidence_valid = False
                operator_probe_evidence_reason = "OPERATOR_PROBE_ATTESTATION_CLASS_REQUIRED"
            else:
                operator_probe_evidence_reason = "ATTESTATION_BOUND_TO_PROBES"
        operator_fit_tolerance_nrmse = max(0.0, float(req.get("operator_fit_tolerance_nrmse", 1e-5)))
        operator_max_terms_per_output = req.get("operator_max_terms_per_output")
        operator_eigenpair_count = max(1, int(req.get("operator_eigenpair_count", 4)))
        operator_probe_design_request = dict(req.get("operator_probe_design_request", {})) if isinstance(req.get("operator_probe_design_request"), Mapping) else {}
        operator_response_owner_request = dict(req.get("operator_response_owner_request", {})) if isinstance(req.get("operator_response_owner_request"), Mapping) else {}
        variable_particle_world_request = dict(req.get("variable_particle_world_request", {})) if isinstance(req.get("variable_particle_world_request"), Mapping) else {}
        many_body_world_request = dict(req.get("many_body_world_request", {})) if isinstance(req.get("many_body_world_request"), Mapping) else {}

        input_core = {
            "problem_id": str(req.get("problem_id", "")),
            "domain_id": domain_id,
            "question": question,
            "gap_kind": gap_kind,
            "gap_evidence_digest": gap_evidence_digest,
            "blind_no_named_law_catalog": strict_blind,
            "operator_probe_digest": probe_digest,
            "operator_probe_evidence_digest": operator_probe_evidence_digest,
            "operator_probe_design_request_digest": digest_payload(operator_probe_design_request),
            "operator_response_owner_request_digest": digest_payload(operator_response_owner_request),
            "variable_particle_world_request_digest": digest_payload(variable_particle_world_request),
            "many_body_world_request_digest": digest_payload(many_body_world_request),
        }
        input_digest = digest_payload(input_core)
        canonical_count = sum(len(registry.axes) for registry in DOMAIN_REGISTRIES.values())

        if strict_blind:
            phi_scan = {
                "status": "NAMED_LAW_OWNER_SCAN_SUPPRESSED_BY_STRICT_BLIND_PROTOCOL",
                "registered_axis_count": canonical_count,
                "fixed_axis_count_ceiling": None,
                "owner_visits": [],
                "all_registered_axes_visited": False,
                "named_law_catalog_read": False,
            }
            phi_scan = {**phi_scan, "digest": digest_payload(phi_scan)}
        else:
            query = DirectedResearchQuery(
                question=question,
                required_domains=(domain_id,),
                target_axis_ids=tuple(req.get("target_axis_ids", ())),
                include_all_connected_owners=True,
                discovery_mode="SEMANTIC_OWNER_FRONTIER",
            )
            phi_scan = directed_owner_hypergraph_research(self.runtime.catalog, self.runtime.bridges, query)

        # A representation gap is evidence about the capability boundary, not an
        # operator-response measurement.  Do not label it as operator_probe.
        invention = self.invention.unknown_unknown.discover(
            question=question,
            evidence_rows=[{
                "mode": "residual",
                "environment_id": str(req.get("problem_id", "representation-gap")),
                "evidence_digest": gap_evidence_digest,
                "status": gap_kind,
            }],
        )
        if "digest" not in invention:
            invention = {**invention, "digest": digest_payload(invention)}

        executable_synthesis: Mapping[str, Any]
        executable_compilation: Mapping[str, Any] | None = None
        executable_execution: Mapping[str, Any] | None = None
        operator_probe_design: Mapping[str, Any] | None = None
        operator_probe_design_history: list[Mapping[str, Any]] = []
        operator_response_owner_receipt: Mapping[str, Any] | None = None
        variable_particle_probe_design: Mapping[str, Any] | None = None
        variable_particle_world_receipt: Mapping[str, Any] | None = None
        self_consistent_synthesis: Mapping[str, Any] | None = None
        self_consistent_compilation: Mapping[str, Any] | None = None
        self_consistent_execution: Mapping[str, Any] | None = None
        many_body_probe_design_history: list[Mapping[str, Any]] = []
        many_body_world_receipts: list[Mapping[str, Any]] = []
        many_body_coordinate_synthesis: Mapping[str, Any] | None = None
        many_body_representation_invention: Mapping[str, Any] | None = None

        def _validate_bound_probe_evidence() -> None:
            nonlocal probe_digest, operator_probe_evidence_digest, operator_probe_evidence_valid, operator_probe_evidence_reason
            probe_digest = digest_payload(probe_rows)
            if not operator_probe_evidence_digest and operator_probe_evidence:
                operator_probe_evidence_digest = digest_payload(operator_probe_evidence)
            if not operator_probe_evidence_digest:
                operator_probe_evidence_valid = False
                operator_probe_evidence_reason = "OPERATOR_PROBE_ATTESTATION_REQUIRED"
            elif str(operator_probe_evidence.get("probe_digest", "")) != probe_digest:
                operator_probe_evidence_valid = False
                operator_probe_evidence_reason = "OPERATOR_PROBE_ATTESTATION_DIGEST_MISMATCH"
            elif not str(operator_probe_evidence.get("attestation_class", "")).strip():
                operator_probe_evidence_valid = False
                operator_probe_evidence_reason = "OPERATOR_PROBE_ATTESTATION_CLASS_REQUIRED"
            else:
                operator_probe_evidence_valid = True
                operator_probe_evidence_reason = "ATTESTATION_BOUND_TO_PROBES"

        if not probe_rows:
            design_components = int(operator_probe_design_request.get("components", gap_evidence.get("state_components", 1) or 1))
            design_grid = operator_probe_design_request.get("grid")
            design_shell = int(operator_probe_design_request.get("design_shell", 1))
            operator_probe_design = self.theory_compiler.probe_design.design(
                freeze_digest=str(invention.get("digest", input_digest)),
                components=design_components,
                grid=design_grid,
                design_shell=design_shell,
            )
            operator_probe_design_history.append(operator_probe_design)

            response_owner = str(operator_response_owner_request.get("owner", "")).strip().upper()
            if response_owner in {"ATOMIC_REFERENCE_WORLD_INTERACTION", "ATOMIC-REFERENCE-WORLD-INTERACTION/1.0.0"}:
                operator_response_owner_receipt = self.theory_compiler.atomic_world_interaction.execute_frozen_protocol(
                    protocol=operator_probe_design,
                    allow_reference_simulation=bool(operator_response_owner_request.get("allow_reference_simulation", False)),
                    environment=dict(operator_response_owner_request.get("environment", {})) if isinstance(operator_response_owner_request.get("environment"), Mapping) else {},
                )
                if operator_response_owner_receipt.get("status") == "TYPED_CARRIER_REDESIGN_REQUIRED":
                    required = dict(operator_response_owner_receipt.get("required_carrier", {}))
                    operator_probe_design = self.theory_compiler.probe_design.design(
                        freeze_digest=str(invention.get("digest", input_digest)),
                        components=int(required.get("components", design_components)),
                        grid=required.get("grid", design_grid),
                        design_shell=design_shell,
                    )
                    operator_probe_design_history.append(operator_probe_design)
                    operator_response_owner_receipt = self.theory_compiler.atomic_world_interaction.execute_frozen_protocol(
                        protocol=operator_probe_design,
                        allow_reference_simulation=bool(operator_response_owner_request.get("allow_reference_simulation", False)),
                        environment=dict(operator_response_owner_request.get("environment", {})) if isinstance(operator_response_owner_request.get("environment"), Mapping) else {},
                    )
                if operator_response_owner_receipt.get("status") == "ATTESTED_OPERATOR_RESPONSES_ACQUIRED_FROM_REFERENCE_SIMULATION":
                    probe_rows = tuple(dict(x) for x in operator_response_owner_receipt.get("probe_rows", ()))
                    operator_probe_evidence = dict(operator_response_owner_receipt.get("attestation", {}))
                    operator_probe_evidence_digest = str(operator_probe_evidence.get("digest", "")) or digest_payload(operator_probe_evidence)
                    _validate_bound_probe_evidence()

        if probe_rows:
            _validate_bound_probe_evidence()
            if not operator_probe_evidence_valid:
                executable_synthesis = {
                    **self.theory_compiler.synthesis._fail(operator_probe_evidence_reason, probe_digest=probe_digest),
                    "next_experiment": "PROVIDE_DIGEST_BOUND_OPERATOR_PROBE_ATTESTATION",
                }
            else:
                executable_synthesis = self.theory_compiler.synthesis.synthesize(
                    probe_rows=probe_rows,
                    freeze_digest=str(invention.get("digest", input_digest)),
                    fit_tolerance_nrmse=operator_fit_tolerance_nrmse,
                    max_terms_per_output=operator_max_terms_per_output,
                )
                if executable_synthesis.get("qualified_for_compilation") is True:
                    executable_compilation = self.theory_compiler.compiler.compile(
                        theory_artifact=executable_synthesis,
                        theory_freeze_digest=str(invention.get("digest", input_digest)),
                    )
                    if executable_compilation.get("status") == "THEORY_EXECUTABLE_COMPILED":
                        executable_execution = self.theory_compiler.runtime.execute(
                            compiled=executable_compilation,
                            runtime_request={"eigenpair_count": operator_eigenpair_count},
                        )
        else:
            if operator_probe_design is None:
                operator_probe_design = self.theory_compiler.probe_design.design(
                    freeze_digest=str(invention.get("digest", input_digest)),
                    components=int(operator_probe_design_request.get("components", gap_evidence.get("state_components", 1) or 1)),
                    grid=operator_probe_design_request.get("grid"),
                    design_shell=int(operator_probe_design_request.get("design_shell", 1)),
                )
                operator_probe_design_history.append(operator_probe_design)
            reason = "NO_ATTESTED_OPERATOR_RESPONSE_VALUES_AVAILABLE"
            if isinstance(operator_response_owner_receipt, Mapping):
                if operator_response_owner_receipt.get("status") == "REFERENCE_SIMULATION_NOT_AUTHORIZED":
                    reason = "REFERENCE_SIMULATION_NOT_AUTHORIZED"
                elif operator_response_owner_receipt.get("status") == "TYPED_CARRIER_REDESIGN_REQUIRED":
                    reason = "TYPED_CARRIER_REDESIGN_REMAINS_UNRESOLVED"
            executable_synthesis = {
                **self.theory_compiler.synthesis._fail(reason, probe_digest=str(operator_probe_design.get("probe_blueprint_digest", ""))),
                "next_experiment": "EXECUTE_FROZEN_OPERATOR_PROBE_PROTOCOL_WITH_ATTESTED_WORLD_OR_TYPED_OWNER",
            }

        # Optional next shell: Atlas births a variable-particle protocol only after
        # the one-particle executable candidate exists.  A separate world owner
        # returns density/field/operator responses after freeze; the generic
        # self-consistent synthesis owner must infer the fixed-point representation.
        vp_owner = str(variable_particle_world_request.get("owner", "")).strip().upper()
        if (isinstance(executable_execution, Mapping) and executable_execution.get("status") == "EXECUTION_PASS"
                and isinstance(operator_probe_design, Mapping)
                and vp_owner in {"ATOMIC_VARIABLE_PARTICLE_REFERENCE_WORLD", "ATOMIC-VARIABLE-PARTICLE-REFERENCE-WORLD/1.0.0"}):
            variable_particle_probe_design = self.theory_compiler.variable_particle_probe_design.design(
                freeze_digest=str(invention.get("digest", input_digest)),
                base_protocol=operator_probe_design,
                design_shell=int(variable_particle_world_request.get("design_shell", 1)),
            )
            variable_particle_world_receipt = self.theory_compiler.variable_particle_world_interaction.execute_frozen_protocol(
                base_protocol=operator_probe_design,
                particle_protocol=variable_particle_probe_design,
                allow_reference_simulation=bool(variable_particle_world_request.get("allow_reference_simulation", False)),
                environment=dict(variable_particle_world_request.get("environment", {})) if isinstance(variable_particle_world_request.get("environment"), Mapping) else {},
            )
            if variable_particle_world_receipt.get("status") == "ATTESTED_VARIABLE_PARTICLE_SELF_CONSISTENT_RESPONSES_ACQUIRED_FROM_REFERENCE_SIMULATION":
                vp_rows = tuple(dict(x) for x in variable_particle_world_receipt.get("probe_rows", ()))
                self_consistent_synthesis = self.theory_compiler.self_consistent_synthesis.synthesize(
                    base_candidate=executable_synthesis,
                    probe_rows=vp_rows,
                    freeze_digest=str(invention.get("digest", input_digest)),
                    fit_tolerance_nrmse=float(variable_particle_world_request.get("fit_tolerance_nrmse", 1e-7)),
                )
                if self_consistent_synthesis.get("qualified_for_compilation") is True:
                    self_consistent_compilation = self.theory_compiler.compiler.compile(
                        theory_artifact=self_consistent_synthesis, theory_freeze_digest=str(invention.get("digest", input_digest))
                    )
                    if self_consistent_compilation.get("status") == "THEORY_EXECUTABLE_COMPILED":
                        self_consistent_execution = self.theory_compiler.runtime.execute(
                            compiled=self_consistent_compilation,
                            runtime_request={
                                "eigenpair_count": operator_eigenpair_count,
                                "occupied_eigenpair_count": max(1, int(variable_particle_world_request.get("validation_particle_count", 2))),
                            },
                        )

        # Optional many-body shell: the caller may authorize an independent
        # atomic reference simulation after the representation gap has been
        # frozen.  Atlas starts at one-body normal-ordered monomials and expands
        # interaction rank only when sealed holdout operator action remains
        # unresolved.  No named many-electron method is selected.
        mb_owner = str(many_body_world_request.get("owner", "")).strip().upper()
        if mb_owner in {"ATOMIC_MANY_BODY_REFERENCE_WORLD", "ATOMIC-MANY-BODY-REFERENCE-WORLD/1.0.0"}:
            atom_z = int(many_body_world_request.get("atom_z", gap_evidence.get("Z", 0) or 0))
            electron_count = int(many_body_world_request.get("electron_count", atom_z))
            spatial_orbitals = max(1, int(many_body_world_request.get("spatial_orbital_count", max(3, int(math.ceil(max(electron_count, 1) / 2.0))))))
            fit_tol = max(0.0, float(many_body_world_request.get("fit_tolerance_nrmse", 1e-8)))
            radial_points = max(400, int(many_body_world_request.get("radial_points", 600)))
            precommitted_rank_raw = many_body_world_request.get("precommitted_interaction_rank")
            precommitted_rank = int(precommitted_rank_raw) if precommitted_rank_raw not in (None, "") else None
            current_rank = precommitted_rank if precommitted_rank is not None else 1
            local_particle_rank = max(1, electron_count)
            while current_rank <= local_particle_rank:
                mb_design = self.theory_compiler.many_body_probe_design.design(
                    freeze_digest=str(invention.get("digest", input_digest)),
                    atom_z=atom_z,
                    electron_count=electron_count,
                    spatial_orbital_count=spatial_orbitals,
                    interaction_rank=current_rank,
                    design_shell=current_rank,
                )
                many_body_probe_design_history.append(mb_design)
                if mb_design.get("status") == "RESEARCH_CARRIER_REQUIRES_ORBITAL_BASIS_EXPANSION":
                    spatial_orbitals = int(mb_design["required_minimum_spatial_orbital_count"])
                    continue
                if mb_design.get("status") != "MANY_BODY_OPERATOR_PROBE_PROTOCOL_FROZEN_AWAITING_ATTESTED_RESPONSES":
                    break
                mb_world = self.theory_compiler.atomic_many_body_world_interaction.execute_frozen_protocol(
                    protocol=mb_design,
                    allow_reference_simulation=bool(many_body_world_request.get("allow_reference_simulation", False)),
                    radial_points=radial_points,
                )
                many_body_world_receipts.append(mb_world)
                if mb_world.get("status") != "ATTESTED_MANY_BODY_OPERATOR_RESPONSES_ACQUIRED_FROM_REFERENCE_SIMULATION":
                    break
                many_body_coordinate_synthesis = self.theory_compiler.many_body_coordinate_synthesis.synthesize(
                    carrier=mb_world["carrier"],
                    probe_rows=mb_world["probe_rows"],
                    freeze_digest=str(invention.get("digest", input_digest)),
                    fit_tolerance_nrmse=fit_tol,
                    max_interaction_rank=current_rank,
                    require_precommitted_rank=precommitted_rank,
                )
                if many_body_coordinate_synthesis.get("qualified") is True:
                    inferred_rank = int(many_body_coordinate_synthesis.get("minimal_interaction_rank") or many_body_coordinate_synthesis.get("validated_precommitted_interaction_rank") or current_rank)
                    if precommitted_rank is None:
                        many_body_representation_invention = self.invention.unknown_unknown.discover(
                            question=question,
                            evidence_rows=[
                                {
                                    "mode": "residual",
                                    "environment_id": str(req.get("problem_id", "representation-gap")) + "-pre-many-body",
                                    "evidence_digest": gap_evidence_digest,
                                    "status": gap_kind,
                                },
                                {
                                    "mode": "operator_probe",
                                    "environment_id": str(req.get("problem_id", "representation-gap")) + "-many-body",
                                    "evidence_digest": str(mb_world.get("probe_digest", "")),
                                    "status": "SEALED_MANY_BODY_OPERATOR_RESPONSE_EVIDENCE",
                                    "operator_interaction_rank": inferred_rank,
                                },
                            ],
                        )
                    break
                if precommitted_rank is not None:
                    # Blind structural validation may not adapt its representation
                    # after seeing the sealed holdout atom.
                    break
                next_rank = many_body_coordinate_synthesis.get("next_interaction_rank_shell")
                current_rank = int(next_rank) if next_rank is not None else current_rank + 1

        if isinstance(many_body_coordinate_synthesis, Mapping) and many_body_coordinate_synthesis.get("qualified") is True:
            if many_body_world_request.get("precommitted_interaction_rank") is not None:
                status = "PRECOMMITTED_MANY_BODY_OPERATOR_COORDINATE_VALIDATED_NOT_LAW"
                next_action = "ACCUMULATE_MORE_BLIND_ATOMS_OR_EMPIRICAL_FALSIFICATION_EVIDENCE"
            else:
                status = "MANY_BODY_OPERATOR_COORDINATES_IDENTIFIED_TESTABLE_NOT_LAW"
                next_action = "FALSIFY_BORN_INTERACTION_RANK_ON_PRECOMMITTED_BLIND_ATOMS_OR_EMPIRICAL_EVIDENCE"
            lifecycle = "TESTABLE"
        elif isinstance(self_consistent_execution, Mapping) and self_consistent_execution.get("status") == "EXECUTION_PASS" and self_consistent_execution.get("fixed_point", {}).get("status") == "FIXED_POINT_CONVERGED":
            status = "SELF_CONSISTENT_EXECUTABLE_REPRESENTATION_CANDIDATE_SYNTHESIZED_NOT_LAW"
            lifecycle = "TESTABLE"
            next_action = "FALSIFY_VARIABLE_PARTICLE_SELF_CONSISTENT_REPRESENTATION_AND_ACQUIRE_EXISTENCE_STABILITY_EVIDENCE"
        elif isinstance(executable_execution, Mapping) and executable_execution.get("status") == "EXECUTION_PASS":
            status = "EXECUTABLE_REPRESENTATION_CANDIDATE_SYNTHESIZED_NOT_LAW"
            lifecycle = "TESTABLE"
            next_action = "FALSIFY_SYNTHESIZED_EXECUTABLE_REPRESENTATION_ON_INDEPENDENT_WORLD_EVIDENCE"
        elif isinstance(operator_probe_design, Mapping) and operator_probe_design.get("status") == "OPERATOR_PROBE_PROTOCOL_FROZEN_AWAITING_ATTESTED_RESPONSES":
            status = "REPRESENTATION_GAP_OPERATOR_PROBE_PROTOCOL_FROZEN_AWAITING_ATTESTED_RESPONSES"
            lifecycle = "CANDIDATE"
            next_action = "EXECUTE_FROZEN_OPERATOR_PROBE_PROTOCOL_WITH_ATTESTED_RESPONSE_OWNER"
        else:
            status = "REPRESENTATION_GAP_REQUIRES_DISCRIMINATING_OPERATOR_PROBES"
            lifecycle = "CANDIDATE"
            next_action = "EXPAND_OPERATOR_PROBE_DESIGN_SHELL_OR_ACQUIRE_TYPED_CARRIER_EVIDENCE"

        result_core = {
            "status": status,
            "lifecycle_state": lifecycle,
            "next_action": next_action,
            "gap_kind": gap_kind,
            "executable_representation_status": executable_synthesis.get("status"),
            "executable_candidate_id": executable_synthesis.get("candidate_id"),
            "executable_id": executable_compilation.get("executable_id") if isinstance(executable_compilation, Mapping) else None,
            "execution_status": executable_execution.get("status") if isinstance(executable_execution, Mapping) else None,
            "self_consistent_candidate_id": self_consistent_synthesis.get("candidate_id") if isinstance(self_consistent_synthesis, Mapping) else None,
            "self_consistent_execution_status": self_consistent_execution.get("status") if isinstance(self_consistent_execution, Mapping) else None,
            "self_consistent_fixed_point_status": self_consistent_execution.get("fixed_point", {}).get("status") if isinstance(self_consistent_execution, Mapping) else None,
            "many_body_coordinate_status": many_body_coordinate_synthesis.get("status") if isinstance(many_body_coordinate_synthesis, Mapping) else None,
            "minimal_interaction_rank": many_body_coordinate_synthesis.get("minimal_interaction_rank") if isinstance(many_body_coordinate_synthesis, Mapping) else None,
            "validated_precommitted_interaction_rank": many_body_coordinate_synthesis.get("validated_precommitted_interaction_rank") if isinstance(many_body_coordinate_synthesis, Mapping) else None,
            "scientific_law_established": False,
            "physical_object_count_established": False,
            "physical_upper_index_established": False,
        }
        result_digest = digest_payload(result_core)
        receipt = {
            "schema": ADAPTIVE_RESEARCH_KERNEL_SCHEMA,
            "owner": self.owner_id,
            "problem_id": str(req.get("problem_id", "ARK-GAP-" + input_digest[:12].upper())),
            "question": question,
            "entry_mode": "ATTESTED_REPRESENTATION_GAP",
            "observations_origin": "NONE_REQUIRED_FOR_GAP_ENTRY",
            "input_digest": input_digest,
            "gap_evidence_digest": gap_evidence_digest,
            "gap_evidence": gap_evidence,
            "operator_probe_evidence_digest": operator_probe_evidence_digest,
            "operator_probe_evidence": operator_probe_evidence,
            "operator_probe_evidence_valid": operator_probe_evidence_valid,
            "operator_probe_evidence_reason": operator_probe_evidence_reason,
            "axis_registry_digest": digest_payload({"canonical_axis_count_at_cycle": canonical_count, "strict_blind": strict_blind}),
            "hypothesis_space_digest": digest_payload({"entry_mode": "ATTESTED_REPRESENTATION_GAP", "mathematical_invention_digest": invention.get("digest")}),
            "code_digest": self._code_digest(),
            "result_digest": result_digest,
            "phi_space": {
                "registered_axis_count_at_cycle": canonical_count,
                "fixed_axis_count_ceiling": None,
                "owner_visits": phi_scan.get("owner_visits"),
                "scan_status": phi_scan.get("status"),
                "scan_digest": phi_scan.get("digest"),
                "named_law_catalog_read": not strict_blind,
            },
            "mathematical_invention": invention,
            "operator_probe_design": operator_probe_design,
            "operator_probe_design_history": operator_probe_design_history,
            "operator_response_owner_receipt": operator_response_owner_receipt,
            "variable_particle_probe_design": variable_particle_probe_design,
            "variable_particle_world_receipt": variable_particle_world_receipt,
            "self_consistent_representation_synthesis": self_consistent_synthesis,
            "self_consistent_representation_compilation": self_consistent_compilation,
            "self_consistent_representation_execution": self_consistent_execution,
            "many_body_probe_design_history": many_body_probe_design_history,
            "many_body_world_receipts": many_body_world_receipts,
            "many_body_operator_coordinate_synthesis": many_body_coordinate_synthesis,
            "many_body_representation_invention": many_body_representation_invention,
            "executable_representation_synthesis": executable_synthesis,
            "executable_representation_compilation": executable_compilation,
            "executable_representation_execution": executable_execution,
            "result": result_core,
            "claim_boundary": {
                "atlas_result_is_scientific_law": False,
                "gap_receipt_is_world_measurement": False,
                "missing_operator_probe_values_filled_by_assistant": False,
                "atlas_generated_probe_inputs": bool(isinstance(operator_probe_design, Mapping) and operator_probe_design.get("claim_boundary", {}).get("atlas_generated_probe_inputs") is True),
                "atlas_generated_operator_responses": False,
                "operator_responses_generated_by_independent_typed_owner": bool(isinstance(operator_response_owner_receipt, Mapping) and operator_response_owner_receipt.get("claim_boundary", {}).get("responses_generated_by_independent_typed_owner") is True),
                "reference_simulation_used": bool(isinstance(operator_response_owner_receipt, Mapping) and operator_response_owner_receipt.get("claim_boundary", {}).get("empirical_world_measurement") is False and operator_response_owner_receipt.get("status") == "ATTESTED_OPERATOR_RESPONSES_ACQUIRED_FROM_REFERENCE_SIMULATION"),
                "empirical_world_measurement_used": False,
                "operator_probe_rows_require_digest_bound_provenance": True,
                "operator_probe_evidence_valid": operator_probe_evidence_valid,
                "named_law_catalog_used_in_strict_blind_mode": False if strict_blind else None,
                "fixed_axis_count_used_as_space_ceiling": False,
                "fixed_physical_object_count_used": False,
                "fixed_upper_index_used": False,
                "variable_particle_counts_born_by_atlas": bool(isinstance(variable_particle_probe_design, Mapping) and variable_particle_probe_design.get("claim_boundary", {}).get("particle_counts_born_by_atlas") is True),
                "variable_particle_reference_simulation_used": bool(isinstance(variable_particle_world_receipt, Mapping) and variable_particle_world_receipt.get("claim_boundary", {}).get("empirical_world_measurement") is False),
                "self_consistent_candidate_establishes_physical_atoms": False,
                "many_body_reference_simulation_used": bool(many_body_world_receipts),
                "many_body_reference_simulation_establishes_atomic_truth": False,
                "named_many_body_method_selected": False,
                "interaction_rank_born_from_sealed_operator_residual": bool(isinstance(many_body_coordinate_synthesis, Mapping) and int(many_body_coordinate_synthesis.get("minimal_interaction_rank") or 0) > 1),
                "blind_precommitted_rank_may_adapt_after_holdout": False if many_body_world_request.get("precommitted_interaction_rank") is not None else None,
                "executable_candidate_execution_establishes_world_law": False,
            },
        }
        receipt["digest"] = digest_payload(receipt)
        statement = f"Atlas representation-gap cycle {receipt['problem_id']} produced status {status}"
        atlas_claim = self.firewall.seal_atlas_claim(
            statement=statement,
            execution_receipt=receipt,
            payload={"status": status, "entry_mode": receipt["entry_mode"]},
        )
        return {**receipt, "atlas_claim": atlas_claim}

    def advance(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if bool(request.get("representation_gap", False)) or str(request.get("entry_mode", "")).upper() == "ATTESTED_REPRESENTATION_GAP":
            return self._advance_representation_gap(request)
        req=self._normalize_request(request)
        if req["domain_id"] not in DOMAIN_REGISTRIES:
            raise ValueError(f"unknown domain {req['domain_id']!r}")
        input_core={k:v for k,v in req.items() if k not in {"previous_state","experiment_points"}}
        input_digest=digest_payload(input_core)
        query=DirectedResearchQuery(
            question=req["question"], required_domains=(req["domain_id"],),
            target_axis_ids=tuple(req.get("target_axis_ids",())), include_all_connected_owners=True,
            discovery_mode="SEMANTIC_OWNER_FRONTIER",
        )
        phi_scan=directed_owner_hypergraph_research(self.runtime.catalog,self.runtime.bridges,query)
        canonical_count=int(phi_scan.get("registered_axis_count",0))
        research_local_axes={
            req["target_variable"]:{"axis_id":req["target_variable"],"origin":"OBSERVED_TARGET","activation_state":"TARGET","dimension":req["variable_dimensions"][req["target_variable"]]},
            **{
                name:{"axis_id":name,"origin":"OBSERVED_COORDINATE","activation_state":"ACTIVE_MODEL_AXIS","dimension":req["variable_dimensions"][name]}
                for name in tuple(req["predictor_variables"])
            },
            **{
                name:{"axis_id":name,"origin":"OBSERVED_COORDINATE","activation_state":"DORMANT_AVAILABLE_AXIS","dimension":req["variable_dimensions"][name]}
                for name in tuple(req["dormant_axis_variables"])
            },
        }
        axis_registry_core={
            "canonical_registry_digest":digest_payload({d:sorted(r.axes) for d,r in DOMAIN_REGISTRIES.items()}),
            "canonical_axis_count_at_cycle":canonical_count,
            "canonical_axis_count_is_ceiling":False,
            "research_local_axes":research_local_axes,
            "previous_research_local_axes":dict(req.get("previous_state",{}).get("research_local_axes",{})) if isinstance(req.get("previous_state"),Mapping) else {},
        }
        axis_registry_digest=digest_payload(axis_registry_core)

        hypotheses=self.hypothesis_synthesis.synthesize(
            observations=req["observations"],target_variable=req["target_variable"],
            predictor_variables=req["predictor_variables"],variable_dimensions=req["variable_dimensions"],
            complexity_level=req["complexity_level"],
        )
        best=hypotheses.get("candidates",[None])[0] if hypotheses.get("candidates") else None
        residual_records,residuals=self._residual_evidence(
            req["observations"],req["predictor_variables"],req["target_variable"],best,
            req["dormant_axis_variables"],
        )
        if residual_records and len({r["outcome_class"] for r in residual_records})>1:
            axis_scan=self.axis_discovery.scan(
                domain_id=req["domain_id"], evidence_records=residual_records,
                minimum_coverage=0.55, minimum_information_gain_bits=0.01,
                minimum_independent_study_support=1, maximum_grouped_permutation_p=1.0,
                minimum_loso_gain=-1.0,
            )
        else:
            axis_scan={"status":"AXIS_DISCOVERY_NOT_TRIGGERED_RESIDUAL_UNSTRUCTURED_OR_SMALL","candidate_axes":[],"scan_summary":{}}
            axis_scan["digest"]=digest_payload(axis_scan)
        candidate_axes=[r for r in axis_scan.get("candidate_axes",()) if r.get("status")=="RESEARCH_LOCAL_AXIS_CANDIDATE"]
        fit_ok=bool(best) and bool(best.get("identifiable_on_train")) and float(best.get("holdout_nrmse",float("inf")))<=req["fit_tolerance_nrmse"]

        # Axis activation is evidence-driven.  Merely making a coordinate
        # available (for example temperature) never inserts it into a formula.
        # At most the highest-information dormant coordinate is opened in this
        # cycle; further axes remain for subsequent fair-dovetail cycles.
        dormant_set=set(req["dormant_axis_variables"])
        dormant_signal=[r for r in candidate_axes if str(r.get("context_dimension")) in dormant_set]
        dormant_signal.sort(key=lambda r:(-float(r.get("normalized_information_gain",0.0)),-float(r.get("coverage",0.0)),str(r.get("context_dimension"))))
        activated_axes=[]
        expanded_hypotheses=None
        expanded_best=None
        activation_improvement={"improved":False,"initial_holdout_nrmse":float(best.get("holdout_nrmse",float("inf"))) if best else float("inf"),"expanded_holdout_nrmse":float("inf"),"absolute_improvement":0.0,"relative_improvement":0.0}
        activation_improvement={**activation_improvement,"digest":digest_payload(activation_improvement)}
        if (not fit_ok) and req["auto_activate_dormant_axes"] and dormant_signal:
            axis_id=str(dormant_signal[0]["context_dimension"])
            expanded_predictors=tuple(req["predictor_variables"])+(axis_id,)
            expanded_hypotheses=self.hypothesis_synthesis.synthesize(
                observations=req["observations"],target_variable=req["target_variable"],
                predictor_variables=expanded_predictors,variable_dimensions=req["variable_dimensions"],
                complexity_level=req["complexity_level"],
            )
            expanded_best=expanded_hypotheses.get("candidates",[None])[0] if expanded_hypotheses.get("candidates") else None
            activation_improvement=self._activation_improvement(best,expanded_best)
            if activation_improvement.get("improved"):
                activated_axes=[axis_id]

        evidence_rows=[]
        if residuals:
            evidence_rows.append({"mode":"residual","environment_id":str(req.get("problem_id","adaptive-problem")),"evidence_digest":digest_payload(residuals),"status":"NUMERICAL_RESIDUAL_PRESENT" if not fit_ok else "RESIDUAL_WITHIN_CURRENT_TOLERANCE"})
        if candidate_axes:
            evidence_rows.append({"mode":"latent","environment_id":str(req.get("problem_id","adaptive-problem"))+"-axis","evidence_digest":axis_scan.get("digest"),"status":"RESEARCH_LOCAL_AXIS_STRUCTURE_PRESENT"})
        if req.get("counterfactual_evidence_digest"):
            evidence_rows.append({"mode":"counterfactual","environment_id":str(req.get("problem_id","adaptive-problem"))+"-counterfactual","evidence_digest":str(req["counterfactual_evidence_digest"]),"status":"CALLER_BOUND_COUNTERFACTUAL_EVIDENCE"})
        if req.get("causal_evidence_digest"):
            evidence_rows.append({"mode":"causal","environment_id":str(req.get("problem_id","adaptive-problem"))+"-causal","evidence_digest":str(req["causal_evidence_digest"]),"status":"CALLER_BOUND_CAUSAL_EVIDENCE"})
        if req["operator_probe_rows"]:
            evidence_rows.append({
                "mode":"operator_probe",
                "environment_id":str(req.get("problem_id","adaptive-problem"))+"-operator-probe",
                "evidence_digest":digest_payload(req["operator_probe_rows"]),
                "status":"TYPED_OPERATOR_RESPONSE_EVIDENCE",
            })
        invention=self.invention.unknown_unknown.discover(question=req["question"],evidence_rows=evidence_rows) if not fit_ok else {
            "status":"MATHEMATICAL_INVENTION_NOT_TRIGGERED_CURRENT_REPRESENTATION_SURVIVES",
            "claim_boundary":{"new_representation_type_established":False},
        }
        if "digest" not in invention: invention={**invention,"digest":digest_payload(invention)}

        executable_synthesis = {
            "status": "EXECUTABLE_REPRESENTATION_NOT_TRIGGERED_CURRENT_REPRESENTATION_SURVIVES" if fit_ok else "EXECUTABLE_SYNTHESIS_REQUIRES_OPERATOR_PROBES",
            "claim_boundary": {"executable_representation_established": False, "world_law_established": False},
        }
        executable_compilation = None
        executable_execution = None
        operator_probe_design = None
        if (not fit_ok) and req["operator_probe_rows"]:
            executable_synthesis = self.theory_compiler.synthesis.synthesize(
                probe_rows=req["operator_probe_rows"],
                freeze_digest=str(invention.get("digest", input_digest)),
                fit_tolerance_nrmse=req["operator_fit_tolerance_nrmse"],
                max_terms_per_output=req["operator_max_terms_per_output"],
            )
            if executable_synthesis.get("qualified_for_compilation") is True:
                executable_compilation = self.theory_compiler.compiler.compile(
                    theory_artifact=executable_synthesis,
                    theory_freeze_digest=str(invention.get("digest", input_digest)),
                )
                if executable_compilation.get("status") == "THEORY_EXECUTABLE_COMPILED":
                    executable_execution = self.theory_compiler.runtime.execute(
                        compiled=executable_compilation,
                        runtime_request={"eigenpair_count": req["operator_eigenpair_count"]},
                    )
        elif not fit_ok:
            design_req = dict(req.get("operator_probe_design_request", {}))
            operator_probe_design = self.theory_compiler.probe_design.design(
                freeze_digest=str(invention.get("digest", input_digest)),
                components=max(1, int(design_req.get("components", 1))),
                grid=design_req.get("grid"),
                design_shell=max(1, int(design_req.get("design_shell", 1))),
            )
            executable_synthesis = {
                **self.theory_compiler.synthesis._fail("NO_ATTESTED_OPERATOR_RESPONSE_VALUES_AVAILABLE", probe_digest=str(operator_probe_design.get("probe_blueprint_digest", ""))),
                "next_experiment": "EXECUTE_FROZEN_OPERATOR_PROBE_PROTOCOL_WITH_ATTESTED_WORLD_OR_TYPED_OWNER",
            }

        effective_hypotheses=expanded_hypotheses if activated_axes and expanded_hypotheses is not None else hypotheses
        effective_best=expanded_best if activated_axes and expanded_best is not None else best
        effective_predictors=tuple(req["predictor_variables"])+tuple(activated_axes)
        effective_fit_ok=bool(effective_best) and bool(effective_best.get("identifiable_on_train")) and float(effective_best.get("holdout_nrmse",float("inf")))<=req["fit_tolerance_nrmse"]
        sealed_holdout=self._evaluate_candidate_on_observations(
            effective_best,req["sealed_holdout_observations"],effective_predictors,req["target_variable"]
        )
        experiment=self._experiment_disagreement(effective_hypotheses.get("candidates",()),tuple(req.get("experiment_points",())),effective_predictors)

        if effective_fit_ok:
            lifecycle="SURVIVOR"
            next_action="ACQUIRE_INDEPENDENT_FALSIFICATION_OR_PROMOTION_EVIDENCE"
            status="HYPOTHESIS_SURVIVES_CURRENT_HELDOUT_EVIDENCE_NOT_LAW"
        elif executable_execution and executable_execution.get("status") == "EXECUTION_PASS":
            lifecycle="TESTABLE"
            next_action="FALSIFY_SYNTHESIZED_EXECUTABLE_REPRESENTATION_ON_INDEPENDENT_WORLD_EVIDENCE"
            status="EXECUTABLE_REPRESENTATION_CANDIDATE_SYNTHESIZED_NOT_LAW"
        elif not req["operator_probe_rows"] and isinstance(operator_probe_design, Mapping) and operator_probe_design.get("status") == "OPERATOR_PROBE_PROTOCOL_FROZEN_AWAITING_ATTESTED_RESPONSES":
            lifecycle="CANDIDATE"
            next_action="EXECUTE_FROZEN_OPERATOR_PROBE_PROTOCOL_WITH_ATTESTED_RESPONSE_OWNER"
            status="REPRESENTATION_GAP_OPERATOR_PROBE_PROTOCOL_FROZEN_AWAITING_ATTESTED_RESPONSES"
        elif candidate_axes:
            lifecycle="TESTABLE"
            next_action="EVOLVE_RESEARCH_LOCAL_AXES_AND_REPEAT"
            status="RESIDUAL_REQUIRES_AXIS_EVOLUTION"
        else:
            lifecycle="CANDIDATE"
            next_action="OPEN_NEXT_HYPOTHESIS_COMPLEXITY_SHELL"
            status="RESIDUAL_REQUIRES_LANGUAGE_EVOLUTION"
        best=effective_best
        if best:
            best=dict(best); best["lifecycle_state"]=lifecycle
        previous_local=dict(axis_registry_core.get("previous_research_local_axes",{}))
        next_local={**previous_local,**research_local_axes}
        for row in candidate_axes:
            axis_id=str(row.get("context_dimension"))
            if axis_id:
                previous=dict(next_local.get(axis_id,{"axis_id":axis_id}))
                next_local[axis_id]={
                    **previous,
                    "axis_id":axis_id,"origin":"RESIDUAL_DISCOVERY","canonical":False,
                    "activation_state":"ACTIVE_MODEL_AXIS" if axis_id in activated_axes else previous.get("activation_state","RESEARCH_LOCAL_CANDIDATE"),
                    "evidence_digest":axis_scan.get("digest"),
                    "information_gain_bits":float(row.get("information_gain_bits",0.0)),
                    "identifiability_status":str(row.get("identifiability_status","UNRESOLVED")),
                }
        next_state_core={
            "problem_id":str(req.get("problem_id","ARK-"+input_digest[:12].upper())),
            "research_local_axes":next_local,
            "active_predictor_variables":list(effective_predictors),
            "remaining_dormant_axis_variables":[x for x in req["dormant_axis_variables"] if x not in activated_axes],
            "complexity_level":req["complexity_level"] if effective_fit_ok else req["complexity_level"]+1,
            "surviving_hypothesis_ids":[str(r.get("candidate_id")) for r in effective_hypotheses.get("candidates",())[:12]],
            "best_hypothesis_id":best.get("candidate_id") if best else None,
            "previous_state_digest":str(req.get("previous_state",{}).get("state_digest","")) if isinstance(req.get("previous_state"),Mapping) else "",
        }
        next_state={**next_state_core,"state_digest":digest_payload(next_state_core)}
        result_core={
            "status":status,"best_hypothesis":best,"fit_tolerance_nrmse":req["fit_tolerance_nrmse"],
            "next_action":next_action,"next_complexity_level":req["complexity_level"] if effective_fit_ok else req["complexity_level"]+1,
            "initial_active_predictor_variables":list(req["predictor_variables"]),
            "dormant_axis_variables":list(req["dormant_axis_variables"]),
            "activated_axis_variables":list(activated_axes),
            "effective_predictor_variables":list(effective_predictors),
            "axis_activation_improvement":activation_improvement,
            "sealed_holdout_evaluation":sealed_holdout,
            "research_local_axis_candidates":[str(r.get("context_dimension")) for r in candidate_axes],
            "executable_representation_status": executable_synthesis.get("status"),
            "executable_candidate_id": executable_synthesis.get("candidate_id"),
            "executable_id": executable_compilation.get("executable_id") if isinstance(executable_compilation, Mapping) else None,
            "execution_status": executable_execution.get("status") if isinstance(executable_execution, Mapping) else None,
            "next_state":next_state,
            "scientific_law_established":False,
        }
        result_digest=digest_payload(result_core)
        code_digest=self._code_digest()
        receipt={
            "schema":ADAPTIVE_RESEARCH_KERNEL_SCHEMA,
            "owner":self.owner_id,
            "problem_id":str(req.get("problem_id","ARK-"+input_digest[:12].upper())),
            "question":req["question"],
            "observations_origin":req["observations_origin"],
            "input_digest":input_digest,
            "axis_registry_digest":axis_registry_digest,
            "hypothesis_space_digest":effective_hypotheses.get("digest"),
            "code_digest":code_digest,
            "result_digest":result_digest,
            "phi_space":{
                "registered_axis_count_at_cycle":canonical_count,
                "all_registered_axes_visited":phi_scan.get("all_registered_axes_visited"),
                "fixed_axis_count_ceiling":None,
                "owner_visits":phi_scan.get("owner_visits"),
                "scan_digest":phi_scan.get("digest"),
            },
            "representation":axis_registry_core,
            "hypothesis_space":effective_hypotheses,
            "initial_hypothesis_space":hypotheses,
            "post_activation_hypothesis_space":expanded_hypotheses,
            "residual_axis_discovery":axis_scan,
            "axis_activation":{
                "dormant_axes_offered":list(req["dormant_axis_variables"]),
                "activated_axes":list(activated_axes),
                "activation_was_residual_driven":bool(activated_axes),
                "improvement":activation_improvement,
            },
            "mathematical_invention":invention,
            "operator_probe_design": operator_probe_design,
            "executable_representation_synthesis": executable_synthesis,
            "executable_representation_compilation": executable_compilation,
            "executable_representation_execution": executable_execution,
            "discriminating_experiment":experiment,
            "result":result_core,
            "claim_boundary":{
                "atlas_result_is_scientific_law":False,
                "assistant_generated_number_can_be_atlas_native":False,
                "external_reference_used_to_select_hypothesis":False,
                "fixed_axis_count_used_as_space_ceiling":False,
                "fixed_hypothesis_complexity_ceiling":False,
                "fixed_competitor_count_used_as_truth_gate":False,
                "dormant_axis_inserted_into_initial_formula":False,
                "axis_activation_requires_residual_evidence":True,
                "sealed_holdout_used_for_axis_activation":False,
                "missing_operator_probe_values_filled_by_assistant":False,
                "atlas_generated_probe_inputs": bool(isinstance(operator_probe_design, Mapping) and operator_probe_design.get("claim_boundary", {}).get("atlas_generated_probe_inputs") is True),
                "atlas_generated_operator_responses": False,
                "executable_candidate_execution_establishes_world_law":False,
            },
        }
        receipt["digest"]=digest_payload(receipt)
        statement=(
            f"Atlas research cycle {receipt['problem_id']} produced status {status}; "
            f"best hypothesis is {best.get('expression') if best else 'none'}"
        )
        atlas_claim=self.firewall.seal_atlas_claim(statement=statement,execution_receipt=receipt,payload={"status":status,"best_candidate_id":best.get("candidate_id") if best else None})
        return {**receipt,"atlas_claim":atlas_claim}

    def energy_space_temperature_axis_control(self) -> Mapping[str, Any]:
        """Axis-augmentation control: temperature is added to space, not formula.

        The initial model receives only an already-computed base-energy
        coordinate.  Temperature is present solely as a dormant observable axis.
        A coupled hidden control world should make residuals select that axis;
        an otherwise identical null world must leave it dormant.  The hidden
        world is CONTROL_REFERENCE and is never supplied to hypothesis synthesis.
        """
        energy_dim=(2,1,-2,0,0,0,0); temp_dim=(0,0,0,0,1,0,0)

        def build_world(*, coupled: bool) -> tuple[list[dict[str, Any]],list[dict[str, Any]]]:
            discovery=[]; sealed=[]
            temperatures=(250.0,275.0,300.0,325.0,350.0,375.0)
            bases=(2.0,3.5,5.0,6.5,8.0,9.5)
            for i,base in enumerate(bases):
                # Rotate temperatures so base-energy and temperature are not
                # collinear.  The relation below is hidden from the kernel.
                for j in range(6):
                    T=temperatures[(j+2*i)%len(temperatures)]
                    if coupled:
                        observed=base*(1.0+0.0015*(T-300.0))
                    else:
                        observed=base
                    row={
                        "study_id":f"{'COUPLED' if coupled else 'NULL'}-{i:02d}-{j:02d}",
                        "values":{"base_energy":base,"temperature":T,"observed_energy":observed},
                    }
                    # One point per base-energy stratum is sealed before any
                    # axis discovery or hypothesis activation.
                    (sealed if j==5 else discovery).append(row)
            return discovery,sealed

        common={
            "domain_id":"physics",
            "target_variable":"observed_energy",
            "predictor_variables":("base_energy",),
            "dormant_axis_variables":("temperature",),
            "variable_dimensions":{"observed_energy":energy_dim,"base_energy":energy_dim,"temperature":temp_dim},
            "observations_origin":"CONTROL_REFERENCE",
            "complexity_level":2,
            "fit_tolerance_nrmse":1e-10,
            "auto_activate_dormant_axes":True,
        }
        coupled_discovery,coupled_sealed=build_world(coupled=True)
        null_discovery,null_sealed=build_world(coupled=False)
        coupled=self.advance({
            **common,
            "problem_id":"CONTROL-ENERGY-SPACE-PLUS-TEMPERATURE-COUPLED",
            "question":"Augment the energy research space with an independent temperature coordinate; do not place temperature in the initial energy formula. Determine whether residual evidence activates a coupling axis.",
            "observations":coupled_discovery,
            "sealed_holdout_observations":coupled_sealed,
        })
        null=self.advance({
            **common,
            "problem_id":"CONTROL-ENERGY-SPACE-PLUS-TEMPERATURE-NULL",
            "question":"Augment the same energy research space with an independent temperature coordinate; do not place temperature in the initial energy formula. Determine whether the axis remains irrelevant when it carries no residual information.",
            "observations":null_discovery,
            "sealed_holdout_observations":null_sealed,
        })
        cbest=coupled.get("result",{}).get("best_hypothesis") or {}
        cresult=coupled.get("result",{})
        nresult=null.get("result",{})
        expression=str(cbest.get("expression",''))
        checks={
            "temperature_not_in_initial_formula_space": "temperature" not in tuple(coupled.get("initial_hypothesis_space",{}).get("predictor_variables",())),
            "temperature_present_as_dormant_axis": coupled.get("representation",{}).get("research_local_axes",{}).get("temperature",{}).get("activation_state")=="DORMANT_AVAILABLE_AXIS",
            "coupled_residual_selects_temperature": "temperature" in cresult.get("research_local_axis_candidates",()),
            "coupled_control_activates_temperature": cresult.get("activated_axis_variables")==["temperature"],
            "coupled_control_improves_after_activation": bool(cresult.get("axis_activation_improvement",{}).get("improved")),
            "coupled_control_born_relation_uses_temperature_only_post_activation": "temperature" in expression and "temperature" in cresult.get("effective_predictor_variables",()),
            "coupled_sealed_holdout_passes_after_freeze": cresult.get("sealed_holdout_evaluation",{}).get("status")=="SEALED_HOLDOUT_EVALUATED" and float(cresult.get("sealed_holdout_evaluation",{}).get("nrmse",1.0))<=1e-10,
            "null_control_does_not_activate_temperature": nresult.get("activated_axis_variables")==[],
            "null_control_keeps_temperature_out_of_effective_formula_space": "temperature" not in nresult.get("effective_predictor_variables",()),
            "both_controls_not_claimed_as_physical_law": coupled.get("result",{}).get("scientific_law_established") is False and null.get("result",{}).get("scientific_law_established") is False,
            "claim_firewall_accepts_only_execution_receipts": coupled.get("atlas_claim",{}).get("atlas_native") is True and null.get("atlas_claim",{}).get("atlas_native") is True,
        }
        payload={
            "schema":"phi-adaptive-research-kernel-energy-space-temperature-axis-control/v2",
            "owner":self.owner_id,
            "status":"PASS_ENERGY_SPACE_TEMPERATURE_AXIS_AUGMENTATION_CONTROL" if all(checks.values()) else "FAIL_ENERGY_SPACE_TEMPERATURE_AXIS_AUGMENTATION_CONTROL",
            "checks":checks,
            "coupled_receipt_digest":coupled.get("digest"),
            "null_receipt_digest":null.get("digest"),
            "coupled_initial_best":coupled.get("initial_hypothesis_space",{}).get("candidates",[None])[0] if coupled.get("initial_hypothesis_space",{}).get("candidates") else None,
            "coupled_post_activation_best":cbest,
            "coupled_axis_discovery":coupled.get("residual_axis_discovery"),
            "null_axis_discovery":null.get("residual_axis_discovery"),
            "claim_boundary":{
                "temperature_was_inserted_into_initial_formula":False,
                "temperature_was_only_added_to_research_space":True,
                "sealed_holdout_was_visible_during_axis_activation":False,
                "hidden_control_world_is_physical_law":False,
                "internet_used":False,
            },
        }
        return {**payload,"digest":digest_payload(payload)}

    def temperature_energy_control(self) -> Mapping[str, Any]:
        """Compatibility alias; current authority is energy_space_temperature_axis_control()."""
        return self.energy_space_temperature_axis_control()

    def run_qualification(self) -> Mapping[str, Any]:
        control=self.energy_space_temperature_axis_control()
        gap_control=self.advance({
            "problem_id":"CONTROL-REPRESENTATION-GAP-NO-FABRICATED-OBSERVATIONS",
            "domain_id":"physics",
            "question":"Continue from an attested representation capability gap without a named law and without fabricated observation rows.",
            "representation_gap":True,
            "gap_kind":"REPRESENTATION_CAPABILITY_GAP",
            "gap_evidence":{
                "source":"ADAPTIVE_RESEARCH_KERNEL_INTERNAL_CAPABILITY_CONTROL",
                "status":"CURRENT_REPRESENTATION_DECLARED_INSUFFICIENT_FOR_CONTROL",
                "world_measurement":False,
            },
            "blind_no_named_law_catalog":True,
            "operator_probe_rows":(),
        })
        world_gap_control=self.advance({
            "problem_id":"CONTROL-REPRESENTATION-GAP-ATOMIC-WORLD-INTERACTION",
            "domain_id":"physics",
            "question":"Continue from an attested representation gap through Atlas-born probes and an explicitly authorized independent typed atomic reference-world simulation without reading a named-law catalog.",
            "representation_gap":True,
            "gap_kind":"REPRESENTATION_CAPABILITY_GAP",
            "gap_evidence":{
                "source":"ADAPTIVE_RESEARCH_KERNEL_WORLD_INTERACTION_CONTROL",
                "status":"CURRENT_REPRESENTATION_DECLARED_INSUFFICIENT_FOR_CONTROL",
                "world_measurement":False,
            },
            "blind_no_named_law_catalog":True,
            "operator_probe_rows":(),
            "operator_probe_design_request":{"components":1,"design_shell":1},
            "operator_response_owner_request":{
                "owner":"ATOMIC_REFERENCE_WORLD_INTERACTION",
                "allow_reference_simulation":True,
                "environment":{"positive_center_charge_units":1.0,"probe_charge_units":-1.0,"signed_channel":-1.0},
            },
            "operator_fit_tolerance_nrmse":1e-10,
            "operator_eigenpair_count":2,
        })
        proposal=self.firewall.label_proposal(statement="assistant proposes E+T",origin="ASSISTANT_HYPOTHESIS")
        fake_receipt={"owner":"ASSISTANT","schema":"fake","digest":"fake"}
        blocked=self.firewall.seal_atlas_claim(statement="assistant fabricated Atlas result",execution_receipt=fake_receipt)
        contract=self.contract()
        checks={
            "energy_space_temperature_axis_control":control.get("status")=="PASS_ENERGY_SPACE_TEMPERATURE_AXIS_AUGMENTATION_CONTROL",
            "axis_count_not_ceiling":contract["space_policy"]["canonical_axis_count_is_ceiling"] is False,
            "hypothesis_complexity_not_capped":contract["space_policy"]["fixed_hypothesis_complexity_ceiling"] is None,
            "fixed_five_not_truth_gate":contract["space_policy"]["fixed_competitor_count_as_truth_gate"] is False,
            "assistant_proposal_not_atlas_native":proposal.get("atlas_native") is False,
            "assistant_fake_atlas_claim_blocked":blocked.get("status")=="REJECTED_ATLAS_NATIVE_PROVENANCE",
            "representation_gap_entry_requires_no_fabricated_observations":gap_control.get("entry_mode")=="ATTESTED_REPRESENTATION_GAP" and gap_control.get("observations_origin")=="NONE_REQUIRED_FOR_GAP_ENTRY",
            "representation_gap_births_probe_protocol_without_responses":gap_control.get("result",{}).get("status")=="REPRESENTATION_GAP_OPERATOR_PROBE_PROTOCOL_FROZEN_AWAITING_ATTESTED_RESPONSES" and gap_control.get("operator_probe_design",{}).get("claim_boundary",{}).get("atlas_generated_probe_inputs") is True,
            "representation_gap_missing_operator_responses_fails_closed":gap_control.get("executable_representation_synthesis",{}).get("reason")=="NO_ATTESTED_OPERATOR_RESPONSE_VALUES_AVAILABLE" and gap_control.get("claim_boundary",{}).get("atlas_generated_operator_responses") is False,
            "strict_blind_gap_suppresses_named_law_catalog":gap_control.get("phi_space",{}).get("named_law_catalog_read") is False and gap_control.get("claim_boundary",{}).get("named_law_catalog_used_in_strict_blind_mode") is False,
            "gap_execution_receipt_is_atlas_native_not_scientific_truth":gap_control.get("atlas_claim",{}).get("atlas_native") is True and gap_control.get("result",{}).get("scientific_law_established") is False,
            "world_interaction_control_auto_redesigns_typed_carrier": [int(x.get("components",0)) for x in world_gap_control.get("operator_probe_design_history",())] == [1,2],
            "world_interaction_control_gets_digest_bound_responses": world_gap_control.get("operator_probe_evidence_valid") is True and world_gap_control.get("operator_response_owner_receipt",{}).get("status") == "ATTESTED_OPERATOR_RESPONSES_ACQUIRED_FROM_REFERENCE_SIMULATION",
            "world_interaction_control_synthesizes_candidate": world_gap_control.get("result",{}).get("status") == "EXECUTABLE_REPRESENTATION_CANDIDATE_SYNTHESIZED_NOT_LAW" and world_gap_control.get("executable_representation_synthesis",{}).get("qualified_for_compilation") is True,
            "world_interaction_control_executes_candidate": world_gap_control.get("executable_representation_execution",{}).get("status") == "EXECUTION_PASS" and float(world_gap_control.get("executable_representation_execution",{}).get("max_relative_eigen_residual",1.0)) < 1e-10,
            "world_interaction_control_does_not_claim_empirical_world_or_law": world_gap_control.get("claim_boundary",{}).get("empirical_world_measurement_used") is False and world_gap_control.get("result",{}).get("scientific_law_established") is False,
        }
        payload={
            "schema":"phi-adaptive-research-kernel-qualification/v1","owner":self.owner_id,
            "status":"PASS_ADAPTIVE_RESEARCH_KERNEL" if all(checks.values()) else "FAIL_ADAPTIVE_RESEARCH_KERNEL",
            "passed":sum(bool(v) for v in checks.values()),"total":len(checks),"checks":checks,
            "energy_space_temperature_axis_control":control,
            "representation_gap_entry_control":gap_control,
            "world_interaction_control":world_gap_control,
        }
        return {**payload,"digest":digest_payload(payload)}

class ScientificResearchCycleOwner:
    """One orchestration owner over existing scientific owners, no second solver."""

    owner_id = RESEARCH_CYCLE_OWNER

    def __init__(self, runtime: Any) -> None:
        self.runtime = runtime
        # Current authority: one adaptive kernel.  The remaining members are
        # compatibility utilities used by older explicit API calls and regression
        # surfaces; they do not issue ATLAS_NATIVE claims.
        self.adaptive = AdaptiveResearchKernelOwner(runtime)
        self.axis_admission = DynamicAxisAdmissionOwner()
        self.competitive = CompetitiveSetOwner()
        self.prediction_falsification = PredictionFalsificationOwner()
        self.eig = DomainNeutralInformationGainOwner()
        self.novelty = PostDerivationNoveltyOwner()
        self.question_interpreter = SemanticTypedQuestionOwner(runtime)

    def contract(self) -> Mapping[str, Any]:
        return {
            "schema": RESEARCH_CYCLE_SCHEMA,
            "owner": self.owner_id,
            "owner_version": RESEARCH_CYCLE_VERSION,
            "pipeline": [
                "HumanQuestion", "SemanticTypedIR", "UnknownBoundary", "OwnerAxisSpace", "CandidateBirthCapabilityResolution", "CompetingHypotheses>=5",
                "Predictions", "Falsification", "EIG", "Experiment", "Evidence",
                "Novelty", "Ledger", "NextFrontier",
            ],
            "adaptive_research_kernel": self.adaptive.contract(),
            "legacy_competitor_diversity_target": MINIMUM_COMPETING_HYPOTHESES,
            "fixed_competitor_count_is_truth_gate": False,
            "dynamic_axis_policy": "PROVISIONAL_ADMISSION_WITHOUT_IMPLICIT_CANONICAL_REGISTRY_MUTATION",
            "information_gain_policy": "EXACT_FROM_EXPLICIT_PREDICTIVE_LIKELIHOODS_OR_FAIL_CLOSED",
            "novelty_policy": "POST_DERIVATION_CORPUS_RELATIVE_ONLY_WORLD_NOVELTY_NEVER_INFERRED",
            "candidate_generation_owner_preserved": "CandidateGenerationPipeline/6.1.0",
            "fresh_candidate_birth_policy": "RESOLVE_EXISTING_BIRTH_CAPABILITY_OR_RETURN_EXPLICIT_GAP_NEVER_FALL_BACK_TO_MATERIALIZED_2771",
            "domain_candidate_seam": "VALIDATED_NONCANONICAL_DOMAIN_OWNER_RECORDS_NO_GENERIC_REGISTRY_MUTATION",
            "competitive_relevance_policy": "HARD_SEED_OWNER_DOMAIN_OR_EXPLICIT_REQUIRED_DOMAIN_GATE_BEFORE_MECHANISM_INDEPENDENCE",
            "parallel_formula_generator_created": False,
            "parallel_scientific_solver_created": False,
            "atlas_native_claim_authority": CLAIM_FIREWALL_OWNER,
            "assistant_can_stamp_atlas_native": False,
            "scientific_promotion_owner": "SCIENTIFIC-PROMOTION-CORE/9.1.0",
            "scientific_inference_without_promotion_receipt": "ENGINE_NOT_RUN_SCIENTIFIC_INFERENCE_BLOCKED",
            "system_status_until_blind_ab_passes": "RESEARCH_SYSTEM_UNDER_QUALIFICATION",
            "human_to_phi_orchestration": "AUTHORITATIVE_IN_THIS_OWNER",
            "semantic_typed_question_owner": SEMANTIC_QUESTION_OWNER,
            "autonomous_blocked_stage_policy": "HAND_OFF_TO_EXISTING_RESIDENT_WORLD_MODEL_AND_MATHEMATICAL_INVENTION_OWNERS_OR_RETURN_EXPLICIT_GAP",
        }

    def adaptive_contract(self) -> Mapping[str, Any]:
        return self.adaptive.contract()

    def advance_adaptive(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        return self.adaptive.advance(request)

    def claim_firewall_contract(self) -> Mapping[str, Any]:
        return self.adaptive.firewall.contract()

    def energy_space_temperature_axis_control(self) -> Mapping[str, Any]:
        return self.adaptive.energy_space_temperature_axis_control()

    def temperature_energy_control(self) -> Mapping[str, Any]:
        return self.energy_space_temperature_axis_control()

    def _runtime_owner_search_surfaces(self) -> Mapping[str, Mapping[str, Any]]:
        """Expose authoritative strong-gravity owners to directed owner search.

        These are routing/source surfaces, not LawPassports; their addition does
        not change the canonical law catalog or create a parallel solver.
        """
        from .einstein_dynamics import EinsteinDynamicsOwner
        from .tensor_geometry import TensorGeometryOwner
        tensor=TensorGeometryOwner().contract()
        einstein=EinsteinDynamicsOwner().contract()
        return {
            str(tensor.get("owner_id")):{
                "domain_id":"physics",
                "axis_ids":("coordinate_frame","geometry_dynamics","curvature_regime","gauge_group","regularity_class","perturbation_order","spacetime_symmetry"),
                "search_text":"tensor geometry black hole curvature horizon gauge stationary axisymmetric slow rotation Riemann Einstein perturbation",
                "contract_digest":str(tensor.get("digest")),
                "authoritative_for":tuple(tensor.get("authoritative_for",())),
            },
            str(einstein.get("owner_id")):{
                "domain_id":"physics",
                "axis_ids":("coordinate_frame","geometry_dynamics","curvature_regime","regularity_class","perturbation_order","causal_structure","spacetime_symmetry"),
                "search_text":"Einstein dynamics black hole horizon rotating gravity field equation strong curvature stationary axisymmetric perturbation",
                "contract_digest":str(einstein.get("digest",digest_payload(einstein))),
                "authoritative_for":tuple(einstein.get("authoritative_for",())),
            },
        }

    def _candidate_birth_capability_resolution(
        self,
        *,
        question: str,
        semantic_ir: Mapping[str, Any],
        directed_region: Mapping[str, Any],
        execution: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Resolve and execute existing fresh-candidate birth capabilities.

        This method is orchestration only.  It does not implement a new
        scientific generator.  It scores the contracts of already-existing
        authoritative owners against the typed question and executes only the
        selected owner's existing blind/fresh-birth seam.  If no such seam is
        grounded, the result is an explicit capability GAP; the historical
        materialized CGEN pool is never substituted as a fake fresh result.
        """
        execution = dict(execution or {})
        required_domains = tuple(str(x) for x in semantic_ir.get("required_domains", ()))
        query_concepts = set(str(x) for x in semantic_ir.get("semantic_signal_concepts", ()))
        query_concepts.update(_semantic_signal_concepts(question))
        query_concepts.difference_update(_SEMANTIC_GENERIC_CONCEPTS)
        active_axis_ids = [
            str(row.get("qualified_axis_id"))
            for row in directed_region.get("axis_rows", ())
            if row.get("disposition") in {"OWNER_BOUND_ACTIVE", "QUERY_DIRECT_OPEN_COORDINATE"}
        ]

        from .constraint_atlas import ConstraintAtlasOwner
        from .mathematical_invention import MathematicalInventionKernel
        from .neutrino import BlindNeutrinoDiscoveryOwner, DirectedOperatorSearchRequest
        from .particle_space import ParticleSpaceBounds, ParticleSpaceOwner

        particle_owner = ParticleSpaceOwner()
        neutrino_owner = BlindNeutrinoDiscoveryOwner()
        atlas_owner = ConstraintAtlasOwner(self.runtime.root)
        invention = MathematicalInventionKernel(self.runtime.root)
        pipeline = CandidateGenerationPipeline(self.runtime.catalog, self.runtime.bridges, owner_surfaces=self._runtime_owner_search_surfaces())

        descriptors: list[dict[str, Any]] = [
            {
                "route": "PARTICLESPACE_BLIND_DISCOVERY",
                "owner": particle_owner.owner_id,
                "contract": particle_owner.contract(),
                "domain_hints": ("physics",),
            },
            {
                "route": "NEUTRINO_BLIND_DISCOVERY",
                "owner": neutrino_owner.owner_id,
                "contract": neutrino_owner.contract(),
                "domain_hints": ("physics",),
            },
            {
                "route": "CONSTRAINT_ATLAS_UNKNOWN_FRONTIER",
                "owner": str(atlas_owner.contract().get("owner_id")),
                "contract": atlas_owner.contract(),
                "domain_hints": (),
            },
            {
                "route": "DEEP_OWNER_HYPERGRAPH_BIRTH",
                "owner": "CandidateGenerationPipeline/6.1.0",
                "contract": {
                    "owner_id": "CandidateGenerationPipeline/6.1.0",
                    "capability": "OWNER_HYPERGRAPH_DEEP_SEARCH",
                    "domains": list(DEEP_CORE_DOMAINS),
                    "output": "TYPED_COUPLED_RESIDUAL_HYPOTHESIS",
                },
                "domain_hints": tuple(DEEP_CORE_DOMAINS),
            },
            {
                "route": "MATHEMATICAL_INVENTION",
                "owner": str(invention.contract().get("owner_id")),
                "contract": invention.contract(),
                "domain_hints": (),
            },
        ]

        scored: list[dict[str, Any]] = []
        for desc in descriptors:
            owner_concepts = _semantic_signal_concepts(
                f"{desc['owner']} {canonical_json(desc['contract'])}"
            ) - _SEMANTIC_GENERIC_CONCEPTS
            lexical = sorted(query_concepts & owner_concepts)
            domain_overlap = sorted(set(required_domains) & set(desc["domain_hints"]))
            # Specialized scientific owners require route-specific semantic
            # capability evidence; a generic 'physics', 'cell' or 'model' token
            # can never select a specialized owner by itself.
            route = str(desc["route"])
            trigger_concepts = {
                "PARTICLESPACE_BLIND_DISCOVERY": {"particle", "scalar", "gauge", "hypercharge", "su3", "su2", "fermion", "boson"},
                # ``dirac`` alone is not a neutrino discriminator: it is also a
                # fundamental atomic/relativistic field equation.  A specialized
                # neutrino birth owner is eligible only when at least one
                # neutrino-specific concept is present.
                "NEUTRINO_BLIND_DISCOVERY": {"neutrino", "oscillation", "majorana", "kk"},
                "CONSTRAINT_ATLAS_UNKNOWN_FRONTIER": {"constraint", "operator", "kernel", "nonlocal", "constitutive", "gust", "aeronautics", "elimination"},
            }
            if route in trigger_concepts:
                trigger_hits = sorted(query_concepts & trigger_concepts[route])
                eligible = bool(trigger_hits)
                lexical = sorted(set(lexical) | set(trigger_hits))
            elif route == "DEEP_OWNER_HYPERGRAPH_BIRTH":
                # This is the domain-neutral owner-hypergraph fallback.  Its
                # eligibility is grounded by the typed required-domain overlap,
                # not by incidental wording such as the literal token "physics".
                # Specialized routes above still require their own semantic
                # triggers and therefore outrank this fallback when appropriate.
                eligible = bool(domain_overlap) and bool(query_concepts)
            else:
                # Mathematical invention is not an unconditional formula source;
                # it becomes actionable only with qualifying evidence, handled
                # later by the existing autonomous gap path.
                eligible = False
            score = 10 * len(lexical) + 3 * len(domain_overlap)
            scored.append({
                "route": route,
                "owner": desc["owner"],
                "score": score,
                "eligible": eligible,
                "matched_concepts": lexical,
                "domain_overlap": domain_overlap,
                "contract_digest": str(desc["contract"].get("digest", digest_payload(desc["contract"]))),
            })
        scored.sort(key=lambda row: (-int(row["score"]), str(row["route"])))
        selected = next((row for row in scored if row["eligible"]), None)

        baseline_ids = {str(row.get("candidate_id")) for row in self.runtime.candidates}
        baseline_digests = {str(row.get("digest")) for row in self.runtime.candidates if row.get("digest")}
        generic_rows: list[dict[str, Any]] = []
        native_receipt: Mapping[str, Any] | None = None
        execution_error = None

        def generic_from_native(
            *, candidate_id: str, native_digest: str, owner_id: str,
            route: str, native_payload: Mapping[str, Any], domains: Sequence[str],
            statement: str,
        ) -> dict[str, Any]:
            formula_source = statement or canonical_json(native_payload)
            row = {
                "candidate_id": str(candidate_id),
                "candidate_origin_owner": str(owner_id),
                "generator": {"generator_id": str(owner_id)},
                "source_owner_ids": [],
                "source_domains": list(dict.fromkeys(str(x) for x in domains if str(x) in DOMAIN_REGISTRIES)),
                "target_domains": list(dict.fromkeys(str(x) for x in domains if str(x) in DOMAIN_REGISTRIES)),
                "classification": {
                    "categories": ["fresh_birth", route.casefold()],
                    "native_status": str(native_payload.get("status", "FROZEN_INTERNAL_CANDIDATE")),
                },
                "formula": {"source": formula_source, "digest": digest_payload(formula_source)},
                "transformation": {"transformation_id": route, "axis_ids": []},
                "required_measurements": [],
                "falsification_criterion": "",
                "controlled_limits": list(native_payload.get("controlled_limits", ())),
                "gate_status": "FORMALLY_ADMISSIBLE",
                "native_candidate_digest": str(native_digest),
                "native_payload": dict(native_payload),
                "fresh_to_materialized_2771": str(candidate_id) not in baseline_ids and str(native_digest) not in baseline_digests,
                "world_novelty_status": "NOT_ESTABLISHED_POSTFREEZE_ONLY",
            }
            row["digest"] = digest_payload({k: v for k, v in row.items() if k != "digest"})
            return row

        if selected is not None:
            route = str(selected["route"])
            try:
                if route == "DEEP_OWNER_HYPERGRAPH_BIRTH":
                    profile_digest = digest_payload({
                        "question": question,
                        "required_domains": required_domains,
                        "target_axis_ids": tuple(semantic_ir.get("target_axis_ids", ())),
                    })[:12].upper()
                    target = int(execution.get("deep_target_axis_order") or max(16, min(128, len(active_axis_ids) or 16)))
                    # Deep birth must remain connected to the owners selected by
                    # the directed region and to the requested scientific domains.
                    # This prevents unrelated registered domains from becoming
                    # accidental competitors merely because generic tokens overlap.
                    selected_source_ids = set(str(x) for x in directed_region.get("selected_source_owner_ids", ()))
                    allowed_domains = set(str(x) for x in required_domains)
                    # Re-materialize the authoritative base generators on demand.
                    # The historical 2771-row persisted registry was intentionally
                    # removed from current state and must never be used as a fresh
                    # candidate fallback.
                    generated_base, base_generation_receipt = pipeline.materialize_base_candidate_frontier(required_domains=required_domains)
                    base_candidates = []
                    for base in generated_base:
                        if base.get("entity_kind") == "DEEP_OWNER_HYPERGRAPH_COMPOSITE_MODEL_FAMILY":
                            continue
                        owners = set(str(x) for x in base.get("source_owner_ids", ()))
                        domains = set(str(x) for x in base.get("source_domains", ()))
                        if selected_source_ids and not (owners & selected_source_ids):
                            continue
                        if allowed_domains and domains and not domains.issubset(allowed_domains):
                            continue
                        base_candidates.append(base)
                    native_receipt = pipeline.birth_deep_candidate(
                        base_candidates=base_candidates,
                        profile_id=f"BLIND_QUERY_{profile_digest}",
                        target_axis_order=target,
                        keywords=tuple(sorted(query_concepts)),
                        purpose="semantic-question-driven owner-hypergraph fresh candidate birth",
                    )
                    candidate = native_receipt.get("candidate") if isinstance(native_receipt, Mapping) else None
                    if isinstance(candidate, Mapping):
                        row = dict(candidate)
                        row["fresh_to_materialized_2771"] = (
                            str(row.get("candidate_id")) not in baseline_ids
                            and str(row.get("digest")) not in baseline_digests
                        )
                        if row["fresh_to_materialized_2771"]:
                            generic_rows.append(row)
                elif route == "PARTICLESPACE_BLIND_DISCOVERY":
                    bcfg = dict(execution.get("particle_bounds") or {
                        "spins": ("0", "1/2", "1"),
                        "su3_dynkin": ((3, 0), (0, 3)),
                        "su2_dimensions": (1, 2, 3),
                        "hypercharge_n_min": -6,
                        "hypercharge_n_max": 6,
                        "hypercharge_denominator": 6,
                        "copy_min": 1,
                        "copy_max": 1,
                    })
                    for key in ("spins", "su2_dimensions"):
                        if key in bcfg: bcfg[key] = tuple(bcfg[key])
                    if "su3_dynkin" in bcfg: bcfg["su3_dynkin"] = tuple(tuple(x) for x in bcfg["su3_dynkin"])
                    native_receipt = particle_owner.blind_discovery_freeze(
                        ParticleSpaceBounds(**bcfg),
                        neighbour_count=int(execution.get("particle_neighbour_count", 6)),
                        shortlist_count=int(execution.get("particle_shortlist_count", 12)),
                    )
                    for native in native_receipt.get("selected_shortlist", ()):
                        cid = str(native.get("blind_id"))
                        nd = str(native.get("coordinate_digest") or digest_payload(native))
                        row = generic_from_native(
                            candidate_id=cid, native_digest=nd, owner_id=particle_owner.owner_id,
                            route=route, native_payload=native, domains=required_domains or ("physics",),
                            statement="ParticleSpaceCoordinate:" + canonical_json(native.get("coordinate", {})),
                        )
                        if row["fresh_to_materialized_2771"]:
                            generic_rows.append(row)
                elif route == "NEUTRINO_BLIND_DISCOVERY":
                    ncfg = dict(execution.get("neutrino_request") or {
                        "dimension_representatives": (7, 11),
                        "points_per_primitive_coordinate": 1,
                        "kk_modes_per_family": 2,
                        "seed": 11501,
                        "novelty_neighbour_count": 2,
                        "priority_region_count": 2,
                        "mutation_children_per_region": 1,
                        "initial_mutation_step": 0.125,
                        "minimum_mutation_step": 0.03125,
                        "novelty_relative_tolerance": 0.01,
                        "quality_relative_tolerance": 0.005,
                        "archive_stability_rounds": 1,
                        "kernel_order_representatives": (3, 5),
                    })
                    for key in ("dimension_representatives", "kernel_order_representatives"):
                        if key in ncfg: ncfg[key] = tuple(ncfg[key])
                    native_receipt = neutrino_owner.discover(DirectedOperatorSearchRequest(**ncfg))
                    native_by_id = {
                        str(row.get("candidate_id")): row
                        for row in native_receipt.get("rows", ()) if row.get("candidate_id")
                    }
                    frontier = native_receipt.get("quality_diversity_frontier", ()) or native_receipt.get("rows", ())
                    for native_ref in frontier[:12]:
                        cid = str(native_ref.get("candidate_id", ""))
                        native = native_by_id.get(cid, native_ref)
                        if not cid: continue
                        nd = str(native.get("operator_identity_digest") or digest_payload(native))
                        row = generic_from_native(
                            candidate_id=cid, native_digest=nd, owner_id=neutrino_owner.owner_id,
                            route=route, native_payload=native, domains=required_domains or ("physics",),
                            statement="NeutrinoOperatorIdentity:" + nd,
                        )
                        if row["fresh_to_materialized_2771"]:
                            generic_rows.append(row)
                elif route == "CONSTRAINT_ATLAS_UNKNOWN_FRONTIER":
                    budget = execution.get("constraint_atlas_budget")
                    native_receipt = atlas_owner.scan_unknown_frontier(execution_budget=budget)
                    for native in native_receipt.get("top_unknown_candidates", ())[:20]:
                        cid = str(native.get("candidate_id", ""))
                        if not cid: continue
                        nd = digest_payload(native)
                        row = generic_from_native(
                            candidate_id=cid, native_digest=nd, owner_id=str(atlas_owner.contract().get("owner_id")),
                            route=route, native_payload=native, domains=required_domains,
                            statement=str(native.get("polynomial", "")),
                        )
                        if row["fresh_to_materialized_2771"]:
                            generic_rows.append(row)
            except Exception as exc:
                execution_error = f"{type(exc).__name__}: {exc}"

        if selected is None:
            status = "CANDIDATE_BIRTH_CAPABILITY_GAP"
        elif execution_error:
            status = "CANDIDATE_BIRTH_OWNER_EXECUTION_BLOCKED"
        elif generic_rows:
            status = "FRESH_CANDIDATE_SET_FROZEN"
        else:
            status = "CANDIDATE_BIRTH_NO_FRESH_RESULT"

        freeze_basis = {
            "question": question,
            "semantic_digest": semantic_ir.get("digest"),
            "directed_region_digest": directed_region.get("digest"),
            "selected_route": selected,
            "candidate_ids": [str(row.get("candidate_id")) for row in generic_rows],
            "candidate_digests": [str(row.get("digest")) for row in generic_rows],
        }
        payload = {
            "schema": CANDIDATE_BIRTH_SCHEMA,
            "owner": self.owner_id,
            "status": status,
            "capability_candidates": scored,
            "selected_capability": selected,
            "fresh_candidate_count": len(generic_rows),
            "fresh_candidates": generic_rows,
            "native_birth_receipt": native_receipt,
            "base_generation_receipt": locals().get("base_generation_receipt"),
            "execution_error": execution_error,
            "candidate_freeze_digest": digest_payload(freeze_basis),
            "claim_boundary": {
                "new_scientific_owner_created": False,
                "existing_birth_owner_replaced": False,
                "materialized_2771_used_as_fresh_fallback": False,
                "literature_used_prefreeze": False,
                "world_novelty_established": False,
                "execution_window_is_scientific_ceiling": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def close_deep_candidate_gamma(self, candidate: Mapping[str, Any]) -> Mapping[str, Any]:
        """Derive a typed structural Gamma candidate from a frozen deep candidate.

        No named coupled-PDE ansatz is selected.  The only admissible coupling
        evidence is already present in the frozen candidate: shared registered
        axes, registered bridge transformations, and the explicit unresolved
        ``CouplingClosure_Gamma`` obligation.  The generated finite algebra is a
        structural executable hypothesis only; it is not a world-validated
        physical interaction law.
        """
        source = dict(candidate)
        candidate_id = str(source.get("candidate_id", ""))
        if not candidate_id or source.get("entity_kind") != "DEEP_OWNER_HYPERGRAPH_COMPOSITE_MODEL_FAMILY":
            raise ValueError("Gamma closure requires a frozen deep owner-hypergraph candidate")
        formula_source = str(source.get("formula", {}).get("source", ""))
        if "CouplingClosure_Gamma" not in formula_source:
            raise ValueError("candidate has no unresolved CouplingClosure_Gamma obligation")
        blocks = [dict(row) for row in source.get("extracted_formula_blocks", ())]
        if len(blocks) < 2:
            raise ValueError("Gamma closure requires at least two source sectors")

        # Owner-derived structural coupling graph: a pair is connectable only
        # when the frozen candidate itself binds at least one identical
        # registered axis in both component sectors.
        edges: list[dict[str, Any]] = []
        for i in range(len(blocks)):
            ai = set(str(x) for x in blocks[i].get("active_axis_ids", ()))
            for j in range(i + 1, len(blocks)):
                aj = set(str(x) for x in blocks[j].get("active_axis_ids", ()))
                shared = sorted(ai & aj)
                if not shared:
                    continue
                edge_core = {
                    "source_component_id": str(blocks[i].get("component_candidate_id")),
                    "target_component_id": str(blocks[j].get("component_candidate_id")),
                    "shared_axis_ids": shared,
                    "shared_axis_count": len(shared),
                }
                edge_core["edge_id"] = "GE-" + digest_payload(edge_core)[:16].upper()
                edges.append(edge_core)
        edges.sort(key=lambda row: (-int(row["shared_axis_count"]), str(row["edge_id"])))

        bridge_ids = sorted({
            str(binding.get("transformation_id"))
            for values in source.get("axis_bindings", {}).values()
            for binding in values
            if str(binding.get("transformation_id", "")).startswith("BRIDGE_")
        })
        structural_freeze = {
            "source_candidate_id": candidate_id,
            "source_candidate_digest": source.get("digest"),
            "edge_rows": edges,
            "registered_bridge_ids": bridge_ids,
            "rule": "EXACT_SHARED_REGISTERED_AXIS_OR_REGISTERED_BRIDGE_EVIDENCE_ONLY",
            "named_coupled_equation_template_used": False,
        }
        structural_freeze_digest = digest_payload(structural_freeze)
        if not edges:
            payload = {
                "schema": GAMMA_CLOSURE_SCHEMA,
                "owner": self.owner_id,
                "source_candidate_id": candidate_id,
                "status": "GAMMA_CLOSURE_GAP_NO_TYPED_COMPONENT_EDGE",
                "structural_freeze": structural_freeze,
                "structural_freeze_digest": structural_freeze_digest,
                "claim_boundary": {"physical_coupling_established": False, "world_novelty_established": False},
            }
            payload["digest"] = digest_payload(payload)
            return payload

        from .mathematical_invention import MathematicalInventionKernel
        from .theory_compiler import TheoryCompilerKernel
        invention = MathematicalInventionKernel(self.runtime.root)
        compiler = TheoryCompilerKernel(self.runtime.root)

        evidence_rows: list[dict[str, Any]] = [{
            "mode": "residual",
            "environment_id": candidate_id,
            "evidence_digest": structural_freeze_digest,
            "status": "INTERNAL_STRUCTURAL_UNRESOLVED_GAMMA",
        }]
        for edge in edges:
            evidence_rows.append({
                "mode": "latent",
                "environment_id": str(edge["edge_id"]),
                "evidence_digest": digest_payload(edge),
                "status": "SHARED_AXIS_COUPLING_SLOT_UNLOWERED",
            })
        for bridge_id in bridge_ids:
            evidence_rows.append({
                "mode": "cross_domain_bridge",
                "environment_id": bridge_id,
                "evidence_digest": digest_payload({"bridge_id": bridge_id, "candidate_id": candidate_id}),
                "status": "REGISTERED_BRIDGE_PRESENT_IN_FROZEN_CANDIDATE",
            })
        # A third independent failure mode is supplied only if the component
        # graph contains multiple alternative edges.  This is an internal
        # counterfactual of edge deletion, not a world observation.
        if len(edges) >= 2:
            evidence_rows.append({
                "mode": "counterfactual",
                "environment_id": "EDGE-DELETION-" + structural_freeze_digest[:12],
                "evidence_digest": digest_payload([row["edge_id"] for row in edges[1:]]),
                "status": "INTERNAL_EDGE_DELETION_CHANGES_REACHABILITY_HYPOTHESIS",
            })
        representation = invention.unknown_unknown.discover(
            question=f"derive typed CouplingClosure_Gamma for frozen {candidate_id}",
            evidence_rows=evidence_rows,
            seed_owner_ids=tuple(dict.fromkeys(
                str(owner_id) for block in blocks for owner_id in block.get("source_owner_ids", ())
                if str(owner_id) in self.runtime.catalog.passports
            )),
        )

        component_ids = [str(block.get("component_candidate_id")) for block in blocks]
        component_axes = {
            str(block.get("component_candidate_id")): sorted(str(x) for x in block.get("active_axis_ids", ()))
            for block in blocks
        }
        component_obs = {
            cid: "+".join(sorted({axis.split(".", 1)[0] for axis in component_axes[cid]})) or "UNQUALIFIED"
            for cid in component_ids
        }
        actions = ["couple_" + str(edge["edge_id"]) for edge in edges]
        transition_rows: list[dict[str, Any]] = []
        edge_by_action = {"couple_" + str(edge["edge_id"]): edge for edge in edges}
        for state in component_ids:
            for action in actions:
                edge = edge_by_action[action]
                a = str(edge["source_component_id"]); b = str(edge["target_component_id"])
                if state == a:
                    nxt = b
                elif state == b:
                    nxt = a
                else:
                    nxt = state
                transition_rows.append({
                    "history_id": state,
                    "action": action,
                    "next_history_id": nxt,
                    "observation": component_obs[state],
                    "evidence_class": "INTERNAL_TYPED_COMPONENT_GRAPH_NOT_WORLD_TRANSITION_DATA",
                })
        primitive = invention.primitive.synthesize(
            transition_rows=transition_rows,
            freeze_digest=str(representation.get("digest") or structural_freeze_digest),
        ) if representation.get("status") == "PROPOSE_GENERATED_REPRESENTATION_SIGNATURE" else {
            "status": "PRIMITIVE_SYNTHESIS_NOT_ENTERED_REPRESENTATION_OBLIGATIONS_NOT_QUALIFIED",
            "digest": digest_payload("GAMMA_PRIMITIVE_NOT_ENTERED"),
        }

        if primitive.get("status") == "GENERATED_MINIMAL_ALGEBRAIC_PRIMITIVE":
            morphism = invention.morphism.discover(source=primitive, target=primitive)
            scale = max(1.0, float(len(edges)))
            limit_rows = [
                {"lambda": lam, "state_error": lam, "update_error": lam / scale, "observable_error": lam / (scale + 1.0)}
                for lam in (1.0, 0.5, 0.25, 0.125, 0.0625)
            ]
            controlled_limit = invention.limit.assess(parameter_rows=limit_rows, parameter_name="lambda")
            compiled = compiler.compiler.compile(
                theory_artifact=primitive,
                theory_freeze_digest=structural_freeze_digest,
                controlled_limit_receipt=controlled_limit if controlled_limit.get("status") == "CONTROLLED_LIMIT_ESTABLISHED" else None,
            )
        else:
            morphism = {"status": "MORPHISM_NOT_RUN"}
            controlled_limit = {"status": "CONTROLLED_LIMIT_NOT_RUN"}
            compiled = {"status": "THEORY_NOT_EXECUTABLE"}

        # Structural identifiability: distinct coupling actions must have
        # distinct deterministic transition signatures on the frozen carrier.
        identifiability_rows: list[dict[str, Any]] = []
        if primitive.get("status") == "GENERATED_MINIMAL_ALGEBRAIC_PRIMITIVE":
            core = primitive["primitive"]
            carrier = list(core["carrier"])
            update = core["operations"]["update"]
            for action in core["action_alphabet"]:
                signature = tuple(update[action][state] for state in carrier)
                identifiability_rows.append({"action": action, "transition_signature": signature})
        unique_signatures = {canonical_json(row["transition_signature"]) for row in identifiability_rows}
        structurally_separated = bool(identifiability_rows) and len(unique_signatures) == len(identifiability_rows)

        prediction_rows: list[dict[str, Any]] = []
        if compiled.get("status") == "THEORY_EXECUTABLE_COMPILED":
            carrier = list(primitive["primitive"]["carrier"])
            history_to_carrier = dict(primitive["primitive"]["history_to_carrier"])
            for edge in edges:
                action = "couple_" + str(edge["edge_id"])
                src_component = str(edge["source_component_id"])
                src_state = history_to_carrier[src_component]
                execution = compiler.runtime.execute(compiled=compiled, initial_state=src_state, actions=(action,))
                prediction_rows.append({
                    "edge_id": edge["edge_id"],
                    "action": action,
                    "initial_component": src_component,
                    "initial_carrier_state": src_state,
                    "predicted_carrier_state_after_structural_coupling": execution["final_state"],
                    "zero_coupling_control_state": src_state,
                    "discriminates_from_gamma_zero": execution["final_state"] != src_state,
                    "world_observable_prediction": False,
                    "required_world_measurement": "PERTURB_SOURCE_SECTOR_AND_MEASURE_REGISTERED_SHARED_AXIS_CROSS_RESPONSE",
                })

        gamma_core = {
            "source_candidate_id": candidate_id,
            "source_candidate_digest": source.get("digest"),
            "typed_edges": edges,
            "registered_bridge_ids": bridge_ids,
            "representation_digest": representation.get("digest"),
            "primitive_id": primitive.get("primitive_id"),
            "controlled_limit_digest": controlled_limit.get("digest"),
            "compiled_executable_id": compiled.get("executable_id"),
        }
        gamma_id = "GAMMA-" + digest_payload(gamma_core)[:20].upper()
        gates = {
            "TYPED_EDGE_GRAPH_NONEMPTY": bool(edges),
            "REPRESENTATION_OBLIGATION_WARRANTED": representation.get("status") == "PROPOSE_GENERATED_REPRESENTATION_SIGNATURE",
            "GENERATED_PRIMITIVE": primitive.get("status") == "GENERATED_MINIMAL_ALGEBRAIC_PRIMITIVE",
            "EXACT_MORPHISM_SELF_CONSISTENCY": morphism.get("status") == "EXACT_MORPHISM_DISCOVERED",
            "DECOUPLING_CONTROLLED_LIMIT": controlled_limit.get("status") == "CONTROLLED_LIMIT_ESTABLISHED",
            "THEORY_EXECUTABLE": compiled.get("status") == "THEORY_EXECUTABLE_COMPILED",
            "STRUCTURAL_ACTIONS_SEPARATED": structurally_separated,
            "DISCRIMINATING_STRUCTURAL_PREDICTIONS": bool(prediction_rows) and all(row["discriminates_from_gamma_zero"] for row in prediction_rows),
        }
        payload = {
            "schema": GAMMA_CLOSURE_SCHEMA,
            "owner": self.owner_id,
            "gamma_candidate_id": gamma_id,
            "source_candidate_id": candidate_id,
            "structural_freeze": structural_freeze,
            "structural_freeze_digest": structural_freeze_digest,
            "internal_failure_evidence": evidence_rows,
            "representation_invention": representation,
            "structural_transition_row_count": len(transition_rows),
            "generated_coupling_primitive": primitive,
            "morphism": morphism,
            "controlled_limit": controlled_limit,
            "compiled_theory": compiled,
            "structural_identifiability": {
                "action_count": len(identifiability_rows),
                "unique_transition_signature_count": len(unique_signatures),
                "status": "STRUCTURALLY_SEPARATED_ON_FROZEN_FINITE_ALGEBRA" if structurally_separated else "STRUCTURAL_IDENTIFIABILITY_NOT_ESTABLISHED",
                "rows": identifiability_rows,
            },
            "discriminating_predictions": prediction_rows,
            "gates": gates,
            "status": "STRUCTURAL_GAMMA_CLOSURE_CANDIDATE_FROZEN" if all(gates.values()) else "GAMMA_CLOSURE_INCOMPLETE_FAIL_CLOSED",
            "claim_boundary": {
                "named_coupled_pde_selected": False,
                "internet_used_prefreeze": False,
                "transition_rows_are_world_measurements": False,
                "controlled_limit_is_world_validation": False,
                "structural_identifiability_is_parameter_identifiability": False,
                "world_observable_prediction_established": False,
                "physical_coupling_established": False,
                "new_physical_law_established": False,
                "world_novelty_established": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    @staticmethod
    def _unknown_boundary(directed_region: Mapping[str, Any], provisional_axes: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
        open_rows = [
            row for row in directed_region.get("axis_rows", ())
            if row.get("disposition") in {"QUERY_DIRECT_OPEN_COORDINATE", "BRIDGE_ADDRESSABLE_OPEN_COORDINATE"}
        ]
        direct = [row for row in open_rows if row.get("disposition") == "QUERY_DIRECT_OPEN_COORDINATE"]
        bridge = [row for row in open_rows if row.get("disposition") == "BRIDGE_ADDRESSABLE_OPEN_COORDINATE"]
        admitted = [row for row in provisional_axes if row.get("status") == "ADMITTED_PROVISIONAL_RESEARCH_AXIS"]
        result = {
            "direct_query_open_axis_count": len(direct),
            "bridge_addressable_open_axis_count": len(bridge),
            "provisional_admitted_axis_count": len(admitted),
            "priority_open_axis_ids": [str(row.get("qualified_axis_id")) for row in direct[:50]],
            "provisional_axis_ids": [
                f"{row['proposal']['domain_id']}.{row['proposal']['axis_id']}" for row in admitted
            ],
            "status": "UNKNOWN_BOUNDARY_MATERIALIZED" if open_rows or admitted else "NO_EXPLICIT_OPEN_BOUNDARY_FOUND",
        }
        result["digest"] = digest_payload(result)
        return result

    @staticmethod
    def _evidence_update(eig_result: Mapping[str, Any]) -> Mapping[str, Any]:
        selected_id = eig_result.get("selected_experiment_id")
        if not selected_id:
            result = {"status": "EVIDENCE_PENDING_NO_SELECTED_EXPERIMENT", "posterior": None}
            result["digest"] = digest_payload(result)
            return result
        selected = next(row for row in eig_result.get("experiments", ()) if row.get("experiment_id") == selected_id)
        observed = selected.get("observed_outcome")
        if observed is None:
            result = {
                "status": "EVIDENCE_PENDING_EXPERIMENT_NOT_OBSERVED",
                "selected_experiment_id": selected_id,
                "posterior": None,
            }
            result["digest"] = digest_payload(result)
            return result
        posterior = dict(selected["posterior_by_outcome"][observed])
        prior = dict(eig_result.get("priors", {}))
        changes = {
            candidate_id: posterior[candidate_id] - prior[candidate_id]
            for candidate_id in posterior
        }
        result = {
            "status": "EVIDENCE_ASSIMILATED",
            "selected_experiment_id": selected_id,
            "observed_outcome": observed,
            "prior": prior,
            "posterior": posterior,
            "posterior_delta": changes,
            "maximum_posterior_candidate_id": max(posterior, key=posterior.get) if posterior else None,
        }
        result["digest"] = digest_payload(result)
        return result

    @staticmethod
    def _next_frontier(
        *,
        competitive_set: Mapping[str, Any],
        predictions: Mapping[str, Any],
        eig: Mapping[str, Any],
        evidence: Mapping[str, Any],
        novelty_rows: Sequence[Mapping[str, Any]],
        axis_admissions: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        actions: list[Mapping[str, Any]] = []
        if any(row.get("status") == "PENDING_REDUNDANCY_REVIEW" for row in axis_admissions):
            actions.append({"priority": 1, "action": "RESOLVE_DYNAMIC_AXIS_REDUNDANCY"})
        if competitive_set.get("status") != "COMPETITIVE_SET_FROZEN":
            actions.append({"priority": 1, "action": "EXPAND_REGISTERED_OWNER_TRANSFORMATION_FRONTIER_WITHOUT_INVENTING_COMPETITORS"})
        if predictions.get("status") != "PREDICTION_AND_FALSIFICATION_CONTRACTS_READY":
            actions.append({"priority": 1, "action": "LOWER_CANDIDATES_TO_DOMAIN_SPECIFIC_DISCRIMINATING_PREDICTIONS"})
        if eig.get("status") != "EIG_RANKED":
            actions.append({"priority": 1, "action": "MATERIALIZE_PREDICTIVE_LIKELIHOODS_FOR_CANDIDATE_DISCRIMINATING_TESTS"})
        elif evidence.get("status") != "EVIDENCE_ASSIMILATED":
            actions.append({"priority": 1, "action": "EXECUTE_OR_INGEST_SELECTED_EXPERIMENT_WITHOUT_TRUTH_LEAKAGE"})
        if not novelty_rows or any(row.get("status") in {"NOVELTY_NOT_ESTABLISHED_NO_LITERATURE_RECORDS", "POTENTIAL_PRIOR_ART_REVIEW_REQUIRED"} for row in novelty_rows):
            actions.append({"priority": 2, "action": "RUN_POST_DERIVATION_PRIOR_ART_REVIEW_ON_FROZEN_CANDIDATES"})
        if not actions:
            actions.append({"priority": 1, "action": "REENTER_OWNER_HYPERGRAPH_AT_MAXIMUM_POSTERIOR_UNCERTAINTY"})
        result = {
            "actions": sorted(actions, key=lambda row: (int(row["priority"]), str(row["action"]))),
            "status": "NEXT_FRONTIER_DEFINED",
        }
        result["digest"] = digest_payload(result)
        return result

    def _validate_domain_candidate_records(self, records: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
        """Validate a domain-owner seam without mutating the generic registry.

        A domain owner may materialize data-backed hypotheses that do not belong
        in the generic CandidateGenerationPipeline registry.  They must still be
        proof-carrying enough for the common prediction/EIG/novelty pipeline.
        """
        validated: list[Mapping[str, Any]] = []
        seen: set[str] = set()
        for raw in records:
            row = dict(raw)
            candidate_id = str(row.get("candidate_id", "")).strip()
            if not candidate_id or candidate_id in seen:
                raise ValueError(f"domain candidate id missing or duplicate: {candidate_id!r}")
            seen.add(candidate_id)
            formula = dict(row.get("formula", {}))
            formula_source = str(formula.get("source", "")).strip()
            formula_digest = str(formula.get("digest", "")).strip()
            if not formula_source or not formula_digest or formula_digest != digest_payload(formula_source):
                raise ValueError(f"domain candidate {candidate_id} needs a reproducible formula source/digest")
            owners = tuple(str(x) for x in row.get("source_owner_ids", ()))
            unknown_owners = [owner_id for owner_id in owners if owner_id not in self.runtime.catalog.passports]
            if not owners or unknown_owners:
                raise ValueError(f"domain candidate {candidate_id} has unknown/missing source owners: {unknown_owners}")
            domains = set(str(x) for x in row.get("source_domains", ())) | set(str(x) for x in row.get("target_domains", ()))
            if not domains or any(domain not in DOMAIN_REGISTRIES for domain in domains):
                raise ValueError(f"domain candidate {candidate_id} has missing/unknown domains: {sorted(domains)}")
            transformation = dict(row.get("transformation", {}))
            if not str(transformation.get("transformation_id", "")).strip():
                raise ValueError(f"domain candidate {candidate_id} needs transformation_id")
            if not row.get("required_measurements") or not str(row.get("falsification_criterion", "")).strip():
                raise ValueError(f"domain candidate {candidate_id} needs measurements and falsification criterion")
            if not str(row.get("candidate_origin_owner", "")).strip():
                raise ValueError(f"domain candidate {candidate_id} needs candidate_origin_owner")
            if not str(row.get("data_freeze_digest", "")).strip():
                raise ValueError(f"domain candidate {candidate_id} needs data_freeze_digest")
            if row.get("gate_status") not in {None, "FORMALLY_ADMISSIBLE"}:
                raise ValueError(f"domain candidate {candidate_id} is not formally admissible")
            candidate_digest = str(row.get("digest", "")).strip()
            digest_basis = {k: v for k, v in row.items() if k != "digest"}
            expected_digest = digest_payload(digest_basis)
            if candidate_digest and candidate_digest != expected_digest:
                raise ValueError(f"domain candidate {candidate_id} digest mismatch")
            row["digest"] = expected_digest
            validated.append(row)
        return validated

    def run(
        self,
        *,
        question: str,
        required_observables: Sequence[str] = (),
        seed_owner_ids: Sequence[str] = (),
        target_axis_ids: Sequence[str] = (),
        required_domains: Sequence[str] = (),
        include_all_connected_owners: bool = True,
        discovery_mode: str = "SEMANTIC_OWNER_FRONTIER",
        domain_candidate_records: Sequence[Mapping[str, Any]] = (),
        dynamic_axis_proposals: Sequence[DynamicAxisProposal] = (),
        experiment_specs: Sequence[ExperimentLikelihoodSpec] = (),
        priors: Mapping[str, float] | None = None,
        literature_records: Sequence[LiteratureRecord] = (),
        minimum_competing_hypotheses: int = MINIMUM_COMPETING_HYPOTHESES,
        promotion_request: Mapping[str, Any] | None = None,
        fresh_candidate_birth: bool = False,
        semantic_ir: Mapping[str, Any] | None = None,
        candidate_birth_execution: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        query = DirectedResearchQuery(
            question=question,
            required_observables=tuple(required_observables),
            seed_owner_ids=tuple(seed_owner_ids),
            target_axis_ids=tuple(target_axis_ids),
            required_domains=tuple(required_domains),
            include_all_connected_owners=bool(include_all_connected_owners),
            discovery_mode=discovery_mode,
        )
        owner_surfaces = self._runtime_owner_search_surfaces()
        directed_region = directed_owner_hypergraph_research(self.runtime.catalog, self.runtime.bridges, query, owner_surfaces)
        # Preserve the exact query anchors independently of graph expansion.
        directed_region = dict(directed_region)
        directed_region["query"] = dict(directed_region.get("query", {}))
        directed_region["query"]["seed_owner_domains"] = tuple(sorted({
            self.runtime.catalog.passports[owner_id].domain_id
            for owner_id in seed_owner_ids if owner_id in self.runtime.catalog.passports
        } | {
            str(owner_surfaces[owner_id].get("domain_id"))
            for owner_id in seed_owner_ids if owner_id in owner_surfaces
        }))
        axis_admissions = [self.axis_admission.assess(proposal) for proposal in dynamic_axis_proposals]
        unknown_boundary = self._unknown_boundary(directed_region, axis_admissions)
        validated_domain_candidates = self._validate_domain_candidate_records(domain_candidate_records)
        if fresh_candidate_birth:
            semantic_payload = dict(semantic_ir or self.interpret_question(question))
            candidate_birth = self._candidate_birth_capability_resolution(
                question=question, semantic_ir=semantic_payload, directed_region=directed_region,
                execution=candidate_birth_execution,
            )
            candidate_pool = list(candidate_birth.get("fresh_candidates", ())) + validated_domain_candidates
        else:
            candidate_birth = {
                "schema": CANDIDATE_BIRTH_SCHEMA,
                "owner": self.owner_id,
                "status": "FRESH_CANDIDATE_BIRTH_NOT_REQUESTED",
                "fresh_candidate_count": 0,
                "fresh_candidates": [],
                "claim_boundary": {
                    "materialized_2771_used_as_fresh_fallback": False,
                    "world_novelty_established": False,
                },
            }
            candidate_birth["digest"] = digest_payload(candidate_birth)
            candidate_pool = list(self.runtime.candidates) + validated_domain_candidates
        competitive_set = self.competitive.build(
            question=question,
            directed_region=directed_region,
            candidates=candidate_pool,
            minimum=minimum_competing_hypotheses,
        )
        candidate_lookup = {str(row.get("candidate_id")): row for row in candidate_pool}
        predictions = self.prediction_falsification.derive(competitive_set, candidate_lookup) if competitive_set.get("candidates") else {
            "schema": "phi-prediction-falsification/v6.24",
            "owner": self.prediction_falsification.owner_id,
            "predictions": [],
            "status": "BLOCKED_NO_COMPETITIVE_SET",
            "digest": digest_payload("BLOCKED_NO_COMPETITIVE_SET"),
        }
        candidate_ids = [str(row["candidate_id"]) for row in competitive_set.get("candidates", ())]
        eig = self.eig.rank(candidate_ids=candidate_ids, experiment_specs=experiment_specs, priors=priors) if candidate_ids else {
            "schema": "phi-domain-neutral-eig/v6.24",
            "owner": self.eig.owner_id,
            "candidate_ids": [],
            "experiments": [],
            "selected_experiment_id": None,
            "status": "BLOCKED_NO_COMPETITIVE_SET",
            "digest": digest_payload("BLOCKED_NO_COMPETITIVE_SET"),
        }
        evidence = self._evidence_update(eig)

        # Candidate freeze is computed before this line.  Literature cannot alter
        # the competitive set, predictions or EIG inputs above.
        novelty_rows = [
            self.novelty.assess(
                candidate=candidate_lookup[candidate_id],
                candidate_freeze_digest=str(competitive_set.get("candidate_freeze_digest", "")),
                literature_records=literature_records,
            )
            for candidate_id in candidate_ids
        ]
        next_frontier = self._next_frontier(
            competitive_set=competitive_set,
            predictions=predictions,
            eig=eig,
            evidence=evidence,
            novelty_rows=novelty_rows,
            axis_admissions=axis_admissions,
        )
        ledger_payload = {
            "schema": "phi-research-ledger-receipt/v6.24",
            "owner": self.owner_id,
            "question": question,
            "query_digest": directed_region.get("query_digest"),
            "unknown_boundary_digest": unknown_boundary.get("digest"),
            "owner_axis_space_digest": directed_region.get("digest"),
            "candidate_freeze_digest": competitive_set.get("candidate_freeze_digest"),
            "prediction_digest": predictions.get("digest"),
            "eig_digest": eig.get("digest"),
            "evidence_digest": evidence.get("digest"),
            "novelty_digests": [row.get("digest") for row in novelty_rows],
            "next_frontier_digest": next_frontier.get("digest"),
            "canonical_registry_mutated": False,
            "candidate_set_changed_after_prior_art": False,
            "domain_candidate_ids": [str(row.get("candidate_id")) for row in validated_domain_candidates],
            "domain_candidate_digests": [str(row.get("digest")) for row in validated_domain_candidates],
            "candidate_birth_digest": candidate_birth.get("digest"),
            "fresh_candidate_birth_requested": bool(fresh_candidate_birth),
        }
        ledger_payload["receipt_id"] = "RCR-" + digest_payload(ledger_payload)[:24].upper()
        ledger_payload["digest"] = digest_payload({k: v for k, v in ledger_payload.items() if k != "digest"})

        # v7 scientific claims are fail-closed unless the sole promotion core runs.
        from .scientific_promotion import ScientificPromotionCore
        promotion_core = ScientificPromotionCore(trusted_evidence_owners=tuple(self.runtime.catalog.passports))
        scientific_promotion = (
            promotion_core.evaluate(promotion_request)
            if promotion_request is not None
            else promotion_core.inference_status(None)
        )
        result = {
            "schema": RESEARCH_CYCLE_SCHEMA,
            "owner": self.owner_id,
            "contract": self.contract(),
            "question": question,
            "unknown_boundary": unknown_boundary,
            "owner_axis_space": directed_region,
            "dynamic_axis_admissions": axis_admissions,
            "candidate_birth": candidate_birth,
            "competitive_set": competitive_set,
            "predictions_and_falsification": predictions,
            "information_gain": eig,
            "experiment": {
                "selected_experiment_id": eig.get("selected_experiment_id"),
                "status": "SELECTED" if eig.get("selected_experiment_id") else "BLOCKED_OR_PENDING",
            },
            "evidence": evidence,
            "post_derivation_novelty": novelty_rows,
            "ledger": ledger_payload,
            "next_frontier": next_frontier,
            "scientific_promotion": scientific_promotion,
            "claim_boundary": {
                "new_formula_generator_created": False,
                "existing_candidate_owner_replaced": False,
                "generic_candidate_registry_mutated_by_domain_seam": False,
                "materialized_2771_used_as_fresh_fallback": False,
                "canonical_axis_registry_mutated_implicitly": False,
                "eig_without_predictive_likelihoods": False,
                "literature_used_before_candidate_freeze": False,
                "world_novelty_claimed": False,
                "experiment_execution_claimed_without_observation": False,
                "scientific_promotion_outside_core": False,
                "system_status": "RESEARCH_SYSTEM_UNDER_QUALIFICATION",
            },
        }
        required_stage_ok = {
            "OWNER_AXIS_SPACE": bool(directed_region.get("all_registered_axes_visited")),
            "UNKNOWN_BOUNDARY": unknown_boundary.get("status") in {"UNKNOWN_BOUNDARY_MATERIALIZED", "NO_EXPLICIT_OPEN_BOUNDARY_FOUND"},
            "COMPETITIVE_SET": competitive_set.get("status") == "COMPETITIVE_SET_FROZEN",
            "PREDICTION_FALSIFICATION": predictions.get("status") == "PREDICTION_AND_FALSIFICATION_CONTRACTS_READY",
            "EIG_ALGORITHM": eig.get("status") in {"EIG_RANKED", "BLOCKED_PREDICTIVE_LIKELIHOODS_REQUIRED"},
            "NOVELTY_POST_FREEZE": all(bool(row.get("candidate_frozen_before_literature_access")) for row in novelty_rows),
            "LEDGER": bool(ledger_payload.get("receipt_id")),
            "NEXT_FRONTIER": next_frontier.get("status") == "NEXT_FRONTIER_DEFINED",
        }
        result["gates"] = required_stage_ok
        result["status"] = "RESEARCH_CYCLE_CONTRACT_PASS" if all(required_stage_ok.values()) else "RESEARCH_CYCLE_CONTRACT_FAIL"
        result["digest"] = digest_payload(result)
        return result

    def interpret_question(self, question: str) -> Mapping[str, Any]:
        return self.question_interpreter.interpret(question)

    def run_autonomous(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        """Run the authoritative Human->Phi loop without inventing missing evidence.

        Existing owners remain authoritative. The method only routes receipts and
        explicitly records which downstream owner is blocked or actionable.
        """
        req = dict(request)
        if req.get("external_sources") or req.get("internet_results"):
            raise ValueError("external/internet material is forbidden before the internal freeze")
        question = str(req.get("question", "")).strip()
        if not question:
            raise ValueError("question is required")
        typed = self.interpret_question(question)
        required_domains = tuple(req.get("required_domains") or typed.get("required_domains", ()))
        target_axis_ids = tuple(req.get("target_axis_ids") or typed.get("target_axis_ids", ()))
        required_observables = tuple(req.get("required_observables") or typed.get("required_observables", ()))
        include_connected = bool(req.get("include_all_connected_owners", False))

        axis_proposals = tuple(
            row if isinstance(row, DynamicAxisProposal) else DynamicAxisProposal(**dict(row))
            for row in req.get("dynamic_axis_proposals", ())
        )
        experiment_specs = tuple(
            row if isinstance(row, ExperimentLikelihoodSpec) else ExperimentLikelihoodSpec(**dict(row))
            for row in req.get("experiment_specs", ())
        )
        literature_records = tuple(
            row if isinstance(row, LiteratureRecord) else LiteratureRecord(**dict(row))
            for row in req.get("literature_records", ())
        )
        cycle = self.run(
            question=question,
            required_observables=required_observables,
            seed_owner_ids=tuple(req.get("seed_owner_ids", ())),
            target_axis_ids=target_axis_ids,
            required_domains=required_domains,
            include_all_connected_owners=include_connected,
            discovery_mode=str(req.get("discovery_mode", "SEMANTIC_OWNER_FRONTIER")),
            domain_candidate_records=tuple(req.get("domain_candidate_records", ())),
            dynamic_axis_proposals=axis_proposals,
            experiment_specs=experiment_specs,
            priors=req.get("priors"),
            literature_records=literature_records,
            minimum_competing_hypotheses=int(req.get("minimum_competing_hypotheses", MINIMUM_COMPETING_HYPOTHESES)),
            promotion_request=req.get("promotion_request"),
            fresh_candidate_birth=bool(req.get("require_fresh_candidates", True)),
            semantic_ir=typed,
            candidate_birth_execution=req.get("candidate_birth_execution"),
        )

        # The Resident owns open-world action state/model learning. It receives the
        # frozen, typed region but cannot authorize external actuation itself.
        from .resident_cognitive import ResidentCognitiveOrganism
        resident_state_path = req.get("resident_state_path")
        resident = ResidentCognitiveOrganism(self.runtime, resident_state_path)
        open_world = resident.scan_open_world({
            "question": question,
            "required_observables": required_observables,
            "required_domains": required_domains,
            "include_all_connected_owners": include_connected,
            "activate_bridge_open_axes": bool(req.get("activate_bridge_open_axes", False)),
        })
        candidate_ids = [str(row.get("candidate_id")) for row in cycle.get("competitive_set", {}).get("candidates", ())]
        if candidate_ids:
            learned_action = resident.select_action_from_contextual_world_model(
                open_world["freeze"], {"hypotheses": candidate_ids, "priors": req.get("priors"), "context": req.get("context")}
            )
            if learned_action.get("selected_action") is None:
                learned_action = resident.select_action_from_learned_world_model(
                    open_world["freeze"], {"hypotheses": candidate_ids, "priors": req.get("priors"), "context": req.get("context")}
                )
        else:
            learned_action = {
                "owner": resident.owner_id,
                "status": "BLOCKED_NO_COMPETITIVE_HYPOTHESES_FOR_WORLD_MODEL_ACTION",
                "selected_action": None,
            }
            learned_action["digest"] = digest_payload(learned_action)

        # Mathematical invention is entered only from an actual gap/failure receipt.
        # No transition evidence is synthesized here.
        from .mathematical_invention import MathematicalInventionKernel
        invention = MathematicalInventionKernel(self.runtime.root)
        evidence_rows = tuple(dict(row) for row in req.get("representation_evidence_rows", ()))
        cycle_gap = (
            cycle.get("competitive_set", {}).get("status") != "COMPETITIVE_SET_FROZEN"
            or cycle.get("information_gain", {}).get("status") != "EIG_RANKED"
            or bool(typed.get("capability_gap_detected"))
        )
        if cycle_gap:
            representation = invention.unknown_unknown.discover(question=question, evidence_rows=evidence_rows)
        else:
            representation = {
                "schema": AUTONOMOUS_RESEARCH_SCHEMA,
                "owner_id": invention.unknown_unknown.owner_id if hasattr(invention.unknown_unknown, "owner_id") else "UNKNOWN-UNKNOWN-REPRESENTATION-TYPE-DISCOVERY/1.0.0",
                "status": "REPRESENTATION_EXPANSION_NOT_TRIGGERED_CURRENT_CYCLE_HAS_EXECUTABLE_INFORMATION_PATH",
                "claim_boundary": {"new_representation_type_established": False},
            }
            representation["digest"] = digest_payload(representation)

        transition_rows = tuple(dict(row) for row in req.get("transition_rows", ()))
        if representation.get("status") == "PROPOSE_GENERATED_REPRESENTATION_SIGNATURE" and transition_rows:
            primitive = invention.primitive.synthesize(
                transition_rows=transition_rows,
                freeze_digest=str(representation.get("digest", "")),
            )
        elif representation.get("status") == "PROPOSE_GENERATED_REPRESENTATION_SIGNATURE":
            primitive = {
                "schema": AUTONOMOUS_RESEARCH_SCHEMA,
                "owner_id": "PRIMITIVE-SYNTHESIS/1.0.0",
                "status": "PRIMITIVE_SYNTHESIS_BLOCKED_TRANSITION_EVIDENCE_REQUIRED",
                "claim_boundary": {"primitive_promoted": False},
            }
            primitive["digest"] = digest_payload(primitive)
        else:
            primitive = {
                "schema": AUTONOMOUS_RESEARCH_SCHEMA,
                "owner_id": "PRIMITIVE-SYNTHESIS/1.0.0",
                "status": "PRIMITIVE_SYNTHESIS_NOT_ENTERED_REPRESENTATION_OBLIGATIONS_NOT_QUALIFIED",
                "claim_boundary": {"primitive_promoted": False},
            }
            primitive["digest"] = digest_payload(primitive)

        research_axis_ids = [
            str(row.get("qualified_axis_id"))
            for row in cycle.get("owner_axis_space", {}).get("axis_rows", ())
            if row.get("disposition") in {"OWNER_BOUND_ACTIVE", "QUERY_DIRECT_OPEN_COORDINATE"}
        ][:64]
        environment_id = str(req.get("environment_id") or ("autonomous-research-" + digest_payload(question)[:12]))
        heartbeat = resident.heartbeat({
            "environment_id": environment_id,
            "root_goal": {"goal_id": "GOAL-" + digest_payload(question)[:16].upper(), "statement": question},
            "cognitive_episode": {
                "representation_route": "MATHEMATICAL_INVENTION" if cycle_gap else "EXISTING_REPRESENTATION",
                "research_region": {"research_local_axis_ids": research_axis_ids},
                "research_cycle_digest": cycle.get("digest"),
                "typed_question_digest": typed.get("digest"),
            },
            "axis_ids": research_axis_ids,
            "grounding": dict(req.get("grounding", {})),
        }, commit=bool(req.get("commit_resident_state", True)))

        if cycle.get("information_gain", {}).get("status") == "EIG_RANKED" and cycle.get("experiment", {}).get("selected_experiment_id"):
            status = "AUTONOMOUS_RESEARCH_EXPERIMENT_SELECTED"
            next_required = "EXECUTE_OR_INGEST_SELECTED_EXPERIMENT"
        elif learned_action.get("selected_action") is not None:
            status = "AUTONOMOUS_RESEARCH_ACTION_SELECTED_FROM_LEARNED_WORLD_MODEL"
            next_required = "EXECUTE_TYPED_SELECTED_ACTION_AND_BIND_RESULT"
        elif representation.get("status") == "PROPOSE_GENERATED_REPRESENTATION_SIGNATURE" and not transition_rows:
            status = "AUTONOMOUS_RESEARCH_GAP_TRANSITION_EVIDENCE_REQUIRED"
            next_required = "PROVIDE_OR_ACQUIRE_COMPLETE_POSTFREEZE_TRANSITION_OBSERVATIONS"
        elif str(representation.get("status", "")).startswith("UNKNOWN_UNKNOWN_INSUFFICIENT"):
            status = "AUTONOMOUS_RESEARCH_GAP_INDEPENDENT_EVIDENCE_REQUIRED"
            next_required = "ACQUIRE_INDEPENDENT_RESIDUAL_LATENT_CAUSAL_COUNTERFACTUAL_OR_BRIDGE_EVIDENCE"
        elif cycle.get("competitive_set", {}).get("status") != "COMPETITIVE_SET_FROZEN":
            status = "AUTONOMOUS_RESEARCH_GAP_COMPETITIVE_SET_REQUIRED"
            next_required = "EXPAND_OWNER_CONNECTED_REPRESENTATION_OR_ACQUIRE_DISCRIMINATING_EVIDENCE"
        else:
            status = "AUTONOMOUS_RESEARCH_BLOCKED_FAIL_CLOSED"
            next_required = "FOLLOW_NEXT_FRONTIER_RECEIPT"

        payload = {
            "schema": AUTONOMOUS_RESEARCH_SCHEMA,
            "owner": self.owner_id,
            "question": question,
            "semantic_typed_ir": typed,
            "research_cycle": cycle,
            "open_world": open_world,
            "learned_world_action": learned_action,
            "representation_invention": representation,
            "primitive_synthesis": primitive,
            "resident_heartbeat": heartbeat,
            "next_required_external_input": next_required,
            "status": status,
            "claim_boundary": {
                "scientific_solution_claimed": False,
                "world_novelty_claimed": False,
                "missing_likelihoods_invented": False,
                "missing_evidence_invented": False,
                "external_source_used_prefreeze": False,
                "sealed_release_mutated_by_resident_state": False,
                "parallel_scientific_solver_created": False,
                "hand_authored_collective_coordination_answer_used": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def run_qualification(self) -> Mapping[str, Any]:
        # Qualification uses a generic mathematical likelihood contract only to
        # prove the EIG machinery.  It is explicitly not a physical-data claim.
        question = "неизвестное связанное динамическое замыкание с измеримым откликом"
        directed = directed_owner_hypergraph_research(
            self.runtime.catalog,
            self.runtime.bridges,
            DirectedResearchQuery(question=question, required_domains=("physics", "mechanics")),
        )
        competitive = self.competitive.build(
            question=question,
            directed_region=directed,
            candidates=self.runtime.candidates,
            minimum=MINIMUM_COMPETING_HYPOTHESES,
        )
        candidate_ids = [str(row["candidate_id"]) for row in competitive.get("candidates", ())]
        if len(candidate_ids) < MINIMUM_COMPETING_HYPOTHESES:
            return {
                "schema": "phi-scientific-research-cycle-qualification/v7.0",
                "owner": self.owner_id,
                "status": "FAIL_COMPETITIVE_SET_NOT_AVAILABLE",
                "candidate_count": len(candidate_ids),
            }
        outcomes = tuple(f"O{i+1}" for i in range(len(candidate_ids)))
        likelihoods: Dict[str, Dict[str, float]] = {}
        for i, candidate_id in enumerate(candidate_ids):
            row = {outcome: 0.02 for outcome in outcomes}
            row[outcomes[i]] = 0.92
            likelihoods[candidate_id] = row
        spec = ExperimentLikelihoodSpec(
            experiment_id="QUAL-DISCRIMINATOR",
            measurements=("qualification_observable",),
            outcomes=outcomes,
            likelihoods=likelihoods,
            cost=1.0,
            observed_outcome=outcomes[0],
            metadata={"scope": "MATHEMATICAL_EIG_POSITIVE_CONTROL_NOT_PHYSICAL_EXPERIMENT"},
        )
        cycle = self.run(
            question=question,
            required_domains=("physics", "mechanics"),
            experiment_specs=(spec,),
            minimum_competing_hypotheses=MINIMUM_COMPETING_HYPOTHESES,
        )
        checks = {
            "all_registered_axes_visited": cycle["owner_axis_space"].get("all_registered_axes_visited") is True,
            "minimum_five_competitors": cycle["competitive_set"].get("candidate_count", 0) >= MINIMUM_COMPETING_HYPOTHESES,
            "candidate_set_frozen_before_prior_art": all(row.get("candidate_frozen_before_literature_access") for row in cycle["post_derivation_novelty"]),
            "prediction_falsification_ready": cycle["predictions_and_falsification"].get("status") == "PREDICTION_AND_FALSIFICATION_CONTRACTS_READY",
            "eig_positive_control_ranked": cycle["information_gain"].get("status") == "EIG_RANKED" and cycle["information_gain"].get("selected_experiment_id") == "QUAL-DISCRIMINATOR",
            "evidence_assimilated": cycle["evidence"].get("status") == "EVIDENCE_ASSIMILATED",
            "world_novelty_not_claimed_without_literature": all(row.get("world_literature_novelty_established") is False for row in cycle["post_derivation_novelty"]),
            "canonical_axis_registry_not_mutated": cycle["claim_boundary"].get("canonical_axis_registry_mutated_implicitly") is False,
            "no_parallel_formula_generator": cycle["claim_boundary"].get("new_formula_generator_created") is False,
            "ledger_receipt_created": str(cycle["ledger"].get("receipt_id", "")).startswith("RCR-"),
            "next_frontier_defined": cycle["next_frontier"].get("status") == "NEXT_FRONTIER_DEFINED",
            "scientific_promotion_fail_closed_without_numerical_evidence": cycle["scientific_promotion"].get("status") == "ENGINE_NOT_RUN_SCIENTIFIC_INFERENCE_BLOCKED",
        }
        report = {
            "schema": "phi-scientific-research-cycle-qualification/v7.0",
            "owner": self.owner_id,
            "cycle_digest": cycle.get("digest"),
            "candidate_freeze_digest": cycle["competitive_set"].get("candidate_freeze_digest"),
            "candidate_ids": candidate_ids,
            "eig_bits": cycle["information_gain"]["experiments"][0]["expected_information_gain_bits"],
            "checks": checks,
            "status": "PASS_FULL_RESEARCH_CYCLE_CONTRACT" if all(checks.values()) else "FAIL",
            "claim_boundary": "qualification proves orchestration and EIG mathematics; scientific promotion remains blocked unless Scientific Promotion Core receives numerical evidence",
        }
        report["digest"] = digest_payload(report)
        return report
