"""Current bounded spin2 horizon-aligned / full parity-odd Euler closure for 13.3.0."""
from __future__ import annotations
import json
from source.lawspace.einstein_dynamics import EinsteinDynamicsOwner
from source.lawspace.tensor_geometry import TensorGeometryOwner
from source.lawspace.schema import digest_payload
SCHEMA="phi-spin2-odd-full-euler-multipole-qualification/v13.0"
OWNER_ID="SPIN2-ODD-FULL-EULER-MULTIPOLE-QUALIFICATION/13.3.0"

def run():
    owner=TensorGeometryOwner()
    tensor=owner.run_spin2_even_odd_gauge_qualification()
    closure=owner.run_horizon_aligned_spin2_odd_closure_qualification()
    oddfull=owner.run_full_parity_odd_euler_multipole_qualification()
    einstein=EinsteinDynamicsOwner()
    screen=einstein.run_spin2_odd_gauge_patch_screen()
    post=einstein.get_spin2_odd_postfreeze_assessment()
    checks={
      "BASELINE_SPIN2_ODD_11_11":tensor.get("all_pass") is True and tensor.get("passed")==tensor.get("total")==11,
      "KERR_O_A2_CONTROL":tensor.get("checks",{}).get("KERR_QUADRATIC_EINSTEIN_CONTROL") is True,
      "I3_A2_EXACT":tensor.get("quadratic_even",{}).get("I3_a2")=="-4320*M**3*cos(theta)**2/r**11",
      "OLD_BL_DEFECT_REPRODUCED":tensor.get("quadratic_even",{}).get("Q_cancel_pole")!=tensor.get("quadratic_even",{}).get("Q_cancel_log"),
      "HORIZON_ALIGNED_CLOSURE_20_20":closure.get("all_pass") is True and closure.get("passed")==closure.get("total")==20,
      "Q_BRANCH_MINUS_15_7":closure.get("even_spin2",{}).get("selected_Q")=="-15/7",
      "TWO_HORIZON_DIAGNOSTICS_MATCH":closure.get("checks",{}).get("KILLING_BLOCK_HORIZON_SHIFT_MATCH") is True,
      "INGOING_POLE_VECTOR_MATCHES_OMEGA_H":closure.get("checks",{}).get("INGOING_POLE_VECTOR_MATCHES_OMEGA_H") is True,
      "FULL_ODD_EULER_21_21":oddfull.get("all_pass") is True and oddfull.get("passed")==oddfull.get("total")==21,
      "ODD_FULL_SOURCE_CONSERVED":oddfull.get("checks",{}).get("ODD_EULER_COVARIANTLY_CONSERVED") is True,
      "ODD_TWO_DERIVATION_ROUTES_AGREE":oddfull.get("checks",{}).get("ROUTE_A_ROUTE_B_FULL_TENSOR_AGREE") is True,
      "FULL_UNPROJECTED_10_COMPONENT_RESIDUALS_ZERO":oddfull.get("checks",{}).get("FULL_UNPROJECTED_10_COMPONENT_RESIDUALS_ZERO") is True,
      "ODD_INGOING_HORIZON_REGULAR":oddfull.get("checks",{}).get("ODD_INGOING_HORIZON_REGULAR") is True,
      "ODD_ACMC_MASS_DIPOLE_REMOVED":oddfull.get("checks",{}).get("ACMC_MASS_DIPOLE_REMOVED") is True,
      "ODD_CURRENT_DIPOLE_UNCHANGED":oddfull.get("checks",{}).get("CURRENT_DIPOLE_UNCHANGED_AT_ODD_ORDER") is True,
      "GAUGE_INVARIANT_OBSERVABLE_EXACT":oddfull.get("checks",{}).get("GAUGE_INVARIANT_EINSTEIN_SQUARE_EXACT") is True,
      "EVEN_INDEPENDENT_NUMERICAL_REPRODUCTION":oddfull.get("checks",{}).get("EVEN_12_9_INDEPENDENT_HORIZON_SHIFT_REPRODUCED") is True,
      "EINSTEIN_SCREEN_14_14":screen.get("all_pass") is True and screen.get("passed")==screen.get("total")==14,
      "POSTFREEZE_16_16":post.get("all_pass") is True and post.get("passed")==post.get("total")==16,
      "KNOWN_LOW_MULTIPOLE_PRIOR_ART_RECORDED":post.get("novelty_verdict",{}).get("low_order_M1_deltaS1")=="KNOWN_PRIOR_ART",
      "WORLD_NOVELTY_NOT_CLAIMED":post.get("claim_boundary",{}).get("world_novelty_established") is False,
    }
    ok=all(checks.values())
    payload={
      "schema":SCHEMA,"owner_id":OWNER_ID,
      "baseline":tensor,"closure":closure,"full_odd_euler":oddfull,"screen":screen,"postfreeze":post,
      "checks":checks,"passed":sum(bool(v) for v in checks.values()),"total":len(checks),
      "status":"PASS_SPIN2_HORIZON_FULL_ODD_EULER_MULTIPOLE_QUALIFICATION" if ok else "BLOCKED_SPIN2_HORIZON_FULL_ODD_EULER_MULTIPOLE_QUALIFICATION",
      "claim_boundary":{
        "bounded_O_alpha_J2_horizon_representation_closed":ok,
        "full_unprojected_parity_odd_euler_tensor_solved_in_bounded_O_beta_a_sector":ok,
        "ACMC_mass_dipole_shift_zero":ok,
        "current_dipole_shift_zero_at_this_order":ok,
        "full_nonperturbative_rotating_black_hole_solved":False,
        "new_physical_dipole_hair_established":False,
        "world_novelty_established":False,
      },
      "next_gate":"higher-spin parity-odd invariant multipoles/observables beyond the published low-order result, with explicit operator-normalization and gauge map",
    }
    return {**payload,"digest":digest_payload(payload)}

if __name__=="__main__": print(json.dumps(run(),ensure_ascii=False,indent=2,sort_keys=True))
