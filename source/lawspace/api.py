"""Strict AI-facing API over the deterministic law-space runtime."""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from .runtime import LawSpaceRuntime
from .schema import digest_payload


class LawSpaceAPI:
    READ_TOOLS = (
        "search_entities", "get_passport", "resolve_symbol", "resolve_constant", "resolve_candidate_quantities", "get_deep_formula_candidates", "find_by_dimensions",
        "find_home_cell", "find_composition_path", "compare_models", "search_candidates", "get_candidate", "search_computational_methods", "search_quantum_method_routes", "get_quantum_method_route", "propose_candidate", "request_next_measurement", "get_neutrino_owner_contract", "get_neutrino_intersection_law_contract", "search_neutrino_source_laws", "get_neutrino_source_law", "search_neutrino_intersection_laws", "get_neutrino_intersection_law", "get_aeronautics_intersection_law_contract", "search_aeronautics_source_laws", "get_aeronautics_source_law", "search_aeronautics_intersection_laws", "get_aeronautics_intersection_law", "compile_aeronautics_intersection_spec", "get_quantum_vacuum_gravity_contract", "search_quantum_vacuum_source_laws", "get_quantum_vacuum_source_law", "search_quantum_vacuum_intersection_laws", "get_quantum_vacuum_intersection_law", "compile_quantum_vacuum_gravity_spec", "get_constraint_atlas_contract", "get_constraint_atlas_qualification", "derive_constraint_atlas_circuit", "scan_constraint_atlas_unknown_frontier", "scan_constraint_atlas_operator_unknown_frontier", "build_constraint_atlas_aeroelastic_projection_bridge", "discover_constraint_atlas_temporal_kernel", "discover_constraint_atlas_spatial_nonlocal_kernel", "get_constraint_atlas_real_gust_aero_lag_discovery", "get_constraint_atlas_real_gust_full_research_cycle", "analyze_constraint_atlas_probe_wing_modal_discriminator", "get_constraint_atlas_probe_wing_modal_discriminator_qualification", "get_constraint_atlas_low_frequency_gust_anomaly_analysis", "get_neutrino_blind_discovery_contract", "get_neutrino_postfreeze_novelty_contract", "compute_neutrino_probability", "get_neutrino_algebraic_contract", "get_neutrino_real_data_contract", "evaluate_neutrino_real_data_candidate", "get_dayabay_likelihood_contract", "get_katrin_likelihood_contract", "get_t2k_likelihood_contract", "get_superk_atmospheric_likelihood_contract", "get_superk_solar_likelihood_contract", "get_neutrino_external_constraints_contract", "get_neutrino_global_contract", "get_scientific_data_ingestion_contract", "get_scientific_research_cycle_contract", "interpret_research_question", "run_scientific_research_cycle", "close_deep_candidate_gamma", "assess_dynamic_axis", "assess_post_derivation_novelty", "rank_experiments_by_information_gain", "get_scientific_promotion_contract", "evaluate_scientific_promotion", "get_scientific_inference_status", "run_scientific_promotion_qualification", "get_axis_modeling_contract", "run_axis_modeling", "run_axis_modeling_realdata_qualification", "get_dynamic_axis_promotion_contract", "get_dynamic_axis_registry_state", "get_common_scientific_rules_contract", "get_domain_plugin_registry_contract", "list_domain_plugins", "get_domain_plugin_contract", "get_black_hole_lab_contract", "evaluate_black_hole_lab", "run_black_hole_lab_qualification", "get_black_hole_dynamic_contract", "run_black_hole_vaidya_benchmark", "assess_black_hole_dynamic_closure", "get_einstein_dynamics_contract", "analyze_einstein_adaptive_axes", "derive_spherical_einstein_equations", "solve_einstein_exact_sector", "derive_einstein_massless_scalar_system", "run_einstein_massless_scalar_pre_horizon_benchmark", "derive_einstein_massless_scalar_horizon_penetrating_system", "run_einstein_massless_scalar_horizon_formation_benchmark", "run_blind_covariant_operator_search", "derive_frozen_blind_operator_black_hole_solution", "continue_blind_covariant_operator_search_after_prior_art_kill", "get_blind_covariant_operator_postfreeze_assessment", "run_blind_representation_branch_search", "derive_frozen_auxiliary_branch_black_hole_solution", "get_blind_representation_postfreeze_assessment", "continue_auxiliary_branch_after_prior_art_kill", "get_auxiliary_cubic_postfreeze_assessment", "continue_blind_representation_search_after_auxiliary_kill", "run_causal_nonlocal_memory_discriminant", "run_blind_causal_nonlocal_metric_closure_search", "run_frozen_causal_nonlocal_metric_closure_experiment", "get_causal_nonlocal_metric_closure_postfreeze_assessment", "run_causal_nonlocal_metric_closure_qualification", "get_curvature_memory_covariant_closure", "run_curvature_memory_order_reduced_black_hole_experiment", "run_curvature_memory_closure_qualification", "rank_blind_representation_frontier", "run_blind_representation_qualification", "assess_general_4d_einstein_problem", "run_einstein_dynamics_qualification", "get_particle_space_contract", "enumerate_particle_space", "search_particle_space_cells", "get_particle_space_cell", "get_particle_space_postfreeze_summary", "get_particle_space_global_form_summary", "run_particle_space_whole_representation_blind", "run_particle_space_blind_discovery", "close_particle_space_coordinate", "run_particle_space_census_qualification", "get_particle_space_collider_qualification_contract", "evaluate_particle_space_d7_reference", "get_particle_space_recast_technical_gate", "run_particle_space_collider_qualification", "get_particle_candidate_dossier_contract", "list_particle_candidate_dossiers", "get_particle_candidate_dossier", "get_particle_candidate_dossier_postfreeze", "run_particle_candidate_dossier_qualification", "get_scientific_verification_contract", "verify_scientific_evidence_bundle", "resolve_external_scientific_source", "get_post_gate_experiment_portfolio_contract", "rank_post_gate_experiment_portfolio", "post_gate_experiment_quadrants", "get_pharmaceutical_domain_contract", "assess_pharmaceutical_research_record", "get_pharmaceutical_axis_subset", "assess_pharmaceutical_hypothesis", "derive_pharmaceutical_selectivity", "get_pharmaceutical_problem_atlas_contract", "get_pharmaceutical_research_operator_contract", "load_pharmaceutical_problem_atlas", "get_pharmaceutical_problem", "prepare_pharmaceutical_world_cycle", "get_phi_cognitive_core_contract", "get_phi_cognitive_state", "get_phi_communication_contract", "analyze_phi_communication", "synthesize_phi_communication_code", "get_phi_resident_cognitive_contract", "get_phi_resident_state", "scan_phi_open_world", "select_phi_open_world_action", "select_phi_resource_aware_action", "run_phi_missing_representation_blind_world", "select_phi_learned_world_action", "select_phi_contextual_world_action", "prepare_phi_typed_world_action", "run_phi_blind_process_isolation_exam", "run_phi_resident_qualification", "get_phi_knowledge_evolution_contract", "get_phi_knowledge_evolution_state", "assess_phi_candidate_world_binding", "assess_phi_candidate_response_projection", "build_phi_world_attestation", "assess_phi_domain_birth", "assess_phi_axis_lifecycle", "resolve_phi_axis_lifecycle", "discover_phi_cross_domain_bridges", "assess_phi_domain_split", "assess_phi_domain_merge", "run_phi_knowledge_evolution_qualification", "get_phi_mathematical_invention_contract", "discover_phi_unknown_unknown_representation", "synthesize_phi_primitive", "discover_phi_morphism", "assess_phi_controlled_limit", "run_phi_mathematical_invention_qualification", "get_phi_theory_compiler_contract", "synthesize_phi_executable_representation", "compile_phi_theory", "execute_phi_compiled_theory", "run_phi_theory_compiler_qualification", "get_phi_resource_theory_contract", "discover_phi_resource_theory", "run_phi_resource_theory_qualification", "get_phi_discriminating_experiment_contract", "design_phi_discriminating_experiment", "run_phi_discriminating_experiment_qualification", "get_phi_long_horizon_scientific_cycle_contract", "freeze_phi_long_horizon_round", "run_phi_long_horizon_scientific_cycle_qualification", "get_phi_prospective_external_validation_contract", "run_phi_prospective_external_validation", "run_phi_prospective_external_validation_qualification", "get_phi_generation_transition_contract", "search_phi_next_generation_ai", "run_phi_generation_transition_qualification", "get_phi_reflexive_architecture_contract", "get_phi_architecture_state", "run_phi_reflexive_architecture_qualification", "get_phi_runtime_self_repair_contract", "get_phi_runtime_execution_policy", "get_phi_developmental_open_endedness_contract", "search_phi_developmental_open_endedness", "run_phi_developmental_open_endedness_qualification", 
    )
    READ_TOOLS = READ_TOOLS + ("focus_research_question", "search_observations_for_law_candidates", "search_observations_for_function_forms", "get_eda_chip_design_contract", "get_eda_chip_backend_status", "run_eda_chip_design_pilot", "get_scalar_law_birth_current", "get_quantity", "compile_neutrino_multidomain_candidate", "get_adaptive_research_kernel_contract", "advance_adaptive_research", "get_claim_provenance_firewall_contract", "run_energy_space_temperature_axis_control", "run_temperature_energy_adaptive_control", "run_adaptive_research_kernel_qualification", "run_open_void_directed_exploration", "get_science_atlas_core_qualification", "get_universal_law_discovery_contract", "run_universal_law_discovery_qualification", "audit_cross_domain_law_grammar", "run_empirical_multidomain_law_search", "get_tensor_geometry_contract", "run_tensor_geometry_axisymmetric_qualification", "run_axisymmetric_lawvoid_tensor_screen", "get_axisymmetric_lawvoid_postfreeze_assessment", "run_rotating_cubic_euler_solution", "get_rotating_cubic_euler_postfreeze_assessment", "run_tensor_geometry_spin2_odd_qualification", "run_tensor_geometry_horizon_aligned_closure_qualification", "run_tensor_geometry_full_parity_odd_euler_multipole_qualification", "run_spin2_odd_gauge_patch_screen", "get_spin2_odd_postfreeze_assessment", "get_electronic_state_space_search_contract", "search_atomic_electronic_state_space", "run_electronic_many_body_coordinate_blind_experiment", "run_open_ended_periodic_frontier", "run_post118_configuration_identifiability_experiment_design", "run_open_ended_nuclear_binding_decay_world", "get_scientific_axis_space_contract", "search_scientific_axis_space", "get_atlas_law_space_search_contract", "search_atlas_law_space", "qualify_frontier_promotion_path", "get_atlas_dovetail_traversal_state", "get_research_triage_contract", "assess_research_data_quality", "rank_exploration_sandbox", "build_hypothesis_passport", "propose_sandbox_what_if_experiments", "get_hypothesis_council_state", "recommend_hypothesis_council_weights")
    REGRESSION_TOOLS = (
        "run_element_compactness_frontier_probe", "run_blind_per_element_reconstruction",
        "run_phi_space_atomic_interior_hole_qualification", "run_autonomous_atomic_frontier",
        "get_frontier_world_attestation", "get_frontier_higher_order_expansion",
    )
    MUTATION_TOOLS = ("run_autonomous_research", "commit_phi_candidate_world_binding", "commit_phi_candidate_response_projection", "execute_phi_candidate_measurement", "commit_phi_domain_birth", "commit_phi_axis_lifecycle", "commit_phi_domain_split", "commit_phi_domain_merge", "promote_dynamic_axis", "run_axis_modeling_with_dynamic_expansion", "run_phi_cognitive_cycle", "run_phi_generated_axis_cycle", "run_phi_resident_heartbeat", "record_phi_world_action_experience", "learn_phi_world_action_model", "learn_phi_contextual_world_action_model", "online_update_phi_world_action_model", "bind_phi_typed_world_action_result", "evolve_phi_resident_ontology", "evolve_phi_higher_order_operator", "run_phi_resident_long_horizon", "run_phi_reflexive_architecture_cycle", "run_phi_runtime_self_repair_cycle", "run_phi_developmental_open_endedness_cycle", "advance_atlas_dovetail_traversal", "record_hypothesis_council_action", "apply_hypothesis_council_weight_recommendation")
    FORBIDDEN_AI_ASSIGNMENTS = ("ATLAS_NATIVE", "ESTABLISHED_LAW", "CONFIRMED_CONSTANT", "EXPERIMENT_PASS")
    ALLOWED_AI_STATES = ("PENDING_PROPOSAL", "PENDING_BRIDGE", "PENDING_NORMALIZATION", "PENDING_CELL_ASSIGNMENT")

    def __init__(self, root: str | Path) -> None:
        self.runtime = LawSpaceRuntime(root)

    @staticmethod
    def _require_regression_mode(regression_mode: bool, tool_name: str) -> None:
        if regression_mode is not True:
            raise PermissionError(
                f"{tool_name} is a quarantined regression/post-freeze surface; "
                "pass regression_mode=True explicitly. Blind/default research must use the "
                "adaptive kernel and may not read answer-bearing atomic receipts."
            )

    def _atlas_dovetail_revisit_digest(self) -> str:
        """Digest current evidence/representation state without making it a truth gate."""
        dynamic_axis_path = self.runtime.root / "data" / "axes" / "canonical_dynamic_axes.json"
        knowledge_path = self.runtime.root / "data" / "knowledge" / "knowledge_evolution_state.json"
        payload = {
            "evidence": {key: dataclasses.asdict(value) for key, value in sorted(self.runtime.evidence.items())},
            "computational_methods": {key: value.digest for key, value in sorted(self.runtime.computational_methods.items())},
            "quantum_method_routes": [row.get("digest", digest_payload(row)) for row in self.runtime.quantum_method_routes],
            "dynamic_axis_state": json.loads(dynamic_axis_path.read_text(encoding="utf-8")) if dynamic_axis_path.is_file() else None,
            "knowledge_evolution_state": json.loads(knowledge_path.read_text(encoding="utf-8")) if knowledge_path.is_file() else None,
        }
        return digest_payload(payload)

    def _atlas_dovetail_state_path(self, *, mutable: bool) -> Path:
        if mutable:
            return self.runtime.external_state_path("atlas_dovetail_traversal")
        from .candidates import DOVETAIL_STATE_RELATIVE_PATH
        return self.runtime.root / DOVETAIL_STATE_RELATIVE_PATH

    def get_atlas_dovetail_traversal_state(self) -> Mapping[str, Any]:
        from .candidates import load_dovetail_state_file, dovetail_state_status
        external = self._atlas_dovetail_state_path(mutable=True)
        sealed = self._atlas_dovetail_state_path(mutable=False)
        if external.is_file():
            state = load_dovetail_state_file(external); source = "EXTERNAL_MUTABLE_RUNTIME_STATE"; path = external
        elif sealed.is_file():
            state = load_dovetail_state_file(sealed); source = "SEALED_RELEASE_SNAPSHOT"; path = sealed
        else:
            state = None; source = "STATE_NOT_YET_MATERIALIZED"; path = sealed
        status = dovetail_state_status(state)
        payload = {
            "schema": "phi-atlas-dovetail-state-view/v1",
            "owner": "CandidateGenerationPipeline/6.28.0",
            "source": source,
            "path": str(path),
            "state_status": status,
            "state_digest": state.get("digest") if state else None,
            "environment_digest_current": self._atlas_dovetail_revisit_digest(),
            "mutable_state_inside_sealed_tree": False,
            "scientific_truth_assigned_by_traversal": False,
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def run_open_void_directed_exploration(
        self, *, frontier_limit: int = 19, use_mutable_dovetail_state: bool = False
    ) -> Mapping[str, Any]:
        from .candidates import CandidateGenerationPipeline, load_dovetail_state_file
        pipeline = CandidateGenerationPipeline(self.runtime.catalog, self.runtime.bridges)
        state_path = self._atlas_dovetail_state_path(mutable=bool(use_mutable_dovetail_state))
        state = load_dovetail_state_file(state_path) if state_path.is_file() else None
        result = dict(pipeline.run_open_void_directed_exploration(
            frontier_limit=frontier_limit, traversal_state=state,
            revisit_digest=self._atlas_dovetail_revisit_digest(), dovetail_steps=0,
        ))
        result["dovetail_state_source"] = "EXTERNAL_MUTABLE_RUNTIME_STATE" if use_mutable_dovetail_state and state else ("SEALED_RELEASE_SNAPSHOT" if state else "INITIALIZED_IN_MEMORY")
        result["baseline_candidate_registry_count"] = len(self.runtime.candidates)
        result["baseline_candidate_registry_used_as_solution_source"] = False
        result["digest"] = digest_payload({k: v for k, v in result.items() if k != "digest"})
        return result

    def advance_atlas_dovetail_traversal(self, *, step_budget: int = 32) -> Mapping[str, Any]:
        """Advance one finite tranche of the same fair open-ended traversal.

        ``step_budget`` bounds only this call.  It is deliberately not a scientific
        search ceiling; repeated calls resume from the content-addressed external
        state and preserve every older node/cursor.
        """
        from .candidates import CandidateGenerationPipeline, load_dovetail_state_file, write_dovetail_state_file, dovetail_state_status
        steps = int(step_budget)
        if steps < 1:
            raise ValueError("step_budget must be positive")
        external = self._atlas_dovetail_state_path(mutable=True)
        sealed = self._atlas_dovetail_state_path(mutable=False)
        if external.is_file():
            state = load_dovetail_state_file(external); source = "EXTERNAL_MUTABLE_RUNTIME_STATE"
        elif sealed.is_file():
            state = load_dovetail_state_file(sealed); source = "SEALED_RELEASE_SNAPSHOT"
        else:
            state = None; source = "INITIAL_STATE"
        pipeline = CandidateGenerationPipeline(self.runtime.catalog, self.runtime.bridges)
        result = dict(pipeline.run_open_void_directed_exploration(
            frontier_limit=19, traversal_state=state, revisit_digest=self._atlas_dovetail_revisit_digest(),
            dovetail_steps=steps,
        ))
        adaptive = dict(result.get("adaptive_multidimensional_subspace_exploration", {}))
        new_state = adaptive.get("dovetail_state")
        if dovetail_state_status(new_state).get("valid") is not True:
            raise RuntimeError("dovetail advance did not produce a valid persistent state")
        write_dovetail_state_file(external, new_state)
        payload = {
            "schema": "phi-atlas-dovetail-advance/v1",
            "owner": "CandidateGenerationPipeline/6.28.0",
            "status": "DOVETAIL_TRANCHE_COMMITTED",
            "state_source_before": source,
            "external_state_path": str(external),
            "step_budget_this_call": steps,
            "fixed_global_step_ceiling": None,
            "state_digest": new_state.get("digest"),
            "last_advance": new_state.get("last_advance", {}),
            "node_count": len(dict(new_state.get("nodes", {}))),
            "materialized_candidate_count_in_view": adaptive.get("candidate_count"),
            "local_search_shell_max": max((int(row.get("local_search_shell", 0)) for row in new_state.get("nodes", {}).values()), default=0),
            "old_nodes_deleted": False,
            "scientific_truth_assigned": False,
        }
        payload["digest"] = digest_payload(payload)
        return payload

    def run_element_compactness_frontier_probe(self, *, regression_mode: bool = False) -> Mapping[str, Any]:
        self._require_regression_mode(regression_mode, "run_element_compactness_frontier_probe")
        from .candidates import CandidateGenerationPipeline
        pipeline = CandidateGenerationPipeline(self.runtime.catalog, self.runtime.bridges)
        result = dict(pipeline.run_element_compactness_frontier_probe(self.runtime.root, regression_mode=True))
        result["baseline_candidate_registry_count"] = len(self.runtime.candidates)
        result["baseline_candidate_registry_used_as_solution_source"] = False
        result["digest"] = digest_payload({k: v for k, v in result.items() if k != "digest"})
        return result

    def run_blind_per_element_reconstruction(self, *, regression_mode: bool = False) -> Mapping[str, Any]:
        self._require_regression_mode(regression_mode, "run_blind_per_element_reconstruction")
        from .candidates import CandidateGenerationPipeline
        pipeline = CandidateGenerationPipeline(self.runtime.catalog, self.runtime.bridges)
        return pipeline.run_blind_per_element_reconstruction(self.runtime.root, regression_mode=True)

    def run_phi_space_atomic_interior_hole_qualification(self, *, regression_mode: bool = False) -> Mapping[str, Any]:
        self._require_regression_mode(regression_mode, "run_phi_space_atomic_interior_hole_qualification")
        from .candidates import CandidateGenerationPipeline
        pipeline = CandidateGenerationPipeline(self.runtime.catalog, self.runtime.bridges)
        return pipeline.run_phi_space_atomic_interior_hole_qualification(self.runtime.root, regression_mode=True)

    def run_autonomous_atomic_frontier(self, *, regression_mode: bool = False) -> Mapping[str, Any]:
        self._require_regression_mode(regression_mode, "run_autonomous_atomic_frontier")
        from .atomic_frontier import AutonomousAtomicFrontierOwner
        return AutonomousAtomicFrontierOwner().run_until_stop()

    def get_frontier_world_attestation(self, *, regression_mode: bool = False) -> Mapping[str, Any]:
        """Return the post-freeze world-attestation ledger with digest verification.

        This is an evidence-binding read surface, not a scientific promotion owner.
        It preserves the pre-freeze frontier/experiment identities and never turns
        prior-art presence or absence into truth/falsity by itself.
        """
        self._require_regression_mode(regression_mode, "get_frontier_world_attestation")
        path = self.runtime.root / "reports" / "FRONTIER_WORLD_ATTESTATION_CURRENT.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        embedded = payload.get("digest")
        body = {k: v for k, v in payload.items() if k != "digest"}
        if embedded != digest_payload(body):
            raise ValueError("frontier world-attestation digest mismatch")
        return payload

    def get_frontier_higher_order_expansion(self, *, regression_mode: bool = False) -> Mapping[str, Any]:
        """Return the digest-bound higher-order post-freeze continuation; never a blind/default source."""
        self._require_regression_mode(regression_mode, "get_frontier_higher_order_expansion")
        from .candidates import frontier_higher_order_expansion
        return frontier_higher_order_expansion(self.runtime.root)

    def get_electronic_state_space_search_contract(self) -> Mapping[str, Any]:
        from .atomic_frontier import ElectronicStateSpaceSearchOwner
        return ElectronicStateSpaceSearchOwner(self.runtime.root).contract()

    def search_atomic_electronic_state_space(self, z: int, **kwargs: Any) -> Mapping[str, Any]:
        """Authoritative owner-connected electronic state-space search.

        Unlike the quarantined historical frontier replay, this surface does not
        read answer-bearing periodic configurations or element exception tables.
        """
        from .atomic_frontier import ElectronicStateSpaceSearchOwner
        return ElectronicStateSpaceSearchOwner(self.runtime.root).search(int(z), **kwargs)

    def run_electronic_many_body_coordinate_blind_experiment(self, **kwargs: Any) -> Mapping[str, Any]:
        """Run the response-frozen many-body coordinate birth and blind structural transfer test."""
        from .atomic_frontier import ElectronicStateSpaceSearchOwner
        return ElectronicStateSpaceSearchOwner(self.runtime.root).run_many_body_coordinate_blind_experiment(**kwargs)

    def run_open_ended_periodic_frontier(
        self,
        z_values: Sequence[int] | None = None,
        *,
        materialize_candidate_set: bool = False,
    ) -> Mapping[str, Any]:
        from .periodic_reconstruction import AtomicOpenEndedFrontierOwner
        return AtomicOpenEndedFrontierOwner(self.runtime.root).run(
            z_values=z_values,
            materialize_candidate_set=materialize_candidate_set,
        )

    def run_post118_configuration_identifiability_experiment_design(self) -> Mapping[str, Any]:
        """Compatibility preview only; authoritative logic is open-ended."""
        return self.run_open_ended_periodic_frontier(
            z_values=tuple(range(119, 125)),
            materialize_candidate_set=True,
        )

    def run_open_ended_nuclear_binding_decay_world(
        self,
        *,
        start_z: int = 119,
        attested_nuclides: Sequence[Mapping[str, Any]] | None = None,
        z_values: Sequence[int] | None = None,
    ) -> Mapping[str, Any]:
        from .periodic_reconstruction import OpenEndedNuclearBindingDecayWorldOwner
        return OpenEndedNuclearBindingDecayWorldOwner(self.runtime.root).run(
            start_z=start_z,
            attested_nuclides=attested_nuclides,
            z_values=z_values,
        )


    def focus_research_question(self, *, question: str, named_observables: Sequence[str],
                                expansion_limit: int = 30) -> Mapping[str, Any]:
        """Convert a question plus explicit observables into an auditable focused quantity neighborhood."""
        from .query_research import QueryDrivenResearchOwner
        return QueryDrivenResearchOwner().focus_question(catalog=self.runtime.catalog, question=question,
                                                          named_observables=named_observables,
                                                          quantity_registry=self.runtime.quantities,
                                                          expansion_limit=expansion_limit)

    def search_observations_for_law_candidates(self, *, observations: Mapping[str, Sequence[float]],
                                                   dimensions: Mapping[str, Sequence[int]],
                                                   target_name: str | None = None,
                                                   question: str | None = None,
                                                   return_limit: int = 25,
                                                   min_subset_size: int = 2,
                                                   max_subset_size: int | None = None,
                                                   permutation_count: int = 0,
                                                   permutation_seed: int = 0) -> Mapping[str, Any]:
        """Focused query mode: observations -> 10..100 ranked mathematical candidates."""
        from .query_research import QueryDrivenResearchOwner
        return QueryDrivenResearchOwner().search_observations(
            observations=observations, dimensions=dimensions, target_name=target_name,
            question=question, return_limit=return_limit, min_subset_size=min_subset_size,
            max_subset_size=max_subset_size, permutation_count=permutation_count,
            permutation_seed=permutation_seed,
        )


    def search_observations_for_function_forms(self, *, observations: Mapping[str, Sequence[float]],
                                                dimensions: Mapping[str, Sequence[int]],
                                                target_name: str, axis_names: Sequence[str] | None = None,
                                                question: str | None = None, return_limit: int = 25,
                                                hypothesis_budget: int = 100,
                                                group_ids: Sequence[str] | None = None,
                                                permutation_count: int = 0,
                                                permutation_seed: int = 0,
                                                function_language_birth: bool = True,
                                                language_birth_nrmse: float = 0.08) -> Mapping[str, Any]:
        """Focused p>1 query lane: exact Pi basis -> competing F(Pi-vector) surfaces."""
        from .query_research import QueryDrivenResearchOwner
        return QueryDrivenResearchOwner().search_function_forms(
            observations=observations, dimensions=dimensions, target_name=target_name,
            axis_names=axis_names, question=question, return_limit=return_limit,
            hypothesis_budget=hypothesis_budget, group_ids=group_ids,
            permutation_count=permutation_count, permutation_seed=permutation_seed,
            function_language_birth=function_language_birth, language_birth_nrmse=language_birth_nrmse,
        )


    def get_eda_chip_design_contract(self) -> Mapping[str, Any]:
        """Return the fail-closed Atlas/OpenROAD chip-design research contract."""
        from .eda_chip_design import EDAChipDesignResearchOwner
        return EDAChipDesignResearchOwner().contract()

    def get_eda_chip_backend_status(self, *, orfs_flow_root: str | None = None, runner: str = "auto") -> Mapping[str, Any]:
        """Inspect whether a real ORFS/OpenROAD world backend is executable."""
        from .eda_chip_design import EDAChipDesignResearchOwner
        return EDAChipDesignResearchOwner().backend_status(orfs_flow_root=orfs_flow_root, runner=runner)

    def run_eda_chip_design_pilot(self, *, orfs_flow_root: str | None = None, runner: str = "auto",
                                  evaluation_budget: int = 18, warm_start_count: int = 12,
                                  candidate_pool_size: int = 256, seed: int = 15260,
                                  timeout_seconds: int = 1800) -> Mapping[str, Any]:
        """Run equal-budget Atlas/random/grid/Bayesian PPA search on real sky130hd/gcd ORFS."""
        from .eda_chip_design import EDAChipDesignResearchOwner
        return EDAChipDesignResearchOwner().run_pilot(
            orfs_flow_root=orfs_flow_root, runner=runner, evaluation_budget=evaluation_budget,
            warm_start_count=warm_start_count, candidate_pool_size=candidate_pool_size,
            seed=seed, timeout_seconds=timeout_seconds,
        )

    def get_atlas_law_space_search_contract(self) -> Mapping[str, Any]:
        from .scientific_axis_space import AtlasLawSpaceSearchOwner
        return AtlasLawSpaceSearchOwner().contract()

    def search_atlas_law_space(
        self, *, variable_names: Sequence[str], values: Sequence[Sequence[float]],
        target_values: Sequence[float], target_name: str, quantity_specs: Mapping[str, Mapping[str, Any]],
        domain_ids: Sequence[str] = ("physics", "metrology"), search_shell: int = 0,
    ) -> Mapping[str, Any]:
        from .scientific_axis_space import AtlasLawSpaceSearchOwner
        return AtlasLawSpaceSearchOwner().discover(
            variable_names=variable_names, values=values, target_values=target_values,
            target_name=target_name, quantity_specs=quantity_specs, domain_ids=tuple(domain_ids), search_shell=int(search_shell),
        )

    def get_scientific_axis_space_contract(self) -> Mapping[str, Any]:
        from .scientific_axis_space import ScientificAxisSpaceOwner
        return ScientificAxisSpaceOwner().contract()

    def search_scientific_axis_space(
        self, *, variable_names: Sequence[str], values: Sequence[Sequence[float]],
        target_values: Sequence[float], target_name: str, quantity_specs: Mapping[str, Mapping[str, Any]],
        domain_ids: Sequence[str] = ("physics", "metrology"), search_shell: int = 0,
    ) -> Mapping[str, Any]:
        from .scientific_axis_space import ScientificAxisSpaceOwner
        return ScientificAxisSpaceOwner().discover(
            variable_names=variable_names, values=values, target_values=target_values,
            target_name=target_name, quantity_specs=quantity_specs, domain_ids=tuple(domain_ids), search_shell=int(search_shell),
        )

    def get_science_atlas_core_qualification(self) -> Mapping[str, Any]:
        from .science_atlas_core import ScienceAtlasCoreKernel
        return ScienceAtlasCoreKernel(self.runtime.root).run_qualification()

    def get_tensor_geometry_contract(self) -> Mapping[str, Any]:
        from .tensor_geometry import TensorGeometryOwner
        return TensorGeometryOwner().contract()

    def run_tensor_geometry_axisymmetric_qualification(self) -> Mapping[str, Any]:
        from .tensor_geometry import TensorGeometryOwner
        return TensorGeometryOwner().run_stationary_axisymmetric_slow_rotation_qualification()

    def run_axisymmetric_lawvoid_tensor_screen(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().run_axisymmetric_lawvoid_tensor_screen()

    def get_axisymmetric_lawvoid_postfreeze_assessment(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().get_axisymmetric_lawvoid_postfreeze_assessment()

    def run_rotating_cubic_euler_solution(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().run_rotating_cubic_euler_solution()

    def get_rotating_cubic_euler_postfreeze_assessment(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().get_rotating_cubic_euler_postfreeze_assessment()

    def run_tensor_geometry_spin2_odd_qualification(self) -> Mapping[str, Any]:
        from .tensor_geometry import TensorGeometryOwner
        return TensorGeometryOwner().run_spin2_even_odd_gauge_qualification()

    def run_tensor_geometry_horizon_aligned_closure_qualification(self) -> Mapping[str, Any]:
        from .tensor_geometry import TensorGeometryOwner
        return TensorGeometryOwner().run_horizon_aligned_spin2_odd_closure_qualification()

    def run_tensor_geometry_full_parity_odd_euler_multipole_qualification(self) -> Mapping[str, Any]:
        from .tensor_geometry import TensorGeometryOwner
        return TensorGeometryOwner().run_full_parity_odd_euler_multipole_qualification()

    def run_spin2_odd_gauge_patch_screen(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().run_spin2_odd_gauge_patch_screen()

    def get_spin2_odd_postfreeze_assessment(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().get_spin2_odd_postfreeze_assessment()

    def get_universal_law_discovery_contract(self) -> Mapping[str, Any]:
        from .law_discovery import UniversalLawDiscoveryOwner
        return UniversalLawDiscoveryOwner(self.runtime.root).contract()

    def run_universal_law_discovery_qualification(self) -> Mapping[str, Any]:
        from .law_discovery import UniversalLawDiscoveryOwner
        return UniversalLawDiscoveryOwner(self.runtime.root).run_qualification()

    def audit_cross_domain_law_grammar(self) -> Mapping[str, Any]:
        from .law_discovery import UniversalLawDiscoveryOwner
        return UniversalLawDiscoveryOwner(self.runtime.root).cross_domain_blind_benchmark()

    def run_empirical_multidomain_law_search(self) -> Mapping[str, Any]:
        from .law_discovery import UniversalLawDiscoveryOwner
        return UniversalLawDiscoveryOwner(self.runtime.root).empirical_multidomain_audit()

    def search_entities(self, query: str, domain_id: str | None = None, limit: int = 20) -> list[Mapping[str, Any]]:
        return [dataclasses.asdict(p) for p in self.runtime.catalog.search(query, domain_id=domain_id, limit=limit)]

    def get_passport(self, owner_id: str) -> Mapping[str, Any]:
        return dataclasses.asdict(self.runtime.catalog.get_passport(owner_id))

    def resolve_symbol(self, symbol: str) -> list[Mapping[str, Any]]:
        result = []
        for passport in self.runtime.catalog.passports.values():
            for record in passport.symbols:
                if record.display == symbol or record.symbol_id == symbol:
                    result.append({"owner_id": passport.owner_id, **dataclasses.asdict(record)})
        return sorted(result, key=lambda x: (x["owner_id"], x["symbol_id"]))

    def resolve_constant(self, constant_id_or_symbol: str) -> Mapping[str, Any]:
        if constant_id_or_symbol in self.runtime.constants:
            return self.runtime.constants[constant_id_or_symbol]
        for record in self.runtime.constants.values():
            if record.get("symbol") == constant_id_or_symbol:
                return record
        raise KeyError(constant_id_or_symbol)

    def resolve_candidate_quantities(self, candidate_id: str) -> Mapping[str, Any]:
        candidate = self.get_candidate(candidate_id)
        contract = candidate.get("property_inheritance_contract", {})
        partition = contract.get("symbol_partition", {})
        constant_by_symbol = {str(row.get("symbol")): row for row in self.runtime.constants.values()}
        introduced = list(partition.get("introduced_quantity_symbols", []))
        resolved_constants = {symbol: constant_by_symbol[symbol] for symbol in introduced if symbol in constant_by_symbol}
        unresolved = [symbol for symbol in introduced if symbol not in resolved_constants]
        return {
            "candidate_id": candidate_id,
            "scientific_status": candidate.get("scientific_status"),
            "inherited_source_symbols": partition.get("inherited_source_symbols", []),
            "introduced_quantity_symbols": introduced,
            "resolved_registered_constants": resolved_constants,
            "unresolved_quantities": unresolved,
            "resolution_protocol": contract.get("quantity_resolution_protocol", []),
        }

    def find_by_dimensions(self, vector: Sequence[str]) -> list[Mapping[str, Any]]:
        return [dataclasses.asdict(p) for p in self.runtime.catalog.find_by_dimensions(vector)]

    def find_home_cell(self, owner_id: str) -> Mapping[str, Any]:
        return dataclasses.asdict(self.runtime.catalog.find_home_cell(owner_id))

    def find_composition_path(self, source_domains: Sequence[str], target_type: str | None = None) -> list[Mapping[str, Any]]:
        return [dataclasses.asdict(b) for b in self.runtime.find_composition_path(source_domains, target_type)]

    def compare_models(self, owner_ids: Sequence[str]) -> Mapping[str, Any]:
        rows = [self.runtime.catalog.get_passport(owner_id) for owner_id in owner_ids]
        return {
            "owners": [p.owner_id for p in rows],
            "domains": [p.domain_id for p in rows],
            "epistemic_states": [p.epistemic_state for p in rows],
            "formula_digests": [p.formula.digest for p in rows],
            "same_home_cell": len({p.home_cell_id for p in rows}) == 1,
        }


    def search_candidates(
        self, *, domain_id: str | None = None, generator_id: str | None = None,
        category: str | None = None, risk_class: str | None = None,
        source_owner_id: str | None = None, limit: int = 100,
    ) -> list[Mapping[str, Any]]:
        rows = []
        for row in self.runtime.candidates:
            if domain_id and domain_id not in row.get("target_domains", ()): continue
            if generator_id and row.get("generator", {}).get("generator_id") != generator_id: continue
            if category and category not in row.get("classification", {}).get("categories", ()): continue
            if risk_class and row.get("classification", {}).get("risk_class") != risk_class: continue
            if source_owner_id and source_owner_id not in row.get("source_owner_ids", ()): continue
            rows.append(row)
        return rows[:max(0, int(limit))]

    def get_candidate(self, candidate_id: str) -> Mapping[str, Any]:
        for row in self.runtime.candidates:
            if row.get("candidate_id") == candidate_id or row.get("owner_id") == candidate_id:
                return row
        raise KeyError(candidate_id)

    def get_deep_formula_candidates(self, limit: int = 20) -> list[Mapping[str, Any]]:
        """Return materialized deep-search hypotheses; no search logic lives in the API."""
        rows = [
            row for row in self.runtime.candidates
            if row.get("generator", {}).get("search_mode") == "DETERMINISTIC_OWNER_HYPERGRAPH_TARGET_TERMINATED"
        ]
        return rows[:max(0, int(limit))]

    def search_computational_methods(self, capability: str | None = None, role: str | None = None, limit: int = 100) -> list[Mapping[str, Any]]:
        rows = []
        for method in self.runtime.computational_methods.values():
            if capability and capability not in method.capabilities:
                continue
            if role and method.role != role:
                continue
            rows.append(dataclasses.asdict(method))
        return rows[:max(0, int(limit))]

    def search_quantum_method_routes(self, capability: str | None = None, limit: int = 100) -> list[Mapping[str, Any]]:
        rows = []
        for row in self.runtime.quantum_method_routes:
            if capability and capability not in row.get("covered_capabilities", []):
                continue
            rows.append(row)
        return rows[:max(0, int(limit))]

    def get_quantum_method_route(self, route_id: str) -> Mapping[str, Any]:
        for row in self.runtime.quantum_method_routes:
            if row.get("route_id") == route_id:
                return row
        raise KeyError(route_id)



    def get_scalar_law_birth_current(self) -> Mapping[str, Any]:
        """Return the digest-bound current dimensional scalar-law birth census."""
        path=self.runtime.root / "data" / "frontiers" / "ATLAS_SCALAR_LAW_BIRTH_CURRENT.json"
        payload=json.loads(path.read_text(encoding="utf-8"))
        embedded=str(payload.get("digest",""))
        body={k:v for k,v in payload.items() if k!="digest"}
        if embedded != digest_payload(body):
            raise ValueError("scalar law birth current digest mismatch")
        return payload

    def get_quantity(self, quantity_id: str) -> Mapping[str, Any]:
        return self.runtime.quantities[quantity_id]

    def compile_neutrino_multidomain_candidate(self, *, candidate_id: str, geometry: str, microparameters: Mapping[str, Any]) -> Mapping[str, Any]:
        from .neutrino import NeutrinoPhenomenologyOwner
        spec = self.runtime.compile_neutrino_multidomain_spec(candidate_id=candidate_id, geometry=geometry, microparameters=microparameters)
        micro, candidate = NeutrinoPhenomenologyOwner().lower_multidomain_lawspace_spec(spec)
        ir = NeutrinoPhenomenologyOwner().micro_to_ir(micro)
        return {
            "derivation": spec,
            "candidate": candidate.to_dict(),
            "microparameters": micro.to_dict(),
            "geometry_ir": ir.geometry_ir.to_dict(),
            "kk_convergence": ir.kk_convergence.to_dict(),
            "takagi_spectrum": ir.takagi_spectrum.to_dict(),
            "claim_boundary": "LAWSPACE_DERIVED_OWNER_EXECUTED_NOT_EMPIRICAL_DISCOVERY",
        }

    def get_neutrino_owner_contract(self) -> Mapping[str, Any]:
        from .neutrino import NeutrinoPhenomenologyOwner
        return NeutrinoPhenomenologyOwner().contract()

    def get_neutrino_intersection_law_contract(self) -> Mapping[str, Any]:
        from .neutrino import NeutrinoLawIntersectionClosureOwner
        return NeutrinoLawIntersectionClosureOwner(self.runtime.root).contract()

    def search_neutrino_source_laws(
        self, *, novelty_status_contains: str | None = None, limit: int = 100,
    ) -> list[Mapping[str, Any]]:
        from .neutrino import NeutrinoLawIntersectionClosureOwner
        return NeutrinoLawIntersectionClosureOwner(self.runtime.root).search_source_laws(
            novelty_status_contains=novelty_status_contains, limit=limit,
        )

    def get_neutrino_source_law(self, owner_id: str) -> Mapping[str, Any]:
        from .neutrino import NeutrinoLawIntersectionClosureOwner
        return NeutrinoLawIntersectionClosureOwner(self.runtime.root).get_source_law(owner_id)

    def search_neutrino_intersection_laws(
        self, *, source_owner_id: str | None = None, classification: str | None = None,
        novelty_status_contains: str | None = None, min_intersection_order: int = 0,
        closure_family_id: str | None = None, limit: int = 1000,
    ) -> list[Mapping[str, Any]]:
        from .neutrino import NeutrinoLawIntersectionClosureOwner
        return NeutrinoLawIntersectionClosureOwner(self.runtime.root).search(
            source_owner_id=source_owner_id, classification=classification,
            novelty_status_contains=novelty_status_contains,
            min_intersection_order=min_intersection_order, closure_family_id=closure_family_id, limit=limit,
        )

    def get_neutrino_intersection_law(self, law_id: str) -> Mapping[str, Any]:
        from .neutrino import NeutrinoLawIntersectionClosureOwner
        return NeutrinoLawIntersectionClosureOwner(self.runtime.root).get_law(law_id)

    def get_aeronautics_intersection_law_contract(self) -> Mapping[str, Any]:
        from .aeronautics import AeronauticsLawIntersectionClosureOwner
        return AeronauticsLawIntersectionClosureOwner(self.runtime.root).contract()

    def search_aeronautics_source_laws(self, *, limit: int = 100) -> list[Mapping[str, Any]]:
        from .aeronautics import AeronauticsLawIntersectionClosureOwner
        return AeronauticsLawIntersectionClosureOwner(self.runtime.root).search_source_laws(limit=limit)

    def get_aeronautics_source_law(self, owner_id: str) -> Mapping[str, Any]:
        from .aeronautics import AeronauticsLawIntersectionClosureOwner
        return AeronauticsLawIntersectionClosureOwner(self.runtime.root).get_source_law(owner_id)

    def search_aeronautics_intersection_laws(
        self, *, source_owner_id: str | None = None, classification: str | None = None,
        novelty_status_contains: str | None = None, min_intersection_order: int | None = None,
        limit: int = 100,
    ) -> list[Mapping[str, Any]]:
        from .aeronautics import AeronauticsLawIntersectionClosureOwner
        return AeronauticsLawIntersectionClosureOwner(self.runtime.root).search(
            source_owner_id=source_owner_id, classification=classification,
            novelty_status_contains=novelty_status_contains, min_intersection_order=min_intersection_order or 0,
            limit=limit,
        )

    def get_aeronautics_intersection_law(self, law_id: str) -> Mapping[str, Any]:
        from .aeronautics import AeronauticsLawIntersectionClosureOwner
        return AeronauticsLawIntersectionClosureOwner(self.runtime.root).get_law(law_id)

    def compile_aeronautics_intersection_spec(self, *, candidate_id: str) -> Mapping[str, Any]:
        return self.runtime.compile_aeronautics_intersection_spec(candidate_id=candidate_id)

    def get_quantum_vacuum_gravity_contract(self) -> Mapping[str, Any]:
        from .quantum_vacuum import QuantumVacuumGravityIntersectionOwner
        return QuantumVacuumGravityIntersectionOwner(self.runtime.root).contract()

    def search_quantum_vacuum_source_laws(self, *, owner_id_contains: str | None = None, limit: int = 100) -> list[Mapping[str, Any]]:
        from .quantum_vacuum import QuantumVacuumGravityIntersectionOwner
        return QuantumVacuumGravityIntersectionOwner(self.runtime.root).search_source_laws(owner_id_contains=owner_id_contains, limit=limit)

    def get_quantum_vacuum_source_law(self, owner_id: str) -> Mapping[str, Any]:
        from .quantum_vacuum import QuantumVacuumGravityIntersectionOwner
        return QuantumVacuumGravityIntersectionOwner(self.runtime.root).get_source_law(owner_id)

    def search_quantum_vacuum_intersection_laws(
        self, *, source_owner_id: str | None = None, classification: str | None = None,
        novelty_status_contains: str | None = None, min_intersection_order: int = 0, limit: int = 200,
    ) -> list[Mapping[str, Any]]:
        from .quantum_vacuum import QuantumVacuumGravityIntersectionOwner
        return QuantumVacuumGravityIntersectionOwner(self.runtime.root).search(
            source_owner_id=source_owner_id, classification=classification,
            novelty_status_contains=novelty_status_contains, min_intersection_order=min_intersection_order, limit=limit,
        )

    def get_quantum_vacuum_intersection_law(self, law_id: str) -> Mapping[str, Any]:
        from .quantum_vacuum import QuantumVacuumGravityIntersectionOwner
        return QuantumVacuumGravityIntersectionOwner(self.runtime.root).get_law(law_id)

    def compile_quantum_vacuum_gravity_spec(self, *, candidate_id: str) -> Mapping[str, Any]:
        return self.runtime.compile_quantum_vacuum_gravity_spec(candidate_id=candidate_id)

    def get_constraint_atlas_contract(self) -> Mapping[str, Any]:
        from .constraint_atlas import ConstraintAtlasOwner
        return ConstraintAtlasOwner(self.runtime.root).contract()

    def get_constraint_atlas_qualification(self) -> Mapping[str, Any]:
        from .constraint_atlas import ConstraintAtlasOwner
        return ConstraintAtlasOwner(self.runtime.root).run_qualification()

    def derive_constraint_atlas_circuit(
        self, *, source_owner_ids: Sequence[str], retain_symbols: Sequence[str]
    ) -> Mapping[str, Any]:
        from .constraint_atlas import ConstraintAtlasOwner
        return dataclasses.asdict(
            ConstraintAtlasOwner(self.runtime.root).derive_circuit(source_owner_ids, retain_symbols)
        )

    def scan_constraint_atlas_unknown_frontier(
        self, *, execution_budget: Mapping[str, int] | None = None
    ) -> Mapping[str, Any]:
        from .constraint_atlas import ConstraintAtlasOwner
        return ConstraintAtlasOwner(self.runtime.root).scan_unknown_frontier(execution_budget=execution_budget)

    def scan_constraint_atlas_operator_unknown_frontier(
        self, *, execution_budget: Mapping[str, int] | None = None
    ) -> Mapping[str, Any]:
        from .constraint_atlas import ConstraintAtlasOwner
        return ConstraintAtlasOwner(self.runtime.root).scan_operator_unknown_frontier(execution_budget=execution_budget)

    def build_constraint_atlas_aeroelastic_projection_bridge(
        self, *, mode_count: int = 4, quadrature_points: int = 4001
    ) -> Mapping[str, Any]:
        from .constraint_atlas import ConstraintAtlasOwner
        return ConstraintAtlasOwner(self.runtime.root).build_aeroelastic_projection_bridge(
            mode_count=mode_count, quadrature_points=quadrature_points
        )

    def discover_constraint_atlas_temporal_kernel(
        self, *, times: Sequence[float], driving_signal: Sequence[float], response_residual: Sequence[float],
        memory_horizon: float, regularization: float = 1.0, train_fraction: float = 0.65,
    ) -> Mapping[str, Any]:
        from .constraint_atlas import ConstraintAtlasOwner
        return ConstraintAtlasOwner(self.runtime.root).discover_temporal_convolution_kernel(
            times, driving_signal, response_residual,
            memory_horizon=memory_horizon, regularization=regularization, train_fraction=train_fraction,
        )

    def discover_constraint_atlas_spatial_nonlocal_kernel(
        self, *, input_fields: Sequence[Sequence[float]], output_fields: Sequence[Sequence[float]],
        regularization: float = 1e-8, train_sample_count: int | None = None,
    ) -> Mapping[str, Any]:
        from .constraint_atlas import ConstraintAtlasOwner
        return ConstraintAtlasOwner(self.runtime.root).discover_spatial_nonlocal_kernel(
            input_fields, output_fields, regularization=regularization, train_sample_count=train_sample_count,
        )

    def get_constraint_atlas_real_gust_aero_lag_discovery(self) -> Mapping[str, Any]:
        from .constraint_atlas import ConstraintAtlasOwner
        return ConstraintAtlasOwner(self.runtime.root).run_real_gust_aero_lag_discovery_qualification()

    def get_constraint_atlas_real_gust_full_research_cycle(self) -> Mapping[str, Any]:
        from .constraint_atlas import ConstraintAtlasOwner
        return ConstraintAtlasOwner(self.runtime.root).run_real_gust_mechanism_competition_research_cycle()

    def analyze_constraint_atlas_probe_wing_modal_discriminator(
        self, *, gust_runs: Sequence[Mapping[str, Any]], modal_decay_records: Sequence[Mapping[str, Any]],
        probe_to_wing_distance_m: float, nominal_modal_frequency_hz: float, nominal_damping_ratio: float,
    ) -> Mapping[str, Any]:
        from .constraint_atlas import ConstraintAtlasOwner
        return ConstraintAtlasOwner(self.runtime.root).evaluate_probe_to_wing_modal_discriminator(
            gust_runs=gust_runs, modal_decay_records=modal_decay_records,
            probe_to_wing_distance_m=probe_to_wing_distance_m,
            nominal_modal_frequency_hz=nominal_modal_frequency_hz,
            nominal_damping_ratio=nominal_damping_ratio,
        )

    def get_constraint_atlas_probe_wing_modal_discriminator_qualification(self) -> Mapping[str, Any]:
        from .constraint_atlas import ConstraintAtlasOwner
        return ConstraintAtlasOwner(self.runtime.root).run_probe_to_wing_modal_discriminator_qualification()

    def get_constraint_atlas_low_frequency_gust_anomaly_analysis(self) -> Mapping[str, Any]:
        from .constraint_atlas import ConstraintAtlasOwner
        return ConstraintAtlasOwner(self.runtime.root).analyze_low_frequency_gust_anomaly_public_evidence()

    def get_neutrino_blind_discovery_contract(self) -> Mapping[str, Any]:
        from .neutrino import BlindNeutrinoDiscoveryOwner
        return BlindNeutrinoDiscoveryOwner().contract()

    def get_neutrino_postfreeze_novelty_contract(self) -> Mapping[str, Any]:
        from .neutrino_global_combination import NeutrinoPostFreezeNoveltyAuditOwner
        return NeutrinoPostFreezeNoveltyAuditOwner().contract()

    def compute_neutrino_probability(
        self, *, initial_flavour: int, final_flavour: int, baseline_km: float, energy_gev: float,
        matter_density_g_cm3: float | None = None, electron_fraction: float = 0.5, antineutrino: bool = False,
    ) -> Mapping[str, Any]:
        from .neutrino import MatterLayer, NeutrinoPhenomenologyOwner
        owner = NeutrinoPhenomenologyOwner()
        if matter_density_g_cm3 is None:
            matrix = owner.vacuum_probability_matrix(baseline_km, energy_gev, antineutrino=antineutrino)
            route = "THREE_NEUTRINO_VACUUM"
        else:
            matrix = owner.matter_probability_matrix(
                energy_gev, (MatterLayer(baseline_km, matter_density_g_cm3, electron_fraction),), antineutrino=antineutrino
            )
            route = "THREE_NEUTRINO_CONSTANT_MATTER"
        if initial_flavour not in (0, 1, 2) or final_flavour not in (0, 1, 2):
            raise ValueError("flavour indices must be 0=e, 1=mu, 2=tau")
        return {
            "owner_id": "NEUTRINO-PHENOMENOLOGY",
            "route": route,
            "initial_flavour": initial_flavour,
            "final_flavour": final_flavour,
            "baseline_km": baseline_km,
            "energy_gev": energy_gev,
            "probability": float(matrix[final_flavour, initial_flavour]),
            "column_normalization_residual": float(abs(matrix[:, initial_flavour].sum() - 1.0)),
            "claim_boundary": "COMPUTED_WITHIN_DECLARED_OSCILLATION_MODEL_NOT_EVIDENCE_FOR_NEW_PHYSICS",
        }


    def get_neutrino_algebraic_contract(self) -> Mapping[str, Any]:
        from .algebraic_experiment import NeutrinoAlgebraicExperimentalOwner
        return NeutrinoAlgebraicExperimentalOwner().contract()

    def get_neutrino_real_data_contract(self) -> Mapping[str, Any]:
        from .neutrino_real_data import NeutrinoRealDataLikelihoodOwner
        return NeutrinoRealDataLikelihoodOwner(self.runtime.root).contract()

    def evaluate_neutrino_real_data_candidate(self, *, candidate_id: str, family: str, candidate_parameters: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        from .neutrino_real_data import NeutrinoRealDataLikelihoodOwner
        return NeutrinoRealDataLikelihoodOwner(self.runtime.root).evaluate_candidate(candidate_id, family, candidate_parameters)


    def get_dayabay_likelihood_contract(self) -> Mapping[str, Any]:
        from .dayabay_full_likelihood import DayaBayFullLikelihoodOwner
        return DayaBayFullLikelihoodOwner(self.runtime.root).contract()

    def get_katrin_likelihood_contract(self) -> Mapping[str, Any]:
        from .katrin_spectral_likelihood import KATRINSpectralLikelihoodOwner
        return KATRINSpectralLikelihoodOwner(self.runtime.root).contract()

    def get_t2k_likelihood_contract(self) -> Mapping[str, Any]:
        from .t2k_published_likelihood import T2KPublishedLikelihoodOwner
        return T2KPublishedLikelihoodOwner(self.runtime.root).contract()

    def get_superk_atmospheric_likelihood_contract(self) -> Mapping[str, Any]:
        from .superk_atmospheric_likelihood import SuperKAtmosphericLikelihoodOwner
        return SuperKAtmosphericLikelihoodOwner(self.runtime.root).contract()

    def get_superk_solar_likelihood_contract(self) -> Mapping[str, Any]:
        from .superk_solar_likelihood import SuperKSolarLikelihoodOwner
        return SuperKSolarLikelihoodOwner(self.runtime.root).contract()

    def get_neutrino_external_constraints_contract(self) -> Mapping[str, Any]:
        from .neutrino_external_constraints import NeutrinoExternalConstraintsOwner
        return NeutrinoExternalConstraintsOwner().contract()

    def get_neutrino_global_contract(self) -> Mapping[str, Any]:
        from .neutrino_global_combination import NeutrinoGlobalCombinationOwner
        return NeutrinoGlobalCombinationOwner(self.runtime.root).contract()


    def get_scientific_data_ingestion_contract(self) -> Mapping[str, Any]:
        from .scientific_data_ingestion import ScientificDataIngestionOwner
        return ScientificDataIngestionOwner(self.runtime.root).contract()

    def propose_candidate(self, proposal: Mapping[str, Any]) -> Mapping[str, Any]:
        state = str(proposal.get("epistemic_state", "PENDING_PROPOSAL"))
        if state not in self.ALLOWED_AI_STATES:
            raise PermissionError(f"AI cannot assign active state {state}")
        origin = str(proposal.get("claim_origin", "ASSISTANT_HYPOTHESIS")).upper()
        if origin == "ATLAS_NATIVE":
            raise PermissionError("AI proposal API cannot assign ATLAS_NATIVE; only CLAIM-PROVENANCE-FIREWALL may stamp it from a valid execution receipt")
        payload = dict(proposal)
        payload["epistemic_state"] = state
        payload["claim_origin"] = origin
        payload["atlas_native"] = False
        payload["active_registry_mutation"] = False
        payload["provenance_level"] = "DECLARED"
        payload["promotion_allowed"] = False
        payload["scientific_inference_status"] = "ENGINE_NOT_RUN_SCIENTIFIC_INFERENCE_BLOCKED"
        payload["proposal_digest"] = digest_payload(payload)
        return payload


    def get_scientific_verification_contract(self) -> Mapping[str, Any]:
        from .scientific_verification import ScientificVerificationCore
        return ScientificVerificationCore().contract()

    def verify_scientific_evidence_bundle(
        self, bundle: Mapping[str, Any], *, required_entity_slots: Sequence[str] = (),
        allowed_entity_states: Mapping[str, Sequence[str]] | None = None,
    ) -> Mapping[str, Any]:
        from .scientific_verification import ScientificVerificationCore
        return ScientificVerificationCore().verify_bundle(
            dict(bundle), required_entity_slots=tuple(required_entity_slots),
            allowed_entity_states=allowed_entity_states,
        )

    def resolve_external_scientific_source(
        self, *, identifier_type: str, identifier: str, expected_title: str = "", resolver_url: str = "",
    ) -> Mapping[str, Any]:
        from .scientific_verification import ExternalSourceResolutionOwner
        return ExternalSourceResolutionOwner().resolve(
            identifier_type=identifier_type, identifier=identifier, expected_title=expected_title, resolver_url=resolver_url,
        )


    def get_research_triage_contract(self) -> Mapping[str, Any]:
        from .research_triage import ResearchTriageSandbox
        return ResearchTriageSandbox.contract()

    def assess_research_data_quality(
        self, *, y: Sequence[float] | None = None, sigma: Sequence[float] | None = None,
        n_points: int | None = None, relative_uncertainty: float | None = None, domain: str = "UNSPECIFIED",
    ) -> Mapping[str, Any]:
        from .research_triage import ResearchTriageSandbox
        return ResearchTriageSandbox.assess_data_quality(
            y=y, sigma=sigma, n_points=n_points, relative_uncertainty=relative_uncertainty, domain=domain
        )

    def rank_exploration_sandbox(
        self, *, hypotheses: Sequence[Mapping[str, Any]], weights: Mapping[str, float] | None = None, dpi_threshold: float = 0.70,
    ) -> Mapping[str, Any]:
        from .research_triage import ResearchTriageSandbox
        state = ResearchTriageSandbox.load_council_state(self.runtime.external_state_path("hypothesis_council"))
        effective = weights if weights is not None else state.get("sandbox_weights")
        return ResearchTriageSandbox.rank_hypotheses(hypotheses, weights=effective, dpi_threshold=dpi_threshold)

    def build_hypothesis_passport(
        self, *, hypothesis: Mapping[str, Any], quality: Mapping[str, Any],
        weights: Mapping[str, float] | None = None, axis_summaries: Sequence[Mapping[str, Any]] = (),
    ) -> Mapping[str, Any]:
        from .research_triage import ResearchTriageSandbox
        state = ResearchTriageSandbox.load_council_state(self.runtime.external_state_path("hypothesis_council"))
        effective = weights if weights is not None else state.get("sandbox_weights")
        return ResearchTriageSandbox.build_passport(
            hypothesis=hypothesis, quality=quality, weights=effective, axis_summaries=axis_summaries
        )

    def propose_sandbox_what_if_experiments(
        self, *, axis_summaries: Sequence[Mapping[str, Any]], count: int = 2,
    ) -> Mapping[str, Any]:
        from .research_triage import ResearchTriageSandbox
        return ResearchTriageSandbox.propose_what_if_experiments(axis_summaries=axis_summaries, count=count)

    def get_hypothesis_council_state(self) -> Mapping[str, Any]:
        from .research_triage import ResearchTriageSandbox
        path = self.runtime.external_state_path("hypothesis_council")
        state = dict(ResearchTriageSandbox.load_council_state(path))
        state["state_path"] = str(path)
        state["state_inside_sealed_tree"] = False
        state["strict_u_gates_modified"] = False
        return state

    def record_hypothesis_council_action(
        self, *, candidate_id: str, action: str, reason: str, expert_id: str = "LOCAL_EXPERT",
        linked_candidate_ids: Sequence[str] = (), feature_snapshot: Mapping[str, float] | None = None,
    ) -> Mapping[str, Any]:
        from .research_triage import ResearchTriageSandbox
        path = self.runtime.external_state_path("hypothesis_council")
        state = ResearchTriageSandbox.load_council_state(path)
        out = ResearchTriageSandbox.record_council_action(
            state=state, candidate_id=candidate_id, action=action, reason=reason, expert_id=expert_id,
            linked_candidate_ids=linked_candidate_ids, feature_snapshot=feature_snapshot,
        )
        ResearchTriageSandbox.write_council_state(path, out)
        return {**dict(out), "state_path": str(path), "strict_u_gates_modified": False}

    def recommend_hypothesis_council_weights(self) -> Mapping[str, Any]:
        from .research_triage import ResearchTriageSandbox
        state = ResearchTriageSandbox.load_council_state(self.runtime.external_state_path("hypothesis_council"))
        return ResearchTriageSandbox.recommend_sandbox_weights_from_council(state)

    def apply_hypothesis_council_weight_recommendation(self) -> Mapping[str, Any]:
        from .research_triage import ResearchTriageSandbox
        path = self.runtime.external_state_path("hypothesis_council")
        state = dict(ResearchTriageSandbox.load_council_state(path))
        rec = dict(ResearchTriageSandbox.recommend_sandbox_weights_from_council(state))
        if rec.get("status") != "SANDBOX_WEIGHT_RECOMMENDATION_READY":
            return {**rec, "applied": False, "state_path": str(path)}
        state["sandbox_weights"] = dict(rec["weights_recommended"])
        state["revision"] = int(state.get("revision", 0)) + 1
        ResearchTriageSandbox.write_council_state(path, state)
        return {**rec, "applied": True, "state_path": str(path), "strict_promotion_weights_changed": False}

    def get_scientific_promotion_contract(self) -> Mapping[str, Any]:
        from .scientific_promotion import ScientificPromotionCore
        return ScientificPromotionCore().contract()

    def evaluate_scientific_promotion(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        from .scientific_promotion import ScientificPromotionCore
        trusted = tuple(self.runtime.catalog.passports) + ("SCIENTIFIC-PROMOTION-QUALIFICATION",)
        return ScientificPromotionCore(trusted_evidence_owners=trusted).evaluate(dict(request))

    def qualify_frontier_promotion_path(
        self, record: Mapping[str, Any], *, controls: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Run the single fail-closed promotion path for a persistent/future frontier record."""
        from .scientific_promotion import ScientificPromotionCore
        trusted = tuple(self.runtime.catalog.passports) + ("SCIENTIFIC-PROMOTION-QUALIFICATION",)
        return ScientificPromotionCore(trusted_evidence_owners=trusted).qualify_frontier_record(
            dict(record), controls=dict(controls or {}),
        )

    def get_scientific_inference_status(self, receipt: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        from .scientific_promotion import ScientificPromotionCore
        return ScientificPromotionCore.inference_status(receipt)

    def run_scientific_promotion_qualification(self) -> Mapping[str, Any]:
        from evaluation.scientific_promotion_benchmark import run_release_qualification
        return run_release_qualification()


    def get_axis_modeling_contract(self) -> Mapping[str, Any]:
        from .axis_modeling import AxisModelingOwner
        return AxisModelingOwner().contract()

    def run_axis_modeling(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        from .axis_modeling import AxisModelingOwner
        return AxisModelingOwner().run(dict(request))

    def run_axis_modeling_realdata_qualification(self) -> Mapping[str, Any]:
        from evaluation.axis_modeling_realdata_qualification import run_release_qualification
        return run_release_qualification(self.runtime.root)

    def get_dynamic_axis_promotion_contract(self) -> Mapping[str, Any]:
        from .research_cycle import DynamicAxisPromotionOwner
        return DynamicAxisPromotionOwner(self.runtime.root).contract()

    def get_dynamic_axis_registry_state(self) -> Mapping[str, Any]:
        from .domains import dynamic_axis_registry_state
        return dynamic_axis_registry_state()

    def get_common_scientific_rules_contract(self) -> Mapping[str, Any]:
        from .scientific_rules import CommonScientificRulesCore
        return CommonScientificRulesCore().contract()

    def get_domain_plugin_registry_contract(self) -> Mapping[str, Any]:
        from .domain_plugins import ScienceDomainPluginRegistry
        return ScienceDomainPluginRegistry().contract()

    def list_domain_plugins(self) -> list[Mapping[str, Any]]:
        from .domain_plugins import ScienceDomainPluginRegistry
        return ScienceDomainPluginRegistry().list_plugins()

    def get_domain_plugin_contract(self, domain_id: str) -> Mapping[str, Any]:
        from .domain_plugins import ScienceDomainPluginRegistry
        return ScienceDomainPluginRegistry().get_domain_contract(domain_id)


    def get_black_hole_lab_contract(self) -> Mapping[str, Any]:
        from .black_hole import BlackHoleLabOwner
        return BlackHoleLabOwner().contract()

    def evaluate_black_hole_lab(self, candidate_id: str, *, mass_kg: float, radius_m: float, ell_q_m: float = 1.616255e-35, beta: float = 1.0, memory_time_s: float | None = None, entropy_gradient_scale: float | None = None, causal_order_parameter: float | None = None) -> Mapping[str, Any]:
        from .black_hole import BlackHoleLabOwner
        return BlackHoleLabOwner().evaluate(candidate_id, mass_kg=mass_kg, radius_m=radius_m, ell_q_m=ell_q_m, beta=beta, memory_time_s=memory_time_s, entropy_gradient_scale=entropy_gradient_scale, causal_order_parameter=causal_order_parameter)

    def run_black_hole_lab_qualification(self) -> Mapping[str, Any]:
        from .black_hole import BlackHoleLabOwner
        return BlackHoleLabOwner().qualification()

    def get_black_hole_dynamic_contract(self) -> Mapping[str, Any]:
        from .black_hole import BlackHoleLabOwner
        return BlackHoleLabOwner().dynamic_contract()

    def run_black_hole_vaidya_benchmark(self, *, mass0_kg: float = 1.98847e30, duration_s: float = 1.0, mass_fraction_change: float = 1.0e-3, orientation: str = "INGOING") -> Mapping[str, Any]:
        from .black_hole import BlackHoleLabOwner
        return BlackHoleLabOwner().run_vaidya_benchmark(mass0_kg=mass0_kg, duration_s=duration_s, mass_fraction_change=mass_fraction_change, orientation=orientation)

    def assess_black_hole_dynamic_closure(self, candidate_id: str) -> Mapping[str, Any]:
        from .black_hole import BlackHoleLabOwner
        return BlackHoleLabOwner().assess_dynamic_closure(candidate_id)

    def get_einstein_dynamics_contract(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().contract()

    def analyze_einstein_adaptive_axes(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().adaptive_axis_analysis()

    def derive_spherical_einstein_equations(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().derive_spherical_equations()

    def solve_einstein_exact_sector(self, sector_id: str) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().solve_exact_sector(sector_id)

    def derive_einstein_massless_scalar_system(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().derive_massless_scalar_cauchy_system()

    def run_einstein_massless_scalar_pre_horizon_benchmark(self, *, amplitude: float = 1.0e-3, r_max: float = 20.0, t_final: float = 0.5, center: float = 7.0, width: float = 1.5) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().run_massless_scalar_pre_horizon_benchmark(amplitude=amplitude, r_max=r_max, t_final=t_final, center=center, width=width)

    def derive_einstein_massless_scalar_horizon_penetrating_system(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().derive_massless_scalar_horizon_penetrating_system()

    def run_einstein_massless_scalar_horizon_formation_benchmark(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().run_massless_scalar_horizon_formation_benchmark()

    def run_blind_covariant_operator_search(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().run_blind_covariant_operator_search()

    def derive_frozen_blind_operator_black_hole_solution(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().derive_frozen_blind_operator_black_hole_solution()

    def continue_blind_covariant_operator_search_after_prior_art_kill(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().continue_blind_covariant_operator_search_after_prior_art_kill()

    def get_blind_covariant_operator_postfreeze_assessment(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().get_blind_covariant_operator_postfreeze_assessment()

    def run_blind_representation_branch_search(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().run_blind_representation_branch_search()

    def derive_frozen_auxiliary_branch_black_hole_solution(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().derive_frozen_auxiliary_branch_black_hole_solution()

    def get_blind_representation_postfreeze_assessment(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().get_blind_representation_postfreeze_assessment()

    def continue_blind_representation_search_after_auxiliary_kill(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().continue_blind_representation_search_after_auxiliary_kill()

    def continue_auxiliary_branch_after_prior_art_kill(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().continue_auxiliary_branch_after_prior_art_kill()

    def get_auxiliary_cubic_postfreeze_assessment(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().get_auxiliary_cubic_postfreeze_assessment()

    def run_causal_nonlocal_memory_discriminant(self, *, tau: float = 1.0, radius: float = 6.0, bump_amplitude: float = 0.25) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().run_causal_nonlocal_memory_discriminant(tau=tau, radius=radius, bump_amplitude=bump_amplitude)

    def run_blind_causal_nonlocal_metric_closure_search(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().run_blind_causal_nonlocal_metric_closure_search()

    def run_frozen_causal_nonlocal_metric_closure_experiment(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().run_frozen_causal_nonlocal_metric_closure_experiment()

    def get_causal_nonlocal_metric_closure_postfreeze_assessment(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().get_causal_nonlocal_metric_closure_postfreeze_assessment()

    def run_causal_nonlocal_metric_closure_qualification(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().run_causal_nonlocal_metric_closure_qualification()

    def get_curvature_memory_covariant_closure(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner()._curvature_memory_exact_covariant_closure()

    def run_curvature_memory_order_reduced_black_hole_experiment(self, *, beta: float = 0.05) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().run_curvature_memory_order_reduced_black_hole_experiment(beta=beta)

    def run_curvature_memory_closure_qualification(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().run_curvature_memory_closure_qualification()

    def rank_blind_representation_frontier(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().rank_blind_representation_frontier()

    def run_blind_representation_qualification(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().run_blind_representation_qualification()

    def assess_general_4d_einstein_problem(self, *, coordinate_condition: str = "UNDECLARED", pde_formulation_class: str = "UNDECLARED", matter_closure_relation: str = "UNDECLARED", initial_data_construction_method: str = "UNDECLARED", numerical_boundary_condition_class: str = "UNDECLARED", constraint_control_scheme: str = "UNDECLARED") -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().assess_general_4d_problem(
            coordinate_condition=coordinate_condition,
            pde_formulation_class=pde_formulation_class,
            matter_closure_relation=matter_closure_relation,
            initial_data_construction_method=initial_data_construction_method,
            numerical_boundary_condition_class=numerical_boundary_condition_class,
            constraint_control_scheme=constraint_control_scheme,
        )

    def run_einstein_dynamics_qualification(self) -> Mapping[str, Any]:
        from .einstein_dynamics import EinsteinDynamicsOwner
        return EinsteinDynamicsOwner().qualification()

    def promote_dynamic_axis(self, proposal: Mapping[str, Any], validation: Mapping[str, Any], *, mutate: bool = True) -> Mapping[str, Any]:
        from .research_cycle import DynamicAxisPromotionOwner, DynamicAxisProposal
        return DynamicAxisPromotionOwner(self.runtime.root).evaluate_and_promote(
            DynamicAxisProposal(**dict(proposal)), dict(validation), mutate=bool(mutate)
        )

    def run_axis_modeling_with_dynamic_expansion(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        from .axis_modeling import AxisModelingOwner
        from .research_cycle import DynamicAxisPromotionOwner, DynamicAxisProposal
        payload = dict(request)
        promotion_cfg = dict(payload.pop("canonical_promotion", {}) or {})
        modeling = AxisModelingOwner().run(payload)
        admission = modeling.get("semantic_axis_admission")
        if not admission or admission.get("status") != "ADMITTED_PROVISIONAL_RESEARCH_AXIS":
            return {
                "modeling": modeling,
                "promotion": {"status": "NO_PROMOTABLE_AXIS_BIRTH"},
                "canonical_registry_mutated": False,
            }
        if not promotion_cfg:
            return {
                "modeling": modeling,
                "promotion": {"status": "VALIDATION_REQUIRED_BEFORE_CANONICAL_MUTATION"},
                "canonical_registry_mutated": False,
            }
        best = dict(modeling.get("best_axis_birth") or {})
        validation = dict(promotion_cfg.get("validation", {}))
        validation.setdefault("measurement_uncertainty_declared", bool(modeling.get("dataset", {}).get("measurement_uncertainty_declared")))
        validation.setdefault("identifiability_pass", bool(best.get("derived_feature_identifiability_pass")))
        validation.setdefault("ood_pass", best.get("status") == "AXIS_BIRTH_OOD_VALIDATED")
        validation.setdefault("ood_fractional_improvement", float(best.get("ood_rmse_fractional_improvement", 0.0)))
        validation.setdefault("complexity_penalized_delta_log_likelihood", float(best.get("axis_score", 0.0)))
        validation.setdefault("derivation", str(best.get("generated_coordinate", "")))
        proposal = DynamicAxisProposal(**dict(admission["proposal"]))
        receipt = DynamicAxisPromotionOwner(self.runtime.root).evaluate_and_promote(
            proposal, validation, mutate=bool(promotion_cfg.get("mutate", True))
        )
        return {
            "modeling": modeling,
            "promotion": receipt,
            "canonical_registry_mutated": bool(receipt.get("claim_boundary", {}).get("canonical_axis_registered")),
        }


    def get_pharmaceutical_domain_contract(self) -> Mapping[str, Any]:
        from .pharmaceutical import PharmaceuticalDomainOwner
        return PharmaceuticalDomainOwner().contract()

    def assess_pharmaceutical_research_record(self, record: Mapping[str, Any]) -> Mapping[str, Any]:
        from .pharmaceutical import PharmaceuticalDomainOwner
        return PharmaceuticalDomainOwner().assess_research_record(dict(record))

    def get_pharmaceutical_axis_subset(self, axis_ids: Sequence[str]) -> Mapping[str, Any]:
        from .pharmaceutical import PharmaceuticalDomainOwner
        return PharmaceuticalDomainOwner().axis_subset(axis_ids)

    def derive_pharmaceutical_selectivity(self, selectivity_profile: Mapping[str, Any]) -> Mapping[str, Any]:
        from .pharmaceutical import PharmaceuticalDomainOwner
        return PharmaceuticalDomainOwner().derive_selectivity_from_profile(dict(selectivity_profile))

    def assess_pharmaceutical_hypothesis(
        self, coordinate: Mapping[str, Any], evidence: Mapping[str, Any] | None = None,
        verification_bundle: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        from .pharmaceutical import PharmaceuticalDomainOwner
        return PharmaceuticalDomainOwner().assess_hypothesis(
            dict(coordinate), dict(evidence or {}), dict(verification_bundle or {}),
        )


    def get_pharmaceutical_problem_atlas_contract(self) -> Mapping[str, Any]:
        from .pharmaceutical_problem_atlas import PharmaceuticalProblemAtlasOwner
        return PharmaceuticalProblemAtlasOwner().contract()

    def get_pharmaceutical_research_operator_contract(self) -> Mapping[str, Any]:
        from .pharmaceutical_problem_atlas import PharmaceuticalResearchOperatorOwner
        return PharmaceuticalResearchOperatorOwner().contract()

    def load_pharmaceutical_problem_atlas(self, atlas_path: str | Path | None = None) -> Mapping[str, Any]:
        from .pharmaceutical_problem_atlas import PharmaceuticalProblemAtlasOwner
        path = Path(atlas_path) if atlas_path is not None else self.runtime.root / "data" / "pharmaceutical" / "pharmaceutical_problem_atlas_v8_3.json"
        return PharmaceuticalProblemAtlasOwner().load_atlas(path)

    def get_pharmaceutical_problem(self, problem_id: str, atlas_path: str | Path | None = None) -> Mapping[str, Any]:
        atlas = self.load_pharmaceutical_problem_atlas(atlas_path)
        for row in atlas.get("rows", ()):
            if str(row.get("problem_id")) == str(problem_id):
                return row
        raise KeyError(problem_id)

    def prepare_pharmaceutical_world_cycle(
        self, problem_id: str, atlas_path: str | Path | None = None,
        verification_bundle: Mapping[str, Any] | None = None,
        predictive_model_receipt: Mapping[str, Any] | None = None,
        predictive_verification_bundle: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        from .pharmaceutical_problem_atlas import PharmaceuticalProblemAtlasOwner
        problem = self.get_pharmaceutical_problem(problem_id, atlas_path)
        return PharmaceuticalProblemAtlasOwner().prepare_world_cycle(
            problem, verification_bundle=verification_bundle,
            predictive_model_receipt=predictive_model_receipt,
            predictive_verification_bundle=predictive_verification_bundle,
        )

    def get_particle_space_contract(self) -> Mapping[str, Any]:
        from .particle_space import ParticleSpaceOwner
        return ParticleSpaceOwner().contract()

    def enumerate_particle_space(self, bounds: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        from .particle_space import ParticleSpaceBounds, ParticleSpaceOwner
        b = ParticleSpaceBounds(**dict(bounds or {}))
        owner = ParticleSpaceOwner()
        cells = owner.enumerate_cells(b)
        return {
            "contract": owner.contract(),
            "summary": owner.census_summary(b),
            "cells": cells,
        }

    def search_particle_space_cells(
        self, *, status: str | None = None, spin: str | None = None,
        sector_tag: str | None = None, su3_label: str | None = None,
        su2_dimension: int | None = None, global_form: str | None = None,
        global_form_compatible: bool | None = None, limit: int = 100, postfreeze: bool = True,
    ) -> list[Mapping[str, Any]]:
        import json
        path = self.runtime.root / "data" / "particles" / (
            "particle_space_census_postfreeze_v7_3.jsonl" if postfreeze
            else "particle_space_census_v7_3.jsonl"
        )
        if not path.exists():
            raise FileNotFoundError(path)
        rows = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                c = row.get("coordinate", {})
                if status and row.get("status") != status: continue
                if spin and c.get("spin") != spin: continue
                if sector_tag and sector_tag not in row.get("sector_tags", ()): continue
                if su3_label and c.get("su3_label") != su3_label: continue
                if su2_dimension is not None and int(c.get("su2_dimension", -1)) != int(su2_dimension): continue
                if global_form is not None:
                    branch = row.get("global_form_axis", {}).get("branches", {}).get(global_form)
                    if branch is None: continue
                    if global_form_compatible is not None and branch.get("compatible") is not global_form_compatible: continue
                rows.append(row)
                if len(rows) >= max(0, int(limit)): break
        return rows

    def get_particle_space_cell(self, particle_id: str, *, postfreeze: bool = True) -> Mapping[str, Any]:
        rows = self.search_particle_space_cells(limit=1000000, postfreeze=postfreeze)
        for row in rows:
            if row.get("particle_id") == particle_id:
                return row
        raise KeyError(particle_id)

    def get_particle_space_postfreeze_summary(self) -> Mapping[str, Any]:
        import json
        path = self.runtime.root / "reports" / "PARTICLE_SPACE_POSTFREEZE_CENSUS_CURRENT.json"
        if not path.exists():
            raise FileNotFoundError(path)
        return json.loads(path.read_text(encoding="utf-8"))


    def get_particle_space_global_form_summary(self) -> Mapping[str, Any]:
        post = self.get_particle_space_postfreeze_summary()
        return post["summary"]["global_form_axis"]

    def run_particle_space_whole_representation_blind(self) -> Mapping[str, Any]:
        from .particle_space import ParticleSpaceBounds, ParticleSpaceOwner
        return ParticleSpaceOwner().whole_representation_blind_benchmark(ParticleSpaceBounds(spins=("1/2",)))

    def run_particle_space_blind_discovery(self) -> Mapping[str, Any]:
        from .particle_space import ParticleSpaceBounds, ParticleSpaceOwner
        return ParticleSpaceOwner().blind_discovery_freeze(ParticleSpaceBounds(), neighbour_count=12, shortlist_count=32)

    def close_particle_space_coordinate(
        self, *, spin: str, su3_dynkin: Sequence[int], su2_dimension: int, hypercharge: Any,
        copy: int = 1, field_realization: str, selected_global_form: str | None = None,
        selection_provenance: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        from .particle_space import ParticleSpaceOwner
        return ParticleSpaceOwner().close_coordinate(
            spin=spin, su3_dynkin=su3_dynkin, su2_dimension=su2_dimension,
            hypercharge=hypercharge, copy=copy, field_realization=field_realization,
            selected_global_form=selected_global_form, selection_provenance=selection_provenance,
        )

    def run_particle_space_census_qualification(self) -> Mapping[str, Any]:
        from evaluation.particle_space_census_qualification import run_release_qualification
        return run_release_qualification()

    def get_particle_space_collider_qualification_contract(self) -> Mapping[str, Any]:
        from .particle_collider import ParticleColliderQualification
        return ParticleColliderQualification().contract()

    def evaluate_particle_space_d7_reference(self, mass_tev: float, lambda_eff_tev: float) -> Mapping[str, Any]:
        from .particle_collider import ParticleColliderQualification
        return ParticleColliderQualification.d7_reference_point(mass_tev, lambda_eff_tev)

    def get_particle_space_recast_technical_gate(self) -> Mapping[str, Any]:
        import json
        path = self.runtime.root / "reports" / "particle_space_recast_technical_gate_status_current.json"
        if not path.exists():
            raise FileNotFoundError(path)
        return json.loads(path.read_text(encoding="utf-8"))

    def run_particle_space_collider_qualification(self) -> Mapping[str, Any]:
        from evaluation.particle_space_collider_qualification import run_release_qualification
        return run_release_qualification(self.runtime.root)

    def get_particle_candidate_dossier_contract(self) -> Mapping[str, Any]:
        from .particle_candidate_dossiers import ParticleCandidateDossierOwner
        return ParticleCandidateDossierOwner().contract()

    def list_particle_candidate_dossiers(self) -> list[Mapping[str, Any]]:
        from .particle_candidate_dossiers import ParticleCandidateDossierOwner
        return ParticleCandidateDossierOwner().build_internal_dossiers()

    def get_particle_candidate_dossier(self, candidate_id: str) -> Mapping[str, Any]:
        from .particle_candidate_dossiers import ParticleCandidateDossierOwner
        return ParticleCandidateDossierOwner().get(candidate_id)

    def get_particle_candidate_dossier_postfreeze(self, candidate_id: str) -> Mapping[str, Any]:
        import json
        path = self.runtime.root / "reports" / "PARTICLE_CANDIDATE_DOSSIERS_POSTFREEZE_CURRENT.json"
        if not path.exists():
            raise FileNotFoundError(path)
        receipt = json.loads(path.read_text(encoding="utf-8"))
        for row in receipt.get("dossiers", []):
            if row.get("candidate_id") == candidate_id:
                return row
        raise KeyError(candidate_id)

    def run_particle_candidate_dossier_qualification(self) -> Mapping[str, Any]:
        from evaluation.particle_candidate_dossier_qualification import run_release_qualification
        return run_release_qualification(self.runtime.root)

    def get_phi_cognitive_core_contract(self) -> Mapping[str, Any]:
        from .cognitive_core import PhiCognitiveCore
        return PhiCognitiveCore(self.runtime).contract()

    def get_phi_cognitive_state(self) -> Mapping[str, Any]:
        from .cognitive_core import PhiCognitiveCore
        return PhiCognitiveCore(self.runtime).memory.load()

    def run_phi_cognitive_cycle(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        from .cognitive_core import PhiCognitiveCore
        return PhiCognitiveCore(self.runtime).run(request, commit=True)

    def run_phi_generated_axis_cycle(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        from .cognitive_core import PhiCognitiveCore
        return PhiCognitiveCore(self.runtime).run_generated_axis_cycle(request, commit=True)

    def get_phi_communication_contract(self) -> Mapping[str, Any]:
        from .cognitive_core import PhiCommunicationOwner
        return PhiCommunicationOwner().contract()

    def analyze_phi_communication(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        from .cognitive_core import PhiCognitiveCore
        return PhiCognitiveCore(self.runtime).communication.analyze(request)

    def synthesize_phi_communication_code(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        from .cognitive_core import PhiCognitiveCore
        return PhiCognitiveCore(self.runtime).communication.synthesize_code(request)

    def get_phi_resident_cognitive_contract(self) -> Mapping[str, Any]:
        from .resident_cognitive import ResidentCognitiveOrganism
        return ResidentCognitiveOrganism(self.runtime).contract()

    def get_phi_resident_state(self) -> Mapping[str, Any]:
        from .resident_cognitive import ResidentCognitiveOrganism
        return ResidentCognitiveOrganism(self.runtime).state.load()

    def scan_phi_open_world(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        from .resident_cognitive import ResidentCognitiveOrganism
        return ResidentCognitiveOrganism(self.runtime).scan_open_world(request)

    def select_phi_open_world_action(self, freeze: Mapping[str, Any], request: Mapping[str, Any]) -> Mapping[str, Any]:
        from .resident_cognitive import ResidentCognitiveOrganism
        return ResidentCognitiveOrganism(self.runtime).select_open_world_action(freeze, request)

    def run_phi_resident_heartbeat(self, event: Mapping[str, Any]) -> Mapping[str, Any]:
        from .resident_cognitive import ResidentCognitiveOrganism
        return ResidentCognitiveOrganism(self.runtime).heartbeat(event, commit=True)

    def record_phi_world_action_experience(self, experience: Mapping[str, Any]) -> Mapping[str, Any]:
        from .resident_cognitive import ResidentCognitiveOrganism
        return ResidentCognitiveOrganism(self.runtime).record_world_action_experience(experience, commit=True)

    def learn_phi_world_action_model(self, min_pair_support: int = 3) -> Mapping[str, Any]:
        from .resident_cognitive import ResidentCognitiveOrganism
        return ResidentCognitiveOrganism(self.runtime).learn_world_action_model(commit=True, min_pair_support=min_pair_support)

    def learn_phi_contextual_world_action_model(self, min_pair_support: int = 3) -> Mapping[str, Any]:
        from .resident_cognitive import ResidentCognitiveOrganism
        return ResidentCognitiveOrganism(self.runtime).learn_contextual_nonstationary_world_action_model(commit=True, min_pair_support=min_pair_support)

    def select_phi_learned_world_action(self, freeze: Mapping[str, Any], request: Mapping[str, Any]) -> Mapping[str, Any]:
        from .resident_cognitive import ResidentCognitiveOrganism
        return ResidentCognitiveOrganism(self.runtime).select_action_from_learned_world_model(freeze, request)

    def select_phi_contextual_world_action(self, freeze: Mapping[str, Any], request: Mapping[str, Any]) -> Mapping[str, Any]:
        from .resident_cognitive import ResidentCognitiveOrganism
        return ResidentCognitiveOrganism(self.runtime).select_action_from_contextual_world_model(freeze, request)

    def online_update_phi_world_action_model(self, min_pair_support: int = 3) -> Mapping[str, Any]:
        from .resident_cognitive import ResidentCognitiveOrganism
        return ResidentCognitiveOrganism(self.runtime).online_update_world_action_model(commit=True, min_pair_support=min_pair_support)

    def prepare_phi_typed_world_action(self, envelope: Mapping[str, Any]) -> Mapping[str, Any]:
        from .resident_cognitive import ResidentCognitiveOrganism
        return ResidentCognitiveOrganism(self.runtime).prepare_typed_world_action(envelope, commit=True)

    def bind_phi_typed_world_action_result(self, prepared: Mapping[str, Any], result: Mapping[str, Any]) -> Mapping[str, Any]:
        from .resident_cognitive import ResidentCognitiveOrganism
        return ResidentCognitiveOrganism(self.runtime).bind_typed_world_action_result(prepared, result)

    def run_phi_blind_process_isolation_exam(self) -> Mapping[str, Any]:
        from .resident_cognitive import ResidentCognitiveOrganism
        return ResidentCognitiveOrganism(self.runtime).run_blind_process_isolation_exam()

    def select_phi_resource_aware_action(self, freeze: Mapping[str, Any], request: Mapping[str, Any]) -> Mapping[str, Any]:
        from .resident_cognitive import ResidentCognitiveOrganism
        return ResidentCognitiveOrganism(self.runtime).select_resource_aware_action(freeze, request)

    def run_phi_missing_representation_blind_world(self, request: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        from .resident_cognitive import ResidentCognitiveOrganism
        return ResidentCognitiveOrganism(self.runtime).run_missing_representation_blind_world(request)

    def evolve_phi_resident_ontology(self, concepts: Sequence[Mapping[str, Any]], evidence: Mapping[str, Any]) -> Mapping[str, Any]:
        from .resident_cognitive import ResidentCognitiveOrganism
        return ResidentCognitiveOrganism(self.runtime).ontology.evolve(concepts, evidence)

    def evolve_phi_higher_order_operator(self, operators: Sequence[Mapping[str, Any]], stress_receipts: Sequence[Mapping[str, Any]], composition_receipt: Mapping[str, Any]) -> Mapping[str, Any]:
        from .resident_cognitive import ResidentCognitiveOrganism
        return ResidentCognitiveOrganism(self.runtime).higher_operators.evolve(operators, stress_receipts, composition_receipt)

    def run_phi_resident_long_horizon(self, events: Sequence[Mapping[str, Any]], budget: Mapping[str, float], consolidation_interval: int = 16) -> Mapping[str, Any]:
        from .resident_cognitive import ResidentCognitiveOrganism
        return ResidentCognitiveOrganism(self.runtime).run_long_horizon(events, budget=budget, consolidation_interval=consolidation_interval, commit=True)

    def run_phi_resident_qualification(self) -> Mapping[str, Any]:
        from .resident_cognitive import ResidentCognitiveOrganism
        return ResidentCognitiveOrganism.run_qualification(self.runtime.root)


    def get_phi_knowledge_evolution_contract(self) -> Mapping[str, Any]:
        from .knowledge_evolution import KnowledgeEvolutionKernel
        return KnowledgeEvolutionKernel(self.runtime.root).contract()

    def get_phi_knowledge_evolution_state(self) -> Mapping[str, Any]:
        from .knowledge_evolution import KnowledgeEvolutionKernel
        return KnowledgeEvolutionKernel(self.runtime.root).state()

    def assess_phi_candidate_world_binding(self, candidate_id: str, dataset_id: str) -> Mapping[str, Any]:
        from .knowledge_evolution import KnowledgeEvolutionKernel
        return KnowledgeEvolutionKernel(self.runtime.root).assess_candidate_world_binding(candidate_id=candidate_id, dataset_id=dataset_id)

    def commit_phi_candidate_world_binding(self, receipt: Mapping[str, Any]) -> Mapping[str, Any]:
        from .knowledge_evolution import KnowledgeEvolutionKernel
        return KnowledgeEvolutionKernel(self.runtime.root).commit_candidate_world_binding(receipt)

    def assess_phi_candidate_response_projection(self, candidate_id: str, dataset_id: str, response_projection_id: str) -> Mapping[str, Any]:
        from .knowledge_evolution import KnowledgeEvolutionKernel
        return KnowledgeEvolutionKernel(self.runtime.root).assess_candidate_response_projection(
            candidate_id=candidate_id, dataset_id=dataset_id, response_projection_id=response_projection_id,
        )

    def commit_phi_candidate_response_projection(self, receipt: Mapping[str, Any]) -> Mapping[str, Any]:
        from .knowledge_evolution import KnowledgeEvolutionKernel
        return KnowledgeEvolutionKernel(self.runtime.root).commit_candidate_response_projection(receipt)

    def execute_phi_candidate_measurement(self, candidate_id: str, dataset_id: str, response_projection_id: str) -> Mapping[str, Any]:
        from .knowledge_evolution import KnowledgeEvolutionKernel
        return KnowledgeEvolutionKernel(self.runtime.root).execute_candidate_measurement(
            candidate_id=candidate_id, dataset_id=dataset_id, response_projection_id=response_projection_id,
        )

    def build_phi_world_attestation(self, verification_bundles: Sequence[Mapping[str, Any]], measurements: Sequence[Mapping[str, Any]] = (), qualification_mode: bool = False) -> Mapping[str, Any]:
        from .knowledge_evolution import KnowledgeEvolutionKernel
        kernel = KnowledgeEvolutionKernel(self.runtime.root)
        return kernel.world.attest(verification_bundles=verification_bundles, measurements=measurements, qualification_mode=qualification_mode, persist_path=kernel.state_path)

    def assess_phi_domain_birth(self, *, scan_receipt: Mapping[str, Any], attestation: Mapping[str, Any], domain_id: str, description_ru: str, axes: Sequence[Mapping[str, Any]], evidence_rows: Sequence[Mapping[str, Any]], domain_role: str = "natural_science") -> Mapping[str, Any]:
        from .knowledge_evolution import KnowledgeEvolutionKernel
        return KnowledgeEvolutionKernel(self.runtime.root).domain_ontogenesis.assess_birth(scan_receipt=scan_receipt, attestation=attestation, domain_id=domain_id, description_ru=description_ru, axes=axes, evidence_rows=evidence_rows, domain_role=domain_role, qualification_mode=False)

    def commit_phi_domain_birth(self, receipt: Mapping[str, Any]) -> Mapping[str, Any]:
        from .knowledge_evolution import KnowledgeEvolutionKernel
        if receipt.get("attestation_tier") != "WORLD":
            raise ValueError("production API refuses non-WORLD domain birth")
        kernel = KnowledgeEvolutionKernel(self.runtime.root)
        return kernel.domain_ontogenesis.commit_birth(receipt, manifest_dir=self.runtime.root / "data" / "domains", state_path=kernel.state_path)

    def assess_phi_axis_lifecycle(self, *, domain_id: str, axis_id: str, to_status: str, evidence: Mapping[str, Any], replacement_axis_id: str | None = None) -> Mapping[str, Any]:
        from .knowledge_evolution import KnowledgeEvolutionKernel
        kernel = KnowledgeEvolutionKernel(self.runtime.root)
        return kernel.axis_lifecycle.propose_transition(domain_id=domain_id, axis_id=axis_id, to_status=to_status, evidence=evidence, replacement_axis_id=replacement_axis_id, state_path=kernel.state_path, qualification_mode=False)

    def commit_phi_axis_lifecycle(self, receipt: Mapping[str, Any]) -> Mapping[str, Any]:
        from .knowledge_evolution import KnowledgeEvolutionKernel
        kernel = KnowledgeEvolutionKernel(self.runtime.root)
        return kernel.axis_lifecycle.commit_transition(receipt, state_path=kernel.state_path)

    def resolve_phi_axis_lifecycle(self, axis_id: str) -> Mapping[str, Any]:
        from .knowledge_evolution import KnowledgeEvolutionKernel
        kernel = KnowledgeEvolutionKernel(self.runtime.root)
        return kernel.axis_lifecycle.resolve_axis(axis_id, state_path=kernel.state_path)

    def discover_phi_cross_domain_bridges(self, signatures: Sequence[Mapping[str, Any]], minimum_score: float = 0.92) -> Mapping[str, Any]:
        from .knowledge_evolution import KnowledgeEvolutionKernel
        kernel = KnowledgeEvolutionKernel(self.runtime.root)
        return kernel.bridge.discover(signatures, minimum_score=minimum_score, persist_path=kernel.state_path)

    def assess_phi_domain_split(self, *, parent_domain_id: str, partition_a: Sequence[str], partition_b: Sequence[str], affinity_rows: Sequence[Mapping[str, Any]], attestation: Mapping[str, Any]) -> Mapping[str, Any]:
        from .knowledge_evolution import KnowledgeEvolutionKernel
        return KnowledgeEvolutionKernel(self.runtime.root).domain_ontogenesis.assess_split(parent_domain_id=parent_domain_id, partition_a=partition_a, partition_b=partition_b, affinity_rows=affinity_rows, attestation=attestation, qualification_mode=False)

    def commit_phi_domain_split(self, receipt: Mapping[str, Any], child_domain_ids: Sequence[str] | None = None) -> Mapping[str, Any]:
        from .knowledge_evolution import KnowledgeEvolutionKernel
        if receipt.get("attestation_tier") != "WORLD":
            raise ValueError("production API refuses non-WORLD domain split")
        kernel = KnowledgeEvolutionKernel(self.runtime.root)
        return kernel.domain_ontogenesis.commit_split(receipt, manifest_dir=self.runtime.root / "data" / "domains", state_path=kernel.state_path, child_domain_ids=child_domain_ids)

    def assess_phi_domain_merge(self, *, domain_a: str, domain_b: str, bridge_coverage: float, prediction_rows: Sequence[Mapping[str, Any]], attestation: Mapping[str, Any]) -> Mapping[str, Any]:
        from .knowledge_evolution import KnowledgeEvolutionKernel
        return KnowledgeEvolutionKernel(self.runtime.root).domain_ontogenesis.assess_merge(domain_a=domain_a, domain_b=domain_b, bridge_coverage=bridge_coverage, prediction_rows=prediction_rows, attestation=attestation, qualification_mode=False)

    def commit_phi_domain_merge(self, receipt: Mapping[str, Any], merged_domain_id: str) -> Mapping[str, Any]:
        from .knowledge_evolution import KnowledgeEvolutionKernel
        if receipt.get("attestation_tier") != "WORLD":
            raise ValueError("production API refuses non-WORLD domain merge")
        kernel = KnowledgeEvolutionKernel(self.runtime.root)
        return kernel.domain_ontogenesis.commit_merge(receipt, merged_domain_id=merged_domain_id, manifest_dir=self.runtime.root / "data" / "domains", state_path=kernel.state_path)

    def run_phi_knowledge_evolution_qualification(self) -> Mapping[str, Any]:
        from evaluation.knowledge_evolution_qualification import run_release_qualification
        return run_release_qualification(self.runtime.root)

    def get_phi_mathematical_invention_contract(self) -> Mapping[str, Any]:
        from .mathematical_invention import MathematicalInventionKernel
        return MathematicalInventionKernel(self.runtime.root).contract()

    def discover_phi_unknown_unknown_representation(self, *, question: str, evidence_rows: Sequence[Mapping[str, Any]], seed_owner_ids: Sequence[str] = ("FND-01", "FND-11", "FND-12", "STRUCTURAL-IDENTIFIABILITY-EQUIVALENCE")) -> Mapping[str, Any]:
        from .mathematical_invention import MathematicalInventionKernel
        return MathematicalInventionKernel(self.runtime.root).unknown_unknown.discover(question=question, evidence_rows=evidence_rows, seed_owner_ids=seed_owner_ids)

    def synthesize_phi_primitive(self, *, transition_rows: Sequence[Mapping[str, Any]], freeze_digest: str) -> Mapping[str, Any]:
        from .mathematical_invention import MathematicalInventionKernel
        return MathematicalInventionKernel(self.runtime.root).primitive.synthesize(transition_rows=transition_rows, freeze_digest=freeze_digest)

    def discover_phi_morphism(self, *, source: Mapping[str, Any], target: Mapping[str, Any]) -> Mapping[str, Any]:
        from .mathematical_invention import MathematicalInventionKernel
        return MathematicalInventionKernel(self.runtime.root).morphism.discover(source=source, target=target)

    def assess_phi_controlled_limit(self, *, parameter_rows: Sequence[Mapping[str, Any]], parameter_name: str = "lambda") -> Mapping[str, Any]:
        from .mathematical_invention import MathematicalInventionKernel
        return MathematicalInventionKernel(self.runtime.root).limit.assess(parameter_rows=parameter_rows, parameter_name=parameter_name)

    def run_phi_mathematical_invention_qualification(self) -> Mapping[str, Any]:
        from evaluation.mathematical_invention_qualification import run_release_qualification
        return run_release_qualification(self.runtime.root)

    def get_phi_theory_compiler_contract(self) -> Mapping[str, Any]:
        from .theory_compiler import TheoryCompilerKernel
        return TheoryCompilerKernel(self.runtime.root).contract()

    def synthesize_phi_executable_representation(
        self, *, probe_rows: Sequence[Mapping[str, Any]], freeze_digest: str,
        fit_tolerance_nrmse: float = 1e-5, max_terms_per_output: int | None = None,
    ) -> Mapping[str, Any]:
        from .theory_compiler import TheoryCompilerKernel
        return TheoryCompilerKernel(self.runtime.root).synthesis.synthesize(
            probe_rows=probe_rows, freeze_digest=freeze_digest,
            fit_tolerance_nrmse=fit_tolerance_nrmse, max_terms_per_output=max_terms_per_output,
        )

    def compile_phi_theory(self, *, theory_artifact: Mapping[str, Any], theory_freeze_digest: str, controlled_limit_receipt: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        from .theory_compiler import TheoryCompilerKernel
        return TheoryCompilerKernel(self.runtime.root).compiler.compile(theory_artifact=theory_artifact, theory_freeze_digest=theory_freeze_digest, controlled_limit_receipt=controlled_limit_receipt)

    def execute_phi_compiled_theory(
        self, *, compiled: Mapping[str, Any], initial_state: str | None = None,
        actions: Sequence[str] = (), runtime_request: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        from .theory_compiler import TheoryCompilerKernel
        return TheoryCompilerKernel(self.runtime.root).runtime.execute(
            compiled=compiled, initial_state=initial_state, actions=actions, runtime_request=runtime_request
        )

    def run_phi_theory_compiler_qualification(self) -> Mapping[str, Any]:
        from evaluation.theory_compiler_qualification import run_release_qualification
        return run_release_qualification(self.runtime.root)

    def get_phi_resource_theory_contract(self) -> Mapping[str, Any]:
        from .resource_theory import ResourceTheoryDiscoveryKernel
        return ResourceTheoryDiscoveryKernel(self.runtime.root).contract()

    def discover_phi_resource_theory(
        self, *, question: str, workload_rows: Sequence[Mapping[str, Any]],
        training_workload_ids: Sequence[str], prospective_workload_ids: Sequence[str],
    ) -> Mapping[str, Any]:
        from .resource_theory import ResourceTheoryDiscoveryKernel
        return ResourceTheoryDiscoveryKernel(self.runtime.root).discover_and_validate(
            question=question, workload_rows=workload_rows,
            training_workload_ids=training_workload_ids, prospective_workload_ids=prospective_workload_ids,
        )

    def run_phi_resource_theory_qualification(self) -> Mapping[str, Any]:
        from evaluation.resource_theory_qualification import run_release_qualification
        return run_release_qualification(self.runtime.root)

    def get_phi_discriminating_experiment_contract(self) -> Mapping[str, Any]:
        from .discriminating_experiment import AutomaticDiscriminatingExperimentKernel
        return AutomaticDiscriminatingExperimentKernel(self.runtime.root).contract()

    def design_phi_discriminating_experiment(
        self, *, question: str, candidate_theory: Mapping[str, Any],
        baseline_theories: Sequence[Mapping[str, Any]], cost_budget: float,
    ) -> Mapping[str, Any]:
        from .discriminating_experiment import AutomaticDiscriminatingExperimentKernel
        return AutomaticDiscriminatingExperimentKernel(self.runtime.root).design(
            question=question, candidate_theory=candidate_theory,
            baseline_theories=baseline_theories, cost_budget=cost_budget,
        )

    def run_phi_discriminating_experiment_qualification(self) -> Mapping[str, Any]:
        from evaluation.discriminating_experiment_qualification import run_release_qualification
        return run_release_qualification(self.runtime.root)

    def get_phi_long_horizon_scientific_cycle_contract(self) -> Mapping[str, Any]:
        from .long_horizon_scientific_cycle import LongHorizonBlindScientificCycleKernel
        return LongHorizonBlindScientificCycleKernel(self.runtime.root).contract()

    def freeze_phi_long_horizon_round(self, *, question: str, active_theories: Sequence[Mapping[str, Any]], cost_budget: float) -> Mapping[str, Any]:
        from .long_horizon_scientific_cycle import LongHorizonBlindScientificCycleKernel
        return LongHorizonBlindScientificCycleKernel(self.runtime.root).freeze_round(question=question, active_theories=active_theories, cost_budget=cost_budget)

    def run_phi_long_horizon_scientific_cycle_qualification(self) -> Mapping[str, Any]:
        from evaluation.long_horizon_blind_cycle_qualification import run_release_qualification
        return run_release_qualification(self.runtime.root)


    def get_phi_prospective_external_validation_contract(self) -> Mapping[str, Any]:
        from .prospective_external_validation import ProspectiveExternalScientificValidationKernel
        return ProspectiveExternalScientificValidationKernel(self.runtime.root).contract()

    def run_phi_prospective_external_validation(self, *, freeze_path: str, external_audit_path: str) -> Mapping[str, Any]:
        from .prospective_external_validation import ProspectiveExternalScientificValidationKernel
        return ProspectiveExternalScientificValidationKernel(self.runtime.root).validate_files(
            freeze_path=freeze_path, external_audit_path=external_audit_path
        )

    def run_phi_prospective_external_validation_qualification(self) -> Mapping[str, Any]:
        from evaluation.prospective_external_validation_qualification import run_release_qualification
        return run_release_qualification(self.runtime.root)

    def get_phi_generation_transition_contract(self) -> Mapping[str, Any]:
        from .generation_transition import GenerationTransitionKernel
        return GenerationTransitionKernel(self.runtime.root).contract()

    def search_phi_next_generation_ai(self) -> Mapping[str, Any]:
        from .generation_transition import GenerationTransitionKernel
        return GenerationTransitionKernel(self.runtime.root).search_next_generation()

    def run_phi_generation_transition_qualification(self) -> Mapping[str, Any]:
        from evaluation.generation_transition_qualification import run_release_qualification
        return run_release_qualification(self.runtime.root)

    def get_phi_reflexive_architecture_contract(self) -> Mapping[str, Any]:
        from .reflexive_architecture import ReflexiveSelfHostedPhiArchitectureKernel
        return ReflexiveSelfHostedPhiArchitectureKernel(self.runtime.root).contract()

    def get_phi_architecture_state(self) -> Mapping[str, Any]:
        from .reflexive_architecture import ReflexiveSelfHostedPhiArchitectureKernel
        return ReflexiveSelfHostedPhiArchitectureKernel(self.runtime.root).state.snapshot()

    def run_phi_reflexive_architecture_cycle(self) -> Mapping[str, Any]:
        from .reflexive_architecture import ReflexiveSelfHostedPhiArchitectureKernel
        return ReflexiveSelfHostedPhiArchitectureKernel(self.runtime.root).run_cycle()

    def run_phi_reflexive_architecture_qualification(self) -> Mapping[str, Any]:
        from evaluation.reflexive_architecture_qualification import run_release_qualification
        return run_release_qualification(self.runtime.root)

    def get_phi_runtime_self_repair_contract(self) -> Mapping[str, Any]:
        from .reflexive_architecture import RuntimeExecutionSelfRepairOwner
        return RuntimeExecutionSelfRepairOwner(self.runtime.root).contract()

    def get_phi_runtime_execution_policy(self) -> Mapping[str, Any]:
        from .reflexive_architecture import RuntimeExecutionSelfRepairOwner
        return RuntimeExecutionSelfRepairOwner(self.runtime.root).current_policy()

    def run_phi_runtime_self_repair_cycle(self) -> Mapping[str, Any]:
        from .reflexive_architecture import RuntimeExecutionSelfRepairOwner
        return RuntimeExecutionSelfRepairOwner(self.runtime.root).run_cycle()

    def get_phi_developmental_open_endedness_contract(self) -> Mapping[str, Any]:
        from .developmental_open_endedness import DevelopmentalOpenEndednessKernel
        return DevelopmentalOpenEndednessKernel(self.runtime.root).contract()

    def search_phi_developmental_open_endedness(self) -> Mapping[str, Any]:
        from .developmental_open_endedness import DevelopmentalOpenEndednessKernel
        k = DevelopmentalOpenEndednessKernel(self.runtime.root)
        state = k.state.snapshot()
        return k.search_owner.search(state)

    def run_phi_developmental_open_endedness_cycle(self) -> Mapping[str, Any]:
        from .developmental_open_endedness import DevelopmentalOpenEndednessKernel
        return DevelopmentalOpenEndednessKernel(self.runtime.root).run_cycle()

    def run_phi_developmental_open_endedness_qualification(self) -> Mapping[str, Any]:
        from evaluation.developmental_open_endedness_qualification import run_release_qualification
        return run_release_qualification(self.runtime.root)

    def get_adaptive_research_kernel_contract(self) -> Mapping[str, Any]:
        from .research_cycle import AdaptiveResearchKernelOwner
        return AdaptiveResearchKernelOwner(self.runtime).contract()

    def advance_adaptive_research(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        from .research_cycle import AdaptiveResearchKernelOwner
        return AdaptiveResearchKernelOwner(self.runtime).advance(request)

    def get_claim_provenance_firewall_contract(self) -> Mapping[str, Any]:
        from .research_cycle import ProvenanceClaimFirewallOwner
        return ProvenanceClaimFirewallOwner().contract()

    def run_energy_space_temperature_axis_control(self) -> Mapping[str, Any]:
        from .research_cycle import AdaptiveResearchKernelOwner
        return AdaptiveResearchKernelOwner(self.runtime).energy_space_temperature_axis_control()

    def run_temperature_energy_adaptive_control(self) -> Mapping[str, Any]:
        """Compatibility alias for the current axis-augmentation control."""
        return self.run_energy_space_temperature_axis_control()

    def run_adaptive_research_kernel_qualification(self) -> Mapping[str, Any]:
        from .research_cycle import AdaptiveResearchKernelOwner
        return AdaptiveResearchKernelOwner(self.runtime).run_qualification()

    def get_scientific_research_cycle_contract(self) -> Mapping[str, Any]:
        from .research_cycle import ScientificResearchCycleOwner
        return ScientificResearchCycleOwner(self.runtime).contract()

    def interpret_research_question(self, question: str) -> Mapping[str, Any]:
        from .research_cycle import ScientificResearchCycleOwner
        return ScientificResearchCycleOwner(self.runtime).interpret_question(question)

    def run_autonomous_research(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        from .research_cycle import ScientificResearchCycleOwner
        return ScientificResearchCycleOwner(self.runtime).run_autonomous(request)

    def close_deep_candidate_gamma(self, candidate: Mapping[str, Any]) -> Mapping[str, Any]:
        from .research_cycle import ScientificResearchCycleOwner
        return ScientificResearchCycleOwner(self.runtime).close_deep_candidate_gamma(candidate)

    def run_scientific_research_cycle(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        from .research_cycle import (
            DynamicAxisProposal, ExperimentLikelihoodSpec, LiteratureRecord,
            ScientificResearchCycleOwner,
        )
        payload = dict(request)
        axis_proposals = tuple(DynamicAxisProposal(**row) for row in payload.pop("dynamic_axis_proposals", ()))
        experiment_specs = tuple(ExperimentLikelihoodSpec(**row) for row in payload.pop("experiment_specs", ()))
        literature_records = tuple(LiteratureRecord(**row) for row in payload.pop("literature_records", ()))
        return ScientificResearchCycleOwner(self.runtime).run(
            dynamic_axis_proposals=axis_proposals,
            experiment_specs=experiment_specs,
            literature_records=literature_records,
            **payload,
        )

    def assess_dynamic_axis(self, proposal: Mapping[str, Any]) -> Mapping[str, Any]:
        from .research_cycle import DynamicAxisAdmissionOwner, DynamicAxisProposal
        return DynamicAxisAdmissionOwner().assess(DynamicAxisProposal(**dict(proposal)))

    def assess_post_derivation_novelty(
        self, candidate_id: str, candidate_freeze_digest: str, literature_records: Sequence[Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        from .research_cycle import LiteratureRecord, PostDerivationNoveltyOwner
        candidate = self.get_candidate(candidate_id)
        records = tuple(LiteratureRecord(**dict(row)) for row in literature_records)
        return PostDerivationNoveltyOwner().assess(
            candidate=candidate,
            candidate_freeze_digest=candidate_freeze_digest,
            literature_records=records,
        )

    def rank_experiments_by_information_gain(
        self, candidate_ids: Sequence[str], experiment_specs: Sequence[Mapping[str, Any]], priors: Mapping[str, float] | None = None,
    ) -> Mapping[str, Any]:
        from .research_cycle import DomainNeutralInformationGainOwner, ExperimentLikelihoodSpec
        for candidate_id in candidate_ids:
            self.get_candidate(candidate_id)
        specs = tuple(ExperimentLikelihoodSpec(**dict(row)) for row in experiment_specs)
        return DomainNeutralInformationGainOwner().rank(
            candidate_ids=tuple(candidate_ids), experiment_specs=specs, priors=priors,
        )

    def get_post_gate_experiment_portfolio_contract(self) -> Mapping[str, Any]:
        from .experiment_portfolio import PostGateExperimentPortfolioOwner
        return PostGateExperimentPortfolioOwner().contract()

    def rank_post_gate_experiment_portfolio(
        self, research_cycle_receipt: Mapping[str, Any], information_gain_receipt: Mapping[str, Any],
        resource_metrics: Mapping[str, Mapping[str, Any]] | None = None, scenario: Mapping[str, Any] | None = None,
        maximize_axes: Sequence[str] = ("expected_information_gain_bits",),
        minimize_axes: Sequence[str] = ("scenario_cost",),
    ) -> Mapping[str, Any]:
        from .experiment_portfolio import PostGateExperimentPortfolioOwner
        return PostGateExperimentPortfolioOwner().rank_from_research_cycle(
            research_cycle=research_cycle_receipt, information_gain=information_gain_receipt,
            resource_metrics=resource_metrics, scenario=scenario,
            maximize_axes=maximize_axes, minimize_axes=minimize_axes,
        )

    def post_gate_experiment_quadrants(
        self, portfolio_receipt: Mapping[str, Any], eig_threshold_bits: float | None, cost_threshold: float | None,
    ) -> Mapping[str, Any]:
        from .experiment_portfolio import PostGateExperimentPortfolioOwner
        return PostGateExperimentPortfolioOwner().quadrant_view(
            portfolio_receipt=portfolio_receipt, eig_threshold_bits=eig_threshold_bits, cost_threshold=cost_threshold,
        )

    def request_next_measurement(
        self, owner_ids: Sequence[str], objective: str,
        experiment_specs: Sequence[Mapping[str, Any]] = (),
        priors: Mapping[str, float] | None = None,
    ) -> Mapping[str, Any]:
        # Replacement-in-place of the old placeholder proposal.  The method now
        # computes exact domain-neutral EIG when predictive likelihoods are
        # supplied and otherwise fails closed rather than inventing them.
        from .research_cycle import DomainNeutralInformationGainOwner, ExperimentLikelihoodSpec
        known = [self.runtime.catalog.get_passport(x) for x in owner_ids]
        candidate_ids = [p.owner_id for p in known]
        specs = tuple(ExperimentLikelihoodSpec(**dict(row)) for row in experiment_specs)
        eig = DomainNeutralInformationGainOwner().rank(
            candidate_ids=candidate_ids, experiment_specs=specs, priors=priors,
        )
        return {
            "status": eig["status"],
            "objective": objective,
            "owner_ids": candidate_ids,
            "required_owner": "systems_control",
            "truth_access": False,
            "information_gain": eig,
            "selected_experiment_id": eig.get("selected_experiment_id"),
            "rule": "measurement must distinguish models without reading private truth; no EIG is claimed without explicit predictive likelihoods",
        }
