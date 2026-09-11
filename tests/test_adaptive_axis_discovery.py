import json
from pathlib import Path

from source.lawspace.adaptive_axis import AdaptiveAxisDiscoveryOwner
from source.lawspace.research_cycle import DynamicAxisProposal
from source.lawspace.scientific_rules import CommonScientificRulesCore

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    return [
        {"record_id":"A1","study_id":"S1","outcome_class":"THERAPEUTIC_SIGNAL", "context":{"disease_model_trigger":"6_OHDA", "species":"RAT", "therapeutic_modality":"SMALL_MOLECULE"}},
        {"record_id":"A2","study_id":"S2","outcome_class":"THERAPEUTIC_SIGNAL", "context":{"disease_model_trigger":"6_OHDA", "species":"RAT", "therapeutic_modality":"SMALL_MOLECULE"}},
        {"record_id":"A3","study_id":"S3","outcome_class":"THERAPEUTIC_SIGNAL", "context":{"disease_model_trigger":"LPS", "species":"RAT", "therapeutic_modality":"SMALL_MOLECULE"}},
        {"record_id":"A4","study_id":"S4","outcome_class":"NO_NEUROPROTECTION", "context":{"disease_model_trigger":"MPTP_ROTENONE", "species":"MOUSE", "therapeutic_modality":"SMALL_MOLECULE"}},
    ]


def positive_generalization_fixture():
    rows=[]
    for i in range(4):
        rows.append({"record_id":f"R-A-{i}","study_id":f"STUDY-A-{i}","outcome_class":"RESPONDER","context":{"novel_endotype_marker":"A"}})
    for i in range(4):
        rows.append({"record_id":f"R-B-{i}","study_id":f"STUDY-B-{i}","outcome_class":"NONRESPONDER","context":{"novel_endotype_marker":"B"}})
    return rows


def test_scan_finds_context_axis_without_mutating_registry():
    owner=AdaptiveAxisDiscoveryOwner()
    result=owner.scan(domain_id="pharmaceutical", evidence_records=fixture())
    rows={r["context_dimension"]:r for r in result["candidate_axes"]}
    assert rows["disease_model_trigger"]["status"] == "RESEARCH_LOCAL_AXIS_CANDIDATE"
    assert rows["disease_model_trigger"]["information_gain_bits"] > 0
    assert rows["therapeutic_modality"]["status"] == "EXISTING_DOMAIN_AXIS"
    assert result["claim_boundary"]["canonical_registry_mutated"] is False


def test_positive_causal_readiness_requires_positive_generalization_contract():
    result=AdaptiveAxisDiscoveryOwner().scan(domain_id="pharmaceutical", evidence_records=positive_generalization_fixture())
    row={r["context_dimension"]:r for r in result["candidate_axes"]}["novel_endotype_marker"]
    assert row["minimum_independent_study_support"] == 4
    assert row["grouped_study_exact_permutation"]["p_value"] < 0.05
    assert row["leave_one_study_out"]["gain"] > 0.0
    assert row["causal_readiness_pass"] is True
    assert result["scan_summary"]["causal_ready_candidate_dimensions"] == ["novel_endotype_marker"]
    assert result["scan_summary"]["automatic_causal_axis_selection_allowed"] is True


def test_tlr7_causal_readiness_rejects_normalized_ig_shortcut():
    evidence=json.loads((ROOT/"data/research_examples/tlr7_ad_context_evidence.json").read_text(encoding="utf-8"))
    result=AdaptiveAxisDiscoveryOwner().scan(domain_id="pharmaceutical", evidence_records=evidence["records"])
    rows={r["context_dimension"]:r for r in result["candidate_axes"]}
    expected=("disease_stage","microglial_state","agonist_exposure_time","agonist_intensity","neuronal_TLR7_state")
    assert all(rows[x]["normalized_information_gain"] < 0.90 for x in expected)
    assert all(rows[x]["causal_readiness_pass"] is False for x in expected)
    assert all(rows[x]["minimum_independent_study_support"] <= 1 for x in expected)
    assert all(rows[x]["leave_one_study_out"]["gain"] <= 0.0 for x in expected)
    assert result["scan_summary"]["causal_ready_candidate_dimensions"] == []
    assert result["scan_summary"]["automatic_causal_axis_selection_allowed"] is False
    assert result["scan_summary"]["causal_readiness_contract"]["normalized_ig_shortcut_threshold_used"] is False


def test_p2x7_high_ig_is_not_causal_readiness_without_replication_and_generalization():
    evidence=json.loads((ROOT/"data/research_examples/p2x7_pd_context_evidence.json").read_text(encoding="utf-8"))
    result=AdaptiveAxisDiscoveryOwner().scan(domain_id="pharmaceutical", evidence_records=evidence["records"])
    assert result["scan_summary"]["high_information_candidate_dimensions"]
    assert result["scan_summary"]["causal_ready_candidate_dimensions"] == []
    assert result["scan_summary"]["automatic_causal_axis_selection_allowed"] is False


