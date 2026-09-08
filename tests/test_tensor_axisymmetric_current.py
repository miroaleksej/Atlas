from pathlib import Path
from source.lawspace.api import LawSpaceAPI
from source.lawspace.einstein_dynamics import EinsteinDynamicsOwner
from source.lawspace.tensor_geometry import TensorGeometryOwner

ROOT = Path(__file__).resolve().parents[1]

def test_tensor_einstein_owners_remain_live_while_old_receipts_are_absent():
    tensor = TensorGeometryOwner().contract()
    einstein = EinsteinDynamicsOwner().contract()
    assert tensor['owner_id'] == 'TENSOR-GEOMETRY-OWNER/12.6.0'
    assert einstein['owner_id'] == 'EINSTEIN-DYNAMICS-OWNER/12.6.0'
    assert tensor['not_claimed']
    assert einstein['hard_boundaries']['exact_reduced_sector_is_general_4d_solution'] is False
    for name in ('TENSOR_SPIN2_ODD_CURRENT.json','BH_SPIN2_ODD_GAUGE_PATCH_CURRENT.json','BH_SPIN2_ODD_POSTFREEZE_CURRENT.json'):
        assert not (ROOT/'reports'/name).exists()
    required = {
        'run_tensor_geometry_spin2_odd_qualification',
        'run_tensor_geometry_horizon_aligned_closure_qualification',
        'run_tensor_geometry_full_parity_odd_euler_multipole_qualification',
        'run_spin2_odd_gauge_patch_screen',
        'get_spin2_odd_postfreeze_assessment',
    }
    assert required.issubset(set(LawSpaceAPI.READ_TOOLS))
