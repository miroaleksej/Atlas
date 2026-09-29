"""Qualification for Φ-Mathematical Invention Kernel current release."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from source.lawspace.schema import digest_payload
from source.lawspace.mathematical_invention import MathematicalInventionKernel
from source.lawspace.domains import canonical_axis_count

SCHEMA="phi-mathematical-invention-qualification/v1"; RELEASE="15.10.3"


def _history_rows():
    # Hidden generator uses three states, each duplicated into two opaque histories.
    # The solver receives only opaque history ids, observations and transitions.
    obs={"a0":"0","a1":"0","b0":"0","b1":"0","c0":"1","c1":"1"}
    trans={
      "a0":{"x":"a0","y":"c0"},"a1":{"x":"a1","y":"c1"},
      "b0":{"x":"c0","y":"b0"},"b1":{"x":"c1","y":"b1"},
      "c0":{"x":"b0","y":"a0"},"c1":{"x":"b1","y":"a1"},
    }
    return [{"history_id":s,"action":a,"next_history_id":t,"observation":obs[s]} for s in sorted(trans) for a,t in sorted(trans[s].items())]


def _primitive(carrier,observe,update,name):
    core={"carrier":list(carrier),"operations":{"observe":dict(observe),"update":{a:dict(v) for a,v in update.items()}},"action_alphabet":sorted(update),"relations":[],"invariants":["finite_total_update"]}
    return {"primitive_id":name,"primitive":core,"digest":digest_payload(core)}


def _representation_language_rows():
    rows = []
    cases = [
        ("path-a", "chain", [("a", "b"), ("b", "c")]),
        ("path-b", "chain", [("x", "y"), ("y", "z")]),
        ("pair-a", "disconnected", [("a", "b"), ("c", "d")]),
        ("pair-b", "disconnected", [("w", "x"), ("y", "z")]),
        ("path-c", "chain", [("m", "n"), ("n", "o")]),
        ("pair-c", "disconnected", [("m", "n"), ("o", "p")]),
    ]
    for trial, label, edges in cases:
        for src, dst in edges:
            rows.append({
                "trial": trial,
                "src": src,
                "dst": dst,
                "environment_id": trial,
                "label": label,
            })
    return rows


def run_release_qualification(root: str|Path|None=None)->dict[str,Any]:
    root=Path(root or Path(__file__).resolve().parents[1]); kernel=MathematicalInventionKernel(root)
    evidence=[
      {"mode":"residual","environment_id":"E1","metric":0.31},
      {"mode":"latent","environment_id":"E1","rank_gap":2},
      {"mode":"causal","environment_id":"E2","intervention_failure":True},
      {"mode":"counterfactual","environment_id":"E2","counterfactual_failure":True},
      {"mode":"cross_domain_bridge","environment_id":"E3","bridge_digest":"opaque"},
    ]
    unknown=kernel.unknown_unknown.discover(question="find minimal unknown representation type needed to predict and update an unknown controlled system",evidence_rows=evidence)
    weak=kernel.unknown_unknown.discover(question="unknown representation",evidence_rows=[{"mode":"residual","environment_id":"E1"}])
    freeze=digest_payload({"benchmark":"opaque_history_transitions","rows":_history_rows()})
    primitive=kernel.primitive.synthesize(transition_rows=_history_rows(),freeze_digest=freeze)
    incomplete=kernel.primitive.synthesize(transition_rows=_history_rows()[:-1],freeze_digest=freeze)
    # Positive exact quotient morphism. Within-group distinctions are intentionally lost.
    A=_primitive(["p0","p1","p2","p3"],{"p0":"0","p1":"0","p2":"1","p3":"1"},{
      "hold":{"p0":"p0","p1":"p1","p2":"p2","p3":"p3"},
      "toggle":{"p0":"p2","p1":"p3","p2":"p0","p3":"p1"}},"A")
    B=_primitive(["q0","q1"],{"q0":"0","q1":"1"},{"hold":{"q0":"q0","q1":"q1"},"toggle":{"q0":"q1","q1":"q0"}},"B")
    Bbad=_primitive(["q0","q1"],{"q0":"0","q1":"1"},{"hold":{"q0":"q0","q1":"q1"},"toggle":{"q0":"q0","q1":"q1"}},"Bbad")
    morph=kernel.morphism.discover(source=A,target=B); morph_bad=kernel.morphism.discover(source=A,target=Bbad)
    rows=[]
    for lam in (1.0,0.5,0.25,0.125,0.0625):
      rows.append({"lambda":lam,"state_error":0.20*lam,"update_error":0.10*(lam**1.2),"observable_error":0.05*(lam**0.8)})
    limit=kernel.limit.assess(parameter_rows=rows)
    no_limit=kernel.limit.assess(parameter_rows=[{"lambda":lam,"state_error":0.2,"update_error":0.1,"observable_error":0.05} for lam in (1.0,0.5,0.25,0.125,0.0625)])
    proof_artifact={
      "theorem_id":"ALGEBRAIC-CONTROL-001","statement":"Two exact polynomial identities hold for all real x.",
      "assumptions":[{"id":"A1","statement":"x is real"}],
      "lemmas":[
        {"id":"L1","statement":"(x+1)^2=x^2+2x+1","depends_on":["A1"],"verification":{"method":"EXACT_SYMBOLIC_IDENTITY","symbols":["x"],"lhs":"(x+1)**2","rhs":"x**2+2*x+1"}},
        {"id":"L2","statement":"(x-1)(x+1)=x^2-1","depends_on":["L1"],"verification":{"method":"EXACT_SYMBOLIC_IDENTITY","symbols":["x"],"lhs":"(x-1)*(x+1)","rhs":"x**2-1"}},
      ],
      "conclusion_id":"L2",
    }
    proof_graph=kernel.formal.decompose(proof_artifact)
    proof_verified=kernel.formal.verify(proof_artifact)
    broken_proof=dict(proof_artifact); broken_proof["lemmas"]=[dict(x) for x in proof_artifact["lemmas"]]
    broken_proof["lemmas"][1]=dict(broken_proof["lemmas"][1]); broken_proof["lemmas"][1]["verification"]={"method":"EXACT_SYMBOLIC_IDENTITY","symbols":["x"],"lhs":"x**2","rhs":"x**2+1"}
    proof_blocked=kernel.formal.verify(broken_proof)
    cex=kernel.formal.search_counterexample_regions({"search_id":"CEX-1","variables":{"x":[-2,-1,0,1,2]},"claim":"x**2 < 2"})
    finite_ok=kernel.formal.search_counterexample_regions({"search_id":"FINITE-OK","variables":{"x":[-1,0,1]},"claim":"x**2 >= 0"})
    handoff=kernel.formal.prepare_formal_kernel_handoff(proof_artifact,target_kernel="LEAN")
    external_attestation=kernel.formal.verify_external_formal_attestation({
      "attestation_id":"QUAL-EXTERNAL-KERNEL-REPLAY",
      "source_identity":{"repository":"https://example.invalid/formal","commit":"0123456789abcdef0123456789abcdef01234567"},
      "toolchain":{"kernel":"LEAN","version":"PINNED-QUALIFICATION"},
      "permitted_axioms":["propext"],
      "theorems":[{"theorem_id":"Qualification.theorem","accepted":True,"actual_axioms":["propext"]}],
      "replay_checks":[{"check_id":"KERNEL","checker":"qualification-checker","accepted":True,"source_unchanged":True,"formal_kernel_evidence":True,"evidence_digest":"a"*64}],
      "provenance":{"issuer":"qualification-fixture","source_url":"https://example.invalid/receipt","receipt_digest":"b"*64},
    })
    bad_external_attestation=kernel.formal.verify_external_formal_attestation({
      "attestation_id":"QUAL-EXTERNAL-BAD-AXIOM",
      "source_identity":{"repository":"https://example.invalid/formal","commit":"0123456789abcdef0123456789abcdef01234567"},
      "toolchain":{"kernel":"LEAN","version":"PINNED-QUALIFICATION"},
      "permitted_axioms":["propext"],
      "theorems":[{"theorem_id":"Qualification.theorem","accepted":True,"actual_axioms":["propext","undeclared"]}],
      "replay_checks":[{"check_id":"KERNEL","checker":"qualification-checker","accepted":True,"source_unchanged":True,"formal_kernel_evidence":True,"evidence_digest":"c"*64}],
      "provenance":{"issuer":"qualification-fixture","source_url":"https://example.invalid/bad","receipt_digest":"d"*64},
    })
    autonomous_birth=kernel.autonomous_candidate_birth.search(
      question="Prove or refute a frozen global statement without a named method",
      epoch_budget=2,axis_birth_budget_per_epoch=12,candidate_budget_per_epoch=6,
    )
    autonomous_birth_next=kernel.autonomous_candidate_birth.search(
      question="Prove or refute a frozen global statement without a named method",
      continuation=autonomous_birth["continuation"],
      epoch_budget=1,axis_birth_budget_per_epoch=12,candidate_budget_per_epoch=6,
    )
    discharge_candidates=[
      {
        "candidate_id":"DQ-C1","representation_family_id":"DQ-R1",
        "representation_signature":{"operation_sequence":["decompose","bound"],"research_local_axis_ids":["RAX-A","RAX-B"]},
        "proof_obligations":[
          {"obligation_id":"DQ-O1","kind":"ASSUMPTION_COMPATIBILITY","status":"UNRESOLVED"},
          {"obligation_id":"DQ-O2","kind":"DERIVE_OR_REFUTE_REPRESENTATION_INVARIANT","status":"UNRESOLVED",
           "verification":{"method":"EXACT_SYMBOLIC_IDENTITY","symbols":["x"],"lhs":"(x+1)**2","rhs":"x**2+2*x+1"}},
          {"obligation_id":"DQ-O3","kind":"COUNTEREXAMPLE_OR_OBSTRUCTION_SEARCH","status":"UNRESOLVED",
           "verification":{"method":"COUNTEREXAMPLE_REGION_SEARCH","search_id":"DQ-CEX","variables":{"x":[-2,-1,0,1,2]},"claim":"x**2 < 2"}},
          {"obligation_id":"DQ-O4","kind":"DERIVE_FROZEN_GOAL_OR_PROVE_BRANCH_IMPOSSIBLE","status":"UNRESOLVED"},
        ],
      },
      {
        "candidate_id":"DQ-C2","representation_family_id":"DQ-R2",
        "representation_signature":{"operation_sequence":["construct"],"research_local_axis_ids":["RAX-C"]},
        "proof_obligations":[
          {"obligation_id":"DQ-O5","kind":"DERIVE_OR_REFUTE_REPRESENTATION_INVARIANT","status":"UNRESOLVED",
           "verification":{"method":"EXACT_SYMBOLIC_IDENTITY","symbols":["x"],"lhs":"x**2","rhs":"x**2+1"}},
        ],
      },
    ]
    discharge=kernel.proof_discharge.discharge(candidates=discharge_candidates,execution_budget=16)
    discharge_portfolio=kernel.proof_discharge.compile_tasks(candidates=discharge_candidates,maximum_tasks=32)
    semantic_candidates=[
      {
        "candidate_id":"SEM-C1","representation_family_id":"SEM-R1",
        "representation_signature":{"operation_sequence":["derive"],"research_local_axis_ids":["RAX-SEM"]},
        "semantic_context":{"frozen_problem_statement":"For all x, (x+1)^2 = x^2 + 2*x + 1"},
        "proof_obligations":[
          {"obligation_id":"SEM-O1","kind":"DERIVE_FROZEN_GOAL_OR_PROVE_BRANCH_IMPOSSIBLE","status":"UNRESOLVED","semantic_claim":"For all x, (x+1)^2 = x^2 + 2*x + 1","semantic_role":"FROZEN_GOAL"},
          {"obligation_id":"SEM-O2","kind":"DERIVE_OR_REFUTE_REPRESENTATION_INVARIANT","status":"UNRESOLVED","semantic_claim":"For all x in {-2,-1,0,1,2}, x^2 >= 0","semantic_role":"BOUNDEDNESS_OR_GROWTH"},
          {"obligation_id":"SEM-O3","kind":"DERIVE_FROZEN_GOAL_OR_PROVE_BRANCH_IMPOSSIBLE","status":"UNRESOLVED","semantic_claim":"There exists a global smooth bounded solution with finite energy","semantic_role":"FROZEN_GOAL"},
        ],
      }
    ]
    semantic_portfolio=kernel.proof_discharge.compile_tasks(candidates=semantic_candidates,maximum_tasks=16)
    semantic_discharge=kernel.proof_discharge.discharge(candidates=semantic_candidates,execution_budget=16)
    semantic_blocked=next(t for t in semantic_portfolio["tasks"] if t["obligation_id"]=="SEM-O3")
    semantic_binding_synthesis=semantic_blocked["binding_synthesis"]
    binding_validation_candidate={
      "candidate_id":"SEM-BVAL-C1","representation_family_id":"SEM-BVAL-R1",
      "representation_signature":{"operation_sequence":["validate_binding"],"research_local_axis_ids":["RAX-BVAL"]},
      "proof_obligations":[dict(x) for x in semantic_binding_synthesis["binding_validation_obligations"]],
    }
    binding_validation_discharge=kernel.proof_discharge.discharge(candidates=[binding_validation_candidate],execution_budget=64)
    autonomous_semantic_discharge=kernel.proof_discharge.discharge(candidates=autonomous_birth["candidates"][:2],execution_budget=16)
    typed_operator_claim="Let a>0 and n=3. Fields y(x,t) satisfy ∂_t y = a Δy and div y=0. Determine whether there exists a global smooth bounded solution on R^3."
    typed_operator_compilation=kernel.semantic_obligation_compiler.compile(
      obligation={"obligation_id":"SEM-OP","kind":"DERIVE_FROZEN_GOAL_OR_PROVE_BRANCH_IMPOSSIBLE","status":"UNRESOLVED","semantic_claim":typed_operator_claim,"semantic_role":"FROZEN_GOAL"},
      candidate={"candidate_id":"SEM-OP-C","representation_family_id":"SEM-OP-R","semantic_context":{"frozen_problem_statement":typed_operator_claim}},
    )
    representation_rows = _representation_language_rows()
    representation_failure = kernel.representation_failure_detector.detect(
      frozen_problem="classify frozen relation outcomes",
      revision_history=[
        {"revision_kind":"ADAPTIVE_CONTEXT_AXIS","goal_closure_gain":0.0},
        {"revision_kind":"BINDING_REFINEMENT","goal_closure_gain":0.0},
      ],
      residual_rows=representation_rows,
    )
    representation_failure_weak = kernel.representation_failure_detector.detect(
      frozen_problem="single revision is not enough",
      revision_history=[{"revision_kind":"ADAPTIVE_CONTEXT_AXIS","goal_closure_gain":0.0}],
      residual_rows=representation_rows,
    )
    representation_birth = kernel.representation_language_birth.synthesize(
      failure_receipt=representation_failure,
      frozen_problem="classify frozen relation outcomes",
      evidence_rows=representation_rows,
      target_field="label",
      group_field="trial",
    )
    representation_birth_blocked = kernel.representation_language_birth.synthesize(
      failure_receipt=representation_failure_weak,
      frozen_problem="single revision is not enough",
      evidence_rows=representation_rows,
      target_field="label",
      group_field="trial",
    )
    representation_validation = kernel.representation_language_birth.validate(
      birth_receipt=representation_birth,
      evidence_rows=representation_rows,
    )
    checks={
      "kernel_owner_contract":kernel.contract()["owner_id"]=="PHI-MATHEMATICAL-INVENTION-KERNEL/1.5.0",
      "semantic_binding_invention_is_kernel_component":kernel.contract()["components"].get("semantic_binding_invention")==kernel.semantic_binding_invention.component_id and kernel.semantic_binding_invention.contract().get("authority")==kernel.contract()["owner_id"],
      "semantic_obligation_compiler_is_kernel_component":kernel.contract()["components"].get("semantic_proof_obligation_compiler")==kernel.semantic_obligation_compiler.component_id and kernel.semantic_obligation_compiler.contract().get("authority")==kernel.contract()["owner_id"],
      "proof_discharge_is_kernel_component":kernel.contract()["components"].get("proof_obligation_discharge")==kernel.proof_discharge.component_id and kernel.proof_discharge.contract().get("authority")==kernel.contract()["owner_id"],
      "representation_failure_detector_is_kernel_component":kernel.contract()["components"].get("representation_class_failure_detector")==kernel.representation_failure_detector.component_id and kernel.representation_failure_detector.contract().get("component")==kernel.representation_failure_detector.component_id,
      "representation_language_birth_is_kernel_component":kernel.contract()["components"].get("autonomous_representation_language_birth")==kernel.representation_language_birth.component_id and kernel.representation_language_birth.contract().get("canonicalization_allowed") is False,
      "representation_class_failure_requires_stalled_history":representation_failure["status"]=="REPRESENTATION_CLASS_INADEQUACY_HYPOTHESIS" and representation_failure_weak["status"]=="REPRESENTATION_CLASS_FAILURE_NOT_ESTABLISHED",
      "representation_language_birth_is_research_local_content_addressed":representation_birth["status"]=="GENERATED_REPRESENTATION_CLASS_PROPOSED" and representation_birth["representation_class"]["representation_class_id"].startswith("BORN-R-") and representation_birth["representation_class"]["canonical"] is False and representation_birth["representation_class"]["research_local"] is True,
      "representation_language_birth_blocks_without_failure":representation_birth_blocked["status"]=="REPRESENTATION_LANGUAGE_BIRTH_BLOCKED_NO_CLASS_FAILURE",
      "representation_language_validation_requires_non_renaming_gain":representation_validation["status"]=="REPRESENTATION_CLASS_BIRTH_VALIDATED_RESEARCH_LOCAL" and representation_validation["non_renaming_gate"] is True and representation_validation["goal_closure_gain"]>0.0 and representation_validation["accepted"] is True,
      "semantic_exact_identity_autocompiles_and_executes":any(r.get("obligation_id")=="SEM-O1" and r.get("method")=="EXACT_SYMBOLIC_IDENTITY" and r.get("discharged") is True for r in semantic_discharge["results"]),
      "semantic_finite_universal_autocompiles_and_executes":any(r.get("obligation_id")=="SEM-O2" and r.get("method")=="FINITE_EXHAUSTIVE_BOOLEAN" and r.get("discharged") is True for r in semantic_discharge["results"]),
      "semantic_high_level_claim_stays_typed_unresolved":semantic_blocked["status"]=="BLOCKED_BINDING_HYPOTHESES_REQUIRE_VALIDATION" and semantic_blocked["semantic_compilation"]["status"]=="TYPED_FORMAL_SCHEMA_COMPILED_REQUIRES_BINDINGS" and len(semantic_blocked["semantic_compilation"]["missing_bindings"])>=3,
      "binding_invention_builds_concrete_research_objects":len(semantic_binding_synthesis["generated_binding_objects"])>=3 and all(x.get("status")=="PROPOSED_RESEARCH_LOCAL_BINDING" for x in semantic_binding_synthesis["generated_binding_objects"]),
      "binding_invention_generates_validation_obligations":len(semantic_binding_synthesis["binding_validation_obligations"])>=6 and semantic_binding_synthesis["claim_boundary"]["generated_binding_is_discharged"] is False,
      "binding_provenance_and_welltypedness_execute":any(r.get("method")=="BINDING_OBJECT_PROVENANCE_ALIGNMENT" and r.get("discharged") is True for r in binding_validation_discharge["results"]) and any(r.get("method")=="BINDING_OBJECT_WELL_TYPEDNESS" and r.get("discharged") is True for r in binding_validation_discharge["results"]),
      "binding_discrimination_remains_unresolved_without_evidence":any(r.get("kind")=="BINDING_DISCRIMINATION_OR_CLOSURE_GAIN" for r in binding_validation_discharge["unresolved_obligation_seeds"]),
      "binding_invention_does_not_select_fixed_domain_catalog":kernel.semantic_binding_invention.contract()["fixed_domain_method_catalog"] is False,
      "semantic_formal_graph_is_frozen_even_when_unresolved":semantic_blocked["semantic_formal_graph"]["status"]=="PROOF_DEPENDENCY_GRAPH_FROZEN" and semantic_blocked["semantic_formal_graph"]["claim_boundary"]["theorem_verified"] is False,
      "typed_missing_bindings_feed_residual_seeds":any(r.get("obligation_id")=="SEM-O3" and len(r.get("missing_bindings",()))>=3 for r in semantic_discharge["unresolved_obligation_seeds"]),
      "born_obligations_are_semantically_compiled_without_external_solution":autonomous_semantic_discharge["semantic_compilation"]["typed_unresolved_count"]>0 and any(r.get("semantic_compilation_digest") for r in autonomous_semantic_discharge["unresolved_obligation_seeds"]),
      "differential_claim_compiles_operator_equations":typed_operator_compilation["status"]=="TYPED_FORMAL_SCHEMA_COMPILED_REQUIRES_BINDINGS" and len(typed_operator_compilation["typed_schema"]["explicit_relations"])>=4 and "LAPLACIAN" in typed_operator_compilation["typed_schema"]["operator_tokens"] and "DIVERGENCE" in typed_operator_compilation["typed_schema"]["operator_tokens"],
      "differential_claim_compiles_formal_obligation_artifact":typed_operator_compilation["formal_obligation_artifact"]["conclusion_id"]=="L-GOAL" and len(typed_operator_compilation["formal_obligation_artifact"]["assumptions"])>=4,
      "differential_claim_missing_semantics_remain_explicit":set(["FUNCTION_SPACE_OR_REGULARITY_PREDICATE_BINDING","OPERATOR_SYMBOL_SEMANTICS_BINDING","FUNCTION_SIGNATURE_AND_CODOMAIN_BINDING"]).issubset(set(typed_operator_compilation["missing_bindings"])),
      "discharge_executes_exact_and_counterexample_tasks":discharge["executed_task_count"]>=4 and discharge["discharged_obligation_count"]>=3,
      "discharge_found_counterexample_refutes_scoped_branch": "DQ-C1" in discharge["refuted_candidate_ids"],
      "false_exact_identity_does_not_discharge":any(r.get("candidate_id")=="DQ-C2" and r.get("discharged") is False and r.get("status")=="REFUTED_INTERNAL_EXACT" for r in discharge["results"]),
      "missing_executable_goal_remains_unresolved":any(r.get("obligation_id")=="DQ-O4" for r in discharge["unresolved_obligation_seeds"]),
      "task_priority_prefers_executable_closure":discharge_portfolio["tasks"][0]["status"]=="READY" and discharge_portfolio["ready_task_count"]>0,
      "closure_gain_not_truth_probability":discharge["claim_boundary"]["closure_gain_is_theorem_truth_probability"] is False,
      "function_language_birth_is_kernel_component_not_new_owner":kernel.contract()["components"].get("function_language_birth")=="FUNCTION-LANGUAGE-BIRTH/1.0.0-COMPONENT" and kernel.function_language.contract().get("authority")==kernel.contract()["owner_id"],
      "function_language_birth_not_global_catalog_space":kernel.function_language.contract().get("fixed_global_language_catalog_is_primary_space") is False,
      "autonomous_candidate_birth_is_kernel_component":kernel.contract()["components"].get("autonomous_mathematical_candidate_birth")==kernel.autonomous_candidate_birth.component_id and kernel.autonomous_candidate_birth.contract().get("authority")==kernel.contract()["owner_id"],
      "autonomous_candidate_birth_crosses_unknown_without_domain_owner":autonomous_birth["status"]=="OPEN_ENDED_MATHEMATICAL_FRONTIER_FROZEN" and autonomous_birth["candidate_count"]>=12 and autonomous_birth["research_local_axis_birth_count"]>0,
      "registered_space_not_search_ceiling":autonomous_birth["registered_axis_space_is_ceiling"] is False and autonomous_birth["claim_boundary"]["search_budget_exhaustion_is_solution"] is False,
      "new_operations_born_from_gap":autonomous_birth["born_operation_count"]>0 and any(str(x).startswith("born_op::") for x in autonomous_birth["operation_alphabet"]),
      "problem_structure_birth_has_semantic_provenance":autonomous_birth.get("problem_structure",{}).get("role_count",0)>0 and any(str(r.get("provenance"))=="FROZEN_PROBLEM_STRUCTURE" for r in autonomous_birth.get("research_local_axis_births",())),
      "continuation_carries_unresolved_proof_residuals":len(autonomous_birth.get("continuation",{}).get("unresolved_obligation_seeds",()))>0,
      "next_epoch_births_axes_from_proof_residuals":any(str(r.get("provenance"))=="UNRESOLVED_PROOF_OBLIGATION_RESIDUAL" for r in autonomous_birth_next.get("research_local_axis_births",())),
      "continuation_advances_unbounded_complexity_shell":autonomous_birth_next["search_epoch_start"]==autonomous_birth["continuation"]["next_epoch"] and autonomous_birth_next["epoch_receipts"][0]["representation_depth"]>autonomous_birth["epoch_receipts"][-1]["representation_depth"],
      "continuation_births_new_candidate_ids":set(x["candidate_id"] for x in autonomous_birth["candidates"]).isdisjoint(set(x["candidate_id"] for x in autonomous_birth_next["candidates"])),
      "generated_proof_programs_not_promoted_to_theorems":all(c["claim_boundary"]["theorem_proved"] is False for c in autonomous_birth["candidates"]) and autonomous_birth["claim_boundary"]["eventual_solution_guaranteed"] is False,
      "unknown_unknown_proposed":unknown["status"]=="PROPOSE_GENERATED_REPRESENTATION_SIGNATURE",
      "unknown_unknown_all_axes_scanned":unknown["phi_scan"]["all_registered_axes_visited"] and unknown["phi_scan"]["registered_axis_count"]==canonical_axis_count(),
      "unknown_unknown_no_fixed_visit_budget":unknown["phi_scan"]["fixed_owner_visit_budget"] is None and unknown["phi_scan"]["fixed_candidate_axis_order_ceiling"] is None,
      "blind_primitive_firewall":unknown["phi_scan"]["knowledge_firewall"]["mode"]=="BLIND_PRIMITIVE_FIREWALL" and unknown["phi_scan"]["knowledge_firewall"]["passport_names_used_for_source_scoring"] is False,
      "internet_not_prefreeze":unknown["claim_boundary"]["internet_used_prefreeze"] is False,
      "known_method_not_selected":unknown["claim_boundary"]["known_method_selected_as_answer"] is False and unknown["obligations"]["known_representation_name_required"] is False,
      "multi_evidence_modes_used":len(unknown["active_evidence_modes"])==5 and unknown["independent_environment_count"]==3,
      "weak_unknown_unknown_fails_closed":weak["status"]=="UNKNOWN_UNKNOWN_INSUFFICIENT_INDEPENDENT_MODES",
      "primitive_generated":primitive["status"]=="GENERATED_MINIMAL_ALGEBRAIC_PRIMITIVE",
      "primitive_not_named_known_method":primitive["primitive_type"]=="GENERATED_FINITE_ALGEBRAIC_SIGNATURE" and primitive["claim_boundary"]["known_representation_selected"] is False,
      "primitive_minimal_carrier_three":primitive["minimality_certificate"]["carrier_cardinality"]==3,
      "primitive_collapses_duplicate_histories":primitive["minimality_certificate"]["input_history_count"]==6 and len(set(primitive["primitive"]["history_to_carrier"].values()))==3,
      "primitive_pairwise_separated":primitive["minimality_certificate"]["all_distinct_carrier_pairs_behaviorally_separated"] is True,
      "primitive_update_total":all(set(v)==set(primitive["primitive"]["carrier"]) for v in primitive["primitive"]["operations"]["update"].values()),
      "incomplete_evidence_blocks_primitive":incomplete["status"]=="PRIMITIVE_SYNTHESIS_BLOCKED_INCOMPLETE_OR_INCONSISTENT_EVIDENCE",
      "world_novelty_not_claimed_for_primitive":primitive["claim_boundary"]["world_mathematical_novelty_established"] is False,
      "morphism_discovered":morph["status"]=="EXACT_MORPHISM_DISCOVERED",
      "morphism_preserves_observation":morph["morphism"] is not None and "observe" in morph["morphism"]["Preserve"],
      "morphism_preserves_update_commutation":morph["morphism"] is not None and "typed_update_commutation" in morph["morphism"]["Preserve"],
      "morphism_records_loss":morph["morphism"] is not None and "source_state_distinction" in morph["morphism"]["Lose"] and len(morph["morphism"]["collapsed_source_pairs"])>=2,
      "morphism_does_not_merge_canonicals":morph["claim_boundary"]["source_target_canonicals_merged"] is False,
      "bad_morphism_fails_closed":morph_bad["status"]=="NO_EXACT_MORPHISM_FOUND",
      "controlled_limit_found":limit["status"]=="CONTROLLED_LIMIT_ESTABLISHED",
      "controlled_limit_direction_discovered_not_supplied":limit["selected_limit_direction"]=="PARAMETER_TO_ZERO",
      "controlled_limit_all_components_pass":all(v["pass"] for d in limit["direction_evidence"] if d["direction"]=="PARAMETER_TO_ZERO" for v in d["components"].values()),
      "wrong_limit_direction_rejected":not next(d for d in limit["direction_evidence"] if d["direction"]=="PARAMETER_TO_INFINITY")["pass"],
      "no_limit_control_rejected":no_limit["status"]=="NO_CONTROLLED_LIMIT_ESTABLISHED",
      "controlled_limit_does_not_promote_theory":limit["claim_boundary"]["new_theory_promoted"] is False,
      "formal_verification_is_kernel_component":kernel.contract()["components"].get("formal_mathematical_verification")=="FORMAL-MATHEMATICAL-VERIFICATION/1.0.0",
      "proof_dependency_graph_frozen":proof_graph["status"]=="PROOF_DEPENDENCY_GRAPH_FROZEN" and proof_graph["conclusion_id"]=="L2",
      "exact_lemmas_verified_relative_to_assumptions":proof_verified["status"]=="FORMAL_DERIVATION_VERIFIED_RELATIVE_TO_DECLARED_ASSUMPTIONS" and proof_verified["verified"] is True,
      "false_identity_remains_proof_obligation":proof_blocked["status"]=="FORMAL_PROOF_OBLIGATIONS_REMAIN" and proof_blocked["verified"] is False and len(proof_blocked["proof_obligations"])==1,
      "counterexample_witness_found":cex["status"]=="COUNTEREXAMPLE_FOUND" and cex["counterexample_found"] is True,
      "finite_no_counterexample_not_unbounded_proof":finite_ok["status"]=="FINITE_REGION_EXHAUSTED_NO_COUNTEREXAMPLE" and finite_ok["claim_boundary"]["no_counterexample_in_finite_region_proves_unbounded_claim"] is False,
      "lean_handoff_frozen_and_not_self_verified":handoff["status"]=="FORMAL_KERNEL_HANDOFF_READY" and handoff["frozen_before_kernel_execution"] is True and handoff["claim_boundary"]["handoff_is_kernel_verification"] is False,
      "external_kernel_attestation_accepted_as_evidence_only":external_attestation["status"]=="EXTERNAL_FORMAL_ATTESTATION_ACCEPTED" and external_attestation["external_attestation_accepted"] is True and external_attestation["verified"] is False and external_attestation["locally_kernel_verified"] is False,
      "external_attestation_axiom_surface_audited":external_attestation["unexpected_axioms"]=={} and external_attestation["claim_boundary"]["axiom_surface_audited_against_declared_permitted_set"] is True,
      "unexpected_external_axiom_blocks_attestation":bad_external_attestation["status"]=="EXTERNAL_FORMAL_ATTESTATION_REJECTED" and bool(bad_external_attestation["unexpected_axioms"]),
      "canonical_axis_count_unchanged":canonical_axis_count()==unknown["phi_scan"]["registered_axis_count"],
      "mechanism_qualification_not_world_discovery":all(x is False for x in (unknown["claim_boundary"]["world_novelty_established"],primitive["claim_boundary"]["world_mathematical_novelty_established"],morph["claim_boundary"]["world_novelty_established"])),
    }
    passed=sum(bool(v) for v in checks.values())
    payload={
      "schema":SCHEMA,"release":RELEASE,"owner_id":"PHI-MATHEMATICAL-INVENTION-QUALIFICATION/1.0.0",
      "status":"PASS_PHI_MATHEMATICAL_INVENTION_QUALIFICATION" if passed==len(checks) else "BLOCKED_PHI_MATHEMATICAL_INVENTION_QUALIFICATION",
      "passed":passed,"total":len(checks),"checks":[{"check":k,"status":"PASS" if v else "FAIL"} for k,v in checks.items()],
      "demonstration":{"autonomous_candidate_birth":{"initial":autonomous_birth,"continued":autonomous_birth_next},"unknown_unknown":unknown,"primitive":primitive,"morphism":morph,"controlled_limit":limit,"formal_verification":{"graph":proof_graph,"verified":proof_verified,"handoff":handoff,"counterexample":cex,"external_attestation":external_attestation},"semantic_obligation_compilation":{"portfolio":semantic_portfolio,"execution":semantic_discharge,"autonomous_execution":autonomous_semantic_discharge,"typed_operator_compilation":typed_operator_compilation,"binding_synthesis":semantic_binding_synthesis,"binding_validation_discharge":binding_validation_discharge},"proof_obligation_discharge":{"portfolio":discharge_portfolio,"execution":discharge},"negative_controls":{"weak_unknown":weak,"incomplete_primitive":incomplete,"morphism":morph_bad,"limit":no_limit,"proof":proof_blocked}},
      "claim_boundary":{"synthetic_qualification_is_new_mathematics":False,"world_novelty_established":False,"internet_used_prefreeze":False,"known_method_catalog_used_as_answer":False,"canonical_axis_count":canonical_axis_count()},
    }
    payload["digest"]=digest_payload(payload); return payload

if __name__=="__main__":
    print(json.dumps(run_release_qualification(),ensure_ascii=False,indent=2,sort_keys=True))
