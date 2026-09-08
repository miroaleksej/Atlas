"""Authoritative one-candidate, multi-experiment neutrino competition owner.

One immutable NeutrinoCandidateIR is transmitted to every experiment and
external-constraint owner.  A global statistic is forbidden unless every
required owner executed its supported likelihood/constraint for exactly the
same candidate digest and shared priors have been de-duplicated.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any, Mapping

from .dayabay_full_likelihood import DayaBayFullLikelihoodOwner
from .katrin_spectral_likelihood import KATRINSpectralLikelihoodOwner
from .neutrino import BlindNeutrinoDiscoveryOwner, DirectedOperatorSearchRequest, HigherDimensionalMicroParameters, NeutrinoPhenomenologyOwner, OscillationParameters
from .neutrino_external_constraints import NeutrinoExternalConstraintsOwner
from .superk_atmospheric_likelihood import SuperKAtmosphericLikelihoodOwner
from .superk_solar_likelihood import SuperKSolarLikelihoodOwner
from .t2k_published_likelihood import T2KPublishedLikelihoodOwner

OWNER_ID = "NEUTRINO-GLOBAL-COMBINATION"
OWNER_VERSION = "6.10.0"
SCHEMA = "phi-neutrino-global-combination/v6.10"


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=float).encode()).hexdigest()


def _freeze_ledger_map(freeze_gate: Mapping[str, Any]) -> dict[str, tuple[str, str]]:
    """Return candidate -> (operator digest, D_discovery quality digest).

    The blind v6.9 freeze freezes the discovery-data nuisance certificate together with the
    operator; v6.10 consumes that immutable ledger without regenerating it.  Two-field entries are accepted only as a compatibility read
    path for pre-data-guided blind scans and are normalized to an empty
    discovery-quality digest; all newly written v6.9 ledgers contain three
    fields.
    """
    ledger: dict[str, tuple[str, str]] = {}
    for raw in freeze_gate.get("candidate_digest_ledger", ()):
        if not isinstance(raw, (tuple, list)) or len(raw) not in (2, 3):
            raise ValueError("freeze ledger entries must bind candidate/operator and optional discovery-quality digest")
        cid = str(raw[0])
        operator_digest = str(raw[1])
        quality_digest = str(raw[2]) if len(raw) == 3 else ""
        if not cid or not operator_digest:
            raise ValueError("freeze ledger contains an empty candidate id or operator digest")
        if cid in ledger and ledger[cid] != (operator_digest, quality_digest):
            raise ValueError("freeze ledger contains conflicting bindings for one candidate")
        ledger[cid] = (operator_digest, quality_digest)
    return ledger


class NeutrinoGlobalCombinationOwner:
    """Single owner of cross-experiment candidate binding and combination.

    Qualification is content-addressed by the exact distribution root, the
    Daya Bay input-artifact generation and the oscillation-parameter payload.
    Re-instantiating this owner therefore cannot repeat the same expensive
    blind benchmark or public-data profile within one process, while a changed
    input artifact or parameter set always invalidates the cached certificate.
    """

    _SHARED_QUALIFICATION_CACHE: dict[tuple[str, int, int, str, str], Mapping[str, Any]] = {}
    _SHARED_QUALIFICATION_LOCK = RLock()

    FAMILIES = ("THREE_NEUTRINO", "STERILE_3P1", "HIGHER_DIMENSIONAL_MICRO_IR", "NSI", "DECOHERENCE")  # experiment-adapter capabilities, not search-space boundary
    REQUIRED_OWNERS = ("dayabay", "katrin", "t2k", "atmospheric", "solar", "external_constraints")
    PUBLIC_PROFILE_TYPE = "PUBLIC_REAL_DATA_GLOBAL_PROFILE"
    EXECUTED_STATUS_PREFIXES = (
        "PASS_LIKELIHOOD_EXECUTED",
        "PASS_PUBLIC_PROFILE_EXECUTED",
        "PASS_CONSTRAINT_EXECUTED",
    )

    def __init__(self, root: str | Path, parameters: OscillationParameters | None = None) -> None:
        self.root = Path(root)
        self.parameters = parameters or OscillationParameters()
        self.parameters.validate()
        self.phenomenology = NeutrinoPhenomenologyOwner(self.parameters)
        self.dayabay = DayaBayFullLikelihoodOwner(self.root)
        self.katrin = KATRINSpectralLikelihoodOwner(self.root)
        self.t2k = T2KPublishedLikelihoodOwner(self.root)
        self.atmospheric = SuperKAtmosphericLikelihoodOwner(self.root)
        self.solar = SuperKSolarLikelihoodOwner(self.root)
        self.external_constraints = NeutrinoExternalConstraintsOwner()
        daya_root, daya_size, daya_mtime = self.dayabay._cache_key
        self._qualification_key = (
            str(self.root.resolve()),
            int(daya_size),
            int(daya_mtime),
            _digest(self.parameters.to_dict()),
            OWNER_VERSION,
        )
        if daya_root != self._qualification_key[0]:
            raise RuntimeError("global owner and Daya Bay owner must bind the same distribution root")
        with self._SHARED_QUALIFICATION_LOCK:
            cached = self._SHARED_QUALIFICATION_CACHE.get(self._qualification_key)
        self._qualification_cache: Mapping[str, Any] | None = deepcopy(cached) if cached is not None else None

    @classmethod
    def _falsification_scope_class(cls, status: str) -> str:
        if any(str(status).startswith(prefix) for prefix in cls.EXECUTED_STATUS_PREFIXES):
            return "EXECUTED_SUPPORTED_LIKELIHOOD"
        structural_tokens = (
            "STANDARD_COORDINATES_ONLY",
            "RESPONSE_FUNCTIONS_UNPUBLISHED",
            "GENERAL_OPERATOR_RESPONSE_COVARIANCE_UNAVAILABLE",
            "MODEL_SCOPE",
        )
        if any(token in str(status) for token in structural_tokens):
            return "BLOCKED_PUBLIC_PRODUCT_SCOPE_INSUFFICIENT_FOR_GENERAL_OPERATOR"
        return "BLOCKED_ARTIFACT_RESPONSE_OR_ADAPTER_INCOMPLETE"

    def _evaluate_candidate_contract(self, *, candidate: Mapping[str, Any], family: str) -> Mapping[str, Any]:
        """Single experiment-combination path for every candidate origin."""
        experiment_results = {
            "dayabay": self.dayabay.evaluate(family=family, candidate_contract=candidate),
            "katrin": self.katrin.evaluate(family=family, candidate_contract=candidate),
            # The global route uses T2K woRC products when Daya Bay is present;
            # the experiment owner remains responsible for selecting the exact
            # published object once the ROOT file is materialized.
            "t2k": self.t2k.evaluate(family=family, candidate_contract={**candidate, "global_surface_policy": "woRC"}),
            "atmospheric": self.atmospheric.evaluate(family=family, candidate_contract=candidate),
            "solar": self.solar.evaluate(family=family, candidate_contract=candidate),
            "external_constraints": self.external_constraints.evaluate(family=family, candidate_contract=candidate),
        }
        profile_ledger = {
            name: {
                "status": row.get("status"),
                "evidence_class": row.get("evidence_class", "MODEL_SCOPED_CONSTRAINT" if name == "external_constraints" else "UNCLASSIFIED"),
                "public_profile_status": row.get("public_profile_status", row.get("status")),
                "candidate_digest": row.get("candidate_digest"),
                "chi2": row.get("chi2"),
                "delta_chi2": row.get("delta_chi2"),
            }
            for name, row in experiment_results.items()
        }
        falsification_scope_ledger = {
            name: {
                "status": row.get("status"),
                "scope_class": self._falsification_scope_class(str(row.get("status", ""))),
                "official_likelihood_executed": bool(row.get("official_likelihood_executed", row.get("status", "").startswith(self.EXECUTED_STATUS_PREFIXES))),
                "synthetic_substitution_allowed": row.get("synthetic_substitution_allowed", False),
            }
            for name, row in experiment_results.items()
        }
        digest_match = all(row.get("candidate_digest") == candidate["digest"] for row in experiment_results.values())
        common = {
            "candidate_id": candidate["candidate_id"],
            "family": family,
            "candidate_digest": candidate["digest"],
            "candidate_contract": candidate,
            "experiment_results": experiment_results,
            "profile_type": self.PUBLIC_PROFILE_TYPE,
            "evidence_ledger": profile_ledger,
            "falsification_scope_ledger": falsification_scope_ledger,
            "chi2": None,
            "log_likelihood": None,
            "promotion_allowed": False,
            "synthetic_substitution_allowed": False,
        }
        if not digest_match:
            return {**common, "status": "BLOCKED_GLOBAL_CANDIDATE_DIGEST_MISMATCH"}
        executed = {
            name: row
            for name, row in experiment_results.items()
            if row.get("status", "").startswith(self.EXECUTED_STATUS_PREFIXES)
        }
        blockers = {
            name: row.get("status")
            for name, row in experiment_results.items()
            if name not in executed
        }
        shared_priors: list[str] = []
        for row in executed.values():
            shared_priors.extend(str(value) for value in row.get("shared_prior_ids", ()))
        duplicated_priors = tuple(sorted({value for value in shared_priors if shared_priors.count(value) > 1}))
        if duplicated_priors:
            return {**common, "status": "BLOCKED_GLOBAL_SHARED_PRIOR_DOUBLE_COUNT", "duplicated_shared_prior_ids": duplicated_priors}
        if blockers:
            return {
                **common,
                "status": "BLOCKED_GLOBAL_EXPERIMENT_LEVEL_LIKELIHOODS_INCOMPLETE",
                "blocked_requirements": blockers,
                "same_microparameters_sent_to_all_owners": True,
                "shared_prior_policy": "T2K_WORC_WHEN_DAYABAY_INCLUDED",
            }
        if set(executed) != set(self.REQUIRED_OWNERS):
            raise RuntimeError("executed global owner set must be complete before combination")
        scalar_contributions = {
            name: row.get("delta_chi2") if row.get("delta_chi2") is not None else row.get("chi2")
            for name, row in executed.items()
        }
        if any(value is None for value in scalar_contributions.values()):
            raise RuntimeError("every executed public profile must expose chi2 or delta_chi2")
        total_chi2 = sum(float(value) for value in scalar_contributions.values())
        return {
            **common,
            "status": "PASS_GLOBAL_EXPERIMENT_LEVEL_LIKELIHOOD_EXECUTED",
            "profile_contributions": scalar_contributions,
            "chi2": total_chi2,
            "log_likelihood": -0.5 * total_chi2,
            "same_microparameters_sent_to_all_owners": True,
            "shared_prior_policy": "T2K_WORC_WHEN_DAYABAY_INCLUDED",
        }

    def evaluate(
        self,
        *,
        candidate_id: str,
        family: str,
        candidate_parameters: HigherDimensionalMicroParameters | Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        if family not in self.FAMILIES:
            raise ValueError(f"unsupported neutrino family: {family}")
        candidate = self.phenomenology.candidate_ir(
            candidate_id=candidate_id,
            family=family,
            microscopic_parameters=candidate_parameters,
        ).to_dict()
        return self._evaluate_candidate_contract(candidate=candidate, family=family)

    def evaluate_frozen_discovery_candidate(
        self,
        *,
        frozen_row: Mapping[str, Any],
        freeze_gate: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Attempt held-out real-data falsification of one immutable blind candidate.

        The frozen operator identity is re-hashed and re-lowered before it is
        transmitted to experiment owners.  The discovery digest and frontier
        freeze digest are evidence bindings; neither EIG nor literature output
        can alter the microparameters at this stage.
        """
        if freeze_gate.get("status") != "FROZEN_BEFORE_FALSIFICATION_AND_LITERATURE_AUDIT":
            raise ValueError("candidate frontier must be frozen before falsification")
        if freeze_gate.get("mutation_after_freeze_allowed") is not False:
            raise ValueError("freeze gate must forbid post-freeze mutation")
        candidate_id = str(frozen_row.get("candidate_id", ""))
        operator_digest = str(frozen_row.get("operator_identity_digest", ""))
        ledger = _freeze_ledger_map(freeze_gate)
        expected_quality_digest = str(frozen_row.get("discovery_quality_digest", ""))
        if not candidate_id or ledger.get(candidate_id) != (operator_digest, expected_quality_digest):
            raise ValueError("frozen candidate/operator/discovery-quality binding is absent from or mismatched against the freeze ledger")
        operator_identity = frozen_row.get("operator_identity")
        if not isinstance(operator_identity, Mapping):
            raise ValueError("frozen candidate lacks operator identity")
        if _digest(operator_identity) != operator_digest:
            raise ValueError("frozen operator identity digest mismatch")
        micro = HigherDimensionalMicroParameters.from_mapping(operator_identity.get("micro_parameters", {}))
        ir = self.phenomenology.micro_to_ir(micro)
        stored = operator_identity.get("observable_kernel", {})
        masses = ir.takagi_spectrum.takagi_masses_ev
        stored_masses = tuple(float(v) for v in stored.get("takagi_masses_ev", ()))
        if len(masses) != len(stored_masses):
            relowering_residual = float("inf")
        else:
            relowering_residual = max((abs(float(a)-float(b)) for a,b in zip(masses, stored_masses)), default=0.0)
        stored_real = stored.get("active_mixing_real", ())
        stored_imag = stored.get("active_mixing_imag", ())
        if stored_real and stored_imag:
            import numpy as np
            active_now = np.asarray(ir.takagi_spectrum.active_mixing_real, dtype=float) + 1j*np.asarray(ir.takagi_spectrum.active_mixing_imag, dtype=float)
            active_stored = np.asarray(stored_real, dtype=float) + 1j*np.asarray(stored_imag, dtype=float)
            if active_now.shape != active_stored.shape:
                relowering_residual = float("inf")
            else:
                relowering_residual = max(relowering_residual, float(np.max(np.abs(active_now-active_stored))))
        if not relowering_residual < 1.0e-12:
            return {
                "status": "BLOCKED_FROZEN_CANDIDATE_RELOWERING_MISMATCH",
                "candidate_id": candidate_id,
                "discovery_operator_identity_digest": operator_digest,
                "discovery_freeze_digest": freeze_gate.get("freeze_digest"),
                "relowering_residual": relowering_residual,
                "chi2": None,
                "promotion_allowed": False,
            }
        result = dict(self.evaluate(
            candidate_id=candidate_id,
            family="HIGHER_DIMENSIONAL_MICRO_IR",
            candidate_parameters=micro,
        ))
        result["discovery_freeze_binding"] = {
            "status": "PASS_FROZEN_OPERATOR_REHASHED_AND_RELOWERED",
            "discovery_operator_identity_digest": operator_digest,
            "discovery_freeze_digest": freeze_gate.get("freeze_digest"),
            "relowering_residual": relowering_residual,
            "postfreeze_mutation_allowed": False,
        }
        result["heldout_falsification_status"] = (
            "EXECUTED" if result.get("status") == "PASS_GLOBAL_EXPERIMENT_LEVEL_LIKELIHOOD_EXECUTED"
            else "BLOCKED_BY_EXPERIMENT_ADAPTER_OR_PUBLIC_LIKELIHOOD_GAP"
        )
        return result

    @staticmethod
    def _discovery_row_candidate_contract(row: Mapping[str, Any]) -> Mapping[str, Any]:
        identity = row.get("operator_identity")
        if not isinstance(identity, Mapping):
            raise ValueError("blind discovery row lacks operator identity")
        takagi = identity.get("observable_kernel")
        if not isinstance(takagi, Mapping):
            raise ValueError("blind discovery row lacks persisted Takagi observable kernel")
        operator_digest = str(row.get("operator_identity_digest", ""))
        if not operator_digest:
            raise ValueError("blind discovery row lacks operator identity digest")
        return {
            "family": "HIGHER_DIMENSIONAL_MICRO_IR",
            "digest": operator_digest,
            "operator_identity_status": "COMPLETE_OWNER_LOWERED_OPERATOR_IDENTITY",
            "operator_identity": {"digest": operator_digest, "takagi_spectrum": takagi},
            "oscillation_parameters": {},
        }

    def run_blind_data_partition_cycle(
        self,
        *,
        request: DirectedOperatorSearchRequest | None = None,
        discovery_periods: tuple[str, ...] = ("6AD", "8AD"),
        heldout_periods: tuple[str, ...] = ("7AD",),
    ) -> Mapping[str, Any]:
        """Run one blind QD batch with real D_discovery and frozen temporal holdout.

        The experiment owner supplies only a scalar public-data quality and its
        nuisance certificate.  It supplies no model-family label, published
        mass template, literature ancestor or distance to 3nu.  Every operator
        and its D_discovery nuisance state are frozen before the held-out period
        is opened.  Held-out results never mutate the frozen archive.
        """
        if set(discovery_periods).intersection(heldout_periods):
            raise ValueError("discovery and held-out Daya Bay periods must be disjoint")
        ir = self.dayabay.ingestion.to_experiment_data_ir(self.dayabay.DATASET_ID)
        if ir.get("status") != "PASS_EXPERIMENT_DATA_IR":
            return {
                "schema": "phi-neutrino-blind-data-partition-cycle/v6.10",
                "owner_id": OWNER_ID,
                "owner_version": OWNER_VERSION,
                "status": "BLOCKED_D_DISCOVERY_EXPERIMENT_DATA_IR_INCOMPLETE",
                "experiment_data_ir": ir,
            }
        quality_contract = {
            "dataset_partition_id": "DAYABAY_TEMPORAL_D_DISCOVERY_6AD_8AD",
            "dataset_id": self.dayabay.DATASET_ID,
            "experiment_owner": f"{self.dayabay.contract()['owner_id']}/{self.dayabay.contract()['owner_version']}",
            "experiment_data_ir_digest": ir["digest"],
            "discovery_periods": discovery_periods,
            "heldout_periods": heldout_periods,
            "quality_metric": "CNP_PROFILE_CHI2_WITH_COMMON_SOURCE_NUISANCE_PROFILED_ONLY_ON_D_DISCOVERY",
            "published_theory_template_input": False,
            "heldout_period_visible_to_discovery": False,
        }

        def quality_evaluator(row: Mapping[str, Any]) -> Mapping[str, Any]:
            candidate = self._discovery_row_candidate_contract(row)
            return self.dayabay.discovery_partition_score(
                family="HIGHER_DIMENSIONAL_MICRO_IR",
                candidate_contract=candidate,
                discovery_periods=discovery_periods,
            )

        scan = BlindNeutrinoDiscoveryOwner(self.phenomenology).discover(
            request,
            discovery_quality_evaluator=quality_evaluator,
            discovery_quality_contract=quality_contract,
        )
        freeze_gate = scan["freeze_gate"]
        ledger: dict[str, tuple[str, str]] = {}
        for entry in freeze_gate.get("candidate_digest_ledger", ()):
            if len(entry) != 3:
                raise RuntimeError("blind data-guided freeze ledger must bind candidate, operator and discovery-fit digests")
            ledger[str(entry[0])] = (str(entry[1]), str(entry[2]))
        frozen_ids = set(ledger)
        frozen_rows = [
            row for row in scan["rows"]
            if row.get("candidate_id") in frozen_ids
            and row.get("status") == "MATERIALIZED_RECONSTRUCTIBLE_FULL_OPERATOR_IDENTITY"
        ]
        heldout_rows = []
        for row in frozen_rows:
            cid = str(row["candidate_id"])
            operator_digest, quality_digest = ledger[cid]
            if operator_digest != row.get("operator_identity_digest") or quality_digest != row.get("discovery_quality_digest"):
                raise RuntimeError("frozen data-guided candidate does not match freeze ledger")
            candidate = self._discovery_row_candidate_contract(row)
            heldout = self.dayabay.heldout_partition_score(
                family="HIGHER_DIMENSIONAL_MICRO_IR",
                candidate_contract=candidate,
                frozen_discovery_profile=row["discovery_quality"],
                heldout_periods=heldout_periods,
            )
            heldout_rows.append({
                "candidate_id": cid,
                "operator_identity_digest": operator_digest,
                "discovery_quality_digest": quality_digest,
                "behavior_cell": row.get("behavior_cell"),
                "primitive_key": row.get("primitive_key"),
                "discovery_chi2": float(row["discovery_quality"]["chi2"]),
                "heldout_chi2": float(heldout["chi2"]),
                "heldout_status": heldout["status"],
                "source_nuisance_refit_on_heldout": heldout["source_nuisance_refit_on_heldout"],
                "heldout_result": heldout,
            })
        reference = self.dayabay.fit_reference_partition(
            discovery_periods=discovery_periods, heldout_periods=heldout_periods
        )
        reference_train = float(reference.get("discovery_chi2", float("nan")))
        reference_hold = float(reference.get("heldout_chi2", float("nan")))
        for row in heldout_rows:
            row["delta_discovery_chi2_vs_partition_reference"] = float(row["discovery_chi2"] - reference_train)
            row["delta_heldout_chi2_vs_partition_reference"] = float(row["heldout_chi2"] - reference_hold)
        by_discovery = sorted(heldout_rows, key=lambda row: (row["discovery_chi2"], row["candidate_id"]))
        predeclared_leader = by_discovery[0] if by_discovery else None
        payload = {
            "schema": "phi-neutrino-blind-data-partition-cycle/v6.10",
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "discovery_owner_id": scan["owner_id"],
            "status": "PASS_BLIND_D_DISCOVERY_BATCH_FROZEN_AND_TEMPORAL_HOLDOUT_EXECUTED" if heldout_rows and all(row["heldout_status"] == "PASS_HELDOUT_PERIOD_PREDICTION_EXECUTED" for row in heldout_rows) else "BLOCKED_BLIND_DATA_PARTITION_CYCLE",
            "data_partition_contract": quality_contract,
            "discovery_scan_digest": scan["digest"],
            "freeze_gate": freeze_gate,
            "frozen_candidate_count": len(heldout_rows),
            "reference_partition_control": reference,
            "predeclared_leader_by_discovery_only": predeclared_leader,
            "heldout_ledger": tuple(sorted(heldout_rows, key=lambda row: row["candidate_id"])),
            "claim_boundary": {
                "heldout_data_visible_before_candidate_freeze": False,
                "heldout_data_used_to_mutate_candidates": False,
                "literature_information_used_in_discovery": False,
                "named_model_family_used_in_discovery": False,
                "candidate_selected_by_heldout_for_final_claim": False,
                "multiple_frozen_candidates_evaluated_on_same_holdout": len(heldout_rows),
                "independent_cross_experiment_replication_still_required": True,
                "literature_novelty_audit_allowed_from_this_cycle_alone": False,
                "new_law_claimed": False,
            },
            "discovery_scan": scan,
        }
        return {**payload, "digest": _digest(payload)}

    def run_qualification(self) -> Mapping[str, Any]:
        if self._qualification_cache is not None:
            return self._qualification_cache
        sample_micro = HigherDimensionalMicroParameters(
            dimensions=1, radii_micrometre=(0.1,), lightest_dirac_mass_ev=0.01,
            kk_modes_per_family=2, family_coupling_scales=(0.05, 0.04, 0.03),
            geometry="FLAT_S1_Z2",
        )
        results = tuple(
            self.evaluate(
                candidate_id=f"GLOBAL-{family}",
                family=family,
                candidate_parameters=sample_micro if family == "HIGHER_DIMENSIONAL_MICRO_IR" else None,
            )
            for family in self.FAMILIES
        )
        directed_qualification = self.phenomenology.run_directed_fullspace_qualification(seed=6701)
        checks = {
            "blind_open_ended_operator_qualification_executed": directed_qualification.get("status") == "PASS_BLIND_OPEN_ENDED_DISCOVERY_QUALIFICATION",
            "high_dimension_operator_identity_executed": directed_qualification.get("execution_summary", {}).get("maximum_executed_dimension", 0) > 4,
            "typed_public_profile_ledger_present": all(row.get("profile_type") == self.PUBLIC_PROFILE_TYPE and len(row.get("evidence_ledger", {})) == len(self.REQUIRED_OWNERS) for row in results),
            "falsification_scope_ledger_present": all(len(row.get("falsification_scope_ledger", {})) == len(self.REQUIRED_OWNERS) for row in results),
            "general_operator_t2k_standard_surface_misuse_blocked": next(row for row in results if row.get("family") == "HIGHER_DIMENSIONAL_MICRO_IR").get("evidence_ledger", {}).get("t2k", {}).get("status") == "BLOCKED_T2K_PUBLISHED_SURFACES_STANDARD_COORDINATES_ONLY",
            "general_operator_atmospheric_scope_gap_classified": next(row for row in results if row.get("family") == "HIGHER_DIMENSIONAL_MICRO_IR").get("evidence_ledger", {}).get("atmospheric", {}).get("status") == "BLOCKED_SUPERK_ATMOSPHERIC_BSM_RESPONSE_FUNCTIONS_UNPUBLISHED",
            "general_operator_solar_scope_gap_classified": next(row for row in results if row.get("family") == "HIGHER_DIMENSIONAL_MICRO_IR").get("evidence_ledger", {}).get("solar", {}).get("status") == "BLOCKED_SUPERK_SOLAR_GENERAL_OPERATOR_RESPONSE_COVARIANCE_UNAVAILABLE",
            "all_families_fail_closed_without_full_artifacts": all(row["status"] == "BLOCKED_GLOBAL_EXPERIMENT_LEVEL_LIKELIHOODS_INCOMPLETE" for row in results),
            "standard_dayabay_public_profile_is_in_active_ledger": results[0].get("evidence_ledger", {}).get("dayabay", {}).get("status") == "PASS_PUBLIC_PROFILE_EXECUTED",
            "dayabay_incomplete_nonoperator_family_contracts_fail_closed": all(
                row.get("evidence_ledger", {}).get("dayabay", {}).get("status") == "BLOCKED_DAYABAY_OPERATOR_IDENTITY_INCOMPLETE"
                for row in results if row.get("family") in {"STERILE_3P1", "NSI", "DECOHERENCE"}
            ),
            "complete_general_owner_lowered_operator_executes_dayabay": next(
                row for row in results if row.get("family") == "HIGHER_DIMENSIONAL_MICRO_IR"
            ).get("evidence_ledger", {}).get("dayabay", {}).get("status") == "PASS_PUBLIC_PROFILE_EXECUTED",
            "same_candidate_digest_bound_across_all_owners": all(
                all(exp.get("candidate_digest") == row["candidate_digest"] for exp in row["experiment_results"].values())
                for row in results
            ),
            "same_microparameters_sent_to_all_owners": all(row.get("same_microparameters_sent_to_all_owners") is True for row in results),
            "no_active_bounded_summary_combination": not hasattr(self, "_standard_predictions"),
            "no_numeric_global_score_without_full_likelihoods": all(row["chi2"] is None for row in results),
            "no_synthetic_substitution": all(row["synthetic_substitution_allowed"] is False for row in results),
            "no_promotion_before_execution": all(row["promotion_allowed"] is False for row in results),
            "reactor_prior_not_double_counted_by_policy": all(row["shared_prior_policy"] == "T2K_WORC_WHEN_DAYABAY_INCLUDED" for row in results),
        }
        upstream_qualifications = {
            "dayabay": self.dayabay.run_qualification(),
            "katrin": self.katrin.run_qualification(),
            "t2k": self.t2k.run_qualification(),
            "atmospheric": self.atmospheric.run_qualification(),
            "solar": self.solar.run_qualification(),
            "external_constraints": self.external_constraints.run_qualification(),
        }
        report = {
            "schema": SCHEMA,
            "release": OWNER_VERSION,
            "owner_id": OWNER_ID,
            "status": "PASS_GLOBAL_OWNER_FAIL_CLOSED_SINGLE_CANDIDATE_CONTRACT" if all(checks.values()) else "BLOCKED_GLOBAL_OWNER",
            "checks": checks,
            "candidate_results": results,
            "directed_fullspace_operator_qualification": {
                "status": directed_qualification.get("status"),
                "row_count": directed_qualification.get("execution_summary", {}).get("row_count"),
                "maximum_executed_dimension": directed_qualification.get("execution_summary", {}).get("maximum_executed_dimension"),
                "maximum_takagi_residual": directed_qualification.get("execution_summary", {}).get("maximum_takagi_residual"),
                "scan_digest": directed_qualification.get("scan_digest"),
                "sha256": directed_qualification.get("sha256"),
            },
            "upstream_owner_status": {
                name: qualification["status"]
                for name, qualification in upstream_qualifications.items()
            },
            "claim_boundary": {
                "published_summary_score_active": False,
                "dayabay_public_detector_period_profile_executed": True,
                "exact_dayabay_reference_software_executed": False,
                "full_global_likelihood_executed": False,
                "global_bsm_competition_executed": False,
                "t2k_standard_parameter_surfaces_used_as_general_operator_likelihood": False,
                "public_product_scope_is_separate_from_artifact_availability": True,
                "blind_open_ended_operator_search_executed": True,
                "synthetic_family_catalog_is_search_boundary": False,
                "public_profile_type": self.PUBLIC_PROFILE_TYPE,
                "one_microparameter_set_enforced": True,
                "sterile_neutrino_detected": False,
                "extra_dimension_detected": False,
                "qualification_lifecycle": "CONTENT_ADDRESSED_SHARED_CACHE_SINGLE_UPSTREAM_QUALIFICATION_PASS",
            },
            "sha256": "",
        }
        report["sha256"] = _digest({**report, "sha256": ""})
        self._qualification_cache = report
        with self._SHARED_QUALIFICATION_LOCK:
            root_key = self._qualification_key[0]
            for key in tuple(self._SHARED_QUALIFICATION_CACHE):
                if key[0] == root_key and key != self._qualification_key:
                    del self._SHARED_QUALIFICATION_CACHE[key]
            self._SHARED_QUALIFICATION_CACHE[self._qualification_key] = deepcopy(report)
        return report

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "schema": SCHEMA,
            "upstream_owners": (
                "DAYA-BAY-FULL-LIKELIHOOD",
                "KATRIN-SPECTRAL-LIKELIHOOD",
                "T2K-PUBLISHED-LIKELIHOOD",
                "SUPERK-ATMOSPHERIC-LIKELIHOOD",
                "SUPERK-SOLAR-LIKELIHOOD",
                "NEUTRINO-EXTERNAL-CONSTRAINTS",
                "NEUTRINO-ALGEBRAIC-EXPERIMENT",
            ),
            "candidate_families": self.FAMILIES,
            "hard_boundaries": (
                "ONE_IMMUTABLE_CANDIDATE_DIGEST_FOR_EVERY_EXPERIMENT",
                "FROZEN_DISCOVERY_OPERATOR_MUST_REHASH_AND_RELOWER_BEFORE_EXPERIMENT_OWNERS",
                "NO_POSTFREEZE_MUTATION_BEFORE_HELDOUT_FALSIFICATION",
                "D_DISCOVERY_NUISANCE_STATE_MUST_BE_DIGEST_BOUND_BEFORE_D_HIDDEN",
                "D_HIDDEN_MUST_NOT_REPROFILE_DISCOVERY_SOURCE_NUISANCE",
                "TEMPORAL_HOLDOUT_IS_INTERNAL_VALIDATION_NOT_CROSS_EXPERIMENT_REPLICATION",
                "PUBLISHED_STANDARD_PARAMETER_SURFACE_IS_NOT_GENERAL_OPERATOR_EVENT_LIKELIHOOD",
                "PUBLIC_PRODUCT_SCOPE_GAP_MUST_NOT_BE_RELABELED_AS_MISSING_DOWNLOAD_ONLY",
                "POSTFREEZE_LITERATURE_NOVELTY_AUDIT_BLOCKED_UNTIL_GLOBAL_REAL_DATA_FALSIFICATION_EXECUTES",
                "NO_CONDITIONAL_SUMMARY_AS_GLOBAL_LIKELIHOOD",
                "NO_DOUBLE_COUNT_OF_SHARED_REACTOR_PRIOR",
                "NO_BSM_PROMOTION_WITHOUT_EXPERIMENT_LEVEL_SHAPES",
                "NO_SYNTHETIC_SUBSTITUTION_FOR_MISSING_REAL_DATA",
                "NO_EXTRA_DIMENSION_DISCOVERY_BEFORE_INDEPENDENT_REPLICATION",
                "PUBLIC_PROFILE_EVIDENCE_CLASS_MUST_REMAIN_TYPED",
                "PARTIAL_EXECUTED_CONTRIBUTIONS_MUST_REMAIN_IN_LEDGER_WHILE_GLOBAL_SCORE_IS_NULL",
                "QUALIFICATION_MUST_NOT_RECREATE_OR_RECOMPUTE_UPSTREAM_OWNER_GRAPH",
                "QUALIFICATION_CACHE_CONTENT_ADDRESSED_BY_ARTIFACT_GENERATION_AND_PARAMETERS",
            ),
        }
        return {**payload, "digest": _digest(payload)}

