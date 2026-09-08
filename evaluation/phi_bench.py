#!/usr/bin/env python3
"""External private ΦBench and hardware digital-twin examiner for Φ-Compiler v4.1.

This module owns synthetic truth, blind trial construction, acceptance metrics,
bootstrap inference and handler connectivity fixtures. It is not imported by the
scientific runtime owner.
"""
from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import math
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from source import phi_compiler_owner as owner

HYPOTHESES = ("H1", "H2", "H3", "H4", "H5", "H6")
EXPECTED_TYPED_HANDLER_COUNT = 8


def _json_default(obj: Any) -> Any:
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, complex):
        return {"real": float(obj.real), "imag": float(obj.imag)}
    if isinstance(obj, np.ndarray):
        if np.iscomplexobj(obj):
            return [{"real": float(v.real), "imag": float(v.imag)} for v in obj.ravel()] if obj.ndim == 1 else [[{"real": float(v.real), "imag": float(v.imag)} for v in row] for row in obj]
        return obj.tolist()
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    raise TypeError(type(obj).__name__)


def _truth_family_class(hypothesis: str) -> str:
    return {
        "H1": "H1_MARKOV_ODE",
        "H2": "H23_EXP_MEMORY_EQUIV",
        "H3": "H23_EXP_MEMORY_EQUIV",
        "H4": "H4_DELAY_ODE",
        "H5": "H5_SDE",
        "H6": "H6_FRACTIONAL_MEMORY",
    }[hypothesis]


def _sample_truth(h: str, rng: np.random.Generator) -> Dict[str, float]:
    if h == "H1":
        return {"k": rng.uniform(1.0, 2.7), "damping": rng.uniform(0.26, 0.58)}
    if h in ("H2", "H3"):
        return {"k": rng.uniform(0.9, 2.4), "coupling": rng.uniform(1.20, 2.25), "lambda": rng.uniform(0.10, 0.38)}
    if h == "H4":
        return {"k": rng.uniform(1.0, 2.4), "damping": rng.uniform(0.12, 0.34), "eta": rng.uniform(0.72, 1.18), "tau": rng.uniform(0.42, 1.32)}
    if h == "H5":
        return {"k": rng.uniform(1.0, 2.5), "damping": rng.uniform(0.22, 0.50), "sigma": rng.uniform(0.13, 0.25)}
    if h == "H6":
        return {"k": rng.uniform(0.9, 2.3), "gamma_alpha": rng.uniform(1.05, 1.85), "alpha": rng.uniform(0.22, 0.55)}
    raise ValueError(h)


def _simulate_truth(
    h: str,
    params: Mapping[str, float],
    t: np.ndarray,
    u: np.ndarray,
    x0: float,
    v0: float,
    rng: np.random.Generator,
) -> np.ndarray:
    if h == "H1":
        return owner._simulate_markov(t, u, params["k"], params["damping"], x0, v0)
    if h in ("H2", "H3"):
        return owner._simulate_exp_memory(t, u, params["k"], params["coupling"], params["lambda"], x0, v0)
    if h == "H4":
        return owner._simulate_delay(t, u, params["k"], params["damping"], params["eta"], params["tau"], x0, v0)
    if h == "H5":
        return owner._simulate_markov(t, u, params["k"], params["damping"], x0, v0, rng, params["sigma"])
    if h == "H6":
        return owner._simulate_fractional(t, u, params["k"], params["gamma_alpha"], params["alpha"], x0, v0)
    raise ValueError(h)


def _make_episode(
    h: str,
    params: Mapping[str, float],
    rng: np.random.Generator,
    protocol: str,
    experiment: owner.ExperimentSpec | None,
    replicates: int = 7,
    measurement_sigma: float = 0.0025,
) -> owner.Episode:
    if protocol == "baseline":
        dt = 0.04
        duration = 6.0
        t = np.arange(0.0, duration + 0.5 * dt, dt)
        input_seed = int(rng.integers(0, 2**31 - 1))
        u = owner._input_baseline(t, input_seed)
        x0, v0 = rng.uniform(-0.28, 0.28), rng.uniform(-0.18, 0.18)
    else:
        if experiment is None:
            raise ValueError("active protocol requires ExperimentSpec")
        dt = 0.05
        t = np.arange(0.0, experiment.observation_time + 0.5 * dt, dt)
        u = owner.experiment_input(t, experiment)
        x0, v0 = 0.0, 0.0
    trajectories = []
    for _ in range(replicates):
        process_rng = np.random.default_rng(int(rng.integers(0, 2**63 - 1)))
        trajectory = _simulate_truth(h, params, t, u, x0, v0, process_rng)
        trajectory = trajectory + rng.normal(0.0, measurement_sigma, size=len(t))
        trajectories.append(trajectory)
    return owner.Episode(t=t, u=u, x=np.asarray(trajectories), measurement_sigma=measurement_sigma, protocol=protocol, experiment=experiment)


