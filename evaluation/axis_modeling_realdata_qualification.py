"""Real-data, synthetic and canonical dynamic-axis qualification for v7.9."""
from __future__ import annotations

import hashlib
import json
import math
import tempfile
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from source.lawspace.axis_modeling import AxisModelingOwner, MODES
from source.lawspace.api import LawSpaceAPI
from source.lawspace.domains import DOMAIN_REGISTRIES, dynamic_axis_registry_state, reload_dynamic_axis_registry
from source.lawspace.research_cycle import AdaptiveResearchKernelOwner, DynamicAxisPromotionOwner, DynamicAxisProposal
from source.lawspace.schema import digest_payload


def dlr_figure23_request(root: str | Path) -> Mapping[str, Any]:
    root = Path(root)
    path = root / "data/external/aeronautics/dlr_olaf_public_multispeed_evidence_v6_26.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    src = doc["sources"][0]["figure23_vector_digitization"]
    curves = src["open_loop_and_closed_loop_points_by_speed_m_s"]
    f, speed, control, y, regime = [], [], [], [], []
    for speed_key in sorted(curves, key=float):
        for control_key in ("open_loop", "closed_loop"):
            for freq, mag in curves[speed_key][control_key]:
                f.append(float(freq)); speed.append(float(speed_key)); control.append(1.0 if control_key == "closed_loop" else 0.0)
                y.append(float(mag)); regime.append(f"U={float(speed_key):g}m/s")
    return {
        "seed": 710023,
        "modes": ["RANDOM", "HYPERVOID", "BOUNDARY", "EXTREME", "CROSSDOMAIN", "UNCERTAINTY", "AXIS_BIRTH"],
        "ood_regime_ids": ["U=40m/s"],
        "dataset": {
            "dataset_id": "DLR-OLAF-FIG23-AXIS-MODELING",
            "observable_id": "WRBM_MAGNITUDE",
            "observable_units": "dB",
            "y": y,
            "sigma": None,
            "regime_ids": regime,
            "provenance": f"{path.relative_to(root)}|DIRECT_PDF_VECTOR_GEOMETRY_NO_OCR|Figure23",
            "axes": [
                {"axis_id": "gust_frequency", "domain": "aeronautics_and_aerostation", "units": "Hz", "role": "observed", "values": f, "provenance": "DLR Figure23 digitized marker x-coordinate"},
                {"axis_id": "wind_speed", "domain": "aeronautics_and_aerostation", "units": "m/s", "role": "observed", "values": speed, "provenance": "DLR Figure23 panel speed"},
                {"axis_id": "control_state", "domain": "aeronautics_and_aerostation", "units": "0=open,1=closed", "role": "observed", "values": control, "provenance": "DLR Figure23 open/closed loop curve identity"},
            ],
        },
    }


def synthetic_hidden_axis_request() -> Mapping[str, Any]:
    rng = np.random.default_rng(710024)
    x0 = np.linspace(0.0, 10.0, 60)
    x = np.concatenate([x0, x0])
    regime = np.asarray(["train"] * len(x0) + ["ood"] * len(x0), dtype=object)
    hidden = np.exp(-0.5 * ((x - 5.6) / 0.65) ** 2)
    sigma = np.full_like(x, 0.08)
    # OOD changes only the noise realization, not the hidden structural law.
    y = 1.0 + 0.25 * x + 2.2 * hidden + rng.normal(0.0, sigma)
    return {
        "seed": 710024,
        "ood_regime_ids": ["ood"],
        "dataset": {
            "dataset_id": "AXIS-BIRTH-SYNTHETIC-CANARY",
            "observable_id": "Y",
            "observable_units": "arb",
            "y": y.tolist(),
            "sigma": sigma.tolist(),
            "regime_ids": regime.tolist(),
            "provenance": "POST_START_SYNTHETIC_HIDDEN_AXIS_CANARY",
            "axes": [{"axis_id": "x", "domain": "physics", "units": "arb", "role": "observed", "values": x.tolist(), "provenance": "synthetic observed coordinate"}],
        },
    }


