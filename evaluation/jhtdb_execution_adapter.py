"""JHTDB domain binding for the common execution runtime. No experiment loop.

Unlike the supplied V6, this never discovers a measurement function by trying it
on held-out data, nor replaces the learned finite-stencil action by FFT axes.
"""
from __future__ import annotations

import io
from pathlib import Path

import numpy as np

from evaluation import turbulence_dns_closure_experiment as dns
from source.lawspace.theory_compiler import PrimitiveFieldOperatorCoordinateBirthOwner as Operators


class DNSFrozenMeasurement:
    adapter_id = "DNS-SGS-FROZEN-TRANSLATION-MOMENT/1"
    implementation_files = (Path(dns.__file__), Path(__import__(Operators.__module__, fromlist=["__file__"]).__file__))

    def preflight(self, contract):
        blockers = []
        samples = {x["sample_id"]: x["request"] for x in contract["samples"]}
        for case in contract["cases"]:
            request = samples[case["sample_id"]]
            ratio = case["filter_ratio"]
            if type(ratio) is not int or ratio < 1 or case["component"] not in dns.COMPONENT_INDEX:
                raise ValueError("invalid DNS component or ratio")
            if case.get("chart") != "COARSE_GRID_FINITE_STENCIL_R3":
                blockers.append({"case_id": case["case_id"], "reason": "FROZEN_NUMERICAL_CHART_REQUIRED"})
            if any(len(range(0, n, ratio)) < 9 for n in request["shape"]):
                blockers.append({"case_id": case["case_id"], "reason": "INSUFFICIENT_COARSE_GRID_FOR_FROZEN_OPERATOR",
                                 "coarse_shape": [len(range(0, n, ratio)) for n in request["shape"]], "minimum_points": 9})
            points = case.get("grid_points")
            if points is None:
                blockers.append({"case_id": case["case_id"], "reason": "FROZEN_GRID_POINTS_REQUIRED"})
            else:
                dns._subcube_slices([len(range(0, n, ratio)) for n in request["shape"]], points, case.get("offset"))
            required = {f for form in contract["forms"] if form["case_id"] == case["case_id"] for f in form["feature_ids"]}
            if required != set(case["axis_signatures"]):
                raise ValueError("frozen axes and signatures differ")
            for spec in case["axis_signatures"].values():
                if (spec["kind"] != "POINTWISE_MONOMIAL_X_LOCAL_TRANSLATION_MOMENT_RESPONSE"
                        or spec["response_field"] not in {"g0", "g1", "g2", "g3"}
                        or spec["coordinate"] not in {"r1", "r2", "r3"}
                        or type(spec["moment_rank"]) is not int or not 1 <= spec["moment_rank"] <= 6):
                    raise ValueError("unsupported frozen operator")
                for factor in spec["carrier_factors"]:
                    if factor["field"] not in {"g0", "g1", "g2", "g3"} or type(factor["power"]) is not int:
                        raise ValueError("invalid carrier factor")
        return blockers

    def measure(self, evidence, cases):
        with np.load(io.BytesIO(evidence), allow_pickle=False) as data:
            velocity = tuple(np.asarray(data[name], dtype=float) for name in ("u", "v", "w"))
            dx = float(data["dx"])
        if not np.isfinite(dx) or dx <= 0 or any(x.ndim != 3 or x.shape != velocity[0].shape or not np.isfinite(x).all() for x in velocity):
            raise ValueError("invalid raw DNS fields")
        result, cached = {}, {}
        for case in cases:
            ratio = case["filter_ratio"]
            if ratio not in cached:
                cached[ratio] = dns._sgs_residual(velocity, (dx, dx, dx), ratio)
            filtered, residual, _ = cached[ratio]
            study = dns._coarse_study(study_id=case["case_id"], role="SEALED", velocity=filtered,
                                      residual=residual, spacing=(dx, dx, dx), filter_ratio=ratio,
                                      atlas_grid_points=case["grid_points"], subcube_offset=case.get("offset"),
                                      component=case["component"])
            fields = {k: np.asarray(v) for k, v in study["fields"].items()}
            interior = (slice(Operators.stencil_radius, -Operators.stencil_radius),) * 3
            features = {}
            for axis, spec in case["axis_signatures"].items():
                response = Operators._differentiate(fields[spec["response_field"]], study["coordinates"][spec["coordinate"]],
                                                    study["coordinate_order"].index(spec["coordinate"]), spec["moment_rank"])
                for factor in spec["carrier_factors"]:
                    base, power = fields[factor["field"]], factor["power"]
                    if power < 0 and np.any(np.abs(base[interior]) <= 1e-14):
                        raise ValueError("singular frozen carrier")
                    with np.errstate(divide="ignore", invalid="ignore"):
                        response = response * np.power(base, power)
                features[axis] = response[interior].ravel().tolist()
            result[case["case_id"]] = {"observed": fields[dns.FIELD["target"]][interior].ravel().tolist(), "features": features}
        return result
