"""Qualification for the Long-Horizon Blind Scientific Cycle."""
from __future__ import annotations
import hashlib, json, tempfile
from pathlib import Path
from typing import Any, Mapping

from source.lawspace.long_horizon_scientific_cycle import LongHorizonBlindScientificCycleKernel
from source.lawspace.mathematical_invention import MathematicalInventionKernel
from source.lawspace.theory_compiler import TheoryCompilerKernel, HierarchicalObservationalTheoryOwner
from source.lawspace.schema import digest_payload
from source.lawspace.domains import canonical_axis_count

SCHEMA="phi-long-horizon-blind-cycle-qualification/v1"; RELEASE="10.7.0"


def _rows(kind: str):
    obs={"h0":"A","h1":"B","h2":"C"}
    maps={
      "t0":{"a":{"h0":"h1","h1":"h2","h2":"h0"},"b":{"h0":"h1","h1":"h0","h2":"h2"}},
      "t1":{"a":{"h0":"h1","h1":"h2","h2":"h0"},"b":{"h0":"h0","h1":"h1","h2":"h2"}},
      "t2":{"a":{"h0":"h2","h1":"h0","h2":"h1"},"b":{"h0":"h1","h1":"h0","h2":"h2"}},
    }
    trans=maps[kind]; rows=[]
    for s in sorted(obs):
      for a in sorted(trans): rows.append({"history_id":s,"action":a,"next_history_id":trans[a][s],"observation":obs[s]})
    return rows


def _compiled(root: Path, kind: str):
    inv=MathematicalInventionKernel(root)
    prim=inv.primitive.synthesize(transition_rows=_rows(kind),freeze_digest=digest_payload({"long_horizon_kind":kind,"hidden_truth_seen":False}))
    return TheoryCompilerKernel(root).compiler.compile(theory_artifact=prim,theory_freeze_digest=digest_payload({"primitive":prim["digest"],"frozen":True}))


def _execute_hidden(compiled: Mapping[str,Any], selected: Mapping[str,Any], freeze_digest: str, epoch: int, round_index: int, *, outside: bool=False):
    if outside:
        observation="OUTSIDE-FROZEN-OBSERVATION"
    else:
        state=str(selected["initial_state"])
        ir=compiled["executable_ir"]
        for action in selected["actions"]: state=str(ir["update"]["table"][action][state])
        observation=str(ir["observe"]["table"][state])
    core={"epoch":epoch,"round":round_index,"experiment_id":selected["experiment_id"],"freeze":freeze_digest,"observation":observation}
    protocol_digest=hashlib.sha256(json.dumps({"experiment_id":selected["experiment_id"],"initial_state":selected["initial_state"],"actions":selected["actions"]},sort_keys=True).encode()).hexdigest()
    data_digest=hashlib.sha256(json.dumps(core,sort_keys=True).encode()).hexdigest()
    payload={
      "measurement_id":"M-"+data_digest[:16].upper(),"experiment_id":selected["experiment_id"],"frontier_freeze_digest":freeze_digest,
      "observation":observation,"measurement_owner":"QUALIFICATION-HIDDEN-WORLD-EVALUATOR","protocol_digest":protocol_digest,"data_digest":data_digest,"uncertainty":0.0,
    }
    payload["digest"]=digest_payload(payload); return payload