def _synthetic_replication(modeling: Mapping[str, Any]) -> Mapping[str, Any]:
    best = dict(modeling["best_axis_birth"])
    rng = np.random.default_rng(710025)
    x0 = np.linspace(0.0, 10.0, 60)
    x = np.concatenate([x0, x0])
    train = np.asarray([True] * 60 + [False] * 60)
    ood = ~train
    hidden = np.exp(-0.5 * ((x - 5.6) / 0.65) ** 2)
    sigma = np.full_like(x, 0.08)
    y = 1.0 + 0.25 * x + 2.2 * hidden + rng.normal(0.0, sigma)
    Z = ((x - np.mean(x[train])) / np.std(x[train]))[:, None]
    B = AxisModelingOwner._baseline_features(Z)
    beta0 = AxisModelingOwner._ridge_fit(B[train], y[train])
    pred0 = B @ beta0
    g = np.exp(-0.5 * ((x - float(best["center_from_train_only"])) / float(best["width_from_train_only"])) ** 2)
    A = np.column_stack([B, g])
    beta1 = AxisModelingOwner._ridge_fit(A[train], y[train])
    pred1 = A @ beta1
    rmse0 = AxisModelingOwner._rmse(y[ood], pred0[ood])
    rmse1 = AxisModelingOwner._rmse(y[ood], pred1[ood])
    return {
        "independent": True,
        "provenance": "POST_START_SYNTHETIC_HIDDEN_AXIS_CANARY_INDEPENDENT_NOISE_SEED_710025",
        "ood_rmse_baseline": rmse0,
        "ood_rmse_augmented": rmse1,
        "fractional_improvement": (rmse0 - rmse1) / rmse0,
        "pass": rmse1 < rmse0,
    }


