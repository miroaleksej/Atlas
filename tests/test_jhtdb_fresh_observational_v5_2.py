from pathlib import Path
import importlib.util
import numpy as np

def _load():
    p=Path(__file__).parents[1]/"evaluation/run_fresh_jhtdb_sgs_observational_experiment.py"
    spec=importlib.util.spec_from_file_location("fresh_runner_v52", p)
    m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def test_transient_errors_and_time_mapping():
    m=_load()
    assert m.jhtdb_timepoint_from_snapshot_index("isotropic8192",0)==1
    assert m._transient_network_error(Exception("HTTP Error 503."))
    assert m._transient_network_error(Exception("Expecting value: line 1 column 1"))
    assert not m._transient_network_error(Exception("frozen observational protocol digest mismatch"))

def test_checkpoint_roundtrip(tmp_path):
    m=_load(); ranges=np.array([[1,32],[1,32],[1,4],[1,1]], dtype=int)
    arr=np.arange(4*32*32*3,dtype=np.float32).reshape(4,32,32,3)
    meta=m._save_checkpoint(sample_dir=tmp_path, protocol_digest="p", sample_id="s", dataset="isotropic8192", snapshot_index=0, api_timepoint=1, ranges=ranges, dz=0, depth=4, edge=32, arr=arr, attempt_count=2)
    arr2, meta2=m._load_checkpoint(sample_dir=tmp_path, protocol_digest="p", sample_id="s", dataset="isotropic8192", snapshot_index=0, api_timepoint=1, ranges=ranges, dz=0, depth=4, edge=32)
    assert np.array_equal(arr,arr2)
    assert meta2["array_sha256"]==meta["array_sha256"]
