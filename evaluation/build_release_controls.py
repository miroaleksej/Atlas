"""Build deterministic release envelope for Φ-Compiler / ScienceAtlas 0.15.29.0."""
from __future__ import annotations
import hashlib,json,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from source.lawspace.schema import digest_payload
from source.lawspace.domains import canonical_axis_count, DOMAIN_REGISTRIES
from source.lawspace.runtime import LawSpaceRuntime
from evaluation.unified_release_qualification import run_release_qualification
from source.lawspace.resident_cognitive import COMPONENT_SCHEMA_VERSION, STATE_SCHEMA_VERSION, AI_ACCEPTANCE_VERSION
from source.lawspace.eda_chip_design import EDAChipDesignResearchOwner
from source.lawspace.research_triage import ResearchTriageSandbox
from evaluation.research_triage_qualification import run as run_research_triage_qualification
from evaluation.release_files import is_local_artifact
RELEASE='0.15.29.0'; OWNER='RELEASE-CONTROLS/0.15.29.0'
EXCLUDE={'RELEASE_MANIFEST.json','HASHES.txt','FILE_TREE.md'}
REAL_REPORT='reports/BLIND_REAL_PHYSICS_EXPERIMENT_CURRENT.json'
FRONTIER_REPORT='reports/ATLAS_FRONTIER_SCAN_CURRENT.json'
FRONTIER_LEDGER='data/frontiers/ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl'
EPROCESS_REPORT='data/frontiers/PERMUTATION_EPROCESS_QUALIFICATION_CURRENT.json'
QUERY_REPORT='data/frontiers/ATLAS_QUERY_RESEARCH_CURRENT.json'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def controlled(root):
 rows=[]
 for p in root.rglob('*'):
  if not p.is_file(): continue
  rel=str(p.relative_to(root))
  if rel in EXCLUDE or is_local_artifact(p,root): continue
  rows.append({'path':rel,'sha256':sha(p),'size':p.stat().st_size})
 return sorted(rows,key=lambda x:x['path'])