def run_release_qualification(root: str | Path) -> Mapping[str, Any]:
    root = Path(root)
    owner = AxisModelingOwner()
    dlr = owner.run(dlr_figure23_request(root))
    dlr_freeze_digest_before_reconciliation = dlr["digest"]
    independent_path = root / "data/external/aeronautics/dlr_olaf_gla_2024_digitized.json"
    independent_doc = json.loads(independent_path.read_text(encoding="utf-8"))
    known_flexible_mode_hz = float(independent_doc["operating_point"]["first_flexible_eigenfrequency_hz"])
    found_center_hz = float(dlr["best_axis_birth"]["center_from_train_only"])
    match_gap_hz = abs(found_center_hz - known_flexible_mode_hz)
    internal_reconciliation = {
        "performed_after_axis_modeling_freeze": True,
        "freeze_digest": dlr_freeze_digest_before_reconciliation,
        "independent_internal_source": str(independent_path.relative_to(root)),
        "registered_related_axis_id": "flexible_mode_frequency",
        "found_center_hz": found_center_hz,
        "independent_flexible_mode_hz": known_flexible_mode_hz,
        "absolute_gap_hz": match_gap_hz,
        "status": "REDISCOVERED_EXISTING_FLEXIBLE_MODE_PROXIMITY" if match_gap_hz <= 0.25 else "NO_INTERNAL_MATCH_FOUND",
        "new_axis_claim_allowed": False,
        "interpretation": "The generated residual-localization coordinate is a data-driven proximity-to-mode coordinate, not evidence for an independent new physical dimension when it coincides with the independently recorded flexible-mode frequency.",
    }
    dlr = dict(dlr)
    dlr["postfreeze_internal_reconciliation"] = internal_reconciliation
    dlr["digest_after_reconciliation"] = digest_payload(dlr)

    synthetic = owner.run(synthetic_hidden_axis_request())
    replication = _synthetic_replication(synthetic)
    proposal = DynamicAxisProposal(**dict(synthetic["semantic_axis_admission"]["proposal"]))
    validation = {
        "promotion_route": "MODEL_DISCOVERED",
        "semantic_class": "DERIVED_COORDINATE",
        "measurement_uncertainty_declared": True,
        "identifiability_pass": bool(synthetic["best_axis_birth"]["derived_feature_identifiability_pass"]),
        "ood_pass": synthetic["best_axis_birth"]["status"] == "AXIS_BIRTH_OOD_VALIDATED",
        "ood_fractional_improvement": synthetic["best_axis_birth"]["ood_rmse_fractional_improvement"],
        "complexity_penalized_delta_log_likelihood": synthetic["best_axis_birth"]["axis_score"],
        "independent_replication": bool(replication["pass"]),
        "replication_provenance": replication["provenance"],
        "falsification_status": "SURVIVED" if synthetic["best_axis_birth"]["local_multiscale_robust_fraction"] >= 0.6 else "FAILED",
        "falsification_protocol": "fixed-center/width neighborhood must preserve OOD gain on >=60% of perturbations",
        "postfreeze_redundancy_status": "NO_REGISTERED_AXIS_EQUIVALENT",
        "derivation": synthetic["best_axis_birth"]["generated_coordinate"],
        "independent_measurement_or_calibration": False,
        "evidence_digest": digest_payload({"model": synthetic["digest"], "replication": replication}),
    }
    with tempfile.TemporaryDirectory(prefix="phi-axis-promotion-") as td:
        overlay = Path(td) / "canonical_dynamic_axes.json"
        # v8 trust boundary: qualification/synthetic evidence may validate the
        # axis-birth engine, but it is not WORLD evidence and therefore must
        # never mutate the canonical scientific registry.  The positive
        # externally-provisioned WORLD canonical-mutation path is qualified in
        # scientific_verification_qualification.py.
        reload_dynamic_axis_registry(overlay)
        before = sum(r.axis_count for r in DOMAIN_REGISTRIES.values())
        promotion = DynamicAxisPromotionOwner(root).evaluate_and_promote(
            proposal, validation, mutate=True, registry_path=overlay
        )
        after = sum(r.axis_count for r in DOMAIN_REGISTRIES.values())
        reload_receipt = reload_dynamic_axis_registry(overlay)
        temp_state = dynamic_axis_registry_state(overlay)
        # Restore the release registry after isolated qualification.
        reload_dynamic_axis_registry()
        restored = sum(r.axis_count for r in DOMAIN_REGISTRIES.values())

    dlr_proposal = DynamicAxisProposal(**dict(dlr["semantic_axis_admission"]["proposal"]))
    dlr_blocked = DynamicAxisPromotionOwner(root).evaluate_and_promote(
        dlr_proposal,
        {
            "promotion_route": "MODEL_DISCOVERED",
            "semantic_class": "DERIVED_COORDINATE",
            "measurement_uncertainty_declared": False,
            "identifiability_pass": bool(dlr["best_axis_birth"]["derived_feature_identifiability_pass"]),
            "ood_pass": False,
            "ood_fractional_improvement": dlr["best_axis_birth"]["ood_rmse_fractional_improvement"],
            "complexity_penalized_delta_log_likelihood": dlr["best_axis_birth"]["axis_score"],
            "independent_replication": False,
            "replication_provenance": "",
            "falsification_status": "SURVIVED",
            "falsification_protocol": "post-freeze independent flexible-mode reconciliation",
            "postfreeze_redundancy_status": "MATCHED_EXISTING_AXIS",
            "derivation": dlr["best_axis_birth"]["generated_coordinate"],
            "evidence_digest": digest_payload(internal_reconciliation),
        },
        mutate=False,
    )

    checks = {
        "DLR_REAL_DATA_STRUCTURE_FOUND": dlr["final_status"] == "STRUCTURE_FOUND_PROMOTION_BLOCKED",
        "DLR_UNCERTAINTY_FAIL_CLOSED": dlr["modes"]["UNCERTAINTY"]["status"] == "BLOCKED_NO_MEASUREMENT_UNCERTAINTY" and not dlr["promotion_allowed"],
        "DLR_OOD_IMPROVEMENT_POSITIVE": bool(dlr["best_axis_birth"] and dlr["best_axis_birth"]["ood_rmse_fractional_improvement"] > 0.0),
        "DLR_POSTFREEZE_REDISCOVERY_NOT_FALSE_NOVELTY": dlr["postfreeze_internal_reconciliation"]["status"] == "REDISCOVERED_EXISTING_FLEXIBLE_MODE_PROXIMITY" and not dlr["postfreeze_internal_reconciliation"]["new_axis_claim_allowed"],
        "DLR_CANONICAL_PROMOTION_BLOCKED_AS_REDUNDANT": dlr_blocked["qualified"] is False and dlr_blocked["gates"]["POSTFREEZE_NO_REGISTERED_EQUIVALENT"] is False,
        "SYNTHETIC_AXIS_BIRTH_VALIDATED": synthetic["best_axis_birth"]["status"] == "AXIS_BIRTH_OOD_VALIDATED",
        "SYNTHETIC_FEATURE_IDENTIFIABLE": synthetic["best_axis_birth"]["derived_feature_identifiability_pass"] is True,
        "SYNTHETIC_INDEPENDENT_REPLICATION": replication["pass"] is True,
        "SYNTHETIC_QUALIFICATION_CANNOT_CANONICAL_PROMOTE_WITHOUT_WORLD_ATTESTATION": after == before and promotion["qualified"] is False and promotion["gates"].get("WORLD_ATTESTATION_READY") is False,
        "SYNTHETIC_QUALIFICATION_LEAVES_ISOLATED_REGISTRY_UNCHANGED": reload_receipt["canonical_axis_count"] == before and temp_state["dynamic_axis_count"] == 0,
        "RELEASE_REGISTRY_RESTORED_AFTER_ISOLATED_CANARY": restored >= before,
    }
    payload = {
        "schema": "phi-axis-modeling-qualification/v8.0",
        "owner": "AXIS-MODELING-QUALIFICATION/8.0.0",
        "checks": checks,
        "passed": all(checks.values()),
        "dlr_real_data_study": dlr,
        "dlr_dynamic_promotion_receipt": dlr_blocked,
        "synthetic_hidden_axis_canary": synthetic,
        "synthetic_independent_replication": replication,
        "synthetic_dynamic_promotion_receipt": promotion,
    }
    payload["digest"] = digest_payload(payload)
    return payload


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _dlr_blind_partition(root: Path) -> Mapping[str, Any]:
    source_path = root / "data/external/aeronautics/dlr_olaf_public_multispeed_evidence_v6_26.json"
    doc = json.loads(source_path.read_text(encoding="utf-8"))
    curves = doc["sources"][0]["figure23_vector_digitization"]["open_loop_and_closed_loop_points_by_speed_m_s"]
    discovery_rows=[]; sealed_rows=[]
    for speed_key in ("30", "50"):
        for control_key in ("open_loop", "closed_loop"):
            control=1.0 if control_key=="closed_loop" else 0.0
            for frequency,magnitude in curves[speed_key][control_key]:
                frequency=float(frequency)
                discovery_rows.append({"record_id":f"U{speed_key}-{control_key}-{frequency:g}","frequency":frequency,"wind_speed":float(speed_key),"control_state":control,"wrbm_db":float(magnitude),"regime":"VALIDATION" if int(round(frequency)) in {5,8,11} else "DISCOVERY"})
    for control_key in ("open_loop", "closed_loop"):
        control=1.0 if control_key=="closed_loop" else 0.0
        for frequency,magnitude in curves["40"][control_key]:
            sealed_rows.append({"record_id":f"U40-{control_key}-{float(frequency):g}","frequency":float(frequency),"wind_speed":40.0,"control_state":control,"wrbm_db":float(magnitude),"regime":"SEALED_U40"})
    def dataset(rows,dataset_id):
        return {"dataset_id":dataset_id,"observable_id":"WRBM_MAGNITUDE","observable_units":"dB","y":[r["wrbm_db"] for r in rows],"sigma":None,"regime_ids":[r["regime"] for r in rows],"provenance":f"{source_path.relative_to(root)}|DIRECT_PDF_VECTOR_GEOMETRY_NO_OCR|Figure23","axes":[{"axis_id":"gust_frequency","domain":"aeronautics_and_aerostation","units":"Hz","role":"observed","values":[r["frequency"] for r in rows],"provenance":"DLR Figure23 marker coordinate"},{"axis_id":"wind_speed","domain":"aeronautics_and_aerostation","units":"m/s","role":"observed","values":[r["wind_speed"] for r in rows],"provenance":"DLR Figure23 panel speed"},{"axis_id":"control_state","domain":"aeronautics_and_aerostation","units":"0=open,1=closed","role":"observed","values":[r["control_state"] for r in rows],"provenance":"DLR Figure23 curve identity"}]}
    discovery_dataset=dataset(discovery_rows,"DLR-OLAF-FIG23-BLIND-DISCOVERY-30-50"); sealed_dataset=dataset(sealed_rows,"DLR-OLAF-FIG23-SEALED-U40")
    precommit={"source_path":str(source_path.relative_to(root)),"source_file_sha256":_sha256_file(source_path),"partition_rule":{"search_speeds_m_s":[30.0,50.0],"sealed_speed_m_s":40.0,"validation_frequency_coordinates":[5.0,8.0,11.0],"partition_uses_target_values":False},"discovery_dataset_digest":digest_payload(discovery_dataset),"sealed_holdout_commitment_digest":digest_payload(sealed_dataset),"discovery_count":len(discovery_rows),"sealed_count":len(sealed_rows)}
    return {"precommit":{**precommit,"digest":digest_payload(precommit)},"discovery_rows":discovery_rows,"discovery_dataset":discovery_dataset,"sealed_rows":sealed_rows,"sealed_dataset":sealed_dataset}


