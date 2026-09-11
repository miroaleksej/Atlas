"""Atlas-native collective epistemic coordination and architecture search.

The owner does not import or encode named external AI architectures.  It derives
an executable coordination search space from mechanisms already present in the
resident organism: information gain, calibration, finite-resource policy,
conflict/controllability constraints and cross-domain structure.

Architecture selection is performed on deterministic internal search worlds and
reported again on a disjoint holdout tranche.  Holdout results never participate
in candidate ranking.
"""
from __future__ import annotations

import itertools
import math
import random
import copy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .schema import digest_payload

SYSTEM_RELEASE = "0.15.29.0"
AI_ACCEPTANCE_VERSION = "15.10.6"
OWNER_ID = "COLLECTIVE-COORDINATION/1.0.0"
SEARCH_OWNER_ID = "COLLECTIVE-COORDINATION-ARCHITECTURE-SEARCH/1.0.0"
SCHEMA = "phi-collective-coordination/v1"
_SEARCH_CACHE: dict[tuple[int, int], Mapping[str, Any]] = {}

FUSION_MODES = ("NONE", "MEAN", "CALIBRATED_MEAN")
RESOURCE_MODES = ("NONE", "SOFT_PENALTY", "HARD_FEASIBILITY")


@dataclass(frozen=True)
class CoordinationArchitecture:
    action_fusion: str
    resource_mode: str
    joint_subset_selection: bool
    calibration_weighted_information: bool
    hard_conflict_exclusion: bool
    evidence_complementarity: bool
    domain_complementarity: bool
    soft_risk_penalty: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "action_fusion": self.action_fusion,
            "resource_mode": self.resource_mode,
            "joint_subset_selection": self.joint_subset_selection,
            "calibration_weighted_information": self.calibration_weighted_information,
            "hard_conflict_exclusion": self.hard_conflict_exclusion,
            "evidence_complementarity": self.evidence_complementarity,
            "domain_complementarity": self.domain_complementarity,
            "soft_risk_penalty": self.soft_risk_penalty,
        }

    @property
    def candidate_id(self) -> str:
        return "CCA-" + digest_payload(self.as_dict())[:20].upper()


def enumerate_architectures() -> tuple[CoordinationArchitecture, ...]:
    """Return the complete finite architecture tranche used by this release.

    This is a tranche, not a ceiling on future architecture space.  The eight
    coordinates are mechanisms already grounded in Atlas owners; no named
    external architecture is present.
    """
    rows = []
    for values in itertools.product(
        FUSION_MODES,
        RESOURCE_MODES,
        (False, True),  # joint subset search
        (False, True),  # calibration
        (False, True),  # hard conflict
        (False, True),  # evidence complementarity
        (False, True),  # domain complementarity
        (False, True),  # soft risk
    ):
        rows.append(CoordinationArchitecture(*values))
    return tuple(rows)


