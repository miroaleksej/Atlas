from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Mapping
from evaluation.freeze_jhtdb_sgs_child_forms import verify_content_digest

EXPECTED_PROTOCOL_DIGEST = "c41038ac515826c3d6acf722488e788b13ad337e5beb40f9d903d7a401fda4bf"
PUBLIC_TEST_TOKEN = "edu.jhu.pha.turbulence.testing-201406"
MAX_TEST_POINTS = 4096


def canonical_digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def jhtdb_timepoint_from_snapshot_index(dataset: str, snapshot_index: int) -> int:
    """Map Atlas/JHTDB documented zero-based snapshot index to givernylocal timepoint.

    The isotropic8192 dataset is documented as snapshots 0..5, while current
    givernylocal validates getCutout timepoints in the inclusive range 1..6.
    Keep the frozen scientific snapshot index unchanged and adapt only at the
    API boundary.
    """
    if dataset == "isotropic8192":
        if snapshot_index < 0 or snapshot_index > 5:
            raise ValueError("isotropic8192 snapshot index must be in 0..5")
        return snapshot_index + 1
    return snapshot_index


def validate_freezes(protocol_doc: Mapping[str, Any], child_doc: Mapping[str, Any]) -> Mapping[str, Any]:
    proto = protocol_doc.get("protocol", {}) if isinstance(protocol_doc.get("protocol"), Mapping) else {}
    source = protocol_doc.get("source_capability", {}) if isinstance(protocol_doc.get("source_capability"), Mapping) else {}
    verify_content_digest(proto)
    verify_content_digest(source)
    verify_content_digest(child_doc)
    if proto.get("source_capability_digest") != source.get("digest"):
        raise ValueError("source capability binding mismatch")
    for form in child_doc.get("forms", ()):
        verify_content_digest(form)
    if proto.get("digest") != EXPECTED_PROTOCOL_DIGEST:
        raise ValueError("frozen observational protocol digest mismatch")
    if proto.get("status") != "OBSERVATIONAL_ARCHIVE_PROTOCOL_FROZEN_AWAITING_FRESH_MEASUREMENTS":
        raise ValueError("observational protocol has unexpected status")
    if proto.get("fresh_measurement_status") != "NOT_ACQUIRED":
        raise ValueError("fresh measurement already marked acquired")
    if proto.get("outcomes_inspected_prefreeze") is not False:
        raise ValueError("fresh outcomes were inspected prefreeze")
    if source.get("class") != "OBSERVATIONAL_ARCHIVE" or source.get("supports_arbitrary_state_intervention") is not False:
        raise ValueError("source capability is not a pure observational archive")
    if child_doc.get("status") != "CHILD_FORMS_FROZEN_BEFORE_FRESH_OBSERVATIONAL_EVIDENCE":
        raise ValueError("child forms are not frozen")
    if child_doc.get("observational_protocol_digest") != proto.get("digest"):
        raise ValueError("child freeze is not bound to this observational protocol")
    if child_doc.get("fresh_data_accessed_for_this_freeze") is not False:
        raise ValueError("child freeze is not premeasurement")
    return proto


def build_requests(proto: Mapping[str, Any]) -> list[dict[str, Any]]:
    requests_out: list[dict[str, Any]] = []
    for sample in proto.get("sample_contracts", []):
        sample_id = str(sample["sample_id"])
        if not sample_id or Path(sample_id).name != sample_id or sample_id in {".", ".."} or "\\" in sample_id:
            raise ValueError("sample_id must be a safe directory name")
        edge = int(sample["cube_edge"])
        x0, y0, z0 = map(int, sample["start_xyz_1based"])
        snapshot_index = int(sample["snapshot"])
        api_timepoint = jhtdb_timepoint_from_snapshot_index(str(sample["dataset"]), snapshot_index)
        if edge <= 0:
            raise ValueError("cube_edge must be positive")
        # testing token must never exceed 4096 points/request.
        slab_z = max(1, MAX_TEST_POINTS // (edge * edge))
        if edge * edge * slab_z > MAX_TEST_POINTS:
            raise ValueError("cannot make a testing-token-safe slab")
        for dz in range(0, edge, slab_z):
            depth = min(slab_z, edge - dz)
            requests_out.append({
                "sample_id": sample["sample_id"],
                "dataset": sample["dataset"],
                "snapshot_index": snapshot_index,
                "jhtdb_timepoint": api_timepoint,
                "xs": x0,
                "xe": x0 + edge - 1,
                "ys": y0,
                "ye": y0 + edge - 1,
                "zs": z0 + dz,
                "ze": z0 + dz + depth - 1,
                "points": edge * edge * depth,
                "slab_offset_z": dz,
            })
    return requests_out


def _import_giverny():
    try:
        import numpy as np  # noqa: F401
        from givernylocal.turbulence_dataset import turb_dataset
        from givernylocal.turbulence_toolkit import getCutout
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "givernylocal is required. Install with: python -m pip install --upgrade givernylocal"
        ) from exc
    return turb_dataset, getCutout



