"""Qualification for Φ-Mathematical Invention Kernel 1.0.0."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from source.lawspace.schema import digest_payload
from source.lawspace.mathematical_invention import MathematicalInventionKernel
from source.lawspace.domains import canonical_axis_count

SCHEMA="phi-mathematical-invention-qualification/v1"; RELEASE="15.10.2"


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
    checks={
      "kernel_owner_contract":kernel.contract()["owner_id"]=="PHI-MATHEMATICAL-INVENTION-KERNEL/1.0.0",
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
      "canonical_axis_count_unchanged":canonical_axis_count()==unknown["phi_scan"]["registered_axis_count"],
      "mechanism_qualification_not_world_discovery":all(x is False for x in (unknown["claim_boundary"]["world_novelty_established"],primitive["claim_boundary"]["world_mathematical_novelty_established"],morph["claim_boundary"]["world_novelty_established"])),
    }
    passed=sum(bool(v) for v in checks.values())
    payload={
      "schema":SCHEMA,"release":RELEASE,"owner_id":"PHI-MATHEMATICAL-INVENTION-QUALIFICATION/1.0.0",
      "status":"PASS_PHI_MATHEMATICAL_INVENTION_QUALIFICATION" if passed==len(checks) else "BLOCKED_PHI_MATHEMATICAL_INVENTION_QUALIFICATION",
      "passed":passed,"total":len(checks),"checks":[{"check":k,"status":"PASS" if v else "FAIL"} for k,v in checks.items()],
      "demonstration":{"unknown_unknown":unknown,"primitive":primitive,"morphism":morph,"controlled_limit":limit,"negative_controls":{"weak_unknown":weak,"incomplete_primitive":incomplete,"morphism":morph_bad,"limit":no_limit}},
      "claim_boundary":{"synthetic_qualification_is_new_mathematics":False,"world_novelty_established":False,"internet_used_prefreeze":False,"known_method_catalog_used_as_answer":False,"canonical_axis_count":canonical_axis_count()},
    }
    payload["digest"]=digest_payload(payload); return payload

if __name__=="__main__":
    print(json.dumps(run_release_qualification(),ensure_ascii=False,indent=2,sort_keys=True))
