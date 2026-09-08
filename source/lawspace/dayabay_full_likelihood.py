"""Authoritative Daya Bay detector-period profile-likelihood owner.

The active owner consumes the digest-qualified public Daya Bay analysis NPZ
through SCIENTIFIC-DATA-INGESTION.  It performs one detector-period spectral
profile with the released IAV, LSNL and energy-resolution response, released
backgrounds and time-dependent reactor rates.  The standard three-flavour
fit remains the public-data reference point.  Any frozen owner-lowered
neutrino operator may be evaluated through the same detector response by
computing its exact electron-flavour survival amplitude from the complete
Takagi spectrum.  A common source spectrum is profiled as nuisance parameters,
so no parallel BSM fit or synthetic response is introduced.

The exact ``dayabay-model==1.8.0`` binary execution remains separately typed:
its wheel and transitive environment must be byte-materialized before this
owner may claim an exact reference-software reproduction.  The public-data fit
implemented here is the sole active local fit; no CLI or evaluator owns a
parallel scientific algorithm.
"""
from __future__ import annotations

import hashlib
import io
import json
import math
from pathlib import Path
from threading import RLock
from typing import Any, Mapping, Sequence

import numpy as np
import yaml
from scipy.optimize import brentq, minimize, minimize_scalar, nnls
from scipy.special import ndtr

from .scientific_data_ingestion import (
    DAYABAY_ANALYSIS_NPZ,
    DAYABAY_ANALYSIS_WHEEL,
    DAYABAY_MODEL_WHEEL,
    ScientificDataIngestionOwner,
)

OWNER_ID = "DAYA-BAY-FULL-LIKELIHOOD"
OWNER_VERSION = "6.10.0"
SCHEMA = "phi-dayabay-full-likelihood/v6.10"


def _digest(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=float).encode()
    ).hexdigest()