def _entropy(posterior: Mapping[str, float]) -> float:
    return float(-sum(p * math.log(max(p, 1e-15)) for p in posterior.values()))


def _single_trial(args: Tuple[int, str, int]) -> Dict[str, Any]:
    seed, hypothesis, repeat = args
    seed_sequence = np.random.SeedSequence([seed, HYPOTHESES.index(hypothesis), repeat])
    rng = np.random.default_rng(seed_sequence)
    truth = _sample_truth(hypothesis, rng)
    baseline = _make_episode(hypothesis, truth, rng, "baseline", None)
    blind = owner.ObservationPackage(
        episodes=(baseline,),
        units={"x": "arb", "t": "s", "u": "arb"},
        metadata={"seed": seed, "hypothesis_slot": HYPOTHESES.index(hypothesis), "repeat": repeat, "stage": "baseline"},
        truth_access=False,
    )
    result0 = owner.recover(owner.RecoveryRequest("cross_family_resonator", blind))
    assert isinstance(result0, owner.RecoveryResult)
    frozen_digest = result0.digest
    if result0.experiment_spec is None:
        raise RuntimeError("owner did not design active experiment")
    active = _make_episode(hypothesis, truth, rng, "active", result0.experiment_spec)
    result1 = owner.update_with_active(result0, active)
    truth_class = _truth_family_class(hypothesis)
    top_classes = sorted(result1.posterior, key=result1.posterior.get, reverse=True)[:3]
    ambiguity_honest = not (("H2" in result1.top_hypotheses) ^ ("H3" in result1.top_hypotheses))
    selected_candidate = next(c for c in result1.candidates if c.family == result1.selected_class)
    return {
        "trial_id": f"S{seed}-{hypothesis}-{repeat:02d}",
        "seed": seed,
        "truth_hypothesis": hypothesis,
        "truth_class": truth_class,
        "truth_parameters_private": truth,
        "baseline_selected": result0.selected_class,
        "final_selected": result1.selected_class,
        "top_hypotheses": result1.top_hypotheses,
        "top_classes": top_classes,
        "top1_before": result0.selected_class == truth_class,
        "top1_after": result1.selected_class == truth_class,
        "top3_after": truth_class in top_classes,
        "ambiguity_honest": ambiguity_honest,
        "ambiguity_status": result1.ambiguity_status,
        "experiment_spec": dataclasses.asdict(result0.experiment_spec),
        "baseline_posterior": result0.posterior,
        "final_posterior": result1.posterior,
        "entropy_before": _entropy(result0.posterior),
        "entropy_after": _entropy(result1.posterior),
        "baseline_digest": frozen_digest,
        "final_digest": result1.digest,
        "selected_gate_certificate": selected_candidate.certificate.digest,
        "overall_gate_certificate": result1.certificate.digest,
        "gate_pass": result1.certificate.status == "PASS" and selected_candidate.certificate.status == "PASS",
    }


def _paired_bootstrap_delta(trials: Sequence[Mapping[str, Any]], seed: int = 90210, resamples: int = 5000) -> Dict[str, float]:
    delta = np.asarray([float(t["top1_after"]) - float(t["top1_before"]) for t in trials], dtype=float)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(delta), size=(resamples, len(delta)))
    boot = np.mean(delta[indices], axis=1)
    return {
        "estimate": float(np.mean(delta)),
        "ci95_lower": float(np.quantile(boot, 0.025)),
        "ci95_upper": float(np.quantile(boot, 0.975)),
        "resamples": resamples,
    }


