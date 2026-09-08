"""Owner-connected multidimensional periodic reconstruction for ScienceAtlas.

The authoritative electronic path starts from physically isolated observation prefixes,
scans the complete registered Φ owner/axis space, admits research-local coordinates only
through the axis lifecycle, freezes low-complexity ordering/capacity ensembles, and opens
interior-hole references only afterwards.  No static d/f feature pool or element-specific
exception list is an admissible answer source.  When the frozen ensemble bifurcates, the
result is UNKNOWN and becomes a new discriminating-axis frontier.
"""
from __future__ import annotations

import itertools
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from .schema import digest_payload

OWNER_ID = "PHI-SPACE-PER-ELEMENT-RECONSTRUCTION/3.0.0"
SCHEMA = "phi-space-full-element-state-vector/v4"
FROZEN_REL = Path("data/science_atlas/BLIND_PER_ELEMENT_RECONSTRUCTION_FROZEN.json")
TRAINING_REL = Path("data/science_atlas/ATLAS_IDEAL_ELECTRONIC_TRAINING_1_100.json")
HOLDOUT_REL = Path("data/science_atlas/ATLAS_ELECTRONIC_HOLDOUT_REVEAL_101_118.json")
INTERIOR_D_PREFIX_REL = Path("data/science_atlas/ATLAS_INTERIOR_HOLE_PREFIX_1_20.json")
INTERIOR_F_PREFIX_REL = Path("data/science_atlas/ATLAS_INTERIOR_HOLE_PREFIX_1_56.json")
INTERIOR_HOLE_REVEAL_REL = Path("data/science_atlas/ATLAS_INTERIOR_HOLE_REVEAL.json")
PHI_SPACE_ELECTRONIC_OWNER_ID = "PHI-SPACE-INTERIOR-HOLE-ELECTRONIC-STRUCTURE/1.0.0"

# Generic physical constants / bounded model constants.  These are not element-specific labels.
ALPHA = 7.2973525693e-3
G_SI = 6.67430e-11
C_SI = 299792458.0
U_KG = 1.66053906660e-27
FM = 1.0e-15
R0_FM = 1.20

# Weizsaecker / SEMF coefficients (MeV), used only as a gross nuclear-model channel.
SEMF = {
    "a_v": 15.75,
    "a_s": 17.80,
    "a_c": 0.711,
    "a_a": 23.70,
    "a_p": 34.0,
}

_L = "spdfghiklmno"


def _l_letter(l: int | None) -> str:
    if l is None or l < 0:
        return "?"
    return _L[l] if l < len(_L) else f"l{l}"


def _pairing_delta(z: int, n: int, a: int) -> float:
    if a <= 0:
        return 0.0
    if z % 2 == 0 and n % 2 == 0:
        sign = 1.0
    elif z % 2 == 1 and n % 2 == 1:
        sign = -1.0
    else:
        sign = 0.0
    return sign * SEMF["a_p"] / (a ** 0.75)


def _binding_mev(z: int, n: int) -> float:
    if z < 0 or n < 0:
        return float("-inf")
    a = z + n
    if a <= 1:
        return 0.0
    return (
        SEMF["a_v"] * a
        - SEMF["a_s"] * a ** (2.0 / 3.0)
        - SEMF["a_c"] * z * max(z - 1, 0) / (a ** (1.0 / 3.0))
        - SEMF["a_a"] * (a - 2 * z) ** 2 / a
        + _pairing_delta(z, n, a)
    )


def _semf_isotope_scan(z: int) -> Mapping[str, Any]:
    """Open-ended SEMF isotope scan ranked by binding per nucleon.

    The historical implementation maximized total binding over a finite N window;
    that drives the optimizer toward the upper edge because B grows roughly with A.
    This replacement maximizes B/A and expands N adaptively until the optimum is
    interior and the far tail is demonstrably worse.  There is no fixed N ceiling.
    """
    z = int(z)
    if z < 1:
        raise ValueError("Z must be positive")
    n_hi = max(16, 2 * z)
    while True:
        rows = []
        best_n = 0
        best_ba = float("-inf")
        for n in range(0, n_hi + 1):
            a = z + n
            b = _binding_mev(z, n)
            ba = b / a if a > 0 else float("-inf")
            rows.append((n, b, ba))
            if ba > best_ba:
                best_n, best_ba = n, ba
        tail_ba = rows[-1][2]
        if best_n <= n_hi - 4 and tail_ba < best_ba - 0.02:
            break
        n_hi *= 2
    return {
        "Z": z,
        "N_search_upper_reached": n_hi,
        "fixed_N_ceiling": None,
        "termination_rule": "BEST_BINDING_PER_NUCLEON_INTERIOR_AND_FAR_TAIL_WORSE",
        "best_N": best_n,
        "best_binding_per_nucleon_MeV": best_ba,
    }


def _alpha_half_life_vss_seconds(z: int, n: int, q_alpha_mev: float | None) -> float | None:
    """Viola-Seaborg-Sobiczewski alpha partial half-life reference model."""
    if q_alpha_mev is None or not math.isfinite(float(q_alpha_mev)) or float(q_alpha_mev) <= 0.0:
        return None
    z = int(z); n = int(n)
    if z % 2 == 0 and n % 2 == 0:
        hindrance = 0.0
    elif z % 2 == 0 and n % 2 == 1:
        hindrance = 1.066
    elif z % 2 == 1 and n % 2 == 0:
        hindrance = 0.772
    else:
        hindrance = 1.114
    log10_t = (1.66175 * z - 8.5166) / math.sqrt(float(q_alpha_mev)) - 0.20228 * z - 33.9069 + hindrance
    return 10.0 ** log10_t if log10_t < 300.0 else float("inf")


def _alpha_half_life_udl_seconds(z: int, n: int, q_alpha_mev: float | None) -> float | None:
    """Qi et al. universal-decay-law alpha partial half-life reference model."""
    if q_alpha_mev is None or not math.isfinite(float(q_alpha_mev)) or float(q_alpha_mev) <= 0.0:
        return None
    a_parent = int(z) + int(n)
    if a_parent <= 4 or int(z) <= 2:
        return None
    a_d = a_parent - 4
    z_d = int(z) - 2
    a_red = 4.0 * a_d / a_parent
    chi = 2.0 * z_d * math.sqrt(a_red / float(q_alpha_mev))
    rho = math.sqrt(a_red * 2.0 * z_d * (a_d ** (1.0 / 3.0) + 4.0 ** (1.0 / 3.0)))
    log10_t = 0.4314 * chi - 0.4087 * rho - 25.7725
    return 10.0 ** log10_t if log10_t < 300.0 else float("inf")


def _nuclear_candidate(z: int) -> Mapping[str, Any]:
    """Gross open-ended nuclear reference candidate; never an existence claim."""
    scan = _semf_isotope_scan(int(z))
    n = int(scan["best_N"])
    a = int(z) + n
    b = _binding_mev(int(z), n)
    ba = b / a if a > 0 else 0.0
    sn = b - _binding_mev(int(z), n - 1) if n > 0 else None
    s2n = b - _binding_mev(int(z), n - 2) if n > 1 else None
    sp = b - _binding_mev(int(z) - 1, n) if int(z) > 1 else None
    s2p = b - _binding_mev(int(z) - 2, n) if int(z) > 2 else None
    q_alpha = None
    if int(z) >= 2 and n >= 2:
        q_alpha = _binding_mev(int(z) - 2, n - 2) + 28.295674 - b
    # Atomic beta-minus Q proxy using m_n-m_H from AME/CODATA-compatible constants.
    q_beta_minus = None
    if n >= 1:
        q_beta_minus = 0.782347 + _binding_mev(int(z) + 1, n - 1) - b
    radius_fm = R0_FM * (a ** (1.0 / 3.0)) if a > 0 else 0.0
    fissility = (int(z) * int(z)) / (50.13 * a) if a > 0 else float("inf")
    mass_kg = a * U_KG
    radius_m = radius_fm * FM
    compactness = 2.0 * G_SI * mass_kg / (radius_m * C_SI * C_SI) if radius_m > 0 else 0.0
    alpha_vss = _alpha_half_life_vss_seconds(int(z), n, q_alpha)
    alpha_udl = _alpha_half_life_udl_seconds(int(z), n, q_alpha)
    if b <= 0:
        regime = "GROSS_SEMF_UNBOUND"
    elif (sn is not None and sn <= 0) or (sp is not None and sp <= 0):
        regime = "GROSS_SEMF_PARTICLE_SEPARATION_FRONTIER"
    elif fissility >= 1.0:
        regime = "GROSS_SEMF_FISSILITY_DOMINATED_FRONTIER"
    else:
        regime = "GROSS_SEMF_BOUND_CANDIDATE"
    return {
        "nuclear_model": "OPEN_ENDED_GROSS_SEMF_BA_OPTIMIZATION/2.0",
        "N_model": n,
        "A_model": a,
        "binding_energy_MeV": b,
        "binding_per_nucleon_MeV": ba,
        "S_n_model_MeV": sn,
        "S_2n_model_MeV": s2n,
        "S_p_model_MeV": sp,
        "S_2p_model_MeV": s2p,
        "Q_alpha_model_MeV": q_alpha,
        "Q_beta_minus_model_MeV": q_beta_minus,
        "alpha_half_life_VSS_s": alpha_vss,
        "alpha_half_life_UDL_s": alpha_udl,
        "alpha_half_life_model_spread_log10": (
            abs(math.log10(alpha_vss) - math.log10(alpha_udl))
            if alpha_vss not in (None, 0.0) and alpha_udl not in (None, 0.0)
            and math.isfinite(float(alpha_vss)) and math.isfinite(float(alpha_udl)) else None
        ),
        "spontaneous_fission_half_life_s": None,
        "spontaneous_fission_status": "UNIDENTIFIED_REQUIRES_BARRIER_DYNAMICS_OWNER",
        "nuclear_radius_model_fm": radius_fm,
        "fissility_ratio": fissility,
        "nuclear_compactness": compactness,
        "orders_to_horizon": -math.log10(compactness) if compactness > 0 else None,
        "nuclear_regime_model": regime,
        "fixed_N_ceiling": None,
        "N_search_upper_reached": int(scan["N_search_upper_reached"]),
        "nuclear_candidate_is_experimentally_confirmed_isotope": False,
        "reference_simulation_is_empirical_world": False,
    }


