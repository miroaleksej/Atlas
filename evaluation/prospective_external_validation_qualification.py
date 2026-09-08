"""Qualification for real post-freeze external validation bridge.

The current real-world attempt is allowed to end BLOCKED.  PASS of this
qualification means the scientific gate behaved correctly, not that the frozen
P2X7 hypothesis was validated.
"""
from __future__ import annotations
import copy, json, tempfile
from pathlib import Path
from source.lawspace.prospective_external_validation import ProspectiveExternalScientificValidationKernel
from source.lawspace.schema import digest_payload
from evaluation.research_proof_qualification import run as run_research_proof

RELEASE='15.10.2'
SCHEMA='phi-prospective-external-validation-qualification/v1'

def run_release_qualification(root: str|Path|None=None):
    root=Path(root or Path(__file__).resolve().parents[1])
    kernel=ProspectiveExternalScientificValidationKernel(root)
    audit_path=root/'data/external/prospective_validation/p2x7_pd_external_audit_2026_08_31.json'
    proof=run_research_proof(root)
    candidate=dict(proof.get('prospective_discovery_gate',{}).get('candidate',{}) or {})
    freeze=kernel.freeze_internal_candidate(candidate)
    audit=json.loads(audit_path.read_text())
    real=kernel.gate.evaluate(freeze=freeze, external_audit=audit)

    # Synthetic controls exercise PASS/FAIL semantics only; they are explicitly
    # qualification fixtures and never become world evidence.
    pos=copy.deepcopy(audit)
    pos['sources']=[{
      'source_id':'QUAL-POS','primary_estimand_available':True,'primary_estimate':0.35,
      'confidence_interval_low':0.10,'confidence_interval_high':0.60,'prospective_after_candidate_freeze':True
    }]
    neg=copy.deepcopy(audit)
    neg['sources']=[{
      'source_id':'QUAL-NEG','primary_estimand_available':True,'primary_estimate':-0.30,
      'confidence_interval_low':-0.55,'confidence_interval_high':-0.05,'prospective_after_candidate_freeze':True
    }]
    p=kernel.gate.evaluate(freeze=freeze,external_audit=pos)
    n=kernel.gate.evaluate(freeze=freeze,external_audit=neg)
    switched=copy.deepcopy(audit); switched['candidate_id']='SWITCHED-AFTER-LOOKUP'
    s=kernel.gate.evaluate(freeze=freeze,external_audit=switched)

    checks={
      'owner_contract':kernel.contract().get('owner_id')=='PHI-PROSPECTIVE-EXTERNAL-SCIENTIFIC-VALIDATION/1.0.0',
      'current_internal_candidate_bound_without_historical_report':freeze.get('status')=='PROSPECTIVE_VALIDATION_FREEZE_BOUND' and freeze.get('claim_boundary',{}).get('historical_report_required') is False,
      'research_proof_candidate_bound':freeze.get('candidate',{}).get('freeze_digest')==candidate.get('freeze_digest') and bool(candidate.get('source_scan_digest')),
      'real_attempt_blocked_not_passed':real.get('status')=='BLOCKED_NO_ADMISSIBLE_PROSPECTIVE_MEASUREMENT',
      'real_primary_count_zero':real.get('admissible_primary_measurement_count')==0,
      'real_external_sources_present':real.get('external_source_count',0)>=5,
      'supportive_evidence_preserved':real.get('supportive_source_count',0)>=1,
      'supportive_not_primary':real.get('claim_boundary',{}).get('supportive_evidence_is_primary_validation') is False,
      'blocked_not_confirmation':real.get('claim_boundary',{}).get('blocked_status_is_candidate_confirmation') is False,
      'candidate_switch_forbidden':real.get('claim_boundary',{}).get('candidate_switch_allowed') is False,
      'positive_fixture_passes':p.get('status')=='PROSPECTIVE_EXTERNAL_VALIDATION_PASS',
      'negative_fixture_fails':n.get('status')=='PROSPECTIVE_EXTERNAL_VALIDATION_FAIL',
      'switch_fixture_blocked':s.get('status')=='BLOCKED_VALIDATION_CONTRACT_VIOLATION',
      'freeze_digest_bound':real.get('validation_freeze_digest')==freeze.get('validation_freeze_digest'),
      'candidate_digest_bound':real.get('candidate_freeze_digest')==freeze.get('candidate',{}).get('freeze_digest'),
      'internet_not_prefreeze':freeze.get('selection_policy',{}).get('internet_used_for_candidate_selection') is False,
    }
    payload={
      'schema':SCHEMA,'release':RELEASE,
      'status':'PASS_PHI_PROSPECTIVE_EXTERNAL_VALIDATION_QUALIFICATION' if all(checks.values()) else 'FAIL_PHI_PROSPECTIVE_EXTERNAL_VALIDATION_QUALIFICATION',
      'passed':sum(map(bool,checks.values())),'total':len(checks),
      'checks':[{'check':k,'status':'PASS' if v else 'FAIL'} for k,v in checks.items()],
      'real_world_attempt':real,
      'claim_boundary':{
        'qualification_pass_means_p2x7_candidate_validated':False,
        'real_external_validation_status':real.get('status'),
        'synthetic_controls_are_world_evidence':False,
        'candidate_switch_after_external_lookup_allowed':False,
        'historical_validation_freeze_report_required':False,
        'validation_freeze_built_from_current_digest_bound_internal_candidate':True,
      }
    }
    payload['digest']=digest_payload(payload)
    return payload

if __name__=='__main__': print(json.dumps(run_release_qualification(),ensure_ascii=False,indent=2,sort_keys=True))
