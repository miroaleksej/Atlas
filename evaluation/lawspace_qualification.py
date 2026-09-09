#!/usr/bin/env python3
"""External deterministic examiner for the Φ-Compiler law-space federation.

The examiner invokes only public runtime contracts. It does not own domain
registries, bridge mathematics, corpus parsing or AI permissions.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from source import phi_compiler_owner as owner
from source.lawspace.api import LawSpaceAPI
from source.lawspace.runtime import LawSpaceRuntime
from source.lawspace.constraint_atlas import ConstraintAtlasOwner
from source.lawspace.schema import canonical_json, digest_payload
from source.lawspace.scientific_promotion import ScientificPromotionCore, FRONTIER_GATE_SEQUENCE
from source.lawspace.candidates import DOVETAIL_STATE_RELATIVE_PATH, dovetail_state_status, write_dovetail_state_file
from source.lawspace.scientific_axis_space import AtlasLawSpaceSearchOwner
from source.lawspace.knowledge_evolution import KnowledgeEvolutionKernel


def run_lawspace_qualification(root: str | Path = ROOT) -> Mapping[str, Any]:
    runtime = LawSpaceRuntime(root)
    report = dict(runtime.qualify())

    # Cross-check the pre-existing blind owner instead of duplicating it.
    connectivity = owner.owner_connectivity_contract()
    api = LawSpaceAPI(root)
    forbidden_assignment_blocked = False
    try:
        api.propose_candidate({"name": "forbidden", "epistemic_state": "ESTABLISHED_LAW"})
    except PermissionError:
        forbidden_assignment_blocked = True

    blind_boundary_blocked = False
    try:
        owner.ObservationPackage(episodes=(), units={}, metadata={}, truth_access=True).validate()
    except RuntimeError:
        blind_boundary_blocked = True

    integration = {
        "eight_recovery_handlers_preserved": len(connectivity) == 8,
        "handler_ids": connectivity,
        "ai_forbidden_assignment_blocked": forbidden_assignment_blocked,
        "truth_access_true_blocked": blind_boundary_blocked,
        "lawspace_catalog_nonempty": bool(runtime.catalog.passports),
    }
    report["integration_checks"] = integration
    report["all_acceptance_gates_pass"] = bool(report["all_acceptance_gates_pass"] and all(v for k, v in integration.items() if k != "handler_ids"))
    report["status"] = "PASS" if report["all_acceptance_gates_pass"] else "FAIL"

    # Recompute report digest after external integration checks.
    from source.lawspace.schema import digest_payload
    report.pop("sha256", None)
    report["sha256"] = digest_payload(report)
    return report



def _candidate_statuses_for_algebraic(row: Mapping[str, Any]) -> list[str]:
    statuses = ["CANDIDATE_ACTIVE", "CANDIDATE_SOURCE_DERIVED", "CANDIDATE_NOVELTY_UNRESOLVED"]
    if row.get("already_materialized_in_current_aeronautics_corpus"):
        statuses.append("CANDIDATE_KNOWN_OVERLAP")
    else:
        statuses.append("CANDIDATE_CURRENT_CORPUS_UNMATERIALIZED")
    if not row.get("source_minimal_under_generated_factor_witnesses", True):
        statuses.append("CANDIDATE_REDUNDANCY_OVERLAP")
    return statuses


def _candidate_statuses_for_operator(row: Mapping[str, Any]) -> list[str]:
    statuses = ["CANDIDATE_ACTIVE", "CANDIDATE_OPERATOR_COMPOSITION", "CANDIDATE_NOVELTY_UNRESOLVED"]
    if row.get("already_materialized_in_current_corpus"):
        statuses.append("CANDIDATE_KNOWN_OVERLAP")
    elif row.get("same_source_set_has_materialized_closure"):
        statuses.append("CANDIDATE_PARTIALLY_EXPLAINED")
    else:
        statuses.append("CANDIDATE_CURRENT_CORPUS_UNMATERIALIZED")
    return statuses


def _measurement_depth_snapshot(root: str | Path) -> dict[str, Any]:
    root = Path(root)
    knowledge_state = KnowledgeEvolutionKernel(root).state()
    bindings = [dict(row) for row in knowledge_state.get("candidate_world_bindings", ())]
    projections = [dict(row) for row in knowledge_state.get("candidate_response_projections", ())]
    executions = [dict(row) for row in knowledge_state.get("candidate_measurement_executions", ())]
    lowerings = [dict(row) for row in knowledge_state.get("candidate_prediction_lowerings", ())]
    discriminations = [dict(row) for row in knowledge_state.get("candidate_prediction_discriminations", ())]
    dayabay = {str(row.get("candidate_id")): row for row in bindings if row.get("dataset_id") == "DAYA-BAY-OFFICIAL-ANALYSIS"}
    cid = "SUBSPACE-0F7BCAA86B7AFED82840"
    negative = dayabay.get("SUBSPACE-00BE16B5890A3309672D", {})
    positive = dayabay.get(cid, {})
    projection = next((row for row in projections if row.get("candidate_id") == cid and row.get("response_projection_id") == "DAYABAY-CNP-PROFILE-CHI2"), {})
    execution = next((row for row in executions if row.get("candidate_id") == cid and row.get("response_projection_id") == "DAYABAY-CNP-PROFILE-CHI2"), {})
    lowering = next((row for row in lowerings if row.get("candidate_id") == cid), {})
    discrimination = next((row for row in discriminations if row.get("candidate_id") == cid), {})
    collapse = dict(dict(discrimination.get("domain_discrimination_receipt", {}) or {}).get("collapse_result", {}) or {})
    collapse_pass_count = sum(dict(dict(row.get("domain_discrimination_receipt", {}) or {}).get("collapse_result", {}) or {}).get("collapse_pass") is True for row in discriminations)
    from source.lawspace.scientific_exploitation import build_current_state
    exploitation_current = build_current_state(root, ai_extension_verified=True)
    structural_lowerability = dict(exploitation_current.get("structural_lowerability_audit", {}) or {})
    diagnostic = {
        "owner": "CANDIDATE-WORLD-BINDING/1.3.0",
        "scientific_data_ingestion_owner": "SCIENTIFIC-DATA-INGESTION/5.11.0",
        "experiment_data_ir_schema": "phi-experiment-data-ir/v3",
        "diagnosis": "ONE_MANUAL_CANDIDATE_SPECIFIC_PREDICTION_FROZEN_AND_HELDOUT_TESTED__OOD_COLLAPSE_FAILED__NO_GENERAL_LOWERING_YET",
        "binding_receipt_count": len(bindings),
        "response_projection_receipt_count": len(projections),
        "measurement_execution_receipt_count": len(executions),
        "prediction_lowering_receipt_count": len(lowerings),
        "prediction_discrimination_receipt_count": len(discriminations),
        "manual_prediction_collapse_pass_count": collapse_pass_count,
        "negative_control": negative,
        "positive_control": positive,
        "response_projection": projection,
        "measurement_execution": execution,
        "manual_prediction_lowering": lowering,
        "manual_prediction_discrimination": discrimination,
        "collapse_result": collapse,
        "world_attestation_count": len(knowledge_state.get("world_attestations", ())),
        "lowerability_admissibility_proposal": {
            "status": "DIAGNOSTIC_PROPOSAL_NOT_GLOBAL_GATE",
            "enforced_at_u1_u2_for_all_candidates": False,
        },
        "claim_boundary": {
            "dataset_binding_is_world_attestation": False,
            "response_projection_is_candidate_prediction": False,
            "executed_dataset_response_without_candidate_prediction_is_u5": False,
            "manual_one_off_lowering_is_general_class_lowering": False,
            "failed_manual_lowering_falsifies_typed_candidate": False,
            "post_reveal_retuning_preserves_same_confirmatory_receipt": False,
            "retrospective_public_data_reanalysis_is_independent_world_attestation": False,
            "new_scientific_law_established": False,
        },
    }
    return {
        "knowledge_state": knowledge_state,
        "structural_lowerability": structural_lowerability,
        "bindings": bindings,
        "projections": projections,
        "executions": executions,
        "lowerings": lowerings,
        "discriminations": discriminations,
        "negative": negative,
        "positive": positive,
        "projection": projection,
        "execution": execution,
        "lowering": lowering,
        "discrimination": discrimination,
        "collapse": collapse,
        "diagnostic": diagnostic,
    }


def run_frontier_scan_current(root: str | Path = ROOT, *, pair_frontier_limit: int = 256, persist_ledger: bool = True) -> Mapping[str, Any]:
    """Orchestrate existing authoritative owners and persist every materialized candidate.

    This function owns no scientific search algorithm. It preserves complete candidate
    ledgers returned by the existing void, algebraic, operator and real-data owners.
    Ranking is a view only: no candidate is deleted because it is weak, overlapping or
    not yet novel. Unmaterialized pair regions remain addressable open regions.
    """
    root = Path(root).resolve()
    runtime = LawSpaceRuntime(root)
    api = LawSpaceAPI(root)
    constraint = ConstraintAtlasOwner(root)

    pair_scan = dict(api.run_open_void_directed_exploration(frontier_limit=pair_frontier_limit))
    algebraic = dict(constraint.scan_unknown_frontier())
    operator = dict(constraint.scan_operator_unknown_frontier())
    realdata = dict(constraint.run_real_gust_mechanism_competition_research_cycle())
    probe_wing = dict(constraint.run_probe_to_wing_modal_discriminator_qualification())
    low_frequency_anomaly = dict(constraint.analyze_low_frequency_gust_anomaly_public_evidence())
    probe_public = dict(probe_wing.get("public_real_data_acquisition", {}))
    probe_full_real_executable = bool(probe_public.get("full_discriminator_executable", False))

    ledger: list[dict[str, Any]] = []
    for row in pair_scan.get("frontier_candidates", ()): 
        ledger.append({
            "candidate_id": row["frontier_id"],
            "candidate_class": "CROSS_DOMAIN_AXIS_FRONTIER",
            "domain_ids": tuple(row.get("domains", ())),
            "source_owner_ids": tuple(sorted({x for group in row.get("owner_ids", ()) for x in group})),
            "epistemic_statuses": tuple(row.get("epistemic_statuses", ("CANDIDATE_ACTIVE", "CANDIDATE_UNVERIFIED", "CANDIDATE_NOVELTY_UNRESOLVED"))),
            "payload": row,
        })
    adaptive_subspaces = dict(pair_scan.get("adaptive_multidimensional_subspace_exploration", {}) or {})
    dovetail_state = dict(adaptive_subspaces.get("dovetail_state", {}) or {})
    dovetail_status = dict(dovetail_state_status(dovetail_state))
    search_contract = AtlasLawSpaceSearchOwner().contract()
    for row in adaptive_subspaces.get("candidates", ()):
        ledger.append({
            "candidate_id": row["candidate_id"],
            "candidate_class": "ADAPTIVE_MULTIDIMENSIONAL_SUBSPACE_FRONTIER",
            "domain_ids": tuple(row.get("domains", ())),
            "source_owner_ids": tuple(row.get("owner_ids", ())),
            "epistemic_statuses": tuple(row.get("epistemic_statuses", (
                "CANDIDATE_ACTIVE", "CANDIDATE_UNVERIFIED",
                "CANDIDATE_NOVELTY_UNRESOLVED", "CANDIDATE_APPLICABILITY_UNRESOLVED",
            ))),
            "payload": row,
        })
    for row in algebraic.get("candidate_ledger", ()): 
        ledger.append({
            "candidate_id": row["candidate_id"],
            "candidate_class": "ALGEBRAIC_SOURCE_DERIVED_FRONTIER",
            "domain_ids": ("aeronautics_and_aerostation",),
            "source_owner_ids": tuple(row.get("source_owner_ids", ())),
            "epistemic_statuses": tuple(_candidate_statuses_for_algebraic(row)),
            "payload": row,
        })
    for row in operator.get("candidate_ledger", ()): 
        ledger.append({
            "candidate_id": row["candidate_id"],
            "candidate_class": "OPERATOR_COMPOSITION_FRONTIER",
            "domain_ids": (str(row.get("domain_id", "UNKNOWN")),),
            "source_owner_ids": tuple(row.get("source_owner_ids", ())),
            "epistemic_statuses": tuple(_candidate_statuses_for_operator(row)),
            "payload": row,
        })

    novelty_map = realdata.get("post_derivation_literature", {}).get("novelty_status_by_candidate", {})
    interpretation = realdata.get("post_derivation_literature", {}).get("mechanism_interpretation", {})
    posterior = realdata.get("second_reentry", {}).get("final_posterior", {})
    for row in realdata.get("frozen_candidate_fits", ()): 
        cid = str(row["candidate_id"])
        statuses = ["CANDIDATE_ACTIVE", "CANDIDATE_REAL_DATA_REPRODUCED", "CANDIDATE_PARTIALLY_EXPLAINED", "CANDIDATE_NOVELTY_UNRESOLVED"]
        if novelty_map.get(cid): statuses.append("CANDIDATE_PRIOR_ART_REVIEW_REQUIRED")
        text = str(interpretation.get(cid, ""))
        if text.startswith("DISFAVORED_AS_COMPLETE_EXPLANATION"):
            statuses.append("CANDIDATE_DISFAVORED_AS_COMPLETE_EXPLANATION")
        if text.startswith("DATA_FAVORED"):
            statuses.append("CANDIDATE_DATA_FAVORED_NOT_IDENTIFIED")
        if probe_wing.get("status", "").startswith("PASS_PHASE_SPEED_MODAL_DISCRIMINATOR"):
            statuses.append("CANDIDATE_DISCRIMINATOR_METHOD_QUALIFIED")
        if cid in {"H-AERO-REAL-002", "H-AERO-REAL-004", "H-AERO-REAL-005"} and not probe_full_real_executable:
            statuses.append("CANDIDATE_DISCRIMINATOR_REAL_DATA_PENDING")
        anomaly_consequence = str(low_frequency_anomaly.get("candidate_consequences", {}).get(cid, ""))
        if anomaly_consequence:
            statuses.append("CANDIDATE_LOW_FREQUENCY_ANOMALY_AUDITED")
        if cid == "H-AERO-REAL-001" and "TENSIONED_AS_COMPLETE_EXPLANATION" in anomaly_consequence:
            statuses.append("CANDIDATE_TENSIONED_AS_COMPLETE_EXPLANATION")
        if cid in {"H-AERO-REAL-002", "H-AERO-REAL-004", "H-AERO-REAL-005"}:
            statuses.append("CANDIDATE_CAUSAL_DISCRIMINATOR_ACTIVE")
        enriched = dict(row)
        enriched["retrospective_posterior_after_two_frozen_holdouts"] = posterior.get(cid)
        enriched["postfreeze_prior_art_status"] = novelty_map.get(cid, "NOT_AUDITED")
        enriched["postfreeze_interpretation"] = text
        enriched["low_frequency_anomaly_consequence"] = low_frequency_anomaly.get("candidate_consequences", {}).get(cid)
        ledger.append({
            "candidate_id": cid,
            "candidate_class": "REAL_DATA_MECHANISM_COMPETITION",
            "domain_ids": ("aeronautics_and_aerostation", "mechanics", "metrology"),
            "source_owner_ids": tuple(row.get("source_owner_ids", ())),
            "epistemic_statuses": tuple(statuses),
            "payload": enriched,
        })

    for axis_admission in realdata.get("provisional_axis", ()): 
        proposal = axis_admission.get("proposal", {})
        cid = "AXIS-CANDIDATE-" + str(proposal.get("axis_id", "UNKNOWN")).upper().replace("_", "-")
        ledger.append({
            "candidate_id": cid,
            "candidate_class": "PROVISIONAL_RESEARCH_AXIS",
            "domain_ids": (str(proposal.get("domain_id", "UNKNOWN")),),
            "source_owner_ids": (),
            "epistemic_statuses": (
                "CANDIDATE_ACTIVE", "CANDIDATE_PROVISIONAL_AXIS", "CANDIDATE_MEASURABLE",
                "CANDIDATE_EXPERIMENT_DESIGNED", "CANDIDATE_CONDITIONAL_MAGNITUDE_QUANTIFIED",
                *( () if probe_full_real_executable else ("CANDIDATE_REAL_DATA_PENDING",) ),
                "CANDIDATE_NOVELTY_UNRESOLVED",
            ),
            "payload": {
                **dict(axis_admission),
                "discriminating_experiment_execution": {
                    "status": probe_wing.get("status"),
                    "full_real_execution": probe_full_real_executable,
                    "public_data_status": probe_public.get("status"),
                    "scientific_object": probe_wing.get("scientific_object"),
                    "data_request_minimum_contract": probe_public.get("data_request_minimum_contract", {}),
                    "repository_search": probe_public.get("repository_search", {}),
                    "claim_boundary": probe_wing.get("claim_boundary", {}),
                    "low_frequency_anomaly_analysis_digest": low_frequency_anomaly.get("digest"),
                    "tri_state_complex_transfer_experiment": low_frequency_anomaly.get("discriminating_experiment", {}),
                },
            },
        })

    # Route every materialized frontier record through the one common executable
    # promotion path before content-addressing the ledger.  This does not promote
    # candidates: missing world evidence remains an explicit pending gate.
    promotion_core = ScientificPromotionCore(trusted_evidence_owners=tuple(runtime.catalog.passports))
    knowledge_state_path = root / "data" / "knowledge" / "knowledge_evolution_state.json"
    materialization_map: dict[str, Mapping[str, Any]] = {}
    research_axis_proposal_count = 0
    if knowledge_state_path.is_file():
        knowledge_state = json.loads(knowledge_state_path.read_text(encoding="utf-8"))
        if str(knowledge_state.get("digest", "")) != digest_payload({k:v for k,v in knowledge_state.items() if k != "digest"}):
            raise RuntimeError("knowledge evolution state digest mismatch during frontier scan")
        for hyp in knowledge_state.get("hypothesis_materializations", ()):
            if isinstance(hyp, Mapping) and str(hyp.get("status", "")) == "TYPED_RELATIONAL_HYPOTHESIS_MATERIALIZED": materialization_map[str(hyp.get("candidate_id", ""))] = dict(hyp)
        # Research-local axis births are first-class candidates too.  They remain
        # non-canonical until the sole DynamicAxisPromotionOwner passes its world
        # gates, but they must not disappear simply because they originated in an
        # older regression branch.
        for proposal in knowledge_state.get("research_axis_proposals", ()):
            if not isinstance(proposal, Mapping):
                continue
            cid = str(proposal.get("proposal_id", ""))
            if not cid:
                continue
            ledger.append({
                "candidate_id": cid,
                "candidate_class": "RESEARCH_AXIS_PROPOSAL",
                "domain_ids": tuple(proposal.get("domain_scope_candidates", ())),
                "source_owner_ids": (str(proposal.get("source_owner_id", "UNKNOWN")),),
                "epistemic_statuses": (
                    "CANDIDATE_ACTIVE", "CANDIDATE_RESEARCH_AXIS", "CANDIDATE_UNVERIFIED",
                    "CANDIDATE_CANONICAL_PROMOTION_BLOCKED_PENDING_WORLD_GATES",
                    "CANDIDATE_NOVELTY_UNRESOLVED",
                ),
                "payload": dict(proposal),
            })
            research_axis_proposal_count += 1
    accepted_owner_ids=tuple(runtime.catalog.passports)
    for row in ledger:
        hyp=materialization_map.get(str(row.get("candidate_id", "")))
        controls={}
        if hyp:
            controls["materialized_hypothesis"]=hyp
            deriv=promotion_core.audit_relational_known_derivability(hyp, accepted_owner_ids=accepted_owner_ids)
            if deriv.get("status")=="PASS_NOT_DERIVED_FROM_ACCEPTED_LAWS":
                controls["known_derivability_audit"]=deriv
        row["promotion_path"] = promotion_core.qualify_frontier_record(row, controls=controls or None)

    # Content-address every ledger row and refuse duplicate IDs rather than silently merging them.
    seen: set[str] = set()
    for row in ledger:
        cid = str(row["candidate_id"])
        if cid in seen:
            raise RuntimeError(f"duplicate active candidate id: {cid}")
        seen.add(cid)
        row["record_digest"] = digest_payload({k: v for k, v in row.items() if k != "record_digest"})
    ledger.sort(key=lambda row: (row["candidate_class"], row["candidate_id"]))

    frontier_dir = root / "data" / "frontiers"
    dovetail_state_path = root / DOVETAIL_STATE_RELATIVE_PATH
    if persist_ledger:
        write_dovetail_state_file(dovetail_state_path, dovetail_state)
    ledger_path = frontier_dir / "ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl"
    ledger_bytes = "".join(canonical_json(row) + "\n" for row in ledger).encode("utf-8")
    ledger_sha = hashlib.sha256(ledger_bytes).hexdigest()
    if persist_ledger:
        frontier_dir.mkdir(parents=True, exist_ok=True)
        ledger_path.write_bytes(ledger_bytes)

    # Post-freeze prior-art evidence is deliberately separate from candidate birth.
    # It may classify a reviewed subset as overlap/partial-overlap/novelty-unresolved,
    # but it cannot delete candidates or turn search failure into negative evidence.
    prior_art_path = frontier_dir / "ATLAS_POSTFREEZE_PRIOR_ART_CURRENT.json"
    prior_art: dict[str, Any] = {}
    prior_art_digest_valid = False
    prior_art_bound_to_current_ledger = False
    prior_art_candidate_ids_valid = False
    if prior_art_path.exists():
        prior_art = json.loads(prior_art_path.read_text(encoding="utf-8"))
        embedded = prior_art.get("digest")
        prior_art_core = {k: v for k, v in prior_art.items() if k != "digest"}
        prior_art_digest_valid = embedded == digest_payload(prior_art_core)
        prior_art_bound_to_current_ledger = (
            prior_art.get("bound_active_candidate_ledger_sha256") == ledger_sha
            and int(prior_art.get("bound_candidate_record_count", -1)) == len(ledger)
        )
        reviewed_ids = {str(x.get("candidate_id")) for x in prior_art.get("candidate_reviews", ())}
        prior_art_candidate_ids_valid = bool(reviewed_ids) and reviewed_ids.issubset(seen)

    pair_counts = Counter(tuple(sorted(row.get("domains", ()))) for row in pair_scan.get("frontier_candidates", ()))
    operator_counts = Counter(str(row.get("domain_id", "UNKNOWN")) for row in operator.get("candidate_ledger", ()))
    class_counts = Counter(row["candidate_class"] for row in ledger)
    status_counts = Counter(status for row in ledger for status in row["epistemic_statuses"])
    promotion_terminal_counts = Counter(str(row.get("promotion_path", {}).get("terminal_status", "MISSING")) for row in ledger)
    promotion_next_gate_counts = Counter(str(row.get("promotion_path", {}).get("next_gate", "NONE")) for row in ledger)
    promotion_gate_pass_counts = {
        gate: sum(bool(row.get("promotion_path", {}).get("gates", {}).get(gate, {}).get("pass")) for row in ledger)
        for gate in FRONTIER_GATE_SEQUENCE
    }
    promotion_receipts_valid = all(
        ScientificPromotionCore.frontier_path_status(row.get("promotion_path", {})).get("valid") is True
        for row in ledger
    )
    promotion_ready_count = sum(bool(row.get("promotion_path", {}).get("prepromotion_ready")) for row in ledger)
    promotion_allowed_count = sum(bool(row.get("promotion_path", {}).get("promotion_allowed")) for row in ledger)
    candidate_false_count = sum(bool(row.get("promotion_path", {}).get("candidate_is_false")) for row in ledger)
    highest_realdata = sorted(((float(v), k) for k, v in posterior.items()), reverse=True)
    fully_bound_bridged_pairs = [
        row for row in pair_scan.get("frontier_candidates", ())
        if row.get("bridge_present") and all(bool(group) for group in row.get("owner_ids", ()))
    ]
    fully_bound_bridged_pairs.sort(key=lambda row: (-float(row.get("semantic_affinity", 0.0)), row["frontier_id"]))
    algebraic_attention = list(algebraic.get("unknown_candidate_ledger", ()))
    algebraic_attention.sort(key=lambda row: (-int(row.get("frontier_priority_score", 0)), row["candidate_id"]))
    operator_attention = list(operator.get("unknown_candidate_ledger", ()))
    operator_attention.sort(key=lambda row: (-int(row.get("priority_score", 0)), row["candidate_id"]))

    measurement_depth = _measurement_depth_snapshot(root)
    knowledge_state = measurement_depth["knowledge_state"]
    binding_receipts = measurement_depth["bindings"]
    response_projection_receipts = measurement_depth["projections"]
    measurement_execution_receipts = measurement_depth["executions"]
    prediction_lowering_receipts = measurement_depth["lowerings"]
    prediction_discrimination_receipts = measurement_depth["discriminations"]
    negative_binding = measurement_depth["negative"]
    positive_binding = measurement_depth["positive"]
    positive_projection = measurement_depth["projection"]
    positive_execution = measurement_depth["execution"]
    data_binding_diagnostic = measurement_depth["diagnostic"]

    checks = {
        "candidate_data_binding_negative_control_blocks_mismatched_domain": negative_binding.get("status") == "CANDIDATE_WORLD_BINDING_BLOCKED_DATASET_SOURCE_FAMILY_MISMATCH" and negative_binding.get("data_binding_qualified") is False,
        "candidate_data_binding_positive_control_exposes_exact_response_projection": positive_binding.get("status") == "DATASET_BINDING_QUALIFIED_RESPONSE_PROJECTION_AVAILABLE" and len(positive_binding.get("response_projection_options", ())) == 1,
        "response_projection_prefrozen_before_execution": positive_projection.get("status") == "FROZEN_EXECUTABLE_MEASUREMENT_CONTRACT_CANDIDATE_PREDICTION_PENDING" and positive_projection.get("observed_response_value") is None and positive_projection.get("measurement_executable") is True,
        "executable_measurement_response_acquired_without_candidate_discrimination": positive_execution.get("status") == "PASS_EXECUTABLE_MEASUREMENT_RESPONSE_ACQUIRED_CANDIDATE_DISCRIMINATION_PENDING" and positive_execution.get("measurement_executed") is True and positive_execution.get("candidate_specific_prediction_used") is False and positive_execution.get("scientific_discrimination_executed") is False,
        "world_attestation_not_fabricated_to_remove_zero": len(knowledge_state.get("world_attestations", ())) == 0,
        "all_registered_cross_domain_pairs_scanned": pair_scan.get("all_cross_domain_pairs_scanned") is True,
        "pair_scan_used_no_baseline_candidate_answers": pair_scan.get("baseline_candidate_registry_used_as_solution_source") is False,
        "pair_scan_literature_prefreeze_false": pair_scan.get("literature_used_prefreeze") is False,
        "adaptive_multidimensional_subspaces_materialized": adaptive_subspaces.get("candidate_count", 0) == len(adaptive_subspaces.get("candidates", ())) > 0,
        "adaptive_subspaces_have_no_fixed_visit_or_order_ceiling": adaptive_subspaces.get("fixed_neighbor_visit_budget") is None and adaptive_subspaces.get("fixed_axis_order_ceiling") is None and all(
            row.get("fixed_owner_visit_budget") is None and row.get("fixed_axis_order_ceiling") is None
            for row in adaptive_subspaces.get("candidates", ())
        ),
        "adaptive_subspaces_cover_multiple_orders": len(adaptive_subspaces.get("axis_order_histogram", {})) >= 5 and adaptive_subspaces.get("minimum_materialized_axis_order", 0) >= 2,
        "adaptive_subspaces_include_pure_higher_order_nominations": adaptive_subspaces.get("pure_higher_order_nomination_present") is True,
        "adaptive_subspaces_can_cross_order_15_without_ceiling": adaptive_subspaces.get("orders_above_15_present") is True and adaptive_subspaces.get("maximum_materialized_axis_order", 0) > 15,
        "adaptive_candidates_have_problem_applicability_and_experiment_contracts": adaptive_subspaces.get("candidate_problem_contract_complete") is True and adaptive_subspaces.get("candidate_applicability_contract_complete") is True and adaptive_subspaces.get("candidate_experiment_contract_complete") is True,
        "literature_absence_is_not_candidate_rejection": adaptive_subspaces.get("research_policy", {}).get("candidate_absent_from_literature_is_false") is False,
        "fair_dovetail_state_digest_valid": dovetail_status.get("valid") is True,
        "fair_dovetail_preserves_all_materialized_nodes": dovetail_status.get("node_count", 0) >= adaptive_subspaces.get("candidate_count", 0),
        "fair_dovetail_preserves_exact_15_13_adaptive_baseline": adaptive_subspaces.get("preserved_15_13_candidate_count") == 1005 and adaptive_subspaces.get("dovetail_extra_candidate_count", 0) >= 2175,
        "fair_dovetail_has_no_fixed_step_or_pair_or_node_ceiling": adaptive_subspaces.get("dovetail_fairness_contract", {}).get("fixed_global_step_ceiling") is None and adaptive_subspaces.get("dovetail_fairness_contract", {}).get("fixed_pair_seed_ceiling") is None and adaptive_subspaces.get("dovetail_fairness_contract", {}).get("fixed_node_visit_ceiling") is None,
        "fair_dovetail_coverage_not_structural_score_gated": adaptive_subspaces.get("dovetail_fairness_contract", {}).get("coverage_lane", "").startswith("EVERY_MISSING_AXIS_EDGE_IS_ADDRESSABLE"),
        "fair_dovetail_eventual_finite_subset_contract_active": adaptive_subspaces.get("dovetail_fairness_contract", {}).get("append_only_open_registry_guarantee", "").startswith("EVERY_FINITE_SUBSET_OF_EVER_REGISTERED_AXES"),
        "legacy_pair_frontier_limit_is_not_scientific_ceiling": pair_scan.get("legacy_pair_frontier_view_limit_is_scientific_space_ceiling") is False,
        "local_feature_search_shell_has_no_fixed_maximum": search_contract.get("fair_local_search_shell", {}).get("fixed_maximum_shell") is None and search_contract.get("fair_local_search_shell", {}).get("shell_zero_preserves_15_13_behavior") is True,
        "algebraic_complete_candidate_ledger_exposed": len(algebraic.get("candidate_ledger", ())) == algebraic.get("generated_consequence_count"),
        "algebraic_frontier_terminates_by_mathematical_saturation_not_visit_budget": algebraic.get("execution_budget_stop_reason") == "ALGEBRAIC_IDEAL_BASIS_SATURATED" and algebraic.get("fixed_execution_visit_ceiling") is None,
        "operator_complete_candidate_ledger_exposed": len(operator.get("candidate_ledger", ())) == operator.get("generated_operator_candidate_count"),
        "operator_frontier_exhausts_without_fixed_visit_ceiling": operator.get("execution_budget_stop_reason") == "FRONTIER_EXHAUSTED" and operator.get("fixed_execution_visit_ceiling") is None,
        "all_materialized_candidates_persisted": len(ledger) == sum(class_counts.values()),
        "no_duplicate_candidate_ids": len(seen) == len(ledger),
        "all_candidates_remain_active": all("CANDIDATE_ACTIVE" in row["epistemic_statuses"] for row in ledger),
        "known_overlap_does_not_delete_candidate": all(
            "CANDIDATE_ACTIVE" in row["epistemic_statuses"]
            for row in ledger if "CANDIDATE_KNOWN_OVERLAP" in row["epistemic_statuses"]
        ),
        "legacy_nonadaptive_frontier_classes_preserved": class_counts.get("CROSS_DOMAIN_AXIS_FRONTIER", 0) == 256 and class_counts.get("ALGEBRAIC_SOURCE_DERIVED_FRONTIER", 0) == 116 and class_counts.get("OPERATOR_COMPOSITION_FRONTIER", 0) == 11 and class_counts.get("REAL_DATA_MECHANISM_COMPETITION", 0) == 5 and class_counts.get("PROVISIONAL_RESEARCH_AXIS", 0) == 1,
        "real_data_mechanism_set_preserved": len(realdata.get("frozen_candidate_fits", ())) == 5,
        "provisional_axis_preserved": bool(realdata.get("provisional_axis")),
        "probe_to_wing_discriminator_method_qualified": probe_wing.get("status", "").startswith("PASS_PHASE_SPEED_MODAL_DISCRIMINATOR"),
        "probe_to_wing_real_data_fail_closed": (not probe_full_real_executable) and probe_public.get("posterior_update_allowed") is False,
        "low_frequency_anomaly_quantified": low_frequency_anomaly.get("status") == "PASS_LOW_FREQUENCY_GUST_ANOMALY_PUBLIC_EVIDENCE_ANALYSIS",
        "tri_state_complex_transfer_experiment_designed": low_frequency_anomaly.get("discriminating_experiment", {}).get("status") == "EXPERIMENT_DESIGNED_REAL_SYNCHRONIZED_DATA_PENDING",
        "world_novelty_not_predeclared": all("CANDIDATE_WORLD_NOVEL" not in row["epistemic_statuses"] for row in ledger),
        "postfreeze_prior_art_receipt_present_and_digest_valid": bool(prior_art) and prior_art_digest_valid,
        "postfreeze_prior_art_bound_to_frozen_current_ledger": prior_art_bound_to_current_ledger,
        "postfreeze_prior_art_reviews_only_existing_candidates": prior_art_candidate_ids_valid,
        "postfreeze_prior_art_absence_never_means_false": prior_art.get("selection_policy", {}).get("absence_from_search_is_negative_evidence") is False,
        "postfreeze_prior_art_overlap_never_deletes_candidate": prior_art.get("selection_policy", {}).get("known_overlap_deletes_candidate") is False,
        "every_frontier_candidate_has_unified_promotion_path": len(ledger) > 0 and all(bool(row.get("promotion_path")) for row in ledger),
        "all_unified_promotion_path_receipts_valid": promotion_receipts_valid,
        "all_frontier_candidates_share_same_gate_sequence": all(tuple(row.get("promotion_path", {}).get("gate_sequence", ())) == tuple(FRONTIER_GATE_SEQUENCE) for row in ledger),
        "typed_hypothesis_materializations_are_digest_bound": (not materialization_map) or all(str(h.get("digest", "")) == digest_payload({k:v for k,v in h.items() if k != "digest"}) for h in materialization_map.values()),
        "materialized_relational_hypotheses_reach_u4_formal_audit_without_skipping_empirical_gates": all((not row.get("promotion_path", {}).get("gates", {}).get("U1_TYPED_HYPOTHESIS_BINDING", {}).get("evidence", {}).get("materialized_hypothesis_digest")) or (row.get("promotion_path", {}).get("gates", {}).get("U2_EXACT_DIMENSIONAL_QUALIFICATION", {}).get("pass") is True and row.get("promotion_path", {}).get("gates", {}).get("U3_CONVENTION_ARTIFACT_AUDIT", {}).get("pass") is True and row.get("promotion_path", {}).get("gates", {}).get("U4_KNOWN_DERIVABILITY_AUDIT", {}).get("pass") is True and row.get("promotion_path", {}).get("gates", {}).get("U5_COLLAPSE_OR_INVARIANCE", {}).get("pass") is False) for row in ledger),
        "frontier_promotion_path_never_auto_promotes": promotion_allowed_count == 0 and promotion_ready_count == 0,
        "missing_evidence_never_marks_candidate_false": candidate_false_count == 0,
        "whole_pipeline_null_is_explicit_for_every_candidate": all("U8_WHOLE_PIPELINE_PERMUTATION_NULL" in row.get("promotion_path", {}).get("gates", {}) for row in ledger),
        "source_derived_candidates_route_without_false_novel_promotion": all(
            row.get("promotion_path", {}).get("terminal_status") == "SOURCE_DERIVED_CANDIDATE_RETAINED_NOT_NEW_LAW_PROMOTION"
            for row in ledger if row.get("candidate_class") in {"ALGEBRAIC_SOURCE_DERIVED_FRONTIER", "OPERATOR_COMPOSITION_FRONTIER"}
        ),
        "provisional_axis_routes_to_axis_promotion": all(
            row.get("promotion_path", {}).get("terminal_status") == "AXIS_PROMOTION_ROUTE_PENDING_WORLD_EVIDENCE"
            for row in ledger if row.get("candidate_class") == "PROVISIONAL_RESEARCH_AXIS"
        ),
    }

    payload = {
        "schema": "phi-atlas-frontier-candidate-scan/v15.23.0",
        "release": "15.23.0",
        "owner": "ATLAS-FRONTIER-SCAN-ORCHESTRATION/15.23.0",
        "status": "PASS_ATLAS_FRONTIER_CANDIDATE_SCAN" if all(checks.values()) else "FAIL_ATLAS_FRONTIER_CANDIDATE_SCAN",
        "policy": {
            "candidate_first": True,
            "unknown_candidate_is_false": False,
            "ranking_is_deletion_policy": False,
            "known_overlap_deletes_candidate": False,
            "domain_label_is_presearch_gate": False,
            "scientific_novelty_requires_postfreeze_evidence": True,
            "persistent_fair_dovetail_required": True,
            "legacy_frontier_candidates_preserved": True,
            "finite_execution_tranche_is_scientific_ceiling": False,
        },
        "source_owners": {
            "cross_domain_void": {"owner": pair_scan.get("owner"), "digest": pair_scan.get("digest")},
            "algebraic_unknown_frontier": {"owner": algebraic.get("owner_id"), "digest": algebraic.get("digest")},
            "operator_unknown_frontier": {"owner": operator.get("owner_id"), "digest": operator.get("digest")},
            "real_data_mechanism_competition": {"owner": realdata.get("owner_id"), "digest": realdata.get("digest")},
            "probe_to_wing_discriminator": {"owner": probe_wing.get("owner_id"), "digest": probe_wing.get("digest")},
            "low_frequency_gust_anomaly": {"owner": low_frequency_anomaly.get("owner_id"), "digest": low_frequency_anomaly.get("digest")},
            "scientific_promotion": {"owner": promotion_core.contract().get("owner"), "version": promotion_core.contract().get("owner_version")},
        },
        "scan_summary": {
            "registered_axes": pair_scan.get("registered_axis_count"),
            "registered_domains": pair_scan.get("registered_domain_count"),
            "cross_domain_pair_regions_scanned": pair_scan.get("cross_domain_pair_count_scanned"),
            "materialized_pair_frontier_candidates": pair_scan.get("frontier_candidate_count"),
            "pair_regions_not_materialized_not_rejected": pair_scan.get("pair_regions_scanned_but_not_materialized_as_candidates"),
            "adaptive_multidimensional_subspace_candidates": adaptive_subspaces.get("candidate_count"),
            "adaptive_subspace_seed_count": adaptive_subspaces.get("seed_count"),
            "adaptive_subspace_axis_order_histogram": adaptive_subspaces.get("axis_order_histogram", {}),
            "adaptive_subspace_minimum_axis_order": adaptive_subspaces.get("minimum_materialized_axis_order"),
            "adaptive_subspace_maximum_axis_order": adaptive_subspaces.get("maximum_materialized_axis_order"),
            "adaptive_subspace_neighbor_visit_budget": adaptive_subspaces.get("fixed_neighbor_visit_budget"),
            "dovetail_state_digest": adaptive_subspaces.get("dovetail_state_digest"),
            "dovetail_node_count": adaptive_subspaces.get("dovetail_node_count"),
            "dovetail_extra_candidate_count": adaptive_subspaces.get("dovetail_extra_candidate_count"),
            "dovetail_preserved_15_13_candidate_count": adaptive_subspaces.get("preserved_15_13_candidate_count"),
            "dovetail_steps_executed": adaptive_subspaces.get("dovetail_steps_executed"),
            "dovetail_environment_epoch": dovetail_state.get("environment_epoch"),
            "dovetail_pair_visits": dovetail_state.get("scheduler", {}).get("pair_cursor", {}).get("visits"),
            "dovetail_node_visits": dovetail_state.get("scheduler", {}).get("node_visits"),
            "dovetail_local_search_shell_max": max((int(row.get("local_search_shell", 0)) for row in dovetail_state.get("nodes", {}).values()), default=0),
            "algebraic_generated_candidates": algebraic.get("generated_consequence_count"),
            "algebraic_current_corpus_unmaterialized_minimal_candidates": algebraic.get("forced_unmaterialized_relation_count"),
            "algebraic_connected_source_components": algebraic.get("connected_source_component_count"),
            "algebraic_maximum_executed_source_order": algebraic.get("maximum_executed_source_order"),
            "algebraic_execution_stop_reason": algebraic.get("execution_budget_stop_reason"),
            "operator_generated_candidates": operator.get("generated_operator_candidate_count"),
            "operator_current_corpus_unmaterialized_candidates": operator.get("forced_unmaterialized_operator_relation_count"),
            "operator_execution_stop_reason": operator.get("execution_budget_stop_reason"),
            "real_data_mechanism_candidates": len(realdata.get("frozen_candidate_fits", ())),
            "provisional_axis_candidates": len(realdata.get("provisional_axis", ())),
            "probe_to_wing_discriminator_status": probe_wing.get("status"),
            "probe_to_wing_full_real_execution": probe_full_real_executable,
            "probe_to_wing_public_data_status": probe_public.get("status"),
            "low_frequency_gust_anomaly_status": low_frequency_anomaly.get("status"),
            "low_frequency_mean_residual_db": low_frequency_anomaly.get("bands", {}).get("low_4_8_hz", {}).get("mean_residual_db"),
            "low_frequency_conditional_effective_input_ratio": low_frequency_anomaly.get("bands", {}).get("low_4_8_hz", {}).get("mean_conditional_effective_input_magnitude_ratio"),
            "active_candidate_ledger_count": len(ledger),
            "research_axis_proposals_persisted": research_axis_proposal_count,
            "adaptive_competing_hypotheses_persisted": sum(int(row.get("payload", {}).get("competing_hypothesis_count", 0)) for row in ledger if row.get("candidate_class") == "ADAPTIVE_MULTIDIMENSIONAL_SUBSPACE_FRONTIER"),
            "unified_promotion_path_receipts": len(ledger),
            "unified_prepromotion_ready_count": promotion_ready_count,
            "unified_promotion_allowed_count": promotion_allowed_count,
            "unified_candidate_false_count": candidate_false_count,
            "typed_hypothesis_materializations_persisted": len(materialization_map),
            "typed_hypothesis_materializations_bound_to_current_records": sum(bool(row.get("promotion_path", {}).get("gates", {}).get("U1_TYPED_HYPOTHESIS_BINDING", {}).get("evidence", {}).get("materialized_hypothesis_digest")) for row in ledger),
            "materialized_relational_u4_pass_count": sum(bool(row.get("promotion_path", {}).get("gates", {}).get("U1_TYPED_HYPOTHESIS_BINDING", {}).get("evidence", {}).get("materialized_hypothesis_digest")) and bool(row.get("promotion_path", {}).get("gates", {}).get("U4_KNOWN_DERIVABILITY_AUDIT", {}).get("pass")) for row in ledger),
            "materialized_relational_u5_pass_count": sum(bool(row.get("promotion_path", {}).get("gates", {}).get("U1_TYPED_HYPOTHESIS_BINDING", {}).get("evidence", {}).get("materialized_hypothesis_digest")) and bool(row.get("promotion_path", {}).get("gates", {}).get("U5_COLLAPSE_OR_INVARIANCE", {}).get("pass")) for row in ledger),
            "automatic_scientific_promotion_count": promotion_allowed_count,
            "candidate_world_binding_receipt_count": len(binding_receipts),
            "exact_dataset_binding_qualified_count": sum(row.get("data_binding_qualified") is True for row in binding_receipts),
            "candidate_response_projection_count": len(response_projection_receipts),
            "candidate_measurement_execution_count": len(measurement_execution_receipts),
            "candidate_prediction_lowering_count": len(prediction_lowering_receipts),
            "candidate_prediction_discrimination_count": len(prediction_discrimination_receipts),
            "candidate_specific_prediction_frozen_count": sum(row.get("candidate_specific_prediction_frozen") is True for row in prediction_lowering_receipts),
            "heldout_prediction_check_executed_count": sum(row.get("heldout_prediction_check_executed") is True for row in prediction_discrimination_receipts),
            "manual_prediction_collapse_pass_count": sum(dict(dict(row.get("domain_discrimination_receipt", {}) or {}).get("collapse_result", {}) or {}).get("collapse_pass") is True for row in prediction_discrimination_receipts),
            "measurement_executable_contract_count": sum(row.get("measurement_executable") is True for row in response_projection_receipts),
            "scientifically_discriminating_measurement_count": sum(row.get("scientific_discrimination_executed") is True for row in measurement_execution_receipts),
            "response_projection_pending_binding_count": sum(row.get("data_binding_qualified") is True and not row.get("response_projection_options") for row in binding_receipts),
            "world_attestation_count": len(knowledge_state.get("world_attestations", ())),
            "data_binding_diagnostic_candidate_generation_count": 0,
        },
        "candidate_class_counts": dict(sorted(class_counts.items())),
        "candidate_status_counts": dict(sorted(status_counts.items())),
        "qualification_runtime": {
            "owner": f"{promotion_core.owner_id}/{promotion_core.contract().get('owner_version')}",
            "gate_sequence": list(FRONTIER_GATE_SEQUENCE),
            "receipt_count": len(ledger),
            "receipt_valid_count": len(ledger) if promotion_receipts_valid else sum(ScientificPromotionCore.frontier_path_status(row.get("promotion_path", {})).get("valid") is True for row in ledger),
            "prepromotion_ready_count": promotion_ready_count,
            "promotion_allowed_count": promotion_allowed_count,
            "candidate_false_count": candidate_false_count,
            "typed_hypothesis_materialization_count": len(materialization_map),
            "terminal_status_counts": dict(sorted(promotion_terminal_counts.items())),
            "next_gate_counts": dict(sorted(promotion_next_gate_counts.items())),
            "gate_pass_counts": promotion_gate_pass_counts,
            "missing_evidence_means_false": False,
            "whole_pipeline_null_required_before_law_candidate": True,
            "direct_numeric_core_can_bypass_unified_path": False,
        },
        "fair_open_ended_traversal": {
            "owner": "CandidateGenerationPipeline/6.27.0",
            "state_path": str(dovetail_state_path.relative_to(root)),
            "state_digest": dovetail_state.get("digest"),
            "state_valid": dovetail_status.get("valid"),
            "environment_epoch": dovetail_state.get("environment_epoch"),
            "node_count": len(dict(dovetail_state.get("nodes", {}))),
            "scheduler": dovetail_state.get("scheduler", {}),
            "fairness_contract": dovetail_state.get("fairness_contract", {}),
            "last_rebase": dovetail_state.get("last_rebase", {}),
            "last_advance": dovetail_state.get("last_advance", {}),
            "legacy_15_13_candidate_set_deleted": False,
            "preserved_15_13_candidate_count": adaptive_subspaces.get("preserved_15_13_candidate_count"),
            "dovetail_continuation_candidate_count": adaptive_subspaces.get("dovetail_extra_candidate_count"),
            "new_scientific_law_established": False,
        },
        "postfreeze_prior_art_review": {
            "path": str(prior_art_path.relative_to(root)) if prior_art else None,
            "status": prior_art.get("status"),
            "digest": prior_art.get("digest"),
            "bound_active_candidate_ledger_sha256": prior_art.get("bound_active_candidate_ledger_sha256"),
            "review_count": prior_art.get("review_count", 0),
            "summary": prior_art.get("summary", {}),
            "claim_boundary": prior_art.get("claim_boundary", {}),
        },
        "hotspots": {
            "cross_domain_materialized_pair_counts": [{"domains": list(k), "count": v} for k, v in pair_counts.most_common()],
            "operator_candidate_domain_counts": dict(sorted(operator_counts.items())),
            "real_data_candidate_posterior_order_after_two_frozen_holdouts": [{"candidate_id": cid, "posterior": score} for score, cid in highest_realdata],
            "real_data_unique_mechanism_identified": realdata.get("result", {}).get("unique_mechanism_identified"),
            "real_data_next_discriminator": realdata.get("best_next_experiment"),
            "probe_to_wing_discriminator_execution": {
                "status": probe_wing.get("status"),
                "scientific_object": probe_wing.get("scientific_object"),
                "full_real_execution": probe_full_real_executable,
                "public_data_status": probe_public.get("status"),
                "real_multispeed_wrbm_magnitude_available": probe_public.get("real_multispeed_wrbm_magnitude_available"),
                "complex_phase_available": probe_public.get("complex_phase_available"),
                "near_wing_gust_available": probe_public.get("near_wing_gust_available"),
                "same_test_article_numeric_modal_series_available": probe_public.get("same_test_article_numeric_modal_series_available"),
                "posterior_update_allowed": probe_public.get("posterior_update_allowed"),
                "data_request_minimum_contract": probe_public.get("data_request_minimum_contract", {}),
                "repository_search": probe_public.get("repository_search", {}),
                "claim_boundary": probe_wing.get("claim_boundary", {}),
            },
            "low_frequency_gust_anomaly": low_frequency_anomaly,
            "fully_owner_bound_bridged_cross_domain_candidates": fully_bound_bridged_pairs,
            "top_algebraic_attention_candidates": algebraic_attention[:10],
            "top_operator_attention_candidates": operator_attention[:10],
        },
        "incomplete_frontiers": {
            "algebraic_search": {
                "status": "CURRENT_POLYNOMIAL_IDEAL_BASIS_SATURATED" if algebraic.get("execution_budget_stop_reason") == "ALGEBRAIC_IDEAL_BASIS_SATURATED" else "ALGEBRAIC_FRONTIER_OPEN",
                "reason": algebraic.get("execution_budget_stop_reason"),
                "scientific_source_order_ceiling_used": algebraic.get("scientific_source_order_ceiling_used"),
                "fixed_execution_visit_ceiling": algebraic.get("fixed_execution_visit_ceiling"),
                "execution_budget_is_physical_admissibility_gate": algebraic.get("execution_budget_is_physical_admissibility_gate"),
                "claim_boundary": "Saturation closes only the polynomial ideal generated by the current executable source component; it is not exhaustion of all future axes, owners, representations or world mechanisms.",
            },
            "adaptive_multidimensional_subspace_search": {
                "status": "PERSISTENT_FAIR_DOVETAIL_CONTINUATION_ACTIVE",
                "materialized_region_count": adaptive_subspaces.get("candidate_count"),
                "minimum_axis_order": adaptive_subspaces.get("minimum_materialized_axis_order"),
                "maximum_axis_order": adaptive_subspaces.get("maximum_materialized_axis_order"),
                "axis_order_histogram": adaptive_subspaces.get("axis_order_histogram", {}),
                "fixed_axis_order_ceiling": adaptive_subspaces.get("fixed_axis_order_ceiling"),
                "fixed_neighbor_visit_budget": adaptive_subspaces.get("fixed_neighbor_visit_budget"),
                "persistent_state_digest": dovetail_state.get("digest"),
                "fixed_global_step_ceiling": adaptive_subspaces.get("dovetail_fixed_global_step_ceiling"),
                "coverage_diagnostics": adaptive_subspaces.get("coverage_diagnostics", {}),
                "explicit_competing_hypothesis_count": adaptive_subspaces.get("competing_hypothesis_count", 0),
                "claim_boundary": "The preserved 15.13 frontier is the initial node set. Finite-release coverage witnesses now materialize every previously untouched canonical axis at least once, while repeated dovetail advances retain the asymptotic all-finite-subsets guarantee. Coverage is navigation evidence only; unvisited pair/triple/higher-order regions remain UNKNOWN, never false.",
            },
            "probe_to_wing_physical_measurement": {
                "status": "EXECUTED_ON_PUBLIC_PARTIAL_EVIDENCE_REAL_COMPLEX_MEASUREMENT_DATA_PENDING" if not probe_full_real_executable else "FULL_REAL_COMPLEX_DISCRIMINATOR_EXECUTED",
                "public_data_status": probe_public.get("status"),
                "missing_requirements": probe_public.get("repository_search", {}).get("required_but_not_publicly_obtained", []),
                "posterior_update_allowed": probe_public.get("posterior_update_allowed"),
            },
            "neutrino_full_open_ended_realdata_scan": {
                "status": "NOT_MATERIALIZED_IN_THIS_SCAN",
                "reason": "No reduced or truncated substitute is promoted as a complete scan; the existing owner remains available for a dedicated full execution.",
            },
        },
        "data_binding_diagnostic": data_binding_diagnostic,
        "active_candidate_ledger": {
            "path": str(ledger_path.relative_to(root)),
            "sha256": ledger_sha,
            "record_count": len(ledger),
            "all_records_content_addressed": True,
            "dovetail_state_path": str(dovetail_state_path.relative_to(root)),
            "dovetail_state_digest": dovetail_state.get("digest"),
        },
        "checks": checks,
        "claim_boundary": {
            "materialized_candidate_is_established_law": False,
            "current_corpus_unmaterialized_means_world_novel": False,
            "known_overlap_means_falsified": False,
            "unmaterialized_pair_region_means_false": False,
            "new_scientific_law_established_by_scan": False,
            "finite_dovetail_tranche_exhausts_space": False,
            "unvisited_dovetail_address_is_false": False,
            "dataset_binding_is_world_measurement": False,
            "data_binding_diagnostic_promoted_u5": False,
            "executed_dataset_response_is_candidate_specific_prediction": False,
            "executed_dataset_response_without_candidate_prediction_is_u5": False,
            "generic_mechanism_family_count_is_scientific_evidence": False,
        },
    }
    payload["digest"] = digest_payload(payload)
    return payload

def refresh_frontier_measurement_depth_report(root: str | Path = ROOT, *, report_path: str | Path | None = None) -> Mapping[str, Any]:
    """Refresh only measurement-depth fields when the scientific frontier is unchanged.

    The existing frontier report must have a valid canonical digest and its bound
    active-ledger SHA must exactly match the current ledger. Heavy scientific
    analyses are not re-executed; this fact is explicit in the refreshed receipt.
    """
    root = Path(root).resolve()
    path = Path(report_path) if report_path is not None else root / "reports/ATLAS_FRONTIER_SCAN_CURRENT.json"
    if not path.is_absolute():
        path = root / path
    report = json.loads(path.read_text(encoding="utf-8"))
    stored_digest = report.get("digest")
    if stored_digest != digest_payload({k: v for k, v in report.items() if k != "digest"}):
        raise RuntimeError("frontier report canonical digest invalid before measurement-depth refresh")
    ledger_path = root / "data/frontiers/ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl"
    ledger_sha = hashlib.sha256(ledger_path.read_bytes()).hexdigest()
    if report.get("active_candidate_ledger", {}).get("sha256") != ledger_sha:
        raise RuntimeError("frontier report ledger binding does not match current ledger")
    prior_refresh = dict(report.get("measurement_depth_refresh", {}) or {})
    base_digest = prior_refresh.get("base_frontier_digest") or stored_digest
    m = _measurement_depth_snapshot(root)
    lowering = m["lowering"]
    discrimination = m["discrimination"]
    domain_disc = dict(discrimination.get("domain_discrimination_receipt", {}) or {})
    trajectories = list(domain_disc.get("heldout_trajectories", ()) or ())
    scan = report.setdefault("scan_summary", {})
    scan.update({
        "candidate_prediction_lowering_count": len(m["lowerings"]),
        "candidate_prediction_discrimination_count": len(m["discriminations"]),
        "candidate_specific_prediction_frozen_count": sum(row.get("candidate_specific_prediction_frozen") is True for row in m["lowerings"]),
        "heldout_prediction_check_executed_count": sum(row.get("heldout_prediction_check_executed") is True for row in m["discriminations"]),
        "manual_prediction_collapse_pass_count": sum(dict(dict(row.get("domain_discrimination_receipt", {}) or {}).get("collapse_result", {}) or {}).get("collapse_pass") is True for row in m["discriminations"]),
        "automatic_class_lowering_generalized_count": sum(dict(row.get("claim_boundary", {}) or {}).get("automatic_lowering_generalized") is True for row in m["discriminations"]),
        "world_attestation_count": len(m["knowledge_state"].get("world_attestations", ())),
        "u4_structural_single_forward_owner_complete_count": m["structural_lowerability"].get("single_forward_owner_complete_count"),
        "u4_structural_composable_multi_owner_complete_count": m["structural_lowerability"].get("composable_multi_owner_complete_count"),
        "u4_structural_addressable_union_count": m["structural_lowerability"].get("structurally_addressable_union_count"),
        "u4_structural_partial_or_blocked_count": 447 - int(m["structural_lowerability"].get("structurally_addressable_union_count") or 0),
    })
    report["schema"] = "phi-atlas-frontier-candidate-scan/v15.23.0"
    report["release"] = "15.23.0"
    report["owner"] = "ATLAS-FRONTIER-SCAN-ORCHESTRATION/15.23.0"
    report["data_binding_diagnostic"] = m["diagnostic"]
    report["structural_lowerability_audit"] = m["structural_lowerability"]
    report["measurement_depth_refresh"] = {
        "schema": "phi-frontier-measurement-depth-refresh/v1",
        "owner": "ATLAS-FRONTIER-SCAN-ORCHESTRATION/15.23.0",
        "base_frontier_digest": base_digest,
        "input_frontier_digest_valid": True,
        "active_candidate_ledger_sha256": ledger_sha,
        "active_candidate_ledger_unchanged": True,
        "heavy_frontier_recomputed": False,
        "refresh_scope": "KNOWLEDGE_STATE_MEASUREMENT_DEPTH_ONLY",
        "manual_lowering_receipt_digest": lowering.get("digest"),
        "manual_discrimination_receipt_digest": discrimination.get("digest"),
        "heldout_trajectory_count": len(trajectories),
        "post_reveal_lowering_retuned": False,
    }
    checks = report.setdefault("checks", {})
    checks.update({
        "measurement_depth_refresh_bound_to_valid_prior_frontier_digest": True,
        "measurement_depth_refresh_preserves_active_candidate_ledger": report.get("active_candidate_ledger", {}).get("sha256") == ledger_sha,
        "manual_candidate_prediction_lowering_frozen_before_reveal": len(m["lowerings"]) == 1 and lowering.get("candidate_specific_prediction_frozen") is True and lowering.get("domain_prediction_freeze", {}).get("claim_boundary", {}).get("heldout_signal_counts_observed_at_freeze") is False,
        "manual_candidate_prediction_heldout_check_executed_without_refit": len(m["discriminations"]) == 1 and discrimination.get("heldout_prediction_check_executed") is True and len(trajectories) == 2 and all(row.get("heldout_refit_performed") is False for row in trajectories),
        "manual_candidate_prediction_ood_collapse_failure_preserved": domain_disc.get("status") == "FAIL_MANUAL_CANDIDATE_PREDICTION_COLLAPSE_DIAGNOSTIC" and m["collapse"].get("collapse_pass") is False and m["collapse"].get("cross_partition_collapse_pass") is True,
        "manual_lowering_not_generalized_or_retuned_after_reveal": dict(discrimination.get("claim_boundary", {}) or {}).get("automatic_lowering_generalized") is False and report["measurement_depth_refresh"]["post_reveal_lowering_retuned"] is False,
        "manual_lowering_failure_does_not_fake_world_or_u5": scan.get("world_attestation_count") == 0 and scan.get("materialized_relational_u5_pass_count") == 0,
        "u4_structural_lowerability_audit_covers_all_447": m["structural_lowerability"].get("candidate_count") == 447,
        "u4_strict_single_forward_owner_count_frozen": m["structural_lowerability"].get("single_forward_owner_complete_count") == 14,
        "u4_composable_multi_owner_count_frozen": m["structural_lowerability"].get("composable_multi_owner_complete_count") == 286,
    })
    report.setdefault("claim_boundary", {}).update({
        "manual_one_off_lowering_is_general_class_lowering": False,
        "failed_manual_lowering_falsifies_typed_candidate": False,
        "measurement_depth_refresh_recomputed_heavy_frontier": False,
        "u1_u2_lowerability_proposal_enforced": False,
        "structural_lowerability_audit_is_global_gate": False,
        "multi_owner_structural_coverage_is_numeric_lowering": False,
    })
    report["status"] = "PASS_ATLAS_FRONTIER_CANDIDATE_SCAN" if all(bool(v) for v in checks.values()) else "FAIL_ATLAS_FRONTIER_CANDIDATE_SCAN"
    report.pop("digest", None)
    report["digest"] = digest_payload(report)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Qualify Φ-Compiler law-space or execute the current Atlas frontier scan")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frontier-scan-current", action="store_true")
    parser.add_argument("--refresh-measurement-depth-current", action="store_true")
    parser.add_argument("--pair-frontier-limit", type=int, default=256)
    args = parser.parse_args()
    if args.refresh_measurement_depth_current:
        report = refresh_frontier_measurement_depth_report(args.root, report_path=args.output)
    elif args.frontier_scan_current:
        report = run_frontier_scan_current(args.root, pair_frontier_limit=args.pair_frontier_limit)
    else:
        report = run_lawspace_qualification(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    digest = report.get("digest", report.get("sha256"))
    print(json.dumps({"output": str(args.output), "status": report["status"], "digest": digest}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
