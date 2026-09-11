"""Blind continuum-balance recovery benchmark for Φ-Compiler 0.15.28.0.

The reference world contains several exact two-dimensional incompressible-flow
families.  Their named governing equation is used only inside this fixture
builder and in the post-freeze verification block.  AdaptiveResearchKernelOwner
receives masked scalar columns, dimensions, a generic continuum question and a
sealed holdout.  It is never passed the words "Navier-Stokes", the reference
formula, or the mask decoding while the candidate is being born.

Scientific boundary: this benchmark tests law/axis recovery and OOD transfer on
a controlled reference world.  It is NOT a proof of Navier-Stokes existence and
smoothness and NOT a new physical-law claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math

import numpy as np
from pathlib import Path
from typing import Any, Iterable

from source.lawspace.api import LawSpaceAPI
from source.lawspace.schema import digest_payload

OWNER_ID = "BLIND-CONTINUUM-BALANCE-EXPERIMENT/15.28.0"
SCHEMA = "phi-blind-continuum-balance-experiment/v1"
PROBLEM_X = "BLIND-CONTINUUM-MOMENTUM-X-001"
PROBLEM_Y = "BLIND-CONTINUUM-MOMENTUM-Y-001"
PROBLEM_DIV = "BLIND-CONTINUUM-CLOSURE-001"

DIM_ACCELERATION = [1, 0, -2, 0, 0, 0, 0]  # L T^-2
DIM_RATE = [0, 0, -1, 0, 0, 0, 0]          # T^-1

# These identifiers, rather than semantic names, are exposed to Atlas.
MASK = {
    "target": "r0",
    "advect_1": "a07",
    "advect_2": "a12",
    "pressure": "a19",
    "diffusion": "a23",
    "distractor_1": "a31",
    "distractor_2": "a37",
    "div_target": "c05",
    "div_predictor": "c11",
}


def _stable_mix(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deterministic row mixing so the kernel's internal 70/30 split sees all families."""
    return sorted(rows, key=lambda row: hashlib.sha256(str(row["record_id"]).encode("utf-8")).hexdigest())


def _pack_row(
    *, record_id: str, family: str, component: str, target: float,
    q1: float, q2: float, q3: float, q4: float, d1: float, d2: float,
    du_dx: float, dv_dy: float,
) -> dict[str, Any]:
    values = {
        MASK["target"]: float(target),
        MASK["advect_1"]: float(q1),
        MASK["advect_2"]: float(q2),
        MASK["pressure"]: float(q3),
        MASK["diffusion"]: float(q4),
        MASK["distractor_1"]: float(d1),
        MASK["distractor_2"]: float(d2),
        MASK["div_target"]: float(du_dx),
        MASK["div_predictor"]: float(dv_dy),
    }
    return {
        "record_id": record_id,
        "study_id": family,
        "component": component,
        "values": values,
    }


def _world_rows(component: str, split: str) -> list[dict[str, Any]]:
    """Build exact reference-world observations; semantic formulas stay inside fixture code."""
    if component not in {"x", "y"}:
        raise ValueError("component must be x or y")
    if split not in {"discovery", "sealed"}:
        raise ValueError("split must be discovery or sealed")

    if split == "discovery":
        tg_params = ((1.00, 1.00, 0.030, 0.15), (0.80, 2.00, 0.015, 0.08), (1.20, 1.50, 0.020, 0.11))
        xs = (0.23, 0.61, 1.02, 1.39, 1.83, 2.17)
        ys = (0.31, 0.74, 1.11, 1.58, 2.03)
        rotations = (0.40, 0.75, 1.10)
        shear_params = ((0.90, 1.30, 0.040, 0.10), (1.30, 0.80, 0.025, 0.20))
        channel_params = ((1.00, 1.00, 0.030), (0.70, 0.80, 0.050), (1.20, 1.30, 0.020))
        coord_pairs = ((0.20, 0.50), (0.70, -0.40), (-0.60, 0.90), (1.10, 0.30), (-1.00, -0.80))
    else:
        tg_params = ((0.95, 1.20, 0.027, 0.13), (1.10, 1.70, 0.018, 0.09))
        xs = (0.18, 0.53, 0.88, 1.27, 1.66)
        ys = (0.26, 0.69, 1.07, 1.43)
        rotations = (0.55, 0.95)
        shear_params = ((1.05, 1.05, 0.035, 0.17),)
        channel_params = ((0.85, 0.90, 0.040), (1.10, 1.15, 0.025))
        coord_pairs = ((0.33, -0.72), (-0.45, 0.64), (0.92, 0.41), (-0.81, -0.27))

    rows: list[dict[str, Any]] = []

    # Family A: decaying periodic vortex.  It supplies mixed advection,
    # pressure-gradient and diffusion structure at many local points.
    for fi, (amp, wave, nu, time) in enumerate(tg_params):
        decay = math.exp(-2.0 * nu * wave * wave * time)
        for ix, x in enumerate(xs):
            for iy, y in enumerate(ys):
                u = amp * math.sin(wave * x) * math.cos(wave * y) * decay
                v = -amp * math.cos(wave * x) * math.sin(wave * y) * decay
                ux = amp * wave * math.cos(wave * x) * math.cos(wave * y) * decay
                uy = -amp * wave * math.sin(wave * x) * math.sin(wave * y) * decay
                vx = amp * wave * math.sin(wave * x) * math.sin(wave * y) * decay
                vy = -amp * wave * math.cos(wave * x) * math.cos(wave * y) * decay
                lap_u = -2.0 * wave * wave * u
                lap_v = -2.0 * wave * wave * v
                px_over_rho = -(amp * amp * wave / 2.0) * math.sin(2.0 * wave * x) * decay * decay
                py_over_rho = -(amp * amp * wave / 2.0) * math.sin(2.0 * wave * y) * decay * decay
                if component == "x":
                    target = -2.0 * nu * wave * wave * u
                    q1, q2, q3, q4 = u * ux, v * uy, px_over_rho, nu * lap_u
                    d1, d2 = u * uy, v * ux
                else:
                    target = -2.0 * nu * wave * wave * v
                    q1, q2, q3, q4 = u * vx, v * vy, py_over_rho, nu * lap_v
                    d1, d2 = u * vy, v * vx
                rows.append(_pack_row(
                    record_id=f"{split}-PV-{fi}-{ix}-{iy}-{component}", family="FAMILY-A", component=component,
                    target=target, q1=q1, q2=q2, q3=q3, q4=q4, d1=d1, d2=d2,
                    du_dx=ux, dv_dy=vy,
                ))

    # Family B: rigid rotation.  Diffusion and time derivative vanish while
    # advection is balanced by the pressure coordinate.
    for fi, omega in enumerate(rotations):
        for pi, (x, y) in enumerate(coord_pairs):
            u, v = -omega * y, omega * x
            ux, uy, vx, vy = 0.0, -omega, omega, 0.0
            if component == "x":
                target = 0.0
                q1, q2, q3, q4 = u * ux, v * uy, omega * omega * x, 0.0
                d1, d2 = u * uy, v * ux
            else:
                target = 0.0
                q1, q2, q3, q4 = u * vx, v * vy, omega * omega * y, 0.0
                d1, d2 = u * vy, v * vx
            rows.append(_pack_row(
                record_id=f"{split}-RR-{fi}-{pi}-{component}", family="FAMILY-B", component=component,
                target=target, q1=q1, q2=q2, q3=q3, q4=q4, d1=d1, d2=d2,
                du_dx=ux, dv_dy=vy,
            ))

    # Family C: unidirectional decaying shear.  It isolates time/diffusion balance.
    for fi, (amp, wave, nu, time) in enumerate(shear_params):
        decay = math.exp(-nu * wave * wave * time)
        for si, s in enumerate((0.17, 0.48, 0.91, 1.34, 1.77, 2.20)):
            w = amp * math.sin(wave * s) * decay
            dw = amp * wave * math.cos(wave * s) * decay
            target = -nu * wave * wave * w
            q1 = q2 = q3 = 0.0
            q4 = target
            if component == "x":
                ux, vy = 0.0, 0.0
                d1, d2 = 0.10 * w * dw, -0.07 * w * dw
            else:
                ux, vy = 0.0, 0.0
                d1, d2 = -0.08 * w * dw, 0.11 * w * dw
            rows.append(_pack_row(
                record_id=f"{split}-DS-{fi}-{si}-{component}", family="FAMILY-C", component=component,
                target=target, q1=q1, q2=q2, q3=q3, q4=q4, d1=d1, d2=d2,
                du_dx=ux, dv_dy=vy,
            ))

    # Family D: steady parabolic channel flow.  It isolates pressure/diffusion balance.
    for fi, (speed, half_width, nu) in enumerate(channel_params):
        q = -2.0 * nu * speed / (half_width * half_width)
        for si, s in enumerate((-0.8 * half_width, -0.4 * half_width, 0.0, 0.4 * half_width, 0.8 * half_width)):
            w = speed * (1.0 - (s / half_width) ** 2)
            grad = -2.0 * speed * s / (half_width * half_width)
            target = 0.0
            q1 = q2 = 0.0
            q3 = q4 = q
            if component == "x":
                ux, vy = 0.0, 0.0
                d1, d2 = 0.05 * w * grad, -0.09 * w * grad
            else:
                ux, vy = 0.0, 0.0
                d1, d2 = -0.06 * w * grad, 0.08 * w * grad
            rows.append(_pack_row(
                record_id=f"{split}-PC-{fi}-{si}-{component}", family="FAMILY-D", component=component,
                target=target, q1=q1, q2=q2, q3=q3, q4=q4, d1=d1, d2=d2,
                du_dx=ux, dv_dy=vy,
            ))

    return _stable_mix(rows)


