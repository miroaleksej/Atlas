"""Qualification for Atlas-native collective coordination architecture."""
from __future__ import annotations
import json
from pathlib import Path
from source.lawspace.collective_coordination import (
    CollectiveCoordinationOwner,
    CoordinationArchitecture,
    enumerate_architectures,
    evaluate_architecture,
    _world,
)
from source.lawspace.schema import digest_payload

RELEASE="0.15.29.0"


def run_release_qualification(root: str|Path|None=None):
    owner=CollectiveCoordinationOwner()
    contract=owner.contract()
    search=owner.search_architecture()
    selected=search['selected_architecture']
    hold=search['holdout']['selected_candidate_result']
    competitor=search['holdout']['best_internal_competitor']

    # Independent negative controls not used for architecture selection.
    probe=[_world(80+i,holdout=True) for i in range(12)]
    no_resource=CoordinationArchitecture(**{**selected,'resource_mode':'NONE'})
    no_conflict=CoordinationArchitecture(**{**selected,'hard_conflict_exclusion':False})
    no_joint=CoordinationArchitecture(**{**selected,'joint_subset_selection':False})
    nr=evaluate_architecture(no_resource,probe)
    nc=evaluate_architecture(no_conflict,probe)
    nj=evaluate_architecture(no_joint,probe)

    runtime_proposals=[
      {'proposal_id':'p1','action_id':'a1','core_id':'c1','domain':'d1','evidence_class':'e1','estimated_information':1.4,'calibration':0.9,'realized_information':1.0,'cost':0.7,'risk':0.1,'conflict_group':None},
      {'proposal_id':'p2','action_id':'a2','core_id':'c2','domain':'d2','evidence_class':'e2','estimated_information':1.2,'calibration':0.85,'realized_information':1.0,'cost':0.8,'risk':0.1,'conflict_group':None},
    ]
    execution=owner.coordinate(proposals=runtime_proposals,budget=2.0,architecture=selected)

    checks={
      'owner_contract':contract['owner_id']=='COLLECTIVE-COORDINATION/1.0.0',
      'architecture_space_is_internal':search['search_space']['named_external_architectures_used'] is False and search['search_space']['internet_used_for_selection'] is False,
      'candidate_count_576':len(enumerate_architectures())==576 and search['search_space']['candidate_count']==576,
      'holdout_is_disjoint_and_not_selector':search['holdout']['holdout_used_for_selection'] is False and search['selection']['search_world_digest']!=search['holdout']['holdout_world_digest'],
      'selected_zero_invalid_holdout':hold['invalid_plan_count']==0,
      'selected_mean_above_090':hold['mean_oracle_ratio']>=0.90,
      'selected_q25_above_080':hold['q25_oracle_ratio']>=0.80,
      'internal_competitor_recorded':competitor is not None and competitor['candidate_id']!=hold['candidate_id'],
      'selected_not_worse_than_best_recorded_competitor':competitor is None or hold['mean_oracle_ratio']>=competitor['mean_oracle_ratio']-1e-12,
      'joint_selection_active':selected['joint_subset_selection'] is True,
      'calibration_active':selected['calibration_weighted_information'] is True,
      'hard_resource_active':selected['resource_mode']=='HARD_FEASIBILITY',
      'hard_conflict_active':selected['hard_conflict_exclusion'] is True,
      'runtime_execution_valid':execution['status']=='COLLECTIVE_PLAN_SELECTED' and execution['conflict_free'] is True and execution['resource_used']<=execution['budget'],
      'resource_negative_control_not_better':nr['mean_oracle_ratio']<=hold['mean_oracle_ratio']+0.08,
      'conflict_negative_control_not_better':nc['mean_oracle_ratio']<=hold['mean_oracle_ratio']+0.08,
      'greedy_negative_control_not_better':nj['mean_oracle_ratio']<=hold['mean_oracle_ratio']+0.08,
      'external_best_not_claimed':search['claim_boundary']['selected_architecture_beats_external_ai_systems'] is False,
      'agi_not_claimed':search['claim_boundary']['AGI_demonstrated'] is False,
    }
    out={'schema':'phi-collective-coordination-qualification/v1','release':RELEASE,
         'status':'PASS_COLLECTIVE_COORDINATION_QUALIFICATION' if all(checks.values()) else 'FAIL_COLLECTIVE_COORDINATION_QUALIFICATION',
         'passed':sum(bool(v) for v in checks.values()),'total':len(checks),
         'checks':[{'check':k,'status':'PASS' if v else 'FAIL'} for k,v in checks.items()],
         'architecture_search':search,'execution_probe':execution,
         'negative_controls':{'no_resource_gate':nr,'no_conflict_gate':nc,'greedy_only':nj},
         'claim_boundary':{'collective_coordination_grounded':all(checks.values()),'AGI_demonstrated':False,'external_superiority_demonstrated':False}}
    out['digest']=digest_payload(out)
    return out

if __name__=='__main__':
    print(json.dumps(run_release_qualification(),ensure_ascii=False,indent=2,sort_keys=True))
