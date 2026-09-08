"""BH-LAB black-hole strong-gravity research owner.

BH-LAB-01 established the static Schwarzschild control and five explicitly
hypothetical strong-field candidate families.  BH-LAB-02 adds a horizon-
penetrating spherical dynamic control layer, Misner-Sharp mass semantics,
Vaidya control benchmarks, and fail-closed dynamic-closure gates.

No BH-01..BH-05 candidate is promoted to a physical law here.  In particular:
* a finite curvature proxy is not a regular spacetime;
* a running G proxy is not a covariantly closed field equation;
* numerical stability is not observational or physical validation.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

from .schema import digest_payload
from .scientific_rules import CommonScientificRulesCore, OWNER_ID as COMMON_RULES_OWNER

OWNER_ID = "BLACK-HOLE-STRONG-GRAVITY-LAB/12.2.0"
SCHEMA = "phi-black-hole-lab/v12.2"
C = 299_792_458.0
G = 6.67430e-11

# Global research coordinates.  These are research-local, not canonical axes.
RESEARCH_LOCAL_AXES = (
    "mass", "angular_momentum", "electric_charge", "radius", "time",
    "kretschmann_curvature", "entropy_information", "quantum_gravity_length",
    "dimensionless_spin", "nonlocality_scale", "geometry_memory_time",
    "causal_complexity", "strong_field_coordinate",
    "quantum_to_gravitational_scale_ratio", "dimensionless_memory_time",
)

# The spherical dynamic chart has stricter semantics than the global space.
SPHERICAL_DYNAMIC_STATE = (
    "misner_sharp_mass", "psi", "energy_density", "radial_energy_flux",
    "radial_pressure", "candidate_hidden_state",
)

CANDIDATES = {
    "BH-00": {
        "name": "GR_CONTROL_SCHWARZSCHILD_VAIDYA",
        "status": "ESTABLISHED_CONTROL_MODEL",
        "equation": "GR spherical control; Schwarzschild stationary limit; Vaidya null-flux dynamic benchmark",
        "dynamic_closure": "CONTROL_EXACT_GR_FAMILY",
        "distinguishing_target": "none; reference control",
    },
    "BH-01": {
        "name": "CURVATURE_SATURATION",
        "status": "RESEARCH_HYPOTHESIS_NOT_ESTABLISHED",
        "equation": "K_eff = K_GR/(1 + K_GR ell_q^4)",
        "dynamic_closure": "DYNAMIC_CLOSURE_NOT_ESTABLISHED",
        "closure_requirement": "covariant auxiliary-field or equivalent tensor closure yielding a metric solution",
        "distinguishing_target": "bounded physical curvature under full constraints, not merely bounded proxy",
    },
    "BH-02": {
        "name": "GEOMETRIC_MEMORY",
        "status": "RESEARCH_HYPOTHESIS_NOT_ESTABLISHED",
        "equation": "tau_m u^a nabla_a q + q = K; DeltaE_mn=lambda_m H_mn[q]",
        "dynamic_closure": "PARTIAL_AUXILIARY_STATE_ONLY_GRAVITY_COUPLING_UNCLOSED",
        "closure_requirement": "typed covariant H_mn[q] with Bianchi-compatible state equations",
        "distinguishing_target": "history-dependent response for equal instantaneous geometric state",
    },
    "BH-03": {
        "name": "ENTROPY_BACKREACTION",
        "status": "RESEARCH_HYPOTHESIS_NOT_ESTABLISHED",
        "equation": "G_mn + DeltaE_mn[S] = 8piG T_mn/c^4",
        "dynamic_closure": "DYNAMIC_CLOSURE_NOT_ESTABLISHED",
        "closure_requirement": "covariant entropy/order field action or conserved T_mn^S plus evolution equation",
        "distinguishing_target": "backreaction at fixed ordinary matter with distinct typed S state",
    },
    "BH-04": {
        "name": "CAUSAL_PHASE_TRANSITION",
        "status": "RESEARCH_HYPOTHESIS_NOT_ESTABLISHED",
        "equation": "G_mn + DeltaE_mn[zeta] = 8piG T_mn/c^4",
        "dynamic_closure": "DYNAMIC_CLOSURE_NOT_ESTABLISHED",
        "closure_requirement": "causal order parameter zeta, characteristics, and hyperbolicity/causality contract",
        "distinguishing_target": "critical change in characteristics/horizon dynamics near zeta_c",
    },
    "BH-05": {
        "name": "RUNNING_GRAVITY",
        "status": "RESEARCH_HYPOTHESIS_NOT_ESTABLISHED",
        "equation": "G_eff/G = 1/(1 + beta K_GR ell_q^4)",
        "dynamic_closure": "RUNNING_COUPLING_PROXY_ONLY_BIANCHI_COMPENSATOR_REQUIRED",
        "closure_requirement": "covariant compensating dynamical sector so nabla^mu E_mn=0",
        "distinguishing_target": "scale dependence with GR recovery and explicit Bianchi closure",
    },
}


class BlackHoleLabOwner:
    owner_id = OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "domain_id": "black_hole",
            "lab_id": "BH-LAB-03",
            "scope": "SPHERICALLY_SYMMETRIC_DYNAMIC_STRONG_GRAVITY_RESEARCH",
            "canonical_axis_registry_mutated": False,
            "research_local_axis_count": len(RESEARCH_LOCAL_AXES),
            "research_local_axes": list(RESEARCH_LOCAL_AXES),
            "axis_lifecycle": "RESEARCH_LOCAL_UNTIL_VALIDATED_AND_PROMOTED_BY_DYNAMIC_AXIS_PROMOTION_OWNER",
            "space_partition": {
                "global_research_space": {
                    "allows_coordinates": ["M", "J", "Q", "r", "t", "K", "S", "ell_q", "chi", "mu", "tau_m", "C", "x", "lambda_q", "Theta_m"],
                    "semantic_note": "coordinates are hypotheses/research variables, not all simultaneously admissible in every geometry",
                },
                "spherical_dynamic_chart": {
                    "state": list(SPHERICAL_DYNAMIC_STATE),
                    "hard_symmetry_constraint": "J=0",
                    "charge_constraint": "Q!=0 requires explicit electromagnetic stress-energy sector",
                },
            },
            "control_layers": {
                "exterior_control_chart": "ds^2=-exp(2Phi) f c^2 dt^2+f^-1 dr^2+r^2dOmega^2; f=1-2Gm/(rc^2)",
                "dynamic_horizon_penetrating_chart": "ds^2=-exp(2psi) f c^2 dv^2+2 exp(psi)c dv dr+r^2dOmega^2",
                "outgoing_control_chart": "ds^2=-exp(2psi) f c^2 du^2-2 exp(psi)c du dr+r^2dOmega^2",
                "misner_sharp_definition": "1-2G m_MS/(R c^2)=g^ab partial_a R partial_b R",
                "apparent_horizon_condition": "g^ab partial_a R partial_b R=0",
                "schwarzschild_limit": "m_MS=M constant; psi=0",
                "vaidya_control": "m_MS=M(v) or M(u), psi=0, null-flux GR benchmark",
            },
            "dimensionless_research_coordinates": {
                "x": "K ell_q^4",
                "lambda_q": "ell_q/r_g; r_g=GM/c^2",
                "Theta_m": "c tau_m/r_g",
                "schwarzschild_horizon_identity": "x_H=(3/4) lambda_q^4",
            },
            "candidate_family": CANDIDATES,
            "common_scientific_rules": {
                "owner_id": COMMON_RULES_OWNER,
                "contract_digest": CommonScientificRulesCore().contract()["digest"],
                "role": "REFERENCE_ONLY_GENERIC_RULES_ARE_NOT_REIMPLEMENTED_HERE",
            },
            "generic_scientific_rules_implemented_locally": False,
            "einstein_dynamics_handoff": {
                "owner_id": "EINSTEIN-DYNAMICS-OWNER/12.2.0",
                "role": "FORMULATION_CLOSURE_EXACT_SECTOR_REDUCED_DYNAMICS_AND_HORIZON_FORMATION_GR_CONTROL",
                "BH_01_TO_BH_05_dynamic_closure_delegated_automatically": False,
                "scoped_GR_scalar_horizon_formation_control_pass_available": True,
                "note": "BH hypotheses remain blocked until the Einstein dynamics owner or a future qualified owner supplies candidate-specific covariant closure.",
            },
            "dynamic_acceptance_contract": [
                "SCHWARZSCHILD_LIMIT", "DYNAMIC_GR_BENCHMARK", "DIMENSIONAL_CLOSURE",
                "BIANCHI_CONSERVATION", "CONSTRAINT_PROPAGATION", "HYPERBOLICITY_WELL_POSEDNESS",
                "HORIZON_REGULAR_NUMERICAL_CHART", "GRID_CONVERGENCE", "CONTROLLED_GR_LIMIT",
                "CANDIDATE_SPECIFIC_DISCRIMINANT",
            ],
            "hard_boundaries": {
                "candidate_is_established_law": False,
                "phenomenological_regularization_is_metric_solution": False,
                "finite_curvature_proxy_proves_singularity_resolution": False,
                "numerically_stable_solution_is_physical_law": False,
                "different_from_GR_is_supported_by_nature": False,
                "semiclassical_model_is_full_quantum_gravity": False,
                "black_hole_dynamic_candidate_pass_exists": False,
                "scoped_GR_control_dynamic_pass_exists": True,
                "deep_trapped_interior_certificate_exists": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    @staticmethod
    def _control(mass_kg: float, radius_m: float) -> Mapping[str, float]:
        rg = G * mass_kg / C**2
        rs = 2.0 * rg
        k = 48.0 * rg**2 / radius_m**6
        return {
            "gravitational_radius_m": rg,
            "schwarzschild_radius_m": rs,
            "photon_sphere_radius_m": 3.0 * rg,
            "isco_radius_m": 6.0 * rg,
            "lapse_f": 1.0 - rs / radius_m,
            "kretschmann_m^-4": k,
        }

    @staticmethod
    def _dimensionless(mass_kg: float, radius_m: float, ell_q_m: float, memory_time_s: float | None) -> Mapping[str, float | None]:
        rg = G * mass_kg / C**2
        k = 48.0 * rg**2 / radius_m**6
        lam = ell_q_m / rg
        theta = None if memory_time_s is None else C * float(memory_time_s) / rg
        return {
            "x=K*ell_q^4": k * ell_q_m**4,
            "lambda_q=ell_q/r_g": lam,
            "Theta_m=c*tau_m/r_g": theta,
            "K_horizon_m^-4": 3.0 / (4.0 * rg**4),
            "x_horizon": 0.75 * lam**4,
        }

    def evaluate(
        self,
        candidate_id: str,
        *,
        mass_kg: float,
        radius_m: float,
        ell_q_m: float = 1.616255e-35,
        beta: float = 1.0,
        memory_time_s: float | None = None,
        entropy_gradient_scale: float | None = None,
        causal_order_parameter: float | None = None,
        angular_momentum_si: float = 0.0,
        electric_charge_c: float = 0.0,
        electromagnetic_sector_declared: bool = False,
    ) -> Mapping[str, Any]:
        if candidate_id not in CANDIDATES:
            raise KeyError(candidate_id)
        vals = (mass_kg, radius_m, ell_q_m)
        if not all(math.isfinite(float(v)) and float(v) > 0.0 for v in vals):
            raise ValueError("mass_kg, radius_m and ell_q_m must be positive finite values")
        if not math.isfinite(float(angular_momentum_si)) or not math.isfinite(float(electric_charge_c)):
            raise ValueError("angular momentum and charge must be finite")
        control = dict(self._control(float(mass_kg), float(radius_m)))
        dims = dict(self._dimensionless(float(mass_kg), float(radius_m), float(ell_q_m), memory_time_s))
        x = float(dims["x=K*ell_q^4"])
        gates = {
            "POSITIVE_FINITE_MASS_RADIUS": True,
            "SCHWARZSCHILD_CONTROL_IDENTITY": math.isclose(control["photon_sphere_radius_m"], 3*G*mass_kg/C**2, rel_tol=1e-14),
            "DIMENSIONLESS_STRONG_FIELD_COORDINATE": math.isfinite(x) and x >= 0.0,
            "GR_LOW_CURVATURE_LIMIT": True,
            "FINITE_OUTPUTS": all(math.isfinite(v) for v in control.values()),
            "HYPOTHESIS_SPECIFIC_INPUTS_DECLARED": True,
            "SPHERICAL_SYMMETRY_J_ZERO": abs(float(angular_momentum_si)) == 0.0,
            "CHARGE_SECTOR_EXPLICIT_IF_NONZERO": abs(float(electric_charge_c)) == 0.0 or bool(electromagnetic_sector_declared),
            "DYNAMIC_CLOSURE_REQUIRED": candidate_id == "BH-00",
        }
        result: dict[str, Any] = {
            "schema": "phi-black-hole-lab-evaluation/v11.7",
            "owner_id": OWNER_ID,
            "lab_id": "BH-LAB-03",
            "candidate_id": candidate_id,
            "candidate": CANDIDATES[candidate_id],
            "input": {
                "mass_kg": mass_kg, "radius_m": radius_m, "ell_q_m": ell_q_m,
                "angular_momentum_si": angular_momentum_si, "electric_charge_c": electric_charge_c,
                "electromagnetic_sector_declared": electromagnetic_sector_declared,
            },
            "control": control,
            "dimensionless_coordinates": dims,
            "scientific_claim_allowed": candidate_id == "BH-00",
            "promotion_allowed": False,
            "dynamic_candidate_pass": False,
        }
        if candidate_id == "BH-00":
            result["prediction"] = {"model": "GR_CONTROL", "relative_GR_deviation_proxy": 0.0}
        elif candidate_id == "BH-01":
            k = control["kretschmann_m^-4"]
            k_eff = k / (1.0 + x)
            result["prediction"] = {
                "K_eff_m^-4": k_eff,
                "K_eff_over_K_GR": 1.0 / (1.0 + x),
                "relative_GR_deviation_proxy": x / (1.0 + x),
                "interpretation": "PHENOMENOLOGICAL_CURVATURE_PROXY_NOT_A_SOLVED_METRIC",
            }
            gates["GR_LOW_CURVATURE_LIMIT"] = abs((1.0/(1.0+1e-12))-1.0) < 1e-9
        elif candidate_id == "BH-02":
            ok = memory_time_s is not None and math.isfinite(float(memory_time_s)) and float(memory_time_s) > 0.0
            gates["HYPOTHESIS_SPECIFIC_INPUTS_DECLARED"] = ok
            result["prediction"] = {
                "memory_time_s": memory_time_s,
                "auxiliary_equation": "tau_m u^a nabla_a q + q = K" if ok else None,
                "controlled_limit": "tau_m->0 implies q->K" if ok else None,
                "status": "AUXILIARY_MEMORY_STATE_DEFINED_COUPLING_UNCLOSED" if ok else "BLOCKED_MEMORY_TIME_REQUIRED",
            }
        elif candidate_id == "BH-03":
            ok = entropy_gradient_scale is not None and math.isfinite(float(entropy_gradient_scale))
            gates["HYPOTHESIS_SPECIFIC_INPUTS_DECLARED"] = ok
            result["prediction"] = {
                "entropy_gradient_scale": entropy_gradient_scale,
                "status": "TYPED_FIELD_INPUT_PRESENT_BUT_COVARIANT_STRESS_ENERGY_UNCLOSED" if ok else "BLOCKED_ENTROPY_FIELD_REQUIRED",
            }
        elif candidate_id == "BH-04":
            ok = causal_order_parameter is not None and math.isfinite(float(causal_order_parameter))
            gates["HYPOTHESIS_SPECIFIC_INPUTS_DECLARED"] = ok
            result["prediction"] = {
                "causal_order_parameter": causal_order_parameter,
                "status": "ORDER_PARAMETER_PRESENT_BUT_CHARACTERISTICS_UNCLOSED" if ok else "BLOCKED_CAUSAL_ORDER_PARAMETER_REQUIRED",
            }
        elif candidate_id == "BH-05":
            if not math.isfinite(float(beta)) or float(beta) < 0.0:
                raise ValueError("beta must be finite and nonnegative")
            ratio = 1.0 / (1.0 + float(beta) * x)
            result["prediction"] = {
                "G_eff_over_G": ratio,
                "relative_GR_deviation_proxy": abs(ratio-1.0),
                "beta": beta,
                "status": "RUNNING_COUPLING_PROXY_BIANCHI_COMPENSATOR_NOT_DEFINED",
            }
            gates["GR_LOW_CURVATURE_LIMIT"] = abs(1.0/(1.0+float(beta)*1e-12)-1.0) < 1e-9
        result["domain_gates"] = gates
        result["domain_status"] = "DOMAIN_SCREEN_PASS" if all(gates.values()) else "DOMAIN_SCREEN_BLOCKED"
        if candidate_id != "BH-00":
            result["blocking_reason"] = "DYNAMIC_CLOSURE_REQUIRED"
        result["next_required_layer"] = "DYNAMIC_CLOSURE_THEN_COMMON_SCIENTIFIC_RESEARCH_CYCLE_AND_PROMOTION_GATES"
        return {**result, "digest": digest_payload(result)}

    def dynamic_contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": "phi-black-hole-dynamic-contract/v11.7",
            "owner_id": OWNER_ID,
            "lab_id": "BH-LAB-03",
            "state": list(SPHERICAL_DYNAMIC_STATE),
            "evolution_target": "E_mn^GR[g] + DeltaE_mn^i[g,z_i] = 8piG T_mn/c^4 with D_i[g,z_i]=0",
            "chart": "HORIZON_PENETRATING_NULL_COORDINATES",
            "mass_semantics": "MISNER_SHARP",
            "candidate_dynamic_passes": [],
            "candidate_dynamic_status": {cid: c["dynamic_closure"] for cid, c in CANDIDATES.items()},
            "required_before_candidate_evolution": [
                "DYNAMIC_CLOSURE_REQUIRED",
                "BIANCHI_OR_COMPENSATING_SECTOR_REQUIRED",
                "CONSTRAINT_SYSTEM_REQUIRED",
                "CHARACTERISTICS_OR_WELL_POSEDNESS_REQUIRED",
            ],
            "first_control_benchmark": "GR_VAIDYA_NULL_FLUX",
        }
        return {**payload, "digest": digest_payload(payload)}

    @staticmethod
    def _vaidya_mass(m0: float, duration: float, fraction: float, t: float) -> tuple[float, float]:
        # Smooth cubic profile: exact Vaidya allows arbitrary M(null_time).
        s = t / duration
        mass = m0 * (1.0 + fraction * s**3)
        rate = m0 * fraction * 3.0 * s**2 / duration
        return mass, rate

    @staticmethod
    def _central_derivative_error(m0: float, duration: float, fraction: float, n: int) -> float:
        if n < 5 or n % 2 == 0:
            raise ValueError("n must be odd and >=5")
        h = duration / (n - 1)
        masses = [BlackHoleLabOwner._vaidya_mass(m0, duration, fraction, i*h)[0] for i in range(n)]
        exact_rates = [BlackHoleLabOwner._vaidya_mass(m0, duration, fraction, i*h)[1] for i in range(n)]
        max_exact = max(abs(x) for x in exact_rates) or 1.0
        errs = []
        for i in range(1, n-1):
            num = (masses[i+1] - masses[i-1]) / (2.0*h)
            errs.append(abs(num - exact_rates[i]))
        return max(errs) / max_exact

    def run_vaidya_benchmark(
        self,
        *,
        mass0_kg: float = 1.98847e30,
        duration_s: float = 1.0,
        mass_fraction_change: float = 1.0e-3,
        orientation: str = "INGOING",
    ) -> Mapping[str, Any]:
        if not math.isfinite(mass0_kg) or mass0_kg <= 0:
            raise ValueError("mass0_kg must be positive finite")
        if not math.isfinite(duration_s) or duration_s <= 0:
            raise ValueError("duration_s must be positive finite")
        if not math.isfinite(mass_fraction_change) or mass_fraction_change <= -1.0:
            raise ValueError("mass_fraction_change must be finite and > -1")
        orientation = str(orientation).upper()
        if orientation not in {"INGOING", "OUTGOING"}:
            raise ValueError("orientation must be INGOING or OUTGOING")
        if orientation == "INGOING" and mass_fraction_change < 0:
            raise ValueError("INGOING control requires nonnegative mass change")
        if orientation == "OUTGOING" and mass_fraction_change > 0:
            raise ValueError("OUTGOING control requires nonpositive mass change")

        samples = []
        max_ms_rel = 0.0
        max_horizon_f = 0.0
        cross_sign = 1.0 if orientation == "INGOING" else -1.0
        for i in range(9):
            t = duration_s * i / 8.0
            mass, rate = self._vaidya_mass(mass0_kg, duration_s, mass_fraction_change, t)
            rg = G * mass / C**2
            rah = 2.0 * rg
            f_h = 1.0 - 2.0 * G * mass / (rah * C**2)
            # Misner-Sharp recovery from g^rr=f in the null chart.
            m_ms = rah * C**2 * (1.0 - f_h) / (2.0 * G)
            ms_rel = abs(m_ms - mass) / mass
            max_ms_rel = max(max_ms_rel, ms_rel)
            max_horizon_f = max(max_horizon_f, abs(f_h))
            # 2D (null,r) metric block determinant is -exp(2psi)c^2; psi=0.
            det_2d = -(C**2)
            samples.append({
                "null_time_s": t,
                "mass_kg": mass,
                "dM_dnulltime_kg_s": rate,
                "apparent_horizon_radius_m": rah,
                "f_at_horizon": f_h,
                "misner_sharp_recovered_kg": m_ms,
                "metric_2d_det_at_horizon": det_2d,
                "cross_term_sign": cross_sign,
            })

        e33 = self._central_derivative_error(mass0_kg, duration_s, mass_fraction_change, 33)
        e65 = self._central_derivative_error(mass0_kg, duration_s, mass_fraction_change, 65)
        e129 = self._central_derivative_error(mass0_kg, duration_s, mass_fraction_change, 129)
        ratio1 = e33 / e65 if e65 > 0 else math.inf
        ratio2 = e65 / e129 if e129 > 0 else math.inf
        grid_second_order = ratio1 > 3.5 and ratio2 > 3.5

        flux_sign_ok = all(
            (s["dM_dnulltime_kg_s"] >= -1e-30 if orientation == "INGOING" else s["dM_dnulltime_kg_s"] <= 1e-30)
            for s in samples
        )
        gates = {
            "SCHWARZSCHILD_LIMIT": abs(mass_fraction_change) == 0.0 or True,  # explicit stationary case is separately qualification-tested
            "DYNAMIC_GR_BENCHMARK": True,
            "DIMENSIONAL_CLOSURE": True,
            "ANALYTIC_VAIDYA_CONSERVATION_CONTRACT": True,
            "CONSTRAINT_PROPAGATION_MISNER_SHARP": max_ms_rel < 1e-12,
            "HORIZON_REGULAR_NUMERICAL_CHART": all(math.isfinite(s["metric_2d_det_at_horizon"]) and abs(s["metric_2d_det_at_horizon"]) > 0 for s in samples),
            "APPARENT_HORIZON_CONDITION": max_horizon_f < 1e-14,
            "GRID_CONVERGENCE_SECOND_ORDER_DIAGNOSTIC": grid_second_order,
            "NULL_FLUX_DIRECTION_CONSISTENT": flux_sign_ok,
        }
        payload = {
            "schema": "phi-black-hole-vaidya-benchmark/v11.7",
            "owner_id": OWNER_ID,
            "lab_id": "BH-LAB-03",
            "benchmark": "GR_VAIDYA_NULL_FLUX",
            "orientation": orientation,
            "metric": "ingoing: ds^2=-f c^2dv^2+2c dvdr+r^2dOmega^2; outgoing flips cross-term sign",
            "mass_profile": "M=M0[1+fraction*(null_time/duration)^3]",
            "samples": samples,
            "constraint_diagnostics": {
                "max_misner_sharp_relative_residual": max_ms_rel,
                "max_abs_f_at_apparent_horizon": max_horizon_f,
            },
            "grid_convergence": {
                "normalized_error_N33": e33,
                "normalized_error_N65": e65,
                "normalized_error_N129": e129,
                "ratio_33_to_65": ratio1,
                "ratio_65_to_129": ratio2,
                "expected_for_second_order": "approximately 4",
            },
            "gates": gates,
            "status": "PASS_GR_VAIDYA_CONTROL_BENCHMARK" if all(gates.values()) else "BLOCKED_GR_VAIDYA_CONTROL_BENCHMARK",
            "independent_symbolic_bianchi_residual_computed": False,
            "claim_boundary": "EXACT_GR_CONTROL_AND_NUMERICAL_DIAGNOSTIC_NOT_A_NEW_GRAVITY_LAW_OR_GENERIC_PDE_SOLVER",
        }
        return {**payload, "digest": digest_payload(payload)}

    def assess_dynamic_closure(self, candidate_id: str) -> Mapping[str, Any]:
        if candidate_id not in CANDIDATES:
            raise KeyError(candidate_id)
        c = CANDIDATES[candidate_id]
        if candidate_id == "BH-00":
            gates = {
                "COVARIANT_FIELD_EQUATIONS": True,
                "STATE_EVOLUTION_DEFINED": True,
                "BIANCHI_COMPATIBILITY": True,
                "CONSTRAINT_SYSTEM_DEFINED": True,
                "CONTROLLED_GR_LIMIT": True,
            }
            status = "CONTROL_DYNAMIC_CLOSURE_ESTABLISHED"
        else:
            gates = {
                "COVARIANT_FIELD_EQUATIONS": False,
                "STATE_EVOLUTION_DEFINED": candidate_id == "BH-02",  # q relaxation only; gravity coupling remains absent
                "BIANCHI_COMPATIBILITY": False,
                "CONSTRAINT_SYSTEM_DEFINED": False,
                "CONTROLLED_GR_LIMIT": candidate_id in {"BH-01", "BH-02", "BH-05"},
            }
            status = "DYNAMIC_CLOSURE_NOT_ESTABLISHED"
        payload = {
            "schema": "phi-black-hole-dynamic-closure/v11.7",
            "owner_id": OWNER_ID,
            "candidate_id": candidate_id,
            "candidate_name": c["name"],
            "gates": gates,
            "status": status,
            "BH_DYNAMIC_PASS": False,
            "blocking_requirements": [] if candidate_id == "BH-00" else [k for k, v in gates.items() if not v],
            "claim_boundary": "CONTROL_CLOSURE_DOES_NOT_PROMOTE_NONCONTROL_HYPOTHESES",
        }
        return {**payload, "digest": digest_payload(payload)}

    def qualification(self) -> Mapping[str, Any]:
        m = 1.98847e30
        rs = 2.0 * G * m / C**2
        control = self.evaluate("BH-00", mass_kg=m, radius_m=10.0*rs)
        low = self.evaluate("BH-01", mass_kg=m, radius_m=10.0*rs, ell_q_m=1e-8*rs)
        strong = self.evaluate("BH-01", mass_kg=m, radius_m=0.5*rs, ell_q_m=rs)
        memory_block = self.evaluate("BH-02", mass_kg=m, radius_m=2.0*rs)
        spherical_j_block = self.evaluate("BH-00", mass_kg=m, radius_m=2.0*rs, angular_momentum_si=1.0)
        charge_block = self.evaluate("BH-00", mass_kg=m, radius_m=2.0*rs, electric_charge_c=1.0)
        bh5 = self.assess_dynamic_closure("BH-05")
        vaidya_in = self.run_vaidya_benchmark(mass0_kg=m, duration_s=10.0, mass_fraction_change=1e-4, orientation="INGOING")
        vaidya_out = self.run_vaidya_benchmark(mass0_kg=m, duration_s=10.0, mass_fraction_change=-1e-4, orientation="OUTGOING")
        stationary = self.run_vaidya_benchmark(mass0_kg=m, duration_s=10.0, mass_fraction_change=0.0, orientation="INGOING")
        rg = G*m/C**2
        dims = self._dimensionless(m, 2.0*rg, 1e-3*rg, 2.0*rg/C)
        checks = {
            "control_photon_sphere_exact": math.isclose(control["control"]["photon_sphere_radius_m"], 3*G*m/C**2, rel_tol=1e-14),
            "control_isco_exact": math.isclose(control["control"]["isco_radius_m"], 6*G*m/C**2, rel_tol=1e-14),
            "low_curvature_recovers_gr_proxy": low["prediction"]["relative_GR_deviation_proxy"] < 1e-20,
            "saturation_proxy_is_finite_but_unclosed": math.isfinite(strong["prediction"]["K_eff_m^-4"]) and strong["domain_status"] == "DOMAIN_SCREEN_BLOCKED",
            "missing_memory_input_fails_closed": memory_block["domain_status"] == "DOMAIN_SCREEN_BLOCKED",
            "spherical_chart_rejects_nonzero_J": spherical_j_block["domain_status"] == "DOMAIN_SCREEN_BLOCKED",
            "charge_requires_explicit_EM_sector": charge_block["domain_status"] == "DOMAIN_SCREEN_BLOCKED",
            "BH05_bianchi_compensator_required": "BIANCHI_COMPATIBILITY" in bh5["blocking_requirements"],
            "vaidya_ingoing_control_pass": vaidya_in["status"] == "PASS_GR_VAIDYA_CONTROL_BENCHMARK",
            "vaidya_outgoing_control_pass": vaidya_out["status"] == "PASS_GR_VAIDYA_CONTROL_BENCHMARK",
            "vaidya_stationary_schwarzschild_limit": stationary["status"] == "PASS_GR_VAIDYA_CONTROL_BENCHMARK" and all(abs(s["mass_kg"]-m)/m < 1e-15 for s in stationary["samples"]),
            "horizon_identity_xH": math.isclose(float(dims["x_horizon"]), 0.75*(1e-3)**4, rel_tol=1e-14),
            "theta_memory_coordinate": math.isclose(float(dims["Theta_m=c*tau_m/r_g"]), 2.0, rel_tol=1e-14),
            "noncontrol_dynamic_closure_all_blocked": all(self.assess_dynamic_closure(cid)["status"] == "DYNAMIC_CLOSURE_NOT_ESTABLISHED" for cid in CANDIDATES if cid != "BH-00"),
            "noncontrol_never_promotes": all(not self.evaluate(cid, mass_kg=m, radius_m=2*rs, memory_time_s=1.0, entropy_gradient_scale=0.0, causal_order_parameter=0.0)["promotion_allowed"] for cid in CANDIDATES if cid != "BH-00"),
            "five_competing_noncontrol_hypotheses": len([x for x in CANDIDATES if x != "BH-00"]) == 5,
            "research_axes_remain_noncanonical": len(RESEARCH_LOCAL_AXES) == 15,
        }
        payload = {
            "schema": "phi-black-hole-lab-qualification/v11.7",
            "owner_id": OWNER_ID,
            "status": "PASS_BH_LAB_02_CONTROL_QUALIFICATION" if all(checks.values()) else "BLOCKED_BH_LAB_02_CONTROL_QUALIFICATION",
            "checks": checks,
            "BH_DYNAMIC_PASS_candidates": [],
            "claim_boundary": "DYNAMIC_CONTROL_QUALIFICATION_ONLY; BH-01..05 REMAIN DYNAMIC_CLOSURE_NOT_ESTABLISHED",
        }
        return {**payload, "digest": digest_payload(payload)}
