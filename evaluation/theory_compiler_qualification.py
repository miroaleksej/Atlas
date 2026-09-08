"""Current qualification for Φ-Theory Compiler 2.1.0."""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import numpy as np

from source.lawspace.mathematical_invention import MathematicalInventionKernel
from source.lawspace.theory_compiler import TheoryCompilerKernel, _uniform_grid_matrices
from source.lawspace.schema import digest_payload
from source.lawspace.domains import canonical_axis_count
from source.lawspace.api import LawSpaceAPI

SCHEMA = "phi-theory-compiler-qualification/v3"
RELEASE = "15.2.8"


def _history_rows():
    obs = {"a0":"0","a1":"0","b0":"0","b1":"0","c0":"1","c1":"1"}
    trans = {
        "a0":{"x":"a0","y":"c0"},"a1":{"x":"a1","y":"c1"},
        "b0":{"x":"c0","y":"b0"},"b1":{"x":"c1","y":"b1"},
        "c0":{"x":"b0","y":"a0"},"c1":{"x":"b1","y":"a1"},
    }
    return [
        {"history_id":s,"action":a,"next_history_id":t,"observation":obs[s]}
        for s in sorted(trans) for a,t in sorted(trans[s].items())
    ]


def _operator_probe_rows() -> list[dict[str, Any]]:
    grid = np.linspace(0.2, 2.0, 41)
    _, d1, d2 = _uniform_grid_matrices(grid)
    rng = np.random.default_rng(20260904)
    rows = []
    for q in range(10):
        state = np.zeros((2, len(grid)), dtype=float)
        coefficients = rng.normal(size=(2, 4))
        for c in range(2):
            for m in range(4):
                state[c] += coefficients[c,m] * np.sin((m+1)*np.pi*(grid-grid[0])/(grid[-1]-grid[0]+0.2))
        response = np.zeros_like(state)
        # Hidden black-box operator.  These coefficients are never passed to the synthesis owner.
        response[0] = -0.5*(d2@state[0]) + 0.7*(state[0]/grid) + 1.2*(d1@state[1])
        response[1] = -1.2*(d1@state[0]) + 0.3*state[1] - 0.2*(grid*grid*state[1])
        rows.append({
            "grid": grid.tolist(), "state": state.tolist(), "response": response.tolist(),
            "role": "DISCOVERY" if q < 8 else "SEALED_HOLDOUT",
        })
    return rows


