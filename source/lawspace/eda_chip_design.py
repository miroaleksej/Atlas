"""Atlas-native chip design-space research over a real external EDA world.

This owner does not reimplement synthesis, placement, routing, DRC or LVS.  It
binds the Atlas research/search layer to OpenROAD Flow Scripts (ORFS), freezes a
small CMOS design space before observations are read, parses machine metrics,
and compares equal-budget search policies.  If a real ORFS backend is absent it
fails closed rather than substituting an analytical/synthetic chip model.
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from scipy.stats import norm, qmc

from .query_research import QueryDrivenResearchOwner, _poly_design
from .schema import digest_payload

OWNER_ID = "EDA-CHIP-DESIGN-RESEARCH/1.0.0"
ZERO_DIMENSION = (0, 0, 0, 0, 0, 0, 0)
# Frozen external-world revision used by the shipped GitHub Actions pilot.
# The owner can also be pointed at another explicit ORFS checkout in a later,
# separately frozen experiment, but 15.26.0 never calls moving master itself.
ORFS_WORKFLOW_COMMIT = "be0dca0b1fd41df54792b3012350cd52bccd99bb"

# Small first-pilot surface.  All knobs are documented ORFS variables and are
# frozen before any EDA result is observed.  The ranges are intentionally
# conservative for sky130hd/gcd; an infeasible point is valid research evidence.
KNOBS: tuple[Mapping[str, Any], ...] = (
    {"name": "CORE_UTILIZATION", "kind": "int", "minimum": 20, "maximum": 50},
    {"name": "CORE_ASPECT_RATIO", "kind": "float", "minimum": 0.70, "maximum": 1.40},
    {"name": "PLACE_DENSITY", "kind": "float", "minimum": 0.55, "maximum": 0.80},
    {"name": "CTS_CLUSTER_SIZE", "kind": "int", "minimum": 10, "maximum": 60},
)


def _finite_number(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def _normalize_config(config: Mapping[str, Any]) -> dict[str, float | int]:
    out: dict[str, float | int] = {}
    for spec in KNOBS:
        name = str(spec["name"])
        if name not in config:
            raise ValueError(f"missing EDA knob {name}")
        raw = float(config[name])
        lo, hi = float(spec["minimum"]), float(spec["maximum"])
        if not (lo <= raw <= hi):
            raise ValueError(f"{name} outside frozen range [{lo},{hi}]")
        out[name] = int(round(raw)) if spec["kind"] == "int" else float(raw)
    return out


def _vector(config: Mapping[str, Any]) -> np.ndarray:
    vals = []
    for spec in KNOBS:
        lo, hi = float(spec["minimum"]), float(spec["maximum"])
        vals.append((float(config[str(spec["name"])]) - lo) / (hi - lo))
    return np.asarray(vals, dtype=float)


def _config_from_unit(row: Sequence[float]) -> dict[str, float | int]:
    out: dict[str, float | int] = {}
    for u, spec in zip(row, KNOBS):
        lo, hi = float(spec["minimum"]), float(spec["maximum"])
        x = lo + float(u) * (hi - lo)
        if spec["kind"] == "int":
            x = int(round(x))
        else:
            x = round(float(x), 6)
        out[str(spec["name"])] = x
    return out


def _unique_configs(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    out = []
    names = [str(x["name"]) for x in KNOBS]
    for row in rows:
        c = _normalize_config(row)
        key = tuple(c[n] for n in names)
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def _candidate_pool(size: int = 256, seed: int = 15260) -> list[dict[str, Any]]:
    """Frozen low-discrepancy candidate pool; no world metrics are consulted."""
    if int(size) < 64:
        raise ValueError("candidate pool must contain at least 64 points")
    sampler = qmc.Halton(d=len(KNOBS), scramble=True, seed=int(seed))
    rows = [_config_from_unit(x) for x in sampler.random(int(size) * 2)]
    out = _unique_configs(rows)
    if len(out) < int(size):
        # Integer knobs can create duplicates; deterministic grid fill closes it.
        grids = [np.linspace(0.0, 1.0, 7) for _ in KNOBS]
        import itertools
        out = _unique_configs(out + [_config_from_unit(x) for x in itertools.product(*grids)])
    return out[: int(size)]


def _maximin_seed(pool: Sequence[Mapping[str, Any]], count: int) -> list[dict[str, Any]]:
    """Deterministic space-filling common warm start shared by every strategy."""
    if int(count) < 12:
        raise ValueError("warm start must be at least 12 for the Atlas function-form lane")
    xs = np.vstack([_vector(c) for c in pool])
    chosen = [int(np.argmin(np.sum((xs - 0.5) ** 2, axis=1)))]
    while len(chosen) < int(count):
        dist = np.min(np.linalg.norm(xs[:, None, :] - xs[np.asarray(chosen)][None, :, :], axis=2), axis=1)
        dist[np.asarray(chosen)] = -1.0
        chosen.append(int(np.argmax(dist)))
    return [dict(pool[i]) for i in chosen]


def _read_clock_period_ns(sdc: Path) -> float | None:
    if not sdc.exists():
        return None
    text = sdc.read_text(encoding="utf-8", errors="ignore")
    # Supports either literal -period N or a local Tcl variable assigned first.
    m = re.search(r"create_clock[^\n]*?-period\s+([0-9]+(?:\.[0-9]+)?)", text)
    if m:
        return float(m.group(1))
    var = re.search(r"set\s+clk_period\s+([0-9]+(?:\.[0-9]+)?)", text)
    return float(var.group(1)) if var else None


def _flatten_metric_json(obj: Any, out: dict[str, Any]) -> None:
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            if isinstance(v, Mapping):
                _flatten_metric_json(v, out)
            else:
                out[str(k)] = v


def _metric(metrics: Mapping[str, Any], exact: Sequence[str], contains: Sequence[str] = ()) -> float | None:
    for key in exact:
        if key in metrics:
            v = _finite_number(metrics[key])
            if v is not None:
                return v
    if contains:
        tokens = tuple(x.lower() for x in contains)
        for key in sorted(metrics):
            low = key.lower()
            if all(t in low for t in tokens):
                v = _finite_number(metrics[key])
                if v is not None:
                    return v
    return None


def _parse_orfs_variant(flow_root: Path, *, platform: str, design: str, variant: str) -> Mapping[str, Any]:
    logs = flow_root / "logs" / platform / design / variant
    reports = flow_root / "reports" / platform / design / variant
    results = flow_root / "results" / platform / design / variant
    metrics: dict[str, Any] = {}
    metric_files = []
    if logs.exists():
        for p in sorted(logs.glob("*.json")):
            try:
                obj = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            _flatten_metric_json(obj, metrics)
            metric_files.append(str(p.relative_to(flow_root)))

    area = _metric(metrics, ("finish__design__instance__area",), ("finish", "design", "instance", "area"))
    power = _metric(metrics, ("finish__power__total", "finish__power__total__corner:nom_tt_025C_1v80"), ("finish", "power", "total"))
    ws = _metric(metrics, ("finish__timing__setup__ws",), ("finish", "timing", "setup", "ws"))
    setup_count = _metric(metrics, ("finish__timing__drv__setup_violation_count",), ("finish", "setup", "violation", "count"))
    route_drc = _metric(metrics, ("detailedroute__route__drc_errors",), ("detailedroute", "route", "drc", "errors"))

    # Keep route-stage DRC and sign-off DRC distinct.  The former is useful
    # diagnostic evidence but MUST NOT satisfy the final sign-off gate when
    # the explicit KLayout DRC receipt is absent.
    signoff_drc_count = None
    drc_count_path = reports / "6_drc_count.rpt"
    if drc_count_path.exists():
        try:
            signoff_drc_count = float(drc_count_path.read_text().strip().split()[0])
        except Exception:
            pass

    lvs_log = logs / "6_lvs.log"
    lvs_text = lvs_log.read_text(encoding="utf-8", errors="ignore") if lvs_log.exists() else ""
    low = lvs_text.lower()
    lvs_positive = any(x in low for x in ("netlists match", "circuits match uniquely", "comparison mode: pass"))
    lvs_negative = any(x in low for x in ("netlists don't match", "netlists do not match", "circuits do not match", "mismatch"))
    lvs_pass: bool | None
    if lvs_positive and not lvs_negative:
        lvs_pass = True
    elif lvs_negative:
        lvs_pass = False
    else:
        lvs_pass = None

    design_cfg = flow_root / "designs" / platform / design / "config.mk"
    sdc = flow_root / "designs" / platform / design / "constraint.sdc"
    clock_period = _read_clock_period_ns(sdc)
    if clock_period is None:
        clock_period = _metric(metrics, ("constraints__clocks__period",), ("constraints", "clock", "period"))
    delay = None if clock_period is None or ws is None else float(clock_period - ws)

    # Timing is fail-closed too: both worst setup slack and the setup
    # violation-count metric must be present.  A missing count cannot be
    # silently interpreted as zero violations.
    timing_pass = bool(ws is not None and ws >= 0.0 and setup_count is not None and setup_count <= 0.0)
    drc_pass = bool(signoff_drc_count is not None and signoff_drc_count <= 0.0)
    gds_present = any(results.glob("6_final.gds")) if results.exists() else False
    # Sign-off is deliberately fail-closed: a missing/ambiguous LVS receipt is not PASS.
    signoff_pass = timing_pass and drc_pass and lvs_pass is True and gds_present
    measurement_complete = (
        all(x is not None and x > 0.0 for x in (area, power, delay))
        and lvs_pass is not None
        and signoff_drc_count is not None
        and ws is not None
        and setup_count is not None
    )

    return {
        "status": "ORFS_MEASUREMENT_COMPLETE" if measurement_complete else "ORFS_MEASUREMENT_INCOMPLETE",
        "platform": platform,
        "design": design,
        "variant": variant,
        "metric_files": metric_files,
        "design_config_present": design_cfg.exists(),
        "metrics": {
            "area_um2": area,
            "power_w": power,
            "clock_period_ns": clock_period,
            "worst_setup_slack_ns": ws,
            "effective_critical_delay_ns": delay,
            "setup_violation_count": setup_count,
            "route_drc_error_count": route_drc,
            "signoff_drc_count": signoff_drc_count,
            "lvs_pass": lvs_pass,
        },
        "gates": {
            "timing_pass": timing_pass,
            "signoff_drc_pass": drc_pass,
            "lvs_pass": lvs_pass is True,
            "gds_present": gds_present,
            "all_signoff_gates_pass": bool(signoff_pass),
            "route_drc_is_signoff_substitute": False,
            "missing_setup_count_is_pass": False,
            "missing_signoff_drc_is_pass": False,
            "missing_lvs_is_pass": False,
        },
        "artifacts": {
            "gds_present": gds_present,
            "final_def_present": (results / "6_final.def").exists(),
            "lvs_database_present": (results / "6_lvs.lvsdb").exists(),
            "drc_report_present": (reports / "6_drc.lyrdb").exists(),
        },
    }


def _penalized_scores(rows: Sequence[Mapping[str, Any]], reference: Mapping[str, float]) -> np.ndarray:
    out = []
    for row in rows:
        m = row.get("measurement", {}).get("metrics", {})
        feasible = row.get("measurement", {}).get("gates", {}).get("all_signoff_gates_pass") is True
        area, power, delay = (_finite_number(m.get("area_um2")), _finite_number(m.get("power_w")), _finite_number(m.get("effective_critical_delay_ns")))
        if area and power and delay and all(reference[k] > 0 for k in ("area_um2", "power_w", "effective_critical_delay_ns")):
            logppa = (math.log(area / reference["area_um2"]) + math.log(power / reference["power_w"]) + math.log(delay / reference["effective_critical_delay_ns"])) / 3.0
            # Failed sign-off stays finite for modelling but can never be selected as a feasible winner.
            out.append(float(logppa + (0.0 if feasible else 8.0)))
        else:
            out.append(20.0)
    return np.asarray(out, dtype=float)


def _reference_from_warm(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, float]:
    keys = ("area_um2", "power_w", "effective_critical_delay_ns")
    out = {}
    for key in keys:
        vals = [_finite_number(r.get("measurement", {}).get("metrics", {}).get(key)) for r in rows]
        finite = [v for v in vals if v is not None and v > 0]
        if not finite:
            raise ValueError(f"no finite warm-start values for {key}")
        out[key] = float(np.median(finite))
    return out


def _raw_ppa(row: Mapping[str, Any]) -> float | None:
    m = row.get("measurement", {}).get("metrics", {})
    vals = [_finite_number(m.get(k)) for k in ("area_um2", "power_w", "effective_critical_delay_ns")]
    if any(v is None or v <= 0 for v in vals):
        return None
    return float(vals[0] * vals[1] * vals[2])


def _predict_atlas(observed: Sequence[Mapping[str, Any]], pool: Sequence[Mapping[str, Any]], reference: Mapping[str, float]) -> tuple[int, Mapping[str, Any]]:
    x = np.vstack([_vector(r["config"]) for r in observed])
    y = _penalized_scores(observed, reference)
    names = [str(s["name"]) for s in KNOBS]
    obs = {name: x[:, j] for j, name in enumerate(names)}
    obs["log_ppa_penalized"] = y
    dims = {name: ZERO_DIMENSION for name in names}
    dims["log_ppa_penalized"] = ZERO_DIMENSION
    fit = QueryDrivenResearchOwner().search_function_forms(
        observations=obs, dimensions=dims, target_name="log_ppa_penalized", axis_names=names,
        question="CMOS PPA/sign-off design-space acquisition", return_limit=10, hypothesis_budget=45,
        permutation_count=0,
    )
    hypotheses = fit.get("hypotheses", [])
    if not hypotheses:
        # Fail-safe remains geometry-driven, never a hidden-world oracle.
        xo = x
        xp = np.vstack([_vector(c) for c in pool])
        novelty = np.min(np.linalg.norm(xp[:, None, :] - xo[None, :, :], axis=2), axis=1)
        return int(np.argmax(novelty)), {"status": "ATLAS_GEOMETRIC_FALLBACK", "query_digest": fit.get("digest")}
    h = hypotheses[0]
    coords = [int(i) for i in h["coordinate_indices"]]
    xp = np.vstack([_vector(c) for c in pool])[:, coords]
    mu = np.asarray(h["standardization"]["mean"], float)
    scale = np.asarray(h["standardization"]["scale"], float)
    z = (xp - mu) / scale
    pred = _poly_design(z, h["monomial_exponents"]) @ np.asarray(h["coefficients"], float)
    xo = x
    novelty = np.min(np.linalg.norm(np.vstack([_vector(c) for c in pool])[:, None, :] - xo[None, :, :], axis=2), axis=1)
    acquisition = pred - 0.20 * novelty
    idx = int(np.argmin(acquisition))
    return idx, {
        "status": "ATLAS_QUERY_FUNCTION_FORM_ACQUISITION",
        "query_digest": fit.get("digest"),
        "rank1_signature": h.get("signature"),
        "rank1_cv_nrmse": h.get("cross_validated_nrmse"),
        "rank1_degree": h.get("polynomial_degree"),
        "rank1_coordinates": h.get("coordinate_indices"),
        "exploration_weight": 0.20,
    }


def _predict_bayes(observed: Sequence[Mapping[str, Any]], pool: Sequence[Mapping[str, Any]], reference: Mapping[str, float]) -> int:
    x = np.vstack([_vector(r["config"]) for r in observed])
    y = _penalized_scores(observed, reference)
    xp = np.vstack([_vector(c) for c in pool])
    # Fixed-hyperparameter GP baseline; no external ML dependency and no target peeking.
    length = 0.35
    noise = 1e-6
    def kernel(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        d2 = np.sum((a[:, None, :] - b[None, :, :]) ** 2, axis=2)
        return np.exp(-0.5 * d2 / (length * length))
    K = kernel(x, x) + noise * np.eye(len(x))
    try:
        L = np.linalg.cholesky(K)
        alpha = np.linalg.solve(L.T, np.linalg.solve(L, y))
        Ks = kernel(xp, x)
        mean = Ks @ alpha
        v = np.linalg.solve(L, Ks.T)
        var = np.maximum(1.0 - np.sum(v * v, axis=0), 1e-12)
    except np.linalg.LinAlgError:
        return int(np.argmin(np.min(np.linalg.norm(xp[:, None, :] - x[None, :, :], axis=2), axis=1)))
    std = np.sqrt(var)
    best = float(np.min(y))
    improvement = best - mean
    z = improvement / std
    ei = improvement * norm.cdf(z) + std * norm.pdf(z)
    return int(np.argmax(ei))


class EDAChipDesignResearchOwner:
    owner_id = OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        core = {
            "schema": "phi-eda-chip-design/v1",
            "owner": OWNER_ID,
            "status": "EDA_CHIP_DESIGN_RESEARCH_CONTRACT",
            "pilot": {
                "platform": "sky130hd", "design": "gcd",
                "world_backend": "OpenROAD Flow Scripts + Yosys + OpenROAD + KLayout",
                "workflow_orfs_git_commit": ORFS_WORKFLOW_COMMIT,
            },
            "frozen_knobs": [dict(x) for x in KNOBS],
            "world_outputs": ["area_um2", "power_w", "worst_setup_slack_ns", "effective_critical_delay_ns", "DRC", "LVS", "GDS"],
            "objective": {
                "feasible_only_winner": True,
                "raw_ppa": "area_um2 * power_w * effective_critical_delay_ns",
                "search_target": "mean(log(A/A_ref), log(P/P_ref), log(D/D_ref)) + infeasible_penalty",
                "reference": "median of common preregistered warm-start observations only",
            },
            "gates": {
                "timing": "worst_setup_slack_ns >= 0 and explicit setup_violation_count <= 0",
                "drc": "explicit sign-off 6_drc_count.rpt count == 0; route DRC is diagnostic only",
                "lvs": "explicit machine/log match required",
                "gds": "final 6_final.gds artifact must exist",
            },
            "comparison": {"strategies": ["ATLAS_QUERY_FUNCTION_FORM", "RANDOM", "GRID", "BAYESIAN_GP_EI"], "equal_budget": True, "common_warm_start": True},
            "claim_boundary": {
                "atlas_reimplements_synthesis_place_route": False,
                "missing_external_backend_is_chip_result": False,
                "synthetic_qualification_is_physical_chip_evidence": False,
                "timing_drc_lvs_or_gds_missing_is_pass": False,
                "route_drc_can_substitute_for_signoff_drc": False,
                "pilot_establishes_tapeout_readiness": False,
                "atlas_beats_baselines_without_live_equal_budget_run": False,
            },
        }
        return {**core, "digest": digest_payload(core)}

    def backend_status(self, *, orfs_flow_root: str | os.PathLike[str] | None = None, runner: str = "auto") -> Mapping[str, Any]:
        root = Path(orfs_flow_root or os.environ.get("ATLAS_ORFS_FLOW_ROOT", "")).expanduser() if (orfs_flow_root or os.environ.get("ATLAS_ORFS_FLOW_ROOT")) else None
        native = bool(shutil.which("openroad") and shutil.which("yosys") and shutil.which("klayout") and shutil.which("make"))
        docker = bool(shutil.which("docker"))
        docker_shell = bool(root and (root / "util" / "docker_shell").exists())
        flow_present = bool(root and (root / "Makefile").exists() and (root / "designs" / "sky130hd" / "gcd" / "config.mk").exists())
        if runner == "native": available = native and flow_present
        elif runner == "docker_shell": available = docker and docker_shell and flow_present
        else: available = flow_present and (native or (docker and docker_shell))
        orfs_git_commit = None
        orfs_git_dirty = None
        if root and root.exists() and shutil.which("git"):
            try:
                orfs_git_commit = subprocess.run(
                    ["git", "rev-parse", "HEAD"], cwd=str(root), text=True,
                    capture_output=True, timeout=10, check=False,
                ).stdout.strip() or None
                dirty_text = subprocess.run(
                    ["git", "status", "--porcelain", "--untracked-files=no"], cwd=str(root), text=True,
                    capture_output=True, timeout=10, check=False,
                ).stdout.strip()
                orfs_git_dirty = bool(dirty_text)
            except Exception:
                pass
        core = {
            "schema": "phi-eda-backend-status/v1", "owner": OWNER_ID,
            "status": "EDA_BACKEND_AVAILABLE" if available else "EDA_BACKEND_UNAVAILABLE",
            "orfs_flow_root": str(root.resolve()) if root and root.exists() else None,
            "flow_present": flow_present, "native_toolchain_present": native, "docker_present": docker,
            "orfs_docker_shell_present": docker_shell, "requested_runner": runner,
            "orfs_git_commit": orfs_git_commit, "orfs_git_dirty_tracked_files": orfs_git_dirty,
            "release_workflow_expected_orfs_git_commit": ORFS_WORKFLOW_COMMIT,
            "substitute_surrogate_used": False,
        }
        return {**core, "digest": digest_payload(core)}

    def evaluate(self, *, config: Mapping[str, Any], orfs_flow_root: str | os.PathLike[str] | None = None,
                 runner: str = "auto", timeout_seconds: int = 1800, variant_prefix: str = "atlas_eda") -> Mapping[str, Any]:
        cfg = _normalize_config(config)
        status = self.backend_status(orfs_flow_root=orfs_flow_root, runner=runner)
        if status["status"] != "EDA_BACKEND_AVAILABLE":
            core = {"schema": "phi-eda-world-evaluation/v1", "owner": OWNER_ID, "status": "BACKEND_UNAVAILABLE",
                    "config": cfg, "backend": status, "measurement": None, "surrogate_used": False}
            return {**core, "digest": digest_payload(core)}
        flow = Path(status["orfs_flow_root"])
        variant = f"{variant_prefix}_{digest_payload(cfg)[:12]}"
        args = ["make", "DESIGN_CONFIG=./designs/sky130hd/gcd/config.mk", f"FLOW_VARIANT={variant}"]
        args += [f"{k}={v}" for k, v in cfg.items()]
        args += ["all", "gds", "drc", "lvs"]
        selected_runner = runner
        if runner == "auto":
            selected_runner = "native" if status["native_toolchain_present"] else "docker_shell"
        cmd = args if selected_runner == "native" else [str(flow / "util" / "docker_shell"), *args]
        started = time.time()
        try:
            proc = subprocess.run(cmd, cwd=str(flow), text=True, capture_output=True, timeout=int(timeout_seconds), check=False)
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            proc = None
            timed_out = True
            stdout = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
            stderr = (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        else:
            stdout, stderr = proc.stdout, proc.stderr
        measurement = _parse_orfs_variant(flow, platform="sky130hd", design="gcd", variant=variant)
        return_code = None if proc is None else int(proc.returncode)
        successful_command = (return_code == 0 and not timed_out)
        core = {
            "schema": "phi-eda-world-evaluation/v1", "owner": OWNER_ID,
            "status": "EDA_WORLD_EVALUATION_COMPLETE" if successful_command else ("EDA_WORLD_EVALUATION_TIMEOUT" if timed_out else "EDA_WORLD_EVALUATION_FAILED"),
            "config": cfg, "backend": status, "runner": selected_runner, "variant": variant,
            "command": cmd, "return_code": return_code, "timed_out": timed_out,
            "elapsed_seconds": float(time.time() - started),
            "stdout_tail": stdout[-4000:], "stderr_tail": stderr[-4000:],
            "measurement": measurement, "surrogate_used": False,
        }
        return {**core, "digest": digest_payload(core)}

    def run_pilot(self, *, orfs_flow_root: str | os.PathLike[str] | None = None, runner: str = "auto",
                  evaluation_budget: int = 18, warm_start_count: int = 12, candidate_pool_size: int = 256,
                  seed: int = 15260, timeout_seconds: int = 1800,
                  evaluator: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
                  evaluator_kind: str = "LIVE_ORFS") -> Mapping[str, Any]:
        budget, warm_n = int(evaluation_budget), int(warm_start_count)
        if budget <= warm_n or warm_n < 12:
            raise ValueError("evaluation_budget must exceed warm_start_count >= 12")
        if budget > 40:
            raise ValueError("first-pilot equal-budget cap is 40 evaluations per strategy")
        pool = _candidate_pool(candidate_pool_size, seed=seed)
        warm = _maximin_seed(pool, warm_n)
        freeze = {
            "platform": "sky130hd", "design": "gcd", "knobs": [dict(x) for x in KNOBS],
            "candidate_pool": pool, "common_warm_start": warm, "evaluation_budget_per_strategy": budget,
            "strategies": ["ATLAS_QUERY_FUNCTION_FORM", "RANDOM", "GRID", "BAYESIAN_GP_EI"], "seed": int(seed),
        }
        freeze_digest = digest_payload(freeze)
        backend = self.backend_status(orfs_flow_root=orfs_flow_root, runner=runner) if evaluator is None else {
            "status": "INJECTED_QUALIFICATION_EVALUATOR", "surrogate_used": evaluator_kind != "LIVE_ORFS"
        }
        if evaluator is None and backend.get("status") != "EDA_BACKEND_AVAILABLE":
            core = {"schema": "phi-eda-chip-pilot/v1", "owner": OWNER_ID, "status": "CHIP_PILOT_BACKEND_UNAVAILABLE",
                    "research_freeze": {**freeze, "digest": freeze_digest}, "backend": backend,
                    "scientific_result": None, "baseline_comparison_performed": False,
                    "claim_boundary": {"chip_design_success_claimed": False, "surrogate_substitution_used": False}}
            return {**core, "digest": digest_payload(core)}

        cache: dict[str, Mapping[str, Any]] = {}
        def world(c: Mapping[str, Any]) -> Mapping[str, Any]:
            cfg = _normalize_config(c); key = digest_payload(cfg)
            if key not in cache:
                ev = evaluator(cfg) if evaluator is not None else self.evaluate(config=cfg, orfs_flow_root=orfs_flow_root, runner=runner, timeout_seconds=timeout_seconds)
                if evaluator is not None:
                    ev = dict(ev)
                    ev.setdefault("config", cfg)
                cache[key] = ev
            return cache[key]

        def observation(c: Mapping[str, Any]) -> Mapping[str, Any]:
            ev = world(c)
            measurement = ev.get("measurement") if isinstance(ev, Mapping) else None
            return {"config": dict(c), "world_evaluation_digest": ev.get("digest") if isinstance(ev, Mapping) else None,
                    "world_status": ev.get("status") if isinstance(ev, Mapping) else None,
                    "measurement": measurement or {"status": "MISSING", "metrics": {}, "gates": {"all_signoff_gates_pass": False}}}

        common = [observation(c) for c in warm]
        try:
            reference = _reference_from_warm(common)
        except ValueError as exc:
            core = {"schema": "phi-eda-chip-pilot/v1", "owner": OWNER_ID, "status": "CHIP_PILOT_WORLD_MEASUREMENTS_INCOMPLETE",
                    "research_freeze": {**freeze, "digest": freeze_digest}, "backend": backend,
                    "common_warm_start_results": common, "error": str(exc), "scientific_result": None,
                    "baseline_comparison_performed": False}
            return {**core, "digest": digest_payload(core)}

        names = [str(x["name"]) for x in KNOBS]
        warm_keys = {tuple(c[n] for n in names) for c in warm}
        remaining0 = [dict(c) for c in pool if tuple(c[n] for n in names) not in warm_keys]
        rng = np.random.default_rng(int(seed))

        def run_strategy(kind: str) -> Mapping[str, Any]:
            rows = [dict(r) for r in common]
            remaining = [dict(c) for c in remaining0]
            acquisition_receipts = []
            for step in range(budget - warm_n):
                if kind == "RANDOM":
                    idx = int(rng.integers(0, len(remaining))); receipt = {"status": "SEEDED_RANDOM"}
                elif kind == "GRID":
                    # Deterministic lexicographic coverage after a common neutral warm start.
                    order = np.lexsort(np.vstack([np.vstack([_vector(c) for c in remaining])[:, j] for j in reversed(range(len(KNOBS)))]))
                    target_rank = min(len(order)-1, int(round(step * (len(order)-1) / max(1, budget-warm_n-1))))
                    idx = int(order[target_rank]); receipt = {"status": "DETERMINISTIC_GRID_COVERAGE"}
                elif kind == "BAYESIAN_GP_EI":
                    idx = _predict_bayes(rows, remaining, reference); receipt = {"status": "GP_EXPECTED_IMPROVEMENT", "fixed_length_scale": 0.35}
                elif kind == "ATLAS_QUERY_FUNCTION_FORM":
                    idx, receipt = _predict_atlas(rows, remaining, reference)
                else:
                    raise ValueError(kind)
                c = remaining.pop(idx)
                rows.append(observation(c)); acquisition_receipts.append({"step": warm_n + step + 1, "config": c, **receipt})
            feasible = [r for r in rows if r.get("measurement", {}).get("gates", {}).get("all_signoff_gates_pass") is True and _raw_ppa(r) is not None]
            feasible.sort(key=lambda r: (_raw_ppa(r), digest_payload(r["config"])))
            best = feasible[0] if feasible else None
            return {"strategy": kind, "evaluation_budget": budget, "common_warm_start_count": warm_n,
                    "acquisitions": acquisition_receipts, "evaluations": rows,
                    "feasible_count": len(feasible), "best_feasible_raw_ppa": _raw_ppa(best) if best else None,
                    "best_feasible_config": best["config"] if best else None,
                    "best_feasible_measurement": best["measurement"] if best else None}

        strategies = [run_strategy(x) for x in ("ATLAS_QUERY_FUNCTION_FORM", "RANDOM", "GRID", "BAYESIAN_GP_EI")]
        feasible_strategies = [s for s in strategies if s["best_feasible_raw_ppa"] is not None]
        overall = min(feasible_strategies, key=lambda s: s["best_feasible_raw_ppa"]) if feasible_strategies else None
        atlas = next(s for s in strategies if s["strategy"] == "ATLAS_QUERY_FUNCTION_FORM")
        baseline_best = min((s for s in strategies if s["strategy"] != "ATLAS_QUERY_FUNCTION_FORM" and s["best_feasible_raw_ppa"] is not None), key=lambda s:s["best_feasible_raw_ppa"], default=None)
        all_four_have_feasible = all(s["best_feasible_raw_ppa"] is not None for s in strategies)
        atlas_beats: bool | None = None
        if all_four_have_feasible:
            atlas_beats = bool(atlas["best_feasible_raw_ppa"] < baseline_best["best_feasible_raw_ppa"])
        real_world = evaluator is None or evaluator_kind == "LIVE_ORFS"
        if real_world:
            live_status = "CHIP_PILOT_LIVE_EDA_COMPLETE" if all_four_have_feasible else "CHIP_PILOT_LIVE_EDA_INCONCLUSIVE"
        else:
            live_status = "CHIP_PILOT_QUALIFICATION_CONTROL_COMPLETE"
        scientific_result = None
        if real_world:
            if all_four_have_feasible:
                scientific_result = {
                    "decision": "ATLAS_BEATS_ALL_BASELINES" if atlas_beats else "ATLAS_DOES_NOT_BEAT_ALL_BASELINES",
                    "atlas_beats_all_baselines": atlas_beats,
                }
            else:
                scientific_result = {
                    "decision": "INCONCLUSIVE_MISSING_FEASIBLE_STRATEGY",
                    "atlas_beats_all_baselines": None,
                }
        core = {
            "schema": "phi-eda-chip-pilot/v1", "owner": OWNER_ID,
            "status": live_status,
            "research_freeze": {**freeze, "digest": freeze_digest}, "backend": backend,
            "normalization_reference_from_common_warm_start": reference,
            "unique_world_evaluations": len(cache),
            "world_evaluations": [cache[k] for k in sorted(cache)],
            "strategies": strategies,
            "comparison": {"overall_best_strategy": overall["strategy"] if overall else None,
                           "atlas_best_raw_ppa": atlas["best_feasible_raw_ppa"],
                           "best_baseline_strategy": baseline_best["strategy"] if baseline_best else None,
                           "best_baseline_raw_ppa": baseline_best["best_feasible_raw_ppa"] if baseline_best else None,
                           "all_four_strategies_have_feasible_design": all_four_have_feasible,
                           "atlas_beats_all_baselines": atlas_beats if real_world else None},
            "scientific_result": scientific_result,
            "claim_boundary": {"equal_budget": True, "common_warm_start": True, "world_results_cached_by_exact_config": True,
                               "qualification_control_is_physical_chip_evidence": False,
                               "atlas_win_claim_allowed": bool(real_world and all_four_have_feasible),
                               "tapeout_ready_claim_allowed": False},
        }
        return {**core, "digest": digest_payload(core)}


def qualification_oracle(config: Mapping[str, Any]) -> Mapping[str, Any]:
    """Nonphysical deterministic control for software qualification only.

    It deliberately has interactions and a narrow feasible region so that the owner,
    constraint gates, caching and all four search policies can be regression-tested.
    Its output MUST never be persisted or described as silicon/EDA evidence.
    """
    c = _normalize_config(config); x = _vector(c)
    # Smooth interacting landscape; Atlas has no direct access to this expression.
    area = 700.0 * (1.15 - 0.22*x[0] + 0.05*(x[1]-0.4)**2 + 0.04*x[2]*x[3])
    power = 0.0018 * (0.92 + 0.18*x[2] + 0.08*x[3] + 0.10*(x[0]-0.55)**2)
    delay = 7.2 * (1.10 - 0.18*x[0] - 0.10*x[2] + 0.13*(x[1]-0.65)**2 + 0.06*x[0]*x[3])
    ws = 0.12 - 0.22*max(0.0, x[0]-0.86) - 0.10*max(0.0, 0.08-x[2])
    drc = 1.0 if (x[0] > 0.90 and x[2] > 0.85) else 0.0
    lvs = not (x[1] < 0.03 and x[3] > 0.95)
    gates = {"timing_pass": ws >= 0, "signoff_drc_pass": drc == 0, "lvs_pass": bool(lvs), "gds_present": True}
    gates["all_signoff_gates_pass"] = all(gates.values())
    measurement = {"status": "SYNTHETIC_QUALIFICATION_ONLY", "metrics": {"area_um2":float(area), "power_w":float(power),
        "clock_period_ns":7.5, "worst_setup_slack_ns":float(ws), "effective_critical_delay_ns":float(delay),
        "setup_violation_count":0.0 if ws>=0 else 1.0, "route_drc_error_count":drc,
        "signoff_drc_count":drc, "lvs_pass":bool(lvs)}, "gates":gates,
        "artifacts":{"gds_present":True}}
    core = {"schema":"phi-eda-qualification-oracle/v1","status":"SYNTHETIC_QUALIFICATION_ONLY","measurement":measurement,
            "surrogate_used":True,"physical_chip_evidence":False}
    return {**core,"digest":digest_payload(core)}
