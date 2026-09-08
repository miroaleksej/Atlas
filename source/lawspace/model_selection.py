"""Authoritative multi-horizon physical model-selection owner.

The owner ranks already fitted scientific model candidates.  It does not fit
models, read a blind holdout, infer a physical law, or repair an unphysical
channel.  Its purpose is narrower and fail-closed:

* aggregate rolling-origin prediction errors over several future horizons;
* reject candidates that violate the declared physicality or pole-stability
  contracts;
* penalise practical non-identifiability and nearly degenerate pseudomodes;
* include a weighted discrete-memory consistency term;
* expose every score component and every rejected gate in a digest-bound
  certificate.

All numerical weights are declared in ``PhysicalSelectionConfig`` and are
therefore part of the reproducible owner contract rather than hidden in a CLI
or experiment script.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

OWNER_ID = "PHYSICAL-MODEL-SELECTOR"
OWNER_VERSION = "4.6.0"
SCHEMA = "phi-multi-horizon-physical-model-selection/v4.6"


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=float)


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class HorizonEvidence:
    """Prediction evidence produced without reading the blind holdout."""

    horizon_id: str
    origin_step: int
    end_step: int
    prediction_steps: int
    rmse: float
    weight: float = 1.0

    def validate(self) -> None:
        if not self.horizon_id:
            raise ValueError("horizon_id must be non-empty")
        if self.origin_step < 0 or self.end_step <= self.origin_step:
            raise ValueError("horizon bounds are invalid")
        if self.prediction_steps != self.end_step - self.origin_step:
            raise ValueError("prediction_steps must equal end_step-origin_step")
        if not math.isfinite(self.rmse) or self.rmse < 0.0:
            raise ValueError("horizon RMSE must be finite and non-negative")
        if not math.isfinite(self.weight) or self.weight <= 0.0:
            raise ValueError("horizon weight must be finite and positive")


@dataclass(frozen=True)
class PseudomodeDescriptor:
    coupling: float
    decay_rate: float
    frequency: float

    def validate(self) -> None:
        if not all(math.isfinite(v) for v in (self.coupling, self.decay_rate, self.frequency)):
            raise ValueError("pseudomode parameters must be finite")
        if self.coupling < 0.0 or self.decay_rate <= 0.0:
            raise ValueError("pseudomode coupling must be non-negative and decay positive")


@dataclass(frozen=True)
class CandidateSelectionEvidence:
    candidate_id: str
    parameter_count: int
    effective_sample_count: int
    horizons: tuple[HorizonEvidence, ...]
    physicality_passed: bool
    physicality_status: str
    cptp_violation_count: int = 0
    minimum_choi_eigenvalue: float | None = None
    pole_stability_passed: bool = True
    pole_stability_margin: float = math.inf
    pole_status: str = "STABLE_BY_CONSTRUCTION"
    identifiability_rank: int = 0
    identifiability_dimension: int = 0
    identifiability_condition_number: float = 1.0
    profile_open_parameter_count: int = 0
    weighted_discrete_memory_error: float = 0.0
    pseudomodes: tuple[PseudomodeDescriptor, ...] = field(default_factory=tuple)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self, minimum_horizons: int) -> None:
        if not self.candidate_id:
            raise ValueError("candidate_id must be non-empty")
        if self.parameter_count < 0:
            raise ValueError("parameter_count must be non-negative")
        if self.effective_sample_count <= 0:
            raise ValueError("effective_sample_count must be positive")
        if len(self.horizons) < minimum_horizons:
            raise ValueError(f"at least {minimum_horizons} horizons are required")
        ids = [h.horizon_id for h in self.horizons]
        if len(ids) != len(set(ids)):
            raise ValueError("horizon identifiers must be unique")
        for horizon in self.horizons:
            horizon.validate()
        if self.cptp_violation_count < 0:
            raise ValueError("cptp_violation_count must be non-negative")
        if self.minimum_choi_eigenvalue is not None and not math.isfinite(self.minimum_choi_eigenvalue):
            raise ValueError("minimum_choi_eigenvalue must be finite when supplied")
        if not math.isfinite(self.pole_stability_margin):
            if self.pole_stability_margin != math.inf:
                raise ValueError("pole_stability_margin must be finite or +inf")
        if self.identifiability_rank < 0 or self.identifiability_dimension < 0:
            raise ValueError("identifiability dimensions must be non-negative")
        if self.identifiability_rank > self.identifiability_dimension:
            raise ValueError("identifiability_rank cannot exceed dimension")
        if self.profile_open_parameter_count < 0:
            raise ValueError("profile_open_parameter_count must be non-negative")
        if not math.isfinite(self.identifiability_condition_number) or self.identifiability_condition_number < 1.0:
            raise ValueError("identifiability condition number must be finite and >=1")
        if not math.isfinite(self.weighted_discrete_memory_error) or self.weighted_discrete_memory_error < 0.0:
            raise ValueError("weighted discrete-memory error must be finite and non-negative")
        for mode in self.pseudomodes:
            mode.validate()


@dataclass(frozen=True)
class PhysicalSelectionConfig:
    minimum_horizons: int = 3
    cptp_eigenvalue_tolerance: float = 1.0e-8
    pole_margin_tolerance: float = -1.0e-8
    condition_reference: float = 100.0
    degeneracy_scale: float = 0.12
    loss_weight: float = 1.0
    worst_horizon_weight: float = 0.30
    horizon_instability_weight: float = 0.12
    complexity_weight: float = 0.10
    identifiability_weight: float = 0.18
    degeneracy_weight: float = 0.12
    memory_consistency_weight: float = 0.18

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class CandidateSelectionResult:
    candidate_id: str
    eligible: bool
    gate_checks: Mapping[str, bool]
    score: float | None
    components: Mapping[str, float]
    diagnostics: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class PhysicalSelectionCertificate:
    selected_candidate_id: str | None
    status: str
    config: Mapping[str, Any]
    results: tuple[CandidateSelectionResult, ...]
    holdout_accessed: bool
    digest: str

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def pseudomode_degeneracy_index(
    modes: Sequence[PseudomodeDescriptor], *, scale: float = 0.12
) -> tuple[float, int, float]:
    """Return smooth degeneracy penalty, close-pair count and minimum distance.

    Distances are dimensionless.  Frequency and decay separations are scaled
    by their local magnitudes; the contribution is weighted by the smaller
    coupling relative to the larger one so a numerically negligible mode does
    not dominate the penalty.
    """

    if len(modes) < 2:
        return 0.0, 0, math.inf
    penalties: list[float] = []
    distances: list[float] = []
    close_pairs = 0
    eps = 1.0e-15
    for i, left in enumerate(modes):
        for right in modes[i + 1 :]:
            decay_distance = abs(left.decay_rate - right.decay_rate) / (
                left.decay_rate + right.decay_rate + eps
            )
            frequency_distance = abs(left.frequency - right.frequency) / (
                1.0 + abs(left.frequency) + abs(right.frequency)
            )
            distance = math.hypot(decay_distance, frequency_distance)
            coupling_weight = min(left.coupling, right.coupling) / (
                max(left.coupling, right.coupling) + eps
            )
            penalties.append(coupling_weight * math.exp(-((distance / scale) ** 2)))
            distances.append(distance)
            if distance < scale:
                close_pairs += 1
    return float(sum(penalties)), close_pairs, float(min(distances))


def _raw_components(
    evidence: CandidateSelectionEvidence, config: PhysicalSelectionConfig
) -> tuple[dict[str, float], dict[str, Any]]:
    ordered = sorted(evidence.horizons, key=lambda h: (h.end_step, h.origin_step, h.horizon_id))
    weights = np.asarray([h.weight for h in ordered], dtype=float)
    errors = np.asarray([h.rmse for h in ordered], dtype=float)
    weights = weights / np.sum(weights)
    weighted_loss = float(math.sqrt(float(np.sum(weights * errors * errors))))
    worst_loss = float(np.max(errors))

    # A candidate whose error stops decreasing as more observations become
    # available is less reliable for extrapolation.  Only adverse increments
    # are penalised; genuine improvement is not rewarded twice.
    adjacent_growth = np.maximum(np.diff(errors), 0.0)
    horizon_instability = float(np.sum(adjacent_growth) / max(worst_loss, 1.0e-15))

    complexity = float(evidence.parameter_count / max(evidence.effective_sample_count, 1))
    if evidence.identifiability_dimension:
        rank_deficit = 1.0 - evidence.identifiability_rank / evidence.identifiability_dimension
        profile_fraction = evidence.profile_open_parameter_count / evidence.identifiability_dimension
    else:
        rank_deficit = 1.0
        profile_fraction = 1.0
    condition_penalty = max(
        0.0,
        math.log10(max(evidence.identifiability_condition_number / config.condition_reference, 1.0)),
    )
    identifiability = float(rank_deficit + profile_fraction + condition_penalty)
    degeneracy, close_pairs, minimum_mode_distance = pseudomode_degeneracy_index(
        evidence.pseudomodes, scale=config.degeneracy_scale
    )
    components = {
        "multi_horizon_loss": weighted_loss,
        "worst_horizon_loss": worst_loss,
        "horizon_instability": horizon_instability,
        "complexity_ratio": complexity,
        "identifiability_penalty": identifiability,
        "pseudomode_degeneracy": degeneracy,
        "weighted_discrete_memory_error": evidence.weighted_discrete_memory_error,
    }
    diagnostics = {
        "horizon_errors": {h.horizon_id: h.rmse for h in ordered},
        "horizon_bounds": {
            h.horizon_id: {"origin_step": h.origin_step, "end_step": h.end_step}
            for h in ordered
        },
        "rank_fraction": (
            evidence.identifiability_rank / evidence.identifiability_dimension
            if evidence.identifiability_dimension
            else 0.0
        ),
        "condition_number": evidence.identifiability_condition_number,
        "profile_open_parameter_count": evidence.profile_open_parameter_count,
        "close_pseudomode_pair_count": close_pairs,
        "minimum_pseudomode_distance": minimum_mode_distance,
        "physicality_status": evidence.physicality_status,
        "pole_status": evidence.pole_status,
        "metadata": dict(evidence.metadata),
    }
    return components, diagnostics


def _normalisation_scale(values: Sequence[float]) -> float:
    positive = sorted(v for v in values if math.isfinite(v) and v > 1.0e-15)
    if not positive:
        return 1.0
    return max(float(np.median(np.asarray(positive, dtype=float))), 1.0e-12)


class MultiHorizonPhysicalModelSelector:
    """Single authoritative owner for physical model selection."""

    def __init__(self, config: PhysicalSelectionConfig | None = None) -> None:
        self.config = config or PhysicalSelectionConfig()

    def select(
        self,
        candidates: Sequence[CandidateSelectionEvidence],
        *,
        holdout_accessed: bool = False,
    ) -> PhysicalSelectionCertificate:
        if holdout_accessed:
            raise PermissionError("blind holdout must not be accessed by the selector")
        if not candidates:
            raise ValueError("at least one candidate is required")
        ids = [candidate.candidate_id for candidate in candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate identifiers must be unique")
        for candidate in candidates:
            candidate.validate(self.config.minimum_horizons)

        raw: dict[str, tuple[dict[str, float], dict[str, Any], dict[str, bool]]] = {}
        for candidate in candidates:
            components, diagnostics = _raw_components(candidate, self.config)
            choi_pass = (
                candidate.minimum_choi_eigenvalue is None
                or candidate.minimum_choi_eigenvalue >= -self.config.cptp_eigenvalue_tolerance
            )
            checks = {
                "multi_horizon_evidence": len(candidate.horizons) >= self.config.minimum_horizons,
                "physicality_contract": bool(candidate.physicality_passed),
                "no_cptp_violations": candidate.cptp_violation_count == 0,
                "choi_lower_bound": choi_pass,
                "pole_stability": bool(candidate.pole_stability_passed)
                and candidate.pole_stability_margin >= self.config.pole_margin_tolerance,
                "finite_score_inputs": all(math.isfinite(v) for v in components.values()),
            }
            raw[candidate.candidate_id] = (components, diagnostics, checks)

        eligible_ids = [cid for cid, (_, _, checks) in raw.items() if all(checks.values())]
        if not eligible_ids:
            results = tuple(
                CandidateSelectionResult(
                    candidate_id=candidate.candidate_id,
                    eligible=False,
                    gate_checks=raw[candidate.candidate_id][2],
                    score=None,
                    components=raw[candidate.candidate_id][0],
                    diagnostics=raw[candidate.candidate_id][1],
                )
                for candidate in candidates
            )
            payload = {
                "owner_id": OWNER_ID,
                "owner_version": OWNER_VERSION,
                "schema": SCHEMA,
                "selected_candidate_id": None,
                "status": "BLOCKED_NO_PHYSICALLY_ELIGIBLE_CANDIDATE",
                "config": self.config.as_dict(),
                "results": [result.to_dict() for result in results],
                "holdout_accessed": False,
                "digest": "",
            }
            digest = _digest(payload)
            return PhysicalSelectionCertificate(
                None,
                payload["status"],
                payload["config"],
                results,
                False,
                digest,
            )

        component_names = tuple(next(iter(raw.values()))[0])
        scales = {
            name: _normalisation_scale([raw[cid][0][name] for cid in eligible_ids])
            for name in component_names
        }
        weights = {
            "multi_horizon_loss": self.config.loss_weight,
            "worst_horizon_loss": self.config.worst_horizon_weight,
            "horizon_instability": self.config.horizon_instability_weight,
            "complexity_ratio": self.config.complexity_weight,
            "identifiability_penalty": self.config.identifiability_weight,
            "pseudomode_degeneracy": self.config.degeneracy_weight,
            "weighted_discrete_memory_error": self.config.memory_consistency_weight,
        }

        results_list: list[CandidateSelectionResult] = []
        for candidate in candidates:
            components, diagnostics, checks = raw[candidate.candidate_id]
            eligible = all(checks.values())
            score = None
            if eligible:
                normalised = {name: components[name] / scales[name] for name in component_names}
                score = float(sum(weights[name] * normalised[name] for name in component_names))
                diagnostics = {
                    **diagnostics,
                    "normalisation_scales": scales,
                    "normalised_components": normalised,
                    "component_weights": weights,
                }
            results_list.append(
                CandidateSelectionResult(
                    candidate_id=candidate.candidate_id,
                    eligible=eligible,
                    gate_checks=checks,
                    score=score,
                    components=components,
                    diagnostics=diagnostics,
                )
            )

        results_list.sort(
            key=lambda result: (
                not result.eligible,
                math.inf if result.score is None else result.score,
                result.candidate_id,
            )
        )
        selected = next(result.candidate_id for result in results_list if result.eligible)
        payload = {
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "schema": SCHEMA,
            "selected_candidate_id": selected,
            "status": "PASS_MULTI_HORIZON_PHYSICAL_SELECTION",
            "config": self.config.as_dict(),
            "results": [result.to_dict() for result in results_list],
            "holdout_accessed": False,
            "digest": "",
        }
        digest = _digest(payload)
        return PhysicalSelectionCertificate(
            selected,
            payload["status"],
            payload["config"],
            tuple(results_list),
            False,
            digest,
        )


def select_physical_model(
    candidates: Sequence[CandidateSelectionEvidence],
    *,
    config: PhysicalSelectionConfig | None = None,
    holdout_accessed: bool = False,
) -> PhysicalSelectionCertificate:
    """Thin functional entrypoint; all logic remains in the owner class."""

    return MultiHorizonPhysicalModelSelector(config).select(
        candidates, holdout_accessed=holdout_accessed
    )
