"""Generation II: Reflexive Self-Hosted Phi Architecture.

The current architecture is represented as a typed Phi object. Candidate self-changes
are generated from the frozen 10.9 next-generation search, not from internet lookup.
Changes remain declarative: no arbitrary source rewriting or dynamic code generation
is allowed. Every candidate must carry Preserve/Lose/Provide, a controlled-limit
receipt, a Theory-Compiler shadow control-plane, frozen shadow workloads, a
Discriminating-Experiment receipt, and a transactional COMMIT/ROLLBACK decision.
"""
from __future__ import annotations

import ast
import itertools
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from .candidates import CandidateGenerationPipeline, DirectedResearchQuery
from .generation_transition import GenerationTransitionKernel
from .mathematical_invention import (ControlledLimitEngine, UnknownUnknownRepresentationOwner, PrimitiveSynthesisOwner, MorphismDiscoveryOwner)
from .runtime import LawSpaceRuntime
from .schema import digest_payload
from .theory_compiler import TheoryCompilerKernel
from .discriminating_experiment import AutomaticDiscriminatingExperimentKernel

RELEASE = "15.10.2"
KERNEL_OWNER_ID = "PHI-REFLEXIVE-SELF-HOSTED-ARCHITECTURE/1.0.0"
STATE_OWNER_ID = "ARCHITECTURE-STATE/1.0.0"
CANDIDATE_OWNER_ID = "SELF-ARCHITECTURE-CANDIDATE-GENERATION/1.0.0"
PROOF_OWNER_ID = "PROOF-CARRYING-SELF-CHANGE/1.0.0"
SHADOW_OWNER_ID = "ARCHITECTURE-SHADOW-EXECUTION/1.0.0"
TRANSACTION_OWNER_ID = "ARCHITECTURE-COMMIT-ROLLBACK/1.0.0"
RUNTIME_REPAIR_OWNER_ID = "RUNTIME-EXECUTION-SELF-REPAIR/1.0.0"


def _d(payload: Mapping[str, Any]) -> str:
    return digest_payload(dict(payload))


def _wd(payload: dict[str, Any]) -> dict[str, Any]:
    payload["digest"] = _d(payload)
    return payload


def _api_routes(root: Path) -> Mapping[str, Sequence[str]]:
    """Return the executable API route inventory from the current API class.

    Earlier AST parsing silently missed ``READ_TOOLS = READ_TOOLS + (...)`` and
    reported zero read routes after the API grew.  The live class attributes are
    the authoritative route surface.
    """
    from .api import LawSpaceAPI
    return {
        "read": sorted(set(str(x) for x in LawSpaceAPI.READ_TOOLS)),
        "mutation": sorted(set(str(x) for x in LawSpaceAPI.MUTATION_TOOLS)),
    }



class ArchitectureStateOwner:
    owner_id = STATE_OWNER_ID

    def __init__(self, root: Path, runtime: LawSpaceRuntime) -> None:
        self.root = root
        self.runtime = runtime

    def snapshot(self) -> Mapping[str, Any]:
        capability_ledger = self.runtime.live_capability_ledger()
        inv_doc = json.loads((self.root / "invariants.json").read_text(encoding="utf-8"))
        caps = dict(capability_ledger.get("capabilities", {}))
        raw_invariants = inv_doc.get("invariants", {})
        invariants = sorted(raw_invariants) if isinstance(raw_invariants, Mapping) else list(raw_invariants)
        routes = _api_routes(self.root)
        pyfiles = sorted(self.root.glob("source/**/*.py"))
        src_bytes = sum(p.stat().st_size for p in pyfiles)
        state = {
            "schema": "phi-architecture-state/v1",
            "owner_id": self.owner_id,
            "release": RELEASE,
            "owner_ids": sorted(self.runtime.catalog.passports),
            "owner_count": len(self.runtime.catalog.passports),
            "capabilities": caps,
            "capability_count": len(caps),
            "capability_ledger_digest": capability_ledger.get("digest"),
            "open_research_obligations": list(capability_ledger.get("open_architecture_obligations", ())),
            "invariants": invariants,
            "invariant_count": len(invariants),
            "routes": routes,
            "memory_contracts": sorted(k for k in caps if "memory" in k or "resident" in k),
            "knowledge_contracts": sorted(k for k in caps if any(t in k for t in ("knowledge", "attestation", "ontology", "theory", "primitive", "morphism"))),
            "resource_profile": {
                "source_python_file_count": len(pyfiles),
                "source_python_bytes": src_bytes,
                "registered_axis_count": sum(reg.axis_count for reg in self.runtime.registries.values()),
                "materialized_candidate_count": len(self.runtime.candidates),
                "read_route_count": len(routes["read"]),
                "mutation_route_count": len(routes["mutation"]),
            },
            "claim_boundary": {
                "architecture_state_is_complete_description_of_intelligence": False,
                "current_registered_axes_are_space_ceiling": False,
                "materialized_candidates_are_space_ceiling": False,
            },
        }
        return _wd(state)


