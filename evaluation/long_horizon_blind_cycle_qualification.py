"""Qualification for the Long-Horizon Blind Scientific Cycle."""
from __future__ import annotations
import hashlib, json, tempfile
from pathlib import Path
from typing import Any, Mapping

from source.lawspace.long_horizon_scientific_cycle import LongHorizonBlindScientificCycleKernel
from source.lawspace.mathematical_invention import MathematicalInventionKernel
from source.lawspace.theory_compiler import TheoryCompilerKernel
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
      checks={
        "kernel_owner":kernel.contract()["owner_id"]=="PHI-LONG-HORIZON-BLIND-SCIENTIFIC-CYCLE/1.0.0",
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
      payload={"schema":SCHEMA,"release":RELEASE,"status":"PASS_PHI_LONG_HORIZON_BLIND_CYCLE_QUALIFICATION" if passed==len(checks) else "BLOCKED_PHI_LONG_HORIZON_BLIND_CYCLE_QUALIFICATION","passed":passed,"total":len(checks),"checks":[{"check":k,"status":"PASS" if v else "FAIL"} for k,v in checks.items()],"summary":{"epochs":32,"total_rounds":total_rounds,"identified_epochs":identifications,"representation_expansions":expansions,"heartbeat_count":state["heartbeat_count"],"theory_demotions":state["theory_demotions"],"state_digest":state["state_digest"]},"demonstration":{"first_epoch":epoch_summaries[0],"outside_control_epoch":epoch_summaries[7],"final_state":state},"claim_boundary":{"synthetic_qualification_is_world_discovery":False,"hidden_truth_revealed_to_solver_prefreeze":False,"internet_used_prefreeze":False}}
      payload["digest"]=digest_payload(payload); return payload

if __name__=="__main__": print(json.dumps(run_release_qualification(),ensure_ascii=False,indent=2,sort_keys=True))
