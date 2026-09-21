import pytest
from source.lawspace.theory_compiler import HierarchicalObservationalTheoryOwner


def test_external_confirmation_cannot_be_granted_by_caller_flag():
    with pytest.raises(ValueError, match='verified evidence'):
        HierarchicalObservationalTheoryOwner().compile(
            theory_id='control', universal_layer={'declared': True},
            host_layer={'declared': True}, regime_layer={'declared': True},
            feasible_domain_layer={'declared': True},
            competing_explanations=[{'id': 'a'}, {'id': 'b'}],
            predictions=[{'prediction': 'p', 'falsification': 'f', 'defense': 'd', 'heldout_refit_allowed': False}],
            evidence_digest='control-not-world-attestation', fresh_external_confirmation=True)
