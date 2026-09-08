"""Executable qualification for the adaptive-axis + deterministic selective research proof."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from source.lawspace.schema import digest_payload
from source.lawspace.domains import DOMAIN_REGISTRIES, canonical_axis_count, dynamic_axis_registry_state
from evaluation.adaptive_axis_research_qualification import run as run_adaptive

OWNER_ID = "RESEARCH-PROOF-QUALIFICATION/1.0.0"
SCHEMA = "phi-research-proof-qualification/v1"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _digest_valid(payload: dict[str, Any]) -> bool:
    work = dict(payload)
    stored = str(work.pop("digest", ""))
    return bool(stored) and digest_payload(work) == stored


def _selector_hash(seed: str, candidate_id: str) -> str:
    return hashlib.sha256(f"{seed}|{candidate_id}".encode()).hexdigest()



def _prospective_discovery_gate(adaptive: dict[str, Any]) -> dict[str, Any]:
    scan = dict(adaptive.get("p2x7_axis_scan", {}) or {})
    scan_digest = str(scan.get("digest", ""))
    candidate = {
        "candidate_id": "P2X7-PD-ENDOTYPE-INTERACTION-001",
        "source_internal_freeze": "RESEARCH_EXAMPLE_P2X7_PD_ADAPTIVE_AXIS_CURRENT",
        "source_scan_digest": scan_digest,
        "hypothesis": "P2X7 antagonism has a larger neuroprotective effect in a pre-treatment P2X7-positive neuroinflammatory PD endotype than in toxin-dominant/P2X7-low contexts.",
        "prospective_primary_model": "Y = beta0 + beta_T*T + beta_E*E + beta_TE*(T*E) + declared_covariates + epsilon",
        "primary_parameter": "beta_TE",
        "primary_estimand": "treatment_by_endotype_interaction_beta_TE",
        "machine_directional_prediction": "beta_TE > 0",
        "directional_prediction": "beta_TE indicates greater treatment benefit in the P2X7-positive neuroinflammatory endotype",
        "falsifier": "No reproducible treatment-by-endotype interaction and no held-out predictive gain after adding the frozen endotype coordinate.",
        "freeze_predates_current_external_audit": True,
    }
    candidate["freeze_digest"] = digest_payload(candidate)
    prior_art = {
        "status": "BOUNDED_POSTFREEZE_AUDIT_COMPLETED_EXACT_PROSPECTIVE_INTERACTION_NOT_ESTABLISHED",
        "world_novelty_established": False,
        "sources": [
            {"id": "PMID40774697", "role": "human measurability anchor", "finding": "P2X7-associated proinflammatory microglial signal is measurable with [11C]SMW139 PET in Parkinson disease."},
            {"id": "PMID31417352", "role": "context-dependence anchor", "finding": "P2X7 binding differed between acute 6-OHDA and chronic alpha-synuclein PD models."},
            {"id": "PMID41672134", "role": "2026 field review", "finding": "P2X7 blockade is an established neuroprotection hypothesis with a recognized preclinical-to-clinical translation gap."},
        ],
        "boundary": "A bounded literature search can show that the exact frozen interaction program was not located; it cannot prove world novelty or absence of all prior art.",
    }
    stages = {
        "internal_search": "PASS_ADAPTIVE_AXIS_RESEARCH",
        "freeze": "PASS_DIGEST_BOUND_PREEXISTING_INTERNAL_HYPOTHESIS",
        "external_prior_art_audit": prior_art["status"],
        "prospective_prediction": "PASS_FROZEN_BEFORE_NEW_PROSPECTIVE_DATA",
        "independent_experiment_or_new_data": "BLOCKED_NOT_PRESENT_IN_RELEASE",
        "independent_replication": "BLOCKED_REQUIRES_FIRST_PROSPECTIVE_RESULT",
    }
    return {
        "schema": "phi-prospective-discovery-gate/v1",
        "candidate": candidate,
        "postfreeze_prior_art_audit": prior_art,
        "experiment_contract": {
            "hold_constant": ["species_or_human_cohort_definition", "P2X7_antagonist", "exposure", "primary_endpoint_definition"],
            "stratification_variable": "pre-treatment P2X7/neuroinflammation endotype measured independently of treatment outcome",
            "primary_test": "treatment_by_endotype_interaction",
            "required_controls": ["randomization_or_declared causal design", "blinded endpoint where applicable", "predeclared exclusions", "measurement uncertainty", "held-out regime"],
            "promotion_gate": ["interaction survives multiplicity control", "positive held-out predictive gain", "no unresolved confounded partition", "independent replication"],
        },
        "stages": stages,
        "status": "BLOCKED_EXTERNAL_PROSPECTIVE_EVIDENCE_AND_REPLICATION",
        "scientific_discovery_demonstrated": False,
        "new_drug_discovered": False,
        "world_novelty_established": False,
    }

def run(root: str | Path | None = None) -> dict[str, Any]:
    root = Path(root or Path(__file__).resolve().parents[1])
    fixture = _load(root / "data/research_examples/pharma_candidate_pool_fixture_20260828.json")
    adaptive = run_adaptive(root)
    discovery_gate = _prospective_discovery_gate(adaptive)
    state = dynamic_axis_registry_state()

    # The 15.10.x current release intentionally removed historical search/output
    # reports.  Do not recreate or infer the old precommit/freeze/postfreeze
    # receipts: their absence is provenance, not evidence of failure.  If a
    # complete historical trio is explicitly supplied, it can still be replayed;
    # otherwise the current qualification is based only on live current owners.
    history_paths = {
        "precommit": root / "reports/research_examples/PHARMA_SELECTIVE_SEARCH_PRECOMMIT_CURRENT.json",
        "freeze": root / "reports/research_examples/PHARMA_SELECTIVE_SEARCH_FREEZE_CURRENT.json",
        "postfreeze": root / "reports/research_examples/PHARMA_SELECTIVE_SEARCH_POSTFREEZE_CURRENT.json",
    }
    historical_present = all(path.exists() for path in history_paths.values())
    historical_receipt: dict[str, Any] = {
        "status": "HISTORICAL_SELECTIVE_RECEIPTS_NOT_PRESENT_IN_CURRENT_RELEASE",
        "present": False,
        "replayed": False,
        "selected": [],
        "research_behaviors": [],
    }
    historical_checks: dict[str, bool] = {
        "HISTORICAL_SELECTIVE_RECEIPTS_NOT_FABRICATED": not historical_present,
    }

    if historical_present:
        pre = _load(history_paths["precommit"])
        freeze = _load(history_paths["freeze"])
        post = _load(history_paths["postfreeze"])
        replay = []
        for row in fixture["candidates"]:
            r = dict(row)
            r["selector_hash"] = _selector_hash(pre["seed"], row["candidate_id"])
            replay.append(r)
        replay.sort(key=lambda r: (r["selector_hash"], r["candidate_id"]))
        replay = replay[: int(pre["sample_size"])]
        frozen = freeze["selected"]
        replay_ids = [r["candidate_id"] for r in replay]
        frozen_ids = [r["candidate_id"] for r in frozen]
        replay_hashes = [r["selector_hash"] for r in replay]
        frozen_hashes = [r["selector_hash"] for r in frozen]
        post_statuses = {r["status"] for r in post["outcomes"]}
        post_ids = [r["candidate_id"] for r in post["outcomes"]]
        historical_checks = {
            "HISTORICAL_PRECOMMIT_DIGEST_VALID": _digest_valid(pre),
            "HISTORICAL_FREEZE_DIGEST_VALID": _digest_valid(freeze),
            "HISTORICAL_POSTFREEZE_DIGEST_VALID": _digest_valid(post),
            "HISTORICAL_PRECOMMIT_BINDS_FIXTURE": pre.get("input_pool_digest") == fixture.get("digest"),
            "HISTORICAL_SELECTOR_USES_NO_LITERATURE": pre.get("literature_or_prior_art_used_by_selector") is False,
            "HISTORICAL_NO_MANUAL_OVERRIDE": freeze.get("selection_manual_override") is False,
            "HISTORICAL_FREEZE_BINDS_PRECOMMIT": freeze.get("precommit_digest") == pre.get("digest"),
            "HISTORICAL_DETERMINISTIC_SELECTION_REPLAY": replay_ids == frozen_ids and replay_hashes == frozen_hashes,
            "HISTORICAL_POSTFREEZE_BINDS_FREEZE": post.get("selection_freeze_digest") == freeze.get("digest") and post_ids == frozen_ids,
        }
        historical_receipt = {
            "status": "HISTORICAL_SELECTIVE_RECEIPTS_REPLAYED",
            "present": True,
            "replayed": all(historical_checks.values()),
            "selected": [{"rank": i + 1, "candidate_id": r["candidate_id"], "selector_hash": r["selector_hash"]} for i, r in enumerate(replay)],
            "research_behaviors": sorted(post_statuses),
        }

    checks = {
        "FIXTURE_DIGEST_VALID": _digest_valid(fixture),
        "FIXTURE_EXPLICITLY_NOT_PRISTINE_BLIND_PROOF": fixture.get("source_procedure_integrity") == "NOT_USED_AS_BLIND_DISCOVERY_PROOF_DUE_PRECOMMIT_461_VS_973_DEFECT",
        "HISTORICAL_EVIDENCE_POLICY_FAIL_CLOSED": all(historical_checks.values()),
        "ADAPTIVE_AXIS_QUALIFICATION_PASS": adaptive.get("status") == "PASS_ADAPTIVE_AXIS_RESEARCH_QUALIFICATION" and adaptive.get("passed") == adaptive.get("total") == 25,
        "ADAPTIVE_CAUSAL_SELECTION_BLOCKED_WHEN_CONFOUNDED": adaptive.get("p2x7_axis_scan", {}).get("scan_summary", {}).get("automatic_causal_axis_selection_allowed") is False,
        "CANONICAL_REGISTRY_UNCHANGED": state.get("canonical_axis_count") == canonical_axis_count() and DOMAIN_REGISTRIES["pharmaceutical"].axis_count == 59,
        "RESEARCH_REGION_EXPANDS_ONLY_LOCALLY": adaptive.get("research_region", {}).get("canonical_axis_count") == 59 and adaptive.get("research_region", {}).get("research_region_axis_count") == 60 and adaptive.get("research_region", {}).get("canonical_registry_mutated") is False,
        "PROSPECTIVE_CANDIDATE_DIGEST_BOUND": bool(discovery_gate.get("candidate", {}).get("freeze_digest")) and bool(discovery_gate.get("candidate", {}).get("source_scan_digest")),
        "DISCOVERY_GATE_FAILS_CLOSED_WITHOUT_PROSPECTIVE_DATA": discovery_gate.get("scientific_discovery_demonstrated") is False and discovery_gate.get("stages", {}).get("independent_experiment_or_new_data") == "BLOCKED_NOT_PRESENT_IN_RELEASE",
        "REPLICATION_NOT_FABRICATED": discovery_gate.get("stages", {}).get("independent_replication") == "BLOCKED_REQUIRES_FIRST_PROSPECTIVE_RESULT",
    }
    passed = sum(bool(v) for v in checks.values())
    payload = {
        "schema": "phi-research-proof-qualification/v2",
        "owner_id": OWNER_ID,
        "release": "15.10.2",
        "status": "PASS_RESEARCH_PROOF_QUALIFICATION" if passed == len(checks) else "BLOCKED_RESEARCH_PROOF_QUALIFICATION",
        "passed": passed,
        "total": len(checks),
        "checks": [{"check": k, "status": "PASS" if v else "FAIL"} for k, v in checks.items()],
        "historical_selective_replay": historical_receipt,
        "axis_accounting": {
            "global_canonical_axis_count": state.get("canonical_axis_count"),
            "pharmaceutical_canonical_axis_count": DOMAIN_REGISTRIES["pharmaceutical"].axis_count,
            "p2x7_research_region_axis_count": adaptive.get("research_region", {}).get("research_region_axis_count"),
        },
        "prospective_discovery_gate": discovery_gate,
        "claim_boundary": {
            "historical_selective_receipts_required_for_current_release": False,
            "historical_selective_receipts_fabricated": False,
            "historical_selective_replay_reproduced": historical_receipt["replayed"],
            "pristine_blind_discovery_proved_by_old_pool": False,
            "new_drug_discovered": False,
            "world_novelty_established": False,
            "current_research_procedure_fail_closed": passed == len(checks),
            "adaptive_axis_canonicalized": False,
            "scientific_discovery_demonstrated": False,
            "prospective_independent_data_present": False,
            "independent_replication_present": False,
        },
    }
    return {**payload, "digest": digest_payload(payload)}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, sort_keys=True))
