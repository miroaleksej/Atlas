"""Blind transferable turbulence-closure discovery from DNS snapshots.

The experiment does NOT provide Atlas with a catalogue of RANS/LES closures or
with precomputed derivative predictors.  A deterministic DNS adapter computes an
attested coarse-graining residual from raw periodic velocity snapshots.  Atlas
receives only masked resolved velocity fields, a filter-width field and the
attested residual target.  Spatial operator coordinates are born inside Atlas
from its translation/algebra meta-primitives.

Scientific boundary: completion of this experiment is not a new turbulence law.
A candidate is interesting only if it survives a sealed regime holdout and a
negative/null control.  A representation gap is a valid scientific outcome.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

from source.lawspace.api import LawSpaceAPI
from source.lawspace.schema import digest_payload

OWNER_ID = "BLIND-DNS-TURBULENCE-CLOSURE-EXPERIMENT/1.0.0"
SCHEMA = "phi-blind-dns-turbulence-closure/v1"
SCALE_OWNER_ID = "BLIND-DNS-SCALE-INVARIANT-REPRESENTATION-EXTENSION/1.0.0"
SCALE_SCHEMA = "phi-blind-dns-scale-invariant-representation-extension/v1"
MANIFEST_SCHEMA = "phi-dns-turbulence-closure-dataset/v1"

DIM_LENGTH = [1, 0, 0, 0, 0, 0, 0]
DIM_VELOCITY = [1, 0, -1, 0, 0, 0, 0]
DIM_ACCELERATION = [1, 0, -2, 0, 0, 0, 0]

COORD = {"x": "r1", "y": "r2", "z": "r3"}
FIELD = {"u": "g0", "v": "g1", "w": "g2", "delta": "g3", "target": "q0"}
COMPONENT_INDEX = {"x": 0, "y": 1, "z": 2}


def _sha256_file(path: Path, chunk: int = 8 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            data = f.read(chunk)
            if not data:
                break
            h.update(data)
    return h.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("dataset manifest must be a JSON object")
    return value


def _canonical_component_list(raw: str | Sequence[str]) -> tuple[str, ...]:
    if isinstance(raw, str):
        parts = [x.strip().lower() for x in raw.split(",") if x.strip()]
    else:
        parts = [str(x).strip().lower() for x in raw]
    if not parts:
        raise ValueError("at least one component is required")
    bad = [x for x in parts if x not in COMPONENT_INDEX]
    if bad:
        raise ValueError(f"unsupported velocity components: {bad}")
    return tuple(dict.fromkeys(parts))


def _manifest_entries(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError(f"manifest schema must be {MANIFEST_SCHEMA!r}")
    entries = [dict(x) for x in manifest.get("datasets", ())]
    if not entries:
        raise ValueError("manifest.datasets must contain DNS snapshot entries")
    roles = {str(x.get("role", "")).upper() for x in entries}
    if "DISCOVERY" not in roles or "SEALED_HOLDOUT" not in roles:
        raise ValueError("manifest requires both DISCOVERY and SEALED_HOLDOUT datasets")
    ids = [str(x.get("study_id", "")).strip() for x in entries]
    if any(not x for x in ids) or len(ids) != len(set(ids)):
        raise ValueError("every dataset entry needs a unique non-empty study_id")
    return entries


def _resolve_dataset_path(manifest_path: Path, entry: Mapping[str, Any]) -> Path:
    raw = str(entry.get("path", "")).strip()
    if not raw:
        raise ValueError(f"study {entry.get('study_id')!r} is missing path")
    p = Path(raw)
    if not p.is_absolute():
        p = (manifest_path.parent / p).resolve()
    if not p.is_file():
        raise FileNotFoundError(p)
    if p.suffix.lower() != ".npz":
        raise ValueError(f"study {entry.get('study_id')!r}: only .npz input is supported")
    return p


def _spacing_from_npz(data: Mapping[str, Any], shape: tuple[int, int, int]) -> tuple[float, float, float]:
    def scalar(name: str) -> float | None:
        if name not in data:
            return None
        arr = np.asarray(data[name], dtype=float)
        if arr.size != 1:
            return None
        return float(arr.reshape(-1)[0])

    vals = [scalar("dx"), scalar("dy"), scalar("dz")]
    if vals[0] is not None and vals[1] is None and vals[2] is None:
        vals = [vals[0], vals[0], vals[0]]
    if all(v is not None for v in vals):
        out = tuple(float(v) for v in vals)  # type: ignore[arg-type]
        if min(out) <= 0:
            raise ValueError("grid spacing must be positive")
        return out

    coords = []
    for name, n in zip(("x", "y", "z"), shape):
        if name not in data:
            raise ValueError("NPZ must contain dx[/dy/dz] scalars or x,y,z coordinate arrays")
        arr = np.asarray(data[name], dtype=float)
        if arr.ndim != 1 or len(arr) != n:
            raise ValueError(f"coordinate {name!r} must be a 1D array of length {n}")
        d = np.diff(arr)
        if len(d) == 0 or np.mean(d) <= 0 or not np.allclose(d, np.mean(d), rtol=1e-8, atol=1e-12):
            raise ValueError(f"coordinate {name!r} must be strictly increasing and uniform")
        coords.append(float(np.mean(d)))
    return tuple(coords)  # type: ignore[return-value]


def _load_velocity(path: Path) -> tuple[tuple[np.ndarray, np.ndarray, np.ndarray], tuple[float, float, float]]:
    with np.load(path, allow_pickle=False) as data:
        missing = [name for name in ("u", "v", "w") if name not in data]
        if missing:
            raise ValueError(f"{path.name}: missing velocity arrays {missing}")
        vel = tuple(np.asarray(data[name], dtype=float) for name in ("u", "v", "w"))
        shape = vel[0].shape
        if len(shape) != 3 or any(arr.shape != shape for arr in vel):
            raise ValueError(f"{path.name}: u,v,w must have the same 3D shape")
        if min(shape) < 16:
            raise ValueError(f"{path.name}: each DNS dimension must contain at least 16 samples")
        if any(not np.all(np.isfinite(arr)) for arr in vel):
            raise ValueError(f"{path.name}: velocity arrays must be finite")
        spacing = _spacing_from_npz(data, shape)
    return vel, spacing


def _spectral_wavenumbers(shape: Sequence[int], spacing: Sequence[float]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    axes = []
    for n, dx in zip(shape, spacing):
        axes.append(2.0 * math.pi * np.fft.fftfreq(int(n), d=float(dx)))
    return np.meshgrid(*axes, indexing="ij")  # type: ignore[return-value]


def _lowpass_mask(shape: Sequence[int], filter_ratio: int) -> np.ndarray:
    if filter_ratio < 2:
        raise ValueError("filter_ratio must be >= 2")
    mask = np.ones(tuple(int(n) for n in shape), dtype=bool)
    for axis, n in enumerate(shape):
        mode = np.fft.fftfreq(int(n)) * int(n)
        cutoff = max(1, int(n) // (2 * int(filter_ratio)))
        keep = np.abs(mode) <= cutoff
        view = [1, 1, 1]
        view[axis] = int(n)
        mask &= keep.reshape(view)
    return mask


def _spectral_filter(field: np.ndarray, mask: np.ndarray) -> np.ndarray:
    return np.fft.ifftn(np.fft.fftn(field) * mask).real


def _spectral_gradient(field: np.ndarray, kmesh: Sequence[np.ndarray]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    fhat = np.fft.fftn(field)
    return tuple(np.fft.ifftn(1j * k * fhat).real for k in kmesh)  # type: ignore[return-value]


def _sgs_residual(
    velocity: tuple[np.ndarray, np.ndarray, np.ndarray], spacing: tuple[float, float, float], filter_ratio: int,
) -> tuple[tuple[np.ndarray, np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray, np.ndarray], float]:
    """Return filtered velocity and exact unresolved convective forcing.

    target_i = -( filter(u_j d_j u_i) - U_j d_j U_i )
    where U is the frozen spectral low-pass field.  This is an observable
    coarse-graining residual, not a supplied closure model.
    """
    shape = velocity[0].shape
    mask = _lowpass_mask(shape, filter_ratio)
    kmesh = _spectral_wavenumbers(shape, spacing)
    filtered = tuple(_spectral_filter(arr, mask) for arr in velocity)
    residuals = []
    for component in range(3):
        grad_fine = _spectral_gradient(velocity[component], kmesh)
        nonlinear_fine = sum(velocity[j] * grad_fine[j] for j in range(3))
        filtered_nonlinear = _spectral_filter(nonlinear_fine, mask)
        grad_resolved = _spectral_gradient(filtered[component], kmesh)
        resolved_nonlinear = sum(filtered[j] * grad_resolved[j] for j in range(3))
        residuals.append(-(filtered_nonlinear - resolved_nonlinear))
    delta = float(filter_ratio) * float(np.prod(np.asarray(spacing, dtype=float)) ** (1.0 / 3.0))
    return filtered, tuple(residuals), delta  # type: ignore[return-value]


def _subcube_slices(shape: Sequence[int], points: int, offset: Sequence[int] | None) -> tuple[slice, slice, slice]:
    p = int(points)
    if p < 9:
        raise ValueError("atlas_grid_points must be >= 9")
    if any(p > int(n) for n in shape):
        raise ValueError(f"atlas_grid_points={p} exceeds coarse-grid shape {tuple(shape)}")
    raw = tuple(int(x) for x in (offset or (0, 0, 0)))
    if len(raw) != 3:
        raise ValueError("subcube_offset must contain exactly three integers")
    starts = []
    for n, start in zip(shape, raw):
        if start < 0 or start + p > int(n):
            raise ValueError(f"subcube_offset {raw} with atlas_grid_points={p} exceeds coarse-grid shape {tuple(shape)}")
        starts.append(start)
    return tuple(slice(s, s + p) for s in starts)  # type: ignore[return-value]


def _coarse_study(
    *, study_id: str, role: str, velocity: tuple[np.ndarray, np.ndarray, np.ndarray],
    residual: tuple[np.ndarray, np.ndarray, np.ndarray], spacing: tuple[float, float, float],
    filter_ratio: int, atlas_grid_points: int, subcube_offset: Sequence[int] | None, component: str,
) -> dict[str, Any]:
    stride = int(filter_ratio)
    coarse_velocity = tuple(arr[::stride, ::stride, ::stride] for arr in velocity)
    coarse_target = residual[COMPONENT_INDEX[component]][::stride, ::stride, ::stride]
    coarse_shape = coarse_velocity[0].shape
    sl = _subcube_slices(coarse_shape, atlas_grid_points, subcube_offset)
    fields = [arr[sl] for arr in coarse_velocity]
    target = coarse_target[sl]
    coarse_spacing = tuple(float(dx) * stride for dx in spacing)
    coords = {
        COORD[axis]: [float(i * h) for i in range(atlas_grid_points)]
        for axis, h in zip(("x", "y", "z"), coarse_spacing)
    }
    delta = float(stride) * float(np.prod(np.asarray(spacing, dtype=float)) ** (1.0 / 3.0))
    return {
        "study_id": study_id,
        "role": role,
        "coordinate_order": [COORD["x"], COORD["y"], COORD["z"]],
        "coordinates": coords,
        "fields": {
            FIELD["u"]: fields[0].tolist(),
            FIELD["v"]: fields[1].tolist(),
            FIELD["w"]: fields[2].tolist(),
            FIELD["delta"]: np.full(target.shape, delta, dtype=float).tolist(),
            FIELD["target"]: target.tolist(),
        },
    }


def _prepare_component_studies(
    manifest_path: Path, manifest: Mapping[str, Any], entries: Sequence[Mapping[str, Any]], component: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    default_ratio = int(manifest.get("filter_ratio", 4))
    default_points = int(manifest.get("atlas_grid_points", 17))
    studies: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    for entry in entries:
        path = _resolve_dataset_path(manifest_path, entry)
        role = str(entry.get("role", "")).upper()
        ratio = int(entry.get("filter_ratio", default_ratio))
        points = int(entry.get("atlas_grid_points", default_points))
        velocity, spacing = _load_velocity(path)
        filtered, residual, delta = _sgs_residual(velocity, spacing, ratio)
        study = _coarse_study(
            study_id=str(entry["study_id"]), role=role, velocity=filtered, residual=residual,
            spacing=spacing, filter_ratio=ratio, atlas_grid_points=points,
            subcube_offset=entry.get("subcube_offset"), component=component,
        )
        studies.append(study)
        target_arr = np.asarray(study["fields"][FIELD["target"]], dtype=float)
        receipts.append({
            "study_id": str(entry["study_id"]),
            "role": role,
            "regime_id": str(entry.get("regime_id", "")),
            "source_path": str(path),
            "source_sha256": _sha256_file(path),
            "source_shape": list(velocity[0].shape),
            "spacing": [float(x) for x in spacing],
            "filter_ratio": ratio,
            "filter_width_geometric": delta,
            "atlas_grid_points": points,
            "subcube_offset": [int(x) for x in entry.get("subcube_offset", (0, 0, 0))],
            "target_rms": float(np.sqrt(np.mean(target_arr * target_arr))),
            "target_mean": float(np.mean(target_arr)),
        })
    return studies, receipts


def _null_studies(studies: Sequence[Mapping[str, Any]], component: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for study in studies:
        row = json.loads(json.dumps(study))
        target = np.asarray(row["fields"][FIELD["target"]], dtype=float)
        digest = hashlib.sha256(f"{component}:{row['study_id']}".encode("utf-8")).digest()
        shifts = tuple(1 + int(digest[i]) % max(1, target.shape[i] - 1) for i in range(3))
        row["fields"][FIELD["target"]] = np.roll(target, shifts, axis=(0, 1, 2)).tolist()
        row["study_id"] = str(row["study_id"]) + "-NULL"
        out.append(row)
    return out


def _request(
    *, component: str, studies: Sequence[Mapping[str, Any]], fit_tolerance: float,
    rank_shell_budget: int, factor_depth_budget: int, axis_birth_trial_budget: int,
    null_control: bool,
) -> dict[str, Any]:
    return {
        "entry_mode": "PRIMITIVE_FIELD_RESIDUAL_LANGUAGE_DISCOVERY",
        "residual_driven_language_expansion": True,
        "problem_id": f"BLIND-DNS-SGS-{component.upper()}" + ("-NULL" if null_control else ""),
        "domain_id": "mechanics",
        "question": (
            "Explain an attested unresolved coarse-graining acceleration field from masked resolved primitive fields. "
            "Birth local operator coordinates internally from translation/algebra primitives. Do not use a named turbulence-closure catalogue."
        ),
        "fit_tolerance_nrmse": float(fit_tolerance),
        "complexity_level": 1,
        "operator_language_search_budget": int(rank_shell_budget),
        "residual_language_factor_depth_budget": int(factor_depth_budget),
        "axis_birth_trial_budget": int(axis_birth_trial_budget),
        "axis_birth_sparse_search_allowed": True,
        "primitive_field_request": {
            "studies": list(studies),
            "coordinate_dimensions": {COORD["x"]: DIM_LENGTH, COORD["y"]: DIM_LENGTH, COORD["z"]: DIM_LENGTH},
            "field_dimensions": {
                FIELD["u"]: DIM_VELOCITY,
                FIELD["v"]: DIM_VELOCITY,
                FIELD["w"]: DIM_VELOCITY,
                FIELD["delta"]: DIM_LENGTH,
                FIELD["target"]: DIM_ACCELERATION,
            },
            "target_field": FIELD["target"],
            "target_action_mode": "DIRECT_FIELD_VALUE",
            "predictor_fields": [FIELD["u"], FIELD["v"], FIELD["w"], FIELD["delta"]],
        },
    }


def _terminal_residual_receipt(receipt: Mapping[str, Any]) -> Mapping[str, Any]:
    if str(receipt.get("schema", "")) == "phi-adaptive-research-kernel-scale-invariant-primitive-field/v1":
        return dict(receipt.get("normalized_inner_receipt", {}))
    return receipt


def _selected_specs(receipt: Mapping[str, Any]) -> list[dict[str, Any]]:
    terminal = _terminal_residual_receipt(receipt)
    final = dict(terminal.get("final_language_receipt", {}))
    born = dict(final.get("primitive_field_operator_birth", {}).get("candidate_axes", {}))
    selected = list(receipt.get("result", {}).get("effective_predictor_variables", ()))
    return [{"axis_id": axis, "signature": born.get(axis)} for axis in selected]


def _decode_signature(spec: Mapping[str, Any] | None) -> str | None:
    if not spec:
        return None
    rank = int(spec.get("moment_rank", 0))
    response = str(spec.get("response_field", "?"))
    coord = str(spec.get("coordinate", "?"))
    factors = []
    if spec.get("carrier_factors"):
        for f in spec.get("carrier_factors", ()):
            f = dict(f)
            factors.append(f"{f.get('field')}^{int(f.get('power', 0))}")
    elif spec.get("carrier_field") is not None and int(spec.get("carrier_power", 0)) != 0:
        factors.append(f"{spec.get('carrier_field')}^{int(spec.get('carrier_power', 0))}")
    left = "*".join(factors)
    op = f"D[{coord}]^{rank}({response})"
    return f"{left}*{op}" if left else op


def _component_summary(component: str, receipt: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(receipt.get("result", {}))
    best = dict(result.get("best_hypothesis") or {})
    sealed = dict(result.get("sealed_holdout_evaluation") or {})
    specs = _selected_specs(receipt)
    terminal = _terminal_residual_receipt(receipt)
    chart = dict(receipt.get("scale_invariant_representation_birth", {})) if isinstance(receipt.get("scale_invariant_representation_birth"), Mapping) else {}
    return {
        "component": component,
        "status": result.get("status"),
        "selected_algebra_carrier_factor_depth": terminal.get("selected_algebra_carrier_factor_depth"),
        "representation_chart_status": chart.get("status"),
        "representation_chart_digest": chart.get("digest"),
        "discovery_holdout_nrmse": best.get("holdout_nrmse"),
        "sealed_nrmse": sealed.get("nrmse"),
        "sealed_rmse": sealed.get("rmse"),
        "selected_axes": [
            {**row, "postfreeze_generic_decode": _decode_signature(row.get("signature"))}
            for row in specs
        ],
        "parameters": best.get("parameters"),
        "causal_status": result.get("causal_status"),
        "scientific_law_established": result.get("scientific_law_established"),
        "atlas_native": receipt.get("atlas_claim", {}).get("atlas_native"),
        "atlas_claim_status": receipt.get("atlas_claim", {}).get("status"),
        "receipt_digest": receipt.get("digest"),
    }


def _freeze_manifest(
    manifest_path: Path, manifest: Mapping[str, Any], entries: Sequence[Mapping[str, Any]], components: Sequence[str],
    fit_tolerance: float, rank_shell_budget: int, factor_depth_budget: int, axis_birth_trial_budget: int,
) -> dict[str, Any]:
    files = []
    for entry in entries:
        p = _resolve_dataset_path(manifest_path, entry)
        files.append({
            "study_id": str(entry["study_id"]), "role": str(entry["role"]).upper(),
            "regime_id": str(entry.get("regime_id", "")), "source_sha256": _sha256_file(p),
            "source_size": p.stat().st_size,
        })
    discovery_regimes = sorted({str(x.get("regime_id", "")) for x in entries if str(x.get("role", "")).upper() == "DISCOVERY"})
    sealed_regimes = sorted({str(x.get("regime_id", "")) for x in entries if str(x.get("role", "")).upper() == "SEALED_HOLDOUT"})
    payload = {
        "schema": "phi-dns-turbulence-closure-freeze/v1",
        "manifest_schema": manifest.get("schema"),
        "manifest_sha256": _sha256_file(manifest_path),
        "components": list(components),
        "datasets": files,
        "discovery_regime_ids": discovery_regimes,
        "sealed_regime_ids": sealed_regimes,
        "regimes_disjoint": set(discovery_regimes).isdisjoint(sealed_regimes),
        "fit_tolerance_nrmse": float(fit_tolerance),
        "operator_rank_shell_budget": int(rank_shell_budget),
        "carrier_factor_depth_budget": int(factor_depth_budget),
        "axis_birth_trial_budget": int(axis_birth_trial_budget),
        "closure_catalog_supplied_to_atlas": False,
        "derived_derivative_predictors_supplied_to_atlas": False,
        "target_is_attested_dns_coarse_graining_residual": True,
        "target_excluded_from_predictor_language": True,
        "resource_budgets_are_scientific_ceilings": False,
    }
    payload["digest"] = digest_payload(payload)
    return payload


def run_experiment(
    *, manifest_path: str | Path, components: Sequence[str] = ("x",), fit_tolerance: float = 0.25,
    rank_shell_budget: int = 4, factor_depth_budget: int = 3, axis_birth_trial_budget: int = 4096,
    run_null_control: bool = True, root: str | Path | None = None,
) -> dict[str, Any]:
    manifest_path = Path(manifest_path).resolve()
    manifest = _load_json(manifest_path)
    entries = _manifest_entries(manifest)
    components = _canonical_component_list(components)
    freeze = _freeze_manifest(
        manifest_path, manifest, entries, components, fit_tolerance,
        rank_shell_budget, factor_depth_budget, axis_birth_trial_budget,
    )
    if not freeze["regimes_disjoint"]:
        raise ValueError("transfer experiment requires discovery and sealed regime_id sets to be disjoint")

    api = LawSpaceAPI(Path(root or Path(__file__).resolve().parents[1]).resolve())
    component_reports = []
    dataset_receipts: dict[str, list[dict[str, Any]]] = {}
    null_reports = []
    for component in components:
        studies, prep = _prepare_component_studies(manifest_path, manifest, entries, component)
        dataset_receipts[component] = prep
        request = _request(
            component=component, studies=studies, fit_tolerance=fit_tolerance,
            rank_shell_budget=rank_shell_budget, factor_depth_budget=factor_depth_budget,
            axis_birth_trial_budget=axis_birth_trial_budget, null_control=False,
        )
        receipt = api.advance_adaptive_research(request)
        summary = _component_summary(component, receipt)
        component_reports.append({"summary": summary, "execution_receipt": receipt})
        if run_null_control:
            null_request = _request(
                component=component, studies=_null_studies(studies, component), fit_tolerance=fit_tolerance,
                rank_shell_budget=rank_shell_budget, factor_depth_budget=factor_depth_budget,
                axis_birth_trial_budget=axis_birth_trial_budget, null_control=True,
            )
            null_receipt = api.advance_adaptive_research(null_request)
            null_reports.append({"summary": _component_summary(component, null_receipt), "execution_receipt": null_receipt})

    protocol_checks = {
        "DATASET_FREEZE_CREATED": bool(freeze.get("digest")),
        "DISCOVERY_AND_SEALED_REGIMES_DISJOINT": freeze.get("regimes_disjoint") is True,
        "NO_NAMED_CLOSURE_CATALOG_SUPPLIED": freeze.get("closure_catalog_supplied_to_atlas") is False,
        "NO_DERIVED_DERIVATIVE_PREDICTORS_SUPPLIED": freeze.get("derived_derivative_predictors_supplied_to_atlas") is False,
        "TARGET_EXCLUDED_FROM_PREDICTOR_LANGUAGE": freeze.get("target_excluded_from_predictor_language") is True,
        "ALL_TOP_LEVEL_ATLAS_PROVENANCE_ACCEPTED": all(
            row["summary"].get("atlas_native") is True for row in component_reports
        ),
        "ALL_SEALED_HOLDOUTS_EVALUATED": all(
            row["execution_receipt"].get("result", {}).get("sealed_holdout_evaluation", {}).get("status") == "SEALED_HOLDOUT_EVALUATED"
            for row in component_reports
        ),
        "NO_SCIENTIFIC_AUTO_PROMOTION": all(
            row["summary"].get("scientific_law_established") is False for row in component_reports
        ),
    }
    if run_null_control:
        protocol_checks["NULL_CONTROL_TOP_LEVEL_PROVENANCE_ACCEPTED"] = all(
            row["summary"].get("atlas_native") is True for row in null_reports
        )

    outcomes = []
    for row in component_reports:
        component = row["summary"]["component"]
        real = row["summary"].get("sealed_nrmse")
        null = next((x["summary"].get("sealed_nrmse") for x in null_reports if x["summary"]["component"] == component), None)
        real_f = float(real) if real is not None else float("inf")
        null_f = float(null) if null is not None else None
        survives = bool(real_f <= float(fit_tolerance))
        null_rejected = bool(null_f is None or (math.isfinite(null_f) and real_f < 0.8 * null_f))
        if survives and null_rejected:
            status = "TRANSFER_CANDIDATE_SURVIVES_CURRENT_SEALED_AND_NULL_EVIDENCE_NOT_LAW"
        elif survives:
            status = "TRANSFER_FIT_SURVIVES_BUT_NULL_CONTROL_NOT_REJECTED"
        else:
            status = "REPRESENTATION_GAP_OR_TRANSFER_FAILURE"
        outcomes.append({
            "component": component, "status": status,
            "real_sealed_nrmse": real_f, "null_sealed_nrmse": null_f,
            "fit_tolerance_nrmse": float(fit_tolerance), "null_rejected": null_rejected,
        })

    protocol_passed = sum(bool(v) for v in protocol_checks.values())
    overall_science = (
        "TRANSFER_CANDIDATE_SURVIVES_CURRENT_SEALED_AND_NULL_EVIDENCE_NOT_LAW"
        if outcomes and all(x["status"] == "TRANSFER_CANDIDATE_SURVIVES_CURRENT_SEALED_AND_NULL_EVIDENCE_NOT_LAW" for x in outcomes)
        else "EXPERIMENT_COMPLETED_WITHOUT_TRANSFER_LAW_PROMOTION"
    )
    payload = {
        "schema": SCHEMA,
        "owner": OWNER_ID,
        "runtime_release_id": api.runtime.current_release_id(),
        "experiment_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "status": overall_science,
        "protocol_status": "PASS_PROTOCOL_INTEGRITY" if protocol_passed == len(protocol_checks) else "FAIL_PROTOCOL_INTEGRITY",
        "protocol_passed": protocol_passed,
        "protocol_total": len(protocol_checks),
        "protocol_checks": [{"check": k, "status": "PASS" if v else "FAIL"} for k, v in protocol_checks.items()],
        "freeze": freeze,
        "dataset_preparation_receipts": dataset_receipts,
        "component_outcomes": outcomes,
        "components": component_reports,
        "null_controls": null_reports,
        "postfreeze_decode": {
            "coordinate_mask": {COORD["x"]: "x", COORD["y"]: "y", COORD["z"]: "z"},
            "field_mask": {FIELD["u"]: "filtered_u", FIELD["v"]: "filtered_v", FIELD["w"]: "filtered_w", FIELD["delta"]: "filter_width", FIELD["target"]: "unresolved_convective_acceleration"},
            "decode_is_verification_and_interpretation_only": True,
        },
        "claim_boundary": {
            "new_turbulence_law_claimed": False,
            "universal_closure_claimed": False,
            "causality_established": False,
            "dns_target_is_independent_empirical_measurement": False,
            "dns_target_is_attested_deterministic_transform_of_supplied_dns_snapshot": True,
            "known_closure_catalog_used_for_candidate_selection": False,
            "sealed_regime_used_for_axis_birth": False,
            "null_control_used_for_axis_birth": False,
            "representation_gap_is_valid_outcome": True,
        },
    }
    payload["digest"] = digest_payload(payload)
    return payload



def _validate_report_digest(report: Mapping[str, Any]) -> bool:
    embedded = report.get("digest")
    if not embedded:
        return False
    return str(embedded) == digest_payload({k: v for k, v in report.items() if k != "digest"})


def _prior_component_receipt(report: Mapping[str, Any], component: str) -> tuple[Mapping[str, Any], str]:
    outcome_status = ""
    for row in report.get("component_outcomes", ()):
        if str(row.get("component", "")) == component:
            outcome_status = str(row.get("status", ""))
            break
    for row in report.get("components", ()):
        summary = dict(row.get("summary", {}))
        if str(summary.get("component", "")) == component:
            receipt = dict(row.get("execution_receipt", {}))
            status = outcome_status or str(summary.get("status", ""))
            return receipt, status
    raise ValueError(f"prior report does not contain component {component!r}")


def _sealed_hashes_from_freeze(freeze: Mapping[str, Any]) -> set[str]:
    return {
        str(row.get("source_sha256"))
        for row in freeze.get("datasets", ())
        if str(row.get("role", "")).upper() == "SEALED_HOLDOUT" and row.get("source_sha256")
    }


def run_scale_invariant_extension(
    *, manifest_path: str | Path, components: Sequence[str] = ("x",), fit_tolerance: float = 0.25,
    rank_shell_budget: int = 4, factor_depth_budget: int = 3, axis_birth_trial_budget: int = 4096,
    run_null_control: bool = True, prior_report_path: str | Path | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Run a representation-level continuation after an attested raw-chart gap.

    The prior gap may have exposed an earlier sealed set.  If the current sealed
    source hashes overlap that prior set, the run is explicitly development
    replay and cannot be promoted as fresh transfer evidence even if the fit
    improves.  A new manifest with unseen sealed hashes is required for a fresh
    scientific holdout.
    """
    manifest_path = Path(manifest_path).resolve()
    manifest = _load_json(manifest_path)
    entries = _manifest_entries(manifest)
    components = _canonical_component_list(components)
    freeze = _freeze_manifest(
        manifest_path, manifest, entries, components, fit_tolerance,
        rank_shell_budget, factor_depth_budget, axis_birth_trial_budget,
    )
    if not freeze["regimes_disjoint"]:
        raise ValueError("transfer experiment requires discovery and sealed regime_id sets to be disjoint")
    api = LawSpaceAPI(Path(root or Path(__file__).resolve().parents[1]).resolve())

    prior_report: dict[str, Any] | None = None
    prior_report_digest_valid = False
    if prior_report_path is not None:
        prior_report = _load_json(Path(prior_report_path).resolve())
        prior_report_digest_valid = _validate_report_digest(prior_report)
        if not prior_report_digest_valid:
            raise ValueError("prior report digest is invalid")

    prior_exposed_hashes = _sealed_hashes_from_freeze(dict(prior_report.get("freeze", {}))) if prior_report else set()
    current_sealed_hashes = _sealed_hashes_from_freeze(freeze)
    sealed_overlap = sorted(prior_exposed_hashes & current_sealed_hashes)
    fresh_sealed_evidence = bool(current_sealed_hashes) and not sealed_overlap

    component_reports: list[dict[str, Any]] = []
    null_reports: list[dict[str, Any]] = []
    dataset_receipts: dict[str, list[dict[str, Any]]] = {}
    prior_gap_receipts: dict[str, dict[str, Any]] = {}

    for component in components:
        studies, prep = _prepare_component_studies(manifest_path, manifest, entries, component)
        dataset_receipts[component] = prep
        if prior_report is not None:
            raw_receipt, prior_status = _prior_component_receipt(prior_report, component)
        else:
            raw_request = _request(
                component=component, studies=studies, fit_tolerance=fit_tolerance,
                rank_shell_budget=rank_shell_budget, factor_depth_budget=factor_depth_budget,
                axis_birth_trial_budget=axis_birth_trial_budget, null_control=False,
            )
            raw_receipt = api.advance_adaptive_research(raw_request)
            prior_status = str(raw_receipt.get("result", {}).get("status", ""))
            # This execution has just exposed the current sealed target, so it is
            # not fresh evidence for the following representation adaptation.
            fresh_sealed_evidence = False
            sealed_overlap = sorted(current_sealed_hashes)
        if "GAP" not in prior_status.upper():
            raise ValueError(f"component {component}: prior run is not an attested representation gap")
        prior_gap = {
            "status": prior_status,
            "receipt_digest": raw_receipt.get("digest"),
            "atlas_native": raw_receipt.get("atlas_claim", {}).get("atlas_native"),
            "source_report_digest": prior_report.get("digest") if prior_report else None,
        }
        prior_gap["digest"] = digest_payload(prior_gap)
        prior_gap_receipts[component] = prior_gap

        request = _request(
            component=component, studies=studies, fit_tolerance=fit_tolerance,
            rank_shell_budget=rank_shell_budget, factor_depth_budget=factor_depth_budget,
            axis_birth_trial_budget=axis_birth_trial_budget, null_control=False,
        )
        request["entry_mode"] = "PRIMITIVE_FIELD_SCALE_INVARIANT_DISCOVERY"
        request["scale_invariant_representation_birth"] = True
        request["attested_prior_representation_gap"] = prior_gap
        receipt = api.advance_adaptive_research(request)
        component_reports.append({"summary": _component_summary(component, receipt), "execution_receipt": receipt})

        if run_null_control:
            null_request = _request(
                component=component, studies=_null_studies(studies, component), fit_tolerance=fit_tolerance,
                rank_shell_budget=rank_shell_budget, factor_depth_budget=factor_depth_budget,
                axis_birth_trial_budget=axis_birth_trial_budget, null_control=True,
            )
            null_request["entry_mode"] = "PRIMITIVE_FIELD_SCALE_INVARIANT_DISCOVERY"
            null_request["scale_invariant_representation_birth"] = True
            null_request["attested_prior_representation_gap"] = prior_gap
            null_receipt = api.advance_adaptive_research(null_request)
            null_reports.append({"summary": _component_summary(component, null_receipt), "execution_receipt": null_receipt})

    protocol_checks = {
        "DATASET_FREEZE_CREATED": bool(freeze.get("digest")),
        "DISCOVERY_AND_SEALED_REGIMES_DISJOINT": freeze.get("regimes_disjoint") is True,
        "PRIOR_GAP_ATTESTED_FOR_EACH_COMPONENT": all(bool(prior_gap_receipts[c].get("receipt_digest")) and "GAP" in str(prior_gap_receipts[c].get("status", "")).upper() for c in components),
        "SCALE_REPRESENTATION_BORN_FOR_EACH_COMPONENT": all(row["summary"].get("representation_chart_status") == "SCALE_INVARIANT_REPRESENTATION_BORN" for row in component_reports),
        "SCALE_CHART_DISCOVERY_ONLY": all(row["execution_receipt"].get("claim_boundary", {}).get("scale_chart_born_from_discovery_predictors_only") is True for row in component_reports),
        "SEALED_TARGET_NOT_USED_FOR_SCALE_BIRTH": all(row["execution_receipt"].get("claim_boundary", {}).get("sealed_target_values_used_for_scale_chart_birth") is False for row in component_reports),
        "SEALED_TARGET_NOT_USED_FOR_SCALE_ESTIMATION": all(row["execution_receipt"].get("claim_boundary", {}).get("sealed_target_values_used_for_scale_estimation") is False for row in component_reports),
        "NO_NAMED_DIMENSIONLESS_GROUP_CATALOG": all(row["execution_receipt"].get("claim_boundary", {}).get("named_dimensionless_group_catalog_used") is False for row in component_reports),
        "ALL_TOP_LEVEL_ATLAS_PROVENANCE_ACCEPTED": all(row["summary"].get("atlas_native") is True for row in component_reports),
        "ALL_SEALED_HOLDOUTS_EVALUATED": all(row["execution_receipt"].get("result", {}).get("sealed_holdout_evaluation", {}).get("status") == "SEALED_HOLDOUT_EVALUATED" for row in component_reports),
        "NO_SCIENTIFIC_AUTO_PROMOTION": all(row["summary"].get("scientific_law_established") is False for row in component_reports),
    }
    if run_null_control:
        protocol_checks["NULL_CONTROL_TOP_LEVEL_PROVENANCE_ACCEPTED"] = all(row["summary"].get("atlas_native") is True for row in null_reports)

    outcomes = []
    for row in component_reports:
        component = str(row["summary"]["component"])
        real = row["summary"].get("sealed_nrmse")
        null = next((x["summary"].get("sealed_nrmse") for x in null_reports if x["summary"]["component"] == component), None)
        real_f = float(real) if real is not None else float("inf")
        null_f = float(null) if null is not None else None
        survives = bool(real_f <= float(fit_tolerance))
        null_rejected = bool(null_f is None or (math.isfinite(null_f) and real_f < 0.8 * null_f))
        if survives and null_rejected and fresh_sealed_evidence:
            status = "FRESH_TRANSFER_CANDIDATE_SURVIVES_SCALE_INVARIANT_SEALED_AND_NULL_EVIDENCE_NOT_LAW"
        elif survives and null_rejected:
            status = "DEVELOPMENT_REPLAY_FIT_SURVIVES_REQUIRES_FRESH_SEALED"
        elif survives:
            status = "SCALE_INVARIANT_FIT_SURVIVES_BUT_NULL_CONTROL_NOT_REJECTED"
        else:
            status = "SCALE_INVARIANT_REPRESENTATION_STILL_GAPPED"
        outcomes.append({
            "component": component, "status": status,
            "real_sealed_nrmse": real_f, "null_sealed_nrmse": null_f,
            "fit_tolerance_nrmse": float(fit_tolerance), "null_rejected": null_rejected,
            "fresh_sealed_evidence": fresh_sealed_evidence,
        })

    protocol_passed = sum(bool(v) for v in protocol_checks.values())
    fresh_survival = bool(outcomes) and all(x["status"] == "FRESH_TRANSFER_CANDIDATE_SURVIVES_SCALE_INVARIANT_SEALED_AND_NULL_EVIDENCE_NOT_LAW" for x in outcomes)
    development_survival = bool(outcomes) and all(x["status"] in {"FRESH_TRANSFER_CANDIDATE_SURVIVES_SCALE_INVARIANT_SEALED_AND_NULL_EVIDENCE_NOT_LAW", "DEVELOPMENT_REPLAY_FIT_SURVIVES_REQUIRES_FRESH_SEALED"} for x in outcomes)
    if fresh_survival:
        overall = "FRESH_SCALE_INVARIANT_TRANSFER_CANDIDATE_SURVIVES_NOT_LAW"
    elif development_survival:
        overall = "SCALE_INVARIANT_DEVELOPMENT_REPLAY_SURVIVES_REQUIRES_FRESH_SEALED"
    else:
        overall = "SCALE_INVARIANT_REPRESENTATION_EVALUATED_WITHOUT_TRANSFER_PROMOTION"

    payload = {
        "schema": SCALE_SCHEMA, "owner": SCALE_OWNER_ID,
        "runtime_release_id": api.runtime.current_release_id(),
        "experiment_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "status": overall,
        "protocol_status": "PASS_PROTOCOL_INTEGRITY" if protocol_passed == len(protocol_checks) else "FAIL_PROTOCOL_INTEGRITY",
        "protocol_passed": protocol_passed, "protocol_total": len(protocol_checks),
        "protocol_checks": [{"check": k, "status": "PASS" if v else "FAIL"} for k, v in protocol_checks.items()],
        "freeze": freeze,
        "prior_report": {
            "path": str(Path(prior_report_path).resolve()) if prior_report_path is not None else None,
            "digest": prior_report.get("digest") if prior_report else None,
            "digest_valid": prior_report_digest_valid if prior_report else None,
            "previously_exposed_sealed_hashes": sorted(prior_exposed_hashes),
        },
        "holdout_reuse_assessment": {
            "fresh_sealed_evidence": fresh_sealed_evidence,
            "overlapping_previously_exposed_sealed_hashes": sealed_overlap,
            "same_exposed_holdout_may_be_used_for_development_diagnostics_only": bool(sealed_overlap),
            "fresh_unseen_sealed_required_for_scientific_transfer_promotion": True,
        },
        "prior_gap_receipts": prior_gap_receipts,
        "dataset_preparation_receipts": dataset_receipts,
        "component_outcomes": outcomes,
        "components": component_reports,
        "null_controls": null_reports,
        "claim_boundary": {
            "new_turbulence_law_claimed": False,
            "universal_closure_claimed": False,
            "causality_established": False,
            "named_dimensionless_group_catalog_used": False,
            "reynolds_number_supplied_to_representation_owner": False,
            "sealed_target_used_for_representation_birth": False,
            "previously_exposed_holdout_can_establish_new_transfer_claim": False,
            "fresh_unseen_holdout_required_after_representation_adaptation": True,
        },
    }
    payload["digest"] = digest_payload(payload)
    return payload


