"""Current-state qualification for Φ-Compiler / ScienceAtlas 0.15.27.0.

The current research state keeps the sealed blind real-data experiment plus the
first Atlas-wide active frontier candidate scan. Historical calculation/search
receipts remain absent. Generated frontier candidates are current research
objects, not baseline source knowledge and not established laws.
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
from fractions import Fraction
from typing import Any
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from source.lawspace.api import LawSpaceAPI
from source.lawspace.runtime import LawSpaceRuntime
from source.lawspace.domains import canonical_axis_count, DOMAIN_REGISTRIES
from source.lawspace.research_cycle import AdaptiveResearchKernelOwner
from source.lawspace.schema import digest_payload
from source.lawspace.knowledge_evolution import CandidateWorldBindingOwner
from source.lawspace.eda_chip_design import EDAChipDesignResearchOwner, qualification_oracle
from source.lawspace.resident_cognitive import COMPONENT_SCHEMA_VERSION, STATE_SCHEMA_VERSION, AI_ACCEPTANCE_VERSION
from source.lawspace.candidates import DOVETAIL_STATE_RELATIVE_PATH, load_dovetail_state_file, dovetail_state_status
from evaluation.first_atlas_native_experiment import run as run_first_control
from evaluation.function_language_birth_qualification import run_release_qualification as run_function_language_birth_qualification
from evaluation.release_files import is_local_artifact
EXT_SRC = ROOT / "extensions" / "ATLAS_AI_RESEARCH_EXTENSION_v0_10_0" / "src"
if str(EXT_SRC) not in sys.path: sys.path.insert(0, str(EXT_SRC))
from scienceatlas_ai.continual import AlphaLedger
from scienceatlas_ai.genesis_shells import FIXED_GENESIS_SHELL_CEILING, SearchPricing, ShellLadder
from scienceatlas_ai.methodology import PipelineNullCalibrationOwner
from scienceatlas_ai.epoch_genesis import SequentialPermutationNullOwner, TriggerBudget as EpochTriggerBudget
from scienceatlas_ai.permutation_eprocess import GainPowerMixture, PermutationGroup

def _epoch_genesis_checks() -> dict[str, bool]:
    null_owner = PipelineNullCalibrationOwner()
    insufficient = null_owner.assess(observed=Fraction(100), null_statistics=[Fraction(0)] * 18, alpha_bp=500)
    exact = null_owner.assess(observed=Fraction(100), null_statistics=[Fraction(0)] * 19, alpha_bp=500)
    seq = SequentialPermutationNullOwner(level=Fraction(1, 40))
    seq_receipt = seq.assess(observed=Fraction(100), null_statistics=[Fraction(0)] * 39)
    budget = EpochTriggerBudget(alpha_total_bp=500, permutation_count=19)
    return {
        "pipeline_null_exact_p_fails_closed_when_resolution_insufficient": insufficient.get("status") == "INSUFFICIENT_NULL_RESOLUTION",
        "pipeline_null_exact_p_passes_only_at_p_within_alpha": exact.get("status") == "PASS" and exact.get("empirical_p") == {"numerator": 1, "denominator": 20},
        "epoch_sequential_null_is_explicitly_not_anytime_valid": seq_receipt.get("status") == "PASS" and seq_receipt.get("claim_boundary", {}).get("is_anytime_valid") is False and __import__("scienceatlas_ai").__version__ == "0.10.0",
        "epoch_rational_alpha_schedule_has_correct_resolution": [budget.permutations_for_attempt(i) for i in range(4)] == [39, 79, 159, 319],
        "epoch_rational_alpha_schedule_prefix_is_below_total": sum((budget.level_for_attempt(i) for i in range(9)), Fraction(0)) == Fraction(511, 10240),
    }


def _genesis_ledger_checks() -> dict[str, bool]:
    ledger=AlphaLedger()
    ledger.grant_for_samples(["q1"],domain="D1",axes=("x","y"),evidence_fingerprints={"q1":"evidence-1"})
    before=ledger.balance_bp
    ledger.grant_for_samples(["q1"],domain="D1",axes=("x","y"),evidence_fingerprints={"q1":"evidence-1"})
    ledger.grant_for_samples(["alias-q1"],domain="D1",axes=("x","y"),evidence_fingerprints={"alias-q1":"evidence-1"})
    ledger.grant_for_samples(["missing-fingerprint"],domain="D1",axes=("x","y"))
    restored=AlphaLedger.from_json(ledger.to_json())
    restored.grant_for_samples(["alias-after-restart"],domain="D1",axes=("x","y"),evidence_fingerprints={"alias-after-restart":"evidence-1"})
    ladder=ShellLadder(); pricing=SearchPricing(); p70=pricing.search_price_bp(families_charged=ladder.shell(70).max_families_examined,permutation_count=1)
    atoms=ladder.shell(20).grammar._atomic_terms(tuple(f"a{i}" for i in range(40)),max_atoms=64)
    return {
      "genesis_alpha_persistent_evidence_dedup_across_aliases": before==25 and ledger.balance_bp==25 and restored.balance_bp==25,
      "genesis_alpha_scoped_grant_requires_evidence_fingerprint": "missing-fingerprint" not in restored.credited_sample_ids,
      "genesis_alpha_domain_scope_blocks_cross_subsidy": not restored.can_spend(25,domain="D2",axes=("x","y")),
      "genesis_alpha_axis_scope_blocks_cross_subsidy": not restored.can_spend(25,domain="D1",axes=("x","z")),
      "genesis_alpha_no_fixed_balance_ceiling": restored.max_balance_bp is None,
      "genesis_shell_ladder_has_no_fixed_ceiling": FIXED_GENESIS_SHELL_CEILING is None,
      "genesis_deepest_affordable_not_truncated_at_63": ladder.deepest_affordable(pricing=pricing,balance_bp=p70,permutation_count=1)==70,
      "genesis_materialisation_guard_is_bounded_prefix": len(atoms)==64 and atoms==tuple(sorted(atoms,key=lambda t:(t.degree,t.powers))),
    }

RELEASE='0.15.27.0'; OWNER_ID='UNIFIED-CURRENT-QUALIFICATION/0.15.27.0'
REAL_REPORT='reports/BLIND_REAL_PHYSICS_EXPERIMENT_CURRENT.json'
FRONTIER_REPORT='reports/ATLAS_FRONTIER_SCAN_CURRENT.json'
FRONTIER_LEDGER='data/frontiers/ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl'
PRIOR_ART_RECEIPT='data/frontiers/ATLAS_POSTFREEZE_PRIOR_ART_CURRENT.json'
DOVETAIL_STATE=str(DOVETAIL_STATE_RELATIVE_PATH)
EPROCESS_REPORT='data/frontiers/PERMUTATION_EPROCESS_QUALIFICATION_CURRENT.json'
SCALAR_LAW_REPORT='data/frontiers/ATLAS_SCALAR_LAW_BIRTH_CURRENT.json'
QUERY_RESEARCH_REPORT='data/frontiers/ATLAS_QUERY_RESEARCH_CURRENT.json'
OLD_CONTROL_REPORT='reports/FIRST_POST_CLEAN_ATLAS_EXPERIMENT_CURRENT.json'
DERIVED_EMPTY_DIRS=('data/evidence','data/particles','data/science_atlas')
DERIVED_FILES=('data/passports/candidates.jsonl','data/passports/quantum_method_routes.jsonl')
AI_FEYNMAN_PATHS=('evaluation/feynman_scientific_axis_qualification.py','evaluation/benchmarks/FEYNMAN_100_WORLD.csv','evaluation/benchmarks/FEYNMAN_100_QUANTITY_METADATA.json')


def _files(root: Path, rel: str):
    p=root/rel
    return [] if not p.exists() else [x for x in p.rglob('*') if x.is_file() and x.name not in {'.gitkeep'}]

def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_release_qualification(root: str|Path|None=None)->dict[str,Any]:
    root=Path(root or ROOT).resolve(); runtime=LawSpaceRuntime(root); api=LawSpaceAPI(root)
    residues={rel:[str(p.relative_to(root)) for p in _files(root,rel)] for rel in DERIVED_EMPTY_DIRS}
    derived_files_present=[rel for rel in DERIVED_FILES if (root/rel).exists()]
    feynman_present=[rel for rel in AI_FEYNMAN_PATHS if (root/rel).exists()]
    report_files=sorted(str(p.relative_to(root)) for p in (root/'reports').glob('*') if p.is_file() and not is_local_artifact(p,root))
    allowed_reports={REAL_REPORT,FRONTIER_REPORT}; unexpected_reports=sorted(set(report_files)-allowed_reports)
    frontier_files=sorted(str(p.relative_to(root)) for p in _files(root,'data/frontiers'))
    allowed_frontier_files={FRONTIER_LEDGER,PRIOR_ART_RECEIPT,DOVETAIL_STATE,'data/frontiers/ATLAS_SCIENTIFIC_EXPLOITATION_CURRENT.json',EPROCESS_REPORT,SCALAR_LAW_REPORT,QUERY_RESEARCH_REPORT}

    stored_real={}; stored_frontier={}
    if (root/REAL_REPORT).exists(): stored_real=json.loads((root/REAL_REPORT).read_text(encoding='utf-8'))
    if (root/FRONTIER_REPORT).exists(): stored_frontier=json.loads((root/FRONTIER_REPORT).read_text(encoding='utf-8'))

    # Heavy scientific receipts are generated by their authoritative owners before
    # qualification and replayed transactionally by FULL CURRENT REPLAY.  The unified
    # gate validates their canonical digests and cross-state invariants; it must not
    # execute the same expensive research cycle a second time.
    control_replay=run_first_control(root)
    real_digest_valid = bool(stored_real) and stored_real.get('digest') == digest_payload({k:v for k,v in stored_real.items() if k != 'digest'})
    frontier_digest_valid = bool(stored_frontier) and stored_frontier.get('digest') == digest_payload({k:v for k,v in stored_frontier.items() if k != 'digest'})
    kernel=AdaptiveResearchKernelOwner(runtime); kernel_contract=kernel.contract(); axis_contract=api.get_atlas_law_space_search_contract()
    adaptive_claim=stored_real.get('adaptive_kernel_receipt',{}).get('atlas_claim',{})
    ledger_path=root/FRONTIER_LEDGER
    ledger_lines=[line for line in ledger_path.read_text(encoding='utf-8').splitlines() if line.strip()] if ledger_path.exists() else []
    ledger_sha=_sha(ledger_path) if ledger_path.exists() else ''
    stored_ledger=stored_frontier.get('active_candidate_ledger',{})
    prior_art_path=root/PRIOR_ART_RECEIPT
    prior_art={}
    if prior_art_path.exists(): prior_art=json.loads(prior_art_path.read_text(encoding='utf-8'))
    prior_art_digest_valid=bool(prior_art) and prior_art.get('digest')==digest_payload({k:v for k,v in prior_art.items() if k!='digest'})
    dovetail_path=root/DOVETAIL_STATE
    dovetail_state=load_dovetail_state_file(dovetail_path) if dovetail_path.is_file() else None
    dovetail_status=dovetail_state_status(dovetail_state)
    fair_contract=dict((dovetail_state or {}).get('fairness_contract',{}))
    live_capabilities=runtime.live_capability_ledger()
    cognitive_state_path=runtime.external_state_path('cognitive_state')
    resident_state_path=runtime.external_state_path('resident_cognitive_state')
    def _outside_release(path: Path) -> bool:
        try:
            path.resolve(strict=False).relative_to(root)
            return False
        except ValueError:
            return True

    
    exploitation=json.load(open(root/'data/frontiers/ATLAS_SCIENTIFIC_EXPLOITATION_CURRENT.json',encoding='utf-8'))
    eprocess_report=json.load(open(root/EPROCESS_REPORT,encoding='utf-8')) if (root/EPROCESS_REPORT).is_file() else {}
    scalar_law_report=json.load(open(root/SCALAR_LAW_REPORT,encoding='utf-8')) if (root/SCALAR_LAW_REPORT).is_file() else {}
    query_research_report=json.load(open(root/QUERY_RESEARCH_REPORT,encoding='utf-8')) if (root/QUERY_RESEARCH_REPORT).is_file() else {}
    scalar_law_digest_valid=bool(scalar_law_report) and scalar_law_report.get('digest')==digest_payload({k:v for k,v in scalar_law_report.items() if k!='digest'})
    query_research_digest_valid=bool(query_research_report) and query_research_report.get('digest')==digest_payload({k:v for k,v in query_research_report.items() if k!='digest'})
    eprocess_core=dict(eprocess_report); eprocess_digest=eprocess_core.pop('digest',None)
    eprocess_cal=eprocess_report.get('type1_empirical_calibration',{})
    eprocess_cb=eprocess_report.get('claim_boundary',{})
    eda_owner=EDAChipDesignResearchOwner()
    eda_contract=eda_owner.contract()
    eda_fail_closed=eda_owner.run_pilot(orfs_flow_root=root/'__NO_ORFS_BACKEND__',evaluation_budget=14,warm_start_count=12,candidate_pool_size=96)
    eda_control=eda_owner.run_pilot(evaluation_budget=14,warm_start_count=12,candidate_pool_size=96,evaluator=qualification_oracle,evaluator_kind='SYNTHETIC_QUALIFICATION_ONLY')
    function_language_qualification=run_function_language_birth_qualification(root)
    fl_checks=function_language_qualification.get('checks',{})
    checks={
      'eda_chip_design_owner_contract_callable': eda_contract.get('status')=='EDA_CHIP_DESIGN_RESEARCH_CONTRACT' and eda_contract.get('pilot',{}).get('platform')=='sky130hd' and eda_contract.get('pilot',{}).get('design')=='gcd',
      'eda_chip_design_api_exposed': {'get_eda_chip_design_contract','get_eda_chip_backend_status','run_eda_chip_design_pilot'} <= set(api.READ_TOOLS),
      'eda_chip_design_missing_backend_fails_closed': eda_fail_closed.get('status')=='CHIP_PILOT_BACKEND_UNAVAILABLE' and eda_fail_closed.get('scientific_result') is None and eda_fail_closed.get('claim_boundary',{}).get('surrogate_substitution_used') is False,
      'eda_chip_design_qualification_control_equal_budget': eda_control.get('status')=='CHIP_PILOT_QUALIFICATION_CONTROL_COMPLETE' and len(eda_control.get('strategies',[]))==4 and len({x.get('evaluation_budget') for x in eda_control.get('strategies',[])})==1 and all(x.get('common_warm_start_count')==12 for x in eda_control.get('strategies',[])),
      'eda_chip_design_qualification_control_not_physical_evidence': eda_control.get('scientific_result') is None and eda_control.get('comparison',{}).get('atlas_beats_all_baselines') is None and eda_control.get('claim_boundary',{}).get('qualification_control_is_physical_chip_evidence') is False,
      'eda_chip_design_signoff_gates_are_fail_closed': eda_contract.get('claim_boundary',{}).get('timing_drc_lvs_or_gds_missing_is_pass') is False and eda_contract.get('claim_boundary',{}).get('route_drc_can_substitute_for_signoff_drc') is False and eda_contract.get('gates',{}).get('lvs')=='explicit machine/log match required' and str(eda_contract.get('gates',{}).get('drc','')).startswith('explicit sign-off'),
      'dimensional_scalar_law_birth_current_digest_valid': scalar_law_digest_valid,
      'dimensional_scalar_law_birth_measured_census': scalar_law_report.get('summary',{}).get('subspace_count')==3706 and scalar_law_report.get('summary',{}).get('p1_frozen_formula_count')==683 and scalar_law_report.get('summary',{}).get('unique_pi_signature_count')==14 and scalar_law_report.get('summary',{}).get('u4_p1_frozen_formula_count')==125 and scalar_law_report.get('summary',{}).get('u4_unique_pi_signature_count')==13,
      'query_research_current_digest_valid': query_research_digest_valid,
      'query_research_current_identity_15_27': query_research_report.get('release')=='0.15.27.0' and query_research_report.get('owner')=='QUERY-DRIVEN-RESEARCH/1.2.0',
      'query_research_bound_to_current_candidate_ledger': query_research_report.get('source_candidate_ledger_sha256')==ledger_sha,
      'query_research_embeds_current_function_language_qualification': query_research_report.get('function_language_birth_qualification',{}).get('status')=='PASS_FUNCTION_LANGUAGE_BIRTH_QUALIFICATION' and query_research_report.get('function_language_birth_qualification',{}).get('digest')==function_language_qualification.get('digest'),
      'query_mode_recovers_unhinted_thiele_coordinate': query_research_report.get('acceptance',{}).get('pass') is True and query_research_report.get('acceptance',{}).get('observed_top_formula')=='k * D^-1 * L^2' and float(query_research_report.get('acceptance',{}).get('observed_top_collapse',9))<0.15,
      'query_mode_multiplicity_counts_full_search_not_display_limit': query_research_report.get('synthetic_reaction_diffusion_control',{}).get('search_surface',{}).get('display_limit_is_search_budget') is False and query_research_report.get('synthetic_reaction_diffusion_control',{}).get('permutation_null',{}).get('entire_ranked_surface_replayed') is True,
      'query_mode_multi_pi_function_form_lane_live': query_research_report.get('multi_pi_function_form_control',{}).get('dimension_kernel',{}).get('nullity') == 4 and query_research_report.get('multi_pi_function_form_control',{}).get('search_surface',{}).get('structural_hypotheses_examined_total') == 45,
      'query_mode_multi_pi_whole_surface_group_null': query_research_report.get('multi_pi_function_form_control',{}).get('permutation_null',{}).get('entire_function_surface_refit_each_permutation') is True and query_research_report.get('multi_pi_function_form_control',{}).get('permutation_null',{}).get('exchangeability_scheme') == 'WITHIN_VALIDATION_GROUP',
      'query_mode_world_data_gap_fails_closed': query_research_report.get('world_data_binding_audit_2026_09_08',{}).get('u5_status') == 'UNKNOWN' and query_research_report.get('world_data_binding_audit_2026_09_08',{}).get('source_stitching_used_to_create_fit') is False,
      'query_mode_function_form_api_exposed': 'search_observations_for_function_forms' in set(api.READ_TOOLS),
      'function_language_birth_qualification_current': function_language_qualification.get('status')=='PASS_FUNCTION_LANGUAGE_BIRTH_QUALIFICATION' and all(fl_checks.values()),
      'function_language_birth_preserves_polynomial_control': fl_checks.get('polynomial_control_preserves_current_language') is True,
      'function_language_birth_improves_periodic_and_local_controls': fl_checks.get('periodic_language_materially_improves_oof_prediction') is True and fl_checks.get('kernel_language_materially_improves_oof_prediction') is True,
      'function_language_birth_noise_negative_control': fl_checks.get('noise_control_does_not_force_language_birth') is True,
      'function_language_birth_dynamic_null_replay': fl_checks.get('dynamic_language_birth_is_inside_permutation_null') is True,
      **_genesis_ledger_checks(),
      **_epoch_genesis_checks(),
      'permutation_eprocess_qualification_current': eprocess_report.get('status')=='PASS_PERMUTATION_EPROCESS_15_20_0' and eprocess_digest==digest_payload(eprocess_core),
      'permutation_eprocess_type1_empirical_1000_paths': eprocess_cal.get('paths')==1000 and eprocess_cal.get('epochs_per_path')==3 and int(eprocess_cal.get('crossings',1001))*20<=1000,
      'permutation_eprocess_claim_is_per_target_only': eprocess_cb.get('per_target_only') is True and eprocess_cb.get('system_wide_error_control') is False and eprocess_cb.get('global_online_controller')=='UNIMPLEMENTED',
      'permutation_eprocess_score_is_preregistered_exact_mixture': GainPowerMixture(powers=(1,2,4,8)).to_json().get('powers')==[1,2,4,8],
      'permutation_eprocess_c6_and_s6_are_exact_groups': PermutationGroup.cyclic(6).verify_group_laws().get('valid') is True and PermutationGroup.symmetric(6).verify_group_laws().get('valid') is True,
      'scientific_exploitation_current': exploitation.get('status')=='PASS_SCIENTIFIC_EXPLOITATION_15_23_0' and exploitation.get('portfolio',{}).get('candidate_count')==stored_frontier.get('scan_summary',{}).get('materialized_relational_u4_pass_count') and exploitation.get('portfolio',{}).get('u10_promotion_count')==0,
      'candidate_data_binding_receipts_persisted': stored_frontier.get('scan_summary',{}).get('candidate_world_binding_receipt_count')==2 and exploitation.get('candidate_data_binding_diagnostic',{}).get('binding_count')==2,
      'candidate_data_binding_negative_control_blocks_domain_mismatch': exploitation.get('candidate_data_binding_diagnostic',{}).get('negative_control',{}).get('status')=='CANDIDATE_WORLD_BINDING_BLOCKED_DATASET_SOURCE_FAMILY_MISMATCH' and exploitation.get('candidate_data_binding_diagnostic',{}).get('negative_control',{}).get('data_binding_qualified') is False,
      'candidate_data_binding_positive_control_exposes_response_projection': exploitation.get('candidate_data_binding_diagnostic',{}).get('positive_control',{}).get('status')=='DATASET_BINDING_QUALIFIED_RESPONSE_PROJECTION_AVAILABLE' and exploitation.get('candidate_data_binding_diagnostic',{}).get('positive_control',{}).get('data_binding_qualified') is True and len(exploitation.get('candidate_data_binding_diagnostic',{}).get('positive_control',{}).get('response_projection_options',[]))==1,
      'candidate_response_projection_prefrozen_and_persisted': exploitation.get('candidate_data_binding_diagnostic',{}).get('response_projection_count')==1 and exploitation.get('candidate_data_binding_diagnostic',{}).get('response_projection',{}).get('status')=='FROZEN_EXECUTABLE_MEASUREMENT_CONTRACT_CANDIDATE_PREDICTION_PENDING' and stored_frontier.get('scan_summary',{}).get('candidate_response_projection_count')==1,
      'candidate_measurement_response_executed_without_fake_discrimination': exploitation.get('candidate_data_binding_diagnostic',{}).get('measurement_execution_count')==1 and exploitation.get('candidate_data_binding_diagnostic',{}).get('measurement_execution',{}).get('status')=='PASS_EXECUTABLE_MEASUREMENT_RESPONSE_ACQUIRED_CANDIDATE_DISCRIMINATION_PENDING' and exploitation.get('candidate_data_binding_diagnostic',{}).get('measurement_execution',{}).get('candidate_specific_prediction_used') is False and exploitation.get('candidate_data_binding_diagnostic',{}).get('measurement_execution',{}).get('scientific_discrimination_executed') is False and stored_frontier.get('scan_summary',{}).get('candidate_measurement_execution_count')==1,
      'candidate_data_binding_and_response_execution_do_not_fake_world_attestation_or_u5': exploitation.get('candidate_data_binding_diagnostic',{}).get('world_attestation_count')==0 and stored_frontier.get('scan_summary',{}).get('materialized_relational_u5_pass_count')==0 and stored_frontier.get('scan_summary',{}).get('scientifically_discriminating_measurement_count')==0,
      'manual_candidate_prediction_lowering_frozen_once': exploitation.get('candidate_data_binding_diagnostic',{}).get('manual_prediction_lowering_count')==1 and stored_frontier.get('scan_summary',{}).get('candidate_prediction_lowering_count')==1 and stored_frontier.get('scan_summary',{}).get('candidate_specific_prediction_frozen_count')==1,
      'manual_candidate_prediction_heldout_check_executed_once': exploitation.get('candidate_data_binding_diagnostic',{}).get('manual_prediction_discrimination_count')==1 and stored_frontier.get('scan_summary',{}).get('candidate_prediction_discrimination_count')==1 and stored_frontier.get('scan_summary',{}).get('heldout_prediction_check_executed_count')==1,
      'manual_candidate_prediction_collapse_failure_is_preserved_not_retuned': exploitation.get('candidate_data_binding_diagnostic',{}).get('manual_prediction_collapse_pass_count')==0 and exploitation.get('candidate_data_binding_diagnostic',{}).get('manual_prediction_discrimination',{}).get('domain_discrimination_receipt',{}).get('status')=='FAIL_MANUAL_CANDIDATE_PREDICTION_COLLAPSE_DIAGNOSTIC' and stored_frontier.get('scan_summary',{}).get('manual_prediction_collapse_pass_count')==0,
      'u4_structural_lowerability_audit_complete': exploitation.get('structural_lowerability_audit',{}).get('candidate_count')==447 and stored_frontier.get('scan_summary',{}).get('u4_structural_single_forward_owner_complete_count')==14 and stored_frontier.get('scan_summary',{}).get('u4_structural_composable_multi_owner_complete_count')==286 and stored_frontier.get('scan_summary',{}).get('u4_structural_addressable_union_count')==300,
      'u4_strict_single_forward_owner_is_small_subset_not_global_gate': exploitation.get('structural_lowerability_audit',{}).get('single_forward_owner_complete_count')==14 and exploitation.get('structural_lowerability_audit',{}).get('interpretation',{}).get('not_a_global_u1_u2_gate') is True,
      'manual_lowering_retry_until_lucky_blocked_by_alpha_ledger': CandidateWorldBindingOwner().contract().get('rules',{}).get('distinct_retry_lowering_for_same_candidate_requires_multiplicity_alpha_ledger') is True and CandidateWorldBindingOwner().contract().get('rules',{}).get('retry_until_lucky_without_alpha_spending_allowed') is False,
      'canonical_axes_preserved': canonical_axis_count()==655,
      'domain_registries_present': len(DOMAIN_REGISTRIES)==13,
      'known_law_catalog_preserved': len(runtime.catalog.passports)==445,
      'computational_method_definitions_preserved': len(runtime.computational_methods)>=24,
      'baseline_candidate_registry_empty': len(runtime.candidates)==0 and not derived_files_present,
      'evidence_registry_empty': len(runtime.evidence)==0 and not residues['data/evidence'],
      'particle_result_store_empty': not residues['data/particles'],
      'science_atlas_result_store_empty': not residues['data/science_atlas'],
      'generated_quantum_routes_empty': len(runtime.quantum_method_routes)==0,
      'active_frontier_store_is_single_current_ledger': set(frontier_files)==allowed_frontier_files,
      'ai_feynman_100_removed': not feynman_present,
      'exactly_two_current_research_reports': set(report_files)==allowed_reports,
      'old_control_report_not_persisted': not (root/OLD_CONTROL_REPORT).exists(),
      'no_unexpected_report_residue': not unexpected_reports,
      'real_blind_experiment_receipt_passes': stored_real.get('status')=='PASS_FIRST_BLIND_REAL_PHYSICS_EXPERIMENT' and stored_real.get('passed')==stored_real.get('total')==18 and all(stored_real.get('checks',{}).values()),
      'stored_real_report_canonical_digest_valid': real_digest_valid,
      'frontier_scan_receipt_passes': stored_frontier.get('status')=='PASS_ATLAS_FRONTIER_CANDIDATE_SCAN' and all(stored_frontier.get('checks',{}).values()),
      'stored_frontier_report_canonical_digest_valid': frontier_digest_valid,
      'low_frequency_anomaly_analysis_passes': stored_frontier.get('scan_summary',{}).get('low_frequency_gust_anomaly_status')=='PASS_LOW_FREQUENCY_GUST_ANOMALY_PUBLIC_EVIDENCE_ANALYSIS',
      'tri_state_experiment_is_designed_not_faked': stored_frontier.get('checks',{}).get('tri_state_complex_transfer_experiment_designed') is True and stored_frontier.get('incomplete_frontiers',{}).get('probe_to_wing_physical_measurement',{}).get('posterior_update_allowed') is False,
      'active_candidate_ledger_count_matches': len(ledger_lines)==stored_ledger.get('record_count')==stored_frontier.get('scan_summary',{}).get('active_candidate_ledger_count') and len(ledger_lines)>0,
      'active_candidate_ledger_hash_matches': bool(ledger_sha) and ledger_sha==stored_ledger.get('sha256'),
      'postfreeze_prior_art_receipt_digest_valid': prior_art_digest_valid,
      'postfreeze_prior_art_bound_to_current_ledger': prior_art.get('bound_active_candidate_ledger_sha256')==ledger_sha and prior_art.get('bound_candidate_record_count')==len(ledger_lines),
      'postfreeze_prior_art_absence_is_neutral': prior_art.get('selection_policy',{}).get('absence_from_search_is_negative_evidence') is False and prior_art.get('claim_boundary',{}).get('novelty_established_by_search_failure') is False,
      'all_materialized_candidates_remain_active': stored_frontier.get('candidate_status_counts',{}).get('CANDIDATE_ACTIVE')==len(ledger_lines),
      'adaptive_multidimensional_frontier_is_active_research_state': stored_frontier.get('candidate_class_counts',{}).get('ADAPTIVE_MULTIDIMENSIONAL_SUBSPACE_FRONTIER',0)>0 and stored_frontier.get('scan_summary',{}).get('adaptive_subspace_maximum_axis_order',0)>15 and stored_frontier.get('scan_summary',{}).get('adaptive_subspace_minimum_axis_order',0)>=2,
      'algebraic_frontier_terminates_by_saturation_not_visit_budget': stored_frontier.get('scan_summary',{}).get('algebraic_execution_stop_reason')=='ALGEBRAIC_IDEAL_BASIS_SATURATED',
      'operator_frontier_exhausts_without_visit_budget': stored_frontier.get('scan_summary',{}).get('operator_execution_stop_reason')=='FRONTIER_EXHAUSTED',
      'unknown_is_not_false_policy_active': stored_frontier.get('policy',{}).get('unknown_candidate_is_false') is False,
      'ranking_is_not_deletion_policy': stored_frontier.get('policy',{}).get('ranking_is_deletion_policy') is False,
      'synthetic_control_remains_replayable': control_replay.get('status')=='PASS_FIRST_POST_CLEAN_ATLAS_EXPERIMENT' and control_replay.get('passed')==control_replay.get('total')==15,
      'atlas_native_provenance_not_world_law': adaptive_claim.get('atlas_native') is True and adaptive_claim.get('scientific_truth_established') is False and stored_real.get('claim_boundary',{}).get('new_physical_law_established') is False,
      'frontier_scan_does_not_claim_new_world_law': stored_frontier.get('claim_boundary',{}).get('new_scientific_law_established_by_scan') is False,
      'adaptive_kernel_contract_callable': bool(kernel_contract.get('owner_id') or kernel_contract.get('owner')),
      'atlas_law_space_contract_callable': bool(axis_contract),
      'core_convergence_exact_7d_dimension_authority': axis_contract.get('canonical_dimension_basis')==['L','M','T','I','Theta','N','J'] and axis_contract.get('dimension_authority')=='EXACT_RATIONAL_7D_KERNEL_VIA_PHI_COMPILER_OWNER',
      'core_convergence_whole_pipeline_null_required_before_promotion': axis_contract.get('qualification_kernel',{}).get('whole_pipeline_permutation_null')=='REQUIRED_BEFORE_SCIENTIFIC_PROMOTION_NOT_EXECUTED_ON_RAW_COORDINATE_BIRTH',
      'core_convergence_not_symbolic_regression': axis_contract.get('expression_tree_is_primary_search_space') is False,
      'p2_conservation_canonicalization_requires_composition_law': axis_contract.get('qualification_kernel',{}).get('conservation_invariant_canonicalization')=='COMPOSITION_ADDITIVITY_REQUIRED__TRAJECTORY_CONSTANCY_ALONE_INSUFFICIENT',
      'p2_resident_version_axes_are_explicitly_separate': COMPONENT_SCHEMA_VERSION=='6.0.0' and STATE_SCHEMA_VERSION=='5' and AI_ACCEPTANCE_VERSION=='15.10.5' and RELEASE not in {COMPONENT_SCHEMA_VERSION,STATE_SCHEMA_VERSION,AI_ACCEPTANCE_VERSION},
      'p2_resident_restore_migration_cli_present': (root/'interfaces/phi_compiler_cli.py').is_file() and 'resident-state-restore' in (root/'interfaces/phi_compiler_cli.py').read_text(encoding='utf-8'),
      'p2_strict_read_only_audit_path_present': (root/'evaluation/read_only_audit.py').is_file() and 'audit-read-only' in (root/'Makefile').read_text(encoding='utf-8'),
      'scientific_depth_u4_executes_for_all_frozen_relational_hypotheses': stored_frontier.get('scan_summary',{}).get('materialized_relational_u4_pass_count')==stored_frontier.get('scan_summary',{}).get('typed_hypothesis_materializations_bound_to_current_records')==exploitation.get('portfolio',{}).get('candidate_count') and int(exploitation.get('portfolio',{}).get('candidate_count') or 0)>0,
      'scientific_depth_u5_u10_remain_world_evidence_gated': stored_frontier.get('scan_summary',{}).get('materialized_relational_u5_pass_count')==0 and stored_frontier.get('scan_summary',{}).get('automatic_scientific_promotion_count')==0,
      'qualification_runtime_covers_every_frontier_candidate': stored_frontier.get('qualification_runtime',{}).get('receipt_count')==len(ledger_lines)==stored_frontier.get('qualification_runtime',{}).get('receipt_valid_count'),
      'qualification_runtime_uses_single_promotion_owner_v9_2': stored_frontier.get('qualification_runtime',{}).get('owner')=='SCIENTIFIC-PROMOTION-CORE/9.2.0',
      'qualification_runtime_fail_closed_no_auto_promotion': stored_frontier.get('qualification_runtime',{}).get('prepromotion_ready_count')==0 and stored_frontier.get('qualification_runtime',{}).get('promotion_allowed_count')==0 and stored_frontier.get('qualification_runtime',{}).get('candidate_false_count')==0,
      'qualification_runtime_whole_pipeline_null_explicit_and_nonbypassable': 'U8_WHOLE_PIPELINE_PERMUTATION_NULL' in stored_frontier.get('qualification_runtime',{}).get('gate_sequence',[]) and stored_frontier.get('qualification_runtime',{}).get('direct_numeric_core_can_bypass_unified_path') is False,
      'fair_dovetail_state_is_digest_valid_and_bound_to_frontier': dovetail_status.get('valid') is True and stored_frontier.get('fair_open_ended_traversal',{}).get('state_digest')==(dovetail_state or {}).get('digest'),
      'fair_dovetail_preserves_15_13_adaptive_identity_set': (dovetail_state or {}).get('baseline_candidate_count')==1005 and stored_frontier.get('fair_open_ended_traversal',{}).get('preserved_15_13_candidate_count')==1005 and stored_frontier.get('fair_open_ended_traversal',{}).get('legacy_15_13_candidate_set_deleted') is False,
      'fair_dovetail_has_no_fixed_global_or_local_scientific_ceiling': fair_contract.get('fixed_global_step_ceiling') is None and fair_contract.get('fixed_pair_seed_ceiling') is None and fair_contract.get('fixed_node_visit_ceiling') is None and fair_contract.get('fixed_axis_order_ceiling') is None and axis_contract.get('fair_local_search_shell',{}).get('fixed_maximum_shell') is None,
      'fair_dovetail_coverage_is_not_score_gated': str(fair_contract.get('coverage_lane','')).startswith('EVERY_MISSING_AXIS_EDGE_IS_ADDRESSABLE') and fair_contract.get('axis_birth_order_is_append_only') is True,
      'fair_dovetail_mutable_runtime_state_defaults_outside_seal': _outside_release(runtime.external_state_path('atlas_dovetail_traversal')),
      'postfreeze_prior_art_binding_migration_preserves_review_content': prior_art.get('binding_migration',{}).get('prior_art_candidate_reviews_modified') is False and prior_art.get('binding_migration',{}).get('prior_art_classifications_modified') is False,
      'live_ai_capability_ledger_is_executable_current_state': live_capabilities.get('capability_count',0)>=250 and live_capabilities.get('executable_read_count',0)>0 and live_capabilities.get('executable_mutation_count',0)>0,
      'live_ai_capability_ledger_uses_no_historical_snapshot': live_capabilities.get('historical_capability_snapshot_used') is False,
      'collective_coordination_remains_explicit_open_ai_obligation': 'collective_coordination' in set(live_capabilities.get('open_architecture_obligations',[])),
      'cognitive_mutable_state_defaults_outside_sealed_release': _outside_release(cognitive_state_path),
      'resident_mutable_state_defaults_outside_sealed_release': _outside_release(resident_state_path),
    }
    payload={
      'schema':'phi-current-state-qualification/v1','release':RELEASE,'owner':OWNER_ID,
      'status':'PASS_CURRENT_STATE_15_27_0' if all(checks.values()) else 'FAIL_CURRENT_STATE_15_27_0',
      'checks':checks,
      'counts':{'canonical_axes':canonical_axis_count(),'domains':len(DOMAIN_REGISTRIES),'known_laws':len(runtime.catalog.passports),'computational_methods':len(runtime.computational_methods),'baseline_candidates':len(runtime.candidates),'active_frontier_candidates':len(ledger_lines),'evidence':len(runtime.evidence),'quantum_routes':len(runtime.quantum_method_routes),'persisted_current_research_reports':len(report_files)},
      'blind_real_physics_experiment':{'status':stored_real.get('status'),'digest':stored_real.get('digest'),'result_summary':stored_real.get('result_summary'),'canonical_digest_valid':real_digest_valid},
      'frontier_candidate_scan':{'status':stored_frontier.get('status'),'digest':stored_frontier.get('digest'),'scan_summary':stored_frontier.get('scan_summary'),'qualification_runtime':stored_frontier.get('qualification_runtime'),'fair_open_ended_traversal':stored_frontier.get('fair_open_ended_traversal'),'ledger_sha256':ledger_sha,'canonical_digest_valid':frontier_digest_valid},
      'postfreeze_prior_art_review':{'status':prior_art.get('status'),'digest':prior_art.get('digest'),'review_count':prior_art.get('review_count'),'summary':prior_art.get('summary'),'bound_ledger_sha256':prior_art.get('bound_active_candidate_ledger_sha256'),'canonical_digest_valid':prior_art_digest_valid},
      'synthetic_control':{'status':control_replay.get('status'),'digest':control_replay.get('digest'),'persisted_as_current_report':False},
      'eda_chip_design':{'contract_digest':eda_contract.get('digest'),'fail_closed_status':eda_fail_closed.get('status'),'qualification_control_digest':eda_control.get('digest'),'live_world_result_established':False},
      'function_language_birth':{'status':function_language_qualification.get('status'),'digest':function_language_qualification.get('digest'),'metrics':function_language_qualification.get('metrics'),'world_result_established':False},
      'ai_runtime':{'capability_count':live_capabilities.get('capability_count'),'open_architecture_obligations':live_capabilities.get('open_architecture_obligations'),'mutable_state_default_external':True,'mutable_state_bundled_in_seal':False},
      'residue':{'derived_directories':residues,'derived_files_present':derived_files_present,'frontier_files':frontier_files,'unexpected_reports':unexpected_reports,'ai_feynman_paths_present':feynman_present},
      'claim_boundary':{'historical_search_or_calculation_receipts_restored':False,'current_frontier_candidates_are_baseline_source_knowledge':False,'current_frontier_candidates_are_established_laws':False,'known_overlap_deletes_candidate':False,'unknown_candidate_is_false':False,'axes_and_static_source_knowledge_are_preserved':True,'cognitive_state_is_external_mutable_runtime_state':True,'resident_learning_is_not_scientific_truth':True,'consciousness_claimed':False,'agi_claimed':False,'finite_dovetail_tranche_exhausts_scientific_space':False,'unvisited_subspace_is_false':False,'legacy_15_13_frontier_deleted':False,'permutation_eprocess_per_target_only':True,'global_online_evalue_controller_implemented':False}
    }
    payload['digest']=digest_payload(payload); return payload


def main(): print(json.dumps(run_release_qualification(),ensure_ascii=False,indent=2,sort_keys=True))
if __name__=='__main__': main()
