"""Owner of model-scope gates for cosmological and gravitational constraints.

Cosmological neutrino-mass limits depend on the cosmological model and data
combination.  Short-distance gravity limits constrain only geometries whose
extra dimensions couple to gravity with the declared compactification scope.
The owner therefore refuses to apply a scalar bound until thermal history,
field localisation, and portal scope are supplied by the same candidate IR.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

OWNER_ID = "NEUTRINO-EXTERNAL-CONSTRAINTS"
OWNER_VERSION = "5.6.0"
SCHEMA = "phi-neutrino-external-constraints/v5.6"


def _digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=float).encode()).hexdigest()


class NeutrinoExternalConstraintsOwner:
    REQUIRED_HIGHER_DIMENSIONAL_SCOPE = (
        "thermal_history_model",
        "gravity_portal_scope",
        "field_localisation_contract",
    )

    def evaluate(self, *, family: str, candidate_contract: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        candidate_contract = dict(candidate_contract or {"family": family, "digest": _digest({"family": family, "qualification": True})})
        if candidate_contract.get("family") != family or not candidate_contract.get("digest"):
            raise ValueError("candidate contract must bind the same family and a non-empty digest")
        candidate_digest = str(candidate_contract["digest"])
        micro = dict(candidate_contract.get("microscopic_parameters") or {})
        missing_scope = tuple(key for key in self.REQUIRED_HIGHER_DIMENSIONAL_SCOPE if family == "HIGHER_DIMENSIONAL_MICRO_IR" and key not in micro)
        if missing_scope:
            return {
                "family": family,
                "candidate_digest": candidate_digest,
                "status": "BLOCKED_EXTERNAL_CONSTRAINT_MODEL_SCOPE_INCOMPLETE",
                "missing_scope": missing_scope,
                "chi2": None,
                "external_constraints_executed": False,
                "promotion_allowed": False,
            }
        return {
            "family": family,
            "candidate_digest": candidate_digest,
            "status": "BLOCKED_EXTERNAL_COSMOLOGY_GRAVITY_LIKELIHOOD_PRODUCTS_NOT_MATERIALIZED",
            "model_scope": {key: micro.get(key) for key in self.REQUIRED_HIGHER_DIMENSIONAL_SCOPE},
            "chi2": None,
            "external_constraints_executed": False,
            "promotion_allowed": False,
            "reason": "MODEL_DEPENDENT_COSMOLOGICAL_AND_GRAVITATIONAL_LIKELIHOODS_MUST_BE_DECLARED_AND_INGESTED_SEPARATELY",
        }

    def run_qualification(self) -> Mapping[str, Any]:
        missing = self.evaluate(family="HIGHER_DIMENSIONAL_MICRO_IR", candidate_contract={
            "family": "HIGHER_DIMENSIONAL_MICRO_IR", "digest": "qualification", "microscopic_parameters": {}
        })
        scoped = self.evaluate(family="HIGHER_DIMENSIONAL_MICRO_IR", candidate_contract={
            "family": "HIGHER_DIMENSIONAL_MICRO_IR",
            "digest": "qualification-scoped",
            "microscopic_parameters": {
                "thermal_history_model": "DECLARED_NOT_EXECUTED",
                "gravity_portal_scope": "NEUTRINO_ONLY_OR_UNIVERSAL_MUST_BE_RESOLVED",
                "field_localisation_contract": "DECLARED_NOT_EXECUTED",
            },
        })
        checks = {
            "incomplete_scope_fails_closed": missing["status"] == "BLOCKED_EXTERNAL_CONSTRAINT_MODEL_SCOPE_INCOMPLETE",
            "scoped_candidate_still_requires_likelihood_products": scoped["status"] == "BLOCKED_EXTERNAL_COSMOLOGY_GRAVITY_LIKELIHOOD_PRODUCTS_NOT_MATERIALIZED",
            "no_generic_cosmological_scalar_bound": missing["chi2"] is None and scoped["chi2"] is None,
            "no_generic_gravity_bound_on_neutrino_only_dimension": scoped["promotion_allowed"] is False,
        }
        report = {
            "schema": SCHEMA,
            "release": OWNER_VERSION,
            "owner_id": OWNER_ID,
            "status": "PASS_EXTERNAL_CONSTRAINT_SCOPE_GATE_FAIL_CLOSED" if all(checks.values()) else "BLOCKED_EXTERNAL_CONSTRAINT_OWNER",
            "checks": checks,
            "unscoped_route": missing,
            "scoped_route": scoped,
            "claim_boundary": {
                "cosmological_limit_is_model_dependent": True,
                "gravity_limit_requires_universal_or_declared_portal": True,
                "external_constraint_likelihood_executed": False,
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
            "required_higher_dimensional_scope": self.REQUIRED_HIGHER_DIMENSIONAL_SCOPE,
            "hard_boundaries": (
                "NO_COSMOLOGICAL_LIMIT_WITHOUT_COSMOLOGICAL_MODEL",
                "NO_GRAVITY_LIMIT_WITHOUT_PORTAL_SCOPE",
                "NO_THERMAL_KK_POPULATION_ASSUMED_WITHOUT_THERMAL_HISTORY",
                "NO_DISCOVERY_CLAIM_FROM_EXTERNAL_PRIOR_ALONE",
            ),
        }
        return {**payload, "digest": _digest(payload)}
