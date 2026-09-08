"""Reproducible v8 pharmaceutical fail-closed gates plus inherited public-PK modeling."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Mapping

import numpy as np
from scipy.stats import chi2 as chi2_distribution

from source.lawspace.domains import DOMAIN_REGISTRIES, canonical_axis_count, dynamic_axis_registry_state
from source.lawspace.pharmaceutical import PharmaceuticalDomainOwner
from source.lawspace.schema import digest_payload


def _fit_summary_models(groups: list[Mapping[str, Any]], mean_key: str, sd_key: str) -> Mapping[str, Any]:
    y = np.asarray([float(g[mean_key]) for g in groups], dtype=float)
    sem = np.asarray([float(g[sd_key]) / np.sqrt(float(g["n"])) for g in groups], dtype=float)
    w = 1.0 / (sem * sem)
    X0 = np.ones((len(groups), 1), dtype=float)
    X1 = np.column_stack([np.ones(len(groups)), np.asarray([0.0, 1.0, 1.0], dtype=float)])
    def fit(X: np.ndarray) -> Mapping[str, Any]:
        beta = np.linalg.solve(X.T @ (w[:, None] * X), X.T @ (w * y))
        pred = X @ beta
        chi2 = float(np.sum(((y - pred) / sem) ** 2))
        dof = max(len(y) - X.shape[1], 1)
        return {
            "parameters": [float(x) for x in beta],
            "predictions": [float(x) for x in pred],
            "chi2": chi2,
            "dof": dof,
            "p_value": float(chi2_distribution.sf(chi2, dof)),
            "aic_up_to_common_constant": float(chi2 + 2 * X.shape[1]),
        }
    m0, m1 = fit(X0), fit(X1)
    return {
        "M0_constant": m0,
        "M1_predeclared_mild_vs_moderate_severe": m1,
        "delta_chi2_M0_minus_M1": float(m0["chi2"] - m1["chi2"]),
        "delta_aic_M0_minus_M1": float(m0["aic_up_to_common_constant"] - m1["aic_up_to_common_constant"]),
        "interpretation": "Group-level summary comparison only; not a patient-level PK model and not an eGFR-to-PK functional law.",
    }


def _metformin_renal_function_model(root: Path) -> Mapping[str, Any]:
    path = root / "data/pharmaceutical/metformin_renal_function_pk_summary_v7_9.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    groups = list(doc["groups"])
    clearance = _fit_summary_models(groups, "renal_clearance_mean_ml_min", "renal_clearance_sd_ml_min")
    cmax = _fit_summary_models(groups, "cmax_mean_mcg_ml", "cmax_sd_mcg_ml")
    result = {
        "schema": "phi-pharmaceutical-dynamic-axis-model/v8.0",
        "dataset": doc,
        "registered_missing_axis": {
            "axis_id": "renal_function_egfr",
            "present": "renal_function_egfr" in DOMAIN_REGISTRIES["pharmaceutical"].axes,
            "semantic_boundary": "The PK table uses CLcr strata; the canonical eGFR axis is a current renal-function coordinate and is not numerically substituted for CLcr in this fit.",
        },
        "renal_clearance_model_comparison": clearance,
        "cmax_model_comparison": cmax,
        "model_result": "RENAL_FUNCTION_COORDINATE_REQUIRED_BY_PUBLIC_SUMMARY_DATA_CONSTANT_MODEL_REJECTED" if clearance["M0_constant"]["p_value"] < 0.01 and cmax["M0_constant"]["p_value"] < 0.01 else "INCONCLUSIVE",
        "claim_boundary": {
            "new_drug_discovered": False,
            "new_pk_law_established": False,
            "egfr_to_clearance_function_established": False,
            "patient_specific_dosing_allowed": False,
            "summary_statistics_only": True,
        },
    }
    return {**result, "digest": digest_payload(result)}


def run_release_qualification(root: str | Path) -> Mapping[str, Any]:
    root = Path(root)
    freeze = json.loads((root/'data/pharmaceutical/pharma_blind_top10_freeze_v7_8.json').read_text())
    evidence = json.loads((root/'data/pharmaceutical/pharma_blind_top10_postfreeze_evidence_v7_8.json').read_text())['evidence']
    prior_art = json.loads((root/'data/pharmaceutical/pharma_blind_top10_postfreeze_prior_art_v7_8.json').read_text())['records']
    known = json.loads((root/'data/pharmaceutical/pharma_known_controls_v7_8.json').read_text())['controls']
    owner = PharmaceuticalDomainOwner()
    known_replay = {name: owner.assess_research_record(record) for name, record in known.items()}
    rows=[]
    for item in freeze['candidates']:
        rank=str(item['rank'])
        assessment=owner.assess_hypothesis(item['coordinate'], evidence[rank])
        rows.append({**item, 'assessment':assessment, 'postfreeze_prior_art':prior_art.get(rank)})
    retained=[x['rank'] for x in rows if x['assessment']['retained_for_research']]
    rejected=[x['rank'] for x in rows if not x['assessment']['retained_for_research']]
    renal_model = _metformin_renal_function_model(root)
    registry_state = dynamic_axis_registry_state()
    report={
      'schema':'phi-pharmaceutical-semantic-qualification/v8.2',
      'owner_contract':owner.contract(),
      'dynamic_axis_registry_state':registry_state,
      'metformin_renal_function_model':renal_model,
      'freeze_digest_input_hashes':[x['hash'] for x in freeze['candidates']],
      'reselection':False,
      'known_control_count':len(known_replay),
      'known_usable_complete_count':sum(x['structurally_complete'] for x in known_replay.values()),
      'candidate_count':len(rows),
      'retained_for_research_ranks':retained,
      'rejected_ranks':rejected,
      'promotion_allowed_count':sum(bool(x['assessment']['promotion_allowed']) for x in rows),
      'world_novelty_established_count':0,
      'status':'PASS_PHARMACEUTICAL_V8_2_SCHEMA_ENRICHMENT_RAW_EVIDENCE_FAILS_CLOSED_AND_INHERITED_RENAL_MODEL_REPLAYS' if len(known_replay)==3 and len(rows)==10 and not any(x['assessment']['promotion_allowed'] for x in rows) and not any(x['assessment'].get('retained_for_research') for x in rows) and all(x['assessment'].get('gates',{}).get('SCIENTIFIC_VERIFICATION',{}).get('status') == 'FAIL' for x in rows) and registry_state['canonical_axis_count'] == canonical_axis_count() and renal_model['model_result'].startswith('RENAL_FUNCTION_COORDINATE_REQUIRED') else 'FAIL',
      'rows':rows,
      'claim_boundary':'v8 raw legacy evidence is untrusted and cannot retain a world research hypothesis. The inherited renal-function modeling is a regression model only; not a medicine, efficacy/safety claim, clinical recommendation, novelty proof, or renewed WORLD attestation.'
    }
    return report

if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('--root',default='.')
    a=p.parse_args(); print(json.dumps(run_release_qualification(a.root),ensure_ascii=False,indent=2,sort_keys=True))
