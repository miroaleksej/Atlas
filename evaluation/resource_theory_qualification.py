"""Qualification for Φ-Resource Theory Discovery 1.0.0."""
from __future__ import annotations
import json, math
from pathlib import Path
from typing import Any

from source.lawspace.resource_theory import ResourceTheoryDiscoveryKernel
from source.lawspace.domains import canonical_axis_count
from source.lawspace.schema import digest_payload

SCHEMA="phi-resource-theory-qualification/v1"; RELEASE="10.5.0"


def _rows(*, broken_prospective: bool=False):
    rows=[]
    # Three training environments and two genuinely unseen prospective environments.
    specs=[("train-A",0,18), ("train-B",18,36), ("train-C",36,54), ("prospective-X",54,72), ("prospective-Y",72,90)]
    for env,start,stop in specs:
        for i in range(start,stop):
            x0=0.20 + ((i*7)%19)/7.0 + (0.15 if env=="train-B" else 0.0) + (0.55 if env.startswith("prospective") else 0.0)
            x1=0.10 + ((i*11)%17)/8.0
            x2=0.15 + ((i*5)%23)/9.0 + (0.10 if env=="train-C" else 0.0) + (0.35 if env=="prospective-Y" else 0.0)
            x3=0.05 + ((i*13)%29)/12.0
            # Hidden benchmark resource is not exposed to the solver.
            r_hidden=(1.0+x0)*((1.0+x2)**2)
            cost=2.3*(r_hidden**0.78)*(1.0+0.018*math.sin(0.71*i))
            if broken_prospective and env.startswith("prospective"):
                cost=1.8*((1.0+x1)**1.65)*(1.0+0.02*math.cos(0.43*i))
            rows.append({
                "workload_id":f"w{i:03d}","environment_id":env,
                "executable_digest":digest_payload({"exe":i%7,"schema":"controlled-workload"}),
                "measurement_receipt_digest":digest_payload({"measurement":i,"env":env}),
                "observables":{"x0":x0,"x1":x1,"x2":x2,"x3":x3},
                # These are deliberately only post-freeze anchors. None are candidate inputs.
                "known_resource_anchors":{
                    "entanglement_entropy":x0,
                    "treewidth":x1,
                    "magic_monotone":x2,
                    "memory_rank":x3,
                },
                "measured_cost":cost,
            })
    train=[r["workload_id"] for r in rows if r["environment_id"].startswith("train-")]
    prospective=[r["workload_id"] for r in rows if r["environment_id"].startswith("prospective-")]
    return rows,train,prospective


