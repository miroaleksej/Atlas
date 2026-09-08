"""Release qualification and post-freeze evidence map for ParticleSpace dossiers v8.0."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from source.lawspace.particle_candidate_dossiers import ParticleCandidateDossierOwner
from source.lawspace.schema import digest_payload


EVIDENCE: dict[str, dict[str, Any]] = {
    "P-001": {
        "prior_art": [{"kind": "REVIEW", "title": "PDG Electroweak Model and Constraints on New Physics", "url": "https://pdg.lbl.gov/2025/reviews/rpp2025-rev-standard-model.pdf"}],
        "world_novelty_status": "KNOWN_SEQUENTIAL_FOURTH_FAMILY_CLASS",
        "postfreeze_status": "MINIMAL_SEQUENTIAL_HEAVY_CHIRAL_FAMILY_STRONGLY_EXCLUDED",
        "experimental_recast": {
            "status": "CLASS_LEVEL_EXCLUSION_SUPPORTED_NOT_A_POINTWISE_LIKELIHOOD",
            "result": "PDG review reports >5 sigma exclusion for a heavy fourth chiral family when EW precision, Higgs production and direct heavy-quark searches are combined.",
            "scope": "MINIMAL_HEAVY_SEQUENTIAL_SM_LIKE_HIGGS_MASS_BRANCH",
            "nonminimal_branch": "A different mass/Higgs completion is a separate hypothesis and must be re-evaluated rather than called an open part of minimal P-001.",
        },
        "next_action": "ARCHIVE_MINIMAL_P001_AS_STRONGLY_EXCLUDED; SPAWN_NONMINIMAL_COMPLETIONS_ONLY_AS_NEW_MODEL_GRAPHS",
    },
    "P-002": {
        "prior_art": [{"kind": "EXPERIMENT_AND_REVIEW", "title": "CMS vector-like T search B2G-24-020", "url": "https://cms-results.web.cern.ch/cms-results/public-results/publications/B2G-24-020/index.html"}],
        "world_novelty_status": "KNOWN_VECTORLIKE_TOP_PARTNER_CLASS",
        "postfreeze_status": "KNOWN_CLASS_WITH_OPEN_MODEL_DEPENDENT_PARAMETER_MANIFOLD",
        "experimental_recast": {
            "status": "CONDITIONAL_CROSS_SECTION_TIMES_BRANCHING_LIMIT",
            "benchmark_slice": {"channel": "single T production, T->tH, opposite-sign dileptons", "sqrt_s_TeV": 13, "luminosity_fb-1": 138, "sigma_times_BR_limit_pb": {"M_T_GeV_600": 2.0, "M_T_GeV_1000": 0.1}},
            "universal_mass_bound": None,
            "blocked_inputs_for_full_dossier_recast": ["production coupling/mixing", "branching fractions", "width", "acceptance for selected flavor hypothesis"],
        },
        "next_action": "BUILD_MASS_MIXING_BRANCHING_GRID_AND_CONFRONT_MULTIPLE_PAIR_AND_SINGLE_PRODUCTION_SEARCHES",
    },
    "P-003": {
        "prior_art": [{"kind": "EXPERIMENT", "title": "CMS HNL in top decays B2G-24-023", "url": "https://cms-results.web.cern.ch/cms-results/public-results/preliminary-results/B2G-24-023/index.html"}],
        "world_novelty_status": "KNOWN_HNL_TYPE_I_SEESAW_CLASS",
        "postfreeze_status": "KNOWN_CLASS_WITH_LARGE_MASS_MIXING_LIFETIME_MANIFOLD",
        "experimental_recast": {
            "status": "PARTIAL_PARAMETER_SLICE_ONLY",
            "covered_mass_GeV": [20, 100],
            "reported_sensitivity": "top->N branching of order 1e-6 to 1e-5; mixing sensitivity roughly 1e-4 to 0.1 across the targeted mass range, model dependent",
            "uncovered_dimensions": ["tau mixing", "Dirac hypotheses", "very long lifetimes", "masses outside 20-100 GeV", "multi-HNL interference"],
        },
        "next_action": "ASSEMBLE_PROMPT_AND_DISPLACED_HNL_LIKELIHOODS_IN_COMMON_mN_Ue_Umu_Utau_COORDINATES",
    },
    "P-004": {
        "prior_art": [
            {"kind": "EXPERIMENT", "title": "ATLAS doubly charged Higgs multi-lepton search", "url": "https://arxiv.org/abs/2211.07505"},
            {"kind": "CURRENT_REANALYSIS_CAVEAT", "title": "Revised exclusion limits from reanalysis of ATLAS multi-lepton search", "url": "https://arxiv.org/abs/2608.03988"},
        ],
        "world_novelty_status": "KNOWN_TYPE_II_SEESAW_SCALAR_TRIPLET_CLASS",
        "postfreeze_status": "KNOWN_CLASS_WITH_BRANCHING_AND_vDELTA_DEPENDENT_OPEN_REGIONS",
        "experimental_recast": {
            "status": "CONDITIONAL_BENCHMARK_LIMIT_WITH_CURRENT_REANALYSIS_CAVEAT",
            "atlas_published_benchmark": "1080 GeV observed lower limit for a left-right symmetric type-II benchmark under equal leptonic branching fractions",
            "nonuniversality": "does not apply to arbitrary Y_Delta/v_Delta/mass-splitting choices, especially WW-dominated or cascade regimes",
            "current_caveat": "a 2026 independent reanalysis questions the auxiliary efficiency and reports a weaker expected type-II bound around 950 GeV; do not encode 1080 GeV as a universal cell exclusion",
        },
        "next_action": "SPLIT_DOSSIER_INTO_DILEPTON_WW_AND_CASCADE_PHASES_THEN_RECAST_EACH_SEPARATELY",
    },
    "P-005": {
        "prior_art": [{"kind": "EXPERIMENT", "title": "CMS high-mass dilepton resonance search EXO-25-021", "url": "https://cms-results.web.cern.ch/cms-results/public-results/preliminary-results/EXO-25-021/index.html"}],
        "world_novelty_status": "KNOWN_ZPRIME_CLASS",
        "postfreeze_status": "KNOWN_CLASS_WITH_COUPLING_DEPENDENT_OPEN_MANIFOLD",
        "experimental_recast": {
            "status": "CONDITIONAL_BENCHMARK_LIMIT",
            "sqrt_s_TeV": 13.6,
            "luminosity_fb-1": 283,
            "benchmark_mass_limits_TeV": {"Zprime_SSM": 5.55, "Zprime_psi": 4.95},
            "generic_cell_limit": None,
            "blocked_inputs_for_generic_recast": ["quark charges/couplings", "lepton charges/couplings", "width", "invisible branching", "interference/line shape"],
        },
        "next_action": "SCAN_ANOMALY_FREE_U1PRIME_CHARGE_ASSIGNMENTS_AND_MAP_DILEPTON_DIJET_INVISIBLE_COMPLEMENTARITY",
    },
    "P-006": {
        "prior_art": [{"kind": "EXPERIMENT", "title": "CMS charged gauge boson search EXO-24-021", "url": "https://cms-results.web.cern.ch/cms-results/public-results/preliminary-results/EXO-24-021/index.html"}],
        "world_novelty_status": "KNOWN_WPRIME_CLASS",
        "postfreeze_status": "KNOWN_CLASS_WITH_UV_COMPLETION_DEPENDENT_OPEN_MANIFOLD",
        "experimental_recast": {
            "status": "CONDITIONAL_BENCHMARK_LIMIT",
            "sqrt_s_TeV": 13.6,
            "luminosity_fb-1": 62,
            "benchmark_mass_limit_TeV": {"SSM_Wprime_combined_e_mu": 5.9},
            "generic_cell_limit": None,
            "blocked_inputs_for_generic_recast": ["UV gauge origin", "quark/lepton current strengths", "right-handed neutrino spectrum", "branching fractions", "width and W-Wprime mixing"],
        },
        "next_action": "BRANCH_INTO_SSM_LIKE_AND_LEFT_RIGHT_COMPLETIONS_BEFORE_ANY_MASS_EXCLUSION_IS_ATTACHED",
    },
    "P-007": {
        "prior_art": [
            {"kind": "EXACT_REPRESENTATION_THEORY", "title": "The phenomenological cornucopia of SU(3) exotica", "url": "https://arxiv.org/abs/2110.11359", "match": "Dirac sextet fermion (6,1,Y), with dimension-5 qg operator allowing Y=1/3"},
            {"kind": "EXPERIMENT_RECAST_TARGET", "title": "CMS paired dijet resonances with b jets EXO-24-039", "url": "https://cms-results.web.cern.ch/cms-results/public-results/preliminary-results/EXO-24-039/index.html"},
        ],
        "world_novelty_status": "EXACT_REPRESENTATION_CLASS_FOUND_IN_PRIOR_ART_NOT_WORLD_NEW",
        "postfreeze_status": "KNOWN_EXACT_CLASS_WITH_DEDICATED_CURRENT_RECAST_GAP",
        "experimental_recast": {
            "status": "RECAST_BLOCKED_SIGNAL_SIMULATION_AND_ACCEPTANCE_REQUIRED",
            "relevant_signature": "QCD pair production followed by X->b g gives paired (b j)(b j) resonances when kappa_b dominates",
            "cms_result": "EXO-24-039 provides 95% CL limits on pair-produced dijet resonances with a b jet plus a light jet in each resonance; its explicit nonresonant benchmark is spin-0 RPV stop, not a color-sextet Dirac fermion",
            "cannot_transfer_stop_mass_limit": True,
            "required_inputs": ["sextet-fermion QCD pair-production cross section", "spin/color dependent acceptance", "b-flavor branching fraction", "detector efficiency", "width/lifetime from kappa_b/Lambda"],
            "lifetime_branches": ["PROMPT_PAIRED_DIJET", "DISPLACED_DECAY", "DETECTOR_STABLE_COLORED_STATE"],
        },
        "next_action": "PRIORITY_RECAST: COMPUTE_SEXTET_PAIR_CROSS_SECTION_AND_EXO-24-039_ACCEPTANCE_FOR_X_TO_BG; THEN STITCH_TO_LLP_SEARCHES_AT_SMALL_kappa/Lambda",
    },
}


def run_release_qualification(root: str | Path | None = None) -> Mapping[str, Any]:
    owner = ParticleCandidateDossierOwner()
    freeze = owner.internal_freeze()
    post = owner.attach_postfreeze_evidence(EVIDENCE)
    rows = {r["candidate_id"]: r for r in freeze["dossiers"]}

    checks: list[dict[str, Any]] = []
    def check(name: str, value: bool, detail: Any = None) -> None:
        checks.append({"check": name, "pass": bool(value), "detail": detail})

    check("SEVEN_DOSSIERS", len(rows) == 7 and set(rows) == {f"P-00{i}" for i in range(1, 8)}, sorted(rows))
    check("P001_EXACT_ANOMALY_CLOSURE", rows["P-001"]["formal_gates"]["spectrum_anomaly_closed"], rows["P-001"]["formal_gates"]["spectrum_anomaly_sum"])
    check("P002_VECTORLIKE_PAIR_ANOMALY_CLOSURE", rows["P-002"]["formal_gates"]["spectrum_anomaly_closed"], rows["P-002"]["formal_gates"]["spectrum_anomaly_sum"])
    check("P003_SELF_ANOMALY_NEUTRAL", rows["P-003"]["formal_gates"]["spectrum_anomaly_closed"], rows["P-003"]["formal_gates"]["spectrum_anomaly_sum"])
    check("P007_SEXTET_PAIR_ANOMALY_CLOSURE", rows["P-007"]["formal_gates"]["spectrum_anomaly_closed"], rows["P-007"]["formal_gates"]["spectrum_anomaly_sum"])
    check("P007_DIM5_QG_PORTAL_PRESENT", any(x.get("role") == "GAUGE_ALLOWED_CHROMOMAGNETIC_qg_PORTAL" and x.get("dimension") == 5 for x in rows["P-007"]["lagrangian"]))
    check("ALL_PROMOTION_FAIL_CLOSED", all(not r["promotion_allowed"] for r in freeze["dossiers"]) and all(not r["promotion_allowed"] for r in post["dossiers"]))
    check("POSTFREEZE_REFERENCES_EXACT_FREEZE", post["internal_freeze_digest"] == freeze["freeze_digest"], {"freeze": freeze["freeze_digest"], "post": post["internal_freeze_digest"]})
    check("LEGACY_STRING_PROVENANCE_REJECTED_BY_CENTRAL_VERIFICATION", all(
        r["postfreeze_evidence_status"] == "FAIL_CLOSED_CENTRAL_SCIENTIFIC_VERIFICATION_REQUIRED" for r in post["dossiers"]
    ))
    check("NO_UNVERIFIED_BENCHMARK_OVERTRANSFER", all(
        r["experimental_recast"]["status"] == "NOT_EVALUATED_VERIFIED_EVIDENCE_REQUIRED" for r in post["dossiers"]
    ))
    check("P007_LEGACY_PRIOR_ART_PRESERVED_ONLY_FOR_AUDIT",
          post["dossiers"][6]["legacy_unverified_postfreeze_evidence"].get("world_novelty_status") == "EXACT_REPRESENTATION_CLASS_FOUND_IN_PRIOR_ART_NOT_WORLD_NEW"
          and post["dossiers"][6]["world_novelty_status"] == "NOT_EVALUATED_VERIFIED_EVIDENCE_REQUIRED")

    passed = sum(int(c["pass"]) for c in checks)
    payload: dict[str, Any] = {
        "schema": "phi-particlespace-candidate-dossier-qualification/v8.0",
        "owner_id": owner.owner_id,
        "checks": checks,
        "passed": passed,
        "total": len(checks),
        "status": "PASS" if passed == len(checks) else "FAIL",
        "internal_freeze_digest": freeze["freeze_digest"],
        "postfreeze_receipt_digest": post["receipt_digest"],
        "blind_novelty_benchmark": False,
        "blind_novelty_boundary": "P-007 prior art was inspected before the batch v7.4 artifact freeze; this release qualifies dossier separation and fail-closed recast, not blind novelty discovery.",
    }
    payload["receipt_digest"] = digest_payload(payload)

    if root is not None:
        root = Path(root)
        reports = root / "reports"; reports.mkdir(parents=True, exist_ok=True)
        data = root / "data" / "particles"; data.mkdir(parents=True, exist_ok=True)
        (reports / "particle_candidate_dossiers_internal_freeze_v7_4.json").write_text(json.dumps(freeze, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (reports / "particle_candidate_dossiers_postfreeze_v7_4.json").write_text(json.dumps(post, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (reports / "particle_candidate_dossier_qualification_v7_4.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (data / "particle_candidate_dossiers_v7_4.json").write_text(json.dumps(post, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    import sys
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    print(json.dumps(run_release_qualification(root), indent=2, sort_keys=True))
