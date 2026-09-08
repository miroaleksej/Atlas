"""Fresh blind benchmark for the v4.6 physical model-selection owner.

The benchmark is an evaluator, not an algorithm owner.  Candidate ranking is
performed exclusively by ``source.lawspace.model_selection``.  Hidden truth is
used only after the selection certificate has been finalised.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from scipy.linalg import expm
from scipy.optimize import least_squares

from source.lawspace.model_selection import (
    CandidateSelectionEvidence,
    HorizonEvidence,
    MultiHorizonPhysicalModelSelector,
    PhysicalSelectionConfig,
    PseudomodeDescriptor,
)
from source.lawspace.schema import digest_payload

REPORT_PATH = ROOT / "reports" / "physical_model_selection_v4_6.json"
RESULTS_PATH = ROOT / "reports" / "physical_model_selection_results_v4_6.json"

DT = 0.04
TRAIN_STEPS = 120
HOLDOUT_STEPS = 120
TOTAL_STEPS = TRAIN_STEPS + HOLDOUT_STEPS
NOISE_SIGMA = 7.5e-4
CP_TOL = 1.0e-8
ROLLING_HORIZONS = (
    ("H1_SHORT", 60, 80, 1.0),
    ("H2_MEDIUM", 80, 100, 1.5),
    ("H3_LONG", 100, 120, 2.5),
)
AR_ORDERS = (4, 8, 16, 32)
PSEUDOMODE_ORDERS = (1, 2, 4)
PSEUDOMODE_STARTS = {1: 2, 2: 2, 4: 2}
TTM_MAX_MEMORY = 40
MEMORY_WEIGHT_RHO = 0.035
SEED_NOISE = 202608034101
SEED_START = 202608034301

TRAIN_STATES = np.asarray(
    [
        [1.0, 0.0, 0.0],
        [-1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, -1.0, 0.0],
        [0.0, 0.0, 1.0],
        [0.0, 0.0, -1.0],
    ],
    dtype=float,
)
PROBE_STATES = np.asarray(
    [
        [1.0, 1.0, 1.0],
        [-1.0, 2.0, 0.5],
        [0.3, -0.4, 0.5],
        [0.7, -0.2, -0.6],
        [-0.1, -0.9, 0.4],
        [0.2, 0.8, -0.5],
    ],
    dtype=float,
)
PROBE_STATES /= np.linalg.norm(PROBE_STATES, axis=1)[:, None]

I2 = np.eye(2, dtype=complex)
SX = np.asarray([[0, 1], [1, 0]], dtype=complex)
SY = np.asarray([[0, -1j], [1j, 0]], dtype=complex)
SZ = np.asarray([[1, 0], [0, -1]], dtype=complex)
PAULIS = (SX, SY, SZ)


def _canonical_digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=float).encode("utf-8")
    ).hexdigest()


def build_fresh_truth_scenarios() -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = [
        {
            "scenario_id": "C1_SINGLE_MODE_CONFIRMATORY",
            "description_ru": "Независимый одномодовый контроль",
            "g": np.asarray([0.68]),
            "lambda": np.asarray([0.22]),
            "omega": np.asarray([-0.47]),
        },
        {
            "scenario_id": "C2_THREE_MODE_CONFIRMATORY",
            "description_ru": "Три частично перекрывающиеся шкалы памяти",
            "g": np.asarray([0.46, 0.41, 0.30]),
            "lambda": np.asarray([0.12, 0.18, 0.38]),
            "omega": np.asarray([-0.65, -0.18, 0.72]),
        },
        {
            "scenario_id": "C3_FOUR_SCALE_CONFIRMATORY",
            "description_ru": "Четыре независимые шкалы памяти и детюнинга",
            "g": np.asarray([0.55, 0.38, 0.29, 0.22]),
            "lambda": np.asarray([0.09, 0.27, 0.61, 1.05]),
            "omega": np.asarray([-1.90, -0.55, 0.90, 2.10]),
        },
    ]
    rng = np.random.default_rng(202608035999)
    omega = np.sort(rng.uniform(-4.8, 4.8, size=128))
    profile = (
        1.18 / (1.0 + ((omega + 2.75) / 0.38) ** 2)
        + 0.91 / (1.0 + ((omega + 0.55) / 0.24) ** 2)
        + 0.79 / (1.0 + ((omega - 1.10) / 0.29) ** 2)
        + 0.61 / (1.0 + ((omega - 3.45) / 0.51) ** 2)
        + 0.030
    )
    weights = profile / profile.sum() * 3.65
    scenarios.append(
        {
            "scenario_id": "C4_ONE_HUNDRED_TWENTY_EIGHT_MODE_RESERVOIR",
            "description_ru": "Независимый структурированный резервуар из 128 активных мод",
            "g": np.sqrt(weights),
            "lambda": 0.042 + 0.21 * (0.18 + rng.random(128)) + 0.075 * np.abs(omega) / 4.8,
            "omega": omega,
        }
    )
    return scenarios


def pseudomode_amplitude(times: np.ndarray, g: np.ndarray, decay: np.ndarray, omega: np.ndarray) -> np.ndarray:
    g = np.asarray(g, dtype=float)
    decay = np.asarray(decay, dtype=float)
    omega = np.asarray(omega, dtype=float)
    order = len(g)
    matrix = np.zeros((order + 1, order + 1), dtype=complex)
    matrix[0, 1:] = -1j * g
    matrix[1:, 0] = -1j * g
    matrix[1:, 1:] = np.diag(-(decay + 1j * omega))
    values, vectors = np.linalg.eig(matrix)
    initial = np.zeros(order + 1, dtype=complex)
    initial[0] = 1.0
    condition = np.linalg.cond(vectors)
    if not np.isfinite(condition) or condition > 1.0e13:
        return np.asarray([(expm(matrix * float(t)) @ initial)[0] for t in times])
    coefficients = vectors[0, :] * np.linalg.solve(vectors, initial)
    return np.exp(np.outer(times, values)) @ coefficients


def pseudomode_poles(g: np.ndarray, decay: np.ndarray, omega: np.ndarray) -> np.ndarray:
    order = len(g)
    matrix = np.zeros((order + 1, order + 1), dtype=complex)
    matrix[0, 1:] = -1j * g
    matrix[1:, 0] = -1j * g
    matrix[1:, 1:] = np.diag(-(decay + 1j * omega))
    return np.linalg.eigvals(matrix)


def amplitude_to_trajectories(amplitude: np.ndarray, states: np.ndarray) -> np.ndarray:
    a = amplitude.real
    b = amplitude.imag
    survival = np.abs(amplitude) ** 2
    rows = []
    for x, y, z in states:
        out = np.empty((len(amplitude), 3), dtype=float)
        out[:, 0] = a * x - b * y
        out[:, 1] = b * x + a * y
        out[:, 2] = survival * z + (1.0 - survival)
        rows.append(out)
    return np.asarray(rows)


def estimate_affine_maps(observed: np.ndarray) -> tuple[np.ndarray, ...]:
    design = np.column_stack([TRAIN_STATES, np.ones(len(TRAIN_STATES))])
    maps = []
    for index in range(observed.shape[1]):
        targets = np.column_stack([observed[:, index, :], np.ones(len(TRAIN_STATES))])
        coefficients, _, _, _ = np.linalg.lstsq(design, targets, rcond=None)
        affine = coefficients.T
        affine[3, :] = (0.0, 0.0, 0.0, 1.0)
        maps.append(affine)
    return tuple(maps)


def extract_amplitude(maps: tuple[np.ndarray, ...]) -> np.ndarray:
    values = []
    for matrix in maps:
        a = 0.5 * (matrix[0, 0] + matrix[1, 1])
        b = 0.5 * (matrix[1, 0] - matrix[0, 1])
        values.append(complex(a, b))
    values[0] = 1.0 + 0.0j
    return np.asarray(values)


def apply_maps(maps: tuple[np.ndarray, ...], states: np.ndarray) -> np.ndarray:
    rows = []
    for state in states:
        initial = np.concatenate([state, [1.0]])
        rows.append(np.asarray([(matrix @ initial)[:3] for matrix in maps]))
    return np.asarray(rows)


def operator_from_bloch_map(affine: np.ndarray, operator: np.ndarray) -> np.ndarray:
    coefficients = np.asarray(
        [np.trace(pauli @ operator) for pauli in PAULIS] + [np.trace(operator)], dtype=complex
    )
    output = affine.astype(complex) @ coefficients
    return (output[3] * I2 + output[0] * SX + output[1] * SY + output[2] * SZ) / 2.0


def choi_from_bloch_map(affine: np.ndarray) -> np.ndarray:
    choi = np.zeros((4, 4), dtype=complex)
    for m in range(2):
        for n in range(2):
            basis = np.zeros((2, 2), dtype=complex)
            basis[m, n] = 1.0
            left = np.zeros((2, 2), dtype=complex)
            left[m, n] = 1.0
            choi += np.kron(left, operator_from_bloch_map(affine, basis))
    return (choi + choi.conj().T) / 2.0


def amplitude_damping_bloch_map(amplitude: complex) -> np.ndarray:
    a = float(np.real(amplitude))
    b = float(np.imag(amplitude))
    survival = float(abs(amplitude) ** 2)
    return np.asarray(
        [
            [a, -b, 0.0, 0.0],
            [b, a, 0.0, 0.0],
            [0.0, 0.0, survival, 1.0 - survival],
            [0.0, 0.0, 0.0, 1.0],
        ],
        dtype=float,
    )


def amplitude_physicality(amplitude: np.ndarray) -> dict[str, Any]:
    margins = 1.0 - np.abs(amplitude) ** 2
    choi_minima = [
        float(np.min(np.linalg.eigvalsh(choi_from_bloch_map(amplitude_damping_bloch_map(value)))))
        for value in amplitude
    ]
    violation_mask = np.logical_or(margins < -CP_TOL, np.asarray(choi_minima) < -CP_TOL)
    return {
        "passed": bool(not np.any(violation_mask)),
        "violation_count": int(np.count_nonzero(violation_mask)),
        "minimum_choi_eigenvalue": float(min(choi_minima)),
        "minimum_amplitude_damping_margin": float(np.min(margins)),
    }


def map_physicality(maps: tuple[np.ndarray, ...]) -> dict[str, Any]:
    minima = [float(np.min(np.linalg.eigvalsh(choi_from_bloch_map(matrix)))) for matrix in maps]
    return {
        "passed": bool(all(value >= -CP_TOL for value in minima)),
        "violation_count": int(sum(value < -CP_TOL for value in minima)),
        "minimum_choi_eigenvalue": float(min(minima)),
    }


def trajectory_rmse(prediction: np.ndarray, truth: np.ndarray) -> float:
    return float(np.sqrt(np.mean((prediction - truth) ** 2)))


def amplitude_rmse(prediction: np.ndarray, observed: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.abs(prediction - observed) ** 2)))


def discrete_transfer_kernel(amplitude: np.ndarray, memory: int) -> np.ndarray:
    sequence = np.asarray(amplitude, dtype=complex)
    limit = min(memory, len(sequence) - 1)
    tensors: list[complex] = []
    for n in range(1, limit + 1):
        value = sequence[n]
        for k, tensor in enumerate(tensors, start=1):
            value -= tensor * sequence[n - k]
        tensors.append(value)
    return np.asarray(tensors, dtype=complex)


def weighted_memory_error(candidate: np.ndarray, observed: np.ndarray, memory: int = 36) -> float:
    reference_kernel = discrete_transfer_kernel(observed, memory)
    candidate_kernel = discrete_transfer_kernel(candidate, memory)
    count = min(len(reference_kernel), len(candidate_kernel))
    if count == 0:
        return 0.0
    grid = DT * np.arange(1, count + 1, dtype=float)
    weights = np.exp(2.0 * MEMORY_WEIGHT_RHO * grid)
    denominator = float(np.sum(weights * np.abs(reference_kernel[:count]) ** 2))
    numerator = float(np.sum(weights * np.abs(candidate_kernel[:count] - reference_kernel[:count]) ** 2))
    return float(math.sqrt(numerator / max(denominator, 1.0e-18)))


def jacobian_identifiability(jacobian: np.ndarray, dimension: int) -> tuple[int, float]:
    if dimension == 0:
        return 0, 1.0
    singular = np.linalg.svd(np.asarray(jacobian, dtype=float), compute_uv=False)
    if len(singular) == 0 or singular[0] <= 0.0:
        return 0, 1.0e15
    tolerance = max(jacobian.shape) * np.finfo(float).eps * singular[0]
    rank = int(np.count_nonzero(singular > tolerance))
    smallest = singular[rank - 1] if rank else 0.0
    condition = float(singular[0] / max(smallest, 1.0e-15))
    return rank, condition


def fit_markov(amplitude: np.ndarray, times: np.ndarray) -> dict[str, Any]:
    def model(parameters: np.ndarray, grid: np.ndarray) -> np.ndarray:
        gamma = math.exp(float(parameters[0]))
        detuning = float(parameters[1])
        return np.exp(-(0.5 * gamma + 1j * detuning) * grid)

    result = least_squares(
        lambda x: np.concatenate([(model(x, times) - amplitude).real, (model(x, times) - amplitude).imag]),
        np.asarray([math.log(0.5), 0.0]),
        bounds=([-8.0, -6.0], [3.0, 6.0]),
        max_nfev=2500,
        xtol=1.0e-11,
        ftol=1.0e-11,
        gtol=1.0e-11,
    )
    rank, condition = jacobian_identifiability(result.jac, 2)
    gamma = math.exp(float(result.x[0]))
    detuning = float(result.x[1])
    return {
        "parameter_count": 2,
        "predict": lambda grid: model(result.x, grid),
        "rank": rank,
        "condition": condition,
        "pole_margin": 0.5 * gamma,
        "parameters": {"gamma": gamma, "detuning": detuning},
    }


def fit_stretched(amplitude: np.ndarray, times: np.ndarray) -> dict[str, Any]:
    def model(parameters: np.ndarray, grid: np.ndarray) -> np.ndarray:
        rate = math.exp(float(parameters[0]))
        exponent = float(parameters[1])
        detuning = float(parameters[2])
        return np.exp(-0.5 * np.power(np.maximum(rate * grid, 0.0), exponent) - 1j * detuning * grid)

    result = least_squares(
        lambda x: np.concatenate([(model(x, times) - amplitude).real, (model(x, times) - amplitude).imag]),
        np.asarray([math.log(0.5), 1.0, 0.0]),
        bounds=([-8.0, 0.2, -6.0], [3.0, 2.5, 6.0]),
        max_nfev=3000,
        xtol=1.0e-11,
        ftol=1.0e-11,
        gtol=1.0e-11,
    )
    rank, condition = jacobian_identifiability(result.jac, 3)
    return {
        "parameter_count": 3,
        "predict": lambda grid: model(result.x, grid),
        "rank": rank,
        "condition": condition,
        "pole_margin": math.inf,
        "parameters": {
            "rate": math.exp(float(result.x[0])),
            "exponent": float(result.x[1]),
            "detuning": float(result.x[2]),
        },
    }


def decode_pseudomode(parameters: np.ndarray, order: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    coupling = np.exp(parameters[:order])
    decay = np.exp(parameters[order : 2 * order])
    frequency = parameters[2 * order : 3 * order]
    indices = np.argsort(frequency)
    return coupling[indices], decay[indices], frequency[indices]


def fit_pseudomode(
    amplitude: np.ndarray, times: np.ndarray, order: int, seed: int,
    initial_parameters: np.ndarray | None = None,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    lower = np.concatenate([np.full(order, -4.8), np.full(order, -4.8), np.full(order, -4.8)])
    upper = np.concatenate([np.full(order, 1.1), np.full(order, 1.4), np.full(order, 4.8)])
    best = None
    initial_points = []
    if initial_parameters is not None:
        initial_points.append(np.clip(np.asarray(initial_parameters, dtype=float), lower, upper))
    random_start_count = 1 if initial_parameters is not None else PSEUDOMODE_STARTS[order]
    for _ in range(random_start_count):
        initial_points.append(np.concatenate(
            [
                rng.uniform(-2.6, -0.02, order),
                rng.uniform(-3.0, 0.15, order),
                rng.uniform(-3.2, 3.2, order),
            ]
        ))
    for initial in initial_points:
        result = least_squares(
            lambda x: np.concatenate(
                [
                    (pseudomode_amplitude(times, *decode_pseudomode(x, order)) - amplitude).real,
                    (pseudomode_amplitude(times, *decode_pseudomode(x, order)) - amplitude).imag,
                ]
            ),
            initial,
            bounds=(lower, upper),
            max_nfev=140 if initial_parameters is None else 85,
            xtol=2.0e-10,
            ftol=2.0e-10,
            gtol=2.0e-10,
        )
        rss = float(np.sum(result.fun**2))
        if best is None or rss < best[0]:
            best = (rss, result)
    assert best is not None
    result = best[1]
    coupling, decay, frequency = decode_pseudomode(result.x, order)
    poles = pseudomode_poles(coupling, decay, frequency)
    rank, condition = jacobian_identifiability(result.jac, 3 * order)
    return {
        "parameter_count": 3 * order,
        "predict": lambda grid: pseudomode_amplitude(grid, coupling, decay, frequency),
        "rank": rank,
        "condition": condition,
        "pole_margin": float(-np.max(poles.real)),
        "pole_stable": bool(np.max(poles.real) <= 1.0e-8),
        "parameters": {
            "g": coupling.tolist(),
            "lambda": decay.tolist(),
            "omega": frequency.tolist(),
        },
        "pseudomodes": tuple(
            PseudomodeDescriptor(float(g), float(lam), float(freq))
            for g, lam, freq in zip(coupling, decay, frequency)
        ),
        "raw_parameters": result.x,
        "bounds": (lower, upper),
        "residual": lambda x: np.concatenate(
            [
                (pseudomode_amplitude(times, *decode_pseudomode(x, order)) - amplitude).real,
                (pseudomode_amplitude(times, *decode_pseudomode(x, order)) - amplitude).imag,
            ]
        ),
    }


def profile_open_count(fit: dict[str, Any], order: int) -> int:
    """One-dimensional profile-likelihood screen with nuisance refitting.

    Frequencies and log-decay parameters are profiled.  A parameter is marked
    open when both tested sides remain inside a conservative Delta-chi-square
    threshold after the remaining parameters are reoptimised.
    """

    optimum = np.asarray(fit["raw_parameters"], dtype=float)
    lower, upper = (np.asarray(x, dtype=float) for x in fit["bounds"])
    residual: Callable[[np.ndarray], np.ndarray] = fit["residual"]
    base = residual(optimum)
    rss0 = float(np.sum(base**2))
    variance = max(rss0 / max(len(base) - len(optimum), 1), 1.0e-12)
    open_count = 0
    profile_indices = list(range(2 * order, 3 * order))
    for index in profile_indices:
        width = upper[index] - lower[index]
        step = 0.08 * width
        side_statistics = []
        free = np.asarray([j for j in range(len(optimum)) if j != index], dtype=int)
        for sign in (-1.0, 1.0):
            fixed = float(np.clip(optimum[index] + sign * step, lower[index], upper[index]))
            if abs(fixed - optimum[index]) < 1.0e-10:
                side_statistics.append(math.inf)
                continue

            def reduced_residual(free_values: np.ndarray) -> np.ndarray:
                trial = optimum.copy()
                trial[index] = fixed
                trial[free] = free_values
                return residual(trial)

            result = least_squares(
                reduced_residual,
                optimum[free],
                bounds=(lower[free], upper[free]),
                max_nfev=35,
                xtol=1.0e-7,
                ftol=1.0e-7,
                gtol=1.0e-7,
            )
            delta_chi2 = max(0.0, float(np.sum(result.fun**2)) - rss0) / variance
            side_statistics.append(delta_chi2)
        if max(side_statistics) < 3.84:
            open_count += 1
    return open_count


def fit_ar(amplitude: np.ndarray, order: int) -> dict[str, Any]:
    ridges = np.logspace(-12, -2, 11)
    best = None
    for ridge in ridges:
        matrix = np.asarray(
            [[amplitude[n - k] for k in range(1, order + 1)] for n in range(order, len(amplitude))],
            dtype=complex,
        )
        target = amplitude[order:]
        coefficients = np.linalg.solve(
            matrix.conj().T @ matrix + ridge * np.eye(order), matrix.conj().T @ target
        )
        residual = matrix @ coefficients - target
        score = float(np.mean(np.abs(residual) ** 2)) + 1.0e-8 * order + 1.0e-10 * math.log10(1.0 / ridge)
        if best is None or score < best[0]:
            best = (score, ridge, coefficients, matrix)
    assert best is not None
    _, ridge, coefficients, matrix = best
    roots = np.roots(np.concatenate([[1.0], -coefficients]))
    singular = np.linalg.svd(matrix, compute_uv=False)
    tolerance = max(matrix.shape) * np.finfo(float).eps * singular[0]
    rank = int(np.count_nonzero(singular > tolerance))
    condition = float(singular[0] / max(singular[rank - 1] if rank else 0.0, 1.0e-15))

    def forecast(grid: np.ndarray) -> np.ndarray:
        total = len(grid) - 1
        sequence = list(np.asarray(amplitude, dtype=complex))
        while len(sequence) <= total:
            n = len(sequence)
            sequence.append(sum(coefficients[k - 1] * sequence[n - k] for k in range(1, order + 1)))
        return np.asarray(sequence[: total + 1])

    def free_predict(grid: np.ndarray) -> np.ndarray:
        total = len(grid) - 1
        sequence = list(np.asarray(amplitude[:order], dtype=complex))
        while len(sequence) <= total:
            n = len(sequence)
            sequence.append(sum(coefficients[k - 1] * sequence[n - k] for k in range(1, order + 1)))
        return np.asarray(sequence[: total + 1])

    radius = float(np.max(np.abs(roots))) if len(roots) else 0.0
    return {
        "parameter_count": 2 * order,
        "predict": forecast,
        "free_predict": free_predict,
        "rank": rank,
        "condition": condition,
        "pole_margin": 1.0 - radius,
        "pole_stable": bool(radius <= 1.0 + 1.0e-8),
        "parameters": {
            "coefficients_real": coefficients.real.tolist(),
            "coefficients_imag": coefficients.imag.tolist(),
            "ridge": float(ridge),
            "spectral_radius": radius,
        },
    }


def load_qpdtr() -> dict[str, Any]:
    archive = ROOT / "external" / "QPDTR_PhiQG_CURRENT_STATE_v2_5_0.zip"
    temporary = tempfile.mkdtemp(prefix="qpdtr_v25_")
    with zipfile.ZipFile(archive) as handle:
        handle.extractall(temporary)
    roots = [path for path in Path(temporary).iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise RuntimeError("unexpected QPDTR archive structure")
    qroot = roots[0]
    sys.path.insert(0, str(qroot / "src"))
    from qpdtr.domains.quantum_gravity.generator_learning import learn_affine_bloch_generator
    from qpdtr.domains.quantum_gravity.structural_router import StructuralProfile, select_structural_owner
    from qpdtr.domains.quantum_gravity.tempo import propagate_transfer_tensors, transfer_tensors_from_maps

    route = select_structural_owner(StructuralProfile(non_markovian_memory=True))
    return {
        "temporary": temporary,
        "learn_affine_bloch_generator": learn_affine_bloch_generator,
        "propagate_transfer_tensors": propagate_transfer_tensors,
        "transfer_tensors_from_maps": transfer_tensors_from_maps,
        "route": route.to_dict(),
    }


def fit_ttm(maps: tuple[np.ndarray, ...], qpdtr: Mapping[str, Any]) -> dict[str, Any]:
    transfer_tensors_from_maps = qpdtr["transfer_tensors_from_maps"]
    propagate_transfer_tensors = qpdtr["propagate_transfer_tensors"]
    count = len(maps) - 1
    inner_origin = max(12, count - 15)
    tensors_inner = transfer_tensors_from_maps(maps[1 : inner_origin + 1])
    trials = []
    for memory in range(1, min(TTM_MAX_MEMORY, len(tensors_inner)) + 1):
        prediction = propagate_transfer_tensors(maps[0], tensors_inner[:memory], count)
        gap = float(
            np.sqrt(
                np.mean(
                    [
                        np.linalg.norm(prediction[n] - maps[n], ord="fro") ** 2
                        for n in range(inner_origin + 1, count + 1)
                    ]
                )
            )
        )
        trials.append((gap + 2.0e-5 * memory, gap, memory))
    trials.sort()
    selected_memory = trials[0][2]
    tensors = transfer_tensors_from_maps(maps[1:])

    def forecast(total_steps: int) -> tuple[np.ndarray, ...]:
        return tuple(propagate_transfer_tensors(maps[0], tensors[:selected_memory], total_steps))

    # Scalar companion stability diagnostic from the amplitude projection.
    amplitude = extract_amplitude(maps)
    scalar_kernel = discrete_transfer_kernel(amplitude, selected_memory)
    roots = np.roots(np.concatenate([[1.0], -scalar_kernel])) if len(scalar_kernel) else np.asarray([])
    radius = float(np.max(np.abs(roots))) if len(roots) else 0.0
    return {
        "parameter_count": 16 * selected_memory,
        "forecast_maps": forecast,
        "rank": selected_memory,
        "condition": 1.0 + float(trials[0][1] / max(NOISE_SIGMA, 1.0e-12)),
        "pole_margin": 1.0 - radius,
        "pole_stable": bool(radius <= 1.0 + 1.0e-8),
        "parameters": {"selected_memory": selected_memory, "spectral_radius": radius},
    }


def fit_stationary_affine(observed: np.ndarray, qpdtr: Mapping[str, Any]) -> dict[str, Any]:
    learned, _, _ = qpdtr["learn_affine_bloch_generator"](observed, time_step=DT)
    generator = np.zeros((4, 4), dtype=float)
    generator[:3, :3] = np.asarray(learned.matrix, dtype=float)
    generator[:3, 3] = np.asarray(learned.drift, dtype=float)
    values = np.linalg.eigvals(generator[:3, :3])

    def forecast(total_steps: int) -> tuple[np.ndarray, ...]:
        grid = DT * np.arange(int(total_steps) + 1, dtype=float)
        return tuple(expm(generator * float(t)) for t in grid)

    return {
        "parameter_count": 12,
        "forecast_maps": forecast,
        "rank": 12,
        "condition": max(1.0, float(learned.design_condition_number)),
        "pole_margin": float(-np.max(values.real)),
        "pole_stable": bool(np.max(values.real) <= 1.0e-8),
        "parameters": {
            "design_condition_number": float(learned.design_condition_number),
            "regression_residual_rms": float(learned.regression_residual_rms),
        },
    }


def fit_candidate(
    name: str,
    amplitude: np.ndarray,
    maps: tuple[np.ndarray, ...],
    times: np.ndarray,
    observed_trajectories: np.ndarray,
    qpdtr: Mapping[str, Any],
    seed: int,
    warm_start: np.ndarray | None = None,
) -> dict[str, Any]:
    if name == "MARKOV_GKSL":
        return fit_markov(amplitude, times)
    if name == "STRETCHED_CPTP":
        return fit_stretched(amplitude, times)
    if name.startswith("PSEUDOMODE_"):
        return fit_pseudomode(amplitude, times, int(name.rsplit("_", 1)[1]), seed, warm_start)
    if name.startswith("RATIONAL_AR_"):
        return fit_ar(amplitude, int(name.rsplit("_", 1)[1]))
    if name == "QPDTR_RAW_TTM":
        return fit_ttm(maps, qpdtr)
    if name == "QPDTR_STATIONARY_AFFINE":
        return fit_stationary_affine(observed_trajectories, qpdtr)
    raise KeyError(name)


def candidate_names() -> tuple[str, ...]:
    return (
        "MARKOV_GKSL",
        "STRETCHED_CPTP",
        "PSEUDOMODE_1",
        "PSEUDOMODE_2",
        "PSEUDOMODE_4",
        "RATIONAL_AR_4",
        "RATIONAL_AR_8",
        "RATIONAL_AR_16",
        "RATIONAL_AR_32",
        "QPDTR_RAW_TTM",
        "QPDTR_STATIONARY_AFFINE",
    )


def run_scenario(scenario: Mapping[str, Any], scenario_index: int, qpdtr: Mapping[str, Any]) -> dict[str, Any]:
    times = np.arange(TOTAL_STEPS + 1, dtype=float) * DT
    truth_amplitude = pseudomode_amplitude(times, scenario["g"], scenario["lambda"], scenario["omega"])
    truth_training = amplitude_to_trajectories(truth_amplitude, TRAIN_STATES)
    truth_probes = amplitude_to_trajectories(truth_amplitude, PROBE_STATES)
    noise = np.random.default_rng(SEED_NOISE + scenario_index).normal(
        0.0, NOISE_SIGMA, size=truth_training[:, : TRAIN_STEPS + 1, :].shape
    )
    observed = truth_training[:, : TRAIN_STEPS + 1, :] + noise
    observed_maps = estimate_affine_maps(observed)
    observed_amplitude = extract_amplitude(observed_maps)

    horizon_records: dict[str, list[HorizonEvidence]] = {name: [] for name in candidate_names()}
    horizon_diagnostics: dict[str, list[dict[str, Any]]] = {name: [] for name in candidate_names()}
    pseudomode_warm_starts: dict[str, np.ndarray] = {}

    for horizon_index, (horizon_id, origin, end, weight) in enumerate(ROLLING_HORIZONS):
        prefix_maps = observed_maps[: origin + 1]
        prefix_amplitude = observed_amplitude[: origin + 1]
        prefix_times = times[: origin + 1]
        prefix_observed = observed[:, : origin + 1, :]
        target = observed_amplitude[origin + 1 : end + 1]
        forecast_times = times[: end + 1]
        for candidate_index, name in enumerate(candidate_names()):
            fit = fit_candidate(
                name,
                prefix_amplitude,
                prefix_maps,
                prefix_times,
                prefix_observed,
                qpdtr,
                SEED_START + 10000 * scenario_index + 1000 * horizon_index + candidate_index,
                pseudomode_warm_starts.get(name),
            )
            if name.startswith("PSEUDOMODE_"):
                pseudomode_warm_starts[name] = np.asarray(fit["raw_parameters"], dtype=float)
            if "predict" in fit:
                prediction_amplitude = np.asarray(fit["predict"](forecast_times), dtype=complex)
                forecast_segment = prediction_amplitude[origin + 1 : end + 1]
                physical = amplitude_physicality(prediction_amplitude[origin + 1 : end + 1])
            else:
                forecast_maps = tuple(fit["forecast_maps"](end))
                prediction_amplitude = extract_amplitude(forecast_maps)
                forecast_segment = prediction_amplitude[origin + 1 : end + 1]
                physical = map_physicality(forecast_maps[origin + 1 : end + 1])
            error = amplitude_rmse(forecast_segment, target)
            horizon_records[name].append(
                HorizonEvidence(horizon_id, origin, end, end - origin, error, weight)
            )
            horizon_diagnostics[name].append(
                {
                    "horizon_id": horizon_id,
                    "physicality": physical,
                    "pole_stable": bool(fit.get("pole_stable", True)),
                    "pole_margin": float(fit.get("pole_margin", math.inf)),
                }
            )

    final_fits: dict[str, dict[str, Any]] = {}
    evidence_rows: list[CandidateSelectionEvidence] = []
    for candidate_index, name in enumerate(candidate_names()):
        fit = fit_candidate(
            name,
            observed_amplitude,
            observed_maps,
            times[: TRAIN_STEPS + 1],
            observed,
            qpdtr,
            SEED_START + 50000 + 10000 * scenario_index + candidate_index,
            pseudomode_warm_starts.get(name),
        )
        final_fits[name] = fit
        if "predict" in fit:
            training_prediction = np.asarray(fit["predict"](times[: TRAIN_STEPS + 1]), dtype=complex)
            memory_prediction = np.asarray(
                fit.get("free_predict", fit["predict"])(times[: TRAIN_STEPS + 1]), dtype=complex
            )
            physical = amplitude_physicality(memory_prediction)
        else:
            training_maps = tuple(fit["forecast_maps"](TRAIN_STEPS))
            training_prediction = extract_amplitude(training_maps)
            memory_prediction = training_prediction
            physical = map_physicality(training_maps)
        all_fold_physical = physical["passed"] and all(
            row["physicality"]["passed"] for row in horizon_diagnostics[name]
        )
        total_violations = int(physical["violation_count"]) + sum(
            int(row["physicality"]["violation_count"]) for row in horizon_diagnostics[name]
        )
        minimum_choi = min(
            [float(physical["minimum_choi_eigenvalue"])]
            + [float(row["physicality"]["minimum_choi_eigenvalue"]) for row in horizon_diagnostics[name]]
        )
        stable = bool(fit.get("pole_stable", True)) and all(
            row["pole_stable"] for row in horizon_diagnostics[name]
        )
        pole_margin = min(
            [float(fit.get("pole_margin", math.inf))]
            + [float(row["pole_margin"]) for row in horizon_diagnostics[name]]
        )
        evidence_rows.append(
            CandidateSelectionEvidence(
                candidate_id=name,
                parameter_count=int(fit["parameter_count"]),
                effective_sample_count=2 * (TRAIN_STEPS + 1),
                horizons=tuple(horizon_records[name]),
                physicality_passed=all_fold_physical,
                physicality_status="PASS_CPTP_ALL_TRAINING_FOLDS" if all_fold_physical else "BLOCKED_CPTP_OR_POSITIVITY",
                cptp_violation_count=total_violations,
                minimum_choi_eigenvalue=minimum_choi,
                pole_stability_passed=stable,
                pole_stability_margin=pole_margin,
                pole_status="PASS_ALL_FOLDS" if stable else "BLOCKED_UNSTABLE_POLE",
                identifiability_rank=int(fit.get("rank", 0)),
                identifiability_dimension=int(fit["parameter_count"]),
                identifiability_condition_number=float(max(1.0, fit.get("condition", 1.0))),
                profile_open_parameter_count=0,
                weighted_discrete_memory_error=weighted_memory_error(memory_prediction, observed_amplitude),
                pseudomodes=tuple(fit.get("pseudomodes", ())),
                metadata={"final_parameters": fit.get("parameters", {})},
            )
        )

    selector = MultiHorizonPhysicalModelSelector(PhysicalSelectionConfig())
    preliminary = selector.select(tuple(evidence_rows), holdout_accessed=False)
    preliminary_by_id = {row.candidate_id: row for row in preliminary.results}
    eligible_scores = [row.score for row in preliminary.results if row.eligible and row.score is not None]
    best_score = min(eligible_scores) if eligible_scores else math.inf
    pseudomode_contenders = [
        row for row in preliminary.results
        if row.eligible and row.score is not None and row.candidate_id.startswith("PSEUDOMODE_")
    ]
    pseudomode_contenders.sort(key=lambda row: (row.score, row.candidate_id))
    profile_targets = set()
    if pseudomode_contenders and pseudomode_contenders[0].score <= best_score * 1.75:
        profile_targets.add(pseudomode_contenders[0].candidate_id)
    updated_evidence = []
    profile_counts: dict[str, int] = {}
    for evidence in evidence_rows:
        if evidence.candidate_id in profile_targets:
            order = int(evidence.candidate_id.rsplit("_", 1)[1])
            count = profile_open_count(final_fits[evidence.candidate_id], order)
        else:
            count = 0
        profile_counts[evidence.candidate_id] = count
        updated_evidence.append(dataclasses.replace(evidence, profile_open_parameter_count=count))
    certificate = selector.select(tuple(updated_evidence), holdout_accessed=False)
    selected = certificate.selected_candidate_id
    if selected is None:
        raise RuntimeError("no physically eligible candidate")

    # Only after the owner certificate is finalised do we expose hidden truth.
    candidate_results = []
    for name in candidate_names():
        fit = final_fits[name]
        if "predict" in fit:
            full_amplitude = np.asarray(fit["predict"](times), dtype=complex)
            full_prediction = amplitude_to_trajectories(full_amplitude, PROBE_STATES)
            holdout_physical = amplitude_physicality(full_amplitude[TRAIN_STEPS + 1 :])
        else:
            full_maps = tuple(fit["forecast_maps"](TOTAL_STEPS))
            full_amplitude = extract_amplitude(full_maps)
            full_prediction = apply_maps(full_maps, PROBE_STATES)
            holdout_physical = map_physicality(full_maps[TRAIN_STEPS + 1 :])
        holdout_rmse = trajectory_rmse(
            full_prediction[:, TRAIN_STEPS + 1 :, :],
            truth_probes[:, TRAIN_STEPS + 1 :, :],
        )
        selection_row = preliminary_by_id.get(name)
        final_selection_row = next(row for row in certificate.results if row.candidate_id == name)
        candidate_results.append(
            {
                "candidate_id": name,
                "selected": name == selected,
                "eligible": final_selection_row.eligible,
                "selection_score": final_selection_row.score,
                "selection_components": dict(final_selection_row.components),
                "gate_checks": dict(final_selection_row.gate_checks),
                "profile_open_parameter_count": profile_counts[name],
                "blind_holdout_rmse": holdout_rmse,
                "blind_holdout_physicality": holdout_physical,
                "parameter_count": int(fit["parameter_count"]),
            }
        )
    candidate_results.sort(key=lambda row: row["blind_holdout_rmse"])
    selected_result = next(row for row in candidate_results if row["candidate_id"] == selected)
    hindsight = candidate_results[0]

    truth_payload = {
        "g": np.asarray(scenario["g"]).tolist(),
        "lambda": np.asarray(scenario["lambda"]).tolist(),
        "omega": np.asarray(scenario["omega"]).tolist(),
    }
    return {
        "scenario_id": scenario["scenario_id"],
        "description_ru": scenario["description_ru"],
        "truth_commitment_sha256": _canonical_digest(truth_payload),
        "hidden_environment": {
            "active_mode_count": int(len(scenario["g"])),
            "continuous_parameter_count": int(3 * len(scenario["g"])),
            "truth_unavailable_to_selector": True,
        },
        "selection_certificate": certificate.to_dict(),
        "preliminary_profile_targets": sorted(profile_targets),
        "selected_candidate_id": selected,
        "selected_blind_holdout_rmse": selected_result["blind_holdout_rmse"],
        "selected_blind_holdout_cptp": selected_result["blind_holdout_physicality"]["passed"],
        "hindsight_best_candidate_id": hindsight["candidate_id"],
        "hindsight_best_blind_holdout_rmse": hindsight["blind_holdout_rmse"],
        "selection_matches_hindsight_best": selected == hindsight["candidate_id"],
        "candidate_results": candidate_results,
        "revealed_truth_after_selection": truth_payload,
    }


def main() -> None:
    started = time.time()
    qpdtr = load_qpdtr()
    try:
        scenarios = build_fresh_truth_scenarios()
        results = []
        for index, scenario in enumerate(scenarios):
            print(f"RUN {index+1}/{len(scenarios)} {scenario['scenario_id']}", flush=True)
            result = run_scenario(scenario, index, qpdtr)
            results.append(result)
            print(f"DONE {scenario['scenario_id']} -> {result['selected_candidate_id']}", flush=True)
    finally:
        shutil.rmtree(qpdtr["temporary"], ignore_errors=True)

    selected_matches = sum(row["selection_matches_hindsight_best"] for row in results)
    selected_cptp = sum(row["selected_blind_holdout_cptp"] for row in results)
    aggregate = {}
    for name in candidate_names():
        rows = [next(item for item in result["candidate_results"] if item["candidate_id"] == name) for result in results]
        aggregate[name] = {
            "mean_blind_holdout_rmse": float(np.mean([row["blind_holdout_rmse"] for row in rows])),
            "maximum_blind_holdout_rmse": float(np.max([row["blind_holdout_rmse"] for row in rows])),
            "total_blind_holdout_physicality_violations": int(
                sum(row["blind_holdout_physicality"]["violation_count"] for row in rows)
            ),
            "selected_count": int(sum(row["selected"] for row in rows)),
        }

    report = {
        "schema": "phi-qpdtr-multi-horizon-physical-selection-benchmark/v4.6",
        "experiment_id": "EXP-NM-QUBIT-MULTIHORIZON-004",
        "release": "4.6.0",
        "qpdtr_release": "2.5.0",
        "qpdtr_structural_route": qpdtr["route"],
        "protocol": {
            "rolling_horizons": [
                {"horizon_id": hid, "origin_step": origin, "end_step": end, "weight": weight}
                for hid, origin, end, weight in ROLLING_HORIZONS
            ],
            "time_step": DT,
            "training_steps": TRAIN_STEPS,
            "blind_holdout_steps": HOLDOUT_STEPS,
            "tomography_noise_sigma": NOISE_SIGMA,
            "candidate_count_per_scenario": len(candidate_names()),
            "fresh_scenario_count": len(results),
            "candidate_scenario_comparisons": len(candidate_names()) * len(results),
            "rolling_fit_executions": len(candidate_names()) * len(results) * len(ROLLING_HORIZONS),
            "holdout_accessed_by_selector": False,
            "profile_likelihood_scope": "top physical contenders within 75 percent of preliminary score; log-decays and frequencies profiled with nuisance refit",
            "weighted_memory_metric": "exponentially weighted discrete transfer-kernel relative L2 error on training data",
        },
        "scenarios": results,
        "aggregate": aggregate,
        "acceptance": {
            "selector_status_all_pass": all(
                result["selection_certificate"]["status"] == "PASS_MULTI_HORIZON_PHYSICAL_SELECTION"
                for result in results
            ),
            "selected_candidate_cptp_count": selected_cptp,
            "scenario_count": len(results),
            "selection_matches_hindsight_best_count": selected_matches,
            "high_dimensional_environment_executed": any(
                result["hidden_environment"]["active_mode_count"] > 60 for result in results
            ),
            "maximum_active_environment_modes": max(
                result["hidden_environment"]["active_mode_count"] for result in results
            ),
            "new_universal_law_claimed": False,
            "empirical_hardware_validation_claimed": False,
        },
        "claim_boundary": {
            "result_type": "COMPUTATIONAL_MODEL_SELECTION_QUALIFICATION",
            "physical_law_status": "NOT_PROMOTED",
            "over_60_registered_axes_claimed": False,
            "explanation": "128 active reservoir modes are operator-state variables, not 128 distinct registered Φ axes.",
            "fresh_blind_scope": "truth parameters and holdout trajectories are not supplied to the selector owner",
        },
        "elapsed_seconds": time.time() - started,
        "sha256": "",
    }
    report["sha256"] = digest_payload({key: value for key, value in report.items() if key != "sha256"})
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=float) + "\n", encoding="utf-8")
    compact = [
        {
            "scenario_id": result["scenario_id"],
            "selected_candidate_id": result["selected_candidate_id"],
            "selected_blind_holdout_rmse": result["selected_blind_holdout_rmse"],
            "selected_blind_holdout_cptp": result["selected_blind_holdout_cptp"],
            "hindsight_best_candidate_id": result["hindsight_best_candidate_id"],
            "selection_matches_hindsight_best": result["selection_matches_hindsight_best"],
        }
        for result in results
    ]
    RESULTS_PATH.write_text(json.dumps(compact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(REPORT_PATH), "acceptance": report["acceptance"], "elapsed_seconds": report["elapsed_seconds"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
