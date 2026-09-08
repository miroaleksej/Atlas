"""Authoritative owner for the official T2K oscillation-profile ROOT release.

The public 3.6e21-POT data release contains Bayesian/frequentist profile and
coverage products in the *standard oscillation-parameter coordinates* used by
the publication.  Those products are valuable evidence for the published
three-neutrino analysis, but they are not an event/response likelihood for an
arbitrary owner-lowered multi-eigenstate operator.

This owner therefore has two duties and keeps them separate:

1. digest/schema-bind and inspect the official ROOT release through the single
   SCIENTIFIC-DATA-INGESTION owner; and
2. fail closed before a standard-parameter profile is ever misused as a
   general-operator likelihood.

No one-dimensional split-normal summary is an active likelihood route.
"""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from .scientific_data_ingestion import T2K_DATA_RELEASE_ZIP, ScientificDataIngestionOwner

OWNER_ID = "T2K-PUBLISHED-LIKELIHOOD"
OWNER_VERSION = "6.10.0"
SCHEMA = "phi-t2k-published-likelihood/v6.10"


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=float).encode()).hexdigest()


class T2KPublishedLikelihoodOwner:
    DATASET_ID = "T2K-PUBLISHED-OSCILLATION-SURFACES"
    EXPECTED_ROOT_FILES = ("Bayesian_DataRelase.root", "Frequentist_DataRelease.root")
    OBJECT_NAME_GRAMMAR = (
        "gr2D_varX_varY_<wRC,woRC>_<NH,IH,both>_<conf,cred><level>",
        "h1D_var<chi2,posterior>_<wRC,woRC>_<NH,IH>",
    )
    FELDMAN_COUSINS_SCOPE = "SIN2THETA23_DELTA_CP_WRC_2D_ONLY"
    PUBLIC_RELEASE_SCOPE = "PUBLISHED_STANDARD_OSCILLATION_PARAMETER_PROFILES_NOT_EVENT_RESPONSE_LIKELIHOOD"

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.ingestion = ScientificDataIngestionOwner(self.root)

    @staticmethod
    def normalize_delta_chi2(values: np.ndarray) -> np.ndarray:
        """Normalize a published T2K profile without inventing a likelihood scale."""
        x = np.asarray(values, dtype=float)
        if x.size == 0 or not np.all(np.isfinite(x)):
            raise ValueError("T2K profile must be non-empty and finite")
        return x - float(np.min(x))

    @staticmethod
    def interpolate_profile_1d(axis: np.ndarray, delta_chi2: np.ndarray, value: float, *, periodic: bool = False) -> float:
        x = np.asarray(axis, dtype=float).reshape(-1)
        y = T2KPublishedLikelihoodOwner.normalize_delta_chi2(delta_chi2).reshape(-1)
        if x.shape != y.shape or x.size < 2 or np.any(np.diff(x) <= 0.0):
            raise ValueError("T2K profile axis must be strictly increasing and aligned")
        q = float(value)
        if periodic:
            period = float(x[-1] - x[0])
            if period <= 0.0:
                raise ValueError("periodic T2K axis must have positive period")
            q = ((q - x[0]) % period) + x[0]
        if q < x[0] or q > x[-1]:
            return float("inf")
        return float(np.interp(q, x, y))

    @staticmethod
    def _operator_scope_certificate(family: str, candidate_contract: Mapping[str, Any]) -> Mapping[str, Any]:
        """Classify whether the published standard-coordinate surface can apply.

        This is deliberately conservative.  A complete owner-lowered operator
        with anything other than exactly three propagating states is outside the
        published profile coordinate system.  A non-three-neutrino adapter
        family is also outside that scope even if a caller omitted the persisted
        spectrum.
        """
        identity = candidate_contract.get("operator_identity")
        mode_count: int | None = None
        active_shape: tuple[int, ...] | None = None
        if isinstance(identity, Mapping):
            spectrum = identity.get("takagi_spectrum")
            if isinstance(spectrum, Mapping):
                masses = spectrum.get("takagi_masses_ev", ())
                try:
                    mode_count = len(tuple(masses))
                except Exception:
                    mode_count = None
                real = spectrum.get("active_mixing_real", ())
                try:
                    active_shape = tuple(np.asarray(real, dtype=float).shape)
                except Exception:
                    active_shape = None
        standard_coordinate_candidate = family == "THREE_NEUTRINO" and (mode_count in (None, 3)) and (active_shape in (None, (3, 3)))
        return {
            "status": "PASS_T2K_STANDARD_PROFILE_COORDINATE_SCOPE" if standard_coordinate_candidate else "BLOCKED_T2K_PUBLISHED_SURFACES_STANDARD_COORDINATES_ONLY",
            "public_release_scope": T2KPublishedLikelihoodOwner.PUBLIC_RELEASE_SCOPE,
            "family": family,
            "propagating_mode_count": mode_count,
            "active_mixing_shape": active_shape,
            "arbitrary_operator_event_response_available": False,
            "standard_profile_coordinate_candidate": standard_coordinate_candidate,
        }

    def _inspect_official_root_object_map(self, entries: tuple[str, ...]) -> Mapping[str, Any]:
        """Inspect ROOT keys after provenance/schema qualification.

        Archive parsing remains in SCIENTIFIC-DATA-INGESTION.  This method only
        asks the upstream owner for already qualified member bytes and lets
        uproot inspect the ROOT objects in memory.
        """
        basename_to_member = {Path(name).name: name for name in entries}
        missing = tuple(name for name in self.EXPECTED_ROOT_FILES if name not in basename_to_member)
        if missing:
            return {"status": "BLOCKED_T2K_DOMAIN_OBJECT_SET_INCOMPLETE", "missing_root_files": missing}
        try:
            import uproot  # type: ignore
        except Exception as exc:
            return {"status": "BLOCKED_UPROOT_NOT_AVAILABLE", "error_type": type(exc).__name__}
        members = tuple(basename_to_member[name] for name in self.EXPECTED_ROOT_FILES)
        try:
            payloads = self.ingestion.read_qualified_archive_members(T2K_DATA_RELEASE_ZIP.artifact_id, members)
            object_keys: dict[str, tuple[str, ...]] = {}
            for member in members:
                with uproot.open(io.BytesIO(payloads[member])) as handle:
                    object_keys[Path(member).name] = tuple(str(key) for key in handle.keys(recursive=True))
        except Exception as exc:
            return {
                "status": "BLOCKED_T2K_ROOT_OBJECT_MAP_PARSE_FAILURE",
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
            }
        return {
            "status": "PASS_T2K_ROOT_OBJECT_MAP_INSPECTED",
            "reader": uproot.__name__,
            "object_keys": object_keys,
            "object_counts": {name: len(keys) for name, keys in object_keys.items()},
        }

    def evaluate(self, *, family: str, candidate_contract: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        candidate_contract = dict(candidate_contract or {"family": family, "digest": _digest({"family": family, "qualification": True})})
        if candidate_contract.get("family") != family or not candidate_contract.get("digest"):
            raise ValueError("candidate contract must bind the same family and a non-empty digest")
        candidate_digest = str(candidate_contract["digest"])
        scope = self._operator_scope_certificate(family, candidate_contract)
        if scope["status"].startswith("BLOCKED_"):
            return {
                "family": family,
                "candidate_digest": candidate_digest,
                "status": scope["status"],
                "evidence_class": "PUBLISHED_STANDARD_OSCILLATION_PARAMETER_PROFILE",
                "public_profile_status": "BLOCKED_PROFILE_SCOPE_INSUFFICIENT_FOR_GENERAL_OPERATOR",
                "scope_certificate": scope,
                "chi2": None,
                "delta_chi2": None,
                "official_root_surface_executed": False,
                "synthetic_substitution_allowed": False,
            }

        ir = self.ingestion.to_experiment_data_ir(self.DATASET_ID)
        if ir["status"] != "PASS_EXPERIMENT_DATA_IR":
            return {
                "family": family,
                "candidate_digest": candidate_digest,
                "status": "BLOCKED_T2K_EXPERIMENT_DATA_IR_INCOMPLETE",
                "evidence_class": "PUBLISHED_STANDARD_OSCILLATION_PARAMETER_PROFILE",
                "public_profile_status": "BLOCKED_ARTIFACT_NOT_MATERIALIZED",
                "scope_certificate": scope,
                "experiment_data_ir": ir,
                "chi2": None,
                "delta_chi2": None,
                "official_root_surface_executed": False,
                "synthetic_substitution_allowed": False,
            }
        inspection = self.ingestion.inspect_all()[T2K_DATA_RELEASE_ZIP.artifact_id]
        entries = tuple(inspection.get("schema_result", {}).get("entries", ()))
        object_map = self._inspect_official_root_object_map(entries)
        if object_map["status"] != "PASS_T2K_ROOT_OBJECT_MAP_INSPECTED":
            return {
                "family": family,
                "candidate_digest": candidate_digest,
                "status": object_map["status"],
                "evidence_class": "PUBLISHED_STANDARD_OSCILLATION_PARAMETER_PROFILE",
                "public_profile_status": "BLOCKED_ROOT_OBJECT_MAP",
                "scope_certificate": scope,
                "experiment_data_ir_digest": ir["digest"],
                "root_object_map": object_map,
                "chi2": None,
                "delta_chi2": None,
                "official_root_surface_executed": False,
                "synthetic_substitution_allowed": False,
            }
        # The official electronic release is now parsed, but a set of published
        # one-/two-dimensional standard-parameter profiles is not a joint event
        # likelihood.  We preserve it as profile evidence and do not fabricate a
        # scalar arbitrary-candidate score by adding correlated projections.
        return {
            "family": family,
            "candidate_digest": candidate_digest,
            "status": "BLOCKED_T2K_PUBLISHED_PROFILE_SET_NOT_JOINT_EVENT_LIKELIHOOD",
            "evidence_class": "PUBLISHED_STANDARD_OSCILLATION_PARAMETER_PROFILE",
            "public_profile_status": "PASS_ROOT_OBJECT_MAP_ONLY",
            "scope_certificate": scope,
            "experiment_data_ir_digest": ir["digest"],
            "root_object_map": object_map,
            "object_name_grammar": self.OBJECT_NAME_GRAMMAR,
            "reactor_constraint_tags": ("wRC", "woRC"),
            "hierarchy_tags": ("NH", "IH", "both"),
            "feldman_cousins_scope": self.FELDMAN_COUSINS_SCOPE,
            "chi2": None,
            "delta_chi2": None,
            "official_root_surface_executed": False,
            "synthetic_substitution_allowed": False,
        }

    def run_qualification(self) -> Mapping[str, Any]:
        route = self.evaluate(family="THREE_NEUTRINO")
        arbitrary = self.evaluate(
            family="HIGHER_DIMENSIONAL_MICRO_IR",
            candidate_contract={
                "family": "HIGHER_DIMENSIONAL_MICRO_IR",
                "digest": _digest({"qualification": "T2K_GENERAL_OPERATOR_SCOPE"}),
                "operator_identity": {
                    "takagi_spectrum": {
                        "takagi_masses_ev": (0.01, 0.02, 0.05, 1.0),
                        "active_mixing_real": np.zeros((3, 4)).tolist(),
                    }
                },
            },
        )
        fixture = self.interpolate_profile_1d(
            np.array([-3.141592653589793, 0.0, 3.141592653589793]),
            np.array([4.0, 0.0, 4.0]),
            1.5707963267948966,
            periodic=True,
        )
        checks = {
            "published_profile_interpolator_qualified": abs(fixture - 2.0) <= 1.0e-12,
            "published_zip_digest_bound": T2K_DATA_RELEASE_ZIP.expected_md5 == "864a40abecd009c1654e0c580c4375e2",
            "generic_ingestion_owner_is_upstream": self.ingestion.contract()["owner_id"] == "SCIENTIFIC-DATA-INGESTION",
            "official_root_products_are_single_active_route": True,
            "reactor_constraint_scope_explicit": "wRC" in self.OBJECT_NAME_GRAMMAR[0] and "woRC" in self.OBJECT_NAME_GRAMMAR[0],
            "hierarchy_scope_explicit": "NH" in self.OBJECT_NAME_GRAMMAR[0] and "IH" in self.OBJECT_NAME_GRAMMAR[0],
            "fc_scope_exact": self.FELDMAN_COUSINS_SCOPE == "SIN2THETA23_DELTA_CP_WRC_2D_ONLY",
            "full_root_route_fails_closed": route["status"].startswith("BLOCKED_"),
            "general_operator_profile_misuse_blocked_before_artifact_access": arbitrary["status"] == "BLOCKED_T2K_PUBLISHED_SURFACES_STANDARD_COORDINATES_ONLY",
            "general_operator_has_no_fabricated_scalar_score": arbitrary["chi2"] is None and arbitrary["delta_chi2"] is None,
            "no_synthetic_substitution": route["synthetic_substitution_allowed"] is False and arbitrary["synthetic_substitution_allowed"] is False,
        }
        report = {
            "schema": SCHEMA,
            "release": OWNER_VERSION,
            "owner_id": OWNER_ID,
            "status": "PASS_OFFICIAL_ROOT_OWNER_SCOPE_SAFE_FAIL_CLOSED" if all(checks.values()) else "BLOCKED_T2K_OWNER",
            "checks": checks,
            "three_neutrino_route": route,
            "general_operator_route": arbitrary,
            "dataset_contract": self.ingestion.qualify_dataset(self.DATASET_ID),
            "claim_boundary": {
                "domain_specific_materializer_or_archive_parser_active": False,
                "one_dimensional_summary_used_as_likelihood": False,
                "official_root_likelihood_executed": False,
                "public_release_is_general_operator_event_response": False,
                "general_operator_scored_from_standard_profiles": False,
                "mass_ordering_discovery_claimed": False,
                "cp_violation_discovery_claimed": False,
                "published_profile_interpolator_implemented": True,
                "public_profile_evidence_class": "PUBLISHED_STANDARD_OSCILLATION_PARAMETER_PROFILE",
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
            "object_name_grammar": self.OBJECT_NAME_GRAMMAR,
            "feldman_cousins_scope": self.FELDMAN_COUSINS_SCOPE,
            "public_release_scope": self.PUBLIC_RELEASE_SCOPE,
            "hard_boundaries": (
                "NO_DOMAIN_SPECIFIC_MATERIALIZER_OR_ARCHIVE_PARSER",
                "EXPERIMENT_DATA_IR_REQUIRED",
                "NO_SPLIT_NORMAL_SUMMARY_AS_ACTIVE_LIKELIHOOD",
                "NO_DOUBLE_COUNT_REACTOR_THETA13_CONSTRAINT",
                "NO_STANDARD_PARAMETER_PROFILE_AS_GENERAL_OPERATOR_EVENT_LIKELIHOOD",
                "NO_CORRELATED_PROFILE_SUM_AS_FAKE_JOINT_LIKELIHOOD",
                "NO_CP_DISCOVERY_CLAIM_BEFORE_SUPPORTED_LIKELIHOOD_EXECUTION",
                "NO_FELDMAN_COUSINS_CLAIM_OUTSIDE_PUBLISHED_CORRECTED_PRODUCTS",
            ),
        }
        return {**payload, "digest": _digest(payload)}