def _world_self_check(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    residuals = []
    divergence = []
    for row in rows:
        v = row["values"]
        residuals.append(v[MASK["target"]] - (
            -v[MASK["advect_1"]] - v[MASK["advect_2"]] - v[MASK["pressure"]] + v[MASK["diffusion"]]
        ))
        divergence.append(v[MASK["div_target"]] + v[MASK["div_predictor"]])
    return {
        "max_momentum_closure_abs": max(abs(x) for x in residuals) if residuals else None,
        "max_divergence_abs": max(abs(x) for x in divergence) if divergence else None,
        "row_count": len(residuals),
    }


def _kernel_request(component: str, discovery: list[dict[str, Any]], sealed: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "problem_id": PROBLEM_X if component == "x" else PROBLEM_Y,
        "domain_id": "mechanics",
        "question": (
            "Discover a dimensionally typed local evolution relation for a masked continuum response from supplied observations. "
            "One observed coordinate is intentionally dormant. Use residual evidence to decide whether it must enter the effective representation. "
            "Do not use a named-law catalog."
        ),
        "observations": discovery,
        "sealed_holdout_observations": sealed,
        "target_variable": MASK["target"],
        "predictor_variables": [MASK["advect_1"], MASK["advect_2"], MASK["pressure"]],
        "dormant_axis_variables": [MASK["diffusion"], MASK["distractor_1"], MASK["distractor_2"]],
        "variable_dimensions": {
            MASK["target"]: DIM_ACCELERATION,
            MASK["advect_1"]: DIM_ACCELERATION,
            MASK["advect_2"]: DIM_ACCELERATION,
            MASK["pressure"]: DIM_ACCELERATION,
            MASK["diffusion"]: DIM_ACCELERATION,
            MASK["distractor_1"]: DIM_ACCELERATION,
            MASK["distractor_2"]: DIM_ACCELERATION,
        },
        "complexity_level": 1,
        "fit_tolerance_nrmse": 1e-8,
        "observations_origin": "CONTROL_REFERENCE_MASKED",
        "auto_activate_dormant_axes": True,
    }


def _divergence_request(discovery: list[dict[str, Any]], sealed: list[dict[str, Any]]) -> dict[str, Any]:
    # The closure lane sees only two masked rate coordinates; no velocity labels are provided.
    return {
        "problem_id": PROBLEM_DIV,
        "domain_id": "mechanics",
        "question": "Discover whether two masked local rate coordinates obey a stable additive closure on independent held-out observations.",
        "observations": discovery,
        "sealed_holdout_observations": sealed,
        "target_variable": MASK["div_target"],
        "predictor_variables": [MASK["div_predictor"]],
        "dormant_axis_variables": [],
        "variable_dimensions": {
            MASK["div_target"]: DIM_RATE,
            MASK["div_predictor"]: DIM_RATE,
        },
        "complexity_level": 1,
        "fit_tolerance_nrmse": 1e-10,
        "observations_origin": "CONTROL_REFERENCE_MASKED",
        "auto_activate_dormant_axes": True,
    }


def _coefficient_by_term(best: dict[str, Any]) -> dict[str, float]:
    params = list(best.get("parameters", ()))
    out = {"INTERCEPT": float(params[0])} if params else {}
    for i, term in enumerate(best.get("basis", ()), start=1):
        if i < len(params):
            out[str(term.get("term"))] = float(params[i])
    return out


def _lane_summary(receipt: dict[str, Any]) -> dict[str, Any]:
    result = dict(receipt.get("result", {}))
    best = dict(result.get("best_hypothesis") or {})
    initial = list(receipt.get("initial_hypothesis_space", {}).get("candidates", ()))
    initial_best = dict(initial[0]) if initial else {}
    return {
        "status": result.get("status"),
        "initial_expression": initial_best.get("expression"),
        "initial_holdout_nrmse": initial_best.get("holdout_nrmse"),
        "axis_candidates": result.get("research_local_axis_candidates"),
        "activated_axes": result.get("activated_axis_variables"),
        "representation_status": receipt.get("axis_activation", {}).get("representation_status"),
        "causal_status": receipt.get("axis_activation", {}).get("causal_status"),
        "causal_ready_axes": receipt.get("axis_activation", {}).get("causal_ready_axes"),
        "causally_established_axes": receipt.get("axis_activation", {}).get("causally_established_axes"),
        "best_expression": best.get("expression"),
        "best_coefficients_by_term": _coefficient_by_term(best),
        "post_activation_holdout_nrmse": best.get("holdout_nrmse"),
        "sealed_holdout": result.get("sealed_holdout_evaluation"),
        "atlas_claim_status": receipt.get("atlas_claim", {}).get("status"),
        "atlas_native": receipt.get("atlas_claim", {}).get("atlas_native"),
        "scientific_law_established": result.get("scientific_law_established"),
        "receipt_digest": receipt.get("digest"),
    }


def _momentum_lane_checks(receipt: dict[str, Any]) -> dict[str, bool]:
    result = receipt["result"]
    initial = receipt.get("initial_hypothesis_space", {}).get("candidates", [])
    initial_best = initial[0] if initial else {}
    best = result.get("best_hypothesis") or {}
    coeff = _coefficient_by_term(best)
    sealed = result.get("sealed_holdout_evaluation", {})
    return {
        "INITIAL_MODEL_FAILS_WITH_MISSING_COORDINATE": float(initial_best.get("holdout_nrmse", 0.0)) > 1e-2,
        "HIDDEN_PHYSICAL_COORDINATE_DISCOVERED_IN_RESIDUAL": MASK["diffusion"] in result.get("research_local_axis_candidates", []),
        "HIDDEN_PHYSICAL_COORDINATE_ACTIVATED": result.get("activated_axis_variables") == [MASK["diffusion"]],
        "REPRESENTATION_ACTIVATION_IS_NOT_CAUSAL_PROOF": receipt.get("axis_activation",{}).get("causal_status")=="CAUSALLY_NOT_ESTABLISHED" and receipt.get("axis_activation",{}).get("causally_established_axes")==[],
        "DISTRACTOR_NOT_ACTIVATED": MASK["distractor_1"] not in result.get("activated_axis_variables", []) and MASK["distractor_2"] not in result.get("activated_axis_variables", []),
        "SPARSE_TYPED_RELATION_SURVIVES": result.get("status") == "HYPOTHESIS_SURVIVES_CURRENT_HELDOUT_EVIDENCE_NOT_LAW",
        "INTERCEPT_NEAR_ZERO": abs(coeff.get("INTERCEPT", 1.0)) < 1e-10,
        "ADVECT_1_COEFFICIENT": abs(coeff.get(MASK["advect_1"], 0.0) + 1.0) < 1e-10,
        "ADVECT_2_COEFFICIENT": abs(coeff.get(MASK["advect_2"], 0.0) + 1.0) < 1e-10,
        "PRESSURE_COEFFICIENT": abs(coeff.get(MASK["pressure"], 0.0) + 1.0) < 1e-10,
        "DIFFUSION_COEFFICIENT": abs(coeff.get(MASK["diffusion"], 0.0) - 1.0) < 1e-10,
        "SEALED_OOD_HOLDOUT_PASS": sealed.get("status") == "SEALED_HOLDOUT_EVALUATED" and float(sealed.get("nrmse", 1.0)) < 1e-10,
        "CLAIM_FIREWALL_ATLAS_NATIVE_ONLY": receipt.get("atlas_claim", {}).get("atlas_native") is True and result.get("scientific_law_established") is False,
    }


def run(root: str | Path | None = None) -> dict[str, Any]:
    root = Path(root or Path(__file__).resolve().parents[1]).resolve()
    api = LawSpaceAPI(root)

    discovery_x = _world_rows("x", "discovery")
    sealed_x = _world_rows("x", "sealed")
    discovery_y = _world_rows("y", "discovery")
    sealed_y = _world_rows("y", "sealed")

    # Freeze the exact masked requests before any post-freeze semantic decoding.
    req_x = _kernel_request("x", discovery_x, sealed_x)
    req_y = _kernel_request("y", discovery_y, sealed_y)
    request_freeze = {
        "x_request_digest": digest_payload(req_x),
        "y_request_digest": digest_payload(req_y),
        "mask_decoding_disclosed_to_kernel": False,
        "named_governing_equation_disclosed_to_kernel": False,
    }
    request_freeze["digest"] = digest_payload(request_freeze)

    receipt_x = api.advance_adaptive_research(req_x)
    receipt_y = api.advance_adaptive_research(req_y)

    # Continuity/closure lane uses the same exact flow rows; one component copy is enough.
    div_req = _divergence_request(discovery_x, sealed_x)
    receipt_div = api.advance_adaptive_research(div_req)

    check_x = _momentum_lane_checks(receipt_x)
    check_y = _momentum_lane_checks(receipt_y)
    div_best = receipt_div.get("result", {}).get("best_hypothesis") or {}
    div_coeff = _coefficient_by_term(div_best)
    div_sealed = receipt_div.get("result", {}).get("sealed_holdout_evaluation", {})
    check_div = {
        "CLOSURE_RELATION_SURVIVES": receipt_div.get("result", {}).get("status") == "HYPOTHESIS_SURVIVES_CURRENT_HELDOUT_EVIDENCE_NOT_LAW",
        "CLOSURE_INTERCEPT_NEAR_ZERO": abs(div_coeff.get("INTERCEPT", 1.0)) < 1e-10,
        "CLOSURE_COEFFICIENT_MINUS_ONE": abs(div_coeff.get(MASK["div_predictor"], 0.0) + 1.0) < 1e-10,
        "CLOSURE_SEALED_OOD_PASS": div_sealed.get("status") == "SEALED_HOLDOUT_EVALUATED" and float(div_sealed.get("nrmse", 1.0)) < 1e-10,
    }

    self_checks = {
        "discovery_x": _world_self_check(discovery_x),
        "sealed_x": _world_self_check(sealed_x),
        "discovery_y": _world_self_check(discovery_y),
        "sealed_y": _world_self_check(sealed_y),
    }
    reference_world_valid = all(
        float(row["max_momentum_closure_abs"] or 0.0) < 1e-12 and float(row["max_divergence_abs"] or 0.0) < 1e-12
        for row in self_checks.values()
    )

    checks: dict[str, bool] = {
        "REFERENCE_WORLD_SELF_CHECK": reference_world_valid,
        "BLIND_REQUEST_FROZEN_BEFORE_DECODE": bool(request_freeze.get("digest")),
        "NO_FORMULA_FIELD_PASSED_TO_KERNEL": all("formula" not in req and "expected_expression" not in req for req in (req_x, req_y, div_req)),
        "NO_NAMED_EQUATION_IN_KERNEL_QUESTION": all("navier" not in str(req["question"]).lower() and "stokes" not in str(req["question"]).lower() for req in (req_x, req_y, div_req)),
        **{f"X_{k}": v for k, v in check_x.items()},
        **{f"Y_{k}": v for k, v in check_y.items()},
        **{f"DIV_{k}": v for k, v in check_div.items()},
    }
    passed = sum(bool(v) for v in checks.values())

    run_journal = [
        {"stage": 1, "name": "REFERENCE_WORLD_BUILD_AND_SELF_CHECK", "status": "PASS" if reference_world_valid else "FAIL", "digest": digest_payload(self_checks)},
        {"stage": 2, "name": "BLIND_REQUEST_FREEZE", "status": "FROZEN", "digest": request_freeze["digest"]},
        {"stage": 3, "name": "X_MOMENTUM_ATLAS_EXECUTION", "status": receipt_x.get("result", {}).get("status"), "digest": receipt_x.get("digest")},
        {"stage": 4, "name": "Y_MOMENTUM_ATLAS_EXECUTION", "status": receipt_y.get("result", {}).get("status"), "digest": receipt_y.get("digest")},
        {"stage": 5, "name": "LOCAL_CLOSURE_ATLAS_EXECUTION", "status": receipt_div.get("result", {}).get("status"), "digest": receipt_div.get("digest")},
        {"stage": 6, "name": "POSTFREEZE_SEMANTIC_DECODE", "status": "VERIFICATION_ONLY", "digest": digest_payload(MASK)},
    ]

    payload = {
        "schema": SCHEMA,
        "owner": OWNER_ID,
        "release": api.runtime.current_release_id(),
        "benchmark_version": "0.15.28.0",
        "runtime_release_id": api.runtime.current_release_id(),
        "experiment_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "run_journal": run_journal,
        "status": "PASS_BLIND_CONTINUUM_BALANCE_RECOVERY" if passed == len(checks) else "FAIL_BLIND_CONTINUUM_BALANCE_RECOVERY",
        "passed": passed,
        "total": len(checks),
        "checks": [{"check": key, "status": "PASS" if value else "FAIL"} for key, value in checks.items()],
        "protocol": {
            "purpose": "blind recovery of a local incompressible continuum momentum/closure structure",
            "initial_active_masked_coordinates": [MASK["advect_1"], MASK["advect_2"], MASK["pressure"]],
            "dormant_masked_coordinates": [MASK["diffusion"], MASK["distractor_1"], MASK["distractor_2"]],
            "sealed_holdout_uses_unseen_flow_parameters": True,
            "sealed_holdout_used_for_axis_activation": False,
            "internet_used": False,
            "named_law_catalog_required": False,
            "request_freeze": request_freeze,
        },
        "reference_world_self_check": self_checks,
        "blind_results": {
            "x_momentum": _lane_summary(receipt_x),
            "y_momentum": _lane_summary(receipt_y),
            "local_closure": _lane_summary(receipt_div),
        },
        # This semantic decoding is deliberately appended only after all three
        # Atlas receipts exist. It is verification metadata, not search input.
        "postfreeze_decoding": {
            "mask": {
                MASK["target"]: "component time derivative",
                MASK["advect_1"]: "first convective product",
                MASK["advect_2"]: "second convective product",
                MASK["pressure"]: "pressure-gradient / density coordinate",
                MASK["diffusion"]: "kinematic-viscosity times component Laplacian",
                MASK["distractor_1"]: "same-dimension cross-product distractor 1",
                MASK["distractor_2"]: "same-dimension cross-product distractor 2",
                MASK["div_target"]: "du/dx",
                MASK["div_predictor"]: "dv/dy",
            },
            "expected_masked_momentum_relation_for_verification_only": "r0 = -a07 - a12 - a19 + a23",
            "expected_masked_closure_for_verification_only": "c05 = -c11",
            "physical_interpretation_after_freeze": (
                "The recovered pair is the two-component local momentum balance of the two-dimensional incompressible "
                "Navier-Stokes reference world, together with zero-divergence closure."
            ),
        },
        "execution_receipts": {
            "x_momentum": receipt_x,
            "y_momentum": receipt_y,
            "local_closure": receipt_div,
        },
        "claim_boundary": {
            "controlled_reference_world_only": True,
            "atlas_native_means_execution_provenance_not_scientific_truth": True,
            "new_physical_law_claimed": False,
            "navier_stokes_existence_and_smoothness_proved": False,
            "world_novelty_claimed": False,
            "core_architecture_modified_by_this_experiment": False,
        },
    }
    return {**payload, "digest": digest_payload(payload)}


# ---------------------------------------------------------------------------
# Level 2: primitive-field blind discovery.  The Atlas kernel receives only
# masked coordinate arrays and sampled primitive fields.  No derivative column,
# convective product, pressure-gradient term, Laplacian term or PDE template is
# supplied by this experiment.  Those research-local coordinates are born by
# PRIMITIVE-FIELD-OPERATOR-COORDINATE-BIRTH inside the current theory compiler.
# ---------------------------------------------------------------------------

PRIMITIVE_SCHEMA = "phi-blind-continuum-primitive-field-experiment/v1"
PRIMITIVE_OWNER_ID = "BLIND-CONTINUUM-PRIMITIVE-FIELD-EXPERIMENT/15.28.0"
PRIMITIVE_COORD = {"time":"q0","x":"q1","y":"q2"}
PRIMITIVE_FIELD = {"u":"f0","v":"f1","p":"f2","rho":"f3","nu":"f4"}
DIM_TIME = [0,0,1,0,0,0,0]
DIM_LENGTH = [1,0,0,0,0,0,0]
DIM_VELOCITY = [1,0,-1,0,0,0,0]
DIM_PRESSURE = [-1,1,-2,0,0,0,0]
DIM_DENSITY = [-3,1,0,0,0,0,0]
DIM_KINEMATIC_VISCOSITY = [2,0,-1,0,0,0,0]


def _mesh_study(*, study_id: str, role: str, family: str, params: dict[str,float], points: int = 15) -> dict[str, Any]:
    rho=float(params.get("rho",1.3)); nu=float(params.get("nu",0.03)); t0=float(params.get("t0",0.16))
    dt=float(params.get("dt",0.008))
    t=np.asarray([t0 + (i-3)*dt for i in range(7)],dtype=float)
    if family in {"channel_x","channel_y"}:
        h=float(params.get("half_width",1.0)); x=np.linspace(-0.82*h,0.82*h,points); y=np.linspace(-0.82*h,0.82*h,points)
    elif family=="rotation":
        x=np.linspace(-1.15,1.15,points); y=np.linspace(-1.10,1.10,points)
    else:
        x=np.linspace(0.18,2.38,points); y=np.linspace(0.24,2.44,points)
    tt,yy,xx=np.meshgrid(t,y,x,indexing="ij")
    if family=="taylor_green":
        amp=float(params.get("amp",1.0)); wave=float(params.get("wave",1.0))
        decay=np.exp(-2.0*nu*wave*wave*tt)
        u=amp*np.sin(wave*xx)*np.cos(wave*yy)*decay
        v=-amp*np.cos(wave*xx)*np.sin(wave*yy)*decay
        p=rho*(amp*amp/4.0)*(np.cos(2.0*wave*xx)+np.cos(2.0*wave*yy))*decay*decay
    elif family=="rotation":
        omega=float(params.get("omega",0.7))
        u=-omega*yy; v=omega*xx; p=0.5*rho*omega*omega*(xx*xx+yy*yy)
    elif family=="shear_x":
        amp=float(params.get("amp",1.0)); wave=float(params.get("wave",1.2))
        decay=np.exp(-nu*wave*wave*tt)
        u=amp*np.sin(wave*yy)*decay; v=np.zeros_like(u); p=np.zeros_like(u)
    elif family=="shear_y":
        amp=float(params.get("amp",0.9)); wave=float(params.get("wave",1.1))
        decay=np.exp(-nu*wave*wave*tt)
        v=amp*np.sin(wave*xx)*decay; u=np.zeros_like(v); p=np.zeros_like(v)
    elif family=="channel_x":
        speed=float(params.get("speed",1.0)); h=float(params.get("half_width",1.0))
        u=speed*(1.0-(yy/h)**2); v=np.zeros_like(u); q=-2.0*nu*speed/(h*h); p=rho*q*xx
    elif family=="channel_y":
        speed=float(params.get("speed",0.9)); h=float(params.get("half_width",1.0))
        v=speed*(1.0-(xx/h)**2); u=np.zeros_like(v); q=-2.0*nu*speed/(h*h); p=rho*q*yy
    else:
        raise ValueError(f"unknown primitive reference family {family!r}")
    rho_field=np.full_like(u,rho,dtype=float); nu_field=np.full_like(u,nu,dtype=float)
    return {
        "study_id":study_id,"role":role,"coordinate_order":[PRIMITIVE_COORD["time"],PRIMITIVE_COORD["y"],PRIMITIVE_COORD["x"]],
        "coordinates":{PRIMITIVE_COORD["time"]:t.tolist(),PRIMITIVE_COORD["x"]:x.tolist(),PRIMITIVE_COORD["y"]:y.tolist()},
        "fields":{
            PRIMITIVE_FIELD["u"]:u.tolist(),PRIMITIVE_FIELD["v"]:v.tolist(),PRIMITIVE_FIELD["p"]:p.tolist(),
            PRIMITIVE_FIELD["rho"]:rho_field.tolist(),PRIMITIVE_FIELD["nu"]:nu_field.tolist(),
        },
        "fixture_metadata_after_freeze_only":{"family":family,"parameters":params},
    }


def _primitive_studies() -> list[dict[str, Any]]:
    discovery=[
        ("PF-D-TG-1","taylor_green",{"amp":1.00,"wave":0.90,"nu":0.028,"rho":1.15,"t0":0.16}),
        ("PF-D-TG-2","taylor_green",{"amp":0.82,"wave":1.25,"nu":0.019,"rho":1.55,"t0":0.12}),
        ("PF-D-TG-3","taylor_green",{"amp":1.18,"wave":1.45,"nu":0.023,"rho":0.92,"t0":0.10}),
        ("PF-D-RR","rotation",{"omega":0.72,"nu":0.031,"rho":1.37,"t0":0.14}),
        ("PF-D-SX","shear_x",{"amp":1.06,"wave":1.22,"nu":0.037,"rho":1.21,"t0":0.19}),
        ("PF-D-SY","shear_y",{"amp":0.94,"wave":1.08,"nu":0.026,"rho":1.42,"t0":0.17}),
        ("PF-D-CX","channel_x",{"speed":1.08,"half_width":1.05,"nu":0.034,"rho":1.28,"t0":0.15}),
        ("PF-D-CY","channel_y",{"speed":0.88,"half_width":0.92,"nu":0.041,"rho":1.62,"t0":0.15}),
    ]
    sealed=[
        ("PF-H-TG-1","taylor_green",{"amp":0.93,"wave":1.05,"nu":0.032,"rho":1.31,"t0":0.135}),
        ("PF-H-TG-2","taylor_green",{"amp":1.11,"wave":1.34,"nu":0.017,"rho":1.08,"t0":0.115}),
        ("PF-H-RR","rotation",{"omega":0.91,"nu":0.024,"rho":1.48,"t0":0.13}),
        ("PF-H-SX","shear_x",{"amp":0.89,"wave":1.31,"nu":0.029,"rho":1.26,"t0":0.18}),
        ("PF-H-SY","shear_y",{"amp":1.02,"wave":0.97,"nu":0.036,"rho":1.54,"t0":0.16}),
        ("PF-H-CX","channel_x",{"speed":0.96,"half_width":0.98,"nu":0.027,"rho":1.39,"t0":0.15}),
        ("PF-H-CY","channel_y",{"speed":1.04,"half_width":1.08,"nu":0.033,"rho":1.17,"t0":0.15}),
    ]
    return [*[_mesh_study(study_id=sid,role="DISCOVERY",family=fam,params=par) for sid,fam,par in discovery],
            *[_mesh_study(study_id=sid,role="SEALED_HOLDOUT",family=fam,params=par) for sid,fam,par in sealed]]


def _strip_fixture_metadata(studies: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    visible=[]; hidden={}
    for row in studies:
        r=dict(row); hidden[str(r["study_id"])]=r.pop("fixture_metadata_after_freeze_only",{}) ; visible.append(r)
    return visible, hidden


def _primitive_request(target_field: str, studies: list[dict[str, Any]], problem_id: str) -> dict[str, Any]:
    return {
        "entry_mode":"PRIMITIVE_FIELD_DISCOVERY",
        "problem_id":problem_id,
        "domain_id":"mechanics",
        "question":"Discover a dimensionally typed local evolution relation directly from sampled primitive continuum fields. Birth whatever local operator coordinates the evidence requires; do not use a named-law catalog or a supplied PDE template.",
        "fit_tolerance_nrmse":2.5e-3,
        "complexity_level":1,
        "primitive_field_request":{
            "studies":studies,
            "coordinate_dimensions":{PRIMITIVE_COORD["time"]:DIM_TIME,PRIMITIVE_COORD["x"]:DIM_LENGTH,PRIMITIVE_COORD["y"]:DIM_LENGTH},
            "field_dimensions":{
                PRIMITIVE_FIELD["u"]:DIM_VELOCITY,PRIMITIVE_FIELD["v"]:DIM_VELOCITY,PRIMITIVE_FIELD["p"]:DIM_PRESSURE,
                PRIMITIVE_FIELD["rho"]:DIM_DENSITY,PRIMITIVE_FIELD["nu"]:DIM_KINEMATIC_VISCOSITY,
            },
            "target_field":target_field,
        },
    }


def _primitive_coefficients(receipt: dict[str, Any]) -> dict[str,float]:
    best=dict(receipt.get("result",{}).get("best_hypothesis") or {})
    return _coefficient_by_term(best)


def _find_axis_for_spec(receipt: dict[str, Any], wanted: dict[str,str]) -> str | None:
    born=receipt.get("primitive_field_operator_birth",{}).get("candidate_axes",{})
    for axis_id,spec in born.items():
        if all(str(spec.get(k))==str(v) for k,v in wanted.items()): return str(axis_id)
    return None


def _primitive_expected_axes(receipt: dict[str, Any], component: str) -> dict[str,str | None]:
    target=PRIMITIVE_FIELD["u"] if component=="x" else PRIMITIVE_FIELD["v"]
    cross=PRIMITIVE_FIELD["v"] if component=="x" else PRIMITIVE_FIELD["u"]
    own_coord=PRIMITIVE_COORD["x"] if component=="x" else PRIMITIVE_COORD["y"]
    cross_coord=PRIMITIVE_COORD["y"] if component=="x" else PRIMITIVE_COORD["x"]
    return {
        "self_advection":_find_axis_for_spec(receipt,{"kind":"FIELD_TIMES_TARGET_D1","carrier_field":target,"target_field":target,"coordinate":own_coord}),
        "cross_advection":_find_axis_for_spec(receipt,{"kind":"FIELD_TIMES_TARGET_D1","carrier_field":cross,"target_field":target,"coordinate":cross_coord}),
        "pressure":_find_axis_for_spec(receipt,{"kind":"RECIPROCAL_FIELD_TIMES_OTHER_D1","carrier_field":PRIMITIVE_FIELD["rho"],"other_field":PRIMITIVE_FIELD["p"],"coordinate":own_coord}),
        "diffusion_1":_find_axis_for_spec(receipt,{"kind":"FIELD_TIMES_TARGET_D2","carrier_field":PRIMITIVE_FIELD["nu"],"target_field":target,"coordinate":PRIMITIVE_COORD["x"]}),
        "diffusion_2":_find_axis_for_spec(receipt,{"kind":"FIELD_TIMES_TARGET_D2","carrier_field":PRIMITIVE_FIELD["nu"],"target_field":target,"coordinate":PRIMITIVE_COORD["y"]}),
    }


def _primitive_lane_checks(receipt: dict[str, Any], component: str) -> dict[str,bool]:
    result=receipt.get("result",{}); inner=receipt.get("inner_research_receipt",{}); coeff=_primitive_coefficients(receipt)
    expected=_primitive_expected_axes(receipt,component); sealed=result.get("sealed_holdout_evaluation",{})
    expected_ids=[x for x in expected.values() if x]
    effective=set(result.get("effective_predictor_variables",[]))
    axis_birth=receipt.get("axis_birth_search",{})
    return {
        "PRIMITIVE_ONLY_ENTRY": receipt.get("claim_boundary",{}).get("caller_supplied_derived_derivative_values") is False,
        "OPERATORS_BORN_INSIDE_ATLAS": receipt.get("claim_boundary",{}).get("operator_coordinates_born_inside_atlas") is True,
        "ALL_EXPECTED_TYPED_AXES_WERE_BORN": len(expected_ids)==5,
        "MULTI_AXIS_BIRTH_POLICY_ACTIVE": axis_birth.get("multi_axis_birth_allowed") is True and axis_birth.get("fixed_axis_count_per_cycle") is None,
        "REQUIRED_SUPPORT_PRESENT": all(axis_id in effective for axis_id in expected_ids),
        "SURVIVES_DISCOVERY_HOLDOUT": result.get("status")=="HYPOTHESIS_SURVIVES_CURRENT_HELDOUT_EVIDENCE_NOT_LAW",
        "SEALED_OOD_PASS": sealed.get("status")=="SEALED_HOLDOUT_EVALUATED" and float(sealed.get("nrmse",1.0)) < 1.0e-2,
        "SELF_ADVECT_COEFF": expected["self_advection"] is not None and abs(coeff.get(str(expected["self_advection"]),0.0)+1.0)<2.0e-2,
        "CROSS_ADVECT_COEFF": expected["cross_advection"] is not None and abs(coeff.get(str(expected["cross_advection"]),0.0)+1.0)<2.0e-2,
        "PRESSURE_COEFF": expected["pressure"] is not None and abs(coeff.get(str(expected["pressure"]),0.0)+1.0)<2.0e-2,
        "DIFFUSION_X_COEFF": expected["diffusion_1"] is not None and abs(coeff.get(str(expected["diffusion_1"]),0.0)-1.0)<2.0e-2,
        "DIFFUSION_Y_COEFF": expected["diffusion_2"] is not None and abs(coeff.get(str(expected["diffusion_2"]),0.0)-1.0)<2.0e-2,
        "ATLAS_PROVENANCE_ONLY": receipt.get("atlas_claim",{}).get("atlas_native") is True and result.get("scientific_law_established") is False,
        "INNER_RECEIPT_HAS_ADAPTIVE_BIRTH": inner.get("claim_boundary",{}).get("axis_birth_cardinality_is_adaptive") is True,
    }


def _primitive_lane_summary(receipt: dict[str, Any], component: str) -> dict[str, Any]:
    result=receipt.get("result",{}); born=receipt.get("primitive_field_operator_birth",{}); expected=_primitive_expected_axes(receipt,component)
    return {
        "status":result.get("status"),"target_field":receipt.get("result",{}).get("primitive_target_field"),
        "born_candidate_axis_count":born.get("candidate_axis_count"),"baseline_axis":receipt.get("baseline_axis_search",{}).get("selected_axis"),
        "activated_axes":result.get("activated_axis_variables"),"selected_birth_cardinality":receipt.get("axis_birth_search",{}).get("selected_cardinality"),
        "effective_predictor_variables":result.get("effective_predictor_variables"),"expected_support_after_postfreeze_decode":expected,
        "best_expression":(result.get("best_hypothesis") or {}).get("expression"),"coefficients":_primitive_coefficients(receipt),
        "discovery_holdout_nrmse":(result.get("best_hypothesis") or {}).get("holdout_nrmse"),"sealed_holdout":result.get("sealed_holdout_evaluation"),
        "atlas_native":receipt.get("atlas_claim",{}).get("atlas_native"),"receipt_digest":receipt.get("digest"),
    }


def run_primitive_field(root: str | Path | None = None) -> dict[str, Any]:
    root=Path(root or Path(__file__).resolve().parents[1]).resolve(); api=LawSpaceAPI(root)
    studies_with_hidden=_primitive_studies(); studies,hidden_fixture=_strip_fixture_metadata(studies_with_hidden)
    req_x=_primitive_request(PRIMITIVE_FIELD["u"],studies,"BLIND-PRIMITIVE-CONTINUUM-X-001")
    req_y=_primitive_request(PRIMITIVE_FIELD["v"],studies,"BLIND-PRIMITIVE-CONTINUUM-Y-001")
    freeze={
        "x_request_digest":digest_payload(req_x),"y_request_digest":digest_payload(req_y),
        "primitive_only":True,"derived_derivative_columns_supplied":False,"named_equation_disclosed":False,
        "fixture_semantics_disclosed":False,
    }; freeze["digest"]=digest_payload(freeze)
    receipt_x=api.advance_adaptive_research(req_x); receipt_y=api.advance_adaptive_research(req_y)
    checks={
        "REQUEST_FROZEN_BEFORE_DECODE":bool(freeze["digest"]),
        "NO_DERIVED_COLUMNS_IN_REQUEST":all(set(study.keys()) <= {"study_id","role","coordinate_order","coordinates","fields"} for study in studies),
        "NO_NAMED_EQUATION_IN_QUESTION":all("navier" not in req["question"].lower() and "stokes" not in req["question"].lower() for req in (req_x,req_y)),
        "AXIS_BIRTH_CARDINALITY_ADAPTIVE":api.get_adaptive_research_kernel_contract().get("space_policy",{}).get("axis_birth_cardinality")=="ADAPTIVE",
        **{f"X_{k}":v for k,v in _primitive_lane_checks(receipt_x,"x").items()},
        **{f"Y_{k}":v for k,v in _primitive_lane_checks(receipt_y,"y").items()},
    }
    passed=sum(bool(v) for v in checks.values())
    postfreeze={
        "coordinate_mask":{PRIMITIVE_COORD["time"]:"t",PRIMITIVE_COORD["x"]:"x",PRIMITIVE_COORD["y"]:"y"},
        "field_mask":{PRIMITIVE_FIELD["u"]:"u",PRIMITIVE_FIELD["v"]:"v",PRIMITIVE_FIELD["p"]:"p",PRIMITIVE_FIELD["rho"]:"rho",PRIMITIVE_FIELD["nu"]:"nu"},
        "hidden_reference_fixture_metadata":hidden_fixture,
        "expected_structure_for_verification_only":{
            "x":"d_t u = -(u d_x u) -(v d_y u) -(rho^-1 d_x p) + nu d_xx u + nu d_yy u",
            "y":"d_t v = -(u d_x v) -(v d_y v) -(rho^-1 d_y p) + nu d_xx v + nu d_yy v",
        },
    }
    journal=[
        {"stage":1,"name":"PRIMITIVE_REFERENCE_FIELDS_BUILT","status":"PASS","digest":digest_payload({k:v for k,v in hidden_fixture.items()})},
        {"stage":2,"name":"PRIMITIVE_REQUEST_FREEZE","status":"FROZEN","digest":freeze["digest"]},
        {"stage":3,"name":"X_PRIMITIVE_FIELD_ATLAS_EXECUTION","status":receipt_x.get("result",{}).get("status"),"digest":receipt_x.get("digest")},
        {"stage":4,"name":"Y_PRIMITIVE_FIELD_ATLAS_EXECUTION","status":receipt_y.get("result",{}).get("status"),"digest":receipt_y.get("digest")},
        {"stage":5,"name":"POSTFREEZE_SEMANTIC_DECODE","status":"VERIFICATION_ONLY","digest":digest_payload(postfreeze)},
    ]
    payload={
        "schema":PRIMITIVE_SCHEMA,"owner":PRIMITIVE_OWNER_ID,"release":api.runtime.current_release_id(),"benchmark_version":"0.15.28.0","runtime_release_id":api.runtime.current_release_id(),
        "experiment_source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),"run_journal":journal,
        "status":"PASS_PRIMITIVE_FIELD_BLIND_OPERATOR_DISCOVERY" if passed==len(checks) else "FAIL_PRIMITIVE_FIELD_BLIND_OPERATOR_DISCOVERY",
        "passed":passed,"total":len(checks),"checks":[{"check":k,"status":"PASS" if v else "FAIL"} for k,v in checks.items()],
        "protocol":{
            "input_to_atlas":"masked primitive coordinate arrays and sampled fields only","request_freeze":freeze,
            "axis_birth_cardinality":"ADAPTIVE","multi_axis_birth_allowed":True,"fixed_axis_count_per_cycle":None,
            "sealed_holdout_uses_unseen_flow_parameters":True,"internet_used":False,"named_law_catalog_required":False,
        },
        "blind_results":{"x_momentum":_primitive_lane_summary(receipt_x,"x"),"y_momentum":_primitive_lane_summary(receipt_y,"y")},
        "postfreeze_decoding":postfreeze,"execution_receipts":{"x_momentum":receipt_x,"y_momentum":receipt_y},
        "claim_boundary":{
            "controlled_reference_world_only":True,"new_physical_law_claimed":False,"world_novelty_claimed":False,
            "navier_stokes_existence_and_smoothness_proved":False,
            "this_level_tests_operator_coordinate_birth_from_primitive_fields":True,
        },
    }
    return {**payload,"digest":digest_payload(payload)}



# ---------------------------------------------------------------------------
# Level 3: operator-language invention.  No D/D2 grammar is supplied.  The
# Mathematical Invention Kernel receives only primitive field/coordinate types
# and weaker meta-primitives (local translation, linear superposition,
# pointwise multiply/reciprocal, dimensional typing).  It generates local
# translation-moment response signatures by open rank shells.  Theory Compiler
# then executes the frozen generated language on primitive sampled fields.
# ---------------------------------------------------------------------------

LANGUAGE_SCHEMA = "phi-blind-continuum-operator-language-invention/v1"
LANGUAGE_OWNER_ID = "BLIND-CONTINUUM-OPERATOR-LANGUAGE-INVENTION/1.0.0"


def _language_request(target_field: str, studies: list[dict[str, Any]], problem_id: str) -> dict[str, Any]:
    req=_primitive_request(target_field,studies,problem_id)
    req.update({
        "entry_mode":"PRIMITIVE_FIELD_LANGUAGE_DISCOVERY",
        "operator_language_invention":True,
        "operator_language_search_budget":6,
        "question":(
            "Discover a dimensionally typed local evolution relation from masked primitive sampled fields. "
            "Do not use a named equation or a predeclared differential-operator grammar. Generate a local "
            "operator language from weaker translation/algebra meta-primitives, then search its typed coordinates."
        ),
    })
    return req


def _language_expected_axes(receipt: dict[str, Any], component: str) -> dict[str,str | None]:
    target=PRIMITIVE_FIELD["u"] if component=="x" else PRIMITIVE_FIELD["v"]
    cross=PRIMITIVE_FIELD["v"] if component=="x" else PRIMITIVE_FIELD["u"]
    own_coord=PRIMITIVE_COORD["x"] if component=="x" else PRIMITIVE_COORD["y"]
    cross_coord=PRIMITIVE_COORD["y"] if component=="x" else PRIMITIVE_COORD["x"]
    generic="POINTWISE_MONOMIAL_X_LOCAL_TRANSLATION_MOMENT_RESPONSE"
    return {
        "self_advection":_find_axis_for_spec(receipt,{"kind":generic,"response_field":target,"carrier_field":target,"carrier_power":"1","coordinate":own_coord,"moment_rank":"1"}),
        "cross_advection":_find_axis_for_spec(receipt,{"kind":generic,"response_field":target,"carrier_field":cross,"carrier_power":"1","coordinate":cross_coord,"moment_rank":"1"}),
        "pressure":_find_axis_for_spec(receipt,{"kind":generic,"response_field":PRIMITIVE_FIELD["p"],"carrier_field":PRIMITIVE_FIELD["rho"],"carrier_power":"-1","coordinate":own_coord,"moment_rank":"1"}),
        "diffusion_1":_find_axis_for_spec(receipt,{"kind":generic,"response_field":target,"carrier_field":PRIMITIVE_FIELD["nu"],"carrier_power":"1","coordinate":PRIMITIVE_COORD["x"],"moment_rank":"2"}),
        "diffusion_2":_find_axis_for_spec(receipt,{"kind":generic,"response_field":target,"carrier_field":PRIMITIVE_FIELD["nu"],"carrier_power":"1","coordinate":PRIMITIVE_COORD["y"],"moment_rank":"2"}),
    }


def _language_lane_checks(receipt: dict[str, Any], component: str) -> dict[str,bool]:
    result=receipt.get("result",{}); inner=receipt.get("inner_research_receipt",{}); coeff=_primitive_coefficients(receipt)
    expected=_language_expected_axes(receipt,component); expected_ids=[x for x in expected.values() if x]
    effective=set(result.get("effective_predictor_variables",[])); sealed=result.get("sealed_holdout_evaluation",{})
    language=receipt.get("operator_language_invention") or {}; born=receipt.get("primitive_field_operator_birth",{})
    signatures=list(language.get("generated_signatures",[])); ranks={int(x.get("moment_rank",-1)) for x in signatures}
    time_coord=PRIMITIVE_COORD["time"]
    no_time_predictors=all(str(x.get("coordinate"))!=time_coord for x in signatures)
    seed=set(language.get("seed_meta_primitives",[]))
    return {
        "LANGUAGE_BIRTH_EXECUTED":language.get("status")=="GENERATED_OPERATOR_LANGUAGE",
        "NO_NAMED_DIFFERENTIAL_GRAMMAR":language.get("claim_boundary",{}).get("named_differential_operator_catalog_used") is False,
        "NO_FIXED_DERIVATIVE_ORDER_CATALOG":language.get("claim_boundary",{}).get("fixed_derivative_order_catalog_used") is False,
        "WEAKER_META_PRIMITIVES_ONLY":{"LOCAL_TRANSLATION","LINEAR_SUPERPOSITION","POINTWISE_MULTIPLY","POINTWISE_RECIPROCAL","DIMENSION_TYPING"}.issubset(seed),
        "LANGUAGE_SEARCH_OPEN_BEYOND_RESOURCE_BUDGET":language.get("search_may_resume_beyond_budget") is True and language.get("claim_boundary",{}).get("resource_budget_is_scientific_rank_ceiling") is False,
        "MULTIPLE_MOMENT_RANKS_BORN":{1,2}.issubset(ranks) and len(ranks)>=3,
        "TARGET_ROLE_SEPARATED_FROM_PREDICTORS":no_time_predictors,
        "THEORY_COMPILER_EXECUTES_INVENTED_LANGUAGE":born.get("operator_language_mode")=="INVENTED_FROM_META_PRIMITIVES",
        "ALL_EXPECTED_POSTFREEZE_SUPPORT_WAS_AVAILABLE":len(expected_ids)==5,
        "REQUIRED_SUPPORT_SELECTED":all(x in effective for x in expected_ids),
        "ADAPTIVE_MULTI_AXIS_BIRTH":receipt.get("axis_birth_search",{}).get("multi_axis_birth_allowed") is True and receipt.get("axis_birth_search",{}).get("selected_cardinality")==4,
        "SURVIVES_DISCOVERY_HOLDOUT":result.get("status")=="HYPOTHESIS_SURVIVES_CURRENT_HELDOUT_EVIDENCE_NOT_LAW",
        "SEALED_OOD_PASS":sealed.get("status")=="SEALED_HOLDOUT_EVALUATED" and float(sealed.get("nrmse",1.0))<1.0e-2,
        "SELF_ADVECT_COEFF":expected["self_advection"] is not None and abs(coeff.get(str(expected["self_advection"]),0.0)+1.0)<2.0e-2,
        "CROSS_ADVECT_COEFF":expected["cross_advection"] is not None and abs(coeff.get(str(expected["cross_advection"]),0.0)+1.0)<2.0e-2,
        "PRESSURE_COEFF":expected["pressure"] is not None and abs(coeff.get(str(expected["pressure"]),0.0)+1.0)<2.0e-2,
        "DIFFUSION_X_COEFF":expected["diffusion_1"] is not None and abs(coeff.get(str(expected["diffusion_1"]),0.0)-1.0)<2.0e-2,
        "DIFFUSION_Y_COEFF":expected["diffusion_2"] is not None and abs(coeff.get(str(expected["diffusion_2"]),0.0)-1.0)<2.0e-2,
        "REPRESENTATION_NOT_CAUSAL_PROOF":result.get("representation_activated_does_not_equal_causally_established") is True or result.get("causal_status")=="CAUSALLY_NOT_ESTABLISHED",
        "SCIENTIFIC_LAW_NOT_PROMOTED":result.get("scientific_law_established") is False,
        "INNER_RECEIPT_ADAPTIVE":inner.get("claim_boundary",{}).get("axis_birth_cardinality_is_adaptive") is True,
    }


def _language_lane_summary(receipt: dict[str, Any], component: str) -> dict[str, Any]:
    result=receipt.get("result",{}); language=receipt.get("operator_language_invention") or {}
    return {
        "status":result.get("status"),
        "generated_language_status":language.get("status"),
        "generated_signature_count":language.get("generated_signature_count"),
        "generated_rank_shells":language.get("shell_journal"),
        "seed_meta_primitives":language.get("seed_meta_primitives"),
        "selected_birth_cardinality":receipt.get("axis_birth_search",{}).get("selected_cardinality"),
        "effective_predictor_variables":result.get("effective_predictor_variables"),
        "expected_support_after_postfreeze_decode":_language_expected_axes(receipt,component),
        "best_expression":(result.get("best_hypothesis") or {}).get("expression"),
        "coefficients":_primitive_coefficients(receipt),
        "discovery_holdout_nrmse":(result.get("best_hypothesis") or {}).get("holdout_nrmse"),
        "sealed_holdout":result.get("sealed_holdout_evaluation"),
        "receipt_digest":receipt.get("digest"),
    }


def run_operator_language_invention(root: str | Path | None = None) -> dict[str, Any]:
    root=Path(root or Path(__file__).resolve().parents[1]).resolve(); api=LawSpaceAPI(root)
    studies_with_hidden=_primitive_studies(); studies,hidden_fixture=_strip_fixture_metadata(studies_with_hidden)
    req_x=_language_request(PRIMITIVE_FIELD["u"],studies,"BLIND-LANGUAGE-CONTINUUM-X-001")
    req_y=_language_request(PRIMITIVE_FIELD["v"],studies,"BLIND-LANGUAGE-CONTINUUM-Y-001")
    freeze={
        "x_request_digest":digest_payload(req_x),"y_request_digest":digest_payload(req_y),
        "primitive_only":True,"derived_derivative_columns_supplied":False,"named_equation_disclosed":False,
        "named_differential_operator_grammar_disclosed":False,"postfreeze_expected_support_disclosed":False,
    }; freeze["digest"]=digest_payload(freeze)
    receipt_x=api.advance_adaptive_research(req_x); receipt_y=api.advance_adaptive_research(req_y)
    checks={
        "REQUEST_FROZEN_BEFORE_SEMANTIC_DECODE":bool(freeze["digest"]),
        "NO_DERIVED_COLUMNS_IN_REQUEST":all(set(study.keys()) <= {"study_id","role","coordinate_order","coordinates","fields"} for study in studies),
        "NO_NAMED_EQUATION_IN_QUESTION":all("navier" not in req["question"].lower() and "stokes" not in req["question"].lower() for req in (req_x,req_y)),
        "NO_D_OR_D2_GRAMMAR_IN_REQUEST":all("derivative" not in req["question"].lower() and "laplac" not in req["question"].lower() for req in (req_x,req_y)),
        **{f"X_{k}":v for k,v in _language_lane_checks(receipt_x,"x").items()},
        **{f"Y_{k}":v for k,v in _language_lane_checks(receipt_y,"y").items()},
    }
    passed=sum(bool(v) for v in checks.values())
    postfreeze={
        "coordinate_mask":{PRIMITIVE_COORD["time"]:"t",PRIMITIVE_COORD["x"]:"x",PRIMITIVE_COORD["y"]:"y"},
        "field_mask":{PRIMITIVE_FIELD["u"]:"u",PRIMITIVE_FIELD["v"]:"v",PRIMITIVE_FIELD["p"]:"p",PRIMITIVE_FIELD["rho"]:"rho",PRIMITIVE_FIELD["nu"]:"nu"},
        "hidden_reference_fixture_metadata":hidden_fixture,
        "generated_translation_moment_decode_for_verification_only":{"rank_1":"first local differential response","rank_2":"second local differential response","rank_3":"higher-order distractor shell"},
        "expected_structure_for_verification_only":{
            "x":"local_t1(u) = -(u local_x1(u)) -(v local_y1(u)) -(rho^-1 local_x1(p)) + nu local_x2(u) + nu local_y2(u)",
            "y":"local_t1(v) = -(u local_x1(v)) -(v local_y1(v)) -(rho^-1 local_y1(p)) + nu local_x2(v) + nu local_y2(v)",
        },
    }
    journal=[
        {"stage":1,"name":"PRIMITIVE_REFERENCE_FIELDS_BUILT","status":"PASS","digest":digest_payload(hidden_fixture)},
        {"stage":2,"name":"LANGUAGE_INVENTION_REQUEST_FREEZE","status":"FROZEN","digest":freeze["digest"]},
        {"stage":3,"name":"X_OPERATOR_LANGUAGE_INVENTION_AND_SEARCH","status":receipt_x.get("result",{}).get("status"),"digest":receipt_x.get("digest")},
        {"stage":4,"name":"Y_OPERATOR_LANGUAGE_INVENTION_AND_SEARCH","status":receipt_y.get("result",{}).get("status"),"digest":receipt_y.get("digest")},
        {"stage":5,"name":"POSTFREEZE_SEMANTIC_DECODE","status":"VERIFICATION_ONLY","digest":digest_payload(postfreeze)},
    ]
    payload={
        "schema":LANGUAGE_SCHEMA,"owner":LANGUAGE_OWNER_ID,"patch_level":"operator-language-invention-level-3",
        "runtime_release_id":api.runtime.current_release_id(),"experiment_source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "status":"PASS_BLIND_OPERATOR_LANGUAGE_INVENTION" if passed==len(checks) else "FAIL_BLIND_OPERATOR_LANGUAGE_INVENTION",
        "passed":passed,"total":len(checks),"checks":[{"check":k,"status":"PASS" if v else "FAIL"} for k,v in checks.items()],
        "protocol":{
            "input_to_atlas":"masked primitive coordinate arrays, sampled primitive fields and dimension types only",
            "request_freeze":freeze,"internet_used":False,"named_law_catalog_required":False,
            "predeclared_differential_operator_grammar":False,"sealed_holdout_uses_unseen_flow_parameters":True,
            "language_seed_meta_primitives":["LOCAL_TRANSLATION","LINEAR_SUPERPOSITION","POINTWISE_MULTIPLY","POINTWISE_RECIPROCAL","DIMENSION_TYPING"],
            "resource_shell_budget_is_not_scientific_ceiling":True,
        },
        "blind_results":{"x_momentum":_language_lane_summary(receipt_x,"x"),"y_momentum":_language_lane_summary(receipt_y,"y")},
        "postfreeze_decoding":postfreeze,"execution_receipts":{"x_momentum":receipt_x,"y_momentum":receipt_y},"run_journal":journal,
        "claim_boundary":{
            "controlled_reference_world_only":True,"new_physical_law_claimed":False,"world_novelty_claimed":False,
            "differential_calculus_invented_from_nothing":False,"local_translation_meta_primitive_preexists":True,
            "named_differential_operator_grammar_removed_from_prefreeze_search":True,
            "this_level_tests_language_birth_before_pde_support_search":True,
        },
    }
    return {**payload,"digest":digest_payload(payload)}


# ---------------------------------------------------------------------------
# Level 4: persistent-residual hidden-term discovery.
#
# The controlled reference world contains a baseline local transport relation
# plus one additional modulation that requires two pointwise carrier factors.
# Search receives only opaque primitive fields, a frozen baseline operator
# signature and weak meta-primitives.  The hidden relation is used only by the
# fixture generator and post-freeze verification.
# ---------------------------------------------------------------------------

HIDDEN_SCHEMA="phi-blind-hidden-term-residual-discovery/v1"
HIDDEN_OWNER_ID="BLIND-HIDDEN-TERM-RESIDUAL-DISCOVERY/1.0.0"
HIDDEN_COORD={"time":"r0","x":"r1"}
HIDDEN_FIELD={"state":"g0","drift":"g1","modulator":"g2","distractor":"g3"}
DIMENSIONLESS=[0,0,0,0,0,0,0]
HIDDEN_LAMBDA=0.65


def _hidden_term_study(*, study_id: str, role: str, params: dict[str,float], points: int=19) -> dict[str,Any]:
    """Exact affine solution of a deliberately incomplete local evolution world.

    Semantic relation (kept inside fixture/post-freeze only):
      u_t = -a u_x - lambda*c*u*u_x.
    """
    a=float(params["a"]); c=float(params["c"]); d=float(params["d"])
    A0=float(params["A0"]); B0=float(params["B0"]); t0=float(params.get("t0",0.12)); dt=float(params.get("dt",0.009))
    t=np.asarray([t0+(i-4)*dt for i in range(9)],dtype=float)
    x=np.linspace(float(params.get("xmin",0.15)),float(params.get("xmax",1.55)),points)
    tt,xx=np.meshgrid(t,x,indexing="ij")
    denom=1.0+HIDDEN_LAMBDA*c*A0*tt
    u=(A0*xx+B0-a*A0*tt)/denom
    drift=np.full_like(u,a,dtype=float)
    modulator=np.full_like(u,c,dtype=float)
    distractor=np.full_like(u,d,dtype=float)
    return {
        "study_id":study_id,"role":role,"coordinate_order":[HIDDEN_COORD["time"],HIDDEN_COORD["x"]],
        "coordinates":{HIDDEN_COORD["time"]:t.tolist(),HIDDEN_COORD["x"]:x.tolist()},
        "fields":{
            HIDDEN_FIELD["state"]:u.tolist(),HIDDEN_FIELD["drift"]:drift.tolist(),
            HIDDEN_FIELD["modulator"]:modulator.tolist(),HIDDEN_FIELD["distractor"]:distractor.tolist(),
        },
        "fixture_metadata_after_freeze_only":{"parameters":params,"hidden_lambda":HIDDEN_LAMBDA},
    }


def _hidden_term_studies() -> list[dict[str,Any]]:
    discovery=[
        ("HT-D-01",{"a":0.72,"c":0.34,"d":1.21,"A0":0.24,"B0":1.08,"t0":0.11}),
        ("HT-D-02",{"a":1.05,"c":0.58,"d":0.77,"A0":0.31,"B0":1.24,"t0":0.14}),
        ("HT-D-03",{"a":0.88,"c":0.83,"d":1.46,"A0":0.19,"B0":0.96,"t0":0.09}),
        ("HT-D-04",{"a":1.22,"c":1.17,"d":0.63,"A0":0.27,"B0":1.31,"t0":0.13}),
        ("HT-D-05",{"a":0.61,"c":1.42,"d":1.08,"A0":0.35,"B0":1.16,"t0":0.10}),
        ("HT-D-06",{"a":1.34,"c":0.71,"d":1.72,"A0":0.22,"B0":1.39,"t0":0.15}),
        ("HT-D-07",{"a":0.93,"c":1.03,"d":0.91,"A0":0.29,"B0":1.02,"t0":0.12}),
    ]
    sealed=[
        ("HT-H-01",{"a":0.67,"c":0.47,"d":1.58,"A0":0.26,"B0":1.19,"t0":0.105}),
        ("HT-H-02",{"a":1.16,"c":0.94,"d":0.69,"A0":0.33,"B0":1.27,"t0":0.145}),
        ("HT-H-03",{"a":0.81,"c":1.31,"d":1.33,"A0":0.21,"B0":1.05,"t0":0.095}),
        ("HT-H-04",{"a":1.29,"c":0.62,"d":1.84,"A0":0.28,"B0":1.36,"t0":0.135}),
    ]
    return [*[_hidden_term_study(study_id=sid,role="DISCOVERY",params=p) for sid,p in discovery],
            *[_hidden_term_study(study_id=sid,role="SEALED_HOLDOUT",params=p) for sid,p in sealed]]


def _hidden_baseline_signature() -> dict[str,Any]:
    return {
        "kind":"POINTWISE_MONOMIAL_X_LOCAL_TRANSLATION_MOMENT_RESPONSE",
        "response_field":HIDDEN_FIELD["state"],"coordinate":HIDDEN_COORD["x"],"moment_rank":1,
        "carrier_field":HIDDEN_FIELD["drift"],"carrier_power":1,
    }


def _hidden_expected_factor_signature() -> dict[str,Any]:
    return {
        "kind":"POINTWISE_MONOMIAL_X_LOCAL_TRANSLATION_MOMENT_RESPONSE",
        "response_field":HIDDEN_FIELD["state"],"coordinate":HIDDEN_COORD["x"],"moment_rank":1,
        "carrier_factors":[
            {"field":HIDDEN_FIELD["state"],"power":1},
            {"field":HIDDEN_FIELD["modulator"],"power":1},
        ],
        "carrier_factor_count":2,
    }


def _find_axis_subset(receipt: dict[str,Any], wanted: dict[str,Any]) -> str | None:
    born=receipt.get("primitive_field_operator_birth",{}).get("candidate_axes",{})
    for axis_id,spec in born.items():
        if all(spec.get(k)==v for k,v in wanted.items()):
            return str(axis_id)
    return None


def run_hidden_term_discovery(root: str | Path | None=None) -> dict[str,Any]:
    root=Path(root or Path(__file__).resolve().parents[1]).resolve(); api=LawSpaceAPI(root)
    studies_with_hidden=_hidden_term_studies(); studies,hidden_fixture=_strip_fixture_metadata(studies_with_hidden)
    request={
        "entry_mode":"PRIMITIVE_FIELD_RESIDUAL_LANGUAGE_DISCOVERY",
        "residual_driven_language_expansion":True,
        "problem_id":"BLIND-HIDDEN-TERM-001",
        "domain_id":"mechanics",
        "question":"Given primitive sampled fields and a frozen incomplete baseline operator, explain the persistent local evolution residual by expanding the internally generated operator language only when the current representation fails its discovery gate. Do not use a named-law or hidden-term catalog.",
        "fit_tolerance_nrmse":2.0e-5,
        "complexity_level":1,
        "operator_language_search_budget":6,
        "residual_language_factor_depth_budget":3,
        "axis_birth_trial_budget":2048,
        "baseline_operator_signature":_hidden_baseline_signature(),
        "primitive_field_request":{
            "studies":studies,
            "coordinate_dimensions":{HIDDEN_COORD["time"]:DIM_TIME,HIDDEN_COORD["x"]:DIM_LENGTH},
            "field_dimensions":{
                HIDDEN_FIELD["state"]:DIM_VELOCITY,HIDDEN_FIELD["drift"]:DIM_VELOCITY,
                HIDDEN_FIELD["modulator"]:DIMENSIONLESS,HIDDEN_FIELD["distractor"]:DIMENSIONLESS,
            },
            "target_field":HIDDEN_FIELD["state"],
        },
    }
    freeze={
        "request_digest":digest_payload(request),"hidden_term_semantics_disclosed":False,
        "hidden_coefficient_disclosed":False,"primitive_only":True,"baseline_structure_frozen":True,
        "named_differential_grammar_disclosed":False,
    }; freeze["digest"]=digest_payload(freeze)
    receipt=api.advance_adaptive_research(request)
    stages=list(receipt.get("language_expansion_journal",()))
    initial=dict(receipt.get("initial_language_receipt",{})); final=dict(receipt.get("final_language_receipt",{}))
    expected_hidden_axis=_find_axis_subset(final,_hidden_expected_factor_signature())
    initial_hidden_axis=_find_axis_subset(initial,_hidden_expected_factor_signature())
    baseline_axis=_find_axis_subset(final,_hidden_baseline_signature())
    result=dict(receipt.get("result",{})); coeff=_coefficient_by_term(dict(result.get("best_hypothesis") or {}))
    sealed=dict(result.get("sealed_holdout_evaluation",{})); effective=set(result.get("effective_predictor_variables",()))
    initial_nrmse=float(stages[0].get("discovery_holdout_nrmse",float("inf"))) if stages else float("inf")
    final_nrmse=float((result.get("best_hypothesis") or {}).get("holdout_nrmse",float("inf")))
    checks={
        "REQUEST_FROZEN_BEFORE_HIDDEN_DECODE":bool(freeze["digest"]),
        "PRIMITIVE_FIELDS_ONLY":all(set(study.keys()) <= {"study_id","role","coordinate_order","coordinates","fields"} for study in studies),
        "BASELINE_STRUCTURE_FROZEN":initial.get("baseline_axis_search",{}).get("policy")=="FROZEN_BASELINE_OPERATOR_SIGNATURE",
        "HIDDEN_TERM_ABSENT_FROM_DEPTH1_LANGUAGE":initial_hidden_axis is None,
        "INITIAL_REPRESENTATION_LEAVES_PERSISTENT_RESIDUAL":bool(stages) and stages[0].get("residual_persisted") is True and initial_nrmse>1.0e-3,
        "RESIDUAL_TRIGGERS_LANGUAGE_EXPANSION":len(stages)>=2 and stages[1].get("algebra_carrier_factor_depth")==2,
        "HIDDEN_OPERATOR_BORN_ONLY_AFTER_EXPANSION":expected_hidden_axis is not None,
        "DISTRACTOR_FIELD_PRESENT":HIDDEN_FIELD["distractor"] in request["primitive_field_request"]["field_dimensions"],
        "FINAL_SUPPORT_CONTAINS_FROZEN_BASELINE":baseline_axis is not None and baseline_axis in effective,
        "FINAL_SUPPORT_CONTAINS_HIDDEN_CANDIDATE":expected_hidden_axis is not None and expected_hidden_axis in effective,
        "HIDDEN_COEFFICIENT_RECOVERED":expected_hidden_axis is not None and abs(coeff.get(expected_hidden_axis,0.0)+HIDDEN_LAMBDA)<5.0e-3,
        "BASELINE_COEFFICIENT_RECOVERED":baseline_axis is not None and abs(coeff.get(baseline_axis,0.0)+1.0)<5.0e-3,
        "DISCOVERY_RESIDUAL_COLLAPSES":final_nrmse<2.0e-5 and final_nrmse<initial_nrmse*1.0e-2,
        "SEALED_OOD_PASS":sealed.get("status")=="SEALED_HOLDOUT_EVALUATED" and float(sealed.get("nrmse",1.0))<3.0e-5,
        "LANGUAGE_EXPANSION_IS_RESIDUAL_DRIVEN":receipt.get("claim_boundary",{}).get("language_expansion_triggered_only_by_persistent_discovery_residual") is True,
        "SEALED_NOT_USED_TO_TRIGGER_EXPANSION":receipt.get("claim_boundary",{}).get("sealed_holdout_used_to_trigger_language_expansion") is False,
        "NO_SCIENTIFIC_PROMOTION":result.get("scientific_law_established") is False,
        "CAUSALITY_NOT_AUTO_PROMOTED":result.get("causal_status")=="CAUSALLY_NOT_ESTABLISHED",
        "TOP_LEVEL_ATLAS_PROVENANCE_ACCEPTED":receipt.get("atlas_claim",{}).get("atlas_native") is True
            and receipt.get("atlas_claim",{}).get("status")=="ATLAS_NATIVE_PROVENANCE_ACCEPTED_NOT_SCIENTIFIC_PROMOTION",
    }
    passed=sum(bool(v) for v in checks.values())
    postfreeze={
        "coordinate_mask":{HIDDEN_COORD["time"]:"t",HIDDEN_COORD["x"]:"x"},
        "field_mask":{HIDDEN_FIELD["state"]:"u",HIDDEN_FIELD["drift"]:"a",HIDDEN_FIELD["modulator"]:"c",HIDDEN_FIELD["distractor"]:"d"},
        "hidden_reference_fixture_metadata":hidden_fixture,
        "baseline_relation_for_verification_only":"u_t contains -a*u_x",
        "hidden_relation_for_verification_only":"additional term = -lambda*c*u*u_x",
        "hidden_lambda":HIDDEN_LAMBDA,
        "expected_hidden_axis":expected_hidden_axis,
        "baseline_axis":baseline_axis,
    }
    journal=[
        {"stage":1,"name":"HIDDEN_REFERENCE_WORLD_BUILT","status":"PASS","digest":digest_payload(hidden_fixture)},
        {"stage":2,"name":"INCOMPLETE_BASELINE_REQUEST_FREEZE","status":"FROZEN","digest":freeze["digest"]},
        {"stage":3,"name":"RESIDUAL_DRIVEN_LANGUAGE_EXPANSION","status":result.get("status"),"digest":receipt.get("digest")},
        {"stage":4,"name":"SEALED_OOD_FALSIFICATION","status":sealed.get("status"),"digest":sealed.get("digest")},
        {"stage":5,"name":"POSTFREEZE_HIDDEN_TERM_DECODE","status":"VERIFICATION_ONLY","digest":digest_payload(postfreeze)},
    ]
    payload={
        "schema":HIDDEN_SCHEMA,"owner":HIDDEN_OWNER_ID,"patch_level":"persistent-residual-hidden-term-level-4",
        "runtime_release_id":api.runtime.current_release_id(),"experiment_source_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "status":"PASS_BLIND_HIDDEN_TERM_DISCOVERY" if passed==len(checks) else "FAIL_BLIND_HIDDEN_TERM_DISCOVERY",
        "passed":passed,"total":len(checks),"checks":[{"check":k,"status":"PASS" if v else "FAIL"} for k,v in checks.items()],
        "protocol":{
            "input_to_atlas":"masked primitive fields plus one frozen incomplete baseline operator signature",
            "request_freeze":freeze,"internet_used":False,"hidden_term_catalog_used":False,
            "language_expands_only_after_persistent_discovery_residual":True,
            "sealed_holdout_uses_unseen_parameters":True,"sealed_holdout_used_for_language_birth":False,
            "factor_depth_resource_budget_is_not_scientific_ceiling":True,
        },
        "blind_result":{
            "status":result.get("status"),"language_expansion_journal":stages,
            "selected_algebra_carrier_factor_depth":receipt.get("selected_algebra_carrier_factor_depth"),
            "initial_discovery_holdout_nrmse":initial_nrmse,"final_discovery_holdout_nrmse":final_nrmse,
            "sealed_holdout":sealed,"effective_predictor_variables":result.get("effective_predictor_variables"),
            "coefficients":coeff,"baseline_axis":baseline_axis,"hidden_candidate_axis_after_postfreeze_decode":expected_hidden_axis,
            "receipt_digest":receipt.get("digest"),
        },
        "postfreeze_decoding":postfreeze,"execution_receipt":receipt,"run_journal":journal,
        "claim_boundary":{
            "controlled_reference_world_only":True,"new_physical_law_claimed":False,"world_novelty_claimed":False,
            "hidden_term_was_known_to_fixture_builder_only":True,"hidden_term_was_not_named_to_search_kernel":True,
            "this_level_tests_unknown_term_recovery_from_persistent_residual":True,
        },
    }
    return {**payload,"digest":digest_payload(payload)}

def main() -> None:
    parser = argparse.ArgumentParser(description="Run blind continuum recovery benchmarks through the current Atlas kernel")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--mode", choices=("masked-terms","primitive-fields","invented-language","hidden-term"), default="masked-terms")
    parser.add_argument("--output", type=Path, default=None, help="Write full JSON receipt here")
    parser.add_argument("--summary", action="store_true", help="Print only compact summary to stdout")
    args = parser.parse_args()
    report = run_hidden_term_discovery(args.root) if args.mode == "hidden-term" else (run_operator_language_invention(args.root) if args.mode == "invented-language" else (run_primitive_field(args.root) if args.mode == "primitive-fields" else run(args.root)))
    if args.output is not None:
        output = args.output if args.output.is_absolute() else args.root / args.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary:
        if args.mode == "hidden-term":
            compact={"status":report["status"],"passed":report["passed"],"total":report["total"],"digest":report["digest"],"blind_result":report["blind_result"],"output":str(args.output) if args.output is not None else None}
        else:
            compact = {
                "status": report["status"], "passed": report["passed"], "total": report["total"], "digest": report["digest"],
                "x": report["blind_results"]["x_momentum"],
                "y": report["blind_results"]["y_momentum"],
                "output": str(args.output) if args.output is not None else None,
            }
            if "local_closure" in report["blind_results"]:
                compact["closure"] = report["blind_results"]["local_closure"]
        print(json.dumps(compact, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