def run_release_qualification(root: str|Path|None=None)->dict[str,Any]:
    root=Path(root or Path(__file__).resolve().parents[1]); kernel=ResourceTheoryDiscoveryKernel(root)
    rows,train,prospective=_rows()
    result=kernel.discover_and_validate(
        question="discover an intrinsic computational resource that predicts execution cost across unseen workloads without selecting named resource measures",
        workload_rows=rows, training_workload_ids=train, prospective_workload_ids=prospective,
    )
    candidate=result["candidate"]; validation=result["prospective_validation"]; projections=result["postfreeze_projection_comparison"]
    # Negative controls.
    bad_rows,bad_train,bad_prospective=_rows(broken_prospective=True)
    negative=kernel.discover_and_validate(
        question="discover stable resource law under prospective regime change",
        workload_rows=bad_rows, training_workload_ids=bad_train, prospective_workload_ids=bad_prospective,
    )
    leakage=kernel.prospective.validate(candidate_receipt=candidate, workload_rows=rows, prospective_workload_ids=(train[0],prospective[0]))
    too_small=kernel.synthesis.synthesize(question="too little support",workload_rows=rows[:6],training_workload_ids=[r["workload_id"] for r in rows[:6]])
    named_prefreeze=[dict(r, observables={**r["observables"],"treewidth":r["known_resource_anchors"]["treewidth"]}) for r in rows[:18]]
    named_blocked=False
    try:
        kernel.synthesis.synthesize(question="named anchor leakage",workload_rows=named_prefreeze,training_workload_ids=[r["workload_id"] for r in named_prefreeze])
    except ValueError:
        named_blocked=True
    expr=candidate.get("frozen_resource",{}).get("expression",{})
    metrics=validation.get("metrics",{})
    comparisons=projections.get("comparisons",[])
    checks={
      "kernel_owner_contract":kernel.contract()["owner_id"]=="PHI-RESOURCE-THEORY-DISCOVERY/1.0.0",
      "synthesis_owner_contract":kernel.synthesis.contract()["owner_id"]=="RESOURCE-LAW-SYNTHESIS/1.0.0",
      "prospective_owner_contract":kernel.prospective.contract()["owner_id"]=="RESOURCE-LAW-PROSPECTIVE-VALIDATION/1.0.0",
      "projection_owner_contract":kernel.projections.contract()["owner_id"]=="RESOURCE-PROJECTION-COMPARISON/1.0.0",
      "internal_phi_scan_all_current":candidate.get("phi_scan",{}).get("registered_axis_count")==canonical_axis_count() and candidate.get("phi_scan",{}).get("all_registered_axes_visited") is True,
      "no_fixed_owner_visit_budget":candidate.get("phi_scan",{}).get("fixed_owner_visit_budget") is None,
      "no_fixed_axis_order_ceiling":candidate.get("phi_scan",{}).get("fixed_candidate_axis_order_ceiling") is None,
      "blind_firewall":candidate.get("phi_scan",{}).get("knowledge_firewall",{}).get("passport_names_used_for_source_scoring") is False,
      "candidate_frozen":candidate.get("status")=="RESOURCE_CANDIDATE_FROZEN" and bool(candidate.get("resource_freeze_digest")),
      "content_addressed_resource":str(candidate.get("resource_id","")).startswith("R-") and len(candidate.get("resource_id",""))==18,
      "opaque_features_only":set(expr.get("feature_ids",()))=={"x0","x1","x2","x3"},
      "known_named_resource_not_selected":candidate.get("claim_boundary",{}).get("known_named_resource_selected_as_answer") is False,
      "prospective_cost_not_used_for_selection":candidate.get("claim_boundary",{}).get("prospective_costs_used_for_candidate_selection") is False,
      "training_environment_cv":len(candidate.get("cv_folds",()))==3,
      "positive_cost_scaling":candidate.get("frozen_resource",{}).get("cost_law",{}).get("slope_log_resource",0)>0,
      "prospective_status_pass":validation.get("status")=="RESOURCE_THEORY_PROSPECTIVELY_QUALIFIED",
      "prospective_environments_disjoint":validation.get("training_and_prospective_environments_disjoint") is True,
      "prospective_workload_count":metrics.get("count")==36,
      "prospective_r2_gate":float(metrics.get("r2_cost",-1))>=0.90,
      "prospective_error_gate":float(metrics.get("mean_absolute_fractional_error",1))<=0.15,
      "each_prospective_environment_pass":all(float(x.get("r2_cost",-1))>=0.75 for x in metrics.get("per_environment",())),
      "resource_theory_result_pass":result.get("status")=="RESOURCE_THEORY_DISCOVERED_PROSPECTIVE",
      "postfreeze_projection_only":projections.get("status")=="POSTFREEZE_RESOURCE_PROJECTION_COMPARISON" and projections.get("selection_feedback_to_frozen_resource") is False,
      "known_anchor_comparisons_present":set(x.get("anchor_name") for x in comparisons)=={"entanglement_entropy","treewidth","magic_monotone","memory_rank"},
      "negative_regime_shift_rejected":negative.get("status")=="RESOURCE_THEORY_NOT_ESTABLISHED" and negative.get("prospective_validation",{}).get("status")=="RESOURCE_THEORY_NOT_ESTABLISHED_PROSPECTIVE_FAILURE",
      "prospective_leakage_rejected":leakage.get("status")=="RESOURCE_THEORY_NOT_ESTABLISHED_PROSPECTIVE_LEAKAGE",
      "insufficient_support_rejected":too_small.get("status")=="RESOURCE_THEORY_NOT_ESTABLISHED_INSUFFICIENT_TRAINING_SUPPORT",
      "named_resource_prefreeze_blocked":named_blocked,
      "internet_not_prefreeze":result.get("claim_boundary",{}).get("internet_used_prefreeze") is False,
      "world_novelty_not_claimed":result.get("claim_boundary",{}).get("world_resource_novelty_established") is False,
      "world_resource_theory_not_claimed":result.get("claim_boundary",{}).get("world_resource_theory_established") is False,
      "synthetic_pass_not_world_discovery":validation.get("claim_boundary",{}).get("synthetic_prospective_pass_is_world_resource_discovery") is False,
      "canonical_axis_count_unchanged":candidate.get("phi_scan",{}).get("registered_axis_count")==canonical_axis_count(),
      "roadmap_next_discriminating_experiment":kernel.contract()["roadmap_dependency"]["next"]=="AUTOMATIC-DISCRIMINATING-EXPERIMENT",
    }
    passed=sum(bool(v) for v in checks.values())
    payload={
      "schema":SCHEMA,"release":RELEASE,"owner_id":"PHI-RESOURCE-THEORY-QUALIFICATION/1.0.0",
      "status":"PASS_PHI_RESOURCE_THEORY_QUALIFICATION" if passed==len(checks) else "BLOCKED_PHI_RESOURCE_THEORY_QUALIFICATION",
      "passed":passed,"total":len(checks),"checks":[{"check":k,"status":"PASS" if v else "FAIL"} for k,v in checks.items()],
      "demonstration":{"result":result,"negative_regime_shift":negative,"leakage_control":leakage,"insufficient_support":too_small,"named_resource_prefreeze_blocked":named_blocked},
      "claim_boundary":{"synthetic_qualification_is_world_resource_discovery":False,"world_resource_novelty_established":False,"internet_used_prefreeze":False,"known_resources_used_only_postfreeze":True,"canonical_axis_count":canonical_axis_count()},
    }
    payload["digest"]=digest_payload(payload); return payload

if __name__=="__main__": print(json.dumps(run_release_qualification(),ensure_ascii=False,indent=2,sort_keys=True))