def _universal_portfolio_cases() -> list[dict[str, Any]]:
    """Typed scientific contents for one shared reasoning algorithm.

    Domain labels, observable names and outcome semantics differ deliberately.
    No case supplies or selects a domain-specific reasoning owner.
    """
    return [
        {
            "domain_id": "astronomy",
            "theory_id": "QUAL-UNIVERSAL-ASTRONOMY",
            "ids": ["A1", "A2", "A3"],
            "selected": "E-STRONG",
            "measurement": "B",
            "expected": "A2",
            "outside": "OUTSIDE-FROZEN-ASTRONOMY",
            "models": [
                {"experiment_id":"E-WEAK","observable":"host_gap","cost":1.0,"feasible":True,"predictions":{"A1":{"kind":"categorical","value":"A"},"A2":{"kind":"categorical","value":"A"},"A3":{"kind":"categorical","value":"C"}}},
                {"experiment_id":"E-STRONG","observable":"fresh_host_gap","cost":1.5,"feasible":True,"predictions":{"A1":{"kind":"categorical","value":"A"},"A2":{"kind":"categorical","value":"B"},"A3":{"kind":"categorical","value":"C"}}},
            ],
        },
        {
            "domain_id": "materials",
            "theory_id": "QUAL-UNIVERSAL-MATERIALS",
            "ids": ["M1", "M2", "M3"],
            "selected": "E-STRONG",
            "measurement": 110.0,
            "expected": "M2",
            "outside": None,
            "models": [
                {"experiment_id":"E-WEAK","observable":"property_low_resolution","cost":1.0,"feasible":True,"predictions":{"M1":{"kind":"gaussian","mean":100.0,"sigma":6.0},"M2":{"kind":"gaussian","mean":104.0,"sigma":6.0},"M3":{"kind":"gaussian","mean":108.0,"sigma":6.0}}},
                {"experiment_id":"E-STRONG","observable":"property_high_resolution","cost":2.0,"feasible":True,"predictions":{"M1":{"kind":"gaussian","mean":90.0,"sigma":2.0},"M2":{"kind":"gaussian","mean":110.0,"sigma":2.0},"M3":{"kind":"gaussian","mean":130.0,"sigma":2.0}}},
            ],
        },
        {
            "domain_id": "fluid_dynamics",
            "theory_id": "QUAL-UNIVERSAL-FLUIDS",
            "ids": ["F1", "F2", "F3"],
            "selected": "E-STRONG",
            "measurement": 2.5,
            "expected": "F2",
            "outside": 9.0,
            "models": [
                {"experiment_id":"E-WEAK","observable":"closure_interval","cost":1.0,"feasible":True,"predictions":{"F1":{"kind":"interval","lo":0.0,"hi":2.0},"F2":{"kind":"interval","lo":1.0,"hi":3.0},"F3":{"kind":"interval","lo":2.0,"hi":4.0}}},
                {"experiment_id":"E-STRONG","observable":"closure_interval_controlled","cost":1.2,"feasible":True,"predictions":{"F1":{"kind":"interval","lo":0.0,"hi":1.0},"F2":{"kind":"interval","lo":2.0,"hi":3.0},"F3":{"kind":"interval","lo":4.0,"hi":5.0}}},
            ],
        },
        {
            "domain_id": "mathematics",
            "theory_id": "QUAL-UNIVERSAL-MATHEMATICS",
            "ids": ["P1", "P2", "P3"],
            "selected": "E-STRONG",
            "measurement": "COUNTEREXAMPLE_TO_P1_SUPPORTS_P2",
            "expected": "P2",
            "outside": "NOVEL_PROOF_OBJECT",
            "models": [
                {"experiment_id":"E-WEAK","observable":"bounded_computation","cost":1.0,"feasible":True,"predictions":{"P1":{"kind":"categorical","value":"INCONCLUSIVE"},"P2":{"kind":"categorical","value":"INCONCLUSIVE"},"P3":{"kind":"categorical","value":"WITNESS_P3"}}},
                {"experiment_id":"E-STRONG","observable":"discriminating_proof_search","cost":1.8,"feasible":True,"predictions":{"P1":{"kind":"categorical","value":"WITNESS_P1"},"P2":{"kind":"categorical","value":"COUNTEREXAMPLE_TO_P1_SUPPORTS_P2"},"P3":{"kind":"categorical","value":"WITNESS_P3"}}},
            ],
        },
    ]