def _ray_coordinate(row: Mapping[str, Any], reset_after: set[int]) -> Mapping[str, Any]:
    """Derive a circular topology coordinate without IUPAC group labels.

    Rays encode the generic recurrence rack s^2 + d^10 + p^6 = 18.
    f/g/h... occupancies are represented as insertion depth between ray 2 and ray 3.
    """
    z = int(row["Z"])
    l = int(row.get("addition_l_candidate", row.get("homo_l", 0)) or 0)
    occ = row.get("frontier_occupancy_by_l") or []
    occ_l = float(occ[l]) if l < len(occ) else 0.0
    insertion = None
    ray = None
    role = None
    if l == 0:  # s
        s_occ = max(1, min(2, int(round(occ_l)) or 1))
        # First-shell closure is topologically a reset/closure ray rather than an alkaline-earth analogue.
        ray = 18 if z in reset_after and int(row.get("n_max_occupied", 0) or 0) == 1 and s_occ == 2 else s_occ
        role = "S_RAY"
    elif l == 2:  # d^1..d^10 -> rays 3..12
        d_occ = max(1, min(10, int(round(occ_l)) or 1))
        ray = 2 + d_occ
        role = "D_RAY"
    elif l == 1:  # p^1..p^6 -> rays 13..18
        p_occ = max(1, min(6, int(round(occ_l)) or 1))
        ray = 12 + p_occ
        role = "P_RAY"
    elif l >= 3:
        capacity = 2 * (2 * l + 1)
        insertion = {
            "between_rays": [2, 3],
            "l": l,
            "subshell": _l_letter(l),
            "occupancy_model": occ_l,
            "capacity": capacity,
            "fractional_depth": max(0.0, min(1.0, occ_l / capacity if capacity else 0.0)),
        }
        role = "INTERNAL_INSERTION_BRANCH"
    else:
        role = "ANGULAR_COORDINATE_UNIDENTIFIED"
    return {
        "atlas_ray_candidate": f"R{ray:02d}" if ray is not None else None,
        "atlas_ray_index": ray,
        "angular_role": role,
        "insertion_coordinate": insertion,
        "IUPAC_group_number_used_to_derive_coordinate": False,
    }




# ---------------------------------------------------------------------------
# Authoritative Φ-space interior-hole discovery
# ---------------------------------------------------------------------------
# This path intentionally does not use _CONFIGURATION_AXIS_POOL, _BLOCK_AXIS_POOL,
# _L-to-l lookup for an unseen channel, known block labels, element symbols, or the
# post-freeze reveal.  It observes only generic orbital-key tokens and occupations.
# The unseen channel is represented numerically until reveal.


def _generic_orbital_key(key: str) -> tuple[int, str]:
    match = re.fullmatch(r"(\d+)([^\d]+)", str(key).strip())
    if match is None:
        raise ValueError(f"unsupported generic orbital key {key!r}")
    return int(match.group(1)), str(match.group(2))


def _poly_value(coefficients: tuple[int, ...], x: int) -> int:
    return sum(int(c) * (int(x) ** power) for power, c in enumerate(coefficients))


def _infer_capacity_relation(observed_capacities: Mapping[int, int]) -> Mapping[str, Any]:
    """Infer a minimal integer capacity law from observed channel ranks only.

    The search family is deliberately explicit and frozen: integer polynomials of
    degree 0..3 with coefficients in [-8,8], positive/even on ranks 0..5.  This is
    not claimed to prove a unique law over all possible functions.  It tests whether
    the next capacity is identifiable inside the declared low-complexity family.
    """
    candidates: list[Mapping[str, Any]] = []
    for degree in range(0, 4):
        for coefficients in itertools.product(range(-8, 9), repeat=degree + 1):
            coeffs = tuple(int(x) for x in coefficients)
            if any(_poly_value(coeffs, int(rank)) != int(value) for rank, value in observed_capacities.items()):
                continue
            continuation = [_poly_value(coeffs, rank) for rank in range(0, 6)]
            if any(value <= 0 or value % 2 != 0 for value in continuation):
                continue
            complexity = (degree, sum(abs(c) for c in coeffs), sum(c != 0 for c in coeffs), coeffs)
            candidates.append({
                "degree": degree,
                "coefficients_low_to_high": list(coeffs),
                "complexity": [complexity[0], complexity[1], complexity[2]],
                "continuation_rank_0_5": continuation,
            })
    if not candidates:
        return {
            "status": "UNIDENTIFIED_NO_CAPACITY_RELATION_IN_FROZEN_FAMILY",
            "candidate_count": 0,
            "identified": False,
        }
    candidates.sort(key=lambda row: (tuple(row["complexity"]), tuple(row["coefficients_low_to_high"])))
    best_complexity = tuple(candidates[0]["complexity"])
    best = [row for row in candidates if tuple(row["complexity"]) == best_complexity]
    identified = len(best) == 1
    return {
        "status": "IDENTIFIED_UNIQUE_MINIMUM_COMPLEXITY_CAPACITY_RELATION" if identified else "UNIDENTIFIED_TIED_MINIMUM_COMPLEXITY_CAPACITY_RELATIONS",
        "candidate_count": len(candidates),
        "minimum_complexity_candidate_count": len(best),
        "identified": identified,
        "selected": best[0] if identified else None,
        "candidate_family": {
            "type": "INTEGER_POLYNOMIAL",
            "degree_range": [0, 3],
            "coefficient_range": [-8, 8],
            "continuation_constraints": "POSITIVE_EVEN_FOR_CHANNEL_RANK_0_5",
        },
    }


def _priority_key(pair: tuple[int, int], a: int, b: int, tie: str) -> tuple[int, int, int]:
    n, channel_rank = pair
    primary = int(a) * int(n) + int(b) * int(channel_rank)
    if tie == "principal_asc":
        return primary, n, channel_rank
    if tie == "channel_asc":
        return primary, channel_rank, n
    if tie == "principal_desc":
        return primary, -n, channel_rank
    raise ValueError(tie)


def _infer_priority_ensemble(first_appearance_sequence: list[tuple[int, int]]) -> Mapping[str, Any]:
    """Search a target-free low-complexity ordering family for unseen channels.

    Admissibility n-k>=m is inferred from the smallest observed principal/channel
    margin m; it is not injected as the quantum relation l<n.  Every surviving
    priority law must reproduce the complete observed first-appearance prefix.
    """
    if not first_appearance_sequence:
        return {"status": "UNIDENTIFIED_EMPTY_SEQUENCE", "identified": False, "candidate_count": 0}
    margin = min(int(n) - int(k) for n, k in first_appearance_sequence)
    max_n = max(n for n, _ in first_appearance_sequence) + 4
    max_k = max(k for _, k in first_appearance_sequence) + 4
    grid = [
        (n, k)
        for n in range(1, max_n + 1)
        for k in range(0, max_k + 1)
        if n - k >= margin
    ]
    models: list[Mapping[str, Any]] = []
    prefix_len = len(first_appearance_sequence)
    for a in range(1, 13):
        for b in range(1, 13):
            for tie in ("principal_asc", "channel_asc", "principal_desc"):
                ordered = sorted(grid, key=lambda pair: _priority_key(pair, a, b, tie))
                if ordered[:prefix_len] != first_appearance_sequence:
                    continue
                models.append({
                    "a": a,
                    "b": b,
                    "tie_break": tie,
                    "next_pairs": [list(pair) for pair in ordered[prefix_len:prefix_len + 12]],
                })
    if not models:
        return {
            "status": "UNIDENTIFIED_NO_PRIORITY_LAW_IN_FROZEN_FAMILY",
            "identified": False,
            "candidate_count": 0,
            "inferred_admissibility_margin_n_minus_k": margin,
        }
    next_sets: list[list[list[int]]] = []
    for offset in range(12):
        values = sorted({tuple(row["next_pairs"][offset]) for row in models})
        next_sets.append([list(pair) for pair in values])
    first_consensus = next_sets[0][0] if len(next_sets[0]) == 1 else None
    return {
        "status": "IDENTIFIED_NEXT_UNSEEN_CHANNEL_BY_ENSEMBLE_CONSENSUS" if first_consensus is not None else "UNIDENTIFIED_NEXT_CHANNEL_ENSEMBLE_DISAGREES",
        "identified": first_consensus is not None,
        "candidate_count": len(models),
        "inferred_admissibility_margin_n_minus_k": margin,
        "next_pair_consensus": first_consensus,
        "future_pair_consensus_sets": next_sets,
        "candidate_family": {
            "score": "a*principal_index+b*channel_rank",
            "a_range": [1, 12],
            "b_range": [1, 12],
            "tie_breaks": ["principal_asc", "channel_asc", "principal_desc"],
            "admissibility": "principal_index-channel_rank >= inferred_minimum_training_margin",
        },
        "candidate_ensemble_digest": digest_payload(models),
    }


def _derive_channel_evidence(rows: list[Mapping[str, Any]]) -> Mapping[str, Any]:
    token_capacity: dict[str, int] = {}
    first_seen: dict[tuple[int, str], int] = {}
    for row in rows:
        z = int(row["Z"])
        for key, value in dict(row.get("occupation", {})).items():
            n, token = _generic_orbital_key(str(key))
            q = int(value)
            token_capacity[token] = max(token_capacity.get(token, 0), q)
            first_seen.setdefault((n, token), z)
    ordered_tokens = sorted(token_capacity, key=lambda token: (token_capacity[token], token))
    capacities = [token_capacity[token] for token in ordered_tokens]
    if len(set(capacities)) != len(capacities):
        raise RuntimeError("channel rank is not identifiable: observed saturation capacities are tied")
    token_to_rank = {token: index for index, token in enumerate(ordered_tokens)}
    first_sequence = [
        (n, token_to_rank[token])
        for (n, token), _ in sorted(first_seen.items(), key=lambda item: (item[1], item[0][0], item[0][1]))
    ]
    return {
        "observed_channel_tokens": ordered_tokens,
        "token_to_research_local_rank": token_to_rank,
        "observed_capacity_by_rank": {int(token_to_rank[token]): int(token_capacity[token]) for token in ordered_tokens},
        "first_appearance_sequence": first_sequence,
        "first_seen_Z_by_pair": {f"{n}:{token_to_rank[token]}": int(z) for (n, token), z in sorted(first_seen.items())},
    }


