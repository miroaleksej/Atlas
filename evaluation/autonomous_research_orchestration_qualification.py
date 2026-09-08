"""Current Human->Phi semantic, fresh-candidate-birth and Gamma qualification for 11.5.0."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from source.lawspace.api import LawSpaceAPI
from source.lawspace.candidates import CandidateGenerationPipeline, DirectedResearchQuery
from source.lawspace.research_cycle import RESEARCH_CYCLE_OWNER, SEMANTIC_QUESTION_OWNER, ScientificResearchCycleOwner, SemanticTypedQuestionOwner
from source.lawspace.runtime import LawSpaceRuntime
from source.lawspace.schema import digest_payload
from source.lawspace.domains import canonical_axis_count

RELEASE = "15.10.2"
SCHEMA = "phi-autonomous-research-orchestration-qualification/v3"

BLIND_CASES: tuple[dict[str, Any], ...] = (
    {"case_id":"Q-QUANTUM","question":"Найди неизвестную закономерность между декогеренцией, шумом и устойчивостью квантового вычисления без заранее заданной формы закона","expected_domains":("quantum_information_and_computational_methods",),"forbidden_active_domains":("pharmaceutical","aeronautics_and_aerostation")},
    {"case_id":"Q-NEUTRINO","question":"Исследуй связь осцилляций нейтрино, массового спектра и идентифицируемости модели без заранее выбранной теории","expected_domains":("physics",),"forbidden_active_domains":("pharmaceutical","aeronautics_and_aerostation")},
    {"case_id":"Q-BIOLOGY","question":"Исследуй связь генотипа, регуляторной сети и гомеостаза клетки без заранее заданного механизма","expected_domains":("biology",),"forbidden_active_domains":("pharmaceutical","aeronautics_and_aerostation")},
    {"case_id":"Q-CONTROL","question":"Исследуй связь причинности, наблюдаемости и устойчивости в распределенной системе управления без потери локальной автономии","expected_domains":("systems_control",),"forbidden_active_domains":("pharmaceutical","aeronautics_and_aerostation")},
    {"case_id":"Q-CROSS-DOMAIN","question":"Исследуй неизвестную связь между шумом измерения, причинной идентифицируемостью и квантовой динамикой без заранее выбранной модели","expected_domains":("physics","quantum_information_and_computational_methods","systems_control"),"forbidden_active_domains":("pharmaceutical","aeronautics_and_aerostation")},
)

BIRTH_CASES: tuple[dict[str, Any], ...] = (
    {"case_id":"B-MATH","question":"Find a new mathematical algebraic primitive without a named representation","expected_domains":("mathematics",),"expected_status":"CANDIDATE_BIRTH_CAPABILITY_GAP","expected_route":None},
    {"case_id":"B-PARTICLE","question":"Найди новую скалярную частицу в калибровочном пространстве без готовой модели","expected_domains":("physics",),"expected_status":"FRESH_CANDIDATE_SET_FROZEN","expected_route":"PARTICLESPACE_BLIND_DISCOVERY"},
    {"case_id":"B-NEUTRINO","question":"Найди новый операторный кандидат для осцилляций нейтрино без готовой модели","expected_domains":("physics",),"expected_status":"FRESH_CANDIDATE_SET_FROZEN","expected_route":"NEUTRINO_BLIND_DISCOVERY"},
    {"case_id":"B-CHEMISTRY","question":"Найди новую связанную структуру транспорта, реакции и поля в химической системе","expected_domains":("chemistry",),"expected_status":"FRESH_CANDIDATE_SET_FROZEN","expected_route":"DEEP_OWNER_HYPERGRAPH_BIRTH","execution":{"deep_target_axis_order":16}},
    {"case_id":"B-MATERIALS","question":"Исследуй новый механизм структуры материала и фазового перехода без готовой модели","expected_domains":("materials_science",),"expected_status":"CANDIDATE_BIRTH_CAPABILITY_GAP","expected_route":None},
    {"case_id":"B-BIOLOGY","question":"Исследуй новый механизм регуляторной сети и гомеостаза клетки без готовой модели","expected_domains":("biology",),"expected_status":"CANDIDATE_BIRTH_CAPABILITY_GAP","expected_route":None},
    {"case_id":"B-EARTH","question":"Исследуй новую закономерность климатической динамики земной системы без готовой модели","expected_domains":("earth_systems",),"expected_status":"CANDIDATE_BIRTH_CAPABILITY_GAP","expected_route":None},
    {"case_id":"B-CONTROL","question":"Найди новый кандидат для причинной наблюдаемости и устойчивости распределенной системы управления","expected_domains":("systems_control",),"expected_status":"CANDIDATE_BIRTH_CAPABILITY_GAP","expected_route":None},
    {"case_id":"B-QUANTUM","question":"Найди новую структуру декогеренции и устойчивости квантового вычисления","expected_domains":("quantum_information_and_computational_methods",),"expected_status":"CANDIDATE_BIRTH_CAPABILITY_GAP","expected_route":None},
)


def run_release_qualification(root: str | Path | None = None) -> dict[str, Any]:
    root = Path(root or Path(__file__).resolve().parents[1])
    runtime = LawSpaceRuntime(root)
    semantic = SemanticTypedQuestionOwner(runtime)
    cycle_owner = ScientificResearchCycleOwner(runtime)
    pipeline = CandidateGenerationPipeline(runtime.catalog, runtime.bridges)
    api = LawSpaceAPI(root)
    checks: dict[str, bool] = {}
    case_rows: list[dict[str, Any]] = []

    # Preserve the 11.4 semantic/frontier acceptance surface.
    for spec in BLIND_CASES:
        typed = semantic.interpret(spec["question"])
        required_domains = tuple(typed.get("required_domains", ()))
        directed = pipeline.directed_research(DirectedResearchQuery(
            question=spec["question"], required_observables=tuple(typed.get("required_observables", ())),
            target_axis_ids=tuple(typed.get("target_axis_ids", ())), required_domains=required_domains,
            include_all_connected_owners=False,
        ))
        active_rows = [row for row in directed.get("axis_rows", ()) if row.get("disposition") in {"OWNER_BOUND_ACTIVE","QUERY_DIRECT_OPEN_COORDINATE"}]
        active_domains = sorted({str(row.get("domain_id")) for row in active_rows})
        expected = tuple(spec["expected_domains"]); forbidden = set(spec["forbidden_active_domains"])
        semantic_ok = required_domains == expected
        all_axes_visited = directed.get("all_registered_axes_visited") is True and directed.get("registered_axis_count") == canonical_axis_count()
        frontier_guard = directed.get("relevance_contract", {}).get("mode") == "RELEVANCE_PRESERVING_FRONTIER"
        frontier_ok = frontier_guard and set(active_domains).issubset(set(required_domains)) and not (set(active_domains)&forbidden) and directed.get("relevance_contract", {}).get("bridge_may_expand_grounded_domain_set") is False
        checks[f"{spec['case_id']}_semantic"] = semantic_ok
        checks[f"{spec['case_id']}_all_axes_classified"] = all_axes_visited
        checks[f"{spec['case_id']}_frontier_relevance"] = frontier_ok
        case_rows.append({"case_id":spec["case_id"],"question":spec["question"],"expected_domains":list(expected),"required_domains":list(required_domains),"registered_axis_count":directed.get("registered_axis_count"),"all_registered_axes_visited":directed.get("all_registered_axes_visited"),"active_action_domain_set":active_domains,"active_axis_count":len(active_rows),"selected_bridge_ids":list(directed.get("selected_bridge_ids",())),"relevance_contract":directed.get("relevance_contract",{}),"semantic_status":typed.get("status"),"semantic_ok":semantic_ok,"frontier_ok":frontier_ok})

    autonomous_rows=[]
    for case_id in ("Q-QUANTUM","Q-CONTROL"):
        spec=next(row for row in BLIND_CASES if row["case_id"]==case_id)
        result=api.run_autonomous_research({"question":spec["question"],"commit_resident_state":False})
        domains=tuple(result.get("semantic_typed_ir",{}).get("required_domains",()))
        status=str(result.get("status","")); fail_closed=status.startswith("AUTONOMOUS_RESEARCH_GAP_") or status=="AUTONOMOUS_RESEARCH_BLOCKED_FAIL_CLOSED"
        no_invention=result.get("claim_boundary",{}).get("missing_likelihoods_invented") is False and result.get("claim_boundary",{}).get("missing_evidence_invented") is False and result.get("claim_boundary",{}).get("sealed_release_mutated_by_resident_state") is False
        active_domains=sorted({str(row.get("axis_id","")).split(".",1)[0] for row in result.get("open_world",{}).get("freeze",{}).get("action_frontier",()) if row.get("axis_id")})
        expected=tuple(spec["expected_domains"])
        checks[f"{case_id}_autonomous_fail_closed"] = domains==expected and fail_closed and no_invention and set(active_domains).issubset(set(expected))
        autonomous_rows.append({"case_id":case_id,"required_domains":list(domains),"active_action_domain_set":active_domains,"status":status,"candidate_birth_status":result.get("research_cycle",{}).get("candidate_birth",{}).get("status"),"representation_status":result.get("representation_invention",{}).get("status"),"primitive_status":result.get("primitive_synthesis",{}).get("status"),"next_required_external_input":result.get("next_required_external_input"),"fail_closed":fail_closed,"missing_evidence_or_likelihood_invented":not no_invention})

    checks["semantic_owner_v2"] = SEMANTIC_QUESTION_OWNER == "SEMANTIC-TYPED-QUESTION/2.0.0"
    checks["research_owner_15_2"] = RESEARCH_CYCLE_OWNER == "SCIENTIFIC-RESEARCH-CYCLE/15.2.8"
    semantic_check_names=list(checks)

    baseline_ids={str(row.get("candidate_id")) for row in runtime.candidates}
    birth_rows=[]; chemistry_candidate=None
    for spec in BIRTH_CASES:
        typed=semantic.interpret(spec["question"]); domains=tuple(typed.get("required_domains",()))
        result=cycle_owner.run(question=spec["question"],required_domains=domains,target_axis_ids=tuple(typed.get("target_axis_ids",())),required_observables=tuple(typed.get("required_observables",())),include_all_connected_owners=False,fresh_candidate_birth=True,semantic_ir=typed,candidate_birth_execution=spec.get("execution"))
        birth=result["candidate_birth"]; selected=birth.get("selected_capability") or {}; route=selected.get("route")
        fresh_ids=[str(row.get("candidate_id")) for row in birth.get("fresh_candidates",())]
        semantic_ok=domains==tuple(spec["expected_domains"])
        resolver_ok=birth.get("status")==spec["expected_status"] and route==spec["expected_route"] and birth.get("claim_boundary",{}).get("materialized_2771_used_as_fresh_fallback") is False
        freshness_ok=(all(cid not in baseline_ids for cid in fresh_ids) and len(fresh_ids)>0) if spec["expected_status"]=="FRESH_CANDIDATE_SET_FROZEN" else (len(fresh_ids)==0 and result["competitive_set"].get("candidate_count")==0)
        checks[f"{spec['case_id']}_semantic"] = semantic_ok
        checks[f"{spec['case_id']}_resolver"] = resolver_ok
        checks[f"{spec['case_id']}_fresh_or_gap"] = freshness_ok
        birth_rows.append({"case_id":spec["case_id"],"question":spec["question"],"required_domains":list(domains),"birth_status":birth.get("status"),"selected_route":route,"fresh_candidate_count":len(fresh_ids),"fresh_candidate_ids":fresh_ids,"competitive_set_status":result["competitive_set"].get("status"),"materialized_2771_used_as_fresh_fallback":birth.get("claim_boundary",{}).get("materialized_2771_used_as_fresh_fallback")})
        if spec["case_id"]=="B-CHEMISTRY" and birth.get("fresh_candidates"):
            chemistry_candidate=birth["fresh_candidates"][0]

    gamma = cycle_owner.close_deep_candidate_gamma(chemistry_candidate) if chemistry_candidate else {"status":"NOT_RUN","gates":{},"claim_boundary":{}}
    gamma_status = gamma.get("status")
    gamma_gates = dict(gamma.get("gates", {}))
    pre_prediction_gates = {k:v for k,v in gamma_gates.items() if k not in {"STRUCTURAL_ACTIONS_SEPARATED","DISCRIMINATING_STRUCTURAL_PREDICTIONS"}}
    prediction_complete = all(bool(v) for k,v in gamma_gates.items() if k in {"STRUCTURAL_ACTIONS_SEPARATED","DISCRIMINATING_STRUCTURAL_PREDICTIONS"})
    checks["GAMMA_structured_closure_or_fail_closed"] = gamma_status in {"STRUCTURAL_GAMMA_CLOSURE_CANDIDATE_FROZEN","GAMMA_CLOSURE_INCOMPLETE_FAIL_CLOSED"}
    checks["GAMMA_pre_prediction_internal_gates_pass"] = bool(pre_prediction_gates) and all(pre_prediction_gates.values())
    checks["GAMMA_prediction_gate_honest"] = (gamma_status=="STRUCTURAL_GAMMA_CLOSURE_CANDIDATE_FROZEN" and prediction_complete) or (gamma_status=="GAMMA_CLOSURE_INCOMPLETE_FAIL_CLOSED" and not prediction_complete)
    checks["GAMMA_no_named_coupled_pde"] = gamma.get("claim_boundary",{}).get("named_coupled_pde_selected") is False and gamma.get("claim_boundary",{}).get("internet_used_prefreeze") is False
    checks["GAMMA_world_claims_blocked"] = gamma.get("claim_boundary",{}).get("physical_coupling_established") is False and gamma.get("claim_boundary",{}).get("new_physical_law_established") is False and gamma.get("claim_boundary",{}).get("world_novelty_established") is False

    semantic_passed=sum(bool(checks[k]) for k in semantic_check_names)
    birth_names=[k for k in checks if k not in semantic_check_names and not k.startswith("GAMMA_")]
    gamma_names=[k for k in checks if k.startswith("GAMMA_")]
    passed=sum(bool(v) for v in checks.values())
    out={
        "schema":SCHEMA,"release":RELEASE,"owner":RESEARCH_CYCLE_OWNER,"semantic_owner":SEMANTIC_QUESTION_OWNER,
        "status":"PASS_UNIVERSAL_FRESH_CANDIDATE_BIRTH_AND_GAMMA_CLOSURE" if passed==len(checks) else "FAIL_UNIVERSAL_FRESH_CANDIDATE_BIRTH_AND_GAMMA_CLOSURE",
        "passed":passed,"total":len(checks),"checks":checks,
        "semantic_frontier":{"passed":semantic_passed,"total":len(semantic_check_names),"blind_cases":case_rows,"autonomous_execution_cases":autonomous_rows},
        "candidate_birth":{"passed":sum(bool(checks[k]) for k in birth_names),"total":len(birth_names),"blind_cases":birth_rows},
        "gamma_closure":{"passed":sum(bool(checks[k]) for k in gamma_names),"total":len(gamma_names),"receipt":gamma},
        "claim_boundary":{"blind_cases_are_acceptance_ground_truth_not_runtime_answer_map":True,"runtime_hand_authored_domain_answer_map_used":False,"all_registered_axes_are_classified_not_continuous_cartesian_exhausted":True,"new_scientific_law_claimed":False,"universal_human_language_understanding_claimed":False,"external_source_used_prefreeze":False,"materialized_2771_used_as_fresh_fallback":False,"gamma_structural_execution_implies_world_truth":False}
    }
    out["digest"]=digest_payload(out)
    return out

if __name__=="__main__":
    print(json.dumps(run_release_qualification(),ensure_ascii=False,indent=2,sort_keys=True))
