"""Current rotating cubic-Euler qualification for release 12.7.0."""
from __future__ import annotations
import json
from source.lawspace.einstein_dynamics import EinsteinDynamicsOwner
from source.lawspace.schema import digest_payload
from source.lawspace.tensor_geometry import TensorGeometryOwner

SCHEMA = "phi-rotating-cubic-euler-qualification/v12.7"
OWNER_ID = "ROTATING-CUBIC-EULER-QUALIFICATION/12.7.0"


def run():
    tensor = TensorGeometryOwner().run_rotating_cubic_euler_qualification()
    owner = EinsteinDynamicsOwner()
    solution = owner.run_rotating_cubic_euler_solution()
    post = owner.get_rotating_cubic_euler_postfreeze_assessment()
    checks = {
        "FULL_CUBIC_EULER_TENSOR_PASS": tensor.get("all_pass") is True and tensor.get("passed") == tensor.get("total") == 9,
        "ONLY_TPHI_PHIT_LINEAR_EULER_COMPONENTS": set(tensor.get("linear_spin_euler_nonzero_components", {})) == {"03", "30"},
        "ROTATING_TPHI_SOLUTION_PASS": solution.get("all_pass") is True and solution.get("passed") == solution.get("total") == 11,
        "DELTA_OMEGA_EXACT": solution.get("solution", {}).get("particular") == "-40*J*M**2/r**9",
        "FULL_MODIFIED_RESIDUAL_ZERO": solution.get("checks", {}).get("FULL_MODIFIED_TPHI_RESIDUAL_ZERO") is True,
        "HORIZON_FACTOR_CANCELLATION": solution.get("checks", {}).get("HORIZON_FACTOR_CANCELLATION_EXACT") is True,
        "ODD_SECTOR_NOT_FALSELY_SOLVED": solution.get("claim_boundary", {}).get("parity_odd_rotating_metric_solution_solved") is False,
        "POSTFREEZE_PRIOR_ART_BOUND": post.get("all_pass") is True and post.get("passed") == post.get("total") == 7,
        "WORLD_NOVELTY_NOT_CLAIMED": post.get("claim_boundary", {}).get("world_novelty_established") is False,
    }
    payload = {
        "schema": SCHEMA,
        "owner_id": OWNER_ID,
        "tensor": tensor,
        "solution": solution,
        "postfreeze": post,
        "checks": checks,
        "passed": sum(bool(v) for v in checks.values()),
        "total": len(checks),
        "status": "PASS_ROTATING_CUBIC_EULER_QUALIFICATION" if all(checks.values()) else "BLOCKED_ROTATING_CUBIC_EULER_QUALIFICATION",
        "claim_boundary": {
            "perturbative_rotating_pure_I3_solution_qualified": all(checks.values()),
            "full_nonperturbative_rotating_black_hole_qualified": False,
            "parity_odd_metric_solution_qualified": False,
            "world_novelty_established": False,
        },
    }
    return {**payload, "digest": digest_payload(payload)}

if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, sort_keys=True))
