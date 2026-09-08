#!/usr/bin/env python3
"""External physical-stand examiner for Φ-Compiler v4.1.

Scientific and safety decisions remain in source.phi_compiler_owner. This module
loads the controlled stand contract, executes deterministic prebuild/tolerance
qualification, validates adapter command sequencing in memory, and provides a
fail-closed real-device acquisition workflow. Network SCPI is never accepted as
a real-time feedback backend.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import time
from itertools import product
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np

from interfaces.instrument_adapters import InstrumentTransportError, RedPitayaSCPIAdapter
from source import phi_compiler_owner as owner


def _json_default(obj: Any) -> Any:
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, complex):
        return {"real": float(obj.real), "imag": float(obj.imag)}
    raise TypeError(type(obj).__name__)


def _finish(report: Dict[str, Any]) -> Dict[str, Any]:
    """Return a fully JSON-safe, digest-bound report.

    The real-device path can contain NumPy arrays and dataclasses. Normalizing
    before hashing prevents CLI-specific stringification and guarantees that the
    persisted report has exactly the payload covered by its SHA-256 digest.
    """
    normalized = json.loads(json.dumps(report, ensure_ascii=False, default=_json_default))
    normalized.pop("sha256", None)
    raw = json.dumps(normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    normalized["sha256"] = hashlib.sha256(raw).hexdigest()
    return normalized


def load_stand_contract(path: str | Path) -> Tuple[Mapping[str, Any], owner.PhysicalStandProfile, owner.SafetyEnvelope, owner.HardwareExperimentSpec]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if raw.get("schema") != "phi-physical-stand/v2.4":
        raise ValueError("Unsupported physical stand schema")
    profile = owner.PhysicalStandProfile(**raw["stand"])
    envelope = owner.SafetyEnvelope(**raw["safety_envelope"])
    experiment = owner.HardwareExperimentSpec(**raw["experiment"])
    profile.validate(); envelope.validate(); experiment.validate()
    return raw, profile, envelope, experiment


def _tolerance_profiles(profile: owner.PhysicalStandProfile, tolerances: Mapping[str, float]) -> Iterable[owner.PhysicalStandProfile]:
    fields = tuple(sorted(tolerances))
    for signs in product((-1.0, 1.0), repeat=len(fields)):
        changes: Dict[str, float] = {}
        for field, sign in zip(fields, signs):
            nominal = float(getattr(profile, field))
            changes[field] = nominal * (1.0 + sign * float(tolerances[field]))
        yield dataclasses.replace(profile, **changes)


def run_prebuild_qualification(contract_path: str | Path) -> Dict[str, Any]:
    raw, profile, envelope, experiment = load_stand_contract(contract_path)
    sample_rate = float(raw["protocol"]["sample_rate_hz"])
    nominal = owner.certify_physical_stand_profile(profile, envelope, experiment, sample_rate_hz=sample_rate)
    corners: List[Dict[str, Any]] = []
    for index, candidate in enumerate(_tolerance_profiles(profile, raw["tolerances"])):
        qualification = owner.certify_physical_stand_profile(candidate, envelope, experiment, sample_rate_hz=sample_rate)
        corners.append({
            "index": index,
            "status": qualification.certificate.status,
            "profile": dataclasses.asdict(candidate),
            "metrics": qualification.certificate.metrics,
            "certificate_digest": qualification.certificate.digest,
            "qualification_digest": qualification.digest,
        })
    all_corner_pass = bool(corners) and all(row["status"] == "PASS" for row in corners)
    metrics = [row["metrics"] for row in corners]
    report: Dict[str, Any] = {
        "schema": "phi-physical-prebuild-qualification/v4.1",
        "owner_version": owner.OWNER_VERSION,
        "contract_schema": raw["schema"],
        "profile_id": profile.profile_id,
        "nominal": {
            "status": nominal.certificate.status,
            "certificate": dataclasses.asdict(nominal.certificate),
            "qualification_digest": nominal.digest,
            "model": dataclasses.asdict(nominal.model),
        },
        "tolerance_box": {
            "corner_count": len(corners),
            "all_pass": all_corner_pass,
            "max_predicted_peak_response_v": max(float(m["predicted_peak_response_v"]) for m in metrics),
            "max_predicted_peak_response_adc_v": max(float(m["predicted_peak_response_adc_v"]) for m in metrics),
            "max_predicted_protection_resistor_power_w": max(float(m["predicted_protection_resistor_power_w"]) for m in metrics),
            "min_points_per_cycle": min(float(m["points_per_cycle"]) for m in metrics),
            "natural_frequency_hz_range": [
                min(float(m["natural_frequency_hz"]) for m in metrics),
                max(float(m["natural_frequency_hz"]) for m in metrics),
            ],
            "corners": corners,
        },
        "gates": {
            "nominal_prebuild": nominal.certificate.status == "PASS",
            "all_tolerance_corners": all_corner_pass,
            "operator_approval_required": bool(raw["protocol"]["operator_approval_required"]),
            "expected_serial_required": bool(raw["protocol"]["expected_serial_required"]),
            "hardware_estop_required": bool(raw["protocol"]["hardware_estop_required"]),
            "scpi_realtime_control_blocked": not bool(raw["protocol"]["scpi_network_control_allowed"]),
        },
        "all_acceptance_gates_pass": False,
        "claim_boundary": {
            "stand_prebuild": "QUALIFIED_OFFLINE" if nominal.certificate.status == "PASS" and all_corner_pass else "NOT_QUALIFIED",
            "real_device": "NOT_RUN",
            "measured_covariance": "NOT_AVAILABLE",
            "hardware_estop": "NOT_RUN",
            "guarded_reentry": "BLOCKED_NO_REALTIME_BACKEND_AND_NO_MEASURED_PRIVATE_VALIDATION",
        },
        "sources": raw.get("sources", []),
    }
    report["all_acceptance_gates_pass"] = all(bool(v) for v in report["gates"].values())
    return _finish(report)


class _InMemoryRedPitaya(RedPitayaSCPIAdapter):
    """Command-contract harness; no physical-device claim."""

    def __init__(self, envelope: owner.SafetyEnvelope, profile: owner.PhysicalStandProfile) -> None:
        super().__init__("in-memory", envelope, relay_enable_pin=profile.relay_enable_pin, relay_feedback_pin=profile.relay_feedback_pin)
        self.commands: List[str] = []
        self.relay_closed = False
        self.output_on = False
        self.triggered = False
        self._waveform_seen = False

    def _write(self, command: str) -> None:
        self.commands.append(command)
        if command.startswith(f"DIG:PIN {self.relay_enable_pin},"):
            self.relay_closed = command.rsplit(",", 1)[-1].strip() == "1"
        elif command == f"OUTPUT{self.output_channel}:STATE ON":
            self.output_on = True
        elif command == f"OUTPUT{self.output_channel}:STATE OFF":
            self.output_on = False
        elif command.startswith("SOUR1:TRAC:DATA:DATA"):
            self._waveform_seen = True
        elif command == "ACQ:TRIG NOW":
            self.triggered = True

    def _query(self, command: str) -> str:
        self.commands.append(command)
        if command == "*IDN?":
            return "RED PITAYA,STEMLAB 125-14,MEM-0001,OS-TEST"
        if command == f"DIG:PIN? {self.relay_feedback_pin}":
            return "1" if self.relay_closed else "0"
        if command == "ACQ:TRIG:STAT?":
            return "TD" if self.triggered else "WAIT"
        if command.startswith("ACQ:SOUR"):
            count = self.BUFFER_SIZE
            x = np.linspace(0.0, 1.0, count, endpoint=False)
            values = 0.02 * np.sin(2 * math.pi * 73 * x)
            return "{" + ",".join(f"{v:.8g}" for v in values) + "}"
        raise InstrumentTransportError(f"Unhandled in-memory query: {command}")

    def close(self) -> None:
        self.emergency_stop(best_effort=True)


def run_adapter_relay_contract(contract_path: str | Path) -> Dict[str, Any]:
    raw, profile, envelope, experiment = load_stand_contract(contract_path)
    adapter = _InMemoryRedPitaya(envelope, profile)
    identity = adapter.identity()
    estop = adapter.prove_hardware_emergency_stop()
    adapter.configure(experiment)
    adapter.arm()
    acquisition = adapter.acquire()
    adapter.emergency_stop()
    checks = {
        "identity_complete": all(bool(str(getattr(identity, f)).strip()) for f in ("vendor", "model", "serial", "firmware", "transport")),
        "relay_estop_open_before": bool(estop["open_before"]),
        "relay_estop_closed_when_armed": bool(estop["closed_when_armed"]),
        "relay_estop_open_after": bool(estop["open_after"]),
        "waveform_uploaded": adapter._waveform_seen,
        "two_input_channels": set(acquisition.channels) == {"in1", "in2"},
        "fresh_acquisition_started": adapter.commands.count("ACQ:START") >= 1,
        "output_disabled_after_stop": not adapter.output_on,
        "relay_open_after_stop": not adapter.relay_closed,
        "scpi_realtime_control_blocked": not bool(raw["protocol"]["scpi_network_control_allowed"]),
    }
    return _finish({
        "schema": "phi-physical-adapter-contract/v4.1",
        "owner_version": owner.OWNER_VERSION,
        "checks": checks,
        "passed": sum(bool(v) for v in checks.values()),
        "total": len(checks),
        "all_acceptance_gates_pass": all(checks.values()),
        "command_count": len(adapter.commands),
        "command_prefix": adapter.commands[:20],
        "claim_boundary": {"transport_and_relay_sequence": "QUALIFIED_IN_MEMORY", "real_device": "NOT_RUN"},
    })


def _capture(adapter: RedPitayaSCPIAdapter, spec: owner.HardwareExperimentSpec) -> owner.RawAcquisition:
    try:
        adapter.configure(spec)
        adapter.arm()
        return adapter.acquire()
    finally:
        adapter.emergency_stop(best_effort=True)


def run_real_device_open_loop_qualification(
    contract_path: str | Path,
    *,
    host: str,
    expected_serial: str,
    operator_approved: bool,
    raw_output_path: str | Path,
) -> Dict[str, Any]:
    """Acquire real calibration/identification data and recover a model.

    This workflow intentionally stops before closed-loop guarded reentry because
    TCP/SCPI is not a qualified deterministic real-time controller backend.
    """
    raw, profile, envelope, experiment = load_stand_contract(contract_path)
    if raw["protocol"]["operator_approval_required"] and not operator_approved:
        raise PermissionError("Operator approval is required before any physical excitation")
    if raw["protocol"]["expected_serial_required"] and not expected_serial.strip():
        raise ValueError("An explicit expected instrument serial is required")
    prebuild = run_prebuild_qualification(contract_path)
    if not prebuild["all_acceptance_gates_pass"]:
        raise RuntimeError("Physical prebuild qualification failed")
    calibration_repeats = int(raw["protocol"]["calibration_repeats"])
    identification_repeats = int(raw["protocol"]["identification_repeats"])
    zero_spec = dataclasses.replace(experiment, amplitude_1=0.0, amplitude_2=0.0, probe_fraction=0.0)
    captures: List[owner.RawAcquisition] = []
    calibration_captures: List[owner.RawAcquisition] = []
    estop_evidence: Mapping[str, Any] = {}
    with RedPitayaSCPIAdapter(
        host, envelope,
        relay_enable_pin=profile.relay_enable_pin,
        relay_feedback_pin=profile.relay_feedback_pin,
        input_channels=(1, 2),
    ) as adapter:
        identity = adapter.identity()
        if identity.serial != expected_serial:
            raise RuntimeError(f"Instrument serial mismatch: expected {expected_serial!r}, received {identity.serial!r}")
        estop_evidence = adapter.prove_hardware_emergency_stop()
        calibration_captures = [_capture(adapter, zero_spec) for _ in range(calibration_repeats)]
        captures = [_capture(adapter, experiment) for _ in range(identification_repeats)]
    latencies = [float(acq.metadata.get("latency_s", math.nan)) for acq in calibration_captures]
    if not all(np.isfinite(latencies)):
        raise RuntimeError("Instrument latency evidence is incomplete")
    channel_gain = float(raw["protocol"]["physical_channel_gain"])
    calibration = owner.estimate_calibration_package(
        identity,
        calibration_captures,
        envelope,
        latencies,
        (raw["protocol"]["input_channel"], raw["protocol"]["response_channel"]),
        channel_gain={raw["protocol"]["input_channel"]: channel_gain, raw["protocol"]["response_channel"]: channel_gain},
        source_kind="MEASURED_DEVICE",
    )
    # Convert all captures to the exact dimensionless time scaling sqrt(LC).
    normalized = [owner.normalize_physical_acquisition(acq, profile, input_channel=raw["protocol"]["input_channel"], response_channel=raw["protocol"]["response_channel"]) for acq in captures]
    t_ref = normalized[0][0]
    if any(len(t) != len(t_ref) or not np.allclose(t, t_ref, rtol=1e-9, atol=1e-9) for t, _, _ in normalized[1:]):
        raise RuntimeError("Identification captures do not share one time grid")
    max_t = float(raw["protocol"]["recovery_max_normalized_time"])
    keep = np.flatnonzero(t_ref <= max_t)
    points = int(raw["protocol"]["recovery_points"])
    selection = keep[np.linspace(0, len(keep) - 1, min(points, len(keep))).astype(int)]
    t_norm = t_ref[selection]
    u_stack = np.stack([u[selection] for _, u, _ in normalized], axis=0)
    x_stack = np.stack([x[selection] for _, _, x in normalized], axis=0)
    measurement_sigma = math.sqrt(max(float(calibration.covariance[1, 1]), 1e-18))
    episode = owner.Episode(t_norm, np.mean(u_stack, axis=0), x_stack, measurement_sigma, "REAL_DEVICE_OPEN_LOOP_IDENTIFICATION", None)
    package = owner.ObservationPackage((episode,), {"t": "sqrt(LC)", "u": "V", "x": "V"}, {"profile_id": profile.profile_id, "identity_serial": identity.serial}, False)
    recovery = owner.recover_resonator_family(package, design_next=False)
    normalized_model = owner.resonator_model_from_recovery(recovery)
    physical_model = owner.denormalize_resonator_model(normalized_model, profile.time_scale_s)
    sample_rate = float(calibration.sample_rate_hz)
    t_pred, _, y_pred, _ = owner.simulate_physical_stand(profile, experiment, sample_rate)
    variance = np.full_like(t_pred, max(float(calibration.covariance[1, 1]), 1e-18))
    safe_cert = owner.certify_hardware_experiment(experiment, calibration, t_pred, y_pred, variance)
    raw_output_path = Path(raw_output_path)
    raw_output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        raw_output_path,
        calibration_t=np.asarray(calibration_captures[0].t),
        calibration_in1=np.stack([acq.channels["in1"] for acq in calibration_captures]),
        calibration_in2=np.stack([acq.channels["in2"] for acq in calibration_captures]),
        identification_t=np.asarray(captures[0].t),
        identification_in1=np.stack([acq.channels["in1"] for acq in captures]),
        identification_in2=np.stack([acq.channels["in2"] for acq in captures]),
    )
    raw_digest = hashlib.sha256(raw_output_path.read_bytes()).hexdigest()
    gates = {
        "prebuild": prebuild["all_acceptance_gates_pass"],
        "identity_exact": identity.serial == expected_serial,
        "hardware_estop": all(bool(v) for v in estop_evidence.values()),
        "calibration": calibration.certificate.status == "PASS",
        "safe_experiment": safe_cert.status == "PASS",
        "recovery": recovery.certificate.status == "PASS",
        "raw_evidence_persisted": raw_output_path.exists() and raw_output_path.stat().st_size > 0,
        "scpi_guarded_reentry_blocked": not bool(raw["protocol"]["scpi_network_control_allowed"]),
    }
    return _finish({
        "schema": "phi-real-device-open-loop-qualification/v4.1",
        "owner_version": owner.OWNER_VERSION,
        "identity": dataclasses.asdict(identity),
        "profile_id": profile.profile_id,
        "estop_evidence": dict(estop_evidence),
        "calibration": dataclasses.asdict(calibration),
        "safe_experiment_certificate": dataclasses.asdict(safe_cert),
        "recovery": dataclasses.asdict(recovery),
        "normalized_recovered_model": dataclasses.asdict(normalized_model),
        "physical_recovered_model": dataclasses.asdict(physical_model),
        "raw_evidence": {"path": str(raw_output_path), "sha256": raw_digest},
        "gates": gates,
        "all_acceptance_gates_pass": all(gates.values()),
        "claim_boundary": {
            "real_device_open_loop_identification": "QUALIFIED" if all(gates.values()) else "NOT_QUALIFIED",
            "controller_compilation": "OFFLINE_ALLOWED_AFTER_MODEL_GATE",
            "guarded_reentry": "BLOCKED_NO_QUALIFIED_REALTIME_BACKEND",
            "technological_breakthrough": "NOT_ESTABLISHED",
        },
    })
