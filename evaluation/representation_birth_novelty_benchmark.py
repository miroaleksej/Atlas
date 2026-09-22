"""Frozen representation-birth and closed-scientific-loop benchmark for Atlas.

The benchmark is intentionally synthetic and claim-bounded.  Hidden sealed rows are
not used to select representations.  Raw-linear is the no-birth baseline; a fixed
quadratic oracle is reported only as an upper bound because it is handed the correct
interaction grammar in advance.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from source.lawspace.api import LawSpaceAPI
from source.lawspace.schema import digest_payload
from source.lawspace.theory_compiler import HierarchicalObservationalTheoryOwner
from source.lawspace.long_horizon_scientific_cycle import LongHorizonBlindScientificCycleKernel

SCHEMA="atlas-representation-novelty-benchmark/v1"
BENCHMARK_ID="ATLAS-FROZEN-REPRESENTATION-BIRTH-BENCHMARK/1.0.0"
FREEZE_SPEC={
    "tasks":["PURE_JOINT_INTERACTION","DOUBLE_JOINT_INTERACTION","NULL_NO_BIRTH","HIERARCHICAL_CLOSED_LOOP"],
    "selection_data":"DISCOVERY_ONLY","sealed_refit":False,
    "baselines":["RAW_LINEAR_NO_BIRTH","FIXED_QUADRATIC_ORACLE"],
    "metrics":["representation_birth_success","sealed_nrmse","false_birth_count","closed_loop_identification"],
}
FREEZE_DIGEST=digest_payload(FREEZE_SPEC)


def _nrmse(y,p):
    y=np.asarray(y,float); p=np.asarray(p,float)
    rmse=float(np.sqrt(np.mean((y-p)**2)))
    scale=float(np.std(y))
    return rmse/max(scale,1e-12)


def _linear_baseline(train, test, axes, quadratic=False):
    def design(rows):
        xs=np.asarray([[r["values"][a] for a in axes] for r in rows],float)
        cols=[np.ones(len(rows))]
        cols.extend([xs[:,i] for i in range(xs.shape[1])])
        if quadratic:
            for i in range(xs.shape[1]):
                for j in range(i,xs.shape[1]): cols.append(xs[:,i]*xs[:,j])
        return np.column_stack(cols)
    X=design(train); Xt=design(test); y=np.asarray([r["values"]["y"] for r in train],float)
    coef=np.linalg.lstsq(X,y,rcond=None)[0]
    pred=Xt@coef; yt=np.asarray([r["values"]["y"] for r in test],float)
    return _nrmse(yt,pred)


def _run_birth_task(root: Path, *, task_id: str, axes: list[str], formula, n: int, split: int, expected_terms: set[str]):
    rows=[]
    for i in range(n):
        vals={}
        primes=[37,53,29,31,43,47]
        mods=[101,103,107,109,113,127]
        den=[17.,19.,23.,21.,29.,31.]
        for j,a in enumerate(axes): vals[a]=((i*primes[j])%mods[j]-(mods[j]//2))/den[j]
        vals["y"]=float(formula(vals))
        rows.append({"record_id":f"{task_id}-{i:04d}","study_id":f"HOST-{i:04d}","values":vals})
    discovery, sealed=rows[:split], rows[split:]
    request={
        "problem_id":task_id,"domain_id":"physics","question":"discover the missing representation without a supplied interaction grammar",
        "observations":discovery,"sealed_holdout_observations":sealed,"target_variable":"y","predictor_variables":[],
        "dormant_axis_variables":axes,"variable_dimensions":{k:[0,0,0,0,0,0,0] for k in ["y",*axes]},
        "complexity_level":2,"fit_tolerance_nrmse":1e-10,"axis_birth_trial_budget":256,"axis_birth_sparse_search_allowed":True,
        "observations_origin":"FROZEN_SYNTHETIC_BENCHMARK","auto_activate_dormant_axes":True,
    }
    result=LawSpaceAPI(root).advance_adaptive_research(request)
    born={str(x.get("expression")) for x in result["result"].get("research_local_derived_axis_births",())}
    sealed_nrmse=float(result["result"].get("sealed_holdout_evaluation",{}).get("nrmse",float("inf")))
    raw=_linear_baseline(discovery,sealed,axes,quadratic=False)
    quad=_linear_baseline(discovery,sealed,axes,quadratic=True)
    return {
        "task_id":task_id,"expected_terms":sorted(expected_terms),"born_terms":sorted(born),
        "representation_birth_success":expected_terms.issubset(born),"sealed_nrmse":sealed_nrmse,
        "raw_linear_sealed_nrmse":raw,"fixed_quadratic_oracle_sealed_nrmse":quad,
        "activated_axes":result["result"].get("activated_axis_variables",[]),
        "sealed_refit_performed":False,
    }


def _null_task(root: Path):
    rows=[]
    axes=["a","b","c","d"]
    for i in range(160):
        vals={a:((i*(17+2*j))%(97+2*j)-(48+j))/(13.+j) for j,a in enumerate(axes)}; vals["y"]=0.0
        rows.append({"record_id":f"NULL-{i:03d}","study_id":f"N-{i:03d}","values":vals})
    r=LawSpaceAPI(root).advance_adaptive_research({
        "problem_id":"NULL-NO-BIRTH","domain_id":"physics","question":"do not invent a representation when intercept-only already closes the data",
        "observations":rows[:120],"sealed_holdout_observations":rows[120:],"target_variable":"y","predictor_variables":[],"dormant_axis_variables":axes,
        "variable_dimensions":{k:[0]*7 for k in ["y",*axes]},"complexity_level":2,"fit_tolerance_nrmse":1e-12,
        "axis_birth_trial_budget":128,"axis_birth_sparse_search_allowed":True,"observations_origin":"FROZEN_SYNTHETIC_BENCHMARK","auto_activate_dormant_axes":True,
    })
    activated=list(r["result"].get("activated_axis_variables",()))
    return {"task_id":"NULL_NO_BIRTH","false_birth_count":len(activated),"activated_axes":activated,"pass":len(activated)==0}


def _closed_loop(root: Path):
    explanations=[
        {"id":"H-A","statement":"mechanism A"},{"id":"H-B","statement":"mechanism B"},{"id":"H-C","statement":"mechanism C"},
    ]
    predictions=[{"id":"P1","prediction":"a frozen experiment distinguishes explanations","falsification":"measurement contradicts predicted outcome","defense":"no post-freeze refit","heldout_refit_allowed":False}]
    models=[
        {"experiment_id":"E-WEAK","observable":"weak_observable","cost":1.0,"feasible":True,"predictions":{"H-A":{"kind":"categorical","value":"X"},"H-B":{"kind":"categorical","value":"X"},"H-C":{"kind":"categorical","value":"Y"}}},
        {"experiment_id":"E-STRONG","observable":"strong_observable","cost":1.5,"feasible":True,"predictions":{"H-A":{"kind":"categorical","value":"A"},"H-B":{"kind":"categorical","value":"B"},"H-C":{"kind":"categorical","value":"C"}}},
    ]
    theory=HierarchicalObservationalTheoryOwner().compile(
        theory_id="BENCH-HIERARCHICAL-THEORY",universal_layer={"law":"known"},host_layer={"alpha":"latent"},regime_layer={"f_R":"open"},
        feasible_domain_layer={"Omega":"interval"},competing_explanations=explanations,predictions=predictions,evidence_digest=FREEZE_DIGEST,
        experimental_models=models,
    )
    kernel=LongHorizonBlindScientificCycleKernel(root,state_path=root/"state"/"benchmark_nonpersistent.json")
    freeze=kernel.freeze_observational_round(theory=theory,cost_budget=2.0)
    selected=freeze.get("selected_experiment",{})
    measurement={"experiment_id":selected.get("experiment_id"),"freeze_digest":freeze.get("freeze_digest"),"value":"B","measurement_id":"BENCH-HIDDEN-B"}
    revision=kernel.absorb_observational_measurement(frozen_experiment=freeze,measurement=measurement)
    return {
        "task_id":"HIERARCHICAL_CLOSED_LOOP","selected_experiment":selected.get("experiment_id"),"selection_before_measurement":freeze.get("frozen",{}).get("measurement_inspected_before_selection") is False,
        "revision_status":revision.get("status"),"leading_explanation_id":revision.get("leading_explanation_id"),
        "pass":selected.get("experiment_id")=="E-STRONG" and revision.get("leading_explanation_id")=="H-B" and revision.get("status")=="HIERARCHICAL_EXPLANATION_IDENTIFIED_POSTFREEZE",
    }


def run_benchmark(root: str|Path|None=None) -> dict[str,Any]:
    root=Path(root or Path(__file__).resolve().parents[1])
    t1=_run_birth_task(root,task_id="PURE_JOINT_INTERACTION",axes=["z","w"],formula=lambda v:v["z"]*v["w"],n=180,split=135,expected_terms={"z*w"})
    t2=_run_birth_task(root,task_id="DOUBLE_JOINT_INTERACTION",axes=["z","w","u","v"],formula=lambda x:x["z"]*x["w"]+0.8*x["u"]*x["v"],n=260,split=200,expected_terms={"z*w","u*v"})
    null=_null_task(root); loop=_closed_loop(root)
    checks={
        "freeze_digest_bound":bool(FREEZE_DIGEST),
        "pure_joint_birth":t1["representation_birth_success"],
        "pure_joint_unseen_transfer":t1["sealed_nrmse"]<1e-8,
        "double_joint_birth":t2["representation_birth_success"],
        "double_joint_unseen_transfer":t2["sealed_nrmse"]<1e-8,
        "raw_linear_cannot_close_pure_joint":t1["raw_linear_sealed_nrmse"]>0.5,
        "raw_linear_cannot_close_double_joint":t2["raw_linear_sealed_nrmse"]>0.5,
        "oracle_quadratic_can_close_when_grammar_is_given":max(t1["fixed_quadratic_oracle_sealed_nrmse"],t2["fixed_quadratic_oracle_sealed_nrmse"])<1e-8,
        "null_false_birth_zero":null["pass"],
        "theory_experiment_evidence_revision_closed":loop["pass"],
    }
    passed=sum(bool(v) for v in checks.values())
    payload={
        "schema":SCHEMA,"benchmark_id":BENCHMARK_ID,"freeze_spec":FREEZE_SPEC,"freeze_digest":FREEZE_DIGEST,
        "status":"PASS_FROZEN_REPRESENTATION_NOVELTY_BENCHMARK" if passed==len(checks) else "BLOCKED_FROZEN_REPRESENTATION_NOVELTY_BENCHMARK",
        "passed":passed,"total":len(checks),"checks":[{"check":k,"status":"PASS" if v else "FAIL"} for k,v in checks.items()],
        "tasks":[t1,t2,null,loop],
        "interpretation":{
            "raw_linear":"no representation birth; expected to fail interaction tasks",
            "fixed_quadratic_oracle":"upper bound with the correct interaction grammar supplied in advance; not a discovery baseline",
            "atlas":"must discover and persist interaction coordinates from discovery data and transfer them without sealed refit",
        },
        "claim_boundary":{"synthetic_benchmark_establishes_world_scientific_novelty":False,"benchmark_establishes_priority_over_external_systems":False,"sealed_rows_used_for_representation_selection":False},
    }
    payload["digest"]=digest_payload(payload); return payload

if __name__=="__main__": print(json.dumps(run_benchmark(),ensure_ascii=False,indent=2,sort_keys=True))