def run_blind_real_physics_experiment(root: str | Path) -> Mapping[str, Any]:
    root=Path(root).resolve(); partition=_dlr_blind_partition(root); owner=AxisModelingOwner()
    modeling=owner.run({"seed":8150002,"modes":list(MODES),"ood_regime_ids":["VALIDATION"],"dataset":partition["discovery_dataset"]})
    observed_points=[{"values":{"gust_frequency":r["frequency"],"wind_speed":r["wind_speed"],"control_state":r["control_state"]}} for r in partition["discovery_rows"]]
    discriminator=owner.design_discriminating_experiment(modeling,observed_points=observed_points)
    best_axis=dict(modeling.get("best_axis_birth") or {}); center=float(best_axis.get("center_from_train_only",float("nan"))); width=float(best_axis.get("width_from_train_only",float("nan")))
    adaptive_observations=[]
    for r in partition["discovery_rows"]:
        g=math.exp(-0.5*((r["frequency"]-center)/width)**2)
        adaptive_observations.append({"record_id":r["record_id"],"study_id":r["record_id"],"values":{"gust_frequency":r["frequency"],"wind_speed":r["wind_speed"],"control_state":r["control_state"],"mode_proximity":g,"wrbm_db":r["wrbm_db"]}})
    adaptive_observations.sort(key=lambda r:(r["values"]["gust_frequency"],r["values"]["control_state"],r["values"]["wind_speed"]))
    experiment_points=[]
    for r in discriminator.get("rows",())[:64]:
        vals=dict(r["axis_values"]); vals["mode_proximity"]=math.exp(-0.5*((float(vals["gust_frequency"])-center)/width)**2); experiment_points.append({"experiment_id":str(r["experiment_id"]),**vals})
    dimless=[0,0,0,0,0,0,0]
    adaptive=LawSpaceAPI(root).advance_adaptive_research({"problem_id":"DLR-OLAF-FIRST-BLIND-REAL-PHYSICS-001","domain_id":"aeronautics_and_aerostation","question":"Using only measured oLAF Figure-23 response coordinates, determine whether the current frequency/speed/control representation leaves stable residual structure requiring a born coordinate and propose a measurement that best separates surviving representations.","observations":adaptive_observations,"sealed_holdout_observations":(),"target_variable":"wrbm_db","predictor_variables":["gust_frequency","wind_speed","control_state"],"dormant_axis_variables":["mode_proximity"],"variable_dimensions":{"wrbm_db":dimless,"gust_frequency":[0,0,-1,0,0,0,0],"wind_speed":[1,0,-1,0,0,0,0],"control_state":dimless,"mode_proximity":dimless},"complexity_level":2,"fit_tolerance_nrmse":0.15,"observations_origin":"PUBLIC_MEASURED_DIGITIZED","auto_activate_dormant_axes":True,"experiment_points":experiment_points})
    code_digest=digest_payload({"axis_modeling":_sha256_file(root/"source/lawspace/axis_modeling.py"),"adaptive_research":_sha256_file(root/"source/lawspace/research_cycle.py"),"qualification":_sha256_file(Path(__file__))})
    freeze_core={"schema":"phi-blind-real-physics-freeze/v1","problem_id":"DLR-OLAF-FIRST-BLIND-REAL-PHYSICS-001","source_file_sha256":partition["precommit"]["source_file_sha256"],"partition_precommit_digest":partition["precommit"]["digest"],"sealed_holdout_commitment_digest":partition["precommit"]["sealed_holdout_commitment_digest"],"axis_modeling_digest":modeling["digest"],"discriminator_digest":discriminator["digest"],"adaptive_kernel_receipt_digest":adaptive["digest"],"adaptive_claim_digest":adaptive["atlas_claim"]["digest"],"code_digest":code_digest,"sealed_holdout_values_consumed_before_freeze":False,"known_flexible_mode_reference_consumed_before_freeze":False}
    research_freeze={**freeze_core,"digest":digest_payload(freeze_core)}
    sealed_commitment_verified=digest_payload(partition["sealed_dataset"])==partition["precommit"]["sealed_holdout_commitment_digest"]
    sealed_evaluation=owner.evaluate_frozen_axis_candidate(modeling,partition["sealed_dataset"])
    adaptive_holdout=[]
    for r in partition["sealed_rows"]:
        g=math.exp(-0.5*((r["frequency"]-center)/width)**2); adaptive_holdout.append({"values":{"gust_frequency":r["frequency"],"wind_speed":r["wind_speed"],"control_state":r["control_state"],"mode_proximity":g,"wrbm_db":r["wrbm_db"]}})
    adaptive_sealed=AdaptiveResearchKernelOwner._evaluate_candidate_on_observations(adaptive.get("result",{}).get("best_hypothesis"),adaptive_holdout,adaptive.get("result",{}).get("effective_predictor_variables",()),"wrbm_db")
    independent_path=root/"data/external/aeronautics/dlr_olaf_gla_2024_digitized.json"; independent_doc=json.loads(independent_path.read_text(encoding="utf-8")); known=float(independent_doc["operating_point"]["first_flexible_eigenfrequency_hz"]); gap=abs(center-known)
    reconciliation={"performed_after_research_freeze":True,"research_freeze_digest":research_freeze["digest"],"independent_source":str(independent_path.relative_to(root)),"independent_source_sha256":_sha256_file(independent_path),"born_center_hz":center,"independent_flexible_mode_hz":known,"absolute_gap_hz":gap,"status":"BLIND_REDISCOVERY_MATCHES_EXISTING_FLEXIBLE_MODE" if gap<=0.25 else "BLIND_STRUCTURE_NOT_RECONCILED_TO_EXISTING_MODE","new_axis_claim_allowed":False}
    selected=discriminator.get("selected_experiment") or {}
    checks={"REAL_PUBLIC_DLR_DATA_USED":modeling.get("dataset",{}).get("dataset_id")=="DLR-OLAF-FIG23-BLIND-DISCOVERY-30-50","PARTITION_IS_TARGET_BLIND":partition["precommit"]["partition_rule"]["partition_uses_target_values"] is False,"SEALED_U40_EXCLUDED_FROM_SEARCH":set(modeling.get("dataset",{}).get("regimes",()))=={"DISCOVERY","VALIDATION"} and 40.0 not in set(partition["discovery_dataset"]["axes"][1]["values"]),"SEALED_HOLDOUT_COMMITMENT_VERIFIED":sealed_commitment_verified,"RESIDUAL_BIRTHS_FREQUENCY_LOCALIZATION":best_axis.get("source_axis_id")=="gust_frequency" and best_axis.get("status")=="AXIS_BIRTH_PROMISING_EXPLORATORY","BORN_CENTER_FROM_DISCOVERY_IS_9HZ":abs(center-9.0)<=1e-12,"INTERACTION_STRUCTURE_USES_SPEED_AND_CONTROL":set(best_axis.get("interaction_axes",()))=={"wind_speed","control_state"},"VALIDATION_ERROR_IMPROVES_MATERIALLY":float(best_axis.get("ood_rmse_fractional_improvement",0.0))>0.50,"FROZEN_MODEL_IS_REPLAYABLE":bool(best_axis.get("frozen_model")),"AUTO_DISCRIMINATOR_RANKED_UNMEASURED_POINT":discriminator.get("status")=="AUTO_DISAGREEMENT_EXPERIMENT_RANKED" and bool(selected) and selected.get("already_observed") is False,"DISCRIMINATOR_USED_NO_TARGET_OR_SEALED_VALUES":discriminator.get("sealed_holdout_values_used") is False,"ADAPTIVE_KERNEL_ACTIVATES_BORN_COORDINATE":adaptive.get("result",{}).get("activated_axis_variables")==["mode_proximity"],"CLAIM_FIREWALL_ACCEPTS_ADAPTIVE_RECEIPT":adaptive.get("atlas_claim",{}).get("atlas_native") is True,"FREEZE_PRECEDES_SEALED_EVALUATION":research_freeze.get("sealed_holdout_values_consumed_before_freeze") is False and sealed_evaluation.get("refit_performed") is False,"SEALED_U40_IMPROVES_WITH_FROZEN_AXIS_MODEL":sealed_evaluation.get("status")=="SEALED_POSTFREEZE_EVALUATED" and float(sealed_evaluation.get("fractional_rmse_improvement",0.0))>0.25,"POSTFREEZE_RECONCILES_TO_INDEPENDENT_FLEXIBLE_MODE":reconciliation["status"]=="BLIND_REDISCOVERY_MATCHES_EXISTING_FLEXIBLE_MODE","NO_FALSE_NOVELTY_OR_PROMOTION":reconciliation["new_axis_claim_allowed"] is False and modeling.get("promotion_allowed") is False,"NO_NEW_WORLD_LAW_CLAIM":adaptive.get("result",{}).get("scientific_law_established") is False and adaptive.get("atlas_claim",{}).get("scientific_truth_established") is False}
    passed=sum(bool(v) for v in checks.values())
    payload={"schema":"phi-first-blind-real-physics-experiment/v1","owner":"BLIND-REAL-PHYSICS-QUALIFICATION/15.8.0","release":"15.8.0","problem_id":"DLR-OLAF-FIRST-BLIND-REAL-PHYSICS-001","status":"PASS_FIRST_BLIND_REAL_PHYSICS_EXPERIMENT" if passed==len(checks) else "FAIL_FIRST_BLIND_REAL_PHYSICS_EXPERIMENT","passed":passed,"total":len(checks),"checks":checks,"precommit":partition["precommit"],"research_freeze":research_freeze,"axis_modeling":modeling,"auto_discriminating_experiment":discriminator,"adaptive_kernel_receipt":adaptive,"sealed_holdout_evaluation":sealed_evaluation,"adaptive_sealed_holdout_evaluation":adaptive_sealed,"postfreeze_reconciliation":reconciliation,"result_summary":{"born_axis":best_axis.get("axis_id"),"born_center_hz":center,"born_width_hz":width,"interaction_axes":best_axis.get("interaction_axes"),"validation_rmse_baseline_db":modeling.get("baseline",{}).get("ood_rmse"),"validation_rmse_augmented_db":best_axis.get("ood_rmse_augmented"),"validation_fractional_improvement":best_axis.get("ood_rmse_fractional_improvement"),"sealed_u40_rmse_baseline_db":sealed_evaluation.get("baseline_rmse"),"sealed_u40_rmse_augmented_db":sealed_evaluation.get("augmented_rmse"),"sealed_u40_fractional_improvement":sealed_evaluation.get("fractional_rmse_improvement"),"selected_discriminating_experiment":selected,"adaptive_activated_axes":adaptive.get("result",{}).get("activated_axis_variables"),"adaptive_claim_status":adaptive.get("atlas_claim",{}).get("status"),"postfreeze_mode_gap_hz":gap},"claim_boundary":{"real_measured_public_data":True,"new_physical_law_established":False,"new_axis_established":False,"scientific_promotion_allowed":False,"reason":"Digitized public Figure-23 data lack declared measurement uncertainty/raw synchronized DAQ; the blind result is a reproducible rediscovery/representation result, not a new-law claim."}}
    return {**payload,"digest":digest_payload(payload)}


if __name__ == "__main__":
    import sys
    args = list(sys.argv[1:]); blind = "--blind-current" in args; args = [a for a in args if a != "--blind-current"]
    root = Path(args[0] if args else ".")
    payload = run_blind_real_physics_experiment(root) if blind else run_release_qualification(root)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
