"""Offline universal execution qualification, including a fail-closed JHTDB case."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile

from source.lawspace.experiment_execution import SCHEMA, adapter_binding, sealed, sha256, verify
from source.lawspace.long_horizon_scientific_cycle import LongHorizonBlindScientificCycleKernel
from source.lawspace.measurement_adapters import LocalEvidenceArchive, TabularJSONMeasurement
from source.lawspace.theory_compiler import HierarchicalObservationalTheoryOwner

ROOT = Path(__file__).resolve().parents[1]


class ControlledOracle:
    adapter_id = "CONTROLLED-TABULAR-ORACLE/1"
    source_class = "FORWARD_ORACLE"
    source_id = "qualification-world"

    def preflight(self, contract):
        return []

    def acquire(self, request, *, idempotency_key=None):
        # Synthetic world only, not a real scientific discovery.
        if idempotency_key != "CONTROL-S1":
            raise ValueError("controlled intervention idempotency key mismatch")
        x = request["design"]
        return json.dumps({"units": {"x": "1", "y": "1"},
                           "columns": {"x": x, "y": [1 + 2 * v for v in x]}}).encode()


def control_contract(kernel, source, measurement):
    theory = HierarchicalObservationalTheoryOwner().compile(
        theory_id="EXECUTION-CONTROL", universal_layer={"relation": "linear"}, host_layer={"id": "synthetic"},
        regime_layer={"id": "controlled"}, feasible_domain_layer={"id": "finite"},
        competing_explanations=[{"id": "H1"}, {"id": "H2"}],
        predictions=[{"prediction": "frozen control", "falsification": "gate failure", "defense": "independent observations",
                      "heldout_refit_allowed": False}], evidence_digest="controlled-world-not-scientific-evidence",
        experimental_models=[{"experiment_id": "E1", "observable": "frozen-fit-compatibility", "cost": 1,
                              "predictions": {"H1": {"kind": "categorical", "value": "compatible"},
                                              "H2": {"kind": "categorical", "value": "incompatible"}}}])
    frozen = kernel.freeze_observational_round(theory=theory, cost_budget=1)
    return {"schema": SCHEMA, "experiment_id": "E1", "evidence_mode": "CONTROLLED_QUALIFICATION",
            "source": {"source_id": source.source_id, "class": source.source_class},
            "source_adapter": adapter_binding(source), "measurement_adapter": adapter_binding(measurement),
            "samples": [{"sample_id": "S1", "request_kind": "INTERVENTION", "idempotency_key": "CONTROL-S1",
                         "request": {"design": [0, 1, 2, 3]}}],
            "cases": [{"case_id": "C1", "sample_id": "S1", "observation_column": "y", "feature_columns": {"x": "x"},
                       "units": {"x": "1", "y": "1"}}],
            "forms": [{"form_id": "F1", "case_id": "C1", "kind": "LINEAR_FEATURES", "feature_ids": ["x"], "coefficients": [1, 2]}],
            "metric": {"name": "NRMSE_STD", "threshold": 0.05, "minimum_std": 1e-12},
            "transport": {"max_retries": 2, "backoff_seconds": 0, "max_bytes_per_sample": 10_000_000},
            "theory_revision": {"frozen_round": frozen, "outcomes": {"ALL_FORMS_PASS": "compatible", "SOME_FORMS_FAIL": "incompatible"}}}


def jhtdb_case(root=ROOT):
    from evaluation.jhtdb_execution_adapter import DNSFrozenMeasurement
    from evaluation.run_fresh_jhtdb_sgs_observational_experiment import validate_freezes
    reports = root / "reports/turbulence"
    protocol = json.loads((reports / "JHTDB_SGS_OBSERVATIONAL_PROTOCOL_FROZEN.json").read_text())
    child = json.loads((reports / "ATLAS_RANDOM20_SGS_CHILD_FORMS_FREEZE.json").read_text())
    acquisition = json.loads((reports / "JHTDB_SGS_FRESH_ACQUISITION_RECEIPT.json").read_text())
    proto = validate_freezes(protocol, child)
    verify(acquisition)
    if acquisition["protocol_digest"] != proto["digest"] or acquisition["child_forms_freeze_digest"] != child["digest"]:
        raise ValueError("legacy acquisition binding mismatch")
    source = LocalEvidenceArchive(root, proto["archive_id"])
    adapter = DNSFrozenMeasurement()
    contract = {"schema": SCHEMA, "experiment_id": "JHTDB-LEGACY-EXECUTION-QUALIFICATION",
                "evidence_mode": "RETROSPECTIVE_REPLAY", "source": {"class": source.source_class, "source_id": source.source_id},
                "source_adapter": adapter_binding(source), "measurement_adapter": adapter_binding(adapter),
                "samples": [], "cases": [], "forms": [],
                "metric": {"name": "NRMSE_STD", "threshold": 0.25, "minimum_std": 1e-12},
                "transport": {"max_retries": 0, "backoff_seconds": 0, "max_bytes_per_sample": 10_000_000},
                "legacy_protocol_digest": proto["digest"], "legacy_child_freeze_digest": child["digest"],
                "qualification_only": True}
    for sample in acquisition["samples"]:
        verify(sample)
        contract["samples"].append({"sample_id": sample["sample_id"], "request_kind": "NATURAL_SAMPLE",
                                    "expected_sha256": sample["npz_sha256"],
                                    "request": {"path": sample["npz_path"], "shape": sample["array_shape_xyz"]}})
        for ratio in sample["filter_ratios_frozen"]:
            for form in child["forms"]:
                cid = f'{sample["sample_id"]}:{ratio}:{form["component"]}'
                contract["cases"].append({"sample_id": sample["sample_id"], "case_id": cid, "filter_ratio": ratio,
                                          "component": form["component"], "chart": "COARSE_GRID_FINITE_STENCIL_R3",
                                          "grid_points": None,  # not specified in legacy child freeze: never invent it
                                          "axis_signatures": {x["axis_id"]: x["signature"] for x in form["selected_axes"]}})
                contract["forms"].append({"form_id": cid, "case_id": cid, "kind": "LINEAR_FEATURES",
                                          "feature_ids": [x["axis_id"] for x in form["selected_axes"]], "coefficients": form["parameters"]})
    return contract, source, adapter


def run(root=ROOT):
    kernel = LongHorizonBlindScientificCycleKernel(root)
    source, measurement = ControlledOracle(), TabularJSONMeasurement()
    contract = control_contract(kernel, source, measurement)
    freeze = kernel.observational_experiments.freeze_execution_protocol(contract, source_adapter=source, measurement_adapter=measurement)
    with tempfile.TemporaryDirectory(prefix="atlas-universal-") as state:
        result = kernel.execute_frozen_experiment(freeze, source_adapter=source, measurement_adapter=measurement, state_dir=state)
        replay = kernel.execute_frozen_experiment(freeze, source_adapter=source, measurement_adapter=measurement, state_dir=state)
    # A second source class and different measurement columns: same core.
    with tempfile.TemporaryDirectory(prefix="atlas-archive-control-") as directory:
        path = Path(directory) / "observation.json"
        path.write_text(json.dumps({"units": {"time": "s", "position": "m"},
                                    "columns": {"time": [0, 1, 2, 3], "position": [1, 3, 5, 7]}}))
        archive = LocalEvidenceArchive(directory, "synthetic-telemetry-archive")
        other = deepcopy(contract)
        other["source"] = {"class": archive.source_class, "source_id": archive.source_id}
        other["source_adapter"] = adapter_binding(archive)
        other["samples"] = [{"sample_id": "S1", "request_kind": "NATURAL_SAMPLE", "request": {"path": path.name},
                              "expected_sha256": sha256(path.read_bytes())}]
        other["cases"][0].update(observation_column="position", feature_columns={"x": "time"}, units={"time": "s", "position": "m"})
        f2 = kernel.observational_experiments.freeze_execution_protocol(other, source_adapter=archive, measurement_adapter=measurement)
        second = kernel.execute_frozen_experiment(f2, source_adapter=archive, measurement_adapter=measurement, state_dir=Path(directory)/"state")
    jc, js, jm = jhtdb_case(root)
    jf = kernel.observational_experiments.freeze_execution_protocol(jc, source_adapter=js, measurement_adapter=jm)
    with tempfile.TemporaryDirectory(prefix="atlas-jhtdb-preflight-") as state:
        jr = kernel.execute_frozen_experiment(jf, source_adapter=js, measurement_adapter=jm, state_dir=state)
    checks = {"forward_execution": result["evaluation"]["outcome"] == "ALL_FORMS_PASS",
              "archive_execution": second["evaluation"]["outcome"] == "ALL_FORMS_PASS",
              "checkpoint_replay_identical": result == replay,
              "theory_revision": result["theory_revision"]["status"] == "HIERARCHICAL_EXPLANATION_IDENTIFIED_POSTFREEZE",
              "jhtdb_incompatible_chart_blocked_before_targets": jr["status"] == "EXECUTION_BLOCKED_PREFLIGHT" and not jr["evidence_acquired"]}
    return sealed({"status": "PASS_UNIVERSAL_EXECUTION_QUALIFICATION" if all(checks.values()) else "FAIL_UNIVERSAL_EXECUTION_QUALIFICATION",
                   "checks": checks, "synthetic_forward": result, "synthetic_archive": second, "jhtdb": jr,
                   "jhtdb_case_count": len(jc["cases"]), "scientific_law_established": False})


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
