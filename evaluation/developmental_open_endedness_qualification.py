"""Qualification for Generation II developmental open-endedness discovery."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from source.lawspace.developmental_open_endedness import DevelopmentalOpenEndednessKernel, SHADOW_DEVELOPMENTAL_METRICS
from source.lawspace.domains import canonical_axis_count
from source.lawspace.schema import digest_payload

RELEASE='15.10.2';SCHEMA='phi-developmental-open-endedness-qualification/v1'

def run_release_qualification(root:str|Path|None=None)->dict[str,Any]:
    root=Path(root or Path(__file__).resolve().parents[1]); k=DevelopmentalOpenEndednessKernel(root); r=k.run_cycle()
    sel=r['selection']; cand=sel['selected_candidate']; bind=r['primitive_binding']; comp=r['compiled']; shadow=r['shadow']; tx=r['transaction']
    mechanisms=list(cand.get('mechanisms',[]))
    single_drop=[]
    for m in mechanisms:
        rr=k.shadow.evaluate(selection=sel,workload_freeze=r['workload_freeze'],disabled=(m,))
        single_drop.append({'mechanism':m,'status':rr['status'],'coverage':rr['coverage_after_dropout']})
    cov=cand.get('coverage',{})
    weakest=min(cov, key=lambda x: (len(cov[x]), x)) if cov else None
    weakest_support=list(cov.get(weakest,[])) if weakest else []
    double_drop=k.shadow.evaluate(selection=sel,workload_freeze=r['workload_freeze'],disabled=tuple(weakest_support))
    rollback=k.transaction.decide(selection=sel,binding=bind,compiled=comp,shadow=double_drop)
    bio=sel.get('biology_axis_status',[])
    feature_obligations=list(cand.get('feature_obligations',[]))
    checks={
      'kernel_owner':k.contract()['owner_id']=='PHI-DEVELOPMENTAL-OPEN-ENDEDNESS/1.0.0',
      'all_registered_axes_scanned':sel['phi_scan']['registered_axis_count']==canonical_axis_count() and sel['phi_scan']['all_registered_axes_visited'] is True,
      'no_fixed_search_ceiling':sel['phi_scan']['fixed_owner_visit_budget'] is None and sel['phi_scan']['fixed_candidate_axis_order_ceiling'] is None,
      'internet_not_prefreeze':sel['phi_scan']['internet_used_prefreeze'] is False,
      'qualified_mechanism_pool_large':sel['qualified_mechanism_candidate_count']>=40,
      'candidate_frozen':sel['status']=='DEVELOPMENTAL_CANDIDATE_FROZEN' and len(sel['freeze_digest'])==64,
      'state_derived_features_present':len(feature_obligations)>=3 and set(feature_obligations)==set(cand['coverage']),
      'exact_minimum_redundant_cover':cand['status']=='EXACT_MINIMUM_REDUNDANT_COVER_FOUND' and cand['component_count']>=2,
      'two_covers_each':all(len(cand['coverage'][o])>=2 for o in feature_obligations),
      'shadow_metrics_not_used_for_birth':sel['claim_boundary'].get('developmental_shadow_metrics_used_for_candidate_birth') is False,
      'no_hand_authored_obligation_tokens':sel['claim_boundary'].get('hand_authored_developmental_obligation_token_map_used') is False,
      'no_named_evolutionary_answer':not any(any(t in m.lower() for t in ('genetic_algorithm','evolutionary_algorithm','neural_architecture')) for m in mechanisms),
      'primitive_generated':bind['primitive']['status']=='GENERATED_MINIMAL_ALGEBRAIC_PRIMITIVE',
      'primitive_finite_minimality':bind['primitive']['minimality_certificate']['all_distinct_carrier_pairs_behaviorally_separated'] is True,
      'morphism_discovered':bind['morphism']['status']=='EXACT_MORPHISM_DISCOVERED',
      'morphism_preserves_update_observe':'observe' in bind['morphism']['morphism']['Preserve'] and 'typed_update_commutation' in bind['morphism']['morphism']['Preserve'],
      'controlled_limit':bind['controlled_limit']['status']=='CONTROLLED_LIMIT_ESTABLISHED' and bind['controlled_limit']['selected_limit_direction']=='PARAMETER_TO_ZERO',
      'theory_compiled':comp['status']=='DEVELOPMENTAL_THEORY_COMPILED' and comp['compiled']['status']=='THEORY_EXECUTABLE_COMPILED',
      'workloads_frozen':len(r['workload_freeze']['freeze_digest'])==64 and all(x['outcome_inspected_prefreeze'] is False for x in r['workload_freeze']['workloads']),
      'shadow_pass':shadow['status']=='DEVELOPMENTAL_SHADOW_PASS',
      'all_postfreeze_metrics_pass':all(shadow['developmental_metrics'].get(x) is True for x in SHADOW_DEVELOPMENTAL_METRICS),
      'bounded_active_budget':len(shadow['lineage']['active_units'])<=shadow['lineage']['active_budget'] and len(shadow['lineage']['retired_units'])>0,
      'single_component_dropout_tolerated':all(x['status']=='DEVELOPMENTAL_SHADOW_PASS' for x in single_drop),
      'double_support_dropout_fails':weakest is not None and double_drop['status']=='DEVELOPMENTAL_SHADOW_FAIL' and double_drop['coverage_after_dropout'].get(weakest)==0,
      'positive_commit':tx['status']=='COMMIT_DEVELOPMENTAL_OPEN_ENDEDNESS_CAPABILITY' and all(tx['checks'].values()),
      'negative_rollback':rollback['status']=='ROLLBACK_DEVELOPMENTAL_OPEN_ENDEDNESS_CANDIDATE',
      'collective_remains_next':r['next_research_obligation']=='COLLECTIVE_COORDINATION',
      'unbounded_world_not_claimed':r['claim_boundary']['unbounded_external_open_endedness_established'] is False,
      'canonical_axis_registry_dynamic':canonical_axis_count()==sel['phi_scan']['registered_axis_count'],
    }
    passed=sum(bool(v) for v in checks.values())
    out={'schema':SCHEMA,'release':RELEASE,'status':'PASS_DEVELOPMENTAL_OPEN_ENDEDNESS_QUALIFICATION' if passed==len(checks) else 'BLOCKED_DEVELOPMENTAL_OPEN_ENDEDNESS_QUALIFICATION','passed':passed,'total':len(checks),'checks':[{'check':k,'status':'PASS' if v else 'FAIL'} for k,v in checks.items()],'cycle':r,'negative_controls':{'single_component_dropout':single_drop,'double_inheritance_dropout':double_drop,'rollback':rollback},'claim_boundary':{'developmental_open_endedness_mechanism_qualified':passed==len(checks),'unbounded_world_open_endedness_proven':False,'biological_evolution_claimed':False,'collective_coordination_grounded':False,'fresh_full_current_release_replayed':False}}
    out['digest']=digest_payload(out);return out
if __name__=='__main__':print(json.dumps(run_release_qualification(),ensure_ascii=False,indent=2,sort_keys=True))
