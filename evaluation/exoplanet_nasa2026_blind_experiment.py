from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any
import sys

ROOT_DEFAULT = Path(__file__).resolve().parents[1]
if str(ROOT_DEFAULT) not in sys.path:
    sys.path.insert(0, str(ROOT_DEFAULT))

import numpy as np
import pandas as pd

from source.lawspace.api import LawSpaceAPI
from source.lawspace.research_cycle import AdaptiveResearchKernelOwner
from source.lawspace.schema import digest_payload

AU_M = 149_597_870_700.0
DAY_S = 86_400.0
M_SUN_KG = 1.98847e30
DIMLESS = [0, 0, 0, 0, 0, 0, 0]

SEARCH_BOUNDS = {"e_a": (-4, 4), "e_P": (-4, 4), "e_M": (-3, 3)}
DORMANT_AXES = [
    "log_planet_mass_earth",
    "log_planet_radius_earth",
    "eccentricity",
    "log_insolation_earth",
    "log_equilibrium_temperature_K",
    "log_stellar_temperature_K",
    "log_stellar_radius_solar",
    "stellar_metallicity_FeH",
    "stellar_logg_cgs",
    "log_distance_pc",
    "discovery_year_centered",
    "system_planet_count",
    "ttv_flag",
    "controversial_flag",
    "relative_period_uncertainty",
    "relative_semimajor_axis_uncertainty",
    "relative_stellar_mass_uncertainty",
]
REQUIRED_COLUMNS = {
    "pl_name", "hostname", "pl_orbper", "pl_orbsmax", "st_mass",
    "pl_bmasse", "pl_rade", "pl_orbeccen", "pl_insol", "pl_eqt",
    "st_teff", "st_rad", "st_met", "st_logg", "sy_dist", "disc_year",
    "sy_pnum", "ttv_flag", "pl_controv_flag", "pl_orbpererr1",
    "pl_orbsmaxerr1", "st_masserr1",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def h64(value: str) -> int:
    return int(hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16], 16)


def host_split(host: str) -> str:
    b = h64(host) % 100
    if b < 60:
        return "discovery"
    if b < 80:
        return "validation"
    return "sealed"


def primitive(v: tuple[int, int, int]) -> bool:
    g = 0
    for x in v:
        g = math.gcd(g, abs(int(x)))
    return g == 1


def canonical_sign(v: tuple[int, int, int]) -> bool:
    return next((x for x in v if x), 1) > 0


def candidate_vectors() -> list[tuple[int, int, int]]:
    out: list[tuple[int, int, int]] = []
    for ea, eP, eM in itertools.product(
        range(SEARCH_BOUNDS["e_a"][0], SEARCH_BOUNDS["e_a"][1] + 1),
        range(SEARCH_BOUNDS["e_P"][0], SEARCH_BOUNDS["e_P"][1] + 1),
        range(SEARCH_BOUNDS["e_M"][0], SEARCH_BOUNDS["e_M"][1] + 1),
    ):
        v = (ea, eP, eM)
        if 0 in v or not primitive(v) or not canonical_sign(v):
            continue
        out.append(v)
    return out


def closure_score(sub: pd.DataFrame, v: tuple[int, int, int]) -> dict[str, float]:
    lx = sub[["ln_a_si", "ln_P_si", "ln_M_si"]].to_numpy(float)
    vv = np.asarray(v, int)
    ln_c = lx @ vv
    raw = float(np.std(ln_c, ddof=1))
    scales = np.std(lx, axis=0, ddof=1)
    denom = math.sqrt(float(np.sum((vv * scales) ** 2)))
    return {
        "rho": raw / denom,
        "sd_logC": raw,
        "mean_logC": float(np.mean(ln_c)),
        "C_hat_SI": float(np.exp(np.mean(ln_c))),
    }


