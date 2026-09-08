"""Dimensional scalar-law birth for Atlas candidate subspaces.

This owner closes the cheapest part of SUBSPACE -> FORMULA.  It never treats
scientific-coordinate axis ids as physical quantities.  Instead it projects a
subspace through its already-qualified source owners to quantity-bearing symbols,
uses their declared 7D SI dimensions, excludes dimensionless quantities from the
Buckingham rank count, and freezes Pi=C only when the exact nullity is one.

Pi=C is a *candidate relation*, not an established law and not evidence that C is
universal.  Distinct candidate ids sharing the same canonical Pi signature belong
to one dimensional prediction-equivalence class at this stage.
"""
from __future__ import annotations

from fractions import Fraction
import math
from typing import Any, Mapping, Sequence

from source.phi_compiler_owner import _fraction_nullspace, _fraction_rref
from .schema import digest_payload

OWNER_ID = "DIMENSIONAL-SCALAR-LAW-BIRTH/1.0.0"
BASIS = ("L", "M", "T", "I", "Theta", "N", "J")


def _dim_tuple(symbol: Any) -> tuple[int, ...] | None:
    d = getattr(symbol, "dimension", None)
    if d is None:
        return None
    raw = (d.length, d.mass, d.time, d.current, d.temperature, d.amount, d.luminous_intensity)
    try:
        return tuple(int(Fraction(str(x))) for x in raw)
    except Exception:
        return None


