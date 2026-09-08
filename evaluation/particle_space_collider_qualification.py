"""Release qualification for ParticleSpace collider/recast capability v7.6."""
from __future__ import annotations

import hashlib
import json
import ast
import re
from fractions import Fraction
from pathlib import Path
from typing import Any

from source.lawspace.particle_collider import ParticleColliderQualification
from source.lawspace.schema import digest_payload

EXPECTED_BLIND_LOGIC_SHA256 = "8436d9a60f4017f3ab17c63ade7e4a7888732e2ed2932404f379c5465de24e9b"
EXPECTED_RANKING_DIGEST = "cbc0580cb24f2562a66fe6ffda8bc3d948c1537254f082a8ecaa7821cbc6b242"
EXPECTED_SHORTLIST_DIGEST = "1c5659f2e0c378712e33aa8aa46a61c5b0c2c30e18cafedc311f27fa7b9a91da"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _blind_logic_sha256(path: Path) -> str:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "ParticleSpaceOwner")
    methods = []
    for node in owner.body:
        if isinstance(node, ast.FunctionDef) and (node.name.startswith("_blind") or node.name.startswith("blind_discovery")):
            text = ast.get_source_segment(source, node) or ""
            text = re.sub(r"SCIENTIFIC-PROMOTION-CORE/[0-9.]+", "SCIENTIFIC-PROMOTION-CORE/<VERSION>", text)
            methods.append(text)
    return hashlib.sha256("\n\n".join(methods).encode("utf-8")).hexdigest()


def _verify_gate_hashes(root: Path) -> bool:
    gate_root = root / "reports" / "particle_space_recast_technical_gate_current"
    hashes = gate_root / "HASHES.txt"
    if not hashes.exists():
        return False
    for line in hashes.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, rel = line.split("  ", 1)
        path = gate_root / rel
        if not path.is_file() or _sha256(path) != expected:
            return False
    return True


def run_release_qualification(root: str | Path | None = None) -> dict[str, Any]:
    root = Path(root or Path(__file__).resolve().parents[1])
    freeze = json.loads((root / "reports" / "particle_space_blind_discovery_freeze_v7_5.json").read_text(encoding="utf-8"))
    gate = json.loads((root / "reports" / "particle_space_recast_technical_gate_status_current.json").read_text(encoding="utf-8"))
    owner = ParticleColliderQualification()
    selected = {int(r["selection_order"]): r for r in freeze["selected_shortlist"]}
    x12 = selected[12]
    x16 = selected[16]
    g12 = owner.global_form_decay_gate(tuple(x12["coordinate"]["su3_dynkin"]), int(x12["coordinate"]["su2_dimension"]), Fraction(int(x12["coordinate"]["hypercharge_numerator"]), int(x12["coordinate"]["hypercharge_denominator"])))
    g16 = owner.global_form_decay_gate(tuple(x16["coordinate"]["su3_dynkin"]), int(x16["coordinate"]["su2_dimension"]), Fraction(int(x16["coordinate"]["hypercharge_numerator"]), int(x16["coordinate"]["hypercharge_denominator"])))
    g7row = selected[7]
    g7 = owner.global_form_decay_gate(tuple(g7row["coordinate"]["su3_dynkin"]), int(g7row["coordinate"]["su2_dimension"]), Fraction(int(g7row["coordinate"]["hypercharge_numerator"]), int(g7row["coordinate"]["hypercharge_denominator"])))
    sample_ct = owner.d7_reference_ctau_m(2.0, 100.0)
    sample_lam = owner.d7_reference_lambda_eff_tev(2.0, sample_ct)

    checks = {
        "blind_selection_algorithm_logic_unchanged_except_promotion_owner_metadata": _blind_logic_sha256(root / "source" / "lawspace" / "particle_space.py") == EXPECTED_BLIND_LOGIC_SHA256,
        "blind_full_ranking_digest_unchanged": freeze["full_ranking_digest"] == EXPECTED_RANKING_DIGEST,
        "blind_shortlist_digest_unchanged": freeze["selected_shortlist_digest"] == EXPECTED_SHORTLIST_DIGEST,
        "x12_selection_identity_unchanged": x12["blind_id"] == "PB-25F3479BE943407EE646",
        "x16_selection_identity_unchanged": x16["blind_id"] == "PB-800B6CB4FBAC6EB1CFD7",
        "x12_k6_zero": g12["global_form_profile"]["residue_k6"] == 0 and g12["pure_sm_linear_decay_obstructed"] is False,
        "x16_k6_zero": g16["global_form_profile"]["residue_k6"] == 0 and g16["pure_sm_linear_decay_obstructed"] is False,
        "nonzero_k6_control_has_sm_decay_obstruction": g7["global_form_profile"]["residue_k6"] == 5 and g7["pure_sm_linear_decay_obstructed"] is True,
        "d7_reference_is_invertible": abs(sample_lam - 100.0) <= 1.0e-10,
        "full_detector_chain_not_fabricated": gate["execution"]["full_detector_chain_executed"] is False,
        "benchmark_embedding_replay_passed": gate["execution"]["benchmark_embedding_replay_pass"] is True,
        "benchmark_embedding_replay_error_below_1e10": float(gate["execution"]["benchmark_embedding_max_relative_replay_error"]) < 1.0e-10,
        "technical_gate_internal_hashes_verified": _verify_gate_hashes(root),
        "generic_x12_exclusion_not_claimed": gate["new_scientific_result"]["generic_x12_excluded"] is False,
        "generic_x16_exclusion_not_claimed": gate["new_scientific_result"]["generic_x16_excluded"] is False,
        "blind_feedback_to_ranking_false": gate["blind_selection_feedback_to_ranking"] is False,
        "world_new_particle_claim_false": gate["world_new_particle_claimed"] is False,
    }
    rows=[{"check":k,"status":"PASS" if v else "FAIL"} for k,v in checks.items()]
    payload = {
        "schema": "phi-particlespace-collider-qualification/v7.6",
        "owner_id": owner.owner_id,
        "capability_id": owner.capability_id,
        "status": "PASS_PARTICLESPACE_COLLIDER_QUALIFICATION_FAIL_CLOSED" if all(checks.values()) else "FAIL_PARTICLESPACE_COLLIDER_QUALIFICATION",
        "passed": sum(bool(v) for v in checks.values()),
        "total": len(checks),
        "checks": rows,
        "x12": {"blind_id": x12["blind_id"], "coordinate": x12["coordinate"], "global_form_gate": g12},
        "x16": {"blind_id": x16["blind_id"], "coordinate": x16["coordinate"], "global_form_gate": g16},
        "recast_gate_status": gate,
        "claim_boundary": {
            "generic_x12_excluded": False,
            "generic_x16_excluded": False,
            "new_particle_claimed": False,
            "conditional_benchmark_embedding_requires_amplitude_validation": True,
            "full_detector_recast_executed": False,
        },
    }
    return {**payload, "digest": digest_payload(payload)}


if __name__ == "__main__":
    print(json.dumps(run_release_qualification(), indent=2, sort_keys=True))
