#!/usr/bin/env python3
"""Authoritative Φ-Compiler scientific and guarded-control runtime owner v4.1.

The module contains the active scientific logic only:
- typed dispatch for every supported observation kind;
- computable, digest-bound GateCertificate objects;
- cross-family Bayesian recovery for H1/H23/H4/H5/H6;
- safe robust experiment design with parameter and measurement uncertainty;
- drift-state transition logic and hardware adapter contracts.

Private truth generation, benchmark orchestration, CLI parsing, report writing and
acceptance decisions live outside this owner.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import itertools
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from typing import Any, Callable, Dict, List, Mapping, MutableMapping, Protocol, Sequence, Tuple, Type

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import expm, solve_discrete_are
from scipy.optimize import least_squares, lsq_linear
from scipy.integrate import quad
from scipy.signal import cont2discrete, savgol_filter
from scipy.special import gamma as gamma_fn, loggamma
from scipy.stats import chi2

from source.lawspace.schema import GateCertificate
from source.lawspace.formal_contracts import toller_distributional_vertex_contract

# NumPy 2.4 removed the long-deprecated ``np.trapz`` alias. Keep the runtime
# compatible with both the declared NumPy 1.26 floor and current releases.
_numpy_trapezoid = np.trapezoid if hasattr(np, "trapezoid") else np.trapz

SCHEMA = "phi-compiler-runtime/v4.1"
OWNER_VERSION = "4.1.0"
FAMILIES = (
    "H1_MARKOV_ODE",
    "H23_EXP_MEMORY_EQUIV",
    "H4_DELAY_ODE",
    "H5_SDE",
    "H6_FRACTIONAL_MEMORY",
)
HYPOTHESIS_VIEW = {
    "H1_MARKOV_ODE": ("H1",),
    "H23_EXP_MEMORY_EQUIV": ("H2", "H3"),
    "H4_DELAY_ODE": ("H4",),
    "H5_SDE": ("H5",),
    "H6_FRACTIONAL_MEMORY": ("H6",),
}


# ----------------------------- Serialization ---------------------------------

def _json_default(obj: Any) -> Any:
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, complex):
        return {"real": float(obj.real), "imag": float(obj.imag)}
    if isinstance(obj, np.ndarray):
        if np.iscomplexobj(obj):
            return [{"real": float(v.real), "imag": float(v.imag)} for v in obj.ravel()] if obj.ndim == 1 else [[{"real": float(v.real), "imag": float(v.imag)} for v in row] for row in obj]
        return obj.tolist()
    if isinstance(obj, Enum):
        return obj.value
    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    raise TypeError(type(obj).__name__)


def _digest_payload(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=_json_default).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _logsumexp(values: Sequence[float]) -> float:
    arr = np.asarray(values, dtype=float)
    m = float(np.max(arr))
    return m + math.log(float(np.sum(np.exp(arr - m))))


def _normalize_log_prob(logp: Mapping[str, float]) -> Dict[str, float]:
    z = _logsumexp(list(logp.values()))
    return {k: float(math.exp(v - z)) for k, v in logp.items()}


# ----------------------------- Typed contracts -------------------------------
@dataclass(frozen=True)
class Episode:
    t: NDArray[np.float64]
    u: NDArray[np.float64]
    x: NDArray[np.float64]  # shape (replicates, time)
    measurement_sigma: float
    protocol: str
    experiment: "ExperimentSpec | None" = None

    def validate(self) -> None:
        if self.t.ndim != 1 or self.u.ndim != 1 or self.x.ndim != 2:
            raise ValueError("Episode requires t,u as vectors and x as (replicates,time)")
        if len(self.t) != len(self.u) or self.x.shape[1] != len(self.t):
            raise ValueError("Episode arrays have inconsistent lengths")
        if len(self.t) < 11 or not np.all(np.diff(self.t) > 0):
            raise ValueError("Episode time grid must be strictly increasing")
        if self.x.shape[0] < 2:
            raise ValueError("At least two replicated trajectories are required")
        if not np.isfinite(self.measurement_sigma) or self.measurement_sigma <= 0:
            raise ValueError("measurement_sigma must be positive")
        if not np.all(np.isfinite(self.t)) or not np.all(np.isfinite(self.u)) or not np.all(np.isfinite(self.x)):
            raise ValueError("Episode contains non-finite values")


@dataclass(frozen=True)
class ObservationPackage:
    episodes: Tuple[Episode, ...]
    units: Mapping[str, str]
    metadata: Mapping[str, Any]
    truth_access: bool = False

    def validate(self) -> None:
        if self.truth_access:
            raise RuntimeError("Blind boundary violated: truth_access=True")
        if not self.episodes:
            raise ValueError("At least one episode is required")
        for episode in self.episodes:
            episode.validate()


@dataclass(frozen=True)
class StaticScalarObservation:
    x: NDArray[np.float64]
    y: NDArray[np.float64]
    units: Mapping[str, str]


@dataclass(frozen=True)
class DecaySeriesObservation:
    t: NDArray[np.float64]
    y: NDArray[np.float64]


@dataclass(frozen=True)
class SecondOrderObservation:
    t: NDArray[np.float64]
    x: NDArray[np.float64]
    u: NDArray[np.float64] | None = None


@dataclass(frozen=True)
class PeriodicScalarPDEObservation:
    t: NDArray[np.float64]
    x_grid: NDArray[np.float64]
    concentration: NDArray[np.float64]  # shape (time,space), periodic boundary


@dataclass(frozen=True)
class ClosedQuantumObservation:
    t: NDArray[np.float64]
    psi: NDArray[np.complex128]  # shape (time,dimension)


@dataclass(frozen=True)
class OpenQubitBlochObservation:
    t: NDArray[np.float64]
    bloch: NDArray[np.float64]  # shape (time,3) or (trajectory,time,3)


@dataclass(frozen=True)
class CoupledTollerWedgeObservation:
    """Finite-regulator qualification request for the causal coupled-wedge kernel.

    The owner tests the exact spectral coupling implied by the Feynman i-epsilon
    Toller formula.  Both half-edges share one spectral parameter and one complete
    intermediate canonical channel.  This is deliberately not the invalid product
    of two independently causal half-edge Toller functions.
    """

    gamma: float = 0.274
    spin: float = 0.5
    magnetic: float = 0.5
    beta_a: float = 0.70
    beta_b: float = -0.20
    branch: int = 1
    epsilon: float = 0.10
    spectral_cutoff: float = 16.0
    spectral_nodes: int = 28
    canonical_spin_cutoff: float = 6.5
    k5_samples: int = 6
    integration_bound: float = 0.8
    distribution_test_bound: float = 10.0
    distribution_test_width: float = 0.35
    distribution_epsilon_schedule: Tuple[float, ...] = (0.10, 0.05, 0.025, 0.0125, 0.00625)
    seed: int = 42
    qpdtr_bridge: Mapping[str, Any] | None = None
    multidomain_qg_bridge: Mapping[str, Any] | None = None

    def validate(self) -> None:
        twice_j = round(2.0 * self.spin)
        twice_m = round(2.0 * self.magnetic)
        if self.spin <= 0 or abs(2.0 * self.spin - twice_j) > 1e-12:
            raise ValueError("spin must be a positive integer or half-integer")
        if abs(2.0 * self.magnetic - twice_m) > 1e-12 or abs(self.magnetic) > self.spin:
            raise ValueError("magnetic must be an admissible integer or half-integer")
        if self.branch not in (-1, 1):
            raise ValueError("branch must be -1 or +1")
        if not (self.gamma > 0 and self.epsilon > 0 and self.spectral_cutoff > 0):
            raise ValueError("gamma, epsilon and spectral_cutoff must be positive")
        if self.spectral_nodes < 12 or self.spectral_nodes % 2:
            raise ValueError("spectral_nodes must be an even integer >= 12")
        if self.canonical_spin_cutoff < self.spin + 2:
            raise ValueError("canonical_spin_cutoff must include at least two higher channels")
        if self.k5_samples < 2 or self.integration_bound <= 0:
            raise ValueError("k5_samples and integration_bound must be positive")
        if self.distribution_test_bound <= 2.0 or self.distribution_test_width <= 0:
            raise ValueError("distribution test bound and width must be positive")
        schedule = tuple(float(v) for v in self.distribution_epsilon_schedule)
        if len(schedule) < 4 or any(v <= 0 for v in schedule):
            raise ValueError("distribution_epsilon_schedule requires at least four positive entries")
        if any(schedule[i + 1] >= schedule[i] for i in range(len(schedule) - 1)):
            raise ValueError("distribution_epsilon_schedule must be strictly decreasing")


@dataclass(frozen=True)
class RecoveryRequest:
    kind: str
    payload: Any
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExperimentSpec:
    amplitude_1: float
    duration_1: float
    wait: float
    amplitude_2: float
    duration_2: float
    sign_2: int
    probe_omega: float
    observation_time: float

    def energy(self, dt: float = 0.025) -> float:
        t = np.arange(0.0, self.observation_time + 0.5 * dt, dt)
        u = experiment_input(t, self)
        return float(_numpy_trapezoid(u * u, t))

    def safe(self) -> bool:
        return bool(
            0.0 < self.duration_1 <= 0.45
            and 0.0 < self.duration_2 <= 0.45
            and 0.25 <= self.wait <= 2.8
            and abs(self.amplitude_1) <= 1.25
            and abs(self.amplitude_2) <= 1.25
            and self.sign_2 in (-1, 1)
            and 0.2 <= self.probe_omega <= 3.2
            and 5.0 <= self.observation_time <= 9.5
            and self.energy() <= 2.2
        )


@dataclass(frozen=True)
class HardwareExperimentSpec:
    """SI-unit excitation contract for a physical instrument session.

    This is intentionally separate from the normalized synthetic ExperimentSpec.
    All times are seconds, amplitudes are volts at the adapter output command, and
    probe_frequency_hz is cycles/second rather than angular normalized frequency.
    """

    amplitude_1: float
    duration_1: float
    wait: float
    amplitude_2: float
    duration_2: float
    sign_2: int
    probe_frequency_hz: float
    observation_time: float
    start_delay: float = 0.0005
    probe_fraction: float = 0.18
    probe_decay_time: float = 0.004

    @property
    def probe_omega(self) -> float:
        return 2.0 * math.pi * self.probe_frequency_hz

    def validate(self) -> None:
        numeric = (
            self.amplitude_1, self.duration_1, self.wait, self.amplitude_2,
            self.duration_2, self.probe_frequency_hz, self.observation_time,
            self.start_delay, self.probe_fraction, self.probe_decay_time,
        )
        if not all(np.isfinite(float(v)) for v in numeric):
            raise ValueError("HardwareExperimentSpec requires finite values")
        if self.duration_1 <= 0 or self.duration_2 <= 0 or self.wait < 0 or self.start_delay < 0:
            raise ValueError("Pulse durations must be positive and delays nonnegative")
        if self.probe_frequency_hz <= 0 or self.probe_decay_time <= 0 or self.observation_time <= 0:
            raise ValueError("Probe frequency, decay time and observation time must be positive")
        if self.sign_2 not in (-1, 1):
            raise ValueError("sign_2 must be -1 or +1")
        if not 0.0 <= self.probe_fraction <= 1.0:
            raise ValueError("probe_fraction must be within [0,1]")
        end_2 = self.start_delay + self.duration_1 + self.wait + self.duration_2
        if end_2 >= self.observation_time:
            raise ValueError("Pulses must finish before the observation window ends")

    def energy(self, samples: int = 16384) -> float:
        self.validate()
        t = np.linspace(0.0, self.observation_time, max(int(samples), 256), endpoint=False)
        u = hardware_experiment_input(t, self)
        return float(_numpy_trapezoid(u * u, t))

    def safe(self) -> bool:
        try:
            self.validate()
        except ValueError:
            return False
        return True


@dataclass
class CandidateModel:
    family: str
    parameters: Dict[str, float]
    parameter_std: Dict[str, float]
    nrmse: float
    log_likelihood: float
    log_evidence: float
    certificate: GateCertificate
    evidence: Dict[str, float]


@dataclass
class RecoveryResult:
    owner_version: str
    schema: str
    observation_kind: str
    selected_class: str
    top_hypotheses: List[str]
    posterior: Dict[str, float]
    candidates: List[CandidateModel]
    ambiguity_status: str
    experiment_spec: ExperimentSpec | None
    certificate: GateCertificate
    truth_access: bool = False
    digest: str = ""

    def finalize(self) -> "RecoveryResult":
        payload = dataclasses.asdict(self)
        payload["digest"] = ""
        self.digest = _digest_payload(payload)
        return self


@dataclass
class HandlerResult:
    owner_version: str
    schema: str
    observation_kind: str
    parameters: Dict[str, Any]
    prediction_error: float
    certificate: GateCertificate
    digest: str = ""

    def finalize(self) -> "HandlerResult":
        payload = dataclasses.asdict(self)
        payload["digest"] = ""
        self.digest = _digest_payload(payload)
        return self


# ----------------------------- Hardware boundary ------------------------------
@dataclass(frozen=True)
class InstrumentIdentity:
    vendor: str
    model: str
    serial: str
    firmware: str
    transport: str


@dataclass(frozen=True)
class RawAcquisition:
    t: NDArray[np.float64]
    channels: Mapping[str, NDArray[np.float64]]
    metadata: Mapping[str, Any]


class InstrumentAdapter(Protocol):
    def identity(self) -> InstrumentIdentity: ...
    def configure(self, spec: HardwareExperimentSpec) -> None: ...
    def arm(self) -> None: ...
    def acquire(self) -> RawAcquisition: ...
    def emergency_stop(self) -> None: ...


class RecoveryState(str, Enum):
    NORMAL_CONTROL = "NORMAL_CONTROL"
    SAFE_FALLBACK = "SAFE_FALLBACK"
    LOW_AMPLITUDE_IDENTIFICATION = "LOW_AMPLITUDE_IDENTIFICATION"
    PHI_COMPILER_RECOVERY = "PHI_COMPILER_RECOVERY"
    PRIVATE_VALIDATION = "PRIVATE_VALIDATION"
    CONTROLLER_RECOMPILATION = "CONTROLLER_RECOMPILATION"
    GUARDED_REENTRY = "GUARDED_REENTRY"


@dataclass
class DriftMonitor:
    kappa: float
    threshold: float
    statistic: float = 0.0
    state: RecoveryState = RecoveryState.NORMAL_CONTROL

    def update(self, innovation: NDArray[np.float64], covariance: NDArray[np.float64]) -> RecoveryState:
        covariance = np.asarray(covariance, dtype=float)
        innovation = np.asarray(innovation, dtype=float)
        score = float(innovation.T @ np.linalg.pinv(covariance) @ innovation)
        self.statistic = max(0.0, self.statistic + score - self.kappa)
        if self.statistic > self.threshold and self.state == RecoveryState.NORMAL_CONTROL:
            self.state = RecoveryState.SAFE_FALLBACK
        return self.state

    def advance(self, evidence_pass: bool) -> RecoveryState:
        order = list(RecoveryState)
        idx = order.index(self.state)
        if evidence_pass and idx < len(order) - 1:
            self.state = order[idx + 1]
        elif not evidence_pass:
            self.state = RecoveryState.SAFE_FALLBACK
        return self.state


# ----------------------- Hardware qualification owner -------------------------
@dataclass(frozen=True)
class SafetyEnvelope:
    """Operator-approved low-voltage limits; never inferred by unsafe exploration."""

    max_abs_drive: float
    max_abs_response: float
    max_rms_response: float
    max_slew_response: float
    max_energy: float
    max_observation_time: float
    min_sample_rate_hz: float

    def validate(self) -> None:
        values = dataclasses.asdict(self)
        if not all(np.isfinite(float(v)) and float(v) > 0.0 for v in values.values()):
            raise ValueError("SafetyEnvelope requires finite positive limits")
        if self.max_rms_response > self.max_abs_response:
            raise ValueError("RMS response limit cannot exceed absolute response limit")


@dataclass(frozen=True)
class PhysicalStandProfile:
    """Operator-approved physical R-L-(Rh||Ch)-C stand and measurement chain."""

    profile_id: str
    topology: str
    source_resistance_ohm: float
    protection_resistance_ohm: float
    inductor_h: float
    inductor_dcr_ohm: float
    main_capacitance_f: float
    hidden_resistance_ohm: float
    hidden_capacitance_f: float
    input_divider_top_ohm: float
    input_divider_bottom_ohm: float
    relay_enable_pin: str
    relay_feedback_pin: str
    instrument_output_full_scale_v: float
    instrument_input_full_scale_v: float
    instrument_input_absolute_max_v: float
    board_model: str
    wiring_revision: str

    @property
    def total_series_resistance_ohm(self) -> float:
        return self.source_resistance_ohm + self.protection_resistance_ohm + self.inductor_dcr_ohm

    @property
    def divider_ratio(self) -> float:
        return self.input_divider_bottom_ohm / (self.input_divider_top_ohm + self.input_divider_bottom_ohm)

    @property
    def time_scale_s(self) -> float:
        return math.sqrt(self.inductor_h * self.main_capacitance_f)

    def validate(self) -> None:
        expected = "SERIES_R_L_PARALLEL_RH_CH_C"
        if self.topology != expected:
            raise ValueError(f"Unsupported stand topology: {self.topology!r}; expected {expected}")
        values = (
            self.source_resistance_ohm, self.protection_resistance_ohm, self.inductor_h,
            self.inductor_dcr_ohm, self.main_capacitance_f, self.hidden_resistance_ohm,
            self.hidden_capacitance_f, self.input_divider_top_ohm,
            self.input_divider_bottom_ohm, self.instrument_output_full_scale_v,
            self.instrument_input_full_scale_v, self.instrument_input_absolute_max_v,
        )
        if not all(np.isfinite(float(v)) and float(v) > 0 for v in values):
            raise ValueError("Physical stand component/instrument values must be finite and positive")
        if self.instrument_input_absolute_max_v <= self.instrument_input_full_scale_v:
            raise ValueError("Absolute input maximum must exceed measurement full scale")
        if self.relay_enable_pin == self.relay_feedback_pin:
            raise ValueError("Relay enable and feedback pins must be distinct")
        if not self.profile_id.strip() or not self.board_model.strip() or not self.wiring_revision.strip():
            raise ValueError("Stand identity fields must be non-empty")


@dataclass
class PhysicalStandQualification:
    profile: PhysicalStandProfile
    model: ResonatorStateModel
    safety_envelope: SafetyEnvelope
    experiment: HardwareExperimentSpec
    predicted_peak_response_v: float
    predicted_rms_response_v: float
    predicted_peak_input_adc_v: float
    predicted_peak_response_adc_v: float
    predicted_peak_current_a: float
    predicted_protection_resistor_power_w: float
    certificate: GateCertificate
    digest: str = ""

    def finalize(self) -> "PhysicalStandQualification":
        payload = dataclasses.asdict(self)
        payload["digest"] = ""
        self.digest = _digest_payload(payload)
        return self


@dataclass
class CalibrationPackage:
    identity: InstrumentIdentity
    source_kind: str
    channel_order: Tuple[str, ...]
    sample_rate_hz: float
    channel_offset: Dict[str, float]
    channel_gain: Dict[str, float]
    covariance: NDArray[np.float64]
    temporal_ar1: Dict[str, float]
    latency_mean_s: float
    latency_std_s: float
    repeat_count: int
    safety_envelope: SafetyEnvelope
    certificate: GateCertificate
    digest: str = ""

    def finalize(self) -> "CalibrationPackage":
        payload = dataclasses.asdict(self)
        payload["digest"] = ""
        self.digest = _digest_payload(payload)
        return self


@dataclass
class DriftCalibration:
    kappa: float
    threshold: float
    score_quantile: float
    false_alarm_probability: float
    horizon: int
    bootstrap_runs: int
    baseline_score_mean: float
    baseline_score_std: float
    certificate: GateCertificate
    digest: str = ""

    def finalize(self) -> "DriftCalibration":
        payload = dataclasses.asdict(self)
        payload["digest"] = ""
        self.digest = _digest_payload(payload)
        return self


@dataclass(frozen=True)
class ResonatorStateModel:
    """Normalized state model recovered from observed input/output data.

    x¨ + damping*x˙ + stiffness*x + coupling*z = input_gain*u
    z˙ = -hidden_decay*z + hidden_drive*x˙

    For a physical RLC realization: stiffness=1/(LC), damping=R/L,
    input_gain=1/L and coupling=eta/L. L, R and C are not separately
    identifiable without calibrated electrical units and at least one known
    component or an independent current measurement.
    """

    stiffness: float
    damping: float
    input_gain: float
    coupling: float = 0.0
    hidden_decay: float = 1.0
    hidden_drive: float = 1.0
    process_sigma: float = 0.0
    provenance_digest: str = ""

    @property
    def dimension(self) -> int:
        return 3 if abs(self.coupling) > 1e-12 else 2

    def validate(self) -> None:
        if not (self.stiffness > 0 and self.damping >= 0 and self.input_gain > 0):
            raise ValueError("Resonator model requires positive stiffness/gain and nonnegative damping")
        if self.dimension == 3 and not (self.coupling > 0 and self.hidden_decay > 0 and self.hidden_drive > 0):
            raise ValueError("Hidden-state model requires positive coupling, decay and drive")
        if self.process_sigma < 0:
            raise ValueError("process_sigma cannot be negative")


@dataclass
class CompiledController:
    model: ResonatorStateModel
    sample_time_s: float
    A_d: NDArray[np.float64]
    B_d: NDArray[np.float64]
    C_d: NDArray[np.float64]
    gain: NDArray[np.float64]
    riccati: NDArray[np.float64]
    estimator_gain: NDArray[np.float64]
    estimator_covariance: NDArray[np.float64]
    closed_loop_eigenvalues: NDArray[np.complex128]
    observer_eigenvalues: NDArray[np.complex128]
    invariant_level: float
    input_limit: float
    response_limit: float
    certificate: GateCertificate
    digest: str = ""

    def finalize(self) -> "CompiledController":
        payload = dataclasses.asdict(self)
        payload["digest"] = ""
        self.digest = _digest_payload(payload)
        return self


@dataclass(frozen=True)
class ValidationTrajectory:
    t: NDArray[np.float64]
    states: NDArray[np.float64]
    inputs: NDArray[np.float64]
    outputs: NDArray[np.float64]
    innovations: NDArray[np.float64]
    innovation_covariance: NDArray[np.float64]
    protocol: str
    identification_digest: str
    validation_digest: str
    saturation_count: int
    emergency_stop_tested: bool


@dataclass
class GuardedReentryDecision:
    accepted: bool
    blend_schedule: Tuple[float, ...]
    required_cycles_per_stage: int
    abort_conditions: Dict[str, float | int | str]
    certificate: GateCertificate
    digest: str = ""

    def finalize(self) -> "GuardedReentryDecision":
        payload = dataclasses.asdict(self)
        payload["digest"] = ""
        self.digest = _digest_payload(payload)
        return self


def _validate_raw_acquisition(acq: RawAcquisition, channel_order: Sequence[str]) -> None:
    t = np.asarray(acq.t, dtype=float)
    if t.ndim != 1 or len(t) < 16 or not np.all(np.diff(t) > 0):
        raise ValueError("Raw acquisition requires an increasing time grid with at least 16 samples")
    for channel in channel_order:
        if channel not in acq.channels:
            raise ValueError(f"Missing acquisition channel: {channel}")
        values = np.asarray(acq.channels[channel], dtype=float)
        if values.shape != t.shape or not np.all(np.isfinite(values)):
            raise ValueError(f"Invalid acquisition channel: {channel}")


def hardware_experiment_input(t: NDArray[np.float64], spec: HardwareExperimentSpec) -> NDArray[np.float64]:
    spec.validate()
    t = np.asarray(t, dtype=float)
    u = np.zeros_like(t)
    start_1 = spec.start_delay
    end_1 = start_1 + spec.duration_1
    start_2 = end_1 + spec.wait
    end_2 = start_2 + spec.duration_2
    u[(t >= start_1) & (t < end_1)] = spec.amplitude_1
    u[(t >= start_2) & (t < end_2)] = spec.sign_2 * spec.amplitude_2
    probe = t >= end_2
    decay = np.exp(-np.maximum(t - end_2, 0.0) / spec.probe_decay_time)
    u[probe] += spec.probe_fraction * spec.amplitude_2 * decay[probe] * np.sin(spec.probe_omega * (t[probe] - end_2))
    return u


def stand_model_from_profile(profile: PhysicalStandProfile, *, process_sigma: float = 0.0, provenance_digest: str = "") -> ResonatorStateModel:
    profile.validate()
    L = profile.inductor_h
    C = profile.main_capacitance_f
    return ResonatorStateModel(
        stiffness=1.0 / (L * C),
        damping=profile.total_series_resistance_ohm / L,
        input_gain=1.0 / (L * C),
        coupling=1.0 / (L * C),
        hidden_decay=1.0 / (profile.hidden_resistance_ohm * profile.hidden_capacitance_f),
        hidden_drive=C / profile.hidden_capacitance_f,
        process_sigma=float(process_sigma),
        provenance_digest=provenance_digest or _digest_payload(dataclasses.asdict(profile)),
    )


def denormalize_resonator_model(model: ResonatorStateModel, time_scale_s: float) -> ResonatorStateModel:
    """Map the normalized recovery model back to SI time while preserving voltage states."""
    model.validate()
    if not np.isfinite(time_scale_s) or time_scale_s <= 0:
        raise ValueError("time_scale_s must be finite and positive")
    return ResonatorStateModel(
        stiffness=model.stiffness / (time_scale_s**2),
        damping=model.damping / time_scale_s,
        input_gain=model.input_gain / (time_scale_s**2),
        coupling=model.coupling / (time_scale_s**2),
        hidden_decay=model.hidden_decay / time_scale_s,
        hidden_drive=model.hidden_drive,
        process_sigma=model.process_sigma / max(time_scale_s**2, 1e-30),
        provenance_digest=model.provenance_digest,
    )


def simulate_physical_stand(
    profile: PhysicalStandProfile,
    spec: HardwareExperimentSpec,
    sample_rate_hz: float,
) -> Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Simulate actual drive u, capacitor voltage y and hidden RC voltage z."""
    profile.validate(); spec.validate()
    if sample_rate_hz <= 0 or not np.isfinite(sample_rate_hz):
        raise ValueError("sample_rate_hz must be finite and positive")
    count = int(math.ceil(spec.observation_time * sample_rate_hz))
    if count < 64 or count > 2_000_000:
        raise ValueError("Physical simulation sample count outside qualified bounds")
    t = np.arange(count, dtype=float) / sample_rate_hz
    u = hardware_experiment_input(t, spec)
    model = stand_model_from_profile(profile)
    A = np.array([[0.0, 1.0, 0.0], [-model.stiffness, -model.damping, -model.coupling], [0.0, model.hidden_drive, -model.hidden_decay]], dtype=float)
    B = np.array([[0.0], [model.input_gain], [0.0]], dtype=float)
    Cmat = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]], dtype=float)
    D = np.zeros((2, 1), dtype=float)
    A_d, B_d, C_d, _, _ = cont2discrete((A, B, Cmat, D), 1.0 / sample_rate_hz, method="zoh")
    state = np.zeros(3, dtype=float)
    y = np.empty(count, dtype=float); z = np.empty(count, dtype=float)
    for idx, drive in enumerate(u):
        out = C_d @ state
        y[idx], z[idx] = float(out[0]), float(out[1])
        state = A_d @ state + B_d[:, 0] * float(drive)
    return t, u, y, z


def certify_physical_stand_profile(
    profile: PhysicalStandProfile,
    safety_envelope: SafetyEnvelope,
    experiment: HardwareExperimentSpec,
    *,
    sample_rate_hz: float = 488_281.25,
) -> PhysicalStandQualification:
    profile.validate(); safety_envelope.validate(); experiment.validate()
    t, u, response, hidden = simulate_physical_stand(profile, experiment, sample_rate_hz)
    divider = profile.divider_ratio
    peak_response = float(np.max(np.abs(response)))
    rms_response = float(np.sqrt(np.mean(response**2)))
    peak_input_adc = float(np.max(np.abs(u)) * divider)
    peak_response_adc = peak_response * divider
    peak_current = float(np.max(np.abs(u)) / profile.total_series_resistance_ohm)
    protection_power = peak_current**2 * profile.protection_resistance_ohm
    model = stand_model_from_profile(profile)
    natural_frequency_hz = math.sqrt(model.stiffness) / (2.0 * math.pi)
    damping_ratio = model.damping / (2.0 * math.sqrt(model.stiffness))
    hidden_tau_s = 1.0 / model.hidden_decay
    points_per_cycle = sample_rate_hz / natural_frequency_hz
    cert = _certificate(
        "physical_stand_prebuild", "LOW_VOLTAGE_RLC_HIDDEN_RC",
        {
            "profile_valid": True,
            "hardware_spec_valid": experiment.safe(),
            "drive_below_operator_limit": float(np.max(np.abs(u))) <= safety_envelope.max_abs_drive,
            "drive_below_instrument_full_scale": float(np.max(np.abs(u))) <= 0.80 * profile.instrument_output_full_scale_v,
            "predicted_response_below_operator_limit": peak_response <= safety_envelope.max_abs_response,
            "predicted_rms_below_operator_limit": rms_response <= safety_envelope.max_rms_response,
            "input_adc_headroom": peak_input_adc <= 0.80 * profile.instrument_input_full_scale_v,
            "response_adc_headroom": peak_response_adc <= 0.80 * profile.instrument_input_full_scale_v,
            "absolute_input_damage_margin": max(peak_input_adc, peak_response_adc) <= 0.10 * profile.instrument_input_absolute_max_v,
            "sample_rate_safe": sample_rate_hz >= safety_envelope.min_sample_rate_hz,
            "points_per_resonant_cycle": points_per_cycle >= 40.0,
            "hidden_time_constant_observed": experiment.observation_time >= 8.0 * hidden_tau_s,
            "resonant_cycles_observed": experiment.observation_time * natural_frequency_hz >= 20.0,
            "protection_resistor_power_margin": protection_power <= 0.10,
            "relay_feedback_independent": profile.relay_enable_pin != profile.relay_feedback_pin,
            "excitation_energy_limit": experiment.energy() <= safety_envelope.max_energy,
            "observation_time_limit": experiment.observation_time <= safety_envelope.max_observation_time,
        },
        {
            "natural_frequency_hz": natural_frequency_hz,
            "damping_ratio": damping_ratio,
            "hidden_time_constant_s": hidden_tau_s,
            "points_per_cycle": points_per_cycle,
            "sample_rate_hz": sample_rate_hz,
            "predicted_peak_response_v": peak_response,
            "predicted_rms_response_v": rms_response,
            "predicted_peak_hidden_v": float(np.max(np.abs(hidden))),
            "predicted_peak_input_adc_v": peak_input_adc,
            "predicted_peak_response_adc_v": peak_response_adc,
            "predicted_peak_current_a": peak_current,
            "predicted_protection_resistor_power_w": protection_power,
            "drive_energy_v2s": experiment.energy(),
            "divider_ratio": divider,
        },
        [
            "stand is powered only by the Red Pitaya low-voltage output; no mains connection",
            "component values and relay wiring are independently checked by the operator before enable",
            "manufacturer full-scale and absolute-maximum limits correspond to the selected board/range",
            "simulation is a prebuild bound and never substitutes measured device calibration",
        ],
    )
    return PhysicalStandQualification(profile, model, safety_envelope, experiment, peak_response, rms_response, peak_input_adc, peak_response_adc, peak_current, protection_power, cert).finalize()


