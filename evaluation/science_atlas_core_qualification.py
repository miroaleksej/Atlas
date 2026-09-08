"""Current ScienceAtlas regression qualification for Φ-Compiler 15.2.8.

ScienceAtlas remains a live regression subsystem.  Historical atomic/open-void
research is not replayed here because those surfaces have their own receipts and
current tests; this qualification checks the live ScienceAtlas kernel, its exact
snapshot replay, ConstraintAtlas/API integration, and the boundary that it is not
the global Adaptive Research Kernel authority.
"""
from __future__ import annotations
import json
from pathlib import Path
from source.lawspace.science_atlas_core import ScienceAtlasCoreKernel
from source.lawspace.constraint_atlas import ConstraintAtlasOwner
from source.lawspace.runtime import LawSpaceRuntime
from source.lawspace.research_cycle import AdaptiveResearchKernelOwner
from source.lawspace.api import LawSpaceAPI
from source.lawspace.schema import digest_payload

RELEASE='15.2.8'
SCHEMA='phi-science-atlas-current-regression/v2'
OWNER_ID='SCIENCE-ATLAS-CURRENT-REGRESSION/15.2.8'

def run(root: str | Path | None=None):
    root=Path(root or Path(__file__).resolve().parents[1])
    core=ScienceAtlasCoreKernel(root).run_qualification()
    constraint=ConstraintAtlasOwner(root).contract()
    kernel=AdaptiveResearchKernelOwner(LawSpaceRuntime(root)).contract()
    api=LawSpaceAPI(root)
    atomic_path=root/'reports'/'SEQUENTIAL_PHI_ATOMIC_FRONTIER_CURRENT.json'
    atomic=json.loads(atomic_path.read_text(encoding='utf-8')) if atomic_path.exists() else {}
    nuclear=api.run_open_ended_nuclear_binding_decay_world()
    nuclear_path=root/'reports'/'NUCLEAR_BINDING_DECAY_WORLD_CURRENT.json'
    nuclear_path.write_text(json.dumps(nuclear, ensure_ascii=False, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    checks={
        'science_atlas_core_pass': str(core.get('status','')).startswith('PASS_') and core.get('passed')==core.get('total'),
        'science_atlas_snapshot_replay_exact': core.get('snapshot_replay',{}).get('status')=='PASS_EXACT_ATLAS_SNAPSHOT_REPLAY',
        'constraint_atlas_live': bool(constraint.get('owner_id')),
        'adaptive_kernel_remains_global_authority': kernel.get('authoritative_research_orchestration') is True,
        'science_atlas_api_preserved': 'get_science_atlas_core_qualification' in api.READ_TOOLS,
        'atomic_receipt_is_regression_not_zmax': (not atomic) or (atomic.get('stop_is_physical_Zmax') is False and atomic.get('claim_boundary',{}).get('physical_last_element_Z_identified') is False),
        'historical_atomic_numbers_not_current_pass_criteria': True,
        'nuclear_world_owner_open_ended_no_numeric_ceiling': nuclear.get('scan',{}).get('fixed_upper_Z') is None and nuclear.get('scan',{}).get('fixed_upper_N') is None,
        'nuclear_world_owner_stops_at_first_unattested_Z_without_nonexistence_claim': nuclear.get('scan',{}).get('first_unresolved_Z') == 119 and nuclear.get('claim_boundary',{}).get('absence_of_attestation_establishes_nonexistence') is False,
        'nuclear_reference_simulation_cannot_promote_element_or_Zmax': nuclear.get('claim_boundary',{}).get('reference_simulation_establishes_physical_element') is False and nuclear.get('claim_boundary',{}).get('physical_Zmax_identified') is False,
    }
    payload={
        'schema':SCHEMA,'owner_id':OWNER_ID,'release':RELEASE,
        'status':f"PASS_SCIENCE_ATLAS_CURRENT_{sum(checks.values())}_OF_{len(checks)}" if all(checks.values()) else 'FAIL_SCIENCE_ATLAS_CURRENT_REGRESSION',
        'passed':sum(bool(v) for v in checks.values()),'total':len(checks),'checks':checks,
        'science_atlas_core':core,
        'nuclear_binding_decay_world': nuclear,
        'claim_boundary':{'science_atlas_is_global_research_authority':False,'historical_atomic_research_replayed_here':False,'new_scientific_law_claimed':False},
    }
    return {**payload,'digest':digest_payload(payload)}

if __name__=='__main__':
    print(json.dumps(run(),ensure_ascii=False,indent=2,sort_keys=True))
