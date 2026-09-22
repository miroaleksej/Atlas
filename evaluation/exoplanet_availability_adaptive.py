from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from evaluation.exoplanet_nasa2026_blind_experiment import (
    AU_M, DAY_S, M_SUN_KG, DORMANT_AXES, REQUIRED_COLUMNS,
    add_base_columns, candidate_vectors, closure_score, h64, host_split,
    registry_matches, safe_relerr, sha256_file, source_table_kind,
)
from source.lawspace.schema import digest_payload
from source.lawspace.theory_compiler import HierarchicalObservationalTheoryOwner
from source.lawspace.long_horizon_scientific_cycle import LongHorizonBlindScientificCycleKernel

def _positive_numeric(df: pd.DataFrame, name: str) -> pd.Series:
    x = pd.to_numeric(df[name], errors="coerce")
    return x.where(np.isfinite(x) & (x > 0))


def _finite_numeric(df: pd.DataFrame, name: str) -> pd.Series:
    x = pd.to_numeric(df[name], errors="coerce")
    return x.where(np.isfinite(x))


def _central_numeric(df: pd.DataFrame, name: str, *, positive: bool = False) -> pd.Series:
    """Return finite central values only; Archive limit values are not point observations."""
    x = pd.to_numeric(df[name], errors="coerce")
    valid = np.isfinite(x)
    lim_name = f"{name}lim"
    if lim_name in df.columns:
        lim = pd.to_numeric(df[lim_name], errors="coerce")
        # NASA limit columns: 0 = central measurement, +/-1 = upper/lower limit.
        valid &= lim.isna() | (lim == 0)
    if positive:
        valid &= x > 0
    return x.where(valid)


def _limit_flag(df: pd.DataFrame, name: str) -> pd.Series:
    lim_name = f"{name}lim"
    if lim_name not in df.columns:
        return pd.Series(0.0, index=df.index, dtype=float)
    return pd.to_numeric(df[lim_name], errors="coerce").fillna(0.0)