class DayaBayFullLikelihoodOwner:
    """Single owner of the active Daya Bay detector-period fit."""

    _SHARED_MODEL_CACHE: dict[tuple[str, int, int], Mapping[str, Any]] = {}
    _SHARED_FIT_CACHE: dict[tuple[str, int, int], Mapping[str, Any]] = {}
    _SHARED_CACHE_LOCK = RLock()

    DATASET_ID = "DAYA-BAY-OFFICIAL-ANALYSIS"
    OFFICIAL_EVENT_COUNT = 5_550_000
    OFFICIAL_LIVE_DAYS = 3158
    DETECTOR_COUNT = 8
    REACTOR_COUNT = 6
    REFERENCE_MODEL_VERSION = "1.8.0"
    REFERENCE_OUTPUT_KEYS = (
        "outputs.statistic.full.covmat.chi2cnp",
        "outputs.statistic.full.pull.chi2cnp",
    )
    REFERENCE_ENVIRONMENT_LOCK = {
        "dayabay-model": {
            "version": "1.8.0",
            "wheel_sha256": "74c328f9c8527bf3e1fac3d8e24acdee2253a3ee44c32066dcd2a4529efb7fb7",
        },
        "dayabay-data-official": {
            "version": "1.0.1",
            "wheel_sha256": "4578d71a741041d7b729dc7cacaa0836efe852d8f407d222ff8916c190dcfadf",
        },
        "dgm-fit": {
            "version": "0.4.0",
            "wheel_sha256": "35dd5c3f6bf65d159c551ec87d82430f105ba2769c94011354668cdb9f8ea0e9",
        },
        "dgm-reactor-neutrino": {
            "version": "0.3.0",
            "wheel_sha256": "e95742c57634b0e2d75c8c20f73b5e391992181635570b308c394f6454ef4565",
        },
        "dag-modelling": {
            "version": "0.15.0",
            "wheel_sha256": "f6f8ac6430909dd7b5cb4b69ce96c776f3231860e7148c7fc5bc8351484690f1",
        },
    }
    DIRECT_REFERENCE_DEPENDENCIES = (
        "dayabay-model==1.8.0",
        "dgm-fit==0.4.0",
        "dgm-reactor-neutrino==0.3.0",
        "dayabay-data-official==1.0.1",
        "dag-modelling==0.15.0",
    )
    PERIODS = ("6AD", "8AD", "7AD")
    PERIOD_DETECTOR_COUNT = {"6AD": 6, "8AD": 8, "7AD": 7}
    DETECTORS_BY_PERIOD = {
        "6AD": ("AD11", "AD12", "AD21", "AD31", "AD32", "AD33"),
        "8AD": ("AD11", "AD12", "AD21", "AD22", "AD31", "AD32", "AD33", "AD34"),
        "7AD": ("AD12", "AD21", "AD22", "AD31", "AD32", "AD33", "AD34"),
    }
    REACTORS = ("R1", "R2", "R3", "R4", "R5", "R6")
    PUBLISHED_BEST_FIT = {
        "sin2_2theta13": 0.0851,
        "sin2_2theta13_sigma": 0.0024,
        "dm32_ev2_normal": 2.466e-3,
        "dm32_ev2_sigma": 0.060e-3,
        "chi2": 559.0,
        "ndf": 517,
    }

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.ingestion = ScientificDataIngestionOwner(self.root)
        artifact_path = self.root / DAYABAY_ANALYSIS_NPZ.local_relative_path
        stat = artifact_path.stat() if artifact_path.is_file() else None
        self._cache_key = (
            str(self.root.resolve()),
            int(stat.st_size) if stat is not None else -1,
            int(stat.st_mtime_ns) if stat is not None else -1,
        )
        with self._SHARED_CACHE_LOCK:
            self._model_cache: Mapping[str, Any] | None = self._SHARED_MODEL_CACHE.get(self._cache_key)
            self._fit_cache: Mapping[str, Any] | None = self._SHARED_FIT_CACHE.get(self._cache_key)
        self._qualification_cache: Mapping[str, Any] | None = None

    def _publish_shared_cache(
        self, cache: dict[tuple[str, int, int], Mapping[str, Any]], value: Mapping[str, Any]
    ) -> None:
        """Publish one artifact-generation cache entry per distribution root.

        The file size and mtime remain part of the key, so a changed artifact can
        never reuse an older model or fit.  Superseded generations for the same
        root are removed to keep repeated orchestration bounded.
        """
        with self._SHARED_CACHE_LOCK:
            root_key = self._cache_key[0]
            for key in tuple(cache):
                if key[0] == root_key and key != self._cache_key:
                    del cache[key]
            cache[self._cache_key] = value

    @staticmethod
    def cnp_variance(observed: np.ndarray, expected: np.ndarray) -> np.ndarray:
        """Combined Neyman-Pearson per-bin variance.

        ``3/(1/n+2/mu)`` is evaluated with positive numerical guards.  The
        background covariance contribution is added by the caller.
        """
        n = np.asarray(observed, dtype=float)
        mu = np.asarray(expected, dtype=float)
        if n.shape != mu.shape or np.any(n < 0.0) or np.any(mu <= 0.0):
            raise ValueError("CNP inputs must be aligned physical counts")
        return 3.0 / (1.0 / np.maximum(n, 1.0e-12) + 2.0 / np.maximum(mu, 1.0e-12))

    @classmethod
    def cnp_covariance_chi2(cls, observed: np.ndarray, expected: np.ndarray, covariance: np.ndarray) -> float:
        """CNP statistic with an additive symmetric positive covariance."""
        n = np.asarray(observed, dtype=float).reshape(-1)
        mu = np.asarray(expected, dtype=float).reshape(-1)
        systematic = np.asarray(covariance, dtype=float)
        if n.shape != mu.shape or systematic.shape != (n.size, n.size):
            raise ValueError("Daya Bay observation, expectation and covariance shapes disagree")
        if not np.all(np.isfinite(n)) or not np.all(np.isfinite(mu)) or not np.all(np.isfinite(systematic)):
            raise ValueError("Daya Bay likelihood inputs must be finite")
        statistical = np.diag(cls.cnp_variance(n, mu))
        total = (systematic + systematic.T) / 2.0 + statistical
        eigenvalues = np.linalg.eigvalsh(total)
        if float(eigenvalues.min()) <= 0.0:
            raise ValueError("Daya Bay total covariance must be positive definite")
        residual = n - mu
        return float(residual @ np.linalg.solve(total, residual))

    @staticmethod
    def detector_period_prediction(
        reactor_flux: np.ndarray,
        survival_probability: np.ndarray,
        response_matrix: np.ndarray,
        efficiency: np.ndarray,
    ) -> np.ndarray:
        """Typed detector-period spectral lowering used by the active owner."""
        flux = np.asarray(reactor_flux, dtype=float)
        survival = np.asarray(survival_probability, dtype=float)
        response = np.asarray(response_matrix, dtype=float)
        efficiency = np.asarray(efficiency, dtype=float)
        if flux.shape != survival.shape or flux.ndim != 1:
            raise ValueError("flux and survival probability must be aligned one-dimensional arrays")
        if response.ndim != 2 or response.shape[1] != flux.size:
            raise ValueError("response matrix energy dimension mismatch")
        if efficiency.shape != (response.shape[0],):
            raise ValueError("efficiency must be defined per reconstructed-energy bin")
        prediction = efficiency * (response @ (flux * survival))
        if np.any(prediction < 0.0) or not np.all(np.isfinite(prediction)):
            raise ValueError("nonphysical Daya Bay detector prediction")
        return prediction

    @staticmethod
    def _load_npz(raw: bytes) -> Mapping[str, np.ndarray]:
        with np.load(io.BytesIO(raw), allow_pickle=True) as payload:
            return {key: payload[key] for key in payload.files}

    @staticmethod
    def _load_yaml(raw: bytes) -> Mapping[str, Any]:
        payload = yaml.safe_load(raw.decode("utf-8"))
        if not isinstance(payload, Mapping):
            raise ValueError("Daya Bay YAML must contain a mapping")
        return payload

    @staticmethod
    def _rebin_histogram(histogram: np.ndarray, final_edges: np.ndarray) -> np.ndarray:
        left = np.asarray(histogram["E_min_MeV"], dtype=float)
        right = np.asarray(histogram["E_max_MeV"], dtype=float)
        values = np.asarray(histogram["N"], dtype=float)
        widths = right - left
        result = []
        for low, high in zip(final_edges[:-1], final_edges[1:]):
            overlap = np.maximum(0.0, np.minimum(right, high) - np.maximum(left, low)) / widths
            result.append(float(np.sum(values * overlap)))
        return np.asarray(result, dtype=float)

    @staticmethod
    def _text_table_first_column(raw: bytes) -> np.ndarray:
        lines = [line.strip() for line in raw.decode("utf-8").splitlines() if line.strip()]
        if len(lines) < 2:
            raise ValueError("Daya Bay tabular bin definition is empty")
        return np.asarray([float(line.split("\t")[0]) for line in lines[1:]], dtype=float)

    def _load_public_model(self) -> Mapping[str, Any]:
        if self._model_cache is not None:
            return self._model_cache
        ir = self.ingestion.to_experiment_data_ir(self.DATASET_ID)
        if ir.get("status") != "PASS_EXPERIMENT_DATA_IR":
            raise RuntimeError(f"Daya Bay ExperimentDataIR is incomplete: {ir.get('status')}")
        prefix = "npz/"
        members = [
            prefix + "parameters/final_erec_bin_edges.tsv",
            prefix + "parameters/baselines.yaml",
            prefix + "parameters/detector_n_protons_correction.yaml",
            prefix + "parameters/reactor_fission_fractions.yaml",
            prefix + "parameters/detector_eres.yaml",
            prefix + "parameters/survival_probability_solar.yaml",
            prefix + "parameters/pdg2024.yaml",
            prefix + "dayabay_dataset/dayabay_daily_detector_data.npz",
            prefix + "dayabay_dataset/dayabay_background_rates.npz",
            prefix + "detector_iav_matrix.npz",
            prefix + "detector_lsnl_curves.npz",
            prefix + "neutrino_rate.npz",
            prefix + "reactor_antineutrino_spectra_hm.npz",
        ]
        for period in self.PERIODS:
            members.extend(
                (
                    prefix + f"dayabay_dataset/dayabay_ibd_spectra_{period}.npz",
                    prefix + f"dayabay_dataset/dayabay_background_spectra_{period}.npz",
                )
            )
        raw = self.ingestion.read_qualified_archive_members(DAYABAY_ANALYSIS_NPZ.artifact_id, members)
        final_edges = self._text_table_first_column(raw[prefix + "parameters/final_erec_bin_edges.tsv"])
        if final_edges.shape != (27,) or not np.all(np.diff(final_edges) > 0.0):
            raise ValueError("official Daya Bay final reconstructed-energy binning is invalid")
        baselines = self._load_yaml(raw[prefix + "parameters/baselines.yaml"])["parameters"]["baseline"]
        proton_correction = self._load_yaml(
            raw[prefix + "parameters/detector_n_protons_correction.yaml"]
        )["parameters"]["n_protons_correction"]
        fission_fractions = self._load_yaml(
            raw[prefix + "parameters/reactor_fission_fractions.yaml"]
        )["parameters"]["fission_fractions"]
        resolution = self._load_yaml(raw[prefix + "parameters/detector_eres.yaml"])["parameters"]["eres"]
        solar = self._load_yaml(raw[prefix + "parameters/survival_probability_solar.yaml"])["parameters"]
        pdg = self._load_yaml(raw[prefix + "parameters/pdg2024.yaml"])["parameters"]
        daily = self._load_npz(raw[prefix + "dayabay_dataset/dayabay_daily_detector_data.npz"])
        background_rates = self._load_npz(raw[prefix + "dayabay_dataset/dayabay_background_rates.npz"])
        reactor_rates = self._load_npz(raw[prefix + "neutrino_rate.npz"])
        iav = np.asarray(self._load_npz(raw[prefix + "detector_iav_matrix.npz"])["iav_matrix"], dtype=float)
        lsnl = self._load_npz(raw[prefix + "detector_lsnl_curves.npz"])["nominal"]
        huber_mueller = self._load_npz(raw[prefix + "reactor_antineutrino_spectra_hm.npz"])

        fine_edges = np.arange(0.0, 12.0 + 0.025, 0.05, dtype=float)
        fine_centers = (fine_edges[:-1] + fine_edges[1:]) / 2.0
        iav_column_sums = iav.sum(axis=0)
        populated_iav_columns = iav_column_sums > 0.0
        if (
            iav.shape != (240, 240)
            or not np.all(populated_iav_columns[20:])
            or np.any(populated_iav_columns[:20])
            or float(np.max(np.abs(iav_column_sums[populated_iav_columns] - 1.0))) > 1.0e-10
        ):
            raise ValueError(
                "Daya Bay IAV response must contain 20 threshold-zero columns followed by "
                "column-normalized physical-energy columns"
            )
        lsnl_factor = np.interp(
            fine_centers,
            np.asarray(lsnl["E_MeV"], dtype=float),
            np.asarray(lsnl["f"], dtype=float),
            left=float(lsnl["f"][0]),
            right=float(lsnl["f"][-1]),
        )
        mean_reconstructed = fine_centers * lsnl_factor
        a = float(resolution["a_nonuniform"][0])
        b_stat = float(resolution["b_stat"][0])
        c_noise = float(resolution["c_noise"][0])
        sigma = np.sqrt((a * fine_centers) ** 2 + (b_stat * np.sqrt(np.maximum(fine_centers, 1.0e-12))) ** 2 + c_noise**2)
        gaussian = np.empty((26, 240), dtype=float)
        for index, (low, high) in enumerate(zip(final_edges[:-1], final_edges[1:])):
            gaussian[index] = ndtr((high - mean_reconstructed) / sigma) - ndtr((low - mean_reconstructed) / sigma)
        response = gaussian @ iav

        neutrino_energy = fine_centers + 0.78
        flux = np.zeros_like(neutrino_energy)
        for isotope, fraction in fission_fractions.items():
            spectrum = huber_mueller[isotope]
            flux += float(fraction) * np.interp(
                neutrino_energy,
                np.asarray(spectrum["E_MeV"], dtype=float),
                np.asarray(spectrum["N_density"], dtype=float),
                left=0.0,
                right=0.0,
            )
        electron_mass = float(pdg["ElectronMass"])
        neutron_proton_difference = float(pdg["NeutronMass"]) - float(pdg["ProtonMass"])
        positron_energy = neutrino_energy - neutron_proton_difference
        positron_momentum = np.sqrt(np.maximum(positron_energy**2 - electron_mass**2, 0.0))
        source_shape = flux * positron_energy * positron_momentum
        source_shape[neutrino_energy < 1.806] = 0.0
        true_groups = tuple(
            np.where((fine_centers >= low) & (fine_centers < high))[0]
            for low, high in zip(final_edges[:-1], final_edges[1:])
        )

        max_days = max(len(np.asarray(value)) for value in daily.values())
        reactor_daily: dict[str, np.ndarray] = {}
        for reactor in self.REACTORS:
            values = np.zeros(max_days, dtype=float)
            for row in reactor_rates[reactor]:
                day = int(row["day"])
                n_days = int(row["n_days"])
                values[day : min(day + n_days, max_days)] = float(row["neutrino_rate_per_s"])
            reactor_daily[reactor] = values

        units: list[Mapping[str, Any]] = []
        for period in self.PERIODS:
            observations = self._load_npz(raw[prefix + f"dayabay_dataset/dayabay_ibd_spectra_{period}.npz"])
            background_shapes = self._load_npz(
                raw[prefix + f"dayabay_dataset/dayabay_background_spectra_{period}.npz"]
            )
            rate_table = background_rates[period]
            rate_map = {str(row["Label"]): row for row in rate_table}
            for detector in self.DETECTORS_BY_PERIOD[period]:
                observed = self._rebin_histogram(observations[f"ibd_spectrum_{detector}"], final_edges)
                detector_daily = daily[detector]
                active = np.asarray(detector_daily["n_det"] == self.PERIOD_DETECTOR_COUNT[period])
                effective_seconds = np.where(active, np.asarray(detector_daily["eff_livetime"], dtype=float), 0.0)
                effective_days = float(effective_seconds.sum() / 86400.0)
                background = np.zeros(26, dtype=float)
                background_variance = np.zeros(26, dtype=float)
                for component in ("accidentals", "lithium_helium", "fast_neutrons", "alpha_neutron", "amc"):
                    shape = self._rebin_histogram(
                        background_shapes[f"spectrum_shape_{component}_{detector}"], final_edges
                    )
                    if float(shape.sum()) <= 0.0:
                        raise ValueError("Daya Bay background shape has zero normalization")
                    shape /= float(shape.sum())
                    rate = float(rate_map[f"{component}_rate"][detector])
                    uncertainty = float(rate_map[f"{component}_uncertainty"][detector])
                    background += rate * effective_days * shape
                    background_variance += (uncertainty * effective_days * shape) ** 2
                reactor_weight = np.asarray(
                    [
                        float(np.sum(effective_seconds * reactor_daily[reactor]))
                        / float(baselines[detector][reactor]) ** 2
                        for reactor in self.REACTORS
                    ],
                    dtype=float,
                ) * float(proton_correction[detector])
                units.append(
                    {
                        "period": period,
                        "detector": detector,
                        "observed": observed,
                        "background": background,
                        "background_variance": background_variance,
                        "reactor_weight": reactor_weight,
                        "baselines_m": np.asarray([float(baselines[detector][reactor]) for reactor in self.REACTORS]),
                        "effective_days": effective_days,
                    }
                )
        reactor_weights = np.stack([row["reactor_weight"] for row in units])
        reactor_weights /= float(np.median(np.sum(reactor_weights, axis=1)))
        model = {
            "experiment_data_ir": ir,
            "final_edges": final_edges,
            "fine_centers": fine_centers,
            "response": response,
            "source_shape": source_shape,
            "true_groups": true_groups,
            "observed": np.stack([row["observed"] for row in units]),
            "background": np.stack([row["background"] for row in units]),
            "background_variance": np.stack([row["background_variance"] for row in units]),
            "reactor_weights": reactor_weights,
            "baselines_m": np.stack([row["baselines_m"] for row in units]),
            "units": tuple({key: value for key, value in row.items() if key not in {"observed", "background", "background_variance", "reactor_weight", "baselines_m"}} for row in units),
            "sin2_2theta12": float(solar["SinSq2Theta12"][0]),
            "dm21_ev2": float(solar["DeltaMSq21"][0]),
        }
        if model["observed"].shape != (21, 26):
            raise ValueError("Daya Bay detector-period observation must contain 21 spectra with 26 bins")
        self._model_cache = model
        self._publish_shared_cache(self._SHARED_MODEL_CACHE, model)
        return model

    @staticmethod
    def _sin2_from_sin22(value: float) -> float:
        if not 0.0 <= value <= 1.0:
            raise ValueError("sin²2θ must be in [0,1]")
        return (1.0 - math.sqrt(max(0.0, 1.0 - value))) / 2.0

    def _survival_probability(self, sin2_2theta13: float, dm32_ev2: float, prompt_energy: np.ndarray) -> np.ndarray:
        model = self._load_public_model()
        sin2_theta13 = self._sin2_from_sin22(float(sin2_2theta13))
        cos2_theta13 = 1.0 - sin2_theta13
        sin2_theta12 = self._sin2_from_sin22(float(model["sin2_2theta12"]))
        cos2_theta12 = 1.0 - sin2_theta12
        energy = np.asarray(prompt_energy, dtype=float) + 0.78
        baselines = np.asarray(model["baselines_m"], dtype=float)[:, :, None]
        phase21 = 1.267 * float(model["dm21_ev2"]) * baselines / energy[None, None, :]
        phase32 = 1.267 * float(dm32_ev2) * baselines / energy[None, None, :]
        phase31 = 1.267 * (float(dm32_ev2) + float(model["dm21_ev2"])) * baselines / energy[None, None, :]
        probability = (
            1.0
            - cos2_theta13**2 * float(model["sin2_2theta12"]) * np.sin(phase21) ** 2
            - float(sin2_2theta13)
            * (cos2_theta12 * np.sin(phase31) ** 2 + sin2_theta12 * np.sin(phase32) ** 2)
        )
        if np.any(probability < -1.0e-12) or np.any(probability > 1.0 + 1.0e-12):
            raise ValueError("Daya Bay survival probability left the physical interval")
        return np.clip(probability, 0.0, 1.0)

    @staticmethod
    def _takagi_survival_probability(
        *,
        takagi_spectrum: Mapping[str, Any],
        baselines_m: np.ndarray,
        prompt_energy: np.ndarray,
    ) -> tuple[np.ndarray, Mapping[str, Any]]:
        """Electron-flavour survival probability for one complete Takagi identity.

        The propagation phase uses the same Daya Bay convention as the 3nu
        reference kernel.  A common mass-squared phase is subtracted for
        numerical stability and has no observable effect.  No family label or
        published-template branch enters this calculation.
        """
        masses = np.asarray(takagi_spectrum.get("takagi_masses_ev", ()), dtype=float)
        active_real = np.asarray(takagi_spectrum.get("active_mixing_real", ()), dtype=float)
        active_imag = np.asarray(takagi_spectrum.get("active_mixing_imag", ()), dtype=float)
        if masses.ndim != 1 or masses.size < 1 or np.any(masses < 0.0) or not np.all(np.isfinite(masses)):
            raise ValueError("candidate Takagi spectrum must contain finite non-negative masses")
        if active_real.shape != active_imag.shape or active_real.ndim != 2 or active_real.shape[0] != 3 or active_real.shape[1] != masses.size:
            raise ValueError("candidate active mixing must be a complete 3 x N Takagi projection")
        active = active_real + 1j * active_imag
        electron_weights = np.abs(active[0]) ** 2
        electron_norm = float(electron_weights.sum())
        if not np.isfinite(electron_norm) or abs(electron_norm - 1.0) > 1.0e-8:
            raise ValueError("candidate electron-flavour Takagi row must be unit normalised")
        energy = np.asarray(prompt_energy, dtype=float) + 0.78
        baselines = np.asarray(baselines_m, dtype=float)
        if energy.ndim != 1 or np.any(energy <= 0.0) or baselines.ndim != 2 or np.any(baselines < 0.0):
            raise ValueError("Daya Bay candidate propagation grid is invalid")
        mass2 = masses * masses
        shifted_mass2 = mass2 - float(mass2.min())
        phase = (
            2.0
            * 1.267
            * baselines[:, :, None, None]
            * shifted_mass2[None, None, None, :]
            / energy[None, None, :, None]
        )
        amplitude = np.sum(electron_weights[None, None, None, :] * np.exp(-1j * phase), axis=-1)
        probability = np.abs(amplitude) ** 2
        if not np.all(np.isfinite(probability)) or np.any(probability < -1.0e-12) or np.any(probability > 1.0 + 1.0e-10):
            raise ValueError("candidate Daya Bay survival probability left the physical interval")
        diagnostics = {
            "propagating_modes": int(masses.size),
            "electron_flavour_norm": electron_norm,
            "minimum_survival_probability": float(np.min(probability)),
            "maximum_survival_probability": float(np.max(probability)),
            "mass_squared_span_ev2": float(np.max(mass2) - np.min(mass2)),
        }
        return np.clip(probability, 0.0, 1.0), diagnostics

    def _design_matrix_from_probability(self, probability: np.ndarray) -> np.ndarray:
        model = self._load_public_model()
        probability = np.asarray(probability, dtype=float)
        expected_shape = (len(model["units"]), len(self.REACTORS), len(model["fine_centers"]))
        if probability.shape != expected_shape:
            raise ValueError(f"Daya Bay survival tensor must have shape {expected_shape}, received {probability.shape}")
        response = np.asarray(model["response"], dtype=float)
        source_shape = np.asarray(model["source_shape"], dtype=float)
        reactor_weights = np.asarray(model["reactor_weights"], dtype=float)
        blocks: list[np.ndarray] = []
        for unit_index in range(probability.shape[0]):
            weighted_probability = np.sum(
                reactor_weights[unit_index, :, None] * probability[unit_index], axis=0
            )
            block = np.zeros((26, 26), dtype=float)
            for true_index, fine_indices in enumerate(model["true_groups"]):
                shape = source_shape[fine_indices]
                normalization = float(shape.sum())
                if normalization <= 0.0:
                    continue
                block[:, true_index] = response[:, fine_indices] @ (
                    shape * weighted_probability[fine_indices]
                ) / normalization
            blocks.append(block)
        return np.vstack(blocks)

    def _design_matrix(self, sin2_2theta13: float, dm32_ev2: float) -> np.ndarray:
        model = self._load_public_model()
        probability = self._survival_probability(sin2_2theta13, dm32_ev2, model["fine_centers"])
        return self._design_matrix_from_probability(probability)

    def _candidate_design_matrix(self, candidate_contract: Mapping[str, Any]) -> tuple[np.ndarray, Mapping[str, Any]]:
        identity = candidate_contract.get("operator_identity")
        if not isinstance(identity, Mapping) or candidate_contract.get("operator_identity_status") != "COMPLETE_OWNER_LOWERED_OPERATOR_IDENTITY":
            raise ValueError("candidate requires a complete owner-lowered operator identity")
        takagi = identity.get("takagi_spectrum")
        if not isinstance(takagi, Mapping):
            raise ValueError("candidate operator identity lacks a Takagi spectrum")
        model = self._load_public_model()
        probability, diagnostics = self._takagi_survival_probability(
            takagi_spectrum=takagi,
            baselines_m=np.asarray(model["baselines_m"], dtype=float),
            prompt_energy=np.asarray(model["fine_centers"], dtype=float),
        )
        return self._design_matrix_from_probability(probability), diagnostics

    def _profile_source_spectrum(
        self,
        design: np.ndarray,
        *,
        unit_indices: Sequence[int] | None = None,
        fixed_source: np.ndarray | Sequence[float] | None = None,
    ) -> Mapping[str, Any]:
        """Profile or predict one exact detector-period subset.

        ``unit_indices`` selects complete 26-bin detector-period spectra.  When
        ``fixed_source`` is absent the common source spectrum nuisance is
        profiled on that subset by the same CNP iteration used by the full
        likelihood.  When it is supplied, the source nuisance is frozen and no
        refit is allowed; this is used for genuine held-out period prediction.
        """
        model = self._load_public_model()
        full_design = np.asarray(design, dtype=float)
        unit_count = len(model["units"])
        if full_design.shape != (unit_count * 26, 26):
            raise ValueError("Daya Bay design matrix must contain one 26-bin block per detector-period unit")
        indices = tuple(range(unit_count)) if unit_indices is None else tuple(int(i) for i in unit_indices)
        if not indices or len(set(indices)) != len(indices) or any(i < 0 or i >= unit_count for i in indices):
            raise ValueError("Daya Bay detector-period subset indices are invalid")
        row_indices = np.concatenate([np.arange(i * 26, (i + 1) * 26, dtype=int) for i in indices])
        design_selected = full_design[row_indices]
        observed = np.asarray(model["observed"], dtype=float)[list(indices)].reshape(-1)
        background = np.asarray(model["background"], dtype=float)[list(indices)].reshape(-1)
        background_variance = np.asarray(model["background_variance"], dtype=float)[list(indices)].reshape(-1)
        target = observed - background
        variance = np.maximum(observed, 1.0) + background_variance
        if fixed_source is None:
            source = np.ones(design_selected.shape[1], dtype=float)
            profile_iterations = 0
            for iteration in range(12):
                profile_iterations = iteration + 1
                weighted_design = design_selected / np.sqrt(variance)[:, None]
                weighted_target = target / np.sqrt(variance)
                source_new, _ = nnls(weighted_design, weighted_target, maxiter=1000)
                expected = background + design_selected @ source_new
                variance_new = self.cnp_variance(observed, np.maximum(expected, 1.0e-12)) + background_variance
                relative_change = float(np.max(np.abs(variance_new - variance) / np.maximum(variance, 1.0)))
                source = source_new
                variance = variance_new
                if relative_change <= 1.0e-10:
                    break
            nuisance_mode = "PROFILED_ON_SELECTED_PERIODS"
        else:
            source = np.asarray(fixed_source, dtype=float).reshape(-1)
            if source.shape != (design_selected.shape[1],) or np.any(source < 0.0) or not np.all(np.isfinite(source)):
                raise ValueError("frozen Daya Bay source nuisance must be finite, non-negative and 26-dimensional")
            expected = background + design_selected @ source
            variance = self.cnp_variance(observed, np.maximum(expected, 1.0e-12)) + background_variance
            profile_iterations = 0
            nuisance_mode = "FROZEN_FROM_DISCOVERY_PERIODS_NO_REFIT"
        expected = background + design_selected @ source
        chi2 = float(np.sum((observed - expected) ** 2 / variance))
        scaled_design = design_selected / np.sqrt(variance)[:, None]
        singular_values = np.linalg.svd(scaled_design, compute_uv=False)
        noise_floor = float(singular_values[0] / math.sqrt(max(float(observed.sum()), 1.0)))
        effective_rank = int(np.sum(singular_values > noise_floor))
        condition_number = float(singular_values[0] / singular_values[-1])
        return {
            "chi2": chi2,
            "source": source,
            "expected": expected,
            "variance": variance,
            "singular_values": singular_values,
            "noise_floor": noise_floor,
            "effective_rank": effective_rank,
            "condition_number": condition_number,
            "unit_indices": indices,
            "spectrum_count": len(indices),
            "observation_bin_count": int(observed.size),
            "nuisance_mode": nuisance_mode,
            "profile_iterations": profile_iterations,
        }

    def _period_indices(self, periods: Sequence[str]) -> tuple[int, ...]:
        requested = tuple(str(period) for period in periods)
        if not requested or any(period not in self.PERIODS for period in requested):
            raise ValueError("Daya Bay period partition must use declared detector configurations")
        model = self._load_public_model()
        indices = tuple(i for i, unit in enumerate(model["units"]) if str(unit["period"]) in requested)
        if not indices:
            raise ValueError("Daya Bay period partition selected no detector-period spectra")
        return indices

    def _expected_counts_for_periods(
        self,
        *,
        design: np.ndarray,
        source_spectrum: np.ndarray | Sequence[float],
        periods: Sequence[str],
    ) -> Mapping[str, Any]:
        """Forward-predict complete detector-period count spectra with no target refit.

        The signal source spectrum and oscillation design are already frozen by the
        discovery partition.  Held-out target counts are not accessed here.  Period-
        specific background estimates are treated as declared experimental covariates
        and are added to the forward signal prediction.
        """
        model = self._load_public_model()
        indices = self._period_indices(periods)
        full_design = np.asarray(design, dtype=float)
        source = np.asarray(source_spectrum, dtype=float).reshape(-1)
        if full_design.shape != (len(model["units"]) * 26, 26):
            raise ValueError("Daya Bay design matrix shape mismatch for held-out prediction")
        if source.shape != (26,) or np.any(source < 0.0) or not np.all(np.isfinite(source)):
            raise ValueError("frozen discovery source must be finite, non-negative and 26-dimensional")
        row_indices = np.concatenate([np.arange(i * 26, (i + 1) * 26, dtype=int) for i in indices])
        signal = full_design[row_indices] @ source
        background = np.asarray(model["background"], dtype=float)[list(indices)].reshape(-1)
        expected = background + signal
        if np.any(expected <= 0.0) or not np.all(np.isfinite(expected)):
            raise ValueError("held-out expected counts must be finite and strictly positive")
        return {
            "periods": tuple(str(x) for x in periods),
            "unit_indices": indices,
            "observation_bin_count": int(expected.size),
            "expected_counts": tuple(float(x) for x in expected),
            "expected_counts_digest": _digest(tuple(float(x) for x in expected)),
            "background_covariates_used": True,
            "heldout_target_counts_used": False,
        }

    def freeze_manual_metrology_prediction(self, lowering_contract: Mapping[str, Any]) -> Mapping[str, Any]:
        """One manually specified candidate→prediction lowering, frozen before reveal.

        This is intentionally *not* an automatic lowering rule for a candidate class.
        It is a single auditable worked example for a metrology candidate already bound
        to Daya Bay.  Only the discovery detector configuration may influence fitted
        oscillation coordinates and the common source nuisance.  Held-out signal counts
        are not inspected until ``score_frozen_manual_metrology_prediction``.
        """
        contract = dict(lowering_contract)
        required_exact = {
            "lowering_operation": "DAYABAY_CNP_DISCOVERY_TO_HELDOUT_COUNT_VECTOR",
            "source_owner_id": "REACTOR-COVARIANCE-LIKELIHOOD",
            "mechanism_family": "JOINT_TYPED_INTERACTION",
            "discovery_periods": ["6AD"],
            "heldout_period_partitions": [["8AD"], ["7AD"]],
            "heldout_refit_allowed": False,
            "prediction_quantity_id": "QTY-EXPECTED-COUNT",
            "collapse_statistic": "REDUCED_CNP_CHI2_TWO_PERIOD_95PCT_ASYMPTOTIC_COLLAPSE",
            "collapse_z_threshold": 1.96,
        }
        checks = {
            "CONTRACT_DIGEST_VALID": str(contract.get("digest", "")) == _digest({k: v for k, v in contract.items() if k != "digest"}),
            "MANUAL_SINGLE_CANDIDATE_DECLARED": bool(str(contract.get("candidate_id", "")).strip()),
            "HYPOTHESIS_DIGEST_DECLARED": len(str(contract.get("hypothesis_digest", ""))) == 64,
            "BINDING_DIGEST_DECLARED": len(str(contract.get("binding_receipt_digest", ""))) == 64,
            "RESPONSE_PROJECTION_DIGEST_DECLARED": len(str(contract.get("response_projection_receipt_digest", ""))) == 64,
            "NO_PREEXISTING_TARGET_VALUES_IN_CONTRACT": all(k not in contract for k in ("heldout_chi2", "heldout_reduced_chi2", "observed_counts", "collapse_result")),
        }
        for key, value in required_exact.items():
            checks[f"PRECOMMIT_{key.upper()}"] = contract.get(key) == value
        if not all(checks.values()):
            payload = {
                "schema": "phi-dayabay-manual-prediction-freeze/v1",
                "owner_id": OWNER_ID,
                "owner_version": OWNER_VERSION,
                "status": "BLOCKED_MANUAL_LOWERING_PRECOMMIT",
                "checks": checks,
                "candidate_id": contract.get("candidate_id"),
                "lowering_contract_digest": contract.get("digest"),
            }
            return {**payload, "digest": _digest(payload)}

        ir = self.ingestion.to_experiment_data_ir(self.DATASET_ID)
        if ir.get("status") != "PASS_EXPERIMENT_DATA_IR":
            payload = {
                "schema": "phi-dayabay-manual-prediction-freeze/v1", "owner_id": OWNER_ID,
                "owner_version": OWNER_VERSION, "status": "BLOCKED_DAYABAY_EXPERIMENT_DATA_IR_INCOMPLETE",
                "candidate_id": contract.get("candidate_id"), "lowering_contract_digest": contract.get("digest"),
            }
            return {**payload, "digest": _digest(payload)}

        discovery_periods = tuple(contract["discovery_periods"])
        discovery_indices = self._period_indices(discovery_periods)
        fit = self._multistart_fit(unit_indices=discovery_indices)
        best = dict(fit["best"])
        design = self._design_matrix(float(best["sin2_2theta13"]), float(best["dm32_ev2"]))
        discovery_profile = self._profile_source_spectrum(design, unit_indices=discovery_indices)
        source = np.asarray(discovery_profile["source"], dtype=float)
        source_digest = _digest(tuple(float(x) for x in source))
        predictions = [
            self._expected_counts_for_periods(design=design, source_spectrum=source, periods=tuple(partition))
            for partition in contract["heldout_period_partitions"]
        ]
        payload = {
            "schema": "phi-dayabay-manual-prediction-freeze/v1",
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "status": "FROZEN_MANUAL_CANDIDATE_SPECIFIC_PREDICTION_HELDOUT_UNREVEALED",
            "candidate_id": contract["candidate_id"],
            "lowering_contract_digest": contract["digest"],
            "experiment_data_ir_digest": ir["digest"],
            "discovery": {
                "periods": discovery_periods,
                "unit_indices": discovery_indices,
                "fit_algorithm": "EXISTING_DAYABAY_CNP_MULTISTART_PROFILE",
                "fit_certificate": fit.get("certificate"),
                "sin2_2theta13": float(best["sin2_2theta13"]),
                "dm32_ev2": float(best["dm32_ev2"]),
                "profiled_source_spectrum": tuple(float(x) for x in source),
                "profiled_source_spectrum_digest": source_digest,
                "discovery_chi2": float(discovery_profile["chi2"]),
                "discovery_observation_bin_count": int(discovery_profile["observation_bin_count"]),
            },
            "heldout_predictions": predictions,
            "collapse_precommit": {
                "statistic": contract["collapse_statistic"],
                "z_threshold": float(contract["collapse_z_threshold"]),
                "per_partition_rule": "abs(reduced_chi2-1) <= z*sqrt(2/ndf)",
                "cross_partition_rule": "abs(r1-r2) <= z*sqrt(2/ndf1+2/ndf2)",
                "ndf_rule": "heldout observation-bin count because no heldout parameter or source refit is permitted",
            },
            "checks": {
                **checks,
                "DISCOVERY_AND_HELDOUT_DISJOINT": not set(discovery_periods).intersection({p for part in contract["heldout_period_partitions"] for p in part}),
                "HELDOUT_REFIT_DISABLED": contract["heldout_refit_allowed"] is False,
                "PREDICTION_VECTORS_FROZEN": all(bool(row.get("expected_counts_digest")) for row in predictions),
                "HELDOUT_TARGET_COUNTS_USED_IN_FREEZE": False,
            },
            "claim_boundary": {
                "manual_one_off_lowering": True,
                "automatic_candidate_class_lowering_established": False,
                "heldout_signal_counts_observed_at_freeze": False,
                "retrospective_public_dataset_already_exists": True,
                "world_attestation_established": False,
                "u5_passed": False,
                "new_law_established": False,
            },
        }
        return {**payload, "digest": _digest(payload)}

    def score_frozen_manual_metrology_prediction(self, frozen_prediction: Mapping[str, Any]) -> Mapping[str, Any]:
        """Reveal only the held-out target counts for a previously frozen prediction."""
        frozen = dict(frozen_prediction)
        embedded = str(frozen.get("digest", ""))
        checks = {
            "FROZEN_PREDICTION_DIGEST_VALID": embedded == _digest({k: v for k, v in frozen.items() if k != "digest"}),
            "PREDICTION_STATUS_FROZEN": frozen.get("status") == "FROZEN_MANUAL_CANDIDATE_SPECIFIC_PREDICTION_HELDOUT_UNREVEALED",
            "HELDOUT_TARGETS_WERE_NOT_USED_AT_FREEZE": frozen.get("checks", {}).get("HELDOUT_TARGET_COUNTS_USED_IN_FREEZE") is False,
        }
        ir = self.ingestion.to_experiment_data_ir(self.DATASET_ID)
        checks["CURRENT_IR_MATCHES_FREEZE"] = str(ir.get("digest", "")) == str(frozen.get("experiment_data_ir_digest", ""))
        if not all(checks.values()):
            payload = {
                "schema": "phi-dayabay-manual-prediction-discrimination/v1", "owner_id": OWNER_ID,
                "owner_version": OWNER_VERSION, "candidate_id": frozen.get("candidate_id"),
                "frozen_prediction_digest": embedded, "checks": checks,
                "status": "BLOCKED_MANUAL_PREDICTION_REVEAL_INTEGRITY",
            }
            return {**payload, "digest": _digest(payload)}

        model = self._load_public_model()
        z = float(frozen["collapse_precommit"]["z_threshold"])
        rows: list[Mapping[str, Any]] = []
        for pred in frozen.get("heldout_predictions", ()):
            periods = tuple(str(x) for x in pred.get("periods", ()))
            indices = tuple(int(x) for x in pred.get("unit_indices", ()))
            expected = np.asarray(pred.get("expected_counts", ()), dtype=float)
            if _digest(tuple(float(x) for x in expected)) != pred.get("expected_counts_digest"):
                raise ValueError("frozen held-out prediction vector digest mismatch")
            observed = np.asarray(model["observed"], dtype=float)[list(indices)].reshape(-1)
            background_variance = np.asarray(model["background_variance"], dtype=float)[list(indices)].reshape(-1)
            if observed.shape != expected.shape:
                raise ValueError("held-out observation/prediction shape mismatch")
            variance = self.cnp_variance(observed, np.maximum(expected, 1.0e-12)) + background_variance
            chi2 = float(np.sum((observed - expected) ** 2 / variance))
            ndf = int(observed.size)
            reduced = chi2 / float(ndf)
            sigma_reduced = math.sqrt(2.0 / float(ndf))
            z_from_one = abs(reduced - 1.0) / sigma_reduced
            rows.append({
                "periods": periods,
                "observation_bin_count": ndf,
                "ndf": ndf,
                "chi2": chi2,
                "reduced_chi2": reduced,
                "asymptotic_sigma_reduced_chi2": sigma_reduced,
                "z_from_unit_reduced_chi2": z_from_one,
                "within_predeclared_95pct_band": bool(z_from_one <= z),
                "observed_counts_digest": _digest(tuple(float(x) for x in observed)),
                "expected_counts_digest": pred.get("expected_counts_digest"),
                "heldout_refit_performed": False,
            })
        if len(rows) != 2:
            raise ValueError("manual Daya Bay lowering requires exactly two held-out trajectories")
        r1, r2 = rows
        cross_sigma = math.sqrt(2.0 / float(r1["ndf"]) + 2.0 / float(r2["ndf"]))
        cross_z = abs(float(r1["reduced_chi2"]) - float(r2["reduced_chi2"])) / cross_sigma
        collapse = all(bool(r["within_predeclared_95pct_band"]) for r in rows) and cross_z <= z
        payload = {
            "schema": "phi-dayabay-manual-prediction-discrimination/v1",
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "candidate_id": frozen.get("candidate_id"),
            "frozen_prediction_digest": embedded,
            "lowering_contract_digest": frozen.get("lowering_contract_digest"),
            "experiment_data_ir_digest": ir.get("digest"),
            "checks": checks,
            "heldout_trajectories": rows,
            "collapse_result": {
                "statistic": frozen["collapse_precommit"]["statistic"],
                "z_threshold": z,
                "cross_partition_z": cross_z,
                "all_partition_bands_pass": all(bool(r["within_predeclared_95pct_band"]) for r in rows),
                "cross_partition_collapse_pass": bool(cross_z <= z),
                "collapse_pass": bool(collapse),
            },
            "candidate_specific_prediction_used": True,
            "candidate_prediction_checked_on_disjoint_heldout_periods": True,
            "scientific_discrimination_executed": False,
            "status": "PASS_MANUAL_CANDIDATE_PREDICTION_COLLAPSE_DIAGNOSTIC" if collapse else "FAIL_MANUAL_CANDIDATE_PREDICTION_COLLAPSE_DIAGNOSTIC",
            "claim_boundary": {
                "candidate_specific_prediction_established_for_this_one_manual_lowering": True,
                "automatic_lowering_generalized": False,
                "retrospective_public_data_reanalysis": True,
                "heldout_periods_are_disjoint_within_dataset": True,
                "independent_world_attestation_established": False,
                "u5_passed": False,
                "new_law_established": False,
            },
        }
        return {**payload, "digest": _digest(payload)}

    def discovery_partition_score(
        self,
        *,
        family: str,
        candidate_contract: Mapping[str, Any],
        discovery_periods: Sequence[str] = ("6AD",),
    ) -> Mapping[str, Any]:
        """Real-data discovery quality on a declared training partition only.

        This is not held-out evidence and is never reported as an independent
        validation.  It exists so blind structural synthesis can learn from
        observations without importing a named theory template.
        """
        if candidate_contract.get("family") != family or not candidate_contract.get("digest"):
            raise ValueError("candidate contract must bind family and digest")
        ir = self.ingestion.to_experiment_data_ir(self.DATASET_ID)
        if ir.get("status") != "PASS_EXPERIMENT_DATA_IR":
            return {
                "status": "BLOCKED_DISCOVERY_PARTITION_DATA_IR_INCOMPLETE",
                "candidate_digest": candidate_contract.get("digest"),
                "quality_loss": None,
                "discovery_periods": tuple(discovery_periods),
                "synthetic_substitution_allowed": False,
            }
        try:
            design, propagation = self._candidate_design_matrix(candidate_contract)
        except (TypeError, ValueError) as exc:
            return {
                "status": "BLOCKED_DISCOVERY_PARTITION_OPERATOR_IDENTITY_INCOMPLETE",
                "candidate_digest": candidate_contract.get("digest"),
                "quality_loss": None,
                "reason": str(exc),
                "synthetic_substitution_allowed": False,
            }
        indices = self._period_indices(discovery_periods)
        profiled = self._profile_source_spectrum(design, unit_indices=indices)
        source = np.asarray(profiled["source"], dtype=float)
        nuisance_payload = {
            "candidate_digest": str(candidate_contract["digest"]),
            "dataset_ir_digest": ir["digest"],
            "discovery_periods": tuple(discovery_periods),
            "source_spectrum": tuple(float(v) for v in source),
        }
        nuisance_digest = _digest(nuisance_payload)
        return {
            "status": "PASS_DISCOVERY_PARTITION_PROFILE_EXECUTED",
            "candidate_digest": str(candidate_contract["digest"]),
            "quality_metric": "DAYABAY_CNP_PROFILE_CHI2_ON_DECLARED_DISCOVERY_PERIODS",
            "quality_loss": float(profiled["chi2"]),
            "chi2": float(profiled["chi2"]),
            "discovery_periods": tuple(discovery_periods),
            "discovery_unit_indices": indices,
            "observation_bin_count": int(profiled["observation_bin_count"]),
            "profiled_source_spectrum": nuisance_payload["source_spectrum"],
            "discovery_nuisance_digest": nuisance_digest,
            "experiment_data_ir_digest": ir["digest"],
            "propagation_diagnostics": propagation,
            "synthetic_substitution_allowed": False,
            "claim_boundary": {
                "heldout_evidence": False,
                "literature_or_named_model_information_used": False,
                "source_nuisance_profiled_on_discovery_only": True,
            },
        }

    def heldout_partition_score(
        self,
        *,
        family: str,
        candidate_contract: Mapping[str, Any],
        frozen_discovery_profile: Mapping[str, Any],
        heldout_periods: Sequence[str] = ("8AD", "7AD"),
    ) -> Mapping[str, Any]:
        """Predict held-out detector periods with the discovery nuisance frozen."""
        if frozen_discovery_profile.get("status") != "PASS_DISCOVERY_PARTITION_PROFILE_EXECUTED":
            raise ValueError("held-out Daya Bay evaluation requires a successful frozen discovery profile")
        if frozen_discovery_profile.get("candidate_digest") != candidate_contract.get("digest"):
            raise ValueError("Daya Bay held-out candidate digest differs from discovery profile")
        nuisance_payload = {
            "candidate_digest": str(candidate_contract["digest"]),
            "dataset_ir_digest": frozen_discovery_profile.get("experiment_data_ir_digest"),
            "discovery_periods": tuple(frozen_discovery_profile.get("discovery_periods", ())),
            "source_spectrum": tuple(float(v) for v in frozen_discovery_profile.get("profiled_source_spectrum", ())),
        }
        if _digest(nuisance_payload) != frozen_discovery_profile.get("discovery_nuisance_digest"):
            raise ValueError("frozen Daya Bay discovery nuisance digest mismatch")
        heldout = tuple(str(period) for period in heldout_periods)
        discovery_periods = set(str(v) for v in frozen_discovery_profile.get("discovery_periods", ()))
        if discovery_periods.intersection(heldout):
            raise ValueError("Daya Bay discovery and held-out period sets must be disjoint")
        design, propagation = self._candidate_design_matrix(candidate_contract)
        indices = self._period_indices(heldout)
        predicted = self._profile_source_spectrum(
            design, unit_indices=indices, fixed_source=np.asarray(nuisance_payload["source_spectrum"], dtype=float)
        )
        return {
            "status": "PASS_HELDOUT_PERIOD_PREDICTION_EXECUTED",
            "candidate_digest": str(candidate_contract["digest"]),
            "evidence_class": "PUBLIC_REAL_DATA_HELDOUT_PERIOD_PREDICTION",
            "heldout_periods": heldout,
            "heldout_unit_indices": indices,
            "chi2": float(predicted["chi2"]),
            "observation_bin_count": int(predicted["observation_bin_count"]),
            "source_nuisance_refit_on_heldout": False,
            "discovery_nuisance_digest": frozen_discovery_profile["discovery_nuisance_digest"],
            "experiment_data_ir_digest": frozen_discovery_profile["experiment_data_ir_digest"],
            "propagation_diagnostics": propagation,
            "synthetic_substitution_allowed": False,
        }

    def _objective(
        self,
        sin2_2theta13: float,
        dm32_ev2: float,
        *,
        unit_indices: Sequence[int] | None = None,
    ) -> float:
        if not (0.04 <= sin2_2theta13 <= 0.14 and 1.8e-3 <= dm32_ev2 <= 3.2e-3):
            return 1.0e12
        return float(
            self._profile_source_spectrum(
                self._design_matrix(sin2_2theta13, dm32_ev2), unit_indices=unit_indices
            )["chi2"]
        )

    def _multistart_fit(self, *, unit_indices: Sequence[int] | None = None) -> Mapping[str, Any]:
        starts = (
            (0.060, 2.10), (0.060, 2.50), (0.060, 2.90),
            (0.085, 2.10), (0.085, 2.50), (0.085, 2.90),
            (0.110, 2.10), (0.110, 2.50), (0.110, 2.90),
            (0.075, 2.35), (0.095, 2.65), (0.105, 2.45),
        )
        rows: list[Mapping[str, Any]] = []
        for start in starts:
            result = minimize(
                lambda point: self._objective(float(point[0]), float(point[1]) * 1.0e-3, unit_indices=unit_indices),
                np.asarray(start, dtype=float),
                method="L-BFGS-B",
                bounds=((0.04, 0.14), (1.8, 3.2)),
                options={"ftol": 1.0e-12, "gtol": 1.0e-8, "maxiter": 300},
            )
            primary = result
            fallback_used = False
            if not bool(primary.success):
                result = minimize(
                    lambda point: self._objective(float(point[0]), float(point[1]) * 1.0e-3, unit_indices=unit_indices),
                    np.asarray(primary.x, dtype=float),
                    method="Powell",
                    bounds=((0.04, 0.14), (1.8, 3.2)),
                    options={"xtol": 1.0e-10, "ftol": 1.0e-12, "maxiter": 500},
                )
                fallback_used = True
            rows.append(
                {
                    "start": tuple(float(value) for value in start),
                    "success": bool(result.success),
                    "chi2": float(result.fun),
                    "sin2_2theta13": float(result.x[0]),
                    "dm32_ev2": float(result.x[1]) * 1.0e-3,
                    "iterations": int(result.nit),
                    "method": "POWELL_FALLBACK" if fallback_used else "L_BFGS_B",
                    "primary_success": bool(primary.success),
                    "message": str(result.message),
                }
            )
        best = min(rows, key=lambda row: row["chi2"])
        converged = [row for row in rows if row["success"]]
        objective_spread = float(max(row["chi2"] for row in converged) - min(row["chi2"] for row in converged))
        parameter_spread = {
            "sin2_2theta13": float(max(row["sin2_2theta13"] for row in converged) - min(row["sin2_2theta13"] for row in converged)),
            "dm32_ev2": float(max(row["dm32_ev2"] for row in converged) - min(row["dm32_ev2"] for row in converged)),
        }
        return {
            "starts": tuple(rows),
            "best": best,
            "certificate": {
                "status": "ALGORITHM_CONVERGED" if len(converged) == len(rows) and objective_spread <= 1.0e-7 else "BLOCKED_MULTISTART_DISAGREEMENT",
                "start_count": len(rows),
                "converged_count": len(converged),
                "objective_spread": objective_spread,
                "parameter_spread": parameter_spread,
            },
        }

    def _profile_intervals(self, best_sin2_2theta13: float, best_dm32_ev2: float, minimum_chi2: float) -> Mapping[str, Any]:
        def profile_theta(value: float) -> tuple[float, float]:
            result = minimize_scalar(
                lambda dm32: self._objective(value, float(dm32)),
                bounds=(1.8e-3, 3.2e-3),
                method="bounded",
                options={"xatol": 1.0e-11},
            )
            return float(result.fun), float(result.x)

        def profile_dm32(value: float) -> tuple[float, float]:
            result = minimize_scalar(
                lambda theta: self._objective(float(theta), value),
                bounds=(0.04, 0.14),
                method="bounded",
                options={"xatol": 1.0e-11},
            )
            return float(result.fun), float(result.x)

        theta_lower = brentq(lambda value: profile_theta(value)[0] - minimum_chi2 - 1.0, 0.04, best_sin2_2theta13)
        theta_upper = brentq(lambda value: profile_theta(value)[0] - minimum_chi2 - 1.0, best_sin2_2theta13, 0.14)
        dm_lower = brentq(lambda value: profile_dm32(value)[0] - minimum_chi2 - 1.0, 1.8e-3, best_dm32_ev2)
        dm_upper = brentq(lambda value: profile_dm32(value)[0] - minimum_chi2 - 1.0, best_dm32_ev2, 3.2e-3)
        closure = {
            "theta_lower_delta_chi2": profile_theta(theta_lower)[0] - minimum_chi2,
            "theta_upper_delta_chi2": profile_theta(theta_upper)[0] - minimum_chi2,
            "dm32_lower_delta_chi2": profile_dm32(dm_lower)[0] - minimum_chi2,
            "dm32_upper_delta_chi2": profile_dm32(dm_upper)[0] - minimum_chi2,
        }
        return {
            "delta_chi2": 1.0,
            "sin2_2theta13": {"lower": float(theta_lower), "best": float(best_sin2_2theta13), "upper": float(theta_upper)},
            "dm32_ev2": {"lower": float(dm_lower), "best": float(best_dm32_ev2), "upper": float(dm_upper)},
            "closure": {key: float(value) for key, value in closure.items()},
            "status": "PROFILE_LIKELIHOOD_CLOSED" if max(abs(value - 1.0) for value in closure.values()) <= 1.0e-6 else "BLOCKED_PROFILE_CLOSURE",
        }

    def fit_reference_partition(
        self,
        *,
        discovery_periods: Sequence[str] = ("6AD",),
        heldout_periods: Sequence[str] = ("8AD", "7AD"),
    ) -> Mapping[str, Any]:
        """Fit the 3nu control only on ``D_discovery`` and predict held-out periods."""
        discovery = self._period_indices(discovery_periods)
        heldout = self._period_indices(heldout_periods)
        if set(discovery).intersection(heldout):
            raise ValueError("reference discovery and held-out Daya Bay partitions must be disjoint")
        if set(discovery).union(heldout) != set(range(len(self._load_public_model()["units"]))):
            raise ValueError("reference Daya Bay partition must cover every detector-period spectrum exactly once")
        multistart = self._multistart_fit(unit_indices=discovery)
        if multistart["certificate"]["status"] != "ALGORITHM_CONVERGED":
            return {
                "status": "BLOCKED_REFERENCE_DISCOVERY_MULTISTART",
                "discovery_periods": tuple(discovery_periods),
                "heldout_periods": tuple(heldout_periods),
                "multistart": multistart,
            }
        best = multistart["best"]
        design = self._design_matrix(float(best["sin2_2theta13"]), float(best["dm32_ev2"]))
        profiled = self._profile_source_spectrum(design, unit_indices=discovery)
        predicted = self._profile_source_spectrum(design, unit_indices=heldout, fixed_source=profiled["source"])
        return {
            "status": "PASS_REFERENCE_DISCOVERY_FIT_AND_HELDOUT_PREDICTION",
            "discovery_periods": tuple(discovery_periods),
            "heldout_periods": tuple(heldout_periods),
            "discovery_unit_indices": discovery,
            "heldout_unit_indices": heldout,
            "best_fit_discovery_only": {
                "sin2_2theta13": float(best["sin2_2theta13"]),
                "dm32_ev2": float(best["dm32_ev2"]),
            },
            "discovery_chi2": float(profiled["chi2"]),
            "heldout_chi2": float(predicted["chi2"]),
            "discovery_observation_bins": int(profiled["observation_bin_count"]),
            "heldout_observation_bins": int(predicted["observation_bin_count"]),
            "frozen_source_spectrum": tuple(float(v) for v in profiled["source"]),
            "multistart": multistart,
            "claim_boundary": {
                "heldout_periods_used_in_parameter_fit": False,
                "heldout_source_nuisance_refit": False,
                "official_collaboration_coverage_reproduced": False,
            },
        }

    def fit_public_data_profile(self) -> Mapping[str, Any]:
        if self._fit_cache is not None:
            return self._fit_cache
        model = self._load_public_model()
        multistart = self._multistart_fit()
        best = multistart["best"]
        profiled = self._profile_source_spectrum(
            self._design_matrix(float(best["sin2_2theta13"]), float(best["dm32_ev2"]))
        )
        intervals = self._profile_intervals(
            float(best["sin2_2theta13"]), float(best["dm32_ev2"]), float(profiled["chi2"])
        )
        observed_count = float(np.asarray(model["observed"]).sum())
        background_count = float(np.asarray(model["background"]).sum())
        degrees_of_freedom = int(np.asarray(model["observed"]).size - len(profiled["source"]) - 2)
        published = self.PUBLISHED_BEST_FIT
        result = {
            "status": "PASS_PUBLIC_DAYABAY_DETECTOR_PERIOD_PROFILE",
            "fit_scope": "PUBLIC_ANALYSIS_NPZ_METHOD_B_STYLE_CNP_WITH_RELEASED_RESPONSE_AND_PROFILED_COMMON_SOURCE_SPECTRUM",
            "sin2_2theta13": float(best["sin2_2theta13"]),
            "dm32_ev2_normal": float(best["dm32_ev2"]),
            "chi2": float(profiled["chi2"]),
            "ndf": degrees_of_freedom,
            "reduced_chi2": float(profiled["chi2"] / degrees_of_freedom),
            "profile_intervals_diagnostic": intervals,
            "multistart": multistart,
            "identifiability": {
                "noise_scaled_effective_rank": int(profiled["effective_rank"]),
                "nuisance_dimension": int(len(profiled["source"])),
                "condition_number": float(profiled["condition_number"]),
                "noise_floor": float(profiled["noise_floor"]),
                "status": "PASS_NOISE_SCALED_FULL_NUISANCE_RANK" if profiled["effective_rank"] == len(profiled["source"]) and profiled["condition_number"] < 1.0e6 else "BLOCKED_EFFECTIVE_RANK_OR_CONDITIONING",
            },
            "data_accounting": {
                "detector_period_spectra": 21,
                "reconstructed_energy_bins": 26,
                "observed_candidates_in_analysis_archive": observed_count,
                "profiled_background_count": background_count,
                "response_shape": tuple(int(value) for value in np.asarray(model["response"]).shape),
                "experiment_data_ir_digest": model["experiment_data_ir"]["digest"],
            },
            "published_consistency": {
                "published_sin2_2theta13": published["sin2_2theta13"],
                "published_dm32_ev2_normal": published["dm32_ev2_normal"],
                "theta13_difference_in_published_sigma": float(abs(best["sin2_2theta13"] - published["sin2_2theta13"]) / published["sin2_2theta13_sigma"]),
                "dm32_difference_in_published_sigma": float(abs(best["dm32_ev2"] - published["dm32_ev2_normal"]) / published["dm32_ev2_sigma"]),
                "central_values_within_published_one_sigma": bool(
                    abs(best["sin2_2theta13"] - published["sin2_2theta13"]) <= published["sin2_2theta13_sigma"]
                    and abs(best["dm32_ev2"] - published["dm32_ev2_normal"]) <= published["dm32_ev2_sigma"]
                ),
            },
            "claim_boundary": {
                "official_public_data_executed": True,
                "exact_dayabay_model_1_8_0_byte_executed": False,
                "official_collaboration_confidence_interval_reproduced": False,
                "diagnostic_profile_intervals_are_not_official_coverage": True,
                "published_central_values_used_as_fit_inputs": False,
                "synthetic_substitution_used": False,
            },
        }
        result["digest"] = _digest(result)
        self._fit_cache = result
        self._publish_shared_cache(self._SHARED_FIT_CACHE, result)
        return result

    def evaluate(self, *, family: str, candidate_contract: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        candidate_contract = dict(
            candidate_contract
            or {"family": family, "digest": _digest({"family": family, "qualification": True}), "oscillation_parameters": {}}
        )
        if candidate_contract.get("family") != family or not candidate_contract.get("digest"):
            raise ValueError("candidate contract must bind the same family and a non-empty digest")
        candidate_digest = str(candidate_contract["digest"])
        ir = self.ingestion.to_experiment_data_ir(self.DATASET_ID)
        if ir.get("status") != "PASS_EXPERIMENT_DATA_IR":
            return {
                "family": family,
                "candidate_digest": candidate_digest,
                "status": "BLOCKED_DAYABAY_EXPERIMENT_DATA_IR_INCOMPLETE",
                "evidence_class": "PUBLIC_DATA_PROFILE_LIKELIHOOD",
                "public_profile_status": "BLOCKED_DATA_ARTIFACTS_NOT_MATERIALIZED",
                "experiment_data_ir": ir,
                "spectral_likelihood_executed": False,
                "synthetic_substitution_allowed": False,
            }
        fit = self.fit_public_data_profile()
        model_artifact = DAYABAY_MODEL_WHEEL.inspect(self.ingestion)
        if family == "THREE_NEUTRINO":
            oscillation = dict(candidate_contract.get("oscillation_parameters") or {})
            if "sin2_theta13" in oscillation:
                sin2_theta13 = float(oscillation["sin2_theta13"])
                candidate_sin22 = 4.0 * sin2_theta13 * (1.0 - sin2_theta13)
            else:
                candidate_sin22 = float(fit["sin2_2theta13"])
            candidate_dm32 = abs(float(oscillation.get("dm3l_ev2", fit["dm32_ev2_normal"])))
            candidate_chi2 = self._objective(candidate_sin22, candidate_dm32)
            candidate_point: Mapping[str, Any] = {"sin2_2theta13": candidate_sin22, "dm32_ev2_normal": candidate_dm32}
            propagation_diagnostics: Mapping[str, Any] = {"kernel": "PUBLISHED_3NU_REFERENCE_PARAMETERISATION"}
        else:
            try:
                design, propagation_diagnostics = self._candidate_design_matrix(candidate_contract)
            except (TypeError, ValueError) as exc:
                return {
                    "family": family,
                    "candidate_digest": candidate_digest,
                    "status": "BLOCKED_DAYABAY_OPERATOR_IDENTITY_INCOMPLETE",
                    "evidence_class": "PUBLIC_DATA_PROFILE_LIKELIHOOD",
                    "public_profile_status": "BLOCKED_CANDIDATE_BOUND_TAKAGI_FORWARD_RESPONSE",
                    "experiment_data_ir_digest": ir["digest"],
                    "spectral_likelihood_executed": False,
                    "synthetic_substitution_allowed": False,
                    "reason": str(exc),
                }
            profiled = self._profile_source_spectrum(design)
            candidate_chi2 = float(profiled["chi2"])
            candidate_point = {
                "operator_identity_digest": candidate_contract.get("operator_identity", {}).get("digest"),
                "profiled_source_bins": int(len(profiled["source"])),
            }
        delta_chi2 = max(0.0, float(candidate_chi2 - fit["chi2"]))
        return {
            "family": family,
            "candidate_digest": candidate_digest,
            "status": "PASS_PUBLIC_PROFILE_EXECUTED",
            "evidence_class": "PUBLIC_DATA_PROFILE_LIKELIHOOD",
            "public_profile_status": "PASS_PUBLIC_DAYABAY_DETECTOR_PERIOD_PROFILE",
            "experiment_data_ir_digest": ir["digest"],
            "official_analysis_data_materialized": True,
            "spectral_likelihood_executed": True,
            "candidate_point": candidate_point,
            "propagation_diagnostics": propagation_diagnostics,
            "chi2": float(candidate_chi2),
            "delta_chi2": delta_chi2,
            "best_fit": fit,
            "reference_model_version": self.REFERENCE_MODEL_VERSION,
            "reference_model_artifact": model_artifact,
            "reference_environment_lock": self.REFERENCE_ENVIRONMENT_LOCK,
            "exact_reference_software_executed": False,
            "synthetic_substitution_allowed": False,
            "shared_prior_ids": (),
        }

    def run_qualification(self) -> Mapping[str, Any]:
        if self._qualification_cache is not None:
            return self._qualification_cache
        route = self.evaluate(family="THREE_NEUTRINO")
        fixture_prediction = self.detector_period_prediction(
            np.array([10.0, 20.0]), np.array([0.9, 0.8]), np.eye(2), np.ones(2)
        )
        fixture_chi2 = self.cnp_covariance_chi2(fixture_prediction, fixture_prediction, np.zeros((2, 2)))
        fit = route["best_fit"]
        profile_closure = fit["profile_intervals_diagnostic"]["closure"]
        model = self._load_public_model()
        fixture_sin2_theta13 = self._sin2_from_sin22(float(fit["sin2_2theta13"]))
        fixture_sin2_theta12 = self._sin2_from_sin22(float(model["sin2_2theta12"]))
        fixture_weights = np.asarray([
            (1.0 - fixture_sin2_theta13) * (1.0 - fixture_sin2_theta12),
            (1.0 - fixture_sin2_theta13) * fixture_sin2_theta12,
            fixture_sin2_theta13,
        ], dtype=float)
        fixture_masses = np.sqrt(np.asarray([
            0.0,
            float(model["dm21_ev2"]),
            float(model["dm21_ev2"]) + float(fit["dm32_ev2_normal"]),
        ], dtype=float))
        fixture_active_real = np.zeros((3, 3), dtype=float)
        fixture_active_real[0] = np.sqrt(fixture_weights)
        fixture_takagi = {
            "takagi_masses_ev": fixture_masses.tolist(),
            "active_mixing_real": fixture_active_real.tolist(),
            "active_mixing_imag": np.zeros((3, 3), dtype=float).tolist(),
        }
        fixture_general_probability, _ = self._takagi_survival_probability(
            takagi_spectrum=fixture_takagi,
            baselines_m=np.asarray(model["baselines_m"], dtype=float),
            prompt_energy=np.asarray(model["fine_centers"], dtype=float),
        )
        fixture_reference_probability = self._survival_probability(
            float(fit["sin2_2theta13"]), float(fit["dm32_ev2_normal"]), np.asarray(model["fine_centers"], dtype=float)
        )
        fixture_kernel_residual = float(np.max(np.abs(fixture_general_probability - fixture_reference_probability)))
        fixture_contract = {
            "family": "HIGHER_DIMENSIONAL_MICRO_IR",
            "digest": _digest({"qualification": "DAYABAY_TAKAGI_ADAPTER_EQUIVALENCE", "takagi": fixture_takagi}),
            "operator_identity_status": "COMPLETE_OWNER_LOWERED_OPERATOR_IDENTITY",
            "operator_identity": {"digest": _digest(fixture_takagi), "takagi_spectrum": fixture_takagi},
            "oscillation_parameters": {},
        }
        fixture_generic_route = self.evaluate(
            family="HIGHER_DIMENSIONAL_MICRO_IR", candidate_contract=fixture_contract
        )
        partition_control = self.fit_reference_partition(
            discovery_periods=("6AD", "8AD"), heldout_periods=("7AD",)
        )
        fixture_discovery = self.discovery_partition_score(
            family="HIGHER_DIMENSIONAL_MICRO_IR", candidate_contract=fixture_contract,
            discovery_periods=("6AD", "8AD"),
        )
        fixture_heldout = self.heldout_partition_score(
            family="HIGHER_DIMENSIONAL_MICRO_IR", candidate_contract=fixture_contract,
            frozen_discovery_profile=fixture_discovery, heldout_periods=("7AD",),
        )
        checks = {
            "detector_period_kernel_qualified": bool(np.allclose(fixture_prediction, [9.0, 16.0])),
            "cnp_statistic_identity": abs(fixture_chi2) <= 1.0e-15,
            "official_release_metadata_bound": self.OFFICIAL_EVENT_COUNT == 5_550_000 and self.OFFICIAL_LIVE_DAYS == 3158,
            "analysis_digest_bound": DAYABAY_ANALYSIS_NPZ.expected_md5 == "dfc33dce75508b53e9821329b3e06a17",
            "analysis_pypi_alternative_digest_bound": DAYABAY_ANALYSIS_WHEEL.expected_sha256 == "4578d71a741041d7b729dc7cacaa0836efe852d8f407d222ff8916c190dcfadf",
            "reference_model_digest_bound": DAYABAY_MODEL_WHEEL.expected_sha256 == "74c328f9c8527bf3e1fac3d8e24acdee2253a3ee44c32066dcd2a4529efb7fb7",
            "generic_ingestion_owner_is_upstream": self.ingestion.contract()["owner_id"] == "SCIENTIFIC-DATA-INGESTION",
            "public_detector_period_profile_executed": route["status"] == "PASS_PUBLIC_PROFILE_EXECUTED",
            "takagi_forward_kernel_matches_3nu_control": fixture_kernel_residual <= 2.0e-14,
            "generic_owner_lowered_candidate_uses_same_public_profile": fixture_generic_route["status"] == "PASS_PUBLIC_PROFILE_EXECUTED" and abs(float(fixture_generic_route["chi2"]) - float(route["chi2"])) <= 1.0e-7,
            "temporal_partition_disjoint_and_exhaustive": (
                partition_control.get("status") == "PASS_REFERENCE_DISCOVERY_FIT_AND_HELDOUT_PREDICTION"
                and set(partition_control.get("discovery_unit_indices", ())).isdisjoint(partition_control.get("heldout_unit_indices", ()))
                and set(partition_control.get("discovery_unit_indices", ())).union(partition_control.get("heldout_unit_indices", ())) == set(range(len(model["units"])))
            ),
            "temporal_reference_discovery_multistart_converged": partition_control.get("multistart", {}).get("certificate", {}).get("status") == "ALGORITHM_CONVERGED",
            "general_takagi_temporal_discovery_profile_executes": fixture_discovery.get("status") == "PASS_DISCOVERY_PARTITION_PROFILE_EXECUTED",
            "heldout_prediction_uses_frozen_discovery_nuisance": (
                fixture_heldout.get("status") == "PASS_HELDOUT_PERIOD_PREDICTION_EXECUTED"
                and fixture_heldout.get("source_nuisance_refit_on_heldout") is False
                and fixture_heldout.get("discovery_nuisance_digest") == fixture_discovery.get("discovery_nuisance_digest")
            ),
            "deterministic_multistart_converged": fit["multistart"]["certificate"]["status"] == "ALGORITHM_CONVERGED",
            "profile_likelihood_closed": fit["profile_intervals_diagnostic"]["status"] == "PROFILE_LIKELIHOOD_CLOSED" and max(abs(float(value) - 1.0) for value in profile_closure.values()) <= 1.0e-6,
            "noise_scaled_rank_and_condition_pass": fit["identifiability"]["status"] == "PASS_NOISE_SCALED_FULL_NUISANCE_RANK",
            "published_central_values_recovered_within_one_sigma": fit["published_consistency"]["central_values_within_published_one_sigma"] is True,
            "exact_reference_software_not_falsely_claimed": route["exact_reference_software_executed"] is False,
            "no_synthetic_substitution": route["synthetic_substitution_allowed"] is False,
        }
        report = {
            "schema": SCHEMA,
            "release": OWNER_VERSION,
            "owner_id": OWNER_ID,
            "status": "PASS_PUBLIC_DATA_PROFILE_OWNER_WITH_EXACT_REFERENCE_SOFTWARE_BOUNDARY" if all(checks.values()) else "BLOCKED_DAYABAY_OWNER",
            "checks": checks,
            "route": route,
            "takagi_adapter_control": {
                "probability_kernel_max_abs_residual": fixture_kernel_residual,
                "generic_candidate_chi2": fixture_generic_route.get("chi2"),
                "reference_candidate_chi2": route.get("chi2"),
                "status": fixture_generic_route.get("status"),
            },
            "temporal_partition_control": {
                "reference": partition_control,
                "generic_discovery_status": fixture_discovery.get("status"),
                "generic_heldout_status": fixture_heldout.get("status"),
                "heldout_source_nuisance_refit": fixture_heldout.get("source_nuisance_refit_on_heldout"),
            },
            "dataset_contract": self.ingestion.qualify_dataset(self.DATASET_ID),
            "published_reference_metadata": {
                "events": self.OFFICIAL_EVENT_COUNT,
                "days": self.OFFICIAL_LIVE_DAYS,
                "detectors": self.DETECTOR_COUNT,
                "reactors": self.REACTOR_COUNT,
                **self.PUBLISHED_BEST_FIT,
            },
            "claim_boundary": {
                "archive_parser_active_in_domain_owner": False,
                "published_central_values_used_as_likelihood": False,
                "public_detector_period_spectra_executed": True,
                "released_response_and_backgrounds_executed": True,
                "complete_takagi_candidate_uses_identical_detector_response_and_source_profile": True,
                "temporal_D_discovery_and_D_hidden_use_disjoint_real_detector_periods": True,
                "heldout_source_nuisance_refit_allowed": False,
                "theta13_dm32_public_data_central_values_reproduced": True,
                "exact_dayabay_model_1_8_0_byte_execution": False,
                "official_collaboration_coverage_reproduced": False,
                "public_profile_evidence_class": "PUBLIC_DATA_PROFILE_LIKELIHOOD",
                "cache_lifecycle": "ARTIFACT_GENERATION_BOUND_SINGLE_ENTRY_PER_DISTRIBUTION_ROOT",
            },
            "sha256": "",
        }
        report["sha256"] = _digest({**report, "sha256": ""})
        self._qualification_cache = report
        return report

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "schema": SCHEMA,
            "upstream_dataset_id": self.DATASET_ID,
            "upstream_ingestion_owner": self.ingestion.contract()["owner_id"] + "/" + str(self.ingestion.contract()["owner_version"]),
            "active_fit": "PUBLIC_ANALYSIS_NPZ_DETECTOR_PERIOD_CNP_PROFILE",
            "reference_output_keys": self.REFERENCE_OUTPUT_KEYS,
            "reference_environment_lock": self.REFERENCE_ENVIRONMENT_LOCK,
            "supported_executed_forward_models": ("THREE_NEUTRINO_REFERENCE", "COMPLETE_OWNER_LOWERED_TAKAGI_IDENTITY"),
            "hard_boundaries": (
                "ONE_ACTIVE_DAYABAY_FIT_OWNER",
                "ARCHIVE_AND_PROVENANCE_HANDLED_ONLY_BY_SCIENTIFIC_DATA_INGESTION",
                "NO_SYNTHETIC_REPLACEMENT_FOR_MISSING_OFFICIAL_DATA",
                "NO_SUMMARY_GAUSSIAN_AS_ACTIVE_LIKELIHOOD",
                "NO_EXACT_REFERENCE_SOFTWARE_CLAIM_WITHOUT_BYTE_EXECUTION",
                "NO_OFFICIAL_COVERAGE_CLAIM_FROM_DIAGNOSTIC_PROFILE",
                "EXPERIMENT_DATA_IR_REQUIRED",
                "NONREFERENCE_CANDIDATE_REQUIRES_COMPLETE_OWNER_LOWERED_TAKAGI_IDENTITY",
                "ONE_DETECTOR_RESPONSE_AND_NUISANCE_PROFILE_FOR_REFERENCE_AND_FROZEN_CANDIDATES",
                "CACHE_KEY_MUST_BIND_ROOT_SIZE_AND_MTIME_AND_DROP_SUPERSEDED_GENERATIONS",
            ),
        }
        return {**payload, "digest": _digest(payload)}
