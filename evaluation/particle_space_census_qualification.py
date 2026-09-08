"""Release qualification for the v7.3 topologically refined open-world ParticleSpace census."""
from __future__ import annotations

import copy
import random
from collections import Counter
from fractions import Fraction
from typing import Any, Mapping

import numpy as np

from source.lawspace.particle_space import (
    ParticleSpaceBounds, ParticleSpaceOwner, anomaly_vector,
    _su3_record, _yukawa_partners,
)
from source.lawspace.schema import digest_payload


def _random_universe_negative_control(seed: int = 20260824, worlds: int = 120) -> Mapping[str, Any]:
    """Destroy SM structure: random five-row worlds should not be magically recovered."""
    owner = ParticleSpaceOwner()
    bounds = ParticleSpaceBounds(spins=("1/2",))
    base = []
    for pq in bounds.su3_dynkin:
        for d2 in bounds.su2_dimensions:
            for n in range(bounds.hypercharge_n_min, bounds.hypercharge_n_max + 1):
                base.append((pq, d2, Fraction(n, bounds.hypercharge_denominator)))
    keys = ("SU3_CUBIC", "SU3_SQ_U1", "SU2_SQ_U1", "U1_CUBIC", "GRAV_SQ_U1")
    cand_meta = []
    cand_anom = []
    cand_tie = []
    truth_index = {}
    for row in base:
        a = anomaly_vector(*row)
        for mult in range(bounds.copy_min, bounds.copy_max + 1):
            idx = len(cand_meta)
            cand_meta.append((*row, mult))
            cand_anom.append([float(mult * a[k]) for k in keys])
            complexity = _su3_record(row[0])[1] * row[1] + abs(float(row[2])) + 0.01 * mult
            yuk = len(_yukawa_partners(*row))
            cand_tie.append(1e-6 * complexity - 1e-8 * yuk)
            truth_index[(*row, mult)] = idx
    A = np.asarray(cand_anom, dtype=float)
    tie = np.asarray(cand_tie, dtype=float)
    rng = random.Random(seed)
    ranks = []
    for _ in range(worlds):
        universe = rng.sample(base, 5)
        hidden_i = rng.randrange(5)
        hidden = universe[hidden_i]
        remaining = [(*row, 3) for i, row in enumerate(universe) if i != hidden_i]
        rem = owner._spectrum_anomaly(remaining)
        remv = np.asarray([float(rem[k]) for k in keys], dtype=float)
        ha = anomaly_vector(*hidden)
        scale = np.asarray([max(abs(float(3 * ha[k])), 1.0) for k in keys], dtype=float)
        dist = np.sqrt(np.sum(((A + remv[None, :]) / scale[None, :]) ** 2, axis=1))
        score = dist + tie
        t_idx = truth_index[(*hidden, 3)]
        truth_score = score[t_idx]
        rank = 1 + int(np.count_nonzero(score < truth_score))
        ranks.append(rank)
    arr = np.asarray(ranks, dtype=int)
    payload = {
        "seed": seed,
        "worlds": worlds,
        "candidate_row_multiplicity_space": len(cand_meta),
        "top1_rate": float(np.mean(arr <= 1)),
        "top10_rate": float(np.mean(arr <= 10)),
        "median_truth_rank": float(np.median(arr)),
        "min_truth_rank": int(np.min(arr)),
        "max_truth_rank": int(np.max(arr)),
        "status": "PASS_RANDOM_UNIVERSE_NEGATIVE_CONTROL" if float(np.mean(arr <= 10)) <= 0.05 else "FAIL_RANDOM_UNIVERSE_NEGATIVE_CONTROL",
    }
    return {**payload, "digest": digest_payload(payload)}


