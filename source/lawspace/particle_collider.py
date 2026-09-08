"""Collider qualification capability under the existing ParticleSpace owner.

This module deliberately does not own candidate generation or scientific promotion.
It provides deterministic global-form/charge-lattice gates and a reference lifetime
coordinate for post-freeze collider qualification.  Candidate-specific experiment
results remain materialized receipts under reports/.
"""
from __future__ import annotations

import math
from fractions import Fraction
from typing import Any, Mapping

from .particle_space import OWNER_ID, sm_gauge_global_form_profile
from .schema import digest_payload
from .scientific_rules import CommonScientificRulesCore, OWNER_ID as COMMON_RULES_OWNER

SCHEMA = "phi-particlespace-collider-qualification/v7.6"
CAPABILITY_ID = "PARTICLESPACE_COLLIDER_QUALIFICATION_V7_6"
HBARC_GEV_M = 1.973269804e-16
ELECTROWEAK_VEV_GEV = 246.0


class ParticleColliderQualification:
    """Post-freeze collider calculations with fail-closed benchmark transfer."""

    owner_id = OWNER_ID
    capability_id = CAPABILITY_ID

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner_id": self.owner_id,
            "capability_id": self.capability_id,
            "role": "POSTFREEZE_COLLIDER_QUALIFICATION_NOT_CANDIDATE_SELECTION_NOT_PROMOTION",
            "common_scientific_rules": {
                "owner_id": COMMON_RULES_OWNER,
                "contract_digest": CommonScientificRulesCore().contract()["digest"],
                "role": "REFERENCE_ONLY_GENERIC_RULES_ARE_NOT_REIMPLEMENTED_HERE",
            },
            "generic_scientific_rules_implemented_locally": False,
            "hard_boundaries": {
                "blind_selector_may_be_mutated_by_collider_feedback": False,
                "postfreeze_evidence_may_rerank_frozen_shortlist": False,
                "benchmark_mass_limit_transfer_without_amplitude_acceptance_equivalence": False,
                "handwritten_unvalidated_ufo_is_physics_evidence": False,
                "missing_generator_or_detector_toolchain_may_be_replaced_by_surrogate_acceptance": False,
                "conditional_benchmark_embedding_is_generic_particle_exclusion": False,
            },
            "reference_lifetime_coordinate": {
                "operator_class": "D7_HIGGS_ASSISTED_THREE_FERMION_PORTAL",
                "definition": "Gamma_ref=v^2*M^5/(1024*pi^3*Lambda_eff^6)",
                "ctau_definition": "ctau=hbarc/Gamma_ref",
                "Lambda_eff_semantics": "absorbs Wilson coefficient, Clebsch/color/flavor normalization and phase-space convention; not a UV scale claim by itself",
            },
            "required_detector_recast_chain": [
                "VALIDATED_UFO",
                "MATRIX_ELEMENT_GENERATOR",
                "VALIDATED_COLOR_FLOW",
                "SHOWER_AND_HADRONIZATION",
                "DETECTOR_EFFICIENCY_OR_VALIDATED_EMULATION",
                "PUBLISHED_OR_VALIDATED_LIKELIHOOD",
            ],
            "global_form_decay_gate": {
                "formula": "k6=(6Y+2*t3+3*s2) mod 6",
                "theorem": "all registered SM anchor representations have k6=0; tensor products of SM fields remain k6=0; therefore a field with nonzero k6 has no operator linear in that field and otherwise composed solely of SM fields",
                "scope": "representation-lattice obstruction only; additional BSM states can open decays",
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    @staticmethod
    def global_form_decay_gate(
        su3_dynkin: tuple[int, int],
        su2_dimension: int,
        hypercharge: Fraction,
    ) -> Mapping[str, Any]:
        profile = sm_gauge_global_form_profile(su3_dynkin, su2_dimension, hypercharge)
        residue = profile.get("residue_k6")
        obstructed = None if residue is None else bool(int(residue) != 0)
        payload = {
            "schema": "phi-particlespace-charge-lattice-decay-gate/v7.6",
            "owner_id": OWNER_ID,
            "coordinate": {
                "su3_dynkin": list(su3_dynkin),
                "su2_dimension": int(su2_dimension),
                "hypercharge": str(hypercharge),
            },
            "global_form_profile": profile,
            "pure_sm_linear_decay_obstructed": obstructed,
            "reason": (
                "NONZERO_K6_CHARGE_COSET_CANNOT_BE_CANCELLED_BY_SM_ONLY_FIELDS"
                if obstructed is True
                else "NO_GLOBAL_FORM_CHARGE_LATTICE_OBSTRUCTION_BY_K6_ALONE"
                if obstructed is False
                else "UNRESOLVED_NONINTEGER_6Y_NORMALIZATION"
            ),
            "additional_bsm_states_can_change_decay_conclusion": True,
            "promotion_allowed": False,
        }
        return {**payload, "digest": digest_payload(payload)}

    @staticmethod
    def d7_reference_width_gev(mass_tev: float, lambda_eff_tev: float) -> float:
        m = float(mass_tev) * 1.0e3
        lam = float(lambda_eff_tev) * 1.0e3
        if not (m > 0.0 and lam > 0.0):
            raise ValueError("mass_tev and lambda_eff_tev must be positive")
        return ELECTROWEAK_VEV_GEV**2 * m**5 / (1024.0 * math.pi**3 * lam**6)

    @classmethod
    def d7_reference_ctau_m(cls, mass_tev: float, lambda_eff_tev: float) -> float:
        return HBARC_GEV_M / cls.d7_reference_width_gev(mass_tev, lambda_eff_tev)

    @staticmethod
    def d7_reference_lambda_eff_tev(mass_tev: float, ctau_m: float) -> float:
        m = float(mass_tev) * 1.0e3
        ct = float(ctau_m)
        if not (m > 0.0 and ct > 0.0):
            raise ValueError("mass_tev and ctau_m must be positive")
        lam6 = ct * ELECTROWEAK_VEV_GEV**2 * m**5 / (HBARC_GEV_M * 1024.0 * math.pi**3)
        return lam6 ** (1.0 / 6.0) / 1.0e3

    @classmethod
    def d7_reference_point(cls, mass_tev: float, lambda_eff_tev: float) -> Mapping[str, Any]:
        width = cls.d7_reference_width_gev(mass_tev, lambda_eff_tev)
        ctau = HBARC_GEV_M / width
        payload = {
            "schema": "phi-particlespace-d7-lifetime-reference/v7.6",
            "owner_id": OWNER_ID,
            "mass_TeV": float(mass_tev),
            "Lambda_eff_TeV": float(lambda_eff_tev),
            "Gamma_ref_GeV": width,
            "ctau_ref_m": ctau,
            "claim_boundary": "REFERENCE_COORDINATE_ONLY_EXACT_WIDTH_REQUIRES_OPERATOR_TENSOR_NORMALIZATION",
            "promotion_allowed": False,
        }
        return {**payload, "digest": digest_payload(payload)}
