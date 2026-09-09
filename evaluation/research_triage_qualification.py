from __future__ import annotations
import json
import tempfile
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from source.lawspace.research_triage import ResearchTriageSandbox


def run():
    t=ResearchTriageSandbox()
    strict=t.assess_data_quality(n_points=1201,relative_uncertainty=0.005,domain="physics")
    empirical=t.assess_data_quality(n_points=120,relative_uncertainty=0.04,domain="astronomy")
    exploratory=t.assess_data_quality(n_points=12,relative_uncertainty=0.02,domain="astronomy")
    noisy=t.assess_data_quality(n_points=5000,relative_uncertainty=0.15,domain="chemistry")
    h={"candidate_id":"H1","equation":"y=f(x)","rho_adj":0.08,"simplicity_score":0.9,"cross_consistency":0.8,"familywise_p":0.01,"uniqueness_score":0.75}
    rank=t.rank_hypotheses([h,{**h,"candidate_id":"H2","rho_adj":0.4}],dpi_threshold=0.7)
    plan=t.propose_what_if_experiments(axis_summaries=[{"axis_id":"x","observed_min":0,"observed_max":1,"target_min":-1,"target_max":2,"sensitivity":2,"relative_uncertainty":0.1}],count=2)
    state={"schema":"phi-hypothesis-council/v1","actions":[],"sandbox_weights":{"fit":.35,"simplicity":.2,"cross_consistency":.3,"fwer_penalty":.15},"revision":0}
    state=t.record_council_action(state=state,candidate_id="H1",action="SPONSOR_REVIEW",reason="known limit")
    checks={
        "STRICT_TIER":strict["quality_tag"]=="STRICT" and strict["canonical_promotion_allowed"] is True,
        "EMPIRICAL_TIER":empirical["quality_tag"]=="EMPIRICAL" and empirical["epistemic_status"]=="PHENOMENOLOGICAL_MODEL" and empirical["canonical_promotion_allowed"] is False,
        "EXPLORATORY_BY_SMALL_N":exploratory["quality_tag"]=="EXPLORATORY" and "BLOCK_U4" in exploratory["strict_pipeline_ceiling"],
        "EXPLORATORY_BY_NOISE":noisy["quality_tag"]=="EXPLORATORY",
        "DPI_RANKS_NOT_PROMOTES":rank["ranked"][0]["candidate_id"]=="H1" and rank["ranking_is_promotion"] is False,
        "WHAT_IF_TWO_POINTS":len(plan["experiments"])==2 and plan["world_result_observed"] is False,
        "MANUAL_OVERRIDE_FAIL_CLOSED":state["actions"][-1]["authoritative_u_gate_override"] is False and "NOT_U6_PASS" in state["actions"][-1]["effect"],
        "CONTRACT_OWNER_SEPARATION":t.contract()["authoritative_scientific_promotion_owner"]=="SCIENTIFIC-PROMOTION-CORE",
    }
    return {"schema":"phi-research-triage-qualification/v1","checks":checks,"passed":sum(checks.values()),"total":len(checks),"all_pass":all(checks.values())}

if __name__=="__main__":
    r=run(); print(json.dumps(r,ensure_ascii=False,indent=2)); raise SystemExit(0 if r["all_pass"] else 1)
