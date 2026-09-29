from __future__ import annotations

import pytest

from source.lawspace.research_cycle import SemanticTypedQuestionOwner
from source.lawspace.runtime import LawSpaceRuntime


@pytest.fixture(scope="module")
def router() -> SemanticTypedQuestionOwner:
    return SemanticTypedQuestionOwner(LawSpaceRuntime("."))


def test_abstract_functional_equation_routes_to_mathematics_only(router):
    result = router.interpret(
        "Determine whether there exists a continuous function f:R->R such that "
        "f(f(x))=x^2+1 for every real x."
    )

    assert result["required_domains"] == ["mathematics"]
    assert result["domain_routing_status"] == "GROUNDED"
    assert {"existence", "topological"} <= set(result["semantic_signal_concepts"])
    assert {"a", "r", "x", "f", "1", "2"}.isdisjoint(result["semantic_signal_concepts"])


def test_navier_stokes_regularity_routes_to_physics_without_prose_contamination(router):
    result = router.interpret(
        "Determine whether smooth finite-energy solutions of the three-dimensional "
        "incompressible Navier-Stokes equations remain globally regular or develop singularities."
    )

    assert result["required_domains"] == ["physics"]
    assert "aeronautics_and_aerostation" not in result["required_domains"]
    assert "chemistry" not in result["required_domains"]


def test_cross_domain_evidence_can_ground_biology_and_chemistry(router):
    result = router.interpret(
        "A mutation changes an enzyme reaction rate under two temperatures."
    )

    assert result["required_domains"] == ["biology", "chemistry"]
    assert "aeronautics_and_aerostation" not in result["required_domains"]


def test_untyped_unknown_process_returns_void_instead_of_guessing_domain(router):
    result = router.interpret("An unknown process with no known domain.")

    assert result["required_domains"] == []
    assert result["target_axis_ids"] == []
    assert result["domain_routing_status"] == "VOID_UNGROUNDED"
    assert result["status"] == "SEMANTIC_TYPED_IR_VOID"
    assert result["grounding_contract"]["owner_text_can_select_domain_without_registry_anchor"] is False
