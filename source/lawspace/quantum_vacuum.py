"""Quantum-vacuum / semiclassical-gravity source-law intersection owner.

This owner closes one specific research-region in the global Φ-LawSpace:
renormalized quantum stress-energy, Casimir boundary conditions, semiclassical
Einstein backreaction, conservation/equivalence and quantum-energy-inequality
gates.  It deliberately distinguishes a local negative stress-energy region
from the total conserved stress-energy of a complete apparatus.

Formal deductive closure is not a claim of engineering antigravity, full
quantum gravity, or publication novelty.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping

from .domains import BASE_DOMAIN_REGISTRIES, DOMAIN_REGISTRIES
from .schema import digest_payload

OWNER_ID = "QUANTUM-VACUUM-GRAVITY-INTERSECTION-CLOSURE"
OWNER_VERSION = "6.16.0"
SCHEMA = "phi-quantum-vacuum-gravity-intersection-database/v6.16"


class QuantumVacuumGravityIntersectionOwner:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.path = self.root / "data" / "passports" / "quantum_vacuum_gravity_intersection_laws.json"
        self.database = json.loads(self.path.read_text(encoding="utf-8"))
        if self.database.get("schema") != SCHEMA:
            raise ValueError("unsupported quantum-vacuum gravity intersection database schema")

    def contract(self) -> Mapping[str, Any]:
        db = self.database
        return {
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "schema": SCHEMA,
            "domain_id": db.get("domain_id"),
            "database_digest": db.get("database_digest"),
            "source_law_count": len(db.get("source_laws", ())),
            "intersection_law_count": len(db.get("laws", ())),
            "global_registered_axis_count": sum(reg.axis_count for reg in DOMAIN_REGISTRIES.values()),
            "max_materialized_intersection_order": db.get("counts", {}).get("max_materialized_intersection_order"),
            "fixed_intersection_order_ceiling": db.get("closure_engine", {}).get("fixed_intersection_order_ceiling"),
            "fixed_materialized_candidate_ceiling": db.get("closure_engine", {}).get("fixed_materialized_candidate_ceiling"),
            "generation_policy": db.get("closure_engine", {}).get("generation_policy"),
            "random_candidate_generation": db.get("closure_engine", {}).get("random_candidate_generation"),
            "literature_feedback_to_derivation": db.get("closure_engine", {}).get("literature_feedback_to_derivation"),
            "claim_boundary": dict(db.get("claim_boundary", {})),
        }

    def get_source_law(self, owner_id: str) -> Mapping[str, Any]:
        for row in self.database.get("source_laws", ()):
            if row.get("owner_id") == owner_id:
                passport = self.root / "data" / "passports"
                for path in sorted(passport.glob("known_*.jsonl")):
                    for line in path.read_text(encoding="utf-8").splitlines():
                        if not line.strip():
                            continue
                        item = json.loads(line)
                        if item.get("owner_id") == owner_id:
                            return {**row, "passport": item}
                raise RuntimeError(f"canonical passport missing for quantum-vacuum source owner {owner_id}")
        raise KeyError(owner_id)

    def search_source_laws(self, *, owner_id_contains: str | None = None, limit: int = 100) -> list[Mapping[str, Any]]:
        rows = []
        for row in self.database.get("source_laws", ()):
            if owner_id_contains and owner_id_contains not in str(row.get("owner_id", "")):
                continue
            rows.append(row)
        return rows[: max(0, int(limit))]

    def get_law(self, law_id: str) -> Mapping[str, Any]:
        for row in self.database.get("laws", ()):
            if row.get("law_id") == law_id:
                return row
        raise KeyError(law_id)

    def search(
        self,
        *,
        source_owner_id: str | None = None,
        classification: str | None = None,
        novelty_status_contains: str | None = None,
        min_intersection_order: int = 0,
        limit: int = 200,
    ) -> list[Mapping[str, Any]]:
        rows: list[Mapping[str, Any]] = []
        for row in self.database.get("laws", ()):
            owners = tuple(row.get("source_owner_ids", ()))
            if source_owner_id and source_owner_id not in owners:
                continue
            if classification and row.get("classification") != classification:
                continue
            novelty = str(row.get("novelty_audit", {}).get("status", ""))
            if novelty_status_contains and novelty_status_contains not in novelty:
                continue
            if len(owners) < int(min_intersection_order):
                continue
            rows.append(row)
        return rows[: max(0, int(limit))]

    @staticmethod
    def _numeric_spot_checks() -> Mapping[str, Any]:
        hbar = 1.054571817e-34
        c = 299_792_458.0
        G = 6.67430e-11
        g = 9.80665

        # Brown-Maclay ideal parallel-plate benchmark.
        a = 1.0e-9
        sigma_matter = 1.0e-6
        C = math.pi**2 * hbar * c / (720.0 * a**4)
        u, px, py, pz = -C, C, C, -3.0 * C
        mu_active_direct = (u + px + py + pz) / c**2
        mu_active_formula = -math.pi**2 * hbar / (360.0 * c * a**4)
        active_mass_residual = abs(mu_active_direct - mu_active_formula) / abs(mu_active_formula)

        # Characteristic semiclassical source-curvature and geodesic-deviation scales.
        K_direct = 8.0 * math.pi * G * abs(u) / c**4
        K_formula = math.pi**3 * G * hbar / (90.0 * c**3 * a**4)
        curvature_residual = abs(K_direct - K_formula) / K_formula
        ell = a
        tidal = c**2 * K_formula * ell
        tidal_formula = math.pi**3 * G * hbar * ell / (90.0 * c * a**4)
        tidal_residual = abs(tidal - tidal_formula) / tidal_formula

        # Complete-apparatus mass figure of merit and inverse critical-gap relation.
        sigma_c = math.pi**2 * hbar / (720.0 * c * a**3)
        eta = sigma_c / sigma_matter
        acrit = (math.pi**2 * hbar / (720.0 * c * sigma_matter)) ** (1.0 / 3.0)
        eta_at_acrit = math.pi**2 * hbar / (720.0 * c * acrit**3 * sigma_matter)
        inverse_residual = abs(eta_at_acrit - 1.0)

        # Weak-gravity force and mechanical-pressure scale separation.
        f_up_area = g * sigma_c
        p_c = math.pi**2 * hbar * c / (240.0 * a**4)
        rgc_direct = f_up_area / p_c
        rgc_formula = g * a / (3.0 * c**2)
        rgc_residual = abs(rgc_direct - rgc_formula) / rgc_formula

        # Fewster-Eveson sampling rescaling: the 4D lower-bound functional scales lambda^-4.
        lam = 3.0
        qei_ratio = lam ** -4
        qei_expected = 1.0 / 81.0
        qei_residual = abs(qei_ratio - qei_expected)

        # Explicit positive-total-mass benchmark prevents local-field/whole-device conflation.
        area = 1.0
        matter_mass = sigma_matter * area
        ec = -math.pi**2 * hbar * c * area / (720.0 * a**3)
        total_mass = matter_mass + ec / c**2

        return {
            "QVAC-IX-001": {"relative_residual": active_mass_residual, "mu_active_kg_m3": mu_active_formula, "pass": active_mass_residual < 1e-12},
            "QVAC-IX-002": {"relative_residual": curvature_residual, "K_C_m-2": K_formula, "pass": curvature_residual < 1e-12},
            "QVAC-IX-003": {"relative_residual": tidal_residual, "a_tidal_m_s2_at_1nm": tidal, "pass": tidal_residual < 1e-12 and tidal > 0.0},
            "QVAC-IX-005": {"eta_C_at_a_1nm_sigma_1e-6": eta, "pass": 4.8e-12 < eta < 4.9e-12},
            "QVAC-IX-006": {"a_crit_m_at_sigma_1e-6": acrit, "inverse_residual": inverse_residual, "pass": inverse_residual < 1e-12},
            "QVAC-IX-007": {"upward_weight_N_m2_at_1nm": f_up_area, "pass": f_up_area > 0.0},
            "QVAC-IX-008": {"relative_residual": rgc_residual, "R_gC_at_1nm": rgc_formula, "pass": rgc_residual < 1e-12 and rgc_formula < 1e-20},
            "QVAC-IX-009": {"lambda": lam, "bound_ratio": qei_ratio, "residual": qei_residual, "pass": qei_residual < 1e-15},
            "QVAC-IX-011": {"complete_apparatus_mass_kg": total_mass, "pass": total_mass > 0.0 and eta < 1.0},
        }

    def run_qualification(self) -> Mapping[str, Any]:
        db = self.database
        expected_digest = digest_payload({k: v for k, v in db.items() if k != "database_digest"})
        source_ids = [str(row.get("owner_id")) for row in db.get("source_laws", ())]
        laws = list(db.get("laws", ()))
        law_ids = [str(row.get("law_id")) for row in laws]

        passport_ids: set[str] = set()
        for path in sorted((self.root / "data" / "passports").glob("known_*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    passport_ids.add(str(json.loads(line)["owner_id"]))

        source_usage_complete = all(
            set(row.get("source_usage", {})) == set(row.get("source_owner_ids", ())) for row in laws
        )
        source_resolution = set(source_ids).issubset(passport_ids)
        law_sources_resolve = all(set(row.get("source_owner_ids", ())).issubset(set(source_ids)) for row in laws)
        validity_complete = all(str(row.get("validity_intersection", "")).strip() for row in laws)
        derivations_complete = all(bool(row.get("derivation")) for row in laws)
        falsification_complete = all(bool(row.get("falsification_criterion")) for row in laws)
        observables_complete = all(bool(row.get("observables")) for row in laws)
        novelty_separate = all(bool(row.get("novelty_audit", {}).get("status")) for row in laws)
        cb = dict(db.get("claim_boundary", {}))
        claim_boundary_ok = (
            cb.get("antigravity_device") == "NOT_ESTABLISHED"
            and cb.get("net_negative_gravitational_mass") == "NOT_ESTABLISHED"
            and str(cb.get("gravity_decoupling", "")).startswith("NOT_SUPPORTED")
            and cb.get("quantum_gravity") == "NOT_SOLVED_BY_SEMICLASSICAL_EQUATION"
        )
        no_fixed_order_ceiling = db.get("closure_engine", {}).get("fixed_intersection_order_ceiling") is None
        no_fixed_candidate_ceiling = db.get("closure_engine", {}).get("fixed_materialized_candidate_ceiling") is None
        random_disabled = db.get("closure_engine", {}).get("random_candidate_generation") is False
        literature_not_in_derivation = db.get("closure_engine", {}).get("literature_feedback_to_derivation") is False
        spots = self._numeric_spot_checks()

        checks = {
            "database_digest_ok": db.get("database_digest") == expected_digest,
            "source_ids_unique": bool(source_ids) and len(source_ids) == len(set(source_ids)),
            "intersection_ids_unique": bool(law_ids) and len(law_ids) == len(set(law_ids)),
            "source_owners_resolve_to_canonical_passports": source_resolution,
            "all_intersection_sources_are_registered_source_laws": law_sources_resolve,
            "source_usage_accounts_for_every_owner": source_usage_complete,
            "validity_intersections_are_explicit": validity_complete,
            "derivations_are_explicit": derivations_complete,
            "observables_are_explicit": observables_complete,
            "falsification_paths_are_explicit": falsification_complete,
            "novelty_status_is_separate": novelty_separate,
            "claim_boundary_blocks_antigravity_overclaim": claim_boundary_ok,
            "no_fixed_intersection_order_ceiling": no_fixed_order_ceiling,
            "no_fixed_materialized_candidate_ceiling": no_fixed_candidate_ceiling,
            "random_formula_generation_disabled": random_disabled,
            "literature_does_not_feed_back_into_derivation": literature_not_in_derivation,
            "global_axis_registry_current_preserved": all(set(BASE_DOMAIN_REGISTRIES[d].axes).issubset(DOMAIN_REGISTRIES[d].axes) for d in BASE_DOMAIN_REGISTRIES),
            "numeric_source_equation_spot_checks": all(bool(row.get("pass")) for row in spots.values()),
        }
        report = {
            "schema": "phi-quantum-vacuum-gravity-intersection-qualification/v6.16",
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "status": "PASS_QUANTUM_VACUUM_GRAVITY_INTERSECTION_CLOSURE" if all(checks.values()) else "BLOCKED_QUANTUM_VACUUM_GRAVITY_INTERSECTION_CLOSURE",
            "database_digest": db.get("database_digest"),
            "checks": checks,
            "counts": dict(db.get("counts", {})),
            "numeric_spot_checks": spots,
            "strongest_materialized_cells": [
                "QVAC-IX-001", "QVAC-IX-002", "QVAC-IX-003", "QVAC-IX-005",
                "QVAC-IX-006", "QVAC-IX-008", "QVAC-IX-010", "QVAC-IX-011",
            ],
            "claim_boundary": cb,
            "sha256": "",
        }
        report["sha256"] = digest_payload({**report, "sha256": ""})
        return report
