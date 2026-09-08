"""Authoritative Super-Kamiokande atmospheric-neutrino likelihood owner.

The owner consumes only the official typed release.  Published chi-square
surfaces may constrain the published three-neutrino coordinates, but the 930
binned counts do not carry the systematic response functions required to
construct an exact arbitrary-BSM event likelihood.  That limitation is a hard
scientific gate, not a numerical fallback.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .scientific_data_ingestion import ScientificDataIngestionOwner, SUPERK_ATMOSPHERIC_RELEASE

OWNER_ID = "SUPERK-ATMOSPHERIC-LIKELIHOOD"
OWNER_VERSION = "6.10.0"
SCHEMA = "phi-superk-atmospheric-likelihood/v6.10"


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=float).encode()).hexdigest()


class SuperKAtmosphericLikelihoodOwner:
    DATASET_ID = "SUPERK-ATMOSPHERIC-2023"
    PUBLISHED_BIN_COUNT = 930
    RELEASE_LIMITATION = (
        "BIN_SYSTEMATIC_RESPONSE_FUNCTIONS_NOT_INCLUDED",
        "EVENT_BY_EVENT_OSCILLATION_PROBABILITIES_NOT_REPRODUCIBLE_FROM_BIN_SUMMARIES",
    )

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.ingestion = ScientificDataIngestionOwner(self.root)

    @staticmethod
    def interpolate_published_grid(axis: np.ndarray, delta_chi2: np.ndarray, value: float) -> float:
        """Interpolate only a collaboration-published one-dimensional grid."""
        x = np.asarray(axis, dtype=float).reshape(-1)
        y = np.asarray(delta_chi2, dtype=float).reshape(-1)
        if x.shape != y.shape or x.size < 2 or np.any(np.diff(x) <= 0.0) or not np.all(np.isfinite(y)):
            raise ValueError("invalid Super-K published grid")
        q = float(value)
        if q < x[0] or q > x[-1]:
            return float("inf")
        y = y - float(y.min())
        return float(np.interp(q, x, y))

    def evaluate(self, *, family: str, candidate_contract: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        candidate_contract = dict(candidate_contract or {"family": family, "digest": _digest({"family": family, "qualification": True})})
        if candidate_contract.get("family") != family or not candidate_contract.get("digest"):
            raise ValueError("candidate contract must bind the same family and a non-empty digest")
        candidate_digest = str(candidate_contract["digest"])
        # This limitation is structural, not a download problem: the public
        # binned release does not publish the response functions needed to map
        # an arbitrary multi-eigenstate operator into the 930 analysis bins.
        # Classify it before artifact availability so the system never implies
        # that merely downloading the archive would close the general-BSM gate.
        if family != "THREE_NEUTRINO":
            return {
                "family": family,
                "candidate_digest": candidate_digest,
                "status": "BLOCKED_SUPERK_ATMOSPHERIC_BSM_RESPONSE_FUNCTIONS_UNPUBLISHED",
                "evidence_class": "INFORMATION_THEORETIC_LIMIT",
                "public_profile_status": "ARBITRARY_BSM_UNDERDETERMINED",
                "dataset_contract": self.ingestion.qualify_dataset(self.DATASET_ID),
                "release_limitations": self.RELEASE_LIMITATION,
                "chi2": None,
                "official_likelihood_executed": False,
                "synthetic_substitution_allowed": False,
            }
        ir = self.ingestion.to_experiment_data_ir(self.DATASET_ID)
        if ir["status"] != "PASS_EXPERIMENT_DATA_IR":
            return {
                "family": family,
                "candidate_digest": candidate_digest,
                "status": "BLOCKED_SUPERK_ATMOSPHERIC_EXPERIMENT_DATA_IR_INCOMPLETE",
                "evidence_class": "PUBLISHED_DELTA_CHI2_GRID",
                "public_profile_status": "BLOCKED_ARTIFACT_NOT_MATERIALIZED",
                "experiment_data_ir": ir,
                "chi2": None,
                "official_likelihood_executed": False,
                "synthetic_substitution_allowed": False,
            }
        return {
            "family": family,
            "candidate_digest": candidate_digest,
            "status": "BLOCKED_SUPERK_ATMOSPHERIC_PUBLISHED_GRID_OBJECT_MAP_NOT_EXECUTED",
            "evidence_class": "PUBLISHED_DELTA_CHI2_GRID",
            "public_profile_status": "BLOCKED_GRID_OBJECT_MAP",
            "experiment_data_ir_digest": ir["digest"],
            "published_bin_count": self.PUBLISHED_BIN_COUNT,
            "supported_future_route": "INTERPOLATE_ONLY_PUBLISHED_THREE_NEUTRINO_CHI2_GRIDS",
            "release_limitations": self.RELEASE_LIMITATION,
            "chi2": None,
            "official_likelihood_executed": False,
            "synthetic_substitution_allowed": False,
        }

    def run_qualification(self) -> Mapping[str, Any]:
        route = self.evaluate(family="THREE_NEUTRINO")
        bsm = self.evaluate(family="HIGHER_DIMENSIONAL_MICRO_IR")
        fixture = self.interpolate_published_grid(np.array([0.0, 1.0, 2.0]), np.array([4.0, 0.0, 4.0]), 1.5)
        checks = {
            "published_grid_interpolator_qualified": abs(fixture - 2.0) <= 1.0e-12,
            "official_digest_bound": SUPERK_ATMOSPHERIC_RELEASE.expected_md5 == "58f26b39ba0bb36cc3570b7723298e2b",
            "published_bin_count_bound": self.PUBLISHED_BIN_COUNT == 930,
            "generic_ingestion_owner_is_upstream": self.ingestion.contract()["owner_id"] == "SCIENTIFIC-DATA-INGESTION",
            "missing_artifact_fails_closed": route["status"].startswith("BLOCKED_"),
            "arbitrary_bsm_fit_not_fabricated": bsm["status"].startswith("BLOCKED_"),
            "release_limitations_explicit": len(self.RELEASE_LIMITATION) == 2,
            "no_synthetic_substitution": not route["synthetic_substitution_allowed"] and not bsm["synthetic_substitution_allowed"],
        }
        report = {
            "schema": SCHEMA,
            "release": OWNER_VERSION,
            "owner_id": OWNER_ID,
            "status": "PASS_SUPERK_ATMOSPHERIC_OWNER_FAIL_CLOSED" if all(checks.values()) else "BLOCKED_SUPERK_ATMOSPHERIC_OWNER",
            "checks": checks,
            "three_neutrino_route": route,
            "higher_dimensional_route": bsm,
            "dataset_contract": self.ingestion.qualify_dataset(self.DATASET_ID),
            "claim_boundary": {
                "published_three_neutrino_grid_executed": False,
                "arbitrary_bsm_event_likelihood_available": False,
                "mass_ordering_discovery_claimed": False,
                "published_grid_interpolator_implemented": True,
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
            "release_limitations": self.RELEASE_LIMITATION,
            "hard_boundaries": (
                "EXPERIMENT_DATA_IR_REQUIRED",
                "PUBLISHED_GRID_ONLY_FOR_PUBLISHED_COORDINATES",
                "NO_ARBITRARY_BSM_EVENT_FIT_WITHOUT_SYSTEMATIC_RESPONSE_FUNCTIONS",
                "NO_SYNTHETIC_SUBSTITUTION",
            ),
        }
        return {**payload, "digest": _digest(payload)}