def _constraint_interval(
    df: pd.DataFrame,
    name: str,
    *,
    positive: bool = False,
    true_mass_from_best_mass: bool = False,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Return observational constraints instead of deleting censored values.

    The 2026 PS/PSCompPars snapshot uses +1 for an upper bound and -1 for a
    lower bound (cross-checked against published Archive solutions such as
    K2-137 b and HD 219134 d).  Point measurements become uncertainty
    intervals.  When ``true_mass_from_best_mass`` is requested, an uncensored
    ``M*sin(i)`` value is a lower bound on the true mass rather than an exact
    mass.  Infinite bounds are deliberate: they preserve what the observation
    actually says without inventing a prior.
    """
    x = pd.to_numeric(df[name], errors="coerce")
    e1 = pd.to_numeric(df[name + "err1"], errors="coerce") if name + "err1" in df.columns else pd.Series(np.nan, index=df.index)
    e2 = pd.to_numeric(df[name + "err2"], errors="coerce") if name + "err2" in df.columns else pd.Series(np.nan, index=df.index)
    lim = _limit_flag(df, name)
    lo = pd.Series(np.nan, index=df.index, dtype=float)
    hi = pd.Series(np.nan, index=df.index, dtype=float)
    finite = x.notna() & np.isfinite(x)

    point = finite & (lim == 0)
    point_lo = (x + e2).where(e2.notna(), x)
    point_hi = (x + e1).where(e1.notna(), x)
    lo.loc[point] = point_lo.loc[point]
    hi.loc[point] = point_hi.loc[point]

    # Snapshot semantics: +1 is an upper bound, -1 is a lower bound.
    upper = finite & (lim > 0)
    lower = finite & (lim < 0)
    lo.loc[upper] = 0.0 if positive else -math.inf
    hi.loc[upper] = x.loc[upper]
    lo.loc[lower] = x.loc[lower]
    hi.loc[lower] = math.inf

    if true_mass_from_best_mass and name == "pl_bmasse" and "pl_bmassprov" in df.columns:
        provenance = df["pl_bmassprov"].fillna("").astype(str).str.lower()
        msini = point & provenance.str.contains(r"msini|m\*sini|m\s*\*?\s*sin", regex=True)
        lo.loc[msini] = point_lo.loc[msini]
        hi.loc[msini] = math.inf

    if positive:
        lo = lo.clip(lower=0.0)
        hi = hi.where((hi > 0) | np.isinf(hi))
    swap = lo.notna() & hi.notna() & (lo > hi)
    if bool(swap.any()):
        tmp = lo.loc[swap].copy()
        lo.loc[swap] = hi.loc[swap]
        hi.loc[swap] = tmp
    return lo, hi, lim


def _interval_overlap(lo1: pd.Series, hi1: pd.Series, lo2: pd.Series, hi2: pd.Series) -> pd.Series:
    valid = lo1.notna() & hi1.notna() & lo2.notna() & hi2.notna()
    out = pd.Series(False, index=lo1.index, dtype=bool)
    out.loc[valid] = np.maximum(lo1.loc[valid].astype(float), lo2.loc[valid].astype(float)) <= np.minimum(hi1.loc[valid].astype(float), hi2.loc[valid].astype(float))
    return out


def _robust_positive_bounds(values: pd.Series, *, sigma_multiple: float = 3.0) -> tuple[float, float]:
    x = pd.to_numeric(values, errors="coerce")
    valid = np.isfinite(x.to_numpy(float)) & (x.to_numpy(float) > 0)
    if int(valid.sum()) < 20:
        return math.nan, math.nan
    logs = np.log(x.to_numpy(float)[valid])
    med = float(np.median(logs))
    mad = float(np.median(np.abs(logs - med)))
    sigma = 1.4826 * mad
    return float(math.exp(med - sigma_multiple * sigma)), float(math.exp(med + sigma_multiple * sigma))


def _safe_log_positive(series: pd.Series) -> pd.Series:
    x = pd.to_numeric(series, errors="coerce")
    out = pd.Series(np.nan, index=x.index, dtype=float)
    mask = np.isfinite(x.to_numpy(float)) & (x.to_numpy(float) > 0)
    out.loc[mask] = np.log(x.loc[mask].astype(float))
    return out


def _robust_log_outlier(values: pd.Series, *, sigma_multiple: float = 6.0) -> tuple[pd.Series, dict[str, float]]:
    """Flag extreme positive values without imposing a hand-picked physical threshold."""
    x = pd.to_numeric(values, errors="coerce")
    valid = np.isfinite(x.to_numpy(float)) & (x.to_numpy(float) > 0)
    flags = pd.Series(False, index=values.index)
    if int(valid.sum()) < 20:
        return flags, {"count": int(valid.sum()), "median_log": math.nan, "robust_sigma_log": math.nan, "lower": math.nan, "upper": math.nan}
    logs = np.log(x.to_numpy(float)[valid])
    med = float(np.median(logs))
    mad = float(np.median(np.abs(logs - med)))
    robust_sigma = 1.4826 * mad
    lo = med - sigma_multiple * robust_sigma
    hi = med + sigma_multiple * robust_sigma
    idx = values.index[valid]
    flags.loc[idx] = (logs < lo) | (logs > hi)
    return flags, {
        "count": int(valid.sum()),
        "median_log": med,
        "robust_sigma_log": robust_sigma,
        "lower": float(math.exp(lo)),
        "upper": float(math.exp(hi)),
        "sigma_multiple": float(sigma_multiple),
    }



def _availability_axis_stability(
    target: pd.Series,
    axis: pd.Series,
    groups: pd.Series,
    *,
    axis_name: str,
    repeats: int = 20,
    folds: int = 4,
) -> dict[str, Any]:
    valid = np.isfinite(pd.to_numeric(target, errors="coerce")) & np.isfinite(pd.to_numeric(axis, errors="coerce")) & groups.notna()
    y_all = pd.to_numeric(target.loc[valid], errors="coerce").astype(float)
    x_all = pd.to_numeric(axis.loc[valid], errors="coerce").astype(float)
    g_all = groups.loc[valid].astype(str)
    fold_gains: list[float] = []
    repeat_rows: list[dict[str, Any]] = []

    def _nrmse(y: np.ndarray, pred: np.ndarray) -> float:
        den = float(np.std(y))
        return float(np.sqrt(np.mean(np.square(y - pred))) / den) if den > 1e-14 else math.inf

    for rep in range(repeats):
        gains: list[float] = []
        for fold in range(folds):
            salt = f"AVAIL-{axis_name}-R{rep:02d}"
            test_mask = np.asarray([h64(f"{salt}::{g}") % folds == fold for g in g_all], dtype=bool)
            if int(test_mask.sum()) < 20 or int((~test_mask).sum()) < 100:
                continue
            ytr = y_all.to_numpy(float)[~test_mask]
            yte = y_all.to_numpy(float)[test_mask]
            xtr = x_all.to_numpy(float)[~test_mask]
            xte = x_all.to_numpy(float)[test_mask]
            beta, *_ = np.linalg.lstsq(np.column_stack([np.ones(len(xtr)), xtr]), ytr, rcond=None)
            base_pred = np.full(len(yte), float(np.mean(ytr)))
            cand_pred = float(beta[0]) + float(beta[1]) * xte
            base = _nrmse(yte, base_pred)
            cand = _nrmse(yte, cand_pred)
            gain = (base - cand) / max(abs(base), 1e-30)
            gains.append(float(gain))
            fold_gains.append(float(gain))
        if gains:
            arr = np.asarray(gains, float)
            med = float(np.median(arr))
            mad = float(np.median(np.abs(arr - med)))
            margin = med - 1.4826 * mad
            pos = float(np.mean(arr > 0))
            repeat_rows.append({
                "median_gain": med,
                "robust_margin": margin,
                "positive_fraction": pos,
                "passes": bool(len(arr) >= 3 and med > 0 and margin > 0 and pos >= 0.75),
            })
    if not fold_gains:
        return {"axis": axis_name, "rows": int(valid.sum()), "hosts": int(g_all.nunique()), "passes": False}
    pooled = np.asarray(fold_gains, float)
    pooled_med = float(np.median(pooled))
    pooled_mad = float(np.median(np.abs(pooled - pooled_med)))
    pooled_margin = pooled_med - 1.4826 * pooled_mad
    pooled_pos = float(np.mean(pooled > 0))
    pass_fraction = float(np.mean([bool(r["passes"]) for r in repeat_rows])) if repeat_rows else 0.0
    return {
        "axis": axis_name,
        "rows": int(valid.sum()),
        "hosts": int(g_all.nunique()),
        "pooled_median_gain": pooled_med,
        "pooled_robust_margin": pooled_margin,
        "pooled_positive_fraction": pooled_pos,
        "repeat_pass_fraction": pass_fraction,
        "passes": bool(pass_fraction >= 0.60 and pooled_margin > 0 and pooled_pos >= 0.70),
    }


def _linear_candidate_outer_validation(
    target: pd.Series,
    axis: pd.Series,
    discovery_mask: pd.Series,
    validation_mask: pd.Series,
) -> dict[str, Any]:
    tr = discovery_mask & target.notna() & pd.to_numeric(axis, errors="coerce").notna()
    va = validation_mask & target.notna() & pd.to_numeric(axis, errors="coerce").notna()
    if int(tr.sum()) < 100 or int(va.sum()) < 20:
        return {"rows_discovery": int(tr.sum()), "rows_validation": int(va.sum()), "gain": math.nan}
    xtr = pd.to_numeric(axis.loc[tr], errors="coerce").to_numpy(float)
    ytr = pd.to_numeric(target.loc[tr], errors="coerce").to_numpy(float)
    xva = pd.to_numeric(axis.loc[va], errors="coerce").to_numpy(float)
    yva = pd.to_numeric(target.loc[va], errors="coerce").to_numpy(float)
    beta, *_ = np.linalg.lstsq(np.column_stack([np.ones(len(xtr)), xtr]), ytr, rcond=None)
    den = float(np.std(yva))
    if den <= 1e-14:
        return {"rows_discovery": int(tr.sum()), "rows_validation": int(va.sum()), "gain": math.nan}
    base = float(np.sqrt(np.mean(np.square(yva - float(np.mean(ytr))))) / den)
    cand = float(np.sqrt(np.mean(np.square(yva - (float(beta[0]) + float(beta[1]) * xva)))) / den)
    return {
        "rows_discovery": int(tr.sum()),
        "rows_validation": int(va.sum()),
        "nrmse_baseline": base,
        "nrmse_candidate": cand,
        "gain": float((base - cand) / max(abs(base), 1e-30)),
        "beta": [float(beta[0]), float(beta[1])],
    }



def _within_host_scope_audit(
    target: pd.Series,
    axis: pd.Series,
    groups: pd.Series,
    discovery_mask: pd.Series,
    validation_mask: pd.Series,
) -> dict[str, Any]:
    """Separate a regime association into within-host vs host/survey-mediated scope.

    This is a scope audit, not a fresh promotion gate: each split is demeaned within
    hosts having >=2 usable planets.  The discovery within-host slope is frozen and
    evaluated on validation hosts after their own within-host centering.  Positive
    outer gain supports a planet-local component; non-positive outer gain lowers the
    interpretation to host/survey-mediated without erasing the regime association.
    """
    def transformed(mask: pd.Series) -> pd.DataFrame:
        valid = mask & target.notna() & pd.to_numeric(axis, errors="coerce").notna() & groups.notna()
        d = pd.DataFrame({
            "host": groups.loc[valid].astype(str),
            "y": pd.to_numeric(target.loc[valid], errors="coerce"),
            "x": pd.to_numeric(axis.loc[valid], errors="coerce"),
        }).dropna()
        counts = d.groupby("host").size()
        d = d[d["host"].isin(counts[counts >= 2].index)].copy()
        if d.empty:
            return d
        d["yd"] = d["y"] - d.groupby("host")["y"].transform("mean")
        d["xd"] = d["x"] - d.groupby("host")["x"].transform("mean")
        varying = d.groupby("host")["xd"].apply(lambda v: bool(float(np.max(np.abs(v.to_numpy(float)))) > 1e-12))
        return d[d["host"].isin(varying[varying].index)].copy()

    tr = transformed(discovery_mask)
    va = transformed(validation_mask)
    if len(tr) < 100 or tr["host"].nunique() < 20 or len(va) < 30 or va["host"].nunique() < 10:
        return {
            "status": "INSUFFICIENT_MULTIPLANET_HOST_SUPPORT",
            "discovery_rows": int(len(tr)), "discovery_hosts": int(tr["host"].nunique()) if not tr.empty else 0,
            "validation_rows": int(len(va)), "validation_hosts": int(va["host"].nunique()) if not va.empty else 0,
        }
    den = float(np.dot(tr["xd"].to_numpy(float), tr["xd"].to_numpy(float)))
    if den <= 1e-20:
        return {"status": "NO_WITHIN_HOST_AXIS_VARIATION"}
    beta = float(np.dot(tr["xd"].to_numpy(float), tr["yd"].to_numpy(float)) / den)
    def gain(d: pd.DataFrame) -> float:
        yy = d["yd"].to_numpy(float); xx = d["xd"].to_numpy(float)
        scale = float(np.std(yy))
        if scale <= 1e-14:
            return math.nan
        base = float(np.sqrt(np.mean(np.square(yy))) / scale)
        cand = float(np.sqrt(np.mean(np.square(yy - beta * xx))) / scale)
        return float((base - cand) / max(abs(base), 1e-30))
    dg = gain(tr); vg = gain(va)
    return {
        "status": "PLANET_LOCAL_COMPONENT_SUPPORTED" if vg > 0 else "HOST_OR_SURVEY_MEDIATED_CANDIDATE",
        "discovery_rows": int(len(tr)), "discovery_hosts": int(tr["host"].nunique()),
        "validation_rows": int(len(va)), "validation_hosts": int(va["host"].nunique()),
        "frozen_within_host_beta": beta,
        "discovery_within_host_gain": dg,
        "validation_within_host_gain": vg,
    }

def _linear_candidate_tail_stress(target: pd.Series, axis: pd.Series, mask: pd.Series) -> dict[str, Any]:
    valid = mask & target.notna() & pd.to_numeric(axis, errors="coerce").notna()
    x = pd.to_numeric(axis.loc[valid], errors="coerce").to_numpy(float)
    y = pd.to_numeric(target.loc[valid], errors="coerce").to_numpy(float)
    if len(y) < 200:
        return {"passes": False, "rows": int(len(y)), "reason": "INSUFFICIENT_ROWS"}
    qlo, qhi = np.quantile(x, [0.15, 0.85])
    gains: list[float] = []
    rows: list[dict[str, Any]] = []
    for side, test in (("LOW", x <= qlo), ("HIGH", x >= qhi)):
        train = ~test
        if int(test.sum()) < 30 or int(train.sum()) < 100:
            continue
        beta, *_ = np.linalg.lstsq(np.column_stack([np.ones(int(train.sum())), x[train]]), y[train], rcond=None)
        den = float(np.std(y[test]))
        if den <= 1e-14:
            continue
        base = float(np.sqrt(np.mean(np.square(y[test] - float(np.mean(y[train]))))) / den)
        cand = float(np.sqrt(np.mean(np.square(y[test] - (float(beta[0]) + float(beta[1]) * x[test])))) / den)
        gain = float((base - cand) / max(abs(base), 1e-30))
        gains.append(gain)
        rows.append({"tail": side, "relative_gain": gain, "rows": int(test.sum())})
    if not gains:
        return {"passes": False, "rows": int(len(y)), "reason": "NO_VALID_TAILS"}
    arr = np.asarray(gains, dtype=float)
    med = float(np.median(arr))
    mad = float(np.median(np.abs(arr - med)))
    margin = med - 1.4826 * mad
    positive = float(np.mean(arr > 0))
    return {
        "passes": bool(len(arr) >= 2 and margin > 0 and positive >= 0.75),
        "rows": int(len(y)),
        "median_gain": med,
        "robust_margin": margin,
        "positive_fraction": positive,
        "tails": rows,
    }


def _nrmse_arrays(y: np.ndarray, pred: np.ndarray) -> float:
    y = np.asarray(y, dtype=float)
    pred = np.asarray(pred, dtype=float)
    den = float(np.std(y))
    return float(np.sqrt(np.mean(np.square(y - pred))) / den) if den > 1e-14 else math.inf


def _host_leave_one_planet_out_test(raw: pd.DataFrame, passports: pd.DataFrame) -> dict[str, Any]:
    """Test whether a shared host coordinate predicts an unseen sibling planet.

    For each multi-planet host and each target planet, lambda_h is estimated from
    the *other* planets only.  The global baseline is frozen from discovery hosts.
    Validation targets are never used to estimate the global baseline or the
    target's own host scale.
    """
    ratio = pd.to_numeric(passports["insolation_catalog_model_ratio"], errors="coerce")
    y = _safe_log_positive(ratio)
    base = pd.DataFrame({
        "host": raw["hostname"].astype(str),
        "y": y,
    }).dropna()
    base["split"] = base["host"].map(host_split)
    counts = base.groupby("host").size()
    base = base[base["host"].isin(counts[counts >= 2].index)].copy()
    discovery = base[base["split"] == "discovery"]
    global_mu = float(discovery["y"].median()) if len(discovery) else 0.0

    rows: list[dict[str, Any]] = []
    for host, grp in base.groupby("host"):
        vals = grp["y"].to_numpy(float)
        idxs = list(grp.index)
        for j, idx in enumerate(idxs):
            others = np.delete(vals, j)
            if len(others) == 0:
                continue
            rows.append({
                "host": host,
                "split": str(grp.loc[idx, "split"]),
                "y": float(vals[j]),
                "host_prediction": float(np.median(others)),
            })
    pred = pd.DataFrame(rows)

    def metrics(split: str) -> dict[str, Any]:
        d = pred[pred["split"] == split].copy()
        if d.empty:
            return {"rows": 0, "hosts": 0}
        yy = d["y"].to_numpy(float)
        hp = d["host_prediction"].to_numpy(float)
        bp = np.full(len(d), global_mu, dtype=float)
        abs_b = np.abs(yy - bp)
        abs_h = np.abs(yy - hp)
        rmse_b = float(np.sqrt(np.mean(np.square(yy - bp))))
        rmse_h = float(np.sqrt(np.mean(np.square(yy - hp))))
        return {
            "rows": int(len(d)),
            "hosts": int(d["host"].nunique()),
            "baseline_discovery_global_log_scale": global_mu,
            "mae_baseline": float(np.mean(abs_b)),
            "mae_host_loo": float(np.mean(abs_h)),
            "mae_relative_gain": float(1.0 - np.mean(abs_h) / max(np.mean(abs_b), 1e-30)),
            "rmse_baseline": rmse_b,
            "rmse_host_loo": rmse_h,
            "rmse_relative_gain": float(1.0 - rmse_h / max(rmse_b, 1e-30)),
            "host_prediction_lower_abs_error_fraction": float(np.mean(abs_h < abs_b)),
            "median_absolute_error_reduction": float(np.median(abs_b - abs_h)),
        }

    return {
        "prediction": "HELD_OUT_PLANET_LOG_INSOLATION_SCALE_FROM_OTHER_PLANETS_OF_SAME_HOST",
        "estimator": "MEDIAN_LOG_SCALE_OF_OTHER_PLANETS_ONLY",
        "global_baseline_frozen_from": "DISCOVERY_HOSTS_ONLY",
        "discovery": metrics("discovery"),
        "validation": metrics("validation"),
        "sealed_reporting_only": metrics("sealed"),
        "heldout_target_used_to_estimate_its_host_scale": False,
        "status": "HOST_LATENT_PREDICTIVE_SUPPORT" if metrics("validation").get("rmse_relative_gain", -math.inf) > 0 else "HOST_LATENT_PREDICTION_NOT_SUPPORTED",
    }


def _host_scale_coherence_null_test(raw: pd.DataFrame, passports: pd.DataFrame, *, permutations: int = 64) -> dict[str, Any]:
    ratio = pd.to_numeric(passports["insolation_catalog_model_ratio"], errors="coerce")
    d = pd.DataFrame({"host": raw["hostname"].astype(str), "ratio": ratio}).dropna()
    d = d[d["ratio"] > 0].copy()
    counts = d.groupby("host").size()
    multi = counts[counts >= 2]
    actual_ratios: list[float] = []
    for host in multi.index:
        vals = d.loc[d["host"] == host, "ratio"].to_numpy(float)
        actual_ratios.append(float(np.max(vals) / np.min(vals)))
    actual = np.asarray(actual_ratios, dtype=float)
    values = d["ratio"].to_numpy(float)
    sizes = multi.to_numpy(int)
    rng = np.random.default_rng(20260920)
    null_fraction: list[float] = []
    null_median_ratio: list[float] = []
    for _ in range(int(permutations)):
        perm = rng.permutation(values)
        cursor = 0
        ratios: list[float] = []
        for size in sizes:
            vals = perm[cursor:cursor + int(size)]
            cursor += int(size)
            ratios.append(float(np.max(vals) / np.min(vals)))
        arr = np.asarray(ratios, dtype=float)
        null_fraction.append(float(np.mean(arr <= 1.10)))
        null_median_ratio.append(float(np.median(arr)))
    actual_fraction = float(np.mean(actual <= 1.10)) if len(actual) else math.nan
    return {
        "multi_planet_hosts": int(len(actual)),
        "multi_planet_rows": int(multi.sum()),
        "actual_fraction_max_min_within_10_percent": actual_fraction,
        "actual_median_max_min_ratio": float(np.median(actual)) if len(actual) else math.nan,
        "null_permutations": int(permutations),
        "null_fraction_within_10_percent_mean": float(np.mean(null_fraction)) if null_fraction else math.nan,
        "null_fraction_within_10_percent_max": float(np.max(null_fraction)) if null_fraction else math.nan,
        "null_median_max_min_ratio_mean": float(np.mean(null_median_ratio)) if null_median_ratio else math.nan,
        "coherence_exceeds_every_null_permutation": bool(null_fraction and actual_fraction > max(null_fraction)),
    }



def _host_effective_luminosity_mechanism_test(raw: pd.DataFrame, passports: pd.DataFrame) -> dict[str, Any]:
    """Resolve the algebraic meaning of the shared host scale before causal interpretation.

    The archive insolation observable obeys S/S_earth = (L_star/L_sun) (AU/a)^2.
    Therefore every central-valued planet defines an effective host luminosity

        L_eff,hp/L_sun = S_catalog,hp * (a_hp/AU)^2,

    while the composite stellar radius/temperature define

        L_RT,hp/L_sun = R_star^2 (T_eff/5772 K)^4.

    Their ratio is exactly the previously introduced lambda_hp.  A coherent
    lambda_h is therefore first a *stellar-luminosity representation gap*; its
    deeper origin may still be physical (different stellar state/model) or
    observational/provenance/calibration.  This test identifies the
    representation without claiming the causal origin.
    """
    insol = _central_numeric(raw, "pl_insol", positive=True)
    a = _central_numeric(raw, "pl_orbsmax", positive=True)
    rs = _central_numeric(raw, "st_rad", positive=True)
    teff = _central_numeric(raw, "st_teff", positive=True)
    valid = insol.notna() & a.notna() & rs.notna() & teff.notna()
    frame = pd.DataFrame({
        "host": raw["hostname"].astype(str),
        "split": raw["hostname"].astype(str).map(host_split),
        "S": insol,
        "a": a,
        "R": rs,
        "T": teff,
    })[valid].copy()
    frame["L_eff"] = frame["S"] * np.square(frame["a"])
    frame["L_RT"] = np.square(frame["R"]) * np.power(frame["T"] / 5772.0, 4.0)
    frame["lambda_luminosity"] = frame["L_eff"] / frame["L_RT"]

    # Identity check against the passport ratio.  It should be numerical-zero
    # apart from floating-point roundoff; failure means the theory layers are
    # internally inconsistent.
    passport_ratio = pd.to_numeric(passports.loc[frame.index, "insolation_catalog_model_ratio"], errors="coerce")
    identity_error = np.abs(np.log(frame["lambda_luminosity"].to_numpy(float)) - np.log(passport_ratio.to_numpy(float)))
    identity_error = identity_error[np.isfinite(identity_error)]

    host_rows: list[dict[str, Any]] = []
    for host, grp in frame.groupby("host"):
        if len(grp) < 2:
            continue
        le = grp["L_eff"].to_numpy(float)
        lr = grp["L_RT"].to_numpy(float)
        cv_eff = float(np.std(le) / max(abs(np.mean(le)), 1e-30))
        cv_rt = float(np.std(lr) / max(abs(np.mean(lr)), 1e-30))
        host_rows.append({
            "host": str(host),
            "split": str(grp["split"].iloc[0]),
            "planets": int(len(grp)),
            "effective_luminosity_solar": float(np.median(le)),
            "radius_temperature_luminosity_solar": float(np.median(lr)),
            "lambda_h_luminosity_ratio": float(np.median(le / lr)),
            "effective_luminosity_cv": cv_eff,
            "radius_temperature_luminosity_cv": cv_rt,
        })
    hosts = pd.DataFrame(host_rows)

    # Prospective sibling prediction in luminosity coordinates.  Estimate the
    # host L_eff from all sibling planets except the target, then predict target
    # insolation using only its semi-major axis.
    loo_rows: list[dict[str, Any]] = []
    for host, grp in frame.groupby("host"):
        if len(grp) < 2:
            continue
        vals = grp[["split", "S", "a", "L_eff", "L_RT"]].copy()
        for idx, row in vals.iterrows():
            siblings = vals.drop(index=idx)
            if siblings.empty:
                continue
            l_eff_pred = float(np.median(siblings["L_eff"].to_numpy(float)))
            pred_host = l_eff_pred / float(row["a"] ** 2)
            pred_rt = float(row["L_RT"] / (row["a"] ** 2))
            y = float(np.log(row["S"]))
            loo_rows.append({
                "host": str(host),
                "split": str(row["split"]),
                "abs_error_RT": float(abs(y - np.log(pred_rt))),
                "abs_error_sibling_Leff": float(abs(y - np.log(pred_host))),
                "sq_error_RT": float((y - np.log(pred_rt)) ** 2),
                "sq_error_sibling_Leff": float((y - np.log(pred_host)) ** 2),
            })
    loo = pd.DataFrame(loo_rows)

    def _metrics(split: str) -> dict[str, Any]:
        d = loo[loo["split"] == split].copy() if not loo.empty else pd.DataFrame()
        if d.empty:
            return {"rows": 0, "hosts": 0}
        mae0 = float(d["abs_error_RT"].mean())
        mae1 = float(d["abs_error_sibling_Leff"].mean())
        rmse0 = float(np.sqrt(d["sq_error_RT"].mean()))
        rmse1 = float(np.sqrt(d["sq_error_sibling_Leff"].mean()))
        return {
            "rows": int(len(d)),
            "hosts": int(d["host"].nunique()),
            "mae_RT_baseline": mae0,
            "mae_sibling_effective_luminosity": mae1,
            "mae_relative_gain": float(1.0 - mae1 / max(mae0, 1e-30)),
            "rmse_RT_baseline": rmse0,
            "rmse_sibling_effective_luminosity": rmse1,
            "rmse_relative_gain": float(1.0 - rmse1 / max(rmse0, 1e-30)),
            "sibling_prediction_better_fraction": float(np.mean(d["abs_error_sibling_Leff"] < d["abs_error_RT"])),
        }

    if hosts.empty:
        coherence = {}
    else:
        coherence = {
            "multi_planet_hosts": int(len(hosts)),
            "median_effective_luminosity_cv": float(hosts["effective_luminosity_cv"].median()),
            "fraction_effective_luminosity_cv_le_1pct": float(np.mean(hosts["effective_luminosity_cv"] <= 0.01)),
            "fraction_effective_luminosity_cv_le_5pct": float(np.mean(hosts["effective_luminosity_cv"] <= 0.05)),
            "fraction_effective_luminosity_cv_le_10pct": float(np.mean(hosts["effective_luminosity_cv"] <= 0.10)),
            "median_radius_temperature_luminosity_cv": float(hosts["radius_temperature_luminosity_cv"].median()),
            "median_lambda_h": float(hosts["lambda_h_luminosity_ratio"].median()),
        }
    validation = _metrics("validation")
    mechanism_identified = bool(
        identity_error.size
        and float(np.max(identity_error)) < 1e-10
        and validation.get("rmse_relative_gain", -math.inf) > 0
        and coherence.get("fraction_effective_luminosity_cv_le_10pct", 0.0) >= 0.75
    )
    return {
        "mechanism_identity": "lambda_hp = L_eff_from_catalog_insolation / L_RT_from_composite_radius_temperature",
        "effective_luminosity_definition": "L_eff/L_sun = (S_catalog/S_earth) * (a/AU)^2",
        "radius_temperature_luminosity_definition": "L_RT/L_sun = (R_star/R_sun)^2 * (T_eff/5772 K)^4",
        "identity_max_abs_log_error": float(np.max(identity_error)) if identity_error.size else math.nan,
        "coherence": coherence,
        "leave_one_planet_out_effective_luminosity_prediction": {
            "discovery": _metrics("discovery"),
            "validation": validation,
            "sealed_reporting_only": _metrics("sealed"),
            "heldout_target_used_to_estimate_L_eff": False,
        },
        "representation_mechanism_identified": mechanism_identified,
        "causal_origin_resolved": False,
        "remaining_competing_origins": [
            "PUBLISHED_OR_ARCHIVE_STELLAR_LUMINOSITY_SOURCE_DIFFERS_FROM_COMPOSITE_R_T",
            "STELLAR_STATE_OR_MODEL_DIFFERENCE",
            "HOST_LEVEL_PROVENANCE_OR_CALIBRATION",
            "UNMODELED_STELLAR_PHYSICS_ONLY_IF_SELF_CONSISTENT_FRESH_DATA_PRESERVES_THE_GAP",
        ],
        "status": (
            "HOST_EFFECTIVE_LUMINOSITY_REPRESENTATION_IDENTIFIED_ORIGIN_UNRESOLVED"
            if mechanism_identified
            else "HOST_LATENT_REPRESENTATION_MECHANISM_OPEN"
        ),
        "claim_boundary": "ALGEBRAIC_REPRESENTATION_IDENTIFICATION_IS_NOT_CAUSAL_ORIGIN_IDENTIFICATION",
    }

def _host_feasible_domain_intersections(raw: pd.DataFrame, passports: pd.DataFrame) -> dict[str, Any]:
    insol_lo, insol_hi, _ = _constraint_interval(raw, "pl_insol", positive=True)
    model_lo = pd.to_numeric(passports["insolation_model_constraint_lower_earth"], errors="coerce")
    model_hi = pd.to_numeric(passports["insolation_model_constraint_upper_earth"], errors="coerce")
    valid = (
        insol_lo.notna() & insol_hi.notna() & model_lo.notna() & model_hi.notna()
        & (insol_lo > 0) & (insol_hi > 0) & (model_lo > 0) & (model_hi > 0)
    )
    alpha_lo = pd.Series(np.nan, index=raw.index, dtype=float)
    alpha_hi = pd.Series(np.nan, index=raw.index, dtype=float)
    alpha_lo.loc[valid] = np.log(insol_lo.loc[valid].astype(float) / model_hi.loc[valid].astype(float))
    alpha_hi.loc[valid] = np.log(insol_hi.loc[valid].astype(float) / model_lo.loc[valid].astype(float))
    frame = pd.DataFrame({
        "host": raw["hostname"].astype(str),
        "alpha_lo": alpha_lo,
        "alpha_hi": alpha_hi,
    }).dropna()
    candidate_hosts = set(passports.loc[passports["host_latent_scale_candidate"].astype(bool), "hostname"].astype(str))
    rows: list[dict[str, Any]] = []
    for host, grp in frame.groupby("host"):
        if len(grp) < 2:
            continue
        lo = float(grp["alpha_lo"].max())
        hi = float(grp["alpha_hi"].min())
        rows.append({
            "host": host,
            "planets": int(len(grp)),
            "intersection_lower_log_lambda": lo,
            "intersection_upper_log_lambda": hi,
            "intersection_nonempty": bool(lo <= hi),
            "previous_host_latent_candidate": bool(host in candidate_hosts),
        })
    total = len(rows)
    nonempty = sum(bool(r["intersection_nonempty"]) for r in rows)
    cand = [r for r in rows if r["previous_host_latent_candidate"]]
    return {
        "host_domain_definition": "OMEGA_h = INTERSECTION_p LOG(S_obs_interval / S_model_interval)",
        "multi_planet_hosts_with_interval_domains": int(total),
        "hosts_with_nonempty_common_lambda_domain": int(nonempty),
        "common_domain_fraction": float(nonempty / total) if total else math.nan,
        "previous_candidate_hosts_with_interval_domains": int(len(cand)),
        "previous_candidate_hosts_with_nonempty_common_domain": int(sum(bool(r["intersection_nonempty"]) for r in cand)),
        "all_previous_candidate_hosts_defensible_by_common_interval_lambda": bool(cand) and all(bool(r["intersection_nonempty"]) for r in cand),
        "claim_boundary": "NONEMPTY_INTERSECTION_MEANS_ALLOWED_NOT_CAUSALLY_ESTABLISHED",
    }


def _host_known_axis_explanation_scan(raw: pd.DataFrame, passports: pd.DataFrame) -> dict[str, Any]:
    ratio = pd.to_numeric(passports["insolation_catalog_model_ratio"], errors="coerce")
    target = _safe_log_positive(ratio)
    planet = pd.DataFrame({"host": raw["hostname"].astype(str), "target": target}).dropna()
    host_counts = planet.groupby("host").size()
    host_target = planet[planet["host"].isin(host_counts[host_counts >= 2].index)].groupby("host")["target"].median().rename("alpha_h").reset_index()
    host_target["split"] = host_target["host"].map(host_split)

    features: dict[str, pd.Series] = {
        "log_stellar_mass_solar": _safe_log_positive(_central_numeric(raw, "st_mass", positive=True)),
        "log_stellar_radius_solar": _safe_log_positive(_central_numeric(raw, "st_rad", positive=True)),
        "log_stellar_temperature_K": _safe_log_positive(_central_numeric(raw, "st_teff", positive=True)),
        "stellar_logg_cgs": _central_numeric(raw, "st_logg"),
        "stellar_metallicity_FeH": _central_numeric(raw, "st_met"),
        "log_distance_pc": _safe_log_positive(_central_numeric(raw, "sy_dist", positive=True)),
        "discovery_year_centered": _central_numeric(raw, "disc_year") - 2000.0,
        "system_star_count": _central_numeric(raw, "sy_snum"),
        "system_planet_count": _central_numeric(raw, "sy_pnum"),
    }
    f = pd.DataFrame({"host": raw["hostname"].astype(str)})
    for name, values in features.items():
        f[name] = values
    host_features = f.groupby("host").median(numeric_only=True).reset_index()
    h = host_target.merge(host_features, on="host", how="left")
    discovery = h["split"].eq("discovery")
    validation = h["split"].eq("validation")
    scans: list[dict[str, Any]] = []
    for name in features:
        stability = _availability_axis_stability(
            h.loc[discovery, "alpha_h"], h.loc[discovery, name], h.loc[discovery, "host"],
            axis_name=f"HOST-LATENT::{name}",
        )
        outer: dict[str, Any] = {"gain": math.nan}
        tail: dict[str, Any] = {"passes": False}
        if bool(stability.get("passes")):
            outer = _linear_candidate_outer_validation(h["alpha_h"], h[name], discovery, validation)
            tail = _linear_candidate_tail_stress(h["alpha_h"], h[name], discovery)
        scans.append({
            "axis": name,
            "discovery_stability": stability,
            "tail_stress": tail,
            "outer_validation": outer,
            "joint_explanation_supported": bool(stability.get("passes") and tail.get("passes") and float(outer.get("gain", math.nan)) > 0),
        })
    scans.sort(key=lambda row: (
        -int(bool(row["joint_explanation_supported"])),
        -float(row["discovery_stability"].get("pooled_robust_margin", -math.inf)),
        row["axis"],
    ))

    # Multivariate known-axis attack.  Ridge strength is selected only by
    # discovery host folds; validation is read afterwards.
    cols = list(features)
    complete = h.dropna(subset=["alpha_h", *cols]).copy()
    dmask = complete["split"].eq("discovery")
    vmask = complete["split"].eq("validation")
    multivariate: dict[str, Any] = {"status": "INSUFFICIENT_COMPLETE_HOSTS"}
    if int(dmask.sum()) >= 100 and int(vmask.sum()) >= 30:
        Xtr = complete.loc[dmask, cols].to_numpy(float)
        ytr = complete.loc[dmask, "alpha_h"].to_numpy(float)
        Xva = complete.loc[vmask, cols].to_numpy(float)
        yva = complete.loc[vmask, "alpha_h"].to_numpy(float)
        mu = np.mean(Xtr, axis=0)
        sd = np.std(Xtr, axis=0)
        sd[sd < 1e-12] = 1.0
        Ztr = (Xtr - mu) / sd
        Zva = (Xva - mu) / sd
        lambdas = (0.0, 0.01, 0.1, 1.0, 10.0, 100.0)
        ranked: list[tuple[float, float, list[float]]] = []
        dhosts = complete.loc[dmask, "host"].astype(str).tolist()
        for lam in lambdas:
            gains: list[float] = []
            for fold in range(4):
                test = np.asarray([h64(f"HOST-MULTI::{host}") % 4 == fold for host in dhosts], dtype=bool)
                if int(test.sum()) < 20 or int((~test).sum()) < 50:
                    continue
                A = np.column_stack([np.ones(int((~test).sum())), Ztr[~test]])
                reg = np.eye(A.shape[1]) * float(lam)
                reg[0, 0] = 0.0
                beta = np.linalg.solve(A.T @ A + reg, A.T @ ytr[~test])
                pred = np.column_stack([np.ones(int(test.sum())), Ztr[test]]) @ beta
                base = np.full(int(test.sum()), float(np.mean(ytr[~test])))
                b = _nrmse_arrays(ytr[test], base)
                c = _nrmse_arrays(ytr[test], pred)
                gains.append(float((b - c) / max(abs(b), 1e-30)))
            if gains:
                arr = np.asarray(gains, dtype=float)
                med = float(np.median(arr))
                mad = float(np.median(np.abs(arr - med)))
                ranked.append((med - 1.4826 * mad, float(lam), gains))
        if ranked:
            ranked.sort(key=lambda row: (-row[0], row[1]))
            margin, lam, gains = ranked[0]
            A = np.column_stack([np.ones(len(ytr)), Ztr])
            reg = np.eye(A.shape[1]) * float(lam)
            reg[0, 0] = 0.0
            beta = np.linalg.solve(A.T @ A + reg, A.T @ ytr)
            val_pred = np.column_stack([np.ones(len(yva)), Zva]) @ beta
            val_base = np.full(len(yva), float(np.mean(ytr)))
            b = _nrmse_arrays(yva, val_base)
            c = _nrmse_arrays(yva, val_pred)
            multivariate = {
                "status": "KNOWN_HOST_AXES_MULTIVARIATE_TESTED",
                "columns": cols,
                "selected_ridge_lambda_discovery_only": float(lam),
                "discovery_fold_gains": [float(x) for x in gains],
                "discovery_robust_margin": float(margin),
                "validation_rows": int(len(yva)),
                "validation_nrmse_baseline": float(b),
                "validation_nrmse_candidate": float(c),
                "validation_relative_gain": float((b - c) / max(abs(b), 1e-30)),
                "joint_explanation_supported": bool(margin > 0 and c < b),
            }
    return {
        "host_count": int(len(h)),
        "discovery_hosts": int(discovery.sum()),
        "validation_hosts": int(validation.sum()),
        "single_axis_explanations": scans,
        "supported_single_axis_count": int(sum(bool(r["joint_explanation_supported"]) for r in scans)),
        "known_axes_multivariate_attack": multivariate,
        "status": (
            "KNOWN_HOST_AXES_EXPLAIN_LATENT_SCALE"
            if any(bool(r["joint_explanation_supported"]) for r in scans) or bool(multivariate.get("joint_explanation_supported"))
            else "HOST_LATENT_SCALE_NOT_EXPLAINED_BY_TESTED_KNOWN_HOST_AXES"
        ),
    }


def build_hierarchical_exoplanet_theory(
    raw: pd.DataFrame,
    passports: pd.DataFrame,
    passport_summary: dict[str, Any],
) -> dict[str, Any]:
    """Compile the current exoplanet observational theory as a formal Atlas object."""
    host_prediction = _host_leave_one_planet_out_test(raw, passports)
    coherence = _host_scale_coherence_null_test(raw, passports)
    luminosity_mechanism = _host_effective_luminosity_mechanism_test(raw, passports)
    feasible = _host_feasible_domain_intersections(raw, passports)
    known_axis_attack = _host_known_axis_explanation_scan(raw, passports)
    regime_rows = list(
        passport_summary.get("irradiation_provenance_audit", {})
        .get("regime_local_candidate_defense", {})
        .get("candidates", [])
    )
    defended = [r for r in regime_rows if str(r.get("status", "")).startswith("DEFENDED_REGIME_LOCAL")]
    planet_local_supported = [r for r in defended if r.get("candidate_scope") == "PLANET_LOCAL_COMPONENT_SUPPORTED"]
    host_mediated = [r for r in defended if r.get("candidate_scope") == "HOST_OR_SURVEY_MEDIATED_CANDIDATE"]

    universal = {
        "equation": "S_phys/S_earth = (R_star/R_sun)^2 * (T_eff/5772 K)^4 / (a/AU)^2",
        "role": "ESTABLISHED_UNIVERSAL_BASELINE_NOT_NOVELTY_CLAIM",
        "catalogue_model_ratio": "lambda_hp = S_catalog_hp / S_phys_hp",
        "rows_with_consistency_ratio": int(passport_summary.get("irradiation_consistency_count", 0)),
        "median_ratio": float(passport_summary.get("insolation_ratio_median", math.nan)),
        "status": "UNIVERSAL_BASELINE_BOUND",
    }
    host_layer = {
        "coordinate": "alpha_h = log(lambda_h)",
        "lambda_definition": "lambda_h = exp(alpha_h)",
        "planet_observation_model": "log(lambda_hp) = alpha_h + f_R(x_hp) + epsilon_hp",
        "leave_one_planet_out_prediction": host_prediction,
        "within_host_coherence_null_test": coherence,
        "known_host_axis_attack": known_axis_attack,
        "effective_stellar_luminosity_mechanism": luminosity_mechanism,
        "status": (
            "PREDICTIVE_HOST_EFFECTIVE_LUMINOSITY_REPRESENTATION_IDENTIFIED_ORIGIN_UNRESOLVED"
            if luminosity_mechanism.get("representation_mechanism_identified")
            else "PREDICTIVE_HOST_LATENT_COORDINATE_MECHANISM_UNRESOLVED"
            if host_prediction.get("status") == "HOST_LATENT_PREDICTIVE_SUPPORT" and known_axis_attack.get("status") == "HOST_LATENT_SCALE_NOT_EXPLAINED_BY_TESTED_KNOWN_HOST_AXES"
            else "HOST_LATENT_LAYER_PARTIALLY_RESOLVED"
        ),
        "canonical_or_causal_claim": False,
    }
    regime = {
        "term": "f_R(M_p, R_p, e, observational_regime, ...)",
        "predeclared_regime_axis": "discoverymethod",
        "defended_regime_candidates": defended,
        "defended_but_host_or_survey_mediated_count": int(len(host_mediated)),
        "planet_local_component_supported_count": int(len(planet_local_supported)),
        "status": (
            "PLANET_LOCAL_TERM_SUPPORTED"
            if planet_local_supported
            else "PLANET_LOCAL_TERM_OPEN_BUT_NOT_YET_WITHIN_HOST_TRANSFER_SUPPORTED"
        ),
        "canonical_or_causal_claim": False,
    }
    feasible_layer = {
        "planet_domain": "Omega_hp = observational interval/censoring constraints for each measured coordinate",
        "host_domain": feasible,
        "semantics": ["REQUIRED", "ALLOWED", "EXCLUDED", "REGIME_LOCAL"],
        "limits_are_constraints": True,
        "model_inferred_is_observed": False,
        "status": "FEASIBLE_DOMAIN_LAYER_ACTIVE",
    }
    competing = [
        {
            "id": "H-KNOWN-STELLAR-STATE",
            "statement": "alpha_h is explained by tested observed stellar/system coordinates",
            "current_status": "WEAKENED" if known_axis_attack.get("status") == "HOST_LATENT_SCALE_NOT_EXPLAINED_BY_TESTED_KNOWN_HOST_AXES" else "SUPPORTED",
            "attack": "discovery host-CV + tail stress + outer validation",
            "defense": "allow multivariate combination of predeclared known host axes selected discovery-only",
        },
        {
            "id": "H-HOST-EFFECTIVE-LUMINOSITY",
            "statement": "alpha_h is the ratio between effective stellar luminosity implied by catalogue insolation and luminosity reconstructed from composite R_star,T_eff",
            "current_status": "REPRESENTATION_IDENTIFIED_ORIGIN_UNRESOLVED" if luminosity_mechanism.get("representation_mechanism_identified") else "LIVE",
            "attack": "break the algebraic identity, sibling L_eff coherence, or held-out sibling prediction on fresh self-consistent data",
            "defense": "S_catalog*a^2 defines L_eff and lambda_h=L_eff/L_RT exactly; sibling planets estimate L_eff without using the held-out target",
        },
        {
            "id": "H-HOST-PROVENANCE-CALIBRATION",
            "statement": "the effective-luminosity representation gap is caused by shared host/source/calibration provenance",
            "current_status": "LIVE_STRONGLY_COMPATIBLE",
            "attack": "require the gap to persist when pl_insol, a, R_star and T_eff come from one self-consistent PS solution",
            "defense": "PSCompPars explicitly permits mixed sources and archive-calculated values; common host L_eff is expected from a shared luminosity source",
        },
        {
            "id": "H-MISSING-HOST-PHYSICS",
            "statement": "the effective-luminosity representation gap contains a missing physical stellar coordinate not represented by tested R_star,T_eff and other host axes",
            "current_status": "LIVE_UNRESOLVED",
            "attack": "explain L_eff/L_RT using provenance/method/source variables or remove the luminosity gap in self-consistent PS",
            "defense": "predict sibling planets and survive fresh self-consistent host-level data",
        },
        {
            "id": "H-PLANET-LOCAL-REGIME",
            "statement": "f_R contains planet-local mass/radius/regime physics after host state is removed",
            "current_status": "WEAKENED_NOT_EXCLUDED" if not planet_local_supported else "SUPPORTED",
            "attack": "within-host outer transfer after host centering",
            "defense": "restrict to predeclared regimes and propagate censoring/uncertainty",
        },
    ]
    predictions = [
        {
            "id": "P-HOST-SIBLING",
            "prediction": "for a held-out planet in a multi-planet host, log(S_catalog/S_phys) is predicted by the median log scale of the other planets of that host",
            "observed_test": host_prediction,
            "falsification": "fresh validation hosts show no improvement over the discovery-global scale baseline",
            "defense": "estimate alpha_h from sibling planets only; never use the held-out target",
            "heldout_refit_allowed": False,
        },
        {
            "id": "P-HOST-FEASIBLE-DOMAIN",
            "prediction": "sibling planets of a host admit a nonempty common alpha_h interval after uncertainty/censoring propagation",
            "observed_test": feasible,
            "falsification": "fresh self-consistent hosts produce empty common alpha_h domains beyond declared uncertainty",
            "defense": "propagate full observational intervals and one-sided limits without point imputation",
            "heldout_refit_allowed": False,
        },
        {
            "id": "P-KNOWN-HOST-AXES",
            "prediction": "if alpha_h is reducible to tested known stellar coordinates, at least one discovery-stable explanation or discovery-selected multivariate model transfers to validation hosts",
            "observed_test": known_axis_attack,
            "falsification": "all tested known-axis explanations fail discovery robustness or outer transfer",
            "defense": "allow discovery-only multivariate ridge combination of all predeclared host axes",
            "heldout_refit_allowed": False,
        },
        {
            "id": "P-HOST-EFFECTIVE-LUMINOSITY",
            "prediction": "for a held-out sibling planet, L_eff=S_catalog*a^2 estimated from the other planets predicts its catalogue insolation better than the composite R_star,T_eff luminosity baseline",
            "observed_test": luminosity_mechanism,
            "falsification": "the lambda identity fails or sibling-inferred L_eff loses validation-host predictive gain",
            "defense": "freeze L_eff estimator to sibling planets only and preserve the causal-origin claim boundary",
            "heldout_refit_allowed": False,
        },
        {
            "id": "P-PLANET-LOCAL-TERM",
            "prediction": "a genuine planet-local f_R term remains predictive after within-host centering on new hosts",
            "observed_test": {"planet_local_supported_count": len(planet_local_supported), "host_or_survey_mediated_count": len(host_mediated)},
            "falsification": "candidate gains reverse after within-host centering on validation hosts",
            "defense": "retain regime-local scope and censored feasible domains rather than demanding a global effect",
            "heldout_refit_allowed": False,
        },
    ]
    evidence_digest = digest_payload({
        "passport_summary_digest": passport_summary.get("digest"),
        "host_prediction": host_prediction,
        "coherence": coherence,
        "luminosity_mechanism": luminosity_mechanism,
        "feasible": feasible,
        "known_axis_attack": known_axis_attack,
    })
    experimental_models = [
        {
            "experiment_id":"E-SELF-CONSISTENT-PS-RETEST",
            "observable":"FRESH_SELF_CONSISTENT_PS_HOST_GAP_STATE",
            "cost":1.0,"feasible":True,
            "predictions":{
                "H-HOST-PROVENANCE-CALIBRATION":{"kind":"categorical","value":"HOST_GAP_COLLAPSES"},
                "H-MISSING-HOST-PHYSICS":{"kind":"categorical","value":"HOST_GAP_PERSISTS"},
                "H-PLANET-LOCAL-REGIME":{"kind":"categorical","value":"HOST_GAP_COLLAPSES_PLANET_RESIDUAL_PERSISTS"},
            },
        },
        {
            "experiment_id":"E-INDEPENDENT-STELLAR-LUMINOSITY",
            "observable":"INDEPENDENT_STELLAR_LUMINOSITY_VS_SIBLING_EFFECTIVE_LUMINOSITY",
            "cost":2.0,"feasible":True,
            "predictions":{
                "H-HOST-PROVENANCE-CALIBRATION":{"kind":"categorical","value":"L_EFF_MATCHES_INDEPENDENT_L_AFTER_SOURCE_ALIGNMENT"},
                "H-MISSING-HOST-PHYSICS":{"kind":"categorical","value":"L_EFF_GAP_PERSISTS_AFTER_SOURCE_ALIGNMENT"},
                "H-PLANET-LOCAL-REGIME":{"kind":"categorical","value":"HOST_LUMINOSITY_ALIGNS_PLANET_RESIDUAL_REMAINS"},
            },
        },
        {
            "experiment_id":"E-FRESH-SIBLING-PREDICTION",
            "observable":"NEW_PLANET_SIBLING_PREDICTION_TRANSFER",
            "cost":1.5,"feasible":True,
            "predictions":{
                "H-HOST-PROVENANCE-CALIBRATION":{"kind":"categorical","value":"PREDICTION_DEPENDS_ON_SHARED_SOURCE_STATE"},
                "H-MISSING-HOST-PHYSICS":{"kind":"categorical","value":"PREDICTION_PERSISTS_ACROSS_INDEPENDENT_SOURCE_STATE"},
                "H-PLANET-LOCAL-REGIME":{"kind":"categorical","value":"PLANET_RESIDUAL_DOMINATES_AFTER_HOST_CORRECTION"},
            },
        },
    ]
    compiled = HierarchicalObservationalTheoryOwner().compile(
        theory_id="EXOPLANET-HIERARCHICAL-OBSERVATIONAL-SPACE/1.1",
        universal_layer=universal,
        host_layer=host_layer,
        regime_layer=regime,
        feasible_domain_layer=feasible_layer,
        competing_explanations=competing,
        predictions=predictions,
        evidence_digest=evidence_digest,
        fresh_external_confirmation=False,
        experimental_models=experimental_models,
    )
    compiled = dict(compiled)
    compiled["domain_status"] = (
        "PREDICTIVE_HOST_EFFECTIVE_LUMINOSITY_REPRESENTATION_SUPPORTED_ORIGIN_UNRESOLVED"
        if luminosity_mechanism.get("representation_mechanism_identified")
        else "PREDICTIVE_HOST_LAYER_SUPPORTED_MECHANISM_UNRESOLVED"
        if host_prediction.get("status") == "HOST_LATENT_PREDICTIVE_SUPPORT"
        else "HIERARCHICAL_THEORY_OPEN"
    )
    compiled["scientific_promotion"] = False
    compiled["fresh_self_consistent_PS_required"] = True
    compiled["digest"] = digest_payload({k: v for k, v in compiled.items() if k != "digest"})
    return compiled


def build_availability_passports(
    raw: pd.DataFrame,
    *,
    frozen_c_hat_si: float,
    g_reference_si: float,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Calculate every catalogue row in its maximal observed/derived subspace.

    Missing observations are never converted to zero or "no effect".  Where the
    frozen orbital relation or an established identity can infer exactly one
    missing quantity, the result is marked MODEL_INFERRED rather than observed.
    """
    out = pd.DataFrame(index=raw.index)
    for name in ("pl_name", "hostname", "discoverymethod", "pl_bmassprov"):
        out[name] = raw[name].astype(str) if name in raw.columns else ""
    out["disc_year"] = _finite_numeric(raw, "disc_year")

    # Point-valued physics uses only central measurements. Archive upper/lower limits
    # remain in the passport as censored observations, never as exact values.
    P = _central_numeric(raw, "pl_orbper", positive=True)
    a = _central_numeric(raw, "pl_orbsmax", positive=True)
    Ms = _central_numeric(raw, "st_mass", positive=True)
    Mp = _central_numeric(raw, "pl_bmasse", positive=True)
    Rp = _central_numeric(raw, "pl_rade", positive=True)
    Teff = _central_numeric(raw, "st_teff", positive=True)
    Rs = _central_numeric(raw, "st_rad", positive=True)
    logg = _central_numeric(raw, "st_logg")
    ecc = _central_numeric(raw, "pl_orbeccen")
    insol = _central_numeric(raw, "pl_insol", positive=True)
    eqt = _central_numeric(raw, "pl_eqt", positive=True)

    out["planet_mass_limit_flag"] = _limit_flag(raw, "pl_bmasse")
    out["planet_radius_limit_flag"] = _limit_flag(raw, "pl_rade")
    out["insolation_limit_flag"] = _limit_flag(raw, "pl_insol")
    out["equilibrium_temperature_limit_flag"] = _limit_flag(raw, "pl_eqt")

    # Maximal per-row axis availability uses exactly the existing DORMANT_AXES semantics.
    axis_values: dict[str, pd.Series] = {
        "log_planet_mass_earth": _safe_log_positive(Mp),
        "log_planet_radius_earth": _safe_log_positive(Rp),
        "eccentricity": ecc,
        "log_insolation_earth": _safe_log_positive(insol),
        "log_equilibrium_temperature_K": _safe_log_positive(eqt),
        "log_stellar_temperature_K": _safe_log_positive(Teff),
        "log_stellar_radius_solar": _safe_log_positive(Rs),
        "stellar_metallicity_FeH": _finite_numeric(raw, "st_met"),
        "stellar_logg_cgs": logg,
        "log_distance_pc": _safe_log_positive(_positive_numeric(raw, "sy_dist")),
        "discovery_year_centered": _finite_numeric(raw, "disc_year") - 2000.0,
        "system_planet_count": _finite_numeric(raw, "sy_pnum"),
        "ttv_flag": _finite_numeric(raw, "ttv_flag"),
        "controversial_flag": _finite_numeric(raw, "pl_controv_flag"),
        "relative_period_uncertainty": safe_relerr(raw["pl_orbpererr1"], raw["pl_orbper"]),
        "relative_semimajor_axis_uncertainty": safe_relerr(raw["pl_orbsmaxerr1"], raw["pl_orbsmax"]),
        "relative_stellar_mass_uncertainty": safe_relerr(raw["st_masserr1"], raw["st_mass"]),
    }
    axis_available = pd.DataFrame({k: np.isfinite(pd.to_numeric(v, errors="coerce")) for k, v in axis_values.items()}, index=raw.index)
    out["available_axis_count"] = axis_available.sum(axis=1).astype(int)
    out["available_axes"] = axis_available.apply(lambda row: ";".join([k for k, ok in row.items() if bool(ok)]), axis=1)

    # Established stellar identity g = G M / R^2 is used only when st_mass is absent.
    R_SUN_M = 6.957e8
    M_SUN_KG_LOCAL = M_SUN_KG
    mass_from_logg_radius = pd.Series(np.nan, index=raw.index, dtype=float)
    can_derive_ms = Ms.isna() & Rs.notna() & logg.notna()
    if bool(can_derive_ms.any()):
        g_m_s2 = np.power(10.0, logg.loc[can_derive_ms].astype(float)) * 0.01
        mass_from_logg_radius.loc[can_derive_ms] = g_m_s2 * np.square(Rs.loc[can_derive_ms].astype(float) * R_SUN_M) / g_reference_si / M_SUN_KG_LOCAL
    Ms_eff = Ms.copy()
    Ms_eff.loc[can_derive_ms] = mass_from_logg_radius.loc[can_derive_ms]
    out["stellar_mass_solar_effective"] = Ms_eff
    out["stellar_mass_source"] = np.where(Ms.notna(), "OBSERVED", np.where(can_derive_ms, "DERIVED_LOGG_RADIUS", "NOT_OBSERVED"))

    # Frozen relation a^3 / (P^2 M*) = C_hat.  It may infer ONE missing orbital coordinate.
    obs_triplet = P.notna() & a.notna() & Ms.notna()
    infer_a = P.notna() & a.isna() & Ms_eff.notna()
    infer_P = P.isna() & a.notna() & Ms_eff.notna()
    infer_M = P.notna() & a.notna() & Ms_eff.isna()

    P_eff = P.copy()
    a_eff = a.copy()
    Ms_orbit_eff = Ms_eff.copy()
    if bool(infer_a.any()):
        p_si = P.loc[infer_a].astype(float) * DAY_S
        m_si = Ms_eff.loc[infer_a].astype(float) * M_SUN_KG
        a_eff.loc[infer_a] = np.cbrt(frozen_c_hat_si * np.square(p_si) * m_si) / AU_M
    if bool(infer_P.any()):
        a_si = a.loc[infer_P].astype(float) * AU_M
        m_si = Ms_eff.loc[infer_P].astype(float) * M_SUN_KG
        P_eff.loc[infer_P] = np.sqrt(np.power(a_si, 3) / (frozen_c_hat_si * m_si)) / DAY_S
    if bool(infer_M.any()):
        a_si = a.loc[infer_M].astype(float) * AU_M
        p_si = P.loc[infer_M].astype(float) * DAY_S
        Ms_orbit_eff.loc[infer_M] = np.power(a_si, 3) / (frozen_c_hat_si * np.square(p_si)) / M_SUN_KG

    status = pd.Series("INSUFFICIENT_ORBITAL_OBSERVATIONS", index=raw.index, dtype=object)
    status.loc[obs_triplet] = "OBSERVED_P_A_MSTAR"
    status.loc[infer_a & Ms.notna()] = "MODEL_INFERRED_A_FROM_P_MSTAR"
    status.loc[infer_P & Ms.notna()] = "MODEL_INFERRED_P_FROM_A_MSTAR"
    status.loc[infer_M] = "MODEL_INFERRED_MSTAR_FROM_P_A"
    status.loc[infer_a & can_derive_ms] = "TWO_STAGE_INFERRED_MSTAR_THEN_A"
    status.loc[infer_P & can_derive_ms] = "TWO_STAGE_INFERRED_MSTAR_THEN_P"
    out["orbital_status"] = status
    out["orbital_period_days_effective"] = P_eff
    out["semimajor_axis_au_effective"] = a_eff
    out["orbital_stellar_mass_solar_effective"] = Ms_orbit_eff
    orbital_calculable = P_eff.notna() & a_eff.notna() & Ms_orbit_eff.notna()
    out["orbital_calculable"] = orbital_calculable

    # Only observed triplets are allowed to measure closure error; inferred triplets would be tautological.
    out["G_hat_star_only_SI"] = np.nan
    out["log_G_ratio_star_only"] = np.nan
    if bool(obs_triplet.any()):
        p_si = P.loc[obs_triplet].astype(float) * DAY_S
        a_si = a.loc[obs_triplet].astype(float) * AU_M
        m_si = Ms.loc[obs_triplet].astype(float) * M_SUN_KG
        ghat = 4.0 * math.pi**2 * np.power(a_si, 3) / np.square(p_si) / m_si
        out.loc[obs_triplet, "G_hat_star_only_SI"] = ghat
        out.loc[obs_triplet, "log_G_ratio_star_only"] = np.log(ghat / g_reference_si)

    two_body = obs_triplet & Mp.notna()
    out["planet_to_star_mass_ratio"] = np.nan
    out["G_hat_two_body_SI"] = np.nan
    out["log_G_ratio_two_body"] = np.nan
    if bool(two_body.any()):
        p_si = P.loc[two_body].astype(float) * DAY_S
        a_si = a.loc[two_body].astype(float) * AU_M
        ms_si = Ms.loc[two_body].astype(float) * M_SUN_KG
        mp_si = Mp.loc[two_body].astype(float) * 5.9722e24
        q = mp_si / ms_si
        g2 = 4.0 * math.pi**2 * np.power(a_si, 3) / np.square(p_si) / (ms_si + mp_si)
        out.loc[two_body, "planet_to_star_mass_ratio"] = q
        out.loc[two_body, "G_hat_two_body_SI"] = g2
        out.loc[two_body, "log_G_ratio_two_body"] = np.log(g2 / g_reference_si)

    # Planet structure: completely independent of orbital completeness.
    planet_structure = Mp.notna() & Rp.notna()
    out["planet_density_earth"] = np.nan
    out["planet_density_g_cm3"] = np.nan
    out["planet_surface_gravity_earth"] = np.nan
    out["planet_escape_velocity_earth"] = np.nan
    if bool(planet_structure.any()):
        m = Mp.loc[planet_structure].astype(float)
        r = Rp.loc[planet_structure].astype(float)
        rho_rel = m / np.power(r, 3)
        out.loc[planet_structure, "planet_density_earth"] = rho_rel
        out.loc[planet_structure, "planet_density_g_cm3"] = rho_rel * 5.514
        out.loc[planet_structure, "planet_surface_gravity_earth"] = m / np.square(r)
        out.loc[planet_structure, "planet_escape_velocity_earth"] = np.sqrt(m / r)
    density_flags, density_thresholds = _robust_log_outlier(out["planet_density_earth"])
    out["flag_extreme_density_robust"] = density_flags
    # Preserve an explicit audit of the pre-v2 mistake: raw limit values used as
    # point masses/radii. This is diagnostic only and never enters physics fits.
    raw_mp_for_audit = _positive_numeric(raw, "pl_bmasse")
    raw_rp_for_audit = _positive_numeric(raw, "pl_rade")
    legacy_density_earth = raw_mp_for_audit / np.power(raw_rp_for_audit, 3)
    legacy_density_flags, _legacy_density_thresholds = _robust_log_outlier(legacy_density_earth)
    out["planet_density_lower_g_cm3"] = np.nan
    out["planet_density_upper_g_cm3"] = np.nan
    out["planet_density_audit_class"] = "NOT_CANDIDATE"
    raw_mp = _positive_numeric(raw, "pl_bmasse")
    raw_rp = _positive_numeric(raw, "pl_rade")
    mass_limit = _limit_flag(raw, "pl_bmasse") != 0
    radius_limit = _limit_flag(raw, "pl_rade") != 0
    censored_structure = raw_mp.notna() & raw_rp.notna() & (mass_limit | radius_limit)
    out.loc[censored_structure, "planet_density_audit_class"] = "INPUT_LIMIT_NOT_PHYSICAL_POINT"
    if "pl_bmasseerr1" in raw.columns and "pl_bmasseerr2" in raw.columns and "pl_radeerr1" in raw.columns and "pl_radeerr2" in raw.columns:
        me1 = pd.to_numeric(raw["pl_bmasseerr1"], errors="coerce")
        me2 = pd.to_numeric(raw["pl_bmasseerr2"], errors="coerce")
        re1 = pd.to_numeric(raw["pl_radeerr1"], errors="coerce")
        re2 = pd.to_numeric(raw["pl_radeerr2"], errors="coerce")
        uncertainty_ok = planet_structure & me1.notna() & me2.notna() & re1.notna() & re2.notna()
        mlo = (Mp + me2).where((Mp + me2) > 0)
        mhi = (Mp + me1).where((Mp + me1) > 0)
        rlo = (Rp + re2).where((Rp + re2) > 0)
        rhi = (Rp + re1).where((Rp + re1) > 0)
        out.loc[uncertainty_ok, "planet_density_lower_g_cm3"] = (mlo.loc[uncertainty_ok] / np.power(rhi.loc[uncertainty_ok], 3)) * 5.514
        out.loc[uncertainty_ok, "planet_density_upper_g_cm3"] = (mhi.loc[uncertainty_ok] / np.power(rlo.loc[uncertainty_ok], 3)) * 5.514
    out.loc[density_flags, "planet_density_audit_class"] = "CENTRAL_EXTREME_REQUIRES_PROVENANCE"
    density_upper = pd.to_numeric(out["planet_density_upper_g_cm3"], errors="coerce")
    density_lower = pd.to_numeric(out["planet_density_lower_g_cm3"], errors="coerce")
    # If the uncertainty interval spans the robust central-population upper boundary,
    # the central extreme is not a robust point anomaly.
    density_hi_g = float(density_thresholds.get("upper", math.nan)) * 5.514
    unresolved_unc = density_flags & density_lower.notna() & np.isfinite(density_hi_g) & (density_lower <= density_hi_g)
    out.loc[unresolved_unc, "planet_density_audit_class"] = "UNCERTAINTY_UNRESOLVED"

    # Candidate DEFENSE: censored values are inequality constraints, not discarded
    # rows.  Propagate the full allowed mass/radius region into a density interval.
    # This distinguishes an effect that is REQUIRED by observations from one that
    # is merely ALLOWED (and therefore must remain a live research candidate).
    mass_constraint_lo, mass_constraint_hi, _ = _constraint_interval(
        raw, "pl_bmasse", positive=True, true_mass_from_best_mass=True
    )
    radius_constraint_lo, radius_constraint_hi, _ = _constraint_interval(raw, "pl_rade", positive=True)
    out["planet_true_mass_constraint_lower_earth"] = mass_constraint_lo
    out["planet_true_mass_constraint_upper_earth"] = mass_constraint_hi
    out["planet_radius_constraint_lower_earth"] = radius_constraint_lo
    out["planet_radius_constraint_upper_earth"] = radius_constraint_hi
    density_constraint_valid = (
        mass_constraint_lo.notna() & mass_constraint_hi.notna()
        & radius_constraint_lo.notna() & radius_constraint_hi.notna()
        & (radius_constraint_hi > 0) & (radius_constraint_lo > 0)
    )
    density_constraint_lo = pd.Series(np.nan, index=raw.index, dtype=float)
    density_constraint_hi = pd.Series(np.nan, index=raw.index, dtype=float)
    density_constraint_lo.loc[density_constraint_valid] = (
        mass_constraint_lo.loc[density_constraint_valid].astype(float)
        / np.power(radius_constraint_hi.loc[density_constraint_valid].astype(float), 3)
    ) * 5.514
    density_constraint_hi.loc[density_constraint_valid] = (
        mass_constraint_hi.loc[density_constraint_valid].astype(float)
        / np.power(radius_constraint_lo.loc[density_constraint_valid].astype(float), 3)
    ) * 5.514
    out["planet_density_constraint_lower_g_cm3"] = density_constraint_lo
    out["planet_density_constraint_upper_g_cm3"] = density_constraint_hi
    out["planet_density_candidate_defense"] = "INSUFFICIENT_CONSTRAINTS"
    if math.isfinite(density_hi_g):
        forced = density_constraint_valid & (density_constraint_lo > density_hi_g)
        allowed = density_constraint_valid & ~forced & (density_constraint_hi >= density_hi_g)
        excluded = density_constraint_valid & (density_constraint_hi < density_hi_g)
        out.loc[forced, "planet_density_candidate_defense"] = "EXTREME_REQUIRED_BY_CONSTRAINTS"
        out.loc[allowed, "planet_density_candidate_defense"] = "EXTREME_ALLOWED_BY_CONSTRAINTS"
        out.loc[excluded, "planet_density_candidate_defense"] = "EXTREME_EXCLUDED_BY_CONSTRAINTS"

    # Stellar structure cross-check.
    stellar_structure = Ms.notna() & Rs.notna()
    out["stellar_density_solar"] = np.nan
    out["stellar_logg_predicted_cgs"] = np.nan
    out["stellar_logg_delta_dex"] = np.nan
    if bool(stellar_structure.any()):
        out.loc[stellar_structure, "stellar_density_solar"] = Ms.loc[stellar_structure].astype(float) / np.power(Rs.loc[stellar_structure].astype(float), 3)
        logg_sun = math.log10(g_reference_si * M_SUN_KG / (R_SUN_M**2) * 100.0)
        pred_logg = logg_sun + np.log10(Ms.loc[stellar_structure].astype(float) / np.square(Rs.loc[stellar_structure].astype(float)))
        out.loc[stellar_structure, "stellar_logg_predicted_cgs"] = pred_logg
        have_logg = stellar_structure & logg.notna()
        out.loc[have_logg, "stellar_logg_delta_dex"] = logg.loc[have_logg].astype(float) - out.loc[have_logg, "stellar_logg_predicted_cgs"].astype(float)

    # Irradiation/equilibrium checks use observed semimajor axis only for data-consistency testing.
    T_SUN_K = 5772.0
    R_SUN_AU = R_SUN_M / AU_M
    irradiation = Teff.notna() & Rs.notna() & a.notna()
    out["insolation_model_earth"] = np.nan
    out["insolation_catalog_model_ratio"] = np.nan
    out["effective_stellar_luminosity_from_insolation_solar"] = np.nan
    out["stellar_luminosity_from_radius_temperature_solar"] = np.nan
    out["stellar_luminosity_representation_ratio"] = np.nan
    out["equilibrium_temperature_model_K"] = np.nan
    out["equilibrium_temperature_catalog_model_ratio"] = np.nan
    if bool(irradiation.any()):
        smodel = np.square(Rs.loc[irradiation].astype(float)) * np.power(Teff.loc[irradiation].astype(float) / T_SUN_K, 4) / np.square(a.loc[irradiation].astype(float))
        tmodel = Teff.loc[irradiation].astype(float) * np.sqrt((Rs.loc[irradiation].astype(float) * R_SUN_AU) / (2.0 * a.loc[irradiation].astype(float)))
        out.loc[irradiation, "insolation_model_earth"] = smodel
        out.loc[irradiation, "equilibrium_temperature_model_K"] = tmodel
        have_i = irradiation & insol.notna()
        have_t = irradiation & eqt.notna()
        out.loc[have_i, "insolation_catalog_model_ratio"] = insol.loc[have_i].astype(float) / out.loc[have_i, "insolation_model_earth"].astype(float)
        out.loc[have_i, "effective_stellar_luminosity_from_insolation_solar"] = insol.loc[have_i].astype(float) * np.square(a.loc[have_i].astype(float))
        out.loc[irradiation, "stellar_luminosity_from_radius_temperature_solar"] = np.square(Rs.loc[irradiation].astype(float)) * np.power(Teff.loc[irradiation].astype(float) / T_SUN_K, 4)
        out.loc[have_i, "stellar_luminosity_representation_ratio"] = (
            out.loc[have_i, "effective_stellar_luminosity_from_insolation_solar"].astype(float)
            / out.loc[have_i, "stellar_luminosity_from_radius_temperature_solar"].astype(float)
        )
        out.loc[have_t, "equilibrium_temperature_catalog_model_ratio"] = eqt.loc[have_t].astype(float) / out.loc[have_t, "equilibrium_temperature_model_K"].astype(float)
    insol_flags, insol_thresholds = _robust_log_outlier(out["insolation_catalog_model_ratio"])
    teq_flags, teq_thresholds = _robust_log_outlier(out["equilibrium_temperature_catalog_model_ratio"])
    out["flag_extreme_insolation_consistency_robust"] = insol_flags
    out["flag_extreme_temperature_consistency_robust"] = teq_flags

    # Provenance/regime audit for irradiation candidates. Q=1 means the S and Teq
    # discrepancies are mutually coherent under zero-albedo blackbody scaling;
    # Q~1/(1-A) with A~0.3 is compatible with a common literature convention.
    tratio = pd.to_numeric(out["equilibrium_temperature_catalog_model_ratio"], errors="coerce")
    sratio = pd.to_numeric(out["insolation_catalog_model_ratio"], errors="coerce")
    qratio = sratio / np.power(tratio, 4)
    out["irradiation_consistency_Q"] = qratio
    out["effective_albedo_like"] = 1.0 - (1.0 / qratio)
    tlo3, thi3 = _robust_positive_bounds(tratio, sigma_multiple=3.0)
    flagged_i = insol_flags
    t_normal = tratio.between(tlo3, thi3, inclusive="both")
    q_zero = qratio.between(0.8, 1.2, inclusive="both")
    q_a03 = qratio.between((1.0 / 0.7) * 0.8, (1.0 / 0.7) * 1.2, inclusive="both")
    out["irradiation_audit_class"] = "NOT_CANDIDATE"
    out.loc[flagged_i & t_normal, "irradiation_audit_class"] = "COMPOSITE_INSOLATION_ONLY_MISMATCH"
    out.loc[flagged_i & ~t_normal & q_zero, "irradiation_audit_class"] = "COHERENT_SOURCE_SCALE_ZERO_ALBEDO_LIKE"
    out.loc[flagged_i & ~t_normal & ~q_zero & q_a03, "irradiation_audit_class"] = "COHERENT_LITERATURE_A03_LIKE"
    if "sy_snum" in raw.columns:
        multi = pd.to_numeric(raw["sy_snum"], errors="coerce") > 1
        out.loc[flagged_i & ~t_normal & ~q_zero & ~q_a03 & multi, "irradiation_audit_class"] = "MULTISTAR_OR_PROVENANCE_UNRESOLVED"
    unresolved_i = flagged_i & out["irradiation_audit_class"].eq("NOT_CANDIDATE")
    out.loc[unresolved_i, "irradiation_audit_class"] = "OTHER_PROVENANCE_OR_CONVENTION"

    # Repeated near-identical discrepancy factors inside one host are a host/source
    # signature rather than evidence for a planet-specific new law.
    out["host_shared_insolation_factor_candidate"] = False
    cand = out.loc[flagged_i & sratio.notna(), ["hostname", "insolation_catalog_model_ratio"]].copy()
    for host, grp in cand.groupby("hostname"):
        vals = pd.to_numeric(grp["insolation_catalog_model_ratio"], errors="coerce").dropna().to_numpy(float)
        if len(vals) >= 2 and float(np.max(vals) / np.min(vals)) <= 1.10:
            out.loc[grp.index, "host_shared_insolation_factor_candidate"] = True

    # Candidate DEFENSE for irradiation/thermal structure.  Instead of treating a
    # point mismatch as a rejection, propagate measurement uncertainties and
    # one-sided limits through the physical model.  Also preserve coherent
    # multi-planet host scale factors as research-local latent-axis candidates.
    rs_lo, rs_hi, _ = _constraint_interval(raw, "st_rad", positive=True)
    teff_lo, teff_hi, _ = _constraint_interval(raw, "st_teff", positive=True)
    a_lo, a_hi, _ = _constraint_interval(raw, "pl_orbsmax", positive=True)
    insol_lo, insol_hi, _ = _constraint_interval(raw, "pl_insol", positive=True)
    eqt_lo, eqt_hi, _ = _constraint_interval(raw, "pl_eqt", positive=True)

    irradiation_constraint_valid = (rs_lo.notna() & rs_hi.notna() & teff_lo.notna() & teff_hi.notna() & a_lo.notna() & a_hi.notna() & (a_lo > 0) & (a_hi > 0))
    smodel_lo = pd.Series(np.nan, index=raw.index, dtype=float)
    smodel_hi = pd.Series(np.nan, index=raw.index, dtype=float)
    tmodel_lo = pd.Series(np.nan, index=raw.index, dtype=float)
    tmodel_hi = pd.Series(np.nan, index=raw.index, dtype=float)
    ii = irradiation_constraint_valid
    smodel_lo.loc[ii] = (
        np.square(rs_lo.loc[ii].astype(float))
        * np.power(teff_lo.loc[ii].astype(float) / T_SUN_K, 4)
        / np.square(a_hi.loc[ii].astype(float))
    )
    smodel_hi.loc[ii] = (
        np.square(rs_hi.loc[ii].astype(float))
        * np.power(teff_hi.loc[ii].astype(float) / T_SUN_K, 4)
        / np.square(a_lo.loc[ii].astype(float))
    )
    tmodel_lo.loc[ii] = teff_lo.loc[ii].astype(float) * np.sqrt((rs_lo.loc[ii].astype(float) * R_SUN_AU) / (2.0 * a_hi.loc[ii].astype(float)))
    tmodel_hi.loc[ii] = teff_hi.loc[ii].astype(float) * np.sqrt((rs_hi.loc[ii].astype(float) * R_SUN_AU) / (2.0 * a_lo.loc[ii].astype(float)))
    out["insolation_model_constraint_lower_earth"] = smodel_lo
    out["insolation_model_constraint_upper_earth"] = smodel_hi
    out["equilibrium_temperature_model_constraint_lower_K"] = tmodel_lo
    out["equilibrium_temperature_model_constraint_upper_K"] = tmodel_hi
    out["insolation_candidate_interval_overlap"] = _interval_overlap(insol_lo, insol_hi, smodel_lo, smodel_hi)

    # T0 above is the full-redistribution, zero-albedo equilibrium temperature.
    # Generic radiative equilibrium allows T/T0 = [4(1-A)/n]^(1/4), with
    # 0<=A<=1 and 1<=n<=4.  Thus 0 < (T/T0)^4 <= 4 without invoking
    # internal luminosity or an additional star.  This is a defense envelope,
    # not a fitted explanation.
    thermal_envelope_hi = (4.0 ** 0.25) * tmodel_hi
    thermal_defensible = eqt_lo.notna() & thermal_envelope_hi.notna() & (eqt_lo <= thermal_envelope_hi)
    out["thermal_balance_candidate_defensible"] = thermal_defensible
    out["thermal_balance_phi_central"] = np.power(tratio, 4)

    out["host_latent_insolation_scale"] = np.nan
    out["host_latent_insolation_scale_cv"] = np.nan
    out["host_latent_scale_thermal_Q"] = np.nan
    out["host_latent_scale_candidate"] = False
    shared_rows = out["host_shared_insolation_factor_candidate"].astype(bool) & sratio.notna()
    for host, grp in out.loc[shared_rows, ["hostname", "insolation_catalog_model_ratio", "irradiation_consistency_Q"]].groupby("hostname"):
        vals = pd.to_numeric(grp["insolation_catalog_model_ratio"], errors="coerce").dropna().to_numpy(float)
        qvals = pd.to_numeric(grp["irradiation_consistency_Q"], errors="coerce").dropna().to_numpy(float)
        if len(vals) < 2:
            continue
        mean = float(np.mean(vals))
        cv = float(np.std(vals, ddof=1) / mean) if len(vals) > 1 and mean != 0 else 0.0
        qmed = float(np.median(qvals)) if len(qvals) else math.nan
        out.loc[grp.index, "host_latent_insolation_scale"] = float(np.median(vals))
        out.loc[grp.index, "host_latent_insolation_scale_cv"] = cv
        out.loc[grp.index, "host_latent_scale_thermal_Q"] = qmed
        out.loc[grp.index, "host_latent_scale_candidate"] = True

    out["irradiation_candidate_defense"] = "NOT_CANDIDATE"
    out.loc[flagged_i, "irradiation_candidate_defense"] = "OPEN_CANDIDATE"
    out.loc[flagged_i & out["insolation_candidate_interval_overlap"], "irradiation_candidate_defense"] = "DEFENDED_BY_OBSERVATIONAL_INTERVAL"
    host_latent = flagged_i & out["host_latent_scale_candidate"].astype(bool)
    host_q = pd.to_numeric(out["host_latent_scale_thermal_Q"], errors="coerce")
    out.loc[host_latent, "irradiation_candidate_defense"] = "SUPPORTED_HOST_LATENT_SCALE"
    out.loc[host_latent & host_q.between(0.8, 1.2, inclusive="both"), "irradiation_candidate_defense"] = "DEFENDED_HOST_LATENT_SCALE_THERMALLY_COHERENT"
    if "sy_snum" in raw.columns:
        multi = pd.to_numeric(raw["sy_snum"], errors="coerce") > 1
        higher_flux = sratio > 1
        out.loc[flagged_i & multi & higher_flux & out["irradiation_candidate_defense"].eq("OPEN_CANDIDATE"), "irradiation_candidate_defense"] = "SUPPORTED_MULTISTAR_FLUX_CANDIDATE"

    out["thermal_candidate_defense"] = "NO_THERMAL_OBSERVATION"
    have_thermal = eqt_lo.notna() & tmodel_hi.notna()
    out.loc[have_thermal, "thermal_candidate_defense"] = "OPEN_THERMAL_CANDIDATE"
    out.loc[have_thermal & thermal_defensible, "thermal_candidate_defense"] = "DEFENDED_BY_ALBEDO_REDISTRIBUTION_ENVELOPE"
    if "discoverymethod" in raw.columns:
        direct = raw["discoverymethod"].astype(str).eq("Imaging")
        out.loc[have_thermal & direct, "thermal_candidate_defense"] = "DEFENDED_DIRECT_IMAGING_INTERNAL_LUMINOSITY_REGIME"

    # Orbit geometry is available independently of P and M* if a and e are observed.
    eccentric_orbit = a.notna() & ecc.notna() & (ecc >= 0) & (ecc < 1)
    out["periastron_au"] = np.nan
    out["apastron_au"] = np.nan
    out.loc[eccentric_orbit, "periastron_au"] = a.loc[eccentric_orbit].astype(float) * (1.0 - ecc.loc[eccentric_orbit].astype(float))
    out.loc[eccentric_orbit, "apastron_au"] = a.loc[eccentric_orbit].astype(float) * (1.0 + ecc.loc[eccentric_orbit].astype(float))

    # Availability zones.  Each row is preserved even when no particular zone applies.
    zones = pd.DataFrame(index=raw.index)
    zones["ORBITAL_OBSERVED_CLOSURE"] = obs_triplet
    zones["ORBITAL_MODEL_ASSISTED"] = orbital_calculable & ~obs_triplet
    zones["PLANET_STRUCTURE"] = planet_structure
    zones["STELLAR_STRUCTURE"] = stellar_structure
    zones["IRRADIATION_MODEL_CHECK"] = irradiation
    zones["ECCENTRIC_ORBIT_GEOMETRY"] = eccentric_orbit
    zones["CATALOGUE_CONTEXT"] = _finite_numeric(raw, "disc_year").notna() | _positive_numeric(raw, "sy_dist").notna()
    zones["UNCERTAINTY_ORBIT"] = obs_triplet & np.isfinite(safe_relerr(raw["pl_orbpererr1"], raw["pl_orbper"])) & np.isfinite(safe_relerr(raw["pl_orbsmaxerr1"], raw["pl_orbsmax"])) & np.isfinite(safe_relerr(raw["st_masserr1"], raw["st_mass"]))
    out["available_zone_count"] = zones.sum(axis=1).astype(int)
    out["available_zones"] = zones.apply(lambda row: ";".join([k for k, ok in row.items() if bool(ok)]), axis=1)
    out["deep_residual_maximal_subspace"] = out["available_axes"]
    out["deep_residual_axis_count"] = np.where(obs_triplet, out["available_axis_count"], 0).astype(int)
    out["deep_residual_eligible"] = obs_triplet & (out["available_axis_count"] > 0)

    status2 = pd.Series("IDENTITY_ONLY", index=raw.index, dtype=object)
    status2.loc[out["available_zone_count"] > 0] = "PARTIAL_OBSERVED_PHYSICS"
    status2.loc[orbital_calculable & ~obs_triplet] = "MODEL_ASSISTED_ORBITAL_PHYSICS"
    status2.loc[obs_triplet] = "OBSERVED_ORBITAL_PHYSICS"
    status2.loc[obs_triplet & (out["available_axis_count"] == len(DORMANT_AXES))] = "FULL_17_AXIS_OBSERVED_ORBITAL"
    out["passport_status"] = status2

    # Aggregate summaries and conservative consistency flags.
    zone_counts = {k: int(v.sum()) for k, v in zones.items()}
    axis_counts = {k: int(v.sum()) for k, v in axis_available.items()}
    orbital_status_counts = {str(k): int(v) for k, v in out["orbital_status"].value_counts().items()}
    passport_status_counts = {str(k): int(v) for k, v in out["passport_status"].value_counts().items()}
    axis_count_distribution = {str(int(k)): int(v) for k, v in out["available_axis_count"].value_counts().sort_index().items()}

    obs_g = pd.to_numeric(out.loc[obs_triplet, "log_G_ratio_star_only"], errors="coerce").dropna().to_numpy(float)
    two_g = pd.to_numeric(out.loc[two_body, "log_G_ratio_two_body"], errors="coerce").dropna().to_numpy(float)
    discovery_mask = raw["hostname"].map(host_split).eq("discovery") & obs_triplet
    availability_axis_scan = [
        _availability_axis_stability(
            out.loc[discovery_mask, "log_G_ratio_star_only"],
            pd.to_numeric(axis_values[name].loc[discovery_mask], errors="coerce"),
            raw.loc[discovery_mask, "hostname"],
            axis_name=name,
        )
        for name in DORMANT_AXES
    ]
    availability_axis_scan.sort(key=lambda row: (-int(bool(row.get("passes"))), -float(row.get("pooled_robust_margin", -math.inf)), -float(row.get("pooled_median_gain", -math.inf)), row["axis"]))

    # After provenance/regime cleaning, ask Atlas whether any non-tautological single
    # coordinate still explains the remaining insolation consistency residual.
    # Insolation and equilibrium-temperature axes themselves are excluded because they
    # directly participate in the target definition.
    clean_i = out["insolation_catalog_model_ratio"].notna() & ~out["flag_extreme_insolation_consistency_robust"]
    clean_target = _safe_log_positive(out["insolation_catalog_model_ratio"])
    irradiation_predictors = [name for name in DORMANT_AXES if name not in {"log_insolation_earth", "log_equilibrium_temperature_K"}]
    cleaned_scan: list[dict[str, Any]] = []
    discovery_clean = raw["hostname"].map(host_split).eq("discovery") & clean_i
    validation_clean = raw["hostname"].map(host_split).eq("validation") & clean_i
    for name in irradiation_predictors:
        row = _availability_axis_stability(
            clean_target.loc[discovery_clean],
            pd.to_numeric(axis_values[name].loc[discovery_clean], errors="coerce"),
            raw.loc[discovery_clean, "hostname"],
            axis_name=f"CLEAN-IRRADIATION::{name}",
        )
        row["original_axis"] = name
        row["outer_validation_gain"] = math.nan
        if bool(row.get("passes")):
            tr = discovery_clean & clean_target.notna() & pd.to_numeric(axis_values[name], errors="coerce").notna()
            va = validation_clean & clean_target.notna() & pd.to_numeric(axis_values[name], errors="coerce").notna()
            if int(tr.sum()) >= 100 and int(va.sum()) >= 20:
                xtr = pd.to_numeric(axis_values[name].loc[tr], errors="coerce").to_numpy(float)
                ytr = clean_target.loc[tr].to_numpy(float)
                xva = pd.to_numeric(axis_values[name].loc[va], errors="coerce").to_numpy(float)
                yva = clean_target.loc[va].to_numpy(float)
                beta, *_ = np.linalg.lstsq(np.column_stack([np.ones(len(xtr)), xtr]), ytr, rcond=None)
                den = float(np.std(yva))
                if den > 1e-14:
                    base = float(np.sqrt(np.mean(np.square(yva - float(np.mean(ytr))))) / den)
                    cand = float(np.sqrt(np.mean(np.square(yva - (float(beta[0]) + float(beta[1]) * xva)))) / den)
                    row["outer_validation_nrmse_baseline"] = base
                    row["outer_validation_nrmse_candidate"] = cand
                    row["outer_validation_gain"] = float((base - cand) / max(abs(base), 1e-30))
                    row["outer_validation_rows"] = int(va.sum())
        cleaned_scan.append(row)
    cleaned_scan.sort(key=lambda row: (-int(bool(row.get("passes"))), -float(row.get("pooled_robust_margin", -math.inf)), -float(row.get("pooled_median_gain", -math.inf)), row["original_axis"]))

    # Candidate DEFENSE must also ask whether a failed population-wide axis is
    # valid in a narrower observational regime.  This is not post-hoc rescue: the
    # regime label is frozen from the catalogue (discovery method), selection is
    # discovery-only, and validation is read only after the axis is selected.
    defense_axes = {name: pd.to_numeric(axis_values[name], errors="coerce") for name in irradiation_predictors}
    defense_axes["log_planet_density_proxy"] = pd.to_numeric(axis_values["log_planet_mass_earth"], errors="coerce") - 3.0 * pd.to_numeric(axis_values["log_planet_radius_earth"], errors="coerce")
    defense_axes["log_planet_surface_gravity_proxy"] = pd.to_numeric(axis_values["log_planet_mass_earth"], errors="coerce") - 2.0 * pd.to_numeric(axis_values["log_planet_radius_earth"], errors="coerce")
    regime_defense: list[dict[str, Any]] = []
    method_counts = raw.loc[clean_i & clean_target.notna(), "discoverymethod"].astype(str).value_counts()
    eligible_methods = [str(method) for method, count in method_counts.items() if int(count) >= 300]
    for method in eligible_methods:
        regime = raw["discoverymethod"].astype(str).eq(method) & clean_i
        regime_discovery = regime & raw["hostname"].map(host_split).eq("discovery")
        regime_validation = regime & raw["hostname"].map(host_split).eq("validation")
        for name, axis in defense_axes.items():
            stability = _availability_axis_stability(
                clean_target.loc[regime_discovery],
                axis.loc[regime_discovery],
                raw.loc[regime_discovery, "hostname"],
                axis_name=f"DEFENSE::{method}::{name}",
            )
            if not bool(stability.get("passes")):
                continue
            validation = _linear_candidate_outer_validation(clean_target, axis, regime_discovery, regime_validation)
            tail = _linear_candidate_tail_stress(clean_target, axis, regime_discovery)
            vg = float(validation.get("gain", math.nan))
            if math.isfinite(vg) and vg > 0 and bool(tail.get("passes")):
                defense_status = "DEFENDED_REGIME_LOCAL_TRANSFER_AND_TAIL"
            elif math.isfinite(vg) and vg > 0:
                defense_status = "DEFENDED_REGIME_LOCAL_TRANSFER_TAIL_LIMITED"
            else:
                defense_status = "DISCOVERY_STABLE_REGIME_CANDIDATE_OUTER_TRANSFER_NOT_YET_DEFENDED"
            host_scope = _within_host_scope_audit(
                clean_target, axis, raw["hostname"], regime_discovery, regime_validation
            )
            regime_defense.append({
                "regime_axis": "discoverymethod",
                "regime_value": method,
                "candidate_axis": name,
                "status": defense_status,
                "discovery_stability": stability,
                "tail_stress": tail,
                "outer_validation": validation,
                "within_host_scope_audit": host_scope,
                "candidate_scope": host_scope.get("status", "UNRESOLVED_SCOPE"),
                "canonical_or_causal_claim": False,
            })
    regime_defense.sort(key=lambda row: (
        -int(row["status"] == "DEFENDED_REGIME_LOCAL_TRANSFER_AND_TAIL"),
        -int(row["status"] == "DEFENDED_REGIME_LOCAL_TRANSFER_TAIL_LIMITED"),
        -float(row["discovery_stability"].get("pooled_robust_margin", -math.inf)),
        row["regime_value"], row["candidate_axis"],
    ))

    observed_mask = obs_triplet & out["log_G_ratio_star_only"].notna()
    full17_mask = observed_mask & (out["available_axis_count"] == len(DORMANT_AXES))
    nonfull_mask = observed_mask & ~full17_mask
    full17_abs = np.abs(pd.to_numeric(out.loc[full17_mask, "log_G_ratio_star_only"], errors="coerce").dropna().to_numpy(float))
    nonfull_abs = np.abs(pd.to_numeric(out.loc[nonfull_mask, "log_G_ratio_star_only"], errors="coerce").dropna().to_numpy(float))
    full17_med_abs = float(np.median(full17_abs)) if len(full17_abs) else math.nan
    nonfull_med_abs = float(np.median(nonfull_abs)) if len(nonfull_abs) else math.nan

    high_q_mask = two_body & (pd.to_numeric(out["planet_to_star_mass_ratio"], errors="coerce") > 0.01)
    high_q_star = pd.to_numeric(out.loc[high_q_mask, "log_G_ratio_star_only"], errors="coerce").dropna().to_numpy(float)
    high_q_two = pd.to_numeric(out.loc[high_q_mask, "log_G_ratio_two_body"], errors="coerce").dropna().to_numpy(float)

    summary = {
        "schema": "atlas-exoplanet-availability-adaptive-passports/v3",
        "rows_preserved": int(len(out)),
        "all_input_rows_preserved": bool(len(out) == len(raw)),
        "unique_planets": int(raw["pl_name"].nunique()),
        "unique_hosts": int(raw["hostname"].nunique()),
        "zone_counts": zone_counts,
        "axis_availability_counts": axis_counts,
        "available_axis_count_distribution": axis_count_distribution,
        "orbital_status_counts": orbital_status_counts,
        "passport_status_counts": passport_status_counts,
        "observed_orbital_closure_count": int(obs_triplet.sum()),
        "model_assisted_orbital_count": int((orbital_calculable & ~obs_triplet).sum()),
        "orbital_calculable_count": int(orbital_calculable.sum()),
        "orbital_unresolved_count": int((~orbital_calculable).sum()),
        "derived_stellar_mass_from_logg_radius_count": int(can_derive_ms.sum()),
        "full_17_axis_observed_orbital_count": int((obs_triplet & (out["available_axis_count"] == len(DORMANT_AXES))).sum()),
        "planet_structure_count": int(planet_structure.sum()),
        "extreme_density_robust_count": int(density_flags.sum()),
        "extreme_density_robust_thresholds": density_thresholds,
        "irradiation_consistency_count": int(out["insolation_catalog_model_ratio"].notna().sum()),
        "insolation_ratio_median": float(np.nanmedian(out["insolation_catalog_model_ratio"].to_numpy(float))),
        "extreme_insolation_consistency_robust_count": int(insol_flags.sum()),
        "insolation_ratio_robust_thresholds": insol_thresholds,
        "equilibrium_temperature_consistency_count": int(out["equilibrium_temperature_catalog_model_ratio"].notna().sum()),
        "equilibrium_temperature_ratio_median": float(np.nanmedian(out["equilibrium_temperature_catalog_model_ratio"].to_numpy(float))),
        "extreme_temperature_consistency_robust_count": int(teq_flags.sum()),
        "equilibrium_temperature_ratio_robust_thresholds": teq_thresholds,
        "limit_semantics": {
            "mass_limit_rows_catalogue": int((_limit_flag(raw, "pl_bmasse") != 0).sum()),
            "radius_limit_rows_catalogue": int((_limit_flag(raw, "pl_rade") != 0).sum()),
            "limits_used_as_central_values": False,
            "limits_preserved_as_inequality_constraints": True,
            "best_mass_msini_preserved_as_true_mass_lower_bound": True,
            "snapshot_limit_sign_semantics": {"+1": "UPPER_BOUND", "-1": "LOWER_BOUND", "0": "POINT_OR_UNCENSORED"},
        },
        "density_provenance_audit": {
            "candidate_class_counts": {str(k): int(v) for k, v in out.loc[(density_flags | censored_structure), "planet_density_audit_class"].value_counts().items()},
            "central_extreme_count_after_limit_filter": int(density_flags.sum()),
            "stress_robust_physical_extreme_count": int((density_flags & out["planet_density_audit_class"].eq("CENTRAL_EXTREME_REQUIRES_PROVENANCE")).sum()),
            "uncertainty_unresolved_extreme_count": int((density_flags & out["planet_density_audit_class"].eq("UNCERTAINTY_UNRESOLVED")).sum()),
            "censored_mass_or_radius_rows": int(censored_structure.sum()),
            "legacy_naive_extreme_count": int(legacy_density_flags.sum()),
            "candidate_defense_counts": {str(k): int(v) for k, v in out.loc[legacy_density_flags, "planet_density_candidate_defense"].value_counts().items()},
            "constraint_extreme_required_count": int((legacy_density_flags & out["planet_density_candidate_defense"].eq("EXTREME_REQUIRED_BY_CONSTRAINTS")).sum()),
            "constraint_extreme_allowed_count": int((legacy_density_flags & out["planet_density_candidate_defense"].eq("EXTREME_ALLOWED_BY_CONSTRAINTS")).sum()),
            "constraint_extreme_excluded_count": int((legacy_density_flags & out["planet_density_candidate_defense"].eq("EXTREME_EXCLUDED_BY_CONSTRAINTS")).sum()),
            "legacy_naive_extreme_reclassification": [
                {
                    "pl_name": str(out.loc[i, "pl_name"]),
                    "mass_limit_flag": float(out.loc[i, "planet_mass_limit_flag"]),
                    "radius_limit_flag": float(out.loc[i, "planet_radius_limit_flag"]),
                    "naive_density_g_cm3": float(legacy_density_earth.loc[i] * 5.514),
                    "reclassified_as": str(out.loc[i, "planet_density_audit_class"]),
                }
                for i in out.index[legacy_density_flags]
            ],
        },
        "irradiation_provenance_audit": {
            "candidate_class_counts": {str(k): int(v) for k, v in out.loc[insol_flags, "irradiation_audit_class"].value_counts().items()},
            "candidate_count": int(insol_flags.sum()),
            "unresolved_candidate_count": int((insol_flags & out["irradiation_audit_class"].isin(["OTHER_PROVENANCE_OR_CONVENTION", "MULTISTAR_OR_PROVENANCE_UNRESOLVED"])).sum()),
            "unresolved_candidates": [
                {
                    "pl_name": str(out.loc[i, "pl_name"]),
                    "hostname": str(out.loc[i, "hostname"]),
                    "audit_class": str(out.loc[i, "irradiation_audit_class"]),
                    "S_catalog_model_ratio": float(out.loc[i, "insolation_catalog_model_ratio"]),
                    "Teq_catalog_model_ratio": float(out.loc[i, "equilibrium_temperature_catalog_model_ratio"]) if math.isfinite(float(out.loc[i, "equilibrium_temperature_catalog_model_ratio"])) else None,
                    "Q": float(out.loc[i, "irradiation_consistency_Q"]) if math.isfinite(float(out.loc[i, "irradiation_consistency_Q"])) else None,
                }
                for i in out.index[insol_flags & out["irradiation_audit_class"].isin(["OTHER_PROVENANCE_OR_CONVENTION", "MULTISTAR_OR_PROVENANCE_UNRESOLVED"])]
            ],
            "host_shared_factor_rows": int((insol_flags & out["host_shared_insolation_factor_candidate"]).sum()),
            "host_shared_factor_hosts": int(out.loc[insol_flags & out["host_shared_insolation_factor_candidate"], "hostname"].nunique()),
            "candidate_defense_counts": {str(k): int(v) for k, v in out.loc[insol_flags, "irradiation_candidate_defense"].value_counts().items()},
            "observational_interval_defended_count": int((insol_flags & out["insolation_candidate_interval_overlap"]).sum()),
            "host_latent_scale_candidate_rows": int((insol_flags & out["host_latent_scale_candidate"]).sum()),
            "host_latent_scale_candidate_hosts": int(out.loc[insol_flags & out["host_latent_scale_candidate"], "hostname"].nunique()),
            "host_latent_scale_cv_median": float(pd.to_numeric(out.loc[insol_flags & out["host_latent_scale_candidate"], "host_latent_insolation_scale_cv"], errors="coerce").dropna().median()) if bool((insol_flags & out["host_latent_scale_candidate"]).any()) else math.nan,
            "host_latent_scale_thermally_coherent_rows": int((insol_flags & out["irradiation_candidate_defense"].eq("DEFENDED_HOST_LATENT_SCALE_THERMALLY_COHERENT")).sum()),
            "thermal_balance_defended_candidate_count": int((insol_flags & out["thermal_balance_candidate_defensible"]).sum()),
            "temperature_normal_3mad_bounds": [tlo3, thi3],
            "q_definition": "(S_catalog/S_model)/(Teq_catalog/Teq_model)^4",
            "cleaned_nonextreme_residual_scan": {
                "selection_population": "DISCOVERY_ONLY_CENTRAL_NONEXTREME_INSOLATION_ROWS_PER_AXIS_MAXIMAL_AVAILABILITY",
                "excluded_tautological_axes": ["log_insolation_earth", "log_equilibrium_temperature_K"],
                "passing_discovery_axis_count": int(sum(1 for row in cleaned_scan if bool(row.get("passes")))),
                "passing_and_outer_validation_positive_count": int(sum(1 for row in cleaned_scan if bool(row.get("passes")) and float(row.get("outer_validation_gain", math.nan)) > 0)),
                "axes": cleaned_scan,
            },
            "regime_local_candidate_defense": {
                "principle": "FAILED_GLOBAL_CANDIDATE_MAY_SURVIVE_IN_A_PREDECLARED_OBSERVATIONAL_REGIME",
                "regime_axis": "discoverymethod",
                "selection_uses_validation": False,
                "defended_transfer_and_tail_count": int(sum(1 for row in regime_defense if row["status"] == "DEFENDED_REGIME_LOCAL_TRANSFER_AND_TAIL")),
                "defended_transfer_tail_limited_count": int(sum(1 for row in regime_defense if row["status"] == "DEFENDED_REGIME_LOCAL_TRANSFER_TAIL_LIMITED")),
                "candidates": regime_defense,
            },
        },
        "star_only_log_G_residual_sd": float(np.std(obs_g, ddof=1)) if len(obs_g) > 1 else math.nan,
        "two_body_log_G_residual_sd": float(np.std(two_g, ddof=1)) if len(two_g) > 1 else math.nan,
        "two_body_rows": int(two_body.sum()),
        "two_body_relative_sd_reduction": float((np.std(obs_g, ddof=1) - np.std(two_g, ddof=1)) / np.std(obs_g, ddof=1)) if len(obs_g) > 1 and len(two_g) > 1 else math.nan,
        "high_mass_ratio_q_gt_0_01": {
            "count": int(high_q_mask.sum()),
            "star_only_median_abs_log_G_residual": float(np.median(np.abs(high_q_star))) if len(high_q_star) else math.nan,
            "two_body_median_abs_log_G_residual": float(np.median(np.abs(high_q_two))) if len(high_q_two) else math.nan,
            "star_only_sd_log_G_residual": float(np.std(high_q_star, ddof=1)) if len(high_q_star) > 1 else math.nan,
            "two_body_sd_log_G_residual": float(np.std(high_q_two, ddof=1)) if len(high_q_two) > 1 else math.nan,
        },
        "maximal_subspace_single_axis_stability": {
            "selection_population": "DISCOVERY_ONLY_OBSERVED_ORBITAL_ROWS_PER_AXIS_MAXIMAL_AVAILABILITY",
            "passing_axis_count": int(sum(1 for row in availability_axis_scan if bool(row.get("passes")))),
            "axes": availability_axis_scan,
        },
        "complete_case_selection_bias": {
            "full_17_axis_observed_count": int(full17_mask.sum()),
            "nonfull_observed_count": int(nonfull_mask.sum()),
            "full_17_axis_median_abs_log_G_residual": full17_med_abs,
            "nonfull_median_abs_log_G_residual": nonfull_med_abs,
            "nonfull_to_full_median_abs_ratio": float(nonfull_med_abs / full17_med_abs) if full17_med_abs > 0 else math.inf,
        },
        "candidate_attack_defense_contract": {
            "attack": "TRY_TO_FALSIFY_WITH_TRANSFER_TAIL_STRESS_AND_PROVENANCE_CONSISTENCY",
            "defense": "MAXIMIZE_CANDIDATE_CONSISTENCY_WITHIN_OBSERVATIONAL_INTERVALS_CENSORING_VALIDITY_DOMAINS_AND_PREDECLARED_REGIMES",
            "censored_observation_is_evidence": True,
            "failure_of_global_law_implies_local_candidate_rejected": False,
            "candidate_can_be_required_allowed_excluded_or_regime_local": True,
            "heldout_data_may_define_defense_after_selection": False,
        },
        "missing_observation_semantics": "NOT_OBSERVED_NE_NO_EFFECT_NE_EXCLUDED",
        "model_inference_semantics": "MODEL_INFERRED_NE_OBSERVED",
    }
    summary["digest"] = digest_payload(summary)
    return out, summary




def run(root: Path, csv_path: Path, *, passports_out: Path | None = None) -> dict[str, Any]:
    raw = pd.read_csv(csv_path, comment="#")
    missing = sorted(REQUIRED_COLUMNS - set(raw.columns))
    if missing:
        raise ValueError(f"required exoplanet columns missing: {missing}")
    table_kind = source_table_kind(raw)

    # Reuse the previously frozen positive-control search exactly; this file does not modify its runner.
    base = add_base_columns(raw)
    discovery = base[base["split"] == "discovery"]
    ranking: list[tuple[float, int, tuple[int, int, int], dict[str, float]]] = []
    for vector in candidate_vectors():
        score = closure_score(discovery, vector)
        ranking.append((score["rho"], sum(abs(e) for e in vector), vector, score))
    ranking.sort(key=lambda row: (row[0], row[1], row[2]))
    _, _, winner, winner_score = ranking[0]

    generated_dim = (3, -1, -2, 0, 0, 0, 0) if winner == (3, -2, -1) else (0, 0, 0, 0, 0, 0, 0)
    matches = registry_matches(root, generated_dim)
    g_match = next((m for m in matches if m.get("constant_id") == "CONST-G"), None)
    g_reference = float(g_match["value"]) if g_match is not None else 4.0 * math.pi**2 * float(winner_score["C_hat_SI"])

    passports, summary = build_availability_passports(
        raw, frozen_c_hat_si=float(winner_score["C_hat_SI"]), g_reference_si=g_reference
    )
    hierarchical_theory = build_hierarchical_exoplanet_theory(raw, passports, summary)
    next_experiment = LongHorizonBlindScientificCycleKernel(root).freeze_observational_round(
        theory=hierarchical_theory, cost_budget=2.0
    )
    if passports_out is not None:
        passports_out = Path(passports_out)
        passports_out.parent.mkdir(parents=True, exist_ok=True)
        passports.to_csv(passports_out, index=False)

    frozen_runner = root / "evaluation" / "exoplanet_nasa2026_blind_experiment.py"
    report = {
        "schema": "atlas-exoplanet-availability-adaptive/v3",
        "status": "FULL_CATALOGUE_AVAILABILITY_ADAPTIVE_PASS_EXECUTED",
        "source": {
            "path": str(csv_path),
            "sha256": sha256_file(csv_path),
            "table_kind": table_kind,
            "rows": int(len(raw)),
            "columns": int(len(raw.columns)),
        },
        "frozen_positive_control_binding": {
            "runner_sha256": sha256_file(frozen_runner),
            "winner_exponents": list(winner),
            "winner_C_hat_SI": float(winner_score["C_hat_SI"]),
            "winner_rho": float(winner_score["rho"]),
            "known_registry_used_for_winner_selection": False,
        },
        "availability_adaptive_passports": summary,
        "hierarchical_observational_theory": hierarchical_theory,
        "next_discriminating_experiment": next_experiment,
        "claim_boundary": {
            "all_input_rows_preserved": True,
            "model_inferred_values_are_observations": False,
            "consistency_outliers_are_new_physical_classes": False,
            "new_residual_law_claimed": False,
            "fresh_external_confirmation_used": False,
        },
    }
    report["digest"] = digest_payload(report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--out", default=None)
    parser.add_argument("--passports-out", default=None)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    csv_path = Path(args.csv).resolve()
    out = Path(args.out).resolve() if args.out else root / "reports" / "NASA_EXOPLANET_AVAILABILITY_ADAPTIVE_CURRENT.json"
    passports_out = Path(args.passports_out).resolve() if args.passports_out else root / "reports" / "NASA_EXOPLANET_AVAILABILITY_PASSPORTS_CURRENT.csv"
    report = run(root, csv_path, passports_out=passports_out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "status": report["status"],
        "rows": report["availability_adaptive_passports"]["rows_preserved"],
        "orbital_calculable": report["availability_adaptive_passports"]["orbital_calculable_count"],
        "orbital_unresolved": report["availability_adaptive_passports"]["orbital_unresolved_count"],
        "passing_single_axes": report["availability_adaptive_passports"]["maximal_subspace_single_axis_stability"]["passing_axis_count"],
        "hierarchical_theory_status": report["hierarchical_observational_theory"]["domain_status"],
        "host_validation_rmse_gain": report["hierarchical_observational_theory"]["layers"]["group_or_host_latent_state"]["leave_one_planet_out_prediction"]["validation"].get("rmse_relative_gain"),
        "frozen_runner_sha256": report["frozen_positive_control_binding"]["runner_sha256"],
        "report": str(out),
        "passports": str(passports_out),
        "digest": report["digest"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