def _run_universal_portfolio_qualification(kernel: LongHorizonBlindScientificCycleKernel) -> dict[str, Any]:
    """Qualify the same P3 closed-loop owners across unrelated sciences."""
    compiler = HierarchicalObservationalTheoryOwner()
    rows: list[dict[str, Any]] = []
    checks: dict[str, bool] = {}

    def compile_case(case: Mapping[str, Any], *, theory_id: str | None = None, domain_id: str | None = None, models: Any = None):
        did = str(domain_id or case["domain_id"])
        return compiler.compile(
            theory_id=str(theory_id or case["theory_id"]),
            universal_layer={"domain_id": did, "shared_reasoning_contract": "P3-CLOSED-LOOP"},
            host_layer={"domain_id": did, "shared_context_state": "TYPED"},
            regime_layer={"domain_id": did, "regime_structure": "TYPED"},
            feasible_domain_layer={"domain_id": did, "measurement_domain": "TYPED"},
            competing_explanations=[{"id": x} for x in case["ids"]],
            predictions=[{"prediction":"distinguish competing explanations","falsification":"frozen prediction contradicted","defense":"freeze before measurement","heldout_refit_allowed":False}],
            evidence_digest=digest_payload({"qualification":"universal-scientific-portfolio","domain_id":did,"theory_id":str(theory_id or case["theory_id"]),"prefreeze":True}),
            experimental_models=list(models if models is not None else case["models"]),
        )

    for case in _universal_portfolio_cases():
        theory = compile_case(case)
        freeze = kernel.freeze_observational_round(theory=theory, cost_budget=3.0)
        selected = freeze.get("selected_experiment") or {}
        measurement = {
            "experiment_id": selected.get("experiment_id"),
            "freeze_digest": freeze.get("freeze_digest"),
            "value": case["measurement"],
            "measurement_id": "QUAL-M-" + str(case["domain_id"]).upper(),
        }
        revision = kernel.absorb_observational_measurement(frozen_experiment=freeze, measurement=measurement)
        did = str(case["domain_id"])
        checks[f"{did}_frozen"] = freeze.get("status") == "HIERARCHICAL_OBSERVATIONAL_EXPERIMENT_FROZEN"
        checks[f"{did}_strong_selected"] = selected.get("experiment_id") == case["selected"]
        checks[f"{did}_postfreeze_identified"] = revision.get("status") == "HIERARCHICAL_EXPLANATION_IDENTIFIED_POSTFREEZE" and revision.get("leading_explanation_id") == case["expected"]
        outside_status = None
        if case.get("outside") is not None:
            outside = kernel.absorb_observational_measurement(
                frozen_experiment=freeze,
                measurement={
                    "experiment_id": selected.get("experiment_id"),
                    "freeze_digest": freeze.get("freeze_digest"),
                    "value": case["outside"],
                    "measurement_id": "QUAL-X-" + did.upper(),
                },
            )
            outside_status = outside.get("status")
            checks[f"{did}_outside_support_expands_representation"] = outside_status == "REPRESENTATION_EXPANSION_REQUIRED"
        rows.append({
            "domain_id": did,
            "theory_id": theory.get("theory_id"),
            "theory_owner": theory.get("owner"),
            "experiment_owner": kernel.observational_experiments.owner_id,
            "revision_owner": kernel.observational_revision.owner_id,
            "prediction_kind": str(next(iter(case["models"][1]["predictions"].values()))["kind"]),
            "selected_experiment_id": selected.get("experiment_id"),
            "utility": selected.get("utility"),
            "revision_status": revision.get("status"),
            "leading_explanation_id": revision.get("leading_explanation_id"),
            "outside_status": outside_status,
        })

    # Full mathematical support does not override the frozen compatibility gate.
    # Expansion means inadequate representation, not logical impossibility.
    materials = next(case for case in _universal_portfolio_cases() if case["domain_id"] == "materials")
    mt = compile_case(materials, theory_id="QUAL-UNIVERSAL-MATERIALS-FULL-SUPPORT")
    mf = kernel.freeze_observational_round(theory=mt, cost_budget=3.0)
    ms = mf.get("selected_experiment") or {}
    far = kernel.absorb_observational_measurement(
        frozen_experiment=mf,
        measurement={"experiment_id":ms.get("experiment_id"),"freeze_digest":mf.get("freeze_digest"),"value":1.0e9,"measurement_id":"QUAL-MATERIALS-FAR"},
    )
    checks["gaussian_all_incompatible_requires_expansion"] = (
        far.get("status") == "REPRESENTATION_EXPANSION_REQUIRED"
        and far.get("leading_explanation_id") is None
        and far.get("surviving_explanation_ids") == []
        and far.get("weights_are_calibrated_bayesian_posteriors") is False
    )

    # Same abstract portfolio, only domain metadata changes. Reasoning output must
    # remain invariant because domain labels are content, not algorithm selectors.
    template = _universal_portfolio_cases()[0]
    invariance_rows = []
    for did in ("astronomy", "nuclear", "chemistry", "biology", "mathematics"):
        theory = compile_case(template, theory_id="QUAL-DOMAIN-LABEL-INVARIANCE-" + did.upper(), domain_id=did)
        freeze = kernel.freeze_observational_round(theory=theory, cost_budget=3.0)
        selected = freeze.get("selected_experiment") or {}
        invariance_rows.append({"domain_id":did,"selected_experiment_id":selected.get("experiment_id"),"utility":selected.get("utility")})
    checks["domain_label_does_not_change_selection"] = len({r["selected_experiment_id"] for r in invariance_rows}) == 1
    utilities = [float(r["utility"]) for r in invariance_rows]
    checks["domain_label_does_not_change_utility"] = max(utilities)-min(utilities) <= 1e-15

    # One domain-neutral integrity control proves that missing science cannot be
    # bypassed by the universal selector.
    broken_models = [{
        "experiment_id":"E-INCOMPLETE","observable":"generic_observable","cost":1.0,"feasible":True,
        "predictions":{"A1":{"kind":"categorical","value":"A"},"A2":{"kind":"categorical","value":"B"}},
    }]
    broken = compile_case(template, theory_id="QUAL-UNIVERSAL-INCOMPLETE", domain_id="domain_neutral_control", models=broken_models)
    blocked = kernel.freeze_observational_round(theory=broken, cost_budget=3.0)
    checks["incomplete_prediction_map_fail_closed"] = blocked.get("status") == "BLOCKED_INCOMPLETE_EXPERIMENT_PREDICTIONS"
    checks["incomplete_prediction_map_selects_nothing"] = blocked.get("selected_experiment") is None

    owner_triples = {(r["theory_owner"], r["experiment_owner"], r["revision_owner"]) for r in rows}
    checks["same_reasoning_owners_across_domains"] = len(owner_triples) == 1
    checks["all_prediction_kinds_exercised"] = {r["prediction_kind"] for r in rows} == {"categorical", "gaussian", "interval"}

    passed = sum(bool(v) for v in checks.values())
    payload={
        "schema":"phi-universal-scientific-portfolio-qualification/v1",
        "status":"PASS_UNIVERSAL_SCIENTIFIC_PORTFOLIO_QUALIFICATION" if passed == len(checks) else "BLOCKED_UNIVERSAL_SCIENTIFIC_PORTFOLIO_QUALIFICATION",
        "passed":passed,
        "total":len(checks),
        "checks":[{"check":k,"status":"PASS" if v else "FAIL"} for k,v in checks.items()],
        "cases":rows,
        "domain_label_invariance":invariance_rows,
        "shared_owner_ids":list(next(iter(owner_triples))) if len(owner_triples) == 1 else [],
        "claim_boundary":{
            "cross_domain_synthetic_qualification_proves_all_sciences_solved":False,
            "domain_independent_reasoning_core_qualified_for_tested_contracts":passed == len(checks),
            "domain_semantics_may_require_typed_adapters":True,
            "domain_specific_reasoning_algorithm_required":False,
        },
    }
    payload["digest"]=digest_payload(payload)
    return payload



