"""Open-world elementary ParticleSpace census for Phi-LawSpace v7.3.

The owner enumerates bounded *research windows* of Lorentz x SM-gauge x copy
coordinates. Bounds are explicit and are never interpreted as a ceiling on the
full theory space. Every unoccupied intrinsically consistent cell remains a
candidate; anomaly cancellation is evaluated as a spectrum-completion
constraint, not as a single-cell prohibition.

Scientific promotion remains owned exclusively by ScientificPromotionCore.
"""
from __future__ import annotations

import dataclasses
import itertools
import math
import numpy as np
from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Iterable, Mapping, Sequence

from .schema import digest_payload

SCHEMA = "phi-particlespace-open-world/v7.3"
OWNER_ID = "PARTICLESPACE-OPEN-WORLD-CENSUS/7.3.0"
BLIND_DISCOVERY_SCHEMA = "phi-particlespace-blind-discovery/v7.5"
BLIND_DISCOVERY_ALGORITHM = "ROBUST_KNN_NOVELTY_PLUS_FARTHEST_POINT_DIVERSITY/1.0"
BLIND_DISCOVERY_NEIGHBOURS = 12
BLIND_DISCOVERY_SHORTLIST = 32

# Restored current-owner downstream closure.  The census coordinate contains
# Lorentz spin, but spin alone does not determine a Lagrangian realization.
# Closure therefore requires an explicit realization branch rather than
# silently inferring one from spin.
PARTICLE_CLOSURE_SCHEMA = "phi-particlespace-candidate-closure/v7.7"
PARTICLE_CLOSURE_SEQUENCE = ("A", "M", "U", "R", "D", "P", "E", "OMEGA")
FIELD_REALIZATIONS_BY_SPIN: dict[str, tuple[str, ...]] = {
    "0": ("REAL_SCALAR", "COMPLEX_SCALAR"),
    "1/2": ("CHIRAL_WEYL", "VECTORLIKE_DIRAC"),
    "1": ("GAUGE_VECTOR", "MASSIVE_VECTOR_MATTER"),
}
_GAUGE_UNITARITY_REFERENCE_COUPLINGS = {"SU3": 1.23, "SU2": 0.652, "U1": 0.357}
_GAUGE_UNITARITY_BOUND = 0.5



@dataclass(frozen=True)
class ParticleSpaceBounds:
    spins: tuple[str, ...] = ("0", "1/2", "1")
    su3_dynkin: tuple[tuple[int, int], ...] = ((0, 0), (1, 0), (0, 1), (2, 0), (0, 2), (1, 1))
    su2_dimensions: tuple[int, ...] = (1, 2, 3, 4, 5)
    hypercharge_n_min: int = -24
    hypercharge_n_max: int = 24
    hypercharge_denominator: int = 6
    copy_min: int = 1
    copy_max: int = 6

    def validate(self) -> None:
        if not self.spins or any(s not in {"0", "1/2", "1"} for s in self.spins):
            raise ValueError("supported spin research window is 0, 1/2, 1")
        if not self.su3_dynkin or any(p < 0 or q < 0 for p, q in self.su3_dynkin):
            raise ValueError("SU(3) Dynkin labels must be nonnegative")
        if not self.su2_dimensions or any(d < 1 for d in self.su2_dimensions):
            raise ValueError("SU(2) dimensions must be positive")
        if self.hypercharge_denominator <= 0 or self.hypercharge_n_min > self.hypercharge_n_max:
            raise ValueError("invalid hypercharge grid")
        if self.copy_min < 1 or self.copy_min > self.copy_max:
            raise ValueError("invalid copy window")

    @property
    def cell_count(self) -> int:
        return (
            len(self.spins) * len(self.su3_dynkin) * len(self.su2_dimensions)
            * (self.hypercharge_n_max - self.hypercharge_n_min + 1)
            * (self.copy_max - self.copy_min + 1)
        )


# (label, dimension, Dynkin index T(R), cubic anomaly A(R), conjugate Dynkin)
_SU3_SMALL: dict[tuple[int, int], tuple[str, int, Fraction, int, tuple[int, int]]] = {
    (0, 0): ("1", 1, Fraction(0), 0, (0, 0)),
    (1, 0): ("3", 3, Fraction(1, 2), 1, (0, 1)),
    (0, 1): ("3bar", 3, Fraction(1, 2), -1, (1, 0)),
    (2, 0): ("6", 6, Fraction(5, 2), 7, (0, 2)),
    (0, 2): ("6bar", 6, Fraction(5, 2), -7, (2, 0)),
    (1, 1): ("8", 8, Fraction(3), 0, (1, 1)),
}


def _su3_dimension(p: int, q: int) -> int:
    return (p + 1) * (q + 1) * (p + q + 2) // 2


def _su3_quadratic_casimir(p: int, q: int) -> Fraction:
    if p < 0 or q < 0:
        raise ValueError("SU(3) Dynkin labels must be nonnegative")
    return Fraction(p * p + q * q + p * q + 3 * p + 3 * q, 3)


def _su3_dynkin_index(p: int, q: int) -> Fraction:
    return Fraction(_su3_dimension(p, q), 8) * _su3_quadratic_casimir(p, q)


def _su3_cubic_anomaly(p: int, q: int) -> Fraction:
    """SU(3)^3 anomaly coefficient normalized to A(3)=+1."""
    dim = _su3_dimension(p, q)
    return Fraction((p - q) * (p + 2 * q + 3) * (2 * p + q + 3) * dim, 60)


def _su3_record(pq: tuple[int, int]) -> tuple[str, int, Fraction, Fraction, tuple[int, int]]:
    if pq in _SU3_SMALL:
        label, dim, t3, a3, conj = _SU3_SMALL[pq]
        return label, dim, t3, Fraction(a3), conj
    p, q = pq
    return (f"({p},{q})", _su3_dimension(p, q), _su3_dynkin_index(p, q), _su3_cubic_anomaly(p, q), (q, p))


def _su2_index(d: int) -> Fraction:
    # T(j)=j(j+1)(2j+1)/3 = d(d^2-1)/12 for d=2j+1.
    return Fraction(d * (d * d - 1), 12)


def _frac_text(x: Fraction) -> str:
    return str(x.numerator) if x.denominator == 1 else f"{x.numerator}/{x.denominator}"


def _charge_spectrum(d2: int, y: Fraction) -> list[str]:
    j = Fraction(d2 - 1, 2)
    return [_frac_text(-j + k + y) for k in range(d2)]


# Left-handed Weyl convention, Q = T3 + Y.
_SM_CHIRAL_ROWS: dict[str, tuple[tuple[int, int], int, Fraction]] = {
    "Q": ((1, 0), 2, Fraction(1, 6)),
    "u^c": ((0, 1), 1, Fraction(-2, 3)),
    "d^c": ((0, 1), 1, Fraction(1, 3)),
    "L": ((0, 0), 2, Fraction(-1, 2)),
    "e^c": ((0, 0), 1, Fraction(1)),
}

_OBSERVED_GAUGE_BASIS_BOSONS = {
    ("0", (0, 0), 2, Fraction(1, 2), 1): "H",
    ("1", (1, 1), 1, Fraction(0), 1): "G",
    ("1", (0, 0), 3, Fraction(0), 1): "W",
    ("1", (0, 0), 1, Fraction(0), 1): "B",
}

# Global-form refinement of the local SM Lie algebra.  A ParticleSpace cell is
# never deleted when a quotient is incompatible: all four branches remain in
# the receipt so the global gauge-group assumption stays explicit and testable.
SM_GAUGE_GLOBAL_FORMS: tuple[str, ...] = ("Z1", "Z2", "Z3", "Z6")
SM_GAUGE_GLOBAL_FORM_LABELS: dict[str, str] = {
    "Z1": "SU(3)c x SU(2)L x U(1)Y",
    "Z2": "(SU(3)c x SU(2)L x U(1)Y)/Z2",
    "Z3": "(SU(3)c x SU(2)L x U(1)Y)/Z3",
    "Z6": "(SU(3)c x SU(2)L x U(1)Y)/Z6",
}


def _su3_triality(pq: tuple[int, int]) -> int:
    # Center charge of SU(3): p+2q == p-q (mod 3).
    p, q = pq
    return (p - q) % 3


def _su2_center_parity(d2: int) -> int:
    # (-1)^(2j), with d2=2j+1.
    return (d2 - 1) % 2


def sm_gauge_global_form_profile(pq: tuple[int, int], d2: int, y: Fraction) -> dict[str, Any]:
    """Return conditional representation consistency for Z1/Z2/Z3/Z6.

    In the standard SM hypercharge normalization the common Z6-center residue is
        k6 = 6Y + 2 t3 + 3 s2 (mod 6).
    Z2 and Z3 quotients require the corresponding residue modulo 2 or 3.
    For the default census Y=n/6, k6 is an integer.  If a caller chooses a
    different hypercharge grid for which 6Y is nonintegral, the quotient branches
    are left UNRESOLVED rather than silently rejected.
    """
    t3 = _su3_triality(pq)
    s2 = _su2_center_parity(d2)
    raw = 6 * y + 2 * t3 + 3 * s2
    if raw.denominator != 1:
        branches = {
            "Z1": {"compatible": True, "status": "ALLOWED_REPRESENTATION"},
            "Z2": {"compatible": None, "status": "UNRESOLVED_NONINTEGER_6Y_NORMALIZATION"},
            "Z3": {"compatible": None, "status": "UNRESOLVED_NONINTEGER_6Y_NORMALIZATION"},
            "Z6": {"compatible": None, "status": "UNRESOLVED_NONINTEGER_6Y_NORMALIZATION"},
        }
        return {
            "axis_id": "sm_gauge_global_form",
            "axis_role": "DISCRETE_THEORY_ASSUMPTION",
            "su3_triality": t3,
            "su2_center_parity": s2,
            "six_hypercharge": _frac_text(6 * y),
            "residue_k6": None,
            "raw_center_charge": _frac_text(raw),
            "branches": branches,
            "formula": "k6=(6Y+2*t3+3*s2) mod 6",
        }
    residue = int(raw) % 6
    compatible = {
        "Z1": True,
        "Z2": residue % 2 == 0,
        "Z3": residue % 3 == 0,
        "Z6": residue == 0,
    }
    branches = {
        form: {
            "compatible": ok,
            "status": "ALLOWED_REPRESENTATION" if ok else "FORBIDDEN_REPRESENTATION_BY_GLOBAL_FORM",
            "group": SM_GAUGE_GLOBAL_FORM_LABELS[form],
        }
        for form, ok in compatible.items()
    }
    return {
        "axis_id": "sm_gauge_global_form",
        "axis_role": "DISCRETE_THEORY_ASSUMPTION",
        "su3_triality": t3,
        "su2_center_parity": s2,
        "six_hypercharge": int(6 * y),
        "residue_k6": residue,
        "raw_center_charge": int(raw),
        "branches": branches,
        "formula": "k6=(6Y+2*t3+3*s2) mod 6",
    }


