from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from evaluation.turbulence_dns_closure_experiment import (
    MANIFEST_SCHEMA,
    DIM_LENGTH, DIM_VELOCITY, DIM_ACCELERATION,
    _sgs_residual,
    run_experiment, run_scale_invariant_extension,
)


def _snapshot(path: Path, amplitude: float, wave: float, n: int = 24) -> None:
    length = 2.0 * np.pi
    x = np.arange(n, dtype=float) * length / n
    X, Y, Z = np.meshgrid(x, x, x, indexing="ij")
    # Deliberately mix retained and filtered-out Fourier content so the exact
    # coarse-graining residual is non-zero in the adapter qualification test.
    u = amplitude * (np.sin(wave * X) + 0.35 * np.sin((wave + 5.0) * Y))
    v = amplitude * (np.cos(wave * Y) + 0.25 * np.sin((wave + 4.0) * Z))
    w = amplitude * 0.20 * np.cos((wave + 3.0) * X)
    np.savez_compressed(path, u=u, v=v, w=w, dx=length / n)


def test_sgs_residual_is_finite_and_nontrivial(tmp_path: Path) -> None:
    path = tmp_path / "one.npz"
    _snapshot(path, 1.0, 2.0)
    with np.load(path) as data:
        velocity = tuple(np.asarray(data[k], dtype=float) for k in ("u", "v", "w"))
        dx = float(data["dx"])
    filtered, residual, delta = _sgs_residual(velocity, (dx, dx, dx), 2)
    assert delta > 0
    assert all(arr.shape == velocity[0].shape for arr in filtered)
    assert all(np.all(np.isfinite(arr)) for arr in residual)
    assert max(float(np.max(np.abs(arr))) for arr in residual) > 1.0e-8


def test_dns_closure_harness_completes_without_auto_promotion(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    rows = []
    cases = [
        ("d1", "DISCOVERY", "REGIME-A", 1.0, 1.0),
        ("d2", "DISCOVERY", "REGIME-A", 0.8, 2.0),
        ("d3", "DISCOVERY", "REGIME-A", 1.2, 1.5),
        ("h1", "SEALED_HOLDOUT", "REGIME-B", 0.95, 2.5),
    ]
    for sid, role, regime, amp, wave in cases:
        path = data_dir / f"{sid}.npz"
        _snapshot(path, amp, wave)
        rows.append({
            "study_id": sid,
            "role": role,
            "regime_id": regime,
            "path": str(path),
            "subcube_offset": [0, 0, 0],
        })
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({
        "schema": MANIFEST_SCHEMA,
        "filter_ratio": 2,
        "atlas_grid_points": 9,
        "datasets": rows,
    }), encoding="utf-8")

    report = run_experiment(
        manifest_path=manifest_path,
        components=("x",),
        fit_tolerance=0.25,
        rank_shell_budget=3,
        factor_depth_budget=2,
        axis_birth_trial_budget=512,
        run_null_control=False,
    )
    assert report["protocol_status"] == "PASS_PROTOCOL_INTEGRITY"
    assert report["protocol_passed"] == report["protocol_total"]
    assert report["freeze"]["regimes_disjoint"] is True
    assert report["components"][0]["summary"]["atlas_native"] is True
    assert report["components"][0]["summary"]["scientific_law_established"] is False
    assert report["claim_boundary"]["new_turbulence_law_claimed"] is False


