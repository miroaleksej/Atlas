"""Adaptive evidence triage, exploration sandbox and hypothesis council.

This module is deliberately *not* a scientific promotion owner.  It sits in
front of / beside :mod:`scientific_promotion` and may rank, preserve and route
weak evidence, but it can never mark any U0..U10 gate as passed.

Authoritative promotion remains owned by SCIENTIFIC-PROMOTION-CORE.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

OWNER_ID = "RESEARCH-TRIAGE-SANDBOX"
OWNER_VERSION = "1.0.0"
SCHEMA = "phi-research-triage-sandbox/v1"
COUNCIL_SCHEMA = "phi-hypothesis-council/v1"

DEFAULT_DPI_WEIGHTS = {
    "fit": 0.35,
    "simplicity": 0.20,
    "cross_consistency": 0.30,
    "fwer_penalty": 0.15,
}

QUALITY_TIERS = {
    "STRICT": {
        "rho_star": 0.05,
        "sigma_star": 0.05,
        "epistemic_status": "STRICT_EVIDENCE_CANDIDATE",
        "canonical_promotion_allowed": True,
        "strict_pipeline_ceiling": "U10_IF_ALL_AUTHORITATIVE_GATES_PASS",
    },
    "EMPIRICAL": {
        "rho_star": 0.15,
        "sigma_star": 0.10,
        "epistemic_status": "PHENOMENOLOGICAL_MODEL",
        "canonical_promotion_allowed": False,
        "strict_pipeline_ceiling": "U5_EVIDENCE_ONLY_NO_LAW_PROMOTION",
    },
    "EXPLORATORY": {
        "rho_star": 0.30,
        "sigma_star": None,
        "epistemic_status": "STRUCTURAL_ANOMALY",
        "canonical_promotion_allowed": False,
        "strict_pipeline_ceiling": "U3_SANDBOX_ONLY_BLOCK_U4",
    },
}


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=float)


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _clip01(value: float) -> float:
    return float(min(1.0, max(0.0, float(value))))


def _robust_scale(y: np.ndarray) -> float:
    y = np.asarray(y, float)
    if y.size < 2:
        return max(abs(float(y[0])) if y.size else 0.0, 1.0)
    q25, q75 = np.quantile(y, [0.25, 0.75])
    iqr_sigma = float((q75 - q25) / 1.349) if q75 > q25 else 0.0
    std = float(np.std(y))
    med = abs(float(np.median(y)))
    return max(iqr_sigma, std, med, 1e-12)


@dataclass(frozen=True)
class DataQualityAssessment:
    n_points: int
    relative_uncertainty: float
    information_density: float
    quality_tag: str
    rho_star: float
    sigma_star: float | None
    epistemic_status: str
    canonical_promotion_allowed: bool
    strict_pipeline_ceiling: str
    reason: str

    def as_dict(self) -> Mapping[str, Any]:
        return {
            "n_points": self.n_points,
            "relative_uncertainty": self.relative_uncertainty,
            "information_density": self.information_density,
            "quality_tag": self.quality_tag,
            "rho_star": self.rho_star,
            "sigma_star": self.sigma_star,
            "epistemic_status": self.epistemic_status,
            "canonical_promotion_allowed": self.canonical_promotion_allowed,
            "strict_pipeline_ceiling": self.strict_pipeline_ceiling,
            "reason": self.reason,
        }


class ResearchTriageSandbox:
    """Non-authoritative evidence triage and human-review support."""

    @staticmethod
    def contract() -> Mapping[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "role": "RANK_ROUTE_PRESERVE_AND_REQUEST_EVIDENCE_ONLY",
            "authoritative_scientific_promotion_owner": "SCIENTIFIC-PROMOTION-CORE",
            "quality_tiers": QUALITY_TIERS,
            "dpi_formula": "normalized(W_fit*(1-rho_adj) + W_simplicity*S + W_cross*C - W_fwer*P_fwer)",
            "default_dpi_weights": DEFAULT_DPI_WEIGHTS,
            "manual_override_can_pass_u_gate": False,
            "sandbox_dimension_exception_can_pass_u2": False,
            "expert_weight_learning_scope": "SANDBOX_RANKING_ONLY",
            "mutable_council_state_inside_sealed_tree": False,
        }
        return {**payload, "digest": _digest(payload)}

    @staticmethod
    def assess_data_quality(
        *,
        y: Sequence[float] | None = None,
        sigma: Sequence[float] | None = None,
        n_points: int | None = None,
        relative_uncertainty: float | None = None,
        domain: str = "UNSPECIFIED",
    ) -> Mapping[str, Any]:
        if y is not None:
            yy = np.asarray(tuple(float(v) for v in y), float)
            if yy.size == 0 or np.any(~np.isfinite(yy)):
                raise ValueError("y must contain finite observations")
            n = int(yy.size)
        else:
            yy = np.asarray([], float)
            n = int(n_points or 0)
        if n < 1:
            raise ValueError("at least one observation is required")

        if relative_uncertainty is not None:
            rel = float(relative_uncertainty)
            uncertainty_source = "DECLARED_RELATIVE_UNCERTAINTY"
        elif sigma is not None:
            ss = np.asarray(tuple(float(v) for v in sigma), float)
            if ss.size != n or np.any(~np.isfinite(ss)) or np.any(ss < 0):
                raise ValueError("sigma must be finite, non-negative and match observations")
            scale = _robust_scale(yy) if yy.size else max(float(np.median(ss)), 1e-12)
            rel = float(np.median(ss) / scale)
            uncertainty_source = "MEDIAN_SIGMA_OVER_ROBUST_SIGNAL_SCALE"
        else:
            # Missing uncertainty is itself weak evidence; it must never select STRICT.
            rel = 1.0
            uncertainty_source = "UNCERTAINTY_UNDECLARED_ASSIGNED_EXPLORATORY"
        if not math.isfinite(rel) or rel < 0:
            raise ValueError("relative uncertainty must be finite and non-negative")

        # Information density is an ordering diagnostic, not a promotion score.
        # It grows sub-linearly with sample size and is attenuated by uncertainty.
        sample_density = min(1.0, math.log1p(n) / math.log1p(1000.0))
        uncertainty_quality = 1.0 / (1.0 + 10.0 * rel)
        info_density = float(sample_density * uncertainty_quality)

        if n > 1000 and rel < 0.01:
            tag = "STRICT"
            reason = "n>1000 and relative uncertainty<1%"
        elif n < 30 or rel > 0.10:
            tag = "EXPLORATORY"
            reason = "n<30 or relative uncertainty>10%"
        else:
            tag = "EMPIRICAL"
            reason = "intermediate evidence density: retained as phenomenological evidence"
        tier = QUALITY_TIERS[tag]
        assessment = DataQualityAssessment(
            n_points=n,
            relative_uncertainty=rel,
            information_density=info_density,
            quality_tag=tag,
            rho_star=float(tier["rho_star"]),
            sigma_star=None if tier["sigma_star"] is None else float(tier["sigma_star"]),
            epistemic_status=str(tier["epistemic_status"]),
            canonical_promotion_allowed=bool(tier["canonical_promotion_allowed"]),
            strict_pipeline_ceiling=str(tier["strict_pipeline_ceiling"]),
            reason=reason,
        )
        payload = {
            "schema": "phi-data-quality-tier/v1",
            "owner_id": OWNER_ID,
            "domain": str(domain),
            "uncertainty_source": uncertainty_source,
            **assessment.as_dict(),
            "quality_tag_is_scientific_truth": False,
        }
        return {**payload, "digest": _digest(payload)}

    @staticmethod
    def _validate_weights(weights: Mapping[str, float] | None) -> Mapping[str, float]:
        raw = dict(DEFAULT_DPI_WEIGHTS if weights is None else weights)
        required = set(DEFAULT_DPI_WEIGHTS)
        if set(raw) != required:
            raise ValueError(f"DPI weights must contain exactly {sorted(required)}")
        vals = {k: float(raw[k]) for k in required}
        if any((not math.isfinite(v) or v < 0.0) for v in vals.values()) or sum(vals.values()) <= 0.0:
            raise ValueError("DPI weights must be finite non-negative and not all zero")
        total = sum(vals.values())
        return {k: vals[k] / total for k in sorted(vals)}

    @classmethod
    def score_hypothesis(cls, hypothesis: Mapping[str, Any], *, weights: Mapping[str, float] | None = None) -> Mapping[str, Any]:
        w = cls._validate_weights(weights)
        rho = _clip01(float(hypothesis.get("rho_adj", 1.0)))
        simplicity = _clip01(float(hypothesis.get("simplicity_score", 0.0)))
        cross = _clip01(float(hypothesis.get("cross_consistency", 0.0)))
        fwer_p = _clip01(float(hypothesis.get("familywise_p", 1.0)))
        alpha = float(hypothesis.get("familywise_alpha", 0.05))
        if not (0.0 < alpha <= 1.0):
            raise ValueError("familywise_alpha must be in (0,1]")
        # Low p is good evidence, high p receives the full penalty.
        fwer_penalty = _clip01(fwer_p / alpha)
        numerator = (
            w["fit"] * (1.0 - rho)
            + w["simplicity"] * simplicity
            + w["cross_consistency"] * cross
            - w["fwer_penalty"] * fwer_penalty
        )
        positive_mass = w["fit"] + w["simplicity"] + w["cross_consistency"]
        dpi = _clip01(numerator / max(positive_mass, 1e-12))
        uniqueness = hypothesis.get("uniqueness_score")
        landscape = {
            "accuracy": 1.0 - rho,
            "simplicity": simplicity,
            "uniqueness": None if uniqueness is None else _clip01(float(uniqueness)),
        }
        payload = {
            "candidate_id": str(hypothesis.get("candidate_id", "UNIDENTIFIED")),
            "equation": str(hypothesis.get("equation", "")),
            "rho_adj": rho,
            "simplicity_score": simplicity,
            "cross_consistency": cross,
            "familywise_p": fwer_p,
            "fwer_penalty": fwer_penalty,
            "weights": w,
            "dpi": dpi,
            "landscape_coordinates": landscape,
            "promising_reject": bool(dpi >= float(hypothesis.get("dpi_threshold", 0.70))),
            "dpi_can_promote_scientific_status": False,
        }
        return {**payload, "digest": _digest(payload)}

    @classmethod
    def rank_hypotheses(
        cls, hypotheses: Sequence[Mapping[str, Any]], *, weights: Mapping[str, float] | None = None,
        dpi_threshold: float = 0.70,
    ) -> Mapping[str, Any]:
        if not (0.0 <= float(dpi_threshold) <= 1.0):
            raise ValueError("dpi_threshold must be in [0,1]")
        rows = []
        for hypothesis in hypotheses:
            row = dict(hypothesis)
            row["dpi_threshold"] = float(dpi_threshold)
            rows.append(dict(cls.score_hypothesis(row, weights=weights)))
        rows.sort(key=lambda r: (-float(r["dpi"]), str(r["candidate_id"])))
        payload = {
            "schema": "phi-exploration-sandbox-ranking/v1",
            "owner_id": OWNER_ID,
            "ranked": rows,
            "candidate_count": len(rows),
            "promising_reject_count": sum(bool(r["promising_reject"]) for r in rows),
            "ranking_is_promotion": False,
            "strict_u_gates_modified": False,
        }
        return {**payload, "digest": _digest(payload)}

    @staticmethod
    def propose_what_if_experiments(
        *, axis_summaries: Sequence[Mapping[str, Any]], count: int = 2,
    ) -> Mapping[str, Any]:
        count = int(count)
        if count < 1:
            raise ValueError("count must be positive")
        candidates = []
        for axis in axis_summaries:
            axis_id = str(axis.get("axis_id", "")).strip()
            if not axis_id:
                continue
            obs_lo = float(axis.get("observed_min")); obs_hi = float(axis.get("observed_max"))
            tgt_lo = float(axis.get("target_min", obs_lo)); tgt_hi = float(axis.get("target_max", obs_hi))
            sensitivity = max(0.0, float(axis.get("sensitivity", 1.0)))
            uncertainty = max(0.0, float(axis.get("relative_uncertainty", 0.0)))
            span = max(abs(obs_hi - obs_lo), 1e-12)
            left_gap = max(0.0, obs_lo - tgt_lo) / span
            right_gap = max(0.0, tgt_hi - obs_hi) / span
            for side, gap, value_range in (
                ("LOW", left_gap, (tgt_lo, obs_lo)),
                ("HIGH", right_gap, (obs_hi, tgt_hi)),
            ):
                if gap <= 0:
                    continue
                score = gap * (1.0 + sensitivity) * (1.0 + uncertainty)
                candidates.append({
                    "axis_id": axis_id,
                    "side": side,
                    "requested_range": [float(value_range[0]), float(value_range[1])],
                    "priority": float(score),
                    "reason": "coverage gap weighted by sensitivity and uncertainty",
                })
        candidates.sort(key=lambda r: (-r["priority"], r["axis_id"], r["side"]))
        selected = candidates[:count]
        status = "EXPERIMENT_GAPS_IDENTIFIED" if selected else "NO_DECLARED_COVERAGE_GAP"
        payload = {
            "schema": "phi-sandbox-what-if-experiment-plan/v1",
            "owner_id": OWNER_ID,
            "status": status,
            "requested_experiment_count": count,
            "experiments": selected,
            "world_result_observed": False,
            "proposal_is_evidence": False,
        }
        return {**payload, "digest": _digest(payload)}

    @classmethod
    def build_passport(
        cls, *, hypothesis: Mapping[str, Any], quality: Mapping[str, Any],
        weights: Mapping[str, float] | None = None, axis_summaries: Sequence[Mapping[str, Any]] = (),
    ) -> Mapping[str, Any]:
        scored = dict(cls.score_hypothesis(hypothesis, weights=weights))
        qtag = str(quality.get("quality_tag", ""))
        if qtag not in QUALITY_TIERS:
            raise ValueError("quality assessment with a known quality_tag is required")
        what_if = cls.propose_what_if_experiments(axis_summaries=axis_summaries, count=2) if axis_summaries else None
        if qtag == "STRICT":
            route = "STRICT_PIPELINE_ELIGIBLE_SUBJECT_TO_ALL_U_GATES"
        elif qtag == "EMPIRICAL":
            route = "PHENOMENOLOGICAL_PASSPORT_AND_META_ANALYSIS"
        else:
            route = "STRUCTURAL_ANOMALY_SANDBOX_BLOCK_BEFORE_U4"
        payload = {
            "schema": "phi-hypothesis-passport/v1",
            "owner_id": OWNER_ID,
            "candidate_id": scored["candidate_id"],
            "equation": scored["equation"],
            "quality_tag": qtag,
            "epistemic_status": quality.get("epistemic_status"),
            "strict_pipeline_ceiling": quality.get("strict_pipeline_ceiling"),
            "canonical_promotion_allowed_by_quality": bool(quality.get("canonical_promotion_allowed")),
            "dpi": scored["dpi"],
            "promising_reject": scored["promising_reject"],
            "landscape_coordinates": scored["landscape_coordinates"],
            "route": route,
            "what_if": what_if,
            "manual_override_can_change_route_for_review": True,
            "manual_override_can_pass_u_gate": False,
        }
        return {**payload, "digest": _digest(payload)}

    @staticmethod
    def load_council_state(path: Path) -> Mapping[str, Any]:
        if not path.is_file():
            return {"schema": COUNCIL_SCHEMA, "actions": [], "sandbox_weights": dict(DEFAULT_DPI_WEIGHTS), "revision": 0}
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, Mapping) or raw.get("schema") != COUNCIL_SCHEMA:
            raise ValueError("invalid hypothesis council state")
        return raw

    @staticmethod
    def write_council_state(path: Path, state: Mapping[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = dict(state)
        payload["digest"] = _digest({k: v for k, v in payload.items() if k != "digest"})
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(path)

    @classmethod
    def record_council_action(
        cls, *, state: Mapping[str, Any], candidate_id: str, action: str, reason: str,
        expert_id: str = "LOCAL_EXPERT", linked_candidate_ids: Sequence[str] = (),
        feature_snapshot: Mapping[str, float] | None = None,
    ) -> Mapping[str, Any]:
        allowed = {"NOTE", "SPONSOR_REVIEW", "REJECT", "FRESH_IDEA_LINK", "REQUEST_SANDBOX_DIMENSION_EXCEPTION"}
        action = str(action).strip().upper()
        if action not in allowed:
            raise ValueError(f"unsupported council action: {action}")
        if not str(candidate_id).strip() or not str(reason).strip():
            raise ValueError("candidate_id and reason are required")
        actions = list(state.get("actions", ()))
        row = {
            "sequence": len(actions) + 1,
            "candidate_id": str(candidate_id),
            "action": action,
            "reason": str(reason),
            "expert_id": str(expert_id),
            "linked_candidate_ids": [str(x) for x in linked_candidate_ids],
            "feature_snapshot": dict(feature_snapshot or {}),
            "authoritative_u_gate_override": False,
            "effect": {
                "SPONSOR_REVIEW": "RETURN_TO_EVIDENCE_ACQUISITION_NOT_U6_PASS",
                "REQUEST_SANDBOX_DIMENSION_EXCEPTION": "SANDBOX_ONLY_U2_REMAINS_CLOSED",
                "FRESH_IDEA_LINK": "NEW_SEARCH_SEED_ONLY_NO_PROMOTION",
                "REJECT": "ARCHIVE_FROM_SANDBOX_WITH_REASON",
                "NOTE": "ANNOTATION_ONLY",
            }[action],
        }
        row["digest"] = _digest(row)
        actions.append(row)
        out = dict(state)
        out.update({"schema": COUNCIL_SCHEMA, "actions": actions, "revision": int(state.get("revision", 0)) + 1})
        out["digest"] = _digest({k: v for k, v in out.items() if k != "digest"})
        return out

    @classmethod
    def recommend_sandbox_weights_from_council(cls, state: Mapping[str, Any], *, learning_rate: float = 0.25) -> Mapping[str, Any]:
        actions = list(state.get("actions", ()))
        labeled = [a for a in actions if a.get("action") in {"SPONSOR_REVIEW", "REJECT"} and isinstance(a.get("feature_snapshot"), Mapping)]
        current = cls._validate_weights(state.get("sandbox_weights") or DEFAULT_DPI_WEIGHTS)
        if len(labeled) < 8:
            return {"status": "INSUFFICIENT_COUNCIL_DECISIONS", "minimum": 8, "observed": len(labeled), "weights": current, "auto_applied": False}
        feature_keys = ("fit", "simplicity", "cross_consistency", "fwer_penalty")
        X=[]; yy=[]
        for row in labeled:
            snap=row["feature_snapshot"]
            if all(k in snap and math.isfinite(float(snap[k])) for k in feature_keys):
                X.append([float(snap[k]) for k in feature_keys]); yy.append(1.0 if row["action"]=="SPONSOR_REVIEW" else 0.0)
        if len(X)<8:
            return {"status":"INSUFFICIENT_VALID_FEATURE_SNAPSHOTS","minimum":8,"observed":len(X),"weights":current,"auto_applied":False}
        X=np.asarray(X,float); yy=np.asarray(yy,float)
        centered_y=yy-np.mean(yy); scores=[]
        for j,k in enumerate(feature_keys):
            x=X[:,j]-np.mean(X[:,j]); denom=float(np.linalg.norm(x)*np.linalg.norm(centered_y))
            corr=float(np.dot(x,centered_y)/denom) if denom>1e-12 else 0.0
            # fwer_penalty is a cost: expert preference for larger penalty should reduce its penalty weight.
            direction = -corr if k=="fwer_penalty" else corr
            scores.append(direction)
        raw={k: max(1e-6,current[k]*math.exp(float(learning_rate)*scores[i])) for i,k in enumerate(feature_keys)}
        total=sum(raw.values()); recommended={k:raw[k]/total for k in sorted(raw)}
        return {"status":"SANDBOX_WEIGHT_RECOMMENDATION_READY","weights_before":current,"weights_recommended":recommended,
                "labeled_decisions":len(X),"auto_applied":False,"strict_promotion_weights_changed":False}
