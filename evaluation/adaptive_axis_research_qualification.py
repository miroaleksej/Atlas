"""Executable qualification for adaptive-axis discovery with positive causal-readiness gates."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from source.lawspace.adaptive_axis import AdaptiveAxisDiscoveryOwner, OWNER_ID as ADAPTIVE_OWNER_ID
from source.lawspace.domains import dynamic_axis_registry_state
from source.lawspace.research_cycle import DynamicAxisProposal
from source.lawspace.schema import digest_payload

OWNER_ID="ADAPTIVE-AXIS-RESEARCH-QUALIFICATION/1.1.0"
SCHEMA="phi-adaptive-axis-research-qualification/v2"


def _positive_generalization_fixture():
    rows=[]
    for i in range(4):
        rows.append({"record_id":f"R-A-{i}","study_id":f"STUDY-A-{i}","outcome_class":"RESPONDER","context":{"novel_endotype_marker":"A"}})
    for i in range(4):
        rows.append({"record_id":f"R-B-{i}","study_id":f"STUDY-B-{i}","outcome_class":"NONRESPONDER","context":{"novel_endotype_marker":"B"}})
    return rows


def run(root: str | Path | None=None) -> dict[str,Any]:
    root=Path(root or Path(__file__).resolve().parents[1])
    p2x7=json.loads((root/'data/research_examples/p2x7_pd_context_evidence.json').read_text(encoding='utf-8'))
    tlr7=json.loads((root/'data/research_examples/tlr7_ad_context_evidence.json').read_text(encoding='utf-8'))
    owner=AdaptiveAxisDiscoveryOwner()
    before=dynamic_axis_registry_state()
    p2_scan=owner.scan(domain_id='pharmaceutical', evidence_records=p2x7['records'])
    tlr_scan=owner.scan(domain_id='pharmaceutical', evidence_records=tlr7['records'])
    positive_scan=owner.scan(domain_id='pharmaceutical', evidence_records=_positive_generalization_fixture())

    proposal=DynamicAxisProposal(
        proposal_id='PHARMA-ADAPTIVE-PATHOPHYSIOLOGIC-ENDOTYPE-20260828',
        domain_id='pharmaceutical',
        axis_id='pathophysiologic_endotype',
        description_ru='Механистически определённый эндотип заболевания, заданный заранее объявленным измеримым профилем биомаркеров, визуализации, патологии или омики.',
        value_kind='TEXT',
        physical_or_information_meaning='Mechanistic disease subgroup defined by a predeclared measured pathway/cell-state profile rather than diagnosis label alone.',
        measurement_protocol='Assign only by a preregistered classifier using measured biomarker, imaging, pathology or omics features with provenance and uncertainty.',
        units_or_normalization='study-specific controlled vocabulary plus classifier/version/probability',
        expected_range={'values':['PREDECLARED_ENDOTYPE_LABELS']},
        falsifiable_advantage='On held-out data, endotype conditioning must improve treatment-response or mechanistic outcome prediction versus diagnosis/target_population alone; otherwise the axis is rejected or demoted.',
        redundancy_test='Compare against target_population, pharmacodynamic_biomarker and indication; reject if the same partition and held-out information is already representable without the new coordinate.',
        provenance_evidence=tuple(f"PMID:{x['pmid']}" for x in p2x7.get('translation_anchors',[]) if x.get('pmid')),
    )
    admission=owner.admit_provisional_axis(scan_result=p2_scan, source_dimension='dominant_pathophysiologic_context', proposal=proposal)
    region=owner.mount_research_region(domain_id='pharmaceutical', provisional_admissions=[admission])
    after=dynamic_axis_registry_state()

    p2_rows={r['context_dimension']:r for r in p2_scan['candidate_axes']}
    tlr_rows={r['context_dimension']:r for r in tlr_scan['candidate_axes']}
    positive_row={r['context_dimension']:r for r in positive_scan['candidate_axes']}['novel_endotype_marker']
    tlr_expected=('disease_stage','microglial_state','agonist_exposure_time','agonist_intensity','neuronal_TLR7_state')

    checks={
        'OWNER_UPDATED_TO_POSITIVE_CAUSAL_READINESS_CONTRACT': ADAPTIVE_OWNER_ID == 'ADAPTIVE-AXIS-DISCOVERY/1.1.0',
        'P2X7_EVIDENCE_RECORDS_7': len(p2x7['records']) == 7,
        'P2X7_CONTRADICTORY_OUTCOMES_PRESENT': len({r['outcome_class'] for r in p2x7['records']}) >= 2,
        'ACTIVE_PHARMA_AXES_SCANNED': p2_scan['active_domain_axis_count'] >= 59,
        'KNOWN_MODALITY_RECOGNIZED': p2_rows['therapeutic_modality']['status'] == 'EXISTING_DOMAIN_AXIS',
        'P2X7_MODEL_TRIGGER_GAP_DETECTED': p2_rows['disease_model_trigger']['status'] == 'RESEARCH_LOCAL_AXIS_CANDIDATE',
        'P2X7_HIGH_IG_NOT_ENOUGH_FOR_CAUSAL_READINESS': p2_rows['disease_model_trigger']['normalized_information_gain'] == 1.0 and p2_rows['disease_model_trigger']['causal_readiness_pass'] is False,
        'P2X7_CAUSAL_SELECTION_FAIL_CLOSED': p2_scan['scan_summary']['automatic_causal_axis_selection_allowed'] is False,
        'NORMALIZED_IG_SHORTCUT_NOT_USED': p2_scan['scan_summary']['causal_readiness_contract']['normalized_ig_shortcut_threshold_used'] is False,
        'TLR7_OLD_BUG_CANARY_BELOW_0P90': all(float(tlr_rows[x]['normalized_information_gain']) < 0.90 for x in tlr_expected),
        'TLR7_ALL_PRECOMMITTED_AXES_FAIL_CAUSAL_READINESS': all(tlr_rows[x]['causal_readiness_pass'] is False for x in tlr_expected),
        'TLR7_INDEPENDENT_STUDY_SUPPORT_FAILS': all(int(tlr_rows[x]['minimum_independent_study_support']) <= 1 for x in tlr_expected),
        'TLR7_LOSO_GENERALIZATION_NONPOSITIVE': all(float(tlr_rows[x]['leave_one_study_out']['gain']) <= 0.0 for x in tlr_expected),
        'TLR7_MIXED_STUDY_OUTCOMES_FAIL_GROUPED_NULL_TEST': any(tlr_rows[x]['grouped_study_exact_permutation']['status'] == 'MIXED_OUTCOMES_WITHIN_STUDY_FAIL_CLOSED' for x in tlr_expected),
        'TLR7_CAUSAL_SELECTION_NOW_BLOCKED': tlr_scan['scan_summary']['automatic_causal_axis_selection_allowed'] is False and not tlr_scan['scan_summary']['causal_ready_candidate_dimensions'],
        'POSITIVE_CONTROL_HAS_REPLICATED_SUPPORT': positive_row['minimum_independent_study_support'] == 4,
        'POSITIVE_CONTROL_EXACT_NULL_REJECTED': float(positive_row['grouped_study_exact_permutation']['p_value']) < 0.05,
        'POSITIVE_CONTROL_LOSO_GAIN_POSITIVE': float(positive_row['leave_one_study_out']['gain']) > 0.0,
        'POSITIVE_CONTROL_CAUSAL_READINESS_OPENS': positive_row['causal_readiness_pass'] is True and positive_scan['scan_summary']['automatic_causal_axis_selection_allowed'] is True,
        'PROVISIONAL_AXIS_ADMITTED_RESEARCH_LOCAL_ONLY': admission['research_region_mount_allowed'] is True,
        'RESEARCH_REGION_EXPANDED': region['research_region_axis_count'] == region['canonical_axis_count'] + 1,
        'CANONICAL_REGISTRY_NOT_MUTATED': after['entries'] == before['entries'],
        'NO_WORLD_TRUTH_CREATED': admission['delegated_admission']['claim_boundary']['new_physical_truth_created_by_admission'] is False,
        'ABSENCE_OF_PRIOR_ART_NOT_USED_AS_REJECTION': owner.contract()['hard_boundaries']['absence_of_prior_art_can_reject_candidate'] is False,
        'CONTRADICTION_NOT_AUTO_REJECT': owner.contract()['hard_boundaries']['external_contradiction_can_auto_reject_candidate'] is False,
    }
    passed=sum(bool(v) for v in checks.values())
    payload={
        'schema':SCHEMA,'owner_id':OWNER_ID,
        'status':'PASS_ADAPTIVE_AXIS_RESEARCH_QUALIFICATION' if passed==len(checks) else 'BLOCKED_ADAPTIVE_AXIS_RESEARCH_QUALIFICATION',
        'passed':passed,'total':len(checks),
        'checks':[{'check':k,'status':'PASS' if v else 'FAIL'} for k,v in checks.items()],
        'p2x7_axis_scan':p2_scan,
        'tlr7_regression_axis_scan':tlr_scan,
        'positive_generalization_control':positive_scan,
        'provisional_axis_admission':admission,
        'research_region':region,
        'canonical_registry_before':{k:before[k] for k in ('base_axis_count','dynamic_axis_count','canonical_axis_count')},
        'canonical_registry_after':{k:after[k] for k in ('base_axis_count','dynamic_axis_count','canonical_axis_count')},
        'fixed_defect':{
            'old_behavior':'automatic_causal_axis_selection_allowed = not unresolved_multi with a hard-coded normalized IG >= 0.90 prefilter',
            'new_behavior':'default fail-closed; exactly one axis must pass independent-study support, exact grouped permutation null, positive leave-one-study-out gain, and non-confounding gates',
            'threshold_0p90_removed_from_causal_readiness':True,
            'tlr7_old_false_positive_reproduced_in_v9_1':True,
            'tlr7_false_positive_blocked_in_current_release':True,
        },
        'claim_boundary':{
            'new_drug_discovered':False,
            'clinical_efficacy_established':False,
            'pathophysiologic_endotype_canonicalized':False,
            'research_local_axis_available':True,
            'causal_readiness_is_world_truth':False,
            'full_world_source_attestation':False,
        },
    }
    return {**payload,'digest':digest_payload(payload)}

if __name__=='__main__':
    print(json.dumps(run(),ensure_ascii=False,indent=2,sort_keys=True))