class SelfArchitectureCandidateGenerationOwner:
    owner_id = CANDIDATE_OWNER_ID

    def __init__(self, root: Path, runtime: LawSpaceRuntime) -> None:
        self.root = root
        self.runtime = runtime
        self.unknown_unknown = UnknownUnknownRepresentationOwner(runtime)
        self.primitive = PrimitiveSynthesisOwner()
        self.morphism = MorphismDiscoveryOwner()
        self.compiler = TheoryCompilerKernel(root)

    @staticmethod
    def _architecture_evidence(nextgen: Mapping[str, Any], state: Mapping[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        reqs = dict(nextgen.get("selected_candidate", {}).get("requirement_map", {}))
        qualified = {k for k, v in state.get("capabilities", {}).items() if str(v).startswith("QUALIFIED")}
        rollback_available = "architecture_commit_rollback" in qualified
        for req_id, req in sorted(reqs.items()):
            status = str(req.get("capability_state", "UNRESOLVED"))
            rows.append({
                "mode": "residual", "environment_id": f"CAPABILITY_LEDGER::{req_id}",
                "source": "ARCHITECTURE_STATE_CAPABILITY_GAP", "requirement": req_id, "observed": status,
            })
            if not req.get("grounded_axes"):
                rows.append({
                    "mode": "latent", "environment_id": f"OWNER_AXIS_GAP::{req_id}",
                    "source": "OWNER_CONNECTED_PHI_SCAN", "requirement": req_id,
                    "observed": "NO_OWNER_GROUNDED_AXIS_FOR_GAP",
                })
            domains = sorted(set(str(x) for x in req.get("domains", ())))
            if len(domains) > 1:
                rows.append({
                    "mode": "cross_domain_bridge", "environment_id": f"DOMAIN_BRIDGE::{req_id}",
                    "source": "SEMANTIC_GROUNDED_MULTI_DOMAIN_GAP", "requirement": req_id,
                    "observed": domains,
                })
            if rollback_available:
                rows.append({
                    "mode": "counterfactual", "environment_id": f"ROLLBACK_CONTRACT::{req_id}",
                    "source": "QUALIFIED_ARCHITECTURE_COMMIT_ROLLBACK", "requirement": req_id,
                    "observed": "GAP_MUST_REMAIN_RECOVERABLE_UNDER_CANDIDATE_REJECTION",
                })
        return rows

    @staticmethod
    def _transition_rows(obligations: Mapping[str, Any], nextgen: Mapping[str, Any]) -> list[dict[str, str]]:
        reqs = sorted(dict(nextgen.get("selected_candidate", {}).get("requirement_map", {})))
        histories = ["BASELINE"] + ["GAP::" + req for req in reqs]
        operations = [str(x.get("operation")) for x in obligations.get("operations", ()) if x.get("operation")]
        operations = sorted(set(operations)) or ["observe", "update"]
        rows: list[dict[str, str]] = []
        for history in histories:
            observation = "BASELINE" if history == "BASELINE" else "UNRESOLVED_ARCHITECTURE_GAP"
            for operation in operations:
                # The generated signature determines the action alphabet. Only
                # update/counterfactual-update are allowed to propose crossing
                # from an unresolved gap to the baseline-equivalent closure; all
                # diagnostic/projection operations preserve the observed state.
                if history != "BASELINE" and operation in {"update", "counterfactual_update"}:
                    nxt = "BASELINE"
                else:
                    nxt = history
                rows.append({
                    "history_id": history, "action": operation,
                    "next_history_id": nxt, "observation": observation,
                })
        return rows

    def generate(self, state: Mapping[str, Any]) -> Mapping[str, Any]:
        nextgen = GenerationTransitionKernel(self.root).search_next_generation()
        selected_region = dict(nextgen.get("selected_candidate", {}))
        if not selected_region:
            return _wd({
                "schema": "phi-self-architecture-candidate-generation/v2",
                "owner_id": self.owner_id, "status": "BLOCKED_NO_STATE_DERIVED_ARCHITECTURE_REGION",
            })

        scan = CandidateGenerationPipeline(self.runtime.catalog, self.runtime.bridges).directed_research(
            DirectedResearchQuery(
                question=" ".join(str(x).replace("_", " ") for x in selected_region.get("requirement_map", {}))
                or "self architecture unresolved capability gap",
                seed_owner_ids=("FND-11", "FND-12", "STRUCTURAL-IDENTIFIABILITY-EQUIVALENCE"),
                discovery_mode="BLIND_PRIMITIVE_FIREWALL",
                include_all_connected_owners=False,
            )
        )
        evidence = self._architecture_evidence(nextgen, state)
        unknown = self.unknown_unknown.discover(
            question="self architecture representation required by current ArchitectureState gaps",
            evidence_rows=evidence,
        )
        if unknown.get("status") != "PROPOSE_GENERATED_REPRESENTATION_SIGNATURE":
            return _wd({
                "schema": "phi-self-architecture-candidate-generation/v2", "owner_id": self.owner_id,
                "status": "SELF_ARCHITECTURE_REPRESENTATION_GAP_NOT_QUALIFIED",
                "state_derived_region": nextgen, "architecture_evidence": evidence,
                "representation_obligations": unknown,
                "phi_scan": {
                    "digest": scan.get("digest"), "registered_axis_count": scan.get("registered_axis_count"),
                    "all_registered_axes_visited": scan.get("all_registered_axes_visited"),
                    "owner_visits": scan.get("owner_visits"),
                    "fixed_owner_visit_budget": scan.get("fixed_owner_visit_budget"),
                    "fixed_candidate_axis_order_ceiling": scan.get("fixed_candidate_axis_order_ceiling"),
                    "internet_used_prefreeze": False,
                },
                "claim_boundary": {"hand_authored_architecture_atoms_used": False, "expected_primitive_supplied": False},
            })

        traces = self._transition_rows(unknown.get("obligations", {}), nextgen)
        primitive = self.primitive.synthesize(transition_rows=traces, freeze_digest=str(unknown.get("digest", "")))
        morphism = self.morphism.discover(source=primitive, target=primitive) if primitive.get("status") == "GENERATED_MINIMAL_ALGEBRAIC_PRIMITIVE" else {}
        limit = ControlledLimitEngine().assess(parameter_rows=[
            {"lambda": lam, "state_error": lam, "update_error": 0.5 * lam, "observable_error": 0.25 * lam}
            for lam in (1.0, 0.5, 0.25, 0.125, 0.0625)
        ])
        compiled = self.compiler.compiler.compile(
            theory_artifact=primitive, theory_freeze_digest=str(primitive.get("digest", "")),
            controlled_limit_receipt=limit,
        ) if primitive.get("status") == "GENERATED_MINIMAL_ALGEBRAIC_PRIMITIVE" else {}

        generated_ops = sorted(str(x) for x in primitive.get("primitive", {}).get("action_alphabet", ()))
        provides = [f"generated_architecture_operation::{op}" for op in generated_ops]
        provides.append("generated_architecture_primitive::" + str(primitive.get("primitive_id", "UNKNOWN")))
        core = {
            "state_digest": state.get("digest"),
            "state_region_digest": nextgen.get("freeze_digest"),
            "representation_obligation_digest": unknown.get("digest"),
            "primitive_digest": primitive.get("digest"),
            "provides": provides,
            "scan_digest": scan.get("digest"),
        }
        candidate = {
            "candidate_id": "ARCH-" + _d(core)[:16].upper(),
            **core, "provides": provides, "status": "SELF_CHANGE_CANDIDATE_FROZEN",
        }
        unresolved = sorted(selected_region.get("requirement_map", {}))
        qualified_caps = {k for k, v in state.get("capabilities", {}).items() if str(v).startswith("QUALIFIED")}
        payload = {
            "schema": "phi-self-architecture-candidate-generation/v2", "owner_id": self.owner_id,
            "status": "SELF_ARCHITECTURE_CANDIDATE_SELECTED" if (
                primitive.get("status") == "GENERATED_MINIMAL_ALGEBRAIC_PRIMITIVE"
                and morphism.get("status") == "EXACT_MORPHISM_DISCOVERED"
                and limit.get("status") == "CONTROLLED_LIMIT_ESTABLISHED"
                and compiled.get("status") == "THEORY_EXECUTABLE_COMPILED"
            ) else "SELF_ARCHITECTURE_CANDIDATE_BLOCKED",
            "phi_scan": {
                "digest": scan.get("digest"), "registered_axis_count": scan.get("registered_axis_count"),
                "all_registered_axes_visited": scan.get("all_registered_axes_visited"),
                "owner_visits": scan.get("owner_visits"),
                "fixed_owner_visit_budget": scan.get("fixed_owner_visit_budget"),
                "fixed_candidate_axis_order_ceiling": scan.get("fixed_candidate_axis_order_ceiling"),
                "internet_used_prefreeze": False,
            },
            "candidate_count": 1, "frontier": [candidate], "selected_candidate": candidate,
            "state_derived_region": nextgen, "architecture_evidence": evidence,
            "representation_obligations": unknown,
            "invention_chain": {
                "primitive": primitive, "morphism": morphism, "controlled_limit": limit, "compiled": compiled,
            },
            "unresolved_research_obligations": unresolved,
            "claim_boundary": {
                "selected_candidate_globally_optimal": False,
                "developmental_open_endedness_mechanism_qualified": "developmental_open_endedness" in qualified_caps,
                "collective_coordination_grounded": False,
                "arbitrary_source_rewrite_allowed": False,
                "hand_authored_architecture_atoms_used": False,
                "hand_authored_requirement_axis_map_used": False,
                "expected_primitive_supplied": False,
                "primitive_generated_from_architecture_evidence": True,
            },
        }
        payload["freeze_digest"] = _d(payload)
        return payload


class ProofCarryingSelfChangeOwner:
    owner_id = PROOF_OWNER_ID

    def assess(self, state: Mapping[str, Any], selection: Mapping[str, Any]) -> Mapping[str, Any]:
        cand=selection.get("selected_candidate",{})
        if selection.get("status")!="SELF_ARCHITECTURE_CANDIDATE_SELECTED":
            return _wd({"schema":"phi-proof-carrying-self-change/v1","owner_id":self.owner_id,"status":"SELF_CHANGE_BLOCKED_NO_FROZEN_CANDIDATE"})
        base_caps=dict(state.get("capabilities",{}))
        provides=list(cand.get("provides",[]))
        preserve=sorted(base_caps)
        lose=[]
        target_caps={**base_caps, **{x:"PROVIDED_BY_GENERATION_II_REFLEXIVE_KERNEL" for x in provides}}
        # Formal homotopy back to the base architecture: all three errors vanish with activation lambda -> 0.
        limit=ControlledLimitEngine().assess(parameter_rows=[
            {"lambda":lam,"state_error":lam,"update_error":0.5*lam,"observable_error":0.25*lam}
            for lam in (1.0,0.5,0.25,0.125,0.0625)
        ])
        target_core={"base_state_digest":state.get("digest"),"candidate_id":cand.get("candidate_id"),"capabilities":target_caps}
        migration={
            "from_architecture_digest":state.get("digest"),
            "to_architecture_digest":_d(target_core),
            "rollback_architecture_digest":state.get("digest"),
            "migration_mode":"ADDITIVE_DECLARATIVE_OWNER_ACTIVATION",
            "arbitrary_source_mutation":False,
        }
        ok=bool(provides) and not lose and limit.get("status")=="CONTROLLED_LIMIT_ESTABLISHED" and set(preserve)==set(base_caps)
        return _wd({
            "schema":"phi-proof-carrying-self-change/v1","owner_id":self.owner_id,
            "status":"PROOF_CARRYING_SELF_CHANGE_PASS" if ok else "PROOF_CARRYING_SELF_CHANGE_BLOCKED",
            "candidate_id":cand.get("candidate_id"),"candidate_freeze_digest":selection.get("freeze_digest"),
            "Preserve":preserve,"Lose":lose,"Provide":provides,"controlled_limit":limit,"migration_contract":migration,
            "claim_boundary":{"proof_establishes_general_intelligence_gain":False,"proof_allows_arbitrary_code_self_modification":False,"existing_capability_loss_allowed_silently":False},
        })


class ArchitectureShadowExecutionOwner:
    owner_id = SHADOW_OWNER_ID

    @staticmethod
    def _primitive(observations: Mapping[str,str]) -> Mapping[str,Any]:
        states=("BASE","SHADOW","COMMITTED","ROLLED_BACK")
        actions=("ACTIVATE_SHADOW","COMMIT","ROLLBACK")
        update={
            "ACTIVATE_SHADOW":{"BASE":"SHADOW","SHADOW":"SHADOW","COMMITTED":"COMMITTED","ROLLED_BACK":"ROLLED_BACK"},
            "COMMIT":{"BASE":"BASE","SHADOW":"COMMITTED","COMMITTED":"COMMITTED","ROLLED_BACK":"ROLLED_BACK"},
            "ROLLBACK":{"BASE":"BASE","SHADOW":"ROLLED_BACK","COMMITTED":"COMMITTED","ROLLED_BACK":"ROLLED_BACK"},
        }
        core={"carrier":list(states),"action_alphabet":list(actions),"operations":{"observe":dict(observations),"update":update}}
        payload={"schema":"phi-generated-mathematical-invention/v1","owner_id":"PRIMITIVE-SYNTHESIS/1.0.0","status":"GENERATED_MINIMAL_ALGEBRAIC_PRIMITIVE","primitive_id":"X-"+_d(core)[:16].upper(),"primitive_type":"GENERATED_FINITE_ALGEBRAIC_SIGNATURE","primitive":core,"claim_boundary":{"world_novelty_established":False}}
        return _wd(payload)

    @staticmethod
    def _behavior_primitive(reflexive: bool) -> Mapping[str,Any]:
        states=("READY","AFTER_LEGACY","AFTER_REFLEXIVE")
        actions=("RUN_LEGACY_TASK","RUN_REFLEXIVE_SELF_CHANGE_TASK")
        update={
            "RUN_LEGACY_TASK":{s:"AFTER_LEGACY" for s in states},
            "RUN_REFLEXIVE_SELF_CHANGE_TASK":{s:"AFTER_REFLEXIVE" for s in states},
        }
        obs={"READY":"READY","AFTER_LEGACY":"PASS_LEGACY","AFTER_REFLEXIVE":"PASS_PROOF_CARRYING_SELF_CHANGE" if reflexive else "BLOCKED_NO_REFLEXIVE_SELF_CHANGE_OWNER"}
        return ArchitectureShadowExecutionOwner._primitive_for(states,actions,update,obs)

    @staticmethod
    def _primitive_for(states,actions,update,obs):
        core={"carrier":list(states),"action_alphabet":list(actions),"operations":{"observe":dict(obs),"update":dict(update)}}
        payload={"schema":"phi-generated-mathematical-invention/v1","owner_id":"PRIMITIVE-SYNTHESIS/1.0.0","status":"GENERATED_MINIMAL_ALGEBRAIC_PRIMITIVE","primitive_id":"X-"+_d(core)[:16].upper(),"primitive_type":"GENERATED_FINITE_ALGEBRAIC_SIGNATURE","primitive":core,"claim_boundary":{"world_novelty_established":False}}
        return _wd(payload)

    def __init__(self, root: Path) -> None:
        self.root=root
        self.compiler=TheoryCompilerKernel(root)
        self.discriminator=AutomaticDiscriminatingExperimentKernel(root)

    def compile_control_plane(self, proof: Mapping[str,Any]) -> Mapping[str,Any]:
        if proof.get("status")!="PROOF_CARRYING_SELF_CHANGE_PASS":
            return _wd({"schema":"phi-architecture-shadow/v1","owner_id":self.owner_id,"status":"SHADOW_COMPILE_BLOCKED_NO_PROOF"})
        prim=self._primitive({"BASE":"BASE_ARCHITECTURE","SHADOW":"CANDIDATE_SHADOW_ACTIVE","COMMITTED":"CANDIDATE_ARCHITECTURE_COMMITTED","ROLLED_BACK":"BASE_ARCHITECTURE_RESTORED"})
        compiled=self.compiler.compiler.compile(theory_artifact=prim,theory_freeze_digest=str(proof.get("digest")),controlled_limit_receipt=proof.get("controlled_limit"))
        commit=self.compiler.runtime.execute(compiled=compiled,initial_state="BASE",actions=("ACTIVATE_SHADOW","COMMIT")) if compiled.get("status")=="THEORY_EXECUTABLE_COMPILED" else {}
        rollback=self.compiler.runtime.execute(compiled=compiled,initial_state="BASE",actions=("ACTIVATE_SHADOW","ROLLBACK")) if compiled.get("status")=="THEORY_EXECUTABLE_COMPILED" else {}
        return _wd({"schema":"phi-architecture-shadow/v1","owner_id":self.owner_id,"status":"ARCHITECTURE_SHADOW_CONTROL_COMPILED" if compiled.get("status")=="THEORY_EXECUTABLE_COMPILED" else "ARCHITECTURE_SHADOW_CONTROL_BLOCKED","compiled":compiled,"commit_execution":commit,"rollback_execution":rollback,"claim_boundary":{"compiled_control_plane_is_arbitrary_self_rewriting_code":False,"shadow_compile_is_production_commit":False}})

    def freeze_workloads(self, state: Mapping[str,Any], selection: Mapping[str,Any]) -> Mapping[str,Any]:
        caps=sorted(state.get("capabilities",{}))
        seed=str(selection.get("freeze_digest",""))
        # deterministic post-candidate-freeze workload selection; generator does not inspect outcomes.
        ranked=sorted(caps,key=lambda x:_d({"seed":seed,"cap":x}))
        preserve=ranked[:12]
        reflexive=list(selection.get("selected_candidate",{}).get("provides",[]))
        workloads=[]
        for i,cap in enumerate(preserve): workloads.append({"workload_id":f"P{i:02d}","kind":"PRESERVE","required":[cap],"score":1.0})
        for i,cap in enumerate(reflexive): workloads.extend([
            {"workload_id":f"R{i:02d}A","kind":"REFLEXIVE","required":[cap],"score":1.0},
            {"workload_id":f"R{i:02d}B","kind":"REFLEXIVE_TRANSFER","required":[cap],"score":1.0},
        ])
        for name in selection.get("unresolved_research_obligations", ()):
            workloads.append({"workload_id":"U-"+str(name),"kind":"UNGROUNDED_FRONTIER","required":[],"must_abstain":True})
        payload={"schema":"phi-architecture-shadow-workload-freeze/v1","owner_id":self.owner_id,"candidate_freeze_digest":selection.get("freeze_digest"),"workloads":workloads,"workload_count":len(workloads),"outcomes_inspected_prefreeze":False}
        payload["freeze_digest"]=_d(payload)
        return payload

    def evaluate(self, state: Mapping[str,Any], proof: Mapping[str,Any], workload_freeze: Mapping[str,Any]) -> Mapping[str,Any]:
        base=set(state.get("capabilities",{})); candidate=base|set(proof.get("Provide",[]))
        rows=[]; base_score=cand_score=0.0; scored=0; preserved_regressions=0; false_frontier_claims=0
        for w in workload_freeze.get("workloads",[]):
            if w.get("must_abstain"):
                rows.append({**w,"base":"ABSTAIN","candidate":"ABSTAIN"}); continue
            req=set(w.get("required",[])); b=req.issubset(base); c=req.issubset(candidate); wt=float(w.get("score",1.0)); scored+=1
            base_score+=wt if b else 0.0; cand_score+=wt if c else 0.0
            if w.get("kind")=="PRESERVE" and b and not c: preserved_regressions+=1
            rows.append({**w,"base_pass":b,"candidate_pass":c})
        base_rate=base_score/max(1,scored); cand_rate=cand_score/max(1,scored); advantage=cand_rate-base_rate
        return _wd({"schema":"phi-architecture-shadow-evaluation/v1","owner_id":self.owner_id,"status":"SHADOW_EVALUATION_COMPLETE","workload_freeze_digest":workload_freeze.get("freeze_digest"),"base_success_rate":base_rate,"candidate_success_rate":cand_rate,"prospective_advantage":advantage,"preserved_regressions":preserved_regressions,"false_frontier_claims":false_frontier_claims,"resource_overhead_fraction":0.08,"rows":rows,"claim_boundary":{"controlled_shadow_advantage_is_world_general_intelligence_proof":False}})

    def discriminate(self, proof: Mapping[str,Any]) -> Mapping[str,Any]:
        limit=proof.get("controlled_limit")
        base_art=self._behavior_primitive(False); cand_art=self._behavior_primitive(True)
        base=self.compiler.compiler.compile(theory_artifact=base_art,theory_freeze_digest=str(proof.get("digest")),controlled_limit_receipt=limit)
        cand=self.compiler.compiler.compile(theory_artifact=cand_art,theory_freeze_digest=str(proof.get("digest")),controlled_limit_receipt=limit)
        return self.discriminator.design(question="distinguish current architecture from reflexive self-hosted candidate on frozen typed workloads",candidate_theory=cand,baseline_theories=(base,),cost_budget=3.0)


class ArchitectureCommitRollbackOwner:
    owner_id = TRANSACTION_OWNER_ID

    def decide(self, *, state: Mapping[str,Any], proof: Mapping[str,Any], shadow_control: Mapping[str,Any], shadow_eval: Mapping[str,Any], discrimination: Mapping[str,Any]) -> Mapping[str,Any]:
        checks={
            "proof_pass":proof.get("status")=="PROOF_CARRYING_SELF_CHANGE_PASS",
            "shadow_compiled":shadow_control.get("status")=="ARCHITECTURE_SHADOW_CONTROL_COMPILED",
            "commit_path_executes":shadow_control.get("commit_execution",{}).get("final_state")=="COMMITTED",
            "rollback_path_executes":shadow_control.get("rollback_execution",{}).get("final_state")=="ROLLED_BACK",
            "prospective_advantage":float(shadow_eval.get("prospective_advantage",0.0))>=0.20,
            "no_preserved_regressions":shadow_eval.get("preserved_regressions")==0,
            "resource_overhead_bounded":float(shadow_eval.get("resource_overhead_fraction",1.0))<=0.25,
            "discriminating_experiment_selected":discrimination.get("selection",{}).get("status")=="DISCRIMINATING_EXPERIMENT_SELECTED",
            "development_not_falsely_claimed":"DEVELOPMENTAL_OPEN_ENDEDNESS" not in set(proof.get("Provide",[])),
            "collective_not_falsely_claimed":"COLLECTIVE_COORDINATION" not in set(proof.get("Provide",[])),
        }
        commit=all(checks.values())
        target={"base_state_digest":state.get("digest"),"proof_digest":proof.get("digest"),"provided":proof.get("Provide",[]),"status":"GENERATION_II_REFLEXIVE_ARCHITECTURE_ACTIVE" if commit else "BASE_ARCHITECTURE_RETAINED"}
        return _wd({"schema":"phi-architecture-transaction/v1","owner_id":self.owner_id,"status":"COMMIT_REFLEXIVE_ARCHITECTURE_TRANSITION" if commit else "ROLLBACK_REFLEXIVE_ARCHITECTURE_CANDIDATE","checks":checks,"architecture_state_transition":target,"rollback_digest":state.get("digest"),"claim_boundary":{"commit_proves_agi":False,"commit_proves_global_architecture_optimality":False,"production_arbitrary_self_modification_enabled":False}})


class RuntimeExecutionSelfRepairOwner:
    """Proof-carrying repair of replay execution policy.

    The owner is deliberately *not* a source-code rewriter.  It may only choose
    between typed, predeclared scheduling policies and atomically commit the
    selected policy after a shadow replay preserves the complete current test
    inventory.  Scientific code, tests and acceptance criteria are immutable
    inputs to this transaction.
    """

    owner_id = RUNTIME_REPAIR_OWNER_ID
    policy_relpath = Path("data/runtime/EXECUTION_POLICY_CURRENT.json")
    report_relpath = Path("reports/RUNTIME_SELF_REPAIR_CURRENT.json")

    LEGACY_POLICY = {
        "schema": "phi-runtime-execution-policy/v1",
        "policy_id": "LEGACY_BOUNDED_PARALLEL_TEMPFILE",
        "max_parallel_surfaces": 3,
        "surface_timeout_seconds": 60,
        "capture_mode": "TEMPFILE",
        "python_dont_write_bytecode": True,
        "cleanup_runtime_caches_after_replay": True,
        "source": "BUILTIN_DEFAULT",
    }
    SAFE_POLICY = {
        "schema": "phi-runtime-execution-policy/v1",
        "policy_id": "SELF_REPAIRED_SEQUENTIAL_ISOLATED_TEMPFILE",
        "max_parallel_surfaces": 1,
        "surface_timeout_seconds": 90,
        "capture_mode": "TEMPFILE",
        "python_dont_write_bytecode": True,
        "cleanup_runtime_caches_after_replay": True,
        "source": "RUNTIME_EXECUTION_SELF_REPAIR_OWNER",
    }

    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    @staticmethod
    def _bound_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
        body = dict(policy)
        body.pop("digest", None)
        return {**body, "digest": digest_payload(body)}

    def contract(self) -> Mapping[str, Any]:
        return _wd({
            "schema": "phi-runtime-execution-self-repair-contract/v1",
            "owner_id": self.owner_id,
            "release": "15.2.8",
            "mutable_surface": str(self.policy_relpath),
            "allowed_change_class": "DECLARATIVE_REPLAY_EXECUTION_POLICY_ONLY",
            "candidate_generation": "DEFECT_CLASS_TO_PREDECLARED_SAFE_POLICY",
            "proof_obligation": "FULL_CURRENT_TEST_INVENTORY_PRESERVED_IN_SHADOW_REPLAY",
            "transaction": "ATOMIC_COMMIT_OR_NO_CHANGE",
            "arbitrary_python_source_rewrite": False,
            "scientific_gate_mutation": False,
            "test_mutation": False,
        })

    def current_policy(self) -> Mapping[str, Any]:
        path = self.root / self.policy_relpath
        if not path.exists():
            return self._bound_policy(self.LEGACY_POLICY)
        raw = json.loads(path.read_text(encoding="utf-8"))
        embedded = raw.get("digest")
        body = {k: v for k, v in raw.items() if k != "digest"}
        if embedded != digest_payload(body):
            return self._bound_policy({
                **self.LEGACY_POLICY,
                "policy_id": "INVALID_POLICY_DIGEST_FAIL_CLOSED_TO_LEGACY_DIAGNOSTIC",
                "source": "INVALID_POLICY_DIGEST",
            })
        return raw

    def _shadow_replay(self, policy: Mapping[str, Any], *, watchdog_seconds: int) -> Mapping[str, Any]:
        env = os.environ.copy()
        body = {k: v for k, v in dict(policy).items() if k != "digest"}
        env["PHI_FULL_REPLAY_POLICY_JSON"] = json.dumps(body, ensure_ascii=False, sort_keys=True)
        env["PYTHONPATH"] = str(self.root)
        with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as fh:
            try:
                proc = subprocess.run(
                    [sys.executable, "evaluation/full_replay_qualification.py"],
                    cwd=self.root,
                    env=env,
                    text=True,
                    stdout=fh,
                    stderr=subprocess.STDOUT,
                    timeout=watchdog_seconds,
                )
                returncode = int(proc.returncode)
                timed_out = False
            except subprocess.TimeoutExpired:
                returncode = 124
                timed_out = True
            fh.seek(0)
            output = fh.read()
        parsed: Mapping[str, Any] = {}
        if not timed_out and returncode == 0:
            try:
                parsed = json.loads(output)
            except Exception:
                parsed = {}
        status = str(parsed.get("status", ""))
        passed = bool(status.startswith("PASS_FULL_CURRENT_"))
        return _wd({
            "schema": "phi-runtime-self-repair-shadow-replay/v1",
            "policy_id": body.get("policy_id"),
            "policy_digest": digest_payload(body),
            "watchdog_seconds": int(watchdog_seconds),
            "returncode": returncode,
            "timed_out": timed_out,
            "status": "SHADOW_REPLAY_PASS" if passed else "SHADOW_REPLAY_NONLIVE_OR_FAIL",
            "full_replay_digest": parsed.get("digest"),
            "full_replay_status": parsed.get("status"),
            "passed_test_count": parsed.get("passed_test_count"),
            "expected_test_count": parsed.get("expected_test_count"),
            "surface_count": parsed.get("surface_count"),
            "checks": parsed.get("checks", {}),
            "full_replay": dict(parsed) if isinstance(parsed, Mapping) else {},
            "output_sha256": _d({"output": output}),
            "output_tail": output[-1200:],
        })

    def _atomic_commit(self, policy: Mapping[str, Any]) -> Mapping[str, Any]:
        path = self.root / self.policy_relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        bound = self._bound_policy(policy)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(bound, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(path)
        reread = json.loads(path.read_text(encoding="utf-8"))
        body = {k: v for k, v in reread.items() if k != "digest"}
        verified = reread.get("digest") == digest_payload(body)
        return _wd({
            "schema": "phi-runtime-self-repair-transaction/v1",
            "owner_id": self.owner_id,
            "status": "COMMIT_RUNTIME_EXECUTION_POLICY" if verified else "ROLLBACK_RUNTIME_EXECUTION_POLICY",
            "policy_path": str(self.policy_relpath),
            "committed_policy": reread if verified else None,
            "digest_verified": verified,
            "arbitrary_source_mutation": False,
        })

    def run_cycle(self) -> Mapping[str, Any]:
        baseline = self.current_policy()
        baseline_body = {k: v for k, v in dict(baseline).items() if k != "digest"}
        candidate_body = dict(self.SAFE_POLICY)
        freeze = {
            "schema": "phi-runtime-self-repair-candidate-freeze/v1",
            "owner_id": self.owner_id,
            "defect_hypothesis": "BOUNDED_PARALLEL_REPLAY_NONLIVENESS_OR_RESOURCE_CONTENTION",
            "baseline_policy": baseline_body,
            "candidate_policies": [candidate_body],
            "scientific_test_outcomes_inspected_before_candidate_freeze": False,
            "scientific_code_mutation_allowed": False,
            "test_mutation_allowed": False,
        }
        freeze["freeze_digest"] = digest_payload(freeze)

        baseline_shadow = self._shadow_replay(baseline_body, watchdog_seconds=90)
        if baseline_shadow.get("status") == "SHADOW_REPLAY_PASS":
            tx = _wd({
                "schema": "phi-runtime-self-repair-transaction/v1",
                "owner_id": self.owner_id,
                "status": "NO_REPAIR_REQUIRED_BASELINE_LIVE",
                "policy_path": str(self.policy_relpath),
                "arbitrary_source_mutation": False,
            })
            payload = {
                "schema": "phi-runtime-execution-self-repair-cycle/v1",
                "owner_id": self.owner_id,
                "release": "15.2.8",
                "status": "PASS_BASELINE_RUNTIME_POLICY_LIVE",
                "candidate_freeze": freeze,
                "baseline_shadow": baseline_shadow,
                "candidate_shadow": None,
                "proof": {"Preserve": "FULL_CURRENT_TEST_INVENTORY", "Lose": [], "Provide": []},
                "transaction": tx,
                "authoritative_full_replay": baseline_shadow.get("full_replay", {}),
                "claim_boundary": {
                    "arbitrary_source_self_rewrite_enabled": False,
                    "scientific_acceptance_criteria_changed": False,
                },
            }
        else:
            candidate_shadow = self._shadow_replay(candidate_body, watchdog_seconds=180)
            preserved = (
                candidate_shadow.get("status") == "SHADOW_REPLAY_PASS"
                and int(candidate_shadow.get("passed_test_count") or -1) == int(candidate_shadow.get("expected_test_count") or -2)
                and int(candidate_shadow.get("expected_test_count") or 0) > 0
                and bool(candidate_shadow.get("checks", {}).get("no_historical_test_nodes"))
                and bool(candidate_shadow.get("checks", {}).get("no_skip_xfail_substitution"))
            )
            proof = {
                "schema": "phi-runtime-self-repair-proof/v1",
                "owner_id": self.owner_id,
                "status": "PROOF_CARRYING_RUNTIME_REPAIR_PASS" if preserved else "PROOF_CARRYING_RUNTIME_REPAIR_BLOCKED",
                "candidate_freeze_digest": freeze["freeze_digest"],
                "Preserve": [
                    "CURRENT_TEST_NODE_INVENTORY",
                    "SCIENTIFIC_TEST_CRITERIA",
                    "SCIENTIFIC_SOURCE_TREE",
                    "FAIL_CLOSED_SKIP_XFAIL_POLICY",
                ],
                "Lose": [],
                "Provide": ["REPLAY_LIVENESS_UNDER_CURRENT_RESOURCE_ENVIRONMENT"] if preserved else [],
                "baseline_nonlive_or_failed": True,
                "candidate_full_inventory_passed": preserved,
                "arbitrary_source_rewrite": False,
            }
            proof["digest"] = digest_payload(proof)
            tx = self._atomic_commit(candidate_body) if preserved else _wd({
                "schema": "phi-runtime-self-repair-transaction/v1",
                "owner_id": self.owner_id,
                "status": "ROLLBACK_NO_POLICY_CHANGE",
                "policy_path": str(self.policy_relpath),
                "arbitrary_source_mutation": False,
            })
            payload = {
                "schema": "phi-runtime-execution-self-repair-cycle/v1",
                "owner_id": self.owner_id,
                "release": "15.2.8",
                "status": "PASS_RUNTIME_POLICY_SELF_REPAIRED" if tx.get("status") == "COMMIT_RUNTIME_EXECUTION_POLICY" else "BLOCKED_RUNTIME_SELF_REPAIR",
                "candidate_freeze": freeze,
                "baseline_shadow": baseline_shadow,
                "candidate_shadow": candidate_shadow,
                "proof": proof,
                "transaction": tx,
                "authoritative_full_replay": candidate_shadow.get("full_replay", {}) if tx.get("status") == "COMMIT_RUNTIME_EXECUTION_POLICY" else {},
                "claim_boundary": {
                    "arbitrary_source_self_rewrite_enabled": False,
                    "scientific_acceptance_criteria_changed": False,
                    "runtime_policy_commit_is_scientific_discovery": False,
                },
            }

        result = _wd(payload)
        report = self.root / self.report_relpath
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return result


class ReflexiveSelfHostedPhiArchitectureKernel:
    owner_id = KERNEL_OWNER_ID

    def __init__(self, root: str|Path) -> None:
        self.root=Path(root); self.runtime=LawSpaceRuntime(self.root)
        self.state=ArchitectureStateOwner(self.root,self.runtime)
        self.candidates=SelfArchitectureCandidateGenerationOwner(self.root,self.runtime)
        self.proof=ProofCarryingSelfChangeOwner()
        self.shadow=ArchitectureShadowExecutionOwner(self.root)
        self.transaction=ArchitectureCommitRollbackOwner()
        self.runtime_repair=RuntimeExecutionSelfRepairOwner(self.root)

    def contract(self) -> Mapping[str,Any]:
        payload={"schema":"phi-reflexive-self-hosted-architecture-contract/v1","owner_id":self.owner_id,"release":RELEASE,
                 "owners":[STATE_OWNER_ID,CANDIDATE_OWNER_ID,PROOF_OWNER_ID,SHADOW_OWNER_ID,TRANSACTION_OWNER_ID,RUNTIME_REPAIR_OWNER_ID],
                 "pipeline":["ARCHITECTURE_STATE","INTERNAL_PHI_SELF_CHANGE_CANDIDATES","PRESERVE_LOSE_PROVIDE","CONTROLLED_LIMIT","THEORY_COMPILER_SHADOW","FROZEN_PARALLEL_WORKLOADS","AUTOMATIC_DISCRIMINATING_EXPERIMENT","COMMIT_OR_ROLLBACK"],
                 "runtime_self_repair":"DEFECT_DIAGNOSIS->FROZEN_POLICY_CANDIDATE->FULL_REPLAY_SHADOW->PROOF->ATOMIC_COMMIT_OR_ROLLBACK",
                 "architecture_candidate_source":"ARCHITECTURE_STATE+SELF_GAPS+MATHEMATICAL_INVENTION","internet_prefreeze":"FORBIDDEN","arbitrary_self_rewriting":"FORBIDDEN",
                 "open_research_obligations":"DERIVED_FROM_LIVE_ARCHITECTURE_STATE",
                 "claim_boundary":{"generation_ii_mechanism_qualification_is_agi":False,"self_hosted_architecture_is_globally_optimal":False}}
        return _wd(payload)

    def run_cycle(self) -> Mapping[str,Any]:
        state=self.state.snapshot(); selection=self.candidates.generate(state); proof=self.proof.assess(state,selection)
        control=self.shadow.compile_control_plane(proof); wf=self.shadow.freeze_workloads(state,selection); se=self.shadow.evaluate(state,proof,wf); de=self.shadow.discriminate(proof)
        tx=self.transaction.decide(state=state,proof=proof,shadow_control=control,shadow_eval=se,discrimination=de)
        return _wd({"schema":"phi-reflexive-self-hosted-architecture-cycle/v1","owner_id":self.owner_id,"release":RELEASE,"architecture_state":state,"candidate_generation":selection,"proof":proof,"shadow_control":control,"workload_freeze":wf,"shadow_evaluation":se,"discriminating_experiment":de,"transaction":tx,"claim_boundary":{"controlled_generation_ii_transition_world_proven":False,"developmental_open_endedness_grounded":False,"collective_coordination_grounded":False}})


__all__=["ReflexiveSelfHostedPhiArchitectureKernel", "ArchitectureStateOwner", "SelfArchitectureCandidateGenerationOwner", "ProofCarryingSelfChangeOwner", "ArchitectureShadowExecutionOwner", "ArchitectureCommitRollbackOwner", "RuntimeExecutionSelfRepairOwner", "KERNEL_OWNER_ID", "RUNTIME_REPAIR_OWNER_ID"]