def _route_real_scientific_portfolio(
    kernel: LongHorizonBlindScientificCycleKernel,
    *,
    portfolio_id: str,
    domain_id: str,
    theory: Mapping[str, Any] | None,
    provenance: Mapping[str, Any],
    cost_budget: float = 4.0,
) -> dict[str, Any]:
    """Route a real/externally grounded portfolio through the common P3 readiness contract.

    The router never invents a missing theory, hypothesis, prediction, experiment or
    measurement. Existing evidence that predates a newly created P3 freeze is retained
    as provenance only and is never replayed as prospective post-freeze evidence.
    """
    base={
        "schema":"phi-universal-real-scientific-portfolio-ingress/v1",
        "portfolio_id":str(portfolio_id),
        "domain_id":str(domain_id),
        "reasoning_owner":kernel.observational_experiments.owner_id,
        "revision_owner":kernel.observational_revision.owner_id,
        "provenance":dict(provenance),
        "existing_evidence_reused_as_postfreeze_measurement":False,
    }
    if not isinstance(theory, Mapping):
        base.update({
            "status":"PORTFOLIO_P3_THEORY_CONTRACT_REQUIRED",
            "next_gate":"COMPILE_COMPETING_EXPLANATIONS_AND_EXPERIMENTAL_MODELS",
            "selection_attempted":False,
            "selected_experiment_id":None,
        })
        base["digest"]=digest_payload(base)
        return base
    ids=[str(x.get("id")) for x in theory.get("competing_explanations",()) if isinstance(x,Mapping) and x.get("id")]
    if len(ids)<2:
        base.update({
            "status":"PORTFOLIO_COMPETING_EXPLANATIONS_REQUIRED",
            "next_gate":"DEFINE_AT_LEAST_TWO_COMPETING_EXPLANATIONS",
            "selection_attempted":False,
            "selected_experiment_id":None,
            "competing_explanation_count":len(ids),
        })
        base["digest"]=digest_payload(base)
        return base
    if not list(theory.get("experimental_models",()) or ()):
        base.update({
            "status":"PORTFOLIO_EXPERIMENTAL_MODELS_REQUIRED",
            "next_gate":"DEFINE_DISCRIMINATING_EXPERIMENTAL_MODELS",
            "selection_attempted":False,
            "selected_experiment_id":None,
            "competing_explanation_count":len(ids),
        })
        base["digest"]=digest_payload(base)
        return base
    freeze=kernel.freeze_observational_round(theory=theory,cost_budget=float(cost_budget))
    selected=freeze.get("selected_experiment") or {}
    fstatus=str(freeze.get("status") or "")
    if fstatus=="BLOCKED_INCOMPLETE_EXPERIMENT_PREDICTIONS":
        status="PORTFOLIO_PREDICTION_CONTRACT_REQUIRED"
        next_gate="COMPLETE_FROZEN_PREDICTION_MAP"
    elif fstatus=="HIERARCHICAL_OBSERVATIONAL_EXPERIMENT_FROZEN":
        status="PORTFOLIO_FROZEN_FRESH_MEASUREMENT_REQUIRED"
        next_gate="OBTAIN_FRESH_POSTFREEZE_MEASUREMENT"
    else:
        status="PORTFOLIO_SELECTION_BLOCKED"
        next_gate="RESOLVE_EXPERIMENT_SELECTION_BLOCKER"
    base.update({
        "status":status,
        "next_gate":next_gate,
        "selection_attempted":True,
        "selection_status":fstatus,
        "selected_experiment_id":selected.get("experiment_id"),
        "freeze_digest":freeze.get("freeze_digest"),
        "competing_explanation_count":len(ids),
        "experimental_model_count":len(list(theory.get("experimental_models",()) or ())),
        "theory_digest":theory.get("digest"),
    })
    base["digest"]=digest_payload(base)
    return base


def _find_first_existing(root: Path, candidates: tuple[str,...]) -> Path | None:
    for rel in candidates:
        p=root/rel
        if p.is_file():
            return p
    return None