def _world(seed: int, *, holdout: bool) -> Mapping[str, Any]:
    rng = random.Random((100_003 if holdout else 17_003) + int(seed) * 7_919)
    regimes = ("BALANCED", "CORE_DROPOUT", "CONSENSUS_TRAP", "RESOURCE_SCARCE", "CONFLICT_DENSE", "CROSS_DOMAIN")
    regime = regimes[seed % len(regimes)]
    domains = ("structure", "dynamics", "evidence")
    evidence_classes = ("analytic", "simulation", "measurement")
    core_ids = ["core_a", "core_b", "core_c", "core_d"]
    if regime == "CORE_DROPOUT":
        core_ids.pop(seed % len(core_ids))

    proposals: list[dict[str, Any]] = []
    action_count = 4
    for action_i in range(action_count):
        # Two independent cores can propose the same action.  Their calibration
        # and information estimates differ; premature fusion can therefore lose
        # useful provenance.
        chosen_cores = (core_ids[action_i % len(core_ids)], core_ids[(action_i + 1) % len(core_ids)])
        for j, core in enumerate(chosen_cores):
            domain = domains[(action_i + j + seed) % len(domains)]
            evidence = evidence_classes[(2 * action_i + j + seed) % len(evidence_classes)]
            base_truth = 0.55 + 1.25 * rng.random()
            reliability = 0.48 + 0.50 * rng.random()
            if regime == "CONSENSUS_TRAP" and action_i == (seed % action_count):
                # Popular-looking action with systematically inflated raw estimate.
                reliability *= 0.58
                base_truth *= 0.78
            estimated = base_truth / max(reliability, 0.18) + rng.uniform(-0.08, 0.08)
            realized = max(0.03, base_truth + rng.uniform(-0.06, 0.06))
            cost = 0.45 + 1.15 * rng.random()
            if regime == "RESOURCE_SCARCE":
                cost *= 1.18
            risk = 0.05 + 0.35 * rng.random()
            conflict_group = None
            if regime == "CONFLICT_DENSE" or action_i in (1, 2):
                conflict_group = f"cg-{(action_i + seed) % 2}"
            proposals.append({
                "proposal_id": f"w{seed}-a{action_i}-{core}",
                "action_id": f"action_{action_i}",
                "core_id": core,
                "domain": domain,
                "evidence_class": evidence,
                "estimated_information": estimated,
                "calibration": reliability,
                "realized_information": realized,
                "cost": cost,
                "risk": risk,
                "conflict_group": conflict_group,
            })

    budget = 3.1 + 0.55 * rng.random()
    if regime == "RESOURCE_SCARCE":
        budget *= 0.68
    domain_synergy = 0.17 if regime != "CROSS_DOMAIN" else 0.31
    return {
        "world_id": f"{'H' if holdout else 'S'}-{seed:03d}",
        "regime": regime,
        "budget": budget,
        "domain_synergy": domain_synergy,
        "proposals": proposals,
        "sealed_holdout": bool(holdout),
    }


def _fuse(proposals: Sequence[Mapping[str, Any]], mode: str) -> list[dict[str, Any]]:
    if mode == "NONE":
        return [dict(x) for x in proposals]
    groups: dict[str, list[Mapping[str, Any]]] = {}
    for row in proposals:
        groups.setdefault(str(row["action_id"]), []).append(row)
    out: list[dict[str, Any]] = []
    for action_id, rows in sorted(groups.items()):
        if mode == "CALIBRATED_MEAN":
            weights = [max(float(r["calibration"]), 1e-9) for r in rows]
        else:
            weights = [1.0] * len(rows)
        total = sum(weights)
        avg = lambda key: sum(w * float(r[key]) for w, r in zip(weights, rows)) / total
        # Discrete provenance is intentionally collapsed here; that is the
        # information loss the search is allowed to measure rather than assume.
        exemplar = max(rows, key=lambda r: float(r["calibration"]))
        out.append({
            "proposal_id": f"fused-{action_id}",
            "action_id": action_id,
            "core_id": "FUSED",
            "domain": exemplar["domain"],
            "evidence_class": exemplar["evidence_class"],
            "estimated_information": avg("estimated_information"),
            "calibration": avg("calibration"),
            "realized_information": avg("realized_information"),
            "cost": avg("cost"),
            "risk": avg("risk"),
            "conflict_group": exemplar.get("conflict_group"),
        })
    return out


def _conflict_free(subset: Sequence[Mapping[str, Any]]) -> bool:
    # Same action from independent cores is not a conflict.  A conflict group is
    # invalid only when it contains distinct actions.
    groups: dict[str, set[str]] = {}
    for row in subset:
        group = row.get("conflict_group")
        if group:
            groups.setdefault(str(group), set()).add(str(row["action_id"]))
    return all(len(actions) <= 1 for actions in groups.values())


def _resource_feasible(subset: Sequence[Mapping[str, Any]], budget: float) -> bool:
    return sum(float(x["cost"]) for x in subset) <= float(budget) + 1e-12