def test_scale_representation_birth_is_discovery_only_and_dimension_balanced() -> None:
    from source.lawspace.mathematical_invention import ScaleInvariantRepresentationBirthOwner

    owner = ScaleInvariantRepresentationBirthOwner()
    shape = (5, 5, 5)
    base = np.ones(shape, dtype=float)
    studies = [
        {
            "study_id": "d1", "role": "DISCOVERY",
            "coordinate_order": ["r1", "r2", "r3"],
            "coordinates": {"r1": list(range(5)), "r2": list(range(5)), "r3": list(range(5))},
            "fields": {
                "g0": (2.0 * base).tolist(), "g1": (3.0 * base).tolist(), "g2": (4.0 * base).tolist(),
                "g3": (0.25 * base).tolist(), "q0": (999.0 * base).tolist(),
            },
        },
        {
            "study_id": "d2", "role": "DISCOVERY",
            "coordinate_order": ["r1", "r2", "r3"],
            "coordinates": {"r1": list(range(5)), "r2": list(range(5)), "r3": list(range(5))},
            "fields": {
                "g0": (4.0 * base).tolist(), "g1": (1.0 * base).tolist(), "g2": (2.0 * base).tolist(),
                "g3": (0.5 * base).tolist(), "q0": (-999.0 * base).tolist(),
            },
        },
    ]
    chart = owner.invent(
        discovery_studies=studies,
        coordinate_dimensions={"r1": DIM_LENGTH, "r2": DIM_LENGTH, "r3": DIM_LENGTH},
        field_dimensions={"g0": DIM_VELOCITY, "g1": DIM_VELOCITY, "g2": DIM_VELOCITY, "g3": DIM_LENGTH, "q0": DIM_ACCELERATION},
        target_field="q0", predictor_fields=("g0", "g1", "g2", "g3"),
    )
    assert chart["status"] == "SCALE_INVARIANT_REPRESENTATION_BORN"
    assert chart["claim_boundary"]["sealed_studies_used_for_birth"] is False
    assert chart["claim_boundary"]["target_values_used_for_scale_estimation"] is False
    exponents = chart["target_scale_exponents"]
    rule_by_id = {row["rule_id"]: row for row in chart["rules"]}
    # Reconstruct the dimension of the born target scale and verify acceleration.
    out = np.zeros(7, dtype=float)
    for rid, exponent in exponents.items():
        out += int(exponent) * np.asarray(rule_by_id[rid]["dimension"], dtype=float)
    assert np.allclose(out, np.asarray(DIM_ACCELERATION, dtype=float))



def test_scale_extension_requires_and_records_fresh_holdout_boundary(tmp_path: Path) -> None:
    data_dir = tmp_path / "data2"
    data_dir.mkdir()
    rows = []
    cases = [
        ("d1", "DISCOVERY", "REGIME-A", 1.0, 1.0),
        ("d2", "DISCOVERY", "REGIME-A", 0.8, 2.0),
        ("d3", "DISCOVERY", "REGIME-A", 1.2, 1.5),
        ("h1", "SEALED_HOLDOUT", "REGIME-B", 0.95, 2.5),
    ]
    for sid, role, regime, amp, wave in cases:
        path = data_dir / f"{sid}.npz"
        _snapshot(path, amp, wave)
        rows.append({"study_id": sid, "role": role, "regime_id": regime, "path": str(path), "subcube_offset": [0, 0, 0]})
    manifest_path = tmp_path / "manifest2.json"
    manifest_path.write_text(json.dumps({"schema": MANIFEST_SCHEMA, "filter_ratio": 2, "atlas_grid_points": 9, "datasets": rows}), encoding="utf-8")
    raw = run_experiment(
        manifest_path=manifest_path, components=("x",), fit_tolerance=0.25,
        rank_shell_budget=3, factor_depth_budget=2, axis_birth_trial_budget=128,
        run_null_control=False,
    )
    prior_path = tmp_path / "prior.json"
    prior_path.write_text(json.dumps(raw), encoding="utf-8")
    scaled = run_scale_invariant_extension(
        manifest_path=manifest_path, components=("x",), fit_tolerance=0.25,
        rank_shell_budget=3, factor_depth_budget=2, axis_birth_trial_budget=128,
        run_null_control=False, prior_report_path=prior_path,
    )
    assert scaled["protocol_status"] == "PASS_PROTOCOL_INTEGRITY"
    assert scaled["components"][0]["summary"]["representation_chart_status"] == "SCALE_INVARIANT_REPRESENTATION_BORN"
    assert scaled["holdout_reuse_assessment"]["fresh_sealed_evidence"] is False
    assert scaled["claim_boundary"]["previously_exposed_holdout_can_establish_new_transfer_claim"] is False
    assert scaled["components"][0]["execution_receipt"]["atlas_claim"]["atlas_native"] is True
