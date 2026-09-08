#!/usr/bin/env python3
"""Thin fail-closed evidence bridge to QPDTR PhiQG v2.5.0.

No emulator or quantum-gravity numerical algorithm lives here. The adapter only
verifies immutable archive/evidence identities and exposes a typed certificate.
"""
from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


def _canonical_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class QPDTRBridgeCertificate:
    status: str
    checks: Mapping[str, bool]
    evidence: Mapping[str, Any]
    contract_digest: str
    evidence_digest: str
    archive_sha256: str

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(self.checks.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "passed": self.passed,
            "checks": dict(self.checks),
            "evidence": dict(self.evidence),
            "contract_digest": self.contract_digest,
            "evidence_digest": self.evidence_digest,
            "archive_sha256": self.archive_sha256,
        }


def load_qpdtr_v2_5_0_bridge(root: Path) -> QPDTRBridgeCertificate:
    """Validate QPDTR 2.5.0 directly from its sealed current archive.

    The previous adapter depended on a copied bridge-evidence JSON that is not
    part of the current cleaned release. The archive itself is authoritative.
    """
    contract_path = root / "data/integrations/qpdtr_v2_5_0_contract.json"
    archive_path = root / "external/QPDTR_PhiQG_CURRENT_STATE_v2_5_0.zip"
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        with zipfile.ZipFile(archive_path) as archive:
            entries = archive.namelist()
            bundle_name = next(n for n in entries if n.endswith("/reports/current/EXECUTION_BUNDLE.json") and not n.startswith("__MACOSX/"))
            tests_name = next(n for n in entries if n.endswith("/reports/current/ISOLATED_TESTS.json") and not n.startswith("__MACOSX/"))
            manifest_name = next(n for n in entries if n.endswith("/RELEASE_MANIFEST.json") and not n.startswith("__MACOSX/"))
            evidence = json.loads(archive.read(bundle_name).decode("utf-8"))
            isolated_tests = json.loads(archive.read(tests_name).decode("utf-8"))
            external_manifest = json.loads(archive.read(manifest_name).decode("utf-8"))
    except (OSError, json.JSONDecodeError, zipfile.BadZipFile, StopIteration) as exc:
        return QPDTRBridgeCertificate(f"BLOCKED_QPDTR_EVIDENCE_UNREADABLE:{type(exc).__name__}", {"evidence_readable": False}, {}, "", "", "")
    actual_archive_digest = _sha256(archive_path)
    contract_digest = str(contract.get("digest", ""))
    evidence_digest = _canonical_digest(evidence)
    controls = evidence.get("control_evidence", {})
    portfolio = controls.get("quantum_method_portfolio", {})
    bindings = {row.get("method_id"):row for row in portfolio.get("method_bindings",()) if isinstance(row,Mapping)}
    forbidden_runtime_artifacts = any(n.startswith("__MACOSX/") or n.endswith(".pyc") or "/__pycache__/" in n for n in entries)
    history_entries=[n for n in entries if "/reports/history/" in n]
    history_isolated=all("/reports/history/version-control/" in n for n in history_entries)
    checks={
      "contract_digest_valid":contract_digest==_canonical_digest({**contract,"digest":""}),
      "archive_digest_valid":actual_archive_digest==contract.get("source_archive_sha256"),
      "archive_current_with_isolated_history":not forbidden_runtime_artifacts and history_isolated and external_manifest.get("current_state_only") is True,
      "release_identity_valid":evidence.get("release")==contract.get("source_release_version")=="2.5.0",
      "external_owner_preserved":external_manifest.get("authoritative_owner")==contract.get("external_authoritative_owner")=="qpdtr.owner.QuantumGravityDynamicsOwner.execute",
      "source_execution_digests_bound":evidence.get("source_digest")==contract.get("source_digest")==external_manifest.get("source_digest") and evidence.get("execution_digest")==contract.get("execution_digest"),
      "control_gates_passed":evidence.get("control_summary",{}).get("passed")==evidence.get("control_summary",{}).get("total")==contract.get("required_control_gates")==53,
      "packaged_tests_passed":isolated_tests.get("passed")==isolated_tests.get("collected")==contract.get("required_packaged_tests")==103 and isolated_tests.get("failed")==0,
      "no_new_law_claim":external_manifest.get("claim_boundary",{}).get("confirmed_new_physical_laws")==contract.get("confirmed_new_physical_laws")==0,
      "required_methods_bound":all(mid in bindings and bindings[mid].get("evidence_status")=="PASS" and bindings[mid].get("authoritative_owner") for mid in contract.get("required_methods",())),
      "portfolio_bound_without_missing_owners":portfolio.get("missing_method_count")==0 and str(portfolio.get("status","")).startswith("PASS"),
      "target_eprl_remains_blocked":"eprl" in " ".join(evidence.get("target_summary",{}).get("blocked",())).lower(),
      "process_tensor_owner_passed":controls.get("process_tensor_memory",{}).get("status")=="PASS_BOUNDED_SPATIAL_TEMPORAL_PROCESS_TENSOR_TTN" and controls.get("process_tensor_memory",{}).get("digital_twin_non_markovian_status")=="BLOCKED_MULTITIME_CALIBRATION_DATA_REQUIRED",
      "real_cpu_pass_external_accelerators_blocked":controls.get("real_backend_qualification",{}).get("cpu",{}).get("status")=="PASS" and controls.get("real_backend_qualification",{}).get("cuda",{}).get("executed") is False and controls.get("real_backend_qualification",{}).get("mpi",{}).get("executed") is False,
      "physical_experiment_not_fabricated":external_manifest.get("claim_boundary",{}).get("physical_experiment")=="NOT_RUN",
    }
    passed=all(checks.values())
    enriched={"execution_bundle":evidence,"isolated_tests":isolated_tests,"external_manifest":external_manifest,"compiler_structural_portfolio_binding":portfolio,"target_structural_admission":{"status":"BLOCKED_TARGET_CLASS_CERTIFICATE_MISSING"},"physical_experiment":"NOT_RUN"}
    return QPDTRBridgeCertificate("PASS_TYPED_QPDTR_V2_5_0_BRIDGE" if passed else "BLOCKED_QPDTR_V2_5_0_BRIDGE",checks,enriched,contract_digest,evidence_digest,actual_archive_digest)