def _actual_utility(subset: Sequence[Mapping[str, Any]], world: Mapping[str, Any]) -> float:
    if not subset:
        return 0.0
    base = sum(float(x["realized_information"]) for x in subset)
    unique_domains = len({str(x["domain"]) for x in subset})
    synergy = float(world["domain_synergy"]) * max(unique_domains - 1, 0) * (base / len(subset))
    return base + synergy


def _predicted_utility(subset: Sequence[Mapping[str, Any]], world: Mapping[str, Any], arch: CoordinationArchitecture) -> float:
    if not subset:
        return 0.0
    infos = []
    for row in subset:
        value = float(row["estimated_information"])
        if arch.calibration_weighted_information:
            value *= float(row["calibration"])
        infos.append(value)
    base = sum(infos)
    scale = base / max(len(subset), 1)
    if arch.domain_complementarity:
        base += 0.18 * max(len({str(x["domain"]) for x in subset}) - 1, 0) * scale
    if arch.evidence_complementarity:
        base += 0.13 * max(len({str(x["evidence_class"]) for x in subset}) - 1, 0) * scale
    if arch.soft_risk_penalty:
        base -= 0.30 * sum(float(x["risk"]) for x in subset)
    if arch.resource_mode == "SOFT_PENALTY":
        over = max(0.0, sum(float(x["cost"]) for x in subset) - float(world["budget"]))
        base -= 1.35 * over
    return base


def _subset_allowed(subset: Sequence[Mapping[str, Any]], world: Mapping[str, Any], arch: CoordinationArchitecture) -> bool:
    if arch.resource_mode == "HARD_FEASIBILITY" and not _resource_feasible(subset, float(world["budget"])):
        return False
    if arch.hard_conflict_exclusion and not _conflict_free(subset):
        return False
    return True


def _choose_plan(world: Mapping[str, Any], arch: CoordinationArchitecture) -> tuple[list[dict[str, Any]], bool]:
    rows = _fuse(world["proposals"], arch.action_fusion)
    if arch.joint_subset_selection:
        best: list[dict[str, Any]] = []
        best_key = (-math.inf, -math.inf, "")
        for mask in range(1, 1 << len(rows)):
            subset = [rows[i] for i in range(len(rows)) if mask & (1 << i)]
            if not _subset_allowed(subset, world, arch):
                continue
            predicted = _predicted_utility(subset, world, arch)
            # Deterministic tie-break: lower cost, then content identity.
            cost = sum(float(x["cost"]) for x in subset)
            identity = digest_payload([str(x["proposal_id"]) for x in subset])
            key = (predicted, -cost, identity)
            if key > best_key:
                best_key = key
                best = subset
    else:
        ranked = sorted(rows, key=lambda x: (_predicted_utility([x], world, arch), -float(x["cost"]), str(x["proposal_id"])), reverse=True)
        best = []
        for row in ranked:
            trial = best + [row]
            if _subset_allowed(trial, world, arch) and _predicted_utility(trial, world, arch) >= _predicted_utility(best, world, arch):
                best = trial
            # Greedy architecture cannot revise earlier choices.
            if len(best) >= 3:
                break
    invalid = (not _resource_feasible(best, float(world["budget"]))) or (not _conflict_free(best))
    return best, invalid


def _oracle(world: Mapping[str, Any]) -> tuple[float, tuple[str, ...]]:
    rows = [dict(x) for x in world["proposals"]]
    best_value = 0.0
    best_ids: tuple[str, ...] = tuple()
    for mask in range(1, 1 << len(rows)):
        subset = [rows[i] for i in range(len(rows)) if mask & (1 << i)]
        if not _resource_feasible(subset, float(world["budget"])) or not _conflict_free(subset):
            continue
        value = _actual_utility(subset, world)
        ids = tuple(sorted(str(x["proposal_id"]) for x in subset))
        if value > best_value + 1e-12 or (abs(value - best_value) <= 1e-12 and ids < best_ids):
            best_value, best_ids = value, ids
    return best_value, best_ids


