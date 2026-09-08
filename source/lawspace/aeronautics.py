"""Aeronautics/aerostation source-law intersection closure owner.

The owner is intentionally narrow: it does not generate arbitrary couplings.  It
reads the authoritative aviation source-law database, verifies provenance and
content digests, materializes only declared deductive closure families, and runs
numerical identity checks that compare selected closures against their source
equations.

Publication novelty and engineering/certification validity remain separate from
formal source-derived correctness.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping

from .schema import digest_payload
from .domains import DOMAIN_REGISTRIES

OWNER_ID = "AERONAUTICS-LAW-INTERSECTION-CLOSURE"
OWNER_VERSION = "6.15.0"
SCHEMA = "phi-aeronautics-law-intersection-database/v6.15"


class AeronauticsLawIntersectionClosureOwner:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.path = self.root / "data" / "passports" / "aeronautics_intersection_laws.json"
        self.database = json.loads(self.path.read_text(encoding="utf-8"))
        if self.database.get("schema") != SCHEMA:
            raise ValueError("unsupported aeronautics intersection-law database schema")

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
            "closure_family_count": len(db.get("closure_families", ())),
            "registered_axis_count": DOMAIN_REGISTRIES["aeronautics_and_aerostation"].axis_count,
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
                return row
        raise KeyError(owner_id)

    def search_source_laws(
        self, *, owner_id_contains: str | None = None, domain_id: str | None = None, limit: int = 200
    ) -> list[Mapping[str, Any]]:
        rows: list[Mapping[str, Any]] = []
        for row in self.database.get("source_laws", ()):
            if owner_id_contains and owner_id_contains not in str(row.get("owner_id", "")):
                continue
            if domain_id and row.get("domain_id") != domain_id:
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
        limit: int = 500,
    ) -> list[Mapping[str, Any]]:
        rows: list[Mapping[str, Any]] = []
        for row in self.database.get("laws", ()):
            owners = tuple(row.get("source_owner_ids", ()))
            if source_owner_id and source_owner_id not in owners:
                continue
            if classification and row.get("classification") != classification:
                continue
            if novelty_status_contains and novelty_status_contains not in str(row.get("novelty_audit", {}).get("status", "")):
                continue
            if len(owners) < int(min_intersection_order):
                continue
            rows.append(row)
        return rows[: max(0, int(limit))]

    def materialize_family_instance(self, family_id: str, parameters: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        parameters = dict(parameters or {})
        family = next((r for r in self.database.get("closure_families", ()) if r.get("family_id") == family_id), None)
        if family is None:
            raise KeyError(family_id)
        grids = tuple(dict(x) for x in family.get("parameter_grid", ({},)))
        if parameters not in grids:
            raise ValueError("parameters are not a declared deterministic family materialization")
        owners = tuple(str(x) for x in family.get("source_owner_ids", ()))
        usage = dict(family.get("source_usage", {}))
        if set(usage) != set(owners):
            raise ValueError("family source_usage does not account for every source owner")
        if not family.get("validity_intersection"):
            raise ValueError("family has no declared validity intersection")
        return {
            "family_id": family_id,
            "name_ru": str(family.get("name_template", family.get("name_ru", ""))).format(**parameters),
            "formula": str(family.get("formula_template", "")).format(**parameters),
            "source_owner_ids": owners,
            "source_usage": usage,
            "interface_variables": tuple(family.get("interface_variables", ())),
            "validity_intersection": family.get("validity_intersection"),
            "assumptions": tuple(family.get("assumptions", ())),
            "derivation": tuple(family.get("derivation", ())),
            "classification": family.get("classification"),
            "theorem_strength": family.get("theorem_strength"),
            "family_parameters": parameters,
        }

    @staticmethod
    def _numeric_spot_checks() -> Mapping[str, Any]:
        # 1. Finite-wing induced drag closure.
        rho, V, S, CL, e, b = 1.0, 70.0, 20.0, 0.6, 0.82, 12.0
        q = 0.5 * rho * V * V
        W = q * S * CL
        AR = b * b / S
        Cdi = CL * CL / (math.pi * e * AR)
        direct_Di = q * S * Cdi
        closure_Di = 2.0 * W * W / (math.pi * e * rho * V * V * b * b)
        induced_residual = abs(direct_Di - closure_Di) / max(abs(direct_Di), 1.0)

        # 2. Pressure-only Mach closure.  Compare against V/a with an explicit perfect-gas state.
        gamma, Rs, T, p = 1.4, 287.05287, 250.0, 45_000.0
        rho2 = p / (Rs * T)
        w, CL2 = 3_500.0, 0.55
        V2 = math.sqrt(2.0 * w / (rho2 * CL2))
        a2 = math.sqrt(gamma * Rs * T)
        M_direct = V2 / a2
        M_closure = math.sqrt(2.0 * w / (gamma * p * CL2))
        mach_residual = abs(M_direct - M_closure)

        # 3. Gust/stall corridor threshold: at w_min the two speed bounds coincide.
        Kg, Ude, a_lift, CLmax, N = 0.88, 15.0, 5.5, 1.6, 1.5
        rho3 = 1.0
        wmin = Kg**2 * rho3 * Ude**2 * a_lift**2 / (2.0 * CLmax * N**2)
        vstall = math.sqrt(2.0 * wmin / (rho3 * CLmax))
        vgust = 2.0 * wmin * N / (Kg * rho3 * Ude * a_lift)
        gust_corridor_residual = abs(vstall - vgust)

        # 4. Solar-airship size cancellation: equal Umax for two geometrically similar volumes.
        eta, Gs, ks, kd, CD, rho4 = 0.22, 900.0, 0.55, 0.24, 0.05, 0.088
        umax = (2.0 * eta * Gs * ks / (rho4 * CD * kd)) ** (1.0 / 3.0)
        balances = []
        for vol in (1.0e3, 1.0e6):
            As = ks * vol ** (2.0 / 3.0)
            Aref = kd * vol ** (2.0 / 3.0)
            ps = eta * Gs * As
            pd = 0.5 * rho4 * CD * Aref * umax**3
            balances.append(abs(ps - pd) / max(ps, 1.0))
        solar_balance_residual = max(balances)

        # 5. Hybrid induced-power ratio.
        buoyancy_fraction = 0.5
        ratio_formula = (1.0 - buoyancy_fraction) ** 1.5
        W5, rho5, Ad = 100_000.0, 1.0, 120.0
        p0 = W5**1.5 / math.sqrt(2.0 * rho5 * Ad)
        pb = (W5 * (1.0 - buoyancy_fraction))**1.5 / math.sqrt(2.0 * rho5 * Ad)
        hybrid_ratio_residual = abs(pb / p0 - ratio_formula)

        # 6. Airship minimum-volume threshold.
        sigmaA, kA, drho = 0.35, 5.0, 1.0
        vcrit = (sigmaA * kA / drho) ** 3
        net_at_crit = drho * vcrit - sigmaA * kA * vcrit ** (2.0 / 3.0)

        # 7. Range penalty boundary must never exceed the unconstrained optimum when CLg > CL*.
        CD0, k = 0.02, 0.045
        cl_star = math.sqrt(CD0 / k)
        clg = 1.25 * cl_star
        range_ratio = 2.0 * (clg / (CD0 + k * clg * clg)) * math.sqrt(CD0 * k)

        # 8. Spectral gust-load alleviation identity on a discrete quadrature.
        dw = 0.5
        phi = (1.0, 0.8, 0.3)
        gol = (4.0, 2.0, 1.0)
        gcl = (2.0, 1.5, 1.2)
        sigma_ol = sum(g * p for g, p in zip(gol, phi)) * dw / (2.0 * math.pi)
        sigma_cl = sum(g * p for g, p in zip(gcl, phi)) * dw / (2.0 * math.pi)
        delta_direct = sigma_cl - sigma_ol
        delta_formula = sum((gc - go) * p for gc, go, p in zip(gcl, gol, phi)) * dw / (2.0 * math.pi)
        spectral_delta_residual = abs(delta_direct - delta_formula)

        # 9. Weather cubic-moment penalty (strict for a nonconstant nonnegative wind history).
        winds = (5.0, 15.0)
        mean_u = sum(winds) / len(winds)
        mean_u3 = sum(u**3 for u in winds) / len(winds)
        weather_penalty = mean_u3 / mean_u**3

        # 10. Ideal storage capacity equals cumulative-deficit peak-to-trough excursion.
        pnet = (3.0, 3.0, -2.0, -4.0)  # W over equal one-second bins; cycle sum is zero.
        cumulative = [0.0]
        for val in pnet:
            cumulative.append(cumulative[-1] + val)
        ecap = max(cumulative) - min(cumulative)
        storage_cycle_residual = abs(sum(pnet))

        # 11. Thermoelastic dwell identity.
        CA, qnet, Eyoung, alpha, Tw0, Tref, sigallow = 15_000.0, 2_000.0, 70e9, 23e-6, 300.0, 300.0, 120e6
        tmax = (CA / qnet) * (sigallow / (Eyoung * alpha) - (Tw0 - Tref))
        Tw_at = Tw0 + qnet * tmax / CA
        sigma_at = Eyoung * alpha * (Tw_at - Tref)
        dwell_residual = abs(sigma_at - sigallow) / sigallow

        # 12. Transition heat-flux ratio contracts remaining dwell exactly in the reduced model.
        qlam, qout, Rq = 3_000.0, 1_000.0, 2.0
        ratio_029 = (qlam - qout) / (Rq * qlam - qout)
        deltaT = 20.0
        tlam = CA * deltaT / (qlam - qout)
        tturb = CA * deltaT / (Rq * qlam - qout)
        transition_dwell_residual = abs(tturb / tlam - ratio_029)

        # 13. Local wall-heating transition clock reaches the linearized threshold.
        Tinf, Retr0, Re_now, Stheta, qnet_tr = 220.0, 1.20e6, 1.10e6, 4.0e5, 600.0
        ttr = CA * Tinf * (Retr0 - Re_now) / (Stheta * qnet_tr)
        dtheta = qnet_tr * ttr / (CA * Tinf)
        Retr_at = Retr0 - Stheta * dtheta
        transition_clock_residual = abs(Retr_at - Re_now) / Re_now

        return {
            "AIR-CTRL-001": {"residual": induced_residual, "pass": induced_residual < 1.0e-12},
            "AIR-IX-005": {"residual": mach_residual, "pass": mach_residual < 1.0e-12},
            "AIR-IX-008": {"residual": gust_corridor_residual, "pass": gust_corridor_residual < 1.0e-12},
            "AIR-IX-015": {"residual": solar_balance_residual, "pass": solar_balance_residual < 1.0e-12},
            "AIR-IX-017": {"residual": hybrid_ratio_residual, "pass": hybrid_ratio_residual < 1.0e-12},
            "AIR-IX-013": {"residual": abs(net_at_crit), "pass": abs(net_at_crit) < 1.0e-12},
            "AIR-IX-019": {"range_ratio": range_ratio, "pass": 0.0 < range_ratio < 1.0},
            "AIR-IX-022": {"residual": spectral_delta_residual, "delta_sigma_z2": delta_direct, "pass": spectral_delta_residual < 1.0e-12 and delta_direct < 0.0},
            "AIR-IX-026": {"K_weather": weather_penalty, "pass": weather_penalty > 1.0},
            "AIR-IX-027": {"E_cap_min": ecap, "cycle_residual": storage_cycle_residual, "pass": ecap > 0.0 and storage_cycle_residual < 1.0e-12},
            "AIR-IX-028": {"residual": dwell_residual, "t_max": tmax, "pass": tmax > 0.0 and dwell_residual < 1.0e-12},
            "AIR-IX-029": {"residual": transition_dwell_residual, "remaining_time_ratio": ratio_029, "pass": 0.0 < ratio_029 < 1.0 and transition_dwell_residual < 1.0e-12},
            "AIR-IX-030": {"residual": transition_clock_residual, "t_transition": ttr, "pass": ttr > 0.0 and transition_clock_residual < 1.0e-12},
        }

    def run_qualification(self) -> Mapping[str, Any]:
        db = self.database
        stored = str(db.get("database_digest", ""))
        database_digest_ok = stored == digest_payload({k: v for k, v in db.items() if k != "database_digest"})

        source_laws = list(db.get("source_laws", ()))
        laws = list(db.get("laws", ()))
        families = list(db.get("closure_families", ()))
        source_ids = [str(x.get("owner_id")) for x in source_laws]
        law_ids = [str(x.get("law_id")) for x in laws]
        family_ids = [str(x.get("family_id")) for x in families]

        source_digests_ok = all(
            row.get("source_law_digest") == digest_payload({**row, "source_law_digest": ""}) for row in source_laws
        )
        law_digests_ok = all(row.get("law_digest") == digest_payload({**row, "law_digest": ""}) for row in laws)
        family_digests_ok = all(
            row.get("family_digest") == digest_payload({**row, "family_digest": ""}) for row in families
        )

        passport_ids: set[str] = set()
        for path in sorted((self.root / "data" / "passports").glob("known_*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    passport_ids.add(str(json.loads(line)["owner_id"]))
        source_owners_resolve = set(source_ids).issubset(passport_ids)
        all_law_sources_resolve = all(set(row.get("source_owner_ids", ())).issubset(set(source_ids)) for row in laws)

        family_by_id = {str(row.get("family_id")): row for row in families}
        family_links_ok = all(
            row.get("closure_family_id") in family_by_id
            and tuple(row.get("source_owner_ids", ())) == tuple(family_by_id[row["closure_family_id"]].get("source_owner_ids", ()))
            and row.get("formula") == family_by_id[row["closure_family_id"]].get("formula_template")
            for row in laws
        )
        source_usage_complete = all(
            set(row.get("source_usage", {})) == set(row.get("source_owner_ids", ())) for row in laws + families
        )
        variables_complete = all(
            row.get("variables") and all(v.get("symbol") and v.get("meaning_ru") and v.get("role") for v in row.get("variables", ()))
            for row in laws + source_laws
        )
        validity_complete = all(str(row.get("validity_intersection", "")).strip() for row in laws)
        derivations_complete = all(row.get("derivation") for row in laws)
        novelty_separated = all(
            row.get("novelty_audit", {}).get("status")
            and row.get("novelty_audit", {}).get("feedback_to_derivation") is False
            for row in laws
        )
        no_novelty_overclaim = all(
            "NOVELTY_NOT_ESTABLISHED" in str(row.get("novelty_audit", {}).get("status", ""))
            or "NOVELTY_NOT_CLAIMED" in str(row.get("novelty_audit", {}).get("status", ""))
            or str(row.get("novelty_audit", {}).get("status", "")).startswith("KNOWN_")
            for row in laws
        )
        no_fixed_order_ceiling = db.get("closure_engine", {}).get("fixed_intersection_order_ceiling") is None
        no_fixed_candidate_ceiling = db.get("closure_engine", {}).get("fixed_materialized_candidate_ceiling") is None
        on_demand_higher_order = db.get("closure_engine", {}).get("on_demand_higher_order_materialization") is True
        random_disabled = db.get("closure_engine", {}).get("random_candidate_generation") is False
        axis_registry_ok = DOMAIN_REGISTRIES["aeronautics_and_aerostation"].axis_count == 175

        spots = self._numeric_spot_checks()
        spot_checks_ok = all(bool(row.get("pass")) for row in spots.values())

        checks = {
            "database_digest_ok": database_digest_ok,
            "source_ids_unique": len(source_ids) == len(set(source_ids)) and bool(source_ids),
            "law_ids_unique": len(law_ids) == len(set(law_ids)) and bool(law_ids),
            "family_ids_unique": len(family_ids) == len(set(family_ids)) and bool(family_ids),
            "source_digests_ok": source_digests_ok,
            "law_digests_ok": law_digests_ok,
            "family_digests_ok": family_digests_ok,
            "source_owners_resolve_to_canonical_passports": source_owners_resolve,
            "all_intersection_sources_are_registered_source_laws": all_law_sources_resolve,
            "family_links_reproduce_materializations": family_links_ok,
            "source_usage_accounts_for_every_owner": source_usage_complete,
            "variables_are_explicit": variables_complete,
            "validity_intersections_are_explicit": validity_complete,
            "derivations_are_explicit": derivations_complete,
            "novelty_is_post_derivation_and_separate": novelty_separated,
            "publication_novelty_is_not_overclaimed": no_novelty_overclaim,
            "no_fixed_intersection_order_ceiling": no_fixed_order_ceiling,
            "no_fixed_materialized_candidate_ceiling": no_fixed_candidate_ceiling,
            "on_demand_higher_order_materialization_enabled": on_demand_higher_order,
            "random_formula_generation_disabled": random_disabled,
            "aeronautics_axis_registry_175_loaded": axis_registry_ok,
            "numeric_source_equation_spot_checks": spot_checks_ok,
        }
        report = {
            "schema": "phi-aeronautics-law-intersection-qualification/v6.15",
            "owner_id": OWNER_ID,
            "owner_version": OWNER_VERSION,
            "status": "PASS_AERONAUTICS_SOURCE_LAW_INTERSECTION_CLOSURE" if all(checks.values()) else "BLOCKED_AERONAUTICS_SOURCE_LAW_INTERSECTION_CLOSURE",
            "database_digest": stored,
            "checks": checks,
            "counts": dict(db.get("counts", {})),
            "numeric_spot_checks": spots,
            "strongest_materialized_cells": [
                "AIR-IX-008", "AIR-IX-009", "AIR-IX-015", "AIR-IX-019", "AIR-IX-020", "AIR-IX-022", "AIR-IX-024", "AIR-IX-025", "AIR-IX-026", "AIR-IX-027", "AIR-IX-028", "AIR-IX-029", "AIR-IX-030"
            ],
            "claim_boundary": dict(db.get("claim_boundary", {})),
            "sha256": "",
        }
        report["sha256"] = digest_payload({**report, "sha256": ""})
        return report
