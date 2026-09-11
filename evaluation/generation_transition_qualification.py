"""Qualification for multi-candidate preregistration, generation boundaries and next-generation AI Phi-space search."""
from __future__ import annotations
import json
from pathlib import Path
from source.lawspace.generation_transition import GenerationTransitionKernel
from source.lawspace.schema import digest_payload
from source.lawspace.domains import canonical_axis_count

RELEASE="15.10.6"

def _candidate_rows(root: Path):
    """Derive a three-candidate prospective portfolio from current active research state.

    This qualification must not depend on reports removed from the sealed current
    system.  It selects current real-data mechanism candidates deterministically
    from the authoritative active frontier and binds every row to its content
    digest.  The portfolio tests preregistration mechanics; it does not promote
    any candidate or pretend a future measurement exists.
    """
    ledger = root / 'data/frontiers/ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl'
    rows = [json.loads(line) for line in ledger.read_text(encoding='utf-8').splitlines() if line.strip()]
    real = sorted(
        (row for row in rows if row.get('candidate_class') == 'REAL_DATA_MECHANISM_COMPETITION'),
        key=lambda row: str(row.get('candidate_id', '')),
    )
    if len(real) < 3:
        raise RuntimeError('current active frontier does not contain three real-data mechanism candidates')
    out=[]
    for row in real[:3]:
        payload=dict(row.get('payload',{})); cid=str(row.get('candidate_id',''))
        out.append({
          'candidate_id':cid,
          'source_freeze_digest':str(row.get('record_digest','')),
          'source_internal_freeze':'ATLAS_ACTIVE_CANDIDATES_CURRENT',
          'primary_estimand':'future discriminating measurement for '+str(payload.get('mechanism_family',cid)),
          'directional_prediction':str(payload.get('formula_source') or payload.get('low_frequency_anomaly_consequence') or 'FROZEN_CANDIDATE_SPECIFICATION'),
          'falsifier':'postfreeze discriminating measurement is incompatible with the frozen candidate prediction under its declared uncertainty contract',
          'data_window_start':'AFTER_PORTFOLIO_FREEZE',
          'candidate_status':'|'.join(str(x) for x in row.get('epistemic_statuses',())),
        })
    return out