def evaluate_architecture(arch: CoordinationArchitecture, worlds: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    ratios: list[float] = []
    invalid_count = 0
    by_regime: dict[str, list[float]] = {}
    for world in worlds:
        oracle_value, _ = _oracle(world)
        plan, invalid = _choose_plan(world, arch)
        invalid_count += int(invalid)
        value = 0.0 if invalid else _actual_utility(plan, world)
        ratio = 0.0 if oracle_value <= 0 else max(0.0, min(value / oracle_value, 1.0))
        ratios.append(ratio)
        by_regime.setdefault(str(world["regime"]), []).append(ratio)
    sr = sorted(ratios)
    q25 = sr[max(0, math.ceil(0.25 * len(sr)) - 1)] if sr else 0.0
    return {
        "candidate_id": arch.candidate_id,
        "architecture": arch.as_dict(),
        "world_count": len(worlds),
        "mean_oracle_ratio": sum(ratios) / max(len(ratios), 1),
        "q25_oracle_ratio": q25,
        "minimum_oracle_ratio": min(ratios) if ratios else 0.0,
        "invalid_plan_count": invalid_count,
        "invalid_plan_fraction": invalid_count / max(len(worlds), 1),
        "regime_mean_ratios": {k: sum(v) / len(v) for k, v in sorted(by_regime.items())},
    }


class CollectiveCoordinationArchitectureSearchOwner:
    owner_id = SEARCH_OWNER_ID

    def search(self, *, search_world_count: int = 36, holdout_world_count: int = 48) -> Mapping[str, Any]:
        cache_key = (int(search_world_count), int(holdout_world_count))
        if cache_key in _SEARCH_CACHE:
            return copy.deepcopy(_SEARCH_CACHE[cache_key])
        search_worlds = [_world(i, holdout=False) for i in range(search_world_count)]
        holdout_worlds = [_world(i, holdout=True) for i in range(holdout_world_count)]
        candidates = enumerate_architectures()
        search_rows = [evaluate_architecture(a, search_worlds) for a in candidates]
        # Invalid plans are fail-closed before utility ranking.  Remaining score
        # orders mean, lower quartile and minimum robustness, then simpler ID.
        ranked = sorted(
            search_rows,
            key=lambda r: (
                -int(r["invalid_plan_count"] == 0),
                -float(r["mean_oracle_ratio"]),
                -float(r["q25_oracle_ratio"]),
                -float(r["minimum_oracle_ratio"]),
                str(r["candidate_id"]),
            ),
        )
        # Above sorting is ascending on negative metrics, so first is best.
        selected_search = ranked[0]
        arch_map = {a.candidate_id: a for a in candidates}
        selected_arch = arch_map[str(selected_search["candidate_id"])]
        holdout = evaluate_architecture(selected_arch, holdout_worlds)

        # Best holdout baseline among architectures that omit at least one active
        # mechanism from the selected candidate.  It is diagnostic only and never
        # participates in selection.
        selected = selected_arch.as_dict()
        holdout_rows = [evaluate_architecture(a, holdout_worlds) for a in candidates]
        competitors = [r for r in holdout_rows if r["candidate_id"] != selected_arch.candidate_id and r["invalid_plan_count"] == 0]
        competitors.sort(key=lambda r: (float(r["mean_oracle_ratio"]), float(r["q25_oracle_ratio"]), float(r["minimum_oracle_ratio"])), reverse=True)
        best_competitor = competitors[0] if competitors else None

        payload = {
            "schema": "phi-collective-coordination-architecture-search/v1",
            "owner_id": self.owner_id,
            "system_release": SYSTEM_RELEASE,
            "ai_acceptance_version": AI_ACCEPTANCE_VERSION,
            "search_space": {
                "axes": {
                    "action_fusion": list(FUSION_MODES),
                    "resource_mode": list(RESOURCE_MODES),
                    "joint_subset_selection": [False, True],
                    "calibration_weighted_information": [False, True],
                    "hard_conflict_exclusion": [False, True],
                    "evidence_complementarity": [False, True],
                    "domain_complementarity": [False, True],
                    "soft_risk_penalty": [False, True],
                },
                "candidate_count": len(candidates),
                "fixed_future_architecture_ceiling": None,
                "named_external_architectures_used": False,
                "internet_used_for_selection": False,
            },
            "selection": {
                "search_world_count": len(search_worlds),
                "search_world_digest": digest_payload(search_worlds),
                "selected_candidate": selected_search,
                "frontier": ranked[:12],
            },
            "holdout": {
                "holdout_world_count": len(holdout_worlds),
                "holdout_world_digest": digest_payload(holdout_worlds),
                "selected_candidate_result": holdout,
                "best_internal_competitor": best_competitor,
                "holdout_used_for_selection": False,
            },
            "selected_architecture": selected,
            "claim_boundary": {
                "selected_architecture_is_world_optimal": False,
                "selected_architecture_beats_external_ai_systems": False,
                "synthetic_internal_holdout_is_external_validation": False,
                "AGI_demonstrated": False,
            },
        }
        payload["freeze_digest"] = digest_payload(payload)
        _SEARCH_CACHE[cache_key] = copy.deepcopy(payload)
        return payload


class CollectiveCoordinationOwner:
    owner_id = OWNER_ID

    def __init__(self) -> None:
        self.search_owner = CollectiveCoordinationArchitectureSearchOwner()

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner_id": self.owner_id,
            "system_release": SYSTEM_RELEASE,
            "ai_acceptance_version": AI_ACCEPTANCE_VERSION,
            "pipeline": [
                "PRESERVE_INDEPENDENT_EPISTEMIC_CORES",
                "GENERATE_TYPED_ACTION_PROPOSALS",
                "CALIBRATE_INFORMATION_VALUE",
                "ENFORCE_HARD_RESOURCE_AND_CONFLICT_FEASIBILITY",
                "JOINT_SUBSET_SEARCH",
                "EXECUTE_ONLY_SELECTED_TYPED_ACTIONS",
            ],
            "delegation": {
                "information_value": "CONTEXTUAL-NONSTATIONARY-WORLD-ACTION-MODEL/2.0.0",
                "finite_resources": "FINITE-RESOURCE-ACTION-POLICY/1.0.0",
                "typed_execution": "TYPED-WORLD-ACTION-ADAPTER/1.0.0",
            },
            "hard_boundaries": {
                "belief_states_are_averaged": False,
                "consensus_required": False,
                "resource_violation_allowed": False,
                "conflicting_joint_actions_allowed": False,
                "internet_can_select_architecture": False,
            },
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def search_architecture(self) -> Mapping[str, Any]:
        return self.search_owner.search()

    def coordinate(self, *, proposals: Sequence[Mapping[str, Any]], budget: float, architecture: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        if not proposals:
            raise ValueError("collective coordination requires at least one proposal")
        if budget <= 0:
            raise ValueError("collective coordination budget must be positive")
        if architecture is None:
            architecture = self.search_architecture()["selected_architecture"]
        arch = CoordinationArchitecture(**dict(architecture))
        world = {
            "world_id": "RUNTIME",
            "regime": "RUNTIME",
            "budget": float(budget),
            "domain_synergy": 0.0,
            "proposals": [dict(x) for x in proposals],
            "sealed_holdout": False,
        }
        plan, invalid = _choose_plan(world, arch)
        if invalid:
            raise RuntimeError("collective coordination produced invalid plan")
        payload = {
            "schema": "phi-collective-coordination-execution/v1",
            "owner_id": self.owner_id,
            "status": "COLLECTIVE_PLAN_SELECTED",
            "architecture": arch.as_dict(),
            "selected_proposal_ids": [str(x["proposal_id"]) for x in plan],
            "selected_action_ids": [str(x["action_id"]) for x in plan],
            "selected_core_ids": [str(x["core_id"]) for x in plan],
            "budget": float(budget),
            "resource_used": sum(float(x["cost"]) for x in plan),
            "conflict_free": _conflict_free(plan),
            "independent_belief_states_preserved": arch.action_fusion == "NONE",
            "claim_boundary": {"plan_is_world_truth": False, "architecture_is_external_best": False},
        }
        payload["digest"] = digest_payload(payload)
        return payload