def run(root=None, *, allow_blocked=False):
 root=Path(root or ROOT).resolve(); q=run_release_qualification(root); rt=LawSpaceRuntime(root)
 qualification_passed=q.get('status')=='PASS_CURRENT_STATE_15_29_0'
 if not qualification_passed and not allow_blocked: raise RuntimeError('current-state qualification failed')
 real=json.loads((root/REAL_REPORT).read_text(encoding='utf-8')); scan=json.loads((root/FRONTIER_REPORT).read_text(encoding='utf-8')); query=json.loads((root/QUERY_REPORT).read_text(encoding='utf-8')); live_ai=rt.live_capability_ledger()
 caps={'schema':'phi-capabilities/current-v1','release':RELEASE,'status':'ADAPTIVE_TRIAGE_SANDBOX_HUMAN_REVIEW_AND_FUNCTION_LANGUAGE_EDA_INTEGRATED','system':'Phi-Compiler / ScienceAtlas Adaptive Triage + Exploration Sandbox + Human Review + Multi-Pi + Function-Language Birth + EDA Chip PPA Pilot','authoritative_research_kernel':'ADAPTIVE-RESEARCH-KERNEL/15.4.0','state':{'historical_search_receipts_restored':0,'historical_calculation_receipts_restored':0,'baseline_candidate_registry_count':len(rt.candidates),'active_frontier_candidate_count':scan['active_candidate_ledger']['record_count'],'evidence_registry_count':len(rt.evidence),'generated_quantum_route_count':len(rt.quantum_method_routes),'current_research_report_count':2},'preserved':{'canonical_axis_count':canonical_axis_count(),'domain_registry_count':len(DOMAIN_REGISTRIES),'known_law_count':len(rt.catalog.passports),'computational_method_count':len(rt.computational_methods),'static_source_knowledge':True},'removed':{'ai_feynman_100_benchmark':True,'historical_reports_and_replays':True,'historical_generated_candidates_frontiers_and_freezes':True,'persisted_synthetic_control_report':True},'blind_real_physics_experiment':{'problem_id':real.get('problem_id'),'status':real.get('status'),'digest':real.get('digest'),'research_freeze_digest':real.get('research_freeze',{}).get('digest'),'scientific_discovery_established':False},'frontier_candidate_scan':{'status':scan.get('status'),'digest':scan.get('digest'),'active_candidate_count':scan['active_candidate_ledger']['record_count'],'candidate_class_counts':scan.get('candidate_class_counts'),'adaptive_subspace':{'candidate_count':scan.get('scan_summary',{}).get('adaptive_multidimensional_subspace_candidates'),'seed_count':scan.get('scan_summary',{}).get('adaptive_subspace_seed_count'),'minimum_axis_order':scan.get('scan_summary',{}).get('adaptive_subspace_minimum_axis_order'),'maximum_axis_order':scan.get('scan_summary',{}).get('adaptive_subspace_maximum_axis_order'),'fixed_axis_order_ceiling':None,'fixed_neighbor_visit_budget':scan.get('scan_summary',{}).get('adaptive_subspace_neighbor_visit_budget'),'lower_order_projection_required_before_higher_order_nomination':False,'candidate_absent_from_literature_is_false':False},'new_scientific_law_established':False},'low_frequency_gust_anomaly':{'status':scan.get('scan_summary',{}).get('low_frequency_gust_anomaly_status'),'mean_residual_db_4_8_hz':scan.get('scan_summary',{}).get('low_frequency_mean_residual_db'),'conditional_effective_input_ratio_4_8_hz':scan.get('scan_summary',{}).get('low_frequency_conditional_effective_input_ratio'),'new_physical_mechanism_established':False},'ai_restore':{'architecture_restored':True,'live_capability_count':live_ai.get('capability_count'),'historical_capability_snapshot_used':live_ai.get('historical_capability_snapshot_used'),'open_architecture_obligations':live_ai.get('open_architecture_obligations'),'resolved_architecture_obligations':live_ai.get('resolved_architecture_obligations'),'mutable_state_external_to_seal':True,'mutable_state_bundled_in_release':False,'resident_learning_is_scientific_truth':False,'consciousness_claimed':False,'agi_claimed':False},'core_convergence':{'canonical_dimension_basis':['L','M','T','I','Theta','N','J'],'exact_rational_dimension_kernel':True,'legacy_5d_boundary_compatibility_only':True,'whole_pipeline_permutation_null_required_before_promotion':True,'parallel_symbolic_regression_core_added':False},'qualification_runtime_convergence':{'scientific_promotion_owner':'SCIENTIFIC-PROMOTION-CORE/9.2.0','frontier_receipt_count':scan.get('qualification_runtime',{}).get('receipt_count'),'frontier_receipt_valid_count':scan.get('qualification_runtime',{}).get('receipt_valid_count'),'prepromotion_ready_count':scan.get('qualification_runtime',{}).get('prepromotion_ready_count'),'promotion_allowed_count':scan.get('qualification_runtime',{}).get('promotion_allowed_count'),'candidate_false_count':scan.get('qualification_runtime',{}).get('candidate_false_count'),'whole_pipeline_null_required_before_law_candidate':scan.get('qualification_runtime',{}).get('whole_pipeline_null_required_before_law_candidate'),'direct_numeric_core_can_bypass_unified_path':scan.get('qualification_runtime',{}).get('direct_numeric_core_can_bypass_unified_path')},'fair_open_ended_dovetail':{'owner':scan.get('fair_open_ended_traversal',{}).get('owner'),'state_digest':scan.get('fair_open_ended_traversal',{}).get('state_digest'),'state_valid':scan.get('fair_open_ended_traversal',{}).get('state_valid'),'preserved_15_13_candidate_count':scan.get('fair_open_ended_traversal',{}).get('preserved_15_13_candidate_count'),'continuation_candidate_count':scan.get('fair_open_ended_traversal',{}).get('dovetail_continuation_candidate_count'),'node_count':scan.get('fair_open_ended_traversal',{}).get('node_count'),'fixed_global_step_ceiling':scan.get('fair_open_ended_traversal',{}).get('fairness_contract',{}).get('fixed_global_step_ceiling'),'fixed_axis_order_ceiling':scan.get('fair_open_ended_traversal',{}).get('fairness_contract',{}).get('fixed_axis_order_ceiling'),'local_search_shell_fixed_maximum':None,'mutable_runtime_state_external_to_seal':True,'finite_tranche_exhausts_scientific_space':False},'p2_closure':{'conservation_canonicalization':'COMPOSITION_ADDITIVITY_REQUIRED','resident_restore_migration':'DIGEST_BOUND_EXTERNAL_ATOMIC_RESTORE','version_axes':{'system_release':RELEASE,'component_schema_version':'6.0.0','state_schema_version':'5','ai_acceptance_version':'15.10.6'},'strict_read_only_audit':'TREE_BYTE_AND_DIRECTORY_IDENTITY_REQUIRED'},'scientific_depth':{'materialized_relational_hypotheses':scan.get('scan_summary',{}).get('typed_hypothesis_materializations_bound_to_current_records'),'u4_formal_derivability_pass':scan.get('scan_summary',{}).get('materialized_relational_u4_pass_count'),'u5_empirical_pass':scan.get('scan_summary',{}).get('materialized_relational_u5_pass_count'),'candidate_world_binding_receipts':scan.get('scan_summary',{}).get('candidate_world_binding_receipt_count'),'frozen_response_projection_contracts':scan.get('scan_summary',{}).get('candidate_response_projection_count'),'executed_measurement_responses':scan.get('scan_summary',{}).get('candidate_measurement_execution_count'),'manual_candidate_prediction_lowerings':scan.get('scan_summary',{}).get('candidate_prediction_lowering_count'),'heldout_prediction_checks':scan.get('scan_summary',{}).get('candidate_prediction_discrimination_count'),'manual_prediction_collapse_passes':scan.get('scan_summary',{}).get('manual_prediction_collapse_pass_count'),'u4_strict_single_forward_owner_complete':scan.get('scan_summary',{}).get('u4_structural_single_forward_owner_complete_count'),'u4_composable_multi_owner_complete':scan.get('scan_summary',{}).get('u4_structural_composable_multi_owner_complete_count'),'u4_structurally_addressable_union':scan.get('scan_summary',{}).get('u4_structural_addressable_union_count'),'scientifically_discriminating_measurements':scan.get('scan_summary',{}).get('scientifically_discriminating_measurement_count'),'world_attestations':scan.get('scan_summary',{}).get('world_attestation_count'),'automatic_promotions':scan.get('scan_summary',{}).get('automatic_scientific_promotion_count')},'qualification_digest':q['digest']}
 caps['collective_coordination']={
  'owner':'COLLECTIVE-COORDINATION/1.0.0',
  'capability_state':live_ai.get('capabilities',{}).get('collective_coordination'),
  'open_obligation':'collective_coordination' in set(live_ai.get('open_architecture_obligations',[])),
  'resolved_generation_anchor':'collective_coordination' in set(live_ai.get('resolved_architecture_obligations',[])),
  'qualification':q.get('ai_runtime',{}).get('collective_coordination_qualification',{}),
  'external_superiority_claimed':False,
  'agi_claimed':False,
 }
 caps['release_control']={
  'current_state_qualification_status':q.get('status'),
  'current_state_qualification_passed':qualification_passed,
  'failed_checks':[k for k,v in q.get('checks',{}).items() if not v],
  'release_candidate_sealed':qualification_passed,
  'blocked_release_controls_materialized_only_when_explicitly_requested':not qualification_passed,
 }
 triage_contract=ResearchTriageSandbox.contract()
 triage_qualification=run_research_triage_qualification()
 caps['research_triage_sandbox']={
  'owner':f"{triage_contract.get('owner_id')}/{triage_contract.get('owner_version')}",
  'contract_digest':triage_contract.get('digest'),
  'qualification_passed':triage_qualification.get('passed'),
  'qualification_total':triage_qualification.get('total'),
  'quality_tiers':triage_contract.get('quality_tiers'),
  'dpi_rank_only':True,
  'manual_override_can_pass_u_gate':False,
  'sandbox_dimension_exception_can_pass_u2':False,
  'hypothesis_council_mutable_state_external_to_seal':True,
  'expert_weight_learning_scope':'SANDBOX_RANKING_ONLY',
 }
 caps['axis_birth_search_policy']={
  'axis_birth_cardinality':'ADAPTIVE',
  'multi_axis_birth':'ALLOWED',
  'higher_order_interaction_axes':'ALLOWED',
  'fixed_axis_count_per_cycle':None,
  'search':['SPARSE','ADAPTIVE','OPEN_ENDED'],
  'problem_structure_selects_birth_cardinality':True,
  'single_axis_greedy_growth_required':False,
  'finite_execution_cycle_materializes_finite_axis_set':True,
  'individual_axis_lifecycle_receipts_required':True,
 }
 caps['representation_activation_epistemics']={
  'representation_activated_equals_causally_established':False,
  'residual_driven_activation_scope':'RESEARCH_LOCAL_MODEL_REPRESENTATION',
  'causal_establishment_requires_separate_authoritative_evidence':True,
  'causal_readiness_failure_blocks_representation_activation':False,
  'receipt_exposes_representation_and_causal_statuses_separately':True,
 }
 caps['primitive_field_operator_birth']={
  'owner':'PRIMITIVE-FIELD-OPERATOR-COORDINATE-BIRTH/1.0.0',
  'primitive_sampled_fields_only':True,
  'caller_supplied_derivative_columns_required':False,
  'named_pde_template_required':False,
  'dimension_typed_operator_grammar':True,
  'adaptive_multi_axis_birth':True,
  'sealed_holdout_used_for_axis_selection':False,
  'representation_activation_is_causal_establishment':False,
  'controlled_reference_world_is_new_physical_law':False,
 }
 caps['query_research']={
  'owner':query.get('owner'),
  'report_digest':query.get('digest'),
  'p1_scalar_lane':True,
  'p_gt_1_function_form_lane':True,
  'exact_pi_basis_frozen_before_function_fit':True,
  'hypothesis_budget_min':10,
  'hypothesis_budget_max':100,
  'whole_function_surface_permutation_refit':True,
  'grouped_null_exchangeability_scheme':'WITHIN_VALIDATION_GROUP',
  'polynomial_surface_is_query_grammar_not_primary_space':True,
  'selected_cv_score_is_unbiased_post_selection_estimate':False,
  'cross_domain_exact_kernel_receipts':query.get('cross_domain_kernel_verification_2026_09_08',{}).get('candidate_count'),
  'complete_joint_world_dataset_identified':False,
  'source_stitching_used_to_create_fit':query.get('world_data_binding_audit_2026_09_08',{}).get('source_stitching_used_to_create_fit'),
  'u5_status':query.get('world_data_binding_audit_2026_09_08',{}).get('u5_status'),
  'function_language_birth_enabled':True,
  'function_language_birth_component':'FUNCTION-LANGUAGE-BIRTH/1.0.0-COMPONENT',
  'mathematical_invention_kernel_owner':'PHI-MATHEMATICAL-INVENTION-KERNEL/1.1.0',
  'generated_function_families':['RATIONAL','EXPONENTIAL','LOGARITHMIC','PERIODIC','PIECEWISE','KERNEL','LATENT'],
  'language_birth_triggered_by_oof_residual':True,
  'language_birth_requires_operation_signal_above_multiplicity_aware_gate':True,
  'dynamic_language_birth_replayed_under_permutation':True,
  'function_language_birth_changes_pi_coordinates':False,
  'noise_can_force_language_birth':False,
  'function_language_search_exhausts_all_mathematics':False,
  'function_language_qualification_status':query.get('function_language_birth_qualification',{}).get('status'),
  'function_language_qualification_digest':query.get('function_language_birth_qualification',{}).get('digest'),
  'function_language_qualification_metrics':query.get('function_language_birth_qualification',{}).get('metrics'),
  'new_scientific_law_established':False,
 }
 caps['autonomous_epoch_genesis']={
  'owner':'epoch-genesis-director/0.1.0',
  'additive_to_research_loop':True,
  'research_loop_rewritten':False,
  'fresh_assessment_and_confirmation_epochs':True,
  'scoped_evidence_fingerprint_boundary':'ResearchLoopOwner._acquire',
  'exact_finite_permutation_p_gate':True,
  'sequential_per_target_union_bound':True,
  'anytime_valid_e_process':False,
  'global_online_fdr_control':False,
  'resource_deferral_is_epistemic_rejection':False,
  'acceptance_compute_ceiling_permutations':200,
  'next_required_permutations_at_resource_frontier':319,
  'new_scientific_law_established':False,
 }
 eprocess=json.loads((root/EPROCESS_REPORT).read_text(encoding='utf-8'))
 ecal=eprocess.get('type1_empirical_calibration',{}); ecb=eprocess.get('claim_boundary',{})
 caps['permutation_eprocess']={
  'owner':'permutation-eprocess-owner/0.1.0',
  'qualification_status':eprocess.get('status'),
  'frozen_genesis_journal_orbit_scoring':True,
  'orbit_calls_write_genesis_journal':False,
  'fresh_epoch_sample_reuse_refused':True,
  'finite_group_normalization_exact':True,
  'score':'equal mixture of (1+sealed_gain_bp)^q for q in {1,2,4,8}',
  'type1_empirical_paths':ecal.get('paths'),
  'type1_empirical_crossings':ecal.get('crossings'),
  'type1_empirical_calibration_is_proof':False,
  'per_target_only':True,
  'ville_threshold_20_is_system_wide_guarantee':False,
  'global_online_controller':'UNIMPLEMENTED',
  'atlas_wide_promotion_from_eprocess_crossing_alone':False,
  's6_selected_demo_is_prospective_power_evidence':False,
 }
 eda=EDAChipDesignResearchOwner(); eda_contract=eda.contract(); eda_backend=eda.backend_status()
 caps['eda_chip_design']={
  'owner':eda_contract.get('owner'),
  'status':'RESEARCH_OWNER_INTEGRATED_LIVE_EDA_RESULT_PENDING',
  'pilot_platform':'sky130hd','pilot_design':'gcd',
  'frozen_knob_count':len(eda_contract.get('frozen_knobs',[])),
  'strategies':eda_contract.get('comparison',{}).get('strategies'),
  'equal_budget_required':True,'common_warm_start_required':True,
  'timing_signoff_drc_lvs_gds_fail_closed':True,
  'route_drc_can_substitute_for_signoff_drc':False,
  'workflow_orfs_git_commit':eda_contract.get('pilot',{}).get('workflow_orfs_git_commit'),
  'backend_status_at_seal':eda_backend.get('status'),
  'live_equal_budget_pilot_completed_in_release':False,
  'atlas_beats_baselines_established':False,
  'tapeout_readiness_claimed':False,
 }
 caps['digest']=digest_payload(caps); (root/'capabilities.json').write_text(json.dumps(caps,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
 inv={'schema':'phi-invariants/current-v1','release':RELEASE,'owner':OWNER,'invariants':{'canonical_scientific_axes_are_persistent_when_dormant':True,'historical_research_state_remains_absent':True,'current_frontier_candidate_ledger_is_persistent_research_state':True,'candidate_ranking_never_deletes_candidate':True,'known_overlap_never_implies_falsification':True,'unknown_never_means_false':True,'unmaterialized_pair_region_never_means_rejected':True,'adaptive_subspace_search_has_no_fixed_order_ceiling':True,'all_axes_not_required_in_each_candidate':True,'lower_order_projection_not_required_for_higher_order_nomination':True,'unmaterialized_subspaces_are_not_rejected':True,'literature_absence_is_not_negative_evidence':True,'candidate_problem_applicability_experiment_contract_required':True,'synthetic_controls_are_replayed_not_persisted_as_research_state':True,'sealed_holdout_is_not_used_for_search_or_refit':True,'known_source_knowledge_is_not_a_search_result':True,'scientific_axis_primary_space_is_not_expression_tree':True,'canonical_dimension_basis_is_7d_si':True,'exact_rational_dimension_kernel_is_authoritative_for_law_space':True,'legacy_5d_dimensions_are_boundary_compatibility_only':True,'whole_pipeline_permutation_null_required_before_scientific_promotion':True,'every_frontier_candidate_has_unified_promotion_path':True,'direct_numeric_promotion_cannot_bypass_unified_frontier_receipt':True,'missing_qualification_evidence_is_pending_not_false':True,'source_derived_candidate_not_promoted_as_independent_new_law':True,'fair_dovetail_state_is_persistent_and_digest_bound':True,'fair_dovetail_has_no_fixed_global_step_ceiling':True,'fair_dovetail_pair_and_node_schedulers_are_starvation_resistant_under_stable_finite_registry':True,'fair_dovetail_axis_birth_order_is_append_only':True,'fair_dovetail_coverage_is_not_structural_score_gated':True,'legacy_15_13_adaptive_frontier_identity_set_is_preserved':True,'finite_execution_tranche_is_not_scientific_space_ceiling':True,'local_law_space_search_shell_has_no_fixed_maximum':True,'ai_feynman_100_is_not_part_of_current_system':True,'atlas_native_provenance_is_not_scientific_truth':True,'resident_mutable_state_is_external_to_sealed_tree':True,'resident_learning_is_not_scientific_truth':True,'cognitive_self_model_cannot_promote_scientific_truth':True,'consciousness_not_claimed':True,'agi_not_claimed':True,'conservation_canonicalization_requires_composition_law':True,'resident_state_restore_is_digest_bound_and_external':True,'system_component_state_ai_acceptance_versions_are_distinct_axes':True,'strict_read_only_audit_proves_sealed_tree_identity':True,'materialized_relational_u4_formal_audit_complete':True,'materialized_relational_u5_u10_world_evidence_gated':True}}
 inv['invariants'].update({
  'autonomous_epoch_genesis_uses_fresh_confirmation_data_after_shell_decision':True,
  'assessment_epoch_is_never_reused_as_genesis_confirmation':True,
  'scoped_epoch_alpha_uses_existing_acquisition_evidence_fingerprint':True,
  'finite_permutation_null_requires_exact_p_with_sufficient_resolution':True,
  'sequential_null_level_is_exact_rational_and_summable_per_target':True,
  'statistical_null_level_is_distinct_from_search_and_promotion_prices':True,
  'resource_deferral_is_not_scientific_rejection':True,
  'sequential_permutation_null_is_not_claimed_anytime_valid':True,
  'global_online_fdr_control_not_yet_claimed':True,
  'permutation_eprocess_orbit_uses_one_frozen_genesis_journal_snapshot':True,
  'permutation_eprocess_orbit_cannot_write_genesis_journal':True,
  'permutation_eprocess_fresh_epoch_sample_reuse_is_refused':True,
  'permutation_eprocess_group_average_e_is_exactly_one':True,
  'permutation_eprocess_ville_threshold_is_per_target_only':True,
  'permutation_eprocess_crossing_cannot_promote_atlas_wide_without_global_controller':True,
  's6_argmax_fixture_is_resolution_demo_not_prospective_power_evidence':True,
  'empirical_type1_calibration_is_sanity_check_not_proof':True,
  'candidate_response_projection_must_be_frozen_before_measurement_execution':True,
  'dataset_response_execution_requires_digest_bound_experiment_data_ir':True,
  'executed_dataset_response_without_candidate_specific_prediction_is_not_u5':True,
  'retrospective_public_data_reanalysis_is_not_independent_world_attestation':True,
  'candidate_prediction_lowering_remains_required_before_scientific_discrimination':True,
  'distinct_manual_lowering_retry_requires_multiplicity_alpha_ledger':True,
  'retry_until_lucky_without_alpha_spending_allowed':False,
  'u4_structural_lowerability_audit_is_not_global_gate':True,
  'query_mode_p_gt_1_uses_exact_kernel_before_function_fit':True,
  'query_mode_whole_function_surface_replayed_under_permutation':True,
  'query_mode_grouped_null_preserves_exchangeability_blocks':True,
  'query_function_grammar_is_not_primary_scientific_axis_space':True,
  'query_function_form_world_claim_requires_joint_axis_data':True,
  'query_partial_world_sources_do_not_establish_u5':True,
  'query_function_language_birth_requires_persistent_oof_residual':True,
  'query_function_language_birth_requires_operation_signal_above_multiplicity_aware_gate':True,
  'query_function_language_birth_does_not_change_exact_pi_kernel':True,
  'query_function_language_birth_not_forced_by_high_error_without_operation_signal':True,
  'query_dynamic_language_birth_replayed_under_permutation':True,
  'query_generated_function_languages_are_finite_query_grammar_not_global_math_space':True,
  'eda_world_backend_is_external_authoritative_evaluator':True,
  'eda_missing_backend_never_uses_surrogate_as_chip_result':True,
  'eda_timing_signoff_drc_lvs_gds_are_fail_closed_gates':True,
  'eda_route_drc_cannot_substitute_for_signoff_drc':True,
  'eda_boolean_comparison_requires_feasible_design_from_all_four_strategies':True,
  'eda_equal_budget_baseline_comparison_required_before_atlas_win_claim':True,
  'eda_synthetic_qualification_is_not_silicon_evidence':True,
 'eda_pilot_does_not_claim_tapeout_readiness':True,
  'axis_birth_cardinality_is_adaptive':True,
  'multi_axis_birth_is_allowed':True,
  'higher_order_interaction_axis_birth_is_allowed':True,
  'fixed_axis_count_per_cycle_is_absent':True,
  'axis_search_is_sparse_adaptive_and_open_ended':True,
  'multi_axis_birth_does_not_bypass_individual_axis_lifecycle':True,
  'collective_coordination_preserves_independent_belief_states':True,
  'collective_coordination_holdout_is_not_architecture_selector':True,
  'resolved_architecture_obligation_is_not_reopened_as_gap':True,
  'collective_coordination_does_not_claim_external_ai_superiority':True,
  'representation_activation_is_not_causal_establishment':True,
  'residual_axis_activation_is_research_local_representation_only':True,
  'causal_establishment_requires_separate_authoritative_evidence':True,
  'primitive_field_operator_coordinates_are_born_inside_atlas':True,
  'primitive_field_operator_birth_requires_named_pde_template':False,
  'primitive_field_benchmark_establishes_new_physical_law':False,
 })
 inv['digest']=digest_payload(inv); (root/'invariants.json').write_text(json.dumps(inv,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
 files=controlled(root)
 man={'schema':'phi-release-manifest/current-v1','release':RELEASE,'owner':OWNER,'status':'ADAPTIVE_TRIAGE_SANDBOX_HUMAN_REVIEW_AND_FUNCTION_LANGUAGE_EDA_INTEGRATED','controlled_file_count':len(files),'controlled_files':files,'current_state_qualification_digest':q['digest'],'blind_real_physics_experiment_digest':real.get('digest'),'research_freeze_digest':real.get('research_freeze',{}).get('digest'),'frontier_scan_digest':scan.get('digest'),'active_candidate_ledger_sha256':scan.get('active_candidate_ledger',{}).get('sha256'),'active_candidate_count':scan.get('active_candidate_ledger',{}).get('record_count'),'low_frequency_gust_anomaly_digest':scan.get('hotspots',{}).get('low_frequency_gust_anomaly',{}).get('digest'),'research_state_policy':{'axes_preserved':True,'static_source_knowledge_preserved':True,'historical_search_results_preserved':False,'historical_calculation_results_preserved':False,'current_blind_real_data_result_preserved':True,'current_active_frontier_candidates_preserved':True,'candidate_ranking_is_deletion_policy':False,'unknown_candidate_is_false':False,'unmaterialized_adaptive_subspace_is_false':False,'literature_absence_is_negative_evidence':False,'fixed_adaptive_subspace_order_ceiling':None,'all_axes_required_per_candidate':False,'synthetic_control_persisted_as_result':False,'ai_feynman_100_preserved':False,'resident_mutable_state_external_to_release':True,'resident_mutable_state_bundled':False,'cognitive_learning_promotes_scientific_truth':False,'canonical_dimension_basis':['L','M','T','I','Theta','N','J'],'exact_rational_dimension_kernel':True,'legacy_5d_boundary_compatibility_only':True,'unified_frontier_promotion_path_required':True,'direct_numeric_promotion_bypass_forbidden':True,'whole_pipeline_null_required_before_law_candidate':True,'fair_dovetail_state_persisted':True,'fair_dovetail_fixed_global_step_ceiling':None,'fair_dovetail_fixed_pair_seed_ceiling':None,'fair_dovetail_fixed_node_visit_ceiling':None,'fair_dovetail_axis_birth_order_append_only':True,'legacy_15_13_adaptive_candidate_count_preserved':1005,'finite_dovetail_tranche_is_scientific_space_ceiling':False,'local_search_shell_fixed_maximum':None,'conservation_invariant_canonicalization_requires_composition_law':True,'resident_state_restore_digest_bound_external':True,'version_identity_axes_separated':True,'strict_read_only_audit_required':True,'materialized_relational_u4_complete':True,'u5_u10_require_world_evidence':True,'response_projection_prefreeze_required':True,'executed_dataset_response_without_candidate_prediction_is_u5':False,'manual_lowering_post_reveal_retuning_allowed':False,'manual_lowering_generalized_to_class':False,'manual_lowering_distinct_retry_requires_alpha_ledger':True,'retry_until_lucky_without_alpha_spending_allowed':False,'u1_u2_lowerability_proposal_enforced':False,'u4_structural_lowerability_audit_is_global_gate':False}}
 man['release_candidate_status']='SEALED_CANDIDATE' if qualification_passed else 'BLOCKED_PINNED_NUMERIC_REPLAY'
 man['current_state_qualification_status']=q.get('status')
 man['current_state_failed_checks']=[k for k,v in q.get('checks',{}).items() if not v]
 man['release_candidate_sealed']=qualification_passed
 man['collective_coordination']=q.get('ai_runtime',{}).get('collective_coordination_qualification',{})
 man['research_state_policy'].update({
  'query_p_gt_1_function_form_lane_enabled':True,
  'query_exact_pi_basis_frozen_before_function_fit':True,
  'query_hypothesis_budget_min':10,
  'query_hypothesis_budget_max':100,
  'query_whole_function_surface_permutation_refit_required':True,
  'query_grouped_null_preserves_validation_groups':True,
  'query_polynomial_surface_is_primary_atlas_space':False,
  'query_selected_cv_score_is_unbiased_post_selection_estimate':False,
  'query_world_claim_requires_complete_joint_axis_data':True,
  'query_partial_source_stitching_allowed':False,
 'query_multi_pi_u5_status':'UNKNOWN',
  'query_function_language_birth_enabled':True,
  'query_function_language_birth_component':'FUNCTION-LANGUAGE-BIRTH/1.0.0-COMPONENT',
  'query_function_language_birth_requires_persistent_oof_residual':True,
  'query_function_language_birth_requires_operation_signal_above_multiplicity_aware_gate':True,
  'query_function_language_birth_changes_exact_pi_kernel':False,
  'query_function_language_birth_replayed_inside_permutation_null':True,
  'query_generated_function_languages_are_finite_query_grammar_not_global_math_space':True,
  'eda_chip_design_owner_integrated':True,
  'eda_external_orfs_world_required_for_chip_result':True,
  'eda_timing_signoff_drc_lvs_gds_missing_is_pass':False,
  'eda_route_drc_can_substitute_for_signoff_drc':False,
  'eda_workflow_orfs_git_commit':eda_contract.get('pilot',{}).get('workflow_orfs_git_commit'),
  'eda_equal_budget_atlas_random_grid_bayesian_comparison_required':True,
 'eda_live_pilot_completed_in_release':False,
  'axis_birth_cardinality':'ADAPTIVE',
  'multi_axis_birth_allowed':True,
  'higher_order_interaction_axes_allowed':True,
  'fixed_axis_count_per_cycle':None,
  'axis_search_policy':['SPARSE','ADAPTIVE','OPEN_ENDED'],
  'multi_axis_birth_bypasses_axis_lifecycle':False,
  'representation_activated_equals_causally_established':False,
  'representation_and_causal_axis_statuses_separated':True,
  'primitive_field_operator_birth_owner':'PRIMITIVE-FIELD-OPERATOR-COORDINATE-BIRTH/1.0.0',
  'primitive_field_caller_supplies_derivative_columns':False,
  'primitive_field_named_pde_template_required':False,
  'primitive_field_sealed_holdout_used_for_axis_selection':False,
  'primitive_field_control_establishes_new_physical_law':False,
 })
 man['research_state_policy'].update({
  'dynamic_quality_tiers_enabled':True,
  'dynamic_quality_tier_can_weaken_strict_u_gate':False,
  'empirical_quality_status':'PHENOMENOLOGICAL_MODEL',
  'exploratory_quality_status':'STRUCTURAL_ANOMALY',
  'exploratory_quality_blocks_before_u4':True,
  'sandbox_dpi_is_scientific_promotion':False,
  'promising_reject_is_u5_or_u6':False,
  'human_sponsor_review_can_pass_u6':False,
  'sandbox_dimension_exception_can_pass_u2':False,
  'hypothesis_council_state_external_to_seal':True,
  'expert_weight_learning_changes_strict_promotion_config':False,
 })
 man['research_triage_sandbox']={
  'owner':f"{triage_contract.get('owner_id')}/{triage_contract.get('owner_version')}",
  'contract_digest':triage_contract.get('digest'),
  'qualification':triage_qualification,
  'quality_tiers':triage_contract.get('quality_tiers'),
  'default_dpi_weights':triage_contract.get('default_dpi_weights'),
  'manual_override_can_pass_u_gate':False,
  'sandbox_dimension_exception_can_pass_u2':False,
  'mutable_state_inside_sealed_tree':False,
 }
 man['query_research']={
  'owner':query.get('owner'),
  'report_digest':query.get('digest'),
  'status':query.get('status'),
  'cross_domain_exact_kernel_status':query.get('cross_domain_kernel_verification_2026_09_08',{}).get('status'),
  'cross_domain_exact_kernel_candidate_count':query.get('cross_domain_kernel_verification_2026_09_08',{}).get('candidate_count'),
  'multi_pi_control_digest':query.get('multi_pi_function_form_control',{}).get('digest'),
  'multi_pi_control_nullity':query.get('multi_pi_function_form_control',{}).get('dimension_kernel',{}).get('nullity'),
  'multi_pi_structural_hypotheses_examined':query.get('multi_pi_function_form_control',{}).get('search_surface',{}).get('structural_hypotheses_examined_total'),
  'multi_pi_familywise_permutation_p':query.get('multi_pi_function_form_control',{}).get('permutation_null',{}).get('familywise_empirical_p'),
  'world_data_status':query.get('world_data_binding_audit_2026_09_08',{}).get('status'),
  'u5_status':query.get('world_data_binding_audit_2026_09_08',{}).get('u5_status'),
  'source_stitching_used_to_create_fit':query.get('world_data_binding_audit_2026_09_08',{}).get('source_stitching_used_to_create_fit'),
  'function_language_birth_component':'FUNCTION-LANGUAGE-BIRTH/1.0.0-COMPONENT',
  'mathematical_invention_kernel_owner':'PHI-MATHEMATICAL-INVENTION-KERNEL/1.1.0',
  'function_language_birth_qualification_status':query.get('function_language_birth_qualification',{}).get('status'),
  'function_language_birth_qualification_digest':query.get('function_language_birth_qualification',{}).get('digest'),
  'function_language_birth_qualification_metrics':query.get('function_language_birth_qualification',{}).get('metrics'),
  'dynamic_language_birth_replayed_under_permutation':True,
  'generated_function_families':['RATIONAL','EXPONENTIAL','LOGARITHMIC','PERIODIC','PIECEWISE','KERNEL','LATENT'],
  'world_function_language_result_established':False,
 }
 man['eda_chip_design']={
  'owner':eda_contract.get('owner'),
  'contract_digest':eda_contract.get('digest'),
  'platform':'sky130hd','design':'gcd',
  'world_backend':'OpenROAD Flow Scripts + Yosys + OpenROAD + KLayout',
  'workflow_orfs_git_commit':eda_contract.get('pilot',{}).get('workflow_orfs_git_commit'),
  'frozen_knobs':eda_contract.get('frozen_knobs'),
  'strategies':eda_contract.get('comparison',{}).get('strategies'),
  'backend_status_at_seal':eda_backend.get('status'),
  'live_result_digest':None,
  'atlas_beats_all_baselines':None,
  'claim_boundary':{'physical_chip_result_established':False,'atlas_vs_baselines':'UNKNOWN','tapeout_ready':False},
 }
 # Evidence/identity repair block: current package identity and scientific census.
 frontier=json.loads((root/FRONTIER_REPORT).read_text(encoding='utf-8'))
 qrt=frontier.get('qualification_runtime',{})
 exploit=json.loads((root/'data/frontiers/ATLAS_SCIENTIFIC_EXPLOITATION_CURRENT.json').read_text(encoding='utf-8'))
 portfolio=exploit.get('portfolio',{})
 wheel_rel='extensions/ATLAS_AI_RESEARCH_EXTENSION_v0_10_0/dist/scienceatlas_ai-0.10.0-py3-none-any.whl'
 wheel=root/wheel_rel
 wheel_version=''
 if wheel.is_file():
  with zipfile.ZipFile(wheel) as zf:
   metadata=zf.read('scienceatlas_ai-0.10.0.dist-info/METADATA').decode('utf-8')
  for line in metadata.splitlines():
   if line.startswith('Version: '): wheel_version=line.split(': ',1)[1]; break
 man['version_identity']={
  'system_release':RELEASE,
  'ai_acceptance_version':AI_ACCEPTANCE_VERSION,
  'component_schema_version':COMPONENT_SCHEMA_VERSION,
  'state_schema_version':STATE_SCHEMA_VERSION,
  'scienceatlas_ai_package_version':wheel_version,
  'scienceatlas_ai_wheel_path':wheel_rel,
  'scienceatlas_ai_wheel_sha256':sha(wheel) if wheel.is_file() else None,
 }
 man['blind_law_capability']={
  'exact_recovery_verified_under_current_valid_controller':False,
  'resource_frontier_verified':True,
  'verified_stop':'DEFERRED_RESOURCE',
  'verified_next_level':'1/320',
  'verified_required_permutations':319,
  'promotion_before_frontier':False,
  'prior_recovery_under_superseded_null_is_current_claim_evidence':False,
  'superseded_by':'exact-p permutation gate; prior run judged at a level the null could not achieve at N=8 (minimum achievable p=1/9 > 0.05)',
 }
 man['scientific_census']={
  'u0_u10_gate_pass_counts':qrt.get('gate_pass_counts',{}),
  'materialized_u4_candidates':frontier.get('scan_summary',{}).get('materialized_relational_u4_pass_count'),
  'materialized_u5_pass':frontier.get('scan_summary',{}).get('materialized_relational_u5_pass_count'),
  'u5_u10_dossiers':portfolio.get('candidate_count'),
  'single_domain_dossiers':portfolio.get('single_domain_count'),
  'cross_domain_dossiers':portfolio.get('cross_domain_count'),
  'automatic_law_promotions':portfolio.get('u10_promotion_count'),
  'candidate_world_binding_receipts':frontier.get('scan_summary',{}).get('candidate_world_binding_receipt_count'),
  'frozen_response_projection_contracts':frontier.get('scan_summary',{}).get('candidate_response_projection_count'),
  'executed_measurement_responses':frontier.get('scan_summary',{}).get('candidate_measurement_execution_count'),
  'manual_candidate_prediction_lowerings':frontier.get('scan_summary',{}).get('candidate_prediction_lowering_count'),
  'heldout_prediction_checks':frontier.get('scan_summary',{}).get('candidate_prediction_discrimination_count'),
  'manual_prediction_collapse_passes':frontier.get('scan_summary',{}).get('manual_prediction_collapse_pass_count'),
  'u4_strict_single_forward_owner_complete':frontier.get('scan_summary',{}).get('u4_structural_single_forward_owner_complete_count'),
  'u4_composable_multi_owner_complete':frontier.get('scan_summary',{}).get('u4_structural_composable_multi_owner_complete_count'),
  'u4_structurally_addressable_union':frontier.get('scan_summary',{}).get('u4_structural_addressable_union_count'),
  'scientifically_discriminating_measurements':frontier.get('scan_summary',{}).get('scientifically_discriminating_measurement_count'),
  'world_attestations':frontier.get('scan_summary',{}).get('world_attestation_count'),
 }
 man['autonomous_epoch_genesis']={
  'status':'RESOURCE_DEFERRED_AFTER_VALID_SEQUENTIAL_SEARCHES',
  'fixture_world_evidence':False,
  'scientific_law_promoted_by_release':False,
  'sequential_controller_anytime_valid':False,
  'e_process_frontier':'OWNER_PRESENT_PER_TARGET_ONLY_GLOBAL_CONTROLLER_OPEN',
 }
 man['permutation_eprocess']={
  'qualification_digest':eprocess.get('digest'),
  'qualification_status':eprocess.get('status'),
  'frozen_genesis_journal_required':True,
  'orbit_member_genesis_journal_writes':False,
  'type1_empirical_calibration':ecal,
  'per_target_only':ecb.get('per_target_only'),
  'system_wide_error_control':ecb.get('system_wide_error_control'),
  'global_online_controller':ecb.get('global_online_controller'),
  'ville_threshold_20_is_system_wide_guarantee':False,
  's6_selected_fixture_is_prospective_power_evidence':False,
  'atlas_wide_promotion_allowed_from_crossing_alone':False,
 }
 man['digest']=digest_payload(man); (root/'RELEASE_MANIFEST.json').write_text(json.dumps(man,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
 (root/'HASHES.txt').write_text('\n'.join(f"{r['sha256']}  {r['path']}" for r in files)+'\n')
 tree=['# FILE TREE — CURRENT 0.15.29.0','',f'Controlled files: {len(files)}','']+[f"- `{r['path']}`" for r in files]
 (root/'FILE_TREE.md').write_text('\n'.join(tree)+'\n')
 return man
if __name__=='__main__': print(json.dumps(run(),ensure_ascii=False,indent=2,sort_keys=True))
