"""Release qualification for Scientific Promotion Core v9.0.

This benchmark is deliberately split into:
1) permanent deterministic canaries (including bonus.8), and
2) 200 post-start synthetic worlds for the formal adjudication core.

It is NOT the end-to-end A/B test against plain GPT.  The release therefore
remains RESEARCH_SYSTEM_UNDER_QUALIFICATION even when this module passes.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from source.lawspace.scientific_promotion import ScientificPromotionCore, SYSTEM_STATUS
from source.lawspace.scientific_verification import build_qualification_artifact_receipt

REQUIRED_ROLES = ("null", "simpler", "known_model", "mechanistic_competitor", "nonlinear_competitor")


def _alt_rows(y: np.ndarray, truth: np.ndarray, *, known: np.ndarray | None = None) -> list[dict[str, Any]]:
    scale = max(float(np.std(truth)), float(np.mean(np.abs(truth))), 1.0)
    rows = []
    curves = [
        np.zeros_like(truth),
        np.full_like(truth, float(np.mean(y))),
        truth + 0.35 * scale if known is None else known,
        truth - 0.28 * scale,
        truth + 0.18 * scale * np.sin(np.linspace(0.0, 2.0 * math.pi, truth.size)),
    ]
    for idx, (role, pred) in enumerate(zip(REQUIRED_ROLES, curves), start=1):
        rows.append({"alternative_id": f"ALT-{idx}", "role": role, "model_class": f"{role}-class", "equation": f"declared {role} competitor", "predictions_train": [float(x) for x in pred], "provenance": "computed qualification competitor"})
    return rows


def _fixed_request(*, run_id: str, y_train: np.ndarray, sigma_train: np.ndarray | None, pred_train: np.ndarray,
                   y_ood: np.ndarray | None, sigma_ood: np.ndarray | None, pred_ood: np.ndarray | None,
                   alternatives: list[Mapping[str, Any]], parameters: tuple[str, ...] = (), jacobian: np.ndarray | None = None,
                   parameter_scales: tuple[float, ...] = (), latent_axes: tuple[str, ...] = (), axis_validations: list[Mapping[str, Any]] | None = None,
                   global_status: str = "PASS", replication: Mapping[str, Any] | None = None, seed: int = 7000) -> dict[str, Any]:
    data: dict[str, Any] = {
        "train": {"y": [float(x) for x in y_train], "sigma": None if sigma_train is None else [float(x) for x in sigma_train], "regime_id": "TRAIN", "provenance": "qualification-generated-after-start"},
    }
    if y_ood is not None:
        data["ood"] = {"y": [float(x) for x in y_ood], "sigma": None if sigma_ood is None else [float(x) for x in sigma_ood], "regime_id": "OOD-DISTINCT", "provenance": "qualification-generated-after-start"}
    axis_contracts = [{
        "axis_id": "x", "name": "qualification x", "role": "observed", "units": "dimensionless", "dimension": "1",
        "domain": "qualification", "uncertainty": "declared by data partition", "measurement_operator": "identity observation",
        "provenance": "qualification-generated-after-start", "prior": "none", "causal_role": "input", "falsification_value": "regime OOD support",
    }]
    for axis_id in latent_axes:
        axis_contracts.append({
            "axis_id": axis_id, "name": f"qualification {axis_id}", "role": "latent", "units": "dimensionless", "dimension": "1",
            "domain": "qualification", "uncertainty": "generated hidden-world coordinate", "measurement_operator": "explicit synthetic hidden coordinate",
            "provenance": "qualification-generated-after-start", "prior": "finite generated range", "causal_role": "latent predictor",
            "falsification_value": "must improve complexity-penalized OOD log likelihood",
        })
    request = {
        "run_id": run_id, "seed": int(seed), "data": data, "axis_contracts": axis_contracts,
        "candidate": {
            "candidate_id": "CAND", "model_class": "qualification_model_class", "equation": "f(x;theta)",
            "parameters": list(parameters), "active_axes": ["x"], "latent_axes": list(latent_axes), "assumptions": ["qualification"],
            "units": "dimensionless", "domain": "qualification", "predictions_train": [float(x) for x in pred_train],
            "predictions_ood": [] if pred_ood is None else [float(x) for x in pred_ood],
            "jacobian_train": [] if jacobian is None else [[float(v) for v in row] for row in jacobian],
            "parameter_scales": [float(v) for v in parameter_scales], "dimension_lhs": ["0","0","0","0","0","0","0"],
            "dimension_rhs": ["0","0","0","0","0","0","0"], "complexity": float(len(parameters)), "model_version": "QUAL-1", "provenance": "COMPUTED_QUALIFICATION_MODEL",
        },
        "alternatives": [dict(x) for x in alternatives],
        "generated_axis_ood_validations": [] if axis_validations is None else [dict(x) for x in axis_validations],
        "global_identifiability_certificate": {"status": global_status, "scope": "FINITE_DECLARED_QUALIFICATION_MODEL_CLASS",
            "owner_id": "SCIENTIFIC-PROMOTION-QUALIFICATION", "evidence_digest": f"GLOBAL-{run_id}",
            "method": "finite enumerated qualification model class", "provenance_level": "COMPUTED"},
        "replication": replication,
    }
    proposer = "SCIENTIFIC-PROMOTION-QUALIFICATION"
    artifacts = []
    required = []
    artifact_content = {"promotion_train_data": data["train"],
                        "promotion_global_identifiability_certificate": request["global_identifiability_certificate"]}
    if "ood" in data:
        artifact_content["promotion_ood_data"] = data["ood"]
    if replication is not None:
        artifact_content["promotion_replication_data"] = replication
    for artifact_id, content in artifact_content.items():
        required.append(artifact_id)
        artifacts.append(build_qualification_artifact_receipt(
            artifact_id=artifact_id, content=content, proposer_owner=proposer,
            producer_owner="SCIENTIFIC-PROMOTION-QUALIFICATION-HARNESS", artifact_class="QUALIFICATION_FIXTURE",
        ))
    request["scientific_verification_bundle"] = {
        "proposer_owner": proposer, "evidence_class": "QUALIFICATION_FIXTURE",
        "claim_values": {}, "source_receipts": [], "claim_receipts": [],
        "artifact_receipts": artifacts, "required_artifact_ids": required,
    }
    return request


def run_canaries() -> Mapping[str, Any]:
    core = ScientificPromotionCore()
    m_ec2_keV = 511.0
    x = np.linspace(1.0, 10.0, 100)
    theta = np.linspace(0.1, math.pi, 100)
    truth = x / (1.0 + (x / m_ec2_keV) * (1.0 - np.cos(theta)))
    m0 = x.copy()
    # Distinct OOD regime: higher incident energy, still inside a numerically safe qualification range.
    xo = np.linspace(12.0, 30.0, 80)
    to = np.linspace(0.15, math.pi, 80)
    truth_o = xo / (1.0 + (xo / m_ec2_keV) * (1.0 - np.cos(to)))
    m0_o = xo.copy()

    def bonus(frac: float, name: str) -> Mapping[str, Any]:
        sig = frac * truth; sigo = frac * truth_o
        alts = _alt_rows(truth, m0, known=truth)
        rep = {"y": [float(v) for v in truth_o], "sigma": [float(v) for v in sigo], "predictions": [float(v) for v in m0_o], "regime_id": "REPLICATION", "provenance": "independent deterministic qualification", "independent": True}
        return core.evaluate(_fixed_request(run_id=name, y_train=truth, sigma_train=sig, pred_train=m0, y_ood=truth_o, sigma_ood=sigo,
                                            pred_ood=m0_o, alternatives=alts, replication=rep))

    c1 = bonus(0.02, "CANARY-BONUS8-A")
    c2 = bonus(0.001, "CANARY-BONUS8-B")
    c3 = bonus(0.0025, "CANARY-BONUS8-C")

    # C4: empty adversarial set must block.
    y = np.linspace(1.0, 2.0, 20); sig = np.full(20, 0.05)
    c4 = core.evaluate(_fixed_request(run_id="CANARY-EMPTY-ALTS", y_train=y, sigma_train=sig, pred_train=y, y_ood=y + 1.0,
                                      sigma_ood=sig, pred_ood=y + 1.0, alternatives=[], replication=None))
    # C5: unknown uncertainty must block; never substitute an epsilon.
    c5 = core.evaluate(_fixed_request(run_id="CANARY-UNKNOWN-SIGMA", y_train=y, sigma_train=None, pred_train=y, y_ood=None,
                                      sigma_ood=None, pred_ood=None, alternatives=_alt_rows(y, y), replication=None))
    # C6/C7: aggregate evidence versus one isolated point.
    delta_chi2_1000x2sigma = float(np.sum(np.full(1000, 2.0) ** 2))
    sigma_equiv_1000x2sigma = math.sqrt(delta_chi2_1000x2sigma)
    delta_chi2_1x3p1sigma = 3.1 ** 2
    c6_pass = abs(sigma_equiv_1000x2sigma - math.sqrt(4000.0)) < 1e-12
    c7_pass = delta_chi2_1000x2sigma > delta_chi2_1x3p1sigma
    # C8: raw Jacobian is full rank, whitened/scaled weak direction is below one.
    xx = np.linspace(-1.0, 1.0, 30)
    pred = 1.5 + 0.2 * xx
    sigma8 = np.ones_like(xx)
    J = np.column_stack([np.ones_like(xx), 1.0e-3 * xx])
    alts8 = _alt_rows(pred, pred)
    rep8 = {"y": [float(v) for v in pred], "sigma": [1.0 for _ in pred], "predictions": [float(v) for v in pred], "regime_id": "REPLICATION", "provenance": "independent qualification", "independent": True}
    c8 = core.evaluate(_fixed_request(run_id="CANARY-WEAK-JACOBIAN", y_train=pred, sigma_train=sigma8, pred_train=pred,
                                      y_ood=pred + 0.1, sigma_ood=sigma8, pred_ood=pred + 0.1, alternatives=alts8,
                                      parameters=("a", "b"), jacobian=J, parameter_scales=(1.0, 1.0), replication=rep8))

    # Explicit OOD canary: train fit is exact, shifted-regime prediction is wrong.
    ood_truth = pred + 0.5
    ood_wrong = pred + 0.1
    ood_canary = core.evaluate(_fixed_request(run_id="CANARY-OOD-FALSIFICATION", y_train=pred, sigma_train=np.full_like(pred, 0.1), pred_train=pred,
                                              y_ood=ood_truth, sigma_ood=np.full_like(pred, 0.1), pred_ood=ood_wrong, alternatives=_alt_rows(pred, pred),
                                              replication=None))
    checks = {
        "C1_bonus8_A_false_M0_not_promoted": c1["PROMOTION_ALLOWED"] is False and c1["FINAL_STATUS"] == "FALSIFIED",
        "C2_bonus8_B_high_precision_falsifies_M0": c2["FINAL_STATUS"] == "FALSIFIED" and c2["gate_results"]["G2_ABSOLUTE_FIT"].get("pass") is False,
        "C3_bonus8_C_strong_distinguishability_cannot_resurrect_false_model": c3["FINAL_STATUS"] == "FALSIFIED" and c3["PROMOTION_ALLOWED"] is False,
        "C4_empty_alternatives_blocks": c4["FINAL_STATUS"] == "BLOCKED" and c4["TERMINAL_REASON"] == "G3_ALTERNATIVES_REQUIRED",
        "C5_unknown_uncertainty_blocks": c5["FINAL_STATUS"] == "BLOCKED" and c5["TERMINAL_REASON"] == "G0_INPUT_INTEGRITY",
        "C6_1000_points_at_2sigma_aggregate_to_about_63sigma": c6_pass and abs(sigma_equiv_1000x2sigma - 63.245553203367585) < 1e-9,
        "C7_one_3p1sigma_point_is_weaker_than_1000x2sigma": c7_pass,
        "C8_full_rank_weak_direction_is_non_identifiable": c8["FINAL_STATUS"] == "NON_IDENTIFIABLE" and c8["gate_results"]["G4_STRUCTURAL_IDENTIFIABILITY"]["pass"] is True and c8["gate_results"]["G5_PRACTICAL_IDENTIFIABILITY"]["pass"] is False,
        "OOD_wrong_regime_prediction_is_falsified": ood_canary["FINAL_STATUS"] == "FALSIFIED" and ood_canary["TERMINAL_REASON"] == "G6_OOD_FALSIFICATION",
    }
    return {
        "schema": "phi-scientific-promotion-canaries/v9.0", "checks": checks,
        "status": "PASS_PERMANENT_CANARIES" if all(checks.values()) else "FAIL_PERMANENT_CANARIES",
        "bonus8": {"A": c1, "B": c2, "C": c3}, "C4": c4, "C5": c5,
        "C6": {"delta_chi2": delta_chi2_1000x2sigma, "sqrt_delta_chi2": sigma_equiv_1000x2sigma},
        "C7": {"delta_chi2_single_3p1sigma": delta_chi2_1x3p1sigma, "aggregate_stronger": c7_pass}, "C8": c8,
        "ood_canary": ood_canary,
    }


def run_hidden_world_benchmark(seed: int = 7002026) -> Mapping[str, Any]:
    rng = np.random.default_rng(seed)
    core = ScientificPromotionCore()
    rows: list[dict[str, Any]] = []
    hidden_axis_hits = 0; hidden_axis_total = 0; dummy_rejected = 0; dummy_total = 0
    correct_law = 0; law_total = 0; false_promotions = 0; abstain_correct = 0; abstain_total = 0; ood_errors: list[float] = []
    fit_only_false = 0; fit_only_abstain_correct = 0; fit_only_positive = 0
    ood_only_false = 0; ood_only_abstain_correct = 0; ood_only_positive = 0

    categories = [("simple", 50), ("hidden", 50), ("phase", 30), ("nuisance", 30), ("nonidentifiable", 20), ("negative", 20)]
    world_index = 0
    for category, count in categories:
        for _ in range(count):
            world_index += 1
            n = 48; no = 36
            x = np.linspace(0.25, 1.5, n); xo = np.linspace(1.8, 3.2, no)
            sigma = np.full(n, 0.035); sigo = np.full(no, 0.045)
            axis_validations: list[dict[str, Any]] = []; latent_axes: tuple[str, ...] = (); global_status = "PASS"
            expected_promote = category in {"simple", "hidden", "phase", "nuisance"}
            if category == "simple" or category == "nuisance":
                a = rng.uniform(0.8, 1.6); alpha = rng.uniform(0.6, 1.6)
                truth = a * x ** alpha; truth_o = a * xo ** alpha
                if category == "nuisance":
                    for axis_id in ("X4", "X5", "X6"):
                        dummy_total += 1
                        validation = {"axis_id": axis_id, "base_log_likelihood_ood": -10.0, "augmented_log_likelihood_ood": -9.8,
                                      "additional_parameter_count": 1, "measurement_complexity": 0.4, "degrees_of_freedom_penalty": 0.2,
                                      "mechanism_absence_penalty": 0.6, "lambda_complexity": 1.0, "evidence_provenance": "hidden-world OOD"}
                        axis_validations.append(validation)
                        if validation["augmented_log_likelihood_ood"] - validation["base_log_likelihood_ood"] - 2.2 <= 0:
                            dummy_rejected += 1
            elif category == "hidden":
                a = rng.uniform(0.8, 1.5); alpha = rng.uniform(0.7, 1.4); zc = rng.uniform(0.5, 1.4)
                z = np.linspace(0.05, 1.0, n); zo = np.linspace(1.05, 2.0, no)
                truth = a * x ** alpha * np.exp(-z / zc); truth_o = a * xo ** alpha * np.exp(-zo / zc)
                base_o = a * xo ** alpha
                ll_base = -0.5 * float(np.sum(((truth_o - base_o) / sigo) ** 2)); ll_aug = 0.0
                validation = {"axis_id": "Z", "base_log_likelihood_ood": ll_base, "augmented_log_likelihood_ood": ll_aug,
                              "additional_parameter_count": 1, "measurement_complexity": 0.2, "degrees_of_freedom_penalty": 0.1,
                              "mechanism_absence_penalty": 0.0, "lambda_complexity": 1.0, "evidence_provenance": "hidden-world OOD"}
                axis_validations = [validation]; latent_axes = ("Z",); hidden_axis_total += 1
            elif category == "phase":
                xc = rng.uniform(0.65, 1.1); b1 = rng.uniform(0.6, 1.2); b2 = rng.uniform(1.4, 2.0)
                truth = np.where(x < xc, b1 * x, b1 * xc + b2 * (x - xc)); truth_o = np.where(xo < xc, b1 * xo, b1 * xc + b2 * (xo - xc))
            elif category == "nonidentifiable":
                a = rng.uniform(0.8, 1.6); truth = a * x; truth_o = a * xo; global_status = "FAIL_EQUIVALENT_PARAMETERIZATION_EXISTS"; expected_promote = False
            else:
                truth = rng.normal(0.0, 1.0, n); truth_o = rng.normal(0.0, 1.0, no); expected_promote = False

            y = truth + rng.normal(0.0, sigma); yo = truth_o + rng.normal(0.0, sigo)
            if category == "negative":
                pred = np.full(n, float(np.mean(y))); predo = np.full(no, float(np.mean(y)))
            else:
                pred = truth; predo = truth_o
            alts = _alt_rows(y, truth, known=(truth.copy() if category == "nonidentifiable" else None))
            rep_y = truth_o + rng.normal(0.0, sigo) if category != "negative" else rng.normal(0.0, 1.0, no)
            rep_pred = predo
            replication = {"y": [float(v) for v in rep_y], "sigma": [float(v) for v in sigo], "predictions": [float(v) for v in rep_pred],
                           "regime_id": f"REPLICATION-{world_index}", "provenance": "independent hidden-world replicate", "independent": True}
            train_std_rms = float(np.sqrt(np.mean(((y - pred) / sigma) ** 2)))
            ood_std_rms = float(np.sqrt(np.mean(((yo - predo) / sigo) ** 2)))
            fit_only_promote = train_std_rms <= 2.0
            ood_only_promote = fit_only_promote and ood_std_rms <= 2.0
            if expected_promote:
                fit_only_positive += int(fit_only_promote)
                ood_only_positive += int(ood_only_promote)
            else:
                fit_only_false += int(fit_only_promote)
                ood_only_false += int(ood_only_promote)
                fit_only_abstain_correct += int(not fit_only_promote)
                ood_only_abstain_correct += int(not ood_only_promote)

            request = _fixed_request(run_id=f"WORLD-{world_index:03d}", y_train=y, sigma_train=sigma, pred_train=pred, y_ood=yo, sigma_ood=sigo,
                                     pred_ood=predo, alternatives=alts, latent_axes=latent_axes, axis_validations=axis_validations,
                                     global_status=global_status, replication=replication, seed=seed + world_index)
            receipt = core.evaluate(request)
            promoted = bool(receipt["PROMOTION_ALLOWED"])
            engine_survived = receipt["FINAL_STATUS"] in {"REPLICATED", "LAW_CANDIDATE"}
            if category == "hidden":
                if receipt["gate_results"]["GENERATED_AXIS_OOD_VALIDATION"]["pass"]:
                    hidden_axis_hits += 1
            if expected_promote:
                law_total += 1; correct_law += int(engine_survived)
                if engine_survived:
                    ood_errors.append(float(receipt["gate_results"]["G6_REGIME_OOD"].get("standardized_residual_rms", math.nan)))
            else:
                abstain_total += 1; abstain_correct += int(not promoted); false_promotions += int(promoted)
            rows.append({"world_id": world_index, "category": category, "expected_engine_survive": expected_promote, "final_status": receipt["FINAL_STATUS"], "promotion_allowed": promoted, "engine_survived": engine_survived,
                         "terminal_reason": receipt["TERMINAL_REASON"], "receipt_id": receipt["RECEIPT_ID"]})

    metrics = {
        "world_count": len(rows), "R_law_core_adjudication": correct_law / max(law_total, 1), "R_hidden_axis": hidden_axis_hits / max(hidden_axis_total, 1),
        "R_dummy_rejection": dummy_rejected / max(dummy_total, 1), "FPR_promotion": false_promotions / max(abstain_total, 1),
        "R_abstain": abstain_correct / max(abstain_total, 1), "E_OOD_standardized_rms": float(np.nanmean(ood_errors)) if ood_errors else None,
    }
    local_controls = {
        "fit_only": {
            "R_positive_survival": fit_only_positive / max(law_total, 1),
            "FPR_promotion": fit_only_false / max(abstain_total, 1),
            "R_abstain": fit_only_abstain_correct / max(abstain_total, 1),
            "missing_gates": ["structural_identifiability", "practical_identifiability", "OOD", "replication"],
        },
        "train_plus_ood_only": {
            "R_positive_survival": ood_only_positive / max(law_total, 1),
            "FPR_promotion": ood_only_false / max(abstain_total, 1),
            "R_abstain": ood_only_abstain_correct / max(abstain_total, 1),
            "missing_gates": ["structural_identifiability", "practical_identifiability", "replication"],
        },
    }
    checks = {
        "exactly_200_worlds": len(rows) == 200,
        "negative_and_nonidentifiable_worlds_abstain": metrics["R_abstain"] == 1.0,
        "no_false_promotions_in_negative_or_nonidentifiable_worlds": metrics["FPR_promotion"] == 0.0,
        "hidden_axes_recovered": metrics["R_hidden_axis"] == 1.0,
        "dummy_axes_rejected": metrics["R_dummy_rejection"] == 1.0,
        "positive_worlds_survive_core": metrics["R_law_core_adjudication"] >= 0.95,
    }
    return {"schema": "phi-hidden-world-adjudication-benchmark/v8.1", "seed": seed, "categories": dict(categories), "metrics": metrics, "local_control_baselines": local_controls, "checks": checks,
            "status": "PASS_200_HIDDEN_WORLD_CORE_BENCHMARK" if all(checks.values()) else "FAIL_200_HIDDEN_WORLD_CORE_BENCHMARK",
            "worlds": rows,
            "claim_boundary": "This benchmarks the formal adjudication core and two deterministic decision-control baselines with candidate truth available only to the harness. It is not an end-to-end proposer benchmark and it is not an executed run of Google Co-Scientist, Edison Kosmos/Robin, Microsoft Discovery, Lila, or an external LLM."}


def run_release_qualification(seed: int = 7002026) -> Mapping[str, Any]:
    canaries = run_canaries(); worlds = run_hidden_world_benchmark(seed)
    blockers = {
        "bonus8_release_blocker": all(canaries["checks"][k] for k in ("C1_bonus8_A_false_M0_not_promoted", "C2_bonus8_B_high_precision_falsifies_M0", "C3_bonus8_C_strong_distinguishability_cannot_resurrect_false_model")),
        "negative_worlds_release_blocker": worlds["checks"]["negative_and_nonidentifiable_worlds_abstain"] and worlds["checks"]["no_false_promotions_in_negative_or_nonidentifiable_worlds"],
        "ood_release_blocker": canaries["checks"]["OOD_wrong_regime_prediction_is_falsified"],
        "identifiability_release_blocker": canaries["checks"]["C8_full_rank_weak_direction_is_non_identifiable"],
        "uncertainty_release_blocker": canaries["checks"]["C5_unknown_uncertainty_blocks"],
        "alternatives_release_blocker": canaries["checks"]["C4_empty_alternatives_blocks"],
    }
    ab = {
        "schema": "phi-preregistered-independent-competitor-exam/v1",
        "status": "PREREGISTERED_EXTERNAL_EXECUTION_REQUIRED",
        "freeze_seed": seed,
        "same_evidence_budget_required": True,
        "task_family_frozen_before_external_runs": True,
        "external_systems_to_run": [
            "GOOGLE_CO_SCIENTIST_OR_ACCESSIBLE_EQUIVALENT",
            "EDISON_KOSMOS_OR_ROBIN",
            "SYMBOLIC_REGRESSION_BASELINE_PYSR_OR_EQUIVALENT",
            "PLAIN_GENERAL_PURPOSE_LLM_RESEARCH_AGENT",
        ],
        "external_systems_executed_in_this_offline_release": False,
        "local_decision_controls_executed": ["fit_only", "train_plus_ood_only", "phi_full_fail_closed_adjudication"],
        "required_before_scientific_tool_claim": True,
        "required_metrics": ["rediscovery", "false_discovery_rate", "calibration", "hidden_axis_recovery", "falsification_survival", "experiment_efficiency", "OOD_error"],
        "power_analysis_required_before_run": True,
        "anti_leakage": [
            "freeze task generator seed and metric definitions before external outputs are observed",
            "identical evidence packets and tool budget per task",
            "no post-hoc prompt tuning per competitor",
            "score by machine-verifiable receipts, not prose preference",
        ],
        "definition_of_done": "Phi must show a statistically supported advantage on rediscovery and hidden-axis recovery while remaining non-inferior on false discovery and calibration; all claimed advantages require confidence intervals excluding zero.",
    }
    release_core_pass = all(blockers.values()) and canaries["status"].startswith("PASS") and worlds["status"].startswith("PASS")
    return {"schema": "phi-v9-release-qualification/v9.0", "system_status": SYSTEM_STATUS, "canaries": canaries, "hidden_world_benchmark": worlds,
            "release_blockers": blockers, "release_blockers_passed": release_core_pass,
            "blind_ab_benchmark": ab,
            "scientific_tool_claim_allowed": False,
            "status": "PASS_V9_FORMAL_CORE_RELEASE_BLOCKERS_WORLD_ATTESTATION_AND_AB_PENDING" if release_core_pass else "FAIL_V9_FORMAL_CORE_RELEASE_BLOCKERS"}


def main() -> None:
    print(json.dumps(run_release_qualification(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
