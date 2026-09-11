from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from evaluation import fetch_jhtdb_real_snapshots as f


def _fake_payload(params):
    zs, ze = int(params["zs"]), int(params["ze"])
    xs, xe = int(params["xs"]), int(params["xe"])
    ys, ye = int(params["ys"]), int(params["ye"])
    z = np.arange(zs, ze + 1)[:, None, None]
    y = np.arange(ys, ye + 1)[None, :, None]
    x = np.arange(xs, xe + 1)[None, None, :]
    arr = np.empty((ze-zs+1, ye-ys+1, xe-xs+1, 3), dtype=np.float32)
    arr[..., 0] = x + 10*y + 100*z
    arr[..., 1] = 2*x - y + z
    arr[..., 2] = x + y - z
    payload = {"data_vars": {"velocity": {"dims": ["z", "y", "x", "values"], "data": arr.tolist()}}, "coords": {}}
    raw = json.dumps(payload, separators=(",", ":")).encode()
    return payload, raw, 200


def test_query_size_remains_below_testing_token_limit():
    assert f.POINTS_PER_QUERY == 18 * 18 * 9
    assert f.POINTS_PER_QUERY < 4096


def test_download_snapshot_assembles_xyz_and_writes_npz(tmp_path: Path):
    spec = f.SNAPSHOTS[0]

    def fetch_json(_session, params):
        assert int(params["xe"]) - int(params["xs"]) + 1 == 18
        assert int(params["ye"]) - int(params["ys"]) + 1 == 18
        assert int(params["ze"]) - int(params["zs"]) + 1 == 9
        return _fake_payload(params)

    receipt = f.download_snapshot(
        spec,
        output_dir=tmp_path,
        token=f.PUBLIC_TESTING_TOKEN,
        session=SimpleNamespace(),
        timeout=1,
        pause_seconds=0,
        fetch_json=fetch_json,
    )
    assert len(receipt["slabs"]) == 2
    path = tmp_path / spec.filename
    with np.load(path, allow_pickle=False) as data:
        assert data["u"].shape == (18, 18, 18)
        # Axis conversion from official z,y,x layout -> Atlas x,y,z.
        x0, y0, z0 = spec.start_xyz
        assert np.isclose(data["u"][0, 0, 0], x0 + 10*y0 + 100*z0)
        assert np.isclose(float(data["dx"]), spec.grid_spacing)


def test_manifest_is_real_cross_re_and_sha_bound(tmp_path: Path):
    out = tmp_path / "dns_snapshots"
    out.mkdir()
    receipts = []
    for spec in f.SNAPSHOTS:
        path = out / spec.filename
        np.savez_compressed(path, u=np.zeros((18,18,18)), v=np.zeros((18,18,18)), w=np.zeros((18,18,18)), dx=spec.grid_spacing)
        receipts.append({"study": f.asdict(spec), "npz_sha256": f._sha256_file(path)})
    manifest_path = tmp_path / "manifest.json"
    provenance_path = out / "provenance.json"
    manifest = f.build_manifest(out, manifest_path, receipts, provenance_path)
    assert manifest["dataset_status"] == "REAL_JHTDB_DNS_CROSS_RE_BLIND_EXPERIMENT"
    roles = {x["role"] for x in manifest["datasets"]}
    regimes = {x["regime_id"] for x in manifest["datasets"]}
    assert roles == {"DISCOVERY", "SEALED_HOLDOUT"}
    assert len(regimes) == 2
    assert all(len(x["source_npz_sha256"]) == 64 for x in manifest["datasets"])
    assert len(manifest["freeze_digest"]) == 64
