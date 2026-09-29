"""Current JHTDB observational-adapter transport and freeze regressions."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def _load_module(name: str, relative_path: str):
    path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _runner():
    return _load_module(
        "jhtdb_observational_runner",
        "evaluation/run_fresh_jhtdb_sgs_observational_experiment.py",
    )


def test_runner_frozen_request_count():
    runner = _runner()
    protocol = {
        "sample_contracts": [
            {"sample_id": "A", "dataset": "isotropic8192", "snapshot": 0, "start_xyz_1based": [1, 2, 3], "cube_edge": 32, "filter_ratios": [2, 4, 8]},
            {"sample_id": "B", "dataset": "isotropic8192", "snapshot": 0, "start_xyz_1based": [4, 5, 6], "cube_edge": 32, "filter_ratios": [2, 4, 8]},
            {"sample_id": "C", "dataset": "isotropic8192", "snapshot": 0, "start_xyz_1based": [7, 8, 9], "cube_edge": 32, "filter_ratios": [2, 4, 8]},
        ]
    }
    requests = runner.build_requests(protocol)
    assert len(requests) == 24
    assert max(row["points"] for row in requests) == 4096
    assert all(row["dataset"] == "isotropic8192" for row in requests)


def test_freezer_rejects_missing_selected_axis():
    freezer = _load_module(
        "jhtdb_child_form_freezer",
        "evaluation/freeze_jhtdb_sgs_child_forms.py",
    )
    try:
        freezer.component_form({"summary": {"component": "x", "selected_axes": [], "parameters": [0, 1]}})
    except ValueError:
        pass
    else:
        raise AssertionError("expected fail closed")


def test_transient_errors_and_time_mapping():
    runner = _runner()
    assert runner.jhtdb_timepoint_from_snapshot_index("isotropic8192", 0) == 1
    assert runner._transient_network_error(Exception("HTTP Error 503."))
    assert runner._transient_network_error(Exception("Expecting value: line 1 column 1"))
    assert not runner._transient_network_error(Exception("frozen observational protocol digest mismatch"))


def test_checkpoint_roundtrip(tmp_path):
    runner = _runner()
    ranges = np.array([[1, 32], [1, 32], [1, 4], [1, 1]], dtype=int)
    array = np.arange(4 * 32 * 32 * 3, dtype=np.float32).reshape(4, 32, 32, 3)
    metadata = runner._save_checkpoint(
        sample_dir=tmp_path,
        protocol_digest="p",
        sample_id="s",
        dataset="isotropic8192",
        snapshot_index=0,
        api_timepoint=1,
        ranges=ranges,
        dz=0,
        depth=4,
        edge=32,
        arr=array,
        attempt_count=2,
    )
    restored, restored_metadata = runner._load_checkpoint(
        sample_dir=tmp_path,
        protocol_digest="p",
        sample_id="s",
        dataset="isotropic8192",
        snapshot_index=0,
        api_timepoint=1,
        ranges=ranges,
        dz=0,
        depth=4,
        edge=32,
    )
    assert np.array_equal(array, restored)
    assert restored_metadata["array_sha256"] == metadata["array_sha256"]