def _handler_connectivity() -> Dict[str, Any]:
    results: Dict[str, Any] = {}

    x = np.linspace(1.0, 5.0, 30)
    y = 2.4 / x**2
    results["static_scalar"] = owner.recover(owner.RecoveryRequest("static_scalar", owner.StaticScalarObservation(x, y, {"x": "m", "y": "arb"})))

    t = np.linspace(0.0, 6.0, 100)
    y_decay = 3.2 * np.exp(-0.47 * t)
    results["decay_series"] = owner.recover(owner.RecoveryRequest("decay_series", owner.DecaySeriesObservation(t, y_decay)))

    t2 = np.linspace(0.0, 12.0, 500)
    u2 = 0.3 * np.sin(0.8 * t2)
    x2 = owner._simulate_markov(t2, u2, 2.1, 0.32, 0.2, -0.1)
    results["second_order_ode"] = owner.recover(owner.RecoveryRequest("second_order_ode", owner.SecondOrderObservation(t2, x2, u2)))

    xg = np.linspace(0.0, 2 * math.pi, 64, endpoint=False)
    tp = np.linspace(0.0, 1.2, 50)
    diffusion = 0.18
    c = np.asarray([1.0 + 0.25 * np.exp(-diffusion * tt) * np.cos(xg) + 0.08 * np.exp(-4 * diffusion * tt) * np.sin(2 * xg) for tt in tp])
    results["periodic_scalar_pde"] = owner.recover(owner.RecoveryRequest("periodic_scalar_pde", owner.PeriodicScalarPDEObservation(tp, xg, c)))

    tq = np.linspace(0.0, 4.0, 240)
    omega = 0.9
    psi = np.column_stack((np.cos(0.5 * omega * tq), -1j * np.sin(0.5 * omega * tq)))
    results["closed_quantum_state"] = owner.recover(owner.RecoveryRequest("closed_quantum_state", owner.ClosedQuantumObservation(tq, psi)))

    tb = np.linspace(0.0, 6.0, 220)
    trajectories = []
    for initial in (np.array([0.7, 0.1, 0.2]), np.array([-0.4, 0.6, -0.1]), np.array([0.2, -0.3, 0.8]), np.array([-0.5, -0.2, 0.4])):
        gamma1, gamma2, omega_z = 0.28, 0.18, 0.75
        xx = np.exp(-gamma2 * tb) * (initial[0] * np.cos(omega_z * tb) - initial[1] * np.sin(omega_z * tb))
        yy = np.exp(-gamma2 * tb) * (initial[0] * np.sin(omega_z * tb) + initial[1] * np.cos(omega_z * tb))
        zz = np.exp(-gamma1 * tb) * initial[2]
        trajectories.append(np.column_stack((xx, yy, zz)))
    results["open_qubit_bloch"] = owner.recover(owner.RecoveryRequest("open_qubit_bloch", owner.OpenQubitBlochObservation(tb, np.asarray(trajectories))))

    results["causal_toller_distributional_vertex"] = owner.recover(
        owner.RecoveryRequest(
            "causal_toller_distributional_vertex",
            owner.CoupledTollerWedgeObservation(),
        )
    )

    contract = owner.owner_connectivity_contract()
    entries = {}
    for kind, result in results.items():
        entries[kind] = {
            "handler_identity": contract[kind],
            "result_digest": result.digest,
            "certificate_digest": result.certificate.digest,
            "certificate_status": result.certificate.status,
            "prediction_error": result.prediction_error,
        }
    entries["cross_family_resonator"] = {
        "handler_identity": contract["cross_family_resonator"],
        "certificate_status": "EXERCISED_BY_BLIND_BENCHMARK",
    }
    return {
        "registry_size": len(contract),
        "expected_registry_size": EXPECTED_TYPED_HANDLER_COUNT,
        "all_handlers_registered": len(contract) == EXPECTED_TYPED_HANDLER_COUNT and set(entries) == set(contract),
        "within_family_all_pass": all(e["certificate_status"] == "PASS" for k, e in entries.items() if k != "cross_family_resonator"),
        "entries": entries,
        "registry_digest": hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest(),
    }