def _write_template(path: Path) -> None:
    template = {
        "schema": MANIFEST_SCHEMA,
        "filter_ratio": 4,
        "atlas_grid_points": 17,
        "datasets": [
            {
                "study_id": "DNS-DISCOVERY-01",
                "role": "DISCOVERY",
                "regime_id": "FLOW-OR-REYNOLDS-A",
                "path": "data/discovery_01.npz",
                "subcube_offset": [0, 0, 0],
            },
            {
                "study_id": "DNS-DISCOVERY-02",
                "role": "DISCOVERY",
                "regime_id": "FLOW-OR-REYNOLDS-A",
                "path": "data/discovery_02.npz",
                "subcube_offset": [4, 4, 4],
            },
            {
                "study_id": "DNS-SEALED-01",
                "role": "SEALED_HOLDOUT",
                "regime_id": "FLOW-OR-REYNOLDS-B",
                "path": "data/sealed_01.npz",
                "subcube_offset": [0, 0, 0],
            },
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", help="JSON dataset manifest")
    parser.add_argument("--components", default="x", help="comma-separated x,y,z")
    parser.add_argument("--fit-tolerance", type=float, default=0.25)
    parser.add_argument("--rank-shell-budget", type=int, default=4)
    parser.add_argument("--factor-depth-budget", type=int, default=3)
    parser.add_argument("--axis-birth-trial-budget", type=int, default=4096)
    parser.add_argument("--skip-null-control", action="store_true")
    parser.add_argument("--representation-mode", choices=("raw", "scale-invariant-after-gap"), default="raw")
    parser.add_argument("--prior-report", help="prior raw DNS report that attests the representation gap")
    parser.add_argument("--output", default="reports/TURBULENCE_DNS_CLOSURE_CURRENT.json")
    parser.add_argument("--write-manifest-template")
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    if args.write_manifest_template:
        _write_template(Path(args.write_manifest_template))
        print(json.dumps({"status": "MANIFEST_TEMPLATE_WRITTEN", "output": args.write_manifest_template}, ensure_ascii=False, indent=2))
        return 0
    if not args.manifest:
        parser.error("--manifest is required unless --write-manifest-template is used")
    runner = run_scale_invariant_extension if args.representation_mode == "scale-invariant-after-gap" else run_experiment
    kwargs = dict(
        manifest_path=args.manifest,
        components=_canonical_component_list(args.components),
        fit_tolerance=args.fit_tolerance,
        rank_shell_budget=args.rank_shell_budget,
        factor_depth_budget=args.factor_depth_budget,
        axis_birth_trial_budget=args.axis_birth_trial_budget,
        run_null_control=not args.skip_null_control,
    )
    if args.representation_mode == "scale-invariant-after-gap":
        kwargs["prior_report_path"] = args.prior_report
    report = runner(**kwargs)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.summary:
        print(json.dumps({
            "status": report["status"], "protocol_status": report["protocol_status"],
            "protocol_passed": report["protocol_passed"], "protocol_total": report["protocol_total"],
            "component_outcomes": report["component_outcomes"], "digest": report["digest"],
            "output": str(output),
        }, ensure_ascii=False, indent=2))
    else:
        print(str(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
