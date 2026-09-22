import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_runner_frozen_request_count():
    m = load("runfresh", ROOT / "evaluation" / "run_fresh_jhtdb_sgs_observational_experiment.py")
    proto = {
        "sample_contracts": [
            {"sample_id": "A", "dataset": "isotropic8192", "snapshot": 0, "start_xyz_1based": [1,2,3], "cube_edge": 32, "filter_ratios": [2,4,8]},
            {"sample_id": "B", "dataset": "isotropic8192", "snapshot": 0, "start_xyz_1based": [4,5,6], "cube_edge": 32, "filter_ratios": [2,4,8]},
            {"sample_id": "C", "dataset": "isotropic8192", "snapshot": 0, "start_xyz_1based": [7,8,9], "cube_edge": 32, "filter_ratios": [2,4,8]},
        ]
    }
    reqs = m.build_requests(proto)
    assert len(reqs) == 24
    assert max(r["points"] for r in reqs) == 4096
    assert all(r["dataset"] == "isotropic8192" for r in reqs)


def test_freezer_rejects_missing_selected_axis():
    m = load("freezer", ROOT / "evaluation" / "freeze_jhtdb_sgs_child_forms.py")
    try:
        m.component_form({"summary": {"component": "x", "selected_axes": [], "parameters": [0,1]}})
    except ValueError:
        pass
    else:
        raise AssertionError("expected fail closed")
