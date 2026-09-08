"""Authoritative Super-Kamiokande solar-neutrino profile owner.

The 2026 release supplies solar-angle ROOT histograms and published
survival-probability intervals.  It does not by itself define a general
cross-experiment covariance likelihood for arbitrary BSM microphysics.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .scientific_data_ingestion import ScientificDataIngestionOwner, SUPERK_SOLAR_RELEASE

OWNER_ID = "SUPERK-SOLAR-LIKELIHOOD"
OWNER_VERSION = "6.10.0"
SCHEMA = "phi-superk-solar-likelihood/v6.10"


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=float).encode()).hexdigest()


class SuperKSolarLikelihoodOwner:
    DATASET_ID = "SUPERK-SOLAR-SKIV-2026"
    ROOT_HISTOGRAM_COUNT = 51

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.ingestion = ScientificDataIngestionOwner(self.root)

    @staticmethod
    def angular_profile_deviance(observed: np.ndarray, signal: np.ndarray, background: np.ndarray) -> float:
        """Poisson deviance for a published angular signal/background histogram."""
        n = np.asarray(observed, dtype=float).reshape(-1)
        s = np.asarray(signal, dtype=float).reshape(-1)
        b = np.asarray(background, dtype=float).reshape(-1)
        if n.shape != s.shape or n.shape != b.shape or np.any(n < 0.0) or np.any(s < 0.0) or np.any(b < 0.0):
            raise ValueError("invalid Super-K solar histogram arrays")
        mu = s + b
        if np.any(mu <= 0.0):
            raise ValueError("solar expected histogram must be positive")
        term = mu - n
        nz = n > 0.0
        term[nz] += n[nz] * np.log(n[nz] / mu[nz])
        return float(2.0 * term.sum())

    def evaluate(self, *, family: str, candidate_contract: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        candidate_contract = dict(candidate_contract or {"family": family, "digest": _digest({"family": family, "qualification": True})})
        if candidate_contract.get("family") != family or not candidate_contract.get("digest"):
            raise ValueError("candidate contract must bind the same family and a non-empty digest")
        candidate_digest = str(candidate_contract["digest"])
        if family != "THREE_NEUTRINO":
            return {
                "family": family,
                "candidate_digest": candidate_digest,
                "status": "BLOCKED_SUPERK_SOLAR_GENERAL_OPERATOR_RESPONSE_COVARIANCE_UNAVAILABLE",
                "evidence_class": "INFORMATION_THEORETIC_LIMIT",
                "public_profile_status": "ARBITRARY_BSM_UNDERDETERMINED",
                "dataset_contract": self.ingestion.qualify_dataset(self.DATASET_ID),
                "missing_for_global_likelihood": (
                    "FULL_BIN_TO_MICROPHYSICS_RESPONSE",
                    "CROSS_BIN_COVARIANCE",
                    "SOLAR_FLUX_AND_NUCLEAR_INPUT_NUISANCE_CONTRACT",
                ),
                "chi2": None,
                "official_likelihood_executed": False,
                "synthetic_substitution_allowed": False,
            }
        ir = self.ingestion.to_experiment_data_ir(self.DATASET_ID)
        if ir["status"] != "PASS_EXPERIMENT_DATA_IR":
            return {
                "family": family,
                "candidate_digest": candidate_digest,
                "status": "BLOCKED_SUPERK_SOLAR_EXPERIMENT_DATA_IR_INCOMPLETE",
                "evidence_class": "PUBLISHED_ANGULAR_PROFILE",
                "public_profile_status": "BLOCKED_ARTIFACT_NOT_MATERIALIZED",
                "experiment_data_ir": ir,
                "chi2": None,
                "official_likelihood_executed": False,
                "synthetic_substitution_allowed": False,
            }
        return {
            "family": family,
            "candidate_digest": candidate_digest,
            "status": "BLOCKED_SUPERK_SOLAR_RESPONSE_COVARIANCE_AND_FLUX_MODEL_REQUIRED",
            "evidence_class": "PUBLISHED_ANGULAR_PROFILE",
            "public_profile_status": "PUBLISHED_PROFILE_EXECUTABLE_GLOBAL_COVARIANCE_BLOCKED",
            "experiment_data_ir_digest": ir["digest"],
            "published_root_histogram_count": self.ROOT_HISTOGRAM_COUNT,
            "available_product": "PUBLISHED_SURVIVAL_PROBABILITY_INTERVALS_AND_SOLAR_ANGLE_HISTOGRAMS",
            "missing_for_global_likelihood": (
                "FULL_BIN_TO_MICROPHYSICS_RESPONSE",
                "CROSS_BIN_COVARIANCE",
                "SOLAR_FLUX_AND_NUCLEAR_INPUT_NUISANCE_CONTRACT",
            ),
            "chi2": None,
            "official_likelihood_executed": False,
            "synthetic_substitution_allowed": False,
        }

    def run_qualification(self) -> Mapping[str, Any]:
        route = self.evaluate(family="THREE_NEUTRINO")
        general = self.evaluate(family="HIGHER_DIMENSIONAL_MICRO_IR")
        fixture = self.angular_profile_deviance(np.array([3.0, 7.0]), np.array([1.0, 2.0]), np.array([2.0, 5.0]))
        checks = {
            "published_angular_profile_kernel_qualified": abs(fixture) <= 1.0e-15,
            "official_digest_bound": SUPERK_SOLAR_RELEASE.expected_md5 == "9a44cbc7a7a4b26ba143c58ccf09419b",
            "published_histogram_count_bound": self.ROOT_HISTOGRAM_COUNT == 51,
            "generic_ingestion_owner_is_upstream": self.ingestion.contract()["owner_id"] == "SCIENTIFIC-DATA-INGESTION",
            "missing_artifact_or_covariance_fails_closed": route["status"].startswith("BLOCKED_"),
            "no_survival_interval_treated_as_full_likelihood": route["chi2"] is None,
            "general_operator_response_gap_classified_before_artifact_access": general["status"] == "BLOCKED_SUPERK_SOLAR_GENERAL_OPERATOR_RESPONSE_COVARIANCE_UNAVAILABLE",
            "no_synthetic_substitution": route["synthetic_substitution_allowed"] is False and general["synthetic_substitution_allowed"] is False,
        }
        report = {
            "schema": SCHEMA,
            "release": OWNER_VERSION,
            "owner_id": OWNER_ID,
            "status": "PASS_SUPERK_SOLAR_OWNER_FAIL_CLOSED" if all(checks.values()) else "BLOCKED_SUPERK_SOLAR_OWNER",
            "checks": checks,
            "route": route,
            "general_operator_route": general,
            "dataset_contract": self.ingestion.qualify_dataset(self.DATASET_ID),
            "claim_boundary": {
                "published_survival_profile_available": True,
                "full_solar_global_likelihood_executed": False,
                "new_msw_physics_claimed": False,
                "published_angular_profile_kernel_implemented": True,
                "public_profile_evidence_class": "PUBLISHED_ANGULAR_PROFILE",
                "arbitrary_bsm_limit_classified_information_theoretically": True,
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
            "hard_boundaries": (
                "EXPERIMENT_DATA_IR_REQUIRED",
                "NO_CONFIDENCE_INTERVAL_AS_FULL_COVARIANCE_LIKELIHOOD",
                "SOLAR_FLUX_AND_RESPONSE_NUISANCE_REQUIRED",
                "NO_SYNTHETIC_SUBSTITUTION",
            ),
        }
        return {**payload, "digest": _digest(payload)}
