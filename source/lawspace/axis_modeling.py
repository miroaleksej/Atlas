"""Domain-neutral AXIS-MODELING owner for Phi-LawSpace v8.0.

The owner starts from data and typed axes, not from a declared physical law.
It samples research regions, fits only a low-capacity baseline, searches for
stable residual structure, explores owner/domain-neutral combinations and void/frontier
regions, proposes generated/latent research axes, and tests those coordinates on a
regime-level OOD partition. Exploration is deliberately wider than promotion: an
unverified candidate is retained as a potential mechanism and is never called false
merely because it is unknown or not promoted. It never promotes a scientific law.

Pipeline:
region -> sample axes -> model baseline -> measure residuals -> detect structure
-> propose missing/generated axis -> local multiscale exploration -> OOD test
-> semantic axis admission -> promotion boundary.
"""
from __future__ import annotations

import dataclasses
import itertools
import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

from .schema import digest_payload
from .research_cycle import DynamicAxisAdmissionOwner, DynamicAxisProposal

SCHEMA = "phi-axis-modeling/v8.0"
OWNER_ID = "AXIS-MODELING/8.0.0"
MODES = (
    "RANDOM", "HYPERVOID", "VOID_FRONTIER", "BOUNDARY", "EXTREME",
    "CROSSDOMAIN", "UNCERTAINTY", "AXIS_BIRTH", "COMBINATION_BIRTH",
)


@dataclass(frozen=True)
class ModelingAxis:
    axis_id: str
    domain: str
    units: str
    role: str = "observed"
    values: tuple[float, ...] = ()
    provenance: str = ""
    owner_id: str = ""

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "ModelingAxis":
        return cls(
            axis_id=str(row.get("axis_id", "")),
            domain=str(row.get("domain", "")),
            units=str(row.get("units", "")),
            role=str(row.get("role", "observed")),
            values=tuple(float(v) for v in row.get("values", ())),
            provenance=str(row.get("provenance", "")),
            owner_id=str(row.get("owner_id", "")),
        )

    def validate(self, n: int) -> None:
        if not self.axis_id or not self.domain or not self.units or not self.provenance:
            raise ValueError("axis modeling requires typed axis_id/domain/units/provenance")
        if self.role not in {"observed", "generated", "latent", "nuisance"}:
            raise ValueError(f"unsupported axis role {self.role}")
        if len(self.values) != n or not np.all(np.isfinite(np.asarray(self.values, dtype=float))):
            raise ValueError(f"axis {self.axis_id}: finite values length must match observable")


@dataclass(frozen=True)
class AxisModelingDataset:
    dataset_id: str
    observable_id: str
    observable_units: str
    y: tuple[float, ...]
    sigma: tuple[float, ...] | None
    regime_ids: tuple[str, ...]
    axes: tuple[ModelingAxis, ...]
    provenance: str

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> "AxisModelingDataset":
        sigma = row.get("sigma")
        return cls(
            dataset_id=str(row.get("dataset_id", "")),
            observable_id=str(row.get("observable_id", "")),
            observable_units=str(row.get("observable_units", "")),
            y=tuple(float(v) for v in row.get("y", ())),
            sigma=None if sigma is None else tuple(float(v) for v in sigma),
            regime_ids=tuple(str(v) for v in row.get("regime_ids", ())),
            axes=tuple(ModelingAxis.from_mapping(a) for a in row.get("axes", ())),
            provenance=str(row.get("provenance", "")),
        )

    def validate(self) -> None:
        n = len(self.y)
        if not self.dataset_id or not self.observable_id or not self.observable_units or not self.provenance:
            raise ValueError("dataset id/observable/units/provenance are required")
        if n < 8 or not np.all(np.isfinite(np.asarray(self.y, dtype=float))):
            raise ValueError("axis modeling requires at least 8 finite observations")
        if len(self.regime_ids) != n or not all(self.regime_ids):
            raise ValueError("regime_ids must be declared for every observation")
        if self.sigma is not None:
            s = np.asarray(self.sigma, dtype=float)
            if s.size != n or not np.all(np.isfinite(s)) or not np.all(s > 0):
                raise ValueError("sigma must be finite, positive and observation-aligned")
        if not self.axes:
            raise ValueError("at least one axis required")
        ids = [a.axis_id for a in self.axes]
        if len(ids) != len(set(ids)):
            raise ValueError("axis ids must be unique")
        for axis in self.axes:
            axis.validate(n)


