#!/usr/bin/env python3
"""Thin evaluator for NEUTRINO-GLOBAL-COMBINATION current frozen candidate."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from source.lawspace.neutrino_global_combination import NeutrinoGlobalCombinationOwner, NeutrinoPostFreezeNoveltyAuditOwner

def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def main():
    p=argparse.ArgumentParser(); p.add_argument('--root',type=Path,default=ROOT); p.add_argument('--output',type=Path,required=True); a=p.parse_args()
    owner=NeutrinoGlobalCombinationOwner(a.root)
    report=dict(owner.run_qualification())
    scan=_load(a.root/'reports'/'neutrino_operator_fullspace_scan_current.json')
    partition=_load(a.root/'reports'/'neutrino_blind_data_partition_current.json')
    leader_id=partition['predeclared_leader_by_discovery_only']['candidate_id']
    frozen_row=next(row for row in scan['rows'] if row.get('candidate_id')==leader_id)
    falsification=owner.evaluate_frozen_discovery_candidate(frozen_row=frozen_row,freeze_gate=partition['freeze_gate'])
    novelty=NeutrinoPostFreezeNoveltyAuditOwner().evaluate(frozen_row=frozen_row,freeze_gate=partition['freeze_gate'],falsification_result=falsification)
    leader=partition['predeclared_leader_by_discovery_only']
    report['predeclared_frozen_cross_experiment_attempt']=falsification
    report['predeclared_internal_holdout_gate']={
        'candidate_id': leader_id,
        'selection_predeclared_from_discovery_only': True,
        'delta_discovery_chi2_vs_partition_reference': leader['delta_discovery_chi2_vs_partition_reference'],
        'delta_heldout_chi2_vs_partition_reference': leader['delta_heldout_chi2_vs_partition_reference'],
        'source_nuisance_refit_on_heldout': leader['source_nuisance_refit_on_heldout'],
        'status': 'FAILED_INTERNAL_HELDOUT_COMPARATIVE_GATE' if float(leader['delta_heldout_chi2_vs_partition_reference'])>0.0 else 'PASSED_INTERNAL_HELDOUT_COMPARATIVE_GATE',
        'promotion_allowed': False,
        'interpretation': 'COMPARATIVE_INTERNAL_VALIDATION_NOT_FORMAL_MODEL_REJECTION_SIGNIFICANCE',
    }
    report['postfreeze_novelty_audit_gate']=novelty
    report['claim_boundary']['predeclared_frozen_candidate_promoted']=False
    report['claim_boundary']['postfreeze_literature_audit_unlocked']=novelty['status'].startswith('READY_')
    report['claim_boundary']['frozen_blind_scan_regenerated_for_v6_10']=False
    report['sha256']=''
    from source.lawspace.schema import digest_payload
    report['sha256']=digest_payload({**report,'sha256':''})
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8'); print(json.dumps({'status':report['status'],'frozen_status':falsification['status'],'novelty_gate':novelty['status'],'output':str(a.output)},ensure_ascii=False))
if __name__=='__main__': main()