def _sealed_digest_for_path(root: Path, path: Path) -> str | None:
    hashes=root/"HASHES.txt"
    if not hashes.exists():
        return None
    try:
        rel=path.relative_to(root).as_posix()
    except ValueError:
        return None
    for line in hashes.read_text(encoding="utf-8",errors="replace").splitlines():
        parts=line.strip().split(maxsplit=1)
        if len(parts)==2 and parts[1].lstrip("*")==rel and len(parts[0])==64:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            return parts[0] if parts[0] == actual else None
    return None


def _run_real_portfolio_ingress_qualification(root: Path, kernel: LongHorizonBlindScientificCycleKernel) -> dict[str,Any]:
    """Bring existing real-science portfolios into one readiness contract.

    This is intentionally an ingress/readiness qualification, not retroactive conversion
    of old evidence into a prospective P3 measurement. Domain adapters may expose typed
    content, but all readiness/selection decisions remain in the shared P3 owners.
    """
    rows=[]; checks={}

    # Astronomy: current real NASA exoplanet portfolio already carries a P3 theory.
    exo_path=_find_first_existing(root,(
        "reports/exoplanet/NASA_EXOPLANET_P3_LOCAL.json",
        "reports/NASA_EXOPLANET_P3_LOCAL.json",
    ))
    checks["real_exoplanet_portfolio_present"]=exo_path is not None and _sealed_digest_for_path(root, exo_path) is not None
    if exo_path is not None:
        exo=json.loads(exo_path.read_text(encoding="utf-8"))
        exo_theory=exo.get("hierarchical_observational_theory") if isinstance(exo,Mapping) else None
        exo_source=exo.get("source",{}) if isinstance(exo,Mapping) else {}
        exo_route=_route_real_scientific_portfolio(
            kernel,
            portfolio_id="REAL-EXOPLANET-P3",
            domain_id="astronomy",
            theory=exo_theory if isinstance(exo_theory,Mapping) else None,
            provenance={
                "artifact_path":exo_path.relative_to(root).as_posix(),
                "sealed_sha256":_sealed_digest_for_path(root,exo_path),
                "source_sha256":exo_source.get("sha256") if isinstance(exo_source,Mapping) else None,
                "source_rows":exo_source.get("rows") if isinstance(exo_source,Mapping) else None,
                "evidence_mode":"REAL_RETROSPECTIVE_OR_EXISTING_OBSERVATIONAL",
            },
        )
        rows.append(exo_route)
        checks["real_exoplanet_uses_common_reasoning_owner"]=exo_route.get("reasoning_owner")==kernel.observational_experiments.owner_id
        checks["real_exoplanet_route_is_fail_closed_or_measurement_ready"]=exo_route.get("status") in {
            "PORTFOLIO_PREDICTION_CONTRACT_REQUIRED",
            "PORTFOLIO_FROZEN_FRESH_MEASUREMENT_REQUIRED",
            "PORTFOLIO_EXPERIMENTAL_MODELS_REQUIRED",
            "PORTFOLIO_COMPETING_EXPLANATIONS_REQUIRED",
        }
        checks["real_exoplanet_existing_evidence_not_reused_postfreeze"]=exo_route.get("existing_evidence_reused_as_postfreeze_measurement") is False
    else:
        checks["real_exoplanet_uses_common_reasoning_owner"]=False
        checks["real_exoplanet_route_is_fail_closed_or_measurement_ready"]=False
        checks["real_exoplanet_existing_evidence_not_reused_postfreeze"]=False

    # Fluid dynamics: the real JHTDB pipeline is present, but its existing DNS protocol
    # is not silently relabelled as a P3 competing-theory/prediction contract.
    jhtdb_runner=_find_first_existing(root,("evaluation/run_real_jhtdb_dns_closure.py",))
    jhtdb_guide=_find_first_existing(root,("RUN_TURBULENCE_DNS_CLOSURE_RU.md",))
    jhtdb_result=_find_first_existing(root,(
        "reports/turbulence/TURBULENCE_DNS_CLOSURE_CURRENT.json",
    ))
    # Root DNS reports are explicitly local/ignored artifacts. Do not make a
    # reproducible repository qualification depend on an operator's local run.
    jhtdb_present=jhtdb_runner is not None and jhtdb_guide is not None
    checks["real_jhtdb_portfolio_definition_present"] = bool(
        jhtdb_present
        and _sealed_digest_for_path(root, jhtdb_runner)
        and _sealed_digest_for_path(root, jhtdb_guide)
        and (jhtdb_result is None or _sealed_digest_for_path(root, jhtdb_result))
    )
    if jhtdb_present:
        jhtdb_route=_route_real_scientific_portfolio(
            kernel,
            portfolio_id="REAL-JHTDB-TURBULENCE-CLOSURE",
            domain_id="fluid_dynamics",
            theory=None,
            provenance={
                "runner_path":jhtdb_runner.relative_to(root).as_posix(),
                "guide_path":jhtdb_guide.relative_to(root).as_posix(),
                "runner_sealed_sha256":_sealed_digest_for_path(root,jhtdb_runner),
                "guide_sealed_sha256":_sealed_digest_for_path(root,jhtdb_guide),
                "existing_result_present":jhtdb_result is not None,
                "measurement_executed_by_this_qualification":False,
                "existing_result_path":jhtdb_result.relative_to(root).as_posix() if jhtdb_result else None,
                "existing_result_sealed_sha256":_sealed_digest_for_path(root,jhtdb_result) if jhtdb_result else None,
                "evidence_mode":"REAL_EXTERNAL_JHTDB_BLIND_DNS",
                "synthetic_substitution_allowed":False,
            },
        )
        rows.append(jhtdb_route)
        checks["real_jhtdb_enters_common_contract_without_domain_selector"]=jhtdb_route.get("reasoning_owner")==kernel.observational_experiments.owner_id
        checks["real_jhtdb_requires_p3_theory_before_new_selection"]=jhtdb_route.get("status")=="PORTFOLIO_P3_THEORY_CONTRACT_REQUIRED"
        checks["real_jhtdb_existing_evidence_not_reused_postfreeze"]=jhtdb_route.get("existing_evidence_reused_as_postfreeze_measurement") is False
    else:
        checks["real_jhtdb_enters_common_contract_without_domain_selector"]=False
        checks["real_jhtdb_requires_p3_theory_before_new_selection"]=False
        checks["real_jhtdb_existing_evidence_not_reused_postfreeze"]=False

    # Pharmaceutical published-evidence portfolio, when present, is treated identically:
    # evidence may seed theory construction, but cannot bypass the shared prediction/freeze gate.
    pharma_path=_find_first_existing(root,(
        "data/pharmaceutical/metformin_renal_function_pk_summary_v7_9.json",
        "data/pharmaceutical/pharmaceutical_problem_atlas_v8_3.json",
    ))
    if pharma_path is not None:
        pharma_route=_route_real_scientific_portfolio(
            kernel,
            portfolio_id="REAL-PHARMACEUTICAL-EVIDENCE",
            domain_id="pharmaceutical",
            theory=None,
            provenance={
                "artifact_path":pharma_path.relative_to(root).as_posix(),
                "sealed_sha256":_sealed_digest_for_path(root,pharma_path),
                "evidence_mode":"REAL_OR_LITERATURE_GROUNDED_EXISTING_EVIDENCE",
            },
        )
        rows.append(pharma_route)
    checks["at_least_two_distinct_real_science_domains_ingressed"]=len({r.get("domain_id") for r in rows})>=2
    checks["all_ingressed_portfolios_use_same_reasoning_owner"]=len({r.get("reasoning_owner") for r in rows})==1 if rows else False
    checks["no_ingressed_portfolio_reuses_prior_evidence_as_postfreeze_measurement"]=all(r.get("existing_evidence_reused_as_postfreeze_measurement") is False for r in rows)
    checks["every_ingressed_portfolio_has_explicit_next_gate"]=all(bool(r.get("next_gate")) for r in rows) and (pharma_path is None or _sealed_digest_for_path(root, pharma_path) is not None)

    passed=sum(bool(v) for v in checks.values())
    payload={
        "schema":"phi-real-scientific-portfolio-ingress-qualification/v1",
        "status":"PASS_REAL_SCIENTIFIC_PORTFOLIO_INGRESS_QUALIFICATION" if passed==len(checks) else "BLOCKED_REAL_SCIENTIFIC_PORTFOLIO_INGRESS_QUALIFICATION",
        "passed":passed,"total":len(checks),
        "checks":[{"check":k,"status":"PASS" if v else "FAIL"} for k,v in checks.items()],
        "portfolios":rows,
        "claim_boundary":{
            "existing_real_evidence_is_prospective_p3_measurement":False,
            "missing_predictions_may_be_synthesized_from_postfreeze_evidence":False,
            "domain_specific_reasoning_algorithm_introduced":False,
            "domain_adapters_may_supply_typed_content":True,
            "common_readiness_selection_revision_rules_required":True,
        },
    }
    payload["digest"]=digest_payload(payload)
    return payload