class AxisModelingOwner:
    owner_id = OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner": OWNER_ID,
            "modes": list(MODES),
            "pipeline": [
                "REGION", "SAMPLE_AXES", "GLOBAL_AXIS_COMBINATIONS", "VOID_FRONTIER",
                "LOW_CAPACITY_BASELINE", "RESIDUAL_STRUCTURE", "AXIS_BIRTH",
                "COMBINATION_BIRTH", "LOCAL_MULTISCALE", "REGIME_OOD",
                "FALSIFICATION_BOUNDARY", "PROMOTION_OWNER",
            ],
            "hard_rules": {
                "literature_before_freeze": False,
                "single_random_hit_can_promote": False,
                "measurement_uncertainty_required_for_scientific_promotion": True,
                "generated_axis_requires_regime_ood_gain": True,
                "canonical_axis_registry_mutation": "ONLY_VIA_DYNAMIC_AXIS_PROMOTION_OWNER_AFTER_VALIDATION",
                "candidate_registry_is_baseline_not_solution_space": True,
                "unknown_candidate_is_not_false": True,
                "void_region_is_research_target_not_proof_of_absence": True,
                "search_and_promotion_are_separate": True,
                "owner_affiliation_cannot_block_axis_combination": True,
                "domain_affiliation_cannot_block_axis_combination": True,
                "high_dimensionality_may_lower_promotion_confidence_but_not_search_admissibility": True,
                "joint_tuple_combination_requires_no_arithmetic_unit_merge": True,
                "arithmetic_composite_coordinate_requires_typed_functor_or_normalization": True,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    @staticmethod
    def _standardize_train(X: np.ndarray, train: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        mu = np.mean(X[train], axis=0)
        scale = np.std(X[train], axis=0)
        scale = np.where(scale > 1e-12, scale, 1.0)
        return (X - mu) / scale, mu, scale

    @staticmethod
    def _baseline_features(Z: np.ndarray) -> np.ndarray:
        # Intentionally low capacity: intercept, linear axes, squares, pairwise interactions.
        n, p = Z.shape
        cols = [np.ones(n)]
        cols.extend(Z[:, j] for j in range(p))
        cols.extend(Z[:, j] ** 2 for j in range(p))
        if p <= 8:
            for i in range(p):
                for j in range(i + 1, p):
                    cols.append(Z[:, i] * Z[:, j])
        return np.column_stack(cols)

    @staticmethod
    def _ridge_fit(X: np.ndarray, y: np.ndarray, ridge: float = 1e-8) -> np.ndarray:
        eye = np.eye(X.shape[1])
        eye[0, 0] = 0.0
        return np.linalg.solve(X.T @ X + ridge * eye, X.T @ y)

    @staticmethod
    def _rmse(y: np.ndarray, pred: np.ndarray) -> float:
        return float(np.sqrt(np.mean((y - pred) ** 2)))

    @staticmethod
    def _log_likelihood(y: np.ndarray, pred: np.ndarray, sigma: np.ndarray) -> float:
        r = (y - pred) / sigma
        return float(np.sum(-0.5 * r * r - np.log(sigma * math.sqrt(2.0 * math.pi))))

    @staticmethod
    def _random_regions(rng: np.random.Generator, axis_ids: Sequence[str], count: int = 64) -> list[list[str]]:
        """Materialize diverse finite axis combinations without an order ceiling.

        ``count`` is an execution/materialization budget, not an admissibility
        bound.  Every order 1..p remains part of the exploration space and the
        full p-axis region is always addressable.  Owner/domain affiliation is
        intentionally absent from the combination gate.
        """
        p = len(axis_ids)
        if p < 1:
            return []
        axes = np.asarray(list(axis_ids), dtype=object)
        out: list[list[str]] = []
        # Deterministic anchors ensure low-, intermediate-, and full-order
        # regions are represented whenever the execution budget permits.
        anchor_orders = [1, 2, 3, 4, 8, 16, 32, 64, p]
        for k in anchor_orders:
            k = min(p, max(1, int(k)))
            ids = sorted(str(x) for x in rng.choice(axes, size=k, replace=False).tolist())
            if ids not in out:
                out.append(ids)
            if len(out) >= count:
                return out
        # Remaining materializations sample the entire order interval 1..p.
        attempts = 0
        while len(out) < count and attempts < max(16, count * 8):
            attempts += 1
            k = int(rng.integers(1, p + 1))
            ids = sorted(str(x) for x in rng.choice(axes, size=k, replace=False).tolist())
            if ids not in out:
                out.append(ids)
        return out

    @staticmethod
    def _combination_metadata(region: Sequence[str], axes: Sequence[ModelingAxis]) -> Mapping[str, Any]:
        lookup = {a.axis_id: a for a in axes}
        selected = [lookup[str(axis_id)] for axis_id in region]
        domains = sorted({a.domain for a in selected})
        owners = sorted({a.owner_id for a in selected if a.owner_id})
        return {
            "axes": list(region),
            "axis_order": len(region),
            "domains": domains,
            "owner_ids": owners,
            "cross_domain": len(domains) > 1,
            "cross_owner": len(owners) > 1,
            "owner_affiliation_is_combination_gate": False,
            "domain_affiliation_is_combination_gate": False,
            "coordinate_semantics": "JOINT_TYPED_TUPLE_REGION_NO_ARITHMETIC_IDENTIFICATION",
            "arithmetic_composition_requires_typed_contract": True,
            "research_status": "AXIS_COMBINATION_RESEARCH_CANDIDATE",
        }

    @staticmethod
    def _hypervoid_score(region: Sequence[str], materialized: Sequence[Sequence[str]]) -> float:
        r = set(region)
        if not materialized:
            return 1.0
        best = 0.0
        for row in materialized:
            m = set(str(x) for x in row)
            union = r | m
            j = len(r & m) / len(union) if union else 1.0
            best = max(best, j)
        return 1.0 - best

    @classmethod
    def _predict_frozen_model(cls, frozen: Mapping[str, Any], axis_matrix: np.ndarray, *, augmented: bool) -> np.ndarray:
        axis_ids = tuple(str(x) for x in frozen.get("axis_ids", ()))
        X = np.asarray(axis_matrix, dtype=float)
        if X.ndim != 2 or X.shape[1] != len(axis_ids):
            raise ValueError("frozen axis model input shape does not match axis_ids")
        mu = np.asarray(frozen.get("train_standardization_mu", ()), dtype=float)
        scale = np.asarray(frozen.get("train_standardization_scale", ()), dtype=float)
        if mu.shape != (X.shape[1],) or scale.shape != (X.shape[1],):
            raise ValueError("frozen standardization shape mismatch")
        Z = (X - mu) / scale
        B = cls._baseline_features(Z)
        if not augmented:
            beta = np.asarray(frozen.get("baseline_coefficients", ()), dtype=float)
            if beta.shape != (B.shape[1],):
                raise ValueError("frozen baseline coefficient shape mismatch")
            return B @ beta
        source_index = int(frozen.get("source_axis_index", -1))
        if source_index < 0 or source_index >= X.shape[1]:
            raise ValueError("invalid frozen source_axis_index")
        center = float(frozen["generated_center"]); width = float(frozen["generated_width"])
        if not math.isfinite(width) or width <= 0:
            raise ValueError("frozen generated_width must be positive")
        g = np.exp(-0.5 * ((X[:, source_index] - center) / width) ** 2)
        lookup = {name: i for i, name in enumerate(axis_ids)}
        extra = [g]
        for axis_id in frozen.get("interaction_axes", ()):
            if str(axis_id) not in lookup:
                raise ValueError(f"frozen interaction axis missing: {axis_id}")
            extra.append(g * X[:, lookup[str(axis_id)]])
        A = np.column_stack([B, *extra])
        coef = np.asarray(frozen.get("augmented_coefficients", ()), dtype=float)
        if coef.shape != (A.shape[1],):
            raise ValueError("frozen augmented coefficient shape mismatch")
        return A @ coef

    def evaluate_frozen_axis_candidate(self, modeling_result: Mapping[str, Any], dataset: Mapping[str, Any]) -> Mapping[str, Any]:
        """Evaluate a frozen axis-born model on data unavailable during search."""
        ds = AxisModelingDataset.from_mapping(dataset); ds.validate()
        candidate = dict(modeling_result.get("best_axis_birth") or {})
        frozen = dict(candidate.get("frozen_model") or {})
        if not frozen:
            payload = {"status": "NO_FROZEN_AXIS_CANDIDATE", "count": len(ds.y)}
            return {**payload, "digest": digest_payload(payload)}
        expected = tuple(str(x) for x in frozen.get("axis_ids", ()))
        supplied = tuple(a.axis_id for a in ds.axes)
        if supplied != expected:
            raise ValueError(f"sealed dataset axis order mismatch: expected {expected}, got {supplied}")
        X = np.column_stack([np.asarray(a.values, dtype=float) for a in ds.axes])
        y = np.asarray(ds.y, dtype=float)
        baseline = self._predict_frozen_model(frozen, X, augmented=False)
        augmented = self._predict_frozen_model(frozen, X, augmented=True)
        rb = self._rmse(y, baseline); ra = self._rmse(y, augmented)
        scale_y = float(np.std(y)) or max(abs(float(np.mean(y))), 1.0)
        rows = [{
            "row_index": i,
            "axis_values": {a.axis_id: float(X[i, j]) for j, a in enumerate(ds.axes)},
            "observed": float(y[i]),
            "baseline_prediction": float(baseline[i]),
            "augmented_prediction": float(augmented[i]),
        } for i in range(len(y))]
        payload = {
            "schema": "phi-axis-modeling-sealed-evaluation/v1", "owner": OWNER_ID,
            "status": "SEALED_POSTFREEZE_EVALUATED", "dataset_id": ds.dataset_id, "count": len(y),
            "baseline_rmse": rb, "augmented_rmse": ra, "baseline_nrmse": rb / scale_y, "augmented_nrmse": ra / scale_y,
            "fractional_rmse_improvement": (rb - ra) / rb if rb > 0 else 0.0,
            "candidate_axis_id": candidate.get("axis_id"), "candidate_frozen_model_digest": digest_payload(frozen),
            "refit_performed": False, "rows": rows,
            "claim_boundary": {"sealed_values_used_for_search_or_fit": False, "postfreeze_evaluation_is_scientific_promotion": False},
        }
        return {**payload, "digest": digest_payload(payload)}

    def design_discriminating_experiment(self, modeling_result: Mapping[str, Any], *, observed_points: Sequence[Mapping[str, Any]] = (), maximum_points: int = 256) -> Mapping[str, Any]:
        """Generate unmeasured input points from train-frozen ranges and rank by competitor disagreement."""
        generated = [dict(x) for x in modeling_result.get("modes", {}).get("AXIS_BIRTH", {}).get("candidates", ()) if x.get("frozen_model")]
        generated = [x for x in generated if x.get("status") != "AXIS_BIRTH_REJECTED"] or generated
        generated = generated[:5]
        if not generated:
            payload = {"status": "DISCRIMINATING_EXPERIMENT_NOT_AVAILABLE", "selected_experiment": None, "rows": []}
            return {**payload, "digest": digest_payload(payload)}
        primary = generated[0]; frozen0 = dict(primary["frozen_model"]); axis_ids = tuple(str(x) for x in frozen0["axis_ids"])
        summaries = dict(modeling_result.get("dataset", {}).get("train_axis_summary", {}))
        if any(axis_id not in summaries for axis_id in axis_ids):
            raise ValueError("train_axis_summary incomplete for discriminator")
        value_sets=[]; best_source=str(primary.get("source_axis_id", "")); center=float(primary.get("center_from_train_only",0.0)); width=float(primary.get("width_from_train_only",0.0))
        for axis_id in axis_ids:
            row=dict(summaries[axis_id]); lo=float(row["minimum"]); hi=float(row["maximum"]); med=float(row["median"]); small=row.get("unique_values_if_small")
            if isinstance(small,list) and small:
                vals=[float(v) for v in small]
                if len(vals)==2 and set(round(v,12) for v in vals) != {0.0,1.0}: vals.append(0.5*(vals[0]+vals[1]))
            else: vals=[lo,med,hi]
            if axis_id==best_source and width>0: vals.extend([center-width,center,center+width])
            vals=[min(hi,max(lo,float(v))) for v in vals]
            value_sets.append(sorted(set(round(v,12) for v in vals)))
        observed=set()
        for point in observed_points:
            vals=dict(point.get("values",point))
            try: observed.add(tuple(round(float(vals[a]),12) for a in axis_ids))
            except (KeyError,TypeError,ValueError): pass
        rows=[]
        for combo in itertools.product(*value_sets):
            if len(rows) >= max(1,int(maximum_points)): break
            key=tuple(round(float(v),12) for v in combo)
            if key in observed: continue
            X=np.asarray([combo],dtype=float); predictions=[float(self._predict_frozen_model(frozen0,X,augmented=False).item())]; labels=["LOW_CAPACITY_BASELINE"]
            for cand in generated:
                frozen=dict(cand["frozen_model"])
                if tuple(str(x) for x in frozen.get("axis_ids",())) != axis_ids: continue
                predictions.append(float(self._predict_frozen_model(frozen,X,augmented=True).item())); labels.append(str(cand.get("axis_id","AXIS_BIRTH")))
            if len(predictions)<2: continue
            rows.append({"experiment_id":f"AUTO-DISC-{len(rows):04d}","axis_values":{a:float(v) for a,v in zip(axis_ids,combo)},"competitor_labels":labels,"candidate_predictions":predictions,"prediction_variance":float(np.var(predictions)),"prediction_span":float(max(predictions)-min(predictions)),"already_observed":False})
        rows.sort(key=lambda r:(-float(r["prediction_variance"]),-float(r["prediction_span"]),str(r["experiment_id"])))
        selected=rows[0] if rows else None
        payload={"schema":"phi-axis-modeling-discriminating-experiment/v1","owner":OWNER_ID,"status":"AUTO_DISAGREEMENT_EXPERIMENT_RANKED" if selected else "DISCRIMINATING_EXPERIMENT_NOT_AVAILABLE","design_policy":"AUTO_GRID_FROM_TRAIN_FROZEN_AXIS_RANGES_AND_BORN_COORDINATE_NO_TARGET_VALUES","selected_experiment":selected,"rows":rows,"invented_likelihoods":False,"sealed_holdout_values_used":False}
        return {**payload,"digest":digest_payload(payload)}

    def run(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        ds = AxisModelingDataset.from_mapping(request.get("dataset", {}))
        ds.validate()
        seed = int(request.get("seed", 0))
        rng = np.random.default_rng(seed)
        modes = tuple(str(m).upper() for m in request.get("modes", MODES))
        unknown_modes = sorted(set(modes) - set(MODES))
        if unknown_modes:
            raise ValueError(f"unsupported AXIS-MODELING modes: {unknown_modes}")

        y = np.asarray(ds.y, dtype=float)
        X = np.column_stack([np.asarray(a.values, dtype=float) for a in ds.axes])
        axis_ids = [a.axis_id for a in ds.axes]
        regimes = np.asarray(ds.regime_ids, dtype=object)
        ood_regimes = set(str(x) for x in request.get("ood_regime_ids", ()))
        if not ood_regimes:
            unique = sorted(set(ds.regime_ids))
            ood_regimes = {unique[-1]}
        ood = np.asarray([str(r) in ood_regimes for r in regimes], dtype=bool)
        train = ~ood
        if np.count_nonzero(train) < 6 or np.count_nonzero(ood) < 2:
            raise ValueError("regime-level OOD split requires >=6 train and >=2 OOD observations")

        Z, mu, scale = self._standardize_train(X, train)
        B = self._baseline_features(Z)
        beta = self._ridge_fit(B[train], y[train])
        pred0 = B @ beta
        train_rmse0 = self._rmse(y[train], pred0[train])
        ood_rmse0 = self._rmse(y[ood], pred0[ood])
        sigma_measured = None if ds.sigma is None else np.asarray(ds.sigma, dtype=float)
        # Exploratory scale is explicitly not a measurement uncertainty.
        dof = max(1, int(np.count_nonzero(train) - B.shape[1]))
        exploratory_sigma = max(float(np.sqrt(np.sum((y[train] - pred0[train]) ** 2) / dof)), 1e-9)

        materialized = tuple(tuple(str(x) for x in row) for row in request.get("materialized_axis_sets", ()))
        random_regions = self._random_regions(rng, axis_ids)
        combination_regions = [self._combination_metadata(row, ds.axes) for row in random_regions]
        hypervoid_regions = sorted(
            ({
                **self._combination_metadata(row, ds.axes),
                "hypervoid_score": self._hypervoid_score(row, materialized),
                "research_status": "VOID_FRONTIER_CANDIDATE",
                "absence_interpretation": "UNRESOLVED_NOT_FALSE_NOT_PHYSICALLY_EMPTY",
                "candidate_explanations": [
                    "SAMPLING_GAP", "KNOWN_CONSTRAINT", "STABILITY_EXCLUSION",
                    "SELECTION_EFFECT", "MISSING_OBSERVER", "MISSING_AXIS",
                    "MISSING_REPRESENTATION", "UNKNOWN_MECHANISM_OR_LAW",
                ],
            } for row in random_regions),
            key=lambda z: (-z["hypervoid_score"], len(z["axes"]), z["axes"]),
        )[:12]

        boundary_rows: dict[str, list[int]] = {}
        extreme_score = np.zeros(len(y), dtype=float)
        for j, axis in enumerate(ds.axes):
            vals = X[:, j]
            lo, hi = np.quantile(vals[train], [0.1, 0.9])
            boundary_rows[axis.axis_id] = [int(i) for i in np.where((vals <= lo) | (vals >= hi))[0].tolist()]
            extreme_score += np.abs(Z[:, j])
        extreme_rows = [int(i) for i in np.argsort(-extreme_score)[: min(12, len(y))].tolist()]

        domains = {a.domain for a in ds.axes}
        crossdomain_rows = [row for row in combination_regions if row["cross_domain"]]
        crossowner_rows = [row for row in combination_regions if row["cross_owner"]]
        crossdomain = {
            "status": "AVAILABLE" if len(domains) >= 2 else "BLOCKED_SINGLE_DOMAIN_DATA",
            "domains": sorted(domains),
            "owner_affiliation_is_combination_gate": False,
            "domain_affiliation_is_combination_gate": False,
            "cross_domain_materialized_region_count": len(crossdomain_rows),
            "cross_owner_materialized_region_count": len(crossowner_rows),
            "materialized_region_count": len(combination_regions),
            "maximum_materialized_axis_order": max((r["axis_order"] for r in combination_regions), default=0),
            "full_dataset_axis_order_materialized": any(r["axis_order"] == len(ds.axes) for r in combination_regions),
            "search_order_ceiling": None,
            "note": "Materialization budget limits execution count only; it does not restrict admissible axis order or ownership/domain combinations.",
        }
        uncertainty_mode = {
            "status": "AVAILABLE" if sigma_measured is not None else "BLOCKED_NO_MEASUREMENT_UNCERTAINTY",
            "measurement_uncertainty_is_declared": sigma_measured is not None,
        }

        # AXIS_BIRTH: discover a residual-localized coordinate on each observed axis.
        residual = y - pred0
        generated: list[Mapping[str, Any]] = []
        binary_axis_indices = [j for j in range(X.shape[1]) if len(np.unique(X[train, j])) == 2]
        for j, axis in enumerate(ds.axes):
            unique = np.unique(X[train, j])
            if unique.size < 4:
                continue
            # Center is chosen only from train residuals. Aggregate repeated x-values.
            best_center = None
            best_strength = -math.inf
            for xv in unique:
                mask = train & np.isclose(X[:, j], xv)
                strength = float(np.mean(np.abs(residual[mask])))
                if strength > best_strength:
                    best_strength, best_center = strength, float(xv)
            spacing = float(np.median(np.diff(unique))) if unique.size > 1 else float(np.std(X[train, j]))
            spread = float(np.std(X[train, j]))
            width0 = max(abs(spacing) * 0.8, spread * 0.12, 1e-9)
            # Width refinement uses train only; OOD is untouched until final scoring.
            candidates = []
            for factor in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
                width = width0 * factor
                g = np.exp(-0.5 * ((X[:, j] - best_center) / width) ** 2)
                extra = [g]
                interaction_axes = []
                for bj in binary_axis_indices:
                    if bj != j:
                        extra.append(g * X[:, bj])
                        interaction_axes.append(ds.axes[bj].axis_id)
                A = np.column_stack([B, *extra])
                coef = self._ridge_fit(A[train], y[train])
                pred = A @ coef
                candidates.append((self._rmse(y[train], pred[train]), width, pred, len(extra), interaction_axes, coef))
            _, width, pred1, extra_count, interaction_axes, augmented_coef = min(candidates, key=lambda z: z[0])
            g_selected = np.exp(-0.5 * ((X[:, j] - best_center) / width) ** 2)
            # Distinguish a useful derived feature from one already spanned by the
            # low-capacity baseline.  This is feature identifiability, not a claim
            # that the coordinate is an independent physical dimension.
            g_coef = self._ridge_fit(B[train], g_selected[train])
            g_resid = g_selected[train] - B[train] @ g_coef
            g_norm = float(np.linalg.norm(g_selected[train]))
            derived_feature_residual_fraction = float(np.linalg.norm(g_resid) / g_norm) if g_norm > 1e-12 else 0.0
            derived_feature_identifiability_pass = derived_feature_residual_fraction > 1e-3
            ood_rmse1 = self._rmse(y[ood], pred1[ood])
            train_rmse1 = self._rmse(y[train], pred1[train])
            eval_sigma = sigma_measured if sigma_measured is not None else np.full_like(y, exploratory_sigma)
            ll0 = self._log_likelihood(y[ood], pred0[ood], eval_sigma[ood])
            ll1 = self._log_likelihood(y[ood], pred1[ood], eval_sigma[ood])
            delta_ll = ll1 - ll0
            penalty = float(extra_count)
            score = float(delta_ll - penalty)
            # local neighborhood uses only fixed center/width perturbations and untouched OOD.
            local = []
            for dc in (-0.5, -0.25, 0.0, 0.25, 0.5):
                for wf in (0.75, 1.0, 1.25):
                    center2 = best_center + dc * max(abs(spacing), 1e-9)
                    width2 = width * wf
                    g = np.exp(-0.5 * ((X[:, j] - center2) / width2) ** 2)
                    extra = [g] + [g * X[:, bj] for bj in binary_axis_indices if bj != j]
                    A = np.column_stack([B, *extra])
                    coef = self._ridge_fit(A[train], y[train])
                    pp = A @ coef
                    local.append({
                        "center": float(center2), "width": float(width2),
                        "ood_rmse": self._rmse(y[ood], pp[ood]),
                        "ood_improves_baseline": self._rmse(y[ood], pp[ood]) < ood_rmse0,
                    })
            robust_fraction = float(np.mean([row["ood_improves_baseline"] for row in local]))
            axis_id = f"generated_residual_localization__{axis.axis_id}"
            status = (
                "AXIS_BIRTH_OOD_VALIDATED" if sigma_measured is not None and score > 0 and robust_fraction >= 0.6
                else "AXIS_BIRTH_PROMISING_EXPLORATORY" if ood_rmse1 < ood_rmse0 and robust_fraction >= 0.6
                else "AXIS_BIRTH_REJECTED"
            )
            residual_by_regime = {}
            for rid in sorted(set(ds.regime_ids)):
                mask = regimes == rid
                rr = y[mask] - pred1[mask]
                residual_by_regime[str(rid)] = {
                    "n": int(np.count_nonzero(mask)),
                    "mean": float(np.mean(rr)),
                    "rmse": float(np.sqrt(np.mean(rr * rr))),
                }
            generated.append({
                "axis_id": axis_id,
                "source_axis_id": axis.axis_id,
                "generated_coordinate": "exp(-0.5*((x-center)/width)^2)",
                "center_from_train_only": best_center,
                "width_from_train_only": float(width),
                "interaction_axes": interaction_axes,
                "frozen_model": {
                    "schema": "phi-axis-modeling-frozen-axis-candidate/v1",
                    "axis_ids": list(axis_ids),
                    "source_axis_id": axis.axis_id,
                    "source_axis_index": int(j),
                    "train_standardization_mu": [float(v) for v in mu],
                    "train_standardization_scale": [float(v) for v in scale],
                    "baseline_coefficients": [float(v) for v in beta],
                    "augmented_coefficients": [float(v) for v in augmented_coef],
                    "generated_center": float(best_center),
                    "generated_width": float(width),
                    "interaction_axes": list(interaction_axes),
                    "baseline_feature_class": "INTERCEPT_LINEAR_SQUARES_PAIRWISE",
                    "interaction_uses_raw_axis_values": True,
                    "fit_rows": int(np.count_nonzero(train)),
                    "validation_rows": int(np.count_nonzero(ood)),
                },
                "train_rmse_baseline": train_rmse0,
                "train_rmse_augmented": train_rmse1,
                "ood_rmse_baseline": ood_rmse0,
                "ood_rmse_augmented": ood_rmse1,
                "ood_rmse_fractional_improvement": float((ood_rmse0 - ood_rmse1) / ood_rmse0),
                "delta_log_likelihood_ood": float(delta_ll),
                "complexity_penalty": penalty,
                "axis_score": score,
                "derived_feature_residual_fraction": derived_feature_residual_fraction,
                "derived_feature_identifiability_pass": derived_feature_identifiability_pass,
                "score_uses_measurement_uncertainty": sigma_measured is not None,
                "exploratory_scale_if_no_sigma": None if sigma_measured is not None else exploratory_sigma,
                "local_multiscale_robust_fraction": robust_fraction,
                "local_multiscale": local,
                "residual_by_regime_after_axis": residual_by_regime,
                "status": status,
                "promotion_status": status,
                "research_status": "POTENTIAL_LAW_OR_MECHANISM_CANDIDATE",
                "epistemic_status": (
                    "OOD_SUPPORTED_CANDIDATE" if status == "AXIS_BIRTH_OOD_VALIDATED"
                    else "UNVERIFIED_CANDIDATE"
                ),
                "unknown_is_false": False,
            })
        # COMBINATION_BIRTH: use cross-domain/cross-owner axis tuples as actual
        # residual carriers.  The generic carrier is a train-frozen radial
        # localization in standardized joint-coordinate space.  This is a
        # research representation, not a claim that nature uses a radial law.
        combination_generated: list[Mapping[str, Any]] = []
        combo_budget = int(request.get("combination_materialization_budget", 48))
        combo_budget = max(0, combo_budget)
        combination_candidates = [row for row in combination_regions if row["axis_order"] >= 2][:combo_budget]
        axis_index = {axis.axis_id: j for j, axis in enumerate(ds.axes)}
        train_indices = np.where(train)[0]
        abs_train_residual = np.abs(residual[train])
        if abs_train_residual.size:
            cutoff = float(np.quantile(abs_train_residual, 0.80))
            high_local = abs_train_residual >= cutoff
        else:
            high_local = np.zeros(0, dtype=bool)
        for meta in combination_candidates:
            idx = [axis_index[a] for a in meta["axes"]]
            R = Z[:, idx]
            high_rows = train_indices[high_local] if np.count_nonzero(high_local) >= 2 else train_indices
            weights = np.abs(residual[high_rows]) + 1e-12
            center = np.average(R[high_rows], axis=0, weights=weights)
            d2 = np.mean((R - center) ** 2, axis=1)
            train_high_d2 = d2[high_rows]
            radius2 = max(float(np.median(train_high_d2)) if train_high_d2.size else 1.0, 1e-6)
            trials = []
            for rf in (0.5, 0.75, 1.0, 1.5, 2.0):
                rr2 = radius2 * rf * rf
                g = np.exp(-0.5 * d2 / rr2)
                A = np.column_stack([B, g])
                coef = self._ridge_fit(A[train], y[train])
                pred = A @ coef
                trials.append((self._rmse(y[train], pred[train]), rf, pred))
            _, radius_factor, predc = min(trials, key=lambda row: row[0])
            ood_rmsec = self._rmse(y[ood], predc[ood])
            train_rmsec = self._rmse(y[train], predc[train])
            robust = float(np.mean([
                self._rmse(y[ood], trial_pred[ood]) < ood_rmse0
                for _, _, trial_pred in trials
            ]))
            improvement = float((ood_rmse0 - ood_rmsec) / ood_rmse0) if ood_rmse0 > 0 else 0.0
            supported = sigma_measured is not None and improvement > 0 and robust >= 0.6
            promising = improvement > 0 and robust >= 0.6
            promotion_status = (
                "COMBINATION_BIRTH_OOD_VALIDATED" if supported
                else "COMBINATION_BIRTH_PROMISING_EXPLORATORY" if promising
                else "COMBINATION_BIRTH_NOT_PROMOTED"
            )
            combination_generated.append({
                **meta,
                "combination_id": "generated_joint_localization__" + "__".join(meta["axes"]),
                "generated_coordinate": "exp(-0.5*mean((z-center)^2)/radius2)",
                "center_standardized_train_only": [float(v) for v in np.asarray(center).ravel()],
                "radius2_train_only": float(radius2 * radius_factor * radius_factor),
                "train_rmse_baseline": train_rmse0,
                "train_rmse_augmented": train_rmsec,
                "ood_rmse_baseline": ood_rmse0,
                "ood_rmse_augmented": ood_rmsec,
                "ood_rmse_fractional_improvement": improvement,
                "local_radius_robust_fraction": robust,
                "promotion_status": promotion_status,
                "research_status": "POTENTIAL_LAW_OR_MECHANISM_CANDIDATE",
                "epistemic_status": "OOD_SUPPORTED_CANDIDATE" if supported else "UNVERIFIED_CANDIDATE",
                "unknown_is_false": False,
                "canonical_axis_registration_allowed_directly": False,
                "claim_boundary": "Joint residual carrier is a representation candidate; physical semantics require owner/bridge/ontology resolution and scientific promotion.",
            })
        combination_generated.sort(key=lambda r: (r["ood_rmse_augmented"], -r["local_radius_robust_fraction"], r["combination_id"]))
        best_combination = combination_generated[0] if combination_generated else None

        generated.sort(key=lambda r: (r["ood_rmse_augmented"], -r["local_multiscale_robust_fraction"], r["axis_id"]))
        best_axis = generated[0] if generated else None

        semantic_admission = None
        if best_axis is not None and best_axis["status"] != "AXIS_BIRTH_REJECTED":
            source = next(a for a in ds.axes if a.axis_id == best_axis["source_axis_id"])
            proposal = DynamicAxisProposal(
                proposal_id=f"AXIS-MODELING-{ds.dataset_id}-{best_axis['source_axis_id']}",
                domain_id=source.domain,
                axis_id=str(best_axis["axis_id"]),
                description_ru=f"Сгенерированная координата локализации устойчивого residual по оси {source.axis_id}",
                value_kind="CONTINUOUS_RANGE",
                physical_or_information_meaning="Data-derived proximity coordinate to a residual-localized regime; physical mechanism remains unresolved until an independent owner identifies it.",
                measurement_protocol=f"Compute from measured {source.axis_id} using center/width frozen on training regimes only.",
                units_or_normalization="dimensionless",
                expected_range={"minimum": 0.0, "maximum": 1.0},
                falsifiable_advantage="Must improve regime-level OOD prediction after complexity penalty and survive local center/width perturbations.",
                redundancy_test="Compare against canonical axes and reject if an existing axis already encodes the same residual-localized coordinate.",
                provenance_evidence=(ds.provenance,),
            )
            semantic_admission = DynamicAxisAdmissionOwner().assess(proposal)

        single_structure = bool(best_axis and best_axis["status"] != "AXIS_BIRTH_REJECTED")
        combination_structure = bool(best_combination and best_combination["promotion_status"] != "COMBINATION_BIRTH_NOT_PROMOTED")
        any_research_candidate = bool(generated or combination_generated or hypervoid_regions)
        scientific_status = (
            "STRUCTURE_FOUND_PROMOTION_BLOCKED" if (single_structure or combination_structure)
            else "CANDIDATES_RETAINED_NOT_PROMOTED" if any_research_candidate
            else "NO_RESEARCH_CANDIDATE_MATERIALIZED"
        )
        if sigma_measured is not None and (
            (best_axis and best_axis["status"] == "AXIS_BIRTH_OOD_VALIDATED")
            or (best_combination and best_combination["promotion_status"] == "COMBINATION_BIRTH_OOD_VALIDATED")
        ):
            scientific_status = "STRUCTURE_FOUND_READY_FOR_PROMOTION_CORE_NOT_PROMOTED"

        result = {
            "schema": SCHEMA,
            "owner": OWNER_ID,
            "dataset": {
                "dataset_id": ds.dataset_id,
                "observable_id": ds.observable_id,
                "observable_units": ds.observable_units,
                "n_observations": len(ds.y),
                "axis_ids": axis_ids,
                "axis_domains": {a.axis_id: a.domain for a in ds.axes},
                "axis_owner_ids": {a.axis_id: (a.owner_id or "UNSPECIFIED_OR_SHARED") for a in ds.axes},
                "regimes": sorted(set(ds.regime_ids)),
                "ood_regimes": sorted(ood_regimes),
                "measurement_uncertainty_declared": sigma_measured is not None,
                "provenance": ds.provenance,
                "train_axis_summary": {
                    axis.axis_id: {
                        "minimum": float(np.min(X[train, idx])),
                        "maximum": float(np.max(X[train, idx])),
                        "median": float(np.median(X[train, idx])),
                        "unique_count": int(len(np.unique(X[train, idx]))),
                        "unique_values_if_small": [float(v) for v in np.unique(X[train, idx])] if len(np.unique(X[train, idx])) <= 6 else None,
                    }
                    for idx, axis in enumerate(ds.axes)
                },
                "freeze_split": {
                    "fit_regimes": sorted(set(str(r) for r in regimes[train])),
                    "validation_regimes": sorted(ood_regimes),
                    "fit_count": int(np.count_nonzero(train)),
                    "validation_count": int(np.count_nonzero(ood)),
                },
            },
            "seed": seed,
            "modes": {
                "RANDOM": {"status": "EXECUTED", "regions": combination_regions[:12], "search_order_ceiling": None},
                "HYPERVOID": {"status": "EXECUTED", "regions": hypervoid_regions},
                "VOID_FRONTIER": {
                    "status": "EXECUTED",
                    "regions": hypervoid_regions,
                    "void_is_proof_of_physical_absence": False,
                    "voids_are_priority_research_targets": True,
                },
                "BOUNDARY": {"status": "EXECUTED", "rows_by_axis": boundary_rows},
                "EXTREME": {"status": "EXECUTED", "row_indices": extreme_rows},
                "CROSSDOMAIN": crossdomain,
                "UNCERTAINTY": uncertainty_mode,
                "AXIS_BIRTH": {"status": "EXECUTED", "candidates": generated},
                "COMBINATION_BIRTH": {
                    "status": "EXECUTED",
                    "materialization_budget": combo_budget,
                    "materialized_candidates": combination_generated,
                    "search_order_ceiling": None,
                    "owner_or_domain_affiliation_blocks_combination": False,
                },
            },
            "baseline": {
                "model_class": "LOW_CAPACITY_POLYNOMIAL_INTERACTION_BASELINE",
                "train_rmse": train_rmse0,
                "ood_rmse": ood_rmse0,
                "exploratory_residual_scale_not_measurement_uncertainty": None if sigma_measured is not None else exploratory_sigma,
            },
            "best_axis_birth": best_axis,
            "best_combination_birth": best_combination,
            "semantic_axis_admission": semantic_admission,
            "combination_semantic_admission": {
                "status": "RESEARCH_LOCAL_COMPOSITE_COORDINATE_REQUIRES_TYPED_OWNER_RESOLUTION" if best_combination else "NO_COMBINATION_MATERIALIZED",
                "canonical_registry_mutated": False,
                "single_domain_owner_required_for_exploration": False,
            },
            "exploration_promotion_split": {
                "exploration_space_restricted_by_candidate_registry": False,
                "exploration_space_restricted_by_owner_affiliation": False,
                "exploration_space_restricted_by_domain_affiliation": False,
                "exploration_axis_order_ceiling": None,
                "promotion_remains_strict": True,
                "high_dimensionality_changes_confidence_not_search_rights": True,
            },
            "final_status": scientific_status,
            "promotion_allowed": False,
            "claim_boundary": {
                "axis_modeling_found_structure": single_structure or combination_structure,
                "research_candidates_retained": any_research_candidate,
                "unknown_candidate_is_false": False,
                "void_region_is_physical_absence": False,
                "new_physical_axis_established": False,
                "new_law_established": False,
                "canonical_registry_mutated": False,
                "reason": "AXIS-MODELING exploration retains potential mechanisms and void/frontier candidates. ScientificPromotionCore alone may promote; failed or incomplete promotion evidence does not make an unknown real-world candidate false.",
            },
        }
        result["digest"] = digest_payload(result)
        return result