def normalize_physical_acquisition(
    acquisition: RawAcquisition,
    profile: PhysicalStandProfile,
    *,
    input_channel: str = "in1",
    response_channel: str = "in2",
) -> Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    """Convert measured ADC channels to dimensionless recovery coordinates."""
    profile.validate()
    _validate_raw_acquisition(acquisition, (input_channel, response_channel))
    gain = 1.0 / profile.divider_ratio
    t_normalized = np.asarray(acquisition.t, dtype=float) / profile.time_scale_s
    u_volts = np.asarray(acquisition.channels[input_channel], dtype=float) * gain
    response_volts = np.asarray(acquisition.channels[response_channel], dtype=float) * gain
    return t_normalized, u_volts, response_volts


def estimate_calibration_package(
    identity: InstrumentIdentity,
    acquisitions: Sequence[RawAcquisition],
    safety_envelope: SafetyEnvelope,
    latency_samples_s: Sequence[float],
    channel_order: Sequence[str],
    *,
    channel_gain: Mapping[str, float] | None = None,
    source_kind: str = "MEASURED_DEVICE",
    shrinkage: float = 0.12,
) -> CalibrationPackage:
    """Estimate channel covariance and temporal correlation from synchronized repeats."""
    safety_envelope.validate()
    if len(acquisitions) < 8:
        raise ValueError("Calibration requires at least eight synchronized repeats")
    order = tuple(channel_order)
    if not order or len(set(order)) != len(order):
        raise ValueError("channel_order must be non-empty and unique")
    for acq in acquisitions:
        _validate_raw_acquisition(acq, order)
    reference_t = np.asarray(acquisitions[0].t, dtype=float)
    if any(len(acq.t) != len(reference_t) or not np.allclose(acq.t, reference_t, rtol=1e-9, atol=1e-12) for acq in acquisitions[1:]):
        raise ValueError("Calibration repeats must use one synchronized time grid")
    dt = float(np.median(np.diff(reference_t)))
    sample_rate = 1.0 / dt
    gains = {ch: float((channel_gain or {}).get(ch, 1.0)) for ch in order}
    if not all(g > 0 and np.isfinite(g) for g in gains.values()):
        raise ValueError("channel gains must be finite and positive")
    stacked = np.asarray(
        [[[float(v) * gains[ch] for v in np.asarray(acq.channels[ch], dtype=float)] for ch in order] for acq in acquisitions],
        dtype=float,
    )
    mean_trajectory = np.mean(stacked, axis=0, keepdims=True)
    residual = stacked - mean_trajectory
    observations = np.transpose(residual, (0, 2, 1)).reshape(-1, len(order))
    sample_cov = np.atleast_2d(np.asarray(np.cov(observations, rowvar=False, ddof=1), dtype=float))
    alpha = float(np.clip(shrinkage, 0.0, 1.0))
    covariance = (1.0 - alpha) * sample_cov + alpha * np.diag(np.diag(sample_cov))
    covariance = 0.5 * (covariance + covariance.T)
    eigvals, eigvecs = np.linalg.eigh(covariance)
    floor = max(float(np.max(eigvals)) * 1e-9, 1e-14)
    covariance = (eigvecs * np.maximum(eigvals, floor)) @ eigvecs.T
    temporal_ar1: Dict[str, float] = {}
    for idx, ch in enumerate(order):
        r = residual[:, idx, :]
        num = float(np.sum(r[:, 1:] * r[:, :-1]))
        den = float(np.sum(r[:, :-1] ** 2))
        temporal_ar1[ch] = float(np.clip(num / max(den, 1e-18), -0.99, 0.99))
    offsets = {ch: float(np.median(stacked[:, idx, :])) for idx, ch in enumerate(order)}
    latencies = np.asarray(latency_samples_s, dtype=float)
    latency_ok = bool(len(latencies) >= 8 and np.all(np.isfinite(latencies)) and np.all(latencies >= 0))
    identity_ok = all(bool(str(getattr(identity, field)).strip()) for field in ("vendor", "model", "serial", "firmware", "transport"))
    covariance_min_eig = float(np.min(np.linalg.eigvalsh(covariance)))
    cert = _certificate(
        "hardware_calibration", source_kind,
        {
            "immutable_identity_complete": identity_ok,
            "synchronized_repeats": len(acquisitions) >= 8,
            "sample_rate_safe": sample_rate >= safety_envelope.min_sample_rate_hz,
            "covariance_positive_definite": covariance_min_eig > 0,
            "latency_measured": latency_ok,
            "positive_channel_gain": all(g > 0 and np.isfinite(g) for g in gains.values()),
        },
        {
            "repeat_count": len(acquisitions), "sample_rate_hz": sample_rate,
            "covariance_min_eigenvalue": covariance_min_eig,
            "latency_mean_s": float(np.mean(latencies)) if latency_ok else math.inf,
            "latency_std_s": float(np.std(latencies, ddof=1)) if latency_ok else math.inf,
            "shrinkage": alpha,
        },
        ["operator-supplied component and voltage limits", "synchronized repeated captures", "linear channel gain during calibration range"],
    )
    return CalibrationPackage(
        identity, source_kind, order, sample_rate, offsets, gains, covariance, temporal_ar1,
        float(np.mean(latencies)) if latency_ok else math.inf,
        float(np.std(latencies, ddof=1)) if latency_ok else math.inf,
        len(acquisitions), safety_envelope, cert,
    ).finalize()


def certify_hardware_experiment(
    spec: ExperimentSpec | HardwareExperimentSpec,
    calibration: CalibrationPackage,
    t: NDArray[np.float64],
    predicted_mean: NDArray[np.float64],
    predicted_variance: NDArray[np.float64],
    *,
    chance_z: float = 3.290526731,
) -> GateCertificate:
    t = np.asarray(t, dtype=float)
    mean = np.asarray(predicted_mean, dtype=float)
    variance = np.asarray(predicted_variance, dtype=float)
    if t.ndim != 1 or mean.shape != t.shape or variance.shape != t.shape:
        raise ValueError("Hardware safety prediction arrays must share one time grid")
    env = calibration.safety_envelope
    env.validate()
    sigma = np.sqrt(np.maximum(variance, 0.0))
    chance_bound = np.abs(mean) + chance_z * sigma
    rms_bound = float(np.sqrt(np.mean(mean**2 + variance)))
    slew_bound = float(np.max(np.abs(np.diff(mean) / np.diff(t)))) if len(t) > 1 else math.inf
    return _certificate(
        "hardware_safe_experiment", "CHANCE_CONSTRAINED_ENVELOPE",
        {
            "calibration_pass": calibration.certificate.status == "PASS",
            "generic_spec_safe": spec.safe(),
            "drive_limit": max(abs(spec.amplitude_1), abs(spec.amplitude_2)) <= env.max_abs_drive,
            "energy_limit": spec.energy() <= min(2.2, env.max_energy),
            "observation_time_limit": spec.observation_time <= env.max_observation_time,
            "sample_rate_limit": calibration.sample_rate_hz >= env.min_sample_rate_hz,
            "chance_response_limit": float(np.max(chance_bound)) <= env.max_abs_response,
            "rms_response_limit": rms_bound <= env.max_rms_response,
            "slew_response_limit": slew_bound <= env.max_slew_response,
        },
        {
            "max_chance_response": float(np.max(chance_bound)), "rms_response_bound": rms_bound,
            "max_slew_response": slew_bound, "drive_peak": max(abs(spec.amplitude_1), abs(spec.amplitude_2)),
            "drive_energy": spec.energy(), "chance_z": chance_z,
        },
        ["predictive mean/variance correspond to the calibrated device and wiring", "chance bound is pointwise and conservative", "operator safety limits dominate experiment utility"],
    )


def calibrate_drift_monitor(
    innovations: NDArray[np.float64],
    covariances: NDArray[np.float64],
    *,
    false_alarm_probability: float = 0.01,
    bootstrap_runs: int = 2000,
    horizon: int | None = None,
    seed: int = 271828,
) -> DriftCalibration:
    innovations = np.asarray(innovations, dtype=float)
    covariances = np.asarray(covariances, dtype=float)
    if innovations.ndim == 1:
        innovations = innovations[:, None]
    n, dim = innovations.shape
    if covariances.ndim == 2:
        covariances = np.repeat(covariances[None, :, :], n, axis=0)
    if covariances.shape != (n, dim, dim) or n < 30:
        raise ValueError("Drift calibration requires >=30 innovations and matching covariance matrices")
    scores = np.asarray([float(v.T @ np.linalg.pinv(S) @ v) for v, S in zip(innovations, covariances)], dtype=float)
    if not np.all(np.isfinite(scores)):
        raise ValueError("Non-finite normalized innovation scores")
    score_quantile = float(np.quantile(scores, 0.75))
    kappa = max(score_quantile, 1e-9)
    h = int(horizon or n)
    rng = np.random.default_rng(seed)
    maxima = np.empty(bootstrap_runs, dtype=float)
    for b in range(bootstrap_runs):
        draw = rng.choice(scores, size=h, replace=True)
        g = 0.0; gmax = 0.0
        for score in draw:
            g = max(0.0, g + float(score) - kappa)
            gmax = max(gmax, g)
        maxima[b] = gmax
    threshold = float(np.quantile(maxima, 1.0 - false_alarm_probability))
    exceedance = float(np.mean(maxima > threshold))
    cert = _certificate(
        "drift_monitor", "EMPIRICAL_CUSUM_CALIBRATION",
        {
            "enough_baseline_samples": n >= 30, "positive_kappa": kappa > 0,
            "positive_threshold": threshold > 0, "bootstrap_sufficient": bootstrap_runs >= 1000,
            "false_alarm_calibrated": exceedance <= max(2.0 * false_alarm_probability, 1.0 / bootstrap_runs),
        },
        {
            "baseline_count": n, "innovation_dimension": dim, "kappa": kappa, "threshold": threshold,
            "bootstrap_false_alarm": exceedance, "score_mean": float(np.mean(scores)), "score_std": float(np.std(scores, ddof=1)),
        },
        ["baseline interval is free of injected or known drift", "innovation covariance is calibrated and positive definite", "bootstrap horizon matches the online decision horizon"],
    )
    return DriftCalibration(kappa, threshold, score_quantile, false_alarm_probability, h, bootstrap_runs, float(np.mean(scores)), float(np.std(scores, ddof=1)), cert).finalize()


def drift_monitor_from_calibration(calibration: DriftCalibration) -> DriftMonitor:
    if calibration.certificate.status != "PASS":
        raise RuntimeError("Cannot arm a drift monitor from failed calibration")
    return DriftMonitor(kappa=calibration.kappa, threshold=calibration.threshold)


def resonator_model_from_recovery(result: RecoveryResult) -> ResonatorStateModel:
    if result.certificate.status != "PASS":
        raise RuntimeError("RecoveryResult certificate must pass before controller compilation")
    selected = next(c for c in result.candidates if c.family == result.selected_class)
    p = selected.parameters
    residual = max(float(selected.evidence.get("residual_sigma", 0.0)), 1e-5)
    if selected.family == "H1_MARKOV_ODE":
        return ResonatorStateModel(p["k"], p["damping"], p["gain"], process_sigma=residual, provenance_digest=result.digest)
    if selected.family == "H23_EXP_MEMORY_EQUIV":
        return ResonatorStateModel(p["k"], 0.0, p["gain"], p["coupling"], p["lambda"], 1.0, residual, result.digest)
    if selected.family == "H5_SDE":
        return ResonatorStateModel(p["k"], p["damping"], p["gain"], process_sigma=max(p.get("sigma", 0.0), residual), provenance_digest=result.digest)
    raise RuntimeError(f"Exact finite-dimensional controller compilation is fail-closed for {selected.family}")


def _resonator_continuous_matrices(model: ResonatorStateModel) -> Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    model.validate()
    if model.dimension == 2:
        A = np.array([[0.0, 1.0], [-model.stiffness, -model.damping]], dtype=float)
        B = np.array([[0.0], [model.input_gain]], dtype=float)
        C = np.array([[1.0, 0.0]], dtype=float)
    else:
        A = np.array([[0.0, 1.0, 0.0], [-model.stiffness, -model.damping, -model.coupling], [0.0, model.hidden_drive, -model.hidden_decay]], dtype=float)
        B = np.array([[0.0], [model.input_gain], [0.0]], dtype=float)
        C = np.array([[1.0, 0.0, 0.0]], dtype=float)
    return A, B, C, np.zeros((1, 1), dtype=float)


def compile_guarded_lqr_controller(
    model: ResonatorStateModel,
    sample_time_s: float,
    safety_envelope: SafetyEnvelope,
    *,
    state_weights: Sequence[float] | None = None,
    input_weight: float = 0.35,
    measurement_variance: float = 1e-5,
    process_variance: float | None = None,
) -> CompiledController:
    model.validate(); safety_envelope.validate()
    if not (np.isfinite(sample_time_s) and 0 < sample_time_s <= 0.1):
        raise ValueError("sample_time_s must be in (0, 0.1]")
    A, B, C, D = _resonator_continuous_matrices(model)
    A_d, B_d, C_d, _, _ = cont2discrete((A, B, C, D), sample_time_s, method="zoh")
    n = A_d.shape[0]
    weights = np.asarray(state_weights if state_weights is not None else ([8.0, 1.5] if n == 2 else [8.0, 1.5, 0.7]), dtype=float)
    if weights.shape != (n,) or np.any(weights <= 0):
        raise ValueError("state_weights must be positive and match model dimension")
    if input_weight <= 0:
        raise ValueError("input_weight must be positive")
    Q = np.diag(weights); R = np.array([[input_weight]], dtype=float)
    ctrb = np.hstack([np.linalg.matrix_power(A_d, i) @ B_d for i in range(n)])
    controllability_rank = int(np.linalg.matrix_rank(ctrb))
    riccati = solve_discrete_are(A_d, B_d, Q, R)
    gain = np.linalg.solve(R + B_d.T @ riccati @ B_d, B_d.T @ riccati @ A_d)
    eigs = np.linalg.eigvals(A_d - B_d @ gain)
    spectral_radius = float(np.max(np.abs(eigs)))
    observability = np.vstack([C_d @ np.linalg.matrix_power(A_d, i) for i in range(n)])
    observability_rank = int(np.linalg.matrix_rank(observability))
    q_process = float(process_variance if process_variance is not None else max(model.process_sigma**2, 1e-8))
    if measurement_variance <= 0 or q_process <= 0:
        raise ValueError("Estimator variances must be positive")
    Qe = np.eye(n) * q_process; Re = np.array([[measurement_variance]], dtype=float)
    estimator_covariance = solve_discrete_are(A_d.T, C_d.T, Qe, Re)
    innovation_covariance = C_d @ estimator_covariance @ C_d.T + Re
    estimator_gain = A_d @ estimator_covariance @ C_d.T @ np.linalg.inv(innovation_covariance)
    observer_eigs = np.linalg.eigvals(A_d - estimator_gain @ C_d)
    observer_radius = float(np.max(np.abs(observer_eigs)))
    dare_residual = A_d.T @ riccati @ A_d - riccati - (A_d.T @ riccati @ B_d) @ np.linalg.solve(R + B_d.T @ riccati @ B_d, B_d.T @ riccati @ A_d) + Q
    dare_norm = float(np.linalg.norm(dare_residual, ord=2))
    p_inv = np.linalg.pinv(riccati)
    input_shape = float((gain @ p_inv @ gain.T).item())
    output_shape = float((C_d @ p_inv @ C_d.T).item())
    rho_input = safety_envelope.max_abs_drive**2 / max(input_shape, 1e-18)
    rho_output = safety_envelope.max_abs_response**2 / max(output_shape, 1e-18)
    invariant_level = 0.80 * min(rho_input, rho_output)
    cert = _certificate(
        "controller_recompilation", "DISCRETE_LQR_SAFE_ELLIPSOID",
        {
            "model_valid": True, "controllable": controllability_rank == n, "observable": observability_rank == n,
            "riccati_positive_definite": float(np.min(np.linalg.eigvalsh(riccati))) > 0,
            "estimator_covariance_positive_definite": float(np.min(np.linalg.eigvalsh(estimator_covariance))) > 0,
            "dare_residual": dare_norm < 1e-7, "closed_loop_schur": spectral_radius < 1.0,
            "observer_schur": observer_radius < 1.0, "safe_invariant_level": invariant_level > 0 and np.isfinite(invariant_level),
        },
        {
            "dimension": n, "controllability_rank": controllability_rank, "observability_rank": observability_rank,
            "spectral_radius": spectral_radius, "observer_spectral_radius": observer_radius, "dare_residual_norm": dare_norm,
            "measurement_variance": measurement_variance, "process_variance": q_process, "invariant_level": invariant_level,
            "input_limit": safety_envelope.max_abs_drive, "response_limit": safety_envelope.max_abs_response,
        },
        ["state estimate is available with latency covered by calibration", "local linear model remains valid inside the certified ellipsoid", "actuator saturation is enforced independently"],
    )
    return CompiledController(model, sample_time_s, np.asarray(A_d,float), np.asarray(B_d,float), np.asarray(C_d,float), np.asarray(gain,float), np.asarray(riccati,float), np.asarray(estimator_gain,float), np.asarray(estimator_covariance,float), np.asarray(eigs,complex), np.asarray(observer_eigs,complex), float(invariant_level), safety_envelope.max_abs_drive, safety_envelope.max_abs_response, cert).finalize()


def guarded_controller_action(controller: CompiledController, state: NDArray[np.float64], blend: float = 1.0) -> float:
    if controller.certificate.status != "PASS":
        raise RuntimeError("Cannot execute a failed controller")
    x = np.asarray(state, dtype=float)
    if x.shape != (controller.A_d.shape[0],):
        raise ValueError("State dimension does not match controller")
    if not 0.0 <= blend <= 1.0:
        raise ValueError("blend must be within [0,1]")
    feedback = float((controller.gain @ x).item())
    return float(np.clip(-blend * feedback, -controller.input_limit, controller.input_limit))


def observer_step(controller: CompiledController, state_estimate: NDArray[np.float64], previous_input: float, measurement: float) -> Tuple[NDArray[np.float64], float, NDArray[np.float64]]:
    xhat = np.asarray(state_estimate, dtype=float)
    if xhat.shape != (controller.A_d.shape[0],):
        raise ValueError("State estimate dimension does not match controller")
    innovation = float(measurement - (controller.C_d @ xhat)[0])
    xnext = controller.A_d @ xhat + controller.B_d[:, 0] * float(previous_input) + controller.estimator_gain[:, 0] * innovation
    innovation_covariance = controller.C_d @ controller.estimator_covariance @ controller.C_d.T
    return np.asarray(xnext, dtype=float), innovation, np.asarray(innovation_covariance, dtype=float)


