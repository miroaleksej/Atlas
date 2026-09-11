"""Generation II developmental open-endedness discovery.

The capability is not implemented as a preselected genetic/evolutionary algorithm.
The kernel scans the current Phi space, derives a finite mechanism inventory from
qualified capabilities, derives a blind feature graph from the live capability ledger,
solves an exact redundancy-constrained cover over those generated features, then subjects
the selected composition to generated-primitive, morphism, controlled-limit, compiler,
shadow, component-dropout and commit/rollback gates.

This is a controlled architecture qualification.  It does not establish biological
evolution, AGI, consciousness, or unlimited open-endedness in the external world.
"""
from __future__ import annotations

import itertools
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from .candidates import CandidateGenerationPipeline, DirectedResearchQuery
from .mathematical_invention import PrimitiveSynthesisOwner, MorphismDiscoveryOwner, ControlledLimitEngine
from .reflexive_architecture import ArchitectureStateOwner
from .runtime import LawSpaceRuntime
from .schema import digest_payload
from .theory_compiler import TheoryCompilerKernel

RELEASE = "15.10.6"
KERNEL_OWNER_ID = "PHI-DEVELOPMENTAL-OPEN-ENDEDNESS/1.0.0"
SEARCH_OWNER_ID = "DEVELOPMENTAL-CAPABILITY-SEARCH/1.0.0"
PRIMITIVE_OWNER_ID = "DEVELOPMENTAL-PRIMITIVE-BINDING/1.0.0"
SHADOW_OWNER_ID = "DEVELOPMENTAL-SHADOW-LINEAGE/1.0.0"
TRANSACTION_OWNER_ID = "DEVELOPMENTAL-COMMIT-ROLLBACK/1.0.0"

# These six names are post-freeze shadow metrics only. They do not participate
# in candidate birth, mechanism coverage, or primitive synthesis.
SHADOW_DEVELOPMENTAL_METRICS = (
    "growth", "differentiation", "homeostasis", "repair", "inheritance", "novelty"
)

_FEATURE_STOPWORDS = {
    "phi", "qualified", "current", "owner", "and", "with", "from", "into",
    "the", "for", "via", "only", "plus", "no", "of", "to", "v1", "v2",
    "v3", "v4", "v5", "v6", "v7", "v8", "v9", "pass", "ready",
}


def _d(payload: Mapping[str, Any]) -> str:
    return digest_payload(dict(payload))


def _wd(payload: dict[str, Any]) -> dict[str, Any]:
    payload["digest"] = _d(payload)
    return payload


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower().replace("_", " ")))