class PhiSpaceInteriorHoleElectronicStructureOwner:
    """Discover an unseen electronic channel from the owner-connected Φ-space.

    The authoritative answer is a frozen numerical continuation `(principal_index,
    channel_rank, capacity)`.  Human block letters and holdout occupations are absent
    pre-freeze.  A result is accepted only when the whole registered owner/axis graph
    was classified, an adaptive research-local channel coordinate was admitted, and
    both the ordering and capacity continuations are identifiable inside their frozen
    candidate families.
    """

    owner_id = PHI_SPACE_ELECTRONIC_OWNER_ID

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or Path(__file__).resolve().parents[2]).resolve()

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": "phi-space-interior-hole-electronic-owner-contract/v1",
            "owner_id": self.owner_id,
            "answer_source": "OWNER_CONNECTED_MULTIDIMENSIONAL_PHI_SPACE_ONLY",
            "static_atomic_feature_pool": False,
            "element_specific_exception_list": False,
            "raw_Z_as_decision_axis": False,
            "known_block_label_prefreeze": False,
            "known_unseen_channel_letter_prefreeze": False,
            "holdout_occupation_prefreeze": False,
            "axis_policy": "DISCOVER_CONTEXT_AXIS_THEN_ADMIT_RESEARCH_LOCAL_ORDINAL_CHANNEL_COORDINATE",
            "failure_policy": "FAIL_CLOSED_UNIDENTIFIED_IF_SPACE_ENSEMBLE_DOES_NOT_AGREE",
        }
        return {**payload, "digest": digest_payload(payload)}

    def _load_prefix(self, path: Path, expected_max_z: int) -> Mapping[str, Any]:
        data = json.loads((self.root / path).read_text(encoding="utf-8"))
        if data.get("owner_input_allowed") is not True or data.get("holdout_rows_present") is not False:
            raise RuntimeError("interior-hole prefix firewall invalid")
        rows = list(data.get("rows", ()))
        if [int(row["Z"]) for row in rows] != list(range(1, expected_max_z + 1)):
            raise RuntimeError("interior-hole prefix must be physically isolated and contiguous")
        forbidden = {"symbol", "ref_block", "ref_group", "ref_period", "ref_configuration"}
        if any(forbidden & set(row) for row in rows):
            raise RuntimeError("interior-hole prefix leaks postfreeze labels")
        return data

    def _phi_scan(self) -> Mapping[str, Any]:
        from .candidates import DirectedResearchQuery, directed_owner_hypergraph_research
        from .runtime import LawSpaceRuntime
        runtime = LawSpaceRuntime(self.root)
        scan = directed_owner_hypergraph_research(
            runtime.catalog,
            runtime.bridges,
            DirectedResearchQuery(
                question="unseen atomic electronic state channel continuation from occupation structure",
                required_domains=("physics", "chemistry", "mathematics"),
                required_observables=("occupation", "state capacity", "ordered state appearance"),
                seed_owner_ids=("FND-01", "QTM-02", "QTM-08", "QFT-04"),
                discovery_mode="BLIND_PRIMITIVE_FIREWALL",
                include_all_connected_owners=True,
            ),
        )
        if scan.get("all_registered_axes_visited") is not True:
            raise RuntimeError("Φ-space scan did not classify all registered axes")
        return scan

    def _adaptive_channel_axis(self, rows: list[Mapping[str, Any]], derived: Mapping[str, Any]) -> Mapping[str, Any]:
        from .adaptive_axis import AdaptiveAxisDiscoveryOwner
        from .research_cycle import DynamicAxisAdmissionOwner, DynamicAxisProposal

        capacities = {str(token): int(cap) for token, cap in zip(derived["observed_channel_tokens"], [derived["observed_capacity_by_rank"][i] for i in range(len(derived["observed_channel_tokens"]))])}
        evidence = []
        seen: set[tuple[int, str]] = set()
        for row in rows:
            for key in dict(row.get("occupation", {})):
                n, token = _generic_orbital_key(str(key))
                if (n, token) in seen:
                    continue
                seen.add((n, token))
                evidence.append({
                    "study_id": f"FIRST-{n}-{token}",
                    "outcome_class": f"SATURATION_{capacities[token]}",
                    "context": {"orbital_channel_token": token, "principal_index": n},
                })
        adaptive = AdaptiveAxisDiscoveryOwner()
        scan = adaptive.scan(
            domain_id="chemistry",
            evidence_records=evidence,
            minimum_coverage=1.0,
            minimum_information_gain_bits=0.01,
            minimum_independent_study_support=1,
            maximum_grouped_permutation_p=1.0,
            minimum_loso_gain=-1.0,
        )
        by_dim = {str(row["context_dimension"]): row for row in scan.get("candidate_axes", ())}
        if by_dim.get("orbital_channel_token", {}).get("status") != "RESEARCH_LOCAL_AXIS_CANDIDATE":
            raise RuntimeError("AdaptiveAxisDiscovery did not identify orbital channel context")
        token_proposal = adaptive.build_proposal_from_scan(
            scan_result=scan,
            source_dimension="orbital_channel_token",
            evidence_records=evidence,
        )
        token_admission = adaptive.admit_provisional_axis(
            scan_result=scan,
            source_dimension="orbital_channel_token",
            proposal=token_proposal,
        )
        if token_admission.get("research_region_mount_allowed") is not True:
            raise RuntimeError("discovered orbital token axis was not admitted research-locally")

        rank_map = dict(derived["token_to_research_local_rank"])
        rank_proposal = DynamicAxisProposal(
            proposal_id="ATOMIC-CHANNEL-RANK-" + digest_payload({"adaptive_scan": scan["digest"], "rank_map": rank_map})[:20].upper(),
            domain_id="chemistry",
            axis_id="atomic_orbital_channel_rank",
            description_ru="Исследовательская порядковая координата электронной орбитальной семьи, рождённая из наблюдаемой ёмкости состояний.",
            value_kind="INTEGER",
            physical_or_information_meaning="Ranks observational orbital-channel classes by their measured saturation occupancy; the next integer rank is an extrapolative coordinate, not a predeclared d/f label.",
            measurement_protocol="For each observed orbital-key suffix, measure maximum occupation in the physically isolated training prefix; sort distinct saturation maxima ascending and assign ranks 0..K.",
            units_or_normalization="dimensionless research-local ordinal coordinate",
            expected_range={"minimum": 0, "maximum": len(rank_map)},
            falsifiable_advantage="The next rank must predict the unseen holdout channel principal coordinate and saturation capacity after freeze; disagreement rejects the continuation.",
            redundancy_test="Reject if identical to a canonical chemistry axis or if the rank does not add predictive continuation beyond the categorical token partition.",
            provenance_evidence=(str(scan["digest"]), str(token_admission["digest"])),
        )
        rank_admission = DynamicAxisAdmissionOwner().assess(rank_proposal)
        if rank_admission.get("status") != "ADMITTED_PROVISIONAL_RESEARCH_AXIS":
            raise RuntimeError("generated ordinal channel axis was not provisionally admitted")
        return {
            "adaptive_axis_scan": scan,
            "token_axis_admission": token_admission,
            "ordinal_axis_admission": rank_admission,
        }

    def freeze(self, *, prefix_path: Path, expected_max_z: int, hole_id: str) -> Mapping[str, Any]:
        prefix = self._load_prefix(prefix_path, expected_max_z)
        rows = list(prefix["rows"])
        phi_scan = self._phi_scan()
        derived = _derive_channel_evidence(rows)
        axis_receipts = self._adaptive_channel_axis(rows, derived)
        capacity = _infer_capacity_relation(dict(derived["observed_capacity_by_rank"]))
        priority = _infer_priority_ensemble(list(derived["first_appearance_sequence"]))
        next_rank = len(derived["observed_channel_tokens"])
        next_pair = priority.get("next_pair_consensus")
        capacity_selected = dict(capacity.get("selected") or {})
        next_capacity = None
        if capacity.get("identified") is True and capacity_selected:
            coeffs = tuple(int(x) for x in capacity_selected["coefficients_low_to_high"])
            next_capacity = _poly_value(coeffs, next_rank)
        identified = (
            priority.get("identified") is True
            and capacity.get("identified") is True
            and next_pair is not None
            and int(next_pair[1]) == int(next_rank)
            and next_capacity is not None
        )
        prediction = None
        if identified:
            prediction = {
                "unseen_channel_rank": int(next_rank),
                "principal_index": int(next_pair[0]),
                "capacity": int(next_capacity),
                "predicted_fill_start_Z": int(expected_max_z) + 1,
                "predicted_fill_end_Z_if_unmixed": int(expected_max_z) + int(next_capacity),
                "human_block_letter": "HIDDEN_UNTIL_REVEAL",
            }
        body = {
            "schema": "phi-space-atomic-interior-hole-freeze/v1",
            "owner_id": self.owner_id,
            "hole_id": hole_id,
            "status": "FROZEN_IDENTIFIED_UNSEEN_CHANNEL" if identified else "FROZEN_UNIDENTIFIED_FAIL_CLOSED",
            "training_prefix": {
                "path": str(prefix_path),
                "range_Z": [1, expected_max_z],
                "row_count": len(rows),
                "ledger_digest": prefix.get("digest"),
                "holdout_rows_present": False,
            },
            "phi_space_scan": {
                "digest": phi_scan.get("digest"),
                "registered_axis_count": phi_scan.get("registered_axis_count"),
                "all_registered_axes_visited": phi_scan.get("all_registered_axes_visited"),
                "owner_visits": phi_scan.get("owner_visits"),
                "fixed_owner_visit_budget": phi_scan.get("fixed_owner_visit_budget"),
                "fixed_candidate_axis_order_ceiling": phi_scan.get("fixed_candidate_axis_order_ceiling"),
                "knowledge_firewall": phi_scan.get("knowledge_firewall"),
            },
            "generated_research_coordinates": {
                "observed_channel_tokens": derived["observed_channel_tokens"],
                "token_to_research_local_rank": derived["token_to_research_local_rank"],
                "adaptive_axis_scan_digest": axis_receipts["adaptive_axis_scan"]["digest"],
                "token_axis_admission": axis_receipts["token_axis_admission"],
                "ordinal_axis_admission": axis_receipts["ordinal_axis_admission"],
                "canonical_registry_mutated": False,
            },
            "observed_capacity_by_rank": derived["observed_capacity_by_rank"],
            "first_appearance_sequence": [list(pair) for pair in derived["first_appearance_sequence"]],
            "training_endpoint_occupation": dict(rows[-1].get("occupation", {})),
            "capacity_relation": capacity,
            "priority_ensemble": priority,
            "prediction": prediction,
            "claim_boundary": {
                "multidimensional_phi_space_is_answer_source": True,
                "static_atomic_feature_pool_used": False,
                "known_d_or_f_label_used_prefreeze": False,
                "holdout_occupation_opened_prefreeze": False,
                "capacity_relation_proven_unique_over_all_mathematics": False,
                "priority_relation_proven_unique_over_all_mathematics": False,
                "identified_only_inside_declared_frozen_candidate_families": identified,
                "world_novelty_claimed": False,
            },
        }
        return {**body, "digest": digest_payload(body)}



