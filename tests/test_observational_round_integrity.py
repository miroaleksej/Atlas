from copy import deepcopy
import pytest
from source.lawspace.schema import digest_payload
from source.lawspace.theory_compiler import HierarchicalObservationalTheoryOwner
from source.lawspace.long_horizon_scientific_cycle import HierarchicalObservationalExperimentOwner, HierarchicalObservationalTheoryRevisionOwner


def theory():
    return HierarchicalObservationalTheoryOwner().compile(
        theory_id='integrity-control', universal_layer={'x': 1}, host_layer={'x': 1},
        regime_layer={'x': 1}, feasible_domain_layer={'x': 1},
        competing_explanations=[{'id': 'a'}, {'id': 'b'}], evidence_digest='test-only',
        predictions=[{'prediction': 'p', 'falsification': 'f', 'defense': 'd', 'heldout_refit_allowed': False}],
        experimental_models=[{'experiment_id': 'e', 'observable': 'o', 'cost': 1,
            'predictions': {'a': {'kind': 'categorical', 'value': 'A'}, 'b': {'kind': 'categorical', 'value': 'B'}}}])


def test_unknown_outcome_requests_expansion_not_nearest_theory():
    frozen = HierarchicalObservationalExperimentOwner().freeze(theory=theory(), cost_budget=2)
    result = HierarchicalObservationalTheoryRevisionOwner().revise(frozen_experiment=frozen,
        measurement={'experiment_id': 'e', 'freeze_digest': frozen['freeze_digest'], 'value': 'OUTSIDE'})
    assert result['status'] == 'REPRESENTATION_EXPANSION_REQUIRED'
    assert result['surviving_explanation_ids'] == []
    assert result['leading_explanation_id'] is None


def test_mutated_frozen_predictions_are_rejected():
    frozen = HierarchicalObservationalExperimentOwner().freeze(theory=theory(), cost_budget=2)
    changed = deepcopy(frozen)
    changed['selected_experiment']['predictions']['a']['value'] = 'CHANGED'
    with pytest.raises(ValueError, match='digest'):
        HierarchicalObservationalTheoryRevisionOwner().revise(frozen_experiment=changed,
            measurement={'experiment_id': 'e', 'freeze_digest': frozen['freeze_digest'], 'value': 'CHANGED'})


@pytest.mark.parametrize('change', ['missing_prediction', 'negative_cost', 'bad_theory_digest'])
def test_invalid_portfolio_is_rejected(change):
    t = theory()
    if change == 'missing_prediction':
        del t['experimental_models'][0]['predictions']['b']
    elif change == 'negative_cost':
        t['experimental_models'][0]['cost'] = -1
    if change != 'bad_theory_digest':
        t['digest'] = digest_payload({k: v for k, v in t.items() if k != 'digest'})
    else:
        t['digest'] = 'unverified'
    if change == 'missing_prediction':
        result = HierarchicalObservationalExperimentOwner().freeze(theory=t, cost_budget=2)
        assert result['status'] == 'BLOCKED_INCOMPLETE_EXPERIMENT_PREDICTIONS'
        assert result['selected_experiment'] is None
        return
    with pytest.raises(ValueError):
        HierarchicalObservationalExperimentOwner().freeze(theory=t, cost_budget=2)
