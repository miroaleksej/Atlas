from pathlib import Path
import hashlib

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_long_horizon_universal_scientific_portfolio_qualification(tmp_path):
    from evaluation.long_horizon_blind_cycle_qualification import _run_universal_portfolio_qualification
    from source.lawspace.long_horizon_scientific_cycle import LongHorizonBlindScientificCycleKernel

    k=LongHorizonBlindScientificCycleKernel(ROOT, state_path=tmp_path/'universal_scientific_portfolio_state.json')
    r=_run_universal_portfolio_qualification(k)
    assert r['status']=='PASS_UNIVERSAL_SCIENTIFIC_PORTFOLIO_QUALIFICATION'
    assert r['passed']==r['total']==22
    cases={row['domain_id']:row for row in r['cases']}
    assert set(cases)=={'astronomy','materials','fluid_dynamics','mathematics'}
    assert all(row['selected_experiment_id']=='E-STRONG' for row in cases.values())
    assert all(row['revision_status']=='HIERARCHICAL_EXPLANATION_IDENTIFIED_POSTFREEZE' for row in cases.values())
    owner_triples={(row['theory_owner'],row['experiment_owner'],row['revision_owner']) for row in cases.values()}
    assert len(owner_triples)==1
    invariant=r['domain_label_invariance']
    assert {row['domain_id'] for row in invariant}=={'astronomy','nuclear','chemistry','biology','mathematics'}
    assert len({row['selected_experiment_id'] for row in invariant})==1
    assert len({row['utility'] for row in invariant})==1
    assert r['claim_boundary']['domain_specific_reasoning_algorithm_required'] is False


def test_real_scientific_portfolios_enter_shared_p3_readiness_contract(tmp_path):
    from evaluation.long_horizon_blind_cycle_qualification import _run_real_portfolio_ingress_qualification
    from source.lawspace.long_horizon_scientific_cycle import LongHorizonBlindScientificCycleKernel

    k=LongHorizonBlindScientificCycleKernel(ROOT, state_path=tmp_path/'real_portfolio_ingress_state.json')
    r=_run_real_portfolio_ingress_qualification(ROOT,k)
    assert r['status']=='PASS_REAL_SCIENTIFIC_PORTFOLIO_INGRESS_QUALIFICATION'
    assert r['passed']==r['total']
    rows={row['portfolio_id']:row for row in r['portfolios']}
    assert 'REAL-EXOPLANET-P3' in rows
    assert 'REAL-JHTDB-TURBULENCE-CLOSURE' in rows
    assert rows['REAL-EXOPLANET-P3']['domain_id']=='astronomy'
    assert rows['REAL-JHTDB-TURBULENCE-CLOSURE']['domain_id']=='fluid_dynamics'
    assert rows['REAL-JHTDB-TURBULENCE-CLOSURE']['status']=='PORTFOLIO_P3_THEORY_CONTRACT_REQUIRED'
    assert len({row['reasoning_owner'] for row in rows.values()})==1
    assert all(row['existing_evidence_reused_as_postfreeze_measurement'] is False for row in rows.values())
    assert all(row['next_gate'] for row in rows.values())
    assert r['claim_boundary']['domain_specific_reasoning_algorithm_introduced'] is False


@pytest.mark.parametrize('stage,expected', [
    ('no_theory', 'PORTFOLIO_P3_THEORY_CONTRACT_REQUIRED'),
    ('one_explanation', 'PORTFOLIO_COMPETING_EXPLANATIONS_REQUIRED'),
    ('no_models', 'PORTFOLIO_EXPERIMENTAL_MODELS_REQUIRED'),
    ('incomplete', 'PORTFOLIO_PREDICTION_CONTRACT_REQUIRED'),
    ('ready', 'PORTFOLIO_FROZEN_FRESH_MEASUREMENT_REQUIRED'),
])
def test_portfolio_readiness_preserves_missing_evidence_gate(tmp_path, stage, expected):
    from evaluation.long_horizon_blind_cycle_qualification import _route_real_scientific_portfolio
    from source.lawspace.long_horizon_scientific_cycle import LongHorizonBlindScientificCycleKernel
    from source.lawspace.theory_compiler import HierarchicalObservationalTheoryOwner

    kernel = LongHorizonBlindScientificCycleKernel(ROOT, state_path=tmp_path/'state.json')
    models = [{'experiment_id': 'E', 'observable': 'outcome', 'cost': 1,
               'predictions': {'H1': {'kind': 'categorical', 'value': 'A'},
                               'H2': {'kind': 'categorical', 'value': 'B'}}}]
    ids = ['H1', 'H2']
    if stage == 'one_explanation':
        ids = ['H1']
    if stage == 'no_models':
        models = []
    if stage == 'incomplete':
        del models[0]['predictions']['H2']
    theory = None if stage == 'no_theory' else HierarchicalObservationalTheoryOwner().compile(
        theory_id='TEST-READINESS', universal_layer={'type': 'test'},
        host_layer={'type': 'test'}, regime_layer={'type': 'test'},
        feasible_domain_layer={'type': 'test'},
        competing_explanations=[{'id': i} for i in ids],
        predictions=[{'prediction': 'outcome', 'falsification': 'mismatch',
                      'defense': 'freeze first', 'heldout_refit_allowed': False}],
        evidence_digest='TEST-PREFREEZE-EVIDENCE', experimental_models=models,
    )
    result = _route_real_scientific_portfolio(
        kernel, portfolio_id='TEST', domain_id='new_domain', theory=theory,
        provenance={'evidence_mode': 'EXISTING'},
    )
    assert result['status'] == expected
    assert result['existing_evidence_reused_as_postfreeze_measurement'] is False
    assert result['selected_experiment_id'] == ('E' if stage == 'ready' else None)


def test_portfolio_seal_requires_matching_file_bytes(tmp_path):
    from evaluation.long_horizon_blind_cycle_qualification import _sealed_digest_for_path

    artifact = tmp_path/'evidence.json'
    artifact.write_text('{}', encoding='utf-8')
    checksum = hashlib.sha256(artifact.read_bytes()).hexdigest()
    assert _sealed_digest_for_path(tmp_path, artifact) is None
    (tmp_path/'HASHES.txt').write_text(checksum+'  evidence.json\n', encoding='utf-8')
    assert _sealed_digest_for_path(tmp_path, artifact) == checksum
    artifact.write_text('{"changed": true}', encoding='utf-8')
    assert _sealed_digest_for_path(tmp_path, artifact) is None


def test_portfolio_missing_inputs_cannot_pass_qualification(tmp_path):
    from evaluation.long_horizon_blind_cycle_qualification import _run_real_portfolio_ingress_qualification
    from source.lawspace.long_horizon_scientific_cycle import LongHorizonBlindScientificCycleKernel

    kernel = LongHorizonBlindScientificCycleKernel(ROOT, state_path=tmp_path/'state.json')
    result = _run_real_portfolio_ingress_qualification(tmp_path, kernel)
    assert result['status'] == 'BLOCKED_REAL_SCIENTIFIC_PORTFOLIO_INGRESS_QUALIFICATION'
    assert result['passed'] < result['total']
    assert result['portfolios'] == []