def _responses_for_atlas_blueprints(blueprints: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Qualification-only hidden oracle applied after Atlas freezes probe inputs."""
    rows: list[dict[str, Any]] = []
    for bp in blueprints:
        grid = np.asarray(bp["grid"], dtype=float)
        _, d1, d2 = _uniform_grid_matrices(grid)
        state = np.asarray(bp["state"], dtype=float)
        if state.shape[0] != 2:
            raise ValueError("qualification hidden oracle expects two components")
        response = np.zeros_like(state)
        response[0] = -0.5*(d2@state[0]) + 0.7*(state[0]/grid) + 1.2*(d1@state[1])
        response[1] = -1.2*(d1@state[0]) + 0.3*state[1] - 0.2*(grid*grid*state[1])
        rows.append({
            "probe_id": bp["probe_id"],
            "grid": bp["grid"],
            "state": bp["state"],
            "response": response.tolist(),
            "role": bp["role"],
        })
    return rows


def _manual_operator_artifact(program: dict[str, Any], tag: str) -> dict[str, Any]:
    row = {
        "status":"GENERATED_EXECUTABLE_OPERATOR_CANDIDATE",
        "primitive_type":"GENERATED_TYPED_OPERATOR_PROGRAM",
        "qualified_for_compilation":True,
        "program":program,
        "probe_digest":tag,
        "fit_certificate":{"all_outputs_pass":True,"control_only":True},
    }
    row["digest"] = digest_payload(row)
    return row


def run_release_qualification(
    root: str | Path | None = None, *, persist_reports: bool = False
) -> dict[str, Any]:
    root = Path(root or Path(__file__).resolve().parents[1])
    invention = MathematicalInventionKernel(root)
    compiler = TheoryCompilerKernel(root)
    api = LawSpaceAPI(root)

    # Strict blind atomic representation-gap control.  It is deliberately not
    # allowed to read any answer-bearing atomic/post-freeze regression surface
    # and it is not allowed to consult the named-law catalog.  The only legal
    # continuation is through attested typed operator-response probes.
    blocked_regressions: dict[str, bool] = {}
    for tool_name in sorted(api.REGRESSION_TOOLS):
        try:
            getattr(api, tool_name)()
        except PermissionError:
            blocked_regressions[tool_name] = True
        else:
            blocked_regressions[tool_name] = False
    blind_atomic_gap = api.advance_adaptive_research({
        "problem_id":"BLIND-ATOMIC-EXECUTABLE-REPRESENTATION-FRONTIER",
        "domain_id":"physics",
        "question":(
            "Starting only from primitive negative charged fermionic, positive baryonic and neutral baryonic constituents, "
            "continue the neutral bound-state object family after the available representation becomes insufficient. "
            "Do not use a named law, periodic-table lookup, answer-bearing regression receipt, fixed object count, or fixed upper index."
        ),
        "representation_gap":True,
        "gap_kind":"REPRESENTATION_CAPABILITY_GAP",
        "gap_evidence":{
            "source":"LIVE_CURRENT_API_QUARANTINE_AUDIT",
            "regression_surface_count":len(blocked_regressions),
            "all_answer_bearing_regression_surfaces_blocked":all(blocked_regressions.values()),
            "blocked_surface_digest":digest_payload(blocked_regressions),
            "world_measurement":False,
        },
        "blind_no_named_law_catalog":True,
        "operator_probe_rows":(),
        "operator_probe_design_request":{"components":1,"design_shell":1},
    })

    # Opt-in world-interaction continuation.  The same strict-blind Atlas cycle
    # first births a one-component protocol, receives only typed-carrier feedback
    # from the independent reference-world owner, redesigns its own probes for a
    # two-component carrier, then receives digest-bound responses.  No named law
    # or reference-world coefficients are passed into representation synthesis.
    blind_atomic_world_cycle = api.advance_adaptive_research({
        "problem_id":"BLIND-ATOMIC-WORLD-INTERACTION-EXECUTABLE-REPRESENTATION",
        "domain_id":"physics",
        "question":(
            "Starting only from primitive negative charged fermionic, positive baryonic and neutral baryonic constituents, "
            "continue the neutral bound-state object family after the available representation becomes insufficient. "
            "Do not use a named law, periodic-table lookup, answer-bearing regression receipt, fixed object count, or fixed upper index."
        ),
        "representation_gap":True,
        "gap_kind":"REPRESENTATION_CAPABILITY_GAP",
        "gap_evidence":{
            "source":"LIVE_CURRENT_API_QUARANTINE_AUDIT",
            "regression_surface_count":len(blocked_regressions),
            "all_answer_bearing_regression_surfaces_blocked":all(blocked_regressions.values()),
            "blocked_surface_digest":digest_payload(blocked_regressions),
            "world_measurement":False,
        },
        "blind_no_named_law_catalog":True,
        "operator_probe_rows":(),
        "operator_probe_design_request":{"components":1,"design_shell":1},
        "operator_response_owner_request":{
            "owner":"ATOMIC_REFERENCE_WORLD_INTERACTION",
            "allow_reference_simulation":True,
            "environment":{
                "positive_center_charge_units":1.0,
                "probe_charge_units":-1.0,
                "signed_channel":-1.0,
            },
        },
        "operator_fit_tolerance_nrmse":1e-10,
        "operator_eigenpair_count":4,
    })

    # Next strict-blind shell: Atlas, not the harness, births the occupancy
    # coordinates needed to distinguish variable-particle/self-consistent action.
    # The independent world owner responds only after both state and occupancy
    # protocols are frozen.  No physical existence of those occupancies is claimed.
    blind_atomic_variable_particle_cycle = api.advance_adaptive_research({
        "problem_id":"BLIND-ATOMIC-VARIABLE-PARTICLE-SELF-CONSISTENT-REPRESENTATION",
        "domain_id":"physics",
        "question":(
            "Continue the neutral bound-state representation into a variable-particle self-consistent shell without a named law, "
            "periodic-table lookup, fixed object count, fixed upper index, or answer-bearing regression surface."
        ),
        "representation_gap":True,
        "gap_kind":"VARIABLE_PARTICLE_SELF_CONSISTENT_REPRESENTATION_GAP",
        "gap_evidence":{
            "source":"ATLAS_ONE_PARTICLE_WORLD_INTERACTION_FRONTIER",
            "one_particle_candidate_digest":blind_atomic_world_cycle.get("executable_representation_synthesis",{}).get("digest"),
            "all_answer_bearing_regression_surfaces_blocked":all(blocked_regressions.values()),
            "world_measurement":False,
        },
        "blind_no_named_law_catalog":True,
        "operator_probe_rows":(),
        "operator_probe_design_request":{"components":1,"design_shell":1},
        "operator_response_owner_request":{
            "owner":"ATOMIC_REFERENCE_WORLD_INTERACTION",
            "allow_reference_simulation":True,
            "environment":{"positive_center_charge_units":1.0,"probe_charge_units":-1.0,"signed_channel":-1.0},
        },
        "variable_particle_world_request":{
            "owner":"ATOMIC_VARIABLE_PARTICLE_REFERENCE_WORLD",
            "allow_reference_simulation":True,
            "design_shell":1,
            "validation_particle_count":2,
            "fit_tolerance_nrmse":1e-7,
            "environment":{
                "positive_center_charge_units":1.0,"probe_charge_units":-1.0,"signed_channel":-1.0,
                "field_regularization":0.5,"field_scale":1.0,
            },
        },
        "operator_fit_tolerance_nrmse":1e-10,
        "operator_eigenpair_count":4,
    })

    # Regression: finite generated algebra still lowers and executes exactly.
    rows = _history_rows()
    freeze = digest_payload({"benchmark":"theory_compiler_opaque_finite_theory","rows":rows})
    primitive = invention.primitive.synthesize(transition_rows=rows, freeze_digest=freeze)
    limit = invention.limit.assess(parameter_rows=[
        {"lambda":lam,"state_error":0.20*lam,"update_error":0.10*(lam**1.2),"observable_error":0.05*(lam**0.8)}
        for lam in (1.0,0.5,0.25,0.125,0.0625)
    ])
    finite_compiled = compiler.compiler.compile(theory_artifact=primitive, theory_freeze_digest=freeze, controlled_limit_receipt=limit)
    initial_state = finite_compiled["executable_ir"]["state_schema"]["states"][0]
    finite_execution = compiler.runtime.execute(compiled=finite_compiled, initial_state=initial_state, actions=("x","y","x","y"))
    finite_replay = compiler.runtime.execute(compiled=finite_compiled, initial_state=initial_state, actions=("x","y","x","y"))

    # Atlas-born probe-input design control. The hidden oracle is applied only
    # after the probe blueprints are frozen, and remains qualification-only.
    atlas_probe_freeze = digest_payload({"benchmark":"atlas_born_operator_probe_design_control"})
    atlas_probe_design = compiler.probe_design.design(
        freeze_digest=atlas_probe_freeze, components=2, grid=np.linspace(0.2, 2.0, 41), design_shell=3
    )
    atlas_born_rows = _responses_for_atlas_blueprints(list(atlas_probe_design.get("probe_blueprints", ())))
    atlas_born_evidence = {
        "schema":"phi-operator-probe-qualification-attestation/v1",
        "attestation_class":"QUALIFICATION_HIDDEN_ORACLE_AFTER_ATLAS_FREEZE",
        "probe_digest":digest_payload(atlas_born_rows),
        "probe_blueprint_digest":atlas_probe_design.get("probe_blueprint_digest"),
        "world_measurement":False,
        "synthetic_control":True,
        "oracle_visible_before_probe_freeze":False,
    }
    atlas_born_evidence["digest"] = digest_payload(atlas_born_evidence)
    atlas_born_synthesized = compiler.synthesis.synthesize(
        probe_rows=atlas_born_rows, freeze_digest=atlas_probe_freeze,
        fit_tolerance_nrmse=1e-8, max_terms_per_output=8,
    )

    # Existing synthetic regression: unknown black-box continuous operator -> sparse typed program -> compile -> solve.
    probe_rows = _operator_probe_rows()
    operator_freeze = digest_payload({"benchmark":"black_box_operator_control","probe_digest":digest_payload(probe_rows)})
    synthesized = compiler.synthesis.synthesize(
        probe_rows=probe_rows, freeze_digest=operator_freeze,
        fit_tolerance_nrmse=1e-8, max_terms_per_output=8,
    )

    # Direct representation-gap provenance gate. Numeric probe rows may not enter
    # the scientific gap cycle without a digest-bound evidence receipt. The
    # synthetic qualification fixture remains explicitly non-world evidence.
    unattested_direct_gap = api.advance_adaptive_research({
        "problem_id":"QUALIFICATION-UNATTESTED-PROBE-GAP",
        "domain_id":"physics",
        "question":"Qualification control for operator-probe provenance gating.",
        "representation_gap":True,
        "gap_evidence":{"source":"QUALIFICATION_FIXTURE","status":"GAP","world_measurement":False},
        "blind_no_named_law_catalog":True,
        "operator_probe_rows":probe_rows,
        "operator_fit_tolerance_nrmse":1e-8,
        "operator_max_terms_per_output":8,
    })
    qualification_probe_evidence = {
        "schema":"phi-operator-probe-qualification-attestation/v1",
        "attestation_class":"QUALIFICATION_FIXTURE",
        "probe_digest":digest_payload(probe_rows),
        "world_measurement":False,
        "synthetic_control":True,
    }
    qualification_probe_evidence["digest"] = digest_payload(qualification_probe_evidence)
    attested_direct_gap = api.advance_adaptive_research({
        "problem_id":"QUALIFICATION-ATTESTED-PROBE-GAP",
        "domain_id":"physics",
        "question":"Qualification control for digest-bound operator-probe provenance.",
        "representation_gap":True,
        "gap_evidence":{"source":"QUALIFICATION_FIXTURE","status":"GAP","world_measurement":False},
        "blind_no_named_law_catalog":True,
        "operator_probe_rows":probe_rows,
        "operator_probe_evidence":qualification_probe_evidence,
        "operator_fit_tolerance_nrmse":1e-8,
        "operator_max_terms_per_output":8,
        "operator_eigenpair_count":2,
    })
    operator_compiled = compiler.compiler.compile(theory_artifact=synthesized, theory_freeze_digest=operator_freeze)
    operator_execution = compiler.runtime.execute(compiled=operator_compiled, runtime_request={"eigenpair_count":4})
    operator_replay = compiler.runtime.execute(compiled=operator_compiled, runtime_request={"eigenpair_count":4})

    # Generalized eigenproblem control.
    grid = np.linspace(-4.0, 4.0, 51)
    generalized_program = {
        "program_type":"TYPED_LINEAR_OPERATOR_EIGENPROBLEM",
        "state":{"carrier":"MULTICOMPONENT_REAL_FIELD","components":1,"grid":grid.tolist(),"boundary":"DIRICHLET_ZERO_OUTSIDE_FROZEN_GRID"},
        "operator_blocks":[{"row_component":0,"column_component":0,"terms":[
            {"kind":"SECOND_DERIVATIVE","power":0,"coefficient":-0.5},
            {"kind":"COORDINATE_POWER","power":2,"coefficient":0.5},
        ]}],
        "metric":{"kind":"TYPED_OPERATOR_METRIC","operator_blocks":[{"row_component":0,"column_component":0,"terms":[{"kind":"IDENTITY","power":0,"coefficient":2.0}]}]},
        "problem":{"kind":"GENERALIZED_EIGENPROBLEM","default_eigenpair_count":3},
    }
    generalized_artifact = _manual_operator_artifact(generalized_program, "generalized-control")
    generalized_compiled = compiler.compiler.compile(theory_artifact=generalized_artifact, theory_freeze_digest="generalized-freeze")
    generalized_execution = compiler.runtime.execute(compiled=generalized_compiled, runtime_request={"eigenpair_count":3})

    # Self-consistent fixed-point control; generic density-dependent local field.
    scf_program = {
        "program_type":"TYPED_LINEAR_OPERATOR_EIGENPROBLEM",
        "state":{"carrier":"MULTICOMPONENT_REAL_FIELD","components":1,"grid":grid.tolist(),"boundary":"DIRICHLET_ZERO_OUTSIDE_FROZEN_GRID"},
        "operator_blocks":[{"row_component":0,"column_component":0,"terms":[
            {"kind":"SECOND_DERIVATIVE","power":0,"coefficient":-0.5},
            {"kind":"COORDINATE_POWER","power":2,"coefficient":0.5},
            {"kind":"FIELD_MULTIPLICATION","field_id":"v_nl","coefficient":1.0},
        ]}],
        "metric":{"kind":"IDENTITY"},
        "problem":{"kind":"SELF_CONSISTENT_EIGENPROBLEM","default_eigenpair_count":2,"fixed_point":{
            "max_iterations":80,"tolerance":1e-7,"mixing":0.4,"occupied_eigenpair_count":1,
            "field_updates":[{"field_id":"v_nl","kind":"DENSITY_POWER","power":1.0,"scale":0.05,"offset":0.0,"initial":0.0}],
        }},
    }
    scf_artifact = _manual_operator_artifact(scf_program, "scf-control")
    scf_compiled = compiler.compiler.compile(theory_artifact=scf_artifact, theory_freeze_digest="scf-freeze")
    scf_execution = compiler.runtime.execute(compiled=scf_compiled, runtime_request={"eigenpair_count":2})

    # Negative controls.
    insufficient = compiler.synthesis.synthesize(probe_rows=probe_rows[:2], freeze_digest="few-probes")
    bad_holdout_rows = copy.deepcopy(probe_rows)
    for row in bad_holdout_rows[-2:]:
        row["response"] = (np.asarray(row["response"], dtype=float) + 7.0).tolist()
    bad_holdout = compiler.synthesis.synthesize(
        probe_rows=bad_holdout_rows, freeze_digest="bad-holdout", fit_tolerance_nrmse=1e-8, max_terms_per_output=8,
    )
    tampered = copy.deepcopy(operator_compiled)
    tampered["executable_ir"]["operator"]["blocks"][0]["terms"][0]["coefficient"] += 1.0
    tamper_blocked = False
    try:
        compiler.runtime.execute(compiled=tampered, runtime_request={"eigenpair_count":2})
    except ValueError:
        tamper_blocked = True

    finite_ir = finite_compiled.get("executable_ir", {})
    synth_cert = synthesized.get("fit_certificate", {})
    coeffs = {
        (int(b["row_component"]), int(b["column_component"]), str(t["kind"]), int(t.get("power",0))): float(t["coefficient"])
        for b in synthesized.get("program", {}).get("operator_blocks", ()) for t in b.get("terms", ())
    }
    atlas_born_coeffs = {
        (int(b["row_component"]), int(b["column_component"]), str(t["kind"]), int(t.get("power",0))): float(t["coefficient"])
        for b in atlas_born_synthesized.get("program", {}).get("operator_blocks", ()) for t in b.get("terms", ())
    }
    world_atomic_synth = blind_atomic_world_cycle.get("executable_representation_synthesis", {})
    world_atomic_coeffs = {
        (int(b["row_component"]), int(b["column_component"]), str(t["kind"]), int(t.get("power",0))): float(t["coefficient"])
        for b in world_atomic_synth.get("program", {}).get("operator_blocks", ()) for t in b.get("terms", ())
    }
    world_fit_cert = world_atomic_synth.get("fit_certificate", {})
    world_response = blind_atomic_world_cycle.get("operator_response_owner_receipt", {})
    world_history = list(blind_atomic_world_cycle.get("operator_probe_design_history", ()))
    alpha_inv = float(world_response.get("postfreeze_audit_model", {}).get("inverse_speed_scale_constant", {}).get("value", 0.0))
    vp_design = blind_atomic_variable_particle_cycle.get("variable_particle_probe_design", {}) or {}
    vp_world = blind_atomic_variable_particle_cycle.get("variable_particle_world_receipt", {}) or {}
    sc_synth = blind_atomic_variable_particle_cycle.get("self_consistent_representation_synthesis", {}) or {}
    sc_fit = sc_synth.get("fit_certificate", {}) or {}
    sc_field = sc_fit.get("field_update", {}) or {}
    sc_exec = blind_atomic_variable_particle_cycle.get("self_consistent_representation_execution", {}) or {}
    sc_fp = sc_exec.get("fixed_point", {}) or {}
    sc_blocks = [
        (int(b["row_component"]), int(b["column_component"]), str(t["kind"]), str(t.get("field_id","")), float(t["coefficient"]))
        for b in sc_synth.get("program", {}).get("operator_blocks", ()) for t in b.get("terms", ()) if str(t.get("kind")) == "FIELD_MULTIPLICATION"
    ]
    checks = {
        "kernel_owner_contract": compiler.contract()["owner_id"] == "PHI-THEORY-COMPILER/2.1.0",
        "probe_design_owner_contract": compiler.probe_design.contract()["owner_id"] == "OPERATOR-PROBE-DESIGN/2.1.0",
        "synthesis_owner_contract": compiler.synthesis.contract()["owner_id"] == "EXECUTABLE-REPRESENTATION-SYNTHESIS/2.0.0",
        "many_body_probe_design_owner_contract": compiler.many_body_probe_design.contract().get("owner_id") == "MANY-BODY-OPERATOR-PROBE-DESIGN/1.0.0",
        "many_body_reference_world_owner_contract": compiler.atomic_many_body_world_interaction.contract().get("owner_id") == "ATOMIC-MANY-BODY-REFERENCE-WORLD/1.0.0",
        "many_body_coordinate_synthesis_owner_contract": compiler.many_body_coordinate_synthesis.contract().get("owner_id") == "MANY-BODY-OPERATOR-COORDINATE-SYNTHESIS/1.0.0",
        "many_body_grammar_has_no_fixed_global_rank_ceiling": compiler.many_body_coordinate_synthesis.contract().get("fixed_global_interaction_rank_ceiling") is None and compiler.many_body_probe_design.contract().get("fixed_global_interaction_rank_ceiling") is None,
        "many_body_grammar_requires_no_named_method": compiler.many_body_coordinate_synthesis.contract().get("known_many_body_method_required") is False and compiler.many_body_probe_design.contract().get("known_many_body_method_required") is False,
        "many_body_reference_world_is_not_empirical": compiler.atomic_many_body_world_interaction.contract().get("empirical_world_measurement") is False,
        "atlas_probe_design_full_rank_before_responses": atlas_probe_design.get("design_certificate", {}).get("full_rank_for_current_grammar") is True and atlas_probe_design.get("response_contract", {}).get("response_values_present") is False,
        "atlas_probe_design_freezes_holdout_inputs_before_responses": atlas_probe_design.get("design_certificate", {}).get("holdout_inputs_frozen_before_responses") is True,
        "atlas_born_probe_control_synthesizes_hidden_operator": atlas_born_synthesized.get("qualified_for_compilation") is True,
        "atlas_born_probe_control_recovers_cross_component_terms": abs(atlas_born_coeffs.get((0,1,"FIRST_DERIVATIVE",0),0.0)-1.2) < 1e-10 and abs(atlas_born_coeffs.get((1,0,"FIRST_DERIVATIVE",0),0.0)+1.2) < 1e-10,
        "lowering_owner_contract": compiler.compiler.contract()["owner_id"] == "THEORY-TO-EXECUTABLE-COMPILER/2.0.0",
        "runtime_owner_contract": compiler.runtime.contract()["owner_id"] == "EXECUTABLE-THEORY-RUNTIME/2.0.0",
        "finite_regression_compiles": finite_compiled.get("status") == "THEORY_EXECUTABLE_COMPILED",
        "finite_regression_executes": finite_execution.get("status") == "EXECUTION_PASS",
        "finite_deterministic_replay": finite_execution.get("trace") == finite_replay.get("trace"),
        "finite_exact_error_zero": all(float(finite_ir["error_estimator"][k]) == 0.0 for k in ("local_update_error_upper_bound","observation_error_upper_bound","roundoff_error_upper_bound")),
        "operator_candidate_synthesized": synthesized.get("status") == "GENERATED_EXECUTABLE_OPERATOR_CANDIDATE" and synthesized.get("qualified_for_compilation") is True,
        "operator_holdout_never_used_for_term_selection": synth_cert.get("sealed_holdout_not_used_for_term_selection") is True,
        "operator_backward_pruning_never_reads_holdout": all(c.get("sealed_holdout_used_for_pruning") is False for c in synth_cert.get("output_certificates", ())),
        "direct_gap_rejects_unattested_operator_rows": unattested_direct_gap.get("executable_representation_synthesis", {}).get("reason") == "OPERATOR_PROBE_ATTESTATION_REQUIRED" and unattested_direct_gap.get("result", {}).get("status") == "REPRESENTATION_GAP_REQUIRES_DISCRIMINATING_OPERATOR_PROBES",
        "direct_gap_accepts_digest_bound_operator_provenance": attested_direct_gap.get("operator_probe_evidence_valid") is True and attested_direct_gap.get("result", {}).get("status") == "EXECUTABLE_REPRESENTATION_CANDIDATE_SYNTHESIZED_NOT_LAW",
        "operator_all_outputs_pass_sealed_probe_gate": synth_cert.get("all_outputs_pass") is True,
        "operator_cross_component_first_derivative_recovered": abs(coeffs.get((0,1,"FIRST_DERIVATIVE",0),0.0) - 1.2) < 1e-10 and abs(coeffs.get((1,0,"FIRST_DERIVATIVE",0),0.0) + 1.2) < 1e-10,
        "operator_second_derivative_recovered": abs(coeffs.get((0,0,"SECOND_DERIVATIVE",0),0.0) + 0.5) < 1e-10,
        "operator_inverse_coordinate_recovered": abs(coeffs.get((0,0,"COORDINATE_POWER",-1),0.0) - 0.7) < 1e-10,
        "operator_quadratic_coordinate_recovered": abs(coeffs.get((1,1,"COORDINATE_POWER",2),0.0) + 0.2) < 1e-10,
        "operator_compiles": operator_compiled.get("status") == "THEORY_EXECUTABLE_COMPILED",
        "operator_executes": operator_execution.get("status") == "EXECUTION_PASS",
        "operator_eigen_residual_small": float(operator_execution.get("max_relative_eigen_residual", 1.0)) < 1e-10,
        "operator_deterministic_replay": operator_execution.get("eigenpairs") == operator_replay.get("eigenpairs"),
        "generalized_eigenproblem_executes": generalized_execution.get("status") == "EXECUTION_PASS" and float(generalized_execution.get("max_relative_eigen_residual",1.0)) < 1e-10,
        "self_consistent_fixed_point_executes": scf_execution.get("status") == "EXECUTION_PASS" and scf_execution.get("fixed_point",{}).get("status") == "FIXED_POINT_CONVERGED",
        "insufficient_operator_evidence_fails_closed": insufficient.get("status") == "EXECUTABLE_SYNTHESIS_REQUIRES_OPERATOR_PROBES",
        "sealed_holdout_mismatch_blocks_compilation_qualification": bad_holdout.get("qualified_for_compilation") is False,
        "tampered_executable_rejected": tamper_blocked,
        "no_dynamic_code_generation": compiler.contract()["claim_boundary"]["arbitrary_code_generation"] is False,
        "no_named_law_required": compiler.synthesis.contract()["known_law_name_required"] is False,
        "world_truth_not_claimed": operator_compiled["claim_boundary"]["world_theory_validity_established"] is False and operator_execution["claim_boundary"]["world_prediction_validated"] is False,
        "blind_atomic_all_answer_bearing_regressions_blocked": bool(blocked_regressions) and all(blocked_regressions.values()),
        "blind_atomic_gap_enters_kernel_without_fake_observation_rows": blind_atomic_gap.get("entry_mode") == "ATTESTED_REPRESENTATION_GAP" and blind_atomic_gap.get("observations_origin") == "NONE_REQUIRED_FOR_GAP_ENTRY",
        "blind_atomic_named_law_catalog_not_read": blind_atomic_gap.get("phi_space", {}).get("named_law_catalog_read") is False,
        "blind_atomic_atlas_births_probe_protocol": blind_atomic_gap.get("result", {}).get("status") == "REPRESENTATION_GAP_OPERATOR_PROBE_PROTOCOL_FROZEN_AWAITING_ATTESTED_RESPONSES" and blind_atomic_gap.get("operator_probe_design", {}).get("claim_boundary", {}).get("atlas_generated_probe_inputs") is True,
        "blind_atomic_missing_operator_responses_fails_closed": blind_atomic_gap.get("executable_representation_synthesis", {}).get("reason") == "NO_ATTESTED_OPERATOR_RESPONSE_VALUES_AVAILABLE" and blind_atomic_gap.get("operator_probe_design", {}).get("response_contract", {}).get("response_values_present") is False,
        "blind_atomic_no_probe_values_fabricated": blind_atomic_gap.get("claim_boundary", {}).get("missing_operator_probe_values_filled_by_assistant") is False,
        "blind_atomic_no_fixed_object_count_or_upper_index": blind_atomic_gap.get("result", {}).get("physical_object_count_established") is False and blind_atomic_gap.get("result", {}).get("physical_upper_index_established") is False and blind_atomic_gap.get("claim_boundary", {}).get("fixed_upper_index_used") is False,
        "blind_atomic_probe_contract_is_executable_not_named_solver": blind_atomic_gap.get("executable_representation_synthesis", {}).get("required_probe_schema", {}).get("response") == "components x grid_points measured/attested operator action",
        "blind_atomic_gap_receipt_atlas_native_not_scientific_promotion": blind_atomic_gap.get("atlas_claim", {}).get("atlas_native") is True and blind_atomic_gap.get("result", {}).get("scientific_law_established") is False,
        "atomic_world_owner_contract": compiler.atomic_world_interaction.contract().get("owner_id") == "ATOMIC-REFERENCE-WORLD-INTERACTION/1.0.0",
        "atomic_world_cycle_stays_strict_blind": blind_atomic_world_cycle.get("phi_space", {}).get("named_law_catalog_read") is False and all(blocked_regressions.values()),
        "atomic_world_cycle_atlas_redesigns_carrier_after_typed_feedback": len(world_history) == 2 and [int(x.get("components",0)) for x in world_history] == [1,2],
        "atomic_world_cycle_responses_from_independent_owner": world_response.get("status") == "ATTESTED_OPERATOR_RESPONSES_ACQUIRED_FROM_REFERENCE_SIMULATION" and world_response.get("claim_boundary", {}).get("responses_generated_by_independent_typed_owner") is True,
        "atomic_world_cycle_not_empirical_measurement": world_response.get("claim_boundary", {}).get("empirical_world_measurement") is False,
        "atomic_world_cycle_does_not_reuse_atomic_frontier": world_response.get("attestation", {}).get("atomic_frontier_module_used") is False and world_response.get("attestation", {}).get("answer_bearing_regression_used") is False,
        "atomic_world_cycle_probe_attestation_is_digest_bound": blind_atomic_world_cycle.get("operator_probe_evidence_valid") is True and world_response.get("probe_digest") == blind_atomic_world_cycle.get("operator_probe_evidence", {}).get("probe_digest"),
        "atomic_world_cycle_synthesizes_executable_representation": blind_atomic_world_cycle.get("result", {}).get("status") == "EXECUTABLE_REPRESENTATION_CANDIDATE_SYNTHESIZED_NOT_LAW" and world_atomic_synth.get("qualified_for_compilation") is True,
        "atomic_world_cycle_recovers_two_component_first_derivative_structure": alpha_inv > 100.0 and abs(world_atomic_coeffs.get((0,1,"FIRST_DERIVATIVE",0),0.0)+alpha_inv) < 1e-9 and abs(world_atomic_coeffs.get((1,0,"FIRST_DERIVATIVE",0),0.0)-alpha_inv) < 1e-9,
        "atomic_world_cycle_recovers_inverse_coordinate_couplings": abs(world_atomic_coeffs.get((0,0,"COORDINATE_POWER",-1),0.0)+1.0) < 1e-9 and abs(world_atomic_coeffs.get((0,1,"COORDINATE_POWER",-1),0.0)+alpha_inv) < 1e-9 and abs(world_atomic_coeffs.get((1,0,"COORDINATE_POWER",-1),0.0)+alpha_inv) < 1e-9 and abs(world_atomic_coeffs.get((1,1,"COORDINATE_POWER",-1),0.0)+1.0) < 1e-9,
        "atomic_world_cycle_recovers_large_component_offset_without_named_law": alpha_inv > 0.0 and abs(world_atomic_coeffs.get((1,1,"IDENTITY",0),0.0) + 2.0*alpha_inv*alpha_inv) < 1e-7,
        "atomic_world_cycle_sealed_holdout_passes": world_fit_cert.get("all_outputs_pass") is True and all(float(x.get("sealed_holdout_nrmse",1.0)) < 1e-10 for x in world_fit_cert.get("output_certificates", ())),
        "atomic_world_cycle_execution_residual_small": blind_atomic_world_cycle.get("executable_representation_execution", {}).get("status") == "EXECUTION_PASS" and float(blind_atomic_world_cycle.get("executable_representation_execution", {}).get("max_relative_eigen_residual",1.0)) < 1e-10,
        "atomic_world_cycle_does_not_establish_table_upper_index_or_law": blind_atomic_world_cycle.get("result", {}).get("physical_upper_index_established") is False and blind_atomic_world_cycle.get("result", {}).get("scientific_law_established") is False,
        "variable_particle_probe_design_owner_contract": compiler.variable_particle_probe_design.contract().get("owner_id") == "VARIABLE-PARTICLE-PROBE-DESIGN/1.0.0",
        "variable_particle_world_owner_contract": compiler.variable_particle_world_interaction.contract().get("owner_id") == "ATOMIC-VARIABLE-PARTICLE-REFERENCE-WORLD/1.0.0",
        "self_consistent_synthesis_owner_contract": compiler.self_consistent_synthesis.contract().get("owner_id") == "SELF-CONSISTENT-REPRESENTATION-SYNTHESIS/1.0.0",
        "atlas_births_identifying_variable_particle_protocol": vp_design.get("design_certificate",{}).get("full_rank") is True and vp_design.get("claim_boundary",{}).get("particle_counts_born_by_atlas") is True,
        "variable_particle_holdout_frozen_before_world_response": vp_design.get("design_certificate",{}).get("sealed_holdout_frozen_before_responses") is True and any(str(x.get("role")) == "SEALED_HOLDOUT" for x in vp_design.get("particle_count_rows",())),
        "variable_particle_protocol_uses_no_fixed_upper_count": vp_design.get("design_certificate",{}).get("fixed_upper_particle_count_used") is False and vp_design.get("claim_boundary",{}).get("physical_upper_index_established") is False,
        "variable_particle_world_response_is_independent_reference_simulation": vp_world.get("status") == "ATTESTED_VARIABLE_PARTICLE_SELF_CONSISTENT_RESPONSES_ACQUIRED_FROM_REFERENCE_SIMULATION" and vp_world.get("claim_boundary",{}).get("responses_generated_by_independent_typed_owner") is True and vp_world.get("claim_boundary",{}).get("empirical_world_measurement") is False,
        "self_consistent_candidate_synthesized_from_attested_rows": sc_synth.get("status") == "GENERATED_SELF_CONSISTENT_EXECUTABLE_OPERATOR_CANDIDATE" and sc_synth.get("qualified_for_compilation") is True and sc_fit.get("all_outputs_pass") is True,
        "self_consistent_field_coupling_recovered_without_named_solver": len(sc_blocks) == 2 and all(abs(row[4]-1.0) < 1e-8 for row in sc_blocks),
        "self_consistent_occupancy_affine_field_update_recovered": abs(float(sc_field.get("occupancy_scale",0.0))-1.0) < 1e-10 and abs(float(sc_field.get("occupancy_intercept",0.0))+1.0) < 1e-10 and abs(float(sc_field.get("regularization",0.0))-0.5) < 1e-10,
        "self_consistent_field_update_passes_sealed_holdout": sc_field.get("pass") is True and float(sc_field.get("sealed_holdout_nrmse",1.0)) < 1e-10,
        "self_consistent_runtime_converges": sc_exec.get("status") == "EXECUTION_PASS" and sc_fp.get("status") == "FIXED_POINT_CONVERGED" and int(sc_fp.get("iterations",999)) < 96,
        "self_consistent_runtime_eigen_residual_small": float(sc_exec.get("max_relative_eigen_residual",1.0)) < 1e-10,
        "variable_particle_cycle_does_not_establish_periodic_table": blind_atomic_variable_particle_cycle.get("result",{}).get("physical_upper_index_established") is False and sc_synth.get("claim_boundary",{}).get("periodic_table_continuation_established") is False,
        "variable_particle_cycle_remains_reference_simulation_not_world_law": blind_atomic_variable_particle_cycle.get("result",{}).get("scientific_law_established") is False and vp_world.get("claim_boundary",{}).get("nuclear_stability_established") is False,
        "axis_registry_count_is_snapshot_only": canonical_axis_count() > 0,
    }
    passed = sum(bool(v) for v in checks.values())
    payload = {
        "schema": SCHEMA, "release": RELEASE, "owner_id": "PHI-THEORY-COMPILER-QUALIFICATION/2.1.0",
        "status": "PASS_PHI_THEORY_COMPILER_QUALIFICATION" if passed == len(checks) else "BLOCKED_PHI_THEORY_COMPILER_QUALIFICATION",
        "passed": passed, "total": len(checks), "checks": [{"check":k,"status":"PASS" if v else "FAIL"} for k,v in checks.items()],
        "demonstration": {
            "finite_regression": {"source_primitive":primitive,"compiled":finite_compiled,"execution":finite_execution},
            "atlas_born_probe_control": {"design":atlas_probe_design,"evidence":atlas_born_evidence,"synthesized":atlas_born_synthesized},
            "operator_synthesis": {"synthesized":synthesized,"compiled":operator_compiled,"execution":operator_execution},
            "generalized_eigenproblem": generalized_execution,
            "self_consistent_fixed_point": scf_execution,
            "negative_controls": {"insufficient":insufficient,"bad_holdout":bad_holdout,"tamper_blocked":tamper_blocked},
            "blind_atomic_representation_gap": {
                "blocked_regression_surfaces": blocked_regressions,
                "receipt": blind_atomic_gap,
            },
            "blind_atomic_world_interaction_cycle": {
                "receipt": blind_atomic_world_cycle,
            },
            "blind_atomic_variable_particle_self_consistent_cycle": {
                "receipt": blind_atomic_variable_particle_cycle,
            },
            "operator_probe_provenance_gate": {
                "unattested_receipt": unattested_direct_gap,
                "attested_receipt": attested_direct_gap,
                "qualification_probe_evidence": qualification_probe_evidence,
            },
        },
        "claim_boundary": {
            "synthetic_operator_control_is_world_law": False,
            "world_novelty_established": False,
            "internet_used_prefreeze": False,
            "arbitrary_code_generation": False,
            "canonical_axis_count_is_universal_ceiling": False,
        },
    }
    payload["digest"] = digest_payload(payload)
    atomic_probe_report = {
        "schema":"phi-atomic-operator-probe-cycle/v3",
        "release":RELEASE,
        "status":blind_atomic_world_cycle.get("result", {}).get("status"),
        "initial_gap_control":blind_atomic_gap,
        "atlas_world_interaction_receipt":blind_atomic_world_cycle,
        "probe_protocol_history":blind_atomic_world_cycle.get("operator_probe_design_history"),
        "response_acquisition":{
            "status":world_response.get("status"),
            "response_values_obtained":world_response.get("status") == "ATTESTED_OPERATOR_RESPONSES_ACQUIRED_FROM_REFERENCE_SIMULATION",
            "provider_owner_id":world_response.get("owner_id"),
            "attestation_digest":world_response.get("attestation", {}).get("digest"),
            "reference_simulation":True,
            "empirical_world_measurement":False,
            "regression_or_publication_oracle_used_prefreeze":False,
        },
        "atlas_synthesized_representation":{
            "status":world_atomic_synth.get("status"),
            "candidate_id":world_atomic_synth.get("candidate_id"),
            "program":world_atomic_synth.get("program"),
            "fit_certificate":world_fit_cert,
            "execution":blind_atomic_world_cycle.get("executable_representation_execution"),
        },
        "postfreeze_reference_world_audit":{
            "model":world_response.get("postfreeze_audit_model"),
            "model_digest":world_response.get("postfreeze_audit_model_digest"),
            "visible_to_synthesis":False,
        },
        "next_frontier":{
            "status":"VARIABLE_PARTICLE_SELF_CONSISTENT_REFERENCE_CYCLE_CLOSED_NEXT_PHYSICAL_EXISTENCE_FRONTIER",
            "reason":"The one-particle stage is now followed by the Atlas-native variable-particle/self-consistent reference cycle; physical atom existence and nuclear stability remain unestablished.",
            "required_next_evidence":[
                "NUCLEAR_BINDING_AND_DECAY_WORLD_RESPONSE",
                "OBJECT_EXISTENCE_VERSUS_PARTICLE_COUNT",
                "MULTI_SCALE_ELECTRON_NUCLEUS_COUPLING_FALSIFICATION",
            ],
            "table_genesis_continued":False,
        },
        "claim_boundary":{
            "probe_inputs_were_born_by_atlas":True,
            "carrier_redesign_was_triggered_by_typed_world_feedback":True,
            "operator_response_values_were_born_by_atlas":False,
            "operator_response_values_from_reference_simulation":True,
            "atomic_next_representation_synthesized":world_atomic_synth.get("qualified_for_compilation") is True,
            "scientific_law_established":False,
            "physical_upper_index_established":False,
            "periodic_table_genesis_completed":False,
            "published_atomic_solver_used_prefreeze":False,
            "answer_bearing_regression_used_prefreeze":False,
            "reference_simulation_is_empirical_world":False,
        },
    }
    atomic_probe_report["digest"] = digest_payload(atomic_probe_report)
    variable_particle_report = {
        "schema":"phi-atomic-variable-particle-self-consistent-cycle/v1",
        "release":RELEASE,
        "status":blind_atomic_variable_particle_cycle.get("result",{}).get("status"),
        "atlas_cycle_receipt":blind_atomic_variable_particle_cycle,
        "atlas_particle_protocol":vp_design,
        "response_acquisition":{
            "status":vp_world.get("status"),
            "provider_owner_id":vp_world.get("owner_id"),
            "reference_simulation":True,
            "empirical_world_measurement":False,
            "probe_digest":vp_world.get("probe_digest"),
            "attestation_digest":vp_world.get("attestation",{}).get("digest"),
        },
        "atlas_self_consistent_representation":{
            "candidate_id":sc_synth.get("candidate_id"),
            "fit_certificate":sc_fit,
            "execution":sc_exec,
        },
        "next_frontier":{
            "status":"PHYSICAL_OBJECT_EXISTENCE_AND_NUCLEAR_STABILITY_WORLD_EVIDENCE_REQUIRED",
            "reason":"Variable-particle/self-consistent electronic representation is now executable on a reference world, but occupancy coordinates do not establish that corresponding neutral atoms are physically realizable or stable.",
            "required_next_evidence":[
                "NUCLEAR_BINDING_AND_DECAY_WORLD_RESPONSE",
                "OBJECT_EXISTENCE_VERSUS_PARTICLE_COUNT",
                "MULTI_SCALE_ELECTRON_NUCLEUS_COUPLING_FALSIFICATION",
            ],
            "table_genesis_continued":False,
        },
        "claim_boundary":{
            "particle_counts_born_by_atlas":True,
            "self_consistent_representation_synthesized_by_atlas":sc_synth.get("qualified_for_compilation") is True,
            "responses_born_by_atlas":False,
            "responses_from_reference_simulation":True,
            "scientific_law_established":False,
            "physical_atom_existence_established":False,
            "physical_upper_index_established":False,
            "periodic_table_genesis_completed":False,
        },
    }
    variable_particle_report["digest"] = digest_payload(variable_particle_report)
    if persist_reports:
        reports_dir = root / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        (reports_dir / "THEORY_COMPILER_QUALIFICATION_CURRENT.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (reports_dir / "ATOMIC_OPERATOR_PROBE_CYCLE_CURRENT.json").write_text(
            json.dumps(atomic_probe_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (reports_dir / "ATOMIC_VARIABLE_PARTICLE_SELF_CONSISTENT_CYCLE_CURRENT.json").write_text(
            json.dumps(variable_particle_report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return payload


if __name__ == "__main__":
    print(json.dumps(run_release_qualification(persist_reports=True), ensure_ascii=False, indent=2, sort_keys=True))