def run_release_qualification() -> Mapping[str, Any]:
    owner = ParticleSpaceOwner()
    bounds = ParticleSpaceBounds()
    summary = owner.census_summary(bounds)
    cells = owner.enumerate_cells(bounds)
    p22648 = next(row for row in cells if row["particle_id"] == "P-22648")
    blind = owner.whole_representation_blind_benchmark(ParticleSpaceBounds(spins=("1/2",)))
    negative = _random_universe_negative_control()

    # v7.5 blind discovery selection is frozen from structural coordinates only.
    # These controls deliberately corrupt every forbidden semantic field and
    # reverse input order; selection/ranking must remain byte-identical by digest.
    blind_discovery = owner.blind_discovery_freeze(bounds, neighbour_count=12, shortlist_count=32, cells=cells)
    semantic_cells = copy.deepcopy(cells)
    for i, row in enumerate(semantic_cells):
        row["observed_name"] = f"PERTURBED_NAME_{i}"
        row["sector_tags"] = [f"PERTURBED_TAG_{i % 13}"]
        row["theory_admissibility"] = f"PERTURBED_THEORY_{i % 7}"
        row["parameter_manifold"] = {"perturbed": i}
        row["yukawa_gate"] = {"renormalizable_sm_higgs_partners": [{"sm_field": "PERTURBED", "higgs": "PERTURBED"}]}
        row["experimental_gate"] = {"status": "PERTURBED", "value": i}
        row["coordinate"]["su3_label"] = f"PERTURBED_LABEL_{i}"
    semantic_blind = owner.blind_discovery_freeze(bounds, neighbour_count=12, shortlist_count=32, cells=semantic_cells)
    reversed_blind = owner.blind_discovery_freeze(bounds, neighbour_count=12, shortlist_count=32, cells=list(reversed(cells)))

    # Post-freeze only: compare the frozen shortlist to the retained v7.4
    # calibration examples.  This comparison is forbidden from feeding back
    # into ranking and exists only to quantify legacy-set overlap.
    from source.lawspace.particle_candidate_dossiers import ParticleCandidateDossierOwner
    legacy = ParticleCandidateDossierOwner().build_internal_dossiers()
    def coord_key(c: Mapping[str, Any]) -> tuple[Any, ...]:
        return (str(c["spin"]), tuple(int(v) for v in c["su3_dynkin"]), int(c["su2_dimension"]), int(c["hypercharge_numerator"]), int(c["hypercharge_denominator"]))
    legacy_map: dict[tuple[Any, ...], set[str]] = {}
    for dossier in legacy:
        for coord in dossier["cell_coordinates"].values():
            legacy_map.setdefault(coord_key(coord), set()).add(str(dossier["candidate_id"]))
    overlap = []
    for row in blind_discovery["selected_shortlist"]:
        matches = sorted(legacy_map.get(coord_key(row["coordinate"]), set()))
        if matches:
            overlap.append({"selection_order": row["selection_order"], "blind_id": row["blind_id"], "legacy_dossier_ids": matches})
    selected = blind_discovery["selected_shortlist"]
    postfreeze_reveal = {
        "feedback_to_ranking": False,
        "legacy_calibration_unique_coordinate_count": len(legacy_map),
        "legacy_overlap_count": len(overlap),
        "legacy_overlap": overlap,
        "spin_counts": dict(sorted(Counter(str(r["coordinate"]["spin"]) for r in selected).items())),
        "closure_class_counts": dict(sorted(Counter(str(r["structural"]["closure_class"]) for r in selected).items())),
        "su3_dimension_counts": {str(k): v for k, v in sorted(Counter(int(r["coordinate"]["su3_dimension"]) for r in selected).items())},
        "su2_dimension_counts": {str(k): v for k, v in sorted(Counter(int(r["coordinate"]["su2_dimension"]) for r in selected).items())},
        "abs_hypercharge_ge_2_count": sum(abs(int(r["coordinate"]["hypercharge_numerator"]) / int(r["coordinate"]["hypercharge_denominator"])) >= 2.0 for r in selected),
    }

    checks = {
        "finite_window_cardinality_exact": summary["cell_count"] == 26460,
        "finite_window_not_claimed_as_space_ceiling": summary["finite_window_is_space_ceiling"] is False,
        "observed_gauge_basis_anchors_present": summary["observed_count"] == 19,
        "unobserved_cells_retained": summary["unobserved_candidate_or_constrained_count"] == 26441,
        "single_cell_anomaly_not_used_as_forbidden_gate": summary["status_counts"].get("FORBIDDEN", 0) == 0,
        "whole_representation_blind_top1_all_five": blind["top1_recovery"] == 1.0 and blind["max_truth_rank"] == 1,
        "whole_representation_ranking_blind_to_hidden_coordinate": all(not row["hidden_coordinate_used_during_ranking"] for row in blind["tasks"]),
        "random_universe_negative_control_passes": negative["status"] == "PASS_RANDOM_UNIVERSE_NEGATIVE_CONTROL",
        "global_form_counts_exact": summary["global_form_axis"]["compatible_cell_counts"] == {"Z1": 26460, "Z2": 13284, "Z3": 8820, "Z6": 4428},
        "global_form_k6_distribution_exact": summary["global_form_axis"]["k6_residue_counts"] == {"0": 4428, "1": 4392, "2": 4428, "3": 4392, "4": 4428, "5": 4392},
        "all_observed_anchors_z6_compatible": summary["global_form_axis"]["observed_incompatible_counts"]["Z6"] == 0,
        "alternative_global_form_branches_retained": summary["global_form_axis"]["alternative_branches_retained"] is True and summary["global_form_axis"]["branch_instance_count"] == 105840,
        "p22648_global_form_canary": (
            p22648["global_form_axis"]["residue_k6"] == 5
            and p22648["global_form_axis"]["branches"]["Z1"]["compatible"] is True
            and all(p22648["global_form_axis"]["branches"][form]["compatible"] is False for form in ("Z2", "Z3", "Z6"))
        ),
        "census_cannot_promote": summary["promotion_allowed_by_census"] is False,
        "blind_discovery_candidate_universe_exact": blind_discovery["candidate_universe_count"] == 4410,
        "blind_discovery_shortlist_exact": len(blind_discovery["selected_shortlist"]) == 32,
        "blind_discovery_prior_art_not_accessed": blind_discovery["literature_accessed_during_ranking"] is False,
        "blind_discovery_legacy_dossiers_not_used": blind_discovery["legacy_dossier_builder_used_during_ranking"] is False,
        "blind_discovery_sector_tags_not_used": blind_discovery["sector_tags_used_during_ranking"] is False,
        "blind_discovery_observed_names_not_used": blind_discovery["observed_names_used_during_ranking"] is False,
        "blind_discovery_semantic_perturbation_invariant": (
            semantic_blind["full_ranking_digest"] == blind_discovery["full_ranking_digest"]
            and semantic_blind["selected_shortlist_digest"] == blind_discovery["selected_shortlist_digest"]
        ),
        "blind_discovery_input_order_invariant": (
            reversed_blind["full_ranking_digest"] == blind_discovery["full_ranking_digest"]
            and reversed_blind["selected_shortlist_digest"] == blind_discovery["selected_shortlist_digest"]
        ),
        "blind_discovery_deterministic_no_rng": blind_discovery["precommit"]["random_seed"] is None and blind_discovery["precommit"]["stochastic_steps"] is False,
        "blind_discovery_cannot_promote": blind_discovery["promotion_allowed"] is False,
        "blind_discovery_freeze_status": blind_discovery["status"] == "BLIND_SELECTION_FROZEN_PRIOR_ART_NOT_ACCESSED",
    }
    payload = {
        "schema": "phi-particlespace-census-qualification/v7.5",
        "owner_id": owner.owner_id,
        "status": "PASS_PARTICLESPACE_OPEN_WORLD_CENSUS_AND_BLIND_SELECTION" if all(checks.values()) else "FAIL_PARTICLESPACE_OPEN_WORLD_CENSUS_OR_BLIND_SELECTION",
        "checks": checks,
        "summary": summary,
        "whole_representation_blind": blind,
        "random_universe_negative_control": negative,
        "blind_discovery": {
            "schema": blind_discovery["schema"],
            "status": blind_discovery["status"],
            "candidate_universe_count": blind_discovery["candidate_universe_count"],
            "selected_shortlist_count": len(blind_discovery["selected_shortlist"]),
            "precommit_digest": blind_discovery["precommit"]["precommit_digest"],
            "full_ranking_digest": blind_discovery["full_ranking_digest"],
            "selected_shortlist_digest": blind_discovery["selected_shortlist_digest"],
            "selection_freeze_digest": blind_discovery["selection_freeze_digest"],
            "claim_boundary": blind_discovery["claim_boundary"],
        },
        "postfreeze_reveal": postfreeze_reveal,
        "p22648_global_form_canary": {
            "particle_id": p22648["particle_id"],
            "coordinate": p22648["coordinate"],
            "global_form_axis": p22648["global_form_axis"],
        },
    }
    return {**payload, "digest": digest_payload(payload)}


if __name__ == "__main__":
    import json
    print(json.dumps(run_release_qualification(), indent=2, sort_keys=True))