def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _transient_network_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    transient_tokens = (
        "http error 429", "http error 500", "http error 502", "http error 503", "http error 504",
        "service unavailable", "temporarily unavailable", "timeout", "timed out",
        "connection reset", "connection aborted", "connection refused", "remote disconnected",
        "jsondecodeerror", "expecting value: line 1 column 1",
    )
    return any(t in msg for t in transient_tokens)


def _checkpoint_paths(sample_dir: Path, dz: int, depth: int) -> tuple[Path, Path]:
    stem = f"slab_z{dz:04d}_d{depth:02d}"
    return sample_dir / f"{stem}.npy", sample_dir / f"{stem}.json"


def _load_checkpoint(
    *, sample_dir: Path, protocol_digest: str, sample_id: str,
    dataset: str, snapshot_index: int, api_timepoint: int,
    ranges: Any, dz: int, depth: int, edge: int,
):
    import numpy as np
    arr_p, meta_p = _checkpoint_paths(sample_dir, dz, depth)
    if not (arr_p.is_file() and meta_p.is_file()):
        return None, None
    try:
        meta = load_json(meta_p)
        verify_content_digest(meta)
        expected = {
            "protocol_digest": protocol_digest,
            "sample_id": sample_id,
            "dataset": dataset,
            "snapshot_index_frozen": snapshot_index,
            "jhtdb_timepoint_api": api_timepoint,
            "ranges_1based": ranges.tolist(),
            "shape_zyxc": [depth, edge, edge, 3],
        }
        for k, v in expected.items():
            if meta.get(k) != v:
                return None, None
        if meta.get("array_sha256") != sha256_file(arr_p):
            return None, None
        arr = np.load(arr_p, allow_pickle=False)
        if list(arr.shape) != expected["shape_zyxc"] or not np.isfinite(arr).all():
            return None, None
        return arr.astype(np.float32, copy=False), meta
    except Exception:
        return None, None


def _save_checkpoint(
    *, sample_dir: Path, protocol_digest: str, sample_id: str,
    dataset: str, snapshot_index: int, api_timepoint: int,
    ranges: Any, dz: int, depth: int, edge: int, arr: Any, attempt_count: int,
) -> dict[str, Any]:
    import numpy as np
    if np.asarray(arr).shape != (depth, edge, edge, 3) or not np.isfinite(arr).all():
        raise ValueError("checkpoint requires finite values and expected shape")
    arr_p, meta_p = _checkpoint_paths(sample_dir, dz, depth)
    tmp = arr_p.with_suffix(arr_p.suffix + ".tmp")
    with tmp.open("wb") as f:
        np.save(f, np.asarray(arr, dtype=np.float32), allow_pickle=False)
    tmp.replace(arr_p)
    meta = {
        "schema": "atlas-jhtdb-sgs-slab-checkpoint/v1",
        "protocol_digest": protocol_digest,
        "sample_id": sample_id,
        "dataset": dataset,
        "snapshot_index_frozen": snapshot_index,
        "jhtdb_timepoint_api": api_timepoint,
        "ranges_1based": ranges.tolist(),
        "z_offset": dz,
        "depth": depth,
        "shape_zyxc": [depth, edge, edge, 3],
        "points": int(edge * edge * depth),
        "array_path": str(arr_p),
        "array_sha256": sha256_file(arr_p),
        "network_attempt_count_for_this_slab": int(attempt_count),
    }
    meta["digest"] = canonical_digest(meta)
    _atomic_write_json(meta_p, meta)
    return meta


