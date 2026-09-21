"""Qualification of the sealed retrospective exoplanet closure example."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import pytest
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / "examples" / "exoplanets_dimensional_birth_of_G.ipynb"
DATA = ROOT / "examples" / "data" / "exoplanets_g_dimension_nasa2018.csv"


@pytest.fixture(scope="module")
def example():
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    namespace = {"__name__": "__atlas_notebook_qualification__"}
    for index, cell in enumerate(notebook["cells"]):
        if cell.get("cell_type") == "code":
            source = "".join(cell.get("source", ()))
            exec(compile(source, f"{NOTEBOOK.name}:cell-{index}", "exec"), namespace)
    return notebook, namespace


def test_example_notebook_is_current_release(example):
    notebook, _ = example
    assert notebook["nbformat"] == 4
    assert notebook["metadata"]["atlas_example"]["release"] == "15.25.0"
    from evaluation.release_files import is_local_artifact
    assert is_local_artifact(ROOT / ".venv" / "bin" / "python", ROOT)
    assert is_local_artifact(ROOT / "package.egg-info" / "PKG-INFO", ROOT)
    assert is_local_artifact(ROOT / ".DS_Store", ROOT)
    assert not is_local_artifact(NOTEBOOK, ROOT)


def test_example_dataset_schema_and_size():
    with DATA.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 50
    assert set(rows[0]) == {
        "source_rowid", "planet_name", "host_name", "pl_orbper_days",
        "pl_orbsmax_au", "st_mass_solar", "source_snapshot", "source_url",
    }


def test_example_dataset_has_positive_observations(example):
    _, namespace = example
    rows = namespace["rows"]
    assert all(row["P_days"] > 0 and row["a_AU"] > 0 and row["M_solar"] > 0 for row in rows)
    assert len({row["host"] for row in rows}) == 38


def test_example_search_surface_is_complete(example):
    _, namespace = example
    assert namespace["SEARCH_BOUNDS"] == {"e_a": (-4, 4), "e_P": (-4, 4), "e_M": (-3, 3)}
    assert len(namespace["candidates"]) == 172


def test_example_freezes_unhinted_kepler_coordinate(example):
    _, namespace = example
    assert namespace["winner"]["exponents"] == (3, -2, -1)
    assert namespace["winner"]["rho"] < 0.01


def test_example_generates_gravitational_dimension(example):
    _, namespace = example
    assert tuple(namespace["dim_C"]) == (3, -1, -2, 0, 0, 0, 0)
    assert namespace["dim_text"](namespace["dim_C"]) == "L^3 M^-1 T^-2"


def test_example_closes_exact_rational_kernel_at_p1(example):
    _, namespace = example
    assert len(namespace["pivots"]) == 3
    assert len(namespace["ns"]) == 1
    assert tuple(int(x) for x in namespace["v"]) == (3, -2, -1, -1)


def test_example_postfreeze_registry_match(example):
    _, namespace = example
    assert namespace["G"]["constant_id"] == "CONST-G"
    assert namespace["G_dim"] == tuple(int(x) for x in namespace["dim_C"])


def test_example_numeric_control_is_within_declared_scale(example):
    _, namespace = example
    inferred = 4 * math.pi**2 * namespace["winner"]["C_hat_SI"]
    reference = float(namespace["G"]["value"])
    assert abs(inferred / reference - 1.0) < 0.03
    assert namespace["between_group_dispersion"] < 0.05


def test_example_receipt_preserves_claim_boundary(example):
    _, namespace = example
    summary = namespace["summary"]
    assert summary["status"] == "RETROSPECTIVE_DIMENSIONAL_CLOSURE_EXAMPLE_PASS"
    assert summary["world_law_discovery_claimed"] is False
    assert summary["historical_172_row_receipt_reproduced"] is False



def _passport_fixture():
    columns = {
        "pl_name": ["Observed b", "InferA b", "InferP b", "Partial b"],
        "hostname": ["Observed", "InferA", "InferP", "Partial"],
        "discoverymethod": ["Transit"] * 4,
        "pl_bmassprov": ["Mass"] * 4,
        "disc_year": [2020, 2021, 2022, 2023],
        "pl_orbper": [365.25, 10.0, np.nan, np.nan],
        "pl_orbsmax": [1.0, np.nan, 0.2, np.nan],
        "st_mass": [1.0, 1.0, 1.0, np.nan],
        "pl_bmasse": [1.0, 5.0, 10.0, 2.0],
        "pl_rade": [1.0, 2.0, 3.0, 1.2],
        "st_teff": [5772.0, 5000.0, 4500.0, np.nan],
        "st_rad": [1.0, 0.9, 0.8, np.nan],
        "st_logg": [4.438, 4.4, 4.5, np.nan],
        "pl_orbeccen": [0.0167, 0.1, 0.2, np.nan],
        "pl_insol": [1.0, 10.0, 2.0, np.nan],
        "pl_eqt": [255.0, 700.0, 400.0, np.nan],
        "st_met": [0.0, 0.1, -0.1, np.nan],
        "sy_dist": [10.0, 20.0, 30.0, 40.0],
        "sy_pnum": [1, 1, 1, 1],
        "ttv_flag": [0, 0, 0, 0],
        "pl_controv_flag": [0, 0, 0, 0],
        "pl_orbpererr1": [0.01, 0.02, np.nan, np.nan],
        "pl_orbsmaxerr1": [0.001, np.nan, 0.002, np.nan],
        "st_masserr1": [0.01, 0.02, 0.03, np.nan],
    }
    return pd.DataFrame(columns)


def test_availability_passports_preserve_every_row_and_missing_semantics():
    from evaluation.exoplanet_availability_adaptive import build_availability_passports
    raw = _passport_fixture()
    passports, summary = build_availability_passports(
        raw,
        frozen_c_hat_si=1.6891158364826438e-12,
        g_reference_si=6.67430e-11,
    )
    assert len(passports) == len(raw) == 4
    assert summary["all_input_rows_preserved"] is True
    assert passports.loc[0, "orbital_status"] == "OBSERVED_P_A_MSTAR"
    assert passports.loc[1, "orbital_status"] == "MODEL_INFERRED_A_FROM_P_MSTAR"
    assert passports.loc[2, "orbital_status"] == "MODEL_INFERRED_P_FROM_A_MSTAR"
    assert passports.loc[3, "orbital_status"] == "INSUFFICIENT_ORBITAL_OBSERVATIONS"
    assert math.isfinite(float(passports.loc[1, "semimajor_axis_au_effective"]))
    assert math.isfinite(float(passports.loc[2, "orbital_period_days_effective"]))
    assert passports.loc[3, "passport_status"] == "PARTIAL_OBSERVED_PHYSICS"
    assert summary["model_inference_semantics"] == "MODEL_INFERRED_NE_OBSERVED"
    assert summary["missing_observation_semantics"] == "NOT_OBSERVED_NE_NO_EFFECT_NE_EXCLUDED"


def test_availability_passports_do_not_measure_closure_on_inferred_orbits():
    from evaluation.exoplanet_availability_adaptive import build_availability_passports
    passports, _ = build_availability_passports(
        _passport_fixture(),
        frozen_c_hat_si=1.6891158364826438e-12,
        g_reference_si=6.67430e-11,
    )
    assert math.isfinite(float(passports.loc[0, "G_hat_star_only_SI"]))
    assert pd.isna(passports.loc[1, "G_hat_star_only_SI"])
    assert pd.isna(passports.loc[2, "G_hat_star_only_SI"])


def test_availability_passports_never_treat_archive_limits_as_point_values():
    from evaluation.exoplanet_availability_adaptive import build_availability_passports
    raw = _passport_fixture().copy()
    raw["pl_bmasselim"] = [1, 0, 0, 0]
    raw["pl_radelim"] = [0, 0, 0, 0]
    passports, summary = build_availability_passports(
        raw,
        frozen_c_hat_si=1.6891158364826438e-12,
        g_reference_si=6.67430e-11,
    )
    assert passports.loc[0, "planet_mass_limit_flag"] == 1
    assert pd.isna(passports.loc[0, "planet_density_g_cm3"])
    assert pd.isna(passports.loc[0, "G_hat_two_body_SI"])
    assert "log_planet_mass_earth" not in str(passports.loc[0, "available_axes"]).split(";")
    assert passports.loc[0, "planet_density_audit_class"] == "INPUT_LIMIT_NOT_PHYSICAL_POINT"
    assert summary["limit_semantics"]["limits_used_as_central_values"] is False


def test_availability_limits_remain_candidate_constraints_not_deleted_evidence():
    from evaluation.exoplanet_availability_adaptive import build_availability_passports
    raw = _passport_fixture().copy()
    raw["pl_bmasselim"] = [1, 0, 0, 0]  # snapshot +1 = upper bound
    raw["pl_radelim"] = [0, 0, 0, 0]
    passports, summary = build_availability_passports(
        raw,
        frozen_c_hat_si=1.6891158364826438e-12,
        g_reference_si=6.67430e-11,
    )
    # The censored mass must not be used as an exact density, but the inequality
    # is retained and propagated into an allowed density interval.
    assert pd.isna(passports.loc[0, "planet_density_g_cm3"])
    assert passports.loc[0, "planet_true_mass_constraint_lower_earth"] == 0
    assert passports.loc[0, "planet_true_mass_constraint_upper_earth"] == pytest.approx(1.0)
    assert math.isfinite(float(passports.loc[0, "planet_density_constraint_upper_g_cm3"]))
    assert summary["limit_semantics"]["limits_preserved_as_inequality_constraints"] is True
    assert summary["candidate_attack_defense_contract"]["censored_observation_is_evidence"] is True


def test_msini_is_preserved_as_true_mass_lower_bound_for_candidate_defense():
    from evaluation.exoplanet_availability_adaptive import build_availability_passports
    raw = _passport_fixture().copy()
    raw.loc[0, "pl_bmassprov"] = "Msini"
    raw["pl_bmasselim"] = [0, 0, 0, 0]
    raw["pl_radelim"] = [0, 0, 0, 0]
    raw["pl_bmasseerr1"] = [0.1, np.nan, np.nan, np.nan]
    raw["pl_bmasseerr2"] = [-0.1, np.nan, np.nan, np.nan]
    raw["pl_radeerr1"] = [0.05, np.nan, np.nan, np.nan]
    raw["pl_radeerr2"] = [-0.05, np.nan, np.nan, np.nan]
    passports, summary = build_availability_passports(
        raw,
        frozen_c_hat_si=1.6891158364826438e-12,
        g_reference_si=6.67430e-11,
    )
    assert passports.loc[0, "planet_true_mass_constraint_lower_earth"] == pytest.approx(0.9)
    assert math.isinf(float(passports.loc[0, "planet_true_mass_constraint_upper_earth"]))
    assert summary["limit_semantics"]["best_mass_msini_preserved_as_true_mass_lower_bound"] is True


def test_hierarchical_observational_theory_owner_compiles_attack_defense_layers():
    from source.lawspace.theory_compiler import HierarchicalObservationalTheoryOwner
    owner = HierarchicalObservationalTheoryOwner()
    result = owner.compile(
        theory_id="TEST-HIERARCHY",
        universal_layer={"equation": "y=f(x)"},
        host_layer={"coordinate": "alpha_h"},
        regime_layer={"term": "f_R"},
        feasible_domain_layer={"domain": "Omega_i"},
        competing_explanations=[{"id": "H1"}, {"id": "H2"}],
        predictions=[{
            "prediction": "held-out sibling is predicted",
            "falsification": "prediction fails",
            "defense": "profile allowed nuisance coordinates",
            "heldout_refit_allowed": False,
        }],
        evidence_digest="evidence-1",
    )
    assert result["status"] == "HIERARCHICAL_THEORY_CANDIDATE_COMPILED"
    assert result["claim_boundary"]["compiled_theory_is_causal_truth"] is False
    assert result["gates"]["PREDICTIONS_ARE_ATTACK_AND_DEFENSE_READY"] is True


def test_hierarchical_theory_preserves_host_prediction_and_feasible_domain_semantics():
    from evaluation.exoplanet_availability_adaptive import (
        build_availability_passports,
        build_hierarchical_exoplanet_theory,
    )
    rows = []
    for host_idx in range(40):
        host = f"H{host_idx:02d}"
        host_scale = 0.8 + 0.01 * host_idx
        for planet_idx, a in enumerate((0.6, 1.0, 1.5)):
            rows.append({
                "pl_name": f"{host} p{planet_idx}", "hostname": host,
                "discoverymethod": "Transit", "pl_bmassprov": "Mass",
                "disc_year": 2020 + (host_idx % 4), "pl_orbper": 100.0 * a ** 1.5,
                "pl_orbsmax": a, "st_mass": 1.0, "pl_bmasse": 1.0 + planet_idx,
                "pl_rade": 1.0 + 0.1 * planet_idx, "st_teff": 5772.0, "st_rad": 1.0,
                "st_logg": 4.438, "pl_orbeccen": 0.01, "pl_insol": host_scale / (a * a),
                "pl_eqt": 278.0 / math.sqrt(a), "st_met": 0.0, "sy_dist": 20.0 + host_idx,
                "sy_pnum": 3, "sy_snum": 1, "ttv_flag": 0, "pl_controv_flag": 0,
                "pl_orbpererr1": 0.01, "pl_orbsmaxerr1": 0.001, "st_masserr1": 0.01,
                "pl_insolerr1": 0.01 * host_scale / (a * a), "pl_insolerr2": -0.01 * host_scale / (a * a),
                "st_raderr1": 0.01, "st_raderr2": -0.01, "st_tefferr1": 10.0, "st_tefferr2": -10.0,
                "pl_orbsmaxerr2": -0.001,
            })
    raw = pd.DataFrame(rows)
    passports, summary = build_availability_passports(
        raw,
        frozen_c_hat_si=1.6891158364826438e-12,
        g_reference_si=6.67430e-11,
    )
    theory = build_hierarchical_exoplanet_theory(raw, passports, summary)
    assert theory["status"] == "HIERARCHICAL_THEORY_CANDIDATE_COMPILED"
    host = theory["layers"]["group_or_host_latent_state"]
    assert host["leave_one_planet_out_prediction"]["validation"]["rmse_relative_gain"] > 0
    mechanism = host["effective_stellar_luminosity_mechanism"]
    assert mechanism["representation_mechanism_identified"] is True
    assert mechanism["identity_max_abs_log_error"] < 1e-12
    assert mechanism["leave_one_planet_out_effective_luminosity_prediction"]["validation"]["rmse_relative_gain"] > 0
    assert theory["domain_status"] == "PREDICTIVE_HOST_EFFECTIVE_LUMINOSITY_REPRESENTATION_SUPPORTED_ORIGIN_UNRESOLVED"
    feasible = theory["layers"]["feasible_observational_domains"]["host_domain"]
    assert feasible["hosts_with_nonempty_common_lambda_domain"] > 0
    assert theory["scientific_promotion"] is False