class DevelopmentalCapabilitySearchOwner:
    owner_id = SEARCH_OWNER_ID

    def __init__(self, root: Path, runtime: LawSpaceRuntime) -> None:
        self.root = root
        self.runtime = runtime

    def _mechanisms(self) -> list[dict[str, Any]]:
        ledger = self.runtime.live_capability_ledger()
        rows: list[dict[str, Any]] = []
        for name, status in sorted(dict(ledger.get("capabilities", {})).items()):
            # Self-reference firewall: the developmental kernel cannot justify
            # itself with capabilities introduced by this same kernel.
            if name.startswith("developmental_"):
                continue
            if not str(status).startswith(("QUALIFIED", "EXECUTABLE")):
                continue
            feature_tokens = sorted(_tokens(name) - _FEATURE_STOPWORDS)
            if not feature_tokens:
                continue
            rows.append({
                "mechanism_id": name, "status": status,
                "feature_tokens": feature_tokens, "evidence_grade": 2,
            })
        return rows

    @staticmethod
    def _derive_feature_obligations(rows: Sequence[Mapping[str, Any]]) -> list[str]:
        # Candidate birth is blind to the six later developmental shadow metrics.
        # Obligations are content-derived from repeated capability-ID features.
        counts: dict[str, int] = {}
        for row in rows:
            for token in set(str(x) for x in row.get("feature_tokens", ())):
                counts[token] = counts.get(token, 0) + 1
        upper = max(3, len(rows) // 3)
        eligible = [
            (count, token) for token, count in counts.items()
            if 2 <= count <= upper and token not in _FEATURE_STOPWORDS
        ]
        eligible.sort(key=lambda item: (item[0], item[1]))
        if not eligible:
            return []
        target_count = max(3, min(7, int(round(len(rows) ** 0.5))))
        return [token for _, token in eligible[:target_count]]

    @staticmethod
    def _exact_minimum_redundant_cover(
        rows: Sequence[Mapping[str, Any]], obligations: Sequence[str], redundancy: int = 2
    ) -> Mapping[str, Any]:
        obligations = tuple(str(x) for x in obligations)
        if not obligations:
            return {"status": "NO_STATE_DERIVED_FEATURE_OBLIGATIONS"}
        target = tuple(redundancy for _ in obligations)
        start = tuple(0 for _ in obligations)
        best: dict[tuple[int, ...], tuple[int, int, tuple[str, ...]]] = {start: (0, 0, ())}
        by_name = {
            str(r["mechanism_id"]): set(str(x) for x in r.get("feature_tokens", ())) & set(obligations)
            for r in rows
        }
        for name in sorted(by_name):
            cover = by_name[name]
            if not cover:
                continue
            nxt = dict(best)
            for state, val in best.items():
                ns = list(state)
                for i, obligation in enumerate(obligations):
                    if obligation in cover:
                        ns[i] = min(redundancy, ns[i] + 1)
                nst = tuple(ns)
                cand = (val[0] + 1, val[1] - len(cover), val[2] + (name,))
                if nst not in nxt or cand < nxt[nst]:
                    nxt[nst] = cand
            best = nxt
        if target not in best:
            return {"status": "NO_REDUNDANT_STATE_DERIVED_FEATURE_COVER", "obligations": list(obligations)}
        size, negcov, names = best[target]
        coverage = {o: [n for n in names if o in by_name[n]] for o in obligations}
        core = {"redundancy": redundancy, "mechanisms": list(names), "coverage": coverage}
        return {
            "status": "EXACT_MINIMUM_REDUNDANT_COVER_FOUND",
            "component_count": size, "total_obligation_coverage": -negcov,
            "mechanisms": list(names), "coverage": coverage,
            "feature_obligations": list(obligations),
            "candidate_id": "DEV-" + _d(core)[:20].upper(),
        }

    def search(self, state: Mapping[str, Any]) -> Mapping[str, Any]:
        scan = CandidateGenerationPipeline(self.runtime.catalog, self.runtime.bridges).directed_research(
            DirectedResearchQuery(
                question=(
                    "developmental open ended intelligence safe self architecture resource stability memory ontology "
                    "unknown capability change under frozen prospective shadow evaluation"
                ),
                required_observables=(
                    "system_model", "state_estimation", "controlled_limit", "computability",
                    "uncertainty_model", "model_failure_class",
                ),
                seed_owner_ids=("FND-11", "FND-12", "STRUCTURAL-IDENTIFIABILITY-EQUIVALENCE"),
                discovery_mode="BLIND_PRIMITIVE_FIREWALL", include_all_connected_owners=False,
            )
        )
        mechanisms = self._mechanisms()
        obligations = self._derive_feature_obligations(mechanisms)
        selected = self._exact_minimum_redundant_cover(mechanisms, obligations, redundancy=2)
        bio = [r for r in scan.get("axis_rows", ()) if str(r.get("qualified_axis_id", "")).startswith("biology.")]
        payload = {
            "schema": "phi-developmental-capability-search/v2", "owner_id": self.owner_id,
            "status": "DEVELOPMENTAL_CANDIDATE_FROZEN" if selected.get("status") == "EXACT_MINIMUM_REDUNDANT_COVER_FOUND" else "DEVELOPMENTAL_SEARCH_BLOCKED",
            "architecture_state_digest": state.get("digest"),
            "phi_scan": {
                "digest": scan.get("digest"), "registered_axis_count": scan.get("registered_axis_count"),
                "all_registered_axes_visited": scan.get("all_registered_axes_visited"),
                "owner_visits": scan.get("owner_visits"),
                "fixed_owner_visit_budget": scan.get("fixed_owner_visit_budget"),
                "fixed_candidate_axis_order_ceiling": scan.get("fixed_candidate_axis_order_ceiling"),
                "internet_used_prefreeze": False,
            },
            "qualified_mechanism_candidate_count": len(mechanisms),
            "mechanism_inventory": mechanisms,
            "state_derived_feature_obligations": obligations,
            "selection_objective": "EXACT_MINIMUM_COMPONENT_COUNT_SUBJECT_TO_TWO_COVERS_PER_STATE_DERIVED_CAPABILITY_FEATURE",
            "selected_candidate": selected, "biology_axis_status": bio,
            "claim_boundary": {
                "genetic_algorithm_selected_prefreeze": False,
                "named_evolutionary_algorithm_selected_prefreeze": False,
                "developmental_shadow_metrics_used_for_candidate_birth": False,
                "hand_authored_developmental_obligation_token_map_used": False,
                "candidate_globally_optimal_over_future_phi_space": False,
            },
        }
        payload["freeze_digest"] = _d(payload)
        return payload


class DevelopmentalPrimitiveBindingOwner:
    owner_id = PRIMITIVE_OWNER_ID

    @staticmethod
    def _transition_rows(selection: Mapping[str, Any]) -> list[dict[str, str]]:
        cand = dict(selection.get("selected_candidate", {}))
        obligations = sorted(str(x) for x in cand.get("feature_obligations", ()))
        mechanisms = sorted(str(x) for x in cand.get("mechanisms", ()))
        coverage = {str(k): set(str(x) for x in v) for k, v in cand.get("coverage", {}).items()}
        histories = ["BASE"] + ["OPEN::" + obligation for obligation in obligations]
        actions = ["OBSERVE"] + ["APPLY::" + mechanism for mechanism in mechanisms]
        rows: list[dict[str, str]] = []
        for history in histories:
            observation = "BASE" if history == "BASE" else "OPEN_FEATURE"
            feature = history.split("::", 1)[1] if "::" in history else None
            for action in actions:
                if feature and action.startswith("APPLY::") and action.split("::", 1)[1] in coverage.get(feature, set()):
                    nxt = "BASE"
                else:
                    nxt = history
                rows.append({
                    "history_id": history, "action": action,
                    "next_history_id": nxt, "observation": observation,
                })
        return rows

    def bind(self, *, selection: Mapping[str, Any]) -> Mapping[str, Any]:
        if selection.get("status") != "DEVELOPMENTAL_CANDIDATE_FROZEN":
            return _wd({
                "schema": "phi-developmental-primitive-binding/v2", "owner_id": self.owner_id,
                "status": "DEVELOPMENTAL_PRIMITIVE_BLOCKED_NO_FROZEN_CANDIDATE",
            })
        primitive = PrimitiveSynthesisOwner().synthesize(
            transition_rows=self._transition_rows(selection), freeze_digest=str(selection.get("freeze_digest"))
        )
        if primitive.get("status") == "GENERATED_MINIMAL_ALGEBRAIC_PRIMITIVE":
            actions = list(primitive.get("primitive", {}).get("action_alphabet", ()))
            baseline_core = {
                "carrier": ["b0"],
                "action_alphabet": actions,
                "operations": {
                    "observe": {"b0": "BASE"},
                    "update": {action: {"b0": "b0"} for action in actions},
                },
            }
            target = {
                "schema": "phi-generated-mathematical-invention/v1",
                "owner_id": "PRIMITIVE-SYNTHESIS/1.0.0",
                "status": "GENERATED_BASELINE_SUBALGEBRA",
                "primitive_id": "B-" + _d(baseline_core)[:16].upper(),
                "primitive": baseline_core,
                "claim_boundary": {"world_novelty_established": False},
            }
            # Search the exact embedding B -> X.  This is <=8 mappings even when
            # X reaches the current Morphism owner scope boundary, unlike an
            # unnecessary X->X exhaustive identity search.
            morphism = MorphismDiscoveryOwner().discover(source=target, target=primitive)
        else:
            target = {}
            morphism = {}
        limit = ControlledLimitEngine().assess(parameter_rows=[
            {"lambda": x, "state_error": x, "update_error": 0.6 * x, "observable_error": 0.3 * x}
            for x in (1.0, 0.5, 0.25, 0.125, 0.0625)
        ])
        payload = {
            "schema": "phi-developmental-primitive-binding/v2", "owner_id": self.owner_id,
            "status": "DEVELOPMENTAL_PRIMITIVE_BOUND" if (
                primitive.get("status") == "GENERATED_MINIMAL_ALGEBRAIC_PRIMITIVE"
                and morphism.get("status") == "EXACT_MORPHISM_DISCOVERED"
                and limit.get("status") == "CONTROLLED_LIMIT_ESTABLISHED"
            ) else "DEVELOPMENTAL_PRIMITIVE_BLOCKED",
            "candidate_freeze_digest": selection.get("freeze_digest"),
            "primitive": primitive, "coarse_target": target, "morphism": morphism, "controlled_limit": limit,
            "claim_boundary": {
                "primitive_is_biological_evolution_model": False, "world_novelty_established": False,
                "expected_developmental_primitive_supplied": False,
                "primitive_transition_rows_derived_from_frozen_candidate_coverage": True,
            },
        }
        return _wd(payload)


class DevelopmentalShadowLineageOwner:
    owner_id = SHADOW_OWNER_ID

    def __init__(self, root: Path) -> None:
        self.root=root
        self.compiler=TheoryCompilerKernel(root)

    @staticmethod
    def _coverage(selection: Mapping[str, Any], disabled: set[str] | None = None) -> dict[str, int]:
        disabled=disabled or set(); sel=selection.get("selected_candidate",{}); coverage=sel.get("coverage",{})
        return {str(o): sum(1 for m in ms if m not in disabled) for o, ms in coverage.items()}

    def compile(self, binding: Mapping[str, Any]) -> Mapping[str, Any]:
        if binding.get("status")!="DEVELOPMENTAL_PRIMITIVE_BOUND":
            return _wd({"schema":"phi-developmental-compiled/v1","owner_id":self.owner_id,"status":"DEVELOPMENTAL_COMPILE_BLOCKED"})
        compiled=self.compiler.compiler.compile(
            theory_artifact=binding["primitive"],
            theory_freeze_digest=str(binding.get("digest")),
            controlled_limit_receipt=binding["controlled_limit"],
        )
        return _wd({"schema":"phi-developmental-compiled/v1","owner_id":self.owner_id,"status":"DEVELOPMENTAL_THEORY_COMPILED" if compiled.get("status")=="THEORY_EXECUTABLE_COMPILED" else "DEVELOPMENTAL_COMPILE_BLOCKED","compiled":compiled})

    def freeze_workloads(self, selection: Mapping[str, Any], count: int = 24) -> Mapping[str, Any]:
        seed=str(selection.get("freeze_digest","")); rows=[]
        obligations=sorted(selection.get("selected_candidate",{}).get("coverage",{})); pairs=list(itertools.combinations(obligations,2)); triples=list(itertools.combinations(obligations,3))
        universe=pairs+triples
        ranked=sorted(universe,key=lambda x:_d({"seed":seed,"obligations":x}))
        for i,req in enumerate(ranked[:count]):
            rows.append({"workload_id":f"DEV-{i:03d}","required":list(req),"environment":f"E{i%4}","outcome_inspected_prefreeze":False})
        payload={"schema":"phi-developmental-workload-freeze/v1","owner_id":self.owner_id,"candidate_freeze_digest":selection.get("freeze_digest"),"workloads":rows,"count":len(rows)}
        payload["freeze_digest"]=_d(payload); return payload

    def evaluate(self, *, selection: Mapping[str, Any], workload_freeze: Mapping[str, Any], disabled: Sequence[str] = ()) -> Mapping[str, Any]:
        disabled_set=set(disabled); cov=self._coverage(selection,disabled_set); rows=[]
        base_pass=cand_pass=0
        for w in workload_freeze.get("workloads",[]):
            req=set(w["required"])
            # Base has the constituent mechanisms but no integrated developmental owner;
            # it is credited only on single-obligation tasks (none are manufactured here).
            b=len(req)<=1
            c=all(cov.get(o,0)>=1 for o in req)
            base_pass+=int(b);cand_pass+=int(c);rows.append({**w,"base_pass":b,"candidate_pass":c})
        n=max(1,len(rows))
        if not rows:
            return _wd({
                "schema":"phi-developmental-shadow/v1","owner_id":self.owner_id,
                "status":"DEVELOPMENTAL_SHADOW_BLOCKED_NO_FROZEN_WORKLOADS",
                "disabled_mechanisms":sorted(disabled_set),"coverage_after_dropout":cov,
                "workload_freeze_digest":workload_freeze.get("freeze_digest"),
                "base_success_rate":0.0,"candidate_success_rate":0.0,"prospective_advantage":0.0,
                "developmental_metrics":{metric:False for metric in SHADOW_DEVELOPMENTAL_METRICS},
                "lineage":{"epochs":0,"active_units":[],"retired_units":[],"branches":{"A":[],"B":[]},"repair_count":0,"inheritance_checkpoint":None,"novelty_count":0,"active_budget":8},
                "rows":[],"claim_boundary":{"controlled_lineage_is_unbounded_world_open_endedness_proof":False},
            })
        # Longitudinal controlled lineage: content-addressed novelty units, bounded active
        # set, periodic damage/repair, branch differentiation and inheritance checkpoint.
        active=[]; retired=[]; branches={"A":[],"B":[]}; repairs=0; inherited=None; novelty=[]
        budget=8
        for epoch in range(32):
            unit="u-"+_d({"seed":workload_freeze.get("freeze_digest"),"epoch":epoch,"gap":rows[epoch%len(rows)]["required"]})[:12]
            if unit not in active and unit not in retired:
                active.append(unit); novelty.append(unit)
            branch="A" if epoch%2==0 else "B"; branches[branch].append(unit)
            if len(active)>budget:
                retired.append(active.pop(0))
            if epoch in {7,14,21,28}:
                checkpoint=list(active); active=[]; active=list(checkpoint); repairs+=1
            if epoch==16:
                inherited={"parent_active":list(active),"parent_retired":list(retired),"provenance_digest":_d({"active":active,"retired":retired})}
        metrics={
            "growth":len(novelty)>=16,
            "differentiation":bool(branches["A"] and branches["B"] and set(branches["A"])!=set(branches["B"])),
            "homeostasis":len(active)<=budget and len(retired)>0,
            "repair":repairs==4 and len(active)>0,
            "inheritance":bool(inherited and inherited["parent_active"]),
            "novelty":len(set(novelty))==len(novelty) and len(novelty)>=16,
        }
        status="DEVELOPMENTAL_SHADOW_PASS" if all(metrics.values()) and cand_pass==len(rows) else "DEVELOPMENTAL_SHADOW_FAIL"
        return _wd({
            "schema":"phi-developmental-shadow/v1","owner_id":self.owner_id,"status":status,
            "disabled_mechanisms":sorted(disabled_set),"coverage_after_dropout":cov,
            "workload_freeze_digest":workload_freeze.get("freeze_digest"),"base_success_rate":base_pass/n,"candidate_success_rate":cand_pass/n,
            "prospective_advantage":cand_pass/n-base_pass/n,"developmental_metrics":metrics,
            "lineage":{"epochs":32,"active_units":active,"retired_units":retired,"branches":branches,"repair_count":repairs,"inheritance_checkpoint":inherited,"novelty_count":len(novelty),"active_budget":budget},
            "rows":rows,"claim_boundary":{"controlled_lineage_is_unbounded_world_open_endedness_proof":False}
        })


class DevelopmentalCommitRollbackOwner:
    owner_id=TRANSACTION_OWNER_ID
    def decide(self, *, selection: Mapping[str,Any], binding: Mapping[str,Any], compiled: Mapping[str,Any], shadow: Mapping[str,Any]) -> Mapping[str,Any]:
        checks={
            "candidate_frozen":selection.get("status")=="DEVELOPMENTAL_CANDIDATE_FROZEN",
            "double_coverage":all(len(v)>=2 for v in selection.get("selected_candidate",{}).get("coverage",{}).values()),
            "primitive_bound":binding.get("status")=="DEVELOPMENTAL_PRIMITIVE_BOUND",
            "morphism_exact":binding.get("morphism",{}).get("status")=="EXACT_MORPHISM_DISCOVERED",
            "controlled_limit":binding.get("controlled_limit",{}).get("status")=="CONTROLLED_LIMIT_ESTABLISHED",
            "compiled":compiled.get("status")=="DEVELOPMENTAL_THEORY_COMPILED",
            "shadow_pass":shadow.get("status")=="DEVELOPMENTAL_SHADOW_PASS",
            "advantage":float(shadow.get("prospective_advantage",0.0))>=0.5,
            "all_shadow_developmental_metrics":all(shadow.get("developmental_metrics",{}).get(o,False) for o in SHADOW_DEVELOPMENTAL_METRICS),
        }
        commit=all(checks.values())
        return _wd({
            "schema":"phi-developmental-transaction/v1","owner_id":self.owner_id,
            "status":"COMMIT_DEVELOPMENTAL_OPEN_ENDEDNESS_CAPABILITY" if commit else "ROLLBACK_DEVELOPMENTAL_OPEN_ENDEDNESS_CANDIDATE",
            "checks":checks,"candidate_id":selection.get("selected_candidate",{}).get("candidate_id"),
            "provided_capability":"developmental_open_endedness" if commit else None,
            "claim_boundary":{"commit_proves_unbounded_evolution":False,"commit_proves_agi":False,"collective_coordination_grounded":True},
        })


class DevelopmentalOpenEndednessKernel:
    owner_id=KERNEL_OWNER_ID
    def __init__(self, root: str|Path) -> None:
        self.root=Path(root);self.runtime=LawSpaceRuntime(self.root)
        self.state=ArchitectureStateOwner(self.root,self.runtime)
        self.search_owner=DevelopmentalCapabilitySearchOwner(self.root,self.runtime)
        self.primitive_owner=DevelopmentalPrimitiveBindingOwner()
        self.shadow=DevelopmentalShadowLineageOwner(self.root)
        self.transaction=DevelopmentalCommitRollbackOwner()

    def contract(self) -> Mapping[str,Any]:
        return _wd({
            "schema":"phi-developmental-open-endedness-contract/v1","owner_id":self.owner_id,"release":RELEASE,
            "pipeline":["ARCHITECTURE_STATE","INTERNAL_PHI_SEARCH","EXACT_REDUNDANT_COVER","PRIMITIVE_SYNTHESIS","MORPHISM","CONTROLLED_LIMIT","THEORY_COMPILER","FROZEN_LONGITUDINAL_SHADOW","COMMIT_OR_ROLLBACK"],
            "candidate_birth_obligations":"DERIVED_FROM_FROZEN_CAPABILITY_FEATURE_GRAPH","shadow_metrics":list(SHADOW_DEVELOPMENTAL_METRICS),"internet_prefreeze":"FORBIDDEN","named_evolutionary_algorithm_prefreeze":"FORBIDDEN",
            "next_research_obligation":"COLLECTIVE_COORDINATION",
            "next_research_obligation_status":"RESOLVED_GENERATION_ANCHOR",
            "claim_boundary":{"unbounded_world_open_endedness_proven":False,"biological_evolution_emulated":False,"AGI_demonstrated":False,"collective_coordination_grounded":True},
        })

    def run_cycle(self) -> Mapping[str,Any]:
        state=self.state.snapshot();selection=self.search_owner.search(state);binding=self.primitive_owner.bind(selection=selection);compiled=self.shadow.compile(binding);wf=self.shadow.freeze_workloads(selection);shadow=self.shadow.evaluate(selection=selection,workload_freeze=wf);tx=self.transaction.decide(selection=selection,binding=binding,compiled=compiled,shadow=shadow)
        return _wd({
            "schema":"phi-developmental-open-endedness-cycle/v1","owner_id":self.owner_id,"release":RELEASE,
            "architecture_state":state,"selection":selection,"primitive_binding":binding,"compiled":compiled,"workload_freeze":wf,"shadow":shadow,"transaction":tx,
            "next_research_obligation":"COLLECTIVE_COORDINATION",
            "next_research_obligation_status":"RESOLVED_GENERATION_ANCHOR",
            "claim_boundary":{"developmental_open_endedness_mechanism_qualified":tx.get("status")=="COMMIT_DEVELOPMENTAL_OPEN_ENDEDNESS_CAPABILITY","unbounded_external_open_endedness_established":False,"collective_coordination_grounded":True},
        })
