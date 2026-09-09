"""Qualification of the sealed retrospective exoplanet closure example."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import pytest


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
