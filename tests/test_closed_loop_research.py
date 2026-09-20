from copy import deepcopy

import pytest

from evaluation.closed_loop_research_experiment import ProcessWorld, run
from source.lawspace.closed_loop_research import ClosedLoopResearchOwner, seal


@pytest.mark.parametrize('seed', [42, 113, 271])
def test_loop_measures_revises_and_freezes_before_final_reveal(seed):
    result = run(seed, 'signal', 2)
    assert result['status'] == 'CLOSED_LOOP_HELDOUT_SUPPORTED_NOT_LAW'
    assert len(result['rounds']) == 2
    for row in result['rounds']:
        assert row['experiment']['digest'] == row['response']['request_digest']
        assert row['experiment']['model_digest'] != row['revised_model_digest']
    assert result['final_freeze']['model_digest'] == result['rounds'][-1]['revised_model_digest']
    assert result['final_evaluation']['refit_performed'] is False
    assert result['claim_boundary']['law_established'] is False
    assert result['claim_boundary']['canonical_registry_mutated'] is False
    assert result['final_axis']['generated_coordinate']


@pytest.mark.parametrize('mode', ['noise', 'shift'])
def test_unpredictable_or_shifted_world_is_not_supported(mode):
    result = run(42, mode, 2)
    assert result['status'] == 'CLOSED_LOOP_REPRESENTATION_GAP'


@pytest.mark.parametrize('corruption', ['request_digest', 'axis_values', 'observed'])
def test_replayed_misbound_or_nonfinite_measurement_is_rejected(corruption):
    world = ProcessWorld()
    class BadAdapter:
        def measure(self, request):
            response = deepcopy(world.measure(request))
            if corruption == 'request_digest': response['request_digest'] = 'old-request'
            if corruption == 'axis_values': response['axis_values']['p'] += 1
            if corruption == 'observed': response['observed'] = float('nan')
            return seal(response)
        def reveal_holdout(self, request):
            pytest.fail('invalid measurement must stop before holdout reveal')
    try:
        with pytest.raises(ValueError):
            ClosedLoopResearchOwner().run(dict(dataset=world.initial, validation_regime_ids=['VALIDATION'],
                                              holdout_dataset_digest=world.holdout_digest), BadAdapter())
    finally:
        world.close()


def test_holdout_substitution_after_search_is_rejected():
    world = ProcessWorld()
    class BadHoldout:
        measure = world.measure
        def reveal_holdout(self, request):
            response = world.reveal_holdout(request)
            response['dataset']['y'][0] += 100
            return seal(response)
    try:
        with pytest.raises(ValueError, match='pre-search commitment'):
            ClosedLoopResearchOwner().run(dict(dataset=world.initial, validation_regime_ids=['VALIDATION'],
                                              measurement_budget=1,
                                              holdout_dataset_digest=world.holdout_digest), BadHoldout())
    finally:
        world.close()


def test_world_disallows_measurements_after_final_reveal():
    world = ProcessWorld()
    try:
        world.reveal_holdout(seal({'model_digest':'frozen'}))
        with pytest.raises(ValueError, match='closed after final reveal'):
            world.measure(seal({'axis_values':{'p':1.2, 'q':0.0}}))
    finally:
        world.close()
