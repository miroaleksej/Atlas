from source.lawspace.einstein_dynamics import EinsteinDynamicsOwner
from source.lawspace.api import LawSpaceAPI
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_curvature_memory_owner_survives_clean_baseline_without_postfreeze_seed():
    owner = EinsteinDynamicsOwner()
    contract = owner.contract()
    assert contract['owner_id'] == 'EINSTEIN-DYNAMICS-OWNER/12.6.0'
    assert not (ROOT/'data/evidence/bh_lawvoid_02_postfreeze_prior_art.json').exists()
    assert callable(owner.run_curvature_memory_order_reduced_black_hole_experiment)
    assert callable(owner.run_curvature_memory_closure_qualification)


def test_curvature_memory_api_and_claim_boundary():
    api=LawSpaceAPI(ROOT)
    tools=api.READ_TOOLS
    assert 'run_curvature_memory_order_reduced_black_hole_experiment' in tools
    assert 'run_curvature_memory_closure_qualification' in tools
    c=api.get_curvature_memory_covariant_closure()
    assert c['full_nonlinear_pg_component_reduction_established'] is False
