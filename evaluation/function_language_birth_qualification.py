"""Current qualification for residual-driven function-language birth.

This is a mechanism qualification, not evidence for a new scientific law.  The
hidden generators are synthetic controls chosen to require distinct operation
classes.  The important gates are: no birth when polynomial residual is already
small, no forced birth on structureless noise, strong improvement on held-out
periodic/local structure, and full replay of data-dependent language birth under
the permutation null.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import numpy as np

from source.lawspace.query_research import QueryDrivenResearchOwner
from source.lawspace.schema import digest_payload

SCHEMA = "phi-function-language-birth-qualification/v1"
OWNER_ID = "PHI-MATHEMATICAL-INVENTION-KERNEL/1.1.0::FUNCTION-LANGUAGE-BIRTH"


def _world(seed: int, n: int = 240):
    rng = np.random.default_rng(seed)
    x = rng.uniform(-2.5, 2.5, (n, 4))
    obs = {f"x{i}": x[:, i] for i in range(4)}
    dims = {name: [0, 0, 0, 0, 0, 0, 0] for name in [*obs, "y"]}
    return rng, x, obs, dims


def _run(y, x, obs, dims, *, birth: bool, permutations: int = 0):
    q = QueryDrivenResearchOwner()
    payload = dict(obs); payload["y"] = np.asarray(y, float)
    return q.search_function_forms(
        observations=payload,
        dimensions=dims,
        target_name="y",
        axis_names=[f"x{i}" for i in range(4)],
        hypothesis_budget=100,
        return_limit=100,
        permutation_count=int(permutations),
        permutation_seed=1729,
        function_language_birth=bool(birth),
    )


def run_release_qualification(root: str | Path | None = None) -> dict[str, Any]:
    # Polynomial negative/control surface.
    rng, x, obs, dims = _world(1701)
    y_poly = 0.8 + 0.4*x[:, 0] - 0.25*x[:, 1] + 0.7*x[:, 0]*x[:, 1] + rng.normal(0, 0.015, len(x))
    poly = _run(y_poly, x, obs, dims, birth=True)

    # Periodic surface: deliberately outside the low-degree polynomial grammar.
    rng, x, obs, dims = _world(1702)
    y_periodic = 1.2*np.sin(3*x[:, 0]) + 0.35*np.cos(2*x[:, 1]) + rng.normal(0, 0.05, len(x))
    periodic_old = _run(y_periodic, x, obs, dims, birth=False)
    periodic_new = _run(y_periodic, x, obs, dims, birth=True, permutations=5)

    # Local bivariate surface: requires joint neighborhood structure.
    rng, x, obs, dims = _world(1703)
    y_kernel = (
        np.exp(-1.5*((x[:, 0]-0.7)**2 + (x[:, 1]+0.5)**2))
        + 0.4*np.exp(-2.0*((x[:, 0]+1.1)**2 + (x[:, 1]-1.0)**2))
        + rng.normal(0, 0.03, len(x))
    )
    kernel_old = _run(y_kernel, x, obs, dims, birth=False)
    kernel_new = _run(y_kernel, x, obs, dims, birth=True)

    # Pure-noise negative control: baseline error is large but operation signals
    # must not be manufactured merely to satisfy a minimum-language count.
    rng, x, obs, dims = _world(1704)
    noise = _run(rng.normal(0, 1.0, len(x)), x, obs, dims, birth=True)

    periodic_old_score = float(periodic_old["hypotheses"][0]["cross_validated_nrmse"])
    periodic_new_score = float(periodic_new["hypotheses"][0]["cross_validated_nrmse"])
    kernel_old_score = float(kernel_old["hypotheses"][0]["cross_validated_nrmse"])
    kernel_best = next(h for h in kernel_new["hypotheses"] if h.get("function_family") == "KERNEL")
    kernel_new_score = float(kernel_best["cross_validated_nrmse"])
    checks = {
        "polynomial_control_preserves_current_language": poly["function_language_birth"]["status"] == "CURRENT_LANGUAGE_RESIDUAL_WITHIN_BIRTH_TOLERANCE" and poly["search_surface"]["born_language_hypotheses_examined_total"] == 0,
        "periodic_residual_births_periodic_operation_language": "PERIODIC" in [r.get("family") for r in periodic_new["function_language_birth"].get("generated_languages", [])] and periodic_new["hypotheses"][0].get("function_family") == "PERIODIC",
        "periodic_language_materially_improves_oof_prediction": periodic_old_score > 0.70 and periodic_new_score < 0.20 and periodic_new_score < 0.30*periodic_old_score,
        "local_joint_residual_births_kernel_language": "KERNEL" in [r.get("family") for r in kernel_new["function_language_birth"].get("generated_languages", [])] and set(kernel_best.get("coordinate_indices", [])) == {0, 1},
        "kernel_language_materially_improves_oof_prediction": kernel_new_score < 0.55 and kernel_new_score < 0.70*kernel_old_score,
        "noise_control_does_not_force_language_birth": noise["function_language_birth"]["status"] == "NO_OPERATION_SIGNAL_ABOVE_BIRTH_GATE" and noise["function_language_birth"].get("generated_languages") == [],
        "dynamic_language_birth_is_inside_permutation_null": periodic_new["permutation_null"].get("dynamic_function_language_birth_replayed_each_permutation") is True and periodic_new["permutation_null"].get("entire_function_surface_refit_each_permutation") is True,
        "claim_boundary_remains_non_world": periodic_new["claim_boundary"].get("function_language_birth_is_world_mathematical_novelty_claim") is False and periodic_new["claim_boundary"].get("candidate_is_confirmed_law") is False,
    }
    payload = {
        "schema": SCHEMA,
        "owner": OWNER_ID,
        "status": "PASS_FUNCTION_LANGUAGE_BIRTH_QUALIFICATION" if all(checks.values()) else "FAIL_FUNCTION_LANGUAGE_BIRTH_QUALIFICATION",
        "checks": checks,
        "metrics": {
            "periodic_polynomial_nrmse": periodic_old_score,
            "periodic_born_language_nrmse": periodic_new_score,
            "periodic_improvement_fraction": 1.0-periodic_new_score/periodic_old_score,
            "kernel_polynomial_nrmse": kernel_old_score,
            "kernel_born_language_nrmse": kernel_new_score,
            "kernel_improvement_fraction": 1.0-kernel_new_score/kernel_old_score,
            "noise_effective_signal_gate": noise["function_language_birth"].get("effective_multiplicity_aware_signal_gate"),
            "noise_max_operation_signal": max(noise["function_language_birth"].get("operation_signal_scores", {"none": 0.0}).values()),
        },
        "claim_boundary": {
            "synthetic_controls_are_world_laws": False,
            "universal_optimizer_superiority_established": False,
            "real_world_replication_established": False,
            "function_language_search_exhausts_all_mathematics": False,
        },
    }
    payload["digest"] = digest_payload(payload)
    return payload


def main():
    import json
    print(json.dumps(run_release_qualification(), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