def add_base_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out[
        (pd.to_numeric(out["pl_orbper"], errors="coerce") > 0)
        & (pd.to_numeric(out["pl_orbsmax"], errors="coerce") > 0)
        & (pd.to_numeric(out["st_mass"], errors="coerce") > 0)
    ].copy()
    out["split"] = out["hostname"].map(host_split)
    out["ln_a_si"] = np.log(out["pl_orbsmax"].astype(float) * AU_M)
    out["ln_P_si"] = np.log(out["pl_orbper"].astype(float) * DAY_S)
    out["ln_M_si"] = np.log(out["st_mass"].astype(float) * M_SUN_KG)
    return out


def representative_hosts(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["planet_hash"] = out["pl_name"].map(h64)
    out = out.sort_values(["hostname", "planet_hash"]).groupby("hostname", as_index=False).first()
    return out


def safe_relerr(err: pd.Series, value: pd.Series) -> pd.Series:
    return np.abs(pd.to_numeric(err, errors="coerce")) / np.abs(pd.to_numeric(value, errors="coerce"))


def residual_frame(rep: pd.DataFrame, winner: tuple[int, int, int], discovery_mean_logc: float) -> pd.DataFrame:
    out = rep.copy()
    vv = np.asarray(winner, int)
    out["frozen_log_residual"] = out[["ln_a_si", "ln_P_si", "ln_M_si"]].to_numpy(float) @ vv - discovery_mean_logc
    out["log_planet_mass_earth"] = np.log(pd.to_numeric(out["pl_bmasse"], errors="coerce"))
    out["log_planet_radius_earth"] = np.log(pd.to_numeric(out["pl_rade"], errors="coerce"))
    out["eccentricity"] = pd.to_numeric(out["pl_orbeccen"], errors="coerce")
    out["log_insolation_earth"] = np.log(pd.to_numeric(out["pl_insol"], errors="coerce"))
    out["log_equilibrium_temperature_K"] = np.log(pd.to_numeric(out["pl_eqt"], errors="coerce"))
    out["log_stellar_temperature_K"] = np.log(pd.to_numeric(out["st_teff"], errors="coerce"))
    out["log_stellar_radius_solar"] = np.log(pd.to_numeric(out["st_rad"], errors="coerce"))
    out["stellar_metallicity_FeH"] = pd.to_numeric(out["st_met"], errors="coerce")
    out["stellar_logg_cgs"] = pd.to_numeric(out["st_logg"], errors="coerce")
    out["log_distance_pc"] = np.log(pd.to_numeric(out["sy_dist"], errors="coerce"))
    out["discovery_year_centered"] = pd.to_numeric(out["disc_year"], errors="coerce") - 2000.0
    out["system_planet_count"] = pd.to_numeric(out["sy_pnum"], errors="coerce")
    out["ttv_flag"] = pd.to_numeric(out["ttv_flag"], errors="coerce")
    out["controversial_flag"] = pd.to_numeric(out["pl_controv_flag"], errors="coerce")
    out["relative_period_uncertainty"] = safe_relerr(out["pl_orbpererr1"], out["pl_orbper"])
    out["relative_semimajor_axis_uncertainty"] = safe_relerr(out["pl_orbsmaxerr1"], out["pl_orbsmax"])
    out["relative_stellar_mass_uncertainty"] = safe_relerr(out["st_masserr1"], out["st_mass"])
    need = ["frozen_log_residual", *DORMANT_AXES]
    arr = out[need].to_numpy(float)
    finite = np.all(np.isfinite(arr), axis=1)
    # Logs above already convert non-positive values to non-finite; no imputation is allowed.
    return out.loc[finite].copy()


def observations(sub: pd.DataFrame) -> list[dict[str, Any]]:
    rows = []
    for _, r in sub.iterrows():
        vals = {"frozen_log_residual": float(r["frozen_log_residual"])}
        vals.update({name: float(r[name]) for name in DORMANT_AXES})
        rows.append({
            "record_id": str(r["pl_name"]),
            "study_id": str(r["hostname"]),
            "values": vals,
        })
    return rows


def registry_matches(root: Path, dim: tuple[int, ...]) -> list[dict[str, Any]]:
    data = json.loads((root / "data" / "constants" / "registry.json").read_text(encoding="utf-8"))
    items = data if isinstance(data, list) else data.get("constants", data.get("items", []))
    matches = []
    for item in items:
        rd = item.get("dimension", {})
        got = (
            int(rd.get("length", 0)), int(rd.get("mass", 0)), int(rd.get("time", 0)),
            int(rd.get("current", 0)), int(rd.get("temperature", 0)), int(rd.get("amount", 0)),
            int(rd.get("luminous_intensity", 0)),
        )
        if got == dim:
            matches.append({
                "constant_id": item.get("constant_id"), "symbol": item.get("symbol"),
                "value": item.get("value"), "unit": item.get("unit"),
            })
    return matches


def source_table_kind(raw: pd.DataFrame) -> str:
    """Classify input without guessing between PS and PSCompPars.

    A PS scientific confirmation must be prefiltered to the archive default
    solution.  Presence of ``default_flag`` therefore changes the table kind
    only when every finite row is exactly 1; mixed/default_flag=0 input fails
    closed instead of being silently filtered after protocol freeze.
    """
    if "default_flag" not in raw.columns:
        return "PSCompPars_COMPOSITE"
    flags = pd.to_numeric(raw["default_flag"], errors="coerce")
    finite = flags[np.isfinite(flags.to_numpy(float))]
    if len(finite) != len(raw) or len(finite) == 0 or not bool((finite == 1).all()):
        raise ValueError("PS input must contain only finite default_flag=1 rows; prefilter the official PS snapshot before running the frozen protocol")
    return "PS_DEFAULT_FLAG_1_SELF_CONSISTENT"


def run(root: Path, csv_path: Path) -> dict[str, Any]:
    source_sha = sha256_file(csv_path)
    script_sha = sha256_file(Path(__file__))
    raw = pd.read_csv(csv_path, comment="#")
    table_kind = source_table_kind(raw)
    missing = sorted(REQUIRED_COLUMNS - set(raw.columns))
    if missing:
        raise ValueError(f"required PSCompPars columns missing: {missing}")
    base = add_base_columns(raw)

    freeze_spec = {
        "schema": "atlas-nasa-exoplanet-2026-blind-freeze/v1",
        "source_sha256": source_sha,
        "source_table_kind": table_kind,
        "split": "sha256(hostname)%100: discovery 0..59, validation 60..79, sealed 80..99",
        "positive_control_search_bounds": SEARCH_BOUNDS,
        "positive_control_candidate_rules": "all-three-nonzero, primitive integer vector, canonical sign",
        "residual_target": "log(C_candidate/C_discovery_geomean)",
        "representative_planet_per_host": "minimum sha256(pl_name), chosen without target values",
        "initial_residual_representation": "INTERCEPT_ONLY",
        "dormant_axes": DORMANT_AXES,
        "residual_complexity_level": 1,
        "fit_tolerance_nrmse": 0.05,
        "axis_birth_trial_budget": 256,
        "sealed_used_for_selection": False,
        "validation_used_for_selection": False,
        "script_sha256": script_sha,
    }
    freeze_digest = digest_payload(freeze_spec)

    vectors = candidate_vectors()
    discovery = base[base["split"] == "discovery"]
    ranking = []
    for v in vectors:
        sc = closure_score(discovery, v)
        ranking.append({"exponents": list(v), **sc})
    ranking.sort(key=lambda x: (x["rho"], sum(abs(e) for e in x["exponents"]), tuple(x["exponents"])))
    winner_row = dict(ranking[0])
    winner = tuple(int(x) for x in winner_row["exponents"])
    # Freeze occurs here. Registry/constants and outer validation/sealed are read only after this point.

    split_control: dict[str, Any] = {}
    for split in ("discovery", "validation", "sealed"):
        sub = base[base["split"] == split]
        win_sc = closure_score(sub, winner)
        rank_rows = []
        for v in vectors:
            sc = closure_score(sub, v)
            rank_rows.append((sc["rho"], sum(abs(e) for e in v), v))
        rank_rows.sort()
        frozen_rank = next(i + 1 for i, row in enumerate(rank_rows) if row[2] == winner)
        split_control[split] = {
            "rows": int(len(sub)), "hosts": int(sub["hostname"].nunique()),
            "frozen_candidate_rank": int(frozen_rank), **win_sc,
        }

    dim_a = np.array([1, 0, 0, 0, 0, 0, 0], int)
    dim_p = np.array([0, 0, 1, 0, 0, 0, 0], int)
    dim_m = np.array([0, 1, 0, 0, 0, 0, 0], int)
    generated_dim = tuple(int(x) for x in (winner[0] * dim_a + winner[1] * dim_p + winner[2] * dim_m))
    matches = registry_matches(root, generated_dim)

    postfreeze_numeric_control = None
    g_match = next((m for m in matches if m.get("constant_id") == "CONST-G"), None)
    if g_match is not None and winner == (3, -2, -1):
        g_hat = 4.0 * math.pi**2 * winner_row["C_hat_SI"]
        g_ref = float(g_match["value"])
        postfreeze_numeric_control = {
            "G_hat": g_hat,
            "G_registry": g_ref,
            "relative_difference": g_hat / g_ref - 1.0,
            "used_for_candidate_selection": False,
        }

    rep = representative_hosts(base)
    residual = residual_frame(rep, winner, winner_row["mean_logC"])
    obs_by_split = {s: observations(residual[residual["split"] == s]) for s in ("discovery", "validation", "sealed")}
    dims = {"frozen_log_residual": DIMLESS, **{name: DIMLESS for name in DORMANT_AXES}}
    request = {
        "problem_id": "NASA-EXOPLANET-PS-DEFAULT-RESIDUAL-BLIND-001" if table_kind.startswith("PS_DEFAULT") else "NASA-EXOPLANET-PSCOMPPARS-2026-09-20-RESIDUAL-BLIND-001",
        "domain_id": "physics",
        "question": "After freezing the best dimensional closure from orbital period, semimajor axis and stellar mass, determine whether the normalized residual contains held-out structure in other observed coordinates; activate only residual-supported axes.",
        "observations": obs_by_split["discovery"],
        "sealed_holdout_observations": [],
        "target_variable": "frozen_log_residual",
        "predictor_variables": [],
        "dormant_axis_variables": DORMANT_AXES,
        "variable_dimensions": dims,
        "complexity_level": 1,
        "fit_tolerance_nrmse": 0.05,
        "axis_birth_trial_budget": 256,
        "axis_birth_sparse_search_allowed": True,
        "observations_origin": "NASA_EXOPLANET_ARCHIVE_PS_DEFAULT_FLAG_1" if table_kind.startswith("PS_DEFAULT") else "NASA_EXOPLANET_ARCHIVE_PSCOMPPARS_USER_SNAPSHOT",
        "auto_activate_dormant_axes": True,
    }
    receipt = LawSpaceAPI(root).advance_adaptive_research(request)
    result = receipt["result"]
    final_candidate = result.get("best_hypothesis")
    final_predictors = result.get("effective_predictor_variables", [])
    initial_candidate = (receipt.get("initial_hypothesis_space", {}).get("candidates") or [None])[0]

    validation_initial = AdaptiveResearchKernelOwner._evaluate_candidate_on_observations(
        initial_candidate, obs_by_split["validation"], [], "frozen_log_residual"
    )
    validation_final = AdaptiveResearchKernelOwner._evaluate_candidate_on_observations(
        final_candidate, obs_by_split["validation"], final_predictors, "frozen_log_residual"
    )
    # Sealed evaluation is deliberately the last numerical operation that can inspect the sealed subset.
    sealed_initial = AdaptiveResearchKernelOwner._evaluate_candidate_on_observations(
        initial_candidate, obs_by_split["sealed"], [], "frozen_log_residual"
    )
    sealed_final = AdaptiveResearchKernelOwner._evaluate_candidate_on_observations(
        final_candidate, obs_by_split["sealed"], final_predictors, "frozen_log_residual"
    )

    selected_axes = list(result.get("activated_axis_variables", []))
    residual_summary = {
        "representative_complete_hosts": int(len(residual)),
        "counts": {s: int(len(obs_by_split[s])) for s in obs_by_split},
        "initial_representation": "INTERCEPT_ONLY",
        "selected_axes": selected_axes,
        "selected_cardinality": int(receipt.get("axis_birth_search", {}).get("selected_cardinality", 0)),
        "axis_birth_policy": receipt.get("axis_birth_search", {}).get("policy"),
        "direct_residual_scores": receipt.get("axis_birth_search", {}).get("direct_residual_scores", {}),
        "discovery_initial_holdout_nrmse": receipt.get("axis_activation", {}).get("improvement", {}).get("initial_holdout_nrmse"),
        "discovery_final_holdout_nrmse": receipt.get("axis_activation", {}).get("improvement", {}).get("expanded_holdout_nrmse"),
        "validation_initial": validation_initial,
        "validation_final": validation_final,
        "sealed_initial": sealed_initial,
        "sealed_final": sealed_final,
        "kernel_status": result.get("status"),
        "next_action": result.get("next_action"),
        "scientific_law_established": False,
        "causal_establishment": False,
    }

    report_core = {
        "schema": "atlas-nasa-exoplanet-2026-blind-experiment/v1",
        "status": "EXPERIMENT_EXECUTED_NOT_SCIENTIFIC_PROMOTION",
        "freeze_spec": freeze_spec,
        "freeze_digest": freeze_digest,
        "source": {
            "path": str(csv_path), "sha256": source_sha,
            "raw_rows": int(len(raw)), "raw_columns": int(len(raw.columns)),
            "table_kind": table_kind,
            "base_positive_rows": int(len(base)), "base_hosts": int(base["hostname"].nunique()),
        },
        "positive_control": {
            "candidate_count": len(vectors),
            "winner": winner_row,
            "top10_discovery": ranking[:10],
            "split_transfer": split_control,
            "generated_dimension_LMTIThetaNJ": list(generated_dim),
            "postfreeze_registry_dimension_matches": matches,
            "postfreeze_numeric_control": postfreeze_numeric_control,
            "known_constant_registry_used_before_freeze": False,
        },
        "residual_multi_axis": residual_summary,
        "atlas_receipt": receipt,
        "claim_boundary": {
            "new_law_claimed": False,
            "world_novelty_claimed": False,
            "pscomppars_values_may_be_composite_or_derived": True,
            "selected_axes_are_representation_candidates_not_causes": True,
            "validation_and_sealed_not_used_for_axis_selection": True,
            "one_planet_per_host_used_for_residual_search": True,
            "sealed_host_overlap_with_discovery": False,
            "sealed_host_overlap_with_validation": False,
        },
    }
    report_core["digest"] = digest_payload(report_core)
    return report_core


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    report = run(root, Path(args.csv).resolve())
    out = Path(args.out) if args.out else root / "reports" / "NASA_EXOPLANET_2026_BLIND_CURRENT.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    r = report["residual_multi_axis"]
    print(json.dumps({
        "status": report["status"],
        "freeze_digest": report["freeze_digest"],
        "positive_control_winner": report["positive_control"]["winner"],
        "positive_control_transfer": report["positive_control"]["split_transfer"],
        "selected_axes": r["selected_axes"],
        "discovery_initial_holdout_nrmse": r["discovery_initial_holdout_nrmse"],
        "discovery_final_holdout_nrmse": r["discovery_final_holdout_nrmse"],
        "validation_initial_nrmse": r["validation_initial"].get("nrmse"),
        "validation_final_nrmse": r["validation_final"].get("nrmse"),
        "sealed_initial_nrmse": r["sealed_initial"].get("nrmse"),
        "sealed_final_nrmse": r["sealed_final"].get("nrmse"),
        "kernel_status": r["kernel_status"],
        "report": str(out),
        "report_digest": report["digest"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
