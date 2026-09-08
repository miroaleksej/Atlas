"""Φ-Resource Theory Discovery.

This owner discovers a scalar intrinsic resource law from frozen execution
measurements without allowing named resource measures (entanglement, magic,
treewidth, rank, ...) to act as pre-freeze answers.  Known measures may be
compared only after the internally synthesized resource expression is frozen.

Qualification demonstrates a mechanism on synthetic workloads; it does not
claim discovery of a world-level computational resource law.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .candidates import CandidateGenerationPipeline, DirectedResearchQuery
from .runtime import LawSpaceRuntime
from .schema import digest_payload

KERNEL_OWNER_ID = "PHI-RESOURCE-THEORY-DISCOVERY/1.0.0"
SYNTHESIS_OWNER_ID = "RESOURCE-LAW-SYNTHESIS/1.0.0"
PROSPECTIVE_OWNER_ID = "RESOURCE-LAW-PROSPECTIVE-VALIDATION/1.0.0"
PROJECTION_OWNER_ID = "RESOURCE-PROJECTION-COMPARISON/1.0.0"
SCHEMA = "phi-resource-theory-discovery/v1"
KNOWN_RESOURCE_ANCHORS = (
    "entanglement", "entanglement_entropy", "magic", "magic_monotone",
    "treewidth", "rank", "operator_rank", "memory_rank", "bond_dimension",
)


def _with_digest(payload: dict[str, Any]) -> dict[str, Any]:
    payload["digest"] = digest_payload(payload)
    return payload


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else float("nan")


def _ols(xs: Sequence[float], ys: Sequence[float]) -> tuple[float, float]:
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("OLS requires >=2 paired samples")
    mx, my = _mean(xs), _mean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if den <= 1e-15:
        raise ValueError("degenerate resource predictor")
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    intercept = my - slope * mx
    return intercept, slope


def _r2(actual: Sequence[float], predicted: Sequence[float]) -> float:
    if len(actual) != len(predicted) or not actual:
        return float("nan")
    m = _mean(actual)
    ss_tot = sum((y - m) ** 2 for y in actual)
    ss_res = sum((y - p) ** 2 for y, p in zip(actual, predicted))
    if ss_tot <= 1e-15:
        return 1.0 if ss_res <= 1e-15 else 0.0
    return 1.0 - ss_res / ss_tot


def _rmse(actual: Sequence[float], predicted: Sequence[float]) -> float:
    if len(actual) != len(predicted) or not actual:
        return float("inf")
    return math.sqrt(_mean([(a - p) ** 2 for a, p in zip(actual, predicted)]))


def _mafre(actual: Sequence[float], predicted: Sequence[float]) -> float:
    if len(actual) != len(predicted) or not actual:
        return float("inf")
    vals = []
    for a, p in zip(actual, predicted):
        vals.append(abs(p - a) / max(abs(a), 1e-12))
    return _mean(vals)


def _corr(xs: Sequence[float], ys: Sequence[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return float("nan")
    mx, my = _mean(xs), _mean(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 1e-15 or vy <= 1e-15:
        return 0.0
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / math.sqrt(vx * vy)


def _gcd_nonzero(values: Sequence[int]) -> int:
    g = 0
    for v in values:
        if v:
            g = math.gcd(g, abs(int(v)))
    return g


@dataclass(frozen=True)
class ResourceExpression:
    feature_ids: tuple[str, ...]
    exponents: tuple[int, ...]

    @property
    def complexity(self) -> int:
        return sum(abs(x) for x in self.exponents) + sum(1 for x in self.exponents if x)

    def value(self, observables: Mapping[str, Any]) -> float:
        log_r = 0.0
        for fid, exp in zip(self.feature_ids, self.exponents):
            if exp == 0:
                continue
            if fid not in observables:
                raise KeyError(f"missing observable {fid}")
            x = float(observables[fid])
            if not math.isfinite(x) or x < 0:
                raise ValueError(f"resource observable {fid} must be finite and nonnegative")
            log_r += exp * math.log1p(x)
        return math.exp(log_r)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "GENERATED_POSITIVE_MONOMIAL_RESOURCE",
            "feature_ids": list(self.feature_ids),
            "exponents": list(self.exponents),
            "formula": "exp(sum_j exponent_j * log(1 + observable_j))",
            "complexity": self.complexity,
        }


class ResourceLawSynthesisOwner:
    """Blindly synthesize a scalar resource coordinate from execution evidence."""

    def __init__(self, runtime: LawSpaceRuntime) -> None:
        self.runtime = runtime

    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": SYNTHESIS_OWNER_ID,
            "candidate_source": "INTERNAL_OWNER_CONNECTED_PHI_SPACE_PLUS_FROZEN_EXECUTION_EVIDENCE",
            "known_resource_measures_prefreeze": "FORBIDDEN_AS_CANDIDATE_ANSWERS",
            "known_resource_measures_postfreeze": list(KNOWN_RESOURCE_ANCHORS),
            "candidate_family": "CONTENT_ADDRESSED_GENERATED_RESOURCE_EXPRESSIONS",
            "training_selection": "LEAVE_ONE_ENVIRONMENT_OUT_LOG_COST_GENERALIZATION_PLUS_COMPLEXITY",
            "prospective_data_visible_before_freeze": False,
        }

    @staticmethod
    def _validate_rows(rows: Sequence[Mapping[str, Any]]) -> tuple[tuple[str, ...], list[dict[str, Any]]]:
        normalized: list[dict[str, Any]] = []
        feature_set: set[str] | None = None
        seen: set[str] = set()
        for raw in rows:
            wid = str(raw.get("workload_id", "")).strip()
            env = str(raw.get("environment_id", "")).strip()
            exe = str(raw.get("executable_digest", "")).strip()
            meas = str(raw.get("measurement_receipt_digest", "")).strip()
            obs = dict(raw.get("observables", {}))
            cost = float(raw.get("measured_cost", float("nan")))
            if not wid or wid in seen or not env or not exe or not meas:
                raise ValueError("workload ids must be unique and provenance fields nonempty")
            if not obs or not math.isfinite(cost) or cost <= 0:
                raise ValueError("each workload requires nonempty observables and positive measured_cost")
            features = set(str(k) for k in obs)
            if any(str(k).lower() in KNOWN_RESOURCE_ANCHORS for k in features):
                raise ValueError("named known resource measures must be supplied only as post-freeze anchors")
            feature_set = features if feature_set is None else feature_set
            if features != feature_set:
                raise ValueError("all workloads must expose the same opaque observables")
            for k, v in obs.items():
                x = float(v)
                if not math.isfinite(x) or x < 0:
                    raise ValueError(f"observable {k} must be finite and nonnegative")
            normalized.append({
                "workload_id": wid,
                "environment_id": env,
                "executable_digest": exe,
                "measurement_receipt_digest": meas,
                "observables": {str(k): float(v) for k, v in obs.items()},
                "known_resource_anchors": {str(k): float(v) for k, v in dict(raw.get("known_resource_anchors", {})).items()},
                "measured_cost": cost,
            })
            seen.add(wid)
        return tuple(sorted(feature_set or ())), normalized

    @staticmethod
    def _expression_frontier(feature_ids: Sequence[str]) -> list[ResourceExpression]:
        if len(feature_ids) > 8:
            raise ValueError("qualification-grade scalar resource frontier supports <=8 opaque observables")
        out: list[ResourceExpression] = []
        for exps in itertools.product((0, 1, 2), repeat=len(feature_ids)):
            if not any(exps):
                continue
            if sum(exps) > 4 or sum(1 for e in exps if e) > 3:
                continue
            # Remove scale-equivalent expressions such as (2,0) vs (1,0).
            if _gcd_nonzero(exps) != 1:
                continue
            out.append(ResourceExpression(tuple(feature_ids), tuple(int(e) for e in exps)))
        return sorted(out, key=lambda x: (x.complexity, x.exponents))

    @staticmethod
    def _fit_expression(expr: ResourceExpression, rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        xr = [math.log(expr.value(r["observables"])) for r in rows]
        yc = [math.log(float(r["measured_cost"])) for r in rows]
        intercept, slope = _ols(xr, yc)
        pred_log = [intercept + slope * x for x in xr]
        pred = [math.exp(v) for v in pred_log]
        actual = [float(r["measured_cost"]) for r in rows]
        return {
            "intercept_log_cost": intercept,
            "slope_log_resource": slope,
            "train_log_rmse": _rmse(yc, pred_log),
            "train_r2_cost": _r2(actual, pred),
            "train_mafre": _mafre(actual, pred),
        }

    @classmethod
    def _cv_score(cls, expr: ResourceExpression, rows: Sequence[Mapping[str, Any]]) -> tuple[float, list[dict[str, Any]]]:
        envs = sorted({str(r["environment_id"]) for r in rows})
        if len(envs) < 3:
            raise ValueError("resource synthesis requires >=3 training environments")
        all_actual_log: list[float] = []
        all_pred_log: list[float] = []
        folds: list[dict[str, Any]] = []
        for env in envs:
            train = [r for r in rows if r["environment_id"] != env]
            hold = [r for r in rows if r["environment_id"] == env]
            if len(train) < 4 or not hold:
                raise ValueError("insufficient environment split support")
            fit = cls._fit_expression(expr, train)
            if fit["slope_log_resource"] <= 0:
                return float("inf"), []
            pred_log = [fit["intercept_log_cost"] + fit["slope_log_resource"] * math.log(expr.value(r["observables"])) for r in hold]
            actual_log = [math.log(float(r["measured_cost"])) for r in hold]
            all_actual_log.extend(actual_log); all_pred_log.extend(pred_log)
            folds.append({"heldout_environment_id": env, "log_rmse": _rmse(actual_log, pred_log), "count": len(hold)})
        cv = _rmse(all_actual_log, all_pred_log)
        # Small explicit complexity penalty, fixed before candidate inspection.
        return cv + 0.003 * expr.complexity, folds

    def synthesize(
        self,
        *,
        question: str,
        workload_rows: Sequence[Mapping[str, Any]],
        training_workload_ids: Sequence[str],
    ) -> Mapping[str, Any]:
        training_ids = tuple(sorted(set(str(x) for x in training_workload_ids)))
        # Hard pre-freeze firewall: do not even normalize/parse non-training cost rows.
        raw_train = [r for r in workload_rows if str(r.get("workload_id", "")) in set(training_ids)]
        feature_ids, rows = self._validate_rows(raw_train)
        row_by_id = {r["workload_id"]: r for r in rows}
        if not training_ids or any(x not in row_by_id for x in training_ids):
            return _with_digest({
                "schema": SCHEMA, "owner_id": SYNTHESIS_OWNER_ID,
                "status": "RESOURCE_THEORY_NOT_ESTABLISHED_INVALID_FREEZE_PARTITION",
                "claim_boundary": {"resource_theory_established": False},
            })
        train = [row_by_id[x] for x in training_ids]
        envs = sorted({r["environment_id"] for r in train})
        if len(train) < 12 or len(envs) < 3:
            return _with_digest({
                "schema": SCHEMA, "owner_id": SYNTHESIS_OWNER_ID,
                "status": "RESOURCE_THEORY_NOT_ESTABLISHED_INSUFFICIENT_TRAINING_SUPPORT",
                "training_workload_count": len(train), "training_environment_count": len(envs),
                "claim_boundary": {"resource_theory_established": False},
            })
        pipeline = CandidateGenerationPipeline(self.runtime.catalog, self.runtime.bridges)
        scan = pipeline.directed_research(DirectedResearchQuery(
            question=question,
            seed_owner_ids=("FND-01", "FND-11", "FND-12", "STRUCTURAL-IDENTIFIABILITY-EQUIVALENCE"),
            discovery_mode="BLIND_PRIMITIVE_FIREWALL",
            include_all_connected_owners=False,
        ))
        frontier = self._expression_frontier(feature_ids)
        scored: list[tuple[float, ResourceExpression, list[dict[str, Any]]]] = []
        for expr in frontier:
            try:
                score, folds = self._cv_score(expr, train)
            except Exception:
                continue
            if math.isfinite(score):
                scored.append((score, expr, folds))
        if not scored:
            return _with_digest({
                "schema": SCHEMA, "owner_id": SYNTHESIS_OWNER_ID,
                "status": "RESOURCE_THEORY_NOT_ESTABLISHED_NO_STABLE_CANDIDATE",
                "phi_scan_digest": scan["digest"],
                "claim_boundary": {"resource_theory_established": False, "internet_used_prefreeze": False},
            })
        scored.sort(key=lambda z: (z[0], z[1].complexity, z[1].exponents))
        best_score, best, folds = scored[0]
        fit = self._fit_expression(best, train)
        runner_up = scored[1][0] if len(scored) > 1 else float("inf")
        frozen_payload = {
            "feature_ids": list(feature_ids),
            "expression": best.to_dict(),
            "cost_law": {"kind": "POWER_LAW_IN_GENERATED_RESOURCE", **fit},
            "training_workload_ids": list(training_ids),
            "training_environment_ids": envs,
            "training_selection_score": best_score,
            "runner_up_score": runner_up,
            "selection_protocol": "LEAVE_ONE_ENVIRONMENT_OUT_LOG_COST_GENERALIZATION_PLUS_FIXED_COMPLEXITY_PENALTY",
            "known_resource_anchors_seen_prefreeze": False,
        }
        freeze_digest = digest_payload(frozen_payload)
        resource_id = "R-" + digest_payload({"expression": best.to_dict()})[:16].upper()
        payload = {
            "schema": SCHEMA,
            "owner_id": SYNTHESIS_OWNER_ID,
            "status": "RESOURCE_CANDIDATE_FROZEN",
            "resource_id": resource_id,
            "phi_scan_digest": scan["digest"],
            "phi_scan": {
                "registered_axis_count": scan["registered_axis_count"],
                "all_registered_axes_visited": scan["all_registered_axes_visited"],
                "owner_visits": scan["owner_visits"],
                "fixed_owner_visit_budget": scan["fixed_owner_visit_budget"],
                "fixed_candidate_axis_order_ceiling": scan["fixed_candidate_axis_order_ceiling"],
                "knowledge_firewall": scan["knowledge_firewall"],
            },
            "candidate_frontier_size": len(frontier),
            "frozen_resource": frozen_payload,
            "resource_freeze_digest": freeze_digest,
            "cv_folds": folds,
            "claim_boundary": {
                "internet_used_prefreeze": False,
                "known_named_resource_selected_as_answer": False,
                "prospective_costs_used_for_candidate_selection": False,
                "resource_theory_established": False,
                "world_resource_novelty_established": False,
            },
        }
        return _with_digest(payload)


class ProspectiveResourceValidationOwner:
    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": PROSPECTIVE_OWNER_ID,
            "required": "DISJOINT_PROSPECTIVE_WORKLOAD_IDS_AND_ENVIRONMENTS_AFTER_RESOURCE_FREEZE",
            "promotion_gate": {
                "prospective_r2_cost_min": 0.90,
                "prospective_mean_absolute_fractional_error_max": 0.15,
                "each_environment_r2_min": 0.75,
                "minimum_prospective_workloads": 12,
            },
        }

    @staticmethod
    def _expr_from_receipt(receipt: Mapping[str, Any]) -> ResourceExpression:
        d = receipt["frozen_resource"]["expression"]
        return ResourceExpression(tuple(d["feature_ids"]), tuple(int(x) for x in d["exponents"]))

    def validate(
        self,
        *,
        candidate_receipt: Mapping[str, Any],
        workload_rows: Sequence[Mapping[str, Any]],
        prospective_workload_ids: Sequence[str],
    ) -> Mapping[str, Any]:
        if candidate_receipt.get("status") != "RESOURCE_CANDIDATE_FROZEN":
            return _with_digest({"schema": SCHEMA, "owner_id": PROSPECTIVE_OWNER_ID, "status": "RESOURCE_THEORY_NOT_ESTABLISHED_NO_FROZEN_CANDIDATE"})
        prospective_ids = tuple(sorted(set(str(x) for x in prospective_workload_ids)))
        train_ids = set(candidate_receipt["frozen_resource"]["training_workload_ids"])
        if not prospective_ids or train_ids.intersection(prospective_ids):
            return _with_digest({"schema": SCHEMA, "owner_id": PROSPECTIVE_OWNER_ID, "status": "RESOURCE_THEORY_NOT_ESTABLISHED_PROSPECTIVE_LEAKAGE"})
        _, rows = ResourceLawSynthesisOwner._validate_rows(workload_rows)
        row_by_id = {r["workload_id"]: r for r in rows}
        if any(x not in row_by_id for x in prospective_ids):
            return _with_digest({"schema": SCHEMA, "owner_id": PROSPECTIVE_OWNER_ID, "status": "RESOURCE_THEORY_NOT_ESTABLISHED_MISSING_PROSPECTIVE_ROWS"})
        prospective = [row_by_id[x] for x in prospective_ids]
        train_envs = set(candidate_receipt["frozen_resource"]["training_environment_ids"])
        prospective_envs = sorted({r["environment_id"] for r in prospective})
        env_disjoint = not train_envs.intersection(prospective_envs)
        expr = self._expr_from_receipt(candidate_receipt)
        law = candidate_receipt["frozen_resource"]["cost_law"]
        b0, b1 = float(law["intercept_log_cost"]), float(law["slope_log_resource"])
        actual = [float(r["measured_cost"]) for r in prospective]
        predicted = [math.exp(b0 + b1 * math.log(expr.value(r["observables"]))) for r in prospective]
        r2 = _r2(actual, predicted); mafre = _mafre(actual, predicted)
        per_env = []
        env_ok = True
        for env in prospective_envs:
            idx = [i for i, r in enumerate(prospective) if r["environment_id"] == env]
            a = [actual[i] for i in idx]; p = [predicted[i] for i in idx]
            er2 = _r2(a, p)
            per_env.append({"environment_id": env, "count": len(idx), "r2_cost": er2, "mafre": _mafre(a, p)})
            env_ok = env_ok and er2 >= 0.75
        pass_gate = len(prospective) >= 12 and env_disjoint and r2 >= 0.90 and mafre <= 0.15 and env_ok and b1 > 0
        payload = {
            "schema": SCHEMA, "owner_id": PROSPECTIVE_OWNER_ID,
            "status": "RESOURCE_THEORY_PROSPECTIVELY_QUALIFIED" if pass_gate else "RESOURCE_THEORY_NOT_ESTABLISHED_PROSPECTIVE_FAILURE",
            "resource_id": candidate_receipt.get("resource_id"),
            "resource_freeze_digest": candidate_receipt.get("resource_freeze_digest"),
            "prospective_workload_ids": list(prospective_ids),
            "prospective_environment_ids": prospective_envs,
            "training_and_prospective_environments_disjoint": env_disjoint,
            "metrics": {"r2_cost": r2, "mean_absolute_fractional_error": mafre, "count": len(prospective), "per_environment": per_env},
            "claim_boundary": {
                "candidate_changed_after_prospective_observation": False,
                "known_named_resource_selected_as_answer": False,
                "world_resource_novelty_established": False,
                "synthetic_prospective_pass_is_world_resource_discovery": False,
            },
        }
        return _with_digest(payload)


class ResourceProjectionComparisonOwner:
    """Post-freeze comparison to named known resource anchors only."""
    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": PROJECTION_OWNER_ID,
            "selection_role": "POST_FREEZE_COMPARISON_ONLY",
            "may_modify_resource_candidate": False,
        }

    def compare(
        self,
        *,
        candidate_receipt: Mapping[str, Any],
        workload_rows: Sequence[Mapping[str, Any]],
        prospective_workload_ids: Sequence[str],
    ) -> Mapping[str, Any]:
        if candidate_receipt.get("status") != "RESOURCE_CANDIDATE_FROZEN":
            return _with_digest({"schema": SCHEMA, "owner_id": PROJECTION_OWNER_ID, "status": "PROJECTION_COMPARISON_BLOCKED_NO_FROZEN_RESOURCE"})
        _, rows = ResourceLawSynthesisOwner._validate_rows(workload_rows)
        row_by_id = {r["workload_id"]: r for r in rows}
        selected = [row_by_id[str(x)] for x in prospective_workload_ids if str(x) in row_by_id]
        expr = ProspectiveResourceValidationOwner._expr_from_receipt(candidate_receipt)
        rv = [expr.value(r["observables"]) for r in selected]
        anchors = sorted(set().union(*(set(r.get("known_resource_anchors", {})) for r in selected))) if selected else []
        comparisons = []
        for name in anchors:
            if name.lower() not in KNOWN_RESOURCE_ANCHORS:
                continue
            vals = [float(r.get("known_resource_anchors", {}).get(name, float("nan"))) for r in selected]
            if not all(math.isfinite(v) for v in vals):
                continue
            comparisons.append({"anchor_name": name, "correlation_with_generated_resource": _corr(vals, rv)})
        return _with_digest({
            "schema": SCHEMA, "owner_id": PROJECTION_OWNER_ID,
            "status": "POSTFREEZE_RESOURCE_PROJECTION_COMPARISON",
            "resource_id": candidate_receipt.get("resource_id"),
            "resource_freeze_digest": candidate_receipt.get("resource_freeze_digest"),
            "comparisons": comparisons,
            "selection_feedback_to_frozen_resource": False,
            "claim_boundary": {"known_anchor_equivalence_established": False},
        })


class ResourceTheoryDiscoveryKernel:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.runtime = LawSpaceRuntime(self.root)
        self.synthesis = ResourceLawSynthesisOwner(self.runtime)
        self.prospective = ProspectiveResourceValidationOwner()
        self.projections = ResourceProjectionComparisonOwner()

    def contract(self) -> Mapping[str, Any]:
        return {
            "owner_id": KERNEL_OWNER_ID,
            "schema": SCHEMA,
            "owners": {
                "synthesis": self.synthesis.contract(),
                "prospective_validation": self.prospective.contract(),
                "postfreeze_projection": self.projections.contract(),
            },
            "pipeline": "INTERNAL_PHI_SCAN->TRAIN_ONLY_RESOURCE_SYNTHESIS->FREEZE->PROSPECTIVE_UNSEEN_WORKLOADS->POSTFREEZE_KNOWN_RESOURCE_PROJECTIONS",
            "claim_boundary": {
                "internet_is_prefreeze_resource_selector": False,
                "known_resource_catalog_is_candidate_answer_space": False,
                "synthetic_qualification_is_world_resource_discovery": False,
                "resource_theory_implies_theory_truth": False,
            },
            "roadmap_dependency": {
                "completed_before": ["PHI-THEORY-COMPILER"],
                "next": "AUTOMATIC-DISCRIMINATING-EXPERIMENT",
                "closure_target": "RESOURCE_LAW->DISCRIMINATING_EXPERIMENT->WORLD_ATTESTATION",
            },
        }

    def discover_and_validate(
        self,
        *,
        question: str,
        workload_rows: Sequence[Mapping[str, Any]],
        training_workload_ids: Sequence[str],
        prospective_workload_ids: Sequence[str],
    ) -> Mapping[str, Any]:
        candidate = self.synthesis.synthesize(question=question, workload_rows=workload_rows, training_workload_ids=training_workload_ids)
        validation = self.prospective.validate(candidate_receipt=candidate, workload_rows=workload_rows, prospective_workload_ids=prospective_workload_ids)
        projections = self.projections.compare(candidate_receipt=candidate, workload_rows=workload_rows, prospective_workload_ids=prospective_workload_ids)
        established = validation.get("status") == "RESOURCE_THEORY_PROSPECTIVELY_QUALIFIED"
        return _with_digest({
            "schema": SCHEMA, "owner_id": KERNEL_OWNER_ID,
            "status": "RESOURCE_THEORY_DISCOVERED_PROSPECTIVE" if established else "RESOURCE_THEORY_NOT_ESTABLISHED",
            "candidate": candidate, "prospective_validation": validation, "postfreeze_projection_comparison": projections,
            "claim_boundary": {
                "world_resource_novelty_established": False,
                "world_resource_theory_established": False,
                "synthetic_mechanism_qualified": established,
                "internet_used_prefreeze": False,
            },
        })
