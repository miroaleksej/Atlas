"""Thin facade over the authoritative neutrino real-data owners.

Scientific logic lives only in the experiment and global owner modules.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .neutrino import OscillationParameters
from .neutrino_global_combination import NeutrinoGlobalCombinationOwner

OWNER_ID = "NEUTRINO-REAL-DATA-ORCHESTRATOR"
OWNER_VERSION = "6.10.0"
SCHEMA = "phi-neutrino-real-data-orchestrator/v6.10"
QUALIFICATION_SCHEMA = "phi-neutrino-real-data-qualification/v6.10"


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=float).encode()).hexdigest()


class NeutrinoRealDataLikelihoodOwner:
    """Thin orchestrator; no scientific formula or ingestion algorithm is owned here."""

    def __init__(self, root: str | Path, parameters: OscillationParameters | None = None) -> None:
        self.root = Path(root)
        self.parameters = parameters or OscillationParameters()
        self.global_owner = NeutrinoGlobalCombinationOwner(self.root, self.parameters)
        # The portfolio reuses the exact owner instances held by the global
        # combination owner.  No duplicate Daya Bay fit/cache lifecycle exists.
        self.dayabay = self.global_owner.dayabay
        self.katrin = self.global_owner.katrin
        self.t2k = self.global_owner.t2k
        self.atmospheric = self.global_owner.atmospheric
        self.solar = self.global_owner.solar
        self.external_constraints = self.global_owner.external_constraints
        self.ingestion = self.dayabay.ingestion
        self._qualification_cache: Mapping[str, Any] | None = None

    def evaluate_candidate(self, candidate_id: str, family: str, candidate_parameters: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        return self.global_owner.evaluate(candidate_id=candidate_id, family=family, candidate_parameters=candidate_parameters)

    def artifact_status(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self.ingestion.inspect_all().values())

    def run_qualification(self) -> Mapping[str, Any]:
        if self._qualification_cache is not None:
            return self._qualification_cache
        dayabay = self.dayabay.run_qualification()
        katrin = self.katrin.run_qualification()
        t2k = self.t2k.run_qualification()
        atmospheric = self.atmospheric.run_qualification()
        solar = self.solar.run_qualification()
        external_constraints = self.external_constraints.run_qualification()
        global_report = self.global_owner.run_qualification()
        ingestion_report = self.ingestion.run_qualification()
        checks = {
            "dayabay_public_profile_owner_executed_with_exact_reference_boundary": dayabay["status"] == "PASS_PUBLIC_DATA_PROFILE_OWNER_WITH_EXACT_REFERENCE_SOFTWARE_BOUNDARY",
            "katrin_official_owner_fail_closed": katrin["status"] == "PASS_OFFICIAL_ARTIFACT_OWNER_FAIL_CLOSED",
            "t2k_official_owner_fail_closed": t2k["status"] == "PASS_OFFICIAL_ROOT_OWNER_SCOPE_SAFE_FAIL_CLOSED",
            "scientific_data_ingestion_fail_closed": ingestion_report["status"] == "PASS_SCIENTIFIC_DATA_INGESTION_FAIL_CLOSED",
            "superk_atmospheric_owner_fail_closed": atmospheric["status"] == "PASS_SUPERK_ATMOSPHERIC_OWNER_FAIL_CLOSED",
            "superk_solar_owner_fail_closed": solar["status"] == "PASS_SUPERK_SOLAR_OWNER_FAIL_CLOSED",
            "external_constraint_scope_gate_fail_closed": external_constraints["status"] == "PASS_EXTERNAL_CONSTRAINT_SCOPE_GATE_FAIL_CLOSED",
            "global_owner_has_single_candidate_contract": global_report["status"] == "PASS_GLOBAL_OWNER_FAIL_CLOSED_SINGLE_CANDIDATE_CONTRACT",
            "single_shared_experiment_owner_graph": all((
                self.dayabay is self.global_owner.dayabay,
                self.katrin is self.global_owner.katrin,
                self.t2k is self.global_owner.t2k,
                self.atmospheric is self.global_owner.atmospheric,
                self.solar is self.global_owner.solar,
                self.external_constraints is self.global_owner.external_constraints,
            )),
        }
        candidates = tuple(self.evaluate_candidate(f"REAL-{family}", family) for family in self.global_owner.FAMILIES)
        report = {
            "schema": QUALIFICATION_SCHEMA,
            "release": OWNER_VERSION,
            "owner_id": OWNER_ID,
            "status": "PASS_REAL_DATA_PORTFOLIO_PARTIAL_PUBLIC_PROFILE_FAIL_CLOSED_GLOBAL" if all(checks.values()) else "BLOCKED_REAL_DATA_OWNER_PORTFOLIO",
            "checks": checks,
            "dayabay": dayabay,
            "katrin": katrin,
            "t2k": t2k,
            "atmospheric": atmospheric,
            "solar": solar,
            "external_constraints": external_constraints,
            "global_combination": global_report,
            "scientific_data_ingestion": ingestion_report,
            "external_artifacts": self.artifact_status(),
            "candidate_results": candidates,
            "claim_boundary": {
                "dayabay_analysis_data_materialized": dayabay.get("route", {}).get("official_analysis_data_materialized") is True,
                "dayabay_public_detector_period_profile_executed": dayabay.get("route", {}).get("spectral_likelihood_executed") is True,
                "dayabay_exact_reference_software_executed": dayabay.get("route", {}).get("exact_reference_software_executed") is True,
                "dayabay_reference_model_materialized": dayabay.get("route", {}).get("reference_model_artifact", {}).get("present") is True,
                "all_required_real_data_artifacts_materialized": False,
                "published_summary_or_reduced_surrogate_active": False,
                "dayabay_public_spectra_and_released_response_executed": True,
                "full_portfolio_published_spectra_and_covariances_executed": False,
                "general_operator_public_product_scope_gaps_explicit": True,
                "t2k_standard_profiles_used_as_general_operator_event_likelihood": False,
                "global_3NU_3P1_HIGHER_DIMENSIONAL_NSI_DECOHERENCE_competition_executed": False,
                "synthetic_3NU_3P1_FLAT_WARPED_NSI_DECOHERENCE_competition_executed": global_report.get("claim_boundary", {}).get("synthetic_3NU_3P1_FLAT_WARPED_NSI_DECOHERENCE_competition_executed") is True,
                "public_real_data_profile_type": global_report.get("claim_boundary", {}).get("public_profile_type"),
                "extra_dimension_detected": False,
                "sterile_neutrino_detected": False,
                "new_physical_law_claimed": False,
                "missing_artifact_policy": "FAIL_CLOSED_NO_SYNTHETIC_REPLACEMENT",
                "experiment_owner_instance_graph": "SINGLE_SHARED_GRAPH_OWNED_BY_NEUTRINO_GLOBAL_COMBINATION",
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
            "authoritative_owners": (
                self.dayabay.contract(), self.katrin.contract(), self.t2k.contract(), self.atmospheric.contract(),
                self.solar.contract(), self.external_constraints.contract(), self.global_owner.contract(), self.ingestion.contract()
            ),
            "hard_boundaries": (
                "FACADE_CONTAINS_NO_SCIENTIFIC_ALGORITHM",
                "NO_SYNTHETIC_REPLACEMENT_FOR_MISSING_REAL_DATA",
                "NO_SUMMARY_OR_REDUCED_SURROGATE_AS_ACTIVE_ROUTE",
                "PARTIAL_PUBLIC_DATA_PROFILE_MUST_NOT_BE_PROMOTED_TO_GLOBAL_SCORE",
                "GLOBAL_OWNER_AND_PORTFOLIO_MUST_SHARE_THE_SAME_EXPERIMENT_OWNER_INSTANCES",
                "PUBLIC_PRODUCT_SCOPE_GAP_IS_NOT_RELABELED_AS_MISSING_DOWNLOAD",
                "NO_STANDARD_PARAMETER_SURFACE_AS_GENERAL_OPERATOR_EVENT_LIKELIHOOD",
                "NO_EXTRA_DIMENSION_DISCOVERY_CLAIM",
            ),
        }
        return {**payload, "digest": _digest(payload)}