def run_release_qualification(root: str|Path|None=None):
    root=Path(root or Path(__file__).resolve().parents[1])
    kernel=GenerationTransitionKernel(root)
    rows=_candidate_rows(root)
    import hashlib
    source_path=root/'data/frontiers/ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl'
    source_sha=hashlib.sha256(source_path.read_bytes()).hexdigest()
    portfolio=kernel.portfolio.freeze(candidates=rows,source_release='ATLAS_ACTIVE_CANDIDATES_CURRENT',source_release_sha256=source_sha)
    pending=kernel.portfolio.summarize_outcomes(portfolio,[
      {'candidate_id':rows[0]['candidate_id'],'status':'BLOCKED'},
      {'candidate_id':rows[1]['candidate_id'],'status':'BLOCKED'},
      {'candidate_id':rows[2]['candidate_id'],'status':'BLOCKED'},
    ])
    nextgen=kernel.search_next_generation()
    caps=json.loads((root/'capabilities.json').read_text())
    completion=kernel.completion.evaluate(portfolio=portfolio,nextgen=nextgen,current_claims=caps.get('claim_boundary',{}))
    bad_switch=False
    try:
      kernel.portfolio.summarize_outcomes(portfolio,[{'candidate_id':'AFTER_LOOKUP_SWITCH','status':'PASS'}])
    except ValueError: bad_switch=True
    selected=nextgen['selected_candidate']
    req=selected['requirement_map']
    gap_ids=sorted(str(x['capability_id']) for x in nextgen.get('architecture_gaps',()))
    anchor_ids=sorted(str(x) for x in nextgen.get('resolved_generation_anchors',()))
    checks={
      'kernel_contract':kernel.contract()['owner_id']=='PHI-GENERATION-TRANSITION-KERNEL/1.0.0',
      'portfolio_three_candidates':portfolio['candidate_count']==3,
      'portfolio_no_internet_selection':portfolio['selection_policy']['internet_used_for_candidate_selection'] is False,
      'portfolio_switch_forbidden':portfolio['selection_policy']['candidate_switch_after_measurement_allowed'] is False and bad_switch,
      'portfolio_waits_for_new_measurements':portfolio['measurement_program']['status']=='PREREGISTERED_AWAITING_NEW_POSTFREEZE_MEASUREMENTS',
      'blocked_not_counted_as_pass':pending['resolved_count']==0 and pending['directional_hit_rate'] is None,
      'nextgen_scans_all_registered_axes':nextgen['scan']['all_registered_axes_visited'] is True and nextgen['scan']['registered_axis_count']==canonical_axis_count(),
      'nextgen_no_fixed_search_ceiling':nextgen['scan']['fixed_owner_visit_budget'] is None and nextgen['scan']['fixed_candidate_axis_order_ceiling'] is None,
      'nextgen_internet_not_selector':nextgen['scan']['internet_used_prefreeze'] is False,
      'architecture_state_derived_from_live_capability_ledger':nextgen.get('architecture_gap_source')=='LIVE_CAPABILITY_LEDGER' and bool(gap_ids or anchor_ids),
      'collective_obligation_resolved_not_reopened':gap_ids==[] and anchor_ids==['collective_coordination'],
      'selected_requirements_equal_live_gap_or_anchor_ids':sorted(req)==sorted(gap_ids or anchor_ids),
      'semantic_grounding_receipts_present':all(len(str(v.get('semantic_digest','')))==64 for v in req.values()),
      'selected_has_owner_grounded_region':selected.get('grounded_requirement_count')==len(req),
      'state_derived_candidates_materialized':nextgen.get('candidate_count',0)>=1 and len(nextgen.get('frontier',()))>=1,
      'collective_holdout_not_used_for_selection':nextgen.get('collective_coordination_search',{}).get('holdout',{}).get('holdout_used_for_selection') is False,
      'selected_region_content_addressed':str(selected.get('candidate_id','')).startswith('NGAI-') and len(str(selected.get('digest','')))==64,
      'generated_architecture_class_not_hand_named':str(nextgen.get('selected_interpretation',{}).get('architecture_class','')).startswith('GENERATED_ARCHITECTURE_REGION-'),
      'no_hand_authored_requirement_axis_map':nextgen.get('claim_boundary',{}).get('hand_authored_requirement_axis_map_used') is False,
      'no_hand_authored_architecture_answer':nextgen.get('claim_boundary',{}).get('hand_authored_architecture_answer_used') is False,
      'selected_not_claimed_correct':nextgen['claim_boundary']['selected_candidate_is_proven_correct'] is False,
      'future_architecture_space_not_exhausted':nextgen['claim_boundary']['candidate_frontier_exhausts_future_architecture_space'] is False,
      'representation_expansion_only_for_ungrounded':all(x.get('requirement') in [k for k,v in req.items() if not v.get('owner_grounded')] for x in nextgen.get('representation_expansion_requests',())),
      'core_boundary_closed':completion['core_architecture_boundary']['status']=='GENERATION_CORE_ARCHITECTURE_CLOSED',
      'external_validation_still_open':completion['generation_validation_boundary']['status']=='GENERATION_NOT_EXTERNALLY_VALIDATED',
      'no_perfection_claim':completion['terminal_perfection_boundary']['status']=='NO_FINITE_PERFECTION_CLAIM',
    }
    payload={'schema':'phi-generation-transition-qualification/v2','release':RELEASE,
      'status':'PASS_PHI_GENERATION_TRANSITION_QUALIFICATION' if all(checks.values()) else 'FAIL_PHI_GENERATION_TRANSITION_QUALIFICATION',
      'passed':sum(bool(x) for x in checks.values()),'total':len(checks),
      'checks':[{'check':k,'status':'PASS' if v else 'FAIL'} for k,v in checks.items()],
      'portfolio':portfolio,'pending_outcomes':pending,'next_generation_search':nextgen,'completion_boundary':completion,
      'claim_boundary':{'nextgen_candidate_is_world_proven':False,'portfolio_candidates_validated':False,'perfect_ai_claimed':False}}
    payload['digest']=digest_payload(payload)
    return payload

if __name__=='__main__':
    print(json.dumps(run_release_qualification(),ensure_ascii=False,indent=2,sort_keys=True))
