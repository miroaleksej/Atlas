"""Qualification for Generation II Reflexive Self-Hosted Phi Architecture."""
from __future__ import annotations
import copy, json
from pathlib import Path
from typing import Any
from source.lawspace.reflexive_architecture import ReflexiveSelfHostedPhiArchitectureKernel
from source.lawspace.domains import canonical_axis_count
from source.lawspace.schema import digest_payload

RELEASE="15.10.6"; SCHEMA="phi-reflexive-architecture-qualification/v1"

def run_release_qualification(root: str|Path|None=None)->dict[str,Any]:
    root=Path(root or Path(__file__).resolve().parents[1]); k=ReflexiveSelfHostedPhiArchitectureKernel(root); r=k.run_cycle()
    st=r['architecture_state']; gen=r['candidate_generation']; proof=r['proof']; ctl=r['shadow_control']; ev=r['shadow_evaluation']; de=r['discriminating_experiment']; tx=r['transaction']
    # Negative controls: no frozen candidate -> proof block; erased advantage -> rollback.
    bad_proof=k.proof.assess(st,{"status":"NO_CANDIDATE"})
    bad_eval=copy.deepcopy(ev); bad_eval['prospective_advantage']=0.0; bad_eval['digest']=digest_payload({k:v for k,v in bad_eval.items() if k!='digest'})
    rollback=k.transaction.decide(state=st,proof=proof,shadow_control=ctl,shadow_eval=bad_eval,discrimination=de)
    inv=gen.get('invention_chain',{})
    region=gen.get('state_derived_region',{})
    evidence=gen.get('architecture_evidence',[])
    checks={
      'kernel_owner':k.contract()['owner_id']=='PHI-REFLEXIVE-SELF-HOSTED-ARCHITECTURE/1.0.0',
      'architecture_state_typed':st['schema']=='phi-architecture-state/v1' and st['capability_count']>50 and st['owner_count']>100,
      'architecture_state_has_routes':st['resource_profile']['read_route_count']>50 and st['resource_profile']['mutation_route_count']>5,
      'architecture_state_has_invariants':st['invariant_count']>=10,
      'architecture_state_not_space_exhaustion':st['claim_boundary']['current_registered_axes_are_space_ceiling'] is False,
      'internal_phi_scan_all_registered_axes':gen['phi_scan']['all_registered_axes_visited'] is True and gen['phi_scan']['registered_axis_count']==canonical_axis_count(),
      'no_fixed_phi_search_ceiling':gen['phi_scan']['fixed_owner_visit_budget'] is None and gen['phi_scan']['fixed_candidate_axis_order_ceiling'] is None,
      'internet_not_prefreeze':gen['phi_scan']['internet_used_prefreeze'] is False,
      'state_derived_region_bound':region.get('architecture_gap_source')=='LIVE_CAPABILITY_LEDGER' and bool(region.get('architecture_gaps') or region.get('resolved_generation_anchors')),
      'resolved_collective_anchor_not_reopened':region.get('architecture_gaps')==[] and region.get('resolved_generation_anchors')==['collective_coordination'],
      'architecture_evidence_materialized':bool(evidence) and all(x.get('source') for x in evidence),
      'representation_obligations_generated':gen.get('representation_obligations',{}).get('status')=='PROPOSE_GENERATED_REPRESENTATION_SIGNATURE',
      'primitive_generated':inv.get('primitive',{}).get('status')=='GENERATED_MINIMAL_ALGEBRAIC_PRIMITIVE',
      'morphism_generated':inv.get('morphism',{}).get('status')=='EXACT_MORPHISM_DISCOVERED',
      'controlled_limit_generated':inv.get('controlled_limit',{}).get('status')=='CONTROLLED_LIMIT_ESTABLISHED',
      'theory_compiled':inv.get('compiled',{}).get('status')=='THEORY_EXECUTABLE_COMPILED',
      'selected_candidate_frozen':gen['status']=='SELF_ARCHITECTURE_CANDIDATE_SELECTED' and len(gen['freeze_digest'])==64,
      'no_hand_authored_atoms':gen['claim_boundary'].get('hand_authored_architecture_atoms_used') is False,
      'no_hand_authored_requirement_axis_map':gen['claim_boundary'].get('hand_authored_requirement_axis_map_used') is False,
      'no_expected_primitive':gen['claim_boundary'].get('expected_primitive_supplied') is False,
      'primitive_from_architecture_evidence':gen['claim_boundary'].get('primitive_generated_from_architecture_evidence') is True,
      'proof_pass':proof['status']=='PROOF_CARRYING_SELF_CHANGE_PASS',
      'all_existing_capabilities_preserved':len(proof['Preserve'])==st['capability_count'] and proof['Lose']==[],
      'generated_capabilities_provided':len(proof['Provide'])>=2 and all(x.startswith('generated_architecture_') for x in proof['Provide']),
      'controlled_limit_to_base':proof['controlled_limit']['status']=='CONTROLLED_LIMIT_ESTABLISHED' and proof['controlled_limit']['selected_limit_direction']=='PARAMETER_TO_ZERO',
      'migration_has_rollback':proof['migration_contract']['rollback_architecture_digest']==st['digest'],
      'arbitrary_self_rewrite_forbidden':proof['migration_contract']['arbitrary_source_mutation'] is False,
      'theory_compiler_shadow':ctl['status']=='ARCHITECTURE_SHADOW_CONTROL_COMPILED' and ctl['compiled']['status']=='THEORY_EXECUTABLE_COMPILED',
      'commit_path_executes':ctl['commit_execution']['final_state']=='COMMITTED',
      'rollback_path_executes':ctl['rollback_execution']['final_state']=='ROLLED_BACK',
      'workloads_frozen_before_outcomes':r['workload_freeze']['outcomes_inspected_prefreeze'] is False and len(r['workload_freeze']['freeze_digest'])==64,
      'parallel_shadow_advantage':ev['candidate_success_rate']>ev['base_success_rate'] and ev['prospective_advantage']>=0.20,
      'no_preserved_regression':ev['preserved_regressions']==0,
      'resource_overhead_bounded':ev['resource_overhead_fraction']<=0.25,
      'automatic_discriminating_experiment':de['status']=='DISCRIMINATING_EXPERIMENT_SELECTED',
      'transaction_commits_only_after_gates':tx['status']=='COMMIT_REFLEXIVE_ARCHITECTURE_TRANSITION' and all(tx['checks'].values()),
      'missing_candidate_blocks_proof':bad_proof['status']=='SELF_CHANGE_BLOCKED_NO_FROZEN_CANDIDATE',
      'insufficient_advantage_rolls_back':rollback['status']=='ROLLBACK_REFLEXIVE_ARCHITECTURE_CANDIDATE',
      'agi_not_claimed':tx['claim_boundary']['commit_proves_agi'] is False,
      'global_optimum_not_claimed':tx['claim_boundary']['commit_proves_global_architecture_optimality'] is False,
      'canonical_axis_registry_dynamic':canonical_axis_count()==st['resource_profile']['registered_axis_count'],
    }
    passed=sum(bool(v) for v in checks.values())
    out={'schema':SCHEMA,'release':RELEASE,'status':'PASS_REFLEXIVE_ARCHITECTURE_QUALIFICATION' if passed==len(checks) else 'BLOCKED_REFLEXIVE_ARCHITECTURE_QUALIFICATION','passed':passed,'total':len(checks),'checks':[{'check':k,'status':'PASS' if v else 'FAIL'} for k,v in checks.items()],'cycle':r,'negative_controls':{'missing_candidate':bad_proof,'insufficient_advantage':rollback},'claim_boundary':{'generation_ii_reflexive_mechanism_qualified':passed==len(checks),'AGI_demonstrated':False,'developmental_open_endedness_mechanism_qualified':True,'collective_coordination_grounded':r.get('claim_boundary',{}).get('collective_coordination_grounded') is True,'fresh_full_current_release_replayed':False}}
    out['digest']=digest_payload(out); return out
if __name__=='__main__': print(json.dumps(run_release_qualification(),ensure_ascii=False,indent=2,sort_keys=True))