def anomaly_vector(pq: tuple[int, int], d2: int, y: Fraction) -> dict[str, Fraction]:
    _, d3, t3, a3, _ = _su3_record(pq)
    t2 = _su2_index(d2)
    return {
        "SU3_CUBIC": Fraction(a3 * d2),
        "SU3_SQ_U1": t3 * d2 * y,
        "SU2_SQ_U1": t2 * d3 * y,
        "U1_CUBIC": d3 * d2 * y**3,
        "GRAV_SQ_U1": d3 * d2 * y,
    }


def _witten_bit(pq: tuple[int, int], d2: int) -> int:
    _, d3, _, _, _ = _su3_record(pq)
    two_t = int(2 * _su2_index(d2))
    return (d3 * (two_t % 2)) % 2


def _observed_name(spin: str, pq: tuple[int, int], d2: int, y: Fraction, copy: int) -> str | None:
    if spin == "1/2" and 1 <= copy <= 3:
        for name, (rpq, rd2, ry) in _SM_CHIRAL_ROWS.items():
            if (pq, d2, y) == (rpq, rd2, ry):
                return f"{name}_G{copy}"
    return _OBSERVED_GAUGE_BASIS_BOSONS.get((spin, pq, d2, y, copy))


def _same_as_sm_row(pq: tuple[int, int], d2: int, y: Fraction) -> str | None:
    for name, row in _SM_CHIRAL_ROWS.items():
        if row == (pq, d2, y):
            return name
    return None


def _color_pair_singlet(candidate: tuple[int, int], sm: tuple[int, int]) -> bool:
    return _su3_record(candidate)[4] == sm


def _su2_higgs_triple_singlet(candidate_d: int, sm_d: int) -> bool:
    jc = Fraction(candidate_d - 1, 2)
    js = Fraction(sm_d - 1, 2)
    # candidate must appear in sm x Higgs(1/2).
    return jc in {abs(js - Fraction(1, 2)), js + Fraction(1, 2)}


def _yukawa_partners(pq: tuple[int, int], d2: int, y: Fraction) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for sm_name, (spq, sd2, sy) in _SM_CHIRAL_ROWS.items():
        if not _color_pair_singlet(pq, spq):
            continue
        if not _su2_higgs_triple_singlet(d2, sd2):
            continue
        for h_name, hy in (("H", Fraction(1, 2)), ("Hdag", Fraction(-1, 2))):
            if y + sy + hy == 0:
                out.append({"sm_field": sm_name, "higgs": h_name})
    return out


def _sector_tags(spin: str, pq: tuple[int, int], d2: int, y: Fraction, copy: int) -> list[str]:
    tags: list[str] = []
    sm_row = _same_as_sm_row(pq, d2, y)
    if spin == "1/2" and sm_row and copy >= 4:
        tags += ["CHIRAL_FAMILY_COPY", f"COPY_OF_{sm_row}"]
    if spin == "1/2" and pq == (0, 0) and d2 == 1 and y == 0:
        tags += ["GAUGE_SINGLET_NEUTRAL_FERMION", "HNL_STERILE_NEUTRAL_SECTOR"]
    if spin == "1/2":
        tags.append("FERMION_MULTIPLET")
        if pq in {(2, 0), (0, 2), (1, 1)}:
            tags.append("EXOTIC_COLOR_FERMION")
    elif spin == "0":
        tags.append("SCALAR_MULTIPLET")
        if d2 > 1 or y != 0 or pq != (0, 0):
            tags.append("ADDITIONAL_SCALAR_SECTOR")
    elif spin == "1":
        tags.append("VECTOR_MULTIPLET")
        if pq == (0, 0) and d2 == 1 and y == 0 and copy >= 2:
            tags.append("ADDITIONAL_NEUTRAL_VECTOR")
        if any(Fraction(q) != 0 for q in _charge_spectrum(d2, y)):
            tags.append("CHARGED_VECTOR_SECTOR")
    if pq in {(2, 0), (0, 2), (1, 1)}:
        tags.append("EXOTIC_COLOR_REPRESENTATION")
    return sorted(set(tags))


def _parameter_manifold(spin: str, pq: tuple[int, int], d2: int, y: Fraction) -> dict[str, Any]:
    base: dict[str, Any] = {
        "mass_GeV": {"domain": "[0,+inf)", "quantitative_open_region": "NOT_COMPUTED_WITHOUT_EXPERIMENT_LIKELIHOOD"},
        "couplings": {"domain": "MODEL_DEPENDENT", "quantitative_open_region": "NOT_COMPUTED"},
        "width_or_lifetime": {"domain": "MODEL_DEPENDENT", "quantitative_open_region": "NOT_COMPUTED"},
    }
    if spin == "1/2":
        base["mass_character"] = {"domain": ["DIRAC_COMPLETION", "MAJORANA_IF_GAUGE_ALLOWED"]}
        if pq == (0, 0) and d2 == 1 and y == 0:
            base["active_flavor_mixing"] = {"coordinates": ["|UeN|^2", "|UmuN|^2", "|UtauN|^2"]}
    return base