POSTFREEZE_NOVELTY_OWNER_ID = "NEUTRINO-POSTFREEZE-NOVELTY-AUDIT"
POSTFREEZE_NOVELTY_OWNER_VERSION = "6.9.0"
POSTFREEZE_NOVELTY_SCHEMA = "phi-neutrino-postfreeze-novelty-audit-gate/v6.9"


class NeutrinoPostFreezeNoveltyAuditOwner:
    """Independent gate between held-out falsification and literature audit.

    This owner intentionally does not contain a literature database.  Its job
    is stricter: refuse any novelty query until an immutable frozen operator
    has been re-lowered and the real-data global owner has actually executed.
    External literature search can then consume the returned audit contract,
    but its result is never allowed to mutate the discovery archive.
    """

    owner_id = POSTFREEZE_NOVELTY_OWNER_ID
    owner_version = POSTFREEZE_NOVELTY_OWNER_VERSION
    schema = POSTFREEZE_NOVELTY_SCHEMA

    def evaluate(
        self,
        *,
        frozen_row: Mapping[str, Any],
        freeze_gate: Mapping[str, Any],
        falsification_result: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        candidate_id = str(frozen_row.get("candidate_id", ""))
        operator_digest = str(frozen_row.get("operator_identity_digest", ""))
        ledger = _freeze_ledger_map(freeze_gate)
        discovery_quality_digest = str(frozen_row.get("discovery_quality_digest", ""))
        freeze_ok = (
            freeze_gate.get("status") == "FROZEN_BEFORE_FALSIFICATION_AND_LITERATURE_AUDIT"
            and freeze_gate.get("mutation_after_freeze_allowed") is False
            and bool(candidate_id)
            and ledger.get(candidate_id) == (operator_digest, discovery_quality_digest)
        )
        binding = falsification_result.get("discovery_freeze_binding", {})
        binding_ok = (
            binding.get("status") == "PASS_FROZEN_OPERATOR_REHASHED_AND_RELOWERED"
            and binding.get("discovery_operator_identity_digest") == operator_digest
            and binding.get("discovery_freeze_digest") == freeze_gate.get("freeze_digest")
            and binding.get("postfreeze_mutation_allowed") is False
        )
        heldout_executed = falsification_result.get("status") == "PASS_GLOBAL_EXPERIMENT_LEVEL_LIKELIHOOD_EXECUTED"
        ready = freeze_ok and binding_ok and heldout_executed
        payload = {
            "schema": self.schema,
            "owner_id": self.owner_id,
            "owner_version": self.owner_version,
            "candidate_id": candidate_id,
            "operator_identity_digest": operator_digest,
            "freeze_digest": freeze_gate.get("freeze_digest"),
            "status": "READY_FOR_POSTFREEZE_LITERATURE_NOVELTY_AUDIT" if ready else "BLOCKED_POSTFREEZE_NOVELTY_AUDIT",
            "checks": {
                "candidate_is_in_immutable_freeze_ledger": freeze_ok,
                "falsification_owner_rehashed_and_relowered_same_operator": binding_ok,
                "heldout_real_data_likelihood_executed": heldout_executed,
            },
            "literature_query_allowed": ready,
            "feedback_to_discovery": False,
            "candidate_mutation_allowed": False,
            "novelty_claim_allowed": False,
            "blocking_reason": None if ready else (
                "HELDOUT_REAL_DATA_FALSIFICATION_NOT_EXECUTED" if freeze_ok and binding_ok and not heldout_executed
                else "FREEZE_OR_BINDING_CONTRACT_FAILED"
            ),
            "audit_contract": {
                "comparison_level": "CANONICAL_OPERATOR_STRUCTURE_NOT_MODEL_NAME",
                "remove_trivial_equivalences": (
                    "PARAMETER_RENAMING", "BASIS_PERMUTATION", "UNITARY_FIELD_REDEFINITION",
                    "CONTROLLED_LIMIT_EQUIVALENCE", "TRIVIAL_DIRECT_SUM",
                ),
                "search_only_after_gate": True,
                "discovery_archive_read_only": True,
            },
        }
        return {**payload, "digest": _digest(payload)}

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": self.schema, "owner_id": self.owner_id, "owner_version": self.owner_version,
            "requires_frozen_discovery_digest": True,
            "requires_executed_heldout_real_data_falsification": True,
            "feedback_to_discovery": False,
            "candidate_mutation_allowed": False,
        }
        return {**payload, "digest": _digest(payload)}