def _fetch_with_retry(getCutout, cube, ranges, strides, *, max_retries: int, retry_base_seconds: float):
    attempts = 0
    while True:
        attempts += 1
        try:
            return getCutout(cube, "velocity", ranges, strides, verbose=True), attempts
        except Exception as exc:
            if not _transient_network_error(exc) or attempts >= max_retries + 1:
                raise
            delay = min(60.0, retry_base_seconds * (2 ** (attempts - 1)))
            print(f"TRANSIENT JHTDB ERROR: {exc}")
            print(f"RETRY {attempts}/{max_retries + 1} IN {delay:.1f}s")
            time.sleep(delay)


def _download_sample(
    sample: Mapping[str, Any], out_dir: Path, token: str, *, protocol_digest: str,
    max_retries: int, retry_base_seconds: float, success_pause_seconds: float, resume: bool,
) -> tuple[Path, dict[str, Any]]:
    import numpy as np
    turb_dataset, getCutout = _import_giverny()

    edge = int(sample["cube_edge"])
    x0, y0, z0 = map(int, sample["start_xyz_1based"])
    snapshot_index = int(sample["snapshot"])
    dataset = str(sample["dataset"])
    api_timepoint = jhtdb_timepoint_from_snapshot_index(dataset, snapshot_index)
    sample_id = str(sample["sample_id"])
    sample_dir = out_dir / sample_id
    sample_dir.mkdir(parents=True, exist_ok=True)

    cube = turb_dataset(dataset_title=dataset, output_path=str(sample_dir), auth_token=token)
    slab_z = max(1, MAX_TEST_POINTS // (edge * edge))
    slabs = []
    slab_receipts = []

    for dz in range(0, edge, slab_z):
        depth = min(slab_z, edge - dz)
        ranges = np.array([
            [x0, x0 + edge - 1],
            [y0, y0 + edge - 1],
            [z0 + dz, z0 + dz + depth - 1],
            [api_timepoint, api_timepoint],
        ], dtype=int)
        strides = np.array([1, 1, 1, 1], dtype=int)
        arr = None
        checkpoint = None
        if resume:
            arr, checkpoint = _load_checkpoint(
                sample_dir=sample_dir, protocol_digest=protocol_digest, sample_id=sample_id,
                dataset=dataset, snapshot_index=snapshot_index, api_timepoint=api_timepoint,
                ranges=ranges, dz=dz, depth=depth, edge=edge,
            )
        if arr is not None:
            print(f"RESUME CHECKPOINT: {sample_id} z_offset={dz} depth={depth}")
            attempts = int(checkpoint.get("network_attempt_count_for_this_slab", 0))
        else:
            ds, attempts = _fetch_with_retry(
                getCutout, cube, ranges, strides,
                max_retries=max_retries, retry_base_seconds=retry_base_seconds,
            )
            names = list(ds.data_vars)
            if len(names) != 1:
                raise RuntimeError(f"unexpected getCutout data variables for {sample_id}: {names}")
            arr = np.asarray(ds[names[0]].values, dtype=np.float32)
            if arr.shape != (depth, edge, edge, 3):
                raise RuntimeError(f"unexpected slab shape {arr.shape}; expected {(depth, edge, edge, 3)}")
            checkpoint = _save_checkpoint(
                sample_dir=sample_dir, protocol_digest=protocol_digest, sample_id=sample_id,
                dataset=dataset, snapshot_index=snapshot_index, api_timepoint=api_timepoint,
                ranges=ranges, dz=dz, depth=depth, edge=edge, arr=arr, attempt_count=attempts,
            )
            if success_pause_seconds > 0:
                time.sleep(success_pause_seconds)
        slabs.append(arr)
        slab_receipts.append(dict(checkpoint))

    raw_zyxc = np.concatenate(slabs, axis=0)
    if raw_zyxc.shape != (edge, edge, edge, 3):
        raise RuntimeError(f"assembled cube shape mismatch: {raw_zyxc.shape}")

    # JHTDB getCutout returns (z,y,x,component). Atlas DNS snapshots use array axes as (x,y,z).
    raw_xyzc = np.transpose(raw_zyxc, (2, 1, 0, 3))
    dx = float(2.0 * np.pi / 8192.0) if dataset == "isotropic8192" else float(getattr(cube, "dx"))
    npz_path = out_dir / f"{sample_id}.npz"
    np.savez_compressed(npz_path, u=raw_xyzc[..., 0], v=raw_xyzc[..., 1], w=raw_xyzc[..., 2], dx=dx)

    receipt = {
        "sample_id": sample_id,
        "dataset": dataset,
        "snapshot_index_frozen": snapshot_index,
        "jhtdb_timepoint_api": api_timepoint,
        "time_index_mapping": "JHTDB_DOCUMENTED_SNAPSHOT_INDEX_ZERO_BASED_TO_GIVERNYLOCAL_TIMEPOINT_ONE_BASED",
        "start_xyz_1based": [x0, y0, z0],
        "cube_edge": edge,
        "filter_ratios_frozen": list(sample.get("filter_ratios", [])),
        "npz_path": str(npz_path),
        "npz_sha256": sha256_file(npz_path),
        "npz_size": npz_path.stat().st_size,
        "array_shape_xyz": [edge, edge, edge],
        "dx": dx,
        "slabs": slab_receipts,
    }
    receipt["protocol_digest"] = protocol_digest
    receipt["digest"] = canonical_digest(receipt)
    _atomic_write_json(sample_dir / "SAMPLE_ACQUISITION_RECEIPT.json", receipt)
    return npz_path, receipt


def main() -> int:
    ap = argparse.ArgumentParser(description="Acquire frozen JHTDB isotropic8192 natural samples without changing the premeasurement freeze.")
    ap.add_argument("--protocol", default="reports/turbulence/JHTDB_SGS_OBSERVATIONAL_PROTOCOL_FROZEN.json")
    ap.add_argument("--child-freeze", default="reports/turbulence/ATLAS_RANDOM20_SGS_CHILD_FORMS_FREEZE.json")
    ap.add_argument("--output-dir", default="examples/jhtdb_sgs_fresh_8192")
    ap.add_argument("--receipt", default="reports/turbulence/JHTDB_SGS_FRESH_ACQUISITION_RECEIPT.json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="Allow replacing an existing acquisition receipt; raw sample coordinates remain frozen.")
    ap.add_argument("--max-retries", type=int, default=8, help="Retries per slab for transient HTTP/network failures (default: 8).")
    ap.add_argument("--retry-base-seconds", type=float, default=2.0, help="Initial retry delay, doubled up to 60 s (default: 2).")
    ap.add_argument("--success-pause-seconds", type=float, default=1.0, help="Pause after each successful network slab to reduce service pressure (default: 1).")
    ap.add_argument("--no-resume", action="store_true", help="Ignore valid slab checkpoints and request all slabs again.")
    ap.add_argument("--reset-checkpoints", action="store_true", help="Delete V5.2 slab checkpoints before acquisition; frozen coordinates are unchanged.")
    args = ap.parse_args()
    if args.max_retries < 0:
        raise SystemExit("--max-retries must be >= 0")
    if args.retry_base_seconds < 0:
        raise SystemExit("--retry-base-seconds must be >= 0")
    if args.success_pause_seconds < 0:
        raise SystemExit("--success-pause-seconds must be >= 0")

    protocol_p = Path(args.protocol)
    child_p = Path(args.child_freeze)
    if not protocol_p.is_file():
        raise SystemExit(f"protocol not found: {protocol_p}")
    if not child_p.is_file():
        raise SystemExit(
            f"child-form freeze not found: {child_p}\n"
            "Run first: python -m evaluation.freeze_jhtdb_sgs_child_forms"
        )

    protocol_doc = load_json(protocol_p)
    child_doc = load_json(child_p)
    proto = validate_freezes(protocol_doc, child_doc)
    request_plan = build_requests(proto)

    print("PROTOCOL:", proto["digest"])
    print("CHILD FREEZE:", child_doc.get("digest"))
    print("SAMPLES:", len(proto.get("sample_contracts", [])))
    print("NETWORK REQUESTS:", len(request_plan))
    print("MAX POINTS/REQUEST:", max(r["points"] for r in request_plan))
    mappings = sorted({(r["snapshot_index"], r["jhtdb_timepoint"]) for r in request_plan})
    print("SNAPSHOT INDEX -> JHTDB TIMEPOINT:", ", ".join(f"{a}->{b}" for a, b in mappings))
    if args.dry_run:
        print(json.dumps(request_plan, indent=2))
        print("DRY_RUN_PASS_NO_FRESH_DATA_ACCESSED")
        return 0

    receipt_p = Path(args.receipt)
    if receipt_p.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite existing acquisition receipt: {receipt_p}")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.reset_checkpoints:
        for sample in proto.get("sample_contracts", []):
            sd = out_dir / str(sample["sample_id"])
            if sd.exists():
                if sd.is_symlink() or sd.resolve().parent != out_dir.resolve():
                    raise ValueError("checkpoint directory escapes output directory")
                shutil.rmtree(sd)
        print("CHECKPOINTS RESET; FROZEN SAMPLE CONTRACT UNCHANGED")
    token = os.environ.get("JHTDB_TOKEN", PUBLIC_TEST_TOKEN)
    sample_receipts = []
    for sample in proto.get("sample_contracts", []):
        _, row = _download_sample(
            sample, out_dir, token, protocol_digest=str(proto["digest"]),
            max_retries=args.max_retries, retry_base_seconds=args.retry_base_seconds,
            success_pause_seconds=args.success_pause_seconds, resume=not args.no_resume,
        )
        sample_receipts.append(row)

    core = {
        "schema": "atlas-jhtdb-sgs-fresh-acquisition/v1",
        "status": "FRESH_RAW_NATURAL_SAMPLES_ACQUIRED_MEASUREMENT_ADAPTER_PENDING",
        "protocol_digest": proto["digest"],
        "child_forms_freeze_digest": child_doc.get("digest"),
        "measurement_adapter_owner_required": proto.get("measurement_adapter_owner"),
        "sample_ids": [r["sample_id"] for r in sample_receipts],
        "samples": sample_receipts,
        "raw_fields": ["u", "v", "w"],
        "fresh_data_acquired": True,
        "fresh_targets_computed": False,
        "fresh_targets_used_for_term_selection": False,
        "scientific_law_established": False,
        "next_action": "RUN_EXISTING_BLIND_DNS_MEASUREMENT_ADAPTER_BOUND_TO_PROTOCOL_DIGEST",
        "transport_resilience": {
            "resume_enabled": not args.no_resume,
            "max_retries_per_slab": args.max_retries,
            "retry_base_seconds": args.retry_base_seconds,
            "success_pause_seconds": args.success_pause_seconds,
            "checkpoint_schema": "atlas-jhtdb-sgs-slab-checkpoint/v1",
        },
        "claim_boundary": {
            "this_runner_is_not_the_scientific_reasoning_owner": True,
            "this_runner_does_not_reimplement_the_frozen_dns_target_adapter": True,
            "this_runner_does_not_fit_or_select_terms_on_fresh_data": True,
            "frozen_snapshot_index_is_not_mutated": True,
            "givernylocal_timepoint_is_api_boundary_mapping_only": True,
        },
    }
    receipt = {**core, "digest": canonical_digest(core)}
    receipt_p.parent.mkdir(parents=True, exist_ok=True)
    receipt_p.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("STATUS:", receipt["status"])
    print("FRESH TARGETS COMPUTED:", receipt["fresh_targets_computed"])
    print("DIGEST:", receipt["digest"])
    print("RECEIPT:", receipt_p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
