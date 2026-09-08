"""First-class ParticleSpace candidate dossiers for Phi-LawSpace v8.0.

This owner does *research dossier assembly*, not scientific promotion.  The
P-001...P-007 set is retained as a calibration/phenomenology qualification set;
it is not a blind discovery selection and must never be used as evidence that
ParticleSpace autonomously ranked these seven hypotheses.  It turns the retained
open-world ParticleSpace examples into explicit model graphs with
completion requirements, interaction operators, production/decay routes,
lifetime scalings and parameter manifolds.  External literature/experimental
evidence is attached only in a separate post-freeze step.

Scientific promotion remains exclusively owned by ScientificPromotionCore.
"""
from __future__ import annotations

from fractions import Fraction
from functools import lru_cache
from typing import Any, Mapping, Sequence

from .particle_space import ParticleSpaceOwner
from .schema import digest_payload
from .scientific_verification import ScientificVerificationCore

SCHEMA = "phi-particlespace-candidate-dossiers/v8.0"
OWNER_ID = "PARTICLESPACE-CANDIDATE-DOSSIERS/8.0.0"

_ANOMALY_KEYS = ("SU3_CUBIC", "SU3_SQ_U1", "SU2_SQ_U1", "U1_CUBIC", "GRAV_SQ_U1")


def _frac(text: str | int | float) -> Fraction:
    return Fraction(str(text))


@lru_cache(maxsize=1)
def _cell_index() -> dict[str, dict[str, Any]]:
    return {r["particle_id"]: r for r in ParticleSpaceOwner().enumerate_cells()}


