from source.lawspace.mathematical_invention import MathematicalInventionKernel
from source.lawspace.research_cycle import ScientificResearchCycleOwner
from source.lawspace.runtime import LawSpaceRuntime


def _relational_rows():
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


def test_representation_language_birth_validates_research_local_class():
    kernel = MathematicalInventionKernel(".")
    rows = _relational_rows()
    failure = kernel.representation_failure_detector.detect(
        frozen_problem="classify frozen relation outcomes",
        revision_history=[
            {"revision_kind": "ADAPTIVE_CONTEXT_AXIS", "goal_closure_gain": 0.0},
            {"revision_kind": "BINDING_REFINEMENT", "goal_closure_gain": 0.0},
        ],
        residual_rows=rows,
    )
    birth = kernel.representation_language_birth.synthesize(
        failure_receipt=failure,
        frozen_problem="classify frozen relation outcomes",
        evidence_rows=rows,
        target_field="label",
        group_field="trial",
    )
    validation = kernel.representation_language_birth.validate(birth_receipt=birth, evidence_rows=rows)

    representation_class = birth["representation_class"]
    assert failure["status"] == "REPRESENTATION_CLASS_INADEQUACY_HYPOTHESIS"
    assert representation_class["representation_class_id"].startswith("BORN-R-")
    assert representation_class["canonical"] is False
    assert representation_class["research_local"] is True
    assert representation_class["definition"]["relations"][0]["argument_fields"] == ["dst", "src"]
    assert validation["status"] == "REPRESENTATION_CLASS_BIRTH_VALIDATED_RESEARCH_LOCAL"
    assert validation["goal_closure_gain"] > 0.0
    assert validation["accepted"] is True


def test_representation_language_birth_blocks_without_stalled_history():
    kernel = MathematicalInventionKernel(".")
    rows = _relational_rows()
    failure = kernel.representation_failure_detector.detect(
        frozen_problem="single revision is not enough",
        revision_history=[{"revision_kind": "ADAPTIVE_CONTEXT_AXIS", "goal_closure_gain": 0.0}],
        residual_rows=rows,
    )
    birth = kernel.representation_language_birth.synthesize(
        failure_receipt=failure,
        frozen_problem="single revision is not enough",
        evidence_rows=rows,
        target_field="label",
        group_field="trial",
    )

    assert failure["status"] == "REPRESENTATION_CLASS_FAILURE_NOT_ESTABLISHED"
    assert birth["status"] == "REPRESENTATION_LANGUAGE_BIRTH_BLOCKED_NO_CLASS_FAILURE"


def test_autonomous_research_can_report_research_local_representation_class(tmp_path, monkeypatch):
    monkeypatch.setenv("PHI_STATE_DIR", str(tmp_path / "state"))
    runtime = LawSpaceRuntime(".")
    owner = ScientificResearchCycleOwner(runtime)
    receipt = owner.run_autonomous({
        "question": "Classify outcomes from repeated frozen relation residuals",
        "required_domains": [],
        "target_axis_ids": [],
        "required_observables": [],
        "commit_resident_state": False,
        "representation_revision_history": [
            {"revision_kind": "ADAPTIVE_CONTEXT_AXIS", "goal_closure_gain": 0.0},
            {"revision_kind": "BINDING_REFINEMENT", "goal_closure_gain": 0.0},
        ],
        "representation_evidence_rows": _relational_rows(),
        "representation_target_field": "label",
        "representation_group_field": "trial",
    })

    assert receipt["representation_language_validation"]["accepted"] is True
    assert receipt["representation_language_birth"]["representation_class"]["canonical"] is False
    assert receipt["claim_boundary"]["research_local_representation_class_is_canonical"] is False