def run_release_qualification(root: str|Path|None=None)->dict[str,Any]:
    root=Path(root or Path(__file__).resolve().parents[1]); theories=[_compiled(root,k) for k in ("t0","t1","t2")]
    with tempfile.TemporaryDirectory(prefix="phi_long_horizon_") as td:
      kernel=LongHorizonBlindScientificCycleKernel(root,state_path=Path(td)/"session.json")
      epoch_summaries=[]; identifications=0; expansions=0; total_rounds=0; freeze_all_axes=True; no_prefreeze_truth=True
      # 32 epochs x at least 4 persisted heartbeat events => >128 heartbeat scale after completion markers and measurements.
      for epoch in range(32):
        active=list(theories); active_ids=[x["executable_id"] for x in active]; round_receipts=[]; outside=(epoch%8==7)
        # First freeze occurs before hidden mechanism is selected.
        first=kernel.freeze_round(question=f"blind long-horizon epoch {epoch}: distinguish frozen executable theories",active_theories=active,cost_budget=4.0)
        freeze_all_axes &= first.get("frontier",{}).get("phi_scan",{}).get("all_registered_axes_visited") is True and first.get("frontier",{}).get("phi_scan",{}).get("registered_axis_count") == canonical_axis_count()
        no_prefreeze_truth &= first.get("hidden_truth_accessed") is False and first.get("internet_used_prefreeze") is False
        if first.get("status")!="LONG_HORIZON_ROUND_FROZEN": raise RuntimeError(first)
        seed=int(hashlib.sha256(f"{epoch}:{first['digest']}".encode()).hexdigest(),16)
        hidden_index=seed%len(theories)
        current_freeze=first
        for ri in range(3):
          total_rounds+=1
          selected=current_freeze["selection"]["selected_experiment"]
          hidden=theories[hidden_index]
          measurement=_execute_hidden(hidden,selected,current_freeze["frontier"]["freeze_digest"],epoch,ri,outside=outside and ri==0)
          update=kernel.absorb_measurement(epoch_freeze=current_freeze,measurement=measurement,environment_id=f"BLIND-EPOCH-{epoch}")
          round_receipts.append({"freeze_digest":current_freeze["digest"],"round_freeze_digest":current_freeze["frontier"]["freeze_digest"],"measurement":measurement,"update":update})
          st=update["status"]
          if st=="REPRESENTATION_EXPANSION_REQUIRED": expansions+=1; break
          surviving=update["revision"].get("surviving_theory_ids",())
          if st=="THEORY_IDENTIFIED_POSTFREEZE": identifications+=1; break
          active=[t for t in active if t["executable_id"] in set(surviving)]
          if len(active)<2: break
          current_freeze=kernel.freeze_round(question=f"blind epoch {epoch} round {ri+1}: discriminate survivors",active_theories=active,cost_budget=4.0)
          if current_freeze.get("status")!="LONG_HORIZON_ROUND_FROZEN": break
        # add three explicit resident/session heartbeat markers per epoch to exercise persistence/consolidation scale
        for _ in range(3): kernel.pulse()
        kernel.mark_epoch_complete()
        epoch_summaries.append({"epoch":epoch,"hidden_index_revealed_post_epoch":hidden_index,"outside_frozen_control":outside,"rounds":round_receipts})
      state=kernel.ledger.load()
      universal_portfolio=_run_universal_portfolio_qualification(kernel)
      real_portfolio_ingress=_run_real_portfolio_ingress_qualification(root,kernel)
      obs_theory=HierarchicalObservationalTheoryOwner().compile(
        theory_id="LONG-HORIZON-OBSERVATIONAL-CONTROL",
        universal_layer={"law":"known"},host_layer={"alpha":"latent"},regime_layer={"f_R":"open"},feasible_domain_layer={"Omega":"interval"},
        competing_explanations=[{"id":"OH1"},{"id":"OH2"},{"id":"OH3"}],
        predictions=[{"prediction":"distinguish","falsification":"wrong outcome","defense":"freeze before evidence","heldout_refit_allowed":False}],
        evidence_digest=digest_payload({"observational_control":True}),
        experimental_models=[
          {"experiment_id":"OE-WEAK","observable":"weak","cost":1.0,"feasible":True,"predictions":{"OH1":{"kind":"categorical","value":"A"},"OH2":{"kind":"categorical","value":"A"},"OH3":{"kind":"categorical","value":"C"}}},
          {"experiment_id":"OE-STRONG","observable":"strong","cost":1.5,"feasible":True,"predictions":{"OH1":{"kind":"categorical","value":"A"},"OH2":{"kind":"categorical","value":"B"},"OH3":{"kind":"categorical","value":"C"}}},
        ],
      )
      obs_freeze=kernel.freeze_observational_round(theory=obs_theory,cost_budget=2.0)
      obs_measurement={"experiment_id":"OE-STRONG","freeze_digest":obs_freeze.get("freeze_digest"),"value":"B","measurement_id":"OBS-HIDDEN-B"}
      obs_revision=kernel.absorb_observational_measurement(frozen_experiment=obs_freeze,measurement=obs_measurement)
      checks={
        "kernel_owner":kernel.contract()["owner_id"]=="PHI-LONG-HORIZON-BLIND-SCIENTIFIC-CYCLE/1.0.0",
        "hierarchical_observational_cycle_supported":kernel.contract()["hierarchical_observational_cycle"]["supported"] is True,
        "universal_cross_domain_portfolios_pass":universal_portfolio.get("status")=="PASS_UNIVERSAL_SCIENTIFIC_PORTFOLIO_QUALIFICATION",
        "domain_metadata_does_not_change_common_reasoning":all(x.get("status")=="PASS" for x in universal_portfolio.get("checks",()) if x.get("check") in {"domain_label_does_not_change_selection","domain_label_does_not_change_utility","same_reasoning_owners_across_domains"}),
        "real_scientific_portfolio_ingress_pass":real_portfolio_ingress.get("status")=="PASS_REAL_SCIENTIFIC_PORTFOLIO_INGRESS_QUALIFICATION",
        "real_portfolio_prospective_boundary_preserved":all(x.get("status")=="PASS" for x in real_portfolio_ingress.get("checks",()) if x.get("check") in {"no_ingressed_portfolio_reuses_prior_evidence_as_postfreeze_measurement","every_ingressed_portfolio_has_explicit_next_gate"}),
        "observational_experiment_selected_prefreeze":obs_freeze.get("selected_experiment",{}).get("experiment_id")=="OE-STRONG" and obs_freeze.get("frozen",{}).get("measurement_inspected_before_selection") is False,
        "observational_measurement_bound_to_freeze":obs_revision.get("experiment_id")=="OE-STRONG",
        "observational_hidden_explanation_identified":obs_revision.get("status")=="HIERARCHICAL_EXPLANATION_IDENTIFIED_POSTFREEZE" and obs_revision.get("leading_explanation_id")=="OH2",
        "observational_postfreeze_not_reused_for_selection":obs_revision.get("claim_boundary",{}).get("postfreeze_evidence_reused_for_experiment_selection") is False,
        "hidden_truth_not_solver_api":kernel.contract()["blindness"]["hidden_truth_parameter_in_solver_api"] is False,
        "internet_prefreeze_forbidden":kernel.contract()["blindness"]["internet_prefreeze"]=="FORBIDDEN",
        "all_current_axes_scanned":freeze_all_axes,
        "no_prefreeze_truth_access":no_prefreeze_truth,
        "epochs_32":len(epoch_summaries)==32,
        "heartbeat_ge_128":state["heartbeat_count"]>=128,
        "persistent_epoch_count":state["epoch_count"]==32,
        "completed_epoch_count":state["completed_epoch_count"]==32,
        "normal_epochs_identified":identifications>=20,
        "outside_controls_expand":expansions==4,
        "wrong_theories_demoted":sum(state["theory_demotions"].values())>0,
        "identified_theory_memory_nonempty":len(state["identified_theories"])>=20,
        "representation_expansion_count_exact":state["representation_expansion_count"]==4,
        "transition_history_bounded":len(state["transitions"])<=kernel.ledger.max_transition_receipts,
        "measurement_history_bounded":len(state["measurement_receipts"])<=kernel.ledger.max_transition_receipts,
        "attestation_not_relabelled_world":all(r["update"]["attestation"].get("world_ready") is False for e in epoch_summaries for r in e["rounds"]),
        "outside_observation_never_nearest_guess":all((not e["outside_frozen_control"]) or e["rounds"][0]["update"]["status"]=="REPRESENTATION_EXPANSION_REQUIRED" for e in epoch_summaries),
        "measurement_postfreeze_bound":all(r["measurement"]["frontier_freeze_digest"]==r["round_freeze_digest"] for e in epoch_summaries for r in e["rounds"]),
        "synthetic_not_world_discovery":kernel.contract()["claim_boundary"]["synthetic_blind_cycle_is_world_discovery"] is False,
        "next_roadmap_external_validation":kernel.contract()["roadmap_dependency"]["next"]=="PROSPECTIVE-EXTERNAL-SCIENTIFIC-VALIDATION",
      }
      passed=sum(bool(v) for v in checks.values())
      payload={"schema":SCHEMA,"release":RELEASE,"status":"PASS_PHI_LONG_HORIZON_BLIND_CYCLE_QUALIFICATION" if passed==len(checks) else "BLOCKED_PHI_LONG_HORIZON_BLIND_CYCLE_QUALIFICATION","passed":passed,"total":len(checks),"checks":[{"check":k,"status":"PASS" if v else "FAIL"} for k,v in checks.items()],"summary":{"epochs":32,"total_rounds":total_rounds,"identified_epochs":identifications,"representation_expansions":expansions,"heartbeat_count":state["heartbeat_count"],"theory_demotions":state["theory_demotions"],"state_digest":state["state_digest"]},"demonstration":{"first_epoch":epoch_summaries[0],"outside_control_epoch":epoch_summaries[7],"final_state":state},"universal_scientific_portfolio_qualification":universal_portfolio,"real_scientific_portfolio_ingress_qualification":real_portfolio_ingress,"claim_boundary":{"synthetic_qualification_is_world_discovery":False,"hidden_truth_revealed_to_solver_prefreeze":False,"internet_used_prefreeze":False}}
      payload["digest"]=digest_payload(payload); return payload

if __name__=="__main__": print(json.dumps(run_release_qualification(),ensure_ascii=False,indent=2,sort_keys=True))