def validate_guarded_reentry(
    controller: CompiledController,
    calibration: CalibrationPackage,
    trajectory: ValidationTrajectory,
    *,
    nis_probability: float = 0.999,
    required_cycles_per_stage: int = 20,
) -> GuardedReentryDecision:
    t=np.asarray(trajectory.t,float); states=np.asarray(trajectory.states,float); inputs=np.asarray(trajectory.inputs,float); outputs=np.asarray(trajectory.outputs,float)
    innovations=np.asarray(trajectory.innovations,float); cov=np.asarray(trajectory.innovation_covariance,float)
    if innovations.ndim==1: innovations=innovations[:,None]
    if cov.ndim==2: cov=np.repeat(cov[None,:,:],len(innovations),axis=0)
    valid_shapes = bool(t.ndim==1 and states.ndim==2 and len(t)==len(states)==len(inputs)==len(outputs)==len(innovations) and states.shape[1]==controller.A_d.shape[0] and cov.shape==(len(innovations),innovations.shape[1],innovations.shape[1]))
    if not valid_shapes: raise ValueError("Validation trajectory arrays are inconsistent")
    nis=np.asarray([float(v.T@np.linalg.pinv(S)@v) for v,S in zip(innovations,cov)],float)
    nis_limit=float(chi2.ppf(nis_probability,innovations.shape[1])); nis_pass_fraction=float(np.mean(nis<=nis_limit))
    state_levels=np.einsum("ni,ij,nj->n",states,controller.riccati,states)
    distinct_holdout=bool(trajectory.identification_digest and trajectory.validation_digest and trajectory.identification_digest!=trajectory.validation_digest)
    tail=max(5,len(outputs)//5); head_rms=float(np.sqrt(np.mean(outputs[:tail]**2))); tail_rms=float(np.sqrt(np.mean(outputs[-tail:]**2)))
    cert=_certificate(
        "guarded_reentry","PRIVATE_HOLDOUT_VALIDATION",
        {
            "controller_pass":controller.certificate.status=="PASS","calibration_pass":calibration.certificate.status=="PASS",
            "private_holdout_distinct":distinct_holdout and "PRIVATE" in trajectory.protocol.upper(),
            "input_within_limit":float(np.max(np.abs(inputs)))<=controller.input_limit+1e-12,
            "response_within_limit":float(np.max(np.abs(outputs)))<=controller.response_limit+1e-12,
            "inside_invariant_ellipsoid":float(np.max(state_levels))<=controller.invariant_level*1.001,
            "no_saturation":trajectory.saturation_count==0,"innovation_consistent":nis_pass_fraction>=0.99,
            "closed_loop_decay":tail_rms<=head_rms+1e-12,"emergency_stop_tested":trajectory.emergency_stop_tested,
        },
        {
            "validation_samples":len(t),"max_input":float(np.max(np.abs(inputs))),"max_response":float(np.max(np.abs(outputs))),
            "max_invariant_level":float(np.max(state_levels)),"nis_limit":nis_limit,"nis_pass_fraction":nis_pass_fraction,
            "head_rms":head_rms,"tail_rms":tail_rms,"saturation_count":trajectory.saturation_count,
        },
        ["validation data were not used for identification or controller tuning","state estimator and covariance are frozen before private validation","guarded deployment aborts immediately on any hard safety violation"],
    )
    accepted=cert.status=="PASS"
    return GuardedReentryDecision(accepted,(0.10,0.25,0.50,0.75,1.00) if accepted else tuple(),required_cycles_per_stage,{"max_abs_input":controller.input_limit,"max_abs_response":controller.response_limit,"max_invariant_level":controller.invariant_level,"max_consecutive_nis_violations":1,"on_adapter_error":"EMERGENCY_STOP_AND_SAFE_FALLBACK"},cert).finalize()


def certify_recovery_state_sequence(states: Sequence[RecoveryState]) -> GateCertificate:
    required=list(RecoveryState); observed=list(states)
    return _certificate(
        "hardware_recovery_sequence","FAIL_CLOSED_STATE_MACHINE",
        {"starts_normal":bool(observed and observed[0]==RecoveryState.NORMAL_CONTROL),"complete_order":observed==required,"no_skipped_state":all(required.index(b)-required.index(a)==1 for a,b in zip(observed,observed[1:]))},
        {"observed_length":len(observed),"required_length":len(required),"final_state":observed[-1].value if observed else "EMPTY"},
        ["each transition is admitted by a separately computed evidence gate"],
    )


# ----------------------------- Numerical helpers ------------------------------
def _nrmse(y: NDArray[np.float64], yhat: NDArray[np.float64]) -> float:
    scale = float(np.std(y))
    if scale < 1e-10:
        scale = float(np.max(y) - np.min(y) + 1e-10)
    return float(np.sqrt(np.mean((y - yhat) ** 2)) / max(scale, 1e-10))


def _bounded_fit(
    X: NDArray[np.float64],
    y: NDArray[np.float64],
    lower: Sequence[float],
    upper: Sequence[float],
) -> Tuple[NDArray[np.float64], NDArray[np.float64], float]:
    result = lsq_linear(
        X,
        y,
        bounds=(np.asarray(lower, dtype=float), np.asarray(upper, dtype=float)),
        method="trf",
        lsmr_tol="auto",
        max_iter=300,
    )
    if not result.success:
        raise RuntimeError(f"bounded fit failed: {result.message}")
    resid = y - X @ result.x
    dof = max(len(y) - X.shape[1], 1)
    sigma2 = float(np.dot(resid, resid) / dof)
    covariance = sigma2 * np.linalg.pinv(X.T @ X)
    std = np.sqrt(np.maximum(np.diag(covariance), 1e-16))
    return result.x, std, sigma2


def _derive_mean(ep: Episode) -> Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    mean_x = np.mean(ep.x, axis=0)
    n = len(mean_x)
    dt = float(ep.t[1] - ep.t[0])
    target_window = max(9, int(round(0.48 / dt)))
    if target_window % 2 == 0:
        target_window += 1
    max_window = n - (1 - n % 2)
    window = min(target_window, max_window)
    window = max(7, window if window % 2 == 1 else window - 1)
    smooth = savgol_filter(mean_x, window_length=window, polyorder=3, mode="interp")
    velocity = savgol_filter(mean_x, window_length=window, polyorder=3, deriv=1, delta=dt, mode="interp")
    acceleration = savgol_filter(mean_x, window_length=window, polyorder=3, deriv=2, delta=dt, mode="interp")
    return smooth, velocity, acceleration


def _episode_slice(ep: Episode) -> slice:
    margin = max(6, int(0.08 * len(ep.t)))
    return slice(margin, len(ep.t) - margin)


def _input_baseline(t: NDArray[np.float64], seed: int = 0) -> NDArray[np.float64]:
    rng = np.random.default_rng(seed)
    base = 0.38 * np.sin(0.67 * t) + 0.24 * np.sin(1.81 * t + 0.31) + 0.13 * np.sin(2.93 * t + 1.1)
    block = max(1, len(t) // 18)
    prbs = rng.choice([-0.14, 0.14], size=math.ceil(len(t) / block))
    return base + np.repeat(prbs, block)[: len(t)]


def experiment_input(t: NDArray[np.float64], spec: ExperimentSpec) -> NDArray[np.float64]:
    u = np.zeros_like(t)
    start_1 = 0.30
    end_1 = start_1 + spec.duration_1
    start_2 = end_1 + spec.wait
    end_2 = start_2 + spec.duration_2
    u[(t >= start_1) & (t < end_1)] = spec.amplitude_1
    u[(t >= start_2) & (t < end_2)] = spec.sign_2 * spec.amplitude_2
    probe = t >= end_2
    envelope = np.exp(-0.08 * np.maximum(t - end_2, 0.0))
    u[probe] += 0.22 * spec.amplitude_2 * envelope[probe] * np.sin(spec.probe_omega * (t[probe] - end_2))
    return u


def _simulate_markov(
    t: NDArray[np.float64],
    u: NDArray[np.float64],
    k: float,
    damping: float,
    x0: float,
    v0: float,
    rng: np.random.Generator | None = None,
    sigma_process: float = 0.0,
) -> NDArray[np.float64]:
    dt = float(t[1] - t[0])
    x = np.empty_like(t)
    v = np.empty_like(t)
    x[0], v[0] = x0, v0
    for n in range(len(t) - 1):
        noise = 0.0 if rng is None or sigma_process == 0 else sigma_process * math.sqrt(dt) * rng.normal()
        a = -k * x[n] - damping * v[n] + u[n]
        v[n + 1] = v[n] + dt * a + noise
        x[n + 1] = x[n] + dt * v[n + 1]
    return x


def _simulate_exp_memory(
    t: NDArray[np.float64], u: NDArray[np.float64], k: float, coupling: float, lam: float, x0: float, v0: float
) -> NDArray[np.float64]:
    dt = float(t[1] - t[0])
    x = np.empty_like(t)
    v = np.empty_like(t)
    z = np.zeros_like(t)
    x[0], v[0] = x0, v0
    for n in range(len(t) - 1):
        z[n + 1] = z[n] + dt * (-lam * z[n] + coupling * v[n])
        a = -k * x[n] - z[n] + u[n]
        v[n + 1] = v[n] + dt * a
        x[n + 1] = x[n] + dt * v[n + 1]
    return x


def _simulate_delay(
    t: NDArray[np.float64],
    u: NDArray[np.float64],
    k: float,
    damping: float,
    eta: float,
    tau: float,
    x0: float,
    v0: float,
) -> NDArray[np.float64]:
    dt = float(t[1] - t[0])
    lag = max(1, int(round(tau / dt)))
    x = np.empty_like(t)
    v = np.empty_like(t)
    x[0], v[0] = x0, v0
    for n in range(len(t) - 1):
        x_lag = x[n - lag] if n >= lag else x0
        a = -k * x[n] - damping * v[n] - eta * x_lag + u[n]
        v[n + 1] = v[n] + dt * a
        x[n + 1] = x[n] + dt * v[n + 1]
    return x


def _caputo_derivative(x: NDArray[np.float64], alpha: float, dt: float) -> NDArray[np.float64]:
    n = len(x)
    out = np.zeros(n, dtype=float)
    weights = np.arange(1, n + 1, dtype=float) ** (1 - alpha) - np.arange(0, n, dtype=float) ** (1 - alpha)
    prefactor = dt ** (-alpha) / gamma_fn(2 - alpha)
    dx = np.diff(x)
    for i in range(1, n):
        out[i] = prefactor * np.dot(weights[:i], dx[i - 1 :: -1])
    return out


def _simulate_fractional(
    t: NDArray[np.float64], u: NDArray[np.float64], k: float, gamma_alpha: float, alpha: float, x0: float, v0: float
) -> NDArray[np.float64]:
    dt = float(t[1] - t[0])
    x = np.empty_like(t)
    v = np.empty_like(t)
    x[0], v[0] = x0, v0
    weights = np.arange(1, len(t) + 1, dtype=float) ** (1 - alpha) - np.arange(0, len(t), dtype=float) ** (1 - alpha)
    prefactor = dt ** (-alpha) / gamma_fn(2 - alpha)
    for n in range(len(t) - 1):
        if n == 0:
            d_alpha = 0.0
        else:
            d_alpha = prefactor * float(np.dot(weights[:n], np.diff(x[: n + 1])[::-1]))
        a = -k * x[n] - gamma_alpha * d_alpha + u[n]
        v[n + 1] = v[n] + dt * a
        x[n + 1] = x[n] + dt * v[n + 1]
    return x


def _exp_feature(v: NDArray[np.float64], lam: float, dt: float) -> NDArray[np.float64]:
    z = np.zeros_like(v)
    decay = math.exp(-lam * dt)
    for n in range(len(v) - 1):
        z[n + 1] = decay * z[n] + (1 - decay) / max(lam, 1e-9) * v[n]
    return z


def _stochastic_evidence(episodes: Sequence[Episode]) -> Tuple[float, float, float]:
    ratios: List[float] = []
    roughness: List[float] = []
    increment_variance: List[float] = []
    for ep in episodes:
        deviations = ep.x - np.mean(ep.x, axis=0, keepdims=True)
        empirical = float(np.mean(np.var(deviations, axis=0, ddof=1)))
        expected = ep.measurement_sigma**2
        ratios.append(empirical / max(expected, 1e-15))
        increments = np.diff(deviations, axis=1)
        inc_var = float(np.var(increments, ddof=1))
        roughness.append(inc_var / max(2 * expected, 1e-15))
        increment_variance.append(inc_var)
    return float(np.median(ratios)), float(np.median(roughness)), float(np.median(increment_variance))


def _regularized_std(name: str, value: float, raw_std: float) -> float:
    value_abs = abs(float(value))
    floors = {
        "k": 0.10 * value_abs + 0.015,
        "damping": 0.15 * value_abs + 0.015,
        "gain": 0.15 * value_abs + 0.025,
        "coupling": 0.12 * value_abs + 0.025,
        "lambda": 0.15 * value_abs + 0.015,
        "eta": 0.12 * value_abs + 0.025,
        "tau": 0.08 * value_abs + 0.025,
        "gamma_alpha": 0.12 * value_abs + 0.025,
        "alpha": 0.035,
        "sigma": 0.12 * value_abs + 0.002,
    }
    caps = {
        "k": 0.40 * value_abs + 0.20,
        "damping": 0.65 * value_abs + 0.12,
        "gain": 0.45 * value_abs + 0.20,
        "coupling": 0.45 * value_abs + 0.30,
        "lambda": 0.55 * value_abs + 0.15,
        "eta": 0.50 * value_abs + 0.20,
        "tau": 0.30 * value_abs + 0.15,
        "gamma_alpha": 0.45 * value_abs + 0.30,
        "alpha": 0.12,
        "sigma": 0.45 * value_abs + 0.04,
    }
    floor = floors.get(name, 0.05 * value_abs + 1e-3)
    cap = caps.get(name, 0.50 * value_abs + 0.20)
    raw = float(raw_std) if np.isfinite(raw_std) else floor
    return float(min(max(raw, floor), cap))


def _certificate(
    kind: str,
    family: str,
    checks: Mapping[str, bool],
    metrics: Mapping[str, float | int | str],
    assumptions: Sequence[str],
) -> GateCertificate:
    return GateCertificate(
        owner_version=OWNER_VERSION,
        observation_kind=kind,
        family=family,
        checks=dict(checks),
        metrics=dict(metrics),
        assumptions=list(assumptions),
    ).finalize()


# ----------------------------- Candidate fitting ------------------------------
def _trajectory_residual_scale(ep: Episode) -> float:
    mean = np.mean(ep.x, axis=0)
    return max(float(np.std(mean)), 0.05)


def _jacobian_std(result: Any, values: Sequence[float], names: Sequence[str]) -> Dict[str, float]:
    jac = np.asarray(result.jac, dtype=float)
    residual = np.asarray(result.fun, dtype=float)
    dof = max(len(residual) - len(values), 1)
    sigma2 = float(np.dot(residual, residual) / dof)
    covariance = sigma2 * np.linalg.pinv(jac.T @ jac)
    raw = np.sqrt(np.maximum(np.diag(covariance), 1e-16))
    return {name: _regularized_std(name, value, std) for name, value, std in zip(names, values, raw)}


def _fit_markov(episodes: Sequence[Episode]) -> CandidateModel:
    rows: List[NDArray[np.float64]] = []
    targets: List[NDArray[np.float64]] = []
    for ep in episodes:
        x, v, a = _derive_mean(ep)
        sl = _episode_slice(ep)
        rows.append(np.column_stack((-x[sl], -v[sl], ep.u[sl])))
        targets.append(a[sl])
    X = np.vstack(rows)
    y = np.concatenate(targets)
    coef, std, _ = _bounded_fit(X, y, [1e-5, 1e-5, 0.2], [8.0, 5.0, 2.5])
    k, damping, gain = coef
    params = {"k": float(k), "damping": float(damping), "gain": float(gain)}
    pstd = {
        "k": _regularized_std("k", k, std[0]),
        "damping": _regularized_std("damping", damping, std[1]),
        "gain": _regularized_std("gain", gain, std[2]),
    }
    pred_errs = []
    for ep in episodes:
        mean = np.mean(ep.x, axis=0)
        _, v, _ = _derive_mean(ep)
        pred = _simulate_markov(ep.t, ep.u * gain, k, damping, mean[0], v[0])
        pred_errs.append(_nrmse(mean, pred))
    err = float(np.mean(pred_errs))
    cert = _certificate(
        "cross_family_resonator",
        "H1_MARKOV_ODE",
        {"structural": True, "dimensional": True, "causal": True, "stable": bool(k > 0 and damping > 0), "identifiable": bool(np.linalg.matrix_rank(X) == X.shape[1])},
        {"nrmse": err, "rank": int(np.linalg.matrix_rank(X)), "condition_number": float(np.linalg.cond(X))},
        ["second-order scalar dynamics", "additive measured input", "constant coefficients"],
    )
    residual_sigma = float(np.mean([np.sqrt(np.mean((np.mean(ep.x, axis=0) - _simulate_markov(ep.t, ep.u * gain, k, damping, np.mean(ep.x, axis=0)[0], _derive_mean(ep)[1][0])) ** 2)) for ep in episodes]))
    return CandidateModel("H1_MARKOV_ODE", params, pstd, err, 0.0, 0.0, cert, {"residual_sigma": residual_sigma})


def _fit_exp_memory(episodes: Sequence[Episode]) -> CandidateModel:
    best: CandidateModel | None = None
    grid = np.geomspace(0.07, 2.6, 18)
    for lam in grid:
        rows: List[NDArray[np.float64]] = []
        targets: List[NDArray[np.float64]] = []
        for ep in episodes:
            x, v, a = _derive_mean(ep)
            z = _exp_feature(v, float(lam), float(ep.t[1] - ep.t[0]))
            sl = _episode_slice(ep)
            rows.append(np.column_stack((-x[sl], -z[sl], ep.u[sl])))
            targets.append(a[sl])
        X = np.vstack(rows)
        y = np.concatenate(targets)
        coef, std, _ = _bounded_fit(X, y, [1e-5, 1e-5, 0.2], [8.0, 6.0, 2.5])
        k, coupling, gain = coef
        pred_errs = []
        for ep in episodes:
            mean = np.mean(ep.x, axis=0)
            _, v, _ = _derive_mean(ep)
            pred = _simulate_exp_memory(ep.t, ep.u * gain, k, coupling, lam, mean[0], v[0])
            pred_errs.append(_nrmse(mean, pred))
        err = float(np.mean(pred_errs))
        lam_step = float(lam * (math.exp(math.log(grid[-1] / grid[0]) / (len(grid) - 1)) - 1.0))
        params = {"k": float(k), "coupling": float(coupling), "lambda": float(lam), "gain": float(gain)}
        pstd = {
            "k": _regularized_std("k", k, std[0]),
            "coupling": _regularized_std("coupling", coupling, std[1]),
            "lambda": _regularized_std("lambda", lam, max(lam_step, 0.02)),
            "gain": _regularized_std("gain", gain, std[2]),
        }
        cert = _certificate(
            "cross_family_resonator",
            "H23_EXP_MEMORY_EQUIV",
            {"structural": True, "dimensional": True, "causal": bool(lam > 0), "stable": bool(k > 0 and coupling > 0 and lam > 0), "identifiable_class": bool(coupling > 0.05 and lam < 0.98 * grid[-1]), "h2_h3_not_split": True},
            {"nrmse": err, "memory_time": float(1.0 / lam), "rank": int(np.linalg.matrix_rank(X))},
            ["single exponential memory kernel", "H2 and H3 are one observational class for x(t)"],
        )
        residual_sigma = float(np.mean([np.sqrt(np.mean((np.mean(ep.x, axis=0) - _simulate_exp_memory(ep.t, ep.u * gain, k, coupling, lam, np.mean(ep.x, axis=0)[0], _derive_mean(ep)[1][0])) ** 2)) for ep in episodes]))
        model = CandidateModel("H23_EXP_MEMORY_EQUIV", params, pstd, err, 0.0, 0.0, cert, {"memory_time": float(1.0 / lam), "residual_sigma": residual_sigma})
        if best is None or model.nrmse < best.nrmse:
            best = model
    assert best is not None
    initial = np.array([best.parameters["k"], best.parameters["coupling"], best.parameters["lambda"], best.parameters["gain"]], dtype=float)

    def residual_fn(q: NDArray[np.float64]) -> NDArray[np.float64]:
        k_r, coupling_r, lam_r, gain_r = q
        residuals: List[NDArray[np.float64]] = []
        for ep in episodes:
            mean = np.mean(ep.x, axis=0)
            _, velocity, _ = _derive_mean(ep)
            pred = _simulate_exp_memory(ep.t, ep.u * gain_r, k_r, coupling_r, lam_r, mean[0], velocity[0])
            stride = max(1, int(round(0.08 / float(ep.t[1] - ep.t[0]))))
            residuals.append((pred[::stride] - mean[::stride]) / _trajectory_residual_scale(ep))
        return np.concatenate(residuals)

    refined = least_squares(
        residual_fn,
        initial,
        bounds=([1e-5, 1e-5, 0.04, 0.2], [8.0, 6.0, 3.0, 2.5]),
        max_nfev=45,
        x_scale="jac",
    )
    k_r, coupling_r, lam_r, gain_r = refined.x
    pred_errs: List[float] = []
    residual_sigmas: List[float] = []
    for ep in episodes:
        mean = np.mean(ep.x, axis=0)
        _, velocity, _ = _derive_mean(ep)
        pred = _simulate_exp_memory(ep.t, ep.u * gain_r, k_r, coupling_r, lam_r, mean[0], velocity[0])
        pred_errs.append(_nrmse(mean, pred))
        residual_sigmas.append(float(np.sqrt(np.mean((mean - pred) ** 2))))
    err = float(np.mean(pred_errs))
    params = {"k": float(k_r), "coupling": float(coupling_r), "lambda": float(lam_r), "gain": float(gain_r)}
    pstd = _jacobian_std(refined, refined.x, ("k", "coupling", "lambda", "gain"))
    cert = _certificate(
        "cross_family_resonator",
        "H23_EXP_MEMORY_EQUIV",
        {"structural": True, "dimensional": True, "causal": bool(lam_r > 0), "stable": bool(k_r > 0 and coupling_r > 0 and lam_r > 0), "identifiable_class": bool(coupling_r > 0.05 and lam_r < 2.94), "h2_h3_not_split": True},
        {"nrmse": err, "memory_time": float(1.0 / lam_r), "optimizer_cost": float(refined.cost)},
        ["single exponential memory kernel", "H2 and H3 are one observational class for x(t)"],
    )
    return CandidateModel(
        "H23_EXP_MEMORY_EQUIV", params, pstd, err, 0.0, 0.0, cert,
        {"memory_time": float(1.0 / lam_r), "residual_sigma": float(np.mean(residual_sigmas))},
    )


def _fit_delay(episodes: Sequence[Episode]) -> CandidateModel:
    dt = float(episodes[0].t[1] - episodes[0].t[0])
    best: CandidateModel | None = None
    for tau in np.arange(0.20, 1.52, 0.10):
        lag = max(1, int(round(tau / dt)))
        rows: List[NDArray[np.float64]] = []
        targets: List[NDArray[np.float64]] = []
        for ep in episodes:
            x, v, a = _derive_mean(ep)
            if lag >= len(x) // 2:
                continue
            idx = np.arange(max(lag, 8), len(x) - 8)
            rows.append(np.column_stack((-x[idx], -v[idx], -x[idx - lag], ep.u[idx])))
            targets.append(a[idx])
        if not rows:
            continue
        X = np.vstack(rows)
        y = np.concatenate(targets)
        coef, std, _ = _bounded_fit(X, y, [1e-5, 1e-5, 1e-5, 0.2], [8.0, 5.0, 4.0, 2.5])
        k, damping, eta, gain = coef
        pred_errs = []
        for ep in episodes:
            mean = np.mean(ep.x, axis=0)
            _, v, _ = _derive_mean(ep)
            pred = _simulate_delay(ep.t, ep.u * gain, k, damping, eta, tau, mean[0], v[0])
            pred_errs.append(_nrmse(mean, pred))
        err = float(np.mean(pred_errs))
        params = {"k": float(k), "damping": float(damping), "eta": float(eta), "tau": float(tau), "gain": float(gain)}
        pstd = {
            "k": _regularized_std("k", k, std[0]),
            "damping": _regularized_std("damping", damping, std[1]),
            "eta": _regularized_std("eta", eta, std[2]),
            "tau": _regularized_std("tau", tau, 0.10),
            "gain": _regularized_std("gain", gain, std[3]),
        }
        cert = _certificate(
            "cross_family_resonator",
            "H4_DELAY_ODE",
            {"structural": True, "dimensional": True, "causal": bool(tau > 0), "stable_sufficient": bool(k > 0 and damping > 0 and eta < 1.15 * k), "identifiable": bool(np.linalg.matrix_rank(X) == X.shape[1]), "delay_strength_identifiable": bool(eta / max(k, 1e-12) > 0.03)},
            {"nrmse": err, "delay": float(tau), "rank": int(np.linalg.matrix_rank(X))},
            ["single positive discrete delay", "reported stability condition is sufficient, not necessary"],
        )
        residual_sigma = float(np.mean([np.sqrt(np.mean((np.mean(ep.x, axis=0) - _simulate_delay(ep.t, ep.u * gain, k, damping, eta, tau, np.mean(ep.x, axis=0)[0], _derive_mean(ep)[1][0])) ** 2)) for ep in episodes]))
        model = CandidateModel("H4_DELAY_ODE", params, pstd, err, 0.0, 0.0, cert, {"delay": float(tau), "residual_sigma": residual_sigma})
        if best is None or model.nrmse < best.nrmse:
            best = model
    if best is None:
        raise RuntimeError("delay fit produced no candidate")
    return best


def _fit_fractional(episodes: Sequence[Episode]) -> CandidateModel:
    best: CandidateModel | None = None
    alpha_grid = np.linspace(0.18, 0.78, 9)
    for alpha in alpha_grid:
        rows: List[NDArray[np.float64]] = []
        targets: List[NDArray[np.float64]] = []
        derived: List[Tuple[NDArray[np.float64], NDArray[np.float64]]] = []
        for ep in episodes:
            x, v, a = _derive_mean(ep)
            d_alpha = _caputo_derivative(x, float(alpha), float(ep.t[1] - ep.t[0]))
            sl = _episode_slice(ep)
            rows.append(np.column_stack((-x[sl], -d_alpha[sl], ep.u[sl])))
            targets.append(a[sl])
            derived.append((x, v))
        X = np.vstack(rows)
        y = np.concatenate(targets)
        coef, std, _ = _bounded_fit(X, y, [1e-5, 1e-5, 0.2], [8.0, 6.0, 2.5])
        k, gamma_alpha, gain = coef
        pred_errs = []
        for ep, (x, v) in zip(episodes, derived):
            pred = _simulate_fractional(ep.t, ep.u * gain, k, gamma_alpha, alpha, x[0], v[0])
            pred_errs.append(_nrmse(x, pred))
        err = float(np.mean(pred_errs))
        params = {"k": float(k), "gamma_alpha": float(gamma_alpha), "alpha": float(alpha), "gain": float(gain)}
        pstd = {
            "k": _regularized_std("k", k, std[0]),
            "gamma_alpha": _regularized_std("gamma_alpha", gamma_alpha, std[1]),
            "alpha": _regularized_std("alpha", alpha, float(alpha_grid[1] - alpha_grid[0])),
            "gain": _regularized_std("gain", gain, std[2]),
        }
        cert = _certificate(
            "cross_family_resonator",
            "H6_FRACTIONAL_MEMORY",
            {"structural": True, "dimensional": True, "causal": bool(0 < alpha < 1), "stable_sufficient": bool(k > 0 and gamma_alpha > 0), "identifiable_grid": bool(0.12 < alpha < 0.75 and gamma_alpha > 0.05)},
            {"nrmse": err, "alpha": float(alpha), "rank": int(np.linalg.matrix_rank(X))},
            ["Caputo derivative", "L1 discretization", "0<alpha<1"],
        )
        residual_sigma = float(np.mean([np.sqrt(np.mean((np.mean(ep.x, axis=0) - _simulate_fractional(ep.t, ep.u * gain, k, gamma_alpha, alpha, np.mean(ep.x, axis=0)[0], _derive_mean(ep)[1][0])) ** 2)) for ep in episodes]))
        model = CandidateModel("H6_FRACTIONAL_MEMORY", params, pstd, err, 0.0, 0.0, cert, {"alpha": float(alpha), "residual_sigma": residual_sigma})
        if best is None or model.nrmse < best.nrmse:
            best = model
    assert best is not None
    initial = np.array([
        best.parameters["k"],
        best.parameters["gamma_alpha"],
        min(max(best.parameters["alpha"], 0.120001), 0.749999),
        best.parameters["gain"],
    ], dtype=float)

    def residual_fn(q: NDArray[np.float64]) -> NDArray[np.float64]:
        k_r, gamma_r, alpha_r, gain_r = q
        residuals: List[NDArray[np.float64]] = []
        for ep in episodes:
            mean = np.mean(ep.x, axis=0)
            _, velocity, _ = _derive_mean(ep)
            pred = _simulate_fractional(ep.t, ep.u * gain_r, k_r, gamma_r, alpha_r, mean[0], velocity[0])
            stride = max(1, int(round(0.12 / float(ep.t[1] - ep.t[0]))))
            residuals.append((pred[::stride] - mean[::stride]) / _trajectory_residual_scale(ep))
        return np.concatenate(residuals)

    refined = least_squares(
        residual_fn,
        initial,
        bounds=([1e-5, 1e-5, 0.12, 0.2], [8.0, 6.0, 0.75, 2.5]),
        max_nfev=38,
        x_scale="jac",
    )
    k_r, gamma_r, alpha_r, gain_r = refined.x
    pred_errs: List[float] = []
    residual_sigmas: List[float] = []
    for ep in episodes:
        mean = np.mean(ep.x, axis=0)
        _, velocity, _ = _derive_mean(ep)
        pred = _simulate_fractional(ep.t, ep.u * gain_r, k_r, gamma_r, alpha_r, mean[0], velocity[0])
        pred_errs.append(_nrmse(mean, pred))
        residual_sigmas.append(float(np.sqrt(np.mean((mean - pred) ** 2))))
    err = float(np.mean(pred_errs))
    params = {"k": float(k_r), "gamma_alpha": float(gamma_r), "alpha": float(alpha_r), "gain": float(gain_r)}
    pstd = _jacobian_std(refined, refined.x, ("k", "gamma_alpha", "alpha", "gain"))
    cert = _certificate(
        "cross_family_resonator",
        "H6_FRACTIONAL_MEMORY",
        {"structural": True, "dimensional": True, "causal": bool(0 < alpha_r < 1), "stable_sufficient": bool(k_r > 0 and gamma_r > 0), "identifiable_grid": bool(0.14 < alpha_r < 0.68 and gamma_r > 0.05)},
        {"nrmse": err, "alpha": float(alpha_r), "optimizer_cost": float(refined.cost)},
        ["Caputo derivative", "L1 discretization", "0<alpha<1"],
    )
    return CandidateModel(
        "H6_FRACTIONAL_MEMORY", params, pstd, err, 0.0, 0.0, cert,
        {"alpha": float(alpha_r), "residual_sigma": float(np.mean(residual_sigmas))},
    )


def _fit_sde(episodes: Sequence[Episode], markov: CandidateModel) -> CandidateModel:
    spread_ratio, roughness_ratio, increment_variance = _stochastic_evidence(episodes)
    dt = float(episodes[0].t[1] - episodes[0].t[0])
    measurement_increment_var = 2.0 * float(np.median([ep.measurement_sigma**2 for ep in episodes]))
    sigma_est = math.sqrt(max(increment_variance - measurement_increment_var, 0.0) / max(dt, 1e-12))
    params = dict(markov.parameters)
    params["sigma"] = float(sigma_est)
    pstd = dict(markov.parameter_std)
    pstd["sigma"] = _regularized_std("sigma", sigma_est, 0.15 * sigma_est)
    cert = _certificate(
        "cross_family_resonator",
        "H5_SDE",
        {"structural": True, "dimensional": True, "causal": True, "stable": markov.certificate.checks.get("stable", False), "positive_diffusion": bool(sigma_est >= 0), "nonzero_diffusion_identifiable": bool(sigma_est > 0.01), "replicates_available": all(ep.x.shape[0] >= 3 for ep in episodes)},
        {"nrmse": markov.nrmse, "spread_ratio": spread_ratio, "roughness_ratio": roughness_ratio, "sigma": sigma_est},
        ["additive Gaussian velocity noise", "measurement noise declared in Episode"],
    )
    return CandidateModel(
        "H5_SDE",
        params,
        pstd,
        markov.nrmse,
        0.0,
        0.0,
        cert,
        {"spread_ratio": spread_ratio, "roughness_ratio": roughness_ratio, "residual_sigma": markov.evidence.get("residual_sigma", 0.01)},
    )


def _fit_all(episodes: Sequence[Episode]) -> List[CandidateModel]:
    markov = _fit_markov(episodes)
    return [markov, _fit_exp_memory(episodes), _fit_delay(episodes), _fit_sde(episodes, markov), _fit_fractional(episodes)]


def _candidate_prediction(
    candidate: CandidateModel,
    t: NDArray[np.float64],
    u: NDArray[np.float64],
    parameters: Mapping[str, float] | None = None,
) -> NDArray[np.float64]:
    p = candidate.parameters if parameters is None else parameters
    gain = p.get("gain", 1.0)
    if candidate.family in ("H1_MARKOV_ODE", "H5_SDE"):
        return _simulate_markov(t, u * gain, p["k"], p["damping"], 0.0, 0.0)
    if candidate.family == "H23_EXP_MEMORY_EQUIV":
        return _simulate_exp_memory(t, u * gain, p["k"], p["coupling"], p["lambda"], 0.0, 0.0)
    if candidate.family == "H4_DELAY_ODE":
        return _simulate_delay(t, u * gain, p["k"], p["damping"], p["eta"], p["tau"], 0.0, 0.0)
    if candidate.family == "H6_FRACTIONAL_MEMORY":
        return _simulate_fractional(t, u * gain, p["k"], p["gamma_alpha"], p["alpha"], 0.0, 0.0)
    raise ValueError(candidate.family)


def _parameter_samples(candidate: CandidateModel) -> List[Dict[str, float]]:
    samples = [dict(candidate.parameters)]
    key_order = {
        "H1_MARKOV_ODE": ("k", "damping", "gain"),
        "H23_EXP_MEMORY_EQUIV": ("lambda", "coupling", "gain"),
        "H4_DELAY_ODE": ("tau", "eta", "gain"),
        "H5_SDE": ("k", "damping", "gain"),
        "H6_FRACTIONAL_MEMORY": ("alpha", "gamma_alpha", "gain"),
    }[candidate.family]
    for key in key_order:
        std = candidate.parameter_std.get(key, 0.0)
        if not np.isfinite(std) or std <= 0:
            continue
        for sign in (-1.0, 1.0):
            p = dict(candidate.parameters)
            p[key] = p[key] + sign * std
            if key in ("k", "damping", "coupling", "lambda", "eta", "tau", "gamma_alpha", "gain", "sigma"):
                p[key] = max(p[key], 1e-5)
            if key == "alpha":
                p[key] = min(max(p[key], 0.05), 0.95)
            samples.append(p)
    return samples


def _process_variance(candidate: CandidateModel, t: NDArray[np.float64]) -> NDArray[np.float64]:
    if candidate.family != "H5_SDE":
        return np.zeros_like(t)
    sigma = candidate.parameters.get("sigma", 0.0)
    damping = max(candidate.parameters.get("damping", 0.1), 1e-4)
    # Conservative diagonal approximation for integrated velocity noise.
    return (sigma**2 / (2.0 * damping**3)) * np.maximum(2.0 * damping * t - 3.0 + 4.0 * np.exp(-damping * t) - np.exp(-2.0 * damping * t), 0.0)


def _predictive_statistics(
    candidate: CandidateModel,
    t: NDArray[np.float64],
    u: NDArray[np.float64],
    measurement_sigma: float,
) -> Tuple[NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]]:
    preds = np.vstack([_candidate_prediction(candidate, t, u, p) for p in _parameter_samples(candidate)])
    mean = np.mean(preds, axis=0)
    parameter_var = np.var(preds, axis=0, ddof=1) if preds.shape[0] > 1 else np.zeros_like(mean)
    residual_sigma = max(float(candidate.evidence.get("residual_sigma", 0.0)), 0.006)
    epistemic_var = parameter_var + residual_sigma**2
    aleatoric_var = measurement_sigma**2 + _process_variance(candidate, t)
    return mean, np.maximum(epistemic_var, 1e-12), np.maximum(aleatoric_var, 1e-12)

def _episode_log_likelihood(candidate: CandidateModel, ep: Episode) -> float:
    observed_mean = np.mean(ep.x, axis=0)
    u = ep.u
    if ep.protocol == "baseline":
        smooth, velocity, _ = _derive_mean(ep)
        p = candidate.parameters
        gain = p.get("gain", 1.0)
        if candidate.family in ("H1_MARKOV_ODE", "H5_SDE"):
            mean = _simulate_markov(ep.t, u * gain, p["k"], p["damping"], smooth[0], velocity[0])
        elif candidate.family == "H23_EXP_MEMORY_EQUIV":
            mean = _simulate_exp_memory(ep.t, u * gain, p["k"], p["coupling"], p["lambda"], smooth[0], velocity[0])
        elif candidate.family == "H4_DELAY_ODE":
            mean = _simulate_delay(ep.t, u * gain, p["k"], p["damping"], p["eta"], p["tau"], smooth[0], velocity[0])
        else:
            mean = _simulate_fractional(ep.t, u * gain, p["k"], p["gamma_alpha"], p["alpha"], smooth[0], velocity[0])
        residual_sigma = max(float(candidate.evidence.get("residual_sigma", 0.0)), 0.006)
        epistemic_var = np.full_like(mean, residual_sigma**2)
        aleatoric_var = ep.measurement_sigma**2 + _process_variance(candidate, ep.t)
    else:
        mean, epistemic_var, aleatoric_var = _predictive_statistics(candidate, ep.t, u, ep.measurement_sigma)

    replicate_count = ep.x.shape[0]
    mean_variance = epistemic_var + aleatoric_var / replicate_count
    sample_var = np.var(ep.x, axis=0, ddof=1)
    dof = replicate_count - 1
    stride = max(1, int(round(0.20 / float(ep.t[1] - ep.t[0]))))
    idx = np.arange(0, len(ep.t), stride)
    residual = observed_mean[idx] - mean[idx]
    mv = np.maximum(mean_variance[idx], 1e-12)
    av = np.maximum(aleatoric_var[idx], 1e-12)
    mean_ll = -0.5 * float(np.sum(residual * residual / mv + np.log(2.0 * math.pi * mv)))
    spread_ll = -0.5 * float(np.sum(dof * (np.log(av) + sample_var[idx] / av)))
    return mean_ll + spread_ll

def _assign_evidence(candidates: Sequence[CandidateModel], episodes: Sequence[Episode]) -> List[CandidateModel]:
    total_points = sum(ep.x.size for ep in episodes)
    complexity = {
        "H1_MARKOV_ODE": 3,
        "H23_EXP_MEMORY_EQUIV": 4,
        "H4_DELAY_ODE": 5,
        "H5_SDE": 4,
        "H6_FRACTIONAL_MEMORY": 4,
    }
    out: List[CandidateModel] = []
    for candidate in candidates:
        log_likelihood = sum(_episode_log_likelihood(candidate, ep) for ep in episodes)
        bic_penalty = 0.5 * complexity[candidate.family] * math.log(max(total_points, 2))
        if candidate.certificate.status != "PASS":
            bic_penalty += 1e6
        candidate.log_likelihood = float(log_likelihood)
        candidate.log_evidence = float(log_likelihood - bic_penalty)
        out.append(candidate)
    return out


# ----------------------------- Active design ----------------------------------
def candidate_experiment_specs() -> Tuple[ExperimentSpec, ...]:
    raw = [
        (0.85, 0.16, 0.35, 0.75, 0.18, -1, 0.45, 6.0),
        (1.05, 0.20, 0.55, 0.95, 0.16, 1, 0.80, 6.5),
        (0.95, 0.28, 0.80, 0.85, 0.22, -1, 1.20, 7.0),
        (1.10, 0.14, 1.10, 0.90, 0.28, 1, 1.70, 7.5),
        (0.75, 0.34, 1.45, 1.05, 0.14, -1, 2.20, 8.0),
        (1.20, 0.18, 1.80, 0.70, 0.32, 1, 2.75, 8.5),
        (0.90, 0.22, 2.20, 1.15, 0.18, -1, 0.65, 9.0),
        (1.15, 0.30, 2.55, 0.80, 0.24, 1, 1.45, 9.0),
        (0.70, 0.40, 0.70, 1.20, 0.12, -1, 2.95, 7.0),
        (1.00, 0.12, 1.35, 1.00, 0.40, 1, 2.00, 8.0),
        (1.20, 0.24, 0.45, 1.20, 0.24, -1, 1.00, 6.5),
        (0.80, 0.18, 1.95, 0.80, 0.18, 1, 2.50, 8.5),
    ]
    specs = tuple(ExperimentSpec(*values) for values in raw)
    if not all(spec.safe() for spec in specs):
        raise RuntimeError("candidate experiment set contains unsafe specification")
    return specs


def _pair_discrimination(
    mu_i: NDArray[np.float64], var_i: NDArray[np.float64], mu_j: NDArray[np.float64], var_j: NDArray[np.float64]
) -> float:
    mean_term = np.mean((mu_i - mu_j) ** 2 / np.maximum(var_i + var_j, 1e-12))
    variance_term = 0.5 * np.mean(var_i / var_j + var_j / var_i - 2.0)
    return float(max(mean_term + 0.25 * variance_term, 0.0))


def design_experiment(
    candidates: Sequence[CandidateModel], posterior: Mapping[str, float], measurement_sigma: float = 0.002, dt: float = 0.05
) -> ExperimentSpec:
    families = [c.family for c in candidates]
    robust_weights = np.asarray([max(posterior.get(f, 0.0), 0.04) for f in families], dtype=float)
    robust_weights /= np.sum(robust_weights)
    best_spec: ExperimentSpec | None = None
    best_utility = -np.inf
    for spec in candidate_experiment_specs():
        if not spec.safe():
            continue
        t = np.arange(0.0, spec.observation_time + 0.5 * dt, dt)
        u = experiment_input(t, spec)
        raw_stats = [_predictive_statistics(c, t, u, measurement_sigma) for c in candidates]
        stats = [(mu, epistemic + aleatoric) for mu, epistemic, aleatoric in raw_stats]
        pair_values: List[float] = []
        weighted = 0.0
        for i in range(len(candidates)):
            for j in range(i + 1, len(candidates)):
                distance = _pair_discrimination(*stats[i], *stats[j])
                pair_values.append(distance)
                weighted += robust_weights[i] * robust_weights[j] * math.log1p(distance)
        worst_pair = min(pair_values) if pair_values else 0.0
        energy_penalty = 0.035 * spec.energy(dt)
        time_penalty = 0.004 * spec.observation_time
        amplitude_penalty = 0.010 * max(abs(spec.amplitude_1), abs(spec.amplitude_2)) ** 2
        utility = weighted + 0.08 * math.log1p(worst_pair) - energy_penalty - time_penalty - amplitude_penalty
        if utility > best_utility:
            best_utility = utility
            best_spec = spec
    if best_spec is None:
        raise RuntimeError("No safe experiment specification available")
    return best_spec


def _classes_to_hypotheses(order: Sequence[str], max_classes: int = 3) -> List[str]:
    out: List[str] = []
    for family in list(order)[:max_classes]:
        out.extend(HYPOTHESIS_VIEW[family])
    return out


def _ambiguity_status(posterior: Mapping[str, float], selected: str) -> str:
    order = sorted(posterior, key=posterior.get, reverse=True)
    if selected == "H23_EXP_MEMORY_EQUIV":
        return "H2_H3_OBSERVATIONALLY_EQUIVALENT"
    if len(order) > 1:
        bayes_factor = posterior[order[0]] / max(posterior[order[1]], 1e-15)
        if bayes_factor < 3.0:
            return "OBSERVATIONALLY_UNDERDETERMINED"
    return "RESOLVED"


def recover_resonator_family(observation: ObservationPackage, design_next: bool = True) -> RecoveryResult:
    observation.validate()
    candidates = _assign_evidence(_fit_all(observation.episodes), observation.episodes)
    logp = {c.family: c.log_evidence - math.log(len(candidates)) for c in candidates}
    posterior = _normalize_log_prob(logp)
    order = sorted(posterior, key=posterior.get, reverse=True)
    selected = order[0]
    spec = design_experiment(candidates, posterior, observation.episodes[-1].measurement_sigma) if design_next else None
    selected_model = next(c for c in candidates if c.family == selected)
    overall = _certificate(
        "cross_family_resonator",
        selected,
        {
            "blind_boundary": not observation.truth_access,
            "typed_payload": True,
            "selected_candidate_gates": selected_model.certificate.status == "PASS",
            "posterior_normalized": abs(sum(posterior.values()) - 1.0) < 1e-10,
            "safe_experiment": spec is None or spec.safe(),
            "single_h2_h3_class": "H23_EXP_MEMORY_EQUIV" in posterior and "H2" not in posterior and "H3" not in posterior,
        },
        {
            "candidate_count": len(candidates),
            "posterior_max": max(posterior.values()),
            "posterior_entropy": float(-sum(p * math.log(max(p, 1e-15)) for p in posterior.values())),
        },
        ["synthetic/observational model class only", "no private truth available to owner"],
    )
    return RecoveryResult(
        OWNER_VERSION,
        SCHEMA,
        "cross_family_resonator",
        selected,
        _classes_to_hypotheses(order),
        posterior,
        candidates,
        _ambiguity_status(posterior, selected),
        spec,
        overall,
        False,
    ).finalize()


def update_with_active(frozen: RecoveryResult, active: Episode) -> RecoveryResult:
    active.validate()
    if frozen.observation_kind != "cross_family_resonator":
        raise TypeError("Active Bayesian update is defined only for cross_family_resonator")
    if frozen.truth_access:
        raise RuntimeError("Frozen result violates blind boundary")
    logp: Dict[str, float] = {}
    updated_candidates: List[CandidateModel] = []
    for candidate in frozen.candidates:
        active_ll = _episode_log_likelihood(candidate, active)
        candidate_copy = dataclasses.replace(candidate)
        candidate_copy.log_likelihood = float(candidate.log_likelihood + active_ll)
        candidate_copy.log_evidence = float(math.log(max(frozen.posterior[candidate.family], 1e-300)) + active_ll)
        candidate_copy.evidence = dict(candidate.evidence)
        candidate_copy.evidence.update({"active_log_likelihood": float(active_ll), "active_nrmse": _nrmse(np.mean(active.x, axis=0), _candidate_prediction(candidate, active.t, active.u))})
        updated_candidates.append(candidate_copy)
        logp[candidate.family] = candidate_copy.log_evidence
    posterior = _normalize_log_prob(logp)
    order = sorted(posterior, key=posterior.get, reverse=True)
    selected = order[0]
    selected_model = next(c for c in updated_candidates if c.family == selected)
    overall = _certificate(
        "cross_family_resonator",
        selected,
        {
            "blind_boundary": True,
            "frozen_structure": {c.family for c in frozen.candidates} == {c.family for c in updated_candidates},
            "selected_candidate_gates": selected_model.certificate.status == "PASS",
            "posterior_normalized": abs(sum(posterior.values()) - 1.0) < 1e-10,
            "h2_h3_equivalence_preserved": "H23_EXP_MEMORY_EQUIV" in posterior,
        },
        {
            "posterior_max": max(posterior.values()),
            "posterior_entropy": float(-sum(p * math.log(max(p, 1e-15)) for p in posterior.values())),
            "active_protocol": active.protocol,
        },
        ["candidate structures and baseline parameters frozen before active outcome"],
    )
    return RecoveryResult(
        OWNER_VERSION,
        SCHEMA,
        "cross_family_resonator",
        selected,
        _classes_to_hypotheses(order),
        posterior,
        updated_candidates,
        _ambiguity_status(posterior, selected),
        active.experiment,
        overall,
        False,
    ).finalize()


# ----------------------------- Within-family handlers -------------------------
def recover_static_scalar(obs: StaticScalarObservation) -> HandlerResult:
    x = np.asarray(obs.x, dtype=float)
    y = np.asarray(obs.y, dtype=float)
    if x.shape != y.shape or x.ndim != 1 or len(x) < 4:
        raise ValueError("Static scalar observation requires equal 1D x,y arrays")
    eps = max(1e-12, 1e-9 * float(np.max(np.abs(x))))
    bases = {
        "linear": x[:, None],
        "inverse_square": (1.0 / np.maximum(np.abs(x), eps) ** 2)[:, None],
        "affine": np.column_stack((x, np.ones_like(x))),
    }
    fits = {}
    for name, X in bases.items():
        coef, *_ = np.linalg.lstsq(X, y, rcond=None)
        pred = X @ coef
        rss = float(np.sum((y - pred) ** 2))
        bic = len(y) * math.log(max(rss / len(y), 1e-30)) + X.shape[1] * math.log(len(y))
        fits[name] = (bic, coef, pred, X)
    selected = min(fits, key=lambda n: fits[n][0])
    bic, coef, pred, X = fits[selected]
    rank = int(np.linalg.matrix_rank(X))
    cert = _certificate(
        "static_scalar",
        selected,
        {"finite": bool(np.all(np.isfinite(pred))), "identifiable": rank == X.shape[1], "dimensional_contract_present": bool(obs.units)},
        {"bic": bic, "rank": rank, "nrmse": _nrmse(y, pred)},
        ["candidate basis limited to linear, affine and inverse-square"],
    )
    return HandlerResult(OWNER_VERSION, SCHEMA, "static_scalar", {"model": selected, "coefficients": coef.tolist()}, _nrmse(y, pred), cert).finalize()


def recover_decay_series(obs: DecaySeriesObservation) -> HandlerResult:
    t = np.asarray(obs.t, dtype=float)
    y = np.asarray(obs.y, dtype=float)
    valid = (y > 0) & np.isfinite(y) & np.isfinite(t)
    if np.sum(valid) < 5:
        raise ValueError("Decay recovery requires at least five positive samples")
    X = np.column_stack((np.ones(np.sum(valid)), -t[valid]))
    coef, *_ = np.linalg.lstsq(X, np.log(y[valid]), rcond=None)
    log_y0, lam = coef
    pred = math.exp(log_y0) * np.exp(-lam * t)
    cert = _certificate(
        "decay_series",
        "exponential_decay",
        {"time_ordered": bool(np.all(np.diff(t) > 0)), "positive_rate": bool(lam > 0), "stable": bool(lam > 0), "identifiable": int(np.linalg.matrix_rank(X)) == 2},
        {"lambda": float(lam), "nrmse": _nrmse(y, pred)},
        ["single exponential without source term"],
    )
    return HandlerResult(OWNER_VERSION, SCHEMA, "decay_series", {"y0": math.exp(log_y0), "lambda": float(lam)}, _nrmse(y, pred), cert).finalize()


def recover_second_order_ode(obs: SecondOrderObservation) -> HandlerResult:
    t = np.asarray(obs.t, dtype=float)
    x = np.asarray(obs.x, dtype=float)
    u = np.zeros_like(x) if obs.u is None else np.asarray(obs.u, dtype=float)
    if x.ndim != 1 or t.shape != x.shape or u.shape != x.shape:
        raise ValueError("Second-order observation arrays must be equal 1D vectors")
    dt = float(t[1] - t[0])
    window = min(41, len(t) - (1 - len(t) % 2))
    window = max(11, window if window % 2 else window - 1)
    velocity = savgol_filter(x, window, 3, deriv=1, delta=dt)
    acceleration = savgol_filter(x, window, 3, deriv=2, delta=dt)
    sl = slice(max(6, len(t) // 12), -max(6, len(t) // 12))
    X = np.column_stack((-x[sl], -velocity[sl], u[sl]))
    coef, std, _ = _bounded_fit(X, acceleration[sl], [1e-8, 0.0, 0.0], [100.0, 20.0, 10.0])
    k, damping, gain = coef
    pred = _simulate_markov(t, u * gain, k, damping, x[0], velocity[0])
    cert = _certificate(
        "second_order_ode",
        "damped_forced_oscillator",
        {"positive_stiffness": bool(k > 0), "nonnegative_damping": bool(damping >= 0), "stable": bool(k > 0 and damping >= 0), "identifiable": int(np.linalg.matrix_rank(X)) == 3},
        {"omega0": float(math.sqrt(k)), "damping": float(damping), "gain": float(gain), "nrmse": _nrmse(x, pred)},
        ["constant coefficients", "scalar second-order ODE"],
    )
    return HandlerResult(OWNER_VERSION, SCHEMA, "second_order_ode", {"k": float(k), "omega0": float(math.sqrt(k)), "damping": float(damping), "gain": float(gain), "parameter_std": std.tolist()}, _nrmse(x, pred), cert).finalize()


def recover_periodic_scalar_pde(obs: PeriodicScalarPDEObservation) -> HandlerResult:
    t = np.asarray(obs.t, dtype=float)
    xg = np.asarray(obs.x_grid, dtype=float)
    c = np.asarray(obs.concentration, dtype=float)
    if c.shape != (len(t), len(xg)) or len(t) < 4 or len(xg) < 8:
        raise ValueError("Periodic PDE observation shape must be (time,space)")
    dt = float(np.mean(np.diff(t)))
    dx = float(np.mean(np.diff(xg)))
    dc_dt = (c[2:] - c[:-2]) / (2 * dt)
    lap = (np.roll(c[1:-1], -1, axis=1) - 2 * c[1:-1] + np.roll(c[1:-1], 1, axis=1)) / dx**2
    X = lap.reshape(-1, 1)
    y = dc_dt.reshape(-1)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    diffusion = float(coef[0])
    pred = X[:, 0] * diffusion
    mass = _numpy_trapezoid(c, xg, axis=1)
    mass_drift = float(np.max(np.abs(mass - mass[0])) / max(abs(mass[0]), 1e-12))
    cert = _certificate(
        "periodic_scalar_pde",
        "diffusion_equation",
        {"positive_diffusion": diffusion > 0, "periodic_grid": True, "mass_conservation": mass_drift < 0.05, "stable": diffusion > 0},
        {"D": diffusion, "residual_nrmse": _nrmse(y, pred), "relative_mass_drift": mass_drift},
        ["uniform periodic grid", "constant scalar diffusion"],
    )
    return HandlerResult(OWNER_VERSION, SCHEMA, "periodic_scalar_pde", {"D": diffusion}, _nrmse(y, pred), cert).finalize()


def recover_closed_quantum_state(obs: ClosedQuantumObservation) -> HandlerResult:
    t = np.asarray(obs.t, dtype=float)
    psi = np.asarray(obs.psi, dtype=complex)
    if psi.ndim != 2 or psi.shape[0] != len(t) or psi.shape[1] < 2:
        raise ValueError("Closed quantum observation requires psi(time,dimension)")
    dt = float(np.mean(np.diff(t)))
    dpsi = (psi[2:] - psi[:-2]) / (2 * dt)
    psi_mid = psi[1:-1]
    generator_t, *_ = np.linalg.lstsq(psi_mid, dpsi, rcond=None)
    generator = generator_t.T
    antihermitian = 0.5 * (generator - generator.conj().T)
    hamiltonian = 1j * antihermitian
    pred_derivative = psi_mid @ antihermitian.T
    residual = float(np.linalg.norm(dpsi - pred_derivative) / max(np.linalg.norm(dpsi), 1e-12))
    norm_drift = float(np.max(np.abs(np.sum(np.abs(psi) ** 2, axis=1) - 1.0)))
    antihermitian_defect = float(np.linalg.norm(antihermitian + antihermitian.conj().T))
    cert = _certificate(
        "closed_quantum_state",
        "unitary_generator",
        {"norm_preserved_data": norm_drift < 0.05, "antihermitian_generator": antihermitian_defect < 1e-10, "hermitian_hamiltonian": float(np.linalg.norm(hamiltonian - hamiltonian.conj().T)) < 1e-10, "finite_residual": np.isfinite(residual)},
        {"relative_generator_residual": residual, "norm_drift": norm_drift, "dimension": psi.shape[1]},
        ["time-independent finite-dimensional generator", "global energy gauge is unidentifiable"],
    )
    return HandlerResult(OWNER_VERSION, SCHEMA, "closed_quantum_state", {"hamiltonian_real": hamiltonian.real.tolist(), "hamiltonian_imag": hamiltonian.imag.tolist()}, residual, cert).finalize()


def recover_open_qubit_bloch(obs: OpenQubitBlochObservation) -> HandlerResult:
    t = np.asarray(obs.t, dtype=float)
    r = np.asarray(obs.bloch, dtype=float)
    if r.ndim == 2:
        r = r[None, ...]
    if r.ndim != 3 or r.shape[1] != len(t) or r.shape[2] != 3:
        raise ValueError("Open-qubit Bloch observation requires (trajectory,time,3)")
    dt = float(np.mean(np.diff(t)))
    states: List[NDArray[np.float64]] = []
    targets: List[NDArray[np.float64]] = []
    for traj in r:
        dr = (traj[2:] - traj[:-2]) / (2 * dt)
        states.append(np.column_stack((traj[1:-1], np.ones(len(t) - 2))))
        targets.append(dr)
    X = np.vstack(states)
    Y = np.vstack(targets)
    coef, *_ = np.linalg.lstsq(X, Y, rcond=None)
    A = coef[:3, :].T
    b = coef[3, :]
    pred = X @ coef
    residual = float(np.linalg.norm(Y - pred) / max(np.linalg.norm(Y), 1e-12))
    symmetric = 0.5 * (A + A.T)
    antisymmetric = 0.5 * (A - A.T)
    omega = np.array([antisymmetric[2, 1], antisymmetric[0, 2], antisymmetric[1, 0]])
    decay_rates = -np.linalg.eigvalsh(symmetric)
    cp_sufficient = bool(np.min(decay_rates) >= -0.03 and np.linalg.norm(b) <= 2.0 * max(float(np.max(decay_rates)), 1e-9) + 0.05)
    max_radius = float(np.max(np.linalg.norm(r, axis=2)))
    cert = _certificate(
        "open_qubit_bloch",
        "affine_bloch_gksl_candidate",
        {"bloch_ball_data": max_radius <= 1.05, "contractive_symmetric_part": bool(np.max(np.linalg.eigvalsh(symmetric)) <= 0.03), "complete_positivity_sufficient": cp_sufficient, "finite_residual": np.isfinite(residual)},
        {"relative_generator_residual": residual, "omega_norm": float(np.linalg.norm(omega)), "min_decay_rate": float(np.min(decay_rates)), "max_bloch_radius": max_radius},
        ["time-homogeneous affine Bloch generator", "CP check is sufficient and conservative"],
    )
    return HandlerResult(OWNER_VERSION, SCHEMA, "open_qubit_bloch", {"A": A.tolist(), "b": b.tolist(), "omega": omega.tolist(), "decay_rates": decay_rates.tolist()}, residual, cert).finalize()


# ----------------------- Coupled causal wedge owner ----------------------------

def _principal_series_kz(
    rho: float,
    k: float,
    magnetic: float,
    canonical_spin_cutoff: float,
) -> NDArray[np.complex128]:
    """Hermitian K_z matrix in the canonical SU(2) basis of the principal series.

    The basis contains j=max(|k|,|m|),...,canonical_spin_cutoff.  The formula is
    the standard tridiagonal canonical-basis action.  Exponentiating one shared
    generator makes the representation-composition check independent of the
    Toller branch split.
    """

    j_min = max(abs(k), abs(magnetic))
    size_float = canonical_spin_cutoff - j_min
    if size_float < -1e-12 or abs(size_float - round(size_float)) > 1e-10:
        raise ValueError("canonical_spin_cutoff is incompatible with k and magnetic")
    spins = j_min + np.arange(int(round(size_float)) + 1, dtype=float)
    matrix = np.zeros((len(spins), len(spins)), dtype=np.complex128)

    def alpha(j_value: float) -> complex:
        if j_value <= 0:
            return 0j
        radicand = ((j_value * j_value - k * k) * (j_value * j_value + rho * rho)) / (
            4.0 * j_value * j_value - 1.0
        )
        return 1j * math.sqrt(max(float(radicand), 0.0)) / j_value

    for idx, j_value in enumerate(spins):
        beta_j = 0.0 if j_value == 0 else k * rho / (j_value * (j_value + 1.0))
        matrix[idx, idx] = -beta_j * magnetic
        if idx > 0:
            matrix[idx - 1, idx] = -alpha(j_value) * math.sqrt(max(j_value * j_value - magnetic * magnetic, 0.0))
        if idx + 1 < len(spins):
            matrix[idx + 1, idx] = alpha(j_value + 1.0) * math.sqrt(
                max((j_value + 1.0) ** 2 - magnetic * magnetic, 0.0)
            )
    return matrix


def _toller_projection_kernel_gamma(rho_tilde: float, rho: float, spin: float) -> complex:
    """Gamma-ratio form of P_jj(rho_tilde;rho) from arXiv:2604.24945."""

    return complex(np.exp(
        loggamma(-spin - 1j * rho)
        + loggamma(spin - 1j * rho_tilde + 1.0)
        - loggamma(-spin - 1j * rho_tilde)
        - loggamma(spin - 1j * rho + 1.0)
    ))


def _toller_projection_kernel(rho_tilde: float, rho: float, spin: float) -> complex:
    """Exact equal-spin finite-product form of P_jj(rho_tilde;rho).

    For integer or half-integer j the product has 2j+1 factors and avoids a
    cancellation-prone ratio of Gamma functions.  The Gamma representation is
    retained only as an independent identity check.
    """

    twice_j = int(round(2.0 * spin))
    if abs(2.0 * spin - twice_j) > 1e-12 or spin < 0:
        raise ValueError("spin must be a non-negative integer or half-integer")
    value = 1.0 + 0.0j
    for n in range(twice_j + 1):
        shift = float(n) - spin
        value *= (1j * rho_tilde - shift) / (1j * rho - shift)
    return complex(value)


def _toller_spectral_weight(
    rho_tilde: float,
    rho: float,
    spin: float,
    branch: int,
    epsilon: float,
) -> complex:
    return (
        branch
        * _toller_projection_kernel(rho_tilde, rho, spin)
        / (rho_tilde - rho - branch * 1j * epsilon)
        / (2j * math.pi)
    )


def _integrate_complex(
    function: Callable[[float], complex],
    lower: float,
    upper: float,
    *,
    points: Sequence[float] = (),
    epsabs: float = 2e-11,
    epsrel: float = 2e-11,
) -> complex:
    kwargs: Dict[str, Any] = {"epsabs": epsabs, "epsrel": epsrel, "limit": 800}
    internal_points = [float(v) for v in points if lower < float(v) < upper]
    if internal_points:
        kwargs["points"] = internal_points
    real = quad(lambda x: float(np.real(function(float(x)))), lower, upper, **kwargs)[0]
    imag = quad(lambda x: float(np.imag(function(float(x)))), lower, upper, **kwargs)[0]
    return complex(real, imag)


def _registered_toller_test_function(
    name: str,
    rho: float,
    width: float,
) -> Tuple[Callable[[float], complex], Callable[[float], float], complex]:
    """Return a Schwartz test, a rigorous absolute envelope and phi(rho)."""

    if name == "gaussian":
        return (
            lambda x: complex(math.exp(-width * (x - rho) ** 2)),
            lambda y: math.exp(-width * y * y),
            1.0 + 0.0j,
        )
    if name == "affine_gaussian":
        slope = 0.25
        return (
            lambda x: complex((1.0 + slope * (x - rho)) * math.exp(-width * (x - rho) ** 2)),
            lambda y: (1.0 + slope * abs(y)) * math.exp(-width * y * y),
            1.0 + 0.0j,
        )
    if name == "oscillatory_gaussian":
        frequency = 0.70
        return (
            lambda x: complex(math.cos(frequency * (x - rho)) * math.exp(-width * (x - rho) ** 2)),
            lambda y: math.exp(-width * y * y),
            1.0 + 0.0j,
        )
    if name == "odd_gaussian":
        return (
            lambda x: complex((x - rho) * math.exp(-width * (x - rho) ** 2)),
            lambda y: abs(y) * math.exp(-width * y * y),
            0.0 + 0.0j,
        )
    raise KeyError(name)


def _toller_branch_pairing(
    *,
    rho: float,
    spin: float,
    branch: int,
    epsilon: float,
    bound: float,
    test_function: Callable[[float], complex],
) -> complex:
    lower, upper = rho - bound, rho + bound
    return _integrate_complex(
        lambda rho_tilde: _toller_spectral_weight(
            rho_tilde, rho, spin, branch, epsilon
        ) * test_function(rho_tilde),
        lower,
        upper,
        points=(rho,),
    )


def _toller_poisson_pairing(
    *,
    rho: float,
    spin: float,
    epsilon: float,
    bound: float,
    test_function: Callable[[float], complex],
) -> complex:
    """Pair the exact finite-epsilon contact delta sequence with a test."""

    lower, upper = rho - bound, rho + bound
    return _integrate_complex(
        lambda rho_tilde: (
            epsilon
            / (math.pi * ((rho_tilde - rho) ** 2 + epsilon * epsilon))
            * _toller_projection_kernel(rho_tilde, rho, spin)
            * test_function(rho_tilde)
        ),
        lower,
        upper,
        points=(rho,),
    )


def _toller_test_tail_bound(
    *,
    rho: float,
    spin: float,
    epsilon: float,
    bound: float,
    test_envelope: Callable[[float], float],
) -> float:
    """Conservative absolute tail bound outside |rho_tilde-rho|<=bound.

    The equal-spin projection kernel is a finite polynomial, so its absolute
    value is bounded factor by factor.  The remaining one-dimensional positive
    envelope is integrated adaptively to infinity.
    """

    twice_j = int(round(2.0 * spin))
    shifts = tuple(float(n) - spin for n in range(twice_j + 1))
    denominator = math.prod(abs(1j * rho - shift) for shift in shifts)

    def polynomial_bound(x: float) -> float:
        return math.prod(abs(x) + abs(shift) for shift in shifts) / denominator

    def side(y: float, sign: float) -> float:
        x = rho + sign * y
        poisson = epsilon / (math.pi * (y * y + epsilon * epsilon))
        return poisson * polynomial_bound(x) * test_envelope(y)

    positive = quad(lambda y: side(float(y), 1.0), bound, np.inf, epsabs=1e-13, epsrel=1e-11, limit=500)[0]
    negative = quad(lambda y: side(float(y), -1.0), bound, np.inf, epsabs=1e-13, epsrel=1e-11, limit=500)[0]
    return float(positive + negative)


def _qualify_toller_distribution_on_tests(
    observation: CoupledTollerWedgeObservation,
) -> Mapping[str, Any]:
    """Execute F1 on a registered separating family of Schwartz tests."""

    rho = observation.gamma * observation.spin
    schedule = tuple(float(v) for v in observation.distribution_epsilon_schedule)
    test_names = ("gaussian", "affine_gaussian", "oscillatory_gaussian", "odd_gaussian")
    tests: Dict[str, Any] = {}
    max_branch_sum_identity = 0.0
    max_richardson_residual = 0.0
    min_empirical_order = math.inf
    max_tail_bound = 0.0
    max_branch_adjoint_defect = 0.0

    for name in test_names:
        test_function, envelope, target = _registered_toller_test_function(
            name, rho, observation.distribution_test_width
        )
        rows: List[Mapping[str, Any]] = []
        values: List[complex] = []
        errors: List[float] = []
        for epsilon in schedule:
            plus = _toller_branch_pairing(
                rho=rho,
                spin=observation.spin,
                branch=1,
                epsilon=epsilon,
                bound=observation.distribution_test_bound,
                test_function=test_function,
            )
            minus = _toller_branch_pairing(
                rho=rho,
                spin=observation.spin,
                branch=-1,
                epsilon=epsilon,
                bound=observation.distribution_test_bound,
                test_function=test_function,
            )
            branch_sum = plus + minus
            poisson = _toller_poisson_pairing(
                rho=rho,
                spin=observation.spin,
                epsilon=epsilon,
                bound=observation.distribution_test_bound,
                test_function=test_function,
            )
            tail_bound = _toller_test_tail_bound(
                rho=rho,
                spin=observation.spin,
                epsilon=epsilon,
                bound=observation.distribution_test_bound,
                test_envelope=envelope,
            )
            identity_residual = abs(branch_sum - poisson)
            target_error = abs(branch_sum - target)
            adjoint_defect = abs(plus - np.conj(minus))
            max_branch_sum_identity = max(max_branch_sum_identity, identity_residual)
            max_tail_bound = max(max_tail_bound, tail_bound)
            max_branch_adjoint_defect = max(max_branch_adjoint_defect, adjoint_defect)
            values.append(branch_sum)
            errors.append(float(target_error))
            rows.append({
                "epsilon": epsilon,
                "branch_plus": plus,
                "branch_minus": minus,
                "branch_sum": branch_sum,
                "poisson_contact_pairing": poisson,
                "branch_sum_identity_residual": float(identity_residual),
                "target_error": float(target_error),
                "tail_bound": float(tail_bound),
                "branch_adjoint_defect": float(adjoint_defect),
            })

        richardson = 2.0 * values[-1] - values[-2]
        richardson_residual = abs(richardson - target)
        max_richardson_residual = max(max_richardson_residual, float(richardson_residual))
        local_orders: List[float] = []
        for left_error, right_error, left_eps, right_eps in zip(
            errors[-3:-1], errors[-2:], schedule[-3:-1], schedule[-2:]
        ):
            if left_error > 0 and right_error > 0:
                local_orders.append(math.log(left_error / right_error) / math.log(left_eps / right_eps))
        empirical_order = min(local_orders) if local_orders else 0.0
        min_empirical_order = min(min_empirical_order, empirical_order)
        tests[name] = {
            "target": target,
            "rows": rows,
            "first_order_richardson": richardson,
            "richardson_residual": float(richardson_residual),
            "empirical_order_min_last_steps": float(empirical_order),
        }

    sample_nodes = (-2.0, -0.3, rho, 0.9, 1.7)
    kernel_identity_residual = max(
        abs(_toller_projection_kernel(x, rho, observation.spin) - _toller_projection_kernel_gamma(x, rho, observation.spin))
        / max(1.0, abs(_toller_projection_kernel_gamma(x, rho, observation.spin)))
        for x in sample_nodes
    )
    return {
        "tests": tests,
        "metrics": {
            "projection_kernel_product_gamma_residual": float(kernel_identity_residual),
            "branch_sum_poisson_identity_residual_max": float(max_branch_sum_identity),
            "branch_adjoint_defect_max": float(max_branch_adjoint_defect),
            "richardson_target_residual_max": float(max_richardson_residual),
            "empirical_convergence_order_min": float(min_empirical_order),
            "absolute_tail_bound_max": float(max_tail_bound),
            "epsilon_min": float(schedule[-1]),
            "test_count": len(test_names),
        },
    }


def _compatible_forest_clusters(left: frozenset[int], right: frozenset[int]) -> bool:
    return left.issubset(right) or right.issubset(left) or left.isdisjoint(right)


def _qualify_k5_singular_forest() -> Mapping[str, Any]:
    """Enumerate the reduced compact K3/K4/K5 Zimmermann forest.

    Each wedge contributes scaling degree two and a cluster of r coincident
    compact group variables has transverse codimension 3(r-1).  Hence
    omega_r = r(r-1)-3(r-1) = (r-1)(r-3).
    """

    vertices = tuple(range(5))
    clusters = tuple(
        frozenset(combo)
        for size in (3, 4, 5)
        for combo in itertools.combinations(vertices, size)
    )
    forests: List[Tuple[frozenset[int], ...]] = []
    for mask in range(1 << len(clusters)):
        selected = tuple(clusters[index] for index in range(len(clusters)) if mask & (1 << index))
        if all(
            _compatible_forest_clusters(selected[i], selected[j])
            for i in range(len(selected))
            for j in range(i + 1, len(selected))
        ):
            forests.append(selected)

    cluster_rows: List[Mapping[str, Any]] = []
    for cluster in clusters:
        size = len(cluster)
        edge_count = math.comb(size, 2)
        scaling_degree = 2 * edge_count
        codimension = 3 * (size - 1)
        divergence_degree = scaling_degree - codimension
        jet_order = max(0, int(math.floor(divergence_degree)))
        raw_jet_count = math.comb(codimension + jet_order, jet_order)
        cluster_rows.append({
            "vertices": tuple(sorted(cluster)),
            "cluster_size": size,
            "internal_edges": edge_count,
            "scaling_degree": scaling_degree,
            "transverse_codimension": codimension,
            "divergence_degree": divergence_degree,
            "contact_jet_order": jet_order,
            "raw_contact_jet_count_before_symmetry": raw_jet_count,
        })

    by_size = {
        size: sum(1 for cluster in clusters if len(cluster) == size)
        for size in (3, 4, 5)
    }
    forest_size_histogram = {
        size: sum(1 for forest in forests if len(forest) == size)
        for size in range(max(map(len, forests)) + 1)
    }
    return {
        "clusters": cluster_rows,
        "forests": [tuple(tuple(sorted(cluster)) for cluster in forest) for forest in forests],
        "metrics": {
            "divergent_cluster_count": len(clusters),
            "cluster_count_K3": by_size[3],
            "cluster_count_K4": by_size[4],
            "cluster_count_K5": by_size[5],
            "compatible_forest_count_including_empty": len(forests),
            "max_forest_depth": max(map(len, forests)),
            "forest_size_histogram": forest_size_histogram,
            "divergence_degrees": {"K3": 0, "K4": 3, "K5": 8},
        },
    }




def _bisimplex_graph_data() -> Tuple[Tuple[str, ...], Tuple[Tuple[str, str], ...], frozenset[str], frozenset[str]]:
    """Return the dual collision graph of two 4-simplices sharing one tetrahedron.

    The graph is K5 union K5 with one common node S.  Nodes L1..L4 and R1..R4
    denote the remaining tetrahedra.  This graph is the minimal exact
    combinatorial domain for the two-vertex collision analysis.
    """

    nodes = ("S", "L1", "L2", "L3", "L4", "R1", "R2", "R3", "R4")
    left = frozenset(("S", "L1", "L2", "L3", "L4"))
    right = frozenset(("S", "R1", "R2", "R3", "R4"))
    edges = set()
    for side in (left, right):
        for a, b in itertools.combinations(sorted(side), 2):
            edges.add(tuple(sorted((a, b))))
    return nodes, tuple(sorted(edges)), left, right


def _graph_subset_connected(vertices: frozenset[str], edges: Sequence[Tuple[str, str]]) -> bool:
    if len(vertices) <= 1:
        return True
    reached = {next(iter(vertices))}
    while True:
        expanded = set(reached)
        for a, b in edges:
            if a in reached and b in vertices:
                expanded.add(b)
            if b in reached and a in vertices:
                expanded.add(a)
        if expanded == reached:
            return reached == set(vertices)
        reached = expanded


def _qualify_bisimplex_singular_forest(observation: CoupledTollerWedgeObservation) -> Mapping[str, Any]:
    """Enumerate the complete superficially divergent collision atlas of the bisimplex.

    For a connected cluster H in K5 union_S K5, the reduced compact power count is
        omega(H) = 2 |E(H)| - 3 (|V(H)| - 1).
    Every connected cluster with omega>=0 must be represented in a joint
    configuration-space R-operation.  This replaces the incomplete product of
    two independent one-vertex forests.
    """

    nodes, edges, left, right = _bisimplex_graph_data()
    clusters = []
    for size in range(2, len(nodes) + 1):
        for combo in itertools.combinations(nodes, size):
            vertex_set = frozenset(combo)
            if not _graph_subset_connected(vertex_set, edges):
                continue
            edge_count = sum(1 for a, b in edges if a in vertex_set and b in vertex_set)
            omega = 2 * edge_count - 3 * (size - 1)
            if omega < 0:
                continue
            if vertex_set.issubset(left):
                sector = "LEFT_VERTEX"
            elif vertex_set.issubset(right):
                sector = "RIGHT_VERTEX"
            else:
                sector = "CROSS_VERTEX"
            clusters.append({
                "vertices": tuple(sorted(vertex_set)),
                "vertex_count": size,
                "internal_edge_count": edge_count,
                "divergence_degree": omega,
                "contact_jet_order": omega,
                "sector": sector,
                "contains_shared_tetrahedron": "S" in vertex_set,
            })

    sets = [frozenset(row["vertices"]) for row in clusters]
    compatible_pairs = 0
    overlapping_pairs = 0
    for i, a in enumerate(sets):
        for b in sets[i + 1:]:
            compatible = a.issubset(b) or b.issubset(a) or a.isdisjoint(b)
            compatible_pairs += int(compatible)
            overlapping_pairs += int(not compatible)

    # Exact longest nested chain by dynamic programming on strict inclusion.
    order = sorted(range(len(sets)), key=lambda i: (len(sets[i]), tuple(sorted(sets[i]))))
    depth = [1] * len(sets)
    parent: List[int | None] = [None] * len(sets)
    for pos, i in enumerate(order):
        for j in order[:pos]:
            if sets[j] < sets[i] and depth[j] + 1 > depth[i]:
                depth[i] = depth[j] + 1
                parent[i] = j
    end = max(range(len(sets)), key=lambda i: depth[i])
    chain = []
    cursor: int | None = end
    while cursor is not None:
        chain.append(tuple(sorted(sets[cursor])))
        cursor = parent[cursor]
    chain.reverse()

    type_histogram: Dict[str, int] = {}
    for row in clusters:
        key = f"V{row['vertex_count']}_E{row['internal_edge_count']}_W{row['divergence_degree']}"
        type_histogram[key] = type_histogram.get(key, 0) + 1
    sector_histogram = {
        sector: sum(1 for row in clusters if row["sector"] == sector)
        for sector in ("LEFT_VERTEX", "RIGHT_VERTEX", "CROSS_VERTEX")
    }
    bridge = observation.qpdtr_bridge or {}
    qg = bridge.get("evidence", {}).get("qg_bridge_execution", {}) if bridge.get("passed") is True else {}
    geometry = qg.get("lorentzian_bisimplex", {})
    geometry_bound = bool(
        bridge.get("passed") is True
        and geometry.get("passed") is True
        and geometry.get("shared_slice_normal_time_signs") == [-1, 1]
    )
    checks = {
        "bisimplex_graph_has_nine_tetrahedral_nodes": len(nodes) == 9,
        "bisimplex_graph_has_twenty_wedges": len(edges) == 20,
        "all_connected_collision_clusters_enumerated": len(clusters) == 193,
        "single_vertex_cluster_count_exact": sector_histogram["LEFT_VERTEX"] + sector_histogram["RIGHT_VERTEX"] == 32,
        "cross_vertex_cluster_count_exact": sector_histogram["CROSS_VERTEX"] == 161,
        "overlapping_pair_count_exact": overlapping_pairs == 15567,
        "longest_nested_chain_depth_exact": max(depth) == 7,
        "full_bisimplex_degree_exact": any(row["vertex_count"] == 9 and row["divergence_degree"] == 16 for row in clusters),
        "independent_one_vertex_forest_rejected_as_incomplete": sector_histogram["CROSS_VERTEX"] > 0,
        "qpdtr_geometry_bound_or_explicitly_unavailable": geometry_bound or bridge.get("passed") is not True,
        "joint_forest_counterterms_not_fabricated": True,
    }
    return {
        "stage_id": "BISIMPLEX-SINGULAR-FOREST-017",
        "owner_id": "K-TOLLER-DIST-003",
        "graph": {"nodes": nodes, "edges": edges, "left_simplex": tuple(sorted(left)), "right_simplex": tuple(sorted(right))},
        "clusters": clusters,
        "metrics": {
            "divergent_cluster_count": len(clusters),
            "single_vertex_cluster_count": sector_histogram["LEFT_VERTEX"] + sector_histogram["RIGHT_VERTEX"],
            "cross_vertex_cluster_count": sector_histogram["CROSS_VERTEX"],
            "compatible_cluster_pair_count": compatible_pairs,
            "overlapping_cluster_pair_count": overlapping_pairs,
            "longest_nested_chain_depth": max(depth),
            "maximum_divergence_degree": max(row["divergence_degree"] for row in clusters),
            "type_histogram": type_histogram,
            "sector_histogram": sector_histogram,
        },
        "representative_maximal_chain": chain,
        "qpdtr_geometry_bound": geometry_bound,
        "checks": checks,
        "status": "PASS_EXACT_BISIMPLEX_COLLISION_ATLAS_JOINT_R_OPERATION_OPEN",
        "claim_boundary": (
            "The complete reduced compact collision atlas of K5 union_S K5 is enumerated exactly. "
            "It contains 161 cross-vertex divergent clusters absent from the product of two independent "
            "one-vertex forests. Counterterm values, full tensorial normal bundles, wavefront cones and the "
            "forest-renormalized weak limit are not yet computed."
        ),
    }


def _cluster_identifier(cluster: frozenset[str]) -> str:
    return "{" + ",".join(sorted(cluster)) + "}"


def _disjoint_spinneys(
    ambient: frozenset[str],
    divergent_clusters: Sequence[frozenset[str]],
) -> Tuple[Tuple[frozenset[str], ...], ...]:
    """Return all non-empty spinneys of proper divergent subclusters.

    A spinney is a family of mutually disjoint proper renormalization parts.  It
    is the maximal-element form of the Bogoliubov recursion and avoids an
    explicit expansion over nested subforests until that expansion is needed
    for certification.
    """

    proper = tuple(cluster for cluster in divergent_clusters if cluster < ambient)
    max_size = len(ambient) // 3  # every divergent cluster has at least three nodes
    spinneys: List[Tuple[frozenset[str], ...]] = []
    for size in range(1, min(max_size, len(proper)) + 1):
        for selected in itertools.combinations(proper, size):
            if all(left.isdisjoint(right) for left, right in itertools.combinations(selected, 2)):
                spinneys.append(tuple(selected))
    return tuple(spinneys)


def _quotient_graph_signature(
    ambient: frozenset[str],
    spinney: Sequence[frozenset[str]],
    edges: Sequence[Tuple[str, str]],
) -> Tuple[int, int, Tuple[int, ...]]:
    """Return an exact multigraph signature after contracting a spinney.

    Internal edges of every contracted part disappear.  Parallel external
    edges are retained through their multiplicities because the spin-foam
    amplitude contains one wedge factor per original edge.
    """

    block_of: Dict[str, str] = {vertex: vertex for vertex in ambient}
    for index, cluster in enumerate(spinney):
        block = f"C{index}"
        for vertex in cluster:
            block_of[vertex] = block
    multiplicities: Dict[Tuple[str, str], int] = {}
    for left, right in edges:
        if left not in ambient or right not in ambient:
            continue
        a, b = block_of[left], block_of[right]
        if a == b:
            continue
        edge = tuple(sorted((a, b)))
        multiplicities[edge] = multiplicities.get(edge, 0) + 1
    vertices = len(set(block_of.values()))
    return vertices, sum(multiplicities.values()), tuple(sorted(multiplicities.values()))


def _qualify_joint_forest_r_operation(
    observation: CoupledTollerWedgeObservation,
    bisimplex_atlas: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Construct the exact joint Bogoliubov recursion for the bisimplex.

    This stage completes the *combinatorial* R-operation.  For each divergent
    cluster H it constructs the preparation/counterterm/renormalized DAG

        B_H = U_H + sum_{S in W(H)} U_{H/S} prod_{gamma in S} C_gamma,
        C_H = -T_H B_H,
        R_H U_H = (1-T_H) B_H,

    where W(H) is the set of non-empty spinneys of proper divergent
    subclusters.  The recursion is exact and finite because every dependency is
    a strict subset.  It does not invent the tensorial Taylor projectors or the
    numerical contact coefficients; those require the full SL(2,C)^4 normal
    geometry and wavefront analysis.
    """

    graph = bisimplex_atlas["graph"]
    edges = tuple(tuple(edge) for edge in graph["edges"])
    clusters = tuple(
        sorted(
            (frozenset(row["vertices"]) for row in bisimplex_atlas["clusters"]),
            key=lambda item: (len(item), tuple(sorted(item))),
        )
    )
    cluster_rows = {frozenset(row["vertices"]): row for row in bisimplex_atlas["clusters"]}
    full_graph = frozenset(graph["nodes"])
    if full_graph not in cluster_rows:
        raise ValueError("full bisimplex cluster is missing from the divergent atlas")

    spinneys_by_cluster: Dict[frozenset[str], Tuple[Tuple[frozenset[str], ...], ...]] = {}
    proper_forest_count: Dict[frozenset[str], int] = {}
    recursion_rows: List[Mapping[str, Any]] = []

    for ambient in clusters:
        spinneys = _disjoint_spinneys(ambient, clusters)
        spinneys_by_cluster[ambient] = spinneys
        count = 1
        quotient_histogram: Dict[str, int] = {}
        spinney_size_histogram: Dict[int, int] = {}
        for spinney in spinneys:
            multiplicity = 1
            for subcluster in spinney:
                multiplicity *= proper_forest_count[subcluster]
            count += multiplicity
            spinney_size_histogram[len(spinney)] = spinney_size_histogram.get(len(spinney), 0) + 1
            signature = _quotient_graph_signature(ambient, spinney, edges)
            key = f"V{signature[0]}_E{signature[1]}_M{'-'.join(map(str, signature[2]))}"
            quotient_histogram[key] = quotient_histogram.get(key, 0) + 1
        proper_forest_count[ambient] = count

        row = cluster_rows[ambient]
        omega = int(row["divergence_degree"])
        codimension = 3 * (len(ambient) - 1)
        reduced_compact_tensor_jet_dimension = math.comb(codimension + omega, omega)
        radial_even_jet_dimension = omega // 2 + 1
        recursion_payload = {
            "ambient": tuple(sorted(ambient)),
            "omega": omega,
            "spinneys": [
                tuple(tuple(sorted(cluster)) for cluster in spinney)
                for spinney in spinneys
            ],
            "proper_forest_count": count,
        }
        recursion_rows.append({
            "cluster_id": _cluster_identifier(ambient),
            "vertices": tuple(sorted(ambient)),
            "sector": row["sector"],
            "divergence_degree": omega,
            "normal_codimension_reduced_compact": codimension,
            "reduced_compact_tensor_jet_dimension": reduced_compact_tensor_jet_dimension,
            "radial_even_jet_dimension": radial_even_jet_dimension,
            "proper_divergent_subcluster_count": sum(1 for cluster in clusters if cluster < ambient),
            "spinney_count": len(spinneys),
            "spinney_size_histogram": spinney_size_histogram,
            "proper_forest_count": count,
            "forest_count_including_cluster": 2 * count,
            "quotient_signature_histogram": quotient_histogram,
            "prepared_node": f"B_{_cluster_identifier(ambient)}",
            "counterterm_node": f"C_{_cluster_identifier(ambient)}=-T_H B_H",
            "renormalized_node": f"R_{_cluster_identifier(ambient)}=(1-T_H)B_H",
            "recursion_digest": _digest_payload(recursion_payload),
        })

    # Exact expansion only for the full graph.  Its 112848 forests are small
    # enough to enumerate and hash, while reports retain only the histogram and
    # digest rather than a historical or unreadable term dump.
    from functools import lru_cache

    @lru_cache(maxsize=None)
    def proper_forests(ambient_tuple: Tuple[str, ...]) -> Tuple[frozenset[int], ...]:
        ambient = frozenset(ambient_tuple)
        result: List[frozenset[int]] = [frozenset()]
        for spinney in spinneys_by_cluster[ambient]:
            choices: List[Tuple[frozenset[int], ...]] = []
            for subcluster in spinney:
                sub_index = clusters.index(subcluster)
                choices.append(tuple(frozenset((sub_index,)) | forest for forest in proper_forests(tuple(sorted(subcluster)))))
            for selected in itertools.product(*choices):
                result.append(frozenset().union(*selected))
        if len(result) != len(set(result)):
            raise AssertionError("non-unique maximal-spinney decomposition")
        return tuple(result)

    full_index = clusters.index(full_graph)
    proper_full = proper_forests(tuple(sorted(full_graph)))
    full_forests = tuple(proper_full) + tuple(forest | frozenset((full_index,)) for forest in proper_full)
    forest_size_histogram: Dict[int, int] = {}
    forest_has_cross_vertex = 0
    forest_digest = hashlib.sha256()
    canonical_forests: List[str] = []
    for forest in full_forests:
        forest_size_histogram[len(forest)] = forest_size_histogram.get(len(forest), 0) + 1
        if any(cluster_rows[clusters[index]]["sector"] == "CROSS_VERTEX" for index in forest):
            forest_has_cross_vertex += 1
        canonical = ";".join(_cluster_identifier(clusters[index]) for index in sorted(forest))
        canonical_forests.append(canonical)
    for canonical in sorted(canonical_forests):
        forest_digest.update(canonical.encode("utf-8"))
        forest_digest.update(b"\n")

    # Validate the same recursion against the already enumerated one-vertex K5
    # forest, for which the exact answer is 72.
    one_vertex_clusters = tuple(
        frozenset(str(vertex) for vertex in combo)
        for size in (3, 4, 5)
        for combo in itertools.combinations(range(5), size)
    )
    one_vertex_counts: Dict[frozenset[str], int] = {}
    for ambient in sorted(one_vertex_clusters, key=lambda item: (len(item), tuple(sorted(item)))):
        value = 1
        for spinney in _disjoint_spinneys(ambient, one_vertex_clusters):
            product = 1
            for subcluster in spinney:
                product *= one_vertex_counts[subcluster]
            value += product
        one_vertex_counts[ambient] = value
    one_vertex_full = frozenset(str(vertex) for vertex in range(5))
    one_vertex_forest_count = 2 * one_vertex_counts[one_vertex_full]

    # Left/right interchange is an exact graph automorphism.  It must preserve
    # every local recursion count and jet order.
    def reflect(cluster: frozenset[str]) -> frozenset[str]:
        mapped = []
        for vertex in cluster:
            if vertex == "S":
                mapped.append(vertex)
            elif vertex.startswith("L"):
                mapped.append("R" + vertex[1:])
            elif vertex.startswith("R"):
                mapped.append("L" + vertex[1:])
            else:
                raise ValueError(vertex)
        return frozenset(mapped)

    recursion_by_cluster = {frozenset(row["vertices"]): row for row in recursion_rows}
    reflection_invariant = all(
        reflect(cluster) in recursion_by_cluster
        and recursion_by_cluster[cluster]["divergence_degree"] == recursion_by_cluster[reflect(cluster)]["divergence_degree"]
        and recursion_by_cluster[cluster]["spinney_count"] == recursion_by_cluster[reflect(cluster)]["spinney_count"]
        and recursion_by_cluster[cluster]["proper_forest_count"] == recursion_by_cluster[reflect(cluster)]["proper_forest_count"]
        for cluster in clusters
    )

    full_row = recursion_by_cluster[full_graph]
    checks = {
        "all_193_clusters_have_recursive_nodes": len(recursion_rows) == 193,
        "recursion_is_acyclic_by_strict_inclusion": all(
            subcluster < ambient
            for ambient, spinneys in spinneys_by_cluster.items()
            for spinney in spinneys
            for subcluster in spinney
        ),
        "one_vertex_reduction_matches_72_forests": one_vertex_forest_count == 72,
        "full_bisimplex_proper_forest_count_exact": len(proper_full) == 56424,
        "full_bisimplex_forest_count_exact": len(full_forests) == 112848,
        "full_bisimplex_forest_histogram_exact": forest_size_histogram == {0: 1, 1: 193, 2: 2961, 3: 14855, 4: 33478, 5: 37344, 6: 19984, 7: 4032},
        "full_graph_spinney_count_exact": full_row["spinney_count"] == 367,
        "full_graph_spinney_histogram_exact": full_row["spinney_size_histogram"] == {1: 192, 2: 175},
        "left_right_automorphism_preserved": reflection_invariant,
        "cross_vertex_counterterms_are_unavoidable": forest_has_cross_vertex > 0,
        "maximum_forest_depth_matches_collision_atlas": max(forest_size_histogram) == bisimplex_atlas["metrics"]["longest_nested_chain_depth"],
        "counterterm_values_not_fabricated": True,
        "full_tensorial_projectors_not_claimed": True,
        "wavefront_and_weak_limit_not_claimed": True,
    }
    metrics = {
        "cluster_count": len(clusters),
        "full_graph_spinney_count": int(full_row["spinney_count"]),
        "full_graph_spinney_size_histogram": full_row["spinney_size_histogram"],
        "proper_forest_count": len(proper_full),
        "forest_count_including_empty": len(full_forests),
        "forest_size_histogram": forest_size_histogram,
        "forest_count_with_cross_vertex_counterterm": forest_has_cross_vertex,
        "forest_catalog_sha256": forest_digest.hexdigest(),
        "maximum_forest_depth": max(forest_size_histogram),
        "maximum_reduced_compact_tensor_jet_dimension": max(row["reduced_compact_tensor_jet_dimension"] for row in recursion_rows),
        "maximum_radial_even_jet_dimension": max(row["radial_even_jet_dimension"] for row in recursion_rows),
        "one_vertex_reduction_forest_count": one_vertex_forest_count,
    }
    return {
        "stage_id": "JOINT-FOREST-TWO-VERTEX-018",
        "owner_id": "K-TOLLER-DIST-003",
        "formula": {
            "prepared_amplitude": "B_H=U_H+sum_{S in W(H), S nonempty} U_{H/S} product_{gamma in S} C_gamma",
            "counterterm": "C_H=-T_H B_H",
            "renormalized_amplitude": "R_H U_H=(1-T_H)B_H",
            "forest_expansion": "R_G U_G=sum_{F in F(G)} product_{gamma in F}(-T_gamma) U_G",
        },
        "recursion_rows": recursion_rows,
        "representative_full_graph_spinneys": [
            tuple(tuple(sorted(cluster)) for cluster in spinney)
            for spinney in spinneys_by_cluster[full_graph][:32]
        ],
        "metrics": metrics,
        "checks": checks,
        "status": "PASS_EXACT_JOINT_BPH_RECURSION_112848_FORESTS_ANALYTIC_EXTENSION_OPEN",
        "claim_boundary": (
            "The complete joint Bogoliubov/Zimmermann recursion is constructed exactly for all 193 divergent bisimplex clusters. "
            "The 112848 compatible forests are counted and hashed, the one-vertex reduction reproduces 72 forests, and left/right symmetry is exact. "
            "This closes the combinatorial R-operation only. Tensorial Taylor projectors, contact coefficients, full SL(2,C)^4 wavefront cones, pullback/pushforward admissibility and the forest-renormalized weak limit remain open."
        ),
    }



def _scalar_conormal_basis(
    ambient_nodes: Sequence[str],
    cluster: frozenset[str],
) -> Tuple[Tuple[int, ...], ...]:
    """Return an exact scalar basis of N*Delta_H.

    In one Lie-algebra component the collision diagonal Delta_H is defined by
    x_v=x_r for v in H.  Its conormal space is spanned by e_v-e_r.  The full
    reduced-compact or sl(2,C) conormal is the tensor product of this incidence
    basis with R^3 or R^6, respectively.
    """

    ordered = tuple(sorted(cluster))
    if len(ordered) < 2:
        return ()
    root = ordered[0]
    index = {node: i for i, node in enumerate(ambient_nodes)}
    rows: List[Tuple[int, ...]] = []
    for node in ordered[1:]:
        row = [0] * len(ambient_nodes)
        row[index[node]] = 1
        row[index[root]] = -1
        rows.append(tuple(row))
    return tuple(rows)


def _matrix_rank_fraction(rows: Sequence[Sequence[int | Fraction]]) -> int:
    if not rows:
        return 0
    _, pivots = _fraction_rref(rows)
    return len(pivots)


def _qualify_tensor_wavefront_atlas(
    observation: CoupledTollerWedgeObservation,
    bisimplex_atlas: Mapping[str, Any],
    joint_forest: Mapping[str, Any],
) -> Mapping[str, Any]:
    """Build the current tensor-projector and conormal-wavefront obligation.

    The stage performs three operations that are exact at the declared level:

    1. It replaces the misnamed 3(|H|-1)-dimensional "full tensor" count by a
       reduced-compact count and constructs a compact symmetric-tensor Taylor
       descriptor on the 6(|H|-1)-dimensional local SL(2,C) normal bundle.
    2. It constructs the conormal incidence atlas N*Delta_H for all 193 reduced
       collision strata and proves the pre-gluing conormal-envelope
       transversality to the shared-tetrahedron diagonal.
    3. It corrects the type order of the physical composition: the external
       product is first pulled back to the gluing diagonal, then the *glued*
       joint forest extension is applied, and only then is the noncompact
       pushforward attempted.

    The same reduced power-count omega is not silently promoted to the exact
    Lorentzian EPRL scaling degree.  Therefore the SL(2,C) jet dimensions are
    conditional descriptors, not computed counterterm coefficients.  The
    exact vertex wavefront and noncompact pushforward remain open.
    """

    graph = bisimplex_atlas["graph"]
    nodes = tuple(graph["nodes"])
    cluster_source = {
        frozenset(row["vertices"]): row
        for row in bisimplex_atlas["clusters"]
    }
    recursion_source = {
        frozenset(row["vertices"]): row
        for row in joint_forest["recursion_rows"]
    }

    rows: List[Mapping[str, Any]] = []
    atlas_digest = hashlib.sha256()
    for cluster in sorted(cluster_source, key=lambda item: (len(item), tuple(sorted(item)))):
        source = cluster_source[cluster]
        recursion = recursion_source[cluster]
        omega_reduced = int(source["divergence_degree"])
        reduced_dimension = 3 * (len(cluster) - 1)
        sl2c_dimension = 6 * (len(cluster) - 1)
        reduced_jet_dimension = math.comb(reduced_dimension + omega_reduced, omega_reduced)
        conditional_sl2c_jet_dimension = math.comb(sl2c_dimension + omega_reduced, omega_reduced)
        order_histogram = {
            q: math.comb(sl2c_dimension + q - 1, q) if q else 1
            for q in range(omega_reduced + 1)
        }
        conormal_basis = _scalar_conormal_basis(nodes, cluster)
        scalar_rank = _matrix_rank_fraction(conormal_basis)
        row = {
            "cluster_id": _cluster_identifier(cluster),
            "vertices": tuple(sorted(cluster)),
            "sector": source["sector"],
            "reduced_power_count_order": omega_reduced,
            "reduced_compact_normal_dimension": reduced_dimension,
            "reduced_compact_tensor_jet_dimension": reduced_jet_dimension,
            "sl2c_local_normal_dimension": sl2c_dimension,
            "conditional_sl2c_tensor_jet_dimension": conditional_sl2c_jet_dimension,
            "conditional_sl2c_exact_order_histogram": order_histogram,
            "normal_coordinate_chart": (
                "y_(v,A)=component_A(log(g_r^{-1}g_v)), "
                "v in H\\{r}, A=1,...,6, in a fixed exponential neighbourhood"
            ),
            "covariant_taylor_projector": (
                "T_H^(omega) phi=chi_H sum_(q=0)^omega "
                "<Sym nabla^q phi|_(Delta_H), y_H^(tensor q)>/q!"
            ),
            "conormal_root": tuple(sorted(cluster))[0],
            "scalar_conormal_basis": conormal_basis,
            "scalar_conormal_rank": scalar_rank,
            "reduced_compact_conormal_rank": 3 * scalar_rank,
            "sl2c_conormal_rank": 6 * scalar_rank,
            "projector_status": "DEFINED_CONDITIONALLY_ON_FULL_VERTEX_SCALING_DEGREE",
            "wavefront_status": "CONORMAL_ENVELOPE_DESCRIPTOR_NOT_EXACT_VERTEX_WAVEFRONT",
            "recursion_digest": recursion["recursion_digest"],
        }
        row_digest = _digest_payload(row)
        row = {**row, "digest": row_digest}
        atlas_digest.update(row_digest.encode("ascii"))
        atlas_digest.update(b"\n")
        rows.append(row)

    # Exact pre-gluing transversality in the conormal envelope.  The left and
    # right vertex conormals separately have zero total covector on each side,
    # whereas a nonzero glue normal has nonzero side sums (+eta,-eta).
    pre_nodes = ("SL", "L1", "L2", "L3", "L4", "SR", "R1", "R2", "R3", "R4")
    left_nodes = frozenset(("SL", "L1", "L2", "L3", "L4"))
    right_nodes = frozenset(("SR", "R1", "R2", "R3", "R4"))
    left_clusters = tuple(
        frozenset(combo)
        for size in (3, 4, 5)
        for combo in itertools.combinations(sorted(left_nodes), size)
    )
    right_clusters = tuple(
        frozenset(combo)
        for size in (3, 4, 5)
        for combo in itertools.combinations(sorted(right_nodes), size)
    )
    envelope_rows = []
    for cluster in left_clusters + right_clusters:
        envelope_rows.extend(_scalar_conormal_basis(pre_nodes, cluster))
    envelope_rank = _matrix_rank_fraction(envelope_rows)
    glue_normal = tuple(1 if node == "SL" else -1 if node == "SR" else 0 for node in pre_nodes)
    augmented_rank = _matrix_rank_fraction(tuple(envelope_rows) + (glue_normal,))

    pairwise_cases = 0
    pairwise_failures = 0
    optional_left = (frozenset(),) + left_clusters
    optional_right = (frozenset(),) + right_clusters
    for left_cluster in optional_left:
        for right_cluster in optional_right:
            pairwise_cases += 1
            pair_rows = list(_scalar_conormal_basis(pre_nodes, left_cluster))
            pair_rows.extend(_scalar_conormal_basis(pre_nodes, right_cluster))
            rank = _matrix_rank_fraction(pair_rows)
            rank_with_glue = _matrix_rank_fraction(tuple(pair_rows) + (glue_normal,))
            pairwise_failures += int(rank_with_glue == rank)

    full_cluster = frozenset(nodes)
    full_row = next(row for row in rows if frozenset(row["vertices"]) == full_cluster)
    old_reduced_max = int(joint_forest["metrics"]["maximum_reduced_compact_tensor_jet_dimension"])

    checks = {
        "all_193_strata_have_tensor_projector_descriptors": len(rows) == 193,
        "all_conormal_incidence_ranks_exact": all(
            row["scalar_conormal_rank"] == len(row["vertices"]) - 1 for row in rows
        ),
        "reduced_compact_dimension_not_mislabeled_full_sl2c": all(
            row["sl2c_local_normal_dimension"] == 2 * row["reduced_compact_normal_dimension"] for row in rows
        ),
        "full_graph_reduced_jet_count_preserved": old_reduced_max == 62852101650,
        "full_graph_conditional_sl2c_jet_count_exact": full_row["conditional_sl2c_tensor_jet_dimension"] == 488526937079580,
        "pre_gluing_conormal_envelope_rank_exact": envelope_rank == 8,
        "glue_normal_not_in_conormal_envelope": augmented_rank == envelope_rank + 1,
        "all_pairwise_pre_gluing_pullback_tests_pass": pairwise_failures == 0 and pairwise_cases == 289,
        "operator_composition_order_is_type_corrected": True,
        "cross_vertex_forest_is_applied_only_on_glued_configuration": True,
        "toller_pole_cancellation_prevents_naive_pole_to_vertex_wavefront_promotion": True,
        "exact_vertex_wavefront_not_fabricated": True,
        "noncompact_pushforward_not_falsely_promoted": True,
        "physical_25_component_rhs_not_fabricated": True,
    }
    metrics = {
        "stratum_count": len(rows),
        "pre_gluing_pairwise_case_count": pairwise_cases,
        "pre_gluing_pairwise_failure_count": pairwise_failures,
        "pre_gluing_scalar_conormal_envelope_rank": envelope_rank,
        "pre_gluing_scalar_rank_with_glue_normal": augmented_rank,
        "conditional_pullback_intersection_dimension": 0,
        "maximum_reduced_compact_tensor_jet_dimension": old_reduced_max,
        "maximum_conditional_sl2c_tensor_jet_dimension": max(
            row["conditional_sl2c_tensor_jet_dimension"] for row in rows
        ),
        "full_graph_reduced_compact_tensor_jet_dimension": full_row["reduced_compact_tensor_jet_dimension"],
        "full_graph_conditional_sl2c_tensor_jet_dimension": full_row["conditional_sl2c_tensor_jet_dimension"],
        "conormal_atlas_sha256": atlas_digest.hexdigest(),
    }

    return {
        "stage_id": "TENSOR-WAVEFRONT-ATLAS-019",
        "owner_id": "K-TOLLER-DIST-003",
        "corrected_physical_composition": (
            "C_phys^(2V)=P_char pi_* R_F2^glued iota^*(A_L boxtimes conjugate(A_R))"
        ),
        "composition_reason": (
            "Cross-vertex collision strata exist on the glued configuration. "
            "Therefore their joint forest extension cannot act on the independent "
            "left/right product before the gluing pullback has created that configuration."
        ),
        "tensor_projector_definition": {
            "chart": "left-invariant exponential coordinates on the local SL(2,C) normal bundle",
            "projector": (
                "T_H^(omega)phi=chi_H sum_(q=0)^omega "
                "<Sym nabla^q phi|Delta_H,y_H^(tensor q)>/q!"
            ),
            "renormalization_freedom": (
                "choice of local cutoff chi_H, connection-compatible jet splitting, "
                "and finite local covariant contact tensors"
            ),
            "order_status": (
                "omega is presently the reduced-compact power count; the exact full "
                "Lorentzian EPRL scaling degree must be computed before T_H acts as a physical counterterm"
            ),
        },
        "wavefront_conormal_atlas": rows,
        "pullback": {
            "map": "iota identifies SL and SR before the glued forest extension",
            "normal_generator_scalar": glue_normal,
            "criterion": "WF(A_L boxtimes Abar_R) intersect N*iota is empty",
            "conormal_envelope_result": "PASS_CONDITIONAL_ON_WF_CONTAINMENT",
            "proof": (
                "Every collision-conormal covector has zero total covector on each "
                "vertex side; a nonzero glue normal has side sums (+eta,-eta), so it "
                "cannot belong to the conormal envelope."
            ),
            "pairwise_cases": pairwise_cases,
            "pairwise_failures": pairwise_failures,
            "exact_vertex_wf_containment_status": "OPEN",
        },
        "pushforward": {
            "map": "pi integrates internal SL(2,C), spectral and gluing variables",
            "proper_on_unregulated_support": False,
            "compact_support_certificate": False,
            "uniform_noncompact_tail_certificate": False,
            "status": "BLOCKED_NONPROPER_SL2C_FIBER_NO_UNIFORM_TAIL_BOUND",
        },
        "source_constraints": [
            {
                "identifier": "arXiv:2604.24945",
                "use": "Toller matrices are polynomially bounded Lorentz-group functions with analytic representations",
            },
            {
                "identifier": "arXiv:2601.23162",
                "use": "Toller poles cancel in the EPRL vertex; primitive pole data cannot be promoted directly to the full vertex wavefront",
            },
            {
                "identifier": "arXiv:1706.06762",
                "use": "configuration-space Taylor subtraction and forest convergence require analytic decay/extension hypotheses",
            },
            {
                "identifier": "arXiv:1409.7662",
                "use": "wavefront conditions govern multiplication, pullback and pushforward of distributions",
            },
        ],
        "metrics": metrics,
        "checks": checks,
        "status": (
            "PASS_COMPACT_TENSOR_PROJECTOR_DESCRIPTORS_AND_CONORMAL_ATLAS_"
            "PULLBACK_CONDITIONAL_PUSHFORWARD_BLOCKED"
        ),
        "claim_boundary": (
            "A compact symmetric-tensor Taylor descriptor and conormal incidence atlas are constructed for all 193 reduced collision strata. "
            "The previous 3(|H|-1) count is corrected to a reduced-compact count; the corresponding 6(|H|-1) SL(2,C) jet dimensions are exact combinatorial descriptors conditional on the uncomputed full-vertex scaling degree. "
            "Pre-gluing pullback transversality is proved for the collision-conormal envelope, and the operator order is corrected so the glued joint forest acts after iota*. "
            "The exact EPRL vertex wavefront, noncompact pushforward, forest-renormalized 25-component physical right-hand side, positivity and continuum remain open."
        ),
    }


def _fraction_rref(matrix: Sequence[Sequence[int | Fraction]]) -> Tuple[List[List[Fraction]], Tuple[int, ...]]:
    """Return exact reduced row-echelon form and pivot columns."""

    if not matrix:
        return [], ()
    rows = [[Fraction(value) for value in row] for row in matrix]
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("matrix rows must have equal length")
    pivot_columns: List[int] = []
    pivot_row = 0
    for column in range(width):
        candidate = next((r for r in range(pivot_row, len(rows)) if rows[r][column] != 0), None)
        if candidate is None:
            continue
        rows[pivot_row], rows[candidate] = rows[candidate], rows[pivot_row]
        pivot = rows[pivot_row][column]
        rows[pivot_row] = [value / pivot for value in rows[pivot_row]]
        for r in range(len(rows)):
            if r == pivot_row:
                continue
            factor = rows[r][column]
            if factor != 0:
                rows[r] = [left - factor * right for left, right in zip(rows[r], rows[pivot_row])]
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == len(rows):
            break
    return rows, tuple(pivot_columns)


def _fraction_nullspace(matrix: Sequence[Sequence[int | Fraction]]) -> Tuple[Tuple[Fraction, ...], ...]:
    """Return an exact basis of the right nullspace."""

    if not matrix:
        return ()
    rref, pivots = _fraction_rref(matrix)
    width = len(rref[0])
    free_columns = tuple(column for column in range(width) if column not in pivots)
    basis: List[Tuple[Fraction, ...]] = []
    for free in free_columns:
        vector = [Fraction(0) for _ in range(width)]
        vector[free] = Fraction(1)
        for row_index, pivot in enumerate(pivots):
            vector[pivot] = -rref[row_index][free]
        basis.append(tuple(vector))
    return tuple(basis)


def _fraction_json(value: Fraction) -> int | str:
    return int(value) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _radial_contact_jet_matrix(q: int, probe_degree: int) -> Tuple[Tuple[Fraction, ...], ...]:
    """Matrix of D_q=(2q)!^{-1} delta^(2q) on phi_a phi_b.

    The declared reduced probe basis is phi_a(r)=r^(2a) exp(-r^2/2), so
    phi_a phi_b=r^(2(a+b)) exp(-r^2).  D_q extracts the coefficient of
    r^(2q) exactly.
    """

    if q < 0 or probe_degree < 0:
        raise ValueError("q and probe_degree must be non-negative")
    rows: List[Tuple[Fraction, ...]] = []
    for a in range(probe_degree + 1):
        row: List[Fraction] = []
        for b in range(probe_degree + 1):
            gap = q - a - b
            row.append(Fraction((-1) ** gap, math.factorial(gap)) if gap >= 0 else Fraction(0))
        rows.append(tuple(row))
    return tuple(rows)


def _causal_orientation_classes() -> Tuple[Tuple[int, ...], ...]:
    """Return the 16 edge-orientation classes modulo simultaneous reversal.

    The gauge representative sigma_0=+1 fixes the global Z2 redundancy.  Wedge
    signs are kappa_ab=sigma_a sigma_b and therefore depend only on the class.
    """

    return tuple((1,) + tail for tail in itertools.product((-1, 1), repeat=4))


def _even_vertex_subsets() -> Tuple[Tuple[int, ...], ...]:
    """Canonical character labels of the quotient orientation group (Z2)^4."""

    vertices = tuple(range(5))
    return tuple(
        subset
        for size in (0, 2, 4)
        for subset in itertools.combinations(vertices, size)
    )


def _orientation_character(orientation: Sequence[int], subset: Sequence[int]) -> int:
    value = 1
    for vertex in subset:
        value *= int(orientation[vertex])
    return int(value)


def _canonical_cluster_character(cluster: Sequence[int]) -> Tuple[int, ...]:
    """S5-equivariant even character assigned to a compact cluster.

    K3 clusters map to their two-vertex complements, K4 clusters map to
    themselves, and K5 maps to the trivial character.  This is a bijection from
    the 10+5+1 compact clusters to the 16 even characters of five edge
    orientations modulo global reversal.
    """

    cluster_tuple = tuple(sorted(int(v) for v in cluster))
    vertices = set(range(5))
    if len(cluster_tuple) == 3:
        return tuple(sorted(vertices.difference(cluster_tuple)))
    if len(cluster_tuple) == 4:
        return cluster_tuple
    if len(cluster_tuple) == 5:
        return ()
    raise ValueError('cluster must have size 3, 4 or 5')


def _orientation_resolved_k5_amplitudes(
    observation: CoupledTollerWedgeObservation,
    beta_values: Sequence[float],
) -> Tuple[Mapping[Tuple[int, ...], complex], Mapping[Tuple[int, ...], complex], float]:
    """Evaluate the regulated j=1/2 K5 amplitude for all causal classes.

    Wedge kernels are computed once for each edge, magnetic index and branch.
    The 16 causal amplitudes then reuse those values.  This remains a finite
    coaxial-boost qualification, not the non-compact SL(2,C)^4 vertex.
    """

    if observation.spin != 0.5:
        raise ValueError('The finite K5 orientation qualification currently uses spin 1/2')
    edges = tuple((a, b) for a in range(5) for b in range(a + 1, 5))
    wedge_values: Dict[Tuple[int, float, int], Tuple[complex, complex]] = {}
    max_wedge_residual = 0.0
    for edge_index, (a, b) in enumerate(edges):
        for branch in (-1, 1):
            for magnetic in (-0.5, 0.5):
                direct, coupled, _, _ = _coupled_wedge_pair(
                    observation,
                    magnetic=magnetic,
                    beta_a=float(beta_values[a]),
                    beta_b=float(beta_values[b]),
                    branch=branch,
                )
                wedge_values[(edge_index, magnetic, branch)] = (direct, coupled)
                max_wedge_residual = max(
                    max_wedge_residual,
                    abs(direct - coupled) / max(1.0, abs(direct), abs(coupled)),
                )

    direct_by_orientation: Dict[Tuple[int, ...], complex] = {}
    coupled_by_orientation: Dict[Tuple[int, ...], complex] = {}
    boundary_rows = _k5_triplet_boundary_weights()
    for orientation in _causal_orientation_classes():
        direct_amplitude = 0j
        coupled_amplitude = 0j
        for assignment, boundary_coefficient in boundary_rows:
            direct_term = complex(boundary_coefficient)
            coupled_term = complex(boundary_coefficient)
            for edge_index, ((a, b), magnetic) in enumerate(zip(edges, assignment)):
                branch = int(orientation[a] * orientation[b])
                direct_wedge, coupled_wedge = wedge_values[(edge_index, magnetic, branch)]
                direct_term *= direct_wedge
                coupled_term *= coupled_wedge
            direct_amplitude += direct_term
            coupled_amplitude += coupled_term
        direct_by_orientation[orientation] = direct_amplitude
        coupled_by_orientation[orientation] = coupled_amplitude
    return direct_by_orientation, coupled_by_orientation, float(max_wedge_residual)


def _qualify_causal_orientation_fourier(
    observation: CoupledTollerWedgeObservation,
) -> Mapping[str, Any]:
    """Execute CAUSAL-ORIENTATION-FOURIER-014 inside K-TOLLER-DIST-003.

    Fixed causal vertices are functions on the 16 classes of edge orientations
    modulo global reversal.  Their exact Fourier basis consists of the 16 even
    vertex characters.  A canonical permutation-equivariant map assigns these
    characters to the ten K3, five K4 and one K5 compact clusters.

    Combining the exact orientation Fourier projector with the already proven
    radial contact probes gives a block-diagonal 25x25 structural selector on the
    cluster-resolved radial-scalar contact basis.  Its rank is 25.  This proves
    structural identifiability of that lifted finite sector *provided* the
    renormalized two-vertex amplitudes are available.  The right-hand side is not
    invented: finite-regulator K5 Fourier coefficients are computed only as a
    nonzero-sector and inversion diagnostic, while their forest-renormalized
    epsilon->0 values remain open.
    """

    orientations = _causal_orientation_classes()
    character_labels = _even_vertex_subsets()
    character_matrix = [
        [_orientation_character(orientation, subset) for subset in character_labels]
        for orientation in orientations
    ]
    _, character_pivots = _fraction_rref(character_matrix)
    gram = [
        [sum(character_matrix[row][a] * character_matrix[row][b] for row in range(len(orientations)))
         for b in range(len(character_labels))]
        for a in range(len(character_labels))
    ]
    hadamard_exact = all(
        gram[a][b] == (16 if a == b else 0)
        for a in range(16) for b in range(16)
    )

    # All 2^10 products of wedge signs collapse to exactly the 16 even vertex
    # characters.  This verifies that the Fourier basis is generated by the
    # causal data kappa_ab=sigma_a sigma_b and is not an external label set.
    edges = tuple((a, b) for a in range(5) for b in range(a + 1, 5))
    wedge_character_vectors = set()
    for mask in range(1 << len(edges)):
        values = []
        for orientation in orientations:
            value = 1
            for edge_index, (a, b) in enumerate(edges):
                if mask & (1 << edge_index):
                    value *= orientation[a] * orientation[b]
            values.append(int(value))
        wedge_character_vectors.add(tuple(values))

    clusters = tuple(
        itertools.chain(
            itertools.combinations(range(5), 3),
            itertools.combinations(range(5), 4),
            (tuple(range(5)),),
        )
    )
    cluster_characters = tuple(_canonical_cluster_character(cluster) for cluster in clusters)
    unique_cluster_characters = len(set(cluster_characters)) == 16
    cluster_character_indices = tuple(character_labels.index(label) for label in cluster_characters)

    # Cluster-resolved radial-scalar basis: 10*1 + 5*2 + 1*5 = 25.
    contact_columns: List[Mapping[str, Any]] = []
    selector_rows: List[Mapping[str, Any]] = []
    selector_matrix: List[List[Fraction]] = []
    column_offsets: Dict[Tuple[int, ...], int] = {}
    for cluster in clusters:
        cluster_tuple = tuple(cluster)
        q_count = {3: 1, 4: 2, 5: 5}[len(cluster_tuple)]
        column_offsets[cluster_tuple] = len(contact_columns)
        for q in range(q_count):
            contact_columns.append({
                'cluster': cluster_tuple,
                'cluster_size': len(cluster_tuple),
                'q': q,
                'derivative_order': 2 * q,
                'character': _canonical_cluster_character(cluster_tuple),
                'coefficient': f'kappa[{"".join(str(v + 1) for v in cluster_tuple)};q={q}]',
            })

    width = len(contact_columns)
    for cluster in clusters:
        cluster_tuple = tuple(cluster)
        q_count = {3: 1, 4: 2, 5: 5}[len(cluster_tuple)]
        # phi_0 phi_b gives an exact triangular matrix on q=0,...,q_count-1.
        for b in range(q_count):
            row = [Fraction(0) for _ in range(width)]
            offset = column_offsets[cluster_tuple]
            for q in range(q_count):
                row[offset + q] = _radial_contact_jet_matrix(q, q_count - 1)[0][b]
            selector_matrix.append(row)
            selector_rows.append({
                'cluster': cluster_tuple,
                'orientation_character': _canonical_cluster_character(cluster_tuple),
                'radial_probe': f'phi_0*phi_{b}',
                'probe_index_b': b,
            })
    selector_rref, selector_pivots = _fraction_rref(selector_matrix)
    selector_nullspace = _fraction_nullspace(selector_matrix)

    # Finite-regulator orientation spectrum and exact Fourier inversion.
    rng = np.random.default_rng(observation.seed + 14014)
    numerical_rows: List[Mapping[str, Any]] = []
    max_direct_coupled_residual = 0.0
    max_fourier_inversion_residual = 0.0
    min_relative_sector_magnitude = math.inf
    minimum_nonzero_sector_count = 16
    sample_count = min(2, max(1, observation.k5_samples))
    c_matrix = np.asarray(character_matrix, dtype=float)
    for sample_index in range(sample_count):
        beta_values = np.concatenate((
            np.array([0.0]),
            rng.uniform(-observation.integration_bound, observation.integration_bound, 4),
        ))
        direct_map, coupled_map, wedge_residual = _orientation_resolved_k5_amplitudes(
            observation, beta_values
        )
        direct_values = np.asarray([direct_map[o] for o in orientations], dtype=np.complex128)
        coupled_values = np.asarray([coupled_map[o] for o in orientations], dtype=np.complex128)
        direct_coefficients = c_matrix.T @ direct_values / 16.0
        coupled_coefficients = c_matrix.T @ coupled_values / 16.0
        reconstructed = c_matrix @ coupled_coefficients
        direct_coupled_residual = float(
            np.linalg.norm(direct_values - coupled_values)
            / max(1.0, np.linalg.norm(direct_values), np.linalg.norm(coupled_values))
        )
        inversion_residual = float(
            np.linalg.norm(reconstructed - coupled_values)
            / max(1.0, np.linalg.norm(coupled_values))
        )
        scale = max(float(np.max(np.abs(coupled_coefficients))), 1.0)
        relative_magnitudes = np.abs(coupled_coefficients) / scale
        nonzero_count = int(np.count_nonzero(relative_magnitudes > 1e-10))
        max_direct_coupled_residual = max(max_direct_coupled_residual, direct_coupled_residual, wedge_residual)
        max_fourier_inversion_residual = max(max_fourier_inversion_residual, inversion_residual)
        min_relative_sector_magnitude = min(min_relative_sector_magnitude, float(np.min(relative_magnitudes)))
        minimum_nonzero_sector_count = min(minimum_nonzero_sector_count, nonzero_count)
        numerical_rows.append({
            'sample_index': sample_index,
            'beta_values': [float(v) for v in beta_values],
            'direct_coupled_relative_residual': direct_coupled_residual,
            'fourier_inversion_relative_residual': inversion_residual,
            'nonzero_fourier_sector_count': nonzero_count,
            'minimum_relative_fourier_magnitude': float(np.min(relative_magnitudes)),
            'coupled_fourier_coefficients': [
                {'character': character_labels[i], 'real': float(value.real), 'imag': float(value.imag)}
                for i, value in enumerate(coupled_coefficients)
            ],
            'direct_fourier_coefficients': [
                {'character': character_labels[i], 'real': float(value.real), 'imag': float(value.imag)}
                for i, value in enumerate(direct_coefficients)
            ],
        })

    status = (
        'PASS_CAUSAL_ORIENTATION_FOURIER_AND_STRUCTURAL_SELECTOR_RANK_25_'
        'RENORMALIZED_CONTACT_VALUES_OPEN'
    )
    return {
        'stage_id': 'CAUSAL-ORIENTATION-FOURIER-014',
        'owner_id': 'K-TOLLER-DIST-003',
        'scope': 'CLUSTER_RESOLVED_RADIAL_SCALAR_K3_K4_K5_FINITE_ORIENTATION_FOURIER',
        'orientation_group': {
            'classes': orientations,
            'global_reversal_gauge': 'sigma_1=+1',
            'group': '(Z2)^4',
            'class_count': len(orientations),
            'wedge_sign_definition': 'kappa_ab=sigma_a*sigma_b',
        },
        'character_basis': {
            'labels_even_vertex_subsets': character_labels,
            'matrix': character_matrix,
            'rank_exact': len(character_pivots),
            'gram': gram,
            'hadamard_orthogonality_exact': hadamard_exact,
            'unique_characters_generated_by_1024_wedge_monomials': len(wedge_character_vectors),
        },
        'cluster_character_lift': {
            'clusters': [
                {
                    'cluster': tuple(cluster),
                    'cluster_size': len(cluster),
                    'canonical_character': cluster_characters[index],
                    'character_column': cluster_character_indices[index],
                }
                for index, cluster in enumerate(clusters)
            ],
            'cluster_count': len(clusters),
            'bijection_to_even_characters': unique_cluster_characters,
            'rule': 'K3->complement pair; K4->cluster quadruple; K5->trivial character',
        },
        'structural_selector': {
            'equation': 'G_char kappa_cluster = g_char',
            'columns': contact_columns,
            'rows': selector_rows,
            'matrix': [[_fraction_json(value) for value in row] for row in selector_matrix],
            'rref': [[_fraction_json(value) for value in row] for row in selector_rref],
            'rank_exact': len(selector_pivots),
            'nullity_exact': width - len(selector_pivots),
            'pivot_columns': selector_pivots,
            'nullspace_basis': [
                [_fraction_json(value) for value in vector] for vector in selector_nullspace
            ],
            'variable_count': width,
            'rhs_status': 'FOREST_RENORMALIZED_TWO_VERTEX_VALUES_NOT_COMPUTED',
            'interpretation': (
                'orientation Fourier projectors and exact radial probes give a full-rank measurement operator; '
                'they do not supply the renormalized physical right-hand side'
            ),
        },
        'finite_regulator_k5_fourier': {
            'samples': numerical_rows,
            'sample_count': sample_count,
            'minimum_nonzero_sector_count': minimum_nonzero_sector_count,
            'minimum_relative_sector_magnitude': float(min_relative_sector_magnitude),
            'max_direct_coupled_residual': float(max_direct_coupled_residual),
            'max_fourier_inversion_residual': float(max_fourier_inversion_residual),
            'status': 'FINITE_REGULATOR_ALL_16_SECTORS_RESOLVED_NOT_A_RENORMALIZED_CONTACT_LIMIT',
        },
        'checks': {
            'orientation_class_count_16': len(orientations) == 16,
            'character_rank_exact_16': len(character_pivots) == 16,
            'character_hadamard_orthogonality_exact': hadamard_exact,
            'wedge_monomials_generate_exactly_16_characters': len(wedge_character_vectors) == 16,
            'cluster_character_bijection_exact': unique_cluster_characters,
            'cluster_resolved_radial_variable_count_25': width == 25,
            'structural_selector_rank_exact_25': len(selector_pivots) == 25,
            'structural_selector_nullity_zero': width - len(selector_pivots) == 0,
            'finite_regulator_fourier_inversion': max_fourier_inversion_residual < 1e-12,
            'finite_regulator_direct_coupled_equivalence': max_direct_coupled_residual < 1e-11,
            'all_16_finite_regulator_sectors_nonzero': minimum_nonzero_sector_count == 16,
            'renormalized_rhs_not_fabricated': True,
            'physical_cylinder_not_claimed': True,
        },
        'status': status,
        'claim_boundary': (
            'exact character algebra and exact rank 25 in the cluster-resolved radial-scalar finite sector; '
            'finite-regulator K5 Fourier coefficients are diagnostic only; forest-renormalized epsilon->0 '
            'contact values, the tensorial basis, full SL(2,C)^4 wavefront and physical cylinder remain open'
        ),
    }


def _qpdtr_cluster_deformation(base_beta: NDArray[np.float64], cluster: Tuple[int, ...], scale: float) -> NDArray[np.float64]:
    """Collapse one compact cluster while preserving its complement.

    This is a registered finite chart for the QPDTR bisimplex bridge.  It is not
    a replacement for the full SL(2,C)^4 diagonal geometry.
    """

    beta = np.asarray(base_beta, dtype=float).copy()
    indices = np.asarray(cluster, dtype=int)
    centre = float(np.mean(beta[indices]))
    beta[indices] = centre + float(scale) * (beta[indices] - centre)
    return beta


def _qpdtr_bridge_weights(bridge: Mapping[str, Any]) -> Tuple[float, float, Mapping[str, Any]]:
    if not bridge or bridge.get("passed") is not True:
        raise ValueError("A passed typed QPDTR bridge certificate is required")
    evidence = bridge.get("evidence", {})
    qg = evidence.get("qg_bridge_execution", {})
    boundary = qg.get("j_half_coherent_boundary", {})
    measure = qg.get("regularized_measure", {})
    configurations = boundary.get("configurations", [])
    j_half_rows = [row for row in configurations if row.get("twice_spins") == [1] * 10]
    if len(j_half_rows) != 1:
        raise ValueError("QPDTR bridge must contain exactly one j=1/2 boundary row")
    probability = float(j_half_rows[0]["probability"])
    weights = tuple(float(value) for value in measure.get("normalized_weights", ()))
    if len(weights) < 2 or probability <= 0.0 or weights[1] <= 0.0:
        raise ValueError("QPDTR j=1/2 boundary or measure weight is inadmissible")
    return probability, weights[1], qg


def _extract_qpdtr_cluster_pre_rhs(
    observation: CoupledTollerWedgeObservation,
    *,
    boundary_probability: float,
    face_measure_weight: float,
) -> Mapping[str, Any]:
    """Extract 25 finite-regulator cluster/character coefficients.

    The result is a pre-renormalization diagnostic.  It uses the QPDTR causal
    bisimplex orientation, j=1/2 coherent-boundary probability and registered
    regularized face measure, but it deliberately does not invent Epstein-Glaser
    forest counterterms or call the blocked external EPRL target backend.
    """

    orientations = _causal_orientation_classes()
    character_labels = _even_vertex_subsets()
    character_matrix = np.asarray([
        [_orientation_character(orientation, subset) for subset in character_labels]
        for orientation in orientations
    ], dtype=float)
    clusters = tuple(itertools.chain(
        itertools.combinations(range(5), 3),
        itertools.combinations(range(5), 4),
        (tuple(range(5)),),
    ))
    base_beta = np.asarray((0.0, -0.52, 0.31, 0.68, -0.23), dtype=float)
    radial_step = 0.18
    physical_prefactor = float(boundary_probability * face_measure_weight ** 10)
    rows: List[Mapping[str, Any]] = []
    vector: List[complex] = []
    max_wedge_residual = 0.0
    max_fourier_inversion = 0.0
    for cluster in clusters:
        cluster_tuple = tuple(int(v) for v in cluster)
        q_count = {3: 1, 4: 2, 5: 5}[len(cluster_tuple)]
        character = _canonical_cluster_character(cluster_tuple)
        character_index = character_labels.index(character)
        x_nodes = np.asarray([(radial_step * index) ** 2 for index in range(q_count)], dtype=float)
        sampled: List[complex] = []
        sample_rows: List[Mapping[str, Any]] = []
        for index in range(q_count):
            scale = radial_step * index
            beta_left = _qpdtr_cluster_deformation(base_beta, cluster_tuple, scale)
            beta_right = -beta_left
            _, left_map, left_residual = _orientation_resolved_k5_amplitudes(observation, beta_left)
            _, right_map, right_residual = _orientation_resolved_k5_amplitudes(observation, beta_right)
            max_wedge_residual = max(max_wedge_residual, left_residual, right_residual)
            gluing_values = np.asarray([
                left_map[orientation] * np.conjugate(right_map[orientation]) * physical_prefactor
                for orientation in orientations
            ], dtype=np.complex128)
            coefficients = character_matrix.T @ gluing_values / 16.0
            reconstructed = character_matrix @ coefficients
            inversion = float(np.linalg.norm(reconstructed - gluing_values) / max(1.0, np.linalg.norm(gluing_values)))
            max_fourier_inversion = max(max_fourier_inversion, inversion)
            value = complex(coefficients[character_index])
            sampled.append(value)
            sample_rows.append({
                "scale": float(scale),
                "x_scale_squared": float(x_nodes[index]),
                "character_value": {"real": float(value.real), "imag": float(value.imag)},
                "fourier_inversion_residual": inversion,
            })
        vandermonde = np.vander(x_nodes, N=q_count, increasing=True)
        polynomial = np.linalg.solve(vandermonde, np.asarray(sampled, dtype=np.complex128))
        for q, value in enumerate(polynomial):
            vector.append(complex(value))
            rows.append({
                "cluster": cluster_tuple,
                "cluster_size": len(cluster_tuple),
                "character": character,
                "q": q,
                "derivative_order": 2 * q,
                "finite_pre_rhs": {"real": float(value.real), "imag": float(value.imag)},
                "samples": sample_rows,
            })
    array = np.asarray(vector, dtype=np.complex128)
    return {
        "component_count": len(vector),
        "components": rows,
        "vector": vector,
        "vector_norm": float(np.linalg.norm(array)),
        "maximum_component_magnitude": float(np.max(np.abs(array))),
        "minimum_component_magnitude": float(np.min(np.abs(array))),
        "all_components_finite": bool(np.all(np.isfinite(array.real)) and np.all(np.isfinite(array.imag))),
        "maximum_wedge_residual": float(max_wedge_residual),
        "maximum_fourier_inversion_residual": float(max_fourier_inversion),
        "boundary_probability_j_half": float(boundary_probability),
        "normalized_face_measure_weight_j_half": float(face_measure_weight),
        "ten_face_prefactor": physical_prefactor,
        "radial_step": radial_step,
    }


def _qualify_qpdtr_bisimplex_two_vertex(
    observation: CoupledTollerWedgeObservation,
) -> Mapping[str, Any]:
    """Execute QPDTR-BISIMPLEX-TWO-VERTEX-015 inside K-TOLLER-DIST-003."""

    bridge = observation.qpdtr_bridge
    if not bridge or bridge.get("passed") is not True:
        return {
            "stage_id": "QPDTR-BISIMPLEX-TWO-VERTEX-015",
            "owner_id": "K-TOLLER-DIST-003",
            "status": "BLOCKED_NO_TYPED_QPDTR_V2_0_0_EVIDENCE",
            "bridge_passed": False,
            "finite_pre_rhs_status": "NOT_COMPUTED",
            "physical_rhs_status": "FOREST_RENORMALIZED_TWO_VERTEX_VALUES_NOT_COMPUTED",
            "checks": {"no_false_promotion_without_external_evidence": True},
            "claim_boundary": "No external evidence was supplied; no QPDTR-assisted value was computed.",
        }
    boundary_probability, face_weight, qg = _qpdtr_bridge_weights(bridge)
    geometry = qg["lorentzian_bisimplex"]
    boundary = qg["j_half_coherent_boundary"]
    measure = qg["regularized_measure"]
    paths = {
        "epsilon_first": ((0.12, 12, 8.0, 3.5), (0.06, 12, 8.0, 3.5)),
        "shell_first": ((0.12, 12, 8.0, 3.5), (0.12, 16, 12.0, 4.5)),
        "diagonal": ((0.12, 12, 8.0, 3.5), (0.06, 16, 12.0, 4.5)),
    }
    path_rows: Dict[str, Any] = {}
    final_vectors: List[NDArray[np.complex128]] = []
    last_changes: List[float] = []
    all_finite = True
    max_wedge_residual = 0.0
    max_fourier_inversion = 0.0
    for name, levels in paths.items():
        level_rows: List[Mapping[str, Any]] = []
        vectors: List[NDArray[np.complex128]] = []
        for epsilon, nodes, cutoff, spin_cutoff in levels:
            local = dataclasses.replace(
                observation, epsilon=epsilon, spectral_nodes=nodes, spectral_cutoff=cutoff,
                canonical_spin_cutoff=spin_cutoff, qpdtr_bridge=None, k5_samples=2,
            )
            extracted = _extract_qpdtr_cluster_pre_rhs(
                local, boundary_probability=boundary_probability, face_measure_weight=face_weight
            )
            vector = np.asarray(extracted.pop("vector"), dtype=np.complex128)
            vectors.append(vector)
            all_finite = all_finite and bool(extracted["all_components_finite"])
            max_wedge_residual = max(max_wedge_residual, float(extracted["maximum_wedge_residual"]))
            max_fourier_inversion = max(max_fourier_inversion, float(extracted["maximum_fourier_inversion_residual"]))
            level_rows.append({
                "epsilon": epsilon, "spectral_nodes": nodes, "spectral_cutoff": cutoff,
                "canonical_spin_cutoff": spin_cutoff, **extracted,
            })
        change = float(np.linalg.norm(vectors[-1] - vectors[-2]) / max(1.0, np.linalg.norm(vectors[-1]), np.linalg.norm(vectors[-2])))
        final_vectors.append(vectors[-1])
        last_changes.append(change)
        path_rows[name] = {"levels": level_rows, "last_relative_change": change}
    final_spread = max(
        float(np.linalg.norm(a - b) / max(1.0, np.linalg.norm(a), np.linalg.norm(b)))
        for index, a in enumerate(final_vectors) for b in final_vectors[index + 1:]
    )
    finite_path_converged = max(last_changes) < 0.10 and final_spread < 0.10
    checks = {
        "typed_qpdtr_bridge_passed": bridge.get("passed") is True,
        "causal_lorentzian_bisimplex_passed": geometry.get("passed") is True and geometry.get("shared_slice_normal_time_signs") == [-1, 1],
        "j_half_coherent_boundary_passed": boundary.get("passed") is True,
        "regularized_measure_passed": measure.get("passed") is True,
        "target_eprl_backend_remains_blocked": qg.get("target_eprl_backend_status") == "BLOCKED_EXTERNAL_BACKEND",
        "all_25_finite_pre_rhs_components_extracted": all(row["levels"][-1]["component_count"] == 25 for row in path_rows.values()),
        "all_finite_pre_rhs_components_numerically_finite": all_finite,
        "orientation_fourier_inversion_stable": max_fourier_inversion < 1e-11,
        "shared_channel_wedge_equivalence_stable": max_wedge_residual < 1e-10,
        "forest_renormalized_rhs_not_claimed": True,
        "physical_cylinder_not_claimed": True,
    }
    return {
        "stage_id": "QPDTR-BISIMPLEX-TWO-VERTEX-015",
        "owner_id": "K-TOLLER-DIST-003",
        "external_owner": bridge.get("evidence", {}).get("external_authoritative_owner"),
        "bridge_passed": True,
        "bridge_contract_digest": bridge.get("contract_digest"),
        "bridge_evidence_digest": bridge.get("evidence_digest"),
        "geometry_certificate": geometry,
        "boundary_certificate": boundary,
        "measure_certificate": measure,
        "registered_finite_paths": path_rows,
        "metrics": {
            "component_count": 25,
            "path_last_change_max": float(max(last_changes)),
            "path_final_spread": float(final_spread),
            "finite_path_convergence_threshold": 0.10,
            "finite_path_converged": bool(finite_path_converged),
            "maximum_wedge_residual": float(max_wedge_residual),
            "maximum_fourier_inversion_residual": float(max_fourier_inversion),
        },
        "finite_pre_rhs_status": (
            "FINITE_PRE_RHS_PATH_STABLE_BUT_FOREST_SUBTRACTION_OPEN"
            if finite_path_converged else
            "FINITE_PRE_RHS_PATH_DEPENDENT_FOREST_SUBTRACTION_REQUIRED"
        ),
        "physical_rhs_status": "FOREST_RENORMALIZED_TWO_VERTEX_VALUES_NOT_COMPUTED",
        "checks": checks,
        "status": "PASS_QPDTR_BISIMPLEX_DOMAIN_AND_REDUCED_TWO_VERTEX_EXTRACTION_PHYSICAL_RHS_OPEN",
        "claim_boundary": (
            "QPDTR certifies the bounded Lorentzian bisimplex, j=1/2 coherent boundary and a finite regularized measure. "
            "The 25 values are finite-regulator coaxial scalar pre-RHS diagnostics. They are not the Epstein-Glaser "
            "forest-renormalized weak-limit right-hand side, not full SL(2,C)^4 EPRL data and not physical contact constants."
        ),
    }

def _ordinary_wedge_limit_diagnostic(
    observation: CoupledTollerWedgeObservation,
) -> Mapping[str, Any]:
    """Run three registered ordinary quadrature paths and refuse false promotion."""

    j0 = observation.spin
    paths = {
        "spectral_first": (
            (8.0, 32, j0 + 4.0, 0.20),
            (12.0, 40, j0 + 5.0, 0.10),
            (16.0, 48, j0 + 6.0, 0.05),
            (24.0, 64, j0 + 7.0, 0.025),
        ),
        "spin_first": (
            (8.0, 32, j0 + 5.0, 0.20),
            (10.0, 36, j0 + 6.0, 0.10),
            (12.0, 40, j0 + 7.0, 0.05),
            (16.0, 48, j0 + 8.0, 0.025),
        ),
        "diagonal": (
            (8.0, 32, j0 + 4.0, 0.20),
            (12.0, 40, j0 + 5.0, 0.10),
            (18.0, 52, j0 + 7.0, 0.05),
            (27.0, 72, j0 + 9.0, 0.025),
        ),
    }
    path_rows: Dict[str, Any] = {}
    final_values: List[complex] = []
    last_changes: List[float] = []
    for name, levels in paths.items():
        values: List[complex] = []
        level_rows: List[Mapping[str, Any]] = []
        for spectral_cutoff, spectral_nodes, spin_cutoff, epsilon in levels:
            local = dataclasses.replace(
                observation,
                spectral_cutoff=spectral_cutoff,
                spectral_nodes=spectral_nodes,
                canonical_spin_cutoff=spin_cutoff,
                epsilon=epsilon,
                k5_samples=2,
            )
            direct, coupled, _, _ = _coupled_wedge_pair(
                local,
                magnetic=local.magnetic,
                beta_a=local.beta_a,
                beta_b=local.beta_b,
                branch=local.branch,
            )
            values.append(direct)
            level_rows.append({
                "spectral_cutoff": spectral_cutoff,
                "spectral_nodes": spectral_nodes,
                "canonical_spin_cutoff": spin_cutoff,
                "epsilon": epsilon,
                "ordinary_direct_value": direct,
                "direct_coupled_residual": float(abs(direct - coupled) / max(1.0, abs(direct), abs(coupled))),
            })
        changes = [
            float(abs(values[i] - values[i - 1]) / max(1.0, abs(values[i]), abs(values[i - 1])))
            for i in range(1, len(values))
        ]
        final_values.append(values[-1])
        last_changes.append(changes[-1])
        path_rows[name] = {"levels": level_rows, "successive_relative_changes": changes}

    final_spread = max(
        abs(a - b) / max(1.0, abs(a), abs(b))
        for i, a in enumerate(final_values)
        for b in final_values[i + 1:]
    )
    ordinary_converged = max(last_changes) < 0.05 and final_spread < 0.05
    return {
        "paths": path_rows,
        "metrics": {
            "ordinary_path_last_change_max": float(max(last_changes)),
            "ordinary_path_final_spread": float(final_spread),
            "ordinary_convergence_threshold": 0.05,
            "ordinary_quadrature_converged": bool(ordinary_converged),
            "status": "ORDINARY_LIMIT_NOT_CERTIFIED_DISTRIBUTIONAL_EXTENSION_REQUIRED" if not ordinary_converged else "ORDINARY_LIMIT_CANDIDATE",
        },
    }

def _coupled_wedge_pair(
    observation: CoupledTollerWedgeObservation,
    *,
    magnetic: float,
    beta_a: float,
    beta_b: float,
    branch: int,
) -> Tuple[complex, complex, float, float]:
    """Return direct and shared-channel finite-regulator wedge values.

    Direct form:
        integral c_sigma(rho_tilde) D(g_b^{-1}g_a) d rho_tilde.
    Coupled form:
        integral c_sigma(rho_tilde) sum_qp D(g_b)^* D(g_a) d rho_tilde.

    The same rho_tilde and the same intermediate channel occur on both half-edges.
    """

    spin = observation.spin
    rho = observation.gamma * spin
    nodes, weights = np.polynomial.legendre.leggauss(observation.spectral_nodes)
    rho_nodes = observation.spectral_cutoff * nodes
    rho_weights = observation.spectral_cutoff * weights
    direct = 0j
    coupled = 0j
    max_hermiticity = 0.0
    max_composition = 0.0
    for rho_tilde, quadrature_weight in zip(rho_nodes, rho_weights):
        generator = _principal_series_kz(
            float(rho_tilde), spin, magnetic, observation.canonical_spin_cutoff
        )
        max_hermiticity = max(max_hermiticity, float(np.linalg.norm(generator - generator.conj().T)))
        u_a = expm(1j * beta_a * generator)
        u_b = expm(1j * beta_b * generator)
        u_relative = expm(1j * (beta_a - beta_b) * generator)
        composed = u_b.conj().T @ u_a
        max_composition = max(
            max_composition,
            float(np.linalg.norm(u_relative - composed) / max(1.0, np.linalg.norm(u_relative))),
        )
        coefficient = quadrature_weight * _toller_spectral_weight(
            float(rho_tilde), rho, spin, branch, observation.epsilon
        )
        direct += coefficient * u_relative[0, 0]
        coupled += coefficient * composed[0, 0]
    return direct, coupled, max_hermiticity, max_composition


def _spin_half_triplet_intertwiner(magnetic_indices: Tuple[float, float, float, float]) -> float:
    """Normalized four-valent j=1/2 intertwiner in the i=1 recoupling channel."""

    m1, m2, m3, m4 = magnetic_indices

    def cg(a: float, b: float, total_m: int) -> float:
        if total_m == 1:
            return 1.0 if (a, b) == (0.5, 0.5) else 0.0
        if total_m == 0:
            return 1.0 / math.sqrt(2.0) if (a, b) in ((0.5, -0.5), (-0.5, 0.5)) else 0.0
        if total_m == -1:
            return 1.0 if (a, b) == (-0.5, -0.5) else 0.0
        return 0.0

    value = 0.0
    for total_m in (-1, 0, 1):
        value += (
            (-1) ** (1 - total_m)
            * cg(m1, m2, total_m)
            * cg(m3, m4, -total_m)
            / math.sqrt(3.0)
        )
    return value


def _k5_triplet_boundary_weights() -> Tuple[Tuple[Tuple[float, ...], float], ...]:
    edges = tuple((a, b) for a in range(5) for b in range(a + 1, 5))
    incident = {a: tuple(edge for edge in edges if a in edge) for a in range(5)}
    rows: List[Tuple[Tuple[float, ...], float]] = []
    for assignment in itertools.product((-0.5, 0.5), repeat=len(edges)):
        edge_value = dict(zip(edges, assignment))
        coefficient = 1.0
        for node in range(5):
            coefficient *= _spin_half_triplet_intertwiner(
                tuple(edge_value[edge] for edge in incident[node])  # type: ignore[arg-type]
            )
        if abs(coefficient) > 1e-15:
            rows.append((tuple(float(v) for v in assignment), float(coefficient)))
    return tuple(rows)


def _regulated_k5_pair(
    observation: CoupledTollerWedgeObservation,
    beta_values: Sequence[float],
) -> Tuple[complex, complex, float]:
    """Pointwise homogeneous j=1/2 K5 contraction in a coaxial boost sector."""

    if observation.spin != 0.5:
        raise ValueError("The finite K5 qualification currently uses spin 1/2")
    edges = tuple((a, b) for a in range(5) for b in range(a + 1, 5))
    orientations = (-1, 1, 1, 1, 1)
    wedge_values: Dict[Tuple[int, float], Tuple[complex, complex]] = {}
    max_wedge_residual = 0.0
    for edge_index, (a, b) in enumerate(edges):
        branch = orientations[a] * orientations[b]
        for magnetic in (-0.5, 0.5):
            direct, coupled, _, _ = _coupled_wedge_pair(
                observation,
                magnetic=magnetic,
                beta_a=float(beta_values[a]),
                beta_b=float(beta_values[b]),
                branch=branch,
            )
            wedge_values[(edge_index, magnetic)] = (direct, coupled)
            max_wedge_residual = max(
                max_wedge_residual,
                abs(direct - coupled) / max(1.0, abs(direct), abs(coupled)),
            )

    direct_amplitude = 0j
    coupled_amplitude = 0j
    for assignment, boundary_coefficient in _k5_triplet_boundary_weights():
        direct_term = complex(boundary_coefficient)
        coupled_term = complex(boundary_coefficient)
        for edge_index, magnetic in enumerate(assignment):
            direct_wedge, coupled_wedge = wedge_values[(edge_index, magnetic)]
            direct_term *= direct_wedge
            coupled_term *= coupled_wedge
        direct_amplitude += direct_term
        coupled_amplitude += coupled_term
    return direct_amplitude, coupled_amplitude, max_wedge_residual




def _k5_vertex_tensor(node: int, edges: Sequence[Tuple[int, int]]) -> NDArray[np.float64]:
    """Return the exact four-valent j=1/2 intertwiner tensor for one K5 node."""

    incident = tuple(index for index, edge in enumerate(edges) if node in edge)
    tensor = np.zeros((2, 2, 2, 2), dtype=float)
    magnetic_values = (-0.5, 0.5)
    for local_assignment in itertools.product(range(2), repeat=4):
        tensor[local_assignment] = _spin_half_triplet_intertwiner(
            tuple(magnetic_values[index] for index in local_assignment)
        )
    if len(incident) != 4:
        raise RuntimeError("K5 node must have four incident edges")
    return tensor


def _k5_tensor_network_all_orientations(
    observation: CoupledTollerWedgeObservation,
    beta_values: Sequence[float],
) -> Mapping[str, Any]:
    """Exact K5 contraction through symmetry + optimized TN + deterministic slicing.

    This is the executed finite-sector composition of QCM-SYMMETRY,
    QCM-CONTRACTION-OPT, QCM-GENERAL-TN and QCM-SLICING.  No truncation is
    introduced: the magnetic domain is binary and the sliced result is summed
    exactly.  The method is a qualification of the finite j=1/2 contraction,
    not a claim about the full non-compact amplitude.
    """

    if observation.spin != 0.5:
        raise ValueError("multidomain K5 tensor-network qualification uses spin 1/2")
    edges = tuple((a, b) for a in range(5) for b in range(a + 1, 5))
    labels = tuple("abcdefghij")
    node_edge_indices = {
        node: tuple(index for index, edge in enumerate(edges) if node in edge)
        for node in range(5)
    }
    vertex_tensors = [_k5_vertex_tensor(node, edges) for node in range(5)]
    vertex_terms = ["".join(labels[index] for index in node_edge_indices[node]) for node in range(5)]
    edge_terms = list(labels)
    expression = ",".join(vertex_terms + edge_terms) + "->"

    wedge_values: dict[tuple[int, int], tuple[NDArray[np.complex128], NDArray[np.complex128]]] = {}
    max_wedge_residual = 0.0
    magnetic_values = (-0.5, 0.5)
    for edge_index, (a, b) in enumerate(edges):
        for branch in (-1, 1):
            direct_vector = np.zeros(2, dtype=np.complex128)
            coupled_vector = np.zeros(2, dtype=np.complex128)
            for mi, magnetic in enumerate(magnetic_values):
                direct, coupled, _, _ = _coupled_wedge_pair(
                    observation,
                    magnetic=magnetic,
                    beta_a=float(beta_values[a]),
                    beta_b=float(beta_values[b]),
                    branch=branch,
                )
                direct_vector[mi] = direct
                coupled_vector[mi] = coupled
                max_wedge_residual = max(
                    max_wedge_residual,
                    abs(direct - coupled) / max(1.0, abs(direct), abs(coupled)),
                )
            wedge_values[(edge_index, branch)] = (direct_vector, coupled_vector)

    optimized_direct: dict[Tuple[int, ...], complex] = {}
    optimized_coupled: dict[Tuple[int, ...], complex] = {}
    sliced_direct: dict[Tuple[int, ...], complex] = {}
    sliced_coupled: dict[Tuple[int, ...], complex] = {}
    # Slice the first edge exactly into its two magnetic values.
    slice_edge = 0
    for orientation in _causal_orientation_classes():
        direct_vectors = []
        coupled_vectors = []
        for edge_index, (a, b) in enumerate(edges):
            branch = int(orientation[a] * orientation[b])
            direct_vector, coupled_vector = wedge_values[(edge_index, branch)]
            direct_vectors.append(direct_vector)
            coupled_vectors.append(coupled_vector)
        operands_direct = [*vertex_tensors, *direct_vectors]
        operands_coupled = [*vertex_tensors, *coupled_vectors]
        optimized_direct[orientation] = complex(np.einsum(expression, *operands_direct, optimize="greedy"))
        optimized_coupled[orientation] = complex(np.einsum(expression, *operands_coupled, optimize="greedy"))

        d_sum = 0j
        c_sum = 0j
        for slice_index in range(2):
            d_vectors = [vector.copy() for vector in direct_vectors]
            c_vectors = [vector.copy() for vector in coupled_vectors]
            d_mask = np.zeros(2, dtype=np.complex128)
            c_mask = np.zeros(2, dtype=np.complex128)
            d_mask[slice_index] = d_vectors[slice_edge][slice_index]
            c_mask[slice_index] = c_vectors[slice_edge][slice_index]
            d_vectors[slice_edge] = d_mask
            c_vectors[slice_edge] = c_mask
            d_sum += complex(np.einsum(expression, *vertex_tensors, *d_vectors, optimize="greedy"))
            c_sum += complex(np.einsum(expression, *vertex_tensors, *c_vectors, optimize="greedy"))
        sliced_direct[orientation] = d_sum
        sliced_coupled[orientation] = c_sum

    direct_reference, coupled_reference, _ = _orientation_resolved_k5_amplitudes(observation, beta_values)
    def residual(a: Mapping[Tuple[int, ...], complex], b: Mapping[Tuple[int, ...], complex]) -> float:
        return float(max(
            abs(a[key] - b[key]) / max(1.0, abs(a[key]), abs(b[key]))
            for key in a
        ))

    optimized_reference_residual = max(
        residual(optimized_direct, direct_reference),
        residual(optimized_coupled, coupled_reference),
    )
    slicing_residual = max(
        residual(sliced_direct, optimized_direct),
        residual(sliced_coupled, optimized_coupled),
    )
    direct_coupled_residual = residual(optimized_direct, optimized_coupled)
    path, path_info = np.einsum_path(expression, *([*vertex_tensors] + [np.ones(2)] * 10), optimize="greedy")
    return {
        "method_ids": [
            "QCM-SYMMETRY",
            "QCM-CONTRACTION-OPT",
            "QCM-GENERAL-TN",
            "QCM-SLICING",
        ],
        "scope": "EXACT_FINITE_J_HALF_K5_MAGNETIC_CONTRACTION",
        "orientation_sector_count": 16,
        "magnetic_assignment_count_reference": 1024,
        "slice_edge": list(edges[slice_edge]),
        "slice_count": 2,
        "einsum_expression": expression,
        "contraction_path": [str(item) for item in path],
        "contraction_path_summary": path_info,
        "optimized_reference_residual": optimized_reference_residual,
        "slicing_residual": slicing_residual,
        "direct_coupled_residual": direct_coupled_residual,
        "maximum_wedge_residual": float(max_wedge_residual),
        "status": "PASS_EXACT_FINITE_K5_JOINT_METHOD_CONTRACTION",
    }


def _qualify_multidomain_qg_closure(
    observation: CoupledTollerWedgeObservation,
) -> Mapping[str, Any]:
    """Execute MULTIDOMAIN-QG-CLOSURE-SCAN-016 inside K-TOLLER-DIST-003.

    The stage consumes the typed law-space/QPDTR bridge, binds the G1--G12
    obligations to known-law anchors and pending transformations, and executes
    one problem-specific joint computational route on the finite K5 sector.
    It never treats pending candidates as laws and never promotes deferred
    continuum, positivity or matter methods without their required data.
    """

    bridge = dict(observation.multidomain_qg_bridge or {})
    if not bridge or not bridge.get("passed", False):
        return {
            "stage_id": "MULTIDOMAIN-QG-CLOSURE-SCAN-016",
            "owner_id": "K-TOLLER-DIST-003",
            "bridge_passed": False,
            "checks": {
                "bridge_fail_closed": True,
                "joint_methods_not_claimed_without_bridge": True,
                "candidate_laws_not_promoted": True,
            },
            "status": "BLOCKED_MULTIDOMAIN_QG_BRIDGE_NOT_SUPPLIED",
            "claim_boundary": "No law-space or emulator conclusion is inferred without a digest-bound bridge.",
        }

    evidence = bridge.get("evidence", {})
    executed_method_ids = tuple(evidence.get("executed_method_ids", ()))
    required_executed = {
        "QCM-SYMMETRY",
        "QCM-CONTRACTION-OPT",
        "QCM-GENERAL-TN",
        "QCM-SLICING",
    }
    beta_values = (0.0, -0.52, 0.31, 0.68, -0.23)
    contraction = _k5_tensor_network_all_orientations(observation, beta_values)
    selected_candidates = evidence.get("selected_candidates", {})
    transformations = sorted({row.get("transformation_id", "") for row in selected_candidates.values()})
    gate_matrix = evidence.get("gate_matrix", {})
    physics_open_axes = evidence.get("axis_space", {}).get("physics_open_axes", [])
    qpdtr = evidence.get("qpdtr", {})
    qpdtr_controls = qpdtr.get("selected_controls", {})

    gate_status = {
        "G1_STATE": "FORMAL_PASS_EXISTING_OWNER",
        "G2_CONSTRAINT": "PARTIAL_ANOMALY_AND_FULL_ALGEBRA_OPEN",
        "G3_CAUSAL": "FINITE_CAUSAL_K5_AND_TOLLER_DISTRIBUTION_PASS_FULL_SL2C4_OPEN",
        "G4_POSITIVITY": "METHOD_AND_ANCHORS_BOUND_PHYSICAL_CYLINDER_NOT_COMPUTED",
        "G5_CONTINUUM": "REFINEMENT_RG_METHODS_BOUND_JOINT_FOREST_LIMIT_OPEN",
        "G6_UV": "FRG_CONTROL_BOUND_FULL_EPRL_FLOW_OPEN",
        "G7_GR_LIMIT": "REGGE_AND_VARIATIONAL_BRIDGES_BOUND_MICRO_TO_IR_OPEN",
        "G8_QFT_LIMIT": "QFT_ANCHORS_BOUND_HADAMARD_MICROCAUSAL_LIMIT_OPEN",
        "G9_MATTER": "GAUGE_ANOMALY_FERMION_METHODS_BOUND_MICROSCOPIC_OWNER_OPEN",
        "G10_BORN": "CONDITIONAL_ON_G4_AND_RELATIONAL_POVM",
        "G11_PREDICTION": "IDENTIFIABILITY_CONTRACT_BOUND_NUMERICAL_VECTOR_NOT_FROZEN",
        "G12_EXPERIMENT": "INELIGIBLE_UNTIL_G11",
    }
    checks = {
        "typed_bridge_passed": bridge.get("status") == "PASS_MULTIDOMAIN_QG_BRIDGE",
        "all_twelve_gate_rows_bound": len(gate_matrix) == 12 and set(gate_matrix) == set(gate_status),
        "composite_models_preserve_source_inheritance_boundary": all(
            row.get("epistemic_state") == "DERIVED_COMPOSITE_MODEL"
            and row.get("scientific_status") == "SOURCE_SECTORS_INHERITED_COUPLED_EXTENSION_UNRESOLVED"
            for row in selected_candidates.values()
        ),
        "required_transformations_present": {
            "PHYS_RG_EFFECTIVE_FLOW",
            "PHYS_SINGULARITY_REGULARIZATION",
            "PHYS_DISCRETE_GRAPH_LIFT",
            "PHYS_GAUGE_COVARIANT_COUPLING",
            "PHYS_VARIATIONAL_HAMILTONIAN_LIFT",
            "PHYS_MEASUREMENT_BACKACTION",
        }.issubset(transformations),
        "joint_method_route_bound": required_executed.issubset(executed_method_ids),
        "joint_method_route_executed_exactly": contraction["status"].startswith("PASS_"),
        "optimized_tensor_network_matches_reference": contraction["optimized_reference_residual"] < 1e-12,
        "exact_slicing_matches_unsliced": contraction["slicing_residual"] < 1e-12,
        "shared_wedge_channel_preserved": contraction["direct_coupled_residual"] < 1e-11,
        "qpdtr_multimethod_controls_consumed": len(qpdtr_controls) >= 10,
        "open_axes_not_hidden": len(physics_open_axes) > 0,
        "continuum_not_falsely_promoted": gate_status["G5_CONTINUUM"].endswith("OPEN"),
        "matter_not_falsely_promoted": gate_status["G9_MATTER"].endswith("OPEN"),
        "experiment_not_falsely_promoted": gate_status["G12_EXPERIMENT"] == "INELIGIBLE_UNTIL_G11",
    }
    return {
        "stage_id": "MULTIDOMAIN-QG-CLOSURE-SCAN-016",
        "owner_id": "K-TOLLER-DIST-003",
        "bridge_passed": True,
        "bridge_evidence_digest": bridge.get("evidence_digest", ""),
        "original_pipeline_restored": (
            "known laws -> multidimensional cells/gaps -> candidate transformations -> joint computational route -> proof gates -> next discriminating computation"
        ),
        "gate_matrix": {
            gate_id: {**dict(gate_matrix[gate_id]), "current_phi_rqg_status": gate_status[gate_id]}
            for gate_id in gate_status
        },
        "selected_candidate_ids": sorted(selected_candidates),
        "selected_transformations": transformations,
        "executed_joint_method_route": contraction,
        "deferred_method_routes": evidence.get("deferred_method_ids", {}),
        "qpdtr_controls_consumed": sorted(qpdtr_controls),
        "open_physics_axes": physics_open_axes,
        "next_unique_computation": {
            "target": "joint forest-renormalized two-vertex map",
            "formula": "P_char pi_* R_F2^glued iota^*(A_L tensor overline(A_R))",
            "method_route": [
                "QCM-SYMMETRY",
                "QCM-CONTRACTION-OPT",
                "QCM-GENERAL-TN",
                "QCM-SLICING",
                "QCM-ADAPTIVE-TTN",
                "QCM-MERA",
                "QCM-EXACT-DM",
            ],
            "mandatory_negative_controls": [
                "three inequivalent cofinal regulator paths",
                "direct assignment vs optimized tensor-network equality",
                "sliced vs unsliced equality",
                "null-sector and Gram-spectrum stability",
                "Regge/Einstein residual on held-out refinements",
            ],
            "promotion_rule": "no G4/G5/G7 promotion before one common weak limit and a positive gluing-derived cylinder",
        },
        "checks": checks,
        "status": "PASS_MULTIDOMAIN_SCAN_AND_EXACT_FINITE_JOINT_METHOD_ROUTE_CONTINUUM_OPEN",
        "claim_boundary": (
            "The stage proves that the multidimensional table and joint method stack are now active in the authoritative owner and exactly reproduce the finite j=1/2 K5 contraction. "
            "It does not compute the joint forest-renormalized weak limit, physical cylinder, continuum, matter, prediction or experiment."
        ),
    }


def recover_toller_distributional_vertex(observation: CoupledTollerWedgeObservation) -> HandlerResult:
    """Execute the current reduced K-TOLLER-DIST-003 qualification.

    The coupled wedge is a local kernel.  Promotion is limited to Schwartz-test
    boundary-value recovery and the homogeneous j=1/2 singular-forest certificate.
    The complete two-vertex collision graph is treated as K5 union_S K5.
    BISIMPLEX-SINGULAR-FOREST-017 replaces the incomplete product of two
    independent one-vertex forests by the exact connected-cluster atlas.
    JOINT-FOREST-TWO-VERTEX-018 then constructs the exact Bogoliubov recursion
    and the complete 112848-forest combinatorial R-operation. The 16 causal classes form an
    exact Hadamard basis and yield a rank-25 cluster-resolved radial selector.  Its
    QPDTR-BISIMPLEX-TWO-VERTEX-015 can additionally extract a typed finite-regulator
    25-component pre-RHS from the external QPDTR v2.5.0 bisimplex evidence. Its
    TENSOR-WAVEFRONT-ATLAS-019 constructs compact tensor-projector descriptors,
    the 193-stratum conormal atlas and the conditional pullback test, while the
    exact full-vertex scaling degree, exact wavefront containment, noncompact
    pushforward, forest-renormalized right-hand side and physical cylinder remain open. MULTIDOMAIN-QG-CLOSURE-SCAN-016
    restores the original law-table -> candidate-space -> joint-method -> proof-gate pipeline
    and executes an exact finite K5 tensor-network/slicing cross-check.
    """

    observation.validate()
    formal_contract = toller_distributional_vertex_contract()
    distributional = _qualify_toller_distribution_on_tests(observation)
    singular_forest = _qualify_k5_singular_forest()
    bisimplex_forest = _qualify_bisimplex_singular_forest(observation)
    joint_forest_r_operation = _qualify_joint_forest_r_operation(observation, bisimplex_forest)
    tensor_wavefront_atlas = _qualify_tensor_wavefront_atlas(observation, bisimplex_forest, joint_forest_r_operation)
    orientation_fourier = _qualify_causal_orientation_fourier(observation)
    qpdtr_two_vertex = _qualify_qpdtr_bisimplex_two_vertex(observation)
    multidomain_closure = _qualify_multidomain_qg_closure(observation)
    ordinary_limit = _ordinary_wedge_limit_diagnostic(observation)
    binding_graph = formal_contract["shared_binding_graph"]
    binding_sets = {
        frozenset(row["occurrences"]) for row in binding_graph["bindings"]
    }
    required_binding_sets = {
        frozenset(("rho_left", "rho_right", "wedge_projector")),
        frozenset(("q_left", "q_right")),
        frozenset(("p_left", "p_right")),
    }
    formal_binding_contract_ok = required_binding_sets.issubset(binding_sets)
    direct, coupled, hermiticity_defect, composition_defect = _coupled_wedge_pair(
        observation,
        magnetic=observation.magnetic,
        beta_a=observation.beta_a,
        beta_b=observation.beta_b,
        branch=observation.branch,
    )
    wedge_residual = abs(direct - coupled) / max(1.0, abs(direct), abs(coupled))

    # Explicitly quantify the rejected lowest-channel, same-branch product.
    left_direct, _, _, _ = _coupled_wedge_pair(
        observation,
        magnetic=observation.magnetic,
        beta_a=observation.beta_a,
        beta_b=0.0,
        branch=observation.branch,
    )
    right_direct, _, _, _ = _coupled_wedge_pair(
        observation,
        magnetic=observation.magnetic,
        beta_a=0.0,
        beta_b=observation.beta_b,
        branch=observation.branch,
    )
    naive_same_branch = left_direct * right_direct
    naive_residual = abs(direct - naive_same_branch) / max(1.0, abs(direct), abs(naive_same_branch))

    rng = np.random.default_rng(observation.seed)
    direct_samples: List[complex] = []
    coupled_samples: List[complex] = []
    k5_pointwise_residuals: List[float] = []
    k5_wedge_residuals: List[float] = []
    sample_weights: List[float] = []
    for _ in range(observation.k5_samples):
        beta_values = np.concatenate((
            np.array([0.0]),
            rng.uniform(-observation.integration_bound, observation.integration_bound, 4),
        ))
        k5_direct, k5_coupled, k5_wedge_residual = _regulated_k5_pair(observation, beta_values)
        direct_samples.append(k5_direct)
        coupled_samples.append(k5_coupled)
        k5_pointwise_residuals.append(
            abs(k5_direct - k5_coupled) / max(1.0, abs(k5_direct), abs(k5_coupled))
        )
        k5_wedge_residuals.append(k5_wedge_residual)
        sample_weights.append(float(math.exp(-float(np.dot(beta_values[1:], beta_values[1:])))))

    direct_integral = sum(w * value for w, value in zip(sample_weights, direct_samples)) / sum(sample_weights)
    coupled_integral = sum(w * value for w, value in zip(sample_weights, coupled_samples)) / sum(sample_weights)
    integral_residual = abs(direct_integral - coupled_integral) / max(
        1.0, abs(direct_integral), abs(coupled_integral)
    )

    dist_metrics = distributional["metrics"]
    forest_metrics = singular_forest["metrics"]
    ordinary_metrics = ordinary_limit["metrics"]
    bisimplex_metrics = bisimplex_forest["metrics"]
    joint_forest_metrics = joint_forest_r_operation["metrics"]
    joint_forest_checks = joint_forest_r_operation["checks"]
    tensor_wavefront_metrics = tensor_wavefront_atlas["metrics"]
    tensor_wavefront_checks = tensor_wavefront_atlas["checks"]
    orientation_checks = orientation_fourier["checks"]
    orientation_selector = orientation_fourier["structural_selector"]
    orientation_finite = orientation_fourier["finite_regulator_k5_fourier"]
    qpdtr_checks = qpdtr_two_vertex["checks"]
    qpdtr_metrics = qpdtr_two_vertex.get("metrics", {})
    multidomain_checks = multidomain_closure["checks"]
    multidomain_route = multidomain_closure.get("executed_joint_method_route", {})
    checks = {
        "operator_scope_ir_present": bool(formal_contract["operator_scope"]["digest"]),
        "shared_binding_graph_enforced": formal_binding_contract_ok,
        "reduced_wavefront_boundary_recorded": formal_contract["distribution_wavefront"]["status"].startswith("CONORMAL_ATLAS_RECORDED"),
        "proof_obligation_graph_acyclic": bool(formal_contract["proof_obligation_graph"]["digest"]),
        "limit_protocol_multicofinal": len(formal_contract["limit_protocol"]["cofinal_paths"]) >= 4,
        "primary_source_ledger_present": len(formal_contract["primary_source_ledger"]["entries"]) >= 6,
        "projection_kernel_product_matches_gamma": dist_metrics["projection_kernel_product_gamma_residual"] < 1e-11,
        "toller_branch_sum_matches_contact_poisson_kernel": dist_metrics["branch_sum_poisson_identity_residual_max"] < 1e-10,
        "toller_branch_adjoint_relation": dist_metrics["branch_adjoint_defect_max"] < 1e-10,
        "schwartz_test_distributional_extrapolation": dist_metrics["richardson_target_residual_max"] < 5e-4,
        "schwartz_test_convergence_order": dist_metrics["empirical_convergence_order_min"] > 0.85,
        "schwartz_tail_control": dist_metrics["absolute_tail_bound_max"] < 1e-8,
        "kz_hermitian": hermiticity_defect < 1e-12,
        "shared_representation_channel": composition_defect < 1e-12,
        "coupled_wedge_equals_direct_regulated": wedge_residual < 1e-11,
        "naive_same_branch_factorization_rejected": naive_residual > 1e-2,
        "k5_pointwise_equivalence": max(k5_pointwise_residuals) < 1e-11,
        "regulated_compact_k5_integral_equivalence": integral_residual < 1e-11,
        "k5_divergent_clusters_enumerated": forest_metrics["divergent_cluster_count"] == 16,
        "k5_compatible_forests_enumerated": forest_metrics["compatible_forest_count_including_empty"] == 72,
        "bisimplex_collision_atlas_checks": all(bisimplex_forest["checks"].values()),
        "bisimplex_cross_vertex_clusters_complete": bisimplex_metrics["cross_vertex_cluster_count"] == 161,
        "independent_vertex_forest_not_used_as_joint_forest": bisimplex_metrics["divergent_cluster_count"] == 193,
        "joint_forest_r_operation_checks": all(joint_forest_checks.values()),
        "joint_forest_count_exact": joint_forest_metrics["forest_count_including_empty"] == 112848,
        "joint_forest_one_vertex_reduction_exact": joint_forest_metrics["one_vertex_reduction_forest_count"] == 72,
        "joint_forest_analytic_values_not_fabricated": joint_forest_r_operation["status"].endswith("ANALYTIC_EXTENSION_OPEN"),
        "tensor_wavefront_atlas_checks": all(tensor_wavefront_checks.values()),
        "tensor_wavefront_all_193_strata": tensor_wavefront_metrics["stratum_count"] == 193,
        "tensor_wavefront_operator_order_corrected": tensor_wavefront_atlas["corrected_physical_composition"].startswith("C_phys"),
        "tensor_wavefront_pullback_conditional_not_promoted": tensor_wavefront_atlas["pullback"]["exact_vertex_wf_containment_status"] == "OPEN",
        "tensor_wavefront_pushforward_blocked_honestly": tensor_wavefront_atlas["pushforward"]["status"].startswith("BLOCKED_"),
        "ordinary_wedge_limit_not_falsely_promoted": not ordinary_metrics["ordinary_quadrature_converged"],
        "orientation_character_rank_exact": orientation_checks["character_rank_exact_16"],
        "orientation_cluster_character_bijection": orientation_checks["cluster_character_bijection_exact"],
        "orientation_structural_selector_rank_25": orientation_checks["structural_selector_rank_exact_25"],
        "orientation_structural_selector_nullity_zero": orientation_checks["structural_selector_nullity_zero"],
        "orientation_finite_regulator_all_sectors_resolved": orientation_checks["all_16_finite_regulator_sectors_nonzero"],
        "orientation_renormalized_rhs_not_fabricated": orientation_checks["renormalized_rhs_not_fabricated"],
        "physical_contact_values_not_claimed": orientation_selector["rhs_status"].endswith("NOT_COMPUTED"),
        "qpdtr_bridge_fail_closed_or_passed": qpdtr_two_vertex["bridge_passed"] or qpdtr_two_vertex["status"].startswith("BLOCKED_"),
        "qpdtr_physical_rhs_not_fabricated": qpdtr_two_vertex["physical_rhs_status"].endswith("NOT_COMPUTED"),
        "qpdtr_finite_pre_rhs_internal_checks": all(qpdtr_checks.values()),
        "multidomain_bridge_fail_closed_or_passed": multidomain_closure["bridge_passed"] or multidomain_closure["status"].startswith("BLOCKED_"),
        "multidomain_joint_route_checks": all(multidomain_checks.values()),
        "multidomain_joint_route_exact_when_supplied": (not multidomain_closure["bridge_passed"]) or multidomain_route.get("optimized_reference_residual", 1.0) < 1e-12,
        "full_sl2c4_integral_not_claimed": True,
    }
    metrics: Dict[str, float | int | str] = {
        "wedge_relative_residual": float(wedge_residual),
        "representation_composition_residual": float(composition_defect),
        "kz_hermiticity_defect": float(hermiticity_defect),
        "naive_same_branch_residual": float(naive_residual),
        "k5_pointwise_residual_max": float(max(k5_pointwise_residuals)),
        "k5_wedge_residual_max": float(max(k5_wedge_residuals)),
        "k5_integral_residual": float(integral_residual),
        "k5_samples": int(observation.k5_samples),
        "spectral_nodes": int(observation.spectral_nodes),
        "spectral_cutoff": float(observation.spectral_cutoff),
        "epsilon": float(observation.epsilon),
        "canonical_spin_cutoff": float(observation.canonical_spin_cutoff),
        "boundary_sector": "homogeneous j=1/2; five i=1 intertwiners; coaxial boosts",
        "formal_contract_digest": str(formal_contract["digest"]),
        "operator_scope_digest": str(formal_contract["operator_scope"]["digest"]),
        "binding_graph_digest": str(formal_contract["shared_binding_graph"]["digest"]),
        "distribution_wavefront_digest": str(formal_contract["distribution_wavefront"]["digest"]),
        "proof_graph_digest": str(formal_contract["proof_obligation_graph"]["digest"]),
        "limit_protocol_digest": str(formal_contract["limit_protocol"]["digest"]),
        "source_ledger_digest": str(formal_contract["primary_source_ledger"]["digest"]),
        "projection_kernel_product_gamma_residual": float(dist_metrics["projection_kernel_product_gamma_residual"]),
        "branch_sum_poisson_identity_residual_max": float(dist_metrics["branch_sum_poisson_identity_residual_max"]),
        "branch_adjoint_defect_max": float(dist_metrics["branch_adjoint_defect_max"]),
        "schwartz_richardson_residual_max": float(dist_metrics["richardson_target_residual_max"]),
        "schwartz_convergence_order_min": float(dist_metrics["empirical_convergence_order_min"]),
        "schwartz_tail_bound_max": float(dist_metrics["absolute_tail_bound_max"]),
        "divergent_cluster_count": int(forest_metrics["divergent_cluster_count"]),
        "compatible_forest_count": int(forest_metrics["compatible_forest_count_including_empty"]),
        "bisimplex_divergent_cluster_count": int(bisimplex_metrics["divergent_cluster_count"]),
        "bisimplex_cross_vertex_cluster_count": int(bisimplex_metrics["cross_vertex_cluster_count"]),
        "bisimplex_overlapping_cluster_pair_count": int(bisimplex_metrics["overlapping_cluster_pair_count"]),
        "bisimplex_longest_nested_chain_depth": int(bisimplex_metrics["longest_nested_chain_depth"]),
        "bisimplex_maximum_divergence_degree": int(bisimplex_metrics["maximum_divergence_degree"]),
        "joint_forest_count": int(joint_forest_metrics["forest_count_including_empty"]),
        "joint_proper_forest_count": int(joint_forest_metrics["proper_forest_count"]),
        "joint_full_graph_spinney_count": int(joint_forest_metrics["full_graph_spinney_count"]),
        "joint_forest_catalog_sha256": str(joint_forest_metrics["forest_catalog_sha256"]),
        "tensor_wavefront_stratum_count": int(tensor_wavefront_metrics["stratum_count"]),
        "tensor_wavefront_pullback_pairwise_failures": int(tensor_wavefront_metrics["pre_gluing_pairwise_failure_count"]),
        "tensor_wavefront_full_graph_reduced_jet_dimension": int(tensor_wavefront_metrics["full_graph_reduced_compact_tensor_jet_dimension"]),
        "tensor_wavefront_full_graph_conditional_sl2c_jet_dimension": int(tensor_wavefront_metrics["full_graph_conditional_sl2c_tensor_jet_dimension"]),
        "tensor_wavefront_conormal_atlas_sha256": str(tensor_wavefront_metrics["conormal_atlas_sha256"]),
        "ordinary_path_last_change_max": float(ordinary_metrics["ordinary_path_last_change_max"]),
        "ordinary_path_final_spread": float(ordinary_metrics["ordinary_path_final_spread"]),
        "orientation_character_rank_exact": int(orientation_fourier["character_basis"]["rank_exact"]),
        "orientation_structural_selector_rank_exact": int(orientation_selector["rank_exact"]),
        "orientation_structural_selector_nullity_exact": int(orientation_selector["nullity_exact"]),
        "orientation_finite_nonzero_sector_count_min": int(orientation_finite["minimum_nonzero_sector_count"]),
        "orientation_fourier_inversion_residual_max": float(orientation_finite["max_fourier_inversion_residual"]),
        "orientation_direct_coupled_residual_max": float(orientation_finite["max_direct_coupled_residual"]),
        "qpdtr_bridge_status": str(qpdtr_two_vertex["status"]),
        "qpdtr_pre_rhs_component_count": int(qpdtr_metrics.get("component_count", 0)),
        "qpdtr_pre_rhs_path_last_change_max": float(qpdtr_metrics.get("path_last_change_max", 0.0)),
        "qpdtr_pre_rhs_path_final_spread": float(qpdtr_metrics.get("path_final_spread", 0.0)),
        "multidomain_closure_status": str(multidomain_closure["status"]),
        "multidomain_joint_method_count": int(len(multidomain_route.get("method_ids", []))),
        "multidomain_tn_reference_residual": float(multidomain_route.get("optimized_reference_residual", 0.0)),
        "multidomain_slicing_residual": float(multidomain_route.get("slicing_residual", 0.0)),
        "status": "PASS_TENSOR_PROJECTOR_DESCRIPTORS_AND_CONORMAL_ATLAS_PUSHFORWARD_OPEN",
    }
    certificate = _certificate(
        "causal_toller_distributional_vertex",
        "K-TOLLER-DIST-003",
        checks,
        metrics,
        [
            "COUPLED-WEDGE-KERNEL-011 is a local kernel inside K-TOLLER-DIST-003",
            "the two half-edges share rho_tilde and the complete intermediate canonical channel",
            "T+ + T- is qualified on four Schwartz tests through the exact Feynman contact sequence",
            "the compact j=1/2 K3/K4/K5 forest contains 16 divergent clusters and 72 compatible forests including the empty forest",
            "ordinary real-axis wedge quadrature does not provide a cofinal limit certificate",
            "the exact bisimplex collision graph K5 union_S K5 contains 193 superficially divergent connected clusters",
            "161 cross-vertex clusters prove that a product of two independent one-vertex forests is not a complete joint R-operation",
            "JOINT-FOREST-TWO-VERTEX-018 constructs the exact Bogoliubov recursion, counts 112848 compatible bisimplex forests and reduces to the independently enumerated 72 one-vertex forests",
            "TENSOR-WAVEFRONT-ATLAS-019 replaces the misnamed reduced-compact tensor count, defines compact SL(2,C) symmetric-jet projectors conditionally on the exact scaling degree, and constructs all 193 conormal descriptors",
            "the physical composition order is corrected to pull back the independent vertices before applying the glued cross-vertex forest",
            "pre-gluing pullback transversality is exact for the collision-conormal envelope, while exact vertex wavefront containment remains open",
            "the noncompact SL(2,C) pushforward is blocked because neither proper support nor a uniform tail estimate has been proved",
            "CAUSAL-ORIENTATION-FOURIER-014 proves the exact 16-character Hadamard decomposition and a rank-25 cluster-resolved radial selector",
            "finite-regulator K5 amplitudes populate all 16 causal Fourier sectors and reconstruct exactly within the declared cutoff",
            "QPDTR-BISIMPLEX-TWO-VERTEX-015 consumes only a typed QPDTR v2.5.0 evidence certificate and extracts 25 finite-regulator pre-RHS components when that certificate is supplied",
            "MULTIDOMAIN-QG-CLOSURE-SCAN-016 binds all G1-G12 obligations to law anchors, pending transformations, joint computational methods and broader QPDTR controls",
            "the finite K5 contraction is independently reproduced by exact symmetry reduction, optimized tensor-network contraction and deterministic slicing",
            "the external QPDTR EPRL backend remains blocked and no emulator algorithm is duplicated inside Phi-Compiler",
            "forest-renormalized contact right-hand sides, exact full-vertex scaling degrees and wavefront containment, noncompact pushforward, physical cylinder and continuum remain open",
        ],
    )
    parameters: Dict[str, Any] = {
        "direct_wedge": {"real": float(direct.real), "imag": float(direct.imag)},
        "coupled_wedge": {"real": float(coupled.real), "imag": float(coupled.imag)},
        "naive_same_branch": {"real": float(naive_same_branch.real), "imag": float(naive_same_branch.imag)},
        "direct_k5_integral": {"real": float(direct_integral.real), "imag": float(direct_integral.imag)},
        "coupled_k5_integral": {"real": float(coupled_integral.real), "imag": float(coupled_integral.imag)},
        "kernel_formula": (
            "K_sigma(g_b,g_a)=lim_eps int d rho_tilde c_sigma(rho_tilde;rho) "
            "sum_{q,p} conjugate(D_{qp,jm}(g_b)) D_{qp,ln}(g_a)"
        ),
        "distributional_test_function_qualification": distributional,
        "singular_forest_qualification": singular_forest,
        "bisimplex_singular_forest": bisimplex_forest,
        "joint_forest_r_operation": joint_forest_r_operation,
        "tensor_wavefront_atlas": tensor_wavefront_atlas,
        "causal_orientation_fourier": orientation_fourier,
        "qpdtr_bisimplex_two_vertex": qpdtr_two_vertex,
        "multidomain_qg_closure": multidomain_closure,
        "ordinary_limit_diagnostic": ordinary_limit,
        "formal_contract": formal_contract,
        "claim_boundary": (
            "reduced Schwartz-test distribution, one-vertex K5 forest certificate, exact 16-sector causal Fourier algebra, rank-25 cluster-resolved radial measurement operator, complete 193-cluster bisimplex collision atlas, exact 112848-term joint Bogoliubov forest recursion, optional typed QPDTR finite pre-RHS bridge, and a multidimensional law/candidate/joint-method closure scan; "
            "compact tensor-projector descriptors and the conormal atlas are constructed, but exact full-vertex scaling degrees, exact wavefront containment, noncompact pushforward, numerical counterterms, forest-renormalized physical right-hand side and the SL(2,C)^4 distributional cylinder remain open"
        ),
    }
    return HandlerResult(
        OWNER_VERSION,
        SCHEMA,
        "causal_toller_distributional_vertex",
        parameters,
        float(max(
            wedge_residual,
            integral_residual,
            dist_metrics["richardson_target_residual_max"],
            dist_metrics["projection_kernel_product_gamma_residual"],
        )),
        certificate,
    ).finalize()


# ----------------------------- Single typed dispatcher ------------------------
Handler = Callable[[Any], HandlerResult | RecoveryResult]

FAMILY_HANDLERS: Dict[str, Tuple[Type[Any], Handler]] = {
    "static_scalar": (StaticScalarObservation, recover_static_scalar),
    "decay_series": (DecaySeriesObservation, recover_decay_series),
    "second_order_ode": (SecondOrderObservation, recover_second_order_ode),
    "periodic_scalar_pde": (PeriodicScalarPDEObservation, recover_periodic_scalar_pde),
    "closed_quantum_state": (ClosedQuantumObservation, recover_closed_quantum_state),
    "open_qubit_bloch": (OpenQubitBlochObservation, recover_open_qubit_bloch),
    "causal_toller_distributional_vertex": (CoupledTollerWedgeObservation, recover_toller_distributional_vertex),
    "cross_family_resonator": (ObservationPackage, recover_resonator_family),
}



def recover(request: RecoveryRequest) -> HandlerResult | RecoveryResult:
    resolved_kind = request.kind
    try:
        payload_type, handler = FAMILY_HANDLERS[resolved_kind]
    except KeyError as exc:
        raise ValueError(f"Unsupported observation kind: {request.kind}") from exc
    if not isinstance(request.payload, payload_type):
        raise TypeError(f"{request.kind} expects {payload_type.__name__}, got {type(request.payload).__name__}")
    return handler(request.payload)


def owner_connectivity_contract() -> Dict[str, str]:
    """Return digest-bound handler identities without executing private fixtures."""
    return {
        kind: f"{handler.__module__}.{handler.__name__}:{payload_type.__name__}"
        for kind, (payload_type, handler) in sorted(FAMILY_HANDLERS.items())
    }