def test_provisional_axis_mount_is_local_only():
    owner=AdaptiveAxisDiscoveryOwner()
    scan=owner.scan(domain_id="pharmaceutical", evidence_records=fixture())
    proposal=DynamicAxisProposal(
        proposal_id="TEST-PATHOPHYS-ENDOTYPE",
        domain_id="pharmaceutical",
        axis_id="pathophysiologic_endotype",
        description_ru="Механистически определённый эндотип заболевания, заданный заранее объявленным измеримым профилем.",
        value_kind="TEXT",
        physical_or_information_meaning="Mechanistic disease subgroup defined by measured pathway/cell-state biomarkers.",
        measurement_protocol="Assign only from a predeclared biomarker, imaging, omics or pathology rule with provenance.",
        units_or_normalization="study-specific controlled vocabulary with explicit classifier",
        expected_range={"values":["PREDECLARED_ENDOTYPE_LABELS"]},
        falsifiable_advantage="Held-out outcome or treatment-response prediction must improve after endotype stratification.",
        redundancy_test="Reject if target_population or another registered axis captures the same mechanistic partition without loss.",
    )
    admission=owner.admit_provisional_axis(scan_result=scan, source_dimension="disease_model_trigger", proposal=proposal)
    assert admission["research_region_mount_allowed"] is True
    region=owner.mount_research_region(domain_id="pharmaceutical", provisional_admissions=[admission])
    assert "pathophysiologic_endotype" in region["research_local_axis_ids"]
    assert region["canonical_registry_mutated"] is False


def test_common_rules_preserve_candidate_and_axis_incompleteness_boundaries():
    rules=CommonScientificRulesCore().contract()["generic_rules"]
    assert rules["absence_of_prior_art_is_not_candidate_rejection"] is True
    assert rules["external_contradiction_triggers_context_or_axis_investigation_before_rejection"] is True
    assert rules["axis_registry_has_no_fixed_ceiling"] is True
    assert rules["candidate_registry_is_baseline_not_solution_space"] is True
    assert rules["unknown_candidate_is_not_false"] is True
    assert rules["synthetic_false_positive_term_requires_known_ground_truth"] is True
    assert rules["void_frontier_regions_are_priority_research_targets"] is True
    assert rules["search_lane_is_broader_than_promotion_lane"] is True
    assert rules["promotion_statistics_do_not_revoke_exploration_rights"] is True
    assert rules["owner_affiliation_does_not_block_axis_combination"] is True
    assert rules["domain_affiliation_does_not_block_axis_combination"] is True
    assert rules["registered_axis_count_is_current_address_space_not_universal_ceiling"] is True


def test_failed_axis_promotion_is_unverified_candidate_not_false_axis():
    from source.lawspace.scientific_promotion import AxisOODValidation
    row=AxisOODValidation(
        axis_id='frontier_axis',base_log_likelihood_ood=-10.0,augmented_log_likelihood_ood=-10.2,
        evidence_provenance='controlled-test',
    ).to_result()
    assert row['accepted'] is False
    assert row['status']=='AXIS_NOT_PROMOTED_NO_OOD_GAIN'
    assert row['epistemic_status']=='UNVERIFIED_CANDIDATE'
    assert row['candidate_is_false'] is False


def test_axis_modeling_does_not_birth_interaction_with_train_constant_axis():
    import math
    from source.lawspace.axis_modeling import AxisModelingOwner

    rows=[]
    for regime,speed in (("FIT",30.0),("VALID",50.0)):
        for control in (0.0,1.0):
            for freq in (5.0,6.0,7.0,8.0,9.0,10.0,11.0,12.0):
                y=20.0 + 0.2*freq + 8.0*math.exp(-0.5*((freq-9.0)/0.8)**2)*(1.0-0.4*control)
                rows.append((regime,speed,control,freq,y))
    request={
        "seed":8150099,
        "ood_regime_ids":["VALID"],
        "dataset":{
            "dataset_id":"TRAIN-CONSTANT-INTERACTION-REGRESSION",
            "observable_id":"Y","observable_units":"arb",
            "y":[r[4] for r in rows],"sigma":None,"regime_ids":[r[0] for r in rows],"provenance":"UNIT_TEST",
            "axes":[
                {"axis_id":"frequency","domain":"physics","units":"Hz","values":[r[3] for r in rows],"provenance":"UNIT_TEST"},
                {"axis_id":"speed","domain":"physics","units":"m/s","values":[r[1] for r in rows],"provenance":"UNIT_TEST"},
                {"axis_id":"control","domain":"physics","units":"0/1","values":[r[2] for r in rows],"provenance":"UNIT_TEST"},
            ],
        },
    }
    result=AxisModelingOwner().run(request)
    best=result["best_axis_birth"]
    assert best["source_axis_id"] == "frequency"
    assert "control" in best["interaction_axes"]
    assert "speed" not in best["interaction_axes"]