class ParticleSpaceOwner:
    owner_id = OWNER_ID

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "coordinate_system": ["spin", "SU3_Dynkin", "SU2_dimension", "hypercharge", "copy", "sm_gauge_global_form"],
            "cell_statuses": ["OBSERVED", "CANDIDATE", "CONSTRAINED", "EXCLUDED_REGION", "FORBIDDEN"],
            "hard_rules": {
                "empty_cell_is_particle_claim": False,
                "consistent_empty_cell_is_candidate": True,
                "single_chiral_cell_nonzero_anomaly_means_forbidden": False,
                "anomaly_is_spectrum_completion_constraint": True,
                "finite_bounds_are_research_window_not_space_ceiling": True,
                "experimental_exclusion_removes_only_parameter_region": True,
                "literature_or_experiment_feedback_before_internal_freeze": False,
                "scientific_promotion_owner": "SCIENTIFIC-PROMOTION-CORE/9.1.0",
                "global_form_branch_is_explicit_not_hidden": True,
                "incompatible_global_form_branch_is_retained_not_deleted": True,
                "blind_discovery_selection_must_ignore_semantic_and_literature_labels": True,
                "downstream_closure_sequence": list(PARTICLE_CLOSURE_SEQUENCE),
                "closure_requires_explicit_field_realization": True,
                "spin_alone_does_not_determine_lagrangian_realization": True,
                "legacy_hypercharge_adapter_is_explicit_Ylegacy_equals_2Ystandard": True,
                "experimental_decay_topology_requires_nonempty_declared_bridge": True,
                "selection_shell_bias_must_be_preserved_in_provenance": True,
                "massive_vector_uv_branches_are_explicit_and_branch_failures_do_not_delete_parent_candidate": True,
                "minimal_block_simple_group_completion_requires_common_gauge_coupling_matching": True,
                "legacy_P001_P007_dossiers_are_calibration_not_blind_selection": True,
            },
            "sm_gauge_global_form_axis": {
                "axis_id": "sm_gauge_global_form",
                "values": list(SM_GAUGE_GLOBAL_FORMS),
                "labels": dict(SM_GAUGE_GLOBAL_FORM_LABELS),
                "formula": "k6=(6Y+2*t3+3*s2) mod 6",
                "compatibility": {"Z1": "always", "Z2": "k6 mod 2 = 0", "Z3": "k6 mod 3 = 0", "Z6": "k6 = 0"},
                "provenance": "INTERNAL_FIRST_P22648_GAP_DISCOVERY_THEN_POSTFREEZE_PRIOR_ART_CONFIRMED_KNOWN_PHYSICS",
                "world_novelty_claim": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    def close_coordinate(
        self, *, spin: str, su3_dynkin: Sequence[int], su2_dimension: int,
        hypercharge: Any, copy: int = 1, field_realization: str,
        selected_global_form: str | None = None,
        selection_provenance: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        """Run the authoritative A->M->U->R->D->P->E->Omega closure.

        Hypercharge is the current standard convention Q=T3+Y.  A legacy
        coordinate must be converted explicitly with legacy_hypercharge_to_standard().
        """
        return _close_particle_coordinate_impl(
            spin=spin, su3_dynkin=su3_dynkin, su2_dimension=su2_dimension,
            hypercharge=hypercharge, copy=copy, field_realization=field_realization,
            selected_global_form=selected_global_form, selection_provenance=selection_provenance,
        )

    def close_cell(
        self, cell: Mapping[str, Any], *, field_realization: str,
        selected_global_form: str | None = None,
        selection_provenance: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        coord = cell.get("coordinate", cell)
        return self.close_coordinate(
            spin=str(coord["spin"]), su3_dynkin=coord["su3_dynkin"],
            su2_dimension=int(coord["su2_dimension"]), hypercharge=coord["hypercharge"],
            copy=int(coord.get("copy", 1)), field_realization=field_realization,
            selected_global_form=selected_global_form, selection_provenance=selection_provenance,
        )

    def enumerate_cells(
        self,
        bounds: ParticleSpaceBounds | None = None,
        *,
        experimental_class_map: Mapping[str, Mapping[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        bounds = bounds or ParticleSpaceBounds()
        bounds.validate()
        rows: list[dict[str, Any]] = []
        expmap = experimental_class_map or {}
        counter = 0
        for spin, pq, d2, n, copy in itertools.product(
            bounds.spins,
            bounds.su3_dynkin,
            bounds.su2_dimensions,
            range(bounds.hypercharge_n_min, bounds.hypercharge_n_max + 1),
            range(bounds.copy_min, bounds.copy_max + 1),
        ):
            counter += 1
            y = Fraction(n, bounds.hypercharge_denominator)
            label3, d3, _, _, conj = _su3_record(pq)
            obs = _observed_name(spin, pq, d2, y, copy)
            avec = anomaly_vector(pq, d2, y) if spin == "1/2" else {k: Fraction(0) for k in ("SU3_CUBIC", "SU3_SQ_U1", "SU2_SQ_U1", "U1_CUBIC", "GRAV_SQ_U1")}
            witten = _witten_bit(pq, d2) if spin == "1/2" else 0
            anomaly_zero = all(v == 0 for v in avec.values()) and witten == 0
            tags = _sector_tags(spin, pq, d2, y, copy)
            global_form = sm_gauge_global_form_profile(pq, d2, y)
            search_class = next((tag for tag in tags if tag in expmap), None)
            exp_record = expmap.get(search_class, {}) if search_class else {}
            status = "OBSERVED" if obs else str(exp_record.get("cell_status", "CANDIDATE"))
            if status not in {"OBSERVED", "CANDIDATE", "CONSTRAINED", "EXCLUDED_REGION", "FORBIDDEN"}:
                raise ValueError(f"invalid experimental cell status {status}")
            theory_status = "PASS_INTRINSIC_CELL_CONSISTENCY"
            anomaly_status = "NOT_APPLICABLE_BOSON" if spin != "1/2" else ("SELF_ANOMALY_NEUTRAL" if anomaly_zero else "REQUIRES_ANOMALY_COMPLETION")
            if spin == "1" and not (y == 0 and ((pq == (1, 1) and d2 == 1) or (pq == (0, 0) and d2 in {1, 3}))):
                theory_status = "PASS_EFFECTIVE_VECTOR_CELL_REQUIRES_UV_DYNAMICAL_ORIGIN"
            row = {
                "particle_id": f"P-{counter:05d}",
                "coordinate": {
                    "spin": spin,
                    "su3_dynkin": list(pq),
                    "su3_label": label3,
                    "su3_dimension": d3,
                    "su3_conjugate_dynkin": list(conj),
                    "su2_dimension": d2,
                    "hypercharge": _frac_text(y),
                    "hypercharge_numerator": n,
                    "hypercharge_denominator": bounds.hypercharge_denominator,
                    "copy": copy,
                    "electric_charge_spectrum": _charge_spectrum(d2, y),
                },
                "global_form_axis": {
                    **global_form,
                    "branches": {
                        form: {
                            **branch,
                            "conditional_cell_status": (
                                status if branch.get("compatible") is True
                                else ("FORBIDDEN" if branch.get("compatible") is False else "UNRESOLVED")
                            ),
                        }
                        for form, branch in global_form["branches"].items()
                    },
                },
                "status": status,
                "observed_name": obs,
                "theory_admissibility": theory_status,
                "anomaly_gate": {
                    "status": anomaly_status,
                    "local_contribution": {k: _frac_text(v) for k, v in avec.items()},
                    "witten_mod2": witten,
                    "rule": "nonzero single-cell anomaly requests a completion spectrum; it does not forbid the cell",
                },
                "yukawa_gate": {
                    "renormalizable_sm_higgs_partners": _yukawa_partners(pq, d2, y) if spin == "1/2" else [],
                },
                "vectorlike_completion": {
                    "conjugate_cell_coordinate": {
                        "su3_dynkin": list(conj), "su2_dimension": d2, "hypercharge": _frac_text(-y)
                    },
                    "exists_inside_symmetric_research_window": (conj in bounds.su3_dynkin and -bounds.hypercharge_n_max <= -n <= -bounds.hypercharge_n_min),
                } if spin == "1/2" else None,
                "sector_tags": tags,
                "parameter_manifold": _parameter_manifold(spin, pq, d2, y),
                "experimental_gate": exp_record if search_class else {"status": "NOT_MATERIALIZED", "quantitative_excluded_region": None},
                "promotion_allowed": False,
                "epistemic_status": "OBSERVED_SOURCE_ANCHOR" if obs else "STRUCTURALLY_ADMISSIBLE_OPEN_WORLD_CANDIDATE",
            }
            row["cell_digest"] = digest_payload(row)
            rows.append(row)
        if counter != bounds.cell_count:
            raise RuntimeError("ParticleSpace census cardinality mismatch")
        return rows

    @staticmethod
    def _spectrum_anomaly(rows: Sequence[tuple[tuple[int, int], int, Fraction, int]]) -> dict[str, Fraction]:
        total = {k: Fraction(0) for k in ("SU3_CUBIC", "SU3_SQ_U1", "SU2_SQ_U1", "U1_CUBIC", "GRAV_SQ_U1")}
        for pq, d2, y, multiplicity in rows:
            a = anomaly_vector(pq, d2, y)
            for k in total:
                total[k] += multiplicity * a[k]
        return total

    @staticmethod
    def _anomaly_distance(residual: Mapping[str, Fraction], scale: Mapping[str, Fraction]) -> float:
        value = 0.0
        for key, r in residual.items():
            s = max(abs(float(scale.get(key, Fraction(0)))), 1.0)
            value += (float(r) / s) ** 2
        return math.sqrt(value)

    def whole_representation_blind_benchmark(self, bounds: ParticleSpaceBounds | None = None) -> Mapping[str, Any]:
        """Hide one complete SM chiral representation across all 3 copies.

        Candidate ranking sees the remaining four rows, the gauge coordinate
        window and anomaly equations. It does not see the hidden row label or
        coordinate. Multiplicity 1..6 is itself searched.
        """
        bounds = bounds or ParticleSpaceBounds(spins=("1/2",))
        bounds.validate()
        all_true = [(pq, d2, y, 3) for pq, d2, y in _SM_CHIRAL_ROWS.values()]
        tasks: list[dict[str, Any]] = []
        candidate_base = []
        for pq, d2, n in itertools.product(bounds.su3_dynkin, bounds.su2_dimensions, range(bounds.hypercharge_n_min, bounds.hypercharge_n_max + 1)):
            candidate_base.append((pq, d2, Fraction(n, bounds.hypercharge_denominator)))
        for hidden_name, hidden_row in _SM_CHIRAL_ROWS.items():
            remaining = [(pq, d2, y, mult) for (name, (pq, d2, y)), mult in zip(_SM_CHIRAL_ROWS.items(), [3] * len(_SM_CHIRAL_ROWS)) if name != hidden_name]
            rem_anom = self._spectrum_anomaly(remaining)
            target_scale = {k: abs(v) for k, v in self._spectrum_anomaly(all_true).items()}
            # total truth is zero, so scale by hidden contribution instead.
            hidden_contrib = {k: 3 * v for k, v in anomaly_vector(*hidden_row).items()}
            target_scale = {k: abs(v) for k, v in hidden_contrib.items()}
            ranked: list[tuple[float, tuple[tuple[int, int], int, Fraction, int], dict[str, Fraction]]] = []
            for pq, d2, y in candidate_base:
                for mult in range(bounds.copy_min, bounds.copy_max + 1):
                    a = anomaly_vector(pq, d2, y)
                    residual = {k: rem_anom[k] + mult * a[k] for k in rem_anom}
                    dist = self._anomaly_distance(residual, target_scale)
                    # Tie-breakers are structural only: exact anomaly closure,
                    # then more renormalizable Higgs links, then lower reps.
                    yuk = len(_yukawa_partners(pq, d2, y))
                    complexity = _su3_record(pq)[1] * d2 + abs(float(y)) + 0.01 * mult
                    score = dist + 1e-6 * complexity - 1e-8 * yuk
                    ranked.append((score, (pq, d2, y, mult), residual))
            ranked.sort(key=lambda x: x[0])
            truth = (*hidden_row, 3)
            rank = next(i + 1 for i, (_, row, _) in enumerate(ranked) if row == truth)
            best = ranked[0]
            tasks.append({
                "hidden_representation": hidden_name,
                "truth_coordinate_revealed_postfreeze": {"su3_dynkin": list(hidden_row[0]), "su2_dimension": hidden_row[1], "hypercharge": _frac_text(hidden_row[2]), "multiplicity": 3},
                "truth_rank": rank,
                "top_candidate": {"su3_dynkin": list(best[1][0]), "su2_dimension": best[1][1], "hypercharge": _frac_text(best[1][2]), "multiplicity": best[1][3]},
                "top_candidate_anomaly_residual": {k: _frac_text(v) for k, v in best[2].items()},
                "candidate_row_multiplicity_space": len(candidate_base) * (bounds.copy_max - bounds.copy_min + 1),
                "hidden_name_used_during_ranking": False,
                "hidden_coordinate_used_during_ranking": False,
            })
        pass_all = all(t["truth_rank"] == 1 for t in tasks)
        payload = {
            "schema": "phi-particlespace-whole-representation-blind/v7.3",
            "owner_id": OWNER_ID,
            "status": "PASS_WHOLE_REPRESENTATION_RECOVERY" if pass_all else "FAIL_WHOLE_REPRESENTATION_RECOVERY",
            "tasks": tasks,
            "top1_recovery": sum(t["truth_rank"] == 1 for t in tasks) / len(tasks),
            "max_truth_rank": max(t["truth_rank"] for t in tasks),
            "mechanism": "ANOMALY_CLOSURE_PLUS_STRUCTURAL_TIEBREAKERS_NOT_COPY_PATTERN",
            "claim_boundary": {
                "qualifies_new_representation_discovery": False,
                "reason": "benchmark establishes deductive recovery of withheld SM rows inside a declared finite gauge window; open-world new-row discovery still requires independent data/constraints and ScientificPromotionCore",
            },
        }
        return {**payload, "digest": digest_payload(payload)}

    @staticmethod
    def _blind_physical_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
        c = row["coordinate"]
        return (
            str(c["spin"]),
            tuple(int(v) for v in c["su3_dynkin"]),
            int(c["su2_dimension"]),
            int(c["hypercharge_numerator"]),
            int(c["hypercharge_denominator"]),
        )

    @staticmethod
    def _blind_coordinate_payload(row: Mapping[str, Any]) -> dict[str, Any]:
        c = row["coordinate"]
        return {
            "spin": str(c["spin"]),
            "su3_dynkin": [int(v) for v in c["su3_dynkin"]],
            "su3_dimension": int(c["su3_dimension"]),
            "su2_dimension": int(c["su2_dimension"]),
            "hypercharge_numerator": int(c["hypercharge_numerator"]),
            "hypercharge_denominator": int(c["hypercharge_denominator"]),
            "electric_charge_spectrum": list(c["electric_charge_spectrum"]),
        }

    @staticmethod
    def _blind_anomaly_signature(row: Mapping[str, Any]) -> tuple[Fraction, ...]:
        gate = row["anomaly_gate"]
        keys = ("SU3_CUBIC", "SU3_SQ_U1", "SU2_SQ_U1", "U1_CUBIC", "GRAV_SQ_U1")
        return tuple(Fraction(str(gate["local_contribution"][key])) for key in keys) + (Fraction(int(gate["witten_mod2"])),)

    def blind_discovery_contract(
        self,
        *,
        neighbour_count: int = BLIND_DISCOVERY_NEIGHBOURS,
        shortlist_count: int = BLIND_DISCOVERY_SHORTLIST,
    ) -> Mapping[str, Any]:
        if neighbour_count < 1 or shortlist_count < 1:
            raise ValueError("blind discovery requires positive neighbour and shortlist counts")
        payload = {
            "schema": BLIND_DISCOVERY_SCHEMA,
            "owner_id": self.owner_id,
            "algorithm": BLIND_DISCOVERY_ALGORITHM,
            "selection_role": "BLIND_RESEARCH_PRIORITY_NOT_TRUTH_OR_NOVELTY_CLAIM",
            "candidate_unit": "ONE_CANONICAL_UNOBSERVED_COPY_PER_UNIQUE_LORENTZ_GAUGE_COORDINATE",
            "canonicalization": "group by (spin,SU3_Dynkin,SU2_dimension,hypercharge); choose lowest-copy CANDIDATE row; copy is retained only for addressability and is excluded from the descriptor",
            "neighbour_count": int(neighbour_count),
            "shortlist_count": int(shortlist_count),
            "random_seed": None,
            "stochastic_steps": False,
            "descriptor": [
                "2*spin",
                "SU3_Dynkin_p",
                "SU3_Dynkin_q",
                "log1p(SU3_dimension)",
                "SU2_dimension",
                "signed_hypercharge_numerator",
                "absolute_hypercharge_numerator",
                "min_electric_charge",
                "max_electric_charge",
                "electric_charge_span",
                "electric_charge_rms",
                "log1p(L1_local_anomaly)",
                "log1p(L2_local_anomaly)",
                "Witten_mod2",
                "compatible_global_form_branch_count",
                "self_anomaly_neutral_bit",
                "exact_pair_anomaly_closure_exists_bit",
            ],
            "normalization": "per-descriptor median/MAD; 1.4826*MAD, fallback std, fallback 1",
            "novelty": "mean Euclidean distance to k nearest neighbours in robust-normalized descriptor space",
            "diversity": "deterministic farthest-point traversal seeded by top novelty; maximize minimum distance to selected set",
            "tie_breaker": "content-derived blind_id ascending after 12-decimal score quantization",
            "forbidden_ranking_inputs": [
                "observed_name",
                "su3_label",
                "sector_tags",
                "parameter_manifold",
                "yukawa_gate",
                "experimental_gate",
                "particle_candidate_dossier titles or builders",
                "prior-art/literature records",
                "experiment/search names or benchmark limits",
                "post-freeze novelty labels",
            ],
            "allowed_occupancy_input": "OBSERVED/CANDIDATE status only to choose an unoccupied canonical copy",
            "promotion_allowed": False,
            "scientific_promotion_owner": "SCIENTIFIC-PROMOTION-CORE/9.1.0",
            "finite_census_is_space_ceiling": False,
        }
        return {**payload, "contract_digest": digest_payload(payload)}

    def _blind_candidate_universe(
        self,
        bounds: ParticleSpaceBounds,
        *,
        cells: Sequence[Mapping[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        source_rows = list(cells) if cells is not None else self.enumerate_cells(bounds)
        groups: dict[tuple[Any, ...], list[Mapping[str, Any]]] = {}
        for row in source_rows:
            groups.setdefault(self._blind_physical_key(row), []).append(row)
        canonical_rows: list[Mapping[str, Any]] = []
        for key in sorted(groups, key=lambda x: (x[0], x[1], x[2], x[3], x[4])):
            candidates = [r for r in groups[key] if r.get("status") != "OBSERVED"]
            if not candidates:
                continue
            canonical_rows.append(min(candidates, key=lambda r: (int(r["coordinate"]["copy"]), str(r["particle_id"]))))

        # Build exact anomaly-complement lookup using only algebraic contributions.
        fermion_signatures: dict[tuple[Fraction, ...], list[str]] = {}
        coordinate_digest_by_particle: dict[str, str] = {}
        for row in canonical_rows:
            coord_payload = self._blind_coordinate_payload(row)
            cdig = digest_payload(coord_payload)
            coordinate_digest_by_particle[str(row["particle_id"])] = cdig
            if str(row["coordinate"]["spin"]) == "1/2":
                fermion_signatures.setdefault(self._blind_anomaly_signature(row), []).append(cdig)
        for vals in fermion_signatures.values():
            vals.sort()

        out: list[dict[str, Any]] = []
        for row in canonical_rows:
            coord = self._blind_coordinate_payload(row)
            coordinate_digest = digest_payload(coord)
            spin = str(coord["spin"])
            anomaly_sig = self._blind_anomaly_signature(row)
            anomaly_values = anomaly_sig[:-1]
            witten = int(anomaly_sig[-1])
            self_neutral = spin == "1/2" and all(v == 0 for v in anomaly_values) and witten == 0
            pair_closure = False
            pair_partner_digest = None
            if spin == "1/2" and not self_neutral:
                target = tuple(-v for v in anomaly_values) + (Fraction(witten),)
                partners = [d for d in fermion_signatures.get(target, ()) if d != coordinate_digest]
                if partners:
                    pair_closure = True
                    pair_partner_digest = partners[0]
            global_form = row["global_form_axis"]["branches"]
            compatible_count = sum(1 for branch in global_form.values() if branch.get("compatible") is True)
            closure_class = (
                "BOSON_ANOMALY_NOT_APPLICABLE" if spin != "1/2"
                else "SELF_ANOMALY_NEUTRAL" if self_neutral
                else "EXACT_TWO_CELL_ANOMALY_COMPLETION_AVAILABLE" if pair_closure
                else "MULTICELL_COMPLETION_REQUIRED"
            )
            blind_id = "PB-" + coordinate_digest[:20].upper()
            out.append({
                "blind_id": blind_id,
                "coordinate_digest": coordinate_digest,
                "canonical_particle_id": str(row["particle_id"]),
                "canonical_unobserved_copy": int(row["coordinate"]["copy"]),
                "coordinate": coord,
                "structural": {
                    "local_anomaly": {
                        "SU3_CUBIC": str(anomaly_values[0]),
                        "SU3_SQ_U1": str(anomaly_values[1]),
                        "SU2_SQ_U1": str(anomaly_values[2]),
                        "U1_CUBIC": str(anomaly_values[3]),
                        "GRAV_SQ_U1": str(anomaly_values[4]),
                        "WITTEN_MOD2": witten,
                    },
                    "closure_class": closure_class,
                    "self_anomaly_neutral": bool(self_neutral),
                    "exact_pair_anomaly_closure_exists": bool(pair_closure),
                    "pair_partner_coordinate_digest": pair_partner_digest,
                    "compatible_global_form_branch_count": compatible_count,
                    "global_form_compatibility": {
                        form: branch.get("compatible") for form, branch in sorted(global_form.items())
                    },
                },
            })
        out.sort(key=lambda r: r["blind_id"])
        return out

    @staticmethod
    def _blind_descriptor(row: Mapping[str, Any]) -> list[float]:
        coord = row["coordinate"]
        spin_twice = {"0": 0.0, "1/2": 1.0, "1": 2.0}[str(coord["spin"])]
        p, q = (int(v) for v in coord["su3_dynkin"])
        d3 = int(coord["su3_dimension"])
        d2 = int(coord["su2_dimension"])
        n = int(coord["hypercharge_numerator"])
        den = int(coord["hypercharge_denominator"])
        charges = [float(Fraction(str(v))) for v in coord["electric_charge_spectrum"]]
        qmin, qmax = min(charges), max(charges)
        qrms = math.sqrt(sum(v * v for v in charges) / max(1, len(charges)))
        anomaly = row["structural"]["local_anomaly"]
        avec = [float(Fraction(str(anomaly[k]))) for k in ("SU3_CUBIC", "SU3_SQ_U1", "SU2_SQ_U1", "U1_CUBIC", "GRAV_SQ_U1")]
        l1 = sum(abs(v) for v in avec)
        l2 = math.sqrt(sum(v * v for v in avec))
        return [
            spin_twice,
            float(p),
            float(q),
            math.log1p(float(d3)),
            float(d2),
            float(Fraction(n, den)),
            abs(float(Fraction(n, den))),
            qmin,
            qmax,
            qmax - qmin,
            qrms,
            math.log1p(l1),
            math.log1p(l2),
            float(int(anomaly["WITTEN_MOD2"])),
            float(row["structural"]["compatible_global_form_branch_count"]),
            1.0 if row["structural"]["self_anomaly_neutral"] else 0.0,
            1.0 if row["structural"]["exact_pair_anomaly_closure_exists"] else 0.0,
        ]

    @staticmethod
    def _robust_normalize_descriptor(x: np.ndarray) -> np.ndarray:
        median = np.median(x, axis=0)
        mad = np.median(np.abs(x - median), axis=0)
        scale = np.where(mad > 1.0e-12, 1.4826 * mad, np.std(x, axis=0))
        scale = np.where(scale > 1.0e-12, scale, 1.0)
        return (x - median) / scale

    def blind_discovery_freeze(
        self,
        bounds: ParticleSpaceBounds | None = None,
        *,
        neighbour_count: int = BLIND_DISCOVERY_NEIGHBOURS,
        shortlist_count: int = BLIND_DISCOVERY_SHORTLIST,
        cells: Sequence[Mapping[str, Any]] | None = None,
    ) -> Mapping[str, Any]:
        bounds = bounds or ParticleSpaceBounds()
        bounds.validate()
        contract = self.blind_discovery_contract(neighbour_count=neighbour_count, shortlist_count=shortlist_count)
        universe = self._blind_candidate_universe(bounds, cells=cells)
        if len(universe) <= neighbour_count:
            raise ValueError("blind universe is too small for requested kNN novelty")
        k = min(int(neighbour_count), len(universe) - 1)
        m = min(int(shortlist_count), len(universe))
        x = np.asarray([self._blind_descriptor(row) for row in universe], dtype=float)
        z = self._robust_normalize_descriptor(x)
        norms = np.sum(z * z, axis=1)
        dist2 = norms[:, None] + norms[None, :] - 2.0 * (z @ z.T)
        dist2 = np.maximum(dist2, 0.0)
        np.fill_diagonal(dist2, np.inf)
        nearest2 = np.partition(dist2, kth=k - 1, axis=1)[:, :k]
        novelty = np.mean(np.sqrt(nearest2), axis=1)
        novelty_q = np.round(novelty, 12)
        by_index = {i: universe[i] for i in range(len(universe))}
        ranking_indices = sorted(range(len(universe)), key=lambda i: (-float(novelty_q[i]), str(by_index[i]["blind_id"])))
        rank_of = {idx: rank + 1 for rank, idx in enumerate(ranking_indices)}

        selected: list[int] = [ranking_indices[0]]
        selection_distance: dict[int, float] = {selected[0]: float("inf")}
        min_distance = np.sqrt(dist2[:, selected[0]])
        min_distance[selected[0]] = -np.inf
        while len(selected) < m:
            remaining = [i for i in range(len(universe)) if i not in set(selected)]
            chosen = min(
                remaining,
                key=lambda i: (
                    -round(float(min_distance[i]), 12),
                    -float(novelty_q[i]),
                    str(by_index[i]["blind_id"]),
                ),
            )
            selection_distance[chosen] = round(float(min_distance[chosen]), 12)
            selected.append(chosen)
            min_distance = np.minimum(min_distance, np.sqrt(dist2[:, chosen]))
            for idx in selected:
                min_distance[idx] = -np.inf

        compact_ranking = [
            {
                "rank": rank_of[i],
                "blind_id": str(universe[i]["blind_id"]),
                "coordinate_digest": str(universe[i]["coordinate_digest"]),
                "novelty_score": float(novelty_q[i]),
            }
            for i in ranking_indices
        ]
        selected_rows: list[dict[str, Any]] = []
        for order, i in enumerate(selected, start=1):
            row = universe[i]
            selected_rows.append({
                "selection_order": order,
                "novelty_rank": rank_of[i],
                "blind_id": row["blind_id"],
                "coordinate_digest": row["coordinate_digest"],
                "canonical_particle_id": row["canonical_particle_id"],
                "canonical_unobserved_copy": row["canonical_unobserved_copy"],
                "novelty_score": float(novelty_q[i]),
                "minimum_distance_at_selection": None if order == 1 else float(selection_distance[i]),
                "coordinate": row["coordinate"],
                "structural": row["structural"],
            })

        precommit = {
            "contract_digest": contract["contract_digest"],
            "algorithm": contract["algorithm"],
            "neighbour_count": k,
            "shortlist_count": m,
            "random_seed": None,
            "stochastic_steps": False,
            "forbidden_ranking_inputs": contract["forbidden_ranking_inputs"],
            "canonicalization": contract["canonicalization"],
            "normalization": contract["normalization"],
            "novelty": contract["novelty"],
            "diversity": contract["diversity"],
            "tie_breaker": contract["tie_breaker"],
        }
        payload = {
            "schema": BLIND_DISCOVERY_SCHEMA,
            "owner_id": self.owner_id,
            "status": "BLIND_SELECTION_FROZEN_PRIOR_ART_NOT_ACCESSED",
            "claim_boundary": "BLIND_RESEARCH_PRIORITY_ONLY_NOT_PARTICLE_DISCOVERY_NOT_WORLD_NOVELTY",
            "bounds": dataclasses.asdict(bounds),
            "finite_census_is_space_ceiling": False,
            "candidate_universe_count": len(universe),
            "precommit": {**precommit, "precommit_digest": digest_payload(precommit)},
            "ranking_input_fields": list(contract["descriptor"]),
            "forbidden_inputs_absent_from_ranking_records": True,
            "full_ranking": compact_ranking,
            "full_ranking_digest": digest_payload(compact_ranking),
            "selected_shortlist": selected_rows,
            "selected_shortlist_digest": digest_payload(selected_rows),
            "literature_accessed_during_ranking": False,
            "experimental_class_map_used_during_ranking": False,
            "legacy_dossier_builder_used_during_ranking": False,
            "sector_tags_used_during_ranking": False,
            "observed_names_used_during_ranking": False,
            "promotion_allowed": False,
            "scientific_promotion_owner": "SCIENTIFIC-PROMOTION-CORE/9.1.0",
        }
        return {**payload, "selection_freeze_digest": digest_payload(payload)}

    def census_summary(self, bounds: ParticleSpaceBounds | None = None, *, experimental_class_map: Mapping[str, Mapping[str, Any]] | None = None) -> Mapping[str, Any]:
        bounds = bounds or ParticleSpaceBounds()
        cells = self.enumerate_cells(bounds, experimental_class_map=experimental_class_map)
        counts: dict[str, int] = {}
        anomaly_counts: dict[str, int] = {}
        tag_counts: dict[str, int] = {}
        global_form_compatible = {form: 0 for form in SM_GAUGE_GLOBAL_FORMS}
        global_form_incompatible = {form: 0 for form in SM_GAUGE_GLOBAL_FORMS}
        global_form_unresolved = {form: 0 for form in SM_GAUGE_GLOBAL_FORMS}
        k6_counts: dict[str, int] = {}
        observed_incompatible = {form: 0 for form in SM_GAUGE_GLOBAL_FORMS}
        for row in cells:
            counts[row["status"]] = counts.get(row["status"], 0) + 1
            a = row["anomaly_gate"]["status"]
            anomaly_counts[a] = anomaly_counts.get(a, 0) + 1
            for tag in row["sector_tags"]:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
            gf = row["global_form_axis"]
            rk = gf.get("residue_k6")
            k6_counts[str(rk)] = k6_counts.get(str(rk), 0) + 1
            for form, branch in gf["branches"].items():
                if branch.get("compatible") is True:
                    global_form_compatible[form] += 1
                elif branch.get("compatible") is False:
                    global_form_incompatible[form] += 1
                    if row["status"] == "OBSERVED":
                        observed_incompatible[form] += 1
                else:
                    global_form_unresolved[form] += 1
        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "bounds": dataclasses.asdict(bounds),
            "finite_window_is_space_ceiling": False,
            "cell_count": len(cells),
            "status_counts": counts,
            "anomaly_status_counts": anomaly_counts,
            "sector_tag_counts": dict(sorted(tag_counts.items())),
            "observed_count": counts.get("OBSERVED", 0),
            "unobserved_candidate_or_constrained_count": counts.get("CANDIDATE", 0) + counts.get("CONSTRAINED", 0),
            "global_form_axis": {
                "axis_id": "sm_gauge_global_form",
                "branch_instance_count": len(cells) * len(SM_GAUGE_GLOBAL_FORMS),
                "compatible_cell_counts": global_form_compatible,
                "incompatible_cell_counts": global_form_incompatible,
                "unresolved_cell_counts": global_form_unresolved,
                "k6_residue_counts": dict(sorted(k6_counts.items())),
                "observed_incompatible_counts": observed_incompatible,
                "alternative_branches_retained": True,
            },
            "promotion_allowed_by_census": False,
        }
        return {**payload, "digest": digest_payload(payload)}


def _fraction(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value, 1)
    if isinstance(value, float):
        return Fraction(str(value))
    if isinstance(value, str):
        return Fraction(value)
    raise TypeError(f"unsupported rational value {value!r}")


def legacy_hypercharge_to_standard(value: Any) -> Fraction:
    """Convert legacy ParticleSpace Q=T3+Y_legacy/2 to current Q=T3+Y."""
    return _fraction(value) / 2


def standard_hypercharge_to_legacy(value: Any) -> Fraction:
    return 2 * _fraction(value)


def _is_real_scalar_representation(pq: tuple[int, int], d2: int, y: Fraction) -> bool:
    return pq[0] == pq[1] and y == 0 and int(d2) % 2 == 1


def _realization_compatibility(spin: str, realization: str, pq: tuple[int, int], d2: int, y: Fraction) -> dict[str, Any]:
    allowed = FIELD_REALIZATIONS_BY_SPIN.get(spin, ())
    if realization not in allowed:
        return {
            "status": "REJECT_FIELD_REALIZATION_SPIN_MISMATCH",
            "compatible": False,
            "allowed_realizations_for_spin": list(allowed),
        }
    if realization == "REAL_SCALAR" and not _is_real_scalar_representation(pq, d2, y):
        return {
            "status": "REJECT_REAL_SCALAR_REPRESENTATION_NOT_GENUINELY_REAL",
            "compatible": False,
            "rule": "REAL_SCALAR requires p=q, Y=0 and odd SU(2) dimension",
        }
    return {"status": "PASS_FIELD_REALIZATION_COMPATIBILITY", "compatible": True}


def _exact_anomaly_record(pq: tuple[int, int], d2: int, y: Fraction) -> dict[str, Fraction]:
    d3 = _su3_dimension(*pq)
    return {
        "SU3_CUBIC": _su3_cubic_anomaly(*pq) * d2,
        "SU3_SQ_U1": _su3_dynkin_index(*pq) * d2 * y,
        "SU2_SQ_U1": _su2_index(d2) * d3 * y,
        "U1_CUBIC": Fraction(d3 * d2) * y**3,
        "GRAV_SQ_U1": Fraction(d3 * d2) * y,
    }


def _anomaly_gate_current(row: Mapping[str, Any]) -> dict[str, Any]:
    kind = str(row["field_realization"])
    pq = tuple(int(v) for v in row["su3_dynkin"])
    d2 = int(row["su2_dimension"])
    y = _fraction(row["hypercharge"])
    if kind in {"REAL_SCALAR", "COMPLEX_SCALAR", "GAUGE_VECTOR", "MASSIVE_VECTOR_MATTER"}:
        return {
            "status": "BOSON_NO_CHIRAL_GAUGE_ANOMALY",
            "closure_complete": True,
            "completion_fields": [],
            "candidate_preserved": True,
        }
    seed = _exact_anomaly_record(pq, d2, y)
    witten = _witten_bit(pq, d2)
    if kind == "VECTORLIKE_DIRAC":
        partner_pq, partner_y = (pq[1], pq[0]), -y
        partner = _exact_anomaly_record(partner_pq, d2, partner_y)
        residual = {k: seed[k] + partner[k] for k in seed}
        return {
            "status": "VECTORLIKE_ANOMALY_CANCELLATION_BY_CONSTRUCTION",
            "closure_complete": all(v == 0 for v in residual.values()),
            "seed_local_anomaly": {k: _frac_text(v) for k, v in seed.items()},
            "combined_anomaly_residual": {k: _frac_text(v) for k, v in residual.items()},
            "combined_witten_mod2": (2 * witten) % 2,
            "completion_fields": [{"su3_dynkin": list(partner_pq), "su2_dimension": d2, "hypercharge": _frac_text(partner_y)}],
            "candidate_preserved": True,
        }
    if kind != "CHIRAL_WEYL":
        return {"status": "UNSUPPORTED_FIELD_REALIZATION", "closure_complete": False, "candidate_preserved": True}
    seed_zero = all(v == 0 for v in seed.values()) and witten == 0
    if seed_zero and _is_real_scalar_representation(pq, d2, y):
        return {
            "status": "ANOMALY_FREE_STANDALONE_REAL_REPRESENTATION",
            "closure_complete": True,
            "seed_local_anomaly": {k: _frac_text(v) for k, v in seed.items()},
            "seed_witten_mod2": witten,
            "completion_fields": [],
            "mass_completion_basis": "MAJORANA_OR_REAL_REP_BILINEAR",
            "candidate_preserved": True,
        }
    # Exact one-field conjugate completion inherited from the v3.38 downstream owner.
    partner_pq, partner_y = (pq[1], pq[0]), -y
    partner = _exact_anomaly_record(partner_pq, d2, partner_y)
    residual = {k: seed[k] + partner[k] for k in seed}
    return {
        "status": "PASS_EXACT_CONJUGATE_ANOMALY_COMPLETION",
        "closure_complete": all(v == 0 for v in residual.values()) and (2 * witten) % 2 == 0,
        "seed_was_standalone_anomaly_free": seed_zero,
        "seed_local_anomaly": {k: _frac_text(v) for k, v in seed.items()},
        "seed_witten_mod2": witten,
        "combined_anomaly_residual": {k: _frac_text(v) for k, v in residual.items()},
        "combined_witten_mod2": (2 * witten) % 2,
        "completion_fields": [{"field_realization": "CHIRAL_WEYL", "su3_dynkin": list(partner_pq), "su2_dimension": d2, "hypercharge": _frac_text(partner_y)}],
        "minimum_added_multiplet_count": 1,
        "minimum_scope": "EXACT_CONJUGATE_EXISTENCE_CLOSURE_NOT_NONMIRROR_GLOBAL_OPTIMUM",
        "candidate_preserved": True,
    }


def _mass_generation_gate_current(row: Mapping[str, Any], anomaly_gate: Mapping[str, Any]) -> dict[str, Any]:
    kind = str(row["field_realization"])
    if kind == "CHIRAL_WEYL":
        if not anomaly_gate.get("closure_complete"):
            return {"status": "CHIRAL_FIELD_CONTENT_CLOSURE_OPEN", "mass_numerically_identified": False}
        if anomaly_gate.get("completion_fields"):
            return {"status": "PASS_RENORMALIZABLE_FULL_MASS_PATH", "operator": "M psi X + h.c.", "numerical_mass": "OPEN", "mass_numerically_identified": False}
        return {"status": "PASS_RENORMALIZABLE_MAJORANA_OR_REAL_REP_MASS_PATH", "operator": "(M/2) psi psi + h.c.", "numerical_mass": "OPEN", "mass_numerically_identified": False}
    if kind == "VECTORLIKE_DIRAC":
        return {"status": "PASS_GAUGE_INVARIANT_RENORMALIZABLE_DIRAC_MASS", "operator": "-M Psi_bar Psi", "mass_dimension": 3, "numerical_mass": "OPEN", "mass_numerically_identified": False}
    if kind in {"REAL_SCALAR", "COMPLEX_SCALAR"}:
        return {"status": "PASS_GAUGE_INVARIANT_RENORMALIZABLE_SCALAR_MASS", "operator": "m_phi^2 phi^dagger phi" if kind == "COMPLEX_SCALAR" else "(m_phi^2/2) phi^2", "numerical_mass": "OPEN", "mass_numerically_identified": False}
    if kind == "MASSIVE_VECTOR_MATTER":
        return {"status": "PASS_EFFECTIVE_PROCA_MASS_BUT_UV_COMPLETION_OPEN", "operator": "m_V^2 V_mu^dagger V^mu", "warning": "mass term does not close longitudinal-vector high-energy unitarity", "numerical_mass": "OPEN", "mass_numerically_identified": False}
    if kind == "GAUGE_VECTOR":
        return {"status": "GAUGE_BOSON_MASS_REQUIRES_DECLARED_STUECKELBERG_OR_SYMMETRY_BREAKING", "numerical_mass": "OPEN", "mass_numerically_identified": False}
    return {"status": "UNSUPPORTED_FIELD_REALIZATION", "mass_numerically_identified": False}


def _su2_quadratic_casimir(dimension: int) -> Fraction:
    d = int(dimension)
    return Fraction(d * d - 1, 4)


def _matter_unitarity_column_current(*, pq: tuple[int, int], d2: int, y: Fraction, statistics: str, real_scalar: bool = False, gauge_couplings: Mapping[str, float] | None = None) -> np.ndarray:
    total_dim = _su3_dimension(*pq) * int(d2)
    casimirs = {"SU3": _su3_quadratic_casimir(*pq), "SU2": _su2_quadratic_casimir(d2), "U1": y * y}
    adj_dims = {"SU3": 8, "SU2": 3, "U1": 1}
    couplings = _GAUGE_UNITARITY_REFERENCE_COUPLINGS if gauge_couplings is None else gauge_couplings
    out = []
    for group in ("SU3", "SU2", "U1"):
        c2 = float(casimirs[group])
        if c2 == 0.0:
            out.append(0.0); continue
        g = float(couplings[group])
        base = (g * g / (8.0 * np.pi)) * np.sqrt(float(total_dim) / float(adj_dims[group])) * c2
        if statistics == "FERMION":
            base *= np.pi / 2.0
        elif statistics == "BOSON":
            if real_scalar: base /= np.sqrt(2.0)
        else:
            raise ValueError(statistics)
        out.append(float(base))
    return np.asarray(out, dtype=float)


def _sm_unitarity_columns_current(*, gauge_couplings: Mapping[str, float] | None = None) -> list[np.ndarray]:
    cols: list[np.ndarray] = []
    for pq, d2, y in _SM_CHIRAL_ROWS.values():
        for _ in range(3):
            cols.append(_matter_unitarity_column_current(pq=pq, d2=d2, y=y, statistics="FERMION", gauge_couplings=gauge_couplings))
    cols.append(_matter_unitarity_column_current(pq=(0, 0), d2=2, y=Fraction(1, 2), statistics="BOSON", gauge_couplings=gauge_couplings))
    return cols


def _largest_a0_current(columns: Sequence[np.ndarray]) -> float:
    if not columns: return 0.0
    return float(np.linalg.svd(np.column_stack(columns), compute_uv=False)[0])


def _massive_vector_uv_completion_gate_current(row: Mapping[str, Any]) -> dict[str, Any]:
    """Construct and test a minimal simple-group gauge-origin branch.

    For a target (R3,R2)_Y vector, embed SU(3) through R3 and SU(2) through
    R2 into the two diagonal blocks of SU(dim(R3)+dim(R2)).  The off-diagonal
    adjoint generators then contain (R3,R2bar)_Y plus its conjugate.  The U(1)
    block charges a,b are fixed by tracelessness and a-b=Y.

    This is a group-theoretic gauge-origin witness, not by itself a viable UV
    theory.  A simple parent group has one gauge coupling, so the induced SM
    subgroup couplings must satisfy the embedding-index matching relation.  We
    test that relation against the owner's declared one-loop SM running window.
    """
    if str(row.get("field_realization")) != "MASSIVE_VECTOR_MATTER":
        return {"status": "NOT_APPLICABLE_NON_MASSIVE_VECTOR_MATTER", "candidate_preserved": True}
    pq = tuple(int(v) for v in row["su3_dynkin"])
    d3 = int(row["su3_dimension"])
    d2 = int(row["su2_dimension"])
    y = _fraction(row["hypercharge"])
    n_parent = d3 + d2
    a = y * Fraction(d2, n_parent)
    b = -y * Fraction(d3, n_parent)
    trace_residual = d3 * a + d2 * b
    cross_charge = a - b
    i3 = 2 * _su3_dynkin_index(*pq)
    i2 = 2 * _su2_index(d2)
    iy = 2 * (d3 * a * a + d2 * b * b)
    relations = {}
    if i3 > 0:
        relations["SU3"] = {"embedding_index": _frac_text(i3), "matching": "g_parent=g3*sqrt(I3)"}
    if i2 > 0:
        relations["SU2"] = {"embedding_index": _frac_text(i2), "matching": "g_parent=g2*sqrt(I2)"}
    if iy > 0:
        relations["U1"] = {"embedding_index": _frac_text(iy), "matching": "g_parent=gprime*sqrt(IY)"}

    best = None
    for scale in np.geomspace(100.0, 1.0e19, 321):
        couplings = _sm_running_couplings_current(float(scale))
        if couplings is None:
            break
        req = {}
        if i3 > 0: req["SU3"] = float(couplings["SU3"] * math.sqrt(float(i3)))
        if i2 > 0: req["SU2"] = float(couplings["SU2"] * math.sqrt(float(i2)))
        if iy > 0: req["U1"] = float(couplings["U1"] * math.sqrt(float(iy)))
        vals = list(req.values())
        if len(vals) <= 1:
            spread = 0.0
        else:
            mean = float(sum(vals) / len(vals))
            spread = float((max(vals) - min(vals)) / mean) if mean else float("inf")
        row_scan = {"scale_gev": float(scale), "required_parent_couplings": req, "relative_spread": spread}
        if best is None or spread < best["relative_spread"]:
            best = row_scan

    match = bool(best is not None and best["relative_spread"] <= 1.0e-6)
    branch_status = (
        "PASS_MINIMAL_BLOCK_SIMPLE_GROUP_COMMON_GAUGE_COUPLING_MATCH"
        if match else
        "REJECT_MINIMAL_BLOCK_SIMPLE_GROUP_COUPLING_MATCHING_NO_COMMON_PARENT_G_IN_DECLARED_ONE_LOOP_WINDOW"
    )
    payload = {
        "status": "GAUGE_ORIGIN_BRANCH_ANALYZED_ALTERNATIVE_UV_CLASSES_OPEN",
        "minimal_block_branch": {
            "status": branch_status,
            "parent_group": f"SU({n_parent})",
            "fundamental_branching": f"{n_parent} -> ({row['su3_label']},1)_a + (1,{d2})_b",
            "adjoint_off_diagonal_contains_target": True,
            "target_branch": {"su3_dynkin": list(pq), "su2_dimension": d2, "hypercharge": _frac_text(y)},
            "block_u1_charges": {"a": _frac_text(a), "b": _frac_text(b)},
            "tracelessness_residual": _frac_text(trace_residual),
            "off_diagonal_hypercharge": _frac_text(cross_charge),
            "embedding_indices": {"SU3": _frac_text(i3), "SU2": _frac_text(i2), "U1": _frac_text(iy)},
            "su3_dynkin_index": _frac_text(_su3_dynkin_index(*pq)),
            "required_g3_over_g2_if_single_parent_coupling": None if i3 <= 0 or i2 <= 0 else float(math.sqrt(float(i2 / i3))),
            "coupling_matching_relations": relations,
            "best_one_loop_matching_diagnostic": best,
            "branch_falsified_within_declared_assumptions": not match,
            "symmetry_breaking_scalar_potential_constructed": False,
            "group_theoretic_embedding_witness": True,
        },
        "surviving_uv_classes": [
            "NONMINIMAL_GAUGE_EMBEDDING_WITH_DIFFERENT_EMBEDDING_INDICES",
            "STRONGLY_COUPLED_OR_COMPOSITE_VECTOR_COMPLETION",
        ] if not match else ["MINIMAL_BLOCK_SIMPLE_GROUP_GAUGE_COMPLETION_REQUIRES_EXPLICIT_BREAKING_SECTOR"],
        "absolute_uv_no_go_proved": False,
        "candidate_preserved": True,
        "new_particle_claimed": False,
        "world_existence_claimed": False,
    }
    return {**payload, "digest": digest_payload(payload)}


def _unitarity_descriptors_current(row: Mapping[str, Any], anomaly_gate: Mapping[str, Any]) -> tuple[list[dict[str, Any]], str | None]:
    kind = str(row["field_realization"]); pq = tuple(row["su3_dynkin"]); d2 = int(row["su2_dimension"]); y = _fraction(row["hypercharge"])
    if kind == "MASSIVE_VECTOR_MATTER":
        return [], "MASSIVE_VECTOR_REQUIRES_UV_GAUGE_OR_COMPOSITE_COMPLETION_BEFORE_GAUGE_UNITARITY_FORMULA_IS_APPLICABLE"
    if kind == "GAUGE_VECTOR":
        return [], "GAUGE_VECTOR_REQUIRES_EXTENDED_GAUGE_GROUP_AND_SYMMETRY_BREAKING_PATTERN_BEFORE_MATTER_MULTIPLET_UNITARITY_TEST"
    if kind == "VECTORLIKE_DIRAC":
        return [
            {"field_realization": "CHIRAL_WEYL", "su3_dynkin": list(pq), "su2_dimension": d2, "hypercharge": _frac_text(y), "statistics": "FERMION"},
            {"field_realization": "CHIRAL_WEYL", "su3_dynkin": [pq[1], pq[0]], "su2_dimension": d2, "hypercharge": _frac_text(-y), "statistics": "FERMION"},
        ], None
    if kind == "CHIRAL_WEYL":
        ds = [{"field_realization": "CHIRAL_WEYL", "su3_dynkin": list(pq), "su2_dimension": d2, "hypercharge": _frac_text(y), "statistics": "FERMION"}]
        ds.extend({**f, "statistics": "FERMION"} for f in anomaly_gate.get("completion_fields", []))
        return ds, None
    if kind in {"REAL_SCALAR", "COMPLEX_SCALAR"}:
        return [{"field_realization": kind, "su3_dynkin": list(pq), "su2_dimension": d2, "hypercharge": _frac_text(y), "statistics": "BOSON"}], None
    return [], "UNSUPPORTED_FIELD_REALIZATION"


def _sm_running_couplings_current(scale_gev: float, reference_scale_gev: float = 100.0) -> dict[str, float] | None:
    if scale_gev < reference_scale_gev or not np.isfinite(scale_gev): return None
    log_ratio = float(np.log(scale_gev / reference_scale_gev))
    b = {"U1": 41.0/6.0, "SU2": -19.0/6.0, "SU3": -7.0}
    out = {}
    for group in ("SU3", "SU2", "U1"):
        g0 = float(_GAUGE_UNITARITY_REFERENCE_COUPLINGS[group])
        inv = 1.0/(g0*g0) - b[group]*log_ratio/(8.0*np.pi*np.pi)
        if inv <= 0.0: return None
        out[group] = float(1.0/np.sqrt(inv))
    return out


def _a0_current(descriptors: Sequence[Mapping[str, Any]], scale_gev: float) -> tuple[float, float] | None:
    couplings = _sm_running_couplings_current(scale_gev)
    if couplings is None: return None
    base = _sm_unitarity_columns_current(gauge_couplings=couplings)
    extra = []
    for d in descriptors:
        pq = tuple(int(v) for v in d["su3_dynkin"])
        extra.append(_matter_unitarity_column_current(pq=pq, d2=int(d["su2_dimension"]), y=_fraction(d["hypercharge"]), statistics=str(d["statistics"]), real_scalar=str(d["field_realization"]) == "REAL_SCALAR", gauge_couplings=couplings))
    return _largest_a0_current(base), _largest_a0_current(base + extra)


def _unitarity_gate_current(row: Mapping[str, Any], anomaly_gate: Mapping[str, Any], uv_gate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    descriptors, blocked = _unitarity_descriptors_current(row, anomaly_gate)
    if blocked:
        if str(row.get("field_realization")) == "MASSIVE_VECTOR_MATTER" and uv_gate:
            branch = uv_gate.get("minimal_block_branch", {})
            return {"status": "MASSIVE_VECTOR_QUANTITATIVE_UNITARITY_BLOCKED_AFTER_MINIMAL_GAUGE_BRANCH_TEST", "reason": blocked, "minimal_uv_branch_status": branch.get("status"), "test_applicable": False, "candidate_preserved": True, "new_particle_claimed": False}
        return {"status": blocked, "test_applicable": False, "candidate_preserved": True, "new_particle_claimed": False}
    ref = _a0_current(descriptors, 100.0)
    if ref is None: raise AssertionError("100 GeV unitarity calibration unavailable")
    baseline, total = ref
    ref_pass = total <= _GAUGE_UNITARITY_BOUND + 1e-12
    first_pass = None; min_pair = None
    for scale in np.geomspace(100.0, 1.0e19, 321):
        pair = _a0_current(descriptors, float(scale))
        if pair is None: break
        total_s = pair[1]
        if min_pair is None or total_s < min_pair[1]: min_pair = (float(scale), float(total_s))
        if first_pass is None and total_s <= _GAUGE_UNITARITY_BOUND: first_pass = (float(scale), float(total_s))
    any_pass = ref_pass or first_pass is not None
    status = "PASS_REFERENCE_GAUGE_PARTIAL_WAVE_UNITARITY_NECESSARY_CONDITION" if ref_pass else ("PASS_GAUGE_PARTIAL_WAVE_UNITARITY_IF_THRESHOLD_ABOVE_DERIVED_SCALE" if any_pass else "NO_MINIMAL_WEAKLY_COUPLED_PASS_BELOW_PLANCK_DIAGNOSTIC_UV_OR_COMPOSITE_COMPLETION_OPEN")
    return {
        "status": status, "test_applicable": True, "reference_scale_gev": 100.0,
        "reference_gauge_couplings": dict(_GAUGE_UNITARITY_REFERENCE_COUPLINGS),
        "sm_baseline_a0_max_replayed": baseline, "candidate_theory_a0_max_at_reference": total,
        "unitarity_bound_abs_re_a0": _GAUGE_UNITARITY_BOUND,
        "necessary_condition_passed_at_reference": ref_pass,
        "necessary_condition_passes_for_some_scanned_threshold": any_pass,
        "threshold_running_diagnostic": {"first_passing_threshold_gev_grid_estimate": None if first_pass is None else first_pass[0], "a0_at_first_pass": None if first_pass is None else first_pass[1], "minimum_a0_in_scan": None if min_pair is None else min_pair[1], "scale_of_minimum_a0_gev": None if min_pair is None else min_pair[0], "diagnostic_upper_scale_gev": 1.0e19, "grid_is_numerical_diagnostic_not_space_ceiling": True},
        "candidate_fields": descriptors, "candidate_preserved": True, "new_particle_claimed": False,
        "source_provenance": "ported replacement-in-place from qpdtr particle_space v3.38; current standard hypercharge Q=T3+Y",
    }


def _beta_delta_descriptor_current(desc: Mapping[str, Any]) -> tuple[Fraction, Fraction, Fraction]:
    kind = str(desc["field_realization"]); pq = tuple(int(v) for v in desc["su3_dynkin"]); d3 = _su3_dimension(*pq); d2 = int(desc["su2_dimension"]); y = _fraction(desc["hypercharge"])
    t3 = _su3_dynkin_index(*pq) * d2; t2 = _su2_index(d2) * d3; t1 = y*y*d3*d2
    if kind == "CHIRAL_WEYL": factor = Fraction(2,3)
    elif kind == "COMPLEX_SCALAR": factor = Fraction(1,3)
    elif kind == "REAL_SCALAR": factor = Fraction(1,6)
    else: raise ValueError(kind)
    return factor*t1, factor*t2, factor*t3


def _rg_gate_current(row: Mapping[str, Any], anomaly_gate: Mapping[str, Any], uv_gate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    descriptors, blocked = _unitarity_descriptors_current(row, anomaly_gate)
    if blocked:
        if str(row.get("field_realization")) == "MASSIVE_VECTOR_MATTER" and uv_gate:
            branch = uv_gate.get("minimal_block_branch", {})
            return {"status": "RG_REQUIRES_SURVIVING_EXPLICIT_UV_COMPLETION_AFTER_MINIMAL_GAUGE_BRANCH_TEST", "reason": blocked, "minimal_uv_branch_status": branch.get("status"), "candidate_preserved": True, "new_particle_claimed": False}
        return {"status": "RG_REQUIRES_UV_COMPLETION_BEFORE_COEFFICIENT_IS_WELL_DEFINED", "reason": blocked, "candidate_preserved": True, "new_particle_claimed": False}
    d1=d2=d3=Fraction(0)
    for desc in descriptors:
        a,b,c=_beta_delta_descriptor_current(desc); d1+=a; d2+=b; d3+=c
    b1=Fraction(41,6)+d1; b2=Fraction(-19,6)+d2; b3=Fraction(-7)+d3
    return {"status": "PASS_ONE_LOOP_GAUGE_RUNNING_SYMBOLIC_CLOSURE", "beta_convention": "beta(g_i)=b_i*g_i^3/(16*pi^2)", "delta_b": {"U1_gprime": _frac_text(d1), "SU2": _frac_text(d2), "SU3": _frac_text(d3)}, "b_above_candidate_threshold": {"U1_gprime": _frac_text(b1), "SU2": _frac_text(b2), "SU3": _frac_text(b3)}, "su2_asymptotic_freedom_preserved": b2<0, "su3_asymptotic_freedom_preserved": b3<0, "u1_landau_running_accelerated": d1>0, "threshold_mass_identified": False, "candidate_preserved": True, "new_particle_claimed": False}


def _rg_window_current(rg: Mapping[str, Any], u: Mapping[str, Any]) -> dict[str, Any]:
    if not str(rg.get("status", "")).startswith("PASS_"): return {"status": "RG_WINDOW_BLOCKED_UNTIL_UV_COMPLETION_DEFINED", "candidate_preserved": True}
    if not bool(u.get("test_applicable", False)): return {"status": "RG_WINDOW_NOT_DEFINED_FOR_CURRENT_VECTOR_COMPLETION", "candidate_preserved": True}
    threshold = 100.0 if u.get("necessary_condition_passed_at_reference") else u.get("threshold_running_diagnostic",{}).get("first_passing_threshold_gev_grid_estimate")
    if threshold is None: return {"status": "NO_WEAKLY_COUPLED_THRESHOLD_FOUND_FOR_RG_WINDOW", "candidate_preserved": True}
    couplings=_sm_running_couplings_current(float(threshold))
    if couplings is None: return {"status":"REFERENCE_RUNNING_UNAVAILABLE_AT_THRESHOLD","candidate_preserved":True}
    rows={}; finite=[]
    for bname,gname in {"U1_gprime":"U1","SU2":"SU2","SU3":"SU3"}.items():
        b=float(_fraction(rg["b_above_candidate_threshold"][bname]))
        if b<=0: rows[bname]={"b":rg["b_above_candidate_threshold"][bname],"landau_pole":"NONE_AT_ONE_LOOP_FOR_NEGATIVE_OR_ZERO_B"}; continue
        g=float(couplings[gname]); log10=(8*np.pi*np.pi/(b*g*g))/np.log(10.0); finite.append((bname,float(log10))); rows[bname]={"b":rg["b_above_candidate_threshold"][bname],"log10_Lambda_over_threshold":float(log10)}
    earliest=min(finite,key=lambda x:x[1]) if finite else None
    return {"status":"PASS_PARAMETRIC_ONE_LOOP_PERTURBATIVE_WINDOW","chosen_threshold_gev_for_diagnostic":float(threshold),"threshold_is_candidate_mass_measurement":False,"group_windows":rows,"earliest_finite_landau_group":None if earliest is None else earliest[0],"earliest_log10_Lambda_over_threshold":None if earliest is None else earliest[1],"candidate_preserved":True}


def _decay_gate_current(row: Mapping[str, Any]) -> dict[str, Any]:
    kind=str(row["field_realization"]); pq=tuple(row["su3_dynkin"]); d2=int(row["su2_dimension"]); y=_fraction(row["hypercharge"])
    bridges=[]
    if kind in {"CHIRAL_WEYL","VECTORLIKE_DIRAC"}:
        for r in _yukawa_partners(pq,d2,y): bridges.append({"operator_class":"RENORMALIZABLE_HIGGS_YUKAWA",**r})
        for sm_name,(spq,sd2,sy) in _SM_CHIRAL_ROWS.items():
            if _color_pair_singlet(pq,spq) and d2==sd2 and y+sy==0:
                bridges.append({"operator_class":"GAUGE_INVARIANT_BILINEAR_MASS_MIXING","sm_field":sm_name})
        return {"status":"PASS_RENORMALIZABLE_SM_DECAY_OR_MIXING_BRIDGE_EXISTS" if bridges else "NO_GENERIC_RENORMALIZABLE_SM_DECAY_BRIDGE_IDENTIFIED","bridges":bridges,"stable_particle_claimed":False,"higher_dimensional_or_extra_sector_decay_not_excluded":True}
    if kind=="REAL_SCALAR" and pq==(0,0) and d2==1 and y==0:
        bridges=[{"operator_class":"LINEAR_HIGGS_PORTAL","expression":"mu_S S H^dagger H"}]
    elif kind=="COMPLEX_SCALAR" and pq==(0,0) and d2==1 and y==0:
        bridges=[{"operator_class":"COMPLEX_LINEAR_HIGGS_PORTAL","expression":"mu_S S H^dagger H + h.c."}]
    elif kind=="COMPLEX_SCALAR" and pq==(0,0) and d2==2 and abs(y)==Fraction(1,2):
        bridges=[{"operator_class":"SECOND_HIGGS_DOUBLET_MIXING","expression":"m12^2 H1^dagger H2 + h.c."}]
    elif kind=="GAUGE_VECTOR" and pq==(0,0) and d2==1 and y==0:
        bridges=[{"operator_class":"KINETIC_MIXING","expression":"epsilon B_{mu nu} X^{mu nu}"}]
    if bridges:
        return {"status":"PASS_DECLARED_RENORMALIZABLE_DECAY_OR_MIXING_BRIDGE_EXISTS","bridges":bridges,"stable_particle_claimed":False}
    return {"status":"DECAY_TOPOLOGY_REQUIRES_REPRESENTATION_PRODUCT_OR_UV_BRIDGE_NOT_FIXED_BY_CURRENT_OWNER","bridges":[],"stable_particle_claimed":False,"candidate_preserved":True}


def _pdg_gate_current(row: Mapping[str, Any]) -> dict[str, Any]:
    return {"status":"PDG_FIXED_FORMAT_NOT_DECISIVE_FOR_REPRESENTATION_COORDINATE","reason":"PDG identity tables do not encode a complete arbitrary SU(3)xSU(2)xU(1) representation coordinate and mass is open","candidate_mass_open":True,"known_particle_identity_claimed":False,"new_particle_claimed":False,"candidate_preserved":True}


def _experimental_gate_current(row: Mapping[str, Any], decay: Mapping[str, Any]) -> dict[str, Any]:
    d3=int(row["su3_dimension"]); d2=int(row["su2_dimension"]); charges=[_fraction(v) for v in row["electric_charge_components"]]
    channels=[]
    if d3>1: channels += ["QCD_PAIR_PRODUCTION","JETS_PLUS_DECAY_PRODUCTS","R_HADRON_OR_STABLE_COLORED_RELIC_IF_LONG_LIVED"]
    if d2>1 or _fraction(row["hypercharge"])!=0: channels += ["ELECTROWEAK_DRELL_YAN_OR_VECTOR_BOSON_PRODUCTION"]
    if any(q!=0 for q in charges): channels += ["PROMPT_MULTICHARGED_OR_CASCADE_SEARCH","HEAVY_STABLE_CHARGED_PARTICLE_OR_HIGH_IONIZATION_IF_LONG_LIVED"]
    if any(q==0 for q in charges): channels += ["MISSING_MOMENTUM_IF_NEUTRAL_COMPONENT_IS_STABLE_OR_INVISIBLE"]
    # Regression fix: status text containing the substring DECAY is not evidence of a bridge.
    if bool(decay.get("bridges")): channels += ["PROMPT_OR_DISPLACED_DECAY_TOPOLOGY_FROM_DECLARED_RENORMALIZABLE_BRIDGE"]
    return {"status":"PASS_FALSIFICATION_CHANNEL_MAP_PARAMETER_POINT_OPEN","search_channels":sorted(set(channels)),"mass_limit_numerically_recast":False,"cross_section_numerically_computed":False,"branching_fractions_numerically_computed":False,"held_out_falsification_rule":"freeze mass/couplings/lifetime, compute production x acceptance x branching fractions, reject if incompatible with declared held-out likelihood/limit","candidate_preserved":True,"new_particle_claimed":False}


def _cosmology_gate_current(row: Mapping[str, Any], decay: Mapping[str, Any]) -> dict[str, Any]:
    d3=int(row["su3_dimension"]); charges=[_fraction(v) for v in row["electric_charge_components"]]; decay_open=not bool(decay.get("bridges")); obligations=[]
    if d3>1 and decay_open: obligations.append("AVOID_COSMOLOGICALLY_STABLE_COLORED_RELIC_OR_DECLARE_NONSTANDARD_COSMOLOGY")
    if any(q!=0 for q in charges) and decay_open: obligations.append("AVOID_COSMOLOGICALLY_STABLE_ELECTRICALLY_CHARGED_RELIC_OR_DECLARE_NONSTANDARD_COSMOLOGY")
    if any(q==0 for q in charges): obligations.append("IF_STABLE_NEUTRAL_COMPONENT_IS_DARK_MATTER_COMPUTE_RELIC_ABUNDANCE_AND_DIRECT_INDIRECT_DETECTION")
    return {"status":"COSMOLOGY_PARAMETER_DEPENDENT_OBLIGATIONS_MAPPED" if obligations else "NO_MODEL_INDEPENDENT_COSMOLOGY_OBLIGATION_BEYOND_STANDARD_THERMAL_HISTORY_ASSUMPTIONS","obligations":obligations,"relic_density_computed":False,"candidate_preserved":True,"new_particle_claimed":False}


def _close_particle_coordinate_impl(*, spin: str, su3_dynkin: Sequence[int], su2_dimension: int, hypercharge: Any, copy: int, field_realization: str, selected_global_form: str | None, selection_provenance: Mapping[str, Any] | None) -> dict[str, Any]:
    pq=(int(su3_dynkin[0]),int(su3_dynkin[1])); d2=int(su2_dimension); y=_fraction(hypercharge); copy=int(copy); realization=str(field_realization)
    if len(su3_dynkin)!=2 or pq[0]<0 or pq[1]<0 or d2<1 or copy<1: raise ValueError("invalid ParticleSpace coordinate")
    compat=_realization_compatibility(spin,realization,pq,d2,y)
    global_form=sm_gauge_global_form_profile(pq,d2,y)
    if selected_global_form is not None and selected_global_form not in SM_GAUGE_GLOBAL_FORMS: raise ValueError("unknown SM global form")
    label,d3,_,_,conj=_su3_record(pq)
    row={"spin":spin,"field_realization":realization,"su3_dynkin":list(pq),"su3_label":label,"su3_dimension":d3,"su3_conjugate_dynkin":list(conj),"su2_dimension":d2,"hypercharge":_frac_text(y),"copy":copy,"electric_charge_components":_charge_spectrum(d2,y)}
    coordinate_digest=digest_payload(row)
    if not compat["compatible"]:
        result={"schema":PARTICLE_CLOSURE_SCHEMA,"owner_id":OWNER_ID,"coordinate":row,"coordinate_digest":coordinate_digest,"field_realization_gate":compat,"global_form_axis":global_form,"overall_closure_status":"REJECT_STRUCTURALLY_INCONSISTENT_REALIZATION","candidate_preserved":False,"new_particle_claimed":False,"world_existence_claimed":False,"selection_provenance":dict(selection_provenance or {})}
        return {**result,"closure_digest":digest_payload(result)}
    selected_branch=None if selected_global_form is None else global_form["branches"][selected_global_form]
    if selected_branch is not None and selected_branch.get("compatible") is False:
        result={"schema":PARTICLE_CLOSURE_SCHEMA,"owner_id":OWNER_ID,"coordinate":row,"coordinate_digest":coordinate_digest,"field_realization_gate":compat,"global_form_axis":global_form,"selected_global_form":selected_global_form,"overall_closure_status":"REJECT_SELECTED_GLOBAL_FORM_INCOMPATIBLE","candidate_preserved":False,"new_particle_claimed":False,"world_existence_claimed":False,"selection_provenance":dict(selection_provenance or {})}
        return {**result,"closure_digest":digest_payload(result)}
    A=_anomaly_gate_current(row); M=_mass_generation_gate_current(row,A); UV=_massive_vector_uv_completion_gate_current(row); U=_unitarity_gate_current(row,A,UV); R=_rg_gate_current(row,A,UV); Rw=_rg_window_current(R,U); D=_decay_gate_current(row); P=_pdg_gate_current(row); E=_experimental_gate_current(row,D); O=_cosmology_gate_current(row,D)
    blockers=[]
    if not A.get("closure_complete",False): blockers.append(str(A.get("status")))
    if "OPEN" in str(M.get("status","")) or "REQUIRES" in str(M.get("status","")): blockers.append(str(M.get("status")))
    if U.get("test_applicable") is False: blockers.append(str(U.get("status")))
    elif not U.get("necessary_condition_passes_for_some_scanned_threshold",True): blockers.append(str(U.get("status")))
    if str(R.get("status", "")).startswith("RG_REQUIRES_"): blockers.append(str(R.get("status")))
    if not blockers: overall="PASS_SYMBOLIC_FALSIFIABLE_THEORY_CLOSURE_PARAMETER_POINT_OPEN"
    elif any("GAUGE_VECTOR" in b or "STUECKELBERG" in b or "EXTENDED_GAUGE" in b for b in blockers): overall="OPEN_EXTENDED_GAUGE_GROUP_COMPLETION"
    elif str(row.get("field_realization")) == "MASSIVE_VECTOR_MATTER" and UV.get("minimal_block_branch", {}).get("branch_falsified_within_declared_assumptions"):
        overall="OPEN_VECTOR_UV_COMPLETION_MINIMAL_BLOCK_GAUGE_BRANCH_REJECTED"
    elif any("MASSIVE_VECTOR" in b or "UV_COMPLETION" in b for b in blockers): overall="OPEN_VECTOR_UV_COMPLETION"
    elif any("UNITARITY" in b or "WEAKLY_COUPLED" in b for b in blockers): overall="MINIMAL_ELEMENTARY_REALIZATION_NO_PERTURBATIVE_PASS_BELOW_PLANCK_UV_OR_COMPOSITE_COMPLETION_OPEN"
    else: overall="THEORY_CLOSURE_OPEN_WITH_EXPLICIT_BLOCKERS"
    result={
        "schema":PARTICLE_CLOSURE_SCHEMA,"owner_id":OWNER_ID,"closure_sequence":list(PARTICLE_CLOSURE_SEQUENCE),
        "coordinate":row,"coordinate_digest":coordinate_digest,"field_realization_gate":compat,"global_form_axis":global_form,
        "selected_global_form":selected_global_form,"A_anomaly_and_field_content_gate":A,"M_mass_generation_gate":M,
        "UV_gauge_or_composite_completion_gate":UV,
        "U_gauge_partial_wave_unitarity_gate":U,"R_one_loop_rg_gate":R,"R_perturbative_window_gate":Rw,
        "D_renormalizable_decay_bridge_gate":D,"P_pdg_occupancy_gate":P,"E_experimental_falsification_gate":E,"OMEGA_cosmology_gate":O,
        "theory_blockers":sorted(set(blockers)),"overall_closure_status":overall,
        "numerical_mass_identified":False,"numerical_couplings_identified":False,"empirical_existence_established":False,
        "literature_novelty_established":False,"candidate_preserved":True,"new_particle_claimed":False,"world_existence_claimed":False,
        "hypercharge_convention":"CURRENT_STANDARD_Q_EQUALS_T3_PLUS_Y","legacy_adapter":"Y_legacy=2*Y_current",
        "selection_provenance":dict(selection_provenance or {}),
        "legacy_module_runtime_dependency":False,
        "restored_from_v3_38_downstream_capability":True,
        "v7_7_minimal_gauge_uv_branch_test_integrated":True,
    }
    return {**result,"closure_digest":digest_payload(result)}



__all__ = [
    "ParticleSpaceBounds", "ParticleSpaceOwner", "anomaly_vector",
    "sm_gauge_global_form_profile", "SM_GAUGE_GLOBAL_FORMS",
    "OWNER_ID", "SCHEMA", "BLIND_DISCOVERY_SCHEMA", "BLIND_DISCOVERY_ALGORITHM",
    "PARTICLE_CLOSURE_SCHEMA", "PARTICLE_CLOSURE_SEQUENCE", "FIELD_REALIZATIONS_BY_SPIN",
    "legacy_hypercharge_to_standard", "standard_hypercharge_to_legacy",
    "_massive_vector_uv_completion_gate_current",
]
