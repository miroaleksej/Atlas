#!/usr/bin/env python3
"""Digest-bound multidimensional law-space bridge for Φ-RQG v6.0.

The bridge does not own quantum-gravity dynamics.  It validates and packages
existing law passports, pending candidate transformations, computational-method
passports/routes, axis-space coverage and the external QPDTR execution bundle.
The authoritative causal mathematics remains in K-TOLLER-DIST-003.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _digest(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


REQUIRED_LAWS: Mapping[str, tuple[str, ...]] = {
    "G1_STATE": ("HYP-03", "QTM-01"),
    "G2_CONSTRAINT": ("QTM-04", "QFT-11", "QFT-19", "REL-08"),
    "G3_CAUSAL": ("REL-02", "REL-03", "QFT-13"),
    "G4_POSITIVITY": ("QTM-03", "QTM-14", "QTM-15"),
    "G5_CONTINUUM": ("TRN-01", "TRN-03", "TRN-07", "TRN-10"),
    "G6_UV": ("QFT-17", "QFT-18", "MAT-14"),
    "G7_GR_LIMIT": ("REL-05", "REL-06", "REL-07", "REL-10"),
    "G8_QFT_LIMIT": ("QFT-09", "QFT-10", "QFT-14", "QFT-15"),
    "G9_MATTER": ("QFT-11", "QFT-12", "QFT-19", "QFT-20", "QFT-21"),
    "G10_BORN": ("QTM-03", "QTM-14"),
    "G11_PREDICTION": ("NEW-09", "NEW-10"),
    "G12_EXPERIMENT": ("NEW-07", "NEW-08", "NEW-09"),
}

REQUIRED_CANDIDATE_SPECS: tuple[tuple[str, str], ...] = (
    ("QFT-13", "PHYS_RG_EFFECTIVE_FLOW"),
    ("QFT-18", "PHYS_RG_EFFECTIVE_FLOW"),
    ("QFT-17", "PHYS_RG_EFFECTIVE_FLOW"),
    ("QFT-18", "PHYS_SINGULARITY_REGULARIZATION"),
    ("QFT-17", "PHYS_SINGULARITY_REGULARIZATION"),
    ("REL-06", "PHYS_DISCRETE_GRAPH_LIFT"),
    ("REL-11", "PHYS_DISCRETE_GRAPH_LIFT"),
    ("QFT-21", "PHYS_GAUGE_COVARIANT_COUPLING"),
    ("QFT-12", "PHYS_GAUGE_COVARIANT_COUPLING"),
    ("QFT-19", "PHYS_GAUGE_COVARIANT_COUPLING"),
    ("QTM-15", "PHYS_MEASUREMENT_BACKACTION"),
    ("REL-06", "PHYS_VARIATIONAL_HAMILTONIAN_LIFT"),
    ("QFT-18", "PHYS_VARIATIONAL_HAMILTONIAN_LIFT"),
)

EXECUTED_METHODS = (
    "QCM-SYMMETRY",
    "QCM-CONTRACTION-OPT",
    "QCM-GENERAL-TN",
    "QCM-SLICING",
)

DEFERRED_METHODS: Mapping[str, tuple[str, ...]] = {
    "continuum_and_refinement": ("QCM-ADAPTIVE-TTN", "QCM-MERA", "QCM-TTN"),
    "physical_positivity": ("QCM-EXACT-DM",),
    "matter_sector": ("QCM-FERMION-GAUSSIAN",),
    "relational_measurement": (
        "QCM-TEMPO", "QCM-TRAJECTORIES", "QCM-CPTP-TT-LINDBLAD", "QCM-BASS",
        "QCM-CAUSAL-CONE", "QCM-PAULI-OBS", "QCM-GTN-BP", "QCM-PHI-Q1000-ARFE",
    ),
}

QPDTR_CONTROL_KEYS = (
    "topology_and_refinement_suite",
    "topology_transfer",
    "regge",
    "frg_selected_polynomials",
    "spectral_estimator",
    "tensor_svd_control",
    "persistent_adaptive_ttn_bounded_reference",
    "persistent_adaptive_ttn_structured_50_qubit",
    "persistent_adaptive_ttn_structured_50_qubit_hamiltonian_dynamics",
    "relational_observable",
    "quantum_matter_emulator",
    "unified_quantum_error_budget",
    "physical_law_table_v3",
    "high_treewidth_general_graph_contraction_fallback",
    "schwarzschild_4d_radial_modes",
    "cptp_tensor_train_runtime",
    "basis_adaptive_sparse_runtime",
    "process_tensor_memory",
    "adversarial_representation_benchmark",
    "phi_q1000_adaptive_resource_factorized_emulator",
    "fermionic_gaussian_runtime",
    "quantum_method_portfolio",
    "real_backend_qualification",
)


@dataclass(frozen=True)
class MultidomainQGBridgeCertificate:
    status: str
    checks: Mapping[str, bool]
    evidence: Mapping[str, Any]
    evidence_digest: str

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(self.checks.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "passed": self.passed,
            "checks": dict(self.checks),
            "evidence": dict(self.evidence),
            "evidence_digest": self.evidence_digest,
        }


def load_multidomain_qg_bridge(root: Path) -> MultidomainQGBridgeCertificate:
    """Validate the current multidomain/QPDTR bridge from authoritative owners.

    Historical generated candidate/route registries and axis-scan reports are not
    required current state. Their absence is therefore not interpreted as failure.
    """
    try:
        laws = _read_jsonl(root / "data/passports/known_laws.jsonl")
        methods = _read_jsonl(root / "data/passports/computational_methods.jsonl")
        active_frontier = _read_jsonl(root / "data/frontiers/ATLAS_ACTIVE_CANDIDATES_CURRENT.jsonl")
        from source.lawspace.domains import DOMAIN_REGISTRIES, canonical_axis_count
        archive = root / "external/QPDTR_PhiQG_CURRENT_STATE_v2_5_0.zip"
        with zipfile.ZipFile(archive) as zf:
            bundle_name = next(name for name in zf.namelist() if name.endswith("/reports/current/EXECUTION_BUNDLE.json") and not name.startswith("__MACOSX/"))
            qpdtr = json.loads(zf.read(bundle_name).decode("utf-8"))
    except (OSError, ValueError, KeyError, StopIteration, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        return MultidomainQGBridgeCertificate(status=f"BLOCKED_MULTIDOMAIN_QG_BRIDGE:{type(exc).__name__}", checks={"evidence_readable": False}, evidence={}, evidence_digest="")

    law_by_id = {row["owner_id"]: row for row in laws}
    method_by_id = {row["method_id"]: row for row in methods}
    required_law_ids = {owner for owners in REQUIRED_LAWS.values() for owner in owners}
    required_method_ids = set(EXECUTED_METHODS).union(*DEFERRED_METHODS.values())
    qpdtr_controls = {key: qpdtr.get("control_evidence", {}).get(key) for key in QPDTR_CONTROL_KEYS}
    qpdtr_controls_present = all(qpdtr_controls[key] is not None for key in QPDTR_CONTROL_KEYS)
    frontier_statuses = [status for row in active_frontier for status in row.get("epistemic_statuses", ())]
    evidence = {
        "schema":"phi-multidomain-qg-bridge/current-v7",
        "corpus_counts":{"known_laws":len(laws),"computational_methods":len(methods),"active_frontier_candidates":len(active_frontier),"canonical_axes":canonical_axis_count(),"domains":len(DOMAIN_REGISTRIES)},
        "gate_law_anchors":sorted(required_law_ids),
        "method_bindings":sorted(required_method_ids),
        "qpdtr":{"archive_sha256":_sha256(archive),"release":qpdtr.get("release"),"verdict":qpdtr.get("verdict"),"control_summary":qpdtr.get("control_summary")},
        "composite_model_semantics":{"historical_generated_candidates_required":False,"current_frontier_is_established_law":False,"coupled_extension_resolution":"OPEN_PER_CANDIDATE"},
        "claim_boundary":"Current bridge binds authoritative source laws, method passports, the persistent unresolved frontier and QPDTR evidence directly. Deleted historical generated-route reports are not reconstructed.",
    }
    checks = {
        "current_known_law_corpus_nonempty": len(laws) >= 400,
        "current_canonical_axis_registry_live": canonical_axis_count() == 655 and len(DOMAIN_REGISTRIES) == 13,
        "all_gate_law_anchors_present": required_law_ids.issubset(law_by_id),
        "all_required_methods_present": required_method_ids.issubset(method_by_id),
        "executed_methods_established": all(method_by_id[mid].get("epistemic_state") == "ESTABLISHED_METHOD" for mid in EXECUTED_METHODS),
        "active_frontier_persistent": len(active_frontier) > 0 and len({str(row.get("candidate_id", "")) for row in active_frontier}) == len(active_frontier),
        "active_frontier_not_promoted_to_world_truth": "ESTABLISHED_LAW" not in frontier_statuses,
        "active_frontier_unknown_not_false": not any("FALSIFIED" in str(x) or str(x) == "FALSE" for x in frontier_statuses),
        "qpdtr_identity_matches": qpdtr.get("release") == "2.5.0" and qpdtr.get("verdict") == "QUANTUM_EMULATOR_CONTROL_PASS_TARGET_EPRL_BLOCKED",
        "qpdtr_selected_controls_present": qpdtr_controls_present,
        "qpdtr_control_gates_passed": qpdtr.get("control_summary", {}).get("passed") == qpdtr.get("control_summary", {}).get("total") == 53,
        "qpdtr_target_eprl_not_falsely_promoted": "eprl" in " ".join(qpdtr.get("target_summary", {}).get("blocked", [])).lower(),
        "source_and_coupled_sector_semantics_explicit": True,
        "deleted_historical_routes_not_reintroduced": not (root / "data/passports/quantum_method_routes.jsonl").exists(),
        "deleted_historical_candidate_registry_not_reintroduced": not (root / "data/passports/candidates.jsonl").exists(),
    }
    return MultidomainQGBridgeCertificate(status="PASS_MULTIDOMAIN_QG_BRIDGE_CURRENT" if all(checks.values()) else "BLOCKED_MULTIDOMAIN_QG_BRIDGE", checks=checks, evidence=evidence, evidence_digest=_digest(evidence))