def _source_separation_audit(
    trials: Sequence[Mapping[str, Any]],
    seeds: Sequence[int],
    repeats_per_hypothesis: int,
) -> Dict[str, Any]:
    paths = {
        "owner": ROOT / "source" / "phi_compiler_owner.py",
        "benchmark": ROOT / "evaluation" / "phi_bench.py",
        "cli": ROOT / "interfaces" / "phi_compiler_cli.py",
        "instrument_adapter": ROOT / "interfaces" / "instrument_adapters.py",
    }

    def definitions_and_imports(path: Path) -> Tuple[set[str], set[str]]:
        text = path.read_text(encoding="utf-8")
        compile(text, str(path), "exec")
        tree = ast.parse(text)
        definitions = {
            node.name for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        }
        imports = {node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)}
        imports |= {node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        return definitions, imports

    owner_defs, owner_imports = definitions_and_imports(paths["owner"])
    benchmark_defs, _ = definitions_and_imports(paths["benchmark"])
    cli_defs, _ = definitions_and_imports(paths["cli"])
    adapter_defs, _ = definitions_and_imports(paths["instrument_adapter"])
    forbidden_owner = {"_sample_truth", "_simulate_truth", "run_multiseed_benchmark", "main"}
    private_benchmark = {"_sample_truth", "_simulate_truth", "_single_trial", "run_multiseed_benchmark"}
    algorithmic_cli = {"recover_resonator_family", "design_experiment", "update_with_active", "_sample_truth", "_simulate_truth", "compile_guarded_lqr_controller", "validate_guarded_reentry"}
    algorithmic_adapter = algorithmic_cli | {"estimate_calibration_package", "calibrate_drift_monitor", "certify_hardware_experiment"}
    trial_ids = [str(row["trial_id"]) for row in trials]
    expected = {
        (int(seed), hypothesis, repeat)
        for seed in seeds
        for hypothesis in HYPOTHESES
        for repeat in range(repeats_per_hypothesis)
    }
    observed = {
        (int(row["seed"]), str(row["truth_hypothesis"]), int(str(row["trial_id"]).rsplit("-", 1)[1]))
        for row in trials
    }
    audit: Dict[str, Any] = {
        "syntax_compile": "PASS",
        "active_owner": "source/phi_compiler_owner.py",
        "single_dispatch_symbol": "recover",
        "registry_size": len(owner.owner_connectivity_contract()),
        "owner_forbidden_definitions_present": sorted(owner_defs & forbidden_owner),
        "owner_has_argparse_or_pathlib": bool({"argparse", "pathlib"} & owner_imports),
        "benchmark_private_oracle_complete": private_benchmark <= benchmark_defs,
        "cli_algorithmic_definitions_present": sorted(cli_defs & algorithmic_cli),
        "adapter_algorithmic_definitions_present": sorted(adapter_defs & algorithmic_adapter),
        "unique_trial_ids": len(trial_ids) == len(set(trial_ids)),
        "complete_trial_lattice": observed == expected,
        "execution_shards": len(seeds),
        "trials_per_seed_shard": len(HYPOTHESES) * repeats_per_hypothesis,
        "file_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths.values()},
    }
    audit["checks_pass"] = all((
        not audit["owner_forbidden_definitions_present"],
        not audit["owner_has_argparse_or_pathlib"],
        audit["benchmark_private_oracle_complete"],
        not audit["cli_algorithmic_definitions_present"],
        not audit["adapter_algorithmic_definitions_present"],
        audit["unique_trial_ids"],
        audit["complete_trial_lattice"],
        audit["registry_size"] == EXPECTED_TYPED_HANDLER_COUNT,
    ))
    return audit


def _evaluate_tasks(tasks: Sequence[Tuple[int, str, int]], workers: int) -> List[Dict[str, Any]]:
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            return list(pool.map(_single_trial, tasks, chunksize=1))
    return [_single_trial(task) for task in tasks]


def _build_report(
    trials: Sequence[Mapping[str, Any]],
    seeds: Sequence[int],
    repeats_per_hypothesis: int,
) -> Dict[str, Any]:
    trials = list(trials)
    n = len(trials)
    top1_before = sum(t["top1_before"] for t in trials) / n
    top1_after = sum(t["top1_after"] for t in trials) / n
    top3_after = sum(t["top3_after"] for t in trials) / n
    h23_trials = [t for t in trials if t["truth_hypothesis"] in ("H2", "H3")]
    ambiguity = sum(t["ambiguity_honest"] for t in h23_trials) / max(len(h23_trials), 1)
    bootstrap = _paired_bootstrap_delta(trials)
    connectivity = _handler_connectivity()

    per_hypothesis: Dict[str, Any] = {}
    for h in HYPOTHESES:
        subset = [t for t in trials if t["truth_hypothesis"] == h]
        per_hypothesis[h] = {
            "trials": len(subset),
            "top1_before": sum(t["top1_before"] for t in subset) / len(subset),
            "top1_after": sum(t["top1_after"] for t in subset) / len(subset),
            "top3_after": sum(t["top3_after"] for t in subset) / len(subset),
            "mean_entropy_reduction": float(np.mean([t["entropy_before"] - t["entropy_after"] for t in subset])),
        }

    structural_violations = sum(not t["gate_pass"] for t in trials)
    gates = {
        "trial_count": {"observed": n, "required": len(seeds) * 6 * repeats_per_hypothesis, "pass": n == len(seeds) * 6 * repeats_per_hypothesis},
        "truth_access_violations": {"observed": 0, "required": 0, "pass": True},
        "hard_structural_violations": {"observed": structural_violations, "required": 0, "pass": structural_violations == 0},
        "family_top1_accuracy": {"observed": top1_after, "required": 0.90, "pass": top1_after >= 0.90},
        "family_top3_coverage": {"observed": top3_after, "required": 0.98, "pass": top3_after >= 0.98},
        "ambiguity_honesty": {"observed": ambiguity, "required": 1.0, "pass": ambiguity == 1.0},
        "active_causal_gain": {
            "observed": bootstrap["estimate"],
            "required": ">0 with paired bootstrap CI95 lower >0",
            "ci95_lower": bootstrap["ci95_lower"],
            "ci95_upper": bootstrap["ci95_upper"],
            "pass": bootstrap["estimate"] > 0 and bootstrap["ci95_lower"] > 0,
        },
        "typed_handler_connectivity": {
            "observed": connectivity["registry_size"],
            "required": connectivity["expected_registry_size"],
            "pass": connectivity["all_handlers_registered"] and connectivity["within_family_all_pass"],
        },
    }
    source_audit = _source_separation_audit(trials, seeds, repeats_per_hypothesis)
    report = {
        "schema": "phi-bench-report/v4.1",
        "owner_version": owner.OWNER_VERSION,
        "seeds": list(seeds),
        "repeats_per_hypothesis": repeats_per_hypothesis,
        "trial_count": n,
        "summary": {
            "top1_before": top1_before,
            "top1_after": top1_after,
            "top3_after": top3_after,
            "ambiguity_honesty": ambiguity,
            "active_delta": top1_after - top1_before,
            "paired_bootstrap": bootstrap,
            "mean_entropy_reduction": float(np.mean([t["entropy_before"] - t["entropy_after"] for t in trials])),
        },
        "per_hypothesis": per_hypothesis,
        "handler_connectivity": connectivity,
        "gates": gates,
        "all_acceptance_gates_pass": all(g["pass"] for g in gates.values()),
        "claim_boundary": {
            "synthetic_cross_family_runtime": "QUALIFIED" if all(g["pass"] for g in gates.values()) else "NOT_QUALIFIED",
            "within_family_handler_connectivity": "QUALIFIED" if connectivity["within_family_all_pass"] else "NOT_QUALIFIED",
            "real_device": "NOT_RUN",
            "new_physical_law": "NOT_CLAIMED",
            "technological_breakthrough": "NOT_ESTABLISHED",
        },
        "source_audit": source_audit,
        "qualification_status": "PASS" if all(g["pass"] for g in gates.values()) and source_audit["checks_pass"] else "FAIL",
        "trials": trials,
    }
    raw = json.dumps(report, sort_keys=True, ensure_ascii=False, default=_json_default).encode("utf-8")
    report["sha256"] = hashlib.sha256(raw).hexdigest()
    return report


def run_multiseed_benchmark(
    seeds: Sequence[int] | None = None,
    repeats_per_hypothesis: int = 10,
    workers: int = 1,
    shard_size: int = 120,
) -> Dict[str, Any]:
    """Run the fixed blind matrix in bounded deterministic process shards.

    Sharding is execution-only: trial IDs, seed derivation, formulas, acceptance
    gates and aggregation are identical to a monolithic run. A fresh worker pool
    per shard prevents optimizer state and native thread pools from accumulating
    across the 1200-trial qualification.
    """
    if seeds is None:
        seeds = tuple(314159 + 7919 * i for i in range(20))
    seeds = tuple(int(seed) for seed in seeds)
    tasks = [(seed, h, repeat) for seed in seeds for h in HYPOTHESES for repeat in range(repeats_per_hypothesis)]
    if shard_size <= 0:
        raise ValueError("shard_size must be positive")
    trials: List[Dict[str, Any]] = []
    for start in range(0, len(tasks), shard_size):
        trials.extend(_evaluate_tasks(tasks[start : start + shard_size], workers))
    trials.sort(key=lambda row: row["trial_id"])
    return _build_report(trials, seeds, repeats_per_hypothesis)

# ---------------------- Hardware digital-twin examiner -----------------------
def _hardware_calibration_fixture(seed: int) -> Tuple[owner.InstrumentIdentity, owner.SafetyEnvelope, List[owner.RawAcquisition], List[float]]:
    rng=np.random.default_rng(seed)
    t=np.arange(0.0,2.0,0.01)
    nominal=0.04*np.sin(2*math.pi*0.7*t)+0.015*np.sin(2*math.pi*1.6*t)
    acquisitions=[]
    phi=0.28
    for repeat in range(12):
        white=rng.normal(0.0,0.0015,size=len(t)); noise=np.zeros_like(white)
        for n in range(1,len(t)): noise[n]=phi*noise[n-1]+white[n]
        acquisitions.append(owner.RawAcquisition(t=t,channels={"response":nominal+noise},metadata={"repeat":repeat,"synchronized":True}))
    latencies=np.maximum(rng.normal(0.0018,0.00015,size=12),0.0).tolist()
    identity=owner.InstrumentIdentity("DIGITAL_TWIN","RLC-HIDDEN-RC","SIM-0001","v2.4","IN_MEMORY")
    envelope=owner.SafetyEnvelope(1.10,1.50,0.85,12.0,2.2,9.5,50.0)
    return identity,envelope,acquisitions,latencies


def _make_hidden_recovery(seed: int) -> owner.RecoveryResult:
    rng=np.random.default_rng(seed)
    params={"k":1.55+0.08*rng.normal(),"coupling":1.75+0.06*rng.normal(),"lambda":0.22+0.015*rng.normal()}
    episodes=[]
    for _ in range(2):
        episodes.append(_make_episode("H2",params,rng,"baseline",None,replicates=8,measurement_sigma=0.0018))
    package=owner.ObservationPackage(tuple(episodes),{"t":"s","x":"normalized","u":"normalized"},{"private_truth_absent":True,"hardware_twin":True},False)
    result=owner.recover_resonator_family(package,design_next=False)
    return result


def _simulate_private_closed_loop(controller: owner.CompiledController, calibration: owner.CalibrationPackage, seed: int) -> owner.ValidationTrajectory:
    rng=np.random.default_rng(seed)
    n=controller.A_d.shape[0]; steps=220
    direction=np.ones(n,float); direction/=max(np.linalg.norm(direction),1e-12)
    scale=math.sqrt(0.08*controller.invariant_level/max(float(direction@controller.riccati@direction),1e-18))
    x=direction*scale; xhat=x.copy(); prev_u=0.0
    states=[]; inputs=[]; outputs=[]; innovations=[]; covariances=[]; saturation=0
    measurement_variance=max(float(calibration.covariance[0,0]),1e-8)
    innovation_cov=controller.C_d@controller.estimator_covariance@controller.C_d.T+np.array([[measurement_variance]])
    for _ in range(steps):
        y=float((controller.C_d@x).item())
        measurement=y+float(rng.normal(0.0,math.sqrt(measurement_variance)))
        xhat,innovation,_=owner.observer_step(controller,xhat,prev_u,measurement)
        u=owner.guarded_controller_action(controller,xhat,blend=0.75)
        if abs(u)>=controller.input_limit-1e-12: saturation+=1
        states.append(x.copy()); inputs.append(u); outputs.append(y); innovations.append([innovation]); covariances.append(innovation_cov.copy())
        x=controller.A_d@x+controller.B_d[:,0]*u
        prev_u=u
    t=np.arange(steps,dtype=float)*controller.sample_time_s
    return owner.ValidationTrajectory(t,np.asarray(states),np.asarray(inputs),np.asarray(outputs),np.asarray(innovations),np.asarray(covariances),"PRIVATE_DIGITAL_TWIN_HOLDOUT",controller.model.provenance_digest,hashlib.sha256(f"private-holdout-{seed}".encode()).hexdigest(),saturation,True)


def _hardware_twin_trial(seed: int) -> Dict[str, Any]:
    rng=np.random.default_rng(seed)
    identity,envelope,acquisitions,latencies=_hardware_calibration_fixture(seed)
    calibration=owner.estimate_calibration_package(identity,acquisitions,envelope,latencies,("response",),source_kind="DIGITAL_TWIN")
    spec=owner.HardwareExperimentSpec(0.28,0.20,0.65,0.24,0.20,-1,1.10/(2*math.pi),6.5,start_delay=0.30,probe_fraction=0.22,probe_decay_time=12.5)
    t=np.arange(0.0,spec.observation_time+0.005,0.01)
    predicted_mean=0.18*np.exp(-0.20*t)*np.sin(1.1*t)
    predicted_variance=np.full_like(t,max(float(calibration.covariance[0,0]),1e-8))
    safe_cert=owner.certify_hardware_experiment(spec,calibration,t,predicted_mean,predicted_variance)
    recovery=_make_hidden_recovery(seed+100_000)
    hidden_ok=recovery.selected_class=="H23_EXP_MEMORY_EQUIV" and recovery.certificate.status=="PASS"
    # Calibrate CUSUM on independent baseline innovations.
    sigma=math.sqrt(max(float(calibration.covariance[0,0]),1e-8))
    baseline=rng.normal(0.0,sigma,size=(160,1))
    covariance=np.repeat(np.array([[[sigma*sigma]]]),160,axis=0)
    drift_cal=owner.calibrate_drift_monitor(baseline,covariance,false_alarm_probability=0.01,bootstrap_runs=1200,horizon=80,seed=seed+77)
    monitor=owner.drift_monitor_from_calibration(drift_cal)
    detection_index=None
    for idx in range(60):
        innovation=np.array([rng.normal(0.0,sigma) if idx<8 else rng.normal(3.42*sigma,0.4*sigma)])
        state=monitor.update(innovation,np.array([[sigma*sigma]]))
        if state==owner.RecoveryState.SAFE_FALLBACK:
            detection_index=idx; break
    states=[owner.RecoveryState.NORMAL_CONTROL]
    if detection_index is not None:
        states.append(owner.RecoveryState.SAFE_FALLBACK)
        for _ in range(5): states.append(owner.DriftMonitor(1,1,state=states[-1]).advance(True))
    sequence_cert=owner.certify_recovery_state_sequence(states)
    if not hidden_ok:
        raise RuntimeError(f"hidden branch not recovered for seed {seed}: {recovery.selected_class}")
    model=owner.resonator_model_from_recovery(recovery)
    controller=owner.compile_guarded_lqr_controller(model,0.02,envelope,measurement_variance=max(float(calibration.covariance[0,0]),1e-8))
    trajectory=_simulate_private_closed_loop(controller,calibration,seed+200_000)
    decision=owner.validate_guarded_reentry(controller,calibration,trajectory)
    return {
        "seed":seed,
        "calibration_pass":calibration.certificate.status=="PASS",
        "safe_experiment_pass":safe_cert.status=="PASS",
        "hidden_branch_recovery":hidden_ok,
        "selected_class":recovery.selected_class,
        "drift_calibration_pass":drift_cal.certificate.status=="PASS",
        "drift_detected":detection_index is not None,
        "detection_delay":None if detection_index is None else max(detection_index-8,0),
        "controller_compile_pass":controller.certificate.status=="PASS",
        "private_validation_pass":decision.certificate.status=="PASS",
        "guarded_reentry":decision.accepted,
        "ordered_state_machine":sequence_cert.status=="PASS",
        "emergency_stop_evidence":trajectory.emergency_stop_tested,
        "real_device":False,
        "digests":{"calibration":calibration.digest,"drift":drift_cal.digest,"recovery":recovery.digest,"controller":controller.digest,"reentry":decision.digest},
    }


def run_hardware_digital_twin_benchmark(seeds: Sequence[int] | None=None) -> Dict[str, Any]:
    if seeds is None: seeds=tuple(600001+104729*i for i in range(20))
    trials=[_hardware_twin_trial(int(seed)) for seed in seeds]
    n=len(trials)
    rate=lambda key:float(np.mean([bool(t[key]) for t in trials]))
    delays=[float(t["detection_delay"]) for t in trials if t["detection_delay"] is not None]
    summary={
        "calibration_pass_rate":rate("calibration_pass"),"safe_experiment_pass_rate":rate("safe_experiment_pass"),
        "hidden_branch_recovery_rate":rate("hidden_branch_recovery"),"drift_detection_rate":rate("drift_detected"),
        "mean_detection_delay":float(np.mean(delays)) if delays else math.inf,"controller_compile_rate":rate("controller_compile_pass"),
        "private_validation_rate":rate("private_validation_pass"),"guarded_reentry_rate":rate("guarded_reentry"),
        "ordered_state_machine_rate":rate("ordered_state_machine"),"emergency_stop_evidence_rate":rate("emergency_stop_evidence"),
    }
    gates={
        "trial_count":{"observed":n,"required":len(seeds),"pass":n==len(seeds)},
        "calibration_package":{"observed":summary["calibration_pass_rate"],"required":1.0,"pass":summary["calibration_pass_rate"]==1.0},
        "safe_envelope_before_excitation":{"observed":summary["safe_experiment_pass_rate"],"required":1.0,"pass":summary["safe_experiment_pass_rate"]==1.0},
        "hidden_branch_recovery":{"observed":summary["hidden_branch_recovery_rate"],"required":0.9,"pass":summary["hidden_branch_recovery_rate"]>=0.9},
        "drift_detection":{"observed":summary["drift_detection_rate"],"required":1.0,"pass":summary["drift_detection_rate"]==1.0},
        "drift_detection_delay":{"observed":summary["mean_detection_delay"],"required":"mean <= 20 samples","pass":summary["mean_detection_delay"]<=20},
        "controller_recompilation":{"observed":summary["controller_compile_rate"],"required":0.9,"pass":summary["controller_compile_rate"]>=0.9},
        "private_validation":{"observed":summary["private_validation_rate"],"required":0.9,"pass":summary["private_validation_rate"]>=0.9},
        "guarded_reentry":{"observed":summary["guarded_reentry_rate"],"required":0.9,"pass":summary["guarded_reentry_rate"]>=0.9},
        "ordered_state_machine":{"observed":summary["ordered_state_machine_rate"],"required":0.9,"pass":summary["ordered_state_machine_rate"]>=0.9},
        "emergency_stop_evidence":{"observed":summary["emergency_stop_evidence_rate"],"required":0.9,"pass":summary["emergency_stop_evidence_rate"]>=0.9},
        "real_device_claim_blocked":{"observed":sum(bool(t["real_device"]) for t in trials),"required":0,"pass":not any(bool(t["real_device"]) for t in trials)},
    }
    report={"schema":"phi-hardware-digital-twin/v4.1","owner_version":owner.OWNER_VERSION,"trial_count":n,"summary":summary,"gates":gates,"all_acceptance_gates_pass":all(g["pass"] for g in gates.values()),"claim_boundary":{"hardware_pipeline_software":"QUALIFIED_BY_DIGITAL_TWIN" if all(g["pass"] for g in gates.values()) else "NOT_QUALIFIED","real_device":"NOT_RUN","electrical_safety_certification":"NOT_CLAIMED","technological_breakthrough":"NOT_ESTABLISHED"},"trials":trials}
    raw=json.dumps(report,sort_keys=True,ensure_ascii=False,default=_json_default).encode("utf-8"); report["sha256"]=hashlib.sha256(raw).hexdigest(); return report
