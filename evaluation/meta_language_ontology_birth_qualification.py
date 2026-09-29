"""Qualification for autonomous meta-language / ontology birth.

This verifies bounded constructor-program birth above the research-local
representation-definition layer.  The result is mechanism qualification only:
it does not establish AGI, unrestricted ontology birth, world novelty, theorem
truth, or canonical registry mutation.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

from source.lawspace.api import LawSpaceAPI
from source.lawspace.knowledge_evolution import UniversalProofMechanismMemoryOwner
from source.lawspace.mathematical_invention import MathematicalInventionKernel
from source.lawspace.schema import digest_payload

OWNER_ID = "ATLAS-AUTONOMOUS-META-LANGUAGE-ONTOLOGY-BIRTH-QUALIFICATION/1.0.0"


def _rows_three_field() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for case in range(8):
        label = "A" if case % 2 == 0 else "B"
        triples = (
            [(0, 0, 0), (0, 1, 1), (1, 0, 1), (1, 1, 0)]
            if label == "A"
            else [(0, 0, 1), (0, 1, 0), (1, 0, 0), (1, 1, 1)]
        )
        for a, b, c in triples:
            rows.append({"case": f"case_{case}", "u": f"u{a}", "v": f"v{b}", "w": f"w{c}", "label": label})
    return rows


def _rows_four_field() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for case in range(10):
        label = "A" if case % 2 == 0 else "B"
        wanted = 0 if label == "A" else 1
        for a in (0, 1):
            for b in (0, 1):
                for c in (0, 1):
                    d = a ^ b ^ c ^ wanted
                    rows.append({
                        "case": f"z{case}",
                        "p": f"p{a}",
                        "q": f"q{b}",
                        "r": f"r{c}",
                        "s": f"s{d}",
                        "label": label,
                    })
    return rows


def _rows_negative() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    triples = [(0, 0, 0), (0, 1, 1), (1, 0, 1), (1, 1, 0)]
    for case in range(8):
        label = "A" if case % 2 == 0 else "B"
        for a, b, c in triples:
            rows.append({"case": f"n{case}", "u": f"u{a}", "v": f"v{b}", "w": f"w{c}", "label": label})
    return rows


def _failure(kernel: MathematicalInventionKernel, problem: str, rows: list[dict[str, str]]) -> Mapping[str, Any]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["case"]].append(row)
    residual_rows: list[dict[str, Any]] = []
    for group, group_rows in grouped.items():
        residual_rows.extend([
            {"environment_id": group, "mode": "residual", "residual": 1.0, "label": group_rows[0]["label"]},
            {"environment_id": group, "mode": "latent", "residual": 1.0, "label": group_rows[0]["label"]},
        ])
    return kernel.representation_failure_detector.detect(
        frozen_problem=problem,
        revision_history=[{"goal_closure_gain": 0.0, "attempt": index} for index in range(3)],
        residual_rows=residual_rows,
    )


def _run_case(kernel: MathematicalInventionKernel, problem: str, rows: list[dict[str, str]]) -> tuple[Mapping[str, Any], Mapping[str, Any] | None, Mapping[str, Any], Mapping[str, Any] | None]:
    failure = _failure(kernel, problem, rows)
    prior_birth = kernel.representation_language_birth.synthesize(
        failure_receipt=failure,
        frozen_problem=problem,
        evidence_rows=rows,
        target_field="label",
        group_field="case",
    )
    prior_validation = (
        kernel.representation_language_birth.validate(birth_receipt=prior_birth, evidence_rows=rows)
        if prior_birth.get("status") == "GENERATED_REPRESENTATION_CLASS_PROPOSED"
        else None
    )
    birth = kernel.meta_language_ontology_birth.synthesize(
        failure_receipt=failure,
        prior_language_validation=prior_validation,
        frozen_problem=problem,
        evidence_rows=rows,
        target_field="label",
        group_field="case",
    )
    validation = (
        kernel.meta_language_ontology_birth.validate(
            birth_receipt=birth,
            evidence_rows=rows,
            prior_max_constructor_arity=2,
        )
        if birth.get("status") == "META_LANGUAGE_CONSTRUCTOR_PORTFOLIO_BORN"
        else None
    )
    return failure, prior_validation, birth, validation


def run_release_qualification(root: str | Path | None = None) -> Mapping[str, Any]:
    root = Path(root or Path(__file__).resolve().parents[1])
    kernel = MathematicalInventionKernel(root)
    problem_three = "Frozen opaque three-field grouped classification with all lower-order projections stalled."
    problem_four = "Frozen opaque four-field grouped classification with all lower-order projections stalled."
    failure_three, prior_three, birth_three, validation_three = _run_case(kernel, problem_three, _rows_three_field())
    _, _, _, validation_four = _run_case(kernel, problem_four, _rows_four_field())
    _, _, _, validation_negative = _run_case(kernel, "Frozen no-signal grouped classification.", _rows_negative())
    api_result = LawSpaceAPI(root).birth_phi_meta_language_ontology(
        failure_receipt=failure_three,
        prior_language_validation=prior_three,
        frozen_problem=problem_three,
        evidence_rows=_rows_three_field(),
        target_field="label",
        group_field="case",
        prior_max_constructor_arity=2,
    )
    memory_ids = {str(row.get("mechanism_id")) for row in UniversalProofMechanismMemoryOwner().canonical_seed()}
    selected_three = (validation_three or {}).get("selected_constructor_program") or {}
    selected_four = (validation_four or {}).get("selected_constructor_program") or {}
    checks = {
        "kernel_version_is_1_6": kernel.contract().get("owner_id") == "PHI-MATHEMATICAL-INVENTION-KERNEL/1.6.0",
        "meta_language_component_is_registered": kernel.contract().get("components", {}).get("autonomous_meta_language_ontology_birth") == "AUTONOMOUS-META-LANGUAGE-ONTOLOGY-BIRTH/1.0.0-COMPONENT",
        "prior_language_still_fails_three_field_case": (prior_three or {}).get("accepted") is False,
        "constructor_portfolio_uses_no_named_representation_catalog": birth_three.get("claim_boundary", {}).get("named_representation_selected") is False,
        "three_field_case_births_minimum_arity_three": (validation_three or {}).get("accepted") is True and selected_three.get("constructor_arity") == 3,
        "three_field_case_improves_untouched_holdout": float((validation_three or {}).get("goal_closure_gain", 0.0)) > 0.0 and float((validation_three or {}).get("born_ontology_holdout_accuracy", 0.0)) >= 0.75,
        "four_field_unseen_case_births_arity_four": (validation_four or {}).get("accepted") is True and selected_four.get("constructor_arity") == 4,
        "four_field_case_improves_untouched_holdout": float((validation_four or {}).get("goal_closure_gain", 0.0)) > 0.0 and float((validation_four or {}).get("born_ontology_holdout_accuracy", 0.0)) >= 0.75,
        "negative_no_signal_control_is_rejected": (validation_negative or {}).get("accepted") is False and float((validation_negative or {}).get("goal_closure_gain", 0.0)) <= 0.0,
        "born_ontology_is_research_local_and_noncanonical": (validation_three or {}).get("ontology_object", {}).get("research_local") is True and (validation_three or {}).get("ontology_object", {}).get("canonical") is False,
        "common_memory_contains_meta_language_mechanisms": {"PM-META-CONSTRUCTOR-BIRTH", "PM-ONTOLOGY-HOLDOUT-GATE", "PM-ONTOLOGY-NONCANONICAL"} <= memory_ids,
        "read_only_api_exposes_birth_and_validation": isinstance(api_result.get("birth"), Mapping) and isinstance(api_result.get("validation"), Mapping) and api_result["validation"].get("accepted") is True,
        "claim_boundary_denies_agi_proof": kernel.meta_language_ontology_birth.contract().get("claim_boundary", {}).get("program_synthesis_is_free_general_intelligence") is False,
    }
    payload: dict[str, Any] = {
        "schema": "phi-autonomous-meta-language-ontology-birth-qualification/v1",
        "owner_id": OWNER_ID,
        "status": "PASS_AUTONOMOUS_META_LANGUAGE_ONTOLOGY_BIRTH" if all(checks.values()) else "FAIL_AUTONOMOUS_META_LANGUAGE_ONTOLOGY_BIRTH",
        "passed": sum(bool(value) for value in checks.values()),
        "total": len(checks),
        "checks": checks,
        "three_field": {"failure": failure_three, "prior_validation": prior_three, "birth": birth_three, "validation": validation_three},
        "four_field": {"validation": validation_four},
        "negative": {"validation": validation_negative},
        "claim_boundary": {
            "qualification_proves_unrestricted_free_ontology_birth": False,
            "qualification_proves_agi": False,
            "qualification_proves_world_novelty": False,
        },
    }
    payload["digest"] = digest_payload(payload)
    return payload


if __name__ == "__main__":
    result = run_release_qualification()
    print(
        "autonomous_meta_language_ontology_birth:",
        result["status"],
        f"{result['passed']}/{result['total']}",
        "digest=" + result["digest"],
    )
    for name, passed in result["checks"].items():
        if not passed:
            print("FAIL", name)
    raise SystemExit(0 if result["status"].startswith("PASS") else 1)