def _sum_anomalies(cells: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    total = {k: Fraction(0) for k in _ANOMALY_KEYS}
    witten = 0
    for row in cells:
        gate = row["anomaly_gate"]
        if row["coordinate"]["spin"] != "1/2":
            continue
        for key in _ANOMALY_KEYS:
            total[key] += _frac(gate["local_contribution"][key])
        witten = (witten + int(gate["witten_mod2"])) % 2
    out = {k: str(v) for k, v in total.items()}
    out["WITTEN_MOD2"] = str(witten)
    return out


def _zero_anomaly(summary: Mapping[str, str]) -> bool:
    return all(_frac(summary[k]) == 0 for k in _ANOMALY_KEYS) and int(summary["WITTEN_MOD2"]) == 0


def _compatibility_summary(cells: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    forms = ("Z1", "Z2", "Z3", "Z6")
    return {
        "cell_k6": {r["particle_id"]: r["global_form_axis"]["residue_k6"] for r in cells},
        "all_cells_compatible": {
            form: all(r["global_form_axis"]["branches"][form]["compatible"] is True for r in cells)
            for form in forms
        },
        "interpretation": "CELL_PROPERTY_ONLY_GLOBAL_FORM_REMAINS_MODEL_LEVEL_ASSUMPTION",
    }


def _base(candidate_id: str, title: str, cell_ids: Sequence[str], *, hypothesis_unit: str) -> dict[str, Any]:
    idx = _cell_index()
    cells = [idx[p] for p in cell_ids]
    anomaly = _sum_anomalies(cells)
    payload = {
        "schema": SCHEMA,
        "owner_id": OWNER_ID,
        "candidate_id": candidate_id,
        "title": title,
        "hypothesis_unit": hypothesis_unit,
        "cell_ids": list(cell_ids),
        "cell_coordinates": {r["particle_id"]: r["coordinate"] for r in cells},
        "formal_gates": {
            "all_cells_exist": True,
            "spectrum_anomaly_sum": anomaly,
            "spectrum_anomaly_closed": _zero_anomaly(anomaly),
            "global_form_compatibility": _compatibility_summary(cells),
        },
        "promotion_allowed": False,
        "scientific_promotion_owner": "SCIENTIFIC-PROMOTION-CORE/9.1.0",
        "prior_art_status": "NOT_EVALUATED_IN_INTERNAL_FREEZE",
        "experimental_recast_status": "NOT_EVALUATED_IN_INTERNAL_FREEZE",
    }
    return payload


def _p001() -> dict[str, Any]:
    d = _base(
        "P-001", "Sequential fourth chiral family", ["P-10738", "P-11884", "P-11920", "P-09244", "P-09004"],
        hypothesis_unit="FIVE_CELL_CHIRAL_SPECTRUM_COPY4",
    )
    d.update({
        "completion": {
            "kind": "COMPLETE_SM_LIKE_CHIRAL_GENERATION",
            "fields": ["Q4", "u4^c", "d4^c", "L4", "e4^c"],
            "gauge_anomaly_closure": "EXACT_WITHIN_FIVE_CELL_SPECTRUM",
            "mass_origin_requirement": "MINIMAL_SEQUENTIAL_BRANCH_REQUIRES_EWSB_YUKAWA_MASSES",
        },
        "lagrangian": [
            {"operator": "y_u4 Q4 H u4^c + h.c.", "dimension": 4, "role": "UP_TYPE_MASS"},
            {"operator": "y_d4 Q4 Hdag d4^c + h.c.", "dimension": 4, "role": "DOWN_TYPE_MASS"},
            {"operator": "y_e4 L4 Hdag e4^c + h.c.", "dimension": 4, "role": "CHARGED_LEPTON_MASS"},
            {"operator": "neutrino mass term requires additional nu4^c or higher-dimensional completion", "dimension": None, "role": "NEUTRINO_COMPLETION"},
        ],
        "decays": {
            "quark_routes": ["t' -> W b / Z t / h t (mixing dependent)", "b' -> W t / Z b / h b (mixing dependent)"],
            "lepton_routes": ["ell4 -> W nu / Z ell / h ell (mixing dependent)", "nu4 routes depend on Dirac/Majorana completion"],
            "stable_limit": "POSSIBLE_ONLY_IF_MIXING_SYMMETRY_SUPPRESSES_DECAYS; NOT_MINIMAL_ASSUMPTION",
        },
        "production": ["QCD_PAIR_PRODUCTION_FOR_tprime_bprime", "DRELL_YAN_EW_PRODUCTION_FOR_HEAVY_LEPTONS", "MIXING_DEPENDENT_SINGLE_PRODUCTION"],
        "lifetime": {
            "prompt_scaling": "Gamma_weak ~ G_F * |V_or_U|^2 * M^3 for M >> mW, up to channel/phase-space factors",
            "long_lived_regime": "small inter-generation mixing",
        },
        "parameter_manifold": ["m_tprime", "m_bprime", "m_ell4", "m_nu4", "V_4i", "U_4i", "Dirac_or_Majorana_nu4", "Higgs_sector_completion"],
        "internal_status": "FORMALLY_CLOSED_MINIMAL_SEQUENTIAL_HYPOTHESIS_READY_FOR_POSTFREEZE_CONSTRAINTS",
    })
    return d


def _p002() -> dict[str, Any]:
    d = _base(
        "P-002", "Vector-like top-singlet fermion pair", ["P-10462", "P-11884"],
        hypothesis_unit="CONJUGATE_FERMION_PAIR",
    )
    d.update({
        "completion": {
            "kind": "VECTORLIKE_DIRAC_PAIR",
            "representation": "(3,1,2/3) + (3bar,1,-2/3)",
            "gauge_anomaly_closure": "PAIRWISE_EXACT",
        },
        "lagrangian": [
            {"operator": "M_T T T^c + h.c.", "dimension": 3, "role": "GAUGE_INVARIANT_VECTORLIKE_MASS"},
            {"operator": "lambda_i Q_i H T^c + h.c.", "dimension": 4, "role": "SM_MIXING_PORTAL"},
            {"operator": "mu_i T u_i^c + h.c.", "dimension": 3, "role": "ALLOWED_SINGLET_MASS_MIXING"},
        ],
        "decays": {"routes": ["T -> W b_i", "T -> Z u_i", "T -> h u_i"], "flavor_pattern": "set by mixing matrices"},
        "production": ["QCD_PAIR_PRODUCTION_COUPLING_INDEPENDENT_AT_LEADING_ORDER", "ELECTROWEAK_SINGLE_PRODUCTION_MIXING_DEPENDENT"],
        "lifetime": {"scaling": "Gamma ~ G_F * theta^2 * M_T^3 for heavy mixed T, up to channel factors", "long_lived_regime": "theta -> 0"},
        "parameter_manifold": ["M_T", "lambda_i", "mu_i", "left_right_mixing_angles", "branching_Wb", "branching_Zt", "branching_ht", "total_width"],
        "internal_status": "ANOMALY_FREE_VECTORLIKE_PAIR_WITH_RENORMALIZABLE_SM_PORTALS",
    })
    return d


def _p003() -> dict[str, Any]:
    d = _base("P-003", "Gauge-singlet neutral fermion / HNL", ["P-08965"], hypothesis_unit="SINGLE_SM_GAUGE_SINGLET_PLUS_PORTAL")
    d.update({
        "family_cells": [f"P-{n:05d}" for n in range(8965, 8971)],
        "completion": {"kind": "TYPE_I_SEESAW_OR_GENERIC_HNL", "sm_representation": "(1,1,0)", "self_anomaly_neutral": True},
        "lagrangian": [
            {"operator": "(1/2) M_N N N + h.c.", "dimension": 3, "role": "MAJORANA_MASS_IF_ALLOWED"},
            {"operator": "y_alpha L_alpha H N + h.c.", "dimension": 4, "role": "NEUTRINO_YUKAWA_PORTAL"},
        ],
        "derived_relations": ["m_D = y v/sqrt(2)", "Theta approximately m_D M_N^{-1} in the seesaw limit"],
        "decays": {
            "below_W": ["N -> l jj", "N -> nu jj", "N -> l l nu", "meson channels where kinematically allowed"],
            "above_W": ["N -> l W", "N -> nu Z", "N -> nu h"],
        },
        "production": ["W/Z mediated production through active-sterile mixing", "top-decay production when kinematically allowed", "meson/tau production at lower masses"],
        "lifetime": {
            "below_W_scaling": "Gamma ~ G_F^2 * m_N^5 * U2 /(96*pi^3) up to flavor/channel coefficients",
            "above_W_scaling": "Gamma ~ G_F * m_N^3 * U2 up to electroweak/channel factors",
            "U2": "sum_alpha |U_alphaN|^2",
        },
        "parameter_manifold": ["m_N", "|UeN|^2", "|UmuN|^2", "|UtauN|^2", "Majorana_or_Dirac", "CP_phases", "lifetime"],
        "internal_status": "SELF_ANOMALY_NEUTRAL_RENORMALIZABLE_PORTAL_HYPOTHESIS",
    })
    return d


def _p004() -> dict[str, Any]:
    d = _base("P-004", "Complex electroweak scalar triplet", ["P-00769"], hypothesis_unit="SINGLE_COMPLEX_SCALAR_MULTIPLET")
    d.update({
        "completion": {"kind": "TYPE_II_SEESAW_REPRESENTATIVE", "representation": "(1,3,1)", "components": ["Delta0", "Delta+", "Delta++"]},
        "lagrangian": [
            {"operator": "M_Delta^2 Tr(Delta^dag Delta)", "dimension": 2, "role": "MASS"},
            {"operator": "(1/2) Y_Delta^{ab} L_a^T C i sigma2 Delta L_b + h.c.", "dimension": 4, "role": "LEPTON_YUKAWA"},
            {"operator": "mu H^T i sigma2 Delta^dag H + h.c.", "dimension": 3, "role": "HIGGS_TRIPLET_PORTAL"},
            {"operator": "quartic H/Delta potential", "dimension": 4, "role": "MASS_SPLITTING_AND_VACUUM"},
        ],
        "derived_relations": ["v_Delta proportional to mu v^2/M_Delta^2 in the decoupling limit", "m_nu proportional to Y_Delta v_Delta"],
        "decays": {
            "Delta_pp": ["l+ l+", "W+ W+"],
            "Delta_p": ["l+ nu", "W+ Z", "W+ h", "cascade modes if splittings permit"],
            "branching_control": "competition between Y_Delta, v_Delta and scalar mass splittings",
        },
        "production": ["DRELL_YAN_PAIR_PRODUCTION", "ASSOCIATED_EW_PRODUCTION", "VBF_ENHANCED_WHEN_vDelta_NONNEGLIGIBLE"],
        "lifetime": {"leptonic_scaling": "Gamma_ll ~ |Y_Delta|^2 M_Delta", "diboson_scaling": "Gamma_WW ~ g^4 v_Delta^2 M_Delta^3/m_W^4, up to factors"},
        "parameter_manifold": ["M_Delta", "mass_splittings", "v_Delta", "mu", "Y_Delta_matrix", "quartic_couplings", "branching_Delta_pp_ll", "branching_Delta_pp_WW"],
        "internal_status": "RENORMALIZABLE_TYPE_II_SEESAW_COMPLETION_AVAILABLE",
    })
    return d


def _p005() -> dict[str, Any]:
    d = _base("P-005", "Additional neutral spin-1 singlet", ["P-17786"], hypothesis_unit="VECTOR_CELL_REQUIRING_UV_GAUGE_OR_COMPOSITE_COMPLETION")
    d.update({
        "completion": {"kind": "GENERIC_ZPRIME", "requirement": "isolated Proca cell is not by itself a UV-complete gauge theory", "allowed_origins": ["ANOMALY_FREE_U1PRIME_GAUGE_BOSON", "STUECKELBERG_OR_HIGGS_MASS", "COMPOSITE_VECTOR_EFFECTIVE_THEORY"]},
        "lagrangian": [
            {"operator": "-1/4 X_munu X^munu - (epsilon/2) B_munu X^munu", "dimension": 4, "role": "KINETIC_AND_KINETIC_MIXING"},
            {"operator": "(1/2) M_X^2 X_mu X^mu", "dimension": 2, "role": "EFFECTIVE_MASS_TERM_REQUIRES_ORIGIN"},
            {"operator": "g_X X_mu J_X^mu", "dimension": 4, "role": "VISIBLE_OR_HIDDEN_CURRENT_PORTAL"},
        ],
        "decays": {"routes": ["l+l-", "qqbar/dijet", "ttbar", "nu nu/invisible", "BSM hidden states"], "availability": "coupling dependent"},
        "production": ["DRELL_YAN_IF_QUARK_COUPLING", "VECTOR_BOSON_OR_ASSOCIATED_PRODUCTION_MODEL_DEPENDENT", "PORTAL_PRODUCTION_IF_KINETIC_MIXING"],
        "lifetime": {"scaling": "Gamma_f approximately proportional to N_c g_f^2 M_X for light fermions", "long_lived_regime": "all visible couplings very small and hidden decays absent"},
        "parameter_manifold": ["M_X", "epsilon", "g_q", "g_e", "g_mu", "g_tau", "g_nu", "g_dark", "charge_assignment", "anomaly_completion", "total_width"],
        "internal_status": "CELL_REQUIRES_MODEL_LEVEL_GAUGE_OR_COMPOSITE_COMPLETION_BEFORE_PHENOMENOLOGY",
    })
    return d


def _p006() -> dict[str, Any]:
    d = _base("P-006", "Additional charged spin-1 singlet", ["P-17821"], hypothesis_unit="CHARGED_VECTOR_CELL_REQUIRING_UV_COMPLETION")
    d.update({
        "completion": {"kind": "GENERIC_WPRIME", "representation": "(1,1,1) with Q=+1", "allowed_origins": ["ENLARGED_GAUGE_GROUP_SU2R_OR_OTHER", "COMPOSITE_VECTOR", "EFFECTIVE_PROCA_WITH_CUTOFF"]},
        "lagrangian": [
            {"operator": "(g_R/sqrt(2)) W_R^+_mu (ubar_R gamma^mu V_R d_R + Nbar_R gamma^mu l_R) + h.c.", "dimension": 4, "role": "LEFT_RIGHT_BENCHMARK_CURRENT"},
            {"operator": "W-Wprime mixing terms", "dimension": None, "role": "MODEL_DEPENDENT_EWSB_MIXING"},
        ],
        "decays": {"routes": ["l nu", "t b", "q qprime", "l N in left-right completions", "WZ/Wh if mixing permits"]},
        "production": ["q qprime DRELL_YAN_LIKE_PRODUCTION_IF_QUARK_CURRENT", "VBF_OR_ASSOCIATED_PRODUCTION_MODEL_DEPENDENT"],
        "lifetime": {"scaling": "Gamma ~ g_prime^2 M_Wprime times open-channel multiplicities", "long_lived_regime": "requires strongly suppressed currents or exotic kinematics"},
        "parameter_manifold": ["M_Wprime", "g_qprime", "g_lprime", "V_R", "W-Wprime_mixing", "m_N", "branching_lnu", "branching_tb", "branching_lN", "total_width", "UV_origin"],
        "internal_status": "CHARGED_VECTOR_REQUIRES_EXPLICIT_DYNAMICAL_ORIGIN",
    })
    return d


def _p007() -> dict[str, Any]:
    d = _base("P-007", "Vector-like color-sextet Dirac fermion", ["P-13387", "P-14833"], hypothesis_unit="CONJUGATE_EXOTIC_COLOR_FERMION_PAIR")
    d.update({
        "completion": {"kind": "VECTORLIKE_DIRAC_SEXTET_PAIR", "representation": "(6,1,1/3) + (6bar,1,-1/3)", "gauge_anomaly_closure": "PAIRWISE_EXACT"},
        "lagrangian": [
            {"operator": "M_X X Xbar + h.c.", "dimension": 3, "role": "VECTORLIKE_MASS"},
            {"operator": "(kappa_q/Lambda) J^{sia} (q_R^c sigma^{mu nu} X_s) G^a_{mu nu} + h.c.", "dimension": 5, "role": "GAUGE_ALLOWED_CHROMOMAGNETIC_qg_PORTAL", "internal_derivation_status": "REPRESENTATION_AND_HYPERCHARGE_ALLOW_DOWN_TYPE_qg_PORTAL"},
        ],
        "decays": {"prompt_route": "X -> q g through dimension-5 dipole", "flavor_choices": ["d g", "s g", "b g"], "higher_routes": "q g gamma/Z and multi-body channels can appear at higher order/operator dimension"},
        "production": ["QCD_PAIR_PRODUCTION_FIXED_BY_COLOR_REPRESENTATION_AND_MASS", "qg_SINGLE_PRODUCTION_PROPORTIONAL_TO_kappa^2/Lambda^2"],
        "lifetime": {"scaling": "Gamma_qg ~ |kappa_q|^2 M_X^3/Lambda^2 up to color/normalization factors", "prompt_displaced_stable_transition": "controlled primarily by |kappa|/Lambda and flavor"},
        "parameter_manifold": ["M_X", "Lambda", "kappa_d", "kappa_s", "kappa_b", "CP_phases", "higher_dim_operator_coefficients", "lifetime"],
        "internal_status": "ANOMALY_FREE_EXOTIC_COLOR_PAIR_WITH_DIM5_qg_PORTAL",
    })
    return d


_BUILDERS = (_p001, _p002, _p003, _p004, _p005, _p006, _p007)


class ParticleCandidateDossierOwner:
    owner_id = OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "scope": "CALIBRATION_AND_PHENOMENOLOGY_DOSSIERS_FOR_P001_TO_P007",
            "selection_origin": "HARDCODED_CALIBRATION_SET_NOT_BLIND_DISCOVERY_RANKING",
            "blind_discovery_evidence": False,
            "pipeline": ["LAGRANGIAN_COMPLETION", "DECAY_OPERATORS", "PRODUCTION", "LIFETIME", "PARAMETER_MANIFOLD", "INTERNAL_FREEZE", "POSTFREEZE_PRIOR_ART", "EXPERIMENTAL_RECAST"],
            "hard_rules": {
                "census_cell_is_discovery": False,
                "dossier_is_scientific_promotion": False,
                "external_evidence_changes_internal_freeze": False,
                "benchmark_limit_transfers_to_generic_cell_without_model_match": False,
                "blocked_recast_must_name_missing_inputs": True,
                "scientific_promotion_owner": "SCIENTIFIC-PROMOTION-CORE/9.1.0",
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    def build_internal_dossiers(self) -> list[dict[str, Any]]:
        rows = []
        for fn in _BUILDERS:
            row = fn()
            row["dossier_digest"] = digest_payload(row)
            rows.append(row)
        return rows

    def internal_freeze(self) -> Mapping[str, Any]:
        rows = self.build_internal_dossiers()
        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "candidate_ids": [r["candidate_id"] for r in rows],
            "dossiers": rows,
            "external_evidence_inputs": [],
            "world_novelty_claim": False,
            "promotion_allowed": False,
        }
        return {**payload, "freeze_digest": digest_payload(payload)}

    def attach_postfreeze_evidence(self, evidence: Mapping[str, Mapping[str, Any]]) -> Mapping[str, Any]:
        """Attach only centrally verified post-freeze evidence.

        A URL/title/result mapping is untrusted input.  The dossier owner recomputes
        ScientificVerificationCore from the raw bundle; a serialized verification
        receipt is never accepted as authorization.  Legacy evidence remains visible
        for audit but cannot change active scientific status.
        """
        freeze = self.internal_freeze()
        out = []
        for row in freeze["dossiers"]:
            cid = row["candidate_id"]
            ev = dict(evidence.get(cid, {}))
            bundle = dict(ev.pop("_scientific_verification_bundle", {}) or {})
            verification = ScientificVerificationCore().verify_bundle(bundle)
            declared = dict(bundle.get("claim_values", {}))
            expected = {
                "postfreeze_status": ev.get("postfreeze_status", "INSUFFICIENT"),
                "world_novelty_status": ev.get("world_novelty_status", "INSUFFICIENT"),
                "experimental_recast_status": dict(ev.get("experimental_recast", {}) or {}).get("status", "INSUFFICIENT"),
            }
            mismatch = [k for k, v in expected.items() if digest_payload(declared.get(k, "INSUFFICIENT")) != digest_payload(v)]
            verified = (
                verification.get("scientific_candidate_allowed") is True
                and str(bundle.get("proposer_owner", "")) == OWNER_ID
                and not mismatch
            )
            merged = {**row}
            merged["legacy_unverified_postfreeze_evidence"] = ev if ev else {}
            merged["scientific_verification"] = verification
            if verified:
                sanitized = dict(verification.get("sanitized_claim_values", {}))
                merged["postfreeze_status"] = sanitized.get("postfreeze_status", "INSUFFICIENT")
                merged["world_novelty_status"] = sanitized.get("world_novelty_status", "INSUFFICIENT")
                recast = dict(ev.get("experimental_recast", {}) or {})
                recast["status"] = sanitized.get("experimental_recast_status", "INSUFFICIENT")
                merged["experimental_recast"] = recast
                merged["postfreeze_evidence_status"] = "VERIFIED_WORLD_EVIDENCE_ATTACHED"
            else:
                merged["postfreeze_status"] = "UNVERIFIED_EVIDENCE_REJECTED"
                merged["world_novelty_status"] = "NOT_EVALUATED_VERIFIED_EVIDENCE_REQUIRED"
                merged["experimental_recast"] = {"status": "NOT_EVALUATED_VERIFIED_EVIDENCE_REQUIRED"}
                merged["postfreeze_evidence_status"] = "FAIL_CLOSED_CENTRAL_SCIENTIFIC_VERIFICATION_REQUIRED"
            merged["verification_bundle_mismatch_fields"] = mismatch
            merged["promotion_allowed"] = False
            merged["postfreeze_digest"] = digest_payload(merged)
            out.append(merged)
        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "internal_freeze_digest": freeze["freeze_digest"],
            "dossiers": out,
            "promotion_allowed": False,
            "claim_boundary": "RESEARCH_DOSSIERS_NOT_PARTICLE_DISCOVERIES_AND_UNVERIFIED_POSTFREEZE_EVIDENCE_CANNOT_CHANGE_ACTIVE_STATUS",
        }
        return {**payload, "receipt_digest": digest_payload(payload)}

    def get(self, candidate_id: str) -> Mapping[str, Any]:
        for row in self.build_internal_dossiers():
            if row["candidate_id"] == candidate_id:
                return row
        raise KeyError(candidate_id)