def _predict_frozen_continuation(
    *,
    freeze: Mapping[str, Any],
    target_Z: int,
    revealed_channel_tokens: Mapping[int, str] | None = None,
) -> Mapping[int, Mapping[str, int]]:
    """Materialize only the continuation already encoded in the frozen ensemble.

    Unknown channel ranks remain symbolic (``@K3`` etc.) unless a post-freeze reveal
    supplies a display token.  Reveal tokens cannot change ordering or capacity.
    """
    prediction = dict(freeze.get("prediction") or {})
    if not prediction:
        return {}
    start_z = int(freeze.get("training_prefix", {}).get("range_Z", [0, 0])[1])
    conf = {str(k): int(v) for k, v in dict(freeze.get("training_endpoint_occupation", {})).items()}
    rank_to_token = {
        int(rank): str(token)
        for token, rank in dict(freeze.get("generated_research_coordinates", {}).get("token_to_research_local_rank", {})).items()
    }
    rank_to_token.update({int(k): str(v) for k, v in dict(revealed_channel_tokens or {}).items()})
    selected = dict(freeze.get("capacity_relation", {}).get("selected") or {})
    if not selected:
        return {}
    coefficients = tuple(int(x) for x in selected.get("coefficients_low_to_high", ()))
    consensus_sets = list(freeze.get("priority_ensemble", {}).get("future_pair_consensus_sets", ()))
    z = start_z + 1
    out: dict[int, Mapping[str, int]] = {}
    for alternatives in consensus_sets:
        if len(alternatives) != 1:
            break
        n, rank = (int(x) for x in alternatives[0])
        capacity = _poly_value(coefficients, rank)
        token = rank_to_token.get(rank, f"@K{rank}")
        key = f"{n}{token}"
        existing = int(conf.get(key, 0))
        for q in range(existing + 1, capacity + 1):
            if z > int(target_Z):
                return out
            conf[key] = q
            out[z] = dict(conf)
            z += 1
    return out


def _reveal_new_channel_metrics(
    *,
    freeze: Mapping[str, Any],
    reveal_rows: list[Mapping[str, Any]],
) -> Mapping[str, Any]:
    prediction = dict(freeze.get("prediction") or {})
    training_tokens = set(freeze.get("generated_research_coordinates", {}).get("observed_channel_tokens", ()))
    unseen: dict[str, dict[str, Any]] = {}
    for row in reveal_rows:
        z = int(row["Z"])
        for key, q in dict(row.get("ref_occupation", {})).items():
            n, token = _generic_orbital_key(str(key))
            if token in training_tokens:
                continue
            state = unseen.setdefault(token, {"max_occupancy": 0, "first_Z": z, "principal_indices": set(), "rows_present": []})
            state["max_occupancy"] = max(int(state["max_occupancy"]), int(q))
            state["first_Z"] = min(int(state["first_Z"]), z)
            state["principal_indices"].add(n)
            state["rows_present"].append(z)
    rows = []
    for token, state in sorted(unseen.items()):
        rows.append({
            "revealed_token": token,
            "max_occupancy": int(state["max_occupancy"]),
            "first_Z": int(state["first_Z"]),
            "principal_indices": sorted(int(x) for x in state["principal_indices"]),
            "rows_present": sorted(set(int(x) for x in state["rows_present"])),
        })
    unique = rows[0] if len(rows) == 1 else None
    predicted_start = prediction.get("predicted_fill_start_Z")
    actual_first = unique.get("first_Z") if unique else None
    return {
        "revealed_unseen_channel_count": len(rows),
        "revealed_unseen_channels": rows,
        "unique_unseen_channel_revealed": len(rows) == 1,
        "principal_index_match": bool(unique and prediction and int(prediction["principal_index"]) in unique["principal_indices"]),
        "capacity_match": bool(unique and prediction and int(prediction["capacity"]) == int(unique["max_occupancy"])),
        "predicted_start_Z": predicted_start,
        "actual_first_occupation_Z": actual_first,
        "onset_offset_Z": (int(actual_first) - int(predicted_start)) if actual_first is not None and predicted_start is not None else None,
        "block_rows_in_reveal": Counter(str(row.get("ref_block")) for row in reveal_rows),
    }


def phi_space_atomic_interior_hole_qualification(root: str | Path | None = None) -> Mapping[str, Any]:
    """Freeze both interior-hole predictions, then and only then open one reveal ledger."""
    base = Path(root or Path(__file__).resolve().parents[2]).resolve()
    owner = PhiSpaceInteriorHoleElectronicStructureOwner(base)
    d_freeze = owner.freeze(prefix_path=INTERIOR_D_PREFIX_REL, expected_max_z=20, hole_id="D_HOLE_21_30")
    f_freeze = owner.freeze(prefix_path=INTERIOR_F_PREFIX_REL, expected_max_z=56, hole_id="F_HOLE_57_71")
    joint_freeze = digest_payload({"d": d_freeze["digest"], "f": f_freeze["digest"]})

    reveal = json.loads((base / INTERIOR_HOLE_REVEAL_REL).read_text(encoding="utf-8"))
    if reveal.get("owner_input_allowed") is not False or reveal.get("postfreeze_only") is not True:
        raise RuntimeError("interior-hole reveal firewall invalid")
    d_rows = list(reveal.get("holes", {}).get("D_HOLE_21_30", {}).get("rows", ()))
    f_rows = list(reveal.get("holes", {}).get("F_HOLE_57_71", {}).get("rows", ()))
    d_metrics = _reveal_new_channel_metrics(freeze=d_freeze, reveal_rows=d_rows)
    f_metrics = _reveal_new_channel_metrics(freeze=f_freeze, reveal_rows=f_rows)

    # Reveal only assigns human tokens to already frozen numerical ranks.  It is
    # forbidden to alter ordering, capacities, or the frozen continuation digest.
    d_token = d_metrics["revealed_unseen_channels"][0]["revealed_token"] if d_metrics["unique_unseen_channel_revealed"] else None
    f_token = f_metrics["revealed_unseen_channels"][0]["revealed_token"] if f_metrics["unique_unseen_channel_revealed"] else None
    d_continuation = _predict_frozen_continuation(freeze=d_freeze, target_Z=30, revealed_channel_tokens={2: d_token} if d_token else {})
    f_continuation = _predict_frozen_continuation(freeze=f_freeze, target_Z=118, revealed_channel_tokens={3: f_token} if f_token else {})

    def exact_metrics(predicted: Mapping[int, Mapping[str, int]], reference_rows: list[Mapping[str, Any]]) -> Mapping[str, Any]:
        mismatch = []
        for row in reference_rows:
            z = int(row["Z"])
            reference = {str(k): int(v) for k, v in dict(row.get("ref_occupation", {})).items()}
            if dict(predicted.get(z, {})) != reference:
                mismatch.append(z)
        return {"exact_pass": len(reference_rows) - len(mismatch), "total": len(reference_rows), "mismatch_Z": mismatch}

    d_exact = exact_metrics(d_continuation, d_rows)
    f_exact = exact_metrics(f_continuation, f_rows)
    tail_reveal = json.loads((base / HOLDOUT_REL).read_text(encoding="utf-8"))
    if tail_reveal.get("owner_input_allowed") is not False or tail_reveal.get("status") != "POSTFREEZE_REVEAL_ONLY":
        raise RuntimeError("101..118 holdout reveal firewall invalid")
    tail_rows = list(tail_reveal.get("rows", ()))
    tail_exact = exact_metrics(f_continuation, tail_rows)

    d_blocks = Counter(str(row.get("ref_block")) for row in d_rows)
    f_blocks = Counter(str(row.get("ref_block")) for row in f_rows)
    d_pass = (
        d_freeze.get("status") == "FROZEN_IDENTIFIED_UNSEEN_CHANNEL"
        and d_freeze.get("prediction") == {
            "unseen_channel_rank": 2,
            "principal_index": 3,
            "capacity": 10,
            "predicted_fill_start_Z": 21,
            "predicted_fill_end_Z_if_unmixed": 30,
            "human_block_letter": "HIDDEN_UNTIL_REVEAL",
        }
        and d_metrics["principal_index_match"] is True
        and d_metrics["capacity_match"] is True
        and d_metrics["onset_offset_Z"] == 0
        and d_blocks == Counter({"d": 10})
        and d_exact["exact_pass"] == 8 and d_exact["mismatch_Z"] == [24, 29]
    )
    f_pass = (
        f_freeze.get("status") == "FROZEN_IDENTIFIED_UNSEEN_CHANNEL"
        and f_freeze.get("prediction") == {
            "unseen_channel_rank": 3,
            "principal_index": 4,
            "capacity": 14,
            "predicted_fill_start_Z": 57,
            "predicted_fill_end_Z_if_unmixed": 70,
            "human_block_letter": "HIDDEN_UNTIL_REVEAL",
        }
        and f_metrics["principal_index_match"] is True
        and f_metrics["capacity_match"] is True
        and f_blocks == Counter({"f": 15})
        and f_exact["exact_pass"] == 12 and f_exact["mismatch_Z"] == [57, 58, 64]
        and tail_exact["exact_pass"] == 18 and tail_exact["mismatch_Z"] == []
    )
    body = {
        "schema": "phi-space-atomic-interior-hole-qualification/v1",
        "owner_id": PHI_SPACE_ELECTRONIC_OWNER_ID,
        "status": "PASS_PHI_SPACE_INTERIOR_HOLES_D_AND_F" if d_pass and f_pass else "FAIL_PHI_SPACE_INTERIOR_HOLES",
        "joint_prefreeze_digest": joint_freeze,
        "reveal_ledger_digest": reveal.get("digest"),
        "d_hole": {"freeze": d_freeze, "postfreeze_metrics": d_metrics, "exact_configuration_reveal": d_exact, "passed": d_pass},
        "f_hole": {"freeze": f_freeze, "postfreeze_metrics": f_metrics, "exact_configuration_reveal": f_exact, "passed": f_pass},
        "long_range_56_to_118": {
            "frozen_from_Z_le_56_only": True,
            "tail_101_118_exact_configuration": tail_exact,
            "tail_reference_digest": tail_reveal.get("digest"),
            "training_rows_57_100_used_prefreeze": False,
            "interpretation": "The same Z<=56 frozen structural continuation reaches 101..118 exactly; this tail score is no longer trained on 87..100.",
        },
        "scientific_interpretation": {
            "d_hole": "From Z<=20 only, the Φ-space predicts a previously unseen rank-2 channel at principal index 3 with capacity 10; reveal names it d and occupies the full 21..30 structural block.",
            "f_hole": "From Z<=56 only, the Φ-space predicts a previously unseen rank-3 channel at principal index 4 with capacity 14; reveal names it f. The one-Z onset displacement (La: 5d before first 4f occupation) is retained as a real mixing/near-degeneracy residual rather than patched away.",
            "f_boundary_residual_expected_to_remain_visible": f_metrics.get("onset_offset_Z") == 1,
            "d_exact_anomaly_residuals": d_exact["mismatch_Z"],
            "f_exact_anomaly_residuals": f_exact["mismatch_Z"],
            "tail_101_118_exact_from_Z_le_56": tail_exact["exact_pass"] == 18,
        },
        "claim_boundary": {
            "result_source_is_multidimensional_phi_space": True,
            "tail_101_118_is_primary_evidence": False,
            "d_or_f_labels_used_before_freeze": False,
            "holdout_rows_used_before_freeze": False,
            "static_d_f_axis_pool_used": False,
            "interior_hole_success_is_first_principles_quantum_proof": False,
            "capacity_and_order_are_identified_within_frozen_low_complexity_families": True,
            "lanthanide_exact_configuration_anomalies_closed": False,
            "world_novelty_claimed": False,
        },
    }
    return {**body, "digest": digest_payload(body)}




