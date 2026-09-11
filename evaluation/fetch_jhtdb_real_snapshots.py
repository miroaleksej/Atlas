"""Fetch the real JHTDB DNS snapshots used by the Atlas closure experiment.

This module is deliberately a data-acquisition adapter, not a turbulence model.
It downloads raw gridded velocity cutouts from the official JHTDB local REST
cutout endpoint and converts them to Atlas' simple NPZ contract (u, v, w, dx).

The frozen experiment uses:
* DISCOVERY: JHTDB isotropic1024coarse, R_lambda ~ 433.
* SEALED_HOLDOUT: JHTDB isotropic4096, R_lambda = 610.57.

With JHTDB's public testing token every HTTP query must remain below 4096 grid
points.  An 18^3 snapshot is therefore assembled from two sequential 18x18x9
slabs (2916 points per request).  No interpolation or derivative service is
used; only raw grid-point velocity is requested.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import requests

OWNER_ID = "JHTDB-REAL-DNS-SNAPSHOT-ADAPTER/1.0.0"
SCHEMA = "phi-jhtdb-real-dns-snapshot-provenance/v1"
MANIFEST_SCHEMA = "phi-dns-turbulence-closure-dataset/v1"
JHTDB_ENDPOINT = "https://web.idies.jhu.edu/turbulence-svc/cutout/api/local"
PUBLIC_TESTING_TOKEN = "edu.jhu.pha.turbulence.testing-201406"
SOURCE_CUBE_EDGE = 18
SLAB_DEPTH = 9
POINTS_PER_QUERY = SOURCE_CUBE_EDGE * SOURCE_CUBE_EDGE * SLAB_DEPTH


@dataclass(frozen=True)
class SnapshotSpec:
    study_id: str
    filename: str
    role: str
    regime_id: str
    dataset: str
    time_index: int
    start_xyz: tuple[int, int, int]
    grid_spacing: float
    reynolds_note: str


# Freeze these selections before Atlas sees any derived target field.
SNAPSHOTS: tuple[SnapshotSpec, ...] = (
    SnapshotSpec(
        "DNS-DISCOVERY-01", "dns_discovery_01.npz", "DISCOVERY",
        "JHTDB-ISOTROPIC1024-RLAMBDA-APPROX-433", "isotropic1024coarse", 1,
        (65, 129, 193), 0.006135923151542565, "R_lambda approximately 433",
    ),
    SnapshotSpec(
        "DNS-DISCOVERY-02", "dns_discovery_02.npz", "DISCOVERY",
        "JHTDB-ISOTROPIC1024-RLAMBDA-APPROX-433", "isotropic1024coarse", 501,
        (257, 321, 385), 0.006135923151542565, "R_lambda approximately 433",
    ),
    SnapshotSpec(
        "DNS-DISCOVERY-03", "dns_discovery_03.npz", "DISCOVERY",
        "JHTDB-ISOTROPIC1024-RLAMBDA-APPROX-433", "isotropic1024coarse", 1001,
        (449, 513, 577), 0.006135923151542565, "R_lambda approximately 433",
    ),
    SnapshotSpec(
        "DNS-DISCOVERY-04", "dns_discovery_04.npz", "DISCOVERY",
        "JHTDB-ISOTROPIC1024-RLAMBDA-APPROX-433", "isotropic1024coarse", 1501,
        (641, 705, 769), 0.006135923151542565, "R_lambda approximately 433",
    ),
    SnapshotSpec(
        "DNS-SEALED-01", "dns_sealed_01.npz", "SEALED_HOLDOUT",
        "JHTDB-ISOTROPIC4096-RLAMBDA-610-57", "isotropic4096", 1,
        (1025, 1537, 2049), 0.0015339807878856412, "R_lambda = 610.57",
    ),
    SnapshotSpec(
        "DNS-SEALED-02", "dns_sealed_02.npz", "SEALED_HOLDOUT",
        "JHTDB-ISOTROPIC4096-RLAMBDA-610-57", "isotropic4096", 1,
        (2561, 3073, 3585), 0.0015339807878856412, "R_lambda = 610.57",
    ),
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path, chunk: int = 8 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            block = f.read(chunk)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def _canonical_digest(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(raw)


def _request_params(spec: SnapshotSpec, z_start: int, z_end: int, token: str) -> dict[str, Any]:
    x0, y0, _ = spec.start_xyz
    return {
        "token": token,
        "function": "velocity",
        "dataset": spec.dataset,
        "xs": x0,
        "xe": x0 + SOURCE_CUBE_EDGE - 1,
        "ys": y0,
        "ye": y0 + SOURCE_CUBE_EDGE - 1,
        "zs": z_start,
        "ze": z_end,
        "ts": spec.time_index,
        "te": spec.time_index,
        "stridet": 1,
        "stridex": 1,
        "stridey": 1,
        "stridez": 1,
        "filter_width": 1,
    }


def _public_params(params: Mapping[str, Any]) -> dict[str, Any]:
    """Return request metadata without exposing a private token."""
    out = dict(params)
    token = str(out.pop("token", ""))
    out["authorization_class"] = "PUBLIC_TESTING_TOKEN" if token == PUBLIC_TESTING_TOKEN else "USER_SUPPLIED_TOKEN_REDACTED"
    return out


def _extract_velocity_array(payload: Mapping[str, Any], expected_z: int) -> tuple[np.ndarray, dict[str, Any]]:
    data_vars = payload.get("data_vars")
    if not isinstance(data_vars, Mapping) or not data_vars:
        raise ValueError("JHTDB response does not contain data_vars")

    candidates: list[tuple[str, np.ndarray, Sequence[str]]] = []
    for name, meta in data_vars.items():
        if not isinstance(meta, Mapping) or "data" not in meta:
            continue
        arr = np.asarray(meta["data"], dtype=np.float32)
        dims = tuple(str(x) for x in meta.get("dims", ()))
        if arr.ndim == 4 and arr.shape[-1] == 3:
            candidates.append((str(name), arr, dims))
    if len(candidates) != 1:
        raise ValueError(f"expected exactly one 4D velocity data variable, got {len(candidates)}")

    name, arr, dims = candidates[0]
    expected = (expected_z, SOURCE_CUBE_EDGE, SOURCE_CUBE_EDGE, 3)
    if arr.shape != expected:
        raise ValueError(f"unexpected JHTDB cutout shape {arr.shape}; expected {expected} (z,y,x,component)")
    if not np.all(np.isfinite(arr)):
        raise ValueError("JHTDB cutout contains non-finite velocity values")
    return arr, {"data_var": name, "dims": list(dims), "shape_zyxc": list(arr.shape)}


def _http_get_json(
    session: requests.Session,
    params: Mapping[str, Any],
    *,
    timeout: float,
) -> tuple[dict[str, Any], bytes, int]:
    response = session.get(JHTDB_ENDPOINT, params=dict(params), timeout=timeout)
    response.raise_for_status()
    raw = bytes(response.content)
    try:
        payload = response.json()
    except Exception:
        payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("JHTDB cutout response must be a JSON object")
    return payload, raw, int(response.status_code)


def download_snapshot(
    spec: SnapshotSpec,
    *,
    output_dir: Path,
    token: str,
    session: requests.Session,
    timeout: float,
    pause_seconds: float,
    fetch_json: Callable[[requests.Session, Mapping[str, Any]], tuple[dict[str, Any], bytes, int]] | None = None,
) -> dict[str, Any]:
    """Download one 18^3 raw velocity cube as two <=4096-point slabs."""
    if POINTS_PER_QUERY >= 4096:
        raise AssertionError("public testing-token query must remain strictly below 4096 points")

    _, _, z0 = spec.start_xyz
    slab_ranges = ((z0, z0 + SLAB_DEPTH - 1), (z0 + SLAB_DEPTH, z0 + SOURCE_CUBE_EDGE - 1))
    slab_arrays: list[np.ndarray] = []
    slab_receipts: list[dict[str, Any]] = []

    for slab_index, (zs, ze) in enumerate(slab_ranges):
        params = _request_params(spec, zs, ze, token)
        if fetch_json is None:
            payload, raw, status = _http_get_json(session, params, timeout=timeout)
        else:
            payload, raw, status = fetch_json(session, params)
        arr, meta = _extract_velocity_array(payload, ze - zs + 1)
        slab_arrays.append(arr)
        slab_receipts.append({
            "slab_index": slab_index,
            "request": _public_params(params),
            "point_count": SOURCE_CUBE_EDGE * SOURCE_CUBE_EDGE * (ze - zs + 1),
            "http_status": status,
            "response_sha256": _sha256_bytes(raw),
            "response": meta,
        })
        if pause_seconds > 0 and slab_index + 1 < len(slab_ranges):
            time.sleep(pause_seconds)

    # Official JHTDB getCutout layout is z,y,x,component.  Convert to x,y,z.
    zyxc = np.concatenate(slab_arrays, axis=0)
    if zyxc.shape != (SOURCE_CUBE_EDGE, SOURCE_CUBE_EDGE, SOURCE_CUBE_EDGE, 3):
        raise AssertionError(f"assembled JHTDB cube has unexpected shape {zyxc.shape}")
    xyzc = np.transpose(zyxc, (2, 1, 0, 3))

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / spec.filename
    np.savez_compressed(
        path,
        u=xyzc[..., 0],
        v=xyzc[..., 1],
        w=xyzc[..., 2],
        dx=np.asarray(spec.grid_spacing, dtype=np.float64),
    )

    with np.load(path, allow_pickle=False) as data:
        for component in ("u", "v", "w"):
            arr = np.asarray(data[component])
            if arr.shape != (SOURCE_CUBE_EDGE,) * 3 or not np.all(np.isfinite(arr)):
                raise AssertionError(f"invalid saved component {component}: shape={arr.shape}")

    file_sha = _sha256_file(path)
    stats = {
        k: {
            "min": float(np.min(xyzc[..., i])),
            "max": float(np.max(xyzc[..., i])),
            "mean": float(np.mean(xyzc[..., i])),
            "std": float(np.std(xyzc[..., i])),
        }
        for i, k in enumerate(("u", "v", "w"))
    }
    return {
        "study": asdict(spec),
        "source_shape_xyz": [SOURCE_CUBE_EDGE] * 3,
        "npz_path": str(path),
        "npz_sha256": file_sha,
        "velocity_statistics": stats,
        "slabs": slab_receipts,
    }


def build_manifest(output_dir: Path, manifest_path: Path, receipts: Sequence[Mapping[str, Any]], provenance_path: Path) -> dict[str, Any]:
    sha_by_id = {str(r["study"]["study_id"]): str(r["npz_sha256"]) for r in receipts}
    entries = []
    for spec in SNAPSHOTS:
        rel = os.path.relpath(output_dir / spec.filename, manifest_path.parent)
        entries.append({
            "study_id": spec.study_id,
            "role": spec.role,
            "regime_id": spec.regime_id,
            "path": rel.replace(os.sep, "/"),
            "subcube_offset": [0, 0, 0],
            "source_dataset": spec.dataset,
            "source_time_index": spec.time_index,
            "source_start_xyz_1based": list(spec.start_xyz),
            "source_npz_sha256": sha_by_id[spec.study_id],
        })
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "dataset_status": "REAL_JHTDB_DNS_CROSS_RE_BLIND_EXPERIMENT",
        "filter_ratio": 2,
        "atlas_grid_points": 9,
        "source_cube_edge": SOURCE_CUBE_EDGE,
        "discovery_regime": "isotropic1024coarse; R_lambda approximately 433",
        "sealed_regime": "isotropic4096; R_lambda = 610.57",
        "provenance_path": os.path.relpath(provenance_path, manifest_path.parent).replace(os.sep, "/"),
        "datasets": entries,
    }
    manifest["freeze_digest"] = _canonical_digest({k: v for k, v in manifest.items() if k != "freeze_digest"})
    return manifest


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _plan() -> dict[str, Any]:
    return {
        "owner": OWNER_ID,
        "endpoint": JHTDB_ENDPOINT,
        "public_testing_token_point_limit": "<4096 points per query",
        "points_per_query": POINTS_PER_QUERY,
        "source_cube_edge": SOURCE_CUBE_EDGE,
        "queries_per_snapshot": 2,
        "snapshots": [asdict(s) for s in SNAPSHOTS],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download real JHTDB DNS snapshots for Atlas turbulence closure discovery.")
    parser.add_argument("--output-dir", default="examples/dns_snapshots", help="directory for generated real-DNS NPZ files")
    parser.add_argument("--manifest", default="examples/turbulence_dns_closure_manifest.real.json")
    parser.add_argument("--provenance", default="examples/dns_snapshots/JHTDB_DOWNLOAD_PROVENANCE.json")
    parser.add_argument("--token", default=os.environ.get("JHTDB_TOKEN", PUBLIC_TESTING_TOKEN), help="JHTDB token; defaults to public testing token or JHTDB_TOKEN")
    parser.add_argument("--timeout", type=float, default=1000.0)
    parser.add_argument("--pause-seconds", type=float, default=1.0, help="sequential-query pause; JHTDB asks testing-token users not to parallelize")
    parser.add_argument("--force", action="store_true", help="overwrite existing NPZ/manifest/provenance files")
    parser.add_argument("--dry-run", action="store_true", help="print frozen download plan without network access")
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    manifest_path = Path(args.manifest)
    provenance_path = Path(args.provenance)
    plan = _plan()
    if args.dry_run:
        print(json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    targets = [output_dir / s.filename for s in SNAPSHOTS] + [manifest_path, provenance_path]
    existing = [p for p in targets if p.exists()]
    if existing and not args.force:
        raise FileExistsError("refusing to overwrite existing real-DNS artifacts without --force:\n" + "\n".join(str(p) for p in existing))

    receipts: list[dict[str, Any]] = []
    with requests.Session() as session:
        for index, spec in enumerate(SNAPSHOTS, start=1):
            print(f"[{index}/{len(SNAPSHOTS)}] JHTDB {spec.dataset} time_index={spec.time_index} -> {spec.filename}", flush=True)
            receipt = download_snapshot(
                spec,
                output_dir=output_dir,
                token=str(args.token),
                session=session,
                timeout=float(args.timeout),
                pause_seconds=float(args.pause_seconds),
            )
            receipts.append(receipt)
            print(f"    SHA-256 {receipt['npz_sha256']}", flush=True)
            if args.pause_seconds > 0 and index < len(SNAPSHOTS):
                time.sleep(float(args.pause_seconds))

    manifest = build_manifest(output_dir, manifest_path, receipts, provenance_path)
    _write_json(manifest_path, manifest)
    provenance = {
        "schema": SCHEMA,
        "owner": OWNER_ID,
        "downloaded_at_utc": _dt.datetime.now(tz=_dt.timezone.utc).isoformat(),
        "source": {
            "provider": "Johns Hopkins Turbulence Database (JHTDB)",
            "endpoint": JHTDB_ENDPOINT,
            "access_mode": "official local REST getCutout endpoint",
            "authorization_class": "PUBLIC_TESTING_TOKEN" if str(args.token) == PUBLIC_TESTING_TOKEN else "USER_SUPPLIED_TOKEN_REDACTED",
            "parallel_queries_used": False,
            "interpolation_used": False,
            "derived_quantities_downloaded": False,
            "only_raw_velocity_downloaded": True,
            "references": [
                "https://turbulence.idies.jhu.edu/database",
                "https://turbulence.idies.jhu.edu/datasets/homogeneousTurbulence/isotropic",
                "https://turbulence.idies.jhu.edu/datasets/homogeneousTurbulence/isotropic4096",
                "https://github.com/sciserver/giverny",
            ],
        },
        "claim_boundary": {
            "these_are_real_dns_snapshots": True,
            "snapshot_selection_is_frozen_before_atlas_search": True,
            "known_turbulence_closure_supplied_to_atlas": False,
            "sealed_dataset_used_for_axis_birth": False,
            "successful_fit_would_establish_new_physical_law": False,
        },
        "plan": plan,
        "files": receipts,
        "manifest_sha256": None,
    }
    _write_json(provenance_path, provenance)
    provenance["manifest_sha256"] = _sha256_file(manifest_path)
    provenance["digest"] = _canonical_digest({k: v for k, v in provenance.items() if k != "digest"})
    _write_json(provenance_path, provenance)

    print(f"manifest:   {manifest_path}")
    print(f"provenance: {provenance_path}")
    print(f"freeze_digest: {manifest['freeze_digest']}")
    print("REAL_JHTDB_DNS_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
