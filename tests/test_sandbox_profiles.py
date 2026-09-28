from source.lawspace.research_triage import ResearchTriageSandbox, SANDBOX_PROFILES


def _hypotheses(n):
    return [
        {
            "candidate_id": f"C{i}",
            "rho_adj": 0.1,
            "simplicity_score": 0.9,
            "cross_consistency": 0.9,
            "familywise_p": 0.001,
            "familywise_alpha": 0.05,
        }
        for i in range(n)
    ]


def test_profiles_are_sandbox_only_and_do_not_modify_promotion():
    assert set(SANDBOX_PROFILES) == {"STRICT", "RESEARCH", "WIDE"}
    out = ResearchTriageSandbox.rank_hypotheses_profiled(_hypotheses(3), profile="RESEARCH")
    assert out["sandbox_only"] is True
    assert out["affects_scientific_promotion"] is False
    assert out["strict_u_gates_modified"] is False
    assert out["sandbox_competition_sufficient"] is True


def test_min_competitors_is_real_routing_gate_not_metadata_only():
    out = ResearchTriageSandbox.rank_hypotheses_profiled(_hypotheses(2), profile="RESEARCH")
    assert out["sandbox_competition_sufficient"] is False
    assert out["profile_promising_for_further_evidence_count"] == 0