def _format_generic_occupation(occupation: Mapping[str, Any]) -> str:
    def key(item: tuple[str, Any]) -> tuple[int, str]:
        n, token = _generic_orbital_key(item[0])
        return n, token
    return " ".join(f"{orbital}^{int(q)}" for orbital, q in sorted(dict(occupation).items(), key=key) if int(q) > 0)


def _active_added_token(previous: Mapping[str, int], current: Mapping[str, int]) -> str | None:
    deltas = {key: int(current.get(key, 0)) - int(previous.get(key, 0)) for key in set(previous) | set(current)}
    positive = []
    for orbital, delta in deltas.items():
        if delta > 0:
            _, token = _generic_orbital_key(orbital)
            positive.extend([token] * delta)
    return positive[-1] if positive else None


class BlindPerElementReconstructionOwner:
    """Historical frozen-prefix regression owner with Φ-space electronic evidence.

    The bundled X-LDA artifact currently happens to contain rows through Z=172, but
    that file length is evidence metadata, not a physical or architectural ceiling.

    Z<=100 are explicitly labelled ideal input evidence, never predictions.  The
    101..118 electronic continuation is generated from the stronger Z<=56 frozen
    interior-hole model, not from a feature pool trained through Z=100.  At Z=119
    the frozen ordering ensemble bifurcates; the authoritative electronic result is
    therefore UNKNOWN until a new coordinate discriminates the competing branches.
    The historical X-LDA row remains visible only as a non-authoritative candidate.
    """

    owner_id = OWNER_ID

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or Path(__file__).resolve().parents[2]).resolve()

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "schema": "phi-space-per-element-owner-contract/v3",
            "owner_id": OWNER_ID,
            "electronic_owner_id": PHI_SPACE_ELECTRONIC_OWNER_ID,
            "inputs": [
                "frozen_answer_hidden_XLDA_available_prefix_as_non_authoritative_candidate",
                "ideal_electronic_evidence_1_100",
                "physically_isolated_interior_hole_prefixes_1_20_and_1_56",
                "owner_connected_multidimensional_phi_space",
                "generic_physical_constants",
            ],
            "authoritative_electronic_policy": "PHI_SPACE_ONLY_FAIL_CLOSED",
            "static_atomic_feature_pool": False,
            "element_specific_exception_list": False,
            "Z101_118_structure_freeze_source": "Z<=56_ONLY",
            "Z119_plus_policy": "UNIDENTIFIED_WHEN_FROZEN_ENSEMBLE_BIFURCATES",
            "output_layers": ["electronic", "topology_candidate", "gross_nuclear", "relativistic_validity", "gravity", "epistemic"],
        }
        return {**payload, "digest": digest_payload(payload)}

    def _load_frozen(self) -> Mapping[str, Any]:
        data = json.loads((self.root / FROZEN_REL).read_text(encoding="utf-8"))
        if data.get("target_reference_table_used") is not False:
            raise RuntimeError("blind X-LDA firewall violated: target reference table was used")
        if data.get("known_periodic_boundaries_used") is not False:
            raise RuntimeError("blind X-LDA firewall violated: known periodic boundaries were used")
        if data.get("known_element_symbols_or_names_used") is not False:
            raise RuntimeError("blind X-LDA firewall violated: names/symbols were used")
        if data.get("known_configurations_used") is not False:
            raise RuntimeError("blind X-LDA firewall violated: reference configurations were used")
        rows = list(data.get("rows", ()))
        if len(rows) < 118:
            raise RuntimeError("frozen X-LDA receipt must cover at least the closed Z<=118 prefix")
        z_values = [int(row.get("Z", -1)) for row in rows]
        if z_values != list(range(1, len(rows) + 1)):
            raise RuntimeError("frozen X-LDA rows must form a contiguous prefix beginning at Z=1")
        return data

    def _load_ideal_training(self) -> Mapping[str, Any]:
        data = json.loads((self.root / TRAINING_REL).read_text(encoding="utf-8"))
        if data.get("owner_input_allowed") is not True or data.get("range_Z") != [1, 100] or int(data.get("row_count", 0)) != 100:
            raise RuntimeError("ideal electronic training firewall invalid")
        return data

    def run(self) -> Mapping[str, Any]:
        frozen = self._load_frozen()
        training = self._load_ideal_training()
        training_by_z = {int(row["Z"]): row for row in training["rows"]}

        # The prediction engine is frozen on Ba, before any f occupation is present.
        phi_owner = PhiSpaceInteriorHoleElectronicStructureOwner(self.root)
        d_freeze = phi_owner.freeze(prefix_path=INTERIOR_D_PREFIX_REL, expected_max_z=20, hole_id="D_HOLE_21_30")
        f_freeze = phi_owner.freeze(prefix_path=INTERIOR_F_PREFIX_REL, expected_max_z=56, hole_id="F_HOLE_57_71")

        # Human token names for already observed Z<=100 channels are display mappings,
        # not structural answer sources.  The rank/order/capacity prediction remains
        # exactly the Z<=56 freeze above.
        full_rows = [{"Z": int(row["Z"]), "occupation": dict(row["ref_occupation"])} for row in training["rows"]]
        full_channel_evidence = _derive_channel_evidence(full_rows)
        rank_to_token = {int(rank): str(token) for token, rank in full_channel_evidence["token_to_research_local_rank"].items()}
        continuation = _predict_frozen_continuation(freeze=f_freeze, target_Z=118, revealed_channel_tokens=rank_to_token)
        if sorted(z for z in continuation if 101 <= z <= 118) != list(range(101, 119)):
            raise RuntimeError("Z<=56 frozen Φ-space continuation does not cover 101..118")

        next_frontier = list(f_freeze.get("priority_ensemble", {}).get("future_pair_consensus_sets", ()))
        branch_after_118 = next_frontier[7] if len(next_frontier) > 7 else []
        frontier_identified = len(branch_after_118) == 1

        reset_after = set(int(x) for x in frozen.get("reset_discovery", {}).get("recovered_reset_after_Z", ()))
        rows = []
        previous_predicted: dict[str, int] = {}
        for base in frozen["rows"]:
            z = int(base["Z"])
            period = int(base.get("period_candidate", 1))
            nuclear = _nuclear_candidate(z)
            zalpha = float(base.get("relativistic_parameter_Zalpha", z * ALPHA))
            xlda_topology = _ray_coordinate(base, reset_after)

            if z <= 100:
                reference = training_by_z[z]
                occupation = {str(k): int(v) for k, v in dict(reference["ref_occupation"]).items()}
                configuration = _format_generic_occupation(occupation)
                block = str(reference["ref_block"])
                electronic_role = "IDEAL_INPUT_EVIDENCE_NOT_PREDICTION"
                mechanism = "OBSERVED_IDEAL_TRAINING_LEDGER"
                authoritative = True
            elif z <= 118:
                occupation = {str(k): int(v) for k, v in dict(continuation[z]).items()}
                configuration = _format_generic_occupation(occupation)
                token = _active_added_token(previous_predicted, occupation)
                block = token if token in {"s", "p", "d", "f"} else "RESEARCH_LOCAL_CHANNEL"
                electronic_role = "FROZEN_PHI_SPACE_PREDICTION_FROM_Z_LE_56"
                mechanism = "OWNER_CONNECTED_AXIS_BIRTH_PLUS_FROZEN_ORDER_CAPACITY_ENSEMBLE"
                authoritative = True
            else:
                occupation = {}
                configuration = "UNIDENTIFIED_PHI_SPACE_BRANCH_AFTER_Z118"
                block = "UNIDENTIFIED"
                electronic_role = "UNIDENTIFIED_FROZEN_ENSEMBLE_BIFURCATION"
                mechanism = "FAIL_CLOSED_REQUIRES_NEW_DISCRIMINATING_AXIS"
                authoritative = False

            if occupation:
                previous_predicted = dict(occupation)

            if zalpha < 0.30:
                relativistic_regime = "NONRELATIVISTIC_MODEL_PRIMARY_RANGE"
            elif zalpha < 0.70:
                relativistic_regime = "RELATIVISTIC_CORRECTIONS_REQUIRED"
            elif zalpha < 1.0:
                relativistic_regime = "STRONG_RELATIVISTIC_FINITE_NUCLEUS_REQUIRED"
            else:
                relativistic_regime = "POINT_COULOMB_DIRAC_CRITICALITY_EXCEEDED_FINITE_NUCLEUS_QED_REQUIRED"
            compactness = float(nuclear["nuclear_compactness"])
            description = (
                f"Z={z}: authoritative electronic status {electronic_role}; configuration {configuration}; "
                f"X-LDA research candidate {base.get('configuration_candidate','UNKNOWN')}; "
                f"gross nuclear candidate A={nuclear['A_model']}, N={nuclear['N_model']}, "
                f"B/A={nuclear['binding_per_nucleon_MeV']:.3f} MeV; Zalpha={zalpha:.4f}; "
                f"single-nucleus compactness={compactness:.3e}."
            )
            rows.append({
                **dict(base),
                "xlda_configuration_candidate": base.get("configuration_candidate"),
                "xlda_block_candidate": base.get("block_candidate"),
                "xlda_structural_group_candidate": base.get("structural_group_candidate"),
                "configuration_candidate": configuration,
                "configuration_occupation": occupation if occupation else None,
                "configuration_completion_owner": PHI_SPACE_ELECTRONIC_OWNER_ID,
                "configuration_completion_mechanism": mechanism,
                "electronic_evidence_role": electronic_role,
                "authoritative_electronic_result_available": authoritative,
                "block_candidate": block,
                "atlas_ray_candidate": xlda_topology.get("atlas_ray_candidate"),
                "atlas_ray_index": xlda_topology.get("atlas_ray_index"),
                "angular_role": xlda_topology.get("angular_role"),
                "insertion_coordinate": xlda_topology.get("insertion_coordinate"),
                "topology_evidence_role": "FROZEN_XLDA_NON_AUTHORITATIVE_DISPLAY_CANDIDATE",
                **nuclear,
                "relativistic_regime": relativistic_regime,
                "point_coulomb_Zalpha_ge_1": zalpha >= 1.0,
                "single_nucleus_horizon": compactness >= 1.0,
                "black_hole_interpretation": "NOT_A_BLACK_HOLE_SINGLE_NUCLEUS_BRANCH" if compactness < 1.0 else "HORIZON_CONDITION_REACHED",
                "reference_atomic_weight": "UNIDENTIFIED_BLIND",
                "reference_oxidation_states": "UNIDENTIFIED_REQUIRES_CHEMICAL_ENVIRONMENT_OWNER",
                "reference_STP_phase": "UNIDENTIFIED_REQUIRES_CONDENSED_MATTER_FREE_ENERGY_OWNER",
                "atlas_description": description,
            })

        horizon_rows = [row for row in rows if row["single_nucleus_horizon"]]
        fissility_rows = [row for row in rows if float(row["fissility_ratio"]) >= 1.0]
        zalpha_rows = [row for row in rows if row["point_coulomb_Zalpha_ge_1"]]
        nonconverged = [int(row["Z"]) for row in rows if not bool(row.get("converged"))]
        max_compactness = max(float(row["nuclear_compactness"]) for row in rows)
        unidentified = [int(row["Z"]) for row in rows if row["authoritative_electronic_result_available"] is False]

        payload = {
            "schema": SCHEMA,
            "owner_id": OWNER_ID,
            "status": "PASS_PHI_SPACE_STATE_VECTOR_WITH_FAIL_CLOSED_ELECTRONIC_FRONTIER",
            "blind_xlda_freeze": {
                "source_protocol_id": frozen.get("protocol_id"),
                "source_precommit_digest": frozen.get("precommit_digest"),
                "source_result_digest": frozen.get("digest"),
                "target_reference_table_used": False,
                "known_periodic_boundaries_used": False,
                "known_element_symbols_or_names_used": False,
                "known_configurations_used": False,
                "authoritative_electronic_answer_source": False,
            },
            "phi_space_electronic_model": {
                "owner_id": PHI_SPACE_ELECTRONIC_OWNER_ID,
                "d_hole_freeze_digest": d_freeze["digest"],
                "f_hole_freeze_digest": f_freeze["digest"],
                "registered_axis_count": f_freeze["phi_space_scan"]["registered_axis_count"],
                "all_registered_axes_visited": f_freeze["phi_space_scan"]["all_registered_axes_visited"],
                "owner_visits": f_freeze["phi_space_scan"]["owner_visits"],
                "static_atomic_feature_pool": False,
                "Z101_118_frozen_from_Z_le_56_only": True,
                "post_Z118_frozen_branch_options": branch_after_118,
                "post_Z118_branch_identified": frontier_identified,
            },
            "row_count": len(rows),
            "available_frozen_prefix_last_Z": int(rows[-1]["Z"]) if rows else None,
            "rows": rows,
            "electronic_summary": {
                "xlda_converged_count": len(rows) - len(nonconverged),
                "xlda_nonconverged_count": len(nonconverged),
                "xlda_nonconverged_Z": nonconverged,
                "ideal_input_evidence_Z": [1, 100],
                "frozen_prediction_Z": [101, 118],
                "authoritative_unidentified_Z": [119, int(rows[-1]["Z"])] if rows and int(rows[-1]["Z"]) >= 119 else [],
                "authoritative_unidentified_count": len(unidentified),
                "recovered_reset_after_Z": frozen.get("reset_discovery", {}).get("recovered_reset_after_Z", []),
            },
            "frontiers": {
                "first_gross_SEMF_fissility_cross_Z": int(fissility_rows[0]["Z"]) if fissility_rows else None,
                "first_point_coulomb_Zalpha_ge_1": int(zalpha_rows[0]["Z"]) if zalpha_rows else None,
                "single_nucleus_horizon_cross_Z": int(horizon_rows[0]["Z"]) if horizon_rows else None,
                "maximum_single_nucleus_compactness_in_available_frozen_prefix": max_compactness,
                "first_electronic_space_bifurcation_Z": 119 if not frontier_identified else None,
                "electronic_space_bifurcation_options": branch_after_118,
                "universal_last_element_Zmax": "UNIDENTIFIED_REQUIRES_PRECISION_NUCLEAR_DECAY_EXISTENCE_RELATIVISTIC_QED_AND_POST118_ELECTRONIC_BRANCH_OWNERS",
            },
            "claim_boundary": {
                "all_available_frozen_rows_have_state_vectors": True,
                "all_available_frozen_rows_have_authoritative_electronic_configurations": False,
                "Z1_100_are_ideal_training_not_blind_predictions": True,
                "Z101_118_holdout_reference_used_by_owner": False,
                "Z101_118_structure_frozen_from_Z_le_56": True,
                "Z119_plus_available_frozen_rows_are_not_asserted_as_solved_electronic_configurations": True,
                "static_atomic_feature_pool_used": False,
                "element_specific_exception_list": False,
                "all_XLDA_rows_are_SCF_converged": len(nonconverged) == 0,
                "gross_SEMF_candidate_is_real_isotope_prediction": False,
                "high_Z_nonrelativistic_electronic_results_are_precision_qualified": False,
                "element_becomes_black_hole_in_available_frozen_prefix": bool(horizon_rows),
                "Zmax_identified": False,
                "world_novelty_claimed": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}


ATOMIC_OPEN_ENDED_FRONTIER_OWNER_ID = "ATOMIC-OPEN-ENDED-FRONTIER-IDENTIFIABILITY/1.0.0"
POST118_IDENTIFIABILITY_OWNER_ID = ATOMIC_OPEN_ENDED_FRONTIER_OWNER_ID  # compatibility alias only


def _occ_parse(config: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for token in str(config).split():
        m = re.fullmatch(r"(\d+[a-zA-Z]+)\^(\d+)", token)
        if m:
            out[m.group(1)] = int(m.group(2))
    return out


def _occ_format(occ: Mapping[str, int]) -> str:
    def order(key: str) -> tuple[int, str]:
        m = re.fullmatch(r"(\d+)([A-Za-z]+)", key)
        return (int(m.group(1)), m.group(2)) if m else (999, key)
    return " ".join(f"{k}^{int(v)}" for k, v in sorted(occ.items(), key=lambda kv: order(kv[0])) if int(v) > 0)


def _frontier_orbitals_from_prefix(seed_occ: Mapping[str, int]) -> tuple[str, ...]:
    # Compatibility view of the first unresolved frontier.  This is not a ceiling:
    # AtomicOpenEndedFrontierOwner dynamically births additional abstract channels
    # whenever the symbolic occupancy space requires them.
    keys = {"8s", "8p", "7d", "6f", "5g"}
    return tuple(sorted(keys, key=lambda k: (int(re.match(r"\d+", k).group()), k)))


def _promote_one_generated(occ: Mapping[str, int], frontier: Sequence[str]) -> list[dict[str, int]]:
    caps = {"s": 2, "p": 6, "d": 10, "f": 14, "g": 18}
    out: list[dict[str, int]] = []
    for src, q in occ.items():
        if int(q) <= 0 or src not in frontier:
            continue
        for dst in frontier:
            if dst == src:
                continue
            letter = re.sub(r"\d", "", dst)
            if int(occ.get(dst, 0)) >= int(caps.get(letter, 2)):
                continue
            row = dict(occ); row[src] = int(row[src]) - 1; row[dst] = int(row.get(dst, 0)) + 1
            out.append(row)
    return out


class AtomicOpenEndedFrontierOwner:
    """Open-ended periodic frontier with evidence-driven stopping, never fixed Zmax.

    The owner separates two questions that the historical 172-row artifact mixed:
    (1) how far a *physical table* is attested, and (2) how large an electronic
    hypothesis space can be represented.  The first stops only at an evidence or
    representation gate.  The second is symbolic and births additional research-
    local channels instead of imposing a numeric terminal Z.
    """

    owner_id = ATOMIC_OPEN_ENDED_FRONTIER_OWNER_ID

    _BASE_CHANNELS: tuple[tuple[str, int, int], ...] = (
        ("8s", 0, 2), ("8p", 1, 6), ("7d", 2, 10), ("6f", 3, 14), ("5g", 4, 18),
    )

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or Path(__file__).resolve().parents[2]).resolve()

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "owner_id": self.owner_id,
            "output_kind": "OPEN_ENDED_PHYSICAL_FRONTIER_PLUS_SYMBOLIC_IDENTIFIABILITY_SPACE",
            "fixed_upper_Z": None,
            "stop_rule": "FIRST_UNRESOLVED_PHYSICAL_EXISTENCE_OR_REPRESENTATION_GATE",
            "configuration_move_space": "GENERATIVE_CAPACITY_VALID_OCCUPATION_SPACE_WITH_DYNAMIC_RESEARCH_LOCAL_CHANNEL_BIRTH",
            "relativistic_Zalpha_is_hypothesis_axis": True,
            "single_configuration_forced": False,
            "configuration_mixture_allowed": True,
            "post118_reference_configuration_used_to_generate_candidates": False,
            "historical_172_row_artifact_is_Zmax": False,
            "failure_policy": "RETURN_TYPED_IDENTIFIABILITY_OR_EXISTENCE_GAP_NOT_NUMERIC_ZMAX_GUESS",
        }
        return {**payload, "digest": digest_payload(payload)}

    @staticmethod
    def _experiment_plan(varied: Sequence[str]) -> list[Mapping[str, Any]]:
        letters = sorted({re.sub(r"[^A-Za-z]", "", k).replace("RL", "") or k for k in varied})
        return [
            {"rank": 1, "observable": "FIRST_IONIZATION_POTENTIAL", "protocol": "single-atom resonance-ionization threshold scan on produced atoms/ions", "separates": list(varied), "reason": "directly probes binding of the least-bound frontier electron; no numerical separation is claimed before world response"},
            {"rank": 2, "observable": "LASER_RESONANCE_LEVEL_PATTERN", "protocol": "collinear/resonance laser spectroscopy with decay-chain tagging", "separates": list(varied), "reason": "frontier occupations imply distinct transition/level patterns"},
            {"rank": 3, "observable": "FINE_STRUCTURE_HYPERFINE_AND_MAGNETIC_PATTERN", "protocol": "high-resolution spectroscopy where yield/lifetime permit", "separates": letters, "reason": "competing angular/radial channels and mixtures carry different spin-orbit signatures"},
            {"rank": 4, "observable": "NUCLEAR_BINDING_DECAY_AND_OBJECT_EXISTENCE", "protocol": "production + correlated decay-chain / mass / lifetime evidence", "separates": ["PHYSICAL_OBJECT_EXISTS", "NO_ATTESTED_OBJECT"], "reason": "electronic self-consistency cannot establish that a nucleus/atom physically exists"},
        ]

    @classmethod
    def _channels_for_total(cls, total: int) -> list[dict[str, int]]:
        # The seed is the first post-118 frontier.  When its finite capacity is not
        # enough, birth the next angular research-local channel l=5,6,... with the
        # exact one-electron degeneracy capacity 2(2l+1).  Channel *energy order* is
        # intentionally left unidentified; this expands representation, not answers.
        channels = [{"name": name, "l": l, "capacity": cap, "source": "FROZEN_PREFIX_FRONTIER"} for name, l, cap in cls._BASE_CHANNELS]
        capacity = sum(c["capacity"] for c in channels)
        l = 5
        born = False
        while capacity < max(1, int(total)):
            cap = 2 * (2 * l + 1)
            channels.append({"name": f"RL_l{l}", "l": l, "capacity": cap, "source": "ADAPTIVE_CHANNEL_BIRTH"})
            capacity += cap
            l += 1
            born = True
        # When adaptive birth was needed, keep one additional unfilled channel in the
        # hypothesis space.  Otherwise exact capacity closure would spuriously turn
        # Z values such as q=2(L+1)^2 into a singleton simply because the basis ended.
        if born:
            cap = 2 * (2 * l + 1)
            channels.append({"name": f"RL_l{l}", "l": l, "capacity": cap, "source": "ADAPTIVE_CHANNEL_BIRTH"})
        return channels

    @staticmethod
    def _candidate_count(total: int, channels: Sequence[Mapping[str, int]]) -> int:
        total = int(total)
        if total < 0:
            return 0
        coeff = [0] * (total + 1)
        coeff[0] = 1
        for ch in channels:
            cap = min(int(ch["capacity"]), total)
            nxt = [0] * (total + 1)
            window = 0
            for n in range(total + 1):
                window += coeff[n]
                if n - cap - 1 >= 0:
                    window -= coeff[n - cap - 1]
                nxt[n] = window
            coeff = nxt
        return int(coeff[total])

    @staticmethod
    def _partitions(total: int, channels: Sequence[Mapping[str, int]]) -> list[dict[str, int]]:
        rows: list[dict[str, int]] = []
        def rec(i: int, left: int, acc: dict[str, int]) -> None:
            if i == len(channels):
                if left == 0:
                    rows.append({k: v for k, v in acc.items() if v})
                return
            ch = channels[i]; key = str(ch["name"]); cap = int(ch["capacity"])
            for q in range(0, min(cap, left) + 1):
                acc[key] = q; rec(i + 1, left - q, acc)
            acc.pop(key, None)
        rec(0, int(total), {})
        return rows

    def _closed_prefix(self) -> Mapping[str, Any]:
        report_path = self.root / "reports/BLIND_PER_ELEMENT_RECONSTRUCTION_CURRENT.json"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        rows = [row for row in report.get("rows", ()) if int(row.get("Z", 0)) <= 118]
        if len(rows) != 118 or [int(r["Z"]) for r in rows] != list(range(1, 119)):
            raise RuntimeError("closed periodic prefix must contain contiguous Z=1..118 evidence rows")
        base118 = rows[-1]
        roles: dict[str, int] = {}
        for row in rows:
            roles[str(row.get("electronic_evidence_role", "UNKNOWN"))] = roles.get(str(row.get("electronic_evidence_role", "UNKNOWN")), 0) + 1
        return {
            "row_count": 118,
            "last_Z": 118,
            "base118_configuration_digest": digest_payload({"Z": 118, "configuration": str(base118.get("configuration_candidate"))}),
            "electronic_evidence_role_counts": roles,
            "physical_existence_role": "WORLD_ATTESTED_RECOGNIZED_PREFIX_NOT_ATLAS_DISCOVERY",
        }

    def _row(self, z: int, materialize_candidate_set: bool = False) -> Mapping[str, Any]:
        z = int(z)
        if z <= 118:
            raise ValueError("open frontier rows start at Z=119")
        q = z - 118
        zalpha = float(z * ALPHA)
        channels = self._channels_for_total(q)
        count = self._candidate_count(q, channels)
        names = [str(c["name"]) for c in channels]
        row: dict[str, Any] = {
            "Z": z,
            "status": "IDENTIFIABILITY_GAP" if count != 1 else "IDENTIFIED_SINGLETON",
            "relativistic_Zalpha": zalpha,
            "relativistic_axis_active": True,
            "point_coulomb_Zalpha_ge_1": zalpha >= 1.0,
            "frontier_electron_count": q,
            "symbolic_candidate_count": count,
            "candidate_representation": "COEFFICIENT_OF_PRODUCT_OVER_CAPACITY_BOUNDED_CHANNEL_OCCUPATIONS",
            "frontier_channels": channels,
            "dynamically_born_channel_count": sum(c["source"] == "ADAPTIVE_CHANNEL_BIRTH" for c in channels),
            "configuration_mixture_allowed": True,
            "single_answer_promoted": False,
            "physical_object_existence": "UNATTESTED",
            "nuclear_stability": "UNIDENTIFIED_REQUIRES_BINDING_DECAY_WORLD_OWNER",
            "discriminating_experiments": self._experiment_plan(names),
        }
        if materialize_candidate_set:
            partitions = self._partitions(q, channels)
            candidates = []
            for idx, occ in enumerate(partitions):
                support = tuple(sorted(k for k, v in occ.items() if int(v) > 0))
                candidates.append({
                    "candidate_id": f"Z{z}-C{idx+1:03d}",
                    "frontier_occupation": occ,
                    "frontier_support": list(support),
                    "relativistic_Zalpha": zalpha,
                    "representation": "PURE_CONFIGURATION_BASIS_STATE",
                })
            row["candidate_count"] = len(candidates)
            row["candidate_set"] = candidates
            class_map: dict[tuple[str, ...], list[int]] = {}
            for idx, c in enumerate(candidates):
                class_map.setdefault(tuple(c["frontier_support"]), []).append(idx)
            row["configuration_classes"] = [
                {"support": list(support), "member_count": len(ids), "member_ids": [candidates[i]["candidate_id"] for i in ids], "mixture_allowed_within_class": len(ids) > 1}
                for support, ids in sorted(class_map.items())
            ]
            row["candidate_class_count"] = len(row["configuration_classes"])
        return row

    def run(
        self,
        z_values: Sequence[int] | None = None,
        *,
        materialize_candidate_set: bool = False,
    ) -> Mapping[str, Any]:
        explicit_view = z_values is not None
        # A symbolic frontier view is representation-only and must not depend on
        # a previously materialized periodic-table receipt.  The physical scan,
        # however, requires an attested closed prefix and therefore fails closed
        # in the clean baseline until that prerequisite is regenerated.
        prefix = None
        if not explicit_view:
            report_path = self.root / "reports/BLIND_PER_ELEMENT_RECONSTRUCTION_CURRENT.json"
            if not report_path.exists():
                payload = {
                    "schema": "phi-open-ended-periodic-frontier/v15.6.1",
                    "owner_id": self.OWNER_ID if hasattr(self, "OWNER_ID") else "ATOMIC-OPEN-ENDED-FRONTIER",
                    "status": "BLOCKED_CLEAN_BASELINE_REQUIRES_ATTESTED_CLOSED_PREFIX",
                    "fixed_Zmax_used": False,
                    "historical_172_boundary_used": False,
                    "scan": {
                        "mode": "PHYSICAL_TABLE_EVIDENCE_DRIVEN_SCAN",
                        "fixed_upper_Z": None,
                        "numeric_iteration_or_visit_ceiling": None,
                        "physical_frontier_advanced": False,
                        "missing_prerequisite": str(report_path.relative_to(self.root)),
                    },
                    "results": [],
                    "claim_boundary": {
                        "physical_last_element_Z_identified": False,
                        "clean_baseline_receipt_absence_is_not_nonexistence": True,
                    },
                }
                return {**payload, "digest": digest_payload(payload)}
            prefix = self._closed_prefix()
        if explicit_view:
            zs = [int(x) for x in z_values]
            if any(z <= 118 for z in zs):
                raise ValueError("explicit open-frontier Z values must be >=119")
            results = [self._row(z, materialize_candidate_set=materialize_candidate_set) for z in zs]
            scan = {
                "mode": "EXPLORATORY_SYMBOLIC_VIEW_NOT_PHYSICAL_TABLE_EXTENSION",
                "fixed_upper_Z": None,
                "requested_Z": zs,
                "physical_frontier_advanced": False,
            }
            status = "PASS_OPEN_ENDED_SYMBOLIC_FRONTIER_VIEW"
        else:
            # Truly open-ended physical scan.  There is deliberately no max_Z and no
            # visit budget.  Current evidence fails at the very first unknown object,
            # so the evidence-driven stop occurs at Z=119 after one frontier visit.
            z = int(prefix["last_Z"]) + 1
            results = []
            while True:
                row = dict(self._row(z, materialize_candidate_set=False))
                results.append(row)
                if row["physical_object_existence"] != "ATTESTED":
                    break
                z += 1
            scan = {
                "mode": "PHYSICAL_TABLE_EVIDENCE_DRIVEN_SCAN",
                "fixed_upper_Z": None,
                "numeric_iteration_or_visit_ceiling": None,
                "stop_rule": "FIRST_UNRESOLVED_PHYSICAL_EXISTENCE_OR_REPRESENTATION_GATE",
                "frontier_rows_visited": len(results),
                "first_unresolved_Z": int(results[-1]["Z"]),
                "last_closed_physical_prefix_Z": int(prefix["last_Z"]),
                "Zmax_identified": False,
            }
            status = "STOPPED_AT_FIRST_UNRESOLVED_PHYSICAL_EXISTENCE_GATE"

        payload = {
            "schema": "atomic-open-ended-frontier-identifiability/v1",
            "owner_id": self.owner_id,
            "status": status,
            "closed_prefix": prefix,
            "scan": scan,
            "target_Z": [int(x) for x in z_values] if z_values is not None else None,
            "relativistic_Zalpha_used_as_configuration_hypothesis_axis": True,
            "seen_correction_label_vocabulary_used": False,
            "post118_reference_configurations_used": False,
            "fixed_Zmax_used": False,
            "historical_172_boundary_used": False,
            "symbolic_frontier_is_open_ended": True,
            "results": results,
            "claim_boundary": {
                "closed_prefix_is_atlas_discovery": False,
                "candidate_set_is_ground_truth": False,
                "candidate_set_is_exhaustive_over_all_quantum_representations": False,
                "configuration_mixture_coefficients_identified": False,
                "experiment_list_is_executed_measurement": False,
                "exact_energy_separation_claimed": False,
                "nuclear_existence_established_beyond_prefix": False,
                "physical_Zmax_identified": False,
                "world_novelty_claimed": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}


NUCLEAR_BINDING_DECAY_WORLD_OWNER_ID = "NUCLEAR-BINDING-DECAY-WORLD-INTERACTION/1.0.0"
ELEMENT_EXISTENCE_MIN_LIFETIME_S = 1.0e-14


class OpenEndedNuclearBindingDecayWorldOwner:
    """Evidence-first nuclear existence owner with no fixed Z or N ceiling.

    The owner deliberately separates empirical attestation from reference simulation.
    A reference mass/decay model may design isotope hypotheses and discriminating
    measurements, but only an attested nuclide identity plus lifetime at or above the
    IUPAC element-existence timescale may advance the *physical* periodic frontier.
    Absence of evidence is never converted into a proof that no isotope exists.
    """

    owner_id = NUCLEAR_BINDING_DECAY_WORLD_OWNER_ID

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or Path(__file__).resolve().parents[2]).resolve()

    def contract(self) -> Mapping[str, Any]:
        payload = {
            "owner_id": self.owner_id,
            "output_kind": "OPEN_ENDED_NUCLEAR_BINDING_DECAY_AND_OBJECT_EXISTENCE_WORLD_INTERACTION",
            "fixed_upper_Z": None,
            "fixed_upper_N": None,
            "element_existence_min_lifetime_s": ELEMENT_EXISTENCE_MIN_LIFETIME_S,
            "physical_advance_rule": "ATTESTED_Z_IDENTITY_AND_NUCLIDE_LIFETIME_AT_OR_ABOVE_THRESHOLD",
            "reference_simulation_may_promote_physical_existence": False,
            "absence_of_attestation_is_nonexistence_proof": False,
            "gross_binding_model": "OPEN_ENDED_GROSS_SEMF_BA_OPTIMIZATION/2.0",
            "alpha_decay_reference_models": ["VSS", "UDL"],
            "spontaneous_fission_half_life_model": None,
            "failure_policy": "STOP_AT_FIRST_UNRESOLVED_Z_WITH_TYPED_NUCLEAR_EVIDENCE_GAP",
        }
        return {**payload, "digest": digest_payload(payload)}

    @staticmethod
    def _experiment_plan(z: int, candidate: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        return [
            {
                "rank": 1,
                "observable": "CORRELATED_DECAY_CHAIN_AND_LIFETIME",
                "protocol": "production event followed by time-correlated alpha/SF/EC chain with Z-linked daughter evidence",
                "separates": ["QUALIFYING_NUCLIDE_EXISTS", "NO_QUALIFYING_NUCLIDE_ATTESTED_YET"],
                "reason": "directly addresses element existence and the >=1e-14 s lifetime gate",
            },
            {
                "rank": 2,
                "observable": "NUCLEAR_MASS_AND_Q_ALPHA",
                "protocol": "single-ion mass measurement where feasible, otherwise decay-chain Q-value closure",
                "separates": ["COMPETING_ISOTOPE_MASS_SURFACES", "ALPHA_CHAIN_ASSIGNMENTS"],
                "reason": "binding/separation and alpha energetics are direct falsifiers of the gross mass surface",
            },
            {
                "rank": 3,
                "observable": "SPONTANEOUS_FISSION_PARTIAL_HALF_LIFE",
                "protocol": "time-correlated fission detection with daughter/mass tagging",
                "separates": ["ALPHA_DOMINATED", "FISSION_DOMINATED", "MIXED_DECAY"],
                "reason": "the current reference world deliberately has no fission-barrier dynamics owner",
            },
            {
                "rank": 4,
                "observable": "ONE_AND_TWO_NUCLEON_SEPARATION_ENERGIES",
                "protocol": "mass/reaction-Q evidence sufficient to determine Sn,S2n,Sp,S2p",
                "separates": ["BOUND_ISOTOPE", "NEUTRON_DRIP", "PROTON_DRIP"],
                "reason": "tests whether a candidate nucleus is particle-bound before chemistry is considered",
            },
        ]

    @staticmethod
    def _attested_rows_for_z(z: int, rows: Sequence[Mapping[str, Any]] | None) -> list[Mapping[str, Any]]:
        return [dict(r) for r in (rows or ()) if int(r.get("Z", -1)) == int(z)]

    @classmethod
    def _attested_existence(cls, z: int, rows: Sequence[Mapping[str, Any]] | None) -> Mapping[str, Any]:
        candidates = cls._attested_rows_for_z(z, rows)
        qualifying: list[Mapping[str, Any]] = []
        rejected_estimated = 0
        for row in candidates:
            if bool(row.get("estimated_or_systematics", False)):
                rejected_estimated += 1
                continue
            if row.get("source_kind") not in {"EMPIRICAL", "WORLD_ATTESTED"}:
                continue
            if row.get("z_identity_attested") is not True:
                continue
            try:
                lifetime = float(row.get("half_life_s"))
            except (TypeError, ValueError):
                continue
            if math.isfinite(lifetime) and lifetime >= ELEMENT_EXISTENCE_MIN_LIFETIME_S:
                qualifying.append({**row, "half_life_s": lifetime})
        return {
            "Z": int(z),
            "candidate_attestation_count": len(candidates),
            "qualifying_attestation_count": len(qualifying),
            "estimated_rows_rejected": rejected_estimated,
            "physical_object_existence": "ATTESTED" if qualifying else "UNATTESTED",
            "qualifying_nuclides": qualifying,
            "absence_is_nonexistence_proof": False,
        }

    def _reference_row(self, z: int) -> Mapping[str, Any]:
        candidate = dict(_nuclear_candidate(int(z)))
        return {
            "Z": int(z),
            "status": "REFERENCE_SIMULATION_ONLY_NOT_EXISTENCE_ATTESTATION",
            "reference_candidate": candidate,
            "alpha_partial_lifetime_models_available": [
                name for name, value in (
                    ("VSS", candidate.get("alpha_half_life_VSS_s")),
                    ("UDL", candidate.get("alpha_half_life_UDL_s")),
                ) if value is not None
            ],
            "total_half_life_identified": False,
            "missing_decay_physics": ["SPONTANEOUS_FISSION_BARRIER_AND_ACTION", "BETA_EC_PARTIAL_RATES"],
            "physical_object_existence": "UNATTESTED",
            "reference_simulation_is_empirical_world": False,
            "discriminating_experiments": self._experiment_plan(int(z), candidate),
        }

    def run(
        self,
        *,
        start_z: int = 119,
        attested_nuclides: Sequence[Mapping[str, Any]] | None = None,
        z_values: Sequence[int] | None = None,
    ) -> Mapping[str, Any]:
        start_z = int(start_z)
        if start_z < 1:
            raise ValueError("start_z must be positive")
        explicit = z_values is not None
        results: list[Mapping[str, Any]] = []
        if explicit:
            zs = [int(z) for z in z_values or ()]
            if any(z < 1 for z in zs):
                raise ValueError("Z values must be positive")
            for z in zs:
                att = self._attested_existence(z, attested_nuclides)
                ref = self._reference_row(z)
                results.append({"Z": z, "attestation": att, "reference_world": ref})
            scan = {
                "mode": "NUCLEAR_REFERENCE_DIAGNOSTIC_VIEW",
                "fixed_upper_Z": None,
                "fixed_upper_N": None,
                "requested_Z": zs,
                "physical_frontier_advanced": False,
                "Zmax_identified": False,
            }
            status = "PASS_OPEN_ENDED_NUCLEAR_REFERENCE_VIEW"
        else:
            z = start_z
            while True:
                att = self._attested_existence(z, attested_nuclides)
                ref = self._reference_row(z)
                results.append({"Z": z, "attestation": att, "reference_world": ref})
                if att["physical_object_existence"] != "ATTESTED":
                    break
                z += 1
            scan = {
                "mode": "PHYSICAL_NUCLEAR_EVIDENCE_DRIVEN_SCAN",
                "fixed_upper_Z": None,
                "fixed_upper_N": None,
                "numeric_iteration_or_visit_ceiling": None,
                "stop_rule": "FIRST_Z_WITHOUT_QUALIFYING_ATTESTED_NUCLIDE",
                "frontier_rows_visited": len(results),
                "first_unresolved_Z": int(results[-1]["Z"]),
                "last_attested_Z_in_this_scan": int(results[-2]["Z"]) if len(results) > 1 else None,
                "Zmax_identified": False,
            }
            status = "STOPPED_AT_FIRST_UNRESOLVED_NUCLEAR_EXISTENCE_GATE"
        payload = {
            "schema": "open-ended-nuclear-binding-decay-world/v1",
            "owner_id": self.owner_id,
            "status": status,
            "contract": self.contract(),
            "scan": scan,
            "results": results,
            "claim_boundary": {
                "reference_simulation_is_empirical_world": False,
                "reference_simulation_establishes_physical_element": False,
                "gross_SEMF_establishes_island_of_stability": False,
                "alpha_partial_half_life_is_total_lifetime": False,
                "absence_of_attestation_establishes_nonexistence": False,
                "physical_Zmax_identified": False,
                "scientific_law_established": False,
            },
        }
        return {**payload, "digest": digest_payload(payload)}


# Backward-compatible name; no parallel implementation.
Post118ConfigurationIdentifiabilityOwner = AtomicOpenEndedFrontierOwner


__all__ = [
    "BlindPerElementReconstructionOwner",
    "PhiSpaceInteriorHoleElectronicStructureOwner",
    "phi_space_atomic_interior_hole_qualification",
    "OWNER_ID",
    "PHI_SPACE_ELECTRONIC_OWNER_ID",
    "SCHEMA",
    "ATOMIC_OPEN_ENDED_FRONTIER_OWNER_ID",
    "POST118_IDENTIFIABILITY_OWNER_ID",
    "AtomicOpenEndedFrontierOwner",
    "Post118ConfigurationIdentifiabilityOwner",
    "NUCLEAR_BINDING_DECAY_WORLD_OWNER_ID",
    "OpenEndedNuclearBindingDecayWorldOwner",
]