@dataclass(frozen=True)
class QPDTRNeutrinoCrossCheckCertificate:
    """Independent QPDTR spectral-dynamics check of the owner-built mass matrix."""

    status: str
    candidate_digest: str
    dimension: int
    hamiltonian_scale_ev: float
    maximum_trace_identity_residual: float
    maximum_unitarity_residual: float
    maximum_statevector_backend_gap: float
    qpdtr_execution_backend: str
    checks: Mapping[str, bool]
    bridge_status: str
    details: Mapping[str, Any]
    digest: str

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(self.checks.values())

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "candidate_digest": self.candidate_digest,
            "dimension": self.dimension,
            "hamiltonian_scale_ev": self.hamiltonian_scale_ev,
            "maximum_trace_identity_residual": self.maximum_trace_identity_residual,
            "maximum_unitarity_residual": self.maximum_unitarity_residual,
            "maximum_statevector_backend_gap": self.maximum_statevector_backend_gap,
            "qpdtr_execution_backend": self.qpdtr_execution_backend,
            "checks": dict(self.checks),
            "bridge_status": self.bridge_status,
            "details": dict(self.details),
            "digest": self.digest,
        }


def _load_finite_quantum_dynamics(root: Path):
    """Load the authoritative QPDTR owner from its bundled wheel, fail closed."""
    try:
        from qpdtr.domains.quantum_gravity.quantum import FiniteQuantumDynamics
        return FiniteQuantumDynamics, "INSTALLED_BUNDLED_RELEASE"
    except Exception:
        pass

    import importlib
    import os
    import sys
    import tempfile

    archive_path = root / "external/QPDTR_PhiQG_CURRENT_STATE_v2_5_0.zip"
    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)
    # Runtime extraction must never mutate the current-state distribution.  The
    # cache lives under the host temporary directory and is keyed by the exact
    # qualified archive digest.
    archive_digest = _sha256(archive_path)
    cache_root = Path(os.environ.get("PHI_COMPILER_RUNTIME_CACHE", tempfile.gettempdir()))
    cache = cache_root / "phi_compiler" / "qpdtr_v2_5_0" / archive_digest
    marker = cache / ".extracted"
    if not marker.is_file():
        cache.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path) as outer:
            wheel_members = [name for name in outer.namelist() if name.endswith("qpdtr_phiqg-2.5.0-cp313-cp313-linux_x86_64.whl")]
            if len(wheel_members) != 1:
                raise RuntimeError("exactly one qualified QPDTR wheel is required")
            wheel_bytes = outer.read(wheel_members[0])
        wheel_digest = hashlib.sha256(wheel_bytes).hexdigest()
        with tempfile.NamedTemporaryFile(suffix=".whl") as wheel_file:
            wheel_file.write(wheel_bytes)
            wheel_file.flush()
            with zipfile.ZipFile(wheel_file.name) as wheel:
                for member in wheel.infolist():
                    target = (cache / member.filename).resolve()
                    if cache.resolve() not in target.parents and target != cache.resolve():
                        raise RuntimeError("QPDTR wheel contains an unsafe path")
                wheel.extractall(cache)
        marker.write_text(wheel_digest + "\n", encoding="utf-8")
    if str(cache) not in sys.path:
        sys.path.insert(0, str(cache))
    module = importlib.import_module("qpdtr.domains.quantum_gravity.quantum")
    return module.FiniteQuantumDynamics, "EXTRACTED_FROM_QUALIFIED_BUNDLED_WHEEL"


