"""Thin executable wrapper for the Atlas 15.26 EDA chip-design pilot."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from source.lawspace.eda_chip_design import EDAChipDesignResearchOwner


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument('--orfs-flow-root',required=True)
    ap.add_argument('--runner',default='docker_shell',choices=('auto','native','docker_shell'))
    ap.add_argument('--budget',type=int,default=14)
    ap.add_argument('--warm-start',type=int,default=12)
    ap.add_argument('--pool-size',type=int,default=256)
    ap.add_argument('--seed',type=int,default=15260)
    ap.add_argument('--timeout',type=int,default=1800)
    ap.add_argument('--output',default='atlas_chip_pilot_result.json')
    ns=ap.parse_args()
    result=EDAChipDesignResearchOwner().run_pilot(
        orfs_flow_root=ns.orfs_flow_root,runner=ns.runner,evaluation_budget=ns.budget,
        warm_start_count=ns.warm_start,candidate_pool_size=ns.pool_size,seed=ns.seed,
        timeout_seconds=ns.timeout,
    )
    Path(ns.output).write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({
        'status':result.get('status'),
        'research_freeze_digest':result.get('research_freeze',{}).get('digest'),
        'unique_world_evaluations':result.get('unique_world_evaluations'),
        'comparison':result.get('comparison'),
        'digest':result.get('digest'),
    },ensure_ascii=False,indent=2,sort_keys=True))
    # A valid negative comparison is a scientific result, not infrastructure failure.
    return 0 if result.get('status')=='CHIP_PILOT_LIVE_EDA_COMPLETE' else 2

if __name__=='__main__': raise SystemExit(main())
