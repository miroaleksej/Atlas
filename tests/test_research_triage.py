from source.lawspace.research_triage import ResearchTriageSandbox


def test_quality_tiers_and_information_density():
    t=ResearchTriageSandbox()
    s=t.assess_data_quality(n_points=1500,relative_uncertainty=.005)
    e=t.assess_data_quality(n_points=100,relative_uncertainty=.05)
    x=t.assess_data_quality(n_points=20,relative_uncertainty=.01)
    assert s["quality_tag"]=="STRICT" and s["rho_star"]==.05 and s["sigma_star"]==.05
    assert e["quality_tag"]=="EMPIRICAL" and e["rho_star"]==.15 and e["sigma_star"]==.10
    assert x["quality_tag"]=="EXPLORATORY" and x["sigma_star"] is None
    assert 0 <= e["information_density"] <= 1


def test_dpi_is_rank_only_and_weighted():
    t=ResearchTriageSandbox()
    r=t.score_hypothesis({"candidate_id":"A","rho_adj":.05,"simplicity_score":1,"cross_consistency":1,"familywise_p":.001})
    assert 0<=r["dpi"]<=1 and r["dpi_can_promote_scientific_status"] is False


def test_expert_sponsor_cannot_pass_u6():
    t=ResearchTriageSandbox(); state={"schema":"phi-hypothesis-council/v1","actions":[],"sandbox_weights":None,"revision":0}
    out=t.record_council_action(state=state,candidate_id="A",action="SPONSOR_REVIEW",reason="expert intuition")
    a=out["actions"][-1]
    assert a["authoritative_u_gate_override"] is False
    assert a["effect"]=="RETURN_TO_EVIDENCE_ACQUISITION_NOT_U6_PASS"


def test_dimension_exception_is_sandbox_only():
    t=ResearchTriageSandbox(); state={"schema":"phi-hypothesis-council/v1","actions":[],"sandbox_weights":None,"revision":0}
    out=t.record_council_action(state=state,candidate_id="A",action="REQUEST_SANDBOX_DIMENSION_EXCEPTION",reason="unit classification disputed")
    assert out["actions"][-1]["effect"]=="SANDBOX_ONLY_U2_REMAINS_CLOSED"


def test_what_if_identifies_uncovered_ranges():
    t=ResearchTriageSandbox()
    r=t.propose_what_if_experiments(axis_summaries=[{"axis_id":"x","observed_min":0,"observed_max":1,"target_min":-1,"target_max":2,"sensitivity":1}],count=2)
    assert len(r["experiments"])==2
