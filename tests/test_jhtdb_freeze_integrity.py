"""Offline checks: content bindings, not independent world attestation."""
from copy import deepcopy
from pathlib import Path

import pytest

from evaluation.run_fresh_jhtdb_sgs_observational_experiment import (
    build_requests, canonical_digest, load_json, sha256_file,
    validate_freezes, _fetch_with_retry,
)
from evaluation.freeze_jhtdb_sgs_child_forms import verify_content_digest

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports/turbulence'


def docs():
    return (load_json(REPORTS/'JHTDB_SGS_OBSERVATIONAL_PROTOCOL_FROZEN.json'),
            load_json(REPORTS/'ATLAS_RANDOM20_SGS_CHILD_FORMS_FREEZE.json'))


@pytest.mark.parametrize('target', ['protocol', 'source', 'child'])
def test_modified_freeze_content_cannot_keep_old_digest(target):
    protocol, child = docs()
    obj = protocol['protocol'] if target == 'protocol' else protocol['source_capability'] if target == 'source' else child
    obj['tampered'] = True
    with pytest.raises(ValueError, match='content mismatch'):
        validate_freezes(protocol, child)


def test_sample_paths_cannot_escape_output_directory():
    protocol, _ = docs()
    protocol['protocol']['sample_contracts'][0]['sample_id'] = '../escape'
    with pytest.raises(ValueError, match='safe directory name'):
        build_requests(protocol['protocol'])


@pytest.mark.parametrize('retries', [0, 2])
def test_retry_budget_is_exact(retries):
    calls = []
    def fail(*args, **kwargs):
        calls.append(1)
        raise RuntimeError('HTTP Error 503')
    with pytest.raises(RuntimeError, match='503'):
        _fetch_with_retry(fail, None, None, None, max_retries=retries, retry_base_seconds=0)
    assert len(calls) == retries + 1


def test_supplied_raw_acquisition_is_bound_without_computing_targets():
    protocol, child = docs()
    proto = validate_freezes(protocol, child)
    receipt = load_json(REPORTS/'JHTDB_SGS_FRESH_ACQUISITION_RECEIPT.json')
    verify_content_digest(receipt)
    assert receipt['protocol_digest'] == proto['digest']
    assert receipt['child_forms_freeze_digest'] == child['digest']
    assert receipt['sample_ids'] == proto['sample_ids']
    assert receipt['fresh_targets_computed'] is False
    assert receipt['scientific_law_established'] is False
    for sample, contract in zip(receipt['samples'], proto['sample_contracts']):
        verify_content_digest(sample)
        assert sample['start_xyz_1based'] == contract['start_xyz_1based']
        assert sample['snapshot_index_frozen'] == contract['snapshot']
        assert sha256_file(ROOT/sample['npz_path']) == sample['npz_sha256']
        for slab in sample['slabs']:
            verify_content_digest(slab)
            assert slab['protocol_digest'] == proto['digest']
            assert sha256_file(ROOT/slab['array_path']) == slab['array_sha256']


def test_author_sgs_selection_replays_in_common_p3_owner():
    from source.lawspace.theory_compiler import HierarchicalObservationalTheoryOwner
    from source.lawspace.long_horizon_scientific_cycle import HierarchicalObservationalExperimentOwner

    family = load_json(REPORTS/'ATLAS_RANDOM20_SGS_HYPOTHESIS_FAMILY_FREEZE.json')
    verify_content_digest(family, 'freeze_digest')
    verify_content_digest(family['hypothesis_family_lineage'])
    assert sha256_file(REPORTS/family['source_reaudit_receipt']) == family['source_reaudit_receipt_sha256']
    models = deepcopy(family['experimental_models'])
    for model in models:
        model['predictions'] = {k: {'kind': 'categorical', 'value': v} for k,v in model['predictions'].items()}
    theory = HierarchicalObservationalTheoryOwner().compile(
        theory_id='LOCAL-REPLAY-AUTHOR-SGS', universal_layer={'family': family['hypothesis_family_lineage']['family_id']},
        host_layer={'scope': 'DNS'}, regime_layer={'scope': 'filter scale'}, feasible_domain_layer={'scope': 'local closure'},
        competing_explanations=family['competing_hypotheses'],
        predictions=[{'prediction': 'declared categories', 'falsification': 'incompatible outcome',
                      'defense': 'freeze first', 'heldout_refit_allowed': False}],
        evidence_digest=family['freeze_digest'], experimental_models=models,
    )
    selected = HierarchicalObservationalExperimentOwner().freeze(theory=theory, cost_budget=4)['selected_experiment']
    assert selected['experiment_id'] == family['selected_experiment_id']
    assert selected['utility'] == family['selected_experiment_utility'] == 0.625
    # Replaying supplied predictions does not establish their scientific adequacy
    # or authenticate the author's claim of a premeasurement freeze.