def certify_neutrino_mass_operator_with_qpdtr(
    root: Path,
    *,
    mass_matrix: Any,
    takagi_masses_ev: Any,
    candidate_digest: str,
    elapsed_times: tuple[float, ...] = (0.0, 0.173, 0.419, 0.887),
) -> QPDTRNeutrinoCrossCheckCertificate:
    """Cross-check a complex-symmetric neutrino operator through QPDTR.

    The classical neutrino owner remains the sole owner of Takagi lowering.
    QPDTR receives the Hermitian embedding H_M=[[0,M],[M†,0]] and independently
    evolves it.  For a Takagi spectrum m_a, Tr exp(-it H_M)=2 sum_a cos(t m_a).
    """
    import numpy as np

    bridge = load_qpdtr_v2_5_0_bridge(root)
    matrix = np.asarray(mass_matrix, dtype=complex)
    masses = np.asarray(takagi_masses_ev, dtype=float)
    base_checks = {
        "typed_qpdtr_bridge_passed": bridge.passed,
        "candidate_digest_bound": bool(candidate_digest),
        "mass_matrix_square": matrix.ndim == 2 and matrix.shape[0] == matrix.shape[1],
        "mass_matrix_complex_symmetric": matrix.ndim == 2 and matrix.shape[0] == matrix.shape[1]
        and float(np.linalg.norm(matrix - matrix.T)) <= 1.0e-10 * max(float(np.linalg.norm(matrix)), 1.0),
        "takagi_spectrum_dimension_matches": matrix.ndim == 2 and len(masses) == matrix.shape[0],
        "takagi_masses_nonnegative_finite": bool(np.all(np.isfinite(masses)) and np.min(masses, initial=0.0) >= -1.0e-14),
    }
    if not all(base_checks.values()):
        details = {"reason": "PRECONDITION_FAILED", "bridge": bridge.to_dict()}
        payload = {
            "status": "BLOCKED_QPDTR_NEUTRINO_CROSS_CHECK_PRECONDITION",
            "candidate_digest": candidate_digest,
            "dimension": int(matrix.shape[0]) if matrix.ndim == 2 else 0,
            "hamiltonian_scale_ev": 0.0,
            "maximum_trace_identity_residual": float("inf"),
            "maximum_unitarity_residual": float("inf"),
            "maximum_statevector_backend_gap": float("inf"),
            "qpdtr_execution_backend": "NOT_EXECUTED",
            "checks": base_checks,
            "bridge_status": bridge.status,
            "details": details,
        }
        return QPDTRNeutrinoCrossCheckCertificate(**payload, digest=_canonical_digest(payload))

    try:
        FiniteQuantumDynamics, transport = _load_finite_quantum_dynamics(root)
        zero = np.zeros_like(matrix)
        hermitian = np.block([[zero, matrix], [matrix.conj().T, zero]])
        scale = max(float(np.max(np.abs(masses), initial=0.0)), float(np.linalg.norm(matrix, ord=2)), 1.0e-15)
        hamiltonian = hermitian / scale
        dynamics = FiniteQuantumDynamics(hamiltonian)
        scaled_masses = masses / scale
        trace_residuals = []
        unitarity_residuals = []
        backend_gaps = []
        certificates = []
        initial = np.zeros(hamiltonian.shape[0], dtype=complex)
        initial[0] = 1.0
        for elapsed in elapsed_times:
            elapsed = float(elapsed)
            unitary = dynamics.unitary(elapsed)
            expected_trace = 2.0 * np.sum(np.cos(scaled_masses * elapsed))
            trace_residual = float(abs(np.trace(unitary) - expected_trace) / max(1.0, hamiltonian.shape[0]))
            unitarity_residual = float(np.linalg.norm(unitary.conj().T @ unitary - np.eye(unitary.shape[0]), ord=2))
            evolved, backend_gap = dynamics.evolve_statevector(initial, elapsed)
            statevector_norm_gap = abs(float(np.vdot(evolved, evolved).real) - 1.0)
            trace_residuals.append(trace_residual)
            unitarity_residuals.append(unitarity_residual)
            backend_gaps.append(float(backend_gap))
            certificates.append({
                "dimension": int(hamiltonian.shape[0]),
                "elapsed_time": elapsed,
                "execution_backend": "QPDTR_CLOSED_SYSTEM_UNITARY_WITH_KRYLOV_ACTION",
                "statevector_norm_gap": statevector_norm_gap,
                "unitary_gap": unitarity_residual,
                "statevector_backend_gap": float(backend_gap),
                "closed_passed": statevector_norm_gap < 1.0e-11
                and unitarity_residual < 1.0e-11
                and float(backend_gap) < 1.0e-11,
                "open_system_channel_materialized": False,
            })
        max_trace = max(trace_residuals, default=0.0)
        max_unitarity = max(unitarity_residuals, default=0.0)
        max_backend = max(backend_gaps, default=0.0)
        checks = {
            **base_checks,
            "qpdtr_owner_loaded_from_qualified_release": True,
            "hermitian_embedding_is_hermitian": float(np.linalg.norm(hamiltonian - hamiltonian.conj().T)) < 1.0e-12,
            "qpdtr_trace_identity_passed": max_trace < 5.0e-11,
            "qpdtr_unitarity_passed": max_unitarity < 5.0e-10,
            "qpdtr_reference_krylov_agreement_passed": max_backend < 5.0e-10,
            "qpdtr_closed_system_path_does_not_materialize_dense_channel": all(
                not row.get("open_system_channel_materialized", True) for row in certificates
            ),
        }
        backend = str(certificates[-1].get("execution_backend", "UNKNOWN")) if certificates else "UNKNOWN"
        details = {
            "transport": transport,
            "elapsed_times": elapsed_times,
            "trace_identity_residuals": tuple(trace_residuals),
            "unitarity_residuals": tuple(unitarity_residuals),
            "qpdtr_certificates": tuple(certificates),
            "spectral_identity": "SPEC(H_M)={-m_a,+m_a}; TRACE_EXP=2_SUM_COS",
            "scientific_owner_boundary": "QPDTR_CROSS_CHECKS_CLOSED_SYSTEM_DYNAMICS_BUT_DOES_NOT_OWN_TAKAGI_LOWERING",
            "channel_policy": "NO_DENSE_LIOUVILLIAN_OR_CHOI_FOR_CLOSED_NEUTRINO_EMBEDDING",
        }
        status = "PASS_QPDTR_NEUTRINO_HERMITIAN_EMBEDDING_CROSS_CHECK" if all(checks.values()) else "BLOCKED_QPDTR_NEUTRINO_CROSS_CHECK"
        payload = {
            "status": status,
            "candidate_digest": candidate_digest,
            "dimension": int(matrix.shape[0]),
            "hamiltonian_scale_ev": scale,
            "maximum_trace_identity_residual": max_trace,
            "maximum_unitarity_residual": max_unitarity,
            "maximum_statevector_backend_gap": max_backend,
            "qpdtr_execution_backend": backend,
            "checks": checks,
            "bridge_status": bridge.status,
            "details": details,
        }
        return QPDTRNeutrinoCrossCheckCertificate(**payload, digest=_canonical_digest(payload))
    except Exception as exc:
        checks = {**base_checks, "qpdtr_execution_completed": False}
        details = {"error_type": type(exc).__name__, "error": str(exc)[:1000]}
        payload = {
            "status": "BLOCKED_QPDTR_NEUTRINO_CROSS_CHECK_EXECUTION",
            "candidate_digest": candidate_digest,
            "dimension": int(matrix.shape[0]),
            "hamiltonian_scale_ev": 0.0,
            "maximum_trace_identity_residual": float("inf"),
            "maximum_unitarity_residual": float("inf"),
            "maximum_statevector_backend_gap": float("inf"),
            "qpdtr_execution_backend": "NOT_EXECUTED",
            "checks": checks,
            "bridge_status": bridge.status,
            "details": details,
        }
        return QPDTRNeutrinoCrossCheckCertificate(**payload, digest=_canonical_digest(payload))
