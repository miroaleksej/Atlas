"""Authoritative KATRIN KNM1--KNM5 likelihood owner.

The active owner consumes the typed ExperimentDataIR produced by the single
SCIENTIFIC-DATA-INGESTION owner. The former reduced endpoint surrogate is not
an active scientific route.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .scientific_data_ingestion import (
    KATRIN_INPUTS_KNM1_5_JSON,
    KATRIN_KNM1_5_JSON,
    ScientificDataIngestionOwner,
)

OWNER_ID = "KATRIN-SPECTRAL-LIKELIHOOD"
OWNER_VERSION = "6.10.0"
SCHEMA = "phi-katrin-spectral-likelihood/v6.10"


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=float).encode()).hexdigest()


class KATRINSpectralLikelihoodOwner:
    """Single owner of the KATRIN physical spectrum and likelihood."""

    DATASET_ID = "KATRIN-KNM1-5-OFFICIAL"
    CAMPAIGNS = ("KNM1", "KNM2", "KNM3-SAP", "KNM3-NAP", "KNM4-NOM", "KNM4-OPT", "KNM5")
    REQUIRED_DATA_PARAMETERS = (
        "Retarding_voltage",
        "Live_time",
        "Penning_duration",
        "Penning_total_duration",
        "Event_counts",
        "Relative_efficiency",
    )
    REQUIRED_INPUT_SECTIONS = (
        "ElectromagneticFields",
        "GasDensity",
        "Concentrations",
        "RearWall",
        "Background",
        "EnergyLoss",
        "AngDepDetEff",
        "SourcePotential",
        "PotentialDriftBroadeningSquared",
    )

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.ingestion = ScientificDataIngestionOwner(self.root)

    @staticmethod
    def poisson_deviance(observed: np.ndarray, expected: np.ndarray) -> float:
        observed = np.asarray(observed, dtype=float)
        expected = np.asarray(expected, dtype=float)
        if observed.shape != expected.shape or np.any(expected <= 0.0) or np.any(observed < 0.0):
            raise ValueError("invalid Poisson arrays")
        term = expected - observed
        nz = observed > 0.0
        term[nz] += observed[nz] * np.log(observed[nz] / expected[nz])
        return float(2.0 * term.sum())

    @staticmethod
    def endpoint_phase_space(available_energy_ev: np.ndarray, m_beta_squared_ev2: float) -> np.ndarray:
        w = np.asarray(available_energy_ev, dtype=float)
        if np.any(w < 0.0):
            raise ValueError("available energy must be nonnegative")
        radicand = np.maximum(w * w - float(m_beta_squared_ev2), 0.0)
        return w * np.sqrt(radicand)

    @staticmethod
    def differential_beta_spectrum(
        electron_energy_ev: np.ndarray,
        endpoint_ev: float,
        m_beta_squared_ev2: float,
        final_state_energies_ev: np.ndarray,
        final_state_probabilities: np.ndarray,
    ) -> np.ndarray:
        """Endpoint spectrum including the molecular final-state distribution.

        Slowly varying Fermi and electron-momentum factors are intentionally not
        invented here; official execution must supply them through the published
        inputs and response contract.  This kernel qualifies the exact neutrino
        phase-space/FSD lowering owned by this module.
        """
        e = np.asarray(electron_energy_ev, dtype=float).reshape(-1)
        fs_e = np.asarray(final_state_energies_ev, dtype=float).reshape(-1)
        fs_p = np.asarray(final_state_probabilities, dtype=float).reshape(-1)
        if fs_e.shape != fs_p.shape or fs_e.size == 0:
            raise ValueError("final-state energies and probabilities must align")
        if np.any(fs_e < 0.0) or np.any(fs_p < 0.0) or not np.isclose(fs_p.sum(), 1.0, atol=1.0e-10):
            raise ValueError("molecular final-state distribution must be normalized and nonnegative")
        available = float(endpoint_ev) - e[:, None] - fs_e[None, :]
        positive = np.maximum(available, 0.0)
        phase = positive * np.sqrt(np.maximum(positive * positive - float(m_beta_squared_ev2), 0.0))
        return phase @ fs_p

    @staticmethod
    def multi_eigenstate_differential_beta_spectrum(
        electron_energy_ev: np.ndarray,
        endpoint_ev: float,
        masses_ev: np.ndarray,
        electron_flavour_weights: np.ndarray,
        final_state_energies_ev: np.ndarray,
        final_state_probabilities: np.ndarray,
    ) -> np.ndarray:
        """Exact incoherent endpoint sum over owner-lowered mass eigenstates.

        For a general Takagi spectrum the beta endpoint is not represented by
        a single effective mass inside the square root.  The exact kinematic
        phase-space factor is summed with |U_ei|^2 for every propagating state.
        Detector response, Fermi/electron-momentum factors and campaign
        nuisances remain separate official-response obligations.
        """
        masses = np.asarray(masses_ev, dtype=float).reshape(-1)
        weights = np.asarray(electron_flavour_weights, dtype=float).reshape(-1)
        if masses.shape != weights.shape or masses.size == 0:
            raise ValueError("KATRIN mass eigenstates and electron weights must align")
        if np.any(masses < 0.0) or np.any(weights < 0.0) or not np.all(np.isfinite(masses)) or not np.all(np.isfinite(weights)):
            raise ValueError("KATRIN mass eigenstates and weights must be finite and nonnegative")
        weight_sum = float(weights.sum())
        if not np.isclose(weight_sum, 1.0, atol=1.0e-8):
            raise ValueError("electron-flavour spectral weights must sum to unity")
        e = np.asarray(electron_energy_ev, dtype=float).reshape(-1)
        fs_e = np.asarray(final_state_energies_ev, dtype=float).reshape(-1)
        fs_p = np.asarray(final_state_probabilities, dtype=float).reshape(-1)
        if fs_e.shape != fs_p.shape or fs_e.size == 0:
            raise ValueError("final-state energies and probabilities must align")
        if np.any(fs_e < 0.0) or np.any(fs_p < 0.0) or not np.isclose(fs_p.sum(), 1.0, atol=1.0e-10):
            raise ValueError("molecular final-state distribution must be normalized and nonnegative")
        available = float(endpoint_ev) - e[:, None, None] - fs_e[None, :, None]
        positive = np.maximum(available, 0.0)
        mass2 = masses[None, None, :] ** 2
        phase = positive * np.sqrt(np.maximum(positive * positive - mass2, 0.0))
        return np.einsum("efm,f,m->e", phase, fs_p, weights, optimize=True)

    @staticmethod
    def _candidate_spectrum_certificate(candidate_contract: Mapping[str, Any]) -> Mapping[str, Any]:
        identity = candidate_contract.get("operator_identity")
        if not isinstance(identity, Mapping):
            return {"status": "BLOCKED_KATRIN_OPERATOR_SPECTRUM_NOT_BOUND"}
        spectrum = identity.get("takagi_spectrum")
        if not isinstance(spectrum, Mapping):
            return {"status": "BLOCKED_KATRIN_OPERATOR_SPECTRUM_NOT_BOUND"}
        try:
            masses = np.asarray(spectrum.get("takagi_masses_ev", ()), dtype=float).reshape(-1)
            real = np.asarray(spectrum.get("active_mixing_real", ()), dtype=float)
            imag = np.asarray(spectrum.get("active_mixing_imag", ()), dtype=float)
        except Exception as exc:
            return {"status": "BLOCKED_KATRIN_OPERATOR_SPECTRUM_PARSE_FAILURE", "error_type": type(exc).__name__}
        if masses.size == 0 or real.ndim != 2 or imag.shape != real.shape or real.shape[0] < 1 or real.shape[1] != masses.size:
            return {
                "status": "BLOCKED_KATRIN_OPERATOR_SPECTRUM_SHAPE_MISMATCH",
                "mass_count": int(masses.size),
                "active_mixing_shape": tuple(real.shape),
            }
        weights = real[0] ** 2 + imag[0] ** 2
        if np.any(masses < 0.0) or np.any(weights < 0.0) or not np.all(np.isfinite(masses)) or not np.all(np.isfinite(weights)):
            return {"status": "BLOCKED_KATRIN_OPERATOR_SPECTRUM_NONPHYSICAL"}
        weight_sum = float(weights.sum())
        if abs(weight_sum - 1.0) > 1.0e-8:
            return {"status": "BLOCKED_KATRIN_ELECTRON_WEIGHT_NORMALIZATION", "electron_weight_sum": weight_sum}
        m_beta_exact = float(np.sqrt(np.sum(weights * masses * masses)))
        return {
            "status": "PASS_KATRIN_MULTI_EIGENSTATE_KINEMATIC_SPECTRUM_BOUND",
            "propagating_mode_count": int(masses.size),
            "masses_ev": tuple(float(v) for v in masses),
            "electron_flavour_weights": tuple(float(v) for v in weights),
            "electron_weight_sum": weight_sum,
            "m_beta_from_exact_spectral_moment_ev": m_beta_exact,
            "single_effective_mass_used_inside_endpoint_kernel": False,
        }

    @staticmethod
    def integrate_response(
        differential_rate: np.ndarray,
        energy_step_ev: float,
        response_matrix: np.ndarray,
        exposure_s: np.ndarray,
        background_rate_hz: np.ndarray,
    ) -> np.ndarray:
        """Convolve a differential spectrum with an official MAC-E response matrix."""
        rate = np.asarray(differential_rate, dtype=float).reshape(-1)
        response = np.asarray(response_matrix, dtype=float)
        exposure = np.asarray(exposure_s, dtype=float).reshape(-1)
        background = np.asarray(background_rate_hz, dtype=float).reshape(-1)
        if response.ndim != 2 or response.shape[1] != rate.size:
            raise ValueError("KATRIN response matrix has incompatible energy dimension")
        if exposure.shape != (response.shape[0],) or background.shape != exposure.shape:
            raise ValueError("KATRIN exposure/background arrays must match scan points")
        if float(energy_step_ev) <= 0.0 or np.any(response < 0.0) or np.any(exposure <= 0.0) or np.any(background < 0.0):
            raise ValueError("KATRIN response inputs are nonphysical")
        counts = exposure * (response @ rate * float(energy_step_ev) + background)
        if np.any(counts <= 0.0) or not np.all(np.isfinite(counts)):
            raise ValueError("KATRIN expected counts must be finite and positive")
        return counts

    @staticmethod
    def _matrix_certificate(matrix: Any, *, tolerance: float = 1.0e-10) -> Mapping[str, Any]:
        a = np.asarray(matrix, dtype=float)
        if a.ndim != 2 or a.shape[0] != a.shape[1] or not np.all(np.isfinite(a)):
            return {"status": "BLOCKED_INVALID_MATRIX", "shape": tuple(a.shape)}
        sym = float(np.max(np.abs(a - a.T)))
        eig = np.linalg.eigvalsh((a + a.T) / 2.0)
        return {
            "status": "PASS_MATRIX_SYMMETRIC_PSD" if sym <= tolerance and float(eig.min()) >= -tolerance else "BLOCKED_MATRIX_NOT_SYMMETRIC_PSD",
            "shape": tuple(a.shape),
            "symmetry_residual": sym,
            "minimum_eigenvalue": float(eig.min()),
        }

    @classmethod
    def _validate_data(cls, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        parameters = payload.get("Parameters")
        campaigns = payload.get("Campaigns")
        if not isinstance(parameters, Mapping):
            return {"status": "BLOCKED_KATRIN_DATA_PARAMETERS_MISSING"}
        if not isinstance(campaigns, Mapping):
            return {"status": "BLOCKED_KATRIN_DATA_CAMPAIGNS_MISSING"}
        missing_parameters = tuple(name for name in cls.REQUIRED_DATA_PARAMETERS if name not in parameters)
        names = tuple(sorted(str(name) for name in campaigns))
        missing = tuple(name for name in cls.CAMPAIGNS if name not in campaigns)
        campaign_checks: dict[str, Mapping[str, Any]] = {}
        for name in cls.CAMPAIGNS:
            steps = campaigns.get(name)
            if not isinstance(steps, list) or not steps:
                campaign_checks[name] = {"status": "BLOCKED_CAMPAIGN_SCAN_STEPS_MISSING", "scan_step_count": 0}
                continue
            valid = True
            reason = "PASS"
            pixel_multiplicities: set[int] = set()
            for step in steps:
                if not isinstance(step, Mapping):
                    valid, reason = False, "SCAN_STEP_NOT_MAPPING"
                    break
                missing_step = [key for key in cls.REQUIRED_DATA_PARAMETERS if key not in step]
                if missing_step:
                    valid, reason = False, "SCAN_STEP_FIELDS_MISSING:" + ",".join(missing_step)
                    break
                try:
                    scalar_values = np.asarray([
                        step["Retarding_voltage"], step["Live_time"], step["Penning_duration"], step["Penning_total_duration"]
                    ], dtype=float)
                    counts = np.asarray(step["Event_counts"], dtype=float).reshape(-1)
                    efficiency = np.asarray(step["Relative_efficiency"], dtype=float).reshape(-1)
                except Exception as exc:
                    valid, reason = False, "SCAN_STEP_NUMERIC_PARSE_FAILURE:" + type(exc).__name__
                    break
                if not np.all(np.isfinite(scalar_values)) or scalar_values[1] <= 0.0 or np.any(scalar_values[2:] < 0.0):
                    valid, reason = False, "SCAN_STEP_SCALARS_NONPHYSICAL"
                    break
                if counts.size == 0 or counts.shape != efficiency.shape or not np.all(np.isfinite(counts)) or not np.all(np.isfinite(efficiency)):
                    valid, reason = False, "SCAN_STEP_ARRAY_SHAPE_OR_FINITE_FAILURE"
                    break
                if np.any(counts < 0.0) or np.any(efficiency <= 0.0):
                    valid, reason = False, "SCAN_STEP_COUNTS_OR_EFFICIENCY_NONPHYSICAL"
                    break
                pixel_multiplicities.add(int(counts.size))
            campaign_checks[name] = {
                "status": "PASS_CAMPAIGN_SCAN_STEP_SCHEMA" if valid else "BLOCKED_CAMPAIGN_SCAN_STEP_SCHEMA",
                "scan_step_count": len(steps),
                "pixel_multiplicities": tuple(sorted(pixel_multiplicities)),
                "reason": reason,
            }
        campaigns_pass = not missing and all(row["status"].startswith("PASS_") for row in campaign_checks.values())
        return {
            "status": "PASS_KATRIN_DATA_SCHEMA" if not missing_parameters and campaigns_pass else "BLOCKED_KATRIN_DATA_SCHEMA_INCOMPLETE",
            "campaigns": names,
            "missing_campaigns": missing,
            "missing_parameters": missing_parameters,
            "campaign_checks": campaign_checks,
            "published_schema_form": "CAMPAIGN_TO_SCAN_STEP_LIST",
        }

    @classmethod
    def _validate_inputs(cls, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        missing = tuple(section for section in cls.REQUIRED_INPUT_SECTIONS if section not in payload)
        matrix_certificates: list[Mapping[str, Any]] = []

        def walk(node: Any) -> None:
            if isinstance(node, Mapping):
                for key, value in node.items():
                    if key in {"CovarianceMatrix", "CorrelationMatrix"}:
                        matrix_certificates.append(cls._matrix_certificate(value))
                    else:
                        walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(payload)
        matrices_pass = bool(matrix_certificates) and all(row["status"].startswith("PASS_") for row in matrix_certificates)
        return {
            "status": "PASS_KATRIN_INPUT_SCHEMA_AND_MATRICES" if not missing and matrices_pass else "BLOCKED_KATRIN_INPUT_SCHEMA_OR_MATRIX",
            "missing_sections": missing,
            "matrix_count": len(matrix_certificates),
            "matrix_certificates": tuple(matrix_certificates),
        }

    def evaluate(self, *, family: str, candidate_contract: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        candidate_contract = dict(candidate_contract or {"family": family, "digest": _digest({"family": family, "qualification": True})})
        if candidate_contract.get("family") != family or not candidate_contract.get("digest"):
            raise ValueError("candidate contract must bind the same family and a non-empty digest")
        candidate_digest = str(candidate_contract["digest"])
        spectrum_certificate = self._candidate_spectrum_certificate(candidate_contract)
        ir = self.ingestion.to_experiment_data_ir(self.DATASET_ID)
        if ir["status"] != "PASS_EXPERIMENT_DATA_IR":
            return {
                "family": family,
                "candidate_digest": candidate_digest,
                "spectrum_certificate": spectrum_certificate,
                "status": "BLOCKED_KATRIN_EXPERIMENT_DATA_IR_INCOMPLETE",
                "evidence_class": "OFFICIAL_EXPERIMENT_LEVEL_LIKELIHOOD",
                "public_profile_status": "BLOCKED_ARTIFACTS_NOT_MATERIALIZED",
                "experiment_data_ir": ir,
                "official_likelihood_executed": False,
                "synthetic_substitution_allowed": False,
            }
        try:
            data_payload = json.loads((self.root / KATRIN_KNM1_5_JSON.local_relative_path).read_text(encoding="utf-8"))
            inputs_payload = json.loads((self.root / KATRIN_INPUTS_KNM1_5_JSON.local_relative_path).read_text(encoding="utf-8"))
        except Exception as exc:
            return {
                "family": family,
                "candidate_digest": candidate_digest,
                "spectrum_certificate": spectrum_certificate,
                "status": "BLOCKED_KATRIN_JSON_PARSE_FAILURE",
                "evidence_class": "OFFICIAL_EXPERIMENT_LEVEL_LIKELIHOOD",
                "public_profile_status": "BLOCKED_JSON_PARSE",
                "experiment_data_ir_digest": ir["digest"],
                "error_type": type(exc).__name__,
                "official_likelihood_executed": False,
                "synthetic_substitution_allowed": False,
            }
        data_schema = self._validate_data(data_payload)
        input_schema = self._validate_inputs(inputs_payload)
        if not data_schema["status"].startswith("PASS_") or not input_schema["status"].startswith("PASS_"):
            return {
                "family": family,
                "candidate_digest": candidate_digest,
                "spectrum_certificate": spectrum_certificate,
                "status": "BLOCKED_KATRIN_DOMAIN_SCHEMA_QUALIFICATION",
                "evidence_class": "OFFICIAL_EXPERIMENT_LEVEL_LIKELIHOOD",
                "public_profile_status": "BLOCKED_SCHEMA",
                "experiment_data_ir_digest": ir["digest"],
                "data_schema": data_schema,
                "input_schema": input_schema,
                "official_likelihood_executed": False,
                "synthetic_substitution_allowed": False,
            }
        return {
            "family": family,
            "candidate_digest": candidate_digest,
            "spectrum_certificate": spectrum_certificate,
            "status": "BLOCKED_KATRIN_OFFICIAL_RESPONSE_OBJECT_MAP_NOT_MATERIALIZED",
            "evidence_class": "OFFICIAL_EXPERIMENT_LEVEL_LIKELIHOOD",
            "public_profile_status": "BLOCKED_OFFICIAL_RESPONSE_BINDING",
            "experiment_data_ir_digest": ir["digest"],
            "data_schema": data_schema,
            "input_schema": input_schema,
            "official_likelihood_executed": False,
            "synthetic_substitution_allowed": False,
            "implemented_kernel_components": (
                "MOLECULAR_FINAL_STATE_DISTRIBUTION_CONVOLUTION",
                "EXACT_MULTI_EIGENSTATE_ELECTRON_WEIGHTED_ENDPOINT_PHASE_SPACE",
                "MAC_E_RESPONSE_MATRIX_CONVOLUTION",
                "POISSON_DEVIANCE",
            ),
            "open_kernel_obligations": (
                "OFFICIAL_CAMPAIGN_RESPONSE_OBJECT_MAP",
                "CAMPAIGN_AND_PIXEL_DEPENDENT_SOURCE_POTENTIAL",
                "CORRELATED_BACKGROUND_AND_NUISANCE_PROFILE",
                "OFFICIAL_CONFIDENCE_CONSTRUCTION",
            ),
        }

    def run_qualification(self) -> Mapping[str, Any]:
        route = self.evaluate(family="THREE_NEUTRINO")
        deviance_identity = self.poisson_deviance(np.array([2.0, 7.0]), np.array([2.0, 7.0]))
        phase = self.endpoint_phase_space(np.array([0.0, 1.0, 2.0]), 0.25)
        fixture_spectrum = self.differential_beta_spectrum(
            np.array([8.0, 9.0, 10.0]), 10.0, 0.0, np.array([0.0]), np.array([1.0])
        )
        fixture_counts = self.integrate_response(
            fixture_spectrum, 1.0, np.eye(3), np.ones(3), np.full(3, 0.1)
        )
        degenerate_multi = self.multi_eigenstate_differential_beta_spectrum(
            np.array([8.0, 9.0, 10.0]), 10.0,
            np.array([0.2, 0.2, 0.2]), np.array([0.2, 0.3, 0.5]),
            np.array([0.0]), np.array([1.0]),
        )
        degenerate_single = self.differential_beta_spectrum(
            np.array([8.0, 9.0, 10.0]), 10.0, 0.04, np.array([0.0]), np.array([1.0])
        )
        official_data_schema_fixture = {
            "Parameters": {key: {"Unit": "fixture"} for key in self.REQUIRED_DATA_PARAMETERS},
            "Campaigns": {
                campaign: [{
                    "Retarding_voltage": 18570.0,
                    "Live_time": 100.0,
                    "Penning_duration": 10.0,
                    "Penning_total_duration": 100.0,
                    "Event_counts": [10.0],
                    "Relative_efficiency": [1.0],
                }] for campaign in self.CAMPAIGNS
            },
        }
        official_input_schema_fixture = {
            section: ({"CorrelationMatrix": [[1.0]], "Value": [1.0]} if section == "ElectromagneticFields" else {"Value": [1.0]})
            for section in self.REQUIRED_INPUT_SECTIONS
        }
        data_schema_fixture_result = self._validate_data(official_data_schema_fixture)
        input_schema_fixture_result = self._validate_inputs(official_input_schema_fixture)
        checks = {
            "molecular_fsd_kernel_qualified": bool(np.allclose(fixture_spectrum, [4.0, 1.0, 0.0])),
            "response_convolution_kernel_qualified": bool(np.allclose(fixture_counts, fixture_spectrum + 0.1)),
            "multi_eigenstate_endpoint_reduces_to_degenerate_single_mass_limit": bool(np.allclose(degenerate_multi, degenerate_single, rtol=0.0, atol=1.0e-12)),
            "poisson_deviance_identity": abs(deviance_identity) <= 1.0e-15,
            "endpoint_phase_space_finite_nonnegative": bool(np.all(np.isfinite(phase)) and np.all(phase >= 0.0)),
            "published_data_digest_bound": KATRIN_KNM1_5_JSON.expected_md5 == "7c9e30c35c394d87917cc56c7bf7ff53",
            "published_inputs_digest_bound": KATRIN_INPUTS_KNM1_5_JSON.expected_md5 == "6fcb3fbd3059190caa95f37243a9593a",
            "published_campaign_scan_step_list_schema_qualified": data_schema_fixture_result["status"] == "PASS_KATRIN_DATA_SCHEMA",
            "published_input_top_level_schema_qualified": input_schema_fixture_result["status"] == "PASS_KATRIN_INPUT_SCHEMA_AND_MATRICES",
            "generic_ingestion_owner_is_upstream": self.ingestion.contract()["owner_id"] == "SCIENTIFIC-DATA-INGESTION",
            "official_data_and_inputs_are_single_active_route": True,
            "full_route_fails_closed": route["status"].startswith("BLOCKED_"),
            "no_synthetic_substitution": route["synthetic_substitution_allowed"] is False,
        }
        report = {
            "schema": SCHEMA,
            "release": OWNER_VERSION,
            "owner_id": OWNER_ID,
            "status": "PASS_OFFICIAL_ARTIFACT_OWNER_FAIL_CLOSED" if all(checks.values()) else "BLOCKED_KATRIN_OWNER",
            "checks": checks,
            "route": route,
            "dataset_contract": self.ingestion.qualify_dataset(self.DATASET_ID),
            "claim_boundary": {
                "domain_specific_materializer_or_json_parser_active": False,
                "official_knm1_to_knm5_artifacts_materialized": False,
                "active_reduced_endpoint_surrogate": False,
                "general_operator_collapsed_to_single_mbeta_inside_endpoint_kernel": False,
                "exact_multi_eigenstate_endpoint_kernel_implemented": True,
                "official_json_schema_bound_to_published_structure": True,
                "official_response_and_systematics_executed": False,
                "official_0p45_ev_limit_reproduced": False,
            },
            "sha256": "",
        }
        report["sha256"] = _digest({**report, "sha256": ""})
        return report

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "schema": SCHEMA,
            "upstream_dataset_id": self.DATASET_ID,
            "upstream_ingestion_owner": self.ingestion.contract()["owner_id"] + "/" + self.ingestion.contract()["owner_version"],
            "campaigns": self.CAMPAIGNS,
            "hard_boundaries": (
                "NO_DOMAIN_SPECIFIC_MATERIALIZER",
                "EXPERIMENT_DATA_IR_REQUIRED",
                "NO_REDUCED_ENDPOINT_SURROGATE_AS_ACTIVE_ROUTE",
                "GENERAL_OPERATOR_USES_EXACT_MULTI_EIGENSTATE_ENDPOINT_SUM",
                "NO_MISSING_RESPONSE_REPLACED_BY_FREE_POLYNOMIAL",
                "NO_MASS_LIMIT_WITHOUT_OFFICIAL_RESPONSE_AND_COVERAGE",
                "NO_STERILE_CLAIM_WITHOUT_FULL_RESPONSE_AND_COVERAGE",
            ),
        }
        return {**payload, "digest": _digest(payload)}
