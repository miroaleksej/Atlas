"""Qualification for Φ-Automatic Discriminating Experiment 1.0.0."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping

from source.lawspace.discriminating_experiment import AutomaticDiscriminatingExperimentKernel
from source.lawspace.mathematical_invention import MathematicalInventionKernel
from source.lawspace.theory_compiler import TheoryCompilerKernel
from source.lawspace.schema import digest_payload
from source.lawspace.domains import canonical_axis_count

SCHEMA="phi-discriminating-experiment-qualification/v1"; RELEASE="10.6.0"


def _rows(kind: str):
    obs={"h0":"A","h1":"B","h2":"C"}
    maps={
      "candidate":{"a":{"h0":"h1","h1":"h2","h2":"h0"},"b":{"h0":"h1","h1":"h0","h2":"h2"}},
      "baseline1":{"a":{"h0":"h1","h1":"h2","h2":"h0"},"b":{"h0":"h0","h1":"h1","h2":"h2"}},
      "baseline2":{"a":{"h0":"h2","h1":"h0","h2":"h1"},"b":{"h0":"h1","h1":"h0","h2":"h2"}},
      "identical":{"a":{"h0":"h1","h1":"h2","h2":"h0"},"b":{"h0":"h1","h1":"h0","h2":"h2"}},
    }
    trans=maps[kind]
    rows=[]
    for s in sorted(obs):
        for a in sorted(trans):
            rows.append({"history_id":s,"action":a,"next_history_id":trans[a][s],"observation":obs[s]})
    return rows


def _compiled(root: Path, kind: str) -> Mapping[str, Any]:
    inv=MathematicalInventionKernel(root)
    primitive=inv.primitive.synthesize(transition_rows=_rows(kind),freeze_digest=digest_payload({"blind_theory":kind,"outcomes_seen":False}))
    if primitive.get("status")!="GENERATED_MINIMAL_ALGEBRAIC_PRIMITIVE":
        raise RuntimeError(primitive)
    return TheoryCompilerKernel(root).compiler.compile(theory_artifact=primitive,theory_freeze_digest=digest_payload({"primitive":primitive["digest"],"postfreeze":True}))


def run_release_qualification(root: str|Path|None=None)->dict[str,Any]:
    root=Path(root or Path(__file__).resolve().parents[1]); kernel=AutomaticDiscriminatingExperimentKernel(root)
    candidate=_compiled(root,"candidate"); b1=_compiled(root,"baseline1"); b2=_compiled(root,"baseline2")
    result=kernel.design(question="find an executable identifiable budget-feasible experiment that maximally separates a frozen generated theory from frozen baselines",candidate_theory=candidate,baseline_theories=(b1,b2),cost_budget=4.0)
    selection=result["selection"]; selected=selection.get("selected_experiment") or {}; freeze=result["frontier"]
    identical=_compiled(root,"identical")
    nondistinct=kernel.design(question="test observational equivalence",candidate_theory=candidate,baseline_theories=(identical,),cost_budget=4.0)
    low_budget=kernel.design(question="test under insufficient experimental budget",candidate_theory=candidate,baseline_theories=(b1,b2),cost_budget=2.0)
    tampered=dict(candidate); tampered["executable_id"]="E-TAMPERED"
    tamper=kernel.design(question="tampered compiled theory must fail",candidate_theory=tampered,baseline_theories=(b1,b2),cost_budget=4.0)
    frontier_rows=list(freeze.get("frozen",{}).get("frontier",()))
    admissible=[r for r in frontier_rows if r.get("executable") and r.get("cost_within_budget") and r.get("identifiable_against_all_baselines")]
    expected_best=sorted(admissible,key=lambda r:(-float(r["mean_predictive_divergence_bits"]),float(r["protocol_cost"]),str(r["experiment_id"])))[0] if admissible else None
    checks={
      "kernel_owner":kernel.contract()["owner_id"]=="PHI-AUTOMATIC-DISCRIMINATING-EXPERIMENT/1.0.0",
      "frontier_owner":kernel.frontier.contract()["owner_id"]=="DISCRIMINATING-EXPERIMENT-FRONTIER/1.0.0",
      "selection_owner":kernel.selection.contract()["owner_id"]=="DISCRIMINATING-EXPERIMENT-SELECTION/1.0.0",
      "attestation_bridge_owner":kernel.attestation_bridge.contract()["owner_id"]=="DISCRIMINATING-EXPERIMENT-ATTESTATION-BRIDGE/1.0.0",
      "candidate_compiled":candidate.get("status")=="THEORY_EXECUTABLE_COMPILED",
      "baselines_compiled":all(x.get("status")=="THEORY_EXECUTABLE_COMPILED" for x in (b1,b2)),
      "internal_phi_scan_all_current":freeze.get("phi_scan",{}).get("registered_axis_count")==canonical_axis_count() and freeze.get("phi_scan",{}).get("all_registered_axes_visited") is True,
      "no_fixed_owner_budget":freeze.get("phi_scan",{}).get("fixed_owner_visit_budget") is None,
      "no_fixed_axis_ceiling":freeze.get("phi_scan",{}).get("fixed_candidate_axis_order_ceiling") is None,
      "blind_firewall":freeze.get("phi_scan",{}).get("knowledge_firewall",{}).get("passport_names_used_for_source_scoring") is False,
      "frontier_frozen":freeze.get("status")=="DISCRIMINATING_EXPERIMENT_FRONTIER_FROZEN" and bool(freeze.get("freeze_digest")),
      "no_arbitrary_depth_ceiling":freeze.get("frozen",{}).get("frontier_generation")=="FINITE_JOINT_STATE_PRODUCT_CLOSURE_NO_ARBITRARY_DEPTH_CEILING",
      "frontier_nonempty":len(frontier_rows)>0,
      "selection_pass":selection.get("status")=="DISCRIMINATING_EXPERIMENT_SELECTED",
      "selected_content_addressed":str(selected.get("experiment_id","")).startswith("Q-") and len(selected.get("experiment_id",""))==18,
      "selected_executable":selected.get("executable") is True,
      "selected_identifiable":selected.get("identifiable_against_all_baselines") is True,
      "selected_within_budget":selected.get("cost_within_budget") is True and float(selected.get("protocol_cost",999))<=4.0,
      "selected_positive_divergence":float(selected.get("mean_predictive_divergence_bits",0))>0,
      "selection_is_actual_argmax":expected_best is not None and selected.get("experiment_id")==expected_best.get("experiment_id"),
      "predictions_runtime_derived":kernel.frontier.contract()["prediction_source"]=="EXECUTABLE_THEORY_RUNTIME_ONLY",
      "caller_prediction_table_forbidden":kernel.frontier.contract()["caller_prediction_tables_allowed"] is False,
      "internet_prefreeze_false":freeze.get("claim_boundary",{}).get("internet_used_prefreeze") is False,
      "world_result_not_seen":freeze.get("claim_boundary",{}).get("world_observation_inspected_before_selection") is False,
      "attestation_protocol_pending":result.get("attestation_bridge",{}).get("status")=="WORLD_ATTESTATION_PENDING_EXTERNAL_MEASUREMENT",
      "attestation_not_world_evidence":result.get("attestation_bridge",{}).get("claim_boundary",{}).get("protocol_is_world_evidence") is False,
      "nondistinct_control":nondistinct.get("status")=="OBSERVATIONALLY_NON_DISTINCT" and nondistinct.get("selection",{}).get("selected_experiment") is None,
      "nondistinct_no_promotion":nondistinct.get("selection",{}).get("theory_promotion_allowed") is False,
      "low_budget_fail_closed":low_budget.get("status")=="NO_FULLY_IDENTIFIABLE_EXPERIMENT_WITHIN_BUDGET",
      "tamper_blocked":tamper.get("frontier",{}).get("status")=="EXPERIMENT_FRONTIER_BLOCKED_UNQUALIFIED_EXECUTABLE",
      "world_falsification_not_claimed":result.get("claim_boundary",{}).get("world_theory_falsified") is False,
      "world_confirmation_not_claimed":result.get("claim_boundary",{}).get("world_theory_confirmed") is False,
      "world_novelty_not_claimed":result.get("claim_boundary",{}).get("world_novelty_established") is False,
      "next_roadmap_long_blind_cycle":kernel.contract()["roadmap_dependency"]["next"]=="LONG-HORIZON-BLIND-SCIENTIFIC-CYCLE",
    }
    passed=sum(bool(v) for v in checks.values()); payload={
      "schema":SCHEMA,"release":RELEASE,
      "status":"PASS_PHI_DISCRIMINATING_EXPERIMENT_QUALIFICATION" if passed==len(checks) else "BLOCKED_PHI_DISCRIMINATING_EXPERIMENT_QUALIFICATION",
      "passed":passed,"total":len(checks),"checks":[{"check":k,"status":"PASS" if v else "FAIL"} for k,v in checks.items()],
      "demonstration":{"result":result,"nondistinct_control":nondistinct,"low_budget_control":low_budget,"tamper_control":tamper},
      "claim_boundary":{"synthetic_qualification_is_world_falsification":False,"world_novelty_established":False,"internet_used_prefreeze":False},
    }
    payload["digest"]=digest_payload(payload); return payload

if __name__=="__main__":
    print(json.dumps(run_release_qualification(),ensure_ascii=False,indent=2,sort_keys=True))