def test_first_blind_real_physics_cycle_replays():
    from evaluation.axis_modeling_realdata_qualification import run_blind_real_physics_experiment
    result=run_blind_real_physics_experiment(ROOT)
    assert result["status"] == "PASS_FIRST_BLIND_REAL_PHYSICS_EXPERIMENT"
    assert result["passed"] == result["total"] == 18
    assert result["result_summary"]["born_center_hz"] == 9.0
    assert result["sealed_holdout_evaluation"]["refit_performed"] is False
    assert result["adaptive_kernel_receipt"]["atlas_claim"]["atlas_native"] is True


def test_adaptive_research_kernel_can_birth_multiple_dormant_axes_in_one_cycle():
    from source.lawspace.api import LawSpaceAPI

    rows=[]
    for i in range(72):
        x=(i-36)/11.0
        z=((i*7)%19-9)/5.0
        w=((i*11)%23-11)/6.0
        d=((i*5)%17-8)/4.0
        y=0.7*x - 1.25*z + 0.9*w
        rows.append({"record_id":f"MAB-{i:03d}","study_id":f"S-{i%6}","values":{"y":y,"x":x,"z":z,"w":w,"d":d}})
    request={
        "problem_id":"MULTI-AXIS-BIRTH-UNIT-CONTROL",
        "domain_id":"physics",
        "question":"Recover a typed response with an adaptively sized dormant-axis birth set.",
        "observations":rows,
        "sealed_holdout_observations":[],
        "target_variable":"y",
        "predictor_variables":["x"],
        "dormant_axis_variables":["z","w","d"],
        "variable_dimensions":{k:[0,0,0,0,0,0,0] for k in ("y","x","z","w","d")},
        "complexity_level":1,
        "fit_tolerance_nrmse":1e-10,
        "observations_origin":"UNIT_CONTROL",
        "auto_activate_dormant_axes":True,
    }
    result=LawSpaceAPI(ROOT).advance_adaptive_research(request)
    assert result["result"]["status"] == "HYPOTHESIS_SURVIVES_CURRENT_HELDOUT_EVIDENCE_NOT_LAW"
    assert set(result["result"]["activated_axis_variables"]) == {"z","w"}
    assert result["axis_birth_search"]["selected_cardinality"] == 2
    assert result["axis_birth_search"]["fixed_axis_count_per_cycle"] is None
    assert result["axis_birth_search"]["multi_axis_birth_allowed"] is True


def test_large_dormant_space_switches_to_sparse_forward_backward_search_without_cardinality_ceiling():
    from source.lawspace.api import LawSpaceAPI

    rows=[]
    distractors=[f"d{i}" for i in range(12)]
    for i in range(96):
        x=(i-48)/13.0
        z=((i*7)%29-14)/7.0
        w=((i*11)%31-15)/8.0
        values={"y":0.65*x-1.15*z+0.85*w,"x":x,"z":z,"w":w}
        for j,name in enumerate(distractors):
            values[name]=(((i*(13+2*j))%(37+2*j))-(18+j))/(9.0+j)
        rows.append({"record_id":f"SP-{i:03d}","study_id":f"S-{i%8}","values":values})
    names=("y","x","z","w",*distractors)
    result=LawSpaceAPI(ROOT).advance_adaptive_research({
        "problem_id":"SPARSE-MULTI-AXIS-BIRTH-UNIT-CONTROL",
        "domain_id":"physics",
        "question":"Recover a typed response in a large dormant coordinate space using sparse adaptive birth.",
        "observations":rows,"sealed_holdout_observations":[],
        "target_variable":"y","predictor_variables":["x"],
        "dormant_axis_variables":["z","w",*distractors],
        "variable_dimensions":{k:[0,0,0,0,0,0,0] for k in names},
        "complexity_level":1,"fit_tolerance_nrmse":1e-10,
        "axis_birth_trial_budget":512,"axis_birth_sparse_search_allowed":True,
        "observations_origin":"UNIT_CONTROL","auto_activate_dormant_axes":True,
    })
    assert result["result"]["status"] == "HYPOTHESIS_SURVIVES_CURRENT_HELDOUT_EVIDENCE_NOT_LAW"
    assert set(result["result"]["activated_axis_variables"]) == {"z","w"}
    assert result["axis_birth_search"]["policy"] == "SPARSE_ADAPTIVE_FORWARD_BACKWARD_SUBSET_SEARCH"
    assert result["axis_birth_search"]["selected_cardinality"] == 2
    assert result["axis_birth_search"]["fixed_axis_count_per_cycle"] is None
    assert result["axis_birth_search"]["resource_budget_is_scientific_cardinality_ceiling"] is False
