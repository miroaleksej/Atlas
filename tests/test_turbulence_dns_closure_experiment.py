from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from evaluation.turbulence_dns_closure_experiment import (
    MANIFEST_SCHEMA,
    _sgs_residual,
    run_experiment,
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