def _canonical_integer_group(vector: Sequence[Fraction], quantity_ids: Sequence[str]) -> tuple[tuple[str, int], ...]:
    vals = [Fraction(x) for x in vector]
    den = 1
    for x in vals:
        den = math.lcm(den, x.denominator)
    ints = [int(x * den) for x in vals]
    gcd = 0
    for x in ints:
        if x:
            gcd = math.gcd(gcd, abs(x))
    if gcd:
        ints = [x // gcd for x in ints]
    first = next((x for x in ints if x), 1)
    if first < 0:
        ints = [-x for x in ints]
    return tuple((str(q), int(e)) for q, e in zip(quantity_ids, ints) if e)


def _formula_text(group: Sequence[tuple[str, int]]) -> str:
    def term(q: str, e: int) -> str:
        return q if e == 1 else f"{q}^{e}"
    return " * ".join(term(q, e) for q, e in group) + " = C_DIMENSIONLESS"


class DimensionalScalarLawBirthOwner:
    owner_id = OWNER_ID

    def quantity_projection(self, record: Mapping[str, Any], catalog: Any) -> Mapping[str, Any]:
        by_q: dict[str, dict[str, Any]] = {}
        for owner_id in record.get("source_owner_ids", record.get("owner_ids", ())):
            passport = catalog.passports.get(str(owner_id))
            if passport is None:
                continue
            for symbol in passport.symbols:
                qid = str(symbol.quantity_id or "").strip()
                dim = _dim_tuple(symbol)
                if not qid or dim is None or not any(dim):
                    # §3 of the Atlas paper: dimensionless/categorical coordinates
                    # do not reduce the dimension matrix and are not counted here.
                    continue
                row = by_q.setdefault(qid, {"quantity_id": qid, "dimension": dim, "source_owner_ids": set(), "symbols": set()})
                row["source_owner_ids"].add(str(owner_id))
                row["symbols"].add(str(symbol.display))
        rows = []
        for qid in sorted(by_q):
            row = by_q[qid]
            rows.append({
                "quantity_id": qid,
                "dimension": list(row["dimension"]),
                "source_owner_ids": sorted(row["source_owner_ids"]),
                "symbols": sorted(row["symbols"]),
            })
        return {
            "quantity_count": len(rows),
            "quantities": rows,
            "dimensionless_quantities_excluded_from_rank": True,
            "axis_ids_are_not_treated_as_physical_quantities": True,
        }

    def freeze(self, record: Mapping[str, Any], catalog: Any) -> Mapping[str, Any]:
        projection = self.quantity_projection(record, catalog)
        qrows = list(projection["quantities"])
        qids = [row["quantity_id"] for row in qrows]
        if not qids:
            core = {
                "schema": "phi-dimensional-scalar-law-birth/v1", "owner": OWNER_ID,
                "candidate_id": record.get("candidate_id"), "status": "NO_DIMENSIONFUL_QUANTITY_PROJECTION",
                "quantity_projection": projection, "scalar_equation_frozen": False,
                "claim_boundary": {"law_established": False, "candidate_formula_established": False},
            }
            return {**core, "digest": digest_payload(core)}
        dims = [tuple(int(x) for x in row["dimension"]) for row in qrows]
        matrix = [[dims[j][i] for j in range(len(qids))] for i in range(7)]
        _rref, pivots = _fraction_rref(matrix)
        nullspace = _fraction_nullspace(matrix)
        nullity = len(nullspace)
        base = {
            "schema": "phi-dimensional-scalar-law-birth/v1", "owner": OWNER_ID,
            "candidate_id": record.get("candidate_id"), "candidate_record_digest": record.get("digest"),
            "quantity_projection": projection, "rank": len(pivots), "nullity": nullity,
        }
        if nullity != 1:
            status = "DIMENSIONAL_RELATION_ABSENT_P0" if nullity == 0 else "FUNCTION_FORM_REQUIRED_P_GT_1"
            core = {**base, "status": status, "scalar_equation_frozen": False,
                    "claim_boundary": {"law_established": False, "candidate_formula_established": False,
                                       "function_form_search_required": nullity > 1}}
            return {**core, "digest": digest_payload(core)}
        group = _canonical_integer_group(nullspace[0], qids)
        signature = digest_payload({"group": group})
        core = {
            **base,
            "status": "DIMENSIONAL_PI_CONSTANT_CANDIDATE_FROZEN",
            "representation_kind": "SCALAR_DIMENSIONAL_PI_CONSTANT_CANDIDATE",
            "scalar_equation_frozen": True,
            "pi_group": [{"quantity_id": q, "exponent": e} for q, e in group],
            "pi_signature": signature,
            "formula": _formula_text(group),
            "constant_symbol": "C_DIMENSIONLESS",
            "claim_boundary": {
                "law_established": False,
                "universal_constant_established": False,
                "candidate_formula_established": True,
                "dimension_analysis_alone_establishes_world_relation": False,
                "data_collapse_and_ood_still_required": True,
            },
        }
        return {**core, "digest": digest_payload(core)}

    def audit_records(self, records: Sequence[Mapping[str, Any]], catalog: Any, *, u4_candidate_ids: Sequence[str] = ()) -> Mapping[str, Any]:
        births = [self.freeze(row, catalog) for row in records]
        frozen = [b for b in births if b.get("scalar_equation_frozen") is True]
        sigs: dict[str, list[str]] = {}
        for b in frozen:
            sigs.setdefault(str(b["pi_signature"]), []).append(str(b["candidate_id"]))
        u4 = set(str(x) for x in u4_candidate_ids)
        u4_frozen = [b for b in frozen if str(b["candidate_id"]) in u4]
        u4_sigs = {str(b["pi_signature"]) for b in u4_frozen}
        summary = {
            "subspace_count": len(records),
            "with_dimensionful_quantity_projection": sum(int(b.get("quantity_projection", {}).get("quantity_count", 0)) > 0 for b in births),
            "with_at_least_two_dimensionful_quantities": sum(int(b.get("quantity_projection", {}).get("quantity_count", 0)) >= 2 for b in births),
            "p0_count": sum(b.get("status") == "DIMENSIONAL_RELATION_ABSENT_P0" for b in births),
            "p1_frozen_formula_count": len(frozen),
            "p_gt_1_function_form_required_count": sum(b.get("status") == "FUNCTION_FORM_REQUIRED_P_GT_1" for b in births),
            "no_dimensionful_quantity_projection_count": sum(b.get("status") == "NO_DIMENSIONFUL_QUANTITY_PROJECTION" for b in births),
            "unique_pi_signature_count": len(sigs),
            "u4_candidate_count": len(u4),
            "u4_p1_frozen_formula_count": len(u4_frozen),
            "u4_unique_pi_signature_count": len(u4_sigs),
        }
        core = {
            "schema": "phi-dimensional-scalar-law-birth-audit/v1", "owner": OWNER_ID,
            "status": "PASS_DIMENSIONAL_SCALAR_LAW_BIRTH_AUDIT", "summary": summary,
            "unique_pi_classes": [
                {"pi_signature": sig, "candidate_count": len(ids), "candidate_ids": sorted(ids),
                 "representative": next(b for b in frozen if b["pi_signature"] == sig)}
                for sig, ids in sorted(sigs.items())
            ],
            "births": births,
            "claim_boundary": {
                "p1_births_are_confirmed_laws": False,
                "candidate_id_count_equals_mathematical_diversity": False,
                "unique_pi_signature_is_the_dimensional_equivalence_key": True,
            },
        }
        return {**core, "digest": digest_payload(core)}


def collapse_score(x, y, *, nbins: int = 12, min_pts: int = 6) -> float:
    """Exact operational collapse metric used by the Atlas v1.0 methodology."""
    import numpy as np
    x=np.asarray(x,float); y=np.asarray(y,float)
    if len(x)!=len(y) or len(x)==0 or np.any(x<=0) or np.any(y<=0):
        raise ValueError("collapse_score requires positive paired observations")
    lx=np.log10(x); edges=np.linspace(lx.min(),lx.max(),int(nbins)+1); sc=[]
    for i in range(int(nbins)):
        mask=(lx>=edges[i])&(lx<edges[i+1])
        if int(mask.sum())>=int(min_pts):
            sc.append(float(np.std(np.log(y[mask]))))
    if not sc:
        raise ValueError("no collapse bins satisfy min_pts")
    denom=float(np.std(np.log(y)))
    if denom<=0:
        raise ValueError("target has zero log-variance")
    return float(np.mean(sc)/denom)


class ScalarLawUtilityOwner:
    """SO-WHAT assessment executed only for an already frozen scalar candidate."""
    owner_id="SCALAR-LAW-UTILITY/1.0.0"

    def assess_collapse(self, *, frozen_formula: Mapping[str, Any], pi_values, response_values,
                        alternative_coordinates: Mapping[str, Sequence[float]] = {}, system_ids: Sequence[str] = (),
                        collapse_threshold: float = 0.15) -> Mapping[str, Any]:
        if frozen_formula.get("scalar_equation_frozen") is not True:
            raise ValueError("SO-WHAT requires a frozen scalar formula/coordinate before data access")
        primary=collapse_score(pi_values,response_values)
        alternatives={str(k):collapse_score(v,response_values) for k,v in dict(alternative_coordinates).items()}
        best_alt=min(alternatives.values()) if alternatives else None
        systems=sorted(set(str(x) for x in system_ids))
        core={
            "schema":"phi-scalar-law-utility/v1","owner":self.owner_id,
            "status":"SCALAR_LAW_COLLAPSE_UTILITY_MEASURED",
            "frozen_formula_digest":frozen_formula.get("digest"),
            "primary_collapse_score":primary,"collapse_threshold":float(collapse_threshold),
            "collapse_pass":primary<float(collapse_threshold),"alternative_collapse_scores":alternatives,
            "best_alternative_collapse_score":best_alt,
            "improvement_factor_vs_best_alternative":(best_alt/primary if best_alt is not None and primary>0 else None),
            "cross_system_count":len(systems),"system_ids":systems,
            "problem_utility":{
                "single_coordinate_replaces_separate_empirics":bool(primary<float(collapse_threshold) and len(systems)>1),
                "dimension_reduction_is_measured":True,
                "world_problem_solved_claimed":False,
            },
            "claim_boundary":{"collapse_is_world_law_proof":False,"ood_and_null_still_required":True},
        }
        return {**core,"digest":digest_payload(core)}
